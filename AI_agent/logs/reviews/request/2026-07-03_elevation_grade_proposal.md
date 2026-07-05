# 立面判卷（elevation grade）设计简报

> 状态：**Claude 出方案，待用户 ratify → 派 Codex 审（方案类双审）**。
> 缘起：CLAUDE.md §2「下一步（用户 2026-07-03 改序）= 先设计立面判卷再做卷子」。
> 日期：2026-07-03。分支 `6.15_ValidationArchM0toM4`。

---

## 0. 一句话

现在的判卷只判**平面窗**（沿面 x 的次要源）、根本没判**权威的立面窗**（reader 在立面图上读出的 `sill/head`）。
拿它做 Sonnet 4.6 对照会**量错东西**。本方案设计立面判卷：per-image 立面识图窗 vs gt，在**(沿面 metre, 竖向 z) 的图自身自然坐标**里逐窗对账（沿面中心 + **sill/head**），绝不经 `derive_facade_frame` 世界解算。

---

## 1. 缺口实锤（为什么必须做）

> **勘误（2026-07-03，数据诚实）**：本节初稿举了一个"South F1 窗 S7 竖向读错 1.5/2.1 vs gt 1.0/2.6"的例子——**该例子是错的、已删**。核 gt 时我只读了 entry 级默认 `sill_m/head_m=1.0/2.6`，没读 **per-opening**：gt South F1 的 x=3.44 那扇小窗 per-opening 就是 `sill=1.5/head=2.1`，reader 的 S7 **读对了**。逐窗复核（脚本对 15 扇立面窗 vs gt per-opening）：**本 run 的 reader sill/head 全部正确**，含正确区分同层不同窗的高度（S7 的 1.5/2.1 vs 邻窗 1.0/2.6）。本 run **没有真的竖向识图错**。

**缺口是结构性的，不依赖"这次抓到一个错"**——三条硬事实（读码坐实）：

1. `reading_score.py:372` — scorer 只处理 `image_kind in (None,"plan")`，**立面 view 被直接 skip**。立面识图窗（唯一带 reader 竖向信息 sill/head 的源）**从未进判卷**。
2. `render_grade.py:444` 的"立面 panel"是**竖向假判卷**：窗盒沿面 x 来自**平面** reading 的 `score["windows"][facade]`（次要源），而 sill/head 从 **gt 借来当参考高度**（docstring line 5 明说 "gt used only as a quiet reference for elevation window heights"）→ **reader 读的 sill/head 从没跟 gt 核对过，永远显示不出竖向错**。
3. `correction_score.py:253` — correction 窗只判 `span`（沿面），`CorrectedGeometry.Window.z=[sill,head]` **携带但被完全忽略**。

**为什么这个盲区危险（而不是"反正 reader 都读对了"）**：
- gt 的 per-window sill/head **真的会变**（South F1：一扇 1.5/2.1、两扇 1.0/2.6；F1 vs F2 = 1.0/2.6 vs 4.0/5.8）。一个偷懒套统一 sill/head 的 reader 会**读错且 100% 静默通过**——今天我们连"reader 有没有读对"都无法自动判定，只能手写脚本临时核（如本次勘误所为）。
- 拿它做 **Sonnet 4.6 对照**：4.6 未必像本 run 的 reader 一样把 sill/head 都读对，而我们**没有任何自动手段**能测到 → 会量错东西。这正是"先设计立面判卷再跑对照"的理由。

**顺带（本次逐窗复核实锤，直接约束设计）**：East 立面**两扇窗沿面 x 都=3.4、竖向叠放**（F1 z=[1.0,2.8]、F2 z=[4.0,5.8]）。⇒ **立面窗匹配绝不能只按沿面 x**，必须用 z/楼层消歧，否则把 F2 窗错配到 F1 gt（对应 §4/§3 的楼层归属与匹配谓词、Codex review MAJOR-2/3）。

⇒ 现判卷判的是"次要且竖向缺失"的平面窗；**权威立面窗的竖向维度是判卷盲区**。correction 全流程优先立面来源，拿平面判卷做模型对照 = 量错东西。

