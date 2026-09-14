# 相邻离线验证原始输出

```text
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /workspaces/EnergyPlus-Agent-dev
configfile: pyproject.toml
plugins: langsmith-0.7.33, xdist-3.8.0, anyio-4.13.0
collected 32 items

tests/test_bim_agent_tools.py .....................                      [ 65%]
tests/test_bim_agent_inputs.py ...                                       [ 75%]
tests/test_plan_partition.py ........                                    [100%]

F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
============================= 32 passed in 40.94s ==============================
```
