# DeepSeek官方模型目录与视觉能力核验

用户明确目标为本地部署和快速交付，不绑定27B；27B专项优化暂缓。本次先查询DeepSeek当前模型及VLM能力，为后续Flash读图测试选型。没有启动读图、整案、推理探针或权重下载。

2026-10-17 19:00:27（UTC+8）使用既有显式DeepSeek凭据向官方`https://api.deepseek.com/models`发出一次GET，HTTP 200，耗时1.454秒。没有打印或保存密钥，没有provider回退。模型推理请求0次。

| API ID | 目录名称 / 官方当前API版本 | 实际目录输入模态 | 输出 | VLM |
|---|---|---|---|---|
| `deepseek-flash` | DeepSeek-V4.1-Flash / V4.1-Flash-1017 | text、image | text | 是 |
| `deepseek-v4-pro` | DeepSeek-V4-Pro / V4-Pro-0813 | text | text | 否 |

两者目录均返回context_window=1,048,576、max_output_tokens=393,216，思考档low/high/max，默认high。目录本身名称不含日期后缀；1017和0813来自当天官方Models & Pricing，不把目录名称当作完整版本锁。

- [官方型号表](https://api-docs.deepseek.com/quick_start/pricing/)明确Flash支持视觉、Pro不支持。旧`deepseek-v4-flash`和`deepseek-v4-flash-vision-exp`为兼容别名，官方说明其请求路由到最新Flash；本次未对旧别名发起推理验证。
- [官方更新日志](https://api-docs.deepseek.com/updates/)记载2026-10-17更新为V4.1-Flash-1017，API调用名仍为`deepseek-flash`。官方列出视觉相关基准提升，但本项目图纸、三维理解和工具闭环尚未实测。
- [视觉接口文档](https://api-docs.deepseek.com/guides/vision/)支持图片与文本共同输入。视觉处理的分辨率、坐标保持及工具返回图片仍须在本项目接入时核对，目录成功不代表读图质量通过。
- 本地部署目标与远端API实测分别判断。官方V4.1模型介绍披露552B主干、输入/输出分别激活8B/16B；激活规模不能直接用作权重内存需求。本轮未核对1017 API与下载权重是否同步，也未评估本地设备能否达到目标速度。

原始证据：[models.json](D:/Sim-BIM-Agent/cache/deepseek-model-catalog-20261017/models.json)、[query.json](D:/Sim-BIM-Agent/cache/deepseek-model-catalog-20261017/query.json)。目录保存文件SHA256为`6386079b69f68b84de0feb0929e27c4d2f69738d9a97f5d354d717eb578e90d2`。官方模型卡：[DeepSeek-V4.1-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash)。

后续读图候选选`deepseek-flash`；本轮只完成目录和文档核验。无产品代码、配置、runtime/domain或桌面变更，未宣称harness已适配或完成真实图片调用。
