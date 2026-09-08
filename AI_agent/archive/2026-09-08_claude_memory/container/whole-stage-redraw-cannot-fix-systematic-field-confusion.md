---
name: whole-stage-redraw-cannot-fix-systematic-field-confusion
description: 4_mep 把对象类型名填进时间表名那一栏，14 个区每次全错、整段重抽三次全败——重抽治不了系统性倾向，只有「让它填不错」
metadata: 
  node_type: memory
  type: project
  originSessionId: cc9a6b0d-6528-4c5f-a729-647c4bb3c4a6
  modified: 2026-08-14T02:43:45.883Z
---

2026-08-13 验收第 3 次跑（`run_2026-08-13_accept_C`）失败的根因，**同日前两次跑同一输入却一次就过**
⇒ 该段是**间歇性的**，但**每次错起来是系统性的**。

**现场**：`mep.hvac_schedule_refs` 报「14 个 HVAC 时间表引用未定义」。
**⛔ 但那是症状不是病因** —— 4_mep 交出的 `hvac_specs` 是 **LLM 手写的原始 IDF 文本（位置敏感）**，
模型给 `ZoneControl:Thermostat` **只写了 4 格**（Name / Zone / `ThermostatSetpoint:DualSetpoint` / 名字），
而 EP 要 **5 格**（Name / Zone / **Control Type Schedule Name** / Control 1 Object Type / Control 1 Name）
⇒ **漏掉「控制类型时间表」那一格、其后全部前移一位** ⇒ 对象类型名落进时间表那一栏。
⭐ **所以不是「填错值」，是「漏一格导致整行位移」。**

⭐ **关键观察：14 个区每次全错、连错三次** ⇒ 不是随机故障，是**对字段语义的系统性误解**。
⇒ **段级「整段重抽 N 次」治不了它** —— 同一个模型 + 同一份输入 + 同样的错法，抽三次得到同样的答案，
只是把 draw budget 烧完然后 `quarantined`（退出码 20）。

⭐ **修法方向 = 让它填不错**（该字段的取值由管线约束或确定性生成 / 只给受限选项），
⛔ **不是加重试、也不是在提示词里叮嘱**。
与 [[model-visible-but-not-its-business]] 同源：**有效修法是「让它做不到」，不是「告诉它别这么做」**。

✅ **门本身工作正常**（值得记，避免下次误伤）：`block=1` 拦住残缺配置不让流到下游，
用尽 3 次重抽预算后走 `quarantined` **停下等人**而非无限重试。

⭐ **同一天该段还有第二种病**：`mep.idf_parse` 崩在裸 `TypeError: unsupported operand ... '//' ... NoneType`
（LLM 输出某字段为 None，解析器崩而非结构化拒绝），**靠段级重试自愈** ⇒
在一次「全绿」的跑里没人看得见。⇒ 两种病都指向 **4_mep 需要专门收拾**。

⚠️ 三次跑的 **2_modelling 顶点全部 400+60 逐位同序全同** ⇒ **不稳定的从来不是几何，是 LLM 段的输出质量**。

## ⛔⛔ 由此露出的架构级缺口（比这一处重要）

- **全仓零字段个数/对齐校验**：`validator/idf_fragments.py` 与 `checks/mep.py` 中
  `arity`/`field_count`/`expected_fields` **命中数为 0**（08-14 复核仍成立）；
  mep 检查**全是语义检查**（08-14 实数 = **18 个** check id，此前记的「19 道」是错的，不影响结论）。
  ⇒ **漏一格能否被发现，取决于移过去的值恰好长得像不像错的**。
  **⛔⛔ 2026-08-14 更正：~~「若移位后的值恰好合法 ⇒ 全门绿 + EP 正常算完 + 结果是错的」~~ ——
  这句在今天的下游路径上【不成立】，已实测证伪。** 详 [[artifact-severity-depends-on-real-consumer]]：
  `*_specs` 文本**从不被贴进最终 IDF**，下游用**具名参数的 MCP 工具**重建
  ⇒ **F-28 的真实危害是「链路被门拦死」（可靠性），不是静默算错物理。**
  （这不改修法方向 —— 让它填不错仍然对；改的是**危害定级**与**新门该上什么档位**。）
- **⛔ 已中过一次**：`checks/mep.py:566` 注释逐字写着「**不是缺时间表**（见 `mep.people_field_alignment`）」
  ⇒ People 上发生过同一类错，对策是给**那一个对象类型**加专用对齐检查 ⇒ **打地鼠**。
- **✅ 通用防线很便宜**：仓里已有 IDD 元数据（`data/dependencies/Energy+.idd` + `data_model.py:IDDField`）
  ⇒ 「每种对象几格、哪格必填」的权威数据本就在手边，**通用对齐门无需逐类型手写规则**。
- ⭐ **判别问法**：**「这道门报的是症状还是病因？病因那一层有门吗？」**
  引用存在性检查只在「移过去的值不像合法值」时才碰巧抓到位移。
