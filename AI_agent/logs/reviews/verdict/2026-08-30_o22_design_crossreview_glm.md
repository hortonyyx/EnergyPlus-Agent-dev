# 跨家族裁决书 · ②-2 设计稿（correction 消费多形态墙证据的契约）

- **日期**：2026-08-30 · **审阅方**：GLM 家族（交换审）· **出稿方**：GPT 家族
- **请求书**：[`../request/2026-08-30_o22_design_crossreview_glm.md`](../request/2026-08-30_o22_design_crossreview_glm.md)
- **送审对象**：[`2026-08-30_o22_evidence_contract_gpt_design.md`](2026-08-30_o22_evidence_contract_gpt_design.md)（设计稿，⛔ 不是代码）
- **审阅基点**：主树 `08.23_AsDrawnReading` @ `ea19582`（请求书头部写 `422c627`；实测
  `git diff 422c627..ea19582 --stat -- src/ tests/ scripts/ case_tests/` = **空**，两个 commit 间代码面零变化，
  承重事实在 HEAD 上逐条重核）。`.pth` 哨兵实测
  `58f547fa9433af6e…`（`_editable_impl_energyplus_agent.pth`，内容 = 主树路径）与派单读数一致。
- 全部实测在 `git archive ea19582` 的 **/tmp/o22_review 副本** + `/tmp/b1_fixture` 上跑；
  主树 `src/` 零写入，答案根 `case_tests/test_baseline/gt/` 零写入；本审唯一可写文件 = 本裁决书。

---

## 裁决：**REWORK**（阻断 1 条 · 不阻断 9 条）

**设计主体成立**：三块正交契约（4 正向声明 + 3 处置 + 候选图）、统一证据包、
基准转换归 correction 内确定性 compiler、三拍「模型出决定、代码出坐标」、§8.3 迁移纪律、
§9 验收矩阵——逐攻击面审下来**没有一个核心主张被推翻**；B1 的主腿（detector→adapter→bundle→compiler→kernel
的静默中线）**被它自己的设计堵住**；B6 六问全答。

**但 B1 出稿方自己点名要打的那条腿，在它自己的 §6.1 里留了一条符合稿子字面的复活路径**（阻断 B-1）：
`basis=unknown` 且无类型化厚度时（f9 的真实形状，实测：`thickness_m=null`、四条 `dimension_refs`
全是长度链、240 只在禁解析的 note 里），偏移候选无 t 可用，候选集若含 `identity`
（「最小扰动」的自然实现，稿子未禁止）则「**硬约束筛后只剩一个候选 ⇒ 自动执行并记账**」的规则
**恰好把最危险的候选唯一化**——外皮线静默当中线，且账面有 auto_action、看似合规。
§5.2 的禁令只禁「因 prompt 曾要求中线」，未禁「因唯一候选」；两表无优先序声明；§9.2 十五条测试
无一条拦 executor 层。**修法一句话级**（硬不变量 + 一条反证测试，见 B-1），不推翻设计——
但这是全稿最核心的承诺（基准隔离），必须稿子自己钉死，不能靠施工单转述 findings。

对六个攻击面问法本身：B1/B3/B4/B5/B6 问法成立；**B2.1 的问法预设窄了**（见 §二开头）。

---

## 〇、§〇 承重事实逐条核对（全部回文件 `grep -n` 核）

