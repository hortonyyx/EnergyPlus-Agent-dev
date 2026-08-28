# 派工单 · ②-1a：**事实层 `as_measured` 落库**（as-received 源 + S7 之前截取 + 逐位可复现）

- **日期**：2026-08-28 · **派工方**：orchestrator · **施工**：待定 · **审**：跨家族
- **档位**：工程档 · **基线**：单1（F-133）交件并收口之后的 HEAD
- **上位**：用户 2026-08-28 授权「统筹推进，按应该的顺序」；本单 = 第 ② 步主线的第 1 单
- **相关口径**（⛔ 动手前必读）：
  [落库方案](../../architecture/gt_revision_ledger.md)（三截结构 + §十 as-received 裁定）·
  [本批指南 §十](../../guides/reading_correction_split_guide.md)（08-28 六条）·
  [F-122 / F-124 / F-134](../../plan.md)

---

## 〇、⛔ 先读

1. **本单只做事实层的第一截 `as_measured`。**
   ⛔ 不做 `revisions`（②-1b）· ⛔ 不做 `as_signed`（②-1b）· ⛔ 不做 `AnswerCompiler` / 出模形式（②-1c）·
   ⛔ 不做 `boundary_condition`（②-1d）· ⛔ 不做 B1 指纹锚（②-1b）· ⛔ 不碰 correction / geometry 内核。
2. ⛔⛔ **绝对不许 `pip install -e .` / 任何写 `site-packages` 的命令。**
3. **停下上报分层**：承重前提错 ⇒ **停下上报**；外围数值错 ⇒ 记一行继续。
   ⚠️ 派工方累计题错 **41+** 次，且**本条线上派工方今天已经自查推翻过三版**（见 §五）。
4. ⛔ **不许改任何哈希、不许绕过任何门。** 门挡住就是门挡住了 —— 那是本单要正经解的第一件事。

---

## 一、承重前提（已实测，⛔ 但请自己复核一遍）

### 1.1 as-received 图今天**跑不通**

```
sm25-L_t3.dxf              sha256=1251f6515382…   ✅ denominator() 跑通，plan-F1 targets=110
sm25-L_t3_as_received.dxf  sha256=4a94922489d3…   ⛔ DenominatorUnavailable
                                                     BLOCK: tarch_input_source_hash_mismatch
```

原因：`gt_sources/sm25-L_anchor/request.json` 的 `source_dxf_sha256` 钉的是**签字件**。
⭐ 报错是**响亮的**（F-126 的修复在起作用），⛔ 不再静默返回空分母。

⚠️ **08-29 那个「原图 108 目标 / plan-F2 106」的读数是【临时改签哈希】拿到的**（探针在 scratchpad，未进仓库）。
⇒ ⛔ **本单不许重复那个做法。**

### 1.2 事实层的原料 = **P1（S0–S4）的输出**，⛔ 不是 S7

