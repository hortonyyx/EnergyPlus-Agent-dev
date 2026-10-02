# 统一 Agent 底座核心接口（阶段 0）

本文固定阶段 1 起使用的底座核心数据契约。代码在 `src/harness_contracts/`，只描述模型请求、工具执行、角色、预算、恢复和上下文，不含建筑对象，也不导入现有建筑模块。建筑共用层可以引用这些通用 ID、资源和事件，核心层不反向引用建筑层。

当前实现是 Pydantic v2 的封闭字段、不可变模型：多余字段和非 JSON 的 NaN／Infinity 会被拒绝，但本阶段没有全面启用 Pydantic strict 类型转换；有多种形态的字段使用带 `kind` 或 `event_type` 的判别联合；单条记录无法判断的前后关系由 `EventLog` 统一检查。它们是记录格式和校验器，不是运行循环。

## 通用引用与“确实缺失”

`refs.py` 提供两种 blob 引用：

- `HashedBlobRef` 保存 URI、媒体类型和 64 位小写 SHA-256。新产生或实际发送的内容使用这一种。
- `HistoricalBlobHashMissing` 只用于旧记录，必须写明 URI、媒体类型和缺哈希原因。它没有虚构的空哈希。

`SourceRef` 再说明来源身份、类别和定位，可指向 blob 或已记录事件。它不强制建筑侧使用某种 `view_id`；建筑层可以把既有 view_id 放进 `source_id` 或 `locator`，并继续维护自己的坐标语义。`ImageTransmission` 同时保存原文件引用、实际发送内容的哈希及其在最终请求中的 JSON Pointer。这样图片缩放或转码后，原图与实际发给服务的字节不会混为一谈。

需要保存任意 JSON 时使用 `CapturedValue`：`inline` 是原值，`blob` 是完整内容的哈希引用，`missing` 是明确的缺失原因。`missing` 不等于空对象、零或执行失败。

旧运行只能映射成 `EventLog(mode="excerpt")`，并提供 `ExcerptDisclosure`：说明节选原因、没有保存的事件类别、已知但缺失的事件 ID 和真实来源记录。节选可以使用 `HistoricalTimestampMissing`、`HistoricalParentMissing`，也可以把最终请求、工具原始结果或模型所见结果分别标缺失。完整新日志拒绝这些历史缺口。这样 `agent_request.json` 一类启动入参不会被冒充为适配器最终请求，CLI stream 中的 `tool_result` 也不会被冒充为截断前的 MCP 原始返回。

## 事件边界

`events.py` 的 `EventEnvelope` 保存 schema 版本、事件/运行/任务 ID、父任务、严格递增序号、带时区时间和判别后的 payload。一个 `EventLog` 只代表一个 run。父任务有根任务、已知父任务和历史缺失三种状态；任务不能把自己列为父任务。

目前只设九类正式 payload，避免把每个小状态拆成独立类型：

| payload | 保存内容与主要约束 |
|---|---|
| `AdapterRequestPayload` | 适配器转换后的最终请求体、每段自动注入内容的来源、图片、参数审计和版本清单。内联请求会校验 JSON Pointer 确实存在，注入文字与最终片段相同。完整日志不能缺最终请求。 |
| `ModelResponsePayload` | 可见文字、工具调用及完整参数、原始响应、用量和思考证据。思考分为公开内容、摘要、服务报告 token 数、签名、无法获得五种；签名没有内容字段，“无法获得”不能与其他四种并列。 |
| `ToolExecutionPayload` | 完整参数、原始结果、实际给模型看的结果、可重复性、执行结果、操作键和已应用写入 ID。历史节选允许原始/所见一侧缺失；完整新日志的成功执行要求两侧都有。 |
| `StateInspectionPayload` | 为未知写恢复或断点恢复读取的持久状态、目标事件和检查结论。保存状态必须有 SHA-256。 |
| `RunLifecyclePayload` | 重试、取消、超时、恢复、失败及停止时已有的产物。重试、恢复和失败各自要求必要字段，恢复 checkpoint 必须与先前检查的状态完全相同。 |
| `BudgetEventPayload` | 预留或结算。事件顺序要求先预留后结算，任务必须一致。 |
| `ContextEventPayload` | 压缩、图片移出当前上下文、按原因取回。压缩只能引用更早事件，取回必须指向同一图片的移出事件。 |
| `ExternalCoordinatorMcpPayload` | 外层命令行协调者经 MCP 的派工、操作或返回。拿不到请求正文时保存 `MissingCapture`，不补造。 |
| `RunAggregateUsagePayload` | 单独保存运行回执里的汇总用量或明确缺失。它不替代各模型消息自己的 usage，也不把运行累计数重复填给每条消息。 |

采样和推理参数由 `ParameterAudit` 分开保存：`requested` 是客户端请求值，`provider_report` 是服务实际报告或明确未报告，`effect` 是有证据的已核实或写理由的未核实。服务未报告时不能标已核实。

