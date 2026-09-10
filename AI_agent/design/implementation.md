# 现有实现与能力边界

旧能力基线依据业务代码 `461dfc98` 和 [2026-09-08 代码审计](../logs/experiments/2026-09-08_management_audit/README.md)。09-09 已新增 M0 源投影、分区比较、显式门/空开口及提前 HTML 查看，并修复贴边窗误拦；当前 case 的具体状态只在 [路线与任务](../project/roadmap.md) 维护。

## 实际调用链

原图入口增量：`flow --reading-model haiku|sonnet --llm-config FILE` 复用隔离读图启动、同门合并和原有检查，再进入共同源主干；仅启动一次，失败/超时留证据，已有接受观测可复用。`pipeline._call_json_llm` 新增显式 `claude_subscription` 文本 JSON 适配，不继承 API 配置、不回退其他模型。`--llm-config` 已从 flow 启动阶段生效。真实实验状态只在路线页维护，不能以入口接线或离线测试代替冷启动保真结果。

当前源底座增量：`bim` / `flow --target source-bim` 接受绑定源摘要的 `--enclosure-input`，生成含整面/局部开敞及未知围护的 v3；完整逻辑空间不变，显示独立扣除开放区域并标示未知。查看器支持 v2/v3、逻辑边界开关和开敞轮廓拾取。未声明仍为 v2；旧 EP 明确拒绝 v3。三种受控历史几何场景已走正常 flow，不包含原图自动识读、水平洞口或空气交换。见 [共同模型](model.md#显式实际围护09-09-v3-增量) 和 [本轮记录](../logs/worklog/2026-09-09_source_enclosure.md)。

此前后端增量支持显式关闭门：`--opening-policy` 按源门 ID 提供关闭状态、构造和理由，门可在后端跨父墙切片，内门两侧 reciprocal、外门单侧，源开闭状态不改。sm24 已实际全年成功（8 热区/58 基面/11 窗/1 源门/2 门面，0 severe），115 项检查通过。门/空通道已知敞开仍明确拒绝，不假装实体门；协作者接口见 [最小物性契约](ep_physics_contract.md)，证据见 [本轮记录](../logs/worklog/2026-09-09_ep_doors.md)。

共同源 BIM 主干后的 EP 分叉已贯通：`flow --target ep --bim-out ... --physics-template ... --zone-bindings ... --backend-out ... --with-ep` 先导出 v2，再由 [ep_branch.py](../../src/agent/execution/ep_branch.py) 读取该文件派生 EP，最后用本机 EnergyPlus 运行。`backend-ep` 单独接已有停点 BIM；物性模板不含几何。sm21 已实际全年成功、14 热区/100 面/15 窗、0 severe、4 条物性模板相关警告，源 BIM 不变。默认 `flow` 现在是 `source-bim`；旧流程需显式 `legacy-ep`。新后端支持范围与证据见 [最新记录](../logs/worklog/2026-09-09_ep_branch.md)。

上一程已有独立源出口：`flow --target source-bim --bim-out NEW_DIRECTORY` 复用 0_reading/1_correction，随后由 `geometry/source_bim.py` 生成完整源边界、接触关系、门窗/连通和检查，不调用旧 EP 建模/切配。`bim` 子命令可重建已接受校正或显式预览候选。三案例源产物与 sm21 实际 flow 已离线验证，223 项相关测试通过。原图 reading 仍未自动调用；旧 EP flow 和确认入口显式保留。详见 [实现与证据](../logs/worklog/2026-09-09_source_bim_pipeline.md)。以下为历史链，不能代表新源目标已经完成冷启动。

历史链路已有实际成功产物：sm21 `run_2026-07-02_sonnet_flow_e2e` 为 14 区/100 面/15 窗，sm24 `run_2026-06-24_opus_reading` 为 11 区/76 面/11 窗，两者的 EP 完成文件均为成功、0 severe。**sm24 是下游运行成功、源分区失真的资产**：用户确认 reading 正确、C2 之前 correction 切房；`1_correction/attempts/002/output.json` 已有 11 个矩形 cell，走廊分为两片、右下办公室分为三片，随后生成三个内部 Wall 配对。历史 judge 的 minor 判定不符合当前源 BIM 标准，应作为回归反例。历史人工参与、模型配置和表示限制不能当成当前自动运行成绩。sm25 已定位到 reading/correction/modelling 阶段产物，未定位到历史 EP 成功文件。最新证据见 [复杂度与分区核对](../logs/worklog/2026-09-09_drawing_route_execution_plan.md)。

| 阶段 | 当前行为与产物 | 实现 |
|---|---|---|
| 0_reading | 默认核验预生成观测；显式 `--reading-model` 可经隔离订阅执行器读取原图并由既有检查接收 | [run_stage.py](../../scripts/tool_scripts/run_stage.py)、[reading](../../src/agent/reading/) |
| 1_correction | legacy/as-drawn 分派、多层证据整合、坐标校正、补窗、已有结构化门/通道记录自动接入与 finalize；明确开口未建会阻塞完整性 | [pipeline.py](../../src/agent/pipeline.py)、[as_drawn_openings.py](../../src/agent/correction/as_drawn_openings.py)、[correction](../../src/agent/correction/) |
| 2_modelling | 构建 BuildingGeometry，造面、切配、挂窗及明确给定的门洞；附带 source_model.json 与源映射检查，CLI 提前生成扣洞 HTML | [build.py](../../src/agent/geometry/build.py)、[source_model.py](../../src/agent/geometry/source_model.py)、[openings.py](../../src/agent/geometry/openings.py) |
| 3_split_pairing | 当前 CLI 再从校正产物重建，序列化 specs 并与前段几何核对；新门洞尚无 EP 适配，遇到时明确停止 | [split_pairing.py](../../src/agent/geometry/split_pairing.py)、run_stage.py |
| 4_mep | 生成非几何语义；HVAC specs 由代码按 zones 替换并合入保留 schedules | pipeline.py、[intakeoutput.py](../../src/agent/intakeoutput.py) |
| 5_intakeoutput | 朝向/坐标合同、已接受产物核对、装配 IntakeOutput 和 sidecar | [output_coordinates.py](../../src/agent/output_coordinates.py) |
| 下游 | IntakeOutput → IDF → EnergyPlus | [graph.py](../../src/agent/graph.py)、[run_full_pipeline.py](../../scripts/run_full_pipeline.py) |

CLI `flow` 保存 attempts、checks、停止原因和可选 judge/确认。`run_pipeline` / `run_pipeline_artifacts` 函数仍有 legacy 加载路径，不能假定和 CLI 支持范围相同。命令与配置优先级见 [运行 case](../workflow/run_case.md)。

## 图纸观测与证据

reading 工具箱、CV、隔离和模型工具可复用，但需要调用者准备配置、观测和执行顺序。`flow` 可显式调用隔离 reading 执行器；真实生成质量按实验判断。
[vector_contract.py](../../src/agent/reading/vector_contract.py) 将 legacy ReadingView 作为消费格式，as-drawn plan v2 / elevation v0 可适配，plan v0 尚不消费；现有 as-drawn 路由要求相应平立面材料，混用或缺失会拒绝。

as-drawn 的 reading 检查覆盖契约、标定和尺寸链，旧字段检查为 NA；来源引用还依赖校正等消费者验证，独立像素自检不等于自动接进 flow。尺寸链和纯像素是不同证据条件，像素量测不能凭统一量化变成尺寸标注精度。
校正证据链已接多层求解、楼层协调、窗口构建与明确门/通道记录的确定性提取。新门洞在楼层装配之后加入，来源配方同步进入独立重放；旧无配方档案不追补新门。projection bridge 的 `outer_skin` 尚未实现，`complete` 只说明对应算法的完成条件，不证明所有房间都已读出。窗位置路线②的 citation 仍有 shadow 阶段，完整替代模型 span 尚未交付。

外墙声明尺寸校正和楼层墙位对齐现保留校正前已有的端点连接：只使用原物理墙带和端点关系证明宿主，把原本可延伸到旧墙轴的有效端头接到移动后的宿主轴。不同候选宿主有冲突、墙坍缩或两方向同时移动后连接仍断开时明确拒绝；不扩大延伸容差，也不将门窗跨度随意缩短。正常链保存端点及宿主移动记录，新来源配方显式标记 `preserve_endpoint_connections_v1`；缺该字段的历史档案仍按旧逻辑重放，摘要保持原意。新候选的保存检查仍从冻结 reading/墙编译字节独立重建，不能靠删除配方把新几何冒充旧档案。`derive_as_drawn_chain_producer` 仅重建候选，不授予接受状态。

同一编墙对象可以包含不相连的墙段，不再把对象身份本身当成缺口有物理隔断的证明。现可通过 `_run/wall_gap_decisions.json` 提交显式连续空间决定，绑定 plan/image/compilation 摘要、墙 ID、已有缺口序号、判读方式和理由；[wall_gap_review.py](../../src/agent/correction/wall_gap_review.py) 从输入推导跨度，不接收 GT 或任意删墙坐标。决定拆开连续分组，原实墙段保持，其余门窗逻辑边界仍按原规则续接。旧门/通道正观测若因此改判，保留在 reclassified 台账和源修改记录中；不能静默丢掉。正常校正入口及独立 writer 重放均消费冻结决定，改变输入/图片或删去新决定会使验证拒绝；历史无决定配方仍按旧行为重放。该能力尚不自动生成语义决定，sm25 首案由开发助手核对原图辅助，未宣称冷启动。

## 模型和几何内核

[correction/schema.py](../../src/agent/correction/schema.py) 中 Cell 以米表达平面、Floor 给出高度；legacy 注释使用 world-frame/centerline，V3 配合当前建筑坐标合同，带 footprint、立面段、来源等字段。
[geometry/modelling.py](../../src/agent/geometry/modelling.py) 提供 ZoneVolume、Surface、Opening 和 BuildingGeometry；后者承载 zone/surface/window/显式门洞派生片，并非完整通用 BIM。当前切配按楼层分组处理墙和相邻层水平面，不能据几何原语支持 polygon 就宣称任意通高、中庭、斜屋面均可运行。

E4 的建筑坐标、Relative、Zone 归零和来源朝向已经接入装配及导出检查；并非全部 legacy 入口都等价消费。[state.py](../../src/agent/state.py) 中 IntakeOutput 仍以 building、site_location 及九类 specs 交接下游，多数 specs 是文本，不能替代可编辑的建筑模型。
V3 外皮事务和 B5 的部分窗宿主/可见性链要求楼层 footprint/family 范围匹配，还会拒绝部分 assumed existence；不能直接用于任意外壳或全推断开口。

### 建筑复杂度的实际边界（09-09 定向核对）

| 能力 | 现有支撑 | 当前不能据此宣称完成的部分 |
|---|---|---|
| 正交非矩形房间 | `Cell.polygon`、C2 多边形造面/挂窗；`test_c2_b1_cell_polygon.py` 已有单个 L 形走廊和 sm24 形状用例 | 整个原图冷启动流程与源分区保真仍需真实 case 验证；不重做已实现的 C2 内核 |
| 立面匹配与缺图 | ViewManifest、立面投影框架、可见性、宿主和来源基础 | 命名立面/已绑定方向不等于未命名视图自动匹配；当前 as-drawn 对缺立面会拒绝 |
| 退台 | V3 每层 footprint 字段，切配已有层间交集及未覆盖 roof/exposed-floor 计算 | `assemble_multifloor_geometry` 仍以 `PER_FLOOR_FOOTPRINT_MISMATCH` 拒绝不同层外形；来源、校验、覆盖和立面消费者须一起贯通 |
| 内院、挑空、通高 | 面模型、区域 z 范围、切配原语可复用 | Cell 只有外环；projection bridge 拒绝 `FOOTPRINT_HAS_INTERIORS`；造区域统一用所属层高度，墙按同层分组、楼板按相邻层处理，未表达一般孔洞/跨层连通空间 |
| 平面非正交 | 底层 polygon/线段及法向原语可复用 | `cell_geometry.cell_polygon` 和 facade visibility 明确拒绝非正交边，run_config 只接受 rectangular/orthogonal_polygon；读图/校正/评分的轴向假设也要变 |
| 整栋旋转/真北 | 建筑局部坐标与朝向出口已有实现 | 旋转的正交建筑与内部斜墙不是同一能力；输入方向识别与未命名立面匹配需分别验收 |

上述为复杂度边界；M0 已执行确定性分区回归和旧产物重放，09-09 新冷启动实验失败，未新增复杂度能力证明。施工顺序、样例和完成依据见 [执行计划](../project/drawing_reconstruction_plan.md)。

## 面向目标的缺口

### gate、judge、GT 的当前接线

- `stage_runner.py` 定义 0–5 的阶段与依赖；`step_orchestrator.py` 在 gate① 后进入 judge/几何确认或继续。正式源确认已在 Stage 2 后阻塞 Stage 3–5，绑定已显示快照并核对可信上游与当前检查；恢复不重抽上游，旧确认随源/检查/查看产物变化失效。旧 ReadingView 自动调用已接；as-drawn 原图自动生产及完整两步裁定仍需贯通，历史 flow 成功不意味着今日已经是一键无人值守。
- [CheckReport](../../src/validator/checks/schema.py) 已区分 invariant 的阻塞与 cross_check 的提示，并有 profile 例外；[StageVerdict](../../src/agent/judge/verdict.py) 明确采用定性清单，minor 放行，severe/fatal 阻塞（J0 有可交校正恢复的例外）。[judge 注册](../../src/agent/judge/executor.py) 当前启用 J0/J1，J4 是停用的 stub。
- 评分并非全部毫米级：legacy 墙位默认容差 0.30 m、窗中心 0.40 m；[typed 评分配置](../../src/configs/judge_score.yaml) 同样包含厘米/分米级阈值；as-drawn 平面位置默认 0.08 m，并纳入两侧量化误差下限。它们是不同消费者的现值，不是本轮推荐的统一容差。
- [GT 配置](../../src/configs/judge_gt.yaml) 的 DXF 节点连接/轴对齐为 0.001 m；as-drawn 分母仍从签字源 DXF 生成。GT 准备/规整精度与最后产品评价容差属于不同环节，不能只修改评分配置便声称解决了前者。
- sm25 当前 J0/J1 已放行，建模的 `kernel.pairing_gate` 将 [InterZone 检查](../../src/validator/interzone.py) 的短边问题升为 invariant，0.065 m 小于硬编码 0.1 m 后停止。该规则来自历史崩溃防护，尚未证明是所有模型/EP 版本的普遍下限；也不是 GT 逐点比较导致的这次直接停止。

09-09 新增 [确定性分区比较器](../../src/agent/judge/source_partition.py) 和三案例诊断入口；[独立分区证据服务](../../src/agent/judge/partition_evidence.py) 已接 J1 评价包，自动读取可用 GT 房间多边形及历史读图墙线。它提供源对象对应、内部边界差异和无支持边界，保留原始参考面差异与未评价范围；J0、as-drawn 独立墙线适配与自动房间身份识读仍待接线。源到派生映射已接 Stage 2：严重实现错误保存候选后返回失败，包含 exploratory 路径；其余既有 gate 阈值未放宽。源投影的具体覆盖与限制见 [共同模型](model.md)，比较器边界见 [评价原则](evaluation.md)。

| 能力 | 已有基础 | 缺口 |
|---|---|---|
| 窗与开口 | 补窗、唯一墙段贴边窗、明确门/空开口及结构化读图记录自动接入、两侧关系和扣洞显示已接线 | 从原图读全门洞、说明文字到可靠开口证据、房间编辑后同步开口、楼板孔洞与新开口仿真适配仍未完成 |
| 朝向与视图匹配 | 候选/假设朝向与 manifest | 枚举槽不是自动多源匹配和仲裁 |
| 查看与编辑 | 离线交互式 3D 查看器、确认/恢复 | 窗移动、墙推拉、自然语言修改的完整回写尚需实现 |
| 外皮体量 | 可复用几何与查看出口 | 专用适配、内部推断及其简化策略尚待建立 |
| CAD 与混合输入 | 已有 CAD/GT 工具及图纸资产 | 生产输入与评测答案需分开；现有图像评测测试仍禁 case_data 带 DXF/DWG，接 CAD 时需相应调整 |
| 下游与物性 | IntakeOutput/IDF/EP 基础 | 最近 case 尚未贯通；协作者交付需核对接口，不重开同类工程 |
| 质量与成本 | checks、judge、配置和记录工具 | 目标档模型仍需形成可比较的实跑基线 |

GT 修订、AnswerCompiler 和评分已有部分接线，尚未统一消费 frozen facts，详见 [验证与评价](evaluation.md)。相关模块按用途复用，设计建议只有落实并实测后才成为能力声明。

09-09 首次显式自动入口实验已执行：[sm21 原图对照与记录](../logs/experiments/2026-09-09_automatic_source_sm21_run01/README.md)。读图技术接受但源分区/门信息失真；CV 候选尚未与输出标定对应。Sonnet 校正超时后停止重试，未产出新 BIM。入口接线不等于图纸重建能力验收；下一步针对保存的实质结构反例改进，不能靠全面提升尺寸启发式门槛代替保真判断。

09-10 收工前核对：本次自动入口实际产出 legacy ReadingView，`_w1_route_correction` 因此进入整案 JSON 校正；`correction_decision` 配置不会改变输入路由。已有 as-drawn 生产工序、决定执行器、多层与门窗装配应作为下轮接线基础，不能把旧归档的“零生产调用”照抄成当前状态。历史好跑测及具体源码入口见 [读图与校正依据](reading_correction.md)。
