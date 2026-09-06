# A-6 工程档证据（2026-09-05，GPT）

工作目录 `/tmp/a6_tickclaim_astra`，基点 `2a51d7fd`。本目录是工程验证，不是 sm25 成绩；模型响应是明确的诊断 fixture，不冒称图像判断。最终全量读数见交件及 `full_suite.txt` 的末尾/退出码。

## 实际执行命令

```sh
python AI_agent/logs/experiments/2026-09-05j_A6_tick_claim/capture_legacy.py
python AI_agent/logs/experiments/2026-09-05j_A6_tick_claim/probe_after.py
python -c "import src.agent.correction.tick_claim as m; print(m.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider tests/test_tick_claim_a6.py tests/test_opening_adjudication_a6.py
python -c "import src.agent.correction.tick_claim as m; print(m.__file__); import src.agent.correction.opening_adjudication as a; print(a.__file__)" && python -m pytest -q -n 6 -p no:cacheprovider
```

`capture_legacy.py` 载入原 capture 的命令定义并逐条执行，只把输出写入本目录；命令表没有改写。保留旧 probe 的 `SPEC/ACTUAL` 区分。旧脚本仍然诊断旧设计，因此旧错误继续出现是预期现象，不拿旧脚本的 exit0 冒充新实现闭合。

## 文件

- `legacy_2026-09-05e.md` / `legacy_2026-09-05h.md`：原命令与未经编辑输出；包括旧统计、counterexamples、arithmetic、D6 工厂和原型 `_nearest` 实际执行。
- `legacy_*_numbers.txt`：分别扫描原来的两份设计稿，不充当本稿数字自查。
- `legacy_capture_run.txt`：capture 命令组退出码；negative rg 结果原样保留。
- `probe_after.py` / `probe_after.txt`：在最终 A6 API 上的反例及具名出口，源数据、诊断模型选择与结果均可重跑。
- `mutable_inputs_before.txt`：`b7be6a29` 上实际发现的 list 别名问题；修后同形输入见 probe_after 末段。
- `enforcement_lines.txt`：最终强制函数/行号索引。契约正文另有逐条链接。
- `full_suite_c4b16824.txt` / `full_suite_6242672d.txt` / `full_suite_b7be6a29.txt`：三个已完成的中间代码版本全量，分别为3874/3875/3876 passed；不是最终版本冒领旧读数。
- `full_suite.txt`：最终代码版本的完整 pytest 原文。

## 旧反例 → 新实现证据索引

| 原反例/类别 | 新输出标签或测试 |
|---|---|
| B-1 非节点合法派生、2550/3450 | ORIGINAL_B1_CENTER…；AXIS…；test_original_center_and_declared_width_derive_non_nodes |
| 同节点塌缩、反向节点 | INTERVAL_CHOICE → RETURN_TO_STEP_ONE_INTERVAL |
| East O01、中点/最近邻、原点误降档、620/870、176/254 | OLD_NEAREST_INPUT / ACTUAL_NEW_ROUTE / EAST_O01_MODEL_PIXEL；所有未裁定输入拒绝提前取事实 |
| South 主链内虚构17970边 | 候选不是事实的同一 SAME_IMAGE_MODEL_REQUIRED 入口；68条x边全部送第一步模型，无任何候选自动定案分支 |
| 4700/4900；4200同值异链；4000/4050；2600/5200碰主链另一节点 | COLLISION 两种覆盖顺序，独立链身份保留 |
| South四边、West两边缺地址 | OLD_SIX_NONPRIMARY_EDGE；真实cfg补证后为可寻址候选，未补证时走显式债 |
| 中间7000污染、重复5000、新2450污染、零段/负段/短cum非零起点 | CHAIN → 相应前缀/域错误 |
| node1+node2=5900伪段长 | NODE_SUM_1600_PLUS_4300_AS_SEGMENTS → OPERAND_REF_DOMAIN；合法段和43000u |
| 差值2700冒充位置4300 | ANCHORED_DIFF… →43000u；原点是显式anchor |
| 4000/8000内侧符号、3600/7600新内侧、全厚/半厚201/202 | AXIS… / FULL_WALL_UNITS… |
| 4200配低档115半厚、跨图测量墙厚、错轴 | MEASURED_WALL_NOT_DECLARATION / CROSS_IMAGE_REF / WRONG_AXIS_REF |
| 有向 -400/100 | NEGATIVE_OR_POSITIVE_DISPLACEMENT_WITH_EXPLICIT_ORIGIN |
| tuple遗漏边、遗漏整图输入 | TRUNCATED_DECISION_UNIVERSE / TRUNCATED_REVIEW_INPUT / MISSING_FACADE_AVAILABILITY |
| 嵌套指针/档位替换、重新finalize、两个有效批次 | REFINALIZED… / TWO_VALID_BATCHES_SAME_SOURCE / VALID_ALTERNATE_BATCH_REJECTED |
| obligation=None 无人兑现 | 原实际API仍 redeemed=()；新增 OWNED_DEBT_BEFORE / AFTER_SUPPLEMENT_RECLAIM_RETIRED 展示本单拥有的闭环 |
| 整体审查推翻、旧响应/旧结果复活 | OLD_BATCH_AFTER_RETURN… / OLD_RESPONSE_AFTER_RETURN… / SPATIAL_RESULT_AFTER_RECONSIDERATION |
| 一档1935与10mm出口 | CHAIN_IMMUNE 1935 →19350u（另有2473不同输入） |
| ②b没有立面洞口行、③没有立面图 | FOUR_CLASSES：②b无几何，③inferred且score_eligible=False；SCOREABLE_COUNT=2 |
| **本轮两条全新同形碰撞** 1800/3600 @318.5 与2150/6450 @407.2 | COLLISION，均独立保留P/Q节点，不随扁平表写序替换 |
| 本轮补证失败状态与普通可变序列 | FAILED_SUPPLEMENT… / AFTER_FIX_MUTABLE…；修前原文单独保存 |

边界：以上验证计算、引用、状态和消费约束；不证明真实图纸上的某个候选在视觉语义上正确。不运行 gt 晋升、不重新签字、不修改既有 B4/T4-a/判分器。
