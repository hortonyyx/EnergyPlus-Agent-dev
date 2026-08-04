# R1 批 C · r1 返工 · 交叉对抗审（Claude 侧 · Opus 档）— **本文最终版**

- **日期**：2026-08-04
- **被审对象**：`d0e33ef` → `57d47ea`（7 commit，施工 = **GLM**，跨家族「谁写谁不批」满足）
- **审阅席**：Claude 侧子代理（Opus 档），只审不修；**主工作树零改动、零 commit、零 push**
- **上游**：[r1 返工派工单](../request/2026-08-04_reading_ruler_batchC_r1_rework_dispatch.md) ·
  [轻门 §5/§6](2026-08-04_reading_ruler_batchC_orchestrator_lightgate.md) ·
  [上轮交叉审](2026-08-04_reading_ruler_batchC_crossreview_claude.md) ·
  [施工执行日志 §7](../execution/2026-08-04_reading_ruler_batchC_glm.md)

---

## 0. 总判定：**APPROVE-WITH-CHANGES**

| 级别 | 数 | 条目 |
|---|---|---|
| **BLOCKER** | **0** | 上轮 BLOCKER（B-1）在我能驱动的**每一条真实路径**上都已修好，且未修出新的 |
| **MAJOR** | **2** | X-1 N-3 删掉了「像素化 dimension 端点」的最后一个探测器（**本批引入的回归**）· X-2 M-3 的「可信画幅」由被测方自己写的字段决定，**产品可自行拆掉这道门** |
| **MINOR** | **3** | X-3 `MAX_CANVAS_PIXELS` 零锁 + L-51 docstring 已失真 · X-4 刚 merge 完、零渲染的 run 照样批得过 · X-5 两处新分支零锁 |
| **NIT** | **2** | X-6 stage-root 陈旧 `_render.png` 无人清理 · X-7 **我自己的环境事故**：探针克隆静默失败（管道吃掉退出码）导致差点在旧树上开工 |

**⭐ 结论一句话**：**上轮判的「只在一条布局上修好了」这次是真的修好了 —— 七条锁全部真绑、零假锁、B-1 的锁确实走盲重读真实路径。
本轮两条 MAJOR 不是 B-1 的复发，而是 M-3/N-3 这一半交付得不完整 —— 与上轮 F-4「移走症状没补检测」**同形、换了个字段**。**

**⛔ 处置建议**：两条 MAJOR **必须在批 C 宣告收口之前闭掉**。理由不是严重度分级，而是：
批 C 收口会解除「不得发布识图分数 / 变好变坏结论」这条硬约束，而 X-1 + X-2 合起来意味着
**「像素/公制混淆」这类坏数据的探测器目前既不完整、又可被被测产品自行绕开** —— 带着它解除约束，
等于用一把自己承认有洞的尺子去发布结论。

---

## 1. 独立全量（主工作树，`pytest -q -n 4`，⛔ 无 `-m`）

```
2117 passed, 10 xfailed, 177 warnings in 595.94s (0:09:55)
```

**与派工单声明的基线 2117 passed + 10 xfailed 逐字一致、零红**（含派工单点名的 `test_zone_agent_creates_two_zones`，本次网络通过）。

---

## 2. P-1（最高权重）· 上轮 BLOCKER 真的修好了，且没修出新的 —— **成立**

**方法：按要求「把每条路径都实际走一遍」，不只读码。** 全部在 `/tmp` 沙箱里用**真实 case（sm24_anchor）+ 真实历史识图产物**驱动**真实 CLI**。

| # | 真实路径 | 怎么驱动的 | 结果 |
|---|---|---|---|
| **A** | **非隔离直跑 / flat flow** | 真 CLI `run_stage.py run sm24_anchor run_p1_flatflow 0_reading` | 归档产物 = **flat `{'1f_view':…,'South_view':…}`（无 `views` 包装）** ⇒ 渲出 2 张 PNG，`status=complete` |
| **B** | **健康 flat flow（五图齐全）** | 同上，run_p1_healthy | gate① 通过（0 block / 5 flag）⇒ **渲出 5 张 PNG**，`status=complete`，judge packet 内含 5 条渲染路径，`approve-review` **rc=0 放行** |
| **C** | **judge 打回后的盲重读** | 真 CLI `resample sm24_anchor run_p1_healthy 0_reading` | attempt 002 生成 ⇒ **两个 attempt 各 5 张 PNG、双双 `complete`**，judge packet 同时给出两轮共 10 条渲染路径 |
| **D** | **隔离 merge 聚合布局** | 真实历史 merge 产物 `run_2026-08-01_haiku_w5_scoped_d2/0_reading/attempts/001/output.json`（带 `isolation_provenance.json`）喂真 `_render_stage` | 渲出 2 张 PNG，`status=complete` |
| **E** | **历史 pre-O-1 run 重渲** | 同 D（该 run 渲染前 `_reading_render_status` = `missing`） | `missing → complete`，未破坏既有产物 |
| **F** | **错误命名的 flat flow** | 真 CLI，reader 把 `1f_view` 写成 `1f_view_view.json` 等五个 | **gate① BLOCK**：`reading.view_manifest_coverage: 5 required view(s) have no matching produced artifact; 5 produced artifact(s) do not match any expected_output_id` |

