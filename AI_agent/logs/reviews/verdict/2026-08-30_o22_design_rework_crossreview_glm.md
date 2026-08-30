# 返工复审裁决书 · ②-2 设计稿（B-1 修法是否堵住了「这类缺陷」）

- **日期**：2026-08-30 · **审阅方**：GLM 家族（交换审，同上一轮 REWORK 的审阅方）· **返工方**：GPT 家族
- **送审对象**：[`2026-08-30_o22_evidence_contract_gpt_design.md`](2026-08-30_o22_evidence_contract_gpt_design.md) 返工版（479 → 631 行，`+180/-28`）
- **基线**：`54e3633`。全部实测在 `git archive 54e3633` 的 **/tmp/o22_r2 副本**上跑（含模块哨兵断言
  `schema/vector_contract.__file__` 均指 /tmp 副本）；旧稿取自 `git show 88ea056:<同路径>`。
  **主树零写入、零 pytest**（本单对象是一份 `.md`，无产品代码改动，跑测试群证明不了任何事）；
  主树 `git status` 的脏 = 另一席位 ②-1d 在途改动，未读成异常。
- **请求书**：[`../request/2026-08-30_o22_design_rework_crossreview_glm.md`](../request/2026-08-30_o22_design_rework_crossreview_glm.md)

---

## 裁决：**APPROVE-WITH-FINDINGS**（阻断 0 · 不阻断 7）

**B-1 的修法是真的堵住了「这类缺陷」，不只是那个例子**：§4.4 #9 两半逐字落稿（`:183`），
§6.1 新增执行优先序句（`:369-370`）把上一轮「两行无优先序」的病根直接收口，
自动执行行加了「未进入过 open_items」前置与「不得回收已开项」双限定（`:363`），
开项行加了「即使后续筛成唯一或 Pareto 支配也仍需显式决定」（`:365`），§5.2 legacy 行同步（`:209`），
§9.2 落了两条反证测试（f9 形状 `:541` + W01 形状 `:542`，均写明夹具与断言，可执行）。

**换同形输入的实测**（返工审第三条，本单核心）：稿子自给的 W01 形状我复核成立且被堵死；
我又自找了**两个它没想到的同形输入**——①全仓 **178 条**「unknown + 厚度只在 callout 里」的真实墙
（sm21 anchor 各 run，dimension_refs 挂 0.25/0.36/0.4 墙厚值、自身 thickness_m=null），
②sm25 2F 真实 single_face **L012**（counterface **墨迹在、被 reader 丢了**，F-86）——
两者按新稿逐门推演**都走不通静默中线**（identity 被 #9 前半挡在候选门外；unknown 必开项；
开项后 #9 后半挡唯一候选/Pareto）。②同时暴露 `counterface_state` 两值枚举盖不住的**第六种真实状态**
（→ N-1，不阻断）。

NF-1～NF-9 九条全部在稿、无沉默跳过（§11.1 逐条处置表 + plan.md:96-97 实际登记核验）；
本轮新数全部指得到产物与 `file:line`（含 W01 双锚点 #L19/#L29 **两处都中**）。
7 条不阻断全部是「施工必钉/补一句话」级，无一条推翻设计主体。

对四个攻击面（A1–A4）的问法本身：**无一问错**，本轮不需要修正提问。

---

## 一、返工审三条逐条（§一）

### ① 旧稿上复现得出 ✅

`git show 88ea056:...gpt_design.md`：

- 旧稿 §4.4 硬不变量**恰好 8 条**（旧 `:162-173`），无 identity 排除、无开项保护；
- 旧 §6.1（旧 `:307/308/310`）：「硬约束筛后只剩一个候选…⇒ 自动执行并记账」与
  「legacy basis unknown ⇒ 进入 open_items」两行**无优先序、无「未开项」限定**；
  旧 §5.2 只禁「因 correction prompt 曾要求中线」这一个理由（旧 `:199`）。

⇒ f9 形状（候选集自然实现为 {identity}）在旧稿字面照走 B-1：外皮线静默当中线、账面合规。**①成立。**

### ② 新稿上复现不出 ✅（这条路关死了）

