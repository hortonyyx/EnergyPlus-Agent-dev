# 交件 · W-1：让一个 case 能完整跑通端到端（零手搓）

> 施工 = GLM（`glm-5.3`）· 工作树 `/tmp/w1_flow_glm`（分支 `wt/09.07h_w1_flow`，基点 `59b6b102`）
> 派工单：[`reviews/request/2026-09-07h_W1_flow_wiring_dispatch.md`](../request/2026-09-07h_W1_flow_wiring_dispatch.md)
> ⚠️ 本交件分三段交付：T1（本段）→ T2（方案，**待主控拍板**）→ T3（拍板后施工）。

## 自检（§一）

```
$ git log --oneline -1
59b6b102 09.07v_W1_dispatch: W-1 派工单（GLM 施工 / Claude 审）
$ python -c "import src.agent.pipeline as m; print(m.__file__)"
/tmp/w1_flow_glm/src/agent/pipeline.py        ✅ 落在工作树
```

---

## T1 · 端到端手搓点普查（实测记录）

方法：以 sm25-L_anchor 为主 case（2 层、6 视图、有 gt、有 4 份 as_drawn 新格式产物 + legacy 全套产物），
用标准入口 `run_stage.py flow` 实走；每撞一处「必须现场手写/手拷/手填」记一条。
所有行号均为 `/tmp/w1_flow_glm` 树上、基点 `59b6b102` 的读数。

### T1.1 手搓点清单

