# 请求书 · 第二轮跨家族复审 — BLOCKER-1 修法 + 摊 B/C/D + 上轮 7 条未裁定

- **日期**：2026-08-12（当日第二次送审）· **席位**：sol（GPT-5.6），effort = `max`
- **上一轮你的裁决**：[verdict/2026-08-12_f22_f9s0s1_rework_rereview_sol.md](../verdict/2026-08-12_f22_f9s0s1_rework_rereview_sol.md)
  —— **CHANGES REQUIRED**，BLOCKER-1 未关闭，你按停止纪律把其余 **7 条标为「未裁定」**。
- **⚠️ 本轮工作树尚未提交** ⇒ **审 `git diff` + 未跟踪文件**，不是审某个 commit。

---

## 0. 本轮送审的四件事

| # | 内容 | 作者 | 位置 |
|---|---|---|---|
| **1** | **BLOCKER-1 修法**：确定性核盖【无条件】印章 + 判卷验印 | Claude 侧 Sonnet（摊 E）| `deterministic.py` · `schema.py` · `judge/correction_score.py` · `tests/test_f22_blocker1_core_stamp.py` |
| **2** | **F-9 路线② S2**：权威 projector + shadow position evidence | Claude 侧 Sonnet（摊 B）| `window_position.py` · `validator/checks/correction.py` · `tests/test_f9_route2_s2_authoritative_projector.py` |
| **3** | **标注法观测量**（纯观测）| Claude 侧 Sonnet（摊 C）| `envelope_transform.py` · `finalize.py` · `tests/test_c2_b2b_envelope_transform.py` |
| **4** | **F-23**：把「测工作目录状态」的断言改成「测这次跑的副作用」| Claude 侧 Sonnet（摊 D）| `tests/test_c2_b4b_phase_d.py` |

**外加：上一轮你标「未裁定」的 7 条（MAJOR-1/2/3 · MINOR-1/2/3 · NIT-1），本轮请一并裁。**
那 7 条对应的代码**自上轮起未再改动**，仍是 `21b4739` 的状态。

---

## 1. ⭐⭐ 本轮最需要你裁的一条（orchestrator 判不了）

**摊 B 自陈：`mutual-nearest` 未实现。** orchestrator 对照设计稿查实如下，**请证伪或确认**：

- 稿 **§5.3 列了「引对了」的六个条件，mutual-nearest 是第 2 条**；
  第 3 条（最优与次优距离之差 > ambiguity epsilon）**依赖它**；
  错误词表里的 **`position_evidence_pair_mismatch` 没有它就结构上不可能触发**。
- 稿 **§10 S2 的内容逐字含「pairing decision」**；
  而 **S3 = 「冻结 citation 规则」+「把 S2 decision 变成 blocking gate」** ⇒ **S3 不负责实现。**

**⇒ orchestrator 的判断**：若 S2 的 decision 只覆盖 6 条里的 3 条，S3 会在不完整判据上承重。

**⭐ 而且这带出一个更普遍的问题（请重点看）**：
shadow 现在会报 `PASS`，但那个 `PASS` **只验了 6 个条件里的 3 个**，
**产物里没有任何东西说明它只验了一部分** ⇒ **一个「通过」看起来比它实际意味着的强。**

**两条出路，请裁**：① 在 S2 补齐条件 2/3/4；
② **显式把「本 decision 覆盖了哪几条」写进产出**（具名的部分实现标记），使 S3 承重前必须先看见缺口。
（orchestrator 倾向 ②：不扩大批次范围，但堵住「不完整的 PASS 长得像完整的 PASS」。）

---

## 2. BLOCKER-1 修法要点（请重点打）

**用户拍板口径** = 让确定性核盖一个**无条件**的「我跑过、版本是 X」印章，判卷改为验印章；
⛔ 不要历史白名单；✅ 接受「现有产物需重跑一次才重新有分数」。

**修法为什么必须无条件**（orchestrator 实测的坑）：`envelope_transform.py` 在无 intent 时**早返回不留记录**
⇒ 图纸本来就按外皮标注时核什么都不用改，**合法产物同样没记录**
⇒ 「没记录」= 「没跑过核」+「跑了但没事干」两件事压成同一个空白。

**请判**：
1. 印章**真的无条件**吗？有没有任何分支能走到 v3 完成却不带印章？
2. **判卷验印是不是 fail closed 到底**？印章缺失 / `None` / 版本不认识 / 结构畸形 / **伪造**五条路径。
   ⚠️ 上一轮你正是用「第五类路径」推翻了 orchestrator 的四分类 —— **请再找第六类。**
