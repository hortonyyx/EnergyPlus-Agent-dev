# 裁决 · 模块 2 第三方向（通道声明 `absent`、包里却带着这条通道的载荷）· GLM 跨家族复核

- **日期**：2026-09-01 · **复核方**：GLM 家族（worktree `/tmp/o22m2_review_glm`，detached `8028bab`）
- **被审 commit**：`ba3303c` · 被审对象：`src/agent/correction/evidence_contract.py`（+187/−50）+
  `tests/test_o22m2_evidence_contract.py`（+324/−0，33 → 40 条锁）
- **复核单**：[2026-09-01g_o22m2_absent_crossreview.md](../request/2026-09-01g_o22m2_absent_crossreview.md)

---

## 1. 裁决

**APPROVE-WITH-FINDINGS · 阻断 0 · 不阻断 4。**

**攻击面 1 的必答题（那一刀 + 该不该停报）——结论先行：那一刀是对的，不需要停报。**
证据链见 §2（引入提交说明原文 + design §3.3/§4.2 原文 + 四处代码实测）。施工方的自签字判断成立。

不阻断 findings（§5 详述）：
- **N-1**（施工方已自报，本轮实测证实并给出读数）：「ambiguous 台账行不算 walls witness」这个判断**没有任何锁钉住**——把 witness 谓词改成 `!= "non_wall"`（收 ambiguous 进 witness），m2 40 条 + m2/m3/m4 91 条**全绿**，全链存货 0。
- **N-2**：`_channel_has_payload` 成为**无调用者的死函数**（新实现改用 `_channel_witness_rows`；grep 全仓仅剩定义行）。
- **N-3**（施工方自报「故意没堵」）：`_assert_channel_source_closure` 仍以 `state != "present": continue` 开头——absent 声明的通道，其载荷**来源**不查（堵了会红掉 m4 夹具）。
- **N-4**（既有缺口，非本件引入）：`covered_by_debt_ids` 不与债的 `channel` 对账。

---

## 2. ⭐⭐⭐ 攻击面 1：`face_dispositions` 算不算 walls 载荷 —— 那一刀 + 停报判定

### 2.1 引入旧行的提交 + 提交说明原文

```
$ git log --oneline -S 'if channel == "walls":' -- src/agent/correction/evidence_contract.py
ba3303c 09.01r_...（删除）
bb91f77 08.31c_O22Module2_Approved_AndTwoStructuralGapsClosed   ← 引入
```

`bb91f77`（2026-08-31，模块 2 一轮返工，GLM 施工）提交说明中与该行相关的**全部**内容：

> 返工（GLM 家族）补两条：**present 通道必须真有载荷（或显式零载荷 debt）** + 一条 wall_claim 的所有 ref 必须同 input_id。

**提交说明只定义了方向（present ⇒ 有载荷），没有定义外延（哪些成员的哪些行算载荷）。**
被删代码的 docstring 引 design §3.3 的原句是 "The channels whose payload this bundle type can
actually witness (design §3.3)"——引的是**哪些通道有载荷成员**，不是「每个成员的每一行都见证 present」。
另一处历史锚点：二轮返工 `2148409` 的提交说明里施工方已点名「第三个方向『absent 却带着载荷』至今无门、
未登记——主控接受，已记入下轮」——即本件正是那笔登记的兑现，不存在一个更早的「absent 语义契约」被推翻。

### 2.2 design §3.3 原文核对（verdict/2026-08-30_o22_evidence_contract_gpt_design.md:107-122）

§3.3 只规定了顶层结构与 `channel_status` 的**通道级**语义：

> `channel_status` 是必要的：把 as-drawn 的墙接通，不等于它已经完整替代旧 `ReadingView` 的门窗、
> 尺寸和房间角色。注册表只有在一个源契约的 correction 必需通道都有适配器，或缺失被显式记为当前
> profile 允许的 evidence debt 时，才可把它从 `KNOWN_NOT_CONSUMED` 改为 `ADAPT`。
> ⛔ 不允许"墙走新腿、窗悄悄仍从目录里随便找 `strokes`"。

