# 几何优先 + 平面再拓扑：长期建模架构设计

> **定位**：一份**前瞻架构设计文档**（design proposal），不是已落地的事实参考。记录 2026-05-29 一次会话收敛出的长期建模架构方向——把"surface 切分/配对"从 LLM 文本推理下沉为「**平面再拓扑（热分区）+ 确定性几何内核**」。
>
> **状态**：**设计讨论已捕获，未落地实现。** 当前主线仍是已交付的两步法（phase1 半人工 + phase2 DeepSeek + 9 下游 subagent，[architecture.md](architecture.md)）。**2026-05-29 定调：本文是与「忠实建模 leg」并行的「再拓扑 leg」——作强力支线推进，实验稳定了再切过去**（它 EP 鲁棒性最优但相对原始信息变化最大、最激进；忠实 leg 因 beyond-EP 价值独立继续）。落地时机见 §9，两腿分工见 [../capability/recognition_modeling_capability.md §8](../capability/recognition_modeling_capability.md)。
>
> **与其他文档关系**：[architecture.md](architecture.md) = 当前事实架构；[../capability/recognition_modeling_capability.md](../capability/recognition_modeling_capability.md) = **另一条腿（忠实建模 leg）** + 识图→建模质量主线；[../deferred/idfpy_embed.md](../deferred/idfpy_embed.md) = idfpy 切换计划；[../plan.md](../plan.md) B5-B7 = 能力升级任务。本文是再拓扑 leg 的**架构骨架**。

---

## 1. 起点：当前 split-pairing 是怎么做的

EP 模型要求 InterZone 边界**逐面一对一对应**（不是几何建模那种一对多）。当相邻层分区不一致时，一道墙/楼板要切成多片、每片配一个对面 zone。这件事当前在管线里分四个环节完成，**没有任何一处用确定性几何算法**：

```
phase2(DeepSeek,纯文本)         逻辑切分 + 配对枚举(谁切在哪子区间、谁配谁 zone)
   ↓ 写进 surface_specs 文本
surface_agent(下游 LLM)          几何实现(子区间文本 → 3D 顶点多边形 + 互逆 OBC 引用)
   ↓ 调 create_surface 工具
surface_converter(纯代码)        照单写入 IDF,只逐面校验形状,不验配对图
   ↓ 装配成 IDF
interzone.py 门(确定性)          事后校验整张配对图(8 项),不切面
```

- **切分决策**：[skills/energyplus_mcp_twostep/phase2/rules.md §2.6](../../skills/energyplus_mcp_twostep/phase2/rules.md)——phase2 在两叠层 x/y break 点并集处切分，逐片枚举进 `surface_specs`（子区间 + zone 级配对，**不出顶点**）。
- **几何实现**：[src/agent/nodes/surface.py](../../src/agent/nodes/surface.py)——surface LLM 代理读文本，把子区间变顶点、设互逆引用。
- **纯写入**：[src/converters/surface_converter.py](../../src/converters/surface_converter.py)——`newidfobject` 直写，逐面形状校验，不看引用图。
- **确定性裁判**：[src/validator/interzone.py](../../src/validator/interzone.py)——装配后、EP 前 fail-fast，验 8 项（目标存在/是 Surface/互逆/单一引用/面积匹配/法向相反/共面/最小边长≥0.1m）。

**核心事实**：切分**决策**（phase2）+ **实现**（surface_agent）全是 LLM，靠 prompt 合规。interzone 门是**事后裁判、不是执行者**。

---

## 2. 现状的结构性问题

### 2.1 两个本可分离的关注点被揉进了 phase2 文本

| 关注点 | 本质 | 当前归属 | 应归属 |
|---|---|---|---|
| (a) zone 在哪 | footprint 多边形 + z_floor + 层高 | LLM(phase2) | **LLM**（需识图/推理，本分） |
| (b) 面怎么切、怎么配 | 给定 (a) 后的**纯几何**：相邻面相交、break 点切分、互逆配对 | LLM(phase2 心算 + surface_agent) | **确定性算法**（不需 LLM） |

把组合性的 (b) 塞进纯文本 LLM 心算（O(n×m) 的 break 点并集枚举），是当前设计的债。

### 2.2 interzone 门抓不到的"覆盖洞"

