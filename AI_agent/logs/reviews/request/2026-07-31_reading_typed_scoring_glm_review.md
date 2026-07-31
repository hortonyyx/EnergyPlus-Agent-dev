# 审阅单 · 识图类型化判卷批（GLM-5.2 验证性对抗审）

> 主控 Opus 5 · 2026-07-31 · 收件人 = GLM-5.2
> 被审对象 = sol 的施工（`f98d248..HEAD` 中所有 `7.31_ReadingTypedScoring*` 提交）
> **谁写谁不批**：sol 施工（GPT 侧），你审（GLM 侧），跨家族。

---

## 0. 你的任务形态

**这是验证性审阅，不是探索性审阅。** 下面每条命题都写死了「验什么 / 什么算不成立」。
你的强项正是这个（回溯测实证达最高档水平），照单逐条验即可，不需要去无线索处找未知缺陷。

**硬纪律（本项目栽过的地方）**：

1. **只审不修。** 发现问题写进裁决书，**不要动生产码**。改了就失去独立性。
2. **neuter 必须真跑。** 在 `/tmp` 克隆里做定点破坏、真跑测试、报告实际变红的测试名。
   2026-07-27 那轮审阅方只出静态审、neuter 无人独立验，结果放过了三处 false-lock。
   2026-07-28 那轮你重跑了 14 个指定 neuter 且与执行日志逐条吻合 —— 那是本项目的正面样板，照那个做。
3. **「全仓绿」不等于「锁是真的」。** 施工方声称的每把锁，都要问「摘掉它守的那道门，它红不红」。
4. **不采信自述。** 施工方执行日志里的每个数字都要你自己复算一遍。

工作区：`/tmp` 下自己克隆，**不要在主工作树里做破坏**。
裁决书落 `AI_agent/logs/reviews/verdict/2026-07-31_reading_typed_scoring_glm.md`。

---

## 1. 背景（只给你判断所需的最小上下文）

2026-07-30 sm24 端到端跑测卡死：v3 判卷层对**识图阶段**既无生产投影也无能力守卫，
一进 J0 即 `ScoreContractError` 未捕获、整条 flow 崩。本批就是修它。

设计基线 = [`AI_agent/proposals/reading_typed_scoring_plan_sol.md`](../../../proposals/reading_typed_scoring_plan_sol.md)
主控裁定 = [`../verdict/2026-07-31_reading_typed_scoring_design_controller_rulings.md`](../verdict/2026-07-31_reading_typed_scoring_design_controller_rulings.md)（U-01–U-15 + D-1/D-2 + **U-13 更正**）
施工日志 = [`../execution/2026-07-31_reading_typed_scoring_sol.md`](../execution/2026-07-31_reading_typed_scoring_sol.md)

**改造前基线**：`f98d248`，全仓 **1786 passed / 10 xfailed / 0 failed**。

---

## 2. 命题清单

### 承重命题（P1–P4 = 验收命脉，任一不成立即 REWORK）

#### P1 · U-13 的「分母是受信输入的纯函数」锁是真锁

**背景**：产品若能把自己的某个 source 变成 unsupported，就能缩掉自己的分母 = 假绿杠杆。
裁定按成因二分：受信输入侧的原因**可以**过滤分母；**产品侧的原因绝不可以**。

**验什么**：
1. 找到那把锁（施工方称 `test_product_geometry_bytes_cannot_change_denominator` 一族）。
   确认它喂的两份产品字节流**除几何畸形外，还在 `facade.local_x_positive` / `facade.mirrored` 上取了反**
   （这是主控 U-13 更正明确要求的；原稿把这两个字段固定住，恰好把杠杆排除在锁的覆盖面外）。
2. **neuter**：把成因二分改成「产品侧原因也过滤分母」（即恢复施工方最初的 `trusted_frame` 过滤权）。
3. 跑测，记录变红的测试名。

