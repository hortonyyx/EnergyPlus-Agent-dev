# F-154 重发执行档

- 日期：2026-09-01
- 施工席：GPT 家族
- 派工单：`2026-09-01_f154_reissue_wall_endcap_unowned.md`
- 状态：施工中（不提交）

## 一、开工自检

### 1. 基线提交

命令：

```bash
git rev-parse HEAD
```

读数：`58bb59f28d785139b48df642783db2c4db7ab537`，与派工基线 `58bb59f` 一致。

### 2. §一三条实测复现

从 `sm25-L_t3_as_received.dxf` 与 `request_as_measured.json` 调用
`build_as_measured`，并对每条 `boundary_ring_losses` 用
`_boundary_wall_groups` / `_boundary_owners` 复核：

```text
plan-F1 edges=44 losses=2
cavity:8bd127719198fd63 area=88.2656 m2
  span=(y,98800,[160000,161200]) nearest=110000 delta=-11200 owners=0
  endcap=w_x_160000_161200_61600_98800 along_max
cavity:04e1293098b1a95a area=28.683212 m2
  span=(y,52401,[99430,100630]) nearest=52400 delta=+1 owners=0
  endcap=w_x_99430_100630_52401_88800 along_min
plan-F2 edges=56 losses=1
cavity:495501ce9b36f0f3 area=70.3392 m2
  span=(x,60000,[110000,111200]) nearest=40000 delta=+20000 owners=0
  endcap=w_y_110000_111200_60000_68400 along_min
```

三条 span 长度均为 1200 units；三条均精确落在一堵垂直轴墙的端头；三条同轴面认领数均为 0。

判别实验只在内存副本中把目标墙 `along_min` 及其两条面线 `13AE`、`13AD`
的 `along_min` 归一到 `52400`，再调用 `derive_boundary_edges` / 
`derive_boundary_ring_losses`（没有改源 DXF 或仓库文件）：

```text
plan-F1 44 edges / 2 losses -> 52 edges / 1 loss
remaining cavity:8bd127719198fd63 area=88.2656 m2 delta=-11200
```

因此 28.68 m2 是独立的 0.1 mm 端点错位；88.27 与 70.34 m2 才是本单的端头无人认领问题。三条实测均可独立复现，未触发 §五停报。

### 3. 指定四文件基线

命令：

```bash
pytest -n 4 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py
```

读数：`84 passed in 27.95s`。

## 二、施工与验收

### 1. 端头认领实验实现

在 `_boundary_owners` 中把 owner 显式区分为 `face` 与 `endcap`。端头判据没有
距离阈值：垂直墙的 face 区间与 span 正长度重叠，墙端点坐标精确相等，并且两条
原始墙面线的端点精确落在同一相交墙带的两张面上。实测的真阳性 T 接分别是：

```text
plan-F1: terminating wall [160000,161200], intersecting band [98800,100000]
plan-F2: terminating wall [110000,111200], intersecting band [57600,60000]
```

0.1 mm 病例的相交墙面是 `52400`，原始端点却是 `52399/52401`，所以没有被
“近似”吸收。端头使用 `facts_exact_wall_endcap_v1` 证据方法并判作 `interzone`：
它是室内墙 T 接的墙轴供应，不是 footprint outer skin；普通 face ray 进入墙体会把
它当 junction fragment，端头的精确双面 T 接证据正是更强的拓扑关系。

实现后从 DXF + request 重建的读数：

```text
plan-F1 edges=88 losses=1
  boundary_condition: interzone=69 exterior=19
  remaining loss=cavity:04e1293098b1a95a area=28.683212 m2 delta=1
plan-F2 edges=91 losses=0
  boundary_condition: interzone=70 exterior=21
```

这逐项复现派工单 §一.4 的实验线索，且没有触碰 `52401/52399` 源输入。

### 2. 派工预报的八红复现

命令：

```bash
pytest -n 4 tests/test_boundary_condition_facts.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py tests/test_denominator_from_facts.py
```