门只审**已声明的配对**是否合法。它抓不到这一类：**本该是内部边界（楼板 / 相邻 zone 间的墙），两侧却都被标成 Outdoors/Adiabatic → 该区域根本不进配对图 → 没有"对"可裁，EP 运行也不报错**（每个面单独合法，物理却凭空多了内外边界）。

抓它需要"相邻层 footprint 求并→求交得该铺满的范围，所有水平配对多边形求并得实际铺到的范围，求差≠空=洞"——多边形并/交/差，需 `shapely`。已决策走 shapely 长期解、当前仅标记（见 [../logs/downstream_agent_changes.md](../logs/downstream_agent_changes.md) 2026-05-29 条）。

---

## 3. 风险随复杂度升级（定落地时机的依据）

覆盖洞 + 切错的概率不是常数，随几何复杂度抬升，拐点正好在路线图前方：

| 阶段 | 几何特征 | 风险 | 原因 |
|---|---|---|---|
| 当前（矩形齐平） | 各层铺满同一 footprint | **低（理论风险）** | "某区域该内部"几乎无歧义；漏配多半成悬空引用被门抓 |
| **B5 非方形（L/U 形）** | 相邻层 footprint 交集是非平凡多边形 | **明显上升（现实风险）** | 下层天花一部分**合法地是 Outdoors（屋面）**、一部分内部楼板；切错"长得就像合法 Outdoors 面"——门看不见 |
| **B6 退台/挑空** | 上层缩进 / 中庭跨层无楼板 | **首要风险** | "这里到底有没有楼板"全靠模型判断，判错=干净覆盖洞，门完全盲 |

结论：现在理论风险 → B5 转现实 → B6 是主要风险。**故根治时机 = B5 非方形开工时**，与 idfpy 切换同期最省力。

---

## 4. 长期架构：平面再拓扑 + 确定性几何内核

### 4.1 支点判断：EP 模型 = 一堆贴合的积木块

EP 仿真模型本质是**一堆贴合在一起的热区积木块，不含真正建筑空间信息**。这是整个简化的支点，也是 OpenStudio FloorspaceJS / ASHRAE 90.1 热分区（周边 5 区 + 核心区）的标准范式：**先把平面划分成 zone 底面，再升起来。**

### 4.2 两半架构

```
phase1 识图(忠实感知:笔画 + 尺寸链 + 置信度)
   ↓
phase2a 平面再拓扑 / 热分区  ←【新】判断层(LLM 适合)
   产出 = 每层 zone 底面多边形剖分 + 外包络 + 立面朝向 + 窗锚点
   不变量 = 每层 zone 底面构成该层 footprint 的一个【平面剖分】(恰好铺满、无缝无叠)
   ↓
phase2b 确定性几何内核  ←【新】机械层(代码,对标 OpenStudio intersect/match)
   底面升起棱柱 → 自动生成 6 面 → 相邻面相交 → 匹配 → break 点切分 → 互逆配对 → 设 OBC
   ↓
6 个非几何 subagent(schedule/material/construction/lights/people/hvac) ← 不变
   ↓
cross_ref / validate / simulate ← 不变(interzone 门退化成廉价 sanity check)
```

### 4.3 杀手锏：覆盖完整性从"事后查"升级为"构造不变量"

若强制 phase2a 产出是合法**平面剖分**（planar partition），则升起 + 配对**天生覆盖完整、天生无洞**。§2.2 那个覆盖洞**在这套范式里根本无法产生**——不需要 shapely 事后查洞（shapely 仍可用于校验剖分本身是否合法，但洞不再是运行期风险）。这是把覆盖风险**从源头消解**，而非加门去抓。

### 4.4 这把 phase2 自然劈两段

- **phase2a 热再拓扑**：高海拔**判断**（怎么把房间并成 zone，依朝向/HVAC/用途——有规范支撑），适合 LLM，出口**确定性可校验**（剖分铺满 footprint）。
- **phase2b 几何实现**：纯**机械**（升起+配对），确定性代码。其输入（一摞校验过的平面剖分）正是让它能确定、能水密的前提。

**判断与机械彻底分开**——这是整套设计的美感所在。

---

## 5. 2D 还是 3D？——2D 逐层剖分当规范层，竖向当例外

再拓扑**在 2D、逐层做（一摞平面剖分），作为规范中间表示；3D 是它的确定性后果（升起），竖向现象作为少数显式例外叠加。**