`VersionManifest` 固定六层版本：代码提交、依赖锁、提示、工具定义、推理参数和模型路由。远端模型另存路由与别名；只有同时给出固定 revision 和证据才能写 `verified_fixed`，否则必须写 `unverified`。锁住本地六层不自动证明远端别名固定。

用量是 `UsageReported(raw_usage=...)` 或 `UsageMissing(reason=...)`。前者保留服务原始对象，后者没有伪造的零 token。当前核心只规范一次模型服务调用的用量/费用结算，不试图表达云账单中与这次调用无直接关系的赠送、折扣、税费或月度调整。

## 角色与模型绑定

`roles.py` 把纯角色定义与模型绑定拆开：

- `RoleDefinition` 保存职责、工具白名单、输入材料、返回要求和预算。只读角色的白名单出现写权限会直接校验失败。`authorize_tool_call` 在执行前同时检查工具名和读写权限。
- `ModelBinding` 保存默认模型、推荐模型和已有证据的验证范围。`validated_scopes=()` 明确表示尚无验证记录，不要求为未运行模型补造范围；一旦填写，范围只能指向已声明模型并必须带证据。失败策略目前唯一合法值是 `stop_and_report`；`initial_model_for` 只返回默认模型。推荐模型是选型资料，不是自动失败切换队列。

这里没有预设模型厂商或建筑角色名。协调、只读局部观察以及后续起草角色都用同一结构；证据包的建筑专属字段由建筑共用层定义。

## 预算与恢复

`budget.py` 将总上限、预留和结算分开。预留用途包括主任务、子任务、上下文摘要和重试，每笔至少有一个正数维度；总预算也至少有一个正数维度。全部预留之和不能超过 token、美元、秒数或调用次数的对应总上限，结算不能超过本笔预留。

服务报告用量时，`ReportedCost` 必须与 `actual.money_usd` 相同。服务没有报告用量时，token 实际值必须保持 `None`，费用只能写 `EstimatedCostUpperBound`，不能用零 token 或“实际费用”伪装估算。阶段 0 采用保守总账：已结算预留不会自动释放再分配，因此可证明不超总额，代价是可能少用预算；动态回收留到运行实现阶段。

`validation.py` 的跨事件检查实现最小恢复规则：

1. 写工具结果为 `unknown` 后，重试前必须先记录实际持久状态读取；检查必须指向原写事件并明确得出 `not_applied`。
2. 若检查发现 `already_applied` 或仍 `inconclusive`，重试会被拒绝。
3. 同一写操作的再次尝试必须显式引用合法 retry，retry 指向紧邻的上一尝试，并保持 `operation_key`、工具名和完整参数不变；只读调用不受这条写链约束。相同操作键不能出现两次成功应用，`applied_write_id` 也不能重复。
4. 已成功工具不能再标重试。模型请求可以重试，但仍需保留原请求和重试事件。
5. 从 checkpoint 恢复前必须检查保存状态，并得到 `safe_to_resume`；恢复引用必须与被检查的 checkpoint 哈希一致。

这些检查防止“连接断了所以再写一次”造成重复修改，但不执行实际状态读取，也不替工具定义幂等语义。阶段 1 的执行器要在调用前给工具正确分类，并产生这些事件。

## 与现有代码的关系

这套核心接口全部是新增，阶段 0 未改现有 `src/agent/execution/`、几何、修订或 `scripts/tool_scripts/`：

- 现有运行记录以后由阶段 1 适配进 `EventEnvelope`；本阶段没有替换现有 trace 文件。
- 现有模型路由以后转换成 `ModelRouteRef` 和 `VersionManifest.model_route`；本阶段没有改路由行为。
- 现有工具调用以后由执行器同时保存 raw 与 shown 结果；本阶段没有包装或调用工具。
- 建筑侧的 view、claim、inference、坐标和源模型版本继续由建筑共用层负责，通过通用 `SourceRef`、事件 ID 和任务 ID 接入。

## 已验证范围与限制

`tests/test_harness_core_contracts.py` 提供可直接借用的四个有效构造器：`make_valid_request_payload`、`make_valid_role`、`make_valid_ledger`、`make_valid_event_log`。正例覆盖最终请求、图片前后哈希、六层版本、四种可得思考及一种不可得思考、未知写恢复、断点恢复、只读角色和三类额外预算；反例覆盖注入位置不实、缺请求引用、夸大参数/远端版本、只读越权、自动换推荐模型、空预留、缺用量伪造零、费用不一致、未查状态重试、重复应用、错误 checkpoint 和错误上下文引用。

阶段 0 没有实现事件持久化、原子追加、运行循环、请求发送、工具执行、压缩算法、预算动态回收或 MCP 服务。`blob` 形式的最终请求由哈希保证身份，核心模型不会读取文件再验证内部 JSON Pointer；需要逐段位置校验的请求应以内联值校验，或由阶段 1 适配器在落 blob 前执行同一检查。历史节选的真实性仍取决于映射时引用正确的原记录，校验器只保证不会把已声明的缺失悄悄变成完整数据。
