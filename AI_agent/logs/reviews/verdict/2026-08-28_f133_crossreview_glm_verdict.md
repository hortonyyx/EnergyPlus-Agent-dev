# 跨家族复核裁决 · F-133 同层轴合并记账（R1/R2/R3）

- **日期**：2026-08-28 · **复核方**：GLM 跨家族席位 · **请求书**：[`request/2026-08-28_f133_crossreview_glm.md`](../request/2026-08-28_f133_crossreview_glm.md)
- **被审**：`49f09dc..2b874f7`（`10115eb` 施工 + `a069476`/`2b874f7` 执行记录；`6b5d9bd` 纯文档不在范围）
- **复核方法**：只看原始派工单 + diff + 我自己跑出来的读数。执行记录 §八/§九（orchestrator 给自己写的复核段）**逐读数独立复现，未采信任何自述**。

## 裁决：**APPROVE-WITH-FINDINGS**（阻断 0 条 · 不阻断 7 条）

---

## 一、独立跑出来的读数原文

### 1.1 全量（`python -m pytest -n 6`，⛔ 无 `-m`，在 `6dcda80` 主树）

```
3208 passed, 13 xfailed, 212 warnings in 951.43s (0:15:51)
EXIT=0
```

| 项 | 读数 |
|---|---|
| `.pth` 哨兵 | 跑前 `2026-08-28T14:00:10Z` / 跑后 `14:16:14Z`，**三行逐字相同**（`5198f6f9…` / `a47a5925…` / `c767f0a0…`）|
| HEAD 跑前/跑后 | `6dcda80` / `6dcda80` ⇒ 无第三方改树 |
| 工作树 | 全程 0 条脏路径（我的探针/neuter 全在 `/tmp` worktree 与副本）|
| 算术 | 3195（基线，施工方读数 + CLAUDE.md 08-29 收工记录旁证）+ 13（新夹具）= 3208 ✅ |
| §七 那条 baseline-marker 用例 | 本次全量**绿**（包含在 3208 内）——又添一次「非本单 diff」佐证 |

### 1.2 四档同层台阶行为（我独立跑，与请求书 §三 表逐字一致）

```
120 mm → y轴 [0.0, 6.0, 6.12, 10.0]   记账 0 条            （没被合并）
 60 mm → y轴 [0.0, 6.03, 10.0]        记账 1 条  step=sliver_merge
 30 mm → y轴 [0.0, 6.02, 10.0]        记账 1 条  step=identity_cluster
 10 mm → y轴 [0.0, 6.0,  10.0]        记账 1 条  step=identity_cluster
```

### 1.3 几何逐位不变（承重前提）—— **66 个 case 前后零差**

对比方法：`git worktree` 检出 `6b5d9bd`（= 施工前代码，`PYTHONPATH` 强制解析并在输出里自证 `CODE_FROM`）与主树跑同一探针，dump **整个 model 减三张审计表** + 非 F-133 审计行 + unsupported + conflicts，逐字段比较：

| 输入族 | 数量 | 几何差 | 非F133审计差 |
|---|---|---|---|
| y 台阶扫描（10/30/40/49/50/60/70/90/95/99/100/101/110/120/150/200 mm）| 16 | 0 | 0 |
| x 台阶（10/30/60/100 mm）| 4 | 0 | 0 |
| 三值台阶（6.0/6.04/6.08）| 1 | 0 | 0 |
| 纯跨层抖动（50 mm / 100 mm）| 2 | 0 | 0 |
| 同层+跨层混合 | 1 | 0 | 0 |
| gap_close 探针（同层 9.8/10.0，相距 200 mm）| 1 | 0 | 0 |
| fuzz（固定 seed，1–3 层网格 + 5–60 mm 抖动 + 随机丢弃 cell）| 40 | 0 | 0 |
| sm25 真产物（`run_2026-08-25_c2_rescore_R0`，orthogonal_polygon）| 1 | 0 | 0 |
| **合计** | **66** | **0** | **0** |

