# 派工单：测试提速（并行）+ 「受影响子集」固定映射表（2026-07-26）

- **施工方**：terra（gpt-5.6-terra, high）— GPT 侧执行档
- **审阅方**：GLM-5.2 照主控另出的结构化清单做验证性对抗审（谁写谁不批，跨家族）
- **主控**：Opus 5（本单即唯一施工契约 + 轻门独立全量）
- **用户拍板（2026-07-26）**：范围 = 并行 + 映射表一起做；派工 = terra 施工 / GLM 复核 / 主控轻门。
- **本单自包含**：没有独立细稿，本单即契约。凡本单未授权的改动，一律不做。

---

## 0. 主控已实测的事实基线（不要重新推测，可复核）

| 项 | 值 |
|---|---|
| 串行全仓（`python -m pytest -p no:cacheprovider -q`） | **1656 passed + 10 xfailed**，**1135 秒**（18:54），exit 0 |
| `-n 16` 并行全仓（同日、同 HEAD `2217393`） | **1656 passed + 10 xfailed**，**260 秒**（4:20），exit 0；10 个 xfail 节点逐条相同 |
| 跑完 `git status --porcelain` | 空（两种跑法都不往仓库里写东西） |
| 机器 | 16 逻辑核；`pytest 9.0.3`；`pytest-xdist 3.8.0` + `execnet 2.1.2` **主控已装进 `/opt/venv`**（但**尚未在 `pyproject.toml` 里声明**——这是你要补的） |
| 慢测大头（`--durations=40`） | `test_gt_promotion_path.py::test_precondition_is_one_to_one_bound` 25 格 ≈ **440 秒**（每格复制一份仓库镜像 + 起子 pytest）；`test_orchestrate_baseline.py` 三条 ≈ 92 秒；`test_isolation.py` 五条 ≈ 105 秒 |

**已探明的坑**：`test_gt_promotion_path.py:504` 的子进程 pytest 会**继承父进程的并行参数**（主控用 `PYTEST_ADDOPTS="-n 4"` 实测：子进程也 `bringing up nodes`、结果仍正确但白烧 CPU）。默认并行落地后，25 格 × 16 worker 会把机器压死，所以子进程那行**必须显式钉单进程**。

---

## 1. 任务 A：并行提速落地

### A1 依赖声明
- `pyproject.toml` 的 `[dependency-groups] dev` 加 `pytest-xdist>=3.8`。
- 跑 `uv lock`。**若 lock diff 触及 `pytest-xdist` / `execnet` 之外的任何包，撤回 lock 改动、只留 pyproject，并在执行日志里说明**（不要顺手升级别的依赖）。

### A2 默认并行 + 子进程钉单进程（主控已定，不要另选方案）
- `[tool.pytest.ini_options]` 增 `addopts = ["-n", "auto", "--dist", "load"]`（`auto` = 跟随机器核数；`load` = 默认按用例散，**不要用 `loadfile`**——25 格变异矩阵在 `loadfile` 下会全落到同一个 worker，提速直接报废）。
- `tests/test_gt_promotion_path.py:504` 的子进程 pytest 命令**显式加 `-n0`**（命令行覆盖 addopts）。这是全仓唯一一处嵌套 pytest（主控已 grep 确认：无 `pytest.main`、无其它 `-m pytest` 子进程）。改完要证明它真生效（见 A4 第 4 条）。
- **不动** `-p no:cacheprovider` 等既有习惯用法；不加 `-x`、不加超时插件、不引入 `pytest-randomly`/`pytest-timeout` 等任何其它插件。

### A3 不要碰的东西
- **不改任何既有测试的断言、容差、xfail 标记**（唯一允许的既有测试改动 = A2 里那行 `-n0`）。
- **不改 `AI_agent/**`**（管理文档由主控自己更新），唯一例外 = 你的执行日志。
- 不改 `.gitignore`、不改 CI 配置（本仓无 CI 配置，不要新建）。
- 不为了让并行变绿而给任何测试加 `serial` 标记 / `xdist_group` / skip。**如果某条测试在并行下真的不稳，停手上报**，不要自己想办法绕。

### A4 验收（命脉：并行必须与串行**逐节点**一致，不是数字对得上就行）
按下列步骤实跑，原始输出全部进执行日志：

