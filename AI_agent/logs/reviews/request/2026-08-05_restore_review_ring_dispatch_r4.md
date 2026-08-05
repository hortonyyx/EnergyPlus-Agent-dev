# 派工单 r4 · 把 reading 的 **review 环**在产品库里恢复（回退 `95ba3dc` 的那一处）

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）· **依据 = 用户 08-05 当面拍板**
- **施工席**：GLM-5.2（排在 F-4 那单之后）
- **性质**：**定向回退**，不是新设计

---

## 1. 用户原话与范围

> 「针对主控介入的改动回退（都收束在专攻 reading 里再去讨论），本身的硬隔离等其他升级先保留，
>  真 reading 出问题了也好排除嫌疑」
> 「先恢复主控介入的那个 review 在环吧，因为我预计 reading 专攻可能并不简单，需要单开支线做，主线先恢复」

**只回退一条**：`95ba3dc`（`8.01_ReadingNoMidRunReviewPoint`）删掉的 **pilot 停等 review 环**。

**⛔ 明确不回退**（这三条虽然也在「发现主控介入之后」，但与机器耦合，回退会当场坏）：
- `d246c90`（08-04）输出文件名按 `expected_output_id` —— merge 门现在强制，回退即被拒收；
- `b8f9a8d`（08-03）R1 批 A 的 guide 改动 —— 与 gate① 一起改的；
- `15cfcb8`（08-01）「先标定再写坐标」提到顶层 —— 回退等于削弱纪律。

**⛔ 也不回退**：硬隔离、`scale_origin` 契约、07-31 那批、判卷层任何东西。

## 2. 要改的两处（`95ba3dc` 自己的提交信息就点明了这两处必须成对改）

1. **`skills/intake_pipeline/0_reading/session_kickoff.md`**
   把 `95ba3dc` 删掉的 Workflow 步骤恢复（`git show 95ba3dc` 的 `-` 侧）：
   - `2. Do **one** pilot image first.`
   - `3. Stop and wait for review of that pilot; do not batch remaining images yet.`
   - `4. After the pilot is approved, batch the rest (…)`
   - 文末 `Do the pilot first, then stop and wait for feedback.`
   **⭐ 但要保留 `95ba3dc` 加进来的好东西**：`guide.md` §6 自检那一段（「第一张做完后逐条自检、
   修完再继续」）**不要删** —— 最终形态 = **pilot → 自检 → 停下等审 → 放行批量**。
   ⛔ 删掉那句「Nobody reviews your work mid-run and nobody will answer a question you ask.」
   （它与 review 环直接矛盾）。

2. **`src/agent/execution/isolation.py:729`** 生成 spawn prompt 的那句副本
   （现文：`"Work straight through to the end on your own: no reviewer will answer you …"`）
   —— `95ba3dc` 原文明写「不改则前者无效」，所以必须同步改回「先做 pilot、停下等审」。

## 3. ⚠️ 一条 orchestrator 的实测发现，施工时必须知道（但**本单不要去解决它**）

我今天用**原样的 07-07 kickoff**（含上述三行）跑了一抽 Haiku：**它没有停**，一口气做完 6 张。

> **原因（推断）**：07-07 的读图器是**会话内子 Agent**，「停下等审」= 结束本轮、交回控制权，天然可实现；
> 今天是 `claude -p` **一次性 headless 调用**，"stop and wait" 结构上没有对应物 ⇒ 模型只能继续做完。

⇒ **本单只负责把文字恢复到位**（这是用户要的「主线先恢复」）。
**「怎么让它真的停」属于会话形态问题，归后续 reading 支线**，⛔ 本单不许顺手改 spawn 形态、不许加轮次控制。
请在简报里把这条限制写清楚，避免下一个人以为文字改了就等于机制回来了。

## 4. 锁 / 验收

- 这两处都是**提示词文本**，锁的形态相应地是「文本契约锁」：
  1. 断言 `session_kickoff.md` 与 `isolation.py` 生成的 spawn prompt **对 pilot/review 的表述一致**
     （⛔ 不许一处说停、一处说别停 —— `95ba3dc` 之所以要成对改，就是这个理由）；
  2. 断言「无人会审你」那句**不再出现**在两处任一。
- 跑 `tests/test_isolation.py` + 全仓 `python -m pytest -q -n auto`，报三个数字。
- 按项目惯例做备份：`backup/Skill_history/2026-08-05_restore_pilot_review_stop/`。

## 5. 交付

- commit（`08.05_<英文标签>`，⛔ 不 push，⛔ 只 add 自己改的文件）；
- 简报 `AI_agent/logs/reviews/execution/2026-08-05_restore_review_ring_glm_r4.md`
  （含 §3 那条限制的复述 + 三数字 + 诚实披露）。
