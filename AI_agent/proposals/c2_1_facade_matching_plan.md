# C2.1 规划稿:立面匹配引擎 + 缺立面补(sm26-U,不转)

> **定位**:规划稿(批次拆解 + 接缝 + 依赖/风险),粗到中粒度;供主控裁决与后续 sol 出工程细稿。**非施工合同**——函数签名/字段/逐测试归各批细稿。
> **出稿**:Fable 5,2026-07-19,受 Opus 主控委派;本轮只出稿存档、不走对抗审(用户拍板)。
> **上位**:[c2_full_unlock_design.md](c2_full_unlock_design.md) v2.2(E1'/E2'/E3'/知识库骨架/§T' sm26 验收器)+ plan.md 2026-07-18 单轴爬坡重切块(权威定义,**取代 07-12 旧 C2.1 三件一体定义**——回字形/内院挪 sm27)。
> **接缝铁律**:匹配在**建筑帧坐标**下按几何绑侧,true-north 无关;旋转(C2.2)=全局单 θ 另一步;三轴正交可叠——本批在**不转**的 U 上验匹配器。

---

## 1. 目标与验收 case

**目标**:全部立面**不命名丢文件夹**,系统按几何把每张立面绑到建筑帧某一侧;「立面开放集、放多少=覆盖率多少」输入契约完整落地。缺件补(无立面窗查表补 assumed-z)在 sm26 了断、不拖 sm27(用户 07-18 定)。

