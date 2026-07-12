# B2b 批施工派发（terra 执行档，2026-07-12）

**任务**：按 [AI_agent/proposals/c2_b2b_detail_spec.md](../../proposals/c2_b2b_detail_spec.md) **v2 定稿**施工 B2b 批（E3' envelope 权威矩阵安全变形）。该稿是**唯一施工合同**（累计式自包含）：签名、wire 形状、gate id、审计形状、断言均以稿为准；含糊处按稿内"施工纪律"，不自创。

## 硬边界

- 基座 = 当前 HEAD（工作树干净）。**只放行 B2b**：不动 B3/Vg/B4/B5/E4 的任何顺带施工；不动 golden/gt/case anchors；不改管理文档（CLAUDE/plan/decision_log/architecture）；本批**不创建 commit**。
- 动工前先按稿 §0.2 执行施工前置门机械断言（只查 B2/B3/Vg 已收录条件；**不得**预读三个 B2b 自建容差字段）；施工步骤 1 完成后执行 §0.3 三容差自检，通过才继续。
- v1/v2 legacy 行为逐字节不变（稿内有逐字节锁测试要求）；B1 安全拒绝分支只许**扩展**不许**替换**（B2 批 F1 教训，安全拒绝分支必须带测试锁）。
- 改 `src/`/`scripts/`/`tests/` 前先备份既有将改文件到 `backup/src_history/2026-07-12_b2b_envelope_transform/`（按仓库相对路径）。

## 测试纪律

- **本执行环境 ~30s 杀前台长进程，全量 pytest 由主控终审独立跑（唯一权威门）**——不要反复尝试全量；分组跑定向模块（新增测试文件 + 被改模块对应测试组），逐组记录 passed 数。
- 稿内测试族（§10/§11 枚举，含 `inspect.signature` 无默认断言、篡改负例、fixture 族）须全数落地；确有未竟，在简报"未决·偏离事项"逐条列明，不得静默。
- 稿章节 → 测试的映射表写进简报（B2 批终审后的既定要求）。

## 交付

1. 工作树内完成全部代码+测试改动（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-12_b2b_construction_brief.md`，结构对齐 [2026-07-11_b2_construction_brief.md](../execution/2026-07-11_b2_construction_brief.md)：改动映射（稿章节×代码落点）/ 备份 / 验收与测试（分组计数）/ 预期行为变化 / 未决·偏离事项 / **review-ask**（自报没把握处、判断取舍、风险点，诚实标注；无则注明 none）。
3. 回复 INLINE 只给 terse report（各组 passed / 改了哪些文件 / 关键结论 / 偏差 / review-ask 摘要）；**不要贴 diff 或文件内容**。

审向：主控（Claude 侧）终审 = 独立全量 pytest + 逐行 diff + review-ask 逐条亲核（方案A：GPT 侧施工、Claude 侧终审）。
