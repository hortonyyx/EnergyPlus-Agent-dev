# B4a Phase C 施工派发（terra 执行档，2026-07-16）

**任务**：按 [AI_agent/proposals/c2_b4a_detail_spec.md](../../proposals/c2_b4a_detail_spec.md) **v2 定稿**施工 **Phase C（Vg segments、opening、elevation、north、candidate writer）**。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase C**（稿 §13 Phase C 行），Phase D（render/overlay）后续单独派工。Phase A（`25d3946`）、Phase B（`0d13b76`）均已 CLOSED 收录。

## 起点：Phase B 已交、Phase C 在其上接
- Phase B 已落 `src/agent/judge/gt_extraction.py`（398 行）：`extract_plan_geometry(inputs) -> PlanExtractionResult`（floors/footprints/zones/source ancestry）+ `inspect_extraction_inputs`；**只产 `PlanExtractionResult`，不伪造 `GroundTruthV3`、无 opening/segment/写盘入口**。
- Phase C = **在 Phase B 的 `PlanExtractionResult` 之上物化 boundary segments / openings / elevation z / north，组装成完整 `GroundTruthV3`，并接通 candidate writer + implementation hashes**。不得重做 Phase B 的 plan polygonize/zone 提取。

## Phase C 范围（稿 §13 Phase C + 对应算法章节）

逐条锚定细稿，**以稿为准**，本单只做指向与门槛，不复述算法：

- **boundary segments 与 surface binding**（§10.5）：对 canonical footprint 四方向调 **Vg 公开纯几何 API**（tolerance 从 config 显式构造 `VisibilityTolerances`；**禁止 import Vg 私有 `_segment_geometry_sha256`**，用 GT 自有 public stable-ID 函数 §5.4）；manifest elevation binding 的 `all_family_segments`/`listed_boundary_entities` scope 精确匹配（选零段/越层/一 locator 映多段 → fail）；每段 `projection_surface_key` lexical 去重成 plural list（零/多 view 合法，不得把 view 当 wall plane、不造 plan-only 假 key）；**所有边保留含全 hidden**。
- **plan opening → 最近合法 boundary segment**（§10.6）：证据组按 closed-outline/grouped-line/virtual bbox 规则取框；合法候选五条同时满足（平行/along span 精确落入 segment full interval/法向 `<= opening_boundary_max_distance_m`/同 footprint·zone 合法边界不跨 notch/kind 与 locator 唯一）；`(normal_distance, endpoint_residual, segment_id)` 排序，前二在 distance+residual 双落 tie epsilon → **fail `opening_segment_assignment_ambiguous`（不得用 ID 消歧）**；无候选 fail；`host_zone_id` 由正宽共线交唯一决定（多/零 zone fail；本批不产 null）。
- **elevation 匹配与 plan-only z**（§10.7）：evidence group 独立取框，两 `Affine1D.source_axis` 须不同；z 须精确落入声明楼层集中**恰一个**楼层竖向区间；**整 view 确定性最小代价 bipartite assignment（非逐窗贪心）**，多最优解落 tie epsilon → fail；一 plan opening 每 view 最多配一项、每 evidence group 恰配一 plan opening（额外 evidence fail）；多 view 观察同 opening 所得 z **必须精确一致（无 vertical-agreement 容差、不平均）**；无覆盖/不可见时 `z_interval=null` 只留 plan ref（**禁止平均窗高/复制相邻 z/楼层默认 sill·head**——sm26 U-notch 内墙窗即此表达：x/width 可评分、z 无 GT claim）。
- **north-axis、来源与最终自检**（§10.8）：manifest null → GT `north_axis_deg=null` + 空 refs；非空则校验 handle 在绑定 view 且 ref 可回溯，**只用 manifest 数值 + human overlay，不自动量角**（`dxf_axis_alignment_tolerance_m` 是长度不得比角度）；source document 只写 label/hash/unit/scale **不写本机 path**；**build 末段硬断言** `doc.generator.tolerances` 与本轮 resolved profile 逐字段全等（不等 fail，此断言只在 `extract_gt_v3` build 末、不得进任一 loader）→ 调 `validate_gt_v3` → canonical dump/reload 再 validate，两 typed object 与 canonical bytes 相同才准落盘。
- **稳定 ID/排序 + canonical bytes + candidate writer**（§5.4/§5.5）：物化 §5 全字段；segment ID `<floor_id>:boundary:<sha256前24位>`，**整文档校验截断碰撞、碰撞即 fail 不自动加序号**；各 list 持久化即 canonical 顺序（乱序报 `gt_wire_noncanonical_order`，不 load 时静默重排）；接通 `canonical_gt_v3_payload/bytes`、`compute_gt_v3_content_sha256`、`write_gt_v3_candidate(overwrite: Literal[False])`、`compute_gt_implementation_hashes`（extractor/validator/Vg 三组按 §5.5 relative POSIX path preimage）。**writer 只接受 `verification.status="candidate"`**；`out.exists()` 或落在 `DEFAULT_GT_DIR`/`gt_sources`/任何 `case_tests/e2e_tests/*/case_data` 内 → 先以稳定错误码拒绝；**不提供 `overwrite=True` 可调用实现**；promotion/sign-off 属后续资产批，本批不偷加。
- **`scripts/tool_scripts/gt_from_dxf.py` v3 重写**（§10.1）：现状已由主控指向 `gt_sources/`，**回归须保持绿**；build-only、无 `--write`/`--promote`/overwrite 落默认根能力。

