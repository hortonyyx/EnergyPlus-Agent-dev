---
name: reading-quality-investigation-2026-06-24
description: 用户顶置 P0：弱模型识图变差诊断；先做 Opus 控变量实验分清 模型弱 vs skill 回归
metadata: 
  node_type: memory
  type: project
  originSessionId: d1f583bf-388f-45a5-b5a9-59b134d10653
---

**2026-06-24 用户定为最高优先级。** 缘起 2026-06-23 sm21 批次重跑（先只 sm21，Sonnet + gpt-5.4-mini 两条 reading 并行）：两条都过 gate① 但 J0（主控）各抓到真识图错、都进 `awaiting_reread`。
- Sonnet 4.6：1f 南带过度分割（家具/尺寸链 tick/窗洞边当墙，8 隔墙 vs 真 2），立面窗数反而满分命中 gt。
- gpt-5.4-mini：平面干净，但 South-F2 4 窗并成 2 + 2f 南带漏 1 墙（4 房→3）。

用户关切：「SM20/SM21 在旧的未规范混沌单步时效果很好，为何单拎出来更简单的 Reading 反而差？」

**⚠️ 诊断修正（2026-06-23 晚，决定性）= 真回归，reading-honest schema 头号嫌疑，非 case×model 非模型弱。用户直觉对、我先前判错。**
- **强线索（非铁证，一环待 A/B 验）**：`smalloffice_21_pre/phase1/{1f,2f}_view.json`（06-09）读的图与 sm21_anchor **md5 完全相同**，1f/2f 各 10 墙、干净 7 区，partition 按"between office 1 and office 2"描述。**但"该 phase1=Sonnet"仅 decision_log 两处文档记载（刻意区分于 05-28 pocv2 的 Opus4.7），产物无 model 字段、git/summary 无 → 无 artifact 硬证**；若实为 Opus，回归论退回"Opus旧 vs Sonnet新"混入模型变量。同模型同满家具图下：**旧 schema(06-09) 干净 / reading-honest 新 schema(06-22 加 provenance/dimension_refs) 后过度分割**(provenance=`dimension_derived`)。**决定性证明=A/B 控变量(同 Sonnet 同图旧/新 schema)，不依赖 sm21_pre 归属。**
- **机理**：新"诚实"字段疑似把模型从"描画出的墙"推向"按尺寸链派生墙存在性"→尺寸段界/窗边造伪墙（诚实机制反噬）。杂物+尺寸链是失败显形场、非根因；触发器是 schema 变更（gpt-mini 另一模型也欠读=跨模型，符合 schema 问题）。
- 先前"case×model 杂物陷阱/非回归"作废（留作排查史）。三模型对比=correction 对比识图共享 Opus4.7、sm20 Sonnet 读干净——降为佐证对照非主因。

**⚠️⚠️ 2026-06-24 A/B 控变量已跑 = 上面的「schema 单因」假设证伪**。单变量隔离（同 Sonnet 4.6 / 同 sm21 1f / 唯一变量=reading skill 版本：当前 reading-honest vs `fa04ef6^`），每臂 2 样本（Sonnet 冷启子代理，隔离 skill 目录、禁读 gt/旧识图/另一臂）。结果：NEW 14/16 墙、OLD 13/14 墙（13–16 重叠、n=2 不显著），**两个 NEW 样本 30 条墙全 `seen`、0 `dimension_derived`**——诊断①推测的"模型用 dimension_derived 给伪墙背书"漏洞根本没触发，头号嫌疑被推翻。原始 8 道南隔墙过度分割在受控隔离下**两臂都没复现**。
- **局限**：n=2 偏小（但"0 dimension_derived"与样本量无关、稳）；任务 prompt 给两臂都注入了"家具进 uncaptured/一条连续墙一笔"纪律（测"schema 是否在已有纪律上额外加重"=否）。
- **真凶重定向**：不在 schema → ① 原 run 经 run_stage 的**实际编排 reading prompt/上下文**（含可能的 testdata thermal_zones 提示）vs 干净隔离 prompt 的差异；② Sonnet 随机性（坏 run 可能是差抽样）。**修法③（收敛 schema 表述）取消**。

