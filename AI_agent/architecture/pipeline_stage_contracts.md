# 管线各阶段：输入 · 输出 · 校验（活文档）

> **0–5 管线的权威接线 + 产物校验登记，活文档。** 逐阶段记清**输入什么 / 输出什么 / 怎么校验**。建于 2026-06-09（几何确定性化），2026-06-14 接通标准 case 布局，**2026-06-15 全文重写**（清掉 phase1/phase2a/phase2b/partA 旧称、并入产物校验登记 + 校验门模型 + reading/correction 分工再定）。取代 [architecture.md](../archive/architecture.md) 的「管线」部分。
>
> **当前唯一术语**：管线 = **0_reading**（识图）→ **1_correction**（校正 LLM + 确定性核）→ **2_modelling** + **3_split_pairing**（几何内核，代码）→ **4_mep**（物理 LLM）→ **5_intakeoutput**（装配，代码）→ 下游 9 subagent → EP。代码入口 [src/agent/pipeline.py](../../src/agent/pipeline.py) `run_pipeline`（`run_correction` + 核 + 几何内核 + `run_mep` + 装配）。**不再用 phase1/phase2a/phase2b——读历史文档遇旧称按此对照。**
>
> **用途**：每段喂哪些 skill / 读什么 / 产什么 / 谁消费；该段校验（现有 ✅⚠️ + 应补 ❌，按 §0.2 三层 + §0.3 judge 门）；规范不变量（§4）；接缝缺口（§5）。**「逐环节约束各阶段输出 + 校验方式」（[plan.md](../plan.md) B2–B4）以本文为施工底图**，随每条校验落地滚动更新。
>
> **触发（2026-06-15）**：sm20_anchor 首跑——2f 识图把整通走廊误切 4 段，但 reading 自检过、渲图肉眼漏、1_correction 靠 testdata 区数+尺寸链**静默修对**、三门只验最终模型故全 0。**识图错全程无一环显式逮住**。本文要解决的就是：让错误在**产生它的那段**显式可见 + 可归因。详见 [[pipeline-0-5-refactor-status]]。
>
> **范围**：本项目侧 = 识图 → 校正 → 几何（造面+切配）→ 物理 → 装配 → 产 `IntakeOutput`。下游 9 subagent / cross_ref / validate 的 **prompt 演进归协作者**（本地有代码可跑）；切配内核技术参考见 [split_pairing_kernel_reference.md](../reference/split_pairing_kernel_reference.md)。

---

## 0. 子流程链总览

```
 actor      阶段                     输入                          产物
─────────────────────────────────────────────────────────────────────────────
 半人工/VLM  0_reading 识图          建筑图 + testdata            0_reading/*.json (strokes+dims)
            (image-bound)                                       + reading_summary.md
               │
               ▼
 LLM        1_correction 校正        reading 矢量 JSON + testdata  CorrectedGeometry
            (image-blind)           + 1_correction 规则(A0–A4)    (correction_geometry.json)
               │
               ▼
 代码        确定性核 (1_correction 内) CorrectedGeometry           snapped CorrectedGeometry
            (no LLM)                + A0 容差 registry            (correction_geometry_snapped.json)
               │
               ▼
 代码        2_modelling+3_split_     snapped CorrectedGeometry    BuildingGeometry → 序列化
            _pairing 几何内核         (造面 + 切配)                zone/surface/fenestration_specs
            (no LLM)                                             (building_geometry.json/geometry_specs.md)
               │
               ▼
 LLM        4_mep 物理              zone 列表 + 必需 construction 集 8 非几何字段
            (image-blind)          + 4_mep 规则                  (mep_output.json)
               │
               ▼
 代码        5_intakeoutput 装配      geometry specs + MEP specs    IntakeOutput + 契约校验
            (no LLM)                                             (intake_output.json)
               │
  ══════════════ 本项目侧契约边界：IntakeOutput（11 字段，不变）══════════════
               ▼
 下游(协作者) 9 subagent + cross_ref + validate    IntakeOutput → 装配 IDF（几何被忠实誊写）
               │
               ▼
 代码        InterZone 门 → simulate  IDF → EP（门 EP 前 fail-fast）
```

实现：编排 [pipeline.py](../../src/agent/pipeline.py) `run_pipeline`（`intake_node` 与 `run_pipeline_deepseek.py` 薄包装共用）；确定性核 [correction/deterministic.py](../../src/agent/correction/deterministic.py)；几何内核 [geometry/](../../src/agent/geometry)（`modelling.py` 造面 + `split_pairing.py` 切配 + `specs.py` 序列化）；装配 [intakeoutput.py](../../src/agent/intakeoutput.py)（`assemble_intake_output` + `validate_contract`）；InterZone 门 [interzone.py](../../src/validator/interzone.py)。**fork (a)**（用户 2026-06-09 定）：几何序列化成 `surface_specs` 文本、下游忠实誊写——`IntakeOutput` 契约不变、下游代码不动。内核 build 硬错直接 raise（几何是确定性必需品，无 LLM 回退）。

> **口径统一（一物多名，2026-06-09）**：同一个「内部边界面之间的对应关系」在不同层不同叫法，等价——
> - **切配** / **split-pairing**（概念）= 把相邻 zone/层之间一对多的面，切成 EP 要求的逐面一对一 + 互逆引用。
> - `surface_specs` 写作 `adjacent_zone` / `adjacent_surface`。
> - IDF 是 `Outside_Boundary_Condition = Surface` + `Outside_Boundary_Condition_Object`（互逆指向对面面）。
> - 代码内核是 `Surface.obc = "Surface"` + `obc_obj`（[split_pairing.py](../../src/agent/geometry/split_pairing.py)）。
> 三表述同一事；**EnergyPlus 没有 `Zone` 边界条件**，写 `OBC=Zone` 是 severe。

> **【未来架构标记，不急落】4_mep 再拆 MEP 撰写分段**：4_mep 现一步出全部 8 个非几何字段。设想拆 material/construction（结构）与 schedule/people/lights/hvac（荷载）。等 mep.md 扩成真先验库后再落。

### 0.1 目标总架构（2026-06-09 用户定调）— 几何彻底确定性化

几何造面 + 切配全部从 LLM 手里收进代码内核，LLM 只剩校正判断 + 物理语义。本节架构**对矩形情形已落地**（非矩形随 B5 shapely）：

```
识图          校正                建模·几何模型      切配·仿真模型       物理信息挂载       下游·产品组装
0_reading     1_correction判断+核  2_modelling        3_split_pairing     4_mep              9 subagent
(LLM/VLM)     (LLM + 代码)        (确定性·已落地)    (确定性·已落地)     (LLM/模板)         (确定性装配)
感知           CorrectedGeometry   cells→zones+面     面切分+互逆配对      物理信息挂上         IDF + EP
```

**一刀切分原则**：**LLM 只做 感知（识图）+ 校正判断 + 物理语义挂载；代码做 所有几何（建模 + 切配）+ 装配。** 「建模·几何」（cells→zones+墙/楼板/天花面 + OBC + 顶点合成）与「切配·仿真」（跨层/邻区面切分 + 互逆配对）都在**确定性造面/切配内核**（核之后吃 cells）。产已完整解析的 surface_specs，下游退化成忠实誊写——`IntakeOutput` 契约不变、下游代码不动。

**触发证据**：sm20/sm21 对照（[split_pairing_kernel_reference §2.5](../reference/split_pairing_kernel_reference.md)）——一步出 LLM 切配做得对、staged 退化，证明几何造面/切配是确定性活儿不该交 LLM。

**落地状态**：✅ 矩形已落地——几何内核 [geometry/](../../src/agent/geometry)（shapely 多边形原生）接进 `run_pipeline`。**待实现**：非矩形（L/U、退台）内核 polygon-native 可吃，端到端随 B5。

