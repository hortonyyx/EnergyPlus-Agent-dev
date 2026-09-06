# E-a′ 源契约施工交件

日期：2026-09-06。工作目录：`/tmp/ea2_astra`；分支：`wt/09.06d_ea2_source_contract`；开工 HEAD：`363844b3`。

**E-a-1..E-a-5 已完成并实测能变红。** 平面侧原生消费 `as_drawn_plan_v2`，没有 v2→v0 转换层，没有新增墙配对算法。完整消费表为下节全部 202 行；施工前表保留为历史证据。

恢复后的未改代码基线为 **3907 passed / 2 skipped / 13 xfailed / 0 failed / 0 errors**。最终全量为 **3942 passed / 2 skipped / 13 xfailed / 0 failed / 0 errors**，新增 35 条，逐位闭合见 §5。

## 1. 自检、基线与授权边界

开工自检原文：

```text
/tmp/ea2_astra
363844b3
/tmp/ea2_astra/src/agent/correction/tick_claim.py
199 AI_agent/logs/reviews/request/2026-09-06d_Ea2_source_contract_dispatch.md
```

完整读过 199 行派工单。派工单的 `8c66e3fd` 是用户指定开工 HEAD `363844b3` 的直接父提交，遵照用户指定 HEAD 开工；未发现本 worktree 中的 AGENTS.md。

原停报已由用户受理为派工边界错误（第 71 次）：允许 pytest/隔离门使用 `/var/tmp/ea2_astra_pytest`。在任何生产改动前，用该 staging 重跑，恢复到 3907。没有修改测试或隔离门来凑绿；代码、交件一直留在本 worktree。历史失败日志仍保留，不能把其 300 failed / 140 errors 当成当前结果。[恢复记录](2026-09-06d_Ea2_evidence/resumption.md)、[恢复全量原文](2026-09-06d_Ea2_evidence/authorized_baseline.log)。

最终全量前再核两个 import，原文如下；[文件](2026-09-06d_Ea2_evidence/final_import_paths.log)：

```text
/tmp/ea2_astra/src/agent/correction/tick_claim.py
/tmp/ea2_astra/src/agent/correction/opening_adjudication.py
```

| 真实源产物 | 面线 | 全部候选对 | 模型选中对 | 空档候选 | 状态 |
|---|---:|---:|---:|---:|---|
| sm25 1F v2 | 49 | 374 | 22 | 85 | SELECTED |
| sm25 2F v2 | 46 | 303 | 21 | 87 | SELECTED |
| sm24 1F v2 | 98 | 1185 | 8 | 87 | SELECTED |

三份原文件的 SHA-256 均与开工 [source_inventory.json](2026-09-06d_Ea2_evidence/source_inventory.json) 相同。真实产物测试逐个枚举 85/87/87 个候选的全部两端，保留源 bytes，通过 submit/consume；未重写源产物或签字基线。`SCHEMA` 定义仍在 `reading/as_drawn/schema.py:112`，由 `as_drawn_v2.py:66` 转出。

B 层措辞记录保留：候选图的“无阈值”指无间距/声明厚度准入阈值；生产枚举本身另有同轴、支撑不重叠、最小沿线重叠等测量条件。本单不改生产候选枚举，也不新增选择阈值。

## 2. 完整消费对照表（头号交付物，202 行）

枚举范围为生产 assemble/schema 与三份真实产物全部路径并集，含容器、数组元素 `[]` 和动态键 `*`。已与 [field_paths.json](2026-09-06d_Ea2_evidence/field_paths.json) 逐项核对：202/202，无遗漏、无重复。[开工表](2026-09-06d_Ea2_evidence/consumption_before.md) 和 [施工后独立副本](2026-09-06d_Ea2_evidence/consumption_after.md) 同时保留。

“结构上不必”指不以该字段直接产生几何；不是可以丢证据，也不等于其内容已经校验。下表明确区分取数、模型提示、仅保存 bytes；Any/deferred 语义尚无人拦截的地方逐行明示。

