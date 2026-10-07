# Q1-H 离线重放笔记

本文件只记录 H 的输入、口径和执行边界。`replay.py` 只调用生产规整 API，不另写一套规整算法；所有评测均为离线，模型请求为 0。

## 输入清单

### 真实 work model 交付

只读主树 `C:/Users/Horton/Desktop/EnergyPlus-Agent-dev/AI_agent/archive/local_backup/cmp3/`：

| 运行 | 交付候选 | 平面稿数 |
|---|---:|---:|
| `sm21_role` | `candidate_09` | 4 |
| `sm21_single` | `candidate_05` | 3 |
| `sm24_role` | `candidate_05` | 1 |
| `sm24_single` | `candidate_18` | 4 |
| `sm25_role` | `candidate_13` | 6 |
| `sm25_single` | `candidate_62` | 16 |

每项读取 `bim/delivery.json`、选中候选的 `source_model.json`、`bim/plan_drafts/*/plan.json`。分工模式另可读取 `tasks/*/bim/trial_workspace/plan_drafts/*/plan.json`。禁止读取或修改主树 `merged`、D 盘 `runs-next`、`runs-cc`。

### 合法历史重放

10-01 Opus 开发辅助亲做三例：

- `AI_agent/logs/experiments/2026-10-01_opus_dev_sm21`
- `AI_agent/logs/experiments/2026-10-01_opus_dev_sm24`
- `AI_agent/logs/experiments/2026-10-01_opus_dev_sm25`

此前 Claude Code 较好成果：

- `2026-09-26_sm25_height_cold_claude_run53`
- `2026-09-26_sm25_height_repeat_claude_run54`
- `2026-09-26_sm24_whole_building_claude_run55`
- `2026-09-26_sm24_whole_building_repeat_claude_run56`
- `2026-09-26_sm21_whole_building_claude_run57`
- `2026-09-27_sm21_whole_building_repeat_claude_run58`

以上目录选择与 `2026-10-05_absorb_a4t/replay.py::sources()` 一致。它们用于检验新规则没有破坏原本合法的平面、房间、门窗和连通，不当作本轮真实 work model 成果。

### E/F 真实试建与开发辅助

- sm24 平面读图员 run3：`C:/Users/Horton/Desktop/EnergyPlus-Agent-dev/AI_agent/archive/local_backup/plan_reader_probe/run3`
- sm24 分工整案 run3：`.../archive/local_backup/role_debug/sm24_run3`
- sm24 分工整案 run7：`.../archive/local_backup/role_debug/sm24_run7`
- sm21 分工整案 run1（两层）：`.../archive/local_backup/role_debug/sm21_run1`
- cmp3 sm25 分工（两层）：`.../archive/local_backup/cmp3/sm25_role/tasks/*/bim/trial_workspace`

F 的尺寸数字只从运行所用原图的可见标注区域人工读取，写成 `dev_auxiliary` fixture；不得从 GT 或评价结果反推输入。先用 `view_image` 逐张看原图，再在原图上按绿色尺寸界线读像素位置；像素扫描只确认已经看见的尺寸界线，不读取 GT、评价结果或生成模型。读数、像素刻度、方法和原图区域都进报告。

## 复用接口与统计口径

- 历史评价复用 `2026-10-07_three_case_comparison/evaluate.py` 产出的 partition、delivery-quality 结构。
- 三档统计复用 `metrics.py::tiers` 的互斥分桶：`<=5cm`、`>5cm 且 <=10cm`、`>10cm 且 <=30cm`、`>30cm`。
- 房间统计使用匹配数与边界 Hausdorff；门窗位置使用沿墙最大端点误差；另保留宿主、门连接和垂直离墙状态。
- 每次规整逐条记录 `eliminated`、`rejected`、未动的真实 `>=30cm` 分离线、房间/门窗/连通计数变化。
- 被硬约束拒绝且无可交付候选的输入不计算“规整后对 GT 指标”，明确写 `after_metrics_unavailable`，不能把拒绝当改善。

