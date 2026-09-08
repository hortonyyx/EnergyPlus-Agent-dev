# proposals / capability 全文与代码核对

审计日期：2026-09-08。审计者：Codex proposal_audit 子代理。任务是清理前的只读审计；本报告是本子代理唯一写入文件，没有修改源码、测试或原技术稿，没有运行测试、完整 case、计费模型或 GT 生成/晋升命令。

## 阅读覆盖与证据等级

原始负责目录共 **43 份 Markdown、22,376 行、1,498,743 字节**。本子代理逐段完整阅读其中 **36 份、14,095 行、998,701 字节**，含全部 8 份旧 capability Markdown 和 28 份旧 proposal。大文件按连续区间读取，工具截断处另行补读，并非只看标题、目录或摘要。重复修订链未再沿引用完整追溯；原稿内包含的修订正文已阅读。源码与测试按每项实现主张查找调用点并阅读关键函数/断言，不宣称通读全仓源码。

另 7 份 C2 大规格由父代理重新分配，本文不冒称读过：`c2_e4_output_contract_spec.md`、`c2_va_detail_spec.md`、`c2_vg_detail_spec.md` 交 pipeline_audit；`c2_b2b_detail_spec.md`、`c2_b4a_detail_spec.md`、`c2_b4b_detail_spec.md`、`c2_b5_detail_spec.md` 交 history_audit。其全文核查见同目录对应报告。父代理新增的 proposals/capability README 与多输入提案不在上述原始计数内，已另读以核对新口径。

文档核对基于接手代码 `461dfc98`，管理整理期间源码未由本审计修改。原稿已按字节存于 [完整原稿](../../../archive/2026-09-08_management_rebuild/original/AI_agent/)。下文“实现”表示源码路径与相关测试断言存在；“测试”表示读过测试，不等于本轮执行通过；历史成绩只按原稿记载，不提升为新实测。

## 应进入当前能力图的结论

1. **已有代码很多，旧提案中的“尚未实现”普遍过期；同时有些严格设计只有类型或枚举槽。** 不能用提案状态、类名或测试总数推断可跑能力。应以真实入口、产物、消费方为准。
2. **图纸原样恢复已能填窗，但门仍缺通用模型。** `as_drawn_windows.py` 由 plan/elevation 观测建立窗；`run_stage.py:626` 在 producer marker 前调用它。未匹配项进入 `unclassified` 等台账。代码没有把全部洞口都转成 BIM 开口，旧“windows=[] 所以整腿无窗”只反映补窗前状态。
3. **F9 引证路线没有完成 live cutover。** raw citation schema、独立方向约定、current-ring projector、六条件 shadow 对账已存在；当前 live legacy draw 仍是 full `CorrectedGeometryV3`，shadow 不写 span、不阻断。S3 active detector、S4 raw→authenticated→hydrated→full 的完整上线不能写成完成。新的 as-drawn 确定性补窗是另一条已接入口，应优先复用，而非被旧 S3/S4 批次牵着走。
4. **typed reading 评分已实现且后来再次改约。** 当前 canonical detector 是 `reading_views_v2`，不是旧提案的 v1。旧 U-10 要求 local_x/mirror 声明不一致即 NA/miss，现代码与测试明确取消这种评分依赖；可信 binding 决定变换。若从旧 2,197 行稿直接复制 U-10，会重新引入已经移除的假漏窗。
5. **数值身份、来源、长度账本、仲裁已有实现，不需重新造。** GT/product 坐标池分开，GT 分母不由产品生成；按来源槽追踪 alias，长度用 exact interval ledger，认证冲突优先于 capability NA。未知 evaluator 的 NA 和运行日志存在。旧独立 sol 稿的“联合 GT/product 坐标池”没有被采用。
6. **朝向和几何能力不能夸大。** `matcher/site_plan` 枚举不等于视图匹配实现。orientation enrichment 消费已有单候选或生成显式 assumed 0，并不负责多源识别融合。C3 退台、挑空、洞、中庭、任意斜屋面仍未由当前契约覆盖；当前 v3 明确要求各层 footprint 相同。
7. **投影有效不证明源房间完整。** projection bridge 的 footprint 与 cells 来自同一墙线 arrangement，铺砌成立是构造结果；漏一堵未观测墙可以合并房间且无 dangling。`completion='complete'` 只表示没有其定义的悬端，不能对外表述为所有房间已恢复。`outer_skin` 是 schema 槽，当前该 bridge 实际只接受 `wall_axis`。
8. **CAD→GT 工具已是可用技术资产，仍不是生产 CAD 模态。** Tarch 已有 cavity/局部墙厚/区划、命名立面、完整 G9、规范化 opening 轮廓、source map、review/promotion 和多层调度。它的 GT 严格拒绝策略不能照搬到“输入少仍输出有用模型”的产品路径。
9. **旧文档的“两条腿”不是本轮两条输入路线。** 前者多指源房间忠实恢复与热区再划分；本轮是图纸输入与带表皮体量输入。保留源房间、源隔断和开口；热区合并/拆分是后续派生，不能先删源几何来换评分或仿真通过。

