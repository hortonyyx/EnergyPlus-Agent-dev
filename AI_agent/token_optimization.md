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

### 2.1 P0 改动 1：MCP 工具返回值改为 ack-only ✅ 已完成（2026-04-27）

**最高 ROI**。MCP CRUD 工具默认只返回操作确认 + 名字，不再吐对象 dump。

**最终方案（对原 verbose 方案的优化）**：未给 77 个 `@mcp.tool` 函数加 `verbose` 参数（避免代码膨胀且 LLM 不会主动用），改在 [src/mcp/tools/base.py](../src/mcp/tools/base.py) 的 BaseTool 模板里直接调整默认返回:

| 操作 | 之前 | 现在 |
|---|---|---|
| `create` | `data = instance.model_dump()`（~1.5-3 KB） | `data = {"name": <name>}`（~30 字节） |
| `update` | 同上 | 同上 |
| `read` / `get` | 完整 dump | **保留完整 dump**（LLM 主动调 `get_*` 即等价于 verbose 路径） |
| `list_all` | `[完整 dump, ...]` | `[<name>, ...]`（仅名字列表） |
| `delete` | 不变 | 不变 |

**create_zone 特例**：[src/mcp/api/core.py](../src/mcp/api/core.py) 显式拼装 `data = {"name": <name>, "surfaces_created": [...]}`，保留 6 个自动 surface 名字（LLM 后续 `update_surface` 必须靠它）。

**workflow.py 不动**：`export_yaml` / `load_yaml` / `run_simulation` / `get_summary` / `validate_config` 的 `data` 都是必须的载荷，未触动。

**改造范围**：仅 2 个文件（[src/mcp/tools/base.py](../src/mcp/tools/base.py) 3 处 + [src/mcp/api/core.py](../src/mcp/api/core.py) 1 处），共 ~10 行修改。

**实测节省（sm_15 端到端回归）**：
- 加载 sm_15 YAML → list_zones 返回 14 名字 / list_surfaces 返回 84 名字 / update_surface 返回 `{"name": "Zone_F1_S1_Floor"}` ✓
- 单次 `update_surface` 响应：~3000 字节 → ~30 字节，84 次累计 -~250 KB context；按 ~4 字符/token 估算 ≈ **节省 ~60k token / case**（超出预期 50k）
- get_summary / validate_config / load_yaml 等 workflow 路径全部回归通过

**备份**：`MCP_history/2026-04-27_mcp_pre_ack_only/`

---

### 2.2 P0 改动 2：MCP 加批量接口 ✅ 已完成（2026-04-27）

**最终范围（对原方案的收窄,详见 §2.2.x 设计讨论）**：只做 2 个 batch,**不做** `create_zones_batch`。

| 工具 | 落地 | 理由 |
|---|---|---|
| **`update_surfaces_batch`** | ✅ | 最热(sm_15: 84 次;真实案例可达 200+);几何复杂度无关(纯字段赋值),partial-success 安全 |
| **`create_fenestration_surfaces_batch`** | ✅ | 中频但与 surface batch 共享代码模式,边际成本低 |
| ~~`create_zones_batch`~~ | ❌ 不做 | 内含 6 个自动 surface + 失败回滚逻辑;批量化 → 逐 zone 状态机复杂度激增;且热区合并后 zone 数封顶 10-30,单调用足够 |

**实际改动范围**：仅 1 文件（[src/mcp/api/envelope.py](../src/mcp/api/envelope.py) 末尾追加 ~120 行;比原估 200-250 行小一半）。
- `base.py` 不动 — batch 循环逻辑直接写在 API 层,避免给 BaseTool 增加抽象
- `server.py` / `state.py` / 其他 `tools/*.py` 全部不动
- 新增依赖：`from pydantic import ValidationError` + `from src.mcp.interface import ToolResponse`

**返回形态**（partial-success 语义）：
```json
{
  "success": true/false,
  "message": "Batch update_surface: 84 succeeded, 0 failed.",
  "data": {
    "count": 84,
    "succeeded": ["Zone_F1_S1_Floor", "..."],
    "failed": [{"name": "X", "error": "validation: ..."}]
  }
}
```

**3 类失败模式回归(实测通过)**：
1. 不存在的目标 → 工具层 `not found` 错误,落入 `failed`
2. 缺 `name` 字段 → API 层预校验拦截,落入 `failed`
3. 字段值非法 → Pydantic / 下游验证错,落入 `failed`
其余项继续正常执行,不会因为 1 个错就全部回滚。