| # | 段 | 撞到什么（实测） | 今天只能怎么绕 | 最小修法（→T2） |
|---|---|---|---|---|
| **A** | 0_reading 产物 | flow 的 0_reading 是 MANUAL 校验器（`run_stage.py:340`「validate the already-produced view JSONs (no LLM)」）。实跑空 run：`⛔ reading.present: no 0_reading/*_view.json found` + `8 required view(s) have no matching produced artifact`。产物必须先在外面产好。legacy 痕量的标准编排**存在**（`spawn_isolated_reader.py build`，一次 kickoff 覆盖 run 全部 images）；as_drawn 新格式的产出器（`reading_toolbox.py build` / 实验原型 `as_drawn_elev.py`）**每份要人工标定 cfg + perception，无 case 级编排** | 从既有 run / 实验目录逐字节拷贝（09-02 即如此）| 本单不修（reading 编排是另一单）；本单只要求**现成产物能以标准文件名落位并被 flow 消费** |
| **A2** | 0_reading 产物文件名 | view_manifest coverage 检查（`view_manifest.py` `check_reading_stage`）只认 `{expected_output_id}.json`（= input_id stem，如 `1f_view.json`）。as_drawn 实验产物名为 `sm25_2f_v2.json` —— **不在 expected set → BLOCK**（extra_stems）| 手工改名拷贝 | 接线时把 as_drawn 产物按 manifest 的 input_id 落位（`1f_view.json` 内容= as_drawn 格式，coverage 只看 stem 不看内容 schema —— 实测确认 `check_reading_stage` 只比 stem 集合） |
| **B** | 1_correction 选腿 | `run_stage.py:457` `run_correction(...)` 不传 `evidence_chain` ⇒ 全部走 legacy pasted-JSON 腿。新腿 `run_multifloor_correction`（`pipeline.py:1639`）生产零调用者（唯一调用者 `tests/test_b2_multifloor_assembly.py`）。**flow CLI 零路由感知**：`classify_vector_json` 在 `run_stage.py` 零命中（与主控读数一致，已复现）| 手写脚本直调 `run_multifloor_correction`（09-02 形态） | **本单主接线点**，见 T2 |
| **B2** | 1_correction 新腿后处理 | ⭐ 实测发现的新断点（派工单未列）：`_draw_correction` 在 `run_correction` 之后还有一段 V3 后处理链：`build_observation_reference_catalog_from_run` → `build_verified_window_inputs_from_run` → `finalize_correction_draw`。其中 `finalize.py:117` 对 `schema_version=="3"` **强制要求** `verified_window_inputs`，而它只能从 legacy `ReadingView` 产物构建（`window_sources.py:313 _window_strokes` 走 `parse_reading_view` 的 `pen=="window"`）。实测：as_drawn 立面产物被 `ReadingView` **静默解析成空壳**（`facade=None, strokes=0`），随后 `derive_manifest_direction_facts` 崩 `direction_fact_invalid`（`input_integrity_error` → hard crash）| 今天无绕法 —— 新腿产物（`projection_bridge.py:851` `windows=[]`）根本过不了 flow 的 gate① 链 | T2 给出：新腿分支的 finalize 组装方案 |
| **C** | reading_summary.md | `pipeline.py:385` F-2b：correction 要求 `0_reading/reading_summary.md`（kickoff contract）。实测拷产物漏了它 → `FileNotFoundError`。flat 手拷不带 summary（isolation merge 才带）| 手拷 | 新腿不吃 summary（evidence chain 不读它）；legacy 路不动 |
| **D** | 层序（plan_runs 自下而上） | ⭐ **产物自声明路径已找到，不需要停报**：`view_manifest` 的 `RequiredViewEntry.floor_ref: int`（`view_manifest.py:404`），来自 `case_data/testdata_prompt.json` 的 `'Floor plans'[].floor`（**声明性元数据，⛔ 非文件名解析**），冻结在 `_run/view_manifest.json`，且有硬校验（`view_manifest.py:505-510`「1-based, ascending」`manifest_floor_ref_non_contiguous`；注释明写「B5's floor mapping is intentionally not OCR/name based」） | 手排 plan_runs 顺序 | T2：按冻结 manifest 的 plan entries `floor_ref` 升序构造 `plan_runs[i]` |
| **E** | elevation_evidence 来源 | `run_multifloor_correction` 要封印载体 `CorrectionEvidenceBundleArtifactV1`。生产者 = `evidence_adapters.py:614 adapt_as_drawn_elevation(raw, input_id, facade_ref)`（对**一份**立面产物字节）。实测 sm25 四立面产物（`sm25_{east,north,south,west}_as_drawn.json`）全部过 adapter，各推 3 条 floor_level_claims → `derive_floor_ladder` = 2 级、z_floor −0.002/3.600、层高 3.602 m（与立面声明 3600 mm 一致）；两平面产物（`sm25_{1f,2f}_v2.json`）各 22 wall_claims + 85 opening_claims | 手调 adapter | T2：接线时从 0_reading 读立面产物 → adapt → ladder |
| **F** | 续跑半途 run 的 profile | 实测：R0 克隆 run 续跑 `flow` 直接 `run_policy_drift` 拒绝 —— flow 的 profile 解析**不回读冻结记录**（`cmd_flow` 走 `_resolve_run_profiles`，run_config 缺失时用 CLI 默认 rectangular，而 R0 冻结的是 orthogonal_polygon）。`judge` 子命令有回读（`resolve_frozen_run_policy`），flow 没有 | CLI 带上 `--capability-profile orthogonal_polygon` | 记为 friction（B 类）；不改（不动本单范围） |
| **G** | judge stop 模式 | R0 类 run 的每段过 gate① 后 `awaiting_judge`，要人写 StageVerdict JSON 提交（`judge ... --verdict`）。无人值守全程需要 **run 建立时** run_config 就声明 `judge: mode: off`（事后改会撞 F 的 drift 拒绝 —— 这是 policy freeze 的设计） | 提交 verdict（实测已走通）| 不修（设计内人工门）；T3 的命令序列含「先写 run_config 再 flow」 |
| **H** | 出分 judge sidecar | flow 跑中报警（实测）：`v3 GT is present but required judge sidecar(s) are missing (judge_score_bindings.json); the v3 scoring layer was skipped`。生产 CLI = `build_score_view_bindings.py --run-dir --gt`（**不在 flow 里，要人记得跑**） | 手跑 | 记录：judge-owned 工具，本单不接（W-2 范围）；但 T3 命令序列会含它 |
| **I** | record | `flow --record` 要求 `--orchestrator <名字>`（实测代码 `run_stage.py:3100`）；reading_mode 必须已声明（`require_reading_mode=True`，M-1）。均为传参，非手搓 | 传参 | 不修 |
| **J** | EP | `_flow_ep`（`run_stage.py:2584`）接线完好，EPW 默认 `data/weather/Shenzhen.epw` 存在，`energyplus 25.1.0` 在 PATH。`--with-ep` 即走 | 已具备 | 不修 |
| **K** | gt 链路 | sm25 已有冻结 gt（`case_tests/test_baseline/gt/sm25-L_anchor/`）⇒ 本单 case **无需**走 `gt_from_dxf → review_build → review_sign → promote`。该链本身含人工签字（review_sign），是设计内 gt 建设流程，非 case 跑通的手搓点 | 用既有 gt | 不修 |

