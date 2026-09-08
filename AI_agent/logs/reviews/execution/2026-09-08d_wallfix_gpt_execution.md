# 2026-09-08d · GPT 接手停报：uv 自动同步与共享环境禁写冲突

状态：**停下上报，尚未进入四项修复；本文件不是完成验收报告。**

## 题面与实际

你以为指定的 `PYTHONPATH=/tmp/w1_flow_glm uv run ...` 可以同时满足
“跑测”和“禁止任何写 site-packages 的命令”；实际是当前环境下普通
`uv run` 会自动同步共享 `/opt/venv`，导入自检已经触发一次卸载和安装。

这是执行命令与硬约束的冲突，未自行改用另一种命令继续跑全量。

## 已执行与证据

- 已读派工单 `AI_agent/logs/reviews/request/2026-09-08c_wallhunt_fix_dispatch.md`
  和题面 `AI_agent/logs/experiments/2026-09-08b_wallhunt/README.md`。
- 始终在 `/tmp/w1_flow_glm`；分支 `wt/09.07h_w1_flow`，接手 HEAD 为
  `5839a85c`，所列前序 W#3 / W#6 提交均在历史中。
- 接手时只有未跟踪的 `case_tests/e2e_tests/sm25-L_anchor/run_wallhunt/`，
  暂存区与已跟踪文件均无改动；该目录未修改、未暂存。
- 执行的导入自检：

  ```bash
  PYTHONPATH=/tmp/w1_flow_glm uv run python -c 'import pathlib, src.agent; p = pathlib.Path(src.agent.__file__).resolve(); print(p); assert p.is_relative_to(pathlib.Path("/tmp/w1_flow_glm"))'
  ```

  实际输出：

  ```text
  Uninstalled 1 package in 2ms
  Installed 1 package in 10ms
  /tmp/w1_flow_glm/src/agent/__init__.py
  ```

- 只读核实：本树无 `.venv`；环境变量 `UV_PROJECT_ENVIRONMENT` 与
  `VIRTUAL_ENV` 均为 `/opt/venv`。
- `/opt/venv/lib/python3.12/site-packages/energyplus_agent-0.1.0.dist-info/direct_url.json`
  当前内容为：

  ```json
  {"url":"file:///tmp/w1_flow_glm","dir_info":{"editable":true}}
  ```

自检导入路径正确，但自检发生了不应发生的共享环境同步。未读取同步前的
安装记录，不能声称知道之前指向哪棵树；未尝试修改共享环境恢复它。

## 待派工方裁决的命令修订

建议显式禁用 uv 同步，并在后续每条 uv 跑测/flow 命令中保持该设置：

```bash
cd /tmp/w1_flow_glm
export UV_NO_SYNC=1
export PYTHONPATH=/tmp/w1_flow_glm
uv run python -c 'import pathlib, src.agent; p = pathlib.Path(src.agent.__file__).resolve(); print(p); assert p.is_relative_to(pathlib.Path("/tmp/w1_flow_glm"))'
uv run pytest -n 6 -q
```

上面是**待裁决的建议，尚未执行**。flow 凭据来源仍按用户指定：

```bash
set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a
```

不复制、不提交、不输出 `.env` 内容。完整 flow 命令序列须在恢复施工并
核实入口后补齐，此处不是端到端可重跑交付。

## 未完成范围

全量基线尚未启动；W#1（含格式检查对照表）、W#4、W#5、W#2 的完整
重跑说明均未完成。没有生产代码变更；W#3 / W#6 未重做，W#7 和窗相关
内容未修改。

## 我这次最薄弱的一处

我在导入自检前没有先检查 uv 的共享环境和自动同步设置，导致自检命令
已触发共享环境写入；应先发现这一冲突再执行 uv。
