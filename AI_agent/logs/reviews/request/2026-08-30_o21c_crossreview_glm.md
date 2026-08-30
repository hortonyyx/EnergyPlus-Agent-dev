# 跨家族审请求书 · ②-1c（AnswerCompiler + 出模两形式 + 依赖闭包 + **出口全检**）

- **日期**：2026-08-30 · **请求方**：orchestrator · **施工方**：**GPT 家族** · **审阅方**：GLM 家族（**交换审**）
- ⭐ **送审对象** = **`407fa44`**；**基线 = `88ea056`**。⛔ 一律以 **`git diff 88ea056..407fa44`** 为准，施工方自述只当索引。
  （当前 HEAD = `422c627`，它**只动 `AI_agent/` 三份 md**，与被审代码无关。）
- **派工单** → [`2026-08-30_o21c_answer_compiler_dispatch.md`](2026-08-30_o21c_answer_compiler_dispatch.md) ·
  **执行记录** → [`../execution/2026-08-30_o21c_answer_compiler_execution.md`](../execution/2026-08-30_o21c_answer_compiler_execution.md)
- **主控权威全量**（已跑）：**3378 passed / 13 xfailed / 0 failed**，14m28s、`-n auto`、exit 0；
  `.pth` 与 HEAD 前后哨兵均同、树两次皆空；`3355 + 23 = 3378` 逐文件闭合。**⇒ 你不需要重跑全量**，受影响子集即可。

---

## 〇、⛔ 请这样审

不信任何自述，直接重跑 · 引用位置一律回文件 `grep -n` 核过（⛔ 别在 diff 文本上数行号）·
一次跑出来的红/绿都不是证据 · ⛔ 不许 `pip install -e .` / 任何写 `site-packages` 的命令 ·
⛔ 不许改被审对象（临时 neuter / 变异只在 `/tmp` 副本，建议 `git archive 407fa44`）· 唯一可写 = 你的裁决书。
⭐ **本轮同机没有别的席位在飞**，你可以用 `-n auto`。

⭐⭐⭐ **本轮的方法论要求（这是重点）**：跨家族审已**连续六轮击穿、六次同一病族**，
**没有一次是「门算错了」** —— 每一次都是**门量的那个东西被换掉了**（锚 / 坐标系 / 分组键 / 目标目录 / 比较字段集 /
**某个名词的外延**）。⇒ 请对本单每一道新门套用**三问**：
① 量得准不准 · ② ⭐ **它量的那个东西能不能被换掉** · ③ ⭐⭐ **反问「哪个方向【没有】锁」，再问「为什么没有」**
（上一轮的答案是「**一加锁就会红**」——那不是缺锁，是缺陷本身在挡着锁）。

---

## 一、做了什么（一句话）

新增 `src/agent/judge/answer_compiler.py`（1045 行）：**一份事实 → 一个确定性派生器 → 两种出模形式**
（`form_a_axis` / `form_b_exterior_skin`），外加 sol B6 的**依赖闭包作废半径**六条、
reading 题目册改从事实层出（`denominator_from_facts`）、净空派生表，
并把 F-146 的结构性正解 **「出口全检」** 落成 `read_facts_for_compilation`。
另背走 NF-1（`write_facts_candidate` 改 `-> None`）· NF-4 · **F-148**（`angle_deg` 进人过目的吸附清单）。

**主控已独立复核、⛔ 不需要你重复的两件**：
1. **答案根零改动** —— `git show --name-only 407fa44` 里 `case_tests/test_baseline/gt/` 零条目；改的是 `gt_staging/`。
2. **staging 三件套的 diff 就是 7 片叶子**（2 个新 `angle_deg` + 5 个 hash 传导），五个 revision 对象逐对象相同。

---

## 二、⭐ 六个攻击面

### A1 · ⭐⭐⭐ 「出口全检」的**信任根在哪** —— 它验的是自洽，不是权威

