# 跨家族复核请求 · **F-156 第六轮 / ②-1d 第四轮**（第三轮返工件）

- **日期**：2026-09-02 · **请求方**：orchestrator · **复核方**：**GPT 家族**（⛔ 不得 Claude —— 施工方是 Claude 施工席）
- **被审 commit**：**`2a5aec4`**（施工方四个原件 `f3e10ed`/`74ea447`/`0bd23fa`/`61f30b3` 逐个 `cherry-pick -x` 落分支）
- **派工单**：[第三轮返工单](2026-09-02f_f156r6_o21d_rework3.md) ·
  **前置裁定**：[停报裁定 · 题错 #71](../verdict/2026-09-02c_f156r5_stop_report_ruling.md) ·
  **上一轮裁决**：[你自己的 REWORK/阻断 2](../verdict/2026-09-02b_f156r4_o21d_crossreview_gpt.md)
- **施工方执行档**：[`2026-09-02f_f156r6_o21d_rework3_claude.md`](../execution/2026-09-02f_f156r6_o21d_rework3_claude.md)
- **被审 diff**：`src/agent/judge/answer_compiler.py` **+82/−71** ·
  `tests/test_o21d_exclusion_gap.py` **+501/−390** · `tests/test_boundary_condition_facts.py` **+25/−7**

⛔ **只看原始需求 + diff + 测试输出**，不必读执行档长篇。

---

## 一、⭐ 上一轮你打穿的两条，这一轮的修法长这样（请你验，⛔ 别采信我的转述）

**你的阻断 1**（`excluded > paired` 把诚实的按阈值排除判红）与
**阻断 2**（`excluded == paired` 放过 50% 灌证）—— 施工方**没有再调那个比例**，
而是**把两类证据在【类型层】分开了**：

- 那个"豁免凭据"字段现在是 **`Literal["below_request_area_threshold"]`** —— **只剩一个值**
  ⇒ producer 自写的 `registered_ring_loss` **在结构上根本表达不成豁免凭据**；
- `registered_ring_loss` 改走 **fail-loud**（具名 structural failure，带 cavity 与该 loss 自己的指纹）。

⇒ ⭐ **请你重点判**：这是**真的把 1:1 阈值拿掉了**，还是**换了个地方重新长出一个没签字的阈值**？
（[[threshold-hardening-is-not-recomputation]]：阈值防噪声、重算防伪造，而这里要的是**分类正确**。）

## 二、⭐⭐⭐ 请你打的三处（假说形态，⛔ 我未代判）

| # | 疑点 | 为什么怀疑 |
|---|---|---|
| **H1** | **`Literal` 单值这一手，会不会把「以后合法的新豁免种类」也一并锁死？** | 今天只有一种独立可证的豁免。若明天出现第二种**同样独立可证**的，加值是不是要改类型？⭐ 这不一定是缺陷（收紧本来就是目的），但**请说清代价**，别让它变成下一轮的隐性阻塞 |
| **H2** | **那条「红能指名来源」的锁，是不是真的【不钉住缺陷存在】？** | 施工方称它遍历 ledger、无写死 id ⇒ F-153 形态 B 修好后自动不再红。⭐ **请实测**：伪造一个"ledger 已空"的状态，那条锁必须**变绿**；⛔ 只读代码不算 |
| **H3** | **fail-loud 之后，那 11 条撤证锁的夹具被重写了 —— 保护的规则活下来了吗？** | 派工单授权重写夹具，⛔ 但**授权重写不等于允许变弱**。⭐ 请核每条锁**现在还能不能红**（[[neuter-proves-wiring-not-discriminating-power]]）|

## 三、⚠️ 真实 sm25 上它是**红的**，⛔ 这是预期，请照此判

施工方报（我未复跑，请你独立复现）：`passed=False`，**4 条 red / 29-29 zone 全 accounted**：

| 码 | 归谁 |
|---|---|
| `converter_zone_excluded_by_producer_written_ring_loss` ×2（plan-F1 cavity `04e1…`）| **本锁** = **F-153 形态 B**（28.68 m²）⇒ ⭐ **该红，这是正确行为** |
| `facts_projected_ring_unavailable` ×2 | **F-157** 延后项，⛔ **不归本单** |

⭐ **判据是**：本锁负责的红**必须全部有出处**，⛔ 不许有一条无来由的常态红
（常态化的假红会掩护真正的静默）。

## 四、⭐ 一件请求方要交代的事（⛔ 与被审 diff 无关，但你该知道）

**上一轮那次停报是【请求方的题错 #71】**，不是施工方的：我把路写死成
「逐条独立证明做不到 ⇒ 就该 fail-loud」这个二选一，而正解是**先问那条 loss 合不合法**
—— 一问就发现它是 F-153 形态 B。⭐ **而那个二选一是我从【你上一轮的裁决】照搬的**。
⇒ 说明这一点不是为了追责，是为了让你知道：**你给的返工边界里那句 either/or，本身也值得你重新看一眼。**

⭐ 施工方**按我的要求独立复核了那张三路对账并确认**（我明说过「别因为是我说的就信」），
记了一处 B 层措辞差异（ledger 字面 `endcap_const_not_a_measured_parallel_face`
vs 单里 `nearest_same_axis_wall_face`，同一件事）。

## 五、常规项

1. 派工单 §五 的**六条验收**逐条**独立复跑**，⛔ 别采信执行档读数。
2. ⭐ 指南 §五#2：**再找一种能骗过新判据的真实错误形态**（施工方自己造的那种挑不出它自己的盲区）。
3. ⭐ **环境**：本 worktree 无 `.env`。跑全量前同一 shell 先执行
   `set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a`，
   否则 `tests/test_zone_agent.py` 必红一条（F-158，与被审 diff 无关）。
   环境自证与 pytest 同一条命令：
   `python -c "import src.agent.judge.answer_compiler as m; print(m.__file__)" && python -m pytest ...`
4. 跑测 **`-n 6`**。
5. 裁决 → `AI_agent/logs/reviews/verdict/2026-09-02g_f156r6_o21d_crossreview_gpt.md`，
   给 APPROVE / APPROVE-WITH-FINDINGS / REWORK + 阻断数 / 不阻断数。
