# 交件 · W-1 的 T3 续做（GLM 施工 / Claude 审）

> **施工 = GLM**（`glm-5.3`）· 工作树 `/tmp/w1_flow_glm`（分支 `wt/09.07h_w1_flow`，基点 `4cc8de33`）
> 派工单：[`reviews/request/2026-09-07p_W1_T3_rework_dispatch.md`](../request/2026-09-07p_W1_T3_rework_dispatch.md)
> 题面 = 复核 [`verdict/2026-09-07l_W1_T3_wip_review.md`](../verdict/2026-09-07l_W1_T3_wip_review.md)（4 阻断 + 2 不阻断 + 附录 A）
> ⚠️ 本交件分两批交付：S1–S4（本批，**含一条 B 类停报**，见 §停报）→ 停报裁决后 S5–S7。

## 自检（§六）

```
$ git log --oneline -1
4cc8de33 09.07q_sync_dispatch: 并入 T3 续做派工单
$ python -c "import src.agent.pipeline as m; print(m.__file__)"
/tmp/w1_flow_glm/src/agent/pipeline.py        ✅ 落在工作树
```

（每段落一条 commit；本批 4 段 4 commits，见 §分段清单。）

---

## ⛔ 停报（B 类 · S4 施工中撞上 · 拍板前提与真产物矛盾）

### 你以为是 X，实际是 Y

**X（拍板书 2026-09-07i §二 T2-③ 的通过理由）**：

> 「四面是同一栋楼的独立观测，一致性是免费的锁；……**sm25 实测四面同为 2 级、层高 3.602 m ⇒ 严格版在真数据上是绿的**，⛔ 没有为了通过而放松」

**Y（我对四份真产物逐面实测）**：**级数**四面确实一致（4×2 级），但 **z 值序列逐面不一致**：

| 面 | F1 z_floor | F1 ceiling | F2 z_floor | F2 ceiling |
|---|---|---|---|---|
| east | −0.0021 | 3.6021 | 3.6000 | 3.6021 |
| north | −0.0018 | 3.6057 | 3.6039 | 3.5922 |
| south | −0.0011 | 3.6007 | 3.5996 | 3.5939 |
| west | −0.0011 | 3.6003 | 3.5992 | 3.6004 |

散布：z_floor F1 **1.0 mm** / F2 **4.7 mm**；层高最大 **13.5 mm**（每张图独立标注/标定，与 T1 实测的 footprint 7–12 mm 残差同源同量级）。

### 证据与归因

- 复现命令（任何人可跑）：`PYTHONPATH=. python -c`，四份产物 = `AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_{east,north,south,west}_as_drawn.json`，逐面 `adapt_as_drawn_elevation` → `derive_floor_ladder`，读数见上表。
- **这不是我的实现错**：T2 方案文本（交件 T2-③）定义的判定就是「比较各级 `z_floor_m` 序列：全一致 → 任取一面；不一致 → `ELEVATION_LADDER_DISAGREEMENT`」。按该定义，真数据红。
- 拍板书的「绿」怎么来的：它引用的实测 = 交件 T2-③ 原文「**实测 East**；其余三面 adapter 均过」——**adapter 过 ≠ ladder 数值一致**；「四面同为 2 级」是级数读数，被滑读成「z 序列一致」。[[citing-someone-elses-fact-does-not-transfer-responsibility]] 的形状，转引处正是拍板书的通过理由。

### 选项与代价（⛔ 我不预设，等主控定）

| 选项 | 做法 | 代价/后果 |
|---|---|---|
| **甲 · 派生容差对账** | 一致性 = z 差在**产物自己声明的标定残差派生的容差**内（同 BLK-1 的零发明常数精神） | 需要设计一个 z 容差派生式（z 是从层数线的像素标定推的 ⇒ 容差可从同一 calibration 声明派生）；改动中等；**四面一致性仍是锁** |
| **乙 · 级数严格 + 差值落账** | 级数不一致 → 响亮失败（保持）；数值差 → 取 manifest 声明序第一面为 carrier，四面差值**落 FLAG 账**（不挡） | 最小、可跑通；「四面一致性」从**锁**降为**记录**；差值可观测 |
| **丙 · 维持严格逐位** | 不动 | **sm25 永远走不通新腿** ⇒ W-1 总验收（端到端跑通）结构性不可达 |

我的推荐（仅供参考）：**乙**——符合用户「先跑通、欠债跑完一次再修」的次序；甲的派生式作为后续加固登记。若主控要甲，派生式的量（标定残差→z 容差）我可以给设计稿再过一轮。

### 停报期间的代码形态（已提交，防悄悄放松）

`_w1_cross_check_elevation_ladders`（`run_stage.py`）**保持严格版文本**（z 序列逐位，不一致 `ELEVATION_LADDER_DISAGREEMENT` 响亮失败），并有一条**正向锁**钉住这个行为：