**证伪三个目标各自的结论**：

- **① 有产物却渲不出图** —— 在 A–F 六条路径上**全部证伪失败**（都渲出来了）。**但见 X-4**：
  「刚 merge 完、还没跑过任何会触发渲染的 verb」这一档确实是零图，且**不阻断**（详 §5）。
- **② 渲染失败没人发现** —— 证伪失败。真失败（逐图 raise / output 读不出 / finalize 崩）三种形态都落
  `render_manifest.json` 且 `status=unavailable`，`cmd_approve_review` 硬拒。
- **③ 健康的 run 被反过来拒批** —— **证伪失败**，六条路径无一复现。
  形状识别的两个分支我也做了穷举核查：`_load_isolated_views`（`isolation.py:560`）**强制**聚合件必须是
  `{'views': {...}}`（否则 merge 直接 raise），`_draw_reading`（`run_stage.py:209-211`）**只**产出 `{vj.stem: view}` ——
  **第三种形状在产品里不可达**，所以 `_extract_reading_views` 的 flat 分支不存在「把元数据 dict 误当 view」的现实入口。

**⇒ P-1 成立。上轮 BLOCKER 已在所有真实路径上闭合。**

---

## 3. P-2 · `empty` / `missing` / `unavailable` 三态互斥可区分，只有真失败才阻断 —— **成立**

`run_stage.py:777-789`（finalize 三分支）+ `:801-820`（`_reading_render_status`）+ `:2329`（唯一阻断点）。

| 状态 | 触发条件 | 阻断 review？ | 我的实测 |
|---|---|---|---|
| `complete` | ≥1 view 渲成、零失败 | 否 | A–E 六条路径 |
| `empty` | 形状认得出、views 为空 | **否** | `{}` ⇒ `empty`，`approve-review` rc=0 |
| `unavailable` | 逐图失败 / output 读不出 / finalize 崩 / **manifest 本身读不出** | **是** | 三种形态各实测阻断 |
| `missing` | 完全没有 manifest | 否（向后兼容，刻意） | 见 X-4 |

**找一条输入让三态混淆或让 `empty` 阻断 —— 证伪失败。** 三态在 `_finalize_reading_renders` 里是互斥的
if/elif/else，`missing` 只由「文件不存在」产生，四者不可能同时成立。

---

## 4. P-3 · M-3 挡得住真实病灶、不误伤合法标注 —— **成立**；但**门的高度由被测方决定（MAJOR X-2）**

### 4.1 挡得住真实病灶 ✅ —— 用**真实产物**验的，不是 fixture

我在全仓找到了那份真实病灶产物（**唯一一份**，全仓扫描 `ocr_texts[].anchor` 绝对值 > 60 的只有它）：

`case_tests/e2e_tests/sm24_anchor/run_2026-08-01_haiku_w5_scoped_d2/0_reading/attempts/001/output.json` → `1f_view`

```
1f_view   n_ocr=1  max_anchor=450  bounds=(0.0, 10.0, 0.0, 20.0)
   regression   -> fail  blocking=True      ← 严格档 BLOCK
   exploratory  -> fail  blocking=False     ← 宽松档 FLAG
South_view  (无 ocr)  -> pass
```

**⇒ 真实的「pixel anchor [360,450] 配 10×20 m 结构」被精确命中，分档正确。**
并且这条检查在**真实 flat-flow CLI 跑测里真的出现在 gate① 输出里**（§2 路径 A 的
`⚠️ 1f_view.reading.ocr_anchors_in_bounds: 1 ocr anchor(s) invalid or out of bounds`）——
不是只在单测里活着。

### 4.2 不误伤合法 metric annotation ✅ —— 全仓真实产物零假阳性

扫全仓 246 个候选 view JSON ⇒ **成功解析 183 个 view，其中 31 个带 `ocr_texts`，`regression` 档下 FAIL 数 = 0**。

### 4.3 ⛔ 有没有「clamp 后放行」 —— **没有**

`_ocr_anchors_in_bounds`（`src/validator/checks/reading.py:319-364`）只 `add_fail` + 落 evidence，
**不改任何坐标、不丢任何条目**。N-3 侧同理（详 §6）。

### 4.4 ⛔ **MAJOR X-2：这道门的高度是被测方自己写的**

`_ocr_anchors_in_bounds` 的「可信画幅」来自 `_image_bounds(view)`（`reading.py:333 → :369`），而
`_image_bounds` **完全由产品自己写的几何算出来**，且优先采信一个**未声明的 extra 字段**
`image_bounds`（`reading.py:405-417`；`ReadingView.model_config = ConfigDict(extra="allow")`，
`src/agent/reading/schema.py:120`）。

实测（同一个 `[360,450]` 像素 anchor，`run_profile="regression"`）：

