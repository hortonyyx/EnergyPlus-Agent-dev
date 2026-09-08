---
name: contamination-hard-isolation-requirement
description: 污染硬隔离已机制化落地（2026-07-08）：clean-room staging + settings/guard 双层强制 + 审计留痕；老 prompt 级协议废弃
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d1f583bf-388f-45a5-b5a9-59b134d10653
---

2026-06-23 用户定：**0_reading reread + 所有阶段 judge 打回触发的盲重抽，必须做物理硬隔离**，不能只靠 prompt 指令约束。

**✅ 2026-07-08 已落地**（Fable 5 编排 + Codex 双审执行，设计 verdict=APPROVE-WITH-CHANGES 5 MAJOR+4 MINOR 全采纳）：
- 四层机制：L1 clean-room staging（repo 外，只拷 images+testdata+skill〔剔 judge_rubric.md〕+cv_toolbox+prescan，MANIFEST sha256+禁运断言）→ L2 headless `claude -p --settings`（allow 仅 staging、deny repo/root/home/web/Agent/mcp）→ L3 PreToolUse guard（结构化 Bash 白名单=仅 `python tools/run_cv_probe.py --request <json>`+少量只读命令；shlex 解析拒复合命令/`python -c`；**词法检查只扫 tool_input 不扫信封**〔transcript_path 误杀是首版真 bug，冒烟抓到已修〕）→ L4 串行 merge+isolation_provenance+access_log 归档进 attempt。
- 件：`src/agent/execution/isolation.py` + `isolation_templates/{guard.py,run_cv_probe.py}` + `scripts/tool_scripts/spawn_isolated_reader.py`；guide 附录 A spawn 协议改隔离版，老 prompt 串废弃。
- 真对抗冒烟验收：staging 内合法读 allow / repo gt 读 settings 拒 / Bash 直读+`python -c` 逃逸 guard 拒，全留痕 access_log。
- pilot→batch **不用 --resume**（上下文污染），每段冷启+feedback 文件（过无禁运 token 词法检查）。

**How to apply**：新重读/盲重抽一律走 `spawn_isolated_reader.py build/spawn/feedback/merge`；spawn 必须干净 env（`--execute` 内置 clean_spawn_env；手动跑要 `env -i` 否则继承外层 CLAUDE 环境变量）。**如实限界**：root+无内核沙箱 ⇒ harness 级强制非 OS 级，OS 沙箱（bwrap/宿主 docker）留增强钩子。codex 执行器隔离=顺延。相关 [[per-stage-validation-judge-architecture]] [[reading-cv-toolkit-methodology]]。

**⚠️ 2026-07-30 硬隔离壳第一次在真实 case 上跑完整识图 ⇒ 抓到三个缺陷，且它很可能是识图质量崩掉的主因**（详 [[reading-cv-toolkit-methodology]] 07-30 条：同模型同工具 8/8 → 1/8）：
- **F-2（MAJOR 候选）staging 不含 `session_kickoff.md` 强制要求的格式样板件**（另一 case 的已接受识图产物，kickoff 原文 "Read it as a style/format anchor"）：`isolation.py` 的 build 零处理该文件，**且 `guard.py` 的 `DENY_TOKENS` 含 `case_tests`** ⇒ 子代理被自己的 kickoff 指向一个墙外、且按原路径尝试必被守卫拒的文件。07-07 走 prompt 级隔离能读全仓故从未暴露。**本轮处置**=主控按不触禁词路径 `reference/worked_example_plan.json` 补入（另一栋楼、不含本 case 信息 ⇒ 非污染），**遗留：手工补入件不进 `MANIFEST.json`，溯源清单漏记**。
- **F-4（MAJOR 候选）guard 的词法禁词扫「整个序列化 tool input」，包括 Write/Edit 的 `content`**（不只路径参数）⇒ 子代理写必交的 `reading_summary.md` 时用「约等号 ~」被判 `home token is forbidden`、**连拒三次一度写不出**；**立面 JSON 里的 `grade line`（室外地坪线）撞禁词 `grade` = 本领域核心词汇被误伤**；同族被拦：`python -c` 内分号、`> /dev/null`、`find | sort`、散文三点省略号（撞 `..`）。**定性 = 可用性缺陷非安全洞（方向 fail-safe），但会被误读成「模型不会写」**。**修法**：路径类禁词只作用于 `_looks_like_path` 判定为路径的参数，不扫散文内容。
- **F-5（MINOR）merge 与 kickoff 的产物形态对不上**：`merge_isolated_output` 硬要 `{"views": {<expected_output_id>: …}}` 单一聚合件，kickoff 却令子代理每图一个 JSON，**无人负责拼装** ⇒ 主控手工按 view manifest 的 `expected_output_id` 机械组装。
- **⚠️ 成本侧（可能是质量崩的主因之一）**：硬隔离把每次探针从「一条带参命令」变成「先 Write 请求 JSON 再执行」= **调用成本翻倍**；本轮探针数 19→8、守卫摩擦另吃 6 轮。**下次改隔离壳前先跑单变量 A/B**（见 [[reading-cv-toolkit-methodology]]）。
