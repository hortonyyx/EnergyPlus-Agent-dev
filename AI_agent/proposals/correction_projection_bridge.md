# 投影桥（墙 → 房间 → `CorrectedGeometry`）设计稿 v1

- **日期**：2026-09-02 · **作者**：orchestrator（主控）· **状态**：⛔ **未过审**，待跨家族对抗审
- **它是什么**：`1_correction` 新链最后一段 —— 把裁决完的**墙 IR** 变成几何内核吃的 `CorrectedGeometryV3`
- **为什么归主控出稿**：这是**几何派生的架构决定**，不是接线（[甲单裁定](../logs/reviews/request/2026-09-02a_wiring_module7_dispatch_v2.md) §表）
- **它挡着谁**：⭐⭐⭐ **sm25 端到端的唯一剩余关键路径**（新链已通，但终点是 `EvidenceChainTerminal`）

---

## 〇、一句话结论 + 一个要拍板的岔口

**结论**：投影桥**不能复用判分侧那份「墙→腔」的代码**，因为两边求的**不是同一个东西** ——
判分侧按**墙面**切出**净空腔**，而产品侧必须按**墙中线**切出房间（用户 2026-08-29 已拍板，理由是 EnergyPlus InterZone）。
⇒ 走**中轴平面剖分**（路 B），⛔ 不走「腔 + 逐边投影」（路 A），⛔ 不共享判分侧实现（路 C）。

**用户已拍板（§七）**：**全部落完再跑端到端，该分几批分几批。**
⇒ 本稿拆成 **B1–B5 五批**，B1（桥核心）可立即派工；⛔ 中途不试跑端到端。

---

## 一、这一步要做什么

```
[已通] 冻结字节 → adapter → 墙编译器 → 待裁决包 → 模型那一拍 → 决策循环
          ↓ 产出 WallCompilationV1.walls: list[ResolvedWallV1]
          ↓                       （中线 p1_m/p2_m · 沿墙区间 · 厚度 · output_basis）
[❌本单] ─────────────── 投影桥 ───────────────
          ↓ 产出 CorrectedGeometryV3（footprint · floors[].cells[] · windows · facade_segments）
[已有] 确定性核 → 2_modelling 造面 → 3_split_pairing → 4_mep → 5_intakeoutput → IDF → EnergyPlus
```

