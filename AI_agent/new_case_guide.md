# 新建测试样例操作指南

> 面向 [../test_data/SmallOffice/](../test_data/SmallOffice/) 目录下新增一个 SmallOffice 测试案例的标准流程。
> 当前基于 **Claude Opus 人工流水线**；未来脚本化评测参见本文第四节。

---

## 零、流水线总览

```
Step 1 准备素材 → Step 2 建目录 → Step 3 写 JSON →
Step 4 挂 MCP → Step 5 LLM 执行 → Step 6 验证归档 → Step 7 留痕
```

---

## 一、Step 1 · 准备视觉素材

在建模 / CAD / 渲染软件导出 4 张 PNG，放进临时目录待用。

| 文件名（强约定） | 必需 | 内容 | 规格建议 |
|---|---|---|---|
| `top_view.png` | **必需** | 俯视平面图，含尺寸标注（开间/进深/墙位） | ≥ 1024 px 宽；黑线墙 + 白色房间；走廊留白 |
| `front_view.png` | **必需** | 正立面图 | 能看清层高、窗位、窗高 |
| `side_view.png` | **必需** | 侧立面图 | 同上 |
| `<supp_plan>.png` | 可选 | 补充平面图 / 剖面 / 轴测 | 复杂造型时提供 |

**关键约束**：
- 俯视图 **必须有尺寸链**（见 §1.1），否则 LLM 无法精确还原房间边界。
- 走廊画成 **宽白带**（宽度 ≥ 房间 1/3），不是细线墙 —— LLM 依靠「宽白带 vs 细黑线」区分走廊和墙（[energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 第 3 条）。
- 楼梯 / 卫生间 / 电梯画出标准符号（楼梯：平行斜线+箭头；WC 标志；电梯框）。

### 1.1 尺寸标注规范（sm_13 起强制）

> **背景**：sm_0 ~ sm_12 全部是**无尺寸的纯几何线框**，坐标完全靠 LLM 从 `Floor area` 反推猜测（见 [smalloffice_0/claude_ep.md:14-29](../test_data/SmallOffice/smalloffice_0/claude_ep.md) 的 `0m/5m/10m/15m` 全是 Claude 自编）。这导致「房间尺寸中位误差」永远无 ground truth 可比。**sm_13 起必须带尺寸标注**，以支撑 [pivot_criteria.md §1.1](pivot_criteria.md) 的房间尺寸误差阈值可测。

**俯视图（`top_view.png`）**：
- **两级尺寸链**
  - 一级（外部）：总开间 / 总进深，画在图外侧上方 + 左侧，单根带箭头
  - 二级（外部）：分段开间 / 分段进深，画在一级之外一层，每段独立数字
- **字体 & 线型**：
  - 数字用**黑色等宽字体**（Consolas / 等线），字号占图面高度 1.5%~2.5%
  - 引出线用 0.5 pt 细黑线，**不与墙线重合颜色**
  - 尺寸线与墙体保持 ≥ 字号 × 2 的留白，避免 OCR 粘连
- **单位**：
  - 全图**只用一种单位**（`mm` 推荐，与下游 `*_mm` 字段对齐）
  - 数字裸写数值（如 `3600`），单位只在图例角落注明一次
- **坐标原点**：左下角 = (0, 0)，x 向右、y 向上（CCW），与 `zonetool_prompt.md` 约定一致。

**立面图（`front_view.png` / `side_view.png`）**：
- 层高尺寸链画在**左侧**外部，逐层标注 `floor_height_mm`
- 窗台高 `window_sill_mm` 与窗顶高 `window_head_mm` 用细引线标注
- 室外地坪标高（Z=0）明确标出

**禁忌**（会让 PaddleOCR 误读）：
- ❌ 尺寸数字压在墙线上
- ❌ 多单位混用（`3600mm` 和 `3.6m` 并存）
- ❌ 分数 / 带小数点不足 2 位（`3.6` vs `3.60` 不一致）
- ❌ 红色 / 蓝色标注（走廊白带区分依赖单色通道）

### 1.2 Ground Truth 记录（新增字段）

sm_13 起，`testdata_prompt.json` 除原有 10 个字段外，**追加**以下 GT 字段（为 [plan.md P0](plan.md) 评测脚本准备）：

| 字段 | 作用 |
|---|---|
| `_gt_meta` | 单位 / 坐标系 / CCW 约定元信息 |
| `Ground truth building envelope` | 外轮廓 footprint + 层高 + 层数 |
| `Ground truth zones` | 每个 zone 的 name / floor / function / `floor_vertices_mm` / `z_origin_mm` / `height_mm` |
| `Ground truth adjacency` | zone → 邻接 zones 列表（无向） |
| `Ground truth fenestration` | WWR / 窗台高 / 窗顶高 / 哪些外墙有窗 |

模板参见项目根目录的 [../../testdata_prompt.json](../../testdata_prompt.json)，新建 sm_13 时直接复制到 `test_data/SmallOffice/smalloffice_13/testdata_prompt.json` 并按实际图纸尺寸改写。

**旧字段依然保留**（`TestName` / `Floor area` / `Number of *` / 3 条路径），skill 文档无需改动即可兼容。

---

## 二、Step 2 · 建案例目录

在 [../test_data/SmallOffice/](../test_data/SmallOffice/) 下**编号递增**建目录（当前末位 `smalloffice_12`，新案例用 `smalloffice_13`）：

```bash
mkdir -p test_data/SmallOffice/smalloffice_13/output
cp /path/to/top_view.png   test_data/SmallOffice/smalloffice_13/top_view.png
cp /path/to/front_view.png test_data/SmallOffice/smalloffice_13/front_view.png
cp /path/to/side_view.png  test_data/SmallOffice/smalloffice_13/side_view.png
```

---

## 三、Step 3 · 写 `testdata_prompt.json`（Format A 入口）

模板（严格照 [smalloffice_11/testdata_prompt.json](../test_data/SmallOffice/smalloffice_11/testdata_prompt.json) 的字段名，**不要改 key**）：

```json
{
    "TestName": "SmallOffice_13",
    "Building location": "Shenzhen",
    "Floor area": "240m²",
    "Building type": "Office",
    "Top view path of the building": "test/test_data/SmallOffice/smalloffice_13/top_view.png",
    "Front view path of the building": "test/test_data/SmallOffice/smalloffice_13/front_view.png",
    "Building side view path": "test/test_data/SmallOffice/smalloffice_13/side_view.png",
    "Path of the supplementary plan example drawing for the building": "",
    "Number of thermal zones per floor of the building": "9",
    "Number of total thermal zones in the building": "18",
    "Number of floors": "2"
}
```

**字段说明**：
- `TestName` → 必须与目录名严格一致（现有 sm_0 / sm_5 的 TestName 都错写成 `"SmallOffice_0"`，**不要沿袭**，新案例务必正确填 `SmallOffice_13`）。
- `Building location` → 当前仅有 [../data/weather/Shenzhen.epw](../data/weather/Shenzhen.epw)，**首选深圳**；其他城市需自备 EPW 放到 [../data/weather/](../data/weather/)。
- `Floor area` → 可空字符串，LLM 会从俯视图尺寸链自算。
- 3 条路径 → 用 `test/test_data/…` 前缀（历史约定保持一致；LLM 实际通过 Read 工具按绝对路径读取，不会出错）。
- 末 3 个整数字段（`Number of thermal zones per floor / total / Number of floors`）→ 这是 **Ground Truth**，评测脚本要拿它比对 LLM 产出，**务必数准**。

---

## 四、Step 4 · 挂载 MCP 服务器

项目 MCP 工具**不是内建的**，必须先启 MCP 服务。二选一：

```bash
# 方式 A：stdio（配合 Claude Desktop / Claude Code 直接挂）
uv run main.py mcp-server

# 方式 B：HTTP（给其他 MCP 客户端用）
uv run main.py mcp-server --transport http --host 127.0.0.1 --port 8000
```

**Claude Desktop** 配置参考（[../README.md](../README.md)）：

```json
{
  "mcpServers": {
    "energyplus-agent": {
      "command": "uv",
      "args": ["--directory",
               "c:/Users/Horton/Desktop/科研2/EnergyPlus-Agent-dev",
               "run", "main.py", "mcp-server"]
    }
  }
}
```

**Claude Code** 用户：在当前目录用 `/mcp` 挂载，或在 `.mcp.json` 写同样的 server 段。挂好后 Claude 能看到 `mcp__EnergyPlus-Agent__create_zone` 等一系列工具。

---

## 五、Step 5 · 触发 LLM 执行

打开 Claude（模型 = **Opus**），投递 4 份 skill 文档 + 案例路径：

````text
请按以下 skill 文档完成 EnergyPlus IDF 构建：

@skills/energyplus_mcp/energyplus_mcp_prompt.md
@skills/energyplus_mcp/zonetool_prompt.md
@skills/energyplus_mcp/schedule_compact_guide.md
@skills/energyplus_mcp/export_idf.md

测试案例目录：
test_data/SmallOffice/smalloffice_13/

严格按 skill 文档执行：
1. 识别 Format A → 读 testdata_prompt.json
2. 读 4 张视图
3. 裁剪 + 6× 放大 + 画标注，保存 top_view_annotated.png
4. 写 claude_ep.md（邻接矩阵 + 坐标表 + ASCII 平面图)
5. 按 list_* → create_* 顺序调 MCP 工具
6. validate_config + export_yaml(smalloffice_13.yaml)
7. 按 export_idf.md 完整脚本转 IDF → output/smalloffice_13.idf
8. 运行仿真：
   energyplus -w data/weather/Shenzhen.epw \
       -d test_data/SmallOffice/smalloffice_13/output \
       -r test_data/SmallOffice/smalloffice_13/output/smalloffice_13.idf
