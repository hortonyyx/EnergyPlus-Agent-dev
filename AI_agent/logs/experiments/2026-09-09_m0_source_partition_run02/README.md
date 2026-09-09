# M0 固定提交源分区诊断

代码：`d37ae2f9`。命令：

```bash
python scripts/tool_scripts/diagnose_source_partitions.py --out AI_agent/logs/experiments/2026-09-09_m0_source_partition_run02
```

运行时业务代码与该提交一致，仅 roadmap 有待同步的文档改动。没有产品模型或 EP 调用；这里的 model_calls=0 指实验调用，不包括开发助手本身。输入路径、文件/接受证明哈希、人工分组条件和检查明细见 [report.json](report.json)。原始/旧 run 均未修改。

打开 [index.html](index.html) 查看汇总：

- sm21：[当前模型](sm21/current_viewer.html)，14 空间/100 面/15 窗，当前重放与源映射通过；独立源分区参照未提供，not_evaluated。
- sm24：[历史错误模型](sm24/archived_viewer.html)，11 cells，三对额外物理 Wall 为 severe；[分区预览](sm24/partition_preview.html) 通过声明的人工分组恢复成 8 个非矩形/矩形空间。预览不建 11 扇窗，[完整候选](sm24/assisted_full_correction.json) 保存原窗及房间重映射。该候选没有完整生产建模通过记录，当前历史全量重建仍受 win_east_2 seam 检查阻塞。
- sm25：[当前模型](sm25/current_viewer.html)，27 空间/208 面/31 窗，源映射通过；65 mm 短边仍阻塞下游。独立源分区参照未提供，not_evaluated。

sm24 fixture 来自用户已确认的错误拆分，几何坐标仍沿用旧 correction；它仅隔离三道切割墙。走廊口开放间隙、门洞和整体图纸正确性未验收；不能称为 GT 对照、无人读图或完整 BIM 修复。源映射通过只证明建模保留校正对象，历史 EP 状态不是本批 EP 成绩。

源到派生摘要、边界/开口映射和未评价范围在各 `source_model.json`；下游检查状态与完整性评价分开。此 run 与开发中 run01 的关系、定向测试和下一步见 [工作记录](../../worklog/2026-09-09_m0_source_partition.md)。
