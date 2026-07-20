# C2.2 规划稿:朝向/总图输入进管线(sm26-rotate,U + 旋转 + 补总图)

> **定位**:规划稿(批次拆解 + 接缝 + 依赖/风险),粗到中粒度;供主控裁决与后续 sol 出工程细稿。**非施工合同**。
> **出稿**:Fable 5,2026-07-19,受 Opus 主控委派;本轮只出稿存档、不走对抗审(用户拍板)。
> **上位**:[c2_full_unlock_design.md](c2_full_unlock_design.md) v2.2 §E4(真北=元数据旋转、证据通道阶梯、sanity 硬门、Facade 语义守卫)+ [c2_e4_output_contract_spec.md](c2_e4_output_contract_spec.md)(输出侧已施工落地)+ plan.md 2026-07-18 块(C2.2 定义)。**本稿吸收原 defer 的「总平/真北进管线 + case_data 组织」专场**(plan.md 07-11 提出、原定档「C2 施工全落地后、case 测试前」;连同 07-12「C2 四标准立面+知识表补默认范围口径」并入——后者实体部分已被 C2.1 知识表批吸收,本稿只承接其视图词汇口径)。
> **接缝铁律**:旋转 = **全局单 θ 元数据**,建筑内部恒正交建筑帧;几何/gt/判卷全建筑帧,θ 只在 EP 出口应用(E4 定性,已落);匹配(C2.1)true-north 无关——**本批叠旋转时 C2.1 匹配器零改动**。

---

## 1. 目标与验收 case

**目标**:解决「旋转怎么进管线」的**输入侧**——输出侧契约(Relative 出口 + Zone 零原点 + θ 唯一 owner + S5 override)已由 E4/B-O 批全部落地,现在补:θ 的**证据从哪来、怎么读、怎么仲裁、怎么变成 accepted orientation evidence**。总图(总平面图)作为新输入模态进管线;「总图标注旋转 / 各层平面标注旋转」两条路都在此了断。

**验收 case = sm26-rotate**:与 sm26-U 同一栋建筑(同几何、同立面集)+ 非零旋转 + 补总平图(带指北针)。核心验收主张:
1. **θ 读得出**:总平指北针 → θ 观测(带 uncertainty、provenance=observed/derived)→ accepted orientation evidence → EP 出口 Building.North Axis=θ,无 "ignored" 警告(E4 探针口径);
2. **正交性成立**:sm26-rotate 与 sm26 的**建筑帧产物逐项等价**(footprint/段表/窗/匹配 sidecar/判卷 sidecar),差异仅 orientation evidence 与 EP 出口 θ——此 diff 断言 = 「旋转不污染几何/匹配」的机器证明;
3. **无证据时诚实**:去掉总平重跑 → default 0 + `provenance: assumed`(已落的 prior_fill 路),判卷角度 claim NA——「真值零」与「未知默认零」不混(E4.2 已定)。

## 2. 现状缺口对账(输出侧已落/输入侧空缺,本次亲核)

| # | 已落资产 | 对 C2.2 的缺口 |
|---|---|---|
| 1 | **输出侧全链落地**:`OutputCoordinateContract`、GlobalGeometryRules 切 Relative、Zone 零原点迁移、S4 占位 0 硬门、S5 无条件 override、building-bound 对象审计、E4/B5 双契约 rebind(B5 Phase D 收官) | 无缺口——本批**不碰输出侧**;输入侧只要产出合法 accepted orientation evidence,下游自动吃 |
| 2 | `NorthAxisEvidence` typed value(value_deg/provenance/source_ids/uncertainty/method/frame_transform_hash,schema v3)+ orientation.py 的 `prior_fill_assumed_zero` 机械生产者 | **`accepted_evidence` 这条 resolution_kind 只有形状没有生产者**(orientation.py 自述 "batch does not implement that merge")——多源证据合并/仲裁生产者 = 本批主体 |
| 3 | **gt/判卷侧已备**:GroundTruthV3 有 `north_axis_deg` 槽 + source_refs;gt_from_dxf 已能从 DXF manifest 提北针(gt_extraction.py role="north_axis") | 产品侧读不出 θ → 判卷「gt 有值且产品 provenance 非 assumed 才计角度误差」的正分支从未走过;判卷本体预计零改/微改 |
| 4 | B-M `view_type` Literal 已含 `site_plan`;`direction_semantics/azimuth_deg/semantics_source` 字段族已冻结;ResolvedViewDirection sidecar 接缝已冻结(B-M §3.4) | generator **无 site_plan 映射行**(case metadata 无总平声明词汇);总平的 opening_evidence 语义未定义(应为空/不承载 opening claims) |
| 5 | reading:0_reading schema(P1a 尺寸链/P1b 立面)+ 隔离 spawn 流程 | **无 site_plan 词汇**:指北针怎么观测(glyph 角度+uncertainty)、总平出什么产物 schema、CV 工具箱是否补量角件——全空 |
| 6 | E4.3 证据阶梯与 sanity 硬门在设计层冻结(metadata 显式 > 指北针读数 > default 0 assumed;±2–3° 记 uncertainty 非判卷容差;不 snap 整角;箭头唯一/page rotation 解析/变换 hash/多枚一致/显式 vs glyph 冲突) | 全部**未施工**;E4.4 Facade 语义守卫(`direction_semantics` 机读)已有 manifest 字段但无消费路径 |
| 7 | case_data 组织:C2.1-A 定分文件夹布局并**预留 `site/` 槽位**(见该稿 §4) | 总平家族的 metadata 声明词汇、B-M 映射、判卷 bindings 是否涉总平——本批定 |

