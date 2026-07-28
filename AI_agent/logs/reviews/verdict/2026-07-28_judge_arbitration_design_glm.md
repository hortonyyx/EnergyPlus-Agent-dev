# 裁决书 · 判卷器「诊断仲裁 + 守恒判据 + 来源身份」设计稿（2026-07-28）

- **审阅方** = GLM-5.2（跨家族，谁写谁不批）
- **被审对象** = [judge_arbitration_and_provenance_plan_sol.md](../../../proposals/judge_arbitration_and_provenance_plan_sol.md)（sol，950 行，施工基线候选）
- **清单** = [glm_checklist](../request/2026-07-28_judge_arbitration_design_glm_checklist.md)（P1–P30）
- **对照** = [问题书](../request/2026-07-28_judge_arbitration_and_provenance_brief.md)
- 本轮**只审设计稿，不审代码**；探针全部在 /tmp 与只读现码上完成，工作树未改。

---

## 0. 总裁决：APPROVE-WITH-CHANGES

方向正确，承重命题（P5/P6/P9/P10/P15/P20/P21/P25）**全部成立**——三条缺口都被换成了**结构性判据**（证书式仲裁 / 区间 owner 重数 / 来源 alias 证书），不再是「症状白名单 + 数值阈值」，这正是三轮同源病根的收口。

但设计稿在**两个新边界**上只给了概念承诺 + 双向门，没有给出可机械判定的算法。前三次失败全在边界条件，这两个边界就是「第四个位置再破一次」的主要风险，必须在施工前钉死（见 MAJOR-1 / MAJOR-2）。故 WITH-CHANGES，不 REWORK：缺陷是「算法未精确化」而非「方向选错」，且双向门（A-L1/A-L2/A-L3、C-L4/C-L5、B-L1/2/3/4）已就位能捕获边界实现错误。

---

## 1. 独立探针证据（不采信设计稿自述）

下列数字均由我在现码上独立复算，与 brief/sol 裁决书逐项吻合，作为命题判定的地基：

| 探针 | 现码行为 | 命中 |
|---|---|---|
| 三段相邻铺满（清单 P9 的 x0..x3）`covered = (x1-x0)+(x2-x1)+(x3-x2)` 顺序累加 vs `obs.length=hypot(x3-x0,0)` | `20.861502717932577(0x...ef7f)` > `20.861502717932574(0x...ef7e)`，**excess=3.552713678800501e-15（1 ulp）** ⇒ `_assert_obs_conservation(covered>length)` **假红 RAISE** | P9 现状、B-L4 现码红 ✓（与 brief 数字逐位一致）|
| 真实过计 `[0,4]+[1,3]→obs[0,4]` | `obs_covered=6.0 > 4.0` ⇒ RAISE（正确）| P10 现码对真实过计仍拒 ✓ |
| A-L3 活体：`exterior_duplicate_owner`(identity)+`advisory_unpaired`(capability) 喂 `_arbitrate_pairing_diagnostics` | **raise `score_unsupported_combination`（NA）**——独立真实 duplicate 被洗成 NA | P5 现状假绿、第三张脸 ✓ |
| 同一活体喂两次（A-L1 形态）| 同样 NA | 现码对 P5/P6 **给同一种诊断、无法区分** ✓ |
| `_REAL_BREAK_REASONS` | `('exterior_interior_topology_conflict','invalid_interior_edge_pair')`，**不含 `exterior_duplicate_owner`** | r3 白名单机制坐实 ✓ |
| 最小同-owner 反向边 `{(0,0)→(2,0):[Z],(2,0)→(0,0):[Z]}` 喂 `_tile_orthogonal_edges` | **产出 `(('Z','Z'))` 内墙**，无 `left_owner!=right_owner` 守卫 | C-L9 现状 ✓ |
| 非相邻重复环 `(0,0),(4,0),(4,4),(0,4),(0,2),(2,2),(0,2)` 喂 `_points` | **接受（未 raise）**，非相邻重复存在 | C-L7 现状（只查相邻坍缩）✓ |
| `_cluster_axis(raw_values: Iterable[float])` / `_build_floor_identity` 展平 `float(p[0])` | 确认进聚类器前来源丢光 | P15/P17 现状 ✓ |
| `score_identity_contract_mismatch` | 全仓仅 `score_schema.py:60` 码表 frozenset 一处，**零 raise** | P17 现状 ✓ |
| `_SUBINTERVAL_SUM_TOL` | 仅 `segment_score.py:798`（target 层守恒门）使用 | 两层不自洽现状 + 设计稿"在本通路移除"措辞准确 ✓ |
| `score_attempt_service`（score_service.py:327） | sm21 走注入的 `legacy_evaluator`，**不进入** `score_typed_attempt`/segment_score 新机制 | P22 分派缝结构保证 ✓ |
| `orthogonality.py` | correction 侧模块，注释明示零 judge/gt import | P23 不变量#4 现状 ✓ |
| GT/correction schema | footprint.exterior.vertices / zone.polygon.exterior.vertices / boundary_segment.{id,p1,p2} / cell.{id,x,y,polygon} 全可索引 vertex_index/endpoint_side；`source_refs` 是 per-segment/per-zone 非 per-vertex | P15 来源 key 可从现有 wire 派生 ✓ |

