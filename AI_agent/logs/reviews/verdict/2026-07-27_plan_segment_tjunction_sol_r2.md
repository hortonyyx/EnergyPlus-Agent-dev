# 对抗复审裁决 · 平面判卷器 T 型接头返工 r1（GPT 侧 sol）

- 日期：2026-07-27
- 施工：GLM-5.2
- 被审对象：`src/agent/judge/segment_score.py`、`tests/test_c2_segment_tjunction.py`
- 本轮范围：上一轮必做项 1 / 2 / 4 / 5；**不审、不以之作为出口理由**：必做项 3（Y-2 分母语义）
- 裁决：**REWORK**
- 审阅纪律：只审不修；活体与 neuter 探针仅在 `/tmp/segment_tjunction_sol_r2_probe.py`、`/tmp/segment_tjunction_sol_r2_neuter.py`

## 1. 总裁决

本轮返工修成了三块实质功能：

1. 上一轮两个指定浮点活体反例均已由 RED 转 GREEN，`1e-9` 缺口仍 RED；
2. correction 共享近正交内边的 exact-reverse 退化路径可用；
3. 两个 zone 都等于完整 footprint 的同向重复覆盖已由 `exterior_duplicate_owner` 拦住。

但仍不能批准，原因均在本轮范围内：

1. **RW-1 的最近格量化仍有确定性的格边界假红。**我构造出 typed correction：同一精确十进制坐标分别由 `8.0600000000005` 与 `8.060000000001 - 5e-13` 产生，两个 binary64 只差 1 ulp；上游五项 finding 全 GREEN，量化后却分别为 `8.06` 与 `8.060000000001`，scorer 报 `score_product_identity_invalid / invalid_interior_edge_pair`。因此“表示层假红已消除/相同接缝必共享身份”不成立。
2. **RW-2 的退化路径只修到了共享内边，未保住一般边的原行为。**一个 footprint 与唯一 cell 完全相同、右侧边 `dx=5e-10, dy=1` 的 typed correction 上游同样全 GREEN；该合法的单 owner exterior general edge 没有反向边，被 `_pair_general_edges` 当作内墙破洞而报 RED。代码注释所称 correction footprint/exterior 已由上游验证为精确 axis-aligned 也不属实。
3. **neuter 自查表仍漏报连带。**独立矩阵证明 `neuter_split` 还会翻 L-a、L-f happy；关闭 canonicalization 或 one-sided guard 还会翻 L-f sad。这些新增锁未被纳入 r1.5 的归并表。Y-1 测试也只用 `SimpleNamespace` 锁 scorer fallback，没有锁住其所宣称的 typed validator→scorer 接缝。

全仓绿色不能覆盖上述活体缺口。

## 2. RW-1 数值身份合同

### 2.1 实现接线与指定三格

| 命题 | 裁断 | 独立证据 |
|---|---|---|
| `_canonical_coord = round(v/1e-12)*1e-12 + 0.0` | **成立** | `segment_score.py:37-46` |
| GT / correction 两侧同函数同参数 | **成立** | zone/cell/footprint 均经 `_edges → _points → _canonical_point`；GT boundary segment 与 observation coercion 也显式复用 |
| 规范化后配对仍用精确 `==` / `<=` | **成立** | `_lies_on_exterior`、正交分桶/覆盖与 general exact reverse 均未引入近似比较 |
| 真实 sm24 `8.059999999999999 → 8.06` 活体消除 | **成立** | 重写 z1 两点、重算 content hash，`validate_gt_v3` GREEN；两值均规范成 `8.06`；抽出 16 条 interior |
| typed correction `0.1+0.2` vs `0.3` 活体消除 | **成立** | validator 五项 GREEN；两值均规范成 `0.3`；抽出 1 条 interior |
| `1e-9` endpoint gap 仍红 | **成立** | 独立夹具报 `score_gt_identity_invalid / invalid_interior_edge_pair` |

以上结果来自 `/tmp/segment_tjunction_sol_r2_probe.py`，没有采信施工日志数字。

### 2.2 主控新命题：量子格边界

#### ① 风险真实性与量级

**成立。**

最近格量化把实数轴分成宽 `q=1e-12` 的格；任何离散映射都有格边界。两种表示相差 `δ` 时，若其相位在每个量子周期内近似均匀，跨界带所占比例约为 `δ/q`：

- 本次 8.06 m 活体的相邻 binary64 间距为 `1.7763568394002505e-15`，故 `δ/q = 0.001776...`，约 **1.8‰**；
- 20 m 处 `ulp = 3.552713678800501e-15`，一 ulp 已约 **3.6‰**；“数个 ulp”可到数‰乃至约 1%。

所以“约千分之一量级”作为一 ulp、8 m 左右的数量级判断成立，但它不是统一上界；取决于坐标量级、两种计算路径的 ulp 距离和坐标相位。对给定数值则完全确定，不是随机偶发。

