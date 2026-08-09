# E4 探针结果:GlobalGeometryRules World→Relative + Zone Origin 归零 + Building North Axis=θ

**验证方案**:`GlobalGeometryRules.Coordinate System` 从 `World` 切到 `Relative`,配合 `Building.North Axis=θ`(0/90/270),对比 EnergyPlus 25.1.0(ExpandObjects 展开后)输出的 `eplusout.eio` / `eplusout.err`,确认几何等价性与告警行为符合预期。

## 核对方法(一句话)

用 `! <HeatTransfer Surface>` / `! <Zone Information>` 头行动态定位 `Azimuth {deg}` / `Floor Area {m2}` / `Volume {m3}` 列号(非硬编码位置),按 `Surface Name` / `Zone Name` 跨四个变体逐条对账;`eplusout.err` 用字符串精确匹配目标告警行。

## 输入 sanity(供参考,非五条之一)

| 变体 | GlobalGeometryRules.Coordinate System | Building.North Axis |
|---|---|---|
| out_world_000 | World | 0 |
| out_rel_000 | Relative | 0 |
| out_rel_090 | Relative | 90 |
| out_rel_270 | Relative | 270 |

四个变体 `eplusout.eio` 中 `HeatTransfer Surface` 行数均为 **114**(Wall 64 / Window 14 / Floor 18 / Roof 18,来自 world_000 的类别拆分,四变体一致),`Zone Information` 行数均为 **14**,表面名称集合与区名称集合四变体完全相同(集合相等校验通过)。窗户(Surface Class=`Window`)在 eio 里**未单独成表**,与其宿主墙一起列在同一张 `HeatTransfer Surface` 表内(用 `Surface Class` 列区分),因此对账口径已覆盖 fenestration,无需另起一路;本次两个模型均无 `Frame/Divider Surface`、`Shading Surface` 数据行(表存在但 0 行)。

## 逐条结论

### 1. rel_000 每个表面 Azimuth == world_000 同名表面 Azimuth(几何不变形)
**PASS**。114 个表面全部按名称配对,114/114 完全相等(容差 1e-6°),0 处不一致。

### 2. rel_090 每面 Azimuth == (rel_000 同面 Azimuth + 90) mod 360
**PASS**。114/114 全部满足(容差 1e-3°),0 处不一致。

### 3. rel_270 每面 Azimuth == (rel_000 同面 Azimuth + 270) mod 360
**PASS**。114/114 全部满足(容差 1e-3°),0 处不一致。

### 4. 四变体 Zone Information 的 Floor Area 与 Volume 全部一致
**PASS**。14 个区 × 3 组变体对(world_000 分别与 rel_000/rel_090/rel_270 比较)= 42 对逐一核对,Floor Area 与 Volume 均完全相等(容差 1e-6 m²/m³),0 处不一致。

*(附带观察,非该条判据:`Zone Information` 里的 `North Axis {deg}` 列在四个变体中均恒为 `0.0`——这是 Zone 自身的 `North Axis` 字段〔本模型未对任何 Zone 单独设置〕,不同于 `Building.North Axis`;EnergyPlus 把 Building 层的旋转直接体现在表面 Azimuth 上,不回写到这一列,属预期行为,不视为异常。)*

### 5. eplusout.err 告警行为
**PASS**。
- `out_world_000/eplusout.err`:命中 1 次 `"GetSurfaceData: World Coordinate System selected.  Any non-zero Building/Zone North Axes or non-zero Zone Origins are ignored."`(以及配套的 `GlobalGeometryRules: Potential mismatch of coordinate specifications...` 告警,同一根因)。
- `out_rel_000` / `out_rel_090` / `out_rel_270` 的 `eplusout.err`:命中 **0** 次该告警行,三者均不含。
- 三个 Relative 变体的告警总数均为 3(Timestep 默认 / SizingPeriod 缺失 / Ground Temperature 缺失,与坐标系无关的共性告警),world_000 为 5(多出上述两条坐标系相关告警)。

## 总表

| 条目 | 判据 | 结果 | 核对数 | 不一致数 |
|---|---|---|---|---|
| 1 | rel_000 Azimuth == world_000 Azimuth | PASS | 114 | 0 |
| 2 | rel_090 Azimuth == rel_000 Azimuth + 90 (mod 360) | PASS | 114 | 0 |
| 3 | rel_270 Azimuth == rel_000 Azimuth + 270 (mod 360) | PASS | 114 | 0 |
| 4 | 四变体 Zone Floor Area / Volume 一致 | PASS | 42 对 | 0 |
| 5 | world_000 独有 "ignored" 告警,三个 rel 变体皆无 | PASS | 4 个 err 文件 | 0 |

**结论**:`GlobalGeometryRules: World→Relative + Zone Origin 归零 + Building.North Axis=θ` 方案在本探针数据上完全验证通过——几何(逐面 Azimuth、逐区 Floor Area/Volume)在旋转下保持刚体不变形且按预期偏转,坐标系相关告警按方案预期消失。
