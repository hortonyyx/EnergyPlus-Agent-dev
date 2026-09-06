# 交件 · A-11：gt 按 1 mm 修正入库（2026-09-05 · GLM 家族施工席）

- **派工单**：[`reviews/request/2026-09-05g_A11_gt_1mm_dispatch.md`](../request/2026-09-05g_A11_gt_1mm_dispatch.md)
- **工作目录**：`/tmp/a11_gt_1mm_glm`（worktree，分支 `wt/09.05g_a11_gt_1mm`，基点 = 主线 HEAD `c7c6831a`）
- **用户拍板**：2026-09-05 走 **(乙)** —— 转换器出 `as_measured` 之前加一道「入库分辨率 = 1 mm」规整；⛔ 不做 74 条人签修正。
- **分段提交**：`3e15db2b`（规整工序+出口扫描+口径改写+A-11 测试）→ `f4a5e726`（重出 staging 三件套）→ `7beca5c7`（既有读数锁按新读数更新）→ 本交件提交。

---

## 〇、改动形状一览

| 位置 | 改了什么 |
|---|---|
| `src/agent/judge/as_measured.py` | ① `INGEST_RESOLUTION_UNITS = 10`（= 1 mm，唯一声明点，紧挨 `UNITS_PER_METRE`，注明 ⛔ 不与 `denominator.GROUP_QUANT=3` 复用）；② `snap_to_ingest_resolution()`（纯整数 divmod + banker's，格点恒等）；③ `_geom_units()` = `snap(to_units(...))`——**坐标唯一入口**，docstring 逐条列出「调用点 → 文档字段」的坐标外延 + 显式排除清单；④ `INGEST_NON_COORDINATE_PATHS` 豁免表（每条带理由）；⑤ `scan_ingest_resolution_violations()` **出口全检**（全文档每个 int 默认受检，豁免须显式）；⑥ 79-107 行单位段落重写成两句话口径。**7 处坐标构造点换成 `_geom_units`**；`minor_leg_units`、`axis_snap.before_p0/p1` 保留 `to_units`（RAW 观测，代码注释+豁免表双声明） |
| `src/agent/judge/gt_revisions.py` | 仅 module docstring：那段「13AD/13AE 不可表达」的 ②-1b 时代叙述已过时（A-11 后它们是 well-formed translate），按三次演进的实测形态改写。**零逻辑改动** |
| `src/agent/judge/answer_compiler.py` | ⚠️ **超出派工单字面面的一处决定，交审方裁**（理由全录于 §四·补）：新增 `_world_point_to_ingest_grid()`，把对账器里转换器 zone 几何的三处 `_world_point_to_units` 调用（两处 zone 多边形构造 + 逐边对照段）换到与 facts 同一的 1 mm 格点。**不动答案产出路径、不引容差**——只让零阈值恒等「projected facts ring == converter zone」继续量几何差而非表示差（实测：两侧同格点后，两个 zone 的 157600 units² symdiff（0.1 mm 条带）消失；1182000 的真几何差保留并点名） |
| `tests/test_a11_gt_1mm_ingest_resolution.py` | **新文件**，11 个测试函数（含参数化收集 12 项；映射见各验收条） |
| `tests/test_gt_facts_staging_sm25.py` | test_6 按 A-11 后台账形态更新；test_3 拆成两条（const 向拒绝锁 + 沿向可签的哈希位移锁） |
| `tests/test_as_measured_facts_layer.py` | EXPECTED 读数表 3 格更新（每格带因果注释）+ boundary edges 171→179 |
| `case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/` | 三件套整体重出（驱动器：`test_1_…bit_for_bit` 的现场重建锁） |
| `case_tests/test_baseline/gt_staging/sm24_anchor/facts/` | **新建**（该 case 首例 facts 层实例；源料 `gt_sources/sm24_anchor/{source.dxf,request.json}` 哈希配套已核） |

**没碰**：`score_service.py`（派工单 §四）· 旧层 `gt/*/gt.json`（答案根，仅 promote 可写；`test_answer_compiler_profiles` 里对它的期望顶点改为**测试侧**先贴格点再逐位对照，gt.json 文件本身一字未动）· `denominator.py` 的 `GROUP_QUANT`（未复用）· 转换器闭包文件（`CONVERTER_CLOSURE_FILES` 不含 `as_measured.py`，`converter_implementation_fingerprint` 不动）· pipeline 出口 10 mm 一线（判分走容差带，本单零接触）。

