# F-15 执行日志 · 校正抽签 schema 暴露内核专属字段

- 派工单：`AI_agent/logs/reviews/request/2026-08-07_f15_producer_schema_scope_dispatch_claude.md`
- 席位：Claude 侧 Sonnet 子代理 · 工作区：主工作树
- 开工 HEAD：`99d9521`（F-9 治本 B1 已由 orchestrator 代提交；`tests/test_f9_root_fix_mirror_hint.py`
  在此之上仍未落库，本次先以 `76a639d` 补齐）

## 0. 开工前置：F-9 保全状态核实

`git log -1` 显示 HEAD 已是派工单指定的保全提交
`08.07_f9_root_fix_b1_advisory_world_interval`（`99d9521`）—— **该步已由 orchestrator 在派工单撰写后完成，
本席位无需重做**。但同一批工作的单测文件 `tests/test_f9_root_fix_mirror_hint.py`
（锁 `derive_observation_reference_catalog`/`format_observation_reference_catalog`，
对着真实崩溃夹具 `tests/fixtures/f9_window_host_crash/` 手算区间常量）仍是 untracked
——orchestrator 的应急提交只带了 `src/`，漏了这个文件。7/7 通过，先单独 commit 补齐
（`76a639d 08.07_f9_root_fix_test_lock_recovery`，零 `src/` 改动）。

## 1. B1/B2 核验

### B1（推断：整个 schema 被交给模型，无留空信号）—— **成立，证据见代码**

- `src/agent/pipeline.py:355`（改动前）：
  `geom_schema = json.dumps(target.schema_model.model_json_schema(), indent=2, ensure_ascii=False)`
  —— `target.schema_model` 对 v3 路径就是 `CorrectedGeometryV3`（`geometry_validator.py:357`），
  **未经任何裁剪**，`facade_segments`（顶层数组）与每扇窗的 `facade_segment_id`
  都作为普通合法字段出现在 dump 出的 JSON Schema 里，随 prompt 一并发给模型
  （`pipeline.py:386` `f"{geom_schema}\n"`）。
- `schema.py`：`facade_segment_id: str | None = None`（WindowV3, 原 :198）、
  `facade_segments: list[FacadeSegment] = Field(default_factory=list)`（CorrectedGeometryV3, 原 :222）
  —— 两者都有默认值、**均非 required**，但 pydantic 的 `model_json_schema()` 仍把它们原样列进
  `properties`，且**没有任何字段级说明**告诉模型"这是核算的、不要填"。
- 结论：B1 成立。修法方向①（接口层结构性剔除）是正确路径。

### B2（推断：F-4 回灌机制在这条路径上没生效，若如此是第二个独立缺陷）—— **成立，且机制确实"接了线但认错类型"**

- 追踪调用链：`run_correction`（默认不传 `draw_validate`）⇒ `validator = _make_correction_validator(...)`
  ⇒ 这个 `_validate` 正是 `_call_json_llm` 的 `validate=` 回调（`pipeline.py:694-703`），
  **确实在 3 次重试循环内部**——`_make_correction_validator`→`parse_correction_draw`
  →`parse.py:101-105` 的早退检查（对**原始 dict**、先于 pydantic 模型校验）会在此处
  `raise WindowResolverInputError("producer_segment_ref_prefilled", category="model_draw_error")`。
  这就是派工单 A1 现象里"attempt 3/3"三次重试都命中同一个错的物理位置。
- **但** `retry_guidance_for_correction`（`vocab.py:242` 原文）的 `_guide` 函数首行是
  `if not isinstance(exc, ValidationError): return None` —— `WindowResolverInputError`
  是 `window_sources.py:75` 定义的 `class WindowResolverInputError(ValueError)`，
  **不是** `pydantic.ValidationError` 的子类。⇒ 每次命中这个错误，`_guide` 直接返回 `None`，
  `guidance_text = ""`，下一次重试是**完全裸的盲重发**（`pipeline.py:310-311`）。
- 结论：B2 成立，且诊断精确到"回灌通道确实挂在重试循环里、但只认 `ValidationError` 一种异常类型，
  漏判了 `WindowResolverInputError` 这整个族"。这是一个独立于 B1 的缺陷（B1 是"模型看到了不该看的字段"，
  B2 是"模型犯错后没人告诉它改哪"），已按派工单要求单独登记并修复（见 §3）。

