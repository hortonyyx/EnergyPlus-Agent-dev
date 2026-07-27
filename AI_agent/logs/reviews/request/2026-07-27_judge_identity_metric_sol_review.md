# 对抗审阅单 · 判卷器「数值身份 + 计分度量」施工批（2026-07-27）

- **审阅方** = sol（gpt-5.6-sol，effort max）· **施工方** = GLM-5.2（谁写谁不批，跨家族）
- **被审对象** = commit `29a1ce0 7.27_JudgeIdentityMetricV2`（11 文件 / +1007 −144）
- **主控** = Opus 5（本单 + 轻门）

---

## 0. 你的任务

对 `29a1ce0` 做**活体探针对抗审**。不是复述施工方简报——**批准者只看原始需求 + diff + 测试输出，不看执行者长篇自述**（协作规约纪律）。
出 **APPROVE / APPROVE-WITH-CHANGES / REWORK**，findings 分 BLOCKER / MAJOR / MINOR / NIT，每条给**可复现的活体探针**（改哪一行 → 什么变红/变绿）。

**权威规格（按此审，不按施工方叙述）**：
1. 施工基线 [proposals/judge_identity_and_metric_plan.md](../../../proposals/judge_identity_and_metric_plan.md)（已过 GLM 跨家族对抗审）
2. 派工单 [2026-07-27_judge_identity_metric_construction_dispatch.md](2026-07-27_judge_identity_metric_construction_dispatch.md)（§5 验收清单 A1–A11 + §5-B 点名风险）
3. 施工方执行日志 [2026-07-27_judge_identity_metric_glm.md](../execution/2026-07-27_judge_identity_metric_glm.md)（**当线索，不当证据**）

---

## 1. 这批要解决的真问题（背景，两分钟）

判卷器原来用「把坐标四舍五入到 1e-12 的格子」判断两个数是不是同一个坐标。**任何这样的全定义离散化都有边界，边界两侧任意接近的两点被判成不同坐标** —— 已连续两轮制造假红（同一十进制几何的不同浮点写法被诬告成拓扑破洞）。本批改为：**对本次实际出现的坐标做单链接聚类 + 直径守卫 + 落在护带内就响亮拒绝**（部分函数：分不清就拒绝，不静默给答案）。

同时两处度量修正：墙的分母从「界面条数」换成**长度（米）**（真实 sm24 实测每米权重最大/最小差 3.96×）；**联合切点原子化**取代一对一指派。

---

## 2. 主控预扫点名的三处（请**独立核实**，不要采信我的判断，也不要因为我列了就默认有问题）

主控预扫 diff 时注意到三处**形状可疑**，请优先投放探针。**结论由你独立得出。**

### P-1 · 既有测试被改写（最高优先）

[tests/test_c2_b4b_phase_b.py](../../../../tests/test_c2_b4b_phase_b.py) 两条既有测试被改：

**(a)** `test_b4b_b2_exact_tie_is_rejected_without_id_tiebreak` → 整条改写为 `test_b4b_b2_duplicate_coverage_routes_to_duplicate_not_ambiguous`。
原断言「两个完全重合的观测 → 抛 `score_match_ambiguous`」被删除，改为断言「→ `duplicate` 状态，不抛」。
- 语义变更本身与基线 C-3 一致（该错误码在平面墙通路应结构性不可达）。**请核的是：删掉的那条负锁，其保护的失败模式是否被新锁真正接手？** 新测试断言了 `duplicates` 计数与 `eligible_units`，但（主控预扫所见）**未断言 `no_duplicate_wall_strokes` criterion 因此判 fail**。若确实没有，重笔是否可能全链静默通过？

**(b)** `test_b4b_b2_segment_states_include_complete_within_miss_extra_and_extent`：
- 断言从 `{...} == {row.status ...}`（**精确集合相等**）弱化为 `{...} <= {...}`（**子集**）⇒ 多出任何状态不再变红。请核这是必要的还是断言弱化。
- 原「超长观测 `long` (2→3.2 对 target 2→3) 产生 `within_tolerance` 且 `extent_symmetric_difference_m == 0.2`」的断言被**删除**，换成一个全新的 `offset` 观测。注释声称新语义是「超长部分算 extra 长度、被覆盖的 target 保持 complete」。
- **请核：这个新语义在哪里被断言？** 若旧断言删了、新语义无锁，就是「改测试让它变绿」。

### P-2 · A8「答案原子/分母 = 答案字节的纯函数」的锁强度

