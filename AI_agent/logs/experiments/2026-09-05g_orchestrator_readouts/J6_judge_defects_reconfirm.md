# J-6 · 判分路径四条未闭合缺陷 · **逐条重新确认**（2026-09-05 主控自查，⛔ 非转引）

> plan.md 闸⑤ J-6 写死：「⛔ 不许假设它们随旧格式一起作废 —— 判分单第一件事就是逐条重新确认
> 它们在新格式下还成不成立」。本条即那次确认。**基准 = 主树 HEAD `b4f0b348`**，全程只读。
> ⭐ **结论：四条不是一类东西 —— 三条账早就该销了，剩下那条的形状变了、比登记时更要紧。**

## 一、总表

| # | 登记时的说法 | 当前树上的实测 | 判定 |
|---|---|---|---|
| **F-90** 楼层 id 两套命名（第 6 处：matcher 在桥之前就比字符串）| `score_service.py:389` 早于桥 `:431`；`segment_score.py:1751` 直接 `target.floor_id != observed.floor_id` | 桥在 **`:564-570`** 建好，经 **`_normalize_correction_plan_floor_ids`（`:355`）** 归一后，才在 **`:585`** 调 `match_plan_segments` ⇒ **顺序已倒过来**；`segment_score` 那行**故意保留**精确比较（docstring 明写「matcher 只在一个命名空间内比，⛔ 不许按拼写/大小写/顺序猜」）| ✅ **已修** |
| **F-100** source-view 桥没接，真实 gt 一到静默全 miss | `score_service.py:469` 直接把 observation 交 `assign_openings`，不传过滤器 | `:650` 调用处**已传** `source_view_to_gt_view_ids=source_view_to_gt_view_ids(score_bindings)`，与正确先例 `reading_typed_score.py:525` 同形 | ✅ **已修**（牙见 §三）|
| **F-101** 合法 `src:<64hex>` locator 被当未注册输入拒掉 | `score_service.py:200` 一律 `split("/", 1)[0]` | 全文件 **`split("/", 1)` 已不存在**；`_derive_window_floor_plan_sources`（`:186`）改为消费**已认证的 claim-link catalog**，注释白纸黑字点名两种合法生产者形式 | ✅ **已修** |
| **F-89** 一张立面跨两层就整份丢 | `reading_typed_adapter.py:667` `if len(floor_ids) != 1:` ⇒ 该视图全部 elevation 组件 `not_applicable` + `denominator_disposition="filter"` | **原样还在**（现行号 **`:681`**），`elevation_floor_partition_unresolved` 五处引用俱在；`grep F-89` 在 `src/` 与 `tests/` **各 0 命中** | ⛔ **仍成立**，且形状变了，见 §四 |

## 二、三条的销账依据（⛔ 不是「看代码像修了」，是溯源）

`git log -S` 定位到修复提交，两笔都在 **F-90 返工** 那一轮：

| 缺陷 | 修复提交 | 提交标题 |
|---|---|---|
| F-90 第 6 处 | **`b735db46`** | `08.26c_F90Rework_Items1And1bAnd2_TheVerificationChannelIsFixedBeforeTheDefect` |
| F-100 · F-101 | **`8ea9aca1`** | `08.26d_F90Rework_Items3And4_TheFilterThatHidBehindAnEmptyTupleIsNowExercised` |

跨家族裁决在库：[`2026-08-26_f90_rework_glm_verdict.md`](../../reviews/verdict/2026-08-26_f90_rework_glm_verdict.md)
（GLM `glm-5.3`，**`APPROVE-WITH-FINDINGS` / 0 阻断 / 7 不阻断** —— ⚠️ **我核了裁决原文**：
plan.md 第 545 行把它记成「APPROVE 零阻断」，**少了 7 条不阻断**，其中一条正是 §三#3）。
⇒ **plan.md 的「未闭合缺陷登记」与 J-6 那一格是【过期账】**，不是新发现。
**J-6 的工作量因此从「四条」缩到「一条 + 一次复量」。**

## 三、⚠️ 销账要带的两句话（⛔ 不许写成「已闭合，不用管了」）

