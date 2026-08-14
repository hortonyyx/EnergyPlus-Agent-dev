# 派工单 · 摊 A —— 让 4_mep 的**设备段**由代码确定性生成，模型碰不到那几格

- **日期**：2026-08-14
- **席位**：Claude 侧执行档（Sonnet 5）
- **审阅去向**：GPT 侧（跨家族）
- **用户拍板**（2026-08-14）：修法形态 = **最小改动（代码按内核区列表直接渲染那段文本）**，
  「把设备段改成结构化字段」留作后续「标注/墙厚/出模」专项 ⇒ ⛔ 本摊不做结构化改造。
- **并行摊**：摊 B（GLM 侧）在做「IDD 驱动的通用字段对齐检查」。**两摊有一处硬接缝，见 §3。**
- **基线**（orchestrator 2026-08-14 独立实测，`a413e66` 干净树）：`rc=0` · **`2603 passed / 10 xfailed / 0 failed`**（`-n auto`，9 分 05 秒）。

---

## 0. 停止规矩（分层）

1. **承重前提错**（本单 §2 的事实、§3 的接缝）⇒ **停下上报**。
2. **外围论据错**（我写的背景叙述、动机、类比）⇒ **报告里写明，然后把主体做完**。

派工方历史错误率 **16/16**（全是题错，不是施工能力问题）。本单里凡是我做的**判断**都标了 ⚠️，
请主动证伪；凡是标「已实测」的，是我今天亲手跑出来的，可复现。

---

## 1. 背景：这一格为什么必须让模型碰不到（已实测，非推测）

08-13 验收连跑 3 次，第 3 次（`case_tests/e2e_tests/sm21_anchor/run_2026-08-13_accept_C`）
**崩在 4_mep 并耗尽段级重抽预算 → `quarantined` → 退出码 20**。根因不是「填错值」，是**漏了一格导致整行位移**：

```
ZoneControl:Thermostat,
  Z01_F1_Office_NW_Thermostat,      ← 1 Name
  Z01_F1_Office_NW,                 ← 2 Zone Name
  ThermostatSetpoint:DualSetpoint,  ← 3 位：EnergyPlus 这里要 Control Type Schedule Name
  Z01_F1_Office_NW_DualSetpoint;    ← 4 位
```
EnergyPlus 该对象前 5 格全是 `\required-field`（`Name / Zone / Control Type Schedule Name /
Control 1 Object Type / Control 1 Name`）⇒ 模型只写 4 格 ⇒ 其后全部前移一位
⇒ `mep.hvac_schedule_refs` 按位置读第 3 格、读到一个不存在的时间表名 ⇒ `block=1`。
**14 个区每次全错、连错三次** ⇒ **整段重抽治不了系统性倾向**（这就是为什么修法不是加重试）。

### ⭐ 两条今天新查实的事实（会影响你的设计，请先接受再动手）

1. **`*_specs` 文本从不被贴进最终 IDF。** 下游 `src/agent/nodes/hvac.py` 把 `hvac_specs`
   当**输入文本**喂给一个 ReAct agent，该 agent 只能通过**具名参数的 MCP 工具**建对象
   （最终 IDF 里是 `HVACTemplate:Zone:IdealLoadsAirSystem ×N` + `HVACTemplate:Thermostat ×1`，
   `ZoneControl:Thermostat` / `ZoneHVAC:IdealLoadsAirSystem` **各 0 个**——`accept_B` 的成品 IDF 已实核）。
   ⇒ **这个缺陷的危害是「链路被门拦死」，不是「静默算错物理」。**
   ⇒ ⛔ 因此**不要**把本摊说成「修复了错误的模拟结果」，那是假的。
2. **同一个毛病，那一格留空就放行、填了字就炸链**：`mep.hvac_schedule_refs` 的
   `blank_reference_policy: pass` 摆在证据里；`run_2026-08-09_f18_e2e_verify` 与
   `run_2026-08-13_post_blocker1_e2e` 的第 3 格是**空的** ⇒ 门放行 ⇒ 一路跑到 EnergyPlus。
   ⇒ **别把「门今天没报」当成「那次是对的」。**

