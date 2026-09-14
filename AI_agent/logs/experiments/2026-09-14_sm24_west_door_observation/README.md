# 西侧仅原图局部观察失败

Haiku只收到原图和“中央走廊西侧内墙”任务，无源候选、旧门数/位置或GT。它误选西外墙，持续量测外窗，120.71秒超时，没有最终费用回执和可用门清单，未应用。

[原图查看运输](execution_verification.json)与[派生图返回](trace_verification.json)通过；运输正确不代表目标正确。后续[带源墙投影定位的观察](../2026-09-14_sm24_west_door_projected_observation/README.md)另起，明确计入辅助信息，不冒称相同输入下能力提升。
