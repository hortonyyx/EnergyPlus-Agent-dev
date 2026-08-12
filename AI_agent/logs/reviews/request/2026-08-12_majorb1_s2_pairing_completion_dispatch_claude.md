# 施工单 · MAJOR-B1 补齐 —— F-9 S2 的 pairing decision 做完整

- **日期**：2026-08-12 · **席位**：Claude 侧 Sonnet · **审**：GPT 侧 sol
- **来源**：[sol 第二轮裁决](../verdict/2026-08-12_round2_blocker1_and_bcd_crossreview_sol.md) `MAJOR-B1`
- **用户 2026-08-12 拍板 = 选项 A「补齐」**（⛔ 不走「改名为部分交付」那条）
- **前置已落库**：`21b4739`（S0/S1）+ 本日提交（S2 首版 + 摊 C/D/E）。基线 = **2539 / 10 xfail / 0 红**。

---

## 第 0 步 · 防假验证自检

在你要改的判定点写**一句必抛异常**，跑你打算用的验收命令，确认**真的抛了**。不抛 ⇒ 停下上报。

> ⚠️ 本项目今天两次栽在探针上：orchestrator 的 neuter 探针**对照组本来就是空的**（用错集合名 + 少传参数），
> 差点误判「未接线」。**⇒ 每个探针必须先自证「我看得见目标」，再断言目标变没变。**

---

## 1. 要补什么（设计稿 §5.3 的条件 2 / 3 / 4）

现状 = shadow 只验「模型已引用的那一对是否在容差内、z-scope 是否匹配」。
**设计稿 §5.3 的通过条件有六条，缺的是**：

- **条件 2 · 唯一 mutual-nearest**：在 `E_i` 所属 elevation view 的**同一已解析 `scope_id` / facade 候选域**内，
  cited `(P,E_i)` 必须是唯一 mutual-nearest pair —— `E_i` 是该 view+scope 内离 `P` 最近的 elevation，
  且 `P` 也是该 scope 同 `floor_ref` plan 域中离 `E_i` 最近的 plan。**不同 elevation view 不互相竞争。**
- **条件 3 · ambiguity margin**：最优与次优距离之差必须大于纯数值 ambiguity epsilon。
- **条件 4 · source 不复用**：全 draw 的 position source 分配无重复。

**⛔ 三条硬约束（稿子原文，不许打折）**：
1. **scope 过滤必须发生在距离计算和 mutual-nearest 排名【之前】** ——
   其他楼层 / z-band 的 stroke **不得进入**该 window 的「次优候选」，
   ⛔ **不能先制造同分再报 ambiguity**。
2. **⛔ 代码不得拿 window 的 citation 或 plan 距离去替 elevation source 猜 scope**（堵死循环论证）。
3. **发现更匹配的未引候选 `E*` ⇒ 结果是 `position_evidence_pair_mismatch`，⛔ 绝不能把 `E_i` 改成 `E*`。**
   catalog 自身同分 / 重复投影 / 缺 channel ⇒ `position_evidence_insufficient`，⛔ 不是反复抽模型。

**⭐ 稿 §12.2 已经写死一把锁**：**「删掉 mutual-nearest 后专用夹具必须转红」** —— 必须兑现。

---

## 2. ⚠️ 一条被 sol 实测证伪的说法（⛔ 不要沿用）

orchestrator 上一份请求书写过「`position_evidence_pair_mismatch` 没有 mutual-nearest 就结构上不可能触发」。
**这句是错的** —— sol 动态验证出两条既有触发路径：① 端点距离超 pairing tolerance；
② cited elevation 的 z-scope 解析到别的楼层（along 距离仍在容差内）。
⇒ **不要拿「这个码能不能触发」当 mutual-nearest 是否存在的判据**，要直接测排名行为本身。

---

## 3. ⭐ 同时要解决 MAJOR-B1 的语义问题（即使补齐了也要做）

sol 的原话：shadow 用**无修饰的 `accepted` / `PASS`** 表达只覆盖部分判据的结果，
产物又**没有机器可读的 coverage** ⇒ **把结论说得比证据强**。

⇒ **decision 必须结构化记录**：`decision/ruleset version` + **`evaluated_conditions`** + **`unevaluated_conditions`**。
⛔ **不能只写自由文本备注。** 补齐之后 `unevaluated_conditions` 应为空 —— **但这个字段必须存在且被锁住**，
使将来任何再次的部分实现**不可能悄悄冒充完整**。
**（这正是本项目今天反复现形的那条：一个「通过」不能看起来比它实际意味着的强。）**

---

## 4. 锁

- **§12.2 那把**：删掉 mutual-nearest ⇒ 专用夹具**转红**。
- **条件 3**：构造「最优与次优距离差小于 epsilon」的真实形态 ⇒ 必须报 ambiguity，**不许硬选一个**。
- **条件 4**：构造两扇窗抢同一个 source ⇒ 必须拒绝。
- **⭐ 顺序锁**：构造一个「别楼层 stroke 距离更近」的形态 ⇒ **scope 过滤若晚于排名就会误判**，此锁必须钉住顺序。
- **coverage 锁**：把某个条件从 `evaluated` 挪到 `unevaluated` ⇒ **消费方必须拒绝**把它当完整判定用。
- 每把锁**自证前提**；⛔ 恒等锁不算正确性锁；⚠️ 遮蔽自查（「有没有第二条防线先把这个变异拦下」）。
- **neuter 至少两个方向**，且**必须覆盖接线**（中和共享实现看调用点跟不跟着变），
  ⛔ 不许用 grep / AST 形状匹配。

## 5. ⛔ 硬纪律

1. **⛔ 派工方错误率 15/15**。本单里凡描述**岔口 / 分类 / 数量 / 位置**的句子都可能是错的前提。
   **⭐ 但本轮规矩分层（新）**：
   **① 承重前提错（错了则任务方向作废）⇒ 停下上报；
   ② 外围论据错（不改变任务方向）⇒ 报告后【继续做完其余部分】。**
   ⛔ 不要因为一句外围描述有误就停掉整单 —— 那已经连续两轮让主体没人审。
2. 验锁 neuter **只在 `/tmp` 做**，做完还原。⛔ 不要 `git checkout/stash/clean/reset`。
   （本单**允许** `git add`/`commit` 自己的改动吗？**⛔ 不允许** —— 提交由 orchestrator 统一做。）
3. 跑测用**独立新文件名**落日志与退出码，判跑完**看 `N passed` 汇总行**。基线 **2539 / 10 xfail / 0 红**。
4. 改 `src/` 前备份到 `backup/src_history/2026-08-12_majorb1/`。

## 6. 输出

执行记录落 `AI_agent/logs/reviews/execution/2026-08-12_majorb1_s2_pairing_completion_claude.md`：
改了什么 · 每把锁绑什么 + 自证前提实测 · neuter 两方向 · **`unevaluated_conditions` 补齐后是否为空** ·
全仓汇总行 · **未验证项与不确定判断（如实列出）**。
