# 09-10 reading/correction 完整梳理与下一项选择

本轮完成指定范围内的历史实跑、单/双线演变、现有接线和方案比较。**历史单线可以做好，as-drawn 也有可复用的证据与编译模块；目前没有对照实验能证明一种表示普遍胜出。下一项先补“观测怎样交给校正”的最小接口，以有证据的单线作为首个贯通对象，保留按需调用双线测量的能力。** 不把重新跑一次 Haiku 整案或整体切换 as-drawn 当作起点。

**后续修订提示（09-10）**：本报告保留梳理完成时的建议。用户随后补充改双线的推理负担动机，并确认“标注 + 像素 ＞ 像素 ＞ 纯推理”、先出 BIM 再提高精度。当前不再预先选择单线或把完整证据接口设为生成前置；最新职责与下一项以 [当前设计](../../../design/reading_correction.md) 和 [路线](../../../project/roadmap.md) 为准。下文原件核对与诊断结果仍保留。

这是主助手交叉核实后的结论。三份 Claude 原始报告用于保留分析过程，**其中被本页第六节纠正的判断不采用**。本轮没有改动生产代码，没有产品 reading/correction 模型实验、DeepSeek 或 EP 调用，没有产出新的冷启动 BIM。

## 一、范围、方法与证据

- 起点：`main@5a37eb71`，工作区干净，仅一个 main 工作树；用户在交接中明确指定三位 Claude 梳理，路线保持开放。
- 三个只读 Claude 订阅会话：历史实跑、架构演变、独立方案比较。请求 `sonnet`、high，实际主模型由 CLI 报告为 `claude-sonnet-5`；这属于开发分析，不是产品运行基线。具体辅助模型、token 和 CLI 费用估算以 [会话汇总](review_sessions.json) 为准。
- 仅给 Read/Grep/Glob，关闭 MCP、hooks 和额外配置来源；子进程不带 API key、第三方端点或模型回退。未使用旧派工脚本的可写工具与环境设置。
- 主助手直接读关键 JSON、源码和原始校正回复，执行文件哈希盘点及三份历史 reading 的只读接口诊断。没有重跑历史判分器，不把现有 score 文件的读取当成新成绩。
- [历史原始报告](history_report.md)、[架构原始报告](architecture_report.md)、[方案原始报告](options_report.md) 与各自 prompt/run 记录一起保存。压缩流日志保存工具读入和返回过程，未修改历史输入/输出。

机器证据：[产物盘点](artifact_inventory.json) / [盘点脚本](inspect_artifacts.py)，[legacy 接口诊断](legacy_adapter_probe.json) / [诊断脚本](probe_legacy_adapter.py)。下面将“原件直接可核查”“历史记录说法”和“本轮技术建议”分开。

## 二、历史好坏跑测到底证明了什么

表中分数是**历史记载的选定墙窗指标**，不是本轮重算，也不是源房间/门洞全面通过。历史模型名仅作档案标签。初始化来自新原图与过程中有无外部审阅，是两个不同维度。

