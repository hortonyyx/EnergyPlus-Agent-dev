# 调查日志 · 墙 3：`run_mep` 产的 load 引用未定义 schedule

- **日期**：2026-08-06
- **席位**：GLM-5.2（调查席），主工作树
- **基点**：分支 `6.15_ValidationArchM0toM4`，HEAD = `b379cd8`
- **派工单**：`AI_agent/logs/reviews/request/2026-08-06_wall3_mep_schedule_investigation_glm.md`
- **状态**：✅ 完成

> ⛔ 本单为调查单，零生产代码改动、零 commit、零 push。一次性脚本放 `/tmp`。
> 证据纪律：每条结论附可独立重跑的命令 / 文件:行号 / 数字。

---

## 0. 开工自检（三行）

```
$ git log --oneline -1
b379cd8 08.05_f10_check_mep_run_profile_signature      ✓ 期望命中

$ git status --short
?? AI_agent/logs/reviews/request/2026-08-06_f9_rediagnosis_investigation_glm.md
?? AI_agent/logs/reviews/request/2026-08-06_wall3_mep_schedule_investigation_glm.md   ← 本单
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_e1_haiku_e2e/0_reading/cv_evidence/
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-04_smoke_downstream/
?? case_tests/e2e_tests/sm21_anchor/run_2026-08-05_smoke_downstream_r2/1_correction/
→ 无 src/ tests/ 未提交改动 ✓；3 个 case_tests 未跟踪目录属已知 ✓；另 2 个未跟踪项是 request/ 下的调查单（含本单）

$ pwd
/workspaces/EnergyPlus-Agent-dev   ✓ 主工作树
```

自检通过。

---

## TL;DR（一句话定性）

那 14 条 `mep.load_to_schedule` offender **全部**是 `People` 对象的 `Activity Level Schedule Name` 被判 `missing`。**不是 LLM 没生成、也不是检查侧取数错、也不是 schedule 名不存在**——是 **LLM 把 `Sch_ActivityLevel` 放错了 People 对象的字段位置**（放第 4 槽，IDD 规定第 10 槽），eppy 按 IDD 严格位置解析时第 10 槽为空 ⇒ 检查按字段名取到空 ⇒ 判 missing。

**主因 = ②`run_mep` 接线缺陷**：MEP specs 以自由文本 IDF 片段承载（`MepOutput.*_specs: str`），prompt + authoring.md **对 People 字段顺序零约束**，LLM 用「两个 schedule 挨着放」的紧凑语义化写法，与 IDD 严格位置解析冲突。检查侧（③）忠实反映 EP 解析、未冤枉产物；LLM（①）有产出成分但非能力问题。**形状 = 接口错位 + 测试绿而真链路崩（最像 F-5）**。

---

## 1. 现象复现

产物在盘上（探针 A 的 4_mep，零 LLM 成本）：

```
case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped/4_mep/
  ├── mep_output.json     # run_mep 结构化产出（MepOutput，8 字段）
  ├── mep_raw.txt         # LLM 原始回复
  └── mep_thinking.txt
```

离线复跑 `check_mep`（脚本全文见 §6 附录，放 `/tmp/probe_check_mep.py`）：

```bash
$ python3 /tmp/probe_check_mep.py
```

`check_mep` 全部 check 结果：

| check_id | status | 备注 |
|---|---|---|
| mep.idf_parse | PASS | eppy 解析成功 |
| mep.placeholder_ban / name_charset / construction_* / schedule_type_refs / schedule_completeness | PASS | |
| mep.schedule_type_refs | PASS | ← 对照点：ScheduleTypeLimits 有 authoring 范例，LLM 写对 |
| mep.schedule_completeness | PASS | ← 同上 |
| **mep.load_to_schedule** | **FAIL** | **"14 load schedule reference(s) are missing or undefined"** |
| mep.hvac_schedule_refs | PASS | HVAC availability/setpoint schedule 都对 |
| mep.load_to_zone / per_zone_coverage | NOT_APPLICABLE | 离线没传 zone_names（生产传了，不影响 load_to_schedule 结论） |

