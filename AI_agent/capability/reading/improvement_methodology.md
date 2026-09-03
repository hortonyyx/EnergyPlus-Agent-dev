# 识图（0_reading）提升 —— 统一管理文档（方法论 + 诊断 + 路线 + 决策）

> **⛔⛔ 时效 banner（2026-08-18 加）**：本文 §0–§7 写于 **2026-07-03 前后**，其中多条主张**此后已被实测降级或推翻**
> —— 尤其「给了 CV 工具就会去量」（08-16 E1 证伪）、以及把 07-07 那次成绩当可审计基准（08-15 查出「不可审计」）。
> **当前口径与全案现状请先读**：
> [CLAUDE.md §2 的 reading banner](../CLAUDE.md) · [plan.md 当前焦点](../plan.md) ·
> **[reading 回归全案报告](../logs/reviews/request/2026-08-18_reading_regression_external_investigation.md)**（一份读完全案）。
> 本文保留价值 = **方法论与 forensics 原文** + **§8 的环节控制边界条文**（从 CLAUDE.md 迁入）。


> **本文 = reading 提升的唯一管理文档**（2026-07-02 立、2026-07-03 折入原 proposal 统一）。凡 reading 提升的
> 诊断、路线（Phase A/B/C）、决策记录、方法论、待办，**都在这一处**。
>
> **文档职责划分（用户 2026-07-03 定）**：`proposals/` = **纯设想、完全没动工**；一旦**动工**（哪怕只落地一档），
> 就整个搬进 `capability/` 的具体能力提升文档，**不再两处并存**（免职责重叠、内容漂移）。reading 提升已动工
> （Phase A 已落地），故原 `proposals/reading_evolution_dual_channel_cv.md` **已折入本文并删除**。
>
> 缘起：`sm21_anchor/run_2026-07-02_sonnet_flow_e2e` 一次冷启 Sonnet 5 reading **几乎完美还原**
> （墙 9/9·窗 15/15·过度分割 0·全 0.0m 偏移，超 sm21_pre 地板），是难得的高质量样本，反推出 reading 提升的方法论。
>
> 关联：[recognition_modeling_capability.md](recognition_modeling_capability.md)（识图→建模质量主线）·
> [pipeline_0-5_capability_upgrade_suggestions.md](pipeline_0-5_capability_upgrade_suggestions.md)（建筑复杂度 C2/C3/C4）·
> [proposals/cad_to_gt_extraction_plan.md](../proposals/cad_to_gt_extraction_plan.md)（DXF 基建复用，Phase C 数据工厂）·
> [[reading-quality-investigation-2026-06-24]]·[[judge-gt-authoritative-images-auxiliary]]·[[run-provenance-recording-requirement]]·
> [[reading-cv-toolkit-methodology]]·[[reading-scaffold-restore-policy]]。
> 落地轨迹（Phase A）：`logs/experiments/2026-06-30_reading_scaffold_restore_validation/`（实测）+
> `logs/reviews/verdict/2026-06-30_reading_phase_a_spec_review.md`（Codex 审）。

---

## 0. 一句话

reading 相比旧 phase1 曾变弱，根因 = **prose 要求双通道证据、但 schema/validator 把缺失/弱证据当 clean 放行**
（prose↔gate 执行落差）+ **VLM 又感知又算几何**（违反 0-5「LLM 感知、代码算几何」）。修复主轴 = **先把证据完整性门
硬化（让 reading 弱可见、尺寸错变响，Phase A ✅）→ 再把"算几何"从 VLM 下沉成确定性代码（Phase B）→ 远期 CV/OCR
前端（Phase C）**。

**2026-07-03 的新实证（本文核心补强）**：一次高质量样本坐实——reading 好**不是"Sonnet 5 眼睛更准"，而是模型自发
写代码（PIL 灰度投影 + numpy + scipy 连通域）把识图做成一套轻量经典 CV——它在「量」不在「看」**。这印证并细化了
「像素忠实的正解是经典 CV、别把 VLM 逼成肉眼像素尺」的判断，给出更可操作的形态：**把这套经典 CV 做成 reading 阶段
的显式工具箱**（Phase B 算术下沉的具体载体），让模型直接调、省发明成本、且弱/开源 VLM 也能借拐杖量准。

**口径**：sm21_pre/phase1（墙9/9·窗14/15）= **回归地板不是天花板**（[[reading-scaffold-restore-policy]]）。

---

## 1. 实证样本 forensics（run_2026-07-02_sonnet_flow_e2e）

**数据来源**：冷启 Sonnet 5 子代理完整 transcript（112 次工具调用：60 Bash / 45 Read / 7 Write）。

### 1.1 模型做了什么（技法）
reading 全程几乎是一套**自己临时搭的经典 CV 流水线**，不是"看图填坐标"：
1. **裁图放大**（PIL `crop`）：先躲开「整张满家具平面一眼看花」的老失败模式（sm21 南带过度分割的历史病根，见 [[reading-quality-investigation-2026-06-24]]）。
2. **灰度掩膜 + 行/列投影定位墙线**：`R≈G≈B 且 60<v<230` 的掩膜隔离灰色墙体像素（排除黑色 tick、白底、绿色尺寸字），对行/列求和取峰值 = 墙的**精确像素位置**。
3. **像素→米标定**：以总尺寸（15000mm = 图宽像素跨度）反推 px/m，把像素位置换算成米 → 9 条墙**全中 0.0m**（肉眼绝无可能全 0，这是「量」出来的直接证据）。
4. **scipy 连通域**（`ndimage.label`）在立面上框窗、数窗 → 窗 **15/15**。

**没用 OCR**：印刷尺寸数字是模型自己 VLM 读的（提供标定锚），几何坐标是像素量的。

### 1.2 时间线（坐实"第一张慢、后面快"）
| 图 | tool 次数 | 耗时 | PIL/像素操作 | 备注 |
|---|---|---|---|---|
| **1f（第一张/pilot）** | 37 | **~30 min** | 30 | **发明并调 CV 配方**（灰度阈值/标定/投影方式的试错） |
| 2f | 13 | 12.3 min | 11 | 复用配方，平面 |
| South | 10 | 13.9 min | 6 | 立面新类型，重建窗检测（scipy） |
| North | 5 | 3.6 min | 3 | 复用立面配方 |
| East | 3 | 4.0 min | 1 | |
| West | 2 | 0.7 min | 1 | 配方完全成型 |