**什么算不成立**：neuter 之后该锁**仍然绿** ⇒ 假锁 ⇒ **BLOCKER**。
或者：锁只比较几何畸形、没比较那两个 facade 字段 ⇒ 覆盖面不足 ⇒ **MAJOR**。

#### P2 · U-10 的帧冲突 = NA + 证人 + **分母保留**

**背景**：sm24 现场，产品在 binding `sign=-1` 的两个立面（North / West）声明了反向 `local_x_positive`，
相关性 4/4。裁定：坐标权威仍在 binding；但该 input 的立面 component 判 NA 并附证人；
**该 input 的答案侧立面目标必须留在分母里、照常算 miss**（不许摘）。

**验什么**（用真实产物，不要手搓）：
- 产物：`case_tests/e2e_tests/sm24_anchor/run_2026-07-27_haiku_e2e/0_reading/attempts/003/output.json`
- 答案：`case_tests/test_baseline/gt/sm24_anchor/gt.json`（**只读，禁写**）
1. 真跑判卷，确认 North / West 出 `elevation_local_x_sense_disagreement` 且**证人含两边的原始声明值**。
2. **决定性探针**：把该产物拷到 `/tmp`，将 North / West 的 `facade.local_x_positive` 改成与 binding 一致
   （`image_left_to_right`），重跑判卷。
   **`window_elevation_geometry` 的 `denominator_units` 必须与改之前逐字相同。**
3. 确认 East / South 没有携带该 reason。

**什么算不成立**：分母在两次之间变了 ⇒ 杠杆仍在 ⇒ **BLOCKER**。
证人缺失或只存了结论没存两边原值 ⇒ **MAJOR**。

#### P3 · U-05 的 rect 墙 = 逐笔画剔除 + 计数，**不是整通道 NA**

**验什么**：
1. 取真实平面视图，注入一条 `pen="wall"` 且 `geometry.kind="rect"` 的笔画。
2. 断言四件事同时成立：
   ① 该视图的 plan-segment component **仍是 applicable**（不是整个 NA）；
   ② 其余笔画照常计分（分数不为全 NA）；
   ③ `unmeasurable_observations` **加 1**；
   ④ 该 rect **既不出现在覆盖侧、也不出现在 extras 侧**。
3. **neuter**：把逐笔画剔除改回「整 component NA」，确认对应锁变红。

**什么算不成立**：④ 里 rect 混进了 extras（那会把不可测当多画计费）⇒ **MAJOR**；
① 退回整通道 NA ⇒ 与裁定不符 ⇒ **MAJOR**。

#### P4 · U-03 的 D-1：correction 对外可见判分**逐字节未变**

**背景**：本批新建 sidecar v9。v9 对 correction 通道必须是纯附加，公开判分一位都不能变。

**验什么**：**不要采信施工方打印的 SHA**。你自己做：
1. `/tmp` 里克隆两份，一份 checkout `f98d248`（改造前），一份 HEAD。
2. 用同一组 correction v3 夹具在两边各跑一次，自己算 `public_rows` / `wall_criteria` 的 SHA-256。
3. 逐条比对。

**什么算不成立**：任何一位不同 ⇒ **BLOCKER**（判分被静默改动）。
或：`f98d248` 侧根本跑不起来（对照不成立）⇒ 如实报告为「无法判定」，不要凑。

---

### 结构命题（P5–P9）

#### P5 · 判卷器对识图**永不抛异常**（C1 / R-4）
喂若干畸形识图 payload（`views` 缺失 / 非对象 / 视图内容乱码 / 空 dict），
断言得到的是**顶层 NA 带 reason**，不是异常冒泡。
特别验：`scorer_internal_failure` 这条通道存在且**计数可见**，且在
`run_profile ∈ {golden, regression}` 下 **fail-closed（raise）**、`exploratory` 下 warn 续行。
**不成立**：任一畸形输入让 `_grade_typed_attempt_artifacts` 抛出 ⇒ **BLOCKER**（这就是原病复发）。