## 关键源码/测试交叉证据

| 主题 | 已读实现证据 | 解释与限制 |
|---|---|---|
| 当前 reading 契约 | `src/agent/reading/contract.py:24`、`reading_typed_adapter.py:997` | detector 所有者已从 judge 移到 reading，judge 重导出同一对象，产品识别不必 import judge。v2 是 envelope 形状识别，不是强制每个视图完整。 |
| typed plan/elevation | `reading_typed_adapter.py:234/666/1287`、`reading_typed_score.py:1208`、`score_service.py:988` | 明确 affine、单 floor elevation 限制、trusted-only 分母函数及总化边界存在。多平面同 floor 与多 floor elevation 在此旧 typed scorer 有明确 NA 分支，不代表所有 as-drawn 能力相同。 |
| 已撤销的 local-x 门 | `tests/test_reading_typed_scoring_slice0.py:274/309/328` | 改 local_x、mirrored 后行与分母相同；历史 North 窗可 complete。旧稿 U-10 与现实现冲突。 |
| 坐标身份 | `segment_score.py:80/129`、`identity_provenance.py:47/312/780` | 分 `(side,floor,axis)`；merge `1e-12`、split `1e-11` 与直径守卫属于评分表示合同，不应成为产品毫米精度指标或普遍几何容差。 |
| 仲裁与守恒 | `certifier.py:445`、`interval_ledger.py:636`、`segment_score.py:1938` | 请求级冲突/NA 决策、缺 evaluator 日志、Fraction 账本/重复收费检查均实装。旧 `_SUBINTERVAL_SUM_TOL` 与 scalar helpers 仍兼容存在，但生产匹配不用它们作守恒依据。 |
| 评分测试 | `tests/test_judge_arbitration_slice4.py:92/147`、`test_judge_identity_metric.py`、`test_judge_interval_ledger.py` | helper/cache/真实保存的对账 artifact 有断言；本轮未重跑。源码某些旧 docstring 仍说“geometry broken”，不能拿它覆盖现 scoring-identity 权责。 |
| F9 分期 | `correction/schema.py:562`、`parse.py:72/259`、`window_position.py:480/1498` | S0 raw 类型与 S2 shadow 存在；明确说明 live producer 还未输出 citation-v2，不能把有 parser 等同于已上线。`0.300` 现为模块常量并交叉校验，不是独立可调 YAML 字段。 |
| F9 测试 | `tests/test_f9_route2_s2_authoritative_projector.py:187/825/854/1563` | 测试真实入口有 shadow、shadow FAIL 不改变 blocking、六条件已评估；它们不证明 S3/S4。 |
| as-drawn 补窗 | `as_drawn_windows.py:247/423`、`run_stage.py:626`、`tests/test_w7_as_drawn_windows.py` | mutually-nearest 对应、房间/host/evidence 交给代码；引用声明与来源台账要保留。当前造的是 window，未分类门没有被静默变成窗；测试 fixture 的固定 model beat 并非自主全 case 成绩。 |
| bridge 基准 | `projection_bridge.py:809/1172/1200/1248`、`tests/test_w6_exterior_frame_lock.py` | `footprint_provenance='derived_from_walls'`，outer_skin 拒绝；W6 将外墙轴线对到声明的 `t/2` 内缩框，并非实现外皮输出模式。 |
| 楼层/洞限制 | `correction/schema.py:546`、`judge/gt_schema.py:518/524/534`、`geometry/split_pairing.py:73` | v3 同 footprint、GT 无洞；墙按 floor 分组，楼板/屋面相邻层配对。局部水平差集能力不等于通高/洞/退台全链能力。 |
| orientation | `execution/view_manifest.py:428`、`correction/orientation.py:390` | full elevation 仍要求声明 direction token；候选大于 1 或冲突拒绝，0 候选按策略需输入或 assumed 0。未见 MatchedViewBinding 或独立输入 matching producer。 |
| Tarch 主干 | `judge/tarch_normalize.py:1865/1916/2149/2311` | 实际采用 cavity→支撑线外扩，sol WallRibbon exact-cover 主干未采用。面积阈值用于候选分类；房间计数/overlay 仍不能证明语义完整。 |
| Tarch elevation | `tarch_normalize.py:3019/3765/4235`、`gt_extraction.py:635` | 命名视图与 datum 真正被消费；G9 真跑 extract_gt_v3；kind+floor 候选已检查；多层 run_tarch_conversion 已存在。旧“字段无人读取”“只跑 plan G9”已过期。 |
| Tarch 源码边界 | `tests/test_tarch_elevation_must_red.py:179/632/665` | 有两层/28 evidence 与完整产物断言。4 个 elevation 诊断名只注册、不直接 emit；真实错误统一经 `tarch_v3_precondition.context.v3_code`，不能按码表长度声称独立能力。 |
| GT 晋升 | `judge/gt_promotion.py:121`、`tests/test_gt_promotion_path.py` | candidate、review inventory、ack、source hash 等被消费；不改 signed GT 来提高产品分数。严格晋升规则适用于评测答案，不要求每次探索模型先完成签字。 |
| F20 接口 | `execution/validation_run.py:83/95/125/185/368`、`tests/test_c2_b5_artifact_trust.py` | accepted v3 artifact 的 proof 由同一 resolver 取，失败不回落 convenience copy；遗留 v1/v2 另走兼容。信任失败与建模几何失败需要区分。 |
| 尚未找到实现 | 搜索 `src/scripts/tests` 并核对模块列表 | 没有 `role_assignments`、`zonification_output`、`score_geometry_vs_gt`、`MatchedViewBinding` 的生产实现；`window_modules` 仅见测试 manifest 示例，不是知识数据生产模块。不能把缺这些名字等同于所有邻近功能全无。 |