````

**LLM 过程中会**：
- `Read` PNG（多模态）
- `Bash` 执行 PIL 标注脚本
- `Write` 生成 `claude_ep.md`
- 调 `mcp__EnergyPlus-Agent__create_zone / create_surface / create_fenestration_surface / …` 累积 `ConfigState`
- 调 `mcp__EnergyPlus-Agent__export_yaml` 导出 YAML
- `Bash` 跑 [export_idf.md](../skills/energyplus_mcp/export_idf.md) 完整脚本 → IDF → EP

**人工兜底**：参照 [claude.md §3.1.2](claude.md) 的系统性缺陷清单主动追问：
- 「请补齐 `schedule_specs` 列表中所有 schedule 的 `create_schedule_compact` 调用」
- 「请为每个 zone 创建 `create_light` 和 `create_hvac_ideal_loads_system`」
- 「请核对内墙构造是否对称（两侧都用 `Int_Wall`），或按 [export_idf.md](../skills/energyplus_mcp/export_idf.md) 第 3 条补丁改成 Adiabatic」

---

## 六、Step 6 · 验证与归档

### 6.1 目录最终形态

```
test_data/SmallOffice/smalloffice_13/
├── testdata_prompt.json          ← 手写
├── top_view.png                   ← 你放的
├── front_view.png                 ← 你放的
├── side_view.png                  ← 你放的
├── top_view_annotated.png         ← LLM 生成
├── claude_ep.md                   ← LLM 生成
├── smalloffice_13.yaml            ← MCP export_yaml 产物
└── output/
    ├── smalloffice_13.idf         ← ConverterManager 产物
    └── eplusout.*                 ← EP 仿真产物（.end / .err / .eso …）
```

