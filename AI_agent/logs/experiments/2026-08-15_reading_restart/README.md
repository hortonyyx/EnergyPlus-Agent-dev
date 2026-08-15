# 2026-08-15 · reading 重启第一批（A1 / A2 两抽）

> **一句话**：在**没有「停下等审阅」环**的形态下，Haiku 4.5 两抽都没能再产出好 reading ——
> **不是差一点，是塌到地板**（墙 3/9 与 1/9，对照 07-07 的 9/9）。
> 失败形状与 08-02 Sonnet 无监督那轮**逐项同形**：全 `seen` · crop_zoom 0 · 目测。
> 同轮撞出两个真缺陷（F-33 已修、**F-34 未修**）。

## 0. 这一批要回答什么

08-14 的验收 3/3 证明的是「**好 reading → EnergyPlus 通**」，那份 reading 是
07-07 Haiku 产物逐字节复用（`cmp` 7/7 全同），**当天一张图都没识**。
剩下的那一半 = 「**机器今天还能不能再产出一份好 reading**」。本批就是它的第一次实测。

用户 08-15 口径：*「实验说话。有杠杆的全部恢复也行，但尽量正向增益保留；
真正让 reading 不依赖高智力模型的放到 reading 专项，现在先解决主线阻塞问题。」*

## 1. 变量设计（07-07 之后共 5 条碰得到读图器的改动）

| | 改动 | 本批处置 |
|---|---|---|
| B1 | 「pilot → 停下等审阅」被删（`95ba3dc`, 08-01），换成「首图跑 §6 自检」 | ⭐ **不恢复** = 唯一变量 |
| B2 | 硬隔离壳（prompt 级 → clean-room + guard） | 保留新壳（顺带复测 F-2/F-4/F-5） |
| B3 | cv_toolbox 强制方式（run 级 directive → skill 常驻文本） | ⭐ **恢复 directive**（逐字抄 07-07） |
| B4 | prescan triage 那一整套（07-07 从未用过 prescan） | 不点名、不禁用，观察它自己走哪条 |
| B5 | `px_m_calibrator` 跨轴 0.30% 硬校验 | 保留（离线实测过为正向 —— **但见 F-34**） |

两抽同配置（纪律：识图成绩至少两抽，同配置曾差 2.8 倍）。
run 目录：`case_tests/e2e_tests/sm21_anchor/run_2026-08-15_reading_restart_{A1,A2}`。

## 2. 结果

### 2.1 分数（同一把尺子 `score_reading_vs_gt --case sm21_anchor`）

| | 07-07 好 reading | A1 | A2 |
|---|---|---|---|
| 平面墙 | **9/9**（最大偏移 **0.0 m**） | **3/9** | **1/9** |
| 平面窗 | **7/7** | **0/7** | **1/7** |

⇒ **两抽都塌**。这不是「同配置方差」能解释的区间。

### 2.2 过程指标（真正的判据 —— 杠杆是工作模式，不是分数）

| | 07-07 | A1 | A2 |
|---|---|---|---|
| CV 工具调用总数 | **92** | **6** | **2** |
| 量了几张图 | **6/6** | **1/6** | **1/6** |
| crop_zoom | **55** | **0** | **0** |
| px_m_calibrator | 10 | 2 | **0**（整轮没标定过） |
| 平面 `dimension_derived` | **35/35 = 100%** | **0/54** | **0/44** |

模型自己在总结里写了实话：
*"interior positions estimated from **visual grid alignment**"* ·
*"window z-heights **visually estimated**"*。

### 2.3 gate①（`exploratory` + `orthogonal_polygon`，policy_hash 与好 reading 那次相同）

| | 07-07 好 reading | A1 | A2 |
|---|---|---|---|
| pass / N/A / fail | 103 / 18 / **6** | 92 / 24 / **12** | 94 / 24 / **10** |
| 是否被 accept | 是 | **否** | **否** |

⚠️ 基准那 6 条 fail 全是 `dimension_chain_closure`（非阻断）⇒ **满分 ≠ 全绿**，别把「有 fail」当退步。

## 3. 结论

- **B1 的替代品没顶住**（n=2）。「首图 §6 自检」在两抽里都没能把工作模式从「扫一遍描述」
  切换成「枚举候选逐条量」。这与 08-03 已坐实的判断一致：
  **打回起的作用不是修错，是切换工作模式，而这个差别从第一笔就存在，返工造不出来。**
- **B3 恢复 directive 救不回来**。directive 逐字写着 measure-before-draw，
  A1 在 1f 上量了 6 次、之后 5 张图一次没量；A2 干脆连标定都没做。
  ⇒ **「量而非看」不是一句强制文字能维持的**，与老结论「prompt 强度不是杠杆」同向。
