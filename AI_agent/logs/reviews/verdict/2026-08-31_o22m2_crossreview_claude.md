# 跨家族审裁决 · ②-2 **模块 2** correction 证据契约类型层

- **裁决**：**APPROVE-WITH-FINDINGS**（阻断 0 · 不阻断 6）
- **送审对象** = `31f873d` · **基线** = `8abd6e0` · **审阅方** = Claude 家族（只读席位 · 换人审 · 恒升一档）
- **请求书** → [../request/2026-08-31_o22m2_crossreview_claude.md](../request/2026-08-31_o22m2_crossreview_claude.md)
- **复核环境**：`git archive 31f873d` 到 /tmp 副本，`PYTHONPATH=<副本>` 令 import 解析到副本（避开 editable `.pth` 串回主树），所有 neuter/变异只改副本。跑测 `-n0`（单文件 28 collected，避免与在飞席位争 CPU）。⛔ 未 `pip install -e .` · ⛔ 未改主树被审对象 · ⛔ 未 `git add`/`commit`。
- **主控权威全量**：31f873d = 3471 passed / 13 xfailed / 0 failed（未复跑，按主控读数采信）。

---

## 〇、总述

模块 2 是**纯类型层 + 硬不变量 1–8 校验器**，零接线。我独立复核后确认施工方**没有虚报**：三份真实产物各自构造并校验通过（`test_acceptance_2` 我在副本上复跑绿），28 条锁绿，两个是非题都对，NF-4 前四种确实响亮、第五种确留 pin。其自报的两处最薄弱（B1/B2）**都被我复现且施工方的自评基本成立**。

判 **APPROVE-WITH-FINDINGS** 而非 REWORK 的依据：所有不阻断项**今天零流量**（无人 import `evidence_contract`），实害只在接线日；且施工方在 execution 档已**主动**披露 B1 并请求确认真空期，未掩盖。给定零接线 + 权威全量 3471 绿，不构成阻断。

但有一条主线要点名：**校验器把大量「引用完整性」锁得很死，却漏了两处「同源 / 载荷闭合」的结构不变量（B1 与 A3 同源）**——两者都属**接线前必补清单**，见下。

---

## 一、⛔ 阻断项：**无**

---

## 二、不阻断项（按重要性排序）

### F-1 · B1 载荷闭合缺口 + 边界推诿（施工方自报最薄弱，我复现且判其边界站不住）
- **现象**：`channel_status.walls=present` 但 `wall_claims=[]`、`face_dispositions=[]`、零 debt 的 bundle **通过 `validate_evidence_bundle`**。设计稿 §3.3 立 `channel_status` 的动机正是防「墙走新腿、openings 悄悄仍从任意含 `strokes` 的文件里捞」——这个洞恰好放过那种形态。
- **我的复现命令与读数**（副本上 `/tmp/probe_b1_b2.py`）：
  ```python
  doc = {"schema": SCHEMA, "observations": {"face_lines": []}, "declarations": {}, "hypotheses": {}}
  # walls=present, source_input_ids=("b1",), wall_claims=[], dispositions=[], debts=[]
  validate_evidence_bundle(art)
  # → 输出：B1 RESULT: walls=present + 0 wall_claims + 0 dispositions -> VALIDATES (hole confirmed)
  ```
- **三问逐条回答**：
  - **① 今天有没有实害**：无（零接线，零流量）。实害在**接线日**（模块 3/7）——若那时不补，一个「墙腿接了但没产出任何 claim」的空跑会被判为合法。
  - **② 边界「载荷闭合归模块 3」站得住吗**：**站不住**。`walls→wall_claims`、`plan_openings→opening_claims` 的闭合是**纯 intra-bundle 检查**（不需 adapter、不解析散文、只看 bundle 自己的字段）。而 `dimensions/room_roles/elevation_openings` 在 bundle 里**根本没有载荷成员** ⇒ 它们只能是 `absent+debt`，`present` 对它们无意义。所以「present 是否真有载荷」只对 walls/openings 有意义，且**这两者本层就能判**。施工方**自己在 execution 档第 177–178 行承认**：「`present 却零 claims 零 debt` 这个极端形态**本层就能判，没判是我的留白**」——这与我的判断一致：这是把**自己该判的**推给了模块 3。
  - **③ 「无一假数却八门全绿」自评对不对**：**对**。channel_status 量对了「状态」这个名词，但「载荷是否真的随行」这个**载体**可被换成空而门不觉——正是本项目 [[gate-measures-right-but-carrier-gets-swapped]] 家族。自评成立，且升高了此项的分量：它不是「少一个 nice-to-have」，是作者自认的招牌病族被留在原地。