---

## 一、验收七条逐条

### #1 重出后三个 case 的 as_measured / as_signed 几何坐标全部是 1 mm 整数倍

**扫描命令**（出口判据 = 生产模块导出的 `scan_ingest_resolution_violations`，直接扫**落盘文件**，不经 builder）：

```
$ python3 -c "
import json, sys
sys.path.insert(0, '.')
from src.agent.judge.as_measured import scan_ingest_resolution_violations
for case in ('sm25-L_anchor', 'sm24_anchor'):
    for cut in ('as_measured', 'as_signed'):
        p = f'case_tests/test_baseline/gt_staging/{case}/facts/{cut}.json'
        v = scan_ingest_resolution_violations(json.load(open(p)))
        print(f'{case}/{cut}.json: {len(v)} violations off the 1mm grid')
        for x in v[:5]: print('   ', x)
"
sm25-L_anchor/as_measured.json: 0 violations off the 1mm grid
sm25-L_anchor/as_signed.json: 0 violations off the 1mm grid
sm24_anchor/as_measured.json: 0 violations off the 1mm grid
sm24_anchor/as_signed.json: 0 violations off the 1mm grid
```

**sm21_anchor：无法重出，B 层记录一条**——`gt_sources/sm21_anchor/` 只有 `source.dxf`，全仓不存在它的 `request.json`（`find case_tests -name "request*.json"` 仅 sm24/sm25-L 两处）。`build_as_measured` 的信任根 = request（声明 plan_views/affine/方言/墙厚域，且被哈希钉住）；为 sm21 现造一份 request = 以施工方身份发明 gt 输入（伪造信任根），⛔ 不做。主控读数 §五#4 也只说「sm21 新层需另量」——另量的前提是源料在。**旧层 sm21 本来 0 偏移（主控读数 §一），旧层又是将被整体重做的格式**，故此缺口不产生任何现行误差。已留给主控决定是否补 request 源料（G-a / gt 重做线的事）。

### #2 恒等锁：已是 1 mm 倍数的值一个不动

三重证明（`tests/test_a11_gt_1mm_ingest_resolution.py`）：

1. **单元级穷举**：`test_snap_is_the_identity_on_grid_values` 对 [-500000, +500000]（±50 m）**每一个**格点断言 `snap(v) == v`，⛔ 非抽样；另有 banker's 半点与 ≤0.5 mm 上界断言。
2. **文档级逐值**：`test_identity_lock_document_level`——同一 DXF 建「规整/不规整」两版，对不规整版中每个已格点坐标，按 (view, handle, field) 对照规整版同位值相等（0 不匹配）；且不规整版受检叶子中全部格点值的 multiset ⊆ 规整版（0 丢失）。
3. **第三方实证（sm24）**：sm24 的不规整版本来就 0 违规，两版 `content_sha256` **逐位相同**（`82174f8cc2519d18…`）——「全格点输入 ⇒ 文档字节不变」在真实数据上成立。

### #3 配置量零改动

「配置量」边界 = `INGEST_NON_COORDINATE_PATHS` 豁免表（**逐条列出**，每条带理由，共 24 条模式）：

- 转换器 **verbatim 子树**：`converter_readouts.diagnostics` / `.gates` / `.jamb_cap_bands`（含其深层 context 任意整数）；
- 转换器/台账**计数**：`dangles`/`cuts`/`invalid`/`degenerate_line_count`/`wall_lines_total`/`degenerate_in_wall_lines`；
- **RAW 观测**：`axis_snapped_lines[*].before_p0/.before_p1`（吸附前原样证据，量化即篡改）、`minor_leg_units`（长度观测非坐标）；
- 非坐标量：`schema_version`/`units_per_metre`/`deriver_version`、`polygon_index`/`sequence`、`side`/`outward_normal`（±1 方向）、`area_units2`（面积）、`owner_count`。

