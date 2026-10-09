# GPT-6 Sol 冷启动整案：可观察行为审查

状态：第一轮最终快照；截至 `finish_bim` 于 2026-10-09 17:46:47（UTC+8）成功回执。本文只使用顶层 bridge 请求/回执、公开工具参数、文件时间与公开产物元数据；未读取 GT，未读取或索取思维链，也未向执行方反馈。

## 配置与统计口径

- requested model：`gpt-6-sol`
- actual model：`unknown`
- reasoning effort：`high`
- 执行方式：外部 agent session 手动调用当前 domain MCP bridge，不是 runtime 内置的 LLM loop。
- provider token：`unknown`
- provider cost：`unknown`
- 开始记录：2026-10-09 17:24:14.884（UTC+8）
- 首次顶层工具请求：17:24:37.702
- 成功 `finish_bim` 回执：17:46:47.571
- 从开始记录到 finish：约 22 分 32.7 秒；从首次工具请求到 finish：约 22 分 9.9 秒。

调用数只按 `<run>/bridge/*/requests.json` 中的顶层请求计算，并用同批 `replies.json` 的 `isError` 判断成功/失败。`tools.jsonl` 中的内部动作不计数，因此 `claim_transaction` 内部的 `record_claim` 没有重复算作模型调用。批次 mtime 只能给出请求开始与整批回执结束时间，不冒充逐调用 server 时钟。

## 完成状态与里程碑

| 里程碑 | 时间（UTC+8） | 可观察结果 |
|---|---:|---|
| 首次 `build_plan_bim` | 17:29:31.680 | 工具写出了 `candidate_01`，但 bridge 回执因 GBK 解码失败而标记失败 |
| 第二次同类试建 | 17:30:05.158 | 写出 `candidate_02`，回执再次发生相同 GBK 解码失败 |
| 首次成功 build 回执 | 17:32:50.972 | `candidate_03`，`source_geometry_ready=true`，返回 2 张工具图 |
| 首次 assembly 尝试 | 17:34:53.817 | 因 stale plan hash 失败，没有成功装配回执 |
| 首次成功 assembly 回执 | 17:37:03.401 | `candidate_07`，29 spaces、61 openings，返回 4 张工具图 |
| 第二次双层重建后 assembly | 17:39:25.939 | `candidate_10`；对象数量保持 29 spaces、61 openings，source hash 已变化 |
| 两次用途返工 | 17:40:02.749 / 17:43:36.312 | `candidate_11` 与 `candidate_12`；对象数量不变，source hash 每次变化 |
| 最终检查批次结束 | 17:46:07.942 | 对 `candidate_12` 完成 inspect/opening/claim 状态检查 |
| `finish_bim` 成功回执 | 17:46:47.571 | 选择 `candidate_12`；`delivery.json` 和 viewer 已存在 |

成功 `finish_bim` 与外层生命周期元数据需要分开：`delivery.json` 已记录 `candidate_12`、`selection_origin=agent_selected`、`viewer_exists=true`，但其中 `generation_status.state` 仍为 `in_progress`。原因是本轮为外部会话，没有调用原 runtime 的 finalize；因此可确认 BIM 工具交付动作成功，不能据此宣称外层 runtime 生命周期已正常完成。

## 顶层工具构成

共 26 个 bridge 批次、54 次顶层工具调用；50 次成功、4 次失败，失败率 7.4%；工具回执共返回 48 张图片。构成如下：

| 工具 | 次数 | 可观察用途 |
|---|---:|---|
| `view_image` | 12 | 查看 6 张完整原图与 6 个平面局部视图 |
| `build_plan_bim` | 8 | 两层试建、修订后重建与立面高度调整后的重建 |
| `claim_transaction` | 6 | 分批记录/应用公开 claim；只按顶层 transaction 计数 |
| `get_bim_reference` | 5 | 读取通用格式与操作说明 |
| `inspect_candidate` | 4 | 检查已保存候选与最终候选 |
| `check_openings` | 4 | 检查开口清单、高度覆盖或最终状态 |
| `view_elevation_candidate` | 4 | 查看四向 source 立面与对应原图 |
| `assemble_plan_bim` | 3 | 一次 stale-hash 失败、两次成功双层装配 |
| `inspect_plan_draft` | 2 | stale-hash 后重新取得两个 draft 的当前哈希 |
| `claim_status` | 2 | 检查 claim 在当前候选上的状态 |
| `revise_bim` | 2 | 两批空间用途调整 |
| `inputs` | 1 | 读取本 run 的已准入输入清单 |
| `finish_bim` | 1 | 选择并交付 `candidate_12` |

