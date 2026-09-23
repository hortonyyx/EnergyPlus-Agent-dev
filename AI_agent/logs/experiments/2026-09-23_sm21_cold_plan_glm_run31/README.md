# sm21 首层原图冷启动结果

GLM仅接收一张首层原图，无旧候选/旧观察/建筑声明/GT。实际`glm-5.3-flash`正常结束，827.95秒，1次调用，CLI估算$1.0895616（非账单）。

交付：[范围说明](delivery.html)、[可旋转模型](candidate_01/viewer.html)、[独立原图回叠](evaluation/independent_original_overlay.png)。最终7空间、7窗、8门、8连接，无未建对象。层高与全部门窗高度都是假设。

独立原图对照：15/15门窗平面位置/宿主、8/8门连接符合预设容差；沿洞口方向最大端点误差4.32cm，外皮表示与门窗图符中线另有约11.9cm垂直墙线方向差异。首层GT空间7/7匹配，无错分/错并；**原始分区仍severe**，四段竖隔墙偏2.88–3.06cm超过原有2cm阈值，未放宽或改GT。详见[evaluation](evaluation/partition.html)、[逐开口核对](evaluation/original_openings.json)。

源/显示精确重放、运行代码哈希、原图隔离通过；26张PNG实际返回模型，包含与保存产物缩放后逐像素一致的源平面和回叠。查看器内联但本次未做浏览器交互测试。原始会话流以`agent_stream.jsonl.gz`无损保存，原字节SHA与压缩核验见`stream_archive.json`。

这是一份有界冷启动有效首稿，不是整栋/高度验收、重复稳定性证明或修改纠错实验。保持已有全楼候选不被单层覆盖。输入方法、辅助边界、费用和下一步见[完整工作记录](../../worklog/2026-09-23_reconstruction_cold_plan.md)及[可复现设置](../2026-09-23_sm21_cold_plan_setup/README.md)。
