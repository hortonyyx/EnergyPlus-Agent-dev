# F-7 调查 · ⚠️停下上报：派工单两预设均不成立，真缺陷=接口错位（F-5 双胞胎）

- **日期**：2026-08-05
- **施工席**：GLM-5.2
- **派工单**：`AI_agent/logs/reviews/request/2026-08-05_f5_ruling_and_f6f7_dispatch.md` §3 F-7
- **状态**：**F-7 调查完成；派工单给的两种可能 + F-4 回灌修法都被证据推翻。请 orchestrator 裁修法方向（接口层，非 F-4 通道）。F-6 已落（`9fd8a9a`），F-2c 独立未阻塞。**

---

## 0. 先答派工单的硬要求：「失败抽签残留产物会不会被下一次消费？」

**结论：不会。**「03:36 残留 `correction_geometry.json`」**不是**被消费的来源。证据链：

1. **`correction_geometry.json`（pre-snap，`pipeline.py:679` 写）无任何生产消费路径读它。** 全仓 grep：只有 `render_geometry_viewer.py:595`（渲染）+ `judge_arbitration_sm24_audit.py:167`（审计脚本）读它；`src/` 生产码零读取。生产消费走 **accepted attempt 归档**（`_load_snapped` → `_accepted_output_path` → `attempts/NNN/output.json`，manifest-first）。
2. **correction 段内当场抽签的 `producer_draw` 是新鲜对象，不读盘。** `run_stage.py:324 geom = run_correction(...)` → `:370 build_verified_window_inputs_from_run(producer_draw=geom, ...)`。`run_correction`（`pipeline.py:599`）每次都 `_call_json_llm` 重新抽签，`correction_geometry.json` 是 LLM 返回**之后**才写的产物，不是输入。
3. **坏 `source_ids` 的抽签不可能成为 accepted attempt，故跨 run resume 不会消费它。** `_claim_links`（`window_sources.py:621`）跑在 `finalize_correction_draw`（`run_stage.py:375`）/ gate① 之**前**；它 raise 的抽签永远到不了 accept。`_auto_start_stage` 的跳过判定（`_stage_advance_ready`）只认 accepted attempt ⇒ 坏抽签不会被当已完成跳过。

⇒ **派工单 F-7 可能 #1（残留产物）排除。** `_claim_links` 拿到的 `source_ids=['D2']` 来自**本次新鲜 LLM 抽签**，不是残留。

---

## 1. 派工单可能 #2（「F-6 同族 / 走 F-4 回灌通道」）也被推翻

派工单 §3：*「如果不是残留……模型不知道 `source_ids` 要填 locator ⇒ 同样走 F-4 的回灌通道，把 locator 的格式要求纳入机械导出。」*

**这条修法结构上行不通，两条独立理由：**

### 1a. F-4 通道根本不会触发——`['D2']` 是 schema 合法的

`FieldProvenance.source_ids: list[str] = Field(default_factory=list)`（`schema.py:125`），**无格式约束**。`['D2']` 是合法 `list[str]` ⇒ 过 pydantic schema ⇒ 过 `_schema_only_correction_validator` ⇒ 被 `_call_json_llm` 当成功返回。

F-4/F-6 的回灌通道**只接 pydantic `ValidationError`**（`vocab.py:retry_guidance_for_correction` → `if not isinstance(exc, ValidationError): return None`）。schema 合法的抽签不产生 ValidationError ⇒ **通道永不开启**。报告 §6 自己的 traceback 就是铁证：失败发生在 `_claim_links`（`window_sources.py:634`），是**语义/源绑定**层 raise 的 `WindowResolverInputError`，不是 schema 层。

⇒ 把 locator 格式塞进 F-4 机械导出，对这条死点**零作用**——没有 ValidationError 可挂。

### 1b. 即便告诉模型格式，它也算不出合法 locator

`source_locator`（`window_sources.py:253`）= `src:` + sha256(`{input_id, observation_id, output_sha256, schema}`)，其中 `output_sha256` = **reading 产物字节的哈希**。模型抽签时既拿不到 reading 字节、也算不出这个哈希 ⇒ **物理上产不出合法 locator**。告诉它「用 `src:<64hex>` 格式」只会让它产出格式正确、内容必错的串。

---

## 2. 真缺陷 = 接口错位（与 F-5 同族：「B5 窗源这条路从没在合规产物上跑通」）

四条证据合围：

