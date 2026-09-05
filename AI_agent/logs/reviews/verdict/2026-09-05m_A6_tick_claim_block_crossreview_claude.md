# A-6 整条线（设计收口＋刻度认领＋四分类裁决）跨家族复核裁决 · Claude 家族

**REWORK · 阻断 2 · 不阻断 3**

- 复核方：Claude 家族，独立于施工方（GPT 家族 `gpt-6-astra`）。
- 工作目录：`/tmp/a6_review_claude`，detached HEAD `94e899e5`。全程未 `pip install -e .`、未 `git add -A`。
- 审阅范围：`2a51d7fd..94e899e5`；被审对象固定为 HEAD 交件三份 + `src/agent/correction/{tick_claim,opening_adjudication}.py` + 两份测试文件。
- 复核单：[`request/2026-09-05m_A6_tick_claim_block_crossreview.md`](../request/2026-09-05m_A6_tick_claim_block_crossreview.md)。
- 独立证据目录：[`experiments/2026-09-05m_A6_tick_claim_crossreview_claude/`](../../experiments/2026-09-05m_A6_tick_claim_crossreview_claude/README.md)（下文 `probe_outputs.txt`、`mutation_log.txt`、`full_suite_claude.txt` 均在该目录）。

## 头条结论

**REWORK**。两条阻断都不要求改写 `tick_claim.py`/`opening_adjudication.py` 的核心逻辑——一条是**登记债**（把三句被删的强制口径变成 `plan.md` 里可查的验收项），一条是**加一处出口重检**（`consume()` 补一次跨行区间校验，属于本模块内部的防御加固，预期不会打红任何现有测试）。除此之外，本单交出的 877 行实现 + 690 行测试在我独立复核的每一个维度（R-1..R-4、§三同形输入、§六变异测试）都站得住，且施工方对自己此前四条阻断的重新表态诚实、未回避。

## 独立读数（§五，先行）

```
/tmp/a6_review_claude/src/agent/correction/tick_claim.py
/tmp/a6_review_claude/src/agent/correction/opening_adjudication.py
3877 passed, 2 skipped, 13 xfailed, 211 warnings in 513.86s (0:08:33)
```

- 两条 `m.__file__` 落在本工作目录 `/tmp/a6_review_claude`（跑前跑后各打印一次，均一致；未受另一并行 Claude 席位影响）。
- `python -m pytest -q -n 6 -p no:cacheprovider` 独立跑出 **3877 passed / 2 skipped / 13 xfailed / 0 failed**，与施工方交件读数**完全一致**。
- 独立 `--collect-only tests/test_tick_claim_a6.py tests/test_opening_adjudication_a6.py` = **27 tests collected**，逐位核对为 22（tick_claim）+ 5（opening_adjudication）；`git diff --name-status 2a51d7fd HEAD -- src tests case_tests` 只有这 4 个新增文件，无其它改动。**3850 + 27 = 3877，逐位闭合，差额 0。**
- 结论：施工方的全量与逐位闭合读数**未发现任何问题**，独立复算一致。

## §一 五处删句的三选一判定（逐句）

独立执行 `git diff c1dab3b8 94e899e5 -- .../2026-09-05j_A6_tick_claim_contract.md`，确认删除内容与交件表格逐字相符，未发现未披露的改动（详见 `probe_outputs.txt` 之外的本节直接 diff，已在下方引用）。

### C:11 / C:83 / C:130（同一件事：正式接线尚未存在，未来接线必须走新出口）

**判定：(b) 缺口是真的但只存在于交件的散文里，没有任何机械可查的登记 ⇒ 这是本单的阻断（阻断①）。**

独立验证链路：

```sh
grep -rn "tick_claim\|opening_adjudication\|TickSession\|OpeningReview" src/agent/pipeline.py
# 无匹配
grep -rln "from.*tick_claim import\|from.*opening_adjudication import" src/
# 只有 opening_adjudication.py 自己 import tick_claim.py，run_pipeline 零引用
```

