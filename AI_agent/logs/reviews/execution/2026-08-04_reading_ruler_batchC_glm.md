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

---

## 7. r1 返工（B-1/M-1/M-2/M-3/N-1/N-2/N-3）— 施工 GLM · 2026-08-04

- **上游**：[r1 返工派工单](../request/2026-08-04_reading_ruler_batchC_r1_rework_dispatch.md)（REWORK = 1 BLOCKER / 3 MAJOR / 3 MINOR）·
  [交叉审](../verdict/2026-08-04_reading_ruler_batchC_crossreview_claude.md) · [轻门 §6](../verdict/2026-08-04_reading_ruler_batchC_orchestrator_lightgate.md)。
- **首要纪律**：每条锁必须走「会踩到该缺陷的那条真实路径」；neuter 在 /tmp 克隆 + `PYTHONPATH=$PWD`（容器 editable `.pth` 指向主仓，不钉克隆等于没做）。
- **B-1/M-1/M-2（上轮中断已落库，本轮不复做）**：`fdb31c0`(B-1 flat-flow 渲染) · `484852a`(M-1 failure artifact) ·
  `f254c56`(M-2 kickoff 按 expected_output_id 命名)。orchestrator 轻门 §6.1 已独立 neuter 四处全部真绑、零连带；
  **B-1 的锁确实走盲重读那条真实路径**（非隔离 fixture）。

### 7.1 M-3 · gate① OCR anchor frame/bounds 检测（commit `fb33162`）— 唯一实质性一条

**⚠️ 重要披露**：M-3 在工作树里是**上一轮撞额度中断时遗留的完整 WIP**（`reading.py`+`schema.py`+3 锁全部写好但
未提交、未验证、未做 neuter）。派工单/轻门只数了已 commit 的三条，没算这份未提交 WIP。**本轮没有盲目信任它、
也没有丢弃**，而是从头严格验证（跑测试 + /tmp 两处 neuter + 全仓）通过后才 commit。

- **`src/validator/checks/reading.py`**：`_ocr_anchors_in_bounds` —— OCR/标注 anchor 落在可信结构画幅
  （`_image_bounds` = strokes + dimension 端点）外、超出 `_OCR_ANCHOR_MARGIN_M=2.0m` ⇒ FAIL `reading.ocr_anchors_in_bounds`，
  给机器可读 evidence（offenders: index/anchor/text/reason + bounds + margin_m）。**⛔ 不 clamp、不静默丢弃，只 surface**。
  空 `ocr_texts` 干净 pass。镜像既有 plan-frame 检查的写法。
- **`src/validator/checks/schema.py`**：`OCR_ANCHOR_BOUNDS_CHECK_ID` + `is_ocr_anchor_check_id` + disposition 分支
  （exploratory/dev ⇒ FLAG；golden/regression ⇒ BLOCK）。与 plan-frame 同 profile split。
- **锁**（`tests/test_checks_reading_correction.py`，3 函数 = 4 测试）：① acceptance[golden/regression] 下像素 anchor
  `[360,450]` FAIL 且 BLOCK；② exploratory 下同 anchor 只 FLAG（`rep.passed` True）；③ in-bounds anchor + margin 内 anchor pass。

**neuter 自查**（/tmp 克隆 HEAD `f254c56` + 拷入 WIP + `PYTHONPATH=$PWD`，`-k ocr`）：

| # | 摘掉哪一处 | 红了哪几条 | 连带 | 判定 |
|---|---|---|---|---|
| **neuter-a** | `_ocr_anchors_in_bounds` 恒 pass（不发射 FAIL） | acceptance[golden]+[regression]+lenient（3 条均断言 FAIL 状态） | 零（in-bounds pass 测试不受影响） | ✅ 检测真绑 |
| **neuter-b** | 去掉 `schema.disposition` 的 OCR BLOCK 分支 | acceptance[golden]+[regression]（2 条均断言「在 blocking 集」） | 零（lenient FLAG + in-bounds 不受影响） | ✅ 阻断策略真绑 |

两处还原后基线复跑 4 passed；工作树零 NEUTER 残留；克隆清理。**M-3 对全部 141 个含 `ocr_texts` 的历史 fixture 零连带**
（真实标签本就落在墙内 + 2.0m 宽 margin）。

### 7.2 N-1 · missing 分支真锁 + 修假 docstring（commit `d96d7fd`）

F-6：`test_L41_complete_render_allows_review_approval` 的 docstring 声称 pin 住 `missing` 分支（pre-O-1 run 可批），
但实测只写 `complete` manifest、从不走 `missing` ⇒ **missing 分支零锁**（守卫加宽到也阻断 missing，五条锁仍全绿）=
本项目「声称在守其实没守」第 6 次。

**取「补真锁」而非「删声称」**（向后兼容行为是刻意的、值得锁）：
- 新增 `test_L41_missing_render_does_not_block_review_approval` —— 不写 manifest（真 missing 路径）⇒
  `_reading_render_status=="missing"` ⇒ `cmd_approve_review` 返回 0（missing 不阻断）。
- 修 `test_L41_complete_render_allows_review_approval` 的假 docstring → 改为指向新锁（不再虚假声称自己 pin missing）。

**neuter 自查**（/tmp 克隆 HEAD `d96d7fd` 前置 + 拷入 N-1 测试）：守卫 `== "unavailable"` → `in ("unavailable","missing")`
⇒ **红 1 条**（missing 测试），9 绿零连带（empty 用 `"empty"` 状态不在集合内故不受影响；complete/unavailable/M-1 测试不受影响）。

### 7.3 N-2 · 已被 M-2 已落库锁覆盖 —— ⛔ 不补冗余锁（上报，无 commit）

派工单 N-2 前提「O-3 命名规范目前零锁」**陈旧**（写于 11:55，早于 M-2 落库）。核查：M-2 commit `f254c56` 已含
`test_build_kickoff_names_outputs_by_expected_output_id_not_view_suffix`（test_isolation.py:189，docstring 明写
"M-2 / N-2 (r1, F-3)"），直接锁住「生成的 kickoff_prompt.md 按 `<expected_output_id>` 命名、引用 input_inventory.json、
不含 `<name>_view`」——正是 N-2 要的「直接锁按 expected_output_id 写名」。

**本轮独立 neuter 复核**（不单靠 orchestrator 轻门 §6.1 N-4）：/tmp 克隆 HEAD `d96d7fd`，把 `_write_kickoff` 文案
精确回退到 F-3 病灶原状（`<name>_view.json`）⇒ **红 1 条**（`assert "expected_output_id" in kickoff` 失败），零连带。
⇒ **M-2 锁真绑，N-2 已覆盖。**

**裁定：不补冗余锁。** 命名规范链已端到端锁住（kickoff 指令层 = M-2 锁；merge 执行层 = L-50 + 既有 extra 测试）。
再加一条只会重蹈 F-5/L-50「零增量约束力」覆辙。F-5（L-50 与既有 extra 共用 hook）是良性冗余、记此不再动作。
（session_kickoff.md 静态规范文本未单独锁，但操作态产物 = 生成的 kickoff 已锁，且 kickoff 独立硬编码嵌入命名规则、
不读 session_kickoff.md，故静态文档漂移不破行为 —— 非阻断观察。）

### 7.4 N-3 · 画布预算自适应缩放（commit `aa58e28`）

`MAX_CANVAS_SIDE_PX=8192` + 固定 `SCALE_PX_PER_M=45` ⇒ 单边 >182m 的建筑永远渲不出（200×20m 板楼 → 9135px > 8192 被拒，
只占总像素预算 1/5）⇒ **撞不变量 #6**（复杂度可扩展性）。

**`scripts/tool_scripts/render_vector_to_png.py`**：
- 新增 `_fit_scale(extent_w, extent_h)` = `min(SCALE_PX_PER_M, MAX_CANVAS_SIDE_PX/longest, sqrt(MAX_CANVAS_PIXELS/area))`。
  小结构（当前 10-20m case）scale=45 **逐字节不变**；大结构按预算降档 px/m。
- `render()` 改用自适应 `scale`（tx/ty 同步）；**只在「结构单边 >8192m（哪怕 1px/m 都装不下 = >8km 假建筑）」时 raise**，
  文案明确「这是结构真的太大、不是 anchor 坏了（O-4 已把 anchor 排除出画幅；像素 anchor 由 gate① M-3 surface）」。
- **⛔ 不是 clamp**：公制几何保留、只调像素分辨率（地图渲染器通用做法）；**⛔ 不 clamp 坏数据**：坏 anchor 由 O-4+M-3 处理。
  「结构合法但太大」与「anchor 坏了」两种拒绝原因现已分离（renderer 只拒尺寸、gate 只报 anchor）。

**锁**（`tests/test_render_vector_to_png.py` L-53）：200×20m 板楼 render 不 raise + canvas 同时满足两边/总预算 +
长边 < 200×45=9000（证明降档而非固定 45）+ 长宽比 >5（证明均匀缩放非 per-side clamp）。

