# R1 修尺子 · 批 B 施工审阅单（审 = GPT 侧 sol · 交叉对抗审）

- **日期**：2026-08-03
- **派工方**：orchestrator（端到端主控）
- **审阅席**：GPT 侧 **sol**，effort = **max**（跨家族对抗审；施工是 GLM，**写稿的不审自己的稿**）
- **被审对象**（施工席 = GLM-5.2，两个 commit 合起来才是完整的批 B）：
  - **`627efac`** `8.03_ReadingRulerR1BatchB_S2Freeze_S3Applicability` —— 批 B 主体
    （7 文件：`view_manifest.py` / `run_provision.py`〔新〕 / `checks/reading.py` / `checks/view_manifest.py` /
    `run_stage.py` / `tests/test_reading_ruler_r1_batchB.py`〔新，13 锁〕 / 执行日志）
  - **`2bb189e`** 中的 **`run_policy_freeze.py`（290 行新模块）+ `run_config.py` / `isolation.py` /
    `checks/schema.py` / `checks/view_manifest.py`** —— 这是同一位施工席的**半截工作**，
    在会话被中断时由 orchestrator 代为提交保命（提交标题看着像纯文档，**别被标题骗过去**）。
- **基线**：orchestrator 独立全量 `pytest -q -n 8` ⇒ **2068 passed + 10 xfailed 零红**
  （批 A 基线 2055 + 本批 13 条锁），与施工方自报逐数字一致。
- **不在本单范围**：批 C（渲染 / 命名 / 像素预算）尚未开工，施工席在 `render_vector_to_png.py`
  上留的 28 行半截改动**已 stash、不在工作树里**。⛔ 不要审它、不要顺手做批 C。
- **性质**：**对抗审**。你的任务不是确认它做了，而是**尽力证伪它真的做到了**。

---

## 0. 一句话背景

reading（识图）环节最近所有分数都不可信。已查明**不是模型退化，是判卷这把尺子和运行政策本身坏了**。
批 A（判卷测量语义）已落库（`b8f9a8d`，全仓 2055 绿 + 10 xfail 零红）。
**批 B 修的是第二条**：**声明的严格档从未真正执行** —— `run_config.yaml` 写着 `regression`(fail-closed) + `orthogonal_polygon`，
实际落盘的 `checks.json` 头部却是 `exploratory` + `rectangular`；那一轮 gate① **本来抓到 5 条 fail**，
按 exploratory 算 = **0 阻断**，按 regression 算 = **4 条 blocker** ⇒ **严格档若真生效，那份产物会被当场拒收**。

**⛔ 硬约束：批 A/B/C 三批全绿之前，本项目不得发布任何新的识图分数或「识图变好/变坏」的结论。**
这意味着**这次审阅是那条约束的解除条件之一** —— 放水的代价是后面一整批实验白跑。

---

## 1. 上游（冲突处以裁定为准）

| 文件 | 作用 |
|---|---|
| `AI_agent/logs/reviews/verdict/2026-08-02_reading_ruler_r1_discussion_sol.md` | **你自己的诊断与方案**（S-2 / S-3 + §4 验收锁表）。⚠️ 见 §3 命题 P-1：施工方在 G4 上**主动偏离了你的原文** |
| `AI_agent/logs/reviews/request/2026-08-03_reading_ruler_r1_batchBC_dispatch.md` | 批 B/C 派工单（锁 L-10…L-23、§4 明令禁止清单、§5 交付要求） |
| `AI_agent/logs/reviews/request/2026-08-03_reading_ruler_r1_batchBC_ruling.md` | **orchestrator 裁定 —— 与派工单冲突处以它为准** |
| `AI_agent/logs/reviews/execution/2026-08-03_reading_ruler_r1_batchB_glm.md` | 施工执行日志（设计 §1 + 改动清单 §2 + neuter 自查 §3 + 全仓结果 §4 + 缺口 §5） |
| `AI_agent/CLAUDE.md` §1.5 | 不变量，尤其 **#4 gt 铁律**、**#6 复杂度可扩展性**、**#7 环节控制边界** |

