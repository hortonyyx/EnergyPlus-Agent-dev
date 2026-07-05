# 方案：A8 —— correction 缺证据 → 确定性路由（Phase A 下游闭合）

> 状态：**定案（§6）—— Claude+Codex 两轮讨论收敛、用户 2026-07-01 ratify 全 6 条，待派 Codex 执行**。
> 关联：[reading_evolution_dual_channel_cv.md §2 A8](../../../proposals/reading_evolution_dual_channel_cv.md)（本方案的母条目，Phase A 裁定时 defer）、
> [plan.md N1g](../../../plan.md)。
> 前置：Phase A（`6.30_ReadingEvidenceGateHardening`）已把「证据债」变成机器可读事实（run_profile / evidence check allowlist / 四信号）。

---

## 0. 一句话

Phase A 让 reading 弱**可见**（证据债 = flag/block by run_profile），但 **exploratory/dev 档证据债只 flag、run 会继续走进 correction**，
此时 image-blind 的 correction 仍可能为「缺尺寸/弱证据」的元素**发明坐标**。A8 = 在 correction LLM 调用**之前**加一道
**确定性 preflight**，按 run_profile 分流证据债，堵住「发明尺寸」这个下游漏洞。

---

## 1. 接缝盘点（Phase A 落地后的现状，已核到行）

| 事实 | 位置 |
|---|---|
| 证据债 = 6 个 evidence check id | `src/validator/checks/schema.py:41` `EVIDENCE_CHECK_IDS` |
| disposition 按 run_profile：golden/regression→BLOCK，exploratory/dev→FLAG | `schema.py:52` `_EVIDENCE_BLOCK_PROFILES` + `disposition()` |
| 四信号（含 `reading_evidence_clean`）已聚合进 baseline | `src/agent/execution/orchestrate.py:77-119` `summarize_gates` |
| `run_profile` 已一路串到 validation/orchestrate/report | `policy.py:44` → `validation_run.py` → `record_baseline` |
| **golden/regression 证据债 BLOCK → reread 已通** | gate① fail → `routing.py:38` `route_stage_failure(0_reading=MANUAL)` → `AWAITING_REREAD`（`reading_runner_available` 时） |
| **`run_correction` 是 correction LLM 唯一入口**，orchestrator + run_pipeline 共用 | `run_stage.py:135` 调 `run_correction(...)`；`pipeline._build_correction_messages` 构 prompt |
| correction prompt 已有结构化输入通道（room_labels / feedback） | `pipeline.py:334-348` |
| `unsupported` 已是 CorrectedGeometry 既有字段（LLM + 确定性核共用） | `correction/schema.py:78`；`deterministic.py` 多处 append |

**关键推论**：
1. **golden/regression → reread 分支 Phase A 已闭合**（走 orchestrator 的 `AWAITING_REREAD`），A8 在此**不新增契约**。
2. ∴ **不需要给 CorrectedGeometry 新增 `needs_reread` 字段**——这消解了 A8 defer 时「触 correction 契约」的顾虑（原提案 §2 A8 的主要顾虑）。
3. A8 的**真正新增价值集中在 exploratory/dev 分支**：证据债 flag、run 续 → correction 目前**看不到证据债** → 可能编坐标。

---

## 2. 设计（三件）

### A8.1 确定性 preflight 函数（新）
- 位置建议：`src/agent/execution/`（消费 CheckReport，属编排/执行地基，非 validator 事实层）。
- 输入：reading 阶段 CheckReport（或 run_dir 下已落盘的 reading checks）+ `run_profile`。
- 逻辑：从 evidence check 结果抽机器可读证据债清单 `EvidenceDebt`（**复用 `CheckResult.evidence` dict，不重算**）——
  哪个 view、哪条 check、机器可读细节（`dimensions_len=0` / 不闭合的 `(chain_id,axis)` / provenance=legacy 的 stroke id / dimension_derived 悬空 refs）。
- 输出：`EvidenceDebt`（结构化、可序列化，落 `1_correction/evidence_debt.json` 留痕）。

### A8.2 golden/regression 分支 = 确定性 fail-closed（补 run_pipeline 缺口）
- orchestrator 路径：**Phase A 已覆盖**（block→AWAITING_REREAD），A8 不动。
- **run_pipeline 一次性路径**（`pipeline.run_pipeline`，image-blind 便捷跑，不跑逐段 gate）：若 `run_profile ∈ {golden,regression}` 且 preflight 检出证据债 →
  **correction 前 fail-closed**（raise/停，不静默续），错误信息指向 reread。**（待 Codex 核实：run_pipeline 是否确实是 golden 会用的路径 / 现状是否真无拦截——见 §5 Q3。）**