## B4b 交接边界（§15.1，硬约束）
Phase C 输出给 B4b 的**稳定输入止于**：typed `GroundTruthV3` loader、verification status 与 generator/source/content hashes、per-floor footprint/zones、完整 segment list（含 hidden/depth/visible_intervals/0..N surface keys）、opening 的 floor/host/segment/along/nullable-z/source refs、optional north。`visible_intervals` 是 **Vg 派生量非独立观察真值**。**B4a 一律不输出** `scoreable`/`claim_status`/`denominator`/`completeness` 等看似半成品字段——那是 B4b 领地；越界即偏差。

## 硬边界
- 基座 = HEAD `e7adafe`（1147 绿 + 9 xfail，树干净）。
- 施工前先跑稿 §14.5 preflight（只查已有依赖，缺依赖停止报 blocker，不改 lockfile）。
- **零资产扰动**（§2.2.8）：不改任何 `gt.json`/DXF/PNG/golden；合成 L/U DXF 只进 pytest 临时目录；`gt_sources/sm21_anchor/source.dxf` 不动。
- **无 v3 baseline 文件**（§13 Phase C 独立合并条件）：本批不写任何 v3 GT 到仓库可见路径。
- gt 铁律：生产路径（executor/correction/reading）零 judge import；`tests/test_gt_discipline.py` 既有门保持绿。
- **本批不碰**：`render_gt.py`/`render_gt_overlay.py`（Phase D）、correction/Vg/Va 生产代码、B4b 车道（score_*/judge_score.yaml 等，现已 CLOSED，不 revert 不重构）。若必须跨界才能过验收 → **停止报 blocker**，不擅自改。
- review-ask 已裁定（§15.3 R1–R5）：0.400m 冻结 profile v1、不自动量角、graphics-export-only fail-closed、loader 只 dual-read v2/v3——**照裁决执行，不重开**。
- 备份：主控已全量备份 `AI_agent/backup/src_history/2026-07-16_b4a_phaseC/`。
- 本批不创建 commit；不改管理文档。

## 测试纪律
- 稿 §13 Phase C 验收全数落地：**L/U 完整 round-trip**（inspect→extract→load→（其后 render 归 Phase D，本批到 load/hash））；多 depth/hidden/plan-only z/nonzero north 正例；**tie / no-candidate / source isolation / overwrite 全负测**。
- **独立合并条件（§13 Phase C 硬门）**：两次不同 DXF entity 顺序产出 canonical bytes **逐字节相同**；无 v3 baseline 文件。这条给一个显式测试锁死（打乱 entity 顺序 → 同 canonical bytes/同 content_sha256）。
- 定向组：新增/扩展 `test_gt_extraction.py`/`test_gt_from_dxf.py`/`test_gt_schema.py` + 既有 `test_inspect_dxf.py`/`test_gt_render.py`/`test_gt_overlay.py`/`test_gt_discipline.py` 回归，逐组记 passed 数；全量 pytest 归主控轻门。
- 稿 §14（Phase C 相关：§14.1 row 剩余拒例、§14.2 extractor/inspector 单测族）全数落地；确有未竟逐条列明不得静默；**稿章节→测试映射表写进简报**。

## 交付
1. 工作树内完成代码+测试（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-16_b4a_phaseC_construction_brief.md`（改动映射/验收与测试/预期行为变化/未决·偏离/review-ask——无则注明 none；**附本批改动文件清单**）。
3. 回复只给 terse report（各组 passed/改动文件/关键结论/偏差/review-ask 摘要），不贴 diff。

审向：**Opus 子代理执行审（升一档·最高对抗档·活体探针）→ 主控轻门（独立全量+抽查+裁决）**。
