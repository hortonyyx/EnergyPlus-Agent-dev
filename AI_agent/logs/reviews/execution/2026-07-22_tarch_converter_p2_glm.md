# 天正→GT v3 转换器 P2(S5–S9)施工续作 + 全面自验 — GLM-5.2 交付说明

**日期**: 2026-07-22  **执行**: GLM-5.2(施工)  **审阅需求**: sol 对抗审(逐条验 §2 硬纪律)
**派单**: `logs/reviews/request/2026-07-22_tarch_converter_construction_dispatch.md`
**方案**: `proposals/tarch_to_gtv3_converter_plan.md`  **§6.1 主控已裁方案 A**

## 0. 结论先行

- **sm24 退出门全绿**:8 腔体→8 区认领、G7 对称差≈0(1.5e-13 m²)、**两两重叠=0**、G8 独立反演对账≈0(8.3e-13 m²)、G4 14==14、**G9 v3 预检通过**、G10 overlay 落盘。`status=PASS`。
- **三道承重闸门齐**:近阈值面清单(6 件)+ G8 + 人核 overlay 全在。
- **全量 pytest**:**1508 passed + 9 xfailed,零回归**(基线 1494 + 本批新增 14 测 = 1508;9 xfail 不变)。
- **S9 落盘**:8 件产物晋升 `case_tests/test_baseline/gt_sources/sm24_anchor/`,**晋升后 bundle 独立复跑 v3 = PASS / 0 issue / 抽出 1 层 8 区**。

⚠️ **诚实披露(核心)**:上两轮写进 `tarch_normalize.py` 的 P2 算法体**未经任何验证**(两轮都卡在算法打磨、撞额度断了)。本轮跑退出门时**发现并修了 4 个真实 bug**(都阻断退出门,详见 §3)。修完后才全绿。这不是"只补验证",而是"验证暴露了上轮代码的错误,必须先修对才能交付"——已逐条落证,不藏假绿。

## 1. 改动文件

| 文件 | 变化 | 说明 |
|---|---|---|
| `src/agent/judge/tarch_normalize.py` | +1063 / −8(净,文件 1860 行) | P2 算法体(S5–S9 + 门 G4–G10)+ 本轮 4 处 bug 修复 + source_map |
| `src/agent/judge/tarch_converter_schema.py` | +7 | `min_room_area_m2`(A_room 域参数,P0 已冻结契约补默认) |
| `tests/test_tarch_converter_p2_geometry.py` | **新建 496 行 / 14 测** | sm24 退出门 + 接头矩阵 + 九门必红(G8 在列)+ S9 落盘 + 往返 |
| `AI_agent/.../2026-07-22_tarch_converter_p2_glm/work/promote_s9_to_gt_sources.py` | 新建 | S9 晋升脚本(staging 跑→显式 cp 到受保护区) |
| `case_tests/test_baseline/gt_sources/sm24_anchor/` | +5 件 | normalized.dxf + manifest + conversion_report + source_map + overlay |
| `backup/src_history/2026-07-22_tarch_converter_p2/` | +2 件 | `*.p2_pre_glm_resume` 回滚点 |

**未碰**(纪律):golden/gt.json/v3 提取器本体(`gt_extraction.py`)/`gt_from_dxf.py`/correction/内核/装配生产路径/0_reading/gt_from_dxf。`gt_extraction.py`/`gt_manifest.py`/`gt_schema.py` **零改动**(只读其契约)。

## 2. S5–S9 要点(本轮通读确认 + 修复点)

