# 读图脚手架行为性改动清单 —— 好版本 → 今天

> **参照系 = 几份好 reading 共同的脚手架状态**（用户 2026-08-16 定的方法）。
> ⛔ 不用单点 diff：单点会不断生成假线索（本文件 §0 有当天被打掉的一条实例）。
> **判据 = 在几份好 reading 里都成立、而今天不成立的东西。**
>
> **这是调研，不是实验。** 全部结论来自 `git diff` 与历史 run 的溯源记录，零额度消耗。

## 〇、先立参照系（这一节本身就打掉了一条假线索）

三份独立的好 reading，各自的树版本都有记录：

| run | 模型 | 墙 | 窗 | git HEAD |
|---|---|---|---|---|
| `run_2026-07-02_sonnet_flow_e2e` | Sonnet 5 | **9/9** | 7/7 | `1595981` |
| `run_2026-07-07_haiku_cv_retest` | Haiku 4.5 | **9/9** | 7/7 | `723b0f9` |
| `run_2026-07-08_gpt54mini_cv_retest` | gpt-5.4-mini | **9/9** | 6/7 | `ebddada` |

（sm24 侧另有 `run_2026-07-07_haiku_cv_probe`，同为 `723b0f9`。）

**⭐ 因果关系（用户 08-16 澄清，此前 orchestrator 记错过）**：好 reading 最先来自
**Sonnet 的一次自发行为**，我们把那个行为**拆解并固化成了 CV 工具箱**，固化之后
**Haiku 做到了、gpt-5.4-mini 也做到了**。⇒ 工具箱的设计意图就是**让模型强弱不再是变量**，
而它成功了两次。**⛔ 因此「模型不行 / 模型漂移」这条解释从根上不成立**，
⛔ 也不存在「强模型赛道 vs 弱模型赛道」——那是 orchestrator 编出来的划分，已撤回。

**好窗口内部（`1595981` → `ebddada`）读图脚手架 = 1522 增、零删**：

| 文件 | 好窗口内变动 | 说明 |
|---|---|---|
| `guide.md` | **0** | 三次成功期间一个字没动 |
| `reading_guide.md` | **0** | 同上 |
| `pen_library.md` | **0** | 同上 |
| `session_kickoff.md` | **+1** | 基本稳定 |
| `cv_toolbox.md` | +58 | ⚠️ **正在建设中，好版本之间本来就不一致** |
| CV 工具实现 | +1400 | 就是「让它变好的那个东西」 |

⇒ **参照系取 `ebddada`**（最后一份好 reading，且是好窗口的超集）。

### ⛔ 本方法当天打掉的一条假线索（记下来，防止重犯）

orchestrator 用**单点 diff**（`723b0f9` vs 今天）发现三条被删的规则
（`prefer empty hands over wrong anchors` / `a gray peak is a candidate, not automatically a wall` /
`log rejections`），并注意到它与今天的失败特征（每抽都多画墙，extra=8–12，而 07-07 是 extra=0）**对得上**。

**多版本一查即倒**：

| | `1595981` 9/9 | `723b0f9` 9/9 | `ebddada` 9/9 | 今天 |
|---|---|---|---|---|
| 那三条规则 | ⛔ | ✅ | **⛔** | ⛔ |

**三份好 reading 里两份没有这三条规则** ⇒ 不可能是杠杆。
⇒ **判据**：**单点 diff 只能产生候选，多版本交集才能过滤。** 凡「时间吻合 + 症状吻合」
仍不足以立论 —— 这已是同一形状第二次（08-15 「省 crop 纪律」那次是第一次）。

---

## 一、⭐⭐⭐ 唯一「两份弱模型成功里都在、今天没有」的一条

### B1 · pilot 停等审阅门被拆除

`session_kickoff.md` Workflow：

```
07-07 / 07-08 ：2. Do one pilot image first.
                3. Stop and wait for review of that pilot; do not batch remaining images yet.
                4. After the pilot is approved, batch the rest.
                （结尾）Do the pilot first, then stop and wait for feedback.

今天          ：Nobody reviews your work mid-run and nobody will answer a question you ask.
                If you find yourself about to stop and ask whether to continue,
                that is the signal to keep going.
                2. Start with one plan image and finish it completely.
                3. Then run guide.md §6 self-check against that finished file …
                （结尾）Work straight through … There is no review point.
```

