# F-9 路线②设计交叉审裁决（sol）

> 日期：2026-08-09  
> 受审稿：`AI_agent/proposals/f9_route2_evidence_citation_design.md`  
> 状态：**终审完成**

## 裁决

**REWORK**

路线②的职责分工可以保留，但这份 v1 设计不能据此施工：它会把“模型独立写的 span vs 所引证据的权威映射”这一现存交叉校验改造成“从所引证据派生 span 再与同一证据比较”的恒真式；同时把 git 历史明确限定为 advisory 的近似函数升格为权威。须先补齐独立证据身份门、外部证据 hydration 阶段合同和 current-ring projector，再重排施工与锁的顺序。

## 审阅边界与方法

- 仅审架构设计，不施工；只读核查源码、测试、产物与 git 历史。
- 逐项回答审阅单 Q1–Q6，并按“摘掉对应修法后锁是否仍绿”检查假锁。
- 无法从现有证据判定之处，明确记录所需探针，不用推测补空白。

## Findings

### BLOCKER

#### B1｜派生与校验使用同一条 stroke，现有 `source_geometry_mismatch` 会被消成恒真

- **具体位置**：设计稿 `:11-12`、`:56-60`、`:74-75`、`:128`；现行强制门 `src/agent/correction/window_host.py:722-739, 818-834`；真实反例 `tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json:257-324` 与 `tests/test_f9_window_host_crash.py:173-199`。
- **为什么错**：当前门有两个独立观测量：模型写的 `window.span`（真实夹具中来自正确 plan stroke）与代码对模型所引 existence strokes 做的 world 映射。真实 F-9 正是 `span=[1.24,3.64]`、却把北立面镜像搭档 `North_view/S5` 引进 `existence.source_ids`，所以 `window_host.py:830-834` 报 `source_geometry_mismatch`。若按设计用所引 stroke 自身派生 `span`，同一 interval 随即再与自己比较，这一道检查按构造必过；模型错引镜像搭档会得到错误但内部自洽的 span，并可能落入搭档房间。设计稿 S4 只规定冲突的**出口**，没有产生冲突的独立判据。
- **建议改法**：施工前先把“证据身份校验门”写进设计并冻结输入契约。至少要求独立通道对账：例如以 plan 的 world-along/host stroke 为位置锚，以 elevation stroke 只提供高度/外观（若 elevation 也声明 along，则其确定性映射必须与 plan 锚在命名容差内重叠）；catalog 有独立锚而模型漏引时才按 `model_draw_error` 结构化拒绝并盲重抽，不能让单条 elevation stroke 自证。若上游根本没有独立锚，应报输入证据不足而不是无意义重抽。若业务允许 elevation-only 窗，必须另行定义可独立验证其身份的第二证据/拓扑约束；现有材料不足以证明仅凭一个 source id 可校验“引对了谁”。同时补一把反事实锁：故意把 `W-F1-N-1` 的引用换成 `North_view/S5`，保留合法、可解析的 source，必须走 `model_draw_error`；撤掉新对账门后该锁必须转绿，证明锁到修法。

#### B2｜设计把派生入口写成 `along.source_ids`，现行强制契约却由 `existence.source_ids` 驱动，且 F-16 marker 不能单独完成外部证据派生

- **具体位置**：设计稿 `:25-27`、`:51-60`、`:73-75`；`src/agent/correction/schema.py:41-57, 357-380, 424-457`；`src/agent/correction/parse.py:120-145`；`src/agent/correction/window_sources.py:972-1008, 1055-1084`；`src/agent/correction/window_host.py:767-783`。
- **为什么错**：现行 `_claim_links` 强制每窗有非 assumed 的 `existence.source_ids`，host resolver 也只从 `claim == "existence"` 的 links 选择 plan/elevation branch；它不把 `along.source_ids` 当 span 派生源。设计的“只有 `provenance.along.source_ids`”会先违反现行 existence totality，或者即使保留 existence，也留下“哪一 claim、多个 source 时谁是权威”的未定义行为。更根本地，`CORRECTION_DRAW_DERIVED` 当前语义是 Pydantic 在验证同一 draw 时即可由同 draw 字段填入（F-16 的 `floor_id -> floor`）；`span` 需要 manifest、raw reading、方向 binding 和 ring，schema validator 拿不到这些外部输入。当前 `CorrectedGeometryV3` 又在建立 verified resolver inputs 之前就要求 `span`，而 verified inputs 的 canonical identity反过来包含已经验证的 producer draw，存在未拆解的阶段/身份环。
- **建议改法**：增加明确的“raw draw contract → source-authenticated hydration → full geometry contract”阶段与类型/版本边界，说明 source link 在何时翻译、方向/ring 在何时物化、派生后的 `span` 如何进入 producer identity/hash、envelope pre/post transform 如何重放。不要仅给继承来的 required `span` 打 marker；若沿用 marker，必须扩展其语义与所有消费者并给独立错误码，不能假称与 F-16 同形。并明确一窗一个 canonical `along` authority 的选择/多源一致性规则，同时保留 existence/host claims 的现有总量与权限约束。

