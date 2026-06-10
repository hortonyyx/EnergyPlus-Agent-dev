# 切配（split-pairing）确定性内核 — 技术参考 + 落位决策

> **⚠️ 决策反转（2026-06-09，用户定）**：切配**收回本项目侧自己做**，不再「归下游」。落位 = **确定性算法，紧接确定性核之后、吃 `CorrectedGeometry` 的 cells 做**（详见 §6）。推翻 2026-06-07「下游另有人做、不归本项目管」的旧定性。
>
> **触发证据（2026-06-09，sm20/sm21 对照）**：见 §2.5。一步出 LLM 能把切配做对（sm20 三层 7/8/4 更难也 0 门 issue、真切子面），**staged 反而退化**（sm21 staged 12/26 issue）——证明切配不是「LLM 做不到」，是 staged 架构把这块跨层几何活儿孤立成 LLM 机械记账杂活、做不稳。结论：**该确定性化、在我方做**。
>
> 下文 §0–§5 是技术参考（切配是什么 / 确定性实现路子 / 关键认知），§6 是落位决策。

---

## 0. 术语（2026-06-07 锁定）

- **切配** = 把几何建模产物（相邻 zone/楼层之间的面**不**一一对应）切成 EnergyPlus 要求的**一一对应**关系（每个 InterZone 面恰好配一个对面 zone 的面）。
- **已定为确定性几何算法**（不是 LLM）。**独立、与两条线（忠实建模 / 热区再拓扑）无关**——两条线只在 zonification 分叉，产出的 zone 体块（粒度不同）都喂同一个切配。
- 管线位置：phase1 → 校正 → zonification → 几何建模(升起) → **切配** → EP。

---

## 1. 切配要解决的问题

EP 模型要求 InterZone 边界**逐面一对一对应**（不是几何建模那种一对多）。当相邻楼层 / 相邻 zone 的分区不一致时，一道墙/楼板要切成多片、每片配一个对面 zone 的面，且两面互逆引用（`outside_boundary_condition = Surface`，`..._object` 指向对面面）。

输入 = 一摞 zone 体块（每个有底面多边形 + z 范围 + 6 个面）。
输出 = 切好、配好、设好互逆 OBC 的面集合，写进 IDF。

确定性算法核心步骤（对标 OpenStudio 的 intersect / match）：
1. 取相邻面（同平面、法向相反的候选对）。
2. 求两侧多边形在公共平面上的**break 点并集**，按之切分成子多边形。
3. 每个子片**恰好配**对面一个 zone 的对应子片。
4. 设互逆 OBC + 反序/同一 construction（EP 要求配对面材料层互逆）。

---

## 2. 现状（本项目当前怎么做切配）

当前切配**没有任何确定性几何算法**，分散在两个 LLM 环节 + 一个事后门：

```
phase2(DeepSeek,纯文本)    逻辑切分 + 配对枚举(谁切在哪子区间、谁配谁 zone)  ← 决策, 我方
   ↓ surface_specs 文本
surface_agent(下游 LLM)    几何实现(子区间文本 → 3D 顶点 + 互逆 OBC 引用)    ← 实现, 协作者方
   ↓ create_surface
surface_converter(纯代码)  照单写入 IDF, 只逐面校验形状, 不验配对图
   ↓
interzone.py 门(确定性)    事后校验整张配对图(8 项), 不切面                  ← 裁判, 我方
```

- 切分**决策**在 [skills/energyplus_mcp_twostep/phase2/rules.md](../../skills/energyplus_mcp_twostep/phase2/rules.md) §2.6 / Step 4（phase2 文本心算 O(n×m) break 点并集枚举）。
- 几何**实现**在 [src/agent/nodes/surface.py](../../src/agent/nodes/surface.py)（surface LLM 把子区间变顶点、设互逆引用）。
- 事后**裁判**在 [src/validator/interzone.py](../../src/validator/interzone.py)（装配后 EP 前 fail-fast，8 项：目标存在/是 Surface/互逆/单一引用/面积匹配/法向相反/共面/最小边长≥0.1m）。**只裁不切。**

**这套的债** = 切分决策+实现全是 LLM、靠 prompt 合规；sm21 三模型实验证明文本心算切配脆（同一道墙跨层 5cm 抖动→退化碎片→EP 段错）。把它换成确定性算法正是切配内核要做的事。

---

## 2.5 sm20/sm21 对照（2026-06-09）— 触发"切配确定性化在我方"决策的证据

拿现在的 InterZone 门审历史 IDF + sm21_pre 新跑：

