# manual dispatch：plan 角色缓存与响应效率补查

状态：初始六角色 delegate 已完成，后续定向 rework 仍在运行。缓存段保留当时的有界快照；末尾新增初始 delegate 的工具可见收口记录。本文只读分析 `manual_dispatch_sm25_retry1` 已保存的请求元数据、provider usage、公开工具调用/回执与产物。未读取 GT，未读取或报告 reasoning 内容；仅使用 provider 实报的 reasoning-token 计数。

## 结论

当前没有证据表明 runtime 为 `plan_f1` 构造了异常不稳定的请求前缀。对两角色前两个请求做相同的离线、图片脱敏 canonical-body 比较，两者最长公共字节前缀完全相同：均为 12,115 bytes，占首请求 26,162 bytes 的 46.31%。两组请求的完整 wire hash 都正常变化，结构也都因新消息和工具结果增长。

provider 实报却不同：`plan_f1` 前两次均 `cached_tokens=0`；`plan_f2` 第 2 次为 8,320。该差异目前只能列为未定，可能涉及 provider 缓存/路由、请求间隔、输入图片块数量及会话增长方式。尤其 `plan_f1` 第 2 请求的图片槽从 1 增至 10，reported image tokens 从 2,486 增至 24,594；`plan_f2` 第 2 请求只从 1 增至 2 个图片槽，image tokens 从 2,550 增至 4,902。这个差异足以阻止把 cache miss 直接归咎于 runtime 前缀不稳定，但也不能据此证明具体 provider 原因。

这里的离线公共前缀是经过图片值替换后的 canonical JSON 字节代理，不是 provider tokenizer 的 cache-key 实现。provider 的 `cached_tokens` 才是缓存命中的权威实报；两者不能按字节/token 比例直接换算。

## 前两个请求的前缀与时间对照

| 角色 | 请求 | UTC 发出 | 与前一响应间隔 | 脱敏 body bytes | messages | image slots | provider cached | reported image tokens |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `plan_f1` | 1 | 09:52:52.212 | — | 26,162 | 2 | 1 | 0 | 2,486 |
| `plan_f1` | 2 | 09:54:31.147 | 1.389 s | 67,744 | 6 | 10 | 0 | 24,594 |
| `plan_f2` | 1 | 09:52:51.713 | — | 26,162 | 2 | 1 | 0 | 2,550 |
| `plan_f2` | 2 | 09:52:59.920 | 0.406 s | 30,851 | 6 | 2 | 8,320 | 4,902 |

两组首请求的结构 shape hash 相同，均有 2 条 messages、12 个 tools、1 个图片槽。第 2 请求均增至 6 条 messages，shape hash 都随新增工具结果改变。`plan_f1` 的请求增长显著大于 `plan_f2`，主要可观察差异是历史中保存了更多图片槽；原始图片身份在各自角色内保持不变，只是同一图片在上下文中重复出现。

完整 wire SHA-256 在每次请求间都不同，这是追加会话内容后的正常现象；本轮没有发现请求被随机重排或公共开头在 `plan_f1` 独有地提前变化。两组第 1→2 请求的离线 longest-common-prefix 指标完全一致，因此现有证据不支持“只有 F1 的 runtime 前缀不稳定”这一判断。

## 已完成 plan 请求的响应与真实工具动作

下表的 response time 是 adapter request 到 model response 的端到端时间。它包含 provider 排队、网络、prefill/cache、reasoning、可见输出和服务端调度，不能当作纯生成时间。工具动作通过 response tool-call ID 与实际 `tool_invocation` 对照；表内只列确实进入 runtime 的动作。