- **S5 腔体识别**:面积二分(face>A_room=腔体,余为墙域);多外环→`tarch_footprint_multiple` 阻断(不取最大);内环→`tarch_profile_hole_unsupported`;近阈值面 `[0.5·A_room, 2·A_room]` 无条件算(承重证据)。A_room=域参数提案,**判据是人声明的数量 G6**(禁自动调 A_room 至数量吻合——纪律)。
- **S6 意图绑定**:坐标归机器(腔体代表点)、数量/名归人;canonical 序(minx,miny);腔体数≠expected→`tarch_cavity_count_mismatch` 阻断。
- **S7 逐边外扩**:清理共线→CCW→每边测厚(march+二分)→远端分类(outer_skin 偏 t / wall_axis 偏 t/2)→厚度变化跨边分裂→支撑线角点重建多边形。L/丁字/十字无需特例代码;自由端永不到此(S4 dangle 门)。
- **G8 独立反演(主保险)**:由**输出 zone 边+basis+厚度**重建墙域,**绝不读 S5 WallRegion**(亲手验 `g8_reconstruct_wall_region` 只用 `zones` 入参——纪律 #1 满足)。
- **S9 落盘(方案 A)**:augmented DXF 追加 GTV3_* 图层(保留全部原句柄)+ manifest(绑 augmented.dxf)+ conversion_report + **source_map 逐边 ancestry** + 人核 overlay;staging 跑,显式 cp 晋升。

## 3. ⚠️ 本轮发现并修复的 4 个 bug(上轮未验证代码)

退出门第一次跑即 BLOCKED。逐个定位、取证、修对(都附带必红/正向夹具):

1. **`build_p2_report` 的 `source_handles=["GTV3_ZONE"]`**(字面层名,非 hex 句柄)→ ZoneEdgeReportV1 校验崩。**修**:S7 给每条 wall 边记真实源墙线句柄(`_edge_source_handles`:按轴+coord+span 重叠匹配腔体边所在的源墙线;min/max 化墙线方向);report 用 `edge.source_handles` + `derived_handle`(GTV3_ZONE 句柄);并落 `source_map` 逐边 ancestry。

2. **S7 厚度 march 探针 pad 太小(2 native 单位)**→ 探针落在垂直墙的 240mm 厚度内,march 沿该墙全长远扫(测出 1760mm、**8000mm** 等荒唐厚度)→ zone 外扩 880/4000mm 鼓进邻居 → **G7 两两重叠 0.0109 m² ≠ 0**。取证:zone5 e0 中点 march=120mm(正确),f=0.9995 近角点 march=8000mm(擦墙)。**修**:`pad = wall_half_thickness_max_native + tau_node`(域参数 `wall_thickness_range_m[1]/2`,非烤死常数——纪律 #4);短边回退中点单探(不再探角点)。**修后 overlap=0.0**。注:G8 此前仍≈0(重叠是内部双重认领,被 ∪zones−∪cav 反演抵消)——正是 G7-overlap 子门存在的意义(抓补偿性误差),G8 抓不到。

3. **footprint 外环带冗余共线门 jamb 顶点**(S4 填料致 union 外环过每个 jamb 多一个亚毫米顶点)→ v3 node-snap 后塌成零长边 → `dxf_short_edge`。**修**:发射前 `_clean_collinear`(与 `_outer_skin_gap_count` 同口径)→ 只留真角点,同形多边形。

4. **manifest `world_from_source_m` 用了 native→world 仿射(m00=mpu=0.001)**,但 v3 `_transform` 先 `native×mpu` 再套仿射 → **双重缩放** → 种子落空 → `dxf_footprint_seed_ambiguous`。取证对照冻结契约:`tests/test_gt_extraction.py`/`test_inspect_dxf.py` 的 v3 manifest 一律 **m00=1.0**(metres→world)。**修**:`_build_manifest` 把 mpu 从线性部分析出(`m00=mpu/mpu=1.0`,平移项不变);种子仍用 native→world 仿射(种子直接出世界米)。

## 4. 独立跑出的 sm24 退出门数字(禁照抄 probes/,本轮独立重导)

落盘:`work/p2_exit_gate_output.json` + 晋升的 `conversion_report.json`。

| 项 | 值 | 期望 | 判 |
|---|---|---|---|
| 腔体数(S5) | 8 | 8 | ✓ |
| 认领区(S6) | 8 | 8 | ✓ G6 pass |
| G7 对称差(∪zones vs footprint) | 1.455e-13 m² | ≈0 | ✓ |
| **G7 两两重叠** | **0.0 m²** | **0** | ✓ |
| **G8 独立反演对称差** | **8.27e-13 m²** | **≈0** | ✓ |
| G4 外开口 / 外皮缺口 | 14 / 14 | 14==14 | ✓ |
| G9 v3 预检 | pass(code=None) | pass | ✓ |
| G10 overlay | 落盘 | 落盘 | ✓ |
| 全门 / status | 全绿 / PASS | 全绿 | ✓ |
| 8 区面积和 | 200.0 m²(=footprint) | 200 | ✓ |

近阈值面清单(承重证据,6 件,均 is_cavity=false):1.034 / 1.152×3 / 1.440 / 1.486 m²(世界坐标已落 conversion_report)。

## 5. 九门必红夹具(G8 明确在列,纪律 #5)

G1/G2/G3/G5 必红在 P1 测文件(`test_tarch_converter_p1_geometry.py`);本批 owns P2 门 G4/G6/G7/G8/G9:

| 门 | 必红夹具 | 断言 |
|---|---|---|
| **G8** | `test_g8_must_red_flipped_basis_diverges` | 翻转 zone0 一条 wall_axis 边的 basis→outer_skin(offset t/2→t),独立重建对称差 >1e-3 → G8 红;绿孪生 pass。证 G8 非 Footprint−Σ 恒等式(恒等式翻 basis 仍绿) |
| G6 | `test_g6_must_red_cavity_count_mismatch` | expected=7(实际 8)→ G6 红 + `tarch_cavity_count_mismatch` |
| G7 | `test_g7_must_red_pairwise_overlap` | 鼓胀 zone0 5mm → 重叠>1e-6 → G7-overlap 子门红(symdiff 仍≈0,正是补偿误差) |
| G4 | `test_g4_must_red_unit_level` | 构造 100 单位未覆盖外皮缺口 → `_outer_skin_gap_count`==1 |
| G9 | `test_g9_must_red_v3_rejects_bad_bundle` | manifest footprint 句柄改 nonexistent → v3 inspection fail-closed |

每个夹具断言**指定门**变红(非"某门红")。每门另有正例(sm24/synthetic 全绿)。

## 6. 5 类接头合成夹具矩阵(裁决稿 §2.5)

直接 shapely 构造(腔体+墙域+footprint)喂 S7,重建顶点对手算:

| 接头 | 夹具 | 验证 |
|---|---|---|
| L/凸角 | `test_s7_single_room_outer_skin_expand_matches_hand_calc` | 单间四边 outer_skin,zone==外皮盒(角点各偏 t=240);G8 反演==墙域 |
| 丁字(共享内墙) | `test_s7_two_room_shared_wall_no_overlap` | 两间共享 240 内墙,各偏 t/2=120 于中线相会,**重叠 0**;G8 反演==墙域 |
| 十字(2×2 网格) | `test_s7_cross_junction_four_rooms_tile` | 四间于中心十字相会,**重叠 0 + 拼满 footprint**;G8 反演==墙域 |
| 自由端 | `test_s4_free_end_blocks_before_s7` | 悬空 stub → S4 dangle 门红(`tarch_wall_free_end`),**S7 不跑**(zones==[]) |

**变厚度跨边**:纪律要求每墙厚度可变、S7 按测厚分裂子边。本轮 `_thickness_profile` 已实现(自适应内探+二分,均匀边 2 探即止,厚度变化 bisect 到 tau_node 内),由 march pad 修复间接验(短边/长边均得正确 120/240)。**未单独构造厚度跨边 synthetic 夹具**——见 §8 跟进债。

## 7. S9 落盘产物清单(晋升 gt_sources/sm24_anchor/)

```
source.dxf            (原,未动)
normalized.dxf        602KB  源 + GTV3_FOOTPRINT/ZONE/OPENING 三图层,保留全部原句柄
manifest.json         7.8KB  绑 normalized.dxf(only_listed 句柄锚定,无"层多一线"漂移)
conversion_report.json  73KB  status=PASS + 10 门 + zones/cavities/walls/openings
source_map.json        33KB  34 条逐边 ancestry(1 footprint + N zone_edge + M opening)
overlay_plan.svg       15KB  人核 overlay(源墙线+外皮环+8 区半透+14 外开口)
```
晋升后**独立复跑 v3**:`inspect=PASS/0 issue`,`extract→1 floor/8 zones`。晋升是显式 cp,转换器从未在受保护区内跑重建(staging 跑 → cp)。

## 8. 测试结果 + 诚实披露(未竟/拿不准/绕过)

**测试**:`tests/test_tarch_converter_p2_geometry.py` **14 测全绿**;全量 **1508 passed + 9 xfailed**。

**未竟/跟进债(不藏)**:
1. **变厚度跨边独立夹具未单独构造**(§6):逻辑已实现且经 sm24 间接验,但缺"一道墙跨中变厚→分裂两子边各带各测厚"的定向 synthetic 断言。sol 审若要求,补一个 shapely 构造的变厚墙域夹具即可。
2. **9 门 vs P2 门口径**:brief 写"九门必红",G1/G2/G3/G5 在 P1 文件复用(未在 P2 文件重写),P2 文件 owns G4/G6/G7/G8/G9。若 sol 认为 P2 文件应自包含全 9 门,可搬。
3. **G10 必红未做**:G10=overlay 落盘(机器部分产出),无真正 fail 模式(verification 恒为 candidate,人核归人),故无必红夹具——按设计。
4. **PNG overlay 未做**:`_write_overlay_svg` 只 SVG(本环境无 matplotlib);PNG 合成为已记 follow-up。
5. **探针数字随稿落盘**:已落 `work/p2_exit_gate_output.json`(brief 要求)。

**拿不准**:
- source_map 的 footprint/opening ancestry 用 `_edge_source_handles`/block+jamb 句柄,诚实但未逐条人核每个句柄对应(34 条机器派生);sol 审可抽查。
- march pad 用 `wall_thickness_range_m[1]/2`(域参数上界),对极端厚墙(接近 0.5m 上界)的短边可能 pad_f 偏大、回退中点单探——sm24 无此情况,但属边界。

**绕过**:无。未放松任何门/容差/契约;未碰 golden/v3 本体;fail-closed 全保留(歧义必阻断)。

## 9. 硬纪律自查(sol 会逐条验)

- [x] **G8 真独立**:只读 `zones`(polygon+vertices+edges),不读 S5 WallRegion(`g8_reconstruct_wall_region(zones)` 唯一入参)。必红夹具证非恒等式。
- [x] **三道承重闸门齐**:近阈值清单+G8+overlay 全在。
- [x] **fail-closed**:多外环/内环/数量不符/v3 拒绝/自由端 全阻断,无猜/取最近/打分。
- [x] **不烤死假设**:无 DEFAULT_WALL_THICKNESS/MAX_WALL_PAIR_DISTANCE/MIN_ROOM_WIDTH;pad 用域参数 `wall_thickness_range` 非常数。
- [x] **A_room 只提案**:判据=数量 G6;未自动调至吻合。
- [x] **outer skin 无界 flood 等价**:S5 多外环/内环直接阻断(不取最大/不填洞)。
- [x] **自由端证明式**:S4 dangle 门阻断,S7 不跑。
- [x] **种子不自证**:坐标归机器、数量/名归人(sm24 role=unspecified、名 r0..r7 仅用数量 8)。
- [x] **容差全取 judge_gt.yaml**;**gt 隔离**:转换器不被 gate①/执行器 import,dialect 仅在 dialect 规则。

## 10. 下一步

P0–P2 施工批**收官就绪**。建议:**sol 对抗审**(逐条验 §2 硬纪律 + §3 四 bug 修复 + §5 必红夹具真绑目标门防 false-lock)→ 主控轻门独立全量 → 合并。转换器落地 = sm24 收官前置满足;之后素材入仓 + 跑 sm25-L = C2 收官。