**验收 case = sm26-U**(凹口朝南、不转、四标准正投影立面、内壁窗平面必画,画法按上位 §T'),两子 case:

| 子 case | 输入 | 验的轴 |
|---|---|---|
| ① 给全 | 四张立面全给、全不命名 | **只测匹配**:4/4 绑对侧 + 端到端照常全绿。注意:U 形侧翼内壁段在四标准视图全 hidden → 内壁窗(平面读出实体)z 查表补 assumed 在①就要工作(§T' 既有验收,非②专属) |
| ② 不给全 | 抽掉 ≥1 张立面(如东立面) | 匹配(余图)+ **整侧 unobserved**:该侧窗实体由平面证据保留(existence/along/width observed),sill/head NA(unobserved)、z 查表 assumed;覆盖率分母如实缩;coverage/assumed 报告(B5b)可读出「少了什么、猜了什么」 |

两子 case 走同一套机制:**hidden 段内壁窗(①②均有)与整侧缺立面(②)在证据模型里同族**——都是「平面立实体、立面无 coverage → 属性 NA + 查表 assumed」,区别只是 NA 的原因(Vg hidden vs 视图缺席),Va/B4b 已按此建模。

## 2. 现状缺口对账(相对已落 B-M/Va/B5/E4/B4b,本次亲核)

| # | 已落资产 | 对 C2.1 的缺口 |
|---|---|---|
| 1 | B-M manifest schema v1:`direction_source` Literal **已预留 `matcher`** 值域、`view_type` 已含 site_plan(view_manifest.py:345,349) | generator C2 生成域只产 `user/standard_assumption`;**`declared_direction_token` elevation 必填**约束卡死不命名立面 → 需放开「elevation + matcher 源 + token 空」组合(schema 条件约束修订 + generator/ruleset 版本 bump) |
| 2 | ResolvedViewDirection sidecar 接缝已冻结(B-M §3.4,attempt-bound、manifest 永不回写) | 该 sidecar 为 E4 true_azimuth 设计;matcher 结果需**同族新 sidecar**(见 §3.Q4),消费端(Va binding/B5 window_sources)现直接拿 manifest declared direction |
| 3 | Va = 唯一 applicability 引擎,source-aware 两支消费公式已落;**sm26 语义锚已写死**(va_spec §8.2:内壁窗 plan 四项 applicable、sill/head NA、assumed 值不改判) | 逻辑本体基本就位;缺的是「视图缺席=整侧 unobserved」的输入路径实跑验证(机制在,未被真 case 打过) |
| 4 | B5 宿主解析全落:plan 分支全段解析(hidden 不阻挡)、elevation 分支只在 visible 段候选 | B5 resolver 的 elevation source 绑定链假定视图方向已知 → 需改从 matcher sidecar 取 resolved 方向(接线改动,算法不动) |
| 5 | **知识表:`src/configs/knowledge/` 不存在,`window_modules.yaml` 零落地**(全仓 grep 无生产码引用) | **缺件补生成侧完全未通**——plan.md 07-18 明言「须在开 sm26 前核实已通/补上」,本批最大从零件;上位设计已冻结四层 schema+消费分级+`knowledge_ref` 五元组,细稿有据可依 |
| 6 | B5b 未施工(设计定位:coverage 归档 + REPORT assumed 桶 + HTML 三色,只消费 B-M manifest 不再造) | 归 C2.1(07-18 定),整批待做;北 axis assumed-0 已是现成的 assumed 桶首个住户 |
| 7 | B4b 判卷:per-claim denominator/NA 机读、sidecar v8 全身份已落 | 需加「视图绑定正确性」对账维度(§3.Q7);`no_oversplit` v3 永久 NA(体检 §3.2#2)在 U 形照旧要人工兜底 |
| 8 | 体检 F4-1:`judge_score_bindings.json` **无生产者、无 SOP、缺失时静默跳过 v3 判卷**;F1-2:capability_profile 无 run_config 槽位 | sm25-L 必接部分先行手工;**系统化修复纳入本批**(§3.Q7 判断)——不命名立面使 bindings 制作更依赖 SOP |
| 9 | 素材:仓库 sm26 零文件、gt 仅 sm21 | 等用户 sm26-U 图(DXF 图形导出);gt_from_dxf v3 已就位 |

## 3. 关键设计问题与推荐

### Q1 · 匹配问题定义:U 形有几个可命名外侧?

C2.1 域内答案 = **恒四个**:四 cardinal 全投影立面(N/S/E/W 建筑帧)。U 形不增加「可命名外侧」——凹口底墙、两翼端墙都出现在同一张 South 全投影里(不同深度,Vg 已按 skyline 判段可见性);侧翼**内壁**在四标准投影里恒 hidden,不构成第五个「侧」。故匹配问题 = **把 K≤4 张不命名全投影立面分派到 4 个 cardinal 侧**(单射;剩侧=unobserved)。
**扩展点(铁律 #6)**:匹配器接口取「候选侧集合」为入参而非硬编码 4 cardinal——sm27 内院立面 = 候选集加内院环侧 + partial 视图,接口不推翻。局部/内院视图匹配**明确出本批**。

### Q2 · 匹配器管线落位(本批最大架构悬点,细稿必须先裁)

匹配需要两样东西:建筑帧 footprint 的四向投影特征(总宽/层数/层高线)与各立面图的同类特征。footprint 权威来自 correction(尺寸链+确定性核),立面特征来自 reading 观测(image-local)。**推荐:匹配器 = correction 确定性 finalize 链内的新确定性步骤,两阶段时序**:

1. **阶段一(plan-first)**:correction LLM + 确定性核先按平面证据出 footprint(现链路本就 plan 权威,E3' 立面只佐证端点/外包——不给方向标签也能出);
2. **阶段二(确定性匹配)**:纯函数 matcher 拿 ①footprint 四向投影 ②各未绑定立面视图的 reading 观测特征 → 打分绑侧,产 sidecar;
3. **阶段三(立面证据整合)**:既有 elevation 证据链(ViewProjectionFrame 落位、E3' 外包佐证、B5 elevation 分支宿主解析、Va elevation binding)全部改从 sidecar 取 resolved 方向,算法零改。

理由:(a) 不破 correction image-blind——matcher 只吃 reading JSON 数字特征,不看图;(b) 不动 B-M 唯一 emitter/manifest 不可变;(c) reading 零改动——P1b 立面本就 image-local 出观测,方向从来是 manifest 携带的外部信息,现在换成 sidecar 携带。**细稿要落死的**:阶段一→三在 `finalize_correction_draw` 现时序(B5 已拆过一次)里的精确插点;correction LLM prompt 对「方向未定的立面观测」怎么呈现(推荐:阶段一 prompt 只喂平面 + 立面延后;或喂「未绑定立面」并禁其影响 footprint——两案细稿裁)。

### Q3 · 确定性打分器(用户 07-10 定案:几何题、确定性主导;图名/OCR 永远只是 hint)

特征阶梯(上位 E0 表既定序):**投影总宽 → 层结构(层数/层高线) → 窗列指纹互相关**。C2.1 具体化建议:
- 总宽:立面 reading 尺寸链总宽 vs footprint 该向投影宽(N/S 取 x 全宽、E/W 取 y 全宽)——U 形四向宽常两两相等(x 对 x、y 对 y),**只能淘汰轴、不能定侧**;
- 层结构:C2 各层同 footprint、等层数 → 四向同层数,**基本无判别力**(诚实登记,不虚报该级贡献);
- **窗列指纹 = 主判别子**:立面窗列 along 位置序列 vs 平面证据该侧窗 along 序列(B5 plan 分支已把平面窗解析到段/along 区间)互相关;**镜像陷阱**是正对:同轴两侧(如 E vs W)在建筑帧里 along 序列互为镜像,matcher 必须对「正序 vs 镜像序」分别打分——这正是 ViewProjectionFrame S/E 正号、N/W 负号约定的用武之地,细稿必须把号位约定接进指纹比对;
- **裁决纪律**:最优侧得分与次优的 margin ≥ 命名阈值(新容差进 correction.yaml + A0,禁裸字面量)才绑;不足 → conflict → interactive `NEEDS_INPUT` / prior_fill 域内 unresolved-INVARIANT,**不猜**。窗数为零或近对称立面天然歧义 → 走 conflict 是设计内行为(anchor case 素材侧规避,见 §6 风险)。

### Q4 · MatchedViewBinding sidecar(接缝新件)

与 ResolvedViewDirection 同族纪律:attempt-bound 独立 sidecar,`{input_id, resolved_building_direction, method/score/margin 摘要, view_manifest_sha256, 所依 correction output_hash, matcher_version}`;manifest 永不回写(content hash 冻结);消费端(Va elevation binding、B5 window_sources、B4b sidecar 身份、B5b 报告)缺失/hash 漂移 fail closed。**已绑侧后,下游一切行为与「用户命名立面」完全同构**——这是「匹配对系统其余部分透明」的正交性主张,判卷可据此断言(①子 case 产物 vs 假想命名版产物,建筑帧内容等价)。

### Q5 · 知识表与 assumed-z 口径(从零立,但 schema 已冻结)

上位设计知识库节已把四层 schema(dataset/entry/candidate/source)、加载硬门、消费分级(确定性查表 > 有证据筛选 > 禁无证据抽签)、`knowledge_ref` 五元组、z=楼层内模数 + ceiling 守卫、alias/taxonomy 映射全部冻结——**本批照抄落地,不再设计**。C2.1 只须裁:
- 第一张表内容:`window_modules.yaml` 给 office 域 `space_type` → 窗台/窗高模数候选(每 entry 恰一 default);sm26 内壁窗与缺侧窗都从这里取 z;
- 触发点:B5 宿主解析完成、窗实体已立而 sill/head 无任何通道证据 → finalize 内确定性 lookup 填值 + `provenance: assumed` + knowledge_ref;**applicability 不因填值改变**(Va §8.2 已锁:值可 assumed,判卷 sill/head 照旧 NA);
- interactive 模式:候选列给用户(`NEEDS_INPUT` 合同已冻结);prior_fill 默认。

### Q6 · 覆盖率随视图开放集累积(机制已就位,本批是首个真实消费者)

分母链已建成:B-M 清单定「给了什么」→ Vg 定「几何上看得见什么」→ Va 按 opening×claim 判 applicable/NA(unobserved) → B4b per-claim denominator。C2.1 不新建机制,只补两件:① 视图缺席(manifest 无该侧 required_view)在 Va 输入侧的表达要与「有视图但 hidden」区分留痕(报告用语不同:「未提供东立面」vs「该段在东立面中被遮挡」);② B5b 把这条链渲染成人读得懂的 coverage 报告。**「放多少=覆盖率多少」的验收口径**:子 case ② 相对 ① 的 score sidecar,缺侧相关 claim 全部从 denominator 消失、其余逐项相等(可作自动断言)。

### Q7 · 判卷侧与 F4-1 归属(判断:纳入本批)

- **judge bindings 照旧 judge-authored**(gt 权威铁律):view→gt 侧绑定由 judge/人从 gt 独立制作,**绝不消费产品 matcher 输出**——不命名立面下这条纪律更要紧(否则 matcher 绑错、判卷跟着错=洗分)。
- **新增匹配正确性对账**:score 侧比对 product MatchedViewBinding vs judge bindings,出 per-view binding 判定(绑错侧 → 该视图下游窗分自然崩,但要有**独立的绑定级判定**先亮红,免得误归因为窗几何 bug)。
- **F4-1 系统化纳入 C2.1-A**:bindings 生产/落位桥(`score_inputs/view_bindings.json` → `<run>/_run/judge_score_bindings.json`)+ flow 在「gt v3 在而 bindings 缺」时 loud-fail(exploratory 可 warn)+ new_case_guide SOP 节。sm25-L 跑测已手工做过一次素材,本批把它变成有工装有文档的正规流程。F1-2(capability_profile 进 run_config.yaml)同批顺手(体检建议「可 C2.1」)。

## 4. 批次拆解(粗中粒度)

```
C2.1-A (输入契约+判卷工装)
  ├─> C2.1-B (匹配引擎本体+sidecar)  ──┐
  ├─> C2.1-C (知识表+assumed-z 生成侧) ─┼─> C2.1-E (sm26 素材+两子 case 端到端)
  └─────────> C2.1-D (B5b 报告批) ─────┘      (B、C、D 相互无依赖,可并行/任意序)
```

| 批 | 内容 | 动哪些环节 | 依赖 | 档 |
|---|---|---|---|---|
| **C2.1-A 输入契约 + 判卷工装** | ① case_data 组织定案:不命名立面的声明方式(推荐:`case_data` 分文件夹 `plans/`+`elevations/`(+`site/` 槽位留 C2.2),testdata_prompt v-next 立面列表免方向;**布局一次定死,C2.2 只加家族不重排**)② B-M generator/schema 修订:elevation + `direction_source=matcher` + token 空合法化,版本 bump,生成期硬门同步(不命名立面数 0..4、重复淘汰规则)③ F4-1 系统化(bindings 生产工装+落位桥+loud-fail+guide SOP)④ F1-2 run_config 槽位 ⑤(可选顺手)体检 #6 负锁补扫 B2/B-M 老门 | case_metadata / view_manifest(schema+generator)/ run_stage(flow)/ run_config / new_case_guide / 判卷工装 | — | M |
| **C2.1-B 匹配引擎** | 确定性打分器纯函数(特征阶梯+镜像分支+margin 阈值)+ MatchedViewBinding sidecar wire + correction finalize 两阶段时序插点 + 消费端接线(Va elevation binding / B5 window_sources 改取 sidecar 方向)+ conflict→NEEDS_INPUT 路 + 合成 fixture 穷举(U/L、镜像陷阱、平局、零窗立面、K<4) | 1_correction(finalize 时序+prompt 呈现)/ correction 确定性核(新纯函数模块)/ Va·B5 消费接线 / correction.yaml+A0 新容差 | A(manifest 能表达不命名立面) | **L,细稿必审**(时序插点+镜像+阈值是主险) |
| **C2.1-C 知识表 + 缺件补生成侧** | `src/configs/knowledge/window_modules.yaml` 骨架+第一张表(照上位冻结 schema)+ strict loader/硬门 + finalize 内 assumed-z lookup 填值(provenance+knowledge_ref 五元组)+ ceiling/净高守卫 + interactive 候选列举路 + REPORT 认账接缝(D 消费) | 新 knowledge 模块 / 1_correction finalize / schema(Window sill/head provenance 槽已在 v3)/ 4_mep 不动 | — (与 B 正交;A 非硬依赖) | M–L,细稿 |
| **C2.1-D B5b 报告批** | coverage 产物归档(attempt-bound,绑 manifest hash+output hash)+ REPORT assumed 清单桶(机械生成:north_axis assumed-0 即首住户,C 落后窗 z 进桶)+ HTML 人工校验三色(observed/derived/assumed)+ 灰纹 NA 区间 + observed-zero vs unknown-fenestration 区分呈现 | report_assembly / render(HTML viewer/grade)/ 只消费 B-M+Va+B5 产物**不再造** | 弱依赖 C(桶内容),可先落骨架 | M–L,细稿(上位已定位为 L) |
| **C2.1-E 端到端收官** | sm26-U 素材入仓(图+reading+gt v3+judge bindings,用户+主控)→ 子 case ①(全给,验匹配 4/4+内壁窗 assumed-z)→ 子 case ②(抽侧,验 unobserved 覆盖率+报告)→ 覆盖率差分自动断言(§3.Q6)→ record baseline | 全链 + 判卷 + report | A+B+C+D | S 工装 + L 跑测 |

**细稿密度建议**:B 必须完整细稿+对抗审(算法+时序+接缝);C、D 中等细稿(schema 已冻结/设计已定位,主要是落点纪律);A 可拆机械子件(F4-1/F1-2)+ 小细稿(B-M 修订);E 按 new_case_guide SOP 走、不出细稿。

## 5. 接缝登记(与已落系统)

| 接缝 | 方向 | 内容 |
|---|---|---|
| B-M | 修订 | matcher 值域激活 + token-空约束放开 + 分文件夹映射;**manifest 不可变/唯一 emitter 纪律不动**,resolved 方向恒走 sidecar |
| Vg | 只读 | 匹配器不碰可见性计算;绑侧后 Vg visible/hidden 照常喂 Va/B5 |
| Va | 接线 | elevation view binding 的方向来源:manifest declared → matcher sidecar(缺失 fail closed);applicability 逻辑零改 |
| B5 | 接线 | elevation 分支宿主解析的视图方向改取 sidecar;plan 分支不受影响(hidden 不阻挡的既有语义正是内壁窗的通路) |
| E4/B-O | 无交 | 匹配建筑帧内完成,θ 无关;C2.2 叠旋转时 matcher 零改动(正交性主张,C2.2 验收) |
| B4b 判卷 | 扩展 | sidecar 身份加 matcher_version/binding hash;binding 正确性对账新判定;denominator 机制照用 |
| 知识库 | 新建 | 骨架+第一张表;墙厚 prior 阶梯等迁入留后续独立轮(上位既定,不扩权) |
| sm27 | 留缝 | matcher 候选侧集合入参化;view_kind=partial/interval coverage 槽位(B-M §3.3)不启用不删除 |

## 6. 依赖 / 风险 / 正交性

- **外部依赖**:用户 sm26-U 图(DXF 图形导出、内壁窗平面必画、窗列**东西向故意不对称**——见下);sm25-L 先收官(C2 收官是本批开工前提,按 plan 既定序)。
- **风险 1(最大)**:匹配歧义。U 形 E/W 两侧若窗列对称,指纹互相关平局 → conflict 问用户是设计内,但 anchor case 该确定性过 → **素材侧要求 sm26 窗列打破镜像对称**(给用户出图清单加一条);测试族必须含「刻意对称→必须 conflict 不许猜」负例。
- **风险 2**:correction LLM 在「立面方向未定」输入下的行为未知(prompt 呈现两案,B 批细稿裁+首跑 judge 盯);兜底=阶段一 plan-only footprint 本就不需要立面。
- **风险 3**:知识表从零落地,首个消费真 case 就是验收 case——C 批落后先用合成 fixture 打穿 lookup→provenance→报告链,别把首验压到 sm26 端到端。
- **风险 4**:F5-1 型缺锁重演——本批每个新硬门(margin 阈值拒绝、sidecar hash 拒绝、lookup 无默认 INVARIANT…)按 B5 Phase C 标准**细稿点名拒绝分支即配负锁**,验收明写。
- **正交性**:B(匹配)与 C(缺件补)无共享代码面,可并行派工;两者只在 E 会师。D 是纯消费端。**C2.2 不等 C2.1 全收**——C2.2 的输入侧(总图/θ)与本批 A 的 case_data 布局有一处握手(site/ 槽位),已在 A 中预留。

## 7. 与 sm25-L 收官、sm27 总验收的关系

- **承接 sm25-L**:sm25-L 验的是「四标准**命名**立面、无匹配」——C2.1 唯一新轴 = 把「命名」换成「几何绑侧」;sm25-L 首跑还会替本批预验 MINOR-3/B4b MINOR-1 等登记债,其 v3 判卷 SOP 手工经验直接喂 A 批的 F4-1 工装化。
- **交棒 sm27**:sm27 唯一新轴 = 内院立面匹配(candidate 集扩内院环 + partial 视图消费);C2.1 把匹配器接口、B-M partial 槽位、覆盖率分母链都留好缝,sm27 是集成收官不再爆新机制。缺件补在本批了断,sm27 不背。
