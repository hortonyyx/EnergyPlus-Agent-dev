---
name: reading-cv-toolkit-methodology
description: ⛔08-01 核心主张已被用户判为假象、全条降级为历史记录·8/8 是带监督拿到的且被打回两次·好轮平面 19-33 次工具调用(crop_zoom 逐条核验)vs 无监督 1-5 次零 crop_zoom·07-07 两轮均无预扫·⭐病灶=self_check.all_visible_strokes_captured 被诚实填 false 但全仓零消费者(文档无法验证别人遵守自己)·冷水=d2 全填 true 仍 24.8%
metadata:
  node_type: memory
  type: project
  originSessionId: bcf21ce5-7aa5-45b0-85be-25130df219c9
  modified: 2026-08-01T15:01:24.087Z
---

**2026-07-03 从一次高质量 reading 样本反推 reading 提升方法论。** 缘起：`sm21_anchor/run_2026-07-02_sonnet_flow_e2e` 冷启 Sonnet 5 reading 几乎完美（墙9/9·窗15/15·过度分割0·全0.0m 偏移，超 sm21_pre 地板）。用户观察"模型一直裁小图仔细看、第一张特别久、批量快"→ 我查子代理完整 transcript 坐实。整理成 **[capability/reading_improvement_methodology.md](AI_agent/capability/reading_improvement_methodology.md)**（reading 提升方案设计地基，把 Phase B/C 也统一整理进去）。

**核心发现（forensics）**：reading 好不是"Sonnet 5 眼睛更准"，是**模型自发写代码把识图做成一套轻量经典 CV——它在"量"不在"看"**。112 次工具调用（60 Bash 几乎全是 PIL+numpy+scipy）：① PIL crop 裁图放大躲满图杂物 ② 灰度掩膜（R≈G≈B 且 60<v<230）隔离墙体像素 + 行/列投影取峰 = 墙精确像素位置 ③ 总尺寸(15000mm=图宽)标定 px↔m → 9 墙全中 0.0m（肉眼绝无可能，是量出来的）④ scipy 连通域数窗 →15/15。**没用 OCR**（尺寸数字 VLM 自读当标定锚）。时间线：1f 第一张 37 calls/~30min/30 PIL 全在**发明调 CV 配方**（阈值/标定/投影试错），2f→West 复用越来越快（West 0.7min）——"慢"的成本几乎全在一次性发明配方。

**Why 重要**：印证并超越原 reading_evolution 提案 §1「像素忠实的正解是经典 CV、别把 VLM 逼成肉眼像素尺」——对立轴不是"VLM vs CV"而是**"VLM 肉眼估像素(弱) vs VLM 调经典 CV 工具量像素(强)"**。且用的是**古典算法(阈值/投影/连通域)非训练模型**，正好绕开用户当初 defer CV 的"自训泛化差"顾虑。

**How to apply（提升杠杆，待设计落地）**：给 reading 阶段一套**显式经典 CV 工具箱**当"看图小工具"——crop / wall-line profiler(灰度投影) / px↔m calibrator / window connected-components(scipy) / (补充)OCR。好处：① 省掉第一张图 30min 发明配方 ② **弱/开源 VLM(北极星目标)也能借拐杖量准** ③ 守 0-5 铁律(现在模型 ad-hoc 黑箱 CV 非确定性/不可复现/不可审，做成一等工具才既拿精度又可审) ④ 是**连接 Phase B(算术下沉，工具箱=metric.anchor_px 通道产出器) 与 Phase C(CV 前端，工具箱=轻量前置版) 的桥**。**caveat**：灰度阈值吃干净 CAD 导出 PNG，扫描/手绘/噪声图要更鲁棒(形态学+自适应阈值)、分档。

**2026-07-06 事后审收口（排队单①）**：Codex 对抗审 `e3ec9ae` 出 3 MAJOR+2 MINOR 当轮全修（`045caae`，496→500 绿）：sidecar 路径穿越+TOCTOU→NNN 正则+独占写、gt 纪律扫描原 token 抓不到直读 gt.json→补 token 变真守卫、fractional bbox 截断破 crop_chain 可逆→floor/ceil 归一、overlay 无可画几何 raise、alpha 白底合成。verdict `logs/reviews/verdict/2026-07-06_cv_toolbox_posthoc_review.md`。CV 批全审计闭环（方案审+执行+事后审）齐了。

