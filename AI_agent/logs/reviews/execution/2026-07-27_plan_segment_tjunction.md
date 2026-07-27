# 执行日志 · 平面判卷器 T 型接头配对修复（2026-07-27）

- **施工** = GLM-5.2（本席）
- **派工单** = `AI_agent/logs/reviews/request/2026-07-27_plan_segment_tjunction_glm_dispatch.md`
- **范围裁定** = 主控 Opus 5 已定（R-1…R-5），施工方不改
- **改的文件** = `src/agent/judge/segment_score.py`（生产码）+ `tests/test_c2_segment_tjunction.py`（新增测试）
- **禁区** = 全部遵守：未碰 `case_tests/**`、`AI_agent/**`（仅本日志）、`.gitignore`、`run_2026-07-27_haiku_e2e/`；未放宽任何容差、未换绿任何既有断言、未加 skip/xfail；neuter 只在 `/tmp` 副本做，工作树零 neuter 残留。

---

## 0. 派工单前提核实（动手前先做，未发现前提有误）

把真实 `case_tests/test_baseline/gt/sm24_anchor/gt.json` 的 F1 层 8 区逐边解析：

- **有向内墙边总数 = 38**（与派工单 §1.1 逐字一致）。
- 共形精确配对 = 7 条（14 条半边）；外墙独占 = 12 条半边；**配不上 = 12 条半边**（与派工单"12 条配不上"一致）。
- 典型 T 型接头：x=4.18 线上 z5 的长西墙 `(4.18,15.94)→(4.18,3.44)`，对面 z0/z1/z2/z4 的东/西墙在其上交错——**且两侧都是未切分的长边**（z0 单边 `[0,8.06]` 未在 3.44 处断开，z5 单边 `[3.44,15.94]` 未在 8.06/13.0 处断开）。即真实形态比派工单描述的"一长对多短"更强：是 **M 长对 N 长、接头错位**。算法必须按此一般情形设计（见 §1）。
- x=4.18 线经切分应得到 4 段：z0↔z4 `[0,3.44]`、z0↔z5 `[3.44,8.06]`、z1↔z5 `[8.06,13]`、z2↔z5 `[13,15.94]`。

**前提完全属实，无误差，按派工单施工**（未触发"停下上报"）。

## 1. 改了什么 / 为什么

### 病根（派工单 §0）
平面判卷器假设内墙两侧顶点完全对齐（conforming mesh）。真实建筑里一条长墙对着若干进深不等的房间，对面被切成多段，于是两侧顶点不对齐：

| 侧 | 位置 | 旧行为 | 后果 |
|---|---|---|---|
| 答案侧 | `extract_gt_plan_segments` | 抛 `score_gt_identity_invalid`/`invalid_interior_edge_pair` | 整个 case 判不了（sm24 实测撞死） |
| 产品侧 | `extract_correction_plan_segments` | 静默 `continue` 跳过 | 走廊墙从不进观测集 ⇒ 全算漏画 = **假红** |

### 修法
新增**一个共享切分 helper** `_pair_interior_edges`，两侧 extract 函数都调它（R-4 同一套判据）。

**helper 算法**（照 `_lies_on_exterior` 风格——精确同直线 + 精确区间覆盖，零容差）：

1. 把同层所有有向内墙边按**支撑正交线**分桶（key = `("V", x)` 或 `("H", y)`，精确坐标相等才算同线），再按走向分 **forward / reverse** 两侧（CCW 多边形在墙两侧反向遍历，故两侧自然落入不同走向）。
2. 对每条线，取 forward ∪ reverse **所有端点的并集**排序，切出**基本子区间**。
3. 对每个基本子区间 `[lo, hi]`：
   - forward 有 1 主、reverse 有 1 主、**不在外墙** → 一道内墙，`zone_ids = sorted(fwd, rev)`，发一条 segment。
   - 两侧都有主 **但在外墙** → 抛 `exterior_interior_topology_conflict`（R-3 冲突）。
   - 任一侧 ≥2 主 → 抛 `invalid_interior_edge_pair`（**重叠**，R-3）。
   - 只有一侧有主、**不在外墙** → 抛 `invalid_interior_edge_pair`（**缺口/洞**，R-3）。
   - 只有一侧有主、**在外墙** → 跳过（外墙由 boundary_segments / footprint 段计分）。
   - 两侧都无主 → 跳过（开间，如走廊东口，不是墙也不是洞）。

