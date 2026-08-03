# R1 Slice 0 · right-to-left 全语料只读调查

- 日期：2026-08-02
- 施工席位：terra
- 范围：仅只读当前仓库的 reading 产物；未修改生产码、测试、配置或历史 run。
- 结论：仓库内有 **4** 个 `image_right_to_left` 声明，分布在 **2 个 run**；**0/4** 的数值真实反射，**4/4** 是 metadata 填错。建议走 **出路乙**（统一 left-to-right canonical x + 显式迁移），不建议仅为该历史语料引入双参数化。

## 0. 前提偏差与调查口径

派工单指定的第三份文件 `AI_agent/logs/reviews/request/2026-08-02_reading_ruler_r1_discussion_brief.md` 不存在。仓库内同内容的问题书实际为 `2026-08-02_reading_ruler_r1_discussion_brief_sol.md`（标题为“问题书 · 让 reading 的判卷尺子变得可信（R1）”）；本调查已读取该文件。此为派工单链接的命名偏差，不影响 Slice 0 的产物扫描。

扫描了现行 `case_tests/**/*.json` 的 1,029 个 JSON，并额外扫描 `AI_agent/logs/**/*.json` 中可解析的 JSON；排除 `backup/`、虚拟环境和源码/测试 fixture。识别规则为：直接 elevation view，或 aggregate `views`/legacy top-level view 内的 `image_kind: elevation`。

结果为 163 个 elevation-view artifact instances：

| 立面契约状态 | instances | 处理 |
|---|---:|---|
| 有 `facade` 对象且 `local_x_positive=image_left_to_right` | 67 | 非 RTL；保留声明、`mirrored`、span、window intervals、可用 binding 的采集结果 |
| 有 `facade` 对象且 `local_x_positive=image_right_to_left` | 4 | 下节逐条做 reflection 对照 |
| 旧产物没有 `facade` 对象 | 92 | 无 `local_x_positive` / `mirrored` 声明，故不能也不应臆测其方向；不能计入“right-to-left 声明” |

这 4 条是不同的物理立面观测（没有因 root alias / aggregate copy 而重复计数）。其余 67 条有声明的观测均为 left-to-right；所有 4 条 RTL 观测都带 `mirrored: "false"`。

## 1. 反射判定方法

对有可用 reviewed binding 的每条 RTL 观测：

1. 由完整 `outline` / `wall_fill` 的 x extent 取 façade span `L`。
2. 从同 run 的 `_run/judge_score_bindings.json` 读取 binding（均声明 canonical `image_left_to_right`），并以 `along_origin + sign × x_local` 将 GT 的 `world_along_interval` 反求为 binding-local target interval。
3. 对每个产品 window interval `[a,b]` 并列比较原值和按产品 RTL 声明应得的 `[L-b,L-a]`。这里判断的是**方向语义是否一致**，不是把产品本身的测量误差误说成满分：原值只要显著接近 binding target/其尺寸链而反射值显著远离，即为“metadata 填错”。

两个 run 都可使用各自的 hash-bound reviewed binding：

- `run_2026-07-27_haiku_e2e/_run/judge_score_bindings.json`
- `run_2026-08-01_haiku_unsup_A_prescan/_run/judge_score_bindings.json`

两份 binding 对 North 均为 `origin=10, sign=-1, canonical local=image_left_to_right`，对 West 为 `origin=20, sign=-1, canonical local=image_left_to_right`。GT 来源为 `case_tests/test_baseline/gt/sm24_anchor/gt.json`；因此 North 的 window binding-local target 是 `[0.54,5.34]`，West 的五个 target 是 `[14.66,19.46]`、`[10.08,11.58]`、`[7.36,8.86]`、`[4.42,5.62]`、`[0.54,2.04]`（顺序不构成配对要求）。

## 2. 逐条 RTL 证据

