# 摊一 · F-16 施工日志（2026-08-08，Claude 侧执行档）

> 基线 = 派工单 `AI_agent/logs/reviews/request/2026-08-08_interface_sweep_round1_fixes_design.md`
> 只做「摊一 · F-16」两步（嵌套标记机制 + `WindowV3.floor` 派生）。
> ⛔ 未碰摊二/摊三（`src/agent/tools/fenestration_tools.py`、`src/validator/checks/schema.py` 是另一席改的）。
> ⛔ 未 `git add`/`commit`（orchestrator 统一提交）。
> 本稿含两轮：**第一轮**交付主体（Step 1+2 全部代码与锁）；**第二轮**是额度中断恢复后，
> 补 orchestrator 独立 neuter 抓到的一处缺锁（N1，见下）。

## 一、改了什么

### Step 1 · 嵌套标记机制（`facade_segment_id` 停止硬编码）

`src/agent/correction/schema.py`：
- 新增 `nested_draw_forbidden_fields(container_cls) -> dict[str, tuple[str,...]]`：
  对 `container_cls` 自己的 `list[<submodel>]` 字段，收集每个子模型上被 `CORRECTION_DRAW_FORBIDDEN`
  标记的字段名。只下探一层（`list[BaseModel]`），不递归更深——现状只需要这一层，递归会有
  "该下探到哪层" 的猜测风险。
- 把 `draw_forbidden_field_names` 内部逻辑抽成 `_marked_field_names(model_cls, marker)`，供两个
  marker 复用（见 Step 2）。
- `parse.py:103`、`window_sources.py:881`（`_producer_preflight`）改为遍历
  `nested_draw_forbidden_fields(...)` 返回值，不再各自硬编码 `"facade_segment_id"` 字符串。

接口形状：**新增函数**（不是让现有 `draw_forbidden_field_names` 支持递归）。理由——
现有函数的调用形状是「拿一个 model class，问它自己的字段」；嵌套场景的调用形状是「拿一个 model
class，问它每个 list 字段的子模型的字段」，两者输入输出形状不同，硬塞进同一个函数要么靠一个
`nested: bool` 参数分叉（等于两个函数共享一个名字），要么真递归到任意深度（但当前只有一层需求，
递归会引入"到底该下探几层"的臆测）。这条判断我在派工单标注的"两种都不顺手就停下上报"范围内自己
判断解决了，没有触发停工。

### Step 2 · `WindowV3.floor` 改为代码派生

`src/agent/correction/schema.py`：
- **新增第二个 marker** `CORRECTION_DRAW_DERIVED`（区别于 `CORRECTION_DRAW_FORBIDDEN`）。原因见
  下方「问题 1 回复」——这不是我随手加的，是发现"复用同一个 marker 会引入一个可致命的假阳性"后
  的必要分岔，不是可选的美化。
- `WindowV3.floor` 从继承的 `str`（必填）覆写为 `str | None = Field(default=None,
  json_schema_extra={CORRECTION_DRAW_DERIVED: True})`——**只在 `WindowV3` 上覆写**，基类 `Window`
  （v1/v2 用）原样不动。
- `CorrectedGeometryV3._v3_integrity`：原来的 `if win.floor != floor.name: raise` 改为
  `if win.floor is None: win.floor = floor.name; elif win.floor != floor.name: raise`——省流：
  不填就派生，填了但对得上就放行（幂等），填了但对不上仍然拒绝（见下方"防线分层"）。
- 新增 `nested_draw_derived_fields(container_cls)`，`nested_draw_forbidden_fields` 的姊妹函数，
  读 `CORRECTION_DRAW_DERIVED` 而非 `CORRECTION_DRAW_FORBIDDEN`。