## 28 份提案逐文件处置

下表“归档”均指保留完整原稿与兼容索引，撤出当前任务/规则入口；并非删除已有实现。除两路混合输入与编辑提案外，不建议继续保留一组独立旧“施工基线”。每行的旧角色审批、批次必须、先全量再开工统一由现行 Agent/plan 替代，不逐条继承。

| 原文件 | 实现事实 / 构想边界 | 处置与值得保留内容 |
|---|---|---|
| `as_drawn_window_sources_design.md` | 当时无窗，现补窗函数和 CLI 调用已存在；门仍主要进未分类账。 | 归档；将当前补窗入口、输入依赖、未匹配项写入能力图。保留先 catalog 后匹配、plan 主定位/elevation 高程的分工；不把 31 窗/3 门历史样本数写成通用合同。 |
| `c2_1_facade_matching_plan.md` | 未命名立面 `MatchedViewBinding`、window_modules、完整多源匹配仍是构想；judge score binding builder 已有，旧“无 producer”须分对象。 | 归档；未命名、缺视图、镜像歧义并入多输入提案。宽度只能排 axis，不足分同轴两面；窗布局可辅助，完全对称仍不可辨识。 |
| `c2_2_orientation_input_plan.md` | output relative/north enrichment 已有；输入侧 site plan、北针识别、多源归并没有因此完成。 | 归档；保留 building-axis/true-north 与 per-view registration 分离、observed 0/assumed 0 分离；旧特定 case/批次不是前置。 |
| `c2_b2_detail_spec.md` | strict V3、polygon、floor IDs、feature-state、动态序列化已有；同 footprint 限制仍在。 | 归档已实现细节，当前架构写真实限制。旧“footprint 任意版本不得从 cells 来”与现 bridge 不同；可记录自导出覆盖的证据局限，不用旧禁令阻断现入口。 |
| `c2_bm_view_manifest_spec.md` | typed manifest、inputs/view IDs、observability、source claims 已实现；枚举中的未来来源不代表自动 producer。 | 归档；保留 input identity 与 output ID/GT view ID 不混用、覆盖与缺失证据分开；删除批次交付与全量重复要求。 |
| `c2_full_unlock_design.md` | 是多个已落地与未落地子稿的历史总路线，末尾“解锁”不等于产品全形态能力。 | 归档；按当前真实入口拆成能力表，勿再把 B2→B5→全部历史债闭合当开工门。 |
| `c2_orthogonal_polygon_design.md` | 正交非凸 polygon、显式 footprint 与 bbox 兼容已有；非正交/洞没有自动获得支持。 | 归档；保留 polygon 是真几何、bbox 是摘要、legacy 兼容按实际契约处理的经验。 |
| `c3_direction_exploration.md` | 退台/挑空/中庭/z-band/跨层窗为方向探索；当前 schema/pairing 仍约束。 | 归档；按真实体量样例再排需求。保留 z 区间配对、holes 可能来自退台差集、along×z 可见性与 source identity。撤销先完成一串 C3 负锁才可开 case 的顺序。 |
| `cad_to_gt_extraction_plan.md` | GT v3 DXF 提取和 Tarch 已实现不少；这是答案链不是产品 CAD 入口。 | 归档；保留单位/视图框/来源句柄/规范化/核图；未来 CAD 作为用户输入合法，不能继承“所有 case_data 禁 CAD”的产品禁令。 |
| `correction_projection_bridge.md` | walls→cells、multifloor、后续补窗现已有；此函数内部仍先生成无窗 base。 | 归档；保留 centerline arrangement、同墙 gap 连续、逐条来源、误删墙无悬端反例。新版 completion 不能作完整房间保证；不继承必须先对所有 GT 坐标达标再首跑。 |
| `dimension_basis_and_wall_thickness_direction.md` | basis 与厚度问题真实；现 bridge 只 wall_axis，预留 outer_skin 未实装；W6 外轴对齐不是完整双基准输出。 | 归档；将表面模型、源边界/物理厚度/计算坐标区别写架构。GT 不应被搬进产品定位 authority；容差按用途配置，不把旧 50mm 全局 snap 当核心目标。 |
| `editable_geometry_confirmation.md` | 静态 viewer/确认已有；直接移窗、推墙、自然语言生成源 patch 的编辑闭环未实现。 | 保留为精简当前提案。改权威源模型/新 attempt 后重建，不能只改 snapped convenience JSON；几何核保证格式/拓扑条件，不保证编辑后的建筑语义正确。 |
| `f20_validate_case_v3_proof_design.md` | accepted artifact trust resolver、v3 proof 下传、三消费者已有。 | 归档并在工具指南指向现 loader；保留无未验证 convenience fallback、信任错误独立。无需为了收工重跑旧 L1–L8/full/neuter。 |
| `f9_route2_evidence_citation_design.md` | S0/S1/S2 已有；S3/S4 live raw/hydration cutover 尚无完整路径。 | 归档；保留独立 plan/elevation 证据、唯一 projector、advisory 与 authority 分开、source scope、物理 ID 与模型 alias 分开。旧强制 plan+elevation 齐全仅该严格路径合同，不能升为产品缺输入禁止输出。 |
| `geometry_first_zonification.md` | 确定性几何核已有；perimeter/core、use grouping、源空间切分面积归属的完整 zoning output 没有。 | 归档并分清源模型与下游热区派生。旧两腿不是两输入；不要把仿真用热区覆盖源房间。按用途允许简化，保留来源对应与面积/WWR变化可查。 |
| `gt_promotion_path_spec.md` | review/build/sign/rerun/promote 及 signed inputs 已有，不再是从零任务。 | 归档；保留同候选 hash 的核图与 source/request/inventory 绑定。常规产品运行不要被 GT 人审流程反客为主；助手不得代替人伪造已签事实。 |
| `hard_isolation_direction.md` | staging、工具面、guard、审计已在 execution 实现；目录隔离不是 OS 不可访问的证明。 | 归档；保留 GT 不进被测生成链、输入清单和可审计 run。词法 guard 有误报历史，不能新增一轮安全脚手架作为轻量 BIM 前置。 |
| `j23_geometry_judge.md` | `score_geometry_vs_gt` 未找到实现；现有确定性检查与 viewer 不能写成完整自动 geometry judge。 | 归档；按需补产物检查。房间划分与热区划分分别评价；确定性失败不要无谓重抽模型。 |
| `judge_arbitration_and_provenance_plan_sol.md` | 来源 key、alias、certifier、exact ledger、日志、版本/cache 实装。 | 归档；保留评分不可测≠生产非法、真冲突≠NA、分母/来源独立。17–26 工程日估算、逐锁 neuter、双角色全量、不可半交付批次均不再治理本轮。 |
| `judge_identity_and_metric_plan.md` | 合并后的分池/长度/单向注册是当前 scorer 的技术基础，后又由 arbitration 扩展。 | 归档；架构只保留最终身份与长度度量口径，不把审阅轮次串当今日接口。 |
| `judge_identity_and_metric_plan_opus.md` | 独立选案之一，不能每条都当实施；固定量子格问题与分段数量扭曲均有价值。 | 归档；保留表示误差≠建筑容差、长度权重应对切段不变、extras 单列。浮点范围/1e-12 证明有明确前提，不是对任意建筑坐标的普遍保证。 |
| `judge_identity_and_metric_plan_sol.md` | 联合 GT/product 池与 exact-only 墙比较是旧独立方案；当前分池并有 judge 容差层，不照搬该稿。 | 归档作为未采用备选。保留信息论边界说明、联合切点/分段不改变长度；尤其不能把其 shared producer coordinate_identity 模块名当当前实现。 |
| `reading_typed_scoring_plan_sol.md` | v9 sidecar、totalization、来源分母已有；reading contract 已 v2、U-10 后来撤销。 | 归档；保留缺失/格式错误不缩分母、trusted capability 分离、零观测≠NA、NA不崩探索流程。不要重加 North/West 声明门、旧自动 full+审查暂停。 |
| `role_binding_phase2.md` | room labels 输入已有；确定性锚点→cell 的 `role_assignments` 产物未见。 | 归档；未来语义绑定可复用几何点包含；未知用途与为下游选 office 默认值不同。物性协作者负责接口与默认，勿把该旧阶段当核心几何前置。 |
| `tarch_elevation_spec.md` | 命名立面、datum、结构 opening carriers、完整 G9、kind/floor 匹配、多层支持已落地并后续扩展。 | 归档；保留 raw whole-block bbox 会吃装饰/门扇、单位只换算一次、start/end 内部一致性不证明跨视图真实手性。旧 exact selector/门块112 是 fixture，不是通用固定事实；未发射码不能当完成门。 |
| `tarch_to_gtv3_converter_plan.md` | 合并基线选 cavity 外扩，吸收 sol 七条证据纪律，代码与此主干一致但已多次演进。 | 归档；保留图形导出 proxy 风险、门 bbox≠门洞、局部厚度证据、独立反演、source map、候选不等于人核 GT。 |
| `tarch_to_gtv3_converter_plan_opus.md` | 算法主干采用，但其墙厚范围 fallback、面积阈值的强保证、自由端一律错误等被合并稿修正。 | 归档；不能抄回独立稿被推翻部分。计数/总面积不能保证局部正确；G8 与人审也是针对已建证据的检查，不是“任意天正图错必红”的数学保证。 |
| `tarch_to_gtv3_converter_plan_sol.md` | WallRibbon 全局 exact-cover 主干未采用，来源/厚度/外皮 flood-fill等七项被吸收。 | 归档备选；不要为“补齐旧设计”重写现转换器。保留纯双线在缺证据时不可唯一判墙/窄房间、房间锚点不可从错面自证、CAD 方言与通用产品 IR 分开。 |

