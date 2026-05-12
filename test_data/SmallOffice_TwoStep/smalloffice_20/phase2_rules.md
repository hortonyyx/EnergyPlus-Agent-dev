# Phase 2 Rules — vector JSON → IntakeOutput（精简版）

> phase2 不看图。所有视觉信息已由 phase1 矢量化进 JSON。本文档专注**"矢量 JSON → IntakeOutput Pydantic"** 的推理 + 输出契约。
> 不读 `skills/energyplus_mcp/*.md`——那些文档里"如何读图"的部分对 phase2 无用，关键输出契约已在本文档复刻。

---

## 0. 输入 / 输出

### 0.1 输入

按目录读：
- **7 份 phase1 矢量 JSON**：`phase1_vector/{1f_view, 2f_view, 3f_view, South_view, North_view, East_view, West_view}.json`，schema 定义见 [vector_schema_v1.md](vector_schema_v1.md)
- **元信息**：`testdata_prompt.json`（楼层数、楼面积、建筑用途、城市等）

### 0.2 输出

一个 `IntakeOutput` Pydantic JSON，11 个字段：
- `building`、`site_location`
- `zone_specs`、`material_specs`、`schedule_specs`、`construction_specs`、`surface_specs`、`fenestration_specs`、`hvac_specs`、`people_specs`、`lights_specs`

9 个 `*_specs` 字段都是自然语言指令（**不是结构化数据**），供下游 9 个 subagent 读，必须可机械执行、内部一致。

### 0.3 误差预算

phase2 不看图 → 任何"图上数值"的错都已经被 phase1 锁定，**你只能引入纯推理误差**：
- 拓扑判错：哪个 zone 是走廊 / 哪面墙是外墙 / 哪扇窗属于哪面墙
- 字段格式错：命名不规范 / 跨字段引用不一致 / 模板写法 / 缺枚举
- 坐标翻译错：立面 x_local ↔ 世界坐标搞反

phase1 JSON 里 `null` 字段是"phase1 没看见"，**不要把 null 当 0 算**；缺失就在你的输出里相应地标注或拒绝建模。

---

## 1. 世界坐标系与立面翻译

### 1.1 全局坐标系

- 原点 = 整栋投影 SW 内角
- x 东向，y 北向，z 上向（地面 z=0）
- 单位米，两位小数

### 1.2 立面 local → world 翻译公式（sm_20 实例，按各 JSON 的 `facade_axis_note` 实际填）

phase1 已在 `phase1_summary.md` §3 给出 4 立面公式（直接套用，**不要自行重推**）：

- South: `X_world = x_local`, `Y_world = 0`, `Z_world = y_local`
- North: `X_world = 15 - x_local`, `Y_world = 8`, `Z_world = y_local`
- East:  `X_world = 15`, `Y_world = x_local`, `Z_world = y_local`
- West:  `X_world = 0`, `Y_world = 8 - x_local`, `Z_world = y_local`

15 / 8 是 sm_20 外包；其他 case 看对应立面 JSON 的 `scale_origin`。

---

## 2. 从 vector JSON 取关键量

### 2.1 外包尺寸

从任一 plan 的 `dimensions` 取总长链：`text="15.00", axis="x"` 是 W，`text="8.00", axis="y"` 是 D。

### 2.2 层高与楼层 z 范围

从任一 elevation 的 left/right 立面 y 总高链 + 分段链推：

- F1: z_floor = 0.00, ceiling_height = 3.60, z_top = 3.60
- F2: z_floor = 3.60, ceiling_height = 3.60, z_top = 7.20
- F3: z_floor = 7.20, ceiling_height = 4.80, z_top = 12.00

或等价：从某立面的 `strokes[pen=wall_fill]` 的 `y_range_m` 直接读（已分层）。两条路径必须互相一致；不一致就报告冲突，不要私自折中。

### 2.3 每层 plan 的 zone 拓扑

每张 plan JSON 的 `strokes[pen=wall]` 给出所有 wall centerline（2D 线段）。**zone = 这些线段围合的最小封闭多边形**。phase2 必须按几何围合判，不要按 ID 顺序判。

例（sm_20 1f）：10 根 wall stroke 围出 6 个房间 + 1 个走廊 = 7 zone（与 testdata `thermal_zones=7` 自洽）。

### 2.4 窗位

每张 elevation JSON 的 `strokes[pen=window]` 给出本立面所有窗的 local rect。通过 §1.2 公式翻回世界坐标，再按 `Y_world` 判属于建筑哪面外墙（North/South：Y=0 或 Y=8；East/West：X=0 或 X=15）。

`y_local` 直接 = `z_world`，不用翻译。

### 2.5 dimensions 的双向用法

dim 链既给坐标又给交叉校验：

