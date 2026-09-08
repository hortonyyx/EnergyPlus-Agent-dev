# EnergyPlus Agent：多模态输入与轻量 BIM

这个仓库研究如何把图纸、文字参数、带表皮体量以及后续 CAD 等混合输入，转成可查看的轻量 BIM，并复用既有 IntakeOutput → IDF → EnergyPlus 链路。
模型精度由输入证据决定；缺失信息通过明确标注的假设和简化处理。
轻量 BIM 是通用核心产物，EnergyPlus 是首个下游插件；我方主线为几何，物性挂接由协作者负责，完整目标见 [产品范围](AI_agent/project_scope.md)。

目前主要实现是图纸路线。两路统一入口尚未完成，最新 sm25 case 已到几何建模阶段，后续仍有阻塞，不能视为端到端已跑通。

## 从这里接手

- [Agent.md](AI_agent/Agent.md)：所有开发助手共同约定，含 Git 授权与“收工”动作。
- [产品范围](AI_agent/project_scope.md) / [模型使用约定](AI_agent/guides/model_usage.md)：包含已从 Codex 本地记忆同步的用户约定。
- [项目说明](AI_agent/README.md) / [当前计划](AI_agent/plan.md)：目标、代码位置、已完成与下一步。
- [当前架构](AI_agent/architecture/pipeline_stage_contracts.md) / [两路融合建议](AI_agent/architecture/multimodal_bim.md)。
- [case 操作](AI_agent/guides/new_case_guide.md) / [开发手册](AI_agent/guides/development.md)。
- [2026-09-08 存档与接手记录](AI_agent/logs/worklog/2026-09-08_takeover.md)。

## 运行环境与入口

使用 [VS Code Dev Container](.devcontainer/README.md) 中配置好的 Python 和 EnergyPlus 环境。
模型凭据放本地 `.env`，配置示例见 [.env.example](.env.example)，不要提交密钥。

```bash
python -m scripts.tool_scripts.run_stage --help
python -m scripts.tool_scripts.run_stage flow --help
```

case CLI 位于 [run_stage.py](scripts/tool_scripts/run_stage.py)，MCP 入口为 [main.py](main.py)。
既有下游实现、转换器、RAG 和工具仍在仓库，可按任务复用；[旧版 README](AI_agent/archive/2026-09-08_pre_takeover/repository_README.md) 仅供历史安装/API 说明查询。

## 主要目录

| 路径 | 用途 |
|---|---|
| `src/agent/` | 输入感知、校正、几何、评测与下游代理链 |
| `src/validator/` | 模型及交接验证 |
| `src/mcp/` / `src/converters/` | MCP 服务和 IDF 转换工具 |
| `scripts/` / `skills/` | 可复用入口、工具与运行规范 |
| `case_tests/` / `tests/` | case 素材/产物与代码测试 |
| `AI_agent/` | 当前管理入口、技术参考与历史记录 |
| `backup/` | 本地恢复副本，不作为远端公开材料 |

主干为 `main`。当前优先级是跑出真实模型，再按结果改进；不把维护脚手架当作研发目标。