确认 `run_pipeline → CorrectedGeometryV3` 完全没有接 `TickSession`/`OpeningReview`；且旧 B4 模块 `opening_synthesis.py` 本身也**零生产调用者**（与 CLAUDE.md 09-05 复核已知事实一致）。执行档 §七 对此如实承认，**不是新发现**。

真正要核的是：这个缺口有没有被**显式记账**。检索结果：

```sh
grep -rn "OpeningReview\|scoreable_openings\|TickSession" AI_agent/plan.md AI_agent/CLAUDE.md AI_agent/decision_log.md AI_agent/architecture/*.md
# 零命中
```

`plan.md:427` 的 **E-a**（端到端接线）唯一写死的两条验收项是「交 judge 必须以 strict 进入」「身份从 bundle 的 `source_artifacts[0]` 提取，不许手拼」——**都不包含** C:11/C:83/C:130 分别要求的三件事：
1. 装配消费新结果时必须通过 `OpeningReview.consume`/`scoreable_openings`，不把历史 JSON 当成当前有效批次；
2. 调用方持久化时必须把源 bytes 与 `TickBatch.record` 一起保存，不能只存预览坐标；
3. 正式接线必须消费本模块的来源与当前出口语义。

这三件事目前**只存在于**执行档 §七「最薄弱一处」的散文里，`plan.md`/`CLAUDE.md`/`decision_log.md`/`architecture/*` 均无一字提及。删句本身合规（那三句确实指不到强制行，属于未来接线的承诺，现在没有装配代码可指），**但删除之后缺口去哪了这件事，交件没有交代**——这正是复核单点名要防的「缺席」。

**修法（不改代码）**：在 `plan.md` 的 **E-a** 行追加这三条为显式验收项（或另起一个具名债条目，如 `A-6-debt-1`），使其成为下一次「E-a 施工单」派工前**机械可查**的前提，而不是只活在这份执行档的散文里。

### C:7（每张 reading 图各一实例）

**判定：(c) 缺口不成立。**

删除理由（「没有图级全局单实例注册器；强制的是给定 owner 与独立 expected ID 下的本次决定，不是禁止两个会话存在」）成立。核心论据：
- `OpeningReview.__init__`（O:190-191）已经对**单次装配内**跨图重复做了检查：`facade.session.packet.image_id in image_ids: raise IMAGE_MANIFEST_DUPLICATE`。
- 真正承重的「同一决定不能被替换」由 `consume(expected_batch_id, batch=None)` 的字节级比对保证（T:493-499，独立验证见下文 §二），与「进程里能否同时存在两个 `TickSession` 对象」无关。
- 建一个跨调用全局单实例注册表，会把本模块从「普通 API 封装」升级为「进程级单例强制」，超过本单 P0 范围（`reassessment.md` 已把同类的 B-4「真封印」判为不阻断，理由一致）。当前没有任何调用路径会为同一张图构造两个并行会话，这是**调用约定**问题，属于未来 E-a 接线时「谁是这张图的唯一持有者」的编排责任，不是本单类型层需要现在解决的缺口。

### C:66（代码调用方修候选或 reading 补证后回第一步）

**判定：(c) 缺口不成立。**

删除的是「自动修候选 / 自动驱动 reading」的**调度器承诺**，保留的是**显式 `reconsider()`** 及其状态约束。P0 治理口径（CLAUDE.md §0）明确「不需要每一步都考虑得特别完善周全」「不建设 Python 内省对抗机制」同一档位下，也不该现在造一个自动补证调度器——这类自动化目前在指南里没有任何设计依据。独立复核 `test_failed_evidence_replacement_cannot_resurrect_old_response` 并做变异测试（见§六变异C）证明**显式路径**本身健壮：补证源不匹配立即拒绝、旧响应在补证失败后仍不可复活、正确补证后才能重新提交。删掉「自动回第一步」的承诺不影响这条链路的完整性。

## §二 把 B2 五类攻击打到冻结机制上

承重机制：`TickBatch(batch_id, record: bytes)` + `TickSession.submit/consume`。全部代码见 `attack_probe_1.py` / `attack_probe_2_chain_reorder.py`，原始输出见 `probe_outputs.txt`。

### 攻击 1（B2 原型：直接改私有属性）—— 像素档被值重推导挡住，链档未被跨行不变量挡住