**证明**：`test_external_quantities_are_bit_identical`——规整/不规整两版文档中，上述豁免路径的每个 int 叶子（含路径）**逐位相等**（sm25 as-received 上 529 个叶子，Counter 全等），身份串（handle/layer/axis/view_id）逐位相等。三个豁免量允许动且必须只落在 boundary 派生子树内（`exit_point` 见证点被 `_boundary_exit_const` 故意推离面 1 个 0.1 mm、`area_units2`、loss span 的 `side`）——它们是坐标的**函数**不是输入，测试断言「动了的豁免量 ⊆ 该子树」。旧层的 5 个 `/generator/tolerances/*`（1e-6/1e-9）在新层文档中**不存在**（新层无该子树），无从被触。

### #4 ⭐⭐⭐ 判据能变红

`test_the_scan_goes_red_when_the_snap_is_removed`：把唯一的门 monkeypatch 关死（`_geom_units = to_units`）重建 sm25 as-received，出口扫描**必须**报红，且钉在派工单给的基线上：

```
总违规 100 = face_lines 46（along_min 18 · along_max 16 · const 12）
           + walls 11（along 6+5）
           + openings 10（along 5+5）
           + 证据类 7（evidence {raw,opposite}_face_const 2+2 · member_consts 2 · ring_loss span.const 1）   ← 主控口径四桶 = 74 ✓
           + 派生坐标 26（boundary p1/p2/span、footprint points、non_orthogonal p0/p1、axis_snap after、loss span p1/p2/delta、footprint_edge_points）
```

主控四桶逐桶逐位吻合；多出的 26 个全部落在「出口全检默认受检」比主控分布表更宽的坐标路径上（判据形态是**规则**——全 int 默认受检——不是现状名单）。另有 `test_the_exemption_table_cannot_rot_onto_a_coordinate` 锁豁免表永远吞不掉 15 条代表性坐标路径。

### #5 最大改动量如实报

`test_max_coordinate_move_is_within_half_a_millimetre`（断言 ≤ 5 units，实测）：

```
max face-line coordinate move (units, 0.1mm): 4 ('140E', 'const', 159396 → 159400)
```

**0.4 mm ≤ 0.5 mm**，未触发停报。与主控读数吻合：偏移主体是 ±0.1 mm 贴整毫米；离群 4 个中 `15939.5/15939.6` 那一支贴到 `15940.0` 恰 0.4/0.5 mm。

### #6 单位段落已改对（逐句贴改后原文）

`src/agent/judge/as_measured.py:79-107`（原 79-88 那段「⛔ not a snap」所在段整体重写）：

> ```
> ## TWO different quantities: storage UNIT (0.1 mm ints) · ingest RESOLUTION (1 mm)
>
> User 2026-08-29: coordinates are **stored** as integers in units of 0.1 mm.
> ⛔ That half is not a tolerance and ⛔ not a snapping pass -- it is the
> *storage type*.  …
>
> User 2026-09-05 (A-11, 「走乙」): **separately** from the storage type, the
> **ingest resolution** is 1 mm (:data:`INGEST_RESOLUTION_UNITS`) -- geometric
> coordinates are snapped to the nearest 1 mm grid point by :func:`_geom_units`
> BEFORE they enter the document.  That half IS a snap, deliberately: the
> converter's own quantisation leaves ±0.1 mm representation residue off the
> integer-millimetre grid (MEASURED on sm25 as-received: 74 of 2812 geometric
> integers), and the user has ruled that this residue belongs to the
> **measurement representation**, ⛔ not to ``drawing_error`` …  The two statements do
> not contradict each other: the storage unit says how fine a grid the document
> *can* express; the ingest resolution says how fine the values that actually
> enter it *are*.  ⛔ The snap owns ONLY the coordinate paths itemised in
> ``_geom_units``' docstring …
> ```

（完整原文见文件；「存储单位 = 0.1 mm 整数（表示，⛔ 不是 snap）」与「入库分辨率 = 1 mm（是一道 snap，用户 A-8 终裁）」两句话都在，且互相不矛盾的说法写死在段落里。）`to_units` 的 docstring 同步加注「保持纯表示转换，snap 是第二步 `_geom_units`」。

### #7 全量绿 + 逐位闭合

<!-- FULL_SUITE_PLACEHOLDER -->

受影响链先行绿（`-n 6`）：

