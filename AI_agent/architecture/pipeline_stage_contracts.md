# 管线子流程契约（子流程 ↔ skill ↔ 中间产物）

> **权威接线参考，2026-06-09**（partA 三段解耦落地后）。本文取代 [architecture.md](architecture.md) 的「管线」部分——后者仍描述 2026-05-06 单步 intake，已失真。
>
> 用途：明确每段子流程**喂哪些 skill、读什么输入、产什么中间产物、谁消费**；锁定不可破的边界（规范不变量）；列出规范必须解决的接缝缺口（喂[识图建模主线 §7](../capability/recognition_modeling_capability.md) 优先级 #2）。
>
> **范围**：本项目侧 = 识图 → 校正 → 几何（造面+切配）→ 物理 → 装配 → 产 `IntakeOutput`。下游 9 subagent / cross_ref / validate 的 **prompt 演进归协作者**（本地有代码可跑）；切配确定性内核（互逆配对）见 [split_pairing_kernel_reference.md](../reference/split_pairing_kernel_reference.md)。
>
> **术语对照（2026-06-10 改名后）**：本文部分段落沿用旧称——**phase1 = 0_reading（识图）**，**phase2a = 1_correction（校正）**，**core = 确定性核（1_correction 内）**，**phase2b 几何 = 2_modelling + 3_split_pairing（代码内核）**，**phase2b 物理 = 4_mep**，**phase2b 装配 = 5_intakeoutput**。代码模块 `src/agent/pipeline.py`（`run_pipeline` 编排 + `run_correction` + `run_mep`）。

---

## 0. 子流程链总览

> **更新（2026-06-09，0–5 重构 Step 2–6 落地）**：phase2b 已**解耦**——几何走确定性内核（建模+切配），物理走 4_MEP（LLM），装配走 5_intakeoutput（确定性）。下图为当前实态；下方 §0.1 的目标架构对矩形情形已落地。

```
 actor         stage                    输入                         产物
─────────────────────────────────────────────────────────────────────────────
 半人工/VLM    0_reading 识图        建筑图 + testdata          0_reading/*.json
               (image-bound)                                    + reading_summary.md
                  │
                  ▼
 LLM           phase2a 校正          vectors + 1_correction(A0–A4) CorrectedGeometry
               (image-blind)                                    (1_correction/correction_geometry.json)
                  │
                  ▼
 代码          core   确定性核        CorrectedGeometry           snapped CorrectedGeometry
               (no LLM)              + A0 容差 registry          (1_correction/..._snapped.json)
                  │
                  ▼
 代码          2_modelling+3_split_  snapped CorrectedGeometry    BuildingGeometry → 序列化
               _pairing 几何内核      (kernel build + 切配)        zone/surface/fenestration_specs
               (no LLM)                                          (2_modelling/3_split_pairing/)
                  │
                  ▼
 LLM           4_mep 物理            zone 列表 + 必需 construction 集 material/construction/schedule/
               (image-blind)        + 4_mep/authoring.md+mep.md   people/lights/hvac + building/site
                  │                                              (4_mep/mep_output.json)
                  ▼
 代码          5_intakeoutput 装配    geometry specs + MEP specs   IntakeOutput + 契约校验
               (no LLM)                                          (5_intakeoutput/intake_output.json)
                  │
   ══════════════ 本项目侧契约边界：IntakeOutput（11 字段，不变）══════════════
                  ▼
 下游(协作者)  9 subagent + cross_ref + validate    IntakeOutput → 装配好的 IDF（几何被忠实誊写）
                  │
                  ▼
 代码          InterZone 门          IDF → pass/fail（EP 前 fail-fast）
                  ▼
               simulate              IDF → EnergyPlus 结果
```

实现：编排在 [src/agent/pipeline.py](../../src/agent/pipeline.py) `run_pipeline`（被 `intake_node` 与 `run_pipeline_deepseek.py` 薄包装共用）；确定性核 [correction/deterministic.py](../../src/agent/correction/deterministic.py)；几何内核 [geometry/](../../src/agent/geometry)（`modelling.py` 造面 + `split_pairing.py` 切配 + `specs.py` 序列化）；4_MEP 段 `run_mep`；装配 [intakeoutput.py](../../src/agent/intakeoutput.py)（`assemble_intake_output` + `validate_contract`）；InterZone 门 [interzone.py](../../src/validator/interzone.py)。**fork (a)**（用户 2026-06-09 定）：几何序列化成 `surface_specs` 文本、下游 surface_agent 忠实誊写；fork (b)（确定性直接造面绕过下游）记录待后续整合再议。内核 build 硬错时直接 raise（几何是确定性必需品，硬错=bug 应修，**不再有 LLM 回退**；旧 `run_phase2b` 已删、`rules.md` 已退役归档 Skill_history）。