**neuter 自查**（/tmp 克隆 + 拷入 N-3 两文件）：`scale = _fit_scale(...)` → 固定 `SCALE_PX_PER_M` ⇒ **红 1 条**（L-53：
200m 边 → 9135px > 8192，精确复现派工单病灶数字 9135），3 绿零连带（L-51/L-52 当前小 case scale 仍 45 不变；
20000m 荒谬结构仍经预检 raise）。

### 7.5 全仓测试结果（四条全部落库后，⛔ 无 `-m`，`-n 6`）

```
2117 passed, 10 xfailed, 177 warnings in 626.73s (0:10:26)
```

= 工作树基线 2115（含 M-3 WIP 的 4 条）+ N-1(1) + N-3(1) = **2117**，零红零回归。
`test_zone_agent_creates_two_zones`（真跑 OpenAI、派工单点名的环境红）本次网络通计入 passed、非确定、与本批无关。
sm21/sm24 manifest byte guard 随全仓绿（N-3 对小 case scale 逐字节不变 ⇒ 渲染产物零变化）。

### 7.6 合规自检

| 项 | 结论 |
|---|---|
| 每条锁走「会踩到缺陷的真实路径」 | ✅ M-3 走真 `check_reading_view`+`schema.disposition`（合成 plan，非 GT）；N-1 走真 `cmd_approve_review` missing 路径；N-3 走真 `rv.render`（200m 结构）；N-2 复核走真 `_write_kickoff` 生成 |
| 断言落具体产物字段 | ✅ M-3 落 `reading.ocr_anchors_in_bounds` FAIL+offenders anchor/reason+blocking 集；N-1 落 `_reading_render_status=="missing"` + `cmd_approve_review` rc=0；N-3 落 canvas size<=budget + 长边<固定45值 |
| 每条 neuter「摘掉即红、零连带」+ 如实登记 | ✅ M-3 两处（3 红/2 红）；N-1（1 红）；N-3（1 红）；N-2 复核（1 红）—— 各零连带 |
| neuter 在 /tmp + `PYTHONPATH=$PWD` + 还原干净 | ✅ 四个克隆均 `__file__` 验证解析到克隆、还原后基线复跑通过、工作树零 NEUTER 残留、克隆清理 |
| ⛔ renderer 不 clamp 坏数据 | ✅ N-3 自适应缩放保留公制几何（非 clamp）；坏 anchor 由 O-4+M-3 surface 不被 renderer 丢弃 |
| 不 push | ✅ r1 四个 commit（fb33162/d96d7fd/aa58e28 + 上轮 fdb31c0/484852a/f254c56）均未 push |
| 不碰 `gt/**` / sm24 testdata / 不读 GT | ✅ r1 改 reading.py/schema.py/run_stage.py(无)/render_vector_to_png.py/isolation.py(无)/4 测试文件，零触碰 |
| 不动 `AI_agent/` 下除自己执行日志外的管理文档 | ✅ 仅续写本执行日志 §7；工作树里 CLAUDE.md/decision_log/plan/lightgate 未提交改动是 orchestrator 的、未 commit |
| 做完一件存一件、每条 commit | ✅ M-3 `fb33162` / N-1 `d96d7fd` / N-3 `aa58e28`（N-2 无代码改动、上报覆盖） |
| 提交前通读 `git status`、只 add 自己文件 | ✅ 每个 commit 仅 `git add` 本条目文件（绝不 `git add -A` 扫走 orchestrator 的 AI_agent 文档）—— 对照记忆 [[wrapup-commit-sweeps-other-seats-wip]] |

### 7.7 给 orchestrator 的交付摘要

- **M-3 已落库**（`fb33162`，**源自中断遗留 WIP、已严格验证非盲信**）：gate① 补 OCR anchor bounds 检测（越界 FLAG、
  golden/regression 下 BLOCK、机器可读原因、⛔ 不 clamp/丢弃）——「移走症状没补检测」已补上。两处 neuter 各零连带。
- **N-1 已落库**（`d96d7fd`）：补 missing 分支真锁 + 修假 docstring（F-6 第 6 次「声称在守其实没守」消除）。neuter 零连带。
- **N-2 ⛔ 不补、上报已覆盖**：M-2 已落库锁 `test_build_kickoff_names_outputs_by_expected_output_id_not_view_suffix`
  直接锁命名规范，本轮独立 neuter 复核真绑。派工单前提「命名规范零锁」陈旧。补冗余锁会重蹈 F-5 覆辙。**请 orchestrator 裁定：N-2 视为已完成（由 M-2 覆盖）确认。**
- **N-3 已落库**（`aa58e28`）：画布自适应缩放（小 case 逐字节不变、大建筑降档可渲、只拒 >8km 荒谬结构、分离两种拒绝原因、
  ⛔ 不 clamp 坏数据）。neuter 精确复现派工单病灶数字 9135、零连带。
- 全仓 **2117 passed + 10 xfailed 零红**（基线 2115 + N-1/N-3 各 1）。
- **r1 七条全部落地**（B-1/M-1/M-2 上轮 + M-3/N-1/N-3 本轮 + N-2 由 M-2 覆盖）。**唯一需 orchestrator 裁定项 = N-2 是否视为已完成。**

## 8. r2（X-1/X-2 必修 + X-3/X-5 MINOR + NIT）— 施工 **Claude 侧执行档**（GLM 额度耗尽后转接）· 2026-08-04

- **上游**：[r2 派工单](../request/2026-08-04_batchC_r2_dispatch.md)（HEAD `d0e33ef`→`57d47ea` 之后又发生
  `8336bd5`/`794b47a`/`79dd53c`/`58f9179` 等 batch D / R4-a 合并，本轮起点 = `58f9179`）·
  [r1 交叉审](../verdict/2026-08-04_reading_ruler_batchC_r1_crossreview_claude.md)（APPROVE-WITH-CHANGES：
  0 BLOCKER / 2 MAJOR / 3 MINOR / 2 NIT）。
- **交接说明**：GLM 上一席位已完成 NIT（单位双关拆分）但未提交，orchestrator `git stash` 保存为
  `stash@{0}`（`batchC-r2-wip-glm-nit-unit-pun-split`）；本轮先 `git stash show -p` 通读全文（唯一改动文件 =
  `render_vector_to_png.py`，14 行：拆 `MAX_CANVAS_SIDE_PX`(像素) / `MAX_STRUCTURAL_SIDE_M`(米) 两个具名常量 +
  同步 docstring/错误文案）确认完整可用后 `git stash apply`（非 `pop`，先留一份回退路径）。**GLM 的实现正确、但确如
  派工单所说零锁** —— 补两条后单独提交，见 §8.0。X-1/X-2/X-3/X-5 全部由本席位从零设计+施工+验证。

### 8.0 NIT · 单位双关拆分补锁（commit `32db683`，含接手 GLM WIP）

**接手内容（GLM）**：`render_vector_to_png.py` 的 `MAX_CANVAS_SIDE_PX`（像素上限，供 `_fit_scale` 用）此前同时被
`render()` 的「结构真的太大」拒绝门当**米制**上限使用——数值上都是 8192、无害，但单位双关：以后调像素预算的人会在
不知情的情况下同时松/紧那道米制拒绝门。GLM 拆出 `MAX_STRUCTURAL_SIDE_M = 8192` 给拒绝门单独用，`_fit_scale` 继续
用 `MAX_CANVAS_SIDE_PX`。逐行核对无逻辑改动，只是把同一个数字用两个独立常量表达。

**补锁（本席位）**：`tests/test_render_vector_to_png.py` 两条 ——
① 只调宽 `MAX_CANVAS_SIDE_PX`（monkeypatch 到 20000），9000m 结构仍必须被 `MAX_STRUCTURAL_SIDE_M`（未动）拒绝；
② 只调窄 `MAX_CANVAS_SIDE_PX`（monkeypatch 到 100），200m 合法建筑仍必须经自适应降档渲出（不撞米制门）。

**neuter 自查**：把 `render()` 的拒绝条件精确改回比较 `MAX_CANVAS_SIDE_PX`（即撤销 GLM 这次拆分）⇒ 两条锁均**红**
（①9000m 不再被拒绝——因为 20000>9000；②200m 结构因米制门被拒绝——因为 100<200 直接 raise）；`git diff` 精确单点、
还原后两锁复绿。**判定：真绑，零连带。**

### 8.1 X-1 + X-2（MAJOR，必修）· gate① 补 dimension 端点 bounds 检测 + 可信画幅换成 case_data 真实像素尺寸（commit `7de68cb`）

**两条设计上强耦合，合并一次提交（原因见下），但分别验证、分别 neuter。**

#### 设计

- **X-1**：N-3（自适应画布缩放）把「像素化 dimension 端点」从「渲染器会 raise」变成「静默降档渲出」，而 gate① 从来
  没有对 `dimensions[].from/.to` 做过 bounds 检测（M-3 只查 `ocr_texts`）——`_collect_points`
  （`render_vector_to_png.py:65-80`）明确把 dimension 端点算进画布延展，`_image_bounds`
  （`reading.py:369-402`，改造前）也把 dimension 端点算进兜底画幅，两处都没有"越界"这个概念。
  → 新增 `reading._dimension_endpoints_in_bounds`（与 `_ocr_anchors_in_bounds` 同规格：越界 FLAG，
  golden/regression 下 BLOCK，机器可读 evidence，⛔ 不 clamp 不丢弃）+ `schema.py` 新
  `DIMENSION_ENDPOINT_BOUNDS_CHECK_ID` + disposition 分支（与 OCR anchor 同 profile split）。
  `_image_bounds` 新增 `exclude_dimensions=True` 选项：dimension 端点检测用的兜底画幅**必须排除 dimension 端点
  自己**（否则一条坏 dimension 会把自己算进画幅、永远"在界内"——同 O-4 排除 OCR anchor 的道理）。
