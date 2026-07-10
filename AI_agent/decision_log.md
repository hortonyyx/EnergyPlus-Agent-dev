# 历史决策档案（decision_log）

> **本文件 = 项目历史决策与里程碑的唯一归档。** CLAUDE.md / plan.md 不再叠加历史叙述——
> 决策史、已闭环里程碑、变更日志都沉到这里。读这里是为了知道"为什么走到今天"；
> 知道"今天是什么 / 接下来做什么"看 [CLAUDE.md](CLAUDE.md) + [plan.md](plan.md)。
>
> **术语对照（2026-06-10 改名后）**：历史叙述沿用旧称——phase1=0_reading / phase2a=1_correction /
> phase2b=2_modelling+3_split_pairing+4_mep+5_intakeoutput / `run_phase2`→`run_pipeline`。
> 当前唯一口径见 [CLAUDE.md](CLAUDE.md) 顶 banner。读历史段落按此对照，勿当当前接口。
>
> **组织**：A 里程碑时间线（倒序，每条含 commits/产物指针）· B 关键决策详档（仍有约束力者
> 在 CLAUDE.md §1 有摘要指针）· C 变更日志。历史文档豁免"口径对齐当前方案"要求，链接可能指向
> 已归档/已改名的旧路径。

---

## A. 里程碑时间线（倒序）

> ✅ **C2 收官冲刺开启 + prescan 候选收窄 + 隔离协议 directive 槽（2026-07-09，Fable5 主控亲手执行=用户当日指示反转 §5#8 一日，570 绿 + 9 xfail，6 commit `9ea0a2e..850d1df`）**：①**W2 三接线债修**（`9ea0a2e`：J1 rubric 件名对齐实产 / `collect_eyeball_assets` 补收 `zones_<floor>.png` 真 bug / correction.yaml 两处 stale 注释）。②**prescan 候选收窄落地**（`20749ff`：`min_strength`/`min_line_len_px`/`label` 参数〔tick=标定锚永不过滤〕+ `diagnostics.axis_summary` 按峰聚合〔1f 370段→48轴〕+ cv_toolbox.md 三新纪律〔候选预算 0.08/30px·立面 `--no-cc`·组内标定复用（平面 91 vs 立面 58 px/m 跨组禁盲复用）〕；**gt 差分幸存验证零构件丢失**后落地、默认值刻意不动保满分带配方；分析 `logs/experiments/2026-07-09_prescan_narrowing/`）。③**C2 收官设计出稿**（`0e28520` `proposals/c2_full_unlock_design.md` 待审）：用户拍板**「C2 直接上完=完全解锁非方形」**（现 sm24 仅内部非方形、外包仍方形）；核心原则**「视图≠面」**（立面识图永不判深度，前后关系全由平面多边形确定性算出）；E1 立面可见性模型（1D skyline+确定性窗归翼=修订 D10#2，A3 降例外）/ E2 缺失立面数据政策（凹形缺口侧壁四视图互遮挡=可精确计算的 unobserved 清单·不发明窗+WARN+判卷 NA(unobserved)）/ E3 envelope 逐边仲裁；批次重排 B2→B2b→B3→B4→B5(+E1)→B5b→B6；§T 用户案例规格（sm25-L / sm26-U〔侧翼内壁放窗=E2 政策验收器〕/ sm27-口可缓，用户明后天出图）。④**Haiku 对比重跑 4 轮 pilot 止损**（`bad0200`，用户拍 reading-only 配置）：**收窄本体阳性**（pilot CV 调用 86→2-6 次·axis_summary 被消费）；质量未达地板（标定系统性锚错 60 vs 真值 92 px/m·幻觉走廊短墙·Haiku 每轮只机械满足 feedback 点名项）；定性=硬隔离协议缺 07-07 两根拐杖（per-run directive 槽+会话连续性），无状态重 spawn 每轮冷启 ~0.25M token（5 会话 ~1.03M）；执行日志 `HAIKU_RETEST_LOG.md`、被拒 pilot 未 merge 零污染。⑤**隔离缺口 #4/#5/#6a 当日直修**（`1078daa`：守卫窄放行 run prescan 子树+拷贝层级对齐 / feedback 自动指针 / spawn `--directive` 槽=07-07 directed 模式复活；#6b staging 内 resume 后置评估）。**C2 双审（Claude 双子会话，用户指示）撞 session 限额中断**——续办=重置后 resume 或明日 Codex 首审（请求单 `logs/reviews/request/2026-07-09_c2_full_unlock_review.md`）。**directed 复跑用户定当日不动**（额度）。**下一轮开场（用户 07-09 收工定）**：① GPT-5.6 发布→双模型家族协作模式修订 ② C2 实现状态白话对齐 → 再回正常排期。
>
> ✅ **GPT-5.4-mini 弱模型交叉测试=阳性满分带（迁移性成立·关闭）+ 跑测 SOP 铁律登记 + Fable5 期文档对齐（2026-07-08 晚，Opus 主控/Codex 施工，未 commit）**：①**交叉测试阳性**（`run_2026-07-08_gpt54mini_cv_retest`，走**正规 flow**：gate①+J0 judge_pass+attempts+render+grade+score_vs_gt+report 四桶）：gpt-5.4-mini（codex CLI·非 Claude Agent tool）+ CV 工具箱在 sm21 = 墙 9/9·0.0m·平面窗 6/7·立面窗 15/15 complete·过度分割 0 = 与 Haiku 07-07/Sonnet 5 同级（仅差 1 平面窗，1f 南窗偏 0.53m）→ **CV 工具箱配方模型无关、非 Haiku 特调**；06-23 无工具箱两失败点全修复（South-F2 四窗并两窗→4/4、2f 漏隔墙 6区→墙 5/5·7区）；**E 批固化在新模型 hold**（spawn prompt 无 measure-before-draw，读 cv_toolbox.md 自声明 required 自发调 13+ CV 工具/图）；效率 ~0.9M tokens/case（~1.5x Haiku，弱模型试错多）；隔离=clean-room staging（gt 物理排除·codex 无 guard 层弱一层）。用户肉检 reading 后**关闭交叉测试**，解锁开源 VLM 验收提前案。②**跑测 SOP 铁律登记 CLAUDE §5**（用户定，已犯几次、浪费 token）：跑 case/reading/judge 前先读 new_case_guide 走单一 `flow`、**禁手搓判卷**（score_vs_gt〔含平面+立面〕/grade/render/attempts 由 flow 自动出，别手动调 elevation_score/score_reading_vs_gt 造轮子）、禁抄近道、非 Claude 模型经 codex CLI 时 prompt 走 stdin（`-i` 吞尾随 prompt）。③**Fable5 期文档对齐**（Opus 出 brief → Codex 施工纯文档，无代码改动）：new_case_guide/CLAUDE/contracts/judge_grade_model/capability 对齐 Fable5 07-06/07/08 代码改动（旧渲染件名→新名·C2 v2 契约〔schema_version/Cell.polygon/capability_profile〕·判卷 polygon 未定义行为现状·测试数→562·栅格 10mm·附录A codex 隔离段）；**codex 顺带抓 3 个代码接线不一致记 backlog**（judge_rubric vs `_render_stage` 产物名 / `collect_eyeball_assets` 漏收 `zones_<floor>.png`＝真 bug / correction.yaml 注释残留）。审轨 `logs/reviews/request/2026-07-08_fable5_doc_alignment_brief.md`。**流程教训**：交叉测试一开始参照旧 run 手搓判卷造轮子（浪费 token+产物不规范），走 flow 才规范——正是本轮 SOP 铁律登记的缘起。

> ✅ **污染硬隔离机制化 + C2 B1 Cell.polygon + 判卷框架修 W1–W6（2026-07-08，Fable5 主控/Codex 双审执行·Opus 接手独立复审+commit `df6f249`，517→562 绿 + 9 xfail·未 push）**：三条独立线。①**污染硬隔离机制化**（Fable5 大审遗留 A1-3 / Top 风险 #2 之一关闭）=新 `src/agent/execution/isolation.py` + `isolation_templates/{guard.py,run_cv_probe.py}` + `scripts/tool_scripts/spawn_isolated_reader.py`：clean-room staging（repo 外·白名单拷贝 case_data+0_reading skill〔跳 judge_rubric.md〕+cv_toolbox+prescan+kickoff）+ headless settings + PreToolUse guard（stdlib-only·结构化 Bash allowlist 仅放行 `python tools/run_cv_probe.py --request <staging内json>`+少量只读命令·deny repo/gt/attempts/verdict/grade/复合shell/`python -c`/绝对路径/symlink 逃逸）+ merge 串行原子（attempt 碰撞重试·provenance hash 纳入 `input_hashes`·MANIFEST/settings/access_log 归档进 attempt）。**Codex 双审 APPROVE-WITH-CHANGES（5 MAJOR：settings 默认拒绝语义 / Read-deny 不拦子进程读文件→结构化 allowlist / cv_probe 平铺布局 import 冲突 / merge 并发未定义 / resume 上下文污染 —— 全采纳）** + 真对抗 `claude -p --settings` 冒烟（抓修 guard 对 Claude Code 信封 `transcript_path` 字段误杀=词法/路径检查只作用于 `tool_input`）。老 prompt 级隔离废弃、new_case_guide 附录 A 改隔离协议。`tests/test_isolation.py` 22 测。②**C2 B1 `Cell.polygon`**（schema v2 + `orthogonal_polygon` profile）+两 case 实战：sm24 走廊做成 8 顶点 C 形单 polygon 区（关闭 [[sm24-nonsquare-first-run-2026-06-24]]「L 走廊拆 2 区」缺陷 11→8 区）；新 `src/agent/correction/cell_geometry.py` 单一 polygon helper 贯穿 core/validator/modelling/judge；实战修 CW 绕向/闭环 ring 规范化进核（`normalized_ccw_polygon` 记 `POLYGON_WINDING_CCW`·delta0·gate① post-core 仍严格）、凹形墙法向 polygon 局部探针（`modelling._local_outward_normal`+`kernel._normals` 弃全局质心）、harness 状态缺陷（`_load_snapped`/viewer manifest-first 防 blocked draw 污染下游 + `--budget-draws` triage 旋钮）；一次 `_find_parent_wall` seam 过度修复被 B0 合同测试拦下并撤回（教训「别修警报、修触发源」）；correction prompt+A0 钉死「一房一 cell」（修正 batch 措辞致 polygon dead-letter）；envelope reconcile 遇 polygon cell 安全跳过（记 unsupported 不动 bbox 边）。③**判卷框架修 W1–W6**（用户报「外包缩一圈」）：W1 judge-off 也渲染 correction·W2 correction 渲染对齐 reading（per-floor plan+per-facade elev+roles）·W3 凹多边形 viewer 耳切·W4 结构栅格 0.05→0.01（保住 0.12 中心线真值·A0 SNAP_GRID 同步·AXIS_JITTER_TOL 澄清为聚类容差）·W5 gt `wall_thickness_m:0.24` 边界 centerline→outer-skin 换算（内墙轴线不动·窗不变）·W6 sm21 07-02 read-only 重批墙4/4·5/5·平面窗全中·立面窗 15/15。**Opus 接手独立大节点复审=通过**（自跑 pytest 562 + 逐行 diff + 关键正确性点逐一核实：manifest-first 防污染/`_geom_signature` 加 polygon 顶点/normals 局部探针符号/envelope 对 polygon 跳过/axis_name 修复）。**新排队（用户拍）**：尺寸基准+墙厚设计轮（方向 ratify [[wall-thickness-dimension-basis-direction]]，`proposals/dimension_basis_and_wall_thickness_direction.md`，排 C2 B4 附近·动手前正式设计文档过 Codex 双审）/ sm24 correction 改错好 reading 登记（无 gt 待补录对账）。审轨 `logs/reviews/{request,verdict,execution}/2026-07-08_*`。

