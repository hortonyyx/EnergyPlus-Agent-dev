# E-a 执行档 · A 层②停报（生产平面源契约不相容）

本单**未完成接线，未通过 E-a-1/2/3**。开工读取完整派工单后，在第一步测量的入口核对中发现：生产证据链的 as-drawn v2 平面不能被 A-6 接收；A-6 接收的 v0 平面又不能进入生产证据链。因此依派工单 §七 **A 层②「本单的承重前提你发现是错的」**停止生产施工，交出可复跑的阻断证据。

这里的停报判断是：**现成 A-6 可消费生产平面源、可以先接现有入口再量配对**这一前提不成立。没有声称在 correction 层扩展 A-6 的源契约不可行，也没有把该扩展说成派工单明文禁止；需要重新对齐的是接线所消费的平面契约和洞口全集。

**未触发 A 层①。真实四立面的配对数尚未测得，不能记为 0，不能据此把病根归为 reading 精度。**本档也不把诊断程序叫作接线后的生产测量。

## 一、开工自检与范围

工作目录 `/tmp/ea_wiring_astra`，分支 `wt/09.06c_ea_wiring`。开工实际输出：

```text
$ pwd
/tmp/ea_wiring_astra
$ git log --oneline -1
f4ee52da 09.06g_wrapup_sixth_leg (A-11 + A-6 两条线合并; 权威全量 3907; 挡路新单 5→2)
$ grep -c 'opening_adjudication\|tick_claim\|OpeningReview\|TickSession' src/agent/pipeline.py
0
$ ls src/agent/correction/{facade_visibility,facade_convention,opening_synthesis,opening_adjudication,tick_claim}.py
src/agent/correction/facade_convention.py
src/agent/correction/facade_visibility.py
src/agent/correction/opening_adjudication.py
src/agent/correction/opening_synthesis.py
src/agent/correction/tick_claim.py
```

派工单 [2026-09-06c_Ea_wiring_dispatch.md](../request/2026-09-06c_Ea_wiring_dispatch.md) 在开工时为未跟踪文件，保持原样，不混入提交。未发现适用的 `AGENTS.md`，未使用子代理或自签跨家族审查。

本轮只新增本执行档和 `AI_agent/logs/experiments/2026-09-06c_Ea_wiring/` 的诊断证据。`src/`、`tests/`、`case_tests/` 相对 `f4ee52da` 的 diff 为空。没有修改 B4、reading、任何判分模块、旧 gt、A-11 或签字产物；没有安装依赖、写 site-packages、使用 `git add -A`，没有到旧工作树写文件。

## 二、真实入口实跑与排查过程

复跑命令（不需要模型服务）：

```sh
python AI_agent/logs/experiments/2026-09-06c_Ea_wiring/probe_contracts.py > AI_agent/logs/experiments/2026-09-06c_Ea_wiring/contract_measurement.jsonl
```

[probe_contracts.py](../../experiments/2026-09-06c_Ea_wiring/probe_contracts.py) 第 65 行实调适配器，第 69 行从 **`artifact.bundle.source_artifacts[0]`** 提取身份，第 70 行用同一份真实源 bytes 构造 TickSession，第 85 行实调未修改的 **`pipeline.run_correction_evidence_chain`**。生产入口显式 `profile="strict"`；`fixed_responses=()` 只用于不调用 provider 的诊断，没有以模型名义补决定，没有送 judge。

完整原文在 [contract_measurement.jsonl](../../experiments/2026-09-06c_Ea_wiring/contract_measurement.jsonl) 第 3—8 行：

| 真实文件 | classifier | 真实 pipeline 入口 | TickSession |
|---|---|---|---|
| `sm25_1f_v2.json` | `as_drawn_plan` / `adapt` | 适配进入决策循环 | `TICK_SOURCE_CONTRACT_UNSUPPORTED` |
| `sm25_2f_v2.json` | `as_drawn_plan` / `adapt` | 适配进入决策循环 | `TICK_SOURCE_CONTRACT_UNSUPPORTED` |
| `sm25_1f_as_drawn.json` | `as_drawn_plan_v0` / `known_not_consumed` | `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED` | 接收，102 条边 |
| `sm25_2f_as_drawn.json` | `as_drawn_plan_v0` / `known_not_consumed` | `EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED` | 接收，90 条边 |

v2 两次入口的原文是 `"status": "accepted", "success": false, "exit_reason": "round_budget_exhausted"`：这里只证明**源契约已被生产入口接收**。由于没有喂模型决定，两次都没有成功产品；不能把 accepted 读成整条生产链成功。

两条拒绝原文（1F；2F 同形原文亦已落盘）：

