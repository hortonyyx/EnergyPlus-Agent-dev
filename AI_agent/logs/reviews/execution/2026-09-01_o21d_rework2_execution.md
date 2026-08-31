# 执行档 · ②-1d 第二轮返工：堵掉 exclusion 无界豁口

- **日期**：2026-09-01 · **施工方**：Claude 家族施工席 · **基线**：`58bb59f`
- **派工单**：[request/2026-09-01_o21d_rework2_exclusion_gap.md](../request/2026-09-01_o21d_rework2_exclusion_gap.md)
- **上一轮裁决**：[verdict/2026-08-30_o21d_rework_crossreview_glm.md](../verdict/2026-08-30_o21d_rework_crossreview_glm.md)

## 〇、开工自检（派工单要求逐条自证）

| # | 项 | 读数 |
|---|---|---|
| ① | `git rev-parse HEAD` | `58bb59f28d785139b48df642783db2c4db7ab537` ✓ |
| ② | 三个穿透自己复跑（⛔ 不转引） | 见 §一，**①/#3 主树复现，②的合成 fixture 因 as_measured 已修而失效，真实成因形态=#3** |
| ③ | 四文件基线 | `pytest -n 4 <四文件>` → **84 passed in 21.57s** ✓ |

## 一、⭐ 自己复跑三个穿透（关键：主树 vs 复核方旧副本）

复核方探针留在 `/tmp/o21d_r2/`（=`0cd2858` 副本）。我先核对：`answer_compiler.py`（含
exclusion 逻辑）从 `0cd2858` 到 `58bb59f` **零 diff**（`git diff 0cd2858..58bb59f -- src/agent/judge/answer_compiler.py` 空），只有 `as_measured.py` 变了 +278（=F-153 loss ledger 落库）。
⇒ 门逻辑一致，可直接主树复现。探针复制到 scratchpad、`REPO` 改指主树后跑：

- **穿透 ①（幻觉 zone 塞进共用 NA cavity，probe_r5）**：主树**复现** ——
  `baseline: passed=True paired=100 zones=29/29`；加幻觉后 `passed=True paired=100 zones=30/30`，
  幻觉被 `cavity:04e...` 吸收为 exclusion。✅
- **穿透 #3（sm25 现存 3 cavity 被误读）**：主树**复现** —— baseline exclusions =
  `[(F1-z0,8bd), (F1-z4,04e), (F1-z5,04e), (F2-z0,495)]`，即 3 个 distinct cavity
  （88.27/28.68/70.34 m²）以「无 logical ring」身份静默通过。✅
  ⭐ **新发现：z4/z5 合法共用 cavity:04e**（z4∩z5 面积=0，内部不相交）⇒ 唯一性判据
  **不能**用「一 cavity 至多一 zone」，否则误杀 baseline。
- **穿透 ②（probe_r3 诚实 L 房间同因静默）**：那个**合成 fixture 在主树上不再复现** ——
  `honest producer derive(5.0)` 现在给 L 房间导出了 6 条边（F-153/F-154 的余段切分/端头
  修复恰好修好了那个 junction-fragment）。但它的**真实成因形态就是 #3**（裁决 §二 A1
  明说「A1 同因失效 = sm25 现在时」）：sm25 那 3 个够大且围合却导不出 ring 的 cavity，
  正是「同因失效、分辨力 0」的活体。⇒ **我按 #3 这个真实成因形态立判据，不去堵那个
  已被上游修掉的合成 fixture。**（[[reproduce-the-form-not-the-run]]）

## 二、修法（纯门侧，只改 `answer_compiler.py` + 新增锁文件）

根因：`reconcile_boundary_basis` 用 `derive_boundary_edges(view, 0.0)`（**生产者本人的
重导函数**）判断 cavity「有没有 ring」，同因失效时把真实房间与幻觉 zone 一并吸收为
「天然 NA」exclusion，且 `accounted_converter_zones.add()` 无条件执行 ⇒ 主声称
「29/29 全有去向」被污染。

三处改动（都在 `reconcile_boundary_basis` 与 `BoundaryBasisExclusionV1`）：

1. **删掉同因重导**：`derive_boundary_edges` 在 `answer_compiler.py` 里**归零**
   （连 import 一起删）。改**消费 `view.boundary_ring_losses` 台账**（被哈希覆盖、已落库）。
   > 机械证据（acceptance #3）：`grep -n derive_boundary_edges src/agent/judge/answer_compiler.py`
   > → **ZERO**。台账 `cavity_id` 与门的 `_cavity_id` 逐字节等价（两套 `_opaque_id`/
   > `_band_rectangle`/footprint 完全相同），可直接按 id 匹配。
2. **exclusion 三分支**（无 stored ring 的 zone）：
   - cavity 在台账 → `evidence=registered_ring_loss`（合法，携 `reason`+面积）；
   - `min_room_area_m2` 传入且 `cavity.area ≤ 阈值` → `below_request_area_threshold`（合法出口，修 N3' 管井假红）；
   - 否则 → 结构红 `facts_boundary_ring_missing`（阈值 None 时 = fail-loud 默认，E3 靠这条保持原消息）。
   新增可选形参 `min_room_area_m2=None`（keyword-only，84 个既有 2-arg 调用不受影响）。
3. **唯一性**：共用同一 exclusion cavity 的 zone 内部两两相交 →
   `converter_zones_overlap_in_shared_exclusion_cavity` 结构红（z4/z5 不相交合法；
   幻觉=z5 副本，重叠 → 红）。

## 三、验收表逐条读数