`src/agent/correction/parse.py`：
- 新增一段独立循环（不是塞进 Step 1 那条循环），基于 `nested_draw_derived_fields`，对**原始
  payload dict**（`model_validate` 之前）检查每个 window 是否填了 `floor`，填了就抛
  `WindowResolverInputError("producer_window_floor_populated", category="model_draw_error")`。
  **为什么不是同一条循环**：两者虽然都是"标记了就不许填"，但触发后要给模型的纠错话术完全不同
  （一个该说"删掉 facade_segments/facade_segment_id"，一个该说"floor 会自动派生、别填、
  floor_id 填对就行"）——错话术等于 F-15 A1 那次教训的另一种形态（说错要删的字段）。

`src/agent/correction/window_sources.py`（`_producer_preflight`）：
- **没有改动去检查 `floor`**——这是本摊设计中最容易踩的坑，见下方「防假阳性」一节。

`src/agent/correction/vocab.py`：
- `producer_facing_json_schema`（模型可见的 JSON Schema 机械剥除函数）改为同时认
  `CORRECTION_DRAW_FORBIDDEN` 与 `CORRECTION_DRAW_DERIVED`——两种标记的"模型不该看见"后果相同，
  只是"看见了硬填之后会发生什么"不同。
- `_MODEL_DRAW_ERROR_GUIDANCE` 新增 `"producer_window_floor_populated"` 词条，专属话术
  （提 `floor`/`floor_id`，不提 `facade_segments`）。

`src/agent/correction/window_host.py`：
- `resolve_window_hosts`（第 721 行原文）：`if floor is None or floor.name != window.floor:`
  拆成两段——`floor is None` 保留（真实可能，floor_id 指向不存在的楼层）；
  `floor.name != window.floor` 半句改成 `assert`（见下方"三处一致性检查"逐条判断）。
- `window_host_claim_issues`（第 529 行原文）：**原样未动**，只加了注释说明为什么不改
  （见下方问题 2 / 三处一致性检查表）。

### 测试改动（隔离性维护，非迁就实现——见问题 3 逐条自查）

- `tests/fixtures/f15_producer_schema_scope/real_crash_draw_north_axis_only.json`：15 个窗口的
  `floor` 字段删除（这份 fixture 建立时 `floor` 是必填字段，现在变成"填了就拒"，且该 fixture 的
  用途是**隔离测 `north_axis`**，留着 `floor` 会在到达 north_axis 检查前先被 floor 检查拦下）。
- `tests/test_f15_producer_schema_scope.py`：
  - 更新对应 fixture 的 docstring 说明新增的一次剥离；
  - `test_guidance_map_covers_exactly_the_three_known_model_draw_error_codes`：3 码改 4 码（新增
    `producer_window_floor_populated`），docstring 同步。
- `tests/test_c2_b2_v3.py::test_finalize_raises_if_core_mutates_window_floor_reference`：手搓
  window dict 里删掉 `"floor": "1F"`（该测试测的是 `floor_id` 篡改，不是 `floor` 合法性）。
- `tests/test_c2_b5_source_routing.py::test_src_c4_producer_resolver_audit_rejected`：
  `_geom().model_dump(mode="json")` 会把已派生的 `floor` 值序列化回原始 dict；该测试要隔离测
  audit-row 拒绝，加一行 `.pop("floor", None)`。
- `tests/test_correction_blind_retry_r3.py::_v3_with_window`：手搓 window dict 删除 `"floor":
  "F1"`（同上，`floor` 现在是派生字段，不该出现在手搓的合法 draw payload 里）。
- `tests/test_f7_observation_reference_translation.py::test_f7_parse_prefilled_raises_in_inner
  _validator_not_outer_classifier`：同 `test_src_c4`，`.pop("floor", None)` 隔离 audit-row 检查。

## 二、锁

新文件 `tests/test_f16_window_floor_derivation.py`，24 条（分 A–I 组，见文件头部 docstring）：

