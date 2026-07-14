# Va 批施工派发（terra 执行档，2026-07-14）

**任务**：按 [AI_agent/proposals/c2_va_detail_spec.md](../../proposals/c2_va_detail_spec.md) **v2 定稿**施工 Va 批（opening×claim applicability 薄适配纯函数）。该稿是**唯一施工合同**（累计式自包含）：纯适配核、strict wire、A0 合同登记与 Va 专属测试族全部以稿为准；judge 与执行器分别用自己的 opening-claim 输入调用同一 gt-blind 函数。

## 硬边界

- 基座 = 当前 HEAD `4e4a967`（B-O 已收录，工作树干净，**1021 绿 + 9 strict xfail**）。**只放行 Va**：不放行 B4a、B4b、B5、B5b、E4、reader、gt、scorer、render、REPORT、golden 或运行编排的顺带施工（稿「放行边界」原文）；不改管理文档（CLAUDE/plan/decision_log/architecture）；本批**不创建 commit**。
- 施工前先按稿 §0 施工门机械断言（只查已收录依赖：claims.py 七 claim 常量 / view_manifest.py / schema.py strict v3 / facade.py frame / facade_visibility.py Vg 核 / feature_state.py 中央 release map）。
- **VA-R2 红线**：`correction/__init__.py` 不导出 Va 符号 + import-order 回归测试（防 `execution.view_manifest→correction/__init__→facade_applicability` 包级环）。
- **gt 铁律**：Va 及其测试绝不 import `src/agent/judge/gt.py`、绝不读 `case_tests/test_baseline/gt/`。
- 备份：主控已全量备份 `backup/src_history/2026-07-14_va_construction/`；你若改 `scripts/`/`tests/` 既有文件，改前按仓库相对路径补备份到同目录。

## 测试纪律

- 定向分组跑（新增测试文件 + 被改模块对应组），逐组记录 passed 数；**全量 pytest 由主控轻门独立跑（唯一权威门）**。
- 稿内测试族全数落地；确有未竟逐条列明，不得静默。稿章节→测试映射表写进简报。
- 零 golden 改动；既有 1021 绿基座不许出现回归。

## 交付

1. 工作树内完成全部代码+测试改动（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-14_va_construction_brief.md`（结构：改动映射（稿章节→文件/测试）/备份/验收与测试/预期行为变化/未决·偏离事项/**review-ask**——无则注明 none — routine spec'd execution）。
3. 回复只给 terse report（各组 passed / 改动文件 / 关键结论 / 偏差 / review-ask 摘要），不贴 diff/文件内容。

审向：**Opus 执行审（升一档，GPT 侧施工→Claude 侧审，谁写谁不批）→ 主控轻门（独立全量 pytest + 抽查 diff + review-ask 裁决）**。（07-14 纠偏阶梯，guide §2。）