```text
TICK_SOURCE_CONTRACT_UNSUPPORTED: None
EVIDENCE_CHAIN_SOURCE_CONTRACT_UNWIRED: {'file': 'sm25_1f_as_drawn.json', 'contract': 'as_drawn_plan_v0', 'reason': None, 'wired': ['as_drawn_plan', 'as_drawn_elevation_v0', 'reading_view_legacy']}
```

排查到的现有路径及不能直接替代的原因：

1. **保持生产 v2 bytes。**适配器成功铸出 bundle；同一份 bytes 及从 bundle 提取的 input_id 进入 TickSession 后，被 [tick_claim.py:328](../../../../src/agent/correction/tick_claim.py#L328) 拒绝。不是文件路径、input_id 手拼或模型服务失败。
2. **改用已被 A-6 支持的真实 v0。**未改动的生产入口在 [pipeline.py:1147](../../../../src/agent/pipeline.py#L1147) 具名拒绝；`adapt_as_drawn_plan` 独立调用也返回 `ADAPTER_CONTRACT_MISMATCH`。不是 pipeline 尚未写 import 导致的拒绝。
3. **是否只是 schema 标签或文件名不同。**不是：v0 从 `/wall_bands/*/opening_runs/*/run_m` 定义全集；生产 bundle 的引用则指向 `/hypotheses/opening_candidates/*/span_m`。1F 为 **51 对 85** 个洞口，2F 为 **45 对 87** 个，ID 交集两层都为空；原文第 5、8 行保留全部 ID。v0 是 `B01:run0` 等，v2 是 `L001g0` 等。因此不能以改名、按顺序替换或把两套 bytes 当成同一个实例保留原身份接通。
4. **是否只补 TickSession 入口就够。**[OpeningReview 第 147—149 行](../../../../src/agent/correction/opening_adjudication.py#L147) 还独立要求源 schema 为 `as_drawn_plan_v0`，第 155—158 行把 bindings 与该源的完整端点集核相等。这一项是代码核查，未伪造可接收 v2 的 session 冒称实跑通过。
5. **立面侧是否另有同类源入口失败。**四份真实立面均已过 B3 适配，按 bundle 身份创建 TickSession，并带真实链配置生成的 supplement，全部成功；具名源身份和 SHA256 在原文第 9、11、13、15 行。阻断发生在进入跨图 OpeningReview 之前的平面契约边界。

这是现有入口和现有源的排查，不是对一切未来适配方案的“不可能性证明”。可行的后续工程方向是让 correction 的 TickSession/OpeningReview 支持生产 v2 原 bytes、真实 opening claim ID 和指针，再处理同源链声明及完整绑定，随后回到本单第一步测量；不能用 v0 旁路的结果冒充 v2 生产结果。

## 三、四立面测量状态及原文

**本节不是已完成的配对测量。**在尚不能建立合法生产平面 TickSession 的状态下，没有 OpeningReview 结果，没有 B4 的本次 unmatched 集合。因此分别列出“尚未进入配对”的洞口和具名入口原因，保留 `pair_count=null`；不填 0，也不把这些 ID 伪称 B4 已审未配对。

| 立面 | 真实洞口数 | 本次配对数 | 尚未进入配对的 ID | 具名阻断原因 |
|---|---:|---|---|---|
| South | 7 | 未测得（null） | O01、O02、O03、O04、O05、O06、O07 | `PRODUCTION_PLAN_V2_REJECTED_BY_TICK_SESSION` |
| East | 13 | 未测得（null） | O01、O02、O03、O04、O05、O06、O07、O08、O09、O10、O11、O12、O13 | 同上 |
| North | 8 | 未测得（null） | O01、O02、O03、O04、O05、O06、O07、O08 | 同上 |
| West | 6 | 未测得（null） | O01、O02、O03、O04、O05、O06 | 同上 |

以上原因是**诊断程序对实际 `TICK_SOURCE_CONTRACT_UNSUPPORTED` 的归类名**，不是新增生产错误码。原文第 9、11、13、15 行均为：`"measurement_status": "BLOCKED_BEFORE_OPENING_REVIEW"`、`"pair_count": null`，并保留每张立面的完整 source 身份。不存在可报告的配对总数。

另一个需要修正的测量前提是派工单 §三“`_elevation_document()` 从链档 mm 值出、不再是像素外推”这一无条件表述。该函数第 123、130 行实际消费 `TickFact.value_u`；[tick_claim.py:458](../../../../src/agent/correction/tick_claim.py#L458) 仅在显式 `select` 时产出 `chain_backed`，显式 `pixel` 仍产出 `pixel_only`。候选出现不等于认领完成。

本次四立面的**固定 pixel 控制**输出（完整原文第 10、12、14、16 行）：

| 立面 | 有候选边数 / 全部边数 | 提交前 | 显式 pixel 后 | 第一洞口 source x → consumed x（m） |
|---|---:|---|---|---|
| South | 28 / 28 | `TICK_BATCH_INVALIDATED` | 28 条 `pixel_only` | `[6.9219, 8.7512]` → `[6.92, 8.75]` |
| East | 52 / 52 | `TICK_BATCH_INVALIDATED` | 52 条 `pixel_only` | `[0.5367, 2.1646]` → `[0.54, 2.16]` |
| North | 32 / 32 | `TICK_BATCH_INVALIDATED` | 32 条 `pixel_only` | `[1.6864, 9.7254]` → `[1.69, 9.73]` |
| West | 24 / 24 | `TICK_BATCH_INVALIDATED` | 24 条 `pixel_only` | `[4.6523, 5.4783]` → `[4.65, 5.48]` |

控制的响应来源原文为 `"fixed pixel control; not a model measurement"`。这证明 A-6 入口允许两档，**不证明模型该选 pixel，不证明链档配对仍为 0，不替代真实同图认领，也不构成 A 层①依据**。既有 A-6 真实四立面测试亦显式用 pixel，见 `tests/test_tick_claim_a6.py:47`。

## 四、三条硬验收和其余接线约束的实际状态

| 验收 | 本轮锁的位置 | 当场变红 | 实际判定 |
|---|---|---|---|
| E-a-1 装配必须消费当前 OpeningReview | 未新增装配锁；A②停工发生在装配接线之前 | 未执行；入口契约拒绝不冒充过期 batch 锁 | **未实施、未验收** |
| E-a-2 两份源 bytes + batch record 落盘并重建 batch_id | 未新增生产持久化器或其锁；诊断日志只有控制批次的 ID | 未执行；日志的 batch_id 不冒充可重建落盘件 | **未实施、未验收** |
| E-a-3 旧 B4 dict API 无生产调用者 | 未新增 grep 锁；现状仍有 `opening_adjudication.py:198` 调用 | 未执行；现状清点不冒充变异验牙 | **未实施、未验收** |

同样，防 bbox 可见性退化锁、朝向接线锁、缺 `elevation_source` 不退债及 South 实例专属退债的接线锁均未新增，未宣称由既有单元测试完成了本单验收。固定控制只到 TickSession 出口，未为未执行的跨图配对提供猜定朝向。

## 五、接线点与两个真实构造点

[wiring_inventory.json](../../experiments/2026-09-06c_Ea_wiring/wiring_inventory.json) 以 AST Call 节点清点 `src/`、`scripts/` 的构造调用，没有把 schema 类定义计入。

| 位置 | 现状及本轮处理 |
|---|---|
| `pipeline.py:1032` `run_correction_evidence_chain` | 实跑 source/adapter 路由；没有修改，A-6 仍为 0 命中 |
| `pipeline.py:1255` 投影前装配段 | 没有接入 OpeningReview；测量入口阻断后停工 |
| `pipeline.py:1347` `run_correction` | 没有修改当前出口和 envelope 读取 |
| `pipeline.py:1605` `run_multifloor_correction` | 没有修改多层调用或交 judge 行为 |
| `projection_bridge.py:845` 构造点一 | 原样保留，`windows=[]`；未声称装配已消费 A-6 |
| `multifloor.py:583` 构造点二 | 原样保留，`windows=[]`；未声称多层拼装已保留洞口 |

**没有本轮新增的生产接线点。**真实入口的 strict 是本次诊断参数，不冒充“交 judge 的 strict 强制锁”已完成。

## 六、最薄弱一处及停报边界

最薄弱处是**尚未得到合法完整平面会话后的跨图读数**。本次证据确立的是两端源契约和全集不相容，未完成真实同图链认领、可见性筛选及 OpeningReview 配对。因此既不能判断修正契约后配对会增加多少，也不能判断 reading 精度是否仍挡路。

A②的判定还包含施工方对“现成 A-6 可直接接入生产”的前提解释；本档明确暴露这一解释供主控判断，没有把“需要扩展 correction 源契约”包装成派工单已有的禁令。后续应先明确 v2 原 bytes 与完整 opening claims 的消费方案，再进行第一步配对测量。本轮不自行改 B4、reading、容差或已签字基线来绕过这个入口。

B 层记录：用户消息要求 `git show --cached --numstat`；实际 Git 返回 `fatal: unrecognized argument: --cached`。按派工单 §五可用的 `git diff --cached --numstat` 查看同一暂存内容后提交，没有因此询问或停工。`AI_agent/plan.md` E-a 行仍写 B4 零生产调用者，按新派工单 §一已明确作废的旧读数处理，本轮没有修改计划文档。