**§3.3 没有写「成员非空 ⇔ present」的字面配方**，也没有写「台账每行皆载荷」。
它支持的是**成员归属**（walls 的载荷成员 = wall_claims + face_dispositions）——这一点新代码原样保留
（`CHANNEL_PAYLOAD_MEMBERS = {"walls": ("wall_claims", "face_dispositions"), ...}`，且 B-1 来源闭合的
reach 仍覆盖**全部**台账行）。真正给出「谁在说话」区分的是 **§4.2 三种面线处置**（design:150-160）：

> | `claimed_wall` | 被恰好一个正向墙声明消费；成对面对应同一 claim | **进入墙编译器**；… |
> | `non_wall` | reading 感知明确断言这条面线不是墙，并给出理由/类别 | 代码自动排除并记账；**它不是待 correction 猜的歧义** |
> | `ambiguous` | reading 明确弃权 | 合法输入、但形成 known-missing evidence debt |

三种处置的下游动作一栏，正是「claimed_wall 才是 walls 通道在说话」的设计出处。
§4.4 不变量 2（design:176）「每条 as-drawn face line 恰好一个处置」是台账完备性的出处。

### 2.3 不变量 2 的实现——台账真是「源产物的函数」吗（单子点名要自己去代码里核）

`evidence_contract.py:1384-1424`（不变量 2 段）：分母 = `face_index`，由
`as_drawn_face_index(doc)`（`:695`）对每个 as-drawn 源产物逐条面线建索引（`:1114`），
`FACE_WITHOUT_DISPOSITION` / `DUPLICATE_DISPOSITION` / `DISPOSITION_REFERENCES_UNKNOWN_FACE`
双向闭环。**遍历域是源产物的面线，与 `bundle.wall_claims` 无关** ⇒ 「满台账被迫于源产物、
不代表 walls 腿产出」成立。（精确化一处：`claimed_wall` 行同时受 claim↔disposition closure
约束——台账不是 100% 与 walls 腿无关，**恰好 claimed_wall 那一行是 walls 腿的消费记录**，
这正是施工方切刀的位置，与 §4.2 对齐。）

### 2.4 模块 3 / 模块 4 的真实行为（施工方声称，本轮独立核实）

- **模块 3**（`evidence_adapters.py:462-480`）：`walls` 的 state 判据就是 `if claims:`——
  **只有正向 wall claim 非空才声明 present**；否则 `absent` + `missing_channel` debt
  （"no positive wall claim could be derived from this product"），而 `face_dispositions`
  **无条件满载**。施工方「模块 3 已收口 adapter 的真实输出 = walls absent + 满台账」属实。
- **模块 4**（`wall_compiler.py`）：墙实体只从 `bundle.wall_claims` 循环编译（`:1260-1276`）；
  `face_dispositions` 的 `non_wall` 行只产 `honor_non_wall_declaration` 记账（`:1278-1292`）、
  `ambiguous` 行只进 undecided 统计（`:1196-1229`）——**没有一条台账行产出墙**。

### 2.5 旧外延的实际行为面（实测，不是推理）

用同一份 `walls=present + 零 claim + 满 non_wall 台账 + 无 zero_payload debt` 的包在新旧代码各跑一次：

```
NEW code (ba3303c): RAISED PRESENT_CHANNEL_WITHOUT_PAYLOAD
OLD code (ba3303c^): PASSED   ← 旧外延让满非墙台账免 zero_payload debt 撑起 present
```

