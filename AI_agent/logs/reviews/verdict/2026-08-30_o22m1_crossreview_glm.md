# 跨家族复核裁决书 · ②-2 模块 1：as-drawn v2 的生产者自己的类型

- **日期**：2026-08-30 · **审阅方**：GLM 家族（换人审）· **施工方**：Claude 家族
- **送审对象** = **`c0dcae1`** · **基线** = **`0cd2858`**（两提交：`bff77de` 本体 + `c0dcae1` 主控修的一处）
- **请求书**：[`../request/2026-08-30_o22m1_crossreview_glm.md`](../request/2026-08-30_o22m1_crossreview_glm.md) ·
  **派工单**：[`../request/2026-08-30_o22m1_as_drawn_producer_types_dispatch.md`](../request/2026-08-30_o22m1_as_drawn_producer_types_dispatch.md) ·
  **执行档**：[`../execution/2026-08-30_o22m1_producer_types_execution.md`](../execution/2026-08-30_o22m1_producer_types_execution.md)
- **实测环境**：全部实验在 `git archive c0dcae1 / bff77de / 0cd2858` 的 **/tmp 副本**上跑
  （模块哨兵断言 `__file__` 均指 /tmp 副本，变异只碰 /tmp）；**主树零写入**、零 `git add/commit`、
  零 `pip install -e .`；跑测一律 `-n 6`。唯一写入 = 本裁决书。

---

## 裁决：**APPROVE-WITH-FINDINGS**（阻断 0 · 不阻断 4）

本单的核心交付**逐条独立复现成立**：生产者出口真的过自己的类型（neuter 摘掉后**恰好只红
1 条**、232 passed，我复跑同读数）；产物逐字节不变（我用真实 `build()` 重跑 sm25_1f，
sha256 `2a563149…36c57` 与跟踪件**全等**）；detector 换类型判别且 15 种元素级破坏逐条
「旧规则说 yes」的前提**在 CI 里被断言**（复述规则与 `0cd2858:215-216` 原文逐字等价——
`_is_declared`=:120-121、`_has_keys`=:116-117，我核过）；受影响子集（宽口径 16 文件，
含 79 条 F-97、53 条本单新锁、诚实门）`-n 6` **391 passed / 0 failed**。

四条不阻断 findings 的共同形状：**行为全部站得住，但三条「承重叙述」有假**（extra=allow
的理由、strict 的 numpy 论证、空骨架挡路的成本账），外加一个**该进模块 2 派工单却零记录**
的错误类（引用完整性）。没有一条推翻交付本体。

---

## 〇、独立复现的总读数（全部 /tmp，主树零写入）

| 项 | 命令要点 | 读数 |
|---|---|---|
| 受影响子集（16 文件宽口径） | `-n 6 -q` @c0dcae1 副本 | **391 passed / 0 failed** |
| 本单新锁数 | `--collect-only` | **53**（与请求书 +53 一致） |
| 验收 2 逐字节 | 真实 `build(cfg_1f_full)` + `dump` | sha256 与跟踪件**全等**（`2a563149…`） |
| 验收 3 neuter | `assemble` 摘掉 `validate_as_drawn_plan` 后跑 10 文件 | **恰好 1 failed**（`test_assemble_refuses_to_emit_a_malformed_product`）/ 232 passed |
| F-152 边 | 两提交副本各跑 `build_edges` | 指向 `src/validator/checks/as_drawn.py` 的边 **bff77de=1（string-path，source=schema.py docstring）→ c0dcae1=0**；可达测试 **0** |
| 诚实门 | 同一测试两副本各跑 | **bff77de FAILED / c0dcae1 passed** |
| 缓做登记 | `grep plan.md` | `ledger`/`roles` 缓做**已登记**（`plan.md:96-97`，`bff77de` 即含）——执行档「请主控补登记」的口子已闭环 |

---

## 一、B1 / B2 / B3 —— 施工方自报最薄弱处（本审最重的一段）

