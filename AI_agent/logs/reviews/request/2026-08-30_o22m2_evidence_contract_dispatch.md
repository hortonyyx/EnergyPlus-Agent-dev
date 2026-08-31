# 派工单 · ②-2 **模块 2**：`correction/evidence_contract.py`（统一证据包的类型层）

- **日期**：2026-08-30 · **派工方**：orchestrator · **施工方**：**Claude 家族**（headless 席位） · **审**：**GPT 家族**（换人审）
- **基线**：**`8abd6e0`**（当前 HEAD）
- **口径来源（已过审，⛔ 不是待讨论的设计）** →
  [`../verdict/2026-08-30_o22_evidence_contract_gpt_design.md`](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
  （GPT 出稿 → GLM REWORK → 返工 → GLM 复审 **APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 7**）
- **本单在施工次序里的位置**：设计稿 §9.1 的**第 2 步**「建统一 source ref 与 bundle：
  **先 shadow 生成，不进模型**」。⛔ **模块 1 已交件**（`bff77de`，跨家族审在飞）。
- **接线现状（主控 2026-08-30 走查）** →
  [`../../experiments/2026-08-30_wiring_gap_survey/README.md`](../../experiments/2026-08-30_wiring_gap_survey/README.md)
  ⇒ **闸门只有一行，闸门后面模块 2–6 一个文件都不存在；本单造第一个。**

---

## 〇、⛔⛔ 排程前提（同机有两个席位在飞）

| 席位 | 家族 | 在干什么 | 它碰的面 |
|---|---|---|---|
| 复核 | **GLM** | 审 ②-2 模块 1 | **只读**；实验在 `/tmp` 副本 |
| 施工 | **GPT** | 修 **F-153** | **写** `src/agent/judge/as_measured.py` |
| **你** | **Claude** | 本单 | **写** `src/agent/correction/evidence_contract.py`（**新文件**）+ 它的测试 |

⇒ **三条硬约束：**
1. ⛔⛔ **不许 `git add`（任何形式）、不许 `git commit`** —— 提交归主控。
   `git status` **不干净是正常的**（那是别人的在途改动）；⛔ 别清理、⛔ 别 `git checkout --` 不属于你的文件。
2. ⛔ **不许 `pip install -e .`** 或任何写 `site-packages` 的命令（venv 全机共享，
   2026-08-27 曾因此作废一次权威全量）。
3. ⛔ **跑测只跑你自己那一个测试文件，且 `-n 4`** —— ⛔ 不许 `-n auto`、⛔ 不许跑全量、
   ⛔ 不许跑 `affected_tests.py` 的全仓 AST 遍历（别人的文件可能是半截状态）。

⭐ **写隔离已实测可接受**：本单只新建 `src/agent/correction/evidence_contract.py` 与
`tests/test_o22m2_evidence_contract.py`；GPT 那边只动 `src/agent/judge/as_measured.py`，两面不相交。

---

## 一、本单要造什么（⛔ 一律以设计稿原文为准，本单不重述业务语义）

**唯一交付 = 类型层 + 它的硬不变量校验 + 逐条锁。⛔ 本单不接线、不产 adapter、不碰 pipeline。**

| 要造的 | 设计稿出处 | 备注 |
|---|---|---|
| `ArtifactPointerV1` / `ObservationRefV1` | §3.2 | ⭐ **只引用、不复制几何** —— `WallClaim` 里⛔ 不许出现 `pos_m`/`edges_m`/`runs_m` 的**值** |
| `CorrectionEvidenceBundleV1` 顶层 | §3.3 | 含 `channel_status[]` / `evidence_debts[]` / `content_sha256` |
| **四种正向墙声明**的 discriminated union | §4.1 表 | `paired_faces` · `solid_band` · `single_face` · `legacy_wall_trace` |
| **三种面线处置** | §4.2 表 | `claimed_wall` · `non_wall` · `ambiguous`（⛔ 三者语义不同，别合并）|
| **硬不变量 1–8 的校验函数** | §4.4 | ⭐ **第 9 条不在本单**（那是编译器/执行器的事，属模块 4/6）|

### ⭐⭐⭐ 一处**设计稿自身被后续裁决覆盖**的地方，⛔ 别照抄

设计稿 §4.1 写 `counterface_state = not_in_observations | observed_unclaimed`（**两值**）。
**这已被同一轮复审的不阻断项 N-1 覆盖** ——
[`../verdict/2026-08-30_o22_design_rework_crossreview_glm.md`](../verdict/2026-08-30_o22_design_rework_crossreview_glm.md) §N-1：
> 缺**第六种真实状态**：counterface **墨迹在、被 reader 丢了**（未提升为 face line）。
> `not_in_observations` 字面真而「未观测」假。**sm25 2F `L012`** 即此态，
> reason 自证 "The ink is there — column 655"。

⇒ **本单必须落地第三值**（设计稿建议名 `ink_present_unpromoted`，**必须带像素 witness pointer**），
或按 N-1 给的另一条路把 `not_in_observations` 定义成「**像素通道亦无墨**」的显式检查。
⭐ **三份真实产物的实际路径**（主控实测）：
`AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/{sm25_1f_v2,sm25_2f_v2,sm24_1f_v2}.json`
（模块 1 的测试就吃这三份，见 `tests/test_o22m1_as_drawn_producer_types.py:47-49`）。

### ⚠️ 一处**你一定会撞上的张力**（派工方先说清，⛔ 别自己发明出口）

模块 1 **刻意没有**给第六态造结构槽位，理由写在
`src/agent/reading/as_drawn/schema.py:75-94`：「零真实实例的 union 成员正是缺陷藏身处，
**这个状态归模块 2 的 EvidenceContract**」，它只**钉住了实例** ——
`tests/test_o22m1_as_drawn_producer_types.py:451` 断言今天 `L012` 的载体是**散文**，
**且往那里塞结构化值会被拒**。

⇒ **本单的界限**：**定义**这个枚举值是你的活；
**从今天这份散文产物里【派生】出它**，是**模块 3（adapter）**的活，⛔ 不在本单。
⇒ 若你发现「不解析散文就派生不出来」，**那是设计层的缺口，请停下上报**
（见 §四），⛔ **不许用正则解析散文来把它变出来**（禁令 5）。

---

## 二、⛔ 本单禁令

1. ⛔ **不许改 `src/agent/reading/vector_contract.py` 的任何 disposition** —— 那是模块 7 的一行注册，
   设计稿 §9.1 明写「**只有到第 7 步**才把 as-drawn 改成 `ADAPT`」。今天改 = 让未类型化产物裸进 prompt（F-97 的形状）。
2. ⛔ **不许动 `src/agent/pipeline.py`**（含 `:367`/`:370` 那两句 `wall-centerline`）—— 那是后面的步骤。
3. ⛔ **不许动 `src/agent/judge/`** —— GPT 席位正在写那一面。
4. ⛔ **不许改任何既有测试的断言**让它变绿；既有锁变红 ⇒ **停下上报**。
5. ⛔ **不许用正则解析自由文本 `note` 去猜 basis**（设计稿 §4.1 明令；本项目已实测两份真实产物
   同一个 `pen=="wall"` 字段，一份是外皮线一份是中线，**只写在 `note` 里**）。
6. ⛔ **别在 `.py` 的字符串常量（docstring 也算）里写带仓库根前缀的生产文件路径** ——
   `affected_tests.py` 对任何字符串常量做仓库相对路径子串匹配就**建一条真实依赖边**（**F-152**，08-30 实犯）。
   引用生产模块请用**点号模块名**。⚠️ 这条规则本身⛔ 不能在 `.py` 里举例说明（举例就又造一条边）。

---

## 三、验收表（⭐ 派工方已逐条与 §一任务项、§二禁令**对撞过**）

| # | 验收项 | 对撞检查 |
|---|---|---|
| **1** | 四种墙声明 + 三种处置各有类型，且 `counterface_state` 有**三**个值 | ⭐ 与 §一 那处「设计稿被 N-1 覆盖」一致；**若你只做了两值，本条必然不通过** |
| **2** | ⭐ **拿三份真实产物做夹具**（sm25 1F / sm25 2F / sm24 1F）：各自能构造出 bundle。<br>⚠️ **`L012` 只要求「第三态在类型上存在且可被构造」**，⛔ **不要求**你从今天的散文里把它**派生**出来（那是模块 3）| 与禁令 5 对撞：**若你为了让 `L012` 自动落到第三态而去解析散文，本条就变成违反禁令 5** ⇒ 故本条**故意把派生排除在验收之外** |
| **3** | 硬不变量 1–8 **每一条各有一把锁**，且每把锁**先断言「合法输入下它是绿的」再断言「破坏后它红」** | ⭐ 本项目口径：只有负向断言的门 = 恒红、结构上不可观测（`gate-with-only-negative-assertions-is-unobservable`）|
| **4** | ⭐⭐ `WallClaim` 里**不存在**任何被复制的几何值 —— 请给出一条**机械**断言（遍历类型字段名，禁 `pos_m`/`edges_m`/`runs_m`/`spacing_m` 之类的值字段），⛔ 不是散文承诺 | 与 §一「只引用不复制」对撞；⚠️ `spacing_m` 设计稿允许**只作缓存审计** ⇒ 若你保留它，必须同时有锁证明**代码从两面重算、不读它** |
| **5** | ⭐⭐⭐ **逐字节可复现**：同一份原始 bytes 两次构造 ⇒ `content_sha256` 相同；**改动源 bytes 任一字节 ⇒ 变** | = 不变量 8；⛔ 别用「哈希整份报告」去当子事实的相等判据（本项目记忆条 `hash-of-whole-report-is-not-an-equality-test-for-its-parts`）|
| **6** | ⭐ **本单【没有】接线，请自证**：`grep` 证明 `vector_contract.py` 与 `pipeline.py` **零 diff** | 与禁令 1/2 对撞：**若你顺手接了线，本条必然不通过** |
| **7** | `pytest tests/test_o22m2_evidence_contract.py -n 4` 全绿；并列出你改/新建的**全部文件路径** | 与禁令 3（不跑全量）、禁令「不提交」一致 |

⚠️ **派工方自查记录**：第 1、4、6 条各钉死一个**本单明令禁止的偷懒解**；
第 6 条是**故意要求你证明自己【没】做某件事** —— 本项目累计 50 次派工题错，
其中「验收要求做一件本单自己禁止的事」出现过两次。

---

## 四、停下上报触发器（⭐ **分层**）

**⛔ 必须停（承重前提）**：
- 设计稿的某条要求与本单禁令**自相矛盾**（⭐ 至今 **50/50 全是派工方的题错**，请放心停）；
- 三份真实产物里**有一份构造不出 bundle**，而原因是**设计稿的类型划分盖不住它**（⇒ 那是设计缺陷，归上一层）；
- 既有锁变红。

**⭐ 只记不停（外围）**：字段命名分歧 · 某个 pointer 的 json_pointer 写法 · sm24 与 sm25 的字段差异 ·
本单范围外的其它缺陷 —— 写进执行档即可。

---

## 五、交付物

1. `src/agent/correction/evidence_contract.py`（新）+ `tests/test_o22m2_evidence_contract.py`（新）。⛔ 不提交。
2. 执行档 → `AI_agent/logs/reviews/execution/2026-08-30_o22m2_evidence_contract_execution.md`，
   内含：验收表 7 项逐条的**命令 + 读数**、**你自己认为最薄弱的一处**、以及希望复核方重点打哪里。
   ⭐ 本项目口径：**「加了就会红」= 缺陷本身在挡锁** —— 遇到这句请如实写出来交给第二个人判。

---

# ⭐ 补充（2026-08-30 深夜 · 二次发单）

## 六、⚠️ 一次发单**没跑起来**（⛔ 与题目无关，别读成异常）

首次派给 Claude 家族 headless 席位，进程**立刻退出**，日志全文只有一行：
`You've hit your monthly spend limit`。⇒ **树上零改动、零孤儿件**（主控已 `git status` 核）。
⇒ 本单**原样重发给 GLM 家族**；⭐ **审改派 GPT 家族**（谁写谁不批）。

## 七、⭐⭐⭐ 必须折进本单的一条：**NF-4（GLM 审模块 1 时实测出来的）**

模块 1 已 **APPROVE-WITH-FINDINGS / 阻断 0 / 不阻断 4** 收口 →
[裁决](../verdict/2026-08-30_o22m1_crossreview_glm.md)。
其中 **NF-4 点名要求「显式写进模块 2 派工单」**，原文要点：

> **引用完整性 / 身份唯一性这一类错误，15 条破坏 + 类型 + detector 全盖不住。**
> 五种「结构合法但语义假」的破坏**全部 PASS 且被认成合法 `as_drawn_plan`**（复核方逐项实测）：
>
> | 破坏 | 结果 |
> |---|---|
> | `pairs[0].face_b` → `"L999"`（**悬空引用**）| PASS |
> | `non_wall_face_lines["L999"]`（**桶键悬空**）| PASS |
> | 两条面线**同 `id`**（身份重复）| PASS |
> | `opening_candidates[0].gap_index = 99`（越界）| PASS |
> | `pair_candidates[0].face_b` → `"L999"` | PASS |
>
> 现有防线：11 道未接线门里只有 `check_pair_reconciliation` 接得住其中 **1 种**；
> **桶键悬空被 accounted 并集静默吸收**（只查 `faces − accounted` **一个方向**）；
> `pair_candidates` 完全不被 reconcile；**重复 id 连未接线门都不管**。
> ⇒ ⭐⭐⭐ **悬空 `face_b` = 在不存在的一面上造墙 = 幻觉墙病族**
> （与 ②-1a「确定性 DXF 上 33 条虚构墙」同族）。

⇒ **本单因此多两条任务项**：

### 任务 3 · `ObservationRefV1` 的**解引用必须真的发生**，不能只是「带了个 pointer」
设计稿 §4.4 不变量 1 已经写了「每个 source ref 都能在冻结原始 bytes 中**唯一解析**」——
**本单必须把它实现成会红的校验，⛔ 不是类型注释**。
⭐ 判据：**上表五种破坏，本单交付后【至少前三种】必须响亮失败**
（悬空 `face_b` · 桶键悬空 · 重复 id）。

### 任务 4 · 盖不住的那几种，**必须像 N-1 那样留 pin**
后两种（`gap_index` 越界 · `pair_candidates` 悬空）若判定归模块 3/4，
⛔ **不许静默留白** —— 按模块 1 对 N-1 的做法**钉一条 pin**：
断言「今天这种破坏**能**通过」，并在 docstring 写明它归哪一模块。
⭐ 立此条的理由（复核方原话）：**⛔ 不要留成两份文档缝里没人派的活**
（本项目已有记忆条 [[review-scope-complement-must-be-reconciled]]）。

## 八、验收表追加两项（⛔ 与 §三 并列，一并生效）

| # | 验收项 | 对撞检查 |
|---|---|---|
| **8** | NF-4 五种破坏**逐条给出交付前/交付后的读数**；**前三种必须从 PASS 变成响亮失败** | 与任务 3 一致；⭐ 与本项目口径对撞：**先断言「改动前它确实能过」再断言现在红**（⛔ 只有负向断言的门恒红、不可观测）|
| **9** | 后两种若不在本单，**各有一条 pin** 说明「今天能过」+ 归属模块 | 与任务 4 一致；**若你静默不提，本条不通过** |

⚠️ **派工方二次自查（补上了首次漏掉的那一格）**：
本次除了把验收项与①禁令②任务项对撞，还额外与 **③「已落库/已签字产物的既有承诺」** 对撞了一遍 ——
**本单只新建文件、不改任何已落库产物，也不改任何 schema 的 `canonical_bytes` 参与面** ⇒ 无哈希扰动。
（立此格的事实依据：同日 F-153 那一单**正是栽在这一格**，施工方强制停报，累计题错 **51**。）
