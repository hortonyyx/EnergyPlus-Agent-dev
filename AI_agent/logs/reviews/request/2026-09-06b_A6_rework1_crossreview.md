# 复核单 · A-6 返工 1 跨家族复核（Claude 家族）

## 〇 你是谁、审什么

- **你是 Claude 家族的独立复核方。施工方是 GPT-6 astra，⛔ 你不是作者，也不得替它改代码。**
- 工作目录 **`/tmp/a6rw1_review_claude`**（detached HEAD `e89908cd`）。⛔ 不要动主树、不要动 `/tmp/a6_tickclaim_astra`。
- 审阅范围：**`94e899e5..e89908cd`**（返工产生的四段提交）：
  ```
  5daa395a  test(a6): preserve pre-fix consumption invariant reproduction
  38bd8f5f  fix(correction): replay complete tick decision invariants at consumption
  4c223571  docs(a6): account for every submit check at the consumption exit
  e89908cd  docs(a6): deliver rework proof and reconciled full-suite results
  ```
- 必读（都在树里）：
  - 返工单 `AI_agent/logs/reviews/request/2026-09-06a_A6_rework1_dispatch.md`
  - **上一轮裁决书**（阻断②的出处）`AI_agent/logs/reviews/verdict/2026-09-05m_A6_tick_claim_block_crossreview_claude.md`
    —— ⛔ 该文件在本 worktree 的基点之前，用 `git show ad14f742:<path>` 取（共享对象库）
  - 施工方交件 `AI_agent/logs/reviews/execution/2026-09-06a_A6_rework1_execution.md`
  - 证据目录 `AI_agent/logs/experiments/2026-09-06a_A6_rework1/`

### ⛔ 不在本轮范围（⚠️ 但你可以核我做得对不对）

**上一轮的阻断① 已由主控自行销账**：施工方按合法出口删掉的三句接线承诺，已写进主树
`AI_agent/plan.md` 的 E-a 行成为 **E-a-1 / E-a-2 / E-a-3**。用 `git show c21b93ae:AI_agent/plan.md` 可读。
⭐ **若你认为这个销账不成立**（比如三条验收项写得不可机械执行、或漏掉了删句里的某个承诺），
**请直接写进裁决书** —— 那是**主控的错**，不是施工方的。

## 一 ⭐⭐⭐ 本轮第一优先：那张「17 项对照表」的**完整性**

返工单要求的核心交付物不是「补一个 `lo < hi`」，而是回答：
**「`submit()` 做过的每项检查，`consume()` 各自重做了没有？」**

施工方交了一张 **17 项**的表（交件 §二，独立版本在 `experiments/2026-09-06a_A6_rework1/submit_consume_checks.md`），
并**自报**除了上一轮已知的第 14 项（区间顺序）外，还找出**另外六项** `consume()` 从未重做的检查：

| # | `submit()` 检查的 | 施工方自报的旧 `consume()` |
|---|---|---|
| 2 | 响应类型与 `packet_id` 对应本包 | 没重验响应 |
| 6 | `reperceive` 不能冻结为事实 | 没核 action |
| 10 | `pixel_pending_evidence` 必须有 `missing_chains` | 没有 |
| 11 | `debt_id` 按本图/边/缺链生成 | 没有，原样导出 |
| 12 | `retired_debt_id` 仅同源同边、无缺链 | 没有，也不导出 |
| 13 | 每行 axis/pointer/witness 来自对应源边 | 部分 |
| 15 | schema/source/image/generation/response 同一记录 | 部分 |

⭐⭐⭐ **你要核的第一件事是：17 是不是【全部】。**

这是**立门三问的第 ② 问**在文档上的形态：**「`submit()` 的检查」这个名词的外延，能不能被换掉？**
施工方自己意识到了这一点（表头写「包含原 submit 的拒绝检查、**条件落值和账字段构造**；**提交副作用也列明**，
避免以『不是 if』漏掉约束」）——**但这仍然是它自己划的外延**。