| 生产格式的字段 | 谁该消费它 | 现在消费了吗 | 若「结构上不必」——被绕过后坏数据流到哪、谁接住 |
|---|---|---|---|
| `declarations` | reading 声明、刻度表达式及墙编译器 | 已分项消费尺寸链和厚度；完整声明同时写入 native_plan/source_declarations | 非整体免消费；执行操作数由 TickSession 核原点/方向/正段/闭合/源哈希；图框等非操作数的语义缺口见各子行。 |
| `declarations.chains` | tick_claim._native_chains、evaluate；刻度认领模型 | 已原生取链 ID、axis、direction、values_mm、world_start_mm；计算前缀和供模型选节点，无墙配对转换 | 非免消费；缺链、错轴/方向、非正段、未闭合或跨源引用由命名 TickClaimError 接住；候选近邻不会自动成为事实。 |
| `declarations.chains.*` | tick_claim._native_chains、evaluate；刻度认领模型 | 已原生取链 ID、axis、direction、values_mm、world_start_mm；计算前缀和供模型选节点，无墙配对转换 | 非免消费；缺链、错轴/方向、非正段、未闭合或跨源引用由命名 TickClaimError 接住；候选近邻不会自动成为事实。 |
| `declarations.chains.*.axis` | tick_claim._native_chains、evaluate；刻度认领模型 | 已原生取链 ID、axis、direction、values_mm、world_start_mm；计算前缀和供模型选节点，无墙配对转换 | 非免消费；缺链、错轴/方向、非正段、未闭合或跨源引用由命名 TickClaimError 接住；候选近邻不会自动成为事实。 |
| `declarations.chains.*.direction` | tick_claim._native_chains、evaluate；刻度认领模型 | 已原生取链 ID、axis、direction、values_mm、world_start_mm；计算前缀和供模型选节点，无墙配对转换 | 非免消费；缺链、错轴/方向、非正段、未闭合或跨源引用由命名 TickClaimError 接住；候选近邻不会自动成为事实。 |
| `declarations.chains.*.ref_coord_m` | reading 定标/转录；模型复核声明 | 结构上不直接产生洞口端点；完整保留在源 bytes 与 native_plan/source_declarations | 错误图框、声明零点、ref_coord 或备注可进审计；本链不重做像素定标，也不验证这些 Any 字段真伪。坐标只取经认领的源 *_m/带链身份的操作数。 |
| `declarations.chains.*.values_mm` | tick_claim._native_chains、evaluate；刻度认领模型 | 已原生取链 ID、axis、direction、values_mm、world_start_mm；计算前缀和供模型选节点，无墙配对转换 | 非免消费；缺链、错轴/方向、非正段、未闭合或跨源引用由命名 TickClaimError 接住；候选近邻不会自动成为事实。 |
| `declarations.chains.*.world_start_mm` | tick_claim._native_chains、evaluate；刻度认领模型 | 已原生取链 ID、axis、direction、values_mm、world_start_mm；计算前缀和供模型选节点，无墙配对转换 | 非免消费；缺链、错轴/方向、非正段、未闭合或跨源引用由命名 TickClaimError 接住；候选近邻不会自动成为事实。 |
| `declarations.drawing_box_px` | reading 定标/转录；模型复核声明 | 结构上不直接产生洞口端点；完整保留在源 bytes 与 native_plan/source_declarations | 错误图框、声明零点、ref_coord 或备注可进审计；本链不重做像素定标，也不验证这些 Any 字段真伪。坐标只取经认领的源 *_m/带链身份的操作数。 |
| `declarations.thickness_callout_note` | reading 定标/转录；模型复核声明 | 结构上不直接产生洞口端点；完整保留在源 bytes 与 native_plan/source_declarations | 错误图框、声明零点、ref_coord 或备注可进审计；本链不重做像素定标，也不验证这些 Any 字段真伪。坐标只取经认领的源 *_m/带链身份的操作数。 |
| `declarations.thickness_callouts_mm` | 墙编译器的模型候选；刻度 full/half-wall 表达式 | 已消费；原生 JSON pointer + source_sha 定位完整厚度；只有显式表达式/模型决策才用于算术 | 非免消费；域/索引/哈希/正厚度/半厚网格检查在 evaluate；不按厚度另配墙；原文字是否读对仍由 reading/模型负责。 |
| `declarations.world_zero_px_declared` | reading 定标/转录；模型复核声明 | 结构上不直接产生洞口端点；完整保留在源 bytes 与 native_plan/source_declarations | 错误图框、声明零点、ref_coord 或备注可进审计；本链不重做像素定标，也不验证这些 Any 字段真伪。坐标只取经认领的源 *_m/带链身份的操作数。 |
| `hypotheses` | 证据适配器、墙编译器、TickSession、OpeningReview | 已消费并完整留在空间复核 packet；选中对、四桶、逐 gap 裁决各有门 | 非免消费；源契约门与全引用/全处置门先行；每个候选须 bind/same_opening/not_opening/register，不能静默漏项。 |
| `hypotheses.ambiguous_face_lines` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `hypotheses.ambiguous_face_lines.*` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `hypotheses.family_roles` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.achromatic_only` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.assignment` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.assignment.*` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.chromaticity` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.pct_of_ink` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.shape` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.shape.area_px_max` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.shape.area_px_median` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.shape.components` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.shape.elongated_fraction` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.shape.fill_ratio_median` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.evidence.*.shape.longest_extent_px` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.family_roles.source` | reading 感知模型；洞口模型复核墨色角色 | 结构上不按色彩统计直接生成窗；完整传入 native_plan/source_hypotheses 供复核 | 这是生产类型登记的 deferred Any；坏值仍能进入复核 packet，无本链语义拦截。代码不按此字段分类/重配；实体必须有显式候选处置，窗还须源 opening_types=window。 |
| `hypotheses.non_wall_face_lines` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `hypotheses.non_wall_face_lines.*` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `hypotheses.note` | 源审计；洞口裁决模型理解方法与来源 | 结构上不解释自然语言生成几何；这些 basis/source/note 字段完整进入 native_plan/source_hypotheses | 坏备注可进复核 packet，当前无自然语言真伪门；任何备注都不能绕过 SELECTED、宿主、逐候选处置、当前批次及端点操作数校验。 |
| `hypotheses.opening_candidates` | TickSession 原生边全集；OpeningReview 候选/宿主/身份裁决 | 已逐候选读 id、face_line、gap_index、span_m；两端保留原生 pointer；全 gap 一一覆盖；逐项模型处置 | 非免消费；未知面/索引由证据门，重复/漏 gap、副本漂移、倒区间由 TickSession；宿主仅取选中墙，别名必须显式指定同墙 primary。 |
| `hypotheses.opening_candidates[]` | TickSession 原生边全集；OpeningReview 候选/宿主/身份裁决 | 已逐候选读 id、face_line、gap_index、span_m；两端保留原生 pointer；全 gap 一一覆盖；逐项模型处置 | 非免消费；未知面/索引由证据门，重复/漏 gap、副本漂移、倒区间由 TickSession；宿主仅取选中墙，别名必须显式指定同墙 primary。 |
| `hypotheses.opening_candidates[].face_line` | TickSession 原生边全集；OpeningReview 候选/宿主/身份裁决 | 已逐候选读 id、face_line、gap_index、span_m；两端保留原生 pointer；全 gap 一一覆盖；逐项模型处置 | 非免消费；未知面/索引由证据门，重复/漏 gap、副本漂移、倒区间由 TickSession；宿主仅取选中墙，别名必须显式指定同墙 primary。 |
| `hypotheses.opening_candidates[].gap_index` | TickSession 原生边全集；OpeningReview 候选/宿主/身份裁决 | 已逐候选读 id、face_line、gap_index、span_m；两端保留原生 pointer；全 gap 一一覆盖；逐项模型处置 | 非免消费；未知面/索引由证据门，重复/漏 gap、副本漂移、倒区间由 TickSession；宿主仅取选中墙，别名必须显式指定同墙 primary。 |
| `hypotheses.opening_candidates[].id` | TickSession 原生边全集；OpeningReview 候选/宿主/身份裁决 | 已逐候选读 id、face_line、gap_index、span_m；两端保留原生 pointer；全 gap 一一覆盖；逐项模型处置 | 非免消费；未知面/索引由证据门，重复/漏 gap、副本漂移、倒区间由 TickSession；宿主仅取选中墙，别名必须显式指定同墙 primary。 |
| `hypotheses.opening_candidates[].ink_by_family` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].ink_by_family.*` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].ink_by_family.*.by_distance_px` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].ink_by_family.*.by_distance_px.*` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].ink_by_family.*.nearest_px` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].ink_by_family.*.on_line` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].ink_by_family.*.span_ratio` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].len_m` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].len_px` | reading 量具、刻度/洞口复核模型；require_v2_plan 核冗余副本 | 已核类型并逐项比较被引用 face.gaps 的同名值；墨迹进 Edge.witness 与 native_plan，长度不替代端点 | 不以统计阈值生成洞口；两份同时伪造的同值测量仍可到模型，当前不重采像素。几何宽度来自被认领两端，不把 len_m/墨色当答案。 |
| `hypotheses.opening_candidates[].span_m` | TickSession 原生边全集；OpeningReview 候选/宿主/身份裁决 | 已逐候选读 id、face_line、gap_index、span_m；两端保留原生 pointer；全 gap 一一覆盖；逐项模型处置 | 非免消费；未知面/索引由证据门，重复/漏 gap、副本漂移、倒区间由 TickSession；宿主仅取选中墙，别名必须显式指定同墙 primary。 |
| `hypotheses.opening_candidates_basis` | 源审计；洞口裁决模型理解方法与来源 | 结构上不解释自然语言生成几何；这些 basis/source/note 字段完整进入 native_plan/source_hypotheses | 坏备注可进复核 packet，当前无自然语言真伪门；任何备注都不能绕过 SELECTED、宿主、逐候选处置、当前批次及端点操作数校验。 |
| `hypotheses.opening_types` | 感知模型的门/窗/非洞口命名；实体裁决 | 已消费；未知 candidate ID 拒绝；bind 输出 WindowV3 要求源类型 window；其他候选显式登记/判非洞口 | 非免消费；PLAN_WINDOW_CLASSIFICATION_REQUIRED 拦未定类型/门冒充窗；本载体不装配门。模型语义误判不是代码用尺寸/墨色阈值补判。 |
| `hypotheses.opening_types.*` | 感知模型的门/窗/非洞口命名；实体裁决 | 已消费；未知 candidate ID 拒绝；bind 输出 WindowV3 要求源类型 window；其他候选显式登记/判非洞口 | 非免消费；PLAN_WINDOW_CLASSIFICATION_REQUIRED 拦未定类型/门冒充窗；本载体不装配门。模型语义误判不是代码用尺寸/墨色阈值补判。 |
| `hypotheses.opening_types_source` | 源审计；洞口裁决模型理解方法与来源 | 结构上不解释自然语言生成几何；这些 basis/source/note 字段完整进入 native_plan/source_hypotheses | 坏备注可进复核 packet，当前无自然语言真伪门；任何备注都不能绕过 SELECTED、宿主、逐候选处置、当前批次及端点操作数校验。 |
| `hypotheses.pair_candidates` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates[]` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates[].face_a` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates[].face_b` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates[].matched_declared_mm` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates[].overlap_px` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates[].spacing_m` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates[].spacing_px` | 证据适配器核完整候选图；模型复核备选 | 已遍历全部端点引用；类型门覆盖每条候选；选中项与候选测量逐项相等；全图进 native_plan | 结构上不从候选图生成配对；未知面由证据门接住，数值仅作复核提示。未选候选的像素统计真伪不在本链重测；本链不增加选择阈值、不自动重配。 |
| `hypotheses.pair_candidates_basis` | 源审计；洞口裁决模型理解方法与来源 | 结构上不解释自然语言生成几何；这些 basis/source/note 字段完整进入 native_plan/source_hypotheses | 坏备注可进复核 packet，当前无自然语言真伪门；任何备注都不能绕过 SELECTED、宿主、逐候选处置、当前批次及端点操作数校验。 |
| `hypotheses.pairs` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[]` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[].face_a` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[].face_b` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[].matched_declared_mm` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[].overlap_px` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[].source` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[].spacing_m` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs[].spacing_px` | 证据适配器读取模型选中对；原有墙编译器与宿主绑定 | 已消费原生选中对；副本除 source 外须与候选完全相等；墙面 source_refs 绑定 gap，墙宽由面位置重算 | 非免消费；悬空/异轴/重复/处置不闭合由证据门；选中副本漂移在 TickSession 拦截；spacing/overlap/厚度标签不驱动新配对；来源文字真伪无代码判官。 |
| `hypotheses.pairs_note` | 源审计；洞口裁决模型理解方法与来源 | 结构上不解释自然语言生成几何；这些 basis/source/note 字段完整进入 native_plan/source_hypotheses | 坏备注可进复核 packet，当前无自然语言真伪门；任何备注都不能绕过 SELECTED、宿主、逐候选处置、当前批次及端点操作数校验。 |
| `hypotheses.pairs_status` | TickSession 与 OpeningReview 原生入口 | 已消费；只有非空 pairs 且状态 SELECTED 能继续 | 非免消费；TICK_PLAN_MODEL_SELECTION_REQUIRED 即时拒绝缺席、空或未完成，不把它们当零墙。 |
| `hypotheses.perception_source` | 源审计；洞口裁决模型理解方法与来源 | 结构上不解释自然语言生成几何；这些 basis/source/note 字段完整进入 native_plan/source_hypotheses | 坏备注可进复核 packet，当前无自然语言真伪门；任何备注都不能绕过 SELECTED、宿主、逐候选处置、当前批次及端点操作数校验。 |
| `hypotheses.solid_band_walls` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `hypotheses.solid_band_walls.*` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `hypotheses.unpaired_wall_faces` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `hypotheses.unpaired_wall_faces.*` | 证据适配器、现有墙编译器；洞口宿主判定 | 已消费四类处置；strict 重编译并比较完整结果及 wall cut lines；通过 source_refs 找候选面所属墙 | 非免消费；引用/重复/覆盖在证据门，未解 open_items 在 OpeningReview 拦截；不成墙的面不能冒充已选宿主，理由文本只保留不猜义。 |
| `image` | reading 图像声明；bundle 身份绑定；审计 | 原字段保留；image 参与补件同源检查；运行身份由 from_artifact 取 source_artifacts[0]，不是标签 | 标签结构上不决定几何；错误标签留在源 bytes，当前无图像内容真伪检查；不能替换 bundle 的 input_id/source_output_sha256。 |
| `image_label` | reading 图像声明；bundle 身份绑定；审计 | 原字段保留；image 参与补件同源检查；运行身份由 from_artifact 取 source_artifacts[0]，不是标签 | 标签结构上不决定几何；错误标签留在源 bytes，当前无图像内容真伪检查；不能替换 bundle 的 input_id/source_output_sha256。 |
| `ledger` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.bridging_applied` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.face_lines` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.faces_with_a_candidate` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.families_assigned` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.families_discovered` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.gap_classified` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.gaps_total` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.opening_candidates` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.opening_types_named` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.pair_candidates` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.pairing_in_observations` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.pairs_selected` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.pairs_status` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.runs_total` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `ledger.unassigned_ink_pct` | reading 账目审计；裁决核实际集合 | 结构上不取汇总生成洞口；保留原 bytes；实际候选/面/墙集合另行遍历、闭合 | 错误汇总仍留在冻结源，无专门 ledger 语义拦截；不能控制候选全集或批次 ID；不得以这些计数替代实际集合，这一 Any 缺口明确保留。 |
| `observations` | 生产类型/证据门；墙编译器；TickSession | 已读 face_lines 及 calibration；dimension_witnesses 留作提示；所有通道源 bytes 一起归档 | 非整体免消费；几何与引用由下列具体门接住；palette/components 等 deferred 通道不因已保存就被宣称验证。 |
| `observations.calibration` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.cross_axis_relative_deviation` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.fill_ratio` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.mm_per_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.profile_bins_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.world_zero_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.world_zero_source` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.x.axis` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.chain_closure_mm` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.cum_mm` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.x.m_per_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.matched_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.max_abs_residual_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.mm_per_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.origin_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.overall_mm` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.x.residual_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.rmse_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.unmatched_ticks_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.x.values_mm` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.y` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.y.axis` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.chain_closure_mm` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.cum_mm` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.y.m_per_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.matched_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.max_abs_residual_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.mm_per_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.origin_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.overall_mm` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.calibration.y.residual_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.rmse_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.unmatched_ticks_px` | reading 像素定标；模型对测量质量的复核 | 结构上不重拟合像素坐标；原字段在 source.bin 原样保存，原点/方向权威来自 declarations.chains | 坏残差/比例/匹配点等可进入源审计，当前不重做 reading 量具校验；它们不升级 evidence tier，pixel_only 仍由显式认领与既有输出网格约束。 |
| `observations.calibration.y.values_mm` | reading 定标；TickSession._chain_records/require_chain | 已消费原生 observations.calibration；对含 values_mm 的链重做正段、域长、总长和前缀和闭合 | 非整体免消费；坏算术链走命名拒绝；权威可选节点取保留 ID 的 declarations.chains，不能拿无链 ID 的测量映射代替。未带 values_mm 的遥测对象仅保留。 |
| `observations.components_by_family` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.components_by_family.*` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.components_by_family.*[]` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.components_by_family.*[].area_px` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.components_by_family.*[].bbox_px` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.dimension_witnesses` | 刻度认领模型的测量提示；不能代替有链 ID 的操作数 | 已将完整原生 map 放入各 Edge.witness；不从丢失 chain ID 的映射反推节点身份 | 结构上不直接用于 evaluate；坏 map 可到模型提示，当前无 map 语义门；可执行候选只从 declarations.chains 与源哈希定位，模型仍须逐端认领。 |
| `observations.dimension_witnesses.x` | 刻度认领模型的测量提示；不能代替有链 ID 的操作数 | 已将完整原生 map 放入各 Edge.witness；不从丢失 chain ID 的映射反推节点身份 | 结构上不直接用于 evaluate；坏 map 可到模型提示，当前无 map 语义门；可执行候选只从 declarations.chains 与源哈希定位，模型仍须逐端认领。 |
| `observations.dimension_witnesses.x.*` | 刻度认领模型的测量提示；不能代替有链 ID 的操作数 | 已将完整原生 map 放入各 Edge.witness；不从丢失 chain ID 的映射反推节点身份 | 结构上不直接用于 evaluate；坏 map 可到模型提示，当前无 map 语义门；可执行候选只从 declarations.chains 与源哈希定位，模型仍须逐端认领。 |
| `observations.dimension_witnesses.y` | 刻度认领模型的测量提示；不能代替有链 ID 的操作数 | 已将完整原生 map 放入各 Edge.witness；不从丢失 chain ID 的映射反推节点身份 | 结构上不直接用于 evaluate；坏 map 可到模型提示，当前无 map 语义门；可执行候选只从 declarations.chains 与源哈希定位，模型仍须逐端认领。 |
| `observations.dimension_witnesses.y.*` | 刻度认领模型的测量提示；不能代替有链 ID 的操作数 | 已将完整原生 map 放入各 Edge.witness；不从丢失 chain ID 的映射反推节点身份 | 结构上不直接用于 evaluate；坏 map 可到模型提示，当前无 map 语义门；可执行候选只从 declarations.chains 与源哈希定位，模型仍须逐端认领。 |
| `observations.face_lines` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[]` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].axis` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].constant_world_axis` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].covered_px` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.face_lines[].edges_m` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].gaps` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[]` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].hi_px` | reading 空档量具；模型像素复核 | 类型已核；原字段保留在源 bytes；本链不由像素边另算洞口米坐标 | 结构上不重复量像素；两像素端的真伪仍到 reading/模型，当前无重测拦截；候选端点须与源 gap.span_m 一致并通过 lo<hi。 |
| `observations.face_lines[].gaps[].ink_by_family` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].ink_by_family.*` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].ink_by_family.*.by_distance_px` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].ink_by_family.*.by_distance_px.*` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].ink_by_family.*.nearest_px` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].ink_by_family.*.on_line` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].ink_by_family.*.span_ratio` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].len_m` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].len_px` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].gaps[].lo_px` | reading 空档量具；模型像素复核 | 类型已核；原字段保留在源 bytes；本链不由像素边另算洞口米坐标 | 结构上不重复量像素；两像素端的真伪仍到 reading/模型，当前无重测拦截；候选端点须与源 gap.span_m 一致并通过 lo<hi。 |
| `observations.face_lines[].gaps[].span_m` | 证据门核 gap 索引；TickSession 核候选副本与全 gap 覆盖 | 已消费 gap 容器及 span_m/len_m/len_px/ink_by_family；所有 gap 必须恰有一个候选且副本相等 | 非整体免消费；错索引、漏 gap、重复、漂移、倒区间分别命名拒绝；墨迹数字共同误测不会被本链重采像素发现，进入模型提示而非阈值分类。 |
| `observations.face_lines[].id` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].ink_coverage_per_run` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.face_lines[].pos_m` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].pos_px` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.face_lines[].runs_m` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].runs_m[]` | 证据引用门、墙编译器；TickSession 的世界轴与宿主绑定 | 已消费；完整面索引与选中对/四桶闭合；墙编译器读面位置/边/段，TickSession 由 constant_world_axis 取沿线轴 | 非免消费；重复/悬空/异轴引用由证据门，未解墙决策及非本源 cut lines 在 Review 拦截；轴或位置误测仍可能保持内部一致，本链不替 reading 重测。 |
| `observations.face_lines[].runs_px` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.face_lines[].runs_px[]` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.face_lines[].support_cols_px` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.face_lines[].support_px` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.face_lines[].support_width_m` | reading 像素量具；证据引用及墙复核审计 | 生产类型逐字段核形状；适配器保留 support_cols_px/runs_px 等证据指针；源 bytes 完整落盘 | 结构上不靠覆盖率/像素宽阈值配墙或分类；这些测量的真伪及跨字段数值关系不在本链全面重算，坏值可到证据/模型审计；墙宿主仍受选中对和处置门约束。 |
| `observations.ink_palette` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.achromatic_only` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.chroma_steps` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.distinct_rgb_values` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[]` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].assign_distance_p50` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].assign_distance_p95` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].brightness_median` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].cells_merged` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].chromaticity` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].core_chromaticity` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].id` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].max_merge_distance` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].pct_of_ink` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].px` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].shape` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].shape.area_px_max` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].shape.area_px_median` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].shape.components` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].shape.elongated_fraction` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].shape.fill_ratio_median` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].shape.longest_extent_px` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.families[].spread` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.ink_px` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.merge_dist` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.min_share` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `observations.ink_palette.unassigned_pct` | reading 墨迹分组量具；感知模型的测量背景 | 结构上不据调色板/连通域生成洞口；原样保存在 TickPacket/source.bin，未把保存冒充语义消费 | 生产类型已登记 deferred Any；坏值可进源审计，当前无本链语义拦截。代码不取颜色/形状阈值判墙判窗，gap 的墨迹副本另见逐项复核行。 |
| `schema` | 生产类型、分类器、TickSession 原生分支 | 已消费；导入 schema.SCHEMA；require_v2_plan 复用原分类器，缺 hypotheses 走已命名拒绝 | 非免消费；不匹配、畸形注册值或歧义均不能借 legacy 键回退；分类器公开行为未改。 |

