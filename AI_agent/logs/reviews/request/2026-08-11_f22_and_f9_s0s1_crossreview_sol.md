# 交叉审请求｜F-22 判卷出模约定修法 + F-9 路线② S0/S1（Claude 侧施工 → GPT 侧审）

**日期**：2026-08-11 · **产物方**：Claude 侧执行档（两个独立席位并行）· **审阅方**：GPT 侧（sol）
**依据**：CLAUDE.md §5#8「谁写谁不批」——本批施工全在 Claude 侧，故终审必须跨家族。
**基线**：施工前全仓 2361 绿 / 10 xfail / 0 红。

---

## 0. 先读这一段：两摊共用一个工作区

两个席位**并行**改同一棵工作树，文件不重叠，但请审阅时注意分账：

| 摊 | 文件 |
|---|---|
| **F-22**（判卷侧） | `src/agent/judge/{correction_score,reading_score}.py` · `scripts/tool_scripts/{run_stage,render_grade}.py` · `tests/{test_judge_batch_b,test_render_grade,test_c2_b4b_contract,test_e2e_break_r2_locks}.py` |
| **F-9 S0/S1** | `src/agent/correction/{schema,parse,facade,facade_applicability,window_sources}.py` · 新增 `src/agent/correction/{facade_convention,window_position}.py` · `src/agent/judge/score_inputs.py`（S1 的第 4 个消费点）· 新增 `tests/test_f9_route2_s{0,1}_*.py` |

⚠️ 施工期间 F-22 席位执行过一次 `git stash`，短暂波及 F-9 席位的未提交改动。
**orchestrator 已独立核实无丢失**（F-9 的 80 条锁全绿 + 文件齐全 + stash 栈只剩两条历史批次旧条目）。
**请审阅方独立复核这一点**（这是本批最容易藏事故的地方）。

---

## 1. F-22 是什么活

判卷侧把已经在**外墙外皮**框的产物**又外扩了一次半墙厚**，导致外圈系统性偏 **0.12 m**。
根因：换算写于 07-08（当时产物确在**墙中轴**框，换算正确）；**08-09 的 F-17 修法把 envelope 变换修好后，
产物自己就到外皮框了，判卷侧没跟**。

**⭐ 登记时只点了一处换算，orchestrator 发单前实测发现是两处**（同一假设的第二处实现）：

| 位置 | 作用 | 可观测性 |
|---|---|---|
| `_boundary_centerline_to_outer` | 外包边界四条边各外扩半墙厚 | **不可观测** —— `LineMatch` 无 status 字段、判定二值（≤0.30 即命中）⇒ 0.12 记进 `delta` 却无人上色 ⇒ 全绿 |
| `_expand_boundary_span` | **内墙线段**端点碰边界时各外扩半墙厚 | 可见但被误读 —— 9 段内墙 `extent_drift=true`、状态从 `complete` 降级为 `within_tol`，**而 `wall_hits` 仍报 4/4、5/5 ⇒ headline 不变** |

**修法三条**（用户 08-10 拍板范围 + 08-11 补定接缝要求）：
① 唯一出模形式写成**一处具名声明**（`CORRECTION_OUTPUT_CONVENTION`），并作为将来「标注/墙厚/出模」专项的**接缝**，
**但本批只实现这一种** —— ⛔ 不实现开关、不加配置项、不加分支；
② 删掉两处换算；③ 外包边界补「容差内=橙色」第三档（与墙段同口径）。
**gt 文件一字未改。**

---

## 2. F-9 S0/S1 是什么活

设计稿 [`proposals/f9_route2_evidence_citation_design.md`](../../../proposals/f9_route2_evidence_citation_design.md) v2.1
（已过对抗审 + 轻门）的头两步，**只做 S0 + S1，不接 live production**：

- **S0** = 阶段合同/错误词表/artifact 版本壳（raw type、`CorrectionTarget` 职责拆分、raw projection context、
  resolver artifact V2、显式 loader registry、typed error categories）。
- **S1** = 把 **4 处** facade sign convention 副本 + 5 处 inline XOR 合并成单源 `facade_convention.py`（gt-free）。

---

## 3. orchestrator 轻门已做的机械核实（**请独立复现，勿采信本节结论**）

| 项 | 结果 |
|---|---|
| F-9 两个锁文件独立跑 | **80 passed**，与施工席自陈逐字一致 |
| S1 truth table 是否手写字面量 | ✅ 是（附手推公式；顶点环取 x∈[2,10]/y∈[3,7] 非零 ⇒ `along_origin` 真被行使，不会碰巧等于 0）|
| 4 处副本是否真的归零 | ✅ 全仓 grep：本地 `_BASE_SIGN`/`_CONVENTION`/`_AXIS` 表**零残留**，XOR **全仓只剩 `facade_convention.py:112` 一处** |
| F-22 修前症状复现 | ✅ 真实产物 `run_2026-08-11_continuous_e2e` attempt 001：外包 8 条 `±0.12`、内墙 9 段 `extent_drift=true` |
| 历史产物框的翻转点 | ✅ 独立量了 sm21 全部 14 个 run：f17 及以前 `[0.12,14.88]`；f18 起 `[0,15]`；**三个 legacy probe run 是 `[-0.1,14.65]`（两种都不是）** |

