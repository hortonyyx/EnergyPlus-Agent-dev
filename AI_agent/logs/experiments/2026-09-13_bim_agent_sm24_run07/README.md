# sm24 东南折角及门归属局部恢复

[打开交付页](delivery.html) · [直接查看模型](candidate_01/viewer.html) · [源BIM](candidate_01/source_model.json) · [独立局部评价](evaluation/local_review.md)

从run04恢复，模型独立区域观察＋自身轮廓参考面复核后，开发选择两个源空间，由确定性代码应用选定trace002。**东南房间和走廊明显改善，整案仍severe；非自主冷启动。** 8空间、54边界、11窗、11门、11连接，无未建开口。源几何/接触/开口宿主自洽pass；离线浏览器加载及旋转通过，0页面错误/外部请求/请求失败。

## 实际变化

- 东南房间从错误矩形恢复完整折角，邻走廊按原两空间并集的剩余区域计算。只有两个空间改形，无新增/删除空间。
- 原内门移到新北侧横墙；保持原ID、空间对和2.1m高度，门宽从1m变为约0.919m。
- 南侧外门保持原坐标、0.9m宽和2.4m高，宿主/外连接由走廊改为东南房间。
- 11扇窗字段全部不变，22个开口ID与11个连接ID无增删。

GT只在源生成结束后使用：东南房间IoU（面积交并比）0.5269→0.9812，对称差面积12.4383→0.4956m²；走廊IoU0.6604→0.8920。东南新折角竖边仍偏约0.194m、顶边约0.047m，其他东侧横墙仍偏0.76/0.38m，整案severe不改。typed_v3窗匹配未接入本诊断，11/11数量不是匹配得分。

## 输入、干预与限制

观察来自 ../2026-09-13_sm24_region_trace_reference_review，其前序独立区域观察未提供BIM、人工正确坐标或GT；参考面复核收到开发问题反馈及模型自身旧trace。应用由开发选择run04、两个空间ID及有界对齐策略：默认0.05m，本次显式0.15m（实验最大允许0.2m），实际只将西侧共边两个顶点同步移0.144324m。其余新内墙/内门坐标沿用模型。没有将GT坐标写入，不吸旧内部隔断、不裁切、源严格守恒检查未放宽。

模型标定仍有像素偏差；其“外表面已核准”的自评不采信。交付页保留标定冲突，源保留旧备注并追加新未决项。源导出器通用generator标签仍写Claude subscription tool loop，真实模式以developer_orchestrated_local_trace_replay、operations和0次应用模型调用为准；交付页已明确确定性应用。

应用代码副本/摘要见implementation及inputs.json，整边/坐标/点位移见normalization_audit.json。实际操作见operations.json；源变化、局部GT诊断、确定性重放见evaluation。此次应用无模型/solver调用，前序四观察合计460.57秒；后三次CLI估算$0.7077932，首轮超时缺最终用量，不能视为完整费用或账单。

执行入口：../2026-09-13_space_trace_setup/apply_trace.py。恢复命令参数为 --observation ../2026-09-13_sm24_region_trace_reference_review --boundary-snap-m 0.15 --out 新目录；源操作/重导出核验为 verify_application.py RUN。