## 3. 实现与强制路径

生产改动只有四个文件，测试为两个新增文件；`src/agent/reading`、`src/agent/judge` 和旧 `gt` 相对开工基点均无 diff，因此分类器判定/返回/异常面及 §四禁改文件保持不变。

- `tick_claim.py:166` 的 require_v2_plan 先复用生产类型分类器和证据门，再检查 SELECTED 非空、选中副本一致、候选与 gap 一一闭合及端点有序；`:416` 的原生分支直接读 `/hypotheses/opening_candidates/.../span_m`，没有 wall_bands 中间件。
- `tick_claim.py:212` 从原生 declarations.chains 计算有链 ID 的前缀和；厚度操作数引用 `/declarations/thickness_callouts_mm` 和源哈希。这里只做声明算术，不做墙身份或空档归并。
- `opening_adjudication.py:257` 复用现有 strict 墙编译器及其固定模型决定，重建完整结果并核 cut lines；候选宿主从 `hypotheses.pairs`/四类处置的 source_refs 追溯。每个空档须由模型显式 bind/same_opening/not_opening/register；不按区间重叠自动并洞口。
- `opening_adjudication.py:432` 装配先 consume，再 scoreable_openings；`:453` 保存空间 packet/result 及各独立 tick archive。`pipeline.py:1347` 是可执行生产入口；`:1526` 的 run_correction evidence-chain 路由实际调用它。历史 dict 被拒绝，进 judge 前的该导出入口必须 strict；完整 run_correction 仍先过原有 strict projection 门。
- `tick_claim.py:557` 从验证过的 bundle.source_artifacts[0] 建 TickSession，冻结 artifact 快照；`:587` 保存原 source.bin、可选原 supplement.bin、batch.json 原 record、packet.json、history.json 和 manifest，`:823` 从字节重建并验证 batch_id。源未提供 supplement 时 manifest 明示 false，绝不捏造第二份来源；审计重建只返回 TickBatch，不授予当前 TickSession 权限。
- `opening_synthesis.py:1253` 的新生产入口要求当前 TickSession。身份与债务只取已验证 bundle；旧数值实现收为内部函数，历史 dict API 仍可被历史测试调用。无 artifact 的历史路径不获身份、不能退债；既有 B4 无声明不退债锁仍通过。朝向仍经 `facade_convention.resolve_sign`（`:1070`），不在调用点造另一套规则。
- `opening_adjudication.py:326` 复用 facade_visibility 的可见区间；凹进 South 墙 pos=0.5、全局 y_min=-0.5 仍可见的正例通过，遮挡反例拒绝。触碰 `_elevation_document` 后，`:144` 委托 `tick_claim.py:621`，后者补了立面 lo<hi 对称消费检查。
- v0 分支未删除。`tick_claim.py:26` 明确登记唯一产出方为 `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/as_drawn.py`，`:440` 分支注释引用登记；`tests/test_ea2_native_tick.py:101` 锁实验产出方和历史源仍可读取。没有声称“删掉也全绿”，本单未做删除实验。

