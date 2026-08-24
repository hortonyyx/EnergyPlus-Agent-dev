# 拿 sm25 的答案直接喂几何内核（2026-08-25 · 探索档 · ⛔ 永不作成绩）

> **起因**：用户 2026-08-25 提「能不能直接捏一份答案出来，从 correction 之后走，
> 看看几何内核那部分有没有问题，反正这个不计入跑测」。
>
> ⛔ **反向铁律（CLAUDE.md §0.2）**：本目录一切产物**永远不得记成成绩** ——
> 答案就在**输入**里，任何"对答案"的分数都是同义反复。
> 它能回答的只有一个问题：**给内核一份正确性无可争议的输入，它自己会不会出错。**

## 一、为什么值得单独做这么一次

`sm25-L_anchor` 的现行产物 `run_2026-08-25_c2_rescore_R0` 停在 `1_correction`。
主控先零成本侦察了一次：把那份**已 accepted** 的 correction 直接喂内核 ——

| | zones | surfaces | InterZone | gate①(kernel) |
|---|---|---|---|---|
| R0 真实产物 | 38 | 266 | 0 | **6 项 0 阻塞** |

⇒ **sm25 停在 correction，不是因为内核跑不动。**

但同一次侦察量到一件事：**R0 的 38 个 cell 里，带 `polygon` 的 = 0** —— 全是矩形包围盒。
而 gt 的 1F 有 **14 个多边形 zone，其中走廊是 14 顶点的凹多边形**。
⇒ **C2 的多边形路径，内核从来没有真正吃过一次。** 这就是捏答案能撞、而现行管线撞不到的地方。

## 二、方法：不伪造信任根

v3 的每扇窗都必须逐扇引用 `0_reading` 的观测（防无证据落笔／防抄答案），
gt 不带这种引用。⛔ **没有去伪造那套证书**（output / window_hosts / resolver_inputs /
feature_states 四份 sha256 互绑）—— 伪造信任根会让整个探针失去意义。

实际做法：

```
gt.json ──[骨架]──> floors / footprint / cells(真多边形)
R0 pre-core draw ──[窗的 reading 引用]──> windows[].provenance
        ↓  两者拼成一份 v3 draw（tools/derive_draw_from_gt.py）
真实生产路径：parse_correction_draw → build_verified_window_inputs_from_run
             → finalize_correction_draw（确定性核）→ 由普通验证器签发 B5 proof
        ↓
materialize_kernel_geometry → check_kernel → serialize_geometry
```

**基准换算**（guide §四之二）：gt 是「外墙外包 + 内墙中轴」，CorrectedGeometry 全程中线
⇒ `--basis centerline` 把外皮内收 t/2（=0.12，外墙 240），`--basis outer` 原样不动。

- 31 扇 gt 窗 ↔ 31 份 R0 窗引用，**一一对应零冲突**（最近邻匹配无重复占用）
  ⇒ 顺带证实两侧是同一批窗。
- 窗证据链 **verified**、gate①(correction) **17 项 0 阻塞** ⇒ 答案版 draw 本身是合法产物。
- ⚠️ `--basis outer` 在窗宿主解析处被拒（`WindowHostResolutionError`）
  ⇒ **现行的门确实拦得住基准错配**，这一条记为门的正面证据，未继续深挖。

## 三、⭐ 撞出两条缺陷（互相独立）

### F-95 顶点规范化把凹多边形毁掉（重）

