# J1 独立源分区证据

[查看对照](index.html) · [汇总与运行身份](report.json)

实现提交 `dfa0b3fa`。运行命令：

```sh
python scripts/tool_scripts/diagnose_partition_evidence.py --out AI_agent/logs/experiments/2026-09-09_m0_partition_evidence_run01
```

复用历史候选及前一程新建 sm25 候选，自动读取已验证 GT 与冻结/已接受 reading。没有新增人工房间分组，没有修改候选或 GT，没有模型、EnergyPlus 或原图冷启动。本 run 不把候选标记为已接受；sm25 保持 unaccepted_candidate。运行时未提交差异仅为 roadmap 的本程施工说明，其摘要见 report。

| 案例 | 参照 / 候选空间 | 结论 |
|---|---:|---|
| sm21 | 14 / 14 | 内部拆并和墙线支持未发现异常；外边界约 100 mm 参考面差异保留原始严重几何报告，整体分区 not_evaluated，不能当成通过 |
| sm24 | 8 / 11 | severe，7 条空间/内部边界差异。读图局部墙线另有 9 对边界待复核，其中包括已知三道额外隔墙；不能把门口、小端段等 9 对全称为假墙 |
| sm25 | 29 / 32 | severe，两处源空间被拆、三段额外内部边界；as-drawn 独立墙面适配未实现，墙线支持 not_evaluated |

每案例 JSON 保存空间对应、完整原始多边形、内部边界位置、候选/参照摘要与读图来源。旧格式仅能验证接受 reading 的字节，不能证明旧 correction 曾消费同一份 reading；此限制写入身份字段。损坏的冻结输入不会退回可变的 stage-root 文件。

sm25 的 [生成来源追踪](sm25-L_anchor/candidate_gap_trace.json) 把三段额外边界关联到原墙对象的自动补线：一层 L043/L044、一层 L039/L040、二层 L041/L042。两面分类分别为 ambiguous/not_opening、ambiguous/not_opening、not_opening/passage。追踪使用候选编墙配方解释生成原因，不进入独立参照比较；厚度范围相交用于定位，不能替代原始符号的语义核对。当前未删这些线，也未解决分类冲突。

服务已接正常 J1 评价包并更新判定说明；此次没有运行模型 judge，不宣称模型已给出新 verdict 或自动硬阻断已新增。验证和接续入口见 [工作记录](../../worklog/2026-09-09_m0_partition_evidence.md)。
