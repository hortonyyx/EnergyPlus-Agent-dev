# M2 · 三道小门 + 批次零卫生(执行简报,待 Codex 方案审)

> 缘起:Fable5 体检 D2-1/D2-2/D2-3 + D1-1/D1-2(`AI_agent/logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md`)。
> 分工:Claude 出简报 → Codex 方案审(xhigh)→ Claude 裁决 → Codex 执行 → Claude 复核。
> 纪律:改 src/skills/tests 前备份 `backup/{src,Skill}_history/2026-07-06_m2_gates/`;零 golden 改动(见 §2 特别验证);零契约改动。

## 1. 四件事

### 1a. D2-1:尺寸链闭合容差对齐 A0(50mm→10mm 命名常数)
- 现状:A0 §4 定 `DIMCHAIN_CLOSE_TOL=10mm`;`src/validator/checks/reading.py:669` 硬编码 `> 0.05`(50mm),`reading.py:45` 注释误导性声称对齐 A0。
- 修法:引入命名常数 `DIMCHAIN_CLOSE_TOL_M = 0.010`(注释指 A0 §4),替换字面量;修正 :45 误导注释。
- **前置实证(执行第一步,先做再改)**:扫全部 `case_tests/**/0_reading/*_view.json` 的链闭合残差分布,报告落在 (10mm, 50mm] 区间的条数——该区间是本次收紧唯一新增 flag 面。若现有 anchor/golden run 有链落此区间,**停下来报告**(连同 legacy 祖父化是否豁免它们的判断)再定,不擅自继续。
- 语义注意:闭合属 evidence 债类(exploratory=flag/golden=block,legacy 祖父化)——收紧不应打破任何现有 legacy golden;执行时验证。

### 1b. D2-2:`mep.construction_thermal_mass` 门(全 NoMass 包络,EP 崩溃类)
- 现状:`authoring.md:58-67` hard 规则;`mep.py:497-512` 只查 NoMass 热阻为正,不查"不透明 construction ≥1 层有质量材料"。2026-06-11 audit 实测发生过全 no-mass draw。
- 修法:check_mep 新增 check_id `mep.construction_thermal_mass`:对每个**不透明** CONSTRUCTION(定义=不含任何 `WindowMaterial:*` 层),要求 ≥1 层是 `MATERIAL`(非 `Material:NoMass`/`Material:AirGap`)。层级=INVARIANT(与 schedule_completeness 同类,EP 正确性硬需求)。
- 边界:纯 WindowMaterial construction(SimpleGlazing standalone)跳过;`Cons_InterFloor` 等内部面构造**纳入**(同属不透明)。

### 1c. D2-3:恒温器/理想负荷 schedule 引用门(S4-07 同清单漏叶)
- 现状:`mep.py:40` `_LOAD_TYPES` 只走 PEOPLE/LIGHTS/ELECTRICEQUIPMENT;`authoring.md:115-121` 六项必需 schedule 清单中 thermostat heating/cooling setpoint 与 ideal-loads availability 三项无引用校验(对象已被 `idf_fragments.py` 解析进索引,只差走一遍)。
- 修法:扩 `_load_refs` 或加 sibling:`ZoneControl:Thermostat` / `ThermostatSetpoint:DualSetpoint`(heating/cooling setpoint schedule 名)、`HVACTemplate:Zone:IdealLoadsAirSystem`(availability 等 schedule 字段)——**非空引用必须存在**于 SCHEDULE:COMPACT 集;字段留空且 IDD 允许空 → pass(别把合法可选空当 missing);authoring 清单要求"必须存在"的对象缺席 → 按既有 missing 语义报。report id 沿用 `mep.load_to_schedule` 家族或新 id,执行者按现有命名规约定。

