# 运行失败诊断（2026-10-12）

本轮用户要求“先做一次诊断，看看为啥现在跑不通”。范围为源码与原始日志审计、当前安装/代理检查、零推理 HTTPS 读取和本机传输复现；没有修改 runtime/domain、启动新建模或更新桌面。

## 结论

当前直接阻点是 ChatGPT 订阅请求的传输断连，另有已明确返回的服务过载。最新证据没有复现旧的大回执上下文停止及缺 usage 结算错误，但真实平面正式提交、整楼装配和自主交付仍未跑通。不能把离线通过解释成真实端到端通过。

现有日志不足以把传输断连归到客户端、代理或上游中的某一层。尤其 `awaiting_response_headers` 并不证明请求已经抵达 OpenAI：源码在获取 token 前就设定该标签，覆盖代理 CONNECT、TLS、上传和响应头等阶段。本轮纯本机实验确认，仅代理 CONNECT 后关闭就会产生与真实失败相同的诊断字段。

## 现场状态与检查结果

| 范围 | 版本/结果 | 耗时、调用与边界 |
|---|---|---|
| Git 与登记 | 开工 `e48b315b`，main 与远端一致，工作区干净；registry verify 通过 | 只读，无模型调用 |
| 开发入口 doctor | ready；runtime v11 / domain v68；Python 3.12.10 | 零模型；只证明文件、资源及必要依赖可加载 |
| 桌面入口 doctor | ready；runtime v7 / domain v65；发布 `d2b1c059` | 两个 doctor 命令合计约 4.95 秒；桌面尚不含最近开发修复 |
| 现有代理 | 10809 正在监听；运行时 rule、TUN、strict-route；OpenAI 规则走代理 | 只读控制面和配置；未关闭、切换或修改代理 |
| 无认证 HTTPS GET /v1/models | 2/2 返回预期 401，均经过 CONNECT、TLS、HTTP 收头 | 1.825 / 3.784 秒；401 来自故意不携带身份的探测，不是账号认证失败 |
| 订阅目录读取 | 首次失败（SubscriptionAuthError，7.834 秒，缺细因）；随后带安全 trace 的读取 HTTP 200、7 个模型 | 后一次 4.258 秒；本地 signed_in=true。目录成功不证明 Responses 推理稳定 |
| 本机连接复用实验 | 同一 adapter 发送 2 次 SSE 请求，实际建立 2 条 TCP | 留档执行 0.519 秒；不能以共用 AsyncClient 直接认定复用了失效连接 |
| 本机代理 EOF 实验 | 只在 CONNECT 阶段断开，即复现同类 RemoteProtocolError、粗阶段标签和缺 status | 留档执行 0.430 秒；没有上游连接或 TLS |

两项本机 case 各执行两次（首次 inline、再次留档），共 4 次 case 执行、6 次本机 adapter send。外网只执行两次无认证 GET 和两次目录读取操作；首次目录内部 HTTP 数量/失败细因未记录，不补造。本轮真实模型推理 **0**、DeepSeek **0**、新增整案 **0**；没有 GT 读取或质量评价。

## 原始失败记录独立重算

| 原运行 | 完整响应 | 失败 | 耗时与终态 |
|---|---:|---|---|
| sm25 recovery，v10/v67 | 37/66 | 26 传输断连 + 3 明确服务过载 | 全程 1283.899 秒；23 次有界重试；四立面已提交，平面 0 正式提交，根整楼交付为空 |
| 单并发 probe，v11/v68 | 1/2 | 第二请求传输断开 | 全程 52.969 秒；失败请求 26.203 秒，配置 timeout 300 秒；未重试，后续并发档和 sm25 接续未启动 |

26 次传输失败耗时 13.766–24.937 秒，中位 15.4535 秒；13 次请求有工具输出、13 次没有。首条协调员请求在没有图片、没有工具续接时就失败，且另有一次无图协调员请求失败。因此故障既不是图片续接专属，也不要求高并发；时间聚集不能据此归到某个超时组件。

三次服务错误明确包含 `server_is_overloaded` 和 `NO_MORE_RETRY`，应与未分类传输失败分开。F2 第五次试建成功后，仍完成四次报告读取和一次看图，随后才遇服务过载；该样本未再发生旧的大回执上下文阻断。66/66 与 2/2 请求均各结算一次、无在途；29+1 次未知 usage 保持未知。

probe 的 `model_budget_exhausted` 是两请求保护上限耗尽后的终态标签，直接失败因素仍是第二请求断连。原运行 journal SHA 与冻结记录一致，正式 continuation run 和 claim 均不存在。

## 初次诊断提出的可选项（后续指令已收窄）

以下是诊断时的建议，并未实施。用户随后明确最近代理连接质量不稳定，要求优先保证 harness 自身可靠，外部原因不应引发过度设计。按下文最新取舍执行，不将下面的 trace、终态呈现改动或 4 请求 probe 列为默认必做前置。