第一次尝试（像素档，交换 x0/x1 的 `value_u`）：

```
consume() REJECTED forged batch: TICK_VALUE_RECOMPUTE_MISMATCH
```

原因：`consume()` 对 `pixel_only` 档**从冻结的 `edge.raw_u` 重新计算** `value_u` 并与伪造记录逐值比对（T:517-522），交换后的值对不上，被挡住。这是「出口全检」的正面例子。

**但换成链档（chain_backed）后攻击成立**（`attack_probe_2_chain_reorder.py`，即攻击 1b）：

```
O02:x0 legitimate candidate values (u): [0, 10000, 20000, 30000]
O02:x1 legitimate candidate values (u): [0, 10000, 20000, 30000]
legit submit() rows (x0,x1): [('O02:x0', 10000), ('O02:x1', 20000)]
FORGED consume() result: x0=30000 x1=0  inverted=True
CONFIRMED: consume() accepts an interval-INVERTED chain-backed batch built
from two individually-legitimate, pre-existing candidates of each edge.
```

做法：`session._current = TickBatch(...)`（普通属性赋值，不是 `object.__setattr__` 绕过 frozen、不是 ctypes、不是导入模块外的私有函数——比 B2 的 `_mint_sealed_ladder()` 门槛更低），把 x0 的候选换成该边**自己合法存在**的 node3（30000u），x1 换成该边自己合法存在的 node0（0u）。`consume()` 对每一行的**数值**都从冻结 `self._packet` 重新 `evaluate()` 并核对（T:513-522）——两行数值各自都对得上（30000 确实是 x0 那条链 node3 的真实值，0 确实是 x1 那条链 node0 的真实值）——**但跨行的区间顺序（x0<x1）从未在 `consume()` 里重新核过**，只在 `submit()`（T:470-480 的 `by_id` 循环）核过一次。

进一步核实：`OpeningReview.__init__`（O:178-179）把 tick facts 的 `value_u` 直接写进 `along_lo_m`/`along_hi_m`，**全程没有 `lo < hi` 的再校验**（`grep -n "along_lo_m\|along_hi_m" opening_adjudication.py` 只有赋值行，无比较）。也就是说：**如果 `_current` 曾经不经过 `submit()` 就被设置**（哪怕是未来一次重构里的一个 bug，不必是恶意攻击），区间倒置的假事实会一路静默流进洞口几何,不会被任何下游校验拦下。

按复核单要求反查「哪个方向没有锁」：submit() 已有的 `by_id` 顺序检查（T:470-480）搬进 `consume()` 重跑一次，对**所有合法批次**（本来就满足顺序）是无操作、不会让任何现有测试变红——不存在「加了就会红」的理由挡着这把锁。**这属于 R-1/B-2「代码重检须给同图回裁出口」这条仍然成立的承诺里，出口重检不完整的一角。**

**判定：阻断②**（不要求重写模块，只要求在 `consume()` 里补一次与 `submit()` 相同的跨行区间重校验；建议同时在 `OpeningReview.__init__` 组装 `along_lo_m/along_hi_m` 处加一道防御性断言，双点加固）。

### 攻击 2（B2 原型：`deepcopy` 走 `cls.__new__`）—— 复现为 `TickSession.__new__` 绕过 `__init__`

```
type(fake) is TickSession: True
FAKE session .consume() SUCCEEDED with zero __init__ validation ever run:
[('O01:x0', 10000), ('O01:x1', 20000), ('O01:z_low', 5000), ('O01:z_high', 15000)]
VERDICT: `type(plan) is not TickSession` in OpeningReview.__init__ would ACCEPT this object.
```

`TickSession.__new__(TickSession)` + `__dict__.update(...)` 完全跳过 `__init__`（无 schema 校验、无链一致性校验、无精度校验），构造出的对象 `type(...) is TickSession` 为真，`OpeningReview.__init__` 的类型检查（`type(plan) is not TickSession`）会照单全收。**判定：与 B2 同型（不阻断，理由同下）**——这条攻击本身没有产出与「正确执行 `__init__`」不一样的**数值**（因为我在构造假会话时仍然让它的 `_packet`/`_current` 内部自洽），`consume()` 的值重推导逻辑照样对自己构造的假 `_packet` 一致地生效；真正有杀伤力的仍然是攻击 1（跨行不变量缺失），本条只证明「类型检查本身不能替代内容校验」这一已知事实，未额外产出新的正确性缺口。

