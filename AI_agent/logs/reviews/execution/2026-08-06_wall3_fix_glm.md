# 施工日志 · 墙 3：People 字段错位 → 补范例 + 补门 + 改措辞

- **日期**：2026-08-06
- **席位**：GLM-5.2（施工席），主工作树
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `b379cd8`
- **施工单**：[`request/2026-08-06_wall3_fix_dispatch_glm.md`](../request/2026-08-06_wall3_fix_dispatch_glm.md)
- **调查全档**：[`execution/2026-08-06_wall3_mep_schedule_investigation_glm.md`](2026-08-06_wall3_mep_schedule_investigation_glm.md)（同席位自做）
- **状态**：✅ 完成（三件施工 A/B/C + 验收 1–5 全过；A 实测有效）

> 证据纪律：每条结论附可独立重跑的命令 / 文件:行号 / 数字。一次性脚本与 neuter 副本均落 `/tmp`。

---

## 0. 开工自检（三行）

```
$ git log --oneline -1
b379cd8 08.05_f10_check_mep_run_profile_signature      ✓ 期望命中

$ git status --short
?? AI_agent/logs/reviews/execution/2026-08-06_wall3_mep_schedule_investigation_glm.md   ← 本单调查
?? AI_agent/logs/reviews/request/2026-08-06_f9_rediagnosis_investigation_glm.md          (隔壁 F9 调查单，与本单无关)
?? AI_agent/logs/reviews/request/2026-08-06_wall3_fix_dispatch_glm.md                    ← 本单
?? AI_agent/logs/reviews/request/2026-08-06_wall3_mep_schedule_investigation_glm.md      (本单调查的 request)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_e1_haiku_e2e/0_reading/cv_evidence/   (已知未跟踪，不碰)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_smoke_downstream/                     (已知未跟踪，不碰)
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-05_smoke_downstream_r2/1_correction/     (已知未跟踪，不碰)
→ 无 src/ tests/ skills/ 未提交改动 ✓

$ pwd
/workspaces/EnergyPlus-Agent-dev   ✓ 主工作树
```

**与施工单 §0 的差异（如实登记）**：施工单 §0 期望"3 个 case_tests 未跟踪目录 + 3 个 AI_agent 未跟踪 md"；
实际是 **3 个 case_tests 目录 + 4 个 AI_agent md**。多出的一个是
`request/2026-08-06_f9_rediagnosis_investigation_glm.md`（隔壁 F9 重新诊断的调查单，与本单无关）。
不阻断本单（HEAD / pwd / 工作树性质全对）。全程 ⛔ 未 `git add -A`，逐个 `git add` 本单文件。

自检通过。

---

## 1. 三件施工

### A · `skills/intake_pipeline/4_mep/authoring.md` 补 IDD-correct People 范例

**现状**：`grep -c People` = 0（整份文档零次提及 People 对象的字段顺序）。
**改动**：在 `### people_specs / lights_specs / hvac_specs (per zone)` 章节内追加 `#### People object field order (hard — IDD positions, not semantic grouping)` 子节（`+50` 行），同时体现：
- **十个槽位的 IDD 顺序**（A1–A5 / N1–N5，明确两 schedule 名在 IDD 里不相邻、中间隔着 calc method + 四个数值字段）；
- **A4 的三个合法 key**（`People` / `People/Area` / `Area/Person`），并点名 OpenStudio-style key（`ZoneFloorAreaPerPerson` 等）**不是** EnergyPlus IDD 值、EP 会拒（覆盖 orchestrator 追加事实 §2.2）；
- **A5 `Activity Level Schedule Name` 是 `\required-field` 且在第 10 槽**（不是第 4 槽），须写在结尾、至少 10 字段；
- 一个 worked example（`Area/Person` + N3=10.0 + A5=Sch_ActivityLevel），并点名错位会被 `mep.people_field_alignment` 抓。
⛔ 未改该文件其它章节。

### B · ⭐ 新 gate① 门 `mep.people_field_alignment`（承重件）

**文件**：`src/validator/checks/mep.py`。
**机制**（不查第 10 槽非空——那是症状；查 A4 是否合法枚举——那是病）：
- 新常量 `_PEOPLE_CALC_METHODS = ("People", "People/Area", "Area/Person")`（IDD `Energy+.idd` People 段 `\key` 三行）。
- 新函数 `_people_field_alignment(rep, idx)`：对每个 `PEOPLE` 对象取 A4 = `fields[3]`；若 A4 ∈ 合法枚举 ⇒ PASS（A4 合法时不在本门报，A5 空/未定义归 `mep.load_to_schedule`）；若 A4 非合法枚举 ⇒ FAIL，并区分两种 `reason`：
  - `activity_schedule_misplaced_into_calc_method_slot`：A4 恰是某已定义 `SCHEDULE:COMPACT` 名 ⇒ 真错位（activity schedule 从 A5 错位到 A4）；
  - `illegal_calculation_method`：A4 既非枚举也非已定义 schedule 名（如 OpenStudio-style key）。