**在两份弱模型成功里的状态**：
- 07-07：kickoff 原文有此门；判卷记录写着 **「pilot-r1 过度分割成 19 道墙，在 pilot review 时被抓出、
  靠 crop 逐处核验消掉」** ⇒ **门被真实使用过，且它正是消除多画墙的那一步**。
- 07-08：溯源记录明写 **「pilot(1f) reviewed by orchestrator before batch (pilot门 kept — Haiku needed one 打回)」**
  ⇒ **换了模型、换了家族，这道门被刻意保留**。

**替代物 = 自检**（`guide.md` §6 逐条自查）。而本仓已多次记录**自检不可靠**：
`self_check.all_visible_strokes_captured` 被诚实填 false 却全仓零消费者（08-01）；
今天的复现里，同一个字段被**翻来覆去改了三次**、两次与自己的摘要矛盾。

**⚠️ 这条「测过」但没测对**：08-15 的 B1 抽只用 per-run directive 恢复了「打回」，
**① 没恢复 kickoff 原文 ② 用冷启续做而不是同一会话** ⇒ 恢复的是打回动作，不是这道门。
**08-16 的复现里这道门真的出现了**（读图器自己停下来等审），
但 orchestrator **在 pilot 还错着的时候就批准放行、并明确解除了后续审阅**
⇒ 其余五张图零 CV 调用。**⇒ 这条至今没有被正确测过一次。**

**可疑度 ⭐⭐⭐**（唯一满足「两份弱模型成功里都在、今天没有」的项）

---

## 二、⭐⭐⭐ 新增的强制义务：让读图器去做好版本明令禁止的事

### A1 · `scale_origin` 成为每张平面图的必填项

好版本 `guide.md` §1 原文：

> **Each image is read in its OWN local 2D frame — the reading stage does NO world placement**

今天：

> Each image is read in its OWN local 2D frame — the reading stage does **no topology placement**.
> The one required plan-frame datum is `scale_origin`; …
> Every plan view **must** declare `scale_origin`.

而 `scale_origin` 要求的是：

> the world origin is **the SW inner corner of the overall projected maximum building boundary**
> … Prefer measuring that SW inner corner as plan-local (0,0) …
> If plan-local (0,0) is elsewhere, record its **signed measured offset** from that SW inner corner.

**这要求读图器同时判断**：① 整栋**跨层**投影最大边界；② 该边界的**内**角
（⇒ 必须判断墙厚 / 内外皮，而墙厚正是本项目「标注/墙厚/出模」专项**尚未解决**的题）；
③ 把它落到世界坐标 —— **这三件都是好版本明文禁止读图器做的「world placement」**。

**扩散面**：这条同时写进了 `session_kickoff.md` 非可议项、`guide.md` §1、§2 schema 注释、
§6 自检清单、`pen_library.md` —— **五处**。

**在两份弱模型成功里的状态**：⛔ **两份都没有这个字段**（好版本明令禁止）。

**可疑度 ⭐⭐⭐**：新增、强制、扩散五处、语义上是全文档最难的一项，
且**方向与好版本的禁令相反**。**从未被任何一抽单独测过**，也不在旧的杠杆清单上。

---

## 三、⭐⭐ 工具从「给答案」变成「会拒绝」

### C1 · `px_m_calibrator` 跨轴不一致直接 RAISE

`tools.py` 新增：两轴独立拟合的 scale 相对偏差 > **0.30%** ⇒
`raise ValueError("cross-axis calibration disagreement: …")`，**在 blend 之前抛**。
`cv_toolbox.md` 同步加了一句「A cross-axis disagreement error means at least one endpoint pair or
transcribed dimension is wrong; do not average or reuse that result.」

**在两份弱模型成功里的状态**：⛔ 两份都没有（工具当时一定会返回一个值）。

**已有实测旁证**：08-15 A1 抽实测后果 = **门报错、没给合法出口 ⇒ 模型放弃像素换算、退回 OCR + 目测**（F-34）。
08-16 复现里读图器的两轴差 **44.6%** —— 在好版本下工具会给它一个（偏的）值继续走，
今天它会被拒 ⇒ 直接掉进 F-34 那条退路。