### 攻击 3（B2 原型：`__class__` 重赋值）—— 被内容字节相等检查挡住

```
type(imp) is TickBatch: True
Impostor with __class__ reassignment ACCEPTED: [...]   # 只是原样克隆 current，无害
Impostor with DIFFERENT forged record REJECTED: TICK_BATCH_INVALIDATED
  (blocked by byte-equality check against self._current.record, not by isinstance)
```

`consume(expected_batch_id, batch=X)` 要求 `X.record == self._current.record`（逐字节比较，T:498），**不是靠 `isinstance`/`type` 挡住的**——所以哪怕把一个普通类的实例通过 `__class__` 重赋值伪装成 `TickBatch`，只要它的 `record` 与当前 `_current.record` 不是逐字节相同，就会被拒绝。**这是三条攻击里唯一一条被彻底挡住、且挡它的机制是「内容比对」而非「类型标签」的**——比 B2 当时的对应设计更强（B2 的等价点是 `isinstance` 检查，这里是内容比对），**记为正面发现，不阻断**。

### 自设攻击 4：canonical JSON 编码collision

```
freeze(0.0) == freeze(-0.0)? False
key order collapsed by sort_keys? True   (预期内，键顺序本就不该承载语义)
freeze(1) == freeze(1.0)? False (int 1 == float 1.0 in Python, must stay distinct in bytes) -> safe, distinct bytes
NaN correctly rejected by allow_nan=False
```

`freeze()`（`sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False`）在 int/float 边界、-0.0/0.0、NaN 上均未发现「语义不同→字节相同」或「语义相同→字节不同」的坍缩。`Expression`/`OperandRef` 的字段类型被严格限定为 `str`/`int`/`Literal[...]`，无浮点字段参与 candidate_id 计算，canonical化在这一层**没有可乘之隙**。**判定：不阻断，本条是正面发现**（design 对这类攻击面的防御比预想的更扎实，未发现需要修的东西）。

## §三 两条自设同形输入 + 自造第三条

**核对施工方两条「新例」（1800/3600/7200@318.5 与 2150/6450/8600@407.2）**：逐结构核对后确认执行档的措辞是**诚实的**——它自己写「两例都保留 `Q:node1` 与 `P:node2` 同值，但不是同一节点的结构；数值、总长、像素键都不同于旧例」，**没有声称这是新的结构维度**，只是同一形状换了数字。三条例子（含原例）在结构上完全一致：P 是 4 节点链、Q 是 3 节点链（跳过第一段）、`Q:node1 == P:node2`。这与复核单警告的「换了数不等于同形而不同」相符，但**执行档本身没有过度宣称**，属于诚实自证，不构成扣分项。

**自造第三条（走未测过的维度）**：`own_third_collision_input.py`。构造三条链 P（5 节点）/Q（3 节点）/R（3 节点）共用同一个像素键 `512.75`，产生 **4 组独立的两两节点值碰撞**（P:node1↔R:node1、P:node2↔Q:node1、P:node4↔Q:node2、P:node4↔R:node2），三种写入顺序：

```
Three write orders produce identical candidate-identity fingerprints: True
Total distinct addressable node candidates at the single pixel key 512.75: 11
  (spans 3 chains x 5/3/3 nodes with 4 pairwise value-collisions)
```

11 个候选身份（`chain_id, index, value_u` 三元组）在三种写入顺序下**逐一存活、指纹完全一致**，且提交前 `consume('not-decided')` 三次都正确抛出 `TICK_BATCH_INVALIDATED`。**结论：R-2 的身份保留机制不是只对「两链一次碰撞」这一种最简形状生效，对三链、多重两两碰撞、任意写入顺序都保持正确——这是比施工方两条新例更强的证据，判定 R-2 在这一维度上稳固，不阻断。**

