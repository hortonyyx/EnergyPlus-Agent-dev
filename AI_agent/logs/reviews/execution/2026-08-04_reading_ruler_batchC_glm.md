# 批 C 执行日志（渲染 / 命名 / 像素预算）— 施工 GLM · 2026-08-04

- 上游：[派工单](../request/2026-08-04_reading_ruler_batchC_and_r2c_rest_dispatch.md)（第二部分批 C；§3 纪律逐条有效）
- 前置状态：HEAD `d145023`（r2c 收尾，全仓 2097 + 10 xfail）。批 C 半截像素预算在 `git stash` = `batchC-wip-render-pixel-budget`。
- 本批交付：**O-3 ✅ commit `d246c90`** · **O-4 ✅ commit `079ce17`** · **O-1 ✅ commit（本轮）**。
- 全仓（批 C 全部交付）：**2106 passed + 10 xfailed 零红**（2101 + O-1 五条锁）。

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

## 3. O-1 · aggregate 自动渲染 ✅

### 设计
病灶（M-1，派工单 + 上轮已定位）：`run_stage.py:_render_stage` 的 `0_reading` 分支 flat glob
`(run_dir/"0_reading").glob("*_view.json")`，而硬隔离 merge 把 aggregate 写到
`attempts/NNN/output.json`（`{'views':{<expected_output_id>:<ReadingView>}}`，`isolation.py:382`），
stage 根目录**无** `*_view.json` ⇒ **glob 匹配零文件、07-08 起每轮识图零渲染、用户看不到任何产物图**。
同函数顶层 `except Exception` best-effort 吞错 ⇒ 渲染失败被吞、伪装 complete。

**架构裁定（取舍）**：派工单写「由 attempt finalization / merge 共用同一个 renderer」。merge 在
`src/agent/execution/isolation.py`（生产、被 ~15 个 merge 测试覆盖），renderer 在
`scripts/tool_scripts/`（tool-script 层）⇒ **不让 isolation.py import tool-script renderer**（层级倒置
+ merge 回归风险）。改为：渲染终结化留在 tool-script 层（`run_stage.py`），由 `_render_stage` 在
merge 写完 attempt 后调用 ——「共用同一个 renderer」= 全用 `render_vector_to_png.render`、唯一换的是
**views 从哪读**（aggregate `output.json` 而非 stage-root glob）。**merge 零改动**（最小风险）。

### 改动清单（`scripts/tool_scripts/run_stage.py`，仅此一个生产文件）
- **`_finalize_reading_renders(attempt_dir)`**（新）：读 `<attempt>/output.json` aggregate views，
  逐图 `rv.render` → 写 `<attempt>/renders/<eid>.png` + `<attempt>/render_manifest.json`
  （`source_output_hash` = `hash_text(output.json)` **同 merge 的 output_hash 哈希器 ⇒ 可对账** ·
  `render_helper_version` = `READING_RENDER_HELPER_VERSION` 常量 · 每图 `{expected_output_id, status,
  render_hash|null, error|null}`）。逐图异常**记进 manifest 不吞**：`status=failed` + error、
  `any_failed=True` ⇒ 总体 `status` 翻 `"unavailable"`（否则 `"complete"`，空 views 也算 unavailable）。
- **`_reading_render_status(attempt_dir)`**（新）：读 manifest 返 `"complete"|"unavailable"|"missing"`
  （无 manifest = missing，兼顾 pre-O-1 run）。
- **`_render_reading_attempts(run_dir)`**（新）：遍历 `0_reading/attempts/` 有 `output.json` 的 attempt
  （accepted 在前），各调 `_finalize_reading_renders`，返回渲染 png 路径（给 judge packet）。
- **`_render_stage` 0_reading 分支改写**：删 flat glob + 删随之死亡的 `_save` helper，改为
  `produced.extend(_render_reading_attempts(run_dir))`。1_correction 分支逐字不动。顶层 `except` 保留
  （仅兜底 stage 级灾难，如 output.json 不可读；逐图失败已在 manifest 记录、不会冒泡到这里）。
- **`cmd_approve_review` 加 guard**：`0_reading` 且 accepted attempt 的 render status == `"unavailable"`
  ⇒ `raise SystemExit("review blocked: ...")`（机器可读理由、点名 manifest status）。
  `"missing"`（pre-O-1 / 未渲染）**故意不阻断**，保 pre-O-1 run 可批（披露见下）。

