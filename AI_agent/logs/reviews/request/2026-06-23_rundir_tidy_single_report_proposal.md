# Run 目录收拾 + 单一 REPORT.md（提案）

Date: 2026-06-23
Branch: `6.15_ValidationArchM0toM4`
Status: 提案，待 Codex 审 → 用户裁决 → 派执行
前置: 承接 `6.23_ReportOrgCuratedFolder`（report/ 策展文件夹已落地）的两条用户追加诉求。
用户决策（2026-06-23）:
1. 根级机器记账收进 **`_run/`** 子文件夹（根目录只剩文件夹 + llm.yaml）。
2. **llm.yaml 留根目录**（输入配置旋钮，好发现好改）；但 **REPORT 最前要汇报本次模型配置**。
3. **汇报给用户 = 单一一个 `REPORT.md`**（只开这一个）；可加索引/链接（eyeball 图、drill-down），但报告本身是一个文件 → **合并掉当前的 FACTS.md + REPORT.md 双文件**。

---

## 0. 目标终态

```
<run>/
  report/
    REPORT.md          ← ★唯一人读文件（生成事实区 + 主控叙事区 + 四桶建议 + eyeball 索引）
    eyeball/           ← 2D 肉检图（REPORT 里链接/索引）
  0_reading/ … 5_intakeoutput/ EP/ manual_review/ verdicts/   ← 阶段产物（不动）
  _run/                ← 机器记账（orchestration_state/baseline/run_manifest/validation_manifest/geometry_approval）
  llm.yaml             ← 配置（留根）
```
根目录视觉=纯文件夹 + 一个 llm.yaml。用户只开 `report/REPORT.md`。

---

## 1. 两块改动

### A. 机器记账迁 `_run/`
迁移这 5 个**生成的承重件**到 `<run>/_run/`：`orchestration_state.json`、`baseline.json`、`run_manifest.json`、`validation_manifest.json`、`geometry_approval.json`。**llm.yaml 不动**（输入配置）。阶段产物文件夹（0–5/EP/manual_review/verdicts）不动。

引用面（grep 实测，全在本仓、可集中改）：
- `orchestration_state.json`：走 `step_orchestrator.STATE_NAME` 常量（3 文件，**改 1 处常量 + 确保都经常量**）。
- `baseline.json`：5 文件（record_baseline 写 + 测试读）。
- `run_manifest.json`：3 文件；`validation_manifest.json`：2 文件；`geometry_approval.json`：1 文件（approval.py）。
- 统一做法：定义 `RUN_META_DIR = "_run"`，所有读写 `run_dir / RUN_META_DIR / <name>`；validate_case/approval/record_baseline/manifest/report_assembly 全改经它。
- golden baseline + 两个 committed run（gpt54/sonnet）物理 `git mv` 进 `_run/`。

### B. 单一 REPORT.md（合并 FACTS，marker 围栏合并）
- **删 FACTS.md 作独立人读文件**；其确定性内容**折叠进 REPORT.md 的生成区**。`baseline.json`（机器成绩单 + evidence_index）留作机器源（在 `_run/`）。
- REPORT.md 结构（生成区 G / 主控区 A，marker 分隔）：
  1. **G — 标题 + 一句话状态**（run_state TLDR）
  2. **G — 本次模型配置**（读 llm.yaml，置顶，用户诉求）
  3. **A — 一句话结论 / 本轮侧重点**（AGENT-FILL）
  4. **G — 事实卡**（verdict / gate① 表 / run_state 详情 / corrections 审计摘要）
  5. **A — 错在哪儿 + 归因**（AGENT-FILL）
  6. **G — 肉视检验索引**（eyeball/ 图链接 + 3D viewer manual_review 指针）
  7. **A — 建议四桶**（机制/能力/脚手架/修法；mini-format + citation）
  8. **G — 附录指针 + evidence_index 摘要**（链接 _run/ drill-down）
- **marker 围栏合并**（取代 create-if-absent，落 D5 当初跳过的选项）：
  - 生成区用 `<!-- GEN:START k --> … <!-- GEN:END k -->` 包裹，每次 record_baseline **重渲刷新**。
  - 主控区用 `<!-- AGENT:START k --> … <!-- AGENT:END k -->` 包裹，record_baseline **原样保留**（首次或缺失区块用 sentinel/AGENT-FILL 占位）。
  - 重跑：解析现有 REPORT.md → 抽出 AGENT 区内容 → 重渲 GEN 区 → 回填保留的 AGENT 区 → 写回。AGENT 区为空/缺失则用骨架占位。
  - **诚实分离仍守**：GEN 区代码写（数字唯一权威）、AGENT 区主控写、citation linter 只查 AGENT 建议区引用 vs `baseline.json.evidence_index`。

---

## 2. 待 Codex 审的点（review-asks）

- **R1 marker 合并的健壮性**：解析失败/marker 被主控误删/区块重复/嵌套 怎么兜底？建议：marker 缺失→视为该 AGENT 区为空用占位、不报错；GEN marker 缺失→整体回退重建（warn）。是否够？
- **R2 `_run/` 迁移有无遗漏的固定路径读者**（除 grep 出的 6 类）？尤其下游 run_full_pipeline / cross_ref / 任何按 `run_dir/baseline.json` 等硬路径的脚本。
- **R3 llm.yaml 留根 + 模型配置置顶**：record_baseline 已有 `_models_from_llm_yaml`，直接复用渲进 REPORT 顶部 G 区即可，无新读取面。确认。
- **R4 golden/测试迁移**：`baseline.json` 路径变 `_run/baseline.json` → test_orchestrate_baseline 等断言路径全改；REPORT.md 单文件后，FACTS.md 相关断言删/改。blast 比 report-org 略小但集中在测试路径。
- **R5 是否保留 REPORT.template.md**？单文件 + marker 合并后，template 可内联进渲染、不必单独落盘；倾向删 template 文件。