**现状**：[`pipeline.py:1255`](../../src/agent/pipeline.py#L1255) 在裁决产物落盘后**主动抛 `EvidenceChainTerminal`**
—— ⭐ 这是**对的**（provisional 不许冒充成品），本单就是把这个终点接上。

---

## 二、我自己量过的八条事实（⛔ 不是转引，每条可复算）

| # | 事实 | 出处 / 命令 |
|---|---|---|
| **1** | 投影桥**全仓零实现** | `grep -rn CorrectedGeometryProjectionEnvelopeV1` 只命中 [`pipeline.py:821`](../../src/agent/pipeline.py#L821) / [`:1261`](../../src/agent/pipeline.py#L1261) 两处**注释与异常文案** |
| **2** | ⭐⭐⭐ **gate① B3 要求 cells 平铺 footprint、不许有洞**，容差 **0.050 m²** | [`geometry_validator.py:85`](../../src/agent/correction/geometry_validator.py#L85) + [`correction.yaml:125`](../../src/configs/correction.yaml#L125) |
| **3** | ⭐⭐⭐ 判分侧的腔 = `footprint.difference(wall_region)` —— **墙带全是洞** | [`answer_compiler.py:862`](../../src/agent/judge/answer_compiler.py#L862) `_cavity_faces` |
| **4** | ⇒ **2 与 3 直接打架**：腔形态的 cells 会让 `hole_area` ≈ 全部墙面积（sm25 量级 = 几十 m²），**顶穿 0.05 m² 三个数量级** | 由 2、3 推出 |
| **5** | 墙编译器**完全不碰洞口** | `grep -c "opening" src/agent/correction/wall_compiler.py` = **0**；而 bundle 里 `opening_claims` 是有货的（[`evidence_contract.py:544`](../../src/agent/correction/evidence_contract.py#L544)）|
| **6** | 新链是**一次一份产物（= 一个视图）** | [`pipeline.py:1004`](../../src/agent/pipeline.py#L1004) `run_correction_evidence_chain(vector_dir, product_filename, floor_ref=…)`；而 `CorrectedGeometryV3.floors` 要**所有楼层** |
| **7** | `windows=[]` 时窗户门**空过成绿**（循环体不进） | [`geometry_validator.py:236`](../../src/agent/correction/geometry_validator.py#L236) |
| **8** | ⭐⭐⭐ **真实产物里 98 个面只有 46 个是单段连续**，52 个断成 2–6 段 | 实测 `sm24_1f_v2.json` 等 7 份：`runs` 分布 `{1:46, 2:35, 3:7, 4:4, 5:4, 6:2}` |

---

## 三、三条路，为什么选中轴剖分

### ⛔ 路 C：产品侧直接复用/import 判分侧的 `answer_compiler`
**否决，两条独立理由**：
1. **它算的是净空** —— 见事实 3/4，产出的东西 gate① 当场红。
2. ⭐ **判分会塌成自洽检验**：答案与产物由同一份代码派生 ⇒ **那份代码自己的错误对分数永远不可见**。
   F-153 就是这份代码里的真缺陷（静默吞掉 3 个被墙完全围合的真实房间，88.27 / 28.68 / 70.34 m²）——
   若产品侧同源，产品会**丢掉同样 3 个房间**，而对分**差异为零**。
   （同族：[[self-consistent-gates-anchor-on-product-chosen-apertures]]）

### ⛔ 路 A：镜像判分侧的形状（先切腔，再把每条边按 t/2 投影回中轴）
**不选，三条理由**：
1. **需要一份 footprint 作为被减数**，而生产侧**没有**（bundle 里没有 footprint 字段，实测）。
2. **继承 F-153 那一族的全部失败模式**（端头 `endcap` · `adjacent_projected_support_lines_are_parallel`）——
   那是**逐边投影**这个机制自带的，不是实现瑕疵。
3. 与判分侧**结构同构** ⇒ 虽然不共享代码，分辨力仍被削弱。

### ✅ 路 B：**中轴平面剖分**（本稿主张）
```
resolved_walls[].resolved_centerline（世界米，⭐ 连续整段）
      │
      ├─ ① 把每条中线延伸/裁剪到与【相邻中线】的交点     ← 设计稿 §5.2「角点来自相邻支撑线求交」
      ├─ ② 这些线段构成一个平面布置(arrangement)
      ├─ ③ cells = arrangement 的每个【有界面】          ← 一个面 = 一个房间
      └─ ④ footprint = 全部有界面的并集                  ⭐ 生产侧自己派生，不需要外部 footprint
      
      厚度 t 在这一步【不参与】—— 它只用于 ⑤ 外包形式(outer_skin) 与 ⑥ 造面时的构造层
```
⭐⭐⭐ **为什么切割用【中线】而不用【墙带】**：实测真实 as-drawn 产物（sm24 1F）
**98 个面里只有 46 个是单段连续**，其余 52 个被打断成 2–6 段（`runs_m`，事实 8）
⇒ **墙带的并集是有缺口的**，拿它求外环会漏。
而 `resolved_centerline` 的定义是 **span the EVIDENCE extent**、角点由**相邻支撑线求交**得到
（[`wall_compiler.py:246`](../../src/agent/correction/wall_compiler.py#L246) docstring）
⇒ **切割线天生连续，断的只是墙带** —— 这一步因此对洞口/断线免疫。
**为什么它天然对**（⛔ 不是"调得对"）：
- **B3 天然满足**：剖分的面**按定义**互不重叠且并集 = footprint ⇒ `hole_area = overlap_area = 0`，⛔ 不靠容差。
- **InterZone 天然配对**：相邻两房间共用**同一条中线** ⇒ A 的东面与 B 的西面**逐顶点重合**
  —— 正是用户 08-29 拍板要的（[指南 §出模形式](../guides/reading_correction_split_guide.md)：
  「内墙只能中轴，理由是硬的（⛔ 不是习惯）」）。
- **与判分侧不同源** ⇒ 判分保住分辨力。
- **零阈值**：不需要 `min_room_area_m2` 这种腔筛阈值（[[proxy-mistaken-for-the-thing]] 的正解形态）。

---

## 四、契约（按设计稿 §5.4，⛔ 不新造词表）

```text
CorrectedGeometryProjectionEnvelopeV1
  source_resolved_sha256      # = WallCompilationV1.content_sha256，绑死输入
  geometry                    # CorrectedGeometryV3，由同一份 walls 确定性派生
  completion = complete | degraded
  residual_evidence_debt_ids[]
  projection_sha256
```
**硬规则（设计稿原文，本稿不改）**：
- `strict` profile 在交给 judge 前**拒绝 `degraded`**；`exploratory` 可放行但报告必须显示 degraded，
  且**不得缩 judge 分母**。
- **丢 envelope / hash 对不上 / debt ids 与 `residual_evidence_debts` 不闭合 ⇒ 投影失败**，
  ⛔ 不得把裸 `geometry` 当完整产物。
- `output_basis` 值域**机械复用**判分侧 `CompiledZoneEdgeV1.basis: Literal["wall_axis","outer_skin"]`
  —— ⭐ **复用的是【值域】不是【实现】**，这不与 §三 的"不同源"冲突。

**失败语义（本稿新增，⛔ 需复核方攻）**：投影是**整层事务** ——
任一必需中线不可派生 ⇒ **整层响亮 NA**，⛔ 不许逐轴保留原样、⛔ 不许静默丢房间。
（立此条的依据 = F-153 的病族定性：**「有存货且被误读」比「零存货未登记」更危险**。）

---

## 五、目标态 vs 现状（⭐ 每格能指到 file:line）

| 环节 | 目标态 | 现状 |
|---|---|---|
| 墙 IR | 中线 + 厚度 + 沿墙区间 + basis | ✅ [`wall_compiler.py:270`](../../src/agent/correction/wall_compiler.py#L270) `ResolvedWallV1` |
| 决策循环 | 模型裁决 + 四个响亮出口 | ✅ [`decision_executor.py:327`](../../src/agent/correction/decision_executor.py#L327)（三家族各自跑通）|
| **墙 → 房间** | 中轴平面剖分 | ❌ **零实现（本单）** |
| **单层 → 多层** | 每视图一份 → 装配成 `floors[]` | ❌ **零实现**；链是一次一份产物（事实 6）|
| **洞口 → windows** | `opening_resolution`（设计稿 §5.4） | ❌ **零实现**；编译器 0 处提及 opening（事实 5），但 bundle 有货 |
| `facade_segments` | 立面分段 | 🟡 类型在（[`schema.py:292`](../../src/agent/correction/schema.py#L292)），**谁来填未定** |
| envelope 落盘 + attempt 消费 | 见 §四 | ❌ 零实现 |

---

## 六、验收怎么写（**规则形态**，⛔ 不写成现状名单）

| # | 规则 | 怎么证 |
|---|---|---|
| 1 | **任意一组合法墙 IR，剖分出的 cells 互不重叠且并集 = footprint** | 零阈值断言 `hole_area == 0 and overlap_area == 0`，⛔ 不用 `coverage_area_tol_m2` |
| 2 | **相邻房间共面**：任意内墙两侧的房间边**逐顶点相等** | 直接断顶点，⛔ 不断哈希（[[hash-of-whole-report-is-not-an-equality-test-for-its-parts]]）|
| 3 | **改一堵墙的厚度，房间边界不动**（中轴口径下厚度不改中线） | 变异实测：改 `resolved_thickness_m` ⇒ cells 逐顶点不变；⭐ 同时**外包形式下必须变** |
| 4 | **少一堵必需的墙 ⇒ 整层响亮 NA**，⛔ 不是少一个房间 | 摘一条中线，断异常码；⛔ 断言"没有静默产物落盘" |
| 5 | ⭐ **判分对本桥的缺陷有分辨力** | 人为在桥里丢一个房间 ⇒ **对分必须变**（这条直接验证 §三 路 C 的否决理由）|
| 6 | 端到端：sm25 一份产物走到 `CorrectedGeometryV3` 并过 gate① | 贴 gate① 逐项读数 |

---


### 六之二、⭐ 我自己认为最薄弱的三处（⛔ 请复核方优先攻这里）

| # | 薄弱处 | 为什么它可能塌 |
|---|---|---|
| **W1** | ⭐⭐⭐ **「把中线延伸到相邻中线的交点」这一步没有签字的规则** | 延多远算求交、延多远算**凭空造墙**？F-143/F-147 用户签的是**吸附**阈值（歪出 ≤10 mm 且角度 ≤1.0°），⛔ **不是延伸**阈值。而 ②-1a 的实证是：在**确定性 DXF** 上照样产出过 **33 条虚构墙**（[[deterministic-input-does-not-imply-correct-derivation]]）⇒ 这一步**必须有准入条件 + 测试函数名清单**，⛔ 不许写散文 |
| **W2** | **悬墙（dangling）与 T 形接头** | 一条中线两端都没碰到邻居 ⇒ arrangement 里不产生有界面 ⇒ 房间少一个。**它会不会静默？** 本稿要求整层响亮 NA（§四），但**判据是什么**没定死 —— ⚠️ F-153 形态 A 的病根正是 T 形接头上的单点采样 |
| **W3** | **「footprint = 全部有界面的并集」把【外轮廓】定义成了派生量** | 若某处外墙没围合，footprint 会静默缩小，而 B3 是拿**这同一个** footprint 当分母 ⇒ ⭐ **自洽门**：分母由产物自选，永远对得上（[[self-consistent-gates-anchor-on-product-chosen-apertures]]）。⇒ 大概率需要一个**外部**外轮廓来源来对账，而生产侧今天没有 |

## 七、✅ 用户已拍板（2026-09-02）：**全部落完再跑，该分几批分几批**

⛔ **原来那个「窗要不要一起做」的二选一作废** —— 派工方问得不准：
实测「一单做完」在今天的新链里**做不出窗**（`WindowV3.z` 必填而新链零 z 来源），
⇒ 两个选项在**产物上无法区分**。用户裁定 = **不将就，全落完再跑端到端。**

### 7.1 ⭐ 洞口的两半各有什么（实测）

| | 有没有来源 | 出处 |
|---|---|---|
| **平面半**（哪堵墙 · 沿墙区间 · 宿主房间 · 朝向）| ✅ 有 | as-drawn 平面产物的 `opening_claims`（⚠️ **纯引用**：只有 `opening_id`+`source_ref`，[`evidence_contract.py:498`](../../src/agent/correction/evidence_contract.py#L498)，桥里要解引用到 face 的 `gaps`）|
| **竖向半**（`WindowV3.z` = 窗台/窗顶）| ✅ **有，但没接线** | **sm25 四个立面的新格式产物已存在**且带 `"z_range_m": [0.181, 2.3111]` + 逐边尺寸链证据（`logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_{east,west,north,south}_as_drawn.json`）|
| legacy 立面 | ⛔ 这条路作废 | 旧视图确实带 z（`{"pen":"window","y_range_m":[1.0,2.8]}`），但**新链的 legacy 适配器写死 `opening_claims=[]`**（[`evidence_adapters.py:662`](../../src/agent/correction/evidence_adapters.py#L662)），且用户 09-01 已拍「旧格式不兼顾」|

⭐ **立面腿比预估便宜**：`as_drawn_elevation_v0` **契约已在册、分类器认得**
（[`vector_contract.py:275`](../../src/agent/reading/vector_contract.py#L275)），只是处置写着 `KNOWN_NOT_CONSUMED`
⇒ **它今天的位置 = 平面产物在模块 3 之前的位置**，是「改处置 + 写适配器」，⛔ 不是从零设计。

### 7.2 ⏭ 批次表（⛔ 端到端跑测排在最后，不中途试跑）

| 批 | 内容 | 前置 | 交付判据（规则形态）|
|---|---|---|---|
| **B1** | ⭐ **投影桥核心**：中轴平面剖分 → cells + footprint；envelope 契约与失败语义 | 无（**可立即派**）| §六 规则 1/2/3/4 |
| **B2** | **多楼层装配**：每视图一份 → `floors[]`（层高 / `z_floor` 的来源要有出处）| B1 | 两层 case 装出 `floors` 且逐层 B3 零洞零重叠 |
| **B3** | **as-drawn 立面腿**：处置改 ADAPT + `adapt_as_drawn_elevation` + 把 `openings[].z_range_m` 变成**带引用的证据** | 无（可与 B1 并行，⛔ 但不同家族）| 四个立面产物全部能进 bundle；z 带 `source_ref` |
| **B4** | ⭐⭐ **洞口合成**：平面半 × 竖向半 → `WindowV3`（宿主房间 · facade · span · z）| B1+B2+B3 | 见下方 ⚠️ |
| **B5** | **端到端** sm25 → IDF → EnergyPlus | B1–B4 | 一口气跑通 ≥3 次（[[one-shot-acceptance-bar-kills-false-claims]]）|

⚠️ **B4 里藏着一个真问题，⛔ 别当接线**：**平面上的那个洞口，和立面上的那扇窗，是同一扇吗？**
这是**跨视图身份配对**，两边的坐标系不同（平面 = 世界 xy；立面 = 沿墙局部 + z）。
⛔ 不许用「按顺序配」或「按最近距离配」这类没人签字的启发式
（[[silent-default-threshold-behind-otherwise-conclusions]]）⇒ **B4 要单独出方案，⛔ 不直接派施工**。

## 八、⛔ 本稿明确不做

改判分侧任何代码 · 修 F-153 / F-157 / F-158 · 动 `as_measured.py` ·
⛔ **不中途试跑端到端**（用户 09-02 定）· 做外包（`outer_skin`）出模形式的**实现**（本稿只要求算法对 basis 参数化，⛔ 不要求两种都落地）·
多层装配的**实现**（⭐ 但契约要留出接缝，见 §五）。
