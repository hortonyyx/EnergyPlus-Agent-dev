# 新建测试样例操作指南 —— 两步法新架构正式版（2026-05-29）

> 面向新增一个 SmallOffice 测试案例的**标准完整流程**（正式测试用）。
>
> **两条使用模式，先分清**：
> - **平时 dev 测试**：直接指定各阶段模型，让主控 Agent 开子代理跑（如 phase1 用一个子会话、phase2 换不同模型对比）。灵活、临时，**不走本指南**。
> - **正式测试（本指南）**：完整端到端。**除 phase1 目前半人工喂矢量外，phase2 + 9 个下游 subagent + EnergyPlus 全自动一次性跑完**。每次测试用**一份 per-case 模型配置**(`<case>/llm.yaml`,从全局拷贝当默认、自己改),方便快速切模型组合;全局 [`src/configs/llm.yaml`](../../src/configs/llm.yaml) 作兜底。详见 §5.1。
>
> **架构**：两步法 intake（[architecture/architecture.md](../architecture/architecture.md)）。phase1 = 图 → 语义矢量 JSON（看图、只识不推）；phase2 = 矢量 JSON → `IntakeOutput`（不看图、纯拓扑推理）。两步分离 = **误差预算分离**（识图错归 phase1，推理错归 phase2）。规则真身在 [`skills/intake_pipeline/`](../../skills/intake_pipeline)。
>
> 旧单步法版本备份在 [logs/backup/new_case_guide.md.bak_2026-05-29](../logs/backup/new_case_guide.md.bak_2026-05-29)。

---

## 零、流水线总览

```
Step 1 备视觉素材  →  Step 2 建案例目录  →  Step 3 写 testdata_prompt.json
   ↓
Step 4 phase1 识图（半人工，唯一人工步）
   - Claude Code 会话 + 多模态强模型，逐图重绘语义矢量
   - 产出：<case>/phase1_vector/*.json + phase1_summary.md
   ↓
Step 5 一次性自动跑（phase2 + 下游 + EP，全部 llm.yaml 配置）
   - python scripts/run_full_pipeline.py <case> \
         --base-dir test_data/SmallOffice_TwoStep --phase1-from phase1_vector
   - intake_node 跑 phase2（矢量 → IntakeOutput）→ 9 subagent → cross_ref
     → validate → 装配 IDF → InterZone 几何门 → simulate
   - 产出：<case>/output/intake_output.json + temp_*.yaml/.idf + eplusout.*
   ↓
Step 6 验收（L1 Pydantic / L2 cross_ref / InterZone 门 / L3 OpenStudio / L4 EP）
Step 7 留痕到 test_data/test_baseline/runs/
```

**和单步法的唯一流程差异**：Step 4 从「一个会话出 `intake_output.json`」变成「phase1 出矢量 JSON」，phase2 收进 Step 5 自动跑。Step 1–3、Step 6–7 基本沿用。

---

## 一、Step 1 · 准备视觉素材

> 素材规范与单步法一致。

立面图**按朝向命名**，每个文件代表其所**面朝**的立面；未提供的朝向按无窗处理。

| 文件名（强约定） | 必需 | 内容 |
|---|---|---|
| `{k}f_view.png`（k=1..N） | **必需** | 第 k 层平面图，含尺寸标注；外包围 `W × D` 必须每层一致 |
| `South_view.png` / `North_view.png` / `East_view.png` / `West_view.png` | 可选 | 对应朝向立面（南=y0 / 北=ymax / 东=xmax / 西=x0） |
| `supp_plan.png` | 可选 | 补充平面 / 剖面 / 轴测 |

**尺寸标注规范**：逐层平面画完整两级尺寸链（总开间/进深 + 分段）；走廊画宽白带（≥房间 1/3 宽）；楼梯/WC/电梯画标准符号；单位 `mm`；原点左下角 (0,0)，x 右 y 上。立面：左标层高链、右标 `top_gap | window_height | sill_height`、底标窗水平位置链、标 Z=0 地坪。

---

## 二、Step 2 · 建案例目录

两步法语料放 [`test_data/SmallOffice_TwoStep/`](../../test_data/SmallOffice_TwoStep)`<case>/`（与单步法 `SmallOffice/` 并列）。

