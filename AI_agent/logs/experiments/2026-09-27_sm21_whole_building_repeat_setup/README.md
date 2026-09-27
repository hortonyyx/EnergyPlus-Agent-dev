# sm21 冻结方法独立重复

[run58 查看入口](../2026-09-27_sm21_whole_building_repeat_claude_run58/delivery.html)，最终 candidate_04。用户要求本轮继续由Astra独立推进还原；无开发子代理或产品委派。

与 run57 保持六原图、逐字任务、系统指引、33 项生产实现 hash、Claude 订阅 Sonnet/medium 和 3000 秒预算一致。新建独立 run，生成只接原PNG及通用任务/工具，不接旧稿、旧标定、GT、开发参照或结果数量。`repeat_preflight.json` 与 `comparison.json` 保存核对结果；模型运行中无人干预。

## 结果与范围

实际 `claude-sonnet-5`，310.58 秒正常结束，1 主调用、无子调用/回退。CLI估算 $1.6289102，为订阅回执估算而非账单，不含开发用量。

- 两层 14 空间、15 窗、14 门/14连接。原图 29 门窗位置及宿主、14 门连接全部对应，未配对项为零；两层连续走廊与分别判读的房间分隔保留。
- 未改容差的严格 2cm GT分区 `minor`，14/14 空间匹配，无错拆错并/漏房和拓扑发现；最大边界差约 1.21cm，最小 IoU 0.99461。该数值是与参照比较的残差，不是观测精度声明。楼层底高/层高对应为 0/3m、3/3.6m。
- 17 外门窗位置、宽度、高度均在原诊断容差内。旧格式 GT 不提供宿主字段；宿主结论仍来自独立原图核验。
- 4 条已确认且数值保持的图像观察覆盖 15 窗。两外门高度虽与 GT 对应，模型只给出像素观察并主动暂缓采纳，交付明确保留未确认；12 内门高度仍假设为层上 2.1m。不能把17参数匹配写成17高度均由模型确认。
- 实际更新了源假设备注，candidate_03→04 的楼层、空间、边界、全部门窗及连接记录严格保持。编译器通用说明和标定未独立验证说明各重复两遍；没有人工改写结果。“厚度为编译器默认值”的备注不能视为已采集有效墙板厚度。
- 模型实际看六原图、检查八对空间关系并看南源立面；未做完整墙路径、逐门窗平面回查或其余三个源立面自检。事后开发核验范围更广，不冒充模型自主验收。
- 原图/实现hash、逐层装配、源/显示精确重放通过；31 张实际工具图片均能解码，真实finish回执9113字符直接JSON，零工具错误。工具日志中的装配内部事件与CLI实际调用分别计数。
- 离线浏览器源hash、双层切换不同画面、旋转、交付说明通过，无页面错误或外网请求。原始流经无损校验后gzip归档。无EP或用户验收。

本程生产代码未变，不重复既有有效pytest。`verification.json`核真实备注更新、全几何记录保持和4确认/2暂缓；诊断仍复用run57旧格式GT与原图参照，没有按本次结果调整答案或阈值。

## 复现

生成不能覆盖旧run，重做先另设独立输出。审计须保持冻结生产实现：

```bash
python -m AI_agent.logs.experiments.2026-09-27_sm21_whole_building_repeat_setup.run_repeat
python -m AI_agent.logs.experiments.2026-09-27_sm21_whole_building_repeat_setup.audit_repeat
python -m AI_agent.logs.experiments.2026-09-27_sm21_whole_building_repeat_setup.verify_evidence
PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python AI_agent/logs/experiments/2026-09-26_sm25_height_review_setup/browser_check.py AI_agent/logs/experiments/2026-09-27_sm21_whole_building_repeat_claude_run58
```

与run57的两次结果支持当前sm21范围内的重复性，不据此宣称普遍稳定。其他两例的最新范围及下一步见[本轮交接](../../worklog/2026-09-27_reconstruction_repeat_and_inventory.md)。