```
ocr pixel only                     bounds=(0.0, 10.0, 0.0, 8.0)     ocr=fail   blocking=True
ocr pixel + 一个像素化 DIM 端点     bounds=(0.0, 365.0, 0.0, 450.0)  ocr=pass   blocking=False
ocr pixel + 一条乱伸的长 stroke     bounds=(0.0, 400.0, 0.0, 500.0)  ocr=pass   blocking=False
产品自己写 image_bounds:{x:[0,1000],y:[0,1000]}                      ocr=pass   blocking=False
```

**失败场景（一句话）**：一个把像素当公制的读图器**不会只错一个字段** —— 它同时把某个尺寸端点
或某条 stroke 也写成像素，于是**它自己把可信画幅撑大到把那个坏 anchor 包进去，M-3 当场失效**。
即：**M-3 只抓得住「恰好只有 ocr_texts 一处错」的窄形状**，抓不住真实的混淆形态。

**这与项目已栽过的 `if provenance != "dimension_derived": continue`（考生写 `seen` 即整条检查跳过）
是同一个病：产品内容决定考卷。** `image_bounds` 这条更直接 —— 一个**未声明的 extra 字段**就能整体关掉这道门。

**如实登记（对施工方公平）**：`_image_bounds` / `_explicit_image_bounds` 是**既有代码，不是本批新增**；
本批新增的是**让它成为一个 BLOCK 决策的唯一依据**。当前 183 份真实产物里 **0 份**写了 `image_bounds`，
所以没有活体利用，属设计性缺口而非在跑的洞。

**出口建议（不下放给施工方猜）**：可信画幅**不得**取自产品几何。已有一个满足
[decision_log §5.14 冻结判据两道题] 的现成第二处记载 —— **`case_data` 源图的像素尺寸 + `view_manifest`
里已冻结的图像指纹**（先于本次运行固定、进 git、被评判方写不了）。把「anchor 是不是像素」判成
「anchor 落在 [0, 图宽px]×[0, 图高px] 这个量级、却又远离公制结构画幅」即可，不依赖任何产品字段。

---

## 5. P-4 · N-3 自适应缩放没有掩盖坏数据 —— **⛔ 不成立（MAJOR X-1）**

### 5.1 ✅ 成立的部分

- **大建筑降档可渲**：200×20 m 板楼 ⇒ canvas `8192×928`（7.6 M px），不 raise。
- **只拒荒谬结构**：20 km ⇒ `CanvasBudgetExceeded: structural extent 20003.0 x 23.0 m exceeds the renderable size (a side > 8192 m even at 1 px/m)`。
- **小 case 逐字节不变** ✅ **实测**：10×8 m 平面 ⇒ `585×495` = `int(13*45) × int(11*45)`，`scale` 恰为 45。
  （施工方声称成立；且全仓 sm21/sm24 manifest byte guard 随全量绿。）
- **两种拒绝原因分离** ✅：renderer 只拒尺寸并在文案里明写「这不是 anchor 的问题」；anchor 归 gate①。
- **⛔ 不是 clamp** ✅：公制几何保留，只调 px/m；`tx`/`ty` 同步（`render_vector_to_png.py:129-134`）。

### 5.2 ⛔ **MAJOR X-1：N-3 删掉了「像素化 dimension 端点」的最后一个探测器 —— 这是本批引入的回归**

`_collect_points`（`render_vector_to_png.py:65-80`）把 **dimension 的 `from`/`to` 端点**算进画幅
（O-4 只把 **OCR anchor** 排除出去，没排除 dimension 端点）。而 M-3
（`src/validator/checks/reading.py:319`）**只检查 `ocr_texts`**。

同一份输入（10×8 m 结构 + 一个像素化尺寸端点 `from=[360,450]`）：

| | 结果 |
|---|---|
| **N-3 之前**（`d0e33ef`，我在克隆里实跑） | `CanvasBudgetExceeded: canvas 16560x20385 (337575600 px) exceeds the pixel budget` ← **3.3 亿像素那个签名** |
| **N-3 之后**（`57d47ea`，主树实跑） | **静默渲出 `6373×7845`**，不 raise |
| **gate① `regression` 档** | `blocking: []`；`dimension_chain_closure` / `stroke_dimension_consistency` / `dimensions_present` **全部 `not_applicable`** |

**失败场景（一句话）**：读图器把一个尺寸标注端点写成像素坐标 —— **渲染器不再报（N-3 之前会报）、
gate① 从来没报过** ⇒ 交付给人看的是一张降档到失真的垃圾图，而**没有任何机器可读信号说它坏了**。

**这正是上轮 F-4 判词的逐字复刻 ——「3.3 亿像素那次爆炸，曾经是坏数据的唯一信号；
把它移走 ⇒ 不再爆炸，但也没有任何地方报告它坏了 ⇒ 坏数据被彻底掩盖（比原来更难发现）」**，
只不过上轮说的是 `ocr_texts`，这轮换成了 `dimensions`。M-3 补了前者、N-3 拆了后者。

