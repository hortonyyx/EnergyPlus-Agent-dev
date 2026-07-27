# 对抗审裁决 · 判卷器「数值身份 + 计分度量」综合稿（GLM-5.2 跨家族对抗审）

- 日期：2026-07-27
- 被审对象：`AI_agent/proposals/judge_identity_and_metric_plan.md`（综合稿 / 施工基线）
- 来源（用于核实综合是否忠实）：`judge_identity_and_metric_plan_opus.md`（Claude 侧）、`judge_identity_and_metric_plan_sol.md`（GPT 侧）
- 背景实证：`2026-07-27_plan_segment_tjunction_sol.md`（r1）、`..._sol_r2.md`（r2）
- 共同问题书：`2026-07-27_judge_identity_and_metric_planning_brief.md`
- 审阅方：GLM-5.2（跨家族，与两份来源稿不同家族）
- 裁决：**APPROVE-WITH-CHANGES**
- 审阅纪律：只审不修；未改动任何被审文件与生产码；全部探针落 `/tmp/glm_judge_review/`；审毕附 sha256 字节不变自证。

## 0. 总裁决与一句话

综合稿的核心四决定（C-1 身份机制 / C-2 长度分母 / C-3 联合切点 / C-4 字节不动）与六条主控裁定（R-1～R-6）**全部经独立探针核实成立**——10 条命题中 9 条成立、1 条（P10 反向找漏）命中一个**实质性未裁定分歧**。该分歧不推翻任何核心决定，但施工前必须显式裁决，否则施工者会在最关键的身份层上二选一瞎猜。故给 APPROVE-WITH-CHANGES：核心可信，带「身份池作用域须显式裁定 + 三处补遗」放行。

本轮所有数字（3.96× 失真、16 邻接、57.86 m、1.67× 余量、ulp 量级、护带余量）均由我在 `/tmp` 独立复算，**未采信综合稿或两份来源稿的任何数字**。

---

## 1. 逐命题裁断

### P1 · 不可能性论证 + 单链接聚类是否让共享身份成无条件结论 —— **成立**

**（a）不可能性命题成立，且我独立构造了 r2 格边界活体。**

综合稿 C-1 称「任何全定义离散化都有边界，边界两侧任意近两点被判异 ⇒ 注定失败」。我用 binary64 算术（**非 Decimal**——Decimal 精确减法会消除该反例，这是审阅时必须注意的坑）复现了 r2 裁决书的格边界对：

```text
left  = 8.0600000000005           (字面量 → binary64)
right = 8.060000000001 - 5e-13    (binary64 减法)
|delta| = 1.776e-15  (1.000 ulp)
canonical(left)  = 8.06
canonical(right) = 8.060000000001   ← 同一接缝的两种合法写法被判异（假红）
```

进一步机械扫描：在 0.3 / 1.0 / 3.0 / 8.06 / 10 / 20 / 32 每个量级都存在「相邻 1-ulp binary64 被当前 `round(v/1e-12)*1e-12` 分到不同量子格」的边界对（如 20 m 量级 `20.0000000000005 ↔ 20.000000000000504`，1 ulp 跨格）。**边界不可避免**，不可能性命题的具体化坐实。定格量化 / Decimal 取整 / 定点整数同构（都是全定义离散化），综合稿的否决成立。

**（b）单链接聚类 + 直径守卫 + 歧义拒绝，在给定输入合同下让共享身份成无条件结论 —— 成立。**

我实现了护带版（merge 1e-11 / split 1e-10 / diam 5e-11）与 sol 单上界版（B=1e-12），对六组输入跑同一矩阵：

| 输入 | 护带版 | sol 单上界版 |
|---|---|---|
| r1-A 真实 sm24 接缝 `8.059999999999999`/`8.06` | 同 atom ✓ | 同 atom ✓ |
| r1-B typed correction `0.1+0.2`/`0.3` | 同 atom ✓ | 同 atom ✓ |
| r2 格边界对（binary64 算术） | 同 atom ✓ | 同 atom ✓ |
| 1e-9 真缺口 | 异 atom ✓ | 异 atom ✓ |
| 5e-11 歧义间距 | **REJECT(ambiguous_gap)** | 异 atom（静默分裂） |
| 链式吞并 200×5e-12 | **REJECT(cluster_too_wide)** | 异 atom（静默分裂） |