## 生产 API

读图侧最终接口：

- `src.agent.geometry.plan_ink_alignment.align_plan_to_ink(image, plan, *, search_world_m=0.30)`
- `src.agent.geometry.plan_dimension_alignment.align_plan_to_dimensions(plan)`

trial 顺序为墨线后尺寸链。F fixture 从顶层 `dimension_chains` 送入，字段为 `id`、`axis`、`segments_mm`、`total_mm`、`tick_pixels`、`source_refs`；生产函数将可采用的链转换成规整输入并移除临时字段。

kernel 使用 `src.agent.geometry.plan_regularization` 的 `regularize_plan`、`regularize_plan_stack`、`validate_regularized_plan*` 和 `enforce_regularized_plan*`。脚本只调用这些生产实现；失败时额外调用生产 validator 列出原稿违反的对象，不自行修几何。

## 执行计划

1. 解析输入清单并核对文件存在、哈希、交付候选和最终平面稿；缺失项以不可用原因报告。
2. 对每个输入计算旧基线的房间、门窗、连通及三档统计。
3. 调用生产 A-C API，保存逐条规整、拒绝、>=30 cm 保持项和前后计数；再用同一评价路径计算后指标。
4. 对 E 的真实试建调用生产墨线对齐；对 F 的少量开发辅助尺寸链调用生产尺寸链规整，并与真实 work model 成果分栏。
5. 写 `replay_report.json.gz`，并让脚本重复运行所得 JSON 稳定；不跑 pytest、不启动模型、不做全量检查。

如需稳定的小输入副本，只复制必要的 `plan.json`、交付/候选元数据、评价 JSON 与原图裁剪到 `AI_agent/archive/local_backup/q1/`，不复制完整大运行。

## 第二轮最终结果（2026-10-08）

第一轮证据已原样冻结到 `round1/`：报告 SHA256 为 `9a680ff7fd2806f7c0097ad34c4b28d53e5e876ea0aec830ce96d36e3ab9b63b`，笔记为 `a034db2392f4e78aa6028b18cf3b9ce489aab87eea06512d968e8647f27e9b35`，逐项表为 `22dc5e598c7aeec4adc10028736fba0fe711ad1b4d1fd24cde90322db827cad6`。

本轮采用修正后的判断：原 `>=0.30m` 线对允许改变，但报告保存逐对前后值；交付不得新造同层 `<0.30m` 的重叠平行墙，空间宽度不得低于 `0.60m`。窄条合并可删除条内种子、迁移门窗及合并同墙重叠开口，但生产报告必须逐项声明 ID、宿主和连接前后值。整体拒绝时 `changes=[]`、`after=None`，尝试项不计作交付消除，也不进入规整后精度统计。

最终生产快照为：

- `plan_regularization.py`: `8a42275a0eb2187d9b88e2e25f3b73e5e73e24be243534f191854f7692679d49`
- `plan_ink_alignment.py`: `9aa7e65433c95ef42894c2bb4050f3af0a7d46e0c3e129c15813bece2e4457a4`
- `plan_dimension_alignment.py`: `a9cca0d6d44f764feb4fe4c2569ec99c9d3bf78ed793c4e25588f3e34d7f891a`

相同输入完整执行两次，两个 JSON 都是 5,385,341 bytes，SHA256 都是 `11d2d4217f13cd50ff29e4303d90af30a42671dd2640d3d43f3ae473e6545b38`，逐字节一致。没有裸 `RuntimeError` 或 `strict_compile_failed`。模型、Paratera、DeepSeek 请求均为 0。上一生产快照的 `f9924c52…` 报告已保存到 `AI_agent/archive/local_backup/q1/replay_report_pre_86ca_f9924c52.json`，不再作为最终结果。

### 真实 work model 六组