**Skill 同步**（强制使用 batch,关键纪律）：
- [skills/energyplus_mcp/energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) Step 3 / Step 4 改为 "USE THE BATCH TOOL — one call only";"first pass must be a single batch call covering every surface produced by Step 2"
- [skills/energyplus_mcp/open_model/energyplus_mcp_prompt.md](../skills/energyplus_mcp/open_model/energyplus_mcp_prompt.md) §0 hard constraint #4 改为 "One tool call per turn",显式说明 batch 调用本身是一次 tool call;Step 7 / Step 8 同步
- 备份至 `Skill_history/2026-04-27_energyplus_mcp_pre_batch/`

**MCP 注册验证**：通过 `mcp.list_tools()` 确认 batch 工具已注册(`update_surfaces_batch` / `create_fenestration_surfaces_batch`),工具总数 77 → 79。

**备份**：`MCP_history/2026-04-27_mcp_pre_batch/`

---

### 2.2.x 设计讨论(对原方案的关键修正,2026-04-27)

落地前与用户讨论后,对原 §2.2 方案做了 3 处实质调整,记录如下供后续参考。

#### A. 范围收窄:不做 `create_zones_batch`

原方案列了 3 个 batch(surfaces / zones / fenestration)。讨论后排除 zones_batch:

- **几何复杂度集中在 `create_zone`**(自动生成 N 面 surface;L 形 / 不规则 zone 时 N 可变),批量化后"以 zone 为粒度"的 partial-success 状态机难写、难维护。
- **热区合并后 zone 数封顶**(realistic case 10-30):14 / 30 次 round-trip 是可接受代价,batch 收益边际。
- **`update_surface` 完全不吃几何复杂度**(只是字段赋值),无论 zone 是矩形还是 L 形,batch 化都同样安全。

→ 几何复杂度的隐性风险全部被关在 `create_zone` 单调用里面了,batch 化只针对"per-item 独立"的工具。

#### B. 实现层不放 `base.py`,直接写在 API 层

原方案在 `base.py` 加 `batch_update` 抽象方法。讨论后改为直接在 `envelope.py` 写 inline 循环:
- `base.py` 抽象的"循环 + 聚合"逻辑只有 ~5 行,抽象不抵成本
- API 层本就要做 Pydantic input 校验,把 batch 循环放这里只多 ~10 行
- 减少 base.py 的耦合,future 工具不会被强制有 batch 方法

→ 总改动 200-250 行 → 120 行,跨 6-8 文件 → 1 文件。

#### C. ROI 随案例规模线性增长 → 现在做 vs. 真实案例下做没差别

讨论中用户问"sm_15 (14 zone) 是否过于理想化、真实案例改动 2 风险更大?"。结论:

| 案例阶段 | zone | surface | 改动 1 后 token | 改动 1+2 后 | batch 节省 |
|---|---|---|---|---|---|
| sm_15 当前 | 14 | 84 | ~95k | ~70k | -25k |
| 中型办公(预估) | ~25 | ~150 | ~140k | ~75k | **-65k** |
| 多层不规则(预估) | ~40 | ~280 | ~240k | ~85k | **-155k** |

- batch 实现成本是**一次性**的(120 行)
- 节省**线性**于 N(surface 数)
- → "等真实案例再做"是错的,因为(a)真实案例时单会话已撑爆 200k(b)实现复杂度与几何无关,提前做不增加工作量

#### D. Skill 改动是真正的隐性风险

batch 工具加了之后,Opus 默认仍按习惯逐个调 `update_surface`。讨论后达成共识:**skill 文档措辞必须强硬**——"USE THE BATCH TOOL — one call only" / "first pass must be a single batch call",不能写成"recommended"。否则 batch 工具加了也没收益,纯净负债(代码 + tool list 噪音)。

落地时已用强约束语气改写了主 skill Step 3/4 和 open_model skill Step 7/8;open_model §0 hard constraint #4 还显式澄清了"一次 batch 调用 = 一次 tool call"避免与"one step per turn"冲突。

---

### 2.3 P0 改动 4：`Tool_scripts/export_idf.py` 外置 ✅ 已完成（2026-04-27）

**落地位置**：[../Tool_scripts/export_idf.py](../Tool_scripts/export_idf.py)（注：根目录新建 `Tool_scripts/`，未沿用规划中的 `scripts/`，避免与已有 `scripts/run_demo.py` 等 LangGraph demo 脚本混在一处）。