1. **prompt 从不提 locator / `src:` 格式 / `source_ids` 语义。** `_build_correction_messages`（`pipeline.py:329`）正文 + correction skill 文档（`A0_contract.md`/`A3_arbitration.md`）只讲 `ns[]`（perception/dimension id），grep `source_id|locator|src:|offer` 在 prompt 正文（388–445）零命中。
2. **prompt 根本拿不到 manifest/readings，无法构造 locator 目录。** `_build_correction_messages` 签名只有 `vector_dir/testdata_text/feedback/evidence_debt/target`——**不接收 manifest、不接收 reading artifacts**，结构上无法 build/offer locator。
3. **locator 目录基建（`build_window_source_offer`）在生产里彻底孤儿。** 全仓 grep：只在 `test_c2_b5_source_routing.py` 被调用；`src/`/`scripts/`/`skills/` 零调用，从未注入任何 correction prompt。
4. **B5 测试夹具手搓 locator 才过 `_claim_links`。** `test_c2_b5_parent_and_verts.py:171/203`、`test_c2_b5_source_routing.py:54/60/224/342` 都是 `source_locator(input_id=, observation_id=, output_sha256=sha256(<reading bytes>))` 现算出真 locator 塞进 `source_ids` ⇒ consumer 自洽、测试永绿；真实 LLM 抽签永远没有 locator ⇒ 必崩。

**模型实际行为是合理的**：真实 sm21 reading 的 window stroke id 就是 `S1`..`S12`（实测 `1f_view.json` 17 strokes / 7 window，id `S1`–`S12`）；模型把能看到的 observation id（`S11` 等）填进 `source_ids`——**它用唯一能引用真实源的方式在引用真实源**。错在消费者要的是模型给不出的 locator，且没有代码层把 observation id 映射成 locator。

⇒ 这是 **F-5 的双胞胎**：消费侧（`_claim_links`）要求的字段形态，生产侧（LLM）既不被告知、也物理上产不出，夹具手搓合规形态 ⇒ 测试绿、真链路必崩。

---

## 3. 附带发现：`_claim_links` 失败是「硬崩 flow」，不是「归档重抽」

`run_one_stage`（`step_orchestrator.py:251`）`out, report = draw_fn(None)`——**`draw_fn` raise 则异常直接穿出**，不会走到 `:253 file_stage_attempt` 归档为失败 attempt + 盲重抽。对照 `correction_draw_issues`（`run_stage.py:355`）返回 `CheckReport` ⇒ 归档重抽。

⇒ 即便修好接口错位，**「源绑定失败的抽签该硬崩还是该归档重抽」**仍是个待裁的独立口径（当前=硬崩）。这一点排在接口修法之后。

---

## 4. 修法方向（**接口层，请 orchestrator 拍**；⛔ 不放宽 `_claim_links` 校验、不手搓第二份 locator 词表）

两个结构性出口（都保持 `_claim_links` 的 locator 严格校验不动）：

- **（A）代码侧映射（R1.5 同形，推荐）**：模型在 `source_ids` 里填它**看得到**的 observation id（如 `S11`），代码在 `_claim_links` 之前用 catalog（已按 `(source_input_id, observation_id)` 建好）把 observation id 映射成 locator。模型永不见/不算 locator；坐标唯一换算归代码。与 R1.5「读图器不写公制坐标、代码唯一换算」、F-5 治理教训（夹具机械导出）完全一致。
  - 要决的点：`source_ids` 语义从「locator」改为「observation id」（B5 契约语义变更，需 orchestrator 认）；observation id 跨视图可能重名（`1f`/`2f` 都有 `S1`）⇒ 映射需带 view/input 上下文（模型可能要给 `1f/S1` 或代码按 window→floor 归属解析）。
- **（B）prompt 侧 offer**：构造 `WindowSourceOfferV1` 注入 prompt，令模型在 `source_ids` 填入 offer 给的 locator。代价：模型誊抄 64-hex 串（脆），且 offer 含 `output_sha256` 每 run 变、不可缓存；更重更易错。

**我倾向 A**（契合项目既有接口层方向 + 模型已在用 observation id 引用真实源）。但 A 改 B5 契约语义、且涉 observation-id 命名空间问题，属设计决策，**不由施工席自裁**。

---

## 5. 请 orchestrator 裁

1. F-7 修法走 **A（代码侧 observation-id→locator 映射）** 还是 **B（prompt 注入 offer）**，还是别的？
2. §3 的「源绑定失败：硬崩 vs 归档重抽」口径顺带定一下。
3. F-7 待裁期间，**F-2c（搬 `identify_reading_contract` 到 `reading/contract.py`，裁定已明确、独立未阻塞）是否先做**？还是严格按序等 F-7 裁完再动？

**纪律**：本轮第 4 次「派工方的题错了」（同 08-04/08-05 前三次形态：派工单前提与代码实情不符）。F-6 已干净落库（`9fd8a9a`，纯 F-6 全仓 2193/10/0、+4 锁零回归、双向 neuter 验分辨力）。F-7 停在这里等裁，未擅动接口、未放宽任何校验。
