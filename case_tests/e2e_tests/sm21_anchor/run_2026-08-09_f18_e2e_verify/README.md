# run_2026-08-09_f18_e2e_verify — 这个 run 是测什么的

> **性质 = 非正式的工程验证跑，⛔ 不是成绩跑。**
> 用户 2026-08-10 定：「这种非正式的都不用记，写明是测什么就行了」
> ⇒ **刻意不走 `flow --record` 官方记账**，因此没有 `_run/baseline.json`、没有 `report/REPORT.md`。
> 引用本 run 时**不得**把它当作任何识图 / 端到端成绩，它只回答「这条链今天通不通」。

## 测什么

验证三个内核／门缺陷的修法，是否让一份 **v3 产物**真的能走完整条链：

| 缺陷 | 症状 | 本 run 要验证的 |
|---|---|---|
| **F-18** | 窗宿主自洽门用浮点精确相等比两条算路，1–4 ULP 偏差 ⇒ 判真实产物「被篡改」并裸抛终止 flow | 1_correction 能否走完并出 accepted 产物 |
| **F-19** | `kernel.window_parent_binding` 在真实产物上 15/15 恒红，而几何是对的 | 2_modelling 能否过 gate① |
| **F-20** | `validate_case` 重建几何时不传窗宿主凭证 ⇒ v3 产物 digest 恒为 None ⇒ 几何确认门**人和机器都签不出来** | 几何确认门能否签发、之后能否推到 EnergyPlus |

## 输入（⚠️ 识图本轮一次都没跑）

- `0_reading/` = **07-07 那份已知满分的 sm21 识图产物逐字节复制**
  （链：`run_2026-07-07_haiku_cv_retest` → 08-08 run → 08-09 f17 run → 本 run，逐跳 `diff -rq` 校验过）。
- ⇒ **本 run 不产生任何识图成绩**；那份产物本身是在「停下等人审阅」的循环里拿到的，非无监督基线
  （见 CLAUDE.md §1.5#7 已排查违规点①）。这也是本 run 不走官方记账的原因之一 ——
  记账门要求声明识图 lane，而本 run 没有可诚实声明的 lane。

## 怎么跑的（⛔ 不是一口气跑完的）

**分三次、跨两天**，每次都是撞墙 → 修墙 → 续跑：

| 时间 | 跑的段 | 结局 |
|---|---|---|
| 2026-08-09 12:33 | 0_reading → 1_correction（**唯一一次真跑 LLM 的 correction**）→ 2_modelling att.001 | 🔴 exit 20，F-19 判 15 窗全错 |
| 2026-08-10 05:49 | 2_modelling att.002 → 3_split_pairing → 出 3D 查看器 | 🔴 exit 20，F-20「no consistent checkpoint」 |
| 2026-08-10 16:59 | 几何确认门签发 → 4_mep → 5_intakeoutput → 下游 9 subagent → EnergyPlus | ✅ 到底 |

**⚠️ 由此产生的口径限制（引用本 run 时必须一起说）**：
1_correction 是在 **08-09 的老代码**上跑的，F-19 / F-20 两个修法在那之后才落库。
⇒ **「用今天的代码从头连续跑一遍还通不通」从未被验证过。**
要拿这个证据，需另起一个全新 run 从 1_correction 跑到底（识图仍可复用）。

## 结果

**EnergyPlus Completed Successfully — 18 Warning; 0 Severe Errors**（5.39 秒）。
18 条警告全部非几何：14 条每区一条的 People 内热提示 + 4 条天气文件/时间步默认项。

几何忠实度证据（⛔「EP 通过 ≠ 几何对」，所以不能只报上面那行）：

- 内核冻结 vs 实际 IDF **逐类计数一致**：`BuildingSurface:Detailed` 100 / `FenestrationSurface:Detailed` 15 / `Zone` 14；
- `EP/output_coordinate_audit.json` 的 `offenders` 与 `zone_normalizations` **均为空**；
- `validate_case` 全量 **176 项检查、`blocked: False`**；
- **2_modelling / 4_mep / 5_intakeoutput / 下游 / 坐标审计 五段零非 PASS**；
- 非 PASS 共 7 条，**全部在本轮开跑前就已存在**（0_reading 六张图各一条
  `dimension_chain_closure` + 1_correction 一条 `evidence_debt_coverage`），exploratory 档不阻断
  ⇒ **本轮推的这一段没有引入新缺陷**。

**几何确认门**：由用户 2026-08-10 看过 `manual_review/geometry_viewer.html` 后当面确认，
orchestrator 代执行签发，digest `3409f90b…`（与开跑前只读预检算出的逐字一致）。
2_modelling 两次 attempt 的 `output.json` **逐字节相同**（`9f1fe95e…`）——
attempt 001 的 FAIL 是 F-19 那道门的缺陷，**几何一个坐标都没动**。

## 登记（本 run 暴露、未修）

1. **`1_correction/attempts/002` 不是重画**：4_mep 前的朝向解析步骤把原本为空的 `north_axis`
   按策略补成**明确标注 `provenance: assumed` 的 0°**（`method: prior_fill_default_zero_v1`、
   `evidence_candidate_count: 0`、带审计侧车）。模型原始 draw 绑定哈希逐字节未变，
   几何 digest 前后一致。
2. **⚠️ 账本漂移**：权威 `_run/run_manifest.json` 记 `1_correction accepted_attempt: 2`，
   而 `_run/orchestration_state.json` 仍写 `attempts=1, accepted=1` ——
   **同一事实两处声明、其中一处漂了**（项目「轴 B」族）。**未修，已登记。**
3. **尺寸基准开关未实现**：本 run 的框是「外圈外皮 + 内墙轴线」混合框
   （实测 `[0.12,14.88]×[0.12,7.88]` → `[0,15]×[0,8]`，**内部分隔线 5.0/10.0/3.0 一条没动**），
   与 gt 同款、无错配；但 2026-07-08 定的 `zone_frame: axis | exterior` 出模开关**至今一行未实现**，
   今天是硬编码走 exterior 档，而那份文档写的默认倾向是 axis。按外皮算全楼 120 m²、
   按轴线算 114.5 m²，**差约 4.8%**，会进到负荷结果里。**未修，已登记。**