```bash
case=smalloffice_22
mkdir -p test_data/SmallOffice_TwoStep/$case/phase1_vector
mkdir -p test_data/SmallOffice_TwoStep/$case/output

cp /path/to/1f_view.png  test_data/SmallOffice_TwoStep/$case/1f_view.png
cp /path/to/2f_view.png  test_data/SmallOffice_TwoStep/$case/2f_view.png
cp /path/to/South_view.png test_data/SmallOffice_TwoStep/$case/South_view.png
# ... 按实际有窗朝向挑选
```

目录约定（**固化布局，2026-06-09**，权威详表见 [pipeline_stage_contracts §3.1](../architecture/pipeline_stage_contracts.md)）：
- 源图（`*_view.png`）+ `testdata_prompt.json` + `llm.yaml` 放 `<case>/` 根
- phase1 矢量产物放 `<case>/phase1/`（旧 case 用 `phase1_vector/`，`--phase1-from` 后跟目录名）
- phase2 产物按 0–5 阶段分门别类放 `<case>/{1_correction, 2_modelling, 3_split_pairing, 4_mep, 5_intakeoutput}/`（2026-06-09 重构）：1_correction=2a 校正+确定性核；2_modelling=几何内核 build（`building_geometry.json`）；3_split_pairing=序列化几何 specs；4_mep=物理撰写（LLM）；5_intakeoutput=最终 `intake_output.json` + 契约校验
- 下游装配 + EP 产物放 `<case>/EP_run/`
- 各阶段校验工具：phase1 用 `render_vector_to_png.py`；1_correction 用 `render_corrected_geometry.py`（逐层平面图）；2_modelling 看 `kernel_gate_report.json`；EP 段 InterZone 门 + EP `.err`

---

## 三、Step 3 · 写 `testdata_prompt.json`

放 `<case>/testdata_prompt.json`（schema A，与单步法一致）：

```json
{
    "TestName": "smalloffice_22",
    "Building location": "Shenzhen",
    "Floor area": "240m²",
    "Building type": "Office",
    "Number of floors": 2,
    "Floor plans": [
        {"floor": 1, "path": "test_data/SmallOffice_TwoStep/smalloffice_22/1f_view.png", "thermal_zones": 7},
        {"floor": 2, "path": "test_data/SmallOffice_TwoStep/smalloffice_22/2f_view.png", "thermal_zones": 7}
    ],
    "South view path of the building": "test_data/SmallOffice_TwoStep/smalloffice_22/South_view.png",
    "North view path of the building": "test_data/SmallOffice_TwoStep/smalloffice_22/North_view.png",
    "East view path of the building":  "test_data/SmallOffice_TwoStep/smalloffice_22/East_view.png",
    "West view path of the building":  "test_data/SmallOffice_TwoStep/smalloffice_22/West_view.png",
    "Path of the supplementary plan example drawing for the building": ""
}
```

| 字段 | 说明 |
|---|---|
| `TestName` | 与目录名严格一致（全小写下划线） |
| `Building location` | 气象文件名映射；当前仅 [Shenzhen.epw](../../data/weather/Shenzhen.epw) |
| `Number of floors` | 与 `Floor plans` 长度一致 |
| `Floor plans` | **必填**数组 `[{"floor": k, "path": "{k}f_view.png", "thermal_zones": int}, ...]` |
| `{South,North,East,West} view path` | 可空。空串 = 该朝向无窗 |

> phase2 读的是**原始 `testdata_prompt.json`**（`run_full_pipeline` 直接传原文，不做摘要）。

---

## 四、Step 4 · phase1 识图（半人工 —— 唯一人工步）

> **目标**：每张图（逐层平面 + 各立面 + 补充图）→ 一份语义矢量 JSON（strokes 笔画 + 尺寸链 + OCR），外加一份 `phase1_summary.md`（含 4 立面 local↔world 翻译公式）。**只识图、不做拓扑**。
>
> **为什么仍半人工**：全自动 VLM phase1（`llm.yaml:intake_phase1` 段，预留未接）等 pivot 阶段再上；当前 dev 用 Claude Code 多模态会话喂，识图质量可控、可人工校验。

### 4.1 跑 phase1

