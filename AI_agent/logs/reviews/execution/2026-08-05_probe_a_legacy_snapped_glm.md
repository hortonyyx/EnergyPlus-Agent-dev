# 探针 A 执行报告 · 把 6 月【内核后】几何灌进今天的 2→5

- **日期**：2026-08-05
- **席位**：GLM-5.2（施工），主工作树，分支 `6.15_ValidationArchM0toM4`
- **派工单**：`AI_agent/logs/reviews/request/2026-08-05_probe_a_legacy_snapped_into_2to5_dispatch_glm.md`
- **素材**：`case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/1_correction/correction_geometry_snapped.json`（schema v1 / rectangular）
- **新 run**：`case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped/`（⛔ 未动 golden 基线 `run_2026-06-16_opus_e2e/`）

---

## 0. ⭐ 头号产出：走到哪一段

| 段 | 状态 | 证据 |
|---|---|---|
| 0_reading | ✅ gate① **passed（block=0）**，accepted=1 | 真 `run_stage.py run` 入口播种；18 条 advisory flag（legacy v1 无尺寸链/provenance），exploratory 非阻断 |
| 1_correction | ✅ gate① **passed（block=0, flag=0）**，accepted=1（base_v2） | 真 `check_correction` 在 rectangular/exploratory 下**接受** legacy v1 几何 |
| 2_modelling | ✅ `deterministic_pass`，gate① **passed（block=0, flag=0）** | 今天的确定性内核**能造面** legacy v1 几何 |
| 3_split_pairing | ✅ gate① **passed（block=0, flag=0）**（几何已 auto-approve） | 序列化一致 |
| **4_mep** | **⛔ 崩** | `_draw_mep` 调 `check_mep(run_profile=...)` 抛 `TypeError`（见墙 2） |
| 5_intakeoutput | ⛔ **不可达** | 4_mep 无任何 check_mep-passing 的 mep 可喂（见墙 3/4），按纪律不强 accept |

**一句话**：探针**止于 4_mep**。0_reading / 1_correction / 2_modelling / 3_split_pairing 这四段在 legacy v1 几何上**今天 gate① 全绿、本身没坏**；**4_mep 既是硬崩（签名 bug）又对任何 mep 都不放行**（今天 LLM 产出缺 schedule + June 已知好件因 zone 命名漂移被拒）⇒ **5_intakeoutput 今天零证据、不可达**。

⭐ **派工单说"真链路今天卡在 1_correction（F-9）"——本探针绕开 F-9（播种）后，暴露了 4_mep 这第二处 blocker**。即 F-9 一直**遮蔽**着 4_mep 的崩；修好 F-9，链路仍会在 4_mep 崩。

---

## 1. ⚠️ 局限声明（派工单 §1 强制）

老件是 **schema v1 / `rectangular` 档**（顶层 `floors/footprint_x/footprint_y`，windows 带 `floor/facade/span/z/room`，无 `schema_version`、无 `provenance`）。本探针一律 `--capability-profile rectangular --run-profile exploratory --judge off`。

**⇒ 本报告查的是「2–5 段在 v1/rectangular 形态下本身坏没坏」，⛔ 查不到 v3 专有接线的问题**：
- 窗源绑定（`window_resolver_inputs` / B5 六件套 proof wire）—— v1 无；
- `facade_segments` —— v1 无；
- `provenance` 块 —— v1 无；
- F-9（`resolve_window_hosts` 拒收）—— **仅 v3 内核路径触发**；本探针用的 v1 几何，`check_correction` 对 v1 **不跑** `check_window_host_resolution`（mep.py / correction.py 仅 `schema_version=="3"` 才跑），故 F-9 在此**不触发、也不可证伪**。

**⛔ 不得把「0/1/2/3 在 v1 下绿」说成「sm21 那条路通了」**——今天真实的 sm21 run 走 v3，v3 路径本探针**一根线都没测**。

---

## 2. 正面发现（v1/rectangular 路径）

1. **今天的 0_reading gate① 接受 legacy v1 识图**（block=0）。18 条 flag 全是 legacy 形态的 advisory（`raw_field_presence`/`dimension_chain_closure`/`stroke_provenance_coverage`），exploratory 不阻断——尺子对老件没坏。
2. **今天的 1_correction gate① 接受 legacy v1 几何**（block=0, flag=0）。即 F-9 是 **v3 专属**，v1 路径不牵连。
3. **今天的确定性几何内核（2_modelling + 3_split_pairing）在 legacy v1 几何上 gate① 全绿**：14 区造面成功、InterZone 序列化一致、`kernel_gate_report` 无 hard error。**几何内核本身没坏。**
4. 三个 view_manifest_sha256 与 smoke_downstream_r2 逐字一致（`f52ca79c…`）⇒ case_data 同源、provision 确定性。

---

