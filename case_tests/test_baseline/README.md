# test_baseline — 规范 baseline（2026-06-16 重构）

> **新方案（2026-06-16）**：baseline 不再是 `runs/` 里粘 `/context` 的人工档案，而是
> **自包含在 anchor case 内的、Agent 编排跑出的、带反馈带记录的金标准**。本目录只留
> **方案说明 + baseline 注册表**；具体怎么跑由主 Agent（编排器 + judge②）执行，操作手册见
> [guides/new_case_guide.md](../../AI_agent/guides/new_case_guide.md)。
>
> **旧 `runs/`（2026-04~05 的 9 个人工档案）已整体挪到**
> [`backup/tests_history/test_baseline_runs/`](../../backup/tests_history/test_baseline_runs)
> （gitignored 本地归档，不再维护）。

---

## 0. ⭐ 本批（C2）素材的**图纸标注约定** —— 明文前提（2026-08-11 用户定）

> **C2 批的 case 图纸一律使用同一种标注法：**
> **① 外墙 —— 总尺寸标到【外皮】，外轮廓即按外包画成边界；**
> **② 内墙 —— 标【轴线】（中线）。**

**这是一条关于【输入素材】的前提，不是管线的输出选项。** 写在这里的目的：

- 今天管线**并没有显式声明**这件事 —— 确定性核是把外轮廓**吸到图纸的总标注上**，
  于是"外轮廓落在外皮"是**图纸标注习惯带来的结果**，不是我们声明的规则
  （唯一接近声明的是 `ENVELOPE_RECONCILE_TOL = 0.30` 那行注释，它假设总标注量到外皮，
  而该假设此前无处声明、无处校验）。
- ⚠️ **换一张按轴线标总尺寸的图，同一套机器会把外轮廓吸到轴线框上，且生产链不会报任何警**
  （位移 0.12 < 0.30 容差），EnergyPlus 照样 0 Severe、判卷照样绿，
  **只是全楼面积差约 4.8%**（外皮 120 m² vs 轴线 114.5 m²）。
- **判别观测量已存在于产物中**：`1_correction` 的 `corrections[]` 里
  `rule_id = deterministic_core.envelope_atomic_transform` 的 `intents`，逐侧记着 `old_value → new_value`。
  **每侧位移 ≈ 半个墙厚 ⇒ 按外包标注（本批）· ≈ 0 ⇒ 按轴线标注。**

**⇒ 因此：新增 C2 素材时必须确认它符合上面这条约定；不符合的图先别进 C2 批。**
这条前提将在「标注 / 墙厚 / 出模」专项中被正式化为**结构化声明**（届时是升级，不是推翻）——
专项材料与用户定的三层分工见 [AI_agent/plan.md](../../AI_agent/plan.md) 的「〇-B / 〇-C」两节。

---

## 1. 一个 baseline anchor 长什么样

**golden 是 run 级、不是 case 级**（2026-06-23 用户定）：golden = **(case 素材 × 一种模型配置 × 流程稳定跑出的稳定结果)** 的那**一次 run**（`<case>/run_<注释>/`）。同一 case 在不同模型配置下是不同 golden 候选；一次 run 只有在**流程稳定 + 结果可复现**时才挣得 golden，不是随便一跑就算。**case = 纯素材**
（`case_data/`，改素材才新 case）；每次跑 = 自包含 run（单 case 可多轮）。run 内**自带**全部反馈与记录：
（注：早于稳定 step-orchestrated 流程的老 run 无编排账本、REPORT 的 run_state 会显 `incomplete`，那些不是真 golden、不必管；真 golden 走稳定流程跑出、天然 `completed_clean`。）

