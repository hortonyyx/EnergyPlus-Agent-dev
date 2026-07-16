# B4a Phase B 施工执行审判词 r1(2026-07-15)

- **审向**:Opus 升一档执行审(terra 施工 → Claude 侧审,谁写谁不批)→ 主控轻门。
- **需求基准**:`AI_agent/proposals/c2_b4a_detail_spec.md` v2(唯一合同;§8/§9/§10 Phase B 界内/§13 Phase B 行/§14)+ 派单 `AI_agent/logs/reviews/request/2026-07-15_b4a_phaseB_construction_dispatch.md`(含 PA-R1/PA-R2 挂账束)。
- **审的产物**(基座 HEAD `526c38e`,均未 commit):重写 `scripts/tool_scripts/inspect_dxf.py`(+~100 行 CLI/preflight)、新增 `src/agent/judge/gt_extraction.py`(359 行)、`src/agent/judge/gt_schema.py`(挂账 3 hunk)、新增 `tests/test_gt_extraction.py`(98 行/5 测)、`tests/test_gt_schema.py`(+~80 行/36→46 测)。
- **信任边界**:仅依据合同原文、代码/测试实体、本审自跑测试与 scratchpad 活体探针;简报仅用于定位。B4b 车道文件(run_stage/score_*/judge_score.yaml 等)未审未动。

---

## 总裁决:REWORK

plan 核心几何链质量高——manifest 绑定、snap/polygonize/seed 选面/zone tiling/ancestry 全部 fail-closed(本审七路探针证实),无 largest-bbox fallback,inspector CLI 的 exit-code/写保护合同实测正确(0/2/3、protected 根/已存在/symlink 全拦、无半文件、重复运行 hash 相同),零资产扰动,Phase A 回归全绿——但一条**静默错真值**的正确性洞(centerline)、一条合同点名检查整体缺失(view-overlap)、派单负测矩阵 8 类只落 2 类且简报报"偏差:none"(VA-C2/PA-C2 同型第三现)、一个 A0 已登记容差全程死参数,合计 4 MAJOR 触发 REWORK。

**severity 计数**:BLOCKER 0 · MAJOR 4 · MINOR 4 · NIT 1(束)。

---

## 逐条 findings

### PB-C1 —— MAJOR:centerline manifest 被静默当 outer_skin 处理,产出错误 footprint(探针坐实)

`src/agent/judge/gt_extraction.py` 全文无 `boundary_reference`/`default_wall_thickness_m`/centerline 任何处理(grep 零命中)。**本审活体探针**:构造 `boundary_reference="centerline"` + `default_wall_thickness_m=0.24` 的合法 manifest,`extract_plan_geometry` **NO-RAISE**,返回未偏移的原 centerline 环 `[[0,0],[4,0],[4,3],[0,3]]`(合同 §10.3.4 应外偏 0.12m 得 outer-skin,或按 §8.2 W5 语义拒绝)。这是本批唯一"静默产出错真值"级别的洞——不是 fail-closed 缺测试,而是 fail-open。§10.3 footprint polygonization 属派单点名的 Phase B 界内(§10 "单位/view region/snap/polygonize/zone 分割");即便主控裁决 centerline 偏移算法留 Phase C,Phase B 也**必须对 `centerline` manifest 以稳定错误码拒绝**,不得静默按 outer_skin 出几何。修法小:入口处 `if view.boundary_reference != "outer_skin": _fail("dxf_centerline_unsupported_in_phase_b")` 或落全 §10.3.4。

### PB-C2 —— MAJOR:§8.2 view clip-box 交叠检查完全缺失(manifest 与 extraction 两侧均无;探针坐实)

合同 §8.2 约束原文:"view clip boxes 先按 unit scale 转 source-m 后,交叠面积不得超过 topology area tolerance"。`gt_manifest.py:_manifest_contract` 不查;`gt_extraction.py` 的 inspect/extract 均不查。**本审探针**:两个 plan clip box 在 source-m 交叠 10 m²(>> 1e-6 tolerance),manifest `model_validate` 接受,`inspect_extraction_inputs` 返回 **PASS 零 issue**,`extract_plan_geometry` 正常出两层几何。交叠区若含实体,当前靠 `dxf_entity_clip_ambiguous`(实体跨界)偶然兜住;交叠区为空时完全无声——§10.2.3 "被真值规则引用的实体必须完全落入唯一 view" 的唯一性前提失去结构保证。view-overlap 同时是派单负测矩阵点名类,测试同缺。

