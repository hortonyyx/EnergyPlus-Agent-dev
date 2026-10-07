# Q1 第三轮交付记录

状态：第三轮已完成。跨层外轮廓按 Opus 最新裁定对齐；四个 sm25 目标均整楼通过；其余 11 组与第二轮的语义、评价指标和 source precision 一致。90 项有效定向检查全部通过；本轮四个临时目录已用 Python `shutil.rmtree` 删除。保留两组旧 `room` 枚举兼容性限制。

日期：2026-10-08。工作树 `D:/EnergyPlus-Agent-worktrees/q1`；分支 `dev/astra-q1-20261007`；基线 `e030b6b0195eea18d2d54261038f8a8f25640518`。未提交、未改共享版本登记，work model / Paratera / DeepSeek 请求均为 0。第二轮原字节证据在 [round2/](round2/README.md)，第一轮在 [round1/](round1/README.md)；本页为当前结论。

## 1. B：跨层外轮廓对齐

“外轮廓不动”仅约束同层 A：内部墙向外墙合并时，外墙作为固定目标。跨层外轮廓边，包括凹口等局部边，适用跨度重叠且距离严格小于 0.30m 的对齐规则；恰好 0.30m 的真实退台保留。

外皮默认上层边对齐到下层对应边；只有上层该边有 F 尺寸依据、下层没有时反向。两边都有尺寸依据时仍按上层对齐下层。每次按单条边的法向移动，不把局部凹口当成整层平移；挂在边上的门窗、相接隔墙端点及共线延续墙链随动。清单记录前后轮廓、源/目标楼层与边索引、位移、门窗和接头 ID。

外皮只允许移动到对层真实且重叠的外皮边。若只有一条内部墙是外皮的共线延续，则固定这条外皮锚线、移动对层普通内部墙；不会把外皮带到任意内部墙坐标。三层顶部独有尺寸依据可沿相邻外皮链逐层向下传播，每步仍要求重叠、位移小于 0.30m 并通过事务检查。

B 以 A 完成后的稿为语义基线，每次移动重新严格编译，检查房间、门窗、宿主和门连接不变；同层没有新增 30cm 内重叠近线，空间不窄于 0.6m。合法的大间距允许改变数值。以下情形拒绝并回滚，保留完整尝试清单：

- 严格编译失败，或房间、开口、宿主、连接关系改变。
- 调整后出现同层硬约束问题，包括新增近线或空间宽度不足。
- 无合法对应外皮目标，或普通内部墙的独有尺寸依据与外皮锚线冲突，导致最终仍有未对齐近线。多层传播遇自身尺寸依据或链断时不强行跨越；剩余不满足约束的稿由最终检查拒绝。

同层 A 的第二轮种子删除、门窗搬移/重叠合并规则保持；非正交输入仍是现有不支持边界。两份授权补丁 [source_save_gate.patch](source_save_gate.patch)、[session_compiled_plan.patch](session_compiled_plan.patch) 保持已应用状态。本轮未追加 session 修改；它与基线的差异仍仅为 `RoleSession.run_reader`、`RoleSession._build_from_artifact` 及 `import copy`，供 Opus 与 Q2 同文件修改协调合并。

最终 kernel SHA256 为 `02481d54bec1834345051bdfbc39bf19f003cacd15c850c7541cb6d6ccb991ce`。覆盖普通与凹口外皮、门窗/隔墙随动、尺寸反向、双侧尺寸默认方向、三层传播、0.30m 边界、同层 A 不变、回滚和真实几何重试拒绝。工具装配入口另验证有效稿/源模型/审计/查看页一致，原稿字节保留。

单模型绘图指引与装配参考同步更正规则，查看页增加“跨层外轮廓边对齐”标签；E/F 仍只在分工试建入口启用。相对最初派工，单模型文本仍由[四处精确替换](intentional_model_text_changes.json)与[两条工具说明](intentional_tool_description_changes.json)约束，参数签名保持。字符数包含空白、不是 token 数：

| 文本 | 派工前 | 第二轮 | 第三轮 |
|---|---:|---:|---:|
| 单模型绘图指引 | 4066 | 4131 | 4149 |
| plan_partition 参考 | 7448 | 8768 | 8768 |
| plan_assembly 参考 | 1725 | 2330 | 2501 |
| 平面读图员指引 | 9045 | 9628 | 9628 |
| build_plan_bim 工具说明 | 442 | 535 | 535 |
| assemble_plan_bim 工具说明 | 546 | 616 | 616 |

## 2. H：完整重放与消除条数

H 共 15 组、25 份平面稿，15 组几何与语义审计通过，其中 13 组通过当前 source 保存检查、`building_precision.total=0`；另 2 组为下述已知枚举限制。原始输入、GT、原图与真实运行目录均只读。

四个第三轮目标均整楼通过，无剩余几何拒绝：