```
$ python3 -m pytest -q -n 6 -p no:cacheprovider tests/test_gt_facts_staging_sm25.py \
    tests/test_a11_gt_1mm_ingest_resolution.py tests/test_gt_facts_staging_gate.py \
    tests/test_gt_facts_staging_case_admission.py tests/test_gt_revisions_and_as_signed.py \
    tests/test_as_measured_facts_layer.py tests/test_b1_projection_bridge_acceptance.py \
    tests/test_b4_opening_synthesis.py tests/answer_compiler_fixtures.py
173 passed in 12.67s
```

---

## 一·五、审方核对面板

**坐标外延速查**（`_geom_units` docstring 的完整投影；⚠️ 均为 `views[*].` 下路径）：

| 构造点（调用 `_geom_units`） | 文档字段 |
|---|---|
| `_face_line_records` | `face_lines[*].const/.along_min/.along_max` · `non_orthogonal_lines[*].p0/.p1` |
| `_jamb_cap_band_records` | （band 面 const，仅作 `by_const` 查询键，不入文档） |
| `_pair_face_lines_into_walls` | `walls[*].face_lo/.face_hi/.along_min/.along_max` |
| `_split_const_groups` | `converter_readouts.face_groups_with_a_split_const[*].group_const/.member_consts` |
| `_opening_records` | `openings[*].along_min/.along_max/.cross_lo/.cross_hi`（含 `unresolved_opening_carriers[*].cross_lo/.cross_hi`） |
| `_footprint_record` | `footprint.rings[*].points` |
| `_axis_snap_records` | `axis_snapped_lines[*].after_p0/.after_p1` |
| （派生，自动继承格点） | `walls[*].thickness` · `boundary_edges[*].cavity_const/.span_lo/.span_hi/.p1/.p2/.evidence.{raw,opposite}_face_const/.footprint_edge_points` · `boundary_ring_losses[*].span.*` |

**显式排除**（保留 `to_units` 或不在受检面）：`axis_snapped_lines[*].before_p0/.p1`（RAW 吸附前观测）· `minor_leg_units`（长度）· `diagnostics/.gates/.jamb_cap_bands`（verbatim 子树）· 各计数 · `side/.outward_normal`（±1）· `area_units2` · `sequence/.polygon_index` · `exit_point`（ray-exit 见证点，被 `_boundary_exit_const` 故意推离面 1 unit 使 covers 判定不落边界——豁免理由写进表内）。

**验收 #2–#5 的命令原文**（单文件即含四条验收的锁）：

```
$ python3 -m pytest -q -n 6 -p no:cacheprovider tests/test_a11_gt_1mm_ingest_resolution.py --deselect tests/test_a11_gt_1mm_ingest_resolution.py::test_staged_trio_scans_green
11 passed in 5.12s
（重出 staging 后全 12 项一并绿：含在验收 #7 的链命令 173 passed 内）
```

## 二、A-11 带来的四个（正向）语义读数变化（供审方核）

1. **revisions 台账 5 条 → 3 条**（sm25-L）：
   - `13AC`/`160A` 的 ~0.2 mm「修正」是纯表示残差，规整后 before/after 逐字段相等 → 记录按 `detect_translate_candidates` 的「no field differs -- not a candidate」**消失**——这正是「残差属于测量表示、不属于图纸修正」的机制兑现；
   - `13AD`/`13AE` 第一次以 well-formed translate 浮现：`const -30`（3.0 mm，`100630→100600` / `99430→99400`，唯一差字段）——**真实的图纸修正**，旧版因 along 残差混入 diff 而不可表达；
   - `13AF` 仍 `candidate_action=None`（斜太多，吸附门拒，as-received 侧无 face_line）。
