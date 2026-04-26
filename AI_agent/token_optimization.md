# Token 优化方案

> **目的**：把单 case token 消耗从 ~150k 降到 ~30-50k。
> **背景**：[CLAUDE.md §7.7](CLAUDE.md)。
> **基础数据来源**：sm_15 全 MCP 流水线实测（[run_log](../test_data/SmallOffice/smalloffice_15/output/run_log.md)） + Explore agent MCP 摸底报告（2026-04-26）。

---

## 1. 问题诊断

### 1.1 sm_15 token 消耗分布

14 zones / 84 surfaces / 12 windows 的几何阶段单 case：

| 来源 | Token 量级 | 占比 |
|---|---|---|
| 14 × `create_zone` × ~2500 | ~35k | 23% |
| **84 × `update_surface` × ~750** | **~63k** | **42%（最大头）** |
| 12 × `create_fenestration_surface` × ~400 | ~5k | 3% |
| 模型在工具调用之间的推理文本 | ~22k | 15% |
| Skill 文档 + system prompt | ~10k | 7% |
| 中途掉线 1 次 → history 重灌 | ~+30k | 20% |
| **合计** | **~150k** | |

### 1.2 单次 MCP 工具的返回值结构（Explore agent 报告确认）

| 工具 | 返回字段 | 体积 |
|---|---|---|
| `update_surface` | `{"success": bool, "message": str, "data": {完整 Surface 对象}}` | 2-4 KB（含 4 顶点 JSON） |
| `create_zone` | 同上 + `surfaces_created: [...]` | 8-12 KB（含 4 个自动 surface） |
| `create_fenestration_surface` | 同上 | 1-2 KB |

**关键澄清**：每次返回**只包含被操作对象的完整 dump**，**不包含全局 ConfigState**——这点比预想好。但单 surface 的 4 顶点 JSON 仍是大头。

### 1.3 为什么本地部署也需要这个改动

常见误解："本地模型 TPM 消失，每次 MCP 调用 token 不要钱了，没必要优化。"

实际：

| 维度 | 闭源 SaaS（Opus / Sonnet） | 本地开源模型 |
|---|---|---|
| TPM 速率限制 | 受限（Tier 决定） | **消失** |
| 每 token **货币成本** | 真金白银 | "免费"（电费 / 显存时间） |
| **上下文窗口容量** | 200k | **更小**（多数 8k-32k；32B 级实际可用 16k-64k） |
| **长 tool-chain 稳定性** | Opus ≈ 99%，Sonnet ≈ 95% | **明显劣化**：50+ 步后开始漏调用、忘参数、回吐文本 |
| **长上下文准确率衰减** | 较缓 | **更陡**：30k token 后准确率可能 -20% |

→ 优化对闭源是省钱、对开源是**能跑通的前提**。两条路都受益。

---

## 2. 改动清单（按 ROI 排序）

### 2.1 P0 改动 1：MCP 工具返回值改为 ack-only

**最高 ROI**。MCP 工具默认只返回操作确认 + 名字，不再吐对象 dump；通过 `verbose=True` 可选回退到完整对象。

**改造形态**：
```python
# 当前
{"success": True, "message": "...", "data": {完整 Surface 对象 with 4 vertices}}

# 改为默认
{"success": True, "name": "F1_S1_Wall_1"}

# 加可选 verbose
update_surface(name="...", verbose=False, ...)  # 默认精简
update_surface(name="...", verbose=True, ...)   # 兼容旧行为
```

**改造位置**：
- [src/mcp/interface.py:12-33](../src/mcp/interface.py) — `ToolResponse` 类型定义
- 各工具实现层（`src/mcp/tools/*.py` + `src/mcp/api/*.py`）

**预计节省**：84 × ~600 token = **~50k / case**
**工作量**：~150 行（统一加 verbose 开关 + 默认精简响应）
**风险**：低
- LLM 不需要看 surface 顶点回显（自己写进去的）
- 只在 debug / `list_*` 时要全量
- 如有极端情况需要回看，`verbose=True` 仍可用

**验收**：sm_15 重跑后 update_surface 的对话历史每次只有 ~150 字而非 ~3000 字。

---

### 2.2 P0 改动 2：MCP 加批量接口（`update_surfaces_batch` 等）

把 84 次 round-trip 压缩成 1 次。

**改造形态**：
```python
# src/mcp/api/envelope.py 新增
@mcp.tool
def update_surfaces_batch(updates: list[dict]) -> dict:
    """Batch update multiple surfaces in one call.

    Args:
        updates: list of dicts, each with keys (name, outside_boundary_condition,
                 sun_exposure, wind_exposure, construction_name, ...)

    Returns:
        {"success": bool, "count": int, "failed": [name, ...]}
    """
    results = [SurfaceTool.update(**u) for u in updates]
    failed = [u["name"] for u, r in zip(updates, results) if not r.success]
    return {"success": not failed, "count": len(results), "failed": failed}
```

