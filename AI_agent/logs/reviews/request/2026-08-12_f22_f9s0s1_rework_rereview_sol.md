# 请求书 · F-22 + F-9 S0/S1 **返工复审（第二轮）** — GPT 侧 sol

- **日期**：2026-08-12
- **席位**：sol（GPT-5.6），effort = `max`
- **类型**：跨家族**复审**（verification review：finding 清单已给定，判每条修法是否真绑目标）
- **⛔ 为什么必须换人**：本批返工**由提出修法的作者自己完成**（F-22 / F-9 两摊各自返工），
  已落库 `21b4739`。按项目铁律「谁写谁不批」，**机械测量作者可做、判断类必须换人**。
  orchestrator 已独立复现若干机械项（下附），**但这不能替代跨家族复审**。

---

## 0. 你要审的东西

| 项 | 位置 |
|---|---|
| **你自己上一轮的裁决书**（8 条 finding 原文） | `AI_agent/logs/reviews/verdict/2026-08-11_f22_f9s0s1_crossreview_sol.md` |
| **返工 diff（唯一权威）** | `git show 21b4739` |
| 两摊原始派工单 | `logs/reviews/request/2026-08-11_f22_judge_output_convention_dispatch_claude.md`<br>`logs/reviews/request/2026-08-11_f9_route2_s0_s1_construction_dispatch_claude.md` |
| F-9 设计稿（S0/S1 验收口径在 §10） | `AI_agent/proposals/f9_route2_evidence_citation_design.md` |

**⛔ 复核简报纪律**：只看**原始需求 + diff + 测试输出**。
**不要**采信任何执行者的长篇自述，也不要采信本请求书里 orchestrator 的结论——
下面 §2 列的每一条都请当作**待证伪的断言**。

---

## 1. 逐条要判的（你上一轮的 8 条）

**BLOCKER-1｜声明 runtime inert + 对 legacy 产物无条件删换算是错误修复**

用户拍板的修法口径 = **「明确拒判，不猜」**：
声明文本缩到 v3 / orthogonal_polygon / post-transform 范围 · 判卷**运行时验证该身份** ·
非该口径或身份不明 ⇒ **显式 fail closed** · ⛔ 不许静默套用外皮口径 · ⛔ 不许加第二套换算分支 ·
假定口径 + provenance 写进侧车并纳入 cache 身份。

请判：
1. 那个常量**现在真的被消费了吗**？（自测判据 = 改成 `bogus`，判卷行为必须变）
2. **fail closed 是真 closed 还是 fail-open 的变形**？特别是：身份缺失 / 字段为 `None` /
   解析异常 / 未知 `schema_version` 四种路径，**有没有哪一条悄悄退回「按 v3 处理」**。
   （参考 F-20 的教训：最易被实现成 `except: 当作无账本`。）
3. 拒判之后**下游拿到的是什么**？`boundary=None` + 空 wall segments 会不会被下游读成
   「零缺陷 ⇒ 满分」？**「拒判」不能长得跟「全对」一样。**
4. provenance 进 cache 身份这件事：**同一份产物换个 profile 会不会命中旧 cache**。

**MAJOR-1 / MAJOR-2｜`WindowPositionDecisionV1` preimage 与 `accepted` 语义过弱**
（可跨 raw/resolver 重放、错误的 raw/context 组合能合法自哈希）
⇒ 按稿 §8.1 补齐 preimage 与 `canonical_window_key`。
请判：**外层自哈希有没有被当成内层身份绑定的替代品**（你上一轮的原话）。
建议判据：构造「raw 换了但 context hash 没换」「context 换了但 raw 没换」两种错配，
看它们**能不能各自合法自哈希通过**。

**MAJOR-3｜`derive_facade_frame` 未接线（两次条件取反等价实现 XOR，形状匹配抓不到）**
⇒ 返工声称已接线，且把 AST 锁**从黑名单改成白名单**。
请判：
1. **用行为验证，⛔ 不要用 grep / 精确 AST 语法**。判据 = 中和 `facade_convention.resolve_sign`，
   看**每一个**声称已接线的调用点是否跟着变。commit 说明称有 **6 个真实调用点**——
   **这个数字请独立核实，不要采信**（上一轮就是「4 处副本」这个数字把 orchestrator 带沟里的）。
