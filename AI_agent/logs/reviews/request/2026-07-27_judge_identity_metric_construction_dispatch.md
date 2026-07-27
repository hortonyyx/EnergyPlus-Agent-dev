# 派工单 · 判卷器「数值身份 + 计分度量」施工批（2026-07-27）

> **施工 = GLM-5.2** / **对抗审 = sol（GPT 侧，max）** / **轻门 = 主控 Opus 5**。用户 2026-07-27 拍板，一次全上不拆批。
> **施工基线 = [judge_identity_and_metric_plan.md](../../../proposals/judge_identity_and_metric_plan.md)**（已过 GLM 跨家族对抗审 APPROVE-WITH-CHANGES）。
> 基线是**唯一权威**，本单只做「落到文件:行 + 出口可验」的展开。**两者冲突以基线为准，并立即回报主控。**
> 来源推导（需要时查，不必通读）：[Claude 侧](../../../proposals/judge_identity_and_metric_plan_opus.md) · [GPT 侧](../../../proposals/judge_identity_and_metric_plan_sol.md)。

---

## 0. 一句话任务

判卷器现在用「把坐标四舍五入到 1e-12 的格子」来判断两个数是不是同一个坐标——**任何这样的定格都有边界，边界两侧任意接近的两点被判成不同坐标**，已连续两轮制造假红。本批把它换成**对本次实际出现的坐标做聚类 + 直径守卫 + 分不清就响亮拒绝**；同时把墙的分母从「界面条数」换成**长度（米）**，用**联合切点原子化**取代一对一指派。

---

## 1. 纪律（先读，违反即返工）

1. **`case_tests/test_baseline/gt/` 下任何字节不得改动**。基线 C-4：sm24 已签字答案不重签、不迁移、不「规范化」。施工前后各跑一次逐字节 hash 对照（见 §5-A5），有差异 = 施工直接失败。
2. **开工/收工两次 `git status --short` 必须逐字相等**（基线 §4 纪律锁）。除本单列明的文件外不得新增/删除任何文件，尤其不得在仓库根落文档或目录（CLAUDE.md §5 硬规矩）。
3. **不得改本管理文档 `AI_agent/CLAUDE.md`**（07-26 教训：施工方越界改管理文档被判 MAJOR）。`AI_agent/` 下只允许写本单指定的执行日志。
4. **gt 铁律（不变量 #4）**：新抽出的共享模块（§4-W5）**零 gt import**，gate①/生产路径绝不 import 判卷器。
5. **不许先定数字再补论证**（基线 R-2）。三个阈值必须先给实测分布，再给数字。
6. **每条锁自带指定 neuter，共用同一守卫的锁必须归并披露**（基线 §5-11，r2 直接教训）：不许把共用一个 `raise` 的多条测试记成多条独立承重锁。自查表里逐条写「摘掉哪一行 → 哪几条测试变红」。
7. **诚实优先于完成**：做不完就精确标 PARTIAL 并说明卡在哪（对标 B4b Phase D 正面样板），**不许伪造 neuter 自查表**。
8. 跑测三档节奏见 [codex_execution_protocol §7.5](../../../guides/codex_execution_protocol.md)：中间轮用 `python scripts/tool_scripts/affected_tests.py` 算受影响子集（**禁自由裁量**），**交付前跑一次全仓**（`pytest`，默认并行，约 4–8 分钟）。基线 = **1685 绿 + 10 xfail**。

---

## 2. 开工门（动手前必须先做，两处已由主控预先核实撞上）

基线 §5-10 要求开工第一步核评分身份摘要是否被钉死。**主控已核，撞上两处，处置如下——照做，不要自己另想：**