**精确性**（R-2 禁吸附禁容差）：共线靠精确坐标相等分桶；覆盖靠精确端点比较 `left <= lo and hi <= right`。任何缺口/重叠/端点不精确都会作为一个基本子区间被 1/3、4 两条判据捕获并报错。未引入任何几何容差，未改 `JudgeScoreConfigV1` 任何阈值，未碰 `_candidate`。

### 接线
- **答案侧** `extract_gt_plan_segments`：删掉旧的逐边 exact-reverse + consumed 循环，改调 helper（`identity_code="score_gt_identity_invalid"`）。覆盖不全仍抛原错误码（R-3）。`interior:` key 用子区间 `min/max` 端点，保证同层唯一（R：派工单 WP-2）。
- **产品侧** `extract_correction_plan_segments`：**删掉静默 `continue`**（R-4），改调同一 helper（`identity_code="score_product_identity_invalid"`）。切分成功 → 走廊墙进入观测集；切分失败（真洞/重叠）→ 按产品侧既有失败语义抛 `score_product_identity_invalid`，**不静默丢弃观测**。

### 为什么这同时保住既有不变量（R：派工单 §1.4 / 锁 6）
共形 exact-reverse 对是本算法的退化特例（forward/reverse 各一条同区间 → 一个基本子区间 → 一对），故 `test_b4b_r1_gt_interior_pairing_and_invariant_raises` 的三段（共形正例 / 不铺满→`invalid_interior_edge_pair` / 内外冲突→`exterior_interior_topology_conflict`）原样通过，**断言未改一字**。

## 2. 七条必红锁 + neuter 自查表

新增 `tests/test_c2_segment_tjunction.py`，锁 1/2/3/4/5/7 为新增；**锁 6 = 既有两条不变量锁（`test_b4b_r1_gt_interior_pairing_and_invariant_raises`）原样通过，未改其断言**。

**neuter 自查方法**：复制真实 `segment_score.py` 到 `/tmp/segment_tjunction_neuter/`，对每条承重代码施加定向 neuter，`importlib` 加载副本跑全部 6 场景，验证"摘掉即翻盘"。**工作树全程未改**（`grep -c "NEUTER\|round(p1" src/agent/judge/segment_score.py` = 0）。

| 锁 | 场景 | 基线结果 | 指定 neuter | neuter 后 | 翻盘? |
|---|---|---|---|---|---|
| **L1** T 正例 | 长边对 4 共线短边 | green（7 段：4 走廊 + 3 房间间） | `neuter_split`（切点只取 forward 端 → 长边无法切分） | **red**（抛 `invalid_interior_edge_pair`） | ✅ |
| **L2** 真实 sm24 | 吃真实签字 GT | green（16 段，零报错） | `neuter_split` | **red**（抛错） | ✅ |
| **L3** 缺口 | 对面有缝 `[5,6]` | red（`invalid_interior_edge_pair`） | `neuter_hole`（关一侧无主非外墙的 raise） | **green**（缝被跳过，假绿） | ✅ |
| **L4** 重叠 | 两 zone 占同一条内墙边（dup-edge） | red（`invalid_interior_edge_pair`） | `neuter_overlap`（关 `len!=1` raise） | **green**（重叠被当 pair 发出，假绿） | ✅ |
| **L5** 端点差 1mm | 对面 `[0,5]`+`[5.001,10]` | red（`invalid_interior_edge_pair`） | `neuter_tolerance`（坐标圆整到 1cm） | **green**（1mm 缝被圆整合拢，假绿） | ✅ |
| **L7** 产品侧 | 同 L1 的 T 接头喂 correction | green（走廊墙进观测集） | `neuter_split` | **red**（抛 `score_product_identity_invalid`） | ✅ |
| **L6** 既有两条不变量 | 不铺满→红 / 内外冲突→红 | red / red | —（既有用例，断言未改） | 原样通过 | ✅（未弱化） |

**全部 6 新锁在指定 neuter 下翻盘；锁 6 既有断言原样通过。** 无 false-lock。

