# reading 环节目标形态与架构 · 设计细稿

- **日期**：2026-08-02
- **出稿**：Fable 5（最高档规划席位，点射）
- **回应**：`AI_agent/logs/reviews/request/2026-08-02_reading_architecture_design_brief.md`（下称「问题书」）
- **性质**：设计细稿，非施工。本稿**累计式自包含**——不引用任何被覆写的旧稿，新执行者只读本稿即可施工。
- **术语**（问题书 §0.0，本稿全篇遵守）：**orchestrator**（端到端主控，只能启动与接收）·
  **reading-agent**（reading 环节内部的调度）· **reading-worker-agent**（实际读图产出观测的 VLM）。

---

## 0. 结论先行 + 我对问题分解本身的意见

### 0.1 一句话结论

07-07 那次 100 % 的产物，拆开看不是「一次运气好的读图」，而是一条**可枚举的工序**：
标定（带残差自检）→ 对候选逐个核验（CV 工具产出的候选集，每条都被显式接受/拒绝并写明理由）→
尺寸链闭合自检 → 跨图（平面↔立面）互证 → 诚实登记测不到的部分。
这条工序里，**orchestrator 当时做的干预**（"打回：只描了主要墙、违反完整性"）
**对应的正是这条工序里"候选没有逐条核验完"这一步的失败**——这是一个**可由代码判定的事实**
（候选集哪些被处置了、哪些没有），不需要人看图才能发现。

**这意味着 Q-D 的答案不是"设计一个更聪明的 reading-agent 去替代 orchestrator 的判断力"，
而是"把 orchestrator 当时能看出来的那几件事，变成 gate① 能看出来的几件事，
再让 reading-agent 去消费 gate① 的结论、触发一次有界返工"。**
reading-agent 本身应该**尽量笨**——它甚至不需要看图（详 Q-D）。真正需要长进的是 gate①。

### 0.2 我对问题书分解的意见（按要求直说）

**Q-B 的提法本身需要修正**："完成度由谁判定"暗示存在一个干净的单一判定者。
**证据不支持这个预设**：§1.6 的自评不可靠、§1.9 的预扫召回不足以当分母、§1.3 的 provenance 字段不相关，
三条独立证据分别否决了三个"单一判定者"候选。**真实答案是一个复合信号集，且明确留有盲区**
（详 Q-B ④）。我把 Q-B 改写为两问：**Q-B-1**（哪些独立信号可以合成一个复合完成度判据）
+ **Q-B-2**（这个复合判据的已知盲区谁来收口、怎么收口——这条问题书没问，但没有答案会让人误以为
gate① 修好之后就"判得准"了，这是危险的默认）。Q-B 正文按这两问回答。

**Q-F 的 Recipes 分层有一处会重开口子**：问题书把 Recipes 描述为"按图纸风格**与能力档**版本化"。
按能力档给**不同工具**违反 §0.3"不为 Haiku 定制方案"的铁律——工具的正确性不能因跑在 Haiku 还是
Sonnet 上而不同。我在 Q-F 里把它收窄为：**工具本体唯一，随能力档变化的只是"要不要默认自动触发"这个调用策略**。

**没有漏问的大问题**，但 Q-D 里藏着一个问题书没单独列出、却是本批次能不能算数的关键——
**§2.3 最后一条**"验收必须脱离 dev 期开发者角色完成"。这不是一句纪律声明就能兑现的，
需要一个**结构性**答案（谁的会话产出了被接受的产物、dev 角色能不能碰到那个会话）。
我把它并入 Q-D ⑥（撤除路径/角色隔离）一起回答，而不是新开一问——因为它和"reading-agent
怎么固化"共享同一个架构接缝：**两者都是"外部观察/调整 只能通过修改下一次运行读到的文件生效，
不能通过任何实时通道进入当前这次运行"**。

### 0.3 全局架构总览（后文 Q-A…Q-H 的落点一图/表说清）

```
orchestrator（只能启动/接收）
   │  create job(FrozenCaseBundle, ReadingProfile) ──────────────────────┐
   ▼                                                                     │
ReadingService.run(bundle, profile) → (status, output, evidence_manifest)│ 只能等待/接收
   │                                                                     │
   │  内部（orchestrator 不可见、不可伸手）：                              │
   │                                                                     │
   │  ┌── reading-worker-agent 第一遍（VLM，看图）──────────┐            │
   │  │      产出 5×ReadingView + candidate_ledger（新字段）│            │
   │  └──────────────────────────────────────────────────┘            │
   │                        │                                          │
   │                        ▼                                          │
   │              gate①（代码，确定性，本稿新增/升级 4 条检查）           │
   │                        │                                          │
   │            ┌───────────┴───────────┐                              │
   │       全过 / NA                 有 BLOCK/FLAG 中命中的子集          │
   │            │                        │                              │
   │            │              reading-agent（Flash 档，纯结构化输入，   │
   │            │               不看图）读 gate① JSON + candidate_ledger,│
   │            │               生成"哪些 candidate_id 需要复核"的       │
   │            │               结构化清单（不含世界坐标/不含 GT）        │
   │            │                        │                              │
   │            │              reading-worker-agent 第二遍（唯一一次，   │
   │            │               只覆盖清单里的候选，不重抽整栋）           │
   │            │                        │                              │
   │            │              gate① 再跑一次 ─────────────┐            │
   │            │                                          │            │
   │            └──────────────────┬───────────────────────┘            │
   │                                ▼                                   │
   │                     merge：选更优/最终一版                          │
   │                     写 reading_mode provenance 块（§2.3 分账，       │
   │                     autonomous 时此块必须全空——代码断言，非约定）    │
   │                                │                                   │
   └────────────────────────────────┴──── (status, output,              │
                                            evidence_manifest) ──────────┘
```

**Core / Recipes / Experimental 工具箱**（Q-F）挂在 reading-worker-agent 与 gate① 两侧：
reading-worker-agent 调用 Core/Recipes 产生候选与标定；gate① 消费候选集合（`cv_evidence/` 侧车）
判定 candidate_ledger 覆盖率。Experimental 只活在单次 run 的 CV Lab（Q-E）里，不进入上图任何一个方框，
除非经 Q-F 的晋升门。

---

## Q-A · 那条「正确路径」到底由哪些动作组成？

### ① 方案

把 07-07（controlled，100 %）与 07-02（tool-invention，100 %）两份达标产物、
与崩掉的几份（07-30 1/8、08-01 A/B 臂、W5 d1/d2）对照，正确路径可以写成**六步工序**，
每步标注「VLM 必须做」还是「应该沉进代码」：

| 步骤 | 内容 | 归属 |
|---|---|---|
| 1. 标定 | 从图上取 2–3 个已知跨距锚点算 px/m，报 RMSE/残差、双轴一致性 | **锚点选取=VLM**（要认出哪段是可信的标注跨距）；**RMSE/一致性计算=代码**（`px_m_calibrator` 已是代码，只是没把 RMSE 接进 gate①） |
| 2. 候选生成 | 跑确定性 CV（`wall_line_profiler`/`window_cc_detector`/prescan）产出候选线段/区域集 | **纯代码**，已存在（`scripts/tool_scripts/cv_probe.py:106-147` 八个子命令） |
| 3. 逐候选核验 | 对每个候选：crop_zoom 放大看、判定是墙/窗/家具/尺寸标注артefact，写 accept/reject+理由 | **VLM 必须做**（语义判别）；但"是否每个候选都被处置了"这件事**可由代码核对**（新字段，见 Q-B） |
| 4. 尺寸链闭合 | segment 之和 == overall，双轴 | **纯代码**，已存在且已是检查（`src/validator/checks/reading.py:693-790 _chain_closure`），只是 disposition 恒为 FLAG（见 Q-B） |
| 5. 跨图互证 | 平面墙链与四立面开洞位置对得上 | **VLM 判别**（跨图语义关联）；**位置数值比对可代码化**（尺寸链跨视图对齐是纯算术，只是目前没做——见 Q-A ⑥ 施工拆批） |
| 6. 诚实登记 | 测不到的字段显式留空/标 `unknown`，不猜 | **VLM 的纪律**；机器只能验证"该留空的确实留空、且没有被下游误判为缺陷"（这正是 P0 断线一命中的坑：`mirrored:"unknown"` 被判卷器当帧向冲突，详 CLAUDE.md 08-02 记录） |

**因此答案**：路径能写成工序（步骤 2/4 已经是代码；步骤 1 的一致性检查、步骤 3 的覆盖率检查、
步骤 5 的跨图算术对齐，是三处「该代码化但还没代码化」的缺口，构成 R3-b/R3-c 与本稿 Q-B 的施工内容）。
**没有哪一步是"必须由更强的模型做判断力才能做"**——07-02 用 Sonnet 现场发明 CV、07-07 用 Haiku +
预制 CV 都做到了 100 %，说明步骤 2/4/5 代码化之后，步骤 1/3/6 对 Haiku 级模型不构成能力壁垒
（Haiku 在 07-07 就是那个执行者）。**真正的失败模式不是"看不懂图"，是"任务分解成了'扫一遍描述'
而不是'枚举候选逐个核验'"**——这是工作流形状问题，不是感知能力问题，与 §1.3 crop_zoom 计数
（好轮 17/16/11 次 vs 崩轮 0 次）完全吻合。

### ② 依据

- `case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/reading_summary.md`
  逐图列出：标定 RMSE（如 1f_view "36.3333 px/m, RMSE 0.33 px"）、
  "52 profiler candidates dispositioned (14 accepted → walls; 38 rejected: furniture / chain
  artifacts / window crossings)"、跨图互证段落（"Cross-image consistency observed"）、
  诚实登记段落（"Repeatedly-null / repeatedly-unknown fields"）——这五个段落**逐字对应上表六步中的
  1/3/5/6**。
- `case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/llm.yaml`：
  "2 rework rounds (discipline 1 + schema 1)"，且 `run_manifest.json` 里
  `0_reading.accepted_attempt = 1`（只有一个 attempt 目录）——**证明那两轮返工发生在同一次会话内、
  merge 之前**，不是"跑了两次、挑一次好的"。reading_summary 表格里 1f_view 一行标注
  "done (pilot, reworked once per review)"——**返工的落点是"平面这一张图不完整"，与问题书 Q-D
  引用的历史记录（"只描了主要墙、违反完整性"）吻合**。
- `src/validator/checks/reading.py:693-790`（`_chain_closure`）、`:829-935`
  （`_stroke_dimension_consistency`）、`:997-1063`（`_partition_on_window_jamb`）——三条检查**已经写好**，
  且 `_partition_on_window_jamb` 的 docstring 与实现精确针对"内墙坐标恰好落在窗垛位置"这个失败模式
  ——**正是 07-30 那次 1/8 的失败形状**（把窗垛当隔墙）。