判读：三组历史反例在两种机制下都无条件吸收（定理 1）；1e-9 缺口都保持异身份（定理 3）；**关键差异在「分不清」区间**——护带版响亮拒绝（兑现 C-1「分不清时显式拒绝」），sol 单上界版静默分裂。这正是综合稿 R-1 取护带的实证依据（见 P2）。

「无条件」是**在给定输入合同下**的无条件：合法写法集合直径 < merge 阈、不同意图间距 > split 阈时，同身份是定理而非概率论断；违反合同时整轮响亮拒绝。这恰是「部分函数」语义，比 round()（合同内仍失败）严格更强。命题第二半成立。

> ⚠️ 一处措辞提醒（不影响成立）：综合稿 C-1 把结论表述为「无条件」，但其「无条件」依赖 sol §2.2 的**输入合法性合同**（4 条：同意图直径 < 阈、异意图间距 > 阈、无恰等上界、归并不坍缩）。综合稿未把该合同显式载入正文（见 P10-②）。

### P2 · R-1 护带 vs 单点边界 —— **成立**

综合稿 R-1 称「单点边界是零测度事件、现实永不触发 ⇒ 漂移略大于上界就静默分裂」。我用 `B=1e-12` 单上界 + link 规则 `dist < B` 实测：

```text
v1 = 8.06 + 0.5005e-12,  v2 = 8.06 - 0.5005e-12
|v1-v2| = 1.0019e-12  >  B
→ 既不 < B（不连边）也不 == B（不触发边界拒绝）⇒ 静默判异
```

`{dist == B}` 在 R 上勒贝格测度为 0，连续分布下 `P(dist==B)=0`——单点边界几乎不可触发，漂移落入 `(B, 真缺口)` 区间即静默分裂、且无响亮拒绝。结合 P1 表中 5e-11/链式两行（sol 静默分裂 vs 护带响亮拒绝），R-1 的论证链完整成立：护带把「分不清」区间从「两个静默答案」变成「响亮拒绝」，是结构性更强、而非位移边界的方案。

无反例可给。

### P3 · R-2 阈值须实测推导；双向余量是否打架 —— **成立（两约束不打架，存在宽可行窗）**

我实测 sm24/sm21 真实数据的合法表示漂移：

```text
sm24: 坐标 192 个，最大幅值 20.0 m；8.06 处 ulp = 1.776e-15
sm21: 坐标 145 个，最大幅值 15.0 m
真实接缝 8.059999999999999 vs 8.06: delta = 1.776e-15 (1 ulp)
20 m 处 ulp = 3.553e-15
```

correction 坐标来自尺寸链加减 / 墙厚折半 / frame 换算（~数十次算术）。保守取 50 ulp 累计漂移 ≈ 1.78e-13 m，现实（~10 ulp）≈ 1.78e-14 m（与综合稿「若干次算术后约 1e-14」吻合）。必红缺口 = 1e-9 m。可行窗 = [1.78e-14, 1e-9]，宽约 5.6×10⁴（10 ulp）～ 5.6×10³（50 ulp）：

| 阈值组 | 下界余量（合并阈/漂移） | 上界余量（1e-9/分裂阈） | 1e-9/直径 |
|---|---|---|---|
| Claude 护带 merge1e-11/split1e-10/diam5e-11 | 56×（50ulp）/ 562×（10ulp） | 10× | 20× |
| sol 单上界 1e-12 | 5.6×（50ulp）/ 28×（10ulp） | 1000× | — |