| 组 | 锁什么 |
|---|---|
| A | schema 派生语义：不填→派生正确值；填了且对→放行；填了且错→抛 `ValidationError`（防线分层，见下） |
| B | v1/v2 完全不受影响（`floor` 仍必填、无 marker） |
| C | `floor` 标记的是 `CORRECTION_DRAW_DERIVED` 不是 `CORRECTION_DRAW_FORBIDDEN`；`facade_segment_id` 反向对照 |
| D | 模型可见 JSON Schema 剥除 `floor`；v1 schema 字节不变 |
| E | `parse_correction_draw` 真实拒绝门 + 重试话术 + e2e（真实 `_call_json_llm` 链路一次纠偏成功） |
| F | 双向属性锁（本轮新增 2 条补齐 FORBIDDEN 嵌套路径，见下「N1 缺锁」） |
| G | `_producer_preflight` 不会对已派生的 `floor` 假阳性（本摊设计中最关键的一条回归锁） |
| H | `resolve_window_hosts` 的 floor 不一致分支：真实构造路径下不可达（assert）；构造后手动篡改仍能抓到 |
| I | `window_host_claim_issues` 的 `floor_identity` 检查刻意保留：伪造外部 claims 仍能抓到 |

## 三、neuter 自查表（含一次假锁披露）

**约定**：所有 neuter 均在 `/tmp/f16_neuter`（工作树之外的临时拷贝）做，做完立即 `rm -rf`；
工作树期间 `git diff --stat` 反复确认未被污染。

| # | 摘掉/改回什么 | 预期红 | 实测结果 |
|---|---|---|---|
| 1 | `_v3_integrity` 里 `win.floor = floor.name` 改回 `pass`（不派生） | Group A "derives_from_floor_id" | 红（`geom.windows[0].floor` 仍是 `None`，断言失败）✅真锁 |
| 2 | `vocab.py` 的 `_strip` 只认 `CORRECTION_DRAW_FORBIDDEN`（去掉 `CORRECTION_DRAW_DERIVED` 分支） | Group D "excludes_floor" | 红（`floor` 重新出现在 stripped schema）✅真锁 |
| 3 | **parse.py 里 Step 1 的 `nested_draw_forbidden_fields` 循环改回硬编码** `item.get("facade_segment_id")` | 预期：无（首版设计缺口） | **⛔ 首版 22 条锁全绿，一条没红**——见下「N1」 |
| 4 | parse.py 里 Step 2 的 `nested_draw_derived_fields` 循环整段删除 | Group E 的 4 条 + Group F 的 `test_unmarking_floor_*`、`test_marking_an_ordinary_nested_field_makes_*` | 红，恰好 5 条：`test_parse_rejects_the_actual_historical_crash_value`、`test_parse_rejects_draw_that_supplies_floor_even_when_correct`、`test_unmarking_floor_makes_the_gate_stop_rejecting_it_live`、`test_marking_an_ordinary_nested_field_makes_the_gate_start_rejecting_it_live`、`test_e2e_real_floor_populated_draw_gets_guided_then_recovers`。✅真锁，零多余、零遗漏 |
| 5（补测） | `window_host.py:721` 的 assert 改回 `if floor is None or floor.name != window.floor:`（老代码） | Group H 的 `test_resolve_window_hosts_floor_desync_assertion_fires_if_geom_mutated_post_construction`（改回后仍会走 conflict 分支而非 assert，故此条锁的断言类型会变；已现场确认原代码在 desync 场景下走的是 `_conflict("floor_mismatch")` 不是 AssertionError，两者互斥，锁仍能感知行为差异——未在本表单独复测第二遍是因为它和 #4 类不是同一份诊断，属于逻辑推导而非独立 neuter，如实标注这一条是推导非实测） | 未独立复测（诚实标注） |

### ⛔⛔ N1：额度中断恢复后，orchestrator 独立 neuter 抓到的缺锁（本轮已补）

**现象**：orchestrator 在 `/tmp` 副本里把 Step 1 的 `nested_draw_forbidden_fields` 循环改回
硬编码 `item.get("facade_segment_id") is not None`（也就是 Step 1 要消灭的那份硬编码本尊），
**24 条锁（当时是 22 条）全绿，一条没红**。