| 案例 | 流程 | 跨层 | 门结果 | 备注 |
|---|---|---|---|---|
| sm20 | **一步出** phase2 | 3层 7/8/4（最错配） | **0 issue** | 19 zone → 26 floor 面/23 ceiling 面，**真切了子面**、45 互逆对 |
| sm21 | **一步出** phase2 | 2层错配 | **0 issue** | （几何有"幽灵房"尺寸错，但配对图自洽）|
| sm21_pre | **staged** phase2(2a/核/2b) | 2层错配 | **12 issue** | 几何更忠实，但切配崩 |
| sm21(6.7) | **staged** | 2层错配 | **26 issue** | 同上 |

**解读**：一步出 LLM 整栋楼同上下文整体推理，切配**自然涌现且做对**（sm20 更难也对，不是运气）；staged 把 phase2 拆成 per-floor 校正后，**没有任何一段"拥有"跨层切配**——phase2a 逐层、核只轴吸附、phase2b 被要求从抽象 cells 机械推导跨层切配（LLM 机械几何记账的弱项）。**不是信息变少**（cells 含全部跨层几何、比矢量更干净），**是把一块确定性几何活儿孤立出来又塞回给 LLM**。→ 该确定性化、在我方做（§6）。

---

## 3. 确定性实现的两条候选路子

### 3.1 自写（建在 shapely + idfpy 上）
- **shapely**：做平面集合代数（多边形并/交/差/break 点切分）——切分主力。
- **idfpy**：数据模型 + schema + IO + 几何 mixin（`area/normal/centroid`、`surface.zone` forward nav）。让"自写切分/匹配内核"从在 eppy 上硬刚降成在 idfpy 上拼装（[deferred/idfpy_embed.md](../deferred/idfpy_embed.md) §3.1 估"自动 boundary 推断实现量级降低 ~10×"）。
- shapely 与 idfpy **互补**：idfpy 出干净 surface 多边形，shapely 做 footprint 集合代数。idfpy 替代不了 shapely。

### 3.2 借 OpenStudio SDK（intersect / match）
- OpenStudio 自带 surface intersect + match boundary 的成熟实现（BEM 工业级、久经考验）。
- 代价 = 引入 OpenStudio SDK 依赖（重）；需评估 license / 部署 / 与现有 eppy/idfpy 栈的衔接。

> 选型对比（能力覆盖 / 依赖重量 / license / 确定性保证 / 引入成本）属下游做切配那方的决策，本参考只列两条路，不替其拍。

---

## 4. 关键认知（别踩的坑）

1. **idfpy 不自动解切配/覆盖**：idfpy `validate()` 是 **schema 校验、不验几何**。覆盖洞 / 切错是**几何缺陷不是 schema 违规**，`validate()` 会愉快放行。别指望切 idfpy 像消掉 glazing bug 那样消掉切配问题（glazing 是 schema 约束所以能被原生拒，切配/覆盖不是）。
2. **覆盖完整性 vs 配对合法性是两件事**：interzone 门（及切配内核）查的是"已声明配对是否合法"；另有一类"覆盖洞"（本该是内部边界、两侧却都标 Outdoors/Adiabatic → 不进配对图 → 门盲、EP 也不报错）需 footprint 并/交/差（shapely）专门查。若 zonification 端能保证输出是**合法平面剖分**，覆盖洞可升为"构造不变量"从源头消解（见 [architecture/geometry_first_zonification.md](../architecture/geometry_first_zonification.md) §4.3）——这是 zonification 端的事，与切配互补。
3. **切配与 zonification 解耦**：切配吃任何粒度的 zone 体块都同一算法。zonification 范式（忠实房间=zone / 热区再拓扑少而大）只改输入基数，不改切配算法。两件事可独立推进。
4. **所有权边界**：当前几何实现在 [surface.py](../../src/agent/nodes/surface.py)（协作者方 LLM）。**新决策（§6）下，切配在我方核之后做、产出已解析的 surface_specs**，下游 surface_agent 退化成忠实誊写——所以**不动下游代码、不改 `IntakeOutput` 契约**（我们交出去的 surface_specs 几何已完整解析，反而帮下游）。这比"下沉到下游 surface.py"更省、不跨所有权边界。

---

## 5. 相关文件