- `src/validator/checks/schema.py:77-90`（`CheckLayer`）+ `:121-...`（`disposition()`）：
  disposition 是与 `CheckLayer` 独立的策略函数，已经按 `check_id` + `run_profile` 做过差异化
  （`_PLAN_FRAME_BLOCK_PROFILES`、`_EVIDENCE_BLOCK_PROFILES` 两个既有的按 profile 升级 BLOCK 的例子）
  ——**这正是本稿要复用的机制、不是要新发明的机制**。
- §1.3 反例（07-02 全 `seen`、零 `dimension_refs`，仍 9/9）—— 已用于排除"provenance 字段本身"作判据。

### ③ 否决的替代方案

- **"把 provenance 字段（`dimension_derived` 占比）接成 gate① 判据"**——问题书 §1.3 已用 07-07/07-02
  两份反例明确否决（07-07 是 13/14 `dimension_derived` 满分，07-02 是全 `seen` 满分）；
  该字段与成绩不相关，接进去只会在两个方向上都误判。**否决理由 = 已有实证反例，不是猜测**。
- **"把'跑了多少次工具调用'直接当判据"**——§1.3 表面上支持（好轮 17–33 次 vs 崩轮 1–5 次），
  但这是相关性不是机制；若直接拿调用次数做阈值，模型会学会刷调用次数而不改善质量
  （这是本项目"把话说清楚连败三次"同一类"表面纪律可被应付"的风险）。
  **改用"候选覆盖率"（调用是否命中了确定性候选集里的每一条）**，因为这个量**不能被无意义的调用刷出来**
  ——刷调用次数而不覆盖候选集，覆盖率不会涨。
- **"让 reading-agent 亲自判断'描述完整了没有'（即重建 orchestrator 当年的判断力）"**——
  否决理由见 §0.1：orchestrator 当时的判断力可以拆解为可代码化的检查（候选覆盖率、链闭合），
  没必要复刻一个"看图判断完整性"的强模型角色，那样只是把 orchestrator 换皮成 reading-agent，
  没有真正降档，也无法给出「摘掉即红」的锁（一个模型的主观判断力没法写成回归测试）。

### ④ 验收形态

- **新增/升级的 gate① 检查清单**（详细字段设计见 Q-B）：
  1. `reading.dimension_chain_closure`、`reading.stroke_dimension_consistency`、
     `reading.partition_on_window_jamb`：**从"永远 FLAG"升级为"`regression`/`golden` 档下 FAIL→BLOCK"**
     （复用 `schema.py` 既有的按-check_id-按-profile 升级机制，新增两个 check_id 进
     `_EVIDENCE_BLOCK_PROFILES` 同族的常量表）。
     **锁**：构造一份含"墙坐标落在未标注 dimension_derived 的窗垛位置"的夹具，`run_profile=regression`
     下 `checks.blocking()` 必须非空；同一夹具在 `exploratory` 下必须仍是 FLAG（回归 R1-b 修好之前的行为
     不能变成"永远 BLOCK"，否则历史 golden 会被错误地全部拒收）。摘掉升级逻辑 ⇒ 该夹具在 `regression`
     下也不再 blocking ⇒ 锁变红。
  2. `reading.candidate_disposition_coverage`（新检查，见 Q-B①）。
  3. `reading.calibration_consistency`（新检查，把 `px_m_calibrator` 已经算出的 RMSE/双轴偏差百分比
     接进 `checks.json`；目前该数字只活在 `cv_evidence/` 侧车里，没有被 gate① 读过）。
     **锁**：构造 RMSE 超阈值 / 双轴偏差超 0.3% 的侧车夹具，检查必须 FAIL；摘掉该检查函数调用
     ⇒ 同夹具变成检查结果列表里完全不出现该 check_id ⇒ 锁断言"该 check_id 存在且状态为 FAIL"变红。
- **验证方法**：本节的判断（"07-07 与 07-02 走的是同一条工序的两种实现"）本身不能靠推理定论，
  需要**把上表六步逐条在 07-07/07-02/07-30 三份产物上跑一遍新检查**，看 07-07/07-02 全过、07-30 大量
  FAIL——这是 R2 阶段就能做（零生产码改动，纯离线重判），但**新检查（候选覆盖率、标定一致性）本身
  还不存在，属本批 R3 施工内容**，跑之前必须先把检查写出来。**无法在不写代码的前提下验证「新检查
  真的能分开好轮与坏轮」——这需要跑 R3 施工 + 离线重判三份历史产物，我在此明说无法纸面判定。**

### ⑤ 风险与副作用

- **候选生成工具本身召回不足会把"覆盖率 100%"变成假阳性的完成度信号**：如果
  `wall_line_profiler` 只找到 5 条候选而真实有 16 段墙（§1.9 实测数字），"5/5 候选全部处置"
  会显示 100% 覆盖率，但漏掉的 11 段墙完全不在这个信号的视野里。**这是本节机制的天花板，不是
  可以关起来的小问题**——见 Q-B② 的诚实标注与 Q-H 的收口建议（gate②/human 发现的漏检必须反哺
  候选生成工具，而不是止步于"覆盖率检查通过了"）。
- **把链闭合/坐标重合检查升级为 BLOCK，会拒收一部分"正确但图纸本身没有可闭合尺寸链"的合法产物**
  （例如某段内墙确实没有标注、只能靠像素测量）——这也是 07-07 自己的 S14 墙（"NO printed dimension"，
  诚实标 `seen` 空 `dimension_refs`）。**不能无差别 BLOCK "链不闭合"，必须区分"该测的没测"与
  "图纸本身没给尺寸链、诚实测量并如实标注"**——这是 Q-B①③ 里要专门处理的边界，写在检查逻辑里
  （已标注 `seen` + 有 CV 侧车引用的，不算入 BLOCK 条件；只有"既没链引用、也没候选/crop_zoom 证据"
  的才 BLOCK）。
- **不得把非方形/复杂体量的建筑烤死进这套检查**（不变量 #6）：链闭合、候选覆盖率这些检查的实现
  必须对"墙数量""房间数量"零假设，只按"图上出现的候选/尺寸链数量"动态计算分母，不写死 sm24/sm21
  的墙数。本稿设计的两个新检查（候选覆盖率、标定一致性）在实现时**必须对任意候选数量/任意链数量
  通用**，这是施工验收的一部分（同一夹具生成器要能吐出 3 段墙和 30 段墙两种规模都测过）。

### ⑥ 施工拆批与顺序

- **可立刻开工（不依赖本稿其余问题的架构拍板）**：R3-b（既有三检查升级 BLOCK）、
  新增 `calibration_consistency` 检查——都是 `src/validator/checks/reading.py` +
  `schema.py` 里现成机制的扩展，不涉及 ReadingService/reading-agent/CV Lab 的任何新接口。
- **需要先有 Q-B 的字段设计才能开工**：`candidate_disposition_coverage`（依赖新 schema 字段
  `candidate_ledger`，见 Q-B①）。
- **需要 R2 数据支撑才能定阈值**：候选覆盖率的 BLOCK 阈值（100%？95%？）需要在 07-07/07-02/
  几份崩轮上先跑出分布再定，不能纸面拍数字——**这需要跑，我在此明说，不用推测阈值填充**。

---

## Q-B · 「做完了没有」由谁判定？

### ① 方案（拆成 Q-B-1 复合判据 + Q-B-2 盲区收口）

**Q-B-1：复合判据的四个独立信号，全部落在 gate①（代码层），不落在 reading-agent 或 judge**：

1. **候选处置覆盖率**（新）：给 `ReadingView` schema 加一个可选字段 `candidate_ledger: list[dict]`，
   每条 `{candidate_id, source_tool, pixel_anchor, disposition: accepted|rejected|superseded,
   stroke_id: str|null, reason: str}`。`source_tool` 与 `candidate_id` 来自 `cv_evidence/<image>/`
   侧车里已经存在的候选产出（`wall_line_profiler`/`window_cc_detector`/prescan 已经在写这些候选，
   只是没人回填"这条候选最后判给了哪个 stroke、还是被拒了"）。gate① 新检查：
   `候选集里出现过的 candidate_id` 是否**全部**在 `candidate_ledger` 里被处置。
   **这是分母问题的部分答案**：分母 = 确定性 CV 工具**已经找到**的候选数（不是 GT 里的真实墙数，
   不依赖已知答案；也不是自评，是工具产出的、被测者改不了的客观集合）。
   **诚实标注它不是完整分母**（见②风险 + Q-B-2）。
2. **标定一致性**（既有数据，接线缺失）：`px_m_calibrator` 已经算出 RMSE 与双轴偏差
   （见 07-07 reading_summary 逐条 RMSE 数字），只是没进 `checks.json`。接进去后可判"标定是否可信"，
   对应 Q-D 引用的历史干预"标定错锚"。
3. **尺寸链闭合**（既有检查，disposition 待升级，见 Q-A④）。
4. **crop 核验覆盖率**（新）：cross-reference `access_log.jsonl`（考场守卫写的、被测者伪造不了的
   命令原文日志，`isolation.py:820-844 _build_provenance` 已经在解析它算 `access_log_entries`/
   `access_log_denied`，只是没喂给 gate①）里的 `crop_zoom` 调用 bbox，与
   `stroke_dimension_consistency`/`partition_on_window_jamb` 标记为"坐标可疑重合"的那些 stroke
   的像素锚点做重叠判定。**这是把§1.3"好轮 17 次 crop_zoom vs 崩轮 0 次"这个相关性，
   转成一条只对"被标记为可疑的坐标"生效的必要条件**（不要求所有 stroke 都被 crop 过，
   只要求"gate① 自己标记为可疑的那些"必须被 crop 过——这样不会对干净利落一次就画对的 stroke
   提出无意义的要求）。

   **实现前提（需要的代码改动）**：`check_reading_view(rep, view, meta, run_profile)` 的
   `meta` 目前是从产物元数据构造的（`_evidence_meta(meta)` 已在多处使用），需要在 merge 阶段
   （`isolation.py::merge_isolated_output`）把 `access_log.jsonl` 的解析结果一并塞进 `meta`
   传给 gate①——`_build_provenance` 已经做了几乎一样的事（供 provenance 记录用），
   **本质是把同一份已解析数据多喂一份给 gate①，不是重新写解析器**。

**判定放在哪一层**：全部四个信号**放在 gate①**（代码，确定性，不消费 GT，可离线重判）。
**理由**：gate① 是唯一同时满足"可复算""不吃 GT""可回归锁住"三条件的层。
reading-agent 消费 gate① 的输出决定要不要触发一次局部返工（详 Q-D），**但不产生新的判定**——
它只是"gate① 说这几个 candidate_id 没被处置，去把它们处置掉"的执行者，不掌握新的判据。
judge（gate②）**继续只做整轮盲重抽**（§2.5 不变），不参与"完成度"判定——完成度判定必须在
"整轮重抽"这个昂贵动作之前就能给出，否则每次都要烧一次完整识图才知道要不要重抽。

