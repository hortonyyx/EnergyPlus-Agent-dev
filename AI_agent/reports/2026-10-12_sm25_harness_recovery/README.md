# sm25 harness 提交与恢复修复 — 2026-10-12

状态：修复、定向离线验证及独立源码审阅通过，已登记runtime v10 / domain v67；启动前独立核对后运行唯一一轮。

实现提交：`5e765337d970548be53c3610bb7f177aecad4c80`。正式登记与最终离线节点所用临时登记的生产文件/模式指纹完全一致；registry verify通过，CLI配置检查返回ready。实际启动HEAD、输入hash及独立预飞在外部cache的`launch-record.json`记录，不在运行中改源码或配置。

用户要求先修好harness，至少让完整流程能跑起来。依据[上一轮冻结实验](../2026-10-12_sm25_plan_sol/README.md)，本次修复成功/失败trial大回执、passed但未submit稿件的接续空档、transport缺usage结算证据矛盾，并补齐协调员读取大reader_artifact的同类问题。保留原始证据、正式提交门槛、返工权限、缺usage未知口径；不修改几何质量门槛来制造通过。

离线验证覆盖百万字节回执后的下一次模型调用和submit、通过稿在新任务中读取/重验/局改/提交、篡改及越权拒绝、传输错误后的有界重试与保守记账。真实服务调用与离线脚本模型分开记录。实施完成后独立审阅，再登记runtime/domain版本。

| 修复 | 行为与边界 |
|---|---|
| 试建回执 | 保存完整审计报告，模型先收到判定、定位问题、必要决策和小引用；按JSON pointer分页读取余下证据。成功试建仍须显式submit。 |
| 通过稿接续 | durable event绑定完整回执、原稿、编译稿、候选源文件及输入图身份；新任务可读取原稿、原样重验或按授权范围局改，随后显式提交。此前已修正失败不再当作当前问题。 |
| 正式reader_artifact | 协调员分页读取大型交付；装配仍从不可变registry读取完整几何，无需模型重抄。 |
| 缺usage结算 | 区分协议上的图片计费规则和实际usage证据；未知用量保留预留，无总token限额时允许原配置的有界重试，有限额时仍保守保护。 |

独立审阅曾复现“仅改回执topology_issues、几何hash不变仍可接续”的完整性缺口，已加完整回执事件摘要验证并复核拒绝；旧事件只有完整原始回执可证明身份，不把不完整投影当作证明。

| 离线验证范围 | 结果 | 耗时与限制 |
|---|---|---|
| 缺usage/重试/记账核心 | 52通过 | 6.62秒，离线adapter |
| runtime邻接 | 103通过，3项最初被旧registry阻断 | 20.49秒；3项已在最终节点实际复验通过 |
| 大trial回执及报告浏览 | 最终7通过 | 8.12秒，含成功后显式提交、失败后继续读报告 |
| trial/submission邻接 | 15项额外通过，1项最初被旧registry阻断 | 原22项中含已更新的6项反馈检查；阻断项已在最终节点通过 |
| 接续与相邻会话 | 最终25专项通过，34邻接通过 | 专项13.90秒；一次新增测试regex错误已修并复验 |
| 协调员大artifact浏览 | 7通过 | 8.16秒，保留完整装配源与篡改拒绝 |
| 本地MCP整楼/恢复及最终邻接 | 30通过 | 794.95秒，sm21/sm24/sm25和中断恢复；含上述4项registry阻断复验 |
| 去重最终结果 | **273通过，0失败，0跳过** | 全部真实模型请求0；非历史全集或独立图纸质量验收 |

最终节点使用外部cache中的临时源码登记，不改生产版本历史；其生产文件哈希须与正式登记一致。完整JUnit及按测试身份去重结果索引：`D:/Sim-BIM-Agent/cache/sm25-gpt-harness-recovery-20261012/offline-validation.json`。独立审阅记录同目录`independent-review.json`，结论无剩余P1/P2；未代替实际模型质量验收。

只读重投影上轮11份成功回执：原模型文本约1.95–3.33MB，当前13,854–16,310bytes；11份原文件哈希全不变。证据：`D:/Sim-BIM-Agent/cache/pytest/trial-feedback-20261012/projection-audit-final.json`。这只是确定性回执投影，不是恢复旧模型运行。

修复后使用相同六图与原配置验证一轮：协调员Sol/high、平面Sol/high、立面Luna/high，6 reader slots、180模型请求/700工具/10800秒、无总token限额、自动上下文。配置只改变batch/case/output标识；实验变量为harness。版本和源码在启动前冻结。运行中只观察，不修稿、不发提示、不改预算、不恢复重跑；有整楼候选后才做独立评价。

配置：[run_high.json](run_high.json)。计划运行：`D:/Sim-BIM-Agent/runs/sm25-gpt-harness-recovery-20261012-high`；证据缓存：`D:/Sim-BIM-Agent/cache/sm25-gpt-harness-recovery-20261012`。旧run/cache均保留。本轮不以启动成功或单层trial通过代替整楼交付及独立质量验收。