1. 仓库根新起独立 Claude Code 会话，选多模态强模型（如 Opus）。
2. 把 [**附录 A · phase1 启动 prompt**](#附录-a--phase1-启动-prompt粘进-claude-code-会话)整段贴入，按 case 改图名表。规则真身在 [`skills/intake_pipeline/phase1/`](../../skills/intake_pipeline/phase1)（`guide.md` 流程/误差预算/输出容器 + `reading_guide.md` 跨画法识别 + `pen_library.md` 笔库），会话运行时读取。
3. 会话先做一张 pilot 停下等审；审 OK 再 batch 其余。

### 4.2 产物 + 人工校验

**产物**：`<case>/phase1_vector/{1f_view,2f_view,...,South_view,...}.json` + `<case>/phase1_vector/phase1_summary.md`。

用 [`Tool_scripts/render_vector_to_svg.py`](../../Tool_scripts/render_vector_to_svg.py) 把矢量 JSON 渲成 SVG/PNG，肉眼比对原图，重点看（[[phase1-output-conventions]]）：
- 杂物（家具/铺装/纹理）有没有被误当 wall/window（假阳性，**最致命**）
- 真墙/真窗有没有漏（假阴性）
- 门洞有没有按规则 heal 成连续墙（带门符号才补、留痕）
- `uncaptured_visual_elements` 是否如实登记了「看到但没画」的

> **误差预算红线**：phase1 一旦看错（误读尺寸、偏移坐标、翻转立面 x 轴、漏笔画），phase2 不看图、无从回溯，会把错当真带下去。**宁可填 `null` 也不猜**。

---

## 五、Step 5 · 一次性自动跑（phase2 + 下游 + EP）

> phase1 矢量落盘后，**一条命令全自动跑完**。phase2 不看图、纯文本推理；之后 9 个下游 subagent 建 IDF；几何门把关；EP 仿真。

### 5.1 模型配置（per-case 独立指定，全局兜底）

**每次正式测试用一份独立的模型配置**，方便快速切模型组合做对比。机制:

- 配置文件解析顺序(`run_full_pipeline` → 环境变量 `EP_AGENT_LLM_CONFIG` → [`src/agent/llm.py:resolve_llm_config_path`](../../src/agent/llm.py)):
  1. `--llm-config <path>` 显式指定 → 用它
  2. 否则 **`<case>/llm.yaml`** 存在 → 用它(**per-case 默认,推荐**)
  3. 否则 → 全局 [`src/configs/llm.yaml`](../../src/configs/llm.yaml)(兜底默认)
- 解析到的配置对**所有自动阶段统一生效**(phase2 + 9 下游);命令行/代码不单独指定模型。

**起一份 per-case 配置**(从全局拷贝当默认,再自己改):
```bash
python scripts/run_full_pipeline.py <case> --base-dir test_data/SmallOffice_TwoStep --init-llm-config
# → 生成 <case>/llm.yaml(全局副本);编辑它设本测试的模型组合,之后正常跑即自动用它
```
`<case>/llm.yaml` 建议随 case 提交,作"这次测试用了什么模型组合"的记录。

各 section → 阶段映射(全局默认值;per-case 拷贝后同结构,改值即可):

| 阶段 | section | 默认模型 | thinking |
|---|---|---|---|
| **phase2 拓扑** | `intake_phase2` | deepseek-v4-pro | **enabled**(单次推理,要思考预算)|
| 下游 surface / construction / fenestration | `default` | deepseek-v4-pro | disabled(几何瓶颈节点用 pro)|
| 下游 zone / material / schedule / hvac / people / lights | `zone`(`*flash` 锚)| deepseek-v4-flash | disabled(CRUD 型节点)|
| phase1(半人工,不经此配置)| —(未来 `intake_phase1`)| Claude Code 会话选的模型 | — |
| cross_ref / validate / **InterZone 门** / simulate | 无 LLM | 确定性代码 | — |

> **thinking 口径**:`intake_phase2` 单次推理开 thinking(重空间推理);`default`/`*flash` 是多轮 ReAct,thinking 必须 disabled(langchain_openai 不回传 `reasoning_content`,开则 400)。两者刻意相反,别"统一"。

### 5.2 触发约定（对话驱动）

> 用户**不必手敲命令**。在长期工作会话里自然语言触发。

**用户口令**（任一）：`跑 <case>` / `Step 5 <case>` / `两步法跑 <case>`。

**助手收到口令依次**：
1. **校验入参**：`<case>/phase1_vector/` 存在且含 `*.json` + `phase1_summary.md`；`testdata_prompt.json` 存在
2. **echo 模型配置**：先解析本次用哪份配置(`<case>/llm.yaml` 若存在,否则全局),再 echo 其 `intake_phase2` + `default` + flash 关键字段(照 §5.1 表),并报明配置文件路径
3. **询问 y/n**：`以上配置开跑？(y/n)`
4. **y** → 后台启动命令，stdout tee 到 `<case>/output/pipeline_run.log`。完成后报告每节点 + InterZone 门结果 + EP 状态
5. **n** → 等用户改 llm.yaml 后再触发

### 5.3 命令（助手内部执行 / 用户绕过时手敲）

```bash
python scripts/run_full_pipeline.py <case> \
    --base-dir test_data/SmallOffice_TwoStep \
    --phase1-from phase1_vector
```

脚本动作：
1. 读 `testdata_prompt.json`（原文）+ 收集图路径
2. `--phase1-from phase1_vector` → 把 `<case>/phase1_vector/` 交给 `intake_node`
3. `intake_node` 跑 **phase2 多段**（[`src/agent/phase2.py`](../../src/agent/phase2.py)）：2a 校正(LLM)→确定性核→**几何内核**(代码：造面+切配，序列化成 surface_specs)→**4_MEP**(LLM，只产非几何 8 字段)→**5_intakeoutput**(代码：装配 + 契约校验)。产物按阶段落 `<case>/{1_correction,2_modelling,3_split_pairing,4_mep,5_intakeoutput}/`，最终 `intake_output.json` 在 `5_intakeoutput/`；下游 + EP 落 `<case>/EP_run/`。几何确定、LLM 只剩物理语义（fork a：下游 surface_agent 忠实誊写）
4. phase 1 并行：zone / material / schedule
5. `cross_ref_foundations` → `construction → surface → fenestration` 串行
6. phase 3 并行：hvac / people / lights
7. `cross_ref_complete → validate`（auto_approval）
8. **装配 IDF → InterZone 几何门**（[`src/validator/interzone.py`](../../src/validator/interzone.py)）：配对存在/互逆/单一引用/面积/法向相反/共面/最小边长。有 issue → `success=False`，**IDF 照落盘但 EP 不跑**
9. 门过 → `simulate`：转 IDF → 跑 EnergyPlus

**有用 flag**：`--llm-config <path>`(显式指定本次模型配置,优先于 `<case>/llm.yaml`);`--init-llm-config`(从全局拷一份 `<case>/llm.yaml` 模板后退出,给你改);`--intake-only`(只跑到 phase2 出 `intake_output.json` 停,调试 phase2 用);`--output-subdir output_v2`(同 case 多版对照);`--no-simulate`(出 IDF 不跑 EP)。

### 5.4 单独迭代 phase2（可选）

只想调 `phase2/rules.md`、不跑下游时，用薄 CLI 包装（与主线同一份 `run_phase2`，不会漂移）：

```bash
python Tool_scripts/run_phase2_deepseek.py --case test_data/SmallOffice_TwoStep/<case>
# 产物：<case>/phase2_intake/deepseek/{intake_output.json, raw_response.txt, thinking.txt}
```

### 5.5 中途异常

| 现象 | 处理 |
|---|---|
| `RuntimeError: ... no api_key` | 检查 `.env` 的 `DEEPSEEK_API_KEY` |
| phase2 报 JSON decode / Pydantic 错 | 看 `<case>/output/phase2_intake/{raw_response,parse_error}.txt`；多半是 phase2/rules 缺口或 phase1 矢量有问题 |
| phase2 卡很久 | client 已设 `timeout=600`；超时会报错而非挂死 |
| `cross_ref_*` 报命名 drift | phase2 输出跨字段命名不一致；看 rules.md 命名约束 |
| **InterZone 门 fail（`success=False`）** | 看日志 `interzone_pair_issues`：退化碎片 / 面积不符 / 不互逆 = **phase2 跨层 split-pairing 几何质量问题**（识图建模质量主线）。门正确挡下，**不是架构 bug**；IDF 已落盘可检视 |
| `simulate` Fatal | 看 `eplusout.err`（门过了仍 fatal 较罕见）|

---

## 六、Step 6 · 验收

| 层 | 检查 | 何处 |
|---|---|---|
| **L1 Pydantic** | `IntakeOutput` 11 字段 schema | 自动（`intake_node` 出 `IntakeOutput` 即过）；手动复验见下 |
| **L2 cross_ref** | zone × material × schedule × surface 命名一致 | 自动（`cross_ref_foundations/complete` 出 `validation_errors`，看 `[node=cross_ref_*]` 行，errors=[]=过）|
| **InterZone 门** | 跨层配对图确定性几何校验 | 自动（EP 前 fail-fast，看日志 `InterZone surface-pair audit` + `pair_issues`）|
| **L3 OpenStudio**（人工）| zone 轮廓/外包/内墙匹配/窗位/楼板叠放 | 用户 OpenStudio 打开 `<case>/EP_run/temp_*.idf` 视察，填 `dimensions_check` |
| **L4 EP 仿真** | `EnergyPlus Completed Successfully` / 0 severe | `<case>/EP_run/eplusout.end` + `eplusout.err` |

L1 手动复验：
```bash
python -c "
import sys, json
sys.path.insert(0, '.')
from src.agent._share import ensure_schema_initialized; ensure_schema_initialized()
from src.agent.state import IntakeOutput
d = json.loads(open('test_data/SmallOffice_TwoStep/<case>/output/intake_output.json', encoding='utf-8').read())
io = IntakeOutput.model_validate(d); print('OK 11 fields; building=', io.building.name)
"
```

> **验收纪律**：`EnergyPlus Completed` **不是**几何正确的充分条件（EP 可在错几何上跑完、或在退化碎片上段错）。InterZone 门 + OpenStudio 视察才是几何把关。门 fail = 几何质量没过（phase2 主线问题），与"架构跑通"分开看。

---

## 七、Step 7 · 留痕到 `test_baseline/runs/`

跑完想存档：对会话说 `记录这次跑 <case> <tag>`，按 [test_baseline/README.md §4.3](../../test_data/test_baseline/README.md) 流程（`baseline_record.py` 起骨架 → 用户粘 `/context` → 助手填非用户字段 → 用户填 `dimensions_check`）。记录时**一并记 InterZone 门的 audit 计数**（总面/互逆对/issue 数）作几何质量信号。

非 baseline 的 capability 实验放 `runs/<YYYY-MM-DD>_capability_<topic>/`。

---

## 八、常见坑位清单

| 坑 | 表现 | 处理 |
|---|---|---|
| phase1 把杂物当结构 | 矢量 JSON 多出家具/铺装笔画 | Step 4.2 SVG 校验时抓；重绘排除进 `uncaptured_visual_elements` |
| phase1 同一道墙跨层估两个值 | 如 F1 隔墙 4.90、F2 4.95 | 5cm 抖动 → 下游切出退化碎片，InterZone 门抓。**根因质量主线**（见 capability 活文档），暂靠门挡 |
| phase2 跨层 split-pairing 写错 | InterZone 门报面积不符/不互逆/双重引用 | phase2 没按两层分区并集切天花/楼板。phase2/rules.md 缺口或 phase1 矢量抖动 |
| phase2 glazing 材料漏声明 | construction 跳过 `Default_Window` → 0 窗 → EP 段错 | rules.md Step 5 "material ↔ construction split" 已挡；新 case 复现则补 rules |
| `--phase1-from` 目录找不到 | `SystemExit: --phase1-from dir not found` | 确认 `<case>/phase1_vector/` 存在且有 `*.json` |
| `intake_phase2` 没配 key | `RuntimeError: intake_phase2 has no api_key` | `.env` 填 `DEEPSEEK_API_KEY` |
| 非深圳位置缺 EPW | `simulate` 找不到 weather | 备 `data/weather/<City>.epw`；默认 `--epw data/weather/Shenzhen.epw` |
| Step 5 中途崩溃续跑 | LangGraph `InMemorySaver` 进程退出丢 checkpoint | 重跑 Step 5（phase1 矢量已落盘，不重复识图）|

---

## 九、与 dev 模式 / Pivot 的关系

- **dev 模式**（主控 Agent 开子代理、临时指定模型）用于：phase2 跨模型对比、phase1 识图迭代、单节点调试。本指南是它的**正式化收口**——同一套 skill 规则 + 同一份 `phase2.py`，只是模型从临时指定改为 llm.yaml 固定、phase1 之后全自动。
- **质量主线**（识图→建模，[capability/recognition_modeling_capability.md](../capability/recognition_modeling_capability.md)）：phase1 忠实识图 + phase2 容差内重生成。当前 phase2 几何质量有波动（跨层配对），InterZone 门负责把"静默坏数据"变成"显式 issue"。质量提升按主线推进，不阻塞本流程跑通。
- **Pivot**（[reference/pivot_criteria.md](../reference/pivot_criteria.md)）：两步法天然分两个微调目标——phase1 =（图, 矢量 JSON）VLM 微调；phase2 =（矢量 JSON, IntakeOutput）纯文本微调。届时 phase1 接 `intake_phase1` 段走 vLLM，本流程 Step 4 也自动化。

---

---

## 附录 A · phase1 启动 prompt（粘进 Claude Code 会话）

> Step 4 用。仓库根新起多模态会话，把下面 `---` 之间整段作首条消息粘入，**按 case 改图名表**。规则真身在 [`skills/intake_pipeline/phase1/`](../../skills/intake_pipeline/phase1)，会话运行时读取，不必拷进 case 目录。

---

I am doing **phase 1 of the two-step intake: redraw the source image with semantic pens** — trace
every visible structural stroke on the architectural drawing by type (wall pen / window pen / wall_fill pen / ...),
and do **no spatial-topology reasoning** at all.

## Mental model

Phase 1 = "re-trace the source image with a set of semantically labeled pens". For example "the wall
pen drew a wall stroke from (0,0)→(15,0)", "the window pen drew a filled rectangle at elevation
(1.4, 1.0)→(3.8, 2.8)".

Phase 1 does **not**: enclose multiple wall strokes into "a room" / judge whether a wall is
"exterior or interior" / say "this window belongs to that wall" / write "the z_min/z_max of the
middle window on the south elevation F2". **All topology reasoning is left to phase 2.**

## Error budget (key, see guide.md §0.1)

Phase 1 sees the image, phase 2 does not. So:

- **perception errors can only be caught in phase 1**. Once phase 1 misreads a dimension, offsets a
  coordinate, flips the elevation x-axis, or misses a stroke, phase 2 cannot backtrack — it takes
  what it gets as truth
- **prefer null over guessing**. null = "I couldn't see it / it isn't dimensioned", which phase 2
  knows is missing. A guessed value is contamination
- EP zones are enclosed by surfaces (2D faces), **walls have no thickness** — plan walls'
  `thickness_m` is always `null`, do not estimate visual stroke width

## Your task

1. Read all three phase-1 skill docs (**required**):
   - `skills/intake_pipeline/phase1/guide.md` — flow / error budget / global constraints / output container / door-healing /
     facade_axis_note spec / self-check / downstream contract
   - `skills/intake_pipeline/phase1/reading_guide.md` — how to *recognize* each element across drawing styles (the
     convention cards + the semantic-category vocabulary)
   - `skills/intake_pipeline/phase1/pen_library.md` — what to *do* with each recognized category (which pen / keep-or-ignore /
     wall_fill convention)
2. Look at the worked example JSON (already hand-authored, e.g. the first plan view — **do not
   rewrite it**), and follow its style for the remaining images
3. Produce one JSON per remaining image, e.g.:

| source PNG | output JSON | image_kind |
|---|---|---|
| `2f_view.png` | `phase1_vector/2f_view.json` | plan |
| `3f_view.png` | `phase1_vector/3f_view.json` | plan |
| `South_view.png` | `phase1_vector/South_view.json` | elevation |
| `North_view.png` | `phase1_vector/North_view.json` | elevation |
| `East_view.png` | `phase1_vector/East_view.json` | elevation |
| `West_view.png` | `phase1_vector/West_view.json` | elevation |
| `supp_plan.png` | `phase1_vector/supp_plan.json` | decide yourself |

Read metadata from `testdata_prompt.json` — but only to learn the floor count / floor height / total
dimensions; **do not copy testdata_prompt content directly into the phase 1 JSON** (phase 1 should
reflect only what is seen in the image).

## Core discipline

1. **plan and elevation use different, minimal pen sets** (pen_library.md):
   - plan legal pens = `wall` / `window`
   - elevation legal pens = `wall_fill` / `window` / `outline`
   - there is **no `other` pen and no `door` pen**; stairs / columns / grids / furniture / decoration
     are recognized then logged in `uncaptured_visual_elements`, **not traced** (do not trace stair treads)
   - cross-use is an error. E.g. an elevation wall body must use `wall_fill`, not `wall`
2'. **Heal door openings into continuous walls (door-healing, guide.md §2.1)**: when you see a door
   leaf / arc on a plan, do not draw a door pen — heal the walls on its two sides into **one
   continuous wall stroke** + a note `healed door opening at <position>` (a door is ignored in EP, a
   wall is a continuous boundary face). Guardrails: only heal openings carrying a door symbol;
   doorless large open spans are kept, not welded (those are real topology signals); windows are not
   healed. Record each heal in `uncaptured_visual_elements`
2. **Split elevation wall bodies as "one wall_fill stroke per floor"** (pen_library.md §3). For a 3-story
   building, each elevation produces 3 wall_fills. Even if the gray looks visually continuous, split
   by the dimension chain's per-floor z ranges
3. **Topology is not phase 1's job.** Forbidden fields: `is_exterior` / `parent_wall_id` / `rooms[]`
   / any "X belongs to Y / X faces outside / X encloses" semantics
4. **Do not expand the pen set, and do not trace non-keep marks.** Columns / beams / decorative lines /
   index arrows / grid lines / stair treads are **recognized then logged in `uncaptured_visual_elements`**,
   not traced as strokes; do not invent enum values like `cornice` / `column` / `level_line` and do
   not fall back to an `other` pen (there is none)
4'. **`uncaptured_visual_elements` is required**: anything "seen but not drawn into strokes" must be
   acknowledged — out-of-dictionary strokes + clutter actively excluded by selective extraction
   (furniture / paving / texture / room text boxes) + healed doors. Even when the dictionary is truly
   enough, write a note rather than leaving it empty ("acknowledged skip" ≠ "silent loss")
5. **One stroke per continuous stroke.** E.g. the south perimeter wall from (0,0) to (15,0) is **one**
   wall stroke, do not split into 3. Door openings do not break a wall (heal into a continuous wall,
   see 2'); a window on a plan is a sub-face and also does not break a wall
6. **Fill null when not found**, no defaults. Plan walls' `thickness_m` is always null (simulation
   doesn't use it, guide.md §0.2); other fields not found in the image are also null
7. **Elevation facade_axis_note must include the sign** (guide.md §4 four-facade table)
8. **OCR verbatim**; if there are no text labels, leave ocr_texts as an empty array

## Workflow

1. Read guide.md + reading_guide.md + pen_library.md + the worked-example plan JSON (understand the style)
2. Do one pilot first (e.g. `2f_view.png`), then stop and let me review — **do not batch all images at once**
3. After I approve the pilot, batch the rest (other plans + elevations + supplemental plan)
4. When all are done, write a `phase1_vector/phase1_summary.md`:
   - per-image confidence self-assessment (high/medium/low, with reasons)
   - which fields were repeatedly null / unknown
   - the four-facade x_local ↔ world-axis table (actual filled values)
   - your feedback on the schema: where it falls short / where it is redundant / which pen enum values are insufficient

## Boundaries

- Do not modify any file under [../../src](../../src), [../../skills](../../skills), [..](..)
- Do not modify the worked-example JSON (it is the reference)
- Do not run `run_full_pipeline.py` or any EnergyPlus tool
- Do not produce IntakeOutput fields (zone_specs / surface_specs / fenestration_specs / ...), that is all phase 2's job

When ready, do the pilot first, then stop and wait for my feedback.

---

完工后人工校验：用 [Tool_scripts/render_vector_to_svg.py](../../Tool_scripts/render_vector_to_svg.py) / [render_vector_to_png.py](../../Tool_scripts/render_vector_to_png.py) 渲图肉眼比对（见 Step 4.2）。

---

## 附录 B · phase2 会话手跑 prompt（可选，跨模型对比用）

> 正式流程 phase2 由 Step 5 `--phase1-from` 自动跑（DeepSeek，`intake_phase2` 段）。本附录仅当你想用**会话**手跑 phase2（如换模型对比、或脚本不可用时）才用。产 `phase2_intake/<model>/intake_output.json` 后，可走 `--intake-from` 喂下游。

---

I am doing phase 2 of the two-step intake. Phase 1 (image → vector JSON) is done (products in
`phase1_vector/`). This session does only **phase 2: vector JSON → IntakeOutput** — no image,
pure text reasoning.

## Required reading

Read in order:

1. `skills/intake_pipeline/phase2/rules.md` — full phase 2 rules (input/output / coordinate translation formulas /
   IntakeOutput field derivation order / naming rules / vertex synthesis / self-check)
2. `skills/intake_pipeline/phase1/guide.md` + `skills/intake_pipeline/phase1/pen_library.md` — phase 1 output format reference (only to understand what your input looks like; phase 2 does not need the reading guide)
3. `phase1_vector/phase1_summary.md` — phase 1 summary (includes the 4-facade local↔world translation formulas, **apply directly**)
4. **every** phase 1 vector JSON under `phase1_vector/` (do not assume a fixed file set):
   - all floor-plan JSONs (`<N>f_view.json`) and all facade-elevation JSONs (`<Name>_view.json`)
   - any supplementary / section JSONs if present (e.g. `supp_plan.json`) — read them too
   - do not assume 3 floors or 4 facades; enumerate what actually exists
5. `testdata_prompt.json` — metadata (floor count, area, city, use)

## Task

Following the field derivation order in `rules.md` §3, produce the IntakeOutput Pydantic JSON, written to:

```
phase2_intake/<model>/intake_output.json
```

For the format, reference the IntakeOutput Pydantic definition in [../../src/agent/state.py](../../src/agent/state.py).
All 11 fields must be present: building / site_location / zone_specs / material_specs /
schedule_specs / construction_specs / surface_specs / fenestration_specs / hvac_specs / people_specs
/ lights_specs.

The 9 `*_specs` fields are **natural-language instructions** (not structured data), but must be
explicit, mechanically executable, and internally consistent — the 9 downstream subagents rely on
these strings. Naming rules are strict (letters/digits/`_` only, literally consistent across fields,
no template writing).

## Mental model

- You have already "seen the image" — all visual info is in the phase 1 JSON. **Do not go back to the original PNG**
- Any error tied to "a value in the image" is phase 1's fault (already frozen); you can only
  introduce pure reasoning errors (topology, naming, field format, coordinate translation)
- A `null` in the phase 1 JSON = "phase 1 didn't see it", **do not treat it as 0**; if missing,
  annotate accordingly in your output
- Elevation local coordinates must be translated back to the world system per the `phase1_summary.md`
  §3 formula, **do not re-derive**

## Workflow

1. Read the required docs (rules / schema / summary / testdata_prompt + sample a few JSONs)
2. Walk through phase2_rules §3 Step 1→7 mentally, confirm you are confident before writing
3. Write `phase2_intake/<model>/intake_output.json` — write it all at once, **do not append in multiple passes**
4. After writing, run the self-check (phase2_rules §7, 9 items) and write the result to `phase2_intake/<model>/self_check.md`
5. If phase2_rules does not cover something and you had to "improvise" to finish, record it in
   `phase2_intake/<model>/phase2_followup_notes.md` so the rules can be extended later

## Boundaries

- Do not modify any phase1_vector/ file (phase 1 products are frozen)
- Do not modify rules.md / phase1/guide.md / phase1/pen_library.md (put suggestions in phase2_followup_notes.md)
- Do not modify any file under [../../src](../../src) / [../../skills](../../skills) / [..](..)
- Do not run `run_full_pipeline.py` or any EnergyPlus tool
- Do not look at the original PNGs (phase 2 discipline)

When done, output three files: `intake_output.json` / `self_check.md` / `phase2_followup_notes.md` (if any).

---

_2026-05-29 — 正式化为两步法新架构完整版：Step 4 改 phase1 半人工识图（产矢量 JSON）；Step 5 改一次性自动（phase2 + 下游 + EP，模型统一 llm.yaml `intake_phase2`/`default`/flash）；Step 6 加 InterZone 几何门验收层；明确 dev 临时模式 vs 正式一次性模式的边界。phase1/phase2 prompt 模板并入附录 A/B（原 new_case_guide_twostep.md 已删）。配套 B1.5.c（intake_node 两步串行）+ InterZone 门（src/validator/interzone.py）。旧单步法版本备份 logs/backup/new_case_guide.md.bak_2026-05-29。_
