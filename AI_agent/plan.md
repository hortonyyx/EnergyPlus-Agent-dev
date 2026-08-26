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
| **①-2** | **G1** gt **原始层**可读 API + **机械复现门** + 信任根显式化 | [用户]口径12 + [sol]#1 | ⏳ **施工中**（Claude 席位，08-27 夜派出）|
| **①-3** | **G2** 墙面线集合**落盘**（世界米 + DXF 原生坐标）+ **不规整清单** | [用户]口径12 | ⏭ 等 G1 的 API 形状定下来 |
| **①-4** | **G3** **判分侧标定归裁判** —— ⛔ 产品自报的标定不能用来换算它自己的答案（自证回路）| [sol]#2 | ⏭ 排在 G2 后；它是 reading grade 能不能成立的前置 |
| **①-5** | **语义升格成正式答案字段并计分**（配对 · 门窗身份 · 墨族角色 · **「我认不出来」这个声明本身**）| [用户]口径11 | ⏭ **必须与 ② 同批**（产物 schema 要一起动）|
| **①-6** | **F-89** 一张立面跨两层就整份丢 | [我方] | ⏸ **本日改判为挂起** —— 真缺陷，但那段代码服务 legacy reading 契约，② 要换掉它（见本日 §三）|
| **①-7** | **F-98** 判分对浮点末位敏感 | [我方] | 观察项，随判分侧改动一并评估 |

#### 第 ② 步「按新方案改造 reading + correction 的 harness（一体改）」

| 包 | 内容 | 来源 | 状态 |
|---|---|---|---|
| **②-0** | **F-97** correction 只吃**声明过的契约**，未声明的**响亮失败** + 消费对账 | [我方] | ⏳ **施工中**（Claude 席位，08-27 夜派出）· ⭐ ② 的必做前置 |
| **②-1** | **冻结出模形式**（跑前配置决定，两种成绩分开排）+ **参考包 → 两个投影** | [用户]口径2 + [sol]第三形态 | ⏭ **② 的第 1 号包** |
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

### 一、基线：主树全量 **3035 passed / 13 xfailed / 0 failed**

`ed0ba09` 主树权威全量（`python -m pytest -q -n auto`，13m27s，与三个席位并行跑故偏慢）。
⭐ 与 08-26 记录的 `3034 passed` 差 1 = F-95 那批锁进来后的自然增量；
⚠️ 并且 `tests/test_zone_agent.py` **本次是绿的** —— 它此前被记为「缺 API 凭据的已知环境红」，
⇒ **那条红不是恒定的**，下次谁再报它红，先确认是不是凭据抖动，⛔ 别当回归。

### 二、⭐⭐ R-6 需要更正：原始层**已经在盘上**，问题是「没人读 + 没被签字覆盖」

登记时 R-6 写的是「量了、用掉了、**存盘时扔了**」。orchestrator 本夜实测，**「扔了」这半是错的**：

- `case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json` 里，**29 个 zone 共 136 条边**，
  每条都带 `basis`（`wall_axis` 90 / `outer_skin` 46）+ `thickness_m`（0.12×78 / 0.24×58）
  + `offset_m` + `source_handles`（真 DXF 句柄）+ `thickness_evidence`。
- ⇒ 真正的两个缺口是：
  **① 判分侧没有任何路径读它**（`gt.py:load_gt` 只读 `gt.json`）；
  **② 它不在人工签字覆盖范围内** —— `tarch_review_bundle.py` 的 `_RUNTIME_BUNDLE_FILES`
  **显式**把 `conversion_report.json` 排除在 `review_index.json` 的 files 清单之外。
- 签字链本身完好（实算：`review_index.inventory_sha256 == review_ack.review_index_sha256 = 490655…`）。
  ⚠️ 注意它签的是 **files 清单的规范化摘要**，不是 `review_index.json` 文件自身的 sha256 ——
  orchestrator 第一次按「文件自身 sha」比对得出「对不上」，**是我算错了**，照生产者定义重算后一致
  （同族 [[recompute-gate-must-mirror-producer-definition]]，本夜第一次现形就被自己抓住）。