**neuter 矩阵交叉效应（诚实登记）**：
- `neuter_hole` 同时翻 L3 与 L5 —— 预期内：L5 的 1mm 缝本质也是"一侧无主非外墙"洞，故关洞检查会同时放过两者。L5 的**指定** neuter 是 `neuter_tolerance`（专证"禁容差"）。
- `neuter_tolerance` 同时翻 L5 与 **L2（sm24）**。L2 翻盘的机理是：我只圆整了 zone 边坐标、没圆整 footprint 边，而 sm24 的 footprint 顶边存的是浮点噪声值 `y=19.999999999999996`（源于 20.0）；圆整把 zone 北墙挪到 `y=20.0`，与原始 footprint 边不再精确相等 → `_lies_on_exterior` 认不出是外墙 → 误判为洞 → 抛错。**这恰好反向证明"禁容差"为何必须**：基线靠 zone 边与 footprint 边共享**同一浮点值**（精确相等）才工作，任何圆整都会扰动它。L2 的指定 neuter 是 `neuter_split`（干净翻盘），`neuter_tolerance` 翻 L2 是诚实的交叉效应、且强化结论。
- L4 用 **dup-edge 夹具**（两 zone 占同一条内墙边）而非"两矩形面积重叠"：后者会连带产生未覆盖边→触发洞检查而非重叠检查，使 `neuter_overlap` 翻不动；dup-edge 才能纯净触发 `len!=1` 重叠守卫。已在测试注释说明。

## 3. 跑测纪律（[codex_execution_protocol §7.5]）

- **跑测声明（中间轮）**：受影响子集由 `scripts/tool_scripts/affected_tests.py --changed src/agent/judge/segment_score.py tests/test_c2_segment_tjunction.py` 算出，禁自由裁量：
  ```
  SCOPE: SUBSET
  tests/test_affected_tests_map.py tests/test_audit_remediation_accepted_inputs.py tests/test_c2_b4b_contract.py
  tests/test_c2_b4b_phase_b.py tests/test_c2_b4b_phase_c.py tests/test_c2_b4b_phase_d.py
  tests/test_c2_b5_parent_and_verts.py tests/test_c2_segment_tjunction.py tests/test_judge_batch_b.py tests/test_run_stage_flow.py
  ```
  结果：**185 passed**（warnings 为既有 `run_config.yaml` 测试夹具运行时提示，与本改动无关）。

- **交付前全仓 `pytest -q` 原始输出**（零回归唯一依据）：
  ```
  1677 passed, 10 xfailed, 150 warnings in 232.95s (0:03:52)
  ```
  基线 = `1671 passed / 10 xfailed / 0 failed / 0 skipped`。本批新增 6 条测试（L1/2/3/4/5/7），`1671 + 6 = 1677`，**零回归、零 skipped、xfail 不变（10）**。150 warnings 全部是 `record_baseline.py`/`run_stage.py` 在测试夹具里 `run_config.yaml missing` 的既有 RuntimeWarning，与本改动无关（中间轮子集同样出现）。exit code = 0。

## 4. 未竟项 / 诚实披露

1. **R-1 分母口径回写未做（按派工单裁定属主控收口动作）**：派工单 R-1 明确"判卷分母 = 切分后的段数"由主控在收口时回写 `AI_agent/architecture/judge_grade_model.md`，**施工方不改 `AI_agent/**`**。本批已按此口径实现（切分后每子区间一条 segment，进入 `_canonical_geometry` 排序与下游 `assign_plan_segments`/`score_plan_segments` 计分），但规格文档回写不在本席范围。请主控收口时确认：切分后段数变多 ⇒ 分母变大 ⇒ 同一绝对偏差的相对分数变化，这与 R-1 裁定一致。
2. **非正交边按违约处理**：helper 对非正交边（既非纯 x 又非纯 y）直接抛 `invalid_interior_edge_pair`。理由：本判卷器 `geometry_profile = "c2_simple_orthogonal_no_holes"`，`_lies_on_exterior` 本就只认正交；GT/correction 多边形均经验证正交。所有现存测试夹具均为正交，未触发。若未来引入斜边需另立口径（属不变量 #6 复杂度升级接缝，非本批）。
3. **sm24 真跑未做**：派工单触发是 `run_2026-07-27_haiku_e2e` 挂起，禁区明令"修好后主控接着跑"。本批只修判卷器并加锁，**未触碰该 run 目录、未重跑端到端**。判卷器侧已用真实 sm24 GT 活体证明不再抛错（L2）。
4. **产品侧失败语义为新增（非既有）**：派工单 R-4 要求"产品侧不得保留静默跳过分支……按产品侧既有失败语义处理"。产品侧原本对内墙无失败语义（只有静默 `continue`）；本批把"真洞/重叠"映射到产品侧既有的 `score_product_identity_invalid` 错误码（与 `coerce_plan_observations` 同码）。合法 correction（共形或 T 接头、铺满 footprint）不会触发；仅畸形 correction（非铺满）才会抛。请审阅方确认此映射符合 R-4 意图。
5. **执行日志只此一份**：本席在 `AI_agent/` 下仅写本日志；`AI_agent/plan.md` 的改动是会话开始前既有（非本席所动，`git status` 起始即为 M）。

