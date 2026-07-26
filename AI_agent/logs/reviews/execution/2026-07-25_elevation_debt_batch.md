# 2026-07-25 立面批「六笔债」执行简报（Claude 侧 Opus 执行档子代理）

- 派工单：`AI_agent/logs/reviews/request/2026-07-25_elevation_debt_batch_dispatch.md`
- 中途主控纠正指令两条（均已执行，见 §7）：① WI-5d 暂停→后解锁 ② 新增 WI-5e
- 基线：`e13efd3`，全仓 1556 passed / 10 xfailed
- 本轮不 commit、不 push；工作区交付

---

## 0.0 全仓回归

```
python -m pytest -q -p no:cacheprovider
→ 1580 passed, 10 xfailed, 148 warnings in 498.52s (0:08:18)      ← FIX-4/FIX-5 返工后终态
```
基线 `1556 passed, 10 xfailed` → **+24 passed、xfailed 不变、failed 0、无新 skip**。零回归。
（演进：首轮 1577 → FIX-1 锚点锁 1578 → FIX-3 审计列锁 1579 → FIX-4 sm21 TYPE 1 逐像素锁 1580。）

**最终交付 hash**（FIX-4/FIX-5 后重生成）
- candidate GT `content_sha256`：`e6f112abcecb56475b3d614acfcd59e49e55bee2ab744d56e4e8a7b658fdf89e`
- manifest `manifest_sha256`：`bed652dfd6b320de6126128095dbc5913e624236b3d9460154cf023f4d6f680f`
- review-index `inventory_sha256`：`5675fa6d4e213d4035b505bb90ed22e778aa8888651e2beb77f32e2782783474`

⚠️ 过程纪律注记：本轮曾有一次全量跑与 neuter 探针**并发**（与 07-24 那次同款污染），该次结果**已作废**；上面这条是 neuter 全部还原、`diff -q` 确认工作区干净之后**重新干净单跑**的结果。

收尾自检（均已执行）：`if False:` / NEUTER 残留 0；禁区（`case_tests/`、`gt_sources/`、`correction_score.py`、Va/Vg）改动 0；`render_gt_overlay.py` diff 中投影函数**只有调用点变化、无 `def` 体与 affine 系数改动**；三个改动文件 `ast.parse` 通过。

---

## 0. 一句话结论

WI-1 / WI-2（§9.3 + §6.6）/ WI-3 / WI-4 / WI-5 / WI-6 **完成**；**WI-2 的 §9.2 frame/title 六格未做**（诚实标注，见 §8）。
12 条新锁全部 neuter 自证为真锁——**其中 1 条我自己写的锁被自查抓出是假锁并已重做**（§4）。
另发现 **3 个派工单之外的问题**（1 个可能需要主控拍板），见 §6。

---

## 1. WI-1 — §6.5 converter ↔ GT 配对一致性 postcheck（完成）

**改了什么**

| 文件 | 位置 | 改动 |
|---|---|---|
| `src/agent/judge/tarch_normalize.py` | 新增 `_PAIRING_Z_TOLERANCE_M` / `_converter_elevation_z` / `_verify_pairing_consistency` | §6.5 postcheck 本体 |
| 同上 | `_run_g9_v3_preflight` | 返回值 2-tuple → 3-tuple，**把 `extract_gt_v3` 的 GT 交出来**（原来丢弃 = 死码根源） |
| 同上 | `run_p2_conversion` G9 段 | G9 绿之后跑 postcheck；漂移 → `g9_ok=False` + emit `tarch_elevation_pairing_drift` |
| 同上 | `build_p2_report` 审计行 | z 改为调用同一个 `_converter_elevation_z` |
| 4 处测试 | `ok, code = …` → `ok, code, _document = …` | 纯机械解包，断言一字未改 |

**为什么这么做**：审计表 z（request affine）与 GT z（manifest affine）是两条独立路径，此前无任何门强制其相等。现在**审计行和门比较的是同一次调用的结果**，人核签的数字就是门比过的数字。

**死码接上**：`tarch_elevation_pairing_drift` emit 引用数 0 → 1。

**z 容差选择理由**：取 **1e-9 m（1 纳米）**。
- 实测：sm24 全 14 个 opening 的 `|GT z − converter z|` **最大 0 .0（逐位相等）**。
- 两条路径代数恒等（manifest scale = request scale / mpu，GT 侧再乘回 mpu），唯一可能差异是浮点重结合噪声；sm24 量级（|z| ≤ 4 m）噪声约 1e-15。
- 1e-9 比量化步长（mm = 1e-3 m）**低 6 个数量级**（不可能吸收真实漂移），比噪声**高 6 个数量级**（不会误报）。
- 没有新造宽容差。

**postcheck 检查项**：generated handle 反查 → view id / kind / z interval 比对 + **每个 relevant pair 恰一组 refs**（0 组=转换器证据无人消费；≥2 组=一份证据被多个 opening 认领）。

**守卫**：postcheck 只在 `elevation_bound`（manifest 真带 elevation binding）时跑。这是我自己的测试抓出来的——E0–E4 已 BLOCK 时 manifest 无立面绑定，跑 postcheck 只会为已报告的失败再造一条次生诊断（违反本文件既有的「入口屏障不制造次生诊断」纪律）。

---

## 2. 上批 §11 row 10 订正

上批简报（`execution/2026-07-24_elevation_construction_terra.md`）§11 row 10 写「GT refs 与 converter ledger 一致 | G9 / audit 实测通过」。

**订正**：该对账项在本批之前**无任何门支撑**——审计行由 ledger 自身构建（无法自证与 GT 一致），而 G9 丢弃了 `extract_gt_v3` 的返回值。当时二者事实上一致（同源），但那是巧合性一致，不是被强制的一致。**自 本批起由 §6.5 postcheck 支撑**（4 条锁，见 §4）。历史简报是过程痕迹，不改写。

---

## 3. WI-2 — 必红夹具与正向 e2e

### 3.1 §9.3 z 组（7 类，全部落地）

