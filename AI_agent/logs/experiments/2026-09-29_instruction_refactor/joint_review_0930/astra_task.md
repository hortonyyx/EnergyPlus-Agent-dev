（执行环境说明：本次只读沙箱改用 Landlock，读文件、git 查看、python 读取均可用；写文件会被拒绝，这是预期的。上一次尝试因沙箱无法启动未读到任何内容，已作废。）

你是 Astra（GPT-6 Astra，本次为 max 推理档），本项目两位最高档开发负责人之一。用户今天的安排原话：「按计划，先你和Astra最高分别独立审查一遍重构，然后你跟它讨论完之后给我汇报，我拍板之后执行」（“你”指 Opus 5.5）。本任务是其中你的**独立审查**：Opus 正同时独立审查，你看不到它这次的结论，它也看不到你的；两份完成后再讨论，最终由用户拍板。

## 审查对象

分支 `dev/opus-guidance-recovery-20260929`（即本工作树）上的“指令层重构第一版”，主要是提交 `d3831882`：改写给工作模型（Sonnet 5）的全部文字——系统提示、图纸做法、参考、工具说明、冷启动入口句、任务提示。按用户要求，审查对象是**重构实现本身**（写法、取舍、是否落实用户的重构决定、有无改错/漏改/矛盾），不只是 run94 的结果。

重构实现当时在较低推理档完成，之后在 max 档做过一次“整体复查”（实验 README 的“整体复查”一节，A1–A6、B1–B7、C）。那份复查是 Opus 上一轮写的：请把它当作**待核的主张**，逐条用原始证据核实或推翻，不要照抄结论。

## 背景（开工先读）

- `AI_agent/Agent.md`（项目入口与约定）；`AI_agent/project/goal.md` 的“当前优先级”；`AI_agent/project/decisions.md` 表格前两行（09-29 两条用户决定）。
- 两份交接：`AI_agent/logs/worklog/2026-09-29_opus_regression_diagnosis_close.md`（回退主因、用户“整体重构指令层”的决定和“改一处写明针对的失败、替换不追加”的规矩）；`AI_agent/logs/worklog/2026-09-29_opus_instruction_refactor_review_close.md`（第一版、run94、本轮建议讨论点）。
- 实验记录：`AI_agent/logs/experiments/2026-09-29_instruction_refactor/README.md`；`AI_agent/logs/experiments/2026-09-29_whole_drawing_guidance/README.md`（run91–93 与回退诊断证据）。

## 代码与版本基准（用 `git show <commit>:<path>`、`git diff` 对照）

- 重构后（本工作树 HEAD）：`scripts/tool_scripts/bim_agent_guidance.py`、`scripts/tool_scripts/run_bim_agent.py`（系统提示组装、入口句、工具说明）、`scripts/tool_scripts/bim_agent_continuation.py`（续查提示）、`tests/test_bim_agent_guidance.py`；分支还改了 `src/agent/geometry/plan_feedback.py`（方向镜像报告）。
- 重构前 = run93 所用代码：`31e6ee5d`（scripts/src/tests 与 `47f74c04` 完全相同）。
- 当前 main：`0e918a5a`（分支之前的 main 指令，run69–90 时期）。
- 好结果时期旧生产树：`468d83f7`（run81 以逐字节相同请求复跑该树也退步）。好结果运行 run53–58 的确切代码版本请从各自运行目录的记录核对。

## 运行证据（均为已有产物，只读）

- run94（重构后）：`AI_agent/logs/experiments/2026-09-29_sm21_instruction_refactor_run94/`——`agent_request.json`（实际系统提示/用户提示/工具定义）、`agent_stream.jsonl.gz`（完整对话，含每次工具调用与返回）、`tools.jsonl`、`plan_drafts/`、`claims/`、`whole_drawing_evaluation.json`、`postrun_audit.json`、`images/`（原图）。
- run93（重构前，对齐提示）：`.../2026-09-29_sm21_aligned_prompt_run93/`；run91：`.../2026-09-29_sm21_whole_drawing_run91/`。
- 好结果：`.../2026-09-26_sm21_whole_building_claude_run57/`、`.../2026-09-27_sm21_whole_building_repeat_claude_run58/`；另有 sm24 run55/56、sm25 run53/54。
- 退步期错误稿：run75/83/86 等（目录名见 `AI_agent/logs/experiments/`）。
- 原图复核截图：`AI_agent/logs/experiments/2026-09-29_instruction_refactor/run94_review_*.png`。

## 请回答（每条给证据位置：文件+行号，或 run 对话中的工具调用序号/时间）

1. 重构是否落实了用户 09-29 的决定（按好结果做法整体重构指令/流程层；工具与几何内核不动；每处写明针对的失败；替换不追加；默认读取量低于好结果时期）？哪里做到了，哪里偏了。
2. 逐条核“整体复查”的 A1–A6、B1–B7 与 C：成立 / 不成立 / 部分成立，理由。特别核：run94 的主要失误是否确由所指的那几句写法造成，还是另有原因（看图方式、裁图大小、工具返回、任务提示、模型本身等）。
3. 复查漏掉或说错的问题：重构中意外删掉或改变的有效内容、新旧矛盾、工具说明与工具返回文字里的流程指令、任务提示/入口句/续查提示、与好结果时期指令的实质差异。对照好结果运行（run57/58）模型实际做了什么、读了哪些文字，与 run94 比较。
4. 修正版应该怎么写：按优先级列具体修改（针对哪条失败、替换哪段文字、改成什么意思），以及明确不要动的地方。
5. “检查量具化”两项（图上画了、两端接墙、但声明里没有的双线隔墙；墙上断口/填充中断与声明门窗不符）：可行性、误报风险、用 run75/83/86/91/93/94 错误稿与 run57/58 好稿离线验证的方案；应作为本轮修复的一部分，还是先只修文字。
6. B1–B3（工具返回瘦身、说明书压量、按场景挂载工具）的优先级，是否作为本轮质量修复的前置。
7. 回归方案（案例、次数、判据、批次顺序）与分支合入 main 的时机。
8. 需要用户拍板的事项，并给出你的建议。

## 约束

- 只读审查：不改任何文件、不提交、不推送、不切分支。沙箱为只读；可以运行只读命令和 python 脚本读取、统计（结果输出到终端，不写文件）。
- 不运行 BIM Agent，不调用任何模型（Claude/Sonnet/GLM/DeepSeek/Paratera 等）；DeepSeek 任何调用需用户事先明确同意，本任务未获同意。不跑 pytest（会写缓存）。
- 不需要子代理；如确实使用，写明型号与范围。
- 不必寻找 Opus 本轮的审查，它不在仓库里。

## 交付

最终回复就是审查报告（中文；Opus 会原样存档，并与自己的审查对照讨论）：

- 开头 5–10 行结论摘要；
- 按上面 1–8 分节；每条区分“已核事实（附证据位置）”和“判断/建议”；
- 结尾列出你与现有“整体复查”意见不同之处，以及你没能核实的内容。