### 6.2 五档验证清单（对应 [claude.md §3.1.2](claude.md) 的基线指标）

```bash
# ① claude_ep.md 存在且非空
test -s test_data/SmallOffice/smalloffice_13/claude_ep.md && echo "[1] OK"

# ② YAML zones 数量 vs testdata_prompt.json 的声明
python -c "
import yaml, json
p='test_data/SmallOffice/smalloffice_13/'
with open(p+'smalloffice_13.yaml') as f: d=yaml.safe_load(f)
with open(p+'testdata_prompt.json') as f: j=json.load(f)
actual=len(d.get('Zone',[]))
expected=int(j['Number of total thermal zones in the building'])
print(f'[2] zones actual={actual} expected={expected} match={actual==expected}')
"

# ③ IDF 存在
test -f test_data/SmallOffice/smalloffice_13/output/smalloffice_13.idf && echo "[3] OK"

# ④ EP 仿真状态（期望 "Terminated--Successfully"，不是 "Fatal Error"）
cat test_data/SmallOffice/smalloffice_13/output/eplusout.end

# ⑤ Severe 数量（应为 0）
grep -c "Severe" test_data/SmallOffice/smalloffice_13/output/eplusout.err
```

### 6.3 子系统覆盖度自检（针对 [claude.md §3.1.2](claude.md) 的系统性缺陷）

