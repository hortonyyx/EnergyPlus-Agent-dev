# 施工交件报告 · 楼层 id 映射层（F-90）

- **派工单**：[`../request/2026-08-25_f90_floor_id_mapping_dispatch.md`](../request/2026-08-25_f90_floor_id_mapping_dispatch.md)
- **席位**：Claude 家族执行档　**交件 commit**：**`3f6731f`**（主树，未 push）
- **复核**：⭐ **GPT 家族**（用户 08-25：「审走 GPT」）
- ⛔ 席位自述按 §5#8 **一律以 `git diff` 为准**。

## ⭐⭐⭐ 最重要的一条：同根因**共 5 处**，不是派工单点名的 1 处

席位按「候选清单可能不完备」的授权自行扩了范围，并显著披露：

| # | 位置 | 后果 |
|---|---|---|
| 1 | `score_service.py` 原 `plan_sources` 查表 | 派工单指名的**崩溃点** |
| 2 | `_resolve_facade_product_to_gt` 的 facade span 归属过滤 | 墙段全不归位 |
| 3 | `build_absence_opening_claims` 的 `floor_refs` 键 | extras 分类崩 |
| 4 | ⭐⭐ `opening_claim_score._assign_openings_for_source` 的**窗-gt 开口匹配本身** | **不崩，但让满分产物静默判成全部 miss** |
| 5 | `map_product_cells_to_gt_zones` 的 zone 归属 | host claim 恒判 miss |

> ⛔ **只修第 1 处会从「崩溃」变成「静默全错」（第 4 处），比原状更隐蔽危险。**

**统一解法**：新增 `_derive_window_floor_plan_sources` —— 从每扇窗 `host` claim
（词表里**唯一只能来自平面通道**的字段）的 `source_ids` 解出 `product floor_id → input_id`，
再经 `score_bindings` 转成 `→ gt floor_id`，**5 处全部走这一条桥**。

## 四个边界的处置（全部**响亮失败**，⛔ 无一处取默认值）

| 情形 | 处置 |
|---|---|
| 窗没有平面引用 | `window_host_claim_missing_source_ids` |
| host claim 引用歧义（多个不同 input_id）| `window_host_claim_ambiguous_source` |
| 引用了未注册的 plan input | `window_host_source_not_a_registered_plan_input` |
| 同一 floor_id 的窗互相矛盾 | `floor_id_maps_to_multiple_plan_inputs` |
| **零窗楼层** | ⛔ 不是问题：该层无窗可判，`_resolve_facade_product_to_gt` 对无证据楼层维持既有 fail-closed |
| **立面** | ⭐ **确认不需要处理** —— 立面走几何/指纹推导，**从不比较 `window.floor_id` 字符串**；F-89 是另一条独立缺陷，⛔ 未混入 |

## ⭐ 十个判据的实际读数（派工单最硬的那条验收）

用走完整 B5 六件套 + 真实 `score_typed_attempt` 的干净 fixture（product 楼层 `"f1"` vs gt `"F1"`，
**刻意复刻 sm25 的命名撞车**）：

```
kind: c2_scored
criterion_id                 eligible  verdict          pass  fail  denom
walls_complete               False     not_applicable    0.0   0.0   0.0
no_extra_walls               False     not_applicable    0.0   0.0   0.0
no_duplicate_wall_strokes    False     not_applicable    0.0   0.0   0.0
boundary_complete            True      fail              0.0  32.0  32.0
windows_placed               False     not_applicable    0.0   0.0   0.0
window_plan_geometry         False     not_applicable    0.0   0.0   0.0
window_elevation_geometry    False     not_applicable    0.0   0.0   0.0
floor_lines_complete         False     not_applicable    0.0   0.0   0.0
no_oversplit                 False     not_applicable    0.0   0.0   0.0
negative_evidence_complete   False     not_applicable    0.0   0.0   0.0
extras: ()   unmeasurable_observations: 0
```

⇒ 十判据**全部有真实读数**（非 crash、非默认值），且窗**正确匹配**（`extras=()`，没被误判成多余观测）。

## 锁的红/绿 + 响亮失败的锁

- **RED**（加锁后、修 `score_service.py` 前）：2 failed，报 `ScoreContractError: score_view_binding_invalid`，命中旧代码
- **GREEN**（修完）：`61 passed in 16.37s`
- **响亮失败锁**：`test_f90_window_without_plan_host_reference_fails_closed_not_silently` PASSED
  （断言 `context.reason == "window_host_claim_missing_source_ids"`）

## 全量与提交

```
3019 passed, 13 xfailed, 212 warnings in 929.78s (0:15:29)
```
对照基线 `3017 passed` ⇒ **+2 正是本单新增的两把锁**，零红零 error。
commit `3f6731f`，4 个文件（`opening_claim_score.py` · `score_service.py` · 两个测试）。

## ⚠️ 与派工单说法不符 —— 两条，**第二条触发了停报条件③**

1. 派工单只点名 1 处修法 ⇒ 实测 5 处（见上）。
2. ⭐⭐ **派工单 §四第 1 条「跑 sm25 那份现成产物、贴出判分结果」在 sm25 R0 上仍未达成** ——
   它撞上**另一个与楼层 id 无关的既有缺陷**：
   **product facade span 在 L 形内角处与 gt 分段边界有约 `0.12 m` 的包含缺口，16 段里 8 段不归位。**
   ⇒ 触发派工单自己给的停报条件 ③「**前提本身错了**」——
   **「修好 F-90 就能让 sm25 R0 判出分」这个前提不完全成立。**

   ⭐ **席位的处置值得记**：用干净 fixture 拿到完整十判据读数作为「确实判出分」的证据；
   用 sm25 R0 的 before/after **报错码变化**（`score_view_binding_invalid` → `score_product_segment_unresolved`）
   作为「F-90 本身已修好、卡在另一处」的独立证据；
   ⛔ **未尝试用容差之类的办法遮盖第二个缺陷**（「那会是**阈值调硬 ≠ 判据重算**的老病」）。

---

## ⭐ orchestrator 的机械核对

| 核了什么 | 结果 |
|---|---|
| `git show --stat 3f6731f` | ✅ 4 文件：`src/agent/judge/opening_claim_score.py`(+21) · `score_service.py`(+124) · `tests/test_c2_b5_parent_and_verts.py`(+129) · `tests/test_judge_identity_metric.py`(+10)。⛔ 未碰 pipeline 内核 / 交接契约 / `src/validator/` / `scripts/` / gt |
| 那个运行时副产物 | ⚠️ 施工中曾改到 `run_2026-08-25_c2_rescore_R0/_run/orchestration_state.json`（仅 `"updated"` 字段），orchestrator 已提醒；**最终提交里没有它** ✅ |
| ⛔ **未独立验证** | 十判据那份 fixture 的构造是否公允 · 5 处同根因的判断 · `0.12 m` 缺口的归因 ⇒ **全部交 GPT 复核** |