六组中 4 组几何、语义、分离线、当前 source materialization 与 `building_precision` 均通过：`sm21_role`、`sm21_single` 各交付 2 条 `move_wall_line`；`sm24_role`、`sm24_single` 保持 0 改动。成功组原 `>=0.30m` 线对共 58 对，其中 44 对不变、14 对改变后仍合法，没有新造同层 `<0.30m` 重叠墙。成功组互斥分桶为：房间边界 `23/8/13/0 -> 21/3/20/0`，沿墙门窗 `86/8/6/0 -> 86/8/6/0`，顺序均为 `<=5cm / 5–10cm / 10–30cm / >30cm`。

`sm25_role` 与 `sm25_single` 的整楼 B 阶段均因跨层墙偏移及固定外轮廓差异被结构化拒绝，`after=None`、交付消除数为 0。role 有 17 个尝试项和 6 个拒绝项（2 个普通跨层墙、4 个固定外轮廓）；single 有 18 个尝试项和 5 个拒绝项（2 个普通跨层墙、3 个固定外轮廓）。固定外轮廓不是只靠整层 XY 平移即可重合，形状或尺寸本身也不同。

整楼拒绝前，四个独立同层 A 结果均通过 strict compile、source materialization 和 `building_precision`，仅作为未交付证据：

| 组/层 | 同层可编译改动 | 语义明细 |
|---|---|---|
| `sm25_role/F1` | 2 个外皮重复墙合并、2 次墙线移动、1 次原位开口重宿主 | `W_bigN: s_O7 -> s_hall`；空间数 `14 -> 14` |
| `sm25_role/F2` | 3 个外皮重复墙合并、3 次墙线移动、1 个 collapsed step 删除、2 条原位开口重宿主 change | `W_BN1: stack5 -> corrH`，`W_MW1: F2_S06 -> conference`，`W_MW2: F2_S06 -> corrH`；消除 1 个无种子窄条空间，空间数 `16 -> 15` |
| `sm25_single/1F` | 1 个外皮重复墙合并、2 次墙线移动 | 空间数 `14 -> 14` |
| `sm25_single/2F` | 1 个外皮重复墙合并、1 次墙线移动 | 空间数 `15 -> 15` |

四层均未删除种子或开口，也没有合并重叠开口。上述 A 阶段改动不计入整楼交付。

### 历史合法重放

10-01 Opus 三组全部通过当前 source 保存门；sm21/sm24 保持 0 改动，sm25 交付 5 条跨层墙移动。Claude Code 六组中，sm21 run57/run58 都通过，各交付 7 条墙链移动，语义、分离线和 source hard check 均通过且 `building_precision.total=0`；此前的 endpoint cycle 已消失。

Claude sm24 run55/run56 的 A–C 几何与语义检查通过且 0 改动，但历史 role 枚举 `room` 不被当前 catalog 接受，因此当前重保存分别标为 `legacy_input_incompatible`，不算当前 source-save 成功，也不归因于 Q1 几何退化。两份既有保存源分别以 SHA `d43ef2e763e24a9d0fbe33353ffc6dad86c99957e712ba71a4c3d45b194fcde8` 和 `e51c31ace6f8a633cd624ed289698362230805159a15752432bfea68dc9e57e6` 通过当前 `precision_report`，均为 0 项。

Claude sm25 run53/run54 因固定外轮廓真实形状或尺寸差异被结构化拒绝，`after=None`、交付消除 0；尝试改动只保留为回滚证据。

### E/F 原始历史试建

E 墨线对齐共 5 个 trial 组、7 层，7 层均产生可交付结果，且没有语义违规。互斥分桶为：房间边界 `29/12/21/5 -> 58/1/3/5`，沿墙门窗 `132/15/5/1 -> 135/15/2/1`。