1. **串行基准**：`python -m pytest -p no:cacheprovider -q -n0 -rA > serial.txt`
2. **并行第一次**：`python -m pytest -p no:cacheprovider -q -rA > par1.txt`
3. **并行第二次**（换一次跑，抓顺序相关的不稳）：同上 → `par2.txt`
4. **逐节点集合严格相等**：从三份输出里抽 `^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) <nodeid>` 排序去重，三份**集合严格相等**（`diff` 出空）。把比对命令和 `diff` 的空输出贴进日志。**只贴 "1656 passed" 三次相同 = 不合格**，必须是节点级集合比对。
5. **仓库零副作用**：每次跑完 `git status --porcelain` 为空（除你自己的改动文件）。
6. **子进程真的单进程了**：给出证据（例如临时给该子进程命令加 `-v`/或直接读子进程 stdout 确认无 `bringing up nodes` / `gw0`），证明 A2 的 `-n0` 落到了子进程，而不是"逻辑上应该生效"。
7. 报三次的墙钟时间。

---

## 2. 任务 B：「受影响子集」固定映射表

### B0 背景（为什么要它）
2026-07-26 用户定的跑测节奏：**施工方中间轮只跑受影响子集 / 交付前跑一次全仓 / 主控轻门独立全量**。现在「受影响子集」没有任何依据，等于让执行档自由裁量——本任务就是把它变成**机械可推导、无自由裁量**的工具。

### B1 落点与形态（主控已定）
- 工具：**`scripts/tool_scripts/affected_tests.py`**（自包含 CLI，不要往 `src/` 里塞开发期工具——`src/` 是生产代码）。
- 显式规则表：**`scripts/tool_scripts/affected_tests_rules.yaml`**（只放"非 Python 路径"的规则 + 未覆盖模块白名单，见 B4/B5）。
- 测试：**`tests/test_affected_tests_map.py`**。
- **不做**：不接 CI、不进 `addopts`、不改任何既有测试、不生成"冻结快照文件"（映射由代码每次现算 = 单一真源，避免快照过期成新债）。

### B2 映射算法（写死，不许换设计）
1. **一等公民文件集** = `src/**/*.py` + `scripts/**/*.py` + `tests/**/*.py`（排除 `__pycache__`、`scripts/tool_scripts/vendor/**`）。
2. **import 边**：`ast` 解析每个一等公民文件，取 `Import` / `ImportFrom`：
   - 绝对导入：模块名首段属于 `src` / `scripts` / `tests` 的，解析成文件路径（含包 `__init__.py`）。仓库里 `from src.x import y` 有 482 处。
   - **相对导入必须支持**（`ImportFrom.level > 0`，仓库 `src/` 里有 65 处），按所在包解析。
   - 解析不到具体文件的（第三方、stdlib）忽略。
3. **字符串路径边（必须做，不许省）**：扫描每个一等公民文件里的**字符串常量**，若其中出现某个一等公民文件的仓库相对路径（如 `"scripts/tool_scripts/gt_from_dxf.py"`），也算一条依赖边。理由：多处测试是用 `subprocess.run([sys.executable, "scripts/tool_scripts/xxx.py", ...])` 调脚本的，**没有 import 边**，只靠 import 图会漏掉真实耦合。
4. **传递闭包**：对每个测试文件 T，`closure(T)` = 从 T 出发沿上述两类边可达的全部一等公民文件。
5. **反向映射**：改动文件 F → `tests(F) = {T | F ∈ closure(T)}`；改动的文件本身是测试文件则含自身。
6. 全过程**确定性**：任何输出（文件列表、命令行）都排序，两次调用逐字节相同。

### B3 CLI 契约
- `--changed <path>...`：显式给改动路径；`--since <git-ref>`：用 `git diff --name-only <ref>...HEAD`（含未提交改动的口径你定，但要在 `--help` 里写清）。
- 首行必须是机器可读的口径声明：`SCOPE: FULL` 或 `SCOPE: SUBSET`。
- 随后打印**可直接粘贴执行的 pytest 命令**，以及一行给执行日志用的声明（形如 `跑测声明：受影响子集 = tests/a.py tests/b.py（依据 affected_tests.py --since <ref>）`）。
- `--explain`：打印每个被选中的测试是**因为哪条边**被选中的（import 链 / 字符串路径命中）。审阅方靠它复核，不是可选项。
- 退出码：正常 0；输入路径不存在等使用错误非 0。

### B4 fail-closed 规则（这是安全性所在，逐条实现 + 逐条上锁）
以下任一情形，输出 **`SCOPE: FULL`**（全仓），**绝不允许输出空集合或"猜一个子集"**：
1. 改动路径不是一等公民 `.py`，且没被 `affected_tests_rules.yaml` 的规则匹配（例：`README.md`、`data/**`、`case_tests/**` 资产、`skills/**`）。
2. 改动路径命中"全仓触发器"：`pyproject.toml`、`uv.lock`、任何 `conftest.py`、`src/configs/**`、`scripts/tool_scripts/affected_tests.py` 本身及其规则表、`tests/b4b_contract_fixture.py` / `tests/b5_test_helpers.py` 之类被广泛共享的测试 helper（**由规则表显式列举，不许用"看起来很通用"这种判断**）。
3. 改动路径**已删除**（在磁盘上不存在）——删除会改变 import 图本身，一律全仓。
4. 规则表自身解析失败 / import 图构建中遇到语法错误文件 —— 一律全仓（并把原因打出来），**不得静默跳过**。