并实测：`walls=absent + 满 non_wall 台账` 在**旧代码上也放行**（旧代码根本没有 absent 方向的门）。
⇒ **旧外延（台账算 walls 载荷）在 absent 方向从未生效过**；它在 present 方向的唯一行为效果 =
让「零产出的 walls 腿借非墙台账免登记」——这与 F-1 自己的 docstring 初衷
（"'walls wired' quietly meaning the walls leg produced nothing" 必须显式 debt）**方向相反**。
删掉它不是丢契约，是把 F-1 的漏放一并关上。

### 2.6 判定 + 停报回答

- **旧语义是深思熟虑的契约，还是顺手写的？——顺手写的。** 四个独立证据：① 引入提交说明只写方向未写外延；
  ② design §3.3 只支持成员归属、§4.2 的处置语义反而支撑切刀；③ 旧外延唯一行为效果与 F-1 自身 docstring
  的初衷相反；④ absent 方向从未生效（无契约方会写一个在自己唯一管的方向上不生效的契约）。
- **那一刀对不对？——对。** 归属保留（表 + B-1 全行 reach），见证细化（claimed_wall-only），
  每一层都能指到 design 原文或已收口代码（§2.2-2.4）。
- **该不该停报？——不该。** 派工单 §二 自己写了「推荐但不指定」+「第三条路很可能存在而我没想到：
  若你找到严格更优的做法，直接走它并说明」——施工方走的是**单内明文的合法出口**，不是违令。
  反过来，若按 §二 字面配方「成员非空 ⇔ present」实现：任何真实 as-drawn 源的台账被迫满载（不变量 2）
  ⇒ absent 永红 ⇒ 与验收项 2（「walls 真空跑必须放行」）、禁令 2（不许动模块 3）、模块 3 已收口口径
  **三重对撞**——字面配方才是那个必须停报的死锁方向。施工方解开死锁而非制造矛盾。
- 附带：复核单攻击面 1 的表述「被删掉的旧代码……语义恰好与这一刀相反」**过强**（见 §7-②）。

---

## 3. 攻击面 2 / 3 实测结论

### 3.1 变异四方向（每做完立即 `git checkout -- src/agent/correction/evidence_contract.py` 还原，四处均确认树干净）

| 变异 | 内容 | 读数 | 判 |
|---|---|---|---|
| **V1 粗化** | witness 谓词回到旧外延（`return True`，所有台账行皆见证） | `2 failed, 38 passed`：`r3_absent_channel_may_not_carry_its_payload` + `r3_honest_absent_channels_are_not_killed` | **有牙**——不误杀方向被钉住 |
| **V2 细化** | 台账行全不算 witness（`return False`） | `2 failed, 38 passed`：`r3_absent…`（payload_row_count 与测试独立算术对不上）+ `r3_a_claimed_wall_ledger_row_alone_is_walls_payload` | **有牙**——claimed_wall-alone 载体被钉住 |
| **V3 回到历史缺陷形状** | `absent` 声明让路（`state not in ("present","absent")` 才红） | `2 failed, 38 passed`：主锁 + claimed_wall-alone 锁；**不误杀锁仍绿** | **有牙且方向正确** |
| **V4 收 ambiguous 进 witness** | `!= "non_wall"` | m2 单文件 `40 passed`；**m2+m3+m4 三文件 `91 passed`** | **无牙——全链存货 0**（N-1） |

两个要求的方向（粗化/细化）都有锁红；「回到历史缺陷形状」（V3）红得精确（只红第三方向锁，不误杀锁不红）。
绿不是恒绿、红不是恒红。⭐ V2 下主锁的红因 = `payload_row_count` 与**测试自己的算术**不一致——
逐成员判据确实在对账，不是成员列表非空。

### 3.2 存货盘点（对 40 条锁逐组合问「各自有没有被量到」）