F 仍只使用最初从原图可见区域人工读取的 5 层辅助尺寸链。旧 fixture 没有 `start_world_m`，4 个独立可编译的尺寸结果均明确报告 `origin_basis=legacy_anchor`。此处统计独立 F 的严格编译：5 层中 4 层通过、1 层结构化拒绝；成功队列从原始到墨线再到尺寸链的房间分桶为 `24/1/7/4 -> 32/0/0/4 -> 32/0/0/4`，门窗为 `77/2/2/0 -> 79/2/0/0 -> 78/3/0/0`。独立 F 拒绝项为 `sm25_cmp3_role_trials/F2`，尺寸链尝试后 `partition mwW` 与固定外皮重叠，所以此队列没有它的 after 指标；这不等于整个 trial 失败，后续 A 的成功衔接另列如下。

`sm24_role_debug_run7/F1` 有两扇门从 `<=5cm` 退到 `5–10cm`。报告把阶段标为 `ink_then_dimension`，因为该层尺寸链只校准轴而没有进一步改几何：

- `D-south`：误差 `0.038856m -> 0.056339m`；像素端点 `[414,877.5]-[446,877.5] -> [413,878]-[445,878]`；宿主外皮项 `footprint:2` 从 `y=877.5` 移到 `878.0`，开口双 jamb 有明确墨线支持。
- `D-hall`：误差 `0.044775m -> 0.053479m`；像素端点 `[406,303]-[452,303] -> [407,298.2504]-[452,298.2504]`；宿主 `partition:wall-top-s` 从 `y=303` 移到 `298.2504`，开口 jamb 有明确墨线支持。

同层 ink report 还逐项拒绝 `W-b1`、`W-b2`、`D-o2`、`D-st`、`D-off3` 的不完整双端证据并保留原端点。完整逐扇坐标、宿主 change、gap evidence 和 rejection 位于 `replay_report.json.gz -> summary.reader_alignment.opening_tier_regressions` 及对应 floor 的 `ink_report`。

新增贯通开发辅助链保存在 `role_fixture_dimension_inputs.json`，SHA256 为 `c416871f6a33e756713d7491add30fe46c23c144df00430e2a1f61ebd0980fe4`，schema 为 `q1_role_fixture_dimension_inputs_v1`、`gt_used=false`。它用于 role fixture 的 pipeline 开发探针；`replay_report.json.gz -> reporting_boundary.pipeline_dev_auxiliary` 明确记录其作用域。它没有混入上述原始 5 层 H 比较或精度统计。

### 旧 F 到 A 的单层衔接探针

对旧 `sm25_cmp3_role_trials/F2` 做了两次完全相同的单层真实探针：原通过稿 → 生产 E → 原 `X_BOTTOM_VISIBLE` 单轴辅助链 F → 生产 `regularize_plan` A → literal compile → source gate。没有使用 `role_fixture_dimension_inputs.json` 的四条新尺寸链，也没有模型请求。正式可重跑脚本为 `reader_dimension_handoff.py`。

两次 `reader_dimension_handoff.json` 都是 186,106 bytes，SHA256 均为 `7f1104b44d500d68b8eb6935899426095a0d604fe151db4534744d6ed599601e`，逐字节一致。最终结果为 `delivered_after_a`：