完整真实入口锁在 `tests/test_ea2_opening_pipeline.py:212`：原生 schema 合成楼层、模型固定回复、由立面 bytes 派生的层高，实际经过 run_correction 的证据循环、strict 投影、当前 Review 和 V3 装配；随后使立面 batch 过期，原入口命名拒绝。没有 mock 装配或持久化函数。新夹具调试中暴露的非整数像素、无效 witness 标签及墙端越过角点均在新增夹具内修正；未放宽任何生产门或修改既有测试。

## 4. E-a-1..E-a-5 当场变红证明

正例与反例均已执行。完整变异脚本：[prove_guards_red.py](2026-09-06d_Ea2_evidence/prove_guards_red.py)；每组源补丁、实际 pytest 命令、汇总：[red_proofs.json](2026-09-06d_Ea2_evidence/red_proofs.json)。脚本只临时替换一处防线，在 finally 中逐字节恢复源；恢复后最终全量全绿。

复现实验必须独占本 worktree 的跑测时段：

```sh
cd /tmp/ea2_astra
python AI_agent/logs/reviews/execution/2026-09-06d_Ea2_evidence/prove_guards_red.py
```

### E-a-1

锁：`tests/test_ea2_opening_pipeline.py:118`（`test_ea1_pipeline_rejects_stale_batch`）。强制行：pipeline.py:1363 → OpeningReview.assemble_geometry:435/436 → consume:422 的当前性复核。变异把 _check_current 改为 pass。过期立面在原实现装配前即拒绝且不落盘；关闭消费防线后直到落盘端才被 TickSession 拦截，已经产生 stale 目录，锁因此变红。此证据证明装配前消费门有牙齿，不把落盘端补救当成装配门已生效。

