# 派工：质量包 Q2（立面独立读门窗左右位置、按墨线对齐，平立面互证由调度员裁决）

派工人：Opus 5.5（项目经理）。工作树 `D:\EnergyPlus-Agent-worktrees\q2`，分支 `dev/astra-q2-20261007`，基于含本派工单的主线提交。**迭代范围：domain · roles、tools、methods、guidance，只影响分工模式；单模型交给模型的内容逐字节不变；runtime 不改。**

**按 `AI_agent/project/unified_agent_acceptance.md` 的“质量包 Q2”一节交付（A–F）。** 先读 [名词规范](../../../project/terminology.md)、[决策](../../../project/decisions.md) 10-07 晚“平面立面各读各的，调度员裁决”与“坐标按标注规整、按像素对齐”、[评价口径](../../../design/evaluation.md)“精度三档”、[工种与角色分工](../../../design/role_division.md)，再读 `src/agent/runtime_roles/elevation.py`（立面产物、`match_elevation`、整组线性拟合）、`assembly.py`（一步建楼）、`assembly_review.py`、`height_evidence.py`、`height_writes.py`、`session.py`（调度员工具与 `edit_bim`）、`guidance.py`（立面读图员与调度员几段）。

**为什么做：** 用户：“平面立面互相佐证，互相配合，不存在以哪边为准……应该是各读各的，然后调度员来最终裁决”；“立面…算一下像素应该很容易对齐的吧，因为边界是很明显的”。现在立面读数只用来认是哪一扇、写高度（对位容差 35 cm、宽度 25 cm），左右位置差多少都不回头改平面；用户看着立面歪的正是左右位置。

**证据（只读，需要时拷到本工作树 `AI_agent/archive/local_backup/q2/`）：** 主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\` 下 `cmp3\`（三例对照：sm24、sm21、sm25 分工各一次）、`role_debug\`（10-06、10-07 sm24 run3–run7、sm21 run1、sm25 run1）、`reader_model_probe\`（27B 立面读图员四份）；参照与评价脚本见 `AI_agent/logs/experiments/2026-10-07_three_case_comparison/`，按角色小题的参照见 `AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/`。主树 `AI_agent/archive/local_backup/merged/` 与 D 盘 `runs-next`、`runs-cc` 是正在跑的整案，只读、不要动。

**设计要点（我的建议，你可按证据调整并写明理由）：**
- 立面墨线对齐做成独立的确定性函数（输入原图、读图员的门窗大致框与标定，输出对齐后的框与移动摘要），在提交检查里调用，产物里同时保存读图员原框与对齐后的框。
- 比对放在一步建楼的对位之后；10 cm 以内平面值不动（不取中间值），超过的列入待裁决，带两边数值、依据与局部图引用；调度员用已有的 `edit_bim` 小修入口落实“采用立面值”，必要时给它加一种操作，不新增工具。
- 待裁决清单每项一行，按偏差从大到小；10–30 cm 允许一次批量“保持平面值并记入说明”。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新。
- **0 次模型请求**；Paratera 0，DeepSeek 0。真实效果由 Opus 合入后在 GLM 上实测。
- 环境：工作树根目录先 `uv sync --frozen --python 3.12`，再 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树。pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/q2/pytest`。不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 机器忙时偶发失败，遇到时单独重跑并如实写。
- **文件归属（三包并行）：** 本包独占 `elevation.py`、`assembly.py`、`assembly_review.py`、`height_evidence.py`、`height_writes.py`、`session.py`，以及新建的立面墨线对齐模块；`guidance.py` 只动立面读图员与调度员的几段（平面读图员几段归 Q1）。**不改**：`src/agent/geometry/` 下现有文件、`scripts/tool_scripts/`、`trial.py`、`readers.py`、`plan_format.py`、`plan_review.py`、`submission.py`（Q1）；`src/agent_runtime/` 与登记表（V1）。确需越界先在报告里说明、交我协调。
- 新检查要克制，只验行为，不锁指引原文和报错原文；被替换设计的旧检查直接删除或改写，不并存。写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。

最终回复按验收 A–F 逐条给结果，附：对齐前后立面读数对参照的三档统计、各次运行平立面差的分档扇数、sm25 分工待裁决清单、指引字数前后对照、检查结果与建议的提交分组。
