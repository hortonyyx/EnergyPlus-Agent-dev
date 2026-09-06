# E-a′ 施工停报：工作目录边界与全量验收冲突

日期：2026-09-06。施工 worktree：`/tmp/ea2_astra`。开工 HEAD：`363844b3`。

**结论：按 A 层停下上报，未实施源入口改造，不能验收为完成。** 本次不是再次否定 §一的源格式事实；三份生产产物及适配器已实测，sm25 1F 的 49/374/22/85 与派工单一致。停点是当前工作边界下无法兑现硬全量验收：用户明令「所有读写都在 `/tmp/ea2_astra` 里做」，现有生产隔离门却要求 staging 必须在仓库外。不是行号或外围数值偏差，也不能靠改隔离门、跳过测试或跨出授权目录解决。

本报告完整保留头号交付物消费表，记录的是**未改生产代码时的消费现状**。五条新增验收锁均未实施，不把既有低层测试当成本单真实接线证明。

## 1. 开工自检与事实实测

开工依次执行用户指定自检，并完整读取 199 行派工单；原文结果：

```text
/tmp/ea2_astra
363844b3
/tmp/ea2_astra/src/agent/correction/tick_claim.py
199 AI_agent/logs/reviews/request/2026-09-06d_Ea2_source_contract_dispatch.md
```

跑全量前再次核对的两个模块：

```text
/tmp/ea2_astra/src/agent/correction/tick_claim.py
/tmp/ea2_astra/src/agent/correction/opening_adjudication.py
```

派工单写基点 `8c66e3fd`，当前 `363844b3` 的直接父提交就是它；按用户明确指定的 HEAD 开工，无基点冲突。未发现工作树内 AGENTS.md。

| 原产物 | face_lines | pair_candidates | pairs | opening_candidates | pairs_status | 现有适配器的 wall_claims / opening_claims |
|---|---:|---:|---:|---:|---|---|
| sm25_1f_v2.json | 49 | 374 | 22 | 85 | SELECTED | 22 / 85 |
| sm25_2f_v2.json | 46 | 303 | 21 | 87 | SELECTED | 22 / 87 |
| sm24_1f_v2.json | 98 | 1185 | 8 | 87 | SELECTED | 12 / 87 |

逐源 SHA-256 与键清单：[source_inventory.json](2026-09-06d_Ea2_evidence/source_inventory.json)。只读原产物，未重写哈希或已签字基线。`SCHEMA` 定义在 `src/agent/reading/as_drawn/schema.py:112`，由 `as_drawn_v2.py:66` 转出。配对选择确实来自 `hypotheses.pairs`；不需要用 v0 名称猜配对。

B 层措辞登记：派工单的「候选无阈值」应精确读作**无间距/声明厚度准入阈值**。生产枚举另有同轴、支撑不重叠、最小沿线重叠等测量条件（`as_drawn_v2.py:455-480`）。这不推翻源格式前提，未拿它停报。

## 2. 消费对照表（202 行，头号交付物）

外延：逐读 `assemble()` 和生产类型，再遍历 sm25 1F/2F、sm24 1F 三份真实产物，合并全部路径；含容器，列表元素记 `[]`，动态键记 `*`，x/y 轴分别列。生产类型声明但实物为空/None 的通道也补入。机器路径清单：[field_paths.json](2026-09-06d_Ea2_evidence/field_paths.json)。

这里的「结构上不必」只表示**不应用该字段直接决定数值/几何**，不代表可以丢掉证据或已验证真伪。凡类型为 Any、缺后续语义校验之处，末列明确登记无人接住，不以「保留 bytes」代替消费与校验。