### PB-C3 —— MAJOR:派单负测矩阵 8 类只落 2 类 + inspector CLI 合同零测试 + 简报"偏差:none"未列缺口(VA-C2/PA-C2 同型第三现)

派单原文:"dangle/cut/bulge/proxy/unit/hash/view-overlap/seed ambiguity 负测"与"`tests/test_inspect_dxf.py` 扩展";"确有未竟逐条列明,不得静默"。实况(`tests/test_gt_extraction.py` 全 5 测逐一核对 + 本审探针):

| 负测类 | 实现 | repo 测试 | 本审探针 |
|---|---|---|---|
| dangle | ✓ | ✓ `test_plan_preflight_rejects_residual_or_bulge[kwargs0]` | — |
| bulge | ✓ | ✓ 同上 `[kwargs1]` | — |
| cut | ✓(polygonize_full 残留同码) | **缺** | — |
| proxy | ✓(且范围过宽,见 PB-C6) | **缺**(全仓无 proxy fixture) | — |
| unit | ✓ | **缺** | mm-DXF vs m-manifest → BLOCKED `dxf_unit_mismatch` ✓ |
| hash | ✓ | **缺**(extraction 路径;manifest 自 hash 拒属 Phase A 旧测) | 篡改源文件 → BLOCKED `dxf_source_hash_mismatch` ✓;篡改 manifest_sha256 → pydantic 拒 ✓ |
| view-overlap | **缺**(PB-C2) | **缺** | 交叠 10m² → PASS(洞) |
| seed ambiguity | ✓ | **缺** | seed 出界 → `dxf_footprint_seed_ambiguous` ✓;双 seed 同 face → `dxf_zone_seed_ambiguous` ✓ |

另:`tests/test_inspect_dxf.py` **一行未动**(2 个旧测全是 legacy `inspect()`;重写后的 `main()` CLI 合同——exit 0/1/2/3、无 manifest UNBOUND、`--json-out` 新建/protected 根/symlink 拒——**零测试覆盖**,行为全靠本审 CLI 探针证实正确)。§14.2 其余 Phase B 界内行(LINE network 与闭 LWPOLYLINE 等价、短边/斜边/链式 snap、clip 边界实体、selector count/zone-seed drift)同样零测试。简报"验收与测试"报 78 passed(数字准确)但"偏差:none"——缺口未逐条列明,与 Va/Phase A 两批同型。抓手价值:PB-C1/C2/C6/C8 四个实现级偏差恰全部藏在未测轴里。

### PB-C4 —— MAJOR:`dxf_axis_alignment_tolerance_m` 全程死参数,axis project-or-block 误用 node_join 容差

合同 §10.2.5:"若 `abs(dx)<=axis_tol < abs(dy)` 则投竖直……两差均小于等于容差是短边 block,两差均大于容差是斜边 block"——axis_tol 是与 node_join 分立的容差;A0 §8.4 已登记 `GT_DXF_AXIS_ALIGNMENT_TOLERANCE`"hard project-or-block"。实况:`gt_extraction.py:193-217 _snap_segments` 的聚类**与**轴投影/短边/斜边四分支全部使用同一个 `tolerance` 形参,两处调用点(`:307/:331` 等)只传 `dxf_node_join_tolerance_m`;`dxf_axis_alignment_tolerance_m` 在 extraction 全文零消费(grep 证实,仅存在于 schema `_relationships`)。判定逻辑形状与合同逐句一致、**当前 profile 两值恰同为 0.001 故今日行为无差**,但:①A0 registry 声称的 hard gate 实际未接线(可审计容差面失真,项目硬纪律);②profile v2 若单调任一值,snap 与 axis 语义将无声绑死漂移——正是 07-05 大审 "win_tol 死参数" 同型。修法一行级:`_snap_segments` 拆双容差形参,聚类用 node_join、四分支用 axis_alignment,调用点补传。

### PB-C5 —— MINOR:inspection report 的 dangle/cut/invalid_ring 计数恒写死 0,BLOCK 时诊断自相矛盾

