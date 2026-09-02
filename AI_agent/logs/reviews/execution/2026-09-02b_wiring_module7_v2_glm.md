# 执行档 · 接线（模块 7 上半）v2 · GLM 施工席（2026-09-02）

- **派工单**：[`../request/2026-09-02a_wiring_module7_dispatch_v2.md`](../request/2026-09-02a_wiring_module7_dispatch_v2.md)
- **施工席**：GLM（glm-5.3）· **工作树**：`/tmp/wiring_glm` · **开工基线**：`36f80be`（= v2 单抬头）
- **开工自检三条**：HEAD=`36f80be` ✓ · v2 单存在 ✓ · `vector_contract.__file__` 落本树 ✓
- **改动清单**（`git diff --numstat` 原文见 §六）：生产 4 文件 + `llm.yaml` + 测试 4 文件改写 + 新锁 1 文件 + 实验档 1 目录

---

## 〇、改动总览

| 文件 | 改了什么 |
|---|---|
| `src/agent/reading/vector_contract.py` | §一A：`Disposition.ADAPT` 新枚举值；`CONTRACT_AS_DRAWN_PLAN` 改指 `ADAPT`；`_classify_rows` 第五分支（⛔ 不进 consumed · ⛔ 不当 offender · ✅ `adapted` 列表 + ledger 行点名）；`VectorDirDecision.adapted` 字段；`as_ledger()` 增 `"adapted"` 键 |
| `src/agent/pipeline.py` | §一B/D：`run_correction_evidence_chain`（新链入口）+ `run_correction(evidence_chain=…)` 显式开关（默认关）+ `EvidenceChainTerminal`；旧腿 `_build_correction_messages` 拒绝带 ADAPT 文件的目录（点名文件 + 指引开关）；§一C 模型拍（`_decision_beat_messages` 提示词 + `_make_decision_response_provider`）；逐环失败记录 `_run/evidence_chain_failure.json`；route 记录 `_run/evidence_chain_route.json`；outcome 落盘 `1_correction/decision_loop_outcome.json` |
| `src/agent/correction/decision_executor.py` | §一C：`run_decision_loop` 增 `response_provider`（模型席：每轮拿到**当轮** packet 再作答）；`responses` 改默认 `()`；双源同给 ⇒ `RESPONSE_SOURCE_AMBIGUOUS`；provider 模式必须显式 `round_budget`。固定 responses 语义逐位不变（m56 全部既有锁绿） |
| `src/agent/correction/decision_schema.py` | §一C：`assert_response_payload_carries_no_coordinates`（无坐标 guard 的运行时对偶：数值叶 + 字符串里坐标对/轴赋值，指名 JSON 路径）+ `CoordinateSmuggledInResponse` |
| `src/configs/llm.yaml` | §一C：`correction_decision` section（模型拍唯一配置入口；删掉则按 llm.py 规则 fallback `default`） |
| `tests/`（4 改 1 增） | 翻 7 处 pin 锁（见 §二变动清单）+ 新锁 `test_o22m7_evidence_wiring.py` 22 条 |

---

## 一、验收 1 —— 真实 sm25 新格式平面产物走完 A→C ✅（**模型真跑**）

命令（工作目录 `/tmp/wiring_glm`；产物落
`AI_agent/logs/experiments/2026-09-02b_m7_evidence_chain_run/`，输入 = 逐字节拷贝的真实
`sm25_2f_v2.json`）：

```python
run_correction_evidence_chain(
    base / '0_reading', 'sm25_2f_v2.json',
    out_dir=base / '1_correction',
    profile='exploratory', round_budget=3,
)   # 不传 fixed_responses ⇒ 模型拍真跑（llm.yaml section correction_decision / deepseek-v4-pro）
```

输出原文：

```
MODEL BEAT RAN. elapsed=185.8s
success: True
exit_reason: success
rounds: 2
  round 0 | selected: 22 | rejected: 0 | failed_checks: [] | completion: degraded
  round 1 | selected: 0 | rejected: 0 | failed_checks: [] | completion: degraded
residual open items: 0
residual debts: 3
degraded walls: 0
```

`_run/evidence_chain_route.json` 原文（模型真跑的证据行 = `response_source`）：