`read_facts_for_compilation`（[`answer_compiler.py:1013-1045`](../../../../src/agent/judge/answer_compiler.py#L1013)）
读答案根 facts 时逐次 `verify_as_signed_reproduction`。而那道 verify
（[`gt_revisions.py:634-647`](../../../../src/agent/judge/gt_revisions.py#L634)）**只做一件事**：
`as_signed == derive(as_measured, revisions)` 逐字节。**主控实测：它不读任何外部锚。**

⛔⛔ **做这个实验的合法方式（派工方已预先裁定，⛔ 别为它停下上报）**：
在 `/tmp` 副本里 `monkeypatch.setattr(ac, "REPO_ROOT", tmp_path)` 造一个**假答案根**。
⛔ **真实 `case_tests/test_baseline/gt/` 一个字节都不许写** —— 那是答案根，动它等于全部历史成绩作废（gt 铁律）。

⇒ **请构造并跑通这个攻击**：改一份 `as_measured`（几何真的动），
**连带重算 `revisions.as_measured_content_sha256` 与 `as_signed`**（三件套内部完全自洽），
放进答案根 ⇒ **出口全检会不会全绿放行**？

- **若会** ⇒ 请判定：F-146 的「结构性正解已实现」这句话**覆盖的范围要重述成什么**。
  ⭐ 注意 sol 的返工条 **①「facts compiler 要外部获授权指纹锚」在盘面上仍标 ⛔ 未做**
  ⇒ 请给出「出口全检 + 外部锚」二者的**分工边界**（哪一半本单已兑现、哪一半仍空着），
  ⛔ 不要简单判成「本单没做外部锚所以扣分」——先判**本单的文字有没有把它说成已经做了**。
- **若不会**（存在我没找到的外部锚）⇒ 请贴出那道锚的 `file:line` 与实测。

⭐ 这条正对本项目的老病族 [[self-consistent-gates-anchor-on-product-chosen-apertures]]：
**重算式判据只验证了「它没算错自己的谎」**。

### A2 · ⭐⭐⭐ 出口全检**今天从没在真实路径上跑过**

**主控实测**：`case_tests/test_baseline/gt/` 底下**零个 `facts/` 目录**（facts 只存在于 `gt_staging/`）
⇒ 今天**每一次**真实调用都走 [`answer_compiler.py:1030-1031`](../../../../src/agent/judge/answer_compiler.py#L1030)
的 **staging 回退**，答案根那一支**结构上到不了**。
三条锁（`tests/test_answer_compiler_exit_gate.py`）**全部**靠 `monkeypatch.setattr(ac, "REPO_ROOT", tmp_path)` + 合成三件套。

⇒ 请查三件：
1. ⭐ **这是「没尺子量」还是「没跑到那一段」**（[[two-kinds-of-latency-no-ruler-vs-never-reached]]）——
   facts 将来靠什么动作进答案根？**`promote_gt_v3` 本单明确没碰**。
   请追一遍：promote 路径**会不会真的把 facts 三件套放到 `gt/<case>/facts/`**？
   ⭐ **预先裁定**：`promote_gt_v3` 在 §三 里是「⛔ 不许**改**」，⛔ **不是**「不许读、不许判」——
   **读它、判它、指出它缺什么，全部在本单范围内**（⛔ 别为这条停下上报）。
   若不会 ⇒ 这道门**永远不会被触发**，它是一道**结构上不可观测**的门。
2. ⚠️ **回退支的跨根问题**：`ac.REPO_ROOT` 被 monkeypatch 之后，
   回退调用的 `gt_facts_staging.read_facts_candidate(case)` 用的是 **`gt_facts_staging` 自己的根**（未被 patch）
   ⇒ 测试里「tmp 答案根为空」会去读**真实 staging**。请判这是测试隔离瑕疵还是会咬到生产路径。
3. **`test_answer_root_read_rejects_bytes_that_arrived_by_an_ungated_route`** 篡改的是
   `as_signed.face_lines[0].along_max`。请问：**篡改 `as_measured` 或 `revisions` 呢？**
   三个文件各自被篡改时是不是**都**会红（⛔ 别只验一个方向）。

### A3 · ⭐⭐⭐ 验收 2 那道门，**主控自己量下来疑似零存货**

派工单验收 2 写的是「**抹掉事实层所有 `basis` 字段，编译器输出逐位不变**」，
对应锁 = [`tests/test_answer_compiler_profiles.py:101-124`](../../../../tests/test_answer_compiler_profiles.py#L101)。
它的做法是：**先自己往 `diagnostics` 里塞一个** `{"basis": "outer_skin", "edge_basis": "wall_axis"}`，
再 scrub 掉所有键名含 `basis` 的项，比较两次编译结果。

⛔ **主控实测**：真实 `gt_staging/sm25-L_anchor/facts/as_signed.json` 里
**键名含 `basis` 的字段 = 0 个**（递归全量扫描）。
⇒ 那么 scrub 在真实数据上是 **no-op**，`with_basis` 与 `without_basis` 的唯一差别
**是测试自己刚种进去的一个 diagnostics blob**。

⇒ **请判这道门有没有牙**，并回答本项目那句自查
（[[gate-teeth-direction-follows-fixture-inventory]]）：
⛔ 别问「有没有对照物」，**要问「它声称覆盖的那种量，有没有被真的量到」**。
具体三问：
1. 「编译器偷吃 converter 的坍缩判断」这件事，**真实的载体是什么**？
   （是 `as_signed` 里的某个键？`converter_readouts` 的结构？还是 `request`？）
   —— **若真实载体根本不叫 `basis`，这道门就是在量一个不存在的东西。**
2. 有没有**别的方向**能让编译器拿到坍缩结论而这道门看不见？（请试着造一个。）
3. 若你判定「facts 里结构上就不可能有 basis」⇒ 那么**这道门恒绿、不可观测**
   ⇒ 请给出**有牙的替代形态**（或明确判定验收 2 本身该改写）。

### A4 · ⭐⭐ `wall_bands` → `cap_handles_v/h` 换轨：那条恒等式是**结构的**还是**语料的**

施工方**没有**照抄上一席位的 `wall_bands` 改动，改用生产几何的 `cap_handles_v/cap_handles_h` 直取，
并锁了「**所有 band 的 handle 并集恰等于 direct map 全集**」（sm24/sm25 各一条，
[`tests/test_denominator_from_facts.py:79`](../../../../tests/test_denominator_from_facts.py#L79)）
+ 一条反事实锁（清空 `jamb_cap_bands` 只让历史审计数归零，`targets`/`opening_targets` 逐位不变）。
**主控认为这是论证不是「看起来合理」**，所以这条送你打的是它的**边界**：

⇒ **那个「并集 == 全集」在什么输入形态下会不成立**？请从 `_build_wall_bands` 的分区实现出发判断：
它是**分区的数学后果**（那就永远成立、锁是恒等锁），还是**依赖两栋楼恰好没有落单 handle**（那就是语料巧合）。
⭐ 这正是 F-147 刚栽过的形状：R1 那行**七格全绿**，根因是**全语料在该带里零存货**。
若你判成恒等锁 ⇒ 请说明它还剩什么分辨力；若判成语料巧合 ⇒ 请造出反例。

### A5 · ⭐⭐ 依赖闭包六条：**分母是谁给的**，`available + NA == expected` 是不是恒等式

R3 六条各有夹具（`tests/test_answer_compiler_closure.py`），核心断言是
「**不得因缺失而缩分母**」「`coverage_expected` 保持 2」「`available + NA == expected`」。

⇒ 请查：
1. **`coverage_expected` 从哪来** —— 是**参照侧**（facts / request 声明的应有件数），还是**产品侧**（编译器自己数出来的）？
   ⭐ 本项目铁律：[[invalidation-blast-radius-must-be-scoped]] ——
   **分母必须是参照侧派生的**，产品侧的不确定性无权删参照目标。若它其实是产品侧数出来的，这六条全部要重判。
2. `available + NA == expected` 若三个数**都由同一段代码同时产出**，它就是**恒等式**（[[lock-must-exercise-real-entry-point]] 的反面）。
   ⇒ 请造一个输入让它**本该不等**，看门红不红。
3. **规则 4「一个歧义洞口不得杀掉 zone 数与外轮廓」的边界谁定** ——
   「局部」的半径是显式声明的，还是从实现里冒出来的？

### A6 · ⭐ 记账与禁令核对（**请独立验，⛔ 别信我**）

1. ⚠️ **执行档有一处因果写错了**（主控核过，属不阻断但影响你读它）：
   它写「`answer_compiler` 新引用使 `reading_grade.py` 已真实进入测试可达图」。
   **实测 `answer_compiler.py` 与 `as_drawn/denominator.py` 都不 import `reading_grade`**；
   真正的覆盖来自**本单新加的测试** [`tests/test_denominator_from_facts.py:15`](../../../../tests/test_denominator_from_facts.py#L15) 直接 import。
   ⇒ **删 allowlist 这个动作方向上是诚实的**（覆盖真的长出来了），但请你独立确认。
2. ⭐ **真正要判的是它的下游后果**：`scripts/tool_scripts/affected_tests_rules.yaml` 删掉
   `src/agent/judge/as_drawn/reading_grade.py` 那条之后，**改判分核心文件的「受影响子集」半径缩小了**。
   ⇒ 请跑 `affected_tests.py --changed src/agent/judge/as_drawn/reading_grade.py` 的**前后对照**，
   并回答：**改 `reading_grade` 的打分逻辑，新选中的那个子集能不能红**？
   （若只有一条 import 型测试选中 ⇒ 判分文件的回归面被静默收窄了。）
3. 已签字件 `request.json` 的 `compute_request_sha256` 前后不变（验收 10）—— 请独立复算贴原文。

---

## 三、⛔ 范围之外（显式对账）

- **edge `boundary_condition` 字段化**（②-1d）· **correction 侧任何改动**（②-2，另有一份设计稿在你手上）
- **重签任何答案** · **改** `promote_gt_v3`（⭐ **读它、判它在 A2 里是明确要求的**）· F-128 / F-132 ·
  正交吸附的**判定与做法**（②-1b-S / F-147 已定死签字）
- **NF-2 / NF-3**（TOCTOU · `.tmp` 清扫）—— 派工单**明确裁定不修、记为已知边界**，前提是本单不引入并发写。
  ⇒ ⭐ **你要验的只有那个前提**：`git diff 88ea056..407fa44` 里**有没有引入对 staging 的并发写或 retry**。有 ⇒ 前提失效，这条就回到范围内。
- 全量跑测（归主控，已跑）

⚠️ **排除条款只证明我想到了这些**。缝里若还有一块两份单子都没覆盖的，**请点名**
（[[review-scope-complement-must-be-reconciled]]：拆成两份请求书送审 ⇒ 并集要显式对账）。

---

## 四、裁决形式

`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT`；findings 分**阻断**/**不阻断**两栏，
每条带**可复现命令 + 实测数字**。裁决书落
`AI_agent/logs/reviews/verdict/2026-08-30_o21c_crossreview_glm.md`。
