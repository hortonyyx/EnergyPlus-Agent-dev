# as-drawn 层契约（reading 观测层 → gt）

> **状态**：⭐ **2026-08-24 六审 APPROVE「可以开始动 gt」时随层落库的硬条件**
> （[六审裁决](../logs/reviews/verdict/2026-08-24d_support_strip_gate_recheck_verdict.md)）。
> 在 B 步（给 gt 加 as-drawn 层）产物落库之前，本文是**准入条件**；落库之后是**活契约**。
> ⛔ 违反其中任一条 ⇒ **该层产物不得记成绩、不得在任何文档里引用它的分数**。
> 分工与判分口径见 [本批开发指南](../guides/reading_correction_split_guide.md)；
> 实证与全部数字见 [实验档](../logs/experiments/2026-08-23_as_drawn_reading_prototype/README.md)。

---

## 一、⭐ 谁可以写哪一层（Finding 1，六审）

| 层 | 谁产 | 为什么 |
|---|---|---|
| **`observations`**（`runs_px` / `support_cols_px` / `gaps` / `calibration`）| ⛔ **只能由参考提取器机器产出** | 见下面那道墙 |
| **`declarations`** | 图纸/配置逐字转录 | —— |
| **`hypotheses` 里的 perception 字段**（族角色 · 配对选择 · 四个分桶 · 逐洞口门窗命名）| ⭐ **外来/模型输入只限这里** | 这些是「认」，本来就该模型做 |

**那道墙**：`runs_match_the_strip` 用参考提取器在原图上重算面线区间，**逐整数精确比对**。
六审实测：一份与参考提取器**只差 1 px**（≈5.9 mm，在一切在用容差之内）的合理外来读数
⇒ **49 条面线全红**，其余十门全绿。⇒ **当前形态下没有任何外来观测层能通过它。**

**⛔ 但这道墙不许松**：削尾家族是当前利润最高的作弊 ——
`foreign_1px` 把多画 0.722 → **0** 且十门全绿；`skip_unscored_tails`（只削不计分的尾）
C1 100 / C2 98.6 / **C4 0.215**，在 sm25 2F 上**只被这一道门**拦住，
而它每端只削 **1–2 px** ⇒ **任何 ≥1 px 的容差都直接放行**。

⇒ **修法不是改门，是这条契约。** 任何「为外来产物放宽 `runs_match` 容差」的改动，
**必须先证明它不放过 1 px 削尾**（验收夹具 = `out/sm25_1f_GLM_foreign_1px.json` 与
`skip_unscored_tails` 的 2F 版）。

---

## 二、⚠️ 已声明的盲区：画框与标定（Finding 3，六审）

`declarations.drawing_box_px` 与 `observations.calibration` 是**产物自报、零门重算**的承重孔径：
两道新门 + forward + reverse **全部按产物自报的框裁剪之后再重算**。

**诚实产物自己就靠这个框丢弃四成结构族墨**（六审实测）：

| | 结构族总墨 | 框外 | 占比 |
|---|---:|---:|---:|
| sm25 1F | 36,608 px | 15,167 px | **41.43%** |
| sm25 2F | 35,805 px | 14,517 px | 40.54% |
| sm24 1F | 36,258 px | 7,575 px | 20.89% |

**今天不赚钱**（六审攻击面 #4/#5 实测：目标包络钉死了框的可用范围，缩框赔 C2；
标定缩放 ±0.5% 内不可检出但远端赔 C1）。
⛔ **但它与五审的根因同构**（「所有自洽门都锚在产物自选的观测孔径上」），
而观测层一旦从别处来，自选框 + 自选标定就是敞开的。

⇒ **二选一，必须落字**：① 加门**从原图重导**画框与标定（镜像生产者定义）；
② 或**明确声明为已知盲区**并把上表这组数记在契约里（**当前选 ②**）。

---

## 三、⛔ 记成绩的四道闸（六审列，主控接受）

| # | 闸 | 状态 |
|---|---|---|
| 1 | **`span_min` 签字** —— 它等价于宣布「一堵墙漏画多少算漏」。⚠️ 六审实测：诚实 sm25 1F 有 **7 个目标的覆盖恰在 0.841**，而现行阈值 0.80 —— **悬崖离诚实值只有 0.04**。签字时必须知道这个数 | ⛔ **待用户** |
| 2 | **冷启隔离读图器首考** —— 不阻塞书写，**as-drawn 层落库后第一件事**；在它跑完之前本层任何分数不得记成绩 | ⛔ **待用户**（要花钱）。⚠️ 六审推断：按 §一那道墙，冷启读图器**不可能**通过 `runs_match` ⇒ 首考的对象只能是 **perception 字段**，观测层仍走参考提取器 |
| 3 | **永久矩阵不许打包陈旧产物** | ✅ **已修**（`run_all.py` 检查退出码 + 要求产物是本轮重写；验收 = `RESULTS_v2.glm_rework` 里 `band_collapse` / `fabricated_profile` 显示**红**，现已满足）|
| 4 | **本契约落字** | ✅ 本文件 |

---

## 四、口径备忘（容易被误读的两处）