**Q-B-2：盲区收口——这是问题书没问、但答不出会留一个隐藏坑的问题**。
上述四个信号无论怎么组合，都对"确定性工具没找到、模型自己也没描出来"的元素**完全失明**
（§1.9 的 5 候选 vs 16 段墙）。这个盲区**不能靠 gate① 关闭**（gate① 没有 GT，天然看不见"漏了什么"）。
**唯一能关闭它的动作是 gate②/human 发现漏检后，把"这类元素为什么没被候选工具找到"反哺进
Core 工具或新增一条 gate① 检查**——即 Q-F 的晋升机制与 Q-B 共享同一条反馈回路
（"gate② 抓到 gate① 没抓到的" ⇒ 强制生成一条候选晋升/新检查候选，不能只写进报告了事）。
**这条回路本稿定为 SOP 纪律，写进 Q-F 与 Q-H 的验收里，但不属于本批施工范围**（本批不新增
候选生成工具，只接线既有信号）。

### ② 依据

- §1.6：`self_check.all_visible_strokes_captured` 等字段"全仓生产代码零消费者"、
  且"d2 四字段全 true 仍 24.8%"——两条证据分别否决"自评当唯一信号"与"自评当阻断项"。
  **本方案不使用自评字段作为判据组成部分**（既不接线也不阻断），仅在 evidence_manifest 里如实
  透传（供人看，不参与 gate① 判定），避免重蹈"把 self_check 变阻断项只会教会模型学 d2"的覆辙。
- §1.9：预扫 5 条 vs 答案 16 段——本方案**不**把预扫候选数当"完成度分母的全部"，
  只当"候选覆盖率"这一个子信号的分母，并在④⑤明确标注局限。
- `src/agent/execution/isolation.py:820-844`（`_build_provenance`）：access_log 解析代码已存在，
  只是消费者只有 provenance 记录、没有 gate①，本方案是"多接一根线"而非新写解析器。
- `src/validator/checks/reading.py:829-861`（`_stroke_dimension_consistency` 的
  provenance-coverage 判定）证明"结构化 stroke provenance 覆盖率"这类聚合式检查已经是这个文件的
  惯用写法，新增 `candidate_disposition_coverage`/`calibration_consistency` 是同构扩展。

### ③ 否决的替代方案

- **"用预扫候选数当完成度分母"**——问题书明确否决（§1.9，5 条不够当 16 段的分母），
  本方案只把候选数当"候选覆盖率"这一个**子**信号的分母，不当总分母，**分母缺口诚实标注为
  Q-B-2 盲区，不假装它是完整的**。
- **"把 self_check 结构化字段变成阻断项"**——§1.6 冷水已否决（会教会模型从 d1 学成 d2：
  诚实的不完成变成自信的做错）。
- **"引入第二个更强模型给第一次读图打分（judge-in-the-loop 当完成度判据）"**——
  否决理由：这实际上是把 orchestrator 的判断力换皮成了另一个模型，既不满足"gate① 可复算"
  （模型判分不可精确复算），也和 §2.5"judge 只能整轮盲重抽"冲突（这里的用法是"局部打分续作"，
  粒度即违规，与 07-31/08-01 教训同型）。
- **"完成度判定放进 reading-agent 自己判断（reading-agent 看了图之后自己说'我觉得够了'）"**——
  否决理由：这就是重新引入一个"自评"，量级从 reading-worker-agent 的自评换成了
  reading-agent 的自评，本质没变，§1.6 的冷水同样适用；而且违反 §2.2③"reading-agent 不得直接写
  最终坐标"隐含的精神（如果它能一票否决/通过整个产物，等于拥有了事实上的裁决权）。

### ④ 验收形态

- 上述四个信号各自的锁见 Q-A④（链闭合/坐标重合升级）与本节新增两个检查的锁：
  - `reading.candidate_disposition_coverage`：**锁 = 构造一份 `cv_evidence` 侧车含 5 个候选、
    `candidate_ledger` 只处置 3 个的夹具，检查必须 FAIL 且 evidence 里列出未处置的 2 个 candidate_id**；
    正例（5/5 全处置，含 reject 的）必须 PASS。摘掉检查函数调用 ⇒ 两个夹具都不再产生该 check_id
    ⇒ 断言"check_id 存在"的锁变红。
  - `reading.calibration_consistency`：见 Q-A④ 同名检查。
  - `reading.crop_verification_coverage`：**锁 = 构造一份 `stroke_dimension_consistency` 会标记为
    可疑的坐标、且 `access_log.jsonl` 里没有覆盖该坐标的 crop_zoom 记录的夹具，检查必须 FAIL**；
    另构造有覆盖的夹具必须 PASS。摘掉 access_log 传参这一步（让 `meta` 里没有该字段）
    ⇒ 检查必须能区分"没有 access_log 数据"（NOT_APPLICABLE，legacy 产物没有这份日志）与
    "有 access_log 但未覆盖"（FAIL）——**这个区分本身要有单独的锁**，否则会把所有老产物错误 FAIL。
- **evidence_manifest 里必须如实注明"候选覆盖率不是漏检率、只是'找到的候选都被看过了没有'"**
  ——这条注明本身要有测试：`evidence_manifest` 的 schema 里 `candidate_coverage` 字段旁必须带一个
  `denominator_source: "cv_toolbox_detected_candidates"` 说明字段，防止将来有人把这个数字误读成
  "完成度百分比"。**锁**：schema 校验测试断言该字段存在且值域固定为已知来源枚举，不能是自由文本。

### ⑤ 风险与副作用

- 与 Q-A⑤ 相同的候选召回天花板——不重复展开，见 Q-B-2 的回路设计。
- **crop_verification_coverage 依赖 access_log 的可用性**：如果换成非 Claude Code 会话的
  reading-worker-agent（例如问题书 §0.3 提到"降档动因=转本地开源 VLM"），需要确认该执行环境
  是否也能产出等价的、不可伪造的工具调用日志。**这一点本稿判不了**——需要在真正切换到本地部署
  VLM 时验证该环境的工具调用能否同样被非侵入式记录；如果做不到，这条信号会在那个环境下整体退化为
  NOT_APPLICABLE，届时完成度判据只剩三个信号，判据强度会下降，这是需要提前登记的技术债。
- **四个信号的组合逻辑（"任一 FAIL 则 BLOCK" vs "加权"）本稿倾向前者**（任一 FAIL under
  `regression`/`golden` 即 BLOCK，因为每个信号已经是"最低限度的自洽性检查"而非"质量评分"，
  达不到这个最低限度就不该通过）。**加权方案被否决**：加权需要给每个信号定权重，
  权重本身就是又一个"拍脑袋定数字"，且历史上"固定容差窗"（R3 时期判卷器"零容差 vs 1e-9"
  来回摆动）已经证明这类数值调参会反复被下一轮反例打脸——**布尔 AND 组合更保守，也更容易被
  单独一条锁验证，符合"放水比冤枉危险"的口径**。

### ⑥ 施工拆批与顺序

- 与 Q-A⑥ 相同批次（同一个文件 `reading.py`/`schema.py`，建议合并成一次施工提交，
  因为四个信号共享同一套"读 `meta`/`cv_evidence`/`access_log`"的接线改动）。
- **`candidate_ledger` schema 字段**需要先过 `src/agent/reading/schema.py` 的字段设计
  （新增可选字段，向后兼容，legacy 产物没有该字段时对应检查一律 NOT_APPLICABLE）——
  这一步理论上不需要等本稿其余部分拍板，**可以立刻开工**，但**必须先由施工方或主控写清楚
  `candidate_ledger` 与现有 `cv_evidence/` 侧车候选 ID 的对应关系**（目前候选 ID 的生成规则在
  `cv_probe.py` 的各子命令输出里，需要核实其是否已经稳定可引用——这一点我没有逐行核对
  `cv_probe.py` 候选 ID 的生成代码，**需要施工前先读一遍确认**，不确定的地方不应该拍死接口形状）。

---

## Q-C · `reading` 环节的边界与接口应该是什么形态？

### ① 方案

```python
class ReadingService:
    def run(
        self,
        case_bundle: FrozenCaseBundle,
        reading_profile: ReadingProfile,
    ) -> ReadingResult:
        ...
```

**`FrozenCaseBundle`**（orchestrator 在 spawn 之前一次性构建，构建后不可变、随 run 落盘并哈希锁定；
这不是新发明，是把已经存在的 `_run/reading_exam_scope.json`/`view_manifest.json`/
`isolation.py::build_isolation_workspace` 的"冻结件"机制正式提升为该函数的显式入参类型）：
- `case_images`：本轮考哪几张图（沿用 08-01 W4 已落地的 `reading_exam_scope` 机制）；
- `testdata`：worked example（`smalloffice_20/0_reading/1f_view.json` 现状不变）；
- `skill_bundle_hash`：`skills/intake_pipeline/0_reading/` 内容哈希（沿用现有 `llm.yaml` 记录习惯，
  提升为结构化字段而非注释里的文本）；
- `toolbox_version`：Core/Recipes 版本号（Q-F 三层注册表落地后，这里钉死一个具体版本，
  不许 run 中途更新）；
- `capability_profile` / `run_profile`：沿用现状（`orthogonal_polygon`/`regression` 等）。

**`ReadingProfile`**（orchestrator 决定"这轮考试怎么考"，但不决定"考试内容"——内容在
`FrozenCaseBundle` 里，profile 只管流程参数）：
- `reading_mode: Literal["autonomous", "controlled"]`；
- `worker_model_id`（reading-worker-agent 模型，如 `claude-haiku-4-5-20251001`）；
- `reading_agent_model_id: str | None`（controlled 时必填，Q-D 定档 Flash 级；autonomous 时必须为
  `None`——这是接口层面的强制，不是约定）；
- `rework_budget: int`（当前唯一合法值 = 1，§2.2③ 硬约束，接口上直接用 `Literal[0, 1]` 而非
  `int`，防止未来有人悄悄放宽）；
- `isolation_mode`：沿用现有隔离 or CV Lab（Q-E 落地前默认现有硬隔离，落地后可选）。

**`ReadingResult`**：
- `status: Literal["complete", "partial", "blocked_gate1", "error"]`——**离散状态，不给置信度分数**
  （置信度分数会诱使下游把它当质量分用，重蹈 provenance 字段被误用的覆辙）；
- `output`：五份 `ReadingView` JSON（schema 不变，仅新增 Q-A/Q-B 提到的可选字段）；
- `evidence_manifest`：见下。

**`evidence_manifest` 内容**（回答问题书"外部在不看图前提下能不能判断这次 reading 可不可信"）：

```jsonc
{
  "reading_mode_provenance": {          // Q-D §2.3 分账块，见 Q-D④
    "lane": "controlled",
    "worker_model_id": "...",
    "reading_agent_model_id": "...",    // autonomous 时必须为 null，代码断言
    "reading_agent_saw_image": false,   // 架构性保证，见 Q-D
    "rework_rounds": 1,
    "rework_trigger_check_ids": ["reading.candidate_disposition_coverage"]
  },
  "gate1_summary": {                    // 每张图、每条 check_id 的 status/disposition 汇总
    "1f_view": {"blocking": [], "flagged": ["reading.stroke_dimension_consistency"]},
    ...
  },
  "candidate_coverage": {               // Q-B①，附 denominator_source 防误读
    "1f_view": {"covered": 14, "total": 14, "denominator_source": "cv_toolbox_detected_candidates"}
  },
  "access_log_digest": {                // 不暴露完整日志（避免体积失控），给可复核摘要
    "sha256": "...", "denied_count": 0, "allowed_tool_histogram": {"crop_zoom": 17, ...}
  },
  "toolbox_version": "core@2026-08-xx"
}
```