**新腿两样输入在 flow 上下文的来源（派工单点名单列）：**

1. `elevation_evidence: CorrectionEvidenceBundleArtifactV1` → `adapt_as_drawn_elevation(0_reading/{立面input_id}.json 的字节)`（产物自声明 `facade_label` 作 facade_ref 语义槽；`pipeline.py:1119-1126` 的既有口径）。
2. `plan_runs: Sequence[MultiFloorPlanRun]` → 冻结 `_run/view_manifest.json` 的 plan entries 按 `floor_ref`（声明 int、1-based 升序）排序，一一构造（vector_dir=0_reading，product_filename=`{input_id}.json`）。
   层数对账：`len(plan_runs) != len(ladder)` → `FLOOR_PLAN_COUNT_MISMATCH`（`pipeline.py:1682` 已有，响亮）。

### T1.2 今天的行为基线（legacy 路径实跑读数）

**基线 1 · 新 run 全流程（run_t1_probe，产物 = H2 的 6 份 legacy view JSON + 手拷 summary）**

```
flow sm25-L_anchor run_t1_probe --judge off --geometry auto
```

- 0_reading：gate① `passed=True, block=0, flag=4`（4 条 flag = partition_on_window_jamb / stroke_dimension_consistency × 2 层）
- 1_correction：**真模型（deepseek-v4-pro）3 draws 全部花完 → quarantined**，~46 min：
  - 14:29 draw1 内层试1 拒（`v3 per-floor footprints must have identical geometry`）
  - 14:47 draw2 内层试1 拒（`cell floor_footprint: polygon edge 3 is not orthogonal`）
  - 15:13 draw3 内层试1 拒（`hit max_tokens — response likely truncated` → JSON 解析失败）
  - 终局 block：`correction.window_source_reference: window source reference rejected (elevation_floor_mismatch): window_id 'w1f_04', candidate_floors ['floor_2']`
- F-97 ledger（确定性读数，`_run/reading_vector_contract_ledger.json`）：`consumed=6 view json, adapted=[], counts.consume=6` ← **T3 前后对账的锚点之一**

**基线 2 · 历史绿 run（run_2026-08-25_c2_rescore_R0，入库提交 `bdbf8154`）**

- 1_correction：gate① `passed=True, block=0, flag=0, attempts=1`（同产物同腿，模型随机性 → 一次绿一次 quarantine；两读数都记，⛔ 不拿单次红下结论）
- 提交记录原文：L 形外轮廓 8 顶点逐点对上、31 扇窗、F1 20 cells / F2 18 cells、总面积 279.2 vs gt 290.0；F-90 判分整份被拒（楼层 id 映射）

**基线 3 · R0 克隆续跑（run_t1_legacy_full）—— 下游 2→5 段 + record 的通行性**

- 带 `--capability-profile orthogonal_polygon`（对齐冻结 policy）续跑：2_modelling ✅ →
  3_split_pairing ✅ → 4_mep ✅（deterministic_pass）→ 5_intakeoutput 在
  `_ensure_orientation_enriched` → `StageRunner.record` 撞 `writer_core_projection_drift`
  （B5 门拒绝 8-25 老产物：deterministic core stamp 版本已变 ⇒ 重放投影不一致）。
  **门行为正确**（防篡改在干活）；含义 = 老 run 不可跨代码版本续跑，全链必须用今天的代码从头跑。

**基线 4 · legacy 重试（run_t1_probe2，同树同代码第二次）—— 「一次红不是证据」纪律的补跑**

```
flow sm25-L_anchor run_t1_probe2 --geometry auto --record --orchestrator glm-5.3-t1probe2
（run_config：judge off 自 provision 起声明）
```

- 0_reading：gate① `passed=True, flag=4`（同基线 1）
- 1_correction：**再次 quarantined**（3 draws 花完，~50 min），终局 block 换了一副面孔：
  `correction.window_host_resolution: window host resolution rejected (3 conflict(s)):
  1f_G01:source_geometry_mismatch; 1f_G02:source_geometry_mismatch; 2f_G02:zero_room_interval_candidates`

