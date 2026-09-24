# sm24 原平面冷启动 run37：未通过

只给一张原平面，无旧稿/标定、建筑JSON、立面或GT。冻结run36生产工具和指导，沿用run32冷启动scope与1800秒预算；GLM订阅`glm-5.3-flash`、medium，实际1051.95秒正常结束，CLI估算$1.693384（非账单）。过程中无开发追加提示或源模型代改。

[查看候选](candidate_01/viewer.html) · [实际源平面](candidate_01/plan_F1.png) · [原图回叠](image_overlays/overlay_002.png) · [独立摘要](evaluation/cold_start_audit.json) · [完整工作记录](../../worklog/2026-09-24_reconstruction_cold_context.md)

结果为9空间/11窗/10门/10连接。东北漏墙与原坐标翻转未重现，但走廊东墙被向下错误延长，把连续空间拆出`zoneA`，东外门及东南内门随之错归属。原始原图/GT及申报坐标诊断均severe；21开口可对应，20位置/19宿主/8门连接匹配。8个参照匹配并不等于通过：6minor、2severe，另多出1空间。

两次编译仅修了端点悬线；回叠后未改分区。18次原图查看、13次基础profile，未使用新双轴`view_pixel_profile`；不能归因为该工具已被采用。22张图像运输、源/显示重放、冻结输入和真实模型型号通过，原始流无损压缩。所有高度是假设，浏览器WebGL未另验。本候选不替换完整采用基点，也不证明重复稳定性。
