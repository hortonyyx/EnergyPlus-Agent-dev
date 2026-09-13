# sm24 分区恢复 run02：东外门修复，分区仍失败

[交付查看](delivery.html) · [源 BIM](candidate_01/source_model.json) · [独立分区报告](evaluation/index.html) · [原图复核](evaluation/visual_review.md)

从 09-12 run01/candidate_01 的 proposal 和五张原图独立恢复，沿用原先已准备的 600 秒任务，未给生成模型正确房间数、错误墙 ID、像素答案、历史好 reading 或 GT。生成侧脚本/内核无改动；GT 只在 summary 保存后的独立评价读取。本次是有范围提示的候选恢复，不是新冷启动。

## 结果与限制

375.54 秒正常结束，Sonnet 自行选定 candidate_01，保存 **9 空间 / 58 边界 / 11 窗 / 11 门 / 11 连接**。东侧门由约 0.96m 恢复至原立面标注的 1.60m，随之调整走廊和相邻会议室的一段共墙。11 窗世界坐标、其余门的物理几何及连接保留。几何自洽通过，离线浏览器加载、楼层切换和旋转通过。

**分区仍 severe，未完成此次主要恢复目标。** 西侧连续办公室仍被多一道实体墙拆开，接待区仍严重压缩，右下折角仍失真。模型末答声称所有分区已核验、没有错误拆分，与原图及独立评价冲突。门宽修好不证明用来承载该门的相邻房间范围正确。

本次实际执行了原图回叠、源平面查看、开口清单及 finish_bim；但未提交图像标记式门窗回查。最终叠图使用的顶侧 y=127、右侧 x=620 被称为墙内皮，原图直接核对均不成立；约0.55%的横纵比例差不能代表锚点正确。仅靠提醒查看和回叠，尚未形成可靠的分区纠错。

## 执行与费用

复现命令（另选不存在的输出目录）：

```sh
python AI_agent/logs/experiments/2026-09-12_sm24_delegation_setup/run_partition_recovery.py --out AI_agent/logs/experiments/2026-09-13_bim_agent_sm24_run02
```

实际主模型 `claude-sonnet-5`、medium，使用既有 Claude 订阅；无付费 API/DeepSeek/EP/部分推理。一次主订阅调用，无 review_detail 局部委派。CLI 记录少量 Haiku 内部辅助量，与读图委派区分。主输出 29471 tokens，CLI 总估算 $1.5597264，非订阅账单；完整用量见 agent_receipt.json 和 summary.json。

复用已有 evaluate.py、verify_execution.py 和两份浏览器脚本实跑。实际图像/源运输核验、原输入/实现摘要、源改动及限制见 [执行核验](execution_verification.json)、evaluation/visual_review.md 和 [楼层浏览器结果](browser_F1/summary.json)、[交付浏览器结果](browser_delivery_check/summary.json)。主助手实际查看了最终浏览器图和最终回叠图。没有生产代码变化，不新增或重跑无关 pytest。

原候选和观察回执完整保留。继续的局部方法试验见 [平面图证观察](../2026-09-13_sm24_plan_observation/README.md)，它单独记账，不倒写为本次恢复成功。
