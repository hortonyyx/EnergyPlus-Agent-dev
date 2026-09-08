---
name: comate-gateway-relay-channel
description: 2026-07-27 用户拍板——公司 Comate 内网网关走「路线 3 人工中继」只做非代码活；含 Fable 5 可回补最高档审阅位
metadata: 
  node_type: memory
  type: project
  originSessionId: d35be1c2-4f94-44e3-8b3a-684b58b6a0f0
  modified: 2026-07-27T09:24:30.238Z
---

**2026-07-27 用户拍板**：公司 Comate 有近乎全量头部模型权限（**含 Fable 5** ⇒ 2026-07-21 [[opus-controller-fable-spot]] 记的最高档审阅位空缺**有回补可能**），但**只走「路线 3·人工中继」**：主控出**脱敏 prompt**（不含项目源码与文件树）→ 用户在 Comate 侧跑 → 结果贴回。**不接为 worker 席位**，施工仍走 Claude/GPT/GLM 现有席位。

**为什么不接为席位（主控只读诊断）**：
1. **网络是第一道坎**：`oneapi-comate.baidu-int.com` 是**百度内网域名**，dev container **连不上**（TLS 0.04s 断；同环境 GitHub 200、智谱 401 正常 ⇒ 出网无碍）。卡点是拓扑不是协议。
2. **协议未证**：网关 = OneAPI 风格（`X-Oneapi-Request-Id` + APISIX），四路由（`/v1/models`·`/chat/completions`·`/messages`·`/responses`）无 token 时均返回统一鉴权错 ⇒ **路由存在 ≠ 协议实现**。worker 的命脉是 `/v1/messages` 的**多轮 tool_use/tool_result 往返**，这一条没验过。
3. **数据流向**：多厂商网关**必须解密**才能路由 + 计费 ⇒ **公司网关是链路的一端、不是管道**，明文提示词对其可见且绑工号；**agent 用法会把整个代码库增量上传**。公司政策鼓励用模型（合规无碍），但**课题组数据不出组**是另一层约束 ⇒ 未确认留存政策前不走施工。待确认三项：请求体是否落盘 / 留存期与查看权 / 是否二次用途。

**⚠️ 诊断纪律（吃过一次亏）**：本 dev container 沙箱把**任何**域名（包括随手瞎编的）解析到递增假地址 `fdfe:dcba:9876::N` 且 TCP **都"连得上"** ⇒ **DNS 解析与 `/dev/tcp` 连通性测试在此环境下全是假阳性**。判可达只能用**不带凭证的真实 HTTP 请求**（看是否回目标服务自己的错误 JSON）。主控首测即中此陷阱，靠"拿两个不存在的域名做对照"自查发现——**测网络前先证明尺子是准的**。

**升级为真席位的顺序**：先网络 → 再协议（多轮工具调用）→ 再合规留存政策。关联 [[codex-execution-protocol]]、[[glm-family-onboarding]]。