| 实例 | 当时实际工作方式 | 历史效果与限制 | 本轮直接核实的依据 |
|---|---|---|---|
| 07-02 Sonnet，sm21 六图 | 自写 PIL/scipy 测量与换算；不是“无工具识图” | 墙 9/9、平面窗 7/7、立面窗 15/15；是工具方法的来源，非固定工具流程实例 | [run](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/)、现有 reading 和 score；112 次调用/60 Bash 来自历史取证，未重新逐条审 transcript |
| 07-05 Haiku，sm21 六图 | 同脚手架降档，但未采用上述测量方式，墙位多为估计 | 0/9、0/7、0/15；不能因外框和楼层线正确就认为内部正确 | [run](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-05_haiku_downgrade/) 的配置、summary、reading |
| 07-07 Haiku，sm21 六图 | 固化工具箱、指令要求量后再画；pilot 一轮返工、候选处置、尺寸与像素对照、订阅断限后恢复 | 9/9、7/7、15/15；有外部过程指导，打回者此前是否见过 GT 不可完整审计 | [run](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/) 的 92 份 CV JSON、逐笔尺寸引用及测量说明；原始返工隔离限制沿用历史审计结论 |
| 07-07 Haiku，sm24 五图 | 同工具方式；流程返工和 schema 修正；无尺寸墙使用标定后像素测量 | 14 墙、11 窗、51 尺寸；当时“好”来自人工查看，无 GT；门多在文字里 | [1F 原件](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/1f_view.json)、[summary](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/reading_summary.md) 与 38 份 CV JSON |
| 07-08 mini，sm21 六图 | 尺寸链算术承担更多落位，工具测量作辅助 | 墙 9/9、平面窗 6/7；未标注墙带余量放错位置使窗偏移，不能列作全绿 | [run](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-08_gpt54mini_cv_retest/) 与 [known_defect](../../../../case_tests/test_baseline/reading_fixtures.json) |
| 08-20 S1 Sonnet，sm21 六图 | 专用空隔离目录、工具箱、外部 pilot 放行；跨订阅窗口恢复同会话 | 历史摘要 9/9、7/7、15/15；墙窗基准不一致仍存在；单次 reading 复现，不是无人值守整案成功 | [配置](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-08-20_acceptance_sonnet_S1/run_config.yaml)、[1F 原件](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-08-20_acceptance_sonnet_S1/0_reading/1f_view.json)、pilot/调用记录 |
| 08-20 G1 mini，sm21 六图 | pilot 经返工放行，后续图仍出错；两轴标定告警后拆轴调用 | 7/9、5/7、立面 6/15；第一张图审过不能外推整案 | [run](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-08-20_acceptance_gpt54mini_G1/) 的裁定/过程与最终产物 |
| 09-09 Haiku，sm21 六图 | 新原图隔离生成，pilot 关闭；工具候选保存，但缺标定及候选到墙窗输出的有效映射 | 技术 accepted，实质漏隔墙、错走廊、门无几何；Sonnet 校正一次超时、一次中断；无 BIM | [失败原件与诊断](../2026-09-09_automatic_source_sm21_run01/README.md)，本轮另从 accepted `output.json` 读取 1F |

费用只能按原记录口径使用：07-07 的约 0.4–0.6M / 0.65M token、S1 单图约 $7.32 是历史过程估算，本轮未核对账单，不据此推出“某路线便宜一个量级”。09-09 reading 有 CLI 用量记录（约 340 秒、44 turn、估算 $0.5196532）；校正超时/中断用量不全，整案总成本未知。订阅窗口耗尽也不能换算成该 case 的净工作时长。

**独立性**：本轮按限定路径扫描到 59 份一层 reading，字节哈希只有 29 种；14 个历史夹具的逐图和全视图文件集哈希均已保存。这是去重诊断，不是成功次数。只相同的一层不能证明全六图相同；08-21 的“19 个目录复用一份”保留为其当时扫描口径，不与今日数字混算。

## 三、单/双线变化的实际含义

### 1. 历史好单线已经包含解释

07-07 sm21 的 `S1–S4` 是外墙外皮（0/15/8 m），内墙使用中线；sm24 也是外墙外皮、内部墙按中线表达。基准写在 note 中，`geometry.thickness_m` 为 null。这不是统一的“所有线都代表轴线”。

08-20 S1 的 `S1` 位于 x=0.12，`S2` 位于 y=7.89；note 明写 centerline，部分窗仍使用标称边界/链值。这与 07-07 的外墙基准不同。当前保存的 S1 score 已把 0.11–0.12 m 外框偏差列为 `within_tol`；`max_wall_offset_m=0` 只统计内部墙位置，不能译为整图零误差。当前 [reading_score.py](../../../../src/agent/judge/reading_score.py) 也有独立 boundary 比较，不沿用“今天评分器从不比较外框”的旧说法。

上述三份好 1F 中，结构化 door/opening/passage 笔画均为 **0**。门的位置有时写得很细，但仍在墙 note/uncaptured 中；“看懂门”和“下游能逐门保留”不是同一交付。

