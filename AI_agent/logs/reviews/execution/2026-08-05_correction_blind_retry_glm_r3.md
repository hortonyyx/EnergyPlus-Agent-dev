# 施工简报 · correction 盲重试 r3（承接 fb78e74）

- **日期**：2026-08-05
- **施工席**：GLM-5.2（承接 `4a11097 → fb78e74` 同一席位）
- **派工单**：`AI_agent/logs/reviews/request/2026-08-05_correction_blind_retry_dispatch_r3.md`
- **基线**：工作树 @ `fb78e74` = **2170 / 10 / 0**（当前工作树 `git stash` 我的 4 文件后独立复算，与 r2 简报逐字一致——非抄录）
- **收工三数字**：**2177 passed / 10 xfailed / 0 failed**（净增 7 锁，零回归）

---

## 0. 一句话

F-4a（重试回灌校验错误）+ F-4b（词表机械导出进 prompt）都按派工单施工；回灌**严格限定 schema 格式类**
（字段路径 + 合法词表），transport / semantic / JSON 三类仍盲重试；词表单一来源机械导出，未手抄第二份。
7 锁 + 5 条 neuter 全部「摘掉即红」且判据有分辨力（每条 neuter 红目标锁、其他绿，证明非恒真）。

---

## 1. 逐条改了什么

### F-4a · 内层重试把校验器的报错带回模型（仅格式类）

`src/agent/pipeline.py` `_call_json_llm` 加可选参数 `retry_guidance: Callable[[BaseException], str | None] | None`：

- 重试时，**仅当拿到模型响应**（`content` 非空——意味着 `create()` 成功返回、是解析/校验失败而非网络）
  **且** `retry_guidance` 把异常翻译成纠正消息时，才在下次 attempt 的 messages 末尾追加一条 user 角色纠正消息。
- **双重门**：(a) `_call_json_llm` 的 `content.strip()` 判断 = transport vs 拿到响应；(b) `retry_guidance` 的
  `isinstance(exc, ValidationError)` 判断 = schema vs 其他。任一门不通过 ⇒ 盲重试。
- 纠正消息只含**字段路径 + 校验器错因 + 该字段的合法词表**（从 schema 机械导出），⛔ 不含几何、上游内容、gt、
  或上一版模型的具体数值（格A 负断言 `"[0.0, 4.0]" not in guidance`）。
- `run_correction` 把 `retry_guidance_for_correction(target)` 传进去；`run_mep` 不传（仍盲重试，符合「只修 correction」）。

### F-4b · 合法词表机械导出进 system prompt（单一来源）

新建 `src/agent/correction/vocab.py`，F-4a 与 F-4b 共用、⛔ 不手抄第二份：

- `window_provenance_vocabulary()` = `sorted(WINDOW_CLAIMS)`（opening-claim 词表，权威源在 `claims.py`）；
- `north_axis_allowed_fields()` = `sorted(NorthAxisEvidence.model_fields)`（pydantic 字段声明）；
- `correction_schema_vocabulary(target)`：v3 才有这两项（`issubclass(schema_model, CorrectedGeometryV3)`），
  v1（rectangular）返回空 ⇒ v1 prompt 字节不变；
- `format_correction_system_vocabulary(target)`：产出 system prompt 的 `ALLOWED VOCABULARY` 块（v1 空串），
  插在 `_build_correction_messages` 的 schema 块之后；
- `retry_guidance_for_correction(target)`：F-4a 闭包，复用同一导出，按出错字段的 loc 附对应词表
  （window provenance / north_axis fields）。

---

## 2. 新锁（7 条，文件 `tests/test_correction_blind_retry_r3.py`）

| 锁 | 分格 / 载荷 | neuter 摘掉后红了哪条 |
|---|---|---|
| `test_f4a_schema_failure_appends_field_path_guidance` | **格A**：第一抽 `north_axis.note` extra_forbidden（真 pydantic ValidationError）⇒ 第二次 messages 多第三条、含 `field path: north_axis.note` + north_axis 合法字段 + 不含几何 `[0.0,4.0]` | N1 红（drop guidance append）✅ |
| `test_f4a_transport_failure_retries_blind` | **格B**：第一抽 ConnectionError ⇒ 第二次 messages 仍 2 条 **且** spy 证 retry_guidance 根本未被调用 | N2 红（drop content gate）✅ |
| `test_f4a_semantic_valueerror_retries_blind` | 第三路：0-window semantic ValueError（content 非空）⇒ 第二次 messages 仍 2 条（predicate 返回 None） | N3 红（widen predicate）✅ |
| `test_f4a_retry_guidance_is_schema_only` | predicate 直测：ValidationError⇒非None 含路径；ConnectionError/ValueError/JSONDecodeError⇒None | N3 红 ✅ |
| `test_f4b_system_prompt_vocabulary_equals_schema_derivation` | v3 prompt 的 ALLOWED VOCABULARY 块 token 集合 == 直接 schema 源（`WINDOW_CLAIMS`/`NorthAxisEvidence.model_fields`）逐元素相等 | N4+N5 红 ✅ |
| `test_f4b_v1_prompt_has_no_vocabulary_block` | v1（rectangular）prompt 无词表块（字节不变） | （守 v1 不退化）|
| `test_f4b_vocab_helpers_derive_from_schema_sources` | vocab helper == schema 源（`sorted(WINDOW_CLAIMS)`/`sorted(model_fields)`） | N4 红 ✅ |