#### B3｜S2 提升了错误的函数：advisory 的近似基准被历史明确禁止进入权威路径

- **具体位置**：设计稿 `:21-27, 73-74`；`src/agent/correction/window_sources.py:469-521`；git `99d9521`（`git log -S "never authoritative"` 唯一命中，2026-08-07）；真实 fixture `tests/fixtures/f9_window_host_crash/1_correction/correction_geometry.json:3-13`。
- **为什么错**：git 历史不是“当初没人敢用”。引入提交 `99d9521` 明写 B3：该函数必须 advisory、绝不进强制路径，目的正是保留与 current-ring 权威变换的独立交叉校验。它没有 real `along_origin`，而是假定 facade 沿轴 `lo == 0`，以 elevation 自报 `overall W` 近似成 `local` / `W-local`；方向不可解析、reading 缺 overall、解析失败时还会返回 `None`。真实 fixture 的 elevation `W=15.0`，但 correction ring 是 `[0.12,14.88]`：北向 local `[1.24,3.64]` 的 advisory 映射是 `[11.36,13.76]`，current-ring 权威映射则是 `[11.24,13.64]`。当前安全性来自“提示可有残差，强制门另取 actual ring”，不是该函数精度足够。S2 若按名执行，会把已登记的 0.12 m 偏差与 `lo==0` 假设直接写入 authoritative `Window.span`，并在退台/L 形放大成静默错误。
- **建议改法**：保留 `_advisory_elevation_world_frame` 的非权威身份；权威派生应调用/抽取 current-ring 的 `ViewProjectionFrame` 实现，以明确的 `along_origin` 和绑定身份工作。若希望提示与强制共用代码，只能共享纯公式 `world = origin + sign*local` 与 sign/flip 规范，不能让二者共享不同来源下伪造出的 origin。设计还必须规定缺方向 sidecar、缺 overall、ring 尚未物化时的阶段化拒绝，而非把 `None` 当可降级权威结果。

### MAJOR

#### M1｜S1 的“单一来源”盘点漏掉实际生产者，并且没有定义 mirror 输入归一语义

- **具体位置**：设计稿 `:31-43, 72, 101-102`；`src/agent/correction/facade.py:32-39, 66-103, 166-203`；`src/agent/correction/window_sources.py:664-683`；`src/agent/reading/schema.py:92-102`。
- **为什么错**：除三份 `_BASE_SIGN` 外，`facade.py::_CONVENTION` 还独立持有 axis/base sign，并由 `derive_view_projection_frame` 真接入 `envelope.py:222`；只合三份 dict 后仍有第二规范。且 legacy `facade.py::_is_mirrored` 把字符串 `"true"` 当真，`window_sources._resolve_facade_flip_fields` 却把所有非 bool（包括 schema 合法的 `"true"`）默认为 false。若 S1 只抽 dict/表达式，不先拍板归一层，会把当前分歧藏进“共享 helper”或无意改变 legacy。
- **建议改法**：盘点并合成完整的 gt-free facade convention（axis + base sign + XOR），让 `facade.py`、`window_sources.py`、`facade_applicability.py` 与 judge 只消费该规范；输入归一单列为版本化 adapter：v3 先把 mirror 解析为严格 bool，`unknown` fail closed，legacy 字符串语义用兼容锁固定。不得让 production import `src.agent.judge`。补 4 facade × mirror bool × local-direction 的字面量真值表，另补 `"true"/"false"/"unknown"` 边界。