---

## 2. 本项目在这类审阅上栽过的坑（**请当作已知失效模式来找**）

1. **「锁绿 ≠ 锁真绑」**：W4 那条锁断言 `score_vs_gt is not None`，而判卷器**拒绝时产出的侧车也不是 None**
   ⇒ 锁一直绿着、判卷其实是拒的，**施工自查 / 主控轻门 / GLM 对抗审三道关全漏**。
   ⇒ **断言必须落在 `payload.kind` 与具体 check-id 的行上**，落在「返回值存在 / 总数变了」上等于没断言。
2. **「边界写窄就被实现得同样窄」**：本项目连续三轮 REWORK 的共同结构 = 机制选对、边界留给施工方猜。
3. **「探针 ≠ 锁」**：临时脚本验过一次不等于回归里有守卫。
4. **「机制验了、没人真跑一次端到端」**：三方都验了冻结/防漂移/守卫真锁，**没有任何一方真的跑一次完整流程看它出没出分**。

---

## 2b. ⚠️ orchestrator 轻门已发现的两条（**披露给你，别重复劳动；但请做同族扫描**）

全档见 [orchestrator 轻门报告](../verdict/2026-08-03_reading_ruler_r1_batchB_orchestrator_lightgate.md)。
**判定 = REWORK（1 MAJOR）**，返工（r1）由同一施工席在额度恢复后做。**你现在审的是 r1 之前的状态。**

### 已发现 MAJOR-1：`flow` / `run` 这条标准 SOP 路径上，病灶仍可复现

批 B 的立项理由是「声明的严格档从未真正执行」。修复关上了 **isolation** 与 **显式 `provision`** 两条路，
**没关上 `cmd_run` / `cmd_flow`**：

- `run_stage.py:1810-1813` 与 `:1987-1991` 里，`capability_profile` 取自 `run_config`，
  **`run_profile` 只取 `args.run_profile`**（argparse 默认 `"exploratory"`，不是 `None`）
  ⇒ **同一次调用一个认 config、一个不认**；
- `_manifest_for_attempts`（`:121`）只 `provision_view_manifest`，**不调 `provision_run_policy`**
  ⇒ 落不下 `_run/run_policy.json`；
- 于是 `_draw_reading`（`:196-205`）拿到 `legacy_defaulted=True`，回落那个 `exploratory`。

orchestrator 实跑复现：config 声明 `regression / orthogonal_polygon` ⇒ 实际
**`exploratory` / orthogonal_polygon**（半生效）。**13 条锁无一走这条路。**

### 已发现 MINOR-1：配置与 CLI 冲突是「静默取其一」，派工单要的是「直接报错」

`run_stage.py:2229-2233`（`cmd_provision`）实现为 config 优先、CLI 兜底。
方向更安全，但属**未披露的规格偏离**（执行日志 §5 只披露了 G4 那一处）。

### ⭐ 要你做的是同族扫描，不是复述上面两条

1. **还有没有别的路径也没接 resolver**（`resample` / `record` / `judge` / `report` / 下游任何读
   `EffectiveRunPolicy` 的地方），使某条路上「声明」与「执行」仍可分叉？
2. **还有没有别的「一个字段认 config、另一个不认」的不对称**？这个形状是本轮缺陷的指纹，
   很可能不止一处。
3. r1 要补的那条锁应该长什么样才**不空转**（给具体断言形态）。

---

## 3. 承重命题（**逐条给 成立 / 不成立 / 无法判定 + 证据**）

> 命题按「被证伪则整批返工」的权重排序。**P-1 与 P-2 是本单特意留给你证伪的两条。**

### P-1（最高权重·施工方主动偏离了你的原文）policy hash 的覆盖面收窄是安全的