> ✅ **CV 工具箱北极星判决性实验=阳性满分 + E 效率批 + sm24 泛化探针（2026-07-07，Fable5 主控/Codex 双审，commit `891356d`，510→517 绿）**：①**sm21 判决性实验阳性**（`run_2026-07-07_haiku_cv_retest`，J0 judge_pass 入账）：Haiku 4.5+CV 工具箱=与 Sonnet 5 基线**逐项相同满分**（墙9/9·平面窗7/7·立面窗15/15·过度分割0·0.0m·boundary 8/8）vs 07-05 无工具箱同模型对照全崩（0/9·0/7·0/15·+9）——**「量而非看」=弱 VLM 关键杠杆坐实**（核心机理=失败模式从「看错」〔感知，救不了〕迁移为「量了不筛/锚错」〔流程，纪律可托〕）。三限定 provenance（工具箱指令要求使用非自发/需 pilot 打回一轮/prompt 级隔离）。**改写既有「模型能力主导」结论适用域**（精化为「prose 脚手架托不起、含 CV 工具箱未测」→本轮已测=阳性，[[haiku-downgrade-model-is-lever]]）。②**sm24 泛化探针 5/5**（`run_2026-07-07_haiku_cv_probe`，reading-only 无 gt）：非方形对行列投影无新难度·无标注构件=标定后像素直测正解·弱 VLM 稳定短板=首抽散漫+schema 写作错（→Phase B 双通道）。③**OCR 数据驱动裁定=维持 Phase C 不提级**（Haiku 读数无错；触发器=交叉测试暴露标定/读数失败）。④**E 效率批**（Codex 审 APPROVE-WITH-CHANGES 6 findings 全采纳）：E1 纪律固化进 cv_toolbox.md（自声明 clean-CAD required）/ E2 prescan-plan/-elevation 宏工具（有界真实线段·中性命名 `line_band_candidate`·capability_profile 声明·advisory-only 无 gate 消费）/ E3 预扫前置化 SOP（用户授权修订：确定性预扫挪编排侧 spawn 前跑·语义判定权完整留 VLM）/ E4 OCR=方案a。顺带修 M1 引入的 pipeline.py import 回归（`compute_evidence_debt_from_vector_dir` 漏引→真实 run 进 correction 即 NameError·509 绿未盖·一行修+回归测试 `test_pipeline_evidence_debt_import.py`）。审轨 `logs/reviews/{request,verdict,execution}/2026-07-07_reading_cv_efficiency_*` + 实验 `logs/experiments/2026-07-07_haiku_cv_retest/`。**下一场（用户拍）= GPT-5.4-mini 弱模型交叉测试**（迁移性验证+省额度·Opus 主控盯 Codex·交接单 HANDOFF_gpt54mini_crosstest.md）。

> ✅ **Fable5 项目大审 + 审计修复 M1–M4 + CV 工具箱 C0/C1 + C2 设计定稿/B0 + facade 接线（2026-07-06，Fable5 主控/Codex 双审，commits `fea6981`/`2661fd4`/`41f842d`/`e3ec9ae`/`045caae`/`c8abb8b`/`802822f`/`be23d12`，468→509 绿）**：①**Fable5 六路取证大审**（报告 `logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md`，390 行）：A 诊断（架构 A1-1~5 / 端到端工程 A2 parity 表 / 迁移完整性第四路复现 GO）+ B 未来（B1 C2/C3/C4 逐阶段升级矩阵〔**补判卷+gt 两条同步升级线**〕/ B2 CV=Phase B 算术下沉载体裁决·sidecar 先行双通道随后·工具放执行侧·Haiku 当验收模型 / B3 再拓扑纳入 stage 1.5）+ C/D 补充自查。**Top 10 风险 + 9 处挑战既有结论**（最重：0_reading 生产路径 6/15 投影缺口·S5 死门·schema_version 是纸面承诺·**判卷层零 capability 感知=非矩形未定义行为**·win_tol 死参数·「脚手架托不起弱VLM」精化为「prose 脚手架」·世界落位仍 LLM prose 掷骰子）。②**修复 M1–M4**（468→489）：M1 口径收口（run_pipeline 内联完整 S0 `check_reading_view`+S5 `check_assembly` 接分档门+`test_check_parity.py` parity 锁）/ M2 三道门+依赖卫生（`DIMCHAIN_CLOSE_TOL_M` 50→10mm 对齐 A0+`mep.construction_thermal_mass`+`mep.hvac_schedule_refs`+pyproject 补 ezdxf/dotenv/openai/attrs·删残缺 `.venv`）/ M3 provenance 自动采集（baseline.json 顶层 provenance=git_sha/dirty/skill 哈希·无时间戳保幂等）/ M4 测试补丁。③**CV 工具箱 C0+C1**（`e3ec9ae`→事后 Codex 对抗审 3 MAJOR+2 MINOR 全修 `045caae`，489→500）：`src/agent/reading/cv_toolbox/` 6 确定性工具 + `cv_probe.py` CLI + `cv_evidence/` sidecar（cv_schema=1·append-only·**预留 Phase B anchor_px/visual/metric 槽位**）+ skill 文档。④**C2 设计定稿+B0**（`c8abb8b` `proposals/c2_orthogonal_polygon_design.md` B0-B6 批次序→`802822f` B0，500→505）=schema_version 真机制（缺省"1"+gate① 拒绝静默降级）+capability_profile 线程化内核全入口（`geometry/capability.py`）+parent-wall 唯一归属+覆盖门 helper 收敛（`geometry/adjacency.py`）。⑤**facade frame 接线**（`be23d12`，505→509）：`derive_facade_frame`（原零调用）接成 gate① `correction.facade_frame_cross_check`（CROSS_CHECK flag-only·确定性 vs LLM 落位·sm21 权威 run 15 窗 0 flag·per-segment 留 B5）。**体检遗留待拍板**（部分已消化）：污染硬隔离（07-08 已做✅）/ INVARIANT 全档硬 raise（政策）/ check registry 全量重构（parity 锁降紧迫度）/ 判卷 §8b segment 模型（C2 硬前置）/ 盲抽真端到端测试。

> ✅ **logs 全量重排（纯过程痕迹）+ Haiku 4.5 降级测试 + Fable5 大审交接备妥（2026-07-05，commits `15ecfd1`/`860e346`/`b25a12e`）**：①**logs 重排**——`logs/` 收敛为纯过程痕迹（`reviews/{request,verdict,execution}` + `experiments/` + `renders/`〔gitignored〕+ 唯一活记录 `downstream_agent_changes.md`），纪律锁 `logs/README.md`；活文档抽离（判卷 spec→`architecture/judge_grade_model.md`·role phase-2/J23→`proposals/`）；130 tracked `git mv` 保 history、零死链。②**Haiku 4.5 降级测试**（`run_2026-07-05_haiku_downgrade`，停 J0·未推下游）= 单变量 A/B（同完全恢复脚手架+同 case+同判卷尺+冷启隔离，唯一变量 reading 模型）：Haiku 平面墙 0/9·平面窗 0/7·过度分割+9·立面窗 0/15·四立面 ambiguous vs Sonnet 5 = 9/9·7/7·15/15·0.0m。**当时裁决「模型能力主导」；⚠️07-07 被 CV 工具箱实验改写适用域=prose 脚手架托不起、含工具箱=满分**（[[haiku-downgrade-model-is-lever]]）。③**Fable5 大审交接备妥**（`CHECKLIST.md`+`codex_cv_plan.md`）。跑前教训=又跳过 SOP 用户确认点被纠正（memory `pre-run-config-confirmation`）。

> ✅ **判卷可视化统一模型重构（2026-07-03/04，`7.03`/`7.04` 批次，SCORER_SCHEMA 2→7，437→468 绿，收工 push）**：把立面判卷+平面判卷改造成一套 diff 模型（权威 spec `architecture/judge_grade_model.md`）。缘起=旧判卷只判平面窗（次要源）、假立面 panel 借 gt 装饰、竖向/长度是盲区（墙画一半长/窗画宽一倍照样满分、违「产品不借 gt」）。**统一模型**：gt 全画灰底→产品按真实坐标如实叠、几何绝不借 gt（红线）→只给产品上色（绿完全命中/橙容差半透明带/红没对上）；平面墙窗=piece-level interval-set 双轴（横向关联+纵向长度集合差）；立面窗=两侧覆盖率 `min(gt_cov,product_cov)`（堵 min-area bug·A1 翻转归一 aligned/flipped/ambiguous）；屋顶/地面/楼板横线判定+立面竖边界修映射。容差进逐 run `grade:` 段（reading/correction 两把独立尺·correction gt-盲故 reading 是准确度真闸门别更松）。新 `src/agent/judge/elevation_score.py`；红线全程守住（`test_gt_discipline` 绿）。方案审 10 findings 全采纳（抓真 bug：立面重合率用「交集/min面积」会误判 complete）。**数据诚实教训**：S7「竖向读错」动机例——核 gt 只看 entry 默认没看 per-opening→编了个不存在的错（真相 reader 全读对），坐实判卷盲区正是我栽的坑本身。**backlog（§8b）**：墙元素粒度（`7.04_GradeBacklogWallGranularity`：穿走廊墙切两段随下段整道染橙）/立面窗移位vs变尺寸/Hungarian/ambiguous config 化/非方形 segment。

> ✅ **规范跑测流程 P1 首跑（sm21 flow e2e）+ 流程清理批次（2026-07-03，`7.03_FlowCleanupBatch1/2`+`BoundaryGrading`，410→437 绿，收工 push）**：①**sm21 正规重跑**（`run_2026-07-02_sonnet_flow_e2e`）= flow P1 首次真实 run 端到端 = **全链路 CLEAN**（三层叠加门逐段全走通·gate① 0 block·EP 0 severe/6 warn·14区/100面/15窗）。reading=冷启 Sonnet 5（非 4.6）墙9/9·窗15/15·过度分割0·全 0.0m 超 sm21_pre 地板（**⚠️归因混杂：15/15 很可能主因 4.6→5、非脚手架恢复·n=1·踩 [[run-provenance-recording-requirement]]**）。**reading forensics**（用户观察坐实）=子代理自发写经典 CV（PIL 灰度投影+px↔m 标定+scipy 连通域·0.0m 来自「量」非「看」）→立 `capability/reading_improvement_methodology.md`（reading 提升唯一管理文档）。抓 flow P1 首个真 bug F1（judge packet 首 pass gt-evidence 全空·manifest 时序·已修）。②**流程清理**（用户 5 点反馈·8 findings Codex 审全采纳）：`run_config.yaml` 五段·结构化 `baseline.models`（reading 钉死）·per-attempt 全渲染+promote·overlay→`render_grade.py` gt 批卷（sidecar-driven·颜色=判定·类别=画法·边界 footprint 四边判定）·F1 修。

> ✅ **规范跑测流程 P1 全落地（2026-07-02，`7.02_FlowP1BatchA/B/C`，commits `36f380a`/`d9fe131`/`f2772f6`，395→410 绿 + 9 strict xfail 不变、零 golden、未 push）**：把终审 GO 的 §8 P1 落到代码（缘起=2026-07-01 sm21 双 Sonnet run 抄近道跳过 judge②/attempts/3D/report → 根因=无单一 anchor-aware 编排命令、正规流程碎成 ~15 命令）。**流程严守协作规约**：Claude 出[执行简报](logs/reviews/request/2026-07-02_flow_p1_execution_brief.md)→Codex 审 **APPROVE-WITH-CHANGES（6 findings）**→Claude 裁决 **6 条全采纳**回改简报〔MAJOR-1 scorer/overlay 绑 accepted attempt+校验 output_hash·MAJOR-2 `--from auto` manifest-first·MAJOR-3 run-scoped LLM 配置+抽共享 intake loader·MAJOR-4 correction floor 映射·MINOR-1 JUDGE_BLOCK 兜底·MINOR-2/3 软降级+`mark_review_approved`〕→Codex 分两批执行→Claude **大节点全面审**（逐行 diff + 独立自跑全量 pytest + record_baseline 签名/correction schema 核）。①**Batch A harness**：单一 `flow` verb（[run_stage.py](../scripts/tool_scripts/run_stage.py)，manifest-first 可续 + 三开关叠加〔`--judge stop/off`·`--review reading,correction`·`--geometry required/auto`〕+ JUDGE_BLOCK 自动盲重抽 stochastic 根 + 下游 invalidate + geometry-auto 审计字段〔actor=flow:auto/policy=auto〕+ 退出码 0/10/20/30 + Batch B 缺失软降级）+ `approve-review` verb + durable 人工校验（新 [execution/review.py](../src/agent/execution/review.py)，`HumanReviewApproval` 绑 accepted `output_hash`、resample 即失效 fail-closed）+ `StepStatus.AWAITING_HUMAN_REVIEW`+`mark_review_approved` + **EP 布局修 option A**（[runner.py](../src/agent/runner.py) 抽共享 `run_downstream_ep`/`load_intake_from`，`run_full_pipeline` 改调它行为保真、EP 无论入口落 `<run>/EP/EP_run/`）+ `cmd_resample` 补 invalidate。②**Batch B gt evidence**：`score_*_vs_gt` 接进 judge_packet 当机读 evidence（**从 accepted attempt `output.json` 生成 + 校验 manifest `output_hash`、篡改 fail-closed raise**）+ 新 [judge/score_policy.py](../src/agent/judge/score_policy.py)（FloorScore→suggested criterion，**advisory-only、绝不写进 `StageVerdict`〔extra=forbid〕、不替 checklist**）+ 新 [judge/correction_score.py](../src/agent/judge/correction_score.py)（J1 correction scorer 吃 accepted `CorrectedGeometry`，floor 名映射 精确>数字序号>z_floor/序、未匹配写 evidence，真实 sm21 F1/F2 验过）+ 新 `_overlay_transform.py`+`render_overlay.py`（gt+产物共用同一 metric transform 画同一 canvas、非 raster 合成、centerline 偏移标容差说明）。③**Batch C**：[new_case_guide.md](guides/new_case_guide.md) 重写为新 SOP（6 步 + 三层叠加门 gate①→judge②→人工校验〔叠加非互斥〕+ gt 权威判卷〔对账为主判据·放宽容差·看图为辅·StageVerdict 仍裁决权威·score_criteria 仅 advisory〕+ overlay + `flow` 命令矩阵 + 退出码 + 3 人工校验开关↔reading(J0)/correction(J1)/geometry），Claude 亲手描述真工具不写 vaporware。**gt 隔离铁律未破**（score/overlay/policy 全 judge-side、validator/pipeline/execution/correction 无 gt import、`test_gt_discipline` 绿）；未动 gate①/judge/verdict 语义·run_pipeline·契约。**J23 几何 judge（P2）= 用户定 defer**（几何本就人工看 HTML viewer、J0/J1 过后 J23 多半主观"形态像不像"参考意义小；动工前提比 P1 侵入=reorder stage-3 门 §8.11#5 + `score_geometry_vs_gt` + sm24 gt）。**下一步 = sm21 正规重跑**（用新 `flow` 端到端验全流程；工具建好+单测过但还没在真实 run 上跑过）。审轨 `logs/reviews/{request/2026-07-02_flow_p1_execution_brief.md,verdict/2026-07-02_flow_p1_execution_brief_review.md,2026-07-02_flow_p1_batch_{a,b}_execution_log.md}`。