⭐⭐ **两次同树同代码的 legacy 1_correction 均 quarantine**（终局原因各异：第一次
`elevation_floor_mismatch`、第二次 `window_host_resolution`）⇒ 按「重跑至少 2 次」纪律互证：
**legacy 真模型腿在 sm25 上今天稳定过不了 gate①（读数 0/2），而 R0（8-25 代码）当时一发绿。**
腿本身是通的（evidence_debt → prompt → 模型 → parse → finalize → check_correction 全链执行，
产物 attempts 全归档）—— 卡的是模型画图质量，不是接线。⇒ **本单接新腿正是「让 case 能跑通」
的路径**：evidence chain 把「模型画整张图」改成「模型只拍板裁决项」（09-02 实测 2 轮 success，
185.8 s）。

### T1.3 ⭐ 派工单 §二 右栏四问的实测回答

| 问 | 实测答案 |
|---|---|
| ① flow 今天怎么定层序 | **不自己定**：legacy 腿把整个 0_reading 目录糊进 prompt，层序在模型脑子里；新腿需要显式层序 → 用冻结 manifest 的 `floor_ref`（见手搓点 D） |
| ② flow 现跑 case 的 reading 产物新旧 | H2/R0 = **全 legacy**（6 份 `*_view.json`，分类器实测全 `reading_view_legacy`）；sm25 的 as_drawn 新格式产物只存在于实验目录（2 plan + 4 elevation，分类器实测 `as_drawn_plan` / `as_drawn_elevation_v0`，见手搓点 E）。**混合产物目录今天不会被 flow 遇到**（coverage 检查按 expected stem 收，多出来的 as_drawn 文件名会 BLOCK） |
| ③ 接新腿后旧 case 会不会变 | 新腿只在「全 as_drawn 产物」时进（T2 方案）；legacy case 的代码路径不动。对账锚点：F-97 ledger 逐位不变 + 全量测试 4009 绿（T3 验收） |
| ④ `CorrectionEvidenceBundleArtifactV1` 从哪来 | `evidence_adapters.adapt_as_drawn_elevation / adapt_as_drawn_plan`（见手搓点 E）；flow 上下文里对 0_reading 的产物字节现场 adapt |

### T1 续记 · 新腿全程真模型探针（可行性证据，⭐ 撞出新的结构事实）

在 flow 上下文之外直调生产入口 `run_multifloor_correction`（09-02 同形态、扩到整 case）：

- 输入：`elevation_evidence = adapt_as_drawn_elevation(sm25_east_as_drawn.json 字节)`；
  `plan_runs = [1f_v2, 2f_v2]`（按 manifest floor_ref 序）
- 每层 evidence chain **各自真模型跑完**（decision loop 正常，deepseek-v4-pro），
  产物：`projection_envelope.json` 各层落盘（floor_1: 16 cells / floor_2: 16 cells，均 degraded 悬端债随行）
- **assemble 处响亮失败**：

```
MultiFloorAssemblyError: PER_FLOOR_FOOTPRINT_MISMATCH:
{'floor_ids': ['1f', '2f'], 'reason': "assembly is common-footprint only (invariant #6);
 per-floor different footprints (setback) are not B2's job"}
```

⭐ 实测两层 footprint 差（投影后）：

| | footprint_x | footprint_y |
|---|---|---|
| 1f | [0.1137, 24.8841] | [0.1175, 19.8784] |
| 2f | [0.1253, 24.8715] | [0.1244, 19.8770] |
| 差 | ~11.6 mm | ~6.9 mm |

⭐⭐ **这是 as_drawn 产物跨图标定的毫米级残差，不是真 setback**（同一栋 L 形楼、两层
真形状一致；每张图独立标定 ⇒ 世界坐标各自带 ~10 mm 残差）。assemble 的 fingerprint 比较
是零容差 ⇒ 残差被当 setback 拒绝。按用户 2026-09-07 的领域口径
（「吸附/分辨率残差机器直接修、真画错才签字」），这类残差属于「机器直接修」类 ——
但**在哪一层修、怎么记账**是 T2 的拍板点（见 T2-④），⛔ 我不擅自加容差动锁。