| # | 稿中断言 | 实测 | 判 |
|---|---|---|---|
| 1 | `pipeline.py:367` 逐字 `world-frame, wall-centerline`、`:370` 逐字 `wall CENTERLINE` | 两行逐字吻合（sed 360–375 实读） | ✅ |
| 2 | `vector_contract.py:205-219` 唯一 `CONSUME` = legacy；`:153-178` 要求显式 `strokes` + `ReadingView.model_validate` 成功 | 吻合；全文件 `Disposition.` 共 5 处（208 CONSUME / 214·222·229 KNOWN_NOT_CONSUMED / 236 EXCLUDE），**CONSUME 唯一** ✅ | ✅ |
| 3 | `as_drawn_v2.py:560` `assemble(...) -> dict` 裸 dict、生产者无自己的类型 | `:560` = `def assemble(...) -> dict:` 吻合；`class \w*(Hypothes\|Percept)\w*` 全仓 `--include="*.py"` **零命中**（grep exit 1） | ✅ |
| 4 | `as_drawn_v2.py:622-631` 原样产出 `pair_candidates`/`pairs`/`non_wall_face_lines`/`unpaired_wall_faces`/`solid_band_walls`/`ambiguous_face_lines` | 六键逐行落在 622/627/628/629/630/631 | ✅ |
| 5 | `Stroke.geometry` 自由 dict、类型上没有 `basis` | 断言成立：`schema.py:49` `geometry: dict = Field(default_factory=dict)`；全文件唯一 `basis` 字段在 `:113`（`RoomRoleObservation.basis`，room-role 语义，与墙无关）。**锚点注**：稿子链接 `#L117` 指到的是 `ReadingView` 类定义行（指类不指字段），断言不受影响 | ✅（锚点精度记 NF-9） |
| 6 | 承重反例：同一 `pen=="wall"`，f9 note 写外皮线、sm22 note 写 centerline | f9 S1 `pen=wall`、note「南侧外周墙（**外皮线** y=0…）」、`smalloffice_22` S1 `pen=wall`、note「south perimeter wall **centerline**」；两者 geometry 键**完全同形**（kind/p1/p2/thickness_m，thickness_m 均 null） | ✅ |

**五行全部成立，承重前提无塌角。**（请求书 §〇 的「对不上即阻断」条件未触发。）

---

## 一、B1 · ⭐⭐⭐ 静默中线腿：**主腿被设计堵住；残缝一条 → 阻断 B-1**

### 1.1 今天链路的实测（问题现实性坐实）

构造 view：S1 外墙 note「外皮线」、S2 内墙 note「centerline」、S3 与 S1 同性质墙 note 却写
「centerline」（互相矛盾），`/tmp/b1_fixture/make_and_run.py` 全链实测：

| 环节 | 实测结果 |
|---|---|
| `_detect_legacy_reading_view(view)` | **True**（收下） |
| `classify_vector_dir` | consumed = `['1f_view.json']` |
| `_build_correction_messages` | view JSON（**含矛盾 note**）**逐字 paste 进 human prompt**（`[reading vector] 1f_view.json` 块）；system prompt 逐字 `wall CENTERLINE` |
| system prompt 里的 basis 感知 | 仅 **prompt 词表散文**（escalation 表里有「unknown wall side, no thickness basis → `reference_or_identity_ambiguity`」）——模型被告知的纪律，**无载体无门** |
| `CorrectedGeometry` / `CorrectedGeometryV3` | `basis/thickness/spacing` 字段 **NONE / NONE**（schema properties 全量枚举） |
| kernel 入口 | `pipeline.py:46` `from src.agent.correction import CorrectedGeometry, apply_deterministic_core`——correction 产物直进 deterministic core，**链上无 wall IR** |

⇒ 今天：混合 basis 输入被**静默当全中线消费**，链上零载体、零门、零升级落地槽。
（也说明 prompt 里那句 escalation 词表今天已是「model-visible but not enforced」——
正是稿子「散文纪律不是防线」立场的实证。）

### 1.2 设计稿堵住了主腿（纸面追踪，沿 detector → adapter → packet → 投影 → kernel）

- §8.2 判别 #3：构造输入无 `schema` 字段 ⇒ legacy structural fallback ⇒ ADAPT(legacy adapter)；
- §8.3：`pen==wall` 一律 `legacy_wall_trace`，历史产物无类型化声明 ⇒ **basis=unknown**；
  ⛔ 正则解析 note、⛔ `unknown→centerline` 暗设；
- §5.2：`basis=unknown` **必须开项**，「不能因 correction prompt 曾要求中线就自动 identity」；
- §4.1：非 unknown 必须有**结构化** basis evidence ref（note 不算）；
- §6.1/§7.2：unknown 开项后由模型选 `request_reperception` 等决定，或 profile 允许的 degraded。
- §5.4 兼容投影：`CorrectedGeometry` 降为「从同一 resolved wall IR **确定性派生**的投影」，
  §9.1 #7 模型不再直填 ⇒ 单向派生 + 入口删除 = **机制**而非措辞；§8.1 双源同槽
  `DUPLICATE_SEMANTIC_INPUT`、迁移期影子 profile 显式命名——**没有一条允许静默 identity 的腿**。

### 1.3 残缝：§6.1 的自动执行规则可以复活它（→ 阻断 B-1）

f9 外墙 S1 的实测（这条链每一环都量过）：

