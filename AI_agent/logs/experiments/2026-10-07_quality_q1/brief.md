# 派工：质量包 Q1（平面几何的三维对齐与防碎条；平面读图员按标注规整、按墨线对齐）

派工人：Opus 5.5（项目经理）。工作树 `D:\EnergyPlus-Agent-worktrees\q1`，分支 `dev/astra-q1-20261007`，基于含本派工单的主线提交。**迭代范围：domain · BIM rules 与 kernel（两种模式都受影响），domain · tools／methods／guidance 只改分工的平面读图员；runtime 不改。**

**按 `AI_agent/project/unified_agent_acceptance.md` 的“质量包 Q1”一节交付（A–I）。** 先读 [名词规范](../../../project/terminology.md)、[决策](../../../project/decisions.md) 10-07 晚的几条（硬约束、坐标按标注规整按像素对齐、专用 OCR 暂缓）、[BIM 简化与容差](../../../design/model.md)“10-02 规整原则与容差分层”、[评价口径](../../../design/evaluation.md)“精度三档”，再读：

- kernel：`src/agent/geometry/plan_partition.py`（编译）、`plan_assembly.py`（多层装配）、`building_precision.py`（A4-T 全楼检查）、`wall_placement.py`、`dimension_chain.py`、`plan_wall_support.py`（墨线支持量测）、`plan_drawing_differences.py`、`wall_reference.py`；
- 工具入口：`scripts/tool_scripts/run_bim_agent.py` 里 `Toolkit` 的建层、修改平面稿、装配三处（`build_plan_bim`、`revise_plan_bim`、`assemble_plan_bim` 的实现与返回）、`bim_agent_precision.py`、`bim_agent_guidance.py`；
- 分工的平面读图员：`src/agent/runtime_roles/trial.py`、`readers.py`、`plan_format.py`、`plan_review.py`、`submission.py`（平面一侧）、`guidance.py`（平面读图员的几段）。

**为什么做：** 10-07 sm25 两种模式的交付稿都有“碎条”与“错开一点点”：二层约 12 cm 的墙缝成了房间，同层 4 处平行墙线只隔 11–13 cm，上下层同轴墙除外墙外全部错开 0.4–22.6 cm。用户：“这个需要专门约束，不能出现这种结果”；“可以想象成不区分方向的三维空间里很多互相挨着的块，这些块要么对齐要么错开，不应该出现错开一点点的情况”。门槛已定：面差不到 30 cm 就对齐，房间任何部位不窄于 0.6 m，同一道墙不许建成两条线。另一半是数据来源：读图员现在自己量像素、两点换算，用户要求位置按尺寸标注规整、按墨线对齐（“数据尽量应该往OCR上的来靠”），标注数字先由读图员读。

**证据（只读，需要时拷到本工作树 `AI_agent/archive/local_backup/q1/`）：** 主树 `C:\Users\Horton\Desktop\EnergyPlus-Agent-dev\AI_agent\archive\local_backup\cmp3\` 下六个运行目录（交付稿、平面稿 `plan_drafts/*/plan.json`、分工的读图员试建）；评价脚本与参照用法见 `AI_agent/logs/experiments/2026-10-07_three_case_comparison/`（`evaluate.py`、`metrics.py`）；10-01 Opus 亲做三例与 Claude Code 较好结果的位置见 [A4-T 报告](../2026-10-05_absorb_a4t/README.md)。主树 `AI_agent/archive/local_backup/merged/` 与 D 盘 `runs-next`、`runs-cc` 是正在跑的整案，只读、不要动。

**设计要点（我的建议，你可按证据调整并写明理由）：**
- 规整做成编译前的独立一步（输入平面稿、输出规整后的平面稿与规整清单），`compile_plan_partition` 本身仍保持“不吸附”的严格编译，便于审计与重放；跨层对齐在装配时对各层平面稿做，再重新编译。
- 规则版本记在每份平面稿里：历史稿按当时规则重放、结果不变（run99 等历史重放检查照旧通过），新稿按新规则。
- 优先级的“按标注”标记由 F 写进平面稿（字段名由你定，写进 `plan_partition` 参考与验收报告），A、B 读它；外轮廓不动。
- 分工的墨线对齐与标注规整只在试建入口调用（“先只开给分工的平面读图员”），单模型的 `build_plan_bim` 不做 E、F，但照样经过 A–C。
- 硬约束的报错要让 3 档、4 档模型一次看懂：一句话说哪两条线、相距多少、多长、怎么改。

**要点：**
- 开工先在本目录写报告初稿 `README.md`，随进度更新；中途断了能从报告接上。
- **0 次模型请求**；Paratera 0，DeepSeek 0。真实效果由 Opus 合入后在 GLM 上实测（sm25 分工为主）。
- 环境：工作树根目录先 `uv sync --frozen --python 3.12`，再 `. .\scripts\activate_windows.ps1`，确认 `src.agent.__file__` 指向本工作树。pytest 显式 `-n 2`，`--basetemp` 放 `AI_agent/archive/local_backup/q1/pytest`。不跑全量。已知 `test_role_end_to_end.py::test_resume_reader_after_trial_checkpoint_does_not_repeat_trial` 机器忙时偶发失败，遇到时单独重跑并如实写。
- **文件归属（三包并行）：** 本包独占上面列的 kernel 文件、`bim_agent_precision.py`、`bim_agent_guidance.py`、`trial.py`、`readers.py`、`plan_format.py`、`plan_review.py`、`submission.py`，以及新建的规整、墨线对齐模块；`run_bim_agent.py` 只动 `Toolkit` 的建层、修改平面稿、装配三处及其返回（`subscription()` 归 V1）；`guidance.py` 只动平面读图员的几段（立面读图员与调度员的几段归 Q2）；交付报告与查看页显示规整清单可改 `scripts/tool_scripts/bim_agent_delivery_display.py`、`render_geometry_viewer.py` 的相关函数。**不改**：`elevation.py`、`assembly.py`、`assembly_review.py`、`session.py`、`height_*.py`（Q2）；`src/agent_runtime/` 与登记表（V1）。确需越界先在报告里说明、交我协调。
- 新检查要克制，只验行为，不锁指引原文和报错原文；被替换设计的旧检查直接删除或改写，不并存。写文本一律 LF；**沙箱下 `.git` 只读，不提交**，报告给出提交分组；交付前尽量删掉自己建的临时目录。
- 内部分工与子代理由你定（子代理优先 5.6 系列，报告写明型号与原因）。本包较大，可以先交 A–D（kernel 两种模式），再交 E–G（读图员），报告里分开写。

最终回复按验收 A–I 逐条给结果，附：规整前后的离线统计（三档）、被消除与被拒的项逐条清单、单模型交给模型的内容变了哪几处、指引字数前后对照、检查结果与建议的提交分组。