变异后的实际命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/mutation_E-a-1 tests/test_ea2_opening_pipeline.py::test_ea1_pipeline_rejects_stale_batch
```

原文摘录（[完整输出](2026-09-06d_Ea2_evidence/red_E-a-1.log)）：

```text
E       AssertionError: assert not True
E        +  where True = exists()
E        +    where exists = (PosixPath('/var/tmp/ea2_astra_pytest/mutation_E-a-1/popen-gw0/test_ea1_pipeline_rejects_stal0') / 'stale').exists
FAILED tests/test_ea2_opening_pipeline.py::test_ea1_pipeline_rejects_stale_batch
1 failed in 3.48s
```

### E-a-2

锁：`tests/test_ea2_opening_pipeline.py:130`（`test_ea2_pipeline_archive_rebuilds_every_batch_byte_for_byte`）。强制行：pipeline.py:1365 → OpeningReview.persist:453 → TickSession.persist:587/verify_tick_archive:823。变异去掉 review.persist，只创建预览输出目录；正例随即缺 source.bin。原实现的正例逐字节比较两源通道与 batch.record，并重建两个批次的 ID。

变异后的实际命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/mutation_E-a-2 tests/test_ea2_opening_pipeline.py::test_ea2_pipeline_archive_rebuilds_every_batch_byte_for_byte
```