| 生产格式的字段 | 谁该消费它 | 现在消费了吗 | 若「结构上不必」——被绕过后坏数据流到哪、谁接住 |
|---|---|---|---|
| `declarations` | 生产类型/分类器与消费入口 | 分类器及适配器接受完整 v2；A-6 _raw_edges / OpeningReview 拒绝 v2 | 不属于免消费；缺层应走 MALFORMED_DECLARED_CONTRACT，现 A-6 未接分类器拒绝路径。 |
| `declarations.chains` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `declarations.chains.*` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `declarations.chains.*.axis` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `declarations.chains.*.direction` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `declarations.chains.*.ref_coord_m` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `declarations.chains.*.values_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `declarations.chains.*.world_start_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `declarations.drawing_box_px` | reading 量具裁图/定标；下游保留声明与测量差异 | 结构上不必在洞口裁决重新裁图或重定原点；A-6 未消费 v2 | 图框裁漏会进入 face_lines/gaps，原点错误会影响全部坐标；现类型 Any 不抓语义错，靠 reading 的像素复算与模型回看，当前 A-6 未接这条复核。 |
| `declarations.thickness_callout_note` | 模型选择声明厚度；刻度表达式按源引用取操作数 | A-6 未读 v2 声明；不得拿它筛 pair_candidates 或重配墙 | 不属于免消费；错值需声明源校验/模型纠正，当前未接线。 |
| `declarations.thickness_callouts_mm` | 模型选择声明厚度；刻度表达式按源引用取操作数 | A-6 未读 v2 声明；不得拿它筛 pair_candidates 或重配墙 | 不属于免消费；错值需声明源校验/模型纠正，当前未接线。 |
| `declarations.world_zero_px_declared` | reading 量具裁图/定标；下游保留声明与测量差异 | 结构上不必在洞口裁决重新裁图或重定原点；A-6 未消费 v2 | 图框裁漏会进入 face_lines/gaps，原点错误会影响全部坐标；现类型 Any 不抓语义错，靠 reading 的像素复算与模型回看，当前 A-6 未接这条复核。 |
| `hypotheses` | 生产类型/分类器与消费入口 | 分类器及适配器接受完整 v2；A-6 _raw_edges / OpeningReview 拒绝 v2 | 不属于免消费；缺层应走 MALFORMED_DECLARED_CONTRACT，现 A-6 未接分类器拒绝路径。 |
| `hypotheses.ambiguous_face_lines` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `hypotheses.ambiguous_face_lines.*` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `hypotheses.family_roles` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.achromatic_only` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.assignment` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.assignment.*` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.chromaticity` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.pct_of_ink` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.shape` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.shape.area_px_max` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.shape.area_px_median` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.shape.components` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.shape.elongated_fraction` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.shape.fill_ratio_median` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.evidence.*.shape.longest_extent_px` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.family_roles.source` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `hypotheses.non_wall_face_lines` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `hypotheses.non_wall_face_lines.*` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `hypotheses.note` | 审计与模型复核来源 | 结构上不必解释自然语言以产生几何；A-6 未消费 v2 | 备注错误留在冻结源和审计，不应参与数值决策；引用存在不等于来源真实性得到验证，当前无人校验自然语言真伪。 |
| `hypotheses.opening_candidates` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[]` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].face_line` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].gap_index` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].id` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].ink_by_family` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].ink_by_family.*` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].ink_by_family.*.by_distance_px` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].ink_by_family.*.by_distance_px.*` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].ink_by_family.*.nearest_px` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].ink_by_family.*.on_line` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].ink_by_family.*.span_ratio` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].len_m` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].len_px` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates[].span_m` | tick_claim 枚举每候选两端；OpeningReview 按面线及 gap 引用消费 | 适配器保留每个候选 source_ref；A-6 未读 v2，仍枚举 wall_bands.opening_runs | 不属于免消费；证据门校验源引用，候选与 gap 的数值一致性及完整覆盖须在消费入口核对。 |
| `hypotheses.opening_candidates_basis` | 审计与模型复核来源 | 结构上不必解释自然语言以产生几何；A-6 未消费 v2 | 备注错误留在冻结源和审计，不应参与数值决策；引用存在不等于来源真实性得到验证，当前无人校验自然语言真伪。 |
| `hypotheses.opening_types` | 感知模型的门/窗/非洞口命名；洞口范围及实体身份裁决 | 前置适配器仅保存源；A-6 未消费 v2 的逐候选分类 | 不属于免消费；不能把所有 gap 默认成窗，需模型处置完整覆盖并留账。 |
| `hypotheses.opening_types.*` | 感知模型的门/窗/非洞口命名；洞口范围及实体身份裁决 | 前置适配器仅保存源；A-6 未消费 v2 的逐候选分类 | 不属于免消费；不能把所有 gap 默认成窗，需模型处置完整覆盖并留账。 |
| `hypotheses.opening_types_source` | 审计与模型复核来源 | 结构上不必解释自然语言以产生几何；A-6 未消费 v2 | 备注错误留在冻结源和审计，不应参与数值决策；引用存在不等于来源真实性得到验证，当前无人校验自然语言真伪。 |
| `hypotheses.pair_candidates` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates[]` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates[].face_a` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates[].face_b` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates[].matched_declared_mm` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates[].overlap_px` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates[].spacing_m` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates[].spacing_px` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pair_candidates_basis` | 审计与模型复核来源 | 结构上不必解释自然语言以产生几何；A-6 未消费 v2 | 备注错误留在冻结源和审计，不应参与数值决策；引用存在不等于来源真实性得到验证，当前无人校验自然语言真伪。 |
| `hypotheses.pairs` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[]` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[].face_a` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[].face_b` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[].matched_declared_mm` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[].overlap_px` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[].source` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[].spacing_m` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs[].spacing_px` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.pairs_note` | 审计与模型复核来源 | 结构上不必解释自然语言以产生几何；A-6 未消费 v2 | 备注错误留在冻结源和审计，不应参与数值决策；引用存在不等于来源真实性得到验证，当前无人校验自然语言真伪。 |
| `hypotheses.pairs_status` | 证据适配器核图及选中引用；OpeningReview 只消费模型选中对 | 适配器遍历候选与选中对；A-6 未读 pairs/pairs_status，只有 v0 墙带 | 不属于免消费；引用/重复/覆盖由证据门拦截；SELECTED 状态与空对需本入口另设门，不能回退候选重配。 |
| `hypotheses.perception_source` | 审计与模型复核来源 | 结构上不必解释自然语言以产生几何；A-6 未消费 v2 | 备注错误留在冻结源和审计，不应参与数值决策；引用存在不等于来源真实性得到验证，当前无人校验自然语言真伪。 |
| `hypotheses.solid_band_walls` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `hypotheses.solid_band_walls.*` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `hypotheses.unpaired_wall_faces` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `hypotheses.unpaired_wall_faces.*` | 证据适配器的面线处置/债务；墙编译器与洞口宿主判定 | adapt_as_drawn_plan 遍历四桶并校验引用/完备性；A-6 未读取 | 不属于免消费；桶引用与覆盖错误由 validate_evidence_bundle 接住；理由文本真伪不由代码猜。 |
| `image` | 源 bytes 身份与图像/楼层绑定；审计展示 | A-6 image_id 由调用者提供；尚无 v2 bundle→TickSession 接线 | 不属于整体免消费；image_label 仅展示，错误标签不应改变来源哈希或取代 bundle 身份。 |
| `image_label` | 源 bytes 身份与图像/楼层绑定；审计展示 | A-6 image_id 由调用者提供；尚无 v2 bundle→TickSession 接线 | 不属于整体免消费；image_label 仅展示，错误标签不应改变来源哈希或取代 bundle 身份。 |
| `ledger` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.bridging_applied` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.face_lines` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.faces_with_a_candidate` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.families_assigned` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.families_discovered` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.gap_classified` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.gaps_total` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.opening_candidates` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.opening_types_named` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.pair_candidates` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.pairing_in_observations` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.pairs_selected` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.pairs_status` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.runs_total` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `ledger.unassigned_ink_pct` | reading 记账；裁决审计核对对应集合 | 结构上不必拿汇总字段生成洞口；当前 A-6 未核对该账 | 汇总被篡改不应生成坐标；真实集合应由入口重数。当前汇总为 Any，语义错误可进入冻结源，无下游专门拦截，登记缺口。 |
| `observations` | 生产类型/分类器与消费入口 | 分类器及适配器接受完整 v2；A-6 _raw_edges / OpeningReview 拒绝 v2 | 不属于免消费；缺层应走 MALFORMED_DECLARED_CONTRACT，现 A-6 未接分类器拒绝路径。 |
| `observations.calibration` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.cross_axis_relative_deviation` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.fill_ratio` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.mm_per_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.profile_bins_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.world_zero_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.world_zero_source` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.axis` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.chain_closure_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.cum_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.m_per_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.matched_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.max_abs_residual_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.mm_per_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.origin_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.overall_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.residual_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.rmse_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.unmatched_ticks_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.x.values_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.axis` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.chain_closure_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.cum_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.m_per_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.matched_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.max_abs_residual_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.mm_per_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.origin_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.overall_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.residual_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.rmse_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.unmatched_ticks_px` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.calibration.y.values_mm` | reading 定标；tick_claim 对链节点、轴、方向、原点作取数与复核 | A-6 只读顶层 calibration 和补充件；未读 v2 的 observations.calibration / declarations.chains | 不属于免消费；坏链本应由 require_chain 与帧校验接住，当前 v2 在源格式分支先被拒绝。 |
| `observations.components_by_family` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.components_by_family.*` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.components_by_family.*[]` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.components_by_family.*[].area_px` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.components_by_family.*[].bbox_px` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.dimension_witnesses` | 刻度认领模型的像素提示，不能替代保留链身份的节点 | 结构上不必把有损像素→数值 map 当坐标权威；A-6 未交付 v2 提示 | 坏 map 会误导刻度指认；数值仍必须从带链 ID 的声明计算。当前 map 是 Any，模型指认复核尚未接入，不存在 map 语义验证保证。 |
| `observations.dimension_witnesses.x` | 刻度认领模型的像素提示，不能替代保留链身份的节点 | 结构上不必把有损像素→数值 map 当坐标权威；A-6 未交付 v2 提示 | 坏 map 会误导刻度指认；数值仍必须从带链 ID 的声明计算。当前 map 是 Any，模型指认复核尚未接入，不存在 map 语义验证保证。 |
| `observations.dimension_witnesses.x.*` | 刻度认领模型的像素提示，不能替代保留链身份的节点 | 结构上不必把有损像素→数值 map 当坐标权威；A-6 未交付 v2 提示 | 坏 map 会误导刻度指认；数值仍必须从带链 ID 的声明计算。当前 map 是 Any，模型指认复核尚未接入，不存在 map 语义验证保证。 |
| `observations.dimension_witnesses.y` | 刻度认领模型的像素提示，不能替代保留链身份的节点 | 结构上不必把有损像素→数值 map 当坐标权威；A-6 未交付 v2 提示 | 坏 map 会误导刻度指认；数值仍必须从带链 ID 的声明计算。当前 map 是 Any，模型指认复核尚未接入，不存在 map 语义验证保证。 |
| `observations.dimension_witnesses.y.*` | 刻度认领模型的像素提示，不能替代保留链身份的节点 | 结构上不必把有损像素→数值 map 当坐标权威；A-6 未交付 v2 提示 | 坏 map 会误导刻度指认；数值仍必须从带链 ID 的声明计算。当前 map 是 Any，模型指认复核尚未接入，不存在 map 语义验证保证。 |
| `observations.face_lines` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[]` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].axis` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].constant_world_axis` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].covered_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].edges_m` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[]` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].hi_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].ink_by_family` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].ink_by_family.*` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].ink_by_family.*.by_distance_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].ink_by_family.*.by_distance_px.*` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].ink_by_family.*.nearest_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].ink_by_family.*.on_line` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].ink_by_family.*.span_ratio` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].len_m` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].len_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].lo_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].gaps[].span_m` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].id` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].ink_coverage_per_run` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].pos_m` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].pos_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].runs_m` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].runs_m[]` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].runs_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].runs_px[]` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].support_cols_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].support_px` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.face_lines[].support_width_m` | reading 量具；证据门核引用；墙编译器与洞口裁决关联同轴同线 | 适配器/证据门读取面线；A-6 未读取 v2 面线，不能从 v0 命名反推 | 不属于免消费；生产类型抓结构，证据门抓身份/闭合；像素量值正确性需 reading 复算，不能以类型校验冒充。 |
| `observations.ink_palette` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.achromatic_only` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.chroma_steps` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.distinct_rgb_values` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[]` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].assign_distance_p50` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].assign_distance_p95` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].brightness_median` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].cells_merged` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].chromaticity` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].core_chromaticity` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].id` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].max_merge_distance` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].pct_of_ink` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].px` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].shape` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].shape.area_px_max` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].shape.area_px_median` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].shape.components` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].shape.elongated_fraction` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].shape.fill_ratio_median` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].shape.longest_extent_px` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.families[].spread` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.ink_px` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.merge_dist` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.min_share` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `observations.ink_palette.unassigned_pct` | reading 量具与感知模型；裁决模型复核墨迹证据 | 结构上不必由代码拿颜色/形状阈值判洞口；尚未交给 A-6 模型 | 畸变会污染模型证据；源类型将这些通道列为 deferred/Any，现有 A-6 无语义接住者。需原字节保留并向模型交付，不能宣称冻结即校验。 |
| `schema` | 生产类型/分类器与消费入口 | 分类器及适配器接受完整 v2；A-6 _raw_edges / OpeningReview 拒绝 v2 | 不属于免消费；缺层应走 MALFORMED_DECLARED_CONTRACT，现 A-6 未接分类器拒绝路径。 |

## 3. 停点、完整全量与逐位闭合

为执行「所有读写都在 worktree 内」，先创建 `.tmp` 并把 pytest/tempfile 临时目录定在其中；未写共享 site-packages，未进入主树或其他 worktree。

```sh
cd /tmp/ea2_astra
mkdir -p .tmp
TMPDIR=/tmp/ea2_astra/.tmp python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/tmp/ea2_astra/.tmp/ea2_baseline > AI_agent/logs/reviews/execution/2026-09-06d_Ea2_evidence/baseline.log 2>&1
```

完整原文：[baseline.log](2026-09-06d_Ea2_evidence/baseline.log)。**以汇总行证明跑完，不靠退出码：**

```text
300 failed, 3467 passed, 2 skipped, 13 xfailed, 205 warnings, 140 errors in 490.87s (0:08:10)
```

逐位闭合：派工单 `3907 + 2 + 13 = 3922`；本次 `3467 + 300 + 140 + 2 + 13 = 3922`。总数差 0；通过数少 440，逐条列出的 FAILED 300 + ERROR 140 = 440；相关子集测试属于这 3922 条，不能再加一次。

[baseline_causes.json](2026-09-06d_Ea2_evidence/baseline_causes.json) 对全量日志的 440 个失败/错误段逐个保留名字和原始 E 行，归因为：

| 类别 | 数量 | 证据与判断 |
|---|---:|---|
| 仓库内 staging 被拒绝 | 438 | 每段原文含 `staging root must be outside repo`；门是 `src/agent/execution/isolation.py:1877-1882`，真实入口 `build_isolation_workspace` 在第 231 行调用 |
| 全仓语料扫描包含本次 pytest 负例 | 1 | `tests/test_f97_vector_contract.py:623`；扫描器第 573 行 `root.rglob("0_reading")` 把 `.tmp` 内 8 份故意坏 JSON 也当成历史语料 |
| 并发生成文件改变 dirty 计数 | 1 | `tests/test_orchestrate_baseline.py:881` 原文差异 `dirty:69408` → `dirty:74222`；`record_baseline.py:93,115` 计入全部 untracked 路径。根据原文差异及实现，归因为仓库内临时文件增长；没有声称隔离重跑过此项 |

承重门的原文代码：

```python
def _require_outside_repo(path: Path) -> None:
    try:
        path.resolve(strict=False).relative_to(_repo_root())
    except ValueError:
        return
    raise ValueError(f"staging root must be outside repo: {path}")
