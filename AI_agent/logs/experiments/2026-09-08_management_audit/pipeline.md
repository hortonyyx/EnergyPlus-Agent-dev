# 管线与架构管理文档审计

审计日期：2026-09-08。代码基线：`461dfc98`，审计开始时管理文档 HEAD：`1ce6df37`。本报告只读源码与已有产物，没有调用计费模型、运行新 case、修改 GT 或业务代码。文档的历史执行结论不能自动当作本次验证结果。

## 阅读覆盖与逐文档处置

以下文件均逐段全文阅读；不是只搜索关键词或读标题。接手前两份长稿由历史审计代理转交本代理，避免重复阅读。

| 文件 | 判定与建议处置 | 应保留的内容 / 应纠正的问题 |
|---|---|---|
| `architecture/as_drawn_layer_contract.md` | 完整归档，现行内容归入证据与评测说明 | 保留观测/声明/假设区别、像素回查能力边界、不得以缩分母获益。删除当期六审、签字与首考作为当前开工闸门的表达。文中 sm25 facts 100 边、三条 ring loss 不是当前存货。 |
| `architecture/gt_and_pipeline_flow_map.md` | 原稿归档，改为简短现行事实图或跳转 | 最有价值的是生产链与 GT 链分离、同源事实可派生多个答案。所谓 as-drawn 零接线、AnswerCompiler/多形态证据/多层未实现等多处已过时。GT 冻结 facts 的统一消费仍未全部兑现，不能因为类已存在就标全链完成。 |
| `architecture/gt_revision_ledger.md` | 原稿归档，必要约定合入证据与评测说明 | 保留 as-measured、修订记录、as-signed 的分离及人工签字不得伪造；状态“未施工”错误。代码实现与 staging 已存在，正式 GT 晋升尚未带 facts。示例里的三种 verdict 也不是当前 schema 完整枚举（还有 unsigned）。 |
| `architecture/harness_versioning.md` | 原稿归档，现行改为轻量能力证据记录 | 保留能力范围必须区分建筑形状与图纸画法、结果可追溯到代码/工具/模型/输入。删除固定六步晋升循环、必须先强模型后降档、探索工具不得进 src 等管理硬门。探索实现可入库，正式能力声明需要相应证据，是两件事。 |
| `architecture/harness_versions.yaml` | 归档历史手账，不应继续称机器清单 | 实际 YAML 语法错误：第 10 行开始 list，却在第 36 行同层写 candidates mapping。`yaml.safe_load` 已实测失败。未找到 src/scripts 对该文件的消费者。旧 v0 能力状态不足以概括 9 月代码。 |
| `architecture/judge_grade_model.md` | 原稿归档，保留短技术入口至现行评测说明 | 保留产品按自身坐标绘制、GT 作参考/缺失注记、容差只影响颜色不搬动产品。旧矩形 scorer 不认 C2 的整体判断已经过时；现有 segment scorer 与 capability dispatch。新 as-drawn 图与 legacy/correction 图不同，不能再称全管线唯一三色模型。 |
| `architecture/multimodal_bim.md` | 作为方向文档保留并对齐当前范围 | 共同轻量 BIM、适配器分开、GT 隔离、来源与假设、短分支早集成均适合。必须保持“建议/未实现”，不能写成现有任意输入降级能力。 |
| `architecture/pipeline_stage_contracts.md` | 保留为现行实现主入口，补齐下面核查结果 | 初步精简方向正确，但需说清 flow 的 0_reading 不生成 reading，3 阶段重建/序列化，MEP 中 HVAC 实际由代码覆盖，以及真实 case 27 zones 尚未证明房间完整。 |
| `architecture/reading_pipeline_architecture.md` | 原稿归档，重新写短的图纸适配架构 | 保留量具/感知/装配职责、SOP 与画法案例分开、固定编排可逐步演进为模型驱动。删除零接线等旧状态及跨家族审批前置；“模型从未真跑”“只支持一种图”等只能归属于具名历史实验。 |
| `guides/new_case_guide.md` | 保留并补真实准备入口与失败定位 | flow 命令只会接收已产出的 reading；指南不能让人误以为原图一键起跑。说明独立 run、输入来源、输出/NA/停止原因。 |
| `guides/reading_correction_split_guide.md` | 保留短分工说明或合入 reading 架构后留跳转 | 目前短稿方向正确。明确两个证据档位合法，correction 整合尺寸证据与跨图空间关系；“缺图允许推断”是当前目标，不代表严格 CLI 已支持。 |
| `archive/2026-09-08_pre_takeover/guides/reading_correction_split_guide.md` | 历史原稿保持归档，不恢复其管理效力 | 1306 行含多轮相互覆盖的“唯一口径”，真正末次状态须追到最后。阅读提炼见后文。 |
| `archive/2026-09-08_pre_takeover/architecture/pipeline_stage_contracts.md` | 历史原稿保持归档，不恢复其管理效力 | 364 行混有 6 月设计、“应补”、已实施补记、全阶段审批与模型流程。保留归因、源几何与下游装配边界、独立 run 概念，实际能力以当前源码核查为准。 |

