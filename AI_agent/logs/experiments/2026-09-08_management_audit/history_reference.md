# 历史、参考资料与接手记忆审计

日期：2026-09-08。审计者：本轮 `history_audit` 子代理。此文是取证记录，不是新的开工门或常驻管理规则。

## 结论与可信范围

推进困难同时来自真实接线问题、过密的开发验收程序和失真的进度入口。不能把全部问题归为模型能力，也不能把全部旧检查当作无用围栏。旧记录已经多次要求“快跑通”，但核心代码必派工、固定跨模型复审、施工与主控各跑全量等要求仍留在同一套活文档里。当前主目录曾落后施工树，进一步放大了“什么都没做好”的观感。

最新的 `run_win_e2e` 已经过校正、生成 31 扇窗并实际进入建模。当前直接卡点是两张跨层配对面宽约 65 mm，触发项目 100 mm 最短边检查。它不是“完全没有跑 case”，也不是“已贯通 EnergyPlus”。本轮没有重跑模型、全量 pytest 或 EnergyPlus；历史测试数均只作为历史证据。

最需纠正的一项旧结论：GT 中少量坐标没有量化到整毫米，和跨层约 60 mm 的墙轴位置差，是两个量级不同的问题。现有证据不能支持“把 GT 小数清掉，65 mm 薄片就消失”，更不能直接修改已签字答案来获得通过。

## 读取覆盖

### 全文读取的管理与记忆资料

本子代理全文读取了以下资料。最初批量输出有截断的长文件，已按小段补读，未以检索摘要冒充通读。

| 范围 | 全读文件 |
| --- | --- |
| `reference/`，接手时版本 | `InterZone_Surface_Matching_TechNote.md`、`split_pairing_kernel_reference.md`、`drawing_to_model_research_landscape.md`、`open_model_guide.md`、`pivot_criteria.md` |
| `deferred/`，接手时版本 | `idfpy_embed.md`、`token_optimization.md` |
| 日志/档案索引 | `logs/README.md`、`logs/worklog/README.md`、`archive/README.md` |
| `archive/2026-09-08_pre_takeover/` | `CLAUDE.md`、`plan.md`、`decision_log.md`、`repository_README.md`、`guides/codex_execution_protocol.md`、`guides/new_case_guide.md` |
| `archive/2026-09-08_codex_memory/` 全部文件 | `MEMORY.md`、`memory_summary.md`、`energyplus-agent-dev.md`、`energyplus-agent-dev-model-routing-2026-09-07.md`、`energyplus-agent-dev-model-probes-2026-09-07.json`、`manifest.json`、`README.md` |
| 演示区 | `showcase_animation/README.md`、`showcase_animation/prototype/README.md` |

上述接手前原稿共 8 份，另两份 `guides/reading_correction_split_guide.md`（1306 行）和 `architecture/pipeline_stage_contracts.md`（364 行）由同组 `pipeline_audit` 全文读取并报告完成，详见 [管线审计](pipeline.md)。不是遗漏后默认通过。

### 全文读取的近期证据

- `logs/experiments/2026-09-07f_plan_reality_audit/README.md`。
- `logs/experiments/2026-09-08a_w1_s3b_probe/README.md`。
- `logs/experiments/2026-09-08b_wallhunt/README.md`，含勘误附录。
- `logs/experiments/2026-09-08c_window_investigation/README.md`。
- `logs/experiments/2026-09-08i_sliver_trace/README.md`，含与正文结论不一致的末尾附记。
- `logs/experiments/2026-09-08_takeover_validation/README.md`。
- `logs/reviews/execution/2026-09-08a_W1_S3b_ding_execution.md`。
- `logs/reviews/execution/2026-09-08d_wallfix_gpt_execution.md`。
- `logs/reviews/execution/2026-09-08e_window_drift_execution.md`。
- `logs/reviews/execution/2026-09-08f_writer_phase_execution.md`。
- `logs/reviews/verdict/2026-09-08f_writer_phase_ruling.md`。
- `logs/reviews/verdict/2026-09-08g_window_landing_readout.md`。
- `logs/reviews/request/2026-09-08h_pairing_dispatch.md`。
- `logs/worklog/2026-09-08_takeover.md`，为首轮接手记录，之后主代理继续更新。