**改造位置**（Explore agent 报告确认）：
- [src/mcp/server.py:45-111](../src/mcp/server.py) — 五大 `register_*_tools()` 注册入口
- [src/mcp/tools/base.py](../src/mcp/tools/base.py) — 加 `batch_update` 抽象方法（~20 行）
- `src/mcp/tools/surface.py` 等具体工具类 — 实现遍历调用（~10-15 行 / 工具 × 12 工具 = ~120 行）
- `src/mcp/api/envelope.py` 等 API 层 — 装饰器注册新工具（~20 行 / 模块 × 5 模块）
- **不需改 ConfigState**（[src/mcp/state.py:33-140](../src/mcp/state.py) 现有 `update()` 已支持局部更新）

**预计节省**（与改动 1 配合）：再省 ~25k / case
**工作量**：~200-250 行跨 6-8 文件（agent 估算）
**风险**：中
- batch 中部分失败的回滚语义需测试（决定是 all-or-nothing 还是 partial-success）
- 错误信息聚合的可读性
- 建议先实现 `partial-success + 详细 failed list` 模式

**优先做的批量接口**（按调用频次）：
1. `update_surfaces_batch` — sm_15 用 84 次（最热）
2. `create_zones_batch` — sm_15 用 14 次
3. `create_fenestration_surfaces_batch` — sm_15 用 12 次

**验收**：sm_15 重跑后 MCP 调用总次数从 110+ 降到 ~10。

---

### 2.3 P0 改动 4：`scripts/export_idf.py` 外置（与 MCP 无关，独立做）

把 [skills/energyplus_mcp/export_idf.md](../skills/energyplus_mcp/export_idf.md) 里 80 行 Python 搬到独立脚本，skill 只留一句调用。

**改造方式**：
1. 在 [scripts/](../scripts/) 下新建 `export_idf.py`：
   ```python
   #!/usr/bin/env python
   """Convert geometry-phase YAML to IDF with the 4 fix patches.

   Usage:
       python scripts/export_idf.py <case_dir>

   Reads:  <case_dir>/output/<case_name>.yaml
   Writes: <case_dir>/output/<case_name>.idf
   """
   import sys
   from pathlib import Path
   from src.validator.data_model import BaseSchema
   from src.converter_manager import ConverterManager

   def export(case_dir: Path) -> Path:
       case_name = case_dir.name
       yaml_path = case_dir / "output" / f"{case_name}.yaml"
       idf_path  = case_dir / "output" / f"{case_name}.idf"

       BaseSchema.set_idf(Path("data/dependencies/Energy+.idd"))
       mgr = ConverterManager(yaml_path)
       mgr.convert_all()

       # Patch 1: RunPeriod None → defaults
       rp = mgr._idf.idfobjects['RUNPERIOD'][0]
       rp.Day_of_Week_for_Start_Day = 'Sunday'
       # ... (其余 6 行 from export_idf.md)

       # Patch 2: Building warmup days
       mgr._idf.idfobjects['BUILDING'][0].Minimum_Number_of_Warmup_Days = 1

       # Patch 3 (geometry-phase no-op but idempotent): Surface→Adiabatic
       for surf in mgr._idf.idfobjects['BUILDINGSURFACE:DETAILED']:
           if surf.Outside_Boundary_Condition == 'Surface':
               surf.Outside_Boundary_Condition = 'Adiabatic'
               # ...

       # Patch 4 (geometry-phase no-op): Schedule:Compact None
       for sch in mgr._idf.idfobjects['SCHEDULE:COMPACT']:
           # ...

       mgr.save_idf(idf_path)
       return idf_path

   if __name__ == '__main__':
       p = export(Path(sys.argv[1]))
       print(f"IDF saved: {p}")
   ```

2. 改 [skills/energyplus_mcp/energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) Step 5 c：
   ```
   c. Convert YAML → IDF: run `python scripts/export_idf.py <case_dir>`.
      The script applies the 4 fix patches automatically.
   ```

3. [skills/energyplus_mcp/export_idf.md](../skills/energyplus_mcp/export_idf.md) 改为「脚本说明文档」（描述 4 个补丁的语义 + 何时该手工调），不再被 LLM 当模板抄。

**预计节省**：3-5k / case
**工作量**：30 分钟（基本是搬代码）
**风险**：0
**验收**：sm_15 重跑后 LLM 不再写内联 80 行 Python；只一行 Bash。

---

### 2.4 P1 改动 3：`create_zone` 自动 boundary 推断

**目标**：让 `create_zone` 在创建 6 个默认 surface 时，**根据楼层位置和邻接关系自动推断**外/内/地/顶 boundary，绝大多数 surface 不需要 `update_surface` 修。

**当前行为**（[src/mcp/state.py](../src/mcp/state.py) ConfigState）：6 个 surface 一律 `Outdoors + Default_Construction`。