读数：`76 passed / 8 failed in 23.67s`。失败测试恰好是派工单任务 3 列出的八条，
没有第九条既有锁变红。此时新内存 content hash 为：

```text
995b14bc763913220a4adade6c4b2eb583e68f8791d782f412a7929f478471fe
```

### 3. ⛔ 正式生成链发现派工题面矛盾，按 §五停报

按任务 2 指定入口，运行仓库既有机械生产脚本；该脚本从两份 DXF/request 重建
三件套，在调用 `write_facts_candidate` 前先执行正式 boundary reconciliation gate：

```bash
python AI_agent/logs/experiments/2026-08-29_o21b_facts_ledger/build_sm25_facts_staging.py
```

写盘前失败：

```text
BoundaryBasisMismatchError:
boundary_basis_reconciliation_failed:mismatches=0[] structural=[
  'facts_boundary_ring_invalid:plan-F1:cavity:8bd127719198fd63',
  'facts_boundary_ring_invalid:plan-F2:cavity:495501ce9b36f0f3'
]
```

独立用 Shapely 复核两条新增 ring：

```text
plan-F1 cavity:8bd127719198fd63 edges=44
  valid=False Self-intersection[110000 159400]
plan-F2 cavity:495501ce9b36f0f3 edges=35
  valid=False Self-intersection[168500 40000]
```

原因不是端头 owner 自身，而是端头令旧推导继续后，既有 classifier 会按设计拒绝
墙体 junction fragments；剩余 logical spans 仍被输出，却在多个位置不首尾相接。
派工钉死的 `88/91` 正包含这两条断裂/自交环。要让正式 gate 通过，必须改变边界环
的合并/投影结构与边数，不再只是任务 3 授权的期望数值更新，也不再保持派工预报
的 `88/91` 读数。因此任务 1/§一.4 与任务 2、任务 3“只改数值、不可改结构语义”
不能同时成立，触发 §五“任务项与禁令自相矛盾 / 锁形状需改”的必停条件。

生成器在 gate 后才写盘，故三件套未被改动；确认命令：

```bash
git diff --exit-code -- case_tests/test_baseline/gt_staging/sm25-L_anchor/facts
```

exit 0。当前旧文件哈希仍为：

```text
as_measured.json  0d3aefa229d277b3197b5cf007747df5885641d58c8a1b6e6cdc376236f2548c
revisions.json    4db9e12690d761581e0c9787515a944fc7606aace969796c3ae24305d9bbbda5
as_signed.json    e5d4da3aeb27246f93b7fae3f19af3d3396699c517bf278f9ce78cb9ab867541
```

没有手改 JSON，没有签 revision，没有运行全量或 `-n auto`，也没有触碰
`src/agent/correction/`、`src/agent/reading/` 或 `gt_sources/`。

### 4. 当前仅本席改动路径

```text
src/agent/judge/as_measured.py
tests/test_boundary_condition_facts.py
AI_agent/logs/reviews/execution/2026-09-01_f154_reissue_execution.md
```

其中测试文件只为私有 `_BoundarySpan` 的 owner 数据结构改名而调整两处既有合成夹具
构造，没有改断言。合成 no-owner / 双 endcap 唯一性锁、staging、授权数值断言、
sm24 探针均因本次必停尚未施工。

## 三、施工方判断

最薄弱处不是端头等值判据，而是题面把“边数增加且 loss 清零”当成“logical ring
成立”；正式消费者另有更强的不变量：edge sequence 必须构成有效简单多边形。当前
两条新 ring 明确违反后者。

希望复核方重点裁决：

1. 是否授权重做 junction-fragment 合并/投影语义，并相应放弃 `88/91` 目标读数；或
2. 是否修改 staging 生成/对账承诺，允许存入 `facts_boundary_ring_invalid` 的环。

在这两者之一被明确授权前，继续“改数到绿”会违反任务 3 三条非谈判项，故停工。
