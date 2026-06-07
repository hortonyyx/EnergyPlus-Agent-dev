# 识图 → 建模 能力提升（长期主线活文档）

> **定位**：识图→建模质量是项目长期主线工作的主要对象。本文档管理这条线的**问题框架 / 诊断证据 / 设计哲学 / 改进方向 / 待定取舍**，是一份持续迭代的活文档。
>
> 与其他文档的关系：[plan.md](../plan.md) B 段（B1.5.b / B5-B7）是任务清单；[floorplan_redraw_strategy.md](floorplan_redraw_strategy.md) 是两步法架构策略与 POC 史；[../architecture/geometry_first_zonification.md](../architecture/geometry_first_zonification.md) 是**并行的另一条腿**（再拓扑：抽象成热区积木、丢弃真实几何，EP 鲁棒性最优但变化最大）。**本文档 = 忠实建模 leg**（保留真实建筑几何的容差重生成），是**质量提升的设计与决策载体**，且有 beyond-EP 的独立产品价值（图纸→建筑模型小 Agent）。两腿并行决策见 §8。skill 的具体落地仍在 [`skills/energyplus_mcp_twostep/`](../../skills/energyplus_mcp_twostep)。
>
> _建档 2026-05-28。首轮内容 = sm21 三模型 phase2 诊断 + 容差重生成设计讨论（讨论已捕获，未落地实现）。_
>
> **⚠️ 术语对齐（2026-06-07，与用户锁定）**：**两条线（忠实建模 / 热区再拓扑）只在 zonification 的方式与粒度上分叉**——忠实 = 房间=zone（需把图纸校正到高精度）；热区再拓扑 = 平面上先划少而大的热区再建模（省校正精度）。**校正（partA）/ 几何建模 / 切配 三段两线共用**。**切配**（面切成 EP 一一对应）= **独立、确定性、与两条线无关**（下游另有人做，技术参考 [../reference/split_pairing_kernel_reference.md](../reference/split_pairing_kernel_reference.md)）。因此本文 §8 早期把"A 类水密装配"当作两腿差异点的框架**已被 §8 表下的更正注修正**：水密=切配，对两腿是同一个确定性算法，不是差异点。zonification 实现的开放调研 = [../logs/review/request/2026-06-07_zonification_approach_request.md](../logs/review/request/2026-06-07_zonification_approach_request.md)。

---

## 1. 核心框架：定性 > 定量

EnergyPlus 仿真真正在意的是**定性约束**，而非毫米级坐标：

- zone 闭合（manifold / 无缝）
- 相邻 zone 贴合、InterZone 面成对
- 窗 ∈ 父面、窗不跨 zone
- 面积 / 体积 / WWR 在误差范围内（量级 ±5%）

**死扣数值是病根**。真实图纸天然带这些"合不上"的来源：

1. **标注本身缺失或有误**（尤其复杂平面，中间常缺尺寸段）。
2. **定位方式 vs 墙厚冲突**：尺寸标注常按轴线/墙中心起，但总尺寸和立面又按外墙外边画 → 子链之和对不上总尺寸。
3. **等分房间被墙厚扰动**：名义等分的开间，因外墙/内墙厚度不一致，实测开间会有细微差异。

这些误差对仿真**不重要**。所以方向是：**给误差范围，让模型在容差内自己判断、修正、再生成；强约束定性优先于定量。**

---

## 2. 诊断证据：sm21 案例研究（2026-05-28）

实验设置：固定 phase1（一份矢量 JSON），phase2 用三个模型各跑一遍（DeepSeek 脚本 / Opus 子代理 / Sonnet 子代理，均图像盲、零会话上下文），下游统一 DeepSeek 9 subagent。

### 2.1 phase1 自身内部矛盾（根因，非感知缺失）

2f 南向隔墙：
- 墙体笔画 `S8/S9/S10` = x **4.95 / 7.50 / 10.05** → 房宽 4.95/2.55/2.55/4.95（"两大中间小"，错）
- 同一份 phase1 抄的尺寸链 `D19–D30` 编码隔墙中线 = **3.75 / 7.50 / 11.25** → **四等分 3.75m**（对）
- phase1 self_check 自认笔画是 "estimated from dim chains"。