**两条约束（下界 > 漂移、上界 < 1e-9）不打架**——存在宽可行窗，两组阈值都满足。综合稿 R-2 称 Claude 组「对 1e-9 必红锁只剩 10× 余量，偏薄」**属实**（我复算 split 1e-10 vs 1e-9 = 10×），但 1e-9 红锁的真正承重是**直径守卫 5e-11**（20× 余量，任何 ≥1e-9 的两点必跨簇、必异身份），split 阈只是「≥split 必异」的辅助保证。故 10× 偏薄但非缺口。R-2「阈值不由本文钉死、须施工批实测推导 + 双向证明」「禁止先定数字再补论证」**完全正确且可满足**。

> 补充：sol 单上界在 50 ulp 漂移下下界余量仅 5.6×，若 correction 算术链更深则可能 < 1（合并阈低于漂移）。这进一步支持 R-1 取护带 + R-2 实测定阈。

### P4 · 长度分母 3.96× 失真 + 分区不变性 —— **成立（3.96× 独立复算精确命中）**

用仓库真实 `extract_gt_plan_segments(sm24 gt)` + Shapely 边界相交双路独立复算：

```text
extract: 4 外围 + 16 内墙；内墙总长 57.86 m
Shapely 两两 boundary intersection: 16 个正长度邻接分量（与 sol r1 独立复算 16 一致）
长度求和 57.86 m == extract 内墙总长 57.86 m（无重复计罚）
内墙长度跨度: min 1.50 m, max 5.94 m = 3.96×
```

**邻接界面单位（现状）**每条权重 1/16，每米权重 max 0.04167/m、min 0.01052/m，**最大/最小 = 3.9600× —— 与综合稿 C-2 的 3.96× 逐位吻合**（独立复算，非抄数）。

**分区不变性**：取最长内墙 5.94 m，邻接界面单位下切成 k 段后该墙占楼层权重 = k/(16+k-1)：

| k | 邻接界面单位权重 | 长度单位权重 |
|---|---|---|
| 1（现状） | 1/16 = 0.0625 | 5.94/57.86 = 0.1027 |
| 2 | 2/17 = 0.1176 | 0.1027 |
| 4 | 4/19 = 0.2105 | 0.1027 |
| 8 | 8/23 = 0.3478 | 0.1027 |

邻接界面单位下同墙权重随切分段数线性上涨（k=8 时 5.6×），长度单位下恒为 0.1027（一维测度可加，数值例 5 段求和 == 原 5.94 ✓）。**失真证伪 + 不变性证明双双成立**，C-2 否决邻接界面、采长度作分母正确。

### P5 · C-3 联合切点后 score_match_ambiguous 结构性不可达 + 支撑线间距余量 —— **成立**

**（a）结构性不可达成立。** 用真实 `judge_score.yaml` config 复现：4 条 1 m target 对 1 条 4 m observation（都在 y=3），当前 `assign_plan_segments` 抛 `ScoreContractError(code=score_match_ambiguous, context={'kind':'segment','candidate_assignments':4})` —— 即综合稿 §4.3 表 1 S2「画对但分段不同 → 抛错不出分」。联合切点覆盖下 union cuts={0,1,2,3,4}、4 原子各 `covered_by_gt=T & covered_by_obs=T` ⇒ 4/4=100%，**无「选哪个」自由度 ⇒ 无并列最优 ⇒ 无歧义**。命题成立：覆盖是集合运算，segment 通路 `score_match_ambiguous` 结构性不可达。

**（b）支撑线间距余量 1.67× 独立复算精确命中。** sm24 内墙按轴分桶取支撑线常数：H 线 {3.44, 4.94, 8.06, 13.0, 14.0, 15.94}（6 条）、V 线 {4.18, 5.82}（2 条）。`plan_position_tol_m = 0.30`（`src/configs/judge_score.yaml` 实读），故 `2×tol = 0.60 m`。H 线最小间距 = 1.00 m、V 线 = 1.64 m，全局最小 = 1.00 m，**余量 = 1.00/0.60 = 1.67× —— 与 Claude 侧稿逐位吻合**。