### A8.3 exploratory/dev 分支 = 确定性 manifest 注入 correction
- `run_correction` 增 `evidence_debt: EvidenceDebt | None = None` 入参（默认 None = **完全向后兼容**，走 feedback 一样的可选通道）。
- `_build_correction_messages` 把 `evidence_debt` 作为**结构化输入块**注入 prompt（复用 room_labels 的注入模式）。
- correction prompt 增一条硬纪律：**「evidence_debt 列出的元素证据不足——不得为其发明世界坐标；无独立证据支持即落 `unsupported`（既有字段），不要静默填值。」**
- 可选兜底 **A8.3b（确定性 CROSS_CHECK，flag 非 block）**：correction 输出后，代码核对「证据债元素是否要么有独立证据、要么落了 unsupported」，否则 flag。让 prompt 纪律有**确定性可见兜底**、不纯靠 LLM 自觉。

---

## 3. 关键裁决（请 Codex 挑战）

1. **exploratory 分支的 prompt 张力**：Codex MAJOR5 原批评「correction 不为缺证据发明尺寸」要「确定性路由**非 prompt 指令**」。
   本方案 exploratory 分支仍含 prompt 纪律。**裁决理由**：
   (a) manifest 本身**确定性、可审计、可落盘**（不是让 LLM 自己判断哪里缺证据）；
   (b) exploratory 本就是「可见+续跑」档，架构上允许 LLM 参与（golden/regression 才走 fail-closed/reread）；
   (c) **真正的确定性强制留 Phase B**——双通道 schema 让 reading 不吐最终坐标，correction 天然无法「发明」；A8 现在做深契约改会与 Phase B 重叠、浪费。
   (d) A8.3b 的确定性 CROSS_CHECK 兜底把「纯 prompt」升级为「确定性事实 + prompt 纪律 + 确定性事后核」。
   → **A8 exploratory = 轻量确定性 manifest + prompt 纪律 + 可选事后门；不做 CorrectedGeometry 深契约改。**
2. **不新增 `needs_reread` 字段**（§1 推论 2）——请 Codex 确认 golden/regression 的 reread 确实由既有 `AWAITING_REREAD` 完整覆盖、A8 无需碰 correction 契约。
3. **范围边界**：A8 只堵「exploratory 编坐标」+「run_pipeline golden 缺口」；不重构 correction、不动 reading↔correction schema 契约、不动 Phase A 的 gate 判定。

---

## 4. 契约 / 测试影响
- **契约**：CorrectedGeometry / reading schema **不动**。`run_correction` 增可选入参（向后兼容）。可能新增 `EvidenceDebt` 轻量 model + `evidence_debt.json` 留痕文件。
- **测试**：① preflight 从 CheckReport 抽证据债（含空债=no-op）② exploratory 下 evidence_debt 注入 prompt 且证据债元素落 unsupported ③ golden/regression run_pipeline fail-closed ④ A8.3b CROSS_CHECK ⑤ 向后兼容（evidence_debt=None 行为不变）。
- **golden 影响**：预期**零 golden 变更**（A8 不改 gate 判定、不改既有 clean run 的 correction 输出——evidence_debt 为空时完全 no-op）。请 Codex 核这条。

## 5. 给 Codex 的审阅问题
- **Q1** exploratory 分支的 prompt 张力裁决（§3.1）是否可接受？还是坚持 exploratory 也必须纯确定性（preflight 直接把证据债元素强制标 unsupported、LLM 不碰）？后者的过激风险（证据债≠一定不可修）与 Phase B 重叠如何看？
- **Q2** preflight 落 `src/agent/execution/`（编排层消费 CheckReport）是否正确层次？还是应属 validator？
- **Q3** run_pipeline 在 golden/regression 下 correction 前**当前是否真无证据债拦截**（§2.2 假设）？run_pipeline 是否是 golden baseline 的实际路径，还是 orchestrator/run_stage 才是（若后者，A8.2 的 run_pipeline 补丁降为次要）？
- **Q4** A8.3b 事后 CROSS_CHECK 是必要兜底还是过度工程（prompt 纪律 + Phase A 既有 jamb/consistency check 已够）？
- **Q5** 有无遗漏的证据债消费路径（如 4_mep 也会因 reading 弱证据受影响）？A8 是否应只限 correction、还是 evidence_debt 应更广地留痕给下游？

---

## 6. 定案口径（Claude+Codex 两轮讨论收敛 + 用户 2026-07-01 ratify 全 6 条）—— 执行依据

