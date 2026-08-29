# 跨家族审请求书 · ②-1b（`revisions` 台账 + `as_signed` + B1 指纹锚 + F-D 加宽）

- **日期**：2026-08-29 · **请求方**：orchestrator（Claude 主控）· **审阅方**：GLM 家族（`scripts/glm_code.sh`，glm-5.3）
- **档位**：工程档 · **审的档位**：升一档、跨家族
- ⭐ **送审对象 = 两个 commit，⛔ 别审工作树**：
  - **`9f0266b`** `08.29_O21b_RevisionsLedgerAndAsSignedDerivation_B1AndFDFingerprints`（主）
  - **`2196723`** `08.29_O21b_RecordCommitHashInExecutionReport`（补记一句话）
  - **基线** = `a40d56d`（纯文档）。审阅期间**主控不动这两个 commit 之外的被审对象**。
- **施工方自述** → `AI_agent/logs/reviews/execution/2026-08-29_o21b_facts_ledger_execution.md`
  ⛔ **一律以 `git diff a40d56d..2196723` 为准**，自述只当索引。
- **派工单** → `AI_agent/logs/reviews/request/2026-08-29_o21b_revisions_and_as_signed.md`

---

## 〇、⛔ 请这样审

1. ⛔ **不要相信送审方的 RESULTS**，直接对夹具重跑。
2. ⛔ **引用位置一律回文件 `grep -n "<锚点>"` 核过** —— 对 `git show` 输出 grep 到的行号**不是文件行号**。
3. ⛔ **一次跑出来的红不是证据，一次跑出来的绿也不是**。判定行为变化前重复跑。
4. ⛔⛔ **绝对不许 `pip install -e .` / 任何写 `site-packages` 的命令**（venv 全机器共享）。
5. ⛔ **验锁用的临时 neuter 只在 `/tmp` 副本里做**，⛔ 不许在工作树里改了再还原。
6. ⭐ **最重要的一条**：除了核对下面列的攻击面，**请再找一种能骗过这些判据的、真实的错误形态** ——
   本项目的历史是**每一轮跨家族审都击穿过一次**，六轮里第五轮那次的作弊「产物里没有一个假数，
   却优于诚实产物且八门全绿」。⛔ 送审方自己挑的破坏方式挑不出自己的盲区。

---

## 一、本单做了什么（五件，⛔ 请自行用 diff 核范围）

| | 内容 | 主要文件 |
|---|---|---|
| **R1** | `revisions` 台账 schema + sm25 五条线的**机器产出待签清单**（全 `unsigned`）| `src/agent/judge/gt_revisions.py`（新，427 行）|
| **R2** | `as_signed` 机械派生 + 逐位可复现门 | 同上 |
| **R3** | B1：`converter_implementation_fingerprint` 从显式 `None` 填成闭包指纹 | `src/agent/judge/as_measured.py`（+38/−7）|
| **R4** | F-D：`converter_sha256()` 从单文件字节哈希 → **13 文件 AST 归一化闭包哈希** | `src/agent/judge/tarch_normalize.py`（+136/−2）· `gt_raw_layer.py`（+59/−6）|
| **R5** | facts 落盘到**新开的** `case_tests/test_baseline/gt_staging/` | `src/agent/judge/gt_facts_staging.py`（新，93 行）|

**施工方报的读数**（⛔ 请独立复现，别抄）：全仓 `3292 passed, 13 xfailed, 0 failed`；
新增 39 条 = `test_gt_revisions_and_as_signed.py` 23 + `test_gt_facts_staging_sm25.py` 5
+ `test_as_measured_facts_layer.py` +4 + `test_tarch_converter_reproducibility.py` +7；
`.pth` 哨兵跑前跑后相同。

---

## 二、⭐ 七个攻击面（前两个施工方已自测承认无锁，⛔ 请判断严重性与修法）

### A1 · **F-D 的 legacy 豁免集合今天没有任何锁**（施工方已自测确认）

`tarch_normalize.KNOWN_PRE_F_D_CONVERTER_SHA256` 是冻结常量集合，用来让已签字件在指纹加宽后不集体变红。
**施工方自测原文**：往里多塞一个**凭空捏造的哈希**，
`test_gt_raw_layer.py` + `test_gt_promotion_path.py` + `test_tarch_converter_reproducibility.py`
**全部 106 passed、零变红**。

⭐ **请判断**：这是不是本项目栽过的那个形状 ——
**「以向后兼容为名加回旧口径」曾经让 6 把锁全绿骗过（17 passed）**，实害是信任根静默挂回可清理目录。
- 往这个集合里塞一个值，**等价于宣布哪一份产物的实现漂移可以不算数** —— 谁有权宣布？
- 最小修法是什么？（例：集合成员必须逐条带 case 名 + 理由 + 一条断言「该 case 今天确实在旧定义下可复现」）
- ⚠️ 注意施工方**故意没有豁免 sm24**（保留 F-132 可见性）——请核实这个"不豁免"是真的，
  且**两者走的是同一段代码路径**（否则"有牙"是假的）。