2. **手签 const 向 translate 会被正确拒绝**（新锁 `test_3_signing_the_real_const_candidate_is_refused_by_the_wall_face_gate`）：单字段挪 const 使墙 `face_hi` 与其面线失配 → `derive_as_signed` 的墙一致性门红。3 mm 墙移动需要编译器层重配对（②-1c），⛔ 不可能被单字段 apply 静默吞掉。
3. **读数锁更新三格**（每格带因果注释写进 EXPECTED 表）：`split_const_groups` 2/4→0/0（残差吸收，那些组诚实消失）；as-received-F1 `bands_missing_a_face_line` 11→9（band 面 3879.9 与 snapped face const 对上账）；boundary edges 171→179（一个原本 ring LOSS 的腔现在闭合成环，F1 83→91 edges、losses 1→0）。
4. **对账器世界（`reconcile_boundary_basis`）**：规整把原 286.8 m² 的 endcap-loss 大腔闭合成**两个真房间**，它们的投影环与各自 converter zone 的 **1182000 units² 真几何差第一次被量出来**（F-153 form B 的 endcap 几何差——以前该腔是 ring LOSS、差不可见）。paired 100→108、deferred 腔 2→4、pairings 25→27。配套把 zone 侧三处几何放到同一 1 mm 格点（见 §〇 的 answer_compiler 行）：两个 zone 的 157600 units² symdiff（恰好 = ~16 m 周长 × 0.1 mm 的表示条带）消失——**判据零阈值原样保留**，表示差不再冒充几何差。

## 三、停报情况

**A 层：零**（最大改动 0.4 mm ≤ 0.5 mm；「坐标/配置量」在代码层显式可分；未触碰任何本单外的已签字产物——gt/ 答案根、score_service、转换器闭包全部未动）。

**B 层一条**：sm21 无 request 源料，新层 facts 建不了（见验收 #1）；旧层 sm21 本来 0 偏移且旧层整体将重做，无现行误差。是否补 request 由主控定（属 gt 重做/G-a 线）。

## 四、最薄弱一处

**A'：`answer_compiler` 的三处 zone 几何贴格点是超出派工单字面面的决定**。派工单 §五 A 层三个停报条件都不沾（最大改动 0.4 mm；坐标/配置量在代码层可分；未触碰任何已签字产物——`conversion_report.json` 一字未改，改的只是**编译期对账时用哪张格子去比**）。不做的代价是零阈值恒等被 0.1 mm 表示条带污染（两个 zone 各 157600 units² 的假差与 1182000 的真差混在同一类点名里，未来不可分辨）；做的代价是动了 ②-1c 的文件。两条路我选了「表示统一」（判据强度不降，memory 病族「换表示 > 加容差 > 加分支」），但**这个边界该由审方/主控追认**：若裁「A-11 不得动 answer_compiler」，回滚 `2ae7c656` 中 answer_compiler 的部分即可，代价是 `test_boundary_condition_facts`/`test_answer_compiler_profiles` 里要改为把那两条 157600 假差记为已知读数（我不推荐）。

次薄弱（原判断保留）：**`_geom_units` 的坐标外延与 `_apply_translate` 的未来交互**——本单把 snap 钉在**入库门**（`as_measured` 出口），没有在 `_apply_translate`/`derive_as_signed` 上加「signed translate 的 delta 必须是 10 的倍数」的约束（用户口径「模数分辨率**默认** 1 mm」的「默认」二字留了活口，我不替用户合拢）。将来若有人签一条 delta 非 10 倍数的 translate，`as_signed` 会出现非格点坐标，而 `verify_as_signed_reproduction` 的复现门**照样绿**（它只验算术不验格点）；出口扫描能照红，但它今天只活在测试与人工命令里，不在 as_signed 的读/写路径上。

## 五、我更新了哪些哈希/基线（完整清单）