`logs/worklog/2026-09_plan_log.md` 先检索整份标题，再全文读取其 09-07 第八程归档块（1823 行至末尾）；其余 09-01 至 09-06 正文没有逐篇重读。09-07 至 09-08 最新状态也由接手前 `CLAUDE.md`、`plan.md` 全文和上述执行/实验材料覆盖。

### 历史日志盘点边界

本次 `Path('AI_agent/logs').rglob('*.md')` 文件系统盘点时共 **1106** 份 Markdown，其中已经含同组新增的管线审计；接手时盘点为 1105 份。分组为：实验 162、施工 214、请求 419、裁决 302、worklog 7、两份顶层 Markdown。这个数量随本轮审计落盘继续增长，不作为固定验收数字。

全部文件已按路径/类别盘点，**未逐篇阅读 1100 多份历史日志**。特别是未单独重读所有旧 request/verdict、旧模型能力考试、全部月报、旧备份目录和所有原始实验脚本。历史正文中的旧指令不自动升级成当前规则；也没有修改历史原数据或伪造其验证完成状态。

### 源码与产物核对

沿问题点读取/检索了 `scripts/tool_scripts/run_stage.py`、`src/agent/pipeline.py`、`src/agent/execution/stage_runner.py`、`src/agent/correction/{finalize,chain_replay,chain_provenance,deterministic,multifloor,projection_bridge,as_drawn_windows}.py`、`src/agent/geometry/{build,specs}.py`、`src/validator/interzone.py` 和相应 checks 入口。范围为有关路由、阶段重放、窗配对、薄片门及序列化，不宣称这些大文件全仓代码审查完成。

直接读取最新 run 的 0/1/2 段 checks、校正 output、building_geometry、两张失败面顶点，以及源事实文件的相应墙记录。并交叉核对 `git log` 中最终配对/债退休/建模首跑提交。没有将 GT 输入生产生成链；此次为只读诊断。

## 逐文档处置建议

