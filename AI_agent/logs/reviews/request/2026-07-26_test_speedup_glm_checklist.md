# GLM-5.2 验证性对抗审清单：测试提速（并行）+ 受影响子集映射表（2026-07-26）

- **审阅方**：GLM-5.2（跨家族；施工方 = GPT 侧 terra，谁写谁不批）
- **审阅类型**：**验证性审阅**——本清单把每条命题的「验什么 / 什么算不成立」写死，你只需逐条实证，不需要在无线索处自由探索（唯一例外 = §B-07，那条明确要你主动找漏）
- **只审不修**：**一行生产代码都不要改**。发现问题写进裁决书，不要顺手修。探针脚本一律放 `/tmp`，不要落仓库。
- **独立性**：不要 import 施工方新写的测试夹具来"验证"它自己；能裸探针复算的就裸探针复算。
- **施工契约（判"是否照做"的基准）**：`AI_agent/logs/reviews/request/2026-07-26_test_speedup_and_affected_map_dispatch.md`
- **施工方自述（判"声称 vs 实况"的基准）**：`AI_agent/logs/reviews/execution/2026-07-26_test_speedup_and_affected_map.md`
- **裁决书落**：`AI_agent/logs/reviews/verdict/2026-07-26_test_speedup_and_affected_map_glm.md`，结论用 `APPROVE` / `APPROVE-WITH-CHANGES` / `REWORK`，每条命题标 **成立 / 不成立 / 无法判定**（无法判定要写清缺什么才能判）。

## 环境须知（省得踩坑）

- 全仓测试**现在默认并行**（`pyproject.toml` 的 `addopts` 有 `-n auto --dist load`）。要串行必须显式 `-n0`。
- 参考量级：串行全仓约 15–25 分钟（受机器负载影响很大），并行全仓约 4.5–8 分钟。**长跑一律后台重定向 + 轮询**。
- 机器 16 逻辑核。变异矩阵那 25 格每格会再起一个子 pytest，机器满载时整机进程会超订——**你自己跑测时别再并行开第二个全仓**，否则数字不可比。
- 基线口径：本批前 = 1656 passed + 10 xfailed；本批后 = 1656 + 新增映射测试条数 + 10 xfailed，**零 failed 零 error**。

---

## §A 并行提速（7 条）

| # | 命题 | 怎么验 | 什么算「不成立」 |
|---|---|---|---|
| A-01 | 依赖声明真实且最小 | 看 `pyproject.toml` dev 组含 `pytest-xdist>=3.8`；`git diff uv.lock` 只新增 `pytest-xdist` 与 `execnet` 两包 | lock 里出现任何第三个包的增删/升级 |
| A-02 | 并行口径是 `-n auto --dist load` | 读 `[tool.pytest.ini_options].addopts`；跑一次全仓看是否真起多 worker | 用了 `--dist loadfile`（会把 25 格变异矩阵压到同一 worker、提速报废），或 addopts 没生效 |
| A-03 | 嵌套子 pytest 真的单进程 | `tests/test_gt_promotion_path.py` 里那条 `subprocess.run([... "-m", "pytest", ...])` 必须带 `-n0`；再独立验证「命令行 `-n0` 能覆盖 addopts 的 `-n auto`」（例：`python -m pytest -q -n0 tests/test_reading_schema.py`，输出不应出现 `bringing up nodes`/`gw0`） | 子进程命令没有 `-n0`，或 `-n0` 实际不覆盖 addopts |
| A-04 | 并行 ≡ 串行（**命脉**） | 你**自己独立跑一次并行全仓**（`-q -rA`），抽 `^(PASSED\|FAILED\|ERROR\|XFAIL\|XPASS\|SKIPPED) <nodeid>` 排序去重，与执行日志里施工方那份**串行**节点集合逐字节比 | 出现任何节点差异；或任一节点在你这轮是 failed/error |
| A-05 | 没有用「盖住问题」的手段换绿 | `git diff` 全部测试文件 + grep 新增的 `skip`/`xfail`/`xdist_group`/`serial`/retry/`--dist loadgroup` | 发现任何一处（本批**唯一**允许的既有测试改动 = A-06/A-07 两处，见下） |
| A-06 | 容差放宽只有主控授权的那一处 | 唯一授权项 = `tests/test_mcp_stdio.py` 的 `timeout=10` → `120`（理由：那是隐含机器速度假设，不是该测试契约；`returncode==0` 与 `stdout==""` 两条断言必须一字未动）；其余测试文件 diff 不得含任何容差/期望值/断言改动 | 出现第二处放宽；或 mcp_stdio 的两条断言被动过 |
| A-07 | E4 是**根因修法**不是遮盖 | `tests/test_e4_relative_north_axis_e2e.py` 的修法应为「把 variant 的 idf 拷进各自 tmp 目录后再喂 EP」；断言/`skipif`/期望值（114 面、14 区、三档容差常量等）逐字未动；并自证跑该模块时仓库路径 `AI_agent/logs/experiments/2026-07-10_e4_relative_north_axis_probe/` 内**不出现** `in.idf` | 改了断言/容差；或仍把仓库内固定 idf 直接喂 EP；或改用 `xdist_group`/skip 之类绕过 |

