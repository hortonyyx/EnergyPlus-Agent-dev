# DeepSeek Flash 两层平面与四立面对照

用户明确授权最新 `deepseek-flash` 在当前 harness 冷启两层平面和四立面，对照既有 6 Sol、Haiku、27B；不组装、不跑整案。27B 专项优化暂缓，主线仍为 6 Sol/high。

## 冻结配置与接入

- 官方 DeepSeek API，`deepseek-flash`，thinking enabled / high，服务默认采样，32,000 输出上限，1,048,576 上下文。本日官方目录名 DeepSeek-V4.1-Flash，官方更新记录为 1017；这是移动别名，不是不可变权重哈希。[目录证据](2026-10-17_deepseek_model_catalog.md)、[思考协议](https://api-docs.deepseek.com/guides/thinking_mode/)。
- 每节点 16 请求 / 60 工具 / 600 秒 / 0 重试，最多两个独立节点并发。原 sm25 六图、公共坐标约定和原读图任务；不向生成端提供 GT、历史答案或人工纠错。
- 补齐官方独立 provider：显式凭据文件、官方 HTTPS 域名、禁止重定向/环境回退，保留完整 reasoning_content，图片沿现有 user 消息通道传输。严格模型 profile 采用官方上下文和每图最多 1,024 token；文本预留为未校准估计，不冒充实测或账单。usage 的图像不重复计入；保留 DeepSeek 缓存命中计数，未登记费用不套用 Paratera 价格。
- 登记 runtime-v24 / domain-v101。领域版本变动仅为路由准入；登记结果 `changed_modes=[]`，提示词、工具目录、任务模板指纹未变。几何、读图交付和评分函数保持原版。旧 registry 记录逐项相等。
- 独立只读审阅 `review_deepseek_route`：无阻塞发现，未改文件、未读凭据、未调用真实模型。真实图片/工具服务闭环须由下面的实跑验证。

离线检查去重 170 项通过，另有 3 项既有 runtime 断言失败：StopIteration 被 Python 转为 RuntimeError，以及两个上下文耗尽旧状态名断言。隔离进程装入基线 HEAD 的原 `loop.py` 重跑这三项，同样失败；未为本次模型实验修改这些旧测试或扩大修复范围。一次 Windows 默认文本编码导致 AST 检查失败，显式 `-X utf8` 后该项通过。新接入首轮发现图像估算账本遗漏与 guard 位置问题，已修复并复验；登记后的 profile 封印检查通过。测试全部离线，无 provider 请求。

## 运行状态

准备运行；最终结果与证据将在本批次终止后补齐，当前不得推断质量。

证据目录：`D:/Sim-BIM-Agent/cache/deepseek-flash-reading-v101-20261017`；运行目录：`D:/Sim-BIM-Agent/runs/deepseek-flash-reading-v101-20261017`。首次从北立面启动，同配置完成其余五个节点。既有三模型只读引用，不重跑。