⭐ **由此定下 G1 的形状**：这一层的可信度**不能靠再要一次人工签字**（那要用户重签），
只能靠「**从已签字的源 DXF 机械复现出同样内容**」—— 正好对上用户口径 12 的
「**来源空间答案从 DXF 机械生成，⛔ 不人工标注**」。

### 三、⭐ 判别法则要补一句：「换一份产物还在吗」判的是**缺陷真不真**，不是**现在该不该修**

08-26 立的法则是「**这条结论是从哪份产物上读出来的？换一份产物它还在吗？**」。
本夜用它判 **F-89**（一张立面跨两层就整份丢）时发现它**不够用**：
F-89 是判卷**代码**里的缺陷（`reading_typed_adapter.py:667`），换产物它当然还在 ⇒ 按老法则「照常排期」。
**但那段代码服务的是 legacy reading 契约**，而第 ② 步一体改要换掉的正是 reading 产物形态
⇒ 修它很可能是在修一段马上要被替换的代码。

⇒ **补一句（本夜立）**：
> **①「换一份产物，这条结论还在吗？」** —— 判**缺陷是否真实**；
> **②「这段代码在新方案里还在吗？」** —— 判**现在该不该修**。
> 两问都过才排期；只过 ① ⇒ **登记为真缺陷，但挂起等新方案定了再排**。

⇒ **F-89 由「照常排期」改为「挂起」**（真缺陷，不撤销登记；等 ② 定了 reading 判分器的去留）。
⭐ 这与用户 08-26 那次纠偏是同一个形状，只是那次的对象是**产物**，这次是**代码**。

### 四、⛔ 记录缺口：sol 的架构意见正文**没有落库**

[`logs/reviews/verdict/2026-08-26_reading_correction_joint_architecture_sol_design.md`](logs/reviews/verdict/2026-08-26_reading_correction_joint_architecture_sol_design.md)
末行写着「**以下为 sol 意见正文（逐字，未改）**」，**其后什么都没有**（全文 43 行，两次提交里都是 43 行）。
而 08-26 的提交说明与 CLAUDE.md banner 都引用了它「给六个可独立派工的工作包」。
⇒ **那六个包的原文已不可恢复**（不在 git、不在 `~/.codex/sessions`）。

**后果与处置**：
- ⛔ 「按 12 条口径重排 sol 那六个工作包」这个下一步**无法照原文执行**；
- ✅ 改为 **orchestrator 按用户 12 条口径自行出派工表**（见下方「⏭ 下一步」的派工盘），
  并在表里注明哪几条是 sol 带回来的、哪几条是我方新排的；
- ⭐ **纪律**：`verdict/` 下的跨家族意见，**贴回原文与落库必须同一次动作**；
  「先落个壳、正文回头补」= 正文永远不会回来（换会话即失忆）。同族 [[list-the-directory-before-writing-a-new-doc]]。

### 五、本夜派出的三个席位（全部在独立 worktree，⛔ 主树只由 orchestrator 改文档）

| 席位 | 单子 | worktree | 内容 |
|---|---|---|---|
| **Claude 施工** | [G1 派工单](logs/reviews/request/2026-08-27_g1_gt_raw_layer_dispatch.md) | `/tmp/ep_g1`（`wt/08.27_gt_raw_layer`）| gt **原始层**可读 API + **机械复现门**（比内容字段⛔不比字节）+ 信任根显式化 |
| **Claude 施工** | [F-97 派工单](logs/reviews/request/2026-08-27_f97_contract_discriminator_dispatch.md) | `/tmp/ep_f97`（`wt/08.27_f97_contract`）| correction 只吃**声明过的契约**，未声明的**响亮失败** + 消费对账 |
| **GLM 复核** | [F-95 复核请求单](logs/reviews/request/2026-08-27_f95_concave_canonicalization_crossreview_glm.md) | `/tmp/ep_f95_review`（detached `ed0ba09`）| 审 `5b7a3a8`（GPT 施工），重点打「4 failed / **2 passed** 里那 2 格」+ 收窄契约有没有踩到真实调用方 |