**能不能判断可信**：**能给出强的自洽性信号（这次 reading 内部有没有说谎/漏做该做的核验），
不能给出几何正确性信号**——后者只有 gate②/人对着 GT 才能判。本稿明确这条边界，
不允许把 `evidence_manifest` 包装成"reading 是否正确"的替代品。

### ② 依据

- 现状 `_run/reading_exam_scope.json` + `view_manifest.json`（W4，CLAUDE.md 08-01 记录）已经是
  "冻结的 case bundle" 的雏形，本方案是把它从"reading stage 专用的临时机制"提升为
  `ReadingService` 的正式入参类型，架构上是收拢现有分散字段，不是从零发明。
- `isolation.py:273-...`（`merge_isolated_output`）已经在做"收 worker 产出 → gate① → 决定
  accepted_attempt"这套逻辑，`ReadingService.run` 的内部实现基本是把这段代码套一层类型化的
  函数签名，**不是重写**。
- 问题书 §2.1"只能启动与接收"——`ReadingResult` 三元组精确对应这句话字面意思。

### ③ 否决的替代方案

- **"orchestrator 能看流式进度/中间产物用于调试"**——否决。这正是造成 07-31/08-01/07-07 三次
  污染的确切通道（orchestrator 在中途看到东西、忍不住评论）。**dev 期调试需求用"事后读已落盘的
  run 目录"满足**（`0_reading/attempts/NNN/` 已经全部落盘，orchestrator 随时能在 run 结束后翻，
  不需要一个新的实时通道）。这不是削弱可调试性，是把"看"和"看的时机"分开——只能在
  `ReadingService.run` 返回之后看，不能在它运行中看。
- **`ReadingResult.status` 用浮点置信度分数代替离散枚举**——否决理由见①，会被下游拿来做质量代理，
  重演 provenance 字段的教训。
- **把 `evidence_manifest` 做成可以直接喂进 gate②/judge 的"预判分"**——否决。
  §2.5 judge 必须整轮盲重抽零信息；如果 evidence_manifest 被 judge 读取用于调整判定，
  等于给了 judge 关于生产过程的信息，混淆"judge 是不知情的第三方裁判"这条边界。
  `evidence_manifest` 只面向**人**（report_assembly 展示）与**报告分账逻辑**（区分 lane），
  不作为 judge 的输入。

### ④ 验收形态

- **锁 1**：`test_reading_service_autonomous_forbids_reading_agent_model_id` ——
  构造 `ReadingProfile(reading_mode="autonomous", reading_agent_model_id="glm-4.5-air")`，
  必须在构造期（Pydantic/dataclass 校验）直接拒绝，不能跑到运行时才发现。
- **锁 2**：`test_evidence_manifest_generated_without_gt_access` —— 在测试里 monkeypatch
  `src/agent/judge/gt.py:load_gt` 使其一调用就 raise，跑一次 `ReadingService.run`，
  断言 `evidence_manifest` 仍完整生成且不为空。**这条锁把"设计工作可以读 gt，产品本身不能读 gt"
  这条 GT 铁律，落到 `ReadingService` 这个具体入口上**，防止将来有人图省事在
  evidence_manifest 生成逻辑里顺手引用 gt。
- **锁 3**：`test_orchestrator_cannot_observe_mid_run_state` —— 这条更多是流程约束，机械验证形态
  = 断言 `ReadingService.run` 的返回类型签名里不存在任何"中途回调/生成器/streaming"接口
  （即接口签名本身是 `-> ReadingResult` 而非 `-> Iterator[...]`），属于**接口形状锁**而非行为锁，
  但仍应写成测试（用 `inspect.signature` 断言返回类型注解），防止未来改动悄悄加一个回调参数。

### ⑤ 风险与副作用

- **`evidence_manifest` 体积/生成开销**：候选覆盖率、access_log 摘要都需要额外计算，
  如果实现得不小心（比如把完整 access_log 塞进 manifest 而非只放摘要），会显著增大产物体积、
  拖慢 dev 期迭代速度。**方案里已明确"给摘要不给全量"**，但这是施工阶段需要盯住的实现细节。
- **接口稳定性 vs 迭代速度的张力**：`ReadingProfile`/`FrozenCaseBundle` 一旦定型，
  后续给 reading-agent 加新字段（比如 Q-D 的 rework 触发清单）都要改这个公共接口，
  有一定的耦合成本。**接受这个成本**——好处是接口稳定给了"能不能安全撤掉 reading-agent"
  一个明确的检验点（改一个字段就能测试两种模式），详 Q-D⑥。

### ⑥ 施工拆批与顺序

- **需要等本稿其余部分（尤其 Q-D）拍板才能定型**——`ReadingProfile`/`ReadingResult` 的字段形状
  直接依赖 Q-D 的 reading-agent 设计（rework 触发清单的具体结构）。**这是问题书自己划的"R4-c 走
  正规程序"边界**，本节不建议提前开工，只建议先把 `FrozenCaseBundle`（现有冻结机制的类型化收拢，
  不涉及 reading-agent）作为独立的、可以先做的子任务。

---

## Q-D · `reading-agent`：怎么把当时那个临场介入正确地固化下来？

### ① 方案

**核心设计决定：reading-agent 不看图。** 它的全部输入是**结构化文本**——
gate① 的 `checks.json`（本稿 Q-A/Q-B 新增字段后）+ `candidate_ledger` + 已生成的 `ReadingView`
JSON 本身（不含图片字节）。它的输出是**一份结构化的"待复核候选清单"**（`candidate_id` 列表 +
触发它的 check_id），交给 reading-worker-agent 做**唯一一次**局部返工。

这个设计直接回答"07-07 那次干预具体做了哪几个动作"（问题书 Q-D 第一问）——按可考据的记录，
两次干预内容分别是**"只描了主要墙、违反完整性"**与更早一次**"标定错锚 / 候选未逐条核验 / 字段全空"**
（问题书原文引用；本稿在 §0.1/Q-A①核实：`reading_summary.md` 里 1f_view 一行标"reworked once
per review"，`llm.yaml` 记"2 rework rounds (discipline 1 + schema 1)"，与该引用吻合但**完整
prompt 原文已丢失、无法逐字核对**——这一点问题书 §1.9 已如实标注为缺口，本稿不假装能补上）。
这四条干预内容逐条映射：

| orchestrator 当时说的 | 对应哪个可代码化信号 |
|---|---|
| "只描了主要墙、违反完整性" | `candidate_disposition_coverage` 未达标（Q-B①） |
| "标定错锚" | `calibration_consistency` FAIL（Q-B①/Q-A④） |
| "候选未逐条核验" | `candidate_disposition_coverage`（同上，两条历史干预其实是同一个信号的两次触发） |
| "字段全空" | `self_check`/`candidate_ledger` 空值检测（Q-B①，注意本稿**不**把自评本身当阻断，
  但"candidate_ledger 完全为空"这种结构性缺失可以是一条独立的"该字段存在但空"检查，
  这不等于依赖自评内容的真假，只是检查该产的字段有没有产） |

**由此，reading-agent 的完整职责边界**：
1. 读取 reading-worker-agent 第一遍产出 + gate① 报告；
2. 若无 BLOCK/FLAG 命中上表信号 ⇒ 直接交给 merge（**没有触发就没有返工**，
   这是"有界"的第一层——不是"reading-agent 决定要不要挑刺"，是"gate① 的既有信号决定"）；
3. 若有 ⇒ **把 gate① evidence 里已经列出的 `candidate_id`/`stroke_id` 原样摘出**，
   拼成一份"请复核以下候选：C7, C12, C19（原因：未处置）；请重新核对标定（原因：RMSE 超阈值）"
   这样的结构化清单——**清单内容 100% 来自 gate① 已经计算出的 evidence 字段，reading-agent
   不添加任何自己"看出来"的新判断**；
4. 交给 reading-worker-agent 做**一次**局部返工（只覆盖清单里的候选/标定，不许重新通读整张图、
   不许改动清单外的 stroke——这个约束需要在 kickoff 里写清楚且由 gate① 事后核验"改动范围"，
   见④）；
5. 重跑 gate①；
6. merge：如果返工版本让触发的检查转 PASS/FLAG 且没有引入新的 BLOCK，采用返工版本；
   否则保留第一遍（**reading-agent 不能让产物变得更差却仍然被采用**——这条需要 merge 逻辑里
   显式比较两版的 blocking 集合，不能简单"总是要最后一版"）。

**§2.2 四条约束核对**：
- **档位不高（Flash 级/thinking off/结构化输出/短上下文）**：因为 reading-agent 不看图、
  只处理结构化 JSON + 短清单，Flash 级模型完全够用，**这不是权衡后勉强够用，是设计上根本不需要
  更强的模型**——它做的事是"把 evidence 字段里已有的 ID 抄进一份清单"，属于结构化信息搬运，
  不是语义判断。
- **一次计划 + 一次局部返工，不重抽整栋**：设计里 rework_budget 硬编码为 `Literal[0, 1]`
  （Q-C②），"局部"由清单范围强制（只覆盖清单里的 candidate_id）。
- **不得直接写最终坐标**：reading-agent 的输出 schema 里**没有坐标字段**——它只产出
  `candidate_id`/`check_id` 的引用列表，坐标只能来自 reading-worker-agent 第二遍的输出。
  这是接口层面的强制，不是纪律要求。
- **与 orchestrator 彻底解耦**：reading-agent 是 `ReadingService` 内部对象，orchestrator 不持有
  对它的引用，只在 `ReadingResult.evidence_manifest.reading_mode_provenance` 里事后读到它存在过。

**够不够复现当时的效果？** ——**这一点本稿判不了，明说无法纸面判定**。
上表把已知的、可考据的干预内容映射成了信号，但**"完整 prompt 原文已丢失"这个缺口意味着
不能排除 07-07 当时还有其他未被记录下来的干预内容**（问题书自己在 §1.9 标注了这个缺口）。
**要判定"够不够"，需要跑 R6 的 C/D 两臂**（问题书 Q-G 已经设计了这个实验，本稿 Q-G 会给出
更省成本的跑法建议）——这不是本稿能替代的。

