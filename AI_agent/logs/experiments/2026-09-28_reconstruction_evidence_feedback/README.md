# 观察与实际几何反馈节点

本节点完成离线开发和用户明确批准的1次整案回归。run86正常结束，质量未恢复：二层漏墙错并、小窗错宽及外门窗高度误判仍在。已结束本批，无重试、委派或额外模型调用。CLI2.1.280，实际`claude-sonnet-5`，不把单次正常调用当成长期可用性保证。

[实际回归结果](../2026-09-28_sm21_evidence_feedback_run86/README.md) · [逐对象复核](../2026-09-28_sm21_evidence_feedback_run86/manual_review.json) · [27次历史质量记录](quality_report/README.md)

## 已实现与验证

- 世界长度槽支持显式`{value, unit}`，m/cm/mm由代码换算，旧数字仍为米，像素不缩放。原提交、数字稿及换算记录分开保存；错误单位拒绝建模但保留稿件。
- 建模反馈显示实际轮廓跨度、标定比例、门窗宽高；局部修订显示实际开口前后变化，含标定造成的间接变化。没有绝对尺度门槛或自动改图。
- 现有`check_openings`在已登记平面标定下核原图观察框是否包含源开口两端；错误编号对应不再仅因房间/类别一致而通过。立面/未标定范围明确不核平面位置；标定改变后旧位置复核过期。
- 重用已有“观察到但未建”的记录，不从像素自动识别漏窗。未提交的观察仍无法自动发现，观察框很宽或开口偏短仍可能满足包含关系，不能据此声称完整几何保真。

94项不同相关检查通过（39项量测/修订/平面/门窗检查、47项MCP与交付、8项本次缺陷反例）。后续标定过期处理相关16项重核通过，包含在94项中，不重复计数。测试命令与结果见[验证记录](verification.json)。

## 真实失败重放

[重放摘要](replay02/summary.json)核run84/run85共393个原文件未变：

- run85原裸数字稿的实际跨度约15000×8000m；开发仅给四个标定世界值添加mm标签，新保存源为15×8m。其他声明、楼层/开口高度不变；原漏东窗/错高度未修。[记录](replay02/unit_result.json)，[保存源](replay02/units_run85/candidate_01/source_model.json)。
- 原样重放run84五门返工，仍可编译；反馈明确两门0.9698276m→1.8642241m，其余未涉及门窗保持。这里保留错误，用来证明反馈可见，未采用为正确结果。[记录](replay02/revision_result.json)。
- 开发从原图提供北侧中部门框，已建门编号/宿主正确但位置错，新增位置检查报错；南小窗以未建观察返回现有漏项。[观察与检查](replay02/observation_result.json)。这些是开发辅助反例，不是工作模型自主发现。
- run53–58、83–85共23份旧数字稿，20份编译提案完全相同、3份保留原错误。[兼容结果](replay02/compatibility.json)。

首个重放在新测试脚本的浮点严格相等断言停止，未进入建模；原目录保留。改为1e-8数值比较后另建`replay02`完成，不覆盖首次记录，不改生产容差。

```bash
python -m AI_agent.logs.experiments.2026-09-28_reconstruction_evidence_feedback.replay --out <new-output-directory>
```

## 本次明确批准的回归

1次sm21六原图冷启动，独立run86；相同既有完整建筑任务，不给旧稿、具体错处、数量或GT。单Sonnet/medium、既有Claude订阅，3000秒、24候选，0续查/局部模型/重试/付费回退。预估消耗只能参考历史CLI标价，约数美元级，不是订阅账单；本批上限为一次主调用。

验证新反馈是否实际采用，以及房间/隔墙/门窗/连接、单位/跨度、高度和可查看交付是否保住。独立原图/GT评价在生成后进行，原容差不改；缺失与错误关系优先于厘米偏差。单次结果不证明稳定恢复，无采用不算方法效果；中断保留unknown。若无整体收益，先重新评估范围/旧基线逐包路线，不追加同条件抽样。

