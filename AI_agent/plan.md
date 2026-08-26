# 行动清单（活计划）

> **职责**：只放**还没做完的事**和**当前一轮的日更**。**体量纪律 = [CLAUDE.md §0.5](CLAUDE.md)（唯一权威）**：
> ⛔ 不放历史叙述——做完的、翻篇的一律搬 [`logs/worklog/`](logs/worklog/)（见文末 §归档）；
> **本文 >900 行 或 出现上一轮日更 ⇒ 收工时当场搬**（§5#12 第 ② 步）。
> 当前状态看 [CLAUDE.md §2](CLAUDE.md) · 历史决策看 [decision_log.md](decision_log.md) ·
> 架构看 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) ·
> 标准工作流看 [guides/new_case_guide.md](guides/new_case_guide.md)。

---

## 当前焦点（2026-08-21）

> **第一目标（用户 08-18 定）= 恢复到 07-07 的 reading 水平。** ⭐ **2026-08-20 已达成一格。**
> 判断法则见 [CLAUDE.md §0.1](CLAUDE.md)：不做这件事，下一次跑测能不能跑起来、结果能不能读？能 ⇒ 登记，不做。

### ✅ 已达成：07-07 水平在当前基座上复现

`run_2026-08-20_acceptance_sonnet_S1`（Sonnet 5 × sm21 全 6 图，**工程档 n=1**）：
**9/9 平面墙 · 7/7 平面窗 · 15/15 立面窗 · 最大偏移 0.0 m · 首抽零返工** —— 与 07-07 靶子逐项相同。
⇒ **「07-07 那个形态在当前代码上还灵不灵」这个问题，答案是灵。** ⛔ n=1 工程档，不作正式成绩。

⚠️ **但满分掩盖了一处几何缺陷**（用户肉眼发现，orchestrator 已坐实）：
外墙落在实测像素中心线（内缩 0.11–0.12 m）、窗仍落在标称尺寸链位置 ⇒ **两个基准不一致**；
判卷只比对由分区边界派生的内隔墙、**从不比对外轮廓坐标** ⇒ 零代价。
**全档 + 四条登记 → [reading 专项 §10](capability/reading/improvement_methodology.md)。**

### 🔻 GPT 那格未达标（不下「退化」结论）

`run_2026-08-20_acceptance_gpt54mini_G1`：7/9 · 5/7 · 立面 6/15。1f pilot 过（4/4·3/3·0.09 m），2f 与四立面塌。
**失效机制已实测**：撞上跨轴分歧告警后**把两轴拆成两次单独调用把告警消掉**（同族 F-63）——
而这是 orchestrator 的返工要求「两轴必须一次给全」**教出来**的
⇒ [[rule-without-legal-exit-breeds-invention]]，**prompt 挡不住，只有工具层能**。
⛔ **不下「GPT 退化」结论**：至少三个变量未控（提示词含不含 measure-before-draw / 返工轮数 / effort 档），
且退化集中在 2f 与立面，而历史树对照**只跑过 1f** ⇒ **缺「GPT × 历史树 × 全案」那一格**，登记归 reading 专项。

### ⭐⭐⭐ 战略调整（2026-08-21 用户当面定，覆盖此前的 reading 推进方式）

> **跑测的目的是升级 harness，不是拿分。分数只是 harness 硬不硬的读数。**

**开发循环（四步，此后按此走）**：
1. **最强模型（orchestrator 本人）亲自下场做** 这个 case 的 reading —— 边做边定：
   要不要造新工具？工具怎么调？最好的 SOP 是什么？哪里易翻车、该用什么约束住？
2. **先摸出工作流，并且自己真做出一份不错的输出**（不是纸上谈兵）。
3. **把能固化的固化进 harness**：工具、skill、提示词、门与约束。（怎么拆分由 orchestrator 定，用户只给目标）
4. **逐级降低模型智力验收**。弱模型也能做出来 = 固化成功。

⛔ 反向做（一上来让弱模型跑、指望它做对）= **许愿，不是开发**。

**推论**：
- **三种 reading 模式作废**（autonomous / controlled / dev 职能）—— 模型强度成了**一根连续刻度**，不是并列赛道。
- **不再纠结「复原 07-07」** —— 改为把历史好 reading 里可提取、可验证、有共性的东西**沉淀进现在的 harness**。
- ⛔ **硬约束：harness 只做增量升级，不为新 case 特化，历史 case 也要照样做得好**
  ⇒ 每条沉淀物必须对 5 份历史好 reading 全绿。
- **隔离铁律的适用范围**（用户已同意）：探索/造 SOP 阶段 orchestrator 可亲自看图亲自做；
  受 08-02 那四条铁律约束（不给生产喂信息 · 这类跑不作成绩 · **收官验收 orchestrator 退场**、
  跑已固化工序 + 已冻结工具箱）。

### ✅ 已做：历史 reading 解剖 + 离线夹具与过程指标（2026-08-21）

全档 → [`logs/experiments/2026-08-21_historical_reading_dissection/`](logs/experiments/2026-08-21_historical_reading_dissection/README.md)

- **去重**：全仓 75 run / 48 份识图产物 ⇒ **独立 reading 只有 27 份**；
  ⭐ 那 19 个「9/9 满分」是**同一份 07-07 产物被复用 19 次**（[[proxy-mistaken-for-the-thing]]）。
- ⭐ **一条不变量：几何是「量」出来的不是「看」出来的** —— **5/5 好 reading 全部用代码测量，零例外**
  （07-02 是**自己现写** PIL+scipy 流水线、60 次 Bash；其余三份用固化工具箱；S1 access log 里 python 114 次）。
  ⚠️ 初稿曾把 07-02 记成「零工具箱 9/9」并当作反例 —— **前提错，用户当场纠正，已重写**；
  且 07-02 **不作形式参照**（现造的工具箱是来源不是实例）。
- ⛔ **但具体做法层面没有单一杠杆** —— 每条候选纪律都有好 reading 反例
  （07-08 零像素锚/零 refs/零台账/只标定 2/6 图，仍 9/9 · 崩掉的 D1 链解释率 100% 而好的 S1 只有 40%）
  ⇒ 按用户口径**多路径可行的环节先做成工具**，后续再取舍/综合/留作不同图纸类型的适配性选项。
- ⭐ **唯一 14/14 完全分开的量 = 证据密度**（转录标注数 ÷ 笔画数）：好 2.37–3.23 / 坏 0.61–2.14。
  ⛔ **仍为 provisional 非门**（14 样本 · 13 个同一栋楼 · 边界只差 0.23）。
- **新产物两件**（不需要 gt / LLM / 跑抽）：
  `case_tests/test_baseline/reading_fixtures.json`（5 好 + 9 坏历史 reading 冻结成夹具）
  + `scripts/tool_scripts/reading_process_metrics.py`（过程指标 + 三道硬门）
  + `tests/test_reading_process_metrics.py`（**27 把锁**：好夹具逐份零告警 · 至少一份坏的红 ·
  今天红的 6 份钉名 · 抓不住的 3 份写成显式缺口 · 每道门配合成红/绿对照）。
  ⭐ **补上的洞**：此前 `reading_regression.py` 比的是分数，而分数要先花钱跑一抽才有 ⇒
  「改了脚手架会不会伤到 reading」只能用钱回答；现在**离线**就能回答。
- **三道硬门**（收录判据 = 好夹具全绿 + 至少一份坏夹具变红）：
  ZERO-PRODUCT · NARROW-OPENING（0.60 m 领域下限）· **POLARITY**（F-69 抽象成不依赖 gt 的判据：
  「窗之间的空档比窗本身更规整」⇒ 疑似把墙垛当窗；跨 12 面墙只响 2 次，好 reading 全沉默）。
  实测坏夹具 **6/9 变红、好夹具 0/5**；叠加 provisional 后 9/9。
- ⭐⭐ **查出一处 harness 退化**：07-07 留了 92/38 份 CV 侧车（每图标定 + 决策台账），
  T1 **同样调了 42 次 cv_probe / 19 次 profiler / 56 次 crop**，但隔离壳 merge 只带回 `1f_view.json`
  ⇒ `cv_evidence/` 整个不存在。**今天只能靠 note 猜，07-07 能逐条查。**
- ⛔ **本轮我两处判读失误已登记**：① 「东墙偏 0.95 m」→ 真因是极性反了；
  ② 「A2 把窗写成图像比例」→ 错，据此写的量纲门在夹具集上一次不响，**当场删掉**
  ⇒「必须在真实夹具上响过」这条收录判据，第一个拦下的是我自己写的门。

### ⏭ 下一步（2026-08-21 夜，结转四条已收三条）

| # | 结转 | 状态 |
|---|---|---|
| 1 | 四道过程门接进 gate① | ⏸ **派工单已出、待拍板派发**（碰 `src/validator/` 须换人施工 + 跨家族审）→ [派工单](logs/reviews/request/2026-08-21_reading_process_gates_into_gate1.md) |
| 2 | 隔离壳 merge 带回 `cv_evidence/` | ✅ **已修（F-35 闭合）**⭐ 该缺陷 08-16 就登记成 **strict xfail**（`test_f35_cv_evidence_should_reach_attempt`），本次修完它自动 XPASS ⇒ 已摘 xfail；全仓 xfail 14→13。：整棵 `out/cv` 拷进 `attempts/NNN/cv_evidence/`，含 overlay PNG；provenance 记 file_count/bytes/sha256，缺席显式记 null。2 把锁 + neuter 实测（摘掉即红）|
| 3 | 07-07 的四件套 + 台账写成 SOP 进 skill 库 | ✅ **已跑完并写成草稿**（2026-08-22 orchestrator 下场 1f+2f）→ [SOP 草稿](logs/experiments/2026-08-22_orchestrator_hands_on/sop_plan_reading.md)；进 skill 库属固化项 |
| 4 | 收 07-07 六条 schema feedback | ✅ **已收**：①④⑤ 本轮修完（guide.md），②早已修，剩 ③（枚举，须派工）+ ⑥（=F-70）|

**✅ 已跑完（2026-08-22，范围经用户当场扩到 1f+2f）** → 见本文「2026-08-22」条目与
[全档](logs/experiments/2026-08-22_orchestrator_hands_on/README.md)。
**⭐ 下一步 = 固化**（新战略第 ③ 步），三项均须**派工 + 跨家族审**：
① 墨迹方言探针 + 洞口带扫描 + 刻度对账 → `src/agent/reading/cv_toolbox/` + `cv_probe.py` CLI
② 彩色 recipe `layered_cad_v1`（**F-70 的正解**）与 `clean_vector_v1` 并列，由方言探针选，⛔ 不许删旧的（sm20 还要用）
③ SOP 进 `skills/intake_pipeline/0_reading/`（主控可直接改）
之后才是第 ④ 步降智验收。⛔ 本轮一切分数不作数。

### ⏭ 更早的下一步（2026-08-21 白天收工态）

| # | 步骤 | 状态 |
|---|---|---|
| 1–7 | 素材 → 转换器多层化 → 立面载体层 → testdata → 转换请求 + 六图标定 → 平面三修 → 候选包 | ✅ |
| 8 | **用户签字（G10）** | ✅ `hortonyyx` @ 2026-08-21T06:52:50Z |
| 9 | 带签名重跑 + 晋升入库 | ✅ **十门全绿**，`gt/sm25-L_anchor/` `f97cea65…` |
| 10 | **Sonnet 读 1f（C2 首考）** | ✅ 已跑并判分（见本日条目）|
| 11 | 读 2f + 四立面（约 $40）| ❌ **⏸ 等拍板** |
| 12 | 跑 0–5 管线 = 真正验到 C2 | ❌ |

**⭐ 下一轮开工时要拍的两件（用户 08-21 未决）**：

| 选项 | 说明 | orchestrator 倾向 |
|---|---|---|
| **A. 查东墙 0.95 m 锚点偏移** | 便宜。7 个窗节奏全对、整列偏 0.95 m；查它拿哪条尺寸链锚的东墙。若是系统性问题，修了对每个非方形 case 都有用 | ⭐ **先做** |
| **B. 修 grade.png 平面面板** | 纯渲染、⛔ 不碰分数。现状：长哈希标签堆叠 + 判据轨道按洞口数吃高度把几何挤成一角 + 每格 `na_reason` 文字平铺。**「7 个 miss 全在东墙」是手工挖 JSON 挖出来的，本该这张图一眼给出** | ⭐ **与 A 一起做**（有能看的图，查 A 快很多）|
| C. 直接读完剩下 5 张图 | 约 $40。但若 A 是系统性偏移，2f 大概率同样丢一列窗 | 放 A/B 之后 |

**⛔ 明确不做**：消除转换器哈希序依赖 / DXF 字节确定化 / 重建可复现性体系（用户 08-20：
「gt 不用做得太复杂，本来就是 dev 期的东西，能做出一个正确的 gt 最重要」）· 再动 guard 围栏 · 补围栏/补审/补锁。

---

## ⏭ 下一步（活表 · 2026-08-26 按用户四步次序重排）

> ⭐⭐⭐ **次序以 [CLAUDE.md §2 banner ①](CLAUDE.md) 的四步为准**：
> **① 把判分修好 → ② 按新方案改造 reading+correction 的 harness → ③ 产出新方案的产物 → ④ 一步步验证**。
> ⛔ **旧 sm25 产物不再作验收对象**；⭐ 判别法则 = **「换一份产物，这条结论还在吗？」**。
> ⚠️ **本表下方阶段编号沿用 08-25 的 0/1/2/3/4，⛔ 与上面四步不是同一套编号**（0/1 已收完，留作账目）。

### ⭐⭐⭐ 派工盘（2026-08-27 夜 · orchestrator 按用户 12 条口径自排）

> ⛔ **不是 sol 那六个包的转写** —— sol 意见正文没落库、原文已不可恢复（本日 §四）。
> 本盘里注明每一条的**来源**：`[sol]` = sol 带回来的结论 · `[用户]` = 12 条口径直出 · `[我方]` = orchestrator 新排。
> ⭐ **判别法则（本日补全为两问）**：①「换一份产物，这条结论还在吗？」判**缺陷真不真**；
> ②「这段代码在新方案里还在吗？」判**现在该不该修**。两问都过才排期。

#### 第 ① 步「把判分修好」