完整预扫与证据：[`AI_agent/logs/experiments/2026-08-14_mep_arity_gate_prescan/README.md`](../../experiments/2026-08-14_mep_arity_gate_prescan/README.md)

---

## 2. 要做什么

**把 `hvac_specs` 整段改成由代码确定性渲染**，模型不再撰写这一段。

### 2.1 接缝（已核实，⚠️ 但仍请你自己确认一遍）

- **渲染发生在 `src/agent/pipeline.py::run_mep` 内部**，覆盖 LLM 返回的 `hvac_specs`。
  **理由 = 单一实现**：`run_mep` 有**两个调用点**——`src/agent/pipeline.py:1389`（flow 主路径）
  与 `scripts/tool_scripts/run_stage.py:714`（分段路径）。放在 `run_mep` 里两条路自动一致；
  放在调用点就会变成「同一假设的两处实现」（本项目吃过这个亏，见 F-22 内墙那处）。
- **区名列表必须来自内核几何对象**，⛔ **不许用正则去解析 `zone_specs` 那段散文**
  （它是给模型看的 markdown 散文，不是 IDF）。两个调用点都拿得到：
  - `pipeline.py:1389` 处：`bg`（`dict.fromkeys(bg.zones)` 就在上面两行）；
  - `run_stage.py:714` 处：`zone_names`，**⚠️ 但它当前是 `set(...)`（`_geometry_zone_meta` 返回，
    `run_stage.py:703`）⇒ 顺序已丢**。你要传**有序序列**，否则两条路径渲染出的文本顺序不同
    ⇒ 「确定性」名不副实。**这一处必须改成有序，并在报告里点名。**

### 2.2 输出形态（⚠️ 这是我下的判断，允许你证伪后改）

渲染成**下游真正会造的那两类对象**：

```
HVACTemplate:Thermostat,
  <thermostat_name>,
  <heating_setpoint_schedule>,
  ,                                  ← Constant Heating Setpoint（留空）
  <cooling_setpoint_schedule>;

HVACTemplate:Zone:IdealLoadsAirSystem,     ← 每个区一个
  <zone_name>,
  <thermostat_name>,
  <availability_schedule>,
  ...
```
**依据**：① 下游 `hvac_agent` 的两个工具正是造这两类；② 现有检查表
`src/validator/checks/mep.py:_HVAC_SCHEDULE_REF_FIELDS` **已经有这两类的条目**
（`HVACTEMPLATE:THERMOSTAT` / `HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM`）⇒ 不需要新增门就被覆盖。
**若你实测发现这个形态在下游或任何门上有障碍 ⇒ 停下上报**（这是承重前提）。

### 2.3 ⚠️ 一个你必须自己解决的岔口：**生成的设备段引用的时间表，谁来定义？**

这是本摊唯一的真岔口，**做错就是把 run C 的死法原样复刻一遍**（引用了不存在的时间表名 ⇒ 门拦 ⇒ 链死）。
现状：时间表名**由模型每轮自己起**，历史产物里出现过 `Sch_Heating_Setpoint` / `HTG_Setpoint` /
`Sch_HtgSetpoint` 三种以上写法；`skills/intake_pipeline/4_mep/mep.md` **没有钉死规范名**（已核实）。

两条候选路（你选，并给出选择理由 + 实测支撑）：

- **(a) 代码同时拥有那 3 张时间表**（供暖设定点 / 供冷设定点 / 设备可用性）：
  用保留名，并把这 3 段 `Schedule:Compact` 一并确定性地并进 `schedule_specs`。
  ⚠️ 需处理：模型可能**另外**又写了自己的设定点时间表 ⇒ 会多出没人引用的孤儿时间表。
  **已核实：仓里没有「未被引用的时间表」这类检查**（`grep -i "unused|orphan|unreferenced"` 在
  `checks/mep.py` 与 `schedules.py` 上 0 命中）⇒ 孤儿**不会**打红任何门，但要在报告里如实说明。
  另外 `schedules.py` 的 day-type 完整性门会照常校验你生成的这 3 张 ⇒ 必须写成完整 day-type 形式。