**✅✅ 2026-06-24 根因彻底坐实 + 误归因源头定位（attempt 级轨迹，结案）**：查 `run_2026-06-23_sonnet_reading/0_reading/attempts/` 1f 三 attempt = att1 16墙**全 seen** / att2 16墙(15 dimension_derived+1seen) / att3 10墙全 seen(接受但 quarantine,3次预算耗尽)。
- **att1 用全 seen 就已 16 墙过度分割** → 过度分割在 dimension_derived 标签出现**之前**就发生,att2 只是给同样 16 墙换标签(墙数没变)。"schema=头号嫌疑"= **误归因,源头精确 = att2 的 judge 判语原话"provenance='dimension_derived' confirms the mechanism"**——这句 judge 假设被当既成事实传进 plan/memory。att1(all-seen)+A/B(0 dim_derived 仍 14-16) 双重推翻。
- **真因** = att1 judge 原话"6 fabricated partitions from **window edges + dimension ticks**" = Sonnet 满家具图**首抽随机感知失败**,不需 schema、不需 testdata(A/B 没给 testdata 仍 14-16)。已接受产物其实干净(新10/旧11),"变差"印象来自盯中间坏 attempt 而非接受产物;系统按设计工作(judge 抓+reread 16→10)。

**✅ 2026-06-25 Sonnet 强/弱 prompt A/B 已跑（plan N1e，结案=prompt 强度不是杠杆）**：单变量(仅启动 prompt 强弱)、4 冷启隔离 Sonnet 子代理(2弱/2强)、强臂保 image-local 加回[坐标硬线·别指望correction回溯+尺寸链算式入note+testdata面积锚定]、`score_reading_vs_gt` 对账。结论=**强 prompt 无清晰坐标优势**：1f 竖墙偏移四臂一致(0.06–0.18m)、cited 0.36m 谁都没复现；窗最好是 weak_2(弱臂)；run 间方差 > prompt 臂差(同 attempt 级"首抽随机失败"结论)。完整 totals(strong 撞 session limit 后由独立隔离子代理补全): weak_1 墙7/9窗4/15·**weak_2 9/9·11/15**·strong_1 9/9·7/15·strong_2 8/9·11/15 → **弱臂 weak_2 与 strong 持平/更好**。已渲 6 张四臂对比图发用户肉检。
- **副产=抓到并修 scorer bug**：`score_reading_vs_gt` 此前只解析 `geometry.p1/p2`(line)、不认 `rect`/`x_range_m` → rect 形窗**静默算0**；首轮 strong5/7 vs weak0/7 窗是假象(两臂窗 x 一样且都命中、weak 用 rect)。修=`reading_score.py` 加 `_as_segment`(line+rect 共用)+回归测试,341→342。**差点把 scorer bug 当 prompt 修好窗** → 再次印证 [[judge-gt-authoritative-images-auxiliary]] 未验证测量不得当结论。详 logs/review/2026-06-25_sonnet_strong_weak_prompt_ab/。

**✅✅ 2026-06-25 完整老脚手架对照 = 决定性翻案(plan N1e)**：用户要求"先别揣测哪环对应哪退化",拿**完整老脚手架**(`127ba06` 全套 skill+prompt)跑 Sonnet 读 sm21,单变量=脚手架。**r1=墙9/9·偏移0.0m·过度分割+1(视觉≈sm21_pre,首次有 Sonnet 跑达标)**;新脚手架同 Sonnet 过度分割+4。**但 r2 平庸(+5)方差仍在;南窗 r1 错3个(老脚手架没救回窗)**。先量化标杆 **sm21_pre=墙9/9·窗14/15·过度分割0**(以前只"假设干净")。结论=**脚手架退化是墙/结构退化主因且可恢复;窗位残留=模型**。活性成分=老脚手架的"尺寸链逐段转写+算术得坐标"纪律(old_r1 summary 自述)。
- **用户 2026-06-25 据 old_r1 改判 sm21_pre 识图本体=Sonnet**(非 Opus;decision_log 旧记 Opus 05-28 pocv2 从无产物级硬证)。之前"sm21_pre=Opus 故无法分离模型/脚手架"的混淆**就此解除**。
- **杂物消融快筛**:去杂物(只留墙窗)把过度分割 +3.5→+2 但没消除、且去尺寸链致坐标崩 → 杂物=帮凶非主犯。
- **脚手架退化双路审计(Claude+Codex 独立枚举,不映射症状/不开方)**:vs `127ba06` skill 三件套~95%相同 → 退化在 ①启动prompt精简(坐标硬线/testdata锚定/一段一笔反例/doc作用说明全删)②§0.1错误预算软化(`fa04ef6`)③schema↔guide多处不同步(dimensions[]示例没跟P1a/朝向三处口径冲突/uncaptured契约分叉)。合并清单 `logs/review/2026-06-25_scaffold_degradation_audit/RECONCILED_candidates.md`(26条5组+优先级)。**保留**:`fa04ef6` 加的反过度分割条款(Positive test/双通道)是 NEW 强于 OLD 处,恢复时别丢。

