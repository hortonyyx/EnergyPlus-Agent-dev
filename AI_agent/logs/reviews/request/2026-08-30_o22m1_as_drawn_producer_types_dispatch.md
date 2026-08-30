# 派工单 · ②-2 模块 1：as-drawn v2 的**生产者自己的类型**

- **日期**：2026-08-30 · **派工方**：orchestrator · **施工方**：**Claude 家族** · **审**：GLM 家族（换人审）
- **基线**：**`2be082d`**（⭐ ②-1d 已交件并过主控权威门 **3385 绿**；工作树干净）
- **状态**：✅ **已发**（2026-08-30）

---

## 〇、⛔⛔ 排程前提（本单最要紧的一条）

**本单⛔ 不许与另一个写席位同时在主树开工。** 立此条的事实依据（本项目实测）：
- 2026-08-30 白天：主控明知复核方在审 `gt_facts_staging.py` 仍派了动 `src/` 的活 ⇒ **复核方中途撞红**
- 2026-08-27：同机三路各跑 `-n auto` ⇒ `load average 17.44/16 核`、worker `OSError`、**无 summary 行**（同机竞争假红）
- ⛔ **也不许用 worktree 绕开**：editable 的 `.pth` **硬编码指向主树**，别的树里跑 python 会**静默串台**

⇒ ⛔ **~~原开工条件「②-1d 已交件且主树 git status 干净」已作废~~**（2026-08-30 二次发单时改写）。

### ⭐ 二次发单的实况与新口径（**派工方已预先裁定，⛔ 别为它停下上报**）

**同机确实有另一个写席位在飞**（GPT 家族，②-1d 返工，正在写 `src/agent/judge/answer_compiler.py`
与 `tests/test_boundary_condition_facts.py`）。**派工方判定可以并行**，依据是**实测的 import 隔离**：

```
本单面：reading/as_drawn/ · vector_contract.py · tests/test_f97_vector_contract.py
对方面：judge/answer_compiler.py · tests/test_boundary_condition_facts.py

实测 ① tests/test_f97_vector_contract.py 里 "judge" 出现 0 次
实测 ② as_drawn_v2.py / vector_contract.py 里的 3 处 "judge" 全是【注释】，无一是 import
实测 ③ 运行时 import reading 侧两个模块 ⇒ 被拉进来的 judge 模块 = 【零】
⇒ 你的测试看不见对方的在途改动
```

**⇒ 因此本单的开工纪律改成三条硬约束：**
1. ⛔⛔ **不许 `git commit`、不许 `git add`（任何形式）** —— 提交归主控。
   理由：对方席位也在这棵树上，**`git add -A` 会扫走它写了一半的东西**（本项目已实犯三次），
   而 `commit` 会移动 HEAD、作废我给对方的环境读数（本项目今天已实犯一次）。
   ⇒ **你只管改文件，改完在收工报告里列全路径，主控来提交。**
2. ⛔ **跑测只跑你自己那几个文件，且用 `-n 4`** —— ⛔ 不许 `-n auto`、
   ⛔ 不许跑 `affected_tests.py` 的全仓 AST 遍历（对方文件可能处于半截状态）、⛔ 不许跑全量。
3. ⭐ **`git status` 现在【不干净】是正常的** —— 那是对方的在途改动。
   ⛔ 别读成异常、⛔ 别清理、⛔ 别 `git checkout --` 任何不属于你的文件。

⭐ **发单时的实况（2026-08-30）**：②-1d 已交件（`8442442`）并过主控权威全量 **3385 绿**，基线已推进到 `2be082d`。
⚠️ **同机有一个【只读】的审阅席位在飞**（GLM 家族，审 ②-1d，实验全在 `/tmp` 副本、只写自己的裁决书）
⇒ **它不写主树**，与本单无写冲突；**但跑测一律 `-n 6`**，⛔ 不用 `-n auto`（同机竞争会造假红）。

---

## 一、承重前提（**主控 2026-08-30 实测**，⛔ 请自己复核，不符就停下上报）

### 1. as-drawn v2 的产物今天是**裸 dict**，生产者没有自己的类型