| 通道状态组合 | 存货 | 出处 |
|---|---|---|
| walls present + witness 有 | 多 | 三个真实产物 + tiny + f1 |
| walls present + witness 无 + zero_payload debt | 1 | `r3_zero_payload_channel_exit_survives` |
| walls present + witness 无 + 无 debt（含满非墙台账形状） | 1 | f1 锁 + 本轮 §2.5 实测 |
| walls absent + 载荷照旧（claims 在） | 1 | `r3_absent…`（§一反例 1） |
| walls absent + 真空（台账也空） | 1 | `r3_honest…`（`_empty_artifact`） |
| walls absent + 满 non_wall 台账 | 1 | `r3_honest…`（`_all_non_wall_artifact`） |
| walls absent + 只有 claimed_wall 台账行（非 as-drawn 源） | 1 | `r3_a_claimed_wall_ledger_row_alone…` |
| walls 行被删 | 1 | `r3_a_deleted_channel_row…` |
| plan_openings absent + 载荷照旧 / present+空+debt / present+空+无 debt | 各 1 | §一反例 2 / f1 / b2 |
| 三条无成员通道 absent / present / 被点名 zero_payload debt | 各有 | 到处 / b2 / b2 |
| **walls absent + 满 ambiguous 台账（放行方向）** | **0** | **无锁**（本轮实测放行正确，见 §4 格③c） |
| **「ambiguous 不算 witness」这个判断本身** | **0** | **无锁**（V4 全绿 = N-1） |
| 非 walls 通道行被删 | 0（专门夹具） | 域循环同一段代码罩住（本轮格③d 实测），风险低 |

### 3.3 绿锚检查

`grep -n "assert .*passed\|validate_evidence_bundle"`：无 `assert <整份审计通过>` 式锚。
断言本体 = `_expect_error(…)` + ctx 逐字段，或 `evidence_contract._assert_channel_payload_closure(bundle)`
**本门直调**（`:1947/:1954/:1965/:1984`——绿锚锚在本锁自己负责的那一段，正确形态）；
`validate_evidence_bundle(art)` 裸调用只作「夹具自身合法」的绿前提。合格。

### 3.4 攻击面 3：三句自查（`_payload_row_witnesses` 为重点）

`_payload_row_witnesses` **是真逐成员**：per-(member, row) 谓词 + `_channel_witness_rows` 逐行走；
witness（`_channel_witness_rows`）与 source reach（`_channel_payload_rows` 全行）**有意分成两个函数**，
B-1 的宽 reach 没有被切掉。测量尺子在测试侧（`_R3_MEASURE` 自己算术，docstring 明言「⛔ Does not call
evidence_contract」）——③「拿来比的两个东西本来就该一样吗」：声明行 vs 独立测量，锚在 §4.2 处置语义上，
不是同义反复（V1/V2 变异下它红 = 有分辨力的证据；分辨力边界在 ambiguous 方向 = N-1）。
七条 R3 锁逐条过了三句自查，未发现把代理量放进承重位置的（`r3_every_payload_bearing…` 是规则锁非名单锁）。

---

## 4. 三格读数表（同一份包、同一脚本跨新旧代码）

| 格 | 输入 | 旧代码 `ba3303c^` | 新代码 `ba3303c`（=HEAD） |
|---|---|---|---|
| ① | §一形状：walls=absent+missing_channel debt，2 claims/4 dispositions 照旧 | **PASSED（缺陷在）** | — |
| ① | §一反例 2：plan_openings=absent，1 opening claim 照旧 | **PASSED（缺陷在）** | — |
| ② | 同一份包（与格①逐字段同构造） | — | `CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD`，ctx 点名 `channel/state/payload_rows=['face_dispositions','wall_claims']/payload_row_count=5` |
| ③a | **自造混合**：walls=absent+载荷照旧 **且** plan_openings=present+清空 opening_claims（同一包两个不一致） | — | 响亮：`CHANNEL_DECLARED_ABSENT_WITH_PAYLOAD`（walls 先到——域序 fail-fast，读数符合 CHANNELS 顺序；第二个错不报属正常单错停机） |
| ③b | **自造**：单动 plan_openings（walls 正常）present+空载荷无 debt | — | `PRESENT_CHANNEL_WITHOUT_PAYLOAD`（第一方向在混合包外独立可报） |
| ③c | **自造**：walls=absent + **满 ambiguous 台账**（4 行全 ambiguous，witness 自证 claims=0） | — | **PASSED（放行，正确）**——补上 V4 证明无锁的那个形状的当前读数 |
| ③d | **自造**：删 plan_openings 整行 | — | `CHANNEL_STATUS_MISSING`（域循环对非 walls 通道也罩住） |