## 8 份 capability 逐文件处置

| 原文件 | 实现/经验核对 | 处置 |
|---|---|---|
| `floorplan_redraw_strategy.md` | 历史高保真描摹策略、工具选取与阶段分工；当时为 EP 把门缺口修成连续墙不等于通用 BIM 应丢门。 | 原稿归档，当前方法只保留观察来源/显式推断/尺寸与像素交叉核对；恢复门洞与连通问题进入能力缺口。 |
| `geometry_consistency/README.md` | 墙带/尺寸链/拓扑互校有价值；墙带重叠不必然是错误，也可能是真接头或表达差别。 | 改成紧凑方法页，检查提出可定位候选，不凭单一图形信号断定建筑错。整层有效性与房间完整性分开。 |
| `pipeline_0-5_capability_upgrade_suggestions.md` | 是全阶段改进清单，不是已交付能力；多 agent、视觉反馈、知识表等混杂建议。 | 归档，实际任务只进 plan。运行模型本轮上限 Sonnet、目标档首批参与，不继承旧 Flash controller/固定模型角色。 |
| `reading/README.md` | 是旧专项索引与方法入口。 | 保留精简索引，事实/在做事项不另维护第二份计划；链接代表案例与当前工具，不要求每会话阅读全部历史实验。 |
| `reading/good_reading_implementations.md` | 有用的 case/date/model/tool/input/intervention 证据表；不少 n=1、手工介入或单图，与完整多图自主 case 不等价。 | 精简成历史样例索引，明确人工程度和产物来源。7月 Sonnet 自造 scipy/PIL CV 不应标无CV；Haiku 结果不能省略 pilot 条件。 |
| `reading/improvement_methodology.md` | 多轮真实教训：像素度量与照抄尺寸混淆、二维标定错误被遮、单图 pilot不能预测其他视图、测量自声明不是证明。 | 归档长链，提炼成本/产物可见性/一次一因/目标模型起步的方法。不能从整数坐标断言没量、强求 subpixel，也不恢复高档模型每run人工指导。 |
| `reading/prescan_snapshot/RESTORE.md` | 4 份 Python 快照为曾移除的 prescan/recipe/权限/测试实现，当前不在运行工具面。 | 保留快照原字节，恢复说明改为与当前接口作差分后选择复用。不能整文件覆盖已演进源码；若决定恢复，同步仓库决策即可，不机械要求旧角色审批。 |
| `recognition_modeling_capability.md` | 历史识图/几何/热区再划分方向；几何核已在仓库，“外包+热区”不等于只保盒子。 | 归档并提炼当前能力矩阵。保留 surface 模型、原房间边界、热区作为派生；代码五项绿/EP成功≠建筑正确。 |