- **B2 硬隔离壳本身没有再拦路**：6 张图全出、merge 成功、guard 7 次 deny 全是
  合理拒绝（管道符 / `find` / `python -c` / 参数格式），**F-2/F-4/F-5 三个修法首次实测通过**。
  ⇒ 07-30 那次 8/8→1/8 的壳侧缺陷这次没复发；**今天的塌不能记在壳头上**。
- **B4**：两抽都以 prescan 起手（07-07 全程 prescan 0 次），然后就**停在候选层没有往下量**。

## 4. 撞出的缺陷

### F-33 gate① 遇到畸形尺寸端点会崩，不是判 fail ✅ 已修 + 已锁 + neuter 实测
A1 的 `North_view` D6 写成 `"to": [11.36]`（少一个分量）。schema 允许（`list[float]`），
`_dimensions_wellformed` 直接 `d.to[1]` → `IndexError` **带崩整个 merge**。
同一文件里 stroke 那条检查显式挡了 `len(pt) >= 2`，dimension 这条没挡。
同族 = F-6（判卷崩而不是说 unsupported），违「门可以判 fail，不可以死」。
修法在 `src/validator/checks/reading.py:_dimensions_wellformed`：present-but-malformed ⇒
`reading.axis_endpoint_consistent` 的 offender；**absent 仍照旧跳过**（不改老产物的判定）。
锁 4 条在 `tests/test_checks_reading_correction.py`，含自证前提用例；
**neuter 实测**：摘掉 `len >= 2` 守卫 ⇒ 锁以原样 `IndexError` 变红。

### ⭐ F-34 B5 跨轴校验有第二个入口 —— 分两次单轴调用即可绕过 ⛔ 未修
A1 的实况：

```
1f_calib_x:  x 锚 425 / 1815.5   → 92.7000 px/m   warnings=0   ← 与 07-07 正确值一致
1f_calib_y:  y 锚 110.5 / 1045.5 → 116.8750 px/m  warnings=0   ← 错（正确 92.675）
```

实测确认：两个锚点放进**同一次**调用 ⇒ `RAISE`（偏差 23.07%）；拆成**两次单轴** ⇒ 两次都
0 warning、门形同虚设。
然后模型**自己**在散文里发现了 26% 不一致，并「解决」为 —— 放弃像素换算、退回 OCR + 目测。
⇒ **门报了错却没给合法出口，模型就自己发明了一个出口。**
⇒ 修正此前的说法：8-15 早先判 B5「纯正向增益」是对着**单次调用**说的；
**按真实入口看，它拦不住实际发生的那条路**（判据「锁必须走真实入口」）。

### F-35（小）cv 证据不进 attempt
`merge` 只带走 `<expected_output_id>.json` + `reading_summary.md`，
`out/*/cv_evidence/` 全留在 `/tmp` staging。⇒ **「它到底量没量」这个审计问题，产物本身回答不了。**
本批证据已手工抢救进 `A1_cv_evidence/` `A2_cv_evidence/`。

## 5. 件

- `process_metrics.py` — 过程指标对账器（**不是判卷器**）。已在 07-07 基准上验过，
  92 / crop_zoom 55 / 平面 35-35 逐项复现。
- `A1_cv_evidence/` `A2_cv_evidence/` — 从 staging 抢救的 CV 证据（见 F-35）。

---

# 追加：B1（恢复 review 环）—— ⛔ 没有恢复到 07-07

`run_2026-08-15_reading_restart_B1_reviewring`。用户 08-15 拍板「可以接受先恢复」，
`reading-agent` 的必要性/形式/智力归 reading 专项。

## 形态
07-07 原形，**⛔ 不改产品 skill**（现行 kickoff 明写 "There is no review point"），
review 环放进 per-run directive 并显式声明覆盖 kickoff 那三句。
协议 = pilot 冷启 → orchestrator 打回（⛔ 不开图纸）→ 冷启续做，⛔ 不用 `--resume`。

| session | 内容 | 时长 |
|---|---|---|
| #1 pilot | 只做 1f，然后停（directive 覆盖生效，**它真的停住了**） | 4 min |
| — | orchestrator 打回 5 条（全文 `_run/feedback_draft.md`，逐句出处 `_run/feedback_provenance.md`） | — |
| #2 batch | 重做 1f + 其余 5 张 | 10 min |
| — | ⚠️ gate① 6/6 view 全拒：`provenance: "pixel-measured"` 非法 | — |
| #3 更正 | 只改词表（`_run/feedback_r2_schema.md`） | 3 min |

