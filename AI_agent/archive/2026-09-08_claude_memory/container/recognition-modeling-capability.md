---
name: recognition-modeling-capability
description: 识图→建模质量长期主线;活文档 AI_agent/capability/recognition_modeling_capability.md;核心决定=容差内重生成放 phase2、phase1 保持忠实感知
metadata: 
  node_type: memory
  type: project
  originSessionId: 21a5ed28-784f-426b-92bf-947d7abd5603
---

识图→建模质量是项目长期主线工作的主要对象,有专门活文档管理:[AI_agent/capability/recognition_modeling_capability.md](AI_agent/capability/recognition_modeling_capability.md)（2026-05-28 建,首轮=sm21 三模型 phase2 诊断 + 容差重生成设计讨论,**讨论已捕获未落地**）。

**核心设计决定（非显然、load-bearing）**：
- **定性 > 定量**：EP 仿真只在意 zone 闭合 / 窗不跨 zone / 面积WWR 在 ±5% 内,不在意 mm 级坐标。死扣数值是病根（真实图纸天然有标注缺失/轴线vs外墙定位冲突/墙厚扰动等"合不上"来源）。
- **容差内重生成**：phase2 从"转写器"升格为"约束求解+重生成器"——拿 phase1 感知（笔画+尺寸链+置信度）在容差内重建 EP 合法拓扑,不逐字照搬坐标。即"结合尺寸链和图形再生成一次"。
- **重生成属于 phase2,phase1 保持忠实感知**（守误差预算分离）。phase1 配套小改=把笔画/尺寸链作两独立通道+置信度交出,不预先仲裁、不吐"估算坐标冒充测量值"。
- **`corrections[]` 审计日志=硬要求**:phase2 每次修正留痕,否则放宽约束=放弃可解释性/可评测性。
- **常识先验红线**:建筑常识库（典型窗台/门宽/最小开间等,phase2 侧,拟单独建文档）严格作裁决/兜底,**不覆盖一致测量数据**。优先级=一致测量>尺寸链推导>常识先验。

**Why（sm21 证据）**:固定 phase1、phase2 换 Opus/Sonnet/DeepSeek 三模型对比发现——(1) **EP 跑通≠几何对**(DeepSeek 几何最差含 1.2m 幽灵房却 EP 最干净;Sonnet 几何最忠实却段错);(2) phase1 自身矛盾(笔画 4.95/10.05 vs 尺寸链 3.75/11.25)时忠实转写会带错下去;(3) Opus 唯一"读尺寸链重新理解"做对了→要升格为强制范式。Sonnet EP 段错真因=phase1 跨图 5cm 抖动(1f 估 4.90/2f 估 4.95)→下游跨层楼板切出 5cm×3m 退化碎片→EP SIGSEGV。

**两条腿并行（2026-05-29 用户定调，不二选一）**——从感知到几何的 phase2 段有两条路：
- **忠实建模 leg = 本活文档**：phase2 容差重生成**保留真实建筑几何**（真墙真房间），A 类（水密：闭缝/吸附/生成规则）+ B 类（仲裁/常识/审计）都在 phase2 解。**有 beyond-EP 产品价值**（约束出高质量=一个"图纸→建筑几何模型"小 Agent，本身有价值，不止喂 EP）。**继续落地、不被再拓扑取代**。
- **再拓扑 leg = [AI_agent/architecture/geometry_first_zonification.md](AI_agent/architecture/geometry_first_zonification.md)**：把 surface 切分/配对下沉为「**平面再拓扑（热区积木，2D 逐层剖分=判断层）+ 确定性几何内核（升起+相交+匹配+切分+配对=机械层）**」，**丢弃真实建筑空间信息**。要点：① 覆盖完整性从"事后 shapely 查"升为**构造不变量**（合法平面剖分天生无洞）；② **idfpy 是使能器非自动解**（validate() 接管引用完整性、几何 mixin 降本~10×，但覆盖洞是几何缺陷非 schema 违规、validate() 会放行，别像 glazing bug 那样指望切 idfpy 自动消）；③ shapely 与 idfpy 互补；④ 主成本=跨协作者契约边界（IntakeOutput 加几何字段 + surface 节点 LLM→代码）非代码量，可并行 flag 灰度切；⑤ **崩溃安全网被撤除**（任何剖分都水密必通→错而不崩，B 类成唯一守门人）。EP 鲁棒性最优但相对原始信息变化最大、最激进 → **作强力支线**实验，稳定再切。
- 节奏：再拓扑确实最好但变化大，先支线；忠实 leg 独立继续。两 leg 共用 phase1 双通道感知 + 误差预算分离 + 下游 + InterZone 门，差异只在 phase2 段。

**How to apply**:讨论识图/建模质量、phase2 规则迭代、误差容忍时读该活文档（§8=两腿分工）。**忠实 leg 落地下一步**=先拍板 §6 的 4 个待定取舍（动手前置），再改 phase2/rules.md + 建常识库。改 skill 仍按 [[CLAUDE.md]] §6#5 备份 Skill_history/。关联 [[twostep-poc-v2-status]]、plan.md B1.5.b/B5-B7。