---

## 2. P1–P30 判定表

「成立」= 设计稿在该命题上经独立推演/探针可成立；「成立*」= 概念成立但挂一条 MAJOR 风险（见 §3）。

| 命题 | 判定 | 独立依据 |
|---|---|---|
| **P1** 核心原则覆盖三轮病因 | **成立** | 四禁止项↔四病因逐一对应：执行顺序=r2、错误文案=r3-B1、浮点偶合=r1/r3-B2、未保留语义前提=R2-B2；均为各轮裁决书真实病因，非事后套用 |
| **P2** 依赖顺序是规范 | **成立** | §0/§6.2：C→A→B 是规范，NA 请求无「先算部分分再定」路径；顺序改不影响出口 |
| **P3** §6.3 五条=结构性保证 | **部分成立** | 第1/3/5 条是结构（无 witness⇒NA；owner 重数；profile 插件）；**第2、4 条依赖未精确化的 envelope 传播与 alias 证书算法** ⇒ 见 MAJOR-1/2 |
| **P4** CERTIFIED_CONFLICT 可机械判定 | **部分成立** | 首批 5 predicate（§4.3）给了具体认证条件与「最小固定核心 witness」可操作定义；通用「所有可接受解释下恒真」未形式化（MINOR，不阻断）|
| **P5** 区分 advisory 派生 vs 独立 duplicate | **成立\*** | 探针坐实现码对两者给同诊断无法区分；设计稿 §4.2/§4.3 用 envelope 把 A/B 固定边与 advisory 非固定端点分开 ⇒ A/B 恒真 CERTIFIED、advisory 派生 CONTINGENT。**envelope 传播算法未给伪代码** ⇒ MAJOR-1 |
| **P6** 不误判既有合法 advisory | **成立\*** | A-L1 形态现码正确 NA（探针）；设计稿保留此结果。同一 MAJOR-1 守门 |
| **P7** reason 降级为纯展示 | **成立** | 通读全文，仲裁用 witness+envelope，无任何 reason 分支；`select_root` 用 (side,floor,locus,diagnostic_id) 不用 reason |
| **P8** 仲裁覆盖整请求所有楼层 | **成立** | §2.2 请求级收齐报告一次仲裁；§4.4 调换楼层不改出口；§4.5/A-L5「不同楼层红+NA⇒整请求红」|
| **P9** 1-ulp 合法铺满不假红 | **成立** | 探针坐实现码假红（1 ulp）；设计稿 §5.2/§5.5 用 exact-rational + 相邻 cut 复用同一 bit pattern，相邻共享端点在 obs 域求值得同一 rational ⇒ 无正长度重叠原子 ⇒ owner=1 合法。论证严格 |
| **P10** 真实过计仍响亮拒绝 | **成立** | 探针坐实现码对 6>4 / 5e-10 拒绝；设计稿 §5.5 observation atom owner>1 拒绝，与 §5.2 mapping certificate 共同守住 |
| **P11** owner 重数不依赖容差 | **成立** | 纯 target_id 集合基数，无阈值 |
| **P12** extra 结构上非负 | **成立** | extra=owner=0 原子并集，exact-rational 减法非负；不再算 length-covered |
| **P13** exact-rational 无损 | **成立** | `as_integer_ratio()` 对有限 binary64 无损（denom 为 2 的幂）；sm24 规模 Fraction 足够，性能风险已识别（§3.7/§5.9）|
| **P14** 闭区间端点重合不判重叠 | **成立** | §5.4 相同 exact 值合一为同 cut，相邻原子共享 cut 无正长度重叠 |
| **P15** 来源 key 在现有输入 | **成立** | GT/correction/reading 三类 key 均可从现有 wire 结构派生，不需改 schema/wire/已签字答案；`source_refs` 非 per-vertex 故不用它（正确）|
| **P16** alias 证书打破距离循环 | **部分成立** | 距离仅提候选（必要）、结构证书焊合（充分）、无证书⇒`unproven_cross_source_alias`——概念上打破循环；**但 `paired_edge_endpoint`/`boundary_chain_endpoint` 判定算法未给，存在退化回距离或过窄风险** ⇒ MAJOR-2 |
| **P17** 合同版本有 raise 路径 | **成立** | 现码零 raise（探针）；设计稿 §3.3 给 version/same-source/unproven-alias/collision 多类 raise，DoD#7 兜底 |
| **P18** 合同④ 覆盖遗漏形态 | **成立** | §3.4 C-4 覆盖非相邻重复/自触自交/同 owner 反向/boundary duplicate-after-merge；C-L7/8/9/10 锁 |
| **P19** 审计字段足够复现 | **成立** | §2.4 列最低字段含 hex/diameter/source key/owner/contract version；§3.4 boundary 补四端点 |
| **P20** 地基不被推翻 | **成立** | §1.4 逐一保留：三阈值、池分离+答案纯函数、长度分母+criterion 三分、联合切点、B-1 单向注册、R-4、W5、advisory 日志；C-L14/C-L15 锁 |
| **P21** 三历史反例转绿 | **成立\*** | 1-ulp boundary 对（C-2 同现码）确定绿；8.06/0.3 对依赖 C-3 alias 证书覆盖 ⇒ 同 MAJOR-2 |
| **P22** sm21 legacy 零变化 | **成立** | `score_attempt_service` 分派缝，legacy 不实例化任何新对象（§1.4/§3.3/§9 一致）|
| **P23** 不变量#4 | **成立** | 新模块 judge-only；orthogonality 零 gt import |
| **P24** 不变量#6 | **成立** | §3.4/§5.2/§6.3：ring 多环、相交谓词一般化、B 任意直线一维参数、A envelope 插件；C-L13 非正交锁 |
| **P25** 33 锁抽查≥8（含 Slice0 五条）| **成立** | Slice0 五条（A-L3/B-L4/C-L1/C-L7/C-L11）现码红全部探针坐实；共用守卫已归并披露（A-L2/A-L3、B-L1/2/3）；neuter 可机械执行 |
| **P26** 七条否决路径未复活 | **成立** | 格子量化/顺序定案/reason 白名单/固定容差/零容差/距离反推/判量不了为 invalid——概念均未复活；距离反推的残留风险=MAJOR-2 |
| **P27** 施工拆分半交付 | **成立** | §7 三条不可半交付定义精确（source 回退 float / category 定红 / fsum 换汤）；§7 末句禁止半成品 source/envelope 单独发布 |
| **P28** Slice0 锁真红 | **成立** | A-L3（探针 NA）、B-L4（探针 1-ulp 假红）、C-L1（现码无 source）、C-L7（探针接受非相邻重复）、C-L11（现码无版本门）现码均红 |
| **P29** 成本估计可信 | **基本成立** | 行数/日数估计合理；但 §5.2 observation 反投影是计分大改，§8.3 影响面可能低估（MINOR-3）|
| **P30** 总状态机自洽 | **成立** | §6.1：C 合同拒绝/A CERTIFIED/B denominator 三类红 + A NA + B rows，所有组合有确定出口；C-0..3 纯输入合同 vs C-4 capability-依赖拓扑在 certifier 内区分 |