2. 白名单式 AST 锁**自身**有没有分辨力：它是不是只在断言「文件里出现了某个名字」？
   建议 neuter = 把某个调用点改成「import 了共享函数但实际不调用」，看锁红不红。

**MINOR-1｜三档实现是先 `round(2)` 再比 0.05 ⇒ 实际绿色阈值不是字面 0.05**
⇒ 返工称改用原始差值。请判阈值**两侧各一格**是否真被钉住（不只是「改了写法」）。

**MINOR-2 / MINOR-3 / NIT-1**：测试标题强于判别力 · 两套 mirror coercion 并存 · 旧文案。
（你上一轮认可「保留 legacy 宽松版」这个决定；请确认返工没有顺手把它收紧。）

---

## 2. orchestrator 已亲跑的机械项 —— **请当作待证伪的断言，不是既定事实**

| 断言 | orchestrator 的做法 |
|---|---|
| 全仓 **2470 passed / 10 xfailed / 0 failed** | 独立全量、退出码 0、日志有汇总行、`.rc` 用**新文件名**（上一次复用文件名差点把陈旧的 `0` 当结果）|
| 声明改 `bogus` ⇒ 判卷**拒判** | 返工前一字不变，返工后行为真的变 |
| legacy 产物 `boundary=None` 拒判 · C2 产物正常 4/4 | 真实产物 |
| `derive_facade_frame` 中和共享函数后 `-1→1` **跟着变** | 返工前纹丝不动 |
| 宽松 mirror 归一保持 | `unknown`/空串/`None`/`yes`/`1` 全部静默 False、零抛异常 |
| 阈值改用原始差值 | `0.054` 由绿转橙 |
| 真实入口 neuter | 外包 8 条边 `delta=0.0/status=complete`、内墙 `extent_drift` 9 → 0 |

**⭐ orchestrator 自己答不了的问题**（正是需要你的地方）：

1. **「明确拒判」这个口径本身，对 legacy 产物是不是正确的工程选择**——
   它让一批历史 probe run 从「有分数」变成「无分数」。orchestrator 是这个修法的共同作者，判不了。
2. **fail closed 的覆盖面够不够**：我测的是我能想到的四条路径，**想不到的那条正是风险所在**。
3. **S0 的身份绑定是否真的堵死了重放**：我验的是「按稿子写的那几种错配」，
   **稿子没想到的错配组合我同样想不到**。
4. **AST 锁白名单化之后，有没有引入新的过度约束**（把合法的实现变体也判红）。

---

## 3. ⛔ 硬纪律

1. **⛔ 不要执行任何 git 写操作**：`checkout` / `stash` / `clean` / `commit` / `reset` 一律禁止。
   （上一轮并行席位执行过一次 `git stash`，短暂波及另一席位的未提交改动。）
   只读命令（`git show` / `git log` / `git diff HEAD`）随意。
2. **判「是否已接线／已合并」只能用行为验证**（中和共享实现看谁跟着变），
   **⛔ 不能用形状匹配**（grep / 精确 AST 语法）——上一轮正是你用这条推翻了 orchestrator。
3. **验锁的 neuter 只在 `/tmp` 做**，做完还原；⛔ 不要留改动在工作树。
4. 跑测请用**独立文件名**落日志与退出码，判「跑完没有」**看汇总行**，不看 `.rc` 存不存在。
5. **⛔ 派工方错误率 13/13**：本请求书里凡是描述**岔口 / 分类 / 数量**的句子
   （「6 个调用点」「四种路径」「8 条 finding」），**都可能是错的前提**。
   发现前提错**请停下上报**，不要照题作答——过去 13 次「停下上报」**全部**是派工方的题错了。

---

## 4. 输出

裁决书落 `AI_agent/logs/reviews/verdict/2026-08-12_f22_f9s0s1_rework_rereview_sol.md`，含：
- **总判定**（APPROVE / APPROVE-WITH-CHANGES / CHANGES REQUIRED）
- 逐条 finding 的**关闭 / 未关闭**判定 + 判据（**实测优先于阅读**）
- 新发现的 finding（按 BLOCKER / MAJOR / MINOR / NIT 分级）
- **你未验证的项，请如实列出**（这一条比多报几个 finding 更有价值）