#### M2｜S1–S4 不是四个可独立验收步骤，且 S3 在 S4 前会形成无身份门的危险中间态

- **具体位置**：设计稿 `:68-77`；现行 parse/build/finalize 顺序 `src/agent/correction/parse.py:79-145`、`window_sources.py:1055-1084`、`finalize.py:94-156`；现行归档出口 `scripts/tool_scripts/run_stage.py:430-452`。
- **为什么错**：S2 未先定义 source authority/多源冲突便不能进入强制路径；S3 的 marker、raw-draw 拒绝、外部证据 hydration、full-model 构造和 identity/hash 必须原子落地，不能只完成一半；而设计把“如何检测/分类错引证据”的 S4 放在移除独立 span 之后。即使最终态打算补门，S3 单独验收时错引证据已可能成为合法、错误 span。S1 可以独立先落，但不是架构推理上必须早于证据契约设计，judge 常量合并也不应阻塞 Q1 门。
- **建议改法**：先加 S0（source authority、独立对账、raw/hydrated/full 三阶段合同、identity/hash 与复杂体量 scope）；再落 gt-free shared convention；权威 projector 先以 shadow 结果运行且保留旧 span 对照；随后先落新冲突检测与 `model_draw_error` 归档锁；最后一次性切换 v3 producer schema/hydration 并删模型 span。安全顺序至少是 `S0 → S1 → shadow projector → S4 detector/routing → S3 cutover`。

#### M3｜目标示例要求模型输出一种生产 prompt 明令禁止且实际 schema 不接受的 `src:` 形式

- **具体位置**：设计稿 `:23, 52-54`；`src/agent/correction/window_sources.py:37, 286-290, 446-461, 916-969`；`src/agent/pipeline.py:446-470`。
- **为什么错**：内部 locator 的真实 wire 是 `src:<64hex>`，hash 由 input id、observation id 和 reading bytes hash 计算；模型看不到也算不出它。模型合法输出是 `<expected_output_id>/<observation_id>`（如 `North_view/S7`），随后代码翻译成内部 locator。设计稿却在“模型输出”中写 `src:<input_id>:<observation_id>:<sha256>`，既不匹配 `SourceLocator` 正则，也破坏 F-7 明确的不可见 hash 边界。
- **建议改法**：把设计分成 model-facing observation reference 与 internal authenticated locator 两层，沿用唯一翻译点 `_translate_observation_reference`；所有目标 wire、错误例和测试都使用真实格式，不要新造第三种表示。

#### M4｜目标 binding 把“每张 view 一个投影”与“所有楼层一个 footprint 指纹/extent”绑死，未过铁律 #6

- **具体位置**：设计稿 `:56-60, 113-115`；`src/agent/correction/window_sources.py:1172-1202`；`src/agent/correction/schema.py:473-484`；`AI_agent/CLAUDE.md §1.5#6`。
- **为什么错**：仿射式本身可扩展，但稿子指定复用的 `VaElevationViewBindingV1` 只有一个 `source_footprint_fingerprint` 和 `along_origin`；现实现还显式要求所有楼层 fingerprint 与 family extent 相同，否则 `direction_binding_ring_incompatible`。退台时同一 facade family 每层可有不同 lo/hi，L 形同 family 可有多段/不同 depth；仅凭一个 along interval 也不能决定是哪段墙。更进一步，退台遮挡是 `along × z` 的二维问题，现一维 visible interval 不能验证 stroke 身份。
- **建议改法**：设计中保留 affine projector，但拆开 view-level datum 与 floor/segment applicability：明确 local-x 的稳定 view datum；对每个 source 绑定 floor/z-band，并让 footprint fingerprint、family extent、segment/depth/visibility按 floor（未来按 z-band）取值。若一张 elevation 跨楼层且共享一个图像坐标原点，origin 应绑定该 view 的显式全局 datum，而不是任选某层 extent；若各层坐标各自归零，则 binding 必须按 floor 分片并版本升级。退台阶段另需 `along × z` 可见域，不能声称现有 V1 binding 原样可长。

#### M5｜§5 的锁没有锁到新生产路径；照现有同名测试实现，摘掉 S2/S3/S4 仍会全绿