**根因**：Group F 当时的两把双向属性锁（`test_unmarking_floor_*`、
`test_marking_an_ordinary_nested_field_makes_the_gate_start_rejecting_it_live`）**全部走
`CORRECTION_DRAW_DERIVED` 那条路**（给 `floor`/`room` 打的都是 DERIVED 标记，命中的是 Step 2
新加的第二条循环）。**没有任何一把锁走 `CORRECTION_DRAW_FORBIDDEN` 的嵌套路径**——Step 1
本身零回归保护：以后谁把它改回硬编码，全仓不会红。这正是本项目反复登记的
「门是真的、锁是缺的」同型（`lock-must-exercise-real-entry-point.md`）。

**修法**：补两条 FORBIDDEN 嵌套路径的双向属性锁，与 Group F 现有两把同形但走
`CORRECTION_DRAW_FORBIDDEN` + 断言 `producer_segment_ref_prefilled`：

- `test_unmarking_facade_segment_id_makes_the_forbidden_gate_stop_rejecting_it_live`——取消
  `WindowV3.facade_segment_id` 的 FORBIDDEN 标记，确认**这个特定类型化门**不再拦它（下游 schema
  仍会用另一个异常类型拒绝——`facade_segment_id` 非空在任何 draw 里都不可能合法，因为它必须引用
  一个真实存在的 `facade_segments` 条目而 draw 阶段该表恒空——所以"解除标记"改变的是"哪个门先
  拦"，不是"这个值突然合法了"；测试用 `pytest.raises(ValidationError, match="unknown
  facade_segment_id")` 精确锁住"变成了另一种拒绝"而非"变成了不拒绝"，如实反映这个字段的特殊性）；
- `test_marking_an_ordinary_nested_field_forbidden_makes_the_gate_start_rejecting_it_live`——给
  `room`（普通未标记字段）打 FORBIDDEN 标记，确认门开始拒绝，且错误码是
  `producer_segment_ref_prefilled`（不是 `producer_window_floor_populated`），证明两种 marker
  各走各的独立循环。

**验收判据（本轮已按要求自己动手复测）**：在 `/tmp/f16_neuter`（全新拷贝）里，把
`nested_draw_forbidden_fields` 循环改回硬编码 `facade_segment_id` 检查，跑
`test_f16_window_floor_derivation.py`：

```
2 failed, 22 passed in 5.91s
FAILED test_unmarking_facade_segment_id_makes_the_forbidden_gate_stop_rejecting_it_live
FAILED test_marking_an_ordinary_nested_field_forbidden_makes_the_gate_start_rejecting_it_live
```

**恰好、只有这两条新锁变红，其余 22 条不受影响**——确认这两把锁是真锁，且未对无关测试引入
collateral。随后确认工作树 `git diff --stat src/agent/correction/parse.py
tests/test_f16_window_floor_derivation.py` 只反映我的合法改动（neuter 拷贝已 `rm -rf`）。

**当前完整锁数**：`test_f16_window_floor_derivation.py` = 24 条（原 22 + 补 2）。

## 四、三个问题的回复

### 问题 1：`CORRECTION_DRAW_DERIVED` 这个新 marker 的判断，你认为对不对？

**你的理解无误，我确认。** 补充我当时排除"复用 `CORRECTION_DRAW_FORBIDDEN`"的具体推导链，
方便你核实我没有偷懒：

1. 若 `floor` 也打 `CORRECTION_DRAW_FORBIDDEN`，它会被 `nested_draw_forbidden_fields` 与
   `facade_segment_id` 一起收进同一个返回值。
2. `_producer_preflight`（`window_sources.py`）拿到的 `producer: CorrectedGeometryV3` 是**已经
   通过 `model_validate` 的实例**——此时 `_v3_integrity` 早就跑完，`floor` 无论模型填没填，**此刻
   必然非 None**（要么是模型填的且校验通过的值，要么是刚被派生填上的值）。
3. 如果 `_producer_preflight` 也无脑遍历 `nested_draw_forbidden_fields` 去检查
   `getattr(item, name) is not None`，`floor` 这一项**对任何合法 v3 draw 都会恒真**——
   等于每一个带窗户的 v3 draw 都会被拒绝，这是会直接把链路打死的假阳性，不是"少覆盖一点"的
   小问题。