| 复杂度 | 2D-逐层剖分够不够 | 说明 |
|---|---|---|
| 当前（单 footprint + 垂直升起） | ✅ 完全够 | 每层一个 2D 剖分 → 升起 |
| **退台**（各层 footprint 不同） | ✅ 仍够 | 每层一个**不同的** 2D 剖分，天然支持 |
| **挑空/通高**（zone 跨层无楼板） | ⚠️ 需例外机制 | 2D-逐层剖分 + **竖向合并标注**（堆叠底面融成高棱柱），不退回纯 3D |
| 斜屋面 | ⚠️ 竖向例外 | 顶面 z 非平 → 升起时按例外 |

**为什么不直接在 3D/phase2 空间里做**：进 3D 推理就丢掉了 2D 平面剖分那个"恰好铺满、无洞"的不变量——而 §4.3 的水密保证和 §6 的评测埋点全挂在这个不变量上。2D 剖分是水密性的所在地，必须守住；3D 应是"升起"这个确定性操作 + 几处显式竖向例外。用户当前"先不考虑挑空"正好——把它隔离成例外，主干保持简单。

---

## 6. 三个必须看见的张力（不是反对，是别踩坑）

1. **热分区判断被"搬走"了，没被"消灭"。** "怎么把房间并成 zone"有主观性，仍需推理（可能仍 LLM）。但这是**好的搬迁**：从易错的低层顶点切分，搬到高层、有规范、更适合 LLM 的分区判断。不免费，只是放到了对的地方。
2. **别抽象过头——envelope 和窗锚点必须留。** "EP 不含建筑空间信息"对内部分区成立，但外包络多边形 + 立面朝向 + 窗在立面上的位置**必须忠实保留**（WWR 按立面算、窗属特定朝向外墙段）。再拓扑是"并内部、留外壳"。
3. **分区粒度是个有能耗后果的旋钮。** 并区粒度变了，负荷和分区结果就变。概念阶段可接受，但理想是**可让用户确认的旋钮**，不悄悄定死。

---

## 7. 与现有体系的关系

### 7.1 协作者契约——为什么几何内核是"另一个架构层"

当前责任切分（[../CLAUDE.md §2/§5.2](../CLAUDE.md)）：本项目侧拥有 intake，产物到 `IntakeOutput` Pydantic JSON（NL `*_specs`）；协作者侧拥有下游 9 subagent 的 prompt + MCP 工具层。**契约边界 = IntakeOutput JSON**。下游设计哲学 = **智能全在 LLM，工具是薄 CRUD 原语**，管线里刻意没有几何引擎。

确定性几何内核之所以是"另一个层"：① 它不是 CRUD 工具，是**生成算法**（吃 zone 体块、吐切好配好的面，接管 LLM 现在的活）；② 它**改契约**（phase2 不再吐枚举好的 split surface_specs，改吐结构化 zone 剖分）；③ 它**跨所有权边界**（surface 阶段的下游 subagent prompt 是协作者拥有的）。所以不是调 prompt，是往"LLM 推理+薄 CRUD"管线里插确定性生成阶段。

### 7.2 idfpy 的影响——使能器，不自动解

idfpy（[../deferred/idfpy_embed.md](../deferred/idfpy_embed.md)）是**数据模型+schema+IO+几何 mixin**库，**不是几何求解器**（没有 OpenStudio 的 intersect/match）。三块影响：

| | 影响 |
|---|---|
| **强化验证侧** | `idf.validate()` 原生跨引用校验，**接管** interzone 门的引用完整性那几项（目标存在/是 Surface/互逆/单一引用），这部分可删（与 [../CLAUDE.md §5.4.D](../CLAUDE.md) "validator 待 idfpy 切换整体删"一致）。但 `validate()` 是 schema 校验**不验几何**（共面/法向/覆盖它不碰） |
| **不自动解切分/覆盖** | ⚠️ 关键区别：覆盖洞是**几何缺陷不是 schema 违规**，`validate()` 会愉快放行有洞的模型。**别指望切 idfpy 像消掉 glazing bug 那样消掉它**（glazing 是 schema 约束所以能被原生拒，覆盖洞不是） |
| **是几何内核的使能器** | `area/normal/centroid` mixin + `surface.zone` forward nav，让"自写确定性切分/匹配内核"从在 eppy 上硬刚降成在 idfpy 上拼装（[idfpy_embed.md §3.1](../deferred/idfpy_embed.md) 明说"自动 boundary 推断实现量级降低"）。**降本~10×** |