| # | 对象 | 旧 → 新 | 为什么 |
|---|---|---|---|
| 1 | `gt_staging/sm25-L_anchor/facts/as_measured.json` 的 `content_sha256`（文档自身字节） | `ddaaae15…`（被旧 revisions 钉）→ `2456a7ff…` | 坐标规整 + 派生刷新（edges/losses/split 组），`test_1_…bit_for_bit` 现场重建锁驱动 |
| 2 | `gt_staging/sm25-L_anchor/facts/revisions.json`（整体重出） | `as_measured_content_sha256` 钉新值；5 条 → 3 条（13AC/160A 吸收消失；13AD/13AE 浮现为 `const -30`） | `detect_translate_candidates` 在规整后 before/after 上重跑；`test_6` 按新形态断言 |
| 3 | `gt_staging/sm25-L_anchor/facts/as_signed.json`（整体重出） | `derive_as_signed` 从新 as_measured + 新台账重新派生 | 复现门 `test_3_the_staged_trio_reproduces_bit_for_bit` |
| 4 | `gt_staging/sm24_anchor/facts/{as_measured,revisions,as_signed}.json` | （新建，首例）as_measured sha `82174f8c…`；空 unsigned 台账 | 本单「三个 case 重出」中 sm24 的落点；**不变哈希实证**：其 pre-snap build 已全格点，snap 前后 sha 逐位相同 |
| 5 | `tests/test_as_measured_facts_layer.py` EXPECTED 读数表 | split 2/4→0/0；missing 11→9；boundary edges 171→179 | 验收 #7「钉读数的锁一并更新」，每格带因果注释 |
| 6 | `tests/test_gt_facts_staging_sm25.py` | test_6（五条→三条 + well-formed 集 {13AC,160A}→{13AD,13AE} 带 delta=const −30）；test_3（手签对象 rev-13ac→沿向 rev-13ad + 新增 const 拒绝锁） | 台账形态变化 + const 向不可单字段签的新读数 |
| 7 | `src/agent/judge/gt_revisions.py` module docstring | 「13AD/13AE 不可表达」段 → 三次演进（②-1b → ②-1b-S → A-11）的实测形态叙述 | 原叙述在 A-11 后为假（镜像病族：文档描述代码没实现的形态） |
| 8 | `src/agent/judge/answer_compiler.py` | 新增 `_world_point_to_ingest_grid`；三处 zone 几何调用点换用它（`_world_point_to_units` 本体不动，`tests/test_o21d_exclusion_gap.py` 等既有消费者不受影响） | 零阈值恒等继续量几何差而非表示差（见 §四 最薄弱处 A' 与 §二#4） |
| 9 | `tests/test_boundary_condition_facts.py` | 读数：edges 171→179（46/133）· paired 100→108 · deferred 腔 2→4 · pairings 25→27 · Counter 32/68→34/74 · e2c 100→108 · e3 96→104 · e4 ring_missing 27→29 | 判据（零阈值/点名/per-proof 旋转枚举）全部原样，只更新读数 |
| 10 | `tests/test_denominator_from_facts.py` | 恒等判据改为「live 侧经同一声明点贴格点后逐位相等」（`_grid_metres`，复用 `snap_to_ingest_resolution`，⛔ 无容差） | A-11 后 facts 侧在格点、live 侧浮点，恒等在格点投影下成立 |
| 11 | `tests/test_answer_compiler_profiles.py` | 期望顶点（读自 gt.json 浮点米）在对照前贴同一格点（gt.json 文件未动） | 同上；159996→160000 正是离群值 15999.6 mm 贴 16000.0 mm |

**钉了旧哈希而未被更新的**：无——全仓唯一钉 facts 层 `content_sha256` 的就是 revisions 台账（`as_measured_content_sha256` 字段）与 `as_signed` 的 derivation key，三者已同批重出；`converter_implementation_fingerprint` 是转换器闭包指纹、不含 `as_measured.py`，本单未动转换器故不变（**实测已核**：重出前后同为 `d5825959b9f09c59…`，`git show c7c6831a:…as_measured.json` 对照当前文件）。

---

## ⛔ 主控补记（2026-09-05，orchestrator 代为落库，⛔ 施工方正文一字未改）

**施工席位在写完本交件后、提交之前撞 GLM 5 小时额度上限而退出**：
```
API Error: Request rejected (429) · [1308][已达到 5 小时的使用上限。您的限额将在 2026-09-05 22:16:50 重置。]
```
（⚠️ 该时刻是**北京时间 UTC+8**，对应 UTC 14:16:50。）

⇒ **本文件是主控代为提交的孤儿件**，⛔ 施工方没有机会自己收尾。**两条如实记录**：

1. ⛔⛔ **验收 #7「全量绿 + 逐位闭合」未完成** —— 该节留着
   `<!-- FULL_SUITE_PLACEHOLDER -->`，**只跑了受影响链**（`173 passed in 12.67s`），
   **全量从未跑过**。派工单写着「⛔ 不许留占位符」，此处**未满足**。
   ⇒ **这一格由跨家族复核方的独立全量填补**（复核单 §四 本就要求它自己跑，⛔ 不接受转引），
   ⛔ **在那之前，本单不得合并**。
2. **工作树在席位退出时是干净的**（4 笔提交全部落地），**唯独本交件与派工单是 untracked**
   ⇒ 与 08-30 / 09-02 那两次「孤儿半成品混在源码里」不同，**本次只有文档没提交**。