### B1 ·「夹具带一条最小真实 face_lines + face_lines 必填」这条路：**通**

在 c0dcae1 的 /tmp 副本上完整走了一遍（不是推演）：

1. `schema.py` 的 `face_lines: list[FaceLineV2] = Field(default_factory=list)` 改为
   **必填无默认**（键必须在；空列表仍合法）；
2. `test_f97_vector_contract.py` 里 **8 处** `"observations": {}`（含 :629/:630 两处**故意残缺**
   的 malformed 夹具——它们因缺 `declarations`/`hypotheses` 依旧残缺）全部注入一条
   14 字段的最小真实面线（含 `gaps: []`、两条 run、区间钉长度 2）；
3. 跑两个文件：**79 条 F-97 全绿（130 passed）；唯二红 = 本单自己钉的两条 pin**
   （`test_the_declared_skeleton_is_still_recognised` 与自家的混合体测试）——都是「翻 pin」
   的预期红，不是「撞锁」；
4. 洞的读数：**裸骨架（缺键）→ UNKNOWN**，reason 响亮（"declares schema='as_drawn_plan_v2'
   but no registered contract has that value with a matching key set"）；
   **空列表 `{"face_lines": []}` → 仍是合法 `as_drawn_plan`**。

⇒ **「加了就会红」的红，红在 8 处夹具的最小合法载荷过时 + 2 条自家 pin，不在 F-97 的任何一条断言上。**
施工方报的「三处」实测为 **test_f97 里 6 处**（:134 裸骨架 · :155 裸骨架 · :284 / :305 / :415
三处混合体 · :640 的 R5 元组；:629/:630 故意残缺不计）**+ 本单自建 2 处**（:417 骨架 pin、:426 混合体）。
⇒ **B1 判定：路通，成本 = 8 处机械修改 + 翻 1 条自钉 pin，F-97 断言零变动。**
挡住它的不是技术，是「F-97 是别人承重的锁、本单不该顺手改」的边界——这个边界感本身是对的
（孤儿件的前车之鉴），但正确动作是**把这条路的实测账交上来**（成本几处、断言动不动），
而不是把「通不通」作为开放问题留给复核方。（→ NF-1）

### B2 · 空产物该判什么：**拆成两种形态，答案相反**

- **缺键形态** `{"observations": {}}`：`assemble` 的返回字典**无条件**产出 `face_lines` 键
  （`as_drawn_v2.py:599`）⇒ 缺键产物**生产者造不出来**，只可能是手造或损坏 ⇒
  **这一层该管**——它正是派工单 §一.2 立单理由（「声明了 schema 但结构不符 ⇒ 静默当合法」）
  的残余半格。**立单理由在这半格上仍然成立**。
- **空列表形态** `{"face_lines": []}`：诚实读图在一张空图/废图上就会产出它 ⇒
  **这一层不该管**。管了就是把结构校验冒充内容判断，会把「诚实的零测量」判成「不合法」。
  「量到零」是内容事实，归宿在判分（0 分）与 11 道门里的 zero-wall 段
  （`check_pair_reconciliation`，`as_drawn.py:608-612`，未接线）。
- detector 是**路由层**：空列表产物**应该**仍路由成 `as_drawn_plan`（账面记「as-drawn 计划、零面线」，
  让判分去打零分），缺键产物路由成 UNKNOWN 更诚实。当前实现把两者都当合法产物 ⇒
  前一半是缺陷（NF-1），后一半是对的。

### B3 · F-97 那几处夹具为什么能用零面线骨架：**它们量的全是路由，不是内容**