### 0.2 校验分级框架（三层，贯穿全管线）

延续既有「三层防线」（坏 draw 重抽 → 确定性核修复/丢弃 → 内核 raise）与误差预算哲学，每段校验按**目的**分三类，登记时标清属哪层：

| 层 | 目的 | 处置 | 例 |
|---|---|---|---|
| **L-不变量**（确定性，硬） | 必须成立的结构/几何不变量，破=bug 或致命 | **raise / block** | cell id 唯一、z-stack 连续、最小边长、construction 全定义、OBC 互逆 |
| **L-交叉核对**（确定性，软） | 与上游约束/另一通道/合理区间对账，**surface 疑点供归因** | **warn / flag**（不阻塞） | 尺寸链闭合、stroke↔dimension 互核、区数 vs testdata、plan↔立面外包一致 |
| **L-肉眼/judge**（感知保真） | 感知活，确定性覆盖不到的真伪 | **人/VLM judge 看渲染** | 渲图 vs 原图、填色区图 cells 铺满、窗在对的立面 |

**关键原则**（用户 2026-06-15「correction 存在就是为了修识图错误」）：校验首要价值是**让错误在产生段显式可见 + 可归因**，**不等于**一定在该段阻断——可恢复的错让 correction 修没问题，但 reading 段应当**flag** 出来。**确定性能查的绝不留给肉眼**。

### 0.3 逐阶段校验门模型（确定性 + LLM-as-judge，开发期）

> 2026-06-15 用户定。每个阶段产中间文件后过**两道门**，决定进下一步 / 打回重做 / 终止。

**两道门（确定性在前、judge 在后）**：
1. **① 确定性自校验**（便宜、先跑）：§0.2 的 L-不变量(block) + L-交叉核对(flag)，结果落该段 `*_checks.json`。失败**先按下方失败分类处置**（stochastic 段盲重抽 / 确定性 code failure fail-closed / 0 当前 manual→`human_redraw_required`），不烧 judge。
2. **② LLM/VLM judge**（①过后才跑）：按该段 **rubric（标准清单）逐条裁**，每条 **pass / 轻微 / 严重 / 致命 + 证据**（**结构化清单，不用数字评分**——本项目「定性 > 定量」）。verdict schema 还含 **`not_applicable` / `insufficient_evidence` / `root_stage|null` / `root_confidence` / `retriable`**（纳入设计 L2；**unknown 不得自动路由**）。判据：**致命/严重 → 打回；轻微 → flag 放行**。

**judge 路由 = severity × recoverability（2026-06-22 用户全程 ratify，已落地，详 [[reading-honest-judge-routing-architecture]] / logs/review/2026-06-21_reading_honest_and_judge_routing_*）**：致命/严重不再单看严重度——加第二轴 `CriterionVerdict.recoverability`（correction_recoverable|unrecoverable|unknown）。**`blocking` 改成 J0-scoped**：severe/fatal 一律 block，**唯独** J0 标 `correction_recoverable` 的放行到 correction、由 J1 对参考独立复审确认；**J1 永远 block**（确认门，无下游 correction 可恢复）；缺省/unknown→当 unrecoverable→**向后兼容**。J0 标 `correction_recoverable` 须**同时**满足四条：①值/坐标错非身份·存在错 ②有独立幸存通道钉真值（尺寸链/footprint/跨层孪生/立面-平面互证）③落 correction 确定性可解集（`stroke_vs_dimension`/`cross_floor_axis_jitter`/主导通道 `checksum_failure`）④被 provenance 或 gate① CROSS_CHECK flag 诚实标出。**默认不确定→中止重读**（假绿出货代价 > 浪费重读）。
- **who-fixes 总纲（image-blind 边界）**：correction **永 image-blind 纯文本、不做 VLM**（开图=翻倍 VLM 要求、杀「看错 vs 改错」归因、饿死小模型监督、重引入「信刚看的图 > 尺寸链」bug；trust-the-dim 正因 correction 不能重感知才成立）。**脚手架=降智机制**（每道护栏=弱模型不必聪明到能独立做对的那件事，服务国产 VLM→本地开源北极星）。**看图仲裁归 judge（J0/J1 本就看图）+ 重读循环，不进 correction 生成**。证据冗余仍在 + 不靠猜→可放行 correction；证据销毁（通道塌缩）/身份错/漏元素→reading 中止。

**失败分类 + 重做规则（2026-06-15 v7 纳入 Codex 设计 H1 / 施工 H1·H2）**：失败**先分类、再决定处置**，**不能一律弹上游**——
| 失败类 | 处置 |
|---|---|
| `upstream_input_failure`（输入违反本段前置）| 弹**上游产出段**（确有上游根因）|
| `deterministic_code_failure`（输入合法、确定性代码违反后置）| **fail-closed、记 code defect、raise；绝不弹上游/换样本掩盖** |
| `stochastic_draw_failure`（0 自动后/1/4 的 draw 不过）| **盲重抽**（同输入换采样；judge 评语只进带外日志、绝不注入 prompt）|
| `judge_mismatch` | 盲重抽 stochastic 段；`root_confidence` 低 → **不自动路由、交人** |
- **0_reading 默认 = `manual` runner** → `human_redraw_required`；**当 `RunPolicy.reading_runner_available=True`**（PR-B，2026-06-22）→ orchestrator 返回**非终止** `awaiting_reread`，主 Agent 冷启**隔离子代理盲重读**（子代理即 runner，不必等外部 VLM API；写 flat view → `resample --force` 记 attempt → 再 gate①→J0；≤`per_stage_draws` → quarantine）。
- **不复用 `_make_correction_validator`** 当通用 harness——抽 `draw_json_once` + 单阶段 `retry_stage_draw`，跨阶段 route/invalidation 归执行地基（[施工方案 M0](../archive/pipeline_validation_build_plan.md)）；明确两入口 `repair_feedback`（下游 repair 可注入）vs `judge_retry_context=None`（必盲抽）不串线。
- **打回目标 = judge 归因的根因阶段**（非机械上一步）；归因不确定不自动路由。
- **预算 = 每阶段 3 次 + 整条 run 全局预算 + 循环检测**；超则终止 + 记 **`quarantined_failure`**（排除 judge 误判/代码 bug/配置错后才进训练 hard-sample 集）。

**judge 密度（自洽口径，纳入设计 L1）**：**自动 judge 只在 LLM 阶段 0/1/4**；**确定性阶段 2/3 无 per-run judge**——只有「用户几何确认门」或 dev 手动 VLM（看渲染、不重算坐标）；**5 无 judge**。

**judge = 开发期脚手架 / 数据工厂**：每条 verdict = ① 训小模型的监督标签 ② "哪些 judge 经验可固化成确定性校验"的清单。等小模型吃透 + 错类固化够多 → **撤顶尖 judge**，上线只留确定性校验 + 小模型（轻量化）。**半人工期**：人类操作员可看 judge 带外评语手修，但不注入任何自动 prompt（不污染训练数据）。

### 0.4 Codex 双 review 纳入（2026-06-15 v7，逐条处置见会话 + [施工方案 v2](../archive/pipeline_validation_build_plan.md)）

两份 review（[设计](../logs/review/review/2026-06-15_pipeline_0-5_validation_architecture_design_review.md) + [施工](../logs/review/review/2026-06-15_pipeline_0-5_validation_build_plan_review.md)，双 CHANGES REQUESTED）已全盘接受。**下表为 v7 修订要点速查——均已逐段改齐落实于 §1/§3 正文（非"上文覆盖下文"，纳入 re-verify High 1）**；机制细节落施工方案 M0–M4：

