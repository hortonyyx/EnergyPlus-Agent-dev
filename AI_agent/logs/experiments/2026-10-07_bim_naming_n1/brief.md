# 派工：命名包 N1（BIM 全部产物统一用公开名）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\n1`，分支 `dev/astra-n1-20261007`，基于含本派工单的主线提交。**迭代范围：domain · BIM rules（公开命名方案）与出图、查看页**；不改模型可见的指引与工具说明、不改 runtime。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“命名包 N1”一节交付。** 先读 [名词规范](../../../project/terminology.md)、[BIM 命名](../../../design/bim_naming.md)、[房间功能类型表](../../../design/room_types.md)，再读 `src/agent/geometry/source_naming.py`、`src/agent/geometry/source_bim.py`、`scripts/tool_scripts/render_geometry_viewer.py`、`src/agent/data/room_types.json`，以及画 `plan_*.png` 平面图、回叠图标签、交付报告的代码（自己定位，列进报告）。

**为什么做：** 用户 10-07 看 BIM 产物后定：用途段内部改短横；同层同用途同方位重复时加编号；全部产物统一用公开名（平面图上现在标的是模型自起的内部编号，如 `PLAN.F1:room-NW`）。用户要靠这些产物自己看结果把控质量，名字要一眼读得懂、处处一致。

**文件范围与并行约定：** 本包负责命名方案、平面图与回叠图的标签、查看页、交付报告里的名字，及对应检查与本实验目录。同时在做的包：D1j、D1k（`src/agent/runtime_roles/` 下多个文件与 `guidance.py`）、RT1（`src/agent_runtime/`）——这些都不要改。**不改** Agent 版本登记。若某处只能改到上述文件，先停下在报告里写明。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。
- 4 份交付稿在主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\cmp3\`（只读）；拷到本工作树 `AI_agent/archive/local_backup/n1/` 再重新生成。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。**本包 0 次模型请求**；Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/n1/pytest`。本机在跑三例对照，不跑全量。
- 新检查要克制，不锁报错原文；写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。

最终回复按验收 A–F 逐条给结果，附改前改后名字对照表、平面图与查看页的渲染结果路径、检查结果与建议的提交分组。
