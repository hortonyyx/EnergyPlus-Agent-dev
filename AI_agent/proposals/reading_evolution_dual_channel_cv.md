# 方案：reading 演进 —— 证据门硬化 + 算术下沉 + 双通道感知 +（远期）CV 前端

> 状态：**Phase A 待 Codex 双审**（2026-06-30）。来自 sm21 脚手架恢复实测 + 三方诊断综合
> （Claude 实测 + 外部模型"可恢复性规则" + Codex 独立架构回归审）。
> 关联：[plan.md N1e/N1f](../plan.md)、[pipeline_stage_contracts.md §0.3/§1](../architecture/pipeline_stage_contracts.md)（0-5 分工铁律）、
> [reading-honest 架构 D1-D5](../decision_log.md)、[proposals/cad_to_gt_extraction_plan.md](cad_to_gt_extraction_plan.md)（DXF 基建复用）。
> 证据：[logs/review/2026-06-30_reading_scaffold_restore_validation/](../logs/review/2026-06-30_reading_scaffold_restore_validation/)（实测）、
> [logs/review/review/2026-06-30_reading_architecture_regression_review.md](../logs/review/review/2026-06-30_reading_architecture_regression_review.md)（Codex 审）。

---

## 0. 一句话

reading 相比旧 phase1 确实变弱，根因 = **prose 要求双通道证据、但 schema/validator 把缺失/弱证据当 clean 放行**
（prose↔gate 执行落差）。修复主轴 = **先把"证据完整性门"硬化（让 reading 弱可见、尺寸错变响）**，
再把"VLM 又感知又算几何"收敛成"VLM 忠实感知双通道、代码算几何"（补全 0-5 那条 reading 只做了一半的原则），
CV/OCR 留后档。**口径**：sm21_pre/phase1（墙9/9·窗14/15）= **回归地板不是天花板**（[[reading-scaffold-restore-policy]]）。

---

## 1. 诊断（三方收敛，已核验）

**实测**（2026-06-30，冷启 Sonnet n=2，恢复后脚手架）：墙均 9/9，但过度分割 run 方差主导（r1=0 / r2=+4）。
attempt 级证据：内墙 x 坐标**全来自尺寸链累加算术**、像素 `anchor` 字段空着、r2 伪墙落窗 jamb 处 `prov=seen`。

**根因（精确）**：
1. 尺寸链在每个构件处分段；VLM 锚链段界画墙，光看链分不清"断点是隔墙还是窗 jamb"→ 窗的尺寸被当"可能有墙"。
2. 判别"是不是墙"的证据是**视觉的**（真隔墙画贯穿进深的墙线），但 VLM 在**用数字推理**；不确定就让链幻觉墙。
3. **架构**：reading 现在做累加算术 = **违反 0-5"LLM 感知、代码算几何"**。

**Codex 架构回归审（已逐条核验，见下表）**：变弱是真的，且根子是 **prose↔gate 执行落差**——
旧 phase1 reading 更强（9/9·14/15），当前 gate① 对"无 dimensions / 无 P1a chain / legacy provenance"**不设硬门**，
所以 reading 弱仍结构性通过，correction 在**救场**而非规范化，"pipeline 绿"掩盖"reading 弱"。

**Codex BLOCKER 核验结果**：

| Codex 断言 | Claude 核验 | 结论 |
|---|---|---|
| B1 dimensions 可空被当 clean | gpt54 1f `dimensions_len=0`；schema `dimensions` default `[]`、P1a 全 optional | ✅ 属实 |
| B2 chain closure 不强制 | `dimension_chain_closure` **代码已存在**（Σ段=总），无 chain_id 即 `NOT_APPLICABLE` 跳过 | ✅ 属实（关键：闭合自校验**已写好、被静默跳过**）|
| B3 facade E/W sign 冲突 | facade.py East`-1`/West`+1` vs A1/old-phase1 East`+1`/West`-1` | ✅ 属实 **+ nuance：facade.py 0 调用点=未接线 dead code、潜伏地雷非活 bug** |
| B4 gate1 全绿 reading 仍错 | Sonnet run 58 pass/0 flag/0 block 却 quarantine | ✅ 属实 |

