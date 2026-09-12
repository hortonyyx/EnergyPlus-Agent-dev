# 09-12 立面与窗恢复准备

从 `run20/candidate_01` 的冷启动派生候选另起 `run21`，六原图与旧 proposal 是生产输入。开工代码 `6b51b19d`，沿用现有工具。`run_recovery.py` 保存完整通用任务：按原图核楼层与窗，保留房间、门和连接，不供正确窗数、坐标或 GT。Claude 订阅 Sonnet 级，600 秒，无 DeepSeek、付费 API、EP 或部分推理。

run21补回3窗、改3窗，但剩五扇一层窗高仍错且没有实际源查看。随后 `7d19f876` 新增 `view_elevation_candidate`，22项几何/stdio相关测试通过；主助手实际查看后修正图例越界和字体不支持的符号。`run_height_recovery.py` 从run21/candidate_03另起run22，480秒，只核垂直位置并要求原图/源立面前后查看，不提供正确高度或GT。新源立面渲染由5.6 Terra实现，主助手接工具、图像反馈和实际验证。底层12项测试与上述22项有重叠，不加总。

原图独立审查委派现有 5.6 Terra 子代理，主助手负责实际实验和核验；审查记录不进入生产输入。GT 对照严格在生成结束后运行。

验证复用上一批脚本：

- `../2026-09-12_wall_host_setup/verify_artifacts.py RUN`：冻结输入/实现摘要和源摘要。
- `../2026-09-12_feedback_recovery_setup/verify_presentations.py RUN`：模型实际收到的原图像素。
- `verify_recovery.py RUN`：实际源房间/边界/门/连接保留、窗变化和源平面/立面返回图片；立面额外从实际源重放，核对像素及完整元数据。
- `../2026-09-12_wall_host_setup/evaluate_cold_start.py RUN`：只在生成后独立评测分区与建成窗。
- 既有两个 `browser_check.py`：离线交付加载、两层显示与旋转。

这些核验各有范围，不将显示成功、回查与模型观察一致或几何通过当作原图还原成功。[run21](../2026-09-12_bim_agent_sm21_run21/README.md)实际补3窗，窗10/15但无源查看；[run22](../2026-09-12_bim_agent_sm21_run22/README.md)实际看6张源立面并修5窗高度，窗15/15、分区pass，保留全部房间/门/连接。后者是已有候选恢复，不是冷启动成绩。
