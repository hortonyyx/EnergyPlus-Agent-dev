# Sim BIM Agent — 开发仓库

从图纸、文字和带贴图三维网格生成可查看、可修改、可供下游分析使用的轻量 BIM。当前主线是自有 runtime 的图纸分工建模；EnergyPlus 是可选下游。稳定识读质量、完整编辑界面与真实 ChatGPT 订阅接通仍有独立验收边界。

本仓库位于 `D:\Sim-BIM-Agent\repo`。桌面 `Sim BIM Agent` 是从固定提交生成的独立发布目录。日常在本仓库开发，验证后发布；不在桌面交付目录累计开发历史。

## 开始开发

读取 [Agent.md](AI_agent/Agent.md) 与 [当前任务](AI_agent/project/roadmap.md)，其余按任务查阅。用户操作说明在 [产品 README](product/README.md)。

```powershell
. ./scripts/activate_windows.ps1
python scripts/dev/check.py
python scripts/dev/check.py --help
python -m src.agent_runtime.agent_registry verify
python scripts/release/build_product.py D:/Sim-BIM-Agent/releases/<版本名>
```

测试选择按 [开发方式](AI_agent/workflow/development.md)；普通检查不调用真实模型。发布前提交程序改动并登记实际变化的 runtime/domain 版本。发布目录内执行 `setup.ps1` 建立运行环境，再运行 `Start.cmd doctor`。

## 目录

| 目录 | 内容 |
|---|---|
| src/agent_runtime、src/harness_contracts | runtime 和公共运行契约 |
| src/agent、scripts/tool_scripts | domain、BIM 工具、指引和查看器 |
| tests | 当前有效检查、小夹具及显式选择的历史检查源码 |
| product、scripts/release | 用户说明、配置、启动入口与发布生成 |
| AI_agent | 当前目标、设计、操作规则和本轮简短记录 |

完整案例在 `D:\Sim-BIM-Agent\cases`，运行在 `runs`，历史证据在 `archive`，临时产物在 `cache`。GT 只供独立评价，不能作为 work model 的输入。Git 保留旧提交；历史资料迁移清单在 archive，不将完整运行目录复制回主线。
