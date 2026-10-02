# 10-02 统一 Agent 阶段 0：接口与验收样例

用户“开工吧，开始开发”。按[开发计划](../../../project/unified_agent_harness_plan.md)，阶段 0 由 Astra 牵头实施，Opus 定验收标准并验收。

- [派工单](brief.md)；[阶段 0 验收标准](../../../project/unified_agent_acceptance.md#阶段-0接口与验收样例)
- 工作树 `.worktrees/astra-stage0`，分支 `dev/astra-stage0-20261002`。

## 派工前的连通测试（Opus，10-02）

上轮 Astra 只做只读调研；本阶段要写代码、跑测试，先测 codex 在容器里能否写入。

- 容器本身禁止建立命名空间（`unshare` 被拒，seccomp 开启、无 CAP_SYS_ADMIN），codex 默认的写沙箱（bwrap）无法启动。
- codex-cli 0.153.4 的 Landlock 只支持只读：工作区写模式两次测试（带与不带额外写目录）所有命令都报“permission profiles requiring direct runtime enforcement are incompatible with --use-legacy-landlock”，未执行任何命令、未写入。用量（`gpt-6-astra`，low）：输入 101,666／66,340（缓存 95,616／61,184），输出 604／367。线程 `01a0fd27-288d-7482-b7bf-725db936412e`、`01a0fd29-e50b-7f42-b45c-aa5b0c25e5d1`。
- 完全访问模式（用户平时直接用 Codex 开发时的设置：`danger-full-access`、免审批）由 Opus 从 Claude Code 内启动时，被 Claude Code 自动权限审核拦下，未运行。启动方式交用户决定。
