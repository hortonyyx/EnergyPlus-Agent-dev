# 审阅请求：几何优先再拓扑 + 两腿并行建模架构

- **日期**：2026-05-29
- **发起**：主开发 Agent（Claude Opus）
- **类型**：架构方向讨论（非代码实现审阅；本轮无代码改动，只有设计文档落档）
- **希望审阅模型**：另一模型（Codex / Gemini）——尤其欢迎与本项目熟悉的下游栈无关的"外部第一性原理"视角

---

## 1. 背景与本轮讨论脉络

本轮从一个 deferred 项（InterZone 覆盖完整性校验）出发，逐步收敛出一条长期建模架构方向。讨论链：

1. **覆盖洞缺口**：现 [src/validator/interzone.py](../../../../src/validator/interzone.py) 的 per-pair 门（8 项确定性校验）抓不到一类缺陷——"本该是内部边界（楼板/相邻 zone 墙），两侧却都被标 Outdoors/Adiabatic → 该区域根本不进配对图 → 门盲、EP 运行也不报错"。检测需多边形并/交/差（shapely）。已决策走 shapely、当前仅标记，落地时机绑 B5。
2. **切分/配对现状**：split-pairing 当前是 **phase2（DeepSeek，文本枚举子区间+配对）→ surface_agent（LLM，顶点+互逆引用实现）→ surface_converter（纯写入）→ interzone 门（事后裁判）**。切分**没有任何确定性几何算法**，全靠两个 LLM 环节的 prompt 合规。
3. **结构性问题**：两个本可分离的关注点被揉进 phase2 文本——(a) zone 在哪（需识图/推理）vs (b) 面怎么切/怎么配（纯几何、可确定性）。
4. **收敛出的长期架构**：把切分/配对下沉为「**平面再拓扑（热区积木，2D 逐层剖分=判断层）+ 确定性几何内核（升起+相交+匹配+切分+配对=机械层）**」。覆盖完整性从"事后查"升为"构造不变量"。
5. **idfpy 关系**：idfpy 是使能器（几何 mixin 降本、validate() 接管引用完整性）但**不自动解**切分/覆盖（覆盖洞是几何缺陷非 schema 违规，validate() 会放行——区别于 glazing bug 那种 schema 约束）。shapely 与 idfpy 互补。
6. **两腿并行决策（用户定调）**：
   - **忠实建模 leg**（[capability/recognition_modeling_capability.md](../../../capability/recognition_modeling_capability.md)）：phase2 容差重生成**保留真实建筑几何**，有 beyond-EP 产品价值（图纸→建筑模型小 Agent），继续落地。
   - **再拓扑 leg**（[architecture/geometry_first_zonification.md](../../../architecture/geometry_first_zonification.md)）：抽象成热区积木、丢真实几何，EP 鲁棒最优但最激进，作强力支线、稳定再切。

---

## 2. 审阅范围

**只审架构推理，不审代码实现**（本轮无代码改动）。核心审阅对象 = 两份新/改文档的论证是否成立、有无逻辑漏洞、有无遗漏的风险或现有技术。

主文档：
- [AI_agent/architecture/geometry_first_zonification.md](../../../architecture/geometry_first_zonification.md)（新建，再拓扑 leg 架构骨架，9 节）
- [AI_agent/capability/recognition_modeling_capability.md](../../../capability/recognition_modeling_capability.md) §8（新增，两腿并行 + A/B 处置差异表）

证据/上下文文件（理解现状用）：
- [src/validator/interzone.py](../../../../src/validator/interzone.py)（现 per-pair 门）
- [src/agent/nodes/surface.py](../../../../src/agent/nodes/surface.py)（surface LLM 节点）
- [src/converters/surface_converter.py](../../../../src/converters/surface_converter.py)（纯写入）
- [skills/energyplus_mcp_twostep/phase2/rules.md](../../../../skills/energyplus_mcp_twostep/phase2/rules.md) §2.6（当前 split-pairing 文本规则）
- [AI_agent/deferred/idfpy_embed.md](../../../deferred/idfpy_embed.md)（idfpy 切换计划）
- [AI_agent/logs/downstream_agent_changes.md](../../../downstream_agent_changes.md) 2026-05-29 条（覆盖洞 deferred + 风险评估）

---

## 3. 关注点（请重点挑战这些判断）

1. **A/B 关注点分解是否成立？** "几何装配/水密性(A) vs 噪声感知仲裁(B)"这个二分是否干净？有没有第三类被漏掉？
2. **"再拓扑使覆盖完整性成为构造不变量"是否正确？** 合法平面剖分天生无洞——这个数学断言在退台/挑空/斜面下还成立吗？2D-逐层+竖向例外的框架够不够？
3. **"崩溃安全网撤除"洞见是否正确且重要？** 论点：再拓扑保证任何剖分都水密必通 → 错而不崩 → B 类成唯一守门人。这是高估还是真风险？现在 EP 段错真的是"有用信号"还是噪声？
4. **2D-逐层为规范层 vs 直接 3D**：选 2D 的理由（守住"铺满无洞"不变量）站得住吗？挑空/斜面作"例外注解"会不会反而更复杂？
5. **idfpy 评估准不准**：① validate() 是 schema 校验不验几何/覆盖；② 覆盖洞是几何缺陷非 schema 违规所以 validate() 放行（区别于 glazing bug）；③ idfpy 给 mixin 但替代不了 shapely 布尔运算。这三条有无错误？
6. **两腿并行 vs 收敛单腿**：用户定"两腿并行不二选一"。这是合理的对冲，还是摊薄资源应该选一条？忠实 leg 的"beyond-EP 产品价值（图纸→建筑模型 Agent）"是否现实？
7. **契约/所有权成本评估**：把 surface 节点从 LLM 换成确定性代码、IntakeOutput 加结构化几何字段——"主成本在跨协作者契约协调而非代码量"判断对不对？并行 flag 灰度切是否可行？
8. **落地时机**：绑"idfpy + B5 非方形同期"是否合理？有没有更早该做的理由（如覆盖洞其实已经在悄悄出错）？
9. **遗漏的现有技术/做法**：业界 BIM-to-BEM / 自动热分区 / OpenStudio intersect-match / CV floorplan 重建 是否有现成方案我们该直接借而不是自造？（另见同日产出的研究现状文档 [reference/drawing_to_model_research_landscape.md](../../../reference/drawing_to_model_research_landscape.md)）

---

## 4. 验收标准（review 文档应给出）

- **Verdict**：架构方向是否 sound？两腿并行是否明智？
- **分级 findings（High/Medium/Low）**：每条含证据 + 建议。尤其针对 §3 的 9 个关注点逐一表态（同意/反对/补充）。
- **遗漏风险**：我们没看见的失败模式或被现有技术已解决的轮子。
- **落地时机与优先级建议**：是否同意"绑 idfpy+B5"，还是有更紧迫的动作。
- 输出落 [AI_agent/logs/review/review/2026-05-29_geometry_first_zonification_review.md](../review/)（命名对齐本 request）。

---

_本 request 与对应 review 均 git 跟踪，作审计轨迹（[CLAUDE.md §6 #14](../../../CLAUDE.md)）。本轮无代码改动，纯架构设计落档 + 跨模型讨论。_