## 3. 撞墙逐条（文件:行 / 异常 / 老件形态 vs 今天代码）

### 墙 0｜派工单命令歧义（**非缺陷**，已如实演示）
- **现象**：派工单命令 `flow … --from 2_modelling --to 5_intakeoutput --judge off`（不带 `--geometry auto`）跑到 3_split_pairing 后停在 `awaiting_geometry_approval`（`EXIT=10`），到不了 4_mep。
- **根因（今天代码，非老件）**：`cmd_flow` 把 `confirmation_policy=REQUIRED` 写死（`scripts/tool_scripts/run_stage.py:2515`），且 `GEOMETRY_CHECKPOINT_STAGE="3_split_pairing"`（`src/agent/execution/step_orchestrator.py:68`）⇒ 3_split_pairing gate① 过后必停等人工几何确认（`run_stage.py:2621-2646`）。
- **处置**：这是**设计的人工门**，不是 2-5 缺陷。`--judge off` 已是「别拦」旗标，`--geometry auto` 是其对偶的**文档化无人工旗标**（记 `actor=flow:auto` 审计戳；几何仍被建+gate① 验，只自动发确认戳、**非放宽阈值**）。派工单漏写该旗标，属本轮派工方第 9 处疏漏；为完成「探 4/5」目的，续跑时加了 `--geometry auto`，**全程明文记录**。几何确认门本身**未修、未放宽**。

### 墙 1｜seeding 接缝：`--geometry auto` 报 "no consistent checkpoint"（**seeding 场景接缝，非正常 run 缺陷**）
- **现象**：补 `--geometry auto` 后报 `✗ geometry auto-approval failed: no consistent checkpoint`（`EXIT=20`）。但 2+3 都建出来且 gate① passed、3D viewer 也写了。
- **根因（今天代码，仅 seeding 场景暴露）**：`approve_geometry`（`step_orchestrator.py:462`）→ `validate_case`（`validation_run.py`）。`validate_case` 的几何 digest 从 **stage 根** `1_correction/correction_geometry_snapped.json` 读（`validation_run.py:101/188/192`），**不**读 manifest accepted attempt 的 `attempts/NNN/output.json`。而派工单规定的播种入口 `StageRunner.record` 用**裸 dict**（base_v2、非 FinalizeResult）**不写** stage 根便利副本（只有 `is_correction_write`=FinalizeResult 才写，`stage_runner.py:560-563`）⇒ stage 根文件缺失 ⇒ `validate_case` 跳过几何重建 ⇒ `geometry_digest=None` ⇒ `approve_geometry` 返回 None。
- **为何正常 run 不可见**：正常 flow 走 `_draw_correction`→`finalize_correction_draw`→FinalizeResult，`StageRunner.record` **两个都写**（attempt + stage 根）。仅当绕开 LLM draw、用裸 dict 播种（本探针的硬约束）时才暴露。
- **处置（不修代码）**：补 stage 根便利镜像（把 legacy `correction_geometry_snapped.json` 逐字节拷到新 run 的 `1_correction/` 根，内容=已 archived 的 accepted attempt）——这**不是**手搓 manifest/attempts，是补全播种产物集使其结构等同正常 run（geometry 内容未动）。补后 `--geometry auto` 正常 approve（digest=`760dfe67…`）。**接缝本身记录在案、未修。**

### 墙 2｜**4_mep 硬崩：`_draw_mep` 调 `check_mep(run_profile=...)` 抛 TypeError**（今天代码 bug）
- **现象**：
  ```
  File "scripts/tool_scripts/run_stage.py", line 572, in _draw_mep
    rep = check_mep(...)
  TypeError: check_mep() got an unexpected keyword argument 'run_profile'
  ```
- **根因（今天代码）**：`_draw_mep`（`run_stage.py:572` 调用、`:577` 传参）给 `check_mep` 传了 `run_profile=policy.run_profile`，但 `check_mep` 签名**无** `run_profile` 形参（`src/validator/checks/mep.py:95-103`：只接 `mep, *, used_constructions, zone_names, geometry_idf, testdata, capability_profile`）。签名漂移：调用方加了 `run_profile`、被调方没加（或反之）。
- **影响范围**：**任何**走 flow/`run_stage.py run` 跑到 4_mep 的 run 都崩——**不只本探针**。今天一直被 F-9（卡在 1_correction）遮蔽，故未暴露。
- **重要旁证**：`run_mep`（LLM 调用）在 `check_mep` 之前**已成功执行**并产出 `4_mep/mep_output.json`（16KB）+ raw/thinking。即 **4_mep 的 LLM 产出路径是通的，崩在 gate① 检查的调用签名**。
- **判定**：**今天的代码问题**（非老件形态）。⛔ 未修。