**G-a · `segment_scorer` 字面量升版（必做）**
- 现状：[score_schema.py:37](../../../../src/agent/judge/score_schema.py#L37) `SEGMENT_SCORER_HELPER_VERSION = "b4b_segment_score_v1"`；[score_schema.py:298](../../../../src/agent/judge/score_schema.py#L298) `segment_scorer: Literal["b4b_segment_score_v1"]`；引用三处：[score_service.py:144](../../../../src/agent/judge/score_service.py#L144)、[tests/test_c2_b4b_contract.py:36](../../../../tests/test_c2_b4b_contract.py#L36)、[tests/test_c2_b4b_phase_d.py:35](../../../../tests/test_c2_b4b_phase_d.py#L35)。
- **处置**：升 `b4b_segment_score_v2`，四处同步（含 `Literal`）。**旧值不保留为兼容分支**——判卷逻辑变了就该换身份。
- **这会让既有评分缓存 sidecar 失效，这是要的效果**（基线 C-4「需要失效的只是派生件」），不是回归。若某测试因缓存失效而红，是该测试把派生件当权威，报告主控，不要加兼容层绕过。

**G-b · 判卷配置 hash 常量 + skill 文档内嵌 hash（本批极可能撞）**
- [tests/test_c2_b4b_contract.py:65](../../../../tests/test_c2_b4b_contract.py#L65) 钉死 `judge_score_config_sha256(config) == "ac2c1470…"`，**且 [:66](../../../../tests/test_c2_b4b_contract.py#L66) 断言同一串 hash 出现在 `skills/intake_pipeline/1_correction/A0_contract.md` 里**。
- 只要往 [src/configs/judge_score.yaml](../../../../src/configs/judge_score.yaml) 加字段（本批的三个阈值若落配置就会），这个 hash 必变。
- **处置**：新 hash 由代码现算，**同步更新测试常量 + A0_contract.md 内嵌值**。改 A0_contract.md 时遵 CLAUDE.md §5#5：**skill 库是英文纯当前版本 spec**，只改数值与必要描述，**不写时间戳/版本日志/缘起 case**。
- **⚠️ 别混淆**：`judge_score.yaml` 里既有的 `opening_assignment_tie_epsilon: 1.0e-9` 是**匹配打分的并列判据**，与本批「1e-9 拓扑缺口必须判红」是**两个不同层的 1e-9**。不要合并、不要互相引用。

**G-c · 基线三个活体反例先复现**（回归锁的靶子，开工时先让它们红/绿状态被记录下来）
1. 真实 sm24：`8.059999999999999` ↔ `8.06`
2. typed correction：`0.1 + 0.2` ↔ `0.3`
3. r2 的 1-ulp 量子格边界对（见 [2026-07-27_plan_segment_tjunction_rework_r1.md](2026-07-27_plan_segment_tjunction_rework_r1.md)）

---

## 3. 现状地形（主控已勘，省你重查）

| 位置 | 现状 | 本批命运 |
|---|---|---|
| [segment_score.py:37-46](../../../../src/agent/judge/segment_score.py#L37) `_COORDINATE_QUANTUM=1e-12` + `_canonical_coord/_canonical_point` | 全定义定格量化 | **删除**，换 §4-W1 聚类 |
| [segment_score.py:116-186](../../../../src/agent/judge/segment_score.py#L116) `_tile_orthogonal_edges` | T 切分已落地（16 段内墙），内部全用 `==`/`<=` 精确比较 | 保留算法，比较改跑在**原子 id** 上（§4-W2） |
| [segment_score.py:189-227](../../../../src/agent/judge/segment_score.py#L189) `_pair_general_edges` | 非正交边只与精确反向配对 | 正交判据外提（§4-W5） |
| [segment_score.py:359-402](../../../../src/agent/judge/segment_score.py#L359) `assign_plan_segments` | 穷举一对一 + 并列即 `score_match_ambiguous` | **换联合切点原子化**（§4-W3），该错误码在此通路结构性不可达 |
| [score_policy.py:53-83](../../../../src/agent/judge/score_policy.py#L53) `_criterion_from_rows` | `getattr(row, "eligible_units", 1.0)` ⇒ `SegmentScore` 无该属性 ⇒ **每段 1 单位 = 界面条数分母**；且 [:65](../../../../src/agent/judge/score_policy.py#L65) `extra` 行同时进 denominator 与 failing ⇒ **产品多画墙会把分母变大** | 分母换长度（§4-W4）；extra 移出 `walls_complete` 分母（R-3） |
| [score_policy.py:114-128](../../../../src/agent/judge/score_policy.py#L114) criteria 元组 | 只有 `walls_complete` 一项管墙 | 加 `no_extra_walls` / `no_duplicate_wall_strokes`（§4-W4） |
| [score_service.py:192-193](../../../../src/agent/judge/score_service.py#L192) `product_to_gt` | 一对一 dict，喂 [:229](../../../../src/agent/judge/score_service.py#L229) 开窗匹配 + [:250](../../../../src/agent/judge/score_service.py#L250) 窗宿主解析 | **点名风险，见 §5-B** |
| [correction/cell_geometry.py:15](../../../../src/agent/correction/cell_geometry.py#L15) `_EPS = 1e-9`、[deterministic.py:63](../../../../src/agent/correction/deterministic.py#L63) | 上游正交容差 | 本批**只加 advisory，不翻 blocking**（R-4） |

---

## 4. 施工范围（W1–W6）

### W1 · 身份层：聚类取代定格（基线 C-1 / C-1′ / C-1″ / R-1 / R-2 / R-5）

- **机制**：对一次 score request 内**实际出现**的坐标，**按轴分别**建图（x 一池、y 一池），距离 < 合并阈才连边，取连通分量为身份原子。原子代表值取该分量的确定性代表（如最小值或均值，**必须钉死并写进合同**，不许依赖输入顺序）。
- **护带（R-1，取 Claude 侧结构，不是单点边界）**：
  - 距离 < `merge_threshold` → 合并
  - 距离 > `split_threshold` → 分裂
  - 落在两者之间（护带内）→ **响亮拒绝**，分码。
  - **禁**用单一上界 + 「恰等于才拒」——那是零测度事件，等于静默分裂。
- **直径守卫**：单链接会链式桥接。连通分量的**直径**超过 `diameter_threshold` → 拒绝，分码（链式桥接超直径）。
- **作用域（C-1′，硬）**：身份池 = `(文档侧, floor_id, 轴)`，**GT 池与产品池完全分离，绝不联合建池**。跨文档比较只发生在判卷容差层（既有 `plan_*_tol_m`），产品切点向答案切点**单向**配准（产品→答案，永不反向）。
- **输入合法性合同（C-1″，必须运行时执行，只聚类不执行 = 验收不通过）**：① 同一意图坐标全部出现值直径 < 合并阈；② 不同意图坐标最小距离 > 分裂阈；③ 无距离落在护带内；④ 归并不得造成零长边 / 相邻重复顶点 / 环自交 / owner 重数冲突。**违反任一条 = 整轮响亮拒绝。**
- **错误分类学（R-5）**：身份层失败一律 fail-closed 且分码，至少覆盖：非有限值 / 护带内歧义 / 链式桥接超直径 / 归并致边坍缩 / 合同版本不匹配。**错误上下文必须记录十六进制 binary64（如 `float.hex()`）与精确直径**，不得只打印舍成十进制的值——否则事后无法复现判定。新错误码需在 [score_schema.py:46](../../../../src/agent/judge/score_schema.py#L46) 的码表与 [:51](../../../../src/agent/judge/score_schema.py#L51) 的门表登记。

**⚠️ W1 的阈值（R-2）——本批最容易被卡的一项，照下面顺序做：**
1. **先实测**：在真实 sm24 已签字答案 + typed correction 产物上，统计同一意图坐标的实际表示漂移分布（最大值、分位数）。20 m 量级 binary64 的 1 ulp ≈ 3.55e-15，若干次算术后经验上约 1e-14 —— **这是待验证的预期，不是可以直接拿来用的结论**。
2. **再定数字**：合并阈下界须**显著高于**实测漂移上限；分裂阈上界须**显著低于**必须判红的最小真实缺口 1e-9。
3. **交付时必须给出**：① 实测漂移分布（含最大值）；② 两侧余量各多少倍；③ **两条锁分别证明**「合法漂移必合并」与「1e-9 缺口必红」。
- 参考：Claude 侧提的一组（合并 1e-11 / 分裂 1e-10 / 直径 5e-11）**对 1e-9 只剩 10× 余量，主控判偏薄**；GPT 侧 1e-12 余量 1000× 但无护带。**两组都不许直接抄**，按实测重新推。

### W2 · T 切分改跑在原子 id 上

`_tile_orthogonal_edges` / `_pair_general_edges` / `_lies_on_exterior` 内部的 `==` / `<=` 比较，改为在 W1 产出的**原子 id**（整数或不可变代表值）上做。语义不变：精确比较仍然精确，只是「什么算同一个坐标」由 W1 权威回答。**不得在这一层引入任何新的容差。**

### W3 · 匹配层：联合切点原子化（基线 C-3）

取代 `assign_plan_segments` 的一对一穷举：把答案与产品的段投影到同一支撑线上，取**双方切点的并集**做原子区间，逐区间做集合运算（覆盖/未覆盖/多余）。⇒ 覆盖是集合运算、无并列最优 ⇒ **`score_match_ambiguous` 在该通路结构性不可达**。
- **出口**：写一条锁证明该错误码在平面墙通路不可达（不是删掉错误码——它在开窗通路仍在用）。
- 跨文档配准判据 = 既有判卷容差（`plan_position_tol_m` 等），**单向性（产品→答案）必须在代码注释与合同里显式声明**。

### W4 · 度量层：分母换长度 + criterion 三分（基线 C-2 / R-3）

- **分母 = 长度（米）**，不是段数。`SegmentScore` 需带长度型 `eligible_units`（或在 `score_policy` 侧提供适配器），使 `_criterion_from_rows` 拿到米。
- **criterion 三分（R-3）**：
  - `walls_complete`：漏画。**分母只来自答案**。
  - `no_extra_walls`：多画。额外长度须为 0。**产品多画不得把分母变大**（现状 [score_policy.py:65](../../../../src/agent/judge/score_policy.py#L65) 违反此条）。
  - `no_duplicate_wall_strokes`：重笔。**若产品语义允许重笔则显式 NA**，不许悄悄忽略。
- 同一个缺口**不得在多个 criterion 里重复扣分**。
- 守恒断言 [score_policy.py:75](../../../../src/agent/judge/score_policy.py#L75) 继续成立（改成长度后仍须 `passing + failing == denominator`）。
- **必须证明**：同一道墙整条画漏时，`failing` 恒等于墙长、**与对面房间数无关**（真实 sm24 实测每米权重最大/最小差 3.96×，就是这条要消灭的失真）。

### W5 · 上下游口径：正交判据抽共享模块（基线 R-4）

- 正交性判据抽进**生产与判卷共用**的模块，**零 gt import**（不变量 #4）。
- **拆开两个问题**：「几何**合不合法**」权威在生产端；「判卷器**能不能量**」权威在判卷端，且判卷端**只许说 unsupported（能力 NA），不许说 broken**。
  > 这是三轮假红的结构性根源——判卷器拿自己的能力上限去宣判上游几何非法。任何新写的拒绝路径都要过一遍这条：我是在说「这不合法」还是「我量不了」？后者一律 NA。
- 上游 `_EPS=1e-9` 收紧**分两阶段**：**本批只加 advisory**，两次真实 run 零命中后再翻 blocking。**本批不得翻 blocking。**

### W6 · R-6 派生件失效与登记

- 需要失效的派生件：旧 `score_vs_gt` sidecar、旧 grade 图、旧 identity 合同下的阶段缓存、`run_2026-07-27_haiku_e2e/` 挂起 run 在校正接受点**之后**的评分派生件。**校正接受点之前的产物不动。**
- `case_tests/test_baseline/gt/sm24_anchor/score_inputs/view_bindings.json` **未入版本控制** —— **本批施工方不碰它**（在受保护 gt 目录内）。主控收工时 `git add`；清单口径归下一批「gt 标准产物清单」。

---

## 5. 验收清单（sol 照此审；每条须有指定 neuter）

### A · 基线 §5 总纲逐条

| # | 出口 | 判红方式 |
|---|---|---|
| A1 | 三个活体反例（sm24 `8.059999999999999`↔`8.06` / `0.1+0.2`↔`0.3` / r2 量子边界对）**全部转绿** | 各一条锁；摘掉聚类即红 |
| A2 | **1e-9 缺口双侧仍红**（答案侧 + 产品侧各一条锁），**错误码逐字不变** | 断言 `ScoreContractError.code` 精确串 |
| A3 | 护带内歧义 = **响亮拒绝**且分码正确 | 构造落在护带内的距离；断言既非合并也非分裂 |
| A4 | Q3 三情形得分：整墙画漏 `0/4`；画对但分段不同 `4/4 = 100%`（现状是抛歧义不出分）；画对一半 `2/4` | 三条独立断言 |
| A5 | **sm24 受保护清单逐字节不变** | 施工前后 hash 对照，差异即失败 |
| A6 | **sm21 legacy 通路零变化**：既有分数字节 + 渲染像素 hash + 分派路径 | 已有 legacy 锁全绿 + 显式对照 |
| A7 | 窗宿主解析**多段覆盖锁**（见 §5-B） | 见下 |
| A8 | **答案原子/分母 = 答案字节的纯函数**（C-1′）：同一份答案配**不同产品**，原子集合与 `denominator_m` **逐字节相同** | 两个不同产品跑同一答案，断言逐字节相等 |
| A9 | **输入合法性合同四条在运行时被执行**（C-1″），违反即响亮拒绝并分码 | 四条各一个违反夹具；**只实现聚类不执行合同 = 不通过** |
| A10 | 开工门 G-a/G-b 处置到位 | 见 §2 |
| A11 | 每条锁自带指定 neuter，**共用守卫的锁归并披露** | 自查表 |

### B · 点名风险（基线 §3，硬性单列，**不许混在常规回归里**）

**⚠️ `score_service.py:192-193` 的 `product_to_gt` 同时喂两个语义不等价的下游**：
- [:229](../../../../src/agent/judge/score_service.py#L229) `assign_openings(..., product_to_gt_segment=...)` —— 开窗匹配
- [:250](../../../../src/agent/judge/score_service.py#L250) `build_correction_host_resolver(product_to_gt_segment=...)` —— **窗宿主解析**

摘掉一对一指派后，一个产品段可能覆盖多个答案段，现有 `dict[str, str]` 结构不足以表达。**若图省事「取第一个」，多段覆盖时窗会静默绑错墙，且没有任何测试变红**（GLM 上轮已逐条核实：既有窗夹具**全是单段**）= 典型「门是真的、锁是缺的」。

**出口（三条全做，缺一即返工）**：
1. 写成**逐键相等的显式契约锁**（不是「长度相等」这类弱断言）。
2. 新增**多段覆盖**的窗夹具（既有夹具全单段，必须新造）。
3. 在交付简报里**单列一条**说明该处怎么改的、为什么语义正确。

### C · 全局

- 全仓 **1685 绿 + 10 xfail** 基线：**零回归**。新增测试计入增量。
- 零 golden 改动；如必须改，**停下报告主控**，不得自行决定。
- 不得触碰：`case_tests/test_baseline/gt/**`、下游 subagent、`AI_agent/CLAUDE.md`。

---

## 6. 交付格式

1. **执行日志**落 `AI_agent/logs/reviews/execution/2026-07-27_judge_identity_metric_glm.md`，含：
   - 每次 commit 的 SHA + 一句话
   - **W1 阈值实测数据**（漂移分布 + 两侧余量倍数）—— 这是 R-2 的核心交付，**不许只给结论数字**
   - **neuter 自查表**：逐条「摘掉哪一行 → 哪几条测试变红」，共用守卫必须归并披露
   - 全仓测试输出尾部（绿/xfail/失败计数）
   - 开工 / 收工两次 `git status --short`
2. **诚实披露**：未完成项精确标 PARTIAL + 卡点，不伪造自查表。
3. 完成后回报主控，主控派 sol 对抗审，再走主控轻门（独立全量 + 亲核 diff）。

---

## 7. 主控备注

- GLM 席位经 [`scripts/glm_code.sh`](../../../../scripts/glm_code.sh) 启动；**凭据只注入子进程，禁全局导出 `ANTHROPIC_*`**（会静默劫持主控会话）。
- 现为非高峰时段（UTC+8 21:00 起），额度扣率较低，适合长批次；高峰 14:00–18:00 (UTC+8) 3× 扣，避开。
- 验锁做 neuter 时**只在 `/tmp` 副本做**，不得把 neuter 状态留在工作树里（07-26 纪律）。
