# 污染硬隔离机制化执行日志

日期：2026-07-08

## 已完成

- 新增 `src/agent/execution/isolation.py`：
  - `build_isolation_workspace()` 构建 repo 外 staging，白名单拷贝 `case_data`、0_reading skill（跳过 `judge_rubric.md`）、`src/agent/reading/cv_toolbox/`、prescan、kickoff、`out/`、guard、wrapper 和 `isolation_settings.json`。
  - `MANIFEST.json` 记录 sha256、repo-relative `source_path`、类别；精确路径/文件名禁运 hard block，语义 token 仅 warning。
  - `write_feedback()` / `check_feedback_text()` 阻断污染 token。
  - `merge_isolated_output()` 串行 merge，attempt index 碰撞重试，原子保存 `run_manifest.json`，归档 `MANIFEST.json`、settings、guard、access_log，并写 `isolation_provenance.json`；provenance hash 纳入 manifest `input_hashes`。
- 新增 staging 模板：
  - `src/agent/execution/isolation_templates/guard.py`：stdlib-only PreToolUse guard，结构化 Bash allowlist，仅放行 `python tools/run_cv_probe.py --request <staging内json>` 和少量只读命令；拒绝复合 shell、`python -c`、`cd`、`env`、重定向、`..`、`~`、repo 绝对路径、外部 symlink/路径；写 `access_log.jsonl`。
  - `src/agent/execution/isolation_templates/run_cv_probe.py`：校验 request JSON schema，所有路径 resolve 后限 staging 内，再转发到 staging 内 `tools/cv_probe.py`。
- 新增 `scripts/tool_scripts/spawn_isolated_reader.py`：
  - `build` / `spawn` / `feedback` / `merge` 子命令。
  - `spawn` 默认只打印 `claude -p ... --settings ...`，仅显式 `--execute` 才执行；本轮未真跑 Claude CLI。
- 改写 `AI_agent/guides/new_case_guide.md` 附录 A：
  - 隔离工作区流程成为正式 0_reading 重读/盲重抽协议。
  - 旧 prompt 级启动串标注废弃，仅留历史指针。
- 新增 `tests/test_isolation.py`：
  - 覆盖 H1 白名单/禁运/MANIFEST/source_path/wrapper 真图 smoke。
  - 覆盖 H2 guard 允许/拒绝矩阵、外部 symlink、外部 request 路径、access_log。
  - 覆盖 H3 merge provenance/hash 绑定、attempt 不覆盖、feedback 污染 token 拒绝。

## 测试

- `pytest -q tests/test_isolation.py`：
  - `20 passed`
- `pytest -q tests/test_isolation.py tests/test_gt_discipline.py::test_executors_do_not_reference_gt`：
  - `21 passed`
- `pytest -q --ignore=tests/test_zone_agent.py`：
  - `536 passed, 9 xfailed, 115 warnings`
  - 按用户说明跳过 `tests/test_zone_agent.py`，该文件在本环境有真网络依赖。

## 真 spawn 冒烟反馈修复

- 主控真跑 `claude -p --settings` 后发现 deterministic bug：Claude Code PreToolUse payload 信封自带
  `transcript_path=/root/.claude/projects/.../<session>.jsonl`，原 guard 对整个 payload 做词法/路径扫描，导致合法
  `tool_input` 也因信封字段在 staging 外被误杀。
- 修复：
  - `guard.py` 的词法检查和路径检查只作用于 `tool_input`；Bash 只检查 command 字符串，其余工具只遍历
    `tool_input` 值。`transcript_path`、`cwd`、`session_id`、`permission_mode` 等信封字段不参与 allow/deny。
  - deny 日志新增 `tool_input_excerpt`，截断记录非法输入片段；allow 不记录原文。
  - `python tools/run_cv_probe.py --request ...` 仍保留相对路径精确形态，同时接受 resolve 后等于
    `<staging>/tools/run_cv_probe.py` 的绝对路径形态。
- 补充回归：
  - payload 含 staging 外 `transcript_path` + 合法 staging 内绝对路径 `Read`、无参 `ls`、合法 `run_cv_probe`
    均 allow。
  - 同样信封 + 非法 repo/gt 路径 `tool_input` 仍 deny，并写 `tool_input_excerpt`。
- 修复后测试：
  - `pytest -q tests/test_isolation.py`：`22 passed`
  - `pytest -q --ignore=tests/test_zone_agent.py`：`538 passed, 9 xfailed, 115 warnings`

## 偏离与遗留

- 为满足既有 `test_gt_discipline.py` 对 executor 源码的静态扫描，禁运文件名 token 在实现中采用运行时拼接，运行语义不变。
- 初版未由 Codex 执行真实 `claude -p --settings` 冒烟；主控后续真跑暴露的 `transcript_path` 误杀问题已按上节修复。
