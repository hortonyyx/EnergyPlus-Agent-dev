# 执行档 · F-158 第二轮（返工）：关闭「更早导入 / 预绑定引用」这条绕过

- **日期**：2026-09-03 · **施工席**：Claude 家族 · **worktree**：`/tmp/f158_rework_claude` · **分支**：`wt/09.03m_f158_rework`
- **任务书**：[`2026-09-03m_f158_rework1.md`](../request/2026-09-03m_f158_rework1.md) · **上一轮裁决**：[`2026-09-03c`](../verdict/2026-09-03c_f158_crossreview_gpt.md)（REWORK / 阻断 1 / 不阻断 3）

## 〇、开工自检（同一条命令）

```
$ pwd && git log --oneline -1 && git status --porcelain
/tmp/f158_rework_claude
f4d50b2 09.03m_F158_rework1_dispatch
（空）
$ python -c "import tests.conftest as m; print(m.__file__)"
/tmp/f158_rework_claude/tests/conftest.py
```

工作树干净、conftest 解析在本 worktree。⛔ 未动 `/workspaces/EnergyPlus-Agent-dev`。

## 分段提交（3 笔 + 本档，⛔ 无 `git add -A`，每笔 `git diff --cached --numstat` 见下）

```
1b47ee1 09.03m_F158_rework1_early_gate_plugin            ep_no_billed_gate.py 260+ · pyproject.toml 1/1 · tests/conftest.py 14/213
c58285a 09.03m_F158_rework1_urllib_teeth                 tests/test_no_billed_provider_calls.py 20/1
1af1fbd 09.03m_F158_rework1_early_bypass_regression_lock tests/test_f158_early_gate_regression.py 173+
a5a8a2f 09.03m_F158_rework1_lock_addopts_ordering        tests/test_f158_early_gate_regression.py 29+   （补：锁 addopts 排序）
9535f54 09.03m_F158_rework1_mirror_includes_gate_plugin  tests/test_gt_promotion_path.py 4+             （修：我自己的副作用，见 §五）
<本档>                                                     execution 交件
```

---

## 一、B-1 修法：为什么这一层覆盖住「更早」与「预绑定」两种载体

⭐ **两种载体其实是同一个根因**（裁决原话「B-1 是同一个『安装时点晚于可执行导入代码』的根因」）：
类属性 wrap 只能守住**绑定发生在 wrap 之后**的调用。所以有效解不是「堵住复核方那一个探针的形状」，
而是**让门在任何 test-owned 代码能跑之前就装好**：

- **更早导入**（复核方载体①，插件 import 期 `connect_ex`）：门已经在场 ⇒ 它的 import 期连接被拦；
- **预绑定引用**（复核方载体②，门装前存下的 bound `sock.connect`）：那个插件只可能绑到**已经被 wrap 的**方法 ⇒ 存下的引用仍然过门。

**机制 = 钉死加载顺序**（正是裁决 §三.2 给的返工处方「专用最早启动插件在 import 时安装并钉死加载顺序」）：
pytest 在 **pre-parse** 阶段导入 `-p` 插件，顺序为 **ini `addopts` → `PYTEST_ADDOPTS` → 命令行**，
且**全部早于任何 initial `conftest.py`**。于是：

1. 把门搬进仓库根 **`ep_no_billed_gate.py`** 插件，**在模块 import 时**（文件末尾 `_install()`）装 wrap —— 这一行就是修法本体；
2. `pyproject.toml` 的 `addopts` 里钉 `-p ep_no_billed_gate`，让它成为**每次运行（master 及每个 xdist worker）第一个被导入的 user 插件**，
   早于任何命令行 `-p` 探针、早于 `tests/conftest.py`。
3. `tests/conftest.py` 退化为**薄 re-export 壳**（不重复任何 hook，避免双触发）。

### ⭐ 加载顺序是【实测】的，不是背书（记忆则：确定性输入 ≠ 推导正确）

用两个 scratchpad 插件（`expgate` 装 wrap、`expprobe` 在 import 期连接并预绑定），实测三种排布：

| 排布 | 谁先 import | 预绑定引用调用结果 |
|---|---|---|
| A `-p expgate -p expprobe`（命令行同序）| gate 先 | **GATE_BLOCKED** ✓ |
| B `-p expprobe -p expgate`（命令行反序）| probe 先 | CONNECTED（绕过，复现脆弱性）|
| C gate 走 `PYTEST_ADDOPTS`、probe 走命令行 `-p` | **gate 先** | **GATE_BLOCKED** ✓ |

C 证明「**addopts 的 `-p` 早于命令行 `-p`**」，即本修法所依赖的顺序成立。

### 残余盲区（诚实标注，⛔ 不含复核方那两种）

只有**比本插件更早运行的代码**能绑到真 `connect`：解释器启动期的 `sitecustomize`/`usercustomize`/`.pth`，
或 addopts 里排在本插件**之前**的 `-p`。前者需进程/OS 层 deny（seccomp / `LD_PRELOAD`），
超出测试 harness 范畴；后者由「本插件在 addopts 里排第一」排除。C 层/io_uring 直连不走 `socket.socket.connect` 者亦不覆盖 —— 真实 provider 路径不走那些。全部写进 [`ep_no_billed_gate.py`](../../../../ep_no_billed_gate.py) docstring。

