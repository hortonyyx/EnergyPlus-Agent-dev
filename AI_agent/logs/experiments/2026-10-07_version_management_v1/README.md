# 版本管理 V1 执行报告

状态：实现与定向验证完成，未提交，交 Opus 复核。A、B、C、E、F、G 通过；D 的现行产品入口通过，旧开发桥根回执存在范围缺口，见下。执行方 Astra；基准 `e030b6b0195eea18d2d54261038f8a8f25640518`，工作树 `D:\EnergyPlus-Agent-worktrees\v1`，分支 `dev/astra-v1-20261007`。

## 范围与边界

- runtime：版本登记、文件核对、公共运行契约、版本记录与运行回执；domain 只新建指纹提供模块，读取 tools／guidance／任务模板，不改变 BIM rules、kernel、methods、roles 或模型收到的内容。单模型与分工都适用。
- 不修改 `src/agent/runtime_roles/`、`src/agent/geometry/` 的现有文件；`run_bim_agent.py` 仅修改 `subscription()` 的版本及回执记录部分。
- 不操作相邻 q1、q2、runs-next、runs-cc 或主树；不写 `.git`，不提交，不跑全量。
- 全部验证离线；模型请求 0，Paratera 0，DeepSeek 0；本包由 Astra 独立实施，未派子代理。

## 开工核对

已完整读取 `Agent.md`、产品目标、当前任务、工作方式、名词规范和最新 10-07 白天交接；开工工作树干净，Git 状态与近期提交已只读核对。

`uv sync --frozen --python 3.12` 首次因共享缓存内 `.git` 只读失败；指定本工作树 `AI_agent/archive/local_backup/v1/uv-cache` 后成功（176 个包，无安装变更）。激活后 `src.agent_runtime.__file__` 指向本工作树。

## A. 自动覆盖

最终 runtime 35 个文件、domain 397 个文件。登记与启动核对均重新枚举目录，新增、删除和内容变化都会检出；包括 `dispatch.py`、`timing.py`、`route_dispatch.json`。文件清单在登记表内，范围与核对结果另见 [registry_verification.json](registry_verification.json)。

| 版本线 | 自动扫描范围 | 依据 |
| --- | --- | --- |
| runtime | `src/agent_runtime/`、`src/harness_contracts/`、`src/__init__.py`、`src/utils/__init__.py`（出现时纳入）、`src/utils/file_lock.py`、`pyproject.toml`、`uv.lock` | 通用循环、服务适配、日志／契约／锁与依赖 |
| domain | `src/agent/`、`scripts/tool_scripts/`、`src/configs/`、`src/mcp/`、`src/utils/`（减去 runtime 所属文件）、`src/validator/`、`src/converters/`、`src/runner/`、`src/converter_manager.py`、`scripts/glm_code.py`、`scripts/glm_code.sh` | 建筑 Agent 与工具、渲染／校验／转换、配置与订阅线路启动依赖 |

排除检查目录、项目文档／`docs`、常规 README／许可证说明、测试发现辅助脚本、日志、缓存、备份临时文件；登记表本身不参与自身哈希。指引正文仍登记。目录中的符号链接／junction 拒绝跟随。范围外新增依赖需更新登记表 `scope`，不需要逐个 `--add-file`。

## B、F. 迁移与命名

正式登记表为 v2：runtime 当前 `runtime-v1-20261007`，domain 当前 `domain-v44-20261007`；runtime 1 条、domain 44 条、历史别名 43 个。旧表按键排序，不能把 JSON 键顺序当登记顺序；按只读 Git 历史恢复引入次序，证据为 [migration_order.json](migration_order.json)。

| 旧号 | 新号 |
| --- | --- |
| `5bb10538` | `domain-v1-20261002` |
| `t1-20261003-r3` | `domain-v2-20261003` |
| `t1-20261003-c2` | `domain-v3-20261003` |
| `t1-20261007-d1k.1` | `domain-v41-20261007` |
| `t1-20261007-n1.1` | `domain-v42-20261007` |
| `t1-20261007-cc1.1` | `domain-v43-20261007` |
| 本包首次完整登记 | `domain-v44-20261007` |

43 条原记录的所有原字段逐项与基准提交比较相等，旧号通过别名继续查询。历史记录标记 `legacy_explicit_files`，保留当时的文件与工具目录哈希；没有保存过的 runtime 版本、角色指纹不补造。旧运行记录不改写。历史查询不会拿现工作树冒充旧版。