另两个 T1 探针读数：
- R0 克隆（run_t1_legacy_full）：2_modelling ✅ → 3 ✅ → 4_mep ✅ → 5_intakeoutput 的
  record 撞 `writer_core_projection_drift` —— B5 门拒绝 8-25 的老产物（core stamp 版本已变）。
  **门是对的**（防篡改在干活）；含义 = 一个 case 要用**今天的代码**从头跑，老 run 不可跨版本续跑。
- 空目录 + 缺 supp_plan（sm20 探针）：manifest 8 required view、老 baseline 只产过 7 个
  （supp_plan_view 从未产出）⇒ sm20_anchor 今天走 flow 会永久卡 0_reading —— 记为 case 数据现状，不修。

---

## T2 · 方案（⭐ 到此停下，等主控拍板；⛔ 未动任何代码）

### T2-0 设计总则

- **沿用「路由由分类器判定、⛔ 永不按文件名」**（`pipeline.py:1048` 既有口径）：判的是**产物字节**走哪条腿；
- **层序用声明源**：冻结 view_manifest 的 `floor_ref`（`testdata_prompt.json` 声明 → provision 冻结 → hash 锁），
  ⛔ 不从文件名解析 —— 与路由口径正交（路由管腿、manifest 管层）；
- **legacy 路一行不动**；**无任何静默回退**（新腿失败 = 响亮失败）；
- 最小改动集 = `scripts/tool_scripts/run_stage.py`（接线）+ `src/agent/pipeline.py` /
  `src/agent/correction/multifloor.py`（仅 T2-④ 需要主控点头的那一小步）。

### T2-① 选腿（在 `_draw_correction` 入口处，`run_stage.py:414` 之后）

对 `0_reading` 的全部 `*_view.json` 逐份 `classify_vector_json`（classifier 的 verdict，与
`_preflight_vector_contracts` 同源 —— F-97 ledger 已经是这个函数写的，路由判定天然入账）：

| 分类结果 | 走向 |
|---|---|
| 全部 `reading_view_legacy` | **现路径逐位不变**（同参数调用 `run_correction`，代码零改动） |
| 全部 `as_drawn_plan` + ≥1 `as_drawn_elevation_v0`（本 case manifest 的 plan/elevation entries 全部有对应产物） | 新腿（T2-②③④） |
| 混合（legacy 与 as_drawn 同目录） | 响亮失败：`SystemExit`，命名 `CORRECTION_MIXED_CONTRACTS`（列两边文件） |
| 有 as_drawn plan 但零 as_drawn elevation | 响亮失败：命名 `ELEVATION_EVIDENCE_MISSING`（没有 ladder 来源；⛔ 不落回 legacy） |
| 任何 `unknown` / 未接线契约 | 响亮失败（分类器+ledger 已有此行为，不重复造） |

### T2-② 层序（`plan_runs` 自下而上）

1. 读冻结 `_run/view_manifest.json`（`cmd_flow` 已 provision，`_manifest_for_attempts` 在场）；
2. 取 plan entries，按 `floor_ref`（声明 int）升序 ⇒ `plan_runs[i]` ↔ 第 i 级；
3. `MultiFloorPlanRun(vector_dir=0_reading, product_filename=f"{input_id}.json",
   out_dir=run_dir/"1_correction"/f"floor_{floor_ref}", profile=policy.run_profile, round_budget=3)`；
4. 数量对账交给既有 `FLOOR_PLAN_COUNT_MISMATCH`（`pipeline.py:1682`）。

### T2-③ elevation 证据与 ladder（`elevation_evidence` 的来源）

1. 枚举 manifest elevation entries → `0_reading/{input_id}.json` 字节 →
   `adapt_as_drawn_elevation(raw, input_id=..., facade_ref=产物自声明 facade_label)`；
2. **四面 ladder 一致性对账**（⭐ 拍板点 1）：`derive_floor_ladder` 逐面跑，比较各级 `z_floor_m` 序列：
   - 全一致 → 任取一面（取 manifest 声明序第一）作 `elevation_evidence`；
   - 不一致 → 响亮失败：命名 `ELEVATION_LADDER_DISAGREEMENT`（列各面 z 序列）。
   我的推荐 = 四面全对账（四面都是同楼的独立观测，一致是免费的一致性锁；任选一面 = 把
   「选哪面」变成隐性任意性）。若主控认为过严（例如某面产物缺层数线），可降级为
   「至少一面成功且全部成功面两两一致」。