## 当前真实入口与阶段接口

| 阶段 / 入口 | 实际行为 | 核查位置 |
|---|---|---|
| CLI `flow` | 有阶段 attempts、accepted 状态、检查和可选 judge/几何确认；不是读取原图后自动完成所有步骤的统一模型产品入口 | `scripts/tool_scripts/run_stage.py:3208` |
| `0_reading` | 明确 MANUAL：读取已存在的 `0_reading/*_view.json`，归并输出并做契约、标定等检查；此函数不调用模型。没有产物会报 `reading.present` 错误 | `scripts/tool_scripts/run_stage.py:339` |
| reading 工具箱 | 已有 `pens/ruler/faces/pairs/gaps/build` 等函数；由调用者准备配置、perception 和工具顺序。工具箱存在不等于通用 reading agent 已完整接入 flow | `scripts/tool_scripts/reading_toolbox.py:58`、`:144`；`src/agent/reading/as_drawn/as_drawn_v2.py` |
| correction 路由 | 依据冻结 view manifest 与产物 classifier 分派，区分 legacy / as-drawn。无 manifest 的旧 run 走 legacy。as-drawn 平面没有立面、混合 legacy/as-drawn、未知或缺失产物会明确拒绝 | `scripts/tool_scripts/run_stage.py:417` |
| 产物契约 | legacy ReadingView 为 CONSUME；as-drawn plan v2 和 elevation v0 为 ADAPT；as-drawn plan v0 仍 KNOWN_NOT_CONSUMED。不是所有名字含 as-drawn 的格式都已支持 | `src/agent/reading/vector_contract.py:253` |
| 单图证据链 | 冻结来源字节→适配→编译→决策 packet→模型决定/固定响应→有限轮执行→成功后投影。默认 round budget 3；固定响应可离线证明接线，但不能报告为模型成绩 | `src/agent/pipeline.py:1058`、`:1230`；`src/agent/correction/decision_executor.py:524` |
| 多层装配 | 立面证据派生楼层高度；按 plan 顺序逐层运行 evidence-chain；核对 plan 数量和楼层梯数；对齐 footprint 与跨层切线；组装 `CorrectedGeometryV3` | `src/agent/pipeline.py:1879`；`src/agent/correction/multifloor.py:548`、`:900`、`:1023`、`:1151` |
| 窗构建与校正归档 | CLI 先多层校正，再 `populate_as_drawn_windows`，生成窗账和 verified inputs，再 finalize、check_correction、交 StageRunner 写 attempt | `scripts/tool_scripts/run_stage.py:546`、`:638`、`:689` |
| `2_modelling` | 接受经校正的几何和窗归属证明，调用 `materialize_kernel_geometry`，产 `BuildingGeometry`；build 内已包括造面、切配和窗挂载 | `scripts/tool_scripts/run_stage.py:948`；`src/agent/pipeline.py:2538`；`src/agent/geometry/build.py:201` |
| `3_split_pairing` | 当前 CLI 再从 accepted correction 调 `build_geometry`，序列化 specs，并与 2 阶段磁盘几何比较；不是从 2 阶段未配对面继续只做一次切配 | `scripts/tool_scripts/run_stage.py:977` |
| `4_mep` | 输入 zones、所需 constructions 和 testdata，模型产非几何语义。`hvac_specs` 始终被代码按 zone_names 替换，并合入保留 schedules，不全由模型控制 | `scripts/tool_scripts/run_stage.py:1035`；`src/agent/pipeline.py:2481`；`src/agent/intakeoutput.py:26` |
| `5_intakeoutput` | CLI 要求 RunManifestV2、accepted correction、accepted MEP；处理朝向，核对 accepted 字节，构建 coordinate snapshot，装配 IntakeOutput 与 sidecar | `scripts/tool_scripts/run_stage.py:1116`；`src/agent/output_coordinates.py` |
| `run_pipeline` / `run_pipeline_artifacts` | 函数入口仍有 legacy ReadingView 加载与旧 correction 路径；不能把 CLI 新链支持范围套到它们。内联函数路径与 CLI 多次重建的行为也有差别 | `src/agent/pipeline.py:2637`、`:2657`、`:2730` |

