# Fable5 项目体检报告

> 2026-07-05 · Fable5 自主主控 · 审计/规划任务(零代码改动)。
> 取证方式:6 路并行子代理(A2 工程链路 / A3 迁移第四路 / C3 烤死假设 / C4 测试+判卷事实;2026-07-06 用户授权追加 D1 环境地基 / D2 skill 一致性)+ Fable5 本人通读全部权威文档(CLAUDE.md / pipeline_stage_contracts.md / judge_grade_model.md / reading_improvement_methodology.md / pipeline_0-5_capability_upgrade_suggestions.md / geometry_first_zonification.md / plan.md / codex_cv_plan.md)后综合裁决。
> A3 特意**不派 Codex**:既有 GO 裁决即 Codex 所出,第四路必须换血统才有独立性。

---

## A 现在(诊断 + 大致修复方向)

### A1 · 0–5 管线架构设计诊断

**总评:架构骨架健康,四条不变量(分工/世界坐标/契约/gt 铁律)在代码层基本站得住;真正的架构级隐患不在"边界画错了",而在三处"边界画对了但执行体不对/执行体重复"。**

**A1-1(最重)· 分工铁律 #1 在两处被"暂时豁免",且豁免已固化成常态**
- 现象:①0_reading 的 schema 要求 VLM 直接吐**最终米制坐标**——迫使 VLM 做尺寸链累加算术,这是文档自认的过度分割根因([reading_improvement_methodology.md §3](AI_agent/capability/reading_improvement_methodology.md):"reading 曾做累加算术=违反 0-5");② 立面 local→world 世界落位——契约文档明确归"确定性代码"([pipeline_stage_contracts.md §1 1_correction 校验(b)](AI_agent/architecture/pipeline_stage_contracts.md)),但实际由 correction LLM 按 A1 §2.2 prose 手工换算符号([pipeline.py:376-380](src/agent/pipeline.py#L376-L380) prompt 原话 "mind the North/West sign flip"),而确定性替代品 `derive_facade_frame` 建好、E/W sign 已翻正并有 gt 锚定测试(commit `23a0e47`),**仍零调用点闲置**(全仓库 grep 仅命中自身)。
- 根因:两处都是"判断-几何分工"里**无判断成分的纯几何**活,却留在随机层。它们不是被架构漏掉,是被 Phase B defer——但 defer 的代价每个 run 都在付(每次世界落位都是一次 LLM 符号推理的掷骰子)。
- 修复方向:Phase B 双通道 schema 解①;②可以**先行单独接线**——`derive_facade_frame` 已具备接线条件(sign 正确+gt 测试在),不必等完整 Phase B,先作 gate① 交叉校验(LLM 落位 vs 确定性落位,不一致即 flag)是零风险中间态。风险/优先级:高(与 B2 排序合并看)。

**A1-2 · 校验体系"一套检查、两路消费",无单一真源保证 parity**
- 现象:同一批 check 函数被 `validate_case`(capstone)与 `run_pipeline`(inline)各自独立接线,两路的接线清单靠人手维护。A2 取证证明它**已经漂移**(0_reading 段与 S5 门禁,详 A2);C3 取证另证 kernel 覆盖逻辑在内核与 validator **双写**([split_pairing.py:99-129](src/agent/geometry/split_pairing.py#L99-L129) vs [kernel.py:238-259](src/validator/checks/kernel.py#L238-L259)),改一处漏另一处。
- 根因:桶③收口是"逐段手工补齐",没有引入"stage→checks→gate 策略"的注册表让两路消费同一清单。
- 修复方向:建 check registry(每 stage 声明检查集+分档策略),`run_pipeline` 与 `validate_case` 都从注册表驱动;加一条 parity 单测(断言两路检查集合相等,豁免项显式登记)。这是防"桶③第二次打开"的结构解。优先级:高(A2 两个缺口的根治形态)。

**A1-3 · judge/重抽隔离是 prompt 级不是机制级(污染面)**
- 现象:盲重抽/reread 的"盲"靠指令自觉——重抽子代理物理上可达 gt/旧 attempts/judge 评语(用户已定待改,memory 在册)。本次体检把它升格为**架构级**问题:judge=数据工厂战略(verdict 当训练标签、错类固化成确定性校验)的全部价值都建立在"评测未被污染"上,prompt 级隔离撑不起这个承诺。
- 修复方向:重抽器只暴露 images+skill 的隔离工作区(目录级白名单,gt/attempts/verdict 物理不可达)。优先级:高(在跑任何"作数"的对照实验前落地,否则 Haiku/4.6 这类 A/B 的可信度都带折扣)。

**A1-4 · 有意为之、无需动但要点名的两处架构张力**
- IntakeOutput 走 NL specs 文本、下游 LLM"忠实誊写"——确定性真值穿过一层随机誊写员才落 IDF,由 InterZone 门兜底。这是 fork (a) 的自觉决策(契约不动、下游不动),idfpy 切换是其既定解;体检确认该 seam 当前由门兜住、无活跃出血点,**不建议现在动**。
- 确定性阶段 2/3 无 per-run judge(J23 defer)——与"确定性阶段靶子是代码"的原则自洽;几何保真靠人工 viewer,C2 之后随复杂度重估即可。

**A1-5 · 架构健康面(正面清单,防止体检只见病)**:gt 隔离铁律代码级清白(A2 独立复核);attempts append-only+hash 绑定闭环成立;correction image-blind 边界未见破坏;`Cons_InterFloor` 类"结构性 obviate"是约束迁移的最优形态(A3#3);[interzone.py](src/validator/interzone.py) 已非正交就绪,是 C4 的现成参照。

---

### A2 · 0–5 端到端工程诊断

> 取证方法:子代理逐项核对 validate_case 与 run_pipeline 的检查清单、run_profile 分档、manifest、gt 隔离、provenance、悬空件,全部 file:line 实证。**parity 全表见文末附录 A2-T。**

**A2-1【HIGH·真缺口】0_reading 结构化不变量在生产路径被静默丢弃(6/~15)**
- `check_reading_view`([checks/reading.py:87-152](src/validator/checks/reading.py#L87-L152))产 ~15 个 check_id,多数是 INVARIANT(按 [schema.py:143-144](src/validator/checks/schema.py#L143-L144) 应无条件 BLOCK)。`validate_case` 全量跑([validation_run.py:128-140](src/agent/execution/validation_run.py#L128-L140));但 `run_pipeline` 只经 `compute_evidence_debt_from_vector_dir` 间接跑一次,随后 `project_evidence_debt` **只保留 `EVIDENCE_CHECK_IDS` 6 个 id**([evidence_preflight.py:96-99](src/agent/execution/evidence_preflight.py#L96-L99)),其余(含 `stroke_ids_unique`/`pen_kind_valid`/`no_topology_fields`/`nondegenerate_geometry`/`axis_endpoint_consistent` 等硬不变量)**不 raise、不 warn、不落盘**。
- 后果:同一份 0_reading 产物可以 validate_case 判 blocked、run_pipeline 无感放行进 1_correction。
- 定性:**"口径齐 validate_case"的声明在 0_reading 段不成立**。说句公道话:桶③的声明范围是 correction/kernel/mep/assembly 四段(那四段确实齐了,A3 与 A2 双路一致),reading 不在其列——但 checklist 问的是"真的一致吗",答案是:**按段算 4/5 齐,按检查算 reading 段漏 9 个**。
- 修复方向:run_pipeline 对每 view 直调完整 `check_reading_view` 走 `_gate_self_check_report` 模式(与 A1-2 注册表方案合并做)。

**A2-2【HIGH·结构性隐患】S5 `check_assembly` 报告在生产路径从未被门禁消费**
- `run_pipeline` 计算并落盘 `assembly_report`([pipeline.py:1011-1017](src/agent/pipeline.py#L1011-L1017)),但全文件 `_gate_self_check_report` 只有 correction/kernel/mep 三处调用(行 917/953/994),assembly 缺席;真正 raise 的是旁路的裸 `validate_contract`([pipeline.py:1018-1028](src/agent/pipeline.py#L1018-L1028))。
- 当前行为恰好等价(check_assembly 目前只包 validate_contract 一个 check),**无活跃 bug**;但未来任何人往 check_assembly 加新 check_id,生产路径会静默失去强制力——典型的"看起来接了、其实是死代码门"。
- 修复方向:assembly 接入 `_gate_self_check_report`,与裸 `validate_contract` 共享同一次结果。

**A2-3【MEDIUM·半设计内】默认 exploratory profile 把 INVARIANT 的 BLOCK 软化为 warn**
- `disposition()` 对 INVARIANT 无条件 BLOCK,但 `_gate_self_check_report`([pipeline.py:735-765](src/agent/pipeline.py#L735-L765))仅 golden/regression 才 raise;`run_pipeline` 默认 `exploratory`([pipeline.py:774](src/agent/pipeline.py#L774)),违规仅 log warning 后照常产出 IntakeOutput。`validate_case._finalize` 则不看 profile、blocking 非空即 blocked([validation_run.py:317-321](src/agent/execution/validation_run.py#L317-L321))。
- 定性:分档本身是既定设计(exploratory=可见续行),S5 contract 全 profile 硬 raise 证明作者知道哪些该无条件硬。但净效果=**默认档下"生产 run 成功"与"validate_case 通过"对同一数据可给相反结论**;dev/baseline 流程都走 validate_case 兜底,真实暴露面是"不跑 validate_case 的裸 intake_node 调用方"。
- 修复方向:二选一——纯 INVARIANT(非证据类)违规全档硬 raise、分档只留给证据类/CROSS_CHECK;或生产入口默认档位升档。倾向前者(与 INVARIANT 语义自洽)。

**A2-4【MEDIUM】`derive_facade_frame` 悬空确认 + 状态更新**
- 全仓库零调用点确认(唯一提及是 [checks/correction.py](src/validator/checks/correction.py) docstring,未 import);**状态比 memory 记录更好**:E/W sign 已在 `23a0e47`(6.30)翻正且有 gt 锚定测试,"sign 与活口径相反"已过时,剩下的只是接线。修复方向见 A1-1。
- 同类悬空扫描仅另得一件:`RunPolicy.reading_runner_ladder`([policy.py:56](src/agent/execution/policy.py#L56))**零消费**(无写入无读取)——要么删,要么按 run 溯源要求补写入点。

**A2-5【LOW·已知欠账坐实】provenance 自动采集为零**
- `run_config.yaml` 全仓库**只有读取点没有写入点**(`load_run_config` 缺文件即 warn+软降级,[run_config.py:117-125](src/agent/execution/run_config.py#L117-L125));`record_baseline` 对缺失模型字段一律填 `"unknown"`;`git_sha`/`is_dirty`/skill 内容哈希 **grep 零命中**。
- 即:run 溯源当前 100% 靠人手按 SOP 填,无自动兜底、无 fail-closed 存在性校验。与 memory `run-provenance-recording-requirement`(用户硬纪律,等 sm24 后做)一致,本次坐实其代码现状。修复方向:`record_baseline`/run 入口自动采集 `git rev-parse HEAD`+`git status --porcelain`+`skills/intake_pipeline/`+`src/agent/reading/` 内容哈希。**建议提前于"下一次作数的对照实验"完成**(与 A1-3 同理:归因基建先于实验)。

**A2-6【清白项】**gt 隔离(机械扫描+独立 grep 双核,`run_stage.py` 的 gt 引用全在 judge packet 构建路径内延迟 import,注释明示"gt is judge-only");attempts append-only(`new_attempt_dir` 最小未用序号+已存在即 raise,accept 只动指针不回改历史);judge_packet 与 accepted attempt 物理同目录绑定,闭环成立。

**附录 A2-T · parity 对照表(validate_case vs run_pipeline)**

| 阶段 | 检查 | validate_case | run_pipeline inline | 结论 |
|---|---|---|---|---|
| 0_reading | `check_reading_view` ~15 id | ✅ 全量每 view | ⚠️ 仅 6 个(evidence 投影) | **A2-1 缺口** |
| 1_correction | `check_correction` | ✅ | ✅ (`_gate` 分档) | 齐 |
| 1_correction | `check_evidence_debt_coverage` | ❌(内含于 check_correction,行为不丢) | ✅ 额外 pre-core 跑 | 不对称,非缺口 |
| 2_modelling | `check_kernel` | ✅ | ✅ | 齐 |
| 2_modelling | `kernel.artifact_consistency` | ✅(stale 检测) | —(现写无 stale 概念) | 设计内 |
| 3_split | specs 一致性 | ✅ | —(现写) | 设计内 |
| 4_mep | `check_mep` | ✅ | ✅ | 齐 |
| 5_intake | `check_assembly` | ✅ 且统一强制 | ⚠️ 算+写盘但不门禁,靠旁路 validate_contract | **A2-2 隐患** |
| EP | `check_ep_baseline` | ✅(有 ep_end 时) | — 超范围 | 设计内 |

---

### A3 · 脚手架迁移完整性——独立第四路裁决:**复现 GO,不挑战**

第四路方法(与前三路血统隔离:前三路均 Codex,本路 Claude 系子代理独立取证):不按 ledger 条目走,直接从 `git show 127ba06` 的旧 phase2 `rules.md`(458 行)+`prompt_template.md` 与 `old_scaffold_127ba06/` 三件套原文**重新自建约束清单**,再逐条在当前 HEAD 找落点;既有三份审计的抽验项在当前 HEAD 重跑等价 grep/read(既有审计基于旧快照,须确认未被后续提交推翻)。

**裁决:复现(REPRODUCE)。** 未发现任何"曾被有效执行、现在无处执行"的约束。要点:

1. **四条原始 ❌ 遗漏(S4-07/S4-12/#9/#5)+ 三条补修(S1-09/S1-18/S23-16)全部代码级验证为真修复**,非仅文档声称——如 S4-07 People activity schedule 门在 [mep.py:418-449](src/validator/checks/mep.py#L418-L449) 且真在调用链上;S1-18 四个 residual 槽是诚实 `NOT_APPLICABLE` 占位([correction.py:43-46](src/validator/checks/correction.py#L43-L46)),非假装实现。
2. **一处既有记录已过时(好消息方向,但有新账)**:上次终审 GO 的 caveat"run_pipeline 自校半拉子"按其**原口径**(correction/mep 未 inline)应撤销——当前 HEAD `run_pipeline`([pipeline.py:902-1023](src/agent/pipeline.py#L902-L1023))已把四段检查 inline,第四路独立证实。**但注意**:A2 取证同时发现两个**不同口径**的新缺口(0_reading 段 6/15 投影 + S5 门禁死代码,见 A2-1/A2-2)——撤旧 caveat 的同时应换记这两条,不是"从此无账"。
3. **一处比 ledger 更强的保证形式,值得记录**:旧 §5.1"InterZone 两栈构造必须互逆"在新架构下不是被"检查"迁移,而是被**结构性 obviate**——[specs.py:110-129](src/agent/geometry/specs.py#L110-L129) 硬编码 `Cons_InterFloor` 常量,LLM 无法 per-pair 覆盖,代码路径不可能产生违例。这是"约束迁移"的最优形态(检查→不可能出错的构造),ledger 未点破这一层。
4. **旧 reading 三件套内容 100% 保留**(逐字 diff),新增全是加固——独立证实"~95% 相同、差异方向是加固非流失"。
5. **两处真实行为差异,均为有意、非流失,但留观察点**:
   - `mep.name_charset` 从旧硬 block 降级为 CROSS_CHECK flag([mep.py:208](src/validator/checks/mep.py#L208))——三轮审计一致认定故意放宽,本路同意(EP 实际容忍更宽字符集,引用漂移由 cross-field 一致性兜底);
   - `uncaptured` 从"非空必填"松到"可空列表"——理论上模型可用 `[]` 蒙混排除项;现无滥用证据,**建议留一个观察点**:若发现模型系统性空列表掩盖,把"识别到家具/门但 uncaptured 为空"升为独立 CROSS_CHECK。
6. **S1-10(非矩形 cell)/S1-12(derive_facade_frame)确认是真实 Phase B 缺口但诚实披露**(schema 注释、kernel 非矩形显式 NA 不假装通过),且**无其他约束被连带静默挂起**(专查了 coverage_completeness:仅矩形 profile 生效、非矩形显式 NA)。

**修复方向**:本项无需修复动作;两个流程性收尾——① 在管理文档撤销"run_pipeline 自校半拉子"过时 caveat(同时换记 A2-1/A2-2 新账);② uncaptured 空列表观察点记入 backlog。**迁移完整性问题维持关闭。**

---

## B 未来(分阶段方案)

### B1 · 建筑复杂度 C2/C3/C4 → 0–5 各阶段升级方案

**总裁决**:`pipeline_0-5_capability_upgrade_suggestions.md` 的 §0–3 路径骨架(C2→C3→C4、内核先行、合成用例打内核)方向正确,**予以确认**;但它只覆盖 0–3 + 少量 4_mep,**漏了三个必须同步升级的子系统:gate② 判卷模型、gt/答案模型、5_intakeoutput 契约演化**。本节按阶段补全成完整矩阵。

**总原则(每档不变)**:内核先行(手搓 CorrectedGeometry 合成用例,InterZone 门 0 issue)→ schema+correction 文档演化 → **gt 模型 + 判卷模型同步升级** → 真实图纸 anchor case → 守卫/门补齐 → 入 test_baseline。判卷若不同步升级,新档 case 就没有自动判据——2026-07-04 的教训(竖向盲区、"补上坐标级判卷才有自动判据")在每一档都会重演。

#### C2(正交多边形 + 多平面立面)——第一战役,内核已半就绪

| 子系统 | 升级内容 | 分期 |
|---|---|---|
| 0_reading schema/脚手架 | 外轮廓折线(polyline footprint)+ 分翼线索进 strokes 词汇;reading_guide 补 L/U 形轮廓识别与"同向不共面立面"的分段描法;**CV 工具箱同步**(见 B2:polygon 掩膜 + per-翼 ROI,勿烤死矩形 ROI) | C2-1 |
| 1_correction schema/判断 | `Cell.polygon` 可选字段(有则优先、无则退回 x/y 矩形)+ **per-floor footprint**(C3 也要用,提前落);窗归翼仲裁进 A3(平面房间布局对位);**`schema_version` 字段落地**(取证已证实:该字段至今不存在,`extra="allow"` 只是兼容不是版本化,详见 C3 节) | C2-1 |
| 2+3 几何内核 | 轴聚类升级为收集全部多边形顶点(正交下仍是 x/y 一维问题);gap_close 的边界从全局矩形改 per-floor footprint 多边形点到边吸附;多边形合法性守卫(自交/退化/非 CCW raise) | C2-2 |
| gate① | **shapely 覆盖完整性门提前到本档落地**(checklist 亦点名):per-floor cell 并集 vs footprint、层间界面配对面并集 vs footprint 交集,差集非空即 block——非矩形后"漏一块"肉眼查不住 | C2-2 |
| 4_mep | 基本不动(zone 列表消费者);朝向相关默认值(如按立面 WWR)留意多平面立面 | C2-3 |
| 5_intakeoutput 契约 | IntakeOutput 11 字段**不动**(几何仍序列化为 specs 文本);surface_specs 的顶点数从 4 变 N,下游誊写协议无须变 | C2-3 |
| gate② judge + 判卷模型 | **判卷 v1 显式声明只支持轴对齐矩形**(judge_grade_model.md §8:平面墙=矩形 gt zone 轴对齐极大区间、立面=cardinal 正交矩形)→ C2 必须落 §8b 的 **segment/polyline 判卷模型**:gt 墙=线段集(带端点),按(方向簇,横向坐标)关联改为按线段邻近关联;立面判卷改沿面局部坐标(设计种子已定:"沿面坐标对斜立面也成立") | C2-2(与内核并行设计) |
| gt/答案模型 | gt.json 从矩形 footprint+轴对齐墙 → 线段/多边形原生;**CAD→gt 工具链(gt_from_dxf)天然支持任意折线,是现成的 gt 升级路径**,先扩 gt schema 再扩判卷 | C2-1 |

#### C3(退台/挑空/中庭/跨层 zone)——内核最大改造档

| 子系统 | 升级内容 | 分期 |
|---|---|---|
| 0_reading | 新 `image_kind: section`(剖面图=挑空 z 证据主源);平面"开洞/上空"标注进 pen 词汇;立面 floor-band 假设放松(CV 的 storey profiler 输出候选而非真值) | C3-1 |
| 1_correction | **`Cell.z_span: [zf, zt]` 可选槽位**(缺省继承所在层)——打破"层=统一 z"的最大一次契约演化;per-floor footprint(C2 已落)承载退台 | C3-1 |
| 2_modelling | `ZoneVolume` 本就带独立 zf/zt,改动小;z-stack 守卫从"层连续"升级为"体块 z 区间合法性" | C3-2 |
| 3_split_pairing | **本档主菜**:墙配对从 by_floor 分组 → **z 区间重叠驱动**(边界线段相交 × z 区间求交,墙在 z 断点竖向切开)——切配第一次从只切楼板扩到**也切墙**;中庭带洞楼板:`_ring_verts` 只取 exterior,须加"polygon 有 interiors → 必须先分解"守卫 + 简单多边形分解步骤 | C3-2(合成用例先行:双层高大堂+单层邻居、中庭带洞楼板) |
| gate① | z 区间守卫;带洞楼板分解完整性(分解片并集=原多边形);退台屋面/悬挑楼板判定(已就绪部分补真实 case 验证) | C3-2 |
| 4_mep | 露台=上人屋面构造语义;挑空大空间的 people/lights 密度语义(双层高体积) | C3-3 |
| 5 契约 | 不动(specs 文本容纳任意面片) | — |
| gate② 判卷 | **立面判卷的 floor-band/楼层线模型必须放松**:退台后"一条楼层线横贯整面"不再成立→楼层线判定改 per-段;挑空 zone 的平面判卷(一个 cell 覆盖两层平面)需 gt 带 z_span | C3-2 |
| gt 模型 | gt schema 加 per-floor footprint + z_span + 洞;剖面图 gt(楼层线/挑空范围) | C3-1 |

#### C4(斜交墙)

| 子系统 | 升级内容 |
|---|---|
| 0_reading | 斜向尺寸链/角度标注识别;CV 工具箱 Hough/LSD 角度聚类档启用(B2 已预留) |
| 1_correction | 核:轴吸附从 x/y 两组一维 → 方向角聚类分簇后沿墙向/法向一维吸附;`Window.facade` 枚举退化 → schema 演化 `wall_ref` 或方向角 |
| 2_modelling | `_find_parent_wall`/`_window_verts` 的轴对齐残留(常数 x/y 平面、span=x/y 区间)改线段投影参数化 |
| 3_split_pairing | shapely 运算本就方向无关,预期改动最小 |
| gate②/gt | 判卷墙关联按方向簇+点到线段距离;gt 线段原生(C2 已铺路) |

**与不变量 #6 的关系**:上表全部走"schema 加槽位 + kernel 扩展 + 判卷/gt 同步"——无一项需要推翻判断-几何分工、单一世界坐标或 IntakeOutput 契约。**真正的风险点在 C3 切墙**(切配算法性质变化最大)和**判卷模型的矩形烤死**(v1 明示不支持,若 C2 前不重构判卷,新档 case 全程无自动判据)。烤死假设的具体点位清单见 C3 节(代码级取证)。

**依赖与推荐次序**:C2 内核现成度最高、真实需求最广 → **先打 C2**;其中 shapely 覆盖门、per-floor footprint、gt/判卷 segment 模型三件是 C3 的直接地基,C2 落完 C3 的增量就只剩 z 维。再拓扑支线与 C2 的关系见 B3。

---

### B2 · reading 上 CV:方向裁决 + 风格泛化 + Phase B/C 衔接

**对 codex_cv_plan.md 的总裁决:方向、工具清单、风格泛化税目表、分期(C0–C6)全部认同,采纳为施工蓝本**;它的工具箱设计(12 件套、每件带 schema 落点+失败模式)和风格变异轴(9 轴带缓解/兜底)超出了本轮需要重抠的粒度。以下是它没有替你拍板的**四个方向性裁决** + 两处挑战。

**裁决 1:定位 = Phase B 的算术下沉载体,不是 Phase C**(答其 open question #10)。
`reading_improvement_methodology.md` §4 已定:Phase B 的"算术下沉"具体形态就是 CV 工具箱(anchor_px 由 profiler 填实,禁 VLM 尺寸链累加)。所以不存在"先 Phase B 再 CV"的顺序问题——**CV 工具箱就是 Phase B 的施工形态**。Phase C(学习型 CV/完整 OCR 前端)维持 deferred,codex 方案的 C6 门槛("学习型必须在风格桶全面胜过经典 CV 才转正")采纳。

**裁决 2:sidecar 先行,双通道 schema 随后**(答其 open question #1)。
C0–C2(其分期)以 evidence sidecar 落地,不动 reading schema 契约——理由:(a) 早期实验免于 schema 审+重录 baseline 的重成本;(b) sidecar 本身就是审计件,符合"工具输出=证据非真相源"的 Phase A 精神。**双通道 schema(`visual.anchor_px` + `metric`)在其 C4 档(算术下沉集成)时正式落**,与 correction 契约更新、evidence 门更新一次过审——这是必然要付的一次 schema 演化,别拆成两次。

**裁决 3:工具放 reading 阶段侧、执行器可调,绝不 judge-side**(答其 open question #2)。
gt 隔离铁律决定了工具箱必须在 gate①/执行器一侧(零 gt 可达);且工具输出要进 attempts 留痕(append-only),供 J0 当 evidence 引用。物理形态建议 `src/agent/reading/cv_toolbox/`(或 scripts 下可调脚本),与 judge 的 scorer(`src/agent/judge/`)严格分树——判卷侧已有自己的度量代码,两边共享算法可以,**共享模块不行**(防止 gt 感知渗入执行侧)。

**裁决 4:gate 政策与验收**(答其 open question #3/#4)。
missing CV anchor:exploratory=warn、golden/regression=等工具箱转正为默认后才 block(转正前 block 会把所有历史 run 打红)。首个验收目标模型:**Haiku 4.5 本身**——它就是已坐实的 0/9·0/15 失败样本,同 case 同判卷尺,scorer 阈值直接用 codex 方案 C1/C2 档的 promotion 线(平面墙 ≥8/9 within-tol 且 extra ≤1;立面窗 ≥12/15 且 extra ≤3,promotion 15/15)。**这是全项目最干净的单变量实验设计:脚手架+模型都钉死,唯一变量=工具箱有无。**

**风格泛化(核心约束)——在 codex 方案之上补三条硬机制**:
1. **风格语料的来源问题 codex 方案没解**:它要求 style-diverse eval set 但没说图从哪来。答案是现成的——**CAD→gt 的 DXF 数据工厂**(`proposals/cad_to_gt_extraction_plan.md`):同一 DXF 可导出多种画风(线宽/填充/图例/有无家具/扫描退化仿真),gt 免费共享。这把"风格桶评测"从"找图+人工标注"降为"渲染参数扫描"。真实扫描件/手绘补少量即可。
2. **每件工具强制声明适用档**(clean-vector / scanned / photo),运行时先过 medium 分类器(哪怕就是 VLM 自报),不适用档**显式降级为 low-confidence 候选**而非硬跑——"确定性工具输出错得很自信"是 CV 引入的最大新风险,宁可空手也不给错锚。
3. **风格桶留 hold-out**:评测桶分"调参可见"与"封存"两组,封存桶只在 promotion 时跑一次——防止工具 recipe 对全部已知风格轴过拟合(sm21 过拟合的教训升一个层级重演)。

**两处挑战**:
- codex 方案 C3(OCR/尺寸链)排在 C1/C2(墙/窗测量)之后,理由是"Sonnet forensics 没用 OCR"。**部分挑战**:对弱 VLM,尺寸数字**抄错**是唯一不可恢复错(方法论 §3),Haiku 的立面 17 extra 说明它连"有多少窗"都测不了,但它抄数字的能力未被单独测过。建议 C1 里加一个**最小 OCR 探针**(只测"弱 VLM 抄尺寸数字错误率"),若错误率高则 C3 提前——别让分期假设未验证就锁死。
- codex 方案把 `quality_overlay_logger` 当普通工具列在最后。**应升格为 C0 的强制件**:没有 accepted/rejected 候选留痕,工具箱一上线,"reading 错"的归因就从"模型看错"变成"模型看错 or 工具给错锚 or 模型选错候选"三选一——不留痕这三者不可分,重蹈"judge 归因假设未验证"的旧坑([[reading-quality-investigation-2026-06-24]] 的教训)。

**与 Phase A/C 的衔接**:Phase A 证据门原样保留,是工具箱的验收 harness(工具箱的产出正好把 A1 链闭合/A2 refs/A6 窗 jamb 门喂饱);Phase A 已知的"完美 reading 误报债"(无 overall/墙厚残差)在双通道 schema 落地时给残差正规通道。Phase C 学习型 CV 只在风格桶实测出经典 CV 天花板后再议。

---

### B3 · 再拓扑(geometry-first zonification)怎么启 + 怎么纳入 pipeline

**定位裁决**:再拓扑 = **kernel 策略替换,非架构推翻**——这在 proposal 里已自洽(zonification 收窄为"平面上新划热区",切配 leg-agnostic 共用)。当前管线"房间即 zone"其实就是谱系里的 `room_identity` 端点,所以启动再拓扑不是"新架构",是**把 zonification 从隐式恒等映射升级为显式可选步骤**。

**纳入位置**:1_correction 之后、2_modelling 之前,作为可选的 **stage 1.5**:输入=snapped CorrectedGeometry(房间 cells),输出=`zonification_output.json` sidecar(zone 底面剖分 + source_room_attribution 分数归属),**不改 IntakeOutput 契约**(proposal §0.3#2 已定)。`method` 提为一等参数(`room_identity`=现状默认 / `perimeter_core` / `use_grouped_rooms`),进 run_config.yaml——与 per-case llm.yaml 同一配置纪律。

**分阶段(采纳 proposal §0.4 交付序,补三处工程锚)**:
1. **P0 觉醒探针(近乎零成本)**:在现有矩形 case 上跑**非阻塞** shapely 覆盖校验报告(§0.4#2)——这一步与 B1 的 C2 覆盖门是**同一件代码**,先以 advisory 形态落地,C2 时提为 block。一件投资两条线收益。
2. **P1 sidecar + 渲染**:定义 `zonification_output.json` schema + diff/渲染件(判卷侧复用 grade 的灰底-产品叠画模型,2D 剖分是最理想的 gt/diff 目标——proposal §7.4)。
3. **P2 perimeter_core MVP**:简单矩形 + 正交 L/U,凹形显式 unsupported;straight-skeleton/Autozoner 只在凹形档引入;用户可确认旋钮(method/进深/朝向桶/例外策略)接几何确认门(viewer 已有,加 zonification preview)。
4. **P3 BEM 保真残差层**:楼层面积/立面外墙面积/WWR/源房→热区映射(§0.3#5)——分区粒度有能耗后果,不是无害实现细节。
5. **P4 use_grouped_rooms**:等房间 cell 拓扑+role 标签可靠(依赖 role phase-2 确定性绑定,proposals/role_binding_phase2.md)。

**与 C2/C3/C4 的关系(checklist 问"再拓扑是否是复杂体量的更优解")——裁决:是部分更优解,但不改变 B1 次序**:
- 再拓扑的杀手锏是**覆盖完整性从"事后查"变"构造不变量"**(平面剖分天生无洞)——恰好是 C2/C3 的首要风险点。所以**启动时机绑 C2 开工**(proposal §9 原判"B5 非方形开工时"仍成立)。
- 但再拓扑**不消灭** C3 的 z 维工程(墙 z-cut、带洞楼板、z_span schema)——2D 逐层剖分+竖向例外(proposal §5)依然要走 B1 C3 那套内核改造。它替代的是"覆盖门"不是"切配"。
- **务实排序**:C2 时先落 P0/P1(探针+sidecar,几天量级),perimeter_core(P2)与 C2 内核并行推进但不互相阻塞;`method` 默认值切换(room_identity→可选 perimeter_core)等双路径对照(沿用 sm20/21 双路径纪律)证明不劣后再动。

**schema/契约变更清单**:zonification sidecar(新)+ method 参数(run_config)+ 几何确认门 preview 件;IntakeOutput/CorrectedGeometry/下游 9 subagent 全部不动。**唯一跨所有权风险**(proposal §7.1 顾虑的契约跨界)在这个纳入方式下不存在——因为切配内核已经在本项目侧,当年"surface 节点归协作者"的边界问题已被 0-5 重构消化掉了。这是 proposal(2026-05-29 写)已过时的一处:**它比当时设想的更容易落地**。

---

## C 补充

### C1 · "模型是杠杆"坐实后,reading 策略的连贯性

**裁决:策略连贯,但重心必须换腿——prose 脚手架投资已到收益天花板,继续加注是死钱;CV 工具箱接棒成为"为弱 VLM 服务"的主载体。**

**对"脚手架托不起弱 VLM"的一个必要精化**(这是与既有结论的分歧点,见总览):Haiku 实验证明的是 **prose 脚手架**托不起弱 VLM——但 Sonnet 5 满分的 forensics 证明它的分数来自**自发写 CV 工具"量"图**,不是"看"得准。换句话说,真正的杠杆变量不是"模型感知力"而是"模型的工具使用能力 + 有没有工具"。Haiku 拿到的脚手架里**没有工具,只有 prose**——所以"脚手架有它托不起弱 VLM 的能力地板"这句话,严格说只对 prose 脚手架成立,对"含 CV 工具箱的脚手架"尚未测试。这不推翻用户裁决(①模型主导 ③CV 提上日程本来就是同一裁决的两面),但把 B2 裁决 4 的实验(Haiku+工具箱)从"锦上添花"升格为**对整个北极星战略的判决性实验**:若 Haiku+工具箱仍归零,弱 VLM 北极星本身要重估(改为"中强开源模型+工具箱")。

**prose 脚手架的死重清点(现在=诊断)**:
- **不该删**:反过度分割条款、坐标硬线、testdata 锚定、一段一笔反例——这些对**强模型**有实证效果(2026-06-25 完整老脚手架对照:同 Sonnet,新脚手架+4 过度分割、老全套 r1=0),删了强模型也退。reading-honest 双通道字段(provenance/confidence/dimension_refs)是 Phase B 双通道 schema 的地基,删=拆自己的路。
- **该冻结不该再加**:prose 强度迭代——N1e 已证 prompt 强弱非杠杆(四臂方差>臂差);"逐条恢复→验证→再恢复"的循环在 2026-06-27 FullRestore + 07-02 Sonnet 5 满分后已完成使命,**边际收益归零**。
- **真死重(可精简,但等 CV 落地后)**:证据门在完美 reading 上的已知误报(无-overall/墙厚残差被判 debt,方法论 §4 Phase A 已知精化点)——这是唯一"因过度约束产生假信号"的部件,修法已定(Phase B 残差正规通道),不必单独动。
- **"先补全后精简"policy 的状态更新**:补全已完成(FullRestore 收口+迁移 GO),现在正式进入"精简待机"——但精简的正确时机是 CV 工具箱转正后(那时才知道哪些 prose 纪律被工具结构性替代,如裁图纪律→crop 工具默认动作)。

**排序(未来=方向)**:① CV 工具箱 C0/C1(B2)——最高优先;② Haiku 判决性复测;③ 双通道 schema(Phase B 正式落);④ prose 精简(工具转正后)。国产/开源 VLM API 接入实验可与 ② 并行——北极星模型的真实能力档位早测早知道。

### C2 · 判卷子系统:模型本身 sound,但对 §8b backlog 有三处修正,对复杂体量泛化=判卷层零准备

**soundness 裁决:v1 在其声明范围内是健全的,且比 backlog 自我评估更好。**代码级证据:
- 移位与变尺寸**已是两把独立的尺**——`position_tol` 与 `extent_tol` 在 [_wall_status_and_drifts](src/agent/judge/reading_score.py#L553-L588) 分别判定,只是默认值凑巧同为 0.30m。§8b"within_tol 区分移位 vs 变尺寸"对**平面墙**其实已成立,真正缺的是立面窗(覆盖率单一判据,along/sill/head delta 只留证据)。
- 墙粒度不一致(§8b Q1/Q3)由坐标聚类+interval-set 并差集处理,"gt 一段 vs 产物两段"有回归测试实证([test_reading_score.py:201](tests/test_reading_score.py#L201))——分段机制本身稳,悬而未决的只是元素计数口径与 status 坍缩(Q2 比例制,维持原 backlog)。
- **§8b"暴力配对换 Hungarian"需要修正**:立面窗配对已经是**穷举回溯 DFS 求最优一对一**([elevation_score.py:572-651](src/agent/judge/elevation_score.py#L572-L651)),不是贪心——不存在"贪心误配"问题,真正的风险是**组合爆炸**(窗数上去后穷举代价指数级;C2 多平面立面窗更多时会先撞性能而非撞正确性)。Hungarian 的价值=多项式化,非纠错。
- 贪心最近邻 `_match_lines` 只用于 footprint 边界;`_match_windows` 是**死代码**(零调用)。

**三个真缺陷(既有 backlog 未记)**:
1. **`win_tol`/`DEFAULT_WIN_CENTRE_TOL_M=0.40` 是死参数**——作为形参出现在 `score_floor`/`score_reading_dir`([reading_score.py:788,850](src/agent/judge/reading_score.py#L788)),但从未传进 `_match_window_segments`(调用处只传 extent_tol/complete_eps)。即**平面窗实际吃墙的 extent_tol,文档语义里的窗中心容差不生效**。spec↔code 漂移,该修或该删。
2. ambiguous 阈值硬编码 0.05([elevation_score.py:780](src/agent/judge/elevation_score.py#L780)),`score_policy` 另有 `EXTRA_MINOR_MAX=2`/`WINDOW_MINOR_RATIO=0.80` 模块常量([score_policy.py:27-28](src/agent/judge/score_policy.py#L27-L28))——config 化 backlog 证实,且范围比原记录大(不止 ambiguous 一处)。
3. correction 侧 flipped 永不采纳、只记 evidence([elevation_score.py:1072-1075](src/agent/judge/elevation_score.py#L1072-L1075))——这与 spec §0"correction 已是世界系、从不翻转"**一致,是对的**,列此仅为确认非缺陷。

**对 C2/C3/C4 的泛化=判卷层零准备(比内核更裸)**:gt/产物墙抽取只认常量 x/常量 y 边([reading_score.py:166-195](src/agent/judge/reading_score.py#L166-L195)),斜墙在打分器里**不可见**;footprint 用 cell 极值 bbox 兜底;立面化简为单一 `span_limit` 数字(无多深度/退台表示);**judge 层零处出现 `capability_profile`/`polygon`**——内核对非矩形至少有显式 NOT_APPLICABLE 豁免,判卷层连豁免分支都没有。∴ B1 表格里"判卷与内核并行设计"不是锦上添花而是硬前置:照现状,C2 第一个非矩形 case 的判卷输出将是**未定义行为而非诚实降级**。修复方向:segment/polyline 判卷模型(§8b 已列)+ 判卷层补 capability_profile 感知(不支持的档显式 NA,对齐内核的诚实姿态)。

### C3 · 契约与 schema 版本化接缝审计:接缝理念成立,但"版本化 schema"目前是纸面承诺

**核心证伪:代码里没有 schema_version 字段。** `CorrectedGeometry`/`BuildingGeometry` 均无 `version`;唯一真实存在的槽位是 `capability_profile: str = "rectangular"`,它贯穿 policy/validator 层但**全仓库只有一处按值分支**([kernel.py:226](src/validator/checks/kernel.py#L226) 非矩形→NOT_APPLICABLE),其余 check 文件只透传进 CheckReport 从不读取;**几何内核三件(`build.py`/`modelling.py`/`split_pairing.py`)对它一无所知**。结论:不变量 #6 的"版本化 schema 是留好的接缝"在文档层成立、在代码层是**未开工的承诺**——C2 开工前第一件事就是把 `schema_version` 真正落进 CorrectedGeometry 并建立分发线,否则"接缝"只是摆设。(接缝①原文 2026-06-11 就建议加 `schema_version`,至今未落。)

**烤死假设点位清单(按松动难度,难→易;完整表见取证附录口径)**:

| # | 点位 | 假设 | 首撞 | 松动难度 |
|---|---|---|---|---|
| 1 | [reading/schema.py:31](src/agent/reading/schema.py#L31) `Facade = Literal["North","South","East","West"]`,correction schema 复用同一 Literal | 每朝向单一立面 + 轴对齐,**全管线最上游的类型根** | **C2**(正交多边形就需"每朝向多段立面",不必等斜交) | 重设计(连带 correction/facade 推导/kernel 窗挂载) |
| 2 | [correction/facade.py:31-44](src/agent/correction/facade.py#L31-L44) `derive_facade_frame` 对一个朝向只返回一个 `base_world` 平面 | 全楼每朝向唯一外墙面 | C2 | 重设计 |
| 3 | [correction/schema.py:71-72](src/agent/correction/schema.py#L71-L72) `footprint_x/y` 单一全局 bbox + [deterministic.py:731-806](src/agent/correction/deterministic.py#L731-L806) 跨层 reconcile/connectivity-close 全程以它为硬锚 | 各层共用 footprint | **C3**(退台后上层外墙偏离全局 footprint,包络协调错位) | 波及契约+核心算法 |
| 4 | [correction/schema.py:36-37](src/agent/correction/schema.py#L36-L37) `Cell.x/y` 必填矩形 + [pipeline.py:315](src/agent/pipeline.py#L315) prompt 明令矩形 cell + `deterministic.py` 全模块只读写 `c.x/c.y` | 矩形 cell(bbox 思维) | C2 | 波及契约(schema 开 polygon 槽 + prompt + 吸附算法改环顶点) |
| 5 | [modelling.py:273-331](src/agent/geometry/modelling.py#L273-L331) `_facade_axis`/`_window_verts`/`_find_parent_wall`:外墙恒 x 或恒 y,同朝向多墙时**静默选最后一个 match** | 轴对齐+单立面(kernel 层) | **C2 即触发隐藏 bug**(L 形房间同朝向两段外墙) | 重设计(窗挂载改线段投影) |
| 6 | [split_pairing.py:54-64](src/agent/geometry/split_pairing.py#L54-L64) 竖直墙配对仅同 `by_floor` 组内两两求交 | 墙配对 by_floor | C3(z 区间重叠的跨层邻接永远查不到→**静默变外墙**) | 重设计(即 B1 C3 的 z 区间驱动) |
| 7 | [split_pairing.py:99-129](src/agent/geometry/split_pairing.py#L99-L129) 楼板/天花只查 `fi±1` + [kernel.py:238-259](src/validator/checks/kernel.py#L238-L259) `_coverage_completeness` **独立重写了同一套相邻-fi 逻辑** | 紧邻楼层索引=竖向邻接 | C3(挑空/中庭跨 >1 层) | 重设计,**且须先收敛双写**(改一处漏另一处=守卫与实现同步漂移的现成隐患) |
| 8 | [geometry_validator.py:49-50](src/agent/correction/geometry_validator.py#L49-L50) `_cell_box` 用 min/max 建 box,完全无视 polygon extra 字段 | 矩形(gate① 层) | C2(polygon cell 流入则 coverage 判定用错误 bbox) | **局部改**(仿 `_cell_polygon` 重写一个函数) |

**两个减轻情节(直接影响 B1 工作量预估)**:
- [interzone.py](src/validator/interzone.py) 已用 Newell 法向+任意平面距离,**不假设正交**——全仓库唯一为 C4 备好的模块,可作其余模块重写参照。
- `modelling.py`/`split_pairing.py` 的核心几何运算本就 shapely polygon-native(L 形合成测试存在:[test_geometry_kernel.py:83-94](tests/test_geometry_kernel.py#L83-L94))。**真正卡死"矩形"的不是内核算法,是喂给它的数据源**(schema 必填 x/y、prompt 只教矩形、correction 核只吸附 bbox 角点)——`polygon` 是个没人会填的后门。∴ C2 的主工作量在 0/1 侧与守卫侧,内核主体改动比文档预估更小,与 capability 阶梯"内核已半就绪"判断一致且更精确。

**修复方向**:C2 开工序 = ① `schema_version` 落地+分发线 → ② Facade Literal 与 `_find_parent_wall` 的多段立面重设计(1/2/5 同根,一起动)→ ③ polygon 数据源打通(4/8/10 同批)→ ④ 双写收敛(7)。#3(per-floor footprint)按 B1 建议提前到 C2 落,免得 C3 再动一次契约。

### C4 · 测试覆盖盲区

**计数核对:属实。**`pytest --collect-only` = 477 = 468+9,与声称吻合。9 个 xfail 全部来自**同一个** `_RERECORD_XFAIL` 标记([test_orchestrate_baseline.py:32](tests/test_orchestrate_baseline.py#L32) + [test_validation_run_baseline.py:26](tests/test_validation_run_baseline.py#L26)),等同一件事解锁:确定性命名后的 sm20/sm21 golden **批次重录**。全是"对 golden run 目录跑 validate_case 精确重建"类,逻辑代码未变、纯 fixture 滞后,strict=True 保证重录后 XPASS 会自动报警。**处置路径清楚,无隐性欠账。**

**已覆盖(反向核实,防误报盲区)**:判卷渲染 19 测逐条断言颜色/虚线/容差带;kernel 五类 invariant 每类有独立触发测试;桶③ correction/kernel 两段有真实 golden-raise 生产路径测试;盲抽"judge 评语不进 prompt"在 harness 与 orchestrator 两层都有断言。

**真盲区(按风险排序)**:
1. **4_mep 的 golden fail-closed 从未被单独触发**——现有 golden-fail 测试全在 1_correction 就退出(mep_checks.json 甚至被断言不存在);4_mep 自查只在 exploratory(warn 续行)路径被测。若 check_mep 门被改坏,golden/regression 是否真拦截**未经验证**。补一个"correction 干净、仅 mep 违规"的 golden raise 测试即闭合。
2. **盲抽的"盲"只在 mock 边界被验证**——全部 flow 测试把 `_make_draw_fn` monkeypatch 掉;接上真实 draw fn 后是否真无前次草稿状态穿越,无端到端测试。另发现 `retry_stage_draw` 在 src/scripts **零调用点**(生产盲抽是 [step_orchestrator.py:251](src/agent/execution/step_orchestrator.py#L251) 自己重写的一份)——又一处双写(与 A1-2 同病),二者逻辑重复但被测的是各自路径。
3. **report_assembly 的三个 evidence 抓取器无任何直接测试**(`_gate_entries`/`_judge_entries`/`_correction_entries` + `ensure_geometry_viewer`)——抓错字段路径时,REPORT.md 的 `[E:..]` 引用会悄悄指向错误证据,而 citation linter 只测格式不测内容。
4. zone_closure 的**面积/周长数值分支**([kernel.py:128-136](src/validator/checks/kernel.py#L128-L136))无专门触发测试(现测只覆盖"整类型缺失"/"zone 未声明")——`_AREA_TOL`/`_PERIM_TOL` 被改坏套件不报警。
5. A2-2 的 assembly 死门同时是测试盲区(无测试断言 assembly_report 的 blocking 会被生产路径消费——因为它确实不被消费)。

**修复方向**:1/4 各补一个负例测试(小);2 补一条不 mock draw fn 的窄端到端(中);3 给三个抓取器各配 fixture 测试(小);5 随 A2-2 修复自带测试。整体看,测试文化是健康的(反向核实通过率高),盲区集中在"生产路径的 fail-closed 分支"与"双写副本",与 A1-2 的结构诊断同源。

---

## D 补充自查(超出体检单,用户 2026-07-06 授权)

> 体检单之外我盘点出四块无人查过的地基,派两路补充取证:D1 环境/依赖/git/誊写 seam;D2 skill 库内部一致性 + prose↔gate 新落差。

### D1 · 环境/运维地基

**D1-1【活雷】根目录 `.venv` 是残缺环境,应删除**
- `.venv/lib/.../numpy/` 目录残缺(连 `__init__.py` 都没有,还混进不相关的 `tinynumpy`),`import numpy` 即 `AttributeError`。权威环境是 `/opt/venv`(Dockerfile:48-51 `UV_PROJECT_ENVIRONMENT=/opt/venv` + devcontainer.json 钉死解释器),当前 PATH 下无害;**但任何走"项目根自动探测 .venv"惯例的工具/IDE/新 agent 会踩中**——本次体检的 C4 取证代理就真踩了。它是某次漏设 `UV_PROJECT_ENVIRONMENT` 的意外产物,不该存在。修法:删 `.venv`,单一来源 `/opt/venv`。
- 注:这条直接解释了"为什么要担心环境漂移"——坑已经咬过一次自己人。

**D1-2【真缺口】`ezdxf` 完全游离于 uv 依赖图外**
- `uv.lock` 里查无 ezdxf(非传递依赖,是彻底缺席);`/opt/venv` 里是手工装的 1.4.4。**全新 `uv sync` 环境跑不了 `gt_from_dxf.py`/`inspect_dxf.py`**——CAD→gt 工具链(未来 gt 生产主路径 + B2 风格语料工厂的依赖)在新机器上静默断裂。修法:补进 pyproject dependencies。
- 次级:`python-dotenv`/`openai`/`attrs`/`langchain_core` 被生产代码直接 import([llm.py:5](src/agent/llm.py#L5)、[pipeline.py:41](src/agent/pipeline.py#L41) 等)但只作传递依赖存在——uv 升级松开引用链即静默失效,应提为直接声明。`click`/`aiohttp` 声明了零 import(可清);`idfpy` 是前瞻预声明(保留)。

**D1-3【降级后的事实】git 运维状态**
- 工作分支与 origin 完全同步,无丢失风险;已跟踪文件零个 >5MB。
- 代理报"本地 main 领先 origin/main 16 commit 未推=潜在丢失"——**主控复核后降级**:merge-base 证实 main 是已推分支的祖先,16 个 commit 的对象早已随分支在远端,只是 **origin/main 的 ref 陈旧**(停在 2026-06-11)。真实事项只有一条:分支对 main 已分叉 **78 commit**、原计划"sm21 批次重录后合并 main"越拖分叉越大;fetch 元数据也两周未刷新。修法:按既定计划推进合并,合并时顺手 `git push origin main` 推平 ref。

**D1-4【虚惊一场+一个真提醒】下游誊写 seam 规模**
- 历史顾虑"64k 截断"**未在生产数据兑现**:实测最大 correction 原始输出 26.5KB(≈上限的 1/10);`geometry_specs.md`/`intake_output.json` **从不回喂任何 LLM prompt**(全仓确认),4_mep 只吃 zone 名列表——**LLM 侧负载随区数扩展、不随面数扩展**,这是当前架构一个未被记录的优点(确定性内核吸收了面数爆炸)。
- 真提醒:截断防线=fail-loud(finish_reason=length→warning→解析失败→3 重试→硬失败),**无分块/升 budget 兜底**。C2/C3 多翼建筑区数非线性增长时余量收窄。修法(轻):correction/mep 调用加 completion_tokens 用量阈值告警(≥80% 上限进 REPORT 标记),为复杂度升级预留分块设计位。

### D2 · skill 库一致性 + prose↔gate 新落差

**挂起项现状核实(三个都有明确答案)**:
- **候选 17(guide §4 世界轴 vs image-local)已闭合**——guide §4 现只讲 image-local 规则并明示"世界落位归 correction",与 schema P1b 一致;legacy 字段仅迁移兼容、无 prose 引用。plan.md 里"§4↔schema 对齐留下轮"的记录**已过时,可勾掉**。
- **judge_rubric.md 仍在 reading/correction 执行 skill 目录内**——确认未移出,与 plan 记录一致,真开着。
- **A1 §2.2 sign 表与 facade.py `_CONVENTION` 完全一致**——6.30 翻正的双重确认(与 A2-4 互证)。

**新发现(按严重度)**:

**D2-1【HIGH】尺寸链闭合门静默漂移到文档值的 5 倍松**
- A0 §4 定 `DIMCHAIN_CLOSE_TOL = 10mm`;[reading.py:45](src/validator/checks/reading.py#L45) 注释还写着"A0 OUTPUT_PRECISION / DIMCHAIN_CLOSE_TOL scale",但真正的闭合比较在 [reading.py:669](src/validator/checks/reading.py#L669) 硬编码 `> 0.05`——**50mm,不挂任何命名常数**。
- 为什么重:链闭合门是 Phase A 的第一刀("用已有代码把 silent misread 变 loud"),而尺寸是唯一不可恢复错——这道门比文档承诺松 5 倍,意味着 10~50mm 之间的链误差全部静默放行。且这正是体检反复见到的病根模式(prose↔gate 落差)在 Phase A 之后的**新发**。修法:换命名常数对齐 A0,或改 A0 并删误导注释——二选一,不许两边各说各话。

**D2-2【HIGH】"包络不得全 NoMass"硬规则零确定性门**
- [authoring.md:58-67](skills/intake_pipeline/4_mep/authoring.md#L58-L67) 把它标为 **hard** 并点名 EP 崩溃类后果(warmup 不收敛→severe);但 [mep.py:497-512](src/validator/checks/mep.py#L497-L512) 只查 NoMass 热阻为正,**从不查不透明 construction 至少含一层有质量材料**。这正是 2026-06-11 audit 实测发生过的 draw 波动("sm21 某次 draw 全配 no-mass")——症状在案、规则在案、门缺席。修法:加 `mep.construction_thermal_mass`(每个不透明 CONSTRUCTION ≥1 层非 NoMass/AirGap 的 MATERIAL)。

**D2-3【HIGH】authoring 六项必需 schedule 清单里 3 项从不做引用校验**
- [mep.py:40](src/validator/checks/mep.py#L40) `_LOAD_TYPES` 只走 PEOPLE/LIGHTS/ELECTRICEQUIPMENT;恒温器 heating/cooling setpoint schedule 与 ideal-loads availability schedule 的悬空引用**无人查**(对象本身已被 idf_fragments 解析进索引,只差走一遍)。S4-07 修的正是同一张清单的另一片叶子(People activity schedule),这三片同类漏叶还开着——同属 EP-fatal 类。修法:扩 `_load_refs` 或加 sibling 走 thermostat/ideal-loads 的 schedule 字段。

**D2-4【MEDIUM 三件】**:① `total_floor_area_m2` 仍零校验(确认既有 backlog 现状);② **A0 registry 反向漂移**——`cross_floor_align_tol_m`/`window_snap_grid_m`/`window_clamp_to_parent` 三个真实驱动核心逻辑的容差([deterministic.py:276-835](src/agent/correction/deterministic.py#L276) + config.py 序不变量)在自称"单一真源"的 A0 §4 里**没有条目**;③ guide §0.1 的 testdata 锚定交叉核**结构性无门**——`check_reading_view` 签名根本没有 testdata 参数,连日后加检查的管道都不存在(可机检:描边范围 vs testdata 总尺寸)。

**D2-5【LOW】**:`self_check.pens_used` schema 声明了但从不与实际 strokes 对账;过度分割通用规则只有窗 jamb 窄门(其余归 J0,定性合理、记录在案即可)。

**D2-6【卫生】**:`skills/intake_pipeline/README.md:8-9,26-28` 带时间戳/改名史/归档指针,违反 skill 库自己的"英文纯当前 spec"政策;4 个 spec 文件首行有中文阶段别名注(政策字面违反,但读起来像有意约定,轻)。reading 三件套里的中文字形是图纸内容示例,合法,已排除。

**未误报确认**:S1-18 四个 residual 占位=诚实 NOT_APPLICABLE(与 A3 互证);A0 核心六常数与 correction.yaml 1:1 无漂移;interzone `_AREA_REL_TOL` 是另一概念非撞名。

---

## 总览:Top 风险清单 + 与既有结论的分歧点

### Top 风险(按严重度)

| # | 风险 | 严重度 | 锚点 | 一句话修法 |
|---|---|---|---|---|
| 1 | **生产路径静默丢弃 0_reading 的 9 个不变量检查**(validate_case blocked 的产物,run_pipeline 无感放行) | HIGH·活跃 | A2-1;[evidence_preflight.py:96-99](src/agent/execution/evidence_preflight.py#L96-L99) | run_pipeline 直调完整 check_reading_view 入 gate① |
| 2 | **实验"作数性"三缺口叠加**:judge/重抽隔离 prompt 级(污染)+ provenance 零自动采集(归因)+ 盲抽只在 mock 边界验证(穿越) | HIGH·横切 | A1-3 / A2-5 / C4#2 | 隔离工作区 + 自动采集 git SHA/skill 哈希 + 一条真 draw fn 端到端;**先于下一次作数的 A/B 落地** |
| 3 | **校验体系两路消费无单一真源,已漂移三处**(reading 投影缺口、S5 死门、coverage/盲抽双写) | HIGH·结构 | A1-2 / A2-2 / C3#7 / C4#2 | check registry + parity 单测,根治"桶③再次打开" |
| 4 | **C2 撞墙点其实集中在判卷层与 schema 数据源,不在内核**:判卷零 capability 感知(非矩形=未定义行为)、Facade Literal 类型根、schema_version 不存在、polygon 无人填 | 现 MEDIUM,C2 开工即 HIGH | C2 节 / C3#1-5 | C2 开工序:schema_version→判卷 segment 模型→polygon 数据源 |
| 5 | **世界落位仍在 LLM prose 里掷骰子**,确定性替代品(sign 已修+gt 测试)闲置 | MEDIUM-HIGH·每 run 都付 | A1-1;[facade.py](src/agent/correction/facade.py) | 先作 gate① 交叉校验接线,不等完整 Phase B |
| 6 | **prose↔gate 落差新发三件**:链闭合门 50mm vs 文档 10mm(Phase A 核心门失准)+ 全 NoMass 包络无门(EP 崩溃类,症状 6-11 实测过)+ 恒温/理想负荷 schedule 引用无门(S4-07 同清单漏叶) | MEDIUM-HIGH | D2-1/2/3 | 一个常数对齐+两个小 check,均小工作量大收益 |
| 7 | 4_mep golden fail-closed 无测试;zone_closure 数值分支无测试;report evidence 抓取器无测试 | MEDIUM | C4#1/3/4 | 各补负例/fixture 测试(小工作量) |
| 8 | 默认 exploratory 把 INVARIANT 软化为 warn(裸 intake_node 调用方暴露) | MEDIUM·半设计内 | A2-3 | 纯 INVARIANT 全档硬 raise,分档留给证据类 |
| 9 | **环境/依赖地基**:残缺 `.venv` 活雷(取证代理已实踩)+ ezdxf 游离 uv 依赖图(新环境 gt 工具链断)+ dotenv/openai/attrs 仅传递声明 | MEDIUM·运维 | D1-1/2 | 删 .venv;补 pyproject 声明 |
| 10 | 判卷 spec↔code 漂移与死代码:win_tol 死参数、阈值硬编码三处、_match_windows/retry_stage_draw/reading_runner_ladder、A0 registry 反向漂移三容差 | LOW-MEDIUM·卫生 | C2 节 / A2-4 / D2-4② | 随 §8b 重设计一并清 |

**排序逻辑说明**:#2 排在结构问题前,因为项目当下的主战略(CV 工具箱验收、Haiku 判决性复测、4.6 对照)全是**实验**,实验基建的可信度缺口直接折损每一个后续结论;#1 是唯一"今天就在发生"的活跃行为缺口。

### 与既有结论对照

**证实(独立复现)**:
- 迁移完整性 GO——第四路复现,无有效约束流失(A3);且发现"结构性 obviate"这一优于检查的迁移形态未被 ledger 记录。
- 桶③四段(correction/kernel/mep/assembly)inline 属实;gt 隔离铁律代码级清白;attempts append-only+hash 绑定闭环;468+9 计数属实且 xfail 处置路径清楚。
- "模型能力是 reading 主导杠杆"成立——但见下方精化。
- 判卷 v1 在声明范围内 sound,"内核已半就绪"判断成立且可加码(内核 polygon-native,卡死在数据源)。

**挑战/修正(七处)**:
1. **"run_pipeline 口径齐 validate_case"不完整**——0_reading 段 6/15 投影 + S5 门禁死代码(A2-1/2);按段算 4/5 齐,按检查算有静默缺口。
2. **"版本化 schema 接缝已留好"是纸面承诺**——schema_version 不存在,capability_profile 全仓库一处消费、内核零感知(C3)。
3. **memory"derive_facade_frame E/W sign 与活口径相反"已过时**——sign 已在 `23a0e47` 翻正并有 gt 锚定测试,剩余问题只是未接线(A2-4)。
4. **§8b"暴力配对换 Hungarian"动机需修正**——立面已是穷举最优,问题是组合爆炸不是误配;平面窗的真问题是 win_tol 死参数(C2 节)。
5. **"脚手架托不起弱 VLM"精化为"prose 脚手架托不起"**——含 CV 工具箱的脚手架未测,Haiku+工具箱复测是北极星战略的判决性实验(C1)。
6. **"run_pipeline 自校半拉子"旧 caveat 应撤销但换记新账**(A3#2)。
7. **capability 阶梯漏了判卷+gt 两条同步升级线**(B1)——不同步则每个新档 case 无自动判据。
8. **plan.md"候选 17 留下轮"已过时**——guide §4 世界轴冲突实际已在 6.27 批次闭合,可勾掉(D2)。
9. **"64k 截断"历史顾虑未兑现且发现未被记录的架构优点**——LLM 侧负载随区数不随面数扩展,确定性内核吸收了面数爆炸(D1-4)。

### 收尾建议(流程性,非本报告执行时点的记录,落地情况见文末附录)

管理文档待同步项:撤旧 caveat 换记 A2-1/A2-2;plan.md 勾掉候选 17;memory `derive-facade-frame` 条目更新(已做);uncaptured 空列表观察点、win_tol 死参数、阈值 config 化、A0 反向漂移三容差并入 §8b/相应 backlog;skill README 卫生清理。

修复批次建议:
- **批次零(顺手级,半天内)**:删残缺 `.venv`;ezdxf/dotenv/openai/attrs 补 pyproject;D2-1 闭合门常数对齐(一行改+一测)。
- **批次一(实验基建,先于一切作数对照实验)**=风险#2 三件(污染硬隔离/provenance 自动采集/盲抽真端到端)。
- **批次二(口径收口)**=风险#1/#3/#8 用 check registry 一把解;D2-2/D2-3 两个小 check 顺批并入(都是 check_mep 加叶子)。
- **批次三(小测试补丁)**=风险#7 三件。
- C2 相关(风险#4/#5)按 B1 开工序走;git 分叉收敛按既定"批次重录后合并 main"计划,勿再拖大。

---

## 附录:修复落地记录(2026-07-06,报告交付后同日执行;本节只记进展,不改上文诊断)

用户授权用剩余额度按报告修复批次开工,Claude 编排/Codex 双审执行,四个模块落地(测试 468→489 绿 + 9 xfail 不变,commit `fea6981`/`2661fd4`/`41f842d`):

| 模块 | 对应风险 | 落地内容 |
|---|---|---|
| M1 口径收口 | #1/#3 | run_pipeline 内联完整 S0 `check_reading_view`(聚合 `0_reading/reading_checks.json`+profile 分档门,A8 sidecar 时序保留);S5 `check_assembly` 接入分档门(contract 保持全 profile 硬 raise、单次计算);**`tests/test_check_parity.py` parity 锁**(豁免表显式登记) |
| M2 三道门+批次零 | #6/#9 | `DIMCHAIN_CLOSE_TOL_M=0.010` 对齐 A0(执行前实证扫描:(10,50]mm 区间 0 条=收紧免费);新 `mep.construction_thermal_mass` + `mep.hvac_schedule_refs`(非空引用必须可解析;heating/cooling availability 字段 defer——旧 run 存在字段错位,记 backlog);pyproject 补 ezdxf/python-dotenv/openai/attrs、删 click/aiohttp、`testpaths=["tests"]`、删残缺 `.venv` |
| M3 provenance | #2 之一 | `_run/baseline.json` 新顶层 `provenance` 块(git_sha/git_dirty/dirty_paths + skills_intake/reading_src/correction_src 目录哈希 + correction_config 哈希;git -C 仓库根锚定;软降级;**无时间戳字段保幂等**);REPORT GEN 加摘要;删零消费 `RunPolicy.reading_runner_ladder` |
| M4 测试补丁 | #7 | 4_mep golden fail-closed(自然违规)、zone_closure 面积数值分支、report_assembly 三个 evidence 抓取器 + viewer smoke |

**过程发现(自证价值)**:pytest 一直在收集 `backup/` 里的备份副本(无 testpaths)——执行器的"目标测试绿"曾部分测在备份副本上;`testpaths` 钉死后现形 2 个真失败(M2 新门正确抓住 M1 测试 fixture 的全 NoMass 构造)并修复。这正是风险#3"两路/双份漂移"病根的又一实例,也反证 parity 锁的必要性。

**仍未做**(需用户拍板/后续轮次):风险#2 其余两件(污染硬隔离=要专门设计轮;盲抽真端到端)、INVARIANT 全档硬 raise(政策)、check registry 全量重构(parity 锁已降低紧迫度)、判卷 §8b 批(用户既定 Sonnet 4.6 后)、C2 开工序。**同日续批**:CV 工具箱 C0+C1(报告 B2 的第一落地批)已开工,轨迹见 `logs/reviews/{request,verdict,execution}/2026-07-06_cv_toolbox_*`。