1. **F-100 的锁只在【一个】夹具方向上有牙**：`tests/test_c2_b5_parent_and_verts.py:1480` 那条把 gt 的
   `source_refs` 造成了**非空**（正是提交标题说的「藏在空元组后面的过滤器现在被行使了」），
   但同文件 **`:1386` / `:1398` / `:1468` 仍是 `source_refs=()`**。
   ⇒ 符合本项目已知病族 [[gate-teeth-direction-follows-fixture-inventory]]：
   **锁只在夹具有存货的方向上有牙**。**新格式真 gt 一到，必须把这条重量一次**，⛔ 不能拿 08-26 的绿当数。
2. **F-101 有真锁，形态是对的**：`test_f90_window_floor_id_and_gt_floor_id_are_independent_namespaces`
   按 `host_source_form ∈ {view_observation, locator}` **参数化**，`locator` 那一臂喂真 `src:<64hex>`
   （`:1525` 断言 `startswith("src:")` 且长度 68）并走完 `score_typed_attempt` ⇒ 走的是真实入口，不是恒等锁。

3. ⭐ **当年复核方点的那个洞已经补上了**（我今天核的，⛔ 非转引）：08-26 裁决 findings 里的「实验 2c」
   实测「**locator 不在 catalog**」那条分支**零锁覆盖**（把 reason 错标，七把锁全绿）。
   今天树上已有 **`test_correction_floor_plan_bridge_fails_closed_with_named_reason`**，
   按 **7 个 reason 码逐一参数化**（`window_host_claim_missing_source_ids` ·
   `window_host_claim_ambiguous_source` · `window_host_source_not_a_registered_plan_input` ·
   `floor_id_maps_to_multiple_plan_inputs` · `verified_plan_floor_catalog_not_total` ·
   `verified_plan_floor_not_registered_for_scoring` · `window_host_disagrees_with_verified_plan_floor_catalog`）
   ⇒ **reason 码本身进了断言**，不再是「红就算数」。

## 四、⭐⭐⭐ F-89：它没被新格式带走，而是变成了 J-3 的一个缺口

**登记时的说法**：判卷代码缺陷，sm25 四张立面每张覆盖 F1+F2 ⇒ 四张全被静默过滤，
`window_elevation_geometry` / `floor_lines_complete` 一律 `not_applicable`。

**今天的三条实测**：
1. **旧路径原样在**：`reading_typed_adapter.py:681` 的 `len(floor_ids) != 1` 分支未动，
   仍产 `cause_class="trusted_input"` + `denominator_disposition="filter"`（**静默进分母处置，不是响亮失败**）。
2. **新格式的 reading 判分器已经有了**：`src/agent/judge/as_drawn/reading_grade.py`（336 行）+
   `denominator.py`（763 行），就是 J-3 那把「线段对线段」的尺子，C1 位置 / C2 覆盖 / C3 切分 / C4 多画 / C5 门窗身份。
3. ⛔⛔ **但它是【平面专用】的**：`grep -ci "elevation|facade|立面"` 在
   `reading_grade.py` = **0**、在 `denominator.py` = **0**。
   ⇒ **新判分器根本没有立面这一维**。

**⇒ 判定改写**（这就是 J-6 要的那种「在新格式下还成不成立」的回答）：
> F-89 **不是**「旧代码里一个待修的 bug」，也**不会**随旧格式作废。
> 真实形状是：**立面侧的 reading 判分，在新格式下【尚未存在】** ——
> 旧的那条路会把多层立面静默过滤掉，新的那把尺子压根不量立面。
> ⇒ 处置**不是**去改 `reading_typed_adapter.py`，而是**把它写进 J-3 判分单的验收里**：
> **sm25 四张立面每张都跨 F1+F2，新 reading 判分器必须能判它们，⛔ 不许有「跨两层就整份 filter」这一档。**

⚠️ 附带一条要在判分单里点名的风险：F-89 的失败形态是 `denominator_disposition="filter"`
—— **它会把整份从分母里拿掉**，于是「没判」和「判了满分」在总分上**长得一样**。
新判分器若也用「过滤」处理不会判的形态，同一个坑会原样复发
（[[absence-conflates-causes-in-observables]] / [[invalidation-blast-radius-must-be-scoped]]）。

## 五、给排期盘面的净影响

- **闸⑤ J-6「四条重新确认」⇒ 缩为**：① 三条销账（改 plan.md 登记，⛔ 不需要派工）
  ② **F-100 在新格式真 gt 上复量一次**（并进判分单）③ **F-89 转为 J-3 单的一条验收项**。
- ⇒ **挡路新单从 6 个 → 5 个**（J-6 不再是独立一单）。⛔ 其余五项不变。
