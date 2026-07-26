# 执行日志：测试提速 + 受影响测试映射（2026-07-26）

施工方：GPT 侧执行档  
施工契约：`AI_agent/logs/reviews/request/2026-07-26_test_speedup_and_affected_map_dispatch.md`

## A1/A2 实施（主控裁定通过）

- `pyproject.toml`：开发依赖新增 `pytest-xdist>=3.8`；pytest 默认参数新增 `-n auto --dist load`。
- `uv lock`：仅新增 `pytest-xdist 3.8.0` 和唯一依赖 `execnet 2.1.2`，无其他包变更。
- `tests/test_gt_promotion_path.py:504`：嵌套 pytest 命令显式新增 `-n0`。

## A4 验收命令与结果

```text
串行：python -m pytest -p no:cacheprovider -q -n0 -rA
并行 1：python -m pytest -p no:cacheprovider -q -rA
并行 2：python -m pytest -p no:cacheprovider -q -rA

墙钟（shell time -p）：
serial = 904.31s
par1   = 258.68s
par2   = 285.62s
```

三次 pytest 汇总尾部（原样保留）：

```text
serial: 1656 passed, 10 xfailed, 150 warnings in 902.42s (0:15:02)
par1:   1656 passed, 10 xfailed, 150 warnings in 257.78s (0:04:17)
par2:   1656 passed, 10 xfailed, 150 warnings in 284.64s (0:04:44)
```

逐节点严格比对（从每份 `-rA` 输出抽取 `^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) <nodeid>`，排序去重）：

```text
wc -l /tmp/2026-07-26_a_{serial,par1,par2}.nodes
  1666 /tmp/2026-07-26_a_serial.nodes
  1666 /tmp/2026-07-26_a_par1.nodes
  1666 /tmp/2026-07-26_a_par2.nodes
  4998 total

diff -u /tmp/2026-07-26_a_serial.nodes /tmp/2026-07-26_a_par1.nodes
diff -u /tmp/2026-07-26_a_serial.nodes /tmp/2026-07-26_a_par2.nodes
diff -u /tmp/2026-07-26_a_par1.nodes /tmp/2026-07-26_a_par2.nodes
```

三条 `diff` 均为空输出、exit 0。审阅方可按以上命令重跑即可自证；原始 stdout 不入库。审阅期内三份原始文件保留在 `/tmp/2026-07-26_a_{serial,par1,par2}.txt`。

子进程单进程证据：并行第 1 轮中，实际运行的嵌套进程为：

```text
/opt/venv/bin/python -m pytest -q -p no:cacheprovider -n0 -m not mutation tests/test_gt_promotion_path.py
```

因此子进程命令已实际携带 `-n0`，覆盖父进程的默认 `-n auto`；其捕获输出未出现 xdist worker 启动标记。

每轮后 `git status --porcelain=v1`：仅本批三个生产改动，以及用户放入的未跟踪派工单；运行未产生额外仓库副作用。执行日志本文件属于派工单允许的唯一 `AI_agent/` 写入。

## B 阶段进展

### B1–B5（已完成首轮）

- 新增 `scripts/tool_scripts/affected_tests.py`：以 AST import 边、相对导入、字符串路径边建立确定性传递闭包；输出 `SCOPE: FULL` / `SCOPE: SUBSET`、可粘贴 pytest 命令、跑测声明和 `--explain` 链。
- 新增 `scripts/tool_scripts/affected_tests_rules.yaml`：列出全仓触发器及 38 项当前真实未覆盖生产模块（每项附原因）。
- 新增 `tests/test_affected_tests_map.py`：已锁确定性、具体 tarch import 选集、真实间接 import 链、字符串路径边、四条 fail-closed、覆盖门和 `--since` 口径。
- 中间测试：`python -m pytest -p no:cacheprovider -q -n0 tests/test_affected_tests_map.py` → `10 passed in 22.98s`。

事实注记：`tests/test_gt_from_dxf.py` 除 subprocess 字符串路径外还实际 `from scripts.tool_scripts import gt_from_dxf as gfd`。因此删掉字符串扫描时，该测试仍会由 import 边选中；字符串锁改为直接断言该字符串边存在，后续 neuter 将据此实跑。该项与派工单“该耦合只存在于字符串 + subprocess”的描述不符，将在交付风险中照实披露。

### B6 neuter 自查表（已实跑并均已还原）