| # | 验收项 | 命令/读数 |
|---|---|---|
| 1 | 三穿透复跑 + 改后各红 | probe_r5 改后 `passed=False`，`converter_zones_overlap_in_shared_exclusion_cavity:plan-F1:cavity:04e...:F1-halluc-in-shared-cavity:F1-z5`；#3/②→ `test_deregistering_a_live_cavity...` 红（见下）|
| 2 | 先绿后红自证 | 每条新锁都先断言合法形态 `passed=True`（z4/z5 共用绿、台账在时绿、阈值内绿），再断言变异红 |
| 3 | 判据不与生产者同因 | `test_reconcile_never_re_derives_the_ring_it_judges`：`inspect.getsource(reconcile)` 里 `derive_boundary_edges` **不存在** ✓ |
| 4 | 反向不许误杀 | `test_below_threshold_cavity_has_a_legit_exit...`：0.058 m² 管井腔 无阈值→红、传生产阈值 5.0→`below_request_area_threshold` 绿 ✓ |
| 5 | 3 cavity 显式登记指向出处 | `test_three_live_cavities_are_registered_exclusions...`：三条 `evidence=registered_ring_loss`、`reason=owner_count`、面积 `8826560000/2868321200/7033920000` units²（=88.27/28.68/70.34 m²）✓ |
| 6 | 已落库哈希未变 | gt_staging facts 三件套 sha256（HEAD vs worktree 相同）：`as_measured 0d3aefa2…` · `as_signed e5d4da3a…` · `revisions 4db9e126…` **全 UNCHANGED** ✓ |
| 7 | 四文件基线全绿 | `pytest -n 4 <四文件>` → **84 passed**（改后再跑仍 84 passed）；+ 新锁一起 = **91 passed in 18.99s** ✓ |
| 8 | 列全改动路径 | `src/agent/judge/answer_compiler.py`（+86/-20）· `tests/test_o21d_exclusion_gap.py`（新，7 锁）· `AI_agent/architecture/as_drawn_layer_contract.md` §5.2 · 本执行档。⛔ 未 `git add`/commit |

补充回归：`pytest -n 4` 所有 import `answer_compiler` 的文件（closure/exit_gate/profiles/boundary）
= **36 passed**（schema 加了必填 `evidence` 字段，只在门内构造、无别处受影响）。

## 四、禁令核对

- ⛔ 纯门侧：未改事实层任何值、未改 `as_measured.py`（`git diff` 空）✓
- ⛔ 未改 `tests/test_boundary_condition_facts.py`（新锁全在 `tests/test_o21d_exclusion_gap.py`）✓
- ⛔ 未碰 `src/agent/correction/`、`src/agent/reading/`、`case_tests/`（我的 diff 只有 `answer_compiler.py`）✓
- ⛔ 未把阈值调到恰好容纳现状：3 cavity 靠**台账登记**放行（与阈值无关）；管井腔靠**生产阈值**（非发明数）✓
- ⛔ 已落库哈希未变（§三#6）✓ · ⛔ 未 `git add`/commit/`-e .`/`-n auto`/全量 ✓
- ⛔ `.py` 字符串常量无仓库根前缀路径（F-152）✓

## 五、⭐ 我自己认为最薄弱的一处

**唯一性判据只是「内部不相交」，对【不重叠的】幻觉挡不住。** penetration ① 的幻觉
是 z5 的**精确副本**（与 z5 完全重叠），被 overlap 拦下。但若攻击者把一个**小的、不
与任何真实 zone 重叠的**幻觉 zone 塞进那 88 m² 大 NA cavity 的空角落，它既在台账
cavity 内（`registered_ring_loss` 放行）、又不与别的 zone 相交 ⇒ **会被吸收，门不红**。
- 我考虑过的更强判据 **面积守恒**（zone 面积和 ≤ cavity 面积）**实测不可用**：z4+z5=
  32.46 m² 已经 > cavity 04e 的 28.68 m²（zone 用墙中线含半墙厚，本就比 footprint-minus-walls
  的原始 cavity 大）——用它会误杀 baseline。
- 根因是**原始 cavity 欠切分**（NA 正因为内部结构坏了没被墙劈开），所以「这个 NA
  cavity 里到底应该有几个 zone」这个上界，事实层今天给不出独立证据（台账每 cavity 只一条）。
  真正的解要等 ring 修好（F-155）后 cavity 能正常切分，届时这 3 条登记清空、问题消失。

## 六、希望复核方重点打哪里

1. **③ 唯一性的残余缺口**（§五）：小的不重叠幻觉能不能钻进大 NA cavity？请构造一个
   「面积 < cavity 且不与真实 zone 相交」的幻觉试试，看是不是我说的那样漏。若漏，这
   是否属于「必须本轮堵」还是「等 ring 修好自然消失」的范畴，请裁定。
2. **② 真实成因形态的判定**：我把「probe_r3 合成 fixture 已被 as_measured 修掉」判成
   「真实成因形态=#3（sm25 现存 3 cavity）」而没有去重造一个新的、能让**当前** derive
   仍失败又不在台账里的诚实小世界。请核这个判定对不对——是不是还有一类「当前 derive
   失败、但不该进台账」的诚实形态被我漏了。
3. **N3' 阈值语义**：我让门在**不传阈值**时对「无 ring+不在台账」的 cavity fail-loud
   （红），只有**传入生产阈值**才给次阈值腔体合法出口。真实 sm25 gate（84 锁）不传阈值
   仍绿是因为它没有 zone 指向次阈值 cavity。请核：这个「默认 fail-loud、显式传阈值才
   放行」的方向对不对，会不会在下一份方言上把按设计的次阈值腔体一律判红。
4. **台账 cavity_id 与门 cavity_id 的等价性**：我论证两套 `_opaque_id` 逐字节相同所以
   可跨模块按 id 匹配。请独立核这个等价（若哪天 as_measured 的 cavity 排序/量化变了，
   门就会静默匹配不上、把已登记的 cavity 当成静默豁口误红）。
