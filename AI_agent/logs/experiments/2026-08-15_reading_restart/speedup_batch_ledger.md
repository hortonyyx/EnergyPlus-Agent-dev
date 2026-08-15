# 提速批（prescan triage）效果登记 —— 撤除前的账

> **用途**：用户 2026-08-15 拍板「把 prescan 撤了，本来就是提速批的一个设想，
> 把这个提速批杠杆的效果登个记然后撤掉」。本文件 = 撤除前把它**买到了什么、代价是什么**记清楚，
> 免得日后有人只看到「删了个能提速 52% 的东西」。
>
> ⚠️ **口径先说清**：下面「代价」一栏是**强相关 + 唯一未排除的假说**，
> **⛔ 不是已证实的因果**。因果检验 = 撤除后的 D 组（用户 2026-08-15 拍板**先只跑一抽 D1**；
> 一抽不构成成绩结论 —— 同配置曾差 2.8 倍，出现方向性变化必须补第二抽）。
> 今天上午刚因为「把时间吻合的改动当原因」翻过一次车，这里不重犯。

## 一、这批是什么（四笔提交）

| 提交 | 日期 | 内容 |
|---|---|---|
| `891356d` | 7.07 | **引入 `prescan-plan` / `prescan-elevation` 本体** + 改写 Disciplines。⭐ 同一笔提交里记录的正是 9/9 那次 retest ⇒ **拿 9/9 的那次跑，prescan 还不存在** |
| `20749ff` | 7.09 | **triage budget**：`--min-strength 0.08 --min-line-len-px 30`、立面 `--no-cc`、`axis_summary`；同时加两条纪律（*one crop per peak band, not one per segment* · 同比例组只标定一张） |
| `421c9d3` | 7.31 | `calibration_span_candidates.json` 派生视图 + **把它定为标定起点、`crop_zoom` 降为「仅解歧义」** |
| `35f13e6` | 7.31 | `long_structural_lines.json` 派生视图（附加索引） |

起因（`20749ff` 的 ANALYSIS.md 原文）：07-08 GPT-5.4-mini 交叉测试指出 prescan 候选太多
（1f 825 个），**弱模型逐候选 crop 核验烧 token（pilot 86 次 cv 调用）**。

## 二、买到了什么（当时实测，这部分站得住）

- **候选总数 3183 → 1521（−52%）**；line_band 通道 −83%～−97%。
- **差分幸存验证**：在该档阈值下，6 张图的平面墙轴（col 9/9、row 8/8）与立面窗边（30 条）
  **零新增丢失** —— 即**收窄本身没有把正确答案过滤掉**。这条结论今天依然有效。
- 核验单位从「370/544 段」聚合到「48/68 轴」。
- 立面 cc ≈ 纯噪声（167 个里 p50 面积 ~95px² = 文本字形）⇒ `--no-cc` 是对的。
- pilot 阶段 CV 调用 **86 次 → 2–6 次**。

## 三、⭐⭐⭐ 代价：**它的账当天就记在同一份日志里，被归因到了别处**

`20749ff` 同批的 `2026-07-09_haiku_prescan_triage` 执行日志，原文写着：

> **✅ prescan 收窄本体阳性**：pilot 阶段 CV 调用 2–6 次（07-08 gpt54mini pilot=86 次）
> …「逐段 crop 核验」的成本源确实被砍掉了。

而**同一份日志的结论是**：pilot **4 轮未过审、预算用尽止损、「质量低于地板」**。

⇒ **「CV 调用塌到 2–6 次」与「质量塌到地板」是同一次跑、同一段文字里的两句话** ——
前者被当成**收益**记账，后者被归因给**隔离协议的两个缺口**：
① spawn 没有 `--directive` 槽（07-07 那条 measure-before-draw 指令传不进去）；
② 一次性 `-p` 无会话连续性（弱模型在无状态重 spawn 循环里拉不回来）。

**⛔ 那两条归因今天已经被后续实测排除：**

| 当时的解释 | 现状 | 排除依据 |
|---|---|---|
| ① 没有 directive 槽 | **早已修好** | A1/A2/C1/C2 四抽全部带 `--directive`（逐字沿用 07-07 原文），质量仍塌 |
| ② 无会话连续性 / 无打回 | **B1 专门恢复过** | 恢复 review 环 + 两轮打回，覆盖 1/6→6/6，**分数不动**（2/9） |

⇒ **07-09 记下的那个「效率收益」，和 07-07→今天的质量塌方，很可能是同一件事的两面**：
砍掉的「逐段 crop 核验成本」= 07-07 拿到 9/9 的那个工作模式本身。

## 四、六抽横向数据（撤除前的基线）

| | 07-07（**无 prescan**） | A1 | A2 | B1 | C1 | C2 |
|---|---|---|---|---|---|---|
| 平面墙 | **9/9** | 3/9 | 1/9 | 2/9 | 0/9 | 0/9 |
| **`crop_zoom`** | **55** | 0 | 0 | 0 | 2 | 1 |
| 量了几张图 | 6/6 | 1/6 | 1/6 | 6/6 | 1/6 | 1/6 |
| 是否用 prescan | **工具不存在** | 是 | 是 | 是 | 是 | 是 |

**⚠️ 上表「是否用 prescan」一行是本轮才敢填的** —— 此前报表里的 `prescan=0` 全是假数
（F-42：`process_metrics.py` 只认编号侧车，prescan 产物无编号），
**那个假数恰好把「今天与 07-07 在 prescan 轴上相同」这个假象做实了**。

