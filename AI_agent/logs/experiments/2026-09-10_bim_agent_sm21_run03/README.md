# sm21 保存候选恢复：方向纠正，开口仍未过关

本次是 **saved_candidate_recovery**，从 run02/candidate_02 的方案和六张原图继续，非新冷启动。只导入 proposal，生产检查在新 seed 重建；旧 GT 对照、开发读图审查和旧报告均未交给模型。开发助手指定检查“坐标约定和开口身份”，没有提供正确坐标、门数或 GT 答案。

- 正常结束 312.54 秒；首修订距首次工具调用 84.70 秒。两版新候选均可查看，14 空间、84 源边界、15 窗、18 门，几何自洽通过。
- 模型根据原图和方案引用自主发现方向矛盾，选择整体 y 反射；代码统一变换空间、窗方向/坐标和门坐标，保留对象 ID。独立分区比较从前轮 severe 改为 pass，两层缺失/额外内边界均为 0；外窗对应从 7/15 提升到 14/15。
- 模型/Haiku 复核确认二层无办公室互通门，却将两处错误连接改成走廊门并保留旧门，形成重复。一层另有两处不受原图支持的门；二层多扇门的位置仍错。一层南侧入口旁窗仍不匹配。因此**整体开口保真 severe，不能当成合格 BIM**。
- 生成侧只用生产几何检查，没有接收事后评价。原图复核见 evaluation/door_review.md；这是开发助手视觉核对，GT 内门清单不完整，不能冒充自动 GT 验收。

## 工具、时间和费用

主模型实际 claude-sonnet-5，medium effort；一次 Haiku 局部复核实际 claude-haiku-4-5-20251001，84.96 秒。主模型估算 $0.8259698，局部复核 $0.0853594，总估算 $0.9113292；这是 CLI 用量估计，非订阅账单。

43 条成功工具记录：主模型 24、子模型 19。两次 revise_bim、四次候选平面查看；未使用 pixel_profile/map_pixels。子模型多次裁图定位才看清，不据此宣称量测能力已验证。工具/提示/effort/恢复输入均较前轮变化，不是单变量对比。

## 查看与复现

- [结果入口](index.html)、[最终候选](candidate_02/viewer.html)、[独立分区/窗对照](evaluation/index.html)
- [请求和指导](agent_request.json)、[输入/实现摘要](inputs.json)、[轨迹统计](trajectory_metrics.json)、[原始生产总结](summary.json)
- 每版 operations.json 保存变换和门改判，原方案不被覆盖。流式 JSON 已无损 gzip，校验摘要见 compressed_streams.json。
- run03 使用的入口脚本保存在 implementation/run_bim_agent.py，字节摘要与 inputs.json 一致。后续 run04 给图片响应补充原尺寸/裁图范围/缩放元数据，其结果单独记录。

命令：

```bash
python scripts/tool_scripts/run_bim_agent.py run \
  --images case_tests/e2e_tests/sm21_anchor/case_data \
  --out AI_agent/logs/experiments/<新的恢复目录> \
  --resume-candidate AI_agent/logs/experiments/2026-09-10_bim_agent_sm21_run02/candidate_02 \
  --scope '<agent_request.json 中的原 scope>' --timeout 600
```

当前代码已增加图片坐标说明；严格复用 run03 行为需使用 implementation 快照。未调用 DeepSeek、付费 API 或 EnergyPlus。