**三份单子都写了同一组硬纪律**：工作目录写死 · ⛔ 不许动主树 · ⛔ 裸跑脚本会因 `.pth` 静默串台（一律 `python -m` / pytest） ·
「明确不做」清单 · **停下上报触发器（含「都次优但有更优解」）** · **orchestrator 自认最弱的一点，请优先证伪**。

⚠️ **踩到一个环境坑**：`scripts/glm_code.sh` 与 `scripts/deepseek_code.sh` **没有可执行位**（`-rw-r--r--`）
⇒ 直接 `scripts/glm_code.sh` 会 `Permission denied (exit 126)`；须 `bash scripts/glm_code.sh`。**登记，不改**（§0.1）。

### 六、F-95 的那条前置核查（08-26 说「查清之前不重派」）—— 已做，**只到 grep 级**

`canonicalize_ring_vertices` 全部调用点 = `geometry/build.py:79`（每个面）· `build.py:85`（每扇窗）·
`validator/data_model.py:1374` · `validator/checks/kernel.py:399`，四处输入都由内核自己按序产出
⇒ **看起来**没有调用方依赖旧 docstring 那句「能吃乱序/自交」。
⛔ **这只是 grep 级，不是行为验证** ⇒ 已作为「我方最弱的一点」写进复核请求单 §3.2，交 GLM 升级成行为验证。

### 七、⭐⭐⭐ 「没有可信的图纸↔世界标定」这句话**在 gt 侧是错的** —— 它已经存在，而且已经被签过字

CLAUDE.md 08-26 banner ③(a) 把「⛔ 没有可信的图纸↔世界标定（现在这个标定是 **reading 自己算的**）」
列为 gt 的四个缺口之一。orchestrator 本夜只读核查，**这条要更正**：

**gt 抽取 manifest 里本来就有逐视图的「像素 → 源坐标」仿射**，且每条都绑着该 PNG 自己的 sha256：

```
GtExtractionManifestV1.raster_overlays[] = RasterOverlayBindingV1
    { id, source_label, source_sha256, view_id, pixel_to_source_m: Affine2D }
                                                └─ 像素 → DXF 原生坐标（米）
PlanViewBindingV1.world_from_source_m : Affine2D   ← 源坐标 → 世界米
```

- sm25 的 manifest **六个视图全部填满**（`1f_view.png` / `2f_view.png` + 四立面），
  `manifest_sha256` 又被写进 `gt.json` 的 `generator.manifest_sha256`（= 在人工签字覆盖内）。
- **唯一的消费者是叠图渲染器**（`scripts/tool_scripts/render_gt_overlay.py:333 _pixel_for_world_plan`），
  ⛔ **没有任何判分路径用它**。
- ⚠️ **sm24 的 manifest `raster_overlays` 是空的 `[]`** ⇒ **这个能力不是全 case 都有**，
  跨 case 迁移前必须逐 case 查，⛔ 别假设它在。

#### 实测：判分侧那把尺子和产物自报的尺子，量出来差多少

拿 as-drawn 原型产物自报的标定，与 manifest 的仿射逐轴比（都换算到世界米，比**匹配刻度之间的跨距**）：

| 视图 | 轴 | 判分侧仿射 − 尺寸链真值 | 产物自报标定 − 尺寸链真值 |
|---|---|---|---|
| 1F | x | **+14.54 mm** | +9.05 mm |
| 1F | y | −5.68 mm | −6.70 mm |
| 2F | x | **+10.24 mm** | −3.09 mm |
| 2F | y | +3.83 mm | +3.49 mm |

⇒ 在 20–25 m 的跨距上两者都在 **±15 mm（≤0.06%）** 内，**判分侧那把略差一点**（合理：
产物是拿刻度拟合出来的，manifest 那把来自 DXF 视图框↔栅格的配准）。