1. **失败分类 + 执行地基**（已改 §0.3）：确定性后置失败 fail-closed 不弹上游；0_reading=manual；新增 M0 执行/审计地基（stage runner / append-only attempts / 失效 DAG / resume / hash 绑定 approval）——**没这层不接 gate**。
2. **facade 仅 image-local**：0_reading 只产 `view_facade / local_x_direction / 可选 mirror+证据`；**world_axis/base_world 由 1_correction 据权威立面名 + reconciled footprint + z-stack 生成**（§1 0_reading/1_correction 的 `facade_axis` 结构字段据此理解）。
3. **reading schema 迁移**：`dimensions[]` 加 `chain_id/role(overall|segment|baseline)/order/value_m/text_verbatim/像素 anchor`；**stroke↔dimension 降为「内部几何-尺寸一致性」低置信 flag、非 2f 主验收**（同一次识图非独立真值，逮不了"自洽地全错"；原图真值交 J0/独立 OCR）。
4. **2f 归因不丢**：1_correction 加 delta/audit 完整性——cells 与 reading 墙图矛盾或依赖 testdata 修正 → 必产带来源 correction/conflict（保住"0 曾错"标签）；固化真实坏 2f fixture。
5. **矩形 coverage 本轮做**（非随 B5）：相邻 cell 共享边 → expected interfaces vs 实际互逆对（集合/面积）= **block**；B5 只泛化非矩形/void。
6. **uncaptured 不 block**：block 只要"存在且为 list"；干净图合法 `[]`。结构 block 改为真不变量（唯一 id/有限数值/非退化/合法 pen×kind/dimension 可解析/axis-端点一致）。
7. **4/5 归属 + 引用图**：Construction **不**引用 Schedule；两条图 `geometry→construction→material` 和 `people/lights/hvac→zone/schedule`。**4 拥有全部 MEP 引用图检查 + 对象语义**（SimpleGlazing standalone / NoMass 正热阻 / schedule type 存在）+ 统一 `idf_fragments.py` parser；**5 只装配+Pydantic+S4 backstop**（不另写 parser）。§1 5 末尾归属表中"construction→material→schedule 链路"归 **4**、不归 5。
8. **check schema v2**：status(pass|fail|skipped|not_applicable|error)/check_version/capability profile/artifact·attempt hash/机器可读 evidence；**policy 与事实分离**（同 coverage check 矩形 block、非矩形 skip）。
9. **用户几何确认门 = 调用策略**：viewer 始终可产；`confirmation_policy=required|optional|disabled` 由调用方定；批准绑 `building_geometry.json` hash、批准后不重抽 1；batch/CI/`--intake-from`（`validation_scope=downstream_only`）不被强插交互。
10. **viewer 先 trimesh**（已是依赖）出 mesh+静态投影 + spike pyvista/three.js 再定；viewer 失败不阻塞几何 check、headless 不可用显式 skip。

---

## 1. 逐段契约（输入 · 输出 · 校验）

### 0_reading — 识图（image-bound，半人工 / 未来 VLM）
- **职责**：把每张图 retrace 成语义矢量 JSON；**只识别、不做拓扑推理**（拓扑全留给 1_correction）。给 1_correction 两个通道：**拓扑+大致位置（strokes）+ 精确量级（dimensions）**。
- **喂的 skill**：[0_reading/guide.md](../../skills/intake_pipeline/0_reading/guide.md)（误差预算/全局约束/输出容器/纪律）+ [reading_guide.md](../../skills/intake_pipeline/0_reading/reading_guide.md)（认类别）+ [pen_library.md](../../skills/intake_pipeline/0_reading/pen_library.md)（类别→画笔/忽略/healing）。
- **输入**：建筑图（多张）+ `testdata_prompt.json`。
- **产物**：`{Nf,*}_view.json`（`strokes[]` + `dimensions[]`〔含 `chain_id/role(overall|segment|baseline)/order/value_m/text_verbatim/像素 anchor`〕 + ocr + 立面 **image-local 朝向字段**〔`view_facade`(图名/元数据来源) / `local_x_positive=image_left_to_right` / `mirrored:true|false|unknown` / `orientation_evidence`〕，**不含 world_axis/base_world——世界落位归 1_correction**）/ `reading_summary.md`（§3 翻译公式仅人看镜像、非承重）/ `reading_checks.json`（**应补**，确定性校验结果，带外归因）/ `*_render.png`（线框，供人/judge 对图）。**填色/区图归 1_correction，不在本段**。
- **消费者**：1_correction。
- **判据**：reading 只问「**这张图画了什么，你忠实描了吗**」——per-image 感知，**不建拓扑、不要参考答案、不做世界落位**（区数/跨图/轴翻落位全归 1_correction）。
- **校验**：
  - **① 确定性**（→ `reading_checks.json`；坏则按 §0.3 失败分类——**0 默认 `manual` runner → `human_redraw_required`**；`reading_runner_available` 开启则非终止 `awaiting_reread`（主 Agent 子代理盲重读，PR-B 2026-06-22））：⚠️现仅 `self_check` 自评。**应补 ❌**：(a) **结构 linter**（L-不变量, block）合法 pen×kind / 无拓扑字段 / plan thickness&world_z=null / 立面 image-local 朝向字段齐全 / 唯一 stroke·dimension id / 有限数值 / 非退化 line·rect / dimension 可解析 / axis-端点一致 /〔**`uncaptured` 仅要求存在且为 list、不要求非空**——干净图合法 `[]`〕；(b) **单图尺寸链闭合**（flag）Σ段==total（用 chain_id/role/order）；(c) **内部几何-尺寸一致性**（原 stroke↔dimension，**低置信 flag、非 2f 主验收**）stroke 近似长≈对应 dimension——只验内部一致，**不能逮"自洽地全错"**（同一次识图非独立真值；原图数字真值交 ②/独立 OCR）；(d) **单图越界**（flag）坐标在本图声明范围内。
  - **② VLM judge**（喂【原图+线框渲染+JSON】，结构化清单，**应补 ❌**）：七类明显识别错误——① 漏描真墙/真窗 ② 杂物当结构（家具/铺装/文字/轴网/楼梯）③ 笔型认错 ④ 数字抄错（复读尺寸标注，**这里才是抄录真值主验收**）⑤ image-local 朝向声明与视图自洽（**声明级**，真翻落位归 1）⑥ 门 healing 错 ⑦ 整片缺失/错位。致命/严重→**`human_redraw_required`**（0 当前 manual；VLM 接入后自动盲重读、3 次→终止）。
  - ⚠️ 现状 L-肉眼：`render_vector_to_png.py` 手动渲图比对（[[phase1-output-conventions]]）。

