# 09-12 sm24 换例与轻量模型分工

开工 `ea5e68d9`，main干净且已同步。此次只做还原建模，使用 `case_tests/e2e_tests/sm24_anchor/case_data` 的五张原始PNG，包含平面和四立面，不使用该目录的旧提示JSON、旧候选、旧reading或GT。沿用已验证工具，没有为了本批修改生产逻辑。

`run_cold_start.py` 保存整案任务和720秒预算。Claude订阅Sonnet级组织整案，任务明确要求早期通过现有 `review_detail` 委派一个Haiku局部证据任务，局部范围和采信由总Agent选择。这是本批检验分工的安排，不是产品强制固定工序。Haiku子任务只得到所选原图与问题，输入/回执/实际图像/输出原样保留；主助手不改写观察或填正确答案。

5.6 Terra负责准备只在生成结束后运行的独立评价脚本，主助手负责原图实验与实际工具反馈核验。typed GT留在评价侧，不能将评价或开发判图结果送入生产输入。没有DeepSeek、付费API、EP或部分推理。

结果入口：[sm24 run01](../2026-09-12_bim_agent_sm24_run01/README.md)。

## 结果与下一入口

run01 已结束：Sonnet 629.88 秒后触发订阅 429，保存一份 9 空间/11 窗/11 门候选，未实际看源图或 finish_bim。Haiku 实质局部任务已完成，但窗数/尺寸段判断错误，父问题还有错误高度预设。实际源分区 severe，窗坐标诊断基本一致；全部边界见 run01 README，不视为整案成功或分工有效。

`evaluate.py` 在有最终 summary 后读取 typed v3 参照；即使模型因额度/超时未正常结束，也评价其真实保存交付。保持原世界坐标、采用独立分区的楼层映射，同层/同立面/同类型且数量一致才列坐标差；不套用 sm21 旧版窗评分、不拟合镜像。`verify_execution.py` 核父/子实际图片返回与子任务隔离。三份执行/评价检查与两份离线浏览器检查均已实际完成，源图未看如实为 false。

`run_partition_recovery.py` 是下一次从 run01/candidate_01 恢复的准备入口，600 秒、独立新 run，仅传旧 proposal 和五原图。范围为源分区/连续空间、受影响门宿主及实际源反馈；不提供正确房间数、错墙 ID、原图像素答案或 GT。没有强制再次委派，若使用局部观察则要求不预填答案。**仅编译和 `--dry-run` 核对，未执行第二次模型调用**；请求预览见 recovery_request_preview.json。Claude 额度恢复后使用新输出目录运行：

```sh
python AI_agent/logs/experiments/2026-09-12_sm24_delegation_setup/run_partition_recovery.py --out AI_agent/logs/experiments/2026-09-12_bim_agent_sm24_run02
```

不因普通任务授权改用付费 API、DeepSeek 或未经验证的替代视觉通道。旧实验保持原样，下一次恢复必须独立统计。