**这三条结论要分开记，⛔ 别混**：
1. ✅ **[sol]#2「产品自报的标定不能用来换算它自己的答案」现在有解了** ——
   判分侧有一把**独立且已签字**的尺子，G3 从「发明一把标定」变成「**把已有的这把接上**」。
2. ⚠️ **它的残差要显式声明并进预算**：`reading_grade.py` 的 `POS_TOL_M = 0.08 m`，
   而这把尺子自带 **~15 mm** ⇒ **吃掉约 19% 的容差带**。⛔ 不许当零。
3. ⛔ **本次比对本身不是对判分侧仿射的验证** —— 我比的是「匹配刻度之间的跨距」，
   而那些刻度像素位置是**产物自己挑的锚点** ⇒ 同族 [[self-consistent-gates-anchor-on-product-chosen-apertures]]。
   它只能说明**两把尺子的比例尺一致**，⛔ 不能说明 manifest 那把的**原点**对。
   ⭐ 原点要验，必须拿**判分侧自己拥有的**特征（例如已签字叠图上 gt 外轮廓与图纸墙线的贴合）去验，
   而且要挑**没人细看过的那张图**（同族 [[half-measured-calibration-hides-as-downstream-gap]]：
   细看过的两张准到 0.31 px，没细看的那张偏 1.73 px）。

#### ⭐⭐ 而且产物侧的像素通道**已经在了** —— sol 那个判别实验今天就能做

as-drawn 产物的每条面线**同时**报两套坐标（sm25 1F 实测）：
`pos_px` / `runs_px` / `cols_px`（**像素**，读图器直接量的）**和** `pos_m` / `runs_m`（**世界米**，
用它**自己那把标定**换算出来的）。

⇒ **描图分可以完全在像素空间里判**：判分侧把自己的答案用 manifest 那把签过字的仿射投到像素，
与产物的 `*_px` 比 ⇒ **产物改自己的标定，描图分一个数都不会动**。
而 `pos_m` 那套降级成**另一个被判的答案**（= 标定分）。
⇒ **[sol]#2 那个判别实验（故意改产品标定 ⇒ 标定分该变、描图分不该变）现在是可实施的**，
⛔ 不需要先改产物 schema。

#### ⭐⭐⭐ 原点也验了：手填的世界零点与签过字的仿射，两张图都对到 **≤0.42 px（≤9 mm）**

08-23 那条教训（[[half-measured-calibration-hides-as-downstream-gap]]）说：
**尺度靠链拟合、原点靠手填**，我细看过的两张准到 0.31 px，**没细看的那张偏 1.73 px**。
现在有了判分侧那把独立的尺子，这个手填值**第一次可以被独立核**（实测）：

| 视图 | 产物 `declarations.world_zero_px_declared` | 判分侧仿射反解的世界零点像素 | 差 | 换算 |
|---|---|---|---|---|
| 1F | (281.5, 1234.5) | (281.852, 1234.916) | (0.352, 0.416) px | ≈ (7.6, 9.0) mm |
| 2F | (241.0, 1258.5) | (241.011, 1258.155) | (0.011, −0.345) px | ≈ (0.2, −7.5) mm |

⭐ 两张图**都在半个像素以内** ⇒ 手填原点这一轮是准的，且**从此不必再靠「有没有人细看过」来保证**。
⚠️ **诚实边界**：这只界定了**两者之差**，⛔ 不等于各自都对 —— manifest 那把仿射自身的精度我没有溯源
（它来自 DXF 视图框↔栅格的配准），只能说两条**独立**得到的原点互相印证。
⭐ 但这正是 [sol]#2 要的形状：**判分侧不再需要相信产品自报的东西**。