**读法**：第一张图那 30 分钟、30 次 PIL 绝大部分在**试错、把 CV 配方调出来**；配方一旦成型，后 5 张直接复用、越来越快（West 仅 0.7 min）。**"慢"的成本几乎全在"发明配方"这一次性开销上**——这正是固化工具箱能省掉的部分。

### 1.3 方法论结论
- **精度来自「量」不来自「看」**：0.0m 偏移 = 像素测量的产物，不是 VLM 感知的产物。这与 0-5 铁律「LLM 感知、代码算几何」**同向**——只不过这次是模型自发用代码算，而非脚手架提供的确定性代码算。
- **过度分割被裁图 + 投影抑制**：裁图放大 + 灰度投影让"窗 jamb / 尺寸 tick 不是贯穿墙"变得可判（历史病根被这套技法直接压住）。
- **"发明配方"是一次性大头**：固化 = 把这次性成本从每个强模型 run 里省掉，且给弱模型免费用。

**⚠️ 两个未排除的混杂（结论要打折）**：① reading 用的是 **Sonnet 5**（`claude-sonnet-5`），历史 sm21 实验全是 Sonnet 4.6——"5 更倾向于写代码去量" vs "5 感知更强"未隔离（4.6 也会写 PIL/scipy）；② **n=1** 单次抽样。∴ 下一步计划含「Sonnet 4.6 再测一次干净流程」+ 多抽验方差（见 §7）。

---

## 2. 核心洞察：经典 CV 工具箱当 VLM 的"看图小工具"

**对立轴不是 "VLM vs CV"，而是 "VLM 肉眼估像素（弱）" vs "VLM 调经典 CV 工具量像素（强）"**：对 VLM，肉眼像素
定位是弱项；但 VLM 一旦有代码工具，会自己把经典 CV 写出来并拿到像素级精度（本次实证）。像素忠实的正解是经典 CV，
不是把 VLM 逼成肉眼像素尺。

**∴ 提升杠杆 = 给 reading 阶段一套显式、经典（非训练）CV 工具箱**，模型作为工具调用：

| 工具 | 作用 | 这次模型的临时实现 |
|---|---|---|
| **crop / zoom** | 局部放大躲过满图杂物 | PIL `crop` |
| **wall-line profiler** | 灰度掩膜 + 行/列投影 → 候选墙线像素位置 | numpy 掩膜 + `sum(axis)` 取峰 |
| **px↔m calibrator** | 用尺寸锚（overall/链）标定比例尺 + 换算 | 手写 15000mm↔图宽 |
| **window/opening detector** | 立面连通域 → 窗框 bbox + 计数 | `scipy.ndimage.label` |
| **（补充）OCR** | 尺寸数字值源，降 misread、兜"碰巧闭合" | 未用（VLM 自读） |

**为什么是经典 CV 不是训练模型**（正好绕开用户当初 defer CV 的顾虑「自训泛化差」）：阈值 / 投影 / 连通域 / Hough
都是**古典算法**，跨画风相对稳、零训练、可审、确定性。**caveat**：灰度阈值吃的是 sm21 这种**干净 CAD 导出 PNG**；
扫描件 / 手绘 / 噪声图上阈值要更鲁棒（形态学去噪、自适应阈值），得单独处理——工具箱要分「干净矢量图（现在能做）」
与「噪声图（后续）」两档鲁棒性。

**与 0-5 铁律的关系**：模型自发在黑箱子代理里做 ad-hoc CV，**强大但非确定性、不可复现、不可审**（每 run 重发明、
配方随机）。把它变成脚手架里的**一等工具**（确定性、留痕）才既拿精度又守铁律。这就是 Phase B / Phase C 要做的正事。

---

## 3. 诊断：reading 为什么曾变弱（三方收敛，已核验）

> 折自原 proposal §1。这是 Phase A/B/C 路线的根因地基。

**实测**（2026-06-30，冷启 Sonnet 4.6 n=2，恢复后脚手架）：墙均 9/9，但过度分割 run 方差主导（r1=0 / r2=+4）。
attempt 级证据：内墙 x 坐标**全来自尺寸链累加算术**、像素 `anchor` 字段空着、r2 伪墙落窗 jamb 处 `prov=seen`。

**根因（精确）**：
1. 尺寸链在每个构件处分段；VLM 锚链段界画墙，光看链分不清"断点是隔墙还是窗 jamb"→ 窗的尺寸被当"可能有墙"。
2. 判别"是不是墙"的证据是**视觉的**（真隔墙画贯穿进深的墙线），但 VLM 在**用数字推理**；不确定就让链幻觉墙。
3. **架构**：reading 曾做累加算术 = **违反 0-5「LLM 感知、代码算几何」**。→ 正解见 §2（把"算"交给 CV 工具/代码）。

**病根 = prose↔gate 执行落差**：旧 phase1 reading 更强（9/9·14/15），当前 gate① 对"无 dimensions / 无 P1a chain /
legacy provenance"曾**不设硬门**，所以 reading 弱仍结构性通过、correction 在**救场**而非规范化，"pipeline 绿"掩盖
"reading 弱"。**Codex 架构回归审的 4 条 BLOCKER 已逐条核验属实**（dimensions 可空被当 clean / chain closure 不
强制〔代码已存在被静默跳过〕/ facade E/W sign 冲突〔facade.py 0 调用点=未接线 dead code〕/ gate1 全绿 reading 仍错）。

**"可恢复性规则"（档位判据）**：对每个子任务问"correction/几何阶段能否从此模型的错误恢复？" 能恢复 → 弱模型/VLM 够；
不能恢复 → 才值得上更可靠抽取器。落地：粗墙/洞口结构 = **可恢复**（correction 设计就吸收缝/偏移/拓扑噪声）→ VLM +
脚手架；**尺寸 = 唯一不可恢复**（读错下游无信息还原）。