**关键澄清（纠正"像素最忠实"前提）**：对 **VLM**，"按像素算"最不可靠（像素定位是弱项）。对立轴 = **感知 vs 计算**，
不是像素 vs 尺寸链。像素忠实的正解是经典 CV / 专用模型（Phase C），非把 VLM 逼成像素尺子。

**外部模型的"可恢复性规则"**（采纳为档位判据）：对每个子任务问"correction/几何阶段能否从此模型的错误恢复？"
能恢复 → 弱模型/VLM 够；不能恢复 → 才值得上更可靠抽取器。落到这里：
- 粗墙/洞口结构 = **可恢复**（correction 设计就吸收缝/偏移/拓扑噪声）→ VLM + 脚手架。
- **尺寸 = 唯一不可恢复**（数字读错下游无信息还原）→ 但见下"闭合反转"。

**OCR 闭合反转（Claude 综合的关键贡献）**：尺寸不可恢复**不是二元**——破坏链闭合的 misread = **可检测**（闭合 fail→reread）；
只有"碰巧仍闭合"才真不可恢复。`dimension_chain_closure` 已写好、只因 chain_id optional 被跳过。
∴ **第一刀不是上 OCR，是强制 chain_id + 激活闭合门**（用已有代码把 silent misread 变 loud），OCR 留作并行降率（暂不起）。

---

## 2. Phase A（本轮）：证据完整性门硬化 —— image-blind、不拆 schema、基本不重录

> 目标：让 reading 弱**可见**、尺寸错**变响**、"pipeline 绿"不再掩盖"reading 弱"。全是 gate/validator/报告/测试，
> reading↔correction 契约不动。**用户已定本轮做 A、OCR 不起、B/C 后续。**

> **以下为 Codex 双审（APPROVE-WITH-CHANGES，1B/6M/3MINOR，`..._reading_phase_a_spec_review.md`）后 Claude 裁定的修订版**（全采纳）。

**A1. 激活尺寸链闭合 —— 要"链完整性"不是只要 chain_id**（Codex BLOCKER）：dimensioned view 必须有 dimensions；
  闭合检查按 **`(chain_id, axis)` 分组**（防 X/Y 或 plan/elevation id 撞），每组须有 overall/baseline + ≥1 ordered segment；
  无 chain_id / 不完整链 / 不闭合 → **evidence 债（非静默 pass）**。**明示局限**：闭合抓**多数**非全部 misread——
  自洽错读仍闭合（已有测试 `test_checks_reading_correction.py:355` 坐实），故 A1 与 A6/A9 合力、非单点万能。
  动 `src/validator/checks/reading.py::_chain_closure` + `check_reading_view`。
