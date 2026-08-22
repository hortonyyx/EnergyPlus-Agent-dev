# 跨家族复核请求 · 判卷路径三缺陷修复（2026-08-22）

**审阅席位**：GLM（glm-5.3）· **施工席位**：Claude 主控（orchestrator）
**规约**：谁写谁不批 —— 本批由主控施工，故必须跨家族审。
⛔ **只看原始需求 + diff + 测试输出**，不看施工方的长篇自述。

**提交**：`19932a2` （父 `2156989`）
**diff**：`git diff 2156989..19932a2 -- scripts/ src/ tests/`
**全量**：`2994 passed, 13 xfailed`（修改前 2946 passed, 13 xfailed）

---

## 一、原始需求（施工前就成立的事实，⛔ 不是施工方的结论）

一份**合法的** 0_reading 产物，如果不是经隔离壳 merge 产生、而是直接写在
`0_reading/*_view.json`（"flat-flow"，仓库里明确支持的第二种形态），会出现三件事：

1. 该 run 即使在 `run_config.yaml` 里**合法声明**只考其中两张图（`reading_exam_scope`，
   且该声明已被冻结进 `_run/reading_exam_scope.json`），gate① 的
   `reading.view_manifest_coverage` 仍按**全部六张图**要求它 ⇒ **必然 BLOCK**。
   同一份声明经隔离壳 merge 路径则被正确尊重。
2. 权威 typed 判卷层返回 `kind: not_applicable / reason: unsupported_reading_contract`，
   **静默跳过判分**，而 gate① 照常报告。
3. `scripts/tool_scripts/score_reading_vs_gt.py` 对该产物报
   `could not map image to a gt floor; pass --floor`，而真实异常是
   `gt_v3_requires_typed_consumer`（legacy 判卷器根本读不了 v3 答案）。

⇒ 合起来：**当前没有任何一条可用命令能给 flat-flow 产物判分。**

**复现（施工前的 HEAD = `2d13ff5`）**：
```
git stash && git checkout 2d13ff5   # 或直接读 2156989 的 attempts/001/score_vs_gt.json
python scripts/tool_scripts/run_stage.py --base-dir case_tests/e2e_tests \
  flow sm25-L_anchor run_2026-08-22_orchestrator_handson_H1 --to 0_reading --judge stop
```

## 二、施工方声称的修法（**请独立判断是否成立**）

| 编号 | 改哪 | 声称的修法 |
|---|---|---|
| F-74 | `scripts/tool_scripts/run_stage.py:_draw_reading` · `src/agent/execution/validation_run.py` | 两处调用点补传 `resolve_frozen_reading_exam_scope(...)` 的结果；范围解析失败按 manifest 失败处理（响亮红），⛔ 不静默回退全量 |
| F-75 | `scripts/tool_scripts/run_stage.py` | 新增 `_as_reading_views_envelope`，在判卷入口把 flat 产物呈现为 v2 信封；声称是既有 `_unwrap_reading_views_envelope`（信封→flat，给 legacy 判卷器）的**精确镜像** |
| F-76 | `scripts/tool_scripts/score_reading_vs_gt.py` | 只在异常确实是 floor mapping 时给 `--floor` 提示，否则按原样报出真异常 |

## 三、⭐ 请重点证伪的五条（施工方自认的薄弱处）

1. **F-75 会不会把「错的产物洗白」？** 施工方声称：`output.json` 的字节与
   `output_hash` 取自文件本身、未被改动，故归一化只是**呈现**，不改身份。
   **请独立验证**：`product_identity` / `source_output_sha256` 是否确实仍绑定原始文件字节？
   有没有路径能让一份**不该被判分**的产物因此被判分？
2. **F-75 的包裹条件是否过宽？** 现条件 = 「dict 且每个 value 都是 dict」。
   仓库里有没有**非 reading** 的产物满足这个形状、因而被误包？（施工方查过 1_correction 走另一分支，
   但**没有穷举**其它 stage。）
3. **F-74 会不会把覆盖检查关掉而不是缩小？** 施工方加了一条反向锁
   （`test_flat_flow_still_blocks_a_view_missing_from_inside_the_declared_scope`）声称能证伪。
   **请判断该锁是否真的能分开「缩小范围」与「关掉检查」**；若不能，请指出并给出更强的锁。
4. **`check_view_manifest_merge` 全仓零生产调用者**（施工方发现但未处理）。
   它与 `check_reading_stage` 的关系是否意味着还有第三条入口也没传范围？
5. **F-76 的分支判据用的是 `str(exc) == "floor mapping"`（字符串比较）**。
   这是施工方能想到的最小改动，但它把一个内部约定钉成了字符串。**请判断是否可接受**，
   不可接受请给出替代（如自定义异常类型）。

## 四、必须实测的三件（⛔ 不接受「读代码看起来对」）

1. **neuter 实测**：分别摘掉 F-74 与 F-75 的**接线**（不是 helper），确认对应锁变红。
   ⚠️ 施工方在这里犯过一次：F-75 的第一版锁只测 helper、**摘掉接线仍全绿**，已重写；
   **请重新独立验证重写后的锁确实咬住接线**。
2. **全量**：主树独立跑一次 `python -m pytest -q -n auto`，与声称的 `2994 passed / 13 xfailed` 对账。
3. **端到端**：跑一次
   `run_stage.py --base-dir case_tests/e2e_tests flow sm25-L_anchor run_2026-08-22_orchestrator_handson_H1 --to 0_reading --judge stop`，
   确认 gate① `block=0`、`attempts/001/score_vs_gt.json` 的 `payload.kind == "c2_scored"`。

## 五、裁决格式

写入 `AI_agent/logs/reviews/verdict/2026-08-22_scoring_path_glm_verdict.md`，含：
`APPROVE / REWORK / BLOCK` + 逐条（BLOCKER / MAJOR / MINOR）+ 每条附**实测命令与输出**。
⛔ 没有实测输出的条目按 MINOR 计。
