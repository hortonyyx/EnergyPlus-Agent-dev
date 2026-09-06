# E-a′ 开工消费盘点（HEAD 363844b3，未改生产代码）

枚举口径：逐读生产 assemble() 与 schema 类型，再合并 sm25 1F/2F、sm24 1F 三份真实产物的全部路径。共 202 行（含容器），`[]` 表示列表元素、`*` 表示动态键，轴 x/y 分开列。源哈希及各集合数量见 source_inventory.json；机器枚举见 field_paths.json。此表记录开工现状，不表示接线完成。

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
