# 新建测试样例操作指南 —— 两步法 Step 4（临时版）

> **临时文档**。当前主线 [new_case_guide.md](new_case_guide.md) 的 Step 4 仍是单步法（半人工 intake）。本文件只覆盖**两步法的 Step 4**（拆 4a phase1 / 4b phase2），用模板临时驱动，方便 B1.5.a 异图 POC v2 期间跑两步法。
>
> **定位**：Step 1–3（备素材 / 建目录 / 写 testdata_prompt.json）与 Step 5–7（下游自动跑 / 验收 / 留痕）**完全复用 [new_case_guide.md](new_case_guide.md)**，本文件只替换中间的 Step 4。
>
> **何时退役**：POC v2 通过、按 [plan.md B1.5.c/e](plan.md) 把 `intake_node` 改成两步串行 + 正式重写 new_case_guide.md 后，本临时文件并入主指南删除。决策背景见 [floorplan_redraw_strategy.md §10](floorplan_redraw_strategy.md)。

---

## 零、与单步法的差异

| 阶段 | 单步法（new_case_guide.md）| 两步法（本文件）|
|---|---|---|
| Step 1–3 | 备素材 / 建目录 / testdata_prompt.json | **完全一致** |
| Step 4 | 一个会话：图 + 文本 → `intake_output.json` | **拆两步**：4a 识图→矢量 JSON；4b 矢量 JSON→`intake_output.json` |
| 规则库 | [skills/energyplus_mcp/](../skills/energyplus_mcp/)（单步法，中文）| [skills/energyplus_mcp_twostep/](../skills/energyplus_mcp_twostep/)（两步法，英文）|
| Step 5–7 | 下游自动跑 + L1–L4 + 留痕 | **完全一致**（下游入口见 §三）|

**案例目录**：两步法语料放 [test_data/SmallOffice_TwoStep/](../test_data/SmallOffice_TwoStep/)`<case>/`（与单步法 `SmallOffice/` 并列）。phase1/phase2 全部中间产物落这里。

误差预算（两步法的核心）：phase1 看图、只产「图上看到了什么」；phase2 不看图、只对矢量 JSON 做拓扑推理。任何图相关的错只能在 phase1 截断，phase2 只引入纯推理错。详见 [phase1_guide.md §0.1](../skills/energyplus_mcp_twostep/phase1/guide.md)。

---

## 一、Step 4a · phase1 识图（图 → 矢量 JSON）

> **目标**：每张图（逐层平面 + 各立面 + 补充图）→ 一份矢量 JSON（语义笔 strokes + 尺寸链 + OCR），外加一份 `phase1_summary.md`（含 4 立面 local↔world 翻译公式）。**只识图、不做拓扑**。

1. 在仓库根新起一个独立 Claude Code 会话，选多模态强模型（Opus 4.7）。
2. 把 [skills/energyplus_mcp_twostep/phase1/prompt_template.md](../skills/energyplus_mcp_twostep/phase1/prompt_template.md) 里 `---` 之间整段作为首条消息粘进去，并**按本 case 改路径**（模板里的图名表 / 目录）。
3. 会话会先做一张 pilot（如 `2f_view`），停下等你审；审 OK 后再 batch 其余图。
4. 人工校验：用 [Tool_scripts/render_vector_to_svg.py](../Tool_scripts/render_vector_to_svg.py) 把矢量 JSON 渲成 SVG，肉眼比对原图，重点看：
   - 杂物（家具/铺装/纹理）有没有被误当 wall/window（假阳性，最致命）
   - 真墙/真窗有没有漏（假阴性）
   - 门洞有没有按 v1.3 规则 heal 成连续墙（带门符号才补、留痕）
   - `uncaptured_visual_elements` 是否如实登记了「看到但没画」的

**产物**：`<case>/phase1_vector/{1f_view,2f_view,...,South_view,...}.json` + `<case>/phase1_vector/phase1_summary.md`。

---

## 二、Step 4b · phase2 拓扑（矢量 JSON → IntakeOutput）

> **目标**：读 phase1 矢量 JSON + testdata_prompt.json，按 [phase2_rules.md](../skills/energyplus_mcp_twostep/phase2/rules.md) 推出 11 字段 `IntakeOutput`。**不看原图**。

两条路径，任选：

### 路径 A — 会话（Opus 等）

新起会话，把 [skills/energyplus_mcp_twostep/phase2/prompt_template.md](../skills/energyplus_mcp_twostep/phase2/prompt_template.md) 改好路径后整段粘入。产 `intake_output.json` + `self_check.md` + （如有）`phase2_followup_notes.md`。

### 路径 B — DeepSeek 自动跑

```bash
python Tool_scripts/run_phase2_deepseek.py --case test_data/SmallOffice_TwoStep/<case>
```

phase1 矢量 JSON 现在**按目录自动扫描**（`phase1_vector/*_view.json`，平面 `<N>f_view` 在前、立面在后），楼层/立面数不同的 case 无需再改脚本。

**产物**：`<case>/phase2_intake/<model>/intake_output.json`（或你约定的位置）。

### L1 校验（同 new_case_guide.md §4.4）

```bash
python -c "
import sys, json
sys.path.insert(0, '.')
from src.agent._share import ensure_schema_initialized
ensure_schema_initialized()
from src.agent.state import IntakeOutput
data = json.loads(open('<path>/intake_output.json', encoding='utf-8').read())
IntakeOutput.model_validate(data); print('OK 11 fields')
"
```

通过 = 可进 Step 5；Pydantic 报错 = 回 4b 让模型改 JSON 重存。

---

## 三、接 Step 5（下游自动跑）

> Step 5–7 流程与 [new_case_guide.md §五–§七](new_case_guide.md) 完全一致（含 `跑下游 <case>` 对话触发、L1–L4 验收、`记录这次跑` 留痕）。

[scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 现有 `--base-dir`，两步法 case 直接指向 `SmallOffice_TwoStep/`，不必再往 `SmallOffice/` 搬：

```bash
# 先把 phase2 产出的 intake_output.json 放到 <case>/output/ 下（--intake-from 相对 <case>/ 解析）
python scripts/run_full_pipeline.py <case> \
  --base-dir test_data/SmallOffice_TwoStep \
  --intake-from output/intake_output.json
```

> 正式两步法主线（B1.5.c）会把 `intake_node` 改成 phase1+phase2 串行调用，连 `--intake-from` 手工搬运一并消失。

---

## 四、与正式版的关系

- 本文件是 POC v2 期间的**操作脚手架**，规则真身在 [skills/energyplus_mcp_twostep/](../skills/energyplus_mcp_twostep/)（英文、纯当前版本 spec）。
- POC v2（[plan.md B1.5.a](plan.md)）通过 → 按 [plan.md B1.5.c/e](plan.md) 把两步法切成 `intake_node` 运行时串行调用 + 把 Step 4 两步正式写进 [new_case_guide.md](new_case_guide.md)（拆 4a/4b、改引用到 twostep 库、去掉 §三 的目录接缝）→ 删除本临时文件。