| # | 变异 | 归属门 | 夹具 |
|---|---|---|---|
| 1 | datum 换成另一条水平线（屋顶线类） | G1 `z_transform_mismatch` / `along_direction_mismatch` | `test_z_datum_swapped_to_another_line_makes_g1_red` |
| 2 | datum source axis 与 z axis 不符 | G1 `z_transform_mismatch` | `test_z_transform_mutations_make_g1_red[axis_mismatch]` |
| 3 | z scale 0.001 → 1.0 | 同上 | `[scale_unit]` |
| 4 | offset 平移 0.2 m | 同上 | `[offset_shift]` |
| 5 | **两个 datum 推出不同 offset** | 同上 | `test_two_datums_deriving_different_offsets_make_g1_red` |
| 6 | 窗框跨楼层 | G9（extractor `elevation_opening_floor_ambiguous` 原码上浮） | `test_window_z_outside_its_floor_blocks_g9[crosses_floor_top]` |
| 7 | 窗 z 高于 ceiling | 同上 | `[above_ceiling]` |

**⚠️ 第 5 格暴露并修掉一个真实缺口**：原实现只取 `view.floor_datums[0]`，**第二个 datum 是死输入**——声明两个互相矛盾的 datum，第一个静默胜出。已改为**遍历校验全部 `floor_datums`**，任一不一致即 BLOCK；记录仍取第一个。这是生产码语义修复，不是纯加测试。

**第 5 格的覆盖边界（如实说明，供 GLM 复验）**：sm24 是**单层** anchor，而 schema `_v3_contract` 要求 `sorted(datum.floor_id) == floor_ids`，故「同一层两个 datum」在**签名请求加载时就会被 schema 拒**；我的夹具是用 `model_copy`（不重跑校验器）构造出这个对象直接喂转换器的。
⇒ 这道门**真正不可替代的价值在多层视图**：F1/F2 各一个 datum 是 schema 合法的，但两者可以推出**不同的 offset**，schema 完全看不见，只有这个循环能抓。neuter 自证（改回 `[:1]` → 锁翻红）证明抓它的确实是这个循环、不是 schema。多层 fixture 在 sm24 上造不出来（无 2F），未补。

**诚实标注（第 6/7 格）**：这两格由 extractor 的楼层包含性检查拥有（同一道门），经 `tarch_v3_precondition.context.v3_code` 上浮，转换器侧没有独立码。两条是不同变异、同一道门，不是两道门。

### 3.2 §6.6 sm24 正向 e2e（10 条全落）

`test_sm24_forward_e2e_post_conditions`：1 plan + 4 elevation / 四 facade projection key 落在正确 facade 的 segment / `len(openings)==14` / 11 window z 全非空 / window z 恰 {[1.0,2.8],[1.0,3.4]} / 3 门 observed z=[0.2,2.6] 且 `> z_floor`（排除 floor default 生成）/ `11C` 非 structural + 唯一 structural outline / 每 opening 有 plan ref 且有 elevation ref / 7 个 interior door 不在 GT / canonical reload 逐字节一致。

**合同硬约束遵守**：生产码没有任何 `if len(openings)==14` 类分支（数字只在测试里）。

### 3.3 §9.2 frame / title 六格 —— **未做**

见 §8 诚实交接。

---

## 4. §9 必红自查表（neuter 自证，逐格）

方法：把目标门判定逻辑改坏 → 跑该锁 → 必须由绿翻红 → 从安全副本还原（**不用 `git checkout`**，本轮改动未提交）。
harness：`/tmp/.../scratchpad/neuter.py`；还原后三个文件与副本 `diff -q` 全一致，`if False:` 残留 0。

| # | 我 neuter 了什么（文件 : 改成什么） | 跑了哪个测试 | 结果 |
|---|---|---|---|
| 1 | `tarch_normalize.py` z 比较条件 → `if False:` | `test_gt_side_z_drift_makes_g9_pairing_red` | 绿→**红** ✓ |
| 2 | `tarch_normalize.py` `if count != 1:` → `if False:` | `test_relevant_pair_without_exactly_one_ref_group_is_pairing_drift` | 绿→**红** ✓ |
| 3 | `tarch_normalize.py` `if opening.kind != rec.kind:` → `if False:` | `test_ledger_kind_and_view_id_drift_are_pairing_drift` | 绿→**红** ✓ |
| 4 | `tarch_normalize.py` postcheck 调用 → `pairing_drift = []`（拆接线） | `test_gt_side_z_drift_makes_g9_pairing_red` | 绿→**红** ✓ |
| 5 | `tarch_normalize.py` `for candidate in view.floor_datums:` → `[:1]`（退回旧行为） | `test_two_datums_deriving_different_offsets_make_g1_red` | 绿→**红** ✓ |
| 6 | `tarch_normalize.py` datum 复合判定 → `if False:` | `test_z_transform_mutations_make_g1_red` | 绿→**红** ✓ |
| 7 | `tarch_normalize.py` 墙厚证据守卫两行 → `pass` | `test_wall_thickness_is_none_without_complete_evidence` | 绿→**红** ✓ |
| 8 | `gt_extraction.py` `wall_thickness_m=thickness_by_floor.get(...)` → `None` | `test_sm24_boundary_segments_carry_evidenced_wall_thickness` | 绿→**红** ✓ |
| 9 | `render_gt_overlay.py` `_outline` 体 → `draw.rectangle(...)` + `return` | `test_v3_outline_edges_are_equal_width_and_dashing_leaves_gaps` | 绿→**红** ✓（**重做后**，见下） |
| 10 | `render_gt_overlay.py` `_review_base` → 退回 `enhance(DIM)` | `test_v3_review_base_keeps_drawing_ink_readable_and_hue_free` | 绿→**红** ✓ |
| 11 | `render_gt_overlay.py` `_weights` → 返回固定常数 `{3,7,3,14}` | `test_v3_stroke_weights_scale_with_raster...` | 绿→**红** ✓ |
| 12 | `render_gt_overlay.py` `DIM = 0.38` → `0.40` | `test_sm21_legacy_overlay_pipeline_is_unchanged` | 绿→**红** ✓ |

### ⚠️ 自查抓出我自己的一条假锁（已重做）