---

## 3. 影响面 / 风险

- 不碰几何/契约/baseline **数值**（只挪 baseline.json 的**位置** + 加 evidence_index 已在上个 PR）。
- 改动：新 `RUN_META_DIR` 常量 + 各读写点（~12 文件）、report_assembly 的 write_report_files 改 marker 合并、render template 折叠进 REPORT、record_baseline 接线、测试路径迁移、golden + 2 committed run `git mv`、docs（new_case_guide/contracts 布局图）。
- 一轮 Codex 审足够（机械迁移 + 一个 subtle 点=marker 合并），非五审级。
- 与命名确定性化解耦。

---

## 4. v2 修订（2026-06-23，采纳 Codex 审 APPROVE-WITH-CHANGES 6 findings 全部）

verdict=APPROVE-WITH-CHANGES（0 BLOCKER / 3 DISAGREE / 3 NIT，落 `logs/review/review/2026-06-23_rundir_tidy_single_report_review.md`）。Claude 裁决全采纳。Codex Verified Notes 确认安全面：STATE_NAME 已集中、geometry_approval 迁移对 digest-bound 检查安全（digest 仍绑 building_geometry/geometry_specs/kernel report，**这三个不动**）、FACTS.md 无运行时解析依赖、`_run/` 不被 .gitignore、无下游 run_full_pipeline/graph/cross_ref 消费者。

### F1（DISAGREE 1）一个共享 `run_meta_path` helper，覆盖 manifest filename override
不能只改 STATE_NAME 常量。`RunManifest.load/save`(manifest.py:124,130) 直接 join run 根、`validate_case(write_reports=True)` 经同一 save override 写 validation summary(validation_run.py:241)、approval/state 也直接 join 根(step_orchestrator.py:497,524；approval.py:67,73)。
- 加 `RUN_META_DIR = "_run"` + `run_meta_path(run_dir, name)`（写时建父目录）。
- 路由：`RunManifest.load/save`(含 `filename=` override)、`GeometryApproval.load/save`、`load_state/update_state/mark_geometry_approved`、`record_baseline`、report 链接/source 全经它。
- 测：`RunManifest.save(run_dir)`→`_run/run_manifest.json`、`save(...,filename="validation_manifest.json")`→`_run/validation_manifest.json`、validation 不再建/写根 `run_manifest.json`、`_run/` 存在时不读根遗留。

### F2（DISAGREE 2）marker 合并 fail-closed
- 只解析**整行精确 marker**、对**固定预期 AGENT 键集**。
- 缺失 AGENT 键 → sentinel/占位 + warn（不报错）。
- **重复/嵌套/反序/未闭合 AGENT marker → 写前 abort**（或写明确命名的 recovery copy 后 fail），绝不静默尽力保留。
- 回归测试：首跑 / 重跑保留 / 二次重跑幂等 / 删 marker→占位 / 重复 marker→失败 / 嵌套→失败 / GEN 载荷内含类 marker 文本不误伤。

### F3（DISAGREE 3）linter 只 lint 抽出的 AGENT 建议区
- marker 解析后，**只把 `AGENT:recommendations` 区内容**喂 `lint_report_citations`（或让 linter 收已抽好的 section），不再扫整 merged markdown 找 `## 建议`。
- GEN 刷新后 AGENT 引用的 evidence id 变陈旧 → **失败**（正确的失效行为），报错**点名陈旧 id + 所在 AGENT 块**，不静默丢/改写主控 prose。

### F4（NIT 4）措辞：可审的写权属分离，非"airtight"
- GEN 区代码写 / AGENT 区主控写 = 防意外覆盖 + 可审，但**不**证明 AGENT 结论/归因散文与 GEN 数字语义一致。
- 文档明确 `baseline.json` / GEN 块为**数字唯一权威**；linter 只 ground 可执行建议、不号称证明全部散文一致。

### F5（NIT 5）迁移清单 = 所有测试/注册表触及的 run，单契约
- 真实 golden anchor：`sm20_anchor/run_2026-06-15_baseline` + `sm21_anchor/run_2026-06-16_opus_e2e`（注册表 index.md:8,9；`test_validation_run_baseline.py:191,199` 断言 sm21 opus run）；加上有 report/ 的 gpt54/sonnet run。
- **迁所有测试触及的 run** 到 `_run/` 布局（`git mv` baseline.json/manifests/geometry_approval/orchestration_state）+ 改全部测试路径断言。**单契约、不搞 read-_run-else-root 双布局**（避免脏代码）。非测试的历史 run（sonnet_retry 等）一并迁保持一致或标历史。

### F6（NIT 6）顺手修 llm.yaml 文档措辞
- `new_case_guide.md:216` 仍写 `<case>/llm.yaml`，run record 实为 `<run>/llm.yaml`（record_baseline.py:38,292 读 `run_dir/llm.yaml`）→ guide/contracts 统一改 `<run>/llm.yaml`；**`run_full_pipeline.py` 的 legacy per-case 配置行为不动**（本 PR 不改 runner）。