#### P6 · F8 的恒真陷阱已避开
原缺陷：识图 `output.json` 没有 `schema_version` 键，`output.get("schema_version","3")` 静默默认 `"3"`
⇒ 任何对识图查 `product_schema` 的守卫都是**永真断言**。
**验**：确认识图契约识别是**结构性的**（认 `views` 形状），不是靠那个默认值。
**neuter**：让契约检测器恒真返回「是识图契约」，确认有锁变红。
**不成立**：neuter 后全绿 ⇒ 守卫无锁 ⇒ **MAJOR**。

#### P7 · 零观测 ≠ 不适用（C2）
**验**：一个 applicable 且零观测的 component ⇒ 答案目标算**真 miss**；
一个 inapplicable 的 component ⇒ 从分母移除**并带 reason**。两者行为必须可区分。
**不成立**：零观测被当成 NA 静默吞掉 ⇒ 假红/假绿混淆 ⇒ **MAJOR**。

#### P8 · gt 铁律未破（不变量 #4）
**验**：新增模块只在 `src/agent/judge/` 下；gate①、执行器、reading 生产路径**零 GT import**。
用 AST 或 grep 全仓扫一遍 import 边。
**不成立**：任何非 judge 模块 import 了 gt ⇒ **BLOCKER**。

#### P9 · 既有行为未被破坏
**验**：① v2 GT 仍走 legacy 路线；② correction v3 仍要求 accepted B5 六件套 + verified proof；
③ 识图 attempt（accepted 与否）都继续进判卷（`run_stage.py` 原注释 F7 的语义）；
④ 没有引入自动 `StageVerdict`。
**不成立**：任一条被改 ⇒ **MAJOR**（越界）。

---

### 卫生命题（P10–P12）

#### P10 · 新的识图 E2E 没有拿答案当被测物
主控发现：原 `tests/test_c2_b4b_phase_d.py::_typed_attempt_payload` 的产品 payload
**整个是从 GT 抄的**（segments 抄 `gt.floors[].boundary_segments`，立面 local_x 是拿 GT 反解绑定算的）
⇒ 计分逻辑上不可能红。裁定：保留其 parity 断言 + 加注释 + 改名 + **另加真 E2E**。
**验**：① 那个 parity 测试的断言体**未被削弱**（只改了名字/注释）；
② 新增的识图 E2E **不从 GT 反解任何产品坐标**（逐行看它的夹具来源）。
**不成立**：新 E2E 里出现任何 `gt.` 派生的产品坐标 ⇒ **MAJOR**（同型复发）。

#### P11 · 全仓数字与基线的差额逐条可解释
基线 `f98d248` = **1786 passed / 10 xfailed / 0 failed**。
**验**：你自己独立跑一次全仓，报告数字；与施工方声称的对账；
新增测试数与 Slice 清单对得上；**xfailed 必须仍是 10**（不许偷偷加 xfail 掩盖失败）。
**不成立**：xfail 变多、或有无法解释的差额 ⇒ **MAJOR**。

#### P12 · 跨批次零碰撞
本轮另一席位（GLM 自己）在改
`src/agent/execution/isolation.py` / `isolation_templates/guard.py` / `scripts/tool_scripts/cv_probe.py` 及其测试。
**验**：sol 的提交**完全没碰**这四处。
**不成立**：碰了 ⇒ 报告为越界（**MINOR** 或 **MAJOR**，视是否改变行为）。

---

## 3. 裁决书要求

1. 每条命题给 **成立 / 不成立 / 无法判定** 三选一，附**你自己跑出来的证据**（命令 + 输出），
   不要引用施工方日志当证据。
2. neuter 表：命题号 / 破坏点 / 实际变红的测试名 / 是否符合预期。
3. 结论用 **APPROVE / APPROVE-WITH-CHANGES / REWORK** 之一，
   并按 BLOCKER / MAJOR / MINOR / NIT 分级列出 finding。
4. **无法判定就写无法判定**，不要凑一个结论 —— 2026-07-22 那轮「无法判定」的诚实标注是被记为正面的。
5. 只审不修。