- [src/validator/interzone.py](../../src/validator/interzone.py) — 现 per-pair 确定性门（切配内核的事后校验可由它退化成 sanity check）
- [src/agent/nodes/surface.py](../../src/agent/nodes/surface.py) — 现 LLM 几何实现（切配内核要取代的）
- [src/converters/surface_converter.py](../../src/converters/surface_converter.py) — 纯写入
- [skills/energyplus_mcp_twostep/phase2/rules.md](../../skills/energyplus_mcp_twostep/phase2/rules.md) §2.6 / Step 4 — 现切分决策文本规则
- [AI_agent/deferred/idfpy_embed.md](../deferred/idfpy_embed.md) — idfpy 切换计划（切配内核的使能器）
- [AI_agent/architecture/geometry_first_zonification.md](../architecture/geometry_first_zonification.md) §7.2 — idfpy/shapely 分工分析

---

## 6. 落位决策（2026-06-09，用户定）— 切配在我方、核之后、吃 cells

**在哪做**：确定性「造面/切配内核」，**紧接 [确定性核](../../src/agent/correction/deterministic.py) 之后**，吃 `CorrectedGeometry` 的 cells（核已握全楼层规整矩形 + 世界坐标）。

**为什么是这个位置**（对标全流程目标架构，见 [pipeline_stage_contracts §0.1](../architecture/pipeline_stage_contracts.md)）：
1. **最早的"干净且齐全"点**：核之后跨层几何第一次同时干净（已吸栅格）+ 齐备（全楼层 cells）。再往下被抽象成自然语言 surface_specs，难逆推。
2. **纯确定性几何**：矩形求交（现在，numpy）/ 多边形求交（B5 用 shapely）。无判断成分，不该让 LLM 碰。
3. **顺"几何=代码 / 语义=LLM"不变量**：把这条线从"cells 确定性、cell→面+切配 交 LLM"下移到"**所有几何面生成（造面+OBC+互逆+切配+顶点）全确定性**"。

**范围**：不只切配——**整个 cell→surface 几何生成**（每 zone 的墙/楼板/天花面 + OBC 判定 + 跨层切分 + 互逆引用 + 顶点合成）都收进这个确定性内核。它**整块吃掉** rules.md §4/§2.6 + surface_agent 里那些脆弱的几何指令。LLM（phase2b/未来 phase3）此后只做语义/物理（材料/时间表/荷载/命名），不碰任何几何。

**对契约的影响**：产出**已完整解析的 surface_specs**，下游 surface_agent 忠实誊写。`IntakeOutput` 11 字段契约不变、下游代码不动（见 §4#4）。

**实现节奏**：矩形情形现可落（在 [deterministic.py](../../src/agent/correction/deterministic.py) 旁加 split/造面模块）；非矩形（L/U、退台）随 B5 上 shapely。是块实打实的活（等于写确定性造面器），高价值、与 #2.1/#2.4/phase3 同向。

---

## 7. 落地状态（2026-06-09，0–5 重构 Step 2–6）✅ 矩形已落地

切配确定性内核**已建成并接进主链**（shapely 多边形原生）：
- 造面+切配：[src/agent/geometry/split_pairing.py](../../src/agent/geometry/split_pairing.py)（同层内墙互逆配对 + 跨层楼板/天花切分配对 + roof/ground + 重叠守卫）+ [modelling.py](../../src/agent/geometry/modelling.py)（zone 体块 + 面顶点合成）。**leg-agnostic**：吃 `list[ZoneVolume]`，任何 zonification 粒度同算法。
- 接线：[phase2.py](../../src/agent/phase2.py) `run_phase2` 核之后 build_geometry → [specs.py](../../src/agent/geometry/specs.py) `serialize_geometry` 序列化成 `surface_specs` → **fork (a)** 下游 surface_agent 忠实誊写。`IntakeOutput` 契约不变、下游不动。
- 验证：[tests/test_geometry_kernel.py](../../tests/test_geometry_kernel.py) 8 测对标 InterZone 门 0 issue（含 sm20-shaped 三层 4/3/2 错配）。**事后裁判** = [interzone.py](../../src/validator/interzone.py) 门（退化成 sanity check，§5 已预言）。
- **待**：非矩形端到端 case 随 B5；sm21_pre e2e = Step 8。fork (b)（确定性直接造面绕过下游）记录待后续整合再议。

---

_2026-06-09 — **决策反转**：切配从"归下游、不归本项目"改为"**我方确定性做、核之后吃 cells**"。源 = sm20/sm21 对照（§2.5）证明 staged 切配退化是架构把确定性几何活儿塞给 LLM，非 LLM 不能。banner + §2.5 + §4#4 + §6 更新。_

_2026-06-07 建档 — 主开发 Agent。源 = 几何管线术语锁定后，把切配从"再拓扑"里摘出作独立 leg-agnostic 确定性轨。（彼时定"实现归下游"，已被 2026-06-09 推翻，见上。）_