六处分头量的是：disposition 路由（:129 KNOWN_NOT_CONSUMED）· correction 的报错路径
（:144 "no wire for it" vs "unknown"）· 双匹配的 AMBIGUOUS 解析（:281/:298/:410/:707 四处）。
**没有一条断言关心「空」**；它们骑在骨架上，只因立案当时那就是最小合法载荷。
本单把「最小合法载荷」的定义从键形改成了类型，夹具的载荷没跟着改 ⇒
**红的是载荷过时，不是锁的逻辑，更不是「缺陷本身在挡锁」**。
⇒ B3 判定：**「若它们本就该带面线」的「该」不成立——不带面线并无设计上的正当性，只是历史最小值。**
正确收口 = 一张微单：8 处载荷 + 翻 1 条 pin，断言零变动（本审已代跑通，上表读数可直接引用）。

---

## 二、A1–A5

### A1 · 顶层 `extra="allow"`：**行为站得住，承重理由是错的**

隔离实测（/tmp，只把顶层 `allow→forbid`，喂**结构合法**的混合体 = 真面线 + `strokes`）：

```
classify → contract_id=unknown · disposition=None · reason="declares schema='as_drawn_plan_v2'
           but matches no registered contract's key set, … malformed declaration …"
是否 CONSUME：False
```

挡住 CONSUME 的是 **BLK-A**（`vector_contract.py:316`：「唯一 legacy 匹配 且 `"schema" in raw`
⇒ UNKNOWN」，恰恰为本单范围外那次 R5 修复立的），**与 extra 设置无关**。而施工方**自己的**
`test_a_type_failure_never_downgrades_a_file_into_being_consumed`（测试 :435-445）就在证明
同一件事——同一文件里两个 docstring 互相矛盾。
forbid 的**真实**代价 = R5 锁要求的「真双匹配必须报 AMBIGUOUS」掉成「malformed declaration」——
**是报告区分度的损失，不是 F-97 的消费实害**。AMBIGUOUS 的语义 = 两个 detector 都说 yes；
as-drawn detector 要对混合体说 yes 就必须容忍多余键 ⇒ 在「只许改判别方式」的本单范围内，
`extra="allow"` 是被 R5 逼出来的唯一解；请求书问的「第三条路」（classify 层对
「声明了注册值 + legacy 结构」单独报冲突）= 路由层手术，属模块 7 收窄，⛔ 本单不做是对的。
⇒ 判定：**行为 ✅、理由 ❌**（三处同错：`schema.py:339`「would drop to a single legacy match
and be **consumed** -- F-97 reopened」、测试 :423-425、执行档 :234）。（→ NF-2）

### A2 · strict=True 的 numpy 论证：**两端皆错**

实测矩阵（真实 `sm25_2f` 基底 + `_plan_ink.dump` 真身）：

| 标量 | strict 校验端 | `dump` 序列化端（`default=lambda o: o.__dict__`） |
|---|---|---|
| `np.float64` | **放行**（float 子类，isinstance 即过） | **原样写出 `0.24`**（stdlib json 原生走 float 分支，`default` 根本不触发） |
| `np.int64` | 拒绝（响亮，loc 指名 `gaps.0.len_px`） | 若到 dump：`AttributeError: 'numpy.int64' object has no '__dict__'` **响亮崩** |

执行档 :318-319 的两个断言（「strict 会直接红」「dump 会把 numpy 标量写成垃圾」）
**没有一个成立**：float64 两端静默通过且字节正确；int64 是响亮拒/响亮崩，
「静默写垃圾」的形态根本不存在（**numpy 标量没有 `__dict__`**）。
⇒ 判定：strict 的既得收益**不依赖这个论证**（`spacing_m` 以文本到达翻红=「载体被换掉」那格，
实测在案），**保留 strict ✅**；但「这是不是一个人的判断」的答案 = **这个判断本身错了，
且错在想象出一个不存在的防护收益**。（→ NF-3）

### A3 · `test_the_fifth_slot_is_pairs_measured_on_the_real_products`：**有牙，双向**

- **roster 方向**：从 `FACE_DISPOSITION_BUCKETS` 摘掉 `non_wall_face_lines` ⇒ fifth_slot 在
  sm25_1f/sm25_2f 两个参数上红 + 四桶计数锁红（sm24_1f 不红——该产物此桶为空，如实记）；