**实际产物**：
- 单一 CLI：`python Tool_scripts/export_idf.py <case_dir>`
- **5 条补丁**（比原计划多 1 条）：
  - **补丁 0（新增）**：`convert_all` 之前预置 1 个 NoMass 占位 Material + 3 个占位 Construction（`Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window`）。原 sm_15 run_log §5.1 已记录但未脚本化的硬要求 — 不加这条，所有 fenestration 会被 `FenestrationConverter` 静默丢掉（每次 `_add_to_idf` 都 `raise ValueError`，外层 `try/except` 吞错并 `state["failed"] += 1`）。
  - 补丁 1-4：原 export_idf.md 的 RunPeriod None / warmup days / Surface→Adiabatic / Schedule:Compact None。
- skill 同步更新：[../skills/energyplus_mcp/export_idf.md](../skills/energyplus_mcp/export_idf.md) 重写为薄文档；[../skills/energyplus_mcp/energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) Step 5c 改为单行 Bash；[../skills/energyplus_mcp/open_model/energyplus_mcp_prompt.md](../skills/energyplus_mcp/open_model/energyplus_mcp_prompt.md) Step 10 同步。

**实测节省（sm_15 冒烟）**：
- 命令：`uv run python Tool_scripts/export_idf.py test_data/SmallOffice/smalloffice_15`
- 产物对象计数：14 zones / 84 surfaces / **12 fenestration** / 3 Construction / 1 Material
- 对比之前：fenestration **0 → 12**（补丁 0 收益）；LLM 不再产出 80 行 inline Python。

**节省**：3-5k / case + 修复 fenestration 静默丢失（隐性收益更大）
**风险**：0（实测通过）

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

**改动 1 单独验收 ✅（2026-04-27）**：
- 单元回归：直调 ZoneTool / SurfaceTool / WorkflowTool create+update+list+read 形状全对（[src/mcp/tools/base.py](../src/mcp/tools/base.py) 模板验证）
- 端到端回归：load_yaml(sm_15) → list_zones=14 名字 / list_surfaces=84 名字 / update_surface 返回 `{"name": "..."}` / get_summary counts 正确 / validate_config 报与之前一致的 96 个占位 Construction 引用错误
- LLM 行为待验证（需要新一轮 sm_15 跑通对比 token 总量 — 见整体验收）

**改动 2 单独验收 ✅（2026-04-27）**：
- 单元回归：用 sm_15 加载后跑 batch,5 个合法 + 3 个故意失败(不存在名 / 缺 name / 非法字段值),返回 5 succeeded / 3 failed,每个 failed 含可读 error 字符串 ✓
- MCP 注册：`mcp.list_tools()` 含 `update_surfaces_batch` + `create_fenestration_surfaces_batch`,工具总数 77 → 79 ✓
- LLM 行为待 sm_15 实跑验证(目标:Step 3 单批 84 次合一 / Step 4 单批 12 次合一,MCP 调用总次数从 ~110 降至 ~10)

**改动 4 单独验收 ✅（2026-04-27）**：
- sm_15 重跑后 LLM 在 IDF 导出时只一行 Bash
- `Tool_scripts/export_idf.py` 已脱离 Claude 会话独立运行（`uv run python Tool_scripts/export_idf.py test_data/SmallOffice/smalloffice_15` 直跑产出 14/84/12 完整 IDF）

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

_最后更新：2026-04-27（晚 2）— P0 改动 2 落地:`update_surfaces_batch` + `create_fenestration_surfaces_batch`,inline 在 [src/mcp/api/envelope.py](../src/mcp/api/envelope.py) 末尾(~120 行,1 文件);base.py 不动;skill 主 + open_model 版 Step 3/4(7/8) 改为强约束 batch-only;备份 `MCP_history/2026-04-27_mcp_pre_batch/` 和 `Skill_history/2026-04-27_energyplus_mcp_pre_batch/`;§2.2 整段重写,新增 §2.2.x 设计讨论(范围收窄不做 zones_batch、实现层选择、ROI 线性放大、skill 强约束)_

_2026-04-27（P0 改动 1 落地：MCP CRUD ack-only，base.py 模板 + create_zone 特例；备份 `MCP_history/2026-04-27_mcp_pre_ack_only/`；§2.1 / §5 改动 1 验收 已勾选）_

_2026-04-27（P0 改动 4 落地：`Tool_scripts/export_idf.py`，含 5 条补丁；§2.3 / §5 改动 4 验收 已勾选）_

_2026-04-26（首版）_