## 四次真实错误

1. 17:29:32，`build_plan_bim`：`'gbk' codec can't decode byte 0x94 ...`。`candidate_01`、source 和 viewer 已写入，但顶层 reply 为 `isError=true`，因此统计为失败。
2. 17:30:06，`build_plan_bim` 重试：相同 GBK 解码错误。`candidate_02` 已写入，顶层 reply 仍统计为失败。两次失败说明 raw 工具成功动作不能代替 bridge 回执状态。
3. 17:34:53，`assemble_plan_bim`：`stale plan hash; inspect each intended draft before assembly`。随后执行两次 `inspect_plan_draft`，使用当前哈希后于 17:37:03 成功装配。
4. 17:41:46，`claim_transaction`：`entries must be a nonempty list`。随后重新生成非空请求，于 17:42:11 获得成功回执。

## 返工与实际产物变化

- 两次 GBK 回执失败均留下完整候选：`candidate_01` 与 `candidate_02` 都为 14 spaces、31 openings。它们的 source hash 不同，但 inventory 相同；仅凭 hash 不能断言几何改善。
- 执行方公开进度记录称，在首轮回执失败后调整了 7 处办公室门跨。之后重新输出的 F1 候选仍为 14 spaces、31 openings，但 source hash 改变；说明产生了新 source 产物，是否更符合原图需由独立评价判断。
- 首次装配采用 `draft_006`（F1）与 `draft_005`（F2），17:37:03 形成 `candidate_07`：29 spaces、61 openings、30 connections。
- 四向立面查看后，两层分别重建为新 draft；第二次装配采用 `draft_007` 与 `draft_008`，二者 plan hash 均不同于首次装配。17:39:25 形成 `candidate_10`，库存仍为 29 spaces、61 openings、30 connections，但 source hash 从 `candidate_07` 的 `41248956…` 变为 `ec797dfc…`，可确认 source 产物实际变化且对象总数保持稳定。
- 17:40:02 从 `candidate_10` 生成 `candidate_11`：公开 `revise_bim` 参数包含 2 个 `set_space_role` 操作。17:43:36 从 `candidate_11` 生成 `candidate_12`：包含 27 个 `set_space_role` 操作。两次返工均保持 29 spaces、61 openings、30 connections，但 source hash 依次变为 `703f1be9…` 与 `cbb67433…`；可确认用途元数据实际改变，没有观察到对象增删。
- 最终候选为 `candidate_12`。以上变化只描述公开产物与工具状态，不构成原图保真或几何质量结论。

## 额外临时脚本

run 根目录共出现 3 个额外 `.py` 临时脚本，均为本轮外部执行辅助，不属于生产代码：

| 文件 | 用途 | 文件活动时间（UTC+8） |
|---|---|---:|
| `prepare_plans.py` | 生成两层 plan 声明及相应 `build_plan_bim` 请求；后续用于门跨与立面相关重建 | 17:29:18–17:38:50 |
| `prepare_height_claims.py` | 将公开立面观察整理为分批 claim 请求及补充请求 | 17:40:39–17:42:01 |
| `prepare_role_edits.py` | 生成空间用途的 `set_space_role` 操作与请求 | 17:43:24 |

此外存在多份显式 `request_*.json` 与 `*_stdout.json`，用于保存 bridge 输入和终端摘要；完整工具证据仍以 `bridge/*/requests.json`、`bridge/*/replies.json` 和返回 PNG 为准。

## 评价边界

本审查没有读取 GT，也没有运行独立评价。所有候选报告均为 `status=not_evaluated`。因此当前只能确认工具行为、返工是否实际落盘、交付动作和可查看产物是否存在；实质空间、门窗、连接和 5/10/30 cm 精度仍须在生成结束后由隔离评价给出。
