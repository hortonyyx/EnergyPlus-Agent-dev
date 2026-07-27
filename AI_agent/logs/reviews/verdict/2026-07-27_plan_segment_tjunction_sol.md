# 对抗审裁决 · 平面判卷器 T 型接头配对修复（GPT 侧 sol）

- 日期：2026-07-27
- 被审对象：`git diff src/agent/judge/segment_score.py` + `tests/test_c2_segment_tjunction.py`
- 裁决：**REWORK**
- 审阅纪律：只审不修；未改动上述两个被审文件；所有自造探针均在 `/tmp/segment_tjunction_sol_probe.py`

## 1. 总裁决

这批修复的主干方向正确，并确实解决了合法 T 型接头在 GT 侧硬拒、correction 侧静默丢观测的问题；真实 sm24 的 16 个内墙邻接也能独立复算吻合。

但当前版本不能批准，原因有三条：

1. **X-2 命脉不成立**：helper 虽未引入 epsilon/圆整，却把未经统一数值规范化的 binary float 当成拓扑身份。真实 sm24 上只把同一个十进制接缝 `8.06` 从 `8.059999999999999` 改写为 `8.06`，重算合法 content hash 后 `validate_gt_v3` 仍为 GREEN，scorer 却报 `invalid_interior_edge_pair`。这是已活体复现的假红，不是推测。
2. **Y-2 主控 R-1 需要重裁**：下游每个切分子段默认计 1 denominator unit；同一道物理墙从 1 段切成 4 段后，整墙漏画由 `1 denominator / 1 failing` 变为 `4 / 4`。更严重的是，一条几何完全覆盖四子段的长 observation 因一对一 assignment 产生 `score_match_ambiguous`（4 个等价 assignment），不是正常命中。
3. **X-1 的“重叠一律红”并未由 helper 全面实现**：两个同向 zone 都完整覆盖 footprint 时，所有重叠边都被当成 exterior-only 跳过，helper 返回 GREEN、0 条内墙。上游 typed validation 通常能先挡住该输入，但这已经证伪 helper docstring/验收命题的普遍表述，也说明新增 overlap 锁只覆盖了“内墙处同时有反向 owner”的窄形态。

## 2. 逐条命题裁断

### X-1「铺不满仍然要红」是否真锁

**总体：不成立。**

分项：

| 命题 | 裁断 | 独立证据 |
|---|---|---|
| 合法长边对四短边能切分 | **成立** | 自造不等长四段夹具得到 7 条内墙（4 条走廊邻接 + 3 条房间邻接） |
| 缺口仍红 | **成立** | `[0,5] + [6,10]` 报 `invalid_interior_edge_pair` |
| 端点差 `1e-9` 仍红 | **成立** | `[0,5] + [5+1e-9,10]` 报同码 |
| 单侧悬空仍红 | **成立** | 长边 `[0,10]` 只有对侧 `[0,5]` 覆盖，报同码 |
| 内墙重复 owner 重叠仍红 | **成立** | A 对面 B/C 同占 `[0,10]`，报同码 |
| 任意重叠一律红 | **不成立** | 两个 zone 都等于完整 footprint，所有边同向且在 exterior；`_pair_interior_edges` 静默跳过，GREEN、0 interior |
| 外墙/内墙冲突仍保留原错误语义 | **成立** | 既有夹具仍报 `exterior_interior_topology_conflict` |
| 新锁逐条独立、无连带 | **不成立** | neuter 单侧缺口守卫同时让 gap、`1e-9` endpoint、单侧悬空三例转绿；三例本质共用一个守卫，不是三条独立承重锁 |

独立 neuter 摘要：

- `neuter_split`：T 正例由 GREEN 变 `invalid_interior_edge_pair`。
- `neuter_hole`：gap、`1e-9` endpoint、单侧悬空同时由 RED 变 GREEN。
- `neuter_overlap`：新增测试所代表的内墙重复 owner 由 RED 变 GREEN；其他 gap/endpoint 保持 RED。
- `neuter_tolerance`（坐标圆到 8 位）：仅 `1e-9` endpoint 夹具在该矩阵中由 RED 变 GREEN。
- `neuter_exterior_conflict`：既有冲突夹具错误原因从 `exterior_interior_topology_conflict` 退化为 `invalid_interior_edge_pair`，因此原断言会红。

这说明主要守卫确实承重，但施工日志所称“全部锁无 false-lock、无连带”不成立。尤其新增测试没有覆盖 `1e-9`（只有 `1e-3`）、单侧悬空和 exterior-only owner multiplicity。

