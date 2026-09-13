# 完整轮廓、连通区域与局部源应用实验入口

运行模型仅使用已登录Claude订阅，Sonnet级上限；不含DeepSeek/API/EP。所有实验另建run，失败观察留存，GT仅在应用结束后评价。

- `run_trace.py`：原图局部观察；可选模型自身旧trace、连通区域工具与开发参考面反馈。完整真实问题以每个run的question/request为准，脚本修订不会追改旧输入。
- `verify_trace.py RUN`：核对原图/问题/receipt摘要、区域和轮廓确定性重放、实际工具返回图与selection摘要；不判断图意。
- `apply_trace.py --observation RUN --out NEW --boundary-snap-m 0.15`：开发选两个源空间，以模型选定的完整轮廓作局部应用。整条边仅与旧两空间并集外缘匹配，共享坐标一致映射；拒绝歧义或最终点位移超限。默认0.05m，显式上限0.2m，本轮0.15m是开发侧选择；不裁切、不吸旧内部隔断。门洞用相同映射，保留已有门窗身份并显式移门/换宿主。
- `apply_trace.py --self-check`：纯合成正交边/门端点/不吸内隔断检查，不调用模型。

生产工具代码提交08392188。模型观测时的源码副本在各观察run/implementation，源应用时另存三份应用代码。含旧trace的两轮历史only_input模板描述不准，README单独说明真实条件，不改写其实际输入。

run07为开发编排的局部观察回放，非自主整案冷启动。源导出器仍保留通用`generator: Claude subscription tool loop`标签，真实执行模式以`developer_orchestrated_local_trace_replay`、应用代码/operations及0次模型调用为准；delivery页面已明确标识确定性应用。