> **口径统一（一物多名，2026-06-09）**：同一个「内部边界面之间的对应关系」在不同层有不同叫法，等价——
> - **切配** / **split-pairing**（口语 / 概念）= 把相邻 zone/层之间一对多的面，切成 EP 要求的逐面一对一 + 互逆引用。
> - `surface_specs` 里写作 `adjacent_zone` / `adjacent_surface`（哪个 zone、哪个对面面）。
> - IDF / EnergyPlus 里是 `Outside_Boundary_Condition = Surface` + `Outside_Boundary_Condition_Object`（互逆指向对面面）。
> - 代码内核里是 `Surface.obc = "Surface"` + `obc_obj`（[split_pairing.py](../../src/agent/geometry/split_pairing.py)）。
> 三者是同一件事的三种表述；**EnergyPlus 没有 `Zone` 边界条件**，写 `OBC=Zone` 是 severe。

> **【未来架构标记，不急落】4_MEP 再拆 phase3（MEP 撰写分段）**：4_MEP 现一步出全部 8 个非几何字段。设想进一步拆 material/construction（结构）与 schedule/people/lights/hvac（荷载）。等 mep.md 扩成真先验库后再落。

### 0.1 目标总架构（2026-06-09 用户定调）— 几何彻底确定性化

当前 phase2b 一步出全部 specs（含几何造面 + 切配 = LLM 做）。**目标**把几何从 LLM 手里全部收进代码：

```
识图        校正                  建模·几何模型      切配·仿真模型       物理信息挂载       下游·产品组装
phase1      phase2a判断 + 确定性核  cells→zones+面     面切分+互逆配对      材料/时间表/HVAC    9 subagent
(LLM/VLM)   (LLM + 代码)          (确定性·待建)       (确定性·待建)        (LLM/模板)         (确定性装配)
感知         CorrectedGeometry     几何建筑模型        EP合法仿真几何        物理信息挂上         IDF + EP
```

**一刀切分原则**：**LLM 只做 感知（识图）+ 校正判断 + 物理语义挂载；代码做 所有几何（建模 + 切配）+ 装配。** 「建模·几何」（cells→zones+墙/楼板/天花面 + OBC 判定 + 顶点合成）与「切配·仿真」（跨层/邻区面切分 + 互逆配对）都收进**确定性造面/切配内核**（核之后、吃 cells），整块吃掉 `rules.md`（已退役，归档 Skill_history） §4/§2.6 + [surface.py](../../src/agent/nodes/surface.py) 的脆弱几何指令。产出**已完整解析的 surface_specs**，下游 surface_agent 退化成忠实誊写——**`IntakeOutput` 契约不变、下游代码不动**。

**触发证据**：sm20/sm21 对照（[split_pairing_kernel_reference §2.5](../reference/split_pairing_kernel_reference.md)）——一步出 LLM 切配做得对、staged 退化，证明几何造面/切配是确定性活儿不该交 LLM。

**落地状态（2026-06-09，0–5 重构 Step 2–6）**：✅ **矩形情形已落地**——几何内核 [geometry/](../../src/agent/geometry)（`modelling.py` 造面 + `split_pairing.py` 切配，shapely 多边形原生）接进 `run_pipeline`，序列化成 `surface_specs`，4_MEP 只剩物理语义，5_intakeoutput 确定性装配。LLM 已不碰几何。`IntakeOutput` 契约不变、下游不动（fork a，下游誊写）。**待实现**：非矩形（L/U、退台）内核已 polygon-native 可吃，但端到端非矩形 case 随 B5 验证；e2e 实测（sm21_pre）= Step 8。

---

## 1. 逐段契约