## 2. 三条候选修法评估 + 选择

- **② 提示词层**：单独使用会与 F-12 教训冲突（prompt 正则锁可被无害改写绕过）——
  但本单**没有把提示词当防线**，只用作 ①③ 的补充说明（见下）。
- **① 接口层**：评估改动面后发现**不需要动 `CorrectedGeometryV3` 本身**——
  该模型只在两处被消费：(a) prompt 构造时 `target.schema_model.model_json_schema()`
  取"给模型看的 schema"；(b) 全流程校验/下游代码用同一个类做**真实解析**。
  只要新增一个"给 prompt 看的 schema 视图"函数，**不改任何 pydantic 字段类型/校验逻辑**，
  就能把 (a) 与 (b) 解耦——契约本身零改动，`_producer_preflight` 也零改动（继续硬拒）。
  ⇒ 改动面比预想小得多，**采纳**。
- **③ 回灌层**：B2 坐实是真实存在的独立缺陷，且成本很低（纯文本、不碰几何/坐标），**采纳**。
- **最终选择：①+③ 组合**（派工单推测的"可能最优"成立）：
  - ① 是主防线——模型的 prompt 里**结构上根本看不到** `facade_segments`/`facade_segment_id`，
    从源头压低模型去填它们的概率；
  - ③ 是纵深防线——万一模型仍以自由文本形式写出这些字段（JSON 输出不是强约束解码，
    理论上仍可能发生），第一次犯错后会收到明确的、格式限定的纠正指示，而不是被判处
    3 次盲重试后硬崩。
  - `_producer_preflight` 的硬拒绝**完全未改**（仍是唯一权威门），符合边界要求。

## 3. 改动清单

| 文件 | 改动 |
|---|---|
| `src/agent/correction/schema.py` | 新增 `CORRECTION_DRAW_FORBIDDEN` 标记常量；给 `WindowV3.facade_segment_id` 与 `CorrectedGeometryV3.facade_segments` 加 `json_schema_extra={CORRECTION_DRAW_FORBIDDEN: True}`。**不改字段类型/默认值/校验逻辑**。 |
| `src/agent/correction/vocab.py` | 新增 `producer_facing_json_schema(schema_model)`：对 `model_json_schema()` 输出做标记驱动的裁剪（顶层 + 每个 `$defs` 条目），并做 `$ref` 可达性剪枝，删除因裁剪而变孤儿的 `$defs`（如 `FacadeSegment`/`WorldInterval`）。`retry_guidance_for_correction`._guide 新增 `WindowResolverInputError` 分支：`category=="model_draw_error"` 时查 `_MODEL_DRAW_ERROR_GUIDANCE`（按 `code` 键控的纯文本、不含任何坐标/数值）；`category=="input_integrity_error"`（上游故障，重抽治不了）仍返回 `None`，保留 F-4a 原有的"只在能靠重抽解决时才引导"纪律。 |
| `src/agent/pipeline.py` | `_build_correction_messages` 改用 `producer_facing_json_schema(target.schema_model)` 而非裸 `model_json_schema()`；v3 目标额外加一句提示（"不要往 corrections/conflicts/unsupported 里塞 `window_host_resolution` 审计行"——这个门是通用 `list[dict]`，结构上剔不掉，只能靠文字提示 + `_producer_preflight` 硬拒兜底）。v1 路径逻辑分支为空字符串，byte-级不变（已锁）。 |

备份：`backup/src_history/2026-08-07_f15_producer_schema/{schema,vocab,pipeline}.py.orig`（改动前原文件）。

## 4. 锁

新文件 `tests/test_f15_producer_schema_scope.py`（15 条），另建夹具
`tests/fixtures/f15_producer_schema_scope/real_crash_draw.json`——**逐字节复制**
`run_2026-08-07_f9_root_fix_verify/1_correction/correction_raw.txt`（真实模型崩溃产出：
2 层楼、15 扇窗、8 个编造的 `facade_segments`〔含 64 个 `a` 的假指纹〕、全部 15 扇窗都填了
`facade_segment_id`）—— **不是手搓夹具**。