- **影响**：接线日的静默空跑风险。
- **建议方向**：在 `validate_evidence_bundle` 补一条 intra-bundle 闭合——`channel_status[c].state=="present"` ⇒ 该 channel 有对应载荷成员非空（walls→有 wall_claim 或 disposition；plan_openings→有 opening_claim），**否则必须带一条显式「零载荷 debt」**。若坚持归模块 3，则**必须**把它写进模块 3 派工单的验收项（像 pin 那样对账），⛔ 不能只留在 execution 档的散文里。

### F-2 · A3（我自造第 6 类：跨视图/跨楼层身份，结构合法但语义假）
- **现象**：一条 `paired_faces` 墙声明，`face_a_ref` 落在 **1F 产物**的 F01、`face_b_ref` 落在 **2F 产物**的 F02——**一堵墙的两个面在不同楼层**——**通过 `validate_evidence_bundle`**。校验器 paired_faces 分支从不断言四个 ref（`face_a_ref`/`face_b_ref`/`hypothesis_ref`/`pair_candidate_ref`）**同源**；hypothesis / candidate 匹配只比 `observation_id` **字符串**，而 `F01`/`F02` 这类 id 在 1F、2F 产物里都存在（sm25_1f / sm25_2f 就同时在库）。
- **我的复现命令与读数**（副本上 `/tmp/probe_a3.py`）：
  ```
  A3 RESULT: cross-floor wall (face_a on 1f, face_b on 2f) -> VALIDATES.
    claim.face_a_ref.input_id = planA floor 1f
    claim.face_b_ref.input_id = planB floor 2f
  ```
  （构造：两份合法 AsDrawnPlanV2 产物 planA/planB，各含同名 F01/F02 同轴；claim 的 hypothesis_ref/candidate_ref 都指 planA，face_b_ref 指 planB；四个面各给一个 disposition。校验全过。）
- **为何是「结构合法但语义假」**：所有引用都解得开、id 都对得上、轴一致、hypothesis/candidate 都匹配——结构无懈可击；但物理上单堵墙的两个面不可能跨楼层。这是 15（施工方）+5（NF-4）种**都没覆盖**的一类，正落在设计稿 §3.2「身份即 input_id」这条纪律**没有被校验器兑现**的缝里。
- **影响**：接线日若模块 3 adapter 有「记错某面来自哪个 source」的 bug，本校验器——作为承重的输入完整性门——会放行。今天零接线、无实害。
- **建议方向**：paired_faces 分支加一条 `face_a_ref.input_id == face_b_ref.input_id == hypothesis_ref.input_id == pair_candidate_ref.input_id` 的同源断言（或更一般地：一条 wall_claim 的所有 ref 必须同 input_id）。这与 F-1 同源——都是「结构不变量没立全」，建议合并进接线前必补清单。

### F-3 · B2 词法耦合（施工方自报次弱，我确认其「仍响亮」成立，但耦合是真实隐患）
- **现象**：不变量 6/7 用 `"AMBIGUOUS" in (decision.reason or "")`（evidence_contract.py:693）区分 `AMBIGUOUS_CONTRACT_MATCH` 与 `MALFORMED_DECLARED_CONTRACT`；判别键是 classifier 的**文案子串**，该文案在 `vector_contract.py:331` 的 `f"AMBIGUOUS: matches ..."`。
- **我的复现与读数**：
  ```
  grep -n '"AMBIGUOUS" in' src/agent/correction/evidence_contract.py   # → 693
  grep -n 'AMBIGUOUS' src/agent/reading/vector_contract.py            # → 331 f"AMBIGUOUS: matches ..."
  ```
  读源码确认该判别整段在 `if decision.contract_id != meta.source_contract_id:` 内，**三个分支（AMBIGUOUS / MALFORMED / else CONTRACT_MISMATCH）全部 `raise`**，无任何 return/pass 出口。