---

## 2. 设计原则（不变量对齐）

- **判卷永远"每张图 vs gt 这一片"，在图自己的自然坐标里。** 立面图的自然坐标 = **(沿面距离, 竖向高度 z)** 两维标量，纯 metric，不构造任何世界 (x,y) 点。
- **绝不调 `derive_facade_frame`。** 局部→世界是**拼装(modeling)**用的（`facade.py` docstring：world placement in 1_correction）。判卷若耦合它，一个 correction 的世界解算错（mirror/sign）会**冒充成识图错**——恰恰违背"gt 权威判卷、看错↔改错分离"。世界解算对不对是 correction 仲裁的事，不是识图准确度。
- **平面窗↔立面窗不一致 = correction 仲裁，不算识图错**（用户 2026-07-03 定）。所以两套窗**各自 vs gt** 判，判卷不做两者互判。
- **不变量 #6 接缝（诚实口径，勿吹过头）**：v1 **只支持 cardinal 矩形**——当前 gt/代码烤着 cardinal 假设（`derive_gt_windows` 把 `x_m` 记为 world-x(N/S)/world-y(E/W)、`render_grade._facade_span_limit` 取 `W_m`/`D_m`）。本设计**不是已经 skew/退台/非方形安全**。它守 #6 的方式是**保留接缝、不烤死不可松动的假设**：判卷在"沿面距离 + 绝对 z"里做、**不构造世界点、不调 `derive_facade_frame`**——所以升级到 #6 = 给 gt 加 facade 元数据（facade id / 沿面长 / 面内 opening 坐标系 or 段 polyline）+ 泛化 `span_limit`，**非重架构**。这才是 #6 要的"留路"，不是"已经能跑斜立面"。（Codex review MAJOR-4）

---

## 3. 坐标模型 + 楼层归属（世界无关）

**gt 权威立面窗**（已在 `gt.json`）：每 opening `{x_m, width_m, sill_m, head_m}`。gt 的 `x_m` = 沿面坐标（N/S 记为 world-x、E/W 记为 world-y，即"从该面 0-端起的沿面距离"）。这就是我们的**参考 local frame**（原点 = 面的 0-端，方向 = +沿面）。

**reading 立面窗**（立面 `*_view.json` 的 `pen=window` stroke）：
- `geometry.x_range_m` = 沿面跨 `[a0,a1]`
- `geometry.y_range_m` = `[sill, head]` **绝对 z**（实测坐实，见 §1）

**correction 立面窗**（`CorrectedGeometry.windows[]`）：`{facade, floor, span:[a0,a1], z:[sill,head]}`。

**楼层归属 = match-first（不做硬 z-band 预分桶，Codex MAJOR-3）**：
- **reading**：per facade 把每扇 reading 窗**先对全部 gt openings 做 z-aware 匹配**（沿面 + z 都进 cost），**楼层从匹配到的 gt opening 反取**。z-中心 band 只用于**未匹配的 extra 归类 + 报告**，且 band 用**半开** `[z_floor, next_z_floor)`、顶层含上界（避免 z=3.0 边界窗、读偏 sill 落错层这类噪声）。
- **correction**：楼层身份用 **`Window.floor` 经现有 floor_map**（`correction_score._map_floors`）当主键，`Window.z` 只作**绝对 z 对账**——**不**按 correction 自己（可能错）的 z 重新分桶。
- facade 归属：reading = 该立面文件声明的 `facade.view_facade`；correction = `Window.facade`。一图一面。

**per-opening sill/head 是权威（Codex MAJOR-1）**：scorer 取 `opening.sill_m/opening.head_m`，**仅** legacy 无 per-opening 数据时才回退 entry 级 `sill_m/head_m`。（本次勘误根因：我误用了 entry 默认。`tests/test_gt_from_dxf.py` 已断言 South/F1 小窗有独立抬高 sill/head → 加回归：该窗判为 **z hit**。）