施工方把 gate① 的 policy hash **收窄为只含 `capability_profile + run_profile`**，
理由是「只有这两项被 `check_reading_stage` 实际消费、决定 blocking；把 review/judge toggle
塞进 gate① 事务会引发无意义的 drift 拒绝」。其余 toggle（`confirmation_policy` / `judge_enabled` /
`validation_scope` / `require_ep`）记录进 `_run/run_policy.json` 作**非哈希上下文**、不参与 drift 判定。

**这偏离你 S-2 原文的「validation/review relevant switches」。** orchestrator 采纳了收窄，但**附了披露义务**，
就是为了让你在这里针对性挑战。

- **要你证伪的形式**：**找出一个不在 hash 里、却能改变 gate① blocking 结论（或改变 `checks.json` 事实行）的开关或输入。**
  找到一个即 P-1 不成立、G4 必须回滚到 sol 原文覆盖面。
- **若证伪失败**，请明确写「已尝试穷举 X 个 toggle，均不影响 blocking」，这条反向坐实收窄安全。
- **附带**：非哈希上下文被写进 `run_policy.json` 却不参与判定，会不会造成**「记录了就以为守住了」的第二类假锁**？

### P-2（最高权重）`unknown` 与 `declared_false` 的差异真的一路保留到 `checks.json`，没有任何一层折回 bool

S-3 的核心病灶就是折叠（「该考的题没考」）。裁定追加约束 #1 要求这个差异**不得在任何一层折回 bool**，
且要有一条锁（并入 L-23）专门断言它。

- **要你证伪的形式**：**构造一条从输入到 `checks.json` 的路径，使 `unknown` 与 `declared_false` 产出逐字节相同的下游表示。**
  序列化、默认值、`model_dump`、`or` 短路、`if not x`、字典 `get(..., False)` 都是候选。
- 同时核：**legacy（absent / 茎字符串）** 的只读路径**能不能把「这是 legacy 默认值」表达出来**，
  会不会看起来像一次正常的 `declared_false` 声明（裁定追加约束 #2）。**底线：legacy 默认档不得冒充 regression。**

### P-3 真实 sm24 / sm21 manifest 的 `content_sha256` 逐字节不变

这是本批的**不可协商前提**（已签字 GT 信任链）。施工方用「按 testdata 形态分支」的联合类型保哈希：
无 `dimensioned_views` 键（sm24）⇒ `dimensioned=False`（bool）；茎字符串列表（sm21）⇒ bool；
结构化对象列表（fixture / 新 case）⇒ `DimensionedApplicability` 对象。

- **核**：这个分支有没有**任何**输入形态会让真实 sm24/sm21 落进对象分支；
  Pydantic v2 的联合序列化在**往返**（load → dump）后是否真的保 bool 类型与字节。
- **要你证伪的形式**：**跑一次真实的 `load_score_view_bindings`**（sm24 签字 GT + 现行 manifest），
  看它出不出分。⚠️ 这正是坑 #4 —— 不要只读代码。

### P-4 L-10 / L-11 这一对对照锁真的证明了「disposition 按 profile 走」

L-10（regression + orthogonal）与 L-11（exploratory）要求：**同字节产品、同检查**，
只有发卷前的 policy 不同 ⇒ L-10 四条 closure blocker + attempt 被 **filed 而非 accepted**；L-11 零 blocker；
**两者的事实行逐字相同**。

- **要你证伪的形式**：**找出一条使两者事实行不逐字相同的合法输入**（哪怕只差一个 N/A 原因字符串）——
  若事实行会随 profile 变，这对锁证明的就不是 disposition，而是「检查本身也变了」。
- 另核 L-12（policy drift 在**创建 attempt 之前**拒绝）与 L-13（新 regression run 缺结构化 `run_profile` ⇒
  **provisioning 失败**，不得默认 exploratory）。

### P-5 L-21 的 fixture 与真 sm24 同构，锁没有空转