**dev 期开发者角色（§2.3）归属与结构性隔离**：本稿同意用户"倾向 orchestrator 兼任"，
理由是 orchestrator 已经是唯一有全仓访问权限、且负责构建 `FrozenCaseBundle` 的角色，
新增第三个角色反而多一层隔离要维护而无额外收益。**但必须补一条结构性保证**（问题书没问、
但不补会让"验收脱离该角色完成"变成一句空话）：**dev-role 观察必须发生在一个不产出被接受结果的
会话里**。具体做法——dev-role 允许对某次 `ReadingService.run` 的**已落盘**产物
（`attempts/NNN/`、`access_log.jsonl`、gate① 报告）做事后分析，并把结论写成对
skill 文本/`cv_probe` 工具/Recipes 的**文件级修改**（走 Q-F 的晋升门）；
**它不允许在一次仍在进行的 `ReadingService.run` 内部注入任何内容**——因为
`ReadingService.run` 根本没有对外暴露任何"运行中可写入"的接口（Q-C③ 已否决 streaming/回调接口）。
**07-07 那次之所以不能算干净基线，正是因为它违反了这条**（orchestrator 在同一个会话、
产物合并之前介入）——本稿的设计让这类介入在架构上不可能发生：下一次想要"dev-role 观察 + 调整"，
必须是"跑一次 → 读产物 → 改文件 → 跑下一次"，物理上分成两次 `ReadingService.run` 调用，
第二次调用不可能知道第一次调用"运行中"发生了什么，因为第一次调用运行时压根没有暴露的信息通道。

### ② 依据

见①内嵌的表格与考据；另：
- `src/agent/execution/isolation.py` 全文没有任何"reading-agent"或"controller"类型的对象，
  确认这是全新组件，不是重命名已有代码。
- `case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/attempts/001/`
  只有一个 attempt 目录（Bash 核实），证明"返工"不是"第二次尝试"而是"同一次会话内的中途调整"，
  这个结构直接支持"reading-agent 在 merge 之前做局部返工"这个设计形状（而不是"reject 整个
  attempt、重开一个新 attempt"）。

### ③ 否决的替代方案

- **"reading-agent 也看图，用一个中等强度的多模态模型做二次核验"**——否决。
  §2.2②"档位不高"允许 Flash 级，但如果给它配图像输入，Flash 级多模态的实际表现未经验证，
  且**一旦看图，"不得直接写最终坐标"这条约束的执行力会下降**（看了图容易忍不住给具体建议，
  这正是 orchestrator 违规的病根——"看了图之后指导 worker"，问题书 §2.1 明令禁止，
  虽然那条是对 orchestrator 定的，但同样的心理/设计陷阱对 reading-agent 一样成立）。
  **让 reading-agent 结构性地看不到图，比"要求它看了图也不说具体建议"更可靠**——
  后者是纪律，前者是架构，本项目"文档不能验证别人是否遵守自己"（§1.7）这条教训明确指向
  架构优于纪律。
- **"reading-agent 用 LLM 自由文本生成返工指令（类似 07-07 的自然语言打回）"**——否决。
  自由文本指令**无法审计是否越过了"只给候选 ID、不给语义判断"这条线**（打回内容里可能夹带
  "我觉得这里应该是墙"这种实质性判断，等于绕过了"不写最终坐标"的精神）。
  改用**结构化输出**（candidate_id 列表 + check_id，不允许自由文本字段，或自由文本字段仅限于
  原样复制 gate① evidence 里已有的字符串）——这也是§2.2②"结构化输出"的字面要求。
- **"reading-agent 决定要不要触发返工（自己判断值不值得）"**——否决。改为"gate① 的信号命中即触发"，
  理由见 Q-B 反对"完成度判定放进 reading-agent"的同一条：会重新引入一个不可复算的判断主体。

### ④ 验收形态

- **锁 1（分账不被稀释）**：`test_report_assembly_refuses_autonomous_with_nonnull_agent` ——
  构造一个 `reading_mode_provenance.lane == "autonomous"` 但
  `reading_agent_model_id != None` 的 evidence_manifest，喂给 report 组装逻辑，
  **必须 raise，不能静默生成报告**。这是 Q-D①"怎么保证分账不被稀释"的机械答案：
  不是靠人工检查报告有没有写错，是靠代码拒绝生成一份自相矛盾的报告。
- **锁 2（reading-agent 不写坐标）**：`test_reading_agent_output_schema_has_no_coordinate_fields` ——
  对 reading-agent 输出的 Pydantic/dataclass 做静态字段扫描，断言字段集合是
  `{candidate_id, check_id, reason}` 的子集，**不包含**任何浮点坐标/`x`/`y`/`px`/`m` 命名模式的字段
  （用命名规则做粗粒度扫描；这不是完美的语义保证，但能挡住最直接的违规写法）。
- **锁 3（reading-agent 不看图，架构保证）**：`test_reading_agent_context_excludes_image_bytes` ——
  构造调用，断言传给 reading-agent 底层模型调用的 payload 里不含任何 base64/图片 MIME 类型内容，
  **只允许纯文本/JSON**。摘掉这个检查 ⇒ 假如未来有人手滑把图片加进 reading-agent 的 context，
  这条锁必须能抓到。
- **锁 4（有界：一次返工上限）**：`test_reading_agent_rework_budget_enforced` ——
  构造 gate① 报告使得返工后仍然 FAIL（模拟"改了还是不达标"），断言 `ReadingService.run`
  **不会**触发第二次局部返工，直接以返工后的最优版本 merge、`status` 视 blocking 情况定为
  `partial`/`blocked_gate1`，**不会无限重试**。
- **锁 5（与 orchestrator 解耦，接口锁）**：Q-C④锁 3 的同类断言，确认 `ReadingService.run`
  没有暴露任何中途回调，orchestrator 拿不到 reading-agent 存在时的任何中间状态。
- **能否复现 07-07 效果**：**验收形态 = R6 的 C 臂（Haiku + Flash reading-agent）在 sm24/sm21
  两个 case、两抽，达到问题书 §4 的量化线（内墙 ≥95%/外轮廓 100%/多画 <3m/窗全项命中）**。
  这是行为验收，不是纸面验收——上面五条锁只能证明"reading-agent 遵守了它被赋予的边界"，
  不能证明"这个边界内的能力够不够"，那是 R6 要跑出来的经验事实。

### ⑤ 风险与副作用

- **"reading-agent 不看图"这个设计选择本身有一个未经验证的假设**：假设"把 orchestrator 当时的
  判断力拆解成结构化信号"这件事**完全**做得到，即 orchestrator 当年看图之后的判断里
  **没有任何**成分是"纯看图才能看出来、无法用候选覆盖率/链闭合/坐标重合这类结构化信号代理"的。
  这个假设**目前只有部分证据支持**（表格里四条历史干预内容全部能映射），**但因为完整 prompt
  丢失，不能排除还有第五条、第六条干预内容映射不上**。如果 R6 的 C 臂没有达标，
  第一个要检查的假设就是这一条——即"reading-agent 需要看图"可能是唯一的补救方向，
  但那会突破§2.2②的档位约束（多模态 Flash 级的实际能力未知），**这需要另一轮设计讨论，
  不在本批范围内预先设计**。
- **候选清单的粒度可能过细或过粗**：如果 gate① 报告的 evidence 里 candidate_id 粒度太细
  （比如把一整面墙拆成多个像素段），返工清单会变得难以执行；如果太粗（一次性打回整张图的所有候选），
  就退化成了"重抽整栋"，违反有界约束。**这需要在实现 Q-A/Q-B 的检查函数时就设计好 evidence 里
  candidate_id 的粒度**——本稿建议以 07-07 reading_summary 里"52 candidates"这种粒度
  （每条独立候选线段/区域一个 ID）为参照，但**具体粒度设计属于 R3 施工细节，不在本稿拍死**。
- **返工可能"改坏"没被清单点名的部分**（reading-worker-agent 二次作答时手滑改了清单外的内容）——
  ④锁清单里没有专门覆盖这一条，**这是本稿的一个已知缺口，建议补一条锁**：
  `test_rework_does_not_touch_strokes_outside_worklist`（比较返工前后，清单外的 stroke
  内容必须逐字节不变），列入 R4-c 施工的验收清单。

### ⑥ 施工拆批与顺序

- **本条整体属问题书划定的"走正规程序"范围**，不可在本稿之后直接施工，需先过交叉对抗审 +
  用户当面拍板。
- 拍板后建议顺序：先落 `ReadingProfile`/`ReadingResult` 接口骨架（Q-C，含
  autonomous/controlled 两分支但 controlled 分支先空转，reading-agent 用一个 stub 代替）
  → 再落 gate① 四个新信号（Q-A/Q-B，这部分可与接口骨架并行）→ 再实现 reading-agent 真实逻辑
  （消费 gate① 报告、生成清单、触发一次局部返工）→ 五条锁全部落地后才能进入 R6 实验。

---

## Q-E · 隔离边界怎么划？

### ① 方案

**信息边界（"哪些路径/哪些内容/网络怎么办"的可执行定义）**：

- **允许读**：本次 run 的 `case_data/`（图像）、`testdata`（worked example）、
  `skills/intake_pipeline/0_reading/`（skill 文本）、`cv_probe` 工具源码本身、
  本次 run 自己的 scratch/输出目录。**用绝对路径前缀白名单判定**（沿用现有
  `_assert_rel_allowed`/`_is_run_prescan_path` 一类的路径判定逻辑，`isolation.py:773-787`），
  **不检查文件内容**。
- **禁止读**：gt / baseline / judge score / review verdict / 其他 run 的目录 / 历史 attempts /
  本仓库源码（`src/`、`AI_agent/`）——**同样用路径前缀黑名单判定**，这部分现状已经是路径判定
  （`HARD_BLOCK_FILENAMES`/`HARD_BLOCK_PARTS`，`isolation.py:53-60`；`guard.py` 里对
  `_repo_root()` 整体 deny），**保留不变**。
- **网络**：默认拒绝一切出站，只放行模型自身 API 端点（这是基础设施层面的出站控制，
  不是命令文本匹配）。**这是本方案与现状差异最大的一条**——现状 `isolation_settings.json`
  （`isolation.py:702-748`）用 Claude Code 自带的 `WebFetch`/`WebSearch` 工具级 deny，
  **但没有约束 Bash 里跑一个裸 socket/`curl`/`requests` 的出站**（一旦放开 Bash 的通用命令能力，
  这个洞就会打开）。CV Lab 方案下 Bash 权限扩大，**网络层面的出站阻断必须补成基础设施级**
  （容器网络策略/无出网网关白名单，不是 hook 里判断命令文本里有没有 `curl` 字样——
  后者正是 §1.8 那种会被同义词绕过、也会误伤合法词汇的机制）。
- **写**：本次 run 的 scratch/输出目录之外一律拒绝，**同样按路径前缀判断**（现状
  `_writable_root` 一类逻辑已经这样做，`guard.py:590-661`，**保留**）。
- **方法**：**不限制**。Bash 命令允许任意形式（含 `python -c`、管道、heredoc、临时脚本）——
  **删除 `guard.py:713-719/734` 的"`python -c` is forbidden"专项禁令**，
  以及 `guard.py:590-707` 那套"逐命令名核对允许表"的机制，改为**只做路径级读写判定 + 网络出站
  基础设施阻断 + 资源上限**，不再判断"命令长什么样"。