`canonicalize_ring_vertices`（[`src/validator/data_model.py:1047`](../../../../src/validator/data_model.py#L1047)）
用**绕质心的角度排序**重排顶点。对凸多边形它能还原环序；**对凹多边形它还原成另一个形状**。

最小复现（14 行，不涉 gt、不涉判分）：

离线夹具 [`tools/concave_canonicalization_matrix.py`](tools/concave_canonicalization_matrix.py)
（不需要 gt / LLM / 跑抽，`python <file>` 直接出下表；今天退出码 = 1）：

| 形状 | 凹角数 | 输入面积 | 规范化后 | |
|---|---|---|---|---|
| 矩形对照 | 0 | 80.000 | 80.000 | OK |
| 单凹角 L 形（6 顶点，= 现有测试 `test_lshape_polygon_clean` 用的那个）| 1 | 84.000 | 84.000 | OK |
| **U 形（8 顶点）** | 2 | 76.000 | **70.000** | **CORRUPTED** |
| Z 形（8 顶点）| **2** | 68.000 | 68.000 | **OK** |
| **梳形（12 顶点）** | 3 | 66.000 | **59.000** | **CORRUPTED** |
| **sm25 走廊 F1-z0（14 顶点）** | 4 | 97.731 | **226.457** | **CORRUPTED** |

⚠️ **本表当场证伪了 orchestrator 自己的初稿断言**：初稿写的是「两个及以上凹角就不满足」，
而 **Z 形有两个凹角却无损** ⇒ **凹角数不是判据**。
真正的判据是「**顶点绕质心的极角是否单调**」—— 凹是**必要非充分**条件，
所以⛔ **靠"有没有凹角"来挑回归夹具会挑出假绿的那一半**。

后果（answer-fed run 实测）：`Z10_F1_Office_S` 地板面积 **226.457 vs 自己的轮廓 97.731**（2.3 倍）、
`Z22_F2_Office_SW` **174.332 vs 78.558**。`kernel.zone_closure` 抓住了（面积对账），
但**规范化后的环仍然 `is_valid=True`** ⇒ 任何"多边形有效性"检查都放行。

⭐ **时间线（`git log` 实测，不是推测）**：
`cell.polygon` 能力 **2026-07-08** 落地（`df6f249`），
`canonicalize_ring_vertices` 及其接进内核 **2026-08-07** 才出现（`a3458cc`，F-13 顶点顺序修复）。
⇒ **规范化比多边形能力晚一个月，是它落地时把已有的多边形能力打坏的**，
而没人发现，因为从那天起到今天**没有一个真凹多边形流过内核**（见下文 R0 对照）。
同族教训 [[free-correctness-evaporates-when-representation-changes]]：
加规范化时要问「**谁在拿变换前的形态跟它比**」—— F-13 那次没人问 cell 多边形会怎样。

⚠️ **两条要一起看**：
1. **已有的 L 形锁不具分辨力** —— `test_lshape_polygon_clean` 断言的正是那个恰好无损的单凹角 L 形。
   ⇒ 「有一把 L 形的锁」和「凹多边形被覆盖了」是两件事。
2. **kernel 与 validator 刻意共用这一个实现**（`build.py` 注释：避免 F-13 那种两套算法分歧）
   ⇒ 校验器与生产者共享同一个错误假设，**只有面积对账这一条路抓得住它**。

### F-96 跨层轴的碎片守卫只管同层，反而把碎片做小

1F 的一道隔墙中轴 `y=15.9996`，2F 对应的是 `y=16.06` —— **真实的 6 cm 错位**。

⭐ **已溯源到原始 DXF 的逐条坐标**（`gt_sources/sm25-L_anchor/sm25-L_t3.dxf`，`WALL` 图层，单位 mm；
世界坐标换算 `y_world = (y_dxf − 28213.6)/1000`，由 `GTV3_FOOTPRINT` 标定）：

| 在哪 | 两条墙面线 y | 厚度 | 中轴 → world |
|---|---|---|---|
| 1F 左半段（world x 0.24→10.0）| 44213.552 / 44333.552 | 120 mm | 44273.552 → **16.0600** |
| **1F 右半段（world x 11.12→14.76）** | **44153.221 / 44273.221** | 120 mm | 44213.221 → **15.9996** |
| 2F 左半段 | 44213.552 / 44333.552 | 120 mm | 44273.552 → **16.0600** |
| 2F 右半段 | 44213.552 / 44333.552 | 120 mm | 44273.552 → **16.0600** |

⇒ **两道墙厚度相同（都是 120），错位的是位置**：**1F 右半段那道隔墙比其余三处整体往南偏了 60.3 mm**。
⛔ 所以它既不是 gt 转换器造的，也不是转换噪声，更不是"两种墙厚"——**原图上就这么画的**，gt 逐字忠实转录。
⭐ 那个 `15.9996` 的 0.4 mm 零头同样不是误差：原图 y 坐标的零头本来就有 `.552` 和 `.221` 两种，
它就是该墙中轴相对标定原点的真实位置（判别实验里把它归整到 16.0 后碎片照旧，已独立印证）。

⭐⭐ **这正是本条缺陷值得修的理由**：真实图纸就是会有这种量级的错位，
而内核当前的反应是切出一条 3 cm 的楼板并让门警告 EnergyPlus 可能崩。
确定性核的动作分两步，第二步破坏第一步：

1. 跨层对齐先判 **"provenance-aware sliver guard kept axes separate"**（delta=0.0，决定不合并）；
2. 同层吸附随即把 1F 那条从 15.9996 推到 **16.03**（delta=0.0304，`AXIS_JITTER_TOL+SNAP_GRID+MIN_EDGE_LENGTH`）。

⇒ 两轴间距从 0.0604 **缩到 0.03**，方向正好朝着它刚判定要保持分离的那条轴。
跨层切分于是切出 **0.03 m 宽**的天花/地板条，InterZone 门只能事后报
`degenerate surface ... EP may segfault in input processing`。

三点判别（同一份输入只改这一个量）：

| 变体 | 跨层轴距 | InterZone |
|---|---|---|
| gt 原值 15.9996 / 16.06 | 0.0604 | **2 条退化面 0.03 m** |
| 抖动归整 16.00 / 16.06 | 0.0600 | **仍 2 条 0.03 m** ⇒ 与那 0.4 mm 抖动无关 |
| 拉开 16.00 / **16.20** | 0.2000 | **0 条** |
| 完全对齐 16.06 / 16.06 | 0 | **0 条**（221 面，不切） |

⭐ **别把主因记错**：0.06 本来就 < 碎片下限 0.1，**不挪也会出碎片**。
⇒ 主因 = **跨层切分产生的碎片没有任何守卫**；吸附朝错方向挪只是**加重因子**（0.06 → 0.03）。

## 四、复现

```bash
E=AI_agent/logs/experiments/2026-08-25_kernel_probe_from_gt
python $E/tools/derive_draw_from_gt.py \
  case_tests/test_baseline/gt/sm25-L_anchor/gt.json \
  case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0/1_correction/correction_geometry.json \
  $E/out/draw_centerline.json --basis centerline
python $E/tools/probe_kernel.py $E/out/draw_centerline.json $E/probe_run --out-dir $E/out/kernel_centerline
```

`probe_run/` **不入库**（是 R0 的逐字拷贝，重复数据）；先重建它：

```bash
R=case_tests/e2e_tests/sm25-L_anchor/run_2026-08-25_c2_rescore_R0
mkdir -p $E/probe_run && cp -r $R/0_reading $R/_run $E/probe_run/
```

窗的引用链需要一份真实 `0_reading`，这是它存在的唯一理由。

判别矩阵单独跑（不需要 `probe_run`，也不需要任何 run）：

```bash
python $E/tools/concave_canonicalization_matrix.py   # 今天退出码 = 1
```

## 五、⛔ 本轮明确没做 / 存疑

- **没修任何 `src/`** —— 两条都在 `src/agent/geometry` · `src/validator`，属**须派工 + 换人审**那一类（CLAUDE.md §0.4#3）。
- **没跑 4_mep / 5_intakeoutput**（4_mep 要花 LLM 钱）；`3_split_pairing` 的序列化已跑通（282 行 surface_specs）。
- **F-91（立面多平面为空）本轮没查**。附带一条观测：答案输入下 `facade_segments` = **16 条、非空**，
  ⇒ F-91 的现象不出在这条路径上，但**这不构成 F-91 已消失的证据**。
- **`--basis outer` 那一支没跑通**（窗宿主冲突），所以「半个墙厚值多少分」这个量**本轮没有量到**。