⇒ **G3 包的题面据此收窄**：① 判分侧读 manifest 的 `pixel_to_source_m` + `world_from_source_m`；
② 残差预算显式声明并从 `POS_TOL_M` 里扣；③ 逐视图 applicability（sm24 那种空 `[]` 必须**响亮降级**，
⛔ 不许静默回退到产物自报的标定）；④ 判别实验（[sol] 给的）：**故意改产品标定 ⇒ 标定分该变、描图分不该变**。
### 八、⭐⭐ 「gt 三层」重新定位：三层里有两层**已经存在**，缺的是**第三层与那道派生步骤**

把口径 12 的三层逐层对到盘上的东西（08-27 实测）：

| 层 | 用户口径 | 盘上现状 |
|---|---|---|
| **原始层** | 忠实转录，**含图纸自身的偏差** | ✅ **已有** —— `review/conversion_report.json`（逐边 basis/厚度/句柄）+ 已签字的 `source.dxf`。量化步长 `quantization_step_m = 0.0001`（0.1 mm）⇒ **没有做任何模数吸附**，图纸的偏差原样留着（例：F-96 那 60.3 mm、F-95 那条 14 顶点走廊）|
| **派生答案层** | 换出模形式只重新派生、**不必重签** | ✅ **已有一份** —— `gt.json` 本身就是「按外墙外皮 + 内墙中轴」这一种出模形式派生出来的（转换器用 `basis` + `offset = t/2` 把面线推成 zone 边界）。⛔ **但只有这一种**，且派生逻辑与「原始层」焊在同一次跑里 |
| **不规整清单** | **显式产出** | ❌ **不存在** |

⇒ **「gt 三层」不是给 gt 加两层，而是把现在焊在一起的东西拆开**：
**原始层（已有，缺的是可读 + 可复现的信任根 = G1）** → **一道显式的派生步骤（现在是隐式的）** → **派生答案层（已有一份）**。

#### ⚠️ 「不规整清单」有两种读法，两条路的产物**恰好是同一份清单**

- **读法甲**：gt 自己做模数吸附，清单 = **吸附动作的流水**（原值 → 吸附后 → 差值 → 依据）。
- **读法乙**：gt **不吸附**（保持忠实），只**声明**吸附分辨率给 correction 用（= 口径 9），
  清单 = **图纸本身相对声明模数的偏差表**（哪条墙不是 240/120 的整数倍、偏多少、原图就是这样）。

⭐ **orchestrator 取读法乙**，三条理由：
1. 口径 12 原文写的是「原始层（**忠实转录含偏差**）」——甲会让原始层不再忠实；
2. 口径 8/9 已经把**浮点吸附判给 correction**、把**分辨率判给 gt 声明** ⇒ 吸附动作本来就不在 gt 侧；
3. ⭐ 甲会踩中 08-26 记的那个陷阱：gt 与 correction 若跑**同一份规整实现**，规则错了两边一起错、
   判分全绿而建筑是错的（= F-95 的形状）。乙让 gt 只出**事实清单**、不出**规整规则**，两边天然不共用。

⛔ **但两条路要产出的第一份东西是同一个**：**逐条列出图纸相对声明模数的偏差**。
⇒ **G2 照做即可，不必等这条歧义定死**；真到要不要让 gt 自己吸附时再请用户拍。

#### ⇒ 由此，本批第三件目标（gt 修正 / gt 出判分答案）比 08-26 的估计**便宜得多**

08-26 记的四个 gt 缺口，08-27 逐条实测后：
**① 面线在哪** —— `as_drawn/denominator.py` 已经能从转换器自己的收集通道机械算出
（sm25 F1 实测：收 225 段 → 排 65 个门垛 → 160 个面段 → 44 条面线 → **110 个可评分目标 / 282.28 m**），
只是**每次现算、没落盘**；
**② 像素坐标** —— 有了 manifest 的 `pixel_to_source_m`（§七）就是**可算的**，不必标注；
**③ 可信标定** —— **已有且已签字**（§七）；
**④ 逐边 basis** —— **已有**（§二）。
⇒ **四条里没有一条需要新的测量或人工标注**，缺的全是**接线 + 信任根 + 落盘**。
### 九、✅ **F-95 跨家族审 = APPROVE，0 阻断** ⇒ 第 ① 步「C2 非方形」那半**收口**

