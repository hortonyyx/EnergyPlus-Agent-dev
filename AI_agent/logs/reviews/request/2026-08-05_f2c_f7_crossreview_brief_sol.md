# 对抗审请求书（sol / GPT 侧，最高档 effort）· F-2c 收口 + F-7 接口修法

- **日期**：2026-08-05
- **委托方**：orchestrator（Opus 5）
- **状态**：**骨架，待两批施工落库后填入 diff 指向**（下方 `⟨待填⟩` 处）
- **谁写谁不批**：F-2c 由 **GLM-5.2** 施工、F-7 由 **Claude 侧 Sonnet** 施工 ⇒ 交 **GPT 侧 sol** 对抗审（跨家族）。

---

## 0. 你要审的是什么

两个修法，**同属一族缺陷**，请当成一件事审：

> **「消费侧要求的字段形态，生产侧既不被告知、也物理上产不出；而测试夹具自己造出了合规形态 ⇒ 测试永远绿、真链路必崩。」**

本轮此前已经撞出这一族的两个实例：
- **F-5**：四个测试文件的夹具**集体照抄了实现的错拼写**（契约 `x_range_m`，实现读 `x_range`）⇒ B5 窗源这条路**从来没在一份合规的真实识图产物上跑通过**。
- **F-7**：消费侧要 64 位 locator（拿识图产物字节算的哈希），模型**物理上算不出**，prompt 从没提过；B5 夹具**手搓真 locator** 才过。

**⇒ 本次审的核心问题不是「代码写得对不对」，而是「这次的修法会不会长出同一族的第三个实例」。**

---

## 1. 背景（最小必要）

- 管线：`0_reading`（识图）→ `1_correction`（校正，LLM）→ 几何内核（代码）→ `4_mep`（LLM）→ `5_intakeoutput`（装配）。
- 本轮主线 = **端到端工程缺陷批**：拿 07-07 那份已知满分的 sm21 识图产物做下游机械烟测，把识图变量摘掉，只问「除识图外这条链今天还通不通」。**通不了**，已逐条撞出 F-1…F-7。
- 全部前序结论见 `AI_agent/plan.md` 顶部 2026-08-05 条。

### 1.1 F-2c（GLM 施工）

把识图产物的**形状探测器** `identify_reading_contract` 从 `src/agent/judge/` 搬到 `src/agent/reading/contract.py`，
让校正段可以合法使用它 —— 因为 B5 A6 有一条硬边界：**`src/agent/correction/` 不得出现 `src.agent.judge`**
（judge-blind，防判卷代码漏进生产）。
- 派工单：`2026-08-05_f2c_closeout_dispatch_glm.md`
- 前序裁定：`2026-08-05_f2c_boundary_ruling.md`（**orchestrator 认错**：原派工单让施工席直接引用 judge 包，必然撞墙）

### 1.2 F-7（Sonnet 施工）

`source_ids` 的语义从「locator」改为「模型看得见的观测引用」（`1f_view/S11`），**由代码翻译成 locator**；
合法引用清单从建 locator 的**同一个出口机械导出**后注入 prompt。
外加：源绑定失败**分两类**（模型抽签写错 ⇒ 归档重抽；识图产物本身对不上 ⇒ 硬崩）。
- 派工单：`2026-08-05_f7_source_ids_dispatch_sonnet.md`
- 前序调查：`../execution/2026-08-05_f7_claim_links_interface_gap_glm.md`

---

## 2. 请重点打的地方（按怀疑度排序）

1. **⭐⭐ 机械导出是真的机械吗？**
   F-7 要求「注入 prompt 的合法引用清单」与「`_catalog` 建 locator 的出口」是**同一个来源**。
   请核：是不是真的一个出口，还是**又长出了第二份词表 / 第二个遍历**（哪怕逻辑一样）。
   本项目已在这上面栽过多次（判卷双尺 / 词表双份 / 夹具手抄）。
2. **⭐⭐ 判据有没有分辨力（不是「有没有被调用」）。**
   本项目 08-04 最贵的教训：**neuter 变红只证明实现被调用了**。
   请对新加的每条锁问：**把实现改成恒真 / 恒假，这条锁会不会仍然绿？** 载荷是不是真实量级和真实形状，还是退化 fixture。
   （实犯过两次：2×2 px 退化 fixture 假绿 / 两堵墙探针假红。）
3. **⭐⭐ 失败分类会不会退化成「没分类」。**
   请核：分类是落在**错误类型/抛出点**上，还是靠匹配错误消息文字；有没有「默认归到某一类」的兜底（= 等于没分类）；
   「归档重抽」那条路会不会**静默吞掉**失败（attempt 是否真的落盘、计数是否真的涨）。
4. **⭐ 有没有留静默回退分支。**
   `_build_correction_messages` 改了签名。请核有没有留旧签名/旧行为的静默分支 ——
   静默回退 = **修法在真实路径上不生效**，正是本项目反复栽的形状。