**资源边界**：CPU/RAM/墙钟/输出大小用**进程级资源限制**（`ulimit`/cgroup/subprocess timeout +
`RLIMIT_AS` 等），**不是 hook 层扫命令文本判断"这个命令看起来会不会很重"**。
具体数值：以 07-02 现场发明 CV 的实测（单张图最长 30 分钟、112 次工具调用）为参照，
给足量余裕（例如单次工具调用 5 分钟墙钟上限、单张图总墙钟 60 分钟上限、进程内存上限按
容器可用内存的合理比例），**具体数字属实现细节、需要在施工时结合容器实际资源做一次实测校准，
本稿不拍死**。

**可验证性/可审计性（"信息流隔离之后怎么保证仍可验证"）**：**保留 `access_log.jsonl`
（`isolation.py:820-844`）不变**——这是本方案里做得对、要继续做的部分：每次工具调用的
原始命令文本、解析后路径、allow/deny 决定，全部落盘、进 provenance 哈希、被测者改不了。
**新增**：对 Bash 里的 heredoc/`python -c` payload，除了记录命令行本身，**额外记录 payload 的
内容哈希**（不是内容本身，只是哈希——这样 dev-role 事后审计"它写了什么算法"时，
如果需要看内容可以配合当时的临时文件一起看，但 access_log 本身不因为存长文本而膨胀）。

### ② 依据

- `src/agent/execution/isolation_templates/guard.py:713-719`
  （`"python -c is forbidden"`）+ `:590-707`（逐命令名允许表）——现状实现，
  确认"按命令形态封杀"是真实存在的机制，不是问题书的夸大描述。
- 问题书 §1.8：08-02 全卷那轮 7 次 denied，含"用 python 检查自己产物的 JSON"与
  `grep`/`find` 组合——这些都是**读自己产物**（合法输入范围内）的正当操作，
  被按命令形态误伤，直接支持"改判据不改边界"的方案方向。
- `isolation.py:702-748`（`_write_settings`）：现有 `deny` 列表已经包含
  `WebFetch`/`WebSearch`/`mcp__*` 这类工具级网络能力封锁，说明"网络层面单独管控"这个思路
  在本项目里已有先例（只是没有覆盖 Bash 内的裸网络调用），本方案是把这个思路**补全**，
  不是新发明。

### ③ 否决的替代方案

- **"保留命令形态黑名单，但把误杀的词加进白名单"（如给 `grade line` 开特例）**——
  否决。这是 whack-a-mole：下一次换个领域词汇又会撞上（本项目历史上已经因为"约等号"符号
  被拒三次、`grade line` 被误伤，见 CLAUDE.md 07-30 记录），**治标不治本**，
  且黑名单越加越长，最终会退化成"猜执行者接下来会打什么字"的军备竞赛。
- **"完全放开网络，事后审计 access_log 里有没有可疑外传"**——否决。
  GT/答案一旦通过网络泄露就不可逆（哪怕只泄露一次），"事后审计"发现的时候已经晚了。
  出站阻断是便宜的保险，且不影响"任意计算方法"这条自由——CV 计算本身不需要网络。
- **"不设资源上限，相信模型不会失控"**——否决。资源失控是运维/成本风险，
  与"是否信任模型的计算方法"是两件事；07-02 最重的一次单图 30 分钟/112 次调用
  可以作为参照给足余裕（不是卡死在这个数字，是以它为下限校准上限），
  上限设置成本很低，不应该省略。

### ④ 验收形态

- **锁 1（不是内容过滤，是基础设施阻断）**：`test_cv_lab_network_denied_regardless_of_spelling` ——
  构造两个字面不同、语义相同的出站尝试（例如目标域名拼写不同的两次 `requests.get`），
  **两次都必须被拦**，且拦截发生在网络层（连接被拒绝/超时），而不是在 hook 解析命令文本时
  就报错——用这个来证明拦截不是靠"认出了某个关键词"。
- **锁 2（07-02 路径的回归验证）**：`test_cv_lab_allows_arbitrary_python_c_pure_computation` ——
  构造一段纯本地 numpy/PIL 计算的 `python -c` 调用（不读写允许范围外的路径、不联网），
  **必须被允许**。这条锁同时验证"删掉 CV Lab、退回旧隔离机制"会让它从允许变成拒绝
  （即拿这条锁去跑旧的 `guard.py` 逻辑，必须失败，证明新旧机制确有实质差异，不是重新贴标签）。
- **锁 3（资源上限真实生效）**：`test_cv_lab_resource_cap_enforced` —— 构造一个会长时间空转/
  大量占内存的脚本，断言进程在上限内被终止，且 `access_log.jsonl` 里有一条明确的
  `resource_killed`/超时记录（不能是静默截断，执行者需要能看到"是被资源上限杀掉的"而不是
  以为自己的脚本莫名其妙没输出）。
- **锁 4（路径边界不变）**：现状 `test_isolation.py` 里已有的 GT/baseline/其他 run 拒绝测试
  **必须保留且继续通过**——CV Lab 只放开"方法"，不放开"信息边界"，这条是回归锁，
  确认改造没有连带放松不该放松的部分。

### ⑤ 风险与副作用

- **出站基础设施阻断的实现成本高于 hook 层文本匹配**：需要容器网络策略/防火墙规则/无出网代理，
  这比在 Python hook 里写一个 `if "requests" in command` 复杂得多，**是本方案里工程量最大的一块**。
  **不能偷工减料退回"用 hook 判断命令里有没有联网相关词汇"**，因为那正是要否决的旧机制的同构复现
  ——如果施工时因为工程量大而退化成文本匹配当"网络阻断"，等于名义上做了 Q-E、实际上什么都没变。
- **资源上限设置不当的双向风险**：设太紧会重演"07-02 那种 30 分钟单图配方发明"被杀死
  （压制了刚好要保留的那条成功路径）；设太松则失去保险意义。**具体数值需要实测校准，
  本稿不拍死，建议第一版给宽松上限（比 07-02 实测再放大几倍），后续按实际运行数据收紧**。
- **"路径级判定不检查内容"这条本身有一个残余风险**：如果执行者在允许读的范围内（比如 skill
  文本、case_data 图像本身）**读到**了什么不该看的内容——这不是本方案要防的（那些本来就是
  合法输入）；但如果执行者**把允许读的内容原样转存到允许写的输出目录、再想办法从输出目录带出去**，
  这条路径本身没有被这套边界挡住（因为读写都在允许范围内）。**这个风险不是 Q-E 要防的**——
  出口带出去这件事最终还是要靠"orchestrator 之外没有人接收这个环境的输出"这条更上层的边界
  （merge 之后产物只进 run 目录，不经任何外部信道），Q-E 只负责这个环境本身的读写/网络/资源，
  **如实标注这条不在本节机制覆盖范围内**。

### ⑥ 施工拆批与顺序

- **属问题书划定"R5 走正规程序"范围**，需等交叉对抗审 + 用户拍板。
- 建议顺序：先落路径级判定的收拢（现状已经是路径判定的部分，整理成单一模块，不变逻辑，
  纯重构，可提前做）→ 网络出站基础设施阻断（工程量最大，需要单独评估容器/CI 环境的实现方式）
  → 删除命令形态黑名单 + 补资源上限 → 四条锁验证 → 才能进入 R7 实验（该实验本身就是在验证
  这批改造有没有真的带来差异）。

---

## Q-F · 工具箱怎么进化，且不作弊？

### ① 方案

三层注册表**认可问题书给出的形状**（Core/Recipes/Experimental），但收紧 Recipes 的分层维度
（见 §0.2 的意见）与晋升门：

- **Core**：随产品发布，当前即 `scripts/tool_scripts/cv_probe.py` 的 8 个子命令
  （crop_zoom / wall_line_profiler / storey_line_profiler / px_m_calibrator /
  window_cc_detector / overlay_logger / prescan-plan / prescan-elevation）。
  **对所有能力档、两条正式 lane 一视同仁可用**——这是"工具正确性不随模型档位改变"的字面落实。
- **Recipes**：**按图纸风格版本化（去掉"能力档"这个维度）**，例如 07-07 reading_summary
  §6 记录的两个真实坑——"dim-green 尺寸链颜色比标准阈值暗（g≈135 vs 224）"、
  "抗锯齿细描内墙 tone 95-170 vs 常规 128"——这类"某种绘图风格下默认阈值失效"的情形，
  适合做成一个"弱线宽松阈值"Recipe，**按检测到的图纸特征（而非按跑图的模型是谁）自动或半自动
  触发**。**能力档只影响"低档模型跑的时候是否默认自动触发这个 Recipe，还是仅作为可选项"
  这一条调用策略**，不影响 Recipe 本身的实现或输出正确性——工具输出对任何调用者都是同一段代码、
  同一个结果。
- **Experimental**：run-local，现场发明（07-02 的 tool-invention 路径的家）。
  在 CV Lab（Q-E）里产生，随 run 落盘（access_log 已经记录了它写了什么），
  **默认不进入下一次 run**，除非走晋升门。

**晋升门**（Experimental/新 Recipe → Recipe/Core，全部条件 AND）：
1. 在**产生它的那个 case** 上证明有改善（必要非充分）；
2. **接口不写死本 case 的坐标/阈值常量**（施工审查项：静态扫描该工具源码里的数值字面量，
   与产生它那个 case 的已知像素尺寸做粗粒度比对，命中即打回要求参数化；这是辅助手段，
   不能替代人审）；
3. 只读 Q-E 划定的合法输入范围（工具本身也要过 CV Lab 的边界检查，不能自己开后门读 gt）；
4. **盲测晋升检验**：在该工具**从未参与开发**的至少一个 holdout case（当前候选池 = sm20/sm21/
   sm24 三个 anchor，未来增加）上跑一遍，**用 gate①/自洽性信号打分（候选覆盖率、链闭合率），
   不用 GT 打分**——GT 只留给晋升到 Core 这一档的最后一次人工确认（见下）；
   不倒退（不能让 holdout case 的既有自洽性指标变差）；
5. 有确定性测试 + 明确写出已知失效场景（例如"该 Recipe 对纯色填充无描边的墙不生效"这类）；
6. 走既有的跨家族审阅流程（§5#8 矩阵），**这就是普通代码变更，不设特殊通道**。
7. **仅 Core 晋升（不含 Recipe 晋升）额外加一条**：晋升评审时允许**恰好一次**、**不可迭代**的
   gate②/人工 GT 核对（不是拿 GT 反复调参，是"看一眼最终结果对不对"这种单次确认动作，
   且必须在晋升记录里写明这是"评审"不是"调参"——如果这次核对发现问题，工具打回重做，
   下次提交视为**新的一次晋升尝试**，不得对着同一次 GT 反复修改重试）。
   **理由见⑤风险**：自洽性信号无法完全排除"系统性偏但自洽"的假阳性，Core 承载的信任等级最高，
   值得这一次性成本；Recipe 层级更低、更新更频繁，不设此门槛以保持迭代速度。