| 文档 | 可保留内容 | 应删除、归档或改写的现行说法 |
| --- | --- | --- |
| `InterZone_Surface_Matching_TechNote.md` | 互逆引用、面积/共面/反法向检查；配对合法不代表邻接覆盖完整 | 0.1 m 是当前项目门限，不是已证明的 EnergyPlus 通用崩溃界限；50 mm 网格只是旧方案。相同 Construction 只有在层序对称等适用条件下才可满足两侧反向关系，不能一概称“平凡满足反序” |
| `split_pairing_kernel_reference.md` | 确定性造面/切配、共享内核、复杂几何后续接缝 | §2“没有确定性内核”与 §7“已落地并接主线”共存。改成现有实现指针与未实现范围，旧调查留档 |
| `drawing_to_model_research_landscape.md` | 问题拆分和历史调研链接 | BEM-only 不合当前目标；“前沿”“不会被淘汰”“无人做此 niche”等不能作为已验证事实。标历史调研，未来真作选型再核时效 |
| `open_model_guide.md` | 配置按角色/调用通道区分；真实模型 ID 和费用留痕 | 逐步人工批准、已删除 `open_model/` 技能入口、过期供应商限制/型号表、与 `.mcp.json` 相互冲突的配置说明、覆盖式预处理示例均不能照搬；新指南回到现有可配置代码和离线验证 |
| `pivot_criteria.md` | 用真实输入衡量能力、成本与人工干预 | “Opus 不达 90/75 之前禁止开源”、HITL 不可产品化、EP 成功率仍 0 等均过时。目标档模型从首批参与，人工编辑是产品能力；不用旧阈值挡开工 |
| `deferred/idfpy_embed.md` | 未来更换下游库的动机、迁移需要哪些接口检查 | 不能把四月迁移设计当已实现或必做；现码仍有 eppy/converters。协作者物性工作“基本完成”来自用户，未经本轮独立验收，先对接不重做 |
| `deferred/token_optimization.md` | 实验性 token 精简经验；修改前后比较实际输出 | 旧 P0/P1 冻结状态、等待 idfpy 后再全 case 重录不再是当下排期；优化以实测瓶颈触发 |
| 三份日志/档案 README | 现行资料与历史证据分开、实验原件留存、索引职责 | 不再从历史 request/缺锁列表自动生成必清债；日志无需每次重读，不能再有“唯一当前口径”历史 banner 盖过现行管理 |
| 原 `CLAUDE.md` | 用户要求、几何确定性、GT 隔离、如实报告、收工同步 | 500 行上下文里嵌状态、排工、审阅阶梯、死模型名与新旧治理冲突。作为归档；跨模型入口改 `AI_agent/Agent.md` |
| 原 `plan.md` | 可复现 bug 证据、真实产物、必要未完成项 | 700 多行闭环史、F 编号累积账、全量成绩、已反转的“唯一下一步”退出活计划；只保当前目标/实际状态/下一步，按价值重选旧债 |
| 原 `decision_log.md` | 用户决策来源、重要失败经验、历史运行边界 | 不是现行规则入口。部分段落单行数千字，反复用“连续抓 MAJOR”证明审阅机制却未衡量交付成本；保原文追溯，现行决策页只摘有效结论与替代关系 |
| 原 `repository_README.md` | 环境、MCP/IDF/RAG 能力简介与可用入口 | “未来才通过 LangGraph 读图”、完整标准覆盖等与现码/现目标不符；根 README 简洁项目介绍并指向 AI_agent，不在根新增另一套协作规则 |
| 原 `codex_execution_protocol.md` | 有界任务、必要上下文、交接产物、真实验证范围 | 强制所有实改派工、审升一档、固定跨家族、工人全量+主控独立全量、分工身份决定谁能改核心等退出；“工人不 commit”与后附“必须分段 commit”本就冲突 |
| 原 `new_case_guide.md` | 独立 run、真实 CLI、失败分类、生成与 GT 评测隔离、保留产物 | 每个 run 配置重复请批、把多层 judge/人工点都当固定流程、没有 GT 的 case 不上主线等不合混合输入目标；命令以当前代码核准，不复制旧空壳模板 |
| 归档 Codex 项目记忆 | 轻量 BIM、双输入路、物性协作边界、运行模型上限、人工编辑、房间保留、成本/精度评估等 | “Claude 跑完才能接手”“先仅写 private memory 不入仓”已被此次接手及新同步要求替代；开发模型分配是偏好不是强制常驻角色矩阵；供应商额度和价格是有日期的历史资料 |
| showcase 两份 README | 演示打开方法、控制、文件结构 | 镜头 Path 1 Drawing to BIM / Path 2 Drawing to BEM 不是当前图纸/外部体量两条输入路径的开发设计。标演示用途；本轮不改画面、资产或历史成品 |

## 推进困难的证据链

### 治理与真实开发脱节

旧执行协议 §7.5 要求施工交付前全仓、主控合树后再独立全仓，把主控结果称为唯一权威。相关测试选择工具对非 Python 改动可直接落 FULL；共享模块的进口关系又会扩到大量测试。一次改动因此会在施工、返工、复核、合树和收工之间反复付验证成本。

这不是仅凭印象：旧 `decision_log.md` 记载 B5 Phase B/C/D 的生产逻辑多次被审为正确，但以“缺安全拒绝分支锁=未交付”返工；B5 C 补 17 锁后又全量，B5 D 补四个拒绝用例再主控全量。07-19 词汇小批的历史记载为审阅约 94k token、主控全量 5.5 分钟。09-08 writer 修复施工全量 4085/487 秒后，主控又独立全量同一规模。这些只证明额外工作实际存在，**没有足够统一计时数据估算其占全天百分比**。