1. **C1 是带阈值的判定，C2（长度覆盖）才是主读数** —— 挖掉每段中间 5/10/20/30/50% 时
   C1 = 100 / 99.1 / 10.2 / 10.2 / 10.2（阈值处是悬崖），C2 = 93.4 / 88.5 / 78.8 / 69.2 / 49.8（平滑）。
2. **`misname_opening_family` / `drop_opening_role` 现在 gt 侧 = 诚实**，⛔ 不是新洞：
   桥接**已经不看门窗族**、只看 perception 的逐洞口命名（F-87），族角色改由不读 gt 的
   `opening_role_matches_where_the_ink_sits` 门负责。

---

## 五、boundary facts 的真实存货与对账门（②-1d 返工）

### 5.1 ⛔ schema/谓词能力不等于落库存货

sm25 当前 facts 落库共 100 条 logical boundary edge：`exterior=32`、
`interzone=68`、`unclaimed_void=0`、`unknown=0`。后两档只有生产谓词级的
合成形态证明，**落库级真实存货仍为 0**；因此不得再表述为“真实 facts 已覆盖
四档”。新增真实 case 前，这两档仍是明确盲区。

`_boundary_footprint` 的 `exterior ring != 1` 分支也同样是**零真实存货**：
2026-08-30 普查的 sm24 plan-F1、sm25 签字件 F1/F2、sm25 as-received F1/F2
全是恰好一个 exterior ring；sm21 无 request，结构上不能进入该路径。
永久回归只能用**合成的第二 exterior ring**触发，⛔ 该夹具不是、也不得被描述成
真实语料覆盖。真实 sm25 的 2 m 顶点毛刺另有独立锁，但它覆盖的是“生产路径把
整层 boundary edges 静默清空后，门必须红”，不替上述 multi-exterior 分支冒充存货。

### 5.2 双向全集账本与失败半径

`reconcile_boundary_basis` 必须同时证明：

1. 每个 stored logical facts cavity ring 恰好配到一个 converter zone，且逐边
   方向/旋转、血缘和 basis 对账；
2. 每个 converter zone 都被一个 facts cavity 认领；若该 cavity 本来就不能形成
   logical boundary ring，必须作为**具名 exclusion**列出，⛔ 不计入 paired edges；
3. 生产几何仍能导出的 logical ring 不得从 stored facts 中消失；任一 view 的
   `boundary_edges=[]` 必须是结构红，零比较绝不等于一致。

正常 sm25 的账本读数是 converter zone `29/29` 全部有去向：25 个 ring、100 条边
逐边配对，另 4 个既有 NA cavity 明列 exclusion（F1-z0/z4/z5、F2-z0），所以
`paired_edges=100` 仍绿，但绝不把 4 个 exclusion 写成“已配对”。E3 删一 ring 只点名
该 ring；E2c 在所有 facts cavity 外多出的 zone 只点名该 zone；E4 空列逐 view/逐 ring
列出缺口。门只观测，绝不改写 facts `boundary_condition` 或 converter `basis`。

### 5.3 五项已知边界与接线

- **残差上限待签字**：`5_000` units（0.5 m）仍是待签数字，只用于限制跨表示
  配对残差（包含 cavity 内皮与 converter 墙中线/外皮之间的系统基准差），不得解释成
  几何正确性容差。sm25 的选中残差 0.247–0.339 m；外墙 offset ≥0.36 m 的方言可能
  对正确配对假红。进入下一份方言前必须 per-case 参数化或由用户签定，⛔ 本返工不
  就地发明替代数。
- **F-150 锁是列举式**：当前清空 6 个判断字段，并覆盖
  `diagnostics[].context` 这条自由 dict 通道；现有编译器消费面已被锁住，但未来新增
  第四个消费点不会自动进入清单，必须同步扩锁。
- **staging 接线**：官方 sm25 facts staging producer
  `build_sm25_facts_staging.py` 在写入三件套前强制运行本门并
  `assert_consistent()`；这属于 staging/走查，不改变、也不绕过 `promote_gt_v3`。
- **既有静默出口的处置**：`exterior != 1`、polygon invalid、以及未提供
  `min_room_area_m2` 导致不产 boundary edges 的既有路径，本返工按“纯门侧”禁令不改
  任一列；统一由非空/全集门具名变红。本实现没有新增静默出口。

---

## 六、这份契约的来历（六轮跨家族审，每轮都击穿过一次）

| 轮 | 家族 | 裁决 | 它找到的作弊 |
|---|---|---|---|
| 一 | sol | REJECT | 一条线两头读到、**中间没读到** |
| 二 | sol | REJECT | **一个像素**把整段墙桥回满分 |
| 三 | sol | REJECT | **把真的漏读说成洞口**（伪造空档证据）|
| 四 | GLM | REWORK | **画穿一扇真窗** · 塌中线 · 换表示法 · 带吞两面 · 剪不计分的墨 |
| 五 | GLM | REWORK | ⭐ **`band_collapse`：产物里没有一个假数，却优于诚实产物且八门全绿** |
| 六 | GLM | ✅ **APPROVE** | 八个攻击面**未找到赚钱的作弊**；两条未锚孔径写成本契约 |

⭐ **每一轮的作弊夹具都永久留在 `run_all.py` 的矩阵里** ——
一个曾经真的骗过判据的作弊，是最有价值的回归夹具。