**14 条全部命中**，与派工单 §1 报错逐字一致。`load_to_schedule` 在 `CheckLayer.INVARIANT`（`mep.py:557`），`disposition()` 对 `mep.*` profile-无关 ⇒ 任何 run_profile 都阻断 ⇒ 这是当前挡在 5_intakeoutput 前面的唯一一堵墙，复现确认。

---

## 2. 那 14 条 offender 逐条明细

`evidence.offenders` 14 条**完全同形**：

```json
{"object": "Z01_F1_Office_NW People", "activity_schedule_ref": "", "reason": "missing"}
...（Z02..Z14，共 14 条，全部 reason="missing"，全部 activity_schedule_ref=""）
```

逐项对账（§4 第 1 问）：

| load 对象（14 个 People） | 字段位置 | LLM 写的值 | 该名字在 schedule_specs 里存不存在 | 检查判定 |
|---|---|---|---|---|
| Z0n_…_ People ×14 | fields[2] = A3 Number of People Schedule | `Sch_Occupancy` | **存在**（schedule_specs 定义了 `Sch_Occupancy`）| ✓ 不报 |
| Z0n_…_ People ×14 | fields[3] = A4 Calculation Method（被占） | `Sch_ActivityLevel` | 名字**存在**，但**落在错的槽**（A4 应是 `People`/`People/Area`/`Area/Person` 枚举）| — |
| Z0n_…_ People ×14 | A5 Activity Level Schedule Name（第 10 槽，按字段名取） | `""`（空）| LLM 本意是 `Sch_ActivityLevel`（存在），但**没放对位置** ⇒ eppy 取到空 | **× 报 missing** |

- **LIGHTS（14 个）**：fields[2] = `Sch_Lights`，**存在** ✓，0 报。
- **ELECTRICEQUIPMENT**：0 个。
- 故 14 = 14 个 People × 1（每人 activity 一条），**全部来自 activity 分支**。

**关键事实**：`Sch_ActivityLevel` 这个 schedule **名字在产物里是存在的**（schedule_specs 第 5 个 Schedule:Compact 就是它），LLM **也确实生成了它**（每个 People 文本第 4 个值都是 `Sch_ActivityLevel`，mep_raw.txt 逐字可证）。问题**不是「没生成」也不是「名字不存在」**，而是**放错了 People 对象的字段位置**。

字段错位的精确对账（eppy 按 IDD 位置解析，`nfields=9`）：

```
IDD 顺序(Energy+.idd:21431, \min-fields 10)   LLM 产物落在该槽的值
A1  Name                                    → 'Z01_F1_Office_NW People'   ✓
A2  Zone                                    → 'Z01_F1_Office_NW'          ✓
A3  Number of People Schedule Name          → 'Sch_Occupancy'             ✓
A4  Number of People Calculation Method     → 'Sch_ActivityLevel'         ✗（应是枚举，被填了 schedule 名）
N1  Number of People                        → 'ZoneFloorAreaPerPerson'    ✗（应是数字，被填了方法名）
N2  People per Floor Area                   → '10.0'                      ✗
N3  Floor Area per Person                   → '0.0'                       ✗
N4  Fraction Radiant                        → ''                          
N5  Sensible Heat Fraction                  → ''
A5  Activity Level Schedule Name (required) → 【缺失】（只解析出 9 字段）   ✗ ⇒ missing
```

LLM 的「心智顺序」：Name, Zone, 人数schedule, **活动schedule**, 计算方法, 人均面积, 辐射比, 显热比 —— 把两个 schedule 挨着放（很自然的语义排序），但 IDD 在 A3 与 A5 之间隔着 Calculation Method + 4 个数值字段。LLM 同时跳过了 N1（Number of People）。

**LLM 原始回复就是错位的**（mep_raw.txt，非后处理扭曲）：

```
'People,\n  Z01_F1_Office_NW People,   !- Name\n
  Z01_F1_Office_NW,           !- Zone Name\n
  Sch_Occupancy,               !- Number of People Schedule Name\n
  Sch_ActivityLevel,           !- Activity Level Schedule Name\n   ← LLM 自己注释都标错：它以为第4位是 activity
  ZoneFloorAreaPerPerson,      !- Calcu...'
```