**判据分辨力**（08-04 教训：neuter 红只证明实现被调用）：每条 neuter 红目标锁、其他绿，证明判据非恒真——

- N1 红格A 但格B/semantic 绿 ⇒ 「schema 回灌」与「不回灌」方向可分；
- N2 红格B 但格A 绿 ⇒ 「transport 不调 guidance」与「schema 调 guidance」可分；
- N3 红 semantic+predicate 但格A/格B 绿 ⇒ schema vs semantic/transport 的 predicate 可分；
- N4 红词表锁但格A/格B 绿 ⇒ 词表判据可分。

载荷均为真形（结构完整 v3 payload 过 `CorrectedGeometryV3.model_validate` + b2 contract；schema 失败用真
pydantic ValidationError，非 mock；格B/格A 共用同一 retry_guidance，唯一变量 = 失败类型）。

---

## 3. neuter 原始输出（自跑，全部改源文件→跑→复原，POST-RESTORE 7 绿）

```
N1 (if guidance_text: → if False and guidance_text:)        : 红 1  test_f4a_schema_failure_appends_field_path_guidance
N2 (去掉 `and content.strip()`)                              : 红 1  test_f4a_transport_failure_retries_blind (spy: guidance_calls==[] 失败)
N3 (predicate 放宽到 ValueError + getattr 防 errors() 崩)    : 红 2  test_f4a_semantic_valueerror_retries_blind + test_f4a_retry_guidance_is_schema_only
N4 (window_provenance_vocabulary 手抄缺 sill/width)          : 红 2  test_f4b_system_prompt_* + test_f4b_vocab_helpers_*
N5 (system prompt 词表块 format → "")                        : 红 1  test_f4b_system_prompt_vocabulary_equals_schema_derivation
POST-RESTORE : 7 passed
```

每条 neuter 恰好红目标锁（N3/N4 各红 2 条是预期：一个机制点被两把锁交叉绑），零意外连带。

---

## 4. 全仓三数字

```
python -m pytest -q -n auto
2177 passed, 10 xfailed, 209 warnings in 391.80s
```

**2177 / 10 / 0**。基线 `fb78e74` = **2170 / 10 / 0**（当前工作树 `git stash` 我的 4 文件后复算，与 r2 简报逐字一致），
+7 新锁 = 2177，xfail 不变，**零回归**。

⚠️ **基线复算的方法学披露**：先尝试 `git worktree` 跑干净 `fb78e74` checkout，得 2157 passed / **5 failed** /
8 skipped——这 5 failed（`test_gt_from_dxf` 用 sm25-L candidate、`real_restore`/`reading_score` 用真 run 产物、
`ep_clean`）全是**测试依赖未跟踪资源**（`sm25-L_anchor/` / `run_2026-08-04_*`，本项目老问题：活输入不在 git 里），
干净 checkout 缺它们即红，**与 fb78e74 真实状态、与我的改动均无关**。改在当前工作树（含这些资源）`stash` 我的
改动复算 ⇒ 2170/10/0，可信。

---

## 5. ⚠️ 诚实披露

### 5.1 连带修了一个接口 fake（必要）

`tests/test_pipeline_evidence_debt_import.py` 的 `fake_call_json_llm` 用**显式 kwargs 钉接口**（证明调用方传了哪些 kwarg）。
`_call_json_llm` 加 `retry_guidance` 后 `run_correction` 传它，fake 不接受 ⇒ TypeError（首跑全仓即撞，已修）。
给 fake 加 `retry_guidance=None` 跟进新 kwarg，保持「显式钉接口」风格（顺带证明 run_correction 确实传了
retry_guidance）。这是接口变更的必要连带，非范围扩张。

### 5.2 retry_guidance 的 vocab 在闭包创建时固定

`retry_guidance_for_correction(target)` 在构造时算一次 `correction_schema_vocabulary(target)` 缓存进闭包。
target 在一次 run 内固定、schema model 静态 ⇒ 是缓存非陈旧风险。若未来 schema 运行时可变需改每次调用重算（当前无此需求）。

### 5.3 没放宽 schema、没碰判卷语义

`CorrectedGeometryV3` schema 一字节未动；修的是「怎么告诉模型合法词表 / 错在哪」，不是「把门开大」。
未碰识图侧、gt、typed v3 判卷。`run_mep` 仍盲重试（派工单只点名 correction）。

### 5.4 guidance 内容边界

格A 负断言 `"[0.0, 4.0]" not in guidance`（不回灌几何坐标）+ 正断言 `"FORMAT error" in guidance`（措辞锚定）。
retry_guidance 只取 pydantic err 的 `loc` + `msg`，**不取 `input` 字段**（input 含被拒 draw 的具体值，禁回灌）。

---

## 6. 边界

⛔ 未碰识图算法 / 未碰 gt / 未碰 typed v3 判卷语义 / 未动容差 / 未放宽 `CorrectedGeometryV3` schema。
`git diff --name-only` = `pipeline.py` + `correction/vocab.py`（新）+ `test_correction_blind_retry_r3.py`（新）+
`test_pipeline_evidence_debt_import.py`（fake 跟进）+ 本简报。提交**只 add 这 5 个**，⛔ 未 `git add -A`：
orchestrator 的未跟踪产物（`sm25-L_anchor/`、`run_2026-08-04/05_*`、前两单 request/verdict、本派工单）一律留在外。