→ phase1 **把估算的笔画坐标当测量值吐出**，与它自己抄对的尺寸链打架。

走廊墙左侧 0.24m 缝：2f 走廊隔墙 `S5/S6` 起点 = `[0.24, 5.00]` / `[0.24, 3.00]`，**不是 x=0**。phase1 把内隔墙描到西外墙**内表面**（内缩 240mm，正好等于图上 `240` 墙厚标注），没连到外墙中线。**内墙(双线按内表面)/外墙(粗线按中线)画法差异未统一到中线坐标系**。1f 同。

南立面 F1 左侧短窗（S7）位置 z 偏：phase1 已自标低置信（900/600/1500 链）。

### 2.2 三模型 phase2 对比

| 模型 | 2f 南隔墙 | 几何正确性（对真实设计） | EP 结局 | 行为本质 |
|---|---|---|---|---|
| **Opus** | 3.75/7.50/11.25（读尺寸链） | ✅ 最好（四等分对） | ✅ 完成 / 12 warning（1 CHKSBS=F1 西南低置信短窗超墙） | 按 rules §2.5 "trust the dim" 用尺寸链推翻笔画估值，**显式写明仲裁理由**——不是看图，是选了更权威通道 |
| **Sonnet** | 4.95/7.50/10.05（信笔画） | 忠实复原 phase1（即 phase1 的错） | ❌ **EP 段错 SIGSEGV (exit 139)** | 忠实转写——这是 phase2 本分，但 phase1 给错了 |
| **DeepSeek** | 0/4.11/5.31/10.89（贴窗边尺寸点） | ❌ 最差（1.2m 幽灵房 S2=office2 窗宽） | ✅ 完成 / 6 warning | 既不忠实笔画也不取链中线，抓错尺寸点 |

### 2.3 Sonnet EP 段错真因（已抠顶点确认）

phase1 在 1f 把同一道隔墙估成 **4.90/10.10**、2f 估成 **4.95/10.05**（跨图 5cm 抖动）。下游做跨层楼板配对时，F1 中间南办公室天花（4.90–10.10）切片配 F2 上方房间，错位必然切出 **4.90–4.95 / 10.05–10.10 两条 5cm×3m 退化碎片**（`F1_SM_Office_Ceiling_S2` 顶点 = x[4.90,4.95]）→ EP 在输入处理阶段段错、core dumped、崩在写 .err 前所以 .err 空。

对比：Opus 错位是 1.15m（4.90 vs 3.75）够粗、不成碎片 → EP OK。DeepSeek 碰巧没踩 <0.1m 碎片 → EP OK。

### 2.4 三条关键教训

1. **EP 跑通 ≠ 几何对**：DeepSeek 几何最差（幽灵房）却 EP 最干净；Sonnet 几何最忠实却段错。验收不能只看 EP 通过。
2. **忠实于 phase1 ≠ 正确**：当 phase1 自相矛盾时，忠实转写会忠实地把错误带下去（Sonnet）。
3. **Opus 的"读尺寸链重新理解一次"正是要让所有模型强制做的事**——把偶然做对升格为范式。

---

## 3. 设计哲学：容差内重生成 + 定性优先

把 phase2 从**转写器**升格为**约束求解 + 重生成器**：拿 phase1 的感知（笔画 + 尺寸链 + 置信度），在误差容差内重建一个 EP 合法、定性自洽的拓扑，而不是逐字照搬坐标。一句话：**结合尺寸链和图形再生成一次。**

---

## 4. 关键架构判断：重生成属于 phase2，phase1 保持忠实感知

两步法命根 = **误差预算分离**（phase1 感知图绑定 / phase2 推理图盲）。本轮 4 条改进几乎全是推理/重建操作，**应全部放进 phase2**，phase1 不动这个原则：

- **phase1 配套小改**：别再吐"估算的隔墙坐标"冒充测量值；把笔画 / 尺寸链作为**两个独立通道 + 置信度**交出，不预先替 phase2 仲裁。
- **phase2 重写为约束求解器**：已同时拿到两个通道，不必新增中间步骤。
- **`corrections[]` 审计日志（硬要求）**：phase2 每做一次修正记一条（如"闭合西走廊 0.24m 缝"、"按尺寸链总和=15.0 归一为四等分 3.75"）。**没有这条日志，放宽约束 = 放弃可解释性与可评测性**，误差归因（看错 vs 改错）会失效。