裁决 → [`logs/reviews/verdict/2026-08-27_f95_concave_canonicalization_glm_verdict.md`](logs/reviews/verdict/2026-08-27_f95_concave_canonicalization_glm_verdict.md)
（GLM `glm-5.3`，独立 worktree，施工方 = GPT sol ⇒ 谁写谁不批成立）

**复核方自己跑的读数**：全量 `3035 passed / 13 xfailed / 0 failed`（与主树基线逐字一致）·
变异全量 `4 failed / 3031 passed`，**4 红全部落在 `tests/test_f95_*` 的四把保形锁、零外溢** ⇒ 定向变红成立。

#### ⭐⭐⭐ 它把我请求单里点名的三处「重点打」全部升级成了实测，而且三处的**框定都是我错**

| 我的题面 | 复核实测 |
|---|---|
| §3.1「`2 passed` = 新锁抓不住的两格，可能是真盲区」| ⛔ **误导性框定**。那两格锁的是**既有 IDF 输出契约**（绕向随 normal · 起点取 UpperLeft），旧实现按其算法性质**构造上就满足** ⇒ **不存在「该抓而没抓」**。F-95 判别锁在变异下 **4/4 全红**。把它们计进分辨力分母**会低估分辨力** |
| §3.2「收窄有没有把原本能跑通的路变成崩溃」（我只做到 grep 级）| ✅ **升级成行为验证**：真入口 `build_geometry` 前后对照电池 **13 个合法对抗配置 + 4 个垃圾输入，逐格一致**；⚠️ **但我的前提句错了** —— 退化环旧状态**不是「被悄悄修好」**：cell 层一直是上游 `cell_polygon` **响亮拒绝**，面层是 Newell 守卫**跳过**，共线三点**修前修后都接受** ⇒ 这些形态**从来没走过 canonicalizer** |
| §3.3「非简单环判定的数值容差是多少、误拒余量多大」| ⚠️ **我预设了容差存在，实际没有**：重复顶点判定是 `np.unique` **精确相等**、简单性委托 GEOS 鲁棒谓词、`area==0.0` 精确。⇒ 正确量纲是「**拒绝只发生在精确退化点，误拒带宽度 = 0**」：两角点相距 1e-3 / 1e-9 / 1e-15 / **5e-324** / 1 ulp **全部 ACCEPT** |

⭐⭐ **最值钱的一条**（我完全没想到去要的）：变异下**同一个 U 形顶点集、只换起点，得到 70 / 65 两个不同的坏形**
⇒ 坐实旧 `cmp_to_key` 比较器**不是全序**。这比「面积对不上」硬一档。

#### 四条不阻断 findings 的去处

| # | 内容 | 去处 |
|---|---|---|
| N1 | 唯一残余理论窗口 = shapely 布尔运算产物自带**精确重复顶点**；13 配置电池（含全部 F-96 碎片宽度）未触发；且旧实现在同一形态下**同样把坏环静默送进 IDF** | ⏭ **并入 F-96**（跨层碎片守卫）一起做，⛔ 不单独开工 |
| N2 | 新合同的「非简单」外延与 GEOS `is_valid` 在「精确重复顶点」一格**不相交**（GEOS 说 valid，本函数拒）——属**合理从严** | 知悉；已由 N1 说明真实路径不产此形态 |
| N3 | `classify_ring_change` 的 `"resorted"` 类别在新合同下**生产侧永不触发**（docstring 已标注为历史诊断类）| ⏭ 分类学债，登记 |
| N4 | 施工方 worktree 的「3034+1 红」= 环境凭据差 | ✅ 已定位为 **`.env` 被 gitignore ⇒ worktree 里没有它**（见本日 §五后记）|

#### 计数

- **「停下上报」→ 36/36**（本日 F-97 那条，仍是我题错）。
- **另加：复核方点出我请求单题面问题 3 条**（上表三行）。⛔ 这三条不是停下上报（GLM 照做了），单独记。
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
