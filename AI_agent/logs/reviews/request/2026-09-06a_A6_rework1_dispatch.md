# 返工单 · A-6 返工 1（阻断②：跨行不变量在 `consume()` 里没有重检）

## 〇 状态与分工

- 交件已被 **Claude 家族跨家族审**判为 **REWORK · 阻断 2 · 不阻断 3**，
  裁决书：`AI_agent/logs/reviews/verdict/2026-09-05m_A6_tick_claim_block_crossreview_claude.md`（可从对象库取，见 §四）。
- ⭐ **先说好消息**（这些复核方独立复算过，⛔ 本轮不要重做）：
  - 独立全量 **3877 passed / 0 failed**，与你的读数**完全一致**；`3850 + 27 = 3877` **逐位闭合差额 0**。
  - R-1..R-4 **四条全部核实通过**；§三你自设的两条同形输入**站得住**，复核方自造的三链版本也通过。
  - 抽 3 条最承重的锁做变异，**三条全部真红**（不是恒红结构）。
  - 攻击 3（`__class__` 重赋值）**被逐字节内容比对挡住** —— ⭐ 复核方明确记为**正面发现**：
    挡它的是**内容比对**而不是 `isinstance`，**比 B2 当时的对应设计更强**。
  - canonical JSON（`freeze()`）在 int/float、`-0.0`/`0.0`、NaN 边界上**没找到坍缩**，也是正面发现。
- **阻断① 已由主控自行销账**，⛔ **不在本单范围** —— 那三句被删的接线承诺已写进
  `AI_agent/plan.md` 的 E-a 行，成为 **E-a-1 / E-a-2 / E-a-3** 三条可查验收项。**你不用管它。**
- ⇒ **本单只做阻断②。** 工作目录 `/tmp/a6_tickclaim_astra`，分支 `wt/09.05j_a6_tick_claim`，
  当前 HEAD `94e899e5`。⛔ 不要 rebase，⛔ 不要动 `src/agent/judge/`。

## 一 ⛔ 阻断②：区间倒置能穿过 `consume()`

复核方的实测输出（`attack_probe_2_chain_reorder.py`）：

```
O02:x0 legitimate candidate values (u): [0, 10000, 20000, 30000]
O02:x1 legitimate candidate values (u): [0, 10000, 20000, 30000]
legit submit() rows (x0,x1): [('O02:x0', 10000), ('O02:x1', 20000)]
FORGED consume() result: x0=30000 x1=0  inverted=True
CONFIRMED: consume() accepts an interval-INVERTED chain-backed batch built
from two individually-legitimate, pre-existing candidates of each edge.
```

**机制**（行号已回文件 `grep -n` 核过）：

