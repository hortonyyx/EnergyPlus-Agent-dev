# 原图墙网编译：实现与验证入口

新 `build_plan_bim` 已接通；真实限时平面实验没有产出候选，不能作为还原成功。完整结论见[工作记录](../../worklog/2026-09-14_reconstruction_plan_partition.md)。

- [运行脚本](run_plan.py)：仅原平面＋原声明、300秒 Sonnet medium，无旧观察/候选/正确墙位或GT；开发指定局部任务和新入口。
- [冻结输入和代码](frozen_inputs.json)、[40项不同离线测试](code_checks.json)。测试分组有重叠，不直接求和。
- [原运行与失败](../2026-09-14_bim_agent_sm24_run17/README.md)：300.55秒超时，原声明/失败原样保留。
- [实际图像运输](verify_execution.py)、[声明/编译重放](verify_compilation.py)：后验脚本，不进入生成模型。
- [事后墙网诊断](diagnose_partition.py)：保留第二份原墙网，明确排除并单存全部17个开口，只定位空间划分错误，不产生可采用还原候选。

图像审核扩展自前一轮 guidance setup；声明运输复用 input setup 的 `verify_declared_run.py`，其无候选出处项目为 false，不能因此声称源出处已验证。事后源重放、独立分区、浏览器检查均复用已有脚本；这些不改写 run17 无候选的结果。

没有低档产品委派或第二次生成调用。Sonnet 请求实际回执为 claude-sonnet-5，总费用因超时缺失；开发 5.6 Sol 子代理不混入产品运行用量。原图流无损 gzip 保存。