⚠️ 复核过程中的自我纠错，记录在案：我第一次跑施工前侧时 `python /tmp/probe.py` 的 `sys.path[0]` 是脚本目录而非 cwd，`import src` 静默落回主树 `.pth` —— 那一次的「前后零差」是主树自己比自己，**无效**。改为 `PYTHONPATH` 强制 + 输出自证 `CODE_FROM` 后重跑才得到上表。（[[agent-worktree-isolation-may-branch-from-stale-base]] 警告的串台在「跑脚本」形态下同样发生，且只多一行 `__file__` 自证就能抓住。）

### 1.4 真产物上的记账（我独立复现，与执行记录声称逐字一致）

sm25 R0：非 F-133 corrections **23** 条 + F-133 **2** 条 = **总 25 条**，conflicts **1** 条，unsupported 1 条。两条 F-133：

```
identity_cluster y floor_2 [5.88, 5.89]    -> 5.88   （separation 10mm）
identity_cluster y floor_2 [14.12, 14.125] -> 14.12  （separation 5mm）
```

⇒ 与执行记录 §四.① 的「总 25 条 / conflicts 1 / 2 条新记账」完全一致；「噪声量可控（真产物 2 条）」属实。

### 1.5 R2 反空转（两树独立复现）

override 配置 `min_edge_length_m: 0.200`、同一条 0.15 m 边的 cell、同一个校验器 `cell_geometry.cell_polygon` 两条调用路：

```
施工前(6b5d9bd):  tol=0.2   modelling._MIN_EDGE 字面量=0.1
                   correction path -> REJECT (ValueError)
                   geometry   path -> ACCEPT
                   ⛔ DIVERGED — same validator, two answers
施工后(2b874f7):  tol=0.2   modelling._min_edge()=0.2
                   correction path -> REJECT (ValueError)
                   geometry   path -> REJECT (ValueError)
                   AGREE
shipped 配置:      两侧均 0.1（值未变）；`_MIN_EDGE` 字面量属性已不存在（None）
```

### 1.6 envelope_transform.py 的 12 行

`ast.dump` 比较 `6b5d9bd` vs `2b874f7` 的该文件：**语法树完全相同** ⇒ 12 行纯注释、零行为。派工单「只加注释、⛔ 本单不改」逐字满足，注释内容确实点名了语义挪用（复用数值不复用语义 + 改 `min_edge_length_m` 会顺带改窗准入的警告）。

---

## 二、请求书 §四 六处重点逐条

| # | 重点 | 我的独立结论 |
|---|---|---|
| 1 | 几何逐位不变 | **成立**（§1.3，66 case 含 fuzz 与真产物零差）|
| 2 | 记账会不会漏 | **两个 kill site 已全覆盖；存在第三条路径但非静默**（下详）|
| 3 | 记账会不会误报 | **跨层 0 误报**：50 mm / 100 mm 两档纯跨层抖动均 0 条 F-133 记账、conflicts 0、轴正确合一（4.90/4.95→4.93；4.90/5.00→4.95）。混合输入归类正确：1F 同层 60 mm 台阶记 `sliver_merge` 一条，F2 跨层搭档并入不记 |
| 4 | R2 值不变 | **成立**（§1.5：shipped 下 0.1/0.1；override 下两路同答案；施工前 divergence 独立复现）|
| 5 | R3 夹具分辨力 | **四种 neuter 全部有牙**（§三）|
| 6 | envelope_transform 无行为 | **成立**（AST 相同，§1.6）|

**第三条路径的查找过程与结论（重点 #2）**：我审了 `_reconcile_cross_floor` 的全部合并机制（identity clustering / Phase B0 footprint anchor / Phase B 跨层 union / Phase C sliver guard / `_snap_to_grid` 吸附）与 `apply_deterministic_core` 的全部后续坐标通道（mapping 应用 / `_close_to_boundary` / z-stack / window snap / legacy 与 v3 envelope reconcile）。结论：

