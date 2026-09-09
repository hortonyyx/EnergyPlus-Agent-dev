# M0 初次开发诊断（非最终验证）

运行：`python scripts/tool_scripts/diagnose_source_partitions.py --out AI_agent/logs/experiments/2026-09-09_m0_source_partition_run01`。

这是首个实现过程中的旧产物重放/人工分组诊断，早于重复窗、窗位变化和源失败硬阻断修补；代码当时尚未提交，manifest 保存接手提交与已跟踪 diff 摘要，不足以标识所有当时的新文件。因此保留作中间观察，不作为最终代码可重复性成绩。

最终固定代码结果见 [run02](../2026-09-09_m0_source_partition_run02/README.md)。本目录原产物保持不变；没有冷启动、产品模型或 EP 调用。sm24 的 8 空间预览不建窗且未恢复门洞连通，不是完整 BIM。