| 角色/请求 | response time | prompt | cached | output | reasoning tokens | 实际工具动作 |
|---|---:|---:|---:|---:|---:|---|
| `plan_f1` #1 | 97.546 s | 9,697 | 0 | 5,396 | 5,350 | `view_image` ×1；`view_plan_blocks` ×1 |
| `plan_f1` #2 | 665.464 s | 47,976 | 0 | 22,413 | 21,552 | `pixel_profile` ×6 |
| `plan_f2` #1 | 7.800 s | 9,755 | 0 | 111 | 66 | `inputs` ×1；`view_image` ×1 |
| `plan_f2` #2 | 177.606 s | 13,675 | 8,320 | 10,495 | 10,477 | `view_plan_blocks` ×1 |
| `plan_f2` #3 | 61.036 s | 52,528 | 1,664 | 3,189 | 2,928 | `pixel_profile` ×2 |
| `plan_f2` #4 | 92.857 s | 58,899 | 51,584 | 633 | 368 | `pixel_profile` ×2 |
| `plan_f2` #5 | 361.736 s | 71,452 | 57,344 | 15,472 | 15,322 | `view_image` ×2 |

`plan_f1` #2 虽然端到端耗时 665.464 秒，但其 completion 中有 22,413 tokens，其中 21,552 为 provider 实报 reasoning tokens。相反，`plan_f2` #4 用 92.857 秒只返回 633 completion tokens。跨度很大，且多角色并发；因此不能用 `completion_tokens / HTTP seconds` 推导模型的纯解码速度，也不能把各角色请求时间相加当墙钟。能确认的只有端到端请求时延、provider token 计数以及随后实际执行的工具。

## provider 实报与离线估算的边界

- provider cache：只采用 `prompt_tokens_details.cached_tokens`，不由本地公共字节前缀推算。
- 离线相似性：仅比较已保存 final request 的结构、hash、长度、脱敏 canonical bytes 与最长公共前缀；图片内容替换为固定占位符，不输出消息或 reasoning 文本。
- provider prompt：包含 cached 部分，也包含 `prompt_tokens_details.image_tokens`；cached 是 prompt 文本的子集，不能再次加到 prompt。
- provider total：`prompt_tokens + completion_tokens`；图片已经在 prompt 内，不再次加入 provider token。
- runtime budget/费用若另列独立图片计费，应作为 ledger 分子单独说明，不能反写成 provider total。

## 问题归属

缓存显示差异目前属于基础设施/provider 观察问题，证据不足以认定模型能力或 runtime 前缀稳定性退步。plan 两角色在请求长度、图片历史和 completion/reasoning 规模上明显不同；这些因素与 provider 路由和缓存策略都未被单独控制。模型行为可以从实际工具选择、请求完成状态和最终产物评价讨论，但不应从 `cached=0` 或单次 HTTP 总时长直接推断。

## 初始六角色收口与 F1 工具链（18:24 快照）

初始六角色共完成 79 个 HTTP 请求；runtime settlement 的当时累计估算为 7.3357986 CNY。二者分别是请求计数与运行时费用估算，不是纯生成时间或供应商最终账单。各角色 `reader_record.runtime_elapsed_seconds` 与实际工具调用如下；角色并发，因此这些时长不能相加作为总墙钟。

| 角色 | runtime elapsed | 实际工具调用 | 完成状态 |
|---|---:|---:|---|
| `elevation_south` | 4:23.459 | 14 | completed |
| `elevation_north` | 7:47.860 | 22 | completed |
| `elevation_east` | 7:58.105 | 23 | completed |
| `elevation_west` | 9:23.897 | 21 | completed |
| `plan_f2` | 26:10.035 | 19 | completed |
| `plan_f1` | 32:02.413 | 58 | completed |

`plan_f1` 的首个 `trial_plan_bim` 在角色启动后约 28:48 发出，占该角色总 elapsed 的约 90%；此前已实际执行 1 次 `view_image`、1 次 `view_plan_blocks` 和 48 次 `pixel_profile`。三次 trial 的工具执行本身分别约 1.549、1.172、2.411 秒。这个分布说明主要墙钟不在 BIM trial 执行内，但仅靠工具时间仍不能进一步拆出 provider 排队、网络、prefill、reasoning 与可见输出各自耗时。