**关于「1.67× 是否够安全」**：1.67× 意味着 GT 支撑线间距 < 0.60 m 时一条产品墙会被两条 GT 线同时记功；真实 sm24 是 1.00 m，不会触发。但 1.67× 偏紧——这是**真实可达的失败模式**（两道近距平行墙的合法建筑），仅靠「看着够」不安全。综合稿 C-7/opus 锁已要求把它写成机器前置校验 `score_supporting_lines_too_close`，这是正确纪律。**结论：余量数字准确、1.67× 偏紧但可接受，前提是该前置校验必须落地为 fail-closed 锁（综合稿已要求）。**

### P6 · C-4 sm24 字节不动 + 签名链不消费判卷器输出 ⇒ 不需重签 —— **成立**

**（a）签名链不消费判卷器输出，属实。** `src/agent/judge/gt_promotion.py` 对 `segment_score`/`score_service`/`score_typed_attempt`/`ScoreIdentity`/`extract_gt_plan` **零引用**（grep 空）。其验签只查：`ConversionReportV1` 十门全绿、`HumanReviewAckV1`（decision=approved + review_index_sha256）、`validate_review_index`（review_index.json 清单）、`compute_gt_v3_content_sha256`（GT 内容 hash）、`_assert_promotion_semantics`（除 verification/content_sha256 外逐字段全等）、request hash。**链上无任何一环消费 segment_score 输出。**

**（b）本方案文件面不触受保护答案。** 综合稿改动面 = 新建 `src/agent/geometry/coordinate_identity.py` + `orthogonality.py`，改 `segment_score.py`/`score_policy.py`/`score_schema.py`/`score_service.py`/`cell_geometry.py`（仅正交那一职）+ 文档/测试。**无一在 `case_tests/test_baseline/gt/sm24_anchor/`**。`compute_gt_v3_content_sha256`（gt_schema.py:662）序列化 GT 文档本身，与 scorer 无关——身份规范化在判卷器**读取之后的内存里**发生（综合稿 C-4/opus §6.2），不重写答案一字节。

故 GT content hash 不变 ⇒ review_index 三 hash（source_dxf + request + inventory）不变 ⇒ 签名继续有效。**「用户不需要再签一次字」成立。** 需失效的只是派生件（旧 score_vs_gt sidecar / grade PNG / 旧 identity 合同缓存），综合稿 C-4 已正确区分。

### P7 · §3 最脆环节（product_to_gt）风险真实 + 既有窗锁全单段 —— **成立（典型「门是真的、锁是缺的」）**

**（a）风险真实。** `score_service.py:192-193` 的 `product_to_gt` 由 `segment_assignment.matched`（当前一对一）构造，随后喂给：`assign_openings`（:229）、`build_correction_host_resolver`（:250）、`build_absence_opening_claims`（:267）、`classify_extra_observation`（:272）—— 即**窗宿主解析与 opening 计分**。摘掉一对一指派后，segment 计分变覆盖式（多对多），但 `product_to_gt` 仍需 `{product_segment → gt_segment}` 单值映射喂窗侧；两者语义不等价。施工若「取第一个覆盖段」，多段覆盖下窗会静默绑错墙。

**（b）既有窗锁全是单段夹具，属实。** 全仓 grep `product_to_gt_segment` 测试用法：

- `test_c2_b4b_phase_b.py`：全为 `{target.boundary_segment_id: target.boundary_segment_id}`（自映射）或 `{product_segment.id: target.boundary_segment_id}`（单段）或 `{"S":"S"}`；
- `test_c2_b4b_phase_c.py`：全为 `{target.boundary_segment_id: target.boundary_segment_id}`（单段自映射）；
- `test_c2_b5_parent_and_verts.py`：`{segment.id: "gt-segment"}`（单段）。