---

## 5. partA 容差校正约束集（设计定稿，2026-06-07 审阅后）

> 取代原"四条改进方向"（用户初步想法）。Codex 审阅 verdict = **整体 sound，3 处修正后逐篇落地**，8 条 finding **全部采纳**。请求 [request](../logs/review/request/2026-06-07_partA_correction_constraint_set_request.md) + 审阅 [review](../logs/review/review/2026-06-07_partA_correction_constraint_set_review.md)。**partA = 校正层**：phase1 噪声/矛盾感知 → 干净自洽、EP 友好的几何基元，并记录每次修正。

### 5.1 切割轴：确定性 vs 判断（= 未来 codify 接缝）

按**操作性质**切，不按现象。这根轴 = 确定性 vs 判断 = 未来切配/idfpy 成熟时可整篇抬走变代码的接缝（确定性篇抬走、判断篇留 LLM）。**审阅修正（finding 2）**：A1/A2 的"确定性"仅在**证据已分级、同一意图墙/轴已判定之后**成立；证据身份、同墙聚类、合法错位 vs 抖动的判别**必须有升级到 A3 的机制**——不是纯机械。

### 5.2 五篇分文档

| 篇 | 类型 | 管什么（审阅后） |
|---|---|---|
| **A0 容差·证据·审计·校验契约** | 脊柱（**升级版**，finding 1） | 容差**分级**（非只数值）+ **证据分级** `direct_measurement\|transcribed_dimension\|estimated_stroke\|inferred_topology\|prior\|unknown` + confidence 模型 + **corrections/conflicts/unsupported schema**（source ids/原值/解析值/rule id/阈值/delta/前后置信/是否改拓扑）+ validation schema + **method profiles**（room_identity/use_grouped_rooms/perimeter_core 各自严格度，finding 7）+ **上游 phase1 provenance 输入契约**（finding 8）|
| **A1 坐标归一化** | 确定性 over typed evidence（+ 升级路径） | 确定路径：世界系 / plan·facade local→world / z-stack / **已知墙厚**的中线转换。升级→A3：墙侧未知 / 缺墙厚 / 原点冲突 / 立面-平面朝向冲突 |
| **A2 正则化/吸附** | 确定性 over typed evidence（+ 升级路径） | 确定路径：规范轴集 / 跨层聚类（**仅当证据说"同一意图墙/轴"**）/ canonical 后再量化 / 子链=总长闭合 / 最小碎片防止。升级→A3：错位超抖动容差 / 语义证据说不同墙·shaft·楼梯 / 聚类会删真房 → A3 或 unsupported |
| **A3 冲突仲裁与补全** | 判断（**mode-aware**，finding 7） | 显式冲突类下的通道优先级 / 缺失补全 / 先验使用规则 / unsupported 策略 / 置信降级 / 决策后**回调 A2 重跑**。perimeter_core 下保守调用，room_identity 下才激进 |
| **A4 建筑常识先验库** | 数据（**硬门控**，finding 5） | 窗台·窗高 / 门·窗宽 / 模数 / 各 space type 房间尺寸先验。**先验只出 warning/score 不直接 correct**；仅证据缺失·矛盾·低置信时才驱动修正；**语义证据支持的异常小房保留或标 conflict**（不归一）；每次用先验记 `prior_id`；**按 building/space type 分型**，禁全局单一最小房表 |

### 5.3 落地序（审阅后微调，finding 3/4）

- **撰写/落地序**：A0 → **（A1-min + A2 同批）** → A4 stub → A3。**不把 A2 独立写在 A1 前**（A2 需坐标系/中线/立面映射前提，先写 A2 会把这些暗埋进去拆不干净）。
- **运行时（带反馈，非单向）**：`A1 → A2-detect → A3-resolve(+A4) → A2-apply → validate`。例：尺寸链 vs 笔画轴冲突，A2 检出、A3 选通道、A2 再确定性建规范轴集。

### 5.4 每篇统一 header 约定（finding 3）

