# sm24 自行选择错处的旧稿复核

[查看模型](candidate_02/viewer.html) · [原图回叠](image_overlays/overlay_002.png) · [独立分区对照](evaluation/declared_frame_partition.html) · [与指定区域复核对照](evaluation/review_comparison.json)

取消上一轮开发指定位置，GLM从同一原平面及run32失败墙网自行选择复核对象，恢复东北分隔、南部折角/门归属及顶部内门。未提供run35成功产物、run34局部回答、正确数量/坐标或GT；没有中途开发提示。

实际现有订阅`glm-5.3-flash`/medium，936.22秒正常结束，CLI估算$1.625188（非账单），无子模型或回退。最终candidate_02为8空间/11窗/10门/10连接，19个旧开口三维顶点及类型保持；原标定、外轮廓和高度假设保持。

按原申报锚点严格反解后，原图空间8/8、minor，21/21宿主、10/10门连接、20/21开口位置匹配。原始原图/GT评分仍severe，保留的坐标翻转、未核高度和DA门约8.25cm端点差没有改写。源/显示精确重放、31张实际图像与两处局部回叠核验通过；无浏览器WebGL交互验收。

这是一次少提示旧稿恢复成功，不是原图冷启动或稳定性证明。生产工具/指导与run35冻结一致，预算由1500增至1800秒，不作单变量因果或耗时优化结论。

`draft_001`重建旧稿；`draft_002`含重复墙被拒绝；`draft_003`生成最终candidate_02。恢复最终模型可用candidate_02，墙网继续入口为draft_003。运行/核验脚本见[设置](../2026-09-23_sm24_self_review_setup/README.md)，完整交接见[节点记录](../../worklog/2026-09-23_reconstruction_self_review.md)。