- Group A（4 条）：`producer_facing_json_schema` 的结构裁剪——剔除两字段、剪掉孤儿 `$defs`
  （`FacadeSegment`/`WorldInterval`）、其余字段逐字节不变、v1 目标零改动。
- Group A 附 1 条：标记本身钉在 schema 源头（`CORRECTION_DRAW_FORBIDDEN` 恰好只出现在这两处）。
- Group B（3 条）：**真实生产函数** `pipeline._build_correction_messages` 产出的 v3 系统提示词里
  schema 区块不含 `facade_segments`/`facade_segment_id`/`FacadeSegment` 字样；v3 提示词含
  `window_host_resolution` 警示句；v1 提示词 schema 区块与未裁剪的 `model_json_schema()`
  逐字节相等（证明 v1 路径零改动）。
- Group C（5 条）：`retry_guidance_for_correction` 对两个 `model_draw_error` 码给出非空、含具体
  字段名的引导；对 `input_integrity_error` 类仍返回 `None`（保留原纪律）；未登记的
  `model_draw_error` 码安全返回 `None`（不崩）；引导映射表恰好只覆盖 `_producer_preflight`
  实际抛出的两个码（新增第三个门却漏配引导会被这条锁点名）。
- Group D（2 条，端到端，走真实 `_call_json_llm` + 真实 `_make_correction_validator`
  + 真实 `parse_correction_draw` 早退检查）：**真实崩溃夹具**作为第 1 次抽签喂入，验证
  ① 触发与真实现象逐字相同的拒绝码 ② 第 2 次抽签消息里出现纠正性第 3 条 message
  ③ 该 message 提到 `facade_segments`/`facade_segment_id` 但不泄漏任何具体坐标
  （断言 `"14.88" not in guidance` 等）④ 2 次即恢复、不再耗尽 3 次预算。
  第二条锁是"控制组"：同一份真实崩溃夹具喂 3 次、`retry_guidance=lambda exc: None`（旧行为），
  确认 3 次后仍以 `RuntimeError` 崩溃——钉死 B2 修复前的真实后果。

## 5. neuter 自验（病灶本体改回缺陷形态，逐个独立复原）

三处独立还原、每次单独跑 `tests/test_f15_producer_schema_scope.py`（15 条）：

1. **还原 schema.py 标记**（去掉两处 `json_schema_extra`，保留 `CORRECTION_DRAW_FORBIDDEN`
   常量定义避免无关的 ImportError 噪音）⇒ **5 条真红**：
   `test_producer_schema_excludes_facade_segments_and_segment_id` ·
   `test_producer_schema_prunes_orphaned_defs` ·
   `test_producer_schema_preserves_everything_else_byte_identical` ·
   `test_schema_forbidden_marker_present_on_exactly_the_two_fields` ·
   `test_v3_prompt_schema_block_excludes_forbidden_fields`。其余 10 条绿（含 Group C/D，
   与该门无关，未被误伤）。
2. **还原 vocab.py 的 `producer_facing_json_schema`**（改回 `return schema_model.model_json_schema()`
   直通）⇒ **4 条真红**（同上一组少了 marker-presence 那条，因为那条只测 schema.py 自身声明，
   与消费函数无关——分辨力符合预期）。
3. **还原 vocab.py 的 `_guide`**（去掉 `WindowResolverInputError` 分支，改回只认
   `ValidationError`）⇒ **3 条真红**：
   `test_retry_guidance_translates_producer_segment_ref_prefilled` ·
   `test_retry_guidance_translates_producer_resolver_audit_prefilled` ·
   `test_e2e_real_crash_draw_gets_guided_then_recovers`。其余 12 条绿（含
   `test_retry_guidance_input_integrity_error_still_retries_blind` 与"控制组"锁均未受影响，
   证明它们真的在测别的东西，不是同一把开关的重复计数）。

三次还原后均逐字节 `diff` 复原（对照 `/tmp/f15_fixed_snapshot/` 与 `backup/src_history/...orig`），
复原后 15/15 再次全绿。

## 6. 真链路主验收