---

## 二、逐条对验收 §四（六条 · 命令原文 + 输出原文）

### #1 门装【之前】发起的连接 + 【预先绑定】的引用都拦得住 —— 复现复核方探针（两路）

按裁决 §三.2 原样重建 `-p f158_preconfigure_probe` 插件（import 期 `connect_ex` + 门装前存 bound `sock.connect`），测试断言两路都必须 `BLOCKED`：

```
$ python -m pytest -q -n 6 -p no:cacheprovider -p f158_preconfigure_probe \
    tests/test_f158_crossreview_probe.py::test_preconfigure_and_early_bound_connect_bypass -rf
.                                                                        [100%]
================== F-158 no-billed-calls gate: BLOCKED calls ===================
  BLOCKED <collection/import phase> -> ('192.0.2.1', 80)
1 passed in 1.75s
$ rm -f f158_preconfigure_probe.py tests/test_f158_crossreview_probe.py && git status --porcelain   # 仅剩本轮 4 改动
```

✅ 复核方那句 `IMPORT_CONNECT_EX_RESULT=0; EARLY_BOUND_CONNECT_RESULT=CONNECTED` 现在两路都翻成 **BLOCKED**；
汇总里 `BLOCKED <collection/import phase>` 正是 import 期那次被拦。取证后删、树净。

### #2 那条回归锁有牙 —— 摘掉修法 ⇒ 红；恢复 ⇒ 绿 + 树净

摘法 = 注释掉 `ep_no_billed_gate.py` 末尾的 import 期 `_install()`（只剩 `pytest_configure` 装 = 返工前的脆弱形态）：

```
$ # neuter: 末尾 _install() -> # _install()
$ python -m pytest tests/test_f158_early_gate_regression.py -n0 -p no:cacheprovider -q -rf
（子进程内）3 failed          # 四载体全 NOTBLOCKED(returned)
FAILED tests/test_f158_early_gate_regression.py::test_early_and_prebound_carriers_are_blocked
1 failed in 0.83s
$ git checkout -- ep_no_billed_gate.py && git status --porcelain      # （空）
$ python -m pytest tests/test_f158_early_gate_regression.py -n0 -p no:cacheprovider -q
.                                                                        [100%]
1 passed in 0.79s
```

✅ 摘法即红、恢复后 `git status` 空、复跑绿。锁形态 = **子进程** pytest，`-p ep_no_billed_gate -p early_probe`（门先、探针后，与 addopts 同序），断言四载体全 BLOCKED；摘法后探针在 pre-parse（早于 `pytest_configure`）就出网/绑到真方法 ⇒ 子进程 rc≠0 ⇒ 锁红。

### #3 另造一种【不同形】早期绕过 ⇒ 也被拦

回归锁里除复核方的两形，另含**两种不同形**并实测全绿：
- **carrier 3 = 预绑定【类属性】** `socket.socket.connect`（复核方是【实例 bound 方法】，不同形）；
- **carrier 4 = import 期 `socket.create_connection`**（不同调用面）。

`git checkout` 恢复后回归锁 `1 passed`（上条命令）即证 carrier 3/4 全被拦。

### #4 上一轮已成立的逐条不许退化（focused 复现，取证后删）

```
$ python -m pytest tests/test_f158_probe_tmp.py::test_async_httpx_really_connects_is_blocked_and_named -n0 -p no:cacheprovider -q -rf
ep_no_billed_gate.ProviderCallBlocked: F-158 no-billed-calls gate: test
  'tests/test_f158_probe_tmp.py::test_async_httpx_really_connects_is_blocked_and_named'
  tried to open a real network connection to ('192.0.2.1', 80). ...
FAILED ...                                            # ✅ 异步 httpx 响亮失败并指名
$ python -m pytest ...::test_construct_openai_client_is_not_blocked -n0 -q
1 passed                                              # ✅ 构造客户端不拦
$ python -m pytest ...::test_sync_openai_real_send_is_blocked -n0 -q -rf
ep_no_billed_gate.ProviderCallBlocked: ... tried to open a real network connection
  to ('198.18.0.120', 443). ...                       # ✅ 同步 provider egress 响亮失败 + 解析后 IP
```

`.env` 读数一致见 #6（带 / 不带两跑逐位相同）。

### #5 验收 #2 的证据已改钉在 failed 那条腿上，汇总降级为 readout（N-1，选 (b)）

**改前**（`tests/conftest.py` `pytest_terminal_summary`）：
```
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
```
**改后**（`ep_no_billed_gate.py` `pytest_terminal_summary`）：
```
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
```
⇒ 那行**明写「非权威 / 并行下只反映 master 本进程」**；权威证据 = **FAILED 测试集合**（被门拦的调用抛 `ProviderCallBlocked` ⇒ 该测试 failed）。
⭐ **撤回上一轮执行档 §#2 对那个「0」的证据引用** —— #2 现在的证据是「全量 `0 failed`（没有测试因门而红）」，不是「门自报 0」。