```

真实测试入口的原文红：

```text
tests/test_cross_axis_exit.py:87:
    manifest = build_isolation_workspace(CASE_DIR, staging_root=root / "staging")
src/agent/execution/isolation.py:231: in build_isolation_workspace
    _require_outside_repo(staging_root)
E       ValueError: staging root must be outside repo: /tmp/ea2_astra/.tmp/ea2_baseline/popen-gw4/c1_staging0/staging
```

这证明仅将临时目录放进工作树不能满足硬全量验收。默认 pytest 临时目录会到授权边界外，未擅自使用；更改 `_require_outside_repo`、跳过上述测试也不能构成原验收。

相关模块未改代码时的子集基线命令：

```sh
TMPDIR=/tmp/ea2_astra/.tmp python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/tmp/ea2_astra/.tmp/ea2_target_baseline tests/test_tick_claim_a6.py tests/test_opening_adjudication_a6.py tests/test_b4_opening_synthesis.py
```

原文：[target_baseline.log](2026-09-06d_Ea2_evidence/target_baseline.log)。

```text
51 passed in 7.53s
```

诊断补充：全量末尾尚未结束时另启动 `--maxfail=1` 以找首个失败，得到全量原因后对该诊断进程发 SIGINT，避免重复跑。其 [first_failure.log](2026-09-06d_Ea2_evidence/first_failure.log) 明记 `xdist.dsession.Interrupted`；**不把这份诊断截断日志算全量完成证据**。

## 4. E-a-1..E-a-5 验收状态（均未完成，不冒认锁）

| 验收 | 当前可指位置与实测 | 本单状态 |
|---|---|---|
| E-a-1 真实 V3 装配消费当前批次 | `opening_adjudication.py:312` 的 consume 及第 318 行的 scoreable_openings 有低层门；既有 `tests/test_opening_adjudication_a6.py:86` 测过重新裁定使结果失效。但 `rg -n 'OpeningReview\|scoreable_openings\|TickSession\|TickPacket\|TickBatch' src/agent/pipeline.py` 无命中 | **未施工**：没有真实装配入口锁，没有本单变红命令；不能以旧低层测试销账 |
| E-a-2 落盘两份源 bytes + batch record 并重建 batch_id | `tick_claim.py` 当前保留 packet 源 bytes 和 batch record；pipeline 尚无对应持久化入口，见上项零命中 | **未施工**：未写落盘/回放机制，未做重建验收 |
| E-a-3 旧 B4 dict API 无生产调用者 | `rg -n 'synthesize_openings\(' src --glob '*.py'` 原文有 `src/agent/correction/opening_adjudication.py:198:            result = synthesize_openings(`，另有定义行 `opening_synthesis.py:1009` | **不满足**：当前还有 1 个生产调用点；未改名掩盖、未新增 grep 锁 |
| E-a-4 空 pairs 或非 SELECTED 响亮失败 | 第 5 节探针：合法全归桶且 `pairs=[]/SELECTED` 仍是 classifier ADAPT，适配器产 0 个 wall_claim；旧 TickSession 因整个 v2 不支持而拒绝 | **未施工**：没有 v2 专用的缺配对拒绝门，格式不支持错误不能算新防线 |
| E-a-5 注册 schema 但缺 hypotheses 走命名拒绝 | 第 5 节探针：分类器已有 BLK-A 路径；旧 TickSession 仍只报 `TICK_SOURCE_CONTRACT_UNSUPPORTED` | **未施工**：未将分类器的命名拒绝接进新入口，未宣称既有分类器通过就是整链通过 |

未触碰 `_elevation_document()`，因此按单中条件未改 A-6-d1。可见性、signed facade_convention、strict 交 judge、bundle 身份提取及不声明 elevation_source 不退债的既有防线均未改动；本单还没有新增接线验收证据。

## 5. 两条同形绕行路径与现场探针

运行命令（只在内存改输入，无生产源码/原件变更）：

```sh
cd /tmp/ea2_astra
PYTHONPATH=/tmp/ea2_astra python AI_agent/logs/reviews/execution/2026-09-06d_Ea2_evidence/probe_source_paths.py
```

可复算脚本：[probe_source_paths.py](2026-09-06d_Ea2_evidence/probe_source_paths.py)。原文：[source_paths.log](2026-09-06d_Ea2_evidence/source_paths.log)。

**路径一：用 `pairs_status=SELECTED` 掩盖空选择，并将全体面线塞入 non_wall 桶以绕过已有完备性门。** 实测：

```text
EMPTY_SELECTED classifier: as_drawn_plan adapt
EMPTY_SELECTED adapter wall_claims: 0
EMPTY_SELECTED current TickSession: TICK_SOURCE_CONTRACT_UNSUPPORTED
```

含义：生产类型和前置证据适配器的合法性不能替代 E-a-4。新入口必须自行检查“有模型选择”，同时保持分类器现有公开行为。当前尚未实现；这份探针没有证明已挡住此路。

**路径二：注册 v2 schema，删 hypotheses，再加 legacy `strokes=[]`，尝试结构 fallback。** 实测：

```text
MISSING_HYPOTHESES_WITH_LEGACY classifier: unknown None
MISSING_HYPOTHESES_WITH_LEGACY reason: declares schema='as_drawn_plan_v2' but matches no registered contract's key set, so it is a malformed declaration, not an undeclared legacy view; structural legacy fallback is reserved for files that declare nothing
MISSING_HYPOTHESES_WITH_LEGACY current TickSession: TICK_SOURCE_CONTRACT_UNSUPPORTED
```

含义：现有分类器 BLK-A 已挡住混合形状，但 A-6 自己尚未使用该分类器。不能在新入口用仅能 JSON parse 的判断绕过它。

## 6. 改动、分段提交、薄弱处与所需裁决

本次仅新增执行证据、盘点与停报文档。**生产文件、测试文件、历史原产物、答案根、已签字基线均未修改**，没有转换层，没有改分类器公开行为，也没有删除 v0。

- 已独立提交 `fb64b7a4`：202 行开工消费表、机器字段路径、三份源清单与哈希。
- 其后把完整原文日志、440 项归因、两条源路径探针与本报告作为第二个独立小步提交；提交前逐路径 add 并查看 `git diff --cached --numstat`。`.log` 被 ignore，显式 `git add -f`。
- v0 现有说明位于 `vector_contract.py:75-80`；实验写入方为 `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/as_drawn.py:410`。本单的新增 v0 锁未实施。
- 停报后清理本次生成的 `.tmp` 测试目录，失败原文已移入持久证据；未修改任何 tracked 文件以消掉失败。

**最薄弱一处**：消费表是基线静态追踪加两条探针，未经过跨家族复核；尤其 Any/deferred 通道的数值/语义错误不受生产类型的完整保护。本报告明确登记了这些缺口，但未实现它们的消费或拒绝闭环。

**所需主控裁决**：是否仅对 pytest 的临时 staging 豁免“所有写入都在 worktree 内”，允许专用仓库外临时目录（建议 `/var/tmp/ea2_astra_pytest`，不是其他 worktree）？本次未创建或写入该目录。若不豁免，应由主控调整本单全量验收边界；施工方不能自行改隔离门或把失败测试跳过。收到目录例外后，才能继续完整源入口改造及五条硬验收。