```
pen=wall · note=外皮线（§8.3 禁解析）        ⇒ basis=unknown
geometry.thickness_m = None                  ⇒ stroke 自身无厚度
dimension_refs = D1/D11/D12/D22，实值        ⇒ 15000(总长)/540(门洞)/900(门洞)/8000(进深)
                                              ——四条全是长度链，无一条墙厚
```

⇒ 按 §5.2，±t 偏移候选**无 t 可用**。此时候选集只有两种照稿施工：
**{identity}**（「最小扰动=相信这条线就是中线」，完全自然的实现，稿子未禁止 identity 进候选集）或空。
若 {identity} ⇒ §6.1 处置表「**硬约束筛后只剩一个候选** ⇒ 自动执行并记账」⇒
**外皮线静默当中线**，账面 auto_action 记录齐全、看似合规——这正是稿子 §十二自己定义的击穿条件
（没有类型化 basis 证据、没有 open item、没有 degraded ledger 被当成中线成功消费）。

为什么稿子现有的话堵不住这条：
- §5.2 的禁令是「不能**因 correction prompt 曾要求中线**就自动 identity」——只禁这个**理由**，
  没禁「因唯一候选 / 因 Pareto 支配」；
- §6.1「互不支配的…候选 | 进入 open_items」与「只剩一个候选 ⇒ 自动执行」两行**无优先序声明**，
  「unknown 必须开项」与「唯一候选自动执行」在最典型输入上给出相反指令；
- 「⛔ 不选最近值」只管厚度取值，identity 不是「值」；
- §9.2 的 `test_legacy_outer_skin_stroke_does_not_become_axis_trace` 测的是 **adapter 层**
  「不吃 prompt 默认」，**executor 层**（开项内容被自动执行规则消化）零覆盖。

**修法（一句话级，不推翻设计）**：
1. §4.4 硬不变量加第 9 条：**「basis 无 centerline 证据的墙，其候选集不得包含 identity 类操作；
   已进入 open_items 的 item 不受『只剩一个候选 / Pareto 支配 ⇒ 自动执行』管辖
   （该规则只适用于未开项情况）」**；
2. §9.2 加 `test_unknown_basis_item_is_never_auto_resolved`：喂 f9 形状（无类型化厚度）夹具，
   断言产物走 open_item / `unsupported_or_reperceive`，auto_actions 中**不出现** identity 中线。

附带（不阻断但施工必钉）：「签名 sidecar」（§8.3）的签名验什么未定义——sidecar 若无验证机制，
「签名」只是词；照稿施工时 sidecar 必须绑定 §3.2 的 sha256 身份（否则是一个新的伪造面）。

---

## 二、B2 · 主控四数复核一致；三问判定 + 一处问法修正

**复核**（`case_tests/**/0_reading/*_view.json` + `tests/**/0_reading/*_view.json` 递归）：
view 文件 **327**（带 strokes **327**）· strokes 总数 **3353** · `pen==wall` **1240** ·
geometry 中 basis 形状键 **0** ——**四数与主控读数逐个一致**。

我加量的三个数（三问都要用）：
- **1240/1240 全带 note**；note 里「中线」264 条、「外皮」**176** 条、「centerline」45 条
  ⇒ note 是**自相矛盾**的信号源（两个方向并存）——「解析 note 承重」在数据上就不可能自洽；
- `pen=wall` 且 `thickness_m` 非 null = **132** 条（有厚度值、无方向无基准——§4.1「不能无条件晋升」的实证面）；
- **as-drawn 产物全仓只有 3 份**（`AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/`
  的 sm25 1F/2F、sm24 1F，均在实验目录）；**sm21 零 as-drawn 产物**（验收三 case 之一只有 legacy 路）。

**对 B2.1 问法本身的修正**：问「代价是不是所有历史输入都得重新感知」预设窄了——按稿子 §7.2，
exploratory/历史 profile 可以 degraded 继续（不重新感知），strict 档才阻断。
**正确问法**：「strict 与 exploratory 两档下，unknown 的历史输入各自的**终点**是什么、
判分读数各自怎么读」。按这个问法：

1. **纪律对不对**：对（note 自相矛盾 176 vs 309，量化坐实「拿自由文本承重」必错）。
   **诚实度 = 部分诚实**：§十一 自报了风险方向（「不足以证明不会让大量历史输入退化为 unresolved」），
   但没量出 100%，也没点名最疼的一条——**sm21 作为验收 case 只有 legacy 路，在新契约下 =
   全 degraded（exploratory）或全量重新感知（strict）**，稿子只字未提（→ NF-1）。