- **X-2**：交叉审证明 `_image_bounds` 的可信画幅可被产品自己撑大三种方式（多写一个像素化 dim 端点 / 一条乱伸的
  stroke / 一个未声明的 `image_bounds` extra 字段）全部命中，`ocr_anchors_in_bounds` 应声从 fail/blocking 变成
  pass/not-blocking。派工单骨架给死：可信画幅只能来自 case_data 源图真实像素尺寸 + 已冻结的图像指纹（view_manifest
  里 R1-6 已核对真实字节的那份），⛔ 不得从 strokes/dimensions/任何 extra 字段推导。
  → `_image_bounds` 新增 `trusted_bounds` 参数：**给了就唯一使用**（连 `_explicit_image_bounds`/strokes 兜底都
  完全不碰）；没给（无 case_dir/manifest 的直调单测、降级/legacy 路径——manifest 缺失已由
  `reading.view_manifest_coverage` 硬阻断）才退回改造前的产品可推导兜底。
  新增 `view_manifest.resolve_view_pixel_bounds(manifest, case_dir)`：对每个 `RequiredViewEntry` 直接
  `PIL.Image.open(case_dir / entry.source_image).size`（真实文件，不读产品任何字段），按 `expected_output_id`
  返回 `(0, W_px, 0, H_px)`。`check_reading_stage` 新增 `case_dir` 参数，解析后按 stem 转发进
  `check_reading_view(..., trusted_image_bounds=...)`；两个真实生产入口
  （`run_stage.py:_draw_reading` 的 `case_dir = run_dir.parent`、`isolation.py:merge_isolated_output` 的
  `case_dir = _repo_root()/binding["case_dir"]`）都已有 `case_dir` 在手，各加一个关键字参数即可接上。

**为什么合并提交**：X-1 的新检测复用 X-2 的 `trusted_bounds` 机制（同一个 `_image_bounds` 函数），拆开提两次会需要
先写一版不带 `trusted_bounds` 的 X-1、再在 X-2 里回头改 X-1 的函数签名——多一轮编辑、不减少风险，纯粹形式主义的
拆分。两条各自独立验证 + 独立 neuter（§8.1.1/§8.1.2），审阅时可分别核对。

**已知边界（如实披露，非本批范围）**：`evidence_preflight.py:231` 与 `validation_run.py:142` 也直调
`check_reading_view`（不经 `check_reading_stage`），本轮**未**给这两处接 `case_dir`/trusted bounds——它们是审计/
报告类的二级校验路径，不是接受 attempt 的主阻断门（主阻断门是 `_draw_reading`/`merge_isolated_output` 用的
`check_reading_stage`，已接）。派工单未点名这两处，本轮不做扩权级改动；如需覆盖，是另一条独立 MINOR。

#### X-2 判定算法的一处诚实说明（自主判断，非派工单钉死细节）

派工单给死了「来源」（case_data 真实像素尺寸），但没给死具体判定公式。交叉审 §4.4 的出口建议原话是
"把「anchor 是不是像素」判成「anchor 落在 `[0,图宽px]×[0,图高px]` 这个量级、却又远离公制结构画幅」"——这句话字面
需要两个独立量纲的量（像素量级 + 公制画幅）同时判断，但公制画幅本身若继续来自 strokes 又会被 X-2 自己禁止的三种
手段撑大（strokes 明确在派工单禁用清单里）。反复推演后本席位采用**更简单、更硬的版本**：`trusted_bounds` 给了就
**直接就是**判定边界（`(0, W_px, 0, H_px)`），不再叠加第二个量纲判断。

**已知局限（主动披露）**：这意味着如果真实 case_data 源图恰好很大（sm24 实测 790×1111 到 2890×1651 不等），一个
"看起来像素、实际不是"的坏值只要数值上小于源图像素宽高，本设计**不会**把它挡下——它只保证产品**不能再把这道门
撑大**（三种命名手段全部失效），不保证挡住"恰好落在源图像素范围内的任意坏值"这类更宽的问题。这与派工单/交叉审
给的硬约束（"不得从产品字段推导画幅"）完全吻合，但比交叉审出口建议里隐含的"双量纲判定"覆盖面窄。锁的构造（§8.1.2）
特意用一个真实 2×2px 的极小合成图像，确保锁测的是"三种撑大手段失效"这条硬约束本身，不依赖上述局限是否触发。
**如认为需要更强的判定（双量纲/量级比较），需要用户或 orchestrator 另行拍板算法细节，本席位不下放给自己猜。**

#### 8.1.1 X-1 锁与 neuter

`tests/test_checks_reading_correction.py` 新增 3 条（`test_dimension_pixel_endpoint_out_of_bounds_blocks_acceptance`
[golden/regression] / `..._only_flags_under_lenient` / `test_dimension_endpoint_in_bounds_and_margin_tolerated_passes`），
逐字复刻派工单 X-1 的复现载荷（10×8m 结构 + 像素化端点 `from=[360,450]`）。

| # | 摘掉哪一处 | 红了哪几条 | 连带 | 走真实入口 | 断言落哪 | 判定 |
|---|---|---|---|---|---|---|
| n-x1a | `schema.disposition` 里 `is_dimension_endpoint_bounds_check_id` 整段分支删除 | `blocks_acceptance[golden]`+`[regression]`（2 条，断言"在 `_ids(rep)` 阻断集合内"） | 零（`only_flags_under_lenient`+`margin_tolerated` 不受影响） | ✅ 真 `check_reading_view`→真 `disposition` | `_DIM_BOUNDS_CHECK in _ids(rep)` | ✅ 真绑 |
| n-x1b | `_dimension_endpoints_in_bounds` 提前 `return`（恒 pass，绕过全部逻辑） | `blocks_acceptance[golden]`+`[regression]`+`only_flags_under_lenient`（3 条，均断言 `result.status is FAIL`） | 零（`margin_tolerated` 断言 PASS，本就期望通过，不受影响） | ✅ 真 `_dimension_endpoints_in_bounds` | `result.status`（具体枚举值，非 None 判定） | ✅ 真绑 |

两处均独立 `cp` 备份 + 精确字符串替换 + `assert s2 != s` 保证命中 + 还原后复跑基线绿，`git diff` 核对零残留。

#### 8.1.2 X-2 锁与 neuter

新增 `test_trusted_bounds_from_case_data_survive_all_three_inflation_tricks`（走**真实生产入口**
`check_reading_stage`，用真实合成 case_dir：`case_data/1f_view.png` 是一张真实 2×2px PNG +
`testdata_prompt.json`，`build_view_manifest(case_dir)` 产出真 manifest；对同一个越界 anchor `[360,450]`
分别尝试交叉审点名的三种撑大手段——多写像素化 dim 端点 / 加一条乱伸 stroke / 声明 `image_bounds` extra 字段——
断言每种手段下 gate① 依然 FAIL+BLOCK）+ `test_trusted_bounds_unavailable_falls_back_without_crashing`
（无 `case_dir`/manifest 时不崩溃、退回改造前行为，钉住降级路径的契约）。

| # | 摘掉哪一处 | 红了哪几条 | 连带 | 走真实入口 | 断言落哪 | 判定 |
|---|---|---|---|---|---|---|
| n-x2a | `check_reading_stage` 里 `trusted_bounds_by_stem = resolve_view_pixel_bounds(...)` 改成恒 `{}`（不再转发 `case_dir`） | `test_trusted_bounds_from_case_data_survive_all_three_inflation_tricks`（三种手段的第一种 `extra_pixel_dimension_endpoint` 即触发 `AssertionError`，`for` 循环短路，其余两种未跑到——已在报告里如实注明，不是"三条全红"而是"跑到即红"） | 零（`unavailable_falls_back` 不受影响，因为它本就走无 trusted_bounds 分支） | ✅ 真 `check_reading_stage` | `result.status is FAIL` + `prefixed in _ids(rep)` | ✅ 真绑 |
| n-x2b | `_image_bounds` 里 `if trusted_bounds is not None: return trusted_bounds` 整段删除（改为注释掉，逻辑上恒走兜底） | 同上（`extra_pixel_dimension_endpoint` 命中） | 零（同上） | ✅ 真 `_image_bounds` | 同上 | ✅ 真绑 |

两处 neuter 输出**逐字重现交叉审报告的数字**：摘掉后 `bounds` 变成 `(0.0, 365.0, 0.0, 450.0)`（被额外的像素化
dim 端点撑大到刚好包住 `[360,450]`），`status` 从 FAIL 翻成 PASS——与交叉审 §4.4 实测表第二行完全一致，证明这条
锁测的就是被点名的那个真实缺口，不是另造的假标靶。

