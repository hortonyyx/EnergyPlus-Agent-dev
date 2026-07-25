# 派工单：天正命名立面处理批施工（terra）

**日期**：2026-07-24 · **主控**：Opus 4.8 · **施工方**：terra（gpt-5.6-terra high，GPT 侧）
**审**：Opus 子代理升一档（Claude 侧·独立上下文·活体探针·探索性对抗审·谁写谁不批）→ 主控轻门
**施工合同**：[proposals/tarch_elevation_spec.md](../../proposals/tarch_elevation_spec.md)（1374 行·已过 Opus 子代理审 APPROVE-WITH-CHANGES·sol 累计并入全部修订·`0dd486a` 提交为施工基线）
**验收总标准（用户定）**：sm24 gt 做成对齐 `case_tests/test_baseline/gt/sm21_anchor` 的交付形态（`gt.json` + `renders/` 含四立面 + overlay），用户看**同 hash review bundle**、人眼核 datum 与手性后签字才锁定。

---

## 0. 当前定位

转换器返工已 CLOSED（07-23，GLM APPROVE-WITH-CHANGES，1539 绿）。之后跑 sm24 暴露两缺口：① 多房间共用外墙→窗无法归属 **已 CLOSED**（`2b7affad`，1541 绿）；② **转换器根本没处理立面**——sm24 DXF 有 4 个命名立面（北/南/西/东立面·`edge` 层 5 框）+ `E_WINDOW` 49 实体，但转换器 `_build_manifest` 只塞平面 view → sm24 gt 无窗高/立面/overlay，做不成 sm21 形态。**本批就是补这块——本轮剩余最重、最大的一块。**

**你不是从零设计。**几何算法、契约、验收纪律、必红夹具矩阵、完成定义**全部在细稿里写死**（§13 明言核心设计"不留施工自由裁量"）。你的活 = **按细稿实现 + 补齐 §9 必红夹具矩阵 + 跑通 sm24 端到端产 gt/overlay**。动手前**完整通读细稿一遍**，尤其 §0.3（最重要纪律）、§2（输入契约）、§3（E0–E8 流水线）、§9（必红矩阵）、§10（施工触点/不改项）、§11（完成定义 15 条）。

---

## 1. 唯一已决主控裁（G10 wire）

细稿 §13 唯一 [M] 已裁：**G10 走「新增 canonical review-index 文件、ack 只绑定 index hash」**（细稿推荐后者，便于未来动态 view 数量）。不是升级现有 ack 为逐文件 hash 列表。其余核心设计**无待决**，按细稿实现。

---

## 2. sm24 素材位置 + 你要撰写 sm24 v3 request

**素材 bundle**（转换器 reworked HEAD 产·可直接复用）：`logs/experiments/2026-07-24_sm24_gt_review/`（**仓库根**，非 `AI_agent/logs/`）
- `source.dxf` = 天正原图（含 4 命名立面框 + `E_WINDOW` + 门块）
- `normalized.dxf` / `manifest.json` / `source_map.json` / `conversion_report.json` = 当前 plan-only 转换器输出（你要把立面加进去）

**你要为 sm24 撰写 v3 立面 request**（`request_version=3`·§2.1–2.7）。sm24 的事实底座**已写死在细稿里、直接照抄**：
- **datum handle 表**（§2.5）：North `125` start / South `102` start / West `144` end / East `12F` end，均绑 `F1.z_floor_m=0`；
- **门块 exact role map**（§2.5/§2.7）：`$EWDLib$00000614` 的 `112`=`structural_outline`，`113`–`11F`（含 CIRCLE `11C`）全 `nonstructural_detail`；
- **along 方向**（§2.6）：South/East 正向、North/West 反向（该 request 显式事实，非全局规则）；
- **title map**（§2.3）：北立面→North / 南立面→South / 东立面→East / 西立面→West。

**⚠️ 受信人工输入边界（§0.3/§2.5/§2.6，务必如实处理，别机器化冒充）**：sm24 地面线**无机器可读 ±0.000**，datum handle 与有向端点是**人信任输入**——机器只能证明 request 内部自洽（sign/offset/端点/plan lo·hi 一致），**不能**从无标签几何证明"这条线在语义上就是 1F datum"、也**不能**区分正确 request 与"sign+端点+along-offset 三者同步一致重标"的 request。**禁**用最低线/框底/窗台标注/"天正通常从 0 画"启发式补 z（§2.5 禁止清单）。这层语义**必须落进逐 opening audit rows + 带 ID/z 标注 overlay 供 G10 人核**。

---

## 3. 命脉：必红夹具矩阵必须真红（主控全程盯）

**这是本批命脉，也是上轮转换器返工你连推三轮的那道关（九门 neuter 假锁死在这）。这次我全程盯 §9 必红矩阵的 neuter 变异测试。**

- **§9（§9.1–9.11）每条必红夹具都必须真正令对应 gate/门变红**——不是加个 fixture 看着像。每道变异（datum 有向端点 sign-only / endpoint-only / along-offset-only / sign+along-offset 端点不变 / door block drift / window grouping 退化 / kind mismatch / hash 篡改 / …）注入后，**目标门必须实际 raise 或产 BLOCK 诊断**，且是**因为该门在算、不是别处兜底或 fixture 恰好非法**。
- **诚实披露不伪造 neuter 自查表**（对标 B4b Phase D / 转换器返工正面样板）：简报里 §9 逐格自查如实报"注入 X → 门 Y 变红/未变红"；**做不到的格子明写未竟，别填绿**。任何"名义有门、变异后仍全绿"= false-lock = 假绿，审必抓、主控轻门也会亲核。
- **特别注意手性那条（§2.6/§9.4）**：sign-only / endpoint-only / along-offset-only / "sign+along-offset 但端点不变" **四种 mutation 必红**；但 **sign+endpoint+along-offset 三者同步一致重标不要求机器红**（人信任边界）——这条**不能**硬造机器门冒充，必须在逐 opening audit + overlay 里显露等 G10 人审。别把 declared-direction consistency gate 说成 source handedness 的机器真值证明。