```
<case>/
  case_data/                  ← THE case（源素材 *_view.png + testdata_prompt.json）
  run_<注释>/                  ← 一次 run（自包含；多轮 = 多个 run_ 文件夹）
    llm.yaml                  本 run 模型组合（= 记录的一部分）
    0_reading/                本 run 识图矢量 + *_render.png + reading_summary.md
    1_correction/ … 5_intakeoutput/
      <stage 产物>
      <stage>_checks.json     ← gate① 确定性反馈（每条 check pass/flag/block + evidence）
      attempts/NNN/           ← append-only 每次抽：output + checks + judge（不覆盖坏草稿）
    2_modelling/building_geometry.json + kernel_gate_report.json
    EP/EP_run/                EP 仿真（eplusout.* 本地 gitignored）
    _run/
      run_manifest.json       各段 accepted 指针 + input hash + geometry approval digest
      validation_manifest.json validate_case summary（非 M0 audit manifest）
      geometry_approval.json  geometry digest approval（如有）
      orchestration_state.json judge-in-the-loop ledger（如有）
      baseline.json           ← 机器成绩单（golden 计数 / digest / gate 汇总 / flags / EP / 抽几次）
    report/
      REPORT.md               ← 唯一人读总反馈（GEN 事实区 + AGENT 叙事/建议 + 🔍 肉检索引）
      eyeball/                ← 汇拢的 2D 肉检件
```

**「干净」收口标准**：gate① **0 block** + EP **0 severe**；cross-check **flag 允许存在但必须在
`_run/baseline.json.flags[]` 与 `report/REPORT.md` 的 GEN 区留痕**。出现不该有的 flag（区数 tripwire、跨图对账不齐
等）→ 回 0_reading 修到干净，不带病入库。

## 2. 三层反馈（来源）

| 层 | 谁产 | 落处 |
|---|---|---|
| **gate① 确定性** | 代码 [`validate_case`](../../src/agent/execution/validation_run.py) | `<stage>_checks.json` + `_run/baseline.json.gates` |
| **judge② 感知** | **主 Agent（编排器自己当 judge，看原图+渲染件+参考）** | `attempts/NNN/judge.json`（verdict schema v2，append-only）|
| **L-肉眼** | **人**（按 `report/REPORT.md` 的 🔍 清单核确定性/judge 都盖不死的感知项）| 人工 |

判据：致命/严重 → **盲重抽**（≤3，超则 quarantine 交人）；轻微 → flag 放行。**judge 评语只进记录、
绝不回灌阶段 prompt**（不污染输入，见手册「不污染原则」）。

> **judge② 的「参考」= gt 评测答案**（[gt/README.md](gt/README.md)）：逐 case bundle `gt/<case>/gt.json`，
> **只 gate② judge / 人 可读**，gate①/执行器绝不 import（铁律，`tests/test_gt_discipline.py` 守）。
> gt 由人读原图得出、故意不含窗 along-facade x；**CAD→gt 满配答案方向**（精确窗 x+宽+区划+门）见
> [proposals/cad_to_gt_extraction_plan.md](../../AI_agent/proposals/cad_to_gt_extraction_plan.md)。
> 人/judge 对照 gt 用 `scripts/tool_scripts/render_gt.py` 出带尺寸标注的平面图+立面图（核布局意图、不核 mm）。

## 3. 生成 / 记录

跑批与 judge 由主 Agent 按 [new_case_guide.md](../../AI_agent/guides/new_case_guide.md) 执行；
跑完用 [`scripts/tool_scripts/record_baseline.py`](../../scripts/tool_scripts/record_baseline.py)
生成 `_run/baseline.json` + `report/REPORT.md`：

```bash
python scripts/tool_scripts/record_baseline.py <case> <run> \
    --base-dir case_tests/e2e_tests --date 2026-06-16 --orchestrator opus-4.8
```

每个 anchor baseline 配一条 golden 测试（断言 `blocked=False` + golden 计数 + EP 干净），见
`tests/test_validation_run_baseline.py`。

## 4. baseline 注册表

见 [index.md](index.md)。

## 5. capability 实验（非 baseline）

跨模型对比、单点能力试验等**非 baseline** 的临时跑，仍走 dev 模式（主 Agent 临时指定模型、子 Agent
跑），产物按需归档，不要求自包含成绩单。
