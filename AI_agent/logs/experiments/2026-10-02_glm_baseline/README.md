# 10-02 GLM Flash 在冻结基准上的换例基线（sm24、sm25）

用户：“在基座开发过程中你可以先调GLM的flash档位继续调整agent……可以结合我们的历史测试先继续用Claude code接GLM把agent开发部分推进一下”。工作模型改用 GLM Flash 后，sm21 只有 09-30 的一次结果，sm24、sm25 还没有。先在当前主线（代码即冻结基准 `5bb10538`）上各跑一次冷启动，作为后续改进的对照，再据实际失败安排工具改进包。

## 条件

- 接入方式：Claude Code + 现有 GLM 订阅，`glm-5.3-flash`（运行器 `--provider glm`）。
- 与 09-30 指引修复批次（run98–101）相同：任务说明、系统提示、参考资料、3000 秒、最多 24 个候选、思考档 medium、任务中禁止委派、无续查。
- 准备（`baseline.py prepare`，0 次模型调用）：sm24 的任务说明、系统提示和原图与 Sonnet run100 逐字节相同。工具由 09-30 GLM 试跑时的 39 个变为 42 个；与 run100 相比有 7 个实现文件不同，都来自合入主线的部分推理改动（`bim_agent_guidance.py`、`bim_agent_inference.py`、`render_geometry_viewer.py`、`run_bim_agent.py`、`parametric_proposal.py`、`proposal_edits.py`、`source_naming.py`）。见 `preflight_glm_sm24.json`、`preflight_glm_sm25.json`。
- 顺序执行，一次调用；上一次未正常结束就停，不重试（[批准记录](approval.json)）。

## 结果

待运行结束后补充。