### 0_reading — 识图（image-bound，半人工 Opus 子代理 / 未来 VLM）
- **职责**：把每张图 retrace 成语义矢量 JSON；**只识别、不做拓扑推理**（拓扑全留给 phase2）。
- **喂的 skill**：[0_reading/guide.md](../../skills/intake_pipeline/0_reading/guide.md)（主指导：误差预算 / 全局约束 / 输出容器 / 纪律）+ [0_reading/reading_guide.md](../../skills/intake_pipeline/0_reading/reading_guide.md)（识别：一个 mark 是什么类别）+ [0_reading/pen_library.md](../../skills/intake_pipeline/0_reading/pen_library.md)（动作：类别→画笔/路由/忽略登记/healing）。三文档分工：`reading_guide` 认类别 → `pen_library` 定动作 → `guide` 管流程容器。
- **输入**：建筑图（多张）+ `testdata_prompt.json`。
- **产物**：`<case>/0_reading/` 下 `Nf_view.json`（楼层平面）/ `*_view.json`（立面）/ supp / `reading_summary.md`（含 §3 立面 local→world 翻译公式）。
- **消费者**：phase2a。

### 1_correction — 校正（image-blind，LLM）
- **职责**：把感知基元（可能有噪声/自相矛盾）变成干净、自洽、仿真友好的几何基元，记录每处实质改动。A1 中线归一+z-stack → A2 规范轴集+吸附+链闭合 → A3 仲裁补全（A4 先验仅在 A0/A3 门控下用）。
- **喂的 skill**：[1_correction/](../../skills/intake_pipeline/1_correction) 全部 5 篇（README + A0 契约 + A1 坐标归一 + A2 规范化 + A3 仲裁 + A4 先验）作 RULE DOCUMENT；phase1 的 `guide.md` + `pen_library.md` 作 REFERENCE（理解矢量基元含义，**不含** reading_guide——那是 phase1 专用）；`reading_summary.md` 作 REFERENCE。
- **输入**：phase1 全部矢量 JSON + testdata + 可选 `feedback`（validate→intake 回修时路由到此段）。
- **产物**：`CorrectedGeometry`（矩形 cells + windows + per-floor z + audit `corrections/conflicts/unsupported`），物化为 `correction_geometry.json`。
- **边界**：**只产几何基元，不产 zones/surfaces**（system prompt 硬约束）。

### core — 确定性核（代码，无 LLM）
- **职责**：建全局规范轴集，把每个 cell/window/footprint 边吸附上去 → (1) 同墙跨层字节一致（消跨层抖动）；(2) 任意两规范轴不近于 `MIN_EDGE_LENGTH`（结构性杜绝退化碎片，EP 输入段错类不可能发生）。**消碎片 ≠ 保正确**：吸附去裂缝但留错布局，几何正确性是判断层（phase2a/A3）的事。
- **喂的 skill**：无（常数应取 [A0 §4 容差 registry](../../skills/intake_pipeline/1_correction/A0_contract.md)）。
- **输入**：`CorrectedGeometry`。
- **产物**：snapped `CorrectedGeometry`（`correction_geometry_snapped.json`）+ `corrections.json`（2a + core 合并 audit）。
- **消费者**：phase2b（读 snapped）；`corrections.json` 当前仅 sidecar（见 §3 缺口 5.4）。

### 2_modelling + 3_split_pairing — 几何内核（代码，无 LLM）
- **职责**：从 snapped `CorrectedGeometry` 确定性造出全部几何面并切配。`modelling`：cell→zone 体块 + 面顶点合成（外法向、CCW-from-outside）；`split_pairing`：同层内墙互逆配对 + 跨层楼板/天花切分配对 + roof/ground + 窗挂外墙。`specs.serialize_geometry` 把 `BuildingGeometry` 序列化成 `zone_specs`/`surface_specs`/`fenestration_specs` 文本 + `used_constructions` 集（construction 按面型/OBC 定，互逆面同名 `Cons_InterFloor`）。
- **喂的 skill**：[2_modelling/spec.md](../../skills/intake_pipeline/2_modelling/spec.md) + [3_split_pairing/spec.md](../../skills/intake_pipeline/3_split_pairing/spec.md)（code-of-spec，非 LLM prompt）。
- **输入**：snapped `CorrectedGeometry`。
- **产物**：3 个几何 spec 文本 + `used_constructions`（喂 4_MEP）；物化 `building_geometry.json` / `geometry_specs.md`。