### X-2 禁吸附、禁容差及浮点表示敏感性

| 命题 | 裁断 | 独立证据 |
|---|---|---|
| `_pair_interior_edges` / `_lies_on_exterior` 路径未新增 epsilon、圆整、近似相等 | **成立** | 支撑线 key、共线、区间覆盖、exterior containment 全部用精确 `==`/`<=`；未发现新 tolerance |
| 施工方所述 sm24 圆整交叉效应成立 | **成立** | sm24 顶边原值 `19.999999999999996`：原 zone edge `_lies_on_exterior=True`；仅圆成 `20.0` 后为 `False` |
| “零容差因此不会造成表示层假红” | **不成立** | 精确比较把数值编码差当拓扑差；见以下两个活体反例 |

反例 A（真实 sm24 GT）：

- z0 顶边原值：`8.059999999999999`
- 将 z1 底边两点仅改写为：`8.06`
- 重算 `GroundTruthV3.content_sha256`
- `validate_gt_v3(..., expected_case="sm24_anchor")`：**GREEN**
- `extract_gt_plan_segments`：**RED / `invalid_interior_edge_pair`**

这是“同一十进制几何、不同 binary float 写法”直接造成的假红。

反例 B（typed correction）：

- A 右边用 `0.1 + 0.2 == 0.30000000000000004`
- B 左边用字面值 `0.3`
- `correction.cell_polygon_contract=True`
- `correction.coverage=True`
- `extract_correction_plan_segments`：**RED / `invalid_interior_edge_pair`**

因此正确接缝不是在 scorer 内偷偷加模糊容差，而是先明确**唯一数值身份契约**：要么信任边界进入 scorer 前使用既有结构网格作一次可审计 canonicalization，之后仍精确配对；要么上游 validation 改为与 scorer 完全一致的 exact topology，并用测试证明合法生产者都输出 canonical coordinates。当前“上游容差放行、scorer 精确硬拒”不可并存。

### X-3 产品侧假红是否消除

**成立（对合法 correction T 接头这一限定命题）。**

独立活体：

- GT target interior = 7；
- correction observation interior = 7；
- 走廊四段 `zone_ids` 为 A-B / A-C / A-D / A-E；
- `assign_plan_segments` matched = 7，双方 unmatched = 0；
- `score_plan_segments` 七条全部 `complete`。

非法 correction 缺口不再静默丢观测，而是：

- code = `score_product_identity_invalid`
- reason = `invalid_interior_edge_pair`

因此 correction 提取侧原始假红根因确已消除。现有 Lock 7 只锁“进入观测集”，建议补一条完整 assignment/score 锁，钉死 7/7 complete 和 0 unmatched。

### Y-1 非正交边硬报错

#### ① 是否引入现实可达回归

**成立。**

不是只有任意 `SimpleNamespace` 才可达。自造两个 cell 共享一条 `dx=5e-10, dy=1` 的精确反向边：

- `validate_corrected_geometry` 的 `correction.cell_polygon_contract=True`
- `correction.coverage=True`
- 旧 exact-reverse 算法可直接配对该共享边
- 新 helper 因两坐标都不精确相等，报 `invalid_interior_edge_pair`

根因是 `cell_geometry.py` 用 `_EPS=1e-9` 判“正交”，新 scorer 却用 exact axis equality。即使当前 deterministic core 常会把生产数据吸附到结构网格，公共 schema/validator 契约仍明确放行该形态；判卷层不能把它另行解释成拓扑破洞。

#### ② 是否违反项目不变量 #6

**成立。**

当前 helper 把支撑线类型硬编码成 `("V", x)` / `("H", y)`，并把未来非正交能力映射成当前通用错误 `invalid_interior_edge_pair`。这不是“当前 capability 明确不支持”的独立边界，而是把 capability 假设烤进了配对内核；未来松动需要重写 helper，并且错误语义无法区分 unsupported geometry 与真实 topology break。

#### ③ 可接受所需登记/接缝

当前形态**不可按仅登记债务接受**。至少应二选一：

1. 在进入 scorer 前的 capability/trust boundary 用稳定的 `unsupported/nonorthogonal` 身份码精确拒绝，并让 validator 与 scorer 使用同一正交定义；helper 不再冒充拓扑破洞；
2. helper 保留非正交 exact-reverse 退化路径，或按一般支撑线/参数区间设计接口；当前 C2 仍只启用正交 T 切分，但未来扩展无需推翻 API。