第 9 格**第一版是假锁**：原测试断言「`_outline` 上下边等宽 == 4」，我 neuter 成 `draw.rectangle` 后**仍然绿**。
追查原因：**派工单 WI-5c 的前提在本环境不成立**——实测 Pillow 12.2.0 下 `ImageDraw.rectangle(..., width=w)` **四条边都是全宽**（width=1/3/4/5 逐一验证，top=bottom=left=right=w）。所以「PIL 矩形底边只有 1px」不是本版本的事实，`_outline` 的存在理由不能是它。
**处置**：① 订正 `_outline` docstring（写明该前提已验证不成立）；② 把锁重写为**以虚线为承重断言**（`draw.rectangle` 根本不能画虚线），neuter 后由绿翻红 ✓；③ 测试 docstring 明写「等宽那半是 `_outline` 的行为锁，不是修复 PIL bug 的证明」。

---

## 5. WI-3 / WI-4 / WI-5 / WI-6

### WI-3 登记面与鲁棒性清理

1. **四个死码（MINOR-1）→ 选「保留 + 文档化 + 加锁」，不删。理由**：
   - P0 契约冻结，`DiagCode` Literal 收窄是契约变更（上一轮已因「P1/P2 破坏 P0 冻结」吃过 MAJOR）；
   - 三个 G9 码的不 emit 是 §6.4 的**设计**：extraction 失败必须原码经 `tarch_v3_precondition.context.v3_code` 上浮，重新拼写成转换器码正是让两套词汇静默漂移的路子；
   - 删掉会丢失「转换器词汇 ↔ extractor 原码」的对应记录。
   **落地**：注册表加说明性注释块 + 新增 `test_declared_not_emitted_elevation_codes_stay_unemitted`——既扫源码证明无 emit，又用真实条件（along 位移 5 m）跑通道，断言 `v3_code == "elevation_opening_no_candidate"` 且四个码一个都没出现。
2. **宽 except（MINOR-2）**：`_run_g9_v3_preflight` 的 `except Exception` 窄化为 `(ExtractionError, GtValidationError, PydanticValidationError)`。真 coding bug 现在会炸出来。
3. **前置 `extract_gt_v3` 未包裹（MINOR-2）**：已包 try → BLOCK（`stage: elevation_plan_prepass`）。
   **未做去重，理由**：前置那次用的是 **plan-only manifest**（立面绑定尚不存在，是它自己的产物），G9 那次用的是**完整 manifest**——两次输入不同，不是同一次调用的重复。要去重就得倒转门序，派工单明确禁止。已在代码注释写明。
4. **NIT-1 docstring**：镜像测试 docstring 订正为「由 elevation `residual_ok` 拥有；directed 手性面由 lo/hi swap 那条覆盖」。
5. **NIT-2 死分支**：`gt_extraction.py` `item is None` 已删。
   **副作用（如实报告）**：删除后 `test_elevation_global_assignment_tie_fails_closed` 失败——该测试**直接传 `item=None`** 调 `_assign_elevation`。即该分支在生产路径确为死分支，但对那条测试是承重的。已把测试改为传真实 evidence binding（kind 匹配），测试意图（歧义配对 fail-closed）一字未变。

### WI-4 sm24 GT 墙厚（完成）

**证据链**（简报要求写清「0.24 从哪来」）：
`S2 量测的 jamb cap`（厚度证据种类 #2）→ `_ZoneEdgeRec.thickness_evidence` / `thickness_native` → 新增 `_outer_skin_thickness_m()` 只看 **basis == `outer_skin`** 的边 → manifest `default_wall_thickness_m` → `gt_extraction` 挂到 `GtBoundarySegmentV3.wall_thickness_m`。

实测：**12 条 outer_skin 边，全部 240.0 mm，全部带 `wall_cap_or_opening_jamb` 证据** → 0.24 m。（内墙 26 条 120 mm，不参与。）

**fail-closed**：只要 ① 无 outer_skin 边 ② 任一条缺证据 ③ 任两条不一致 —— 一律返回 `None`，不取平均、不填默认。负锁 `test_wall_thickness_is_none_without_complete_evidence` 三种情形全覆盖 + neuter 自证。

**影响面**：extractor 只是**搬运** manifest 声明值，自己不量、不兜底；manifest 没声明的（现有全部 v3 测试 fixture）保持 `None`，故零回归。sm21 走 v2 legacy 路径，未触碰。

### WI-5 出图（完成，含主控新增的 WI-5e）

**a. 底图（降级为次要，仍做）**：v3 分支改为**灰度 + ×0.75**，legacy 完全不走这条路。
量化判据：**原图墨迹（luma>40）平均亮度保留率 ≥ 0.6**，实测 **0.747**（legacy 乘法为 0.38，约 2.0×）。灰度还顺带解决了色相冲突——成图上任何饱和色都必然属于 gt。锁：`test_v3_review_base_keeps_drawing_ink_readable_and_hue_free`。

**b. 平面用途填充 + 标签**：半透明填充（alpha 70，对齐 sm21）+ `zone_id role` 文字。用途来自 **review-only 注记文件** `review_annotations.json`：不回写 gt.json（GT role 仍 `unspecified`）、不参与任何 gate、进 review-index inventory、未注记 zone 退中性灰。锁：`test_v3_review_annotations_are_review_only_and_never_guess`。**⚠️ zone↔用途有一处对不上，见 §6.1。**

**c. envelope 补底边**：改 `_outline` 四条显式边。**前提证伪见 §4**——真正价值是虚线能力。

**d. 校准精修（主控解锁后执行）**：见下。

**e. 叠加发糊（主控新增，最高优先）**：
- 线宽/字号**全部按图幅比例**（sm21 2133px 为基准）：`line=3·s, bar=9·s, box=5·s, font=20·s`。锁：`test_v3_stroke_weights_scale_with_raster...`。
- **字体：`ImageFont.load_default(size=N)` 在 Pillow 12.2 返回的已经是 FreeTypeFont（内嵌 Aileron），不是位图字体**（已实测）。且本环境 `/usr/share/fonts`、site-packages、仓库内**均无任何 TTF**（matplotlib 未安装），内嵌 Aileron 是唯一可依赖字体。⇒ 可做的是**字号随图幅 + 加深色描边（`stroke_width`）**，已落地；换字体无退路可换，如实说明。
- **占用问题（我独立诊断的主因）**：gt 用的 cyan 与图纸自身开口墨迹**同色**，且实心描边**盖住**了人核唯一要比对的那条线。⇒ 开口框改**虚线**，图纸自身的线从缝隙里透出来（见 `diag/crop_south_new_4x.png`：灰色细线连续穿过青色虚线，二者重合肉眼可判）。
- footprint envelope 改为**最后绘制**，避免被沿边的 zone 描边盖掉。