### 8.2 X-3（MINOR）· `_fit_scale` 的 `total_fit` 项补锁 + 修正失真 docstring（commit `066fff4`）

**病灶**：交叉审 neuter x1（摘掉 `total_fit` 项，只剩 `min(SCALE_PX_PER_M, side_fit)`）在全仓受影响子集下**全绿**——
因为现有所有大结构 fixture 都是"细长条"（如 200×20m），`side_fit` 单独就已经把画布压进总像素预算内，`total_fit`
从未真正成为瓶颈。另外 `test_L51_over_budget_structural_canvas_is_refused_not_clamped` 的 docstring 声称在守
"pixel budget"，但其 20000m 夹具触发的其实是 `MAX_STRUCTURAL_SIDE_M` 米制单边帽（在 `_fit_scale` 之前的独立
预检），压根没走到 `MAX_CANVAS_PIXELS` 那条路径——"声称在守其实没守"第 7 次。

**补锁**：构造一个**接近正方形**（500×500m，非细长条）的大结构。算术验证：加 1.5m margin 后延展 503×503m，
`side_fit` 单独会给出 `int(503×8192/503)=8190px`、面积 `8190²≈67,076,100px` **超过** `MAX_CANVAS_PIXELS=50,000,000`
——此时 `total_fit` 才是真正把画布压回预算内的那一项。锁断言渲染不 raise 且实际面积 `<= MAX_CANVAS_PIXELS`，并
额外算出"仅用 side_fit 会超预算"这个前提本身（避免锁本身也踩到"恒真断言"同一个坑）。同时把
`test_L51_over_budget_structural_canvas_is_refused_not_clamped` 的 docstring 改正，明确指向米制单边帽，并指向新
测试作为"谁在守 `MAX_CANVAS_PIXELS`"的答案。

**neuter 自查**：`_fit_scale` 返回值改成 `min(SCALE_PX_PER_M, side_fit)`（精确复现交叉审 x1 的摘除方式）⇒ 新锁
**红**（`img.size` 变成 8191×8191，面积超预算，逐字复现交叉审报告数字）；还原后复绿。

### 8.3 X-5（MINOR）· 两处零锁分支补锁（commit `f7cc1ff`，**零生产码改动**——两处代码本就正确，只是没锁）

**X-5a**（`run_stage.py` `cmd_approve_review` 的 `0_reading` 分支，读 manifest 顶层 `error` 字段 surface 进
`SystemExit` 文案）：现有唯一相关锁 `test_L41_failed_render_blocks_review_approval` 把 `error` 写在
`views[0]` 里（per-view 层），从未在**顶层**写过 `error`，所以 `mf.get("error")` 在那条既有测试里恒为 `None`，
"读顶层 error 并 surface"这三行代码可以整段删除、既有测试仍然全绿（因为它只断言了消息**前缀**
`match="review blocked: ..."`，从未断言具体原因文本）。新增
`test_L41_top_level_manifest_error_is_surfaced_in_review_block_reason`：manifest 顶层写一个带独特标记字符串的
`error`，断言 `SystemExit` 消息里**包含该标记**（而非只匹配前缀）。

**X-5b**（`_reading_render_status` 的 `except (json.JSONDecodeError, OSError): return "unavailable"` 分支）：
现有测试要么完全不写 `render_manifest.json`（走 `missing` 分支），要么写合法 JSON（走正常读取分支），从未写过一个
**存在但读不出**的文件——这条 except 分支因此零锁：如果有人把它误改成 `return "missing"`（`missing` 不阻断，
`unavailable` 阻断），全部既有测试仍然绿。新增 `test_L41_corrupt_render_manifest_reports_unavailable_and_blocks_review`：
写入 `"{not valid json"`（真实存在、真实读不出的文件），断言 `_reading_render_status` 返回 `"unavailable"`（不是
`"missing"`）且 `cmd_approve_review` 阻断。

**neuter 自查**：

| # | 摘掉哪一处 | 红了哪几条 | 连带 | 走真实入口 | 断言落哪 | 判定 |
|---|---|---|---|---|---|---|
| n-x5a | 删除 `cmd_approve_review` 里读顶层 `mf.get("error")` 的 try 块 | `test_L41_top_level_manifest_error_is_surfaced_in_review_block_reason`（`match="distinctive-marker-x5a"` 找不到，实际消息回退成通用文案） | 零（`test_L41_failed_render_blocks_review_approval` 仍绿——它只断言前缀） | ✅ 真 `cmd_approve_review` | `SystemExit` 消息文本 | ✅ 真绑 |
| n-x5b | `except (...): return "unavailable"` 改成 `return "missing"` | `test_L41_corrupt_render_manifest_reports_unavailable_and_blocks_review`（`assert ... == "unavailable"` 实得 `"missing"`） | 零（`test_L41_missing_render_does_not_block_review_approval` 仍绿——它测的是真正没有 manifest 文件的场景，不受这条 except 分支影响） | ✅ 真 `_reading_render_status` | 具体字符串枚举值 | ✅ 真绑 |

两处均还原后复跑绿，`git diff` 核对 `run_stage.py` 生产码逐字节不变（本条只加测试，未改产品代码——两处代码
本身就是对的，缺的只是锁）。

### 8.4 X-4（判断题，orchestrator 裁）· `missing` 该不该在「新 run」上阻断

**现象复核（不重复交叉审的实测，直接引用其结论）**：`spawn_isolated_reader.py` 的 `_cmd_merge` 只调
`merge_isolated_output`，merge 本身从不渲染；`_reading_render_status` 在 `render_manifest.json` 完全不存在时
返回 `"missing"`；`cmd_approve_review`（`run_stage.py:2329` 一带）只阻断 `"unavailable"`，`"missing"` 直接放行。
⇒ 一个刚合并完、还没跑过任何渲染动作的**新** run，`approve-review` 会在人类**从未看过任何一张图**的情况下 rc=0
"批准"。

**我的判断：`missing` 应该在"新 run"上阻断，理由三条**：

1. **"missing 不阻断"这条设计的初衷是向后兼容，不是"新 run 允许零图批准"**——它是在 O-1（渲染机制本身）落地时
   为了不让 pre-O-1（渲染机制诞生之前）的历史 run 被追溯性地判定为"不可批准"而加的豁免。这个初衷从未主张"新
   建的 run 也可以没有任何渲染就被批准"——只是当时的实现（"文件不存在就是 missing，missing 不阻断"）**恰好**
   把这两种语义不同的情况折叠进了同一个状态值，而没人注意到覆盖面比原意图更宽。
2. **approve-review 的存在理由是"人类看过材料再签字"**，不管"没有材料"的原因是"这是老 run 渲染机制还没发明"
   还是"这是新 run 但还没触发渲染"，结果对签字这个动作的意义都一样：**签字人没有看到任何东西**。用"是不是历史
   遗留"来决定要不要阻断，是在保护"记录的完整性"（不追溯破坏老 run），而不是在保护"签字的真实性"（新 run 应该
   有东西可看）——这两件事不冲突，可以同时满足。
3. **两种候选修法后果不同，我倾向"从源头消除歧义"而非"事后用元数据推断"**：
   - **候选 A（事后判别）**：给 `missing` 加一个"是不是历史遗留"的判据（比如检查 accepted attempt 的
     `StageRecordV2.artifact_contract` 是否等于 `"reading_isolated_v2"`——我核实过这个字段在
     `isolation.py:432` 确实是新隔离 merge 写入的合同标记，`migrated_v1` 才是老迁移 run 的合同标记，两者字面
     可区分），是"新 run 无 manifest ⇒ 阻断"、"老 run（迁移合同）无 manifest ⇒ 不阻断"。**缺点**：这是一个
     间接代理指标——`artifact_contract` 描述的是"数据形状"，不是"渲染是否已尝试"，用它反推"该不该已经渲染了"
     混淆了两件事；且这只是"现有字段恰好可以借用"，不是为这个目的设计的，未来任何一次 contract 值的扩展/演进
     都可能悄悄改变这条判据的含义而没人发觉（本项目已多次在"用现成字段推断本不相关的事"上栽过跟头，
     `decision_log` 里能找到至少两次同型教训）。
   - **候选 B（源头消除）**：`merge_isolated_output` 成功（接受）合并后，直接调用一次
     `_finalize_reading_renders`（renderer 已经现成、`_render_reading_attempts` 已经证明这条链路可靠），让
     "刚合并完的 attempt"永远不会处于"完全没有 manifest"这个状态——`missing` 因此**只可能**由"渲染机制诞生
     之前就已存在的 run"产生（构造上如此，不需要推断）。**优点**：彻底消除"新 run 会不会被误判为历史遗留"这
     个判别问题本身（无需判别，因为新 run 不会再落入这个状态）；同时**顺带解决了用户体验缺口本身**——被阻断的
     人类现在有真实渲染材料可看，而不只是被正确地拒绝、但仍然没有材料。**代价**：merge 从"纯元数据操作"变成
     "元数据+渲染"，多了一步可能失败的 I/O（不过 `_finalize_reading_renders` 本身已经把渲染失败的情况处理成
     `"unavailable"` 并阻断，不会静默吞掉——这正是 O-1 这条机制存在的意义）；如果 merge 出的 attempt 未被接受
     （gate① BLOCK、不被 accept），提前渲染的这次调用可能是"白做"的（成本很小，一次 PNG 渲染，不是不可接受）。

   **我倾向候选 B**，因为它不是"猜新老 run"，而是让"新 run 处于 missing 状态"这件事**不可能发生**，判别问题
   随之消失；候选 A 只是把"要不要阻断"这个问题换了个更隐蔽的地方继续猜。但**两个方案都涉及生产代码逻辑改动，
   不是"补锁"能覆盖的范围**，按纪律停在这里不动手，请 orchestrator 裁定选哪个（或两个都不要、维持现状）。