每篇开头声明：消费的 input artifact 字段 / 可写的 output 字段 / 何时必须吐 `corrections[]` / 何时必须吐 `conflicts[]`·unsupported 而非硬修 / 是否可改拓扑。这条 header 约定防止五篇退化成五坨 prompt 散文。

### 5.5 corrections[] 分级（finding 6）

硬要求，但只对**实质改动**。A0 区分四类事件：**normalization**（输出精度内取整，无害）/ **corrections**（改了源值·拓扑·闭缝·吸轴·选了某证据通道）/ **conflicts**（未解或超阈歧义）/ **unsupported**（当前不能安全修）。硬规则：凡改几何超出输出取整、改拓扑、改证据权威、或调用先验，**必须记**；记不出 source ids + rule id 就标 unsupported、别静默通过。

### 5.6 验收（写完 skill 后据此判）

- sm21 全病灶可解释：0.24m 墙侧缝 / 5cm 跨层抖动 / 尺寸链 vs 笔画冲突 / 1.2m 幽灵房疑似。
- 每条 correction 有 source ids + rule ids。
- A2 不得仅凭坐标接近合并轴（语义证据说不同则不并）。
- A4 先验不得覆盖高置信证据、不得抹掉带标签的 service/shaft/WC 房（否则标 conflict）。
- perimeter_core 模式可跳过高细节内房仲裁，同时保住外壳/立面/WWR 正确。
- 旧 phase1 JSON 可降置信运行，但新 provenance 字段须显式声明需求。

---

## 6. 待定取舍（已拍板 / 已被审阅解决）

1. **重生成放哪** → phase2 内（容差校正 partA + zonification + 几何建模），无独立 reconciliation pass。✅
2. **`corrections[]` 硬要求** → 是，但分级、只对实质改动（§5.5）。✅
3. **先验红线** → 确认，且加硬门控（§5.2 A4 / finding 5）：先验只出 score、语义证据优先、记 prior_id、按 space type 分型。✅
4. **阈值框架** → A0 定容差分级 + method profiles（§5.2 A0）；具体数值随首篇落地时锁。✅

---

## 7. 状态与下一步

- 状态：**Phase 1（A0 + A1 + A2）已写 + 审 + 定稿**。三篇均在 [`skills/.../PartA-correction/`](../../skills/energyplus_mcp_twostep/phase2/PartA-correction)：
  - **A0**：8 findings 全纳入（claim-type 分级证据 / 审计 envelope / tolerance registry / 第 7 类 conflict / PartA-scoped validation + 顶层 status / 三档 profile A3-A4 强度 / provenance mode）；容差常数用[检索包](../logs/review/review/2026-06-07_partA_priors_tolerance_retrieval.md)国标值回填（SNAP=50mm/M2、MIN_EDGE=0.1m、gap 100/300/500 分带、WWR/area ±5%、PERIMETER_DEPTH 归 zoning）。
  - **A1（坐标归一化）/ A2（正则吸附）**：A1A2 review conditionally accept + A0 re-verify closeable，6 条 minimal patch 全改（A1 不自行调 A4 先验、facade 竖向走 transform 不硬假设；A2 轴身份只用 AXIS_JITTER_TOL/>则升 A3、SNAP_GRID 非预闭合取整、sliver 吸收作唯一改拓扑且条件化；A0 §4 加轴身份 vs 闭缝 vs 输出优先级）。