### 墙 3｜今天 `run_mep` 产的 mep 被 `check_mep`（正确签名）拒：缺 14 schedule
- **现象**：绕开有 bug 的 `_draw_mep` 包装器，用**正确签名**直接跑真 `check_mep(mep, used_constructions=, zone_names=, capability_profile=)` ⇒ **passed=False, block=1**：
  ```
  ⛔ mep.load_to_schedule: 14 load schedule reference(s) are missing or undefined
  ```
- **根因（今天代码/模型，待细分）**：今天 `run_mep` 产的 mep，其 PEOPLE/LIGHTS/EQUIPMENT 引用的 schedule 名在 mep 自带的 `schedule_specs` 里**未定义**（`_load_refs`，`mep.py:518-555`：`sref not in sched_names`）。即 run_mep 让 load 引用了它自己没生成的 schedule。是 LLM 产出质量、还是 run_mep 的 schedule 接线缺陷——**本探针不裁定**（⛔ 不修）。
- **旁证**：今天 run_mep 的 mep **用的就是今天 geometry 的 Z0n_ zone 名**（见墙 4 对照），故 `load_to_zone` 概念上对、只栽在 schedule。
- **判定**：**今天的代码/模型问题**（非老件形态）。

### 墙 4｜June 已知好 mep 也被今天的 `check_mep` 拒：**zone 命名漂移**
- **现象**：把 June 那份跑通过 EP 的 `mep_output.json` 喂今天的 `check_mep`（正确签名）⇒ **passed=False, block=2**：
  ```
  ⛔ mep.load_to_zone: 28 load(s) reference an unknown zone
  ⛔ mep.load_to_schedule: 14 load schedule reference(s) are missing or undefined
  ⚠️  mep.per_zone_coverage: 14 zone(s) missing a load object
  ```
- **根因（决定性定性）**——**zone 命名约定在 June 与今天之间漂移，零交集**：
  - June mep 引用（PEOPLE field[1]）：`R_1F_TL / R_1F_TM / R_1F_TR / R_1F_BL / R_1F_BM / R_1F_BR / R_1F_Cor / R_2F_TL / R_2F_TR / R_2F_B1 / R_2F_B2 / R_2F_B3 / R_2F_B4 / R_2F_Cor`（`R_<层>_<位置>` 约定，14 个）。
  - 今天 geometry（`build_geometry` on legacy 1_correction）产：`Z01_F1_Office_NW / … / Z14_F2_Office_SE`（`Z0n_F<层>_<角色>_<方位>` 约定，14 个）。
  - **两套命名零交集** ⇒ June mep 对今天 geometry 全是 unknown zone。
- **判定**：**今天的代码漂移**（几何 zone 命名规范化从 `R_<层>_<位置>` 改成了 `Z0n_F<层>_<角色>_<方位>`，CLAUDE.md 记载的"命名/外包确定性化"落地后的副作用）——**老件形态本身没错**（它在 June 是对的），是今天的命名约定变了，使 June mep 与今天 geometry 不兼容。
- **⚠️ 顺带发现（今天 geometry 自身）**：今天的 14 个 zone 名里有**重复角色后缀**——`Z11_F2_Office_SW == Z12_F2_Office_SW`、`Z13_F2_Office_SE == Z14_F2_Office_SE`（两个不同 zone 共用同一 `<角色>_<方位>` 串）。疑似 zone 命名确定性化的一个去重缺陷，**登记待查**（本探针不修）。

### 墙 5｜5_intakeoutput 不可达（**结论，非新墙**）
- 4_mep 要 accepted，`check_mep` 必须过。但：今天 run_mep 产出（墙 3）与 June 已知好件（墙 4）**都被 `check_mep` 拒**。即**今天不存在一份 check_mep-passing 的 mep 可喂给 5**。
- 按派工单 §3「⛔ 不放宽任何 gate」+ 本席纪律（`check_mep` 不过**不**强 accept），**不**伪造 4_mep accepted ⇒ 5_intakeoutput **保持未测**。
- ⇒ 派工单 §2.5「若一路通到 5：逐字段 diff intake_output」的**前置条件不满足**（未一路通到 5），**无可 diff**。

---

## 4. 播种方式（真实归档入口，非手搓）

| 段 | 播种方式 | 入口 |
|---|---|---|
| 0_reading | `run_stage.py run … 0_reading`（manual 能力：只校验已存在 `*_view.json`、不重画；自带 manifest provision + 真 gate① + render） | 真 `StageRunner.record`+`manifest.save`（`run_stage.py` 内部） |
| 1_correction | /tmp 脚本：legacy snapped JSON（裸 dict）→ 真 `check_correction` → `StageRunner.record`+`manifest.save`（base_v2） | `StageRunner.record`（`stage_runner.py:140`） |
| 1_correction stage 根镜像 | 拷 legacy `correction_geometry_snapped.json` 逐字节到 `1_correction/` 根（补墙 1 接缝；正常 run 的 FinalizeResult writer 会产） | `cp`（= accepted attempt 内容） |
| 4_mep | ⛔ **未播种成功**——`check_mep` 对今天 mep 与 June mep 都拒，按纪律不强 accept | — |