## 5. 产物指针

- 生产码 diff：`src/agent/judge/segment_score.py`（+`_pair_interior_edges` helper；两侧 extract 改调它；产品侧删静默 `continue`）。
- 新增测试：`tests/test_c2_segment_tjunction.py`（6 锁）。
- neuter harness（过程件，在 `/tmp`，未入仓）：`/tmp/neuter_harness.py` + `/tmp/segment_tjunction_neuter/`。
- 待主控：对抗审派 GPT 侧 sol（谁写谁不批，跨家族）；R-1 规格回写；sm24 端到端续跑。

---

# r1 返工段（2026-07-27，REWORK 后续作）

承接 sol 对抗审 REWORK（[verdict](../verdict/2026-07-27_plan_segment_tjunction_sol.md) §5 必做项 1/2/4/5）。**必做项 3（Y-2 分母语义重裁）属 B 批**，本批**不动** `score_policy`/`assign_plan_segments`/`score_plan_segments` 计分口径，**不回写 R-1 到任何架构文档**。主控三条裁定 RW-1/2/3 已照办；前提核实无误（未触发「停下上报」）。

## r1.0 范围 / 禁区
- **做**：① 数值身份合同（RW-1）② 非正交接缝错配（RW-2）③ exterior-only 多 owner 守卫（RW-3）④ 产品侧测试升级（L-f）。
- **不做**：Y-2 分母语义（B 批，另单）。
- 禁区遵守：未碰 `case_tests/**`、`AI_agent/**`（仅本日志续写）、`.gitignore`、`run_2026-07-27_haiku_e2e/`；未放宽容差、未换绿既有断言（Lock4 见 r1.6 连带说明）、未加 skip/xfail；neuter 只在 `/tmp`。

## r1.1 RW-1 数值身份合同（表示层规范化，**非几何容差**）
**病根**（活体复现 `/tmp/sm24_false_red_probe.py`）：scorer 把 binary float 当拓扑身份。同一十进制接缝 z0 写 `8.059999999999999`、z1 写 `8.06`（差 ~9e-16）→ 落进不同支撑线桶 `(H,8.059999999999999)` vs `(H,8.06)` → 单侧悬空假红 `invalid_interior_edge_pair`；而 `validate_gt_v3._ring_vertices` 只查**单 zone 边**正交（每条边 dx/dy）、不查**跨 zone 接缝一致** → GREEN。两者错配 = 假红。correction 侧 `0.1+0.2`(=0.30000000000000004) vs `0.3` 同型。

**修法**：scorer 入口对所有顶点做一次可审计规范化 `_canonical_coord(v)=round(v/QUANTUM)*QUANTUM+0.0`，GT/correction **同函数同参数**（`_points` 统一入口 + `extract_*` 的 boundary_segments/footprint + `coerce_plan_observations` 三处都过它），规范化后**一切比较仍精确**（`==`/`<=`），禁止近似比较、禁止配对/覆盖加容差。

**量子 = 1e-12**。分离度证明（`/tmp/canonical_probe.py` 实测）：
- `ulp(20m) = 3.55e-15` → `quantum/ulp = 281`（显著大于，吸收几个 ulp 的表示噪声）；
- `1e-9` 端点缺口 = `1000 quantum`（显著小于，缺口仍判红，见 L-c）；
- 幂等 + `-0.0` 卫生（`+0.0` 把 `-0.0` 归零，不污染 dict key/tuple 比较）。
对标既有先例 `FACADE_VISIBILITY_DEPTH_EPSILON=1e-9`（`A0_contract.md`「absorbs only IEEE-754 arithmetic noise … not a physical resolution」）。代码注释 + 本日志均明写「这是表示层规范化、不是几何容差」。

**活体反例（修复前 RED → 修复后 GREEN）**：
- 反例 A 真实 sm24（z1 底边 `8.059999999999999`→`8.06` + 重算 `content_sha256`）：validator GREEN / 旧 scorer RED(`invalid_interior_edge_pair`) / 新 scorer GREEN(16 interior)。
- 反例 B typed correction（A 右边 `0.1+0.2`、B 左边 `0.3`）：`cell_polygon_contract`+`coverage` GREEN / 旧 scorer RED / 新 scorer GREEN(1 interior)。

