# sm24 局部边界量测探针

Haiku在61.03秒完成6次原图查看、6次新像素量测；量测和图像运输核验通过，但观察仍错，不能作为正确几何答案。

[独立原图复核](evaluation/visual_review.md) · [完整回答](response.json) · [实际工具轨迹](detail_01/tools.jsonl) · [量测回查](measurement_verification.json) · [输入与视图核验](execution_verification.json)

开发助手只选择“东南空间与交通区相接的边界及开口”问题，没有给裁区、坐标、房间数、旧模型、旧观察或GT；Haiku自行选图/裁区/RGB/阈值。150秒上限，实际模型`claude-haiku-4-5-20251001`，输出5797 token，CLI估算$0.0776693，属于既有订阅、非账单。

6次量测中两次无候选。工具返回的原图摘要、未改动裁图、候选峰值上的实际像素支持区间、保存与返回的图像/元数据均核验一致。Haiku仍将办公家具/窗等线条纳入墙和门的解释，未恢复真实边界转折；有调用量具不代表读图正确。原始回答按原文送下一次恢复作为可质疑线索，未经开发助手修正；这不计冷启动或低档reading成功。

实现快照在`implementation/`；[可复跑入口](../2026-09-13_pixel_support_setup/run_probe.py)默认拒绝覆盖已有run。原图语义独立复核留在`evaluation/`，不送生成。