**改造逻辑**：
- F1 zone 的最低面 → `Ground + Default_Ext_Wall`
- 顶层 zone 的最高面 → `Outdoors + SunExposed + Default_Ext_Wall`（屋面）
- 与已存在 zone 共面的 wall → `Adiabatic + Default_Int_Wall`
- 其余 wall → `Outdoors + SunExposed + Default_Ext_Wall`

**预计节省**：14-zone 案例下，84 次 update_surface 砍到 ~10-20 次（只剩需要修正的边角内墙）→ 配合改动 1+2 还能再省 ~15k
**工作量**：~100-150 行（加邻接判断 + 几何 coplanar 检测）+ 修改 skill 文档
**风险**：中-高
- 几何邻接判断容易引入 bug（浮点等于、cocircular 顶点排序）
- 需要单元测试覆盖：单层 / 多层 / 退台 / 挑空
- skill Step 3 表格需要重写为"只覆盖偏离自动推断的 case"

**为什么 P1 而非 P0**：风险较高，且 P0 三档做完单 case 已经能进 ~70-80k 区间，对 Opus 调试和 Sonnet 测试已经够用。改动 3 是为本地开源模型部署做的真正减负，本阶段非必需。

---

## 3. 综合预估

| 状态 | 单 case token | Opus 单会话能否完成 | 备注 |
|---|---|---|---|
| 当前（sm_15 实测） | ~150k | 勉强（已掉线 1 次） | baseline |
| 改动 4 单做 | ~145k | 同 | 收益最小但风险 0 |
| 改动 1 单做 | ~100k | 稳定 | 最大杠杆 |
| 改动 1+4 | ~95k | 稳定 | |
| 改动 1+2 | ~75k | 余裕大 | **P0 完成态** |
| 改动 1+2+4 | ~70k | 余裕大 | **推荐目标** |
| 改动 1+2+3+4 | ~30-50k | 余裕极大 | 可上 Sonnet / 开源 |

---

## 4. 实施顺序

**第一阶段**（本周可做完，纯 token 优化，风险可控）：

1. **Day 1**：改动 4 — 30 分钟搬代码 + sm_15 验证脚本调用通畅
2. **Day 1-2**：改动 1 — MCP `interface.py` 加 verbose 开关、默认精简 ack；做单元测试
3. **Day 2-3**：改动 2 — 加 batch 接口，先做 `update_surfaces_batch`（最热），再做 `create_zones_batch` / `create_fenestration_surfaces_batch`
4. **Day 3**：sm_15 重跑做 token 回归对比；目标 ≤ 80k
5. **Day 4**：Sonnet 4.6 重跑 sm_15 做能力对比

**第二阶段**（本地模型部署前必须做）：

6. 改动 3 — 自动 boundary 推断（带单元测试）
7. ConverterManager 加 `geometry_only=True` 旁路（省去预置 3 个占位 Construction 的手工补丁，参考 [sm_15 run_log §5.1](../test_data/SmallOffice/smalloffice_15/output/run_log.md)）

---

## 5. 验收标准

**改动 1 单独验收**：
- sm_15 重跑后 update_surface 的对话历史里每次工具结果 ≤ 200 字
- 全程跑通无 missing-info 错误（说明 LLM 不依赖 verbose 回显）
- `verbose=True` 测试用例验证回退路径

**改动 2 单独验收**：
- sm_15 重跑后 MCP 工具调用 ≤ 10 次（vs 原 110+ 次）
- batch 中刻意构造 1 个失败用例，其余应 partial-success 完成，failed list 准确
- 错误信息可读（说出哪个 surface 哪个字段错了）

**改动 4 单独验收**：
- sm_15 重跑后 LLM 在 IDF 导出时只一行 Bash
- `scripts/export_idf.py` 能脱离 Claude 会话独立运行（开发者直接 `python scripts/export_idf.py <case>` 复现）

**整体验收**：
- sm_15 全程不掉线
- token 总量 ≤ 80k
- IDF 产物对象计数与之前一致（zones=14 / surfaces=84 / fenestration=12）
- OpenStudio 3D 视图打开后几何完全一致

---

## 6. 与其他工作流的衔接

- **MEP 阶段 skill**：MEP 阶段 skill 落地时（未来），同样需要 batch 接口 — Materials / Constructions / Schedules / People / Lights / HVAC 都是大量重复创建。本轮 P0 改动 2 的 batch 接口会被 MEP 阶段直接复用。
- **AI_agent/eval/run_case.py**（[plan.md](plan.md) P0）：评测脚本会自动跑 sm_0..sm_15 全集，token 优化可以让 Opus baseline 跑得起（13 案例 × 150k = 2M token，按 Opus 价格不便宜）。
- **Sonnet 降级 / 本地开源迁移**：token 优化是这两条路能跑通的前提，详见上文 §1.3。

---

_最后更新：2026-04-26（首版）_