**无一例多段覆盖夹具**（一条产品段跨多条 GT 段，或反之）。`multiple_segment_candidates` 的命中均在 correction 生产路径 `window_host`（拒绝单窗跨多段），非 scorer 的 `product_to_gt` 多段覆盖。⇒ 综合稿 §3「既有窗锁全是单段夹具」**逐条核实成立**，风险确为「门是真的、锁是缺的」。综合稿 §3 已要求①逐键相等显式契约锁 ②多段覆盖窗夹具 ③派工单单列一条——正确且必要。

> 措辞小疵（不影响成立）：综合稿 §3 写 product_to_gt「同时喂**墙的计分**与窗的宿主解析」。精确说：墙计分（`segment_rows`）由 `score_plan_segments` 独立算，**不消费** `product_to_gt`；`product_to_gt` 是**由墙指派结果派生**、再喂窗侧。共享的是「构造来源」而非「墙计分消费」。综合稿表述略宽，但所指风险（共享构造 + 语义不等价 + 无多段锁）准确。

### P8 · R-4 unsupported vs broken + gt 铁律 —— **成立（可实现、不违反 gt 铁律）**

**可实现**：R-4 把「几何合不合法」权威归生产端、「判卷器能不能量」权威归判卷端，后者只许说 `unsupported_product_geometry`（capability NA）、不许说 `broken`。现行 `invalid_interior_edge_pair` 把「量不了」错写成「拓扑破洞」是三轮假红根因；R-4 拆开后，真缺口仍报 `invalid_interior_edge_pair`（合法，product vs GT 比对后的真洞），近正交非精确轴对齐边报 capability NA。语义分离干净。

**不违反 gt 铁律**：
- `correction/cell_geometry.py`（gate① 生产路径）对 `src.agent.judge` **零 import**（已核实）；
- 拟建 `src/agent/geometry/coordinate_identity.py` + `orthogonality.py` 落 `src/agent/geometry/`（既有 modelling/split_pairing/build/specs 的共享层），依赖方向 生产 → 共享 ← 判卷，**不含答案、不 import judge.gt**；
- capability NA 判定只看**产品几何形状**（atom 化后是否精确轴对齐），不需读 GT；
- gate① 新增的 `correction.axis_exactness` advisory 只检产品，不读答案。

综合稿 opus 锁 B-1（AST 扫描钉死共享模块 import 闭包不含 `judge.gt`/`gt_schema`/`test_baseline`）是可执行且充分的守卫。R-4 成立。

### P9 · view_bindings.json 未入 git + 不在签名清单 —— **成立（第四次同型复发，逐项核实）**

```text
git log case_tests/.../score_inputs/view_bindings.json   → 空（从未 commit）
git check-ignore view_bindings.json                       → exit 1（未被 .gitignore 忽略，可 add 却没 add）
git status --porcelain .../sm24_anchor/                   → ?? score_inputs/（未跟踪）
view_bindings.json mtime = 2026-07-27 03:40
gt.json / review_ack.json mtime = 2026-07-26 06:49（转正时刻）
review_ack.json signed_at = 2026-07-26T06:48:55Z，绑 source_dxf/request/overlay/review_index 四 hash，无 view_bindings
review_index.json files 清单 = gt/gt.json + 7 renders + opening_elevation_audit + review_annotations，无 score_inputs/view_bindings
grep view_bindings in review/                            → 空（不在任何 review 清单）
```

**逐项属实**：未入版本控制、不在 07-26 签名清单、mtime 晚于转正。即「人签转正之后，往受保护答案根写了既不在签名清单、又不在版本控制里的文件」。综合稿 R-6 已正确登记为同族第四次复发 + 两份规矩打架（`new_case_guide §0.3` 要它放此路径 vs 转正通道要受保护目录 ⊆ 签名清单），并裁定「文件入版本控制（无条件）+ 清单口径归 gt 标准产物清单批 + 施工开工/收工两次 git status 逐字相等」。成立。

### P10 · 反向找漏：三稿共漏 + 综合失真 —— **命中一个 MAJOR 未裁定分歧 + 两处 MINOR 补遗**