---

## 3. 定性：②`run_mep` 接线缺陷（主因）

派工单给的三个选项：①LLM 产出质量 / ②run_mep 接线缺陷 / ③检查侧取数口径。**判据如下，不给印象。**

### 先排除 ③（检查侧取数口径）

- `_people_activity_schedule_name`（`mep.py:614-624`）通过 eppy raw 对象按 **IDD 字段名** `Activity_Level_Schedule_Name` 取值（`raw` 在 `idf_fragments.py:46,100` 设为 eppy idfobject）。
- eppy 按 IDD 严格位置解析，**与 EnergyPlus 引擎解析方式一致**。A5 `Activity Level Schedule Name` 是 `\required-field`（`Energy+.idd:21431` 段）。
- 故检查侧取到的「空」= **EP 真跑时也会读到空** ⇒ EP 会因 required-field 缺失/Calculation Method 非法枚举报 Severe。
- ⇒ **检查侧忠实反映 EP 解析、没有冤枉产物**。判据：若放宽此检查，产物进 EP 必崩。**排除 ③**。
- （仅一处可改进的「呈现口径」：offender 措辞 `reason:"missing"` 易误读为「LLM 没写 activity」，真相是「写了但放错位置」——这是诊断措辞问题，非取数问题，见 §4-C。）

### 再排除「纯 ①」（LLM 该生成而没生成）

- LLM **生成了** `Sch_ActivityLevel`：它在 schedule_specs 里定义了该 schedule（检查 `schedule_type_refs`/`schedule_completeness` 双 PASS），并在每个 People 文本里写了它（mep_raw.txt 逐字可证）。
- 故不是「该生成没生成」。是「生成位置错」。**排除纯 ①**。

### 坐实 ②（run_mep 接线缺陷）—— 三条独立判据

1. **schema 放任字段位置**：`MepOutput` 的 `schedule_specs/people_specs/lights_specs` 全是 `str`（`intakeoutput.py:34-37`）。字段位置语义**零机器约束**，全靠 LLM 自觉对齐 IDD。
2. **prompt + authoring.md 对 People 零约束**：
   - `run_mep` 的 system prompt（`pipeline.py:730-748`）只说「author per-zone people/lights/hvac against these exact names」「follow the naming rules」，**不提 People 字段顺序**。
   - `skills/intake_pipeline/4_mep/authoring.md`：`grep -c People` = **0**、`grep -c '[Aa]ctivity'` = 1（仅 line 78/84 是 ScheduleTypeLimits 的 `ActivityLevel` 类型名）。**People 对象字段顺序零约束、零范例**。
3. **判决性因果对照（同一 LLM、同一产物、同一 prompt 框架）**：
   - `ScheduleTypeLimits`：authoring.md **给了**字段顺序范例（line 78「field 2 … MUST be …」+ line 84 范例）⇒ LLM 写对 ⇒ `mep.schedule_type_refs` PASS + `mep.schedule_completeness` PASS。
   - `People`：authoring.md **零约束** ⇒ LLM 用紧凑语义化写法 ⇒ 字段错位 ⇒ `mep.load_to_schedule` 14 条。
   - **给顺序约束的对象写对了，没给的对象写错了** ⇒ 病因是「接线没给约束」，不是「LLM 能力不行」。

⇒ **主因 = ②run_mep 接线缺陷**（schema 自由文本 + 文档零约束，让 IDD 字段位置无机械保证）。LLM（①）只是缺陷的触发器，不是根因。

---

## 4. 修法选项（2–3 个，含「什么都不改」）· ⛔ 不动手

### 选项 A（推荐·治本·轻量）：给 People 一个 IDD-correct 字段顺序范例

**做什么**：在 `authoring.md` 里加 People 对象的字段顺序范例（仿 ScheduleTypeLimits 那段），明确：A4 = Calculation Method（枚举 `People`/`People/Area`/`Area/Person`）、A5（第 10 字段）= Activity Level Schedule Name，**禁止把 activity 提前**；并要求 People 写够 ≥10 字段。