- **数据方向**：从 sm25_2f 夹具删掉一对 pair（L002↔L003）⇒ 该产物参数红
  （两张面落在五格之外）。
- 「什么产物上会红」的完整清单：`pairs_status != "SELECTED"` / 有面线落在五格之外 /
  四桶单独已覆盖全部（无法证明 pairs 必需）——任一触发即红。
⇒ 判定：**有牙**。逐产物数据锁 + roster 锁的双向锁；新产物进 `_TRACKED` 自动被量。
施工方担心的「依赖 SELECTED」恰是牙的一半：换状态的产品无法静默骑上完备性前提。

### A4 · 自造第 16 种破坏：**引用完整性 / 身份唯一性——15 条一条都盖不住，类型也盖不住**

五种「结构合法但语义假」（全部以真实 sm25_2f 为基底、逐项实测）：

| 破坏 | 类型 | detector |
|---|---|---|
| `pairs[0].face_b` → `"L999"`（悬空引用） | PASS | `as_drawn_plan / KNOWN_NOT_CONSUMED` |
| `non_wall_face_lines["L999"]`（桶键悬空） | PASS | 同上 |
| 两条面线同 `id`（身份重复） | PASS | 同上 |
| `opening_candidates[0].gap_index = 99`（越界） | PASS | 同上 |
| `pair_candidates[0].face_b` → `"L999"` | PASS | 同上 |

现有防线盘点：11 道未接线门里只有 `check_pair_reconciliation` 接得住其中 **1 种**
（pairs 悬空，`as_drawn.py:556-558`）；**桶键悬空被 accounted 并集静默吸收**
（:584-586 只查 `faces − accounted` 一个方向）；`pair_candidates` 完全不被 reconcile；
**重复 id 连未接线门都不管**（:775 的 `duplicate_face` 是变异**生成器**不是门）。
而 11 门本身未接线（`rules.yaml:44` 诚实条目；本审复核**能到达它的测试 = 0**）。
⇒ 这一类正是新分工要加载的：pairs → correction → 墙编译，**悬空 face_b = 在不存在的一面上
造墙 = 幻觉墙病族**（②-1a「确定性 DXF 上 33 条虚构墙」同族）。设计稿把 pointer 纪律划给
模块 2（EvidenceContract 的 `ObservationRefV1` 回指，设计稿 §4.1 表），模块边界可辩；
但本单对 N-1 有 pin 有 handoff，**对这一类零记录零 pin**。（→ NF-4）

### A5 · 类型今天的真实流量：**管线侧零，生产者出口非零；属「没跑到那一段」**

- `pipeline.py:367/370` 两句 wall-centerline 逐字在（实测读行）；全表 `CONSUME` 仅 legacy
  一项（本单测试钉住）；全仓 `as_drawn_plan_v2` 的 JSON **只存在于 `AI_agent/logs/` 下**
  （grep 实测）⇒ **detector 在生产管线里今天零真实流量**。
- 按 [[two-kinds-of-latency]] 分类：**「没跑到那一段」，不是「没尺子量」**——尺子在且在跑：
  53 把锁今日全数执行（collect 53 + 受影响子集 391 绿），生产者出口校验有真实流量
  （`build()` 重跑逐字节复现，neuter 证明摘得动且恰好只红 1 条）。
- **「接线那天，53 把锁里第一次真正执行的 = 0 把**——它们是单元锁，可达性不因接线改变；
  接线改变的是 detector 的生产流量（从零起步）。这一层的今日实际收益 = **生产者出口铁闸**
  （残废产物出不了 `build`）；ledger 判读收益今天为零（没有生产产物可判）。

---

## 三、两个是非题