### 8.5 全仓测试结果（⛔ 无 `-m`，`pytest -q -n 4`）

<!-- 全仓跑测尾部原文见交付回复 -->

### 8.6 合规自检

| 项 | 结论 |
|---|---|
| 每条锁走「会踩到缺陷的真实路径」 | ✅ X-1 走真 `check_reading_view`→真 `disposition`；X-2 走真 `check_reading_stage`+真 `resolve_view_pixel_bounds`+真 2×2px PNG 文件；X-3 走真 `rv.render`（500×500m 结构）；X-5 走真 `cmd_approve_review`/`_reading_render_status` |
| 断言落具体产物字段 | ✅ 全部落 `status` 枚举值 / `evidence["offenders"][...]` 具体字段 / `SystemExit` 消息文本包含独特标记 / 渲染像素面积数值比较，零处落在「不是 None」或「总数变了」 |
| 每条 neuter「摘掉即红、零连带」+ 如实登记 | ✅ NIT(2 处)/X-1(2 处)/X-2(2 处)/X-3(1 处)/X-5(2 处)共 9 处独立 neuter，逐处见上文小节，零假锁 |
| neuter 精确单点替换 + 还原 | ✅ 每处 `cp` 备份 + Python 脚本 `assert old in s` / `assert s2 != s` 保证命中且非空替换，还原后复跑基线绿、`git diff` 核对干净 |
| 不 push | ✅ 本轮 4 个 commit（`32db683`/`7de68cb`/`066fff4`/`f7cc1ff`）均未 push |
| 不碰 `gt/**` / sm24 testdata / 不读 GT | ✅ 本轮改动文件：`render_vector_to_png.py`/`reading.py`/`schema.py`/`view_manifest.py`(×2)/`run_stage.py`/`isolation.py` + 4 测试文件，零触碰 gt/testdata |
| 不动 `AI_agent/` 下除自己执行日志外的管理文档 | ✅ 仅续写本执行日志 §8；工作树里 CLAUDE.md/decision_log/plan/lightgate 的未提交改动是 orchestrator 的，本轮零碰、零 `git add` |
| 做完一件存一件、每条 commit | ✅ NIT `32db683` → X-1+X-2 `7de68cb` → X-3 `066fff4` → X-5 `f7cc1ff`，每条改完立即验证+neuter+commit，未攒到最后 |
| 提交前只 add 自己文件 | ✅ 每个 commit 显式 `git add <具体文件列表>`，未用 `-A`/`.`；`git status` 显示的 AI_agent 未提交改动全轮未被 `git add` 命中 |
| 全仓跑测在交付前完整跑一次 | ✅ 见 §8.5（尾部原文见最终交付回复，退出码用 `pytest ...; echo $?` 而非管道 tail 判定）|

### 8.7 给 orchestrator 的交付摘要

- **X-1 已落库**（随 `7de68cb`）：gate① 新增 `reading.dimension_endpoints_in_bounds`，与 M-3 同规格。2 处 neuter 真绑。
- **X-2 已落库**（随 `7de68cb`）：可信画幅改为唯一来源 case_data 真实像素尺寸（经 `resolve_view_pixel_bounds`），
  三种撑大手段全部失效。2 处 neuter 真绑，且 neuter 后的行为逐字复现交叉审报告的数字。**附一处主动披露**：判定
  算法本身（"trusted_bounds 直接当边界"vs 交叉审出口建议的"双量纲判断"）是本席位在派工单未钉死处自行选择的
  更简单版本，已在 §8.1 详细说明局限，如需更强判定需另行拍板。
- **X-3 已落库**（`066fff4`）：`total_fit` 补锁（500×500m 近正方形结构，逼近 `total_fit` 真正生效）+ 修正
  `test_L51_over_budget_structural_canvas_is_refused_not_clamped` 失真 docstring。neuter 真绑。
- **X-5 已落库**（`f7cc1ff`，零生产码改动）：两处零锁分支各补一条锁（顶层 error surfacing + 损坏 manifest
  的 unavailable 分类）。neuter 真绑。
- **NIT 已落库**（`32db683`，接手 GLM WIP + 补锁）：单位双关拆分，GLM 实现正确、本席位补两条锁。neuter 真绑。
- **X-4 未动代码，判断已交 §8.4**：认为 `missing` 应在新 run 上阻断，倾向候选 B（merge 后自动渲染，从源头消除
  "新/老 run"判别问题），候选 A（用 `artifact_contract` 字段推断）作为备选列出并说明其局限。两个候选都涉及
  生产代码改动，按纪律停下不动手，请 orchestrator 裁定。
- 全仓测试结果见 §8.5 / 最终交付回复（退出码 + 尾部原文）。


---

## 9. r3（B-1 BLOCKER + M-1/M-2 MAJOR + MINOR 批 D 标签）— 施工 **Claude 侧执行档** · 2026-08-04

- 上游：[r3 派工单](../request/2026-08-04_batchC_r3_dispatch.md)（sol 独立复核证伪 r2 的 X-2：2×2 px 退化 fixture 掩盖了「像素当米」的量纲错配）。
- 前置状态：HEAD `f7cc1ff`（r2 收尾）；工作树里 `AI_agent/` 下其余管理文档的未提交改动是 orchestrator 的，本轮零碰、零 `git add -A`。
- 本批交付：**B-1 ✅ commit `bc50aae`** · **M-1 ✅ commit `3b2f469`** · **M-2 作为 B-1 的结构性副产品一并闭合（同一 commit，附独立回归锁）** · **MINOR（批 D 标签）✅ commit `4e19ab6`**。

### 9.0 这轮的性质（照派工单口径）

不是"没做"，是"判据没有分辨力"——r2 的 X-2 用 2×2 px 合成图人为保证了 `[360,450]` 越界；真实 case_data
（790–3000 px）会让同一检测放行原始坏载荷。本轮**全部新增/替换的锁都用真实量级 fixture**（790×1111 px，
对齐 `sm24_anchor/case_data/1f_view.png` 的真实尺寸），且每条判据类锁都配了"正例（坏载荷被 block）+
反例（合法产物不被误伤）"两条。

### 9.1 B-1 · 可信 bounds 把源图像素宽高当米制上下界 ✅ commit `bc50aae`

**路线选择：(b) 单位异常判据（内部一致性，无外部根），理由如下（照派工单要求给理由）**：

- **(a) 米制上界路线被排除**：把源图像素尺寸 × 标定比例换算成米制上界，需要一个"米/像素"比例；
  全仓 grep 过 `scale_origin`/print-scale/paper-scale 相关字段，**唯一存在的比例来源是 `scale_origin`
  （`src/agent/reading/schema.py:123`），而它是读图器（被评判方）自己声明的 dict**（`_plan_scale_origin`
  只校验它"存在且可用"，从不校验它"对不对"）。用它反推米制上界，等于把"考生自己填的比例"当成判卷基准——
  与 B-1 要修的原始缺陷同型（"考生自己填的决定这道题考不考"）。仓库里**没有第二个不可写的比例来源**
  （没有 DXF/PDF 图纸自带的打印比例元数据、没有独立标定文件）。⇒ 路线 (a) 不成立。
- **(b) 内部一致性判据被采用**：判"该坐标量级相对本视图**自己的结构（墙体/轮廓）几何**是否荒谬"
  （`src/validator/checks/reading.py:_structural_metric_reference`）。这不是在冻结一个外部事实（§5.14
  管的是那种场景），而是**固定算法（在 gate① 代码里、读图器写不到）应用在被评判方自己的数据上**的自洽检查
  ——与本文件已有的 `_chain_closure`/`_stroke_dimension_consistency` 同一族（都是"用提交物自己的其他部分
  校验提交物的某一部分"，不是"和外部冻结值比"）。
  **为什么不会误伤合法大建筑**：判据用该视图 STROKE 几何（仅墙/轮廓，不含 OCR/dimension，避免自证）的
  **中位数 + 中位绝对偏差（MAD）**、乘 10 倍（"大一个数量级"）作为容差半宽，下限 5 m；容差随建筑自身尺度
  线性放大，120×90 m 的大建筑与 10×8 m 的小建筑用**同一相对判据**，不会因为建筑大就被冤枉。
  **为什么中位数而非 min/max**：r1/r2 的三条"撑大自己边界"攻击之一（`stray_long_stroke`，插一条额外墙体
  伸到坏值附近）对 min/max 判据必胜（一个新端点就能把边界拉过去），对中位数/MAD **几乎免疫**——单个离群点
  混进多个真实点里，中位数几乎不动（execution log 内联了具体数值推演，`_structural_metric_reference` 的
  docstring 也留了同一个证明）。另两条攻击（`extra_pixel_dimension_endpoint`／`declared_image_bounds`）
  被**结构性排除**：新判据只读 strokes，从不读 dimensions/OCR/`extra.image_bounds`。