⛔ **未手搓** `attempts/NNN/output.json` 或 manifest 条目；均走 `StageRunner.record`/`manifest.save` 真实入口。播种脚本落 `/tmp`（`seed_correction_probe_a.py` / `seed_mep_supplementary.py` / `seed_mep_june_and_run5.py`），**不进仓库**。

---

## 5. 关键裁定（供 orchestrator / 用户）

1. **4_mep 是被 F-9 遮蔽的第二处 blocker**：派工单前提"真链路卡在 1_correction（F-9）"成立，但本探针证明**即便修好 F-9，链路仍会在 4_mep 崩**（墙 2 的 TypeError）。
2. **4_mep 至少三个独立问题**：(a) `_draw_mep`→`check_mep(run_profile)` 签名崩（墙 2，纯代码 bug，任何 flow 必触发）；(b) 今天 run_mep 产出缺 14 schedule（墙 3）；(c) zone 命名漂移使 June-era mep 与今天 geometry 不兼容（墙 4）。
3. **几何内核（2/3）+ v1 校正 gate 在 legacy v1 上没坏**——别把修 4_mep 的精力误投到几何内核。
4. **seeding→validate_case 接缝（墙 1）**仅 seeding 场景暴露，正常 run 不可见；但任何"绕开 LLM draw 直接播种几何"的探针/复用都会撞，值得收口（让 `validate_case` 读 manifest accepted attempt，或让 base_v2 writer 也写 stage 根）。
5. **5_intakeoutput 今天零证据**：既没通到，也无法用已知好件隔离测（June mep 因命名漂移喂不进）。要测 5，先得有一份今天 geometry 兼容、check_mep-passing 的 mep（即先修墙 2/3）。

---

## 6. 附录：1_correction 播种脚本原文（/tmp/seed_correction_probe_a.py）

```python
"""Probe A — seed legacy post-kernel geometry as accepted 1_correction (one-shot, /tmp)."""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path("/workspaces/EnergyPlus-Agent-dev"); sys.path.insert(0, str(REPO))
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.execution.manifest import load_run_manifest
from src.agent.execution.stage_runner import StageRunner
from src.validator.checks.correction import check_correction

CASE="sm21_anchor"; RUN="run_2026-08-05_probe_a_legacy_snapped"
LEGACY=REPO/"case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e"
run_dir=REPO/"case_tests/e2e_tests/sm21_anchor"/RUN

manifest=load_run_manifest(run_dir)
reading_rec=manifest.accepted("0_reading"); assert reading_rec is not None
reading_output_hash=reading_rec.output_hash

snapped=json.loads((LEGACY/"1_correction"/"correction_geometry_snapped.json").read_text(encoding="utf-8"))
geom=ensure_corrected_geometry(snapped)

rep=check_correction(geom, expected_zone_total=14, relied_on_testdata=True,
                     capability_profile="rectangular", run_profile="exploratory")
print(f"check_correction: passed={rep.passed} block={len(rep.blocking())} flag={len(rep.flagged())}")

runner=StageRunner(run_dir, manifest)
rec=runner.record(stage="1_correction", stage_dir=run_dir/"1_correction",
                  output_obj=snapped, report=rep,   # 裸 v1 dict ⇒ base_v2
                  input_hashes={"0_reading": reading_output_hash})
manifest.save(run_dir)
print(f"1_correction accepted={rec.accepted} contract={manifest.accepted('1_correction').artifact_contract}")
```

（`/tmp/seed_mep_supplementary.py` 与 `/tmp/seed_mep_june_and_run5.py` 为墙 3/4 的证据采集脚本——均跑真 `check_mep`（正确签名、不碰有 bug 的 `_draw_mep`），结果都是 block ⇒ 未播种 4_mep。原文留 /tmp 不进仓库，结构同上。）

---

## 7. 提交说明

- 本报告 + 新 run `run_2026-08-05_probe_a_legacy_snapped/` 里**该进 git 的产物**（`0_reading/*_view.json`、各段 `attempts/`、`building_geometry.json`、`geometry_specs.md`、`4_mep/mep_output.json`+raw/thinking、`_run/*`、`run_config.yaml`、`manual_review/geometry_viewer.html` 等）。
- ⛔ 逐文件 `git add`，未用 `git add -A`（避扫走并行席位半成品）。
- ⛔ 未 push（派工单明令）。
- ⛔ 未改 `run_2026-06-16_opus_e2e/`（golden 基线）、未改 `case_tests/test_baseline/gt/`、未改任何 `src/`（本单是探、不是修）。