```bash
python -c "
import yaml
p='test_data/SmallOffice/smalloffice_13/smalloffice_13.yaml'
with open(p) as f: d=yaml.safe_load(f)
def n(k): return len(d.get(k,[])) if isinstance(d.get(k),list) else (1 if d.get(k) else 0)
print(f'zones={n(\"Zone\")}')
print(f'surfaces={n(\"BuildingSurface:Detailed\")}')
print(f'fenestration={n(\"FenestrationSurface:Detailed\")}')
print(f'schedules={n(\"Schedule:Compact\")}                 ← 历史普遍为 0，新案例务必 > 0')
print(f'people={n(\"People\")}')
print(f'lights={n(\"Lights\")}                              ← 历史普遍为 0，新案例务必 > 0')
print(f'hvac_ideal={n(\"HVACTemplate:Zone:IdealLoadsAirSystem\")}  ← 历史普遍为 0，新案例务必 > 0')
"
```

---

## 七、Step 7 · 留痕（用于开源模型迁移对照）

- 用 Claude Opus 跑完的**对话记录**存成：
  ```
  AI_agent/experiments/<YYYY-MM-DD>_opus_sm13/transcript.md
  ```
- 走 LangGraph Agent 路径时用 [../scripts/export_trace.py](../scripts/export_trace.py) 导出 tool-call trace 作为微调数据。
- 把 §6 产出的 5 档指标 + 子系统覆盖度写进 `AI_agent/experiments/<date>_<model>/result.json`，供后续跨模型比对。

---

## 八、常见坑位清单

| 坑 | 表现 | 处理 |
|---|---|---|
| `TestName` 写错（沿袭 sm_0/5 的 bug） | 评测脚本按目录名对不上 | 命名与目录严格一致 |
| 俯视图缺尺寸链 | LLM 瞎猜房间宽度 → zone 数量错 | 返工加标注；或 JSON 里补 `Floor area` 兜底 |
| 走廊画成细线 | LLM 把走廊识别为墙 → 少一个 zone | 画成宽白带（≥ 房间 1/3 宽） |
| 挂 MCP 走错目录 | `create_zone` 工具不可见 | 确认 `--directory` 指向仓库根 |
| LLM 跳过 schedule/lights/HVAC | IDF 生成但 EP Fatal | 主动追问补齐 |
| 内墙跨区构造不对称 | EP Severe: InterZone not matched | 导 IDF 时**必须**执行 [export_idf.md](../skills/energyplus_mcp/export_idf.md) 第 3 条补丁（内墙 `Outside_Boundary_Condition=Adiabatic` + `Int_Wall`） |
| 非深圳位置缺 EPW | `energyplus` 启动即报找不到 weather | 先放好 [../data/weather/](../data/weather/)`<City>.epw` |
| `uv.lock` 解析报错 `duplicate key "xxhash"` | `uv run` 无法启动环境 | 修 `uv.lock` 的重复条目，或临时用系统 Python + 手装依赖 |

---

## 九、自动化脚本蓝图（未来工作）

当前 Step 5 仍是**人工对话驱动**。目标是把整条流水线脚本化，复用 [../src/agent/](../src/agent/) 的 LangGraph：

```python
# AI_agent/eval/run_case.py （草图）
def run_case(case_dir: Path, llm_config: LLMConfig) -> CaseResult:
    prompt_json = case_dir / "testdata_prompt.json"
    images = [case_dir / n for n in ("top_view.png",
                                     "front_view.png",
                                     "side_view.png")]

    graph = build_graph()
    initial = AgentState(
        user_input = prompt_json.read_text(encoding="utf-8"),
        image_paths = [str(p) for p in images if p.exists()],
    )
    context = SimContext(
        epw_path  = Path("data/weather/Shenzhen.epw"),
        output_dir = case_dir / "output",
    )
    state = run_session(graph, initial, context,
                        {"configurable": {"thread_id": case_dir.name}},
                        on_interrupt=auto_approval)

    return CaseResult(
        has_claude_ep = (case_dir/"claude_ep.md").exists(),
        has_yaml      = bool(list(case_dir.glob("*.yaml"))),
        has_idf       = (case_dir/"output"/f"{case_dir.name}.idf").exists(),
        ep_started    = (case_dir/"output"/"eplusout.end").exists(),
        ep_completed  = "Successfully" in
                        (case_dir/"output"/"eplusout.end").read_text(),
        zone_match    = count_zones() == expected_total_zones(),
    )
```

脚本到位后，新建案例只做 Step 1–3，然后：

```bash
python AI_agent/eval/run_case.py test_data/SmallOffice/smalloffice_13
```

即可自动跑完 Step 4–6 并产出指标。这是 [claude.md §4.3](claude.md) 的 **M2 里程碑**。

---

_最后更新：2026-04-21（增补 §1.1 尺寸标注规范 + §1.2 GT 字段）_