3. **拒判会不会长得像全对**？（下游消费者拿到 `boundary=None` 会不会读成零缺陷）
4. 印章进了产物 ⇒ **有没有打坏既有哈希/批准链**？（F-20 前科）

---

## 3. orchestrator 已亲跑的项 —— **请当作待证伪的断言**

| 断言 | 做法 |
|---|---|
| **权威全量 2539 passed / 10 xfailed / 0 failed** | 独立跑、rc=0、`.rc` 新文件名且时间戳晚于日志、汇总行在（今日起点 2470 ⇒ +69 零回归）|
| 印章无条件 | `deterministic.py:1117` 唯一 v3 `return` 前最后一句、无 `if`；能覆盖伪造值 |
| **摊 E 的 §3 防护是真的** | **换方向 neuter**：把坑造回去（印章只在「核真改了东西」时才盖）⇒ `test_zero_displacement_legit_product_is_still_trusted` **转红** |
| 真实产物行为 | `f17`（翻转前、真差 0.12m）⇒ 拒判 · `continuous_e2e`（翻转后、正确）⇒ **也拒判**（既定代价）|
| **摊 B 接线是真的** | **换方向 neuter**（不用施工席的「摘 projector / 换 advisory frame」）：中和共享实现 ⇒ **18 红**，含 `test_real_stepwise_entry_*` / `test_real_integrated_entry_*` / `test_binding_unavailable_is_a_third_state_*` |
| **摊 C 四态真可分** | **第三方向 neuter**：把被推翻的原口径装回去（从过滤后的 intents 推状态）⇒ 「按轴线」「超容差」两格锁**转红** |
| 摊 D 替换正确 | 文件系统指纹（对 git 状态盲）+ 两种旧失效模式各有 `/tmp` 隔离 repo 的自证锁 |
| 归属 | 28/28 改动文件逐个认领，零无主；两摊互相覆盖的风险**未发生** |

**⭐ orchestrator 自己答不了的**：
1. **mutual-nearest 那条（见 §1）** —— 设计范围的裁定。
2. **印章方案本身的工程正确性** —— 我参与了岔口分析，判不了。
3. **fail closed 的第六类路径** —— 我只能想到我想到的那五类。
4. 摊 D 把「一次性纪律检查被烤成永久测试」的定性 —— 它给的证据链我复核过，但**它是唯一信源**。

---

## 4. ⛔ 两条新登记债（本轮发现，未修，供你判要不要升级）

- **F-24**：判卷侧车 **cache key 不含印章状态**（摊 E 自报、超其所有权未修）。
  orchestrator 核实其「当前零影响」依据成立（盘上 `scorer_schema` 分布 9×20/8×4/7×4/6×1，**无一到 "10"**），
  **但结构性缺口是真的** —— 一旦出现 "10" 的侧车，印章变化不会让它失效 ⇒ **fail-open 入口**。
- **F-25**：**`SCORER_SCHEMA` 同名两处、值不同** —— `run_stage.py:94="10"` vs `judge/score_schema.py:40="8"`
  （**orchestrator 撞到，席位未提**）。轴 B 族。需先判是不是同一事实。

---

## 5. ⛔ 硬纪律

1. **⛔ 不要任何 git 写操作**（`checkout`/`stash`/`clean`/`commit`/`reset`）——
   **本轮工作树有大量未提交改动，一次误操作会全丢。** 只读命令随意。
2. **判「是否已接线／已关闭」只能用行为验证**，⛔ 不能用 grep / 精确 AST 语法。
3. 验锁 neuter **只在 `/tmp` 做**（推荐 pytest 插件式 runtime monkeypatch，零源码改动），做完还原。
4. **⛔ 派工方错误率 14/14** —— 本书里凡描述**岔口 / 分类 / 数量 / 位置**的句子都可能是错的前提。
   **发现前提错请停下上报**（上一轮你正是这么抓到 BLOCKER 的）。
5. 跑测用**独立新文件名**落日志与退出码，判跑完**看汇总行**。**当前基线 = 2539 / 10 xfail / 0 红。**

## 6. 输出

裁决书落 `AI_agent/logs/reviews/verdict/2026-08-12_round2_blocker1_and_bcd_crossreview_sol.md`：
总判定 · BLOCKER-1 是否**真关闭** · §1 那条裁定 · 上轮 7 条逐条关闭/未关闭 ·
摊 B/C/D 各自 finding · 新发现 · **你未验证的项（如实列出）**。