**P10-①【MAJOR，施工前必须显式裁定】两源稿对「身份池作用域」实质性分歧，综合稿未裁定。**

- **opus §2.5**：池 = `(文档侧 ∈ {gt, product}, floor_id, 轴)` —— **文档内聚类、跨文档不联合**。理由（原文）：「避免让 GT 的身份受产品输入影响（那会开一个『产品能改自己分母』的口子）」。跨文档只在 `_candidate`/覆盖配准层带容差（合法度量层）。
- **sol §2.1/§3.1**：「一次 score request 内，按 (coordinate_frame, floor_scope, axis) 收集 **GT 与 product** 的所有坐标」+「gate② 对 **GT + 产品联合**建立 request-local atom」—— **联合池**。

两版**互斥**：opus 的池不含跨文档边，sol 的池含。综合稿 C-1 写「对**一次 score request 内**实际出现的坐标按轴建图…取连通分量作为身份原子」——字面读作**联合（sol）**，但**未明确裁定**，也**未回应 opus 的反论**（产品改自己分母）。

后果差异（实测级）：联合池下，产品坐标若落在 GT 墙端点附近（< 直径阈 ~5e-11 m），会并入同簇、簇代表偏移，使 **GT 墙长（分母）对产品输入敏感**——正是 opus 警告的口子；文档内池下 GT atom 独立于产品、分母稳定。幅度虽亚皮米级（簇直径 ≤ 5e-11 m，墙长偏移 ~1e-10 m，远低于分数分辨率），但属**测量独立性的架构原则**，且对抗场景或未来放宽阈时会被放大。综合稿把「联合切点」（C-3，两版都同意的覆盖机制）与「联合身份池」（C-1，两版分歧的身份机制）混在「联合」一词下，掩盖了后者未裁定。

**这是本轮唯一实质性施工阻断项**：施工者必二选一，且两选择给出不同的正确性保证。综合稿须在 C-1 显式裁定并回应反论。**我倾向 opus 的文档内池**（保分母稳定、闭合「产品改分母」口子、与 gt 铁律精神一致）；若采 sol 联合池，须显式接受「亚皮米级偏移」取舍并写入合同。

> 注：此非「综合稿做错决定」，而是「两源稿分歧未被综合裁决」。综合稿自定位「只承载决定与出口、推导细节见两源稿」——但池作用域是**未定决定**而非已定细节，须在综合稿落锤。

**P10-②【MINOR】输入合法性合同未载入综合稿正文。** sol §2.2 明确定义「合法 score request」四条件（同意图直径 < 阈 / 异意图间距 > 阈 / 无恰等上界 / 归并不坍缩），这是 C-1「无条件吸收」结论的**真前提**。综合稿 C-1 把结论表述为无条件，却未把这四条件载入正文。施工者若只读综合稿，可能实现聚类却不定义/执行输入合同，使「无条件」声称落空（变成「合同外静默」）。建议综合稿 C-1 附一句指向 sol §2.2 合同，或把四条件浓缩列入。

**P10-③【MINOR】ScoreIdentityV8 摘要变更的开工门未入综合稿验收总纲。** opus §4.4 指出改 `segment_scorer` Literal 为 `"c2_segment_coverage_v2"` + 加 `coordinate_identity` 字段会改变新 run 的 `ScoreIdentityV8` 摘要，并立锁 D-1（开工先核 `test_c2_b4b_contract.py` 是否钉死 identity 摘要常量）。综合稿 §5 验收总纲 8 条未含此开工门。建议补入，免施工者撞钉死常量。

**未发现综合稿对两源稿的失真改写**：R-1 取护带（采 Claude 结构）、R-3 三分 criterion（采 GPT）、C-4 字节不动（两版一致）均忠实承袭，3.96× / 1.67× / 1000× 等数字我独立复算吻合。综合稿无「声称大于实况」之处（对比 r2 对施工日志的同类批评）。

---

## 2. 必改项（APPROVE-WITH-CHANGES 条件）