> ✅ **reading 脚手架恢复实测 + reading 演进方案 + Phase A 证据门硬化（2026-06-30，`6.30_ReadingEvidenceGateHardening`，测试 349→365 绿、golden 零差）**：本轮三段。①**实测**——冷启 2 个隔离 Sonnet 子代理用恢复后脚手架（`6.27_ReadingScaffoldFullRestore`）重读 sm21、`score_reading_vs_gt` 对账：r1 墙9/9·过度分割0·2f竖墙0.0m（**复现 sm21_pre 地板**）/ r2 墙9/9·过度分割+4·窗12/15。**结论=墙/结构稳达回归地板；过度分割+窗位仍 run 方差/模型主导、非 prose 能根治**（r1/r2 同脚手架同图一干净一+4）。产物 `logs/experiments/2026-06-30_reading_scaffold_restore_validation/`。②**reading 演进方案（用户发起）+ 三方诊断综合**——病根=**prose↔gate 执行落差**（reading docs 要双通道证据、schema/validator 把缺失/弱证据当 clean → correction 救场、"pipeline 绿"掩"reading 弱"）+ **算术在 VLM**（reading 纯尺寸链累加算坐标、像素 anchor 空着，违反 0-5"LLM 感知/代码算几何"；扒 attempt 坐实 r2 伪墙落窗 jamb 处 `prov=seen`）。关键澄清=对 VLM"按像素算"最不可靠，对立轴是**感知 vs 计算**非像素 vs 尺寸链；像素忠实正解是经典 CV 非逼 VLM。外部模型"可恢复性规则"（correction 能否从此错恢复→能则弱模型够/不能才上抽取器）+ Claude"闭合反转"（`dimension_chain_closure` 早写好、chain_id optional 被跳→强制即把 silent misread 变可检测，故**闭合门优先、OCR 暂不起**）。三档路线落 [capability/reading_improvement_methodology.md](capability/reading_improvement_methodology.md)（原 `proposals/reading_evolution_dual_channel_cv.md`，2026-07-03 折入 capability 统一管理并删原）：**A 证据门硬化（本轮）/ B 双通道+算术下沉（尺寸驱动重建·Shapely polygonize）/ C OCR+CV（DXF 数据工厂起手·用户定先不上 CV）**。Codex 独立架构回归审坐实变弱（4 BLOCKER，`logs/reviews/verdict/2026-06-30_reading_architecture_regression_review.md`）+ Phase A spec 审 APPROVE-WITH-CHANGES（1B/6M/3MINOR 全采纳）。③**Phase A 落地（两批，Codex 执行 / Claude 大节点全面审+冒烟）**：A1 链完整性闭合〔`(chain_id,axis)` 分组+overall/segment 完整+注明抓多数非全部〕/ A2 `dimension_derived⇒resolvable refs` 纯门不 mutate / A3 新 `RunPolicy.run_profile`〔exploratory|dev|golden|regression〕+ `EVIDENCE_CHECK_IDS` 机器可读 allowlist + 四信号串 validate_case→run_stage→record_baseline→report / A4 dimensioned 经 case manifest 声明〔新 `case_metadata.py`，不 import gt〕+ 强制 dimensions/P1a / A5 provenance legacy·partial 升 fail / A6 `partition_on_window_jamb` advisory〔**返修**：初版被 dim-position+both-join 双 guard 放过 r2 伪墙，去 guard 后抓 4 道〕/ A7 raw 字段存在性 sidecar〔absent≠[]〕/ A9 `score_reading_vs_gt --json-only` + sm21 phase1 floor 回归测试 / A10 facade.py East/West sign 翻正〔East+1/West−1 对齐 A1+gt-validated，test-first 锚 gt East-F2/West-F2、facade.py 仍未接线〕。**flag/block 裁定**=syntax 永 block / evidence exploratory=flag·golden=block / **legacy_migrated 祖父化**（2 个 legacy golden 不被打 block、待批次重录自愈）。**A8 defer**（触 correction 契约）。冒烟坐实门咬合：gpt54 空 dimensions→regression block、r2 伪墙→A6 flag。**未动 reading/correction schema 契约**。审轨 `logs/reviews/execution/2026-06-30_reading_phase_a_batch{1,2}_execution_log.md`。**残留**=Phase B/C + A8 跟批 + reading 1-5 修法。

> ✅ **audit→评测归因 baseline 侧收口（PR-A，2026-06-22，测试 297→300 绿、golden baseline 零字节差）**：同源欠债之一（§5.4）。`record_baseline` best-effort 读 `1_correction/corrections.json` → `baseline.json.corrections_summary`（counts by kind/rule_id/stage + capped corrections rows + **full conflicts/unsupported** + sidecar 状态）+ `RUN_REPORT.md` 新增 `## 校正审计（看错↔改错归因）` 节（conflicts/unsupported 在前）；**不动 gate flags/计数**（Codex Finding 6）。Codex 审 `APPROVE-WITH-CHANGES`（7 findings 全采纳 + **用户定 SPLIT**：PR-A 先行 / PR-B auto re-read 后做）。残留=gt-diff×corrections 机械 JOIN（N4）。**auto re-read（PR-B）经用户纠正**=主控 Agent 冷启隔离**子代理即 0_reading runner**（非 VLM-API-gated，我先前误判）、3 次不过终止、每步 judge 判定，与 0–5 一致；方案+交接协议已定（proposal §6 addendum：AWAITING_REREAD 非终止态 + RunPolicy.reading_runner_available 默认 False 向后兼容 + 子代理写 flat `0_reading/*_view.json` 再 `resample --force` 记 attempt + 预算线程化到 root 段 + 预声明 model/effort ladder），**PR-A + PR-B 均已落地**（PR-A commit `0c625fe`；PR-B 测试 300→307 绿、golden baseline 零差：`policy.reading_runner_available` 默认 False 向后兼容 + `AWAITING_REREAD` 非终止态 + `_verdict_outcome` 用 root 段算预算 + run_stage `--reading-runner-available` + 5 步盲重读协议打印 + routing/guide/rubric 同步；Codex `APPROVE-WITH-CHANGES` 7 findings 全采纳 + 大节点逐行审 + 抹平 guide tab）。方案+审 logs/reviews/{request/2026-06-22_audit_attribution_and_auto_reread_proposal.md,verdict/2026-06-22_audit_attribution_and_auto_reread_review.md}。