- 直接用：read 数字作距离
- 校验用：strokes 端点坐标应与 dim 链积累一致（如 South_view F1 第二窗 x_range=[6.30,8.70] 应等于 dim 链 1.40+2.40+2.50=6.30 起，宽 2.40）。若不一致**信 dim**，stroke 坐标可能是 phase1 描摹偏移

---

## 3. IntakeOutput 字段推导顺序

按以下顺序产，避免后字段引用前字段时的命名漂移：

### Step 1 — `building`

从 testdata：name = `Smalloffice_20`（snake/camel mix 也行，无空格）、type = `Office`、num_floors = 3、total_floor_area_m2 = 360。

### Step 2 — `site_location`

从 testdata "Building location": "Shenzhen" → `city = "Shenzhen_CN"`（命名规则见 §5）、climate_zone 按地理常识或不填、weather_file = `Shenzhen.epw`（与 [.env](.env) `data/weather/Shenzhen.epw` 一致）。

### Step 3 — `zone_specs`

逐层逐 zone 显式列出，**严禁** `Floor_N_*` 模板写法。

命名约定（示例）：`F{1|2|3}_{方位|功能}` 如 `F1_S1` / `F1_Corridor` / `F2_S1` / `F3_North_Office`。所有 zone 名后续被 `surface_specs` / `fenestration_specs` / `hvac_specs` / `people_specs` / `lights_specs` 引用，必须**字面一致**（无大小写漂移、无加 `Zone_` 前缀的同/异写法）。

每个 zone 必须显式给：
- `x_range`、`y_range`（世界系，米）
- `z_floor`、`ceiling_height`
- 用途（office / corridor / etc.）

走廊也是一个 zone（不是 surface）。

### Step 4 — `surface_specs`

每个 zone 的 4 面 wall + 1 个 floor + 1 个 ceiling（顶层是 roof）。**逐 surface 显式列**，禁止模板写法。

外墙 / 内墙判断：
- 外墙 = 该 surface 位于建筑外包边界（plan 上属于外周 wall stroke 之一）→ `outside_boundary_condition = Outdoors`
- 内墙 = 该 surface 在两 zone 之间 → `outside_boundary_condition = Zone`，并显式给出 `adjacent_zone_name`

楼板 / 天花板：
- F1 floor → Ground（`outside_boundary_condition = Ground`）
- F2 floor = F1 ceiling → InterZone，配对（split-pairing 必须显式列每对，禁止"foreach"）
- F3 floor = F2 ceiling → 同上
- F3 ceiling = Roof（顶层）→ `outside_boundary_condition = Outdoors`，surface type = `Roof`

**Cross-floor split-pairing 必须显式枚举**（B1 hardened constraint），例：

```
- F2_S1.floor pairs with F1_S1.ceiling  [zone (F2_S1) ↔ zone (F1_S1)]
- F2_S2.floor pairs with F1_S2.ceiling
- ...
```

不要写 "F2 各 zone floor 对应 F1 同名 zone ceiling" —— 这是模板。

每个 surface 必须显式给：
- 4 vertex CCW from outside（zonetool_prompt 规则；本文档 §6 给出 4 立面 vertex 合成公式）
- construction name（参见 Step 6 占位）

### Step 5 — `material_specs` / `construction_specs`

材料 + 占位 construction：
- `Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window` / `Default_Floor` / `Default_Ceiling` / `Default_Roof` / `Default_GroundFloor`
- 玻璃用 `WindowMaterial:SimpleGlazingSystem`（**必须 standalone Construction**，不与 air gap / 第二片玻璃叠加，否则 EP 会 NaN fatal）
- 不透明 surface 用 simple stack（如 stucco + insulation + gypsum）

### Step 6 — `fenestration_specs`

每扇窗显式列：name / parent_surface_name / construction / 4 vertex CCW from outside / WWR 信息可选。

**parent surface mapping** 走 §2.4 公式：从 elevation 的 window stroke local rect → world rect → 落在哪面外墙 → parent_surface_name = 该外墙的 surface name。

**chain z 自检**：`z_max - z_min == sill 起算的窗高`，与 elevation 右侧 dim 链对账（schema §0.1 是 phase1 的事，phase2 拿到值后再校验一次）。

### Step 7 — `schedule_specs` / `people_specs` / `lights_specs` / `hvac_specs`

按 testdata `Building type = Office` 用 ASHRAE 90.1 Office 默认负载档：
- people: 10 m²/person，9-18 工作日 schedule
- lights: 10 W/m²，同 schedule
- hvac: IdealLoadsAirSystem，cooling 24°C / heating 20°C
- schedule: `Office_Workday` / `Office_Weekend` 等典型 schedule_compact

所有命名遵守 §5。

---

## 4. zone 围合 → 多边形 → vertex 合成

每个 zone 的 4 面墙在 plan 上是 4 条 wall centerline。CCW from outside 4 vertex 合成（顶视图，每面墙顺时针看是从 outside 看）：