### 2. as-drawn 不是把所有判断都推到 correction

08-23/24 的调整针对过早合并面线、用首尾跨度跨过真实空档、按已声明厚度筛墙导致漏隔墙等问题。它把**观测墨迹、图纸声明、语义假设**分开，保留两面各自的连续区间和空档，避免单线生成时丢失不可恢复的信息。

但 reading 仍判断哪些墨是墙、哪两条面线属于同一墙、空档像门还是窗；校正负责采信尺寸、选择输出基准、处理跨图关系。as-drawn 也支持实心墙带和独立面，不只支持双线画法。具体演变见 [旧分工指南](../../../archive/2026-09-08_pre_takeover/guides/reading_correction_split_guide.md) 和 [原型设计](../2026-08-23_as_drawn_reading_prototype/design_as_drawn_layer.md)。这些文件中的旧数值硬门、审批和模型档位不恢复为当前要求。

实际原型 `sm25_2f_v2.json` 的 `family_roles.source` 明写由主控直接看图，`perception_source` 也可追查；当前有 46 条面线、303 配对候选、21 已选配对和 87 条开口类型记录。它支持数据结构与确定性编译的可行性，**不证明目标模型可自主完成全部判断**。[09-02b 单图决定环](../2026-09-02b_m7_evidence_chain_run/README.md) 消费了这些辅助观测；此外 [run_win_e2e](../../../../case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/1_correction/_run/evidence_chain_route.json) 也保存了真实模型路由及两层决定环结果。因此不能称“历史只有一次真模型调用”，也不能把模型选择尺寸/厚度候选等同于它从原图自主完成墙面配对。

### 3. correction 的目标分工可以跨表示复用

目标仍是两步：逐图裁定尺寸证据，再跨图做空间推理；每步都是“代码列问题 → 模型给有依据的决定 → 代码执行与重检”。用单线还是面线不改变这个协作原则。没有依据的歧义允许保留未知，不能让模型自由重写整栋坐标，也不能让确定性补线把开敞走廊封死。

## 四、当前代码已接什么、还缺什么

| 入口/组件 | 本轮核对结论 | 复用边界 |
|---|---|---|
| [automatic_reading.py](../../../../src/agent/execution/automatic_reading.py) | 自动启动隔离订阅读图、归档/恢复；显式 `pilot_review_gate=False` | 没有实现完整的感知任务编排；本次实跑产出 legacy ReadingView |
| [run_stage.py](../../../../scripts/tool_scripts/run_stage.py) `_w1_route_correction` | 依据冻结视图的真实契约路由；全 legacy 进旧校正，全 as-drawn 平/立面进新分支 | `correction_decision` 配置名不会自动切路；混合契约有明确拒绝，不能只换配置 |
| [pipeline.py](../../../../src/agent/pipeline.py) `run_correction` | legacy 仍让模型写校正几何；evidence_chain 有适配、问题包、执行、编译、投影 | 决定环已存在，不等于两步建筑整体判断全部自动实现 |
| [evidence_adapters.py](../../../../src/agent/correction/evidence_adapters.py) + [wall_compiler.py](../../../../src/agent/correction/wall_compiler.py) | 支持 legacy 墙线 claim，结构化 centerline 可直接成为轴；无结构化基准则明确未知 | legacy 适配器只接墙，窗/门、尺寸等通道未完整适配；不是现成无损转换器 |
| [as_drawn_v2.py](../../../../src/agent/reading/as_drawn/as_drawn_v2.py) | 测量/候选/合成工序已在生产源码；有 perception 与 opening_types 输入 | 上游识别仍需真实模型形成，辅助 perception 不等于该步骤自动完成 |
| `_draw_correction_as_drawn` / `run_multifloor_correction` | 已接平立面、层高、多层装配、补窗、开口政策和 finalize；有源配方重放 | 完整新原图到源 BIM 未被证明；不得退回旧文档“全未接线”的判断 |
| 源 BIM 停点及 EP 分叉 | 当前共同源生成、查看和已有后端保留 | 表示方案改动不能另造 EP 几何路线；灰空间细化、编辑、物性扩展不进入本项 |

