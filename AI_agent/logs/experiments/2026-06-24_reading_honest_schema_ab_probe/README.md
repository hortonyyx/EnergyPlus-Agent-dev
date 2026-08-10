# reading-honest schema 回归 —— A/B 控变量探针 + 误归因翻案（2026-06-24）

## 结论一句话
诊断①推测的"reading-honest 的 `dimension_derived` schema 字段导致过度分割"是**误归因**，已证伪。
真因 = Sonnet 对满家具图的**首抽随机感知失败**（南带把窗洞边/尺寸链 tick 当竖隔墙），与 schema 无关。
判 sm21 时 judge+reread 机制按设计正确处置（att1/att2 16墙 → att3 10墙命中 gt）。

## 实验设计（单变量隔离）
- 模型钉死 = Sonnet 4.6；图钉死 = sm21 `1f_view.png`（满家具平面）。
- 唯一变量 = 0_reading skill 版本：**NEW = 当前 reading-honest**（HEAD）vs **OLD = `fa04ef6^`**（reading-honest 之前）。
- NEW guide 有 7 处 provenance 提及、OLD 0 处（差异确认只在 reading-honest；judge_rubric 不被 reading 子代理读，排除 600d30e 污染）。
- 每臂 2 样本，Sonnet 冷启子代理，隔离 skill 目录、禁读 gt/旧识图/另一臂/testdata。

## 结果（墙数已代码核实）
| 臂 | 样本 | 墙 | 窗 | wall provenance | 文件 |
|---|---|---|---|---|---|
| OLD | s1 | 13 | 7 | 无 provenance 字段 | old_s1_13walls.png / arm_old_s1.json |
| OLD | s2 | 14 | 7 | 无 provenance 字段 | old_s2_14walls.png / arm_old_s2.json |
| NEW | s1 | 14 | 7 | 全 `seen`、0 `dimension_derived` | new_s1_14walls.png / arm_new_s1.json |
| NEW | s2 | 16 | 9 | 全 `seen`、0 `dimension_derived` | new_s2_16walls.png / arm_new_s2.json |

## 跟 gt 对账（sm21 gt = `case_tests/test_baseline/gt/sm21_anchor/gt.json`，DXF 抽取 + 用户人工核过）
- **gt 真值 Floor 1 = 10 道墙**：4 外墙 + 6 内墙（走廊 y=3/y=5 两横 + 南带 x=5/x=10 两竖 + 北带 x=5/x=10 两竖）；南北各 3 房、走廊全宽。
- 四份 A/B **北带全对**（2 竖墙 3 房）；**南带全部切多**（gt 2 道竖墙 → 读成 4–5 道）→ schema 无关，是南带窗+尺寸 tick 的感知问题。
- 附带：OLD-s1、NEW-s2 各有一处西侧 `-0.9` 小凹口几何误读（Sonnet 偶发幻觉台阶）。

## 决定性证据（attempt 级，误归因翻案）
`case_tests/e2e_tests/sm21_anchor/run_2026-06-23_sonnet_reading/0_reading/attempts/`：
- **att1 = 16 墙、全 `seen`** → 过度分割在 `dimension_derived` 标签出现**之前**就发生。
- att2 = 16 墙（15 `dimension_derived` + 1 seen）→ 同样的 16 墙换了标签，墙数没变。
- **att3 = 10 墙、全 `seen` → 精确命中 gt**（= 磁盘接受的 `1f_view.json`，逐字节同；但该 run `stop_reason=quarantined@0_reading`，judge 第 3 次仍判 severe、预算耗尽）。
- "schema=头号嫌疑"的源头 = **att2 的 judge 判语原话** "provenance='dimension_derived' confirms the mechanism" —— 这句 judge **假设**被原始诊断当既成事实，传进 plan/memory。att1（all-seen 16墙）+ A/B（0 dimension_derived 仍 14–16）双重推翻。

## 行动
- **schema 修法③（收敛 dimension 表述）取消** —— 不是病因。
- 真 lever：南带杂物/尺寸掩膜 or 局部放大裁图（原"次要"升为主）；首抽纪律强化"窗洞边≠墙、尺寸 tick≠墙"；加 reread 预算；换强模型（Opus 跑 sm24 一次干净）。
- 流程教训：judge 的归因**假设**未用 attempt 级事实验证，不得直接成为修法依据。

详见 plan.md N1d。