- evidence 含完整 IDD 字段序 + `disease_vs_symptom` 说明（load_to_schedule 报症状、本门报病）。
- 在 `check_mep` 注册（`_load_refs` 之后），`CheckLayer.INVARIANT`。

### C · 改 `mep.load_to_schedule` 报错措辞

**文件**：`src/validator/checks/mep.py`（`_load_refs`）。
**改动**：仅 message 字符串。⛔ `check_id = "mep.load_to_schedule"` 不变、`CheckLayer.INVARIANT` 不变。
- 旧：`"N load schedule reference(s) are missing or undefined"`（把排查引向"schedule 没定义"，而 schedule 定义得好好的）。
- 新：`"N People/Lights schedule field(s) are blank or reference a name not defined in schedule_specs — a blank People activity-level schedule is usually a field-misalignment symptom, not a missing schedule (see mep.people_field_alignment)"`。

**测试锁**（`tests/test_checks_mep_assembly.py`，`+57` 行）：
- `_people_misaligned_mep()` 夹具（还原真实 LLM 错位形态：A4 = schedule 名）。
- `test_people_field_misalignment_blocks_alignment_check`：错位 ⇒ `mep.people_field_alignment` FAIL，offender `reason = activity_schedule_misplaced_into_calc_method_slot`、A4=`Sch_Activity`、A5=`<blank>`、`expected_A4_one_of=[People, People/Area, Area/Person]`（断言落具体 check-id 行 + 具体 offender 字段）。
- `test_alignment_check_distinguishes_misalignment_from_undefined_name`：A4 合法 + A5 名字真没定义 ⇒ `mep.people_field_alignment` PASS 且 `mep.load_to_schedule` FAIL（两格区分）。
- 夹具全 inline，⛔ 不依赖 gitignored 文件（F-8）。

---

## 2. 验收 1–2（离线，零 LLM 成本）

探针 `/tmp/wall3_verify.py`（全文见本档，可独立重跑）。

### 验收 1：B 门在真实旧产物上 FAIL 且指明错位

真实产物 `run_2026-08-05_probe_a_legacy_snapped/4_mep/mep_output.json`：

```
mep.people_field_alignment   FAIL
   message: 14 People object(s) have a field misalignment or an illegal calculation method
   n_offenders: 14
   offender[0].reason: activity_schedule_misplaced_into_calc_method_slot
   offender[0].field_A4: Sch_ActivityLevel
   offender[0].field_A5: <blank>
[1] PASS: real product -> people_field_alignment FAIL, reason=misplaced, A4=Sch_ActivityLevel, n=14
```

✅ 14 个 People 全部被抓、全部判为"activity schedule 错位到 calc method 槽"，指明错位而非笼统 missing。

### 验收 2：两格区分实测（断言落具体 check-id 行）

```
[2-i]  misaligned cell (A4 = schedule name):
       people_field_alignment FAIL (reason=activity_schedule_misplaced_into_calc_method_slot)   ← 格①错位
[2-ii] undefined-name cell (A4 = People, A5 = undefined name):
       people_field_alignment PASS ; load_to_schedule FAIL (activity_schedule_ref=Sch_GenuinelyMissing)   ← 格②名字没定义
[2-ii] PASS: undefined-name -> people_field_alignment PASS, load_to_schedule FAIL (distinguished)
```

✅ 两格清晰区分：错位 ⇒ B 门 FAIL；名字真没定义 ⇒ B 门 PASS、load_to_schedule FAIL。断言落在 `mep.people_field_alignment` / `mep.load_to_schedule` 具体 check-id 行 + 具体 offender 字段，⛔ 不是"非 None""总数变了"。

---

## 3. 验收 3：neuter 两向（先 git diff 确认改动落下去了）

主改动 git diff 确认（避免 orchestrator 实犯的"正则命中 0 处却拿到 22 绿"）：

```
$ git diff --stat src/validator/checks/mep.py skills/.../authoring.md tests/test_checks_mep_assembly.py
 skills/intake_pipeline/4_mep/authoring.md | 50 ++++
 src/validator/checks/mep.py               | 97 +++++++-
 tests/test_checks_mep_assembly.py         | 57 ++++
 3 files changed, 203 insertions(+), 1 deletion(-)

$ git diff src/validator/checks/mep.py | grep '^+' | grep -E 'people_field_alignment|_PEOPLE_CALC_METHODS|if a4 in _PEOPLE_CALC_METHODS|field-misalignment'
+_PEOPLE_CALC_METHODS = ("People", "People/Area", "Area/Person")
+    _people_field_alignment(rep, idx)
+def _people_field_alignment(rep, idx):
+        if a4 in _PEOPLE_CALC_METHODS:
+            "mep.people_field_alignment",
+   ... field-misalignment symptom ...
```