**sm21 legacy 逐像素不变的证明方式**：新增 `test_sm21_legacy_overlay_pipeline_is_unchanged`，把 `overlay_plan`×2 + `overlay_elev`×4 现场重渲，与**已锁定基线资产** `case_tests/test_baseline/gt/sm21_anchor/renders/*.png` 逐像素比对，**6 张全部 0 差异像素**。neuter（`DIM 0.38→0.40`）→ 红 ✓。

**WI-5d 校准精修**（主控解锁后）：
- 检测助手 `recalibrate_plan.py`：以 **RGB(128) 墙体填充带**为锚（唯一无歧义），取其**外侧墙体轮廓线的亚像素强度质心**为外皮面。
  （踩过的坑，如实记：第一版用通用「最外侧主导线」检测，**抓到了图外的绿色尺寸线**（W=204/E=655，各向异性 14.6%）；改为锚定填充带后正确。）
- 检出：**W 247.50 / E 611.50 / N 150.50 / S 877.62**；x=36.4000、y=36.3558 px/m，**各向异性 0.121%**（判据 ≤0.30%）。
- 与主控给的数（W248.5/E612.5/N151.5/S877.5，各向异性 0.28%）差约 1px：**x 跨距完全一致（364px→36.40 px/m 逐位相同）**，差别只在原点；主控取的是 2px 抗锯齿线对的内侧边，我取的是强度质心。
- **验收**：footprint 四边残差 旧 **3.50px → 新 0.00px**；内部墙轴/区界线残差 新 **≤1.99px**（判据 ≤2px）。
- **信任边界未变**：助手只提议，控制点仍在 request 里声明，converter 只校验。新 request 落 `logs/experiments/2026-07-25_sm24_gt_review/request_v3_calibrated.json`，**07-24 目录原样保留**。
- **四张立面校准一个字没动**（主控已验像素级精确）。

### WI-6 重生成 bundle（完成）

`logs/experiments/2026-07-25_sm24_gt_review/`（新目录，旧目录未动；**未做 promotion**，未写 `case_tests/test_baseline/gt/` 或 `gt_sources/`；G10 保持 candidate）。
产物：`gt/gt.json`、`gt/renders/`（7 张，**同一 staging 目录内生成后一次原子 rename**，符合 §7.2）、`opening_elevation_audit.json`（14 行）、`review_index.json`、`manifest.json`、`conversion_report.json`、`review_annotations.json`。
门：G1–G5、G7–G9 全绿；G6/G10 False = 待人签的正确 candidate 态；BLOCK 诊断 0。

**关键 hash（FIX-3 返工后重生成，覆盖同一目录 —— 这三个是最终交付值）**
- candidate GT `content_sha256`：`f289b53d9f0d1b3969a3ce0dc2740d693f946f2caf922012305676361d7700f2`
- manifest `manifest_sha256`：`f3926bf8a8b3ea28633ee316da8ee650e3107d456ebb6998bf308bff1c6d9359`
- review-index `inventory_sha256`：`d6880bbee1b4b4ec2159307add4a3f6d3747b48dd64504f86a9e3c9c8e79022d`（10 个文件；算法写在 index 的 `inventory_algorithm` 字段）
- request `request_sha256`：`ae0fec087ef2a04814f3dbffc31553b25ea8e1c1d98eedf0b4ae383a7d4ac8a2`

⚠️ **这三个 hash 是单次 run 的值，主控复跑不会一致** —— 原因见 §6.2（ezdxf 每次写入新时间戳/GUID）。几何与 GT 内容本身是确定的。

**14 行审计表摘要**（opening / kind / host zone / along 区间 / z 区间）

| opening | kind | host | along | z |
|---|---|---|---|---|
| op_ae4 | window | z0 | [0.54, 5.34] | [1.0, 3.4] |
| op_af6 | window | z0 | [0.54, 2.04] | [1.0, 2.8] |
| op_af0 | window | z1 | [11.14, 12.64] | [1.0, 2.8] |
| op_af3 | window | z1 | [8.42, 9.92] | [1.0, 2.8] |
| op_aed | window | z2 | [14.38, 15.58] | [1.0, 2.8] |
| op_ac3 | **door** | z3 | [0.54, 2.14] | [0.2, 2.6] |
| op_ae1 | window | z3 | [4.66, 9.46] | [1.0, 3.4] |
| op_ae7 | window | z3 | [17.96, 19.46] | [1.0, 2.8] |
| op_aea | window | z3 | [17.96, 19.46] | [1.0, 2.8] |
| op_ade | **door** | z4 | [4.54, 5.44] | [0.2, 2.6] |
| op_af9 | window | z4 | [7.96, 9.46] | [1.0, 2.8] |
| op_ac9 | **door** | z5 | [5.7, 7.3] | [0.2, 2.6] |
| op_aff | window | z6 | [8.84, 13.64] | [1.0, 3.4] |
| op_afc | window | z7 | [14.38, 15.58] | [1.0, 2.8] |

（`op_ae7` 与 `op_aea` along 相同是正常的：分属 West / East 两个立面，along 是各自 facade 的局部坐标。）
GT 全部 boundary segment 的 `wall_thickness_m` = **0.24**。

---

## 6. 派工单之外发现的问题（需主控知悉／拍板）

### 6.1 【需拍板】zone↔用途注记自相矛盾（WI-5b）

派工单给的注记：`z0 会议 / z3 接待 / z5 门厅 / 其余办公`，并附描述「z5 是**南侧带门厅的小间**」。

我按 GT 几何核对：

| zone | 顶点 | 面积 | bbox | 核对 |
|---|---|---|---|---|
| z0 | 4 | 33.69 | (0,0)-(4.18,8.06) | ✅ 西南大房间、长会议桌 = 会议 |
| z3 | 4 | 40.60 | (0,15.94)-(10,20) | ✅ 北端、L 形沙发 = 接待 |
| **z5** | **8** | **33.54** | **(4.18,3.44)-(10,15.94)** | ❌ **C 形中央交通空间，第二大区，既不小也不在南侧**；host 的是**东**门 `op_ac9` |
| z4 | 6 | 26.29 | (4.18,0)-(10,4.94) | ← 「南侧带门厅的小间」实际匹配这个：L 形、南侧、host **南**门 `op_ade` |

