# 批 C 执行日志（渲染 / 命名 / 像素预算）— 施工 GLM · 2026-08-04

- 上游：[派工单](../request/2026-08-04_reading_ruler_batchC_and_r2c_rest_dispatch.md)（第二部分批 C；§3 纪律逐条有效）
- 前置状态：HEAD `d145023`（r2c 收尾，全仓 2097 + 10 xfail）。批 C 半截像素预算在 `git stash` = `batchC-wip-render-pixel-budget`。
- 本批交付：**O-3 ✅ commit `d246c90`** · **O-4 ✅ commit `079ce17`** · **O-1 ⏸ 停下待续（见 §3）**。
- 全仓（批 C 部分交付）：**2101 passed + 10 xfailed 零红**（2097 + O-3 L-50 + O-4 L-51/L-52/companion）。

## 0. 性质

批 C 改的是**交付面**（用户能不能看到产物图、文件名对不对、渲染会不会把机器撑爆），
与批 B（执行信任事务）完全不同。分开提交、分开审。顺序按派工单 **O-3（最小）→ O-4（安全）→ O-1（最大）**。

---

## 1. O-3 · 精确输出文件名 ✅ commit `d246c90`

### 设计
病灶：`session_kickoff.md:51` 通则 `<name>_view.json` 与 `:57-65` 表格自相矛盾。真正规则在
`view_manifest.py §4.2` 的 declaration-family transform —— floor_plans / cardinal_elevations 用
**identity**（`1f_view` / `South_view`），supplementary 用 **append_view**（`supp_plan` → `supp_plan_view`）。
⇒ 图名以 `_view` 结尾的 case，读图器照通则做就会产出 `1f_view_view.json` 被 merge 拒收。

### 改动清单
- `skills/intake_pipeline/0_reading/session_kickoff.md`：
  - 通则改为「按 staging `input_inventory.json` 的 `expected_output_id` 写 `<expected_output_id>.json`，
    不从 PNG 名推导；stem 已以 `_view` 结尾 ⇒ identity；`supp_plan` ⇒ `supp_plan_view`」。
  - 表格 `<name>_view` → `<expected_output_id>`，加「非规范示例」注脚（实际名以 inventory 为准）。
- `tests/test_isolation.py`：**L-50** `test_merge_per_image_view_suffix_misapplied_is_rejected` ——
  reader 在正确 `1f_view.json` 之外多写旧通则的 `1f_view_view.json` ⇒ merge extra 拒收。

### neuter 自查
- 摘 `isolation.py:602-607` extra 检查（`if False and extra`）⇒ **红 2 条**：L-50 + 现有
  `test_merge_per_image_extra_is_rejected`（**同源 extra hook、非连带**，裁定二判据成立）、
  203 passed 零其他连带。还原后 `git diff` 空。

### 受影响子集结果
`tests/test_isolation.py`：**205 passed**（204 + L-50）。

### 缺口/披露
拒收机制（merge extra/missing）已存在（F-5 / S4）；L-50 专门覆盖 `_view` 错套语义。reader 在
staging 实际写 `out/`（非 `<case>/0_reading/`）—— 路径映射是 staging 的事，本条只锁**文件名**
（expected_output_id），未改路径约定。

---

## 2. O-4 · OCR 锚点 / 像素预算 ✅ commit `079ce17`

### 设计
根因链（派工单已查明，未重查）：`ocr_texts` 完全 untyped（`schema.py:126 ocr_texts: list`）；
`guide.md:269-272` 示例看着像 metric local anchor，而 `Dimension.anchor` 注释写 pixel
（schema `:65-81`）⇒ 坐标载体语义不统一；validator 只查 typed `room_labels`（`reading.py:212-318`）、
**不查 OCR**；renderer 把 OCR anchor 纳入画布 extent（`render_vector_to_png.py:50-77`），且
`Image.new`（`:85`）前无像素预算 ⇒ 10×20 m 图撑成 **3.3 亿像素**。