### 锁（`tests/test_reading_renders.py`，新建 5 条）
- **L-40a** `test_L40_isolation_aggregate_renders_per_attempt_with_hashes`：只产
  `attempts/001/output.json`、stage 根无 `*_view.json` ⇒ `_render_reading_attempts` 生成
  `renders/<eid>.png` + manifest，每图 `render_hash` == `hash_file(png)`、`source_output_hash` ==
  `hash_text(output.json)`、`render_helper_version` 齐全、status=complete。
- **L-40b** `test_L40_render_stage_reading_branch_reads_attempts_not_stage_root`：真入口
  `_render_stage("0_reading", ...)` 返回两图 png 路径、落在 `attempts/001/renders/`。
- **L-41a** `test_L41_render_failure_records_unavailable_not_complete`：monkeypatch
  `rv.render` 抛 ⇒ manifest status=`unavailable`（非 complete）、每图 `failed`+error、无 png；
  `_reading_render_status` 返 unavailable。
- **L-41b** `test_L41_failed_render_blocks_review_approval`：accepted 0_reading + manifest
  unavailable ⇒ `cmd_approve_review` `SystemExit("review blocked...")`。
- **L-41c** `test_L41_complete_render_allows_review_approval`：complete manifest ⇒ 批准返回 0
  （钉 guard 精确、不过度阻断）。

### neuter 自查（备份→改→跑→cp 还原，`git diff` 干净）
- **L-40 neuter**：`_render_reading_attempts` 还原成 stage-root flat glob（M-1 病灶）⇒ **红 2 条**
  （L-40a + L-40b，**同源 flat glob 依赖、非连带**），3 条 L-41 不受影响（它们直调
  `_finalize_reading_renders` / `cmd_approve_review`，不经 glob）。
- **L-41 吞错 neuter**：逐图 `except` 改成「标记 rendered / 不翻 any_failed」（吞进 complete）⇒
  **红 1 条**（L-41a，status 变 complete），其余 4 绿。
- **L-41 guard neuter**：`cmd_approve_review` guard `and False` 关掉 ⇒ **红 1 条**（L-41b，DID NOT RAISE、
  直接批准），其余 4 绿。
- 三次 neuter 各**恰好红其目标、零连带**；还原后 `git diff` 仅本批改动、neuter 痕迹清零。

### 受影响子集结果
`test_reading_renders` + `test_run_stage_flow` + `test_render_vector_to_png` + `test_judge_batch_b`
+ `test_audit_remediation_accepted_inputs` + `test_reading_typed_scoring_slice{0,1}`
+ `test_c2_b4b_phase_d` + `test_c2_b4b_contract`：**122 passed 零红**（warnings = 既有 run_config 缺失，
  与本批无关）。

### 缺口/披露
- **「是否阻断纯数值 gate①」裁定 = 不阻断**：渲染是交付面（人看图），gate① 是识图正确性数值门；
  渲染失败不污染 gate① 数值。渲染失败只阻断**人工 review 批准**（`cmd_approve_review`），不阻断
  merge / gate① / flow 推进。failure artifact = `render_manifest.json`（status=unavailable + 每图 error）。
- **`"missing"` 不阻断 approve-review**：pre-O-1 run / 从未渲染的 run 无 manifest，按 missing 放行
  （保向后兼容）；只有「渲染试过且失败」(unavailable) 才阻断。若后续要求「review-required run 必有
  manifest 否则也阻断」，是另一次拍板（会断 pre-O-1 run）。
- **judge packet `renders` 列表**：`_render_stage` 现返回 accepted attempt 在前的所有 attempt 渲染 png
  路径（旧实现返回 stage-root 渲染）；judge 仍能看到全部渲染图。
- **accepted stage-root 别名**：派工单提「只能是便利副本、非唯一证据」—— 本批证据落在
  `attempts/NNN/renders/` + `render_manifest.json`；未发现/未新增 stage-root 别名机制（既有
  `_draw_reading` 行为不动）。
- **每 attempt 都渲染**（非仅 accepted）：与 `_render_all_typed_attempt_grades` 同形（遍历所有 attempt），
  便于 judge 看每个 attempt；idempotent（重跑覆写）。

---

## 4. 全仓测试结果（批 C 全部交付后，⛔ 无 `-m`）