新 run 目录 `case_tests/e2e_tests/sm21_anchor/run_2026-08-07_f15_producer_schema_verify/`
（未覆盖任何既有 run）。`0_reading` 原样拷入 07-07 `run_2026-07-07_haiku_cv_retest/0_reading` 的
6 份 `*_view.json` + `reading_summary.md`（不重跑识图）。`run_config.yaml`：
`run_profile: exploratory` / `capability_profile: orthogonal_polygon` / `judge.mode: off` /
`review: {reading:false, correction:false, geometry:false}` / correction 模型
`deepseek-v4-pro`（effort high）—— 与 `run_2026-08-07_f9_root_fix_verify` 同配置，唯一变量是
本单的 F-15 修法。

```
python scripts/tool_scripts/run_stage.py --base-dir case_tests/e2e_tests --date 2026-08-07 \
    flow sm21_anchor run_2026-08-07_f15_producer_schema_verify \
    --judge off --geometry auto --to 1_correction
```

**第一次真跑（原始 F-15 修法，只标了 `facade_segments`/`facade_segment_id`）**：
`attempts/` 落地了 **001、002 两个归档 attempt**（此前 F-9 那次是彻底空的）——越界字段那道墙倒了、
归档重抽通道也通了。但最终仍在 attempt 3/3 失败：

```
attempt 3/3: ValueError: b2 draw contract requires empty facade_segments and null north_axis
```

`facade_segments` 这次确认为空（标记生效），**但模型仍然填了 `north_axis`**——orchestrator 独立核实
（详见 §9）并派了本单的续作。

## 7. 全仓回归（原始 F-15 修法，未含 §9 续作）

开工基线（本席位独立跑）：**2269 passed / 10 xfailed / 0 failed**
（先于 F-15 改动，含 §0 补齐的 F-9 测试锁）。

F-15 改动 + 15 条新锁落地后独立全量：**2284 passed / 10 xfailed / 0 failed**
（+15，零回归，零红）。

## 8. 边界自查（原始 F-15 修法）

- 未改 `_BASE_SIGN` / 方向约定。
- 未放宽任何容差、未碰 0.12m 既有债。
- 未改下游提示词 / 几何内核 / drift 门。
- `_producer_preflight` 的两处硬拒绝**逐字节未动**（`git diff` 确认 `window_sources.py` 零改动）。
- 未写自指锁（Group D 的真实崩溃夹具来自磁盘上的真实模型产出，不是拿实现自己的输出喂自己；
  Group A/B 用独立的 `CorrectedGeometryV3.model_json_schema()`/`_build_correction_messages`
  真实调用做比对基准，不是复述实现内部逻辑）。
- 未 `git add -A`；逐文件 add，提交前通读 `git status --short`。
- 未 push。

---

## 9. 续作（orchestrator A3 派工）：`north_axis` 是同族第二个门，两处「禁止清单」独立维护而漂移

### 9.1 orchestrator 的 A1/A2/A3 核实

**A1（真跑事实）**：`run_2026-08-07_f15_producer_schema_verify/1_correction/attempts/` 有 001、002 两个
归档 attempt——原始修法确实让越界字段那道墙倒了、归档重抽通道也通了。
**A2（真跑事实）**：最终仍在 attempt 3/3 失败，`facade_segments` 这次为空（标记生效），
**但模型仍然填了 `north_axis`**。
**A3（orchestrator 诊断，本席位独立复核为真）**：门在 `parse.py:113-116`
（改动前）—— `if target.phase_contract == "b2" ...: if geom.facade_segments or geom.north_axis is not
None: raise`，**硬编码检查两个字段名**；而 `schema.py` 的 `CORRECTION_DRAW_FORBIDDEN` 标记原本只打在
`facade_segment_id`（WindowV3）与 `facade_segments`（CorrectedGeometryV3）—— **`north_axis` 没标**。
⇒ 两处「禁止清单」各自维护、没有任何东西保证一致，`north_axis` 从一开始就是"门在禁、标记没禁、
prompt 因此照样展示"的漏网字段。

### 9.2 B1/B2 结论（orchestrator 的推断）

**B1（治标 vs 治本）**：只补标 `north_axis` 是治标——下次谁再加一道门，标记集还会再漂。**采纳**：
根治 = 把 `parse.py` 的 b2 门从"硬编码两个字段名"改成"遍历 `schema.py` 里被标记的字段"，让
**标记本身成为门的唯一输入**，而不是"标记"与"门"各自独立列出同一份名单。