## §四 R-1..R-4 逐条闭合复核

方法：所有行号一律用 `awk 'NR==<n>{print}'` 或 `grep -n` 直接回源文件核对（**不从 diff/`git show` 数行号**），并对每条设计要求额外跑一次端到端行为验证（而非只读代码）。

### R-1（候选/事实分离 + 全集来源 + 回第一步）—— 核实通过

- 锚点核对：T:305 `_raw_edges` 定义 / T:397 `SAME_IMAGE_MODEL_REQUIRED` / T:429 `STALE_TICK_RESPONSE` / T:436 全集覆盖比较 / T:449 chain_backed 求值 / T:458 pixel_only 求值 / T:478 区间检查条件 / T:486 冻结当前批次 / T:542 `_current = None` / T:555 重建新包 —— **全部逐行核对无误**（见 `probe_outputs.txt` 之外，本表通过 `awk` 精确定位，未见文档记录）。
- **端到端验证**（`r1_r4_e2e.py`）：构造一个真实 `OpeningReview`，提交 `whole_building_review='return_to_step_one'`：

  ```
  submit() returns named exit: RETURN_TO_STEP_ONE_FROM_SPATIAL  detail={'images': ('plan1',), 'exits': {}}
  CONFIRMED: old plan batch invalidated -- consume() now raises TICK_BATCH_INVALIDATED
  ```

  确认「整体审查推翻 ⇒ 使旧批次失效 ⇒ 依赖它的输入随之失效」这条状态转换**真实可执行**，不是只停留在文档描述。

### R-2（身份≠同值 + 补证退债闭环）—— 核实通过

- 碰撞例三条（原例+两条新例+我方三链例）均确认身份不因同值坍缩。
- **端到端验证**（`r2_debt_lifecycle.py`）：`pixel_pending_evidence` 产生 `debt_id` → `reconsider(supplement=...)` 供入缺失链 → 重新 `select`（chain_backed）→ `retired_debt_id` 精确等于原 `debt_id`：

  ```
  debt_id after first submit: 755af91f...
  After reconsider+select(chain_backed): retired_debt_id=755af91f... == original debt 755af91f...? True
  ```

  且独立确认这条退债链路**完全不touch** legacy B4 的 `obligation=None`/`assert_backed` 逻辑（执行档 §五对此的表述准确，未借旧 API 的行为冒充新模块已经修复）。

### R-3（完整运算签名，5900 vs 4300 硬例）—— 核实通过（含一次自我纠错）

首次构造硬例时误用 `domain="segment"` 索引 1/2（这实际算出的是合法的「segment1+segment2」= 节点1到节点3的距离，本身正确，不是漏洞——是我自己的测试构造错误）。按契约原意重构（`domain="node"` 的 node1/node2 喂进 `anchored_sum`）后：

```
evaluate() REJECTED as designed: OPERAND_REF_DOMAIN (would have produced 5900=5900 if allowed)
Legit segment0+segment1 sum: 43000 units = 4300.0mm (true value 4300mm)
```

`resolve(ref, "segment")` 严格要求 `ref.domain == "segment"`，把 node ref 递给它会在入口被拒绝——**硬例确认走不通**，且走的是具名出口 `OPERAND_REF_DOMAIN`。

### R-4（本次认领决定绑定）—— 核实通过

- `attack_probe_1.py` 攻击 3 已证明：换一份内容不同的批次会被 `TICK_BATCH_INVALIDATED` 拒绝，挡它的是**内容字节比对**不是类型标签。
- **端到端验证**（`r1_r4_e2e.py`）：两个各自独立构造、源字节完全相同的 `TickSession`（`sA`/`sB`），各自 `submit()` 后：

  ```
  same source bytes -> same packet_id? True
  same source bytes -> same batch_id (since content identical)? False
  Cross-session batch substitution REJECTED: TICK_BATCH_NOT_CURRENT_DECISION
  ```

  因为两次 `submit()` 的 `TickResponse.reason` 字段不同（"A" vs "B"），批次内容/哈希天然不同，跨 session 替换被拒绝——证明「当前持有者绑定」不依赖 session 对象身份，而是绑定到**冻结内容**本身，符合契约设计意图。

