# reading / correction：历史依据与下轮设计入口

2026-09-10 收工前核对。用户要求先回看历史好跑测及由此提炼的架构，下轮再继续施工；本页是设计依据与接线差距，不是新实现验收。历史规则中的审批、模型名称、精度和批次要求不自动恢复，当前产品边界以 [目标](../project/goal.md) 为准。

## 历史已经回答了什么

| 证据 | 已支持的认识 | 不应外推的结论 |
|---|---|---|
| [07-05 Haiku 降级实验](../logs/experiments/2026-07-05_haiku_downgrade_test/README.md) | 同脚手架下直接读整案，平面墙 0/9、窗 0/7、立面窗 0/15；外框对不代表内部结构对 | 不能把这次差结果视为新发现，也不能据此断言 Haiku 在所有受约束子任务都无用 |
| [好 reading 形式总账](../archive/2026-09-08_management_rebuild/original/AI_agent/capability/reading/good_reading_implementations.md) 的 07-07 sm21 / sm24 | Haiku 配合固化工具、局部放大、标定、尺寸链对照及候选处置，曾得到好的观测；[07-07 实跑记录](../logs/experiments/2026-07-07_haiku_cv_retest/README.md) 包含 pilot 和返工 | 不是“裸 Haiku 整案自动成功”；sm24 当时是人工查看、无 GT，sm21 返工原文及评测隔离仍有审计限制 |
| 同总账的 07-02 Sonnet 与 [08-21 解剖](../logs/experiments/2026-08-21_historical_reading_dissection/README.md) | Sonnet 好结果中实际自写了 PIL / scipy 测量工具；工具化有价值 | 07-02 是工具工作方式的来源，不是可直接复制的固定工具流程，更不是“不用工具也能好”的反例 |
| [08-20 S1 配置](../../case_tests/e2e_tests/sm21_anchor/run_2026-08-20_acceptance_sonnet_S1/run_config.yaml) 及形式总账 | 全六图复现墙 9/9、平面窗 7/7、立面窗 15/15；有测量和尺寸证据，采用专用隔离目录、pilot、同会话恢复 | 是一次有过程记录的历史复现，不是无人值守稳定性或当前模型版本的保证；历史名称按原档记录，不当作今天可调用 ID |

08-21 解剖还发现：多个 run 复用同一份 reading，不能按目录数累计独立成功次数。具体工具次数、引用标签或证据密度不是普遍充分条件；已有好结果采用不同测量路径。应复用历史夹具 [reading_fixtures.json](../../case_tests/test_baseline/reading_fixtures.json)，连同其中已知缺陷一起评价，不能把旧“好”标签等同当前门洞/源房间完整验收。

## 保留既有分工

历史 [reading 架构](../archive/2026-09-08_management_rebuild/original/AI_agent/architecture/reading_pipeline_architecture.md) 的核心仍适用：**模型决定看哪里、用什么工具以及对象是什么；代码负责测量、换算与证据核对。** SOP 保存好的操作方法，判例保存不同画法；不把某个彩色 CAD 样例的固定处理顺序写成全部图纸的唯一算法。

reading 保存三类信息：原图测到的线/墨迹和空档、图上声明的尺寸文字、模型对墙/门/窗等的解释与不确定性。解释引用可追查的候选和尺寸，公制坐标由代码推导；“调过工具”不代表最终坐标用了工具结果。回叠原图属于工作循环，重复修订应有范围和预算。门/空开口必须保留可定位证据，旧流程的 healed 墙线只能是后续拓扑辅助，不能消掉源门及连通。

历史 [reading / correction 分工指南 §15](../archive/2026-09-08_pre_takeover/guides/reading_correction_split_guide.md) 给出的 correction 目标是两步：

1. **逐图裁定尺寸证据**：代码列出同一对象的证据及分歧，无歧义部分直接计算；模型处理真实歧义；代码落坐标并复查。
2. **跨图空间推理**：对齐楼层、平立面与开口身份，模型判断冲突和建筑整体是否合理，代码执行决定、重建并复查。

两步都采用“代码列问题 → 模型给决定 → 代码执行与检查”，不是让模型再次自由写整栋几何。尺寸不足的对象允许带来源的推断；不要求 reading 先解决所有建筑问题，也不指望 correction 凭空找回未记录的门墙。真实开敞、门洞和画法断口不能仅按缺口长度自动归类。GT 留在评价侧，后端物性和热区切配不进入这两步。

## 09-09 接线实际走到了哪里

[automatic_reading.py](../../src/agent/execution/automatic_reading.py) 接通的是现有隔离读图进程，显式关闭 pilot；本次六图产出是旧 `ReadingView`，仍允许模型写公制笔画。工具候选留档了，但没有标定/候选到输出的有效对应，故“订阅进程已接通”不等于上述 reading 架构落地。

[run_stage.py](../../scripts/tool_scripts/run_stage.py) 的 `_w1_route_correction` 按输入契约选择路径；本次走 `_draw_correction` 的 legacy 分支，再经 [pipeline.py](../../src/agent/pipeline.py) `run_correction` 让模型生成整份校正几何。配置中写了 `correction_decision` 不会自动切到决定式架构。首请求超时只证明本次调用未完成，不能据此判断目标 correction 架构是否有效。

另一方面，代码已有 [as_drawn_v2 工序](../../src/agent/reading/as_drawn/as_drawn_v2.py)、`_draw_correction_as_drawn`、多层装配、[决定执行器](../../src/agent/correction/decision_executor.py)、开口接入与 [配方重放](../../src/agent/correction/chain_replay.py)。不能照抄 08 月文档中的“完全未接线”；也不能把已存在的局部模块宣称为两步全部自动完成。部分历史 perception/缺口决定由开发助手填写，必须与真实模型生成分开。[09-02b 决策环实跑](../logs/experiments/2026-09-02b_m7_evidence_chain_run/README.md) 有单图真实模型调用，但使用历史 DeepSeek 通道；它不证明整案几何正确，也不授权今天复跑。

## 下轮先做的设计工作

先把一个历史好 reading 的实际输入、工具调用、产物和评价，与当前 as-drawn / correction 消费接口逐项对齐，明确哪些组件复用、哪些接口缺失，再开实施任务。优先核对 07-07 sm21/sm24、08-20 S1，以及 09-09 失败样本；不再从“单一 Haiku 直接整案重抽”起步。

建议以当前可用的 Sonnet 级承担流程规划、复杂语义与建筑整体判断，Haiku 等目标档先承担有明确输入输出的候选识别或转录子任务，再比较质量与实际总消耗；这是待实测的分工建议，不是已证最优架构，也不提高产品模型上限。具体进程数量、是否按图分任务、局部复核和预算，下轮结合历史证据定，不先堆多层审查。

验收按阶段分别回答：观测是否忠实、correction 是否保留真实空间和开口、源 BIM 是否自洽可查看。保留一个完整 case 的主线目标，但先验证最关键接口，避免一边重新发明旧设计、一边消耗整案请求。新方案未定前不加大重试、不以全面提高尺寸门槛代替正确的工作方式。