**1 · `c0dcae1` 是不是把红压绿？——不是，是把假事实撤掉。** 四点实测：
① 指向 `src/validator/checks/as_drawn.py` 的依赖边 **bff77de=1**（string-path，source 就是
schema.py 那句 docstring）**→ c0dcae1=0**；② 同一道诚实门 **bff77de FAILED / c0dcae1 passed**
（同命令、各自 /tmp 副本）；③ `c0dcae1` 只动 `schema.py` docstring（+11/-1）与三份 md，
**没碰门、没碰 `uncovered_allowlist`（`rules.yaml:44` 条目仍在）、没碰 `affected_tests.py`**；
④ 可达性复核 = **0 个测试**（「真·无人测试」为真，allowlist 条目诚实）。
bff77de 上的红 = 门**正确地**抓到「一句散文制造假覆盖」；修法 = 删掉假覆盖、恢复真话。
「把前缀加回去就再红」由 bff77de 那次 FAILED 本身证明（它就是带前缀的版本）——门仍然武装。
若当初选的是「从 allowlist 删条目、把假覆盖当既成事实」，那才是压红；实测排除。
类级缺陷 F-152 未修（已登记 plan.md、请求书 §五明示不在本单）。

**2 · N-1 第六态有没有按设计稿落地？——落了，且落法正确。**
设计稿 `:517`「`AsDrawnPlanV2` 覆盖当前 sm25 1F/2F、sm24 1F 三份产物；生产者经模型出口，
现有字段与语义不变」+ `:77`「先忠实接住当前 `dict[face_id, reason_text]`，不要趁建模偷偷
重写历史产物」——三份产物（含 L012 载体 sm25_2f）全部过型（`test_every_tracked_product_validates`）；
桶以 prose 入型；L012 被 `test_n1_the_sixth_counterface_state_exists_only_as_prose_today`
钉住，**且带反向锁**（换成结构 dict 今天必被类型拒绝——哪天生产者在那里出结构，类型必须被
有意地改）。第六态的**结构化解**（加第三值 / 像素通道显式检查）设计稿 `:143` 划给模块 2 的
`counterface_state`——本单不发明槽位正是「零实例 union 分支是缺陷藏身处」的项目口径，
且 handoff 那句「模块 2 ⛔ 不能解析散文」已写进执行档 §五。**不是漏项。**

---

## Findings

### 阻断（0 条）

无。派工单 7 条验收逐条独立复现通过（1 有牙且前提被 CI 断言 · 2 逐字节三方全等 ·
3 neuter 摘得动且恰好只红 1 条 · 4 四桶裁定依据成立且被两条测试钉住 · 5 缓做清单 13 项
与模型互为充要 + plan.md 登记已闭环 · 6 disposition 未动 · 7 受影响子集 391 绿）。

### 不阻断（4 条）

