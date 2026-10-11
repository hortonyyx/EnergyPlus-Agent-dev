# 模型配置与能力边界

Work model 可按任务替换与组合，原则见 [模型约定](../workflow/models.md)。配置表达实际服务、型号、参数和保护线，不按五档标签决定建筑任务能力。

## 当前入口

`src/agent/runtime_configuration.py` 校验配置后生成或启动相应入口：

| mode | 入口 | 当前输入 |
|---|---|---|
| `single_model` | `src.agent.runtime_entry` | PNG 图像或 GLB |
| `role_division` | `src.agent.runtime_roles.entry` | 图纸 PNG |
| `external_coordinator_mcp` | `src.agent.runtime_coordinator` | 显式开发实验，由外部调度员协调 |

`check` 和 `command` 不调用模型；`launch` 才启动运行。产品通过 `sim_bim.py check/run` 使用同一配置，字段见 [配置示例](../../product/config.example.json) 与实际 CLI 帮助。

分工配置的 `roles` 绑定 coordinator、plan_reader、elevation_reader 的 provider、model、reasoning_effort、output_tokens 等参数，没有固定强弱组合。

## 三类配置

| 类别 | 内容 | 主要实现 |
|---|---|---|
| 服务连接 | 协议、端点、凭据、超时与限制 | `src/agent_runtime/providers.py` 与适配器 |
| 模型 profile | 型号、上下文/图片/输出限制、思考参数与价格来源 | `src/agent_runtime/estimation.py` 及配置 |
| 任务与角色 | 输入、目标、角色参数、并发、预算、目录 | `runtime_configuration.py`、`runtime_roles/config.py` |

官方声明、目录暴露和项目实测是不同证据。出现在目录不保证本地 profile、视觉、工具循环和任务质量均通过。

## 替换与验证

先核对服务兼容性与 profile，再做获准范围内的验证。按角色替换可以减少对照变量，但不强制逐级尝试每档。失败不自动转到未授权收费线路。

ChatGPT 授权与目录核验已完成，真实推理另验。GPT-6 Sol 标杆未启动，不以示例中的 GPT-6.1 Sol 冒充。新平台或本地服务按实际需要接入。

旧 `model_routes` / `llm.yaml` 仍供显式历史或兼容工具使用，不替代现行用户运行配置。旧原型记录见 [归档索引](../reports/archive-index.md)。