`workflow/development.md` 的两处旧登记方法已替换，`project/terminology.md` 的版本号一行已更新；没有改写全局目标、路线或当前交接。

## C. 模式指纹

domain 新模块 `src/agent/version_fingerprints.py` 输出 JSON；runtime 只执行登记表配置的提供命令并读取 JSON，不导入 domain。四个原始 MCP 目录通过真实 `serve/list_tools` 离线取得；角色目录调用生产包装器的 `list_tools`，不调用模型或建模动作。角色指引调用现有 getter，不复制文字。任务模板从实际入口的表达式提取，以固定占位值表示用户输入、图片与时间；入口结构不能解析时登记失败，不回退到旧哈希。

已核对的实际来源：

- 单模型：`run_bim_agent.py` 的 `run_guide`、`run_experiment`、`subscription`、`worker_agents`，以及 `bim_agent_guidance.py`、`src/agent/runtime_entry.py`。
- 分工：`runtime_roles/entry.py`、`session.py`、`readers.py`、`elevation.py`、`guidance.py`、`coordinates.py`。这些现有 domain 文件均未修改。
- 单模型目录按 review／continuation 开关计算实际可见工具，指引覆盖无图片、图纸、网格视图、照片与 unknown 变体，包含 Claude Code 可选 worker 的现有提示。Q1／Q2 合入后重登记会读取新的指引和工具。

每组有工具、指引、任务模板三个 SHA-256 和聚合 SHA-256。下表为聚合指纹前 16 位，完整值在 [mode_fingerprints.json](mode_fingerprints.json)。

| 模式 | 聚合 SHA-256 前 16 位 |
| --- | --- |
| `single_model/coordinator` | `66f766a6cd9f00b0` |
| `single_model/coordinator_mesh` | `478d18abd3bb696b` |
| `single_model/readonly` | `4877c1e978658aaf` |
| `single_model/readonly_mesh` | `27599319731e1bc4` |
| `role_division/coordinator` | `83d990451d4ba4fc` |
| `role_division/plan_reader` | `a8a036d68423d715` |
| `role_division/elevation_reader` | `d6d5dca5b90c2f6b` |

本次首次补录的 7 组均出现在 `changed_modes`；这表示此前未记录这些指纹，不表示模型所见改变。四组原始工具目录哈希与 `t1-20261007-cc1.1` 相等。测试在内存中只改平面读图指引，只有该角色指纹改变，单模型及其他角色保持不变。

## D. 运行标记与范围缺口

现行自有 runtime 单模型、三角色分工，以及 Claude Code／GLM 的 `subscription()` 入口，均在首请求前核对两条版本线。版本记录与回执写入 runtime 版本、domain 版本、`single_model`／`role_division`、各角色线路／型号／实际思考参数／输出上限和 Git 提交。分工子任务继承根记录的全角色配置；三例的 17 份子回执已逐项与根回执核对，证据见 [offline_run_identities.json](offline_run_identities.json)。旧 `agent_version` 字段继续保留，值为 domain 正式号。

自有 runtime 使用 `versions.json`；外部订阅入口补 `<name>_versions.json`，并与原 request／receipt 写同一身份。调用方上下文不能覆盖核验后的版本字段。Claude Code 没有显式输出上限，`output_tokens=null`，标明 `client_default_not_exposed`，未为补记录而改实际命令或推测上限。旧日志能读入；新增字段缺失时保留空值，跨实现的恢复仍受原有版本一致性检查约束。

**未闭合：旧开发模型外层 MCP 桥** `src/agent/runtime_coordinator.py` 的根 `coordinator-config.json`／`receipt.json` 没有升级成新字段；它通过公共 `agent_version_record()` 已获得两条线的启动核对，桥内局部观察子运行通过 `make_versions()` 获得双版信息，但不能据此称根回执已满足 D。“domain 只新建指纹模块”的归属限制禁止本包改这个现有文件。旧桥额外局部观察提示也不混入本次七组产品模式指纹。

建议 Opus 确认是否仍把旧桥列入当前产品运行范围；若保留，另协调其 `initialize()`／`finish()`，调用本包 `external_run_identity()` 写根配置与回执，外层 dev model 不可见的型号／参数如实标为未采集，再做旧桥定向检查。这是 D 的已知缺口，不能按 A–G 全绿验收。

## E. 单命令

仓库根激活环境后：

```powershell
python -m src.agent_runtime.agent_registry register
python -m src.agent_runtime.agent_registry verify
python -m src.agent_runtime.agent_registry verify --version t1-20261007-cc1.1 --lookup
```

