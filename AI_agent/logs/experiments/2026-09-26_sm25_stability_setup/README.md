# sm25 整栋原图独立重复与内门抽查

按用户“先稳定做好，再降低依赖、加快速度、节省成本”继续。`run_repeat.py`复用run53逐字相同scope、六原PNG，不给旧模型/标定/观察/评价/正确数量或高度。生产源码本轮未改；相对run53只有上一程已提交的最终摘要压缩差异，不称所有实现完全一致。

新[run54交付](../2026-09-26_sm25_height_repeat_claude_run54/delivery.html)：实际Sonnet5/medium，527.89秒、1次现有Claude订阅主调用、无子模型或回退，CLI估算$1.8147054，非实际账单。Astra独立开发、验收；无Opus或部分推理任务。

29空间/31窗/30门，源与显示、草稿编译及整栋装配精确重放。独立GT29/29空间对应，无漏房/错拆错并身份信号；34/34外开口位置、宽度、高度、宿主均匹配现有judge容差。严格2cm分区仍severe，最大边界差约16.6cm、最小IoU约0.909；27内门高度仍为2.1m假设。

`audit_internal_doors.py`从原图选两层各三扇，包含不同朝向及单双扇门，用近似墙代表线/门框端点和两侧空间内部点核对位置、宽度与源连接。参考与裁图在`internal_door_reference`，未向生成传递。run53与run54均6/6通过（6px端点/宽度容差），最大端点差分别4.24/3.16px。仅六扇，不证明27内门全量/完整性、门高或开闭状态；重投影采用各自生成标定，不是独立米制标定精度测试。原run53没有改写，新增抽查报告存此setup。

本次真正收到`finish_bim`压缩回执：8,822字符、可解析JSON、无转存提示，未核27内门高度仍明确保留。实际流有5次claim对象ID不存在的报错，模型自行纠正后6条高度claim确认34外开口；失败没有覆盖或伪装成首次成功。模型直接看过六图，仅抽查首层4对空间关系，未调用完整墙路径或源立面专用查看工具，不称全范围视觉复核。

源assumptions仍有两条早期“高度待立面核实”的旧备注，与已确认的外开口高度状态不一致；原文保留为待修说明问题，不能将几何对应称为全部说明也已正确。

## 命令与证据

```bash
python -m AI_agent.logs.experiments.2026-09-26_sm25_stability_setup.run_repeat
python -m AI_agent.logs.experiments.2026-09-26_sm25_stability_setup.audit_repeat
python -m AI_agent.logs.experiments.2026-09-26_sm25_stability_setup.audit_internal_doors AI_agent/logs/experiments/2026-09-26_sm25_height_repeat_claude_run54
python -m AI_agent.logs.experiments.2026-09-26_sm25_stability_setup.audit_transport
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-26_sm25_height_review_setup/browser_check.py AI_agent/logs/experiments/2026-09-26_sm25_height_repeat_claude_run54
```

生成只运行一次，后四项为结束后的独立评价。原图/实现hash、源/显示/装配重放、18张实际图像运输和离线浏览器hash/切层/旋转/无外部请求均通过。无新生产代码，因此沿用上一程相同代码的相关离线测试，不重复全量或宣称新增单测。

`evaluation/repeat_transport.json`按原始CLI流统计真实工具调用，`tools.jsonl`会对一次调用记录多个事件，两者不可混用计数。流已无损压缩为`.jsonl.gz`。

这是run53之后一次同图独立重复，支持本例主要分区及外开口高度的重复性，未证明跨图纸普遍稳定。下一项冻结当前生产方法做整栋换例，优先sm24六原图，不回喂本次Haiku局部答案；内门扩大核验按结果继续，毫米/厘米精修和降本后置。