## r1.2 RW-2 非正交边（Y-1）—— 选① exact-reverse 退化路径
**二选一**：选①（恢复非正交精确反向配对），不选②（独立能力错误码 + 证明上游先拒）。**理由**：correction 侧上游 `cell_geometry._EPS=1e-9` 判正交（`dx>_EPS and dy>_EPS`），放行 `dx<1e-9` 的近正交边（如 `dx=5e-10`）→ 方案②「上游先拒⇒不可达」对 correction 侧**不成立**（GT 侧 `_ring_vertices` 虽精确判正交会先拒，但两侧口径不一致，scorer 不能把 validator 放行的合法几何另行解释成拓扑破坏——否则就是 RW-2 点名的错配）。

**修法**：`_pair_interior_edges` 分流——正交边（`p1[0]==p2[0]` 或 `p1[1]==p2[1]`）进 `_tile_orthogonal_edges`（原 T 切分逻辑）；非正交边进新 `_pair_general_edges`（exact-reverse 配对：一条 directed edge 配其精确反向 `(p2,p1)`；找不到反向 / 同向多 owner → `invalid_interior_edge_pair`）。footprint/exterior 正交（上游验证），非正交边永不在 exterior，exterior/interior 冲突检查在此路径不可达、故意省略。**不变量 #6 升级接缝注释已留**：C2 今只启用正交 T 切分，未来非正交 profile 在 `_pair_general_edges` 扩展无需推翻 API。

## r1.3 RW-3 helper 合同漏洞 —— 补守卫变红（方案 A）
**病根**：两 zone 都 = 完整 footprint，所有边都在 exterior、同向重复 → 旧版 exterior-only 单侧分支静默跳过 → GREEN、0 interior（漏洞）。

**选 A（补守卫变红）而非 B（收窄合同 + 证明入口先校验）**：上游 coverage 是**面积级**容差（`coverage_area_tol_m2`），helper 是**边级**拓扑，两层不同；方案 B「证明所有入口先做 owner multiplicity 校验」不够严密（面积级放行不蕴含边级正确）。

**修法**：`_tile_orthogonal_edges` 的 exterior-only 单侧分支补守卫——某子区间只一侧有 owner、`on_exterior`、且该侧 `owner>1` → 抛 `exterior_duplicate_owner`。合规 tiling 每条 exterior 边每侧恰 1 owner（zone 不重叠铺满），合法情况不误伤（Lock1/L2/L7 的 exterior 边均单 owner）。**注释明写**：此守卫**只**捕「exterior-only 同向多 owner」这一具体形态，**不**宣称 helper 自身「overlap 一律红」（面积级 zone overlap 是上游 coverage validator 职责，另一层）—— 对标 07-26 GLM 抓的 Y-06「声称大于实况」同型禁令。

## r1.4 锁 L-a…L-f + Y-1（`tests/test_c2_segment_tjunction.py` 追加 8 测函数；L-f 验收项拆合法 assignment / 失败语义两测）

| 锁 | 场景 | 期望 | 守卫 |
|---|---|---|---|
| **L-a** 真实 sm24 变体 | z1 底边 `8.059999999999999`→`8.06`、重算 hash | validator GREEN **且** scorer GREEN(16) | RW-1 规范化 |
| **L-b** typed correction | A 右边 `0.1+0.2`、B 左边 `0.3` | validate GREEN **且** scorer GREEN(1) | RW-1 规范化 |
| **L-c** 1e-9 端点缺口 | A[0,10] 对 B[0,5]+C[5+1e-9,10] | RED `invalid_interior_edge_pair` | 量子分离度 + one-sided |
| **L-d** 单侧悬空 | 长边对侧只盖一半 | RED `invalid_interior_edge_pair` | one-sided interior |
| **L-e** exterior 多 owner | 两 zone 都 = footprint | RED `exterior_duplicate_owner` | RW-3 守卫 |
| **Y-1** 非正交 exact-reverse | 两 cell 共享 `dx=5e-10` 反向边 | GREEN(1) 配对 | RW-2 退化路径 |
| **L-f** 产品侧完整 | 合法 T 接头 assign+score | 0 unmatched / 全 complete；缺口→RED `score_product_identity_invalid` / 浮点→不假红 | 全链 |

## r1.5 neuter 独立性自查（`/tmp/neuter_independence_probe.py`，**如实披露共用守卫**）