### 4_mep — 物理信息撰写（image-blind，LLM）
- **职责**：只产非几何的 8 个字段——`building`/`site_location` + `material`/`construction`/`schedule`/`people`/`lights`/`hvac_specs`。必须定义 `used_constructions` 里每个 construction（否则面挂不上、EP fatal）。
- **喂的 skill**：[4_mep/authoring.md](../../skills/intake_pipeline/4_mep/authoring.md)（撰写规则）+ [4_mep/mep.md](../../skills/intake_pipeline/4_mep/mep.md)（默认值）。
- **输入**：testdata + 序列化的 zone 列表（取 zone 名写 per-zone people/lights/hvac）+ 必需 construction 集 + 可选 `feedback`。
- **产物**：`MepOutput`（8 字段，`4_mep/mep_output.json`）。

### 5_intakeoutput — 装配（代码，无 LLM）
- **职责**：把 3 个几何 specs + 8 个 MEP 字段机械拼成 `IntakeOutput`，跑确定性契约校验（每个 `used_constructions` 必须在 `construction_specs` 里被定义，逐 token 严格匹配；缺则 raise）。
- **输入**：geometry specs + `MepOutput`。
- **产物**：`IntakeOutput`（`5_intakeoutput/intake_output.json`）——**本项目侧交接契约（11 字段不变）**。
- **硬错处理**：内核 build 硬错 `run_pipeline` 直接 raise（无 LLM 回退；旧 `run_phase2b` + `rules.md` 已删/归档）。