2. **§9.4 在 100% unknown 下**：「旧 ReadingView 历史 case | **显式 centerline 的 fixture 保持兼容**；
   basis 不明者必须显示 open item/degraded」——实测 basis 键 = 0 ⇒ **「显式 centerline 的 fixture」
   在今天存量上是空集**（sm22 的 centerline 只在 note，按 §8.3 同样 unknown）⇒ 该行前半句无验收对象，
   整行实际宣告「所有历史 case 都 degraded」；与第一行「correction judge 各项不下降」并置时
   这个矛盾稿子没有点破（→ NF-1，与 §9.4 改写合并为返工项）。
3. **第三条路存在，稿子没提**（→ NF-2）：
   - **(a) 墙级定向再感知（推荐）**：稿子的 `reperception_required` 词汇已在框架内，缺的只是**粒度**——
     把「重新感知」从整图级降为**墙级带锚点的定向请求**（crop 到该墙区域，reading 模型看图回
     类型化 basis 声明 + 像素证据）。分工最干净（认 = 模型在 reading **且有图**），成本
     O(unknown 墙数)，不是 O(全图重跑)。sm21 的「全量重新感知」按此化为每墙一次小调用。
   - **(b) note 作为模型可见线索**：§8.3「自由文本只能做审计展示」一刀切禁掉了它——但「**代码**
     正则解析 note 成结构化事实」（该禁）与「**模型**在 open_item 里读 note 线索选候选，
     决定带 decision_id、坐标代码算、事后全检」（可议）是两件事。因 note 实测自相矛盾，
     (b) 只能当线索不能当证据，弱于 (a)；列此是为了把 §8.3 的禁令边界写准。
   - 主控 ⛔ 的「加配置逐图声明」两条路都不沾（无人工填写）。
   - 另注：本批既定次序本就是「统一按新 reading 做」，历史 legacy case 的 degraded 大半被方向吸收；
     真正剩下的代价面就是 sm21（无 as-drawn 产物，得先跑一次新 reading——那是既定方向，不是本稿新增成本）。

---

## 三、B3 · 同一把刀砍它的三块划分

1. **`legacy_wall_trace` 混轴？——是，但为「轴未明示」而非「划分错误」**（→ NF-3）。
   `paired_faces`/`solid_band`/`single_face` 的断言内容是**几何角色明确**的观测
   （两面 / 墨带 / 单面），`legacy_wall_trace` 断言「是墙相关线迹」——几何角色**未知**的降级声明。
   四种 kind 实际横跨「角色已知 ×3 + 角色未知 ×1」两档，而稿子批评「六形态」用的正是
   「混了不同性质的轴」这把刀。判不阻断：四种按「断言内容」划分仍同质（都是「证据与墙的关系」），
   且 legacy trace 确实无法给出几何角色——但表格应加一列「几何角色已知？」明示这根隐藏轴，
   否则施工者会把四种当同层做 discriminated union 的完备性论证。
2. **第五种存在**（→ NF-4）：`single_face` 的 canonical 字段只写
   `counterface_state=not_in_observations`——但存在「**另一面被观测到、却未被认作面线**」
   （落在 `ambiguous_face_lines` / `non_wall_face_lines` 桶）的情况：此时字面「另一面没有进入
   observations」为**假**，字段会说谎，下游裁决模型被喂假前提。
   （间接护栏 = §7.2 ambiguous 的 evidence debt 机制；但字段枚举应扩为
   `not_in_observations | observed_unclaimed`。）
3. **`claimed_wall` 与四种声明是否记两遍、谁是权威**：**稿子答了且有机制**——
   disposition 是**面线级**消费账（每条 face_line 恰好一个处置），claim 是**墙级**断言内容；
   一致性由 §4.4 #2（恰好一个处置、重复售卖 = 输入完整性错误）与 §7.1（non_wall 引用不存在
   又被 claim 消费 = 契约错误）互锁。权威 = claim 是断言权威、disposition 是消费账，不一致响亮失败。
   此面通过。

---

## 四、B4 · 三拍铁律逐处查「坐标有没有间接出口」

1. **operation 参数来自模型？** 否——`source_values[]` 是 refs，值由 resolver 从 hash 绑定源重算
   （§3.2「所有派生值由 resolver 从被 hash 绑定的源节点重算」）✅。