```
tests/test_w1_flow_routing.py::test_real_products_do_disagree_strictly
  = 四份真产物过该函数 ⇒ SystemExit('ELEVATION_LADDER_DISAGREEMENT')
```

⇒ 裁决前任何人（包括我）把对账放松都会红这条锁；裁决后按主控选的选项改锁。

**S7 端到端跑通依赖本停报的裁决**（四面对账是 flow 新腿 draw 的必经步；选乙/甲才能跑通）。

---

## S1 · BLK-A —— 把「缺席」真的变成信号（commit `5c3a8603`）

- `window_evidence_channel_split_debt`（`evidence_preflight.py`）：`WINDOW_EVIDENCE_ON_CHAIN_NOT_ON_LEDGER` 从两处 docstring 变成可落盘的 `EvidenceDebt`。disposition 按 **evidence-chain 轴**（exploratory=flag / strict=block）；chain 原词进 `evidence["evidence_chain_profile"]`，顶层 `run_profile` 记同侧 RunProfile（exploratory→"exploratory" / strict→"regression"）——**一次显式翻译、原词保留**，⛔ 不是第二套债机制（id 空间装得下：`check_id` 是自由 str；停报触发器未触发）。
- `run_multifloor_correction` 新参数 `evidence_debt_path`：**进入函数先登记**（链预算零消耗），strict 先落盘后 raise（挡本身可审计）；profile 混合的 plan_runs 具名拒 `PLAN_RUN_PROFILE_MIXED`。
- 锁×3：新腿产出债含该 id（exploratory=flag）/ strict 先落盘后挡且 fake 链零调用 / 混合 profile 响亮失败。

## S2 · BLK-E + RED-1 —— 容差只从链消费过的字节派生（commit `1e44a022`）

**选路论证**（派工单要求写明）：选 **(b) 的忠实实现**，但**对账锚不是 `source_resolved_sha256`**——我实测该字段是 **wall compilation 的 content hash**（`projection_bridge.py` 的 docstring 逐字「it IS the wall compilation's content_sha256」），**不是产物字节的 hash**，按字面对账恒不一致。实际锚 = **链在冻结处自己记的 per-floor hash**：

- 链侧（`run_correction_evidence_chain`）：source_read 冻结后算 `sha256(raw)`，落两处——① per-floor sidecar `chain_source_record.json`（`out_dir` 内，⭐ 必要：route 记录是 run 级 last-writer-wins，探针实测 `_run/` 只剩 floor_2 的 route，多层会互相覆盖）；② route 记录加 `source_bytes_sha256` key（route 断言全是单 key 检查，无 exact key-set 金锁，已核）。
- wiring 侧（`run_multifloor_correction`）：链后重读产物 → hash 与 sidecar 对账 → 不一致 = `PLAN_PRODUCT_BYTES_DRIFTED_FROM_CHAIN`、record 缺失 = `CHAIN_SOURCE_RECORD_MISSING`。
- 为什么不是 (a)（链回传 doc）：要动 `run_correction` 返回类型（影响所有调用者）或旁路容器或 envelope（versioned schema 翻搅），三者都比 sidecar 重且收益相同。
- 锁×4 + RED-1 转绿（⚠️ 按派工单提醒，转绿本身不作验收——验收靠字节漂移具名红 + 缺 record 具名红 + 绿半边（对账一致时不可见）+ sidecar 在 source_read 即落盘（链死于 adapt 仍在盘））。

## S3 · BLK-B —— 空 proof 实测过 gate① + finalize 后半段接线（commit `1accba98`）

探针（`experiments/2026-09-07p_w1_s3_probe/run_probe.py`，两段分离）：

- **CASE A（合成干净两层 V3 + 真 manifest/产物字节）**：`build_verified_window_inputs_as_drawn` → `finalize_as_drawn_chain_geometry` → `check_correction` = **passed=True / blocking=0 / 18 结果** ⇒ **空 proof 不在任何不变量上红，S3 停报触发器不触发**。已固化为永久锁 `tests/test_w1_as_drawn_finalize.py::test_empty_window_set_clears_gate1_on_a_clean_assembled_v3`。
- **CASE B（真链 probe 产物）**：红在 `validate_final_corrected_geometry`——cell 边 **4.33 cm** < `min_edge_length_m` 0.10（gate① 的 `_MIN_EXTENT`=0.05 也红）。判定：**链产物质量问题**（两把尺子都是既有不变量、legacy 同样适用；probe 链是 degraded——每层 16 个悬端债），⛔ 不是空 proof 问题。09-02 那次成功链 completion 也是 degraded ⇒ **S7 真模型链可能撞同一堵墙**，已列为 S7 已知风险。
- 新生产函数 `finalize_as_drawn_chain_geometry`（`finalize.py`，`finalize_correction_draw` 一行不动）：finalize 事务的 as_drawn **后半段**——Vg 写 `facade_segments`（bridge 产空表而 `derive_feature_state_claims` 拒空，这是实测撞出的真依赖）→ 空 claims/evidence 账 → `validate_final`（同把尺子）→ identity + evidence ledger。跳过的只是 legacy 前半（envelope 提取吃 legacy ReadingView 静默空壳 + core——新腿几何已过 bridge 自己的核）。
- 锁×4（`tests/test_w1_as_drawn_finalize.py`）：空集全链 gate① 零阻断 / Vg 在链终环落 segments / S1 债随行 FLAG 不 block / 非 v3 target 响亮拒绝。