```json
{
  "route": "evidence_chain",
  "source_file": "sm25_2f_v2.json",
  "contract": "as_drawn_plan",
  "adapter": "adapt_as_drawn_plan",
  "profile": "exploratory",
  "round_budget": 3,
  "response_source": "model:correction_decision",
  "outcome_success": true,
  "exit_reason": "success",
  "outcome_path": "AI_agent/logs/experiments/2026-09-02b_m7_evidence_chain_run/1_correction/decision_loop_outcome.json"
}
```

模型最后一轮原始响应（`1_correction/correction_decision_raw.txt` 全文；round 1 对新
provisional 的 accept，绑当轮 packet_hash）：

```json
{
  "packet_hash": "e25325847df74713f5be82d7ccb2e6f6a0437f4c8bcedccaa7c36e677f8540a3",
  "item_decisions": [],
  "whole_building_review": {
    "verdict": "accept",
    "findings": []
  }
}
```

- round 0 的 22 项 `select_candidate` 决策：`decision_loop_outcome.json` 的
  `rounds[0].selected_item_ids`（22 个 item id 全列）+ `rounds[0].decision_hash`
  （`76906624…`）。⚠️ `_call_json_llm` 只存 last attempt 的 raw，round 0 的原始文本被
  round 1 覆盖——既有行为，未改。
- 全档（README + 输入 + 产物 + thinking）→
  [`logs/experiments/2026-09-02b_m7_evidence_chain_run/`](../../experiments/2026-09-02b_m7_evidence_chain_run/README.md)

## 二、验收 2 —— 新链关闭时全量不红不丢 + 变动清单 ✅

汇总行（`-n 6`，与导入自证同一条命令；全档 →
[`logs/experiments/2026-09-02b_m7_evidence_chain_run/full_suite_tail.txt`](../../experiments/2026-09-02b_m7_evidence_chain_run/full_suite_tail.txt)）：

```
3654 passed, 13 xfailed, 211 warnings in 486.60s (0:08:06)
EXIT=0
```

`failed` 恒 **0**、`xfailed` 恒 **13**、`passed` = **3654** ≥ 3632。
差值 = 3654 − 3632 = **22** = 新锁 `tests/test_o22m7_evidence_wiring.py` 的 22 条
（`--collect-only` 实测 22 collected）；翻锁 7 处全部为改写/改名，数量不增不减——
**没有计划外的红，也没有消失的锁**。

### 变动清单（每条被改写/改名的锁，与「它原本保护的规则，现在由谁保护」）

| # | 锁（旧名 → 新名） | 原本保护的规则 | 现在由谁保护 |
|---|---|---|---|
| 1 | `test_o22m1…::test_as_drawn_is_still_known_but_not_consumed` → `test_as_drawn_plan_is_wired_to_the_adapter` | as-drawn 是已知合同、⛔ 不被消费 | 同名锁的新形态（ADAPT 断言）+ `test_o22m7…::test_adapt_files_are_named_not_consumed_not_offenders`（不进 consumed/不当 offender 的台账三行表）+ f97 新目录拒绝锁（#6） |
| 2 | `test_o22m1…::test_no_new_contract_became_consumable` → `test_only_the_two_named_contracts_hold_wires` | 没有任何合同能悄悄长出一条线 | **同一把锁扩成两方向规则**：consuming 集合与 adapting 集合各自恰为一个点名合同；变异红（4b）由 `test_o22m7…::test_4b_a_third_contract_quietly_turning_{adapting,consuming}_goes_red` 两方向锁死 |
| 3 | `test_o22m2…::test_as_drawn_is_still_not_consumed` → `test_as_drawn_plan_is_adapt_not_consumed` | as-drawn 不被消费（模块 2 视角的同一 pin） | 同名锁新形态（ADAPT 且 ⛔ 不是 CONSUME——两条腿互斥由 `vector_contract` 第五分支结构保证） |
| 4 | `test_o22m3…::test_as_drawn_is_still_not_consumed` → `test_as_drawn_plan_is_adapt_not_consumed` | 同上（模块 3 视角） | 同上 |
| 5 | `test_f97…::test_b3_as_drawn_plan_is_known_but_not_consumed` → `test_b3_as_drawn_plan_is_wired_to_the_adapter` | as-drawn 识别为已知合同、第三种行为 | 同名锁新形态（ADAPT），`test_o22m7` 方向 1 锁真产物路由 |
| 6 | `test_f97…::test_b3_as_drawn_raises_and_says_known_not_unknown` → `test_b3_as_drawn_directory_is_refused_by_the_pasted_json_leg` | 目录里有 as-drawn 产物 ⇒ 旧腿响亮拒绝、点名文件、与 unknown 可分辨 | 同名锁新形态：拒绝仍在（点名文件 + 指引 `evidence_chain=True`），「不许静默丢掉 as-drawn 证据」成为新断言 |
| 7 | `test_f97…::test_nf1_empty_face_lines_list_is_still_as_drawn_plan`（内部断言翻） | 诚实空读 `face_lines: []` 仍路由 as_drawn_plan | 同一锁，disposition 行随合同注册翻为 ADAPT（识别行为未动，锁的另一半 `contract_id` 断言原样） |