⇒ 实际 `rework_rounds = 2`（不是 run_config 声明的 1）：**第 2 轮是 orchestrator 自己
措辞不当造成的**，见下「教训 ①」。

## 结果

| | 07-07 | A1 | A2 | **B1** |
|---|---|---|---|---|
| 平面墙 | **9/9**（最大偏移 0.0 m） | 3/9 | 1/9 | **2/9**（命中的最大偏移 **0.0 m**）|
| 平面窗 | **7/7** | 0/7 | 1/7 | **0/7** |
| 量了几张图 | 6/6 | 1/6 | 1/6 | **6/6 ✅** |
| 标定走工具 | ✅ | 部分 | ❌ | **✅** |
| 平面 `dimension_derived` | **35/35** | 0/54 | 0/44 | **8/30 ↑** |
| CV 调用总数 | **92** | 6 | 2 | **24** |
| **crop_zoom** | **55** | 0 | 0 | **0 ⛔** |
| gate① | 6 fail · accept | 12 fail · 拒 | 10 fail · 拒 | 9 fail · **accept** |

## ⭐ 本轮最重要的结论：打回修的是「覆盖」，不是「深度」

打回把**测量覆盖**从 1/6 修到 6/6（正是打回第 2、3 条要的），
`dimension_derived` 从 0 回到 8，标定回到工具上 —— **行为确实被改变了**。
**但分数没动**（2/9）。

剩下的那条差是 **crop_zoom：07-07 用了 55 次，A1/A2/B1 三轮全是 0**。
而 B1 命中的墙 **max offset 0.0 m** ⇒ **不是量不准，是没去量那些地方**：
外轮廓精确命中，内部隔墙整片缺失或错位。

⇒ 把 08-03 那句判断收窄一格：
> 「任务被分解成『扫一遍描述』而不是『枚举候选逐条量』—— 形状问题不是耐力问题」

**成立，但打回只能改前半段（去量几张图），改不了后半段（每处量到什么粒度）。**
07-07 的 9/9 是「候选 → 放大到该处 → 核验 → 再落笔」这个**逐候选深度**换来的，
而这三轮里一次都没发生。

## 教训

### ① ⭐ 立硬纪律必须同时给合法出口 —— 本日第二次现形
打回第 4 条写的是 *"the label has to match how you got the number"*，
**却没给合法词表**。模型用像素量了、又不是从尺寸链推的，觉得 `seen` / `dimension_derived`
都不贴切，于是**自己造了一个 `pixel-measured`**，六张图全中、gate① 全拒。
⇒ 与 F-34（门报要求却没给出口 ⇒ 模型自己发明出口）**同形**，同一天撞两次。
⇒ 07-07 那次打回原文从未落盘 ⇒ **没人知道当时有没有踩同样的坑**。本 run 的打回原文已落盘。

### ② 「07-07 是干净基线」从未被证据支持
07-07 的 `run_config.yaml` 把 orchestrator 一栏写作 `role: judge2+orchestration`
（`claude-fable-5`）⇒ **打回者本人就是持 gt 的 judge②**（不变量 #4：gt 只有 judge / 人可读）。
它打回前有没有看过 gt 无记录。
⇒ 本 run 的污染形态与 07-07 **同形，而非更差**（本 run 的污染已在 run_config 与
`feedback_provenance.md` 里明写）。

### ③ gate① 收下了一份 2/9 的产物
`exploratory` 档下 9 条 fail 全非阻断 ⇒ accept。这不是缺陷（gate① 本就不判识图质量，
质量归 gate② / gt），但**「过了 gate① 」不能当作「这份 reading 能用」**。

## 缺陷登记（本轮新增，均未修）
- **F-34** 跨轴校验有**两种**绕过：拆两次单轴调用 · **根本不调用该工具**
  （B1 pilot 手算 px→m 即是）⇒ 门挂在一个可选工具上。
- **F-35** cv 证据不进 attempt（merge 只带 `<expected_output_id>.json` + summary）
  ⇒ 「它到底量没量」产物自身回答不了；三轮证据均靠手工从 `/tmp` staging 抢救。
- **F-36** 全仓一条红 `test_b2_prescan_reproduction`：`accept_D/E/F` 由 `dc7b239`
  （08-14 收工那笔）落库但未进 `_PRESCAN_OBJECT_LEVEL` 分类表。
  08-14 记的「2635 绿」跑在 `151e055`、**那笔之后没人再跑全量** ⇒ 又是「尺子跑在改动之前」。