**实现**：`_structural_metric_reference`（新函数，`reading.py`）取代 `_image_bounds(trusted_bounds=...)` 分支；
`resolve_view_pixel_bounds`（`src/agent/execution/view_manifest.py`）及其在 `check_reading_stage`
（`src/validator/checks/view_manifest.py`）里的 `case_dir`/`trusted_bounds_by_stem` 消费**整体移除**（不是
留着不用——留着会变成"看似仍在防护、实际零消费者"的假 docstring，同族于本项目已撞过四次的病）。

**锁（`tests/test_checks_reading_correction.py`，真实 790×1111 px 图 + 真 `check_reading_stage`/
`build_view_manifest` 入口）**：
- `test_b1_pixel_anchor_blocks_on_a_real_case_data_scale_image`（正例：`[360,450]` 在真实尺度图上仍 block）
- `test_b1_legitimate_product_on_a_real_case_data_scale_image_is_not_flagged`（反例：合法值不被误伤）
- `test_b1_large_legitimate_building_is_not_falsely_accused` + `test_b1_unit_anomaly_scales_with_structural_extent`
  （120×90 m 建筑：合法值过、10 倍量级的坏值仍挡——证明判据是相对的、不是绝对阈值）
- `test_b1_resists_stray_stroke_self_inflation`（r1/r2 三招撑大之一，中位数/MAD 免疫，真实图入口复测）
- `test_b1_declared_image_bounds_and_dimension_endpoints_cannot_inflate_the_reference`（另两招，结构性排除）
- `test_b1_m2_undecodable_source_image_no_longer_degrades_the_check`（见 §9.2）

旧 `_write_x2_case(image_size=(2,2))` 及依赖它的两条测试（`test_trusted_bounds_from_case_data_survive_all_three_inflation_tricks`、
`test_trusted_bounds_unavailable_falls_back_without_crashing`）**整体删除**，不是留着共存——它们测的正是
已经不存在的"trusted vs fallback 双路径"概念，留着会产生两套不一致的判据心智模型。

**neuter 台账**：把 `_ocr_anchors_in_bounds`/`_dimension_endpoints_in_bounds` 的 `_structural_metric_reference(view)`
换回旧的 `trusted_bounds` 直接比较（活体验证过一次，见开发过程；本节交付前最终态未残留 neuter 痕迹，
`git diff --stat` 干净）。目标测试集 `tests/test_checks_reading_correction.py` 单独跑 **95 passed**；
交叉受影响面 `tests/test_reading_ruler_r1_batchB.py`（21）/`tests/test_check_view_manifest_coverage.py`+
`test_view_manifest_generator.py`+`test_view_manifest_schema.py`+`test_isolation.py`（295）/
`tests/test_run_stage_flow.py`（35）逐一单独复跑，零红、零意外变化。

### 9.2 M-2 · 源图不可解码时静默回落 ⇒ 作为 B-1 的结构性副产品闭合

sol 的 M-2 复现依赖 `resolve_view_pixel_bounds` 对不可解码图片 `continue` 跳过、静默回落到产品自算 bounds——
但这个函数**整个被 B-1 删除**（§9.1）。新判据从不读取/解码 case_data 图片文件，"解码失败回落"这条路径
**不再存在**，不是"修复了"而是"不再有这个分支"。用 `test_b1_m2_undecodable_source_image_no_longer_degrades_the_check`
钉住：case_data 目录里放一个真实的、PIL 打不开的垃圾字节 `.png` 文件，走真实 `build_view_manifest` +
`check_reading_stage`（`build_view_manifest` 只 hash 原始字节、不需要解码，成功），`[360,450]` 依旧 block，
`reading.view_manifest_coverage` 依旧 PASS——与 sol §2.2 表格里"图片不可解码"那一行的现象吻合，但结果从
"静默放行"变成"照常 block"。

### 9.3 M-1 · reading_mode 冻结过晚 ✅ commit `3b2f469`

**根因**：`provision_reading_mode` 唯一写点在 `record_baseline()`（record 时刻），读的是 `run_config.yaml`
**当时**的内容——0_reading 真实执行发生在更早，中间可以被编辑。

**修法**：把冻结挪到 `_manifest_for_attempts`（`scripts/tool_scripts/run_stage.py`）——`cmd_run`/`cmd_resample`/
`cmd_flow` 三个 attempt-creating 入口**唯一共同的**、且早于任何 stage 被绘制/校验的关口，与 `run_policy` 冻结
同一笔事务（`provision_run(...)` 紧接着）。**机会性**（`reading_mode is None` 时整段跳过）——不新增"每个 run
必须声明 lane"的强制，只保证"声明了就不能在执行后被换"。`provision_reading_mode` 自身的幂等 + drift 检测
（已有代码，未改）天然提供了这个保证：同一 run 第二次调用若声明变了，直接 `reading_mode_drift` 抛错。
`ValueError` 包成 `SystemExit`（照 `_manifest_for_attempts` 内既有的 V1-grandfather 拒绝同一惯用法，
CLI 命令的拒绝是可控退出不是裸异常）。

**锁**（`tests/test_reading_mode.py::test_M1_late_edit_after_reading_executed_fails_closed_not_recorded_as_autonomous`）：
走**两次真实 `cmd_flow` 调用**（不是内部函数直调）——第一次声明 `lane:controlled`（真 reading-agent 在场）、
`from=to=0_reading`、不 record，0_reading 真实执行；随后把 `run_config.yaml` 改成 `lane:autonomous`；
第二次 `cmd_flow(..., record=True)` 必须 `pytest.raises(SystemExit, match="reading_mode_drift")`——
冻结记录仍是 `controlled`，`_run/baseline.json` 从未被写出。**neuter**（拿掉 `_manifest_for_attempts` 里
`reading_mode is not None` 那段/拿掉三处调用点的 `reading_mode=run_config.reading_mode` 实参）后复跑：
锁在**更早**的断言处就红（`_run/reading_mode.json` 在第一次调用后就不存在，因为唯一写点又回到了 record 时刻）
——证明锁确实绑在新增的早冻结机制上，不是绑在其他偶然因素上。

未改动 `record_baseline()` 内部逻辑（`require_reading_mode=True` 分支仍调用 `provision_reading_mode`）——
它现在只在"早冻结从未发生"（未声明 lane）时才会真正写入，drift 场景在到达它之前已经在 `_manifest_for_attempts`
被拦下，这是防御纵深不是遗漏；`record_baseline.py` 独立 CLI（sol S-3 提到的"仍宽松"另一半）**不在本条范围**
——r3 派工单 M-1 的措辞明确锁"走真实 `flow --record` 入口"，未要求覆盖独立 CLI，如需覆盖需另行派工。

**复跑**：`tests/test_reading_mode.py` + `tests/test_run_stage_flow.py` 51 passed；扩大面
`tests/test_isolation.py`+`test_check_view_manifest_coverage.py`+`test_orchestrate_baseline.py`+
`test_provenance_baseline.py` 263 passed + 1 xfailed。

### 9.4 MINOR · 批 D 内部标签重叠/截断 ✅ commit `4e19ab6`

两个独立缺陷，sol 的 mutation 表 N-16（删掉五类内部标签绘制、新测试仍 5 passed）证明了**旧测试对标签内容
零绑定**：

1. **截断**：`segment.id[-10:]`/`polygon.id[-14:]`/`opening.id[-12:]` 三处硬切片。改为 `_fit_label_font`
   ——在 `[6,9]` 字号区间里找一个能让**完整**文本 `draw.textlength` 落进预算宽度的最大字号，找不到就用最小
   字号照样画完整文本（宁可视觉溢出也不裁字，照派工单"⛔ 不许裁掉"字面执行）。
2. **重叠**：claim rail 按 opening 数量从面板底部往上堆行（每行 `_TYPED_RAIL_ROW_H=20px`），旧代码算幾何缩放比例
   时用整个面板高度，不管 rail 会占多少行——openings 一多，rail 行就会画进几何区。改为**先按该楼层 opening 数
   算出 `rail_reserved` 保留带，再用"面板高度 − 保留带"去拟合几何缩放比例**，几何绘制物理上不可能再画进
   保留带。

**锁**（`tests/test_batch_d_typed_grade.py`，用 `batch_d_four_facade_fixture`——F1 每个立面各一扇窗，
共 4 个 opening，正是 sol 复现用的对抗形状）：
- `test_L_D4_segment_polygon_opening_labels_are_full_untruncated_text`：把 render 的 `audit` 字典扩展出
  `label:segment:*`/`label:polygon:*`/`label:opening:*`/`label:floor_polygon_count:*` 条目（存的是**实际画的
  完整文本**，与 `draw.text` 同一变量），断言等于未截断的真实 id（segment id 如
  `"F1:boundary:North:0"` 长 20 字符，远超旧的 `[-10:]` 切片长度，确保 fixture 真的踩中截断场景）。