**本轮只读接口实测**：07-07 sm21、08-20 S1、07-07 sm24 一层分别得到 10/10/14 条墙 claim，**全部基准 unknown、可执行轴线 0、可选基准候选 0、开口 claim 0**，completion=degraded，源字节未变。原因是原件基准只在 note、没有结构化厚度；适配器刻意不从自由文字偷偷猜基准。缺的是可执行的证据接口，不是更大的重试预算。

## 五、方案比较与下一项

三个方案是**职责选择**，不应与现有类名一一绑定。组合表示不等于必须把所有图都迁成 as-drawn；双线方案也不应被定义为“派生后就丢弃原观测”。

| 方案 | 有依据的优势 | 已知成本/风险 | 本轮选择 |
|---|---|---|---|
| A：reading 输出有测量依据的单线 | 多份真实 reading 经外部过程审阅取得好结果；最接近现有自动入口 | 提前判断基准；旧笔画缺结构化门/基准；不能直接接现有决定式适配器 | **首个有界贯通对象**，补最小接口后再作原图验证；不是恢复整案自由坐标校正 |
| B：reading 保留墙面证据，correction 派生参考线 | 两面不等长、缺口、厚度/基准歧义可追查；已有工序和编译器 | 识别族/配对/空档的自主能力和整案成本仍缺验证；候选量可能很大 | 保留；sm25 等复杂缺口处有实际用处，不强迫简单图先完成全部面配对 |
| C：原观测与派生单线并存 | 能回查/重算；已有 compiler 的 source refs 可复用 | 若要求处处完整双份几何，会扩大输出、适配和同步负担 | 采用**最小可追溯原则**：留原观测引用与派生依据；不新建两套平行权威几何 |

这是本轮技术取舍，**不是已证明 A 更准/更便宜，也不是用户另行确认了唯一长期架构**。

下一项的具体边界：

1. 先落一份最小的 reading→correction 接口样例：稳定墙/开口 ID、参考线基准、测量或尺寸依据、实际连续段/缺口、宿主与相邻信息、未知和推断标识。输入为本轮三份历史 1F，以及已保存 sm25 面线/连续走廊反例。旧 note 的解释若由开发助手补录，单独存为辅助决定，绝不改旧 reading 或冒充冷启动。
2. 在该接口上验证确定性执行：不凭空挪墙、不静默丢窗/门、不把计算切分变成物理隔断；sm24 的 11-cell 反例继续判为分区错误。证据缺失时应得到具体待判项，不能以空输出 accepted 作为成功。先验证墙基准、一个真实门和一处连续走廊，避免先铺全套新 schema。
3. 再开一个新原图 run，先一张代表性平面，通过后扩完整 sm21。Sonnet 级负责工序/歧义/整体判断；Haiku 等目标档承担可检查的转录或候选识别，记录实际干预、耗时、token 和失败。保留每图局部回看与有限修订；若采用外部 pilot，应注明外部参与，不把一次人工审核流程称作无人值守成功。
4. 对照分别评价 reading 忠实程度、correction 有没有改坏分区/连通、源 BIM 是否自洽可查看。GT 只给评价侧。合理未标注墙厚余量、合法自由墙端、工具调用多少不能单独作为硬失败/成功标准。

本轮到架构梳理与下一项设计为止，没有执行以上新接口施工或新原图 run。

## 六、主助手对原始报告的纠正