### A2 · **`gt_staging/` 没有写保护，且与 `gt/<case>/facts/` 同名**（施工方自报最薄弱处）

新目录 `case_tests/test_baseline/gt_staging/<case>/facts/{as_measured,revisions,as_signed}.json`。
- `gt/` 的唯一写者是晋升、`gt_sources/` 的唯一写者是签字流程；**这个新目录没有唯一写者**。
- 文件名与将来 `gt/<case>/facts/` **同名** ⇒ 若某次晋升实现直接整目录拷贝，
  **一份从未跑过可复现门的假货可能被当真货晋升**。
- 施工方建议的最小限制：让 `write_facts_candidate` 落盘前**强制跑一次 `verify_as_signed_reproduction`**，
  把「写进去」和「能过复现门」绑成一个动作。⭐ **请判断这够不够** ——
  它防的是「写了没验」，⛔ 防不了「别人绕开这个函数直接写文件」。

### A3 · ⭐⭐ **消费对账的守恒面选错了**（主控 2026-08-29 实测，⛔ 请独立复现）

主控在 `plan-F1`（as-received）实测：

```
all_wall_handles = 226      wall_lines_total = 223
face_lines = 222   non_orthogonal = 1   degenerate = 0     ⇒ 223 = 222 + 1 + 0 逐位成立
```

⇒ **对账等式全绿，同时 3 笔墙层墨迹无声地离开了记录**（`226 − 223`）。
守恒面守的是「**收集到的**」，⛔ 不是「**看见的**」。同族 `absence-conflates-causes-in-observables`。
⚠️ 顺带：`consumed_wall_handles` 实测**长度 = 0** —— 字段在、没人填，
而「空列表」与「确实没有被消费的」在产物上分不开。

**请判断**：① 复现得出吗 ② 归属是 ②-1a 的遗留还是 ②-1b 该管 ③ 正确的守恒面应该是什么。

### A4 · **两把「非正交」尺子，同一个词两种归宿**（主控实测）

| handle | as-received 几何 | 谁判的 | 归宿 |
|---|---|---|---|
| `13AD` | dx=3639.90 · **dy=5.81** | 转换器 `tau_axis` = **1 mm**（两腿都超）| ⛔ 整条丢弃，**事实层无一处点名** |
| `13AE` | dx=3640.10 · **dy=5.81** | 同上 | ⛔ 同上 |
| `13AF` | **dx=0.19** · dy=120.00 | 转换器**放行**；`as_measured` 按 0.1 mm 整数是否相等判 | ✅ 进 `non_orthogonal_lines` |

**请判断**：两个阈值该不该显式命名、该不该合并；以及「被转换器丢弃」这一类要不要也itemize。

### A5 · **`candidate_action` 是派工单里没有的新字段**（施工方自己加的）

施工方的理由：派工单同时要「候选 action 可见」和「未签字进不了 `as_signed`」，
一个字段装不下 ⇒ 拆成 `candidate_action`（不受签字约束）与 `action`（受约束），
`derive_as_signed` 只读 `.action`。
**请判断**：这个分离是**结构性的**还是**可绕过的** ——
试着构造一条记录，让 `candidate_action` 的内容以任何方式影响 `as_signed`。

### A6 · ⭐⭐⭐ **签一条 `translate` 之后，`as_signed` 里的墙与它点名的面线静默失同步**（主控**已实测**，⛔ 请独立复现）

