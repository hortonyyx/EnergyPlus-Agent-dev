# P1 交付说明 · 天正→GT v3 转换器(GLM-5.2 施工)

> 日期 2026-07-22 · 施工 GLM-5.2 · 主控 Opus 4.8 · 范围 **仅 P1 = S0–S4**
> 施工基线 = [`proposals/tarch_to_gtv3_converter_plan.md`](../../../proposals/tarch_to_gtv3_converter_plan.md)
> 派单 = [`request/2026-07-22_tarch_converter_construction_dispatch.md`](../request/2026-07-22_tarch_converter_construction_dispatch.md)
> P0 契约(本轮基座)= [`execution/2026-07-22_tarch_converter_p0_glm.md`](./2026-07-22_tarch_converter_p0_glm.md) + `src/agent/judge/tarch_converter_schema.py`
>
> **本轮做 P1 = S0–S4,在 P0 冻结契约之上实现算法体;退出门 sm24 洞口 21/21 + 三零残留 + Σ面积零残差,数字独立重导(对得上探针目标)。未进 P2。§6.1 主控已裁方案 A(§0.1),本轮按 A 在 staging 跑,不晋升。**

---

## 0. 摘要 — 退出门全部达成

| 退出门(brief §2) | 状态 | 独立跑出的数字(本实现,非抄探针) |
|---|---|---|
| sm24 洞口 21/21(S3 双证据) | ✅ | resolved **21** / unresolved **0** / ambiguous **0**(11 窗 + 10 门) |
| 三零残留(S4) | ✅ | dangles **0** / cuts **0** / invalid **0**(faces **51**) |
| Σ面积零残差(S4) | ✅ | sum_area **200.0 m²** == footprint **200.0 m²**(delta **0.0**) |
| 对得上探针目标(brief #7) | ✅ | 退化 0/保留 132、jamb cap V/H 34/39、faces 51、200.0 m² —— 与 probes/final.py 目标逐项吻合 |

**与探针数字的关系**:上述数字由本实现**独立重导**(我写了算法体,跑 sm24 真图得出),随后与 `probes/final.py` 的目标交叉核对——全部吻合,故未触发"对不上即停"。测试里的期望值是**本实现的稳定输出**,不是从 probes/ 抄来的未验数字。

---

## 1. 改动文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `src/agent/judge/tarch_normalize.py` | **新增** | P1 算法体 S0–S4 + 报告构建(~620 行)。judge 侧,不进 gate①/执行器。 |
| `src/agent/judge/tarch_converter_schema.py` | **扩展(契约)** | `TarchConversionRequestV1` 加 `wall_thickness_range_m`(带默认 `[0.06,0.50]` + 有序校验)——S2 jamb-cap 识别必需的建筑域 sanity 区间。**可选字段,P0 fixture 不破。** |
| `tests/test_tarch_converter_p1_geometry.py` | **新增** | 21 测:sm24 e2e 出口门 + 合成夹具每个 fail 分支正/必红 + 确定性 + 报告契约 + staging 纪律。 |
| `tests/test_gt_discipline.py` | **扩展** | `_FORBIDDEN` 加 `tarch_normalize`(gt 隔离硬纪律#4 守新模块;runtime 无导入→仍绿)。 |
| `backup/src_history/2026-07-22_tarch_converter_p1/` | **备份** | 动 `src/` 前 `judge/` + `test_gt_discipline.py` 备份。 |

**未碰**:golden、gt.json、v3 提取器本体(`gt_extraction.py`)、`gt_from_dxf.py`、correction/内核/装配生产路径、0_reading。S0–S4 全新增,零生产码修改(仅契约加一个可选字段)。

---

## 2. S0–S4 实现要点

落点 `src/agent/judge/tarch_normalize.py`,顶层入口 `run_p1_plan_view(dxf_path, request, plan_view, tooling) -> P1PlanViewGeometry`(纯:读 DXF、出几何+诊断+门)。DXF 路径经 `assert_staging_input` 强制 staging(§0.1 方案 A)。

- **S0 输入体检**:proxy 实体计数(`PROXY` in dxftype)>0 → `tarch_source_proxy_present`;`$INSUNITS` unitless 必须带显式 `metres_per_unit`,声明单位与 scale 不一致 → `tarch_units_undeclared`;视图框 = 请求的 `clip_box_dxf`(人声明),校验该框存在闭合 LWPOLYLINE + 框内**恰好 1 个**标题文字(否则 `tarch_view_frame_missing`/`tarch_view_frame_ambiguous`)。**不读 "edge" 层名**(gt 隔离:层名/块名只活在请求的 `TarchDialectRulesV1`/选择器里)。
- **S1 坐标量化**:`q = τ_node/10`(派生,`derive_quantization_step`,非配置项),DXF 原生单位网格 `round(v/q)*q`。退化(量化后零长度)线 → `tarch_wall_degenerate_line`(INFO)丢弃。**G2 守恒**:两个相距 >τ_node 的源坐标不得落到同格点 → `tarch_quantization_conflict`。正交性走 `|dx|,|dy| ≤ τ_axis`(非浮点精确相等,D3),越界 → `tarch_wall_nonorthogonal`。
- **S2 墙线归集 + jamb cap**:WALL 层 LINE → 量化;长度在 `[t_min,t_max]`(建筑域 sanity 区间,**只作过滤器不作厚度来源**)的短线 = 墙垛端头(jamb cap),厚度证据 kind #2(`wall_cap_or_opening_jamb`),每段存 proof_handles。capV(竖短线)/capH(横短线)分桶;按横截面 `[c1,c2]` 归并为 wall band。**无 `DEFAULT_WALL_THICKNESS` 等常量。**
- **S3 洞口双证据(缺一不填)**:对每个 WINDOW 层 INSERT,取量化 bbox;对 axis ∈ {x,y} 试解——在垂直轴端头集合里找位于 bbox 沿轴跨度 `(lo,hi)` 两端、且横截面 `[c1,c2]` **完全相同**的两根 cap,再要求 bbox 法向区间与 `[c1,c2]` **有正重叠**(此条把门块开启扇排除在判定外 = D2)。**恰好一解才填**(矩形 = 沿墙跨度取自块、法向取自墙体);0 解 → `tarch_opening_block_unresolved`,多解 → `tarch_opening_block_ambiguous`,块名不匹配门窗前缀 → `tarch_opening_kind_ambiguous`。门窗几何解析**统一**(法向恒取自 cap,故门块 bbox 的开启扇天然被排除);块名只用于 window/door 分类与报告。
- **S4 拓扑闭合**:线集 = 全部墙线 + 全部洞口矩形 4 边 → `polygonize_full(unary_union(segs))`。`dangles/cuts/invalid` 全 0 且 `Σ面积 == footprint`(unary_union(faces),τ_area 内)。残留悬空 → `tarch_wall_free_end`(定位到真实 dangle 端点,**绝不自动延伸**=Q5);cuts/invalid 或面积不符 → `tarch_topology_residual`。洞口外/内分类(D5):外法向面落在 footprint 外环 → exterior,否则 `tarch_interior_opening_excluded`(INFO)。

---

## 3. sm24 独立跑出的数字(出口门)

实跑 `case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf`(sha256 与 SURVEY 一致),源 DXF 拷进 staging 后跑:

```
degenerate lines: 0 | wall_lines kept: 132
jamb caps V/H:    34 / 39          wall bands: 26
openings:         21  (window 11 / door 10)   unresolved 0  ambiguous 0
classification:   exterior 14 / interior_excluded 7   (= 11 窗 + 3 外门 / 7 内门,与 D5 吻合)
faces: 51   dangles 0  cuts 0  invalid 0
sum_area_m2 200.0 == footprint_area_m2 200.0   (delta 0.0)
gates: G1 ✓  G2 ✓  G3 ✓  G5 ✓   (G4 守恒=14==14 是 S7/P2,P1 不发)
BLOCK diagnostics: 0    INFO: 7(7 个内门 excluded)
report: PASS  (round-trip ✓)
```

**D2 验证**:外门 AC3 解出矩形 `[23597.6,46325.2]–[25197.6,46565.2]`(240 厚北墙上的 1600 洞),**不是**块 bbox 的 1600×780(开启扇越出外墙 660mm 被正确排除)。测试 `test_sm24_door_opening_excludes_swing_arc` 断言之。

---

## 4. 必红夹具清单(每 fail 分支,S0–S4)

纪律#5:P1 接线的每个 fail 分支都有正例(green)+ 必红负例(断言**指定码**变红,非"正常输入过门")。

| 阶段 | 码 | 必红夹具(合成 DXF) | 测试 |
|---|---|---|---|
| S0 | `tarch_view_frame_ambiguous` | 框内 2 标题 / 0 标题 | `test_s0_view_frame_ambiguous_{two,zero}_titles` |
| S0 | `tarch_view_frame_missing` | clip_box 远离、无闭合框匹配 | `test_s0_view_frame_missing` |
| S0 | `tarch_entity_unsupported` | WALL 层放 CIRCLE | `test_s0_entity_unsupported_circle_in_wall` |
| S0 | `tarch_units_undeclared` | header 声明 mm 但 request 给 cm scale | `test_s0_units_undeclared_on_scale_mismatch` |
| S0 | `tarch_source_proxy_present` | 谓词单测(PROXY 实体计数) | `test_s0_proxy_count_predicate` |
| S1 | `tarch_wall_nonorthogonal` | WALL 层斜线 | `test_s1_wall_nonorthogonal_rejected` |
| S1 | `tarch_quantization_conflict` | 构造 >τ_node 塌缩源表(G2 守卫) | `test_s1_quantization_conflict_unit` |
| S1 | `tarch_wall_degenerate_line`(INFO) | 零长度墙线 → INFO 非 BLOCK | `test_s1_degenerate_line_is_info_not_block` |
| S3 | `tarch_opening_block_unresolved` | 删 jamb cap → 块无配对 | `test_s3_opening_unresolved_no_caps` |
| S3 | `tarch_opening_block_ambiguous` | 块法向跨两条同厚墙带 → 2 解 | `test_s3_opening_ambiguous_two_bands` |
| S3 | `tarch_opening_kind_ambiguous` | 未知块名(`$Furniture$`) | `test_s3_opening_kind_ambiguous_unknown_block` |
| S4 | `tarch_wall_free_end` | 房间内墙 stub → dangle | `test_s4_wall_free_end_dangle` |
| S4 | `tarch_topology_residual` | 构造面积不符残差(守卫) | `test_s4_topology_residual_area_mismatch_unit` |

正例:`test_synthetic_green_one_window_closes`(单房一窗:1 洞口 rect 精确、三零、24.0==24.0、G1–G5 绿)。

---

## 5. 测试结果

- `tests/test_tarch_converter_p1_geometry.py`:**21 测全绿**。
- **全量:`1494 passed + 9 xfailed`**(基线 1473 + P1 新增 21 = 1494;9 xfail 既有 legacy golden 待 sm21 批次重录,**零回归**)。

---

## 6. 诚实披露(未竟 / 拿不准 / 绕过纪律处)

对标 B4b/B5 正面样板,逐条标明,不藏假绿:

1. **P1 不写 augmented normalized DXF、不产 manifest/overlay**(§0.1:晋升落盘是 P2/P9)。故报告 `normalized_dxf_sha256` 在 PASS 时**绑源 DXF bytes**(P1 未改图),P2 S9 写入 GTV3_* 图层后会重绑。已披露,非占位隐瞒。
2. **walls[] = jamb-cap 归并的 wall band,`coord_mm` 取两面中线代表值**(band_id 编码两面真实坐标,thickness 来自 cap)。P2 把 band 精化为完整 ribbon(双面 track + 接头)。这是 P1 的诚实简化,非最终形态。
3. **G4(14==14 外皮缺口守恒)P1 不发**:该守恒是 S7(`tarch_opening_skin_gap_mismatch`),P1 只做 S3 外/内**分类**(INFO)。装一个恒 pass 的 G4 桩会是 false-lock,故 P1 门序列为 G1/G2/G3/G5,G4 留 P2。
4. **G2 在 P1 只做量化守恒**;"每道墙 fully evidenced"的厚度证据 rigor(`tarch_wall_thickness_unevidenced`/`tarch_wall_entity_unaccounted`)是 P2 ribbon 工作,P1 只记 `wall_proof_coverage` 计数,不硬 fail。
5. **S3 几何续接证人相关码未接线**(`opening_fill_conflict`/`opening_gap_unexplained`/`opening_evidence_unbound`/`opening_host_ambiguous`/`skin_gap_unattributed`):这些服务"块被炸成线"的图(plan §4 S3),sm24 带块,P1 用块双证据;续接证人是 P2 增量。本轮未声称覆盖。
6. **报告 status = PASS 需几何**:P1 用 walls[](band)满足;P2 加 zones 后报告完整。P1 的 PASS 语义="S0–S4 几何全过",非"bundle 完成"。
7. **契约加了 `wall_thickness_range_m`**(P0 冻结契约之上):S2 必需,schema 加可选字段+默认 `[0.06,0.50]`+有序校验,P0 fixture 不破(已验 P0 测仍绿)。按 brief"别改契约除非必要且披露"——必要且已披露。
8. **`tarch_topology_residual` 面积不符分支是守卫**:干净 polygonize 不会面积不符(Σ==union 恒成立),该分支用构造残止单测覆盖(纪律#5 仍配必红)。dangles→`wall_free_end` 是真实可达路径(sm24 缺一洞即触发)。
9. **S0 视图框不读 "edge" 层名**:用请求 `clip_box_dxf` + 框内标题数校验(gt 隔离比硬编码层名更干净)。若主控/sol 认为应显式校验 edge 层闭合框,可加(请求加 frame 层名字段)。

---

## 7. 下一站(P2,本轮不做)

- **S5–S9**:腔体识别(面积二分,近阈值面清单 + G6 计数 + G8 反演三道承重)→ 意图绑定 → **逐边外扩到混合基准框**(外包外皮/内墙轴线)→ 九门(含 **G8 必红夹具**:故意把某边 basis 记反 ⇒ 断言 G8 红)→ 落盘(追加 GTV3_* 图层 + manifest + source_map + overlay)。
- 退出门 = sm24 8 区、对称差 0.000000、人核 overlay 通过。
- 审阅:派单定 **sol(gpt-5.6-sol,effort max)审**,谁写谁不批。

---

## 8. 最终测试结果

- P1 测试 `tests/test_tarch_converter_p1_geometry.py`:**21 passed**。
- 全量 `python -m pytest`:**`1494 passed, 9 xfailed`**(352s;基线 1473 + P1 新增 21;9 xfail 既有 legacy golden,**零回归**)。
- gt 隔离 `tests/test_gt_discipline.py`:扩展 `_FORBIDDEN`(加 `tarch_normalize`)后仍绿。