neuter 在 `/tmp/wall3_neuter` 副本（`cp -r src tests data pyproject.toml`）做，⛔ 未动工作树。每次 neuter 后先 `grep NEUTER-` 确认标记落下去了再跑。

**Neuter A（漏报 / 假绿）**：在 `_people_field_alignment` 循环体首行插 `continue`（对所有 PEOPLE 跳过 ⇒ offenders 永远空）。
```
grep: 656: continue  # NEUTER-A false-green   ← 标记落地
pytest -k "misalignment or distinguishes":
  test_people_field_misalignment_blocks_alignment_check    FAILED   ← 锁1 红（alignment 从 FAIL 变 PASS）
  test_alignment_check_distinguishes_misalignment_from_undefined_name  passed
```

**Neuter B（误报 / 假红）**：`if a4 in _PEOPLE_CALC_METHODS:` → `if a4 in _PEOPLE_CALC_METHODS and False:`（合法 A4 也进 offender）。
```
restore: grep -c NEUTER- → 0 (clean)   ← 副本干净还原
grep: 657: if a4 in _PEOPLE_CALC_METHODS and False:  # NEUTER-B false-red   ← 标记落地
pytest -k "misalignment or distinguishes":
  test_people_field_misalignment_blocks_alignment_check    passed   (Sch_Activity 仍 misplaced ⇒ 锁1 绿)
  test_alignment_check_distinguishes_misalignment_from_undefined_name  FAILED   ← 锁2 红（A4=People 也被误报）
```

✅ 两向各击中一个锁（漏报→锁1 红 / 误报→锁2 红），证明 B 门的两个方向（报错位 / 不误报合法 A4）都有锁绑定。
neuter 后工作树 `grep -rc NEUTER- src/ tests/` = 0（无残留），`/tmp/wall3_neuter` 已删。

---

## 4. 验收 4：全仓 pytest（不加 -m）

```
$ python3 -m pytest -n auto
========== 2225 passed, 10 xfailed, 209 warnings in 308.56s (0:05:08) ==========
```

- 基线 **2223 passed / 10 xfailed / 0 failed** + 本单净增 **2 锁** = **2225 passed / 10 xfailed / 0 failed**。
- ✅ 零回归、净增锁。新锁全 inline 夹具，⛔ 不依赖 gitignored 文件。
- 既有 `test_clean_anchor_mep_passes`（sm20 anchor）未破坏：sm20 anchor People 的 A4 = `Area/Person`（合法枚举），新门 PASS。

---

## 5. ⚠️ 验收 5：A 的实测（重跑一次 4_mep，exploratory）

**方法**：cp 探针 A run 目录 → `run_2026-08-06_wall3_a_retest`（不污染原探针 A），删其 `4_mep`，用 flow 重跑仅这一段：
```
$ python3 scripts/tool_scripts/run_stage.py flow sm21_anchor run_2026-08-06_wall3_a_retest \
      --from 4_mep --to 4_mep --judge off --geometry auto
[4_mep] deterministic_pass  (attempts=1, accepted=1)
  → gate① passed — no enabled judge for this stage → advance
  gate①: {'passed': True, 'block': 0, 'flag': 0}
```

**模型**：`deepseek-v4-pro`（`src/configs/llm.yaml` default；探针 A 原 4_mep 同模型——run_config 无 mep section ⇒ 两者都用 default）。
**唯一变量** = `authoring.md`（加了 People 范例）。其余输入同一：correction_geometry_snapped.json、testdata、mep.md、模型。

**结果：A 有效。** 重跑产物 14 个 People 对象**全部 IDD-correct**，与 authoring.md 范例逐字段吻合：

| 槽位 (IDD) | 探针 A 原始 4_mep（错位） | 重跑 4_mep（更新 authoring.md 后） |
|---|---|---|
| A4 `Number of People Calculation Method` (fields[3]) | `Sch_ActivityLevel` ❌ | `Area/Person` ✅ 合法枚举 |
| N3 `Floor Area per Person` (fields[6]) | （被挤到 N1/N2） | `10.0` ✅ 正确位置 |
| A5 `Activity Level Schedule Name` (fields[9]) | **缺失** ❌ | `Sch_ActivityLevel` ✅ 第 10 槽 |