同时旧史也记录了真正需要修的缺陷：新增 proof 未接跨阶段消费者、凹形极角排序损坏面积、writer 重放比较错阶段、render 仍按旧 reading 字段画空图。旧检查并非全无价值；新体系应按影响选择验证，并尽早用真实产物贯通，而不是用“所有 guard 都有负测”替代建筑输出。

用户 06-20 已要求 memory 同步管理文档；08-18 已要求科研快跑通、产品化后置、不要逐层加规则。后来这些上位指令仍与旧核心代码必派工/复审规则并存。因此此次要移走冲突旧规则的正文权威，而不是只在顶端加一次新 banner。

### 09-07 至 09-08 的实际阻塞逐层出现

| 当时阻塞 | 证据与当前判断 |
| --- | --- |
| 新 evidence chain 已有实现，正式 flow 仍未消费 | 09-07 reality audit 承认原“未动工”错误；当时 `run_multifloor_correction` 的消费还主要在测试。09-08 已完成 flow 路由，不能继续称零接线 |
| 新 as-drawn 被旧 reading schema 当空 strokes/dimensions | wallhunt 的 24 FLAG 属契约错配；“会判零分”后来已撤回，原生 scorer 当时已有高分。现在最新 checks 按产品契约分派，旧字段显式 N/A；N/A 不代表全部新像素检查已完成 |
| 临时树不带 `.env` | 真运行曾缺凭据；共享 editable 安装串树是另外的历史环境问题。源码位置和环境配置需一次核对，不能把哈希哨兵当每步前置 |
| 共线细分点造成 min-edge 拒绝 | corner-only 规整保留曲线、删除冗余共线点，09-08a 清了这一类假短边；不是把真实短折角也删掉 |
| footprint 对齐但 cells 没跟着变 | 不换环撞共底面指纹；只换环出现二层约 0.45 m² hole。真实跨表示几何不一致，后续修复已使最新校正两层 coverage 为零洞/零越界/零重叠 |
| writer 用 legacy 内核复演 as-drawn | 生成成功但无法归档，后续 proof/建模拿不到接受材料。现 `stage_runner.py` 依据 chain provenance 选择对应 replay |
| 造窗后 producer/finalize/replay 阶段不一致 | 窗 floor 补齐时序造成 31 字段差异；JSON list 与内存 tuple 造成 62 容器差异；宿主解析后的 replay 被当作解析前前缀，31−31=0 却要求后缀 31。现已统一序列化比较并返回 pre-host replay |
| 审计空列表与 `relied=td_path.exists()` | 当时造成 `audit_completeness` BLOCK，盲重试不会修固定接线；补窗后 31 条宿主审计使门通过，但“文件存在=几何依赖”语义问题不能宣称已单独修复 |
| 31 窗已归档但影子配对拒 21 | 后续双向配对及物理洞归并落库；旧“下一步改双向”已完成。最新 `rejected_window_ids=[]`、31 窗保留；旧 W#7 无窗台账债已退休 |
| 建模暴露真实短配对面 | 当前剩下的直接阻塞：Z04_Ceiling2 与 Z20_Floor1，65 mm；见下 |

### 65 mm 薄片：已知事实与未证实假说

最新产物：`case_tests/e2e_tests/sm25-L_anchor/run_win_e2e/`。

