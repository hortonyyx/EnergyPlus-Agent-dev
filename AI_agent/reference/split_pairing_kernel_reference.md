# 切配（split-pairing）确定性内核 — 技术参考

> **性质**：技术参考 / 背景知识，**不是本项目的待办或 spec**。切配下游另有人在做、不归本项目管（2026-06-07 用户定）。本文档供理解切配是什么、确定性实现有哪些路子、与本项目其它环节怎么衔接——作交接/对齐参考，不作决策。

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
4. **所有权边界**：当前几何实现在 [surface.py](../../src/agent/nodes/surface.py)（协作者方）。把切配下沉为确定性内核会动这段代码 + 改契约（phase2 不再吐 split 枚举），跨所有权边界——下游做切配那方需与协作者协调。

---

## 5. 相关文件

- [src/validator/interzone.py](../../src/validator/interzone.py) — 现 per-pair 确定性门（切配内核的事后校验可由它退化成 sanity check）
- [src/agent/nodes/surface.py](../../src/agent/nodes/surface.py) — 现 LLM 几何实现（切配内核要取代的）
- [src/converters/surface_converter.py](../../src/converters/surface_converter.py) — 纯写入
- [skills/energyplus_mcp_twostep/phase2/rules.md](../../skills/energyplus_mcp_twostep/phase2/rules.md) §2.6 / Step 4 — 现切分决策文本规则
- [AI_agent/deferred/idfpy_embed.md](../deferred/idfpy_embed.md) — idfpy 切换计划（切配内核的使能器）
- [AI_agent/architecture/geometry_first_zonification.md](../architecture/geometry_first_zonification.md) §7.2 — idfpy/shapely 分工分析

---

_2026-06-07 建档 — 主开发 Agent。源 = 几何管线术语锁定后，把切配从"再拓扑"里摘出作独立 leg-agnostic 确定性轨。切配实现归下游，本文档仅技术参考。_