**⚠️ 对施工方公平的一点**：派工单 N-3 的字面要求（自适应缩放 / 分离两种拒绝原因 / 不 clamp）**都做到了**。
漏的是「还有第三类坏数据既不是 anchor、也不是合法的大结构」—— 这是派工单没点名的边界，
**属「边界写窄就会被实现得同样窄」的第 N 次现形，不是施工方偷工**。

**出口建议**：把 M-3 的 bounds 检查从「只查 `ocr_texts`」扩到「查一切**声明为公制**的坐标是否与
标定尺度自洽」，或至少给 dimension 端点补一条同族检查；两者都要用 §4.4 那个不依赖产品字段的量级判据。

---

## 6. P-5 · 逐锁 neuter 台账（**独立复跑，8 + 4 处**）

**环境纪律**：`/tmp` 克隆 + **`PYTHONPATH=$PWD`**（已逐次用 `import` 的 `__file__` 验证解析到克隆）；
每次**逐字精确单点替换**（mutator 脚本自带 `assert count==1`，改动为空即判「结果作废」）；
跑完 `git checkout -- .` 复原并核 `git diff` 干净。

**克隆基线**：`tests/test_reading_renders.py + test_render_vector_to_png.py + test_checks_reading_correction.py
+ test_isolation.py + test_run_stage_flow.py` ⇒ **1 failed（环境红）+ 338 passed**。
环境红 = `test_partition_on_window_jamb_real_restore_reading_r2_flags_four`，
真因 `FileNotFoundError: AI_agent/logs/experiments/2026-06-30_.../sonnet_r2/1f_view.json`（gitignored 输入不在克隆里）。
**下表所有「红了哪几条」均已扣除这条环境红。**

### 6.1 七条锁的真绑验证（本轮要求的那八处）

| # | 摘掉哪一处实现（逐字） | 红了哪几条 | 连带 | 走真实入口？ | 断言落哪 | 判定 |
|---|---|---|---|---|---|---|
| **n1** | `_extract_reading_views` 的 flat 分支删掉（只认 `{'views':…}` = B-1 病灶原状） | `test_L40_flat_flow_blind_reread_renders_and_approves` | **零** | ✅ 真 `_render_stage` + 真 `cmd_approve_review`，flat 归档件、**非隔离 fixture** | `renders/<eid>.png` 存在 + manifest `status=="complete"` + rc==0 | ✅ 真绑 |
| **n2** | 三分支 status 换回旧三元式（空集 ⇒ `unavailable`） | `test_L41_empty_view_set_is_not_render_failure` | 零 | ✅ 真 `_finalize_reading_renders` + 真 `cmd_approve_review` | manifest `status=="empty"` + `views==[]` + rc==0 | ✅ 真绑 |
| **n3** | `_finalize_reading_renders` 读/解析的 `try/except` 改回 `raise`（M-1） | `test_L41_unreadable_output_records_failure_artifact_not_missing` | 零 | ✅ 真 finalize（无 monkeypatch）+ 真 `cmd_approve_review` | manifest 存在 + `status=="unavailable"` + `error` 非空 + SystemExit | ✅ 真绑 |
| **n4** | `_render_reading_attempts` 的 per-attempt `try/except` 整段删掉（M-1 / F-2） | `test_L41_render_loop_survives_catastrophic_attempt` | 零 | ✅ 真 `_render_reading_attempts` | 已渲 attempt 的 png 仍在 `produced` + 崩掉的那个 `status=="unavailable"` | ✅ 真绑 |
| **n5** | `_write_kickoff` 文案**逐字**回退到 `<name>_view.json`（M-2 / F-3 病灶原状） | `test_build_kickoff_names_outputs_by_expected_output_id_not_view_suffix` | 零 | ✅ 读**真生成**的 `kickoff_prompt.md` | `expected_output_id` / `input_inventory.json` 在文内、`<name>_view` 不在 | ✅ 真绑 |
| **n6a** | `_ocr_anchors_in_bounds` 恒 pass（M-3 检测失明） | `..._blocks_acceptance[golden]`、`[regression]`、`..._only_flags_under_lenient` **3 条** | 零（in-bounds 那条不受影响） | ✅ 真 `check_reading_view` | `status is FAIL` + `evidence["offenders"][0]["anchor"]==[360,450]` | ✅ 真绑 |
| **n6b** | `schema.disposition` 的 OCR BLOCK 分支删掉（只剩 FLAG） | `..._blocks_acceptance[golden]`、`[regression]` **2 条** | 零（lenient FLAG + in-bounds 不受影响） | ✅ 真 `disposition` | check-id 在 `rep.blocking()` 集合内 | ✅ 真绑 |
| **n7** | `cmd_approve_review` 守卫加宽到 `in ("unavailable","missing")`（N-1） | `test_L41_missing_render_does_not_block_review_approval` | 零 | ✅ 真 `cmd_approve_review`，真 missing 路径（完全无 manifest） | `_reading_render_status=="missing"` + rc==0 | ✅ 真绑 |
| **n8** | `scale = _fit_scale(...)` 换回 `SCALE_PX_PER_M`（N-3） | `test_L53_large_legit_building_renders_via_adaptive_scale` | 零 | ✅ 真 `rv.render` | canvas 双预算内 + 长边 < 200×45 + 长宽比 > 5 | ✅ 真绑 |