**单子清单之外的翻锁**（v2 单预警「清单可能不全」，自扫发现）：只有 #7 一把。
v0 原型锁 `test_b3_historical_as_drawn_prototypes_are_known_contracts` 断言的是
`as_drawn_plan_v0` / `as_drawn_elevation_v0` 两个合同（本单未动，仍
`KNOWN_NOT_CONSUMED`）——**未翻、未改**。

新增锁（非翻锁）：`tests/test_o22m7_evidence_wiring.py` 22 条，覆盖验收 3/4/4b/5 与 B/D
开关，逐条对应见 §三/§四。

## 三、验收 3 —— 新链打开、任一环失败 ✅（五环各一次）

锁：`test_o22m7_evidence_wiring.py::test_link_failure_{source_read,adapt,compile,model,loop}`。
每环断言三件事：① 异常类型**原样**穿出（`pytest.raises` 按各自异常类型抓：`OSError` /
`json.JSONDecodeError` / `WallCompilerError` / `RuntimeError` / `DecisionLoopError`）
② `_run/evidence_chain_failure.json` 落盘且 `failed_stage` 指名该环 ③
`decision_loop_outcome.json` **不存在**。全文件共享 booby trap：`_build_correction_messages`
被替换成一碰即炸的 sentinel——旧腿在链上任何一环失败时都未被碰（「没有悄悄走旧的贴
JSON 路」的机械证明）。

失败环的构造方式（每环一个真实病因，非 monkeypatch 捏造，除 model 环外）：

| 环 | 病因 | 记录的 stage |
|---|---|---|
| source_read | 文件不存在（`OSError`） | `source_read` |
| adapt | 非 JSON 字节（`JSONDecodeError`） | `adapt` |
| compile | strict profile + ambiguous 面债 → 模块 4 自己的 `AMBIGUOUS_DEBT_BLOCKS_STRICT_PROFILE` | `compile` |
| model | `_call_json_llm` 重试耗尽（`RuntimeError`，monkeypatch 模拟 provider 死亡） | `model` |
| loop | 固定响应裁决本 packet 没有的 item → 模块 6 自己的 `DecisionLoopError` | `loop` |

（compile 环的 stage 归属按异常家族判：`WallCompilerError`/`EvidenceContractError` ⇒
compile、`DecisionLoopError` ⇒ loop、其余 provider 模式 ⇒ model——`pipeline.py` 的
`run_correction_evidence_chain` 里有注释说明。）

## 四、验收 4 / 4b / 5 ✅

**验收 4 三方向**（`test_route_direction_{1,2,3}…`）：
1. 合法新格式（真实 `sm25_2f_v2.json`）→ `route.adapter == "adapt_as_drawn_plan"`，走完落盘；
2. 旧格式（真实 `1f_view.json`，探针同款 68 KB 产物）→ `route.adapter == "adapt_legacy_reading_view"`；
3. 结构损坏的新格式（真产物挖掉 `observations`，再做一个**带 `strokes` 伪装**的变体）→
   `classify_vector_json` 两变体都 `CONTRACT_UNKNOWN`（BLK-A **实测**，非引注释）+
   `adapt_legacy_reading_view` 对同字节 `ADAPTER_CONTRACT_MISMATCH`（双向锁死，不许静默落回
   legacy）+ 新链入口自己的 `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED` 拒绝。

**验收 4b**：`test_4b_a_third_contract_quietly_turning_adapting_goes_red`——把第三个合同
（`Disposition.ADAPT`）塞进 `CONTRACTS`，用与主锁**同一个判据函数** `_wiring_sets`（显式传参，
⛔ 不重抄断言）重放 ⇒ `AssertionError`。对偶方向（第三个合同变 CONSUME）另有一锁。

