# R1 C：sm24 四立面并发／依次实验准备

本目录已经准备好固定四题、独立评价参照、真实 MCP 运行脚本和报告模板；当前没有发送模型请求。运行侧只读取 `facade_cases.json` 和四张已有原图，评价侧才读取 `facade_references.json`。图片不复制进证据目录，按仓库路径、SHA-256 和尺寸核验。

实验固定为 Qwen3.8-27B：同样四题先用 `delegate_to_roles` 四并发一次，再把 `max_concurrent_observers` 设为 1 依次一次。两轮共用一个 20 票持久账本；每题最多 2 次模型请求，格式补救也占同一题预算，失败与超时同样占票。每题要求逐扇给宽度、窗台、窗顶和原图像素框，并按楼层报窗数。评价用 5 cm 含边界口径，并单列东、西两扇 4800 mm 大窗。

先做离线核验：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_experiment.py validate
```

获派运行时从本工作树执行以下命令。`run` 是唯一会调用 Paratera 的命令；它通过真实 `src.agent.runtime_coordinator`、真实 `FrozenBimTools` 和协调器的 `delegate_to_roles`，没有脚本自建的单题 `gather` 旁路：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_experiment.py run \
  --out "$PWD/.r1-work/facade_experiment" \
  --credentials-file /workspaces/EnergyPlus-Agent-dev/.env
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_experiment.py evaluate \
  --out "$PWD/.r1-work/facade_experiment"
```

可从中断处重启同一 `run` 命令：已完成的批次直接复用，未完成的协调器目录走恢复路径，任务 ID、协议和 20 票账本均不重置。若源码、题库或协议改变，恢复会拒绝。最终产物是 `batch_results.json`、`evaluation.json` 和 `REPORT.md`；原始事件、请求、回包、图片身份和每个子任务状态保留在两个 coordinator 目录。

完成评价后，用阶段 3 的无损归档器保存运行目录；四张仓库原图按路径和哈希引用，不在归档中重复存字节：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_pack.py pack \
  --archive AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_evidence.compact.tar.xz \
  --source facade_experiment=.r1-work/facade_experiment \
  --reference case_tests/e2e_tests/sm24_anchor/case_data/North_view.png \
  --reference case_tests/e2e_tests/sm24_anchor/case_data/South_view.png \
  --reference case_tests/e2e_tests/sm24_anchor/case_data/East_view.png \
  --reference case_tests/e2e_tests/sm24_anchor/case_data/West_view.png
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_pack.py verify \
  --archive AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_evidence.compact.tar.xz
```

参照依据是四份既有 sm24 原图识读 JSON 的固定哈希。它们只用于事后评价，没有放进问题、notes、运行输入或冻结工具目录。两扇单列大窗特指东立面第一扇和西立面第五扇；北立面也有一扇 4800 mm 窗，但不拿它替换本次指定反例。