- `TickSession.submit`（[`tick_claim.py:426`](../../../../src/agent/correction/tick_claim.py#L426)）里的
  `by_id` 循环（**469–478 行**，`if high and row["value_u"] >= by_id[high]["value_u"]`）
  是这批数据**唯一一次**被验证跨行顺序的机会。
- `TickSession.consume`（**493 行**）对**每一行的数值**都从冻结包重新 `evaluate()` 并核对，
  两行数值**各自都对得上**（`30000` 确实是 x0 那条链 node3 的真值，`0` 确实是 x1 那条链 node0 的真值）
  —— **但跨行的 `lo < hi` 从未在 `consume()` 里重核**。
- `OpeningReview.__init__`（[`opening_adjudication.py:178-179`](../../../../src/agent/correction/opening_adjudication.py#L178)）
  把 `value_u` 直接写进 `along_lo_m`/`along_hi_m`，**全程没有 `lo < hi` 校验**。

⇒ 倒置的假区间会**一路静默流进洞口几何**。
⚠️ **这不需要有人恶意攻击** —— 未来一次重构里的普通 bug（谁在 `submit()` 之外设了 `_current`）就够了。

### ⭐⭐⭐ 但本单要修的不是这一个例子，是这一类

复核方按「反查哪个方向没有锁」给了答案：把 `submit()` 已有的顺序检查搬进 `consume()` 重跑一次，
对所有合法批次是**无操作**、**不会打红任何现有测试** ⇒ **不存在「加了就会红」的理由挡着这把锁**。

**⇒ 你要交的不是「补一个 `lo < hi`」，而是回答下面这个问题并按答案施工：**

> **`submit()` 里做过的每一项检查，`consume()` 各自重做了没有？**

做法：把 `submit()`（426 行起）的检查**逐项列成表**（每项：检查什么 · 在哪一行 · `consume()` 有没有重做 · 在哪一行）。
- 凡是 `consume()` **没有**重做的，逐项判断：**是该重做**（⇒ 补上），还是**结构上不必**（⇒ 写明为什么，
  并说明「如果它被绕过，坏数据会流到哪里、被谁接住」）。
- ⭐ **这张表本身就是交付物**，它把「修好了这个例子」变成「修好了这一类」。

### 硬约束

- ⭐⭐⭐ **修法必须是【出口全检】，⛔ 不是【入口收窄】。**
  本项目 09-05 已**正面证明**过：入口收窄不属于有效解那一族 —— B2 返工 3 自造五类攻击，
  **三类把入口封印整个绕过去**（`deepcopy` 走 `cls.__new__` · 私有 minter 可外部调用 · `__class__` 重赋值不触发钩子），
  **全部由出口全检接住**。
  ⇒ ⛔ **不要**靠「把 `_current` 改成更私有的名字」「加类型钉」「禁止外部赋值」来修；
  ⛔ 也**不要**把 `attack_probe_2_chain_reorder.py` 这个具体反例串写进任何黑名单。
- **建议双点加固**（复核方原话）：`consume()` 补跨行重校验 **+** `OpeningReview.__init__`
  组装 `along_lo_m/along_hi_m` 处加一道防御性断言。第二点是纵深，⛔ 不能替代第一点。
- 新增的拒绝出口要**具名**（与既有 `TICK_*` 出口同风格），⛔ 不要裸 `AssertionError`/裸 `ValueError`。

## 二 ⭐⭐⭐ 验收（三条，缺一不合格）

1. **改动前复现得出**：在 `94e899e5` 上跑复核方的探针，攻击**成立**。
2. **改动后复现不出**：同一探针，被**具名出口**拒绝。
3. ⭐⭐⭐ **换同形但不同的输入，仍然走不通** —— **你自己造至少两条**，⛔ 不许只用复核方那一条。
   同形的定义是「**跨行不变量在 `consume()` 处缺失**」，⛔ 不是「区间倒置」这一个症状。
   提示（⛔ 不是穷举，你要自己找）：`z_low`/`z_high` 那一对 · 一条边上多于两行时的**中间行互换** ·
   **跨边**的行被搬到另一条边名下 · 覆盖完整但**行数对不上**的组合。

> ⛔ **①② 只验证「这个例子修好了」，③ 才验证「这一类修好了」。**
> 08-27 实测：①② 双绿，而唯一新加的 ③ 一次抓出全部 3 条阻断。

## 三 跑测与纪律

```sh
cd /tmp/a6_tickclaim_astra && \
python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
```

- ⭐⭐⭐ 两条 `m.__file__` **必须落在 `/tmp/a6_tickclaim_astra` 里**（承重不变量，⛔ 不是 `.pth` 哈希）。
- ⛔ 一律 `-n 6`。**判跑完看汇总行**，⛔ 不看退出码文件、⛔ 不用 `nohup`。
- **基线是 3877**（复核方独立复算过）。新增测试会把它推高，**逐位闭合要你自己数**：
  `3877 + 你新增的条数 = 新读数`，差一条都要说明差在哪。
  ⚠️ 预期你补的这道锁**不会打红任何现有测试**（复核方已论证）；**若真打红了，那本身是重要发现，要写清**。
- ⛔ `pip install -e .` 或任何写 `site-packages` 的命令。
- ⛔ `git add -A`；逐路径 add，commit 前看 `git show --cached --numstat`。
- ⚠️ `.gitignore:258` 有 `*.txt`，新增 txt 证据必须 `git add -f`，否则**静默丢件**。
- ⭐⭐⭐ **必须分段提交**：⚠️ 你在上一单里**三次**撞 `Selected model is at capacity` 退出，
  **三次都发生在活干完之后**，靠分段提交才一行代码没丢。这次照做。

## 四 需要读的东西（都在共享对象库里，用 `git show` 取，⛔ 不要去别的 worktree）

```sh
git show 6ffb1429:AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/attack_probe_2_chain_reorder.py
git show 6ffb1429:AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/probe_outputs.txt
git show ad14f742:AI_agent/logs/reviews/verdict/2026-09-05m_A6_tick_claim_block_crossreview_claude.md
```

## 五 交件

`AI_agent/logs/reviews/execution/2026-09-06a_A6_rework1_execution.md`，必须含：

- **`submit()` 检查逐项对照表**（§一的核心交付物）
- **三条验收各自的命令原文与输出原文**
- **你自己造的两条同形输入是什么、为什么它们同形而不同**
- **完整全量汇总行 + 逐位闭合**（自己数）
- **最薄弱一处**（⛔ 不许写「无」）

⛔ 不许留占位符。

## 六 ⭐ 停下上报（分层）

- **A 层（停）**：① 本单或裁决书的**承重前提**你发现是错的（⭐ 包括：你论证下来
  「`consume()` 重做 `submit()` 的某项检查」**会**打红现有测试 —— 那说明前提错了）
  ② 要动 §三 禁令 ③ 会改到已落库产物的哈希或已签字基线。
- **B 层（记一条继续）**：行号 / 措辞 / 外围数值不一致。

> 本项目至今 **69/69** 次「停下上报」全部是**派工方的题出错** ⇒ 该停就停，⛔ 不要自行绕路。