`CorrectedGeometryV3` 已有每层 footprint、polygon cells、windows、facade segments、来源字段、core stamp 和 north_axis；但它仍围绕仿真几何与旧校正契约组织，不能自动当作未来完整通用 BIM。类型入口：`src/agent/correction/schema.py:446`。`BuildingGeometry` 是 zone/surface/window 几何表示：`src/agent/geometry/modelling.py:112`。

`IntakeOutput` 仍为 11 字段：building、site_location、zone/material/schedule/construction/surface/fenestration/hvac/people/lights_specs。多数 specs 是下游任务文本，不是可编辑 BIM 的完整结构化模型（`src/agent/state.py:28`）。

### 已有检查与没有被检查的范围

- flow reading 走 `check_reading_stage` → `check_reading_product`（`src/validator/checks/view_manifest.py:31`、`:78`；`reading_product.py:43`）。as-drawn 会记录 legacy 检查为 NA，并检查契约、标定可用、尺寸存在与闭合。不能把这些 NA 算作相应能力通过。
- 历史 as-drawn 十一道像素自检仍在 `src/validator/checks/as_drawn.py:800` 的独立 `main(doc_path,cfg_path,out_path)`，本次未找到 src/scripts 的生产调用；它不是 flow reading 默认自动执行的十一道检查。
- 几何 `build_geometry` 已执行 `pair_surfaces`，并检查窗不能静默丢失（`src/agent/geometry/build.py:235`、`:259`）。v3 还要求窗归属证明，即使零窗也需要；这是现有 API 事实，不能由管理文档暗中取消。
- 当前最短边检查 `_MIN_EDGE=0.10` 来自项目 `src/validator/interzone.py:64`、`:127`，不是本报告验证出的 EnergyPlus 普适物理下限。报错文本“EP may segfault”属于当前代码措辞，本次没有运行 EP 验证该因果。
- 旧文中的“确定性就是正确”“任何确定性检查都不能看出走廊幻墙”等绝对句不宜保留。确定性只意味着给定输入可复现；规则覆盖和建筑正确性仍需分别验证。

## GT 与评分链事实

