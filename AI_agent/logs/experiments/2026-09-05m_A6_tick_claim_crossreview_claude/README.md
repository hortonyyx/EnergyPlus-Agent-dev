# A-6 跨家族复核（Claude）· 独立证据目录

工作目录 `/tmp/a6_review_claude`，detached HEAD `94e899e5`。本目录下所有脚本均为复核方
（Claude 家族）本轮独立编写并执行，不复用施工方脚本。

## 文件

- `attack_probe_1.py` — §二 攻击 1（直接改 `_current` 私有属性,像素档）、攻击 2（`TickSession.__new__`
  绕过 `__init__`）、攻击 3（`__class__` 重赋值伪造 `TickBatch`）、自设攻击 4（canonical JSON collision）。
- `attack_probe_2_chain_reorder.py` — 攻击 1 精修版：用两个**各自合法**的链候选交叉装配，
  证明 `consume()` 接受一个跨边顺序倒置（x0>=x1）的伪造批次。
- `own_third_collision_input.py` — §三 自造第三条同形输入：三条链共用一个像素键、
  Q 的两个节点分别撞上 P 的两个不同节点（施工方原两条新例只覆盖了「两链一次碰撞」这一种形状）。
- `r3_hard_example.py` — R-3 硬例复核（`node1+node2` 当段长签名，5900 vs 真值 4300）。
- `r2_debt_lifecycle.py` — R-2 独立验证：本模块自身的补证退债生命周期，与旧 B4
  `obligation=None` 问题完全解耦。
- `r1_r4_e2e.py` — R-1（`return_to_step_one` 端到端失效旧批次）与 R-4（跨 session 但
  同源字节的批次替换仍被拒绝）端到端复核。
- `probe_outputs.txt` — 以上全部脚本本轮实际执行的原始输出（未编辑）。
- `full_suite_claude.txt` — 独立全量 `-n 6` 原始日志（`3877 passed, 2 skipped, 13 xfailed`）。
- `mutation_log.txt` — §六 三处变异测试的命令与结果记录（变异已在验证后用 `git checkout --` 复原）。

## 复现命令

```sh
cd /tmp/a6_review_claude
python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)"
python -m pytest -q -n 6 -p no:cacheprovider
python AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/attack_probe_1.py
python AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/attack_probe_2_chain_reorder.py
python AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/own_third_collision_input.py
python AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/r3_hard_example.py
python AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/r2_debt_lifecycle.py
python AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/r1_r4_e2e.py
```