2. **`SNAP_TO_DECLARATION` 吸附值谁定？** 声明值来自 callout/dimension refs，代码解析；
   模型只选操作（`symbolic_operation` 枚举）✅。**但** `whole_building_review.findings[].requested_effect`
   只写了「结构化意图，不含坐标」而**未给 schema**——「把 W 与 W3 对齐」类意图中模型指定**参照实体**，
   这是模型→坐标的最近通道，必须在施工单把 requested_effect 的 kind 枚举化（→ NF-6）。
3. **两个弃权出口下游怎么算、谁判**：稿子答了且基本可执行——`non_wall` = reading 模型的否定语义
   判断，代码自动排除记账（§6.1/§7.1）；`ambiguous` = `known_missing` 状态，strict 档
   「可能改变房间围合/墙拓扑/洞口 host/出模边界 ⇒ 阻止成功」（依赖分析由代码做），
   exploratory 档 degraded 继续 + judge 不缩分母（§7.2）。**未接线的半条**：
   judge/记录侧今天消费的是兼容投影 `CorrectedGeometry`，实测
   `src/agent/judge/correction_score.py` 全文**不读** `conflicts`/degraded/completion——
   「judge 不缩分母」今天无执行者（好消息：judge 看不到 ⇒ 无从放水；坏消息：degraded 产物与完整产物
   在投影消费侧不可区分）。投影派生规则必须写明 debt 摘要落在哪（→ NF-5）。
4. **投影会不会变成第二份真相**：**机制在**——§9.1 #7 模型不再直填 `CorrectedGeometry`
   （prompt 出口契约换成 `CorrectionDecisionResponseV1`，入口删除），投影单向派生
   （resolved → CorrectedGeometry），步骤 1–6 过渡期生产真相仍在旧腿、新腿 shadow。
   判「机制」✅（非措辞）。

---

## 五、B5 · §0.1 逐个过：**能今天开工的最小集 = 6 个模块 + vector_contract 一行注册**

「下一次跑测」= 本批目标 ③（新 reading 落地后拿 **sm25** 全流程撞通，correction 侧换到吃 as-drawn 证据）。
逐模块过「不做它，下一次跑测能不能跑起来、结果能不能读」：

| # | 模块 | 甲/乙 | 理由（实测依据） |
|---|---|---|---|
| 1 | `reading/as_drawn/schema.py` | **甲**（可裁字段） | 不做 ⇒ detector 只能键形判别（今天的 as-drawn detector 实测 = `_is_declared + _has_keys`）⇒「声明了 schema 但结构不符」静默当合法 ⇒ §4.4 #7 `MALFORMED_DECLARED_CONTRACT` 无牙 ⇒ **错得读不出**。裁剪：字段覆盖 = 墙 + 洞口两族（face_lines / pairs / pair_candidates / 五桶 / opening_candidates / opening_types——稿子 §3.1 自己点名洞口半边不能丢）；ledger/roles 等非墙通道登记 plan.md 缓做 |
| 2 | `correction/evidence_contract.py` | **甲**（可裁字段） | 统一包是全部下游的载体；没有它引用闭环/不变量 1–8 无处落。裁剪：`ObservationRefV1` 的 `native_handle`/`evidence_resolution` 两槽可缓（稿子自己说当前图像产物「不得伪造」handle ⇒ 先不建该槽） |
| 3 | `correction/evidence_adapters.py` | **甲** | 不做 ⇒ as-drawn 进不了 correction（今天 disposition = KNOWN_NOT_CONSUMED 实测）⇒ sm25 撞通无从谈起 |
| 4 | `correction/wall_compiler.py` | **甲**（可裁检查面） | 不做 ⇒ 无 provisional、无 open_items，三拍第一拍不存在。裁剪：拓扑/dimension 一致性先做最小面（对撞/围合）；cost_vector 的跨层差异维度缓做 |
| 5 | `correction/decision_schema.py` | **甲**（可裁回环） | 模型出口契约；`extra="forbid"` + 无坐标字段是铁律本体。裁剪：findings 回环先做**单轮**（finding → 新候选 → 下一轮 → 终止），轮次预算/decision hash 循环检测登记缓做 |
| 6 | `correction/decision_executor.py` | **甲** | 不做 ⇒ 决定变不成坐标，跑不通 |
| 7 | `vector_contract.py` **收窄改造**（CONSUME→ADAPT 重命名、目录 ledger 重排） | **乙**（登记 plan.md） | 不做它跑测照常：现有 CONSUME 语义上 = ADAPT-to-legacy-adapter，键名不换不跑偏。**例外的一片属甲**：`as_drawn_plan` 的 disposition 从 KNOWN_NOT_CONSUMED 改为指到新 adapter——**一行注册**，是模块 3 生效的前提，不是收窄工程 |