- **具体位置**：设计稿 `:90-102`；现有 `tests/test_f9_root_fix_mirror_hint.py:47-146`；现有 convention/parity 锁 `tests/test_c2_vg_visibility.py:237-263`、`tests/test_c2_b5_source_routing.py:179-215, 245-288`。
- **为什么错**：北向非对称数字是必要条件，但稿子没有要求手性锁从“模型可输出、无 `span` 的 raw v3 draw”进入真实 parse/hydration/finalize。仓内同名 F9 锁只比较 advisory catalog 与旧 draw 中模型已经写好的 plan span；即使拟议的权威 projector、`span` hydration 和错引 detector 全部不存在，它仍会绿。S1 的“两个引用同一常量”也可能只证明两个导出名相同，却漏掉仍在运行的 `facade.py::_CONVENTION`，或让 production/judge 一起调用同一个错误 helper。仓内已有 4 facade × mirror × local-direction 的 `derive_view_projection_frame` 真值表，但它只锁一个 helper 且 fixture 的 `lo==0`；source-routing frozen parity 又主要是 South、mirrored South、East。两者都不替代 North/West 的新权威链路，也不覆盖非零 `lo` 或所有 live consumer 的接线。此外真实 fixture 同时含 elevation overall `15.0` 与 ring `[0.12,14.88]`；若“手算值”不先声明采用哪个 datum/对账策略，精确等于、仅重叠、最终采用 plan 值三种断言会锁住三种不同语义。
- **建议改法**：把锁规格改成入口、出口与 neuter 都明确的路径锁：raw v3 不含 `span` → model-facing `view/observation` 翻译 → authenticated hydration → current-ring projection → 独立 plan/elevation 对账 → finalize，并逐窗断言 `(span, room, facade_segment_id/host_zone_id, source audit)`。把正确 source 换成合法镜像搭档时必须产生 typed `model_draw_error` 并走归档；分别旁路 projector、hydrator、对账门或最终写回后，该测试必须至少一项转红。S1 另需 4 facade × mirror bool × local-direction 的外部字面量真值表、非零 `lo/hi`，以及禁止 live consumer 留本地 `_BASE_SIGN`/`_CONVENTION`/flip 公式的结构锁。手算 oracle 必须来自用户已拍板的建筑立面约定、明确的世界/图像 datum 与冻结原始数值，不能由 production/judge helper 生成。

### MINOR

#### m1｜“平面与立面不许分支”混淆了统一接口与不同坐标类型

- **具体位置**：设计稿 `:56-64`；`src/agent/correction/window_sources.py:108-133`；`src/agent/correction/window_host.py:722-745`。
- **为什么错**：plan source 天生携带 world-x/world-y 及墙面法向区间，elevation source 携带 local-along 并需要 binding；前者还须按 facade 选择 x/y 并做 plane check。两种 discriminated source 不可能在无类型分派的情况下读取同一字段。“无分支”若照字面执行，只会把分派藏进 helper 或丢掉 plan 的平面约束；真正要消除的是重复的立面仿射公式，不是合法的 channel dispatch。
- **建议改法**：定义一个穷尽分派的 `project_source_along`（名称示意）：plan adapter 产出已在 world frame 的 canonical interval 并保留 plane evidence，elevation adapter 唯一调用 authoritative affine projector；下游只消费统一的 projected evidence 类型。规范写“一处公开投影入口、一份 elevation 公式”，不要写“没有分支”。

### NIT

_无。_

## 六个必答问题

### Q1：模型引错证据靠什么检出

**结论：设计稿当前没有这道门，并且会消灭一道现存、已由真实事故证明有效的交叉校验。**

现行链路不是靠 advisory 强制：`_advisory_elevation_world_frame` 只把近似 world interval 写入提示词。真正的门在 `resolve_window_hosts`：

1. `window.span` 是模型独立写入的 world interval（`schema.py:207-215`）。
2. resolver 从 `existence.source_ids` 取 source；plan 直接取 world interval，elevation 经 current-ring binding 映射（`window_host.py:722-739, 767-783`）。
3. 任一所引 source 与模型 span 无正重叠，即报 `source_geometry_mismatch`（`:824-834`）。

真实 fixture 正好证明其分辨力：`W-F1-N-1` 的模型 span/plan 声明是 `[1.24,3.64]`，但 existence 同时错引 `North_view/S5`；最终四窗均以 `source_geometry_mismatch` 被拒绝并归类为 `model_draw_error`。这不是理论上的冗余检查。

