# 10-10 Lite BIM domain 与失败实测交接

domain v57 的固定10cm规整开发、离线验证和一次人工调度sm25实测已结束。**完整规整BIM输出未完成。** runtime v2保持，不能以旧成功稿或本轮旧稿回放替代交付。

## 实现与验证

共享尺寸链/XYZ落值、局部锚点、原始/采用读数审计、拓扑保护、立面规整、跨层目标标高分离及精简返工上下文已落地。仅分工角色fingerprint改变，单模型参照保持。专用OCR和自动选步长未实现。

生产集成`851b62ce`、版本登记`bb4c9eac`、夹具修复`3484cae5`均已推送；实测冻结HEAD为`3484cae5`。全量首次5,969 passed / 12 failed / 17 skipped / 13 xfailed；12项旧夹具/指引断言修复后六个完整文件61/61通过，未重复全量。旧sm25两层回放340/334个编译XYZ坐标均落0.1m网格，库存和原件哈希保持，不代表新看图质量。

## 实测终态

- Paratera Qwen3.8-27B/thinking读平面，Qwen3.8-Flash/thinking读立面，项目经理人工调度；coordinator HTTP 0，无fallback、DeepSeek/Claude/GLM调用。
- 62分24.5秒（初始化至root stop），99请求/98响应/1超时/0在途，130工具/6错误。98响应已知provider total 5,280,555、cache/input 81.04%、费用9.1655892 CNY；完整用量/费用未知。
- 四立面accepted，原图复核未见实质错误；118项原始/采用读数，4项改变、最大2.34cm，尚未平立面匹配及装配。
- F1五份完整raw声明均在numeric产物前失败；先后自修格式、漏底墙、近轴接头和北侧门组，最后卡南侧两双扇组误合；事后另发现西上门宽误读。F2 40请求、50次观察、零trial。
- F1第21请求遇60分钟角色时限，产生缺usage的settlement。root budget永久`money_cny_usage_unavailable`，重启仍阻断，没有正式reconcile入口。未修改账本或重开run绕过。
- F2人工盘点和六尺寸链已准备、原图复核，JSON未派发；F1仅讨论人工转交失败raw声明，未形成新任务。人工恢复收益没有实测。
- 无整楼候选/交付，不读取GT；5/10/30cm精度不可评价，最终平面、回叠、BIM查看页未生成。诊断图明确标记非BIM。

完整表格与查看入口见[本轮报告](../experiments/2026-10-10_sm25_lite_regularization/README.md)，[行为](../experiments/2026-10-10_sm25_lite_regularization/observer_notes.md)、[恢复阻断](../experiments/2026-10-10_sm25_lite_regularization/recovery_blocker.md)、[近轴接头诊断](../experiments/2026-10-10_sm25_lite_regularization/trial_003_dimension_order_diagnosis.md)。

## 下一步

先围绕本次证据讨论接口级改动，不自动重复抽样：完整raw声明在编译前失败后仍可受哈希保护地局部修订；近轴接头整理与尺寸链移动原子处理关联节点；人工协调有阶段产物/介入入口。缺usage的保守上界或可审计补账属于runtime候选，本轮未改。现有Q1前置的离线尝试仍失败，不能当作已解决。

粗网格不能纠正两门读成一门或尺寸对象错误；F2长读图无稿不能靠再加提醒、放大限额宣称解决。新付费实测范围另定，本次授权的一次运行已消耗。

## 归档与清理

运行复制回主树`AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/manual_dispatch_sm25_lite_v1`，5,763文件/44,444,654 bytes逐文件SHA一致。完整run、实现patch、旧稿离线回放和测试日志共5,792文件，打包22,516,390 bytes，解包流逐文件哈希复验通过；证据分支`evidence/sm25-lite-2026-10-10`已推送，提交`f80d9613391b06d25cbad785254a90ff2720ce30`。

两棵实现树已先归档后收回。运行树在归档校验后收回Git登记，但删除目录时`Filename too long`；随后原生PowerShell清理被自动审批拒绝（`blocked by policy`），未换方法重试。保留`D:\EnergyPlus-Agent-worktrees\lite-sm25-run-20261010`的33,890文件 / 3,260,100,713 bytes残留，不声称全部清理。C/D剩余约17.46/177.23 GiB，其他任务的旧工作树和受限残留保持。最终事实见[清理记录](../experiments/2026-10-10_sm25_lite_regularization/cleanup_receipt.json)及[备份回执](../experiments/2026-10-10_sm25_lite_regularization/evidence_backup.json)。静态报告页已浏览器复核，9个本地资源链接存在、诊断图加载、无横向溢出或控制台错误；浏览器及临时localhost服务已关闭。