**§9.2 测试 × §0.1**：跑测必需 = byte-identical 确定性、face 恰好一个处置、legacy 不吃默认、
坐标字段拒绝、sm24 四 solid band（验收 case）、双面余段存活（sm25 有不等长面，会真咬）；
**B-1 返工新增的 `test_unknown_basis_item_is_never_auto_resolved` 同属甲**（它锁的是全稿核心承诺）。
可缓 = 厚度反事实矩阵、ambiguous 反事实矩阵；`DUPLICATE_SEMANTIC_INPUT` / `AMBIGUOUS_CONTRACT_MATCH`
两条建议保留（F-97 家族的牙齿，便宜）。
**§9.3 喂答案两层全是甲**：第二条（resolved 答案直喂内核）是稿子自己说的「最便宜也最承重」。

⇒ **最小集 = 模块 1–6 + 模块 7 的一行注册**；砍掉的不是「第 7 个模块」而是模块 7 的收窄工程。
各乙项欠的账：收窄重命名欠「跑测读数不因键名变化失配」的一次核对（届时与 judge/报告侧联动）；
ledger/roles 源模型欠「非墙通道进 bundle 时补 channel_status」；findings 无限回环欠轮次预算设计。

---

## 六、B6 · 六问机械对账 + R-6 判定

| 派工单 §二 问题 | 稿子位置 | 判 |
|---|---|---|
| 1 形态字段与语义 | §四（4 声明 + 3 处置 + 候选图，各带「断言什么/不断言什么/必带引用」三列） | ✅ |
| 2 基准在哪层转换、谁做（含 R-6 半句） | §5.1（correction 内确定性 compiler，reading 不加 centerline 便利字段、适配器不做坐标） | ✅ |
| 3 三拍怎么落 | §六（packet/response/executor，含 stale hash、轮次、响亮退出） | ✅ |
| 4 弃权怎么进出 | §七（non_wall=否定断言、ambiguous=弃权，进出两侧都有、profile 分档） | ✅ |
| 5 与已声明契约并存还是取代 | §8.1（源注册表并存、correction 内单执行腿、同槽双源失败） | ✅ |
| 6 迁移与验收 | §9.1 八步 / §9.2 测试 / §9.3 喂答案 / §9.4 矩阵 | ✅（§9.4 一行待改写，见 NF-1） |

**六问全答，无遗漏。**

**R-6 是机制不是措辞**：实测今天 `CorrectedGeometry`(V1/V3) 零 `thickness`/`spacing`/`basis` 字段、
correction 产物直进 deterministic core 无 wall IR——稿子的改动是**真接线**：
`ResolvedWallV1` 新代码产物携带 `observed_face_spacing_m`/`resolved_thickness_m`/两个 basis +
`thickness_resolution`，且「内核权威输入改为 `CorrectionResolvedV1`」。
**施工验证点**：kernel 入口真换 + §9.2 末条 `test_observed_spacing_and_resolved_thickness_survive_kernel_entry`
落地才算数（稿子 §5.4 自己写了）。「R-6 在 **pipeline 侧**不再复发」的限定词用得准（gt 侧归 ②-1c）。

---

## 缝隙对账（请求书 §三 要求点名）

- **②-1c 出模两形式 ↔ 本稿 `ResolvedWallV1.output_basis`：缝真实存在，双方都没覆盖**（→ NF-8）。
  实测：判分侧已有既有词表 `answer_compiler.py:110` `basis: Literal["wall_axis", "outer_skin"]`
  （:605–609 一处取值默认 `"wall_axis"`）；本稿 `output_basis` 只有字段名**没有取值域**。
  两套词表若各自定义，②-2 施工完后 correction 产物自述的输出基准与判分侧读墙基准**各说各话**，
  对账无键。**对齐责任归 ②-2 施工方**（它是后出者，且本稿 ⛔ 不动 gt 侧 ⇒ 只能它来引用）：
  `output_basis` 的 Literal 直接引用判分侧既有定义或写明机械映射表。这不是「向 judge 新增事实」
  （引用既有词表 ≠ 新增事实），不违反稿子 §十 的边界。