### B5 未覆盖模块的诚实清单
- 测试 `tests/test_affected_tests_map.py` 里加一条：**每个 `src/**/*.py` 与 `scripts/**/*.py` 要么至少映射到 1 个测试文件，要么出现在规则表的 `uncovered_allowlist` 里**；两者都不满足 → 测试失败。
- 你需要照实把当前真实的未覆盖模块填进 `uncovered_allowlist`（每条带一句为什么，例如"下游 LangGraph 节点，本项目侧无测试"）。**不许为了让这条测试变绿而伪造映射边或注释掉断言。**

### B6 必红锁（每条都要 neuter 验证 = 只有对应用例变红）
1. **确定性**：同一输入两次调用输出逐字节相同。
2. **真 import 边**：改 `src/agent/judge/tarch_normalize.py` → 选中集合包含 `tests/test_tarch_converter_p1_geometry.py`、`..._p2_geometry.py`、`test_tarch_converter_gate_mutations.py`（实际值以你跑出来的为准，锁要写死具体期望，不许写 `len(...) > 0` 这种空断言）。
3. **传递边（间接依赖）**：挑一个真实的"测试没直接 import、但经中间模块可达"的模块作为输入，断言对应测试被选中。**必须是真的间接边**，不能拿直接边冒充（在日志里说明你选的是哪条链）。
4. **字符串路径边**：改 `scripts/tool_scripts/gt_from_dxf.py` → 选中 `tests/test_gt_from_dxf.py`（该耦合只存在于字符串 + subprocess）。neuter 掉 B2#3 的字符串扫描后，**这条必须变红**——这是证明该机制不是死码的唯一手段。
5. **fail-closed 四条**（B4 逐条）：非一等公民路径 / 全仓触发器 / 已删除文件 / 规则表坏掉 → 各自 `SCOPE: FULL`。
6. **B5 覆盖门**：把 `uncovered_allowlist` 里任一条删掉 → 该测试必须变红（证明门是真的）。

### B7 汇报（B 部分）
除代码与测试外，执行日志里给出：
- `--explain` 的一份真实样例输出（选一个有代表性的改动路径）。
- 现实数据：对 `src/agent/judge/tarch_normalize.py`、`src/agent/pipeline.py`、`scripts/tool_scripts/run_stage.py` 三个输入各跑一次，报**选中测试文件数** + **该子集实际跑一遍的墙钟时间**（对比全仓 260 秒，让人看得出提速是否真的有意义）。

---

## 3. 验收纪律（全批共用，前两批都栽在这）

1. **neuter 自查表 = 交付物**：每条必红锁 → neuter 什么（哪一行改成什么）→ 哪条用例变红 → 是否**只**红该条。每一格都必须是你**实跑过**的结果。
2. **诚实披露优于伪装完成**：做不完、或某条锁 neuter 后没红（= 假锁），照实写。本项目里"诚实 PARTIAL"被主控当正面样板；伪造自查表直接 REWORK。
3. **全仓零回归**：基线 **1656 passed / 10 xfailed / 0 failed**。交付前跑一次全仓，原始输出尾部贴进执行日志。任务 A 落地后全仓 = 并行跑，仍须 1656/10/0。
4. 不得放宽任何既有容差、断言、xfail 口径来让新测试变绿。
5. 中间轮可以只跑受影响子集（本批就在建这个工具，先手工判断也行），但**交付前那一次必须全仓**。

## 4. 交付物

1. 生产改动：`pyproject.toml`（+ 可能的 `uv.lock`）、`tests/test_gt_promotion_path.py` 那一行、`scripts/tool_scripts/affected_tests.py`、`scripts/tool_scripts/affected_tests_rules.yaml`
2. 测试：`tests/test_affected_tests_map.py`（B6 全部必红锁）
3. neuter 自查表
4. 执行日志 `AI_agent/logs/reviews/execution/2026-07-26_test_speedup_and_affected_map.md`（含 A4 七项证据 + B7 数据）
5. **不要 git commit**（主控轻门后统一提交）

## 5. 汇报格式

回主控时只给：① 做了什么（按 A / B 分节）② 完整 neuter 自查表 ③ A4 的逐节点集合比对证据 + 三次墙钟 ④ 全仓测试原始输出尾部 ⑤ 未竟项与已知风险 ⑥ 你认为最脆的一处及理由。**不要长篇自述实现过程**——审阅方只看原始需求 + diff + 测试输出。