- **下一步 = Phase 2：A4 stub（用检索包先验大表填）→ A3**（评测 gated，[plan.md B2-B4](../plan.md) 尺子立起来后放开 A3/A4 精度判断档）。phase1 侧按 A0 §6 上游契约小改（provenance+置信度，归 phase1 skill 另议）；接入 phase2/rules.md 及改既有 skill 按 [CLAUDE.md §6#5](../CLAUDE.md) 备份。
- 检索包先验大表（A4 素材）：[partA_priors_tolerance_retrieval.md](../logs/review/review/2026-06-07_partA_priors_tolerance_retrieval.md)——办公建筑门窗/房间/层高/WWR 国标值 + 红线（先验只出 score、按 space type 分型、不覆盖测量）。
- 依赖/耦合：A1/A2 现在做不浪费（room_identity + use_grouped_rooms 都用，且改善 perimeter_core 的立面/窗锚点）；A3/A4 mode-aware、perimeter_core 下克制（与 [zonification 调研](../architecture/geometry_first_zonification.md) §0 一致）。评测尺子（[plan.md B2-B4](../plan.md)）立起来后才放开 A3/A4 精度判断档。
- 对应任务：[plan.md](../plan.md) B1.5.b（phase1/phase2 skill 迭代）+ B5-B7。
- sm21 实验产物：`test_data/SmallOffice_TwoStep/smalloffice_21/phase2_intake/{deepseek,opus,sonnet}/` + `output_{opus,sonnet}/`（未 commit）。

---

## 8. 两条腿并行：忠实建模 leg（本文档）vs 再拓扑 leg（2026-05-29 决策）

**定调（用户）**：两条腿并行推进，不二选一。

- **本文档 = 忠实建模 leg**：phase2 作容差重生成约束求解器，**保留真实建筑几何**（真墙、真房间）。§1-§7 全部适用——A 类（水密：闭缝/吸附/生成规则）和 B 类（仲裁/常识/审计）**都在 phase2 解**，没有剖分内核兜底水密。
  - **本项目之外的价值**：若真能约束出高建模质量，等于实现了一个 **图纸 → 建筑几何模型** 的小 Agent 流程。这个忠实保留建筑空间的能力本身就有产品价值，不止服务 EP。
- **[geometry_first_zonification.md](../architecture/geometry_first_zonification.md) = 再拓扑 leg**：抽象成热区积木块、**丢弃真实建筑空间信息**；A 类降为内核构造不变量、B 类迁入 phase2a 判断层。对 EP 鲁棒性最优，但**相对原始信息变化最大**（最激进）。
- **关系与节奏**：再拓扑确实最好（EP 几乎必通），但变化大；先作**强力支线**推进、实验稳定了再切过去。忠实 leg 因其 beyond-EP 价值**独立继续落地**，不被再拓扑取代。

### 8.1 两 leg 对 A/B 两类问题的处置差异

> A 类 = 几何装配/水密性（"积木怎么拼合法"）；B 类 = 噪声/矛盾感知下的判断（"说谎的图纸里正确几何是什么"）。

| | 忠实建模 leg（本文档） | 再拓扑 leg |
|---|---|---|
| A 类（水密装配） | phase2 重生成求解器解（§5.1/§5.4 生成规则**全保留**） | 内核构造不变量（自动免费） |
| B 类（噪声仲裁/常识） | phase2 解（§5.2/§5.3/corrections **全保留**） | phase2a 判断层解（仍需） |
| 真实建筑几何 | **保留**（产品价值所在） | 丢弃（抽象成块） |
| 崩溃安全网 | **保留**（错几何仍可能 EP 段错 = 有用信号） | **撤除**（任何剖分都水密必通 → 错而不崩，B 类成唯一守门人） |
| 相对原始信息变化 | 小（忠实） | 大（激进） |

> **更正注（2026-06-07，术语锁定后）**：上表「A 类（水密装配）」一行**已不成立作差异点**。按 2026-06-07 约定，水密装配 = **切配**（面切成 EP 一一对应）= **确定性算法、对两腿是同一个**（两腿产出的 zone 体块粒度不同，但都喂同一个切配），下游另有人做、不归本项目管。因此两腿的真正差异**只在 zonification 的方式与粒度**（真实房间=zone vs 平面先划少而大的热区）+ 随之而来的**校正精度需求**（忠实需高、再拓扑省）。「真实建筑几何 保留/丢弃」「相对原始信息变化 小/大」两行仍成立；「崩溃安全网」一行的口径也随切配统一为确定性而变（两腿都靠确定性切配水密通过，崩溃安全网论点需重审，待 partA 讨论时一并处理）。

### 8.2 共享基础设施
两 leg 共用：phase1 忠实感知（笔画+尺寸链+置信度双通道）、两步法误差预算分离、下游 9 subagent、InterZone 门、**校正(partA)、几何建模、切配**。差异只在 **zonification 这一段怎么从平面定出 zone**——忠实 leg 是"房间=zone 保留真墙"，热区再拓扑 leg 是"平面先划少而大的热区"。