**gt `x_m` 口径**：v1 视 gt `x_m` 为**已归一到 facade-local 沿面距离**（cardinal 矩形下 = world-x(N/S)/world-y(E/W)）；scorer 另加一道**沿面锚定 sanity**：reading 立面 `x_range_m` 须是 metric 且落在 `[0, span_limit]` 附近（用 wall_fill/envelope 描边或 dimension 佐证）——A1 反射只解方向、不解任意 origin/scale（Codex MAJOR-4）。

---

## 4. 翻转/朝向处理 = A1 翻转鲁棒（定稿算法，Codex MAJOR-5）

**背景**：P1b 立面 reading 是 image-local（原点/方向任意）；本 run Sonnet 靠 testdata 锚定四面沿面直接命中 gt、**无翻转**，但弱 reader/未锚定会 image-local 与 gt 沿面**反向**（尤 North：从外看左=东、gt 按 world-x 从西端计）。

**定稿算法（精确、避免逐窗被翻转救回）**：
1. **区间反射要整段翻**：`[a0,a1] → [span_limit−a1, span_limit−a0]`（**反射后重排端点**，绝不独立翻端点否则区间倒挂）。
2. **orientation 每 facade/view 选一次**（跨该面所有楼层一起定），**不逐窗选**。
3. **确定性择优**：对 `aligned` 与 `flipped` 各算一遍全面匹配，按 `(最大化 placed_hit → 最大化 matched → 最小化归一 cost)` 择优；**平票偏 `aligned`**；分数相等/接近 → 报 `orientation=ambiguous`。
4. flipped 命中在 **reading grade** = reconcile 信号（correction 仲裁料）、**不当逐窗 miss 扣分**；竖向 z 绝对、**不翻转**。

**correction 侧 A1 收紧（关键）**：`CorrectedGeometry.Window.span` **已是世界系沿面 span**——correction 若翻转就是**建模镜像了、真错**。故 correction grade **默认按 aligned 判**，翻转只在有独立朝向佐证时才提示，**绝不像 reading 那样把翻转当良性豁免**。

---

## 5. 匹配 vs 准确度语义（定稿谓词，Codex MAJOR-2）

现有"两把独立尺 vs 同一 gt"（reading grade + correction grade）。**先关联、再判准，四态分明、不重复计数**：

1. **候选关联（candidate）**：facade + 归一 orientation 下，`|read_along_center − gt_along_center| ≤ elevation_along_tol_m` **且**一道松竖向 sanity（z 区间相交 或 同/邻层 band + 边界 slack）。
2. **placed_hit**：候选对的 `along_center`、`sill`、`head`（宜含 width/edge）**全部**各自在容差内。
3. **matched_with_z_drift**：候选对但 z 超容差 → 计为 **"关联上但没放准"**（`elevation_windows_placed` 记不合格），**但不**同时当 gt miss + read extra **双计**。
4. **miss**：某 gt opening 无候选。**extra**：某 read 窗未关联到任何 gt。

**sidecar 同时暴露 `matched_total` 与 `placed_hit_total`** + 每窗 `along/sill/head(/width) delta` + `status ∈ {placed_hit, matched_with_z_drift, miss(gt侧), extra(read侧)}` + `orientation`。

**报告字段**：along-center delta、**sill delta / head delta（新增·真正填 gap 的一维）**、width delta（默认 reported-only）、facade×floor 计数。

**两卷各自的 gt-盲性**：reading grade 是**准确度真闸门**（reader 直接对 gt，别让它更松，否则静默缺口后移无解）；correction grade 吃 `CorrectedGeometry.windows.z`，判结构操作后净效果。默认两把尺相等。

---

## 6. judge evidence（advisory，绝不进 StageVerdict）

`score_policy.py` 新增 advisory criterion **`elevation_windows_placed`**（沿面+竖向），**仅从 sidecar 的 elevation 段派生**（不掺 plane 段），`suggested_status ∈ {pass, minor, severe}`（miss/z-drift 计不合格、within-tol 淡化）。
`extra="forbid"` 纪律不破：**只作机读 evidence 喂 judge_packet，绝不写 `StageVerdict`、不替 checklist**（StageVerdict 仍是裁决权威）。**守 gt 红线**：新 criterion 及其数据源全 judge-side；gate①/pipeline/execution/correction 不得 import——**gate 一旦碰 gt 就是拿答案关门、judge 撤了 gate 就泄题**。