**B2（phase_contract 是否需要给标记也加阶段限定）——orchestrator 明确要求"查清、别想当然"**：
查 `parse.py`/`feature_state.py`/`orientation.py` 三处后确认：
- `phase_contract` 只有两个取值：`"b2"`（草稿/Vg 定稿阶段，`north_axis` 必须留 `None`）与
  `"e4_orientation"`（**独立的确定性富化阶段**，`orientation.py:481-484` 专门为此新建一个
  `CorrectionTarget(..., phase_contract="e4_orientation")`，**这个 target 从未被喂给校正 LLM 的 prompt
  构造函数** `_build_correction_messages`/`producer_facing_json_schema`——那两者的唯一调用者
  `run_correction`/`correction_target()` 恒定产出 `phase_contract="b2"` 的 target）。
- `feature_state.derive_feature_state_claims` 显式证实：**只要 `phase_contract != "e4_orientation"`**
  （即校正草稿这条路径），`typed_north_axis` 恒为 `"declared_unpopulated"`——`north_axis` 在草稿阶段
  **永远不该被填**，不是"某些 capability_profile 允许、某些不允许"这种需要标记本身携带阶段信息的情形。
- ⇒ **orchestrator 的推断被证伪、按其"不要想当然"的要求推翻**：标记不需要携带阶段限定。
  单一布尔标记已经足够正确，因为标记的两个消费者（`producer_facing_json_schema` 与新版 b2 门）
  **各自的调用上下文本身就已经是 b2-only 的**——阶段限定已经在"谁会调用这个函数"这一层完成，
  不需要在标记数据结构里重复表达。

### 9.3 收口：单一来源 + 防漂移锁

**改动**（`src/agent/correction/schema.py` / `parse.py`，均已 `cp` 备份到
`backup/src_history/2026-08-07_f15_producer_schema/{schema.py.orig2,parse.py.orig,
parse.py.pre_windowresolvererror,vocab.py.orig2}`）：
1. `schema.py`：给 `CorrectedGeometryV3.north_axis` 补 `json_schema_extra={CORRECTION_DRAW_FORBIDDEN:
   True}`；新增 `draw_forbidden_field_names(model_cls)`——遍历 `model_cls.model_fields`、返回带该标记
   的顶层字段名，**这是标记的唯一读取入口**。
2. `parse.py` 的 b2 门改为 `populated = [name for name in draw_forbidden_field_names(CorrectedGeometryV3)
   if getattr(geom, name)]`，不再硬编码 `"facade_segments"`/`"north_axis"` 两个字面量。同时把 raise 的
   异常类型从裸 `ValueError` 换成 `WindowResolverInputError(..., category="model_draw_error")`（与
   `_producer_preflight`、parse.py 早退检查同一个类型/分类），新码 `producer_b2_forbidden_field_
   populated`——这样它自动获得 `retry_guidance_for_correction` 的引导（原来是裸 `ValueError`，`_guide`
   认不出、盲重试；真跑日志显示 attempt 1/3、2/3 都在这条消息上盲耗）。message 文本保留原前缀
   `"b2 draw contract requires empty facade_segments and null north_axis"`，`test_c2_b2_v3.py:264` 的
   既有正则匹配不用改（`WindowResolverInputError.__str__` = `f"{code}: {context}"`，`context["message"]`
   携带该前缀，逐位验证过）。
3. `vocab.py`：`_MODEL_DRAW_ERROR_GUIDANCE` 新增 `producer_b2_forbidden_field_populated` 一条格式化、
   不泄漏坐标的引导文本。

**⛔ 未触碰**：`_producer_preflight`（window_sources.py）逐字节不动；b2 门的 `if target.phase_contract
== "b2"` 阶段限定逐字节不动（仍是原来的 if，只改了 if 内部枚举字段名的方式）；未碰
`format_correction_system_vocabulary` 的 `north_axis_fields` 词汇块（残留但无害的小瑕疵，登记不修，
见 §10）。

### 9.4 防漂移锁（非自指）

`tests/test_f15_producer_schema_scope.py` 新增 Group E（3 条）+ north_axis 版 Group D e2e（1 条）+
Group C 追加（1 条）+ Group A/B 既有测试改为覆盖三字段（不再是"恰好两个"）——**共 20 条**（15 → 20）。