- 校正输出为 27 个空间、31 扇窗。两层 `correction.coverage` 全零残差。窗宿主/位置证据检查通过。
- 建模有 27 个 zone、208 张 surface；zone closure 和法向检查通过。只有 pairing gate 的两条最短边 issue。非矩形 `kernel.coverage_completeness` 当前为 N/A，不能据此前两项通过称所有空间邻接完备。
- 失败面共处 z=3.6，x 范围 [11.0598,14.8784]，y 范围 [15.99965,16.0646]。差为 **0.06495 m**，面积约 **0.24802 m²**，两面互逆引用。它是有面积的条带，不是零面积退化面。
- `src/validator/interzone.py` `_MIN_EDGE=0.10` 检查所有面，issue 文本含 “EP may segfault”；本 run 没有执行到 EnergyPlus。**项目门拦住**是事实，**此几何必使 EP 崩溃**未经本次验证。
- 09-08i 溯源正文把源事实墙轴定位为 F1 东侧 16.00 m、F2 对应 16.06 m；reading 另外加入约 4.95 mm 残差。F2 吸附命中 F1 西侧 16.0646 m 的近轴，不能把隔着约 65 mm 的另一轴当标定噪声一起吞掉。
- 更早原 `plan.md` F-96 已记原始 DXF 同为 120 mm 厚墙，其位置相差约 60.3 mm；当时实验 0.0604→2 条 issue，归整 0.0600→仍 2 条，0.20 或完全对齐→0。这里是历史测量报告，**本轮没有重新运行 DXF 提取器**；它与此次源事实和几何产物互相支持。
- 09-08i 末尾从“60 mm 恰为半墙厚”和少量非整毫米 GT 坐标推断“GT 面/轴混淆”，但同一报告明示仍待验证，且与正文源事实不一致。该推断不能升级成已确定根因。

建议后续功能开发先做小型离线几何诊断：确认该局部源图意图，以及轻量 BIM 应保留/简化此台阶的策略和用户可见标记；比较工程用途允许的简化与下游有效性。不要先为所有 GT 小数重签一轮，也不要只删失败面或吞房间来制造全绿。

## 新体系需要明确保存的用户要求

1. 核心是通用轻量 BIM，EnergyPlus 为首个下游。图纸/现有 case 与带表皮外部体量是两个输入适配方向，共用建筑表达、几何内核与输出。
2. 保留原始房间、分隔与连接关系。热区合并是下游派生；上下游不要都把 room 与 thermal zone 当同一个不可逆对象。
3. 物性由协作者负责。可共用同套物性作几何比较，但本轮不把旧 MEP/idfpy 稿复活为主工程。
4. 缺信息可以假设、默认、简化；清楚区分 observed、推断和人工修改。人审、直接几何编辑与自然语言修改是产品路线，现有 viewer 只支持查看/确认，写回仍未实现。
5. 产品运行模型可配置，目标档模型从第一批实验参与，运行上限 Sonnet 级；开发模型选择是另一件事。旧“最强完成后才让弱模型参加”的规定已被明确替代。
6. 项目知识和用户反馈必须同次进入仓库管理文档；本地 memory 只留索引。不得把“接手前暂存私有记忆”继续当现在授权。
7. Git 日常操作授权和“收工=文档对齐+提交推送+临时树归位”形成长期约定；不因换模型或收工重复全量。

## 本报告不作的声称

没有新端到端成功、没有新 reading 能力/成本测量、没有验证所有历史 bug、没有对外部模型价格/能力网页重新联网核验、没有把历史人员签字改写成助手签字。旧资料中的源链接作为历史证据保存；本报告仅评价它们在当前管理系统中的职责和与本地代码/产物的对应关系。

## 补充：四份 C2 大规格全文审计

主代理追加分工后，已逐段全文读取接手前 `c2_b2b_detail_spec.md`（1144 行）、`c2_b4a_detail_spec.md`（1414 行）、`c2_b4b_detail_spec.md`（1750 行）、`c2_b5_detail_spec.md`（1616 行），合计 **5924 行**。包含版本史、全部 wire、算法、分阶段施工、负测矩阵、评审裁决和开放问题，未仅按标题提炼。B2b/B4a/B4b/B5 原稿分别为 7 月的 v2/v2/v2/v3；读取对象包含接手时临时参考 banner，其后主代理改为归档跳转。原字节留在 [管理重建原稿](../../../archive/2026-09-08_management_rebuild/original/AI_agent/proposals/)。

对照范围是各稿相关实现入口与关键限制，不是全文件行对行重新验收。没有运行这些规格要求的历史测试矩阵，也没有把历史审阅锁升级为本轮待办。