- footprint anchor 与 Phase B 结构上**不会**并同层两条轴（同层候选竞争会被 block + 记 ambiguity；一个 anchor 每层只服务一个候选）。
- envelope 轴移动有 pre-move guard（拒绝穿越最近内部轴 / 压扁到 min_edge 以下），不会并轴。
- `_snap_to_grid` 造成的同层合轴必然先经过 kill site 1 或 2（同层两轴距 < 100mm 才可能 snap 到同值）。
- **唯一漏网的通道 = `_close_to_boundary`（gap_close，`gap_close_threshold_m` = 0.300）**：同层两轴相距 100–300 mm 且一条贴 footprint 边界时，该轴被吸到边界与另一条重合——两个 kill site 都不触发、F-133 记 0 条。实测（同层 9.8 / 10.0，相距 200 mm）：产物 y 轴 `[0.0, 10.0]`、F-133 = 0 条，**但有 2 条 `deterministic_core.gap_close` 记账**（9.8→10.0，位移 200 mm > output_precision_m 10 mm），且中间的 cell 压扁进 unsupported（`cell collapsed below min_edge_length after snap`）。⇒ 该通道自带响亮记账与失败信号，**不是「静默合并」**；真正静默的窗口（gap_close 位移 ≤ 10 mm 且无 F-133 行）要求两轴距 ≤ 10 mm，那种距离已被 kill site 1 记账。**判：不构成阻断，记 N-1。**

---

## 三、我做的 neuter 与结果（/tmp 副本，主树未动）

副本基线：13 passed（与施工方同读数）。四种：

| neuter | 做了什么 | 结果 |
|---|---|---|
| **A** | 记账 flush 循环改 `for event in []`（记账全去）| **4 红**：三档正向记账参数化 + 10mm-精度那条 |
| **B** | `_min_edge()` 改回 `return 0.10` 字面量 | **1 红**：`test_modelling_edge_floor_follows_the_active_correction_config`（override 锁咬住回退）|
| **C** | 只删 kill site 1（identity_cluster）的记账调用 | **3 红**：10/30 mm 档记账断言；**60 mm 档仍绿** ⇒ 「只覆盖 sliver_merge 会漏 <50 mm 整段」实证 |
| **D**（我加，施工方未做）| 聚类容差 ×4（动合并行为本身）| **3 红**：`test_step_120mm_survives`（坐标快照）+ 120mm 零记账极 + 60mm 参数化 ⇒ **四条坐标快照锁不是空转**，它们的牙在行为面 |

关于请求书 §四.5 的空转判据（「某条用例两种 neuter 都不红 ⇒ 空转」）：四条坐标快照与 `value_is_unchanged` 那条对 A/B 确实都不红——但 D 证明坐标锁有牙（动行为即红），value 锁的牙在 yaml-retune 方向。**每条锁的牙都在不同变异方向上**，与 A/B 两种 neuter 的组合无一条用例全无牙。判：**无空转用例**（[[gate-teeth-direction-follows-fixture-inventory]] 的又一例，记 N-5）。

---

## 四、请求书 §五 两问 + 施工方异议 + §七 的独立判断

### #42 `_MIN_EDGE` 有没有第四处 —— **没有**

全仓 sweep（全部 `0.1x` 字面量常量）：

```
correction/geometry_validator.py:48 _SPAN_TOL   = 0.10  # 窗宽-房间容差 —— 不同的量
judge/as_drawn/reading_grade.py:50  EXTRA_MIN_M = 0.10  # 多画计量忽略 sliver —— 不同的量
validator/checks/kernel.py:35       _AREA_TOL   = 0.10  # 面积容差(m²) —— 量纲都不同
validator/checks/kernel.py:36       _PERIM_TOL  = 0.10  # 周长容差 —— 不同的量
validator/interzone.py:64           _MIN_EDGE   = 0.10  # ⭐ 语义同一：degenerate sliver 守卫
```

