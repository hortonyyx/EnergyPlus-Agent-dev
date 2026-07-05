# 审阅请求：correction 层 A1-min + A2（含 A0 修订 re-verify）

- **日期**：2026-06-07
- **发起**：主开发 Agent（Claude Opus）+ 用户
- **类型**：skill 文档审阅（partA 逐篇落地第 2 批；同时回验上一轮 A0 审阅的修订）
- **希望审阅模型**：另一模型（Codex / Gemini）

---

## 1. 背景

partA 校正约束集逐篇落地。A0 已审过定稿（上一轮 8 findings 全采纳 + 检索包国标值回填）。本批写 **A1-min（坐标归一化）+ A2（正则吸附）**，二者引 A0 的 evidence/tolerance/audit 口径，按设计为"确定性 over typed evidence + 升级到 A3"。

**本轮审阅含两部分**（用户要求）：
- **(主) A1-min + A2 是否成立、可定稿**；
- **(回验) A0 上一轮 6 条 minimal patch 是否真落实、有无引入新问题**。

---

## 2. 审阅对象

**主审**：
- [A1_coordinate_normalization.md](../../../../skills/energyplus_mcp_twostep/phase2/PartA-correction/A1_coordinate_normalization.md)
- [A2_regularization.md](../../../../skills/energyplus_mcp_twostep/phase2/PartA-correction/A2_regularization.md)

**回验**（上一轮 review 的 6 条 minimal patch 是否落实）：
- [A0_contract.md](../../../../skills/energyplus_mcp_twostep/phase2/PartA-correction/A0_contract.md)（重写版）
- 上一轮 review：[2026-06-07_correction_A0_contract_review.md](../review/2026-06-07_correction_A0_contract_review.md)

上下文：
- [README.md](../../../../skills/energyplus_mcp_twostep/phase2/PartA-correction/README.md)（运行时 + header 约定）
- [recognition_modeling_capability.md §5](../../../capability/recognition_modeling_capability.md)（partA 定稿设计）
- [检索包](../review/2026-06-07_partA_priors_tolerance_retrieval.md)（容差常数来源）

skill 库口径：**英文纯当前版本 spec**，无时间戳/版本日志/决策史/案例引用。

---

## 3. 关注点 — A1-min + A2（主审）

1. **A1/A2 边界**：A1 只做"参照系+中线+z-stack"、A2 做"规范轴集+吸附+闭合+量化+碎片"——切分干净吗？有无该在 A1 却放进 A2（或反之）的内容？
2. **确定性 over typed evidence 是否真落实**（上轮 finding 2 的核心）：A2 §1 "仅 topology_identity 证据支持 same-axis + 偏移≤AXIS_JITTER_TOL 才合并、坐标接近不够"——这条够不够硬挡住"吸掉真实错台/shaft"？A1 中线转换的升级路径（墙侧/墙厚未知→A3）够不够？
3. **升级路径完整性**：A1/A2 所有"判断"是否都有明确的 deterministic-path vs escalation-path？有没有偷偷做了本该升 A3 的决策？
4. **常数引用**：A1/A2 引 A0 registry 常数（SNAP_GRID/MIN_EDGE_LENGTH/AXIS_JITTER_TOL/GAP_*/DIMCHAIN_CLOSE_TOL/OUTPUT_PRECISION）是否用对、量纲对、profile 对？
5. **运行时反馈**：A2 §6 "detect→A3-resolve(+A4)→apply" 与 A0/README 运行时一致吗？A2 检出冲突后交 A3、A3 决策后 A2 再确定性建轴——闭环对吗？
6. **崩溃杀手是否真到位**：A2 §1 跨层统一 + §5 碎片防止，能否真正消除"同墙跨层 5cm 抖动→退化碎片→EP 段错"那类？有无漏网路径？
7. **量化次序**：A2 §4 "canonicalization+closure 之后才量化、不能先量化"——这条对吗、够醒目吗？
8. **profile 适用**：A1/A2 全 profile 适用 + perimeter_core 下内部轴只为例外/归属——表述准确吗？

## 4. 关注点 — A0 回验（6 条 minimal patch）

逐条确认是否落实、有无残漏/新问题：
1. §7 validation 去 `zones`、改 PartA-scoped 目标（footprint/room_cell/facade/window_anchor，thermal_zone 保留）+ 顶层 status。
2. §1 加 claim_type + 三套 authority ladder（numeric/topology_identity/semantic）。
3. §2 审计 envelope 字段（stage/method_profile/entity locator/frame/unit）+ 三 schema 补字段（value_type/tolerance_name/candidate source_ids[]）。
4. §3 加第 7 类 `reference_or_identity_ambiguity`。
5. §4 容差改 registry 表（status/source_or_basis/profiles/hard-warn）+ 检索包常数回填。
6. §5 三档 profile 的 A3/A4 强度（use_grouped_rooms 语义+闭合强、perimeter_core 保守、room_identity 全）。

---

## 5. 验收标准（review 文档应给出）

- **Verdict（A1+A2）**：是否可定稿、进入 A4 stub + A3。
- **Verdict（A0 回验）**：6 条 patch 是否 closeable。
- 逐条回应 §3（8 点）+ §4（6 点）。
- 缺漏/新问题清单。
- 输出落 [../review/2026-06-07_correction_A1A2_and_A0_reverify_review.md](../review/)（命名对齐本 request）。

---

_本 request 与对应 review 均 git 跟踪。A1+A2 定稿后续 A4 stub（用检索包先验表）→ A3。_