| 锁 | 临时 neuter | 实跑结果 | 只红对应锁 |
| --- | --- | --- | --- |
| 确定性 | `tuple(sorted(selected))` → `tuple(selected)` | `test_deterministic_output_and_cli_contract` 失败；其余 9 通过 | 是 |
| 真 import 边 | 不解析 `from pkg import module` 的 alias 子模块 | `test_tarch_import_edges_select_the_locked_tests` 失败；其余 9 通过 | 是 |
| 传递边 | `find_path` 禁止第二跳及以后（只跑对应测试） | `test_transitive_import_edge_is_not_a_direct_edge` 失败 | 是（目标测试单独实跑；完整覆盖门也依赖传递闭包） |
| 字符串路径边 | `elif isinstance(node, ast.Constant) and isinstance(node.value, str):` → `elif False` | `test_string_path_edge_is_recorded_for_gt_from_dxf`、`test_pure_string_path_subprocess_edge_selects_cv_toolbox`、B5 覆盖门失败；其余 8 通过 | 否：已有直接边断言与 B5 覆盖门也正确依赖同一机制，诚实记录 |
| fail-closed：非一等公民 | 跳过 `path not in file_set` 检查 | 对应 fail-closed 测试失败；其余 9 通过 | 是 |
| fail-closed：全仓触发器 | 跳过规则表触发器检查 | 对应 fail-closed 测试失败；其余 9 通过 | 是 |
| fail-closed：删除 | 跳过磁盘存在性检查 | 对应 fail-closed 测试失败；其余 9 通过 | 是 |
| fail-closed：规则表坏掉 | 不捕获 `yaml.YAMLError` | 对应 fail-closed 测试错误；其余 9 通过 | 是 |
| B5 覆盖门 | 删除 `_grade_transform.py` 的 allowlist 项 | `test_every_production_module_is_mapped_or_honestly_allowlisted` 失败；其余 9 通过 | 是 |

neuter 后每次立即还原；还原后的中间回归：`10 passed in 22.14s`。

### B7 实际子集数据（默认并行）

`--explain` 样例（`src/agent/judge/tarch_normalize.py`）：

```text
SCOPE: SUBSET
python -m pytest -p no:cacheprovider -q tests/test_affected_tests_map.py tests/test_gt_from_dxf.py tests/test_gt_overlay.py tests/test_gt_promotion_path.py tests/test_tarch_converter_gate_mutations.py tests/test_tarch_converter_p1_geometry.py tests/test_tarch_converter_p2_geometry.py tests/test_tarch_converter_reproducibility.py tests/test_tarch_elevation_must_red.py
跑测声明：受影响子集 = tests/test_affected_tests_map.py tests/test_gt_from_dxf.py tests/test_gt_overlay.py tests/test_gt_promotion_path.py tests/test_tarch_converter_gate_mutations.py tests/test_tarch_converter_p1_geometry.py tests/test_tarch_converter_p2_geometry.py tests/test_tarch_converter_reproducibility.py tests/test_tarch_elevation_must_red.py（依据 affected_tests.py --changed src/agent/judge/tarch_normalize.py）
EXPLAIN: tests/test_gt_from_dxf.py: tests/test_gt_from_dxf.py --import--> src/agent/judge/tarch_normalize.py
EXPLAIN: tests/test_tarch_converter_p1_geometry.py: tests/test_tarch_converter_p1_geometry.py --import--> src/agent/judge/tarch_normalize.py
```

| 改动输入 | 选中测试文件数 | 实跑结果 / pytest 墙钟 |
| --- | ---: | --- |
| `src/agent/judge/tarch_normalize.py` | 9 | `216 passed, 1 xfailed`，125.06s |
| `src/agent/pipeline.py` | 86 | `1608 passed, 10 xfailed`，255.37s |
| `scripts/tool_scripts/run_stage.py` | 6 | `74 passed`，21.54s |

对照 A 的全仓 257.78s：`run_stage.py` 子集有明显收益；`pipeline.py` 因共享依赖和字符串路径闭包几乎等于全仓，工具如实报告而不假装提速。

## 续批：E4 输入侧隔离与字符串边诚实性复查

### E4 并行根因修复（主控明确授权的既有测试例外）

`tests/test_e4_relative_north_axis_e2e.py::ep_outputs` 现在对每个 variant：

1. 在该 variant 自己的 `tmp_path_factory` 目录复制 `_PROBE/<variant>.idf`；
2. 将 EnergyPlus 的 `cwd` 设为该专属目录，并把这份副本传给 EnergyPlus；
3. 继续把输出写在同一 `tmp_path_factory` 根下的 `output/`。

