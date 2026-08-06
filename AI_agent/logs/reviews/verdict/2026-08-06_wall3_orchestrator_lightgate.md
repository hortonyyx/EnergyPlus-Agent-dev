# orchestrator 轻门 · 墙 3：People 字段错位

- **日期**：2026-08-06 · **裁决**：**PASS** · **施工席**：GLM-5.2（调查 + 施工同席，见 §5 说明）
- **落库**：`e58edb1` · **调查单**/**施工单**/**执行日志** 见 `request/` `execution/` 同名文件

---

## 1. 真相（orchestrator 独立复核，非采信）

真实产物 `run_2026-08-05_probe_a_legacy_snapped/4_mep/mep_output.json`：14 个 `People` **只写了 9 个字段、从第 4 槽起整体错位一格**。
`Sch_ActivityLevel` **在 `schedule_specs` 里定义了**，只是被放进 A4（IDD 那里是 `Number of People Calculation Method`）。

**⛔ 后果远不止「缺一个 schedule」**（orchestrator 用 eppy + `Energy+.idd` 逐槽实证）：

| IDD 字段 | 拿到的值 | |
|---|---|---|
| Number of People Schedule Name | `Sch_Occupancy` | ✅ |
| Number of People **Calculation Method** | `Sch_ActivityLevel` | ❌ |
| **Number of People** | `ZoneFloorAreaPerPerson` | ❌ |
| **People per Floor Area** | `10.0` | ❌ |
| **Floor Area per Person** | `0.0` | ❌ |
| Activity Level Schedule Name | `''` | ❌ ← **原来唯一被抓到的** |

⇒ **人员密度被读成「每平方米 10 人」**（本意「每人 10 m²」）。**原 gate① 在这份产物上 13 pass / 1 fail，唯一抓到的是最轻的症状。**
⇒ **追加事实（调查未报，orchestrator 从 IDD 查出）**：`ZoneFloorAreaPerPerson` **本身就不是合法值**
（`A4` 的 `\key` 只有 `People` / `People/Area` / `Area/Person`，是 OpenStudio 说法）⇒ **位置摆正也照样被 EP 拒**。

## 2. 定性（判决性对照，已复核）

| 对象 | `authoring.md` 给字段顺序范例了吗 | LLM 写对了吗 |
|---|---|---|
| `ScheduleTypeLimits` | ✅ 给了（`skills/intake_pipeline/4_mep/authoring.md:82-85`）| ✅ 检查双 PASS |
| `People` | ❌ **`grep -c "People"` = 0** | ❌ 字段全错位 |

**⇒ 给了约束的写对、没给的写错 ⇒ 病因 = 接线没给约束，不是模型能力。** 可证伪判据，非印象。
**同族第四张脸**：`people_specs` 是自由文本 `str`、字段位置零机器约束；而所有 mep 夹具都是**人手写的 IDD-correct 顺序**，
从未模拟真实 LLM 的「紧凑错位」形态 ⇒ **夹具的形态分布 ≠ 真实产出分布** ⇒ 测试全绿、真链路必崩。

## 3. 交付与 orchestrator 独立验证

| 项 | 结果 |
|---|---|
| **A** `authoring.md` 补 IDD-correct People 范例（10 槽顺序 + A4 三合法 key + A5 必填 + 点名 OpenStudio key 非法）| ✅ |
| **B ⭐** 新 gate① `mep.people_field_alignment`（`INVARIANT`）—— **抓 A4 非法枚举 = 病**，⛔ 不查 A5 空 = 症状；区分 `misplaced` vs `illegal_calc_method` | ✅ |
| **C** `mep.load_to_schedule` 措辞改为指向真实成因（`check_id`/`layer` 未动）| ✅ |
| **真实旧产物实测**（orchestrator 亲跑）| 新门 FAIL，14 offender 全 `activity_schedule_misplaced_into_calc_method_slot`，证据含 A4 实际值 + 期望枚举 + A5 `<blank>` + 整句诊断 ✅ |
| **⭐ A 的实测**（orchestrator 亲验重跑产物）| `run_2026-08-06_wall3_a_retest/4_mep/mep_output.json`：People **完整 10 槽**、`A4 = Area/Person`（合法）、`Floor Area per Person = 10.0`（密度已正确）、`A5 = Sch_ActivityLevel` 在第 10 槽 ⇒ **`check_mep` 15 pass / 3 N/A / 0 fail / blocking = 0** ✅ |
| **独立全量** | **2225 passed / 10 xfailed / 0 红**（319.66s）；基线 2223 ⇒ **净增 2 锁零回归**。与施工方数字逐字一致 |
| **独立 neuter**（orchestrator 自做，先 `git diff` 确认落地）| 把门改成空操作（`for obj in []`）⇒ **`test_people_field_misalignment_blocks_alignment_check` 恰好红**（`- fail / + pass`）、其余 4 绿 ⇒ **锁真绑** |
| **POST-RESTORE** | 恢复后 `git diff` 与提交一致（零残留）|

## 4. ⭐⭐ 墙 3 解除 ⇒ 4_mep 第一次通过

**这是本轮主线的关键节点**：0→4 段的最后一堵墙倒了，**下一步可第一次撞到 5_intakeoutput（整条链至今唯一零证据的一段）。**

## 5. 结转与注意

- ⚠️ **A 是单次证据**（一次 4_mep 重跑，模型 deepseek-v4-pro，唯一变量 = `authoring.md`）。
  施工方已如实写明噪声警示。**这正是 B 门存在的理由** —— 按 CLAUDE.md §4#2，
  不变量由确定性门兜底，A 只是让模型更容易写对，**不作为保证**。
- ⚠️ **同席位既调查又施工**（GLM 连做两单）。本单属「解法由调查定案 + orchestrator 独立复核过承重断言 + 独立 neuter + 独立全量」，
  故未另派跨家族审。**若后续 B 门要扩到其它 load 对象（Lights/ElectricEquipment），应走跨家族对抗审。**
- **登记：`people_specs` 改结构化 = 治本方向**（根除整类字段错位），动契约层 + 全部夹具，**需用户拍板，未排期**。
- **⭐ 治理教训（新，与「夹具必须钉到契约单一来源」并列）**：
  **夹具不仅要用对字段名，还要覆盖真实产出的形态分布。**
  本例中夹具全是人手写的 IDD-correct 顺序 —— 形态「正确」，但真实 LLM 从不产出这种形态。
  ⇒ **判别问法扩充：「这个夹具的形状，真实生产方真的会产出吗？」**