**✅ 2026-06-25 续 = P0 脚手架候选已恢复(`6.25_ReadingScaffoldP0Restore`,验证待跑)**:把 RECONCILED P0 恢复进**版本化 skill `guide.md`**(不放回非版本化启动 prompt——那正是退化根因):候选1坐标精度硬线回§0.1·候选2 testdata总尺寸/层高锚定回§0.1(纯交叉校验不抄)·候选4一段一笔加具体坐标(0,0)→(15,0)+新增"窗洞边/jamb当墙"过度分割负例§5·候选12错误预算重锐化("冗余通道=须挣得的唯一逃生口",保 reading-honest 但不让"correction会修"软化坐标)·候选16 `dimensions[]`示例对齐schema P1a(`text_verbatim/value_m/chain_id/role/order`,与测试fixture一致)。**反过度分割条款(候选14)原样保留**。启动 prompt 版本化=新建 `skills/intake_pipeline/0_reading/session_kickoff.md`(durable纪律只recap+指guide.md)、`new_case_guide`附录A缩成单行命令(用户定:纪律进guide.md+新建kickoff文件;judge文档移出推下轮)。342 passed/9 xfailed(纯markdown改)。**残留=经验验证**(冷启隔离Sonnet重读sm21+`score_reading_vs_gt`对账看是否climb到墙9/9·窗14/15·过度分割0)+P1候选(口径冲突消歧/prompt信息密度)。

**✅ 2026-06-25 续续 = 迁移完整性通查(plan N1f,进行中)**:用户澄清"拉齐"真义=**补查 0-5 架构重构对旧脚手架约束/能力的迁移遗漏/污染/冲突(非按版本回退)**;recon 坐实迁移审计只做过 5.12 单步→两步法,**6.10-6.16 两步法→0-5 几何确定性大重构漏做反向迁移审计**(decision_log/logs 无"旧约束→新落点"核对)。基线=两步法 sm21_pre,范围=reading 先行,**多模型双路已落盘**(Codex 49/1/4/2 + DeepSeek v4-pro 58/0/2/0,`logs/review/2026-06-25_reading_migration_completeness_audit/`;DeepSeek 走 .env key+llm.py intake_correction raw client、脚本自读材料**主控遵指令未自查**)。**明天 Claude 综合→RECONCILED + 针对性核 prompt→代码门迁移([需代码核验]项) + ⚠️冲突·斩断桶逐条和用户过取舍·共存(用户定不自决)**。去向四桶=✅已迁/❌遗漏/⚠️冲突·斩断/🗑有意删。

**How to apply（当前=最高优先级,第一阶段目标 Sonnet 干净读 sm21）**：先做便宜的=**逐条排查恢复脚手架候选**(P0 已恢复见上、待验证;余 P1:口径冲突消歧+prompt信息密度),保 reading-honest 架构、保反过度分割条款;再叠 best-of-N/reread 压方差;窗位单列子目标(立面→平面 window-x,可能需强模型/专项)。换模型/SFT 是后手。~~schema 修法③出局;prompt 强度~~——注意:**"prompt 强度非杠杆"指本轮只往新 skill 加 3 句的弱对照;完整老脚手架(整套)确有效,二者不矛盾**。真 lever=攻"窗洞边/尺寸 tick 当墙"首抽失败——杂物/尺寸掩膜 or 局部裁图(原次要**升为主**)/首抽纪律强化窗洞边≠墙/加 reread 预算/换强模型(Opus sm24 一次干净 [[sm24-nonsquare-first-run-2026-06-24]])。**流程教训**:judge 的归因**假设**未验证就成修法依据、传遍文档;judge 假设进修法前必须用 attempt 级事实证。详 plan.md N1d。相关 [[reading-honest-judge-routing-architecture]] [[run-provenance-recording-requirement]] [[sm21-dualmodel-round-2026-06-21]] [[recognition-modeling-capability]]。
