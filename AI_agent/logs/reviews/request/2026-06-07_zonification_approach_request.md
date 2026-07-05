# 调研请求：plane-first zonification 怎么做（算法 vs LLM vs 范式）

- **日期**：2026-06-07
- **发起**：主开发 Agent（Claude Opus）+ 用户
- **类型**：技术调研委托（非代码审阅；只调研，不实现、不改代码/契约）
- **希望承接模型**：research Agent（另一模型）——欢迎 BEM 自动热分区 / OpenStudio / CV floorplan 的外部第一性原理视角

---

## 0. 术语约定（2026-06-07 与用户锁定，全文按此口径）

- **再拓扑** = 在 phase1 画出的平面基础上**进行新的 zone 区划分**（重划热区）。是 zonification 的一种方式，**不含切配**。
- **两条线** = 都只是 **zonification（怎么定 zone）方式与粒度的选择**：
  - **忠实建模**：完全修好图纸、按房间为 zone 建完整几何模型（房间=zone，需把图纸校正到高精度）。
  - **热区再拓扑**：直接在平面上先分好 zone（少而大的热区，按真仿真热区规范）再建模（**不需要把图纸校正到很高精度**）。
- **切配** = 把几何建模（面**不**一一对应）切成 EP 要求的一一对应关系。**已定为确定性几何算法、独立、与两条线无关**——**本请求不调研切配**（下游另有人做，技术参考另出，见 [reference/split_pairing_kernel_reference.md](../../../reference/split_pairing_kernel_reference.md)）。

管线：phase1 识图 → 校正 → **zonification（两条线在此且仅在此分叉）** → 几何建模(升起) → 切配(确定算法) → EP。

---

## 1. 本请求的唯一问题

**给定一张平面图（假设已校正到够用程度），若选择"直接在平面上先划分 zone"（即热区再拓扑），这一步该交给大模型、还是用相关平面算法、还是怎么做？**

典型场景：一个复杂的 20 房间平面，按热区划分可能 4-5 个 zone 就够。怎么从 20 个房间得到这 4-5 个热区？

---

## 2. 委托方的初步判断（请验证或推翻，别预设它对）

> **"算法 vs LLM" 不是对的那一刀；"几何剖分 vs 语义归并"才是，权重取决于瞄准的范式（= 分区粒度旋钮）。**
>
> zonification 二分：
> - **几何骨架**（周边环按进深内偏 + 朝向 N/S/E/W 切 + 核心区）= **算法主导**。shapely 多边形偏移/切割；OpenStudio 自带 perimeter-core measure，BEM 几十年成熟实践。让 LLM 做 = 重造我们正想逃离的几何心算。
> - **语义归并 + 例外**（哪些房并成一个 zone，按 use/schedule/load/system；哪个设备间单列；开敞区怎么处理）= **LLM/规则**（喂房间元数据）。
>
> 范式决定权重：
> - **范式 A 周边+核心自动分区**（90.1 Appendix G 式）：边界不沿真实墙，吃 footprint+进深+朝向 → ~5 区。算法绝对主导，最鲁棒、最"真仿真"、最不需校正精度，但真实房间全丢。
> - **范式 B 按用途归并真实房间**（沿现有墙合并同朝向同用途相邻房）→ ~8-10 区。LLM 主导归并 + 算法执行 union，保留部分真实几何、更接近忠实、仍需校正。
>
> **结论假设**：热区几何骨架让算法领跑，LLM 只供语义标签 + 偏离标准的例外。调研第一步 = 先定瞄准范式（纯周边核心 / 用途归并 / 可调粒度谱系），算法/LLM 权重随之落出。

---

## 3. 调研要回答的子问题

1. **范式选择**：范式 A（周边核心自动分区）/ 范式 B（用途归并）/ 可调粒度谱系——哪个更适合本项目（杂乱真实图 → 仿真就绪 BEM）？给推荐 + 理由。
2. **几何剖分算法**：周边环内偏 + 朝向切 + 核心区，shapely 自写 vs OpenStudio perimeter-core measure。能力 / 依赖 / 成本对比。
3. **语义归并**：LLM 判断 vs 规则（over use/schedule/load 元数据）vs 混合；归并的输入需要 phase1 提供哪些语义标签。
4. **剖分合法性校验**：怎么确定性校验输出是合法平面剖分（铺满 footprint / 无重叠 / 无空洞）。
5. **粒度旋钮**：分区粒度是有能耗后果的旋钮，能否做成用户可确认的参数？范式 A/B 是否就是旋钮两端？
6. **校正精度耦合**：每种范式各需 phase1 校正到什么精度？（热区再拓扑省校正是其卖点之一，需量化"省多少"。）
7. **中间表示 schema**：zonification 输出（per-floor zone 底面剖分 + 外包络 + 立面朝向 + 窗锚点）用什么数据结构表达，能干净喂给后续几何建模与切配，且是好的 GT/评测目标。
8. **现成方案**：BIM-to-BEM / 自动热分区 / OpenStudio / CV floorplan 重建里有没有现成的、该直接借而非自造的（另见 [reference/drawing_to_model_research_landscape.md](../../../reference/drawing_to_model_research_landscape.md)）。

---

## 4. 明确不在范围内

- **切配**（面切成 EP 一一对应）：确定性算法、独立、下游有人做、不归本项目管。技术参考另出（[reference/split_pairing_kernel_reference.md](../../../reference/split_pairing_kernel_reference.md)），本请求不碰。
- **忠实建模 leg**（房间=zone）：那条线 zonification 近乎 identity，不是本请求重点；本请求聚焦"热区再拓扑"这条线怎么实现。
- 不动代码、不改 phase2/rules.md、不改 IntakeOutput 契约。

---

## 5. 相关文件

- [AI_agent/architecture/geometry_first_zonification.md](../../../architecture/geometry_first_zonification.md)（再拓扑架构骨架；注意其早期"再拓扑"含切配，按本请求 §0 术语重新对齐）
- [AI_agent/capability/recognition_modeling_capability.md](../../../capability/recognition_modeling_capability.md)（忠实建模 leg + sm21 诊断 + 两腿并行）
- [skills/energyplus_mcp_twostep/phase2/rules.md](../../../../skills/energyplus_mcp_twostep/phase2/rules.md) §2.3 / Step 3（当前 zone 拓扑 + zone_specs 的 LLM 文本做法）
- [AI_agent/reference/drawing_to_model_research_landscape.md](../../../reference/drawing_to_model_research_landscape.md)（研究现状三流派）

---

## 6. 验收标准（调研结论文档应给出）

- **范式裁决** + 推荐 zonification 实现路线（算法/LLM 各承担什么、缝在哪）。
- 逐条回应 §3 八个子问题 + 对 §2 初步判断逐条采纳/推翻。
- 中间表示 schema 草案。
- 校正精度耦合的量化（热区再拓扑到底省多少校正）。
- 现成方案清单（该借的 vs 该自造的）。
- 输出落 [AI_agent/logs/review/review/2026-06-07_zonification_approach_review.md](../review/)（命名对齐本 request）。

---

_本 request 与对应 review 均 git 跟踪，作审计轨迹（[CLAUDE.md §6 #14](../../../CLAUDE.md)）。术语口径见 §0。_