1. `AsMeasuredV1`、修订台账、`AsSignedV1` 和重放校验都有代码。`src/agent/judge/gt_revisions.py:169` 为 RevisionV1，`:445` 为 derive_as_signed，`:656` 为 verify_as_signed_reproduction；暂存读写见 `gt_facts_staging.py:251`、`:277`。
2. `AnswerCompiler` 已实现 A 全轴线与 B 外皮形式（`answer_compiler.py:100`），compile/reproject/reading_exam/clear_span_table 都存在（`:365`、`:371`、`:395`、`:412`、`:435`）。旧文“未实现”应纠正；也不能因此宣称正式 GT 全链已采用它。
3. `promote_gt_v3` 仍复制 gt.json、renders、五份 review 文件和源输入，没有复制 facts 三件套（`gt_promotion.py:121`、`:158`）。异常路径只清正式 GT destination 的代码仍存在（`:170`）；本次未故障注入，不把历史 F-128 的全部后果当作新实测。
4. 实际 `case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/` 有三件套；`gt/sm25-L_anchor/facts/` 不存在。当前 facts 两层边数 91+88=179，墙数55+53，boundary_ring_losses 两层均0；revisions 为空。旧文100边、25 rings、3 ring losses等均属于旧存货。
5. reading 新评分已经接上 CLI：`run_stage.py:2352`、`:2426` 调 `judge/as_drawn/flow_wiring.py`。plan 从 request 哈希匹配的已签字 DXF 重算 denominator（`flow_wiring.py:162`、`:172`）；elevation 从 GT 派生 targets（`:194`）。所以“没有评分消费者”错误，但“所有评分已经由 frozen facts 统一派生”也错误。
6. C2 segment 评分与 capability 分支已经存在：`judge/segment_score.py`、`judge/reading_typed_score.py`、`judge/score_schema.py:1490`。旧“judge 对 C2 零感知 / 无法显式 NA”不能继续作为当前事实。
7. 图层颜色与容差值应按具体 scorer/config 解释。旧 judge_grade_model 中绿色/橙色/红色规范主要描述旧图与 correction 图；as-drawn reading 的漏画/多画/答案留白图采用另一套语义，不能强行合并。

## run_win_e2e 当前证据

证据根：`case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/`。直接读取各阶段 `attempts/001/checks.json` 与校正 output，未执行新推理。

| 阶段 | 已有检查结果 | 能说明什么 |
|---|---|---|
| 0_reading | 25 pass / 132 not_applicable | 已有六视图产物被接收；不是132项通过，更不是本次自动识图成功。 |
| 1_correction | 11 pass / 6 not_applicable | 已有2层、27 cells/zones、31窗的v3校正产物和窗归属检查。 |
| 2_modelling | 4 pass / 1 fail / 1 not_applicable | 已造出27 zones、208 surfaces、31窗；两张短边面触发 pairing gate。 |
| 3–5 / EP | 未发现相应完成 attempt checks | 不能称整案完工或已仿真。 |

具名失败：`Z04_Ceiling2` 与 `Z20_Floor1` 的 shortest edge 约0.0650m，小于当前0.1m守卫。几何已经产出，停止在检查；这与“今天没有推进任何 case”在感受上相符，但实现事实应写成“已有中间几何，贯通仍未完成”。

另一个需要保留的完整性风险：该run为27 zones，而现行 sm25 GT为29 zones。`correction.zone_count_tripwire` 的证据是 `actual=27, expected=null`，因此 pass 不能证明房间完整。本次未逐房匹配，不能断言必定少了哪两间，也不能为消差直接改GT。下一真实case工作应把房间对应检查与可查看几何一起做，而不只越过短边门。

## 长历史指南补充发现

- 同一长稿先后出现“唯一口径”“与前文冲突以本节为准”，保留正文再加横幅不能消除误导。它混合了已作废计划、当前产品决定、实现细节、反复审查和试验数据，应整体归档并重新提炼。
- 最后分辨率终裁是 **GT 1mm、pipeline出口10mm、坐标存储/算术0.1mm整数**，不是中途写过的“统一10mm”或“所有数必须相等”。代码已有 `judge/as_drawn/resolutions.py` 的双分辨率声明与量化误差带，但现行正式GT仍有亚毫米值，不能称修正入库已完成。
- 旧8月30日“正交吸附最大10mm且1°”已经再次变化。当前 `tarch_normalize.py:158` 是5°，`:160`明确旧10mm绝对上限退休，按request最薄声明墙厚派生CAP；`:578`以后按角度、CAP和端点锚分档。源码注明9月7日用户授权，此处只记当前实现及出处，不自行恢复旧阈值。
- 用户曾明确要求保留两档尺寸证据：有尺寸链指认时从链或其推导值取数；没有可指认刻度时，像素证据仍是合法低档来源。不能单独复制旧“像素永不作为坐标”绝对句，否则与同文后半段及当前低信息降级目标冲突。
- `paired_faces / solid_band / single_face / axis_trace / ambiguous / non_wall`并非当前六个对等墙类型。后续已修成正向墙声明、面线处置、候选图几类。代码正向声明是 PairedFaces、SolidBand、SingleFace、LegacyWallTrace；`FaceDispositionV1`另表述处置（`correction/evidence_contract.py:270`、`:283`、`:292`、`:369`、`:404`）。
- “旧格式整条拆干净”在9月1日稿曾获授权，但现在代码仍有legacy，当前用户允许按需复用旧资产；不能把旧拆除批次恢复为本轮开工硬门，也不能假称拆除已经完成。
- 旧指南有针对小面的EP历史实验称某些10–60mm面可运行；它不足以证明本次65mm面完全没风险，却足以说明“项目100mm门=EP必然底线”不成立。新文应保留可追溯实验索引，下一步按具体产物最短诊断。
- 图纸尺寸冲突处理、模型推断与用户确认需要按来源说明；旧“所有阈值签字”“每个参数扫描”“所有判据跨家族审”等制度性要求不应被重新带入现行管理体系。
- 旧 stage contract 的独立 run、自包含产物、错误发生处可见、区分代码错误和输入错误有价值；自动judge密度、全套baseline前置、恒定11字段不可演进等属于旧实现/排期，不能变成新多模态产品架构不可修改的边界。