§9.2.4:"报告 polygons/dangles/cuts/invalid rings;任一残留为阻断"——wire 专设三个 count 字段。实况 `gt_extraction.py:312/:315`:成功路径与 BLOCK 路径均硬编码 `dangle_count=0, cut_count=0, invalid_ring_count=0`(`_polygonize` 一见残留即抛,计数丢弃)。dangle DXF 的 report = status BLOCKED + issue `dxf_polygonize_residual` + **dangle_count=0**——阻断正确但诊断 wire 撒谎,human review 拿不到"几条残线"。修法:`_polygonize` 返回或带出 `len(dangles.geoms)` 等计数再决定 fail。

### PB-C6 —— MINOR:proxy 阻断范围过宽——全 modelspace 计数,view 外 proxy 也 BLOCK(合同:view 外只 INFO)

§9.2.2/§10.2.2:bound view **内** proxy/custom object 阻断;"view 外对象只列 INFO,不进入真值"。实况 `gt_extraction.py:298/:316-317`:`proxy_count` 对整个 modelspace 求和,`manifest 存在 ⇒ severity="BLOCK"`,不看位置。真实合并 TArch 图签/图框 proxy 几乎必在 clip box 外——现实现会把本可提取的图纸整体 BLOCKED。方向是 fail-closed(不产错真值)故仅 MINOR,但与合同明文相反且直接影响真实 sm25/26 可用性。

### PB-C7 —— MINOR:§10.4.2 seed 距边最小距离(> node-join)未实施(探针坐实)

合同:"每个 manifest zone seed 必须严格落在唯一 face interior,**距任何边大于 node-join tolerance**"。实况 `gt_extraction.py:333/:344` 仅 `face.contains(Point(...))`。**探针**:seed 距 zone 边 0.1mm(< 0.001m)→ NO-RAISE 正常出几何。边缘 seed 在容差内属两可归属,合同要求拒。

### PB-C8 —— MINOR:clip 边界触碰实体被静默排除(合同:必须 fail;探针坐实)

§9.2.3:"落在 clip 边界上的歧义实体;clip 边界触碰需 fail,不能按实体中心随意归侧"。实况 `_inside`(`gt_extraction.py:129-131`)全严格不等号:实体**部分**在内部分在界上/界外 → `dxf_entity_clip_ambiguous` ✓;但实体**整体恰在** clip 边界线上 → `not any(membership)` → 静默跳过。**探针**:ZONE 层线段完整落在 clip ymin 线上 → 无声排除,extraction PASS。若该实体恰是 selector 目标,只会以间接的 count mismatch 或错几何显形。修法:membership 三值化(inside/on-edge/outside),on-edge 即 fail。

### PB-C9 —— NIT(束)

①CLI 把完整 report 先打 stdout 再做 `--json-out` 写保护检查(`inspect_dxf.py:main`):json-out 被拒时 stdout 已有一份 status=PASS 的 report + exit 3,调用方若只看 stdout 会误读(建议先验参再输出);②BLOCK 路径 `ezdxf.readfile` 双读同文件(`gt_extraction.py:297`);③`_UNITS` 表缺 ft(INSUNITS=2)——合法 ft DXF 恒 `dxf_unit_mismatch`(fail-closed 但错因,manifest Literal 却含 "ft");④PA-R2① "self-touch 拒例"名不副实:param6 的 L 环实际以 `gt_hash_footprint_mismatch` 拒(fingerprint 漂移,row 3/4 已有覆盖),真 self-touch(重访顶点)本审探针证实由 `gt_polygon_repeated_vertex` 拒但零 repo 测试;Inf 拒(wire 层探针 ✓)同零测试——简报该两项属过报;⑤PA-R2② 双 zone 歧义 host repo 测例仍缺(r2 探针已证行为正确,固化仍欠);⑥`_write_report` exists-check 与 `os.replace` 间有 TOCTOU 窗(mkstemp 原子性只保无半文件,不保不覆盖竞态新建文件);⑦CLI 以全零 `GtImplementationHashesV1` 填 `InspectionInputs`(report wire 无 hash 字段故今日惰性;`compute_gt_implementation_hashes` 现已可算,建议直接用真值);⑧manifest 未查 zone_id 跨 view 唯一性(§8.2 唯一性清单未点名,仅留痕,Phase C 物化 wire 时 validator 会兜)。

---