- 原稿可编译，房间/开口/门/窗为 `16/30/14/16`；房间桶为 `0/4/10/1`，门窗桶为 `19/9/2/0`。
- E 后仍为 `16/30/14/16`，没有 room ID、开口宿主或门连接变化；房间桶改善到 `10/1/3/1`，门窗桶为 `19/10/1/0`。
- F 接受旧尺寸链并报告 `origin_basis=legacy_anchor`，但独立 literal compile 因 `mwW` 与 `footprint[5]` 在 `x=470.2px` 重合而拒绝。这正是主表把 F 记为 4/5 的边界：它统计独立 F 严格编译；实际 trial 继续交给 A 后可以恢复为可交付平面。
- A 实际交付 3 个 `merge_duplicate_wall_into_fixed_footprint`、2 个 `move_wall_line`、1 个 `remove_collapsed_wall_step` 和 2 个 `retain_openings_on_merged_wall`。其中退化的 `mwW` 余段没有 hosted opening，按生产审计删除；literal compile 通过。
- F 后 A 的房间/开口/门/窗为 `15/30/14/16`；房间桶为 `12/0/3/0`，门窗桶为 `20/9/1/0`。真实 source gate 通过，`building_precision.total=0`。
- 唯一消失的房间 `F2_S06` 没有命名 seed，原编译 polygon 面积为 `2.196719857m²`，边界 source refs 同时精确命中本次 fixed merges 的 `corrS` 与 `mwW`，因此只按这一条无种子外皮窄条消除接受，未泛化放宽其他房间变化。
- `W_BN1`、`W_MW1`、`W_MW2` 的 kind 均保持 `window`、单宿主数保持 1；三项宿主变化分别同时被对应 `merge_duplicate_wall_into_fixed_footprint.object_ids.openings` 和 `retain_openings_on_merged_wall` 认领：`stack5 -> corrH`、`F2_S06 -> conference`、`F2_S06 -> corrH`。门连接、命名种子和开口总数均不变。

完整 E/F 报告、A 的逐项 changes、原稿/E/F 后 A 的语义及精度、F 候选与 A 结果的真实 source gate，以及针对上述唯一条带和三扇窗的 `q1_dimension_handoff_semantic_audit_v1` 均保存在 `reader_dimension_handoff.json`。独立 F 的 4/5 统计没有改写，另列的 handoff 证据证明第五层在生产 A 后可交付。
## 第三轮最终结果（2026-10-08）

第三轮按最终裁定允许跨层、重叠且严格小于 `0.30m` 的外皮边对齐：默认移动上层边到下层边；只有上层边有 F 尺寸坐标依据而下层没有时，才允许反向移动下层边。同层 A 的外皮仍固定。每条 `move_footprint_edge` 都必须有有效的 source/target floor 和 edge index，目标必须是对层真实 footprint edge；无目标 edge 的内部墙对齐不计为外皮消除。

最终生产快照为：

- `plan_regularization.py`: `02481d54bec1834345051bdfbc39bf19f003cacd15c850c7541cb6d6ccb991ce`
- `plan_ink_alignment.py`: `9aa7e65433c95ef42894c2bb4050f3af0a7d46e0c3e129c15813bece2e4457a4`
- `plan_dimension_alignment.py`: `a9cca0d6d44f764feb4fe4c2569ec99c9d3bf78ed793c4e25588f3e34d7f891a`
- `replay.py`: `05f9c83c219b2d1b5fa2fa0b039a1f6127a9f8e43dbfff65f86467bad51f7ff8`

完整 H 用同一输入执行两次，两个 JSON 均为 9,350,672 bytes，SHA256 均为 `67c9892bcfc8720b0cc99f38084615b4d4919026f54b79b41c6739e57ea53dc7`，逐字节一致。补充 handoff 也执行两次，两个 JSON 均为 186,106 bytes，SHA256 均为 `2288ebcf5e19dfd761457760dcf4c7cfbed4cc8eb17032020a84007778f83e8d`。模型、Paratera、DeepSeek 请求均为 0；未运行 pytest 或全量检查。

### 总体裁定

15 组 A-C 重放全部通过 H 的几何、语义、同层分离线、跨层外皮政策和未对齐近线审计：13 组通过当前 source save gate；Claude sm24 run55/run56 几何仍通过且保持 0 改动，但旧 `room` 枚举不兼容当前 catalog，继续单列为 `legacy_geometric_pass_source_save_incompatible`。其余 11 组的 after 语义、三档评价指标和 source precision 与 round2 的规范化 SHA 全部一致，没有退步。