> 本节 **supersede §2–§5 的开放式表述**。执行以本节为准。

**本质定性（用户已 ratify）**：Phase A 让"reading 弱"变成机器可判定的**结构性证据事实**（非置信度分数：无 dimensions / 链不闭合 / dimension_derived 指不到 refs 等）。A8 = 让证据债**有后果**——给 correction 这个尚不完善的软环节装**第一个仪表 + 前后确定性卡门**：中间 LLM 那步仍软（prompt 纪律），A8 只在前后各包一层确定性代码去消费+兜底。零改契约是**顺序**（先可观测攒样本、再谈硬化），非妥协。

**6 条敲定口径**：
1. **evidence_debt.json = 确定性投影 / 交接产物，非"唯一真相源"**。真相源永远是 0_reading CheckReport 的 6 个 evidence check 结果；evidence_debt.json 由 preflight 对该子集**确定性投影**（过滤 + 重判 disposition + 整形），**可随时从 CheckReport 重算**（防双写 drift）。
2. **A8.3b = 必需的 correction 后确定性 CROSS_CHECK**，disposition by run_profile（exploratory=flag / golden·regression=block）。只做**覆盖性校验**（债元素是否被显式回收/标注），**不判坐标对错**。**明标强弱不对称**：element-local 债（`dimension_derived_refs.offenders` 指具体 stroke）→ 强核到 cell/window；view/global 债（`dimensions_present=0`、chain 不闭合）→ 映射不到具体 cell、退化为"audit 是否提及该债"的 advisory 级。文档不得把它当均匀强门。
3. **unsupported 不混写**：LLM 侧用既有 `conflicts` 表达"证据不足未决"；`unsupported` 仍只归确定性核写入。**零改 CorrectedGeometry 契约**。
4. **run_pipeline 口径 = "永远产投影、按 profile 设防"**：给 `run_pipeline()` 加可选 `run_profile`（默认 `exploratory`）。correction 前**总是**现算 reading 证据投影（复用 `check_reading_view`，只算 reading、不改契约）并落 `1_correction/evidence_debt.json`（全路径可观测）；但**仅 golden/regression 才 fail-closed**。默认 exploratory 只多一个 advisory 产物、生成行为不变。（"现算"= 现算投影/重判 disposition，**不等于**默认开 gate。）
5. **扩展位最小化**：manifest 只留 `schema_version` + `producer` 两个追加友好字段。**不预搭 severity 分级 / check 家族框架**（样本少 = 少猜结构；留空间 = 最小+追加友好，不是提前搭满货架）。
6. **preflight 按当前请求的 run_profile 重判 disposition**，**不信任落盘 CheckReport 自带的 profile**（同一 reading 事实 exploratory=flag、golden=block；投影可重算的前提就是 disposition 随当前运行意图重判）。**必测**"report.run_profile=exploratory 但 preflight run_profile=regression 仍 fail-closed"。

**边界 / 层次确认**：
- preflight 落 `src/agent/execution/`，复用 validator 的 `disposition()` / `is_evidence_check_id()`；**validator 保持纯事实层**（不知道 correction / unsupported）。
- **不新增 `needs_reread` 字段**：golden/regression 的 reread 走既有 `AWAITING_REREAD`（stepwise：`step_orchestrator.run_one_stage()` 在 `reading_runner_available=True` + 0_reading gate① blocking 时转换；runner 不可用 → human/hard-stop，A8.2 须显式声明此依赖与降级行为）；run_pipeline 便捷路径用 correction 前 fail-closed 抛错。
- correction 入口两条路径都汇到 `run_correction()`（stepwise `scripts/tool_scripts/run_stage.py:_draw_correction()` + `run_pipeline()`）；preflight/manifest 注入在 `run_correction()` 单点，覆盖两路。
- 4_mep 不直接消费 reading；evidence_debt.json 作 run 级留痕进 report/evidence index 供归因，**不扩 prompt 到 4_mep**。
- **预期零 golden 变更**（evidence_debt 为空时全 no-op；不改 gate 判定）。

**测试清单**：① preflight 从 CheckReport 投影（空债=no-op）② preflight 用当前 run_profile 重判（第 6 条必测）③ exploratory 下 evidence_debt 注入 prompt ④ A8.3b 覆盖门 element-local 强核 + view/global advisory ⑤ golden/regression run_pipeline fail-closed ⑥ 向后兼容（run_profile 默认 exploratory / evidence_debt=None 行为不变）⑦ 零 golden 变更回归。