- ②-1c 裁决已点的 NF-7（`read_facts_for_compilation` 的 request 配对契约）维持范围外；
  correction 侧（本稿）、edge boundary_condition（②-1d）维持范围外裁定。
- 两份请求书的并集在本审后无新裸区：gt 侧对账归 ②-1c（已裁），correction→判分的 basis 词表缝本审点名。

---

## Findings 汇总

### 阻断（1 条）

| # | 内容 | 证据 |
|---|---|---|
| **B-1** | ⭐⭐⭐ **§6.1 自动执行规则可复活静默中线腿**：`basis=unknown` 且无类型化厚度时（f9 真实形状），偏移候选无 t；候选集若含 identity（稿子未禁止），「硬约束筛后只剩一个候选 ⇒ 自动执行并记账」恰好把最危险的候选唯一化——外皮线静默当中线，账面 auto_action 看似合规。§5.2 禁令只禁「因 prompt」，未禁「因唯一候选」；两表无优先序；§9.2 无 executor 层反证。**修法**：§4.4 加第 9 条硬不变量（identity 不入无 centerline 证据墙的候选集；已开项 item 不受自动执行管辖）+ §9.2 加 `test_unknown_basis_item_is_never_auto_resolved` | §一.3；f9 实测（thickness_m=null、D1/D11/D12/D22=15000/540/900/8000 全长度链）；`/tmp/b1_fixture/make_and_run.py` |

### 不阻断（9 条）

| # | 内容 | 证据 |
|---|---|---|
| NF-1 | 代价诚实度部分缺失 + §9.4 旧 case 行取空：1240/1240 全 unknown（复核同主控）而「显式 centerline 的 fixture」在今天存量上是**空集**（basis 键 0）⇒ 该行实际宣告全部历史 case degraded，与「不下降」并置的矛盾未点破；sm21 零 as-drawn 产物（验收 case 之一只有 legacy 路）只字未提。**随返工改写**：§9.4 该行 + 明说两档终点 | §二.1–2；B2 复核脚本 |
| NF-2 | 第三条路存在：(a) **墙级定向再感知**（`reperception_required` 已在框架内，只缺粒度——整图级降为墙级带锚点定向请求，reading 模型看图回类型化 basis，成本 O(unknown 墙数)；推荐）；(b) note 作为 open_item 模型可见线索（代码不解析 ≠ 模型不可见，但 note 实测自相矛盾 176 外皮 vs 309 中线/centerline，只配当线索）。§8.3 一刀切「只能做审计展示」把边界写粗了 | §二.3 |
| NF-3 | 划分隐藏轴未明示：4 种 kind = 几何角色明确 ×3 + 几何角色未知 ×1（`legacy_wall_trace` 是降级声明），恰是它批评「六形态」的同类混轴。表格加「几何角色已知？」一列即收口 | §三.1 |
| NF-4 | 第五种情况存在：另一面**被观测但未被认作面线**（ambiguous/non_wall 桶）时，`single_face` 的 `counterface_state=not_in_observations` 字面为假——枚举应扩 `observed_unclaimed`。间接护栏 = §7.2 evidence debt | §三.2 |
| NF-5 | residual debt 的投影槽未定义：judge 侧实测消费投影 `CorrectedGeometry` 且 `correction_score.py` 全文不读 conflicts/degraded ⇒「judge 不缩分母」今天无执行者（judge 不可见 ⇒ 无从放水，但 degraded 与完整产物在投影消费侧不可区分）。投影派生规则须写明 debt 摘要落点，或 attempts 记录消费 `CorrectionResolvedV1` 本体 | §四.3 |
| NF-6 | `requested_effect` schema 未枚举：findings 通道里模型指定参照实体（「与 W3 对齐」）是模型→坐标最近通道，施工单必须枚举化其 kind 集 | §四.2 |
| NF-7 | B5 最小集：**6 模块 + vector_contract 一行注册**；模块 7 的收窄工程（ADAPT 重命名/ledger 重排）登记 plan.md 不做。各甲模块的可裁字段与各乙项欠账见 §五 表 | §五 |
| NF-8 | `output_basis` 词表未定义 vs 判分侧既有 `basis: Literal["wall_axis","outer_skin"]`（`answer_compiler.py:110` 实测）⇒ 两套词表无对齐人；对齐责任归 ②-2 施工方（引用既有定义/写明机械映射，不算向 judge 新增事实） | 缝隙对账 |
| NF-9 | 承重锚点精度：`schema.py:117` 是 `ReadingView` 类定义行（`Stroke.geometry: dict` 实际在 `:49`）——断言成立、锚点指类不指字段；另全仓已存在一个类型化 `basis`（`RoomRoleObservation.basis:113`，room-role 语义），照稿新增 `geometry.basis` 时两处同名不同义须在源模型注释里写清。「签名 sidecar」的签名验什么未定义（应绑 §3.2 的 sha256 身份，否则是新伪造面） | §〇 表 #5；§一.3 附带 |

