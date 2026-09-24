# 全墙段支持回查的实现与验证

生产工具读取模型实际保存的墙网，按选择的颜色/容差/窄带半径检查完整路径，将已声明开口与其他无支持段分别报告，并返回未标记原图和路径对照。有编译则附上声明中的相邻空间；不识别语义、不改BIM或按GT修墙。

入口：

```bash
python -m AI_agent.logs.experiments.2026-09-24_sm24_path_support_setup.replay
python -m AI_agent.logs.experiments.2026-09-24_sm24_path_support_setup.run_recovery
python -m AI_agent.logs.experiments.2026-09-24_sm24_path_support_setup.audit_recovery --run AI_agent/logs/experiments/2026-09-24_sm24_path_support_glm_run38
```

运行/回放目录已存在时拒绝覆盖。独立评价只在生成结束后运行，沿用原图观察与容差；工作模型没有评测输入。

35项相关离线检查通过。[真实回放](replay/replay_audit.json)检出run37虚构长墙的108样本缺口，源几何未变。run38是GLM1500秒预算的有界旧稿恢复，明确要求使用新工具，但不提供具体错处；364.37秒正常完成，修复至8空间、21/21宿主、10/10门连接，原图平面minor。不是原图冷启动或重复稳定性证明。结果见[工作记录](../../worklog/2026-09-24_reconstruction_path_support.md)。