| 门 | 新稿位置 | 实测 |
|---|---|---|
| §4.4 #9 前半（identity 不入候选集） | `:183` | 逐字 = 返工单验收 1 的第一半 ✅ |
| §4.4 #9 后半（已开项不受唯一候选/Pareto 管辖） | `:183` | 逐字 = 第二半 ✅ |
| 执行优先序句（完整性门 → #9 候选门 → 判开项 → 仅对**从未开项**用自动规则） | `:369-370` | 上一轮病根（两行无优先序）直接收口 ✅ |
| 自动执行行双限定（「未进入过 open_items」前置 + 「不得用于回收已开项」） | `:363` | ✅ |
| 开项行（unknown 先开项；**即使后续筛成唯一或 Pareto 支配也仍需显式决定/再感知**） | `:365` | ✅ |
| §5.2 legacy 行（unknown 必开项；**无论有无 thickness_m** 都先按 #9 排 identity） | `:209` | ✅ |
| §9.2 反证 ×2（f9 形状 + W01 形状，各写夹具与断言） | `:541/:542` | 可执行，不是只写测试名 ✅ |

### ③ 换同形输入仍走不通 ✅（两条自选，均为真实产物、非合成）

**复核稿子自给的 W01**（`sm25-L_anchor/run_2026-08-22_orchestrator_handson_H1/0_reading/1f_view.json`）：
`thickness_m=0.239`、geometry 键仅 `kind/p1/p2/thickness_m`（无 basis）✅；
`ReadingView.model_validate` + `_detect_legacy_reading_view` 在 /tmp 副本（哨兵断言通过）**都收下** ✅。
⭐ 我加量的几何事实：W01 笔画 x=0.119，恰为 note 自报墨带 px281.5/292.5 换算出的
[−0.0068, 0.2312] 的**正中**——这个方言是「中线笔画+带厚度」，而 note 自称
「face line **(centreline)** of the wall band」（**一笔画内自相矛盾**，比 f9 的跨笔画矛盾更狠），
且几何真值（线在带中心）只存在于 note 与像素里、结构化面上一无所有——
identity 在这里碰巧会给出对的答案，这正是静默腿最危险的形态；
新稿仍强制它走「开项 → 墙级再感知 → 类型化 basis → 显式 centerline 行（§6.1）」，
结果同、但每一步有据。**堵死 ✅**

**自选同形输入 #1：unknown + 厚度只在 callout（全仓 178 条真实墙）。**
f9 是「四条 ref 全长度链、无 t 可用」，W01 是「厚度在笔画上」；第三种真实形状是
**厚度不在笔画上、在 dimension_refs 里**——`basis` 键无 + `thickness_m=null` +
refs 挂着 0.09–0.5 m 的真墙厚 callout（例：`sm21_anchor/run_2026-07-07_haiku_cv_retest/1f_view.json`
S4←D24/D26=0.25、S8←D15=0.36；`run_2026-07-01_sonnet_e2e_r2/2f_view.json` S5←D_L3=0.4）。
逐门推演：adapter → `legacy_wall_trace(unknown)`（§8.3 禁解析 note）→ #9 前半删 identity →
§5.2 unknown 必开项 → callout 厚度只构成 `OFFSET_±/SNAP_TO_DECLARATION` 类符号候选，
方向仍无据 → 即便硬约束把四个候选筛剩一个，#9 后半挡住自动执行 →
终点只能是显式决定/墙级再感知/degraded 带债/`unsupported_or_reperceive`。**走不通 ✅**

**自选同形输入 #2：sm25 2F 真实 single_face L012 —— 第六种 counterface 状态。**
`sm25_2f_v2.json` 的 `unpaired_wall_faces.L012`（x=9.15 隔墙，真实 single_face），
其 reason 原文：*"IS a wall face … but its other face is missing from the observations.
**The ink is there — column 655 carries 170 px over rows 1080-1249** — and the reader dropped it
（F-86 列组均值缺陷）"*. 即 counterface **被观测过（墨在）、但没被提升为 face line**：
`not_in_observations` 字面为真（确实不在 observations 里）而「未观测到」为假；
`observed_unclaimed` 又要求一个不存在的 observation 节点 pointer——**两值枚举哪个都装不下**（→ N-1）。
静默中线路径本身：single_face 无 centerline 证据 → #9 前半同样删 identity → side/thickness 多解开项 →
#9 后半挡唯一化。**走不通 ✅**（但 packet 会拿一个失真的状态喂决定模型）。

顺带对账请求书给过的另两个候选方向（已查、非跳过）：「同墙两端 note 打架」与
「unknown + 多值厚度打架」在全仓**均为 0 例**（同轴近距配对扫描 + 单笔画 refs 冲突扫描），
今天只能是合成形状，未采用。

