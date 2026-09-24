# sm24 全路径方法独立重复设置

run40逐字复用run39的生成scope、同一原平面及生产实现，运行前校验全部冻结哈希。新GLM订阅调用、medium、1800秒；没有旧墙网/坐标/答案或运行中干预。内门无高度信息不作为验收阻塞，保留假设说明与原始诊断；此约定没有改动生成提示。

```bash
python -m AI_agent.logs.experiments.2026-09-24_sm24_repeat_support_setup.run_repeat
python -m AI_agent.logs.experiments.2026-09-24_sm24_repeat_support_setup.audit_cold --run AI_agent/logs/experiments/2026-09-24_sm24_repeat_support_glm_run40
python -m AI_agent.logs.experiments.2026-09-24_sm24_repeat_support_setup.summarize_trajectory
python -m AI_agent.logs.experiments.2026-09-24_sm24_repeat_support_setup.compare_repeats
```

已有run目录拒绝覆盖；生成结束后才运行独立原图/GT评价，不改变原始候选或调整容差。评价脚本复用run39方法。两次保留全部结果，重复样本仍少，不能推广为任意建筑稳定通过。结果见[工作记录](../../worklog/2026-09-24_reconstruction_repeat_support.md)。

运行与核验已结束：两次均8空间一一对应、21/21宿主、10/10门连接；严格数值偏差仍有波动。保留[双次比较](repeat_comparison.json)和[run40产物](../2026-09-24_sm24_repeat_support_glm_run40/README.md)，下一项换sm25楼层。
