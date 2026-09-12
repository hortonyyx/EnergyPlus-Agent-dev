# 原图证据与具体墙段对应

本批补现有回叠，既显示完整模型墙段也显示尺寸原始端点。位置计算依赖调用方标定，不对尺寸引出线或宿主正确性做自动结论，不修改几何。

- [离线检查](offline_validation.json)：32项相关检查通过，字体回退调整后定向5项通过，范围重叠不相加。
- [开发侧原失败预览](known_host_preview.png) / [位置记录](known_host_projection.json)：仅为重放核对，采用run17源与run16原标定；不是可靠标定、合并候选或生产输入。主助手已查看，证据点与南排宿主明显分离。
- [独立实验启动脚本](run_recovery.py)：新建run18，从run17/candidate_02恢复，六原图与proposal，无正确宿主、坐标或GT注入。Claude订阅Sonnet级，480秒，无DeepSeek/付费API/EP。
- [实际回叠核验脚本](verify_feedback.py)：生成后校验源/图像/标定与投影重放，并解码模型实际收到的image block逐像素核对；不以成功运输认证读图正确。

[run18实际结果](../2026-09-12_bim_agent_sm21_run18/README.md)：已通过原图/回叠改正北南墙段归属，物理几何未变，标定仍有约5.3%跨轴差。随后用[独立冷启动脚本](run_cold_start.py)只给原图新建run19，结果单独核验；完整过程见[本轮交接](../../worklog/2026-09-12_reconstruction_wall_host.md)。

后续原图冷启动[run19](../2026-09-12_bim_agent_sm21_run19/README.md)取得平面分区pass，但窗对照失败、模型删除了六条未建门。`5fed31a5` 给原宿主失败附上源绝对高度范围，相关22项通过；[原失败重放](opening_failure_replay/report.json)仍保留六门与拒绝状态，明确说明楼层/门高度冲突。以[短恢复脚本](run_opening_recovery.py)从未删除门的candidate_02另建run20，不提供正确高度或GT。

[run20结果](../2026-09-12_bim_agent_sm21_run20/README.md)：32.32秒内保留原门声明并改正绝对高度，六门及六连接建成，当前14空间/12窗/14门。原图冷启动分区pass与窗4/15配对分别保留；未重读原图或修窗，不能算整案成功。全部当前状态以[交接](../../worklog/2026-09-12_reconstruction_wall_host.md)为准。
