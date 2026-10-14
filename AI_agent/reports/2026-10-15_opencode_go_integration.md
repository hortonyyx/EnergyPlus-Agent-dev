# OpenCode Go 合入与小范围验收

## 授权与合入范围

按用户“分支完成后合入并简单测试”的授权，在每小时跟进中发现`codex/opencode-go`已明确完成。完成标记为[handoff.json](2026-10-15_opencode_go/handoff.json)，分支HEAD为`86c8c79f`，工作树干净，且已包含主线收工文档提交`4f86191f`。主库以fast-forward合入，没有改动对方未提交工作。

此次只整合独立Go订阅provider、六型号的协议/profile、单模型及角色路由、用量和配置示例；未调整BIM几何、检查流程或domain方法。默认`product/config.example.json`和已准备的6 Sol配置与合入前一致，并发、共享预算和恢复能力保留。

新入口为[Go配置示例](../../product/config.opencode-go.example.json)与[接入说明](../workflow/opencode_go.md)。默认产品仍为`gpt-6-sol/high`；Go示例独立使用Kimi K3，不替换默认模型。

## 独立审阅与验证

两名独立审阅者分别核对provider/凭据/协议/记账，以及runtime/预算/恢复/并发路径，未发现P1/P2代码阻断。另一名审阅者核对完成交接、正式登记及已有XML。代码没有增加客户端付费回退、自动切号或DeepSeek调用；服务端账号的余额回退设置未核验。

| 本次合入检查 | 结果 | 耗时 | 新真实模型调用 |
|---|---|---:|---:|
| Go专用13项、产品配置2项、既有Sol配置及共享预算/并发3项 | 18通过 | 首批共6.83秒 | 0 |
| 原登记下的版本封印及实际本地MCP目录 | 2失败，定位为CRLF/LF哈希差异 | 同首批 | 0 |
| 按主库字节新增登记后，仅复验失败2项 | 2通过 | 8.19秒 | 0 |
| 登记完整性核验 | v18/v79通过 | CLI只读检查 | 0 |

有效去重20项全部通过，没有重跑全量、相邻96项或BIM整案。测试使用临时假凭据、MockTransport及本地stdio；没有读取真实凭据或新增服务探针。

首次失败原因：开发工作树`model_profiles.json`是CRLF，而仓库属性规定`text eol=lf`，Git检出也为LF。二者JSON完全一致、CRLF规范为LF后字节相同，但旧v17登记了工作树CRLF哈希`e9e7da0c3c8a20d87b85a89dc2130076f34128575cc74576becf8f0cee6ae254`。主库与Git blob的LF哈希为`458ecd756e291312459c02927b7ea03e37b55762e20fceb0eed73324fc223d71`。

保留旧登记不可变；按主库实际字节新增**runtime-v18-20261015**，domain仍为**domain-v79-20261015**。没有关闭哈希检查、改回CRLF或改写v17历史记录，也没有新增provider逻辑修补。

本次证据：[首批18通过/2失败](D:/Sim-BIM-Agent/cache/opencode-go-integration-20261015/targeted.xml)、[封印复验2通过](D:/Sim-BIM-Agent/cache/opencode-go-integration-20261015/sealed.xml)。

## 复用的真实接入证据与边界

分支接线阶段已有9次真实模型请求、4次工具、3327实报tokens，本次没有重复调用。GLM-5.3-Flash、Kimi K3、Claude Haiku 5.5、GPT-6 Luna通过工具→合成图片→颜色与nonce闭环；MiniMax M3只给最终文本、未按要求调用工具，不能算闭环通过；Qwen3.8 Max没有真实调用。

该证据来自分支记录的不同临时快照，不能合写成同一发布版重复实测，也不能推断六型号均具备建筑识读或整楼交付能力。完整调用表、失败修复和范围见[原接线报告](2026-10-15_opencode_go/README.md)。本次仅核验并复用证据。

## 发布与交接

完成登记、定向验证后，从固定提交生成发布包并走现有原位桌面更新流程。安装结果、发布提交及SHA索引在本节收尾补齐；在验收完成前不把桌面同步写为成功。

检查流程和现有domain流程继续留待下一轮讨论，保持用户已接受的首版基线，后续仍要并发，以6 Sol约10分钟提交且无明显harness自身问题为优化目标。此自动跟进完成后停用，不自动追加该优化任务。