## 五、已排除的其他解释（别再重测）

- **review 环 / 人工打回**（B1）—— 改覆盖不改深度。
- **cv_toolbox.md 文档文本**（C1/C2）—— 三条省 crop 纪律逐字回滚到 07-07，工作模式没变。
- **模型身份** —— 07-07 的 `llm.yaml` 写明就是 `claude-haiku-4-5-20251001`，与今天同一 ID。

⇒ **prescan 的存在本身，是唯一还没被单独测过的主变量。**
机理假说：**改文字改的是「建议」，没改「可选项集合」**；只要存在一条一次调用就能拿到
上千个候选的路，逐候选放大核验就永远不是阻力最小的路。
同族判据 [[rule-without-legal-exit-breeds-invention]] 的镜像面 ——
**给了免费的近路，纪律文字挡不住。**

## 六、撤除决定与范围（2026-08-15 用户拍板）

**撤除点 = 能力层，不是文档层**（只改文档已被 C 组证伪）：

| 位置 | 动作 | 理由 |
|---|---|---|
| `src/agent/execution/isolation_templates/run_cv_probe.py::ALLOWED_TOOLS` | 删 `prescan-plan` / `prescan-elevation` | **唯一授权表**（guard 注释明写自己那份「不是授权列表」）|
| `isolation_templates/guard.py::PROBE_TOOL_NAMES` | 同步删 | 否则报错文案还在给模型打广告 |
| `skills/intake_pipeline/0_reading/cv_toolbox.md` | 删 prescan 工具条 + 删 `long_structural_lines` 纪律条 | 后者是 prescan 派生产物，工具没了它就指向不存在的文件 |

**⛔ 不删的**：`recipes.py` 里的 prescan 实现与它的锁。
理由 = 用户口径「prescan 那批**提效**改动统一归 reading 专项」——
撤的是**读图器的可选项**，不是把这批工作销毁；日后 reading 专项要复活它，代码和差分幸存
验证结论都还在。

**连带损失（如实记）**：`calibration_span_candidates.json` 与 `long_structural_lines.json`
两个派生视图随之对读图器不可见。前者是 7.31 定的标定起点 ⇒ 标定回到 `crop_zoom` + 尺寸链，
**这正是 07-07 的形态**，与 C 组已回滚的文档纪律一致。

## 七、撤除后必须跑的验证

D 组两抽（`run_2026-08-15_reading_restart_D{1,2}_noprescan`），**唯一变量 = prescan 不可用**，
其余与 C1/C2 逐字相同。判读三岔：

- `crop_zoom` 上去且分数回来 ⇒ **杠杆坐实**，提速批的代价成立，本文件第三节从假说升为结论；
- `crop_zoom` 上去但分数不回来 ⇒ 工作模式可以换回来，但换回来不够 ⇒ 还有第四个变量；
- `crop_zoom` 仍是 0 ⇒ prescan 也不是杠杆，剩 `session_kickoff.md` 改写与硬隔离壳摩擦两项。

⛔ 在 D 组跑完之前，**不得**把「prescan 是元凶」写成结论。

---

## 八、撤除执行记录（2026-08-15）

- 改动三处：`run_cv_probe.ALLOWED_TOOLS`（唯一授权表）· `guard.PROBE_TOOL_NAMES`（报错文案）
  · `cv_toolbox.md`（prescan 工具条 + long_structural_lines 纪律条 + "Treat prescan and
  profiler outputs" 里的 prescan 字样）。
- **行为验证**（⛔ 不接受形状匹配）：
  ① `python tools/cv_probe.py prescan-plan …` → guard DENY「only tools/run_cv_probe.py may be executed」
  ② `run_cv_probe.py --tool prescan-plan` → wrapper「unsupported cv_probe tool: 'prescan-plan'」
  ③ 阴性对照 `--tool crop_zoom` → 过授权层
  ④ staging 内复验：`ALLOWED_TOOLS` 六项、`cv_toolbox.md` 内 prescan 字样 0 处。
- 受影响锁 `test_isolation.py` + `test_cv_toolbox.py` + `test_gt_discipline.py` = **246 全绿**。

### ⛔ 撤除时撞出的新缺陷 F-43

**从沙箱授权表里删掉两个工具，零测试变红** —— 全仓没有任何测试引用
`run_cv_probe.ALLOWED_TOOLS` 或 `guard.PROBE_TOOL_NAMES`。
收窄是安全方向，但同一空档意味着**放宽同样是静默的**：
给一个「防污染硬隔离」沙箱新增一个可执行工具，本该是必须动锁的改动。
⇒ 同族 [[interface-sweep-gate-vs-range-check]]：**暴露面本身就是防线，而这道防线没有守卫。**

### ⚠️ 更正：本文件第一节表格里「07-07」那一格的含义

07-07 run 的产物是被 `891356d` 带进仓的 ⇒ 跑那次时文档是父提交 `e3ec9ae`（7.06）：
Disciplines 只有三条，没有 Calibrate first / Measure before drawing / crop_zoom 强制，也没有 prescan。
⇒ **「拿 9/9 的那次，文档指令比今天任何一抽都少」** —— 这是「文本不是杠杆」的第四份独立证据，
也说明 C 组回滚的目标（891356d 的七条）本身就是**事后照着成功结果写出来的文本**，不是当时的输入。