第二步是实跑确认所必需的输入侧隔离：仅传入绝对副本路径、仍保留仓库工作目录为 cwd 时，EP 仍会相撞 `in.idf`；将 cwd 定在副本所在的 variant 目录后，临时链接只能在该隔离目录创建。没有改动此文件任何断言、容差、skip 条件或 114 面 / 14 区等期望值。

模块单独默认并行两轮（原始 stdout 留在 `/tmp`）：

```text
python -m pytest -p no:cacheprovider -q -rA tests/test_e4_relative_north_axis_e2e.py

轮 1: 8 passed in 6.72s；shell time -p real 7.39s
轮 2: 8 passed in 6.75s；shell time -p real 7.37s
```

`_PROBE/in.idf` 观察方式：第 1 轮在 pytest/七个并行 EnergyPlus 进程仍存活时执行：

```text
ps -eo pid,ppid,stat,etime,args | rg 'pytest.*test_e4_relative_north_axis_e2e.py|EnergyPlus'
find AI_agent/logs/experiments/2026-07-10_e4_relative_north_axis_probe -maxdepth 1 -name in.idf -print
```

`ps` 显示七个 EnergyPlus 命令均使用各自的 `/tmp/pytest-of-root/.../popen-gw*/e4_ep0/world_000/world_000.idf` 输入；紧随其后的 `find` 无输出。轮后再次 `find` 也无输出。代价：xdist 让模块级 fixture 在 7 个分到参数的 worker 上重复执行 EnergyPlus；该模块墙钟约 7.4 秒（CPU 时间约 54 秒）。

### B 字符串/subprocess 边复查与新增锁

仓库**存在**真正没有 import 边的字符串/subprocess 耦合：`tests/test_cv_toolbox.py` 的两个端到端用例以 `subprocess.run([sys.executable, "scripts/tool_scripts/cv_probe.py", ...])` 调用 `scripts/tool_scripts/cv_probe.py`。`build_edges` 实查该对存在 `string-path` 边而不存在 `import` 边。

保留原 `gt_from_dxf` 字符串边直接断言，并新增 `test_pure_string_path_subprocess_edge_selects_cv_toolbox`：改 `cv_probe.py` 时必须选中 `test_cv_toolbox.py`，且明确断言没有同对 import 边。因此字符串扫描是当前仓库中的承重机制，而非仅前瞻性防护。

还原后映射测试：`python -m pytest -p no:cacheprovider -q -n0 tests/test_affected_tests_map.py` → `11 passed in 23.04s`。

新增锁的 neuter 实跑（已立即还原）：把 `affected_tests.py` 的
`elif isinstance(node, ast.Constant) and isinstance(node.value, str):`
临时改为 `elif False`。结果：

```text
FAILED test_string_path_edge_is_recorded_for_gt_from_dxf
FAILED test_pure_string_path_subprocess_edge_selects_cv_toolbox
FAILED test_every_production_module_is_mapped_or_honestly_allowlisted
3 failed, 8 passed in 17.73s
```

新的纯字符串锁必红；另两条同样依赖字符串边（已有直接边断言及 B5 覆盖门），故不是“只红对应锁”，此共享依赖已明确披露。

### 交付前全仓（三轮；E4 修复后）

后台重定向的原始 stdout 保留于 `/tmp/2026-07-26_final_{serial,par1,par2}.txt`，未写入仓库；每轮都用 `-rA`，因此可抽取逐节点状态。

```text
串行：python -m pytest -p no:cacheprovider -q -n0 -rA
并行 1：python -m pytest -p no:cacheprovider -q -rA
并行 2：python -m pytest -p no:cacheprovider -q -rA

serial: 1667 passed, 10 xfailed, 150 warnings in 870.08s (0:14:30)
        shell time -p real 871.88s
par1:   1667 passed, 10 xfailed, 150 warnings in 260.47s (0:04:20)
        shell time -p real 261.36s
par2:   1667 passed, 10 xfailed, 150 warnings in 266.89s (0:04:26)
        shell time -p real 267.94s
```

计数为原始 `1656 passed` 加本批 `tests/test_affected_tests_map.py` 的 11 条新增测试，再加既有 10 xfailed；三轮均零 failed / error。

逐节点集合严格比对：

