# R1 批 B · r1 交叉对抗审（路 2／共 2）· 被审 = R1-1…R1-4 / R1-6 / R1-7（GLM 产出）+ 补完 P-3…P-9 · 审 = Claude 侧子代理

- **日期**：2026-08-03
- **派工方**：orchestrator（端到端主控）
- **审阅席**：**Claude 侧子代理（Opus 档）**。⚠️ 原计划派 sol 重审，**用户 08-03 拍板改走 Claude 侧**（本单据此改派）。
  施工方 = GLM-5.2，审方 = Claude 侧 ⇒ **「谁写谁不批」满足，跨家族**。
- **性质**：**对抗审**。你的任务不是确认它做了，而是**尽力证伪它真的做到了**。
- **另一路并行**：R1-5（terra 产出）由另一个 Claude 子代理审
  （[路 1 审阅单](2026-08-03_reading_ruler_r1_crossreview_claude_r15.md)）。**两路互不通气，不要去审对方的范围。**

---

## 0. 一句话背景（不含答案，只给事实）

reading（识图）环节最近所有分数都不可信。已查明**不是模型退化，是判卷这把尺子和运行政策本身坏了**：
`run_config.yaml` 声明 `regression`(fail-closed) + `orthogonal_polygon`，实际落盘的 `checks.json` 头部却是
`exploratory` + `rectangular`；那一轮 gate① 本来抓到 5 条 fail，按 exploratory 算 = 0 阻断、按 regression 算 = 4 条 blocker
⇒ **严格档若真生效，那份产物会被当场拒收**。

批 B 修的就是这条。**r0 落库后两轮审（orchestrator 轻门 + sol 交叉审）独立收敛到同一句话**：

> **修好的是「机制存在」，没修好的是「机制在所有真实路径上都生效」。**

⇒ REWORK（6 MAJOR + 1 MINOR）⇒ **r1 七条全部返工完成，你审其中六条。**

**⛔ 硬约束：批 A/B/C 三批全绿之前，本项目不得发布任何新的识图分数或「识图变好/变坏」的结论。**
这次审阅是那条约束的解除条件之一 —— **放水的代价是后面一整批实验白跑。**

---

## 1. 被审对象（六条 + 一条 context 接线）

| commit | 条目 | 修的是 |
|---|---|---|
| `63a41b9` | **R1-1** | `flow` / `run` 标准入口：声明严格档、实际跑宽松档（`run_stage.py` + `test_run_stage_flow.py`）|
| `2daf846` | **R1-1 续** | J-1 的 `context` 接线（`run_stage.py` + `test_run_stage_flow.py`）|
| `3e3ac1e` | **R1-2 + J-2** | 档位**拼错一个字母** ⇒ 静默降档；混合列表 raise（`run_config.py` / `view_manifest.py` + 两个测试文件）|
| `6d38f0c` | **R1-3** | 离线审计面把四态折回 bool、丢结构化声明（`case_metadata.py` / `evidence_preflight.py` / `validation_run.py` / `pipeline.py`）|
| `c9b1aae` | **R1-4** | fail-closed 落在冻结产物写盘之后 ⇒ 可绕过（`run_provision.py`）|
| `472c844` | **R1-6** | 签字来源零校验（`"0"*64` 占位指纹放行）（`view_manifest.py`）|
| `1e3be7f` | **R1-7** | 配置与 CLI 冲突静默取其一（`run_stage.py`）|

**⛔ 不在本单范围**：`c56cbe1`（R1-5，terra 产出）= 路 1 的范围；批 C（渲染 / 命名 / 像素预算，半截在 `git stash`）。

**基线**：orchestrator 独立全量 `pytest -q -n 8` ⇒ **2089 passed + 10 xfailed 零红**（起点 2068 → 净增 21 条锁、零回归）。

---

## 2. 上游（冲突处以裁定为准）