**Group E 的设计明确针对"不许自指"**：不是断言"实现自己派生的字段集合等于自己"，而是**在真实
`CorrectedGeometryV3` 类上用 `monkeypatch` 动态改标记**，观察**真实** `parse_correction_draw` 门的
接受/拒绝行为是否随之变化——这是外部可观测效应，不是读一遍实现再跟自己比对：
- `test_marking_a_previously_ordinary_field_makes_the_b2_gate_reject_it_live`：`notes` 字段本来没人
  拿它当门禁字段。运行时给它打上标记，真实 `parse_correction_draw` **立刻**开始拒绝一个填了 `notes`
  的草稿——证明"标记一次，两个消费者都自动生效"里"门"那一半是真的（不是仍然硬编码在读别的东西）。
- `test_unmarking_a_real_forbidden_field_makes_the_b2_gate_stop_rejecting_it_live`：反方向，把
  `north_axis` 的标记摘掉，真实门**立刻**不再拒绝一份填了 `north_axis` 的草稿——证明门里**没有**
  残留的旧硬编码检查在暗中兜底（如果改造只是"新增一条基于标记的检查、旧的硬编码检查没删干净"，
  这条会失败，因为摘标记后旧硬编码仍会拒绝）。
- `test_prompt_stripper_and_b2_gate_agree_on_forbidden_set_after_a_live_marker_change`：同一次运行时
  标记变更，`producer_facing_json_schema`（prompt 裁剪，JSON-schema-dict 路径）与
  `draw_forbidden_field_names`（b2 门，pydantic-model 路径）两个**结构完全不同**的消费者必须同时
  observe 到同一个新字段——这是"单一来源"论断本身的直接证据。
  （踩坑记录：`model_json_schema()` 的输出被 pydantic 缓存、与 `model_fields` 分开，纯 `monkeypatch.
  setattr` 不会让缓存失效，必须显式 `model_rebuild(force=True)`；用 `try/finally` 手动配平，
  `finally` 里连带断言复原后确实恢复原状，不只是"希望它复原了"。）

**neuter 自验（两轮独立还原，逐条对照精确红哪几条）**：
1. **只还原 schema.py 的 `north_axis` 标记**（去标记，保留 `draw_forbidden_field_names` 与其余两个
   已标字段不变）⇒ **6 条真红**：`test_producer_schema_excludes_facade_segments_and_segment_id` ·
   `test_producer_schema_prunes_orphaned_defs` ·
   `test_producer_schema_preserves_everything_else_byte_identical` ·
   `test_schema_forbidden_marker_present_on_exactly_the_three_fields` ·
   `test_unmarking_a_real_forbidden_field_makes_the_b2_gate_stop_rejecting_it_live`
   （其**控制步**"改标记前必须先被拒绝"这一步本身失败——因为没标记了，从一开始就不被拒绝，
   这本身就是缺陷复现）·
   `test_e2e_real_crash_north_axis_only_draw_gets_guided_then_recovers`。其余 14 条绿，
   与该字段无关的 Group C/D 原始锁、`notes` 相关的 Group E 两条均未被误伤。
2. **只还原 parse.py 的 b2 门**（改回硬编码 `("facade_segments", "north_axis")` 两个字面量，
   绕过 `draw_forbidden_field_names`）⇒ **2 条真红**：
   `test_marking_a_previously_ordinary_field_makes_the_b2_gate_reject_it_live` ·
   `test_unmarking_a_real_forbidden_field_makes_the_b2_gate_stop_rejecting_it_live`
   （两条都是直接操练"门是否真的读标记"这件事的锁）。其余 18 条绿——特别是
   `test_prompt_stripper_and_b2_gate_agree_on_forbidden_set_after_a_live_marker_change` 保持绿，
   因为这次只碰了门、没碰 schema 标记与 prompt 裁剪，精确对应"只神经了门这一侧"。

两轮均逐字节 `diff` 复原（对照 `/tmp/f15_fixed_snapshot2/`），复原后独立重跑 20/20 全绿。

### 9.5 全仓回归（含续作）

续作改动 + 5 条新锁落地后独立全量：**2289 passed / 10 xfailed / 0 failed**
（2284 → 2289，+5，零回归，零红）。

### 9.6 真链路重跑（含续作）

（结果见 §10，占位待重新真跑完成后填。）
