# 派工单（GLM 席位）· 探针 A —— 把 6 月跑通过 EP 的**内核后产物**灌进今天的 2→5

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **席位**：GLM-5.2，**主工作树**
- **用户拍板**：两条探针都跑（B 已由 orchestrator 跑完，**通过**）；本单 = 探针 A。

> **⚠️ 派工方自述**：本轮我已出错八次（含刚被你如实登记的「调用点枚举不全」那次）。
> **本单里凡是与代码实情不符的地方，一律停下上报，不要硬做。** 在本项目这是记功不是记过。

---

## 0. 这条探针要回答什么

**用户的话**：「能不能直接拿之前端到端跑通的中间产物直接来试呢？反正是探工程问题。」

**现状**：真链路今天卡在 **1_correction**（F-9，几何内核里的窗户归属拒收），
⇒ **2_modelling / 3_split_pairing / 4_mep / 5_intakeoutput 今天一律零证据** ——
不是「验过没问题」，是**根本没测到**。

**已知的另一半**（orchestrator 刚跑完的探针 B）：
拿 6 月那份 `run_2026-06-16_opus_e2e/5_intakeoutput/intake_output.json`
灌进今天的下游（9 subagent → IDF → EnergyPlus）⇒
**`EnergyPlus Completed Successfully-- 6 Warning; 0 Severe Errors`，`eplusout.err` 里 Severe 0 行。**
产物落 `case_tests/e2e_tests/sm21_anchor/probe_b_2026-08-05_legacy_intake/`。
**⇒ 下游半边今天是好的。**

**⇒ 本单 = 补上中间那段唯一的空白：2_modelling → 5_intakeoutput。**

## 1. 素材（orchestrator 已核实，不必重找）

来源 = `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/`
（6 月真跑到 EP 的 2 层 sm21 golden run，`EP/EP_run/eplusout.end` 在）。

| 文件 | 作用 | 已核 |
|---|---|---|
| `1_correction/correction_geometry_snapped.json` | **确定性内核之后**的几何 = 2_modelling 真正消费的那份 | ✅ 存在 |
| `1_correction/correction_geometry.json` | 内核**之前**的 LLM 原始抽签 | ⛔ **不要用这份** |

**⚠️ 契约档位**：老件是 **schema v1 / `rectangular` 档**
（顶层 `floors/footprint_x/footprint_y`，`cells` 嵌在 floors 里，windows 带 `floor/facade/span/z/room`，
**无 `schema_version`、无 `provenance`**）。orchestrator 已比对过 `correction_target("rectangular")` 的
`CorrectedGeometry`，**结构逐项对得上**。

**⇒ 本单一律用 `--capability-profile rectangular`。**
**⚠️ 这条探针查的是「2–5 段本身坏没坏」，⛔ 查不到 v3 专有接线（窗源绑定 / facade_segments / provenance）的问题** ——
报告里必须写清这条局限，**不得**把「探针 A 绿」说成「sm21 那条路通了」。

## 2. 要做的

1. **新建一个 run 目录**（建议 `run_2026-08-05_probe_a_legacy_snapped`），
   **⛔ 绝对不许改动或覆盖 `run_2026-06-16_opus_e2e/`**（那是签过字的 golden 基线）。
2. **把老件播种成 1_correction 的 accepted attempt**：
   - 用 `StageRunner.record(...)` + `manifest.save(...)` 走**真实归档入口**，
     **⛔ 不许手搓 `attempts/NNN/output.json` 和 manifest 条目**（手搓出来的东西证明不了真实入口能吃它）。
   - 0_reading 也需要一个 accepted attempt 才能推进 ⇒ 用同一个 run 的 `0_reading/*_view.json`
     （老件那份识图产物就在 `run_2026-06-16_opus_e2e/0_reading/`）。
     **如果 0_reading 的 gate① 在今天的档位下不放行，⛔ 不要放宽 gate、停下上报** —— 那本身就是发现。
   - 播种脚本落 `/tmp`，**⛔ 不进仓库**（它是一次性工具，不是产品代码）。
3. **跑**：`flow sm21_anchor <run> --from 2_modelling --to 5_intakeoutput --judge off`
   · `--run-profile exploratory` · `--capability-profile rectangular`
   （用户 08-05 定：「现在你确保不会拦端到端就行」⇒ 一律 exploratory）。
4. **撞到墙就逐条记**，**⛔ 不要修** —— 本单是**探**，不是修。
   每堵墙记：崩在哪个文件:行 · 异常类型与消息 · **它是「老件形态问题」还是「今天的代码问题」**
   （判据同 F-5/F-7：消费侧要的形态，生产侧当年产得出来吗；今天的代码是不是加了当年没有的要求）。
5. 若一路通到 `5_intakeoutput`：**把产出的 `intake_output.json` 与 6 月那份逐字段 diff**，
   报告差异（这能直接看出 2–5 段今天有没有语义漂移）。

## 3. ⛔ 明确不做

- ⛔ 不碰 1_correction 的 LLM 抽签（本探针的全部意义就是绕开它）
- ⛔ 不碰 F-9（`resolve_window_hosts` 那条，另有排期）
- ⛔ 不修任何撞到的墙（只记录）
- ⛔ 不放宽任何 gate 来「让它过去」—— 被拦住本身就是本单要的信息
- ⛔ 不动 `case_tests/test_baseline/gt/`（gt 铁律）

## 4. 交回

报告落 `AI_agent/logs/reviews/execution/2026-08-05_probe_a_legacy_snapped_glm.md`，含：

- **走到哪一段**（这是本单的头号产出）
- 每堵墙的逐条记录（文件:行 / 异常 / 「老件形态」还是「今天代码」的判定 + 证据）
- 若通到底：`intake_output.json` 与 6 月那份的逐字段 diff
- **§1 那条局限的明文声明**（v1 档，查不到 v3 专有接线）
- 播种用的那段脚本原文（贴进报告，便于复现；**文件本身留 /tmp 不进仓库**）

**提交**：只提交这份报告 + 新 run 目录里**该进 git 的产物**（跑测中间产物按现有 `.gitignore` 规矩走）。
**⛔ 逐文件 `git add`，不许 `git add -A`。⛔ 不要 push。**
**做完一件存一件**（容器 OOM 会带走会话）。