[冻结条件](frozen.json)含41个生产文件、六图、任务及参考散列；[真实入口/MCP预检](preflight.json)在模型进程边界阻断、预检模型调用0，确认参考实际返回。随后用户明确答复“启动这1次回归（推荐）”，[批准记录](approval.json)绑定冻结散列；[执行回执](execution_receipt.json)确认仅1次，无重试。

```bash
python -m AI_agent.logs.experiments.2026-09-28_reconstruction_evidence_feedback.batch prepare
# 以下run已执行，禁止用此记录重复启动：
python -m AI_agent.logs.experiments.2026-09-28_reconstruction_evidence_feedback.batch run
```

`approval.json`须记录本批用户原指令并绑定`frozen.json`散列；脚本不自动重试，不覆盖已有run。工程检查不代替项目约定的节点回归批准。

## 回归结论与边界

1189.87秒正常完成，6个候选，最终两层13空间、15窗、14门、14条已记录连接；15×8m跨度和3.0/3.6m层高保持。旧固定坐标系原图位置6/29、宿主22/29、连接9/14，严格分区severe。本次Y向下，与参考相反；另存仅反转Y方向的诊断，位置17/29，既有观察/容差/原成绩不变。诊断宿主29/29、连接14/14仍把两个原房间映射成一个宿主，不能覆盖二层南中部漏墙错并。

小窗已建却取错标注段，约0.365m而非1.2m，且套用普通窗高；一层东窗头高差0.2m被旧0.3m容差接受。两外门由假设2.7m误改为3.0m，原图约2.1m。17个外开口高度有图像绑定不等于高度正确。第一次返工错移隔墙后，第二次据图把门宿主改回东房，体现局部有效修订；门端点仍有误。最后用途编辑保持几何，但旧门高待核备注未完全清理。

实际尺寸反馈4次、修订变化2次，读取的6份参考散列与冻结内容一致；未读reconstruction/opening_review，显式单位、量测绑定、原图门窗框均未采用。不能用这一条证明未采用功能有效/无效，也不能把本次退步归因于新包。源/装配重放、41文件/六图、29次原图返回字节/像素和双层离线浏览器检查通过，均不代替建筑质量。

生成后核查命令（均0模型调用；方向诊断输出拒绝覆盖）：

```bash
python -m AI_agent.logs.experiments.2026-09-28_reconstruction_evidence_feedback.evaluate_run AI_agent/logs/experiments/2026-09-28_sm21_evidence_feedback_run86
python -m AI_agent.logs.experiments.2026-09-28_reconstruction_evidence_feedback.audit_feedback AI_agent/logs/experiments/2026-09-28_sm21_evidence_feedback_run86
python -m AI_agent.logs.experiments.2026-09-28_reconstruction_evidence_feedback.audit_orientation AI_agent/logs/experiments/2026-09-28_sm21_evidence_feedback_run86
python -m AI_agent.logs.experiments.2026-09-28_reconstruction_evidence_feedback.summarize_run AI_agent/logs/experiments/2026-09-28_sm21_evidence_feedback_run86
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-26_sm25_height_review_setup/browser_check.py AI_agent/logs/experiments/2026-09-28_sm21_evidence_feedback_run86
python scripts/tool_scripts/bim_regression_report.py AI_agent/logs/experiments/2026-09-28_reconstruction_evidence_feedback/quality_runs.json --out AI_agent/logs/experiments/2026-09-28_reconstruction_evidence_feedback/quality_report
```

本包关闭，保留工程修复与全部失败证据，不以继续叠提醒/同条件重抽推进。下一入口改为离线收敛旧较好基线逐包加回的具体范围，重点区别首稿对象解释、图像坐标与能力增量；run81旧树也未完整恢复，不能把回旧树本身当成修复。新增整案另备具体方案再提请，当前不启动迁移或新批次。