> A 段背景（判 A-07 用）：EnergyPlus 会在「输入 idf 所在目录」建临时 `in.idf` 链接并在结束时删除。原来该 fixture 喂的是仓库内固定路径，xdist 下同一模块级 fixture 在多个 worker 各跑一次 → 两个 EP 进程对同一目录建同名链接 → 撞。全仓只有这一个测试真跑 EnergyPlus。

---

## §B 受影响子集映射表（8 条）

被审对象：`scripts/tool_scripts/affected_tests.py` + `scripts/tool_scripts/affected_tests_rules.yaml` + `tests/test_affected_tests_map.py`。

设计口径（判"是否照做"的基准）：一等公民 = `src/**` + `scripts/**` + `tests/**` 的 `.py`（排除 `__pycache__`、`scripts/tool_scripts/vendor/`）**加仓库根 top-level `*.py`**；边有两类 = AST import 边（含相对导入）+ **字符串路径边**（某文件的字符串常量里出现另一个一等公民文件的仓库相对路径，用来捕获 `subprocess` 调脚本这种没有 import 的耦合）；改动文件 F → 选中所有「传递闭包里含 F」的测试文件。

| # | 命题 | 怎么验 | 什么算「不成立」 |
|---|---|---|---|
| B-01 | 输出确定性 | 同一输入连跑两次逐字节相同；且**与文件遍历顺序无关**（把 `first_class_files` monkeypatch 成反序，输出不变） | 两次不同，或反序后输出变化 |
| B-02 | fail-closed 五条真的回落全仓 | 逐条实跑：① 非一等公民路径（如 `README.md`）② 全仓触发器（如 `pyproject.toml`、`src/configs/**`、`**/conftest.py`、共享测试 helper）③ 已删除/不存在的路径 ④ 规则表坏掉（monkeypatch 到一份坏 YAML）⑤ 改动模块无任何覆盖测试 —— 五条都必须 `SCOPE: FULL` 且给出原因 | 任一条输出 `SCOPE: SUBSET`、空集合、或崩溃退出（崩溃≠fail-closed） |
| B-03 | 字符串边是承重机制不是死码 | 把 `build_edges` 里扫 `ast.Constant` 字符串那一支临时禁掉（**在 `/tmp` 的仓库副本或改完立刻还原**），`tests/test_affected_tests_map.py` 里那条纯字符串边锁（cv_probe ↔ test_cv_toolbox）必须变红 | 禁掉后仍全绿 = 假锁 |
| B-04 | 根入口边是承重机制 | 同法把「仓库根 top-level `*.py` 纳入集合」这一支禁掉，`src/mcp/server.py` → `tests/test_mcp_stdio.py` 那条锁必须变红 | 禁掉后仍全绿 |
| B-05 | 传递闭包真的传递 | 锁里举的例子必须**确无直接边**、链长 ≥ 2（自己用 `build_edges` 复算一遍，别只信断言） | 举的其实是直接边；或链长 1 |
| B-06 | 覆盖门双向且清单诚实 | `tests/test_affected_tests_map.py` 的覆盖门应断言「实算 uncovered 集合 == allowlist 键集合」（严格相等，双向）；随手删一条 allowlist 必红、随手加一条已被覆盖的模块也必红；再抽查 3 条 allowlist 理由是否**事实成立**（例：写"无测试跑它"的模块，全仓 grep 确认真没有测试经 import/字符串/CLI 触到它） | 只做单向；或抽查发现理由与事实不符（这类"清单是谎言"按 MAJOR 记） |
| B-07 | **漏选反例自查（本批最重要一条，需要你主动找）** | 独立挑 **5 个**生产模块（建议覆盖：一个被 CLI/subprocess 调的脚本、一个被 `-m 模块名` 形式调起的模块、一个被动态导入/字符串模块名引用的模块、一个只被数据/配置驱动的模块、一个深层公共模块），先**自己人工判断**「改它之后哪些测试真的可能变红」，再与工具输出比 | 找到**漏选**（工具没选、但实际会因该改动变红的测试）= MAJOR；过度选择（多选了）不算缺陷 |
| B-08 | 不确定时倾向全仓 | 通读 `affected_tests()`：任何异常/不确定路径都应汇成 `SCOPE: FULL`，不得静默缩小集合；确认没有 `except` 吞掉后继续按子集走的路径 | 存在「出错了仍返回 SUBSET」的路径 |