## 挂账件逐项验(PA-R1 + PA-R2)

| 项 | 裁定 | 证据 |
|---|---|---|
| PA-R1 parts 前缀写保护 + 新建 case 负测 | **CLOSED(实为 HEAD 已含)** | `gt_schema.py:688-692` parts 形状策略 + `tests/test_gt_schema.py:241-251` brand_new_case 负测(断言目录前后均未被误建)在 HEAD `526c38e` 即已存在(`git show` 证实),本批仅复核;跑绿 ✓。`inspect_dxf.py` 新增 `_protected_output` 复刻同策略并加 gt_sources 根,symlink 探针拦截 ✓ |
| PA-R2① row2 剩余拒例 + row8 两小口 | **部分** | bool(ceiling True)/NaN/CW/nonorth/hole/multipolygon(extra)+missing→None+bad JSON(`gt_wire_decode_failed`)全落 ✓;**self-touch 名不副实、Inf 缺**(PB-C9④) |
| PA-R2② 双 zone host/重复 key/plan-only 两向 | **部分** | 重复 projection key ✓ + plan-only z 非空 ✓(`test_plan_only_mismatch_and_duplicate_projection_key_are_rejected`);双 zone 歧义 host repo 测例仍缺(PB-C9⑤) |
| PA-R2③ OmegaConf.load 联合 patch | **CLOSED** | `test_gt_schema.py:219` 与 `Path.read_bytes` 锁并联,双 typed 入口在锁下走通 ✓ |
| PA-R2④ `wall_thickness_m` 删合同外默认 | **CLOSED** | `gt_schema.py:185` 改必填 nullable;pop 后 wire 拒的负测在 param 族 ✓ |
| PA-R2⑤ 死代码清除 + assert 改显式 raise | **CLOSED** | methods canonical 检查删除(本审核实其确不可达:verified 分支要求 methods 与 expected 精确相等、candidate 要求空,乱序必先撞 `gt_wire_*_verification_invalid`);`assert key is not None` → `_fail("gt_source_elevation_surface_missing")` ✓ |
| PA-R2⑥ implementation hashes 正例 | **CLOSED** | `test_implementation_hashes_are_available_once_phase_b_extractor_exists`:三组 64hex 非全零 ✓(gt_extraction.py 落地后 extractor 组可算) |
| PA-R2⑦ 错误码名义偏差留痕不改 | **CLOSED** | `gt_default_root_candidate_forbidden` 未动 ✓ |

## 施工方 review-ask 裁决

- **extraction fail-closed 行为(clip/snap/polygonize/ancestry)**:主链**正确且实测扎实**——manifest 绑定(hash/unit/selector/count)、跨界实体拒、snap 链式漂移拒(component 直径门)、短边/斜边拒、polygonize 残留/sliver 拒、多面 seed-containment 唯一选面(无 largest-bbox,token 扫描零命中)、zone 无/多 seed 拒、zone 出 footprint 拒、tiling 对称差门、逐边 ancestry 缺失拒、跨层 footprint canonical 精确等同门,全部按合同 fail-closed(七路探针+两 repo 测);**但四处合同偏差**:centerline fail-open(PB-C1)、view-overlap 未查(PB-C2)、axis 容差误接(PB-C4)、seed 距边未查(PB-C7)。
- **inspector UNBOUND/BLOCKED JSON/exit-code 合同**:CLI 行为**实测合规**——有 manifest PASS=0/无 manifest UNBOUND=2/内部错=3;`--dxf` 拒 GT 根(允许 gt_sources,合 §10.1);`--json-out` 拒已存在/gt/gt_sources/case_data(含未建目录 parts 匹配)/symlink 逃逸,原子写无半文件,report 无绝对路径,重复运行 byte-identical。**但零测试固化**(归 PB-C3),外加 stdout 先于写保护(PB-C9①)与 count 写死(PB-C5)。

---

## 测试族对账表(合同 §13 Phase B 验收 + §14.2 Phase B 界内行 → 落点)