---

## 4. ⛔ orchestrator 挂的 finding（请重点打这一条）

**`CORRECTION_OUTPUT_CONVENTION` 的声明文本，适用范围写宽了。**

声明里写「1_correction 产物的外轮廓**现在已经**表达在外皮上」。实测：

- 外皮框来自 `apply_v3_envelope_transaction`，而它**只在 `schema_version == "3"`（`capability_profile=orthogonal_polygon`）时才走**
  （`deterministic.py:_apply_envelope_reconcile`）；
- `capability_profile=rectangular`（legacy schema v1）走 `_apply_legacy_envelope_reconcile`，产物**不在外皮框**；
- 而 **`run_stage.py:2824` 的 CLI 默认值就是 `rectangular`** —— run_config 漏写该项即静默落到这一档
  （盘上 28 份 run_config 有 24 份显式声明，今天的 SOP 声明 `orthogonal_polygon`）。

⇒ **判卷侧现在写死"产物在外皮框"，而生产侧的框由 `capability_profile` 决定 —— 同一事实的两处声明，可以各自漂。**
这正是**轴 B**那一族。请审阅方判定：
① 声明文本是否必须显式限定适用范围（v3/orthogonal_polygon）；
② 是否需要一道**廉价的守卫或 provenance**（例如把假定的 convention 记进侧车、或对 v1 产物显式拒绝/标记），
   还是留给「标注/墙厚/出模」专项；
③ 本批是否可以在不加守卫的情况下落库。

**⚠️ orchestrator 的立场**：不认为这条构成 BLOCKER（活路径声明了 v3、全仓绿、用户已拍板单一出模形式），
但**认为声明文本必须限定范围** —— 一句适用范围过宽的声明，正是将来"两边各自漂"的起点。

---

## 5. 施工席自报的一条超预期实测（请核实其定性）

F-22 席位在 P4（老 run 重跑判卷的影响面）里测了 **46 个真实历史 attempt**，报告：

- 当前约定的 run：`0.12 → 0.0`，**改善**；
- pre-f18 的 v3 run：`0.0 → ±0.12`，**恰为预期值**；
- **三个 legacy probe run**（`probe_a_legacy_snapped` / `wall3_a_retest` / `f13_e2e_verify`）：
  外包 N/E 边**从"命中但偏移大"直接变成脱靶**（`read=None`），内墙 `wall_hits` 从 5/5 掉到 2/5、4/4 掉到 0/4
  ⇒ **真实的判定翻转，不只是"变差 0.12"**。

**orchestrator 独立复核了成因**：这三个 run 的 footprint 是 `[-0.1, 14.65]`，**自带约 0.22 m 配准偏移**，
旧的双重外扩恰好把 E 边的 `-0.35` 补成 `-0.23`、压进 0.30 容差 ⇒ **删掉换算后露出的是本来就存在的偏差**。
⇒ orchestrator 定性：**不是新引入的缺陷，是原本被掩盖的偏差重新可见**，方向正确。
**请审阅方独立判这条定性是否成立**（若成立，它是本批的正向证据而非风险）。

---

## 6. 请审阅方重点打的方向

1. **§4 那条 finding**（声明适用范围）——是否够、是否需要守卫。
2. **两把改写的老锁是否退化成空锁**：`test_judge_batch_b.py` 的两把老锁夹具从轴线框改成了外皮框，
   请验「把删掉的换算恢复回去，这两把锁是否真的转红」。
3. **`SCORER_SCHEMA` 9→10 的两把字面值锁**：请验第二把（`test_major1_stale_schema_sidecar_recomputed_current_reused`）
   的"陈旧侧车 vs 当前侧车"两侧**没有被一起改成同一个值**（那会把这把锁改废）。
4. **F-9 的 AST structure lock 是否可被绕过**（施工席声称静态文本分析不可能被运行时遮蔽）。
5. **S1 声称"行为保持"**：施工席刻意**没动** `facade.py::derive_facade_frame` 里宽松的字符串归一
   （换成严格版会把「未知值静默当 False」变成抛异常 = 真实行为改变）。请判这个保守取舍是否正确、
   以及**这处不一致会不会本身就是一个潜伏缺陷**。
6. **遮蔽**：对本批每把锁问「这个夹具里有没有第二条防线先于目标门拦下变异」。

⛔ 请勿采信本请求书任何结论 —— 上面每一条都请独立复现。**派工方历史错误率 13/13。**