| 面 | vertex 1 | vertex 2 | vertex 3 | vertex 4 |
|---|---|---|---|---|
| South wall (y=y_floor) | (x_min, y_min, z_top) | (x_max, y_min, z_top) | (x_max, y_min, z_floor) | (x_min, y_min, z_floor) |
| East wall (x=x_max) | (x_max, y_min, z_top) | (x_max, y_max, z_top) | (x_max, y_max, z_floor) | (x_max, y_min, z_floor) |
| North wall (y=y_max) | (x_max, y_max, z_top) | (x_min, y_max, z_top) | (x_min, y_max, z_floor) | (x_max, y_max, z_floor) |
| West wall (x=x_min) | (x_min, y_max, z_top) | (x_min, y_min, z_top) | (x_min, y_min, z_floor) | (x_min, y_max, z_floor) |
| Floor | (x_min, y_min, z_floor) | (x_max, y_min, z_floor) | (x_max, y_max, z_floor) | (x_min, y_max, z_floor) |
| Ceiling/Roof | (x_min, y_max, z_top) | (x_max, y_max, z_top) | (x_max, y_min, z_top) | (x_min, y_min, z_top) |

非矩形 zone 用同样的 CCW 原则但要 polygon vertex 多于 4 个；sm_20 全 rect，4 vertex 够。

---

## 5. 命名规则（强制）

字符集：仅字母 / 数字 / `_`。**禁**：空格、逗号、分号、连字符、斜杠、括号。

跨字段引用必须**字面一致**：
- `surface_specs` / `fenestration_specs` 里的 construction 必须在 `construction_specs` 出现
- `hvac_specs` / `people_specs` / `lights_specs` 里的 schedule 必须在 `schedule_specs` 出现
- `surface_specs` / `fenestration_specs` / `hvac_specs` / `people_specs` / `lights_specs` 里的 zone 必须在 `zone_specs` 出现

合法例：`Shenzhen_CN` / `Zone_F2_C` / `Window_Office_South_1`
非法例：`Shenzhen, China` / `Zone F2 C` / `Wall-01`

---

## 6. 不允许的写法

- ❌ `Floor_N_*` 模板 / `for N in 2..5` / `typical floors` / `repeat for upper floors`
- ❌ `TBD` / `same as above` / `see above` / `etc.` / `...`
- ❌ 跨字段命名漂移（`Zone_F1_S1` vs `F1_S1` vs `zone_f1_s1`）
- ❌ surface_specs 写"F2 各 zone floor 对应 F1 ceiling"——必须逐对枚举
- ❌ fenestration_specs 不给 parent_surface_name 或不给 CCW vertex
- ❌ SimpleGlazingSystem 与 air gap / 第二片玻璃同 Construction 叠加（EP 必 fatal）

---

## 7. 自检清单

产 IntakeOutput 后，逐项过：

- [ ] 11 字段齐
- [ ] 所有 zone 显式枚举（无模板写法），逐层 zone 数与 testdata `thermal_zones` 自洽（sm_20 = 7+8+4 = 19）
- [ ] 所有 surface 逐 zone 显式枚举（每 zone 4 wall + floor + ceiling/roof）
- [ ] cross-floor split-pairing 逐对枚举
- [ ] 所有 fenestration 给 parent_surface_name 且映射回有效外墙 surface name
- [ ] 跨字段引用字面一致（construction / schedule / zone）
- [ ] 命名字符集合法
- [ ] WWR 自检（南 3 窗 × 2 层 × 2.40×1.80 / 北 3 窗 F1 + 4 窗 F2 + 1 通长窗 F3 / 东 西各 1 个 F3 小窗）每个立面外墙面积匹配
- [ ] z 值连续无 gap：F1 ceiling 顶 = F2 floor 底 = 3.60，F2 ceiling 顶 = F3 floor 底 = 7.20

---

## 8. 与现有 skills 文档的关系

本文档替代 phase2 任务对 `skills/energyplus_mcp/*.md` 的依赖。三份文档原本承担三类职责：

| 原 skill 文档 | 关于"读图"的部分 | 关于"输出契约"的部分 |
|---|---|---|
| `energyplus_mcp_prompt.md` | §D 全章（D1-D6 图纸识别 / 全局坐标 / 立面 chain）| §Mandatory Internal Derivation Order |
| `intake_output_contract.md` | 无 | 全文（命名 / 无模板 / cross-floor split-pairing / fenestration chain）|
| `zonetool_prompt.md` | §如何看立面识窗 | §CCW vertex synthesis 表 |

phase2 用矢量 JSON 后，所有"读图部分"作废；"输出契约部分"的精华已浓缩进本文档 §3-§7。zonetool 的 vertex 合成表见本文档 §4。

如果跑 phase2 时发现本文档未覆盖某条原 skill 强约束，请在输出末尾追加 `phase2_followup_notes` 字段记录，便于后续补本文档。