| # | 要求 | 落点 | 裁定 |
|---|---|---|---|
| 1 | 合成 L/U 两层 footprint+zones 正例 | `test_extracts_two_floor_l_or_u_plan_with_manifest_ancestry`(L 6 顶点/U 8 顶点 ×2 层,ancestry source_id 断言,跨层 footprint 等同断言) | **已落** |
| 2 | dangle 负测 | `test_plan_preflight_rejects_residual_or_bulge[kwargs0]` | **已落** |
| 3 | bulge 负测 | 同上 `[kwargs1]` | **已落** |
| 4 | cut 负测 | —— | **缺**(实现同码路径) |
| 5 | proxy 负测 | —— | **缺**(实现在,范围偏差 PB-C6) |
| 6 | unit 负测 | —— | **缺**(探针 ✓ fail-closed) |
| 7 | hash 负测(source/manifest) | manifest 自 hash 拒=Phase A 旧测 | **缺**(extraction 路径;探针 ✓) |
| 8 | view-overlap 负测 | —— | **缺 + 实现缺**(PB-C2) |
| 9 | seed ambiguity 负测 | —— | **缺**(探针 ✓ 两类均拒) |
| 10 | 禁止 largest-bbox fallback | 实现=seed-containment 唯一选面;token 扫描零命中 | **部分**(无多面正/负 repo 测例) |
| 11 | inspection 无 manifest 只能 UNBOUND | `test_inspection_without_manifest_is_unbound`(API 层)+ CLI exit 2 探针 | **已落**(API)/CLI 零测 |
| 12 | `test_inspect_dxf.py` 扩展(CLI/preflight) | 一行未动,2 旧测全 legacy `inspect()` | **缺** |
| 13 | LINE network 与闭 LWPOLYLINE 等价(§14.2) | fixture 只有 LWPOLYLINE footprint | **缺** |
| 14 | 斜边/短边/链式 snap 负测(§14.2) | —— | **缺**(2mm skew 探针 ✓ 拒) |
| 15 | clip 边界实体 fail(§14.2) | —— | **实现缺**(PB-C8 静默排除) |
| 16 | selector count/zone-seed drift(§14.2) | zone seed missing/count 门实现在 | **缺** |
| 17 | centerline 0.24→0.12 外偏(§14.2) | —— | **实现缺**(PB-C1 fail-open) |
| 18 | 不写默认 GT / 无 writer 入口 | `gt_extraction.py` 零写盘;CLI 只 `--json-out` 新建非资产路径 | **已落**(探针+源码核) |
| 19 | Phase A 回归全绿 | 六组自跑 78(见下) | **已落** |

小结:已落 5 / 部分 1 / 缺 10 / 实现缺 3(其中 17=PB-C1、15=PB-C8、8=PB-C2 双缺)。

---

## 定向测试组结果(本审自跑)

| 组 | passed | 与简报对账 |
|---|---|---|
| `tests/test_gt_extraction.py` | 5 | 简报"Phase B extraction + inspector 7"=5+2 ✓ |
| `tests/test_inspect_dxf.py` | 2(全 legacy) | ✓ |
| `tests/test_gt_schema.py` | 46 | ✓(简报 46) |
| `tests/test_gt_discipline.py` | 6 | ✓ |
| `tests/test_gt_from_dxf.py` | 11 | ✓(回归绿,Phase C 车道未动) |
| `tests/test_gt_render.py` | 5 | ✓ |
| `tests/test_gt_overlay.py` | 3 | ✓ |
| **合计定向** | **78** | 与简报一致;`git diff --check` PASS;资产扫描 clean(零 gt/golden/PNG/DXF 变动) |

主控合树全量情报(1135 绿 + 9 xfail)与本定向核数不冲突,不替代。

**本审活体探针清单**(scratchpad,未入仓):①CLI 五路(PASS=0/UNBOUND=2/--dxf 进 GT 根=3/--json-out 进 GT 根=3 无半文件/--json-out 已存在=3/新路径=0 且 0600 原子落盘);②symlink 逃逸 `--json-out` → 拦 ✓;③重复运行 stdout sha256 相同 ✓;④unit/source-hash/manifest-hash 篡改三路 → 全 BLOCK/拒 ✓;⑤view clip 交叠 10m² → manifest 接受 + inspect PASS + extract 成功(**洞,PB-C2**);⑥centerline+0.24 → 未偏移原环 NO-RAISE(**洞,PB-C1**);⑦seed 出界/双 seed 同面 → 两码拒 ✓;⑧seed 距边 0.1mm → NO-RAISE(**PB-C7**);⑨clip 边界线实体 → 静默排除(**PB-C8**);⑩2mm skew 边 → BLOCKED(经 node_join 顶包,axis 容差本身死参,**PB-C4**);⑪真 self-touch 环 → `gt_polygon_repeated_vertex` 拒 ✓(零测);⑫Inf 顶点 → wire 拒 ✓(零测)。

