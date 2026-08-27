# 跨家族复核单 · F-126（denominator 空分母响亮失败）

- **日期**：2026-08-29 · **复核方**：GLM（glm-5.3）· **施工方**：Claude 执行档 · **派工方**：orchestrator（Claude 主控）
- **被审 commit**：**`48f1d10`**（分支 `08.23_AsDrawnReading`，⛔ 未 push）
- **原派工单**：`AI_agent/logs/reviews/request/2026-08-29_f126_denominator_loud_failure.md`
- **⛔ 你只看**：原派工单 + `git show 48f1d10` + 测试输出。**⛔ 不要看施工方的长篇自述**（本单已把必要事实摘出来）。

---

## 一、⚠️ 先看这条：**派工方（我）的题面错了，而且是承重的**

原派工单 R2 写的是：

> 「**上游有 BLOCK 诊断**（哈希门 / S0 失败等）⇒ 响亮失败，错误信息里点名那些诊断码」

**这条按字面不可实现。**施工方发现并已由 orchestrator **独立复现**：

```
把 as-received DXF 配一份重新签名的 request（绕过哈希门）喂进 plan-F1：
  targets = 108（非空）
  诊断 = tarch_wall_nonorthogonal×2 [BLOCK] + tarch_wall_free_end×1 [BLOCK]
        + tarch_interior_opening_excluded×13 [INFO] + tarch_wall_degenerate_line×1 [INFO]
```

⇒ **「有 BLOCK」与「分母不可用」不是一回事**。若照我的字面实现，**L4 自己的夹具会先抛异常**。
我写题面时只想到了哈希门，没想到 `tarch_wall_nonorthogonal` 也是 BLOCK。**这是派工方题错第 39 次。**

**施工方的处置**：把触发条件改成「**分母为空**」，再按有无 BLOCK 分两个 reason；
「**有 BLOCK + 非空分母**」仍照常返回，只是那些码现在随 `diagnostics` 出来。
它把这个偏离写进了 docstring 与 commit body，并声明「判它可不可判分是策略问题，本文件不拥有」。

---

## 二、⭐ 请你回答的四问（第 1 问最重要）

### 1. ⭐⭐ 这个偏离对不对？它是不是只把病挪了个位置？

`diagnostics` 现在**出得来**了，但**消费方（`as_drawn/reading_grade.py`）并不看它**。
⇒ 一份「从有 BLOCK 级拓扑问题的图算出来的分母」照样被正常判分，没人被迫表态。

**问**：这是不是把 F-64 那个「零产出不报红」的形状，从**生产方**挪到了**消费方**，
而 F-126 只关掉了其中一半？如果是，缺的那一半该由谁、在哪一层补？
⚠️ **⛔ 不要只回答"应该让消费方也检查"** —— 请给出**判据**：在什么条件下一个带 BLOCK 的分母仍然可判分。

### 2. ⭐ 再找一种能骗过这 4 把新锁的**真实错误形态**

⛔ 不是造一个合成 bug，是「**哪一种真实的改法会让 L1–L4 全绿而缺陷仍在**」。
（上一轮你在同类问题上找到过 `os.walk` 那条回退腿 —— 就按那个标准。）

### 3. L4 的存货方向真的对吗？

L4 要验「被丢弃的非正交线段清单」。**签字件在这个方向上实测存货 = 0** ⇒ 拿它做夹具，`len==count` 是 `0==0`，
对「根本没建这个清单」的代码也全绿。施工方改用 `as_received` + **在 `tmp_path` 里重新签名**的 request 造存货。

**问**：这算不算**另一种**「病灶方向没存货」？重新签名这个动作本身有没有引入新的盲区
（比如它顺带绕过的东西，正好是别的锁在守的）？

### 4. 换**同形输入**仍然走不通吗？

只验证「sm25 `plan-F1` 这个例子修好了」不算数。
**问**：换另一个 case（`sm24_anchor`）、或另一个 view（`plan-F2` / elevation），这条路是不是**仍然**走不通？
还是这次修法只在一个例子上成立？

---

## 三、事实清单（orchestrator 已逐条独立复现，⛔ 你可以不信，请自己再跑）

| | 读数 |
|---|---|
| `git diff --numstat HEAD~1` | `6 13 scripts/tool_scripts/affected_tests_rules.yaml` · `129 4 src/agent/judge/as_drawn/denominator.py` · `244 0 tests/test_as_drawn_denominator_f126.py` |
| 全量 | `3146 passed, 13 xfailed, 212 warnings in 1025.53s`，`PYTEST_EXIT=0` |
| 算术 | 上一次权威全量 **3138** + 新增 **8**（6 个 `def test_`，其中 2 个参数化）= **3146** ✓ |
| `.pth` 前后哨兵 | `58f547fa…` 两次同值 |
| 缺陷原样 | 签字件 `plan-F1` = 110 targets / 31 openings / 225 segs；`_as_received` 配签字 request = **全 0 且函数正常返回**，顶层键恰好 9 个 |
| 第三个文件为何被碰 | 仓库自己的覆盖诚实门发现 `denominator.py` 不再是「无测试」，而 allowlist 条目原文写着 "…directly **yet**" ⇒ **移出 allowlist**（= 收紧，不是放松），并留注释禁止为消红再加回来 |

**施工方自报的变异矩阵**（⛔ 请抽验，别照收）：撤 `raise` ⇒ L2×2/L2b/L3 四红 · 撤 `diagnostics` 键 ⇒ L3 红 ·
两个 reason 压成一个出口 ⇒ L2b 红 · 清单恒为 `[]` ⇒ L4 红 · **L4 夹具换成签字件 ⇒ L4 红**（陷阱验证）。

---

## 四、裁决格式

`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT`，**逐条 finding 标阻断/不阻断**，
每条给**可复现命令 + 实测数字**。⛔ 不要复述我的话，⛔ 不要只给意见。

⚠️ **跑测请用 `pytest -n 6`**（⛔ 不用 `-n auto`），⛔ **绝对不许跑 `pip install -e .`**（venv 全机器共享）。
⛔ 不要修改工作树（只读复核）；要改请在裁决里写清楚该怎么改。