> ✅ **reading 诚实机制 + judge recoverability 路由（2026-06-22，`6.22_ReadingHonestJudgeRouting`，修 sm21 Sonnet 识图，测试 288→297 绿、golden baseline 零字节差）**：诊断 + 用户全程 ratify 的架构定调。根因=2026-06-07 founding 框架（trust-the-dim）**correction 半边早已落地**（`A3:28` `stroke_vs_dimension`→信尺寸链）、**reading 半边从没落进 0-5 schema**（Stroke 无 provenance、缺 stroke↔dimchain check、无双通道纪律/门≠窗负例、verdict 无 recoverability 轴）→ correction 仲裁机器**收不到冲突信号**。**D1-D5 总纲**：correction 永 image-blind 纯文本**不做 VLM**（开图=翻倍 VLM 要求/杀归因/饿死小模型监督/重引入信图>尺寸链 bug）；脚手架=降智机制（服务国产 VLM→本地开源北极星）；看图仲裁归 judge+重读、不进 correction 生成；who-fixes 判据=证据冗余在+不靠猜才放行 correction、证据销毁/身份错/漏元素→reading 中止；「EP/保险通过≠几何对」（DeepSeek 幽灵房 EP 绿）。**两战线修，correction(A1-A4+核)一行不动**：①**reading 诚实**=`Stroke` 加可选 `provenance/confidence/dimension_refs` + 落地承诺已久的 **stroke↔dimchain 一致性 CROSS_CHECK**（非阻塞 flag/10mm/perimeter 排除/中性 verify 措辞）+ `provenance_mode` 报告 + guide/pen/judge prose（双通道纪律/dim-tick≠wall/门≠窗/`provenance→A0` 映射 `seen≠direct_measurement`）；②**judge 两轴**=`CriterionVerdict.recoverability` + `blocking` 改 **J0-scoped**（J0 severe+`correction_recoverable` 才放行、J1 severe 永 block、缺省→block 向后兼容）+ J0 四条放行判据+默认中止 + `record_baseline._verdict_blocking` 改用 property + orchestrator pass-through 审计消息+计数 + J1 确认门归因。**关键：可选字段+CROSS_CHECK flag+verdict 向后兼容→不需重录 baseline**。**Codex 双审**（APPROVE-WITH-CHANGES，5 findings 全采纳：J0-scoped blocking / record_baseline 漂移 / 审计消息 / coincidence 10mm 中性 / provenance→grade 映射）+ **Claude 大节点全面审**（逐行 diff + 自跑 pytest 297 + 命门确认 `CROSS_CHECK FAIL=FLAG 非 BLOCK`，[checks/schema.py:106](../src/validator/checks/schema.py#L106)）。Component 2（持久化手动 0_reading prompt/模型）defer。**sm21 重跑验证**待与其他待改项（命名确定性化等）攒齐一次性跑。方案+审 logs/reviews/{request/2026-06-21_reading_honest_and_judge_routing_proposal.md,verdict/2026-06-21_reading_honest_and_judge_routing_review.md}。

> ✅ **几何确认 viewer 挪 manual_review（2026-06-21，commit `c029ef9`，测试 288 绿）**：`geometry_viewer.html` 从 `2_modelling/`（管线阶段输出）挪到独立 `<run>/manual_review/`（人工确认产物、后续接编辑回写 [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md)）。run_stage 输出改路 + 补 `roles=discover_roles(bg)`（此前该路未传 roles→白模型，现按房间类型着色）；record_baseline RUN_REPORT 文档 + .gitignore 路径模式同步；building_geometry.json 输入仍读 2_modelling、discover_roles 相对深度不变。冒烟确认（686KB 自包含、14 role 发现）+ pytest 288。

> ✅ **room role 向 0_reading 迁移 phase-1 + N2 关闭（2026-06-21，commit `04a02a8`，测试 281→288 绿）**：①**role phase-1**——room role 现由 `1_correction`(DeepSeek,**image-blind**)凭布局先验猜→判错(圆桌房→office)。reading 看得见图,role 该归它。本期收窄落地：reading 加**可选** `RoomRoleObservation`(`room_labels`,topology-light:role+anchor+label_text+basis,默认空→baseline/legacy 安全) + 共享 role 词表 `src/agent/roles.py`(CANONICAL_ROLES+ALIASES+normalize) + reading 校验(仅非空时;role/basis/id=INVARIANT、anchor-in-bounds=CROSS_CHECK 因 bounds 启发式) + correction prompt 把 room_labels 当**输入**且优先采用图像观测 role。**Cell 输出 schema 不变**(不加必填字段→不增 DeepSeek malformed 风险)。绑定仍 correction 隐式做(输入从盲先验升级为图像观测)。**Codex 三轮双审**(REWORK[确定性 anchor-in-cell 需 plan→world 一等变换、当前无]→Claude 降级 source-linkage→APPROVE-WITH-CHANGES[sidecar 不入主 JSON]→用户收窄 phase-1→APPROVE)+ 大节点全面审(代码+自跑 288+escalate anchor-bounds 降级修)。**phase-2 远期**(用户定"更精准修法缓做")=确定性绑定 sidecar+`role_source_label_id`+gate① provenance+plan→world 变换产物。设计全程 `logs/reviews/{request,verdict}/2026-06-21_role_*`。②**N2 关闭**——sm21 South 2F 窗 along-facade x "真 bug" 经诊断+自验=**不复现**(GPT54 产出 x=gt 完全一致),是 06-16 Opus 旧轮产物(那轮 correction 沿立面平移 -0.24m,疑墙厚补偿误加 along-facade 轴,降级 backlog)。③**命名确定性化**侦察完成(blast radius 极宽:全下游精确名+30+测试+baseline 字节相等重录;依赖 role 已就位)→列为下一项。未动 IntakeOutput 契约/run_pipeline/下游。

> ✅ **Claude 编排/Codex 执行协作规约 + P0#1 跨层概念墙对齐（2026-06-21，commits `ddbaa82`=代码 / `6.21_CodexExecutionProtocol`=文档，测试 277→281 绿）**：①**协作规约**（用户定）——Claude+Codex 两订阅各 5h 窗口，坚持 **Claude 主控**（保质量+记忆单一权威）、执行尽量派 Codex（推理算 Codex 额度、Claude 只花 spec+审 diff+读简报，省上下文+拉长每周期产能）。**审阅方向反转**（替代旧 §5#8「Codex 审 Claude」）：Claude 出方案 → Codex 审方案（落 logs/reviews/）→ Claude 裁决（**不盲从**）→ 派 Codex 执行器 → Claude 审结果（git diff + **自跑 pytest 兜底**）；方案类决策**双审**后再派。**本机沙箱硬坑实测**：Codex MCP 碰本地文件必须 `danger-full-access`（read-only/workspace-write 起 bwrap 失败→静默回退读 GitHub @main、行号不可信）；sandbox 建 thread 时定死、换权限须新开会话；看图走 CLI `codex exec -i`；默认 gpt-5.5/xhigh 宜高不宜低。操作手册 [guides/codex_execution_protocol.md](guides/codex_execution_protocol.md) + CLAUDE §5#8。②**P0#1 跨层墙对齐**（首个走新流程的修复）——根因修正：轴线图**本就全楼共享**，真因=同层/跨层共用 `axis_jitter_tol=0.05`、走廊跨层差恰 0.10m 卡容差缝（不聚类 + sliver `<0.10` 严格不并）→ 两轴幸存生碎面（非原记「各层独立 snap」）。修=`deterministic.py` 新增 `_reconcile_cross_floor`（per-floor identity[留全 raw]→footprint 硬锚→**mutual-nearest** 跨层匹配[图级冲突即 flag、不静默合]→provenance-aware sliver），新容差 `cross_floor_align_tol_m=0.11`。**sm21_anchor(GPT54) 112→100 面**、走廊两层对齐 y[3.15,4.85]、zones/windows 不变、4 条 cross_floor_align audit 可查。**Codex 双审**（REWORK[3 DISAGREE+2 BLOCKER：贪心误抢/provenance-blind sliver 反并/0.20 太激进抹真错位]→Claude 裁决采纳+校准[tol 0.20→0.11、flag 路由 unsupported→advisory]→`codex-reply` 二审 APPROVE-WITH-CHANGES 无 BLOCKER）+ **四重验证**（代码逐行审+自跑 pytest 281+新测非空+sm21 端到端）。审计轨迹 logs/reviews/{request,verdict}/2026-06-21_cross_floor_wall_alignment_*。未动契约/run_pipeline/下游。

> ✅ **管理文档重构 + 3D 查看器交互增强（2026-06-20，commits `b9f4919`/`3f9ed35`，测试 →277 绿）**：①**管理文档重构**（用户定 5 条方向）——三主文档职责互斥：CLAUDE.md（结构+当前状态+约定+索引，424→137 行）/ plan.md（活计划，近细远粗，523→80 行）/ **新建 decision_log.md**（历史决策唯一归档）；architecture/ 收敛为**单一当前架构文档** pipeline_stage_contracts.md，其余 git mv 到 **archive/**（历史架构+已实现工程计划+已 close 的 handoff）/ **capability/**（全流程能力升级）/ **新建 proposals/**（未落地方案：geometry_first_zonification / editable_geometry_confirmation / cad_to_gt）；活文档链接改向 + 口径通扫；test_baseline index/README 同步；**新增硬纪律 CLAUDE §5#1 = memory↔管理文档同步**（换主控模型不丢信息）+ §5#5 skill 库 clean-spec 政策。Codex MCP 直审 CHANGES REQUESTED（1M+2L）→全修→CLOSEABLE。②**3D 查看器交互增强**（`render_geometry_viewer.py`，逐条用户眼检通过）——zone 模式按**房间类型**固定色着色（ROLE_COLORS ~25 类型，复用 render_gt 调色板，role 从 1_correction/correction_geometry.json 取）+ 色块→类型图例；surface 改 flat 材质（整 zone 统一色、顶面不再 washout）；选中信息分行带标题 kv；edge 选中改整条粗管高亮 + 高亮件强制最上层；**拾取跟随墙透明度**（opaque=遮挡判定只点最前可见、调低透明度才穿透到后面）。

> ✅ **CAD→gt 满配答案方向 + gt 渲染核验 + East-West 窗高修复（2026-06-20，commits `a10f00a`→`41558e1` 共 6 个）**：①**CAD→gt 提取**——用天正 CAD（DXF）机器级精确抽几何自动生成满配 gt（含精确窗 along-facade x），替代人读 PNG 的妥协（人读窗 x 不准、故意不写）。前置工具链落地（ezdxf + proxy-graphics 解码 + `inspect_dxf.py` + `gt_from_dxf` 提取器 + 跨源 overlay 核验）；方向方案见 [proposals/cad_to_gt_extraction_plan.md](proposals/cad_to_gt_extraction_plan.md)（设计待审，过 Codex 审）。一鱼两吃=未来 CAD 矢量输入模态种子。②**gt 渲染核验**——`scripts/tool_scripts/render_gt.py` 出带尺寸标注的平面图+立面图（区块按 role 填色、footprint 分带尺寸链、立面窗按 [sill,head] z 框出+计数），人对照原图核**布局意图**不核 mm；gt 改逐 case bundle `gt/<case>/{gt.json,source.dxf,renders/}`。③**East-West 窗高 + 渲染一致性修复**。测试 →**274 绿**（新增 test_gt_from_dxf/test_gt_overlay/test_gt_render/test_inspect_dxf/test_merge 等）。**残留**：sm21 South 2F 窗 along-facade x 仍是真 bug（待核 1_correction）。

> ✅ **逐段 judge-in-the-loop 编排（sm21 待办#1）+ 离线交互式 3D 几何检视（#3）+ Codex MCP 直审工作流（2026-06-19，commit `525091b`，全部 Codex CLOSEABLE，测试 253 绿）**：①**#1 逐段编排**——把"整链跑完再事后 judge"换成**逐段阻塞循环**：新增 [`src/agent/execution/step_orchestrator.py`](../src/agent/execution/step_orchestrator.py)（`run_one_stage`=draw+gate①+段内盲重抽≤预算→停在 awaiting_judge/deterministic_pass/awaiting_geometry_approval/quarantined；`submit_verdict` 按 **verdict.root_stage** 路由[manual→human_redraw / deterministic→交人 / stochastic→resample]；`approve_geometry`/`geometry_is_approved`/`update_state`+`orchestration_state.json`）+ 逐段 CLI [`scripts/tool_scripts/run_stage.py`](../scripts/tool_scripts/run_stage.py)（verbs run/judge/resample/approve-geometry/status，接真执行器+gate①+渲染+judge packet+**几何阻塞门**：未 approve 时 4_mep 直接拒跑）。纪律：盲重抽不回灌 judge 评语、per-stage 预算**磁盘派生**(≤3 共用井)、语义坏 correction draw 走外层 gate① 计数落盘(非内层静默重试)。②**#3 离线 3D 检视**——新增 [`render_geometry_viewer.py`](../scripts/tool_scripts/render_geometry_viewer.py) 出**自包含离线** `geometry_viewer.html`（vendor three.js r0.137.5 内联、几何内嵌经 `_js_embed` 防 script breakout、双击即用）：orbit/缩放 + 墙体半透明 + X/Y/Z 截面 + 爆炸 + **select by floor/zone/surface/edge → 出 面积/体积/长度** + CAD 式顶点吸附持续测距 + 点选高亮 + 指北针/轴标注；z-fighting 不删面解决；接进几何检查点（GLB 从主流程剥离、`render_building_3d.py` 留作工具）。③**Codex MCP 直审工作流**（§6 #14 变体）：经 `mcp__codex__codex`(`danger-full-access`,用户授权) 自主读文件+跑 pytest 审，findings 内联回我、我**落盘** `logs/reviews/{request,verdict}/2026-06-19_*`；#1 与 #3(两轮)均 CHANGES REQUESTED→逐条修→re-verify **CLOSEABLE**。④**可编辑几何确认环节**愿景另落 [proposals/editable_geometry_confirmation.md](proposals/editable_geometry_confirmation.md)（DEFERRED,先讨论）。测试 204→**253 绿**;`geometry_viewer.html` 已 gitignore(可重生成)。

> ✅ **新 baseline 方案 + 主 Agent 操作手册（2026-06-16，commits `9688d4a`→`30d7907`）**：定下 dev 期运行模型——**主控 Agent（对话里 Opus/GPT5.5）当编排器 + judge②**，各阶段执行器用独立 API/冷启子 Agent 隔离跑（不污染输入），跑完给用户**人读总反馈 + 🔍 肉视检验清单**；0_reading 接 VLM 后再一键化。①**老 baseline 全挪 backup**（`test_baseline/runs/` 9 个 → `backup/tests_history/test_baseline_runs/`），`test_baseline/` 重构为**方案说明 + baseline 注册表**（[index.md](../case_tests/test_baseline/index.md)）——baseline 改为**自包含在 anchor 内**（gate① `*_checks.json` + `attempts/NNN/{output,checks,judge}` append-only + `baseline.json` 成绩单 + `RUN_REPORT.md` 人读反馈）。②**工具**：`src/agent/execution/orchestrate.py` + `scripts/tool_scripts/record_baseline.py`。③**手册**：[new_case_guide.md](guides/new_case_guide.md) 重写为「主 Agent 编排器+judge② 操作手册」。④**两条用户定原则 + gt 参考答案**：**初始 case = 最小**（只 `case_data/` + `llm.yaml`，1–5/EP 跑中建、绝不预搭空骨架）；**参考答案 gt** 放 [`case_tests/test_baseline/gt/<case>/gt.json`](../case_tests/test_baseline/gt)（**只 gate② judge 经 `src/agent/judge/gt.py:load_gt` 读，gate①/执行器绝不 import**）；建 **sm21_anchor gt** 并 **verified**。⑤**per-run 自包含布局 + 精确坐标判责**：**case = 纯素材**；**每次跑 = 自包含 `<case>/run_<注释>/`**；**精确坐标容差带由确定性层判**（核坍缩成规范值 + gate① 带容差不变量 + 交叉核对软 flag；gt rect_m 是布局意图±墙厚故意不精确，judge 只判布局/计数/窗位定性）。sm21_anchor 首份自包含 baseline 入库（opus-4.8 编排：14 区/100 面/15 窗，对 gt 逐立面命中，gate① 全绿，EP 0 severe）。测试 →**213 绿**。

> ✅ **0–5 校验架构 M0–M4 一轮全落地（2026-06-15，commits `06d01a0`→`83e94ed`，测试 103→204 全绿）**：按施工方案 **M0→M1→M2a/b/c→M3→M4** 全部开工完成。①**M0 执行/审计地基**：`src/validator/checks/schema.py`（CheckReport v2，`disposition()` policy≠fact）+ `src/agent/execution/`（manifest append-only + 内容寻址 hash / stage_runner / 失效 DAG / resume / RunBudget / approval digest / routing 失败分类）。②**M1**：`src/agent/reading/`（P1a dimension chain + P1b facade image-local schema + legacy 迁移）+ `src/validator/idf_fragments.py`（统一 eppy parser）。③**M2 逐段确定性 check**：`checks/{reading,correction,kernel,mep,assembly}.py` + `correction/{geometry_validator,facade}.py`——矩形 coverage completeness block + MEP 引用图+对象语义 + S5 backstop 归因 owner=4 + EP end 断言；视觉件 `render_elevation_windows.py`+`render_building_3d.py`；真坏 fixture × 4。④**M3 judge harness**：verdict schema v2 + `retry_stage_draw` 单阶段盲抽（两入口不串线）+ J0/J1 rubric + J4 disabled stub。⑤**M4 capstone**：`validate_case` 非侵入式跑全段 gate①。**纪律全守**：未动 `IntakeOutput` 契约 / 未动 `run_pipeline` / 未动下游 9 subagent。**Codex 实现审阅三轮闭环**（CHANGES REQUESTED ×2 → CLOSEABLE）：抽 building_geometry 序列化为单一真源、validate_case 对账磁盘 2/3 产物、digest 仅一致后算、zone_closure 遍历声明 zone。

> ✅ **sm20_anchor 端到端首跑 + 0–5「逐阶段输入·输出·校验」架构设计 + Codex 三轮审阅闭环（2026-06-15，纯文档/设计）**：跑 sm20_anchor（Sonnet 重识图）**19 区(7/8/4)/135 面/16 窗、三门 0 issue、EP Completed 0 severe**；过程发现 **2f 识图把整通走廊误切 4 段**（用户肉眼抓、我渲图漏），但 1_correction 靠 testdata+尺寸链**静默修对**——**识图错全程无门逮住** → 系统化设计 0–5 逐段校验门（落 [pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md) v8 + [archive/pipeline_validation_build_plan.md](archive/pipeline_validation_build_plan.md) v3 施工方案）：每段**两道门**（①确定性自校验→`*_checks.json`，②LLM/VLM judge 结构化清单非数字分）；**失败分类**（确定性后置 fail-closed 不弹上游 / 只 stochastic 0/1/4 盲重抽 / 0=manual→human_redraw / judge 评语不注入 prompt）；2/3 确定性靶子 + **交互 3D 查看器=上线保留的用户几何确认门**；judge=开发期数据工厂→上线撤。Codex 设计+施工双 CHANGES REQUESTED → re-verify → CLOSEABLE（关键纠正=确定性判坏不弹上游、加 M0 执行/审计地基、facade 仅 image-local·world 落位归 correction）。

> ✅ **仓库整理 + Codex review 闭环 + 标准 case 布局落地（2026-06-14，commits `7494253`→`8e3b1a8` 共 8 个，测试 99→103）**：①**仓库结构整理**——脚本合并 `scripts/`(总启动) + `scripts/tool_scripts/`(子操作) + `tests_scripts/`(开发脚本)；根 history 备份归并 `backup/{Skill,src,MCP,scripts}_history/`；`test_data/` → **`case_tests/{0_reading_tests, e2e_tests, test_baseline}`** + 旧单步语料归档 `backup/tests_history/SmallOffice`。②**Codex「phase→0–5 阶段名清理」review 闭环**（6 findings 全修）：M1 代码硬伤（`pipeline.py:_section()` 严格化：`intake_correction` 缺失 raise 不再静默落 `default`）/ M2-M4 活文档全改 0–5 当前接线。③**标准 case 组织结构定调**：`<case>/{llm.yaml(根), case_data/(素材), 0_reading…5_intakeoutput/, EP/(IDF)→EP/EP_run/(仿真)}`；建参考 case **`sm20_anchor`**；**代码路由接通**（`SimContext.ep_run_subdir` opt-in、testdata 读 case_data）。

> ✅ **0–5 完整体检 + 硬伤当日全修 + 复杂度路径骨架（2026-06-11，Fable 5，commits `b530a8a`/`49c3fea`/`4df069e`/`35aa185`/`696e2c2`/`58627cd`，测试 69→99）**：**sm21 + sm20（3 层新架构首验）双端到端一把过**（两门 0 issue / EP 0 severe / 誊写保真 100% / 切配覆盖手算 0 洞），落 **4H/3M/3L 硬伤当日全修**：H1 重复 cell id 守卫 / H2 z-stack 连续性 / H3 EP 退出码闭环（fatal 不再误报 success）/ **H4 窗朝向匹配** / M1-M3 / L1-L3。**三层防线**：draw 级复合校验→确定性核修复/显式丢弃→内核 raise backstop。另起 [0–3 复杂度升级路径骨架](capability/pipeline_0-5_capability_upgrade_suggestions.md)（C2 正交多边形+多平面立面 → C3 退台/挑空 → C4 斜交墙）。

> ✅ **0–5 阶段重构完成（2026-06-09→06-10，Step 1–8，commits `29845ea`…`3577…`）**：管线重构为 **0–5 阶段架构**。几何彻底确定性化（内核造面+切配→序列化 surface_specs，fork a 下游誊写），phase2b 解耦成 4_MEP(LLM 物理)+5_intakeoutput(确定性装配)，`IntakeOutput` 契约不变。**Step 8 e2e（干净 sm21）**：确定性几何 InterZone 门 0 issue + 4_MEP 契约 0 issue + 下游忠实誊写 100 面 + 装配 IDF 门 0 pair_issues（对照旧 staged 12–26 issue）。详见 §B.5.11 + [archive/2026-06-09_pipeline_0-5_refactor_handoff.md](archive/2026-06-09_pipeline_0-5_refactor_handoff.md)。

> ✅ **EP 跑通 + 两个真因修复 + B 结案（2026-06-10，commits `04e7dbe`/`fd3d4bf`/`5e2f881`）**：之前"EP 段错=环境"是**误判**。真因①不完整 `Schedule:Compact`（漏 `AllOtherDays`）→ 容器 EP 25.1.0 段错 → 加**确定性 schedule 门**（[src/validator/schedules.py](../src/validator/schedules.py)）+ authoring 硬化。真因② sm21 "0 窗" **不是内核 bug** = **1_correction (DeepSeek) 偶发抽风**（漏窗/非法 JSON）→ `_call_json_llm` 加重试 + 窗完整性自检。**实证**：sm21 14 区/100 面/**15 窗**/两门 0 issue/EP Completed 0 severe；sm23（单层 9 区 11 窗）EP 干净跑通。

---

## B. 关键决策详档（§5.1–5.13）

> 历史细节（sm_0..16 baseline / token 优化 P0 全过程 / Claude Code harness 切换 / sm_13/14/15/16 输入规格演进）已沉淀在各专题文档 + `backup/tests_history/test_baseline_runs/` + git log。本节保留**对当前架构仍有约束力**的决策（其摘要在 CLAUDE.md §1）。

### 5.1 几何 / MEP 阶段拆分（2026-04-25, sm_15）
IDF 建模拆「几何阶段」+「MEP 阶段」，独立会话可由不同模型执行；占位 construction：`Default_Ext_Wall` / `Default_Int_Wall` / `Default_Window`。**全局唯一世界坐标系**：原点 = 整栋投影最大边界 SW 内角，禁止每层本地原点。

### 5.2 协作者侧 LangSmith trace 解码（2026-05-05）
`20260414_192502/` 共 335 个 run JSON。锁定 10 节点 LangGraph 拓扑（intake → schedule → material → construction → zone → surface → fenestration → lights → people → hvac）+ 子 ReAct 节点。每个 subagent 输入合同：「主任务 specs + 下游 specs（reference only）」。本项目侧职责真正边界 = **产 IntakeOutput Pydantic（不产 epJSON）**。

### 5.3 半人工工作流固化 + A2 多 LLM 配置（2026-05-06）

**A. IntakeOutput schema drift 验证 PASS**
- 协作者 trace 与本地 [state.py:23](../src/agent/state.py#L23) + [validator/data_model.py BuildingSchema/SiteLocationSchema](../src/validator/data_model.py) 逐字段对账：top-level 11 字段 / BuildingSchema 8 字段 / SiteLocationSchema 5 字段，**全部一致**

**B. DeepSeek V4 pro 文本通路 capability test PASS**
- HARD_USER_INPUT（5 层办公楼 + 中庭，1953 字符）→ 49k completion / 11 字段齐 / Pydantic PASS / 0 命名违规 / 跨字段引用 100% 一致
- 软风险：DeepSeek 用 `Floor_N_*` 模板写法（协作者是逐个枚举）→ 已在 [new_case_guide.md §4.2](guides/new_case_guide.md) Step 4 prompt 加硬约束补丁
- artifacts：[../case_tests/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake](../case_tests/test_baseline/runs/2026-05-06_capability_deepseek_v4pro_intake)

**C. A2 多 section LLM 配置已实施**
- [llm.yaml](../src/configs/llm.yaml) 拆 `default`（DeepSeek V4 pro）+ `intake`（Claude Opus 4.7）
- [llm.py:create_llm(node_name)](../src/agent/llm.py) 路由；back-compat 旧 flat 格式
- [intake.py:158](../src/agent/nodes/intake.py#L158) 加 short-circuit（`state.intake_output is not None` → 跳 LLM 调用）让 `--intake-from` 半人工流可用
- env vars：`DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY`（[`.env.example`](../.env.example)）

**D. 半人工工作流固化**
- [guides/new_case_guide.md](guides/new_case_guide.md) 重写（旧版备份 [logs/backup/new_case_guide.md.bak_2026-05-06](logs/backup/new_case_guide.md.bak_2026-05-06)）
- [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py) 三种入口（`<case>` 全自动 / `--intake-from` 半人工 / `--intake-only` 调试）

**E. 实验日志归档目录迁移**
- 旧 `AI_agent/experiments/` 全空已废
- 一律落 [../case_tests/test_baseline/runs](../case_tests/test_baseline/runs)
- 命名：建模 baseline `<YYYY-MM-DD>_<case>_<tag>/`；capability test `<YYYY-MM-DD>_capability_<topic>/`

### 5.4 simulate 全链路通验证 + 真因定位（2026-05-07 晚）

**A. 真跑 EP 实证**：把 sm_16_newarch IDF 直接喂 EnergyPlus 25.2.0
- T-vertex **不卡 EP**：warm-up 无任何几何相关 severe → [plan.md B0'](plan.md) 关闭
- 真 fatal：window 求解器在 `F1_NORTH_W_WINDOW` 收敛失败（4 个 glazing face 温度全 NaN）
- Root cause：fenestration_agent 把 `WindowMaterial:SimpleGlazingSystem` 当作一层玻璃片，组成 玻璃→空气→玻璃 三明治 Construction（EP IDD 硬约束：SimpleGlazing 必须 standalone）
- 手工把 `Window_Double_Glazing` Construction 改成单层引用 SimpleGlazing 后 EP `Completed Successfully` / 0 severe / 9 warnings / 14.8 秒（artifacts [`smalloffice_16_newarch/output/ep_run_glazingfix/`](../backup/tests_history/SmallOffice/smalloffice_16_newarch/output/ep_run_glazingfix)）

**B. 架构结论**：✅ 半人工 intake → 自动下游 → IDF → EnergyPlus 全链路机制 100% 通；零架构层 bug。所有剩余问题都是单一 subagent prompt 级建模质量

**C. 决策：不调 fenestration / construction prompt**
- 理由：idfpy 自带 schema 校验，切换后会原生拒绝该组合；短期 prompt 修属重复投资
- 主线焦点切到**几何正确性**（[plan.md B1/B2/B3](plan.md)），simulate 跑通暂不作短期目标

**D. validator 临时放宽永久化**：[src/validator/data_model.py](../src/validator/data_model.py) `validate_geometry_closure` 保持 `logger.warning`，不恢复 raise；待 idfpy 切换时整体删

### 5.5 B1 阶段闭环 + surface_agent z_floor hotfix（2026-05-12）

**A. B1 整体迁移交付**（[plan.md §B1](plan.md)）
- 3 个 skill 文档库（[`energyplus_mcp_prompt.md`](../skills/energyplus_mcp/energyplus_mcp_prompt.md) / [`intake_output_contract.md`](../skills/energyplus_mcp/intake_output_contract.md) / [`zonetool_prompt.md`](../skills/energyplus_mcp/zonetool_prompt.md)）按 [`energyplus_mcp_migration_audit_2026-05-11.md`](energyplus_mcp_migration_audit_2026-05-11.md) 4 个 Gap 全部补硬约束
- 关键补强：per-floor window chain hard rule（Gap A）/ cross-floor split-pairing required enumeration（Gap B/D，直接挡 `RoofCeiling references not-found` fatal）/ fenestration absolute-world-z primary + per-window self-check（Gap D，但下面 B 揭示这还不够）/ unsupported-case 双标统一（Gap C）/ fenestration chain N-window 通式 + 反例（针对 sm_20 暴露的 top_gap 混淆 slip）
- 旧 vertex synthesis 表恢复回 [`zonetool_prompt.md`](../skills/energyplus_mcp/zonetool_prompt.md)
- artifacts：sm_18（deepseek 起稿，EP fatal anchor）/ sm_19（codex 起稿，10 CHKSBS warning anchor）/ sm_20 output（B1 only，10 CHKSBS）/ sm_20 output_new（B1 + surface fix，0 CHKSBS）

**B. surface_agent z_floor hotfix**（[logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 2026-05-12 条）
- 真因：[`src/agent/nodes/surface.py`](../src/agent/nodes/surface.py) 的 `SURFACE_SYSTEM_PROMPT` 只收 `surface_specs`、看不到 `zone_specs`，且 prompt 没指引读 `z_floor / ceiling_height` → DeepSeek 默认按 3 m 层高建墙 → 上层窗 z 落在墙外 CHKSBS partial-overlap
- 修复：(a) 同时传 `zone_specs + surface_specs` 两段；(b) 加 "per-floor z values come from zone_specs" 硬指引；(c) worked example 改为 F2_S1 (`z_floor=3.60, h=3.60`)
- 备份：[backup/src_history/2026-05-12_surface_agent_zfloor_fix/](../backup/src_history/2026-05-12_surface_agent_zfloor_fix)
- 验证：sm_20 output_new EP `Completed Successfully` / 0 severe / 14 warning（全无害）/ F2 wall z=[3.60,7.20] / 窗 z=[4.60,6.40] 严格落在墙内

**C. 架构通透性新基准**：sm_20 取代 sm_16_newarch 成为"全链路真跑 cleanly 通"的新 anchor（sm_16_newarch 要手工修一行 Construction，sm_20 一把过）。

**D. 残留**：intake 对 East/West F3 corridor 窗有偶发 `z_max = z_min + top_gap` 计算 slip（写成 9.60 应为 10.60）—— 已在 [`intake_output_contract.md`](../skills/energyplus_mcp/intake_output_contract.md) `fenestration_specs > Right-side chain pattern (general)` 加 N 窗通式 + 反例 + 自检规则，下次跑新 case 应被挡住；sm_20 落盘的错值保留作 audit anchor，未手工修。

**E. 工程改动**
- [src/mcp/tools/workflow.py](../src/mcp/tools/workflow.py)：显式传 `output_directory` 给 `runner.run_idf`，EP 产物现在落 `<case>/output/` 而不是全局 `output/results/`（commit `1a817e0`）
- [scripts/run_full_pipeline.py](../scripts/run_full_pipeline.py)：加 `--output-subdir` flag 方便同 case 多版对照（sm_20 跑了 `output/` 和 `output_new/` 两版）

### 5.6 两步法 intake POC PASS + B1.5 立项最高优先级（2026-05-12 晚）

**A. POC 验证结果**（sm_20 全套两步法，详见 [floorplan_redraw_strategy.md §9](capability/floorplan_redraw_strategy.md)）

- **Phase 1**（识图）：Claude Code 会话 + Opus 4.7，7 张图 → 7 份矢量 JSON + summary。schema = strokes[] + pen 类型（wall / wall_fill / window / outline / other），含 plan / elevation 词典分拆 + 4 立面 facade_axis_note 含符号
- **Phase 2**（拓扑）：双路径对比
  - Opus 路径（Claude Code 会话直写）
  - DeepSeek 路径（[`scripts/run_pipeline_deepseek.py`](../scripts/run_pipeline_deepseek.py)，绕过 langchain、thinking enabled、max_tokens=64k、`_fix_js_concat` regex 修 JS 风格字符串拼接、`ensure_schema_initialized()` 初始化 IDD）
- **Step 6 全链路**：Opus 路径 + 下游 9 subagent + EP fatal（construction asymmetry 规则漏洞，phase2_rules v1.3 已修）；**DeepSeek 路径 EP cleanly Completed**（0 severe / 9 warning / 8.49s 全年）
- **F3 corridor 窗 z 修正**：两步法两条路径都对（z=10.60）/ anchor 单步法错（z=9.60）—— phase1 锁定识图结果让 phase2 无机会重做坐标推导，误差预算分离生效

**B. 决策**：**两步法立为新主线**。B1.5 提升为最高优先级（[plan.md B1.5](plan.md)）。B2-B4 评测基线规范化并行推进但必须从一开始就支持矢量 JSON 中间层。

**C. Artifacts 迁移**
- 测试 case：[`case_tests/e2e_tests/smalloffice_20/`](../case_tests/e2e_tests/smalloffice_20)（与 `SmallOffice/smalloffice_20/` 同素材，两步法跑）
- Skill 演进源：[`skills/intake_pipeline/`](../skills/intake_pipeline)（`phase1_vector_schema.md` v1.2 + `phase2_rules.md` v1.3 + 两个 prompt 模板 + README）
- DeepSeek 自动跑批脚本：[`scripts/run_pipeline_deepseek.py`](../scripts/run_pipeline_deepseek.py)
- SVG 渲染（phase1 人工校验工具）：[`scripts/tool_scripts/render_vector_to_svg.py`](../scripts/tool_scripts/render_vector_to_svg.py)
- 三方对比详表：[`case_tests/e2e_tests/smalloffice_20/compare/diff.md`](../case_tests/e2e_tests/smalloffice_20/compare/diff.md)

**D. 后续主线动作**（[plan.md B1.5](plan.md)）
- B1.5.a 异图 POC v2（噪声 / 装饰 / 索引 / 楼梯）
- B1.5.b phase2_rules.md / phase1_vector_schema.md 持续迭代（吸收 Opus 10 条 followup notes）
- B1.5.c `intake_node` 重写为两步串行调用（保留 `--intake-from` short-circuit）
- B1.5.d `scripts/run_pipeline_deepseek.py` 迁入主线作 phase2_node
- B1.5.e [`new_case_guide.md`](guides/new_case_guide.md) Step 4 拆 4a phase1 / 4b phase2
- B1.5.f 评测脚本支持识图错 ↔ 推理错自动归因

### 5.7 异图 POC v2 PASS（sm21）+ 切新架构 greenlight（2026-05-28）

**A. sm21 端到端 PASS**：2 层办公异图（15×8 m，含家具/门噪声）全套两步法（phase1 冷启 Opus 子代理识图 → phase2 DeepSeek 盲跑拓扑 → 下游 9 subagent → EP）。EP `Completed Successfully` / 0 severe / 0 fatal / 6 无害 warning / 5.07s / **15 窗**。继 sm_20 的第二个两步法干净 EP anchor，且首个**异图**（非 sm_20 同源素材）跑通。phase1 重绘忠实（零家具泄漏、门 healing、立面两层 wall_fill 分割、facade 翻译表符号正确），误差预算守住（助手看过图但 phase2 走不看图的 DeepSeek 脚本）。

**B. 暴露并修复 phase2 规则缺口（咱们负责侧）**：phase2 首跑把窗玻璃只写进 `construction_specs` 内联 `WindowMaterial:SimpleGlazingSystem`、`material_specs` 漏声明具名 glazing 材料 → material 节点没建玻璃材料 → construction 节点 `list_materials` 找不到、按其 prompt 正确跳过 `Default_Window` → fenestration 中止 0 窗 → EP 段错。**下游 3 节点行为全对，根因在 phase2/rules.md**（非协作者下游 prompt）。修复：[`phase2/rules.md`](../skills/intake_pipeline/4_mep/mep.md) Step 5 新增 "material ↔ construction split" 硬规则（glazing 材料必须作具名 `WindowMaterial:SimpleGlazingSystem` 进 material_specs、`Default_Window` 按名引用、禁内联）。重跑验证 PASS。备份 `backup/Skill_history/2026-05-28_phase2_glazing_material_rule/`。

**C. 决策：切两步法新架构 greenlight**：POC v2 异图跑通 → 确定切两步法为主线架构，[plan.md B1.5.c](plan.md)（`intake_node` 重写为 phase1+phase2 串行）就此解禁。**建模质量问题（几何细节等）仍较大，按"切架构 + 质量慢慢解决"并行推进**，不阻塞架构切换。

**D. prompt 模板归一 + 工具修整**：phase1/phase2 启动 prompt 从 skill 库移进 `guides/new_case_guide_twostep.md`（已删，prompt 后并入 new_case_guide.md 附录）Step 4a/4b（一处，[[skills-lib-clean-spec-policy]]）；[`run_pipeline_deepseek.py`](../scripts/run_pipeline_deepseek.py) 改为从 skill 库直接读规则文档（消除 case 级陈旧副本依赖）。

### 5.8 两步法切主线架构落地 + InterZone 确定性几何门 + 正式流程指南（2026-05-29）

**A. B1.5.c 两步法 `intake_node` 串行重写交付**（[plan.md B1.5.c/d](plan.md)）：`intake_node` 三路分发（短路 `--intake-from` / `phase1_vector_dir`→phase2 / legacy 单步）；新增 [src/agent/pipeline.py](../src/agent/pipeline.py)（phase2 **单一实现**，DeepSeek raw client + thinking，读 `llm.yaml:intake_correction`）；[run_full_pipeline.py](../scripts/run_full_pipeline.py) 加 `--reading-from`；[`run_pipeline_deepseek.py`](../scripts/run_pipeline_deepseek.py) 收成 `phase2.py` 的薄 CLI 包装（脚本与主线不再漂移，B1.5.d）。**e2e 首次完整跑通新架构**（phase1 矢量→phase2→9 下游→IDF 装配），机制 100% 通。

**B. InterZone 确定性几何门**（审阅 A 落地）：新增 [src/validator/interzone.py](../src/validator/interzone.py)，在 [`WorkflowTool`](../src/mcp/tools/workflow.py) 装配 IDF 后、跑 EP 前作 fail-fast 门（OBC=Surface 目标存在/互逆/单一引用/面积/法向相反/通用点到面共面/最小边长 ≥0.1m）。标定 4 个已知 IDF **零误杀**；e2e 全新 phase2 输出上**当场抓 6 个跨层 split-pairing 缺陷挡 EP**。把"EP 通过≠几何对"从隐患变显式可定位 issue。

**C. per-case 模型配置**（用户定调，2026-05-29）：**正式测试每次独立指定模型组合**——`<case>/llm.yaml`（`--init-llm-config` 从全局拷模板）经环境变量 `EP_AGENT_LLM_CONFIG`（[`llm.py:resolve_llm_config_path`](../src/agent/llm.py)）对 phase2 + 9 下游统一生效；全局 [`llm.yaml`](../src/configs/llm.yaml) 兜底。换模型组合 = 改 per-case 文件,不动全局。

**D. 正式流程指南**（B1.5.e）：[guides/new_case_guide.md](guides/new_case_guide.md) 正式化为**两步法完整版**（phase1 半人工 + phase2/下游/EP 一次性自动 + per-case 配置 + InterZone 门验收层 + dev临时模式vs正式模式边界）；phase1/phase2 启动 prompt 并入其**附录 A/B**，临时文件 `new_case_guide_twostep.md` 已删（guide 完全并轨）。旧单步法版备份 [logs/backup/new_case_guide.md.bak_2026-05-29](logs/backup)。同时清理旧单步法架构遗物 `test_data/{claude_ep.md,EnergyPlus_Agent_Prompt.md}`（无引用孤儿）。

**E. 跨模型审阅闭环**：两份 Codex review（[InterZone 门](logs/reviews/verdict/2026-05-29_interzone_pair_gate_review.md) + [两步法切换](logs/reviews/verdict/2026-05-29_twostep_intake_node_switch_review.md)）共 **3 High + 4 Med/Low 全修**；[re-verify](logs/reviews/verdict/2026-05-29_review_fixes_reverify_review.md) 判 G1-G4/T1-T5 全 PASS、两 review **closeable**。测试 5→23（[tests/test_interzone.py](../tests/test_interzone.py) 12 + [test_intake_twostep.py](../tests/test_intake_twostep.py) 3 + [test_llm_config.py](../tests/test_llm_config.py) 3）。

**F. 残留**：① **建模质量主线**——phase2 跨层 split-pairing 几何质量有波动（同一道墙跨层 5cm 抖动 + 天花未按下层细分区切分），属识图建模主线（[capability/recognition_modeling_capability.md](capability/recognition_modeling_capability.md) 审阅 B 设计已捕获，未落地）；门负责抓，容差重生成待做。② guide 完全并轨（删 twostep 附录）。③ 全自动 VLM phase1（`intake_phase1` 段预留未接）。④ InterZone **覆盖完整性**校验（抓"本该是内部边界、两侧却都标 Outdoors/Adiabatic、不在配对图里"的洞，per-pair 门 + EP 都漏）——**决策 2026-05-29 走 `shapely` 长期解、不急实现仅标记**，落地时机 = 招到能暴露的 case 或 B5 开工时（[logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 2026-05-29 条）。

### 5.9 PartA 容差校正层落地 + phase2 三段解耦 + P0 通过（2026-06-07）

忠实建模 leg（[capability/recognition_modeling_capability.md](capability/recognition_modeling_capability.md)）的几何校正能力首次进 phase2 执行。详细接线见 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)；改动史见 [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 2026-06-07 条。

**A. PartA 校正层 skill 库**（[skills/intake_pipeline/phase2/PartA-correction/](../skills/intake_pipeline/phase2/PartA-correction)）：A0 契约（容差 registry / 证据模型 / audit schema / 校验 schema / method profiles / 上游 provenance 契约）+ A1 坐标归一 + A2 规范化 + A3 仲裁 + A4 几何先验 + README。切分轴 = 确定性（A1/A2）vs 判断（A3/A4），即未来 codify 接缝。

**B. phase2 一步出 → 三段解耦**：sm21 实测一步出不可靠（LLM 不执行 A2 跨层统一 → 4 个 0.05m 碎片被门拦）。根因 = 校正未物化、确定性操作交 LLM。改为 **2a 校正(LLM,出 `CorrectedGeometry`) → 确定性核(代码) → 2b 建模(LLM,出 `IntakeOutput`)**（[src/agent/pipeline.py](../src/agent/pipeline.py) + [src/agent/correction/](../src/agent/correction)）；中间态全物化（埋点/换模型/baseline diff 基础就位）；每段独立 LLM section。**确定性核结构性消碎片**（sm21 gate 4→0）。

**C. EP 拦路逐层剥离**：核消碎片后门过，EP 暴露下游问题——rules.md Step 4 内墙 `OBC=Zone`（EP 25.1.0 不认）改 `OBC=Surface`+互逆；InterZone 门补非法 OBC 守卫（旧版对 Zone 完全盲）。剩余互逆配对 26 issue = **切配轨**（非 partA），门精准抓、无崩溃。

**D. 用户认定 P0 通过**（2026-06-07）：每类失败现精确归层。**待完善**（不阻塞 baseline，= 下一步优先级 #2，缺口详见 pipeline_stage_contracts §5）：① 确定性核统一误差约束（吸 `SNAP_GRID` 而非簇均值，常数取 A0 registry）② 几何+MEP 先验两段共享库（A4 现仅几何、仅 phase2a）③ phase1 上游 provenance 契约 ④ audit sidecar 接评测归因。**输出契约 `IntakeOutput` 不变，下游零影响。**

**E. 实验产物未入库**（惯例）：`smalloffice_21/{output_*,phase2_intake/staged_*}`。

### 5.10 优先级 #2 落地 + 固化流程 + 切配定性反转 + 目标架构（2026-06-09）

详见 [capability/recognition_modeling_capability.md §7.1](capability/recognition_modeling_capability.md) + [logs/downstream_agent_changes.md 2026-06-09](logs/downstream_agent_changes.md)。

**A. partA 待完善 #2 落地**：确定性核 #2.1（容差外置 [correction.yaml](../src/configs/correction.yaml) + 吸 `SNAP_GRID` + 窗户分级 10mm+钳父墙）/ #2.4（连接性补缝 300mm，内墙→外墙）/ #2.2（MEP 去混合为 [priors/mep.md](../skills/intake_pipeline/phase2/priors/mep.md) draft 种子）。新增 [CorrectedGeometry 渲染器](../scripts/tool_scripts/render_corrected_geometry.py)。测试 27→30。

**B. 固化规范流程 + 产物布局**：`run_full_pipeline --reading-from` 产物按阶段分门别类（`<case>/{phase1, phase2/{partA,partB}, EP_run}`，[pipeline_stage_contracts §3.1](architecture/pipeline_stage_contracts.md)）。新建 **`smalloffice_21_pre`**（干净 sm21，phase1=Sonnet sub-agent，余全 DeepSeek）完整跑通：phase1 忠实、#2.1 验证（全栅格无 mm 级值）、门抓 12 切配 issue/EP 按设计未启动。

**C. 切配定性反转（重要，反转 2026-06-07 旧定）**：sm20/sm21 对照证明**一步出 LLM 切配做得对**（sm20 三层 7/8/4 更难也 0 门 issue、真切子面），**staged 退化**（12/26 issue）。根因 = staged 把跨层切配孤立成 LLM 机械记账，非 LLM 不能。→ **切配收回本项目侧、确定性做**（[split_pairing_kernel_reference §6](reference/split_pairing_kernel_reference.md)）。

**D. 目标总架构定调（用户）**：`识图→校正→建模·几何(确定性)→切配·仿真(确定性)→物理挂载→下游·组装`。一刀切分：**LLM 只做 感知+校正判断+物理语义；代码做 所有几何(建模+切配)+装配**。几何造面/切配全收进确定性内核（核之后吃 cells），下游退化成誊写、契约不变。与 phase3（MEP 分段）同向。**待实现**（矩形现可落 / 非矩形随 B5 shapely）。详见 [pipeline_stage_contracts §0.1](architecture/pipeline_stage_contracts.md)。

### 5.11 0–5 管线重构 Step 2–7 落地：几何彻底确定性化（2026-06-09）

落地 §5.10.D 定调的目标架构。详见 [archive/2026-06-09_pipeline_0-5_refactor_handoff.md](archive/2026-06-09_pipeline_0-5_refactor_handoff.md) + [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)（已更新）+ [archive/rules_md_split_map.md](archive/rules_md_split_map.md)。

**A. 几何确定性内核接进主链**（Step 2–4）：[src/agent/geometry/](../src/agent/geometry) `modelling.py`（cells→zone 体块+造面）+ `split_pairing.py`（互逆配对+跨层切分，leg-agnostic）+ `specs.py`（序列化）。Step 2 先验证内核覆盖 rules.md 几何 edge case（sm20-shaped 三层 4/3/2 错配对标 InterZone 门 0 issue），Step 3 拆两模块，Step 4 接进 `run_phase2`（先 advisory，物化 building_geometry.json + 门报告）。

**B. phase2b 解耦**（Step 5，用户定 **fork (a)**）：单一 phase2b LLM 拆成 **几何序列化(代码)→4_MEP(LLM 只产 8 非几何字段)→5_intakeoutput(代码装配+契约校验)**。几何序列化成 `surface_specs` 文本、下游 surface_agent 忠实誊写——`IntakeOutput` 11 字段契约不变、下游代码不动。新增 [src/agent/intakeoutput.py](../src/agent/intakeoutput.py)（`MepOutput` + `assemble_intake_output` + `validate_contract` 逐 token 查 4_MEP 是否定义了几何引用的每个 construction，缺则 raise）。construction 词汇表（`CONSTRUCTION_VOCAB`）是序列化器↔4_MEP 的接缝（互逆面同名 `Cons_InterFloor`）。内核 build 硬错时回退 legacy `run_phase2b`（Step 8 后删）。

**C. 产物布局 0–5 阶段化**（Step 6）：`<case>/{1_correction,2_modelling,3_split_pairing,4_mep,5_intakeoutput}/`（替 partA/partB），直接落 `<case>` 下（同 EP_run）。skill 库 `4_mep/authoring.md`（物理撰写规则）；`phase2/rules.md` 标 SUPERSEDED（仅 legacy fallback 用）。

**D. 口径统一**（Step 7）：**切配 = `adjacent_zone`/`adjacent_surface`(surface_specs) = `OBC=Surface`+`object`(IDF) = `obc`+`obc_obj`(代码)**，同一事三表述；EP 无 `Zone` 边界条件（[pipeline_stage_contracts §0 口径框](architecture/pipeline_stage_contracts.md)）。fork (b)（确定性直接造面绕过下游）记录待后续整合再议。

**E. 测试 50 绿**（kernel 8 + 序列化/装配/契约 4 + 内核接线 3 + 历史）。每步 备份→实现→DeepSeek 审→commit。**残留**：① Step 8 sm21_pre e2e 复测（用干净手搓输入，per 用户决定 phase2a 重叠 defect 另开）② legacy `run_phase2b` + `rules.md` Step 8 后删 ③ 非矩形端到端随 B5。

### 5.12 0–5 完整体检 + 硬伤当日全修 + 复杂度路径骨架（2026-06-11，Fable 5）

[audit request](logs/reviews/request/2026-06-10_pipeline_0-5_full_audit_request.md) → [review + 处置记录](logs/reviews/verdict/2026-06-11_pipeline_0-5_full_audit_review.md) 闭环；改动史 [downstream_agent_changes.md 2026-06-11 条](logs/downstream_agent_changes.md)。

**A. 体检实证（验收全过）**：sm21（14 区/100 面/15 窗）+ **sm20 三层新架构首验一把过**（19 区/135 面/16 窗、z-stack 0/3.6/7.2 正确合成、旧 0_reading schema 兼容）；两案例 InterZone+schedule 门 0 issue、EP `Completed Successfully` 0 severe、warning 全无害；**下游誊写保真 100%**（235 面逐顶点比对全为同环旋转、零法向翻转）；切配覆盖完整性手算独立验证 0 洞；correction 4 次 LLM 调用全一发即中。

**B. 硬伤 4H/3M/3L 全修（三 commit）**：`49c3fea` 内核守卫（H1 跨层重复 cell id 三处 dict last-wins → 核+内核 raise；H2 z-stack 裸奔 → 核 ≤0.3m 吸附+内核 >0.02m raise；M1 丢窗 raise；M2 钳制产非法窗 → 显式丢弃记 unsupported；L3 facade Literal；**H4 修复中新发现**——`_find_parent_wall` 不看朝向，全进深房间南窗静默挂北墙，加 Newell 外法向匹配）；`4df069e` EP 闭环（H3 `run_simulation` 原丢弃 `run_idf` 返回值、EP fatal 报 success——接住 + 新增 `read_ep_end()` 解析 `eplusout.end`，失败返 `success=False` 带 err 尾部，成功消息含 severe/warning 数 → **baseline EP 断言可自动化**；M3 schedule 门 audit 行）；`35aa185` correction 稳健性（L1 配置错不再静默 fallback；L2 传输异常进重试；draw 级复合校验 schema/0 窗/重复 id/z 断裂 → 坏 draw 重抽）。**三层防线定型**：draw 重抽 → 核修复/显式丢弃 → 内核 raise。测试 69→**99 绿**；audit 复现脚本反向验证全 PASS；sm20 e2e 复跑（`output_fable_audit_postfix`）回归一致。

**C. 0–3 复杂度升级路径骨架**（`58627cd`，[capability 文档](capability/pipeline_0-5_capability_upgrade_suggestions.md)，用户定调主战场）：阶梯 **C2**（正交多边形 + 多平面立面；内核 shapely 半就绪，缺口在 0/1 窗归翼仲裁 + 覆盖门提前落地）→ **C3**（退台已就绪先收；挑空/跨层 zone = 内核最大改造：墙配对 by_floor → z 区间重叠驱动、切配首次扩到**切墙**、带洞楼板分解）→ **C4**（斜交墙：核旋转系吸附 + 窗挂载投影化）。三原则：分工线不动 / 内核先行（合成用例先升 2+3）/ 守卫与档位同步。五接缝：schema 演化（四处同步）/ 核算法 / 切配 z-cut / 门守卫 / 识图输入类型（C3 需剖面图 image_kind）。

**D. capability 顺手发现**（4_mep）：材料质量跨 draw 波动（sm21 某 draw 全 no-mass）/ 活动量数值超典型区间 / design days+地温默认块缺——记录待落地，不阻塞。

### 5.13 仓库整理 + Codex review 闭环 + 标准 case 布局（2026-06-14，commits `7494253`→`8e3b1a8`）

建规范 baseline 前的整理 + 收尾会话。改动史见 [downstream_agent_changes 2026-06-14 条](logs/downstream_agent_changes.md)。

**A. 仓库结构整理**：① **脚本合并**——散在 `scripts/` + `Tool_scripts/` 收成单一体系：`scripts/`(总启动 `run_full_pipeline`+`run_pipeline_deepseek`) / `scripts/tool_scripts/`(render×3 + baseline_record + preprocess_images) / 根 `tests_scripts/`(deepseek_review) / 根 `backup/scripts_history/`(退役归档 run_demo/export_trace/_share/export_idf/idfpy_roundtrip)。② **history 备份归并** `backup/{Skill,src,MCP,scripts}_history/`（核实旧文档「都被 gitignore 排除」**失实**——实际多为跟踪/未忽略，已就地校正 §6#5）。③ **`test_data/` → `case_tests/`**（`0_reading_tests`=phase1_generalization / `e2e_tests`=SmallOffice_TwoStep / `test_baseline` 随迁内部不动）+ 旧单步语料 `SmallOffice` → `backup/tests_history/`。④ 删空占位 `docs/` + gitignore Fable audit 产物。

**B. Codex「phase→0–5 阶段名清理」review 闭环**（CHANGES REQUESTED，6 findings 全修，[review 处置表](logs/reviews/verdict/2026-06-10_phase_to_stage_terminology_cleanup_review.md)）：**M1 代码硬伤**——`pipeline.py:_section()` `intake_correction` 缺失原静默落下游 `default` ReAct 配置（错模型/thinking），改**显式 raise**；`intake_mep` 仅回退已确认存在的 correction（+3 测试）。**M2-M4**：会话首加载 CLAUDE.md §1.2/1.3/2.1/6#7/7 + 权威 pipeline_stage_contracts §3.1 + new_case_guide + corpus/case READMEs 全部从已删 phase1/phase2/run_phase2/partA 改为 0–5 当前接线（命令 `--reading-from phase1`→`0_reading`、产物路径、已落地内核"待建"→"已落地"）；CLAUDE.md 顶加统一术语 banner。

**C. 标准 case 组织结构定调（用户）+ 代码路由接通**：`<case>/{llm.yaml(根), case_data/(图纸+testdata), 0_reading…5_intakeoutput/, EP/(IDF)→EP/EP_run/(仿真)}`。建首个参考 case **`sm20_anchor`**（sm20 干净素材，未跑）。代码路由：`run_full_pipeline` 读 `case_data/testdata_prompt.json`（缺则回退 case 根=旧 case 兼容）；新增 **`SimContext.ep_run_subdir`** opt-in（贯穿 `workflow.run_simulation`/simulate 节点），默认正式流让 EP 仿真落 `EP/EP_run/`、IDF 留 `EP/`，不影响其他调用方。测试 99→**103 绿**。**下一步**：跑 sm20_anchor 出干净产物 → 逐环节约束各阶段输出 + 校验方式 → sm21 起规范 baseline → sm23 质量 → 接 VLM。


---

## C. 变更日志（CLAUDE.md + plan.md 合并，倒序）

### CLAUDE.md changelog

_2026-06-14 — **仓库整理 + Codex review 闭环 + 标准 case 布局**：新增 §5.13 + 顶部 banner。①仓库结构整理（脚本合并 `scripts/`+`tool_scripts/`+`tests_scripts/`、history 归并 `backup/`、`test_data/`→`case_tests/`、旧单步语料归档 `backup/tests_history/`、删空 docs/）；②Codex「phase→0–5 阶段名清理」review 闭环（M1 `pipeline.py:_section()` 严格化代码修+3 测试、M2-M4 活文档全改 0–5 当前接线、顶加术语 banner）；③标准 case 结构定调（`case_data/`+0–5+`EP/EP_run/`+根 `llm.yaml`）+ 建 `sm20_anchor` + 代码路由接通（`SimContext.ep_run_subdir` opt-in、testdata 读 case_data）。测试 99→103。下一步=逐环节约束输出+校验 → sm21 规范 baseline。_

_2026-06-09 (v2) — **优先级 #2 落地 + 固化流程 + 切配定性反转 + 目标架构**：新增 §5.10。partA #2.1/#2.4/#2.2 落地（容差外置 correction.yaml + SNAP_GRID 吸附 + 窗户分级 + 连接性补缝 300mm + MEP 去混合 + CorrectedGeometry 渲染器，测试 30）；固化产物布局（`<case>/{phase1,phase2/{partA,partB},EP_run}`）+ 新建 sm21_pre 完整跑通；**切配定性反转**（sm20/sm21 对照证明一步出 LLM 切配做得对、staged 退化→切配收回我方确定性做，反转 2026-06-07"归下游"）；**目标总架构定调**（识图→校正→建模·几何→切配·仿真→物理挂载→下游，LLM 只做感知+校正判断+物理语义、代码做所有几何+装配）。§8.1 加"确定性造面/切配内核"P0 待建 + phase3 标记。详见 §5.10 + [pipeline_stage_contracts §0.1/§3.1](architecture/pipeline_stage_contracts.md) + [split_pairing_kernel_reference §6](reference/split_pairing_kernel_reference.md)。_

_2026-06-09 — **状态对齐到 6.7 partA + #1 规范梳理**：新增 [architecture/pipeline_stage_contracts.md](architecture/pipeline_stage_contracts.md)（子流程↔skill↔中间产物权威接线 + 5 条规范不变量 + 4 条待解接缝缺口，喂优先级 #2/#3）；CLAUDE.md 补 §5.9（PartA 校正层 + phase2 三段解耦 + P0 通过，精简版）；§1.2 架构图更新为两步法+phase2 三段（原单步图已失真）；§1.3 加 phase2.py / correction/ / interzone.py；§7 索引加 pipeline_stage_contracts + PartA-correction；§8.1 建模质量主线标 P0 通过 + 三优先级。改动史见 [logs/downstream_agent_changes.md](logs/downstream_agent_changes.md) 2026-06-07 条。_

_2026-05-29 — **两步法切主线落地 + InterZone 几何门 + 正式指南 + per-case 配置**：新增 §5.8。B1.5.c/d/e 交付（`intake_node` 两步串行 + `src/agent/pipeline.py` 单一实现 + `--reading-from` + `run_pipeline_deepseek` 收薄 + `new_case_guide.md` 正式版两步法）；审阅 A 落地确定性 InterZone 门（`src/validator/interzone.py`，EP 前 fail-fast，e2e 全新输出抓 6 缺陷）；per-case 模型配置（`<case>/llm.yaml` 经 `EP_AGENT_LLM_CONFIG` 覆盖，全局兜底）；两份 Codex review 3 High + 4 Med/Low 全修、re-verify 全 PASS；测试 5→23。§7 索引更新（new_case_guide.md 正式版 / twostep 降级附录）；§8.1 B1.5 子任务标进度。残留=建模质量主线（phase2 跨层配对波动，审阅 B 待落地）。详见 §5.8。_

_2026-05-28 — **异图 POC v2 PASS（sm21）+ 切新架构 greenlight**：新增 §5.7（sm21 2 层异图全链路 EP cleanly 跑通 / phase2 glazing material 规则缺口暴露并修复 / 切两步法主线 greenlight，B1.5.c 解禁 / prompt 模板归一 + run_pipeline_deepseek 读 skill 库）；plan.md B1.5.a 标 ✅ 首个异图 PASS。glazing 修复=[`phase2/rules.md`](../skills/intake_pipeline/4_mep/mep.md) Step 5 "material ↔ construction split" 硬规则（根因在咱们侧 phase2 规则，非协作者下游 prompt）。质量问题按"切架构 + 慢慢解决"并行。详见 §5.7 + plan.md B1.5.a。_

_2026-05-25 — 交叉审阅工作流 + 两步法 skill 库整合：§6 新增 #14（`AI_agent/review/` 的 request→review→act 闭环，首份是 Codex 审两步法迁移）；§7 索引加 `new_case_guide_twostep.md`（临时两步法 Step 4 指南，后已删并入 new_case_guide.md）+ [`review/`](logs/reviews)。配套：两步法 skill 库（[`../skills/intake_pipeline/`](../skills/intake_pipeline)）已全英文化 + 清成纯当前版本 spec（无时间戳/版本日志/决策引用）+ 补回旧单步法输出契约缺口 + 按 Codex review 5 条 findings 修复（去 sm_20 硬编码 / split-pairing sub-range / fenestration 审计字段 / supp+blank facade / phase1 thickness 例子）。_

_2026-05-19 — 多端开发环境上线：§6 新增 #13（VS Code Dev Container 统一 Win/Mac/云，容器内 EnergyPlus 25.1.0 与宿主机 v25.2.0 patch 差异提示），§7 文档索引加 [`../.devcontainer/README.md`](../.devcontainer/README.md)。三个 AI CLI 改在 Dockerfile 构建期装（修原 postCreateCommand 静默半完成 bug）。#13 补 `docker/` 服务器/MCP-server 部署镜像用法（docker-compose 正式版 vs dev 热重载版），与 `.devcontainer/` 区分。_

_2026-05-12 (晚) — **两步法 POC PASS + B1.5 立项**：新增 §5.6（sm_20 全套两步法验证结果 + 决策切主线 + artifacts 迁移目录），§7 索引加两步法 skill / corpus 路径，§8.1 加 B1.5 最高优先级 todo。详见 [`floorplan_redraw_strategy.md §9`](capability/floorplan_redraw_strategy.md) + [plan.md B1.5](plan.md)。_

_2026-05-12 — B1 阶段闭环：新增 §5.5（sm_18/19/20 真跑发现 + B1 全部交付 + surface_agent z_floor hotfix）；§6 #5 升级为"Skill / MCP / 下游 subagent 三类备份"并加 backup/src_history/ + downstream_agent_changes.md 流程；§7 文档索引加 downstream_agent_changes.md；§8.1 B1 标 ✅ 切主线到 B2-B4。详见 [`downstream_agent_changes.md`](logs/downstream_agent_changes.md) 2026-05-12 条 + [plan.md B1](plan.md)。_

_2026-05-07 (晚 v3) — runner.py 加 EP exe 三级解析（`$ENERGYPLUS_EXE` env → PATH → 硬编码 `D:\EnergyPlusV25-2-0\energyplus.exe`）；`.env` / `.env.example` 同步加 `ENERGYPLUS_EXE`；§1.3 路径表说明同步。下次跑 `run_full_pipeline.py <case>` 不再卡 FileNotFoundError。_

_2026-05-07 (晚 v2) — §1.3 加 EnergyPlus 引擎本地路径 + EPW 默认气象；§7 plan.md 描述更新为三阶段；§8.1 加新主线 B1 (阶段 1 恢复) + B2-B4 / B5-B7 阶段汇总。详见 [plan.md changelog](plan.md)。_

_2026-05-07 (晚) — 真跑 sm_16_newarch IDF 实证 EP 全链路通：T-vertex 不卡 EP，真 fatal 是 fenestration SimpleGlazing layer 兼容性 bug。决策不调 prompt（与 idfpy 切换一并解），主线焦点切到几何正确性。新增 §5.4；§8.1 重写活跃 todo（关 T-vertex / 加 per-subagent 模型配置）；§8.2 加 fenestration glazing deferred item。_

_2026-05-07 — 重写精简：原 410 行压到 ~150 行；§7 历史 timeline（sm_13/14/15/16 各 baseline + token 优化 P0 全过程 + Claude Code harness 切换等）整体下移到 baseline runs / git log；保留对当前架构仍有约束力的决策（几何/MEP 拆分 / trace 解码 / 半人工固化 + A2）；§5 索引补 backup/；§6 #5 合并 backup/Skill_history/backup/MCP_history 备份约定；§8 拆活跃 / 搁置 / Pivot 三档。详细历史变更日志见 git log。_

### plan.md changelog

_2026-05-29 — **B1.5.c/d/e/g 交付（两步法切主线 + InterZone 门 + 正式指南）**：B1.5.c `intake_node` 三路分发串行 + `src/agent/pipeline.py` 单一实现 + `--reading-from` + per-case 模型配置；B1.5.d `run_pipeline_deepseek` 收成薄包装；B1.5.e `new_case_guide.md` 正式化两步法；新增 B1.5.g InterZone 确定性几何门（审阅 A，EP 前 fail-fast，e2e 全新输出抓 6 缺陷）。两份 Codex review 3 High + 4 Med/Low 全修、re-verify 全 PASS；测试 5→23。e2e 首次完整跑通新架构（机制 100% 通，几何质量挂门 = 建模质量主线问题，审阅 B 待落地）。详见 [CLAUDE.md §5.8](CLAUDE.md)。_

_2026-05-12 (晚) — **两步法 POC PASS + B1.5 立项最高优先级**：sm_20 全套两步法（phase1 矢量化 → phase2 拓扑建模）+ 下游 + EP 真跑通过（DeepSeek 路径 EP cleanly / Opus 路径暴露 InterZone construction rule 漏洞已在 phase2_rules v1.3 修）。F3 corridor 窗 z 修正（anchor 单步错 9.60，两步法都对 10.60）证明误差预算分离生效。新增 B1.5 节：POC v2 异图 / intake_node 改两步 / 评测嵌入 / new_case_guide 重写。详见 [floorplan_redraw_strategy.md §9](capability/floorplan_redraw_strategy.md) + B1.5 节。两步法 artifacts 迁到 [`case_tests/e2e_tests/`](../case_tests/e2e_tests)，skill 演进源在 [`skills/intake_pipeline/`](../skills/intake_pipeline)。_

_2026-05-12 — **B1 阶段闭环**：3 个 skill md 全部按 audit 4 个 Gap 补硬约束 + fenestration chain N 窗通式 + 反例；surface_agent prompt + 输入装配 hotfix（backup/src_history 备份 + downstream_agent_changes.md）。sm_20 半人工流 EP cleanly 跑通取代 sm_16_newarch 成为新通透性 anchor。推荐执行顺序更新：主线焦点切到 B2-B4（评测基线规范化）。详见 [CLAUDE.md §5.5](CLAUDE.md) + B1 节本文。_

_2026-05-07 (晚 v2) — B 段三阶段重组（用户路线图）：阶段 1 恢复 [B1] / 阶段 2 评测基线规范化 [B2-B4] / 阶段 3 能力升级 [B5-B7] / 远期 [B8-B9]。新 B1 = 旧 skill 约束迁移到新架构（吸收原 B4 CoT 内容）；新 B4 = Opus baseline + 校对方案 + token 协议升级（吸收原 B0'''）；新 B5/B6/B7 = 非方形平面 / 全局坐标退台挑空 / 规范化绘图（含原 B5 PaddleOCR 预处理）；新 B8/B9 = 原 B6/B7 远期 pivot。Milestone 映射加 M0 恢复阶段。_

_2026-05-07 (晚) — 真跑 sm_16_newarch IDF 喂 EP 实证：T-vertex 不卡 EP（B0' 关闭），真 fatal = fenestration_agent SimpleGlazing layer 兼容性 bug，手工修后 EP PASS。决策：不调 prompt，与 idfpy 切换一并解；当前主线焦点切到几何正确性。推荐顺序去 B0；B0/B0'/B0''/§C 全更新。_

_2026-05-07 — A 段四项全闭环（A1 schema drift PASS / A2 多 section LLM / A3 run_full_pipeline 三入口 / A4 文档全修订），从主体下沉到表格；新增 B0 sm_17 端到端首跑作为半人工流验证；B3 改半人工版（用户无 Anthropic API）；B4 加入 Floor_N_* 模板禁用补丁；B5 改 Tool_scripts 预处理脚本（半人工流 intake 在会话外）；B6 footnote 去掉 A2 依赖（已就绪）；C 段加 sm_17。_

_2026-05-05 全文重写。删旧版 CoT vs 前置小模型探讨；按 architecture.md 新架构理解重组为「代码跑通 + 识图能力」两线 TODO。_
