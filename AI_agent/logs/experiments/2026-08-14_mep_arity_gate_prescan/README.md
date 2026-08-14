# 2026-08-14 派工前机械核实：IDD 字段对齐门会照红多少历史产物 + F-28 定性再修正

**性质**：orchestrator 亲跑的**只读**预扫（plan.md 2026-08-13 §七 明令「派工前必做的机械核实，⛔ 不许发单前跳过」）。
**零生产码改动**；探针 = `probe_arity.py`（本目录），输出 = `prescan_output.md`。

---

## 一、预扫结论（问题：新增 IDD 对齐门会当场红掉多少历史产物）

判据 = 用仓里已有的 IDD 元数据（`data/dependencies/Energy+.idd`，经 eppy `objidd` 暴露 `\required-field`）
对每个 `*_specs` 解析出的对象查两件事：① 有 `\required-field` 标记的格是否缺失/为空 ② 字段数是否超出 IDD 上限。
解析走仓里唯一 parser `src/validator/idf_fragments.py:parse_mep_fragments`（与真实检查同一份解析）。

**结果：21 份产物中 15 份会红**（明细见 `prescan_output.md`）：

> **⛔ 2026-08-14 当日更正（摊 B 席位指出、orchestrator 核实）**：这 21 份里
> **`smalloffice_23` 那份不在版本库里**（`.gitignore:320` 显式排除 `case_tests/e2e_tests/smalloffice_23/4_mep/`）
> ⇒ **「21 份」是本机工作目录的属性，干净检出只有 20 份，红 14 份。**
> 结论方向不变（该门直接阻塞仍会红掉验收 A 与 08-09 首次到 EP 那份），但**数字以 20/14 为准**。
> **这是 F-8 族又一例**：`git check-ignore -v` 一行就能发现，预扫时没跑。

| 产物 | 红对象数 / 总对象数 | 主要类型 |
|---|---|---|
| sm20 `run_2026-06-15_baseline` | 19 / 138 | `ZoneHVAC:EquipmentConnections` 缺 Zone Air Node Name |
| sm21 `run_2026-06-16_opus_e2e` | 14 / 64 | `People` 缺 Activity Level Schedule Name |
| sm21 `run_2026-06-20_gpt54_reading` | 14 / 50 | 同上 |
| sm21 `run_2026-06-23_gpt54mini_reading` | 14 / 66 | 同上 |
| sm21 `run_2026-07-01_sonnet_e2e_r1` | **42 / 79** | People + ZoneControl:Thermostat + IdealLoads 三类同时 |
| sm21 `run_2026-07-02_sonnet_flow_e2e` | 14 / 106 | `ZoneControl:Thermostat` 缺 Control Type Schedule Name |
| sm21 `run_2026-08-05_probe_a_legacy_snapped` | 14 / 64 | People |
| sm21 `run_2026-08-09_f18_e2e_verify` | 14 / 80 | Thermostat（**该 run 是「全链首次跑到 EP、0 Severe」那份**）|
| sm21 `run_2026-08-13_accept_C` | 14 / 92 | Thermostat（**F-28 本尊，验收 C 崩在这里**）|
| sm21 `run_2026-08-13_batchI_accept_02` | 14 / 64 | IdealLoads 缺 Zone Supply Air Node Name（**该 run 是验收 A、六条全中、EP 0 Severe**）|
| sm21 `run_2026-08-13_oneshot_acceptance` | 28 / 106 | Thermostat + IdealLoads |
| sm21 `run_2026-08-13_post_blocker1_e2e` | 14 / 109 | Thermostat |
| sm21 `run_2026-08-13_surface400_accept_01` | 28 / 106 | Thermostat + IdealLoads |
| sm24 `run_2026-06-24_opus_reading` | 22 / 99 | Thermostat（只写 2 格）+ EquipmentList |
| `smalloffice_23`（case 目录） | 9 / 35 | People |

**干净的 6 份**：`sonnet_e2e_r2` · `wall3_a_retest` · `f13_e2e_verify` · `continuous_e2e` ·
`accept_B`（验收 B）· `batchI_accept_01`。

⇒ **⛔ 这道门若直接上成阻塞门，会把「验收 A」和「08-09 首次跑到 EP」两份已签字的产物一起判红。**
（A 的 EP 输出实核：`EP/EP_run/eplusout.err` 末行 `Completed Successfully-- 4 Warning; 0 Severe Errors`。）

---

## 二、⭐⭐⭐ F-28 定性**第二次**修正（推翻 plan.md 08-13 §六之二 的因果链）

plan.md 写的是：「`hvac_specs` 是 LLM 手写的原始 IDF 文本（位置敏感）⇒ 漏一格 ⇒ 整行位移
⇒ 若移过去的值恰好合法则 19 道门全绿 + EP 正常算完 + **结果是错的**」。

**前半句对，后半句（silent 物理错）在今天的下游路径上不成立 —— 已实测证伪。**

