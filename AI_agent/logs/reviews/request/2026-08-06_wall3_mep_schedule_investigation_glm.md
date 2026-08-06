# 调查单 · 墙 3：`run_mep` 产的 load 引用未定义 schedule

> **⚠️ 这是「调查单」不是「施工单」**（2026-08-06 起本项目新分的两种派工形态）。
> **本单不写病因假设、不写修法、不写验收条件** —— 那些正是要你查出来的东西。
> 派工方（orchestrator）本轮已因「预先写死病因/验收」错了 5 次，故本单**刻意不给**。
> **⛔ 本单只调查、不改生产代码。**

- **日期**：2026-08-06
- **派工方**：orchestrator（Opus 5）
- **席位**：GLM-5.2，**主工作树**
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD 应为 `b379cd8`

---

## 0. 开工自检（三行，不对就停）

```bash
git log --oneline -1     # 期望 b379cd8 08.05_f10_check_mep_run_profile_signature
git status --short       # 期望：无 src/ tests/ 的未提交改动；3 个 case_tests 未跟踪目录属已知、不要动
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```

⚠️ **主工作树里有 3 个未跟踪的 case_tests 产物目录**（待用户定去留）。
**⛔ 绝不 `git add -A`**；本单不需要你提交任何代码。

## 1. 现象（唯一已知事实）

F-10 刚修完（`b379cd8`），4_mep 的硬崩已解除。用**正确签名**跑真实 `check_mep` ⇒ 仍被阻断：

```
mep.load_to_schedule: 14 load schedule reference(s) are missing or undefined
```

该检查在 [`src/validator/checks/mep.py:556`](../../../src/validator/checks/mep.py)，层级 **`INVARIANT`**
⇒ **任何 run_profile 都阻断**（`disposition()` 对 `mep.*` profile-无关，见 F-10 轻门）。
⇒ **这是当前挡在 5_intakeoutput 前面的唯一一堵墙**，而 5_intakeoutput 至今零证据。

**已知的只有这一句报错。它是什么性质 —— 未裁定，就是本单要你查的。**

## 2. 复现路径（零 LLM 成本，产物已在盘上）

探针 A 的 4_mep 产物已落盘，**不需要重跑 LLM**：

```
case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped/4_mep/
  ├── mep_output.json     # run_mep 的结构化产出
  ├── mep_raw.txt         # LLM 原始回复
  └── mep_thinking.txt
```

`run_mep` 实现在 [`src/agent/pipeline.py:772`](../../../src/agent/pipeline.py)。
检查侧的取数逻辑见 `mep.py` 里 `_hvac_schedule_refs` 附近（`sched_bad` 是怎么攒出来的）。

**⇒ 建议先离线跑一次 `check_mep(mep_output, ...)` 拿到 `evidence.offenders` 那 14 条具体是什么。**
（怎么跑你自己定；⛔ 不要为此改生产代码。）

## 3. 边界

- ⛔ **不改任何 `src/` / `scripts/` / `skills/` 生产代码**（本单是调查）
- ⛔ **不改任何测试**
- ⛔ **不放宽、不绕过 `mep.load_to_schedule`**
- ⛔ **不碰 `case_tests/` 下任何未跟踪目录**
- ✅ 可以写一次性脚本，但**放 `/tmp`**，不要落回仓库
- ✅ 可以读 git 历史（`git log -L` / `git log -S` 很有用）

## 4. 请你回答的（这就是交付物）

1. **那 14 条具体是什么？** 逐条列出：哪个 load 对象、引用了哪个 schedule 名、那个名字在产物里到底存不存在。
2. **⭐ 定性**：这是 **①LLM 产出质量问题**（模型该生成而没生成）、还是 **②`run_mep` 的接线缺陷**
   （prompt/schema/后处理让它结构上产不出）、还是 **③检查侧取数口径不对**（schedule 其实在，检查没找到）？
   **给出判据，不要给印象。**
3. **⭐ 2–3 个修法选项，每个写清后果与代价**（含"什么都不改会怎样"）。**⛔ 不要动手修。**
4. **是不是和 F-5/F-7/F-10 同族**（接口错位 / 测试绿而真链路崩）？是就说明是哪一种形状，不是也直说。

## 5. 证据纪律（本轮新立，硬要求）

> **⛔ 不接受「我看了 / 我读了 / 我核实过」作为结论依据。**
> 每条结论必须给出**我能独立重跑的东西**：具体命令、具体文件路径 + 行号、具体数字。
>
> **缘起**：08-05 一份调查报告写「我读了源图逐位核实」并据此定性，
> 事后发现它读的是一张**左右完全对称**的图（镜像与否长得一模一样）⇒ **该证据零分辨力，结论是错的**。
> **凡涉及"方向/左右/对称"的判断，必须先证明载荷本身不对称。**

## 6. 交付

调查日志落 `AI_agent/logs/reviews/execution/2026-08-06_wall3_mep_schedule_investigation_glm.md`。
**先落骨架再补内容**（会话可能被 OOM 中断，做完一件存一件）。
**⛔ 不要 commit、不要 push**（本单零代码改动，只有一个日志文件）。

## 7. 停下上报的合法出口（**记功不记过**）

本轮至今 **7 次「施工席停下上报」，7 次都是派工方（我）的题错了**，零次是施工方能力问题。
以下任一情况**立刻停下上报**：本单陈述的事实与你看到的不符 · 基点/路径不对 ·
你认为这个问题的提法本身有问题 · 你查到一半发现真相与本单的框架不兼容。

**如实说「做不到」或「你的题错了」不受惩罚，反而是本项目最有价值的产出之一。**