⇒ **你必须独立枚举一遍**，⛔ 不许照着它的表核。至少用两套互不依赖的口径，例如：
- 逐行读 `94e899e5` 版本的 `submit()` 全文（`git show 94e899e5:src/agent/correction/tick_claim.py`），
  把**每一个 `if`/`raise`/赋值/字典构造**都标号；
- 以及一套**不依赖阅读顺序**的口径（比如：`submit()` 能抛出的**全部**具名 code 集合，
  对照 `consume()` 能抛出的集合，看差集）。
- **两套口径的结果不一致的地方，就是要写进裁决书的地方。**

## 二 ⭐⭐ 第 3 / 16 / 17 项：「结构上不必重做」是理由还是借口

施工方对三项**没有**照搬，各给了理由（原文见交件 §二 表末段）：

- **#3** current 必须尚未终结 —— 「消费要求已有 current，消费不承担再次提交」
- **#16** `digest(record)→current` 与追加 history —— 「**提交副作用**而非可重复执行的验证；
  ⭐ **改坏 current 的普通赋值仍可进行，内容出口会重检，未新增封印或私有名字屏障**」
- **#17** 成功提交后从待退债集合移除已 retired 项 —— 「若直接拿已清空的**提交后** map 重放，
  **会误拒合法批次**，所以重检前提而不重做副作用」

**逐项做对抗检验**，每项回答同一个问题：
> **如果这一项在 `consume()` 处确实不重做，那么一份【绕过 `submit()` 被塞进去的】坏数据，
> 具体会流到哪里、被谁接住？指到行。若答案是「没人接住」，这就是新的阻断。**

⭐ **#16 的措辞值得特别肯定也值得特别验**：它明确说**没有**加封印/私有名字屏障 ——
这正是本项目「⛔ 入口收窄不是有效解，出口全检才是」的口径。**实测它说的是不是真的**：
`session._current = <你伪造的 TickBatch>` 这条路**应当仍然走得通**（赋值不报错），
而**内容在 `consume()` 出口被全检拒绝**。⛔ 如果它其实是靠「让你赋不进去」挡住的，那就是入口收窄，要记。

⚠️ **#17 的理由是可证伪的**：它声称「拿提交后 map 重放会**误拒合法批次**」。**造一个合法批次去验证这句话**
—— 若实测不会误拒，那这条理由不成立，`consume()` 就应该重做它。

## 三 ⭐⭐⭐ 三条复核（缺一不合格）

1. **改动前复现得出**：在 `94e899e5` 上，上一轮那条攻击**成立**
   （复核方原探针：`git show 6ffb1429:AI_agent/logs/experiments/2026-09-05m_A6_tick_claim_crossreview_claude/attack_probe_2_chain_reorder.py`）。
2. **改动后复现不出**：在 `e89908cd` 上，被**具名出口**拒绝。
3. ⭐⭐⭐ **换同形但不同的输入，仍然走不通** —— **你自己造**，⛔ 不许只用施工方或上一轮造的那些。
   ⭐ **同形的定义按【类】不按【症状】**：「跨行/跨字段不变量在 `consume()` 处缺失」，
   ⛔ 不是「区间倒置」这一个症状。**优先攻上表里那六项新补的**（#2/#6/#10/#11/#12/#13/#15），
   因为它们是**本轮才第一次有锁**的方向 —— 新锁的分辨力从未被外部验证过。

## 四 ⭐ 分辨力：这批新锁摘得动吗

本轮新增 **17 条**测试、新增/涉及这些具名出口（已回文件 `grep` 取，⛔ 未转引交件）：

```
TICK_INTERVAL_NOT_ORDERED        TICK_ROW_RECOMPUTE_MISMATCH
TICK_BATCH_RESPONSE_INVALID      TICK_BATCH_RESPONSE_MISMATCH
TICK_BATCH_METADATA_MISMATCH     TICK_BATCH_NOT_CURRENT_DECISION
TICK_DECISION_COVERAGE_MISMATCH  EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE
```