#### ② 现实可达性

**成立，已构造 typed 活体。**

精确十进制算术中：

```text
8.0600000000005 == 8.060000000001 - 0.0000000000005
```

binary64 中两条生产路径得到：

```text
left  = 8.0600000000005
right = 8.060000000000501
delta = 1.7763568394002505e-15
canonical(left)  = 8.06
canonical(right) = 8.060000000001
```

把它们分别作为两个 cell 的共享边：

- `correction.cell_polygon_contract` GREEN；
- `correction.coverage` GREEN；
- 其余 nondegenerate / zstack / tripwire 也 GREEN；
- scorer RED：`score_product_identity_invalid / invalid_interior_edge_pair`。

这不是只调用私有 helper 的任意对象，而是 `CorrectedGeometryV3 + CellV3` 的公开 typed 路径。坐标尾数本身处于亚皮米级，物理上罕见；但计算生成器可产生任意量子相位，且 scorer 当前没有输入小数位/guard-band 合同，因此“不可达”不能成立。

#### ③ 接受还是换更强方案

**必须换更强方案；仅登记残留风险不足。**

理由：

- 当前公开 validator 明确放行该输入，scorer 却把它误报成真实 topology break；
- 风险对具体输入是确定性的，并会随同一 floor 的多条 seam 累积，不能只用单边的千分位比例评估 case 级风险；
- RW-1 的目标是建立数值身份合同，而不是把已知假红从常见点移到格边界。

更强方案应在 trust boundary 建立可证明的离散身份，例如保留原始十进制 token、按明确允许的 scale 转 fixed-point integer，并拒绝不满足 scale/guard-band 的输入；或者采用有最大簇直径与歧义拒绝语义的文档级表示噪声归并。单纯把 `q` 改大/改小，或把同一最近格算法换成 Decimal round，都会移动而不是消灭边界。无论选哪条，仍须证明 `1e-9` 缺口保持 RED。

### 2.3 “假红已消除”是否声称大于实况

**成立（有一处文字范围需要区分）。**

执行日志没有逐字出现标题式的“所有假红已消除”；其“两个活体修复前 RED → 修复后 GREEN”是准确的限定陈述。但 r1.4 的“浮点→不假红”以及代码注释 `identical seams share one identity` 是无保留的普遍表述，已被格边界活体证伪。因此若“假红已消除”指 RW-1 的一般合同，它就是“声称大于实况”；只能写成“消除了 L-a/L-b 指定表示，并仍存在量子边界残留”，除非改用更强方案。

## 3. RW-2 非正交边

### 3.1 施工方否决方案②的理由

**成立。**

`cell_geometry.py:159-162` 的判据是：

```python
if dx > _EPS and dy > _EPS:
    raise ...
```

其中 `_EPS=1e-9`。因此 `dx=5e-10, dy=1` 不会被 correction validator 拒绝。独立 typed 两 cell 活体得到五项 validator GREEN，且当前 `_pair_general_edges` 能输出一条 A-B interior segment。

所以“上游先拒 ⇒ scorer hard reject 不可达”在 correction 侧确实不成立；方案②在当前 validator 合同下不可选。GT `_ring_vertices` 使用精确 `dx != 0 and dy != 0`，两侧口径不同。主控返工单把“先拒”写成方案②必须证明的条件，而非既成事实；技术可行性前提有误，但派单本身保留了前提核实出口。

### 3.2 方案①是否完整恢复原行为

**不成立。**

`_pair_general_edges` 对每条 general edge 一律要求 exact reverse；其注释据“footprint/exterior rings are axis-aligned (validated upstream)”省略 exterior 检查。但 correction schema 的 `FootprintRing` 只约束 finite/min_length，`validate_corrected_geometry` 也没有对 footprint 做精确正交检查。

独立 typed 活体：

```text
footprint = cell A =
[(0,0), (1,0), (1+5e-10,1), (0,1)]
```

结果：

- validator 五项全 GREEN；
- cell 的右侧近正交边与 footprint 边完全相同，是合法 single-owner exterior；
- scorer 把该边送入 `_pair_general_edges`，因无 reverse 报
  `score_product_identity_invalid / invalid_interior_edge_pair`。

因此 exact-reverse 退化路径修复了“共享 general interior”，却把可达的 general exterior 误作破洞。需要让 validator 与 scorer 对 footprint 正交定义一致，或在 general path 精确识别 single-owner exterior，并继续守住 duplicate/conflict 语义。

## 4. RW-3 helper 漏洞与合同注释