| # | 现象 → 我的复现 | 影响 | 建议方向 |
|---|---|---|---|
| **NF-1** ⭐ | **缺键空骨架仍被认成合法产物**：`{"schema":…,"observations":{},…}` 改动前后都绿、今天仍 `as_drawn_plan`。B1 实测**这条路通**：face_lines 必填 + 8 处夹具注入真实面线 ⇒ **79 条 F-97 全绿**（130 passed），唯二红是本单自家两条 pin；裸骨架翻成响亮 UNKNOWN。生产者无条件产出该键（`as_drawn_v2.py:599`）⇒ 缺键形态生产者造不出。⚠️ 施工方报「三处」，实为 **test_f97 6 处 + 本单自建 2 处** | 派工单 §一.2 的立单理由（「声明了 schema 但结构不符 ⇒ 静默当合法」）在这半格仍成立；但 `KNOWN_NOT_CONSUMED` 无消费面，实害=账面把伪造品记成良品 | **微单一张开**：8 处载荷 + 翻 1 条自钉 pin，断言零变动（本审读数可直接当施工依据）。空列表形态**不要**在类型层拒——那半格该留给判分/zero-wall 门 |
| **NF-2** | **`extra="allow"` 的承重理由是假的**：施工方称 forbid 会让混合体「掉成单一 legacy 匹配被 **CONSUME**——F-97 重开」。实测 forbid 下结构合法混合体 → **UNKNOWN / disposition=None，非 CONSUME**（BLK-A `vector_contract.py:316` 挡住，与本单自家测试 :435-445 证明的同一件事）。forbid 的真实代价只是 R5 要求的 AMBIGUOUS 报告掉成 malformed | 三处错误叙述进树（`schema.py:339`、测试 :423-425、执行档 :234）——未来任何收紧决策若引用它，会在一个不存在的风险上让步 | 改三处叙述为「forbid ⇒ 混合体从 AMBIGUOUS 掉成 malformed-UNKNOWN（BLK-A 兜底不 CONSUME），破坏的是 R5 的双匹配报告锁」；行为不动 |
| **NF-3** | **strict 的 numpy 论证两端皆错**：`np.float64` 是 float 子类 ⇒ strict **放行**、dump 原样写出正确数字；`np.int64` 校验端响亮拒、dump 端 `AttributeError`（numpy 标量无 `__dict__`）响亮崩——「写成垃圾」的形态不存在（执行档 :318-319） | 记录性错误；strict 的真实收益（spacing 文本翻红）不受影响 | 更正执行档与后续引用；若真想堵 float64 通道，需在类型层显式拒子类（pydantic `strict` 不做这件事）——先判断值不值得 |
| **NF-4** ⭐ | **引用完整性/身份唯一性这一类错误，15 条破坏 + 类型 + detector 全盖不住**（5 种实测全过，见 §二.A4 表）；唯一能接住 1 种的 `check_pair_reconciliation` 未接线；桶键悬空被 accounted 并集**静默吸收**、`pair_candidates` 无人 reconcile、重复 id 连门都不管 | 新分工的加载面：pairs → 墙编译，悬空 face_b = 幻觉墙病族（②-1a 同族）；今天零流量，接线日若仍无锁则**静默** | **显式写进模块 2 派工单**（EvidenceContract 的 ref 回指 + 解引用失败处置），并给本模块补一条「引用完整性=已知不设防」的 pin（对齐 N-1 的处理方式），⛔ 不要留成两份文档缝里没人派的活 |

### 复核为「成立」的事项（非 finding，记录在案）

- A3 fifth_slot 双向有牙（roster 摘桶红 2 产物参数 + 计数锁；夹具删一对 pair 红该参数）。
- 执行档的「三份产物 sha256 三方全等」我以其中一份独立重建复核（全等）；另两份未重跑（同构流程，风险低）。
- F-97 测试文件在 `0cd2858..c0dcae1` 零改动（numstat 无该文件）。
- 施工方承重前提自检的三条（detector 旧规则原文 / 11 门未接线 / 全仓无生产 as-drawn 产物）逐条复核为真。
- 「五桶=四桶+pairs」的裁定：三处依据（`select_pairs` 只读四桶 · `as_drawn.py:576-583` 点名同样四个 · 三份产物实测）我抽查第二、三处成立；第五格=pairs 的论证与 `reading_grade.py:121-124` 的并集口径一致，无重复计数。

---

## 方法论备注

- **「答案若是『加了就会红』，那是缺陷本身在挡锁」——本轮的落点**：实测答案是
  「红的是 8 处过时的最小载荷 + 2 条自家 pin，**不是任何断言**」⇒ 缺陷没有在挡锁，
  挡锁的是「别人的锁文件不该本单顺手改」的**流程边界**。施工方自我举报的方向对，
  但把「通不通」留成开放问题、并把成本低估为「三处」——量一遍只要十分钟。
- **承重叙述与行为分离审**：本单四条 finding 有三条是「行为对、理由错」。这类错的实害
  不在当下而在未来——下一个收紧/放宽决策引用这些理由时，会在不存在的风险上让步
  （A1 的「forbid ⇒ CONSUME」若被当成事实，顶层永远不敢重审）。
- **第 16 种破坏的选取**：没有造它已想到的畸形键，选了「引用完整性」——因为新分工下
  这一类直达墙编译（幻觉墙病族），且实测五连穿。F-149 的教训（复核方自挑的探针也可能
  推不动）同样适用于我：本审的五个探针全部实际穿过（type PASS + detector 判良品），非推演。

