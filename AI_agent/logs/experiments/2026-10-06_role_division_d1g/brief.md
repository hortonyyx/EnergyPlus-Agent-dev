# 派工：分工体系 v1 · D1g（调度员的弯路）

派工人：Opus 5.5（项目经理）。工作树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-worktrees\d1g`，分支 `dev/astra-d1g-20261006`，基于含本派工单的主线提交（当前 Agent `t1-20261006-d1f.1`）。

**按 `AI_agent/project/unified_agent_acceptance.md` 的“分工体系 v1 · D1g”一节交付。** 先读同一文件 D1c 验收结论后面的补记，再读 [sm24 分工整案调试](../2026-10-06_role_division_sm24_debug/README.md)（run3 的逐步过程、结果与改进清单是本包的依据），然后读 `src/agent/runtime_roles/` 的 `session.py`（派工、建层、对位、写高度）、`elevation.py`（对位与 `height_application`）、`guidance.py`（调度员与平面读图员指引）、`trial.py`、`submission.py`、`plan_review.py`，以及 `scripts/tool_scripts/bim_agent_role_heights.py`。

**为什么做：** sm24 分工调试 run3 第一次从原图走到整案交付，读图员合计 39 次请求、约 108 万 token，门窗位置 20/21 比单模型好；但调度员 41 次请求、371 万 token，约一半花在可避免的弯路上：自己把平面 y 轴写成“图像从上到下”导致南北镜像；平面返工后先在旧稿上对位；两次拿内层的对位编号去写高度；按平面读图员假设的层高 3.0 米建层，写完高度才改成 3.6 米（立面外轮廓顶是 4.5 米），新稿与旧高度记录不在一条链上只好重写；四个立面并行写高度，每次都以同一份稿为底而分叉，重写时又分叉。原始运行在证据分支 `evidence/role-division-sm24-debug-2026-10-06`（需要时用 `git show <分支>:<文件>` 取出，解到 `AI_agent/archive/local_backup/d1g/` 下，用完删除）。

**文件范围：** `src/agent/runtime_roles/`、`scripts/tool_scripts/bim_agent_role_heights.py`、`src/agent/runtime_configuration.py` 与 `src/agent/runtime_roles/entry.py` 中并发默认值相关部分、`tests/` 中角色相关检查、本实验目录。单模型的指引、工具目录、请求与返回逐字节不变；不改 `scripts/tool_scripts/run_bim_agent.py` 与 `src/agent/geometry/` 的共用内核（可以调用）。不改历史实验数据与原始输入。

**要点：**
- 开工先在本目录写报告初稿 `README.md`（设计说明：固定坐标约定怎样附到每个读图任务、镜像标定时提交要什么依据、建层怎样接收标高及其依据、写高度怎样一次成稿与串行接续、何时算“内容相同不另存”、怎样判断对位所用稿基于被替代的产物），随进度更新。
- 指引改动是**替换**：给出调度员、平面读图员指引改前改后的字符数（改前调度员 1,937、平面读图员 8,698），说明删了哪些、加了哪些。
- C 项要给出离线复现：按 run3 的调用顺序（四个立面并行写，再并行补写）跑一遍，给出改前改后的存稿数与最终稿是否带齐四个立面的高度。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。
- **本包 0 次模型请求**：不跑真实整案，合并后由 Opus 复跑 sm24 分工调试。Paratera 0，DeepSeek 0。
- 跑检查：工作树根目录先执行 `. .\scripts\activate_windows.ps1`（本工作树自己的 `.venv` 已建好；脚本已默认 `OPENBLAS_NUM_THREADS=1`），确认 `src.agent.__file__` 指向本工作树；pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/d1g/pytest`（先建好父目录）。改了登记文件后用 `python -m src.agent_runtime.agent_registry register --root . --version <新版本>` 登记再跑真实工具检查。**交付前把 `AI_agent/archive/local_backup/d1g/` 下的临时目录删掉**（沙箱身份建的目录，本机账户事后删不掉）。沙箱里结束进程的检查会因权限失败，注明即可。不为变绿放宽保护性断言。
- **Windows 上写文本一律 LF**：`write_text(..., newline="\n")` 或现有写入辅助。
- **沙箱下所有 `.git` 都是只读的：不要尝试提交、建分支或改 Git 配置。** 改动留在工作树，报告给出建议的提交分组。

不设硬时限。最终回复按验收 A–I 逐条给结果，附 C 项的复现数字、指引字符数、检查结果与建议的提交分组。