主控自己的 `DIAGNOSIS.md` 也写「z5（8 顶点 C 形**走廊**）」，与「门厅」口径不同。
**我的处置**：**严格按 ID 施加注记（z5→lobby），没有自行改用途**；把矛盾写进 `review_annotations.json` 的 `_open_question` 字段（该文件在 review-index inventory 内，用户签的是整包）。**请主控在用户签字前裁定**：z5 是否应为 corridor、「门厅」是否应移到 z4。

### 6.2 【重要】bundle hash 跨 run 不可复现（先于本批存在，未修）

同一份 request、同一份源 DXF，连跑两次得到**不同的** manifest hash 与 GT `content_sha256`。
根因已定位到字节级：`_write_augmented_dxf` 保存时 **ezdxf 写入三处易变字段** ——`$TDUPDATE/$TDCREATE` 儒略日时间戳、`$FINGERPRINTGUID/$VERSIONGUID` 随机 GUID、文件尾 `1.4.4 @ <ISO 时间戳>` 注释（两次 diff 恰好只有这 22 行）。
链路：augmented DXF 字节 → `manifest.source_dxf_sha256` → `manifest_sha256` → `generator.manifest_sha256` → GT `content_sha256` → review-index inventory。

**后果**：① 主控轻门「独立干净复跑逐字对齐」**对不上 hash**（几何完全一致，只有这三处）；② G10 的 hash 绑定人签，**理论上无法被任何后续复跑重新验证**——签字绑的 GT 没有任何一次重跑能复现。
**未修**，因为要动 DXF 写出与 hash 契约，超出本批边界且会平移所有既有 hash（含已晋升的 `gt_sources/sm24_anchor/`）。
**修法草案**：保存前把 `$TDUPDATE/$TDCREATE/$FINGERPRINTGUID/$VERSIONGUID` 钉为常量，并去掉/固定尾部版本注释；或改用 GT canonical 内容 hash 而非 DXF 字节 hash 作为绑定根。**请主控定是否单开一批。**

### 6.3 07-24 交付的 overlay 无法由仓库代码复现

07-24 bundle 的四张立面 overlay 上有 `op_af6 z=[1.00,2.80]` 逐 opening 标注和 `datum 102: start->plan.lo` 图例，**但仓库里任何版本的 `render_gt_overlay.py` 都不画这些**（全仓 grep 无来源，实验目录也无脚本）。即那批图是**未入库的本地改动**产出的，committed 代码复现不出交付物；而 spec §7.4 [S] 明确要求「四张带 opening ID、plan along interval、z_interval 标注的 overlay」——等于该 [S] 项此前只存在于图里、不存在于代码里。
**本批已把标注正式实现进 committed 渲染器**（`op_id along=[..] z=[..]`）。
同理 `review_index.json` 的 `inventory_sha256` 算法也不在仓库里，我用 5 种常见公式都复现不出 07-24 那个值 ⇒ 本批**显式定义**该算法并写进 index 的 `inventory_algorithm` 字段。

---

## 6.5 主控轻门 FIX-1 / FIX-2 返工（2026-07-25 第二轮）

### FIX-1（必修）平面 z4 标签在交付图上不可见 —— 已修

**主控抓到的缺陷**：标签锚点用的是 `(min(xs), max(ys))` = **bbox 西北角**。对 L/C 形多边形该点不保证落在本区内：z4（6 顶点 L）的 bbox NW 角 (4.18, 4.94) 落在 **z5 走廊条**上；而 zone 按 z0→z7 逐区「填充+描边+标签」交替绘制，z5 的填充在 z4 之后画，**把 z4 的标签整个盖掉** ⇒ 交付图 8 个区只有 7 个有标签。用户签的正是「8 个区的房间归属」，少一间 = 这道人核门是漏的。**我上一轮没发现，主控逐像素核出来的。**

**改法（两处，都在 `render_gt_overlay.py` v3 平面分支）**：
1. 新增 `_label_anchor()`：用 shapely `polylabel`（pole of inaccessibility，最内点，最适合放字）求锚点，`representative_point()` 作兜底，并**显式校验 `polygon.contains(point)`**，不满足就走兜底。**不用 bbox 角、不用质心**（质心对 C 形同样在区外——见下方 neuter 第 2 格实证）。
2. **绘制分层**：第一遍只画所有 zone 的填充+描边并把标签排队；开口、footprint 画完之后，**第二遍统一画全部标签**（`anchor="mm"` 居中）。后画的区再也盖不到先画的字。

**新增锁 + neuter 自证**

| 锁 | neuter 了什么 | 结果 |
|---|---|---|
| `test_plan_zone_label_anchors_fall_inside_their_own_polygon`（真跑 sm24 8 区，含 z4 的 6 顶点 L、z5 的 8 顶点 C；断言每个锚点在**本区内**且**不在任何他区内**） | `_label_anchor` 改回 bbox NW 角 | 绿→**红** ✓ |
| 同上 | `_label_anchor` 改成质心 | 绿→**红** ✓（证实质心同样不安全） |
| `test_sm24_...y_down_rectangle_corners` 新增绘制顺序断言（最后一个 polygon 必须早于第一个 text；plan 段 polygon=8、text=8+1 stamp） | 标签改回逐区内联绘制 | 绿→**红** ✓ |

该锁还带一条**回归见证断言**：旧的 bbox-NW 锚点确实 `not z4.covers(...)` 且 `z5.covers(...)`。
（写这条时我第一版用了 `contains` 而失败——实测该点恰好落在 z5 的**西边界线上**，`contains` 不含边界。已改用 `covers`（含边界），并在注释写明 PIL 填充多边形是**含边界**的，所以它确实会被 z5 的填充覆盖。这是措辞精度问题，不是缺陷判断有误。）

**交付图实证（8/8 可见）**：用「渲染两次，第二次抑制 zone 标签，逐像素求差」的方式验证**标签像素真的活到了最终合成图**，而不是只被调用过：