**⇒ 八处 neuter 全部「摘掉即红、零连带、走真实入口、断言落具体产物字段」，零假锁。**
与轻门 §6.1 四处 + 施工方 §7 三处台账**逐条吻合**（我复跑了全部，不采信自述）。

**⭐ 断言质量单独核过**：**没有一条**断言落在「不是 None / 总数变了」上 —— 每条都落到
`status` 字符串、`offenders[0].anchor` 具体值、`renders/<eid>.png` 具体路径、或 `rc`/`SystemExit` 上。
这是本项目栽过两次的地方，本轮干净。

### 6.2 ⭐ **找到 orchestrator 与施工方都漏的：三处「门是真的、锁是缺的」**

我额外做了四处**子项 neuter**（拆开 `_fit_scale` 的两个约束项、拆开 M-1 的 reason 管线、拆开 status 的异常分支）：

| # | 摘掉哪一处 | 结果 | 判定 |
|---|---|---|---|
| **x1** | `_fit_scale` 去掉 **total_fit** 项（只剩 `min(SCALE_PX_PER_M, side_fit)`） | **全绿**（只剩环境红） | ⛔ **零锁 → MINOR X-3** |
| **x2** | `_fit_scale` 去掉 **side_fit** 项 | 红 1（`test_L53...`） | ✅ 真绑 |
| **x3** | `cmd_approve_review` 里读 manifest `error` 当 reason 的三行删掉 | **全绿** | ⛔ **零锁 → MINOR X-5a** |
| **x4** | `_reading_render_status` 的「manifest 读不出 ⇒ `unavailable`」改成 `missing` | **全绿** | ⛔ **零锁 → MINOR X-5b** |

---

## 7. P-6 · 挑战 N-2 裁定 —— **裁定成立，我证伪失败，维持「不补冗余锁」**

**要证伪的形式：找一条产品可用的输入，写出错名却被接受。** 我试了两条，**都被拒**：

1. **flat-flow 真 CLI**：把五个产物全部按 O-3 病灶拼名（`1f_view` → `1f_view_view.json`）⇒
   `⛔ reading.view_manifest_coverage: 5 required view(s) have no matching produced artifact;
   **5 produced artifact(s) do not match any expected_output_id**` ⇒ gate① BLOCK。
2. **隔离 merge**：`_load_isolated_views`（`isolation.py:560-612`）在 S4 逐图装配分支对
   missing / extra **双向 fail-closed**；聚合分支则强制 `{'views': {...}}` 形状，键名再经
   `check_reading_stage` 的 `view_manifest_coverage` 复核。

**⇒ 命名规范的「指令侧 + 执行侧」两半都有真锁**：
指令侧 = M-2 的 `test_build_kickoff_names_outputs_by_expected_output_id_not_view_suffix`（我 n5 独立验真）；
执行侧 = **`reading.view_manifest_coverage`（既有 INVARIANT 检查，两条路径共用）** + L-50。
**再补一条只会重蹈 F-5「零增量约束力」。orchestrator 的裁定我不推翻。**

**一条观察（非 finding）**：施工方在 §7.3 里说的「执行侧由既有 extra 检查锁」，更准确的说法是
**`view_manifest_coverage` 这条 INVARIANT 检查**（它 `missing` 与 `extra` 双向都报、且不受 run_profile 分档影响），
L-50 是 merge 侧的第二道。口径写清楚更好，结论不变。

---

## 8. P-7 · 边界合规 —— **全部成立**

（全部用 **tree-to-tree** diff 核，主仓库**未跑任何会刷新索引的命令**，含 `git status`。）

| 项 | 结论 | 证据 |
|---|---|---|
| 未 push | ✅ | `git rev-list --count origin/6.15_ValidationArchM0toM4..57d47ea` = **13**（本批 7 + 前序 6） |
| `gt/**` 与 sm24 `testdata_prompt.json` 零字节 | ✅ | `git diff --name-only d0e33ef 57d47ea -- 'case_tests/test_baseline/gt/**' '**/testdata_prompt.json' 'skills/**'` ⇒ **空** |
| 未读 GT | ✅ | 新增锁全部自造合成 payload；M-3 的锁用 `_clean_plan_payload`，N-3 的锁用合成 200×20 结构 |
| 未原地改历史 manifest / attempt | ✅ | 改动文件列表里**零** `run_20*` / `attempts/` / `manifest` 命中 |
| `stroke_dimension_consistency` 未升硬门 | ✅ | 本批 `src/` + `scripts/` diff 中该串命中数 = **0** |
| 未做批 D / 批 E / R1.5 | ✅ | 改动仅 4 个生产文件 + 4 个测试文件，全部对应 B-1/M-1/M-2/M-3/N-1/N-3 |
| 未动 `AI_agent/` 下除自己执行日志外的管理文档 | ✅ | `AI_agent/` 改动**只有** `logs/reviews/execution/2026-08-04_reading_ruler_batchC_glm.md` 一个文件 |
| 工作树里 `AI_agent/` 未提交改动**是 orchestrator 的** | ✅ 已按要求**不记到施工方头上**；且施工方 §7.6 明记「每个 commit 仅 `git add` 本条目文件、绝不 `-A`」，与我看到的 commit 内容一致 |