1. **【MAJOR·施工前】C-1 显式裁定身份池作用域**（文档内 opus vs 联合 sol）并回应「产品改自己分母」反论。我推荐文档内池。该项不定，不许开 W1 派工单。
2. **【MINOR】C-1 附载输入合法性合同**（sol §2.2 四条件），使「无条件」结论的前提显式可审计。
3. **【MINOR】§5 验收总纲补 ScoreIdentityV8 摘要变更开工门**（opus D-1）。

P9 治理项（view_bindings.json）综合稿 R-6 已正确登记，无需改动，仅此确认准确。

---

## 3. 被审文件字节不变自证

审阅全程仅 Read + `/tmp/glm_judge_review/` 探针，未对任何被审文件/生产码调用 Edit/Write。

```text
# 综合稿（被审对象）
24274dcded36a9c65975509b213ccccf9f0cc25afbc13b333df7771f8ed50d7f  AI_agent/proposals/judge_identity_and_metric_plan.md

# 来源稿（用于核实综合忠实度，只读）
1795c62b20bbecd4a235b82d897bef08bebe1927a0a3140e7557b552f8cb5e5a  AI_agent/proposals/judge_identity_and_metric_plan_opus.md
6731152a8e80f338ccf25b7685aa0164fbdfd5422af48775d2e1aa45474a17ea  AI_agent/proposals/judge_identity_and_metric_plan_sol.md

# 关键生产码（只读，用于核实 P6/P7/P8）
f3f4e60e720030ac49af0bad6bd553e129a9856c27e3358f012153689ffd1644  src/agent/judge/segment_score.py
92c2f93d6b41735e8d1f7d51a17e5a8719f907dabde1c951e4a33e515d9c5aa1  src/agent/correction/cell_geometry.py
8e64256cce17b01c04aae1997bc100161335aa6128fabfd45fc2d273f8828a9e  src/agent/judge/score_policy.py
cf50d4c3a14d9446445c688bc9d4d1e7ef6a2356798d9f5d5b01f1f71e111da5  src/agent/judge/score_service.py
14a676c7f29bd45d810deef3929ebc5a4020c7d3b6ca1cea62cacfdc4eff970b  src/agent/judge/gt_schema.py
```

审前（开工首条 sha256 记录）与审毕两组**逐字一致**。

## 4. 探针清单（全部落 /tmp，零仓库写入）

| 脚本 | 产出命题 |
|---|---|
| `/tmp/glm_judge_review/probe_identity.py` | P1 ulp 量级、P2 单点边界零测度、P3 sm24/sm21 漂移实测 + 双向余量表 |
| `/tmp/glm_judge_review/probe_lattice.py` | P1 r2 格边界 binary64 复现 + 机械扫描跨格对、P1 单链接聚类六组矩阵（护带 vs sol） |
| `/tmp/glm_judge_review/probe_q3.py` | P4 16 邻接 / 57.86 m / 3.96× / Shapely 独立复核 / 分区不变性 |
| `/tmp/glm_judge_review/probe_q4.py` | P5-(a) 支撑线间距 1.00/1.64 m、余量 1.67× |
| `/tmp/glm_judge_review/probe_amb.py` | P5-(b) score_match_ambiguous candidate_assignments=4 实证触发 |

复现：`python3 /tmp/glm_judge_review/probe_*.py`（各自带 `sys.path` 注入，仓库根执行）。

## 5. 治理数据点

- 本轮 10 命题：9 成立 / 0 不成立 / 0 无法判定；P10 反向找漏命中 1 MAJOR（未裁定分歧）+ 2 MINOR。
- 与本系列前几轮 GLM 验证性审阅一致：核心可信、活体探针独立验真、只审不修自证。本轮**未发现综合稿对两源稿的失真改写或「声称大于实况」**（区别于 r2 对施工日志的同类批评）。
- 综合 = 跨家族双独立出案后的施工基线，质量明显高于单稿；唯留「身份池作用域」一处在两源分歧上未落锤，是综合方应补的最后一锤。
