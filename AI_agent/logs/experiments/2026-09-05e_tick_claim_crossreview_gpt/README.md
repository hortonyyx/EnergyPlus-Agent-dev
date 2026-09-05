# 刻度认领返工 1 · GPT 独立复核证据

被审对象固定为 `dc886036`；当前主线只通过 `git show b4f0b348:<path>` 读取，未切树、未合并。全部探针只读原料与代码，不改 `src/`、`tests/` 或 site-packages。任务书在工作树内预置为 untracked，未由本席提交。

命令（在 `/tmp/tickrw1_review_gpt` 执行；各命令 exit 0）：

```sh
python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py statistics
python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py counterexamples
PYTHONDONTWRITEBYTECODE=1 python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py arithmetic
python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/probe.py numbers
python3 AI_agent/logs/experiments/2026-09-05e_tick_claim_crossreview_gpt/capture_evidence.py
```

对应输出为同名 `.txt` 与 `evidence.md`。`statistics` 全扫 68 边；签名只比较段名，**多链值是否相同则独立读取各 cfg 链，以 Decimal 前缀和精确比较**。这是额外的源依赖，不能冒称仅从扁平 witness 表就证实多链同指。

`counterexamples` 的最近刻度部分执行仓库实际 `_nearest` 函数（AST 提取，避免加载图像流水线）；段名分流是对稿中 D5 的直译。后半的 D2/D4/D6 行是**构造性契约分析的输入与结论记录**，不是不存在的拟议校验器的运行输出。`arithmetic` 才实际调用当前树的链闭合门、整数转换器和 ArtifactPointer 类型，打印导入路径。没有运行拟议 schema、B2 在飞实现、pytest 或端到端流程。

`numbers` 列出全部 170 个数字 token / 948 次出现及每次行号。表外 token 只是机械覆盖检查；定位符类可按类别涵盖，是否属于遗漏需结合正文语义裁定。

分段提交：先提交本目录的独立证据；后提交正式裁决。最终结论以裁决书为准。