| neuter（摘掉即翻盘） | 翻转的锁 | 守卫 | 独立性 |
|---|---|---|---|
| `_canonical_point`→identity | **L-a, L-b** | A（RW-1 规范化） | **L-a、L-b 共用此守卫** |
| `quantum`→1e-8 | **只 L-c** | B（量子分离度） | L-c 独立视角 |
| 删 one-sided raise | **L-c, L-d, Lock3** | C（one-sided interior） | **三者共用此守卫** |
| 删 ext_dup raise | **只 L-e** | E（RW-3 exterior dup） | 独立 |
| 删 interior_overlap raise | 无翻转 | D | Lock4 实由 E 承重 |
| `_pair_general_edges`→raise | **只 Y-1** | F（RW-2 exact-reverse） | 独立 |

**承重锁归并（返工单「共用守卫须合并说明」）**：
- **承重锁 1（RW-1 规范化，守卫 A）** = L-a（GT 活体）+ L-b（correction 活体）**两个反例**，neuter 同时翻两者 —— 是同一承重锁，不是两条独立锁。
- **承重锁 2（one-sided interior，守卫 C）** = L-c（1e-9 gap）+ L-d（dangling）+ Lock3（gap）**三种缺口形态**，neuter 同时翻三者 —— 同一守卫。L-c 另有守卫 B（量子）的独立视角（neuter quantum 只翻 L-c）。
- **承重锁 3（RW-3 exterior dup，守卫 E）** = L-e，独立。
- **承重锁 4（RW-2 exact-reverse，守卫 F）** = Y-1，独立。
- **守卫 D（interior_overlap）无锁独占承重**：Lock4（dup B）neuter D 后仍由守卫 E 承重（exterior 边也同向重复），印证 Lock4 现 reason=`exterior_duplicate_owner`（见 r1.6）。

上一轮把共用守卫的三条记成独立承重锁被点名；本轮按返工单如实归并披露，不重复该错。

## r1.6 连带效应：Lock4 断言更新（**非换绿**）
dup B（C 完全=B）现在遍历到 exterior 桶（y=0 等）时先命中 RW-3 守卫报 `exterior_duplicate_owner`，而非旧的 interior overlap `invalid_interior_edge_pair`（x=2 内墙双 reverse owner）。Lock4 **仍红**（未换绿），断言改为接受 `{invalid_interior_edge_pair, exterior_duplicate_owner}` 并注释「dup B 同时命中 interior overlap 与 exterior dup 两守卫，reason 取遍历顺序」。纯 exterior-only 形态另由 L-e 独立锁定。

## r1.7 跑测（[codex_execution_protocol §7.5]）
- **中间轮受影响子集**（`affected_tests.py --changed src/agent/judge/segment_score.py tests/test_c2_segment_tjunction.py` 算死）：10 文件，**193 passed**（warnings 为既有 `run_config.yaml` 夹具运行时提示，与本改动无关）。
- **交付前全仓 `pytest -q`**：
```
1685 passed, 10 xfailed, 150 warnings in 269.18s (0:04:29)   exit code = 0
```
基线 = `1677 passed / 10 xfailed / 0 failed / 0 skipped`（r0 终态）。本批新增 **8 测函数**（L-a/b/c/d/e + Y-1 + L-f 合法 assignment + L-f 失败语义；返工单 L-f 验收项拆 happy/sad 两测），`1677 + 8 = 1685`，**零回归、零 skipped、xfail 不变（10）**。150 warnings 全是 `record_baseline.py`/`run_stage.py` 在测试夹具里 `run_config.yaml missing` 的既有 RuntimeWarning，与本改动无关（中间轮子集同样出现）。

## r1.8 产物指针
- 生产码：`src/agent/judge/segment_score.py`（+`_COORDINATE_QUANTUM`/`_canonical_coord`/`_canonical_point`；`_pair_interior_edges` 分流 `_tile_orthogonal_edges`+`_pair_general_edges`；RW-3 exterior dup 守卫；入口规范化三处接线）。
- 测试：`tests/test_c2_segment_tjunction.py`（+L-a/b/c/d/e + Y-1 + L-f×2；Lock4 断言更新）。
- 探针（`/tmp`，未入仓）：`canonical_probe` / `sm24_false_red_probe` / `three_repro_probe` / `verify_fix_probe` / `typed_and_product_probe` / `product_probe` / `neuter_independence_probe`。
- 待主控：对抗审派 GPT 侧 sol 复审（谁写谁不批）；B 批 Y-2 分母语义重裁（另单）。