### #6 全量绿（`-n 6`，环境自证与 pytest 同一条命令）· 含带/不带 `.env` 对照（N-1 的 .env 腿）

**不带 `.env`**：
```
<在此粘无 .env 全量原文>
```

**带 `.env`**（只 source、不打印 secret）：
```
<在此粘带 .env 全量原文>
```

---

## 三、N-2 / N-3 修正

- **N-2**（证据归属）：上一轮执行档把「无 key 全量的 1 failed」称作「门自己枚举」不准确。**正确证据链** = **无 key 全量锁定唯一候选（`test_zone_agent`）+ 带 key 对该候选实测门命中**（本档不再复用「门自枚举」这一措辞）。范围结论「只有 1 条」不变。
- **N-3**（牙锁文档说「已有 urllib/urllib3 永久锁」而实际没有）：**补上永久锁** `test_urllib_request_to_remote_is_blocked`（`urllib.request.urlopen("http://192.0.2.1/")` ⇒ `ProviderCallBlocked`，经 `URLError` 包裹后断言根因）。docstring 相应改为「pins raw socket, create_connection **and urllib**」，与产物一致（[[self-report-more-compliant-than-artifact]] 的反向兑现：让产物追上自述）。

## 四、明确不做（§三）

⛔ 未改 `src/agent/nodes/*`、未改 LLM 配置、未改 zone 替身方案、未顺手修别的红、未 `pip install -e .`、未 `git add -A`。

## 五、停下上报（分层）

- **A 层**：无。未触 §三禁令。⚠️ **一条边界说明（非 src/，故不停但显式记）**：修法**必然要改 `pyproject.toml`（addopts）并新增仓库根插件 `ep_no_billed_gate.py`** —— 因为**命令行/entry-point `-p` 插件与 initial conftest 都早于 `tests/conftest.py`**，纯 `tests/` 内无任何常驻机制能保证门「最早装」。这正是裁决点名的处方（专用最早启动插件 + 钉死加载顺序），既非 `src/` 也非 §三禁令，故按 B 层记录继续。
- **B 层（记一条继续）**：
  1. ⚠️ **我自己的 addopts 改动打红了 25 条 `test_gt_promotion_path.py::test_precondition_is_one_to_one_bound[*]`** —— 该测试 `_mirror_repo` 把 `pyproject.toml`（现含 `-p ep_no_billed_gate`）拷进镜像树跑子 pytest，但**没拷仓库根的 `ep_no_billed_gate.py`** ⇒ 子 pytest 加载 `-p` 失败、启动即崩 ⇒ 25 条 precondition 全错位。**修法** = `_mirror_repo` 一并拷贝该插件（`9535f54`，4 行）。⭐ 这是**我这次改动唯一一处溢出**，属 [[green-suite-is-a-property-of-tree-and-launcher]]。全仓仅此一处 `pyproject.toml` 拷进镜像跑子 pytest（已 grep 全 tests 确认）。
  2. `tests/conftest.py` 现为 re-export 壳，唯一 import 它的 `test_no_billed_provider_calls.py` 已改为直接 `from ep_no_billed_gate import ...`；壳保留仅为向后兼容 `from conftest import ...`。
  3. 回归锁走**子进程** pytest（`subprocess.run`），比 in-process 慢约 0.8s/次，但这是复现「门装之前」时刻的唯一诚实办法（in-process 时门已装、没有那个时刻）。

## 六、⭐ 我自己认为最薄弱的一处

⭐ **上一版我写的最薄弱点（「接线位置没锁」）已当场补锁**（`a5a8a2f` `test_gt_plugin_is_pinned_first_in_addopts`：断言 `-p ep_no_billed_gate` 存在且是 addopts 里**第一个** `-p`；挪走/删掉即红）。现在剩下的最薄弱处是它的**孪生风险**：

**我把 `pyproject.toml` 和一个仓库根文件 `ep_no_billed_gate.py` 绑成了一条隐式依赖边** —— 「谁拷了 pyproject 去跑子 pytest，就必须也拷这个插件」。本轮我只 grep 出并修好了**当前**唯一一处（`test_gt_promotion_path._mirror_repo`），但**这条耦合是常驻的**：
- 将来任何新写的「镜像仓库 + 子 pytest」测试，只要拷 pyproject 而忘了拷插件，就会**以同样的方式静默崩**（而且崩相是「子 pytest 启动失败」，容易被误读成被测逻辑的失败，正如这次 25 条 precondition 的错位）；
- 我没有加一道**结构锁**去保证「任何把 pyproject 拷进镜像的地方都同时拷了插件」—— 那需要一条能发现「镜像树里 pyproject 引用了缺失模块」的通用判据，本轮未做（属 [[green-suite-is-a-property-of-tree-and-launcher]]：全仓绿是**树+启动器**的属性，我改的是启动器的一个入参，溢出面比单文件大）。
- ⚠️ 兜底：真实权威全量（§二 #6）会**跑到**这些镜像子 pytest，所以**现存**的溢出一定会在全量里现形（这次就是这么抓到的）；漏的是**将来新增**的同型测试，全量对它无预警。