**OCR 闭合反转（关键）**：尺寸不可恢复**不是二元**——破坏链闭合的 misread = **可检测**（闭合 fail→reread）；只有
"碰巧仍闭合"才真不可恢复。`dimension_chain_closure` 已写好、曾因 chain_id optional 被跳过。∴ **第一刀不是上 OCR，
是强制 chain_id + 激活闭合门**（用已有代码把 silent misread 变 loud），OCR 留作并行降率（Phase C）。

---

## 4. reading 提升路线（Phase A ✅ 已落地 / B / C）

### Phase A（✅ 已落地，2026-06-30 `6.30_ReadingEvidenceGateHardening` + `A8_CorrectionEvidenceRouting`）
证据完整性门硬化：让 reading 弱**可见**、尺寸错**变响**、"pipeline 绿"不再掩盖"reading 弱"。全是 gate/validator/报告/
测试，**reading↔correction 契约未动、基本不重录**。逐项（已落地记录）：
- **A1 尺寸链闭合**：dimensioned view 必须有 dimensions；闭合按 `(chain_id,axis)` 分组，每组须 overall/baseline + ≥1
  ordered segment；无 chain_id / 不完整 / 不闭合 → evidence 债。局限：闭合抓多数非全部（自洽错读仍闭合）→ 与 A6/A9 合力。