1. **先补传输证据。** 在 Responses 请求记录连接新建/复用、代理 CONNECT、TLS、上传完成、API 响应头、SSE 首帧及阶段耗时。只保留允许的事件名、计数/状态和安全错误分类，不记录 token、完整 headers 或未经清洗的异常文本。当前 `src/agent_runtime/responses.py:443` 的粗阶段标签会误导故障定位。
2. **补终态因果呈现。** 同时呈现运行停止原因与最后一个模型失败原因，避免 probe 被表面上的“预算耗尽”掩盖实际断连；这是诊断建议，本轮未实施。
3. **最小真实链路鉴别后再接续。** 建议先用原 Sol/high、单并发、保留原代理做最多 4 个请求（两组首请求→看图工具续接），无自动重试或回退，首次传输失败即停；精确 trace 区分实际失败阶段。通过仅表示小样本可用，不能证明长期稳定，随后再按独立范围验证原剩余额度接续。该建议未执行，不沿用旧批次授权。
4. **端到端通过后再同步桌面。** 当前桌面版本滞后是额外部署边界，不是已证明的开发版断连根因。

第二条 probe wire 为 1,204,774 bytes，首条 602,640 bytes：原图历史与工具回图各保留一次，导致体积翻倍；结构合法，仅作为后续载荷对照变量，不能认定为大小限制。当前 adapter 在收到终态 SSE 后立即 return，本机 HTTP/1.1 样本因此没有复用连接；直接加 `Connection: close` 缺乏当前证据支持。

OpenAI 官方将流开始前的接入错误、结构化服务错误与连接失败分开，要求保留实际状态、错误码和 request ID。参见 [Errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)；本轮不能凭缺失状态码断言上游责任。

## 证据与后续入口

- 原 recovery：`D:/Sim-BIM-Agent/runs/sm25-gpt-harness-recovery-20261012-high/events.jsonl`。首请求失败第 6 行；服务错误第 446、560、570 行；F2 成功试建第 499 行。
- 原 probe：`D:/Sim-BIM-Agent/cache/harness-continuation-20261012/probe/live-1/stage1_F1/events.jsonl`，失败第 16 行。
- 本轮留档：`D:/Sim-BIM-Agent/cache/diagnosis-20261012/` 内 `recompute_events.py`、`recovery-event-recompute.json`、`probe-event-recompute.json`、`check_connectivity.py`、`current-connectivity.json`、`check_catalog_trace.py`、`catalog-trace.json`、`loopback_transport_cases.py`、`loopback-transport-results.json`。原始大日志与本机诊断缓存未复制入 Git。
- 代理只读核验：当前 `clash-verge.yaml` 的规则与运行时控制接口一致；规则集 `proxy.yaml:18228` 含 `+.openai.com`。14:58/16:44 更新日志称配置字节相同；可读日志缺失败请求细节，服务日志目录当前不可读，未绕过权限。
- 上轮实现、版本冻结、接续方案及历史独立验收保留在 [harness 终态接续交接](2026-10-12_harness_continuation/README.md)。本轮没有重跑其 382 项离线全集。

收口时 C 盘余 51.17 GiB、D 盘余 158.28 GiB。本轮仅新增诊断记录与缓存脚本，未改变模型配置、账号、代理或桌面安装。

## 用户后续明确的工程取舍：先确认 harness，不为外部波动扩建设计

用户补充近期代理连接质量不稳定。它是新的现场线索，尚不构成对历史每次失败的归因。本轮只做已有验证的覆盖审查，停止将细粒度网络 trace、更多重试或恢复机制当作默认开发任务。

已重新核对 `validation.json` 引用的 9 份结果 XML：文件全部存在，SHA-256 全部吻合；382 个去重通过项是分批定向检查的既有结果，本次没有重跑。`independent_review.json` 列出的源码及测试文件哈希全部一致，已审范围没有未关闭的 P1/P2。受检运行代码仍为 runtime v11/domain v68。

| harness 责任 | 现有证据 | 判断边界 |
|---|---|---|
| 请求、工具和图像往返 | `test_runtime_responses_integration.py` 覆盖 Responses 工具/图片循环、只执行完整响应、未知 usage 结算与受限重试 | 服务响应使用模拟传输，不能证明外网稳定 |
| 试建反馈、返工与正式提交 | `test_role_trial_feedback.py` 的大成功回执→继续循环→显式提交；`test_role_rework_handoff.py` 的通过未提交稿→读取→重试建→显式提交 | 证明契约和状态流，不能证明 work model 必然作出正确判断 |
| 输入、派工、整楼装配与交付 | `test_role_continuation_entry.py` 与 `role_d1_fixtures.py` 运行真实 frozen-MCP 工具、六 reader 交付、故障终止、新运行接续、`finish_bim` 及 BIM/查看器文件断言 | 模型响应为脚本，证明工程链路能执行；不是独立真实建模通过 |
| 外部失败时保全状态 | 现有有界重试、retry hint 否决、终态报告、预算/usage保全与明确新运行接续均有覆盖；最近真实 journal 结算合法 | 不要求 harness 在持续断网或服务明确拒绝时强行完成 |

当前工程结论：**已知内部阻断已修复并有对应验证，现有审计没有发现需要立即追加实现的 harness 阻断。** 这不等于绝对无缺陷；真实模型自主完成整楼仍保留为验收边界。后续优先在连接可用时复用现有运行能力验证；只有发现可复现的内部错误，才做相应最小修复。简单失败记录、状态保存和既有有界重试保留，不因代理抖动扩建网络系统。

查看器覆盖也保持准确边界：上述集成测试检查 HTML 生成、存在与大小，本次未重新打开浏览器验收交互；不能将文件断言表述为浏览器视觉验收通过。

本次补充为只读证据与源码审查，新增自动化测试 0、模型请求 0、网络探测 0、运行代码改动 0；没有修改代理。