```text
rg '^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) ' /tmp/2026-07-26_final_serial.txt | sort -u > /tmp/2026-07-26_final_serial.nodes
rg '^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) ' /tmp/2026-07-26_final_par1.txt | sort -u > /tmp/2026-07-26_final_par1.nodes
rg '^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) ' /tmp/2026-07-26_final_par2.txt | sort -u > /tmp/2026-07-26_final_par2.nodes

wc -l /tmp/2026-07-26_final_{serial,par1,par2}.nodes
  1677 /tmp/2026-07-26_final_serial.nodes
  1677 /tmp/2026-07-26_final_par1.nodes
  1677 /tmp/2026-07-26_final_par2.nodes
  5031 total

diff -u /tmp/2026-07-26_final_serial.nodes /tmp/2026-07-26_final_par1.nodes
diff -u /tmp/2026-07-26_final_serial.nodes /tmp/2026-07-26_final_par2.nodes
diff -u /tmp/2026-07-26_final_par1.nodes /tmp/2026-07-26_final_par2.nodes
```

三条 `diff` 均为**空输出、exit 0**：三份节点集合逐字节相等。

## 续批返工（主控轻门 r1：F1–F4，已完成）

### F1：仓库根 Python 入口纳入图

- `first_class_files()` 现额外纳入仓库根的 top-level `*.py`（当前为
  `main.py`）；模块解析也接受这类根模块。
- 新锁 `test_root_entrypoint_string_path_reaches_mcp_server` 固定链：
  `tests/test_mcp_stdio.py --string-path--> main.py --import--> src/mcp/server.py`。
  因而修改 `src/mcp/server.py` 必须选中 `tests/test_mcp_stdio.py`。
- 重算白名单后删除了 14 个已覆盖条目：全部 `src/mcp/**` 条目与
  `src/rag/{chunk,embedding,rag,vector}.py`；`main.py` 的函数内 lazy import
  同样由 AST 遍历计入边。

### F2/F3：空子集 fail-closed 与双向覆盖门

- 若第一等公民模块没有任何可达测试，映射现返回 `SCOPE: FULL`，并给出
  `changed first-class module has no covering test` 原因；不再打印与“无测试文件”
  自相矛盾的裸 pytest 全仓命令。锁使用仍在 allowlist 的
  `scripts/tool_scripts/baseline_record.py`。
- B5 覆盖门现为精确相等：`uncovered == set(uncovered_allowlist)`；它既拒绝未
  列出的真实未覆盖模块，也拒绝已覆盖却遗留的过期条目。

### F4：MCP stdio 启动容差（主控明确授权）

`tests/test_mcp_stdio.py` 的 `subprocess.run(..., timeout=10)` 已改为
`timeout=120`。两条契约断言 `result.returncode == 0` 和 `result.stdout == ""`
未改，未加入 skip/retry/xfail/标记。这是主控授权的机器负载容差放宽：上一轮
三连中串行已完成 `1667 passed`，但并行第 1 轮在 gw12 出现
`subprocess.TimeoutExpired ... timed out after 10 seconds`，当轮为 `1 failed`，
并行第 2 轮因此未启动。根因是 16 个外层 worker 与变异矩阵的嵌套子 pytest
同时抢占机器，使 MCP server 启动超过了隐含的 10 秒机器速度假设；测试契约并
不是十秒启动。嵌套子 pytest 已保持显式 `-n0`，避免每个子进程再派生 xdist
worker；它们仍是额外进程，故此前确实观察到进程超订压力。

### 新锁的 neuter 自查（均已还原）

| 锁 | 临时 neuter / 控制 | 实跑结果 |
| --- | --- | --- |
| F1 根入口链 | 将 `for candidate in root.glob("*.py")` 改为 `for candidate in ()` | 仅 `test_root_entrypoint_string_path_reaches_mcp_server` 失败：`tests/test_mcp_stdio.py` 不再被选中；其余图仍可构建。 |
| F2 空集转全仓 | 将 `if not selected:` 改为 `if False:` | 仅 `test_uncovered_first_class_module_falls_back_to_full_scope` 失败（得到 `SUBSET`）。 |
| F3 allowlist 反向门 | 控制性地临时把已覆盖的 `src/mcp/server.py` 放回 allowlist | 完整双向断言使 `test_every_production_module_is_mapped_or_honestly_allowlisted` 失败（right set extra）；把断言 neuter 回旧的单向 `not uncovered - allowlist` 后，同一控制转为通过。随后同时还原。 |

还原后定向回归：

```text
python -m pytest -p no:cacheprovider -q -n0 -rA tests/test_affected_tests_map.py
13 passed in 51.58s

python -m pytest -p no:cacheprovider -q -n0 -rA tests/test_mcp_stdio.py
1 passed in 7.85s
```