| 组 | A 同层消除 | B 内墙移动记录 | 消除外皮近线的唯一线对 | 内墙跨层近线，前→后 |
|---|---|---:|---:|---:|
| cmp3 sm25 role | F1 合并 2 条重复墙；F2 合并 3 条、消除 1 个无种子窄条空间、删除 1 个退化接头 | 15 | 4 | 15→0 |
| cmp3 sm25 single | 1F、2F 各合并 1 条重复墙 | 16 | 3 | 16→0 |
| Claude sm25 run53 | 0 | 22 | 8 | 24→0 |
| Claude sm25 run54 | 0 | 16 | 8 | 16→0 |

role 合计消除 5 条重复墙线与 1 个窄条空间；single 合计消除 2 条重复墙线。真实输入中删除命名种子、合并重叠开口均为 0；对应行为由合成用例覆盖，不把测试数算进真实消除数。

全部 H 的内部墙跨层近线由 100 对降到 0 对，依据生产检查的 `storey_wall_offset_under_0_30m` 逐项计数；B 共交付 92 条内部墙移动记录。另有 23 对外轮廓偏差被消除，分别为上表 4/3/8/8；外皮对齐不计作删除墙线，也不与内部墙的线对/移动记录混加。23 项都具有有效源/目标边、原始跨度重叠、位移小于 0.30m、最终落点正确及目标边保持的证据。四组历史稿没有 F 外皮尺寸依据，因此实际方向全部为二层到一层。single 的 `Pm1N` 移到上层 `QhallS` 外皮锚线，外皮没有向内部墙移动，不计为第 4 对外皮消除。

其余 11 组对照第二轮：after 语义、精度分桶及逐项误差、source precision（排除源摘要字段）的规范化 SHA 全部一致：

| 来源 | 当前结果 |
|---|---|
| cmp3 sm21 role/single | 两组当前保存通过，各对齐 2 条走廊墙 |
| cmp3 sm24 role/single | 两组当前保存通过，0 改动 |
| Opus sm21/sm24/sm25 | 三组当前保存通过；前两组 0 改动，sm25 移墙 5 次 |
| Claude sm21 run57/run58 | 两组当前保存通过，各移墙 7 次 |
| Claude sm24 run55/run56 | 几何/语义通过且 0 改动；旧 `room` 枚举不兼容当前 catalog，仍不能算当前重新保存成功。既有保存源经当前 precision 检查均为 0 项 |

三档按互斥桶 `≤5cm / (5,10]cm / (10,30]cm / >30cm` 展示；A–C 表只统计当前保存通过的队列，旧枚举两组不混入：

| 队列 | 房间边界，前→后 | 沿墙门窗，前→后 |
|---|---|---|
| cmp3 成功 6 组 | 57/12/25/8 → 56/7/36/3 | 183/24/11/4 → 183/24/11/4 |
| Opus 成功 3 组 | 45/0/6/0 → 43/2/6/0 | 109/2/0/0 → 109/2/0/0 |
| Claude 当前保存成功 4 组 | 54/20/12/0 → 48/28/10/0 | 158/21/1/0 → 158/21/1/0 |
| E 原始 7 层 | 29/12/21/5 → 58/1/3/5 | 132/15/5/1 → 135/15/2/1 |
| 独立 F 可编译的 4 层，原稿→E→F | 24/1/7/4 → 32/0/0/4 → 32/0/0/4 | 77/2/2/0 → 79/2/0/0 → 78/3/0/0 |

对齐改善跨层一致性，不保证每项 GT 误差单调改善。E/F 原始队列保持第二轮结果：E 为 7/7；独立 F 为 4/5，第五层接 A 后通过。既有两扇 sm24 run7 门从 ≤5cm 退至 5–10cm 的记录和墨线证据仍在 JSON 中，未隐藏或归为本轮新问题。

[sm25 F2 的 E→F→A 衔接](reader_dimension_handoff.json)仍通过严格编译与 source 保存检查，precision 为 0。房间/开口/门/窗为 `16/30/14/16 → 15/30/14/16`：只消除已审计的无种子窄条 `F2_S06`；三扇窗宿主变化逐项被合并记录认领，门连接和命名种子不变。此探针不重复累计进上表原稿 A 消除数。

完整 H 双跑均为 9,350,672 bytes，SHA256 `67c9892bcfc8720b0cc99f38084615b4d4919026f54b79b41c6739e57ea53dc7`；handoff 双跑均为 186,106 bytes，SHA256 `2288ebcf5e19dfd761457760dcf4c7cfbed4cc8eb17032020a84007778f83e8d`。主代理在清理前独立读取两次产物与正式文件，确认三者逐字节一致，记录在[重复性核对](round3_repeatability.json)。

完整输入与边界见[回放笔记](replay_notes.md)，全部操作与消除条目见[逐项清单](itemized_changes.md)和[完整 JSON](replay_report.json.gz)。正式证据保留原始输入路径与 SHA，重放不依赖已删除的本轮临时副本。

## 3. 三例贯通、四项恢复与范围核对

本轮最终有效的 90 个定向条目全部通过，未跑全量。所有本轮 pytest 均显式使用 `-n 2 -p no:cacheprovider`，临时数据限于本轮目录。

| 定向文件 | 通过数 |
|---|---:|
| test_plan_regularization.py | 55 |
| test_bim_regularization_integration.py | 8 |
| test_building_precision.py | 9 |
| test_role_end_to_end.py | 10 |
| test_role_single_parity.py | 5 |
| test_role_compiled_plan.py | 3 |

