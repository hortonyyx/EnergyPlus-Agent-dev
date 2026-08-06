# 施工单 · 墙 3：People 字段错位 → 补范例 + 补门 + 改措辞

> **这是「施工单」**（解法已由调查定案）。调查全档：
> [`execution/2026-08-06_wall3_mep_schedule_investigation_glm.md`](../execution/2026-08-06_wall3_mep_schedule_investigation_glm.md)（你自己写的）。
> orchestrator 已**独立复核**该调查的全部承重断言，并**追加两条它没报的事实**（见 §2）。

- **日期**：2026-08-06 · **席位**：GLM-5.2，主工作树 · **基点**：`6.15_ValidationArchM0toM4` @ `b379cd8`

## 0. 开工自检（不对就停）

```bash
git log --oneline -1     # 期望 b379cd8
git status --short       # 期望：3 个 case_tests 未跟踪目录 + 3 个 AI_agent 未跟踪 md（本单相关，可提交）
pwd                      # 期望 /workspaces/EnergyPlus-Agent-dev
```
⛔ **绝不 `git add -A`**。

## 1. 结论回顾（已核实，作为施工前提）

真实产物 `run_2026-08-05_probe_a_legacy_snapped/4_mep/mep_output.json` 里，14 个 `People` 对象
**只写了 9 个字段，且从第 4 槽起整体错位一格**。`Sch_ActivityLevel` **在 `schedule_specs` 里定义了**，
只是被放进了第 4 槽（IDD 那里是 `Number of People Calculation Method`），
真正的第 10 槽 `Activity Level Schedule Name`（`A5`，**`\required-field`**）为空。

## 2. ⭐ orchestrator 追加的两条事实（你的调查没报，施工必须覆盖）

1. **错位的后果远不止"缺一个 schedule"** —— eppy 按 IDD 位置解析的实际结果：

   | IDD 字段 | 拿到的值 | |
   |---|---|---|
   | Number of People Schedule Name | `Sch_Occupancy` | ✅ |
   | Number of People **Calculation Method** | `Sch_ActivityLevel` | ❌ |
   | **Number of People** | `ZoneFloorAreaPerPerson` | ❌ |
   | **People per Floor Area** | `10.0` | ❌ |
   | **Floor Area per Person** | `0.0` | ❌ |
   | Activity Level Schedule Name | `''` | ❌ ← 唯一被现有检查抓到的 |

   ⇒ **人员密度被读成「每平方米 10 人」**（LLM 想表达的是「每人 10 m²」）。
   ⇒ **gate① 在这份产物上 13 条 pass / 1 条 fail，唯一抓到的是最轻的症状。**

2. **⭐ 方法名本身也是非法值** —— IDD `A4` 的合法 key 只有 **`People` / `People/Area` / `Area/Person`**
   （`Energy+.idd` People 段 `\key` 三行）。LLM 写的 `ZoneFloorAreaPerPerson` **是 OpenStudio 说法、不是 EnergyPlus IDD 值**
   ⇒ **就算把位置摆正，EP 照样拒。** §3 的 A 必须同时覆盖「顺序」与「合法取值」。

## 3. 施工内容（三件）

### A · 给 `skills/intake_pipeline/4_mep/authoring.md` 补 People 范例
现状 `grep -c "People"` = **0**（整份文档零次提及）。仿该文件 `:82-85` `ScheduleTypeLimits` 那段的写法，
给一个 **IDD-correct 的完整 People 范例**，必须同时体现：**十个槽位的顺序** + **`A4` 的三个合法 key** +
**`A5` 是必填**。⛔ 不要顺手改该文件其它章节。

### B · ⭐ 补一道 gate① 门（本单的承重件）
**要求的行为**（机制你自己定，我不指定实现）：
- 在**上面那份真实产物**上必须 **FAIL**，且**指明是字段错位**，⛔ 不是笼统的 "missing or undefined"；
- 必须能**区分两种情况**：①字段错位 ②字段位置对但 schedule 名真的没定义 —— 两格都要有实测；
- ⛔ **不许只检查「第 10 槽非空」** —— 现有检查已经在做这件事，那是症状不是病。

> **为什么必须有这道门**：CLAUDE.md §4#2 —— **强制约束别交给 LLM 记得，关键不变量一律确定性门强制、不靠 prompt**。
> 只做 A 就是把不变量交给提示词，本项目已因此撞过多次。

### C · 改报错措辞
现有 `mep.load_to_schedule` 的 `"missing or undefined"` 会把排查引向「schedule 没定义」，
**而 schedule 定义得好好的** ⇒ 措辞需指向真实成因。⛔ 不要改它的 `check_id` 与 `layer`。

## 4. 验收

| # | 条件 |
|---|---|
| **1** | B 的门在**真实旧产物**上 FAIL 且指明错位（离线可验，**零 LLM 成本**）|
| **2** | B 的两格区分实测（错位 / 名字真没定义），断言落在**具体 check-id 行**上。⛔ 不许断言「非 None」「总数变了」|
| **3** | **neuter 两向**，且**先 `git diff` 确认改动真的落下去了**再跑（orchestrator 犯过「正则命中 0 处却拿到 22 绿」）|
| **4** | 全仓 `pytest -n auto`（**不加 `-m`**），基线 **2223 绿 / 10 xfail / 0 红**，要求净增锁零回归。新锁**不许依赖 gitignored 文件**（F-8）|
| **5** | **⚠️ A 的实测**：重跑一次 4_mep（**仅这一段**，`exploratory` 档），看 LLM 是否写出 IDD-correct 的 People。**如实报告结果，有效无效都要写。** |

> **⭐ 关于验收 5 的合法退出口（重要）**：A 属于「靠文档说服模型」，**本项目的历史是这类修法不可靠**。
> **⛔ 如果实测显示 A 无效，不要反复改 prompt 去凑** —— 停下上报，那说明修法要转向 B 那道门兜底
> 或转结构化（`people_specs` 改结构化 = 治本方向，**本单不做**）。
> **「A 没用」是一个完全合格的交付结论，记功不记过。**

## 5. 边界

⛔ 不改 `people_specs` 的类型（结构化是治本方向，需用户拍板，本单不做）·
⛔ 不碰 `case_tests/` 未跟踪目录 · ⛔ 不 push · ✅ 一次性脚本放 `/tmp`

## 6. 交付

代码 + 锁 + 执行日志 `execution/2026-08-06_wall3_fix_glm.md`（含验收 1–5 的**实际命令与实际输出**、neuter 的 `git diff` 证据）。
**自己 commit**（message 仿 `08.06_wall3_people_field_order`，body 含 ①改动 ②为何此刻 ③影响），**不要 push**。
可一并 `git add` 本单与调查单两份 md。

## 7. 停下上报（**记功不记过**）

本轮至今 **7 次「停下上报」，7 次都是派工方的题错了**。本单事实与你看到的不符 ·
验收条件做不到 · 你认为修法方向有问题 ⇒ **立刻停下上报**。⛔ 硬凑出一把假锁是本项目最贵的错误。