## S4 · BLK-C —— flow 生产入口接线（commit `09.07u_*`，本批末段）

`scripts/tool_scripts/run_stage.py`：

- `_w1_route_correction`：对冻结 manifest 全部 required entries 的**在盘产物**逐份 `classify_vector_json`（⛔ 不按文件名）→ 全 legacy = legacy 腿（**原代码路径零改动**）；全 as_drawn（plan 槽 `as_drawn_plan` + elevation 槽 `as_drawn_elevation_v0`）= 新腿；as_drawn plan + 零 as_drawn elevation = `ELEVATION_EVIDENCE_MISSING`；其余混法（legacy/as_drawn 混、槽位错放、unknown）= `CORRECTION_MIXED_CONTRACTS`；产物缺文件 = `CORRECTION_PRODUCT_MISSING`；无 manifest 的 standalone run = legacy（那些 run 的既有行为，非静默回退——新腿结构上需要 manifest 的 floor_ref）。
- `_draw_correction_as_drawn`：层序 = 冻结 manifest `floor_ref` 升序构造 `plan_runs`（⛔ 不解析文件名）→ 四面 ladder 对账（⚠️ 停报中，保持严格版）→ `run_multifloor_correction`（S1/S2 的债账 + snap 账 + 授权重读全部接上）→ `build_verified_window_inputs_as_drawn` → `finalize_as_drawn_chain_geometry` → 既有 `check_correction`（expected_zone_total 等照传）→ 返回 flow 标准 `(FinalizeResult, report)` 形状（StageRunner 同一 writer 归档，B5/Vg 校验链对新腿同样生效）。
- chain profile 翻译：permissive RunProfiles（exploratory/dev）→ chain "exploratory"；strict 侧（golden/regression）→ chain "strict"（S1 债按拍板挡，⛔ 不静默）。
- 锁×9（`tests/test_w1_flow_routing.py`）：legacy/as_drawn 路由、无 manifest 保旧、混合/槽位错/零立面响亮、新腿 draw 经 flow 形状端到端（mock 链）gate① 零阻断 + 层序来自 floor_ref + 债/snap 账落位、strict 档翻译 + 挡、**停报锁**（真产物四面对账响亮）。
- ⚠️ **`run_pipeline`（pipeline.py 侧入口）本批未接**：T2 拍板方案的改动面（T2-⑧ 表）不含它，且「旧 case 行为逐位不变」以它为锚；flow CLI 是用户口径的标准入口。若主控要 run_pipeline 也路由 ⇒ 加一件（B 类报备，不算静默跳过）。

## 分段清单（本批）

| 段 | commit | 内容 |
|---|---|---|
| S1 | `5c3a8603` | 通道分叉债登记 + 锁×3 |
| S2 | `1e44a022` | 链授权重读 + RED-1 + 锁×4 |
| S3 | `1accba98` | 空 proof 实测 + as_drawn finalize + 锁×4 |
| S4 | （本 commit） | flow 路由 + 新腿 draw + 锁×9 + 停报锁 |

测试读数（本批涉及文件）：`test_b2_multifloor_assembly` 37 passed、`test_o22m7_evidence_wiring` 全绿、`test_w1_as_drawn_finalize` 4 passed、`test_w1_flow_routing` 9 passed、flow/stage_runner 邻域 65 passed。全量在 S7（停报裁决后）。

## 待办（停报裁决后）

- S5（RED-2 注释）/ S6（RED-3 prescan 登记）/ N-1 / N-2：与停报无关，可在等待期间完成。
- S7 总验收：全量 0 failed + 端到端命令序列 —— **依赖停报裁决**（四面对账是必经步）。

## 最薄弱的一处（本批版，S7 后更新）

**`finalize_as_drawn_chain_geometry` 复用 `validate_final_corrected_geometry` + StageRunner 的 B5/Vg writer 校验链，是我「读码+离线实测」判定新腿产物能被同一套 writer 接受的依据——但我没有把一个真·新腿产物走完 flow 的 StageRunner.record（attempts 归档 + accepted 指针 + 下一 stage 的 loader）实测过**（S4 的 flow-shape 测试 mock 了链，S3 的 CASE B 红在 validate_final 没走到 writer）。如果 writer 链上还有 V3 新腿形态接不上的点（例如 accepted-loader 对 `footprint_snap_ledger.json` 这类新 sidecar 的存在性校验），S7 端到端会在 1_correction 之后的 stage 才爆出来。S7 的端到端命令序列就是这个判定的实测。
