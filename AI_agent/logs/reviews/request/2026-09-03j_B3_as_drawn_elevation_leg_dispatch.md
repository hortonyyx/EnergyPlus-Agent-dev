# 派工单 · **B3：as-drawn 立面腿**（把立面证据接进统一 bundle）

- **日期**：2026-09-03 · **派工方**：orchestrator · **施工方**：**GLM 家族** · **审**：⏳ 与施工方不同家族（⛔ 不得 GLM）
- **权威口径** = [设计稿 v7 §7.2 B3 行](../../proposals/correction_projection_bridge.md)（四轮跨家族审）
- **为什么是现在**：B3 **无前置**，而它同时是 **B2（多层装配）** 与 **B4（洞口合成）** 的关键路径。

## 一、⭐ 它挡着两件事（⛔ 都是实测，不是推测）

| 缺的东西 | 今天从哪来 | 新链里有没有 |
|---|---|---|
| **窗的竖向尺寸** `WindowV3.z`（窗台/窗顶）| 模型在**旧贴 JSON 路**里填 | ⛔ **零来源**（平面产物无 z；legacy 适配器写死 `opening_claims=[]`）|
| **楼层标高 / 层高** `FloorV3.z_floor` + `ceiling_height` | 同上（[`pipeline.py:419`](../../../src/agent/pipeline.py#L419) 提示词原文「Each floor gives z_floor + ceiling_height」）| ⛔ **零来源**（墙编译器完全没有 z）|

⭐ **而立面产物里两样都有**（主控实测 `sm25_east_as_drawn.json`）：
- `openings[].z_range_m` —— 例：`[0.181, 2.3111]`
- `structure_lines` 的水平线直接给楼层标高 —— **S06 `pos_m ≈ 0.000`（地面）· S05 `3.600`（二层）· S04 `7.202`（屋顶）**，
  且 z 标定链 `cum_mm = [0, 1000, 2600, 3600, 4600, 6200, 7200]` **逐位闭合**
- `calibration.world_zero_source == "chain_fit"`（⭐ 原点已是**派生**的，不再是手填），带交叉核对 `delta_mm` 0.9–4.5

## 二、⭐ 起点比想象的近（主控实测，⛔ 不是从零设计）

```
src/agent/reading/vector_contract.py:276   CONTRACT_AS_DRAWN_ELEVATION_V0
                                            Disposition.KNOWN_NOT_CONSUMED   ← 只差这一步
src/agent/correction/evidence_contract.py:441-443
   ChannelName = Literal["walls", "plan_openings", "elevation_openings", ...]  ← 通道名【已经在类型里】
grep -c "adapt_as_drawn_elevation" evidence_adapters.py = 0                    ← 适配器不存在
```
⇒ **它今天的位置 = 平面产物在模块 3 之前的位置**：**改处置 + 写适配器**，⛔ 不是从零设计契约。
⭐ 且**真实语料已备齐**：sm25 四个立面的新格式产物都在
（`AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out/sm25_{east,west,north,south}_as_drawn.json`）。

## 三、任务项

| # | 做什么 |
|---|---|
| **T1** | `Disposition` 从 `KNOWN_NOT_CONSUMED` 改为 **`ADAPT`**（⭐ 镜像平面那条路已有的做法）|
| **T2** | 写 `adapt_as_drawn_elevation`：把立面产物翻成 bundle 的 **`elevation_openings` 通道** + `channel_status` |
| **T3** | ⭐ **把 `openings[].z_range_m` 变成【带引用的证据】** —— 每个 z 必须能指回它在冻结字节里的出处（`source_ref`），⛔ 不许裸值 |
| **T4** | ⭐⭐ **楼层标高同样成为带引用的证据**：从 `structure_lines` 里**哪几条算楼层线**要有**可判定的规则**，⛔ 不许「挑看起来像的那几条」|
| **T5** | 四个立面产物**全部能进 bundle**，且 bundle 的 `content_sha256` **逐位可复现** |

## 四、⛔ 明确不做

⛔ **洞口合成**（平面洞口 ↔ 立面窗的**身份配对** = **B4**，⭐ 已另有实测方案，见
[实验档](../../logs/experiments/2026-09-02b_b4_cross_view_identity/README.md)）·
⛔ **多层装配**（B2）· ⛔ 动投影桥 / `pipeline.py` 的接线（B1 正在跨家族审，⛔ 别碰同一片）·
⛔ 动 legacy 那条腿（拆旧腿另有单）· ⛔ `pip install -e .` · ⛔ `git add -A`。
⭐ **必须分段提交**（⛔ 不许攒到最后；本项目已因此丢过 1035 / 1273 / 119 行）。

## 五、⛔ 三条纪律（用户 2026-09-02 令，见[指南 §十三](../../guides/reading_correction_split_guide.md)）

1. ⛔ **代码里不得出现长度/高度常数** —— 需要尺寸只能**从被处理的数据里取**。
   ⚠️ **本单最容易犯的一处**：⛔ **不许把「层高 3.6 m」「两层」这类 sm25 的读数写进任何判定**。
2. ⛔ **夹具不许只用 sm25 的立面** —— 至少造一份**层高不同、层数不同**的合成立面
   （⭐ 例如三层、层高 2.9 / 3.3 / 4.2 混排）。
3. **⛔ 不要求**为「局部立面 / 分段立面」写泛化分支（该能力未解锁）——
   但**那个假设要局部化 + 有名字**，且**不成立时响亮**（⛔ 不许静默按「横跨整栋」处理）。
   ⭐ 依据：主控 B4 探针已实测「立面尺寸链总长 == 外皮沿轴跨度」在 sm25 四张图上成立，
   **但那是这批图纸的画法性质，⛔ 不是定理**。

## 六、验收（规则形态）

| # | 规则 | 怎么证 |
|---|---|---|
| **1** | 四份真实立面产物**全部被分类为 `as_drawn_elevation_v0` 并走 adapter** | ⛔ 用分类器的判定，不是文件名 |
| **2** | **每个 z 与每个楼层标高都能指回冻结字节里的出处** | 随机抽 3 个，逐个把 `source_ref` 解引用回原值 |
| **3** | **楼层线的挑选是规则，不是名单** | 换一份**层数不同**的合成立面 ⇒ 规则仍挑对；⛔ 不许出现 sm25 的具体标高 |
| **4** | bundle **逐位可复现**（同字节 ⇒ 同 `content_sha256`）| 跑两次比哈希 |
| **5** | ⭐ **坏输入响亮失败**：z 缺失 / 标定链不闭合 / 尺寸链总长与外皮跨度对不上 ⇒ **具名错误**，⛔ 不静默 | 各造一个 |
| **6** | 全量绿（**`-n 6`**）| 环境自证与 pytest 同一条命令 |

## 七、停下上报（分层）

**A 层（停）**：① 要做任务项必须动 §四 禁令 ② 发现会改**任何已落库/已签字产物的哈希或基线**
③ 实测发现 §一/§二 的某条**根本不成立**（⭐ 请务必自己复现，⛔ 别因为是我量的就信）。
**B 层（记一条继续）**：行号/读数对不上 · 命名 · 顺手发现的新缺陷。

## 八、交件

`AI_agent/logs/reviews/execution/2026-09-03j_B3_as_drawn_elevation_execution.md`：
命令原文 + 输出原文，逐条对 §六 六条报，写**你自己认为最薄弱的一处**与希望复核方重点打哪里。