5. **⭐ 严格校验有没有被偷偷放宽。**
   派工单明写 `_claim_links` 的校验**一个字不放宽**、B5 A6 两条守卫**一个字不许改**。请核是否被动过。
6. **搬家有没有留下第二个探测器 / 新的循环依赖。**
   F-2c 应当只剩**一处** `def identify_reading_contract`，judge 侧是 re-export、调用点语义零变化。
7. **真实产物跑通那一步的证据成色。**
   F-7 的核心验收 = 在 07-07 真实 sm21 产物上跑到 1_correction 出 accepted attempt。
   请核那次跑是不是走的标准 `flow` SOP、是不是真调了 LLM、有没有被降级成 mock 或手搓。

---

## 3. 判据与纪律

- **放水比冤枉危险**（本项目定论）。不确定就标 PLAUSIBLE 并说清怎么验证，别为了给结论而给结论。
- 结论用 **BLOCKER / MAJOR / MINOR / NIT** 四档 + **APPROVE / APPROVE-WITH-CHANGES / REWORK** 总判。
- 每条 finding 请给：**具体文件:行** + **一句「什么输入会让它错」的失败场景**。抽象的「建议改进」不计入。
- **⛔ 不要碰 `case_tests/test_baseline/gt/`**（gt 铁律：只有 gate② judge 和人可读）。
- 你**只审、不改**（谁写谁不批的另一半：审阅方也不动手）。

---

## 4. 具体指向

| 项 | 内容 |
|---|---|
| F-2c 提交 | **`a8c367a`**（GLM）· orchestrator 轻门 **PASS** → [`../verdict/2026-08-05_f2c_closeout_orchestrator_lightgate.md`](../verdict/2026-08-05_f2c_closeout_orchestrator_lightgate.md) |
| F-7 提交 | **`a174fe8`**（Sonnet，分支 `f7-source-ids-sonnet`）→ 合并 **`86ab24b`** · 轻门 **PASS** → [`../verdict/2026-08-05_f7_source_ids_orchestrator_lightgate.md`](../verdict/2026-08-05_f7_source_ids_orchestrator_lightgate.md) |
| 建议 diff 范围 | `git diff 3310ed3..86ab24b`（含两批全部改动）|
| 全仓（orchestrator 独立跑，零过滤）| **2212 绿 / 10 xfail / 0 红**（基线 `9fd8a9a` = 2193 ⇒ F-2c +4、F-7 +15，零回归）|
| 两席位执行日志 | [`../execution/2026-08-05_f2c_closeout_glm.md`](../execution/2026-08-05_f2c_closeout_glm.md) · [`../execution/2026-08-05_f7_source_ids_sonnet.md`](../execution/2026-08-05_f7_source_ids_sonnet.md) |
| 真实产物跑通的 run 目录 | `case_tests/e2e_tests/sm21_anchor/run_2026-08-05_f7_verify_sonnet/`（**未提交**，跑测产物）|

## 5. ⭐ orchestrator 已自查过的点（省你时间，但**欢迎推翻**）

以下我已独立实测，**如果你能证伪任何一条，那比新增 finding 更有价值**：

1. **合并正确性**：F-2c 与 F-7 改过同一函数，git 自动合并成功。我按括号配平扫描了
   `window_sources.py` 全部 `raise WindowResolverInputError(...)` ⇒ **0 处漏填 `category`**
   （漏填即运行时 `TypeError`，自动合并不会察觉）。`finalize.py`/`parse.py` 的 4 处亦已核。
2. **分类判据双向分辨力**：一律判 `model_draw_error` ⇒ 只红「输入坏必须硬崩」那条；
   一律判 `input_integrity_error` ⇒ 只红「模型错必须归档重抽」那条。**互不误伤。**
3. **翻译层**：禁用翻译 ⇒ 恰好 8 条相关锁红、其余 7 条绿。
4. **单一探测器**（F-2c）：两个方向各自绑住（遮蔽 re-export ⇒ 红在 `is`；换模块加第二个 def ⇒ 红在源码扫描）。

## 6. ⭐⭐ 我最想让你打的一条（我自己不确定）

`build_observation_reference_catalog_from_run` 在 view manifest 或任一识图产物**不在盘上时返回 `None`**
（清单不注入 prompt）。其 docstring 自陈：*「advisory prompt content only；执法侧独立重算，
缺清单只削弱引导、不削弱契约」*。

**这个辩解在「正确性」上我认为成立，但在「可用性」上我存疑**：
清单缺失 ⇒ 模型无引导 ⇒ 必然填错 ⇒ 归档重抽 ⇒ **可能空转烧完整个重抽预算，且报错看不出真因**。
本项目刚在 F-3/F-4 上栽过同型（「静默降级 → 两段之后炸 → 报一句看不懂的话」）。

**请判**：v3 目标下是否该把「清单可导出」升为**前置条件**（缺则明确失败）而非静默降级？
若该升，最小改法是什么？

**交回落**：`../verdict/2026-08-05_f2c_f7_crossreview_sol.md`
