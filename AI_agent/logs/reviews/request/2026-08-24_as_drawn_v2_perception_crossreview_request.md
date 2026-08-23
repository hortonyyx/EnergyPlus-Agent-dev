# 跨家族三审请求书 · as-drawn v2 + perception 进环

- **送审方**：orchestrator（Opus 5）· **日期**：2026-08-24 · **分支** `08.23_AsDrawnReading`（未合并）
- **前两轮裁决（同一被审对象的前身，均 REJECT）**：
  [一审](../verdict/2026-08-23_as_drawn_design_crossreview_sol.md) ·
  [二审](../verdict/2026-08-23b_as_drawn_design_v2_crossreview_sol.md)
- **被审对象**：`AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/`
  的**代码 + 产物 + 实证档**（⛔ 不是设计稿 —— 见下「这次送审的是什么」）
- **本批口径**：[`AI_agent/guides/reading_correction_split_guide.md`](../../../guides/reading_correction_split_guide.md)

---

## 〇、⭐ 这次送审的是什么，以及为什么形式变了

前两轮我送的是**设计稿**，两次 REJECT 的**病根相同**：
「**我产出的叙述比我产出的东西更合规**」——一审是我自选的变异挑不出自己的盲区，
二审是设计稿描述了代码根本没实现的形态、还拿旧实现的数去证明它。

⇒ **这一轮不送设计稿。** 送的是：

1. **能跑的代码**（`tools/`）
2. **跑出来的产物**（`out/`、`perception/`）
3. **一条命令重跑全部数字**：`python3 …/tools/run_all.py` → [`out/RESULTS_v2.json`](../../experiments/2026-08-23_as_drawn_reading_prototype/out/RESULTS_v2.json)
4. **只陈述当前形态的实证档**：[`README.md`](../../experiments/2026-08-23_as_drawn_reading_prototype/README.md)
   （v1 那份混合口径档已更名 `README_v1_mixed_evidence.md` 原文保留，⛔ 其数字作废）

**⇒ 本文里每一个数，请直接用 `run_all.py` 复算，⛔ 不要采信本文的转述。**

---

## 一、二审列的「进 gt 之前必须解决」七条 —— 逐条交代

| # | 二审要求 | 本轮处置 |
|---|---|---|
| 1 | **真产出一份 v2 三层 JSON 夹具**，用它重跑全部数字 | ✅ 已做（08-23 A3/A4）。本轮进一步：**全部数字改由 `run_all.py` 一次产出**，落 `RESULTS_v2.json` |
| 2 | `NEAR_WINDOW_M` 改为可重算证据，⛔ 不得用单像素 `>0` 桥整段 | ✅ 已改（`OPENING_SPAN_MIN`，按空档**长度**的占比，单像素动不了它）。`punch_middle_one_pixel` 实测 **0.0 / 0.0** |
| 3 | G-1 加 distinct-source + 最小可分辨间距；补 4 种坏夹具 | ✅ 四种都在（`duplicate_face` / `fabricate_pair_from_midline` / **错误配对** / **单像素门窗噪声**）。⭐ 「assignment 复用」不是造出来的：**新对账门在诚实产物上就抓到了 4 条面线被卖了两次** |
| 4 | 立面线反证必须比完整 runs + 一对一 assignment + 按 view 推楼层 | ✅ 三件都做了 → `reconstruct_elev_lines_check_v2.py`。**清空 `runs_m` 由 24/24 变 0/24**。⚠️ **一对一没有真实夹具**，见 §三 |
| 5 | ⛔ 放弃「0.74 可分真假线」，在 no-bridge 形态下重新找独立证据 | ✅ **已放弃该主张**，本轮任何结论都不引用 `ink_coverage` 作为真假面线的判据 |
| 6 | 定义 **gt 的可评分分母** | ❌ **仍未做**（gt 冻结中）。这是本轮**已知的最大缺口**，见 §三 |
| 7 | README 清理为只陈述 v2 | ✅ 已重写 |

---

## 二、本轮新增的三件（请重点打）

### 2.1 ⭐⭐⭐ 「认」从配置替身变成**独立的 perception 文件**

`perception/<case>.json` 由做识别的一方产出（本轮是 orchestrator 亲手看图），六个桶：
`family_roles` · `wall_pairs` · `solid_band_walls` · `unpaired_wall_faces` ·
`non_wall_face_lines` · ⭐ `ambiguous_face_lines`（**「我认不出来」是合法答案**）。

代码侧三条：**候选穷举 ⛔ 无间距阈值** · **缺 perception ⇒ 响亮降级** · **完备性对账**（每条面线都要有归属）。

**实测**：sm25 1f 49 条面线 / **374** 个候选 / 22 对；2f 46 / 303 / 21；sm24 98 / **1185** / 8。
**gt 侧分数在换掉配对实现前后逐位不变**（sm25 **93.3** / sm24 **100.0**）
⇒ 反证了判分从不消费配对假设。