**承重命题八条全部成立**（P5/P6/P9/P10/P15/P20/P21/P25），其中 P5/P6/P21 标 `*` 因挂在 MAJOR-1/2 上。

---

## 3. Findings

### MAJOR-1 · CapabilityEnvelope 的传播算法是「第四个位置」主风险，必须施工前钉死
- **位置**：设计稿 §4.2 envelope 定义 + §4.3「最小固定核心 witness」。
- **问题**：P5/P6 的区分全靠「A/B 的固定来源边 ⊄ cell C 的 envelope」这一条。设计稿给了 envelope 的**枚举项**（advisory 源边/源顶点/小分量坐标/ring 相邻边端/pairing cut-owner），但「传播按 source data-dependency 做」是**一句承诺，不是可机械判定的规则**。前三次失败全在边界——这就是 A 的新边界。若施工把传播做**宽**（把 A/B 固定边也标 capability-dependent）⇒ P5 假绿复发；做**窄**（漏标 P6 派生端点）⇒ P6 假红复发。
- **要求**（施工前）：把「给定一条 advisory 边，机械枚举其 capability-dependent 事实闭包」写成判定步骤/伪代码，明确**终止条件**（哪些边端算「由小分量坐标决定」、T-junction cut 怎么入闭包），并通过 A-L1（P6 NA）/A-L2（1e-9 真缝红）/A-L3（P5 红）双向门**实测**。设计稿 §4.7 已识别此风险并设双向门——补的是**算法本身**，不是门。