**✅ 2026-07-07 北极星判决性实验=阳性满分（排队单②，Fable5 主控）**：Haiku 4.5+工具箱在 sm21 gt 判卷与 Sonnet 5 基线**逐项相同**（墙9/9·平面窗7/7·立面窗15/15 complete·0.0m·过度分割0）vs 07-05 无工具箱对照全崩——机理=失败模式从"看错"（感知,救不了）迁移为"量了不筛/锚错"（流程,纪律可托）。三限定：工具箱**指令要求使用**非自发/需 **pilot 打回一轮**（两案皆然:标定错锚·量了不筛·漏描·anchor 写成自创 dict）/prompt 级隔离。**sm24 探针**（非方形+无标注构件,5/5 收口无 gt）：正交多边形对行列投影无新难度;**无标注构件=标定后像素直测正解**;弱 VLM 跨 case 稳定短板=首抽散漫+schema 写作错（Phase B 双通道/schema 外包直接证据）。**OCR 数据驱动裁定=维持 Phase C**（Haiku 读数无错;触发器=跨模型标定/读数失败）。**E 效率批同日落地**（Codex 审 6 findings 全采纳,517 绿）：E1 纪律固化进 skill（cv_toolbox.md 自声明 clean-CAD required,per-run 指令不再需要）+E2 prescan-plan/-elevation 宏工具（有界真实线段·中性命名 line_band_candidate·capability_profile+不支持档 raise）+E3 预扫前置化 SOP（用户授权方向修订:确定性预扫挪编排侧 spawn 前,语义判定权留 VLM）。成本基线=Haiku 0.4-0.65M tokens/case（返工+单工具循环是大头）。**迁移性判断**：确定性工具+纪律+验收 harness 模型无关,漂移的只有残留 VLM 职责→Haiku 只当下限探针,换模型=harness 重跑验收（一天内）。**下一场（用户拍）=GPT-5.4-mini 交叉测试**（Opus 盯 Codex 跑,交接单 `logs/experiments/2026-07-07_haiku_cv_retest/HANDOFF_gpt54mini_crosstest.md`）;开源 VLM api 首验收提前案待其结论。顺带修 M1 引入的 pipeline.py import 回归（run_correction NameError+回归测试）;容器网络只通 Anthropic,DeepSeek correction 宿主侧续。**✅ 2026-07-08 Phase B/C 定位澄清（Opus 接手·用户认可）**：「CV 上了」≠「Phase B 做了」——CV 工具箱 = **Phase B 的施工载体**（Fable5 报告 B2 裁决1），**仍必需、非过度设计、只是当前不紧急**。现状=**载体已上**（C0/C1 sidecar+工具+VLM 手动调用验证=07-07 阳性），**架构下沉未做**：①双通道 schema（visual.anchor_px+metric·reading 不吐坐标）②算术下沉求解器（代码消费 CV 证据求解）③derive_facade_frame 真替 LLM 世界落位（仅做了 gate① flag-only 交叉校验）。**后置≠取消**：sm24 探针「VLM schema 写作错/anchor 自创 dict」+facade 未接线=Phase B 欠债入口。触发器（报告 B2 裁决2）=迁移性验证充分（gpt54mini）+要接双通道/开源 VLM 时（双通道 schema 在「算术下沉集成」档一次落·含 correction 契约更新+重录 baseline·别拆两次）。

**✅ 2026-07-08 GPT-5.4-mini 交叉测试=阳性满分带（迁移性成立，用户肉检后关闭）**：gpt-5.4-mini（经 codex CLI，非 Claude Agent tool）+ CV 工具箱在 sm21 判卷=**墙 9/9·0.0m·平面窗 6/7·立面窗 15/15 complete·过度分割 0** = 与 Haiku 07-07/Sonnet 5 同级（仅差 1 平面窗，1f 南窗偏 0.53m）→**配方模型无关、非 Haiku 特调**。06-23 无工具箱两失败点全修复（South-F2 四窗并两窗→4/4；2f 漏隔墙 6区→墙 5/5·7区）。**E 批固化在新模型 hold**（prompt 无 measure-before-draw，读 cv_toolbox.md 自发调 13+ CV 工具/图）。效率 ~0.9M tokens/case（~1.5x Haiku，弱模型试错多，East 单图 72 调用）。run=`run_2026-07-08_gpt54mini_cv_retest`（走正规 flow：gate①+J0 judge_pass+attempts+render+grade+score_vs_gt+report 四桶）。**解锁**=开源 VLM 验收提前案（用户定是否推）。**⚠️流程教训**：我一开始参照旧 run 手搓判卷（现查 elevation_score API + 手动汇总）造轮子，该直接走 flow（自动出 score_vs_gt 含平面+立面/grade/render/attempts）；codex 喂图坑=`-i` 可变参数吞尾随 prompt→走 stdin。已把跑测铁律登记 CLAUDE §5（走 flow/禁手搓判卷/禁抄近道）。**fable 期(07-06/07/08)高价值内容已沉淀活文档**（Opus 接手：decision_log 07-03→07-08·plan backlog+Phase B/C·contracts §5.6-5.8·capability B1 补·geometry proposal §9 B3·Codex 复核 APPROVE-WITH-CHANGES 4 findings 全采纳,commit `ebddada`；代码批 `df6f249`）。相关 [[haiku-downgrade-model-is-lever]] [[reading-evolution-and-phase-a]] [[standardize-test-flow-and-judge-arch]]。