## 建议最精简的现行架构组织

1. `pipeline_stage_contracts.md`：当前入口、阶段职责、生产者/消费者、关键产物、支持范围及代码链接。不要放旧排期与审批史。
2. `reading_pipeline_architecture.md`：图纸证据、两档尺寸依据、reading/correction分工、当前manual起点和接线、朝多模态的适配边界。
3. `multimodal_bim.md`：目标模型与两路输入的共同最小接口、源房间/派生热区、交互修订和缺失说明；保持设计状态。
4. `evidence_and_evaluation.md`：生产与GT隔离、测量/修订/签字、正式与探索证据、GT/评分链当前未连通部分、量化与容差的不同含义。其余旧架构路径留简短索引到归档即可。

进度与case数只在plan或具名实验档维护，架构文档不反复复制滚动数字。源码技术约束说明“当前会怎样”，项目管理约定说明“如何合理推进”；不要把代码中每条历史围栏注释升级成工作审批规则。

## C2 大提案补充：E4 / Va / Vg 全文阅读

三份均在旧提案原路径全文阅读，随后核查对应生产者/消费者；没有按旧稿执行其施工前置或全量测试要求。

| 文件 | 当前实现核对 | 文档处置 |
|---|---|---|
| `proposals/c2_e4_output_contract_spec.md`（980行） | 已有 `OutputCoordinateContract`、accepted correction验证、derive、snapshot、装配/加载接口（`src/agent/output_coordinates.py:124`、`:370`、`:593`、`:697`、`:914`、`:968`）；MEP 0占位门（`checks/mep.py:278`）、Zone归零（`nodes/zone.py:56`、`:77`）、ConfigState/IDF坐标校验（`validator/output_coordinates.py:572`）及Workflow导出门（`mcp/tools/workflow.py:129`、`:311`、`:339`）均有接线。不是“B-O未来再施工”。本次没有重跑EP四变体，不能把旧114面/14区结果当本次证据。 | 原稿归档，当前架构只保留建筑系顶点、EP Relative、Zone零原点与校正朝向来源、legacy边界、sidecar入口。旧 artifact 名 `correction_e4_orientation_v1` 等已演进至B5家族，字段表应链接实码，不重新复制过时strict schema。 |
| `proposals/c2_va_detail_spec.md`（769行） | `facade_applicability.py:387` 已实现七claim逐项适用性；生产端 `window_host.py:1281` 与评测端 `opening_claim_score.py:287`、`:297`、`:303` 都调用它。不能再写“Va施工待排 / B4b以后才消费”。 | 原稿归档；保留 applicability与值正确性/来源不同、plan不受立面遮挡过滤、elevation按可见区间、partial不是固定半分、缺声明不能由产品洗掉GT分母。七claim、严格identity、半开区间具体wire链接源码，通用BIM不必复制整套评分接口。 |
| `proposals/c2_vg_detail_spec.md`（608行） | Vg段派生与可见性已在 `facade_visibility.py:348`、`:420`、`:456`；legacy finalize与新as-drawn finalize均调用 materializer（`finalize.py:161`、`:303`）。不是“只放行细稿未改代码”。 | 原稿归档；保留一个方向可能有多个深度不同立面、hidden段仍保留、建筑系方向与真北不同、Vg几何可见性与Va证据适用性分工。当前正交无洞等假设是已有模块能力边界，不要升成全项目永久上限。 |