shapely 与 idfpy **互补**：idfpy 出干净 surface 多边形，shapely 做 footprint 集合代数（并/交/差）。idfpy 替代不了 shapely。

### 7.3 改动范围——不大改，定点改

| 环节 | geometry-first 下 | 改动量 |
|---|---|---|
| phase1 识图 | 不动 | 无 |
| phase2 | 输出格式改：不再枚举 split 进 NL，改吐结构化 zone 剖分 + 层高（phase2 [rules.md §2.4](../../skills/energyplus_mcp_twostep/phase2/rules.md) **本就在算"zone=最小闭合多边形"**，只是现在拍扁成 NL，改出口不改推理） | 中 |
| IntakeOutput 契约 | 加结构化几何字段（跨边界，需协作者协调） | 中 |
| zone 节点 | 基本不动（EP Zone 本就只是 name+origin） | 小 |
| **surface 节点** | **LLM ReAct → 确定性几何内核**（核心改动，代码量不大） | 中 |
| fenestration | 窗贴到生成好的墙上；可续 LLM（局部任务）或一并确定化 | 小～可选 |
| construction/material/schedule/lights/people/hvac | 不动 | 无 |
| cross_ref/validate/simulate | 不动；interzone 门退化成 sanity check | 无～减 |

**主成本不在代码，在两件事**：① 契约改动**跨协作者所有权边界**（IntakeOutput 加字段 + surface 节点从 LLM 换代码）；② 内核本身（建在 shapely+idfpy 上代码量不大）。**且能并行灰度切**：把内核做成可选 surface 节点（flag），与现有 LLM 并存，同 case 双路径对照（沿用 sm_20/sm21 双路径纪律），证明不劣后再退役 LLM 节点。**不必 big-bang。**

### 7.4 评测埋点（接 B2-B4）

2D zone 剖分是**最理想的 GT/评测目标**：给 2D 分区标 ground-truth、做 diff，比给 NL specs 或 3D 顶点标注容易一个量级。这个埋点能撑起整个评测体系（[../plan.md B2-B4](../plan.md)），且让"识图错 ↔ 推理错"归因更干净（phase2a 剖分错 vs phase2b 升起错可分离）。

---

## 8. 一图总结：当前 vs 目标

| | 切分/配对决策 | 引用完整性校验 | 几何正确性校验 | 覆盖完整性 |
|---|---|---|---|---|
| **现在** | LLM(phase2+surface_agent) | interzone 门 | interzone 门 | ❌ 缺 |
| **切 idfpy 后(仍 LLM 切)** | 仍是 LLM | `idf.validate()` 原生 | 仍需自写(idfpy 给 mixin 降本) | 仍需 shapely 事后查 |
| **目标(再拓扑+几何内核,建在 idfpy 上)** | **降为确定性代码** | validate + 内核不变量 | 内核不变量 | **构造不变量(几乎免费)** |

---

## 9. 落地时机 + 待决策点

**时机**：与 **idfpy 切换 + B5 非方形** 同期做最省力，三件事一锅端：① 验证原生化（idfpy validate）② 几何内核（再拓扑+升起+配对）③ 非方形支持（不同剖分）。当前矩形机制下不急，覆盖洞是理论风险。

**待决策点**（动手前拍板）：
1. **再拓扑放 phase2a 独立步 vs 并进 phase2 重写**——本文倾向独立 phase2a（判断/机械分离更干净）。
2. **再拓扑是 LLM 判断 + 确定性校验 vs 规则化（ASHRAE 90.1 周边/核心自动分区）**——倾向 LLM 判断起步、规则做兜底/校验。
3. **IntakeOutput 几何字段 schema**——需与协作者就契约边界协调（这是主成本）。
4. **挑空/斜面的竖向例外机制具体形态**——本轮先不锁，先把 2D 逐层主干 + 例外注解的框架定下。
5. **几何内核自写 vs 借 OpenStudio SDK intersect/match**——idfpy 路线下倾向自写（轻、可控）；待评估 OpenStudio SDK 引入成本。

---

_2026-05-29 建档 — 单次会话收敛。源起 = InterZone 覆盖完整性 deferred 讨论（用户问"在哪解决/会不会 phase2 复杂度过高"）→ 收敛出 geometry-first 确定性内核 + 平面再拓扑（热分区）两半架构。状态：设计讨论已捕获，未落地。落地时机 = idfpy + B5 同期。_
