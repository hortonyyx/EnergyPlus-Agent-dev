# sm21 整案回归定位（09-27）

状态：两组已结束并核验。Astra独立实施，无开发子代理；没有生产代码变更。单独精简常驻指引未恢复旧质量，不采用该变体，未证唯一根因。

先核对run58与run69的实际输入、首次错误时序及保存声明重放，再做一组有界对照。旧较好结果继续保留，不将局部恢复或用途/依据覆盖率作为整案成功。

## 两组条件

两组均为sm21六原图、与run57/58/69完全相同任务、当前代码和全部39工具、当前按需参考及反馈、Claude订阅Sonnet/medium、3000秒、24候选、0续查。保留命名、类型目录及尽量合理选型/少unknown政策。生成侧没有旧BIM/标定/观察、GT、参考数量或开发者局部答案；运行中不干预。

- run71/current：当前完整常驻指引。
- run72/baseline_policy：旧468d83f7通用指引加当前合理选型、类型/命名参考入口和额度说明；移除后来增加的用途补依据、常驻证据裁图/视图引用复核段落。具体唯一差异见`guidance.diff`，工具、按需参考、反馈不删。

这检验的是一组常驻指引的整体影响，不能区分组内各段，也不是完整旧运行环境复现。两组均关闭续查以隔离首次生成，不能据此判断续查总体效果。单组/单对结果不能证明统计因果或恢复稳定性；若结果不支持假设，保留当前生产实现并记录。

## 可复查入口

统一从仓库根用`python -m AI_agent.logs.experiments.2026-09-27_sm21_regression_setup.<模块>`：

- `preflight`：将所有历史成功候选重新导出到临时目录，逐字段核物理几何/宿主/连接；只写本目录结论，原实验不变。
- `run_pair current --run NEW_NAME`或`run_pair baseline_policy --run NEW_NAME`：拒绝覆盖旧run；先冻条件/实际指引哈希，调用结束后保存生产文件快照。实验覆盖只在父进程`GUIDE`变量，MCP继续使用当前全部工具及参考；实际订阅请求保存完整system_prompt。
- `audit_run RUN_PATH`：生成结束后核哈希、实际模型、装配及源/显示重放；复用固定原图门窗参照和GT容差，并查实际图像运输及离线浏览器。GT只在此阶段载入。

没有生产代码修改、付费API、DeepSeek、EP或产品子代理。指引实验、原图生成和事后评价分别留证。

## 实际结果

| 条件 | 原图位置 | 空间/开口/连接 | 主要遗留 |
|---|---|---|---|
| [当前指引run71](../2026-09-27_sm21_guidance_control_run71/README.md) | 25/29，宿主29/29、连接14/14 | 14/29/14 | 二层北走廊墙约19cm偏位；首层南小窗和东窗高度不符；分区severe |
| [精简指引run72](../2026-09-27_sm21_guidance_ablation_run72/README.md) | 原始0/29 | 14/28/13 | 把mm填进m字段，XY放大1000倍；漏南外门，套错首层窗型；分区severe |

run72仅在临时目录按模型自己写的mm依据作XY÷1000诊断，得到14空间匹配/分区minor、已建28位置与宿主/13连接对应。该结果只区分单位与拓扑，不是模型自主修复或采用模型；原始成绩不变。两组均无实际源立面查看，图面回叠和自报关系不足以发现错尺度/错窗型。原图对应不能由16项高度关联或14项用途依据替代。

两次实际claude-sonnet-5主调用合计2258.22秒，CLI估算$9.013289（非账单；两run等待有重叠，不是总墙钟耗时）。当前同一工具仍能生成较run69更好的位置结果，但没有恢复run58的完整质量；单对结果不支持将新增指引列为已证根因，更不支持把退步简单归结为模型波动。

## 本轮验证和证据

- `historical_replay.json`：10份旧成功候选全部物理字段精确重放；旧好稿与退步稿首次输入相同。
- `historical_view_replay.json`：60份历史主调用原图PNG返回字节与当前重放一致。
- `historical_stage_positions.json`：好稿首次整栋/最终均29/29；退步稿首次整栋/最终均11/29，错误早于续查和height claim。
- `cli_initialization_comparison.json`：run58/69/71/72实际均Sonnet 5、Claude Code 2.1.280；工具36→39，不能将退步归因已证的CLI版本更换。
- `pair_conditions.json`、`pair_results.json`：实际40生产文件、原图/设置相同，唯system_prompt不同；两组完整结果。
- 两run的`postrun_audit.json`、`evaluation/view_reference_audit.json`、`browser_qa/`：源与显示、装配、69处实际原图视图、两层离线显示/旋转/点选通过。
- 主Python没有playwright；浏览器验证复用已有环境，不安装新依赖：`PYTHONPATH=/tmp/ep-bim-browser-qa/lib/python3.12/site-packages python -m AI_agent.logs.experiments.2026-09-27_sm24_room_types_setup.browser_check RUN_PATH`。`audit_run`与浏览器分开运行。
- `diagnose_units`：仅生成run72事后单位诊断，不修改原结果。所有普通验证为离线确定性检查，本轮无新增生产改动，因此不重复pytest全量。

下一项先控制同一常驻指引，对比旧成功运行底座（保留命名/合理类型语义）与当前工具清单、自动反馈及按需参考的差异。先保存记录/重放筛选，再最短明确对照；不要继续同条件抽样、宣称缩短prompt已经修复，或以本例答案加硬编码。公制标定、不同窗型和实际源立面检查是观测点，不先再造新工具。