这些稿件提供了“为何推进一步需要反复全量”的直接制度证据：E4 §11列12步，随后明确要求“每步先跑本节对应小测试，再跑全量”；Va §13及Vg §13又要求全量、独立交叉复核、严格文件白名单、固定旧xfail集合与zero-golden。该组合把合理的局部契约保护扩大成每批重复验收和权限升级。现行管理应让相关检查与真实产物验证承担改动风险，模型角色切换/收工本身不重跑已通过范围；原稿保留供追溯，不迁回这些制度要求。

## 重建正文复核与新 case 操作事实

全文复核主助手重写的 `Agent.md`、`management.md`、现行 architecture 七份正文、`guides/new_case_guide.md`、`guides/session_entry.md` 和 `capability/README.md`。新体系已明确实现与目标、现行规则与旧稿、工作状态与历史证据的区别，未发现需要停工确认的产品冲突。下列修正建议已发主助手，由其修改正文；本审计不改其他文件。

- 坐标表述应避免笼统称 `CorrectedGeometry`/V3 都是“世界坐标”。E4 输出保留建筑系绝对数值顶点，EnergyPlus Relative、Zone 原点/相对角归零；legacy 的 world 路径另说。
- as-drawn reading 的当前 flow 检查是契约、标定和尺寸链，不能概括为已全面校验观测引用。`src/validator/checks/reading_product.py:43` 的分支把旧字段检查逐项标 NA，来源引用约束还分布在下游证据适配与校正链。
- 查看器应称“离线交互式 3D 查看器”。`scripts/tool_scripts/run_stage.py:1479` 生成 `manual_review/geometry_viewer.html`，静态 HTML 文件不等于没有交互。
- 新 case 原图和声明位于 `<case>/case_data/`，元数据为 `testdata_prompt.json`；reading 产物放 `<case>/<run>/0_reading/*_view.json`。`view_manifest.py:941` 从 case 原始声明与图片生成 manifest；`run_stage.py:3488` 的 `provision CASE RUN` 可以预配，不要求手写 manifest。CLI flow 也会预配。
- 当前 as-drawn correction 要求平面 plan v2 加立面 elevation v0。缺立面报 `ELEVATION_EVIDENCE_MISSING`，夹杂 legacy 或放错槽报 `CORRECTION_MIXED_CONTRACTS`（`run_stage.py:417`）；不能把现有入口说成已经支持任意少量图纸降级。
- `run_config.yaml` 存在时，flow 的 `judge_mode` 来自配置，`--judge off` 可能不会覆盖；配置 scope 也可能将默认 `--to 5_intakeoutput` 改成较早出口（`run_stage.py:3217`、`:3220`）。run/capability profile 同样需和配置核对，不能假定显式 CLI 一律胜出。
- **模型配置接线缺口：** `flow --llm-config` 与 run/case 下的 `llm.yaml` 仅在 `_flow_ep` 解析并设置 `EP_AGENT_LLM_CONFIG`（`run_stage.py:2871`、`:2887`），调用时在前六阶段之后。此前 correction/MEP 通过 `src/agent/llm.py:26` 读取环境变量或全局 `src/configs/llm.yaml`；仅放 run 配置或传该 CLI 参数不能固定整条 flow 的模型组合。当前若需要全链固定配置，应在启动该子进程前设置 `EP_AGENT_LLM_CONFIG`；本轮仅记缺口，没有改配置、业务代码或调用模型。
- 现行评分文档应简述 AnswerCompiler/staged facts 已有、promotion 未复制 facts、plan grade 仍从哈希匹配 signed DXF 编译分母、elevation grade 用 GT targets 的真实状态。保留实现边界即可；case 数量、边数与单次评分不需重复放进架构。

本次复核没有重跑 case 或 pytest。会话入口的 Codex 加载验证由主助手负责，本审计只核对其文字与所述验证范围，没有另行声称验证 Claude 客户端。