- **(b) 代码从模型交出的 `schedule_specs` 里识别出这 3 张的名字再渲染**。
  ⚠️ 这等于把「哪张是供暖设定点」交给启发式判断 ⇒ 又回到「靠猜」，与本摊目的相悖。**我倾向 (a)。**

⛔ **不论选哪条，硬条件不变：渲染出的设备段引用的每一个时间表名，都必须存在于最终 `schedule_specs` 里。**
请为这条写一把独立的锁。

### 2.4 提示词同步（必须做，但**不作为防线**）

`skills/intake_pipeline/4_mep/authoring.md` 与 `pipeline.py::_build_mep_messages` 里
要求模型撰写 `hvac_specs` 的话必须撤掉/改写（否则模型继续白写一段被你丢弃的文本，浪费 token 且误导）。
⚠️ **提示词只是省 token，不是防线** —— 防线是「代码覆盖了那个字段」。⛔ 不许把「提示词已叮嘱」写进验收证据。

---

## 3. ⛔ 与摊 B 的硬接缝（改动前必须确认，变了就停）

摊 B 要加一道通用字段对齐检查，用户拍板的档位是**分档**：
**对「代码确定性生成的对象类型」阻塞，对模型自由撰写的部分只报告**。
摊 B 那份「阻塞名单」的初值就是 **§2.2 的两类**（`HVACTemplate:Thermostat` /
`HVACTemplate:Zone:IdealLoadsAirSystem`）。
⇒ **你若改了输出形态，摊 B 的名单当场作废** ⇒ **停下上报，不要自行改名单**（那是另一摊的面）。

---

## 4. 验收条件（⚠️ 已逐条核过可达性 + 互不冲突）

> 上一轮我犯过「只动这些文件」与「全仓必须绿」互相冲突的错误（第 16 次派工方题错）。
> 本单**不限制你改哪些文件**；请按需要改，并在报告里列出改了什么、为什么。

- **A1 防假验证自检（第一步就做）**：先证明你的验收路径**真的经过被改的代码**。
  最省的做法：把渲染函数中和掉（例如让它返回空串）⇒ 你的锁必须**变红**；恢复 ⇒ 变绿。
  **⛔ 锁不许通过 monkeypatch `run_mep` 来测**（仓里已有多处这么 stub 的测试，
  例：`tests/test_a8_evidence_routing.py:106`、`tests/test_checks_mep_assembly.py:790`）——
  那样测的是 stub，不是接线。**要 stub 就 stub `run_mep` 内部那次 LLM 调用**
  （`_call_json_llm`），让 `run_mep` 本体真的跑一遍。
- **A2 覆盖性锁**：让被 stub 的 LLM 返回一段**明显错误的 `hvac_specs`**（例如 accept_C 里那段 4 格文本，
  或干脆是垃圾字符串）⇒ 断言 `run_mep` 交出的 `hvac_specs` **与模型返回的无关**、逐字等于渲染器输出。
- **A3 两条路径一致**：断言 flow 路径与 `run_stage` 分段路径渲染出的文本**逐字相同**（含区顺序）。
- **A4 引用闭合**：断言渲染出的设备段引用的每个时间表名都存在于 `schedule_specs`（§2.3 硬条件）。
- **A5 门实测**：拿本摊产物跑 `check_mep`，`mep.hvac_schedule_refs` 必须 PASS；
  **且 18 道 mep 检查里不得有任何一条由 PASS 变成 FAIL**。
- **A6 全仓 pytest 绿**（默认 `-n auto`）：`N passed / 10 xfailed / 0 failed`，
  **报告里贴 rc 与汇总行**（⛔ 不许只说「跑过了」；`.rc` 文件名不许复用上一次的）。
- **A7 ⛔ 不许放宽或关闭任何现有门**来让验收通过。

---

## 5. 报告要写的（除常规 diff 说明外）

1. §2.3 你选了哪条路、为什么、孤儿时间表的实际数量。
2. §2.1 `run_stage.py` 那处 `set(...)` 你怎么改的。
3. **你自己判断没做到 / 没验证的事项**（本项目要求施工方自陈未验证项，历史上这一栏抓出过真缺陷）。
4. 若你认为 §2.2 的形态判断错了 —— 写清理由，**停下上报**，不要边改边做。
