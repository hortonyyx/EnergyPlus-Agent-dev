# 首轮空间识别：协调指引与按需参数参考

仅原图整案sm24/run15，沿用run13/14五原图、通用目标、Sonnet订阅medium、600秒。无seed、历史观察、正确数量、坐标、GT或中途开发反馈。改动仅为开场工作指引收拢与参数文档按需读取，几何/量测/查看与评价算法不变；这是一份方法探索，不是统计消融或降本证明。

`run_cold.py`冻结并保存工具代码（含新增guidance文件）、输入与范围。运行结束采用本目录`verify_execution.py`（前一程脚本增加只读参考工具的合法名称）和`verify_references.py`，复用`2026-09-14_cold_reconstruction_setup/`中的`summarize_run.py`、`audit_source.py`；独立评测沿用`2026-09-12_sm24_delegation_setup/evaluate.py`。后者仅生成完成后读取GT。

完成依据：参考文档实际可读、示例通过真实建模接口、旧工具回归通过；新整案核第一次保存耗时、实际观察/量测/子调用、保存后空间修订和原图保真。失败如实保留，不因检查通过或工具使用增多改变采用基点。


结果：run15已完成且保真失败。`observe_spaces.py`随后另起原平面/空间解释/编号区域方法探针，Sonnet low/180秒，90.6秒完成但仍错把完整隔墙当家具。它不是整案或同范围成本消融。两次结果见[本轮记录](../../worklog/2026-09-14_reconstruction_focused_guidance.md)。

run15冻结后补回按需开口文档的整层complete范围与复核语义、墙尺寸残差解释，GUIDE未改。`reference_preservation.json`记录的是run15冻结前的四段参数逐字保留；它不冒充后补文档的字节相同。全接口22项通过；后补文档单项检查1项通过（与22项重叠）。

查看器复现需复用既有环境：`PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-10_autonomous_recovery_setup/browser_check.py RUN --out NEW_OUTPUT`。默认`/opt/venv`无Playwright；本次没有安装依赖或浏览器。