---

## 9. P-8 · 不变量 #6（复杂度可扩展性）—— **判断：`_fit_scale` 合格；三态 status 模型有一处将来要松动**

**`_fit_scale` ✅ 不会成为要推翻的假设。** 它是「结构画幅」的纯函数，没有烤死任何体量假设：
非方形 / 退台 / 挑空 / 中庭在每张视图上仍然只表现为一个 2D 包围盒，降档缩放对它们同样成立。
N-3 本身就是**拆掉**一条烤死的假设（「没有建筑单边超过 182 m」），方向正确。

**⚠️ 两处将来会硌到的地方（判断，不算 finding）**：

1. **`MAX_CANVAS_SIDE_PX` 现在同时当「像素上限」和「米上限」用**（`> 8192` 那个判断的单位是**米**）。
   这是个单位双关，目前数值上无害，但等有人要调像素预算时会踩。建议拆成两个命名常量。
2. **`empty` 是 attempt 级、不是 view 级**。将来一个 aggregate 里若出现「本层是挑空/竖井、这张视图合法地没有几何」，
   现模型会把它算成一条渲染成功的 view 还是让整个 attempt 变 `empty`？——
   目前是「只要有一张渲出来就 `complete`」，那张空视图**静默消失**。
   多 attempt 场景没问题（每个 attempt 独立算），**单 attempt 内的 per-view 空态是缺的**。
   建议在 view 记录里加 `status="empty"` 这一档，而不是等撞上再改语义。

---

## 10. 清单外自主发现 / 逐条 finding

### MAJOR X-1 · N-3 删掉了「像素化 dimension 端点」的最后一个探测器（**本批引入的回归**）
- **位置**：`scripts/tool_scripts/render_vector_to_png.py:107-126`（拒绝条件改为只看米制单边）
  + `scripts/tool_scripts/render_vector_to_png.py:65-80`（`_collect_points` 仍把 dimension 端点算进画幅）
  + `src/validator/checks/reading.py:319`（`_ocr_anchors_in_bounds` 只查 `ocr_texts`）
- **一句话失败场景**：读图器把一个尺寸标注端点写成像素坐标 ⇒ N-3 之前渲染器会 raise（3.3 亿像素签名），
  现在静默渲出降档垃圾图，而 gate① 对 dimension 端点从来没有 bounds 检查 ⇒ **坏数据零信号**。
- **证据**：见 §5.2 三行对照表（克隆 `d0e33ef` 实跑 raise / 主树 `57d47ea` 实跑 `6373×7845` / gate① `blocking: []`）。

### MAJOR X-2 · M-3 的可信画幅由被测方自己写的字段决定
- **位置**：`src/validator/checks/reading.py:333`（`bounds = _image_bounds(view)`）·`:369 _image_bounds`
  ·`:405-417 _explicit_image_bounds` ·`src/agent/reading/schema.py:120`（`extra="allow"`）
- **一句话失败场景**：产品只要额外写一个像素化 dimension 端点、一条乱伸的 stroke、
  或一个未声明的 `image_bounds` extra 字段，就把可信画幅撑大到包住那个坏 anchor ⇒ **M-3 当场失效、不再阻断**。
- **证据**：§4.4 四行实测表（同一 `[360,450]`，`fail/blocking=True` → `pass/blocking=False`）。
- **公平登记**：`_image_bounds` 是既有代码；本批新增的是让它成为 BLOCK 决策的唯一依据。183 份真实产物里 0 份用 `image_bounds`。

### MINOR X-3 · `MAX_CANVAS_PIXELS` 零锁 + L-51 的 docstring 已经失真
- **位置**：`scripts/tool_scripts/render_vector_to_png.py:41, 82-93` ·`tests/test_render_vector_to_png.py:71-85, 119`
- **一句话失败场景**：把 `_fit_scale` 的 `total_fit` 项摘掉，**全仓受影响子集全绿**
  （neuter x1）—— 8000×8000 m 的结构会渲成 8192×8192 ≈ **6710 万像素、超出 5000 万预算**，没有任何锁会红。
- **附带**：`test_L51_over_budget_structural_canvas_is_refused_not_clamped` 的 docstring 仍写
  *"a STRUCTURAL canvas that genuinely exceeds the **pixel budget** is REFUSED"*，
  但它的 20000 m 夹具现在触发的是**米制单边帽**，与像素预算无关 ⇒
  **「声称在守其实没守」第 7 次**（这次是 docstring 与实际触发路径脱钩）。
  L-53 第 119 行虽有 `<= MAX_CANVAS_PIXELS` 断言，但其夹具只有 7.6 M px ⇒ **该断言恒真、零约束力**。