**✅ 2026-07-09 prescan 候选收窄落地（Fable5 亲手执行=用户当日指示反转 §5#8 一日，`20749ff`）**：07-08 报告效率项——prescan 加 `min_strength`/`min_line_len_px`（只滤 line_band；**tick=标定锚永不过滤**）+`label`（参数化侧车共存）+`diagnostics.axis_summary`（按投影峰聚合，1f 370段→48轴=弱模型逐段 crop 核验的主刀）。**gt 差分幸存验证零构件丢失**（推荐档 0.08/30px：平面墙轴/立面窗边全保；立面窗边本就不在 line band 通道、走 window_cc_detector）。cv_toolbox.md 新纪律=候选预算+立面 `--no-cc`（立面 cc≈文本噪声+粘连轮廓）+**组内标定复用**（平面组 91 vs 立面组 58 px/m 跨组差 58% 禁盲复用；单锚点抽验 ≤1px）。**默认值刻意不动**保满分带配方，推荐档由 skill 文档驱动。分析=`AI_agent/logs/experiments/2026-07-09_prescan_narrowing/ANALYSIS.md`。**当日 Haiku 对比重跑=pilot 4 轮止损（用户拍 reading-only 配置后执行）**：run_2026-07-09_haiku_prescan_triage 终止于 pilot（标定系统性锚错 60 vs 真值 92 px/m·幻觉走廊短墙·窗错位；Haiku 每轮只机械满足 feedback 点名项）。**收窄本体阳性**（pilot CV 调用 86→2-6 次、axis_summary 被消费）；**新主导成本=硬隔离协议无状态重 spawn 循环**（5 会话 ~1.03M 新 token，每轮打回冷启重来 ~0.25M）——07-07 满分的两根拐杖（per-run directive 开场指令+连续交互会话）在 07-08 硬隔离协议下都不在（缺口 #5/#6 已登记 plan.md）。**修 spawn --directive 槽后按 07-07 directed 模式复跑**。执行日志=logs/experiments/2026-07-09_prescan_narrowing/HAIKU_RETEST_LOG.md。codex reasoning effort 下调=下次跑测实验变量非代码。

**⚠️⚠️ 2026-07-30 适用域重大修订（sm24 端到端第一次尝试撞出，用户提假设 + 主控当场用盘上数据证实）**：同一把尺子（sm24 GT 八道隔墙·容差 0.30m）量三份历史识图 ⇒ **06-24 Opus 5/8 · 07-07 Haiku+工具箱 8/8 满分 · 07-30 Haiku+工具箱+预扫+硬隔离 1/8（多画 10）**。**同模型同工具从满分掉到几乎全错 = 机制退化、非模型能力。**
- **产出量同步崩**：笔画 25→15（平面 window **11→0**，并错误断言"平面里没有窗"）· 尺寸转录 51→13 · uncaptured 诚实登记 15→3 · 探针 19→8（另 6 次被隔离守卫拒）= **只做了约四分之一的活**。
- **失败形状**：15 条墙全 `dimension_derived` **零实测**；把北立面尺寸链 `540|1600|2520|4800|540` 的累加位置画成四道纵向内墙（**那是窗与垛不是隔墙**），而真正标隔墙的底部链 `4180|1640|4180`（→ 4.18/5.82 = GT 两道纵墙）在 pilot 轮读到过、正式轮却没用 ⇒ **工具跑了、量出来的数没进产物**。
- **⭐ 结论修订**：**「量而非看」没被推翻；被推翻的是「给了工具就会去量」**。工具可用性 ≠ 工具被用于承重坐标。**判卷/复盘必查 `provenance` 分布，全 `dimension_derived` 零实测即红旗。**
- **归因候选四条（需单变量四臂 A/B 分清）**：① 硬隔离令探针成本翻倍（先 Write 请求文件再执行；07-07 可直接带参调用）② 守卫词法摩擦吃 6 轮 ③ 预扫 803 噪音候选可能把模型锚定到尺寸链 ④ **主控 directive 把「尺寸链逐字读」列为可接受来源第一位 = 主控自身也是变量**（如实登记）。
- **下一步实验（便宜且判决性）**：固定 Haiku + sm24 平面，四臂 = `07-07 原样` / `+预扫` / `+硬隔离` / `+两者`。
- 与 07-09 那条同源并升级：当时已发现「07-07 满分的两根拐杖在硬隔离协议下都不在」，本轮是该缺口在**真实验收跑**上的完整代价显形。详 `AI_agent/logs/experiments/2026-07-30_sm24_e2e_attempt/`，相关 [[contamination-hard-isolation-requirement]]。