4. 我在写 `_producer_preflight` 之前先用一行 Python 验证了这个直觉（`nested_draw_forbidden_fields`
   若把 `floor` 也收进去，`_producer_preflight` 的现有循环形状会立刻踩雷），确认后才决定拆两个
   marker，而不是先写完再被测试炸出来。Group G 的
   `test_producer_preflight_does_not_misfire_on_derived_floor` 就是这条判断的回归锁——它走的是
   `build_verified_window_resolver_inputs` 真实入口（内部调用 `_producer_preflight`），不是直接
   拼一个假实例。

### 问题 2：`envelope_transform.py:324/529`、`window_host.py:689` 为什么没动？

这三处检查的都是 `facade_segment_id`（F-15 的字段），**不是** `floor`（F-16/本摊 Step 2 的字段），
本来就不在本摊改动范围内——这条边界我认可，理由是**用途完全不同、且已用 grep 逐一确认**：

- `window_host.py:689`（`resolve_window_hosts` 函数体最前面）：
  `if any(window.facade_segment_id is not None for window in geom.windows):` ——这是
  `resolve_window_hosts` 自己的入参前置条件："传进来的 geom 不能已经带 facade_segment_id
  绑定"，触发就是 `WindowHostResolutionError(..., fallback_action="invariant_no_geometry_commit")`。
- `envelope_transform.py:324`（`run_envelope_hard_gates`）：
  `binding_ok = not candidate.facade_segments and all(w.facade_segment_id is None for w in
  candidate.windows)` ——B2b 信封变换后的候选几何必须还没有 Vg 绑定，这是"变换阶段结束时"的
  硬门，一个独立的 `EnvelopeGateFinding("correction.facade_segment_binding", ...)`。
- `envelope_transform.py:529`（`apply_v3_envelope_transaction`）：
  `if before.facade_segments or any(w.facade_segment_id is not None for w in before.windows):
  raise EnvelopeTransformRejected(...)` ——B2b 事务**开始前**的前置条件，"已经做过 Vg 绑定的
  geometry 不能再进入信封变换"。

三处共同点：都在检查 `facade_segment_id`（F-15 的字段），且都是**某个处理阶段自己的前置/后置
不变量**（"这一步开始/结束时，绑定字段必须还是空的"），跟"模型在 draw 时是否非法填了这个字段"
是两件事——即使 Step 1 把 `_producer_preflight`/`parse.py` 的检测机制换成读标记，这三处依然要
保留各自的硬编码检查，因为它们检查的不是"model_draw_error"意义上的"模型填错了"，而是"内核自己
的处理顺序有没有被破坏"（比如"信封变换不该在 Vg 绑定之后跑"这种阶段顺序错误，追责对象是代码
逻辑而不是模型）。把它们也改成读标记会把两种性质不同的检查混到一起，且这三处根本不涉及
`floor`，本摊没有理由碰它们。

### 问题 3：5 个测试文件 + 1 个 fixture 的改动，有没有更接近"迁就"的？

逐条自查（判据：改动是否让测试**继续检验它原本要检验的东西**，还是让测试**换了个更容易过的
断言**）：

- `real_crash_draw_north_axis_only.json` + 其 docstring：删的是 `floor` 字段（现在是派生字段，
  `floor` 值本身不影响这份 fixture 要测的 north_axis 隔离性）。**判定：隔离性维护。**
  反证：如果我是在"迁就"，应该会去改这份 fixture 里 `north_axis` 相关的内容让断言更容易过——
  我没有碰任何一处 `north_axis` 字段。
- `test_c2_b2_v3.py`：该测试的断言是 `pytest.raises(ValueError, match="source_identity_invalid")`，
  跟 `floor` 的值毫无关系（测的是 `floor_id` 篡改后 finalize 是否拦截）。删掉 `"floor": "1F"`
  前后，这条断言的检验对象（`source_identity_invalid`）完全没变。**判定：隔离性维护。**
