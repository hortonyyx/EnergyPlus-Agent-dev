# sm21 六原图整栋独立生成 run57

[查看交付](delivery.html) · [直接模型](candidate_04/viewer.html) · [完整设置与限制](../2026-09-26_sm21_whole_building_setup/README.md)

最终candidate_04，两层14空间/15窗/14门。原图29门窗位置和宿主、14门连接对应；严格2cm GT分区minor，17外开口位置/宽/高容差内。12内门高度仍假设。单Sonnet5/medium调用377.66秒，CLI估算$1.232221，非账单。

`postrun_audit.json`为源/显示、输入hash、装配与GT检查；`evaluation/original_openings.json`独立原图位置/宿主/连接；`evaluation/gt/`保留GT原评价和旧格式外开口诊断；`evaluation/semantic_review.json`记录手工核看与限制，`evaluation/tool_transport.json`记录实际调用。查看器检查见`browser_qa/report.json`。

仅一次sm21冷启动，尚待独立重复。重复备注未清理；模型未做专门源立面/全墙路径和全开口自检。生成后开发评价不构成用户验收，未运行EP。