neuter 对账（验收项 4）：neuter 整个 `validate_evidence_bundle` ⇒ **20 failed**（名单 = 旧 16 +
新 R3 4 条：`r3_absent / r3_a_deleted_channel_row / r3_a_claimed_wall_ledger_row_alone /
r3_a_mapped_member_without_a_source_rule`）——与派工单「16 → 20」逐数对上；单独 neuter
`_assert_channel_payload_closure` ⇒ 5 failed（f1 + b2 + 上述前 3 条）。新门确在生产校验器里。
其余 R3 锁（放行方向）在 neuter 下不红是结构必然，其分辨力由 V1（`r3_honest…` 红）证明。

定向基线：`m2 = 40 passed`；`m2+m3+m4 = 91 passed`；`m2+m3+m4+m56 = 164 passed`——与执行档读数逐数同。

---

## 5. 删除面（−50）逐处结论

| # | 删的是什么 | 去处 | 结论 |
|---|---|---|---|
| 1 | `_CHANNELS_WITH_PAYLOAD_MEMBERS = ("walls","plan_openings")` 常量+注释（~10 行） | `CHANNEL_PAYLOAD_MEMBERS` 显式表，键集等价；两个使用点改查表键 | **安全**（信息零丢失，且新增规则锁 `r3_every_payload_bearing…` 对账表 vs bundle 类型） |
| 2 | `_channel_has_payload` 两个手写分支 | `bool(_channel_witness_rows(...))` | **有行为变化，判为收紧而非丢失**（唯一变化面 = §2.5 的假 present 免登记，与 F-1 初衷一致）。附 N-2：该函数现已无调用者 |
| 3 | `_assert_channel_payload_closure` 旧循环头（`for status in …` + `if state != "present": continue` + 单向判定） | 域循环 + `rows_by_channel` + 双向对账 + `CHANNEL_STATUS_MISSING` | **本件目的所在**；被删的 early-continue 正是缺陷本体，多钉了「行存在」载体 |
| 4 | `_channel_payload_source_ids` 手写分支（~15 行） | 表派生 + `_payload_row_source_ids` per-member 规则 | **安全**（行为等价：source reach 仍全行；新增 `PAYLOAD_MEMBER_WITHOUT_SOURCE_RULE` 把「加成员忘教规则」从静默空集变响亮，有锁） |
| 5 | `_assert_channel_source_closure` / zero-payload 段的 `_CHANNELS_WITH_PAYLOAD_MEMBERS` 引用（2 行） | 改查 `CHANNEL_PAYLOAD_MEMBERS` | **安全**（等价替换；N-3 的 early-continue 是**保留未删**，非本件删除） |

删除面没有一处「服务的对外契约被丢」：成员归属保留在表里，present 方向的门收紧，absent 方向补上。
`content_sha256` 六份抽查三份（tiny / all_non_wall / legacy）在新旧代码下**逐份相同**（验收项 6 ✅）。

---

## 6. 复现命令 · 哨兵 · 状态