**perception 坏夹具 5 种，4 种红**（`RESULTS_v2.json → perception_neuters`）：
把标注文字当墙面 🔴 · 漏掉一条面线不表态 🔴 · 配错墙 🔴🔴 · 引用不存在的线 🔴 ·
**把「窗」和「家具」的族名对调** → 原本**六道门全绿而 gt 侧 94.6→51.4**，据此新增判据后 🔴。

### 2.2 新增两条不读 gt 的判据，都是被自己的假绿逼出来的

- `observations_recomputable_from_own_pixels`：查出 **`edges_m` 从来没有消费者**（是个藏东西的地方）。
  ⚠️ **这门第一版差点误伤诚实的 sm24**（偏 1.480 px vs 门 1.5 px），真因是**我的重算公式偷设了
  「墨迹质心 = 支撑列中点」这个生产者从没做过的假设**；改按生产者自己的仿射映射逐边重算后偏差 **0.004 px**。
- `opening_role_matches_where_the_ink_sits`：门窗墨迹落在墙断口里的占比
  （sm25 1f **97.8%** / sm24 **80.3%**，家具族 **0.14%**）。

### 2.3 ⭐⭐ 两把尺子互补，现在是实测

变异 `extend_runs_full`（谎称每条面线画满全图）：
**gt 侧 93.3 → 97.3（高于诚实产物）**，不读 gt 的反向对账 **49 条违规、最差覆盖 0.0127**。
`duplicate_face` / `widen_all` 同形（gt 侧免疫、自洽重算门红）。

---

## 三、⛔ 我自己知道的洞（请当作起点，不是清单）

1. **gt 可评分分母仍未定义**（二审 #6 未解）。
2. **一对一 assignment 没有真实夹具** —— 手上没有任何图纸能让两个目标落进同一条线的容差
   （sm25 楼层线相距 3.6 m）。只有合成 `--selftest`：v1 的 `min()` 判 2 个目标都满足、v2 判 1 个。
3. **立面「多画」不计分**，只有 `unpredicted_lines` 旗标：`spray_lines`（每条旁边撒 3 条）
   与 `duplicate_line` 都是 **24/24 免疫**，只有旗标从 0 跳到 72 / 24。
4. **进深台阶线只有一栋楼的正例**；sm24/sm21 立面**坐标未验**（缺尺寸链转录）。
5. **sm24 有 78 / 98 条面线 perception 主动弃权** —— 数字没错，但离「这张图认全了」很远。
6. **F-86 未修**：列组按「组内多数列」保留区间 ⇒ 一整段面线被静默丢掉（sm25 2f 一堵隔墙只进来一个面）。
   候选修法 `max(1)` 实测 sm25 93.3→94.7、sm24 仍 100.0，**但吃掉 sm24 五个洞口** ⇒ 不采纳。
7. ⭐⭐ **本轮 perception 由 orchestrator 产出，而 orchestrator 在产出它之前已经看过 gt 侧判分结果**
   ⇒ **「模型能不能做到」这个问题本轮没有回答**，要冷启隔离读图器才算数。用户已知悉并拍板走这条（零花费探索档）。

---

## 四、请审阅方回答的四个问题

1. **⭐ 硬纪律 #2 的兑现**：请**再找一种能骗过这套判据的、真实会发生的错误形态**
   （前两轮你各找到一种：一条线两头读到中间没读到 / 一个像素桥回整段墙）。
   ⛔ 请不要只复核我列的变异——我自己挑的破坏方式挑不出我自己的盲区，这是前两轮的病根。
2. **哪些数是假的**：请用 `run_all.py` 复跑，指出本文与 README 里**对不上**的数字。
3. **perception 这个接口有没有偷藏判断**：六个桶里，有没有哪个实际上让代码替模型做了决定？
   反过来：有没有哪个「认」的动作还留在代码里没被拎出来？
4. **能不能进 gt（B 步）**：动 gt 不可逆。若不能，请给**最小的一组必须先解决项**。

**裁决请落**：`AI_agent/logs/reviews/verdict/2026-08-24_as_drawn_v2_perception_crossreview_<family>.md`

---

## 五、复现

```bash
cd <repo>
python3 AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/tools/run_all.py
# 单项：
EXP=AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype
python3 $EXP/tools/checks_as_drawn_v2.py $EXP/out/sm25_1f_v2.json $EXP/tools/cfg_1f_full.json /tmp/c.json [<变异名>]
python3 $EXP/tools/reconstruct_check_v2.py sm25-L_anchor '{"F1":"'$EXP'/out/sm25_1f_v2.json","F2":"'$EXP'/out/sm25_2f_v2.json"}' /tmp/r.json [<变异名>]
python3 $EXP/tools/reconstruct_elev_lines_check_v2.py --selftest
```