正式六文件批次为 **90 passed，230.96s**，XML 为 [pytest_round3_acceptance.xml](pytest_round3_acceptance.xml)。之后将其中一个依赖内部调用顺序的测试替换为真实凹口/延续墙几何用例，同一 ID 补跑 **1 passed，4.18s**，证据为 [pytest_round3_final.xml](pytest_round3_final.xml)。该用例验证原宽 0.7m 的空间在拟移动后变成 0.5m 时，外皮事务与共线墙重试均结构化拒绝并回滚。生产代码始终冻结，汇总按同一条目的最新结果计数为 90，不重复算成 91。

三例 sm21/sm24/sm25 在真实冻结 MCP 上贯通通过；四个恢复边界均通过：读图员试建检查点、全部读图完成、建层写入回执后、声明事务回执后。两层 fixture 仍经过正常装配审阅门。离线 fixture 使用脚本化模型响应，因此这里验证工具贯通与恢复，不外推真实 work model 的识图或裁决质量。

通过 [prepare_offline_snapshot.py](prepare_offline_snapshot.py) 生成 q1 独占隔离快照，并用 `BIM_AGENT_REGISTRY_PATH` 指向 `round3-snapshot/agent_versions.json`。90 项完成后回读全部 89 个登记文件，哈希与测试前快照相同；共享版本登记原字节不变。[冻结输入证据](round3_frozen_inputs.json)保留完整命令、89 文件清单及哈希，隔离快照已按要求删除。

[检查汇总](verification_summary.json)单列第三轮批次、每项最新结果与 XML SHA，不把第二轮 154 项当作本轮重跑。XML 仅将 CRLF 归一为 LF，并确认解析后的 XML 树不变。历史 run99 的 75 步重放沿用前轮证据，本轮未重复；当前 legacy 分支在定向入口测试中覆盖。

[范围检查](scope_check.json)记录 Python 编译、LF、只读 Git 检查、生产 SHA 与函数级差异。runtime、共享版本登记、Q2 立面/装配/裁决及 role_state 代码未追加修改；session 仅保留第 1 项两处授权消费者。相邻 v1/q2、D 盘 runs-next/runs-cc 及主树 merged 运行未改动。初轮 `uv sync` 受 .git 只读限制后，本轮沿用 q1 现有 .venv 与 UTF-8 激活脚本。

work model、Paratera、DeepSeek 请求为 **0**。延续两个 `gpt-5.6-sol` / high 开发子代理分担 kernel 与离线回放，遵循派工的 5.6 优先约定；主代理负责集成、模型可见文字、独立证据核对和清理。生产范围仍是 domain 的 BIM rules/kernel/tools 与获授权的平面 reader 消费路径。

## 4. 临时目录清理与提交分组

已执行用户指定的 Python `shutil.rmtree`，删除本轮四个临时目录；删除后全部不存在。共 9,507 个文件、350,198,737 逻辑字节，约 334.0 MiB：

| 删除目录（均在 AI_agent/archive/local_backup/q1/） | 文件数 | 逻辑字节 | 删除后 |
|---|---:|---:|---|
| round3-kernel | 6 | 849,678 | 不存在 |
| round3-replay | 24 | 67,829,956 | 不存在 |
| round3-pytest | 9,476 | 280,981,816 | 不存在 |
| round3-snapshot | 1 | 537,287 | 不存在 |

[cleanup_round3.py](cleanup_round3.py)先验证全部绝对目标在 q1 本轮白名单内，拒绝 Git 元数据及未知 reparse point。首次预检在删除前发现 18 个 pytest `current` 符号链接而停止；逐个核实目标都位于各自本轮目录内后，统计时不遍历链接，交由 Python 标准库移除链接本身，再完成四目录删除。完整路径、计数、链接目标和删除后状态保存在[清理记录](cleanup_round3.json)，目录归属在[创建记录](round3_temp_ownership.json)。

正式日志、XML、输入证据、前两轮归档保留；此前轮次 scratch、其他工作树、运行中的整案和所有 Git 元数据不属于本次清理目标。未提交、未修改共享版本登记，版本统一由 Opus 合并后处理。

建议提交分组（仅供 Opus 合并）：

1. **A–D 几何与保存门**：`plan_regularization.py`、`building_precision.py`、`plan_partition.py`，Toolkit 建层/修改/装配与 source 保存门、审计摘要及行为测试；含本轮跨层外皮、宿主/接头随动与回滚。
2. **E–G 读图校正与指引**：墨线/尺寸模块、trial/readers/plan_format/submission、平面指引与参考、相关 fixture/测试；含本轮外轮廓规则文字及清单展示。
3. **授权 session 消费者**：`session.py` 的 `run_reader`、`_build_from_artifact` 与 `test_role_compiled_plan.py`，由 Opus 与 Q2 同文件改动协调合并。
4. **H–I 验证与交接**：冻结 MCP 贯通/恢复 fixture，三轮证据、回放脚本、逐项清单、XML/汇总、冻结/重复性核对、清理脚本及记录、本 README。
