---
name: flow-reuses-accepted-attempts-reset-two-state-files
description: 改了生产代码后重跑 flow 拿新读数——只删 stage 目录没用，必须同时回退 run_manifest.json 与 orchestration_state.json 里的该 stage 条目
metadata: 
  node_type: memory
  type: project
  originSessionId: dda29000-298b-4b12-a9ad-349b94bb2f3b
---

2026-09-08h 实测（sm25-L_anchor/run_win_e2e，改配对代码后重跑 1_correction）：

flow 对**已接受**的 attempt 不重执行，直接复用归档工件重打分——attempt 工件
（如 window_resolver_inputs.json）逐位还是旧的，跑完看似"改动无效"。
只删 `1_correction/` 目录不够：flow 会报 `attempts=0, accepted=1` 且**什么都不产出**。

**Why**: 接受状态记在两处——`_run/run_manifest.json`（`stages.<stage>.accepted_attempt`
+ 工件哈希）与 `_run/orchestration_state.json`（`stages.<stage>.status`）。
两个都回退（pop 掉该 stage 条目）再删 stage 目录，才会真正重跑（真凭据、重新计费一轮）。

**How to apply**: 重跑前先备份旧 `1_correction/`（那是改前读数的唯一证据，删了就没了）；
判"这次跑用的是新代码"看新工件哈希/内容变了没有（如目录行数 96→67），
⛔ 不要只看"跑完了"。run 目录本身 untracked、归主控管，动前留备份并在交件里写明。
