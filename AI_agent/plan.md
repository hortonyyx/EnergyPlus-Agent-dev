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
| **⭐⭐ 新 F-90** | ⛔ **correction 侧判分对多层 case 整份被拒，真因是楼层 id 两套命名且无映射层**：判分绑定用 gt 的命名 `floor_id="F1"/"F2"`，而 correction 产物的窗用管线内部命名 `floor_id="floor_1"/"floor_2"`；[`score_service.py:371`](../src/agent/judge/score_service.py#L371) `plan_sources.get(window.floor_id)` 取不到 ⇒ 抛 `score_view_binding_invalid`（gate `scoring.view_bindings`）⇒ `score_vs_gt.payload.kind="rejected"`，**十个判据一个都没跑**。⭐ 与 **F-89 是一对**：F-89 让立面侧判不了、F-90 让 correction 侧判不了 ⇒ **C2 批两侧至今都没有被判过分**。实测 2026-08-25 `run_2026-08-25_c2_rescore_R0`（gate① 反而是零 block 零 flag 通过的）| **登记**（2026-08-25）· ⛔ 碰 `src/agent/judge/` 须派工 |
| **⭐⭐⭐ 新 F-91** | ⛔ **C2 的「立面多平面」在 correction 产物里是空的，窗因此无法定位**：sm25 实测 `facade_segments = 0`、**31/31 扇窗的 `facade_segment_id` 全为 `null`**。⭐ 而 L 形上「北」「东」各自**不是一道墙**：朝北的有 y=20(x 0→15) 与 y=6(x 15→25) 两道、进深差 14 m；朝东的有 x=15(y 6→20) 与 x=25(y 0→6) 两道、进深差 10 m。实测 F1 北面有一扇窗 span=[15.3,23.3]，**完全落在 y=20 那道墙的范围之外**（那道墙只到 x=15）⇒ 它属于 y=6 那道，但没有任何字段这么说 ⇒ 渲染器与下游只能猜，窗被画到楼外（用户 2026-08-25 目视发现「窗户没在位置」，orchestrator 复核属实）。⭐⭐ **沿墙数值本身是全对的**：31/31 扇与 gt 的 `world_along_interval` 两端误差合计 **0.0 m** ⇒ ⛔ **不是算错，是没绑定**。⚠️ **2026-08-25 晚补注（免得两个数打架）**：当天「答案直喂内核」的诊断里测到 `facade_segments` = **16 条非空** —— ⛔ **那不构成本条已消失的证据**，两者输入不同：本条测的是 **R0 的真实 correction 产物**，那次测的是**从 gt 机械派生的输入**。⇒ 只能说明「立面段在答案输入下产得出来」，⛔ 不能说明「模型产的那份为什么是空的」。 | **登记**（2026-08-25）· 这是 C2 阶梯表里 C2 那一行的「立面多平面」本体 |
| **⭐⭐ 新 F-92** | **cell 多边形能力未被使用**：sm25 实测两层 38 个 cell 的 `polygon` **全为 `null`**，全部是 x/y 矩形区间。⭐ 后果不是「切错了」——实测 F1 19/20、F2 18/18 的 cell **≥95% 落在单一 gt 分区内**、零 cell 越界、零 gt 分区漏覆盖；真正的差别是 **gt 把整栋走廊建成一个 18 顶点连通多边形，correction 把它拆成 7 个矩形**。⚠️ 并注意 gt 自己也几乎全是矩形（F1 13/14、F2 14/15 是四边形），⛔ 所以「矩形化」本身不等于错，错的是**非矩形的那一个（走廊）无法表达** | **登记**（2026-08-25）· C2 阶梯表「cell 多边形」本体 |
| **⭐⭐⭐ 新 F-93** | ⛔ **全仓已红 4 项且两天无人发现，四项同源 = gt 重签后锁与夹具没跟着更新**。2026-08-25 主控权威全量实测：**3010 passed / 1 failed / 3 errors / 13 xfailed**（⛔ 不是 CLAUDE.md §1.3 仍写着的「2835 绿」）。**已在昨天的提交 `f7d64f4` 上复跑，同样 4 项红 ⇒ 与今日工作、与工具箱转正均无关。** 逐项：① `test_elevation_score_bindings::test_generator_fails_closed_on_sm25_multi_floor_fingerprint` —— 它 assert「两层 footprint 指纹不一致时生成器必须 fail closed」，而 **08-22 用户拍板的 S1 修法正是让指纹逐位一致**；实测 sm25 两层指纹与顶点均**逐位相同** ⇒ **锁的前提已被修没了，锁是陈旧的，⛔ 不是生成器回归** （同族 [[regression-case-must-prove-its-own-premise]]）。⭐ **推论：orchestrator 2026-08-25 用该生成器建的六图绑定是合法的**。② ③ ④ `test_reading_typed_score_f67` 三项 ERROR = `score_view_binding_invalid / identity mismatch`：夹具指向的 `run_2026-08-21_c2_first_sonnet_T1` 记的 `gt_content_sha256=f97cea65…`，而当前 gt 是 `135b282c…`。⭐ **时间线**：锁改于 `96604c9`(08-22)、gt 改于 `e982eba`(08-23) ⇒ **gt 晚于锁一天入库，锁没跟着走**。⚠️ **治理后果**：期间所有「全仓绿」的说法都是失效的口径 | **登记**（2026-08-25）· 修法须派工（碰 `tests/`+夹具）|
| **⭐⭐ 新 F-94** | ⛔ **venv 里的 editable-install `.pth` 硬编码指向主树，合并回主线后会从「响亮失败」变「静默串台」**：`/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth` 内容 = `/workspaces/EnergyPlus-Agent-dev`（主控实测确认）。后果：在**任何非主树的工作树**里**裸跑**（非 `-m`、非 pytest）一个 `from src.xxx import …` 的脚本，若脚本自身目录下无 `src/` 包，`src` 会**静默从主树解析**。⭐ 由施工席位在转正工作中撞出并用探针实测复现；跨家族审（GLM）独立确证根因链：脚本模式 `sys.path[0]`=脚本目录 → `src` 落主树 → `REPO_ROOT` 指错树 → 路径守卫 raise，并实测受影响面三项（探针 / `inspect_dxf` 两测试 / `reading_toolbox` 裸跑 `ModuleNotFoundError`）。⭐⭐ **GLM 判定为合并前必须处理项**（合并后同名文件在两棵树都存在，踩坑不再报错、改成静默用错那棵树的代码）| **登记**（2026-08-25，跨家族审随裁决带出）· ⛔ **合并回主线前必须处理** |
| **⭐⭐ 新 F-97** | ⛔ **新识图产物会被当原始文本喂进校正提示词，同时绕过识图门 —— 一条沉默路径**：`discover_vector_files`（[pipeline.py:84-107](../src/agent/pipeline.py#L84)）扫 `*.json` **全部**并分成 plans / elevations / **`others`**（= 不匹配平面图正则、且不以 `_view.json` 结尾的所有 JSON）⇒ 一份 `sm25_1f_v2.json` 放进 `0_reading/` 会落进 `others` 并进提示词；而识图门 [`evidence_preflight.py:229`](../src/agent/execution/evidence_preflight.py#L229) 只 `glob("*_view.json")` ⇒ **看不见它**。⭐ **由 GPT 跨家族设计答复点出，orchestrator 已独立复核两处代码 + 做了行为实测**（⛔ 不是只读代码）：把 `1f_view.json` 与 `sm25_1f_v2.json` 并排放进一个 `0_reading/`，`discover_vector_files` 返回 **`['1f_view.json', 'sm25_1f_v2.json']`** ⇒ **as-drawn 产物确实会进 correction 的输入**；同一目录上 `compute_reading_report_from_vector_dir` 跑了 **21 项检查、0 阻塞** ⇒ ⭐⭐ **门不只是看不见它，还给出了绿灯** —— 比「看不见」更糟。⛔ **它比「喂不进去」严重**：喂不进去是响亮失败，这条是**静默地半喂进去**。⇒ 一体改的**契约判别器**必须显式化：未知契约类型响亮失败 | **登记**（2026-08-25）· ⛔ 碰 `src/agent/pipeline` 须派工 |
| **⭐⭐⭐ 新 F-95** | ⛔ **顶点规范化把凹多边形毁掉，而校验器与生产者共用同一个实现**：[`canonicalize_ring_vertices`](../src/validator/data_model.py#L1047) 用**绕质心角度排序**重排环，对凸多边形能还原、**对凹多边形还原成另一个形状**。离线夹具 [`concave_canonicalization_matrix.py`](logs/experiments/2026-08-25_kernel_probe_from_gt/tools/concave_canonicalization_matrix.py)（不需 gt/LLM/跑抽）：矩形 **OK** · 单凹角 L 形 84.000→84.000 **OK** · **U 形 8 顶点 76.000→70.000** · Z 形 8 顶点 68.000→68.000 **OK** · **梳形 12 顶点 66.000→59.000** · **sm25 走廊 14 顶点 97.731→226.457**。⚠️ **该表当场证伪了 orchestrator 初稿的断言「两个及以上凹角就坏」—— Z 形 2 凹角却无损** ⇒ **凹角数不是判据**，判据是「顶点绕质心的极角是否单调」，凹是**必要非充分**条件 ⇒ ⛔ 按「有没有凹角」挑回归夹具会挑出假绿的那一半。实测后果：`Z10_F1_Office_S` 地板面积 **226.457 vs 自己的轮廓 97.731**（2.3 倍）、`Z22_F2_Office_SW` 174.332 vs 78.558 ⇒ `kernel.zone_closure` 4 条阻塞。⚠️ **规范化后的环仍 `is_valid=True`** ⇒ 任何"多边形有效性"检查都放行，**只有面积对账抓得住**。⭐⭐ **两条附带教训**：① 已有的 `test_lshape_polygon_clean` 断言的正是那个**恰好无损**的单凹角 L 形 ⇒ **有锁 ≠ 有分辨力**（[[neuter-proves-wiring-not-discriminating-power]]）；② kernel 与 validator **刻意共用**这一实现（build.py 注释：避免 F-13 两套算法分歧）⇒ 校验器与生产者共享同一个错误假设。⭐ **打击面已界定**（`grep` 清点调用点）：生产侧 [`build.py:78`](../src/agent/geometry/build.py#L78) 对**每个面**、[`:84`](../src/agent/geometry/build.py#L84) 对**每扇窗**各跑一次；校验侧 [`data_model.py:1338`](../src/validator/data_model.py#L1338) 与 [`checks/kernel.py:398`](../src/validator/checks/kernel.py#L398) **用同一个函数**。⇒ ⭐ **实际受害的只有凹多边形 zone 的 Floor/Ceiling/Roof** —— 墙面与窗都是矩形（凸），规范化对它们无损。**这与实测自洽**：`zone_closure` 报的正是 `floor_area` / `top_area`，⛔ 没有一条 wall 告警。⇒ 修法的回归面应据此收窄。⭐ **现行管线撞不到它**：R0 的 38 个 cell 带 `polygon` 的 = **0**（全 bbox=凸）⇒ 与 **F-92 是一对**（多边形能力没被用，所以它的缺陷也没被暴露）| **登记**（2026-08-25，答案直喂内核撞出）· ⛔ 碰 `src/validator/`+`src/agent/geometry/` 须派工 |
| **⭐⭐ 新 F-96** | ⛔ **跨层切分产生的碎片没有守卫，而同层吸附还把它做得更小**：1F 一道隔墙中轴 `y=15.9996`、2F 对应 `y=16.06`。⭐ **已溯源到原始 DXF 逐条坐标**（`sm25-L_t3.dxf` `WALL` 层，mm）：1F 右半段两条面线 44153.221/44273.221、其余三处（1F 左半段 + 2F 两段）均为 44213.552/44333.552 ⇒ **四处厚度都是 120，错位的是位置：1F 右半段那道墙整体往南偏 60.3 mm** ⇒ ⛔ 既不是转换器造的、也不是噪声、更不是两种墙厚，**原图就这么画的**，gt 忠实转录。确定性核第二步破坏第一步 —— ① 跨层对齐判 `provenance-aware sliver guard kept axes separate`（delta=0.0，决定不合并）；② 同层吸附随即把 1F 那条推到 **16.03**（delta=0.0304，`AXIS_JITTER_TOL+SNAP_GRID+MIN_EDGE_LENGTH`）⇒ 间距 0.0604 **缩到 0.03**，方向正朝着它刚判定要保持分离的那条轴。跨层切分于是切出 **0.03 m 宽**天花/地板条，InterZone 门事后报 `degenerate surface … EP may segfault`。**三点判别**（只改这一个量）：0.0604→2 条 · 抖动归整 0.0600→**仍 2 条**（⇒ 与 0.4 mm 抖动无关）· 拉到 0.20→**0 条** · 完全对齐→**0 条**。⭐ **别记错主因**：0.06 本来就 < 碎片下限 0.1，**不挪也会出碎片** ⇒ 主因 = **跨层碎片无守卫**，吸附朝错方向挪只是**加重因子** | **登记**（2026-08-25，同上）· ⛔ 碰 `src/agent/correction/deterministic.py` 须派工 |
| **⭐ 新债 D-1** | **`tools/` 原件与 `src/` 新件双份并存**：跨家族审裁定 (a) 接受双份 + 登记 + **限期退役**。成因是 `glm_cheats.py`/`glm_rework.py`/`glm_probes.py`/`glm_sweeps.py` 用 `spec_from_file_location` **按文件路径**加载被搬走的模块，删原件会炸掉五轮跨家族审累积的全部作弊夹具。⛔ 与「不两处并存」冲突，**日后改一份忘另一份是必然的**。⇒ 退役动作 = 夹具改成按模块加载，**须另开单** | **登记**（2026-08-25）|
| F-62 · N-1 / N-2 | guard 词法围栏同族缺陷 | **未修**（`observe` 档下影响归零）|
| F-63 | 跨轴门抓不住拆轴规避 | ⭐ **本轮活体复现**（GPT 主动拆轴消警）；修法归 [专项 §9.1](capability/reading/improvement_methodology.md) |
| F-64 | gate① 对「零产出」是瞎的 | 登记 |
| ~~v3 判卷 null `scale_origin`~~ | ~~sm24 准入门~~ | ✅ **本轮已解**（`f2ea22e`，GLM 施工）|
| — | 全链无门校验「note 里的换算式 ↔ 笔画坐标」一致性 | ⭐ 确定性可查、成本低 |
| — | 读图器会自发产出**清单外文件**（`_validated_1f_view.json`）| 本轮由 merge 门拦住并归档；登记 |

**复审债**：甲-5 · 丙-1 / 丙-2（同前）。**本轮新增零复审债**——转换器批已由 GLM 跨家族审 + 主控轻门。

---

## 2026-08-25 · **架构定稿 + 管子拆开 + 工具箱转正(APPROVE)**；C2 首次被真正量过

> 全档见各提交（`08.25a`–`08.25l`，12 个）。⛔ 本节只留结论与指针。

### 一、reading 侧（做完的）

- ⭐⭐⭐ **架构落成独立文档** → [architecture/reading_pipeline_architecture.md](architecture/reading_pipeline_architecture.md)
  （用户令「架构的东西都落到 architecture，单独一个文档」）。含**三层归属**（量具=代码当卡尺 / 工序=模型 / 出口=代码且 agent 改不动）·
  **SOP 与判例是两份东西** · 落地节奏「现在先代码固定编排，后期改模型驱动」· **九条已知盲区**。
- ⭐⭐ **判分口径细化**（用户定，进 guide §四）：**reading 判「描得像不像」· correction 判「画得对不对」**，
  因为 correction 之后信息才简化收束。⛔ 别再把完备性负担全压给 reading（那是**分工塌了**，不是 reading 强）。
- ⭐ **新判分器的 grade 图落成** → `render_reading_grade.py`（旧那张是 v1 时代的，与新判分器对不上）。
- ⭐ **T 形接头已解**（用户定「橙色标注，不扣分」）：真因不是「该不该扣」，是**分母凭空多要 3.36 m**——
  答案的 DXF 在另一堵墙落脚处本来就断成两段，`merge_m` 把它们焊起来了。
  修法 = 目标**保持完整但带洞**（洞里不要求 C2、不罚 C4，两端仍在真墙端故 C3 不受影响）。
  ⭐ 副产品：**`merge_m` 彻底不承重**（0.0→2.0 恒 110 目标 / 278.92 m）。诚实数 C2：98.6→**99.2** / 97.0→**97.8** / 97.5→**97.9**，其余判据逐字段未变。
  ⛔ 中途错修一次（先做成「切开目标」，C2 涨了但 C3 错切 0→8、C4 多画 0.72→2.65 —— 惩罚只是换了个口子出来）。
- ⭐⭐ **管子拆开**：`as_drawn_v2.build()` 316 行 → **9 个可单独调的工序 + 薄 build()** + CLI `reading_toolbox.py`
  （`pens`/`ruler`/`faces`/`pairs`/`gaps`/`build`）。**验收 = 三个 view 产物逐字节相同**。
- **两组实测已进架构文档盲区节**：① 六个「只改语义不动几何」的变异 ⇒ **grade 判语义错误的后果、门判语义声明本身**，
  ⛔ 两个都看才闭合（唯一盲区=族角色对调，grade 一个数不动、门 2 道红）；
  ② **「墙统一记成有厚度的墙带」评估后不采纳**（它就是五审 `band_collapse` 的形状）；
  配对负担实测 374/303/1185 候选里真需判断的只有 **2/1/0** 个，⛔ 但「互为最近邻」会把两条「240」标注文字配成一堵墙（间距 0.1190/0.1082 m）。

### 二、C2 验证（sm25，⏸ 已按用户令停在 correction）

⭐ **成的**：L 形外轮廓 **8 顶点逐点对上、拓扑完全一致**，每点朝内缩 0.11–0.13 m ≈ 半个 240 墙厚
⇒ **形状全对，只差一条系统性基准换算**。窗**沿墙数值 31/31 与 gt 误差 0.0 m**。gate① 零 block 零 flag。

⛔ **没成的**（用户目视三条，复核后两条属实一条不成立）：
**F-91** 立面多平面在产物里是空的（`facade_segments=0`、31/31 扇 `facade_segment_id` 全 null）⇒ 窗被画到楼外 ·
**F-92** cell 多边形未被使用（38 个 cell 的 `polygon` 全 null）·
⚠️ **「内部识别很差」数据不支持**：F1 19/20、F2 18/18 的 cell ≥95% 落在单一 gt 分区内、零越界零漏覆盖；
差别只有走廊（gt 一个 18 顶点多边形 vs correction 7 个矩形），**而 gt 自己也几乎全是矩形**（13/14、14/15）。

⭐⭐ **两侧都没法判分**：**F-89**（一张立面跨两层就整份丢）+ **F-90**（楼层 id `F1` vs `floor_1` 无映射层）
⇒ **C2 批落地后两侧至今一次都没被判过分** —— 这就是「C 批拖久了」的实际状态：**不是没落地，是落地了但没有尺子量过**。

⛔ **并更正主控自己一处**：J0 裁定里把 reading 那 20% 判为 `correction_recoverable`，
**实测 correction 并没有消化它**（footprint 仍停在 0.12 的面线基准）。

### 三、工具箱转正 + 跨家族审

- **派工两次**：第一次施工席位被分到一棵**停在 560 个提交之前**的 worktree，它**停下上报**（只读诊断、零改动、不编造）
  —— **是主控选的隔离方式出的错**，「停下上报」累计 **23/23 全是派工方题错**。
- 第二次（Claude/Sonnet，主控自建 worktree）交件 `283e868`，**GLM 跨家族审 ✅ APPROVE**
  → [裁决](logs/reviews/verdict/2026-08-25b_toolbox_transplant_crossreview_glm_verdict.md)。
  ⭐ 它做了主控没做的一步：**在原路径搭对照组把夹具矩阵跑两遍，两份 RESULTS 深度逐字段 0 差异**。
  ⭐ 并逐版本 `git show` 独立确证 F-93 那条推论 ⇒ **主控 08-25 建的六图绑定合法，当日 C2 结论不作废**。
- 主控抽验两条均证实 GLM：`checks/as_drawn` 实为 **5 处** import（施工方自述「4 行」漏报一处）· `.pth` 内容确为主树绝对路径。
- ⛔ **更正主控自己**：我说多出的 3 项红「都是 worktree 环境产物」，GLM 只确证 2 项，第 3 项复现不出
  ⇒ 应记为 **4 前置 + 2 环境产物 + 1 未复现**。

### 三之二、⭐ 拿 sm25 的答案直接喂内核（用户 2026-08-25 提，探索档，⛔ 永不作成绩）

> 用户原话：「能不能直接捏一份答案出来从 correction 之后走呢？我还是想看看几何内核那部分有没有问题，
> 反正这个不计入跑测」。⛔ **答案在输入里 ⇒ 任何"对答案"的分数都是同义反复**，本节一切产物不进成绩账。

**全档 → [`logs/experiments/2026-08-25_kernel_probe_from_gt/`](logs/experiments/2026-08-25_kernel_probe_from_gt/README.md)**

- **先零成本侦察**：R0 那份已 accepted 的 correction 直接喂内核 ⇒ **38 zone / 266 面 / 31 窗 / InterZone 0 条 / gate①(kernel) 6 项 0 阻塞**
  ⇒ ⭐ **sm25 停在 correction，不是因为内核跑不动。**
- **方法上没伪造信任根**：v3 每扇窗必须逐扇引用 `0_reading` 观测，gt 不带 ⇒ **骨架取 gt、窗的引用取 R0**，
  走**真实生产路径**（`finalize_correction_draw` → 由普通验证器签发 B5 proof）。
  31 扇 gt 窗 ↔ 31 份 R0 引用**一一对应零冲突**；窗证据链 verified；gate①(correction) **17 项 0 阻塞**。
- ⭐⭐ **撞出两条独立缺陷 → F-95（顶点规范化毁凹多边形）· F-96（跨层碎片无守卫）**，见上表。
- ⛔ **本轮明确没做**：没修任何 `src/`（两条都属须派工那一类）· 没跑 4_mep/5_intakeoutput（要花钱）·
  **F-91 没查**（附带观测：答案输入下 `facade_segments`=**16 条非空**，⛔ 这不构成 F-91 已消失的证据）·
  `--basis outer` 那一支在窗宿主处被拒（⇒ **门拦得住基准错配**，正面证据）
  ⇒ **「半个墙厚值多少分」这个量本轮没有量到**。

### 三之三、⭐⭐ gt 该录"原图"还是录"合理建筑"（2026-08-25 用户提，orchestrator 有不同落点）

> 用户（**图纸作者本人**）确认那 6 cm 是画图时的偏差，并主张：
> ① gt 应**按一个建筑**来做而不是按孤立图纸；② gt 应做成**按图纸少量修复后的合理建筑**，
> 而不是原样录入；③ **gt 加一道校验**；④ 这类看不出来的误差**本来就该被 correction 吸收**。

**①③④ orchestrator 完全同意**（④ 尤其：guide §四之二 早就写着「模数吸附归 correction，⛔ 尚未实现」，
用户这句话与现行口径一致，是**登记了没做**的事）。
**② 建议换个落点**，理由是两条，都不是偏好问题：

1. **gt 铁律**（CLAUDE.md §0.3#1）：动 gt = 全部历史成绩作废。
2. ⭐ **更要命的是判据会塌** —— ⚠️ **但这句要写准确**（2026-08-25 GPT 跨家族答复更正 orchestrator，已接受）：
   会塌的前提是「**只保存归一化后的答案、把原始层覆盖掉**」；那时「correction 到底有没有吸收这个偏差」
   就永远判不出来 —— 答案里已经没有偏差，吸不吸收都是同一个分
   （[[silent-default-threshold-behind-otherwise-conclusions]]）。
   ⭐ **归一化的答案本身并不有害，恰恰是它才能区分「已吸收」与「未吸收」**；有害的只是**丢掉原始层**。
   orchestrator 此前对用户的措辞漏写了这个前提，特此更正
   ⇒ 下面那套三层方案本来就规避了它，**结论方向不变**。

⭐ **正解是用户自己 2026-08-20 定过的那条**：「**gt 不应是一张确定的图，而应是原始信息集合，
按出模形式派生对应的标准答案**」⇒ 三层而不是二选一：
**原始层忠实转录**（含偏差，可查）+ **显式的「图纸不规整清单」**（校验产出，⛔ 不是悄悄改）
+ **按出模规则派生的答案层**（吸附在这里发生，规则换了可重新派生、⛔ 不必重签 gt）。
correction 的靶子于是明确：它要把 15.9996 和 16.06 收成同一条，而判分对着**派生层**判，判得出来。

**⛔ 并实测出一条硬前置**：普查工具撞了两次墙（详见实验档三之二）——
按距离聚类**恰好漏掉**那处 60.4 mm；换结构判据后 11 条里 **9 条误报**（外墙两个面在拐角处支撑同样不重叠）。
⇒ **纯坐标分不开「真墙」与「画图偏差」，两者数值上重叠**；可靠判据只能是重算式的
（「这段距离等不等于某条已知墙的实测厚度」）⇒ **需要 gt 保留逐边 `basis`+`thickness`
—— 那正是已登记的 R-6** ⇒ **「gt 加校验」与 R-6 是同一件事，⛔ 不能分别排期。**

⭐ **R-6 的工作量应下调重估**（2026-08-25 复核 GPT 引用时撞出）：
`ZoneEdgeReportV1`（[tarch_converter_schema.py:1096](../src/agent/judge/tarch_converter_schema.py#L1096)）
**已经是一个正式定义好的 schema 类型**（`p1`/`p2`/`basis`/`thickness_m`/`offset_m`/`derived_handle`）
⇒ ⛔ **不需要重新设计记录格式**，缺的只是**把它晋升进 gt 的序列化**
（`GtZoneV3` 现在只有 `id`/`name`/`role`/`polygon`/`source_refs`，
[gt_schema.py:164](../src/agent/judge/gt_schema.py#L164)，确实没有任何厚度或基准字段）。

**已 DXF 确证的两处偏差**：1F 右半段隔墙整体南偏 **60.3 mm** · 1F 左段同一道隔墙分两段画差 **0.088 mm**
⇒ **量级差 700 倍、成因不同**，⛔ 别指望一条规则同时收掉。

### 四、⏭ 下一步（用户 2026-08-25 定序）

> 用户口径：**支线回并之后统一按新 reading 做**（免得版本不匹配）；**新 reading 落地后先拿 sm25 全流程撞通**；
> ⭐ **「新 reading 本身就和 correction 是一体的，要一起改」**。

**⭐⭐ 今天新发现的最大缺口：as-drawn 产物喂不进 correction。**
correction 读 `*_view.json` 的 `strokes`（带 `pen`，prompt 还引用笔画 id、数 `pen=="window"`），
as-drawn 产 `observations.face_lines`/`hypotheses` —— **两套 schema 完全不通，零接线**。
且**基准不同**。⭐ **2026-08-25 更正归属**：原写「旧 reading 自述唯一基准=墙中线」，复核后找到更硬出处 —— **是 `1_correction` 的提示词在要求中线**（[pipeline.py:365-369](../src/agent/pipeline.py#L365) 逐字写着 `wall-centerline` / `wall CENTERLINE`）⇒ **不是 reading 换格式要适配，是 correction 自己在要这个基准**，一体改必须动那两句字符串。
⇒ 写转换层塌成中线 = 在 reading 侧偷偷替 correction 干活并扔掉信息（**R-6 同形**）。
⇒ **用户已定方向：reading 与 correction 一起改。⭐ 先拉 sol 讨论架构**（涉及 reading 专项 + 出模专项主体）。

| 阶段 | # | 事项 | 状态 |
|---|---|---|---|
| **0 清合并阻塞** | 0-a | **F-94** venv `.pth` 硬编码主树 | ⭐ **派工单已出**（先出方案后施工）→ [单](logs/reviews/request/2026-08-25_merge_blockers_f93_f94.md) · **待用户拍板派发** |
| | 0-b | **F-93** 全仓 4 项红（陈旧锁 + 陈旧夹具） | ⭐ **同一张单**（已与 0-a 打包）· 四项 2026-08-25 由主控复跑确证 |
| | 0-c | 重跑 `RESULTS_v2.json`（陈旧，主控造成） | ⏭ 主控 |
| | 0-d | 合并 `toolbox_into_src_08.25` → `08.23_AsDrawnReading` | ⏭ |
| **1 新 reading 落地** | 1-a | ⭐⭐ **reading + correction 一体改**（含 as-drawn→correction 接线） | ⭐ **先与 sol 讨论架构** → [讨论稿](logs/reviews/request/2026-08-26_reading_correction_joint_architecture_discussion_sol.md)；⭐⭐ **备料已到**：GPT 跨家族设计答复 → [全档](logs/reviews/verdict/2026-08-25_reading_correction_unification_gpt_design.md)（**证伪了我方倾向**：接口不能定成「吃两条面线」—— sm24 实物有 4 堵墙是单条实心带）|
| | 1-b | **冷启读图器首考**（模型真产 perception）| ⛔ 要花钱，待拍板 |
| | 1-c | 补新工具 + 判例 + SOP | 用户定：属 harness 迭代，**回并后再做** |
| | 1-d | **F-90** 楼层 id 映射（否则撞通了也量不了）| 建议提前到本阶段 |
| **2 撞通** | 2-a | sm25 全流程（用新 reading）| **用户 08-25 定：推完主线再用 sm25 撞，把 C2 批的问题撞出来** |
| | 2-b′ | **F-95 / F-96**（答案直喂内核已撞出，见「三之二」）| 撞通时一并处置 |
| **3 gt 层** | 3-a | ⭐ **R-6 + gt 不规整校验（同一件事）** | 用户 08-25「**这个可能要提前了**」⇒ **建议并进本阶段，不单独提前** |
| | 3-b | correction 的**模数/共线吸附**（guide §四之二 登记未实现）| 建议并进 1-a 一体改 |
| | 2-b | **F-89** 多层立面判卷 | 立面侧再说 |

⛔ **D-1 双份代码债**（`tools/` 原件与 `src/` 新件并存）：GLM 裁定 (a) 接受 + 登记 + **限期退役**，退役须另开单。

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