- `test_L_D4_claim_rail_reserved_band_stays_free_of_plan_geometry`：4-opening 楼层算出的保留带（面板底部
  `rail_reserved` px 高、全宽）内，断言**不出现任何 GT 几何色**（TRUTH/GT_FILL/GT_EDGE/REFERENCE ——
  这四种颜色只有几何绘制会用，claim rail 只用 GREEN/ORANGE/RED/hatch，两者色域不交叉，因此这个判据不依赖
  rail 具体画在哪个 x 位置）。

**neuter 台账（两处，均活体验证、备份/还原用 `cp` 而非 `git checkout --`）**：
1. 把 `polygon_label`/`segment_label` 换回 `[-14:]`/`[-10:]` 切片 ⇒ `test_L_D4_segment_polygon_opening_labels_are_full_untruncated_text`
   红（`AssertionError: assert 'ry:North:0' == 'F1:boundary:North:0'`），`test_L_D4_claim_rail_...` 不受影响。
2. 把 `scale` 计算里的 `- rail_reserved` 项去掉（退回旧公式）⇒ `test_L_D4_claim_rail_reserved_band_stays_free_of_plan_geometry`
   红（`AssertionError: (148, 148, 142)` ——TRUTH 色出现在保留带内，与 sol 报告描述的"South 边界/标签被
   rail 盖住"同一现象），`test_L_D4_segment_polygon_opening_labels_...` 不受影响。
   两处均**零连带**（各自 neuter 只影响对应的新锁），还原后 `git diff --stat` 干净、24 条批 D 测试复跑全绿。

**⚠️ 运维事故如实登记**：施工过程中两次误用 `git checkout -- <file>` 想撤销"临时 neuter 探针"，
结果连同**尚未 commit 的正式修复**一起撤没了（`git checkout --` 撤到的是最近一次 commit，不是"探针前"）——
两次都靠及时发现 + 重新逐字重写修复内容补救，最终交付的代码与被误删前逐字一致（已用 `grep`/`diff` 核对）。
自此往后的 neuter 验证一律改用 `cp <file> <backup>` / `cp <backup> <file>` 而不是 git 命令，避免与真实改动
的提交状态耦合。

### 9.5 全仓测试结果（⛔ 无 `-m`，`pytest -q -n 4`）

<!-- 全仓跑测尾部原文见交付回复 -->

### 9.6 合规自检

| 项 | 结论 |
|---|---|
| 判据类检查 fixture 用真实量级 | ✅ B-1 全部新锁用 790×1111 px（对齐 sm24_anchor 真实源图），零 2×2 px 残留 |
| 每条锁另证「正例 block + 反例不误伤」 | ✅ B-1 六条（含大建筑一对）/ M-2 一条（undecodable 仍 block）/ M-1 一条（真实两次 flow 调用）/ MINOR 两条（截断+重叠各自独立） |
| 锁走真实入口 | ✅ B-1/M-2 走真 `check_reading_stage`+`build_view_manifest`；M-1 走真 `cmd_flow` 两次调用；MINOR 走真 `render_typed_grade` |
| 断言落具体字段/文本 | ✅ B-1 落 `status`/`evidence["offenders"]["reason"]` 具体子串；M-1 落 `SystemExit` message 子串 + `reading_mode.json`/`baseline.json` 具体字段；MINOR 落 `audit["label:*"]` 具体文本 + 具体 RGB 元组 |
| neuter「摘掉即红、零连带」+ 如实登记 | ✅ B-1（开发中活体验证）/ M-1（一处）/ MINOR（两处）逐条见 §9.1/9.3/9.4，含一次运维事故的如实登记 |
| 判命令成败用 `cmd > log 2>&1; echo $?` | ✅ 全程未用 `\| tail` |
| 不 push | ✅ 本轮 3 个 commit（`bc50aae`/`3b2f469`/`4e19ab6`）均未 push |
| 不碰 `gt/**` / sm24 testdata / 不读 GT | ✅ 本轮改动文件：`reading.py`/`view_manifest.py`(×2)/`run_stage.py`/`isolation.py`/`render_grade.py` + 3 测试文件，零触碰 gt/testdata |
| 不动 `AI_agent/` 下除自己执行日志外的管理文档 | ✅ 仅续写本执行日志 §9；工作树里其余 AI_agent 改动是 orchestrator 的，零 `git add` |
| 做完一件存一件、每条 commit → 再跑全仓 → 再回报 | ✅ B-1 commit→全仓验证（2153/10/0）→M-1 commit→目标+扩大面验证→MINOR commit→目标面验证→**本节交付前再跑一次完整全仓**（见 §9.5/最终交付回复） |
| ⛔ R1.5/R2/reading_mode 强制/独立 CLI 收口 | ✅ 均未做（M-1 明确限定"走 flow --record 入口"，独立 CLI 收口留白见 §9.3 结尾） |

### 9.7 给 orchestrator 的交付摘要

- **B-1（BLOCKER）已落库**（`bc50aae`）：选路线 (b) 单位异常判据，理由详 §9.1；`resolve_view_pixel_bounds`
  连同其消费方一并移除（不留假装仍在用的死代码）；六条新锁全部用真实图像尺度，含大建筑不误伤的相对判据证明。
- **M-2（MAJOR）已闭合**（同 commit）：作为 B-1 的结构性副产品——依赖的解码分支已不存在，配一条独立回归锁。
- **M-1（MAJOR）已落库**（`3b2f469`）：冻结点挪到 `_manifest_for_attempts`（与 run_policy 同一事务），
  机会性（未声明不强制）；两次真实 `cmd_flow` 调用的锁复现并挡住了 sol 的 LATE_FREEZE_PROBE 原始场景。
  `record_baseline.py` 独立 CLI 未覆盖（超出本条派工范围，需另行派工）。
- **MINOR（批 D 标签）已落库**（`4e19ab6`）：截断改字号自适应、重叠改保留带隔离几何缩放；audit 字典新增
  可断言的文本条目，两条新锁各自独立 neuter 验真。
- **运维事故已如实登记**（§9.4 末）：两次误用 `git checkout --` 撤掉未提交的正式修复，均已发现并逐字重写补救。
- 全仓测试结果见 §9.5 / 最终交付回复（退出码 + 尾部原文）。

## 10. r4（降档）— 施工 **Claude 侧执行档** · 2026-08-04

- 上游：orchestrator 直接派工（口头/上下文指令，非独立派工单文件）——r3 加的单位异常判据经 sol 独立复核 +
  orchestrator 独立实测，两个方向都不稳（假阴性：全像素空间结构可蒙混；假阳性：普通闭合 polyline 房间 +
  合法标注、狭长建筑 + 合法标注均被误 FAIL），**挡住了下一步要跑的 sm21/sm24 正式生产 run**。
- **用户已拍板（2026-08-04）**：把这两条检查从「阻断」降为「提醒」，结构性修法归 R1.5（读图器只写像素锚点
  + 引用的标注，米制由代码唯一换算）。**不许再在这个启发式上打补丁。**
- 前置状态：HEAD `e515f6c`（R1 批 B r1 收尾），本条紧接批 C r3 之后落库，全仓基线 2106 + 10 xfail 零红。

### 10.0 这轮的性质

不是修 bug、不是加新判据——是**收窄一个已知不可靠机制的处置范围**：从「决定要不要拒收整份产物」降到
「记一笔提醒，人来看」。**⛔ 不删检查、⛔ 不吞证据**：`_ocr_anchors_in_bounds` /
`_dimension_endpoints_in_bounds` / `_structural_metric_reference` 三个函数一行代码未删，FAIL 事实、
`offenders`、`structural_reference` 证据字段照常产出；变的只是 `schema.disposition()` 里这两个
check_id 的出口——`_OCR_ANCHOR_BLOCK_PROFILES` / `_DIMENSION_ENDPOINT_BLOCK_PROFILES` 从
`{"golden", "regression"}` 改成永久空集，任何 profile 下都只到 FLAG、不到 BLOCK。

### 10.1 改动清单

**`src/validator/checks/schema.py`**（唯一生产码改动点）：
- 两个常量改为 `frozenset()`（空集，`disposition()` 里对应分支因此永远不落进 `if run_profile in {...}`，
  但**分支本身保留**、标 `# unreachable while the set above is empty` 而非直接删掉，保留「这里曾经/将来
  可能有 BLOCK 出口」的可读性，不是留死代码掩盖）。
- 两处常量定义上方的注释、`disposition()` 内两处分支注释：写明 2026-08-04 r4 降档、已知假阴性
  （全像素空间结构可蒙混）+ 假阳性（普通 10x8 m 闭合 polyline 房间、60x4 m 狭长建筑，均举出会触发的
  具体形状），结构性修法指向 R1.5。

**`src/validator/checks/reading.py`**（仅 docstring，零逻辑改动）：
- `_ocr_anchors_in_bounds` / `_dimension_endpoints_in_bounds` 两个 check 函数 docstring 各加一段
  ⚠️ 2026-08-04 r4 说明：ADVISORY ONLY（FLAG，任何 profile 下都不 BLOCK），并点名"不要靠调 MAD 因子 /
  margin 去'修'——那只是把一种失败模式换成另一种"，结构性修法是 R1.5。