**⚠️ 2026-07-31 再次修订适用域**：本条记录的「Haiku+工具箱 = 8/8 满分」**是带主控监督拿到的**——过程记录显示 pilot r1 被主控打回并被明确告知「标定错锚 / 候选未逐条核验 / 字段全空」。上线无主控 ⇒ **该成绩不能作为无监督基线**，「量而非看」的结论仍成立，但「弱模型能独立达到该水平」**未被证明**。详 [[reading-supervision-contamination]]。

**⛔⛔ 2026-08-01 收工：本条的核心主张已被用户判定为假象，全条降级为「历史记录」不得再作依据。**
- **⚠️ 上一条的引文有误（08-01 查证更正）**：「标定错锚 / 候选未逐条核验 / 字段全空」是 **sm21** 那轮 r1 的打回内容；
  **8/8 是 sm24**，它有自己的记录且**被打回两次**（r1 纪律：标定 RMSE 86mm 锚粗 / **只描「主要墙」违完整性** /
  窗未描 / px→m 换算自相矛盾 → 指令「锚收紧到 ±1px、**全墙完整描**、单一换算公式留痕」；r2 纯 schema 形状）。
- **⭐ 机制侧硬数据（08-01 主控实测）**：好成绩两轮平面图工具调用 **sm21 = 33/24 次（crop_zoom 17/16）·
  sm24 = 19 次（crop_zoom 11）**＝**逐个候选放大核验**；08-01 无监督两抽 **1–5 次、crop_zoom 零次**。
  **⚠️ 且 07-07 两轮均无预扫**（`cv_evidence/` 无 `prescan/`）⇒ **「8/8 配方里本来就不含预扫」**，
  主控此前「撤预扫会掉回 0%」的断言**说过头了、已收回**。
- **⭐⭐ 病灶（08-01 双独立调查，sol 先发现 + 主控独立验证两遍）**：产物里
  `self_check.all_visible_strokes_captured` **是结构化字段、被诚实填 `false`、而全仓生产代码零消费者**
  ⇒ gate① 0 阻断放行。**读图器没有不听话：它自评了、如实报了、提交了；没人说 false 不许交、也没人读那个字段。**
  ⇒ **「把话说清楚」连续失败三次**（E1 写进 skill → W1 提顶层 → W3 把正确写法写进报错，
  **第三次把标准答案递到手上仍放弃**）＝ **文档不可能验证别人有没有遵守自己**。
- **⚠️ 冷水**：同轮 d2 四个自检字段**全填 `true`、成绩仍只有 24.8%** ⇒ 把该字段变阻断项只能抓
  「诚实的没做完」，**抓不住「自信的做错」**，且大概率**把 d1 变成 d2**。
- **归因仍不干净**（两边独立收敛）：07-07 事前完整 prompt **从未落盘**（原文「完整 prompt 在主控 transcript」）
  ⇒ 无法排除「那次打回是它第一次被要求」；07-07 vs 08-01 差 ≥4 变量；同配置两抽差 **2.8×**（噪声主导）。
  **且打回不是零信息**——含「你漏了哪些」这类针对产物自身的差异。
- **⇒ 下轮起点**：用户判「之前的 reading 都是假象、没有准确回归的办法」，**先点射 Fable 出方案**
  （**Fable 已退订 ⇒ 走 Comate 人工中继**，见 [[comate-gateway-relay-channel]]）。
  方向在册＝把测量移进代码、识图降为「在确定性候选上分类 + 查漏」；**实测卡点＝候选召回不足**
  （长线 5 条 vs 答案 16 段内墙；其中 3 条精度 0.06–0.07 m）。详 [[reading-supervision-contamination]]。