## 3. 关键设计问题与推荐

### Q1 · 总图作为新输入模态的契约(reading 对总平出什么)

总平进 B-M = **新视图家族 `view_type=site_plan`**(枚举已在,加 generator 映射行 + metadata 声明词汇即可,不 bump 大版本预期)。范围**强围栏**:C2.2 只从总平消费**一件事——朝向证据**(指北针/显式角度标注)。总平上其余信息(周边建筑/道路/红线/阴影关系/建筑轮廓)**一律不进管线**(轮廓 cross-check、周边遮挡是 C3+ 的缝,登记不做)。因此:
- reading 对总平的产物 schema = 轻量新 view 类型:北针观测(glyph 位置、指向角读数、uncertainty、可选杆/头描述)+ 可选显式角度文字标注 + 图幅 rotation/mirror 判定所需最小观测;**不出墙/窗/尺寸链**;
- 观测手段:沿用「量而非看」方法论——推荐 CV 工具箱补一个量角件(向量两点取角),VLM 只定位与读文字,角度由量取;uncertainty 如实记;
- `opening_evidence.potentially_observable_claims` 对 site_plan 行 = 空集(不承载 opening claims,负证据永不开启)。

### Q2 · θ 证据阶梯与冲突仲裁(生产者 = 本批主体)

