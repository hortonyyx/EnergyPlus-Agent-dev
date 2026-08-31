# 派工单 · **②-2 模块 5 + 模块 6**：待裁决包 / 决定响应 · 决定执行器

- **日期**：2026-09-01 · **派工方**：orchestrator · **施工方**：**GLM 家族** · **审**：**GPT 家族**（跨家族）
- **基线**：**`58bb59f`** · **权威全量**：**3519 passed / 13 xfailed / 0 failed**（12m14s、`-n auto`、exit 0，四项哨兵全干净）
- **口径出处**：设计稿 [`2026-08-30_o22_evidence_contract_gpt_design.md`](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
  **§6.1 / §6.2 / §6.3**（三拍循环）+ **§9.1 第 5 步**（「建 packet/response/executor：
  模型输出 schema 无坐标，**先用固定 response 测三拍执行器，再接模型**」）。该设计稿**已过审、是现行口径**。
- **前置**：模块 1/2/3 **已跨家族审收口**；**模块 4 已交付但未过审**（见 §一 的纪律）。

---

## 〇、⛔ 排程（同机三席，家族各一）
GPT = F-154 重发（写 `src/agent/judge/` + `gt_staging/`）· **你 = 本单（写 `src/agent/correction/` 两个新文件）** ·
Claude 席 = NF-1 微单（写 `src/agent/reading/as_drawn/schema.py` + `tests/test_f97_vector_contract.py`）。
⇒ ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量；跑测 **`-n 4`**；
`git status` 不干净是正常的，**别碰别人的文件**；若你的测试因别人的改动变红 ⇒ **停下上报，别去修**。

---

## 一、⛔ 最要紧的一条纪律：**模块 4 未过审，你只许【消费】它，不许【改】它**

模块 4（`wall_compiler.py`）本轮正在送审。你要在它上面盖楼，但：
- ✅ **可以**：`from .wall_compiler import compile_wall_ir, WallCompilationV1, OpenItemV1, SymbolicCandidateV1, …`
- ⛔ **不许**：改 `wall_compiler.py` 任何一行；⛔ **更不许**在模块 5/6 里补一份平行实现。
- ⭐ **发现模块 4 不够用时 ⇒ 停下上报**（防 [[free-correctness-evaporates-when-representation-changes]]）。
  模块 3 与模块 2 并行时用的就是这条，**当时它生效了**。

⭐ **模块 4 已经给你留好了接缝**：`FixedDecisionV1` 的 docstring 逐字写着
「The response SCHEMA is module 5's; this type is deliberately the minimal binding」。
⇒ **你的 response 类型是那条接缝的正式版**，`FixedDecisionV1` 是它的最小绑定。

---

## 二、任务

### 任务 1 · 模块 5 = `src/agent/correction/decision_schema.py`（**新文件**）
出两个类型（字段以设计稿 §6.1 / §6.2 为准，**⛔ 不许自己发明字段**）：

**`CorrectionDecisionPacketV1`**（代码 → 模型）：
`packet_hash` · `input_bundle_hash` · `solver_revision` · `round_index` · `previous_decision_hashes[]` ·
`provisional_geometry` · `provisional_wall_summaries[]` · `entity_to_source_refs[]` · `auto_actions[]` ·
`consistency_results[]` · `open_items[]`。
⭐ `open_items` / `auto_actions` / 候选的形状**直接复用模块 4 已有的** `OpenItemV1` / `AutoActionV1` /
`SymbolicCandidateV1`，⛔ 不许重新定义一遍。

**`CorrectionDecisionResponseV1`**（模型 → 代码）：
`packet_hash` · `item_decisions[]`（`item_id` · `action ∈ {select_candidate, reject_all, request_reperception}` ·
`candidate_id`（仅 `select_candidate`）· `reason_code`）· `whole_building_review`
（`verdict ∈ {accept, findings}` · `findings[]`）。

⭐⭐⭐ **`requested_effect` 用 discriminated union，五个 kind 的值域是封闭的**（设计稿 §6.2 那张表逐字）：
`review_alignment` · `review_segmentation` · `review_topology_relation` · `review_opening_host` ·
`request_wall_reperception`。每个 kind 自己的 strict schema，⛔ 禁止未列字段。

⛔⛔ **模型输出 schema `extra="forbid"`，且【结构上】不存在任何坐标字段**
（`x/y/z/p1/p2/span/thickness_m` 一个都不许有）。
⭐ 这条不是靠命名纪律，是靠**类型层让它不存在** —— [[gate-measures-right-but-carrier-gets-swapped]]：
⛔ 别用词法检查（「字段名里不含 x」）来堵，那种堵法可以被换个名字绕过。

### 任务 2 · 模块 6 = `src/agent/correction/decision_executor.py`（**新文件**）
执行器**只接受绑定当前 `packet_hash` 的响应**，按设计稿 §6.3 五步：
① 校验 response 与候选集合 → ② 运行 `symbolic_operation`，**所有坐标/厚度/交点由代码求** →
③ 更新 `ResolvedWallV1` 与 source trace → ④ 重跑拓扑/围合/重叠/洞口 host/跨层与信息保存检查 →
⑤ 总体 finding 生成新候选，仍有 open item 则进入下一轮。

**成功条件必须同时满足**（设计稿 §6.3 逐字）：无 blocking open item · 确定性检查通过 ·
模型对**同一个 provisional hash** 给出总体 `accept` · 没有 strict profile 不允许的 residual evidence debt。
**响亮退出的四种**：无进展 · decision hash 循环 · 陈旧 packet · 轮次预算耗尽 ——
退出时**保留残余清单**，且 ⛔ **最后一次 provisional geometry 不是成功产物**。

### 任务 3 · ⛔ **本单不接模型**（设计稿 §9.1 第 5 步）
**只用固定 response 夹具测三拍执行器**。⛔ 不许改 prompt、不许改 `pipeline.py`、
⛔ 不许把 `as_drawn_plan` 的 disposition 改成指向新 adapter（那是模块 7 的一行，**必须最后做**）。

### 任务 4 · ⭐⭐⭐ **零接线锁用模块 4 的【改强版】形状，⛔ 不许用朴素版**
模块 2/3 那条 `test_the_..._imports_no_pipeline` 只查 `pipeline`；
而**朴素的「judge 不在 `sys.modules`」在这个包里结构性不可能绿** ——
import 任何 `correction` 子模块都会走包 init 链，经 `window_sources → reading → execution.step_orchestrator`
把 `{judge, judge.executor, judge.retry, judge.verdict}` 带进来。这是**包的既有基座，不是你的接线**。
⇒ **照抄模块 4 的两把锁形状**（[`tests/test_o22m4_wall_compiler.py:611`](../../../tests/test_o22m4_wall_compiler.py#L611)）：
1. **差集判据**：import 你的模块后的 pipeline∪judge 可达集，必须与 import 模块 2 契约后的**完全相等**；
2. **AST 判据**：解析你自己源码的全部非标准库 import，白名单**显式列出**，将来长出第三条 import 在 diff 上就红。

---

## 三、⛔ 禁令
1. ⛔ 不许改 `wall_compiler.py` / `evidence_contract.py` / `evidence_adapters.py` / `window_sources.py`
   （模块 1–4，其中 4 正在送审）。不够用 ⇒ **停下上报**。
2. ⛔ 不许动 `src/agent/judge/` 与 `case_tests/test_baseline/`（GPT 席在写）、
   ⛔ 不许动 `src/agent/reading/`（Claude 席在写）。
3. ⛔ 不许改 `pipeline.py`、不许改任何 prompt、不许改 `vector_contract.py` 的 disposition 注册。
4. ⛔ 不许在响应类型里出现任何坐标字段；⛔ 不许让执行器接受不在 packet 内的 candidate、
   不许接受陈旧 `packet_hash`、不许「选最近值」兜底。
5. ⛔ 不许改既有测试断言；既有锁变红 ⇒ **停下上报**。
6. ⛔ 不许 `git add`/`commit`/`pip install -e .`/`-n auto`/跑全量。
7. ⛔ 在 `.py` 的字符串常量（docstring 也算）里**不要写带仓库根前缀的生产文件路径** ——
   会造出一条真实依赖边（F-152 实证）。用不带前缀的相对写法或点号模块名。

## 四、验收表（⭐ 已按**三格**对撞：①禁令 ②任务项 ③**已收口模块的既有承诺**）

| # | 验收项 | 对撞检查 |
|---|---|---|
| 1 | ⭐⭐⭐ **坐标在响应类型里【结构上】不存在**：给出一份 `extra="forbid"` 的反证 —— 往 response 里塞 `x` / `thickness_m` / 任意新字段，**逐个被类型层拒绝**（不是被某条 if 拒绝） | ⛔ 与禁令 4 对撞；⛔ 与「别用词法堵」对撞：**若你的拒绝来自字段名匹配，本条不通过** |
| 2 | ⭐⭐ **陈旧 packet 必拒**：拿上一轮的 `packet_hash` 回复当前轮 ⇒ 响亮失败 | 与任务 2 一致 |
| 3 | ⭐⭐ **不在 packet 内的 candidate 必拒**：编一个合法格式但不在候选集里的 `candidate_id` ⇒ 响亮失败 | 与禁令 4 对撞 |
| 4 | ⭐⭐⭐ **四种响亮退出各有一份夹具**（无进展 · decision hash 循环 · 陈旧 packet · 轮次预算耗尽），且**退出时残余清单非空**、**最后一次 provisional geometry 没有被当成成功产物** | ⭐ 与设计稿 §6.3 逐字对撞 |
| 5 | ⭐⭐⭐ **成功条件的四个合取项各自可单独证伪**：造四份夹具，各让**一个**条件不成立 ⇒ **各自必须失败**。⛔ 只给一份「全满足则成功」不算交付 | ⭐ [[gate-with-only-negative-assertions-is-unobservable]]：证明这四条不是摆设 |
| 6 | ⭐⭐ **五个 `requested_effect` kind 各有一份夹具**，且**每个 kind 的未列字段被拒**；⛔ 第六个 kind 必须被类型层拒绝 | 与任务 1 的「封闭值域」对撞 |
| 7 | ⭐⭐ **模块 4 零改动自证**：`git diff 58bb59f -- src/agent/correction/wall_compiler.py src/agent/correction/evidence_contract.py src/agent/correction/evidence_adapters.py src/agent/correction/window_sources.py` **零输出** | ⛔ 与禁令 1 对撞：**若你「顺手」改了模块 4，本条必然不通过** |
| 8 | ⭐⭐ **零接线锁用改强版**（差集 + AST 两把），并给出它**当场变红**的证据（故意加一条非白名单 import ⇒ 红） | ⛔ 与任务 4 对撞；⛔ 用朴素版本条不通过 |
| 9 | **确定性**：同一份 packet + 同一份固定 response 跑两次 ⇒ 输出**逐字节相同**（沿用模块 4 的 canonical sort + `content_sha256` 纪律） | ⭐ 第三格对撞：与模块 2/4 已收口的哈希纪律一致 |
| 10 | `pytest -n 4` 跑**你的新测试文件 + 模块 1–4 的四个既有测试文件**，给出逐文件读数；⛔ 既有四个文件的数字**一个都不许变** | ⛔ 与禁令 5 对撞 |
| 11 | 列全改动路径（⛔ 不提交） | 与禁令 6 一致 |

## 五、停下上报（分层）
**必停**：模块 4 的 IR 不够用（⛔ 别自己补） · 设计稿 §6.1/§6.2/§6.3 里有互相矛盾的要求 ·
既有锁变红 · 任务项与禁令自相矛盾 · **本单要求的某件事在树上根本不存在**。
**只记不停**：字段取名分歧 · 测试条数 · `reason_code` 值域该多宽。

⭐⭐⭐ **累计 54 次停报，54 次都是派工方的题错 —— 放心停。**
⭐ **本单的选项清单本身也是个没签字的前提**：若你找到严格更优的做法，**直接走它并说明**
（[[dispatch-options-list-is-itself-a-hidden-premise]]）。

## 六、交付
代码（⛔ 不提交）+ 执行档 `AI_agent/logs/reviews/execution/2026-09-01_o22m56_execution.md`，
逐条给命令+读数、**你自己认为最薄弱的一处**、希望复核方重点打哪里。

---

# ⭐ 裁决（2026-09-01 · 回应施工方的停报）

## 七、**停报成立 —— 派工方题错 #56（累计 56，仍 56/56）：我把机制放错了模块**

**施工方报**：§6.3 第 ⑤ 步「finding 生成新候选」只能交付到**接收/校验/携带**；
五个 kind 里三个的候选生成需要模块 4 封闭枚举里没有的操作，
且 **§6.2 把生成器指派给 compiler / opening resolver，不是执行器**。

**主控逐字核实设计稿 §6.2 那张表，成立**：
```
review_alignment          → compiler 从这组既有实体生成有界 alignment candidates
review_segmentation       → compiler 根据 source intervals 枚举切分/合并候选
review_topology_relation  → compiler 枚举合法连接或分离操作并重跑围合
review_opening_host       → opening resolver 生成 rehost 候选
request_wall_reperception → 生成 §7.3 的墙级定向请求，不生成几何
```
⇒ **候选生成一条都不归执行器**，而我把 §6.3 第 ⑤ 步整条写进了本单（模块 6）的任务 2。
⇒ **同族 题错 #53**（「把语义规则写在哪一节，当成机制归哪个模块」）。

## 八、⭐ 施工方的处置**判对了**，⛔ 不升级为阻断
它没有整单停摆，而是**交付机制 + 显式上报**，依据是 §9.1 第 5 步「**先测执行器机制**」。
⇒ 主控确认：**本单范围内它已做完**；第 ⑤ 步的**生成器**属于**模块 4 的扩面**，另立单。
⭐ 这是第 56 次停报、第 56 次派工方题错 —— **停报机制今天第二次省下一整轮返工。**

## 九、⚠️ 施工方自报的最薄弱处 —— 主控接受并**登记为不阻断**
「检查面只有 2 项（共线重叠 + 余段覆盖），§6.3 点名的**拓扑 / 围合 / 洞口 host / 跨层**四类未实现」，
且它明说「**也未伪装**」（数据不在模块 4 IR；`check` 是封闭 Literal，假检查名构造不出来）。
⇒ **这与模块 4 那条阻断是同一形状**（声称覆盖的量没被量到），
**但两者性质不同**：模块 4 是**实现了却没人量**，本条是**明确声明没实现且结构上装不出来**。
⇒ ⛔ 不阻断；⭐ **登记**：「一个只破围合、不破重叠的决定集今天会被判成功」，随第 ⑤ 步生成器一并解决。

## 十、⇒ 下一步
① 本单绿件**送 GPT 跨家族审**（⛔ GLM 写的，不能自审）；
② **另立单：模块 4 补候选生成器**（§6.2 那三行 + opening resolver），
   ⭐ 与 [模块 4 补锁返工单](2026-09-01_o22m4_rework_single_face_channel.md) **合并成一张**更省
   —— 都是模块 4 的面，且都要动它的封闭枚举。
