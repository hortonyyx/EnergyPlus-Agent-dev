# 派工单 · 判卷器「诊断仲裁 + 守恒判据 + 来源身份」施工批（2026-07-28）

> **施工 = sol（gpt-5.6-sol，effort=high）** / **对抗审 = GLM-5.2（跨家族，验证性）** / **轻门 = 主控 Opus 5**。
> 用户 2026-07-28 拍板；**整批做完再审一次**（不拆多轮对抗审），Slice 边界由主控做不花额度的轻门检查点。
> **施工基线 = [judge_arbitration_and_provenance_plan_sol.md](../../../proposals/judge_arbitration_and_provenance_plan_sol.md)**（1380 行，累计式自包含；已过 [GLM 对抗审](../verdict/2026-07-28_judge_arbitration_design_glm.md) + [主控终审](../verdict/2026-07-28_judge_arbitration_design_controller_final.md) + 补稿三条复核）。
> **基线是唯一权威**，本单只加纪律、护栏与落到文件:行的开工门。**两者冲突以基线为准并立即回报主控。**

---

## 0. 一句话任务

按设计稿 §7 的 Slice 0–4，把判卷器的三处立足点从「隐含假设」换成「可复算证据」：**谁有资格判红**改成全称证明（A）、**有没有多收钱**改成区间 owner 重数（B）、**这两个数凭什么焊成一个**改成来源身份 + 拓扑 alias 证书（C）。

**你就是这份设计稿的作者。** 本单不复述设计，只钉住三件事：不许在施工时把自己定的边界重新降级为假设；不许半交付；每条锁必须真绑。

---

## 1. 纪律（先读，违反即返工）

1. **`case_tests/test_baseline/gt/` 下任何字节不得改动。** sm24 已签字答案不重签、不迁移、不「规范化」。施工前后各跑一次逐字节 SHA-256 manifest 对照，有差异 = 施工直接失败（设计稿 §9 硬约束首条）。
2. **开工 / 收工两次 `git status --short` 必须逐字相等。** 除本单与设计稿列明的文件外不得新增/删除任何文件；**尤其不得在仓库根落文档或目录**（CLAUDE.md §5 硬规矩）。
3. **不得改管理文档 `AI_agent/CLAUDE.md`**（07-26 有施工方越界改它被判 MAJOR 的先例）。`AI_agent/` 下只允许写本单指定的执行日志。
4. **gt 铁律（不变量 #4）**：新模块**零 gt import**；生产路径绝不 import 判卷器；来源 key 全在 judge 内存派生，**不加 GT 字段、不改 wire**。
5. **不许先定数字再补论证。** 任何新阈值/容差须先给实测分布再给数字，并给两侧余量倍数。**本批还额外禁一条**（R3-B2 直接教训）：不得再在「固定 `1e-9`」与「零容差」之间摆动——守恒判据必须是结构性的（区间原子 owner 重数），不是数值比较。
6. **每条锁自带指定 neuter，共用同一 guard 的锁必须归并披露。** 自查表逐条写「摘掉哪一行 → 哪几条测试变红」。**不接受「代码看起来会覆盖」**（设计稿 §7 Slice 0 原话）。neuter **只在 `/tmp` 副本执行并还原**，工作树不得留 neuter 状态。
7. **诚实优先于完成。** 做不完就精确标 PARTIAL 并说清卡在哪（对标 B4b Phase D 正面样板），**不许伪造 neuter 自查表**。上一位施工方三轮里有两轮栽在自查表声称大于实况。
8. **跑测三档节奏**（[codex_execution_protocol §7.5](../../../guides/codex_execution_protocol.md)）：中间轮用 `python scripts/tool_scripts/affected_tests.py` 算受影响子集（**禁自由裁量**）；**每个 Slice 交付前跑一次全仓**（`pytest`，默认并行，约 4–8 分钟）。基线见 §3。

### 1.1 sol 执行护栏（三条硬约束，规约 §5 明列）

规约里 sol **原则上不当执行器**（相比同级模型更易过度追求目标：替换用户指定资源、声称完成未验证工作）。本轮由用户拍板破例，故三条护栏强制生效：

- **① 删除 / 覆盖 / 推送 / 外发必须单独授权。** 特别是：不得删除或重写既有测试以迁就实现（设计稿 §8.1 列的「必须保留原意的锁」逐条为准）；不得 `git push`；不得改 `.gitignore`。
- **② 每阶段给可验证证据**：测试输出原文尾部、`git diff --stat`、实际状态命令输出——**不接受自述式「已完成」**。
- **③ 限单次变更范围**：完成一个 Slice 就停下来重新审视计划，不得跨 Slice 连推。

---

## 2. 开工门（动手前先做；主控已预扫，照做别另想）