1. **`*_specs` 文本从不被贴进最终 IDF。** 下游 `src/agent/nodes/hvac.py` 把 `hvac_specs`
   当**输入文本**喂给一个 ReAct agent，该 agent 只能通过**具名参数的 MCP 工具**
   （`create_thermostat` / `create_ideal_loads_system`）建对象 ⇒ **结构上不可能发生位移**。
2. **活证据（验收 B）**：`accept_B` 的 `hvac_specs` 里 `ZoneHVAC:IdealLoadsAirSystem`
   **少写了 A4/A5 两格**（`50` 落进 Zone Exhaust Air Node Name、`13` 落进 System Inlet Air Node Name、
   `0.015` 落进 Max Heating Supply Air Temperature）——**位移比 F-28 还狠**；
   而它的最终 IDF `HVACTemplate:Zone:IdealLoadsAirSystem` 是
   `Max Heating Supply Air Temperature = 50 / Min Cooling = 13 / 湿度比 0.0156、0.0077` —— **语义完全正确**。
   ⇒ 下游 LLM **按含义重新落位**了，没有照抄位置。
3. **最终 IDF 里根本没有那两类对象**：`accept_B` 的 IDF 计数 =
   `HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM ×14` + `HVACTEMPLATE:THERMOSTAT ×1`，
   `ZoneHVAC:IdealLoadsAirSystem` / `ZoneControl:Thermostat` **各 0 个**。

**⇒ F-28 的真实危害是【可靠性】不是【静默算错】**：
`mep.hvac_schedule_refs` 用 eppy **按位置**读那段文本，位移后读出一个不存在的时间表名
⇒ `block=1` ⇒ 段级重抽 3 次用尽 ⇒ `quarantined` ⇒ 退出码 20，**整条链死在 4_mep**。

**⇒ 另一条更该记的**：同一个缺陷，**写成空格就放行、写成垃圾值就炸链**。
`mep.hvac_schedule_refs` 的 `blank_reference_policy: pass` 摆在证据里；
`f18_e2e_verify` / `post_blocker1` 的 thermostat 第 3 格是**空的** ⇒ 门放行 ⇒ 一路跑到 EP；
`accept_C` 第 3 格是 `ThermostatSetpoint:DualSetpoint` ⇒ 门拦下 ⇒ 链死。
**决定生死的是「模型那一格留空还是填了东西」，不是缺陷本身。**（同族：memory `absence-conflates-causes-in-observables`。）

---

## 三、维持不变的两条（原登记正确，已复核）

- **全仓零字段个数/对齐校验**：`grep -rn "arity|field_count|expected_fields" src/` **0 命中**（10 条全是
  `parity` / `granularity` / `collinearity` 之类误命中）。mep 检查全是语义检查。
  ⚠️ 顺带更正一处数字：plan.md 记的是「19 道 mep 检查」，`checks/mep.py` 里实际登记的 check id 是
  **18 个**（`mep.idf_parse` / `placeholder_ban` / `name_charset` / `building_north_axis_placeholder` /
  `site_matches_testdata` / `construction_coverage` / `construction_to_material` / `construction_thermal_mass` /
  `schedule_type_refs` / `schedule_completeness` / `load_to_zone` / `load_to_schedule` / `hvac_schedule_refs` /
  `people_field_alignment` / `per_zone_coverage` / `simpleglazing_standalone` / `nomass_positive_resistance` /
  `reasonability_bands`）。这处差异**不影响任何结论**。
- **打地鼠先例属实**：`skills/intake_pipeline/4_mep/authoring.md` 有整整一节
  「People object field order (hard — IDD positions, not semantic grouping)」+ 10 格逐格表，
  是 People 出事后补的；`ZoneControl:Thermostat` **没有对应节**。
  ⇒ 预扫也证实这条提示词补丁**没根治**：`opus_e2e` / `gpt54_reading` / `gpt54mini` /
  `sonnet_e2e_r1` / `probe_a_legacy` / `smalloffice_23` 六份产物的 People 仍缺 Activity Level Schedule Name。
- **IDD 元数据可用、通用门便宜**：本预扫本身就是用 `objidd` 的 `\required-field` 做的，零新依赖。

---

## 四、探针自证（memory 纪律：探针零输出 ≠ 目标不存在）

已知坏件 `accept_C` **必须被抓到**：抓到了 —— `ZONECONTROL:THERMOSTAT × 14`，
`authored=4 / idd=12 / missing=['Control 1 Name']`，与 plan.md 记的原始文本逐字吻合。
已知好件 `accept_B` 的 thermostat 类**不存在**（它压根没写 ZoneControl:Thermostat）⇒ 未误报该类。

## 五、⚠️ 本预扫的口径限制

- 判据只做了「required 格缺失/为空」+「字段数超上限」两条，**没有做 `\type choice` 合法值校验**
  （若做，`post_blocker1` 的 `Control 1 Object Type = HTG_Setpoint` 也会红）⇒ 真实门若更严，红的会更多，不会更少。
- 「下游按含义重新落位」是**一份产物上的一次观测**，不是结构性保证 —— 它由下游 LLM 的行为决定，
  ⛔ 不得据此声称「位移永远无害」。