---

## 二、A1 · #9 后半的接线（有没有第三条绕开 open_items 的路）

**主结论：接线成立。**「进 open_items」与「自动执行」从两处无序文字变成一句显式优先序 +
行内双限定，上一轮的病因（两行无优先序）不因换了位置而残留。**但用同一把刀反查「哪个方向没锁」，
找到两处同病族的 letter-gap（均不阻断）**：

1. **§6.1 的「已签规则」自动行不在优先序句里，也不受 #9 后半字面管辖**（N-2）。
   优先序句（`:369`）只序了「唯一候选/Pareto」这一条规则；而自动表里还有第三条自动路
   「已签规则唯一决定的数值闭合、同墙连续段接缝 ⇒ 自动；规则 id 必须入账」（`:364`）。
   #9 后半的原文只豁免『只剩一个候选 / Pareto 支配 ⇒ 自动执行』。该行的自然辖域是数值闭合
   （§5.3 厚度解析），且 §5.2 明写 unknown 必须先开项，所以照稿施工的**自然**实现不会拿它造中线；
   但「两行无优先序」正是上一轮的阻断形状，这次返工自己立的优先序句漏序了这第三行。
   一句话可收口（该行同样不得用于化解已开项 item / 不得产出任何 basis 决定）。
2. **成功判定缺「开项闭环」不变量**（N-3）。§6.3 成功条件（`:420`）是
   「无 **blocking** open item + … + 无 strict 不允许的 residual debt」——
   谁判 blocking、未决 item 若被判非 blocking 后落在哪里，稿面没有不变量绑死
   （`CorrectionResolvedV1.residual_evidence_debts[]` 有槽，但没有任何一句
   「成功时 open_items ⊆ 已决 ∪ 债 ∪ 再感知清单」）。字面上，一个被模型忽略的 unknown
   item 可以既不决定、也不进债、成功照发——与 B-1 同族（状态边界未闭合）。
   自然实现（未决 ⇒ blocking ⇒ 循环到预算耗尽响亮退出，§6.3 末句有此路）会走对，
   故不阻断；施工单补一句不变量 + 一条反证测试即可。

其余第三路候选逐一排除：候选集为空 → `unsupported_or_reperceive`（`:367`）；
legacy `pen==wall` 一律单产 `legacy_wall_trace`（§8.3），无 pair 通道；
`non_wall`/中分线两自动行的触发条件各自带结构性前提，不依赖开项状态。

## 三、A2 · 自报最薄弱处判对了没有

**判对了，且定性准确**。residual debt 从 `CorrectionResolvedV1` 经 envelope 落到 attempt/report
确实是全稿最薄的一环：`correction_score.py` 不读 degraded/conflicts 是我上一轮的实测，
本稿 §5.4 把落点定义到了 schema（`CorrectedGeometryProjectionEnvelopeV1`：completion/debt ids/
双 hash）与失败语义（丢 envelope、hash 对不上、debt 不闭合 ⇒ 投影失败，不得把裸 geometry
当完整产物），strict 前置阻断 / exploratory 照跑但报告 degraded 且不缩分母。

**「设计缺口」还是「施工必钉」**：**施工必钉为主，但有一处真设计缺口**——
§9.2 十六行测试里**没有一行**打这个它自己点名的最薄弱处（§十三自己出的第二问
「抽裸 CorrectedGeometry 去跑 judge，attempt/report 会不会响亮失败」没有对应测试行）。
上一轮 B-1 的教训正是「adapter 层有测试、executor 层零覆盖」；这里同型：
envelope 有 schema、**消费侧零测试**（→ N-4，补两行：strict 拒 degraded 裸 geometry、
envelope 缺失/hash 不闭合响亮失败）。其余（runner 接线、报告面显示）归施工单。

## 四、A3 · NF-1～NF-9 机械对账（无沉默跳过）