| run / artifact / facade | span；产品声明 | 产品 window x intervals | 若按声明反射 | binding 对照与结论 |
|---|---|---|---|---|
| `run_2026-07-27_haiku_e2e` · `0_reading/attempts/003/output.json` · North | `L=10`；`image_right_to_left`，`mirrored="false"` | `S3 [0.54,4.66]`；`S4 [6.74,9.46]` | `S3 [5.34,9.46]`；`S4 [0.54,3.26]` | binding window target 为 `[0.54,5.34]`。原 `S3` 左端相同、右端仅 0.68 m 的读图误差；反射后两个端点合计偏差 8.92 m。更直接地，产物自身 D2–D6 尺寸链按 `0→0.54→5.34→7.86→9.46→10` 顺序记录。**未反射，metadata 错。** |
| `run_2026-07-27_haiku_e2e` · `0_reading/attempts/003/output.json` · West | `L=20`；`image_right_to_left`，`mirrored="false"` | `S3 [0.84,2.34]`；`S4 [3.62,5.02]`；`S5 [6.92,8.42]`；`S6 [10.42,11.92]`；`S7 [13.02,17.82]` | `[17.66,19.16]`；`[14.98,16.38]`；`[11.58,13.08]`；`[8.08,9.58]`；`[2.18,6.98]` | 原 `S3` 贴近 canonical target `[0.54,2.04]`（端点合计误差 0.60 m），且 D2–D12 从左缘 `0` 单调写到右缘 `20`；反射后的 `S3` 被移到 `[17.66,19.16]`，不再对应该左端 target。其余 windows 亦是原值方向接近同序 targets、反射后顺序倒置。**未反射，metadata 错。** |
| `run_2026-08-01_haiku_unsup_A_prescan` · `0_reading/attempts/001/output.json` · North | `L=10`；`image_right_to_left`，`mirrored="false"` | `N6 [1.36,4.36]`；`N7/N9 [5.40,6.40]`；`N8/N10 [6.40,7.40]` | `N6 [5.64,8.64]`；`N7/N9 [3.60,4.60]`；`N8/N10 [2.60,3.60]` | 唯一 GT window target 为 `[0.54,5.34]`。原 `N6` centre 距 target centre 0.08 m；反射后 centre 相差 4.20 m。该产物的 D_n11–D_n15 也以 `0→0.54→5.34→7.86→9.46→10`（标注“left edge”）展开。**未反射，metadata 错。** |
| `run_2026-08-01_haiku_unsup_A_prescan` · `0_reading/attempts/001/output.json` · West | `L=20`；`image_right_to_left`，`mirrored="false"` | `W6 [1.04,2.04]`；`W7 [3.24,4.24]`；`W8 [5.44,6.44]`；`W9 [7.64,8.64]`；`W10 [11.84,15.84]` | `[17.96,18.96]`；`[15.76,16.76]`；`[13.56,14.56]`；`[11.36,12.36]`；`[4.16,8.16]` | 原 `W6` 贴近 canonical 左端 target `[0.54,2.04]`（右端精确相同），而反射将其移至右端 `[17.96,18.96]`。产物的命名也从 `W6` “far left” 向 `W10` “right-center”递进；D_w11–D_w21 按左缘 `0` 至右缘 `20` 编号。**未反射，metadata 错。** |

没有任何一条在 `x_canonical=L-x_product` 后与 reviewed binding 的 local target 更一致。四条均是“产品数值/尺寸链以 image-left-to-right 起算，但元数据写 image-right-to-left”；`mirrored=false` 不改变该结论。

## 3. 对三问的直接回答

1. **right-to-left 声明共 4 处**：`run_2026-07-27_haiku_e2e` 的 North、West 各一处；`run_2026-08-01_haiku_unsup_A_prescan` 的 North、West 各一处。其余有 facade 声明的 67 处都是 `image_left_to_right`；92 处旧 artifact 没有方向声明，不能被算作 RTL。
2. **数值真的反射：0 处；没反射、只是 metadata 填错：4 处。** 每一条的 span、raw interval、`L−x` interval、binding target 及产物自身 x 尺寸链证据均列于上表。没有“数据不足无法判定”的 RTL 条目；四条都有对应 reviewed binding。
3. **建议走出路乙：发布新 schema，统一 left-to-right canonical x，并对这 4 个错误旧声明做显式、hash-bound metadata migration。** 原因是当前仓库的 RTL 语料没有任何一个“合法但数值真的反射”的实例；保留双参数化会为一个不存在的历史编码族增加 score surface 和测试矩阵。迁移必须只修声明、保留 raw product bytes/原 hash、产出 postimage hash 和 migration rule/reviewer，不得原地改历史 `_run`、attempt 或 GT。92 个无方向声明的旧 artifact 不应在此结论下被猜测迁移；它们需要单独的 legacy/unsupported 判定规则。

## 4. Slice 边界

本 Slice 到此停止。未开始 S-1，等待 orchestrator 对出路甲/乙作设计裁定。
