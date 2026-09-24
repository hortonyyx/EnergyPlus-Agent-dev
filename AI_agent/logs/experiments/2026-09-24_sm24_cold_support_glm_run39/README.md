# sm24 原图冷启动 run39

GLM订阅`glm-5.3-flash`、medium，单次1325.70秒；原图一张、无旧稿/标定/建筑JSON/GT。冻结run38实现，明确要求完整路径支持回查。完整过程见[工作记录](../../worklog/2026-09-24_reconstruction_cold_support.md)，输入/重跑见[设置](../2026-09-24_sm24_cold_support_setup/README.md)。

模型独立生成8空间/11窗/10门/10连接，连续走廊和东南折墙保留。空间8/8一一对应、宿主21/21、门连接10/10；原始原图位置14/21、分区severe（4空间边界约11cm偏移），声明框架诊断位置20/21、分区仍severe。高度全部假设，GT三维severe，不能作为完整还原验收通过或重复稳定证明。全路径工具在唯一有效候选后调用，未触发后续改形；附近墨线支持不证明墙代表线准确。

- [模型查看](candidate_01/viewer.html) / [源平面](candidate_01/plan_F1.png) / [原图独立叠合](evaluation/independent_original_overlay.png)
- [原始评价与源/显示核验](postrun_audit.json) / [冷启动核验摘要](evaluation/cold_start_audit.json) / [声明框架诊断](evaluation/declared_frame_diagnostic.json)
- [真实调用轨迹](evaluation/observation_and_edit_trace.json) / [候选轨迹](evaluation/candidate_trajectory.json) / [完整路径反馈](plan_wall_support/support_001.json)
- [实际反馈图像验证](evaluation/actual_feedback_images.json) / [25图运输](transport_audit.json) / [流无损归档](stream_archive.json)

源/显示精确重放，25图可解码、20图与保存RGB相同，viewer无远程脚本；未验证浏览器WebGL交互。CLI估算$1.857008非订阅账单。原始模型自评保留在agent_receipt.json，独立结论以上述生成后评价为准。
