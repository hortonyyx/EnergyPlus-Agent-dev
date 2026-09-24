# sm25 首层原图换例设置

只向GLM提供 `inputs/1f_view.png`，来自run30保存的原件副本；不提供旧候选、墙网、标定、房间/门窗数量、建筑声明或GT。沿用run39/40通用scope，预算由1800增至2400秒，实际订阅路由仍 `glm-5.3-flash` / medium，无其他通道回退。原图、scope、生产代码散列分别冻结。

## 先发现并修复工具范围缺口

run41启动后开发预检发现原像素编译器只接受矩形轮廓，而sm25原图为凹形；在首份声明前主动中止（55.77秒、无候选），保留回执与无损压缩流。不是模型质量失败，也不是成功冷启动；开发原应在调用前检查这一能力边界。

现复用已有源出口对逐层 `footprint.vertices` 的支持，保留完整正交凹形，不填包围盒。窗朝向由标定后逆时针轮廓的实际边计算，支持凹入外墙；门窗完整宿主、越界/跨接头检查保持。无需新几何schema或手工改源。矩形产物未变：[run39/40编译重放](rectangular_replay.json)。

验证：`tests/test_plan_partition.py`、`tests/test_bim_agent_plan_partition.py`（新测试加入前）及`tests/test_parametric_proposal.py`合跑18项通过；新增凹形工具源/回叠测试1项、既有全路径stdio测试1项通过，共20项不同检查。包括凹口面积/原环保持、凹入窗实际顶点与朝向、翻转标定、内外门连接、保存重放、跨凹口窗拒绝以及既有错误反馈。不新增全量成绩。

run42用新代码重新独立启动，scope与原图不变，未继承run41观察。启动脚本：[run_supported.py](run_supported.py)，配置：[frozen_supported_method.json](frozen_supported_method.json)。`run_cold.py`及旧冻结文件记录中止实验，按当前代码执行会因预期的哈希变化拒绝。

## 评测隔离

[原图独立观察](original_observations.json)在run42首份声明前冻结，参考来自原图灰色墙带中线和青色门窗符号；14个空间、15窗、16门仅属评测清单，不进入模型输入。参照含完整连续走廊和两个凹入处，[核对图](evaluation_reference/annotated_reference.png)可查看。25000/20000总尺寸及界线定义独立米制框架；内部墙取中线，外墙也取中线，因此与外皮基准的差异须单列。

[audit_run.py](audit_run.py)只在生成结束后执行：源与显示精确重放、原图分区/门窗/连接比较、按模型声明锚点反解的诊断、未改写GT首层三维诊断、真实图像运输及无损归档。声明框架转换不拟合候选，不修改源或替代原始评分。无资料高度不参加平面验收；内部门高度带假设不阻塞。GT二层不属于本次输入范围。

```bash
python -m AI_agent.logs.experiments.2026-09-24_sm25_cold_support_setup.audit_run --run AI_agent/logs/experiments/2026-09-24_sm25_cold_support_glm_run42
```

真实建模结果见[run42记录](../2026-09-24_sm25_cold_support_glm_run42/README.md)：冷启动未通过，假墙错拆走廊、漏西侧下部门。生成后的[开发局部重放](developer_repair_diagnostic/summary.json)用`diagnose_repair.py`仅替换一条墙路径并补一门，恢复14空间/31开口/16连接且保持其余几何，证明工具可表达正确关系；不是GLM自主修复。未按评测答案改写原成绩。下一项是局部修改已存墙网时可靠保留其余声明。