`derive_as_signed`（[`gt_revisions.py:280`](../../../src/agent/judge/gt_revisions.py#L280)）只重写 `view.face_lines`，
`walls` / `openings` / `converter_readouts` 原样 `model_dump` 带过；
而 `AsMeasuredViewV1._ledger_identity` 校验的是台账恒等式、id 唯一、悬空引用、三桶互斥并集，
**⛔ 没有一条比对 `wall.face_lo` / `face_hi` / `thickness` 与它引用的那两条面线的实际 `const`**。

**主控实测（纯内存，未写树）**：在 `plan-F1` 上签一条 `translate`（`field="const"`，`delta_0p1mm=500` = 50 mm），
打在一条**被墙真实引用**的面线上：

```
面线 1379:                       const 0 -> 500              （动了）
墙 w_x_0_2400_52400_86400 自报:  face_lo=0 face_hi=2400 thickness=2400
它引用的面线实际 const:           lo=[500]  hi=[2400]   ⇒ 实际间距 1900
⇒ ⛔ 没有 raise，派生成功；墙自报 240.0 mm，实际 190.0 mm
```

⭐⭐ **最锋利的一处**：`AsMeasuredWallV1` 的 docstring **逐字声称**
「`thickness` 是两条存储面线的整数差，所以**『从两条面线重算再逐位比对』是一道真的检查**，
不是重跑一遍浮点公式」—— **文档声称这道检查是真的，而全仓没有任何代码做它。**
同族 `gate-with-only-negative-assertions-is-unobservable`。

⚠️ **今天不咬人**（sm25 五条全 `unsigned` ⇒ `as_signed == as_measured`）⇒ **潜伏**；
而 `as_signed` 恰恰是**两把判分尺子将来都要读的那份东西**。
施工方在注释里**声明了这个边界**（「一次移动大到会改变配对的翻译超出本单范围」），
⛔ **但没有为它加门、也没有测它** —— 声明边界 ≠ 守住边界。

**请判断**：① 独立复现得出吗 ② 正确的处置是「派生后重跑配对」还是「加一道一致性门并对不上就响亮失败」
③ 它该在 ②-1b 返工里解，还是随 ②-1c（`AnswerCompiler` + 依赖闭包）一起解。

### A7 · **B1「外部锚」退化成「计算方法可审计」**

施工方判断：走「指纹存进受签字保护的载体」这条路在本单约束下**不可执行**，依据两条事实核查 ——
① `HumanReviewAckV1` 签的四个字段里**没有一处能装实现指纹** ② 本仓库**没开 GPG**（`commit.gpgsign` 未设置、`HEAD` 无签名）。
⇒ 最终锚 = 代码自己算自己（范围从 1 个文件扩到 13 个文件的 AST 归一化哈希）。
**请复核那两条事实核查**；若有误，R3 的结论要重推。
⭐ 并请判断：**「计算方法可审计」算不算 sol 的 B1 要的「外部获授权指纹锚」** —— 施工方自己写了「⛔ 没有升级成真正的外部签名，这是本单留下的、明确没解决的缺口」。

---

## 三、⛔ 本单范围之外（⭐ 显式对账，免得缝里那半没人审）

以下**不在本次审阅范围**，且**各自有明确去处**，⛔ 不要因为它们没做而给本单开阻断：

| 不审什么 | 去处 |
|---|---|
| `AnswerCompiler` / 两种出模形式 / 6a-6b-6c / 依赖闭包 / 局部计分 | **②-1c**（派工单草稿已写） |
| 逐边 `boundary_condition` | **②-1d**（F-121） |
| 改 `promote_gt_v3`、修 **F-128**（回滚不对称） | 随 gt 重做重签 |
| 修 **F-132**（sm24 晋升件已漂移） | 同上；⭐ 本单**故意保留它可见** |
| 正交吸附（转换器把丢弃改成吸附） | ⚠️ **状态有变，见 §四** |
| correction 侧任何改动 / 判分器改读事实层 | **②-2** / ②-1c |

---

## 四、⭐ 请你顺带裁一件事（本单的下游后果，主控已实测）

②-1b 交付后主控实测：

```
签字件      plan-F1 face_lines = 225      plan-F2 = 222
as-received plan-F1 face_lines = 222(+1 非正交)  plan-F2 = 222（逐位相同）
逐视图 handle 集合差：只在签字件 = ['13AD','13AE','13AF']，as-received 侧无多出
```

⇒ **`as_signed` 结构上比签字图少 3 条面线**（因为那 3 条要么被转换器丢弃、要么不是常数坐标面线，
而用户拍板①「`action` 先只实现 `translate`」使它们无法被台账补回）。
⇒ **②-1c 原定的头号验收「形式 B 必须复现今天签字的 `gt.json`」结构上过不了。**

⭐ 并由此**推翻一条现行口径**：指南 §十写「正交吸附**在今天的判分上不承重**，因为**签字件一条歪线都没有**」——
那句话在 `as_measured` 还从**签字件**出的时候是对的；**08-28 把它改成从 as-received 出之后，歪线进到了事实层的输入里，它承重了。**

**请给意见（⛔ 不是让你现在改代码）**：甲 = 先做正交吸附（转换器把丢弃改成吸附，那 3 条自动变成轴对齐面线，
根本不需要 revision，但要重跑全部签字件对照且 F-D 指纹会翻转）；
乙 = 加一种拉直类 `action`（走「遇到再加」，但「把哪条斜线吸到哪根轴上」本身就是吸附规则，
等于把吸附实现在台账里 = 同一件事做两遍）。
⭐ **若你判断有严格更优的第三条，请直接给出** —— 本项目「停下上报」的历史统计是 **38/38 都是派工方的题错了**。

---

## 五、裁决形式

`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT`，并把 findings 分成
**阻断** 与 **不阻断** 两栏，每条带**可复现命令 + 实测数字**。
裁决书落 `AI_agent/logs/reviews/verdict/2026-08-29_o21b_crossreview_glm.md`。