- **施工方自评「仍响亮、只是 code 错位」是否成立**：**成立**。改一句措辞最坏只会让本应 `AMBIGUOUS_CONTRACT_MATCH` 的输入落到 `MALFORMED_DECLARED_CONTRACT` 或 `CONTRACT_MISMATCH`——**永远不会静默通过**。这与请求书引用的 [[lexical-guard-cannot-be-completed]] 的**致命面**（词法漏洞导致静默漏过）不同：这里词法只影响**分类精度**，不影响**是否拦截**。
- **影响**：非阻断。属可维护性隐患：跨仓改 classifier 文案会静默降低本门的 code 精度（下游若按 code 分流会误判）。
- **建议方向**：让 classifier 用**结构化枚举/标志位**（如 `decision.match_kind == AMBIGUOUS`）而非把语义藏在自由文本 `reason` 里，evidence_contract 据结构字段判，不据子串。

### F-4 · B3 记账：nf4_1 / nf4_2 断言的是**测试工厂**的 code（非阻断，因验证器级对照真实存在）
- **B3 主实验（neuter validate_evidence_bundle → 空操作）读数**：
  ```
  PYTHONPATH=<副本> python -m pytest tests/test_o22m2_evidence_contract.py -n0
  # → 11 failed, 17 passed
  ```
  **恰好 11 条**在摘掉承重校验器后变红 = 真正「摘得动」`validate_evidence_bundle` 的锁：
  `test_inv1..inv8`（8）+ `test_n1_...witness` + `test_observed_unclaimed...` + `test_nf4_4_...gap_index`。
  ⇒ 承重锁 = `validate_evidence_bundle`（生产代码）的说法**属实**。
- **其余 17 条分类**（我逐条溯源，非转引）：
  - pydantic **生产模型**校验器（也是生产齿，另一机制）：`test_acceptance_1`、`test_n1` 的无-witness 子断言、`test_legacy_non_unknown_basis...`；
  - **生产函数** `as_drawn_face_index`（去重齿）：`test_nf4_3`——我 neuter 工厂 `_must_exist` 后它**仍绿**（因其齿在生产函数，我没 neuter），坐实其齿可摘且在生产代码（evidence_contract.py:644）；
  - classifier 前提 / determinism / type-walk / 零接线行为门：其余。
  - **只有 `test_nf4_1` / `test_nf4_2`** 断言的 code（`SELECTED_PAIR_REFERENCES_UNKNOWN_FACE` / `BUCKET_KEY_REFERENCES_UNKNOWN_FACE`）**只在测试文件**（helper `_must_exist`）——即这两条锁**锁的是测试工厂自己**。
- **B3 反向实验（neuter 工厂 `_must_exist`）读数**：`nf4_1`、`nf4_2` 双双失败（DID NOT RAISE / KeyError 泄漏），`nf4_3` 仍绿 ⇒ 坐实前两者依赖测试工厂拒绝。
- **裁决**：**不阻断**。因为同破坏族的**验证器级对照**在生产代码且被 11 条里的 inv2/inv3 摘中——`PAIR_HYPOTHESIS_MISMATCH`(evidence_contract.py:904，nf4_1 对照)、`DISPOSITION_REFERENCES_UNKNOWN_FACE`(1048，nf4_2 对照)。施工方「每族破坏都有绕开构造器、直接打在校验器上的独立证据」**成立**，**没有一条破坏族只有测试工厂在把关**。仅记账提醒：`nf4_1`/`nf4_2` 作为「before/after readings」时，其 assert 语义是「今天工厂会拒」，**不是**「校验器会拒」——两者别在 review 时混为「校验器有齿」。