| 文件 | 作用 |
|---|---|
| [`request/2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md`](2026-08-03_reading_ruler_r1_batchB_rework_dispatch.md) | **r1 派工单**：R1-1…R1-7 逐条原始要求 + §3 锁纪律 + J-1/J-2 |
| [`request/2026-08-03_reading_ruler_r1_batchB_j1j2_ruling.md`](2026-08-03_reading_ruler_r1_batchB_j1j2_ruling.md) | J-1 / J-2 的 orchestrator 裁定 |
| [`request/2026-08-03_reading_ruler_r1_batchBC_dispatch.md`](2026-08-03_reading_ruler_r1_batchBC_dispatch.md) | 批 B/C 原派工单（锁 L-10…L-23、§4 明令禁止清单、§5 交付要求）|
| [`request/2026-08-03_reading_ruler_r1_batchBC_ruling.md`](2026-08-03_reading_ruler_r1_batchBC_ruling.md) | **裁定 —— 与派工单冲突处以它为准**（含追加约束 #1「不得在任何一层折回 bool」/ #2）|
| [`request/2026-08-03_reading_ruler_r1_batchB_review_sol.md`](2026-08-03_reading_ruler_r1_batchB_review_sol.md) | **上一轮给 sol 的审阅单**：其 §3 的 **P-3…P-9 没跑完**，本单要你补完（见 §4）|
| [`verdict/2026-08-03_reading_ruler_r1_batchB_review_sol.md`](../verdict/2026-08-03_reading_ruler_r1_batchB_review_sol.md) | sol 的**部分稿**（跑到一半被其平台内容策略中断，P-1/P-2 + 5 条候选 MAJOR，**全部读码推断零探针**）|
| [`execution/2026-08-03_reading_ruler_r1_batchB_glm.md`](../execution/2026-08-03_reading_ruler_r1_batchB_glm.md) | 施工执行日志（§6 = r1 段：设计 / 改动 / neuter 自查 / 缺口披露）|
| `AI_agent/CLAUDE.md` §1.5 | 不变量，尤其 **#4 gt 铁律**、**#6 复杂度可扩展性** |

---

## 3. 本项目在这类审阅上栽过的坑（**请当作已知失效模式来找**）

1. **「锁绿 ≠ 锁真绑」**（栽过两次）：① W4 那条锁断言 `score_vs_gt is not None`，而判卷器**拒绝时产出的侧车也不是 None**
   ⇒ 锁绿着、判卷其实在拒，施工自查 / 主控轻门 / GLM 对抗审**三道关全漏**；
   ② **r0 的 13 条锁无一走 `cmd_run` / `cmd_flow`**，且 L-13 直接把 `None` 传给内部函数、**绕过 argparse 默认值 `exploratory`**
   ⇒ **锁绿着而缺陷还在**。⇒ r1 派工单 §3 明令：**锁必须经过真实 CLI 入口**，断言落**具体 check-id 行 + `checks.json` 头部字段**。
   **⭐ 这是本单权重最高的核查点。**
2. **「边界写窄就被实现得同样窄」**：连续多轮 REWORK 的共同结构 = 机制选对、边界留给施工方猜。
3. **「探针 ≠ 锁」**：临时脚本验过一次不等于回归里有守卫。
4. **「机制写了、没接线」**（第 N 次）：`provision_run_policy` 的 `context` 参数曾**全仓零生产调用者传参**
   ⇒ 「其余 toggle 记进 `run_policy.json` 作非哈希上下文」**从未发生**。J-1 就是为此立的。
   **凡看到新增参数 / 新增字段，先问「谁真的传它 / 谁真的读它 / 读了会不会改变判定」。**
5. **「raise ≠ 没落盘」**（R1-4 的本体）：fail-closed 发生在写盘之后 ⇒ 磁盘上已留下可用产物。
6. **「一个字段认 config、另一个不认」** = 本轮缺陷的指纹（R1-1 的本体）。**这个形状很可能不止一处，请做同族扫描。**

---

## 4. 承重命题

> 逐条给 **成立 / 不成立 / 无法判定 + 证据**。证据 = 文件:行 + 你实际跑的命令与输出摘录。
> **「读代码看起来没问题」不是证据。**

### 4A. 针对 r1 六条本身

#### G-1（最高权重）六条的锁**全部真绑**、走**真实入口**、断言落在**具体 check-id 行**

- **逐条独立 neuter**：摘掉哪一处实现 ⇒ 恰好红哪几条 ⇒ 有无连带 ⇒ **有没有摘掉实现仍然绿的假锁**。
- **逐条核入口**：R1-1 / R1-2 / R1-7 的锁**是否真的经过 argparse / CLI 命令函数**，
  还是又一次绕过默认值直接喂内部函数（= r0 L-13 的复发）。
- **核断言形态**：有没有落在「返回值存在 / 总数变了 / 字段非空」这类等于没断言的形状。
- R1-4 的锁必须断言**失败之后磁盘上没有可用产物**（不是只断言 raise）；
  R1-6 的锁必须断言**伪造的 `image_sha256` 被拒**（r0 fixture 里那个 `"0"*64` 期望通过，现在应该反过来）。

#### G-2 病灶在**所有真实路径**上都关上了（不是又挑了几条路接上）

