# 派工单 · 补窗的归档 drift + `audit_completeness`（GPT 施工 / Claude 审）

> **派工方** = orchestrator（claude-opus-5）　**执行方** = GPT 席位（`gpt-6-astra`）
> **工作目录写死 `/tmp/w1_windows_claude`**，分支 `wt/09.08_windows`，基点 `c7513af9`
> ⚠️ **这棵树不是你上一轮那棵**。上一轮你在 `/tmp/w1_flow_glm` 修四堵墙（已全部合并进本树）。

## 〇 · 为什么是你做

这段代码（造窗 + 重放镜像）是**主控写的**，⛔ 主控审不了自己。
⭐ 而且主控已经**停在猜测边缘**：连续三轮「改一处→重跑→换一个错」后，
上一轮列的三个可能原因**全是推测、一个都没量** —— 所以停下来交接，⛔ 不是因为难。

## 一 · 当前状态（主控实测，⛔ 非转引）

**✅ 已跑通**（走生产入口 `run_stage.py`，⛔ 不是离线探针）：
`1_correction/as_drawn_window_account.json` 落盘 ——
**34 个立面洞口 → 造出 31 个窗**；3 个未分类（实测=门）；2 个平面孤儿。
`finalize` 全段通过：造窗 → `resolve_window_hosts` → `derive_window_evidence_ledger`。

**⛔ 卡点**：归档时
```
chain_replay.py:287  ValueError: chain_replay_producer_drift
  the chain replayed from the frozen compilations assembles a different producer
  than the marker carries
```
⇒ `run_win_e2e/1_correction/attempts/` **为空**（没有一次归档成功）。

## 二 · 任务 A：定位并修掉 producer drift

**背景**：生产侧在建 marker **之前**调 `as_drawn_windows.populate_as_drawn_windows`
把 31 个窗填进几何（`run_stage.py` 的 `_draw_correction_as_drawn`）。
主控已给 `chain_replay.replay_as_drawn_chain` **补上同一个调用**（`c7513af9`），
但 producer **仍然 drift**。

⭐ **下一步应该做的是【把两个 producer 逐字段 diff 出来】，⛔ 不是继续猜。**
主控没做这一步，就是因为不想在树里留临时诊断——**你可以做，但用完删掉**。

⛔ **红线**：⛔ **不许放宽那个字节比较**。它是 F-22 BLOCKER-1
「producer/ring/cells 被一起改得内部自洽」那种伪造的**唯一拦截点**；
它这次报 drift 是**正确工作**（主控往 producer 加了 31 个窗，它发现重放复现不出来）。
修法只能是**让重放真正镜像生产方的推导**。

⛔ **停下上报触发器**：若你发现生产侧与重放侧**结构上不可能产出同一份 producer**
（例如生产用了重放拿不到的输入），**停下报** —— 那意味着设计要改，⛔ 不是接线问题。

## 三 · 任务 B：`correction.audit_completeness`

```
⛔ correction.audit_completeness: geometry was changed (or relied on testdata) but
   no correction/conflict was recorded — attribution to 0_reading would be erased
```
判据在 `src/validator/checks/correction.py:502 _audit_completeness`（:138 调用）。

**你上一轮自己报的病因**（本单原样引用）：
> `_make_draw_fn` sets `relied` from testdata file existence, while the as-drawn
> finalize emits empty corrections/conflicts.

⇒ 又是「legacy 形状的假设套在 as_drawn 腿上」这一类。
⭐ 修法要问的是：**as_drawn 腿上，「归因到 0_reading」这件事由什么承载？**
它的几何是确定性投影出来的、没有 LLM 改写动作，所以 corrections 为空是**诚实的**；
但 `relied` 说它依赖了 testdata ⇒ 两者必有一个说错了。⛔ 别直接把门关小。

## 四 · 验收

1. **全量 `0 failed`**：
   `cd /tmp/w1_windows_claude && PYTHONPATH=/tmp/w1_windows_claude /opt/venv/bin/python -m pytest -n 6 -q`
   ⛔ **禁 `uv run`**（它会重同步共享 `/opt/venv`；你上一轮正是因此停报，派工方已改口径）。
2. ⭐ **任务 A 的判据是一个读数，⛔ 不是「不报错」**：
   `run_win_e2e/1_correction/attempts/001/output.json` 里 **`windows` 的长度 = 31**。
   ⚠️ **「归档成功」不等于「窗跑通了」** —— 主控上一轮正是被这个骗过：
   那次 `attempts=3 / accepted=3` 看上去像跑通，实际 `windows=0`（造窗没接线）。
3. 跑 flow 要凭据：`set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a`

## 五 ⭐⭐⭐ 分段提交：三个触发点（这个写法实测有效，⛔ 别退回「记得提交」）

- **A** 准备**开始下一段之前** → 先 commit（哪怕半截，写 WIP）
- **B** 准备**跑全量之前** → 先 commit
- **C** 准备**写交件之前** → 先 commit 代码

⛔ 只 `git add` 明确路径，禁 `git add -A`；commit 前必看 `git diff --cached --numstat`。

## 六 · 交件

`AI_agent/logs/reviews/execution/2026-09-08e_window_drift_execution.md`，末尾要有「我这次最薄弱的一处」。

## 七 · 停下上报

⭐ 历史读数 **73/73 全是派工方的题错**，你上一轮**两次**停报都对（`uv run` 自相矛盾、
W#1 的零分判断错）。觉得单子哪里不对，**大概率真是我错了** —— ⛔ 别绕过去。