⇒ `_MIN_EDGE` 语义的独立声明只有 `interzone.py:64` 这第三处，**无第四处**；其余四处是不同量恰合同值。施工方「记一行未动、留下轮」合规（`src/validator/` 确在本单授权范围外）。补一条处置依据：interzone 的 `_MIN_EDGE` 是**门**（报 issue、不动坐标），它与 yaml 值分歧时会以「红」显现而非静默错——留下轮风险可控。

### #43 记账要不要过 `output_precision_m` 滤网 —— **施工方处置（显式不过滤）正确**

1. 两个量语义不同：`output_precision_m` 管「一次坐标挪了多少才算值得记的规整」（normalization）；本记账管「两条身份不同的轴变成一条」（identity）。10 mm 台阶每侧只挪 5/0 mm，按位移滤网必被滤掉，而它正是验收③点名要有记录、也是 200/180 墙真台阶的量级。
2. 代价实测可控：真产物全量只 2 条（§1.4），清单没有被噪声淹没。
3. 决策已写死在夹具（`test_10mm_step_is_recorded_even_though_each_side_moves_under_output_precision`，断言 per_value_delta ≤ output_precision_m 仍记账 + separation=0.010）。

### 施工方异议：`_same_floor_sliver_conflict`「量错了尺子」 vs 派工方「方向反了」 —— **施工方读法更准，orchestrator 采纳正确**

- 「方向反了」若成立，隐含修法是翻转比较符——那会把 <100 mm 的同层合并全部改成 conflict，60 mm 真台阶保住的**同时每一次 60 mm 模型抖动也保住**，恰是派工单 §三 判死的抛硬币（施工方的告诫成立）。
- 按函数注释立意（「valid same-floor **Phase A** separations are never silently collapsed」），Phase A = identity clustering、阈值 `axis_jitter_tol_m`(50 mm)；实现却拿 `min_edge_length_m`(100 mm) 量 ⇒ 50–100 mm 的 valid separation 不受保护。**病根是阈值来源（尺子），不是比较方向（符号）。**
- 「近乎恒假」我独立佐证：我的 65 个合成 case（含 40 个多层抖动 fuzz）conflicts **全部为 0**；且结构上进入合并分支的前提是两组 canonical 相距 < 100 mm，而守卫要求 support 值相距 ≥ 100 mm 才 conflict ⇒ 只有「已并过一次、support 带多值的组」才可能触发。
- 本单未改它 ✓ 合规。

### §七 那条红 —— **确实与本单 diff 无关，「可能是真回归」的怀疑可排除**

机理我读了代码：

- 该测试最后的断言是**幂等**：连续两次 `record_baseline` 生成的 REPORT.md 逐字相同。
- `_collect_git_provenance()`（`scripts/tool_scripts/record_baseline.py:88-116`）在**每次**生成时跑真实共享主树的 `git rev-parse HEAD` + `git status --porcelain --untracked-files=all`，行数进报告 provenance 段。
- ⇒ 差分唯一来源 = 两次生成之间 HEAD 或脏路径计数变了。本单 diff 在施工方跑全量期间是**静态**工作树内容（三次 record 之间不变），结构上不可能造成差分；能造成差分的只有窗口内第三方写树——orchestrator 已自认（窗口内提交 `6b5d9bd`），施工方的失败差分 `dirty:4→5` 与之吻合；复跑绿；**我的全量里它也绿**。
- 附带判断：该测试把「本进程外的整棵共享树在 ~90 秒内不许变」写进了前提——既知结构性脆弱（[[green-suite-is-a-property-of-tree-and-launcher]]），与本单无关，值得单独排期（fixture 冻结 provenance），不属本单 findings。

---

## 五、不阻断 findings（7 条）

**N-1 · gap_close 是「同层两轴并一」的第三条路径，F-133 记账不覆盖它（但非静默）。** 见 §二。建议 ②-2 落地时把 gap_close 通道的记账语义（「位移」而非「身份合并」）一并过一遍：一次 200 mm 的真实分隔被 gap_close 抹掉时，产物上只有 `gap_close` 位移行 + 可能的 unsupported，没有 `same_floor_axis_merge` 行——两类记录在「台阶消失」这个语义上不对齐。