裁定 §2.1：fixture 必须 5 个 required view（含 plan 与 elevation 两类）；声明 `declared_true` 后
`dimensions_present` / `dimension_p1a_fields` **各 5 行由 N/A 转真实判定**；**其他 check-id 逐项不变**；
**四条 closure 仍 block**（打开尺寸类检查不会顺手把已有阻断洗掉）。

- **核**：断言是否落在**具体 check-id 的行**上；fixture 是不是被简化成「2 个 view / 只有 plan」这种证明不了接线的形状。

### P-6 产品内容不能决定考卷（L-22）

固定 trusted `true`，清空 / 填充产品的 `dimensions[]` ⇒ manifest / applicability / **分母不变**；
空数组必须使 `dimensions_present` **fail/block，不是 N/A**。

- **要你证伪的形式**：找一条产品可控的输入，使 `dimensioned` 或分母发生变化 = **考生改考题**。

### P-7 neuter 自查真实、零连带

执行日志 §3 应逐条记「摘掉哪一处实现 ⇒ 恰好红哪一条锁 / 有无连带」。

- **核**：orchestrator 会独立复跑每一条；**请你抽查至少 3 条**，重点看**有没有哪条锁摘掉实现后仍然绿**（假锁），
  以及**有没有一条实现同时被多条锁覆盖而单条锁其实空转**。

### P-8 §4 明令禁止清单零违反

逐条核：① `stroke_dimension_consistency` **未**升硬门；② **未**原地改历史 manifest / attempt / GT；
③ 无「当前样例转绿」式验收；④ 未从产品 `dimensions[]` 反推；⑤ 未把 N/A 一律计 miss
（object-conditional N/A 保留且带机器可读原因）；⑥ **未读 GT**（`case_tests/test_baseline/gt/`，
铁律：gate①/执行器绝不 import）；⑦ 未顺手做批 D / 批 E；⑧ 欠规格边界有无被自行降级为假设；
⑨ 未 push、未碰 `gt/**` 与 sm24 `testdata_prompt.json` 任何字节。

### P-9 复杂度可扩展性（不变量 #6）

`DimensionedApplicability` 与 `run_policy` 的 schema，在**非方形 / 退台 / 挑空 / 中庭**的将来会不会成为要推翻的假设？
本条只要「有没有烤死当前简化假设」的判断，**不要求设计**。

---

## 4. 你可以做 / 不可以做

- ✅ 读全仓任意源码与测试；跑测试；**在 `/tmp` 做破坏性探针**（neuter 验锁一律只在 `/tmp` 做）。
- ✅ 跑真实评分路径以证伪 P-3。
- ⛔ **不改工作树、不提交、不 push**。发现要改的地方，写进审阅报告让施工方改。
- ⛔ **不读 GT 里的答案数字**（P-3 只需要跑签字侧车的**校验**，不需要看答案）。
- ⛔ 不要顺手扩范围到批 C / 批 D / R1.5。

---

## 5. 交付

报告落 `AI_agent/logs/reviews/verdict/2026-08-03_reading_ruler_r1_batchB_review_sol.md`，含：

1. **总判定**：APPROVE / APPROVE-WITH-CHANGES / **REWORK**（BLOCKER / MAJOR / MINOR / NIT 计数）。
2. **P-1…P-9 逐条**：成立 / 不成立 / 无法判定 + **证据**（文件:行、命令与输出摘录）。
   ⚠️ **「看起来没问题」不是证据。**
3. **清单外自主发现**（上一轮 GLM 就是在清单外抓到第二道无锁守卫 S-1，请照做）。
4. **你证伪失败的尝试也要写**（这些是反向坐实，价值不低于发现缺陷）。
5. 独立全量测试结果（`pytest -q -n 6`，⛔ 不许 `-n auto`〔内存〕，⛔ 永远不许加 `-m` 过滤）。
   基线 = **2055 passed + 10 xfailed 零红**（批 A 之后）。

**orchestrator 轻门 = 独立全量 + 亲核 diff + 独立复跑每一条 neuter，是唯一权威门；你的报告不是终裁，但 BLOCKER 一律先信。**