---

## 方法论备注

- **对派工单攻击面的判定**：B1/B3/B4/B5/B6 问法成立且全部被实测推进；**B2.1 问法预设窄了**
  （「重新感知 or 默认」二选一漏了 profile 分档的第三态），正确问法与答案见 §二。
  派工方题错计数本单**未 +1**。
- **三问逐门**（本稿的关键门）：
  - 迁移纪律（unknown 开项）：①量得准（paper 上）；②**载体可换**——开项内容可被 §6.1 自动执行规则
    消化（B-1 实例：开项机制完好，决定权被隔壁表的数值规则换掉了）；③没锁的方向 = executor 层自动
    选择与候选集构成，理由是稿子没写到——这正是 B-1。
  - 「judge 不缩分母」：量得对，但**无执行者**（judge 消费投影、投影无 debt 槽）——NF-5。
  - 兼容投影单真相：机制在（入口删除 + 单向派生），③没锁的方向 = 投影的 debt 摘要槽（同 NF-5）。
- **一次读数不是证据的执行**：主控四数我独立复核（一致）；f9 厚度声明面换了四个 id 逐条读值；
  B1 链路五环节每环单独实测，未依赖单点。

## 可复现命令（均在 /tmp 副本，主树零写入）

```bash
git -C /workspaces/EnergyPlus-Agent-dev archive ea19582 | tar -x -C /tmp/o22_review && cd /tmp/o22_review

# §〇 承重事实五行
sed -n '360,375p' src/agent/pipeline.py                       # 367/370 逐字 CENTERLINE
sed -n '205,219p;153,178p' src/agent/reading/vector_contract.py
sed -n '555,565p;620,632p' src/agent/reading/as_drawn/as_drawn_v2.py
grep -n "geometry: dict\|class ReadingView\|basis" src/agent/reading/schema.py   # :49 / :117 / :113
python3 -c "import json;d=json.load(open('tests/fixtures/f9_window_host_crash/0_reading/1f_view.json'));[print(s['id'],s['pen'],s['geometry'].get('thickness_m'),s.get('dimension_refs')) for s in d['strokes'] if s['pen']=='wall']"

# B1 全链（detector→classify→prompt paste→schema 字段→kernel 入口）
python3 /tmp/b1_fixture/make_and_run.py     # 五环节输出见 §一.1
python3 - <<'EOF'                            # f9 S1 的四条 dimension 全是长度链
import json; d=json.load(open('tests/fixtures/f9_window_host_crash/0_reading/1f_view.json'))
by={x.get('id'):x for x in d['dimensions']}
print({k:(by[k]['text_verbatim'],by[k]['value_m']) for k in ('D1','D11','D12','D22')})
EOF

# B2 复核（主控四数 + note 矛盾面 + thickness 面）
python3 - <<'EOF'
import json,glob
from pathlib import Path
fs=glob.glob('case_tests/**/0_reading/*_view.json',recursive=True)+glob.glob('tests/**/0_reading/*_view.json',recursive=True)
ts=ws=bk=th=0; nm={'centerline':0,'外皮':0,'中线':0}
for f in fs:
    d=json.loads(Path(f).read_text()); st=d.get('strokes')
    if not isinstance(st,list): continue
    ts+=len(st)
    for s in st:
        if s.get('pen')=='wall':
            ws+=1; g=s.get('geometry') or {}
            th+= g.get('thickness_m') is not None
            n=s.get('note') or ''
            for k in nm: nm[k]+= k in n
            bk+=sum('basis' in k.lower() for k in g)
print(len(fs),ts,ws,bk,th,nm)
EOF

# B4.3 judge 可见性
grep -n "conflicts\|degraded\|completion" src/agent/judge/correction_score.py | head

# NF-8 词表缝
grep -n 'Literal\["wall_axis"' src/agent/judge/answer_compiler.py
```

—— GLM 跨家族审阅席位 · 2026-08-30
