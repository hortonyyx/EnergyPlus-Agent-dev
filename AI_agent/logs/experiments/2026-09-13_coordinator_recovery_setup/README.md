# Sonnet调度、Haiku局部执行与代码改形

[工作记录](../../worklog/2026-09-13_reconstruction_coordinator.md) · [run04结果](../2026-09-13_bim_agent_sm24_run04/README.md)

本批响应用户对工作模型角色、时间和消耗的明确要求。Sonnet级仍为上限，首个局部观察优先Haiku，确定性代码执行局部改形。没有DeepSeek、付费API或EP。

从仓库根运行：

```bash
python AI_agent/logs/experiments/2026-09-13_coordinator_recovery_setup/run_recovery.py --dry-run
python AI_agent/logs/experiments/2026-09-13_coordinator_recovery_setup/run_recovery.py --out AI_agent/logs/experiments/NEW_RUN
```

`--dry-run`只打印任务、不调用模型。实际运行只读run03/candidate_01 proposal与五原图，300秒模型主调用预算，包含子任务等待；不导入旧评价。默认run04已存在，重跑必须传新目录。任务由开发助手选为局部恢复，但具体待核问题、子问题、几何决定由Sonnet选择，不是冷启动或完全自主发起。

生成完成后按实际回执统计角色/时间/用量：

```bash
python AI_agent/logs/experiments/2026-09-13_coordinator_recovery_setup/audit_runtime.py AI_agent/logs/experiments/NEW_RUN
```

父时长已含串行子时长，不相加作为总耗时；差值还含工具/启动开销。CLI费用不是订阅账单。原图/源运输复用[verify_execution.py](../2026-09-12_sm24_delegation_setup/verify_execution.py)，GT评价复用同目录`evaluate.py`，只能在summary落盘后运行，不回流给生成模型。

当前方法参考历史量测/候选处置，但没有恢复全部历史工序，也未增加其房间数等先验；与上次run03输入、范围和预算不同，不作严格同条件消融。
