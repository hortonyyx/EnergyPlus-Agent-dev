# A-6 收口契约（累计式自包含，2026-09-05）

工程档 / 科研 P0。目标是同图尺寸认领及跨图洞口裁决可运行、可读账；不建设通用算式语言、Python 内省防线或模数参考表。本契约直接描述最终 API，不以旧设计稿正文补定义。

## 1. 阶段与边界

第一步由 `TickSession` 拥有，每张 reading 图各一实例：代码枚举整图证据和候选 → 同图模型返回 `TickResponse` → 代码落值、检查区间、冻结本次决定。第二步 `OpeningReview` 持有各图独立的预期批次 ID：复验当前事实 → 调用既有 B4 精确配对 → 模型返回身份取舍及整栋审查 → 代码产生四分类账和坐标。

两阶段的新实现位于 `tick_claim.py` 与 `opening_adjudication.py`。现有 B4 算术/零容差判据/义务注册表保持原实现；新第二步实际调用它，输入 x、z 均从第一步重推导。B4 的历史低层 dict API 保留，本单的受约束消费入口是 `OpeningReview`，不是把那个低层函数宣称成已封装的新契约。旧 evidence bundle 没有加字段；既存 reading 字节和 bundle 哈希原样保留。新刻度证据层同时覆盖 x/z，不采用“x 新值 + z 旧裸值”的分流。

这里交付子环节 API 与代码执行，不在本单接 `run_pipeline`、调用付费模型、重做 gt 或运行 sm25 端到端；这些属派工盘面的 E-a / J 等接线和验收工作。`CorrectedGeometryV3` 装配消费新结果时，应通过当前 `OpeningReview.consume`/`scoreable_openings` 获取，不把历史 JSON 当成当前有效批次。

## 2. 冻结输入与全集来源

`TickSession(raw: bytes, *, image_id: str, supplement: bytes|None=None, expressions: tuple[(edge_id, Expression),...]=(), max_rounds: int=3)`。

- `raw` 是 reading 原始 JSON 字节。只消费 `as_drawn_elevation_v0` 和 `as_drawn_plan_v0`。立面完整枚举 `openings` 每洞 x0/x1/z_low/z_high；平面完整枚举各 `wall_bands[*].opening_runs[*].run_m` 两端。调用者不提供缩短后的边清单。
- `image_id` 是本次输入槽位；`source_sha=sha256(raw)` 是字节身份；`edge_id` 来自冻结原件的洞口 ID/角色，平面为 `band_id:run<index>:lo|hi`。平面索引只有在原字节不变时才可沿用退债身份。
- `TickPacket` 含 `packet_id/image_id/source_sha/generation/edges/source_bytes/supplement_bytes/diagnostics`。`Edge` 含 `edge_id/axis/raw_u/pointer/witness/candidates/missing_chains`；witness 以不可变 JSON bytes 保存，原来的像素与段名全部保留。
- packet 身份覆盖源哈希、补证哈希、代次以及**完整边集合和候选集合**。第一步响应集合必须和该完整集合精确相等；第二步拓扑绑定必须和已复验平面全集精确相等，四个方向的 `present/absent` 必须逐一声明。
- 无独立视觉确认的当前 witness 全部走 `SAME_IMAGE_MODEL_REQUIRED`。最近邻、`ALL_S1`、单链相邻段、多链同值都不自动终结。空图没有边，可用空响应由代码终结并记空账；非空图本批不增加自动认领规则。未来自动规则需要独立指认依据，本单未预设其存在。
- witness 引用链的所有节点均可成为候选，故模型能纠正最近邻选错的节点；没有 witness 时枚举本图该轴的声明链节点。派生候选由代码通过 `expressions` 给出，模型选择其 ID。候选越界、不属于本图或运算非法在包构造阶段报具名错误。