| 原稿 | 已有实现与保留价值 | 不能照搬的旧状态/限制；处置 |
| --- | --- | --- |
| B2b：外形原子变形 | `envelope_transform.py:736` 的 `apply_v3_envelope_transaction` 已存在；只在证据允许的方向移动共享轴，连带 footprint、cells 和挂靠窗端点，失败留冲突/回滚。先临时 Vg + 宿主解析，变形后重验，最后才物化稳定段引用的思想可复用 | 原稿的特定 draft/final 顺序、旧 helper 版本及“此批不得改哪些文件”不是新产品通用制度。现函数仍在所有层 fingerprint 不相等时拒绝；as-drawn 已经过 projection bridge，自有 `finalize_as_drawn_chain_geometry`，不会再一律进旧包络变形。归档全文，现行架构只指向实际入口和适用范围 |
| B4a：GT v3、DXF、渲染 | `gt_schema.py`、`gt_manifest.py`、`gt_extraction.py`、`gt_render_model.py` 以及候选/晋升工具已在代码中。typed v2/v3 双读、来源/单位/坐标、候选与签字资产区分、动态多段渲染、plan-only 窗 z 可为空均有可复用契约 | “只有 sm21 GT”“sm25/26 尚未来到”“promotion 工具只能未来做”是旧起点。GT 的严格真值规则不能强加给缺信息的生成器。各层外形相同、无孔洞等是这个 C2 profile 的限制；现 validator/extractor 把原完全相同改为 node-join 容差内相同，仍不是任意退台。归档，正式评测按当前 loader/资产状态核实 |
| B4b：段级评分与 applicability | `segment_score.py`、`opening_claim_score.py`、`score_service.py`、`score_schema.py` 已有生产实现；参考证据决定分母、NA 不等于错、部分可见区间按实际长度、没有完整负覆盖不能因未匹配就判多余，这些语义保留 | 原稿统一 `SCORER_SCHEMA=8` 已不准确：当前 service 使用 `ScoreSidecarV9` 与 `finalize_score_sidecar_v9`；旧 V8 和 `SCORE_SIDECAR_SCHEMA="8"` 常量仍保留，CLI legacy cache 为 `LEGACY_SCORE_CACHE_SCHEMA="11"`。不能仅看常量或照抄旧截图结构。四 Phase 的逐字对账、全链旧债、固定 PNG 像素值不是每次产 BIM 的前提 |
| B5：窗来源、宿主与证明产物 | `window_sources.py`、`window_host.py`、finalize/build/writer 已实现。plan 证据可挂不可见内凹段；elevation 证据要可见；窗 span 要由实际 segment 与房间边界完整承载；无完整负证据时另一视图没画不等于不存在。宿主引用、顶点和跨阶段产物应一致，不应静默跳窗 | 每个窗 existence 必须非 assumed、全部楼层外形/方向框一致、跨 room/造面 seam 一律拒绝等仍是现有路径的能力限制，不能说新混合入口已满足。原稿让模型只引用 `src:<64hex>`，现码已加入人可读 `<expected_output_id>/<observation_id>` 翻译，避免要求模型计算它看不到的 raw artifact hash。Fable 最终批准、每拒绝分支逐个独立锁、四层重复全量等退出管理权威 |

### 代码对账的具体结论