```
# 开工自检
git log --oneline -1            # → 8028bab ✅
git status --porcelain          # → 空 ✅
python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)"
                                # → /tmp/o22m2_review_glm/src/.../evidence_contract.py ✅（未串主树）

# 哨兵（两次）
开工: e7171c929a4f12339023618e6d34aa4726c60508ebba4a85e2dcd47162790619  ← ⚠️ 与单上 58f547fa… 不符，见 §7-①
交件前: 58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43  ← ⚠️ 复核期间被改回主树值，见 §7-①
# 开工时 .pth 内容 = "/tmp/o22m2_review_glm"（指向本 worktree，mtime 2026-09-01 14:09:16）

# 承重断言
git diff --stat ba3303c HEAD -- src/agent/correction/evidence_contract.py tests/test_o22m2_evidence_contract.py
# → 空（零 diff）✅

# 定向跑测（一律 -n 6）
python -m pytest tests/test_o22m2_evidence_contract.py -q -n 6                      # 40 passed
python -m pytest tests/test_o22m2_evidence_contract.py tests/test_o22m3_evidence_adapters.py \
   tests/test_o22m4_wall_compiler.py -q -n 6                                        # 91 passed
python -m pytest … tests/test_o22m56_decision_loop.py -q -n 6                       # 164 passed

# 变异 V1–V4 / neuter 单门 / neuter 整校验器 / 格①旧代码：正文各节已贴原文读数；
# 每次变异后均 `git checkout -- src/agent/correction/evidence_contract.py`（⛔ 从未 `checkout -- .`）
```

交件前 `git status --porcelain`：见本文件末尾附录（本 worktree 干净）。

---

## 7. 这份单子哪里写错了

1. **（B 层）哨兵在复核窗口内两头都不对**：单 §五 写「应为 `58f547fa…`，变了即停下上报」——开工实测
   `e7171c92…`（`.pth` 指向**我的 worktree**，主控 14:09:16 为本次复核所改，没回头更新单子里的值）；
   交件前又实测回 `58f547fa…`（复核中途被改回主树指向）。两头致命方向（串主树/串回主树）都不成立：
   `__file__` 开工与终读数均指向本 worktree，全部变异与跑测发生在本树代码上。但「变了即停」条款若被
   字面执行，这轮复核会在开工第一步白停——「单里⛔不写会漂的字段」（§6.5⑤-bis）的违例，且哨兵值
   在窗口内被第三方动过本身就是 2026-08-27 事故的同款形状（本轮方向无害，记录在案）。
2. **（B 层，措辞）攻击面 1 的「语义恰好相反」过强**：精确事实是**旧外延只在 present 方向生效过**
   （absent 方向旧代码什么都放行，本轮实测）；它的 present 方向效果 = 让假 present 免登记，与 F-1
   初衷相反。「旧代码把台账算作 walls 载荷」作为**契约陈述**不成立——它是一次只定了方向的顺手实现。
   （结论不受影响：单子要求「若不是契约 ⇒ 给证据」，§2.5 的双向实测就是证据。）
3. **（B 层）§一 读数「40 passed in 7.73s」**：本轮 4.19s 同为 40 passed——时间字段也是会漂的字段。
4. 其余（commit/文件/行号/机制描述/三格/验收项）逐条核过，无 A 层矛盾；未触发停报。

---

## 附：交件前终读数

```
$ git status --porcelain        # /tmp/o22m2_review_glm
（空）
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43   （开工时为 e7171c92…，复核中途被改回）
$ python -c "import src.agent.correction.evidence_contract as m; print(m.__file__)"
/tmp/o22m2_review_glm/src/agent/correction/evidence_contract.py     （终读数仍指向本 worktree，未串主树）
$ python -m pytest tests/test_o22m2_evidence_contract.py -q -n 6
40 passed in 4.15s                                                   （终态基线复跑）
```

建议（不阻断，供主控排期）：把 N-1 补成一条「absent + 满 ambiguous 台账必须放行」的锁 + 一条
「ambiguous 不入 witness 集」的规则锁（可用 V4 形状做夹具），一并挂进下一个动 `evidence_contract.py`
的单；N-2 的死函数在下次动该文件时顺带删除或给调用者。