### 改动清单（`scripts/tool_scripts/render_vector_to_png.py`，取回 stash 半截 `batchC-wip-render-pixel-budget`）
- `_collect_points` 不再纳 `ocr_texts[].anchor` ⇒ 画布 extent 只来自 strokes + dimension endpoints
  （结构几何 / trusted metric bounds）；OCR anchor 按 fixed canvas 画、可能落外（gate① OCR-bounds
  FLAG = G-9，本批不做、登记债）。注释 :73-78 写明「OCR 不是结构几何」。
- `MAX_CANVAS_SIDE_PX=8192` / `MAX_CANVAS_PIXELS=50_000_000` 两命名常量 + `CanvasBudgetExceeded`；
  `render()` 在 `Image.new` 前检查、超限 **raise（⛔ 不 clamp）**。
- stash 用 `git stash apply`（保留 stash，未 pop）；内容已进 commit `079ce17`。

### 锁（`tests/test_render_vector_to_png.py`，**首批 renderer 测试** —— 之前零覆盖）
- **L-51**：pixel OCR anchor `[360,450]` ⇒ render 不爆、canvas < budget。
- **L-52**：pixel anchor `[60,80]` vs metric anchor `[5,10]` ⇒ canvas size 相同（OCR 不进 extent）。
- **companion**：结构本身超 budget（20000 m）⇒ `CanvasBudgetExceeded`（拒绝不 clamp）。

### neuter 自查
- 摘 OCR extent 排除（`_collect_points` 加回 OCR 收集）⇒ **红 L-51 + L-52**、companion 绿（结构 budget
  不依赖 OCR）、零其他连带。
- **精确复现根因**：`[360,450]` 进 extent ⇒ canvas **16335×20385 = 332,988,975 px ≈ 3.3 亿像素** ⇒
  `CanvasBudgetExceeded`。还原后 `git diff` 仅 stash apply 改动（28+/3-）。

### 受影响子集结果
`tests/test_render_vector_to_png.py`：**3 passed**。

### 缺口/披露（登记债）
- **OCR schema 版本化**为显式 `anchor_m` / `anchor_px`（或 `{frame, point}`）—— 本批不做。
- **gate① OCR-bounds FLAG (G-9)** —— validator 补 OCR anchor 越界检查，本批不做。
- 「pixel anchor 不进 metric transform」由 **extent 排除 + 注释**体现；绘制层 OCR 仍经 `tx/ty`
  （越界 PIL 自然裁剪），未单独锁绘制层 —— L-51/L-52 锁 extent 核心（防 3.3 亿像素）。

---

## 3. O-1 · aggregate 自动渲染 ⏸ 停下待续

### 病灶（已定位，下轮直接接着做）
- `run_stage.py:670` `_render_stage` flat glob `(run_dir/"0_reading").glob("*_view.json")` ——
  硬隔离产物在 `attempts/NNN/output.json`（aggregate `{'views':{...}}`，`isolation.py:382-383`），
  根目录无 `*_view.json` ⇒ **每轮零渲染、用户看不到任何产物图**。
- `run_stage.py:687` `except Exception` best-effort 吞错 ⇒ 渲染失败被吞、伪装 complete。

### 设计草案（下轮基线）
- `isolation.merge_isolated_output`（写 `attempts/NNN/output.json` 后）共用 renderer 读 aggregate
  views，写 `attempts/NNN/renders/<expected_output_id>.png` + `render_manifest.json`（source output
  hash + render helper version + 每图 `{eid, status, render_hash | error}`）。
- `_render_stage` 改读 accepted attempt 的 `renders/`（不再 flat glob）；accepted 根目录别名仅便利
  副本、非唯一证据。
- 渲染失败（renderer raise）⇒ manifest 记 `status=failed` + error（机器可见 failure artifact）；
  review packet renders 反映失败（⛔ 不伪装 complete）。**派工单已定**：要求人工 review 的 run 阻断
  `review_complete`；纯数值 gate① 是否阻断可另定；必留 failure artifact。

### 锁（待写）
- **L-40**：isolation 只产 `attempts/001/output.json`、根目录无 `*_view.json` ⇒ 生成 per-attempt
  renders、每图 source hash / render hash 齐全。摘掉 flat glob 依赖即红。