路线②若直接以被引 stroke 生成 span，再让同一 source 参与上述 overlap 检查，二者同源，模型错引时也自洽；所以设计稿 `§7` 的“引的证据对不对 = 代码可校验”目前是无机制支撑的结论。缺门应是**独立来源的身份对账**，首选 plan world-along + host/room 锚对 elevation 派生结果；不能把“派生值落在某个合法房间”当身份正确，因为镜像搭档本身就是合法房间。只有在两个独立证据一致后才能写 authoritative span；不一致时结构化拒绝。缺锚若因模型漏引而 catalog 中实际存在，才归档重抽；若上游没有可用独立锚，则应报输入证据不足，现有证据无法支持自动判定。

### Q2：`_advisory_elevation_world_frame` 能否提升为权威

**不能按设计稿 S2 所写直接提升；advisory 标记有明确、可追溯的正确性原因。**

`git log -S "never authoritative" -- src/agent/correction/window_sources.py` 唯一命中 `99d9521`；blame 显示函数、注释与标记同一提交引入。提交说明刻意避免“同义反复”：提示侧用 reading 自报 overall width，强制侧仍由 `materialize_current_ring_va_elevation_bindings` 从 correction draw 的 actual ring 独立重算 `along_origin`，因此交叉校验不退化。它同时登记了 `lo == 0` 只是假设、真实 fixture 已有 `lo=0.12`、退台/L 形会静默误导。

当前真正可作为权威基础的是 `window_sources.py:1144-1202` 的 current-ring binding 加 `window_host.py:722-739` 的 `ViewProjectionFrame` 映射，不是 `_advisory_elevation_world_frame`。但前者当前也有适用域限制：它要求所有楼层 footprint fingerprint 与 family extent 完全一致（`:1177-1189`），否则报 `direction_binding_ring_incompatible`；这需要在 Q6 的扩展设计里解开。

“谁会因为以为它仍只是提示而算错”的直接答案：任何把 elevation overall width 当 actual world extent、或允许 facade-axis `lo != 0` 的调用者；现有 F9 真实 fixture 已给出 0.12 m 实例，未来 per-floor footprint / 退台则会让同一错误不再只是小残差。

### Q3：S1–S4 的分解、顺序与缺步

**结论：S1 可独立做，但“必须最先”只是施工偏好；S2–S4 的分解与顺序不成立。**

- S1 合并规范源是好事，适合作为独立、行为不变的先行重构；但范围必须含 `facade.py::_CONVENTION`，并冻结 mirror 归一语义与 import 边界。
- S2 不能提升 `_advisory_elevation_world_frame`；应新增/抽取带 actual ring datum 的权威 projector。最安全的独立验收形态是先 shadow 计算，继续保留模型 span，度量二者偏差。
- S3 不是“打 marker + strip”即可。F-16 的 marker 由同一个 Pydantic draw 内部即时派生；本案需外部原始 reading/manifest/binding，必须新增 pre-hydration wire 或等价阶段。marker、raw input 拒绝、hydration、full schema、producer identity 与 legacy scope 需原子验收。
- S4 不能排在 S3 后。先有独立证据冲突 detector 与 typed routing，才可移除旧交叉校验。现有 `run_stage.py` 已有 `WindowResolverInputError` / `WindowHostResolutionError` 的 `model_draw_error` 归档出口，可复用，但新 detector 与错误码仍须设计并锁住。

至少缺两件稿外工作：① source authority + plan/elevation 独立对账规则；② raw draw → authenticated hydrated geometry 的阶段/身份合同（含 hash replay、envelope pre/post ring）。建议顺序见 M2。

### Q4：锁是否有分辨力

**结论：§5 的方向正确，但规格不足；北向真实数字本身不构成路径锁，至少有三种假绿。**