---

## 返工清单(主控裁决后下发)

1. **[PB-C1]** centerline:Phase B 内至少 fail-closed 拒 `boundary_reference="centerline"`(稳定码),或按 §10.3.4 落偏移;补正/负测。
2. **[PB-C2]** §8.2 clip-box 交叠检查(source-m 面积 vs topology tolerance)落 manifest validator(或 extraction 入口)+ 负测。
3. **[PB-C3]** 按对账表补齐负测矩阵(cut/proxy/unit/hash/view-overlap/seed ×2)+ inspector CLI 合同测试(exit 0/2/3、json-out 保护、UNBOUND)进 `tests/test_inspect_dxf.py`;确属后续 phase 的逐条列明,简报不得再报"偏差:none"。
4. **[PB-C4]** `_snap_segments` 拆双容差:聚类=node_join,轴投影/短边/斜边=axis_alignment;调用点补传;补一条两值不等时行为分叉的测试。
5. **[PB-C5~C8]** 残留计数真实上报;proxy 阻断限 bound view 内(view 外 INFO);seed 距边 > node_join 门;clip 边界触碰实体 fail。
6. **[PB-C9]** 酌情:stdout 先验参后输出、_UNITS 补 ft、真 self-touch/Inf 拒例、双 zone host 测例、真 implementation hashes 入 CLI。

核几何链与 CLI 信任面基座扎实(本批探针无一穿透写保护/UNBOUND 判定),返工有界:两处 fail-open 补门、一处容差接线、一批测试。

---

# r2 复审(2026-07-15/16)

同审向、同基准,对象=返工后工作树(gt_extraction.py 359→388、gt_manifest.py +18、inspect_dxf.py CLI 重排、test_gt_extraction.py 98→170/5→9 测、test_inspect_dxf.py +CLI 合同测、test_gt_schema.py 46→48 测)。工作树复核:本车道 7 文件 + 简报,零资产扰动,`git diff --check` PASS,B4b 车道未触碰。简报已按派单列明偏差(centerline 拒绝路线、Phase C/D 留待、TOCTOU NIT)——r1 "偏差:none" 型缺口已改正。

## r1 findings 逐条闭合