| # | 稿面落点 | 实核 |
|---|---|---|
| NF-1 | §9.4 旧 case 行重写：明写「今天没有可验的显式 centerline 存量子集：1240/1240 unknown、basis 键 0」+ strict/exploratory 两档终点 + **点名 sm21 零 as-drawn** +「两档都不得宣称兼容且不下降」 | ✅（`:566`；「显式 centerline fixture 保持兼容」的空集承诺已删） |
| NF-2 | §7.3 墙级带锚点定向再感知 + `O(unknown 墙数)` + note 的「代码禁解析 ≠ 模型不可见（untrusted_context）」边界 | ✅（`:443-457`） |
| NF-3 | §4.1 表新增「几何角色已知？」列 + 表下文字 | ✅（`:139-146`） |
| NF-4 | `counterface_state` 扩 `observed_unclaimed`（带原节点+disposition 引用） | ✅（`:143`）——但见 N-1：真实存量里还有它盖不住的第六态 |
| NF-5 | §5.4 envelope + attempt/report 消费 + 失败语义 | ✅（`:286-301`）——测试行缺失见 N-4 |
| NF-6 | §6.2 `requested_effect.kind` 封闭枚举五值 + 消费规则 | ✅（`:393-404`）——表达力对账见 N-6 |
| NF-7 | §9.1/§十 最小集=模块 1–6+一行注册；收窄工程登记 plan | ✅（`plan.md:96-97` 主树基线实核，登记真实存在） |
| NF-8 | `output_basis` 机械复用判分侧 `wall_axis\|outer_skin`，`centerline/wall_face/unknown` 不得作为 output_basis 出现在下游 | ✅（`:281-284`；`answer_compiler.py:110` @54e3633 实测即该 Literal） |
| NF-9 | 锚点修到 `schema.py:49`；`RoomRoleObservation.basis:113` 同名不同义两处声明；sidecar 绑 §3.2 身份 | ✅（`/tmp` 副本 `sed -n 49p;113p` 逐字中；§二+§8.3 双处写明） |

九条全在，处置与理由齐。返工单验收 5（sidecar 绑 sha256 身份或明写不做）✅：§8.3 给了
完整载荷与验证程序（重算 sha → 验签 → pointer/id 唯一解析 → issuer/key 受信，任一不合 ⇒ 回 unknown）。
残留一个它没答的点归入 N-5：**验的是「谁说的、说的是哪份产物」，不是「说法有据」**——
载荷八字段无一指向像素/结构证据，basis 值本身无 evidence ref，签发者未定义。
机制今天休眠（无 issuer、无 fixture，§9.4 也明写验签子集「将来才新增」），不阻断；
首用前必须钉：非 unknown 的 legacy basis 要么带 pixel witness，要么明标 producer-asserted，
且 §9.2 补「可信签发者但 basis 无据」的处置测试。

## 五、A4 · 新数 provenance（主控已核 2 个，其余全部回文件实测）

| 断言 | 实测（/tmp/o22_r2 @54e3633） | 判 |
|---|---|---|
| f9 `pen==wall` 恰 10 条、thickness 全 null、S1–S4 外皮 / S5–S10 中线 | 10 / 0 非空 / note 逐条读：S1–S4「外皮线」、S5–S10「中线」 | ✅ |
| f9 `:35` = 外皮线笔画 | 第 35 行 = S1 的 note 行（南侧外周墙·外皮线 y=0） | ✅ |
| sm22 `:27` = centerline | 第 27 行 = `"south perimeter wall centerline"` | ✅ |
| W01 `thickness_m=0.239`、无 basis 键 | 值=0.239；geometry 键 = `kind/p1/p2/thickness_m` | ✅ |
| W01 双锚点 `#L19` / `#L29` | 第 19 行 = `"geometry": {`；第 29 行 = `"thickness_m": 0.239` —— **两处都对**（一指节点一指值） | ✅ |
| 存量 1240 / basis 键 0 / 有厚度 132 / sm21 零 as-drawn | 327 views · 1240 wall strokes · basis 键 0 · thickness 非 null 132 · `*sm21*` as-drawn 产物 0 | ✅ |
| as-drawn 三份产物（sm25 1F/2F、sm24 1F） | `…_prototype/out/` 的 `sm25_1f_v2 / sm25_2f_v2 / sm24_1f_v2` | ✅ |
| W01 view 能被 ReadingView/detector 收下 | /tmp 哨兵下 `model_validate` OK、`_detect_legacy_reading_view=True`（f9 同 True） | ✅ |
| `answer_compiler.py:110` 词表 | 第 110 行 = `basis: Literal["wall_axis", "outer_skin"]` | ✅ |
| sm24 四 solid band | `sm24_1f_v2`：solid=4（L001/L030/L098+1） | ✅ |

**零无出处之数。**（本轮我加的三个新数——178 条 callout 厚度墙、L012、W01 笔画=带中心——
出处即本裁决 §一.③ 与可复现命令。）