### F-5 · A2 记账：第五种 pin 的对账**已完成**（请求书前提已过时）
- 请求书 §A2 的问法基于「模块 3 派工单还没写」。**该前提今天不成立**：`AI_agent/logs/reviews/request/2026-08-31_o22m3_evidence_adapters_dispatch.md` 已存在，第 52–56 行**显式接住** `test_nf4_5` 这条 pin，且第 56 行加了纪律「若判归模块 4 必须改写 pin 只归模块 4，⛔ 不许两边都不接」，验收项第 3 条把「pin 从 PASS 变红 或 改写只归模块 4」写成硬门。plan.md:309 亦登记。
- **裁决**：**非隐患**。[[review-scope-complement-must-be-reconciled]] 的「缝里没人派」在此**已被对账**。仅提示：pin 目前是一条**绿测试 + docstring**，本身不强制模块 3 去补——真正的保证在模块 3 派工单的验收硬门，那门已写。✓

### F-6 · A1 记账：NF-4 #4 纳入本单的理由成立，无夹带越界
- `gap_index` 越界纳入本单：理由「纯引用完整性、无散文解析」**成立**——我在 B3 主实验里看到 `test_nf4_4` 被 neuter 校验器摘中（`OPENING_GAP_INDEX_OUT_OF_RANGE`，evidence_contract.py:998），是真 validator 齿，不是工厂齿。
- 逐条核范围（`git diff --numstat 8abd6e0..31f873d`）：模块 2 只新增 `evidence_contract.py` + `test_o22m2_evidence_contract.py` 两个源文件，**无夹带其它 src 改动**。
- **裁决**：理由成立，无顺手扩范围。✓

---

## 三、两个是非题

1. **「零接线」是真的吗？** —— **是**。`git diff --stat 8abd6e0..31f873d -- src/agent/reading/vector_contract.py src/agent/pipeline.py` = **空**（两文件整文件零 diff）。`grep -rn evidence_contract src/ --include=*.py`（排除自身）= **空**（无生产代码 import）。副本上 `test_the_type_layer_imports_no_pipeline` 复跑绿。✓

2. **有没有碰进 `canonical_bytes` 的面 / 任何已落库产物？** —— **模块 2 侧没有**。`grep -nE 'open\(|\.write|Path\(|gt_staging|canonical_bytes' evidence_contract.py` = **空**（纯函数、零写盘）。⚠️ **须知**：送审 commit `31f873d` **同时打包了 `src/agent/judge/as_measured.py` 的 +254/−21**，那是 **F-153**（`derive_boundary_ring_losses` 等边界环损失，`git diff` 逐条确认无一行 `evidence_contract`/`CorrectionEvidenceBundle`），按请求书 §五 **不属本单**，故未审；但请注意此 commit 混装两单，若后续需回滚模块 2 需留意这一点。F-153 是否碰 `content_sha256`/已落库 staging 归 F-153 那一单复核。

---

## 四、给用户的一句白话

施工方交的这份「证据契约」是一层**纯定义 + 检查器**，还没接到任何实际流程上，所以今天不会出事。我逐条核过：他没虚报，三份真实图纸都能过检，28 条检查里有 11 条是真正咬在承重检查器上的（我把检查器拆掉验证过）。发现两个**同一类的小缺口**：检查器管住了「引用对不对得上」，但漏了两处「东西是不是真在同一个来源、通道说有货是不是真有货」——其中一处（跨楼层拼成一堵墙）是我自己造出来撞的，另一处施工方自己也承认了。两处**今天都不咬人**，但**接线之前必须补**，我已写清补法。判**通过但带整改项**，不阻断。

---

*复核人：Claude 家族跨家族审席位 · 2026-08-31 · 副本复现脚本 `/tmp/.../scratchpad/probe_b1_b2.py`、`probe_a3.py`（会话内临时件）*