| zone | role | 锚点 px | 存活标签像素 |
|---|---|---|---|
| z0 | meeting | (324,731) | 427 |
| z1 | office | (324,495) | 316 |
| z2 | office | (324,352) | 332 |
| z3 | reception | (429,224) | 479 |
| **z4** | **office** | **(529,796)** | **331** ← 上一轮为 0 |
| z5 | corridor | (457,642) | 419 |
| z6 | office | (535,477) | 340 |
| z7 | office | (535,333) | 320 |

（过程注记：我第一版验证脚本用「统计纯标签色像素 > 20」的判据，误报 6 个区「缺失」；根因是 11px 字号下绝大多数字形像素是与黑色描边混合的抗锯齿色，纯色像素本就只有十几个。判据太糙，已换成上面的差分法。**不是产物有问题，是我的第一版度量有问题。**）

### FIX-2（主控裁定）z5 → `corridor` —— 已应用

`review_annotations.json`：`z5` 由 `lobby` 改为 `corridor`；`_open_question` 换成 `_resolved`（记录：原指令 ID 与描述互相矛盾、主控 2026-07-25 按几何裁定为 corridor、最终仍以用户签字为准）；`_verified_by_builder.z5` 相应改为 `RESOLVED`。**其余 7 个用途一字未动**，z4 维持 `office`。

## 6.6 主控轻门 FIX-3 返工（第三轮）：审计表丢了三个字段

**主控抓到的缺陷（判 MAJOR）**：`opening_elevation_audit.json` 每行比 07-24 少三个字段——`opening_id`、`plan_world_along_interval`（两者都是合同 §7.4 [S] **明文**要求）、`host_zone_id`（用户人核「8 个区房间归属」的依据）。其余 15 字段一致。

**为什么是硬缺陷**：§7.4 把逐 opening 表定为**整面镜像残余风险的强制 backstop**，明写「不是可省略的辅助信息」。
- 没有 `plan_world_along_interval`，「plan interval 有没有因整面镜像换到另一扇窗」这条人核**物理上做不了**（表里只有立面侧区间）。
- 没有 `opening_id`，表与 overlay **对不上号**：overlay 标的是 GT 的 `op_af6`，表里只有 `ev_South_view_af6`，属两套句柄空间。
- 没有 `host_zone_id`，房间归属无从核起。

**根因**：与 §6.3 同源——07-24 那三个字段来自那批**未入库的本地改动**，committed 的 `build_p2_report` 从来没有过它们。所以不是我改坏了，而是「幽灵交付」的第二个受害面；但净效果是**我的交付物在人核面比 07-24 弱**，必须修。

**改法（权威来源单一化）**：新增 `P2ConversionResult.elevation_document` 保存 **G9 真正提取出来的那份 GT**（即 WI-1 postcheck 用的同一份），`build_p2_report` 用 §6.5 同款 join（GT 的 `opening_elevation` ref 的 generated handle ↔ ledger 记录）取 `opening.id` / `opening.host_zone_id` / `opening.world_along_interval`。**没有另起一套转换器侧推导**——表里的数就是权威文档里的数。

**新增锁 + neuter 自证**（`test_elevation_audit_rows_carry_the_contract_mandated_opening_columns`：14 行每行三字段非空；`opening_id` 与 GT opening 集合**双向完全一致且无重复**；`host_zone_id` ∈ 8 个 zone id 且等于 GT 值；`plan_world_along_interval` 与 GT 逐值相等；overlay 画的 opening id ⊆ 表里的 id）

| neuter 了什么 | 结果 |
|---|---|
| `opening_id` 置 None（退回 07-25 行形态） | 绿→**红** ✓ |
| `plan_world_along_interval` 置 None | 绿→**红** ✓ |
| `host_zone_id` 置 None | 绿→**红** ✓ |
| 拆掉 GT join（`opening_by_handle` 永不填充） | 绿→**红** ✓ |
| **join key 用错**（所有行都配到同一个 opening） | 绿→**红** ✓ |

**顺带发现并修掉同一文件的第二处退化（主控未点名）**：07-24 的审计文件是 `{candidate_gt_sha256, manifest_sha256, rows}` **字典信封**，把表自绑到它所描述的那份 GT/manifest；我上一版写成了**裸 list**，丢了这层自绑定。已补回同款信封，实测 `candidate_gt_sha256` 与交付 `gt.json`、`review_index.json` 三者一致。

**字段顺序差异属有意为之**：07-24 是 `sort_keys=True` 的**字母序**，我这版是**合同 §7.4 清单的逻辑顺序**（opening_id → evidence → view/facade/floor/kind → host zone → plan 区间 → 立面区间 → world → z → datum 溯源 → handles）。字段集合与 07-24 **完全相同（18/18，零缺零增）**，只是排序更贴合合同与人眼阅读。

**交付实证**：18/18 字段齐备；14 行 `opening_id` 与 GT 14 个 opening **双向完全一致**；`host_zone_id` 全部落在 8 个 zone 内且等于 GT；`plan_world_along_interval` 与 GT 逐值相等。

## 6.7 用户验收返工 FIX-4 / FIX-5（第四轮）

### FIX-4 — `gt_plan.png` / `gt_elev.png` 对齐 sm21 形态

**先定位代码边界（关键事实）**：sm21 的两张 TYPE 1 基线资产由 `render_gt.py` 的 **legacy v2 渲染器** `_render_plan_v2` / `_render_elev_v2` 产出，实测**今天仍逐像素可复现**；sm24 走的是完全独立的 `gt_render_model.render_plan_model` / `render_elevation_model`。**两条路径不共享代码**，所以改 v3 不可能动 sm21——但仍按要求补了逐像素锁。

**plan 新增**：标题 + 两行图例；每层小标题 `F1 z=0 h=4.5m 8 zones`；**上方 x / 左侧 y 绿色尺寸链**（刻度取自 GT 的 zone 边界坐标，分段值 + 总值全部现算，无写死）；房间按用途填充 + 两行标签（`z3` / `reception`）；窗=粗蓝条、门=棕色 + `DOOR`；底部 `windows S:2+door N:1+door E:3+door W:5  sill-head z 1-2.8, 1-3.4`。**用途来自 review 注记**（`render_plan_model(model, *, review_annotations=...)`，review-only 规矩不变：不入 GT、不进门、未注记退中性灰），CLI 加 `--review-annotations`。