| 包 | 内容 | 来源 | 状态 |
|---|---|---|---|
| **①-1** | **F-95** 顶点规范化收窄为有序简单环（= C2 非方形那半的本体）| [我方] | ✅ **收口** —— GLM 跨家族审 **APPROVE / 0 阻断**（08-27），4 条不阻断 findings 已分流 |
| **①-2** | **G1** ⇒ **派生审计件的可读 API + 机械复现门** | [用户]口径12 + [sol]#1 | ⏳ **返工已交件** `ef41a39`（**整张豁免清单已删**，全量 3046）· **⛔ 未过审** |
| **①-2′** | ⭐⭐⭐ **VS：sm25-F1「裁判事实包垂直切片」五步**（还原并核对签字 candidate → **exact manifest/request 落进 case-owned 路径** → **未参与拟合的 DXF 特征做原点 holdout** → 直接以产品 `*_px` 做一次像素判分 → **「只改产品标定：标定分变、描图分不变」判别实验**）| [sol] 08-27 | ⏭ **下一件事**（覆盖原 ①-3/①-4 的排法）<br>⭐⭐ **2026-08-27 升级理由**：第 2 步**不再是整理，是修 F-111** —— GLM 实跑证明 **sm24 的签字 request 已经不可寻**（`logs/experiments/` 是它唯一栖身处，已被清理）⇒ 复现门**可用面已经掉到 2 份 case 里的 1 份**。⇒ **这一步现在有一个已经咬过人的缺陷做靠山，⛔ 别再当成「顺手做」排在后面**；且它同时决定 F-111 是「找回归档」还是「明确放弃 sm24」|
| ~~①-3~~ | ~~**G2** 墙面线落盘 + 不规整清单~~ | [用户]口径12 | ⛔ **暂缓扩面**（sol：模数格点政策未签字前，「两种读法第一份清单相同」判早了）|
| ~~①-4~~ | ~~**G3** 判分侧标定归裁判~~ | [sol]#2 | ⇒ **并入 ①-2′ 的第 2–5 步**（它本就该排在 G2 之前）|
| **①-5** | **语义升格成正式答案字段并计分**（配对 · 门窗身份 · 墨族角色 · **「我认不出来」这个声明本身**）| [用户]口径11 | ⏭ ⭐ **改**：**判分侧的字段与语义先冻结（属 ①）**，producer 侧实现随 ②（sol 指出原写法与四步次序冲突）|
| **①-6** | **F-89** 一张立面跨两层就整份丢 | [我方] | ⏸ **本日改判为挂起** —— 真缺陷，但那段代码服务 legacy reading 契约，② 要换掉它（见本日 §三）|
| **①-7** | **F-98** 判分对浮点末位敏感 | [我方] | 观察项，随判分侧改动一并评估 |

#### 第 ② 步「按新方案改造 reading + correction 的 harness（一体改）」

| 包 | 内容 | 来源 | 状态 |
|---|---|---|---|
| **②-0** | **F-97** correction 只吃**声明过的契约**，未声明的**响亮失败** + 消费对账 | [我方] | ⏳ **返工已交件** `f2a8ccf`（三条阻断全修，全量 3070）· **⛔ 未过审** |
| **②-1** | **冻结出模形式** + **`ReferenceFactsV1` + 单一确定性 `AnswerCompiler(profile)`**（同一份 facts 同时派生 axis 投影 · exterior 投影 · 像素描图分母 · 不规整事实表；run config 只选哪个是正式成绩，⛔ 不让证据阈值选形式；metamorphic 门：两投影只差声明的 t/2、往返可恢复、缺资料整份 `unprojectable`）| [用户]口径2 + [sol] 08-27 第三形态 | ⏭ **② 的第 1 号包**，⚠️ **等 ①-2′ 的读数再定形**；⛔ 投影是**整层事务**，任一必需墙边不可派生就整份响亮 NA，⛔ 不许逐轴保留原样 |
| **②-2** | correction 改成吃「**带原始引用的多形态墙证据**」（六形态：paired_faces / solid_band / single_face / axis_trace / ambiguous / non_wall）· **并改掉提示词里那两句 `wall-centerline`** | [用户] + [GPT 08-25 证伪] | ⏭ 一体改本体 |
| **②-3** | **F-87** 门窗身份逐洞口外置（「认」还有一块留在评分器里）| [我方] | ⏭ 随 ②-1/②-2 |
| **②-4** | **墙厚**：优先双通道（像素+标注）· 像素单通道兜底 · **浮点吸附归 correction** · **吸附分辨率跟 gt 走**（gt 声明 → 跑前抄进配置 → 判分侧核对一致，不一致响亮失败）| [用户]口径8/9 | ⏭ 随 ②-2；⚠️ **那个分辨率参数目前没有名字、没人签字** |

#### 第 ③④ 步

⏭ 等 ②。⛔ **旧 sm25 产物不作验收对象**；③ 的验收对象 = **一体改之后的新产物**。

#### 债 / 小单（不占主线工期）

**D-2** 装机路径根治（⚠️ 摘 `.pth` 须排在 G1/F-97 落地后，共享环境会撞车）· **D-3** 判分缓存版本改派生摘要 ·
**D-1** 双份代码限期退役 · GLM 七条不阻断 findings（含「locator 不在 catalog」分支错命名 + 零锁）·
**F-105** reading 侧 NA detail 语义变了但 helper 版本没提 · `scripts/*.sh` 缺可执行位（登记不改）。

---