- **A2 `dimension_derived ⇒ dimension_refs 非空且可解析**（纯门、不 mutate）。
- **A3 gate 四信号 + run_profile plumbing**：`syntax-valid / evidence-clean / J0 semantic-clean / pipeline-recovered`；
  新 `RunPolicy.run_profile`（exploratory|dev|golden|regression，不复用 capability_profile）一路串到报告；evidence 机器可读 allowlist。
- **A4 dimensioned fixture ⇒ `dimensions[]` 非空 + 新 reading 带 P1a 字段**（case 元数据加"该图有尺寸标注"声明）。
- **A5 provenance coverage 升级**：legacy/partial provenance 在 golden/regression → flag/block。
- **A6 window-jamb 交叉门**（缩到 per-view 真有的证据：窗 stroke 几何 / 墙轴线 / wall-join / 链累加位；去掉 wall_fill/thickness）。
- **A7 legacy 原始字段存在性留痕**（`raw_has_dimensions/raw_has_uncaptured/legacy_migrated`，让"default 成 clean"≠"真 clean"）。
- **A8（跟批已落地）correction 证据债前后卡门**：`evidence_preflight.py`（`EvidenceDebt` 确定性投影 + run_profile 重判）+
  correction prompt 注入债块（债元素别编坐标、落 `conflicts` 不碰 `unsupported`）+ correction 后 `check_evidence_debt_coverage`
  覆盖门。**本质=给 correction 软环节装仪表+前后确定性卡门，不修 reading、不修伪墙**（修弱那刀在 Phase B）。
- **A10 E/W sign**：以 A1（East+1/West−1，gt-validated）为准；facade.py 常量已翻正（未接线，翻安全，守 [[derive-facade-frame-unwired-ew-sign-trap]]）。
- **flag vs block**：syntax-invalid → 永久 block；evidence-incomplete → exploratory/dev = flag（可见、喂 J0+reread、run 续）/ golden·regression = block；legacy_migrated 祖父化（不打 block 现有 legacy golden）。

> **已知精化点**：本次 run 的 8 个 `dimension_chain_closure` flag 是 Phase A 门在**完美 reading 上误报**（C_top 15.0 vs
> 分段和 14.76 = 内隔墙厚未标注；C_bottom/C_right 无 overall 只有分段）。证据门无法区分"诚实的无-overall/墙厚残差"与
> "真识图债" → 把 run 自动状态误判成 `reading_evidence_debt`。宜并 Phase B 双通道时给残差正规通道解。

### Phase B（后续·根治）：双通道 reading + 算术下沉代码
- **双通道 schema**：每元素带 `visual{anchor_px|null, relative, confidence}` + `metric{dimension_refs, raw_segments,
  confidence}` + provenance；**reading 不吐最终米制坐标**。
- **确定性尺寸约束求解器**算几何（"尺寸驱动重建"——施工图里尺寸才是真值）；再拓扑用 Shapely `polygonize`（别自写平面剖分）。
- correction 分**确定性**（吸附闭合/共面/规整）vs **语义**（"窗属哪个房间"）——前者纯几何、后者才动 LLM/规则。
- 在此**接线 `derive_facade_frame` + 锁 E/W sign**（gt 校验后再改，守 [[derive-facade-frame-unwired-ew-sign-trap]]）= 确定性 local→world 可审变换 + 每 run persist facade transform 表。
- **本次样本的补强（关键）**：`anchor_px` 通道**不该空着让 VLM 用尺寸链累加算**（历史过度分割根因），而应由 **§2 的
  wall-line profiler 工具**把像素 anchor 填实——这次模型自发做了，Phase B 要把它变成脚手架提供的确定性工具。
  **∴ Phase B 的"算术下沉"具体形态 = §2 CV 工具箱**：不是纯符号求解，而是「CV 量像素 anchor + 尺寸链标定 + 约束求解」。
- 好处：算术-致-过度分割从源头消失、双通道给 correction 仲裁、reading 任务变小利于弱/开源 VLM、接上"plan-local→world 一等变换"。
- 代价：新 schema + 求解器 + correction 改 + **重录 baseline**；走 Claude 方案→审→执行。

### Phase C（远期·并行 R&D）：OCR + CV 前端
- **C1 OCR**（PaddleOCR，中文图开箱不训练）当尺寸数字值源——降 misread、兜"碰巧仍闭合"的残余不可恢复错。原决策：
  闭合门优先、OCR 暂不起；本次样本显示 VLM 自读尺寸够用，OCR 优先级仍可后置。
- **C2 CV 前端**（仅泛化逼迫时）：起手式 = DXF→(PNG, 逐层掩膜) 数据工厂（复用 CAD→gt 基建，免人工标注）→ 经典 CV
  （LSD/Hough 抽墙线 + 形态学 wall_fill + 线宽剥尺寸层 + 比例尺=尺寸文字↔延伸线像素距）→ 必要时训检测器（YOLO/分割，
  现成 CubiCasa5K/HEAT 有域差当对照）。**用户判断：自训泛化太差（reading 要吃各种风格图），先不上 CV**。
- **本次样本的意义**：§2 工具箱就是 C2 的**轻量前置版**——先把这次模型手写的 crop/投影/连通域/标定做成工具，比一步
  到位建完整 CV 前端**更快见效、风险更低、且保 VLM 在环做语义判断**（比现状更贴 0-5 北极星：CV 出确定性视觉通道、VLM 退化成语义活）。

---

## 5. 从这次样本能固化进脚手架的具体项（候选，待设计）

1. **CV 工具箱四件套**（§2 表）：crop / wall-line profiler / px↔m calibrator / window connected-components，做成 reading 阶段可调的确定性脚本或函数（干净矢量图档先行）。
2. **配方即工具**：把"灰度阈值 60-230 隔离墙体、行列投影取峰、总尺寸标定 px/m"写成默认 recipe，省掉第一张图的 30 分钟发明成本。
3. **anchor_px 强制填实**（接 Phase B 双通道）：禁止内墙 x 纯尺寸链累加、要求像素 anchor 由 profiler 工具产出。
4. **裁图纪律工具化**：把"满图先裁带放大再判隔墙"从 prose 纪律升级为工具默认动作（压过度分割）。
5. **鲁棒性分档**：干净 CAD PNG（阈值 CV 够）vs 噪声/扫描/手绘（形态学 + 自适应阈值），工具箱声明适用档。

> **✅ 工具箱 C0+C1 已落地（2026-07-06，Fable5 方案→Codex 审 APPROVE-WITH-CHANGES→Codex 执行→Fable5 复核，496 绿，commit `e3ec9ae`）**：
> `src/agent/reading/cv_toolbox/`（6 工具：crop_zoom / wall_line_profiler / px_m_calibrator / window_cc_detector /
> storey_line_profiler / overlay_logger，确定性零 RNG）+ CLI `scripts/tool_scripts/cv_probe.py` + sidecar
> `0_reading/cv_evidence/`（`cv_schema="1"`·append-only·crop_chain 可逆·**预留 Phase B anchor_px/visual/metric 槽位**）
> + skill 文档 [0_reading/cv_toolbox.md](../../skills/intake_pipeline/0_reading/cv_toolbox.md) + kickoff 指针；
> gt-discipline 扫描扩到 `src/agent/reading/**`+CLI。上表候选 **1/2/4 即此批**；**3**（anchor_px 强制）归 Phase B、
> **5**（鲁棒性分档）归 C5,均未做。审轨 `logs/reviews/{request,verdict,execution}/2026-07-06_cv_toolbox_c0c1_*`。
> **✅ 北极星判决性实验已判（2026-07-07）= 阳性满分**：Haiku 4.5+工具箱在 sm21 判卷与 Sonnet 5 基线逐项相同
> （9/9·7/7·15/15·0.0m）vs 无工具箱对照全崩；失败模式从"看错"（感知）迁移为"量了不筛"（流程纪律可托）。
> 三限定（指令要求使用/pilot 打回一轮/prompt 级隔离）+ sm24 非方形探针（无标注构件=标定后像素直测正解、
> schema 写作=弱 VLM 稳定短板→Phase B 证据）+ **E 效率批**（纪律固化进 skill / prescan 宏工具〔有界线段·中性
> 命名·profile 声明〕/ 预扫前置化 SOP，517 绿）详 `logs/experiments/2026-07-07_haiku_cv_retest/`。
> §7 "弱 VLM 可用性"已验证；"OCR 时机"数据驱动维持 Phase C（触发器=跨模型标定/读数失败即提级,先 advisory）。
> **下一步 = GPT-5.4-mini 交叉测试**（迁移性验证，交接单在实验目录 HANDOFF_gpt54mini_crosstest.md）。

---

## 6. 决策记录（用户已拍）

1. **E/W 约定**：以 A1（East+1/West−1，gt-validated）为准；facade.py 常量已翻正 + 有 gt 锚定 E/W sign 测试；未接线，接核前再对 gt 校验。
2. **OCR 时机**：闭合门优先，**OCR 暂不起**（Phase C）。
3. **flag vs block**：syntax→永久 block；evidence→exploratory=flag / golden=block（Claude 裁定、用户授权）。
4. **CV 前端**：用户定**先不上自训 CV**（泛化差、reading 要吃各风格图）；但**经典 CV 工具箱**（非训练）不在此禁令内，是 Phase B 的推荐形态。
5. **文档职责**（2026-07-03）：proposal=设想/未动工；动工后进 capability；reading 提升统一本文，不两处并存。

---

## 7. 未决 / 待验（诚实清单）

- **Sonnet 4.6 对照**：同图干净流程再跑 4.6，隔离"模型行为（倾向写 CV）" vs "感知强度"。（下一步计划已含）
- **方差**：n=1 → 多抽几次 Sonnet 5 看 15/15 是否稳定，还是这次运气好。
- **弱 VLM 可用性**：CV 工具箱能否让弱/开源 VLM（北极星目标）也读到接近的精度——需实测。
- **噪声图鲁棒性**：灰度阈值在非干净图上的失效边界。
- **Phase A 误报精化**：证据门在完美 reading 上把无-overall/墙厚残差误判成 debt（本 run 已见），并 Phase B 解。

---

_2026-07-02 立、2026-07-03 折入原 `proposals/reading_evolution_dual_channel_cv.md`（该 proposal 已删，内容全在本文）。
缘起 = run_2026-07-02_sonnet_flow_e2e 高质量 reading 样本 forensics（用户观察"模型一直裁小图仔细看"+"第一张特别久、
批量快" → transcript 坐实 = 模型自发经典 CV）。本文 = reading 提升的唯一管理文档（诊断/路线/决策/方法论/待办一处）。_

---

## 8. 环节的控制边界 + 成绩归因（原 CLAUDE.md §1.5 不变量 #7 正文，2026-08-18 搬入）

> **⛔ 搬家理由（必须先读）**：本节这一整包（`reading-agent` / autonomous↔controlled lane / 成绩归因 / 隔离档位）
> 已由用户 **2026-08-16 当面拍板打包延后、全部归 reading 专项**，**⛔ 不是本批的准入门**。
> orchestrator 曾因把本节正文当现行口径读，**连续三次**得出「07-07 模式违规、须先实现 `reading-agent`」的错误结论
> （08-16 两次 + 08-17 一次）⇒ 故从根文件 CLAUDE.md 迁出，只在此处保留全文备查。
> **当前批次的现行口径 = [CLAUDE.md §2](../CLAUDE.md) 的 reading banner**：
> 按 **07-07 模式**（orchestrator 亲自审 pilot、多轮同一会话）直接跑，⛔ 不停在治理口径上。
> 仍然生效的只有开头那条硬边界：**端到端 orchestrator 对某环节内部只能启动与接收**。

7. **环节的控制边界 + 成绩归因（2026-07-31 立 → 08-01 校准 → ⭐2026-08-02 用户重订，
   [调研报告 §0.4/§0.5](../logs/reviews/verdict/2026-08-02_reading_regression_controller_cv_investigation.md) 为唯一口径，
   下述 07-31/08-01 两版判据凡与本版冲突处**全部作废**）**：
   本条现在管两件事——**谁不许伸手（端到端主控）** 和 **成绩怎么记账（provenance）**；
   它**不再**禁止「环节内部存在更强 agent 或针对性反馈」。
   - **⛔ 端到端主控（本 Agent）对某环节内部：只能启动与接收。**
     ✅ 可以：创建 job / 传入**冻结的** case bundle + profile / 等待 / 接收 `status + output + evidence manifest`；
     dev 期编排（建工作区 / spawn / merge / 跑确定性工具 / 决定跑什么）仍合法；**主控兼任 judge 仍合法**。
     ⛔ 不可以：写自由文本 directive / feedback；**看了图之后指导 worker**；替它挑 CV 参数或返工区域；
     操作环节内部会话；**接触 gt 之后把任何结论送回同一个 run**。
   - **✅ 环节内部允许有自己的 controller（08-02 新增许可）**：reading 可以配置属于
     `ReadingService` 内部的控制 agent 去指挥弱 VLM，条件是——
     ① 与端到端主控**彻底解耦**（外部看仍是 reading 自己走完输入→输出）；
     ② **档位不高**（DeepSeek v4Flash 级或以下、thinking off、结构化输出、短上下文）；
     ③ **有界**：最多「一次任务计划 + 一次局部返工」，不重抽整栋，**不得直接写最终坐标**
     （最终 stroke 必须来自 worker + 工具证据）；④ 它是**权衡方案不是永久架构**，后续要代码化 / 降档 / 撤除。
   - **⛔ 成绩记账 = 两条正式 lane + 一个 dev 期职能（⭐2026-08-02 晚用户当面更正，
     此前记成「三条并列 lane」**是错的**）**（配 `reading_mode` provenance 块：
     `reading-agent` / `reading-worker-agent` 各自模型、`reading-agent` 是否看图、返工轮次、
     工具箱版本、隔离档）：
     - **autonomous**（目标 VLM + 冻结工具箱，**零 `reading-agent`**）= **北极星、长期目标**；
     - **controlled**（+ `reading-agent`）= **当前批次的验收 lane**。
     **controlled 完全算真实工程成功**，但**不得记成「弱模型独立满分」**；
     autonomous lane 必须一直保留，否则不知道离「本地开源 VLM 自主完成」还有多远。
     - **另有一个 dev 期开发者职能（不是 lane、不产生正式成绩）**：允许**最强模型观察 reading
       （乃至其他环节）的内部过程**，提炼方法论 / 搓适配工具 / 改进流程，**作为成果资产纳入项目开发本身**。
       角色归属用户**倾向 orchestrator 兼任**（可再议）。**四条铁律**：
       ⛔ 不能给项目生产本身提供**信息** · ✅ 可以提供思路 / 方法 / 工具 ·
       ⛔ 这种模式下的**跑测不作为正式成绩** · ⛔ **一个 case 的收官验收必须脱离该角色完成**
       （验收时跑的是已固化工序 + 已冻结工具箱，该角色不在场）。
     - **⭐ 本批次目标口径（用户 08-02 晚更正）**：**不是**「autonomous 拿到好 reading」——那是北极星；
       **本批 = 在 `reading-agent` 在场的形态下，sm21 与 sm24 两个 case 都拿到接近满分**，
       本质是**先恢复到「Haiku 做 sm21/sm24 满分」那个状态**（那时本就有高档模型部分介入），
       只是把当时 orchestrator 的**临场介入固化成 `reading-agent` + 与 orchestrator 隔离 + 降档到 Flash**。
       ⇒ **不是提高分数，是用合规形态重新达到一次。** 拿到之后再尝试撤掉 `reading-agent` 验证 autonomous。
   - **⛔ 隔离原则改写（08-02）**：**严格限制可见信息与写出边界，不限制在合法输入上采用何种计算方法。**
     要防的是漏题与污染（gt / baseline / judge / 其他 run / 历史答案 / 网络外传），
     **不是**模型用了哪种算法 —— 按命令形态封杀通用 CV 编程（`python -c`、临时脚本）属于**能力封口**，
     它封掉的正是 07-02 Sonnet 那条成功路径。
   - **judge 出口不变**：判定不过 ⇒ **整轮盲重抽、零信息**（相当于另外做一次）；
     judge **不得**告诉执行环节「哪里错了、该怎么改」。（注意区分：**环节自己的 controller 做局部返工是允许的**，
     受 judge 约束的是**跨环节的评判者**。）
   **⚠️ 已排查完的违规点（2026-08-01 全面排查，[审计报告](../logs/experiments/2026-08-01_controller_in_production_audit/README.md)）**：
   ① **pilot 停等 review + `feedback.md` 续作通道**，且「停下等审阅」**写在产品 skill 库
      `session_kickoff.md` 里**（不是 dev 脚手架）⇒ 读图器被自己的启动文件命令停下等人；
      **07-07 的 8/8 正由此而来** ⇒ 该成绩非无监督基线。**08-01 已改**（自检后继续，无 review 点）；
   ② **per-run directive**（198 行，主控看着上轮失败当场写）⇒ 待拆分：通用纪律沉淀进 standing 文档 /
      针对上轮错法的删除。**⚠️ 与补门成对做**——其 §2、§4.7 实为两条缺失 gate① 检查的替代品，只删不补即退化；
   ③ **预扫参数由主控临时挑**（跑预扫本身合法，参数必须是随产品发布的固定档）；
   ④ **污染闸门 `check_feedback_text` 是纯词法**，挡不住裸坐标与具体错处 ⇒ 上述通道无实质约束。
   **⚠️ 07-31 原文列的另两条已作废**（v1 判据过宽所致）：~~识图段无代码执行器~~、~~judge② 由主控担任~~
   —— 按 08-01 校准判据**均属合法 dev 编排**。
   **⭐ 08-02 重要改判**：上面 ①–④ 违的是**「端到端主控伸手」**这一条，**仍然成立**；
   但**同样的动作若由 `ReadingService` 内部的 controller 做（解耦 + 低档 + 有界 + 如实分账），现在是允许的**。
   即：**要禁的从来是「谁在做」和「记成谁的成绩」，不是「reading 内部有没有控制」。**
   详 [08-02 调研报告](../logs/reviews/verdict/2026-08-02_reading_regression_controller_cv_investigation.md)
   · [08-01 排查报告](../logs/experiments/2026-08-01_controller_in_production_audit/README.md)
   · [07-31 缘起](../logs/experiments/2026-07-31_sm24_e2e_retry/SUPERVISION_CONTAMINATION.md)。

---

## 9. ⭐ reading 专项收件箱（2026-08-19 用户拍板打包进来的三项）

> **用户当日口径**：「根治打包收进 reading 专项。现在就是在最新基座上确认移植好，两项验收：
> GPT-5.4-mini 和 Sonnet 在 sm21、sm24 上都出好 reading。至于后面怎么让这套机制变成强制、
> 让 haiku 水平回归，都收进 reading 专项。」
> ⇒ 下列三项**一律不进本批验收的关键路径**，⛔ 也不得再当拍板项反复上报。

### 9.1 把「量而非看」变成强制（根治）

**病灶（2026-08-19 实测定位，非推理）**：`px_m_calibrator` 是纯除法器，**入参 `px_a`/`px_b` 收自由数字**
—— 没有任何东西要求那两个像素来自工具输出。⇒ **眼估的数字进去，出来一份带侧车、残差、
`confidence: high` 的「测量结果」。** 门检查的是算术自洽，不是输入来路。

**证据链**：
- 07-07 满分那次的最终标定锚 = `425.4 / 1815.9`（**亚像素**）+ 17 次 `crop_zoom`（2×–8×）
  ⇒ 机制是**放大后再看、再除以放大倍数**，不是「工具测出来的」。
- 2026-08-19 Sonnet 同形复现：锚 `273.56 / 1172.48`，16 次 `crop_zoom`，标定误差 **0.15%**。
- 同日 Haiku 在**同一份 staging、同一份 prompt**下：`crop_zoom` **0** 次，锚 `280 / 1235`（整数），
  标定误差 **6.4%**，墙 0/4。
- 感知探针（合成图，只有四条线，问「按图宽比例」⇒ 帧无关）：Haiku 两次重复稳定偏差，
  最大 **26 个百分点**。⇒ **眼估准不了，且不是随机噪声。**

**修法方向（三条，均可机器强制）**：
1. **标定锚只收 `candidate_id`**，必须指向某个工具输出的候选。预扫本来就产 **234 个 `tick_candidate`**
   （亚像素，如 `493.1994`）—— 部件早就有，只是从没要求标定必须用它。
2. **两轴必须一次调用给全**（堵 F-63：拆成两次单轴 ⇒ 跨轴门无比对对象，08-19 Haiku 又活体复现一次，
   它自己写下「X 59.33 / Y 60.63 差 3%，取平均 60」）。
3. **米制换算归代码**，读图器只写像素锚点 + 证据引用。

### 9.2 让 Haiku（弱模型）水平回归

⛔ **未查明**：今天的 Haiku 不走「放大回读」那条路，而 07-07 的 Haiku 走过。
已排掉：当前栈（历史树上同样坏）· 帧错位（修好后仍 0/4）· 指令跟随与算术
（探针②：告知「参照长度是 12.0 不是 15.0」⇒ 一次改对，`px_per_m` 80→100 全部重算正确）·
配方本身（同一份 staging 换 Sonnet 即 4/4）。
**未分开**：模型权重/服务端 · Claude Code CLI/runtime · 图像投递。分开它们的唯一干净办法 =
**绕开 Claude Code 直接打 Anthropic API**（未做）。

### 9.3 图像分辨率 / 帧对齐（F-51 的取舍）

**2026-08-19 用户拍板：⛔ 先不考虑降分辨率省成本，直接读原图。**
⇒ 已落地：`DEFAULT_VISION_RESIZE_TIER = "none"`（staging 原样交付，逐字节不动），
`--vision-resize-tier {none,standard,high_res}` 补上入口（此前**无任何入口**，是 08-17 复审记的那处 MINOR）。
**留给专项的问题**：Anthropic 侧对 pre-4.7 模型仍会内部缩到 `standard`（1f: 2133→1377），
⇒ 对 Haiku 一代，「读图器看到的帧 ≠ 工具量的帧」这个错位**只要不预缩就还在**。
F-51 当初正是为消除它而建。**要不要为弱模型重新开启预缩、还是靠 9.1 让帧错位不再重要 —— 归本专项。**
（Sonnet 5 = 4.7+ 一代，`high_res` 对本案图纸是空操作 ⇒ 读原图即天然对齐；codex/GPT 不经该链路。）

### 9.4 ⛔ 本批验收的准入门（不属于本专项，但卡在这里）

**sm24 验收前必须先解**：v3 typed 判卷对 null `scale_origin` 判 `plan_frame_unavailable` + `retain_as_miss`
⇒ **整条 plan 通道（`plan_segments` + `plan_openings`）按 miss 计、与 `run_profile` 无关、永不报错**
⇒ 「拿不准留 null」会把 plan 通道**合法地考成结构性零分**。只跑 sm21 走 legacy 判卷、零影响。
**作者不得是 orchestrator**（碰判卷 = 工程档，§0.2）。

### 9.5 ⭐ 2026-08-19 追加：好 reading 有**两条**不同的路，不是一条

回查 07-08 那份 9/9 的证据后，原先「07-07 的机制 = 放大回读」这个单一叙事**不完整**：

| 路线 | 实例 | 机制 | 1f 工具调用 |
|---|---|---|---|
| **A · 像素标定** | 07-07 haiku · **2026-08-19 sonnet** | `crop_zoom` 放大 2–8× → 读回 tick → 除以倍数 ⇒ **亚像素锚** → 标定 → 换算 | 17 / 16 次 crop_zoom |
| **B · 尺寸链算术** | **07-08 gpt-5.4-mini** | 逐条转录尺寸链（32 条）→ **直接做算术**，几乎不用像素 | 仅 4 次；**1f 上零次 `px_m_calibrator`** |

**证据**：07-08 那份 1f 产物 10 条墙**全 `provenance: seen`、`dimension_refs` 0/10**，
全六图仅 1 次 `px_m_calibrator`，而 1f 墙判 **4/4**。
⇒ 对**满标注的矩形平面**，路线 B 是精确的，且比 A 便宜得多。

**⇒ 对修法的影响（重要）**：§9.1 那条「标定锚只收 `candidate_id`」**只堵住路线 A 的眼估入口**。
路线 B 的风险在别处——**转录数字被改**（H2 那轮 Haiku 把北链 `1240`→`1480` 凑闭合就是这个）。
⇒ **两条路要各配一道确定性门**：
- A：锚点必须来自工具候选（+ 两轴一次给全）
- B：**转录值与图上 OCR 对账 + 链闭合必须由代码校验**，⛔ 不许改转录数去凑

### 9.6 ⚠️ 预扫（prescan）：被消费，但在产物里不可见

- `723b0f9`（07-07）**没有** prescan；`ebddada`（07-08）**有**，且 07-08 那次是 orchestrator **前置**拷进 staging 的。
- **两次实测都显示：读图器大量读了预扫候选，但产物里零引用。**
  2026-08-19 P1 臂 transcript 里 `prescan` 出现 **676 次**，最终产物 `candidate_id` 引用 **0**；
  07-08 同样为 0。
- ⇒ **「用没用预扫」在产物上不可观测，只有 transcript 分得开** —— 同族
  [[absence-conflates-causes-in-observables]]。
- **现状**：实现仍在（`cv_probe.py` 有 `prescan-plan`/`prescan-elevation`），
  但 **08-15 已从 `ALLOWED_TOOLS` 撤除** ⇒ **读图器自己调不到**（实测报 `unsupported cv_probe tool`），
  只能由 orchestrator 前置。
- **2026-08-19 已从当前工作环境撤出 —— ⛔ 是【延后】不是【放弃】**（用户原话：
  「prescan 这条路不是说放弃了，是统一收到 reading 专项到时候一起考虑，这些方案和代码也不要丢了呀」／
  「从现在的工作环境撤掉，不是说就永远不要了」）。
  撤出的理由是终结 08-15→08-19 的**半死状态**（实现在、授权撤了 ⇒ 读图器调不到），
  那是「放回 / 保持前置 / 撤出」三者里最差的一个。
  **代码、测试、恢复步骤完整留档**：[`prescan_snapshot/`](prescan_snapshot/RESTORE.md)
  （四份文件，与 `0cfa289` 逐字节相同，附恢复时必须一并处理的六处）。
- **⏸ 待本专项拍的决策项**：① 放回授权表让读图器自取 ② 保持 orchestrator 前置（= 07-08 原样）③ 继续搁置。
- **⭐ 与 §9.1 合并考虑，⛔ 不要分开决策**：预扫对 1f 产出 **234 个 `tick_candidate`**（亚像素），
  而 §9.1 的根治修法「标定锚只收 `candidate_id`」**正需要一个机器检出的 tick 来源**
  —— prescan 的恢复与那条修法很可能是同一件事。


---

## 10. ⭐⭐⭐ 2026-08-20 收件：满分产物里的「不干净」= 一处判卷看不见的几何缺陷

> **来源**：用户 2026-08-20 肉眼观察——「虽然 sonnet 这次 reading 出来是满分，但是读出来的图不是那么干净，
> 跟之前的好 reading 比多了很多乱七八糟的东西，之前读出来的都很干净」。
> orchestrator 据此逐笔画对账，**把这个视觉印象坐实成了一个具体缺陷**。

### 10.1 现象不在笔画层

S1（08-20 Sonnet 满分）与 #2（07-07 haiku）的**笔画清单完全相同**：
六张图的笔画数、笔种、几何类型逐项一致（1f 10 墙 7 窗 · 2f 10 墙 8 窗 · 立面 4/7/9/3）。
⇒ **不是多画了东西。**

### 10.2 病灶：墙与窗被放进了两个不同的基准

| | 外墙坐标 | 窗坐标 |
|---|---|---|
| **#2 07-07 haiku** | `0.0` / `15.0` / `8.0`（标称整数） | `y=[7.76, 8.0]` · `x=[14.76, 15.0]` |
| **#7 08-20 Sonnet** | **`0.11` / `0.12` / `14.89` / `7.89`**（内缩 ≈ 半个墙厚） | `y=[7.76, **8.0**]` · `x=[14.76, **15.0**]`（**未跟随内缩**）|

⇒ **墙落在实测像素中心线，窗落在标称尺寸链位置，两者差 ≈0.11–0.12 m。**

**视觉后果**（= 用户看到的「乱」）：窗比墙探出 0.11 m ⇒ 蓝色窗条超出墙线、
东窗探出部分在渲染里表现为右边缘的一条绿线、外圈因「墙线 + 探出的窗边」而呈双线。
⇒ **「不干净」不是审美问题，是几何不一致的视觉显影。**

### 10.3 ⛔ 为什么满分掩盖了它 —— 判卷压根不看外墙

`gt/sm21_anchor/gt.json` 的 `floors[*]` **只有 `zones`，没有 `walls`**；
判卷比对的墙段是**由分区边界派生的内隔墙**（1f 只判 4 道：x=5 · x=10 · y=3 · y=5），
外轮廓只以 `footprint: {W_m: 15.0, D_m: 8.0}` 存在，**其坐标从不被逐段比对**。

⇒ **外圈那 0.11–0.12 m 的内缩在判卷上零代价。** 满分 9/9 · 7/7 · 0.0 m **同时成立**且**不矛盾**。

⇒ ⭐ **同族 [[ep-zero-severe-is-not-physical-correctness]] / [[proxy-mistaken-for-the-thing]]**：
**分数是代理量，不是「图读对了」本身。** 本例是该判据在 reading 侧的第一份直接证据 ——
**一个满分产物里藏着一处系统性的外轮廓偏移，而现有全部自动门无一能看见它；
发现它的是用户肉眼。**

### 10.4 收件登记（本专项待处理，⛔ 非本批阻塞项）

| 项 | 内容 |
|---|---|
| **R-1** | **判卷对外轮廓是瞎的**。要不要给 gt 加外墙段、或给 footprint 加逐边坐标比对？（注意：这会改判卷尺，属工程档，且会影响历史成绩可比性）|
| **R-2** | **墙/窗基准不一致**是读图器侧的真缺陷。它与「尺寸基准 + 墙厚方向」专项（`proposals/dimension_basis_and_wall_thickness_direction.md` 的 `zone_frame: axis\|exterior`）是**同一个题**，⛔ 应合并决策，不要分头修 |
| **R-3** | 07-07 用标称整数、S1 用实测中心线 —— **哪一个才是本项目要的口径**，尚未定案。定不下来，「干净」就没有判据 |
| **R-4** | ⭐ **方法论**：本条是用户肉眼抓到、全部自动门漏掉的。⇒ **每一批 reading 收工时，至少肉眼看一遍渲染图**，别只看分数。成本几秒，今天的收益是一个系统性缺陷 |

---

## 11. ⭐⭐⭐ 2026-09-03 用户拍板：**07-07 那两根「拐杖」= 干扰，⛔ 现在不恢复**

> **用户原话**：「这个登记就行，**先不要恢复**，因为理论上还是需要**脱离强模型指导**，
> 我们**按新模式来试**，弱模型**实在脱离不了**再考虑恢复这种干扰**以及怎么做**这种干扰。」

### 11.1 当年到底发生了什么（事实，⛔ 非印象）

2026-07-09 的 Haiku 对比重跑 **4 轮 pilot 全不达标、预算用尽止损**
（详档 [`logs/experiments/2026-07-09_prescan_narrowing/HAIKU_RETEST_LOG.md`](../../logs/experiments/2026-07-09_prescan_narrowing/HAIKU_RETEST_LOG.md)，
里程碑见 [`decision_log.md`](../../decision_log.md) 2026-07-09 条）。

- ✅ **那轮真正要验的东西成立了**：prescan 收窄本体阳性 —— pilot 阶段 CV 调用从 07-08 的
  **86 次砍到 2–6 次**，reader 消费了 519 行收窄候选表与 `axis_summary`。
- ❌ **但质量没到地板**：r1 零 CV 纯目测 → r2 纪律满分但只描 4 道外墙 →
  r3/r4 **标定系统性锚错**（60 vs 真值 **92 px/m**，疑似一直锚在尺寸文本行而非延伸线 tick）
  + 幻觉走廊短墙 + 窗错位。**行为模式很稳定：每轮只机械满足 feedback 点名项，丢掉其余全部上下文。**
- ⭐ **根因定性（当时最值钱的发现）**：07-07 Haiku 满分靠的**两样东西**，在 07-08 硬隔离协议下**都不在了**：
  1. **per-run 开场指令**（kickoff 变成 manifested 通用文案，**没有 directive 槽**）
  2. **连续交互会话**（改成一次性 `-p` + 无状态全量重 spawn；每轮打回冷启重来 **~0.25M token**，5 会话共烧 **~1.03M**）

### 11.2 三个隔离缺口的今天状态（⛔ 逐条核过代码，非转引）

| # | 缺口 | 状态 |
|---|---|---|
| **#4** | `isolation._copy_prescan` 与 `_assert_rel_allowed` **互斥** ⇒ documented SOP 那条路**从未真实走通、无测试** | ✅ 已修（`1078daa`）|
| **#5** | `feedback.md` 落了 staging，但 **spawn 重启 prompt 与 kickoff 协议都不指向它** ⇒ reader 新会话**不知道自己被打回过** | ✅ 已修（feedback 自动指针）|
| **#6a** | spawn 缺 `--directive` 槽 | ✅ 已修，**且今天仍在**：[`spawn_isolated_reader.py:183`](../../../scripts/tool_scripts/spawn_isolated_reader.py#L183)（带污染检查、落 `staging/directive.md`）|
| **#6b** | **staging 内会话 resume**（= 会话连续性那根拐杖）| ⛔ **从未做**，当时标「后置评估」|

### 11.3 ⛔ 本条的裁定（用户 2026-09-03）

1. ⛔ **现在不恢复这两样。** 它们**不是「无害的拐杖」，是【干扰】** ——
   ⭐ **目标是让 reading 脱离强模型指导**，⛔ 不是让弱模型靠喂 per-run 指令达标。
   （与 [CLAUDE.md §1.5 不变量 #7](../../CLAUDE.md) 一致：orchestrator ⛔ 写自由文本 directive。）
2. ⚠️ **⛔ 主控 2026-09-03 的一句判断已被用户当场纠正**：我说过
   「隔离已改成物理隔绝 ⇒ 这两样跟抄答案无关、可以直接还回去」——
   **那个框架是错的**：隔离只是当年砍掉它们的**顺带理由**，**不是唯一理由**；
   真正的理由是**自主性目标**。⇒ 「不削弱隔离」**证明不了**「应该恢复」。
3. ✅ **先按新模式试**（本批的新 reading/correction 分工 + 新跑测流程）。
4. **触发条件**（⛔ 到条件才重开）：**弱模型按新模式试过、实在脱离不了** ⇒ 那时才讨论两件事，
   ⭐ **而且是两件、不是一件**：① **要不要**恢复这种干扰 ② ⭐ **怎么做**这种干扰
   （⛔ 不是简单还原 07-07 的做法 —— 那会把「成绩归谁」重新搅浑，见 §8 控制边界）。
5. ⭐ **代码现状与本裁定不冲突**：`--directive` 槽**留在代码里**（它本身是能力），
   ⛔ **裁定管的是「新模式下不许用它做强模型指导」**；#6b 保持不做。