---

## §C 交付纪律（4 条）

| # | 命题 | 怎么验 | 什么算「不成立」 |
|---|---|---|---|
| C-01 | 执行日志数字可复现 | 你自己那次并行全仓的计数（passed/xfailed/failed）与日志一致；再抽一个子集命令实跑，量级与日志表格相符（墙钟不要求逐秒吻合，机器负载会浮动） | 计数对不上；或子集实跑结果与声称不符 |
| C-02 | neuter 自查表可复现 | 抽 **4 格**（务必含 B-03、B-04 两条机制格）按表里写的 neuter 方式实跑，结果与表里写的一致；注意表里已诚实披露有两格「非只红对应锁」（字符串扫描连带覆盖门），这属于已披露的共享依赖、不算隐瞒 | 抽查任一格与表里不符（表里写红实际绿 = 假表 = 直接 REWORK 级别） |
| C-03 | 无越界改动 | `git status` + `git diff` 只应出现：`pyproject.toml`、`uv.lock`、`tests/test_gt_promotion_path.py`（一行 `-n0`）、`tests/test_e4_relative_north_axis_e2e.py`（fixture 隔离）、`tests/test_mcp_stdio.py`（timeout）、三个新增文件（`affected_tests.py`、`affected_tests_rules.yaml`、`tests/test_affected_tests_map.py`）、`AI_agent/logs/reviews/**` 的派工单与执行日志 | 出现任何其它文件改动（尤其 `src/` 生产码、`case_tests/` 资产、`.gitignore`、CI 配置） |
| C-04 | 未提交 | `git log` HEAD 仍是 `2217393`，本批改动全在工作树 | 已 commit |

---

## 汇报格式

裁决书只要：① 结论（APPROVE / APPROVE-WITH-CHANGES / REWORK）② 逐条命题表（成立 / 不成立 / 无法判定 + 一句证据）③ 每条「不成立」写成可执行的出口（改什么、怎么验收）并标 BLOCKER/MAJOR/MINOR ④ 你实跑的关键原始输出尾部（并行全仓一次 + neuter 抽查 4 格）⑤ 你认为最脆的一处及理由。**不要复述实现细节**，主控只看结论 + 证据。