**lane 分账协调**：晋升发生**不改变任何历史 run 的 lane 记录**（`reading_mode_provenance` 是
每次 run 落盘时的快照，不可变）。晋升只改变**未来** autonomous-lane run 可用的 Core/Recipes
版本——即"tool-invention 产出可以进 Core 从而变成 autonomous lane 的一部分"这句话的机械落实：
下一次 autonomous run 引用新版本的 `toolbox_version`，那一刻起该工具才第一次算进
autonomous lane 的能力范围。

### ② 依据

- `scripts/tool_scripts/cv_probe.py:106-147`：现有 8 子命令即 Core 的现状基线。
- 07-07 `reading_summary.md` §6"Schema feedback"第 6 条明确写出两个真实的图纸风格阈值坑，
  是"Recipe 该长什么样"最直接的第一手证据。
- 问题书 Q-F 的三层结构本身与 plan.md R8 一致（`AI_agent/plan.md` "R8 · 工具箱进化机制"块），
  本节是把它具体化为可施工的晋升门，不是另起炉灶。

### ③ 否决的替代方案

- **"按能力档发不同版本的 Core 工具"**——见 §0.2，否决理由 = 直接违反 §0.3"不为 Haiku 定制"
  的用户铁律；也会让"降档阶梯"这个方法论失去意义（如果 Haiku 用的工具本身就和 Sonnet 不同，
  就没有"同一条工序换低档模型跑"这回事了，等于默默放弃了降档验证的前提）。
- **"晋升门用 GT 反复迭代直到工具在原 case 上分数最高再放行"**——问题书 §Q-F 硬约束已明确否决
  （"不得用同一 case 的 GT 反复调参之后宣称泛化"）。
- **"完全不用 GT，晋升只看自洽性信号"**——否决（仅针对 Core 一档）。理由见⑤：自洽性信号
  能被"系统性偏但自洽"的假阳性骗过，Core 是最高信任等级，值得付出"一次性、不可迭代"的
  GT 核对成本；但**保留这条只对 Core 生效、不下放到 Recipe**，是在"不作弊"与"不过度消耗 GT
  这个稀缺资源"之间取的平衡——如果连 Recipe 晋升都要 GT 核对，GT 会被消耗得更频繁，
  增加"看得多了就等于调参"的滑坡风险。
- **"人工评审员自己判断像不像过拟合，不设机械检查"**——否决。这类判断非常依赖评审员的经验和
  当时状态，历史上（07-27/07-28 那批判卷器设计）已经反复出现"边界留给施工方/评审方猜"就会
  出漏洞的教训；机械检查项（静态扫描常量、holdout 跑分对比）虽然不完美，
  但比"全凭评审员肉眼"更可复现、更可审计。

### ④ 验收形态

- **锁 1**：`test_promotion_blocked_without_holdout_case` —— 构造一个只在单一 case 上有评测记录
  的候选工具提交，晋升 CLI/校验脚本必须拒绝，报错信息需明确指出缺 holdout 证据。
- **锁 2**：`test_promotion_rejects_hardcoded_case_dimensions` —— 构造一个源码里出现
  与已知某 case 像素尺寸吻合的数值字面量的候选工具，静态扫描步骤必须标记（即使不是唯一判据，
  至少要能拦下明显案例，如 07-19 NIT-1 记录的"用真实楼宽 15.0 当占位符"那种坑的同类问题）。
- **锁 3**：`test_core_promotion_requires_single_gt_review_record` —— 晋升到 Core 的记录里
  必须包含"gt_review: {reviewer, timestamp, verdict, iteration_count: 1}"这样的字段，
  且 `iteration_count` 若 >1（说明对同一版本反复看 GT 调整过）必须拒绝晋升。
- **锁 4（回归 holdout 不倒退）**：`test_promotion_does_not_regress_holdout_self_consistency` ——
  在候选工具版本前后各跑一次 holdout case 的 gate① 自洽性汇总，新版本的候选覆盖率/链闭合率
  不能低于旧版本，否则拒绝晋升。

### ⑤ 风险与副作用

- **自洽性信号是泛化能力的代理指标，不是证明**：一个工具可能在两个 case 上都"自洽地系统性错"
  （比如永远把某类描边识别成中心线偏移半个墙厚——这正是问题书 §R2-b 记录的真实历史坑，
  08-01 那轮减卷产物"每条轴线都在容差内却因基准不对判低分"）。**这是本方案的天花板**，
  单靠自洽性信号的 holdout 无法完全排除这种情况，**这也是为什么 Core 晋升额外要求一次性 GT
  核对**——把这个残余风险压缩到"只在最高信任层级花一次 GT"，而不是完全无视。
- **holdout case 池目前只有三个（sm20/sm21/sm24）**，随着晋升次数增加，同一个 holdout case
  被反复用作"未参与开发"的验证对象，本身也会逐渐失去"holdout"的意义（工具开发者即使没有直接
  用它调参，也会因为"知道有这三个 case 存在、大概长什么样"而产生隐性偏置）。
  **风险登记，不在本批解决**——扩大 holdout 池（sm25-L 等未来 case 完成后加入）是持续性工作，
  依赖主线 case 交付节奏，本稿只能提示这一点。

### ⑥ 施工拆批与顺序

- **三层目录结构（Core/Recipes/Experimental 的物理布局与元数据格式）可以先设计、不依赖
  reading-agent/CV Lab 拍板**——这是纯组织性工作。
- **晋升门的机械检查（静态扫描/holdout 跑分对比）依赖 Q-E 的 CV Lab 落地**（Experimental 工具
  产生于 CV Lab 环境，晋升检查需要能在同样的边界下重跑它）——**排在 R5 之后**。
- **Core 晋升的一次性 GT 核对，需要在 SOP 层面明确"谁有权做这次核对"**（本稿建议 = 与 gate②/
  human 复核同一批人，不额外设新角色），**这条不需要代码，是流程文档，可以现在就写进
  new_case_guide.md，不必等其余部分**。

---

## Q-G · 实验怎么设计，才能把因果分离出来？

### ① 方案

**认可问题书的 R6 四臂 + R7 两臂设计，但给出更省成本的执行顺序 + 两处必须明确的前置条件**：

**执行顺序（分阶段花钱，而不是一次性把 12 场全跑完）**：

- **阶段 1（先跑，最省）**：R6 的 **A（Haiku autonomous）+ C（Haiku + Flash reading-agent）**，
  各两抽，共 4 场。这两臂直接回答 Q-D①"够不够复现 07-07 效果"这个最核心的悬而未决问题。
  **判读**：
  - C 两抽都达标（§4 量化线）⇒ **本批次的验收条件已经满足**（controlled lane 达标），
    B/D 变成"锦上添花"的确认性实验，可以缓做或不做——省下 4 场。
  - C 没有两抽都达标 ⇒ 需要区分"是候选机制不够"还是"是 Flash 档次不够"，这时才需要跑
    **B（Haiku + 确定性审计，即只有 gate① 升级、没有 reading-agent）** 来分离
    "gate① 升级本身贡献了多少"与"reading-agent 的返工循环贡献了多少"；
    和 **D（Haiku + 强 reading-agent）** 来判断"是不是档位不够、换更强模型能不能补上"。
  - B≈A（gate① 升级几乎不带来提升，因为没有返工机制能利用它）且 C 有提升 ⇒
    说明提升来自"检测到问题后能重做一次"这个循环本身，不是检测能力本身——
    这是问题书 Q-G 提出的判读口径，本稿认可并采纳原文措辞。
  - D 也不达标 ⇒ 问题书原文判读"问题在工具与任务分解，别再加 reading-agent 推理"——
    本稿认可，且指出这种情况下应该回头看 Q-A⑤ 的候选召回天花板（很可能是候选生成工具本身的
    召回不够，不是"agent 不够聪明"）。
- **阶段 2（视阶段 1 结果决定要不要跑）**：B、D 各两抽，共 4 场。
- **R7（可与阶段 1 并行，甚至更早跑）**：Sonnet + 固定 wrapper 硬隔离 vs CV Lab，各两抽，共 4 场。
  **建议提前到最先跑**，理由：① 它本质是"改造后的隔离有没有引入回归"的验证，不依赖 Q-D
  的 reading-agent 是否落地，只依赖 Q-E 落地；② Sonnet 目前已经接近满分（全卷 92.1%），
  这个实验是**差异检测**（isolation 改造前后是否有实质差别），不是**能力探底**，
  成本敏感度低（就算这 4 场跑出来 Sonnet 表现没变化，也是有信息量的负结果——
  说明 07-08 老隔离机制的摩擦对 Sonnet 这个档位影响不大，问题主要在低档模型，
  这本身是一条值得记的结论）。

**总成本**：最省情况 = R7 四场 + R6 阶段 1 四场 = 8 场；最贵情况（阶段 1 不达标）= 8 + 4 = 12 场，
与问题书原设想一致，**本稿只是给出了"能不能不跑满 12 场"的判读优先级，没有减少最坏情况的场次**。

**两处必须明确的前置条件（问题书没写、但不写清楚会让结果不可比）**：

1. **R6 各臂的执行时 `run_profile` 与验收时 `run_profile` 要分开**。
   如果直接用 `regression`（Q-A/B 升级后会 BLOCK）去跑 A 臂（无 reading-agent、没有任何返工
   机制），一旦触发 BLOCK，run 会在半路被拒收、**产不出完整数据**（无法比较"最终产物质量"，
   因为根本没有最终产物）。**建议**：R6/R7 所有臂执行时统一用 `exploratory`（允许跑到底、
   产出完整数据），**报告与验收判读时，对同一份产物用 `regression` 的 disposition 规则重算一遍
   blocking 集合**（`schema.py::disposition()` 是纯函数，可以对同一份 `checks.json` 事后
   套用不同 `run_profile` 重算，不需要重新跑一次识图）。这样"执行不中断"与"验收标准从严"
   两个目标不冲突。
2. **R6 若在 Q-E 的 CV Lab 落地之前先跑，结果要显式标注"隔离机制未升级"**，
   因为旧隔离的命令形态封杀（§1.8 的 7 次 denied）本身就是一个混杂变量——
   如果 A/C 两臂都在旧隔离下跑，测出来的差异里混着"旧隔离对 candidate 覆盖率检查触发的返工
   有多少摩擦"这个未知量。**如果 R5 暂未完成而 R6 先跑，报告必须注明"本轮结果为
   isolation-confounded，CV Lab 落地后建议至少重跑表现最弱的一臂做复核"**——
   这不是阻塞 R6 先跑（阶段 1 的目的是尽早拿到 Q-D 的核心答案，值得先跑哪怕有混杂),
   而是要求报告诚实标注这个混杂，不能把这轮结果当作排除了隔离因素的干净结论。

### ② 依据