| r1 finding | 状态 | 闭合证据(本审独立验证) |
|---|---|---|
| PB-C1(MAJOR centerline fail-open) | **CLOSED** | 施工方选显式拒绝路线(合同允许,§10.3.4 外偏留 Phase C):`_check_input`(`gt_extraction.py:304-305`)对任一 plan view `boundary_reference != "outer_skin"` → `dxf_centerline_unsupported_in_phase_b`,inspect/extract 双入口同门;e2e BLOCKED 测试行(`test_gt_extraction.py:121`)。**r1 探针复跑**:centerline+0.24 → blocked,不再静默出未偏移几何 ✓ |
| PB-C2(MAJOR view-overlap 缺失) | **CLOSED** | 新 `validate_manifest_view_clips`(`gt_manifest.py:249-264`):全 view(含 elevation)pairwise,raw clip 乘 `metres_per_unit²` 转 source-m 面积再比 topology tolerance,合 §8.2 原文;接线 `_check_input:300-303`(inspect+extract 双消费);直接函数负测 + e2e BLOCKED 行双测。manifest model 自身不查(wire 无容差,docstring 说明设计意图)——属 r1 修法允许的 "extraction 入口" 路线。**r1 探针复跑**:空区 10m² 交叠 → BLOCKED `dxf_view_clip_overlap`,extract 拒 ✓ |
| PB-C3(MAJOR 负测矩阵+CLI 零测) | **CLOSED(实质)** | 八类全落:dangle/bulge(r1 已有)、cut(`test_cut_residual_is_blocked_and_reported`,但见 PB-C10)、proxy(`test_proxy_inside_bound_view_is_blocked`,monkeypatch 全实体成 proxy 走 bound-view BLOCK 路径)、unit(`dxf_unit_mismatch` 行)、hash(source_dxf_sha256 篡改 → BLOCKED 首 issue 断言)、view-overlap(双测)、seed ambiguity(多 seed 同 face)+加赠 seed-near-boundary、clip-boundary 两行;CLI 合同测(`test_inspect_dxf.py:97-115`)覆盖 exit 0/1/2/3 全梯 + UNBOUND JSON + `--json-out` 落盘 + 已存在拒且 **stdout 为空** + 缺 manifest=3。残留小尾归 PB-C12 |
| PB-C4(MAJOR axis 容差死参) | **CLOSED** | `_snap_segments` 拆双形参(`gt_extraction.py:203`):聚类+component 直径=node_join(`:207,216`),轴投影/短边/斜边四分支=axis_alignment(`:224-227`);四调用点(`:327,330,359,368`)均双传;**两值不同行为区分测试**落地(`test_axis_alignment_tolerance_is_independent_from_node_join_tolerance`:同一 2m/5mm 斜段,axis=0.01 投平、axis=0.001 拒 `dxf_nonorthogonal_edge`)——A0 登记 knob 已活 ✓ |
| PB-C5(MINOR 计数写死 0) | **CLOSED(带新发现 PB-C10)** | diagnostics dict 贯穿 `_polygonize`(`:232-236`),成功/BLOCK 两路 view 行均携真实计数;但类别互换见 PB-C10 |
| PB-C6(MINOR proxy 全域阻断) | **CLOSED(主体)+残留 PB-C11** | bound view 内 proxy 逐实体 bbox 判定,BLOCK 带 view_id+handle(`:336-343`);manifest 下 view 外 proxy 不再阻断 ✓;unbound 时 INFO ✓ |
| PB-C7(MINOR seed 距边) | **CLOSED** | `face.boundary.distance(seed) <= node_join → dxf_zone_seed_near_boundary`(`:374-375`)+ 0.5mm 负测。**r1 探针复跑**:0.1mm seed → 拒 ✓ |
| PB-C8(MINOR clip 边界静默排除) | **CLOSED** | `_clip_membership` 三值化(`:135-139`),edge → `dxf_entity_clip_boundary`(`:167-169`)+ e2e 测试行。**r1 探针复跑**:边界线实体 → BLOCKED ✓。NIT 残留:edge 判定用坐标值等式,远在框外但 x 恰等 clip xmin 的实体也判 edge(仅过度阻断方向,归 PB-C12) |
| PB-C9(NIT 束) | 大部闭合 | ①stdout 先验参后输出 ✓(CLI 测断言 exit 3 时 stdout 空;本审探针三路 protected/symlink 均 stdout_len=0);③`_UNITS` 补 ft(`:117`)✓;⑦CLI 用真 `compute_gt_implementation_hashes` ✓;④Inf 拒例+真 self-touch 环(7 顶点重叠闭边)拒例 ✓;⑤双 zone 正宽共线 host 拒例 ✓(`test_opening_host_with_two_positive_boundary_zone_matches_is_rejected`);②BLOCK 路径 `ezdxf.readfile` 双读仍在(`:315`);⑥TOCTOU 见下 |

## PB-C9⑥ TOCTOU 定级确认:维持 NIT

`_write_report` 的 `path.exists()` 检查与 `os.replace` 间存在竞态窗:窗内他进程在同一**非保护**路径新建的文件会被覆盖。定级依据:①保护谓词是路径静态判定,竞态不可能把写入挪进资产根(本审三路探针:gt 根/symlink/未建 gt_sources 全拦、零落盘、stdout 零泄漏);②mkstemp+fsync+replace 保证无半文件不变;③报告是诊断产物、单用户 CLI,窗口毫秒级;④修法(`open(path,'x')` 独占 create)顺手但无安全增益。**NIT 确认**,随 Phase C/D 顺手修。

## r2 新 findings

### PB-C10 —— MINOR:dangle/cut 解包顺序与 shapely 合同互换,测试把互换固化(探针坐实)