### MINOR X-4 · 刚 merge 完、零渲染的 run 照样批得过
- **位置**：`scripts/tool_scripts/spawn_isolated_reader.py:55-60`（merge 路径**不调用任何渲染**）
  + `scripts/tool_scripts/run_stage.py:2329`（只有 `unavailable` 阻断）
- **一句话失败场景**：隔离 merge 落 attempt ⇒ 没有 `render_manifest.json` ⇒ 状态 `missing` ⇒
  **`approve-review` 直接放行一个一张图都没有的 run**（实测：真实历史 run，0 张 PNG，`✓ review approved`）。
- **定性**：这是施工方 §「缺口/披露」主动披露、轻门 §2 裁定二**已采纳**的权衡，
  **不算隐藏缺陷**。但采纳理由写的是「pre-O-1 的历史 run」，而实际覆盖面是
  **每一个新的隔离 run，直到有人跑了别的 verb 才渲染** —— 这一点值得让 orchestrator 知道后重新确认一次。
- **可行出口（零成本、不断 pre-O-1）**：run manifest 里已有 `artifact_contract == "reading_isolated_v2"`
  与 attempt 的 mtime，**「新 run 无 manifest」与「pre-O-1 run 无 manifest」本来就机器可分**；
  或更简单：`merge_isolated_output` 成功后直接调一次 `_finalize_reading_renders`。

### MINOR X-5 · 两处新分支零锁
- **a**（`run_stage.py:2331-2340`）：M-1 新加的「把 manifest 的 `error` 当机器可读原因surface 到
  approve-review 报错文案」整段删掉 ⇒ **全绿**（neuter x3）。
  现有锁只 `match="review blocked"`，**没断言那条 reason 真的被 surface 出来** —— M-1 的核心卖点无锁。
- **b**（`run_stage.py:817-819`）：`_reading_render_status` 的「manifest 本身读不出 ⇒ `unavailable`」
  改成 `missing` ⇒ **全绿**（neuter x4）。**失败场景**：`render_manifest.json` 被截断/损坏 ⇒
  一个渲染状态未知的 run 从「阻断」静默变成「放行」。这是 O-1 遗留、非本批新增，但 N-1 的正文
  就是「missing 与真失败必须可区分」，这条分支正是那个区分的守门人。

### NIT X-6 · stage-root 陈旧 `_render.png` 无人清理
`_render_stage` 的 0_reading 分支不再写 `0_reading/<stem>_render.png`，但**也不清理**。
真实历史 run 里那两张 pre-O-1 的 PNG 仍在原地、**不进任何 `render_manifest.json`** ⇒
人打开 stage 目录看到的可能是上一轮的旧图。非阻断。

### NIT X-7 · 环境坑（**我自己犯的错，如实登记 —— 且我第一版报告把病因写错了，此处更正**）

**现象**：我的探针克隆 HEAD 是 **`d0e33ef`，落后 6 个 commit**（主仓 HEAD 是 `57d47ea`）。

**我第一版把它写成「`git clone --local` 会取到落后的 HEAD」—— 这是错的，已更正。真因是**：

```
$ git clone --local --no-hardlinks /workspaces/EnergyPlus-Agent-dev <probe> 2>&1 | tail -3
fatal: destination path '<probe>' already exists and is not an empty directory.
$ echo "pipeline rc=$?"
pipeline rc=0                    ← ⛔ 管道把 clone 的非零退出码吃掉了
```

**⇒ 两条独立的坑叠在一起**：
1. 该路径下**已存在上一轮交叉审会话留下的克隆**（文件时间戳 03:41–03:51，正是上一轮我自己的探针脚本），
   `git clone` 因此直接 `fatal` 拒绝执行；
2. **`cmd 2>&1 | tail -N` 会把 `cmd` 的退出码换成 `tail` 的退出码** ⇒ 后台任务回执显示
   **"completed (exit code 0)"**，而实际上克隆根本没发生。

**⇒ 我是在旧克隆上开的工，并且回执告诉我一切正常。** 我是靠「顺手 `git log` 核一眼 HEAD」才发现的，
**不是靠任何机制**。这与本项目已栽多次的「哨兵判据不可靠 / 探针≠锁」同族：
**回执说成功，不等于那件事发生了。**

**对本轮结论的影响 = 无**（如实说明依据，不是自我开脱）：
发现后我 `git fetch && git checkout 57d47ea` 并 `git rev-parse HEAD` 逐字核对；
此后每次 neuter 前 `git checkout -- .`、mutator 自带 `assert count==1`、
改动为空即判结果作废、跑完复原并核 `git diff` 干净；克隆基线（1 环境红 + 338 passed）
也是在同一棵树上测的，因此对照有效。克隆里残留的上一轮 `.py`/`.sh` 探针脚本在**仓库根**、
不在 `tests/` 下，且我每次 pytest 都显式指定测试文件路径 ⇒ 不参与收集、不影响结果。

**⇒ 建议写进纪律（与已登记的 `PYTHONPATH=$PWD` 并列）**：
1. 克隆一律先 `rm -rf <probe>`，且**克隆命令不许接管道**（要看输出就先落文件再 `tail`），
   否则失败会被静默成功；