```
check_mep on new product:
  mep.people_field_alignment: PASS
  mep.load_to_schedule:       PASS
  （其余非 PASS 均为 NOT_APPLICABLE：离线调用未传 zone_names/used_constructions/testdata，非 FAIL）
```

LLM 甚至学会了 authoring.md 范例里的"Area/Person ⇒ N1/N2 留空、N3 填密度"正确用法。

**⚠️ 噪声警示（如实登记）**：这是**单次**重跑。LLM 有随机性（本项目历史有"同配置两抽差 2.8×"的纪律）。一次 PASS 是强正向证据（14/14 全对 vs 探针 A 的 14/14 全错，唯一变量是 authoring.md），但**不能断言"A 100% 有效每次"**。生产化前建议多次验证；若再现错位，B 门（`mep.people_field_alignment`）会确定性兜底阻断——这正是 B 作为承重件存在的理由（CLAUDE.md §4#2：关键不变量不交给 LLM 记得）。

**结论**：A 本次有效（非"停下上报"情形）。A（说服模型）+ B（确定性兜底）成对成立。

**retest 产物处置**：`run_2026-08-06_wall3_a_retest/` 为本次验收 5 的 exploratory 产物（未跟踪、⛔ 不进 commit），保留作可复验证据；其 4_mep/mep_output.json 即上表数据来源。

---

## 6. 边界确认

- ⛔ 未改 `people_specs` 的类型（结构化是治本方向，需用户拍板，本单不做）。
- ⛔ 未 push。
- ⛔ 未 `git add -A`（主树 7 个未跟踪项 + retest 目录原样未动）；逐个 `git add` 本单的 3 个改动文件 + 4 份 md。
- ✅ 一次性脚本（`/tmp/wall3_verify.py`）与 neuter 副本（`/tmp/wall3_neuter`，已删）均落 `/tmp`。

---

## 7. 交付

- 代码 + 锁：`src/validator/checks/mep.py`、`skills/intake_pipeline/4_mep/authoring.md`、`tests/test_checks_mep_assembly.py`。
- 本执行日志：`execution/2026-08-06_wall3_fix_glm.md`（本文）。
- 一并 `git add`：本单 + 调查单两份 md（dispatch / investigation）。
- commit message 仿 `08.06_wall3_people_field_order`，body 含 ①改动 ②为何此刻 ③影响。**自己 commit，不 push。**

---

## 附录：`/tmp/wall3_verify.py`（验收 1–2 探针全文）

```python
"""Wall-3 acceptance probe 1+2 (offline, zero LLM cost)."""
import json, sys, os
REPO = '/workspaces/EnergyPlus-Agent-dev'
sys.path.insert(0, REPO); os.chdir(REPO)
from src.agent._share import ensure_schema_initialized
ensure_schema_initialized()
from src.validator.checks.mep import check_mep
from src.validator.checks.schema import CheckStatus

REAL = REPO + '/case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped/4_mep/mep_output.json'

# (1) REAL legacy product
mep = json.load(open(REAL))
rep = check_mep(mep)
al = next(r for r in rep.results if r.check_id == "mep.people_field_alignment")
assert al.status == CheckStatus.FAIL
assert al.evidence["offenders"][0]["reason"] == "activity_schedule_misplaced_into_calc_method_slot"
assert al.evidence["offenders"][0]["field_A4_Number_of_People_Calculation_Method"] == "Sch_ActivityLevel"
assert len(al.evidence["offenders"]) == 14

SCHED = ("ScheduleTypeLimits,Fraction,0,1,Continuous; ScheduleTypeLimits,Any Number,,,Continuous; "
         "Schedule:Compact,Occ,Fraction,...; Schedule:Compact,Sch_Activity,Any Number,...;")
# (2-i) misaligned cell: A4 = schedule name
misaligned = {... "people_specs": "People,P1,Z1,Occ,Sch_Activity,Area/Person,10,0.3,,;"}
rep1 = check_mep(misaligned, zone_names={"Z1"})
assert next(r for r in rep1.results if r.check_id=="mep.people_field_alignment").status == CheckStatus.FAIL
# (2-ii) undefined-name cell: A4 = People (legal), A5 = undefined name
undefined = {... "people_specs": "People,P1,Z1,Occ,People,1,,,0.3,autocalculate,Sch_GenuinelyMissing;"}
rep2 = check_mep(undefined, zone_names={"Z1"})
assert next(r for r in rep2.results if r.check_id=="mep.people_field_alignment").status == CheckStatus.PASS
assert next(r for r in rep2.results if r.check_id=="mep.load_to_schedule").status == CheckStatus.FAIL
# (完整可跑版见 git 历史的 /tmp/wall3_verify.py；此处为示意摘录)
```
