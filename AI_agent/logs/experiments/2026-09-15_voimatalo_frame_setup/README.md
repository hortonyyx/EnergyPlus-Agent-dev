# 09-15 Voimatalo 坐标恢复实验准备

原单体GLB、原声明和上一程原网格生成的candidate_02；不提供新角度、GT或开发预制视图。开发限定为坐标关系恢复，保留数值几何，以区分方向改善和外形/内部修复；不是冷启动或整案完成。Sonnet medium现有订阅，1800秒上限，无付费API、DeepSeek或回退。实际命令见command.json，运行结果独立保存于同级frame_run01。


run01在527.64秒由开发结束：大清单回执不可读且重复请求，首份-76°候选错转未采用。旧码技术审计完成后，增加按楼层/分页读取，修复源墙仅部分邻接时的外露片漏画；`partial_contact_replay/`保存旧源42.8m²外露片恢复证据，不改源。run02用`command_run02.json`/`run02.py`，仍从原先候选出发，补充先看旧坐标基线、以整栋形状核90°/180°方向歧义的方法提示，无新数值答案。不是单因素消融。


最终run02正常完成549.75秒，查看与限制见[结果](../2026-09-15_voimatalo_frame_run02/README.md)。复现浏览器核验使用已有环境：`PYTHONPATH=/tmp/ep-bim-browser-qa/lib/python3.12/site-packages PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers python .../check_viewer.py RUN`；这里只复用了当前机器已存在的隔离Playwright及浏览器，不是项目普通Python依赖。新机器需另行准备浏览器环境。