- **要你证伪的形式**：**找出一条仍能让「声明的档」与「实际执行的档」分叉的路径。**
  候选面：`run` / `flow` / `provision` / `resample` / `record` / `judge` / `report` / `isolation` build+merge /
  任何读 `EffectiveRunPolicy` 的下游。**找到一条 G-2 即不成立。**
- **同族扫描**：还有没有**别的「一个字段认 config、另一个不认」的不对称**（本轮指纹）。

#### G-3 R1-2 的 fail-closed 没有把历史 replay 打死，也没给非法值留后门

- 非法 / 缺失 / 漂移三态在**新 run provisioning** 时是否都 fail-closed；
  历史 replay 的只读容忍是否**必须标 legacy**、**能不能冒充 regression**（裁定追加约束 #2 的底线）。
- **要你证伪的形式**：构造一个输入，使非法档位值在某条路上仍只 warn 并回落。

#### G-4 R1-3 的四态真的一路保留到 `checks.json`，没有任何一层折回 bool

裁定追加约束 #1 逐字要求「不得在任何一层折回 bool」。r0 在 `validation_run.py` / `case_metadata.py` /
`evidence_preflight.py` 三处折叠过。

- **要你证伪的形式**：**构造一条从输入到 `checks.json` 的路径，使 `unknown` 与 `declared_false` 产出逐字节相同的下游表示。**
  序列化、默认值、`model_dump`、`or` 短路、`if not x`、`dict.get(..., False)` 都是候选。
- 另核：`pipeline.py` 也在这条 commit 里被改了 —— **它为什么需要改？改动有没有超出 R1-3 的范围？**

#### G-5 J-1 的处置真的落地了

J-1 = policy hash 覆盖面收窄是否安全。orchestrator 已核实**两个不在 hash 里的 toggle 能改变 gate① 事实与阻断面**
（`validation_scope=DOWNSTREAM_ONLY` ⇒ 整段跳过 0–4 的 validators；`require_ep` ⇒ 增一条 fail-closed 的 ERROR），
且那条「记进非哈希上下文」的兜底**全仓零生产调用者传参**。

- **核裁定怎么判的、施工怎么落的、落的是不是同一件事**（裁定见上游表）。
- **核 `context` 现在真的被传了吗**：谁传、传了什么、**有没有任何消费者读它**、
  还是又一条「记录了就以为守住了」的**第二类假锁**。

#### G-6 J-2 的处置（混合列表）没有把合法输入误伤

拒绝畸形输入 vs 静默兼容 —— 核裁定与实现是否一致，且**真实 sm24 / sm21 的现有输入形态不会被新 raise 误伤**。

#### G-7 边界合规（逐条核，给证据）

① 未 push；② `gt/**` 与 sm24 `testdata_prompt.json` **零字节改动**；③ 未读 GT；
④ 未原地改历史 manifest / attempt / GT；⑤ 无「当前样例转绿」式验收；⑥ 未从产品 `dimensions[]` 反推；
⑦ 未把 N/A 一律计 miss（object-conditional N/A 应保留且带机器可读原因）；
⑧ `stroke_dimension_consistency` **未**被升成硬门；⑨ 未顺手做批 C / 批 D / R1.5；
⑩ 欠规格边界有没有被自行降级为假设。

### 4B. 补完 sol 上轮没跑完的 P-3…P-9（**按 r1 之后的当前状态审，不是 r0**）

原文见 [上一轮审阅单 §3](2026-08-03_reading_ruler_r1_batchB_review_sol.md)。摘要 + 本单口径：

- **P-3 真实 sm24 / sm21 manifest 的 `content_sha256` 逐字节不变** —— **本批不可协商的前提**（已签字 GT 信任链）。
  施工用「按 testdata 形态分支」的联合类型保哈希：无 `dimensioned_views` 键（sm24）⇒ bool；茎字符串列表（sm21）⇒ bool；
  结构化对象列表 ⇒ `DimensionedApplicability` 对象。
  **⚠️ 这条要你真跑**：跑一次真实的 `load_score_view_bindings`（sm24 签字 GT + 现行 manifest），**看它出不出分**
  —— 上一轮的坑 #4 就是「三方都验了机制，没有任何一方真的跑一次完整流程」。
  ⛔ 只需跑签字侧车的**校验**，**不需要看 GT 里的答案数字**。
  另核 Pydantic v2 的联合序列化在**往返**（load → dump）后是否真的保 bool 类型与字节。
