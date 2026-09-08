# 接手验证（2026-09-08）

代码基点：`461dfc98`。本轮未修改业务代码、GT、测试或运行 skill。

## 离线接线回归

命令：

```bash
python -m pytest tests/test_w1_flow_routing.py tests/test_w3_chain_replay_lock.py tests/test_w7_as_drawn_windows.py -q -n 2
```

退出码 0，原始输出：

```text
bringing up nodes...
bringing up nodes...

.................................                                        [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
33 passed in 15.22s
```

## CLI

`python -m scripts.tool_scripts.run_stage --help` 与 `flow --help` 均退出 0；只读帮助，未跑新 case。

## 链接与差异

当前入口全文及56份参考文档新增状态说明共208个本地链接，缺失0。历史正文原有链接未宣称全部修复。
`git diff --check` 通过；相对整合代码的 src/scripts/tests/skills/pyproject.toml/uv.lock 差异为空。

## 恢复

完整 bundle 已通过 verify 和独立 clone。旧树移除前逐一比对 HEAD、tracked/staged diff、额外文件清单和字节。
工作树与分支收拢结果见[接手记录](../../worklog/2026-09-08_takeover.md)。

未做：全量 pytest、新冷启动 reading、计费模型调用、完整 IDF/EP case。