## 管理与代码需要分开处理的旧约束

- 文档中的“主控/施工/复核三四席”“必须跨模型/跨家族”“先 tests-only RED、每锁 neuter、每次全量 0 skipped”“待批准不得施工”“每批完停主控”均为历史治理，不继承为新任务准入。已有良好测试/loader 可以继续使用；取消的是反复仪式，不是随意篡改契约。
- 老提案允许的 plan-only/elevation-only、F9 严格要求双源、后来的 as-drawn 双源造窗是不同路径/版本，必须标明范围。当前目标允许输入不足时显式默认/推断出粗模型，不能拿旧严格路径的拒绝合同否决目标。
- `tests/test_gt_discipline.py` 仍检查 case_data 中零 DXF/DWG。这是图像评测阶段防答案泄漏的代码事实；未来真正接生产 CAD 输入时应将用户模态输入与 GT 资产分开，并修改相应断言，不能默认所有 CAD 都是禁品。本轮不改代码。
- `projection_bridge` 的 completion 名称容易被误读；当前文档应明确其局部定义。若将来产品 UI 展示“完整”，需有源房间/缺失证据层定义，而非复用该枚举文案。本轮不追加新门。
- 独立方向、物理厚度、材料构造、source room identity、热区派生、模型预算属于公共契约，图纸/体量两个短分支不应复制各自一套。公共 IR 先由一个最小真实样例验证，体量不要假装成一张 reading 平面图硬塞旧 scorer。