**验收 5**：三把锁一组——
- `test_5_guard_passes_legal_and_rejects_every_smuggle_channel`：guard 直测四方向（合法含
  单个尺寸叙述过；数值叶 / 字符串坐标对 / `x=` 轴赋值三通道拒）；
- `test_5_the_beat_rejects_smuggled_coordinates_end_to_end`：**类型合法但字符串塞
  `12.34, 56.78`** 的 payload 经假 transport 走 provider 全真路径（真 `_call_json_llm` 的
  retry + validate）→ `RuntimeError` from `CoordinateSmuggledInResponse`；
- `test_5_neuter_the_guard_and_the_rejection_disappears`：**摘掉实现**（guard 换 no-op）后
  同一 payload 畅通无阻——即上一条锁的绿完全由 guard 实现承载（类型层看不见字符串里的数，
  不是同义反复）。

## 五、验收 6 —— 全量绿 ✅

见 §二汇总行（`-n 6`）。

## 六、git 与产物

`git diff --numstat`（提交前）：

```
48	7	src/agent/correction/decision_executor.py
72	1	src/agent/correction/decision_schema.py
437	3	src/agent/pipeline.py
53	11	src/agent/reading/vector_contract.py
18	0	src/configs/llm.yaml
25	10	tests/test_f97_vector_contract.py
29	6	tests/test_o22m1_as_drawn_producer_types.py
8	5	tests/test_o22m2_evidence_contract.py
11	7	tests/test_o22m3_evidence_adapters.py
```

（另有未跟踪新增：`tests/test_o22m7_evidence_wiring.py`（22 锁）+
`AI_agent/logs/experiments/2026-09-02b_m7_evidence_chain_run/`（验收 1 全档）+
本执行档。）

提交：只 add 本单动过的明确路径（见提交 itself）。

---

## 七、B 层对账（派工方说的 vs 我实测的）

| 派工方说的 | 我实测的 | 判 |
|---|---|---|
| pin 锁 `test_b3_…` 在 159/214 | `grep -n` 实测 `159`（`test_b3_as_drawn_plan_is_known_but_not_consumed`）/ `214`（`test_b3_as_drawn_raises_and_says_known_not_unknown`） | ✅ 一致（v2 更正后的行号） |
| pin 锁清单 6 把 | 6 把全部实存；**另扫出 1 把会翻**：`test_nf1_empty_face_lines_list_is_still_as_drawn_plan`（L211 断言 disposition） | ⚠️ 清单确不全（v2 单已预警），已一并翻 |
| §〇 表「①→②→③ 在真实 sm25 新格式产物上通」 | 复测通（冒烟 + 验收 1 全链 + 模型拍真跑 success） | ✅ |
| §〇 表 22 份 v2 产物含 sm25 两层 | 未重量（不在本单必做；引用了其中 `sm25_2f_v2.json`，能过 `AsDrawnPlanV2` 校验——链路本身就是证明） | ➖ 未复核（未承重） |
| `pipeline.py:452` 把识图 JSON 原文贴进提示词 | 改前属实（`_build_correction_messages` 的 `[reading vector]` chunk）；本单未删该行为（拆旧腿是另一单），只加了 ADAPT 目录拒绝 | ✅ |
| `run_correction` 在 `pipeline.py:732` | 实测 L732（改前） | ✅ |
| `_classify_rows` 是四分支穷举 | 实测四分支（unintelligible/CONSUME/EXCLUDE/KNOWN_NOT_CONSUMED+else） | ✅ 本单加第五分支（ADAPT） |
| 设计稿 `…_gpt_design.md:476` 目标态三值收窄 | 未逐字复核（范围裁定已由派工方给定，⛔ 不必再上报；本单按裁定执行「新增 ADAPT，不重命名」） | ➖ 未复核（裁定已给） |

## 八、本单明确不做（对照 §二，均未做）

投影桥 / 拆旧腿 / 重命名与 ledger 重排 / 补围栏加阈值——全部未动。`_build_correction_messages`
的 ADAPT 目录拒绝**不是**新围栏：它是「新链开了不许回落」的镜像规则（旧腿也不许静默吞
ADAPT 文件），且 A 项台账要求「在 ledger 里被点名」的行为面。若复核方判它越界，属 A 层
分歧，我按 §四停报流程接受裁定。
