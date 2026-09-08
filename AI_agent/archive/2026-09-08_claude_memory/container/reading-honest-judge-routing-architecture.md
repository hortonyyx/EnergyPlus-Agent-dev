---
name: reading-honest-judge-routing-architecture
description: reading↔correction 接缝架构定调(2026-06-21 用户ratify):correction永image-blind纯文本不做VLM/脚手架=降智机制/看图仲裁归judge+重读/judge两轴severity×recoverability/根因=founding框架reading半边没落地
metadata: 
  node_type: memory
  type: project
  originSessionId: 77c1f46e-6330-4c7b-bbcf-1e41b1f4ac67
---

2026-06-21 用户全程 ratify 的架构决策(修 sm21 Sonnet 识图的总纲)。方案 doc =
`AI_agent/logs/review/request/2026-06-21_reading_honest_and_judge_routing_proposal.md`(待 Codex 双审→派执行)。

**D1 correction 永远 image-blind 纯文本,不做 VLM。** 开图给 correction = 翻倍 VLM 要求、违背北极星(国产VLM API→本地开源=逐步**降低**模型智能要求)、两条训练数据流(图→JSON 训 reading VLM / JSON→IntakeOutput 训 correction 文本模型)塌成一个更难的 VLM 问题、杀归因、让 reading 烂掉饿死小模型监督、还会重引入"信自己刚看的图>尺寸链"的 bug(trust-the-dim 正因 correction 不能重感知才有效)。

**D2 脚手架 = 降智机制本身。** 每道护栏(provenance/双通道/J0J1门/重读)都是"弱模型不再需要聪明到能独立做对"的那件事。所以修 reading 靠**机制**(不是换强模型)是战略中心:次顶尖(Sonnet级)reading 现在用机制顶到 GPT-5.4 干净的上界,小模型才有好监督蒸馏。

**D3 看图仲裁归 judge(J0/J1 本就看图)+ 重读循环,不进 correction 生成。**

**D4 who-fixes 判据(image-blind 边界):** correction 只修"独立冗余证据仍在 JSON + 不靠猜"的值错→可放行;证据销毁(尺寸链刻度当墙=通道塌缩)/漏元素/身份错(门当窗)/需要猜→必须 reading + J0 中止重读。"EP/保险通过 ≠ 几何对"(founding §2.4:DeepSeek 1.2m 幽灵房 EP 干净通过)。

**D5 只有矢量 JSON 被证明是 correctness 有损瓶颈(schema 表达不了)才回头考虑 VLM-correction。** sm21 不是(GPT-5.4 产出干净 JSON=表达力够,瓶颈是 reading 质量)。

**judge 路由两轴(用户点名要仔细设计的):** severity × recoverability。`recoverability ∈ {correction_recoverable, unrecoverable, unknown}` 做成 CriterionVerdict 显式字段;`blocking = any(severe/fatal 且 ≠ correction_recoverable)`,缺省→当 unrecoverable→**向后兼容**老 verdict。J0 放行四条**同时**满足:①值错非身份/存在错 ②有独立幸存通道钉真值 ③冲突落 A3 §1 可解集 ④缺陷被诚实标(provenance/check)。**默认不确定→中止**(假绿出货代价 > 浪费重读)。J1=确认门:对参考独立复审,归因 reading(通道不够/感知错)vs correction(仲裁砸了)。

**根因:** founding 框架(2026-06-07,见 [[recognition-modeling-capability]] §2-§5)**correction 半边已落地**(`A3_arbitration.md:28` stroke_vs_dimension→trust the chain;A0 evidence model 全齐),**reading 半边从没落进 0-5 schema**:Stroke 无 provenance/confidence(`schema.py:35-43`)、`reading.py:13` 承诺的 stroke↔dimchain consistency check 没实现(只有 _chain_closure)、guide 无双通道纪律/dim-tick≠wall 负例、pen_library 无门≠窗反例、verdict 无 recoverability 轴。

**修复=两条等重战线,correction(A1-A4+确定性核)一行不动:** Front1 reading 诚实(Stroke 加 provenance/confidence/dimension_refs + 落地那个 check + guide/pen/judge prose);Front2 J0 recoverability 路由(verdict 加轴+blocking 改 + J0 四条判据+默认中止 + J1 归因)。**关键:可选字段+非阻塞 flag+verdict 向后兼容 → 不需重录 sm20/sm21 golden baseline。**

**已落地 + 文档同步(2026-06-22 `6.22_ReadingHonestJudgeRouting`):** 代码两战线全落(测试 288→297、golden baseline 零字节差、Codex APPROVE-WITH-CHANGES 5 findings 全采纳、Claude 大节点逐行审 + 命门确认 CROSS_CHECK FAIL=FLAG 非 BLOCK)。D1-D5+两轴路由已同步进 contracts §0.3/§5.3 + decision_log §A + plan N1b + CLAUDE §2(memory↔文档硬纪律已闭环)。**残留=sm21 重跑验证**,用户定与命名确定性化等其他待改项**攒齐一次性重跑**(不单独跑)。**同源欠债收尾(2026-06-22,接着同日做):** 框架三件套=让错「可见→可归因→可重读恢复」。**可见**=本条(provenance);**可归因**=PR-A `0c625fe`(`record_baseline` 读 `1_correction/corrections.json` → `baseline.json.corrections_summary` + RUN_REPORT「校正审计(看错↔改错)」节;不动 gate flags/计数;收口 contracts §5.4 baseline 侧;残留 gt-diff×corrections JOIN 归 N4);**可重读恢复**=PR-B `600d30e`(0_reading auto re-read——**子代理即 runner**:主控 Agent 冷启隔离子代理重看图,**非 VLM-API-gated**[我先前误判、用户纠正];`AWAITING_REREAD` 非终止态 + `RunPolicy.reading_runner_available` 默认 False 向后兼容 + `_verdict_outcome` 用 root 段算预算 + 子代理写 flat view→`resample --force` 记 attempt;3 次不过 quarantine;orchestrator 保持纯逻辑不 spawn、spawn 是主控运行时协议;盲——判语/prior/gt 不注入)。两 PR 各经 Codex `APPROVE-WITH-CHANGES`(7 findings 全采纳)+ SPLIT + Claude 大节点逐行审,测试 288→**307** 绿、golden baseline 全程零字节差。**坑:本机分类器(auto 权限模式)曾长时间不可用卡死所有 write 类工具,改手动确认模式绕过。** 关联 [[per-stage-validation-judge-architecture]] [[sm21-dualmodel-backlog]] [[codex-execution-protocol]]。