- `test_c2_b5_source_routing.py::test_src_c4`、`test_f7_observation_reference_translation.py`
  的对应测试：断言分别是 `match="producer_resolver_audit_prefilled"`，检验对象是"audit row 被
  拒绝"，跟 `floor` 无关。`.pop("floor", None)` 只是防止一个**不相关的、更早触发的**门抢先命中，
  没有改变原始断言想验证的内容。**判定：隔离性维护。**
- `test_correction_blind_retry_r3.py::_v3_with_window`：这个 helper 被
  `test_f4a_semantic_valueerror_retries_blind` 使用，断言是"语义 ValueError 必须走盲重试、不能
  附加纠错提示"（`len(second) == 2`）。删掉 `"floor": "F1"` 前，这份手搓 payload 会先被我的新
  `floor` 门拦下（返回一个 `model_draw_error`，**附带**纠错提示），而不是走到该测试真正想测的
  "语义校验失败"（0 窗但 reading 有窗）分支——**如果不删，测试会因为一个完全不相关的原因失败，
  而不是因为它自己要测的机制坏了**。删掉后测试重新回到"只测语义 ValueError"这一条路径。
  **判定：隔离性维护，且是必须改（不改就是我的新功能误伤了老测试的隔离性）。**

**没有一处是"迁就"**——迁就的定义是"把断言改弱/改错让实现蒙混过关"，而我这五处改动都是
**移除一个跟被测机制无关、但因为 `floor` 现在有了新语义而意外触发的门**，被测的核心断言
（错误码、异常类型、match 文本）**一个字没改**。

## 五、全仓实际数字

**中间轮**（Step 1+2 落地后，未加专属锁前）：
`python -m pytest tests/ -q -n auto` → **2299 passed, 10 xfailed, 0 failed**（358.61s）。

**加完 `test_f16_window_floor_derivation.py`（含本轮补的 2 条）之后本地未再单独跑一次全仓**——
orchestrator 已代跑独立全量并逐项对账：

> 独立全量（主树）= **2321 passed / 10 xfailed / 0 failed**，
> 逐项对账：基线 2289 + 另一席（摊二/摊三）10 + 我的 22 = 2321，零回归。

本轮新增 2 条锁后，`test_f16_window_floor_derivation.py` 单文件 = 24 passed（已本地跑过，见上）；
`test_f15_producer_schema_scope.py` + `test_f16_window_floor_derivation.py` 合跑 = 44 passed。
未再触发全仓（orchestrator 的独立全量口径优先，且本轮只新增两个纯新增测试函数、不改动任何
生产代码，回归面为零）。

## 六、其余边界问题（派工单薄弱处自查，第一轮已作答，此处保留存档）

1. **Step 1 接口形状**：新增函数（`nested_draw_forbidden_fields`），没有走递归化现有函数——
   理由见第一节，属已解决、未触发停工。
2. **`floor` 改非必填的 pydantic 校验顺序**：已实测确认无问题——子类覆写字段类型/默认值时，
   父类必填约束不会渗透到子类（用一个最小 `Base`/`Sub` pydantic 模型直接验证过，见施工过程记录），
   `WindowV3.floor` 变成真正可选，v1 的 `Window.floor` 保持必填,两者互不干扰。
3. **三处一致性检查是否真的都恒真**：**不是全部**——`window_host.py:529`
   （`window_host_claim_issues` 里的 `floor_identity`）**不是恒真**，已在第一轮当场发现并停下
   确认（不是事后猜的）：它比对的是 `resolution.floor_id`（来自外部、不可信的 `claims` 载荷）
   而不是 `window.floor_id`，一份伪造的 `claims` 完全可能让 `resolution.floor_id` 指向一个真实
   存在但名字不同的楼层——这与 `floor` 的 schema 派生毫无关系,该检查是这份"未受信任审计"函数
   本身要做的事，**原样保留，未改动**（对应 Group I 的锁,已实测伪造 claims 场景下它确实还会
   触发）。另外两处（`schema.py:302`、`window_host.py:721`）在真实构造路径下确认恒真，
   已分别改成派生逻辑与 `assert`。
