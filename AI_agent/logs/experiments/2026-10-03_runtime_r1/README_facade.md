# R1 C：sm24 四立面并发／依次实验

固定实验已于 2026-10-03 完成，实际结果见 [facade_report.md](facade_report.md)，完整可重建证据见 [facade_evidence.compact.tar.xz](facade_evidence.compact.tar.xz)，独立结构与账本审计见 [facade_evidence_verification.json](facade_evidence_verification.json)。两组共用的 20 票持久账本已经关闭在 9 票，不得重跑、恢复或追加抽样。运行侧只读取 `facade_cases.json` 和四张已有原图，评价侧才读取 `facade_references.json`。图片不复制进证据目录，按仓库路径、SHA-256 和尺寸核验。

实验固定为 Qwen3.8-27B：同样四题先用 `delegate_to_roles` 四并发一次，再把 `max_concurrent_observers` 设为 1 依次一次。两轮共用一个 20 票持久账本；每题最多 2 次模型请求，格式补救也占同一题预算，失败与超时同样占票。每题要求逐扇给宽度、窗台、窗顶和原图像素框，并按楼层报窗数。评价用 5 cm 含边界口径，并单列东、西两扇 4800 mm 大窗。

本次使用的离线核验命令为：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_experiment.py validate
```

以下命令仅记录本次已经完成的运行和评价步骤，**不得再次执行 `run`**。`run` 是唯一会调用 Paratera 的命令；它通过真实 `src.agent.runtime_coordinator`、真实 `FrozenBimTools` 和协调器的 `delegate_to_roles`，没有脚本自建的单题 `gather` 旁路：

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_experiment.py run \
  --out "$PWD/.r1-work/facade_experiment" \
  --credentials-file /workspaces/EnergyPlus-Agent-dev/.env
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r1/facade_experiment.py evaluate \
  --out "$PWD/.r1-work/facade_experiment"
```

本次最终产物是 `batch_results.json`、`evaluation.json` 和 `REPORT.md`；原始事件、请求、回包、图片身份和每个子任务状态保留在两个 coordinator 目录。恢复能力只用于解释脚本设计，本实验账本已关闭，不能再用它继续运行。

本次用以下阶段 3 无损归档命令保存运行目录；四张仓库原图按路径和哈希引用，不在归档中重复存字节。命令用于审计记录，不要以重新运行实验为前提改写证据：

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