**elev 新增**：标题 + 图例；**2×2 排布**、顺序改为 **South / North / East / West**（原为字母序）；每面标题 `South elevation 10 m wide  2 win (gt-exact x)`；**绿色宽度链 + 绿色层高链 + 蓝色 sill/窗高/head 链**；楼层分隔线；窗=浅蓝填充框、门=棕框 + `DOOR`；四面共用一个比例尺，画布按真实图元尺寸算（不再有裁字与大片死白）。

**排版返工（我自己看图发现的，逐条修掉）**：单段尺寸链重复打印总值（`4.5/4.5`）→ 只在 ≥2 段时打总值；竖链总值压住分段数字 → 移到链顶端外侧；`N win` 文字压住 DOOR 框 → 移出外框到左栏；顶部尺寸链压住图例与楼层标题 → 重排上边距。

**锁**：`test_sm21_legacy_type1_gt_renders_are_unchanged` —— 现场重渲 `_render_plan_v2` / `_render_elev_v2` 与两张committed 基线资产逐像素比对，**0 差异像素**。

### FIX-5 — 平面 overlay 窗条看不清

`bar` 由纯比例（790px 图上只有 3px）改为 **`max(6, round(9×scale))`**，并加**深色外描边**（`bar+4` 黑底 + 彩色芯）画在最上层。
**取值理由**：6px 明显可辨，且**仍小于 240mm 墙在该图上占的约 9px**（36.3 px/m），所以窗条留在墙带内、**不会盖住图纸自己的窗洞线**（人核的对照物）。深色描边解决的是「窗条与区框描边同粗近色、糊在一起」。对比图：`diag/fix5_window_bar_compare_6x.png`（07-24 / 本版 / 原图 三行 6×）。

**锁**：原比例锁拆成两半——`box` 仍验**纯比例**；`bar` 改为验**下限 ≥6 且 < 0.24×px_per_m**（即不得粗到吃掉墙带）。neuter（把下限改回 2）→ 红。

### neuter 自查（本轮 3 格，全真）

| neuter 了什么 | 跑了哪个测试 | 结果 |
|---|---|---|
| `_weights` 的 `bar` 下限 6 → 2（退回纯比例） | `test_v3_stroke_weights_scale_with_raster...` | 绿→**红** ✓ |
| `render_gt.py` `SCALE = 46 → 47`（扰动 legacy v2 渲染器） | `test_sm21_legacy_type1_gt_renders_are_unchanged` | 绿→**红** ✓ |
| `render_gt.py` `HEADER = 70 → 72` | 同上 | 绿→**红** ✓ |

### ⚠️ GT `content_sha256` 变了 —— 已查明，**不是数据改动**

主控要求「若 GT hash 变了就停下报告」。它确实变了，但我查到根因是 §6.2 已登记的那条债，**不是非预期数据改动**，证据三条：

1. **我 FIX-4/FIX-5 改的三个文件（`gt_render_model.py` / `render_gt.py` / `render_gt_overlay.py`）都不在 `compute_gt_implementation_hashes` 的任何一组里**（extractor / validator / vg 三组均不含），结构上无法影响 GT hash。
2. **同一份代码连跑两次，逐叶子 diff 只差 3 个叶子**，且全是从 augmented DXF 字节派生的哈希：`sources[0].content_sha256`、`generator.manifest_sha256`、`content_sha256`。**几何 / openings / zones / 厚度零差异。**
3. 交付 GT 语义逐项复核**与上一版完全一致**：14 openings（11 窗 + 3 门）、窗 z 恰 {[1.0,2.8],[1.0,3.4]}、门 z [0.2,2.6]、8 个 zone 全 `unspecified`、`wall_thickness_m` 全 0.24、14 个 opening id 一字不差。

⇒ 结论：GT 数据没动，hash 位移 100% 来自 ezdxf 每次写入新时间戳/GUID（§6.2）。**这也再次说明 §6.2 那条债会让「hash 没变 = 数据没变」这个直觉失效**，建议排期修。

## 6.8 用户验收返工 FIX-6（第五轮）：TYPE 1 plan 两处标注缺陷

### FIX-6a — `z5 corridor` 没有标签

**根因**：我在 FIX-4 里写的 TYPE 1 标签锚点是 **bbox 中心**（`(min+max)/2`）。z5 是 8 顶点 C 形，其 bbox 中心落在邻室里，名字被画到别人家再被那家的填充盖掉 ⇒ 交付图 8 个区只有 7 个有名字。
**这是 FIX-1 的同类缺陷换了一条代码路径**——我自己在简报里写过 TYPE 1 与 overlay 两个渲染器不共用代码，却没有把 polylabel 修法同步过来。

**改法**：`gt_render_model` 增加本地 `_label_anchor()`（shapely `polylabel` + `representative_point` 兜底 + `contains` 显式校验），并改为**两遍绘制**（先全部填充/描边/开口条，最后统一画标签）。

### FIX-6b — `DOOR` 文字被门条盖住（读成 `DO OR`）

**改法**：`DOOR` 不再画在门条正中，而是沿该立面的**内法线偏到一侧**（N/S 上下 22px、E/W 左右 30px），三个门统一处理，不是只修东门。

### 锁与 neuter 自查（4 格）

新锁 `test_type1_plan_labels_every_zone_and_keeps_door_captions_clear`：8 个锚点各自**在本区内、且不在任何他区内**；8 个名字用「渲染两次 / 第二次抑制标签 / 逐像素求差」证明**活到最终合成图**；3 个 `DOOR` 锚点与自己门条中点距离 **≥12px**（门条宽 8px）；外加**结构性绘制顺序断言**（最后一个 polygon/line 必须早于第一个 label）。

| neuter 了什么 | 结果 |
|---|---|
| 锚点改回 **bbox 中心**（即出厂缺陷本身） | 绿→**红** ✓ |
| 锚点改成**质心** | 绿→**红** ✓ |
| 两遍绘制改回**逐区内联画标签** | 绿→**红** ✓（见下方订正） |
| `DOOR` 偏移改回 `(0,0)`（画回门条正中） | 绿→**红** ✓ |