F1/F2 实际 CLI 样例：

```text
$ python scripts/tool_scripts/affected_tests.py --changed src/mcp/server.py --explain
SCOPE: SUBSET
python -m pytest -p no:cacheprovider -q tests/test_affected_tests_map.py tests/test_mcp_stdio.py
EXPLAIN: tests/test_mcp_stdio.py: tests/test_mcp_stdio.py --string-path--> main.py ; main.py --import--> src/mcp/server.py

$ python scripts/tool_scripts/affected_tests.py --changed scripts/tool_scripts/baseline_record.py
SCOPE: FULL
python -m pytest -p no:cacheprovider -q
跑测声明：受影响子集 = 全仓（…原因：changed first-class module has no covering test: scripts/tool_scripts/baseline_record.py）
```

### 交付前三次跑（最终态）

原始 stdout 仍只留在 `/tmp/2026-07-26_d_{serial,par1,par2}.txt`，不入库。

```text
serial: python -m pytest -p no:cacheprovider -q -n0 -rA
        1669 passed, 10 xfailed, 150 warnings in 1559.70s (0:25:59)
        shell wall 1573.65s
par1:   python -m pytest -p no:cacheprovider -q -rA
        1669 passed, 10 xfailed, 150 warnings in 480.17s (0:08:00)
        shell wall 486.38s
par2:   python -m pytest -p no:cacheprovider -q -rA
        1669 passed, 10 xfailed, 150 warnings in 441.80s (0:07:21)
        shell wall 460.11s
```

三次均为零 failed / 零 error。节点集合按以下命令抽取后，三个文件均 1679 行；
随后三条 `diff -u` 都为空输出、exit 0。

```text
rg '^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) ' /tmp/2026-07-26_d_serial.txt | sort -u > /tmp/2026-07-26_d_serial.nodes
rg '^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) ' /tmp/2026-07-26_d_par1.txt | sort -u > /tmp/2026-07-26_d_par1.nodes
rg '^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) ' /tmp/2026-07-26_d_par2.txt | sort -u > /tmp/2026-07-26_d_par2.nodes

wc -l /tmp/2026-07-26_d_serial.nodes /tmp/2026-07-26_d_par1.nodes /tmp/2026-07-26_d_par2.nodes
  1679 /tmp/2026-07-26_d_serial.nodes
  1679 /tmp/2026-07-26_d_par1.nodes
  1679 /tmp/2026-07-26_d_par2.nodes
  5037 total
```

`-n auto` 在本机 16 个逻辑处理器上实际拉取 16 个 xdist worker；本轮并行已稳定
通过。前述上一轮的超订现象仍如实保留：`-n0` 消除了嵌套 pytest 的 worker 倍增，
但外层 worker 与单进程子 pytest 同时存在，仍会增加调度压力。

## 返工 r2：映射锁加固、可收集目标过滤与字符串边方向约束

### R-01 — DONE：`--since` 锁自造已提交与未提交证据

`test_since_uses_committed_range_only` 现在在 `tmp_path` 初始化独立 Git 仓库：先
提交 `baseline.py`，记录基点；再提交 `committed.py`；最后只修改已跟踪的
`baseline.py` 而不提交。锁断言 `changed_since(base)` **仅**返回
`["committed.py"]`，所以不再依赖本仓工作树是否刚好脏着。

### R-02 — DONE：只输出 pytest 会收集的目标，helper 仍是图节点

- 图仍遍历所有 `tests/` Python 文件，故 `test → helper → src` 边不被删除；选择
  输出则只接受 basename 为 `test_*.py` 的节点。
- 新锁对 `src/agent/pipeline.py` 的 `SUBSET` 输出断言不含
  `tests/b4b_contract_fixture.py` 与 `tests/b5_test_helpers.py`，且每个输出目标都
  是 `test_*.py`；同时直接锁住
  `test_c2_b4b_phase_b.py → b4b_contract_fixture.py → facade_visibility.py` 两条图边。
- 实际 CLI 声明（`affected_tests.py --changed src/agent/pipeline.py`）仅列出可收集
  测试文件；不再产生 helper 目标或空 pytest 命令。若没有可收集测试，既有
  `changed first-class module has no covering test` 的 FULL 回落仍生效。

### R-03 — DONE：登记 `resources.files` 动态盲区

