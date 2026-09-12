# sm24 原图冷启动与实际 Haiku 局部委派

[可查看 BIM](delivery.html) · [独立分区对照](evaluation/index.html) · [原图与门窗复核](evaluation/visual_review.md) · [实验准备和恢复入口](../2026-09-12_sm24_delegation_setup/README.md)

本次已保存 **9 空间 / 58 源边界 / 11 窗 / 11 门 / 11 连接**，源几何自洽通过，浏览器断网加载与旋转通过；**还原失败，且 Agent 未正常完成**。独立分区 9 对 8、severe，西侧连续办公室被拆开，多处隔墙及接待区严重错位。不能因窗口坐标准确或模型可看而判整案通过。

## 输入和真实运行

代码 `ea5e68d9`，720 秒预算；仅五张原始平面/立面 PNG，无旧 proposal、旧 reading、提示 JSON、GT 或评测结果。生产代码沿用已有实现，没有为本例填几何答案。总 Agent 请求 Sonnet、medium，实际 `claude-sonnet-5`。本批明确要求一次早期局部 Haiku 委派，具体任务由总 Agent 选择；不是产品固定流水线。

总运行 629.88 秒，22 次原图查看、1 次 review_detail、1 次 build_bim；唯一候选保存时余约 90 秒。没有源平面/立面查看、原图回叠、开口回查或 finish_bim。随后 Claude 订阅返回 429：`You've hit your session limit · resets 6:30pm (UTC)`。这是本次回执报告的重置时刻，不是已核实的当前剩余额度。没有自动重试、换付费 API 或调用 DeepSeek。

[summary.json](summary.json) 的 `agent_response_completed=false`，交付来源为 `latest_saved_fallback_not_agent_selected`，即系统保留最新候选。CLI result 虽有 subtype=success / terminal_reason=completed，但同时 is_error=true、429、退出码 1，不能误记正常完成或超时。

## 委派是否实际有效

Haiku 仅得到 East_view.png 与父模型问题，隔离清单/图片哈希/原始响应均保留。实际 `claude-haiku-4-5-20251001`、110.66 秒、10 次图像查看和 1 次像素统计，正常返回了实质回答。委派约在运行第八分钟才开始，完成后才保存候选；没有做到早期分工与早期保存。

[独立原图复核](../2026-09-12_sm24_delegation_setup/haiku_observation_review.md)确认：Haiku 把三窗读成四窗，门的位置和“接地”判断也错。父问题自行带入了错误的“10000mm 高”前提，不符合本批要求的中性提问；不能把此任务称为完全无暗示的独立观察。Sonnet 保留东侧三窗、层高 4.5m，未将第四窗直接写入，但明确记录冲突未核清。此次证明分工与证据隔离可运行，**没有证明准确率或降本收益**。

| 实际调用 | 耗时 | CLI 估算美元（非账单） |
| --- | ---: | ---: |
| Sonnet 主运行（含内部少量 Haiku 辅助量） | 629.88 秒，包含等待子任务 | 1.1424378 |
| Haiku 局部子任务 | 110.66 秒 | 0.0882912 |
| 本批合计 | 不将父子耗时相加 | 1.2307290 |

主回执 Sonnet 输出 43121 tokens，Haiku 子回执 usage 输出 9505 tokens；子回执 modelUsage 另含内部辅助量，合计输出 9521，不能重复累计。开发侧独立评价/Haiku 复核由 5.6 Terra 分担，开发助手用量不在这两个 Claude 回执里。

## 独立核验和边界

- 10 项实现文件与 5 张原图哈希、实际源摘要通过，证据见 [artifact_verification.json](artifact_verification.json)。
- 父 22 张及子 10 张实际返回图片逐像素重放通过；子任务只有所选原图/问题、只读工具，返回文本未改，见 [execution_verification.json](execution_verification.json)。其中 selected_source_viewed 明确为 false。
- 独立评价仅在 final summary 写出后读取已人工核验的 typed GT v3，用实际源空间比较。西侧错拆房及接待区米级位移均有原图支持，不是小容差差异。
- 11 窗在同楼层/立面/类型等数量组内作世界坐标排序诊断，水平/高度端点基本一致；这是坐标诊断，缺完整读图证据对应清单，不称完整窗匹配评分，也不验证窗所属房间。
- 东外门宽仅 0.96m，相对原图 1.6m 少 0.64m。proposal 自行将其截到错误走廊范围，并写了 `clamped to Corridor jog cell extent`；不是构造器静默截断。三外门均漏掉图上约 0.2m 的门槛高度，室内门位置和宿主仍需核对。
- [交付浏览器检查](browser_delivery_check/summary.json)与[楼层旋转检查](browser_F1/summary.json)均通过，主助手看了实际截图。该验证不代表图纸保真。

没有新增生产代码，复用上一程相关测试，不重复全量。原始输入、候选、失败回执与独立评价保留；大事件流无损压缩，原摘要见 compressed_streams.json。后续从 candidate_01 加五原图另起恢复，优先核房间分隔，再检查受影响门宿主；恢复结果必须与本次冷启动失败分开报告。