原文摘录（[完整输出](2026-09-06d_Ea2_evidence/red_E-a-2.log)）：

```text
E       FileNotFoundError: [Errno 2] No such file or directory: '/var/tmp/ea2_astra_pytest/mutation_E-a-2/popen-gw0/test_ea2_pipeline_archive_rebu0/opening_batches/a88d0fda12148711313d513f075e8267b6ef77a4ed1570f5de9e17f4623f8898/060cf2110da3a1477106ca80edb3aec9bec005b50bfad39000aeb17c1e01c408/source.bin'
FAILED tests/test_ea2_opening_pipeline.py::test_ea2_pipeline_archive_rebuilds_every_batch_byte_for_byte
1 failed in 3.50s
```

### E-a-3

锁：`tests/test_ea2_opening_pipeline.py:146`（`test_ea3_no_production_call_to_historical_dict_api`）。强制锁为 grep 扫描 src/scripts 下所有 Python 的旧 API 调用，排除其定义。变异在 pipeline 增加一个旧 dict API 调用，grep 立即检出。该锁针对字面生产调用，不能声称防御任意动态反射调用。

变异后的实际命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/mutation_E-a-3 tests/test_ea2_opening_pipeline.py::test_ea3_no_production_call_to_historical_dict_api
```

原文摘录（[完整输出](2026-09-06d_Ea2_evidence/red_E-a-3.log)）：

```text
E       AssertionError: ['src/agent/pipeline.py:1348:    synthesize_openings(elevation_doc={})']
E       assert not ['src/agent/pipeline.py:1348:    synthesize_openings(elevation_doc={})']
FAILED tests/test_ea2_opening_pipeline.py::test_ea3_no_production_call_to_historical_dict_api
1 failed in 3.36s
```

### E-a-4

锁：`tests/test_ea2_native_tick.py:42`（`test_ea4_model_selection_required`）。强制行：tick_claim.py:183。变异关闭非空/SELECTED 门；即使四桶已经完整记账，空列表仍不得成为零墙。四个参数分支中三条被放行、None 跌入非命名迭代错误，全部变红。

变异后的实际命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/mutation_E-a-4 tests/test_ea2_native_tick.py::test_ea4_model_selection_required
```