---

## 4. Scope 边界（§10·越界停工回主控）

- **改**（§10 施工触点·边界非逐行）：`tarch_converter_schema.py`（legacy V1 不变·v3 独立 discriminated datum-bound variant·有向端点·door block exact role map·raster controls·诊断码·source-map op）/ `tarch_normalize.py`（E0–E8·门块结构轮廓 extraction/union·generated elevation outlines·complete manifest·完整 G9）/ `gt_extraction.py`（elevation assignment 加 kind equality·顺带修 `_assign_elevation` 的 kind 缺口=另一 D8）/ 对应 `tests/`。
- **不改**（§10）：GT v3 wire 的 `ElevationViewBindingV1`/`ElevationOpeningEvidenceV1` 字段、`GroundTruthV3` opening wire、v2 legacy adapter、scorer/Va/Vg 既有语义、`render_gt.py`/`render_gt_overlay.py` 核心投影算法。**若发现必须改以上"不改"项，停工回主控，不得借实现便利扩大范围。**
- **不动**：gate①、执行器、reading/correction、golden、`gt.json` 铁律路径语义、v2 legacy 数据语义/默认 scorer。**禁** execution/reading/correction/gate① import 转换器。

---

## 5. 完成定义（§11 十五条·功能验收非仅 unit 绿）

细稿 §11 是硬完成定义，**逐条落实并在简报对账**。要害摘录：
- legacy v1/v2 极简 elevation intent 不回归，只有 v3 `named_datum_bound` variant 能进 E0–E8；
- sm24 44 window LINE → 11 规范化 window outlines；5 door INSERT 只经 block `112` 结构轮廓 → 3 exterior-door outlines；7 interior door 继续 INFO 排除；
- 11 window 与 plan exterior window 一一链接，无 orphan/ambiguity；14 opening 全有 source-observed z（11 window 是核心验收）；
- 四 datum 有向端点按 request 映射 plan lo/hi；South 对称窗四类 mutation 必红（见 §3）；CIRCLE `11C` exact 排除、门 z 与 raw virtual bbox 无数据依赖；
- complete manifest 含 1 plan + 4 elevation bindings；G9 真跑 `extract_gt_v3`（非 preflight）；
- `gt_elev.png` 四个真实 surface（非 NO-BINDING 占位）；四张 `overlay_{East,North,South,West}_view.png` 经三点有向 calibration、同一原子 `gt/renders/` bundle、不过界；
- conversion report 与 overlay 对 14 relevant openings 逐项列 `z_interval` + datum start/end→plan lo/hi 映射，绑同一 inventory hash（供 G10 人核）；
- 全量测试无 v2/execution/reading/correction 回归。

**产出位置**：gt + renders 产到 **review 目录**（如 `logs/experiments/2026-07-24_sm24_gt_review/gt/`），**先给用户人核、不直接写 `case_tests/test_baseline/gt/sm24_anchor/`**（那是 G10 签字锁定后的事）。**不写受保护 `gt/`、`gt_sources/` 目录**（转换器 work_dir guard 会拦）。

---

## 6. 审阅需求（Opus 子代理会这样探，你自己先堵）

- **活体探针打 false-lock**：审会 neuter 每道 §9 门看是否真红、会挖空/篡改 datum affine·门块 fingerprint·raster hash 看 gate 是否穿透。你交付前**自己先跑一遍 neuter 自查**（诚实填表）。
- **恒真式自检/死分支**（历史高频 MAJOR，如 B4a Phase C F1 `!=` 恒 False）：任何"自比自"的 tolerance/一致性校验都会被抓。
- **shipped-untested**（历史第三高频）：§9/§11 声称的验收轴必须每轴有真测试，别声称覆盖实无。
- **信任根穿透**（B-M CR-01 / B-O CR4-5 同族）：hash 只比自报字段不重算 payload、终门只读 state 被篡改穿透——datum/门块/raster 三处 hash 都要真重算校验。
- **契约冻结破坏**：v3 request/manifest 新字段全进 canonical hash（§2.1/§2.4）；别加了字段不进 hash。

---

## 7. 纪律

- 动 `src/` 前 `cp` 备份到 `backup/src_history/2026-07-24_elevation/`。
- **诚实披露**：做不完/部分/残留明写简报，别把未竟说成完成；§9 neuter 自查表如实填（见 §3）。
- **备份下游若动**（本批不该动下游）；如需动"不改"项先停工回主控。
- 简报落 `AI_agent/logs/reviews/execution/2026-07-24_elevation_construction_terra.md`：sm24 v3 request 撰写结果 / E0–E8 实现要点 / 门块结构轮廓合成 / 完整 G9 / kind 修复 / §9 逐格 neuter 自查表 / §11 十五条逐条对账 / sm24 gt+renders 产出（含四立面 overlay）+ 与 sm21 交付形态对齐情况 / 全仓测试结果（现基线 **1541 passed, 10 xfailed**）。
- 完成 `git commit`（label 如 `7.24_TArchElevationConstruction`·body 三段：①改动 ②为何此刻 ③影响·结尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`）。**别 push。**
- 全程中文。审 = Opus 子代理升一档，之后主控轻门。