### MAJOR-2 · C-3 alias 证书（paired_edge_endpoint / boundary_chain_endpoint）判定算法未给出，存在退化回「距离反推意图」的风险
- **位置**：设计稿 §3.3 C-3 五种证书 + §3.4。
- **问题**：`paired_edge_endpoint` 要判「两个不同 owner 的反向边端点共址」。这最终要读端点共址/边反向——**仍是数值判定**。设计稿的辩护（距离仅提候选、结构证书才焊合）概念上成立（P16 部分成立），但没给出证书判定**凭什么独立于距离**：若施工把「端点距离<merge」当成 `paired_edge_endpoint` 的判定，就回到 brief §4 已否决的「距离反推意图」。同时 P21 的 8.06/0.3 历史反例能否转绿，**直接依赖**这两个证书能识别它们的共享墙/同来源关系。
- **要求**（施工前）：明确 `paired_edge_endpoint`/`boundary_chain_endpoint` 的判定依据是 **wire 结构字段**（edge owner + 方向、boundary `world_along_interval` 连续性、ring 顶点序号），而非坐标数值接近；给出可机械判定的规则；C-L4（三历史反例升级为带 source/topology 正式夹具仍绿）+ C-L5（无关系 sub-merge 必红）双向门实测。否则 P16 退化、P21 回红。

### MINOR-1 · §3.2 来源 key 表「"exterior"/hole_id」与现 GT schema 禁洞的关系应注明
现 `gt_schema.py` 对 footprint/zone 强制 `interior_rings` 为空（`gt_profile_holes_unsupported`，c2 profile）。表中 `hole_id` 槽位是给未来带洞 profile 留的（合不变量#6），但设计稿未注明，施工方可能误以为现 GT 有洞。建议加一句「v1 仅 exterior，hole_id 为 profile 扩展槽」。

### MINOR-2 · contract_version 进入 scorer identity 的方式未说清
§3.3 说「按既有协议 bump `SEGMENT_SCORER_HELPER_VERSION`」。现码 `helpers.segment_scorer` 是硬编码串 `"b4b_segment_score_v2"`（score_service.py:166）。是并入该串、还是 `ScoreIdentityV8` 新增字段？两者对 sidecar hash 与旧 v3 派生件失效面影响不同，施工前需定。