### downstream — 9 subagent + cross_ref + validate（协作者维护 prompt）
- **职责**：`IntakeOutput` → 装配 IDF。
- **喂的 skill**：各下游节点 prompt（在 [src/agent/nodes/*.py](../../src/agent/nodes)，**协作者维护**）。
- **InterZone 门**：装配后、EP 前 fail-fast（OBC=Surface 目标存在/互逆/单一引用/面积/反法向/共面/最小边长，+ 非法 OBC 守卫含 Zone）。
- **产物**：IDF → EP 结果。

---

## 2. skill ↔ 子流程矩阵

| skill 文档 | phase1 | phase2a | core | 几何内核(2_3) | 4_mep | 5_intakeoutput | 下游 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 0_reading/guide.md | ●主 | ○参考 | | | | | |
| 0_reading/reading_guide.md | ●主 | | | | | | |
| 0_reading/pen_library.md | ●主 | ○参考 | | | | | |
| 1_correction/A0–A4 + README | | ●规则 | (常数源) | | | | |
| 2_modelling/spec.md + 3_split_pairing/spec.md | | | | ●code-of-spec | | | |
| 4_mep/authoring.md + mep.md | | | | | ●规则 | | |

| 下游各节点 prompt（src/nodes/*.py） | | | | | | | ●协作者 |

`●主`=该段主规则；`○参考`=背景理解喂入；`●code-of-spec`=非 LLM prompt，是代码内核的规格文档；`(常数源)`=应作单一真源被代码读取（A0 registry，5.1 已接）。

## 3. 中间产物 ↔ 子流程矩阵

| 产物 | 产出段 | 消费段 | 形式 / 备注 |
|---|---|---|---|
| `0_reading/*.json` + `reading_summary.md` | phase1 | phase2a | 半人工落盘；矢量 JSON + 立面翻译公式 |
| `correction_geometry.json` | phase2a | core | `CorrectedGeometry`（pre-snap）；**baseline diff 目标** |
| `correction_geometry_snapped.json` | core | 几何内核 | `CorrectedGeometry`（post-snap，权威坐标） |
| `corrections.json` | 2a + core | — *(sidecar)* | corrections/conflicts/unsupported 合并；当前不喂下游（见 5.4） |
| `building_geometry.json` | 几何内核(2_modelling) | 序列化器 | zones+面（确定性造面+切配）+ `kernel_gate_report.json`（门判定，advisory） |
| `geometry_specs.md`（zone/surface/fenestration_specs） | 几何内核(3_split_pairing) | 5_intakeoutput + 4_mep(zone 列表) | 序列化的几何 specs 文本 + `used_constructions` 集 |
| `mep_output.json` | 4_mep | 5_intakeoutput | `MepOutput` 8 非几何字段 |
| `intake_output.json` | 5_intakeoutput | 下游 | `IntakeOutput` 11 字段 = **交接契约**（geometry 3 + MEP 8 装配 + 契约校验）|
| IDF / EP 结果 | 下游 / simulate | — | InterZone 门 + EP |

### 3.1 固化的 on-disk 布局 + 每阶段校验工具（2026-06-09）

`run_full_pipeline.py <case> --base-dir test_data/SmallOffice_TwoStep --reading-from phase1` 产出按阶段分门别类（[run_full_pipeline.py](../../scripts/run_full_pipeline.py) + [pipeline.py](../../src/agent/pipeline.py) `run_pipeline` 固化）：

```
<case>/
  *.png, testdata_prompt.json        源素材（输入）
  llm.yaml                           per-case 模型组合
  phase1/  (= 0_reading)             phase1 产物（半人工 / sub-agent）
    {1f,2f,..}_view.json + *_render.png + reading_summary.md
  1_correction/                      phase2a 校正 + 确定性核
    correction_geometry.json            LLM 直出（pre-snap）
    correction_geometry_snapped.json    核吸附后（权威坐标）
    corrections.json                 2a+核 audit
    phase2a_raw.txt
  2_modelling/                       几何内核 build
    building_geometry.json           zones+面（确定性造面+切配结果）
    kernel_gate_report.json          InterZone 门对内核几何的判定（advisory）
  3_split_pairing/
    geometry_specs.md                序列化的 zone/surface/fenestration specs
  4_mep/                             物理撰写（LLM）
    mep_output.json + mep_raw.txt
  5_intakeoutput/
    intake_output.json               IntakeOutput 交接契约
    contract_issues.json             契约校验失败时（缺 construction 等）
  EP_run/                            下游装配 + EP
    temp_*.idf / temp_*.yaml / intake_output.json / pipeline_run.log
```

| 阶段 | 产物 | 校验工具 / 信号 |
|---|---|---|
| phase1 | `phase1/*.json` | [render_vector_to_png.py](../../Tool_scripts/render_vector_to_png.py)/`_svg.py` → 肉眼比对原图 |
| phase2a+核 | `partA/*.json` | [render_corrected_geometry.py](../../Tool_scripts/render_corrected_geometry.py) → 逐层平面图肉眼看（cells 铺满? 跨层轴统一? 窗在对的立面?）；Pydantic 结构；`corrections.json` audit。**待补**：A0 §7 确定性校验器（coverage/closure/z-stack，见 §5.1 类） |
| phase2b | `partB/intake_output.json` | Pydantic + 下游 L2 cross_ref |
| 下游+EP | `EP_run/` | **InterZone 门**（EP 前 fail-fast，确定性）+ L3 OpenStudio + L4 EP completed |

---

## 4. 规范不变量（不可破）

1. **CorrectedGeometry 边界**：phase2a 只出几何基元（cells/windows/z），不出 zones/surfaces；phase2b 把坐标当权威，不重推导。错误隔离在校正段，可单独评测迭代。
2. **IntakeOutput 边界**：11 字段契约不变；partA 切三段对下游 9 subagent / cross_ref / validate / InterZone 门**零影响**。
3. **确定性 vs 判断切分**：A1/A2（typed evidence 之上）+ core = 确定性；A3/A4 = 判断。**消碎片（core，防崩溃）与几何正确（phase2a，判断）是两件事**，刻意分离。
4. **skill = 单一真源**：所有 skill 文档运行时从 `skills/` 载入，不内联复制；A0 容差 registry 是常数单一真源（**目标**，见 5.1 缺口）。
5. **per-stage 可换模型**：`intake_correction` / `intake_mep` LLM section（缺则回退 `intake_correction`），换模型 = 改 per-case `<case>/llm.yaml`。

---

## 5. 规范须解决的接缝缺口（喂识图建模主线 §7 优先级 #2/#3）

### 5.1 A0 registry ↔ 确定性核 漂移 ✅ 已解（2026-06-09，优先级 #2.1）
原 [deterministic.py](../../src/agent/correction/deterministic.py) 把常数 Python 硬编码、不含 `SNAP_GRID`，簇均值吸附产 mm 级非栅格值。**已修**：容差外置 [src/configs/correction.yaml](../../src/configs/correction.yaml)（核从 config 读、env 可覆盖）；轴算法改 **聚类→吸附 50mm 栅格→碎片守卫**（簇均值不漏出）；**窗户分级** 10mm + 钳进父墙（不吸结构栅格）。值溯源 A0 §4。详见 [downstream_agent_changes.md 2026-06-09 条](../logs/downstream_agent_changes.md)。**doc 残留**：A0 §4 同步窗户分级策略 + window_snap_grid 命名。

### 5.2 先验割裂：几何（A4）vs MEP（散落）→ MEP 已抽离为草稿种子（2026-06-09，决策：几何优先）
原状：[A4_priors.md](../../skills/intake_pipeline/1_correction/A4_priors.md) = 结构化**几何**先验（phase2a/A3 用）；**MEP 默认值**（人密度/LPD/时间表/HVAC 设点）作 4 行散文混在 `rules.md`（已退役，归档 Skill_history） Step 7。**用户定调（2026-06-09）**：当前聚焦几何建模正确性，输入也无荷载/时间表数据，MEP 暂不建库——**只去混合**：把 Step 7 的默认值抽到 [priors/mep.md](../../skills/intake_pipeline/4_mep/mep.md)（标 DRAFT 种子），rules.md Step 7 改指针 + 保留 schedule 完整性契约，phase2b 加载 mep.md（值不变、行为不变）。**deferred**：(a) 把 mep.md 扩成分型/分级/带出处的真先验库 + (b) 几何先验(A4)与 MEP 合并进 `priors/`（统一库）——**都等几何稳定后再做**。Step 5 的 material/construction 是结构规则非先验值，留 rules.md。

### 5.3 phase1 provenance 契约未在上游落实（→ 优先级 #2.3）
[A0 §6](../../skills/intake_pipeline/1_correction/A0_contract.md) 定义了 `provenance_mode`/`coverage` + per-claim 证据分级，但 phase1 三文档还**不产结构化 provenance** → phase2a 实际跑 `legacy` 模式（估算笔画与测量值不可区分，全降级 `estimated_stroke`）。规范目标：phase1 输出容器带 provenance（strokes/dim-chains/labels/facades/windows 各自 source+confidence），让 phase2a 能按证据分级仲裁，"别把估算笔画当测量值吐"。

### 5.4 audit sidecar 未被消费（→ 优先级 #3 baseline 归因）
`corrections.json` 已物化但下游/评测不消费（P0 决策保 `IntakeOutput` 纯净、避免 64k 截断）。建 baseline 时需"看错（phase1/2a 判断）vs 改错（下游）"归因 → fast-follow 接入评测。

### 5.5 连接性补缝（#2.4，2026-06-09 部分落地）
"内墙没顶到外墙、留小缝" → 闭包不连续就形不成 zone（BEM fatal）。与轴吸附是**两类操作**（身份 50mm vs 连接性 300mm，A0 §4 分开）。**已落**：确定性核加连接性 pass——cell 边落在 footprint 边界内侧 ≤ `gap_close_threshold`(300mm) → 吸到边界封口（[deterministic.py](../../src/agent/correction/deterministic.py) `_close_to_boundary`，方向性、仅内墙→外墙）。阈值 300mm 而非 A0 老值 100mm：代价不对称（没闭合=致命 / 误闭合=罕见且 BEM 本须封）+ 真建筑少有 <300mm 有意缝。**残留**：① 内墙→内墙连接性（隔墙没顶到另一隔墙，风险更高暂不做）② 300–1000mm 走 A3（门洞/开口判断）、≥1000mm 走 zonification（开放边界，one-zone-vs-two）—— 这两段属 A3/zonification 判断，非确定性核。

---

## 6. 范围说明
- **切配 + cell→面几何生成**（互逆配对 / 造面 / OBC / 顶点）= **本项目侧确定性化、核之后做**（§0.1；2026-06-09 反转旧"归下游"定，见 [split_pairing_kernel_reference §6](../reference/split_pairing_kernel_reference.md)）。**待建**。
- **下游 9 subagent / cross_ref / validate prompt** = 协作者维护（本地有代码）。
- **InterZone 覆盖完整性校验**（shapely 长期解）= 标记未实现，落地时机 = B5 非方形 / 招到暴露 case（[downstream_agent_changes.md 2026-05-29 条](../logs/downstream_agent_changes.md)）。
