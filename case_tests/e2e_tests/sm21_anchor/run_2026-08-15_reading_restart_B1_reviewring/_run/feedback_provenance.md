# 打回文本逐句出处 — B1 pilot review

> **为什么有这份文件**：orchestrator 在写这份打回**之前**已被 gt 污染
> （为出 A1/A2 分数跑过 `score_reading_vs_gt`，终端打印了 gt 的墙坐标与窗跨）。
> 判据「⛔ 接触 gt 之后不得把任何结论送回同一个 run」因此在本 run 上已被触碰。
> 本文件是缓解措施而非豁免：**打回的每一句都必须溯到「产物自身证据」或「skill 原文」**，
> 溯不到的不许进 feedback。全文见 `feedback_draft.md`（= 实际发出的 `feedback.md`）。
>
> ⭐ 附带查明（2026-08-15）：07-07 那次打回**同样不是干净的** —— 该 run 的
> `run_config.yaml` 把 orchestrator 一栏写作 `role: judge2+orchestration`
> （`model_id: claude-fable-5`），即**打回者本人就是持 gt 的 judge②**。
> 它在打回前有没有看过 gt 无记录。⇒「07-07 是干净基线」这一说法**从未被证据支持**，
> 本 run 的形态与之同形、而非更差。

## 逐条

| # | 打回里说的 | 出处 | 类别 |
|---|---|---|---|
| 1 | 标定没走工具、没留 sidecar | `out/` 下**零** `px_m_calibrator` sidecar（实测 `ls`）；模型自己的 summary：*"Manual pixel-to-meter conversion"* | 产物自身 |
| 1 | 「必须可复现，否则是无效数据」 | `cv_toolbox.md` §Disciplines 原文 | skill 原文 |
| 1 | 「x/y 放同一次调用让跨轴校验真的跑」 | `cv_toolbox.md` 原文（px_m_calibrator 条）+ F-34（拆两次单轴可绕过，同日实测） | skill 原文 + 机制 |
| 2 | 内部隔墙坐标是目测 | 模型 summary "Measurement Uncertainties" #1 **原话** | 产物自身 |
| 2 | 「量而非画完再找支持」 | `cv_toolbox.md` §Disciplines "Measure before drawing" 原文 | skill 原文 |
| 2 | 「你手上有 29 列 + 19 行候选」 | `1f_walls_col/001_wall_line_profiler.json`(29) · `1f_walls_row/…`(19) 实测计数 | 产物自身 |
| 3 | 尺寸链只转录了约 10 条、闭合未验 | 模型 summary "Uncertainties" #3 **原话** | 产物自身 |
| 3 | 「每个链条数字都要进 dimensions」 | `guide.md` §6 checklist 原文 | skill 原文 |
| 4 | 15 条 stroke 里 11 条 `seen`、只有 4 条带 `dimension_refs` | 产物 JSON 实测统计 | 产物自身 |
| 5 | `ocr_texts` 为空但图里有文字 | 模型 summary "Uncertainties" #4 **原话** + 产物 `ocr_texts` 长度 0 | 产物自身 |
| 收尾 | 「每张图各自量，不许继承布局」 | A1/A2 实测的失败形状（只量第一张）；**未向读图器透露 A1/A2 存在** | 方法纪律 |

## ⛔ 刻意没说的（即使我知道）

- 任何坐标数值（墙位、窗位、隔墙 x/y）
- 正确的墙/窗**数量**
- 任何方向性提示（「偏左了」「少了一堵」「那面墙不在那」）
- 它画错了**哪一条** —— 打回只指方法，不指具体错处
- gt / baseline / 其他 run / 判卷结果的任何信息

## 自查

通读 `feedback_draft.md` 后确认：全文**零数字坐标**；出现的数字只有
`29` / `19`（它自己的候选计数）、`15` / `11` / `4`（它自己的 stroke 计数）、
`~10`（它自己的原话）。这些全部是**读图器自己产物里的量**，不是答案。