| 原始报告中的说法 | 核实后的处理 |
|---|---|
| options：07-07 好 reading “靠模型直接画门” | **不采用**。三份好 1F 均无结构化 door/opening；门主要在墙 note/uncaptured 中，见盘点。 |
| options：as-drawn 组件彼此尚未接通、门身份尚未外置 | **不采用过时状态**。当前 `_draw_correction_as_drawn` 已接多层/窗/开口；实际 v2 原件和当前生产者都有 `opening_types`。未完成的是自主感知及整案验证等剩余范围。 |
| options：B/C 已合一，因此 C 不再是可选方案 | **不采用这个排他推论**。现有编译器保存引用并不能决定 reading 在哪一步输出单线；A 也可以保留观测引用。 |
| options：缺 pilot 是 09-09 失败的已证直接原因 | **降为待验证的流程假说**。关闭 pilot 和无有效标定都是事实，但未做消融实验，不能给两者分别作因果定量。 |
| options：工具次数接近历史、尺寸链全过、内部墙无自由端作为验收 | **不采用通用硬门**。这些指标都有合法例外；验收真实墙/空间/开口及可执行证据，按案解释异常。 |
| history：sm24 错切只是后续确定性内核分解 | **纠正阶段归因**。[06-24 原始 correction 回复](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading/1_correction/correction_raw.txt) 已直接列出 11 cells；后续再把切分变成内部 Wall。不同 run 的谱系应分开，但不沿用旧 REPORT 的“不算错”。 |
| history：07-07 sm24 与 06-24 不同，因此可排除 07-07 correction 改坏 | **不能外推**。不同原件可确认；07-07 实跑日志还单独登记了用户发现 correction 把正确值改偏。没有逐案核完不能宣布其他 run 无此类问题。 |
| history：97/8≈92% 表示检查通过率 | **不采用**。保留原始 97 PASS / 24 N/A / 8 FAIL；不把数量比例解释为可信度，原报告算式也不成立。 |
| history：本次目录属于另一次中断的尝试、建议清理 | **不采用**。它看到的是自己仍在运行的实时目录；本轮只有一次三会话派工，完成记录已保存，无重复尝试。 |
| architecture：legacy 没有真实歧义可裁，窗/门未适配是因为都只在文字里 | **不采用**。三份原件有 7/7/11 个结构化 window 笔画，适配器仍未翻译；unknown 且没有候选说明信息/接口缺失，不等于无歧义。不能通过改路由并“接受基准未知”解决。 |
| architecture：历史唯一真实决定环证明模型做了墙面配对 | **不采用**。09-02b 与 run_win_e2e 均有真实模型记录；上游配对已有 perception 来源，决定环选择厚度等候选并不能证明感知自动完成。 |
| architecture：仓库默认 DeepSeek 配置说明近期重建可能发生了调用 | **不由配置推断执行**。默认配置、显式订阅覆盖、固定决定和 replay 是不同路径；实际调用只按对应 run 的请求记录判断。本轮仅只读诊断，没有进入任何产品模型调用路径。 |
| architecture：自动入口“永远只能 legacy” | **限定到已核查路径**。当前默认脚手架和 09-09 实跑走 legacy；尚未实现自动 as-drawn 感知编排，不能扩大成任意产物在路由器中都不可达。跨图确定性装配已接，不等于模型整体空间判断已完整落地。 |
| 旧文档/报告对 S1 “0.0 m”的泛化 | **限定指标范围**。内部墙横向偏差为 0，不等于外边界/墙端零差；当前盘上评分明确保存 boundary 偏差。 |

上述复核说明需要对照生产者、消费者和原件，不能以多助手意见一致代替证据。

## 七、复现与未覆盖范围

从仓库根运行，仅离线读原产物；可重定向到新的临时文件，与本目录 JSON 比较：

```bash
python AI_agent/logs/experiments/2026-09-10_reading_architecture_review/inspect_artifacts.py
python -m AI_agent.logs.experiments.2026-09-10_reading_architecture_review.probe_legacy_adapter
```

本轮检查：JSON 可解析、三份接口诊断可复现、历史源字节未变、新文档引用存在、diff/敏感内容检查。没有生产行为改动，不运行 pytest 全量。历史测试成绩沿用其原记录，不合计为今日新验证。

范围覆盖 07-02、07-05、07-07 sm21/sm24、07-08、08-20 S1/G1、as-drawn 演变、09-02 单图决定环与 09-09 失败；没有通读全仓历史，也没有验证新模型的盲测成功率、A/B 整案成本、一般非正交/挑空等能力。当前仍无新冷启动可用 BIM。