- 逐条问「**不加这处改动，这门本来红不红**」。只有负向断言的门 = 恒红，结构上不可观测。
- ⭐⭐⭐ **锁只在【夹具有存货】的方向上有牙，而存货是【检查形态】的函数**。
  ⛔ 别问「有没有对照物」，要问「**它声称覆盖的每种量，各自有没有被量到**」。
- **抽你认为最承重的 3 条做变异**（改实现让它该红），确认真的红，然后复原并确认恢复全绿。

## 五 独立读数（⛔ 不许引用施工方的数字当结论）

```sh
cd /tmp/a6rw1_review_claude && \
python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)" && \
python -m pytest -q -n 6 -p no:cacheprovider
```

- ⭐⭐⭐ 两条 `m.__file__` **必须落在 `/tmp/a6rw1_review_claude` 里**（承重不变量，⛔ 不是 `.pth` 哈希）。
  跑前跑后各打印一次。若不是，⛔ 立即停下上报。
- ⛔ 一律 `-n 6`。**判跑完看汇总行**，⛔ 不看退出码文件、⛔ 不用 `nohup`。
- 施工方报 `3894 passed / 2 skipped / 13 xfailed`，`3877 + 17 = 3894`。**自己数一遍**，差一条都要说明差在哪。
- ⭐ **特别核一句施工方的主张**：本轮新锁**没有打红任何既有测试**（3877 条全部仍绿）。
  ⚠️ 这条若成立是好事（上一轮复核方论证过「不存在『加了就会红』的理由挡着这把锁」）；
  **若不成立**（有既有测试被改动过以适配新锁），那是**放水**，要点名列出改了哪些测试、改了什么。
  ⇒ **必查**：`git diff --stat 94e899e5 e89908cd -- tests/` 里**除新增文件外**有没有既有测试文件被修改。

⚠️ **本 worktree 的基点在 A-11 合并之前**，所以这里的 3894 与主树当前的 3863 不可直接相比 ——
**这是预期的，⛔ 不要当成异常**。合并进主树后的预测值是 `3863 + 27 + 17 = 3907`，那一格由主控在合并后自己核。

## 六 交件

`AI_agent/logs/reviews/verdict/2026-09-06b_A6_rework1_crossreview_claude.md`

必须含：**头条结论**（APPROVE / APPROVE-WITH-FINDINGS / REWORK + 阻断数）·
**§一 你独立枚举出的 `submit()` 检查清单，以及它与施工方 17 项表的差集** ·
**§二 第 3/16/17 项的对抗检验结果（含 #17 那条可证伪理由的实测）** ·
**三条复核逐条读数** · **你自己造的同形输入是什么、为什么它同形** ·
**§四 变异测试结果** · **既有测试有没有被改动（放水检查）** ·
**未复现项清单** · **是否改过被审对象（如实披露）** · **最薄弱一处**。

⛔ 不许留占位符。⛔ 不许把施工方的读数当自己的读数。
⚠️ `.gitignore:258` 有 `*.txt`，新增 txt 证据必须 `git add -f`，否则**静默丢件**。
⛔ `git add -A`；逐路径 add，commit 前看 `git show --cached --numstat`。
⛔ `pip install -e .` 或任何写 `site-packages` 的命令。
⭐ **分段提交**：每完成一块提一次。

## 七 ⭐ 停下上报（分层）

- **A 层（停）**：① 本单、返工单或上一轮裁决书的**承重前提**你发现是错的
  （⭐ 包括：主控对阻断①的销账不成立）② 要动 §六 禁令 ③ 会改到已落库产物的哈希或已签字基线。
- **B 层（记一条继续）**：行号 / 措辞 / 外围数值不一致。

> 本项目至今 **69/69** 次「停下上报」全部是**派工方的题出错** ⇒ 该停就停，⛔ 不要自行绕路。