同时需要：

- 架构文档登记当前 capability 与未来 general segment seam；
- typed GT/correction 的正负锁；
- `5e-10`、`1e-9` 边界值锁，证明 validator 与 scorer 口径一致。

### Y-2 分母语义

| 命题 | 裁断 | 证据 |
|---|---|---|
| “每切分子区间是一条 segment”与当前实现机械一致 | **成立** | extract 每个 elementary interval 发一条 `PlanSegment`；score 每条发一行 |
| 同一道物理墙切成 n 段不会重复计罚 | **不成立** | `score_policy._criterion_from_rows` 对无 `eligible_units` 的 segment row 默认每行 1 unit |
| 同一道物理墙切成 n 段会把整墙错误计罚 n 次 | **成立** | 同一 4m 墙完全漏画：unsplit 为 denominator/failing `1/1`；split4 为 `4/4` |
| 单长 observation 可自然覆盖 n 个 target 子段 | **不成立** | 一条 `[0,4]` observation 对四条 1m target 触发 `score_match_ambiguous`，`candidate_assignments=4` |

因此 R-1 不是单纯“分母变大但自洽”。它改变了物理墙在总分中的权重：邻接房间切得越细，同长度/同错误的墙权重越高；reading 若以一笔表达整墙，还会因一对一 assignment 被硬拒。

主控需在收口前重新裁定至少两件事：

1. denominator unit 是“邻接界面”“物理墙”“长度”中的哪一种；
2. target 与 observation 分段不一致时，是先按联合 cut set 规范化后计分，还是允许一对多覆盖匹配。

在该语义未定前，不应把 R-1 回写成稳定架构合同。

## 3. 真实 sm24 独立复算

未采用派工单/执行日志数字。用 Shapely 对 8 个 zone 两两求 boundary intersection，独立得到 **16 个正长度 LineString 邻接分量**；实现也抽出 16 条。

独立邻接计数：

- 单分量：z0-z1、z0-z4、z0-z5、z1-z2、z1-z5、z2-z3、z2-z5、z3-z5、z3-z7、z5-z7、z6-z7；
- z4-z5 = 3；
- z5-z6 = 2；
- 合计 `11 + 3 + 2 = 16`。

所以新增真实 case 正例的 16 不是抄数，且本轮 T 切分主算法对当前 sm24 的结果正确。

## 4. 测试结果

- 受影响小门：`7 passed in 2.21s`
  - `tests/test_c2_segment_tjunction.py`
  - `tests/test_c2_b4b_phase_b.py::test_b4b_r1_gt_interior_pairing_and_invariant_raises`
- 独立全仓：`1677 passed, 10 xfailed, 150 warnings in 243.83s (0:04:03)`
- failed = 0；未采信施工方或主控报数。

全仓绿只能证明既有锁未回归，不能推翻上文活体反例；反例恰好是当前测试集缺口。

## 5. REWORK 必做项

1. 统一 GT / correction validator 与 scorer 的数值身份合同；增加真实 sm24 `8.059999999999999` vs `8.06` 变体锁，以及 `0.1+0.2` vs `0.3` typed correction 锁。
2. 处理 Y-1：不得让 validator 认可的近正交 exact-reverse 几何在 scorer 中被误报为 topology break；补明确 capability seam/错误码或一般线段退化路径。
3. 主控重裁 Y-2；补“单长 observation 对多个 target 子段”与“同墙切分前后 denominator/failing”契约锁。
4. 补 exterior-only 多 owner 重叠守卫，或把 helper 合同明确收窄并证明所有调用入口必先完成 owner multiplicity validation；不能继续宣称 helper 自身“overlap 一律红”。
5. 产品侧测试从“观察集出现”提升为完整 assignment/score：0 unmatched、全 complete；并补产品缺口/重叠/浮点表示失败语义。

## 6. 被审文件字节不变自证

审前：

```text
03d068d749227af66f87f8c43fa489dbf23d821e7b14ccd248eab1832be38a77  src/agent/judge/segment_score.py
d07368bf8073b29354d49d78021029ff43ad92685bd19444c3126510661cb49c  tests/test_c2_segment_tjunction.py
```

审毕：

```text
03d068d749227af66f87f8c43fa489dbf23d821e7b14ccd248eab1832be38a77  src/agent/judge/segment_score.py
d07368bf8073b29354d49d78021029ff43ad92685bd19444c3126510661cb49c  tests/test_c2_segment_tjunction.py
```

两组 sha256 逐字一致。