**N-2 · 90–100 mm 段的叙述不精确。** `structural_snap_grid_m` 吸附会把 95/99/101 mm 台阶的间隔推到恰好 ≥100 mm（6.095→6.1）从而**保住**；实测 95/99/100/101 mm 四档全部保住、零记账（90 mm 及以下才死于 Phase C）。kill site 2 注释「50-100 mm steps survive clustering but die here」在 90<x<100 段不严格成立。行为是既存的（施工前后逐位相同），不影响本单验收；下次碰到这段注释顺手改准。

**N-3 · 请求书 §二 的 numstat 笔误：** `2b874f7` 实测 `19 0`（请求书写 `20 0`）。外围数值错，不承重。

**N-4 · orchestrator §九 的「基线 3195」不是它自己跑的。** §九只记录了改动后全量；基线 3195 采信自施工方 §四.⑤，由 CLAUDE.md 08-29 收工记录旁证。不构成问题，但「独立复核」的叙述里这一项实为「采信+旁证」。

**N-5 · 锁的牙分布在不同变异方向。** `value_is_unchanged` 对 neuter B 不红（字面量回退后值恰好同）；四条坐标快照对 A/B 不红、对 D 红。判不空转，但「两种 neuter」的组合面内各有盲方向——挑变异时要按锁声称覆盖的量各自打到（参考 [[gate-teeth-direction-follows-fixture-inventory]] 08-29 的「存货是检查形态的函数」）。

**N-6 · `corrections` 落点的下游面核过两处，安全：** `_resolved_debt_ids`（validator/checks/correction.py:574-579）只认 `kind == "debt_resolution"` 的行——F-133 行无 kind，结构上不可能误销 evidence debt；`_audit_completeness` 只要求「几何被改时有 sourced 审计行」，新行只增不减。全量绿为总佐证。

**N-7 · 施工方 §五 的「单跑该用例 4 次全绿」我未复跑。** 该用例单次 ~90 s 且绿/红取决于共享树是否有第三方写入，此刻复跑证明力弱；我以读代码定位机理（§四）+ 我的全量结果代替。如实说明。

---

## 六、对 orchestrator §八/§九（给自己写的复核段）的专门审

本单唯一外部检查点，按「派工方给自己打分」的怀疑强度审：

1. **读数全部复现一致**：四档行为、13 passed、真产物 25 条 corrections / 1 conflict、两 kill site 归属——我的独立读数与之逐字相同，未发现美化或选择性 reporting。
2. **自认实犯诚实且到位**：「那条红是 orchestrator 造成的——第三次同型」直接点名自己，并把硬口径收紧为「有席位跑全量时连文档提交都不做」。我的机理分析（§四）支持该归因。
3. **三条裁决**（#42 成立为题错 / 施工方读法更准 / #43 处置正确）我全部独立复核**同意**。
4. **没说到的**：N-1（gap_close 第三路径）、N-2（90–100 mm 段）、N-4（基线采信）、N-3（numstat 笔误）。
5. 活链证据表核验：`pipeline.py:46` / `correction/finalize.py:132` / `stage_runner.py:337` / `modelling.py:569` / `split_pairing.py:35/77/109` 全部属实；`_build_axis_map` 全仓确系零调用死代码。

---

## 七、结论

三件交付（R1 记账 · R2 合一 · R3 夹具）全部按派工单落地；⛔ 明令红线（不改任何合并/吸附数值、不改 `_same_floor_sliver_conflict`、不碰 `src/agent/judge/`、不删锁不放宽断言）经 diff + AST + 66 case 逐位对比 + 四种 neuter 确认未越。承重前提「几何逐位不变」成立（66 case 零差）。**零阻断。**

**APPROVE-WITH-FINDINGS。**