`pytest -q -n 6` ⇒ **2106 passed + 10 xfailed，零红**（507s；2101 + O-1 五条锁 = 2106，精确符合、
零回归）。`test_zone_agent_creates_two_zones`（派工单点名的 env 红、真跑 OpenAI 网络超时）本次网络通
而过 ⇒ 计入 passed、非确定、与本批无关。sm24/sm21 manifest byte guard 仍随全仓绿。

---

## 5. 合规自检

| 项 | 结论 |
|---|---|
| 锁走真实入口 | ✅ L-50 经真 `merge_isolated_output`；L-51/L-52 经真 `rv.render`；L-40 经真 `_render_reading_attempts`/`_render_stage`；L-41 经真 `_finalize_reading_renders`（monkeypatch 真 `rv.render` 抛）+ 真 `cmd_approve_review` |
| 断言落具体产物字段 | ✅ L-50 落 merge extra raise；L-51 落 canvas < budget；L-52 落 size 相等；L-40 落 `renders/<eid>.png` + manifest `source_output_hash`/`render_hash` 具体字段；L-41 落 manifest `status`==unavailable + `cmd_approve_review` SystemExit |
| 每条 neuter 自查如实登记 | ✅ L-50（摘 extra ⇒ 红 2 同源非连带）；L-51/L-52（摘 OCR extent ⇒ 红、复现 3.3 亿像素根因）；L-40（还原 flat glob ⇒ 红 2 同源非连带）；L-41 吞错（⇒ 红 1）+ guard（⇒ 红 1）两次各零连带 |
| neuter 在 /tmp / 还原干净 | ✅ 备份 → 改 → 跑 → cp 还原，`git diff` 干净（neuter 痕迹清零） |
| ⛔ renderer 不「clamp 之后放行」 | ✅ O-4 超限 `raise CanvasBudgetExceeded`、不 clamp |
| ⛔ 渲染失败不伪装 complete | ✅ O-1 逐图失败记 manifest `status=unavailable` + 阻断 `cmd_approve_review`（L-41a/b/c） |
| 不 push | ✅ 批 C commit 未 push |
| 不碰 `gt/**` / sm24 testdata | ✅ 批 C 改 skill md + renderer + run_stage + 3 测试文件，零触碰 |
| 不读 GT | ✅（L-40 fixture 自造合成 aggregate，非 GT） |
| 不动 `AI_agent/` 下除自己执行日志外的管理文档 | ✅ 工作树含 orchestrator 未提交 `CLAUDE.md`/`decision_log.md`/`lightgate.md`/`plan.md`，**非本批、未 commit** |
| 做完一件存一件、每条 commit | ✅ O-3 `d246c90` / O-4 `079ce17` / O-1（本轮） |
| stash 只看不 pop | ✅ O-4 用 `git stash apply`（保留 stash），未 pop |

---

## 6. 给 orchestrator 的交付摘要

- **O-3 已落库**（`d246c90`）：reader 产物名按 `expected_output_id`（不从 PNG 名推导）+ L-50
  （merge 拒收 `_view` 错套，neuter 同源非连带）。
- **O-4 已落库**（`079ce17`）：renderer 画布不纳 annotation + 硬像素预算（拒绝不 clamp）+ L-51/L-52
  （neuter 精确复现 3.3 亿像素根因）。
- **O-1 已落库**（本轮）：`_render_stage` 0_reading 改读 attempt aggregate（删 flat glob）+
  `_finalize_reading_renders` 写 `attempts/NNN/renders/<eid>.png` + `render_manifest.json`
  （source hash + helper version + 每图 status/hash）+ 渲染失败记 unavailable + 阻断 `cmd_approve_review`
  （L-40a/b + L-41a/b/c，三次 neuter 各零连带）。**07-08 起每轮零渲染的交付面缺陷已修**。
- 全仓 2106 passed + 10 xfailed 零红（2101 + O-1 五条）。
- **裁定一/裁定二已照办**：r2c-2 不重做、§9 如实记 `6e06ecf` 记账；「零连带」判据写进 r2c-2 / r2c-4 / L-50 / L-40 / L-41 的 neuter 自查。

批 C 三条（O-3/O-4/O-1）全部交付、零回归。O-1 在 dedicated 窗口一次做完整（L-40 渲染 + L-41 失败阻断
共享 manifest status 字段、不可分），跨 merge/flow/review 三处核心路径、全仓验证通过。