- **后果**：仅改 skill 文档（非 `src/` 生产码）；下次跑 LLM 应能遵守——**有判决性对照支撑**：ScheduleTypeLimits 有范例 LLM 就写对了。
- **代价/风险**：prompt 级约束，**非机器强制**（schema 仍是 str）；若 LLM 仍不遵守，问题再现。属本项目「关键不变量别交给 LLM 记得」铁律的弱化版——但 People 字段顺序目前只能靠 prompt（除非走选项 B）。
- **验证**：可零成本用盘上产物改 authoring 后重跑一次 `run_mep` 看 load_to_schedule 是否转 PASS。

### 选项 B（治本·机器强制·重）：`people_specs` 从自由 str 改结构化

**做什么**：把 `MepOutput.people_specs`（及 lights/equipment）从 `str` 改为结构化（pydantic 模型 / 明确字段槽），由代码按 IDD 顺序序列化成 IDF 文本；LLM 只填语义字段（zone、sched 名、密度、方法）。

- **后果**：字段位置由代码保证，**根除整类「字段错位」缺陷**（不只 People）；契合不变量 #1（LLM 只做语义判断、代码做所有结构）。
- **代价**：改 `MepOutput` 契约层 + `run_mep` 后处理 + `5_intakeoutput` 装配 + 下游消费 + **全部 mep 测试夹具**。`MepOutput` 是交接契约的一部分（不变量 #3 邻近），影响面大、工作量重。最稳但最贵。

### 选项 C（诊断增强·不解除阻断·可作 A 的补充）

**做什么**：保持现状 schema，让检查侧在 activity 为空时附带判「fields[3]（A4）是否被填了一个 schedule 名 / fields[4]（N1）是否非数字」，把 offender 措辞从笼统 `missing` 改为 `activity-schedule-misplaced`，并指向真槽位。

- **后果**：不解决问题（产物仍不能进 EP、仍阻断），但诊断**不再误导**（避免下游误以为是「LLM 漏写 schedule」而跑错修法方向）。
- **代价**：检查侧改诊断措辞 + 加字段错位启发式；不解除阻断。

### 选项 D（什么都不改·代价）

F-10 让 `check_mep` 能跑了，但 `load_to_schedule` 仍 INVARIANT 阻断所有 run_profile ⇒ **5_intakeoutput 至今零证据、且将继续零证据**；任何走 flow 的 run 跑到 4_mep 必被这 14 条挡死，下游 IDF/EnergyPlus 全程得不到真实产物验证。**这是当前挡在 5_intakeoutput 前面的唯一一堵墙**，不修则端到端链路永久卡在 4_mep。

**建议排序**：A（性价比最高、有对照证据、零 src 改动）→ 若 A 实测仍漏则升 B。C 可与 A 并做以纠正诊断措辞。D 不可接受（链路死锁）。

---

## 5. 是否与 F-5/F-7/F-10 同族

**是。两个形状都占，最像 F-5。**

### 形状一：接口错位 ✓（与 F-5/F-7/F-10 同）
- F-5 = 消费侧读错字段名（契约 `x_range_m` vs 代码 `x_range`）。
- F-10 = `check_mep` 签名漂移（调用方加 `run_profile`、被调方没有）。
- **本案** = LLM 自由文本产出（紧凑语义化）vs eppy/EP 严格 IDD 位置解析，中间**无机械对齐**（`*_specs: str` 放任字段位置）。「两个 schedule 挨着放」在 LLM 的语义里自洽，在 IDD 的位置语法里非法——典型接口错位。

### 形状二：测试绿而真链路崩 ✓（最像 F-5）
所有 mep 检查测试夹具的 People **都是人手写的 IDD-correct 顺序**：
- `tests/test_check_parity.py:111-121` 与 `tests/test_run_pipeline_self_checks.py:95-105`：`Name, Zone, Occ, People(calc method), 1, , , 0.3, Autocalculate, Activity` —— activity 在**第 10 位**。
- `tests/test_checks_mep_assembly.py:300-320`（`_people_activity_mep`）：activity 也按 IDD 位置插在 Autocalculate 之后。

