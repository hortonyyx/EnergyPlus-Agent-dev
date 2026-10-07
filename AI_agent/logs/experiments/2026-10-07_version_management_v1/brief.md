# 派工：版本管理 V1（runtime 与 domain 分开登记、带日期命名、各模式指纹）

派工人：Opus 5.5（项目经理）。工作树 `D:\EnergyPlus-Agent-worktrees\v1`（10-07 起工作树放 D 盘，用户要求不占 C 盘），分支 `dev/astra-v1-20261007`，基于含本派工单的主线提交。**迭代范围：runtime 为主**（版本登记、核对与运行回执）；domain 只加一个提供各模式指纹的函数，不改任何行为。单模型与分工模式交给模型的内容都不能变。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“版本管理 V1”一节交付（A–G）。** 先读 [名词规范](../../../project/terminology.md)（runtime／domain 分界、版本号一行）与 [工作方式](../../../workflow/development.md) 里版本登记的写法，再读 `src/agent_runtime/agent_registry.py`、`versions.py`、`agent_versions.json`，以及单模型和分工各角色组装工具清单、指引、任务说明的代码（`src/agent/runtime_roles/`、`scripts/tool_scripts/` 下，自己定位，列进报告）。

**为什么做：** 现在只有一个 Agent 版本号，登记 85 个文件，几乎都在 domain，runtime 只登记 `loop.py`；今天合入的 RT1 新增 `dispatch.py`、`timing.py`、`route_dispatch.json` 都不在登记内，改了不变号。新文件要手动 `--add-file`，10-07 漏登过 `assembly.py`，N1 的 `bim_agent_delivery_display.py` 也是手动补的。单模型与分工共用一个号，单模型没变只能靠逐字节对照间接证明。接下来要密集做提速实验（思考档、各角色配置、domain 改动），每次运行必须能说清用的是哪版 runtime、哪版 domain、哪种模式。

**与验收原文的两处更新：**
- 登记表现有 **43** 个记录（10-07 新增 `t1-20261007-d1k.1`、`t1-20261007-n1.1`、`t1-20261007-cc1.1`）。按登记顺序编为 domain-v1…v43，旧号保留作别名；下一个新 domain 版本是 v44。runtime 从 v1 起。
- 运行配置里每个角色已可分别设思考档（`roles.*.reasoning_effort`）。运行回执与版本记录要写全各角色的线路、型号、思考档与输出上限（D 项）。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。
- **0 次模型请求**；Paratera 0，DeepSeek 0。
- 环境：工作树根目录先 `uv sync --frozen --python 3.12`，再 `. .\scripts\activate_windows.ps1`，确认 `src.agent_runtime.__file__` 指向本工作树。pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/v1/pytest`。不跑全量。
- 本机同时在跑 GLM 与 Claude 的整案（D 盘另外的运行工作树），不要动别的工作树和主树的运行目录。
- 文件归属：本包负责 `src/agent_runtime/agent_registry.py`、`versions.py`、`agent_versions.json` 及登记、核对、回执相关代码和检查；`scripts/tool_scripts/run_bim_agent.py` 里只动 `subscription()` 写回执与版本记录的部分（Claude Code 线路）；domain 侧只**新建**一个指纹模块，不改 `src/agent/runtime_roles/`、`src/agent/geometry/` 下的现有文件（同时进行的质量包 Q1、Q2 在改那里的规则、工具与指引，见验收记录两节的文件归属）。指纹模块要在 Q1、Q2 合入后仍能算出新的指引与工具，不复制它们的文字。
- 新检查要克制，不锁报错原文；写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。

最终回复按验收 A–G 逐条给结果，附迁移后的登记表摘要（新旧号对照前后几条）、一次登记命令的输出示例、各模式指纹清单，以及检查结果与建议的提交分组。
