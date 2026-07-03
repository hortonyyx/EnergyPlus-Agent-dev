# 识图（0_reading）提升 —— 统一管理文档（方法论 + 诊断 + 路线 + 决策）

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
> 落地轨迹（Phase A）：`logs/review/2026-06-30_reading_scaffold_restore_validation/`（实测）+
> `logs/review/review/2026-06-30_reading_phase_a_spec_review.md`（Codex 审）。

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

> 这些**都还没落地、待设计**。落地路径 = 走正规提案（Claude 方案→Fable5/Codex 审→执行→复核），并与 Phase B 的双通道
> schema 一并设计（工具箱是双通道 `metric.anchor_px` 通道的产出器）。

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
