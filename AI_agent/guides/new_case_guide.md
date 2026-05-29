# 新建测试样例操作指南 —— 两步法新架构正式版（2026-05-29）

> 面向新增一个 SmallOffice 测试案例的**标准完整流程**（正式测试用）。
>
> **两条使用模式，先分清**：
> - **平时 dev 测试**：直接指定各阶段模型，让主控 Agent 开子代理跑（如 phase1 用一个子会话、phase2 换不同模型对比）。灵活、临时，**不走本指南**。
> - **正式测试（本指南）**：完整端到端。**除 phase1 目前半人工喂矢量外，phase2 + 9 个下游 subagent + EnergyPlus 全自动一次性跑完**。每次测试用**一份 per-case 模型配置**(`<case>/llm.yaml`,从全局拷贝当默认、自己改),方便快速切模型组合;全局 [`src/configs/llm.yaml`](../../src/configs/llm.yaml) 作兜底。详见 §5.1。
>
> **架构**：两步法 intake（[architecture/architecture.md](../architecture/architecture.md)）。phase1 = 图 → 语义矢量 JSON（看图、只识不推）；phase2 = 矢量 JSON → `IntakeOutput`（不看图、纯拓扑推理）。两步分离 = **误差预算分离**（识图错归 phase1，推理错归 phase2）。规则真身在 [`skills/energyplus_mcp_twostep/`](../../skills/energyplus_mcp_twostep)。
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

目录约定：
- 源图（`*_view.png`）放 `<case>/` 根
- phase1 矢量产物放 `<case>/phase1_vector/`
- phase2 + 下游 + EP 产物放 `<case>/output/`（或 `--output-subdir` 指定的子目录）

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
2. 把 [`new_case_guide_twostep.md` §一的 phase1 启动 prompt](new_case_guide_twostep.md) 整段贴入，按 case 改图名表。规则真身在 [`skills/energyplus_mcp_twostep/phase1/`](../../skills/energyplus_mcp_twostep/phase1)（`guide.md` 流程/误差预算/输出容器 + `reading_guide.md` 跨画法识别 + `pen_library.md` 笔库），会话运行时读取。
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
3. `intake_node` 跑 **phase2**（[`src/agent/phase2.py`](../../src/agent/phase2.py)，DeepSeek raw client + thinking，读 `intake_phase2` 段）→ 产 `IntakeOutput`，落 `<case>/output/intake_output.json`，phase2 调试产物落 `<case>/output/phase2_intake/`
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
| **L3 OpenStudio**（人工）| zone 轮廓/外包/内墙匹配/窗位/楼板叠放 | 用户 OpenStudio 打开 `<case>/output/temp_*.idf` 视察，填 `dimensions_check` |
| **L4 EP 仿真** | `EnergyPlus Completed Successfully` / 0 severe | `<case>/output/eplusout.end` + `eplusout.err` |

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

_2026-05-29 — 正式化为两步法新架构完整版：Step 4 改 phase1 半人工识图（产矢量 JSON）；Step 5 改一次性自动（phase2 + 下游 + EP，模型统一 llm.yaml `intake_phase2`/`default`/flash）；Step 6 加 InterZone 几何门验收层；明确 dev 临时模式 vs 正式一次性模式的边界。配套 B1.5.c（intake_node 两步串行）+ InterZone 门（src/validator/interzone.py）。旧单步法版本备份 logs/backup/new_case_guide.md.bak_2026-05-29。_
