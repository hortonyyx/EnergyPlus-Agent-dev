# 实现入口

当前结构与边界统一见 [architecture.md](architecture.md)，不再在本文件叠加逐日实现历史。

- 用户入口：`sim_bim.py` → `src/agent/product_cli.py`
- 运行配置：`src/agent/runtime_configuration.py`
- 单模型：`src/agent/runtime_entry.py`
- 分工：`src/agent/runtime_roles/entry.py`
- runtime：`src/agent_runtime`
- BIM工具：`scripts/tool_scripts/run_bim_agent.py`
- 当前 domain 职责与资源：[源码导航](../../src/agent/README.md)、[继承关系](domain_lineage.md)
- 显式历史流程：`src/agent/legacy/pipeline.py`、`graph.py`、`intake/`；当前 BIM 入口不执行其编号步骤
- 发布：`scripts/release/build_product.py`
- 检查选择：`scripts/dev/check.py`、`tests/check_groups.json`

历史实现说明保存在D盘归档和Git历史；当前状态见 [roadmap](../project/roadmap.md)。