3. sm25 实测：四面各推 3 条 floor_level_claims、ladder 均 2 级（z=−0.002/3.600、层高 3.602 m）——
   一致性对账在真数据上是绿的（实测 East；其余三面 adapter 均过）。

### T2-④ 跨层 footprint 毫米残差（⭐ 拍板点 2 —— 不解决则 sm25 走不通 assemble）

现状：两层投影 footprint 差 7~12 mm（跨图标定残差）⇒ `PER_FLOOR_FOOTPRINT_MISMATCH`。
候选：

- **(γ) 我推荐：assemble 前显式吸附步** —— `multifloor.py` 新函数
  `snap_footprints_to_reference(geometries, *, tolerance_m)`：以 ground 层（plan_runs[0] 的投影）为
  参照，把上层 footprint 顶点逐点吸附（对应顶点距离 ≤ tolerance 才动），**吸附账逐顶点落盘**
  （`1_correction/footprint_snap_ledger.json`，接线层 sidecar）+ evidence_debt 登记
  `FOOTPRINT_SNAP_APPLIED`（exploratory FLAG / strict 挡，走既有政策表）。容差取
  `max(2×tolerance_resolution_m, 0.05 m)`（投影分辨率的两倍，来源 = 产物自声明 `tolerance_resolution_m`）。
  超容差 ⇒ **不吸附、原样交给 assemble** ⇒ 既有 `PER_FLOOR_FOOTPRINT_MISMATCH` 照常红（真 setback 不被吞）。
  理由：符合用户领域口径（吸附/分辨率残差机器直接修、真画错才签字）；invariant #6 的零阈值锁**不动**；
  既有测试不受影响（合成夹具 footprint 精确一致 ⇒ 吸附零位移）。
- (α) 不吸附、改用「以 1f 为锚重投影 2f」—— 把 2f 的 calibration 绑到 1f：动 as_drawn 产线，超出本单。
- (ε) 放宽 assemble 的 fingerprint 容差 —— 动 invariant #6 的锁，需要独立审，⛔ 不在本单。

### T2-⑤ 新腿产物的 gate①（⭐ 拍板点 3 —— B2 手搓点的解法）

新腿返回的 V3 已过**它自己的确定性 core**（projection_bridge 的 cut/partition/cells + assemble 的
z-stack/footprint/z 校验），旧腿的 `finalize_correction_draw` 链（envelope 提取 + window 通道）
对 as_drawn 目录**语义不适用且实测崩**（`load_reading_view` 空壳 + `direction_fact_invalid`）。
方案：

1. **不调** `finalize_correction_draw`（旧腿专用，一行不动）；
2. 新腿分支构造 `verified_window_inputs` 的 **as_drawn 版合法空集**：新函数
   `build_verified_window_inputs_as_drawn(manifest, raw_reading_artifacts)`（`window_sources.py`）——
   rows = `()`（as_drawn 的窗证据走 evidence chain 的 opening_claims，**不进** legacy 的
   pen-stroke 账本），facts = manifest `building_axis` + 产物 `facade_label` 走既有
   `_resolve_facade_flip_fields`（不再 `parse_reading_view`）。复用
   `build_verified_window_resolver_inputs` 的 canonical 装配（同一指纹规则，不造第二套）；
3. window host proof/evidence（gate① 硬要求，`geometry_validator.py:285`）走 finalize 同款
   `resolve_window_hosts`（空 claims 合法构造 —— producer `windows=[]`，账实相符：无窗可裁）；
   ⭐ 配套显式 debt：`WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER`（exploratory FLAG / strict 挡）——
   把「窗证据在 chain 里、不在 legacy 账本里」这个事实**记账而不是静默**；
4. gate① 用既有 `check_correction`（expected_zone_total 等全部照传）+ attempts 归档走
   `StageRunner`（与旧腿同一 writer —— B5 replay 门对新产物同样生效）。

### T2-⑥ 旧腿不变的对账方案（验收 2 的证据结构）