原文摘录（[完整输出](2026-09-06d_Ea2_evidence/red_E-a-4.log)）：

```text
E       TypeError: 'NoneType' object is not iterable
E       Failed: DID NOT RAISE <class 'src.agent.correction.tick_claim.TickClaimError'>
FAILED tests/test_ea2_native_tick.py::test_ea4_model_selection_required[None-ABSENT_NO_MODEL_SELECTION]
FAILED tests/test_ea2_native_tick.py::test_ea4_model_selection_required[keep-None]
FAILED tests/test_ea2_native_tick.py::test_ea4_model_selection_required[pairs0-SELECTED]
FAILED tests/test_ea2_native_tick.py::test_ea4_model_selection_required[keep-SELECTED_INCOMPLETE]
4 failed in 2.94s
```

### E-a-5

锁：`tests/test_ea2_native_tick.py:59`（`test_ea5_missing_hypotheses_named_refusal`）。强制行：tick_claim.py:180/181。变异关闭分类器拒绝门；无 hypotheses（含同时带 legacy strokes 的版本）跌入 KeyError，不能满足已命名拒绝要求，两条都红。

变异后的实际命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/mutation_E-a-5 tests/test_ea2_native_tick.py::test_ea5_missing_hypotheses_named_refusal
```

原文摘录（[完整输出](2026-09-06d_Ea2_evidence/red_E-a-5.log)）：

```text
E       KeyError: 'hypotheses'
FAILED tests/test_ea2_native_tick.py::test_ea5_missing_hypotheses_named_refusal[True]
FAILED tests/test_ea2_native_tick.py::test_ea5_missing_hypotheses_named_refusal[False]
2 failed in 2.71s
```

### visibility

锁：`tests/test_ea2_opening_pipeline.py:190`（`test_recessed_visible_wall_is_not_replaced_by_bbox_extreme`）。附加硬约束：把 South 可见墙强制限制为全局 bbox 最低面；凹进但可见的正例立即被错拒，证明原实现使用可见区间。

变异后的实际命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/mutation_visibility tests/test_ea2_opening_pipeline.py::test_recessed_visible_wall_is_not_replaced_by_bbox_extreme
```

原文摘录（[完整输出](2026-09-06d_Ea2_evidence/red_visibility.log)）：

```text
E           src.agent.correction.tick_claim.TickClaimError: MUTATION_BBOX_EXTREME: None
FAILED tests/test_ea2_opening_pipeline.py::test_recessed_visible_wall_is_not_replaced_by_bbox_extreme
1 failed in 3.27s
```

### A-6-d1

锁：`tests/test_ea2_opening_pipeline.py:182`（`test_elevation_consumer_rechecks_order_when_upstream_guard_is_bypassed`）。附加对称锁：使上游 consume 暂时返回退化区间，再关闭 elevation_document 内的 lo<hi 检查；消费者不再拒绝，锁变红。

变异后的实际命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/mutation_A-6-d1 tests/test_ea2_opening_pipeline.py::test_elevation_consumer_rechecks_order_when_upstream_guard_is_bypassed
```

原文摘录（[完整输出](2026-09-06d_Ea2_evidence/red_A-6-d1.log)）：

```text
E       Failed: DID NOT RAISE <class 'src.agent.correction.tick_claim.TickClaimError'>
FAILED tests/test_ea2_opening_pipeline.py::test_elevation_consumer_rechecks_order_when_upstream_guard_is_bypassed
1 failed in 3.48s
```

## 5. 跑测与逐位闭合

未改生产代码、解除 staging 冲突后的命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/authorized_baseline
```

