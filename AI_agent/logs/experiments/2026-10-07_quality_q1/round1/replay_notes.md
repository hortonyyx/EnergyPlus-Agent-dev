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

## 实际结果

`replay_report.json.gz` 共重放 15 组、25 份历史平面稿和 5 组 reader 试建（7 层），模型、Paratera、DeepSeek 请求均为 0。报告记录输入、参照、评价器与三份生产模块的路径和 SHA-256。

- 15 组中 6 组可交付、9 组结构化拒绝。真实 cmp3 六份只有 sm24 role/single 原样通过；sm21 role/single 的跨层暂移会改变原本至少 30 cm 的真实分离线，最终保守门逐对列出 `changed_legitimate_separations` 并回滚；sm25 role/single 列出 0.109–0.152 m 的近外轮廓重复线、受门窗或命名种子保护的窄条，以及小于 0.6 m 的空间。四份拒绝稿均没有“规整后”指标。
- 真实成功组不应用任何移动，房间边界互斥四档保持 `7/3/6/0`，门窗沿墙位置保持 `33/4/5/0`；房间、门窗、宿主与门连接均未变化。这是“安全不动”，不代表 sm21、sm25 缺陷已自动消除；它们由拒绝阻止交付。
- Opus 开发辅助三例中 sm21、sm24 原样通过，sm25 因跨层移动会改变五组真实分离线而拒绝。Claude Code 六例中 sm24 两例原样通过；sm21、sm25 四例的各次候选暂移合计记录 75 条去重后的“尝试但未交付”变更，均由带对象、前后值和原因的跨层保守拒绝回滚。真实 cmp3 的 sm21 role/single 另各记录 2 条回滚的跨层尝试。
- 全部六组成功结果里，原本至少 30 cm 的分离线均绝对不变：真实 cmp3 `24/24`、Opus `28/28`、Claude Code `26/26`。拒绝组中的暂移结果只作诊断，不混入成功结果。
- E 的 7 层墨线对齐全部能严格编译。房间边界（墙位代理）四档 `29/12/21/5 → 58/1/3/5`，门窗沿墙位置 `132/15/5/1 → 135/15/2/1`。旧探针暴露的 14 个门窗退档由双端门框与明确墙洞证据规则全部拒绝；拒绝理由保存在逐对象 report。
- F 的 5 层开发辅助尺寸链全部能严格编译。房间边界 `24/5/17/5 → 墨线后 42/1/3/5 → 尺寸后 44/0/2/5`；门窗 `96/11/4/0 → 98/12/1/0 → 98/12/1/0`。逐扇仍有 `D-south`、`D-hall` 两项从 `<=5cm` 退到 `5-10cm`，完整像素、宿主墙和墨线证据已列入报告；总体没有 `>30cm` 项。全部 reader 成功结果的房间数、门窗数、宿主与门连接不变。

同一生产代码与同一输入连续两次运行所得 JSON SHA-256 均为 `9a680ff7fd2806f7c0097ad34c4b28d53e5e876ea0aec830ce96d36e3ab9b63b`。最终 kernel SHA-256 为 `3234859c2ce2ba5467408343b0a28979349ca120a7e3b3ded837d961a1dfbb27`，墨线对齐 SHA-256 为 `9aa7e65433c95ef42894c2bb4050f3af0a7d46e0c3e129c15813bece2e4457a4`；所有拒绝均有结构化 report，没有裸 `RuntimeError` 或 `strict_recompile_failed`。