## 可复现命令（全部 /tmp，主树零写入）

```bash
# 副本与哨兵
for c in 0cd2858 bff77de c0dcae1; do mkdir -p /tmp/rv_$c && git -C /workspaces/EnergyPlus-Agent-dev archive $c | tar -x -C /tmp/rv_$c; done
python3 -c "import sys; sys.path.insert(0,'/tmp/rv_c0dcae1'); import src.agent.reading.as_drawn.schema as s; assert s.__file__.startswith('/tmp')"

# 受影响子集（16 文件,-n 6）
cd /tmp/rv_c0dcae1 && python3 -m pytest tests/test_a8_evidence_routing.py tests/test_audit_remediation_accepted_inputs.py \
  tests/test_check_parity.py tests/test_e2e_break_r2_locks.py tests/test_f7_observation_reference_translation.py \
  tests/test_f97_vector_contract.py tests/test_f9_route2_s0_raw_contract.py tests/test_f9_route2_s2_authoritative_projector.py \
  tests/test_f9_window_host_crash.py tests/test_mep_hvac_deterministic.py tests/test_o22m1_as_drawn_producer_types.py \
  tests/test_pipeline_evidence_debt_import.py tests/test_run_pipeline_self_checks.py tests/test_as_drawn_denominator_f126.py \
  tests/test_gt_revisions_and_as_signed.py tests/test_affected_tests_map.py -n 6 -q
# → 391 passed

# B1：face_lines 必填 + 8 处夹具注入真实面线（脚本见裁决 §一；要点）
#   schema.py: 'face_lines: list[FaceLineV2] = Field(default_factory=list)' → 'face_lines: list[FaceLineV2]'
#   test_f97: '"observations": {}' → '"observations": {"face_lines": [<14 字段真实面线>]}'（8 处）
#   → test_f97 79 全绿 / 130 passed；唯二红 = 本单两条自钉 pin；裸骨架 → UNKNOWN

# A1：顶层 extra allow→forbid 后分类结构合法混合体
#   → contract_id=unknown, disposition=None（非 CONSUME），reason=malformed declaration（BLK-A）

# A2：np.float64 → spacing_m：type PASS；dump 写出 0.24（default 不触发）
#     np.int64 → len_px：type REJECT；json.dumps 原生 TypeError + default 下 AttributeError

# A4：五探针（悬空 face_b / 悬空桶键 / 重复 id / gap_index=99 / candidate 悬空）→ 全部 type PASS + detector=as_drawn_plan

# 是非题1：边与门
for d in /tmp/rv_bff77de /tmp/rv_c0dcae1; do cd $d && python3 -c "
import sys; sys.path.insert(0,'$d')
from scripts.tool_scripts.affected_tests import first_class_files, build_edges
e = build_edges(first_class_files())
print('$d edges into target:', len([x for x in e if x.target=='src/validator/checks/as_drawn.py']))"; done
# → 1 → 0；pytest tests/test_affected_tests_map.py::test_every_production_module_is_mapped_or_honestly_allowlisted
#    bff77de FAILED / c0dcae1 passed；rules.yaml:44 条目仍在

# 验收2 逐字节：真实 build() 重跑
cd /tmp/rv_c0dcae1 && python3 -c "
import sys, json, hashlib; sys.path.insert(0,'.')
import src.agent.reading.as_drawn.as_drawn_v2 as A
from src.agent.reading.as_drawn._plan_ink import dump
dump(A.build(json.load(open('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/cfg_1f_full.json'))),'/tmp/rb.json')
print(hashlib.sha256(open('/tmp/rb.json','rb').read()).hexdigest() == hashlib.sha256(open('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_1f_v2.json','rb').read()).hexdigest())"
# → True
```

—— GLM 跨家族审阅席位 · 2026-08-30