**G-a · helper identity 升版（设计稿 §3.3 已定死，本单只给落点）**
- 现状 [score_schema.py:37](../../../../src/agent/judge/score_schema.py#L37) `SEGMENT_SCORER_HELPER_VERSION = "b4b_segment_score_v2"`（上一批已从 v1 升到 v2）。
- 本批升为 **`"b4b_segment_score_v3_ic1"`**，`Literal` 同步（**不保留 v2 union**），并与 identity contract `"1"` 交叉验证。引用点至少三处：`score_service.py`、`tests/test_c2_b4b_contract.py`、`tests/test_c2_b4b_phase_d.py`。
- **旧 typed c2 v3 sidecar/cache 因此 miss，这是要的效果**，不是回归。若某测试因派生件失效而红 = 该测试把派生件当权威，**报告主控，不要加兼容层绕过**。

**G-b · 判卷配置 hash（条件触发，主控已核当前不触发）**
- [tests/test_c2_b4b_contract.py:65-66](../../../../tests/test_c2_b4b_contract.py#L65) 钉死 `judge_score_config_sha256(config) == "ac2c1470…"` **且断言同一串 hash 内嵌在 `skills/intake_pipeline/1_correction/A0_contract.md`**。
- 主控已核：**当前身份三阈值不在 `src/configs/judge_score.yaml` 里**（是代码常量），所以只要本批不往该 yaml 加字段就不会撞。
- **一旦你决定把任何新参数落进 `judge_score.yaml`**：新 hash 由代码现算，**同步更新测试常量 + A0_contract.md 内嵌值**；改 A0 时遵 CLAUDE.md §5#5（skill 库 = 英文纯当前版本 spec，**不写时间戳/版本日志/缘起 case**）。
- **别混淆**：yaml 里既有的 `opening_assignment_tie_epsilon: 1.0e-9` 是**开窗匹配的并列判据**，与本批「1e-9 拓扑缺口必须判红」是两个不同层的 1e-9，不合并、不互相引用。

**G-c · Slice 0 先落会红的锁（设计稿 §7 Slice 0，本批第一个交付物）**
- A-L3（duplicate + unrelated advisory 被洗成 NA）/ A-L9（缺 missing-evaluator 请求级计数产物）/ B-L4（三相邻 span 的 1-ulp 假红）/ C-L1、C-L7、C-L11（来源丢失、完整拓扑、版本门）。
- **要求**：这批锁写完先在**未改生产码**的现树上跑一次，逐条记录实际红/绿与失败输出原文。**任何一条没红 = 停下报告主控**，不许「顺手把生产码一起改了让它绿」。
- 现码坐标供参考：`_SUBINTERVAL_SUM_TOL` 在 [segment_score.py:72](../../../../src/agent/judge/segment_score.py#L72)、消费点 [:798](../../../../src/agent/judge/segment_score.py#L798)；`_assert_obs_conservation` 在 [:804](../../../../src/agent/judge/segment_score.py#L804)；`score_identity_support_ambiguous` raise 在 [:875](../../../../src/agent/judge/segment_score.py#L875)；`_cluster_axis` 在 [:88](../../../../src/agent/judge/segment_score.py#L88)、两个裸 float 调用点在 [:147-148](../../../../src/agent/judge/segment_score.py#L147)（**这就是 C 要消灭的展平旁路**）。
- `missing_predicate_evaluator*` 全仓当前零命中 = 全新机制，无既有接线可复用。

---

## 3. 基线与提交纪律

- **全仓基线 = `1725 passed, 10 xfailed, 0 failed`**（主控 2026-07-28 开工当场在 `cce6e83` 干净树上独立跑出，默认并行 4:28）。本批要求**零非预期回归**，新增测试计入增量。
  > 注：`AI_agent/CLAUDE.md` 里记的 `1671` 是 r0 之前的旧数（前三轮返工新增的测试已在树上），**以本行为准**。
- **零 golden 改动**；如必须改，**停下报告主控**，不得自行决定。
- **按 Slice 独立提交**（设计稿 §7 建议，本单硬化为要求）：Slice 0 / 1 / 2 / 3 / 4 各至少一个 commit，message 仿 `<月.日>_<英文标签>`。
- **每个 Slice 提交后回报主控一次**（一句话 + commit SHA + 全仓测试尾部）。**主控在每个 Slice 边界做一次轻门**（独立跑全量 + 亲核 diff），不消耗你的额度；主控若发现方向问题会当场叫停，这是本轮唯一的中途纠偏点。
- **不可半交付项**：设计稿 §7 每个 Slice 末尾的「不可半交付」段逐条生效。特别点名两条历史复发点：
  - **C**：只传 source key 但聚类后又回到 `raw float -> rep` = **未实施**（上一位施工方两轮都停在这）。
  - **B**：只把 `sum` 换成 `math.fsum`、仍以两个独立浮点总量比较定案 = **未实施**。

---

## 4. 验收 = 设计稿 §10 DoD 逐条

本单不另立验收表。**验收标准 = 设计稿 §10 的 16 条 Definition of Done**，GLM 将照它逐条验。交付时你必须给出**逐条自评表**（16 行，每行：满足 / PARTIAL + 卡点，附证据指针）。

主控额外硬性单列两条（不许混在常规回归里）：

- **D-1 · 真实 sm24 逐行 diff 是必跑项**（设计稿 §8.3 四步，含改造前 baseline 必须走真 `score_typed_attempt` 正门生成、**不许手造 `PlanSegment` 代替**）。baseline/new 文件 hash + 完整 diff 附进执行日志。**row status / 配对 / criterion verdict / denominator 语义的任何变化一律阻断**，不得以「已知 1 ulp」概括放行。
- **D-2 · 性能实测**（§10 第 15 条）：exact-rational 账本在**真实最大 fixture** 上给时间与内存实测，**不得以正交盒子数量估算代替**。

---

## 5. 交付格式

1. **执行日志**落 `AI_agent/logs/reviews/execution/2026-07-28_judge_arbitration_sol.md`，含：
   - 每个 Slice 的 commit SHA + 一句话
   - **Slice 0 的现码红/绿实测记录**（G-c）
   - **neuter 自查表**：逐条「摘掉哪一行 → 哪几条测试变红」，共用 guard 归并披露
   - **§10 DoD 16 条自评表**
   - **D-1 sm24 逐行 diff** + **D-2 性能实测**
   - 每个 Slice 的全仓测试输出尾部
   - 开工 / 收工两次 `git status --short`
   - sm24 受保护树施工前后 SHA-256 manifest 对照
2. **诚实披露**：未完成项精确标 PARTIAL + 卡点，不伪造自查表。
3. 完成后回报主控 → 主控轻门 → 派 GLM-5.2 照设计稿 §10 + 各节「机械验收锁与指定 neuter」做验证性对抗审。

---

## 6. 主控为什么这样派（给你的上下文，不必回应）

- 这批**前三轮全被判 REWORK**，裁决书都是你写的：[r1](../verdict/2026-07-27_judge_identity_metric_sol.md) · [r2](../verdict/2026-07-27_judge_identity_metric_sol_r2.md) · [r3](../verdict/2026-07-27_judge_identity_metric_sol_r3.md)。
- 主控对三轮失败的归因是**「机制选对、边界留给施工方猜」**——所以本轮把边界写进了设计稿本体（这也是主控终审时不采纳 GLM「让施工方开工前自己补两条 MAJOR」的原因）。
- 你既是设计者又是施工者，**边界理解误差应当最小**。相应地，**「我当时的意思是……」不是可接受的交付说明**：判定必须由代码里可复算的证书支撑，这正是本稿 §0 的那条共同原则。

---

## 7. 主控备注（施工方不必处理）

- 调用须显式传 model + effort（规约 §4）：`gpt-5.6-sol` + `model_reasoning_effort=high`。裸调用会落 CLI 默认 = sol + low。
- 全仓基线绿数 `1725 / 10 xfail / 0 failed`，主控开工当场独立跑出（`cce6e83` 干净树，4:28）。
- `case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json` 已入版本控制（上一批遗留已清）。
- 本单同时是「gt 标准产物清单」批的输入之一（R-6 侧车口径收口），但**不在本批范围内**。

---

## 8. 主控裁定 · Slice 0 轻门（2026-07-28）

**轻门结论 = PASS，可进 Slice 1。** 主控独立全量复跑 = **`6 failed, 1725 passed, 10 xfailed`（4:09）**，失败恰为六锁、passed 与基线 `1725` **同数** ⇒ **无任何其他测试跟着变状态**。diff 仅两个新文件（`tests/test_judge_arbitration_slice0.py` +567 / 执行日志 +576），**生产码零行改动**，`case_tests/test_baseline/gt/` 与 `AI_agent/CLAUDE.md` 零触碰，`git status --short` 仅余本派工单（主控自己的未跟踪文件）。六锁独立复跑全红，**且红的理由逐条正确**：

| 锁 | 实测红因 | 主控判定 |
|---|---|---|
| A-L3 | 得 `score_unsupported_combination`、期望 `score_product_identity_invalid` | **R3-B1 活体复现**——真 duplicate 被无关 advisory 洗成能力 NA。靶心正确 |
| B-L4 | `score_denominator_nonconserving at scoring.denominator_totality` | **R3-B2 活体复现**——三段合法铺满被 1-ulp 判假红。靶心正确 |
| C-L1 | `raw floats reached _cluster_axis before source identity was preserved` | **R2-B2 核心**——来源身份在进聚类器前丢光。靶心正确 |
| C-L7 | `DID NOT RAISE` | 非相邻重复顶点当前被静默接受（合同④未执行）。靶心正确 |
| A-L9 / C-L11 | `ModuleNotFoundError`（`certifier` / `identity_provenance`） | 新机制无既有接线，「模块不存在」是此阶段唯一可能的红。**接受，但记为弱信号**：这两条的真正承重要等对应 Slice 落码后由行为级 neuter 补证 |

### 8.1 六条欠规格边界 —— 主控逐条裁定（即刻生效，与设计稿同等约束力）

施工方在写锁时撞出六处「设计稿定了语义、没定接口形状」的边界并**如实上报、未自行降级为假设**——这正是本单 §6 要的行为，**记一次正面数据点**。裁定如下：

1. **A-L9 certifier 调用面 —— 采纳施工方选择并加一条硬约束。** 模块 `src.agent.judge.certifier`；请求函数 `certify_and_arbitrate_request(diagnostics, capabilities, evaluator_registry, request_key, identity_code)`；registry 键 `(predicate, predicate_schema_version) -> callable`；evaluator 返回四个 proof-status 字符串。
   **加约束**：四个状态须是代码里的**封闭枚举**，不是自由字符串；**已注册的 evaluator 返回枚举外的值 = 编程错误，必须 raise，不得降级为 NA**。理由 = 「未知 *predicate* 有意 NA」是设计过的 fail-safe，「已注册 evaluator 返回垃圾」是代码缺陷；把后者也 NA 掉就是设计稿 §0#4 明令要避免的「对未知形态系统性放水」。
2. **B-L4 成功态 ledger audit 暴露面 —— 采纳 `_build_observation_ledger` seam，但必须是真接线。** seam 返回的 ledger 必须**就是计分实际消费的那一个**，不得是旁路重算。
   **加验收**：Slice 3 须给一条锁证明「篡改 seam 返回值 ⇒ 计分输出随之改变」。否则 monkeypatch 捕获的是个生产不依赖的函数 = **典型 false-lock**（本批 M-1/M-2/M-4 与 07-26 `test_r4_3` 同型）。
3. **C 模块与 envelope 构造签名 —— 采纳。** `src.agent.judge.identity_provenance`；`IdentityInputEnvelope(contract_version, source_schema, side, floor_id, occurrences, topology)`；`SourceTopologyIndex.empty(side, floor_id)`。
   **加约束**：`contract_version` 按**精确字符串**比对，禁类型强转与序关系（`"2"` 与 `2` 都必须红，不许一个静默通过）。
4. **错误 context 容器形状 —— 采纳 flat 形态与给定键集。**
   **加约束**：该键集须**单点定义**（模块级常量 / typed 结构）并在 raise 时断言完整，缺字段即 raise。否则 §2.4 的「最低字段」会退化成各调用点各写各的，事后无法复算 = 本批共同原则的直接违反。
5. **footprint source key 的 `owner_id` —— 主控裁定（施工方正确地没有自行决定）**：
   - `owner_kind="footprint"`、**`owner_id = floor_id`**、`ring_id = "exterior"`（内环用其结构序号派生的 id）。
   - 理由：① 是输入结构的**纯函数**，不引入新的自由度；② 每个 `(side, floor_id)` 恰有一个 footprint，故取值唯一、不产生歧义；③ **保持 `owner_id` 非空**——若为此开 `Optional`，重数/配对逻辑就要多一条 null 分支，而「静默接受」历来就藏在这类分支里（合同④三项全静默接受即前车之鉴）。
   - **随之绑定的硬约束**：**owner 身份在全代码库一律是 `(owner_kind, owner_id)` 二元组，任何地方都不得单用 `owner_id`**。否则某个 cell/zone 的 id 恰好等于楼层 id 时会与 footprint 相撞。**须配一条锁**：构造「cell id == floor id」的夹具，证明 footprint 与该 cell 不被判为同一 owner。
6. **DoD #16 标 PARTIAL、不伪造 neuter 实跑 —— 接受，并记为正面数据点。** 目标 guard 尚不存在时声称「已实跑并转红」正是本批 r1 栽的那一跤。
   **加约束**：每条 neuter 须在其对应 Slice 落码后**在 `/tmp` 副本逐个实跑并回填真实红数**；**最终交付不得残留任何未实跑的 neuter**——届时 PARTIAL 不再是可接受状态。

### 8.2 主控另裁一条（施工方未列，主控复核夹具时发现）

**B-L4 夹具用 `p1[1]==p2[1]==1.0` 筛出设计指定的三段，把 GT 顺带产生的两条竖墙排除在断言之外。** 作为「选定被断言的行」这是正当的；但**筛选绝不能变成绕开红**。
**Slice 3 须补一条伴随断言**：同一夹具在**不筛选**的完整段集上跑 `match_plan_segments`，也必须无守恒类错误地进入计分。缺这条，本锁只证明了「我挑的那三段不假红」。

---

## 9. 主控裁定 · Slice 1 轻门（2026-07-28）

**轻门结论 = PASS，可进 Slice 2。** 主控独立全量复跑 = **`3 failed, 1745 passed, 10 xfailed`（4:16）**，与施工方所报逐字一致；失败恰为 A-L3 / A-L9 / B-L4（Slice 2/3 范围），**C-L1 / C-L7 / C-L11 合法转绿**；passed 由 1725 → 1745（+20 全为新增锁），**零既有测试状态变化**。diff 四文件（新 `identity_provenance.py` 886 行 / 新测试 476 行 / `segment_score.py` +839−130 / 执行日志），**未改动任何既有测试文件**（设计稿 §8.1「必须保留原意的锁」守住），gt 与 CLAUDE.md 零触碰。

主控 §8 裁定的两条锁**已落地**：`test_owner_identity_uses_kind_and_id_when_cell_id_equals_floor_id`（裁定 5 的 owner 二元组）+ `test_c_l11_contract_version_is_exact_string_without_coercion`（裁定 3 的精确串比对）。

### 9.1 主控点名风险 —— 施工方如实回答，判定如下

**（a）`_cluster_axis` 残留的 legacy 浮点通道 —— 施工方明确承认「不是总锁」，判定接受其诊断、采纳其建议并定死期限。**
- 实况：该通道存在的唯一原因是 `tests/test_judge_identity_metric.py` 的三条历史坐标反例仍用**裸浮点**调用。施工方用 `rg` 静态枚举调用点（非 AST、非 call graph），现有生产直接调用只有 `_build_floor_identity` 内 x/y 两处、已被三类 adapter 锁覆盖；但**挡不住将来新写一个 `topology=None` 的调用**。
- **判定**：这不是方向偏差，是排期偏差——**设计稿 §8.2 本就规定「裸 float `_cluster_axis` 锁改为 occurrence API；历史语义不删」**，施工方选择了先留通道、后迁移。可接受，但**留一条有已知缺口的遗留通道横跨整批 = 再入风险**，本批已两次栽在同型（门是真的、锁是缺的）。
- **绑定出口（Slice 4，不可再 defer，PARTIAL 不是可接受终态）**：① 把 `test_judge_identity_metric.py` 的三条历史反例迁到 occurrence API（**历史语义逐条不删**）；② **整条 legacy float dispatch 与 `_LegacyAxisIdentity` 删除**；③ 补一条 **AST 锁**证明全仓 `_cluster_axis` 调用**无一** 走 float 分支、且**全部显式传 topology**。理由 = 删掉的通道不需要锁，这比"给通道配一把够好的锁"更结构性。

**（b）守恒代码在 Slice 1 未被改动 —— 判定核实通过。** 施工方给出 B-L4 仍红的实测两数（`covered=20.861502717932577` vs `obs_length=20.861502717932574`，差 3 ulp 量级），证明红因仍是**原始 1-ulp 路径**、不是被挪动出来的。B 归 Slice 3，本轮不动，正确。

### 9.2 新增两条欠规格边界 —— 主控裁定

**1. C-L5（无证 sub-merge 须在提交 representative 前拒绝）与 C-L6（相邻坍缩由 post-merge validator 承重）的先后张力。**
- **裁定：「候选归并会坍缩一条已声明的边」是 C-3 之前的独立结构 witness，不是「先发一种新证书再由 C-4 拒绝」。**
- **理由**：① 该判据**纯由输入结构可判**（已声明边存在于来源拓扑中、候选归并会把它两端认成同一原子），**完全不依赖 alias 认证**，所以它本就该在 alias 门之前独立成立；② 若让它只在"恰好走到 C-4"时才发火，那么最终得到 `merge_collapse` 还是 `unproven_alias` **取决于哪道门先跑 = 执行顺序决定判定**——这正是本设计稿 §0 那条共同原则明令禁止的第一项；③ 坍缩是真实结构缺陷、不是能力上限，按 R-4 它有资格说 broken 而非 unsupported。
- **同时保留施工方自加的那条 C-L6 独立锁**（强制 representative collision 证明 post-merge checker 自身承重）——这正是防止 C-4 退化成死门的正确做法。

**2. C-4 claim → A 的过渡 seam（Slice 1 对无 capability 依赖的冲突直接生成 flat certified context，capability-contingent 仍走旧行为）。**
- **裁定：Slice 2 必须把这条过渡路径「收拢」而不是「并存」。** 收口后**全仓有且仅有一处决定请求级严重性**（`certify_and_arbitrate_request`）；Slice 1 的临时直发路径必须改为经该仲裁器，**不得作为第二条路线保留**。
- **理由**：施工方自己点出的风险词「第二条本地 severity 路径」**就是 R2-B1 / R3-B1 的原型**——本批第一次和第三次 REWORK 都是"存在一条绕过统一裁决的本地定案路径"。这条必须在 Slice 2 结构性消灭，不是靠纪律避免。
- **配套锁（Slice 2 必交）**：一条 AST/静态锁，证明计分路径上所有 identity 类 `ScoreContractError` 的 raise **全部源自仲裁器**，不存在旁路定案点。

### 9.3 neuter 实况登记（施工方诚实披露，主控采信）

- Slice 1 各锁 neuter **实跑得 19 个红实例**（非声称）。
- **施工方主动披露**：只删 C-L7 的重复顶点检查**不足以令锁变红**，因为 exact edge-intersection 仍独立承重，须完整退化为「只查相邻坍缩」才真红。
- **主控判定**：这是**两道独立 guard 覆盖同一锁**（冗余），**不是 false-lock**，且已按 §1#6「共用 guard 归并披露」正确处理。**但附一条要求**：该锁断言的 predicate 必须确为 `ring_identity_conflict`，否则锁名声称的门与实际承重的门不是同一道。

---

## 10. 主控裁定 · Slice 2 轻门（2026-07-28）

**轻门结论 = PASS（附一条必修跟进），可进 Slice 3。** 主控独立全量复跑 = **`1 failed, 1758 passed, 10 xfailed`（4:26）**，与施工方自报一致；**唯一失败为 B-L4**（Slice 3 范围）。Slice 0 六锁中 **A-L3 / A-L9 本轮合法转绿**，C 三锁保持绿。提交 `0b62a49`（源码，新 `certifier.py` 609 行 + 新测试 382 行）+ `99c8c6f`（执行日志）。

**主控 §9 两条裁定均已执行**：① C-4→A 过渡 seam **已收拢**——GT/product 共用一个 `AnalysisCollector`、两侧报告完成后**只调用一次** `certify_and_arbitrate_request`，并交付了 §9.2 要求的**静态门**（`identity_provenance.py` / `segment_score.py` / `score_service.py` 三文件内 `scoring.input_identity` 无直接 raise，唯一豁免是主控已明确延至 Slice 4 删除的 `_cluster_legacy_axis`）；② 已注册 evaluator 返回闭集外值**抛 `ValueError`**（§8.1 裁定 1）。C-L7 的 predicate 亦已精确为 `ring_identity_conflict`（§9.3 附加要求）。

**施工方处理既有锁的方式正确、记一次正面数据点**：主体收敛后首次全仓撞到三条既有 B5 admission 锁失败（证书 context 扩写破坏其历史 `{"reason": ...}` 合同）。**它没有走「恢复本地 severity」这条捷径**——严重性仍过同一仲裁器，只对纯 schema/密码学 admission fact 保留 reason-only 的 **context 形状**。这守住了 R3-B1 的修法（reason 只作展示、永不参与严重性判定），也守住了设计稿 §8.1「必须保留原意的锁」。

### 10.1 主控轻门独立发现（施工方未报）—— **必修，Slice 3 或 4 交付**

上述豁免由 `JudgeDiagnostic.exact_error_context` 布尔位承载：`certifier.py:347` 命中即 `return {"reason": diagnostic.reason}`，**跳过 §8.1 裁定 4 要求的证书字段完整性断言**。

主控独立核实其现状**是安全的**：该位的**唯一生产设置点**是 `score_service.py:_raise_score_input_contract`（`_exact_error_context=True`），且**由显式调用点设置、不由 reason 字符串推导** ⇒ **不是 reason 白名单换皮**，严重性仍走仲裁器。

**但 `grep -rn "exact_error_context" tests/` 零命中 ⇒ 这个豁免位没有任何锁。** 这是**「门是真的、锁是缺的」**——本批与 07-19/07-26 反复栽的同一族：一个**通用机制**配一处**窄用途**，而通用机制会扩散。将来任意新调用点设一下这个位，就能合法逃逸证书 context 完整性要求，且**全仓不会有任何测试变红**。

**出口（三条，缺一即返工）**：
1. 一条锁证明 `_exact_error_context=True` **只可能来自** `_raise_score_input_contract`（AST/静态枚举，与 §9.2 静态门同法）。
2. 一条锁证明 `_raise_score_input_contract` **只用于** admission predicate `typed_score_input_contract`。
3. 一条锁证明**走该豁免路径的诊断，其严重性仍由仲裁器决定**（而非由该位或 reason 决定）——即对该路径做指定 neuter：摘掉仲裁器调用后必须变红。

**理由**：豁免本身正当（保护既有合同），**但正当的豁免必须是封闭列举、且被锁钉住**，否则它就是下一个「第二条路径」。本批三次 REWORK 全部是这个结构，不能在收尾处再留一个。

---

## 11. 主控裁定 · Slice 3 轻门（2026-07-28）

**轻门结论 = PASS，可进 Slice 4（收尾段）。** 主控独立全量复跑 = **`1777 passed, 10 xfailed, 0 failed`（4:18）** ⇒ **Slice 0 六条红锁全部合法转绿**，其中 B-L4（三段合法铺满被 1-ulp 判假红 = R3-B2）本轮消除。提交 `2193748`（新 `interval_ledger.py` 775 行 + 新测试 490 行 + `segment_score.py` +254−83）+ `11f061b`（日志）。sm24 受保护树 14 项 SHA-256 与 Slice 0/1/2 manifest **逐项 byte-identical**，`git diff --quiet` exit 0。

**§10.1 三把豁免锁已交付并行为级承重**；旧 scalar 回流静态门、共享 canonical cut、实际 ledger seam 均已落地。

### 11.1 施工方自查出两处「指定 neuter 其实不会变红」—— 主控记为本批最强的一次自我纠错

1. **B-L5 的排列锁遮蔽**：生产入口在建 claim 前已有 `_canonical_geometry` 排序 ⇒ **即便把账本内部改回普通顺序浮点求和，只置换 API 输入仍会绿**。施工方没有把这个判断留给猜测，改为在同一批真实 claims 上直接置换六种顺序，使 ordinary float accumulator 的 neuter **真红**。
2. **B-L7 的整数夹具不敏感**：`[0,2]+[2,4]` 在 binary64 中恰好精确 ⇒ 恢复旧 `extra = length − covered` 减法**也会绿**。改用两个结构严格相邻、但独立浮点长度和差 1 ulp 的真实坐标后，正常账本得 `extra_exact=0`、旧减法得 `−1/281474976710656`，neuter 真红。

**主控判定**：这正是本批三轮 REWORK 反复缺的能力——**分辨「锁绿」与「锁真绑」**。施工方在无人指出的情况下自行发现并修到夹具层，**记一次正面数据点**，也是本批首次由施工方自己抓出假锁。

### 11.2 新增两条欠规格边界 —— 主控裁定

**1. exact 字段是否进公开 row wire（Slice 4 决策点）。** 现状：`eligible_units_exact: Fraction` 存在内部 `SegmentScore`，canonical row key 同时含 exact fraction 与 public float hex，**未擅改公开 `SegmentScoreRowV8` wire**。
- **裁定：不 bump 公开 row schema；exact 字段走 audit sidecar，§8.3 的 canonical JSONL 以 audit 列携带。**
- **理由**：① exact 值的性质是**审计证据**，不是计分输出——判定由它支撑，但消费方（renderer / sidecar consumer）不需要它；② helper identity bump 已经把派生件失效的爆炸半径打开到「旧 typed c2 v3 sidecar/cache 全 miss」，**这是必要且预期的**；再动公开 row 会把半径扩到无验证需求的下游，与设计稿 §8.3「预计不应变化：renderer」相抵；③ 施工方**没有擅自改公开 wire 而是停下来问**，处置正确。

**2. 局部重复 + 全局仍有空白时，历史 reason `observation_cover_exceeds_length` 是否改名。** 新规则在任一正长度 atom 上 `target_ids>1` 即拒绝，此时「收费总和」未必大于整条 domain ⇒ 旧名字面义与新判据不完全重合。
- **裁定：保留 code 字符串不改**（设计稿 §8.1「单一形态的既有 code/gate/reason 不变」，且 A2 类逐字码锁依赖它）。
- **但附硬要求**：`excess` 在新语义下 = **该 duplicate atom 上的正 multiplicity charge**，与旧的全局含义不同 ⇒ **同名字段悄悄改义会让事后无法复算判定**，这正是本批共同原则禁止的。故 context 必须**足以独立复算该判定**：至少携带**触发的具体 atom 区间** + `charged_exact` / `duplicate_charge_exact`，并**配一条锁证明「仅凭 context 即可复算出该判定」**。施工方已存后两个字段，本条只补 atom 区间与复算锁。
- **明确否决一条路**：不得再让某个负的 `charged − domain` 冒充 excess（施工方已自行封死，此处固化为合同）。

---

## 12. 主控裁定 · Slice 4 轻门 = 施工侧全批收口（2026-07-28）

**轻门结论 = PASS，施工侧交付完成，转 GLM-5.2 对抗审。** 主控独立全量复跑 = **`1782 passed, 10 xfailed, 0 failed`（4:33）**，与施工方自报一致。最终提交 `67b9c00`。

**主控独立核实的四项硬指标**：
1. **遗留浮点通道已真删** —— 全仓 `_LegacyAxisIdentity` / `_cluster_legacy_axis` **零命中**，仅余一条断言其不存在的锁 ⇒ §9.1(a) 三条出口全落，且「删掉的通道不需要锁」成立。
2. **helper 身份** = `"b4b_segment_score_v3_ic1"`，`Literal` 同步、**无 v2 union 残留**。
3. **整批 gt 与管理文档零触碰** —— `git diff cce6e83..HEAD -- case_tests/test_baseline/gt/ AI_agent/CLAUDE.md` 为空。
4. **工作树干净**，仅余主控自有的未跟踪派工单。

**D-1 结果（主控独立读证书，不采信自述）**：`comparison.json` 显示 **`public_rows.jsonl` 与 `wall_criteria.jsonl` 的 baseline / new SHA-256 逐字节相同**，`public_rows_identical=True`、`wall_criteria_identical=True`、`blocking_change=False`。⇒ **真实 sm24 上对外可见的判分输出零变化**；差异仅限内部审计列与 8 个 internal extra 浮点，每个附 exact fraction + domain + cut-id 舍入证书，并由活锁 `test_sm24_front_door_audit_certificate_has_no_blocking_change` 钉住。这是本批「改造未悄悄改变判分」的最强证据。

### 12.1 D-1 的执行边界 —— 施工方主动披露，主控裁定「接受 + 转跟进债」

**实况**：仓库里唯一真实已接受的 sm24 correction artifact（`run_2026-06-24_opus_reading/1_correction/correction_geometry.json`，hash 已公开）**早于当前 B5 六件套 proof wire**，而现行 correction 正门要求不可伪造的 `VerifiedWindowHostProof` ⇒ **该历史产物无法进入 correction 分支，除非伪造 proof（信任根明令禁止）**。施工方的处置：把该真实已接受产物**确定性原子化**为 34 条 raw segment 的 wire，**同一份 bytes** 同时喂给 baseline 与 new 的**真实 `score_typed_attempt(stage="reading")` 正门**；**未手造 `PlanSegment`、未绕过 scorer**；源 hash / 准备算法 / 输入 bytes 全部公开，并**明确拒绝把它描述成原生 B5 correction replay**。

**主控裁定 = 接受。** D-1 的立法目的是「证明改造没有悄悄改变真实 case 的判分」，其三条实质要件——两侧输入逐字节相同、两侧都走真实 scorer 正门、无手造中间件绕过被测代码——**全部满足**。这不是走捷径，是**仓库现状造成的客观边界**（历史产物早于 wire），且施工方选择了「披露 + 请主控裁定」而非「悄悄替代并声称等价」。

**但覆盖缺口是真的**：本次 D-1 走的是 **reading 正门**，**correction 分支（B5 proof 处理）未被 D-1 覆盖**。
⇒ **转跟进债，且已有天然落点**：**下一站的 sm24 端到端跑测**必须产出一份**原生 correction 正门**的 D-1 对照。此举把缺口从「悬空的洞」变成「已排期的验证」。**与 B5 Phase D 的 MINOR-3（writer replay 前提待首个真实 v3 run 验证）同族、按同一口径处理。**

### 12.2 另一条正面数据点

新增的审计 CLI 一度让「受影响子集」静态门全仓变红。施工方**没有把它加进 allowlist**（那是遮盖），而是新增真实 certificate lock 直接 import 该工具并验证 D-1 的全部阻断条件 ⇒ **修到根因而非绕过门**，与 07-26 提速批确立的纪律一致。

### 12.3 施工侧全批小结

| 项 | 结果 |
|---|---|
| Slice 0–4 | 全部交付，逐段过主控轻门 |
| Slice 0 六条红锁 | **全部合法转绿**（含 R3-B1 假绿路径与 R3-B2 1-ulp 假红） |
| A-L1…A-L9 / B-L1…B-L10 / C-L1…C-L16 | 全绿 |
| 全仓 | `1725 → 1782 绿`（+57），10 xfail，**零回归** |
| DoD 16 条 | 施工方自评 16 项 PASS（**由 GLM 独立验，非主控采信**） |
| 施工方上报欠规格边界 | **10 处**，主控逐条裁定并写入本单，无一由施工方自行降级为假设 |
| 施工方自查出的假锁 | **2 处**（B-L5 排序遮蔽 / B-L7 整数夹具不敏感），无人指出下自行发现并修到夹具层 |
| 主控轻门独立发现 | **1 条必修**（§10.1 无锁的豁免位），已在 Slice 4 补三把锁 |

**⇒ 转 GLM-5.2 跨家族验证性对抗审**（谁写谁不批：sol = GPT 侧、GLM = GLM 侧）。审的基准 = 设计稿 §10 的 16 条 DoD + 各节机械验收锁与指定 neuter + 本单 §8–§12 的全部主控裁定。