---

## 7. 卷子（renderer·real 立面 panel 替换假 panel）

现 `render_grade.py:444` 的假立面 panel（平面窗沿面 + gt 借高）**替换为真立面判卷**，**严格 sidecar-driven 只读、绝不重算/回查窗高**（Codex MAJOR-7）：

- **sidecar 每条立面 match 自带完整盒**：`truth.span/truth.z`、`read.span/read.z`、各 delta、`status`、源 stroke/window id、floor、facade、`orientation`。renderer **只**能拿 gt 画**建筑外轮廓 + 楼层线**，**窗高一律来自 sidecar 的 `read.z`/`truth.z`**，不再 `_window_meta` 借 gt 高。
- 视觉语言沿用：gt opening = 真值盒（灰真值丝）；窗 **placed_hit 绿实框 / matched_with_z_drift 沿面对但 sill/head 超容差 = 竖向漂移标注（read 盒实 + gt 盒丝 + 竖向 delta）/ miss 红虚框+淡红填充 / extra 红实框**；sill/head 在容差内漂移 → 淡绿竖向容差带 + 灰真值线（补齐现只有沿面 drift 带）。
- 画布 = (沿面, z)，每 facade 一 panel。**立面 sidecar 段缺失 → 画 "no elevation score"，绝不回退旧假 panel**。
- **平面 panel 保留**平面窗沿面车道，**明确标注 "plan-derived (secondary)"**，与权威立面 panel 区分。

---

## 8. 配置 / 容差（`grade:` 段，run-scoped，两把尺）

`<run>/run_config.yaml` 的 `grade:` 段（7.03 Batch1 已建）增补立面容差：
```yaml
grade:
  reading:   { wall_tol_m: 0.30, window_centre_tol_m: 0.40,
               elevation_along_tol_m: 0.40, sill_tol_m: 0.30, head_tol_m: 0.30 }
  correction:{ ... 同结构 ... }
```
- 独立于 `correction.yaml`（那是确定性核坍缩生产尺，另一回事）。
- **end-to-end 线程化（Codex MINOR-10）**：`GradeConfig` 加三容差 + `GradeConfig.as_tolerances()` 序列化 → 进 `score_vs_gt.json` sidecar `tolerances`（严格复用键，改容差不复用旧分）→ scorer + policy 都读它 → `run_config.yaml` 解析测试更新 → **`SCORER_SCHEMA` 递增**（老 sidecar 不得当成含权威立面分渲染）。
- `width` 容差：本轮**默认 reported-only**（不 gate），预留字段。

---

## 9. 交付物 + 接线点（file:line）

| # | 交付 | 位置 |
|---|---|---|
| 1 | **新** `ElevationWindowMatch` + per-facade 结果 dataclass + 匹配/翻转/语义（**独立结构，不塞进 `FloorScore.windows`**，Codex MAJOR-6）| **新** `src/agent/judge/elevation_score.py` |
| 2 | 立面窗**专用抽取器**（吃 `pen=window` rect 的完整 `x_range_m/y_range_m`、留 stroke id、坏形状报 evidence；**不复用** `_as_segment`——它把 rect 压中线会抹掉 z，Codex MINOR-11；legacy 无 z 的 line 窗 → no-data/extra 不伪造 z）| `elevation_score.py`（reading 侧）|
| 3 | correction 侧立面判：`Window.floor`(经 floor_map)+`Window.z` 绝对对账、A1 收紧 | `correction_score.py`（新增段，`FloorScore` plane 段不动）|
| 4 | sidecar 顶层新段 `elevation`（与 plane `scores` 并列）+ advisory `elevation_windows_placed`（仅从该段派生）| `score_policy.py` + sidecar writer |
| 5 | real 立面 panel（sidecar-driven，完整盒）| `render_grade.py:444`（`_draw_elevation_panel`）|
| 6 | flow 产立面 score → judge_packet（绑 accepted `output_hash`、篡改 fail-closed）| `run_stage.py`（沿 Batch B `_judge_gt_artifacts` 口径）|
| 7 | `grade:` 立面容差 end-to-end + `SCORER_SCHEMA` bump | `run_config.yaml` schema + `GradeConfig` + sidecar tolerances |
| 8 | 测试：per-opening z 权威(S7=hit) / 匹配四态语义 / East 叠窗 z 消歧 / 翻转整段反射+per-facade / zero-window(West F1)≠no-data / **advisory 不进 StageVerdict** / **`test_gt_discipline` 仍绿 + 扩到新 scorer** | `tests/` |