## §六 分辨力：新锁摘不摘得动

抽取 3 条自认最承重的锁做变异（命令与原始输出见 `mutation_log.txt`）：

| 变异对象 | 变异内容 | 目标测试 | 结果 |
|---|---|---|---|
| T:478 区间检查条件 | 改为 `if False:`（永不触发） | `test_collapsed_or_reversed_interval_returns_to_first_step` | **2 failed**（DID NOT RAISE） |
| T:464-467 退债条件 | `retired_debt_id` 恒为 `None` | `test_debt_supplement_reclaim_retirement` | **1 failed**（`assert 0 == 2`） |
| T:168-170 补证源不匹配检查 | 改为 `if False:`（永不触发） | `test_failed_evidence_replacement_cannot_resurrect_old_response` | **1 failed**（DID NOT RAISE） |

三处变异均已用 `git checkout -- src/agent/correction/tick_claim.py` 复原，复原后重新跑 `tests/test_tick_claim_a6.py tests/test_opening_adjudication_a6.py` = **27 passed**，与变异前一致。**结论：三条锁均有真实牙齿，不是恒红/无观测力的结构。**

## 未复现项清单

- 未运行真实模型（reading VLM / correction LLM）对刻度做认领决策；证据里的模型响应均为诊断 fixture，与执行档 §七 的边界声明一致。
- 未接 `run_pipeline`/`CorrectedGeometryV3`/judge，未跑 sm25 端到端——这属于 E-a/J 的验收范围，本单契约本身也明确排除。
- 未逐条重新执行施工方 `capture_legacy.py`/`probe_after.py` 里全部 97 行探针输出（已抽样核对表中引用的关键行，未做逐行复算）。
- 未对 `opening_adjudication.py` 的四分类（①②a②b③）逐类做变异测试（§六抽样落在 `tick_claim.py`，因为它是本单两条最重阻断都涉及的文件；`opening_adjudication.py` 的核心状态机——回第一步失效——已在 R-1 端到端验证中间接覆盖）。
- 未验证「跨进程」场景（本单契约本身也明确声明不覆盖）。

## 是否改过被审对象

**改过，且已复原，如实披露**：§六变异测试对 `src/agent/correction/tick_claim.py` 做了三次临时字符级修改（详见 `mutation_log.txt`），每次修改后立即运行目标测试观察失败，随后立即 `git checkout -- src/agent/correction/tick_claim.py` 复原。复原后 `git status --short src/ tests/` 确认无残留改动，且重跑两个新测试文件确认 27/27 恢复全绿。**除这三次变异-复原循环外，未对被审对象做任何其它修改**；未修改任何裁决书、执行档、契约正文。

## 最薄弱一处

不是施工方自己在 §七点名的那处（生产接线缺失，这个已经诚实披露且合理排除在本单范围外），而是**两处「入口检查了、出口没有对称地重新检查」的组合**：

1. §一的 C:11/C:83/C:130 组——这是**契约文档层面**的入口/出口不对称：删句本身对，但删除之后的约束只活在这份执行档的散文里，`plan.md` 的 E-a 验收项没有跟着补上，导致下一次施工可能只读 `plan.md` 而看不到这三条约束。
2. §二发现的**代码层面**的入口/出口不对称：`submit()` 的跨行区间检查（T:470-480）是这条批次唯一一次被验证顺序正确的机会，`consume()`（T:493-526）只验证逐行数值与整体覆盖，不重验跨行顺序。这两处**都精确对应本项目反复出现的同一个病根**——「入口收窄不是有效解，出口全检才是」——只是这次它不是攻击者恶意构造出来的假想威胁，而是**契约文档到验收清单之间、以及 submit() 到 consume() 之间**两处本来就该对称、但没有做对称的位置。两处修法都很轻（各自几行），但都需要在下一版里显式补上，而不是留给「以后有人会记得」。

---

**分段提交说明**：本裁决与独立证据目录一次性完成后分两段提交——第一段提交独立探针脚本与原始输出（`experiments/2026-09-05m_A6_tick_claim_crossreview_claude/`），第二段提交本裁决文档本身。