### MINOR-3 · §5.2 observation interval 反投影的影响面 §8.3 可能低估
把 obs interval 从「target 投影」改为「obs 自身弧长反投影」是**所有 v3 墙计分**的路径改动（§5.9 自承「改变少量 v3 extra 最后 1 ulp」）。§8.3 只列「少量 v3 score service / identity contract 锁」，建议显式声明：改造前后对真实 sm24 v3 逐行 diff（§5.9 控制项已提）是必跑项，影响面估计应含全部 v3 segment 计分锁。

### MINOR-4 · §5.3 eligible_units round 到 float 后下游 criterion 的 1-ulp 边界
守恒门用 exact-rational（正确），但 `eligible_units` 公开为 float 后，`complete/within/miss`（用 `claim_complete_epsilon_m`）仍是 float 比较。P9 要求「计分正确」——守恒不拒已满足，但 criterion 边界仍有 1-ulp 抖动可能。设计稿已声明该 epsilon 不接触守恒/负数（§5.5），分层正确；记录为已知精度遗留，非缺陷。

### MINOR-5 · B-L4「cut id 复用」实现承诺 vs Slice 3 不可半交付措辞
§5.2「共享 canonical target 顶点经同一 obs 参数函数求值一次并复用 cut id」是 P9 成立的关键实现承诺。Slice 3 不可半交付只点名「fsum 换汤」，未明确覆盖「不复用 cut id、对每 target 独立算 obs interval」。B-L5（顺序全排列 canonical bytes 不变）部分捕获。建议把「cut id 复用」写进 Slice 3 不可半交付清单，免施工方独立求值回到 1-ulp。

---

## 4. 清单外发现

**E1（确认设计稿已正确处理，记录备查）**：现码 target 层用 `_SUBINTERVAL_SUM_TOL=1e-9`（承认累加漂移）、observation 层零容差，**两层互不自洽**——这正是 r3-B2 的根。设计稿 B 用 exact-rational ledger 统一两层并移除该容差在守恒通路的职责（§7 Slice 3）。探针确认 `_SUBINTERVAL_SUM_TOL` 仅 `segment_score.py:798` 一处使用，设计稿「在本通路移除」措辞准确。✅

**E2（向施工方提示的第四张脸风险）**：现码 `_arbitrate_pairing_diagnostics` 的三分支（real_breaks 白名单 / capability / ambiguous）就是第三张脸的机制，设计稿 certifier 正确取代它。但 certifier 的「首批 5 个 predicate evaluator」（§4.3）**不能在施工时退化成「只有这 5 个 predicate 能红」的新白名单**——那等于把 reason 白名单换成 predicate 白名单，第四张脸。设计稿 §2.3 已用「无 evaluator ⇒ `diagnostic_evidence_incomplete` NA，不自动定罪」守住正向；反向（有 evaluator 是否一定红）靠 witness 恒真性而非 predicate 名字——请在施工日志显式声明这条不变量。

---

## 5. 结论

- **方向**：三条缺口各自的结构性判据（A 证书式仲裁 / B 区间 owner 重数 / C 来源 alias 证书）**正确**，直击三轮同源病根（症状白名单 + 数值阈值摆动）。承重命题全部成立。
- **风险**：集中在两个**新边界**——A 的 envelope 传播（MAJOR-1）、C 的 alias 证书判定（MAJOR-2）。这是前三次「方向都对、边界出错」的下一个边界。设计稿在这两处给了概念框架 + 双向门，但缺可机械判定的算法。
- **裁决**：**APPROVE-WITH-CHANGES**。施工方在 Slice 1（C）/ Slice 2（A）开工前，须先把 MAJOR-1（envelope 传播闭包枚举规则）与 MAJOR-2（alias 证书判定规则，依据 wire 结构而非距离）写成可机械判定的步骤，并用各自双向门实测；MINOR 1–5 并入施工日志。钉死这两条边界后，本稿可直接按 §7 拆施工，不需施工方再自行补边界裁定。

> 本裁决独立探针完成、工作树未改、未采信设计稿自述。承重命题逐条经现码或严格推演验证；两处 MAJOR 是「算法精化」而非「方向缺陷」，故 WITH-CHANGES 而非 REWORK。