**可疑度 ⭐⭐**（机理清楚、有实测旁证，但从未单独隔离测过）

---

## 四、⭐ 噪声类：新增负担与文档自相矛盾（单条不致命，合计吃注意力）

| # | 内容 | 好版本 | 今天 |
|---|---|---|---|
| **D1** | **`local_x_positive` 文档自相矛盾**：§4 明写 "Do not emit `facade.local_x_positive`"，而 **§6 自检清单仍要求** "elevation `facade` block filled image-local (view_facade + **local_x_positive** + mirrored)" | 一致（要求填） | **⛔ 自相矛盾** |
| **D2** | `expected_output_id` / `input_inventory.json` 命名规则 **+12 行**（含「不要在 `_view` 后面再加 `_view`」的反例说明） | 无 | 有 |
| **D3** | `reading_guide.md` **+30 行**：虚线/隐藏窗四条负例规则 · 非矩形外轮廓凹角 · 翼部划分 —— **sm21/sm24 都用不到**（都是矩形共底面盒子） | 无 | 有 |
| **D4** | `pen_library.md` +5 行：`scale_origin` 再述一遍（A1 的扩散面之一） | 无 | 有 |
| **D5** | `dimensions[]` 新增三个可选键 `boundary_kind`/`boundary_endpoint`/`boundary_ref`（wing-break） | 无 | 有 |
| **D6** | `Stroke` 新增 `line_style` / `visibility` 两个可选字段 | 无 | 有 |

⇒ 合计：读图器在动笔之前要多读 **~50 行与本 case 无关的规则**，其中一条**自相矛盾**。

---

## 五、已排除 / 已撤，不必再测

| 项 | 状态 |
|---|---|
| 输入图纸 | 逐字节相同（6/6 sha256 已核） |
| 模型身份 / 模型漂移 | **⛔ 从根上不成立**：三模型两家族都做到过；工具箱本就是为了消除模型变量而拆出来的 |
| `cv_toolbox.md` 那三条被删规则 | **⛔ 已证伪**（`ebddada` 也没有，见 §0） |
| prescan 存在 | 08-15 D1 已从能力层撤除并行为验证 |
| guard 能力封口（A3） | 08-16 E1 已撤除；能力被用了 4 次、零次用于测量 |
| 判卷器 | 老产物今天重判仍 9/9 ⇒ 尺子没变 |

---

## 六、⇒ 建议的恢复顺序（保留其他开发，只回滚影响项）

按「两份弱模型成功里都在 / 都没有」排：

1. **B1 · 恢复 pilot 停等审阅门**（改 `session_kickoff.md` 的 Workflow 段回到好版本形态，
   其余一律不动）。**唯一满足交集判据的一项**，且两份成功都刻意保留过它。
   ⚠️ 恢复它意味着承认「reading 环节需要一个审阅者」——这与「autonomous 北极星」有张力，
   但按用户 08-02 口径，**controlled lane 完全算真实工程成功**，只是不得记成「弱模型独立满分」。
2. **A1 · 把 `scale_origin` 从「读图器必填」挪走**（改由 correction 段推导，或降为可选/可 null）。
   理由不是「它没用」，而是**它让读图器去做好版本明令禁止的 world placement，且依赖尚未解决的墙厚判断**。
3. **C1 · 给跨轴校验一个合法出口**（拒绝时返回两轴各自的值 + 明确的下一步，
   而不是抛异常让模型退回目测）。⛔ 不是撤掉校验 —— 校验本身是对的，缺的是出口。
   同族判据：**立规则不给合法出口 ⇒ 模型自己发明出口**。
4. **D1 · 修掉 `local_x_positive` 的文档自相矛盾**（零风险，顺手做）。
5. D2–D6 · 暂不动（噪声类，单条不致命；若 1–3 恢复后仍不达标再考虑瘦身）。

**⛔ 口径**：以上是**调研结论 + 排序**，⛔ 不是「已验证的修法」。
本仓已两次栽在「从文档 diff 反推出结论就写进 plan」上（08-15 省 crop、08-16 那三条规则）
⇒ **每一条恢复后都要跑，且按纪律至少两抽。**