### 1_correction — 校正（image-blind，LLM）+ 确定性核（代码）
- **职责**：把感知基元（含噪声/自相矛盾）变成干净、自洽、仿真友好的几何基元，记录每处实质改动。A1 中线归一+z-stack → A2 规范轴集+吸附+链闭合 → A3 仲裁补全（A4 先验仅 A0/A3 门控下用）。**尺寸链为权威量级，冲突升级 A3（`checksum_failure`）。** 确定性核：建全局规范轴集吸附（消跨层抖动 + 杜绝退化碎片 + 连接性补缝）。
- **喂的 skill**：[1_correction/](../../skills/intake_pipeline/1_correction) 全 5 篇（README + A0 契约 + A1 坐标归一 + A2 规范化 + A3 仲裁 + A4 先验）作 RULE；0_reading 的 `guide.md`+`pen_library.md` 作 REFERENCE（懂矢量基元含义）；`reading_summary.md` 作 REFERENCE。常数取 [A0 §4 容差 registry](../../skills/intake_pipeline/1_correction/A0_contract.md) / [correction.yaml](../../src/configs/correction.yaml)。
- **输入**：0_reading 全部矢量 JSON（strokes+dims+**image-local 朝向**）+ testdata。
- **边界**：**只产几何基元（cells/windows/per-floor z），不产 zones/surfaces**（system prompt 硬约束）。
- **产物**：`correction_geometry.json`（pre-snap）/ `correction_geometry_snapped.json`（核吸附后，权威坐标）/ `corrections.json`（校正+核 audit）/ `correction_raw.txt`(+thinking/parse_error) / **`correction_checks.json`（应补，gate① 确定性结果）**。**视觉件（应补，2026-06-15 分工锁定）**：**填色区图** `*_zones.png`（逐层，post-snap cells 上色；现 zonification 未启=房间即 zone，是 judge/人看 redraw 保真的主件）+ **立面窗位图** `*_elev.png`（校正后窗画回各立面包络，与原立面比）+ **(将来 zonification 启)** zone 划分图（只画最终 zone、不画墙）。
- **判据**：correction 问「**能否无定性错重画回原图？区数/窗数对不对（有参考答案）**」——跨图 reconcile + 拓扑 + 对参考。**全管线最依赖人工校验的一段**（理想=能无定性错重画原图）。
- **校验**（2026-06-15 锁定）：
  - **① 确定性**（→ `correction_checks.json`；1 是 stochastic 段，坏则**盲重抽**）：✅ 现有 draw 级校验（schema/0窗/dup cell id/z 断裂，[pipeline.py:360](../../src/agent/pipeline.py#L360)，将抽成 `draw_json_once`+`retry_stage_draw`，见 §3.2#7）；✅ Pydantic；✅ 核 任两轴不近 `MIN_EDGE_LENGTH` + 连接性补缝（§5.5）。**应补 ❌**：(a) **A0§7 几何校验器**（block）cells 铺满 footprint 无洞无叠 / 闭包 / z-stack 连续数据级 / 非退化；(b) **立面世界落位 + 翻译（代码）**——据 reading 的 image-local 朝向 + 权威立面名 + reconciled footprint + z-stack **确定性生成 `world_axis/sign/base_world` 并把立面 stroke/window 翻 world**（world 落位本就归本段；sign 需独立证据、不许凭 VLM 自声明）；(c) **跨图对账**（flag）plan 外包 W×D==各立面宽 / z-stack 跨 4 立面一致 / 共享尺寸 plan↔立面相等；(d) **窗位落墙**（flag）每个翻译后窗落在其楼层带的某面外墙上——**逮立面轴翻落位 + 飘窗**；(e) **区数 tripwire**（flag）每层 cells 数 vs testdata `thermal_zones`——逮 2f 那种粗错；(f) **delta/audit 完整性**（block）当 cells 拓扑与 reading 墙图明显矛盾、或修正依赖 testdata 时，**必须产带来源的 correction/conflict 记录**——最终修对也保住"0_reading 曾错"标签（防 2f 式静默修对擦掉归因）。
  - **② VLM judge**（①过后；**judge 看得见原图**——外部评判、补 correction 自身 image-blind 的盲、还能把错归因回 reading。喂【原图 + 填色区图 + 立面窗位图 + 参考答案】，结构化清单裁）：① **区划保真**(填色区图 vs 原平面：房间无错并/错分/缺失/多出) ② **跨层一致**(同墙跨层对齐，5cm 抖动类) ③ **窗位保真**(窗落对立面/楼层/位置 vs 原立面) ④ **区数/窗数 vs 参考**(数对不对 + 差异有无合理解释；与 ①e tripwire **双管**——确定性数个数当快 tripwire、judge 做布局级裁决讲清合理合并/拆分) ⑤ **整体 redraw**(能否无定性错重画回原图)。致命/严重→打回**根因段**（reading 或 correction）、3 次终止。
  - **参考答案来源**：testdata（区数/楼层/外包）+ 轻量 per-case GT（窗数、可选 zone 布局）= 接 B2 `gt.json`（[plan.md](../plan.md) B2）。
  - ⚠️ 现状 L-肉眼：`render_corrected_geometry.py` 手动逐层平面图。

### 2_modelling + 3_split_pairing — 几何内核（代码，无 LLM）
- **职责**：从 snapped `CorrectedGeometry` 确定性造全部几何面并切配。`modelling`：cell→zone 体块 + 面顶点合成（外法向、CCW-from-outside）；`split_pairing`：同层内墙互逆配对 + 跨层楼板/天花切分配对 + roof/ground + 窗挂外墙。`specs.serialize_geometry` 序列化成 `zone_specs`/`surface_specs`/`fenestration_specs` + `used_constructions`（construction 按面型/OBC 定，互逆面同名 `Cons_InterFloor`）。
- **喂的 skill**：[2_modelling/spec.md](../../skills/intake_pipeline/2_modelling/spec.md) + [3_split_pairing/spec.md](../../skills/intake_pipeline/3_split_pairing/spec.md)（code-of-spec，非 LLM prompt）。
- **输入**：snapped `CorrectedGeometry`。
- **产物**：`building_geometry.json`（`zones`/`surfaces`/`windows`）+ `kernel_gate_report.json`（**block 关口判定**，非 advisory）+ `geometry_specs.md`（3 specs 文本）+ `used_constructions`（喂 4_mep）+ **`kernel_checks.json`（应补，gate① 确定性结果）**。**3D 查看器（应补）**：building_geometry 建一次 mesh → **trimesh（已是依赖）出 mesh + GLB/静态投影先行**；交互 viewer（pyvista `export_html` vs 轻量 three.js：转/半透/剖切 + 「按切配上色」互逆对同色·未覆盖边界高红）**先 spike 再定产品依赖**；**viewer 失败不阻塞几何 check，headless 不可用要显式 skip、非假 PASS**。
- **校验**（2026-06-15 锁定；确定性阶段**靶子是代码=单测+不变量**，per-run 由 gate① 裁、**无 per-run LLM judge**）：
  - **① 确定性**（→ `kernel_checks.json`）：✅ L-不变量 内核硬守卫（[modelling.py:280+](../../src/agent/geometry/modelling.py#L280)）dup cell id / z-stack 不连续 **raise** / 最小边长 `_MIN_EDGE=0.10` 退化面地板。**应补 ❌**：① **逐 zone 封闭完整**（楼板+天花+全部周墙、无缺面，block）② **法向一致**（全外法向、CCW-from-outside，block）③ `kernel_gate_report` **从 advisory 提为 block 关口**（互逆配对/面积/反法向/共面/最小边长）④ **覆盖完整性（shapely，矩形本轮 block，v7 纳入 Codex 设计 H4/施工 H4）**——相邻 cell 共享边推 expected internal interfaces vs 实际互逆对（集合/面积对账），抓「本该内部边界、两侧却都标 Outdoors/不在配对图」的洞（per-pair 门+EP 都查不到，§6）；**B5 只泛化非矩形/void**，矩形检查不延后 ⑤ **spec 自洽**（surface_specs 引用 zone 存在、`adjacent_surface` 目标存在；放 3 序列化时，与 5 契约互补）。
  - **② 人工/可选 VLM（非 per-run judge）**：(a) **用户几何确认门 = 调用策略**（**非管线不可绕过的交互**）——viewer 始终可产；`confirmation_policy=required|optional|disabled` 由产品/CLI 调用方定；批准**绑定 accepted geometry checkpoint digest**（`building_geometry`+`geometry_specs`+kernel check report+stage/check version），**批准后不得重抽 1_correction**（resume 复用已批准 attempt）；batch/CI/`--intake-from`（`validation_scope=downstream_only`）不被强插交互。BEM 常见「先看模型再跑」，**区别于 dev 期用完即撤的 LLM judge**。(b) **dev 调试**——确定性 flag 时转图定位坏面。(c) **新形状兜底**——可选对静态 PNG 跑一次性 VLM「像不像这栋楼」，dev 手动触发、不进自动流。

### 4_mep — 物理信息撰写（image-blind，LLM）
- **职责**：只产非几何 8 字段——`building`/`site_location` + `material`/`construction`/`schedule`/`people`/`lights`/`hvac_specs`。必须定义 `used_constructions` 里每个 construction（否则面挂不上、EP fatal）。
- **喂的 skill**：[4_mep/authoring.md](../../skills/intake_pipeline/4_mep/authoring.md)（撰写规则）+ [4_mep/mep.md](../../skills/intake_pipeline/4_mep/mep.md)（默认值/DRAFT 种子）。
- **输入**：testdata + 序列化 zone 列表（取 zone 名写 per-zone people/lights/hvac）+ 必需 construction 集。
- **产物**：`mep_output.json`（8 字段）+ `mep_raw.txt`(+thinking/parse_error) + **`mep_checks.json`（应补，gate① 结果）** + **MEP 摘要表 markdown**（应补，construction/material + per-zone 荷载/作息/设点，给人/judge 扫——MEP 版「渲染件」）。
- **现状定调（2026-06-15）**：输入几乎无 MEP 信息 → MEP **基本全套默认**（mep.md DRAFT，§5.2 暂缓建库）。**本轮只搭校验框架**：引用完整性是 EP 正确性硬需求、**现在实做**；合理性区间 + 语义 judge **先留框架占位、等补足 MEP 输入再充实**。
- **校验**（2026-06-15 锁定框架）：
  - **① 确定性**（→ `mep_checks.json`，1 是 stochastic 段坏则盲重抽）：✅ Pydantic（MepOutput）。**应补 ❌（现做）**：经**统一 `idf_fragments.py` parser**（一次解析 MEP fragment bundle → 对象索引 + 诊断，所有 check 共用、禁各自 regex；解析失败=block+重抽）→（i）**引用完整性**（两条图：`geometry→construction→material` + `people/lights/hvac→zone/schedule`；construction/material/schedule/per-zone 覆盖，construction 覆盖从 5 前移）+（ii）**schedule 完整性**（Schedule:Compact 含 AllOtherDays，从 IDF 门前移）+（iii）**对象语义**（block）`WindowMaterial:SimpleGlazingSystem` standalone construction / `Material:NoMass` 正热阻 / schedule type 引用存在 / 必填字段 / 正值——逮 SimpleGlazing 多层 fatal、no-mass draw。**应补 ❌（占位，补 MEP 输入后充实）**：**合理性区间 flag**（LPD/人密度/设点/活动量/U 值落典型区间）。
  - **② 文本 LLM judge**（轻，无图；**占位，等 MEP 数据驱动后变重**）：读 `mep_output + testdata(类型/气候) + zone 列表`，结构化清单裁**类型适配性**（作息匹配占用类型/荷载匹配用途/材料适配气候）。致命/严重→盲重抽、3 次终止。
  - **参考来源**：mep.md DRAFT 典型值/区间（当前）→ 真先验库（§5.2 deferred）；MEP 是类型默认非 case 特异，**不需 per-case gt.json**。

### 5_intakeoutput — 装配（代码，无 LLM）
- **职责**：把 3 个几何 specs + 8 个 MEP 字段机械拼成 `IntakeOutput`，跑确定性契约校验。
- **输入**：geometry specs + `mep_output`。
- **产物**：`intake_output.json`（**交接契约，11 字段不变**）+ **`assembly_checks.json`**（应补，gate① 全部结果，扩自 `contract_issues.json`）。
- **校验**（确定性、**无 judge、无渲染**）：5 **只做 `assemble_intake_output` + Pydantic + 接受 S4 report/hash 的 backstop**——✅ `validate_contract`（[intakeoutput.py:67](../../src/agent/intakeoutput.py#L67)，4 前移后成 backstop、复用同函数不另写 parser）；✅ Pydantic IntakeOutput。**全部 MEP 引用图（含 zone↔load）归 4_mep**（4 已持有 required zone set + used constructions，绝大多数 seam 在 4 输出点即可见，**非"只有装配后才显形"**）。内核 build 硬错 `run_pipeline` 直接 raise（无 LLM 回退）。
- **跨阶段自洽归属**（唯一 owner，避免重复）：`surface/window→zone / adjacent_surface 目标` = **3**（几何内部，序列化时查）；`geometry→construction→material` + `people/lights/hvac→zone/schedule` + 对象语义 = **4**（MEP 引用图唯一 owner）；**5 = 最终 Pydantic assembly + 上述结果的 backstop**（重复检查标 defense-in-depth、不参与 root-stage 归因）。

### downstream — 9 subagent + cross_ref + validate（协作者维护 prompt）
- **职责**：`IntakeOutput` → 装配 IDF。
- **喂的 skill**：各下游节点 prompt（[src/agent/nodes/*.py](../../src/agent/nodes)，**协作者维护**）。
- **产物**：`EP/temp_*.idf`/`temp_*.yaml`/`intake_output.json` 副本；`EP/EP_run/eplusout.{err,end,eso,csv,…}`/`ep_console.log`/`pipeline_run.log`。
- **校验**：✅ L-不变量 **InterZone 门** `audit_interzone_surface_pairs`（[interzone.py:224](../../src/validator/interzone.py#L224)，EP 前 fail-fast：OBC=Surface 目标存在/互逆/单一引用/面积/反法向/共面/最小边长 + 非法 OBC 含 Zone）+ **schedule 门** `_check_schedules`（[schedules.py](../../src/validator/schedules.py)）+ **EP end 门** `read_ep_end`（[runner.py:31](../../src/runner/runner.py#L31)，解析 `eplusout.end` 出 completed/severe/warning，H3 已修假 success）；⚠️ L3 OpenStudio 人工 + L2 cross_ref。**应补 ❌**：EP 断言自动化 baseline（`read_ep_end` 阈值：0 severe / warning 白名单，接 test_baseline B2–B4）。

---

## 2. skill ↔ 阶段矩阵

| skill 文档 | 0_reading | 1_correction | 确定性核 | 几何内核(2+3) | 4_mep | 5_intakeoutput | 下游 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 0_reading/guide.md | ●主 | ○参考 | | | | | |
| 0_reading/reading_guide.md | ●主 | | | | | | |
| 0_reading/pen_library.md | ●主 | ○参考 | | | | | |
| 1_correction/A0–A4 + README | | ●规则 | (常数源) | | | | |
| 2_modelling/spec.md + 3_split_pairing/spec.md | | | | ●code-of-spec | | | |
| 4_mep/authoring.md + mep.md | | | | | ●规则 | | |
| 下游各节点 prompt（src/nodes/*.py） | | | | | | | ●协作者 |

`●主`=该段主规则；`○参考`=背景理解；`●code-of-spec`=非 LLM prompt，代码内核的规格文档；`(常数源)`=作单一真源被代码读取（A0 registry）。

## 3. 中间产物 ↔ 阶段矩阵

| 产物 | 产出段 | 消费段 | 形式 / 备注 |
|---|---|---|---|
| `0_reading/*.json` + `reading_summary.md` | 0_reading | 1_correction | 半人工落盘；矢量 JSON（strokes+dims+facade_axis）+ 翻译镜像 |
| `reading_checks.json` *(应补)* | 0_reading | — *(带外归因)* | 确定性校验结果 |
| `correction_geometry.json` | 1_correction | 确定性核 | `CorrectedGeometry`（pre-snap）；**baseline diff 目标** |
| `correction_geometry_snapped.json` | 确定性核 | 几何内核 | post-snap，权威坐标 |
| `corrections.json` | 1_correction+核 | — *(sidecar)* | corrections/conflicts/unsupported 合并（见 §5.4） |
| `correction_checks.json` *(应补)* | 1_correction | — *(带外归因)* | gate① 确定性校验结果 |
| 填色区图 `*_zones.png` / 立面窗位图 `*_elev.png` / (将来)zone 区图 *(应补)* | 1_correction | judge/人 | redraw 保真 + 区划/窗位核对（zonification 启后另出纯 zone 图） |
| `building_geometry.json` | 几何内核(2) | 序列化器 | zones+面 + `kernel_gate_report.json`（提为 block 关口）+ `kernel_checks.json` *(应补)* |
| 3D 查看器（trimesh mesh+静态投影，交互 spike 后定）/ PNG *(应补)* | 几何内核(2+3) | **用户确认门=调用策略** / dev / 可选 VLM | 转/半透/剖切 + 按切配上色；`confirmation_policy` + hash 绑定批准；viewer 失败不阻塞 check |
| `geometry_specs.md` | 几何内核(3) | 5_intakeoutput + 4_mep(zone 列表) | 序列化几何 specs + `used_constructions` |
| `mep_output.json` | 4_mep | 5_intakeoutput | 8 非几何字段 |
| `intake_output.json` | 5_intakeoutput | 下游 | `IntakeOutput` 11 字段 = **交接契约** |
| IDF / EP 结果 | 下游 / simulate | — | InterZone 门 + EP |

### 3.1 固化的 on-disk 布局 + 每阶段校验工具

> **case = 纯素材；run 自包含（2026-06-16 用户定；2026-06-23 布局整理）**：`<case>/` 入库只含 `case_data/`（素材 + testdata），**改素材才新 case**。每次跑 = 自包含 `<case>/run_<注释>/`（单 case 可多轮 run），内含本 run 的 `llm.yaml` + `0_reading/` + `1_correction…5_intakeoutput/` + `EP/` + `_run/`（机器记账：manifest / validation summary / baseline / state / approval）+ `report/REPORT.md`（唯一人读报告，GEN 事实区 + AGENT 叙事/建议 + `eyeball/` 索引）；1–5/EP 由代码**跑中建**、绝不预搭空骨架。下方「全树」即一个 **run 目录** run 后的样子（非 case 根）。`validate_case(<run_dir>)`/`record_baseline(<case> <run>)` 对 run 目录操作（case 素材由 `run_dir.parent` 解析）。评测参考答案 gt 不在 case 内，放 `case_tests/test_baseline/gt/<case>.json`（**judge② 专用，gate①/执行器绝不读**，见 [new_case_guide §0.2](../guides/new_case_guide.md)）。

`run_full_pipeline.py <case> --base-dir case_tests/e2e_tests --reading-from 0_reading` 产出按阶段分门别类：

```
<case>/
  llm.yaml                           per-run 模型组合（run 根）
  case_data/                         源素材：*.png + testdata_prompt.json
  0_reading/                         识图产物（半人工 / sub-agent）
    {1f,2f,..}_view.json + reading_summary.md + *_render.png (+ reading_checks.json 应补)
  1_correction/                      校正(LLM) + 确定性核
    correction_geometry.json            LLM 直出（pre-snap）
    correction_geometry_snapped.json    核吸附后（权威坐标）
    corrections.json                 校正+核 audit
    correction_raw.txt               (+ correction_thinking.txt / correction_parse_error.txt)
    (+ 填色区图 / zone 区图 应补)
  2_modelling/
    building_geometry.json           zones+面（确定性造面+切配结果）
    kernel_gate_report.json          内核几何门判定（**block 关口**）+ kernel_checks.json 应补
  3_split_pairing/
    geometry_specs.md                序列化的 zone/surface/fenestration specs
  4_mep/
    mep_output.json + mep_raw.txt    (+ mep_thinking.txt / mep_parse_error.txt)
  5_intakeoutput/
    intake_output.json               IntakeOutput 交接契约
    contract_issues.json             契约校验失败时
  EP/                                IDF 相关输出（下游装配）
    temp_*.idf / temp_*.yaml / intake_output.json 副本 / idf_plan.png
    EP_run/                          EP 仿真输出: eplusout.* / ep_console.log / pipeline_run.log
  _run/
    run_manifest.json                accepted attempts + hashes
    validation_manifest.json         validate_case summary
    geometry_approval.json           geometry digest approval（如有）
    orchestration_state.json         judge-in-the-loop ledger（如有）
    baseline.json                    数字权威 scorecard + evidence_index
  report/
    REPORT.md                        唯一人读报告；GEN 区代码刷新，AGENT 区主控保留
    eyeball/                         汇拢的 2D 肉检件
```

> **路由（2026-06-14 接通）**：`run_full_pipeline` 读 `case_data/testdata_prompt.json`；`SimContext.ep_run_subdir="EP_run"` 让 EP 仿真落 `EP/EP_run/`、IDF 留 `EP/`。

> **M0 布局（append-only attempts，施工 M0）**：每段 `<stage>/attempts/NNN/{output,checks,judge}.*`（**不覆盖坏 draw**）+ `_run/run_manifest.json`（指向各段 accepted attempt + input artifact hashes + stage/check version）+ `_run/geometry_approval.json`（绑定 accepted geometry checkpoint digest = building_geometry+geometry_specs+kernel check report+version；批准后 resume 复用、不重抽）。失效 DAG：`0→1-5 / 1→2-5 / 2→3-5 / 3→4-5 / 4→5`。

> **每段校验工具速览见 §1 各段「校验」条**（现有 ✅⚠️ + 应补 ❌，带 file:line）；本表不重复。

### 3.2 应补校验 backlog（按杠杆排序）

> **实现状态（2026-06-15 v9，M0–M4 一轮落地，测试 103→191）**：下表「应补 ❌」**确定性部分已全部落地**——schema/policy 地基 [`src/validator/checks/schema.py`](../../src/validator/checks/schema.py)（CheckReport v2，policy≠fact）；执行/审计地基 [`src/agent/execution/`](../../src/agent/execution)（append-only attempts/失效 DAG/resume/budget/approval digest/失败分类 routing）；逐段确定性 check [`src/validator/checks/{reading,correction,kernel,mep,assembly}.py`](../../src/validator/checks) + [`src/agent/correction/{geometry_validator,facade}.py`](../../src/agent/correction) + 统一 parser [`src/validator/idf_fragments.py`](../../src/validator/idf_fragments.py)；judge harness [`src/agent/judge/`](../../src/agent/judge)（verdict v2 + 单阶段盲抽不串线 + J0/J1 rubric + J4 disabled stub）；视觉件 `render_elevation_windows.py` + `render_building_3d.py`(trimesh，headless 显式 skip)；capstone [`validate_case`](../../src/agent/execution/validation_run.py) 非侵入跑全段 gate①（原设计未动 `run_pipeline`/契约/下游）。施工进度表见 [build_plan §5](../archive/pipeline_validation_build_plan.md#5-施工进度)。**更新（2026-07-01，桶③完全关闭）**：`run_pipeline` 现已**内联自校、口径齐 `validate_case`**（在原 capstone 之外、契约/下游仍不动）——evidence 覆盖（A8）+ 完整 `check_kernel`（**全 invariant**：InterZone+zone_closure+normals+spec+coverage，S23-16 起、`7.01` 桶③升级）+ 完整 `check_correction`（S1，post-core）+ `check_mep`（S4）+ `check_assembly`（S5 artifact，`7.01` 桶③），产 `1_correction/correction_checks.json`+`2_modelling/kernel_checks.json`+`4_mep/mep_checks.json`+`5_intakeoutput/assembly_checks.json`，按 `run_profile` 分档（exploratory 写产物+warn 可见续行／golden·regression fail-closed raise 带外部 profile；S5 contract 是**全 profile 硬 raise**、不走分档）；`intake_node` 默认 exploratory 零新硬失败。**桶③（生产路径自校）已完全关闭**。**仍 deferred**：judge LLM/VLM 真实接线（harness 已就位、judge_fn 可插拔）/ 4_mep 合理性区间（占位）/ viewer 交互层 spike / resume 接进 `run_pipeline`（地基就位）。

逐段「应补 ❌」汇总成施工序（纪律：每条明确归 §0.2 三层 + §0.3 哪道门；确定性校验配单测；改 skill/src 按 [CLAUDE.md §6#5](../CLAUDE.md) 备份）：

1. **0_reading 确定性 linter**（结构 + 尺寸链闭合 + **stroke↔dimension 互核** + 单图越界）+ **VLM judge rubric（七类明显识别错误）** —— 杠杆最高，在源头逮感知错。**用户定 = 本轮规范各阶段产物时一起做**（含 2026-06-15 缺的数字/越界类，**区数/跨图移到 1_correction**）。
2. **1_correction（2026-06-15 锁定）**：gate① = A0§7 几何校验器 + **立面 local→world 代码翻译**（取代 summary §3 散文）+ **跨图对账**（外包/z-stack/共享尺寸）+ **窗位落墙**（逮轴翻落位/飘窗）+ **区数 tripwire**（cells 数 vs testdata）→ `correction_checks.json`；视觉件 = **填色区图 `*_zones.png` + 立面窗位图 `*_elev.png`**（+ 将来 zone 区图）；gate② = **看原图的 VLM judge** 对参考答案（testdata + B2 gt.json）裁 redraw 保真 5 条。
3. **2+3 几何内核（2026-06-15 锁定，确定性靶子=代码）**：gate① = 封闭完整 + 法向一致 + `kernel_gate_report` 提为 block 关口 + 互逆/面积 + **矩形覆盖完整性 block（本轮做，B5 泛化非矩形）** + spec 自洽 → `kernel_checks.json`；**交互 3D 查看器**（trimesh mesh+静态投影先行，pyvista/three.js spike 后定）= 用户几何确认门（**调用策略 + hash 绑定**）；**无 per-run LLM judge**。
4. **4_mep（2026-06-15 锁框架）**：**现做** = 引用完整性（construction/material/schedule/per-zone 覆盖，construction 从 5、schedule 完整性从 IDF 前移）+ `mep_checks.json` + MEP 摘要表；**占位待 MEP 输入再充实** = 合理性区间 flag + 文本 judge 类型适配。MEP 现全套默认（§5.2）。
5. **5_intakeoutput（2026-06-15 锁定，v7 修订）**：只做 `assemble_intake_output` + Pydantic + **接受 S4 report/hash 的 backstop**（zone↔load 跨域缝亦可在 4 输出点见，5 不另写 parser）→ `assembly_checks.json`；**无 judge、无渲染**。
6. **EP 断言自动化**（`read_ep_end` 阈值接 test_baseline B2–B4）+ **corrections.json 接评测归因**（§5.4）。
7. **执行/审计地基 + judge 门基建**（施工 M0/M3）：**不复用 `_make_correction_validator`**——抽 `draw_json_once` + 单阶段 `retry_stage_draw`（两入口 `repair_feedback` vs `judge_retry_context=None` 不串线）；跨阶段 route/失效 DAG/resume/hash 绑定 approval 归 `src/agent/execution/`；verdict schema v2 + 全局预算 + 循环检测 + 带外日志 + hard sample **先 quarantine**。

---

## 4. 规范不变量（不可破）

1. **CorrectedGeometry 边界**：1_correction 只出几何基元（cells/windows/z），不出 zones/surfaces；几何内核(2/3) 把坐标当权威，不重推导。错误隔离在校正段，可单独评测迭代。
2. **IntakeOutput 边界**：11 字段契约不变；0–5 分段对下游 9 subagent / cross_ref / validate / InterZone 门**零影响**。
3. **确定性 vs 判断切分**：A1/A2 + 确定性核 = 确定性；A3/A4 = 判断。**消碎片（核，防崩溃）与几何正确（1_correction，判断）是两件事**，刻意分离。
4. **skill = 单一真源**：所有 skill 运行时从 `skills/` 载入，不内联复制；A0 容差 registry 是常数单一真源。
5. **per-stage 可换模型**：`intake_correction` / `intake_mep` LLM section（缺则回退 `intake_correction`），run 记录换模型 = 改 `<run>/llm.yaml`。
6. **judge 不给流程额外信息 + 失败分类**（2026-06-15，v7 纳入 Codex 设计 H1）：judge 评语只进带外日志、绝不注入子流程 prompt；重做=盲重抽；**确定性后置失败 fail-closed 记 code defect、不弹上游/不换样本掩盖**；只 stochastic 0/1/4 盲重抽（0 当前 manual→human_redraw_required）；归因不确定（`root_confidence` 低）不自动路由；全局预算+循环检测、hard sample 先 `quarantined`。

---

## 5. 规范须解决的接缝缺口（喂识图建模主线 §7 优先级 #2/#3）

### 5.1 A0 registry ↔ 确定性核 漂移 ✅ 已解（2026-06-09，优先级 #2.1）
原 [deterministic.py](../../src/agent/correction/deterministic.py) 把常数硬编码、不含 `SNAP_GRID`，簇均值吸附产 mm 级非栅格值。**已修**：容差外置 [correction.yaml](../../src/configs/correction.yaml)；轴算法改 **聚类→吸附 50mm 栅格→碎片守卫**；**窗户分级** 10mm + 钳进父墙。值溯源 A0 §4。**doc 残留**：A0 §4 同步窗户分级策略 + window_snap_grid 命名。

### 5.2 先验割裂：几何（A4）vs MEP（散落）→ MEP 已抽离为草稿种子（2026-06-09）
[A4_priors.md](../../skills/intake_pipeline/1_correction/A4_priors.md) = 结构化**几何**先验（1_correction/A3 用）；**MEP 默认值**抽到 [mep.md](../../skills/intake_pipeline/4_mep/mep.md)（标 DRAFT 种子，值不变行为不变）。**deferred**（等几何稳定后）：(a) mep.md 扩成分型/分级/带出处真先验库 (b) 几何先验(A4)与 MEP 合并进统一 `priors/`。

### 5.3 0_reading provenance 契约 ✅ 已解（2026-06-22，修 sm21 Sonnet 识图）
**已落地**：`Stroke` 加可选 `provenance`(seen|dimension_derived|estimated|unknown)/`confidence`/`dimension_refs`（[schema.py](../../src/agent/reading/schema.py)）；reading 校验器落地承诺已久的 **stroke↔dimension 一致性 CROSS_CHECK**（非阻塞 flag，10mm 容差，perimeter 排除，中性「verify」措辞）+ **`provenance_mode`(full|partial|legacy) 报告**（[checks/reading.py](../../src/validator/checks/reading.py)）；guide/pen 补**双通道纪律**(尺寸链刻度≠墙) + 门≠窗负例 + **provenance→A0 grade 映射**(`seen`=视觉存在证据→numeric `estimated_stroke`，**非 `direct_measurement`**；`dimension_derived`→`transcribed_dimension` 须带 `dimension_refs`)。correction A1-A4 **不动**（trust-the-dim 早已落地，缺的只是上游冲突信号）。审计 logs/review/2026-06-21_reading_honest_and_judge_routing_{proposal,review}。
> 原缺口（留档）：A0 §6 定义了 provenance_mode/coverage + per-claim 证据分级，但 0_reading 三文档曾**不产结构化 provenance** → 1_correction 实际跑 `legacy` 模式，估算笔画与测量值不可区分。这也是 §1「尺寸链为权威量级」从隐式变显式的前提。

### 5.4 audit sidecar → baseline 归因 ✅ baseline 侧已收口（2026-06-22，PR-A）
`corrections.json` 已物化且 correction 门查完整性，但此前 `record_baseline`/`_run/baseline.json` 不消费它。**已落地**：`record_baseline` best-effort 读 `1_correction/corrections.json` → `_run/baseline.json.corrections_summary`（counts by kind/rule_id/stage + capped corrections rows + **full conflicts/unsupported** + sidecar 状态）+ `report/REPORT.md` 的 GEN 事实区新增校正审计摘要；**不动 gate flags/计数**（Finding 6）。审计轨迹 logs/review/2026-06-22_audit_attribution_and_auto_reread_{proposal,review}。**残留（N4）**：把 gt-diff 与 corrections 机械 JOIN（逐差异自动判 看错↔改错），属评测嵌入。原 P0 决策仍保 `IntakeOutput` 纯净（不把 audit 灌进交接契约、避免 64k 截断）。

### 5.5 连接性补缝（#2.4，2026-06-09 部分落地）
"内墙没顶到外墙、留小缝" → 闭包不连续就形不成 zone（BEM fatal）。与轴吸附是**两类操作**（身份 50mm vs 连接性 300mm，A0 §4 分开）。**已落**：核加连接性 pass——cell 边落 footprint 内侧 ≤ `gap_close_threshold`(300mm) → 吸到边界封口（[deterministic.py](../../src/agent/correction/deterministic.py) `_close_to_boundary`，方向性、仅内墙→外墙）。**残留**：① 内墙→内墙连接性（风险更高暂不做）② 300–1000mm 走 A3（门洞判断）、≥1000mm 走 zonification（开放边界）——属判断，非确定性核。

---

## 6. 范围说明
- **切配 + cell→面几何生成**（互逆配对/造面/OBC/顶点）= **本项目侧确定性化、核之后做**（§0.1；2026-06-09 反转旧"归下游"定，见 [split_pairing_kernel_reference §6](../reference/split_pairing_kernel_reference.md)）。**已落地（矩形）**；非矩形随 B5 shapely。
- **下游 9 subagent / cross_ref / validate prompt** = 协作者维护（本地有代码）。
- **InterZone 覆盖完整性校验**（shapely 长期解）= 标记未实现，落地时机 = B5 非方形 / 招到暴露 case（[downstream_agent_changes.md 2026-05-29 条](../logs/downstream_agent_changes.md)）。

---

_2026-06-15 (v6) — **5_intakeoutput 校验定稿 + 0–5 全锁**（逐阶段探讨收尾）：5 = 确定性跨域引用完整性（zone↔per-zone 荷载、construction→material→schedule 链路）→ `assembly_checks.json`，契约成兜底，**无 judge 无渲染**；新增「跨阶段自洽归属」表（3 几何内部 / 4 MEP 内部 / 5 跨域接缝，不重复）。**0–5 逐段输入·输出·校验全部锁定**，下一步出施工方案 + Codex review。_
_2026-06-15 (v5) — **4_mep 校验框架定稿**（逐阶段探讨锁第 4 段）：现状=输入几乎无 MEP 信息、基本全套默认，**本轮只搭框架**——引用完整性（construction/material/schedule/per-zone 覆盖 + schedule 完整性，从 5/IDF 前移）是 EP 正确性硬需求现在实做；合理性区间 flag + 文本 judge 类型适配先占位、等补 MEP 输入再充实。产物加 `mep_checks.json` + MEP 摘要表。MEP 是类型默认非 case 特异、不需 gt.json。_
_2026-06-15 (v4) — **2+3 几何内核校验定稿**（逐阶段探讨锁第 3 段）：确定性阶段靶子=代码（单测+不变量）、**无 per-run LLM judge**；gate① 确定性集（封闭完整/法向一致/kernel_gate_report 提 block/互逆+面积/覆盖完整性 shapely 随 B5/spec 自洽）→ `kernel_checks.json`；产物加 **交互 3D 查看器**（pyvista `export_html`：转/半透/剖切 + 按切配上色，并掉单出 2D 覆盖图）+ 静态 PNG；**关键**：交互 3D = **上线保留的用户几何确认门**（确认几何对才进仿真，区别于 dev 期 LLM judge）。§3 矩阵 + §3.2#3 同步。_
_2026-06-15 (v3) — **1_correction 校验定稿**（逐阶段探讨锁第 2 段）：产物加 `correction_checks.json` + 填色区图 `*_zones.png` + 立面窗位图 `*_elev.png`（+将来 zone 区图）；gate① 确定性 = A0§7 几何校验器 + 立面 local→world 代码翻译 + 跨图对账 + 窗位落墙 + 区数 tripwire；gate② = 看原图的 VLM judge 对参考答案（testdata + B2 gt.json）裁 redraw 保真 5 条；区数双管（tripwire + judge）。§3 矩阵 + §3.2#2 同步。_
_2026-06-15 (v8) — **纳入 Codex re-verify（NOT YET CLOSEABLE → must-fix 全落）**：re-verify High 1 = §0.4 不能当覆盖 banner，**§1/§3 逐段改齐 v7 口径**（已删/改：0_reading facade→image-local 朝向字段·uncaptured 不 block·stroke↔dim 降低置信「内部一致性」非 2f 主验收·0=manual→human_redraw；1_correction world 落位在本段生成+delta/audit 归因；2/3 viewer trimesh 先行·用户门=调用策略+hash·kernel_gate_report 提 block；4_mep idf_fragments parser+对象语义 block；5 仅 assemble+backstop·全 MEP 引用图归 4；§0.3 门①失败分类·§3.2#7 不复用 validator·§3.1 加 attempts/manifest/approval 目标布局·§0.4 改为速查非覆盖）。施工方案 v3 补完整失效 DAG + approval digest + facade canonical schema + per-milestone 验收测试矩阵。Codex 判：三项 must-fix 完成即两 review CLOSEABLE、可直接开工 M0、无需第三轮架构重审。_
_2026-06-15 (v7) — **纳入 Codex 双 review（设计+施工，双 CHANGES REQUESTED，全盘接受）**：§0.3 改失败分类（确定性后置 fail-closed 不弹上游 / 只 stochastic 0/1/4 盲重抽 / 0=manual→human_redraw / 全局预算+循环检测 / hard sample quarantine / 不复用 `_make_correction_validator`）+ verdict schema v2（not_applicable/insufficient_evidence/root_stage/root_confidence/retriable）+ judge 密度自洽；新增 §0.4「Codex 纳入」10 条（facade 仅 image-local·world 落位归 correction / reading schema 迁移 dimension chain+provenance / stroke↔dim 降低置信非 2f 主验收 / 2f 归因 delta-audit / 矩形 coverage 本轮 block / uncaptured 不 block / 4 拥有 MEP 引用图+对象语义+idf_fragments parser·5 仅 backstop / check schema v2 policy-事实分离 / 用户门=调用策略+hash / viewer trimesh 先行）；§1 2/3·5 + §3.2 + §4 不变量 6 同步。机制细节落 [施工方案 v2](../archive/pipeline_validation_build_plan.md)（M0 执行地基→M1 schema/parser→M2a/b/c→M3→M4）。_
_2026-06-15 (v2) — **全文重写按 0–5 口径 + 并入校验门模型 + reading/correction 分工再定**：清掉 phase1/phase2a/phase2b/partA 旧称（§0 图/§2/§3 矩阵/§4 不变量/§5.3 全换 0–5 名）；§0.3 新增逐阶段校验门模型（确定性①+judge②、结构化 verdict 不用数字分、盲重抽、3 次预算、judge=数据工厂、密度按阶段、judge 不给流程额外信息）；§1 0_reading 校验收窄为 per-image（结构 linter/尺寸链闭合/stroke↔dimension 互核/越界 + 七类 VLM judge），**区数/跨图/填色区图移到 1_correction**；1_correction 补填色区图/zone 区图 + 立面 local→world 代码翻译 + 跨图 reconcile + 对参考答案 judge；§4 加不变量 6（judge 不给流程信息）。_
_2026-06-15 (v1) — 并入「逐阶段产物与校验登记」，升级为「输入·输出·校验」活文档（§0.2 三层框架 + §1 每段校验 + §3.2 backlog）。_
_2026-06-09 — 建文档（几何确定性化后权威接线参考）。_