| 命题 | 裁断 | 证据 |
|---|---|---|
| 两 zone 都等于完整 footprint 的同向重复覆盖不再静默 GREEN | **成立** | 独立夹具报 outer code `score_gt_identity_invalid`、reason `exterior_duplicate_owner` |
| 新守卫只针对 exterior-only 同向多 owner | **成立** | 分支只在 `on_exterior` 且单侧 owner 存在时检查该侧 `len>1` |
| 新增 inline 注释如实说明不是通用 area-overlap 检测 | **成立** | `segment_score.py:171-177` 明写 specific shape / NOT every overlap |
| helper 整体合同已完全收窄 | **不成立** | `_tile_orthogonal_edges` 与 `_pair_interior_edges` 的 docstring 仍无限定地写“a gap, an overlap ... is rejected”；与新增 inline 限定并列，合同文字仍自相矛盾 |

功能守卫本身通过；需统一上层 docstring、inline 注释和执行日志的范围，不得再把“指定 exterior duplicate 已拦截”扩写成“helper 检测一切 overlap”。

## 5. 新锁独立性、连带与 false-lock

独立运行 `/tmp/segment_tjunction_sol_r2_neuter.py`，核心矩阵如下：

| neuter | 实际翻转 |
|---|---|
| `canonical → identity` | L-a、L-b、**L-f sad** |
| `quantum → 1e-8` | 仅 L-c |
| 删除 one-sided raise | L-c、L-d、Lock3、**L-f sad** |
| 删除 exterior duplicate raise | 仅 L-e |
| 删除 interior overlap raise | 无测试翻转；Lock4 仍由 exterior duplicate 守卫拦截 |
| `_pair_general_edges → raise` | 仅 Y-1 |
| `neuter_split` | Lock1、Lock2、**L-a**、Lock7、**L-f happy** |

裁断：

1. **“已把 L-a/L-b 与 L-c/L-d/Lock3 如实归并”成立。**日志列出的六种 r1 mutation 结果与我的独立结果一致；Lock4 不独占 interior-overlap 守卫也披露正确。
2. **“全部新增锁的连带均已如实登记”不成立。**r1.5 没有列 L-f happy/sad，也没登记 L-a 对 `neuter_split` 的依赖。L-a 是 canonicalization + sm24 T-split 的复合锁；L-f happy 共用 split；L-f sad 同时共用 canonical 与 one-sided。
3. **没有发现完全不承重的新测试，但存在一条范围性 false-lock/半锁。**Y-1 测试使用 `SimpleNamespace`，不调用 `validate_corrected_geometry`；它能锁住 scorer general fallback，却不能锁住其 docstring 宣称的“上游认可 → scorer 认可”全链。若 validator 明日改为拒绝，该测试仍会 GREEN。应改成 typed correction 并先断言相关 findings GREEN。
4. **L-f 两测的功能断言本身成立。**合法 T 接头确为 0 unmatched / 全 complete；产品 gap 确实以 product identity error 失败。问题是 neuter 归并证据缺项，不是这些断言为假。

返工单明确要求每条新锁给指定 neuter，若共用守卫则归并并登记连带；本轮仍未满足这一验收项。

## 6. 测试复算

- 受影响小门：`15 passed in 8.96s`
  - `tests/test_c2_segment_tjunction.py`
  - `tests/test_c2_b4b_phase_b.py::test_b4b_r1_gt_interior_pairing_and_invariant_raises`
- 独立全仓：`1685 passed, 10 xfailed, 150 warnings in 259.96s (0:04:19)`
- failed = 0；未采信主控/施工方的 1685 数字。

## 7. REWORK 必做

1. **RW-1**：改用能处理格边界的数值身份合同；补本文 typed boundary 活体。不得只改措辞或移动量子边界，且 `1e-9` 缺口必须继续 RED。
2. **RW-2**：补 general exterior 接缝，消除本文“唯一 cell = 近正交 footprint”上游 GREEN / scorer RED；修正“exterior 已由上游精确正交验证”的不实注释，并把 Y-1 锁升级为 typed validator→scorer 全链。
3. **RW-3**：保留当前 `exterior_duplicate_owner` 守卫；统一 helper docstring 为已实际实现的窄合同。
4. **锁表**：把 L-a、L-f happy/sad 的全部共用守卫与连带纳入 neuter 归并表，不得继续称现表已覆盖全部新锁。

Y-2 分母语义仍由另一批裁定，不是本次 REWORK 理由。

## 8. 被审文件字节不变自证

审前：

```text
f3f4e60e720030ac49af0bad6bd553e129a9856c27e3358f012153689ffd1644  src/agent/judge/segment_score.py
1b3f0292b8d37c864e1dea813a5a45316fb8c066de342794e36bf6be73207fa8  tests/test_c2_segment_tjunction.py
```

审毕：

```text
f3f4e60e720030ac49af0bad6bd553e129a9856c27e3358f012153689ffd1644  src/agent/judge/segment_score.py
1b3f0292b8d37c864e1dea813a5a45316fb8c066de342794e36bf6be73207fa8  tests/test_c2_segment_tjunction.py
```

两组 SHA-256 逐字一致。