强制位置：[`_raw_edges`](../../../../src/agent/correction/tick_claim.py#L305)、[`build_packet`](../../../../src/agent/correction/tick_claim.py#L331)、[`submit` 全集比较](../../../../src/agent/correction/tick_claim.py#L435)、[`OpeningReview` 全集与四向清单比较](../../../../src/agent/correction/opening_adjudication.py#L155)。这些是来源集合与消费入口的实际关系，不以“循环过一遍”作为完整性证明。

## 3. 多链补证与操作数资格

补证 schema 为 `tick_reading_supplement_v1`，字段：

```text
source_sha: 原 reading 字节 sha256
image: 与原 reading image 相等
chains: {chain_id: {
  axis: x|y|z, values_mm: [正段长...], cum_mm: [0, 前缀和...], overall_mm,
  origin_mm, direction: -1|1, qualification: drawing_dimension
}}
primary: {axis: chain_id}
declarations: [{axis, callout_id, quantity: wall_thickness,
                qualification: drawing_dimension, kind: full|half, value_mm}]
```

入口把源缓冲区复制为 bytes，Expression 把操作数复制为 tuple；第二步也复制 bindings/facades/walls 序列，公开 packet 是只读属性，避免普通 list 别名在提交后改变输入。对应强制位点见 `Expression.__post_init__`、`build_packet` 入口、`OpeningReview.__init__` 入口及其 `packet` property。

这是 reading 提交给 correction 的额外**声明证据源**，不是对原 JSON 的改写。`freeze_prototype_supplement(raw, config_bytes)` 对原型已有具名链配置执行此交接：核图像身份、立面方向名及 primary 声明数组，保留原配置全文，再冻结全部链。真实平面使用 `cfg_1f_full.json`；旧 `cfg_1f.json` 不含具名 chains，走 `SUPPLEMENT_CONFIG_MISSING_CHAINS`。函数不从扁平像素值表反造链身份，也不将配置里的墙厚候选自动认成已确认 callout（故原型补证的 declarations 为空）。

节点地址是 `(source_sha, chain_id, domain="node", index)`；段地址的 domain 为 `segment`；声明厚度地址固定 `chain_id="declarations", domain="declaration"`。数值来自对应冻结记录，单位是 mm，经精确转换成为 0.1 mm 整数。资格解析读取补证的 `drawing_dimension` 记录和原图绑定；不是从操作数 role 字符串或同值成员反推。链的位置 = `origin_u + direction * cum_u[index]`，段长不带原点。

信任边界：reading 对“这是图上声明”的转录负责任，第一步模型对“这条边该认它”负责任。哈希不证明 reading 的语义判断正确；本模块验证冻结记录的图身份、引用域、算术及本次选择。本单没有声称抵抗有权替换全部 reading 输入的调用方。

强制位置：[`_chain_records`](../../../../src/agent/correction/tick_claim.py#L158)、[`freeze_prototype_supplement`](../../../../src/agent/correction/tick_claim.py#L189)、[`evaluate.resolve`](../../../../src/agent/correction/tick_claim.py#L234)。`require_chain` 强制正段、零相对原点、节点数=段数+1、总长闭合、每个中间前缀；错误分别为 `CHAIN_DOMAIN_INVALID / CHAIN_SEGMENT_NOT_POSITIVE / CHAIN_TOTAL_NOT_CLOSED / CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM`。

## 4. 运算完整签名

公共 `Expression(operation, anchor, operands=(), direction="positive", thickness_kind=None)`；anchor 必为**一个本图同轴 node ref**，返回值一律是该图局部轴的**位置**。`direction` 为 positive/negative，不从边的 lo/hi 推断。下表之外的角色/基数组合拒绝。

| operation | operands 的精确域/基数 | 公式（u=0.1mm） | 额外条件/拒绝 |
|---|---|---|---|
| `node` | 0 | anchor 位置 | direction 必 positive；thickness_kind 必 None |
| `anchored_sum` | 1..N 个同链连续 `segment` ref | anchor + sign × Σ段长 | 索引必须逐个连续；node ref 冒充段立即 `OPERAND_REF_DOMAIN` |
| `anchored_diff` | 同链两个 `node` ref，顺序为被减/减入端 | anchor + sign × (operand[1]位置 − operand[0]位置) | 差是位移，必须显式加到 anchor；允许有向负差 |
| `axis_half_span` | 同链两个 `node` ref | anchor + sign × (operand[1]位置 − operand[0]位置)/2 | 精确整除；否则 `CHAIN_HALF_SPAN_UNGRID`。覆盖中心3000、链宽900的2550/3450 |
| `axis_half_wall` | 恰一个声明厚度 ref | anchor + sign × half_thickness | quantity 必 wall_thickness；kind 与 thickness_kind 相等。full 除2且精确整除；half 原样。非正/错声明拒绝；半格为 `WALL_THICKNESS_HALF_UNGRID` |

所有 node/segment 的 axis 必须与当前边相同、source_sha 必须与当前原件相同。跨链 anchor 可以作为位置锚，但每个 sum/diff/span 的被求和/差链自身一致，且所有链已经显式变换到同图同轴；不暗假设两条不同链的累计原点都是世界原点。

强制实现为 [`evaluate`](../../../../src/agent/correction/tick_claim.py#L223)，非声明、跨图、错轴、坏 ref 分别走 `OPERAND_NOT_DECLARED / OPERAND_CROSS_IMAGE / OPERAND_FRAME_MISMATCH / OPERAND_REF_MISSING`，不是自动二档。`OPERATION_SIGNATURE_INVALID`、`SEGMENTS_NOT_CONTIGUOUS` 也是输入拒绝；代码调用方修候选或 reading 补证后回第一步。真正“无可指认刻度”的二档由模型 `pixel` 明确裁定。

**硬例**：链节点 `[0,1600,4300,7500]` 的 node1+node2 不属于段长签名，直接拒绝；合法 segment0+segment1 = 4300mm。不能先算成5900再靠区间门蒙混。数学上合法的2550/3450非节点结果由 `axis_half_span` 精确放行，无节点成员检查。

## 5. 模型响应、两档与本次决定

`TickResponse(packet_id, choices: tuple[TickChoice,...])`，`TickChoice(edge_id, action, candidate_id=None, reason)`。Pydantic strict、extra=forbid，提交时从普通字段重验一次；第一步没有 `whole_building_review` 或模型坐标字段。

| action | 结果/责任 |
|---|---|
| select | candidate_id 必为该边候选。代码 evaluate，tier=chain_backed |
| pixel | 模型认定该处无合适刻度；tier=pixel_only；正常低档，无债 |
| pixel_pending_evidence | 必须确有 missing_chains；二档出值，另记本模块拥有的补证债 |
| reperceive | `RETURN_TO_READING`，本次不冻结事实 |

存储/算术为0.1mm；二档读取 `load_core_tolerances().output_precision_m`（当前10mm），记录配置字段名和冻结的实际 u 值，以 Decimal ROUND_HALF_UP 规整。一档在 submit 和 consume 两个位置都直接 evaluate，不经该规整。gt 的1mm不在本模块消费，不改 gt；跨图配对精确相等与 gt 判分容差是不同职责。

`TickBatch(batch_id, record: bytes)` 的 record 持久化 schema、packet_id、source_sha、image_id、generation、完整 response、出口声明、完整 rows。每行保存原像素 pointer/witness、完整选中 Candidate（含运算与操作数）、choice/reason、tier、代码值、debt_id/retired_debt_id。batch_id 是这些规范 JSON 字节的 sha256。`TickPacket` 同时保留原件和补证 bytes；调用方持久化时需一起保存这两份源及批次 record，不能只保存预览坐标。

`TickSession` 是当前批次持有者；第二步保留独立 expected_batch_id。`consume(expected_batch_id, batch=None)` 精确核当前身份、字节、packet及source，按选中表达式或原始像素重新计算，再校完整集合和结果。普通重新 finalize、换 ref/tier/元素、拿另一有效批次替换，均不能通过这个入口。**这个保证只覆盖给定当前持有者和独立预期 ID 的正常 API 消费，不声称 Python 对象不可被反射修改。**

强制位置：[`TickResponse`](../../../../src/agent/correction/tick_claim.py#L122)、[`submit`](../../../../src/agent/correction/tick_claim.py#L426)、[`consume` 身份检查](../../../../src/agent/correction/tick_claim.py#L493)、[`consume` 重推导](../../../../src/agent/correction/tick_claim.py#L503)。

## 6. 回第一步与退债状态转换

```text
候选包(g) --完整同图响应/区间通过--> 当前批次(g)
候选包(g) --区间塌缩或反向--> reconsider --> 新候选包(g+1)
当前批次(g) --第二步推翻/补证--> reconsider --> 旧批次失效 + 新候选包(g+1)
任一重裁 --耗尽 max_rounds--> REGISTER_PENDING_ROUND_LIMIT（无当前有效批次）
```

`reconsider(reason, raw=None, supplement=None, expressions=())` 是具名出口。它先写失效历史、清 current，再增加 generation；即使补证不合法或预算耗尽，旧事实也不恢复。相同源的派生候选在重裁时保留；旧响应因 packet_id 不同拒绝。补证失败时额外保持 `REGISTER_PENDING_READING_INPUT`，旧响应不能重新终结；补证纠正后可在预算内重新构包。默认3轮是执行预算参数，非毫米阈值，调用方可显式调整。

补证闭环由 **reading 提供新增冻结 supplement → correction 第一阶段调用 reconsider → 同图模型重新选择 → submit 新批次 → 代码决定是否退债** 执行。retired_debt_id 只有在同 edge_id、原 source_sha 未变、无缺链、且新选择为一档时写出。补证单纯“有了一个路径”、新输入碰巧同值、或者 source 字节改变而复用索引，都不会自动退这笔债。改变原 reading 字节的重读可以重裁，但原债保留历史待显式重新核身份；本批已实现的是**不改原件的冻结补证**兑现路线。

这不是 `EvidenceDebtV1(obligation=None)` 的描述文本承诺；刻度补证债由 `TickSession` 自己处理。B4/T4-a 的既有 obligation 枚举及 resolver 不被本单扩展或改写。

强制位置：[`区间回裁`](../../../../src/agent/correction/tick_claim.py#L478)、[`retired_debt_id 条件`](../../../../src/agent/correction/tick_claim.py#L464)、[`先失效再重裁`](../../../../src/agent/correction/tick_claim.py#L538)、[`预算阻止旧响应复活`](../../../../src/agent/correction/tick_claim.py#L427)。

## 7. 四分类第二步

`OpeningReview(plan, expected_plan_batch_id, bindings, facades, walls)`。
`PlanBinding` 是 correction 的洞口拓扑决定（源 opening_id、family、wall_id、room_id、host line、floor_origin_u）；数值端点由平面当前 tick facts 覆盖，不采用 caller line 的旧端点。floor_origin_u 必须显式提供，沿墙轴必须和立面方向的 world_axis 相等；有图时镜像/局部正向交给 B4 的声明校验，不默认补 False。墙几何来自既有 projection bridge，不在 A-6 重新造墙。`FacadeInput` 明确四个方向的 session/expected_batch_id 或二者均 None；有图没洞与没图在此分开。

冻结审查输入包含所有平面事实、绑定、墙、四向可用性、所有立面事实、B4结果、全部待配对洞口。模型 `SpatialResponse(packet_id, choices, whole_building_review, reason, reconsider_image_ids=())` 的 choices 要覆盖每个平面洞；每条 `OpeningChoice` 选 pair/register/infer。pair 必须是该方向已有的立面 ID，且不能复用同一立面洞。

| 类别 | 触发及执行 |
|---|---|
| ① | 模型确认身份，两个已确定沿墙区间精确相等；正常配对，z取立面 |
| ②a | 模型确认身份但区间不同；取立面尺寸/沿墙位置，平面墙/房身份保留 |
| ②b | 该方向立面在，模型判缺洞或判不了；只登记，span/z均None，无新增几何 |
| ③ | 明确无该方向立面；模型可纯推断高度和相对楼层窗台尺寸，代码保留平面位置并加楼层原点、规整出口；来源inferred、score_eligible=False。也可登记判不了 |

③ 的 `InferredDimensions(height_mm:int, sill_above_floor_mm:int)` 是**本批纯模型的尺寸假设**，不是第一步认领响应，也不是模型提供世界坐标；代码计算绝对 z 和出口规整。没有默认尺寸、常见尺度表或模数策略。推测正高在出口格点塌缩会具名登记拒绝。这里明确承认第二步③有数值尺寸假设，**不把第一步“无模型坐标字段”夸成整棵第二步响应树无数字**。

whole_building_review=return_to_step_one 时按图 ID 回第一步，当前审查输入和既有结果随批次失效；register 时整栋结果均不可从可计分出口取出。接受的第二步结果通过 `consume(expected_result_id)` 取得，仍逐图核当前批次；`scoreable_openings(expected_result_id)` 只导出当前、非推测且已解决的结果。历史 result.record 可供审计，不是有效性凭证。

强制位置：[`当前批次读取`](../../../../src/agent/correction/opening_adjudication.py#L233)、[`响应全集`](../../../../src/agent/correction/opening_adjudication.py#L262)、[`四分类执行`](../../../../src/agent/correction/opening_adjudication.py#L272)、[`回第一步`](../../../../src/agent/correction/opening_adjudication.py#L248)、[`可计分出口`](../../../../src/agent/correction/opening_adjudication.py#L316)。

## 8. 保证的实际边界

验证证明：本图来源与算术域成立、选择有账、集合完整、当前批次绑定、二档/推测显式、旧批次不能经新消费入口复用。模型是否认对刻度、是否选对墙房或对应洞口，仍是可被重裁的语义判断，不是哈希或整数等式能证明的事实。

本单没有修改 gt、判分器、既有 facts 或签字 fixture；没有声称新增 JSON 会自动被现有评分服务识别。正式接线需消费这里的来源和当前出口语义；对 raw 历史记录绕开 API 的使用不在已验证保证内。跨进程自动恢复当前批次持有者、本楼通用拓扑重检、真实模型端到端质量不作为本单已完成事实。

---

## ⛔ 主控补记（2026-09-05，orchestrator 代为落库，⛔ 施工方正文一字未改）

**施工席位（`gpt-6-astra`）在写完本契约文档、尚未写执行档时退出**，日志原文：
```
ERROR: Selected model is at capacity. Please try a different model.
tokens used 290,564
```
⚠️ **这是新形态**：⛔ **不是额度上限（1308/429），是 provider 容量**。

### 现场如实记录

| 项 | 状态 |
|---|---|
| **实现与测试** | ✅ **7 笔提交全部落地**（`tick_claim.py` 558 · `opening_adjudication.py` 319 · 两份测试 365 行）⭐ **分段提交又一次只让文档受损** |
| **收口契约文档**（本文件）| ✅ 已写完 130 行，**但席位没来得及提交** ⇒ 主控代为落库 |
| **中间三次全量** | ✅ **全绿**：`6242672d` → `3875 passed / 0 failed`（EXIT_CODE=0）· `b7be6a29` → `3876` · `c4b16824` → `3874` |
| ⛔ **HEAD `7b6f5885` 的全量** | **被打断**：`full_suite.txt` 无汇总行、无 `EXIT_CODE` ⇒ **⛔ 不得当作绿**（本项目口径：判跑完看汇总行）|
| ⛔ **执行档（交件）** | **不存在** —— 逐条验收对账、自设同形输入、逐句强制对账**均未产出** |

### ⇒ 本单**未完成**，⛔ 不得合并；缺口两条
1. **HEAD 的完整全量**（带汇总行 + `m.__file__` 落在本工作树）。
2. **执行档**：逐条对派工单验收、§三 四小节自证（含**自设两条同形输入**）、最薄弱一处。

⭐ **中间三次绿是有价值的线索**（说明主体路径没有大面积破坏），但**⛔ 不能替代 HEAD 的读数** ——
HEAD 相对 `c4b16824` 又有两笔改动（`b7be6a29` / `7b6f5885` 之后的收敛），那两笔没有被任何一次完整全量覆盖。