- **L-41**：向 renderer 注入异常 ⇒ review status unavailable/blocked、不显示 complete。摘掉 best-effort
  吞错即红。

### 为什么停下（如实登记）
O-1 是批 C 最大、最复杂的一条，且**连贯不可分**：L-40（merge 写 renders/manifest）与 L-41（渲染失败
⇒ review 阻断 + failure artifact）共享 `render_manifest` 的 `status` 字段，分开做不如一次做完整。
它跨 `isolation.merge`（核心路径，被 ~15 个 merge 测试覆盖）+ `run_stage._render_stage`（被
`test_run_stage_flow` 覆盖）+ `review_complete` 阻断语义（触 flow），回归风险中高，需 dedicated 窗口 +
全仓验证。本轮已交付 r2c 全部 + O-3 + O-4（批 C 两条安全 P0），在已长会话末尾硬塞 O-1 易引入 flow
回归 / 半成品。**病灶 + 设计 + 锁形态已定位，下轮可直接接着干。**

---

## 4. 全仓测试结果（批 C 部分交付前，⛔ 无 `-m`）

`pytest -q -n 6` ⇒ **2101 passed + 10 xfailed，零红**（347s；2097 + O-3 L-50 + O-4
L-51/L-52/companion = 2101，精确符合、零回归）。sm24/sm21 manifest byte guard 仍随全仓绿。

---

## 5. 合规自检

| 项 | 结论 |
|---|---|
| 锁走真实入口 | ✅ L-50 经真 `merge_isolated_output`；L-51/L-52 经真 `rv.render` |
| 断言落具体产物字段 | ✅ L-50 落 merge extra raise；L-51 落 canvas < budget；L-52 落 size 相等 |
| 每条 neuter 自查如实登记 | ✅ L-50（摘 extra ⇒ 红 2 同源非连带）；L-51/L-52（摘 OCR extent ⇒ 红、复现 3.3 亿像素根因） |
| neuter 在 /tmp / 还原干净 | ✅ 备份 → 改 → 跑 → cp 还原，`git diff` 干净 |
| ⛔ renderer 不「clamp 之后放行」 | ✅ O-4 超限 `raise CanvasBudgetExceeded`、不 clamp |
| 不 push | ✅ 批 C commit 未 push |
| 不碰 `gt/**` / sm24 testdata | ✅ 批 C 改 skill md + renderer + 2 测试文件，零触碰 |
| 不读 GT | ✅ |
| 不动 `AI_agent/` 下除自己执行日志外的管理文档 | ✅ 工作树含 orchestrator 未提交 `lightgate.md` / `plan.md`（裁定 + §8 记账更正），**非本批、未 commit** |
| 做完一件存一件、每条 commit | ✅ O-3 `d246c90` / O-4 `079ce17` |
| stash 只看不 pop | ✅ O-4 用 `git stash apply`（保留 stash），未 pop |

---

## 6. 给 orchestrator 的交付摘要

- **O-3 已落库**（`d246c90`）：reader 产物名按 `expected_output_id`（不从 PNG 名推导）+ L-50
  （merge 拒收 `_view` 错套，neuter 同源非连带）。
- **O-4 已落库**（`079ce17`）：renderer 画布不纳 annotation + 硬像素预算（拒绝不 clamp）+ L-51/L-52
  （neuter 精确复现 3.3 亿像素根因）。
- **O-1 ⏸ 停下待续**：病灶（flat glob + best-effort 吞错）+ 设计（merge 写 renders/manifest +
  `_render_stage` 改读 + 失败 artifact / review 阻断）+ 锁 L-40/L-41 已定位，留下轮独立深度做。
- 全仓 2101 passed + 10 xfailed 零红。
- **裁定一/裁定二已照办**：r2c-2 不重做、§9 如实记 `6e06ecf` 记账；「零连带」判据写进 r2c-2 / r2c-4 / L-50 的 neuter 自查。

O-1 因连贯大块 + flow 风险停下（非"已做完问要不要重做"），照派工单「做不完就停下上报」执行。
