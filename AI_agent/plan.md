# 行动清单（活计划）

> **本文件 = 当前开发计划的活文档**：记录最近的决策与待办，**动态调整、近细远粗**。不是"一次定终身"的路线图——
> 随开发进展滚动重写。**分出去的独立模块用单独文档**（见末尾「分出去的模块」）；项目结构/当前状态看
> [CLAUDE.md](CLAUDE.md)；已闭环里程碑与历史决策看 [decision_log.md](decision_log.md)；架构细节看
> [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)。
>
> 优先级：P0（立即）/ P1（一周内）/ P2（依赖 P0/P1）。术语口径见 CLAUDE.md 顶 banner。

---

## 当前焦点

0–5 管线 + 逐段校验架构（gate① 确定性 + gate② judge）已落地，sm20/sm21 两份 golden baseline 在册。
**当前在把"逐段 judge-in-the-loop 编排"真跑起来、出第一份带 judge 的规范 baseline**，并扫尾两步法/评测的残留。

> **🔴 [P0 顶置 · 2026-06-24 首做] 识图质量诊断**——见 [N1d](#n1d-p0-识图质量诊断-2026-06-24-顶置)。
> 2026-06-23 sm21 批次重跑：Sonnet + gpt-5.4-mini 两条 reading J0 都 severe→reread。**决定性证据已坐实=真回归**：
> sm21_pre（06-09 Sonnet，**md5 同一张图**）读干净 7 区，reading-honest 新 schema(06-22) 后同模型同图过度分割
> （provenance=dimension_derived）。**头号嫌疑=reading-honest 的 dimension 字段**，非杂物/非模型弱。先 diff 旧/新 schema + A/B 控变量。

---

## 近期（细）

### N1. [P0] ✅ sm21_anchor 出首份 judge-in-the-loop baseline（2026-06-21 完成）
- 用 [`scripts/tool_scripts/run_stage.py`](../scripts/tool_scripts/run_stage.py) 逐段真驱动 sm21_anchor（draw→gate①→judge②→盲重抽/几何 approve→4_mep）。**已跑通**：GPT-5.4 识图 run 端到端 clean，三份 baseline 在册（见 N1b）。
- 残留：更新 [test_baseline/index.md](../case_tests/test_baseline/index.md) + golden 测试（待 commit 时一并）。

### N2. [P0] ✅ 关闭 — sm21 South 2F 窗 x bug 不复现（2026-06-21）
- 诊断（Codex 探查 + Claude 自验）：GPT54 run 实际产出 South 2F 窗 x = gt 完全一致（[2.19,3.39]…[11.61,12.81]）。原"真 bug"是 **06-16 Opus 旧轮**产物（那轮 1_correction 把窗 x 沿立面平移 -0.24m）。随识图质量提升消失。诊断 `logs/review/request/2026-06-21_sm21_south2f_window_x_diagnosis.md`。
- 潜在隐患（降级 backlog，不急修）：Opus 轮的 -0.24m 疑似"墙厚补偿误加到 along-facade 轴"——当前好识图不触发，可能是潜伏 correction 逻辑 bug。

### N1b. [P0] sm21 双模型轮(2026-06-21) backlog —— GPT-5.4 跑测暴露的真问题
> 本轮：GPT-5.4(codex CLI `-i`)识图 → 干净 14区/112面/15窗、EP 0 severe；Sonnet 0/2 阻塞(J1/J0)；
> judge-in-the-loop 验证成功。三份 baseline 在 `case_tests/e2e_tests/sm21_anchor/run_2026-06-2*`。
> 本轮已改：run_stage S5 缺 IDD 初始化 → 加 `ensure_schema_initialized()`（待 commit）。

- **[P0] ✅ 核加跨层内墙对齐 + 外包优先（2026-06-21 完成，`6.21_CrossFloorWallAlign`）**：根因修正——轴线图**本就全楼共享**，真因=同层/跨层共用 `axis_jitter_tol=0.05`，走廊跨层差恰 0.10m 卡在容差缝（不聚类、sliver `<0.10` 严格不并）→ 两轴幸存生碎面。修=`deterministic.py` 新增 `_reconcile_cross_floor`：per-floor identity → footprint 硬锚 → **mutual-nearest** 跨层匹配（图级冲突即 flag、不静默合）→ provenance-aware sliver；新容差 `cross_floor_align_tol_m=0.11`。走廊两层对齐到 y[3.15,4.85]，**sm21 112→100 面**、zones/windows 不变。经 Codex 双审（REWORK→APPROVE-WITH-CHANGES）+ 四重验证。审计轨迹 `logs/review/{request,review}/2026-06-21_cross_floor_wall_alignment_*.md`。
- **[P1] ✅ viewer 挪独立人工文件夹（2026-06-21 `6.21_ViewerToManualReview`）**：`2_modelling/geometry_viewer.html` → `<run>/manual_review/geometry_viewer.html`（run_stage 输出改路 + 补 role 着色、record_baseline 文档 + .gitignore 同步）。后续接编辑回写 [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md)。
- **[P1] 房间类型(role) 移回 reading — ✅ phase-1 落地（2026-06-21 `6.21_RoleObservationsPhase1`）**：reading 加可选 `room_labels`(RoomRoleObservation,topology-light) + 共享词表 `src/agent/roles.py` + correction prompt 把 room_labels 当输入优先采用。绑定仍 correction 隐式做（输入升级）。**phase-2（远期，"更精准修法"用户定缓做）**：确定性绑定 sidecar `role_assignments.json` + `Cell.role_source_label_id` + gate① role-provenance INVARIANT + 4_mep unknown 策略 + sm21 baseline 重录 + **plan-local→world 一等可审变换产物**（确定性 anchor-in-cell 的使能件，把 LLM 移出空间绑定）。完整设计在 `logs/review/{request,review}/2026-06-21_role_to_reading_plan_*.md`（含 v1/v2/v3 演进 + Codex 三轮审）。
- **[P1] ✅ 命名确定性化（2026-06-23 `6.23_DeterministicNaming`，Codex 双审 REWORK→APPROVE-WITH-CHANGES + Claude 大节点全面审）**：zone/surface/window 名全部**代码确定性生成**，与 LLM `Cell.id` 解耦。方案 = **zone `Z{NN}_F{层}_{类型}_{方位象限}`**（绝对序号 `Z01..` 为唯一 handle、用户加；方位=质心相对全楼 footprint 中心罗盘、居中=`C`）+ **墙按 footprint CCW 圈序 `Z01_W1..`**（用户定，替代罗盘——非矩形 >4 面也唯一、向 C2-C4 泛化）+ 窗 `{父墙}_Win{k}` + 水平面 `Z01_Floor/Ceiling/Roof[片号]`；保留 `Cell.id` 作内部源身份。关键机制：**规范顺序并进数据流**（zvs 按 `(z层序,质心N→S→W→E,几何指纹,cell_id末位)` 排，序列化独立 re-sort → 杀 LLM 序泄漏）、配对走**对象引用 tuple→原地命名→回填 obc_obj**、floor 改按 z 排名（顺手修 cross-floor 邻接潜在 bug）、role 归一器（`meeting room`→`Meeting_Room`）、`zone_meta` 序列化进 building_geometry.json + viewer 先读它。真实 sm21 eyeball：14 区/112 面/15 窗、互逆完整性 0 违例。**本轮 = 代码 + ~30 inline-fixture 单测改新名 + 新增回归（cell 序无关/配对穿排序/role/C带/窗序）**；走 validate_case 精确重建的 9 个 golden 测试**打 strict xfail**（reason=pending sm21 batch）。测试 **323 passed / 9 xfailed**。审计轨迹 `logs/review/{request,review}/2026-06-23_deterministic_naming_*`。侦察 map `2026-06-21_role_and_naming_recon.md`。
- **[P0] ✅ 外包优先：立面外包尺寸权威 + 确定性吸收（2026-06-23 `6.23_EnvelopeFacadePriority`，Codex 三审 REWORK→REWORK→APPROVE + Claude 大节点全面审）**：根因——zone footprint 老跑成 ~14.76×7.76（每边内缩半墙厚 0.12=建在墙体中线），系统性差 ~0.24m、≠ gt 外包 15×8（同 N2 -0.24m 窗 x 漂移根）。外包信号"在但没结构化"（reading 立面维度 legacy 格式有 `from=[0,..] to=[15,..]`、`role=overall` 全 run 没人填；核又只拿 CorrectedGeometry 看不到 reading）。修=**新 `src/agent/correction/envelope.py`**（共享 util，pipeline+validator 同调）：从立面视图维度 from/to **bounds**（单位安全 bounds-first、`text="15000"→15.0`）+ outline/wall_fill 描边 extent（覆盖 gpt54 无 dimensions[]）抽**评分候选**（overall note/role > 描边 > 裸 max > text），要第二证据、跨立面分歧→conflict；解析成 `AuthoritativeEnvelope`(每轴 bounds)。`apply_deterministic_core` 加 `authoritative_envelope` 入参（None=向后兼容）：传**权威 bounds 设 lo+hi**（`[0.12,14.88]→[0,15]` 非 fixed-lo）→ **attachment-based 只挪贴旧边界的 cell 外边**（内隔墙不动、窗 along 默认不平移、靠父外墙重建跟）→ **pre-move 碰撞门**（越内轴/翻转/<min_edge 0.10 则 skip+unsupported）→ 结构化 audit → `validate_corrected_geometry` 兜底。`envelope_reconcile_tol_m=0.30` 进 correction.yaml+CoreTolerances+A0 `ENVELOPE_RECONCILE_TOL`。**验证**：sonnet+gpt54 correction → footprint **[0,15]×[0,8]**、内隔墙保留、**South 窗 world-x 精确命中 gt**（2.19/3.45/4.11/6.3/9.69/11.36/11.61）。测试 **335 passed/9 xfailed**。审计 `logs/review/{request,review}/2026-06-23_envelope_facade_priority_*`（三审）。**记录到 backlog（用户定后续）**：① 通用尺寸链 `overall>segment` 差额内分；② 终极优先序 **轴线 > 立面外包 > 平面外包**（轴线最高、需平/立共轴系判定，"很规范的图"轴线完全确立时为最优）；③ reading dimension `role` 全量填（legacy→P1a 迁移，让 overall/segment 结构化）；④ 抽取的 reversed-facade local→world 用 sorted bounds 近似（sm21 对、非通用变换，异图前补）。
- **[reference] judge 答案来源已核（2026-06-23）**：`load_gt` 读 **gt.json** 当答案（DXF 仅 bundle 留痕、judge 不直接读）；sm21 gt = `gt_from_dxf v2` 抽 + **用户人工核过**（gt.json 补 `_verified` 标记：dimensioned 直出图 + gt 叠原图核对）。**plan.md N3 已陈旧**（DXF 6-20 已导出、gt 已是 DXF 版）。
- **[P1] ✅ 机制落地（2026-06-22 `6.22_ReadingHonestJudgeRouting`）— 查 Sonnet 识图变差 + 平面降质**：诊断=**不是 Sonnet 变差/不是新回归**，是 2026-06-07 founding 框架（trust-the-dim）**reading 半边没落进 0-5 schema**（Stroke 无 provenance、缺 stroke↔dimchain check、无双通道纪律/门≠窗负例、verdict 无 recoverability 轴）→ correction 收不到冲突信号、照抄识图错穿到 J1。修=两战线（**reading 诚实** provenance/confidence/dimension_refs + stroke↔dimchain CROSS_CHECK + guide/pen prose；**judge 两轴** recoverability，J0-scoped blocking + 四条放行判据+默认中止 + J1 确认门归因），**correction(A1-A4+核)不动、不需重录 baseline**。架构总纲 D1-D5（correction 永 image-blind 不做 VLM / 脚手架=降智机制服务国产VLM→开源北极星 / 看图仲裁归 judge+重读 / who-fixes=证据冗余在+不靠猜才放行）用户全程 ratify。详 decision_log §A + contracts §0.3/§5.3 + logs/review/2026-06-21 提案+审。**残留=sm21 重跑验证**（与下方命名确定性化等待改项攒齐一次性跑，用户定）。
- **[P1] 同源欠债收尾（reading-honest 配套，让错可见→可归因→可重读恢复三件套的后两件）**：① **✅ audit→评测归因 baseline 侧（PR-A，2026-06-22）**——`record_baseline` 读 `1_correction/corrections.json` → `baseline.json.corrections_summary` + `RUN_REPORT` 加「校正审计（看错↔改错归因）」节（**不动 gate flags/计数**，Codex Finding 6）；残留=gt-diff×corrections 机械 JOIN 并入 N4 评测。② **✅ 0_reading auto re-read（PR-B，2026-06-22 落地，测试 →307 绿）**——**子代理即 0_reading runner**（主控冷启隔离子代理重看图，非 VLM-API-gated，先前误判已纠正）、3 次不过终止、每步 judge 判定，与 0–5 一致；`AWAITING_REREAD` 非终止态 + `RunPolicy.reading_runner_available` 默认 False 向后兼容 + 子代理写 flat `0_reading/*_view.json` 再 `resample --force` 记 attempt + 预算线程化到 root 段（J1 root=0_reading）+ 预声明 model/effort ladder（盲、判语不注入）。方案+审 `logs/review/2026-06-22_audit_attribution_and_auto_reread_{proposal,review}`（Codex `APPROVE-WITH-CHANGES`，7 findings 全采纳 + 用户定 SPLIT）。
- **[P2] ✅ 主控汇报优化（2026-06-23 `6.23_ReportOrgCuratedFolder`，五审闭环 8→4→2→1→0）**：每 run 产**单一 `report/`** = `FACTS.md`(确定性事实卡) + `REPORT.md`(主控+judge 动态撰写、**四桶建议** 机制/能力/脚手架/修法) + `eyeball/`(显式 collector 汇 2D 肉检图；3D viewer 留 manual_review 指针)。事实层(代码)/叙事层(主控)分离 + `REPORT.md` create-if-absent 防覆写；新增 **evidence_index**(坐标式稳定 id + dup 断言) + **citation linter**(建议必挂证据、纯词法) + **run_state**(复用 TERMINAL_STOP/ADVANCE_OK + PENDING + 几何 supersede，状态感知不发死链)；RUN_REPORT.md→report/ 原子迁移；新 `scripts/tool_scripts/report_assembly.py`、测试→320。两份真实 run（gpt54 clean / sonnet stopped）已生成 report/ 验证。审计轨迹 logs/review/2026-06-22_run_report_organization_{proposal,review}（一~五审）+ 2026-06-23_report_org_execution_log。**残留**：主控撰写 REPORT.md 叙事+四桶建议是**每次跑后**的活（骨架已就位，sm21 重跑时实操）。

### N1d. [P0] 识图质量诊断（2026-06-24 顶置）
> 缘起：2026-06-23 sm21 批次重跑（先只 sm21；Sonnet + gpt-5.4-mini 两条 reading 并行）。两条都过 gate①
> 但 **J0（主控多模态）各抓到真识图错、都路由进 `awaiting_reread`（非终止，机制按设计运转）**：
> - **Sonnet 4.6**：1f 南带**过度分割**（把家具/底部尺寸链 tick/窗洞边当墙 → 8 道南隔墙 vs 真 2；S9-S16，其中 3.44/6.3/11.36 是南立面窗 x）；北带 S7/S8 反而对（x≈5/10）。立面窗数 S7/N5/E2/W1 **完全命中 gt**。
> - **gpt-5.4-mini**：平面**干净**（1f 7 区对、无过度分割），但 **South-F2 把 4 窗合并成 2**（1200|720|1200 当一扇宽窗）+ **2f 南带漏 1 隔墙**（4 房→3、2f 仅 6 区）。
> - 互补失败模式：Sonnet 平面差/立面满分；gpt-mini 平面好/立面欠读细节。

- **⚠️ 诊断修正（2026-06-23 晚，决定性证据）= 这是真回归，reading-honest schema 是头号嫌疑，非单纯 case×model**：
  - **强线索（非铁证，一环待验）**：`smalloffice_21_pre/phase1/{1f,2f}_view.json`（2026-06-09）读的图与 sm21_anchor **md5 完全相同（同一文件）**，结果 **1f 10墙、2f 10墙、各干净 7 区**，partition 按房间关系描述（"vertical partition **between office 1 and office 2**"），self_check=模型自检非手搓。**但"该 phase1=Sonnet"仅 decision_log 两处文档记载（且刻意与 05-28 pocv2 的 Opus4.7 区分），产物内无 model 字段、git log 无、summary 未记 → 无 artifact 级硬证**。若它实为 Opus，回归论退回"Opus旧干净 vs Sonnet新崩"、模型变量重新混入。**∴ 不靠此环——下方 A/B 控变量（同模型同图旧/新 schema）是不依赖该归属的决定性证明。**
  - **同一 Sonnet、同一张满家具的图**：**旧 schema(06-09) 读干净** / **reading-honest 新 schema(06-22 加 `provenance/confidence/dimension_refs` + dimension-chain 强调) 后(06-20·06-23) 过度分割**，且 06-23 wall provenance=**`dimension_derived`**。**新"诚实"字段疑似把模型从"描绘画出的隔墙"推向"按尺寸链派生墙的存在性"→ 在尺寸段界/窗边造伪墙**（讽刺：诚实机制本意提升识图、却可能反噬）。
  - **先前"非回归 / case×model 杂物陷阱"判断作废**（保留作排查史）。杂物+尺寸链仍是 dimension-derived 失败的**显形场**，但**触发器是 schema 变更**，非根因。gpt-mini（另一模型）在新 schema 上也欠读，与"schema 问题、跨模型"一致。
  - 旧线索仍有效：三模型对比是 correction 对比（识图共享 Opus4.7 一份）；sm20(06-15 Sonnet)读干净（但 sm20 无家具）——这些现在归为**佐证 schema 回归的对照**，非主因。
- **⚠️⚠️ A/B 控变量已跑（2026-06-24）= 「schema 单因」回归假设证伪**：单变量隔离（同 Sonnet 4.6 / 同 sm21 1f / 唯一变量 = reading skill 版本，当前 reading-honest vs `fa04ef6^`），每臂 2 样本（隔离 skill 目录 `/tmp/ab_{new,old}/0_reading/`，Sonnet 冷启子代理只喂图+skill、禁读 gt/旧识图/另一臂）。结果：NEW 14/16 墙、OLD 13/14 墙（区间 13–16 重叠、n=2 不显著），且**两个 NEW 样本 30 条墙全标 `seen`、0 条 `dimension_derived`**——诊断①推测的"模型用 dimension_derived 给伪墙背书"漏洞**根本没触发**，头号嫌疑证伪。06-23 那批 `provenance=dimension_derived` 不是 schema 的普遍行为。**局限**：n=2 偏小（"0 dimension_derived"与样本量无关、稳）；任务 prompt 给两臂都注入了"家具进 uncaptured/一条连续墙一笔"纪律（测的是"schema 是否在已有纪律上**额外**加重"=否，非全裸 prompt 之差）。**∴ 原定修法③（收敛 schema 表述）取消**——schema 不是过度分割主因。
- **重定向（真凶不在 schema）**：原始 sm21 的 8 道南隔墙过度分割在受控隔离下**两臂都没复现**（强差消失）；进一步查 attempt 级轨迹彻底坐实，见下。
- **⚖️ 根因坐实 + 误归因源头定位（2026-06-24，决定性）**：查 `run_2026-06-23_sonnet_reading/0_reading/attempts/` 1f 三次 attempt = **att1 16墙全`seen` / att2 16墙(15`dimension_derived`+1seen) / att3 10墙全`seen`(接受但 quarantine,3次预算耗尽)**。决定性事实：① **att1 用全 `seen` 就已 16 墙过度分割**——过度分割在 `dimension_derived` 标签出现**之前/无需该标签**就发生了，att2 只是给同样的 16 墙换了标签（墙数没变）；② **"schema=头号嫌疑"是一次误归因，源头精确定位 = att2 的 judge 判语**原话"provenance='dimension_derived' confirms the mechanism"，这句 judge **假设**被原始诊断当既成事实，传进 plan/memory 成头号嫌疑。att1(all-seen 16墙)+ A/B(0 dimension_derived 仍 14-16) 双重推翻它。③ 过度分割本质 = att1 judge 原话"6 fabricated partitions from **window edges + dimension ticks**" = **Sonnet 对满家具图的首抽随机感知失败**，既不需 schema、也不需 testdata 提示（A/B 没给 testdata 仍 14-16）。④ 已接受产物其实**干净**（新10/旧11墙），"reading 变差"的印象来自盯**中间坏 attempt**(16)而非接受产物——系统按设计工作（judge 正确抓 + reread 16→10）。
- **真正 lever（schema 修法③彻底出局）**：攻"**窗洞边/尺寸链 tick 被当墙**"的首抽感知失败——① 杂物/尺寸掩膜 or 局部放大裁图（**原"次要"升为主 lever**）；② 首抽纪律专门强化"窗洞边≠墙、尺寸 tick≠墙"；③ 加 reread 预算（这道难题 3 次没跑够）；④ 换强模型（Opus sm24 一次干净）。
- **流程教训**：一句 judge **假设**判语（"dimension_derived confirms the mechanism"）被当事实、直接成修法依据，未先验证就传遍 plan/memory。**judge 的归因假设进入修法前必须先用 attempt 级事实证伪/坐实**。呼应 [run 溯源记录硬化] —— attempt 级 provenance 本就在册（attempts/NNN 全留），这次靠它翻案，印证留痕价值。
- _（历史）原"明天修法方向"：①diff 旧/新 skill〔已做〕②A/B 控变量〔已做〕③收敛 schema 表述〔取消，证伪〕④杂物掩膜〔升为主 lever〕。_
- **机制侧已验证**：judge-in-the-loop 全程正确（gate① 结构过 → J0 多模态抓存在性错 → 判 unrecoverable → auto-reread 启动）；gpt-mini reread att2 经**通用"不合并相邻窗"纪律**把 South 立面 5→7 修对（命中 gt），证明 discipline-safe lever 有效、但平面隔墙欠读非一句通用纪律可救。
- **[P1] 污染硬隔离硬化（2026-06-23 用户定，后续改）**：reread + **所有阶段 judge 打回的盲重抽**必须**物理硬隔离**，不能只靠 prompt 约束。现状=子代理/codex 物理上有文件读权限、仅被"告知"别看 gt/旧 attempts/judge 评语（旧 flat 文件还在同目录、codex 还 danger-full-access）→ 误差预算靠自觉、不可硬保证。改法方向：给重抽器**只暴露 images+skill 的隔离工作区**（gt/attempts/judge 产物移出其可达路径或只读黑名单），把"不污染"从指令级提升到机制级。归校验架构 contamination 不变量。
- **[P1] run 溯源记录硬化（2026-06-24 用户定，等 sm24 后做、不急）**：本次回归诊断卡在「`sm21_pre`(06-09) 识图是 Sonnet/Opus、旧/新 schema」无法从产物坐实——逼出 A/B 控变量才能证。教训=**每 run 必详记全链路模型配置 + 脚手架/skill 状态**。两块缺口在 `record_baseline`/`_run/` 元数据补齐：① **全链路模型配置**——`llm.yaml` 只记 correction/mep/下游，**reading 模型漏记**（注释写"人工不经 API 无需配置"，恰是归因最关键变量），补 reading 模型 + effort/ladder + 主控 orchestrator 模型；② **脚手架/skill 状态**——戳 git HEAD SHA + dirty flag，且因 skill 可能有未提交改动，连 `skills/intake_pipeline/` + `src/agent/reading/` **内容哈希**一起记（"这 run 跑在 reading-honest 之前/之后"事后可硬证）。**注**：`fa04ef6` commit 已写 "Component 2 (persist manual 0_reading prompt/model) deferred"——缺口早识别、被推迟，本教训坐实该补。归校验架构 provenance。
- **本轮产物留痕**：`run_2026-06-23_sonnet_reading`、`run_2026-06-23_gpt54mini_reading`（各 attempts/001 + J0 verdict + reread_ladder.md）。
- **结论锚**：judge-in-the-loop + reading-honest + auto-reread 机制本身**验证成功**（错可见→正确判不可恢复→盲重读启动）；问题在**识图产物质量**这一环。

### N1e. [P0] Sonnet 怎么顶 + reading 退化（2026-06-24，**下次起点**）
> 目标=让 Sonnet 现在就能用于 reading。坐标级对账(`score_reading_vs_gt`)实测:同一张图盲读,**Opus 墙 9/9 窗 10/15;Sonnet 墙 7/9(1f 竖墙偏 0.36m) 窗 4/15**——Sonnet 原始盲读坐标差(用户裁定"Sonnet 仍很糟、Opus 基本正确")。
- **reading 退化调查已结(双路收敛,详 [logs/review/2026-06-24_reading_degradation_dual_investigation.md](logs/review/2026-06-24_reading_degradation_dual_investigation.md))**:核心 skill 规则没退化,但 ① fa04ef6 把"坐标必须读准"软化成"有尺寸链可由 correction 恢复"(对坐标 vs gt 是真退化)② 启动 prompt 06-16 缩水(丢了总尺寸锚定 + 四立面映射表 + 8 条 discipline)③ schema/guide 的 dimension 字段不同步。**注:均为指令层退化的合理机制,未证明=Sonnet 坐标错成因;sm21_pre 好识图本体是 Opus。**
- **下次做 = Sonnet 强/弱 prompt A/B**:给 Sonnet 恢复旧式强 prompt(坐标必须读准·别指望 correction 恢复 + testdata 总尺寸锚定 + 四立面映射表 + 尺寸链算式入 note),vs 现 prompt,**两边都用 `score_reading_vs_gt` 按 gt 坐标量**,看 Sonnet 1f 竖墙 0.36m + 窗错位能否压下去。顺带可修 schema/guide 不同步。
- 历史归因彻底闭合:sm21_pre 干净识图本体=Opus(05-28 pocv2),非 Sonnet 盲读;详 [[reading-quality-investigation-2026-06-24]]。

### N3. [P1] CAD→gt 满配答案（见 [proposals/cad_to_gt_extraction_plan.md](proposals/cad_to_gt_extraction_plan.md)）
- 工具链已就位（ezdxf + proxy-graphics 解码 + `gt_from_dxf` + overlay 核验）。**待用户从天正图形导出/另存 DXF** → 抽满配 gt（精确窗 x+宽、精确区划、门）。方案过 Codex 审、设计待落。
- **sm24（非方形）待补 gt（2026-06-24 用户定"做完 gt 再继续"）**：sm24_anchor 已跑出首份 run（`run_2026-06-24_opus_reading`，Opus 识图 + 全放行 + EP 0 severe，自包含收口完毕、`completed_clean`），但**无 gt**——补 gt 前不入册 golden、不再继续。补时关键=约定**非矩形房间的"期望热区数"口径**（L 走廊算 1 还是 2），区数正确性才能定量。

### N3b. [P1] sm24 非方形端到端首跑 —— 发现（2026-06-24）
> 首个非方形 case 探针。footprint 10×20m 规整、**内部 L 形走廊 + 阶梯西墙右下 office**。Opus 识图干净（reading-honest provenance 在强模型上**未诱发过度分割**，是诊断②的强模型对照点）→ 全链路跑通、EP 0 severe。run 在 `case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading/`。
- **核心能力发现（归 C2 非方形）**：确定性内核把**非矩形开敞空间过度分区**——L 形走廊拆成 Z06+Z10 两个 EP 热区，阶梯 office 拆成 3 区（8→11）。拆出的碎片**导热耦合正确**（`Z06_W1↔Z10_W5` 互逆匹配、InterZone 配对零缺陷）但**无空气耦合**（无 AirBoundary/ZoneMixing），EP 视为隔导热墙的独立区、物理上是一个连通开敞空间。→ **需在内核分解后加"区合并 / air-boundary"步骤**（同一开敞空间的矩形碎片标 `Construction:AirBoundary` 或合并单热区）。详 REPORT.md 建议·能力升级桶。
- **脚手架坑**：`run_full_pipeline` 把 EP 产物写 `<case>/output/` 而非 `<run>/EP/EP_run/`，anchor 布局下需手动归位才能 record_baseline --require-ep。应让下游 EP 输出直接落 run 目录。

### N4. [P1] 两步法 / 评测残留（原 B1.5.b / B1.5.f / B2–B4）
- **skill 迭代**：phase1 识图库 + 笔库（跨画法泛化）；phase2 规则吸收可机械化项（命名约定 / 负载密度 / day-type 名）。
- **评测嵌入**：gt diff 评测脚本（zone_f1 / 尺寸误差 / WWR / special_zone_f1 + 识图错↔推理错归因）；嵌进 record_baseline 流程。
  - **✅ 坐标级 reading↔gt 评分器已落地（2026-06-24 `score_reading_vs_gt`）**：`src/agent/judge/reading_score.py`（judge 侧，经 load_gt 读 gt，不破 gt 隔离铁律）+ CLI `scripts/tool_scripts/score_reading_vs_gt.py` + `tests/test_reading_score.py`（测试 335→341）。从 gt zone rect 派生内墙竖/横线 + 窗 span，对识图墙/窗坐标逐元素匹配，报命中/漏/多 + 实际偏移。**这是用户定的权威 reading 评测口径**（[[judge-gt-authoritative-images-auxiliary]]：数据 vs gt 为唯一标准、看图仅辅助）。残留：zone_f1/WWR 等综合指标 + 嵌 record_baseline。
- **GT 数据集扩面**：sm20/sm21 已有 gt；按需补 ≥1 异图坐实泛化。

---

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
| 0–3 复杂度升级路径（C2/C3/C4）| [capability/pipeline_0-5_capability_upgrade_suggestions.md](capability/pipeline_0-5_capability_upgrade_suggestions.md) | 骨架已立，随中期推进 |
| 再拓扑 leg（热区积木 zonification）| [proposals/geometry_first_zonification.md](proposals/geometry_first_zonification.md) | 强力支线，休眠 |
| 可编辑几何确认环节 | [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md) | DEFERRED，先讨论 |

---

## 搁置（依赖外部进展，不安排时间）

- **idfpy 替换主线**（[deferred/idfpy_embed.md](deferred/idfpy_embed.md)）：等协作者侧 MCP 全线重写交付。
- **token 优化**（[deferred/token_optimization.md](deferred/token_optimization.md)）：等 idfpy 切换后大量 CRUD 工具消失再评估。
- **fenestration/construction SimpleGlazing 兼容性 prompt 修**：等 idfpy schema 原生覆盖（当前几何优先，不动 prompt）。
- **Sonnet 4.6 / Haiku 4.5 降级测试**；**OpenStudio 几何验收**（用户人工，不卡代码）。

---

## 已完成（一行汇总，详见 [decision_log.md](decision_log.md)）

A 代码跑通 ✅ · B1 旧 skill 迁移恢复 ✅ · 两步法 POC + 切主线 + InterZone 门 + 正式指南 ✅ · 0–5 阶段重构（几何确定性化）✅ · EP 跑通 + schedule 门 ✅ · 完整体检 4H/3M/3L 全修 ✅ · 仓库整理 + 标准 case 布局 ✅ · 0–5 校验架构 M0–M4 ✅ · 新 baseline 方案 + 主 Agent 操作手册 + gt ✅ · 逐段 judge 编排 + 离线 3D 查看器 ✅ · CAD→gt 工具链 + gt 渲染 ✅