### F1 首稿的可见形状与拓扑

首稿调用公开参数声明 8 点正交 footprint、18 条 partition、30 个 opening（15 门、15 窗）和 15 个 space seed。原图与 `draft_001/draft_view.png` 的全图对照显示：外轮廓的东西两处阶梯式凹入均保留；两间北侧房间、东侧七间串列房间、中西部两间上下房间、南侧两间大会议室及贯通的交通/入口区均有对应声明。试建回执对 18 条正交内部分隔的 scoped `drawing_differences` 为 0，但回执明确排除了外墙、门窗、斜线、高度、房间身份和整栋完整性，因此不能把该值当作原图完整保真。

同一全图对照还发现一处清楚的材料遗漏：原图在西侧内凹竖向外墙、两间西南会议室正上方有一扇单扇门，首稿 overlay 没有对应橙色 opening。原图可见门符号为 16 个，而首稿只声明 15 个门。该遗漏不改变 14 个内部空间的分隔计数，但缺少一条室内到室外的门连接。当前全图尺度未见另一处同等明确的 F1 外轮廓或主要内墙遗漏；这只是可见 overlay 复核，不是 GT 比对或最终质量结论。

### 两次 repair 与第三次成功

1. `trial_001` 失败是七条东侧串列房间的横向分隔端点停在 `x=970`，距 footprint 竖线 `x=975` 约 5 px。回执逐项给出 `P-RD1` 至 `P-RD6` 及 `P-RS2` 的 junction repair；下一次调用只把这七个端点延到 `x=975`，没有新增墙。首次失败回执到第二次 trial 调用间隔约 23.85 秒。
2. `trial_002` 随后发现 `S-ENTRY` 与 `S-CORR` 两个 seed 位于同一个连通空间。回执要求先查原图中是否存在遗漏隔墙；若没有，则移除或移动冗余 seed。第三次调用仅移除 `S-CORR`，保留入口/交通区为一个空间；第二次失败回执到第三次 trial 调用间隔约 88.53 秒。
3. `trial_003` 于 18:23:16 +08:00 成功，写出 `candidate_01`，包含 14 个空间、30 个 opening；`source_geometry_ready=true`。从第一次 trial 调用到成功回执约 1:57.5。

### 最终提交阻力

成功 trial 后共有三次 `submit_plan_reading`：

- 第一次在 notes 中把“未见北箭头”等完整说明句直接放进 `notes.item`，被拒绝为“不是已声明 plan object”。
- 第二次把 `S-ENTRY`、`footprint`、`D14` 写为 item，仍首先因裸 `S-ENTRY` 不是工具接受的已声明对象写法而被拒绝。
- 第三次只提交 `{"trial_id":"latest"}`，于 18:24:20.756 +08:00 成功接受；从 trial 成功到 accepted 约 64.23 秒，其中两次都是提交 schema/对象引用摩擦，不是几何试建失败。角色随后在 18:24:34 左右完成。

### 人工观察触发的有界 rework

初始 delegate 完成后，调度员复看 F1 `draft_003` 并结合 `assemble_from_readers` 的 candidate_05 回执；后者独立报告 West artifact 的 `F1_D2` 为 elevation-only。这个信号与上述缺失西侧凹墙门相容，但当前记录不强行认定两个标识必定指向同一开口。

调度员随后发出两个有界 rework：`plan_f1_rework` 仅指出原图和读图员自身 overlay 中可见的缺门位置，不给坐标或替代几何；`elevation_east_rework` 仅指出该 reader 自己记录的 D1 墨迹底部约 0.19 m 与其提交 sill=0 的矛盾，并要求重查原 crop。第一次把东立面 target 写成裸 `D1` 的尝试在 task admission 阶段、任何 HTTP 前被拒绝，随后改为合法 `openings:D1`。该 admission 错误不计为模型请求、模型失败或 token/费用。此快照时两项 rework 都只有 1 个 adapter request，尚无 response/tool result；不推断未完成结果。