基线 A8 与 C-1′ 要求：同一份答案配不同产品，**原子集合与 `denominator_m` 逐字节相同**（这条锁的作用是把「产品能改自己分母」机械焊死）。
施工方写了 `test_a8_answer_denominator_independent_of_product`（[tests/test_judge_identity_metric.py:257](../../../../tests/test_judge_identity_metric.py#L257)），主控预扫认为**这条锁比施工方自己披露的要强**（它确实用两个截然不同的产品跑同一答案）。
- **但请核**：分母比较用的是 `pytest.approx`，基线要求的是**逐字节相同**。`approx` 能否放过一个真实的「产品影响答案分母」的微小污染？
- 施工方在披露 #2 里称这是「架构锁，非行级守卫，neuter 不触发符合预期」。**请独立判断**：把 GT 池与产品池联合建池（即制造 C-1′ 明令禁止的情形），这条锁会不会红？不红就是 false-lock。

### P-3 · §5-B 点名风险的出口 2 被打了折扣

派工单 §5-B 出口 2 要求：**新增多段覆盖的窗夹具**（既有窗夹具全是单段，这是基线 §3 点名的「门是真的、锁是缺的」高危处）。
施工方披露 #1 承认用的是 `_resolve_facade_product_to_gt` 的**单元夹具**，不是完整 va e2e 窗夹具，理由是「窗走 facade 映射通路（candidates==1），interior 多段覆盖架构上不影响窗」。
- **请独立验证这个理由是否成立**：窗宿主解析（[score_service.py](../../../../src/agent/judge/score_service.py) `build_correction_host_resolver(product_to_gt_segment=...)`）拿到的 `product_to_gt` 里，interior 多对多的条目**真的进不了窗的宿主判定**吗？
- 若理由成立 → 记 MINOR/跟进项即可。**若不成立 → 这正是基线点名的静默绑错墙，且没有任何测试会红 = BLOCKER。**

---

## 3. 必须独立验真的验收出口（派工单 §5，不限于此）

| # | 出口 | 建议探针 |
|---|---|---|
| A1 | 三个活体反例转绿（sm24 `8.059999999999999`↔`8.06` / `0.1+0.2`↔`0.3` / r2 量子边界对） | 摘掉聚类是否即红 |
| A2 | **1e-9 缺口双侧仍红**，错误码逐字不变 | 断言的是精确码串还是宽松 match |
| A3 | 护带内歧义 = 响亮拒绝且分码正确 | 构造护带内距离；确认既非静默合并也非静默分裂 |
| A4 | Q3 三情形：整墙漏画 `0/4` / 画对但分段不同 `4/4` / 画对一半 `2/4` | 三条是否真独立 |
| A5 | `case_tests/test_baseline/gt/` **逐字节不变** | 独立 hash 对照，别信简报 |
| A6 | sm21 legacy 通路零变化（分数字节 + 渲染像素 hash + 分派路径） | legacy 是否真未受 v2 身份影响 |
| A7 | 窗宿主多段覆盖锁 | 见 P-3 |
| A8 | 答案原子/分母 = 答案字节纯函数 | 见 P-2 |
| A9 | **输入合法性合同四条运行时被执行**（① 同意图坐标直径 < 合并阈 ② 异意图最小距离 > 分裂阈 ③ 无距离落护带内 ④ 归并不致零长边/重复顶点/环自交/owner 重数冲突）；**只聚类不执行合同 = 不通过** | 四条各造违反夹具，逐条确认响亮拒绝 + 分码 |
| A11 | 每条锁自带指定 neuter，**共用守卫的锁归并披露** | 施工方自查表列 5 守卫（A 合并 / B 护带 / C 直径 / D 长度 / E match），**独立复算**是否真零 false-lock |

**另请核 R-2（阈值推导纪律）**：施工方取 `merge=1e-12` / `split=1e-11` / `diam=1e-11`，声称由实测推导（sm24 gt 零漂移、最大 1.78e-15）。
- 注意 `merge=1e-12` **恰好等于被删掉的旧量化常量 `_COORDINATE_QUANTUM`**。请核这是实测推出的巧合，还是把旧数字换了个名字（基线 R-2 明令禁止先定数字后补论证）。
- 核两侧余量：合并侧对实测漂移、分裂侧对 1e-9 缺口，各多少倍，是否如声称。

**R-4 口径**：新写的拒绝路径，是否有任何一条在说「这几何不合法」而非「我量不了」？基线明确：判卷器**只许说 unsupported，不许说 broken** —— 这是三轮假红的结构性根源。

---

## 4. 边界与纪律

- **只审不修**（谁写谁不批）。发现问题写 finding + 探针，**不要动生产码**；验锁 neuter 只在 `/tmp` 副本做，工作树必须还原。
- 全仓基线：施工方声称 **1706 passed + 10 xfailed**（改造前 1685 + 10）。请**独立跑全量**核实（默认并行，约 4–8 分钟），不采信简报数字。
- 不得改 `AI_agent/CLAUDE.md`、不得动 `case_tests/test_baseline/gt/`、不得在仓库根落文件。
- 裁决书落 `AI_agent/logs/reviews/verdict/2026-07-27_judge_identity_metric_sol.md`。

## 5. 主控提示

- 本批**连续第十三批**升一档交叉对抗审。前十二批**首轮均抓出 MAJOR**，其中多次是「生产码本体零 bug、但锁是假的」（false-lock = false-green 近亲）。请把探针预算优先投在**锁的真伪**上，而不是重读生产逻辑。
- 施工方主动披露了三条「性质标注非 PARTIAL」的折扣项（见其日志末尾）。**主动披露不等于免审** —— 恰恰是最该投探针的地方。
