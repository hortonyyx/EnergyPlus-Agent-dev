# sm21 原图冷启动：legacy profile反馈

已完成，尚未恢复旧基线。candidate_08保留2层/14空间/29门窗/14连接；原图位置20/29、宿主29/29、连接14/14，严格分区severe，具体大小及高度错误见[原图语义复核](evaluation/semantic_review.md)。本次不替换旧采用基点。

[打开交付查看器](candidate_08/viewer.html) · [源BIM](candidate_08/source_model.json) · [独立审计](postrun_audit.json) · [浏览器证据](browser_qa/report.json)

用户批准的两次对照之一，六原PNG、无旧BIM/量测/GT/中途提示；Claude订阅实际claude-sonnet-5/medium，1次主调用，955.91秒，CLI估算$4.494975（非账单），0续查/子调用/重试。生产基点87f8eae8，40文件快照及实际39工具/指引/参考哈希已核。

成功pixel_profile回执12次，新增反馈送达=False。本组结果须结合[完整两组条件和限制](../2026-09-27_sm21_profile_feedback_setup/README.md)理解；单次差异不证明稳定性或退步根因。