[`as_drawn_v2.py:560 assemble()`](../../../../src/agent/reading/as_drawn/as_drawn_v2.py#L560) 的签名是 `-> dict`；
全仓 `class \w*(Hypothes|Percept)\w*` 对 Python 类**零命中**。
主控枚举了它实际返回的键：**44 个**（`schema` / `observations` / `declarations` / `hypotheses` /
`face_lines` / `pairs` / `pair_candidates` / `non_wall_face_lines` / `unpaired_wall_faces` /
`solid_band_walls` / `ambiguous_face_lines` / `opening_candidates` / `opening_types` / `ledger` / …）。

### 2. ⭐⭐⭐ **今天的 detector 只做键形判别 ⇒「声明了 schema 但结构不符」静默当合法**

[`vector_contract.py:214-219`](../../../../src/agent/reading/vector_contract.py#L214)：
```python
ContractSpec(
    CONTRACT_AS_DRAWN_PLAN,
    Disposition.KNOWN_NOT_CONSUMED,
    lambda raw: _is_declared(raw, AS_DRAWN_PLAN_SCHEMA)
    and _has_keys(raw, "observations", "declarations", "hypotheses"),
    ...)
```
⇒ **只要顶层有那三个键、且 `schema` 字符串对得上，就算「识别成功」** ——
里面装什么、每个桶的元素长什么样，**没有任何东西在看**。

⇒ ⭐ **这就是本单存在的理由**（GLM 判它是**甲档必做**，原文）：
> 不做 ⇒ detector 只能键形判别 ⇒「声明了 schema 但结构不符」静默当合法
> ⇒ §4.4 #7 `MALFORMED_DECLARED_CONTRACT` 无牙 ⇒ **错得读不出**。

### 3. 也没有别人在替它把关

`src/validator/checks/as_drawn.py`（11 道 gt-free as-drawn 门）**至今没接进 `run_pipeline`/gate①**
（`affected_tests_rules.yaml` 的 `uncovered_allowlist` 里逐字写着这条）⇒ ⛔ 别指望它兜底。

---

## 二、要做什么（两件）

### R1 · 新建 `src/agent/reading/as_drawn/schema.py`：**生产者自己的 Pydantic 类型**

⭐ **裁剪范围逐字引 GLM 裁决书 §五表第 1 行**（⛔ 我不转述）：
> 裁剪：字段覆盖 = **墙 + 洞口两族**（`face_lines` / `pairs` / `pair_candidates` / **五桶** /
> `opening_candidates` / `opening_types`——稿子 §3.1 自己点名洞口半边不能丢）；
> **`ledger`/`roles` 等非墙通道登记 plan.md 缓做**

⚠️ **「五桶」是复核方的简写，主控数下来只有四个明显候选**
（`non_wall_face_lines` / `unpaired_wall_faces` / `solid_band_walls` / `ambiguous_face_lines`）
⇒ **请你自己把第五个定下来并写明依据**；若你判定就是四个，**说清楚**，⛔ 别凑数。

**硬要求**：
- 类型必须**由生产者拥有**（放 `reading/as_drawn/`，⛔ 不放 `correction/`），
  且 `as_drawn_v2.assemble` 的返回值要**真的经过它**（⛔ 不许只定义不使用 —— 那是恒真的门）。
- 缓做的通道（`ledger`/`roles` 等）**必须显式声明为「本版不校验」**，⛔ 不许用 `extra="allow"` 一笔带过而不留痕。
- ⛔ **不许改任何几何/判断逻辑** —— 本单只加类型与校验，产物内容**逐字节不变**。

### R2 · detector 从**键形判别**换成**类型判别**

[`vector_contract.py`](../../../../src/agent/reading/vector_contract.py) 里 `CONTRACT_AS_DRAWN_PLAN` 的 detector
改成「调用生产者自己的类型」。
⛔ **本单只改 detector 的判别方式，`Disposition` 仍保持 `KNOWN_NOT_CONSUMED`** ——
把它改成指向新 adapter 是**模块 3** 的事（②-2 后续单），⛔ 不在本单。

---

## 三、验收项（⛔ 每条我都能说出它什么情况下会不通过）

| # | 验收 | ⛔ 什么情况下不通过 |
|---|---|---|
| 1 | ⭐⭐⭐ **有牙**：造一份「`schema` 字符串对、三个顶层键都在、但**桶里的元素结构不符**」的输入，**必须响亮红**；并实测**同一份输入在改动前是绿的** | 改动前后都绿 ⇒ 无牙（[[gate-with-only-negative-assertions-is-unobservable]]）|
| 2 | ⭐⭐ **产物逐字节不变**：真实 sm25/sm24 as-drawn 产物过一遍新类型，**序列化结果与改动前逐字节相同** | 类型顺手「规整」了产物 ⇒ 那是改内容不是加校验 |
| 3 | ⭐ **真的经过它**：`assemble` 的返回值实际被类型校验（⛔ 不是定义了一个没人用的类）—— 请给**摘得动**的证据（把校验拿掉，某条测试必须红）| 定义了但没接线（[[lock-must-exercise-real-entry-point]]）|
| 4 | 「五桶」到底几个 + 依据，**写进 docstring 或执行档** | 含糊带过 |
| 5 | 缓做通道**显式声明**，且**能列出清单** | 用 `extra="allow"` 静默放行、说不清缓了哪些 |
| 6 | `Disposition` 仍是 `KNOWN_NOT_CONSUMED`（⛔ 本单不接 adapter）| 顺手把 as-drawn 接进 correction ⇒ 越界到模块 3 |
| 7 | ⛔ **~~原文「开工时 git status 干净」已作废~~（派工方题错 #50，施工方当场抓出）** —— 二次发单时 §〇 已改成「不干净是正常的（那是并行席位）」，而我**没把验收表重新对撞一遍**。<br>**现行口径**：受影响子集绿 · **收工时 `git status` 里属于本单的路径 == §六 清单**（其余路径必须能指出是谁的）· ⛔ **零 `git add`/`commit`** | 收工时出现本单之外**且说不清归属**的路径 ⇒ 可能扫到了别的席位的在途改动 |

---

## 四、⛔ 明确不做（本单）

模块 2–6（`evidence_contract` / `evidence_adapters` / `wall_compiler` / `decision_schema` / `decision_executor`）·
**把 as-drawn 接进 correction**（模块 3）· `vector_contract` 的**收窄工程**（`CONSUME`→`ADAPT` 重命名 / ledger 重排，
**已登记 plan.md 不做**）· 改 `pipeline.py` 那两句 `wall-centerline` · gt 侧一切 · 降模型智力。

### ⛔⛔ 派工方已预先裁定的两处张力（⛔ 别为它们停下上报）

1. **R2 要改 detector，而 §四禁「`vector_contract` 的收窄工程」** —— **不冲突**：
   禁的是**重命名与 ledger 重排**；**换判别方式**是模块 1 的本体（GLM 原文把收窄工程判为乙、把判别口径判为甲）。
2. ⭐ **验收 3 要「把校验拿掉看测试红不红」，而 R1 禁「改任何几何/判断逻辑」** —— **不冲突**：
   那是 **neuter 实验**（证明锁摘得动），⛔ 不是产品改动。
   合法做法 = 在 `/tmp` 副本上摘，或本地临时摘、**跑完立即还原并在执行档贴还原后的 `git diff` 为空**。
   ⛔ 交件的 diff 里不许留任何 neuter 痕迹。

3. **验收 2 要「产物逐字节不变」，而 R1 要加类型** —— **不冲突**：
   Pydantic 校验**不改内容**。⚠️ 但若你发现真实产物**过不了**你写的类型 ⇒
   **那是必须停下上报的情形**（要么类型写紧了，要么产物真有结构问题，两种处置完全不同，⛔ 别自己选）。

---

## 五、⛔ 停下上报触发器（**分层**）

**必须停**（承重前提错）：
1. §〇 的开工条件不成立（②-1d 未交件 / 主树不干净）
2. §一.2 的 detector 实测核不出来
3. ⭐ 真实 as-drawn 产物过不了新类型（见 §四预裁 2）
4. 本单任务项与本单禁令真的互斥

**只记不停**（外围）：「五桶」到底几个 · 字段命名 · 缓做清单的边界。
⭐ 本项目「停下上报」**累计 48 次全部是派工方（我）的题错** ⇒ 觉得题有问题请一定停。

---

## 六、交件时请列出**本单改动的全部路径**

收工报告里贴一份**明确路径清单**（验收 7 要对着它核）。
⛔ **提交只 `git add` 这些明确路径，不许 `git add -A`** —— 本项目实测三次被 `git add -A`
扫走过并行席位的半成品（最近一次扫走了别人写了一半的 129 行）。
提交前必看 `git diff --cached --numstat`。