**⚠️ 自查订正（诚实记录）**：两遍绘制那一格**第一版是假锁**——我最初只写了「像素可见」这种结果型断言，把两遍改回内联后**仍然绿**。查因：**锚点修正之后，zone 之间互不重叠，后画的 zone 填充根本盖不到正确锚点上的字**，所以顺序对「zone 填充」这一面不承重。真正需要顺序保护的是**之后才画的门条与 footprint 外框**。处置：补一条**结构性顺序断言**（事件序列里最后一个 polygon/line 必须早于第一个 label），neuter 后由绿翻红 ✓。**结论：两遍绘制保留，但其理由是防门条/外框、不是防 zone 填充**——上一版简报里我对 overlay 那条的措辞把这点说宽了，一并在此订正。

### GT 语义复核（改图前后逐项相同）

14 openings（11 窗 + 3 门）/ 窗 z 恰 {[1.0,2.8],[1.0,3.4]} / 门 z [0.2,2.6] / 8 zone 全 `unspecified` / `wall_thickness_m` 全 0.24 / 14 个 opening id 一字不差 / 外包 10×20 / 审计 14 行 × 18 字段且自绑 hash 一致。GT hash 位移仍是 §6.2 的 ezdxf 债。

### 主控已处置、本轮未做的三条

§6.2（bundle hash 跨 run 不可复现）登记为跟进债本批不修；§6.3（07-24 交付物无法由仓库代码复现）由主控写入管理文档；§6.4（GLM 清单 `git checkout` 冲突）由主控在交付 GLM 前 commit 并改清单措辞。§9.2 六格按主控指示**本批不再开工**，登记为下批「先补门、再补锁」。

---

## 6.4 【运维告警】GLM 核验清单 C-00 的 `git checkout` 与本轮未提交状态冲突

GLM 清单 C-00 第 4 条要求：neuter 后「立刻 `git checkout -- <file>` 还原」。
**本轮全部改动都在工作区、未 commit**（派工单要求不 commit）。若 GLM 照此执行，`git checkout -- src/agent/judge/tarch_normalize.py` 会把本批改动**整个抹掉**，回到 `e13efd3`，之后所有核验都在核验旧代码。
⇒ **请主控在把工作交给 GLM 之前先 commit**（或改指示 GLM 用「先 `cp` 安全副本、还原时 `cp` 回来」，即我本轮 neuter harness 的做法）。我本轮正是因此没有用 `git checkout` 还原。

---

## 7. 主控中途指令执行情况

| 指令 | 执行 |
|---|---|
| WI-5d 暂停、只做诊断、若是 GT 数据问题立即停下汇报 | 已照做。诊断结论：**不是 GT 数据问题**——四张立面 14 个 opening 的 gt↔图纸像素偏差 **最大 1.2px、均值 0.325px**，框尺寸差 ≤1px（`diag/alignment_diagnosis.json`）。故未停工，继续。 |
| WI-5a 降级 | 已降级为次要，仍做，R-01 硬约束照旧 |
| 新增 WI-5e，与 WI-5b 合并 | 已做（见 §5 WI-5e） |
| WI-5d 解锁、按检出外皮面重算平面控制点 | 已做，验收判据均达标（§5 WI-5d） |
| 四张立面校准不要动 | 一个字未动 |
| WI-6 等根因结论 | 已在结论之后执行 |

---

## 8. 诚实交接

### 未竟项（精确列出）

1. **WI-2 的 §9.2 frame / title 六格必红夹具 —— 未做**（0 条）。上下文预算耗尽，按派工单优先级（WI-1 > §9.3 z > WI-5 出图 > WI-4 > §9.2/§6.6）它排在最后一档，我选择保住前面几项的质量与 neuter 自证。
   **并且我在设计阶段就发现其中至少两格现在过不了**，一并交出以便下批直接施工：
   - 「bbox 相同但 handle 指向第二框」：现实现对 `frame_entity_handle` **只检查存在性**（`frame is None`），完全不校验其几何/bbox ⇒ 指向另一个实体不会红。**需要新增校验才能让这格真红**，不是补个测试就行。
   - 「entity 跨 frame 边」：未见对应校验。
   - 「frame handle 不存在」「框内 0/2 标题」「alias map 未列」大概率已被 `tarch_elevation_title_mismatch` 覆盖，但**我没有实测**，不敢写「已覆盖」。
   ⇒ 建议下批当作**「先补门、再补锁」**处理，而不是纯夹具批。
2. **§9.3 第 6/7 格由同一道门拥有**（extractor 楼层包含性），非两道独立门——已在 §3.1 标注。
3. **配对 postcheck 的 kind / view-id / ref-count 三格是函数级锁**（直接调 `_verify_pairing_consistency` 并篡改 ledger 一侧），只有 **z 漂移那格是整条生产路径**。原因：kind/view-id 若从 ledger 侧改，manifest 证据会同步改，extraction 会先在 `elevation_opening_no_candidate` 红掉，够不到 postcheck；要让两侧真正分叉只能模拟接线漂移。**接线本身另有独立 neuter（第 4 格：拆掉 postcheck 调用 → 红）**，故不构成假锁，但覆盖形态如实标注。
4. **`_calibrate` / `_density_box` 等 legacy 自动密度框未被 v3 复用**（合同 §7.3 禁止），本批也没有让它进 v3。WI-5d 的检测助手是**离线脚本**，不在生产判定路径内。

### 已知限制

- **sm24 平面底图 790×1111**（sm21 为 2133×1345），底图本身分辨率受限，这是案例输入资产的属性。**未改 `case_data/` 原图**。无损放大方案本批**未做**（会改输出像素尺寸、可能牵动 hash 与测试），如需可另议。
- 本批测试仍引用 `logs/experiments/2026-07-24_sm24_gt_review/` 下的 `source.dxf` / `request_v3*.json` 作为夹具输入（该目录按要求原样保留）。新校准 request 只用于 WI-6 bundle。

### 边界遵守

未写 `case_tests/test_baseline/gt/`、`gt_sources/`、`case_tests/e2e_tests/*/case_data/`；未动 scorer / Va / Vg / v2 legacy adapter / reading / correction / execution；未动 `_pixel_for_world_plan` / `_pixel_for_world_elevation` / affine 系数（WI-5 全部是 draw-only + 合成层）；未放松任何 fail-closed 门；未加生产后门；未为过测试改容差；未 commit / push。
备份：`backup/src_history/2026-07-25_elevation_debt/`（5 文件）、`backup/scripts_history/2026-07-25_elevation_debt/`（1 文件）。