本次迁移使用 `register --date 20261007 --legacy-order AI_agent/logs/experiments/2026-10-07_version_management_v1/migration_order.json`，完整输出见 [registration.json](registration.json)，摘要：

```json
{
  "runtime_version": "runtime-v1-20261007",
  "domain_version": "domain-v44-20261007",
  "changed_lines": ["runtime", "domain"],
  "file_counts": {"runtime": 35, "domain": 397},
  "changed_modes": [
    "role_division/coordinator", "role_division/elevation_reader", "role_division/plan_reader",
    "single_model/coordinator", "single_model/coordinator_mesh",
    "single_model/readonly", "single_model/readonly_mesh"
  ]
}
```

随后相同命令输出 `changed_lines=[]`、`changed_modes=[]`，登记表 SHA-256 前后相等。只变 runtime 数据或新增 runtime 文件，仅 runtime 增号；只变 domain 文件或模式指纹，仅 domain 增号；删除文件也不能绕过启动检查。记录以临时文件原子替换，登记过程中源文件变化会拒绝写入。旧 `--version` 可作可选别名，已取消手动 `--add-file`。

## G. 验证

全部 `pytest -n 2`，仅本包定向范围；没有全量、整案模型请求或计费调用。累计覆盖 96 个不同检查，最终均有通过结果。命令、耗时与失败处理保存在 [checks.json](checks.json)，各批原始输出保存在 [test_outputs.md](test_outputs.md)。

| 批次 | 结果 | 范围 |
| --- | --- | --- |
| 登记与契约 | 52 过，44.42 秒 | 登记／别名／增删与无变化、订阅回执、显式登记表覆写、估算及事件契约 |
| 贯通与恢复 | 42 过、1 失败，489.19 秒 | sm21／sm24／sm25 的真实冻结 MCP 离线贯通、恢复、目录核对、单模型首请求字节对照、既有 runtime 行为 |
| 正式表复验 | 21 过，63.49 秒 | 登记与模式提供器、订阅回执、三例首请求字节对照、截止后拒绝启动、前批失败项 |

中间唯一失败：既有测试将整个 `subprocess.Popen` 替换为“禁止模型启动”，同时拦住新增的只读 `git rev-parse`。修正测试中的 Git 元数据替身后通过，生产行为未为测试绕开检查。其他直接替换模型启动的检查也补同样的元数据隔离；没有放宽模型调用拦截。没有遇到已知 trial 恢复偶发失败。

开发阶段使用临时登记表，正式表最后一次迁移；贯通后仅补公共包入口覆盖、排除说明文件／测试发现脚本，并纳入现有 Claude worker 提示指纹，运行行为未变。最终登记／回执／首请求检查在正式登记表上重跑，未重复已有通过的整组离线贯通。历史原字段、原始工具目录、`subscription()` 命令表达式及运行器其他函数另作直接比较，结果见 `registry_verification.json`。`git diff --check` 通过。

本次 `source_commit` 是未提交工作树的基准 `e030b6b0`；版本文件哈希记录当前修改，未来运行的 `git_commit` 读取实际 HEAD。没有把未提交修改声称为该 Git 提交本身的内容。

## 交回 Opus

建议两组提交（本包未执行 Git 写入）：

1. runtime 双版本登记／核对／回执、公共契约、domain 新指纹模块、`subscription()` 记录段、正式迁移表、检查使用的 `migration_order.json` 及对应检查。检查文件为 `test_runtime_agent_registry.py`、`test_bim_agent_glm_route.py`、`test_role_single_parity.py`、`test_runtime_r3.py`、`test_bim_time_budget.py`；后三个仅隔离新增 Git 元数据查询。代码与正式登记表一起提交，避免中间提交只带旧表而拒绝新运行。
2. 两处操作文档、本目录其余证据与报告。

合并 Q1／Q2 后保留本包迁移历史，再在合并树执行一次 `register`，由实际文件和模式指纹决定是否增号；不要拿本工作树的 v44 代表尚未合入的 Q1／Q2 改动。D 的旧桥缺口交 Opus 协调；全局验收、路线、交接与提交／推送仍由 Opus 处理。

验证证据已归档。递归清理本包临时目录的命令被自动审批审查拒绝，工具仅返回 `blocked by policy`，命令未执行；临时目录和本工作树 `.venv` 均保留，状态见 [cleanup.json](cleanup.json)。uv 临时缓存还含一个零字节 `sdists-v9/.git` 标记，按只读边界保留。不改换方式绕过拒绝，不操作运行工作树和相邻质量包。