- 问题书 §1.5"单抽是噪声"（2.8 倍差）——直接支持"每臂至少两抽"这条硬约束，本稿沿用不改。
- `AI_agent/plan.md`"R6/R7 · 受控实验"块——本稿的四臂/两臂设计与措辞基本采纳该块原文，
  本稿的增量贡献是执行顺序（阶段化）与两条前置条件。
- `src/validator/checks/schema.py:121-...`（`disposition()`）是纯函数、只吃 `run_profile`
  参数——这是"执行用宽松档、报告用严格档重算"这个方案在代码层面可行的直接依据
  （不需要新写重算逻辑，函数已经支持这样用）。

### ③ 否决的替代方案

- **"一次性跑满 12 场再统一分析"**——否决，理由是成本；阶段化设计能在花掉三分之一成本时
  就拿到"controlled lane 是否达标"这个批次最核心的问题的答案，没理由不这样做。
- **"用单抽 + 事后 bootstrap 估计方差代替两抽"**——否决。本项目已经实测同配置两抽差 2.8 倍
  （§1.5），这种量级的方差不是靠统计推断技巧能弥补的，**真实跑两抽仍是最直接、最不会被
  质疑"是不是统计方法选错了"的做法**。
- **"用不同 run_profile 分别跑 A 臂两次（一次 exploratory 一次 regression）当作变量隔离"**——
  否决，改用"跑一次 exploratory + 事后用纯函数重算" ——因为分别跑两次会引入**新的**噪声
  （两次识图会话本身的方差，§1.5 已经证明这个量级不小），而 `disposition()` 是确定性纯函数，
  事后重算不会引入任何噪声，结果更干净。

### ④ 验收形态

- 本节的"验收"即问题书 §4 的量化线本身，不重复列出。
- **过程验收（判读口径是否被正确执行）**：报告文档必须显式写出①每臂的 `run_profile`
  执行值与验收值分别是什么②每臂是否 isolation-confounded（Q-E 是否已落地）——
  **这是报告格式检查，不是代码锁**，属于 R6/R7 跑测 SOP 的一部分，建议写进
  `new_case_guide.md` 的判读记录模板。

### ⑤ 风险与副作用

- **阶段化执行的风险**：如果阶段 1（A/C）看起来"差不多达标但有一两条边缘未过"，
  会有主观空间去"要不要跑阶段 2"——**这个判断本身需要写死的量化标准**，本稿建议直接采用
  问题书 §4 给的量化线（内墙 ≥95%/外轮廓 100%/多画 <3m/窗全项命中）作为唯一判据，
  不接受"接近了、感觉应该没问题"这类模糊判断——**再次回到"文档不能验证别人是否遵守自己"
  这条教训**：判读标准必须是可以被机械核对的数字，不能是主观感觉。
- **R7 提前跑可能"浪费"**（如果最终发现 Q-D 的 reading-agent 设计需要大改，R7 验证的隔离机制
  可能也要跟着改）——**接受这个风险**，理由是 R7 的验证目标（CV Lab 有没有实质性放松限制且
  没有打开信息泄露口子）相对独立于 reading-agent 的具体设计细节，即使 reading-agent 大改，
  隔离层的验证结论大概率仍然有效。

### ⑥ 施工拆批与顺序

- 全部依赖 R4-c（reading-agent，A/C/D 需要）与 R5（CV Lab，C/D 若要在新隔离下跑、R7 需要）
  先行落地，**不可提前开工**，但**判读口径文档（本节①②）现在就可以写进 SOP**，不需要等代码。

---

## Q-H · 排序与依赖

### ① 方案

本稿认可 `AI_agent/plan.md` 现有的依赖图（R0✅→R1→R2/R3/R4-a/R5→R6/R7→R8），
在此基础上补三条本稿新增的强制顺序关系（来自 Q-A…Q-G 的具体设计）：

```text
R1（修尺子，P0）
  └─→ R3-b/c + Q-A/Q-B 四个 gate① 新信号（同一批文件，建议合并施工批次）
         └─→ R2（离线重判历史产物，验证新信号能否分开好轮/坏轮——Q-A④ 明说需要跑）
                └─→ 阈值定案（候选覆盖率/标定一致性的 BLOCK 阈值，需要 R2 数据，不能纸面拍）

R4-a（reading_mode 分账块，便宜）── 可与上面任何一支并行，越早做越好
                                    （越晚做，越多"忘记标注 lane"的历史 run 无法归类）

【本稿交叉对抗审 + 用户拍板】── 卡住下面三支
  ├─→ Q-C ReadingService 接口骨架（先只做 FrozenCaseBundle 类型化，不依赖 reading-agent 细节）
  ├─→ Q-E CV Lab（路径判定收拢可提前，网络阻断/资源上限待拍板后做）
  └─→ Q-D reading-agent（需要 Q-C 骨架 + Q-A/Q-B 的 gate① 信号已落地）
         └─→ R6（需要 Q-D 落地；C/D 两臂若要用 CV Lab 还需要 Q-E）
R7（需要 Q-E 落地，建议提前跑，见 Q-G①）

R6 + R7 出结果 ─→ R8 晋升机制机械检查落地（Q-F 目录结构可提前，晋升门检查依赖 Q-E）
                 ─→ §4 五条验收判据逐条核对 ─→ reading 批次收口 ─→ 回归主线（sm24 e2e → C2 收官）
```

### ② 可以立刻开工的清单（不依赖本稿架构部分拍板）

1. R1 全部（问题书已经列出，本稿不改）；
2. Q-A/Q-B 的 gate① 检查升级与新增（`reading.py`/`schema.py` 扩展，复用既有机制）——
   **但 `candidate_ledger` schema 字段的具体形状需要先核实 `cv_probe.py` 候选 ID 的稳定性**
   （Q-B⑥ 已标注为需要施工前先读一遍确认的事项）；
3. R4-a（`reading_mode` 分账块 + 报告按 lane 拆分）；
4. Q-F 的目录结构设计与晋升 SOP 文档（不含机械检查代码）；
5. Q-C 的 `FrozenCaseBundle` 类型化收拢（现有冻结机制的重构，不涉及 reading-agent）；
6. Q-G①②的判读口径写进 SOP 文档。

### ③ 必须等本稿交叉对抗审 + 用户当面拍板才能开工的清单

1. Q-C 的 `ReadingProfile`/`ReadingResult`/`evidence_manifest` 完整接口（含 controlled 分支）；
2. Q-D 的 reading-agent 完整实现；
3. Q-E 的 CV Lab（命令形态黑名单删除 + 网络出站基础设施阻断 + 资源上限）；
4. Q-F 的晋升门机械检查（依赖 Q-E）；
5. R6/R7 实验执行（依赖 2/3）。

### ④ 验收形态

- 本节验收 = 上面依赖图本身能否被机械核对："某个任务的施工 PR 是否在其声明的前置条件全部
  合并之后才开始"——这属于项目管理/git 历史核对，不是代码锁，**建议在派工单里显式写清楚
  每个 Slice 的前置依赖**（沿用本项目一贯的 Slice 拆分 + 派工单纪律），而不是新增一种机制。

### ⑤ 风险与副作用

- **依赖图本身可能因为施工中发现的新事实而调整**（例如 Q-B⑥ 提到的 `candidate_ledger`
  与既有候选 ID 的对应关系如果核实后发现不稳定，Q-A/Q-B 的施工会被推迟，进而推迟后续所有依赖它
  的工作）——**这是设计阶段无法消除的风险，只能要求施工方一旦发现前置假设不成立立刻停下上报**
  （沿用本项目"欠规格边界不许自行降级为假设"的纪律，多次在决策记录里验证有效）。

### ⑥ 施工拆批与顺序

即②③两个清单本身，不再重复。**建议派工方式**：②清单可以合并成 1-2 个施工批次先行（预计与
R1 同批或紧随其后），③清单等本稿走完交叉对抗审 + 用户拍板后，按
`Q-C 骨架 → Q-E 路径部分 → Q-D → Q-E 网络/资源部分 → R6/R7 → Q-F 机械检查 → R8`
的顺序分批派工，**每批仍遵守"整批做完再审一次、不拆多轮对抗审"的既有纪律**（除非某批本身
体量过大到需要 Slice 拆分，那时按 Slice 边界做轻门而非拆多轮完整对抗审）。

---

## 附录：本稿明确"无法在不施工前提下判定"的事项清单（汇总，避免散落各节被漏读）

1. **Q-A④**：新增的候选覆盖率/标定一致性检查能否真的在 07-07/07-02/07-30 三份历史产物上
   分开"好轮"与"坏轮"——需要先写出检查代码，再离线重判三份产物（R2 阶段）。
2. **Q-B⑤**：候选覆盖率信号在非 Claude Code 执行环境（未来本地开源 VLM 部署）下，
   工具调用是否还能产出等价的不可伪造日志——需要在真正切换执行环境时验证。
3. **Q-D④/⑤**：reading-agent 按本稿设计（不看图、结构化清单驱动一次局部返工）
   够不够复现 07-07 的效果——需要跑 R6 的 C/D 两臂，两抽起。
4. **Q-D⑤**：reading-agent 结构化信号是否完整覆盖了 07-07 当时全部的干预内容——
   完整 prompt 已丢失，无法逐字核对，只能靠 R6 的行为结果间接判断（C 臂若不达标，
   这是首要怀疑对象）。
5. **Q-E⑤**：网络出站基础设施阻断与资源上限的具体数值——需要结合施工时容器/CI 环境的
   实际能力做一次实测校准，本稿只给出参照量级（以 07-02 实测为下限）。
6. **Q-F⑤**：holdout case 池（当前仅 sm20/sm21/sm24）是否足够支撑晋升门的泛化证明强度——
   随晋升次数增加需要持续评估，不是一次性能判定完的事。
7. **Q-B⑥**：`candidate_ledger` 新字段与 `cv_probe.py` 现有候选 ID 生成机制的对应关系是否稳定
   ——本稿未逐行核对 `cv_probe.py` 各子命令的候选 ID 生成代码，需要施工前先确认。

---

## 结语：与问题书 §0.4 的对照自检

本稿全篇没有在任何一节论证"要不要 reading-agent"——按 §0.4 的裁定，这个问题已经关闭。
Q-D 的全部篇幅用于回答"怎么固化"：把 07-07 可考据的干预内容拆解成四个可代码化信号（Q-A/Q-B），
让 reading-agent 变成一个不看图、只搬运 gate① 结论的 Flash 级结构化调度器（Q-D①），
用接口形状（Q-C）与五条锁（Q-D④）把 §2.2 四条约束从纪律变成代码断言，
用"两次运行物理隔离、中间只能通过改文件传递"的架构（Q-D①末段）落实
"验收必须脱离 dev 期开发者角色完成"这条此前只是文字声明的要求。
**本批次的验收标准仍然是问题书 §4：controlled lane 在 sm21/sm24 两案、全卷、各两抽，
拿到接近满分——本稿的全部设计都是为了让这件事发生一次，且发生的方式是可审计、可复现、
可以在将来被拆掉重验证"autonomous 单独行不行"的**，不是去论证或替代那个北极星目标本身。
