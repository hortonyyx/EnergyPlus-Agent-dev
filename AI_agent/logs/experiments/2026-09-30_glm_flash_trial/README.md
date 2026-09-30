# GLM Flash 独立试跑（2026-09-30）

用户要求先试 GLMFlash，不替代主开发。选 sm21，与 run98 使用完全相同的六张原图、任务、系统指引、44 个生产文件和预算；仅调用通道与工作模型改为现有 GLM 订阅的 `glm-5.3-flash`。单次冷启动，3000 秒，最多 24 个候选，无续接、委派、自动重试或付费 API 回退。

`trial.py prepare` 在进程启动边界阻断模型调用，核对原图、完整提示、生产文件和实际 MCP 工具；`trial.py run` 只启动批准的独立目录一次。`preflight.json` 保存准备证据，运行目录保存请求、回执、输出和生产代码快照。现有 Sonnet run99–103 编号及审批保持原样，结果不作为模型切换或稳定性结论。

实验脚本不重试；Claude CLI 内部的请求重试不受本脚本控制。与 run98 一致，禁委派写在任务中，`review_detail` 仍暴露，生成结束后检查是否实际调用。

工作树缺少私有 `.env`，本地仅建立指向主工作树 `.env` 的忽略链接供现有订阅启动脚本读取；密钥不进入记录或 Git。CLI 版本为本机已核对的 `2.1.284 (Claude Code)`。

评估在生成结束后使用现有 sm21 原图/GT 对应核验及 run98 的房间一一对应、外部门窗高度 5 cm 标准。GT 不传给生成模型。CLI 金额仅为客户端估计，不是订阅账单。

`audit_sm21.py` 复制自 `2026-09-27_sm21_current_tools_setup/audit_run.py`，仅将订阅回执断言改为 GLM/Flash，并移除与旧 run58 的任务比较尾段；评分函数和参考数据不变。`evaluate.py` 复用 `instruction_fix/evaluate.py` 的行为、房间和高度检查，独立写 `trial_evaluation.json` 及与 run98 的 `comparison.json`，不伪装 Claude 回执。