---

## Findings

### 阻断（0 条）

无。返工单验收 1–6 逐条通过；B-1 修法经三条同形输入（W01 / 178-callout / L012）推演均封死。

### 不阻断（7 条）

| # | 内容 | 证据 / 修法 |
|---|---|---|
| **N-1** ⭐ | `counterface_state` 缺**第六种真实状态**：counterface **墨迹在、被 reader 丢了**（未提升为 face line）。`not_in_observations` 字面真而「未观测」假；`observed_unclaimed` 需要不存在的节点 pointer。sm25 2F `L012`（模块 1 首批必须覆盖的三份产物之一）即此态，reason 自证 "The ink is there — column 655"。不修则 packet 拿失真前提喂决定模型（「没有对面证据」⇒ 模型可能接受 degraded，而一次定向再感知即可收回）。**修法**：加第三值（如 `ink_present_unpromoted`，必须带像素 witness pointer）或把 `not_in_observations` 的判定定义成「像素通道亦无墨」的显式检查 | §一.③；`sm25_2f_v2.json hypotheses.unpaired_wall_faces.L012` 原文 |
| **N-2** | §6.1 第三条自动路「已签规则唯一决定 ⇒ 自动」（`:364`）未被优先序句（`:369`）序入、不受 #9 后半字面管辖——与上一轮 B-1 同病族（自动规则未被优先序网住）。自然实现不会拿它造中线（§5.2 unknown 必开项），故不阻断；一句话收口：该行同样不得化解已开项 item、不得产出任何 basis/方向决定 | §二.1 |
| **N-3** | 成功判定缺「开项闭环」不变量：`:420`「无 blocking open item」的 blocking 判定者未定义，成功时 `open_items ⊆ 已决 ∪ 债 ∪ 再感知` 无一句绑死——被模型忽略的未决项字面上可既不决定也不进债而成功照发。补一句不变量 + 一条反证测试（未决项存在时成功必须失败或落债） | §二.2 |
| **N-4** | 自报最薄弱处（envelope→attempt/report）**零测试行**：§9.2 十六行无一打消费侧，而 §十三自己出的第二问正是攻击这里。同上一轮「adapter 有测试、executor 零覆盖」的形状。补两行：strict 拒 degraded 裸 geometry；envelope 缺失 / hash 不闭合 / debt 不闭合 ⇒ 响亮失败 | §三；`:420/:526-547` |
| **N-5** | sidecar 验的是**身份+签名**不是**主张有据**：载荷八字段（input_id…key_id）无一指向像素/结构证据，basis 值无 evidence ref；签发者未定义（「issuer 受 profile 信任」）。签发侧若把 note 正则结果拿去签名，验证全绿、basis=centerline、§6.1 显式 centerline 行放行 auto identity——B-1 换门复活。机制今日休眠（无 issuer/fixture）故不阻断；首用前必钉：非 unknown legacy basis 带 pixel witness 或明标 producer-asserted + §9.2 处置测试 | §四 NF-9 段；§8.3 `:491-506` |
| **N-6** | `requested_effect.kind` 封闭枚举与 §6.2 自己举的例子未对账：「走廊幻墙」（一堵**不该存在**的墙）在五 kind 里无直接对应——`review_topology_relation` 的 `connect/separate` 是关系操作、`review_segmentation` 是切/并段，删墙只能勉强挤进 connect。补一句「设计自举例子 → kind」映射表或承认该 kind 缺失 | `:393-404` vs `:408` |
| **N-7** | 代价诚实度补一寸：稿子拿 W01 当展示例，但 W01 所在 view **22 堵墙全部 unknown**（本审实测：22/22 带厚度、无 basis 键、note 自称 "face line (centreline)" 一笔画内自相矛盾）——strict = 22 次墙级再感知 / exploratory = 全 degraded。§9.4 点名了 sm21 的量级，没点名自己引用的这份主力 legacy view 的量级。与 NF-1 同宗（代价要说全），一句话补 | §一.③ W01 复核段 |

---

## 方法论备注

- **第三条才是有牙的那条，本轮再次实证**：①② 在旧稿/新稿上都一次过；真正压测试的是
  三条同形输入——其中两条（178-callout、L012）是稿子与请求书都没列到的形状。
  178 那条若在旧稿上走：厚度从 callout 来 ⇒ 候选有 t ⇒ 「硬约束筛剩一个 ⇒ 自动」在旧稿字面
  同样放行，且比 f9 更隐蔽（账面连「无 t 可用」的破绽都没有）。