## 旧路径兼容与精简建议

代码/测试仍出现这些旧路径：

- `execution/view_manifest.py` → `proposals/c2_bm_view_manifest_spec.md`；
- `output_coordinates.py`、`correction/orientation.py` → `proposals/c2_e4_output_contract_spec.md`；
- `execution/validation_run.py`、`test_c2_b5_artifact_trust.py` → `proposals/f20_validate_case_v3_proof_design.md`；
- `reading/cv_toolbox/recipes.py`、`execution/isolation.py`、`isolation_templates/guard.py`、`run_cv_probe.py`、`test_gt_discipline.py` → `capability/reading/prescan_snapshot/`；
- `tests/test_judge_arbitration_slice4.py:149` 实际读取 `AI_agent/logs/reviews/execution/artifacts/judge_arbitration_slice4/comparison/comparison.json`。这类运行资产不可因“日志清理”误删或仅改成 Markdown 跳转。

前三组多为注释/技术引用，可保留简短历史跳转页，让当前规范指向 architecture/capability，原技术论证指向字节快照；无需为了文档移动改产品代码。prescan 的四个 Python 快照保留原位置/字节，说明页可以精简。真实测试 fixture/审计 JSON 保留可读取路径。

建议只保留三类当前页面：**一个 plan 记录实际任务，一个 capability 矩阵记录已实现/边界，一个 architecture 契约集合记录产品结构**。proposals 只放仍在选择中的多输入与编辑设计；旧详细规格统一归档，不维护 35 份可同时发号施令的“基线”。技术经验仍可查，切换模型时仓库文档足够恢复目标、约束、事实与下一步。

## 本轮未验证

未运行任何测试/模型/case，未验证历史分数可重现，未声称最近完整 EnergyPlus case 已贯通。未穷举源码每个回退分支；上述“尚未实现”限于检索到的调用面和明确 schema/代码限制，不是对未来扩展不可能的判断。7 份 C2 大规格由另外两位子代理补全覆盖，父代理应将三份审计合并到总索引后再声称整套管理原稿读完。