[`P1PlanViewGeometry`](../../../src/agent/judge/tarch_normalize.py#L204) 已经带齐要的每一样：
`wall_lines`（量化后的面线，含 handle）· `wall_bands`（配好的墙）· `openings` ·
`footprint_polygon` · `dangles / cuts / invalid` · `diagnostics` · `wall_line_layers`。

⇒ **F-122 的要求由此自动满足** —— F-122 实测 `ZoneEdgeReportV1.p1/p2/basis/offset` 是
**S7 扩张之后**的答案边（`offset == (t if outer_skin else t/2)` **136/136** = 生产者公式的回放；
**272 个端点全部离开原 cavity 0.06–0.34 m**）。⛔ **一个字段都不许从 S7 复制过来。**

---

## 二、要做什么（三件）

### R1 · **as-received 的转换请求书**（⛔ 不许改哈希）

让 `as_measured` 能在 **as-received DXF** 上正经跑出来。**做法由你判断**，两条路我都能接受：

| | 做法 | 注意 |
|---|---|---|
| **甲** | 新增一份 `request_as_measured.json`，`source_dxf_sha256` 指向 as-received 件 | 简单；⚠️ 但**两份 request 会各自漂移**（F-130 的形状），要说清谁是谁的下游 |
| **乙** | 让 `TarchConversionRequestV1` 显式声明**两个源**（`authorized_source` + `as_received_source`），门按用途选 | 更正确；⚠️ 但**碰签名 payload 就会让签字件失效** ⇒ **⛔ 不许进签名 payload**，只能加在 payload 之外或走版本闸 |

⭐ **无论哪条，都要保证**：签字件 `request.json` 的 **`compute_request_sha256` 逐位不变**
（sm25 = `d738d0ac…`、sm24 = `ae0fec08…`、sm24 manifest = `c40cbc8b…`）。**贴前后对照原文。**

### R2 · `AsMeasuredV1` schema + 从 P1 截取

**存什么**（逐层、逐视图）：

| 字段 | 内容 | ⛔ 注意 |
|---|---|---|
| `face_lines` | 每条面线：`handle` · 轴向 · 常数位 · 沿墙区间 | ⭐ **坐标一律 0.1 mm 整数**（⛔ 不存浮点，用户 08-29 定）|
| `walls` | 由 `wall_bands` 来：两条面线的引用 + 厚度 + 沿墙区间 | 厚度是**派生量**（两面线之差），但**落盘**，且必须能从两条面线逐位重算 |
| `openings` | 由 `openings` 来：位置 · 宽度 · 承载墙引用 | —— |
| `footprint` | 外轮廓环 | —— |
| `converter_readouts` | `dangles` / `cuts` / `invalid` / `diagnostics` | ⭐ **原样搬**，⛔ 一个几何都不要重算（08-29 教训：转换器早就算了，是消费方把读数丢在地上）|

⛔⛔ **明令不存的三样**：
1. **`basis`** —— 外皮/中轴是**出模形式的选择**，不是测量事实（指南 §十.6b）⇒ 归 ②-1c
2. **扩张后的端点** —— F-122
3. **`boundary_condition`（内外墙身份）** —— 归 ②-1d（sol B5）

### R3 · **逐位可复现门**

> 同一份 as-received DXF + 同一份 request + 同一份代码，**重跑两次，`as_measured.json` 字节相同**。

⚠️ **已知坑**：仓库登记过「转换器输出依赖 Python 哈希随机化」（同输入同代码两次跑，规范化 DXF 字节与
`content_sha256` 戳不同，固定 `PYTHONHASHSEED` 即稳定）。
⇒ **本门必须自己扛住这件事**（排序全部显式、⛔ 不依赖 `set`/`dict` 的遍历序），
⛔ **不许靠"跑测时设 PYTHONHASHSEED"糊过去**。**请实测两次跑并贴哈希。**

---

## 三、验收（⛔ 每条都要能不通过）

1. ⭐ **签字哈希逐位不变**：sm25 request `d738d0ac…` · sm24 request `ae0fec08…` · sm24 manifest `c40cbc8b…`
   ⇒ **贴前后两组原文。**
2. ⭐⭐ **as-received 图真的跑通了**：贴 `plan-F1` / `plan-F2` 的面线数、墙数、洞口数。
   ⭐ **并与签字件的读数对照** —— 已知应有差异（**F-129**：F1 侧签字件 110 目标 / as-received 108 目标，
   差一堵 120 mm × 3.64 m 的内隔墙；F2 两侧逐位相同）。**对不上 ⇒ 停下上报。**
3. ⭐⭐ **逐位可复现**：两次跑的 `as_measured.json` sha256 **相同**，⛔ 且**不许设 `PYTHONHASHSEED`**。
   **贴两次哈希原文。**
4. ⭐ **反空转**：证明这门不是恒真 —— 造一处会让它红的改动（例如把一条面线挪 0.1 mm），实测变红。
5. ⭐ **零 S7 依赖**：`grep` 证明新代码**没有引用** `ZoneEdgeReportV1` / `ZoneExpansion` / `s7_expand_zones`。**贴 grep 原文。**
6. **整数表示**：断言 `as_measured.json` 里**每一个坐标都是整数**（0.1 mm 单位），⛔ 没有浮点。
7. **全量** `pytest -n 6`（⛔ 无 `-m`、⛔ 不用 `-n auto`）+ **`.pth` 前后哨兵**。贴汇总行原文与基线读数。
8. **范围**：贴 `git diff --numstat` 原文。

---

## 四、⚠️ 边界（本单**明确不解**，⛔ 不许顺手做）

- **B1 外部获授权指纹锚** ⇒ ②-1b（它要和 `revisions` 的信任根一起设计）
- **F-D 指纹只盖一个文件** ⇒ ②-1b
- **那 5 条线的 `revisions` 记录** ⇒ ②-1b
- **`as_signed` 派生** ⇒ ②-1b
- **F-132 sm24 晋升件已漂移** ⇒ 随 gt 重签
- ⭐ **一致性检查重接事实层** ⇒ 事实层落库之后单独做（含今天新加的「分区线 vs 墙中轴」一类）

---

## 五、⚠️ 派工方在这条线上今天已经推翻过自己三版，请主动证伪

1. ⛔ **拿死代码当证据**（`_build_axis_map` 全仓零调用）⇒ 请自己 `grep` 确认你要改/要读的每一处**都在真实调用链上**。
2. ⛔ **把两个不同的常量混为一谈**（内核 `_MIN_EDGE` vs correction 轴合并参数）。
3. ⛔ **给用户的建议与用户自己 08-29 的裁定相反而没查到**（F-124 销账取①、今天改判取②）。
   ⇒ **若你发现本单某条与某份文档里已有的口径冲突 ⇒ 停下上报**，⛔ 别自己挑一个执行。
4. ⚠️ **§一.2「P1 已带齐事实层要的每一样」是我读 dataclass 字段得出的判断，没有逐字段验过是否够用。**
   若你发现**缺了某样必需的东西**（例如面线的 layer 归属、洞口与承载墙的引用关系）⇒ **停下上报**，
   ⛔ 不要自己去 S5–S7 里取——那正是 F-122 的坑。