`gt_extraction.py:234`:`polygons, dangles, cuts, invalid = polygonize_full(...)`,而 shapely `polygonize_full` 返回序为 **(polygons, cut_edges, dangles, invalid_ring_lines)**(本审读 docstring+活体探针证实)。效果:report wire 的 `dangle_count`↔`cut_count` 交叉错标。**探针**:`test_cut_residual_is_blocked_and_reported` 的 "cut" 夹具线 `(0,0.5)-(1,0.5)`(一端接墙一端自由)实际是 **dangle**(落 shapely 返回元组第 3 位,cut_edges 为空),测试断言 `cut_count > 0` 恰因互换而过——测试通过本身即 bug 证据。阻断行为不受影响(任一残留 → BLOCK,r1 dangle 测同理仍绿)。修法一行:调换解包顺序,并给该测试换真 cut 夹具或改断言 dangle_count。

### PB-C11 —— MINOR:proxy bound-view 门三处残留(角点采样可逃逸+异常 fail-open+view 外 INFO 缺)

①`gt_extraction.py:339` 用 bbox **四角点**判 view 归属:包住整个 view 的巨型 proxy(图签框/xref 边框,现实常见)四角全在 clip 外 → `inside=False` 逃逸 BLOCK(本审逻辑探针:`(-100,-100)~(100,100)` bbox vs `(-1,-1,5,4)` clip → False)。修法:改矩形相交测试(两轴 `extmin<clip_max and extmax>clip_min`)。②`:340-341` `except Exception: inside = False`——bbox 计算失败的 proxy 静默不阻断,fail-open 方向错(存疑应 BLOCK)。③有 manifest 时 view 外 proxy 仅计入 `proxy_entity_count`,无 INFO issue(§9.2.2 "view 外对象只列 INFO");简报 PB-C6 行 "view 外只 INFO" 表述与实现不符。三处同门合报一条 MINOR。

### PB-C12 —— NIT(束,测试小尾+遗留)

json-out protected-root/symlink/未建 gt_sources 负测未进 repo(本审探针全拦,行为正确);LINE network 与闭 LWPOLYLINE 等价正例(§14.2)仍缺;selector count drift、footprint-seed-ambiguous 变体无直接测;`_clip_membership` 坐标等式过宽判 edge(过度阻断方向);BLOCK 路径双读 DXF(PB-C9②遗留)。

## 定向测试组结果(r2 自跑)

| 组 | passed | 对账 |
|---|---|---|
| `tests/test_gt_extraction.py` | 9 | 简报 "Phase B extraction + inspector 12"=9+3 ✓ |
| `tests/test_inspect_dxf.py` | 3(2 legacy + 1 CLI 合同) | ✓ |
| `tests/test_gt_schema.py` | 48 | ✓ |
| discipline/from_dxf/render/overlay | 25(6+11+5+3) | ✓ |
| **合计定向** | **85** | 与简报一致;`git diff --check` PASS;资产扫描 clean |

主控合树全量情报(1146 绿 + 9 xfail)方向一致,不替代本定向核数。

**r2 探针清单**(scratchpad,未入仓):①r1 四洞复跑=view-overlap 空区→BLOCKED `dxf_view_clip_overlap` / centerline→blocked / seed 0.1mm→`dxf_zone_seed_near_boundary` / clip 边界实体→blocked,全数闭合 ✓;②unit/source-hash/seed 出界/多 seed 四路仍拒 ✓;③CLI 六路=PASS 0/UNBOUND 2/protected gt 根 3/symlink 3/未建 gt_sources 子目录 3(三路 stdout 全空、零落盘)/重复运行 stdout sha256 相同 ✓;④shapely `polygonize_full` 返回序探针:dangle 夹具线落元组第 3 位 → 解包互换坐实(PB-C10);⑤巨型 proxy bbox 四角采样逃逸逻辑探针 → False(PB-C11①)。

## r2 总裁决:APPROVE-WITH-CHANGES

r1 四 MAJOR 全部实质闭合且带测试与探针复证(centerline 拒绝路线合同允许、简报已留痕);四 MINOR 中 C5/C7/C8 闭、C6 主体闭。残留 **2 MINOR**(PB-C10 计数互换——一行修+换夹具;PB-C11 proxy 门三小洞——均在诊断/预检面)+ **2 NIT 束**(PB-C9 遗留、PB-C12 测试小尾)。**真值路径(manifest 绑定→snap→polygonize→seed→tiling→ancestry)无任何已知 fail-open**;两条残留 MINOR 都不在真值几何链上。不需再开返工轮:PB-C10/C11 可随 Phase C 施工单携带或出小补丁,由主控裁决;全量 suite 权威门归主控轻门。