1. **新目标与 B5 的缺省策略还有真实距离。** `window_sources.py:1263` 的 `_claim_links` 对缺 existence/source 或 `provenance="assumed"` 拒绝。`materialize_current_ring_va_elevation_bindings`（1646 行起）对所有层逐一派生 fingerprint/family extent 后要求精确相同。`resolve_window_hosts`（749 行起）在有窗时必消费该 helper。体量输入用窗墙比生成假设窗、缺立面也能出模型等能力要另做清楚的生成/派生契约，不能靠在新管理文档里允许假设就宣称代码已放行。
2. **B2b/GT/宿主层的“同 footprint”不是一条统一容差。** B2b 比 fingerprint；B5 frame 比 fingerprint 和 extent；`gt_schema.py:522` 与 `gt_extraction.py:445` 调 `_ordered_rings_equal_within_tolerance`，用 GT 存档的 node-join 值。来源、用途、精度各异。这是后续跨层差异和体量适配需要理解的实现边界，不要求本轮先清掉所有限制。
3. **B4a loader 已实现存档容差重验。** `gt.py:73` 的 file loader 调 `validate_gt_v3(... tolerances=document.generator.tolerances)`；case loader还要求 `human_verified`，包括自定义根。legacy `load_gt` 对 v3 明确拒绝。不能用当前 config 漂移强制所有旧 GT 重新签字；也不能把原始 dict 硬塞旧矩形 scorer。
4. **B4b 内边不是照旧稿只做整条端点反向匹配。** 现 `segment_score.py` 有 per-side/floor 的坐标身份、正交边 atom 切分（`_tile_orthogonal_edges`）及一般边 exact-reverse 分支；参考和产品池不混合。其守恒也已改为 interval ledger 的精确分片，旧 `_SUBINTERVAL_SUM_TOL` 注释明确仅历史 helper 兼容。新文档不应把这些实现退回旧 v2 规格，更无需为了管理清理再造另一套评分器。
5. **B5 源引用的可用性已经改过。** `_translate_observation_reference`（1200 行起）解释模型无法计算含原始 reading bytes 哈希的 locator，接收 `<expected_output_id>/<observation_id>` 后由代码转换；旧 src locator 仍兼容。保留可追溯性的目标，废除“必须让模型直接输出长哈希”的旧交互要求。
6. **源码注释也存在滞后。** 当前 `finalize_as_drawn_chain_geometry` 和 `build_verified_window_inputs_as_drawn` 的部分 docstring 仍写 LEGAL EMPTY SET / `windows=[]`，其函数体与最新 31 窗产物已不如此。此次管理审计把现状记准；这类注释可在后续触及文件时修正，不为它们另开一轮阻塞性施工。
7. **旧 B4b 与 B5 是评价/产物能力，不是整个产品都必须成功到同一状态。** 正式 B5 评分要求受验 artifact contract，不能把未经评分产物宣传为正式成绩；但模型查看、推断输出和评测 N/A 可以明确分开，不必先凑齐所有评测资产才能展示一次有效探索结果。

### 技术纠偏与撤销范围

保留确定性几何、来源与单位、GT 隔离、不能静默吞输出、实际关键关系检查。撤销旧规格的管理权威，不等于批量删除已存在的代码检查，更不等于解除 artifact 身份验证后继续报成功。

历史稿不断扩展“每一条拒绝分支必须有独立锁”“每阶段逐字段逐字节对账”“固定跨模型签字”，使局部窗挂载功能承担源目录、manifest、frame、hash、Va、writer、loader、build、judge、report 全消费者同步。这解释了小改动为何易出现多轮返工，但尚不能据此判断哪个检查应直接删除。后续只针对阻碍真实用例的具体检查评估保留、简化或替换，先拿相邻实际产物验证影响。

不要继承 B4a“GT 缺值不能猜”为生产链普遍禁猜；不要继承 B5“assumed 不能立窗”为体量路线永恒规则；不要继承 B2b/C2 的同层外形作为通用 BIM 架构限制。新产品可以生成显式假设的几何，也须让导出消费者知道它是推断/简化，且继续检查几何有效性。

### 新正文复核覆盖

追加审计时全文复核了新 `Agent.md`、`README.md`、`plan.md`、`project_scope.md`、`guides/{development,new_case_guide,reading_correction_split_guide,session_entry,model_usage}.md`、`capability/README.md`、`architecture/{multimodal_bim,coordinates_and_geometry,evidence_and_evaluation}.md`、`reference/geometry_methods.md`。新正文已清楚区分已实现与目标，并移除历史批次/模型复审作为默认开工门。已向主代理反馈“门窗构建”应改为实际补窗/门类观测区分，以及 B5 assumed/同外形限制需加入能力边界。配置加载实测和远端 Git 状态由主代理负责，本子代理未独立复跑。
