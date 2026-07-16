# B4a Phase B 施工派发（terra 执行档，2026-07-15）

**任务**：按 [AI_agent/proposals/c2_b4a_detail_spec.md](../../proposals/c2_b4a_detail_spec.md) **v2 定稿**施工 **Phase B（inspector、manifest、plan polygonize）**。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase B**（稿 §13 Phase B 行），Phase C/D 后续单独派工。Phase A 已 CLOSED 收录（`25d3946`）。

## Phase B 范围（稿 §13 + 对应章节）

- **重写/扩展 `scripts/tool_scripts/inspect_dxf.py`**（§9 v3 preflight：只读 inspect + manifest preflight；无自动真值推断；inspection 无 manifest 只能 UNBOUND）；
- **新增 `src/agent/judge/gt_extraction.py`** 的 plan 侧提取核（§10 中 Phase B 界内部分：单位/view region/snap/polygonize/zone 分割；唯一 DXF I/O 在边缘函数；可复用 Vg 公开纯几何 API 与 `correction.footprint.footprint_fingerprint`，correction 不得反向 import judge）；
- 产出 = 内部 strict **`PlanExtractionResult`**（floors/footprints/zones/source ancestry），**不伪装成尚缺 segment/opening/generator hash 的合法 `GroundTruthV3`**；
- manifest 接入：extraction/inspection 消费 Phase A 已落的 `gt_manifest.py` wire（§8），不改其 wire 定义（如确需改 → 停止报 blocker）；
- 测试：`tests/test_inspect_dxf.py` 扩展 + extraction core 测试族（§13 Phase B 验收 + §14 对应行）：合成 L/U 两层 footprint+zones 正例；dangle/cut/bulge/proxy/unit/hash/view-overlap/seed ambiguity 负测；**禁止 largest-bbox fallback**。

## 挂账件并入本批（主控裁决，Phase A 终审遗留）

见 [verdict/2026-07-14_b4a_phaseA_review_r1.md](../verdict/2026-07-14_b4a_phaseA_review_r1.md) 残留清单：

- **PA-R1（MINOR）**：`gt_schema.py:683` 未来 e2e case 目录写保护——glob 枚举改 resolved 相对路径 `parts` 前缀匹配（`('case_tests','e2e_tests',*,'case_data')`），补新建 case 目录负测。
- **PA-R2 NIT 束**：①§14.1 row 2 剩余拒例（bool/NaN-Inf/CW/nonorth/self-touch/hole/multipolygon）+ row 8 两小口（missing→None、bad JSON）补测；②双 zone 歧义 host、重复 projection key、plan-only 两向 mismatch 补 repo 测例固化；③monkeypatch 锁加 `omegaconf.OmegaConf.load` 联合 patch；④`wall_thickness_m` 删合同外 `= None` 默认（合同 §5.2 本无默认）；⑤`gt_schema.py:446` methods canonical 死代码清除 + `:465` 生产 `assert` 改显式 raise；⑥`compute_gt_implementation_hashes` 在 `gt_extraction.py` 落地后 extractor 组可算——补正例测试；⑦错误码 `gt_default_root_candidate_forbidden` 名义偏差**留痕不改**（稳定码）。

## ⚠️ 并行车道边界（本批新情况）

另一批（B4b Phase A，判卷 scorer 侧）**同树并行施工**。其车道 = `src/agent/judge/score_schema.py`/`score_config.py`/`score_inputs.py`（新增）、`reading_score.py`/`correction_score.py`/`elevation_score.py`/`score_policy.py`（adapter）、`src/configs/judge_score.yaml`、`scripts/tool_scripts/run_stage.py`/`build_judge_score_inputs.py`/`render_grade.py`/`_grade_transform.py`/`score_reading_vs_gt.py`、`skills/intake_pipeline/1_correction/A0_contract.md`，及其新测试文件。**本批一律不碰以上文件**；`git status` 出现对方车道的改动属正常，**不要 revert、不要重构、不要读其半成品当依据**。若发现必须跨车道改动才能过验收 → 停止报 blocker。

本批同样不碰：`render_gt.py`/`render_gt_overlay.py`（Phase D）、`gt_from_dxf.py`/`test_gt_from_dxf.py`（Phase C 重写；其现状已由主控指向 `gt_sources/`，回归须保持绿）、`gt.py`（Phase A 定稿）、correction/Vg/Va 生产代码。

## 硬边界

- 基座 = HEAD `526c38e`（sm21 source.dxf 已迁 `case_tests/test_baseline/gt_sources/sm21_anchor/`，全量 1106 绿 + 9 xfail，树干净）。
- 施工前先跑稿 §14.5 preflight（只查已有依赖，缺依赖停止报 blocker，不改 lockfile）。
- 零资产扰动（§2.2.8）：不改任何 `gt.json`/DXF/PNG/golden；合成 L/U DXF 只进 pytest 临时目录；`gt_sources/sm21_anchor/source.dxf` 本批不动。
- 不提供 `--write`/`--promote`/overwrite 能力（§2.2.7/§5.5）。
- gt 铁律：生产路径（executor/correction/reading）零 judge import；`tests/test_gt_discipline.py` 既有门保持绿。
- 备份：主控已全量备份 `backup/src_history/2026-07-15_b4a_phaseB_b4b_phaseA/`。
- 本批不创建 commit；不改管理文档。

## 测试纪律

- 定向组：新增/扩展 extraction+inspector 测试 + 既有 `test_gt_schema.py`/`test_gt_discipline.py`/`test_gt_from_dxf.py`/`test_gt_render.py`/`test_gt_overlay.py` 回归，逐组记 passed 数；全量 pytest 归主控轻门。
- 稿 §14 中 Phase B 相关测试族全数落地；确有未竟逐条列明，不得静默；稿章节→测试映射表写进简报。
- 独立合并条件（§13 Phase B）：inspection 无 manifest 只能 UNBOUND；不写默认 GT；Phase A 回归全绿。

## 交付

1. 工作树内完成代码+测试（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-15_b4a_phaseB_construction_brief.md`（改动映射/验收与测试/预期行为变化/未决·偏离/review-ask——无则注明 none；**附本批改动文件清单**，供主控按车道切分 diff）。
3. 回复只给 terse report（各组 passed/改动文件/关键结论/偏差/review-ask 摘要），不贴 diff。

审向：**Opus 执行审（升一档）→ 主控轻门（独立全量+抽查+裁决）**。