**A2. `dimension_derived ⇒ dimension_refs 非空且可解析**（纯门、不 mutate，Codex MAJOR6）：refs 必须指向存在的 dimension id；
  否则 **flag/block**（删原"降级 estimated"——validator 不得改写 view；如需归一另起 normalizer，本轮不做）。
**A3. gate 信号拆四档 + 机器可读 plumbing**（Codex MAJOR1/MAJOR2）：`syntax-valid` / `evidence-clean` / `J0 semantic-clean` / `pipeline-recovered`。
  - **新增 run-intent 载体**：`RunPolicy.run_profile`（exploratory|dev|golden|regression），**不复用 `capability_profile`**（那是几何能力非质量政策）；
    经 `validation_run.validate_case` → `run_stage` → `record_baseline` → 报告 一路串下去。
  - **evidence 信号机器可读**：加 evidence 类别 / 稳定 check-id allowlist（别从 prose 推），让 `evidence-clean` 红能被报告读到。
  - 报告改两处：`record_baseline.py:504`（facts/baseline.json）+ `report_assembly.py:301`（标记聚合）。
**A4. dimensioned fixture ⇒ `dimensions[]` 非空 + 新（非 legacy）reading 带 P1a 字段**（Codex MAJOR3 + Gap）：
  需 **"该图有尺寸标注" 的元数据源**——case manifest（`testdata_prompt.json` 现不声明）或 RunPolicy；本轮在 case 元数据加一处声明。
**A5. provenance coverage 升级**：`legacy`/`partial` provenance 在 golden/regression → flag/block（现总 add_pass，`reading.py:501/519`）。
**A6. window-jamb 交叉门 —— 缩到 per-view 真有的证据**（Codex MAJOR4）：扩 `_stroke_dimension_consistency`，
  独立证据**仅用**：窗 stroke 几何（rect `x_range_m`/line 端点 → jamb x）、墙轴线、wall-join 证据、链累加位。
  **去掉 wall_fill/thickness**（plan thickness 本就 null）；**跨层一致挪 run 级单独 check**（per-view 拿不到多视图）。
**A7. legacy 原始字段存在性留痕 —— 提进核心批**（Codex 测序：A4/A5 需它区分 legacy/defaulted）：在 `legacy.py`/加载器留
  `raw_has_dimensions/raw_has_uncaptured/legacy_migrated`（优先 sidecar 元数据、不加输出字段），让"default 成 clean"≠"真 clean"。
**A8.（本轮 DEFER，Claude 裁定）correction 不为缺证据"发明"尺寸**：Codex MAJOR5——它要**确定性路由**非 prompt 指令、
  且触 correction 契约（`needs_reread` 非现有字段）。**拆到 A1/A2/A4 落定证据债事实后的跟批**做（确定性 preflight：golden/regression 把证据债路由 reread；exploratory 把证据债摘要喂 correction 出 `unsupported`）。
**A9. score_reading_vs_gt 接进 sm21 reading regression harness**：phase1（9/9·14/15）作回归**地板**；
  **加纯 JSON 模式**（现 `--json` 仍先打人读行，`score_reading_vs_gt.py:98`）。判 side 不破 gt 隔离（`reading_score.py:10` + `test_gt_discipline`）。
**A10. E/W sign：gt 锚定测试 + 翻 facade.py 常量**：以 A1（East+1/West−1，gt-validated）为准；test-first 断言
  `to_world_along()` 的 **sign**（现 East 测只测 axis/base 不测 sign）→ fail on 现 facade.py（East−1/West+1）→ 翻两常量。
  **gt 锚点用 East-F2 + West-F2 窗世界 x**（`gt.json:300/323`；**West-F1 窗数=0、原"W1"写错**，Codex MINOR2）；judge/test side 读 gt。
  facade.py 未接线（仅测试引用）→ 现在翻安全。守 [[derive-facade-frame-unwired-ew-sign-trap]]：授权来自 gt 证据非推理。

**flag vs block 裁定（Claude 定，用户授权）**：
- syntax-invalid → **永远 block**；
- evidence-incomplete → **exploratory/dev = flag**（可见、喂 J0+reread、run 续；evidence-clean 转红）/ **golden/regression = block**；
- **legacy_migrated 祖父化**（Claude 裁 MAJOR3）：evidence 门只 block **非 legacy** reading；现有 2 个 legacy golden（opus 06-16/sonnet 06-15）= 已知 wart、待 sm21 批次重录自愈，**不被本轮打 block**。
- flag 永不等于忽略（路由 J0/reread + 转红信号）。

**Phase A 执行顺序（采纳 Codex 测序）**：①A3 政策/信号 plumbing → ②A7 raw 元数据 → ③A1/A2/A4 证据门 → ④A5 provenance 升级 → ⑤A9 评分 harness → ⑥A6 jamb 冗余 → ⑦A10 E/W sign（独立，可早可晚）。**A8 defer 到跟批。**
**golden/测试影响（Codex MAJOR3，须预案非事后发现）**：A1/A4/A5/A7 在 block 模式会动 sm21 golden 期望——靠 legacy 祖父化避开现有 golden；新 sm21 批次重录产合规 golden。预期触及 `test_validation_run_baseline.py:216`、`test_orchestrate_baseline.py:142/224`。
**代价**：validator/checks + policy + record_baseline + report_assembly + 测试 + case 元数据；**reading/correction schema 契约不动**（A8 defer 故不触 correction 契约）。

---

## 3. Phase B（后续·根治）：双通道 reading + 算术下沉代码

- **双通道 schema**：每元素带 `visual{anchor_px|null, relative, confidence}` + `metric{dimension_refs, raw_segments, confidence}` + provenance；**reading 不吐最终米制坐标**。
- **确定性尺寸约束求解器**算几何（"尺寸驱动重建"非"像素几何重建"——施工图里尺寸才是真值）；再拓扑用 **Shapely `polygonize`**（外部建议，别自写平面剖分；更鲁棒可 CGAL arrangement）。
- correction 分**确定性**（吸附闭合/共面/规整）vs **语义**（"窗属哪个房间"）——前者纯几何、后者才动 LLM/规则。
- 在此**接线 `derive_facade_frame` + 锁 E/W sign**（B3/backlog#3）= 确定性 local→world 可审变换产物（+ 每 run persist facade transform 表，治 MAJOR4）。
- 好处：算术-致-过度分割从源头消失、双通道给 correction 仲裁、reading 任务变小利于弱/开源 VLM、接上"plan-local→world 一等变换"坑。
- 代价：新 schema + 求解器 + correction 改 + **重录 baseline**；走 Claude 方案→Codex 审→Codex 执行。

---

## 4. Phase C（远期·并行 R&D，暂不起）：OCR + CV 前端

- **C1 PaddleOCR** 当尺寸数字值源（中文图开箱、不训练）——降 misread 率、兜"碰巧闭合"残余。**闭合门优先、OCR 之后**（用户定暂不起）。
- **C2 CV 前端**（仅泛化逼迫时）：**起手式 = DXF→(PNG, 逐层掩膜) 数据工厂**（复用 CAD→gt 基建，免人工标注）→ 经典 CV（LSD/Hough 抽墙线 + 形态学 wall_fill + 线宽剥尺寸层 + 比例尺=尺寸文字↔延伸线像素距）→ 必要时训检测器（YOLO/分割）。现成预训练（CubiCasa5K/HEAT）有域差、当对照。
- 立项理由 = 复杂真实图**缺尺寸标注**时几何只能从像素来。**用户判断：自训泛化太差（reading 要吃各种风格图），先不上 CV**；保持"维护脚手架 + 后续按子任务拆"。
- 嵌 0-5：CV 跑 VLM 前出确定性视觉通道，VLM 退化成语义活——比现状更贴 0-5 北极星。

---

## 5. 决策记录（用户已拍）

1. **E/W 约定**：以 A1（East+1/West−1，gt-validated）为准；facade.py 错、Phase A test-first 翻常量 + 加 gt 锚定 E/W sign 测试。
2. **OCR 时机**：闭合门优先，**OCR 暂不起**（Phase C）。
3. **flag vs block**：syntax→永久 block；evidence→exploratory=flag / golden=block（Claude 裁定、用户授权）。
4. **本轮范围**：**Phase A**（A 先做，B 后续，C 不急）。

---

## 6. 推进

- **✅ Codex 方案审已闭环（2026-06-30，APPROVE-WITH-CHANGES，1B/6M/3MINOR，全采纳）** → §2 已为修订版（链完整性/run_profile/机器可读信号/legacy 祖父化/A6 缩范围/A8 defer/A10 锚点修正/Codex 测序）。审轨 `logs/review/review/2026-06-30_reading_phase_a_spec_review.md`。
- **下一步 = 派 Codex 执行器**（简报含「审阅需求」自报需复核处）→ Claude 大节点全面审（自跑 pytest + 逐行 diff + sm21 重跑对 score）。
- 按 [[codex-execution-protocol]]；Claude 不亲手写 src/。