⇒ **夹具天然遵守 IDD 位置（人写的），从未模拟真实 LLM 的紧凑错位形态**。于是 `test_people_primary_and_activity_schedules_pass_load_to_schedule` 等锁住的是「正确顺序下能过」，而**没有任何测试覆盖「LLM 把 activity 放第 4 位」这种真实产出形态** ⇒ 检查在测试上永远绿，真 LLM 产物一跑就 14 条。

这是 memory [[real-chain-run-exposes-what-tests-cannot]] 记录的「一族三形态」的**第四张脸**：F-5（夹具照抄实现错拼写）/ F-7（夹具手搓生产方给不出的形态）/ F-8（依赖没进版本库的数据）/ **本案（夹具手搓了 IDD-correct 形态，而真实 LLM 给出的是紧凑错位形态——夹具的形态分布 ≠ 真实产出分布）**。判别问法（换台机器/换份真产物还成立吗）：本案**只在真 LLM 产物上成立、在测试夹具上永不成立** ⇒ 单测全绿一条没抓到，与 F-5 同构。

---

## 6. 证据附录（命令 / 文件:行号 / 数字）

### 6.1 关键文件:行号

| 位置 | 作用 |
|---|---|
| `src/validator/checks/mep.py:41` | `_LOAD_TYPES = ("PEOPLE","LIGHTS","ELECTRICEQUIPMENT")` |
| `src/validator/checks/mep.py:523-560` | `_load_refs`：sched_bad 来源（fields[2] + PEOPLE activity）|
| `src/validator/checks/mep.py:556-558` | `mep.load_to_schedule` add_fail（INVARIANT，14 条来自此）|
| `src/validator/checks/mep.py:614-624` | `_people_activity_schedule_name`：按 IDD 字段名取（正确）|
| `src/validator/idf_fragments.py:46,100` | `IdfObject.raw` = eppy idfobject（按 IDD 位置解析）|
| `src/agent/pipeline.py:715-769` | `_build_mep_messages`：prompt，**无 People 字段顺序约束** |
| `src/agent/pipeline.py:772-802` | `run_mep` 实现 |
| `src/agent/pipeline.py:1350-1356` | 生产调用 `check_mep`（F-10 后正确签名）|
| `src/agent/intakeoutput.py:34-37` | `MepOutput.schedule_specs/people_specs/lights_specs: str`（位置零约束根因）|
| `skills/intake_pipeline/4_mep/authoring.md:78,84` | ScheduleTypeLimits 字段顺序范例（**People 段缺失**）|
| `data/dependencies/Energy+.idd:21431` | People IDD：A5 Activity Level Schedule Name，`\required-field`，`\min-fields 10` |
| `tests/test_check_parity.py:111-121`、`tests/test_run_pipeline_self_checks.py:95-105`、`tests/test_checks_mep_assembly.py:300-320` | 测试夹具 People（IDD-correct 顺序，未覆盖错位形态）|
| `case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped/4_mep/mep_output.json` | 真实 LLM 产物（错位形态）|

### 6.2 关键数字

- offenders = **14**，全部 `{"reason":"missing", "activity_schedule_ref":""}`，object = Z01..Z14 × People。
- schedule_specs 定义 **6** 个 Schedule:Compact：`Sch_Occupancy / Sch_Lights / Sch_Heating_SP / Sch_Cooling_SP / Sch_ActivityLevel / Sch_Availability`。
- PEOPLE = **14**、LIGHTS = **14**、ELECTRICEQUIPMENT = **0**。
- eppy 解析 People `nfields = 9`（IDD `\min-fields 10`，第 10 槽 A5 缺失）。
- authoring.md `grep -c People` = **0**。

### 6.3 可独立重跑的复现脚本（`/tmp/probe_check_mep.py`）