- `_structural_metric_reference` docstring 新增「KNOWN LIMITATIONS」大段：逐条写出假阴性的机制（整份
  view 的 stroke 几何本身就是像素尺度时，median/MAD 基准是从那份像素尺度几何算出来的，坏坐标相对它就不
  再是离群值）+ 假阳性的机制（闭合 polyline 把起点重复写成终点时，median 被拉向那个重复角点而不是形状
  中心——10x8 m 房间 `[(0,0),(10,0),(10,8),(0,8),(0,0)]` 算出 median_x=0（不是 5）+ MAD_x=0，把同一个
  房间里合法的公制标注都关在容差带外面）。

**`tests/test_checks_reading_correction.py`**：
- 7 处既有断言从「`check_id in _ids(rep)`（即 blocking）」改成「`check_id not in _ids(rep)` +
  `check_id in {r.check_id for r in rep.flagged()}` + （能推出时）`rep.passed`」，docstring 同步改写
  "BLOCKS" → "advisory / FLAG"，neuter 描述从「删掉检查会怎样」改成「重新加回 BLOCK 分支会怎样」（因为
  现在要锁住的是「不 BLOCK」这件事，删检查已经不是这两条锁要防的方向）：
  - `test_ocr_pixel_anchor_out_of_bounds_blocks_acceptance` → 更名
    `..._is_advisory_under_acceptance`
  - `test_dimension_pixel_endpoint_out_of_bounds_blocks_acceptance` → 更名
    `..._is_advisory_under_acceptance`
  - `test_b1_pixel_anchor_blocks_on_a_real_case_data_scale_image` → 更名
    `test_b1_pixel_anchor_is_still_surfaced_on_a_real_case_data_scale_image`
  - `test_b1_unit_anomaly_scales_with_structural_extent`
  - `test_b1_resists_stray_stroke_self_inflation`
  - `test_b1_declared_image_bounds_and_dimension_endpoints_cannot_inflate_the_reference`
  - `test_b1_m2_undecodable_source_image_no_longer_degrades_the_check`
  两条纯 lenient-profile 测试（`..._only_flags_under_lenient` ×2）**断言本身未变**（本来就测 FLAG），
  只更新了 docstring 说明它们与新增的 acceptance-profile 测试现在是同一件事的两半。
- **新增两条反例锁**（本轮真正的交付重点，见 §10.2）。

### 10.2 两条反例锁的实测结果

放在 B-1 段落末尾，`test_b1_r4_closed_polyline_10x8_room_with_legitimate_annotation_is_not_blocked` /
`test_b1_r4_elongated_60x4_building_with_legitimate_annotation_is_not_blocked`。两条都用**单条闭合
polyline stroke**（真实"描房间轮廓再回到起点"的常见编码）+ 一条落在形状内部、明显合法的 OCR 标注：

| | 形状（closed polyline） | 合法标注 anchor | 算出的 fence | 结果 |
|---|---|---|---|---|
| 反例锁 #1 | `(0,0)→(10,0)→(10,8)→(0,8)→(0,0)` | `[9.0, 4.0]`（房间正中偏右，绝非越界） | x∈[-5,5], y∈[-5,5]（median 被重复的 (0,0) 拉到 0，非几何中心 5） | **FAIL**（真实复现了假阳性）+ **不 BLOCK**（`rep.passed is True`） |
| 反例锁 #2 | `(0,0)→(60,0)→(60,4)→(0,4)→(0,0)` | `[55.0, 2.0]`（狭长建筑远端，仍在建筑内） | 同上机制，x∈[-5,5], y∈[-5,5] | **FAIL** + **不 BLOCK**（`rep.passed is True`） |

用 Python 独立算了一遍这两个 fence（`median`/`MAD` 手算，不依赖被测代码）先确认了这就是 r3 派工单描述
的那个真实故障形状，再写进测试固定断言，不是拍脑袋编的反例。两条锁都断言四件事：`status is
CheckStatus.FAIL`（如实记录已知假阳性，不假装它消失了）、`check_id not in _ids(rep)`（不进 blocking
集合）、`check_id in rep.flagged()`（仍然被 FLAG 出来，人能在报告里看到）、`rep.passed`（这份合法产物
最终没被拒收）。这正是本轮降档要保证的东西：**已知有假阳性的检查依然照实报告，但不能再拿这个假阳性去
拒收一份好端端的产品**。

### 10.3 neuter 台账

对 `src/validator/checks/schema.py` 做一次性反向 neuter（把两个常量从空集改回
`{"golden", "regression"}`，模拟"有人把降档撤销、悄悄把 BLOCK 分支重新接上"）：先 `cp` 一份到 scratchpad
备份，用脚本原地把 `frozenset()` 换回 `frozenset({"golden", "regression"})`，跑完整个目标测试文件后
再用备份 `cp` 回原文件还原（未用 `git checkout --`，规避本项目 memory 里记过的「探针期间 git 命令误撤
未提交改动」事故模式）：

```
cp src/validator/checks/schema.py <scratchpad>/schema_backup.py
python3 -c "改两个常量 frozenset() → frozenset({'golden','regression'})"
pytest -q tests/test_checks_reading_correction.py > neuter_r4.log 2>&1; echo $?
cp <scratchpad>/schema_backup.py src/validator/checks/schema.py   # 还原
```

红了 **11 条**（`echo $?` = 1，86 passed / 11 failed）——比最初口算预期的 9 条多 2 条，原因是两条
acceptance-profile 参数化测试（`test_ocr_pixel_anchor_out_of_bounds_is_advisory_under_acceptance` /
`test_dimension_pixel_endpoint_out_of_bounds_is_advisory_under_acceptance`）各 `@pytest.mark.parametrize`
了 `golden`/`regression` 两档，算作 4 条独立用例而非 2 条；**如实按实测数字更正，不按口算数字報告**。
完整红单：
`test_ocr_pixel_anchor_out_of_bounds_is_advisory_under_acceptance[golden]` /
`[regression]`、`test_dimension_pixel_endpoint_out_of_bounds_is_advisory_under_acceptance[golden]` /
`[regression]`、`test_b1_pixel_anchor_is_still_surfaced_on_a_real_case_data_scale_image`、
`test_b1_unit_anomaly_scales_with_structural_extent`、`test_b1_resists_stray_stroke_self_inflation`、
`test_b1_declared_image_bounds_and_dimension_endpoints_cannot_inflate_the_reference`、
`test_b1_m2_undecodable_source_image_no_longer_degrades_the_check`、以及新增的两条反例锁
`test_b1_r4_closed_polyline_10x8_room_with_legitimate_annotation_is_not_blocked` /
`test_b1_r4_elongated_60x4_building_with_legitimate_annotation_is_not_blocked`——恰好是本轮改写/新增的
「断言不 BLOCK」的全部用例。两条纯 lenient-profile 测试（`..._only_flags_under_lenient` ×2，本来就没
变过断言）**不受影响、仍绿**。零连带：其余 86 条全绿（97 − 11 = 86，与实测 `86 passed` 吻合）。
还原后重跑全文件，97 passed、`git diff -- src/validator/checks/schema.py` 干净（与备份逐字节相同）。

### 10.4 已知假阴/假阳的具体形状（写进证据、供人核对）

- **假阴性**：一份 view 的全部 stroke 几何本身就是用像素坐标写的（不是"混了一个坏点"，是整份坐标系
  错了）——`_structural_metric_reference` 从这份像素尺度的几何本身算出 median/MAD，坏的 OCR anchor /
  dimension endpoint 相对这个基准不再是离群值，直接放行。
- **假阳性（本轮两条反例锁固定的形状）**：
  1. 普通 10x8 m 房间，用单条闭合 polyline 描边、起点终点重复（"描完一圈回到起点"的自然写法）——
     median 被拉向重复的角点，把房间内部合法的标注关在容差带外。
  2. 60x4 m 狭长建筑，同样的闭合 polyline 编码，同样的机制。
- 两种假阳性的共同根子：这是一个**统计启发式**（median/MAD 相对一份坐标点集的健壮统计量），不是对
  "单位"这个语义概念的真实校验——它没有办法知道这些点是不是真的构成了一个"形状"，更判断不出这个形状
  的单位是米还是像素。

### 10.5 结构性修法归 R1.5

不打算在 MAD 因子、margin、或者"排除重复端点"这类启发式补丁上继续投入——每一次调整都只是把一种失败
模式换成另一种（调紧会漏真正的像素坐标、调松会误伤更多合法形状），因为病根不在参数、在**这一层根本
拿不到"单位"这个信息**：`ReadingView` 里只有一堆浮点数，无论是米是像素，看起来都一样。真正消灭这个问题
的地方在上游——**R1.5**（读图器只写源图像素锚点 + 引用的尺寸标注，公制坐标由确定性代码唯一换算）落地后，
"像素被当成米"这个错在接口层面就写不出来，不需要靠下游猜。本轮的降档是撑到 R1.5 落地之前的过渡状态：
不再让一个不可靠的启发式挡生产 run，同时不假装它已经解决了。

### 10.6 全仓测试结果（⛔ 无 `-m`，`pytest -q -n 4`）

<!-- 全仓跑测尾部原文见交付回复 -->