按 E4.3 冻结阶梯施工,**多源合并生产者**落 correction 域(orientation.py 预留的 merge 位):
1. **用户 metadata/总平显式标注**(数值直接给)>
2. **指北针读数**(reading 观测,带 uncertainty)>
3. **default 0 + assumed**(已落,不动)。
仲裁纪律(细稿点名拒绝分支,each 配负锁):多枚北针在 uncertainty 内一致才合并、超差 = conflict;显式标注与 glyph 超阈值 = conflict 记档(阈值命名进配置 + A0);page rotation/mirror 未解析 = 不产证据(fail closed 落 assumed?否——**产 conflict 停机**,静默降级 assumed-0 会把「读不了」洗成「没提供」,违 E2' 诚实缺失纪律);conflict → A3/interactive `NEEDS_INPUT`(合同已冻结)。产物 = accepted orientation evidence(`resolution_kind=accepted_evidence`),经既有 finalize_orientation_enrichment→S5 override 全自动下行。

### Q3 · 「总图 / 各层平面标注旋转」两条路了断

- **路 1(主路)= 总平指北针/显式标注**:如 Q1/Q2。
- **路 2 = 各层平面上的指北针/朝向标注**:定性为**第二证据通道,只做一致性、不做逐层对齐**——各层平面恒定义在建筑帧(平面图纸轴 = 建筑轴,这是 C2 制图词汇的公理),**不存在「每层各自转」**;层平面北针若在,读出后进 Q2 合并器与总平证据互验(超差 = conflict),**绝不产生 per-floor θ**。
- **两条路都没有** = default 0 + assumed(已落)。
- **了断声明**:C2 域内 θ 的语义自由度只有「一个全局角 + 它的证据来源清单」;任何「逐层平面对齐/每层旋转」需求即打破单 θ 模型,属 C3+ 新档,本批显式拒绝(schema 不留 per-floor 角度槽,防烤死方向反着来——这里**不留槽是对的**,因为多 θ 是语义推翻而非扩展,真要做时走新版本)。

### Q4 · 旋转注入 E4 的接线(输入侧 θ → 已落输出侧)

零新契约:accepted orientation evidence 已是输出侧的既定输入(E4.2 唯一 owner = accepted correction orientation 产物)。本批只是让这个产物第一次**由真证据生产**而非 assumed-0 机械件。接线核对清单(细稿逐项):evidence 的 `frame_transform_hash`(image→building 变换)由 reading 观测链供给;`direction_semantics` 消费路径(E4.4 守卫)首次激活——sm26-rotate 立面不命名(C2.1 匹配器绑侧),故 `true_azimuth` 命名映射路在本 case 实际不触发,留合成测试覆盖;B5 Phase D 的 E4 rebind/relation 守卫对新 evidence 生产者零改动(消费侧只认 schema+hash)。

### Q5 · case_data 组织定案(吸收 defer 专场)

承接 C2.1-A 布局(`plans/`+`elevations/`+`site/` 槽位),本批落 `site/`:
- testdata_prompt v-next 加总平声明(路径+「带指北针与否」不声明——有没有北针是 reading 观测事实,metadata 只声明「这是总平」);
- **分文件夹 = 只给 kind 不给 direction**(07-11 主控初判维持):文件夹定 view_type,方向恒由 matcher(立面)/无方向概念(平面/总平);
- 07-12 并入的「四标准立面+知识表补默认」范围口径,在 07-18 重切后的归属:立面词汇与知识表归 C2.1,本稿只确认**总平进词汇表**后 C2 输入词汇收口为 {逐层平面,全投影立面(0..4 不命名),补充平面,总平}——partial/内院仍 sm27。

### Q6 · 判卷与正交性验收

- 角度判卷:gt `north_axis_deg` 有值 **且** 产品 provenance 非 assumed → 计角度误差(判卷容差与测量 uncertainty 分开配置,E4.3 已定);assumed-0 → NA。gt 侧槽位/提取已落,预计只补 score 侧一个小判定件;
- **正交性差分断言(本批特色验收,机器可跑)**:sm26 与 sm26-rotate 双 run 的建筑帧产物(correction accepted output、匹配 sidecar、判卷 sidecar 的建筑帧部分)逐项 diff = 仅 orientation 相关字段;EP 出口 azimuth 逐面差恒 θ(E4 探针已给了 θ=0/90/270 合成版,本批升级为真 case 版);
- judge bindings(F4-1 工装,C2.1-A 落)对总平:总平不参与窗判卷,bindings 无需总平条目;北针判卷走 gt north_axis source_refs 既有链。

## 4. 批次拆解(粗中粒度)

```
C2.2-A (总图输入契约: metadata/B-M/reading 词汇)
  └─> C2.2-B (θ 证据链+仲裁生产者)
        └─> C2.2-C (E4 注入接线核对+判卷小件+合成端到端)
              └─> C2.2-D (sm26-rotate 素材+双 run 正交性验收)
```

| 批 | 内容 | 动哪些环节 | 依赖 | 档 |
|---|---|---|---|---|
| **C2.2-A 总图输入契约** | testdata_prompt v-next 总平声明词汇 + `site/` 文件夹落地 + B-M generator site_plan 映射行(opening claims 空集、无 direction 概念)+ reading 总平产物 schema(北针观测/显式标注/rotation-mirror 最小观测)+ reading skill 总平词汇 + CV 量角件评估(推荐做,小件) | case_metadata / view_manifest generator / 0_reading schema+skill / cv 工具箱 | C2.1-A(布局槽位) | M,细稿(schema 面小但双端) |
| **C2.2-B θ 证据链 + 仲裁** | 多源合并生产者(orientation.py 预留位):阶梯优先级 + 多枚一致门 + 显式 vs glyph 冲突门 + page rotation 未解析停机 + frame_transform_hash 链 + conflict→NEEDS_INPUT + 产 accepted_evidence;命名阈值进配置+A0;拒绝分支全配负锁(B5 Phase C 标准) | 1_correction(orientation 域)/ correction.yaml / A3·interactive 路 | A | **L,细稿必审**(仲裁语义是主险) |
| **C2.2-C 注入接线 + 合成端到端** | E4 消费侧核对(rebind/relation 守卫对新生产者零改验证)+ `direction_semantics` 消费路首激活(true_azimuth 合成测试覆盖)+ score 侧角度判定小件(gt 有值×provenance 非 assumed)+ 合成 case θ∈{0,90,任意角} 端到端(EP azimuth 逐面断言,升级既有探针为回归) | E4 消费侧(核对为主)/ judge score 小件 / 合成 fixture | B | M |
| **C2.2-D sm26-rotate 验收** | 素材入仓(同 U 几何+总平带北针;gt north_axis_deg 由 DXF 提取)→ 双 run:sm26-rotate 全链 + 去总平重跑 assumed-0 路 → **正交性差分断言**(建筑帧产物 θ-only diff + EP 出口逐面差 θ)→ record baseline | 全链 | C + sm26(C2.1-E)已收 | S 工装 + M 跑测 |

**细稿密度建议**:B 完整细稿+对抗审;A 中等细稿;C 以核对清单+测试族为主(消费侧零改是验收主张,不是免检理由);D 按 SOP 走。

## 5. 接缝登记(与已落系统)

| 接缝 | 方向 | 内容 |
|---|---|---|
| E4/B-O 输出侧 | **只消费不改** | accepted orientation evidence 契约不动;本批产真证据版;S5 override/Relative 出口/审计零改动(改了=越界) |
| orientation.py | 填空 | `accepted_evidence` 生产者落进预留位;`prior_fill_assumed_zero` 机械件保持为无证据兜底,两路互斥经同一 finalize |
| B-M | 扩展 | site_plan 映射行 + metadata 词汇;manifest 不可变/唯一 emitter 不动;`direction_semantics` 字段首次有真消费者 |
| reading | 扩展 | 新 view 家族产物 schema + skill 词汇 + CV 量角件;隔离 spawn 流程照旧(总平同样走 clean-room) |
| C2.1 匹配器 | 无交(验收主张) | 匹配建筑帧内、true-north 无关;sm26-rotate 上 matcher 行为与 sm26 逐字节等价 = 正交性断言的一部分 |
| gt/判卷 | 微扩 | gt 槽位/DXF 提取已落;score 侧补角度判定;judge bindings 不涉总平 |
| C3+ | 留缝登记 | 总平轮廓 cross-check、周边遮挡、true_azimuth 命名立面映射的真实 case、多 θ(语义推翻,走新版本非留槽) |

## 6. 依赖 / 风险 / 正交性

- **外部依赖**:sm26-U 素材与 C2.1-E 先收(sm26-rotate 复用同几何);用户补总平图(带指北针;§T' 已含「总平/指北针若有一并给」)。**排程上 A/B/C 三批不等 C2.1 全收**——只依赖 C2.1-A 的布局槽位,证据链/合成端到端可与 C2.1-B/C/D 并行;唯 D 等 sm26 收官。
- **风险 1**:北针 glyph 观测质量(VLM 读旋转符号历来不稳)——已由「量而非看」纪律对冲(CV 量角+VLM 定位);uncertainty 如实记、判卷容差独立配置;实在读不出 = conflict 停机不猜(Q2 已裁)。
- **风险 2**:范围蠕变——总平是信息最杂的图种,Q1 强围栏(只取朝向)要在细稿/审里守死;任何「顺手读轮廓对一下」都是越界。
- **风险 3**:仲裁语义细节(多枚北针、显式 vs glyph、page rotation)负例多、易漏锁——B 批按「点名拒绝分支即配负锁」标准出细稿,吸取 F5-1 缺锁教训。
- **风险 4**:assumed-0 与真 0 混淆回归——E4.2 已在类型层分开,但输入侧首次有真证据后,「证据说 0」的 case 要有专门测试(provenance=observed、value=0,判卷计分不 NA)。
- **正交性**:本批不碰几何/匹配/判卷主体;三轴(匹配/旋转/缺件补)在 sm27 首次全叠加,C2.2 的差分断言正是叠加前最后一道正交性质检。

## 7. 与 C2.1、sm27 总验收的关系

- **承接 C2.1**:输入布局槽位(site/)由 C2.1-A 预留;sm26-rotate 复用 sm26 全套素材与 gt(仅 gt north_axis_deg 从 null 变有值 + 总平 source_ref);匹配器零改动是本批验收主张之一。
- **交棒 sm27**:sm27 = 旋转 + 自配立面 + 缺件补 + 内院匹配四轴叠加,前三轴分别由 C2.2/C2.1/C2.1 验掉,sm27 唯一新轴 = 内院;本批的正交性差分断言方法(双 run 建筑帧 diff)可直接复用为 sm27 的叠加质检工装。
