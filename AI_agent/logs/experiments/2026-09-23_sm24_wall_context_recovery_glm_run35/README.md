# sm24 原图墙网有界恢复

[查看最终候选](candidate_02/viewer.html) · [原图回叠](image_overlays/overlay_002.png) · [申报坐标分区对照](evaluation/declared_frame_partition.html) · [节点证据与限制](../../worklog/2026-09-23_reconstruction_wall_context.md)

从run32失败墙网继续，开发指定东侧分隔、走廊折角和顶部内门；仅原平面和旧失败声明，无成功答案、旧局部回答或GT输入。GLM现有订阅`glm-5.3-flash`/medium，965.66秒，CLI估算$1.5267848（非账单），已结束。

选定candidate_02：8空间/11窗/10门/10连接，东北漏墙与东南折角已修；19个旧开口三维顶点保持，仅顶部内门和东南内门修改。源/显示精确重放、实际图像传输核验通过。

原稿坐标上下翻转按本次范围保留，因此原始原图/GT评分仍severe。仅在独立诊断中反解候选原申报标定后，完整空间8/8、minor；21/21宿主、10/10连接、20/21开口位置匹配。未改DA门端点差约8.25cm，所有高度是假设。诊断没有修改候选或替代原始评分，当前不覆盖旧完整采用模型，也不算自主冷启动成功。

`plan_drafts/draft_001`为旧稿重建；`draft_002`含零长占位墙被拒绝；`draft_003`生成最终candidate_02。恢复最终候选用`--resume-candidate`；继续墙网可用本次draft_003，不能误拿初始重建稿。

本次6次原图查看、11次普通profile、3次编译、2次局部源回叠、1次选定。未用新增双轴profile回执、未调用子模型；不能将恢复改善单归因于新工具。没有浏览器WebGL交互验收。运行/评测脚本见[实验设置](../2026-09-23_sm24_wall_context_setup/README.md)。
