# R2-D Agent 版本登记交付

## 结果

已把原来写死在 `runtime_tools.py` 的五个入口文件哈希和四种工具目录哈希移入独立登记表，并依据 10-02 GLM 基线的 `experiment_condition.json` 把登记范围补齐为实际 45 个工具实现依赖。运行前按登记的当前版本核对工具、指引和任务说明文件；工具服务启动后再核对实际 MCP 目录。历史版本 `5bb10538` 保留为不可覆盖的首条记录。

登记表：`src/agent_runtime/agent_versions.json`。历史版本 `5bb10538` 登记 45 个实现依赖，分类为 `tool`、`guidance`、`task_description`，并登记 coordinator、readonly 及两种 mesh 目录的哈希。45 项已逐一与当前字节及 `git show 5bb10538:<path>` 核对，均与基线条件记录相同。

运行版本：`VersionManifest.agent_version` 为兼容字段；`make_versions()` 对当前登记做逐文件核验后，写入版本 ID 与完整登记记录 evidence。因此 `versions.json`、请求事件中的版本清单和开始事件所引用的 runtime config 都能还原当前 Agent 版本。主线程已在 `loop._stop()` 把版本 ID 写入运行回执。

## 命令

核对当前版本：

```bash
uv run python -m src.agent_runtime.agent_registry verify --root .
```

登记只修改既有文件的新版本，并同时离线探测四种真实 MCP 工具目录：

```bash
uv run python -m src.agent_runtime.agent_registry register --root . --version <新版本ID>
```

新版本增加了工具、指引或任务说明文件时显式纳入：

```bash
uv run python -m src.agent_runtime.agent_registry register --root . \
  --version <新版本ID> \
  --add-file tool:scripts/tool_scripts/<新工具文件>.py
```

`--add-file` 可重复使用，类别限 `tool`、`guidance`、`task_description`。登记命令拒绝覆盖同名历史版本，写入采用临时文件替换；默认把新记录切为当前版本。

新增源文件可以通过登记纳入哈希闭包；若实际新增了对模型公开的工具名称，还必须显式扩充角色白名单和重复执行策略。版本登记本身不会绕过权限策略。

## 反例与验证

- 五个原锁入口文件逐个复制到隔离仓库并各改动一次；每次运行核对均因对应路径哈希变化失败。
- 另改动入口之外的 `src/agent/geometry/plan_partition.py`，证明工具子实现变化同样会被拒绝，不会只守住五个入口。
- 对改动后的文件登记 `test-next`，核对立即通过；再次读取登记表确认旧 `5bb10538` 记录逐字不变。
- 新建 `bim_agent_new_tool.py`，以 `--add-file` 对应的程序接口登记后进入新版；随后改动该新文件，核对失败；历史记录仍不变。
- 实际执行一次 CLI 登记探测，四种 MCP 目录哈希与历史登记完全一致；随后 CLI `verify` 通过。没有模型或外部 API 调用。
- 首轮定向：`tests/test_runtime_agent_registry.py tests/test_runtime_frozen_tools.py tests/test_runtime_estimation.py`，27 项通过。
- 联合定向：再加 `tests/test_harness_core_contracts.py tests/test_runtime_r2_truncation.py`，62 项通过。
- 完整 45 文件闭包及新增文件场景补测：版本登记与冻结工具两文件，17 项通过；临时目录修正后版本登记 9 项再通过。
- 现役冻结工具测试已改为从当前登记读取 source commit、指引文件哈希及四种目录哈希；只有当前版本仍为 `5bb10538` 时才核历史 material 字节。用 mock 的未来版本证明期望会随新指引和目录哈希更新；该文件 9 项通过。
- `git diff 5bb10538..HEAD -- scripts/tool_scripts src/agent/geometry src/agent/correction src/agent/execution` 无输出；本包未改冻结工具、指引、几何、修正或现有执行模块。

## 提交与文件

- `f529daed68e687af84c3ebdb458089d693202d06` `Add versioned agent registry`
- `d41e3327dcdda576ea78a26c6c53cdb40a59d23d` `Support new files in agent versions`
- `0882b4ed` `Cover full agent tool dependency set`
- `6d8618b5` `Keep registry probes inside worktree`

改动文件：

- `src/agent_runtime/agent_registry.py`
- `src/agent_runtime/agent_versions.json`
- `src/agent_runtime/versions.py`
- `src/agent/runtime_tools.py`
- `src/harness_contracts/events.py`（只增加 `VersionManifest.agent_version` 一行）
- `tests/test_runtime_agent_registry.py`

本简报文件单独由后续提交保存。

## 集成接口与待办

主循环回执接口已由主线程接入：`self.versions.agent_version.identifier`，旧测试构造的版本清单允许该字段为空。

外层协调已由主线程在 `CoordinatorSession.initialize()` 的 `configuration` 和 `coordinator-session` source 写入完整登记记录，`CoordinatorSession.state()` 的 `runtime_state` 返回版本 ID；该服务没有独立根运行回执，state 同时提供账目摘要。其内部观察子任务使用普通 Runtime，回执沿用主循环字段。

开发子代理：`gpt-5.6-sol`／high，用于 D 版本登记实现与复核；协作接口未提供 token 用量，记为未知。Paratera、DeepSeek、GLM 与其他模型调用均为 0。