1. **手性锁会锁错层。** 现有 `test_f9_root_fix_mirror_hint.py` 已用同一批 North 真实数字，且是手算、非对称、能区分镜像搭档；但它只调用 advisory catalog，并拿旧 draw 的模型 span 当独立 oracle。完全摘掉未来 S2/S3/S4，它仍然绿。合格的新锁必须从模型真实 wire（无 `span`）进入新增 hydration，并穿过 finalize；正确引用逐窗落到正确 room/segment，错引合法搭档则结构化拒绝。
2. **North 一例不足以锁 convention 全域。** 它能抓本次 base `-1` 缺陷，却抓不到 axis-y 的 West、mirror 与 `image_right_to_left` 双 XOR 抵消、或错误的 `along_origin`。仓内 `test_view_projection_frame_double_flip_xor_truth_table` 已覆盖 4 facade × 2 mirror × 2 local-direction，可作为基础，但它只直测一个 helper，且 rectangle 从零起点。仍需 North + West 新权威路径、South + East 正向控制，并把 extent 改成非零起点，否则接线缺失或 `lo==0` 错法仍绿。
3. **S1 双锁的逻辑只在 oracle 独立时成立。** “同一对象/同一常量”锁只证明 identity，不证明所有 live consumer 真在用它；“等于手算值”须由 `facade.py:9-17` 所记、用户已拍板的建筑约定，加上明确的 local/world datum 和字面量输入独立推得。不得从 production helper、judge helper、其 hash 或其输出回填 expected。还要对每个 live consumer 做 neuter：恢复一份本地 dict/flip 后，结构锁或真实路径锁必须红。
4. **逐属性要求尚未落成可执行 oracle。** 不能只比窗集合或投影区间集合；要按 window id 断言最终 `span`、`room`、`facade_segment_id/host_zone_id` 与 source audit。否则两窗互换仍可能集合等价。

真实 fixture 的 `15.0` vs `[0.12,14.88]` 还要求拆成两把锁：一把精确锁 current-ring projector 的数学结果，另一把锁其与独立 plan anchor 的容差/冲突策略。只断言“有重叠”会让错误 origin 躲在宽窗里；只断言等于 plan span 又会在未定义 0.12 m reconciliation 前擅自决定权威。

### Q5：三条未决

#### 5.1 `source_ids` 粒度与缺失策略

建议 **fail closed，不做隐式平面回落**：

- v3 producer contract 将权威位置 citation 设为必填、非空，并定义 exact-one authority 或明确的 plan-anchor + elevation-detail 配对。
- 若 catalog 中存在合格 source 而模型漏引，归类 `model_draw_error`，结构化拒绝、归档、盲重抽。
- 若上游根本没有可形成独立身份锚的证据，记录“输入证据不足”的业务阻断；重抽模型也不能凭空生成证据。它不是 invariant tamper，但也绝不能猜最近窗、借用 existence/host claim，或偷偷回落到未被模型指认的 plan stroke。
- 只有当模型**明确把 plan stroke 指认为 along authority** 时，plan 路径才可退化为恒等映射；这不是 fallback。

#### 5.2 legacy v1/v2

按 schema 版本保持 v1/v2 的 required model-authored `span`、只让 v3 走新 hydration，**本身不构成第二份 v3 实现**；这是版本化兼容边界，仓内 `finalize.py:98-115` 已有“legacy 禁 verified inputs / v3 强制 verified inputs”先例。条件是：

- override 只落 `WindowV3`，base `Window` wire/serializer 字节不变；
- legacy 不新增任何另一套 local→world projector，不复用 v3 错误码假装经过认证；
- 给 v1/v2 schema、parse、serialize 与历史 artifact byte-parity 加 scope 锁；v3 则必须只有一个 projector。

#### 5.3 judge 权属与隔离

用户已许可改 judge 侧常量；从现有架构看，共享**无 case/GT 数据的规范函数**不会让生产在运行时影响 judge。仓内 W5 已有同类先例（production 与 judge 共享 gt-free orthogonality yardstick），B5 纪律也允许 judge import production helper 做 parity、严禁反向 import。

但设计需写清依赖方向：推荐 `production → gt-free shared convention ← judge`（或 judge 单向 import gt-free production helper）；shared 模块不得 import judge/gt/test_baseline，production 继续静态保证零 judge import。judge-owned、预先冻结的 binding 字面量/GT 仍必须独立存在，且用手写 truth table 校验 shared convention；否则两端一起改错时 oracle 会失声。只满足这些条件，S1 才是“消除规范漂移”，不是“让生产结果喂给判卷”。

### Q6：复杂体量可扩展性

**结论：公式可长，稿中的 binding/定义域不能原样长。**