规则表头部已登记带点分模块名的 `resources.files` 动态耦合为静态图已知盲区：其
后果是 no-cover allowlist 较宽，但映射 fail-closed 回落全仓、不会漏跑。
`isolation_templates/guard.py` 与 `run_cv_probe.py` 两条理由均已明确：它们由
`resources.files` 动态注入 staging，`test_isolation` 在隔离 staging 中执行副本，
静态图不能捕获，故 no-cover 兜底 FULL。

### R-04 — PARTIAL：方向约束与 `cv_probe` 收缩完成；`pipeline` 未见预期下降

前置证据：执行

```text
rg -n -i --glob '*.py' '(subprocess\\.(run|Popen|call|check_call|check_output)|\\bopen\\(|\\.read_text\\(|importlib\\.(import_module|resources)|__import__\\()' src scripts | rg 'tests/'
```

无输出；未发现生产模块真实读取或执行 `tests/` 文件的例外。

字符串路径边现只允许 `tests/` 目标由 `tests/` 来源建立，保留测试到 helper 的
传递、切断生产字符串注释/文档到测试节点的伪桥。新增锁固定
`src/agent/judge/gt.py → tests/test_gt_discipline.py` 的字符串边不存在，且
`cv_probe.py` 仍选中真正的 `test_cv_toolbox.py`，不再通过该桥选中
`test_gt_from_dxf.py`。

实测可收集测试数（同一当前工作树）：

| changed path | 方向约束关闭 | 方向约束开启 |
| --- | ---: | ---: |
| `scripts/tool_scripts/cv_probe.py` | 85 | 3 |
| `src/agent/judge/gt.py` | 85 | 29 |
| `src/validator/schedules.py` | 86 | 86 |
| `src/agent/pipeline.py` | 85 | 85 |

因此实现了派工单指定的方向规则、`cv_probe.py` 显著缩至个位数，覆盖门与既有五条
fail-closed 锁仍通过；但 `pipeline.py` 在过滤后的口径下没有明显下降，未硬凑为
DONE，交主控复核真实依赖团。

### R-05 — DONE：两处死包装清理

- `package_for_path` 合并为单一 `parts.pop()`。
- 传递链锁移除无意义的一次元素推导式，直接断言路径长度。

### 中间回归与 neuter 自查表（全部仅在 `/tmp` 副本实跑）

正常态映射测试：

```text
python -m pytest -p no:cacheprovider -q -n0 -rA tests/test_affected_tests_map.py
15 passed in 48.45s
```

三个临时副本均从当前工作树复制并补齐只读根入口；临时改动从未进入工作树。

| 新锁 | `/tmp` neuter：改哪一行/改成什么 | 变红用例 | 全组实跑；是否只红该条 |
| --- | --- | --- | --- |
| R-01 三点 Git 范围 | `changed_since`: `f"{ref}...HEAD"` → `ref` | `test_since_uses_committed_range_only` | `1 failed, 14 passed in 27.73s`；是 |
| R-02 可收集过滤 | `runnable_tests = tuple(... name.startswith("test_"))` → `runnable_tests = test_nodes` | `test_subset_contains_only_runnable_test_files_and_keeps_helper_transit` | `1 failed, 14 passed in 26.19s`；是 |
| R-04 生产→测试字符串桥 | `target in node.value and not (target.startswith("tests/") and not source.startswith("tests/"))` → `target in node.value` | `test_production_string_paths_cannot_bridge_through_test_nodes` | `1 failed, 14 passed in 26.20s`；是 |

### 交付前全仓（默认并行）

原始 stdout：`/tmp/2026-07-26_r2_full.txt`。命令：

```text
python -m pytest -p no:cacheprovider -q -rA
```

原始输出尾部：

```text
XFAIL tests/test_tarch_converter_p2_geometry.py::test_free_end_non_zoning_with_proof_deferred - §2.6 free-end non_zoning proof path is deferred; current S4 blocks every dangle fail-closed
XFAIL tests/test_orchestrate_baseline.py::test_record_baseline_on_anchor - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_optional_policy_never_blocks_on_approval - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_sm20_anchor_reports_writable - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_sm20_anchor_positive_baseline - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_sm21_anchor_positive_baseline - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_require_ep_passes_on_clean_run - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_confirmation_required_blocks_until_approved - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_run_with_clean_ep_validates - deterministic-naming golden re-record pending sm21 batch
XFAIL tests/test_validation_run_baseline.py::test_geometry_digest_computed - deterministic-naming golden re-record pending sm21 batch
1671 passed, 10 xfailed, 150 warnings in 288.61s (0:04:48)
```