报告把三个阶段分开：A 为各 `floor_reports` 中的同层墙线合并、窄条和语义映射；B 内墙移动为 stack 顶层 `move_wall_line`；B 外皮消除为通过逐边政策审计的唯一 `(source_floor_id, source_edge_index, target_floor_id, target_edge_index)` 数量。所有成功组的生产 `storey_wall_offset_under_0_30m` 未对齐近线从 100 对降到 0 对，其中真实 work model `35 -> 0`、Opus 辅助 `5 -> 0`、Claude 合法重放 `60 -> 0`。共交付 92 条 B 内墙移动记录和 23 对 B 外皮消除；没有无效或未计数的外皮 change。

四个第三轮目标均整楼交付：

| 组 | A 同层结果 | B 内墙移动 | B 外皮唯一对 | 跨层未对齐近线 |
|---|---|---:|---:|---:|
| `sm25_role` | F1 合并 2 条固定外皮重复墙；F2 合并 3 条、消除 1 个无种子窄条、移除 1 个 collapsed step；语义映射逐项保留 | 15 | 4 | `15 -> 0` |
| `sm25_single` | 1F/2F 各合并 1 条固定外皮重复墙，无房间或开口删除 | 16 | 3 | `16 -> 0` |
| Claude run53 | A 0 改动 | 22 | 8 | `24 -> 0` |
| Claude run54 | A 0 改动 | 16 | 8 | `16 -> 0` |

四组共 23 条 `move_footprint_edge`，全部有有效 source/target edge index、原始边实际重叠、位移严格小于 `0.30m`、after source 落在 target 坐标且 target 外皮保持原位。四个历史输入都没有 F 外皮尺寸依据，因此 23 条方向全部为 F2→F1。`sm25_single` 先前错误的 QhallS 外皮到下层内部 Pm1N 的记录已不存在；最终由下层内部墙 Pm1N 移到上层已锚 QhallS，不计外皮 pair。

真实 work model 六组现全部当前可交付、source gate 通过且 `building_precision.total=0`。互斥精度分桶为：房间边界 `57/12/25/8 -> 56/7/36/3`，沿墙门窗 `183/24/11/4 -> 183/24/11/4`，顺序均为 `<=5cm / 5-10cm / 10-30cm / >30cm`。这反映外皮与墙线一致性修复，不能解释为全部 GT 误差单调改善。

### E/F 与 handoff

原始历史 E/F 队列口径不变：E 的 7/7 层可交付；旧 5 条 F 辅助链独立严格编译为 4/5，且旧输入继续报告 `origin_basis=legacy_anchor`。F 成功队列的房间分桶仍为 `24/1/7/4 -> 32/0/0/4 -> 32/0/0/4`，门窗仍为 `77/2/2/0 -> 79/2/0/0 -> 78/3/0/0`。两项已知的 `sm24_role_debug_run7/F1` 门窗退档和逐扇墨线证据仍完整保存在主 JSON。

sm25 F2 的单层 E→旧 F→A handoff 在最终 kernel 上仍为 `delivered_after_a`：A 交付 3 条 `merge_duplicate_wall_into_fixed_footprint`、2 条 `move_wall_line`、1 条 `remove_collapsed_wall_step`、2 条 `retain_openings_on_merged_wall`；literal compile 与真实 source gate 通过，`building_precision.total=0`。房间/开口/门/窗为 `16/30/14/16 -> 15/30/14/16`，只接受已审计的无种子 `F2_S06` 固定外皮窄条消除及 `W_BN1`、`W_MW1`、`W_MW2` 三项精确宿主映射。旧 F 表的 4/5 仍表示独立 F 严格编译，不能改写成最终 trial 拒绝。

第三轮正式结果替代第二轮作为当前结论；`round2/` 与 `round1/` 继续保持原字节证据，不被改写。
`AI_agent/archive/local_backup/q1/round3-replay/` 只含可再生的双跑副本、预冻结探针和检查脚本，将在交付前删除；正式 `replay_report.json.gz`、`reader_dimension_handoff.json`、本笔记、脚本，以及报告内的原始输入绝对路径和 SHA 已足以重建与复核，不依赖该临时目录。