```python
"""One-shot probe (investigation-only). Replays check_mep on the on-disk
4_mep product to extract the exact offenders behind
'mep.load_to_schedule: 14 ... are missing or undefined'."""
import json, sys, os
REPO = '/workspaces/EnergyPlus-Agent-dev'
sys.path.insert(0, REPO); os.chdir(REPO)
from src.agent._share import ensure_schema_initialized
ensure_schema_initialized()
from src.validator.checks.mep import check_mep, _people_activity_schedule_name
from src.validator.idf_fragments import parse_mep_fragments

P = REPO + '/case_tests/e2e_tests/sm21_anchor/run_2026-08-05_probe_a_legacy_snapped/4_mep/mep_output.json'
mep = json.load(open(P))
rep = check_mep(mep)  # zone_names=None 默认；load_to_schedule 独立于 zone_names

print("=== ALL CHECKS ===")
for r in rep.results:
    print(f"  {r.check_id:34s} {str(r.status):14s} {r.message}")
print("\n=== load_to_schedule OFFENDERS ===")
for r in rep.results:
    if r.check_id == 'mep.load_to_schedule':
        print(json.dumps(r.evidence, indent=2, ensure_ascii=False))

idx = parse_mep_fragments(mep)
print("\n=== defined SCHEDULE:COMPACT ===", sorted(idx.has_name('SCHEDULE:COMPACT')))
print("n PEOPLE/LIGHTS/EQUIP =", len(idx.of_type('PEOPLE')), len(idx.of_type('LIGHTS')), len(idx.of_type('ELECTRICEQUIPMENT')))
print("\n=== PEOPLE field-by-field (first) ===")
o0 = idx.of_type('PEOPLE')[0]
for i, fv in enumerate(o0.fields):
    print(f"  fields[{i}] = {fv!r}")
print("  activity(resolved) =", repr(_people_activity_schedule_name(o0)),
      "| raw.Activity_Level_Schedule_Name =", repr(getattr(o0.raw, 'Activity_Level_Schedule_Name', '<no-attr>')))
```

**实测输出摘录**（`head`/`tail` 已在调查中捕获，落 `/tmp/probe_check_mep.out` 可复核）：

```
mep.load_to_schedule   FAIL   14 load schedule reference(s) are missing or undefined
offenders: [{object: Z01_.. People, activity_schedule_ref: "", reason: "missing"} × 14]
defined: ['Sch_ActivityLevel','Sch_Availability','Sch_Cooling_SP','Sch_Heating_SP','Sch_Lights','Sch_Occupancy']
n PEOPLE/LIGHTS/EQUIP = 14 14 0
fields[0]='Z01_F1_Office_NW People'  fields[1]='Z01_F1_Office_NW'
fields[2]='Sch_Occupancy'   ← A3 ✓
fields[3]='Sch_ActivityLevel' ← 落在 A4(Calculation Method) ✗
fields[4]='ZoneFloorAreaPerPerson' ← 落在 N1(Number of People) ✗
fields[5]='10.0' fields[6]='0.0' fields[7]='' fields[8]=''
activity(resolved)='' | raw.Activity_Level_Schedule_Name=''   ← A5 第10槽空 ⇒ missing
```

### 6.4 IDD People 字段定义（`data/dependencies/Energy+.idd:21431`）

```
People,
   \min-fields 10
  A1 , \field Name                          ← fields[0]
  A2 , \field Zone or ZoneList ... Name     ← fields[1]
  A3 , \field Number of People Schedule Name← fields[2]
  A4 , \field Number of People Calculation Method  (choice: People/People/Area/Area/Person) ← fields[3]
  N1 , \field Number of People              ← fields[4]
  N2 , \field People per Floor Area         ← fields[5]
  N3 , \field Floor Area per Person         ← fields[6]
  N4 , \field Fraction Radiant              ← fields[7]
  N5 , \field Sensible Heat Fraction        ← fields[8]
  A5 , \field Activity Level Schedule Name  \required-field   ← fields[9] = 第10槽（LLM 产物缺失）
```

---

## 7. 边界确认

- ⛔ 未改任何 `src/` `scripts/` `skills/` `tests/` 生产代码。
- ⛔ 未 commit、未 push、未 `git add -A`（主树 5 个未跟踪项原样未动）。
- ✅ 一次性脚本仅落 `/tmp/probe_check_mep.py`。
- ✅ 唯一产出 = 本日志文件。