### 1d. 批次零卫生(顺批)
- `pyproject.toml`:`ezdxf`、`python-dotenv`、`openai`、`attrs` 提为直接依赖(体检 D1-2:ezdxf 完全不在 uv.lock;其余三个仅传递可达但被生产代码直接 import——`src/agent/llm.py:5`、`src/agent/pipeline.py:41`、`src/rag/vector.py:5`);同步 `uv lock`(**只加新条目,不升级既有 pin**——lock diff 里如出现无关升级即停)。`click`/`aiohttp` 零 import——**确认无 entry-point/插件式用法后删除**,拿不准就留着并在简报回执里说明。
- 删除仓库根残缺 `.venv`(numpy 损坏,gitignored,权威环境=/opt/venv,Dockerfile:48-51)。

## 2. 验收
- 1b/1c 各配正负测试;1a 配"49mm 不闭合被抓"回归测试。
- **零 golden 特别验证**:对现有 anchors 的 `mep_output.json`/reading 产物离线跑新检查,确认无 retroactive 失败;若某 anchor 挂新门(如历史 mep 恰好全 NoMass),**停下来报告**并给降级选项(INVARIANT→CROSS_CHECK flag),不擅自改 anchor。
- 全量 pytest 绿;`uv sync` 干净环境可解析 ezdxf(能 import 即可,不跑 DXF 工具)。

## 2b. 裁决(2026-07-06,Codex 审 APPROVE-WITH-CHANGES,5 findings 全采纳,本节为定案)

1. **1a 定案**:实证扫描 (10mm,50mm] 区间 **0 条**→收紧免费,直接落 `DIMCHAIN_CLOSE_TOL_M = 0.010` 命名常数+修 :45 误导注释;祖父化路径已确认(evidence 类,legacy_migrated flag)。
2. **1c 缩范围定案(finding 1/3,golden-neutral 是硬约束)**:只做「**非空 schedule 引用必须可解析**」(空=pass,**不**强制 IDD-required 存在性——anchors 的 ZoneControl A3 留空是常态);对象覆盖表按 finding 2:`ZoneControl:Thermostat`、`ThermostatSetpoint:DualSetpoint`(+单 setpoint 变体)、`ZoneHVAC:IdealLoadsAirSystem` **和** `HVACTemplate:Zone:IdealLoadsAirSystem`、`HVACTemplate:Thermostat`,用 `raw.<Field_Name>` 表驱动;**本批只验主 availability 字段+setpoint schedule 字段,heating/cooling availability 字段 defer**(旧 run 存在字段错位会 retro-fail,记 backlog:「anchors 中发现错位 HVAC fragment」)。执行时对全部现存 run 目录做信息性预扫并把"哪些旧 run 会新挂"写进执行日志(不改 anchor)。
3. **1b 定案(finding 4)**:opaque=CONSTRUCTION 且无任何 `WINDOWMATERIAL:*` 层;要求 ≥1 层解析为**恰好 `MATERIAL`**(NoMass/AirGap/InfraredTransparent 均非质量层);`Construction:AirBoundary` 不在 `of_type("CONSTRUCTION")` 内,helper/测试点名防未来越界。预扫:8 个 anchor MEP 全过;smalloffice_23(legacy 非 anchor)会新挂——执行时确认无测试依赖它的 mep 通过性。
4. **1d 定案(finding 5)**:加 `ezdxf`/`python-dotenv`/`openai`/`attrs`(注意 import 名 `attr`)四个直接依赖,删 `click`/`aiohttp`(click 经 typer 传递仍在);裸 `uv lock` 后审 diff,出现无关升级即停。`.venv` 删除由主控亲手做,不在本批。
5. 执行时只跑目标测试(全量 suite 主控合流后统一跑)。

## 3. 审阅需求
1. 1b"不透明"定义是否有漏(air boundary/特殊构造?);
2. 1c 各对象的 schedule 字段名/IDD 可选性核对(别把可选空报成 missing);
3. 1a 收紧的祖父化路径确认;
4. pyproject 改动对 uv.lock 的最小 diff 路线;
5. click/aiohttp 删除安全性。