- **「没有假数，但结论凭空」的病族反查**（CLAUDE.md §2 ③）：W01 是最典型样本——
  identity 恰好给出对的结果（线真在带中心），若静默放行会在验收面上**奖励**这条腿；
  新稿把它强制改走「再感知 → 类型化声明 → 显式 centerline 行」，结果同、证据链在。
- **一次读数不是证据的执行**：主控核过的 2 个数全部独立重跑（0.239/132）；主控没核的
  数（f9 十条、三份产物、锚点、plan.md 登记、detector 收下）也全部回文件实测，
  无一条转述。请求书给的另两个候选方向（两端不一致/多值厚度）查过为 0 例，记录在案而非跳过。
- **对四个攻击面问法的判定**：A1–A4 均成立，本轮派工方题错计数不加一。
  A2 的二分问法（设计缺口 vs 施工必钉）恰好切出了 N-4（真缺口）与施工钉（其余）的分界。

## 可复现命令（全部在 /tmp，主树零写入）

```bash
git -C /workspaces/EnergyPlus-Agent-dev archive 54e3633 | tar -x -C /tmp/o22_r2 && cd /tmp/o22_r2

# ① 旧稿 B-1 复现（8 条不变量 + 两行无优先序）
git -C /workspaces/EnergyPlus-Agent-dev show 88ea056:AI_agent/logs/reviews/verdict/2026-08-30_o22_evidence_contract_gpt_design.md \
  | sed -n '162,173p;199p;305,311p'

# ② 新稿封堵（#9 / 优先序 / 行限定 / 测试行 / §5.2）
grep -n "已进入 \`open_items\`\|执行优先序\|不得用于\|即使后续筛成唯一\|test_unknown_basis" \
  AI_agent/logs/reviews/verdict/2026-08-30_o22_evidence_contract_gpt_design.md

# ③-1 W01 形状 + 几何事实（笔画=带中心）+ detector 收下（哨兵断言见下）
python3 - <<'EOF'
import json; d=json.load(open('case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H1/0_reading/1f_view.json'))
w=[s for s in d['strokes'] if s.get('pen')=='wall']
print(len(w), all((s['geometry'].get('thickness_m') is not None) and ('basis' not in s['geometry']) for s in w))
w01=[s for s in w if s['id']=='W01'][0]; print(w01['geometry'])
print('band centre x =', ((281.5-281.8137799148931)+(292.5-281.8137799148931))/2*0.021634122339601443)
EOF
python3 -c "import sys; sys.path.insert(0,'/tmp/o22_r2'); import json, src.agent.reading.schema as s, src.agent.reading.vector_contract as v; assert s.__file__.startswith('/tmp/o22_r2'); d=json.load(open('case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H1/0_reading/1f_view.json')); print(s.ReadingView.model_validate(d) and v._detect_legacy_reading_view(d))"

# ③-2 自选同形 #1：unknown + 厚度在 callout（178 条）
python3 - <<'EOF'
import json, glob
from pathlib import Path
n=0
for f in sorted(glob.glob('case_tests/**/0_reading/*_view.json',recursive=True)+glob.glob('tests/**/0_reading/*_view.json',recursive=True)):
    d=json.loads(Path(f).read_text()); by={x.get('id'):x for x in (d.get('dimensions') or [])}
    for s in (d.get('strokes') or []):
        if s.get('pen')=='wall' and not (s.get('geometry') or {}).get('thickness_m'):
            tv=[(r,by[r]['value_m']) for r in (s.get('dimension_refs') or []) if r in by and by[r].get('value_m') and 0.09<=by[r]['value_m']<=0.5]
            if tv: n+=1
print('unknown + callout-thickness walls:', n)
EOF

# ③-3 自选同形 #2：L012 第六态
python3 -c "import json; d=json.load(open('AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_2f_v2.json')); print(d['hypotheses']['unpaired_wall_faces']['L012'])"

# A3/A4：plan.md 登记 + 词表锚点 + 存量四数
grep -n "模块 7 的收窄工程" AI_agent/plan.md | head -1
sed -n '110p' src/agent/judge/answer_compiler.py && sed -n '49p;113p' src/agent/reading/schema.py
# 存量 327/1240/0/132 复跑见上一轮裁决 §二 脚本（本次同读数）
```

—— GLM 跨家族审阅席位 · 2026-08-30