`world_along = along_origin + sign * local` 是一维正交投影的正确仿射形式；L 形并不会让 x/y 坐标映射本身失效。但必须区分“坐标投影”与“宿主段身份”：L 形同 family 多段可有重叠投影和不同 depth，派生出 world interval 后仍须结合 floor、segment、depth 与 visibility 决定宿主，不能靠 along 单值完成身份校验。

`along_origin` 只有在 local-x 的 datum 被明确规定时才良定义。当前实现用每层该 family 的 min/max extent 推 origin，并以“所有层 extent/fingerprint 相同”门把歧义挡掉；退台一松门就出现多个候选 origin。因此未来有两种合法合同：

1. 一张 view 有显式、全楼共享的投影 datum，则一个 view-level origin 可复用，各 floor 另持自己的 segment/visibility binding；或
2. local 坐标按楼层/z-band 重置，则 origin 与 fingerprint 必须按 `(input_id, floor_id/z_band)` 分片。

设计稿两者都未选，却直接指定单个 `VaElevationViewBindingV1`，不满足铁律 #6。另据现有 C3 风险登记，退台可见性会从一维 along skyline 升为二维 `along × z`；即使 span 投影公式保留，证据适用性/错引检测也必须升级。修订稿应明确这个版本接缝，不要求本批实现复杂体量，但不能把 shared-footprint V1 当最终接口。

## 自主发现

- **M3（清单外）**：设计给模型的 `src:<input>:<obs>:<sha>` wire 既不是模型可见格式，也不是内部 locator 的真实格式；这是独立于六问发现的协议错误。
- **M1 的额外一半（清单外）**：实际还有第四份生产 convention `facade.py::_CONVENTION`；并且 schema 合法的字符串 `mirrored="true"` 在 `facade.py` 与 `window_sources.py` 被相反解释。合并常量前必须先解决这项输入语义，不然“单一来源”会把哪一边的行为固化仍属偶然。
- **m1（清单外）**：plan/elevation 应共享 canonical projector API，但不能抹去二者的坐标类型与 plan plane evidence。

## 建议的验收门

修订稿至少应把以下验收条件写到可执行粒度：

1. **契约门**：冻结 model-facing raw v3 schema（无 `span`、引用为 `view/observation`）、hydrated/full schema、唯一 source authority/多源一致性、canonical hash 与 replay 顺序；缺失、重复、冲突 evidence 均有明确 typed 分类。
2. **独立身份门**：正确 plan anchor + elevation source 接受；把 elevation 换成可解析的镜像搭档后拒绝为 `model_draw_error` 并归档重抽。删除/旁路对账 detector 后此锁必须失败。
3. **投影门**：4 facade × mirror × local-direction 的字面量真值表；North/West 真实手性路径；`lo=0.12, hi=14.88` 一类非零 origin；advisory `W=15.0` 与 current-ring authority 明确得到不同结果，防两者重新同源。
4. **接线路径门**：raw no-span draw 走真实 parse/hydration/finalize，逐 id 断言 span、room、segment/host zone 与审计引用；分别 neuter projector、hydration 写回、host resolution 后都能转红。
5. **隔离与单源门**：production 不 import judge/GT；shared convention 不 import case/GT；所有 live production/judge consumer 不再声明本地 sign/flip 规范；judge 继续持有独立冻结的 expected truth table。
6. **兼容/扩展门**：v1/v2 历史 wire 与 canonical bytes 不变；v3 只有一份 projector。不同 per-floor footprint 在当前版本至少 typed fail closed，并由版本化 floor/z-band binding 接缝承接，不能偷偷取第一层或 overall `W`。

## 核查记录

- 已按要求依次阅读审阅单、受审设计稿、`AI_agent/CLAUDE.md §1.5`。
- `git log -S "never authoritative"` 与 blame 均把 advisory 边界追到 `99d9521`；该提交说明明确要求提示换算与 current-ring 强制换算保持独立。
- 只读运行 `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q tests/test_f9_root_fix_mirror_hint.py tests/test_f9_window_host_crash.py tests/test_c2_b5_source_routing.py`：**41 passed in 12.22s**。这只证明当前基线与上述代码阅读一致，不为尚未施工的设计背书。
- 另单跑既有 4 facade × mirror × local-direction truth table：**16 passed in 8.39s**；它证明 `derive_view_projection_frame` 当前字面量约定被锁，但不证明拟议 shared convention 的所有消费者接线或新 hydration 路径。