**⭐⭐ 今天新发现的最大缺口：as-drawn 产物喂不进 correction。**
correction 读 `*_view.json` 的 `strokes`（带 `pen`，prompt 还引用笔画 id、数 `pen=="window"`），
as-drawn 产 `observations.face_lines`/`hypotheses` —— **两套 schema 完全不通，零接线**。
且**基准不同**。⭐ **2026-08-25 更正归属**：原写「旧 reading 自述唯一基准=墙中线」，复核后找到更硬出处 —— **是 `1_correction` 的提示词在要求中线**（[pipeline.py:365-369](../src/agent/pipeline.py#L365) 逐字写着 `wall-centerline` / `wall CENTERLINE`）⇒ **不是 reading 换格式要适配，是 correction 自己在要这个基准**，一体改必须动那两句字符串。
⇒ 写转换层塌成中线 = 在 reading 侧偷偷替 correction 干活并扔掉信息（**R-6 同形**）。
⇒ **用户已定方向：reading 与 correction 一起改。⭐ 先拉 sol 讨论架构**（涉及 reading 专项 + 出模专项主体）。

| 阶段 | # | 事项 | 状态 |
|---|---|---|---|
| **0 清合并阻塞** | 0-b | **F-93** 全仓 4 项红 | ✅ **已闭合**（`b3e0a32` · GLM APPROVE-WITH-FINDINGS · 全仓 `3014 passed` 全绿）|
| | 0-a | **F-94** 装机路径 —— **A 案止血** | ✅ **已闭合**（`91ae82d` · GLM APPROVE-WITH-FINDINGS · 全量 `3016 passed`）|
| | 0-f | GLM 对 A 案的 5 条 findings（**锁不验 `parents[N]` 参数** · ⭐ **`tests_scripts/` 是覆盖外的现存串台入口** · 保守误报清单 · E402 现在不动 · 锁 CLI 恒 exit 0）| ⏭ 与 0-e 一并打包下轮派工；⭐ 第 2 条**或并入 D-2** |
| | 0-a′ | **F-94 B 案根治** | ✅ **已转债 D-2**（用户 08-25 拍板）· 退役须另开单 |
| | 0-e | GLM 三条不阻塞 findings（测试改名 · **1-a 锁内置反向对照** · docstring 小瑕）| ⏭ 下轮派工打包 |
| **1 支线回并** | 1-a | 合并 `toolbox_into_src_08.25` → `08.23_AsDrawnReading` | ✅ **已回并**（`0182bea`，13 文件/3741 行**零冲突**；全量 **`3017 passed`**）。⭐⭐ **合并适配一处由新锁抓出**：`reading_toolbox.py:39` import `src` 无自举 ⇒ **锁的第一次真实捕获**（非夹具、非人造）|
| | 1-b | **债 D-1** 双份代码（`tools/` 原件 vs `src/` 新件）| ⚠️ **自本次合并起在主线上正式成立**（实测两处 `as_drawn_v2.py` 并存）· 退役须另开单 |
| **2 一体改** | 2-a | ⭐⭐ **reading + correction 一体改** | ⏳ **前置 = 与 sol 讨论架构**（⭐ **需用户拉人**）→ [讨论稿（已改写至最新）](logs/reviews/request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md) · [GPT 备料](logs/reviews/verdict/2026-08-25_reading_correction_unification_gpt_design.md) |
| | 2-b | **F-97** 契约判别器（未知契约响亮失败）| **一体改的必做项**（已行为实测：门不但看不见它，还给绿灯）|
| | 2-c | **F-87** 门窗身份没外置 | 归 reading 侧，随一体改 |
| **3 撞 sm25 / C2**<br>⚠️ **本阶段的验收对象已由用户 08-26 改为「一体改之后的新产物」**，⛔ 旧 R0 不再作验收对象 | 3-0 | ⭐ **F-90** 楼层 id 两套命名无映射层 | ⛔ **补审 = REJECT**（2026-08-26，GPT）→ [裁决](logs/reviews/verdict/2026-08-25_f90_floor_id_mapping_gpt_verdict.md)。**未闭合**：同根因**第 6 处**（plan segment matcher，桥建立之前就比字符串）+ 三条独立阻断 **F-100/F-101/F-102**。⭐ 那份「十判据读数」被推翻（唯一 eligible 的那条判的就是第 6 处的 bug）。**⇒ 需另开修复单（派工 + 换人审）** |
| | 3-0′ | ⏸ **F-99** 立面段与 gt 边界差 `0.12 m` | ⛔ **挂起，不排期**（用户 08-26 纠偏）—— 病根 = **correction 提示词在要中线基准**（`pipeline.py:365-369`），**一体改必须改那两句** ⇒ 现在修大概率白修。一体改落地后**用新产物**重测，再决定它还存不存在 |
| | 3-0″ | ✅ **F-102** 判分缓存 identity · ✅ **F-103** 官方口子压平 NA 原因 | ✅ **已修**（`b735db4`）—— 这两条是**验收通道本身**，与产物格式无关，**换新产物后照样需要** |
| | 3-a | sm25 全流程（用新 reading）| 等 2 |
| | 3-b′ | ⭐ **F-92 cell 多边形能力**（内部正交多边形）| ⭐ **2026-08-26 用户拍板改回在范围内**：「按实际形状，这就是 C2 批要解决的事呀，**内部和外部都解锁正交多边形**」⇒ **能力本身就是 C2 目标**；⛔ 只有「旧产物 38 个 cell 的 `polygon` 全 null」那条**读数**仍属挂起。⚠️ 一个连通走廊拆成多个 cell **会真的多出能耗热区与人造隔墙**（`modelling.py:479` 一 cell 一 ZoneVolume · `split_pairing.py:68` 相邻 cell 产区间墙，sol 指出）|
| | 3-b | **F-95** 顶点规范化毁凹多边形（**代码侧，有效**）| ⭐ 原与 F-92 并列，现拆开：F-95 是 validator+geometry 的实现缺陷、有离线夹具矩阵可证，**不依赖任何产物** ⇒ 照常排期；F-92 移入 3-d′ 挂起 |
| | 3-c | **F-96** 跨层碎片无守卫 | 同批 |
| | 3-d | **F-89** 一张立面跨两层就整份丢（**judge 代码侧，有效**）| ⭐ 与 F-91 拆开：F-89 是判卷代码缺陷、与产物格式无关，照常排期 |
| | 3-d′ | ⏸ **F-91** 立面多平面为空 · ⏸ **F-104** 核前草图有 cell 缺口（⭐ **F-92 已移出挂起**，见 3-b′）| ⛔ **挂起**（用户 08-26 纠偏）—— 三条**都是从同一份旧产物 R0 上读出来的观察**，新 reading+correction 产的东西可能不长这样 ⇒ 一体改后重测 |
| | 3-e | **F-98** 判分对浮点末位敏感 | 观察项，随判分侧改动一并评估 |
| | 4-a′ | ⭐ **gt 出一份 manual view 的 HTML，供人签字** | **登记，不着急上**（2026-08-26 用户）—— ⭐ 与 **gt 三层**配套：三层里的**「不规整清单」**正需要一个人能看的出口（清单只有机器可读 = 等于没有人在看）。⛔ 不排本轮工期 |
| **4 gt 层** | 4-a | ⭐ **R-6（保留逐边 basis+thickness）+ gt 不规整校验** | ⭐ **同一件事，⛔ 不能分别排期**；工作量已下调（`ZoneEdgeReportV1` 已是正式 schema）|
| | 4-b | **R-1** 判卷对外轮廓是瞎的 · **R-5** 房间类型词表 | 随 gt 层 |
| | 4-c | **R-3** 内外墙基准拐角错位 | 归**出模专项**，本轮不动 |

⛔ **债 D-3（2026-08-26 新登记）**：判分缓存的 helper 版本是**手工字符串**，改了语义忘提版本时**零拦截**（锁全绿、缓存照常命中旧 sidecar）⇒ 应改成**从实现闭包派生的组合摘要**，人工版本降为可读标签。GPT 与 GLM **两家独立给出同一判定**；⛔ 本轮明令不实施，另开单。同族 [[version-number-is-not-behavior-attestation]]。

⛔ **D-1 双份代码债**（`tools/` 原件与 `src/` 新件并存）：GLM 裁定 (a) 接受 + 登记 + **限期退役**，退役须另开单。

---

## 未闭合缺陷登记

| 编号 | 内容 | 状态 |
|---|---|---|
| **⭐ 新** | **转换器输出依赖 Python 哈希随机化**：同输入同代码跑两次，规范化 DXF 字节与 `content_sha256` 戳不同（实测固定 `PYTHONHASHSEED` 即稳定）。**答案内容跨 5 个种子恒定** ⇒ gt 正确性不受影响 | **登记不做**（用户 08-20 拍板）；已由新锁钉住「内容跨种子稳定」 |
| **⭐ 新** | **已签字答案的溯源戳与现行代码不一致**：sm24 的 `vg_implementation_sha256` 记 `60cab9e6`，干净 HEAD 算出 `8e45fd15`（07-27 后那四个 `correction/` 文件被改过 4 次）。⭐ **但答案内容实测逐字段一致 ⇒ 历史成绩仍可信** | sm24 由用户重签（用户 08-20 允诺）；⚠️ 重签时须认真看新叠图（渲染实测差 3–4% 像素）|
| **⭐ 新 R-1** | **判卷对外轮廓是瞎的**（gt 无 `walls`，只比对分区派生的内隔墙）| → [reading 专项 §10](capability/reading/improvement_methodology.md) |
| **⭐ 新 R-2** | 读图器**墙/窗基准不一致** | → 与「尺寸基准+墙厚方向」专项**合并决策** |
| **⭐ 新 F-65** | **立面窗提取只认 `LINE`，`window_selector.entity_types` 从不被读取**（`tarch_normalize.py:1694` 硬编码 `dxftype()=="LINE"`）。sm25 立面窗全是 `INSERT`(17 个 `$EWDLib$00000533`)+`LWPOLYLINE`(14) ⇒ **静默产 0 窗**，另有 17 条 `door_block_drift` 误报（窗块走了门那条路）。F-64 同族（零产出不报红）。实测应得 **31 扇窗 + 3 樘门**（东 12 · 北 8 · 南 7 · 西 4；门：东双开 1 + 西 2）| ✅ **本轮已修**（sol 施工 · GLM 跨家族审 APPROVE · 主控权威全量 3 次 2937 绿）|
| ~~F-66~~ | ~~东立面两门块重合~~ **⛔ 我报错了，已撤回**：拿插入点当外包框的代理量，实算 matrix44 变换后两块**相邻不重叠**（x 64727–65527 / 65527–66327）= 一樘 1600 宽双开门，现行 union 平铺逻辑正好合并它 | **撤销**（[[proxy-mistaken-for-the-thing]]）|
| **⭐ 新** | **立面诊断码迁移**：门图层上块名不在任何规则里的 INSERT，旧报 `door_block_drift`、现报 `tarch_elevation_entities_unconsumed`（门仍 G3 红，仅码变）| **知悉即可**；下游若按诊断码分诊需更新对照 |
| **⭐ 新** | `module_union_min_gap_m` 若声明值 ≤ 量化容差，「小于声明值必红」的区间退化为空 | **登记不做**（现实声明 0.5 m ≫ 容差；加下界属补围栏，§0.1）|
| **⭐⭐ 新 R-6** | ⛔ **主控初登记「gt 里根本不存在内墙厚度」，用户质疑后查明说法是错的** —— 转换器**每条 zone 边都量了厚度**并存进 `_ZoneEdgeRec`（[`tarch_normalize.py:873`](../src/agent/judge/tarch_normalize.py#L873)：`basis` = `outer_skin`\|`wall_axis` + **`thickness_native` 实测厚度** + `offset_native`），且正是用 **t/2** 把 zone 从净空撑到中轴（`_offset_for`, [:1058](../src/agent/judge/tarch_normalize.py#L1058)）。**但 `GtZoneV3` 只序列化 `polygon`** ⇒ **量了、用掉了、存盘时扔了**。⭐ **正确说法 = gt 把原始信息用掉了但没留下来**，⛔ 不是没有。⭐⭐ 且 `basis` **字面就是出模形式的开关**，逐边应用一次即销毁 ⇒ 留下 `(p1,p2,basis,thickness)` 就能**换出模形式而不重跑转换器/不重签**，内墙厚度也就有答案可对照 | **登记**（2026-08-23）· ⭐ **不是独立缺陷**，是 **B 步（gt 加 as-drawn 层）同一件事的又一症状**（与「`_WallFacePair` 算了但没落进 gt.json」同形）· 直接印证用户 08-20 定的「gt 应是原始信息集合、按出模形式派生」 |
| **⭐ 新 R-3** | **非方形外包导致 gt 内外墙基准对不齐**：内墙走**中轴**、外墙走**外包**，Z 形/退台上两者在拐角处必然错位 | **登记**（2026-08-21 用户令）→ 归**出模专项**解决，本轮不动 |
| **⭐ 新 R-4** | **立面「前后关系轮廓线」**：C2 落地后非方形建筑的立面出现进深台阶线（sm25 西立面距左端 6000 那条竖线 = 西向墙面在 y=14 处从进深 0 退到 5 m）。数据**已在 gt 里**（每立面族 `boundary_segments` 各带进深坐标）| **① 叠图已画** ✅（2026-08-21，绿线 + `depth a→b` 标注，与图纸自身那条线重合）· **② 显式元素 + 判卷计分仍缺** → 归 C2/判卷专项 |
| **⭐ 新 R-5** | **⛔ 全项目没有统一的房间类型词表**：gt 侧 `gt_schema.py:234 role: str`、pipeline 侧 `correction/schema.py:201 role: str = "office"` **都是自由字符串无枚举**；唯一的词表是叠图渲染器里那个**配色字典**（`office/meeting/corridor/reception/lobby`），两边谁都没引用它 ⇒ **表述不一致已是现实** | **登记**（2026-08-21 用户令）：建一套**全量房间类型表**，gt 与 pipeline 都从这里选；**下一个 case 落地** |
| **⭐ 新** | **房间类型（role）sm25 全为 `unspecified`**：叠图着色用的是 orchestrator 目视判定，**只进 `review_annotations`、不进 gt**。用户 2026-08-21：**下一个 case 起由用户填房间类型，届时 orchestrator 提醒** | **登记 + 提醒项** |
| **⭐ 新 F-67** | ⛔ **一个角部歧义洞口作废整份判卷，且长得跟「什么都没读对」一模一样**（F-64 家族）。sm25 1f 实测：15 个平面洞口里 **14 个候选唯一**，**1 个**在 `(15,20)` 转角处同时落进东墙 `x=15` 与北墙 `y=20` 的容差 ⇒ `reading_typed_score.py:410` 的处置是**把该组件的全部观测移除** ⇒ 平面频道 `not_applicable` ⇒ **37 条分段行全 miss**。sm24 是矩形，永远产生不了「两面外墙在转角同时入容差」⇒ 该路径从未被走到 | ✅ **已修**（sol 施工）：作废半径由**整个组件**缩到**单个观测**；⭐ **分母不动**（gt 派生，歧义观测无资格删 gt 目标——此处主控原写「移出分母」被 sol 推翻）；频道只汇总 disposition=`score` 的组件。4 把新锁含「歧义观测进分子必红」。实测：37 全 miss → **31 完整 / 15 miss / 1 多画**，`denominator_sha256` 逐字节不变 |
| **⭐ 新 F-68** | **`judge_score_bindings.json` 全仓没有生成器** —— sm24 那份是手工产的；sm25 一判卷就撞「required judge sidecar(s) are missing ⇒ v3 scoring layer was skipped」，**权威判卷被静默跳过**（跑测照常报 gate① 绿）| ✅ **已补** `scripts/tool_scripts/build_score_view_bindings.py`（平面已支持；⚠️ 立面绑定尚未实现，遇到时响亮报错而非产半份文件）|
| **⭐ 新 F-69** | ⭐⭐ **读图器「窗/墙垛」极性可以逐面墙各选一种，全链无门校验一致性**。sm25 1f 实测：北墙用「两块之间的空档」= 对；东墙用「检测到的块本身」= **7 个窗全部报成了墙垛**（两端逐个 ≤0.15 m 对上 gt 墙垛）⇒ 窗放对 8/15。⛔ 与 Z 形凹口/锚点定位无关；两种口径的差别**明写在 `note` 里**，属确定性可查 | **待定**（本轮候选修项；详证见本日「五之四」）|
| **⭐ 新 F-70** | ⭐⭐ **CV recipe 只有一个、色调窗口写死、零旋钮**：`recipes.py` 全仓仅 `clean_vector_v1`，掩膜 `R≈G≈B 且 60<v<230`，注释自述 seeded from **sm21** forensics。实测该掩膜看得见的前景：sm21 **68.3%** / sm24 53.0% / **sm25 24.8%**（sm25 按图层配色，70.1% 前景是彩色被 `rgb_tol=8` 排除；sm21 那个 v=128 灰墙体在 sm25 不存在）。⛔ **不得断言「对 sm25 失效」**——`wall_line_profiler` 在 sm25 仍返回 21/18 条候选（sm21 是 29/19）。成立的是：**同一把写死的尺子跨图纸看得见的东西差 2.8 倍，而没有第二个 recipe、没有旋钮、也没有任何门在图纸落到窗口外时报红**。与 F-65 同形。⛔ **并已排除它与 F-69 的因果**：实测现行灰掩膜在 sm25 上仍**正确定位东墙两条面线**（列投影峰值 px 964/975 = 真值），换成「任何非背景墨迹」掩膜只多出一个 957 峰 ⇒ **极性反了不是掩膜看不见造成的** | **登记**；⭐ 这正是 07-07 读图器一年前报的第 ⑥ 条反馈 |
| **⭐ 新 F-71** | **07-07 schema feedback 六条里四条至今未修**（结转 #4 已收，详见解剖档 §七之二）：~~① `anchor` 字段形状~~ ✅ 已修 · ③ 厚度 callout 无 `role`（枚举仍 `overall|segment|baseline`）· ~~④ 门 z 链非零底段~~ ✅ 已修（guide §2.1.1）· ~~⑤~~ ✅ 已修 · **剩 ③ 厚度 callout 无 role（改枚举，须派工）+ ⑥ = F-70**。②已修（无填充立面裁决在 `pen_library.md:26`）。⭐ 顺带确认 08-16 行为清单的 **D1（`local_x_positive` 自相矛盾）已修** | ✅ **①④⑤ 本轮已修**；剩 ③（枚举，须派工）与 ⑥（=F-70）|
| **⭐ 新 F-72** | ⭐⭐⭐ **现有链闭合门查「Σ段值==总长」，从结构上分不开「余量放对」与「余量丢掉」**。实证：07-07 与 07-08 对 sm21 顶链转录**逐字相同**（段和皆 14.76、总长皆 15.00，差 0.24 m）；07-07 把余量放进两条 120 mm 无标注隔墙带、末段收在 **15.00**；07-08 首尾相接、末段收在 **14.76** ⇒ 窗依次偏 −0.12/−0.24 ⇒ **6/7**。⭐ **新判据 = 落位闭合**（链摆到图上的跨度必须等于其声称总长），实测好夹具 4/5 绿、07-08 红（**红得对**）、坏夹具 F1+G1 命中 | **待拍板**：需同时引入夹具 `known_defects`（好夹具允许被红，当且仅当红的是已登记缺陷）|
| **⭐ 新** | **cv_evidence 归档的仓库增长**：实测 07-07 sm21 一份 **12 MB**，其中 JSON 侧车仅 **984 KB**、overlay PNG **11 MB**（92%）。⭐ 08-21 那整轮解剖**只读了 JSON、一张 overlay 都没开**；但 overlay 的真实消费者是**人工目视复核**，故两者都留、并把 `total_bytes` 记进 provenance ⇒ 增长可见而非静默 | **登记不做**（§0.1）；若日后仓库变重，从这个数字下手 |
| **⭐ 新 F-73** | 过程门 NARROW-OPENING 用**浮点严格小于**比 0.60 m：`10.9 − 10.3 = 0.5999999999999996` ⇒ **一扇图纸明写 600 mm 的窗被判成「窄得不可能」**，一份正确 reading 被门判红 | ✅ **已修**（改按毫米比较，域下限一毫米没动）+ 2 把锁；**neuter 实测**摘掉修复该锁即红 |
| **⭐ 新 F-74** | gate① 的 `reading.view_manifest_coverage` 在 **flat-flow 路径**上不传已冻结的 `reading_exam_scope`（[run_stage.py:385](../scripts/tool_scripts/run_stage.py#L385) 与 [validation_run.py:314](../src/agent/execution/validation_run.py#L314) 都略掉了该参数）⇒ 声明只考两张图的 run **必然 BLOCK**；隔离壳 merge 路径会传 ⇒ **同一份声明、两个入口、两种判决**。⛔ **本条曾附一句「另：`check_view_manifest_merge` 全仓零生产调用者」—— 那是我编的**：我把 `check_reading_stage` 的 docstring 里那句描述性的「merge 同门 checker」当成了函数名，并当作实测事实写进三份文档。**代码中从来没有过这个函数**（GLM 跨家族审 MINOR-1 抓出）。隔离壳路径其实一直是 `isolation.py:823 → check_reading_stage(exam_scope=...)`，修复前就传了 —— 「两个入口两种判决」这个结论本身成立，编造的只是那句附注。 | ✅ **已修**（两个调用点各补传已冻结的应试范围）+ 2 把锁（含「范围内缺图仍须 BLOCK」反向锁）+ neuter 实测 |
| **⭐ 新 F-75** | flat-flow 把 attempt 产物写成裸 `{stem: view}` 而非 `{"views": {...}}` 的 ReadingViews-v2 信封 ⇒ `identify_reading_contract` 判 `unrecognized` ⇒ **权威 typed 判卷静默降级成 `not_applicable`**（F-68 同形、F-64 同族）| ✅ **已修**（两个调用点各补传已冻结的应试范围）+ 2 把锁（含「范围内缺图仍须 BLOCK」反向锁）+ neuter 实测 |
| **⭐ 新 F-76** | v3 答案无法被 legacy 判卷器读（`gt_v3_requires_typed_consumer`），而 `score_reading_vs_gt.py` 把该异常**报成误导性的「could not map image to a gt floor; pass --floor」**。F-75+F-76 合起来 ⇒ **当前没有任何一条可用命令能给 flat-flow 产物判分** | ✅ **已修**（判卷接缝补上 flat→v2 信封归一化，与既有反向归一化互为镜像）+ **走真实入口的接线锁** + neuter 实测（⚠️ 第一版锁只测 helper、摘掉接线仍绿，已重写） |
| **⭐ 新 F-77** | `cv_probe.py --sidecar-name` 只接受 `NNN_tool` 形式而 `--help` 只字未提，报错在栈底才现形 | **登记**（一行 help 文本）|
| **⭐ 新 F-78** | 墙带厚度取面线质心间距（像素），**未吸附到图纸声明的 240/120**：sm25 1f 量出 0.237–0.249 / 0.110–0.125，**2f 出现 0.131 / 0.146 两个不存在的厚度** ⇒ 那两条八成是错配的墙带，而**没有任何门会因此报红** | **登记**；修法与洞口同形（吸附+残差记账+超容差报红）|
| **F-71③ 实战现形** | 孤立的**墙厚 callout 在当前 schema 里没有合法形态**：`dimension_chain_closure` 要求每个 `chain_id+axis` 组同时有 overall 与有序 segment，且 dimensioned 视图每条 dimension 都必须有 `chain_id` ⇒ **忠实转录「240」的读图器过不了 gate①** ⇒ 门在教读图器丢真标注（[[rule-without-legal-exit-breeds-invention]] 同族）。⭐ **07-07 那份 sm24 好 reading 同样会被拦**（它的 `C_thickness_callouts` 也只有 segment）| **待派工**（改 schema 枚举）|
| **⭐ 新 F-86** | **一条面线的一整段被静默丢掉**：`as_drawn_v2.py` 的 `_ink_groups` 用 `along = keep[:, g].mean(1) >= FILL_RATIO` —— 某段墨迹只要**不是列组内多数列**都有，整段就被丢。实测 sm25 2f 列 655 在第 1080–1249 行有 **170 px** 墨迹，所在组是 653–656（4 列）⇒ 0.25 < 0.5 ⇒ 丢 ⇒ **该隔墙只有一个面进产物**（`L012` 最近的候选伙伴在 3.795 m 外）。⭐ 是**认**的时候撞出来的：不硬配就得给它一个说法 | **登记**（2026-08-24）。⛔ **候选修法 `max(1)` 已实测但不采纳**：sm25 gt 侧 93.3→**94.7**、sm24 仍 100.0，**但 sm24 有 5 个洞口断口被整个填平**（实心带方言里一列门垛就补上了）⇒ **会静默 heal 洞口**。正解 = 按 run 兼容性拆分列组 |
| **⭐ 新 F-87** | **门窗身份没有外置**：本批指南把「这洞是门还是窗」判给 reading 的模型，但 perception 的六个桶里**没有逐洞口 / 逐组件的 opening 身份桶**；现行代码只做「门窗族墨迹够多 ⇒ 这段空档可桥接」的二值判断，且该判断长在评分器里（`_extent`）。⇒ 「认」还有一块留在代码里 | **登记**（2026-08-24，跨家族三审 Q3(b)#4 指出，主控复核属实）· 归 B 步前置组第 3 项 |
| **⭐ 新 F-88** | **转换器把真墙面片段误判成门垛**：门垛识别只看长度（落在墙厚区间 [0.06,0.50] m 即算），而 sm25 走廊墙连着 7 樘门、**门与门之间的真墙面只有 0.36 m** ⇒ 实测 sm25 1F 长度规则排 **124** 条、按几何（必须横跨两条对向面线）只应排 **65** 条 ⇒ **59 条真墙面被删**。后果之一：45 个 `wall_bands` 里 **32 个厚度 > 0.25 m**（0.30×16 / 0.36×11 …），而该图只声明 240 / 120 | **已查清**（2026-08-24 夜，`tools/f88_probe.py` 只读探针）：**症状坐实** —— 已签字 gt 的转换报告里 84 条墙厚证据有 **60 条 > 0.25 m**（0.30×32 / 0.36×22 …），来源全是 `wall_cap_or_opening_jamb`。**影响实测 = 无**：把门垛判定换成几何判定重跑同一份转换（sm25 移除 119/244 个门垛、sm24 移除 23/73），**房间多边形逐字节相同**（29 / 8 个）⇒ **污染的是溯源记录那一层，没挪动答案几何，历史成绩不作废**。⭐ 探针自带「补丁生效证明」。**仍应修，但不是 gt 准入阻塞项** |
| **⭐⭐ 新 F-89** | ⛔ **多层立面的 reading 判卷从未实现，且失败方式是静默整份过滤**：[`reading_typed_adapter.py:667`](../src/agent/judge/reading_typed_adapter.py#L667) `if len(floor_ids) != 1:` ⇒ 一张立面图只要跨两层，该视图的**全部** elevation 组件被打成 `not_applicable` / `elevation_floor_partition_unresolved`（`cause_class=trusted_input`、`denominator_disposition=filter`）。sm25 是**两层**，四张立面每张都覆盖 F1+F2 ⇒ **四张立面全被丢**，`window_elevation_geometry` / `floor_lines_complete` 一律 `not_applicable`。⭐ **后果**：C2 的另一半「立面多平面」**至今一次都没被判过分**，而 sm25 正是第一个多层非矩形 case。⛔ 与 F-65（立面窗只认 LINE）不同族：那条是**产不出窗**，这条是**产出了但判卷不收**。实测 2026-08-25 重判 `run_2026-08-25_c2_rescore_R0`，绑定六图全建成、`content_sha256` 与 08-22 那次逐位相同 ⇒ ⛔ **不是缺绑定** | **登记**（2026-08-25）· 阻塞「C2 立面侧验收」，⛔ 不阻塞平面侧 |
| **⭐⭐ 新 F-90** | ⛔ **correction 侧判分对多层 case 整份被拒，真因是楼层 id 两套命名且无映射层**：判分绑定用 gt 的命名 `floor_id="F1"/"F2"`，而 correction 产物的窗用管线内部命名 `floor_id="floor_1"/"floor_2"`；[`score_service.py:371`](../src/agent/judge/score_service.py#L371) `plan_sources.get(window.floor_id)` 取不到 ⇒ 抛 `score_view_binding_invalid`（gate `scoring.view_bindings`）⇒ `score_vs_gt.payload.kind="rejected"`，**十个判据一个都没跑**。⭐ 与 **F-89 是一对**：F-89 让立面侧判不了、F-90 让 correction 侧判不了 ⇒ **C2 批两侧至今都没有被判过分**。实测 2026-08-25 `run_2026-08-25_c2_rescore_R0`（gate① 反而是零 block 零 flag 通过的）⭐⭐⭐ **2026-08-26 跨家族补审 = REJECT**（GPT `gpt-5.6-sol`/xhigh）→ [裁决](logs/reviews/verdict/2026-08-25_f90_floor_id_mapping_gpt_verdict.md)。**阻断点 = 同根因还有第 6 处未修**：`score_typed_attempt` 在楼层桥建好之前（[`score_service.py:389`](../src/agent/judge/score_service.py#L389) vs 桥在 `:431`）就调 plan segment matcher，而 matcher [`segment_score.py:1751`](../src/agent/judge/segment_score.py#L1751) 直接比 `target.floor_id != observed.floor_id`。**orchestrator 已独立复跑坐实**：同一份几何、只把楼层名 `f1`→`F1`，从 `16 m extra + 16 m miss` 变成 `16 m complete`。⭐⭐ **由此推翻施工那份十判据读数的意义**：那唯一 eligible 的 `boundary_complete=0/32` **就是这第 6 处的读数**，不是产物的错 ⇒ 我拿到的是「九条没判 + 一条判的是自己的 bug」（正是请求单第 2 条我自己标注的最弱点，答案比我猜的更糟）。另有阻断项 3 条 → **F-100 / F-101 / F-102**（见下）| ⛔ **REJECT，未闭合**（2026-08-26）· 处置 = 在 `main` 上另开修复单，⛔ 不回退历史 |
| **⭐⭐⭐ 新 F-91** | ⛔ **C2 的「立面多平面」在 correction 产物里是空的，窗因此无法定位**：sm25 实测 `facade_segments = 0`、**31/31 扇窗的 `facade_segment_id` 全为 `null`**。⭐ 而 L 形上「北」「东」各自**不是一道墙**：朝北的有 y=20(x 0→15) 与 y=6(x 15→25) 两道、进深差 14 m；朝东的有 x=15(y 6→20) 与 x=25(y 0→6) 两道、进深差 10 m。实测 F1 北面有一扇窗 span=[15.3,23.3]，**完全落在 y=20 那道墙的范围之外**（那道墙只到 x=15）⇒ 它属于 y=6 那道，但没有任何字段这么说 ⇒ 渲染器与下游只能猜，窗被画到楼外（用户 2026-08-25 目视发现「窗户没在位置」，orchestrator 复核属实）。⭐⭐ **沿墙数值本身是全对的**：31/31 扇与 gt 的 `world_along_interval` 两端误差合计 **0.0 m** ⇒ ⛔ **不是算错，是没绑定**。⚠️ **2026-08-25 晚补注（免得两个数打架）**：当天「答案直喂内核」的诊断里测到 `facade_segments` = **16 条非空** —— ⛔ **那不构成本条已消失的证据**，两者输入不同：本条测的是 **R0 的真实 correction 产物**，那次测的是**从 gt 机械派生的输入**。⇒ 只能说明「立面段在答案输入下产得出来」，⛔ 不能说明「模型产的那份为什么是空的」。 | **登记**（2026-08-25）· 这是 C2 阶梯表里 C2 那一行的「立面多平面」本体 |
| **⭐⭐ 新 F-92** | **cell 多边形能力未被使用**：sm25 实测两层 38 个 cell 的 `polygon` **全为 `null`**，全部是 x/y 矩形区间。⭐ 后果不是「切错了」——实测 F1 19/20、F2 18/18 的 cell **≥95% 落在单一 gt 分区内**、零 cell 越界、零 gt 分区漏覆盖；真正的差别是 **gt 把整栋走廊建成一个 18 顶点连通多边形，correction 把它拆成 7 个矩形**。⚠️ 并注意 gt 自己也几乎全是矩形（F1 13/14、F2 14/15 是四边形），⛔ 所以「矩形化」本身不等于错，错的是**非矩形的那一个（走廊）无法表达** | **登记**（2026-08-25）· C2 阶梯表「cell 多边形」本体 |
| **⭐⭐⭐ 新 F-93** | ⛔ **全仓已红 4 项且两天无人发现，四项同源 = gt 重签后锁与夹具没跟着更新**。2026-08-25 主控权威全量实测：**3010 passed / 1 failed / 3 errors / 13 xfailed**（⛔ 不是 CLAUDE.md §1.3 仍写着的「2835 绿」）。**已在昨天的提交 `f7d64f4` 上复跑，同样 4 项红 ⇒ 与今日工作、与工具箱转正均无关。** 逐项：① `test_elevation_score_bindings::test_generator_fails_closed_on_sm25_multi_floor_fingerprint` —— 它 assert「两层 footprint 指纹不一致时生成器必须 fail closed」，而 **08-22 用户拍板的 S1 修法正是让指纹逐位一致**；实测 sm25 两层指纹与顶点均**逐位相同** ⇒ **锁的前提已被修没了，锁是陈旧的，⛔ 不是生成器回归** （同族 [[regression-case-must-prove-its-own-premise]]）。⭐ **推论：orchestrator 2026-08-25 用该生成器建的六图绑定是合法的**。② ③ ④ `test_reading_typed_score_f67` 三项 ERROR = `score_view_binding_invalid / identity mismatch`：夹具指向的 `run_2026-08-21_c2_first_sonnet_T1` 记的 `gt_content_sha256=f97cea65…`，而当前 gt 是 `135b282c…`。⭐ **时间线**：锁改于 `96604c9`(08-22)、gt 改于 `e982eba`(08-23) ⇒ **gt 晚于锁一天入库，锁没跟着走**。⚠️ **治理后果**：期间所有「全仓绿」的说法都是失效的口径 ⭐ **✅ 2026-08-25 晚闭合**：施工 `b3e0a32`（Claude 席位）· **GLM 跨家族 APPROVE-WITH-FINDINGS** → [裁决](logs/reviews/verdict/2026-08-25_merge_blockers_f93_f94_glm_verdict.md)。**全仓恢复全绿：`3014 passed, 13 xfailed`（GLM 自己跑的，EXIT=0）**。1-a 保留锁、换成真正满足前提的合成 gt；1-b 走了派工单没给的第三条路（现场对当前 gt 重建绑定、只写 tmp、不动历史 run、不换被测对象）。⛔ 剩 3 条不阻塞 findings 见裁决 §五 | **✅ CLOSED**（2026-08-25）|
| **⭐⭐ 新 F-94** | ⛔ **venv 里的 editable-install `.pth` 硬编码指向主树，合并回主线后会从「响亮失败」变「静默串台」**：`/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth` 内容 = `/workspaces/EnergyPlus-Agent-dev`（主控实测确认）。后果：在**任何非主树的工作树**里**裸跑**（非 `-m`、非 pytest）一个 `from src.xxx import …` 的脚本，若脚本自身目录下无 `src/` 包，`src` 会**静默从主树解析**。⭐ 由施工席位在转正工作中撞出并用探针实测复现；跨家族审（GLM）独立确证根因链：脚本模式 `sys.path[0]`=脚本目录 → `src` 落主树 → `REPO_ROOT` 指错树 → 路径守卫 raise，并实测受影响面三项（探针 / `inspect_dxf` 两测试 / `reading_toolbox` 裸跑 `ModuleNotFoundError`）。⭐⭐ **GLM 判定为合并前必须处理项**（合并后同名文件在两棵树都存在，踩坑不再报错、改成静默用错那棵树的代码）⭐ **2026-08-25 晚：方案已出并经 GLM 审「合格」**（三候选覆盖三个规定维度，事实基础抽查属实 —— `scripts/` 32 个脚本恰 6 个含自举）：**A** 扩展现有自举模式（改 26 个文件，机械低风险，⛔ 但不移除 `.pth`，交互式 `python -c` 仍串台）· **B** 删 `.pth` + 强制 `-m`（裸跑从**静默串台**变**响亮失败**，⛔ 但破坏 ≥15 处文档化命令）· **C** 按树设 `PYTHONPATH`（⛔ 最弱，全靠人记得 source）。⭐ **GLM 补充意见：长期应对齐 B，A 只是收窄暴露面不消除机制；A+B 组合应作为正式建议呈用户拍板**（涉共享环境）⭐ **✅ 2026-08-25 晚：A 案已闭合** —— 施工 `91ae82d`（16 脚本各 +5 行自举 + 新增 AST 机械锁）· **GLM 跨家族 APPROVE-WITH-FINDINGS** → [裁决](logs/reviews/verdict/2026-08-25_f94_bootstrap_glm_verdict.md)· 全量 **`3016 passed, 13 xfailed`**（GLM 自己跑的）。**B 案 = 债 D-2（中高紧迫）** | **✅ A 案 CLOSED**（2026-08-25）· 合并阻塞已解除 |
| **⭐⭐ 新 F-98** | ⚠️ **08-23 那次 gt 重签做的是一次【全局浮点清理】，而它足以改变判分结果 —— 派工单把这件事说小了**（**第 24 次「停下上报」，仍是派工方题错，累计 24/24**）。派工单把 F-93 1-b 定性为「夹具指向了旧哈希」；施工席位上报「不只是哈希，几何数值本身也变了」。**orchestrator 独立复核，规模比它说的还大**：`e982eba~1` vs 当前，F1/F2 外轮廓**各 8 个顶点全部改变**、zone 顶点 **136 个全部改变**，模式为 `13.999999999999996→14.0` · `-3.55e-15→0.0` · `4.9999999999999964→5.0` · `16.06→16.060000000000002` —— **同一真实点、更干净的浮点表示**。⭐⭐ **真正值得警惕的推论**：一次**纯粹的浮点末位清理**竟能让 T1 那份真实识图产物重新判分时**多出一条 support-line 并列歧义**（1 opening+1 segment → 1+2）⇒ **判分在容差边界上对浮点末位敏感**（施工席位定位为落在 `plan_position_tol_m=0.30` 内的「轴线 vs 外皮」半墙厚老问题的又一现形）。⛔ **本条不是「gt 重签错了」**（清理后的值更干净、更接近真值）；要盯的是**判分结果会随无害的表示变化而漂移**这件事 | **登记**（2026-08-25，施工席位上报 + orchestrator 独立复核确证）· ⛔ 修法碰 `src/agent/judge/` 须派工 |
| **⭐⭐ 新 F-99** | ⛔ **产物的立面段与 gt 分段边界在 L 形内角处差约 `0.12 m`，16 段里 8 段不归位** ⇒ 判分报 `score_product_segment_unresolved`。**由 F-90 施工席位撞出并如实上报**：修完楼层 id 映射的全部 5 处后，sm25 R0 **仍判不出分**，卡在这一条。⭐⭐ **`0.12 m` = 半个 240 墙厚** ⇒ **与本日查明的「基准换算」同源**（gt 是「外墙外包 + 内墙中轴」而 correction 全程中线，见「三之二」）。⭐ **席位的处置值得记**：⛔ **没有用调容差遮过去**（「那会是**阈值调硬 ≠ 判据重算**的老病」），而是用干净 fixture 拿到十判据读数证明 F-90 已修好、再用报错码从 `score_view_binding_invalid` → `score_product_segment_unresolved` 的变化证明卡在另一处 ⇒ ⚠️ **推翻了派工单的前提**（「修好 F-90 就能让 sm25 判出分」），**第 28 次停下上报、仍是派工方题错** | **登记**（2026-08-25）· ⛔ 碰 `src/agent/judge/` 须派工 · ⭐ 归「撞 sm25/C2」阶段，与 F-91/F-95 同批 |
| **⭐⭐ 新 F-97** | ⛔ **新识图产物会被当原始文本喂进校正提示词，同时绕过识图门 —— 一条沉默路径**：`discover_vector_files`（[pipeline.py:84-107](../src/agent/pipeline.py#L84)）扫 `*.json` **全部**并分成 plans / elevations / **`others`**（= 不匹配平面图正则、且不以 `_view.json` 结尾的所有 JSON）⇒ 一份 `sm25_1f_v2.json` 放进 `0_reading/` 会落进 `others` 并进提示词；而识图门 [`evidence_preflight.py:229`](../src/agent/execution/evidence_preflight.py#L229) 只 `glob("*_view.json")` ⇒ **看不见它**。⭐ **由 GPT 跨家族设计答复点出，orchestrator 已独立复核两处代码 + 做了行为实测**（⛔ 不是只读代码）：把 `1f_view.json` 与 `sm25_1f_v2.json` 并排放进一个 `0_reading/`，`discover_vector_files` 返回 **`['1f_view.json', 'sm25_1f_v2.json']`** ⇒ **as-drawn 产物确实会进 correction 的输入**；同一目录上 `compute_reading_report_from_vector_dir` 跑了 **21 项检查、0 阻塞** ⇒ ⭐⭐ **门不只是看不见它，还给出了绿灯** —— 比「看不见」更糟。⛔ **它比「喂不进去」严重**：喂不进去是响亮失败，这条是**静默地半喂进去**。⇒ 一体改的**契约判别器**必须显式化：未知契约类型响亮失败 | **登记**（2026-08-25）· ⛔ 碰 `src/agent/pipeline` 须派工 |
| **⭐⭐⭐ 新 F-95** | ⛔ **顶点规范化把凹多边形毁掉，而校验器与生产者共用同一个实现**：[`canonicalize_ring_vertices`](../src/validator/data_model.py#L1047) 用**绕质心角度排序**重排环，对凸多边形能还原、**对凹多边形还原成另一个形状**。离线夹具 [`concave_canonicalization_matrix.py`](logs/experiments/2026-08-25_kernel_probe_from_gt/tools/concave_canonicalization_matrix.py)（不需 gt/LLM/跑抽）：矩形 **OK** · 单凹角 L 形 84.000→84.000 **OK** · **U 形 8 顶点 76.000→70.000** · Z 形 8 顶点 68.000→68.000 **OK** · **梳形 12 顶点 66.000→59.000** · **sm25 走廊 14 顶点 97.731→226.457**。⚠️ **该表当场证伪了 orchestrator 初稿的断言「两个及以上凹角就坏」—— Z 形 2 凹角却无损** ⇒ **凹角数不是判据**，判据是「顶点绕质心的极角是否单调」，凹是**必要非充分**条件 ⇒ ⛔ 按「有没有凹角」挑回归夹具会挑出假绿的那一半。实测后果：`Z10_F1_Office_S` 地板面积 **226.457 vs 自己的轮廓 97.731**（2.3 倍）、`Z22_F2_Office_SW` 174.332 vs 78.558 ⇒ `kernel.zone_closure` 4 条阻塞。⚠️ **规范化后的环仍 `is_valid=True`** ⇒ 任何"多边形有效性"检查都放行，**只有面积对账抓得住**。⭐⭐ **两条附带教训**：① 已有的 `test_lshape_polygon_clean` 断言的正是那个**恰好无损**的单凹角 L 形 ⇒ **有锁 ≠ 有分辨力**（[[neuter-proves-wiring-not-discriminating-power]]）；② kernel 与 validator **刻意共用**这一实现（build.py 注释：避免 F-13 两套算法分歧）⇒ 校验器与生产者共享同一个错误假设。⭐ **打击面已界定**（`grep` 清点调用点）：生产侧 [`build.py:78`](../src/agent/geometry/build.py#L78) 对**每个面**、[`:84`](../src/agent/geometry/build.py#L84) 对**每扇窗**各跑一次；校验侧 [`data_model.py:1338`](../src/validator/data_model.py#L1338) 与 [`checks/kernel.py:398`](../src/validator/checks/kernel.py#L398) **用同一个函数**。⇒ ⭐ **实际受害的只有凹多边形 zone 的 Floor/Ceiling/Roof** —— 墙面与窗都是矩形（凸），规范化对它们无损。**这与实测自洽**：`zone_closure` 报的正是 `floor_area` / `top_area`，⛔ 没有一条 wall 告警。⇒ 修法的回归面应据此收窄。⭐ **现行管线撞不到它**：R0 的 38 个 cell 带 `polygon` 的 = **0**（全 bbox=凸）⇒ 与 **F-92 是一对**（多边形能力没被用，所以它的缺陷也没被暴露）| **登记**（2026-08-25，答案直喂内核撞出）· ⛔ 碰 `src/validator/`+`src/agent/geometry/` 须派工 |
| **⭐⭐ 新 F-96**<br>⭐ **2026-08-27 并入 F-95 审的 N1**：唯一残余理论窗口 = shapely 布尔运算产物自带**精确重复顶点**的环（13 配置电池含全部 F-96 碎片宽度**未触发**；且旧实现在同一形态下**同样把坏环静默送进 IDF**）⇒ 与本条一起守卫，⛔ 不单独开工 | ⛔ **跨层切分产生的碎片没有守卫，而同层吸附还把它做得更小**：1F 一道隔墙中轴 `y=15.9996`、2F 对应 `y=16.06`。⭐ **已溯源到原始 DXF 逐条坐标**（`sm25-L_t3.dxf` `WALL` 层，mm）：1F 右半段两条面线 44153.221/44273.221、其余三处（1F 左半段 + 2F 两段）均为 44213.552/44333.552 ⇒ **四处厚度都是 120，错位的是位置：1F 右半段那道墙整体往南偏 60.3 mm** ⇒ ⛔ 既不是转换器造的、也不是噪声、更不是两种墙厚，**原图就这么画的**，gt 忠实转录。确定性核第二步破坏第一步 —— ① 跨层对齐判 `provenance-aware sliver guard kept axes separate`（delta=0.0，决定不合并）；② 同层吸附随即把 1F 那条推到 **16.03**（delta=0.0304，`AXIS_JITTER_TOL+SNAP_GRID+MIN_EDGE_LENGTH`）⇒ 间距 0.0604 **缩到 0.03**，方向正朝着它刚判定要保持分离的那条轴。跨层切分于是切出 **0.03 m 宽**天花/地板条，InterZone 门事后报 `degenerate surface … EP may segfault`。**三点判别**（只改这一个量）：0.0604→2 条 · 抖动归整 0.0600→**仍 2 条**（⇒ 与 0.4 mm 抖动无关）· 拉到 0.20→**0 条** · 完全对齐→**0 条**。⭐ **别记错主因**：0.06 本来就 < 碎片下限 0.1，**不挪也会出碎片** ⇒ 主因 = **跨层碎片无守卫**，吸附朝错方向挪只是**加重因子** | **登记**（2026-08-25，同上）· ⛔ 碰 `src/agent/correction/deterministic.py` 须派工 |
| **⭐⭐ 新 F-100** | ⛔ **correction 判分路径没有接 score binding 的 source-view 桥，真实 gt 的 `source_refs` 一到就静默全 miss**：[`score_service.py:469`](../src/agent/judge/score_service.py#L469) 直接把 observation 交给 `assign_openings`，而 [`opening_claim_score.py:351-364`](../src/agent/judge/opening_claim_score.py#L351) 要用 `input_id → gt_source_view_ids` 过滤。⭐ **正确接法本仓库已有先例**：[`reading_typed_score.py:512-534`](../src/agent/judge/reading_typed_score.py#L512) 就是这么做的 ⇒ 两条路走了两套。复核方实测：`without_binding_bridge matched 0 / target_miss 1` vs `with_binding_bridge matched 1 / target_miss 0`。⭐⭐ **它此前一直躲在 F-90 的施工 fixture 后面** —— 那份 fixture 把 gt 的 `source_refs` 造成空元组（[`test_c2_b5_parent_and_verts.py:1455-1472`](../tests/test_c2_b5_parent_and_verts.py#L1455)），于是过滤器根本没被行使 ⇒ 同族 [[feed-the-answer-in-to-test-the-code-alone]] 的反面：**夹具把答案造成了不行使能力的形状** | **登记**（2026-08-26，GPT 跨家族补审 finding 3）· ⛔ 碰 `src/agent/judge/` 须派工 |
| **⭐⭐ 新 F-101** | ⛔ **合法的 `src:<64hex>` 溯源 locator 被 F-90 新映射器当成未注册输入拒掉**：[`window_sources.py:952-957`](../src/agent/correction/window_sources.py#L952) 白纸黑字声明**两种合法形式**（① 已解析的 `src:<64hex>` 直通 ② `<expected_output_id>/<observation_id>`），而新映射器 [`score_service.py:200`](../src/agent/judge/score_service.py#L200) 一律 `split("/", 1)[0]` ⇒ 整串 hash 被当 `input_id`，落进 `window_host_source_not_a_registered_plan_input`。复核方实测：一个带 `src:<hash>` host 引用的 B5 bundle **成功产出 `VerifiedWindowHostProof`**，随后 scorer 拒绝它。⭐ **这是第 3 条「派工方题错」**（派工单暗含前提「host `source_ids` 总能按 `/` 拆出 input id」，该前提不完整）。⛔ 不是坏输入被挡住，是**合法输入被挡住**；修法 = 从已复验的 `window_host_proof` / `window_resolver_inputs` catalog 把 locator 解析回 source input | **登记**（2026-08-26，GPT 跨家族补审 finding 4）· ⛔ 碰 `src/agent/judge/` 须派工 |
| **⭐⭐⭐ 新 F-102** | ⛔ **判分语义改了、缓存 identity 没改 ⇒ 官方 run-stage 会继续命中修复前的旧 sidecar**：复核方在真实 R0 上实测 `live = not_applicable/unsupported_view_contract`（已走到 F-99）、`cache_hit = True`、`cached = rejected/score_view_binding_invalid`（= **修复前**的结论）、`same_identity = True`。位置：[`score_service.py:269-278`](../src/agent/judge/score_service.py#L269) · [`score_schema.py:1665-1691`](../src/agent/judge/score_schema.py#L1665) · [`run_stage.py:2176-2181`](../scripts/tool_scripts/run_stage.py#L2176)。⭐⭐ **治理后果比缺陷本身重**：F-90 修没修好，**从官方跑测口子上看不出来** —— 走 `flow` 拿到的仍是旧结论。⇒ 同族 [[cache-in-front-of-a-gate-is-a-second-entrance]]（「我验的是这道门，还是绕过它的那条路」）+ [[version-number-is-not-behavior-attestation]]。修法 = 给 correction floor/source normalization 版本化 helper identity + 补一把「旧 sidecar 必须 cache miss」的回归锁 | **登记**（2026-08-26，GPT 跨家族补审 finding 5）· ⛔ 碰 `src/agent/judge/` + `scripts/` 须派工 |
| **⭐ 新 F-104** | ⚠️ **同一个 attempt 目录里存着两份不一致的几何，且都被跟踪**：`1_correction/attempts/001/output.json`（accepted，核后）两层 cell 对 footprint **零 gap 零 overhang**；而同目录 `window_resolver_inputs.json` 内嵌的 `producer_draw_canonical_bytes`（核前草图）`floor_2` 的 symmetric difference = **0.12515 m²**（`(0.12,14.12,5.13,14.125)` 0.02505 + `(14.88,5.88,24.89,5.89)` 0.10010）。⭐ **大概率是设计如此**（确定性核在 LLM 草图之后跑，两份本就该不同），⛔ **所以本条先记成观察项、不记成缺陷**。**值得盯的点**：窗户 host proof / resolver-input catalog 是**对着核前草图**认证的，而被判分的 plan segment 来自**核后产物** ⇒ 若确定性核哪天会重排/重编楼层，F-90 那条桥的 rank 依据就会与认证依据脱节（当前 rank 取自 accepted 产物的 `z_floor` 排序，故**现在是安全的**）。⭐ 附带教训见本日「五之三」：orchestrator 只核了「坐标在不在 accepted 产物里」就断言了它**来自哪里**，被对方证据当场推翻 | **观察项**（2026-08-26）· ⛔ 未证实为缺陷，先请审阅方判 |
| **⭐ 新 F-105** | **reading 侧的「判不出分」原因文本语义变了，但 reading 的 helper 版本没跟着提** ⇒ **旧 sidecar 会 cache 命中并返回旧值**：F-103 把 `not_applicable` 分支的 `detail` 从粗分类 `reason` 改成了具体 `error.code`（[`score_service.py:899`](../src/agent/judge/score_service.py#L899)），而该函数 `_total_failure_result` **reading / correction 两 stage 共用**（调用点 `:1003` / `:1010`）；correction 侧的 `opening_matcher` 已提到 v5，**reading 侧恒为 `reading_opening_global_assignment_v1`**（[`score_schema.py:53`](../src/agent/judge/score_schema.py#L53)）。⭐⭐ **这是 F-102「语义变了 identity 没变」的微型重演**，同一天、同一个包里又长出来一次 ⇒ 佐证 GLM finding #3 的判定（**手工版本号是执行机制不是根治机制**）。**当前无实害**（`detail` 全仓零代码消费者，GLM 已扩面 grep 确认）。**处置**：下次动 reading 判分语义**必须**升 `READING_OPENING_MATCHER_HELPER_VERSION`；或现在就升一档 + 补一把「旧 reading NA sidecar 必须 cache miss」的锁 | **登记**（2026-08-26，GLM 跨家族审 finding 2）· ⛔ 碰 `src/agent/judge/` 须派工 |
| **⭐ 新债 D-2** | **装机路径的根治（B 案）= 工程维护债**（用户 2026-08-25 拍板：「按你的推荐，这个 B 登记到工程维护债上」）。**A 案先做止血**（给裸跑脚本各加一行自举，⛔ 只收窄暴露面**不消除机制**）；**B 案 = 删掉共享 `.pth` + 全部入口改走 `python -m`**，届时踩坑从**静默串台**变**响亮失败**。⛔ **代价即它成为债的原因**：破坏 ≥15 处已写进 `guides/` 的裸跑命令 + 各席位的手指记忆，须一次系统性迁移。⭐ **GLM 独立意见与此一致**：「长期应对齐 B，A 只是收窄暴露面、不消除机制」。⭐⭐ **2026-08-25 GLM 复核明确裁定：紧迫度⛔ 不因 A 案的机械锁降低** —— 「那道锁把 A 从**约定**变成了**机制**，但只是**执行机制**（enforcement），不是**根治机制**；『真正的机制性根治仍然只有 B』**一字不改**」。三条实测据：① `.pth` 注入机制**原样活着**（实测在 `sys.path` 末尾 index 5）· ② **锁的覆盖边界 = A 的收窄边界**，覆盖外有**现成活例** `tests_scripts/deepseek_review.py:28`（模块级 src 导入 + 无自举 + docstring 文档化裸跑，在 worktree 里跑就静默串台，锁对此沉默）· ③ 锁**只验形态不验参数**（`parents[N]` 层数写错则锁绿而串台依旧）。⇒ ⭐ **准确表述：锁 = 在一个枚举过的暴露面上，把「忘关门」从静默变成响亮；它机制化了「A 的完备性不退化」，⛔ 没有也不可能机制化掉串台本身。** | ⭐ **中高紧迫**（GLM 定：**本批收尾前后排期，⛔ 不写「远期」**）—— 多席位 worktree 是常态（当前挂着 3 棵树），每次开树都在 A 覆盖外的入口冒险；而 B 成本不高（删 `.pth` + 全走 `python -m`），**收益是整个缺陷类目消失**。退役须另开单 |
| **⭐ 新债 D-1** | **`tools/` 原件与 `src/` 新件双份并存**：跨家族审裁定 (a) 接受双份 + 登记 + **限期退役**。成因是 `glm_cheats.py`/`glm_rework.py`/`glm_probes.py`/`glm_sweeps.py` 用 `spec_from_file_location` **按文件路径**加载被搬走的模块，删原件会炸掉五轮跨家族审累积的全部作弊夹具。⛔ 与「不两处并存」冲突，**日后改一份忘另一份是必然的**。⇒ 退役动作 = 夹具改成按模块加载，**须另开单** | **登记**（2026-08-25）|
| **⭐⭐ 新 F-106** | ⛔ **gate① 的检查报告正被反向喂进 correction 的提示词**：`*_checks.json`（`stage_check_report`：无 `schema` 键，含 `stage`+`results`+`report_schema_version`）住在历史 run 的 `0_reading/` 里，而 `discover_vector_files` 把它归进 `others` ⇒ `pipeline.py` 逐份原样贴进提示词。实测 `case_tests` 下 `0_reading/**` 有 **108** 份带 `report_schema_version` 的 JSON（施工席位按 `0_reading/` 根目录口径数到 **43** 份）。**现代 run（sm25 R0 / sm21 2026-08-20）的 `0_reading/` 根目录已无边车 ⇒ 现网 live 路径干净**，但任何历史目录被重放、或先跑 `validate_case(write_reports=True)` 再跑 correction，边车就在 | **登记**（2026-08-27，F-97 施工席位「停下上报」时撞出，orchestrator 复核属实）· 处置已定 = 声明式排除 + 消费对账点名（随 F-97 落地）· ⛔ **影响面本轮不追** |
| **⭐⭐ 新 F-107**（GLM 记 F'-1；= 原 F-4 结转）| ⛔ **G1 复现门与 `RawLayerTrust` 至今零生产消费方** —— GLM 窄+宽两轮 grep 实测（`verify_raw_layer_reproduction｜load_gt_raw_layer｜RawLayerTrust｜GtRawLayer｜reproduction_status｜inputs_unavailable｜not_attempted｜trustworthy`）：生产代码 **0 命中**，全部命中为无关注释/测试。⇒ **「响亮降级」目前只活在返回值与测试断言里**。⭐ 同族 [[absence-conflates-causes-in-observables]]：**没有消费者的响亮 = 没有响亮。** 修法 = 接线时消费者把**非 `reproduced` 一律当红** | **登记**（2026-08-27，GLM 返工审 F'-1）· ⛔ 接线时必做，⛔ 碰 `src/agent/judge/` 须派工 |
| **⭐⭐ 新 F-108**（GLM 记 F'-2）| ⛔ **盘上报告 schema 非法时走【裸异常】而不是四态 verdict**：`gt_raw_layer.py:472` 的 `model_validate_json` **不在 try 内** ⇒ GLM 造的 11 种形态里有 **6 种**（数字→字符串 / 塞未知字段 / 删必填 / 改 gate id / 嵌套塌缩 / 外包一层）直接炸出 `ValidationError`。**今天响亮无害**（且无消费者，见 F-107）；⭐ **接线之日就是隐患** —— 调用方对异常的处理若与 verdict 分叉，「响亮」就漏气。修法照抄本单 F-2 的样式：接进 `content_mismatch`（或专设状态）+ 指针取自校验错误路径 | **登记**（2026-08-27，GLM 返工审 F'-2）· ⛔ 碰 `src/agent/judge/` 须派工 |
| **⭐ 新 F-109**（GLM 记 F'-3）| **晋升件反解的掩护面 = 恰好 `verification.methods` 一个元数据字段**：GLM 实测篡改该字段**门照绿**（反解把它 reset 回 `[]` 再哈希，签字链管不到）。其余字段 status/reviewer/日期有交叉核对，再其余全在 content hash 里。⛔ **纯元数据、动不了几何**，故不阻断；但当前签字链对它**零绑定**。修法：docstring 声明，或给 methods 也加交叉核对 | **登记**（2026-08-27，GLM 返工审 F'-3）|
| **⭐⭐⭐ 新 F-110**（GLM 记 F'-4）· ⭐ **口径已进 CLAUDE.md banner ②′** | ⚠️ **VG 指纹升 fatal 的运维代价：本批期间 sm25 复现门预计常红**。`vg_implementation_sha256` 覆盖 `correction/{facade_visibility,facade,footprint,schema}.py` 四件，且是**文件粒度**不是行为粒度 ⇒ **只改 `correction/schema.py` 里与转换无关的行（正是本批 reading/correction 一体改的主战场）也会报 `implementation_drift`**。⭐ **为什么仍成立**：归因不错（确实「这棵树不再是产出该报告的实现」），且组内无闭包外文件、不会混进假漂移。⭐⭐ **消化方式是流程性的**（红 = 「树动了」的信号 + 重签仪式），⛔ **代码消不掉**。⇒ **谁在本批期间看到这道门红，先对照本条，⛔ 别记成缺陷/回归** | **口径**（2026-08-27，GLM 返工审 F'-4）· ⛔ 不是待修缺陷，是**必须先声明的已知代价** |
| **⭐⭐ 新 F-111**（GLM 记 F'-5）| ⛔ **sm24 的签字 request 已不可寻 ⇒ 复现门可用面 = 现存 2 份 case 里的 1 份**。GLM **实跑 sm24_anchor** ⇒ `inputs_unavailable`（`logs/experiments/` 下无 request.json 能重算出签字哈希）。门 **fail-closed 行为正确**（响亮、不假绿），但可用面只剩 sm25。⚠️ **orchestrator 题面错**：我把这条写成「目录**被清理则会**降级」的**将来时风险**，实测**它已经发生** ⇒ 下次盘点复现门读数按「**可用面 1/2**」记账。⭐ request 的权威来自**内容重算**（位置不承权）⇒ 把真件归档到耐久位置是安全的找回路径；或明确记「sm24 复现门不可用」 | **登记**（2026-08-27，GLM 返工审 F'-5）· 需排期：找回归档 or 明确放弃 |
| **⭐ 新 N-3（F-95 审）** | `classify_ring_change` 的 `"resorted"` 类别在新合同下**生产侧永不触发**（docstring 已标注为历史诊断类）；将来若给 `GeometrySchema` 接非内核生产者需重读此合同 | **登记**（分类学债，极小）|
| F-62 · N-1 / N-2 | guard 词法围栏同族缺陷 | **未修**（`observe` 档下影响归零）|
| F-63 | 跨轴门抓不住拆轴规避 | ⭐ **本轮活体复现**（GPT 主动拆轴消警）；修法归 [专项 §9.1](capability/reading/improvement_methodology.md) |
| F-64 | gate① 对「零产出」是瞎的 | 登记 |
| ~~v3 判卷 null `scale_origin`~~ | ~~sm24 准入门~~ | ✅ **本轮已解**（`f2ea22e`，GLM 施工）|
| — | 全链无门校验「note 里的换算式 ↔ 笔画坐标」一致性 | ⭐ 确定性可查、成本低 |
| — | 读图器会自发产出**清单外文件**（`_validated_1f_view.json`）| 本轮由 merge 门拦住并归档；登记 |

**复审债**：甲-5 · 丙-1 / 丙-2（同前）。**本轮新增零复审债**——转换器批已由 GLM 跨家族审 + 主控轻门。

---

## 2026-08-27（夜班 · 用户睡觉，orchestrator 持续推进）

> 用户交代：「**施工优先走 claude 侧，GLM 审，三方 GPT 待命**；没有重大问题需要我判断的你就持续推。」
> ⇒ 本节 = 夜班的全部动作与读数。**口径类结论一律同步进 CLAUDE.md**（§5#12 ①-c）。

### 一～十二、⛔ **已逐字搬走** → [`logs/worklog/2026-08_plan_log.md` · 2026-08-27 夜班](logs/worklog/2026-08_plan_log.md)

> 内含：主树全量基线 3035 绿 · **R-6 更正（原始层已在盘上）** · 判别法则补成两问 · sol 架构意见未落库的记录 ·
> 三个席位派出 · F-95 前置核查 · **「没有可信图纸↔世界标定」在 gt 侧是错的** · gt 三层重新定位 ·
> **F-95 跨家族 APPROVE** · **sol 判我四条结论全部只「部分成立」并给出严格更优的路** · G1 施工交件 · 夜班暂停。

### 十三、✅ **两条返工同时落地**（额度恢复后一轮做完）—— ⛔ 但**两条都还没过审**

> ⚠️ 用户 08-27 新拍板并已进 CLAUDE.md §5#7.5：**一个模型家族同时只能在飞一个任务**，跨家族可并行。
> 本轮据此排：**Claude 家族 = F-97 返工**（唯一一件）· **GPT 家族 = G1 返工** ·
> GLM 留着做下一轮复核（且 14:00–18:00 CST 是它 3 倍扣额的高峰）。

| 单 | 席位 | commit | 全量 | 状态 |
|---|---|---|---|---|
| **F-97 返工** | Claude | `f2a8ccf` | **3070 passed / 13 xfailed / 0 failed** | ⏳ **未过审** |
| **G1 返工** | GPT sol | `ef41a39` | **3046 passed / 13 xfailed / 0 failed** | ⏳ **未过审** |

#### F-97 返工：三条阻断全修（施工方**先独立复现了三条**再动手）

| 判据 | 读数 |
|---|---|
| R1 | 未登记声明 ⇒ `unknown` 并点名 `future_reading_contract_v99`；**3 条锁全走真实 `_build_correction_messages`** |
| R2 | 已登记声明 + legacy ⇒ 仍 `AMBIGUOUS: matches 2 declared contracts`，同时点名两契约 |
| R3 | 畸形边车 ⇒ 真实入口红并点名；**兼容面 43/43 边车仍 EXCLUDE、328/328 legacy 仍 CONSUME**（已写成硬断言）|
| R4 | 真实 `run_correction` 两负例（顶层 list / 非法 JSON）⇒ 点名异常 + **ledger 两次都在盘上** |
| R5 | 字节变化面 `56/49/7/0，移除 170,455 B` —— **与返工前逐字相同 ⇒ 收紧零代价** |
| R7 | neuter 逐条：B-01→3 红 · B-02→2 红 · B-03→3 红，三次 `passed+failed` 均 = 3070 ⇒ **零附带** |

⭐⭐ **它自己撞到并修好了裁定预警的那个坑**：第一版写「有 `schema` 键就不是 legacy」，
**当场把双命中从 `AMBIGUOUS` 塌成单命中** —— 实测抓到后收窄成「只否决**未登记的**声明」。
⭐⭐⭐ **它自陈最值钱的一条**：B-02 正是它上一轮自陈「弱的就是这个」的地方
⇒ **「自陈不确定」≠「已处理」**，识别出弱点却没修，复核方就会把它变成阻断。

#### G1 返工：**整张豁免清单已删除**（⛔ 不是收窄成白名单）

按上一轮 GLM 实测出的更优解：**把已验证的 `review_ack.json` + `review_index.json` 一并喂进复现跑**
⇒ **diff = 0 指针**，`_pointer_is_signature_dependent` / `SIGNATURE_DEPENDENT_POINTERS` /
`HUMAN_REVIEW_GATE_IDS` **全部删除**，复现结果**不再过滤任何指针**。

| 判据 | 读数 |
|---|---|
| R1 | 旧豁免符号 `rg` **0 命中**；未改动树 `status=reproduced` / `differing_pointers=()`；签字链三值一致 `49065597…` |
| **R2** | ⭐ **分辨力没退化**（我最担心的一条）：边厚度 0.12→0.13 ⇒ 指名 `/zones/0/edges/0/thickness_m`；**篡改 G6 几何证据 `near_threshold_faces/0/area_m2` 2.544→2.545 ⇒ 仍红并指名** |
| R3 | `converter_sha256` 漂移 ⇒ `implementation_drift`，与 `content_mismatch` 仍可分 |
| R4 | **F-2 已修**：`gates` 塞重复 id ⇒ `content_mismatch` 指针 `/gates`（原本静默照绿）|
| R5 | **F-3 选「VG 升 fatal」**：`vg_implementation_sha256` 精确覆盖 correction 四件、四件全在闭包内且无闭包外噪声；extractor/validator 仍 advisory |
| R7 | 五次 neuter 每次 **1 failed / 10 passed**，只红对应锁 |
| R8 | **补上原 A1/A6 的真值**（上一轮 GLM 裁决里那两个 `{{PASSED}}` 占位符）：A1 = 29 zone / 136 边 / basis 90:46 / 厚度 78:58；A6 双向各 1 failed / 6 passed |

⭐ **它还顺手补了一个我没想到的洞**：晋升后的 `gt.json` 会**合法**改变 `verification` 与 `content_sha256`
⇒ 字节哈希不等于 index 里的 candidate；复现门现在**反解这两个允许的变化并重算 `candidate_gt_sha256`**，
证明其余语义（含 generator 指纹）仍来自签字 candidate。

#### ⛔ 两位施工方各自点名的「最可能塌」（下一轮复核的靶子）

- **F-97**：`DECLARED_SCHEMA_VALUES` 是**手写的第二处清单**，往 `CONTRACTS` 加契约却忘同步
  ⇒ 「已登记被判成未登记」静默错配。⭐ **这是「第二个定义」这个病的第三次现形。**
  另：`_preflight_vector_contracts` 与 `_build_correction_messages` **各分类一遍**；
  `==43`/`==328` 硬断言没写「为什么是这个数」的出口，后来者可能当误报放宽；
  B-02 的 `CheckReport` 信任根只验了产物侧、**没回溯 `validation_run.py:292` 的构造类型**。
- **G1**：签字 request **只在 `logs/experiments/**` 可得**（目录被清理 ⇒ 响亮降级 `inputs_unavailable`，不假绿但门失效）；
  晋升语义将来若新增可变字段本门会 fail-closed；`gt_extraction`/`gt_manifest`/`gt_schema`/`tarch_converter_schema`
  在闭包内但无精确指纹（**抓得住、归因错**）；全部实测**只在 sm25 一个 case**。

#### ⏭ 下一轮第一件事

**两条返工各送一轮跨家族审** —— F-97 返工由 Claude 施工 ⇒ 审可派 **GLM**；
G1 返工由 GPT 施工 ⇒ 审可派 **GLM 或 Claude**，⛔ 不能是 GPT。
⚠️ 按新并发规，**同一家族同时只接一件**；GLM 高峰 14:00–18:00 CST 3 倍扣额，长审排 18:00 后。
### 十四、⏳ **两条返工的跨家族审已派出（日班，用户拍板「现在同开」）**

| 单 | 被审 commit | worktree | 施工方 | **复核席位** | 为什么是它 |
|---|---|---|---|---|---|
| **F-97 返工** | `f2a8ccf` | `/tmp/ep_f97` | **Claude** | **GPT sol** | 上一轮那三条阻断是它提的 ⇒ 让它自己验有没有堵上 |
| **G1 返工** | `ef41a39` | `/tmp/ep_g1` | **GPT sol** | **GLM** | 「把签字件喂进复现跑、整张豁免清单直接删」这条路是它上一轮提的 ⇒ 让它自己回头验 |

⛔ **两条都不是「谁写谁批」**：F-97 由 Claude 施工故 Claude 不能审；G1 由 GPT 施工故 GPT 不能审。
⇒ CLAUDE.md banner ⑤ 原写「F-97 返工 → GLM 或 Claude」**是错的**，已当场改正。
✅ 符合 §5#7.5 并发规：**GPT 一件 · GLM 一件**，Claude 家族只留 orchestrator。
⚠️ 用户知情并拍板：GLM 现在处在 14:00–18:00 CST 的 **3× 扣额高峰**，照跑。

**两份请求单**（结构一致）→ [F-97](logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md) ·
[G1](logs/reviews/request/2026-08-27_g1_rework_crossreview_glm.md)。
两份都写了：原始问题（⛔ 不是「diff 干了什么」）· 上一轮裁决原文 · 重点处 · **A1–A7 逐条判据且每条都写明「什么情况下会不通过」**（对治
[[acceptance-bar-must-not-be-written-from-the-result]]）· 明确不做 · 停下上报触发器（含「都次优但有更优解」）·
**「orchestrator 自认可能写错的地方，请优先证伪」**。

#### ⛔⛔ 第 37 次「停下上报」—— 又是派工方（我）的题错，**而且是当场自造的**

**GPT 第一次派出开工即停**，⛔ 没做任何实体复核。它抓的是：
我在 §〇 写「工作树干净、`status --porcelain` 为空」（**开单那一刻确实为空**），
可我**紧接着自己把请求单拷进了那个 worktree**；再叠上「交件时只剩你的裁决文件」
⇒ **两条结构上不可同时满足**，且它无权删/提交那份既有文件。

⭐ **这条的新意不在「我写错了一个数」，而在于**：那句话**写下时是真的**，是我**自己后续的动作**把它变成了假的。
⇒ **派工单里凡是描述「工作树/环境当前长什么样」的句子，必须在【最后一个准备动作做完之后】重新核一遍**，
⛔ 不能在写单时核完就当数。同族 [[stop-and-report-catches-dispatcher-errors]]。
⭐ 顺带：**同一个坑在 G1 单上也埋着**（我写「3 份 untracked」，拷进请求单后实际是 4 份）——
GPT 的红让我在 GLM 撞上之前先改掉了。**跨家族的价值又一次不是在被审对象上兑现的。**

**处置**：停下上报裁决逐字归档 → [`stopreport.md`](logs/reviews/verdict/2026-08-27_f97_rework_gpt_stopreport.md)；
题面已修；worktree 清回「只剩请求单一份」；**已重新派出**。

#### ⛔⛔⛔ 第 38 次 —— 而这一次**病因不是那个数，是我的触发器写得不分层**

第二次派出，GPT sol **又是开工即停**：我在 §〇 写返工面「另有**三份** md」，`--numstat` 实测**四份**
（我是照着 `--stat` 的省略显示随手数的，数漏一行）。它引的正是我自己写的触发器 #1
「数值 / 文件名对不上 ⇒ 停下上报」。**它照办，完全正确。**

⭐⭐⭐ **代价与病因严重错配**：返工面里有几份 markdown，**与「三条阻断有没有被堵上」零关系**，
却让**整轮实体复核（全量 + neuter + 主动找缝 + 三条阻断双向验证）一次都没跑**。**两轮空转、约 5.3 万 token。**
⛔⛔ **而「触发器必须分层」这条，我 2026-08-12 就写进 memory 了**
（[[stop-and-report-catches-dispatcher-errors]] How-to-apply #11：
「① 承重前提错 ⇒ 停；② 外围论据错 ⇒ **报告并继续审其余**。⛔ 不许再写成无差别的『发现前提错就停』」），
**然后在这份派工单上写了无差别版。** ⇒ **「写下自检 ≠ 执行自检」这个形状，在同一条 memory 里已是第二次。**

**两条机械化修法（已落地到两份派工单）**：
1. 触发器 #1 改成**分层版**，并附判别问法：**「这条错如果成立，我还需不需要审这份 diff？需要 ⇒ 只记不停。」**
2. ⭐ 凡写「共 N 份 / 另有 N 个」这类**计数**，一律**贴 `--numstat` / `--name-status` 原始输出**，
   ⛔ 不用自己数出来的中文数词。§〇 的起点、提交链、diff 面现在全是逐字读数。
⇒ **累计题错 38/38。**

⚠️ **同一分层修法已同步补进 G1 那份请求单**（GLM 正在飞，避免它撞同一堵墙）。
⇒ **第三次派出已发。**

⭐ **顺带一条对「跨家族价值」的读数更正**：本轮 GPT 两次交件**零实体产出**，
但它两次都精准打在**派工方**身上 —— 这与 08-27 之前「跨家族抓的是被审对象」的印象不同。
⛔ 别把「复核轮空转」记成复核方的问题。

#### 顺手修掉的一处过期口径

**CLAUDE.md §1.3 `tests/` 行**原写「⛔ **当前红着**：3010 passed / 1 failed / 3 errors」（08-25 读数），
而那批红 = **F-93**，早已于 `b3e0a32` 闭合。⇒ 已改为
**✅ 全绿 3035 passed / 13 xfailed / 0 failed**（08-27 主控权威全量，commit `ed0ba09`），
并注明**当前 HEAD `534b5a2` 相对 `ed0ba09` 只动了 `AI_agent/` 文档**（`src`/`tests`/`scripts`/`skills` 零改动，已实测）
⇒ 该读数对当前 HEAD 仍成立。**这正是 §5#12 ①-b 要防的「每次新会话第一眼读到过期口径」。**

#### ✅ **G1 返工 = APPROVE / 0 阻断**（GLM，[裁决逐字](logs/reviews/verdict/2026-08-27_g1_rework_glm_verdict.md)）

**它先跑全量**（我在单子里把这条排成第一个动作，就是冲着上一轮的欠账去的）：
逐字 `3046 passed, 13 xfailed, 211 warnings in 405.32s`，exit 0。
⇒ **上一轮那两格 `{{PASSED}}` 占位符（A1/A6）清偿。**

| 上一轮 finding | 现状 |
|---|---|
| **F-1** 豁免形状从结果反推 | ✅ **整张清单已删**（非白名单化）；`rg` 0 命中；比对路径**不过滤任何指针** |
| **F-2** 重复 gate id 照绿 | ✅ 已修（`content_mismatch` / 指针 `/gates`），且**接进 verdict 通道而非裸炸** |
| **F-3** VG 纯闭包却降 advisory | ✅ 选了升 fatal；docstring 洞清单已含 `gt_schema` |
| **F-4** `inputs_unavailable` 无生产消费者 | ⏭ **结转债**（派工单本就划出范围）⇒ 现 **F'-1** |

⭐⭐⭐ **它回头验了自己上一轮提的那条路线（「把签字件喂进复现跑」）会不会变成自证 —— 实测【不成立】**，
而且给了非循环依据：喂进去的 `review_ack.json` / `review_index.json` **不是从被审报告派生的**
（`_RUNTIME_BUNDLE_FILES` 明确把 `conversion_report.json` / ack / index 都排除在 index 之外；
ack 签的是 DXF 字节哈希 + request 内容哈希 + files 清单规范摘要，**没有一样来自被审报告**），
且门**自己重算** files 摘要、不信自报值。
⭐ **而且比旧设计强**：旧豁免对那 8 族指针**完全免检**（塞什么假 evidence 都行），新设计要求它们与签字件**逐字段一致**。

⭐⭐ **换方向自造 11 种形态级变异 + 3 次独立 neuter，无一「改内容却照绿」。**
（重排 / 空数组 / 类型变化 / 塞未知字段 / 删必填 / 改 gate id / 嵌套塌缩 / 外包一层 —— 6 种走 schema 裸异常路径，见 F'-2。）

#### ⭐ G1 的五条不阻断 findings（**F'-4 与 F'-5 有排期含义，别只当记账**）

| # | 内容 | 我的处置 |
|---|---|---|
| **F'-1** | 复现门与 `RawLayerTrust` 至今**零生产消费方**（窄+宽 grep 实测）⇒「响亮降级」只活在返回值与测试断言里 | **接线时必做**：消费者把非 `reproduced` 一律当红 |
| **F'-2** | 盘上报告 schema 非法时以**裸 `ValidationError`** 退出（`gt_raw_layer.py:472` 的 `model_validate_json` 不在 try 内），不是四态 verdict | 今天无消费者故无害；**接线之日即隐患**。修法照抄本单 F-2 的样式 |
| **F'-3** | 反解的掩护面 = **恰好 `verification.methods` 一个元数据字段**（实测篡改它门照绿） | 纯元数据、动不了几何；登记 + 声明或补交叉核对 |
| ⭐ **F'-4** | **VG 升 fatal 的运维代价**：vg 组 = `correction/{facade_visibility,facade,footprint,schema}.py` **文件粒度指纹** ⇒ **本批 reading/correction 一体改期间，只要动 `correction/schema.py` 就会 `implementation_drift`**，sm25 **预计常红** | ⭐⭐ **必须先写进本批跑测口径**，否则届时会被当回归。已进 CLAUDE.md |
| ⭐ **F'-5** | **sm24 的签字 request 已不可寻** —— GLM 实跑 sm24_anchor ⇒ `inputs_unavailable`。⇒ **门的可用面 = 现存 2 份 case 里的 1 份** | 找回真件归档到耐久位置，或明确记「sm24 复现门不可用」 |

⚠️ **它据此更正了我的一处题面**：我把「request 目录被清理**则会**响亮降级」写成**将来时的风险**，
**实测它已经发生**（sm24 今天就是 `inputs_unavailable`）。⇒ 下次盘点复现门读数按「**可用面 1/2**」记账。
⭐ 另：它按分层触发器把「3 份 vs 4 份 untracked md」**只记不停** ⇒ **今天改触发器这一下当场兑现。**

#### ⛔⛔ F-97 复核：**第三次派出做完了实体复核，但交件被 provider 安全过滤拦掉**

GPT sol 第三次派出**没有再停**，实打实审了 **113,184 token**，造出了新夹具、还跑了 neuter
（我在 worktree 里捡到它没来得及还原的那一处：`vector_contract.py` 摘掉 `_declares_unregistered_schema` 那两行）。
**但最后写裁决时连吃两条 `ERROR: This content was flagged for possible cybersecurity risk`** ⇒
**裁决文件没写成、neuter 没还原**（我已 `git checkout --` 还原，worktree 现只剩请求单一份 untracked）。
⇒ 同族已登记：08-16「审隔离壳的活被 GPT provider 过滤拦死 6 次，改派 GLM，**措辞最多改一次**」。

⭐ **它的探针文件已保住** → [`artifacts/2026-08-27_f97_rework_gpt_probe/`](logs/reviews/execution/artifacts/2026-08-27_f97_rework_gpt_probe/)
（`_review_f97_new_probe.py` 118 行 + 未还原的 neuter diff；⚠️ 完整 stdout 因 `*.log` 被 ignore **只在本机**
`AI_agent/logs/reviews/execution/2026-08-27_f97_rework_gpt_review.stdout.log`，⛔ 未入库）。

⛔⛔ **以下全是【它写的断言】，orchestrator 一条都没跑过 —— ⛔ 不是实测事实，只作下一轮复核的线索**：

| 探针 | 它断言的 |
|---|---|
| `test_new_b01/b02/b03_..._at_real_run` | 三条阻断的**原夹具**已在真实入口被拦、被点名、被记账 |
| ⭐ `test_registered_but_malformed_declaration_still_falls_back_and_is_consumed` | 顶层声明 **as-drawn schema** 但只带 legacy `strokes` ⇒ 仍判 `reading_view_legacy` 并**被消费** |
| ⭐⭐ `test_unhashable_schema_crashes_before_ledger`（`schema=[]` / `{}`）· `test_invalid_utf8_crashes_before_ledger` | **崩在 ledger 之前 ⇒ 与 B-03 同形**（B-03 可能只修了它举的那一种输入） |
| `test_empty_and_bom_files_are_named_and_ledgered` | 空文件 / BOM ⇒ 点名且记账（**这条是好消息**）|
| `test_uppercase_and_nested_json_are_absent_from_ledger_inventory` | `MYSTERY.JSON`（大写）与子目录里的 json **不进 ledger 清单** |

⇒ **F-97 仍然【未过审】。** 下一轮的处置见本节末尾。

#### ✅ **G1 已并回主线并过了主树权威全量**

`10fb3b6`（`--no-ff` 合并 `wt/08.27_gt_raw_layer`，3 文件 / 779 行，**零冲突**）。
**主树权威全量**（`python -m pytest -q -n 6`，18m10s，exit 0）：

```
3046 passed, 13 xfailed, 212 warnings in 1090.36s (0:18:10)
```

⇒ 与 GLM 在 worktree 里跑的 `3046 passed / 13 xfailed / 0 failed` **计数一致**；较合并前主树 3035 净增 11
（G1 原件 7 + 返工 4）。**合并门通过。**
⚠️ 该轮与 GLM 审 F-97 同机并行（各 `-n 6`，峰值 `load average 14.94/16 核`）—— **没有出现 08-27 那种无 summary 行的假红**，
⇒ **`-n 6` × 2 路是安全配置**，`-n auto` × 3 路不是。这条给 §5#7.5 补了一个正例读数。

#### ⛔ **F-97 返工 = REWORK / 3 条阻断**（GLM 第四次派出，[裁决逐字](logs/reviews/verdict/2026-08-27_f97_rework_glm_verdict.md)）

**先说公道话**（GLM 原话）：**返工是真修** —— GPT 三条阻断在 `8fda4c1` 上它用独立夹具**全部复现**
（B-03 连 `AttributeError: 'list' object has no attribute 'get'` 原文都一致），在 `f2a8ccf` 上**各自原夹具全部不再复现**；
三次 neuter 各跑全量，红集 **3/2/3** 与施工自述全对上、**零附带**；干净树全量 **3070 passed / 13 xfailed / 0 failed**。
⭐ **GPT 那三条阻断，无一判错。**

⭐⭐⭐ **三条新阻断【全部】出自请求单 §3.1 的判据 ③「修法只堵住了被举的那一种输入，换同形输入又走通」** ——
**那是本轮唯一新加的一条判据，一次抓三条。**⇒ **值得固化进模板**：凡「修了某条阻断」的返工审，
判据必须同时要求 ①旧 commit 复现得出 ②新 commit 复现不出 ③**换同形输入仍走不通**。

| 阻断 | 内容 |
|---|---|
| **BLK-A** | **B-01 只修了「未登记」这半** —— GPT 的返工要求原文是「未登记 / **畸形**显式 schema + legacy 结构 ⇒ unknown」。声明**已登记**值但**缺该契约必需键** + `strokes` ⇒ **仍判 `reading_view_legacy` 并被静默消费**。三个已登记值（`as_drawn_plan_v2` / `v0` / `elevation_v0`）**全部实测塌缩** |
| **BLK-B** | **B-03 在【组合入口】原样保留** —— `run_pipeline_artifacts` 在 `pipeline.py:1368 / :1376 / :1411` **自己先解析了 `*_view.json`**，全部先于 `:1414` 的 `run_correction`。同一夹具在 `f2a8ccf` 上仍死在**逐字相同**的 `AttributeError`、**无 ledger**。⭐ **正对照**：同一毒文件改名 `mystery.json` ⇒ 正确点名 + 记账 ⇒ **纯入口顺序问题**。⛔ 返工自己 docstring 写的 "Runs before ANY consumer that parses `*_view.json`" **在这一层是假的** |
| **BLK-C** | **「ledger 永不抛」这个前提不成立** —— 三个**普通文件系统/编码现实**全部崩在账落盘之前：① `schema=[]`/`{}` ⇒ 对 frozenset 判成员 `TypeError: unhashable type`；② 非法 UTF-8 ⇒ `UnicodeDecodeError`（`_classify_rows` 只捕 `JSONDecodeError`）；③ **`0_reading/backup.json` 是个目录** ⇒ `IsADirectoryError`。⭐ 前两个是复跑 GPT 探针线索、**第三个是 GLM 自加的** |

⭐ **GPT 探针那 5 条线索的最终判定**（GLM 逐条复跑）：#2 → **BLK-A** · #3 → **BLK-C** ·
#1 成立但「真实入口」只覆盖到 `run_correction`（⇒ 正是 BLK-B 藏身处）· #4 成立**非缺陷** · #5 成立**不阻断**（N-E）。
⇒ ⭐⭐ **「把另一席位的探针当线索交下去、要求独立复跑 + 另外自己找」这个做法兑现了**：
GPT 被过滤拦掉的那 113k token **没有白烧**。

#### ⭐ 六条不阻断里两条有排期含义

- **N-B**｜`==43` / `==328` **语料快照常量** —— ⚠️ **本批第 ③ 步「产出新方案产物」一落地、任何新 `0_reading/*.json` 入库就会让它们红**
  ⇒ **合法增长被当失败，诱发后来者机械放宽**；且语料根 `Path(".")` 依赖 cwd。
  建议改**不变量断言**（unknown==0 / 被移除的 `*_view.json`==0 / 每份被判边车可由 `CheckReport` 解析）替代计数快照。
- **N-A**｜`DECLARED_SCHEMA_VALUES` **无机械对账的第二处清单** —— **今天不会错配**（探针证三值↔三契约一一对应），
  但**加契约时会静默**，GLM 用 monkeypatch **双方向都实测演示过**：只加 spec 不进集合 ⇒ 原 AMBIGUOUS **静默塌缩成单判**；
  只进集合不加 spec ⇒ **B-01 经漂移重开**。建议给 `ContractSpec` 加 `declared_schema_value` 字段**从源头派生**。

#### ✅ **本轮题面零承重错、零停下上报** —— 38 连败后的第一份干净派工单

GLM 逐项核过 §〇 的全部 git 读数（HEAD / 两段 `--numstat` / 3 提交链 / 祖先关系 / 开工恰 2 份 untracked）**逐字一致**。
唯一点名：**我把 B-03 的病根概括成「helper proxy 冒充生产入口锁」过窄** ——
它给了更好的写法，**已采纳**：
> **F-c 的「失败必留账」要在【所有】会碰 `0_reading` 的入口、与【所有】输入形态下成立。**

⇒ 这正是 BLK-B（入口层级）与 BLK-C（输入形态）两条的统一描述，而它们**都与 helper proxy 无关**（锁全走真实入口也拦不住）。
⭐ 另一处口径澄清：`170,455` = **提示词块字节**（含包装、strip 后内容），**原始文件字节是 168,149** ——
以后此类数字须注明口径。

#### ⏳ **F-97 第二轮返工已派出**（用户拍板 · Claude 施工 ‖ GLM 审）

[派工单](logs/reviews/request/2026-08-27_f97_rework2_dispatch.md) · worktree `/tmp/ep_f97` · 起点 `f2a8ccf`。
✅ 符合 §5#7.5 并发规（Claude 一件、GLM 待命）与 §0.4#3（碰 `src/agent/pipeline` 内核 ⇒ 派工 + 换人审）。

⭐⭐⭐ **本单把「换同形输入」这一格【下放给施工方自己跑】** —— 三条阻断各要交满三格：
① `f2a8ccf` 上复现得出 · ② 新 commit 上复现不出 · ③ **自己造同形输入去打，并写出按什么方向找的**。
理由即本日读数：**前两格上一轮全绿，第三格一次抓三条。**⛔ 别再把这一格全押在复核方身上。

⭐ **N-A / N-B 明确本轮不做**，但 **N-B 挂了硬闸**：
**本批第 ③ 步「产出新方案产物」开工前必须先把 `==43`/`==328` 改成不变量断言** ——
否则新 `0_reading/*.json` 一入库就红，**合法增长被当失败**。

#### ⭐ 发单前最后一刻重跑，当场抓到两处自己的题面错

`§〇` 我先写「3 份 untracked / CLAUDE.md 448 行」，**最后一刻重跑实测是 4 份 / 447 行**
（第 4 份正是本派工单自己；448 是主树的行数、worktree 那份是 `f2a8ccf` 时的 447）。
⇒ **今天花两轮空转换来的那条新规矩（描述环境现状的句子必须在最后一个准备动作之后重核）当场兑现**，
**这两条没有变成第 39、40 次停下上报。**

---

## 2026-08-26（已翻篇，逐字归档）

> F-90 补审 REJECT → 返工 → GLM APPROVE 零阻断 · 用户一天定死 12 条口径 · sol 架构意见 · gt 修正前置化 ·
> F-95 派工被顶回（第 35 条）· 基准 12 cm 定性。**全文逐字** → [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)。

## 2026-08-25（已翻篇，逐字归档）

> 架构定稿 · 管子拆 9 工序 · 工具箱转正 APPROVE · C2 首次被真正量过 · 答案直喂内核撞出 F-95/F-96 · gt 三层立场
> **2026-08-26 收工时逐字搬入** [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)。

## 2026-08-24（已翻篇，逐字归档）

> 六段（**六审 APPROVE·gt 放行书写** · 五审 `band_collapse` · 四审证伪两个数 · **可评分分母 + reading 判分器落成** · 三审 REJECT · 模型真进环）
> **2026-08-25 收工时逐字搬入** [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)。

## 2026-08-23（已翻篇，逐字归档）

> 两段（**as-drawn 路线分叉：形态样板 + 五步计划**；**sm25 gt 签字入库 + 判分首次真正跑通 + 全案对答案**）
> **2026-08-24 收工时逐字搬入** [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)。

## 2026-08-20（已翻篇，逐字归档）

- 07-07 水平在当前基座复现（Sonnet 9/9·7/7·15/15·0.0 m）· 转换器多层化 · 三条判据修正
- 立面洞口「载体方言层」落地（F-65）· sm25 立面阻断解除（31 窗 + 3 门）
⇒ 全文见 [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)

## 2026-08-22（已翻篇，逐字归档）

> 全部 9 段（orchestrator 亲自下场跑通 sm25 1f+2f · F-69 真因 · 开发循环被用户纠正 · harness 版本管理立规 · 立面判卷绑定三轮返工 · 立面朝向约定 · 判卷路径三缺陷）
> **2026-08-24 逐字搬入** [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)。

## 2026-08-21（已翻篇，逐字归档）

- sm25 gt 候选包产出并签字 · 转换器三修 + 判卷两修 · C2 首考判分（外轮廓 94.4% / 窗 8/15） · 停下上报 8/8 全是派工方题错
⇒ 全文见 [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)

---

## 2026-08-19（已翻篇，逐字归档）

- 三臂判别跑完 · 病灶定位到「肯不肯把看放到放大镜后面」· 根治与 Haiku 回归打包归专项
- GPT 判别臂第一格：历史栈今天仍能出满分 reading（一轮返工，4/4 · 3/3）
⇒ 全文见 [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md)

## 中期（粗）—— 能力升级（原 B5–B7）

按 **[capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md)** 的 C 阶梯推进（内核先行 + 守卫同步）：
- **C2 正交多边形 + 多平面立面**（含 shapely 覆盖完整性门提前落地）
- **C3 退台 / 挑空**（墙配对 by_floor → z 区间重叠驱动、切配扩到切墙）
- **C4 斜交墙**

并行支线：识图→建模质量主线见 [capability/recognition_modeling_capability.md](capability/recognition_modeling_capability.md)；再拓扑 leg（休眠）见 [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md)。

---

## 远期 —— 开源模型 + Pivot（原 B8–B9）

- 部署 vLLM + Qwen2.5-VL / DeepSeek-VL；切 [llm.yaml](../src/configs/llm.yaml) `intake` section（A2 已就绪）；跑同一套评测横向对比。
- LoRA SFT（phase1=(图,矢量JSON) VLM / phase2=(矢量JSON,IntakeOutput) 纯文本，两数据流独立），holdout ≥ Opus 80% 后切默认 provider。
- 双阈值见 [reference/pivot_criteria.md](reference/pivot_criteria.md)。

---

## 分出去的独立模块（指针）

| 模块 | 文档 | 状态 |
|---|---|---|
| CAD→gt 满配答案 / CAD 输入模态种子 | [proposals/cad_to_gt_extraction_plan.md](proposals/cad_to_gt_extraction_plan.md) | 设计待审，工具链就位 |
| reading 提升（诊断+Phase A/B/C+CV 工具箱方法论）| [capability/reading/improvement_methodology.md](capability/reading/improvement_methodology.md) | **已动工**（Phase A ✅ 落地）→ 统一管理文档；原 proposal 已折入并删（2026-07-03）|
| 0–3 复杂度升级路径（C2/C3/C4）| [capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md) | 骨架已立，随中期推进 |
| 再拓扑 leg（热区积木 zonification）| [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md) | 强力支线·休眠·**Fable5 B3(07-06)已更新启动条件**（绑 C2 开工·stage 1.5·`method` run_config·比原设想更易落地，见其 §9）|
| 可编辑几何确认环节 | [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md) | DEFERRED，先讨论 |

---

## 搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）：等协作者侧 MCP 全线重写交付。
- **token 优化**（[deferred/token_optimization.md](deferred/token_optimization.md)）：等 idfpy 切换后大量 CRUD 工具消失再评估。
- **fenestration/construction SimpleGlazing 兼容性 prompt 修**：等 idfpy schema 原生覆盖（当前几何优先，不动 prompt）。
- **Sonnet 4.6 降级测试**（本环境够不到，需用户独立会话；**Haiku 4.5 降级测试已跑 ✅ 2026-07-05，见 N2b ③**）；**OpenStudio 几何验收**（用户人工，不卡代码）。

---

## 已完成（一行汇总，详见 [decision_log.md](decision_log.md)）

A 代码跑通 ✅ · B1 旧 skill 迁移恢复 ✅ · 两步法 POC + 切主线 + InterZone 门 + 正式指南 ✅ · 0–5 阶段重构（几何确定性化）✅ · EP 跑通 + schedule 门 ✅ · 完整体检 4H/3M/3L 全修 ✅ · 仓库整理 + 标准 case 布局 ✅ · 0–5 校验架构 M0–M4 ✅ · 新 baseline 方案 + 主 Agent 操作手册 + gt ✅ · 逐段 judge 编排 + 离线 3D 查看器 ✅ · CAD→gt 工具链 + gt 渲染 ✅

---

## 归档（过程痕迹，⛔ 非活文档）

| 归档 | 内容 |
|---|---|
| [`logs/worklog/2026-08_plan_log.md`](logs/worklog/2026-08_plan_log.md) | plan 日更 2026-08-01 → 08-18（reading 重启七抽 · 基座普查 · 验收 3/3 · 下游断链 · F-22 批）|
| [`logs/worklog/2026-07_plan_log.md`](logs/worklog/2026-07_plan_log.md) | plan 日更 2026-07-31 + 原「当前焦点」章节正文（sm24 端到端 / 判卷器身份与度量批）|
| [`logs/worklog/2026-06_backlog_closed.md`](logs/worklog/2026-06_backlog_closed.md) | 原「近期（细）」整节（2026-06 批次，绝大多数已 ✅）|
| [`decision_log.md`](decision_log.md) | 里程碑与决策详档（历史决策的唯一归档）|