2. 克隆后第一件事是 `git rev-parse HEAD` **与被审 SHA 逐字核对**，核不上即停。

---

## 11. ⭐ 证伪失败的尝试（按要求登记 —— 这些是对施工方的反向坐实）

| # | 我想证伪什么 | 怎么试的 | 结果 |
|---|---|---|---|
| 1 | 找一条真实路径让**健康 run 被反过来拒批** | 六条真实路径（flat flow ×2 / resample / 隔离聚合 / 历史 pre-O-1 / 错名） | **失败** —— 无一复现 |
| 2 | 让形状识别器**把真实 merge 产物的元数据 dict 误当 view** | 通读 `_load_isolated_views` + `_draw_reading` 两个唯一产出点 | **失败** —— 第三种形状在产品里不可达 |
| 3 | 找一条**产品可用输入写出错名却被接受**（P-6 挑战 N-2） | flat-flow 真 CLI 全部错名 + merge 双分支 | **失败** —— `view_manifest_coverage` 双向 BLOCK |
| 4 | 找 **M-3 误伤合法 metric annotation** | 全仓 246 个候选文件 ⇒ 183 个真实 view（31 个带 ocr）跑 `regression` | **失败** —— FAIL 数 = **0** |
| 5 | 找**假锁 / 连带** | 8 处主 neuter 逐字精确替换 | **失败** —— 每处恰好红其目标、零连带 |
| 6 | 破坏 **N-3 的小 case 逐字节不变** | 实测 10×8 m ⇒ `585×495`，`scale` 恰为 45 | **失败** —— 声称属实 |
| 7 | 在 M-3 / N-3 里找 **「clamp 后放行」** | 通读两处实现 | **失败** —— M-3 只 surface；N-3 只动 px/m、公制几何不动 |
| 8 | 让 **`empty` 阻断** 或让三态混淆 | 构造空 aggregate / 损坏 output / 逐图 raise / 无 manifest 四种输入 | **失败** —— 四态互斥、只有真失败阻断 |

**⇒ 与上轮同样的结论再次成立：施工方的锁没有问题。本轮两条 MAJOR 是「覆盖面 / 边界」问题，不是实现质量问题。**

---

## 12. 给 orchestrator 的处置建议

1. **批 C 不建议就此收口。** 先闭 X-1 + X-2，再解除「不得发布识图分数」的硬约束 ——
   否则等于承认尺子有洞还去发布结论。两条都是**窄修**（一条检查扩字段 + 一个不依赖产品字段的量级判据），
   不是重构。
2. **X-2 的出口不要下放给施工方猜。** 本项目已经因为「边界写窄就被实现得同样窄」栽过多次，
   而这条的两种做法（信产品几何 vs 信源图像素尺寸）后果相反。建议 orchestrator 直接给死骨架：
   **可信画幅只能来自先于本次运行就固定、且被评判方写不了的第二处记载**（`case_data` 源图尺寸 + 已冻结的图像指纹）。
3. **X-3 / X-5 三处零锁**顺手补（各一条断言即可），并把 L-51 那句失真的 docstring 改掉 ——
   「声称在守其实没守」这次是第 7 次，不要留着。
4. **X-4 请重新确认一次裁定**：轻门 §2 裁定二写的是「pre-O-1 历史 run 不阻断」，
   但实际覆盖面是「每个新隔离 run 在渲染发生前都不阻断」。若认可，请把覆盖面如实写进裁定原文。
5. **X-7 写进跑 neuter 的标准纪律**（与 `PYTHONPATH=$PWD` 并列）：
   **① 克隆前先 `rm -rf`，且克隆命令不许接管道**（`cmd | tail` 会把失败伪装成 exit 0，我本轮就被这样骗过）；
   **② 克隆后 `git rev-parse HEAD` 与被审 SHA 逐字核对，核不上即停。**
   这条是我自己踩的，与本项目「哨兵判据不得用文件非空」「探针≠锁」同族 —— **回执说成功 ≠ 那件事发生了**。

---

## 13. 独立全量尾部原文（主工作树，`pytest -q -n 4`，⛔ 无 `-m`）

```
tests/test_run_stage_flow.py::test_v1_run_resumable_after_explicit_migration
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:2140: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-6088/popen-gw1/test_v1_run_resumable_after_ex0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2117 passed, 10 xfailed, 177 warnings in 595.94s (0:09:55)
```

**克隆基线尾部原文**（`/tmp` 克隆 @ `57d47ea`，`PYTHONPATH=$PWD`，受影响五文件）：

```
FAILED tests/test_checks_reading_correction.py::test_partition_on_window_jamb_real_restore_reading_r2_flags_four
1 failed, 338 passed, 14 warnings in 13.82s
```
（唯一红 = 环境红，`FileNotFoundError: AI_agent/logs/experiments/2026-06-30_reading_scaffold_restore_validation/readings/sonnet_r2/1f_view.json` —— gitignored 输入不在克隆里，与本批无关。）