- **P-4 L-10 / L-11 这对对照锁真的证明了「disposition 按 profile 走」** ——
  同字节产品、同检查，只有发卷前 policy 不同 ⇒ L-10 四条 closure blocker + attempt 被 **filed 而非 accepted**、L-11 零 blocker、
  **两者事实行逐字相同**。**要你证伪的形式**：找出一条使两者事实行不逐字相同的合法输入（哪怕只差一个 N/A 原因字符串）。
  另核 L-12（policy drift 在**创建 attempt 之前**拒绝）与 L-13（新 regression run 缺结构化 `run_profile` ⇒ provisioning 失败）
  —— ⚠️ **L-13 正是上轮被判「绕过真实 CLI」的那条，重点看 r1 有没有真修**。
- **P-5 L-21 的 fixture 与真 sm24 同构，锁没有空转** —— fixture 必须 5 个 required view（含 plan 与 elevation 两类）；
  声明 `declared_true` 后 `dimensions_present` / `dimension_p1a_fields` 各 5 行**由 N/A 转真实判定**；
  **其他 check-id 逐项不变**；**四条 closure 仍 block**（打开尺寸类检查不得顺手洗掉已有阻断）。
- **P-6 产品内容不能决定考卷（L-22）** —— 固定 trusted `true`，清空 / 填充产品的 `dimensions[]`
  ⇒ manifest / applicability / **分母不变**；空数组必须使 `dimensions_present` **fail/block，不是 N/A**。
  **要你证伪的形式**：找一条产品可控的输入，使 `dimensioned` 或分母发生变化 = **考生改考题**。
- **P-7 neuter 自查真实、零连带** —— 已并入 G-1，**在 G-1 里一并交付即可**。
- **P-8 §4 明令禁止清单零违反** —— 已并入 G-7。
- **P-9 复杂度可扩展性（不变量 #6）** —— `DimensionedApplicability` 与 `run_policy` 的 schema，
  在**非方形 / 退台 / 挑空 / 中庭**的将来会不会成为要推翻的假设？**只要判断，不要求设计。**

---

## 5. 你可以做 / 不可以做

- ✅ 读全仓任意源码与测试；跑测试；读 `AI_agent/` 下任意文档与 git 历史。
- ✅ **破坏性探针（neuter 验锁）一律只在 `/tmp` 的克隆里做**：
  `git clone --local --no-hardlinks /workspaces/EnergyPlus-Agent-dev <你的 scratchpad>/probe`，在克隆里改、在克隆里跑。
- ⛔ **不改主工作树、不提交、不 push、不 stash**。发现要改的地方，写进审阅报告让施工方改。
- ⛔ **主仓库里只跑只读 git 命令**（`git log` / `git show` / `git diff`）；
  ⛔ **不要在主仓库跑 `git status`**（会抢 index 锁，本项目已因此卡死过一个施工席）。
- ⛔ **不读 GT 答案数字**（`case_tests/test_baseline/gt/`；铁律：gate①/执行器绝不 import，人与 gate② judge 才可读）。
- ⛔ 不要扩范围到 R1-5（路 1）/ 批 C / 批 D / R1.5。

**跑测纪律**：`pytest -q -n 4`（⛔ 不许 `-n auto`〔内存〕，⛔ **永远不许加 `-m` 过滤**）。
基线 = **2089 passed + 10 xfailed 零红**。⚠️ 另一个审阅子代理可能同时在跑测，故限 `-n 4`。

---

## 6. 交付

报告落 **`AI_agent/logs/reviews/verdict/2026-08-03_reading_ruler_r1_crossreview_claude_glm.md`**，含：

1. **总判定**：APPROVE / APPROVE-WITH-CHANGES / **REWORK**（BLOCKER / MAJOR / MINOR / NIT 计数）。
2. **G-1…G-7 + P-3…P-6 / P-9 逐条**：成立 / 不成立 / 无法判定 + 证据（文件:行、命令与输出摘录）。
3. **逐锁 neuter 台账**：锁名 → 摘掉哪一处 → 红了哪几条 → 有无连带 → 是否假锁 → **是否经过真实 CLI 入口**。
4. **清单外自主发现**（上一轮 GLM 就是在清单外抓到第二道无锁守卫 S-1，请照做）。
5. **你证伪失败的尝试也要写** —— 这些是反向坐实，价值不低于发现缺陷。
6. 独立全量测试结果（命令 + 尾部输出原文）。

**⚠️ 做完一件存一件、先落骨架再补**（本项目已两次因会话中断白做整轮）。
**⛔ 骨架里的「暂定 REWORK」不得当结论**：报告必须自带「本文最终版」标记。

**orchestrator 轻门 = 独立全量 + 亲核 diff + 独立复跑 neuter，是唯一权威门；你的报告不是终裁，但 BLOCKER 一律先信。**