[完整原文](2026-09-06d_Ea2_evidence/authorized_baseline.log) 的汇总行：

```text
3907 passed, 2 skipped, 13 xfailed, 211 warnings in 468.57s (0:07:48)
```

恢复后 3907+2+13=3922；原停报 3467+300+140+2+13=3922，差额 0。仅 staging 冲突解除和仓内试跑临时目录清理，便让 440 个失败/错误恢复为通过。

最终全量命令（变异已全部恢复，生产代码检查点 `95d79cef`）：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -q -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/final_full
```

[完整原文](2026-09-06d_Ea2_evidence/final_full.log) 的完整汇总行：

```text
3942 passed, 2 skipped, 13 xfailed, 211 warnings in 479.47s (0:07:59)
```

**0 failed / 0 errors；3942+2+13=3957。** 新增 test_ea2_native_tick 24 条、test_ea2_opening_pipeline 11 条，共 35 条；3907+35=3942，3922+35=3957，两种口径差额均为 0，原 2 skipped / 13 xfailed 不变。[独立收集原文](2026-09-06d_Ea2_evidence/new_collection.log) 为 `35 tests collected in 1.45s`。本单未更改任何既有测试。

相关阶段原文：[原生刻度 54 passed](2026-09-06d_Ea2_evidence/native_tick.log)、[字节归档 62 passed](2026-09-06d_Ea2_evidence/tick_archive.log)、[既有 B4/A-6 46 passed](2026-09-06d_Ea2_evidence/current_b4.log)、[最终新增锁 35 passed](2026-09-06d_Ea2_evidence/entry_visibility.log)。阶段集合有重叠，不相加冒充全量。

## 6. 自设两条同形绕过路径

路径一：昨天的 spatial_result.json 自洽，调用者把 parse 后的 dict 当作当前 Review 送进真实 pipeline。`tests/test_ea2_opening_pipeline.py:154` 实测 `CURRENT_OPENING_REVIEW_REQUIRED`；同一锁还实测 exploratory 被 `OPENING_JUDGE_STRICT_REQUIRED` 拒绝。历史 JSON 没有当前会话的授权。

路径二：攻击者改 source.bin，顺手更新 manifest 的外层哈希，仍拿旧 batch.json 冒充重建成功。`tests/test_ea2_native_tick.py:166` 实测 `OPERAND_CROSS_IMAGE`；原生链操作数仍绑旧源哈希，重算外层校验不能洗掉内部来源关系。

两条另行执行的命令：

```sh
TMPDIR=/var/tmp/ea2_astra_pytest python -m pytest -v -n 6 -p no:cacheprovider --basetemp=/var/tmp/ea2_astra_pytest/bypass_paths tests/test_ea2_opening_pipeline.py::test_pipeline_never_treats_historical_json_as_current_review tests/test_ea2_native_tick.py::test_archive_rehashed_manifest_cannot_launder_changed_source
```

[原文](2026-09-06d_Ea2_evidence/bypass_paths.log)：

```text
[gw0] [ 50%] PASSED tests/test_ea2_opening_pipeline.py::test_pipeline_never_treats_historical_json_as_current_review
[gw1] [100%] PASSED tests/test_ea2_native_tick.py::test_archive_rehashed_manifest_cannot_launder_changed_source
============================== 2 passed in 4.81s ===============================
```

## 7. 最薄弱处与实测边界

最薄弱处是原始测量和模型语义的真实性：palette、components、ledger、部分 calibration/declarations 仍是生产类型明确 deferred 的通道；有些坏数据能进入源审计或模型提示，保存哈希并不证明其正确。全部具体去向和“谁未接住”已写在消费表末列，没有把它们报成全面验证。

本单的真实三源证据覆盖原生全集读取与 submit/consume；完整 strict pipeline 装配使用合法原生 schema 的合成建筑、固定模型答复，验证的是源契约/当前性/装配/持久化接线，**没有声称已经完成 sm25/sm24 整栋的在线跨立面模型复盘**。本导出载体是 WindowV3：源声明 window 才可 bind；门、未定类空档须显式登记，不能默转成窗；推测和待定结果不会进 scoreable_openings。

空间 Review 还要求调用方提供已纠正楼层几何并冻结其内容；真实 run_correction 会比对其刚得到的 strict 投影。可见性的凹进/遮挡测试单独改变提供的 footprint 以检验几何算法，不能拿该合成 footprint 声称真实 reading 的轮廓正确。

## 8. 分段提交

| 提交 | 独立小步 |
|---|---|
| fb64b7a4 | 开工完整 202 行消费盘点 |
| da89e8a4 | 已受理的工作目录/staging 冲突停报证据 |
| f80e3b52 | staging 口径更正后 3907 原基线恢复 |
| 631f6afb | 原生 v2 刻度入口及源拒绝门 |
| c182f761 | bundle 身份与可重建字节归档 |
| 33a65eee | B4 与入口阶段的已通过日志（该提交仅含日志） |
| fac0153f | 当前 Review → B4 → V3 生产接线代码与锁 |
| 257b41a2 | strict 真入口、可见性与绕过锁 |
| 95d79cef | 五项硬验收及两项附加变红原文 |

本报告、完整施工后消费表和最终全量证据作为最后的文档小步提交。每次均逐路径 add，并在 commit 前检查 git diff --cached --numstat；未用 git add -A、pip install、site-packages 写入或 -n auto。