1. 全量测试 `-n 6`（主控基线 4009 passed / 0 failed / 2 skipped / 13 xfailed）；
2. **F-97 ledger 逐位对账**：改造前后各跑一次 legacy case 的 `flow`（0_reading 后即止，
   1_correction 起手就写 ledger）⇒ `reading_vector_contract_ledger.json` diff 必须为空；
3. 代码路径审计：legacy 分支的 `run_correction(...)` 调用参数 diff 一致。

### T2-⑦ 失败形态总表（⛔ 无静默回退）

| 输入形态 | 行为 | 命名 |
|---|---|---|
| 混合产物 | 响亮失败 | `CORRECTION_MIXED_CONTRACTS` |
| as_drawn plan 无 as_drawn elevation | 响亮失败 | `ELEVATION_EVIDENCE_MISSING` |
| 层数 ≠ ladder 级数 | 响亮失败（既有） | `FLOOR_PLAN_COUNT_MISMATCH` |
| 四面 ladder 不一致 | 响亮失败（新） | `ELEVATION_LADDER_DISAGREEMENT` |
| 跨层 footprint 残差超容差 | 响亮失败（既有） | `PER_FLOOR_FOOTPRINT_MISMATCH` |
| 残差被吸附 | 吸附账落盘 + debt（新） | `FOOTPRINT_SNAP_APPLIED` |
| 证据包缺/字节漂移 | 响亮失败（既有 B3 门） | `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE` 等 |
| 新腿 chain 终局无产物 | 响亮失败（既有） | `EvidenceChainTerminal` |

### T2-⑧ 预计改动面

| 文件 | 改动 | 性质 |
|---|---|---|
| `scripts/tool_scripts/run_stage.py` | `_draw_correction` 路由分支 + 新腿 draw 函数（~120 行） | 接线 |
| `src/agent/correction/window_sources.py` | `build_verified_window_inputs_as_drawn`（~40 行） | 格式适配（复用 canonical 装配） |
| `src/agent/correction/multifloor.py` | `snap_footprints_to_reference`（~50 行，T2-④ 拍板后） | 显式吸附步 + 账 |
| `src/agent/pipeline.py` | `run_multifloor_correction` 内插吸附步（1 处调用） | 同上 |
| `tests/` | 新腿路由/失败形态/吸附账的单测（含旧腿 ledger 逐位不变锁） | 锁 |

⭐ **明确不做**（对齐派工单 §三）：0_reading 产齐编排、gt 链自动化、W-2 判分锁、
F-137/F-131/F-134/G-g/F-149、任何重构。

---

## ⛔ 停下点（本交件当前状态）

T1 普查完成（上）；T2 方案如上。**等主控对三个拍板点回复后进 T3**：
① 四面 ladder 一致性对账（推荐：全对账）② footprint 毫米残差的吸附步（推荐：γ 方案）
③ 新腿 gate① 的空集 window inputs + 显式 debt（推荐：如 T2-⑤）。

T1/T2 阶段产物（工作树 `wt/09.07h_w1_flow`，本 commit）：
- `case_tests/e2e_tests/sm25-L_anchor/run_t1_probe{,2}/`（legacy 基线 run × 2，judge off 声明在案）
- `case_tests/e2e_tests/sm25-L_anchor/run_t1_legacy_full/`（R0 克隆续跑 + J1 verdict 复现件）
- `case_tests/e2e_tests/sm20_anchor/run_t1_probe/`（sm20 八视图缺一现状复现）
- `AI_agent/logs/experiments/2026-09-07h_w1_t1_probe/`（新腿探针产物：两层 projection_envelope + assemble 失败复现）
- 主树交件即本文件

## 最薄弱的一处（派工单 §七 4 —— T1/T2 阶段版，T3 后更新）

**我对「新腿 gate① 可走空集 window inputs + resolve_window_hosts 空账」的判断是读码+离线
adapter 实测推出的，没有真正把一个 assembled V3 喂进 `check_correction` 跑过**（探针在
assemble 的 footprint mismatch 处就停了，没走到 gate①）。如果这个判断错（例如空 proof 在
`window_host_claim_issues` 的某条不变量上红），T2-⑤ 的方案 3 要改成「新腿 gate① 用独立的
check 入口」——改动面不变但深度增加（要写新 check 而不是复用）。T3 开工第一件事就是拿
探针产物实测这条路，错了立刻回报。