**gt 隔离铁律不破（红线）**：全部 judge-side（读 gt），gate①(`validator/checks`)/pipeline/execution/correction **零 import**；`test_gt_discipline` 必须仍绿、并把新 `elevation_score.py` 纳入"仅 judge-side"守护。**gate 有 gt = 拿答案关门；judge 可撤，gate 撤不掉——所以答案只能待在可撤的 judge 侧。**

---

## 10. 非目标 / 边界 / 空数据语义

- **不**世界解算、**不**碰 `derive_facade_frame`、**不**改 reading/correction schema 契约、**不**进 StageVerdict、**不**碰 gate①。
- 平面判卷**保留**（平面窗仍作次要源判、明确标注 "plan-derived / secondary"）。
- **zero-window vs no-data 必须分清（Codex MINOR-9）**：每个 facade×floor 组合都显式发 `matches=[]`/`extras=[]`（含 gt count=0，如 **West/Floor 1**）。**gt 空 + read 无窗 = pass；gt 空 + read 有窗 = extra；sidecar/facade/view 缺失 = no-data**（非 pass）。保 `test_render_grade_empty_facade_is_not_no_data` 的既有区分。
- backlog（本轮不做）：立面楼板线/屋顶/地面判定保持灰（沿 BoundaryGrading 口径）；沿面宽度单列 criterion；#6 skew/非方形（需 gt 加 facade 元数据）。
- 做完立面判卷 →（另轮）Sonnet 4.6 干净流程对照。

---

## 11. 决策点（用户 2026-07-03 已 ratify）

- **决策点 A（朝向）= A1 翻转鲁棒**：试恒等 + 关于面中心反射两种，取匹配更好者，报告 `orientation=aligned|flipped`；flipped 命中作 reconcile 信号、不当逐窗 miss 扣分；竖向 z 绝对不翻转。
- **决策点 B（范围）= reading + correction 两卷都上竖向判定**：两把独立尺各自 vs gt。correction 侧 `correction_score.py` 补 `Window.z=[sill,head]` 判定（现成携带、被忽略）。
- **决策点 C = 平面窗判卷保留**，明确标注 "secondary / plan-derived"，与权威立面 panel 并列。

## 12. Codex 方案审裁决（2026-07-03）

Codex review = **APPROVE-WITH-CHANGES，11 findings，Claude 全采纳**（`logs/review/review/2026-07-03_elevation_grade_review.md`）。已折进上文：
- MAJOR-1 假 S7 例（§1 勘误，per-opening z 权威）· MAJOR-2 四态匹配语义（§5）· MAJOR-3 match-first 楼层归属（§3）· MAJOR-4 #6 诚实收口（§2）· MAJOR-5 翻转整段反射+per-facade+correction 收紧（§4）· MAJOR-6 独立结构不塞 FloorScore（§9#1）· MAJOR-7 renderer 完整盒 sidecar-driven（§7）。
- MINOR-8 advisory/gt 守护测试（§9#8）· MINOR-9 zero-window 语义（§10）· MINOR-10 容差 end-to-end + schema bump（§8）· MINOR-11 立面专用抽取器（§9#2）。

两条属**数据诚实**（MAJOR-1/4）是我方案自身的错，已据实改，不是实现细节。

⇒ **本简报即定稿（implementation-ready）**。下一步：派 Codex 执行（分批，medium/high）→ Claude 大节点全面审（自跑 pytest + 逐行 diff + 真图核对 + `test_gt_discipline` 绿）。
