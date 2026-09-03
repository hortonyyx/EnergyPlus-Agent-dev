# 执行档 · F-158 第三轮（返工 2）· Claude 家族施工席

- **日期**：2026-09-03（第三程）· **施工方**：Claude 家族施工席 · **审**：GPT 家族
- **工作目录**：`/tmp/f158_rework2_claude` · **分支**：`wt/09.03y_f158_rework2`
- **任务书**：[`2026-09-03y_f158_rework2.md`](../request/2026-09-03y_f158_rework2.md)
- **本轮提交**（分段，⛔ 未攒到最后）：

| commit | 内容 |
|---|---|
| `c509b41` | T1 常驻行为自检 `tests/test_f158_gate_behavioral_selfcheck.py` |
| `60a3258` | T1 分辨力锁（牙锁）`test_behavioral_selfcheck_has_teeth`（加进 `test_f158_early_gate_regression.py`）|
| `c3abb1a` | T3 镜像插件结构锁 `test_mirror_ships_the_egress_gate_plugin`（`test_gt_promotion_path.py`）|
| `28148ea` | T2 门 docstring 改诚实（`ep_no_billed_gate.py`）|

---

## 先说清楚：本轮和上一轮的关键差别（甲案，不再堵启动形态）

⛔ 我没有再往「四载体锁」里加 urllib 探针，也没枚举启动形态（`-o addopts=` / `PYTEST_ADDOPTS` / `-c` / rootdir …）——
那条路对启动形态无上界，上一轮我自己就写过这个结论。

本轮按用户拍板的**甲案**：加一条**行为自检 T1**——真去连 TEST-NET，断言被门拦住。
任何让门没装上的起法，都撞同一堵墙（T1 红），从「静默漏」变「点名红」。

### ⭐ 一条设计上的硬约束（决定了 T1 怎么写）

`ep_no_billed_gate.py` 在 **import 时就 `_install()`**（文件末行），而 `tests/conftest.py`
又 `from ep_no_billed_gate import ...`（纵深防御）。⇒ **在 `tests/` 真实套件里，即便 `-o addopts=`
去掉了 `-p` 钉，门也会经 conftest 的 import 自动装上。** 这意味着：

1. **真实全量套件对 `-o addopts=` 其实仍然是防住的**（conftest 兜底）——复核方的绕过窗口在
   **pre-parse 的 `-p probe` 插件 import 期**，那早于任何 conftest，T1（测试体）跑不到那一刻。
   ⇒ **甲案是【发现】不是【拦截】，我已把这句写进 T2。**
2. **T1 若在模块顶部 `import ep_no_billed_gate`，光是 import 就会自装门，`-o addopts=` 起也会假绿。**
   ⇒ 故 **T1 模块级不 import 门**，异常按**类名 + 模块名**识别（`ProviderCallBlocked` / `ep_no_billed_gate`）。
3. ⇒ 要展示「门关 T1 红」，必须在**没有 conftest 的最小树**里跑（正是复核方 B-1 的做法）。牙锁就这么做。

---

## §五 逐条

### #1 复核方那条绕过现在会被点名（`-o addopts=` ⇒ T1 红，且文案指出是启动配置问题）

在无 conftest 的最小树里，拷 T1 文件为 `test_probe.py`，`-o addopts=` 起（去掉 ini 的 `-p` 钉）：

```
$ D=$(mktemp -d) && cp tests/test_f158_gate_behavioral_selfcheck.py "$D/test_probe.py"
$ PYTHONPATH=/tmp/f158_rework2_claude python -m pytest -q -o addopts= -p no:cacheprovider "$D/test_probe.py" --rootdir "$D"
OFF pytest rc=1
...
E   AssertionError: F-158 egress gate did NOT intercept a connection to TEST-NET ('192.0.2.1', 80):
    connect() returned instead of raising ProviderCallBlocked. The gate is not installed in this
    pytest process — the way it was started disabled the no-billed-calls gate, so billed provider
    calls are possible.
1 failed in 0.02s
```

- rc=1（1 failed），报错文案直说「the way it was started disabled the no-billed-calls gate」。✅
- ⚠️ **本沙箱实测**：连 `192.0.2.1` **不是超时而是 `connect()` 直接返回成功**（记忆里「本沙箱任何地址都解析/连得通」，
  也正因如此**门关时真出网是可能真花钱的**——更说明门要紧）。T1 的 `else` 分支正好覆盖「未拦截=连上了」这一形态，
  **不会挂起**（配 0.05s 超时，即便超时也只多等 0.05s）。

### #2 T1 有牙（摘掉门 ⇒ T1 红；恢复后 `git status --porcelain` 空；同一条命令跑环境自证与 pytest）

牙锁 `test_behavioral_selfcheck_has_teeth`（常驻）把**同一个 T1 文件**拷进无 conftest 的最小树跑两次：

```
$ D=$(mktemp -d) && cp tests/test_f158_gate_behavioral_selfcheck.py "$D/test_probe.py"
$ PYTHONPATH=/tmp/f158_rework2_claude python -m pytest -q -o addopts= -p no:cacheprovider "$D/test_probe.py" --rootdir "$D"; echo rc=$?
OFF pytest rc=1
1 failed in 0.02s
$ PYTHONPATH=/tmp/f158_rework2_claude python -m pytest -q -o addopts= -p ep_no_billed_gate -p no:cacheprovider "$D/test_probe.py" --rootdir "$D"; echo rc=$?
ON pytest rc=0
1 passed in 0.00s
```

门关 rc=1（红）、门开 rc=0（绿）。✅ 这条已固化成常驻锁（`60a3258`），防「恒绿=不可观测」。

环境自证 + pytest **同一条命令**（`m.__file__` 落在工作目录里）：

```
$ python -c "import ep_no_billed_gate as m; print(m.__file__)" && \
    python -m pytest -q -n0 -p no:cacheprovider tests/test_f158_gate_behavioral_selfcheck.py
/tmp/f158_rework2_claude/ep_no_billed_gate.py
.                                                                        [100%]
================== F-158 no-billed-calls gate: BLOCKED calls ===================
  BLOCKED tests/test_f158_gate_behavioral_selfcheck.py::test_egress_gate_behaviorally_blocks_a_real_connection -> ('192.0.2.1', 80)
1 passed in 0.03s
```

`m.__file__ = /tmp/f158_rework2_claude/ep_no_billed_gate.py`（落在本工作目录）✅。
牙锁演示用的都是 `mktemp -d` 的临时树，**不写工作树**；本轮全部改动均已 commit ⇒ 交件时 `git status --porcelain` 空（见文末）。

### #3 T1 不打真 provider（地址 + 禁代理 + 超时）

- **地址**：`("192.0.2.1", 80)` = RFC 5737 TEST-NET-1，不可路由、永不是真 provider。
- **禁代理**：用 **raw `socket.connect`**，直连该 IP，**不经任何 HTTP 代理层**（代理是 HTTP 客户端概念，
  raw socket 不读 `*_proxy` 环境变量）。⇒ 结构上就不会被代理变成一次真出网。
- **超时**：`sock.settimeout(0.05)`。门装上时 wrapper 在任何字节离开前就抛，成本≈0；门没装上时最多多等 0.05s。

（形态照抄复核方探针 + `tests/test_no_billed_provider_calls.py` 既有约定。）

### #4 承诺改诚实（T2）

`grep -n "structurally impossible" tests/ *.py` ⇒ 只有 `ep_no_billed_gate.py` 的 docstring 谈「出网结构性不可能」
（`test_checks_mep_assembly.py:725` 是 `disposition()` 的、无关；架构/指南文档无此断言，见下）。

```
$ grep -rn "structurally impossible" --include=*.py .
ep_no_billed_gate.py:1        (T2 已改，见下)
tests/test_checks_mep_assembly.py:725   # 关于 disposition()，与出网无关，不动
```

改前（`ep_no_billed_gate.py:1-2`）：
```
F-158 — make a real, *billed* provider call structurally impossible in the
default test suite, and do it **before any test-owned code can run**.
```
改后（新增「Honesty about the shape of the promise (T2)」一节，节选）：
```
Under the **default startup configuration** a billed provider call is structurally
impossible: ... It is **not** true, however, that *no test can ever* reach the network
regardless of how pytest is started: a different startup config can drop the pin
(-o addopts=, PYTEST_ADDOPTS override, -c <other config>, a foreign rootdir with no
tests/conftest.py). Those do not fail silently — the behavioural self-check
tests/test_f158_gate_behavioral_selfcheck.py ... goes red for any run whose gate is off ...

That self-check is a detector, not an interceptor: it guarantees you *see* red, but a
test that ran *before* it in a gate-off process and truly reached the network has already
spent the money.
```
⭐ **含「甲案是发现不是拦截」那半句**（`detector, not an interceptor` + 「钱已花」）。✅

### #5 T3 有明确去向（加锁）

选择**加结构锁**（非「不做」）：`test_mirror_ships_the_egress_gate_plugin`（`test_gt_promotion_path.py`）。
调 `_mirror_repo` 后断言镜像里 `pyproject.toml` 与 `ep_no_billed_gate.py` 同在。
标 `@pytest.mark.mutation` ⇒ 被子 pytest 的 `-m "not mutation"` 排除（不会在镜像里递归），主套件仍收集计数。

有牙实测（临时删掉 `_mirror_repo` 里的插件拷贝行）：
```
$ python -m pytest -q -n0 -p no:cacheprovider "tests/test_gt_promotion_path.py::test_mirror_ships_the_egress_gate_plugin"
tests/test_gt_promotion_path.py:607: AssertionError
FAILED tests/test_gt_promotion_path.py::test_mirror_ships_the_egress_gate_plugin
1 failed in 1.10s       # 还原后 1 passed
```
被 `-m "not mutation"` 排除验证：
```
$ python -m pytest ... -m "not mutation" --collect-only "...::test_mirror_ships_the_egress_gate_plugin"
no tests collected (1 deselected)
```
⚠️ **残留（诚实标注）**：这锁只覆盖**当前已存在的**镜像站点（`_mirror_repo`）。
「未来任何新写的拷 pyproject 去跑子 pytest 的地方也必须拷插件」这条**无法用结构锁提前堵**
（[[lexical-guard-cannot-be-completed]]）——那是词法护栏永远补不完的那一类。**归属**：属 harness 工程债，
下一个新增镜像站点的施工席在提交时自查。

### #6 §四那条规则我自己走了一遍（grep 出所有【会起子 pytest 的地方】+ 逐处结论）

```
$ grep -rnE '"-m",\s*"pytest"|"pytest",|-m pytest|pytest\.main' --include=*.py .
tests/test_f158_early_gate_regression.py:173   _run_child          (既有)
tests/test_f158_early_gate_regression.py:224   _run_selfcheck      (本轮新增，牙锁)
tests/test_gt_promotion_path.py:632            变异矩阵子 pytest    (既有)
scripts/tool_scripts/affected_tests.py:286/290 只【打印】命令串，不 spawn
tests/test_affected_tests_map.py:29            只断言那串字符串，不 spawn
AI_agent/logs/experiments/.../o22m4_channel_probe.py  实验档 docstring，套件不收集
```

| 子 pytest 站点 | 会收集到 T1 吗？ | 那里门装上了吗？ |
|---|---|---|
| `test_f158_early_gate_regression._run_child`（跑 `test_inner.py`，cwd=tmp）| ❌ 只收 `test_inner.py`（显式目标，tmp 树里没有 T1）| 显式 `-p ep_no_billed_gate`，装上 |
| `test_f158_early_gate_regression._run_selfcheck`（本轮牙锁，跑 `test_probe.py`=T1 副本）| ✅ **就是要跑 T1**：门关跑（断言红）+ 门开跑（断言绿）| 门关分支故意不装；门开分支 `-p ep_no_billed_gate` |
| `test_gt_promotion_path` 变异矩阵（跑 `tests/test_gt_promotion_path.py`，cwd=mirror）| ❌ 只收 `test_gt_promotion_path.py`（T1 在别的文件）；且 T3 被 `-m "not mutation"` 排除 | 镜像拷了 pyproject 钉 + 插件 ⇒ 装上（T3 锁的就是这一条）|
| `-n 6` 每个 xdist worker | ✅ T1 在某一个 worker 上跑 | addopts `-p` 对 worker 生效 + 每个 worker 的 conftest 都 import 门 ⇒ 装上（全量绿里已验证）|

⇒ **没有一处会让 T1 意外炸**；凡有子 pytest 真跑到 F-158 附近，门都是装上的。

### #7 上一轮已成立的逐条不许退化

`tests/test_no_billed_provider_calls.py`（同步 OpenAI 路径=raw socket / create_connection / connect_ex / **urllib**）
+ `tests/test_f158_early_gate_regression.py`（复核方那个**双载体探针**：import 期 connect + 预绑定实例/类引用，两路 BLOCKED）
一并跑：

```
$ python -m pytest -q -n0 -p no:cacheprovider tests/test_affected_tests_map.py \
    tests/test_no_billed_provider_calls.py tests/test_f158_gate_behavioral_selfcheck.py \
    tests/test_f158_early_gate_regression.py
......................s....                                              [100%]
  BLOCKED ...test_raw_socket_connect_to_remote_is_blocked_and_names_this_test -> ('192.0.2.1', 80)
  BLOCKED ...test_socket_create_connection_to_remote_is_blocked -> ('192.0.2.1', 80)
  BLOCKED ...test_connect_ex_to_remote_is_blocked -> ('192.0.2.1', 80)
  BLOCKED ...test_urllib_request_to_remote_is_blocked -> ('192.0.2.1', 80)
  BLOCKED ...test_egress_gate_behaviorally_blocks_a_real_connection -> ('192.0.2.1', 80)
26 passed, 1 skipped in 70.25s
```
（`1 skipped` = `@pytest.mark.live` 那条，默认套件排除，未退化。）`test_early_and_prebound_carriers_are_blocked` 仍 `3 passed`（含 4 载体）。✅

### #8 全量绿（`-n 6`）· 带 / 不带 `.env` 两跑

- 基线 = `3717 passed / 2 skipped / 13 xfailed / 0 failed`（exit 0）。本轮新增 **3 个 passed**（T1 + 牙锁 + T3）⇒
  逐位闭合应为 `3717 + 3 = 3720 passed`。
- 本工作树**无 `.env` 文件**（`ls .env` 不存在，`.env` 被 gitignore）⇒ 默认跑即「不带 .env」；
  「带 .env」我造 dummy 键的 `.env`（门在 socket 层拦，dummy 键不会真出网），跑完删。
- ⚠️ 同机有 GPT 席位在跑全量（PID 24989，`-n 6`，导入 `evidence_contract`）⇒ 用 `-n 6`，判假红看 summary 行。

> ### ⭐ 以下两跑由 **orchestrator 代跑并据实补入**（2026-09-03 15:37–15:56 UTC）
> **原因**：施工席在等后台 run#1 时被切断。⭐ 它**没有留假数**，只留了一行「两跑完成后据实补入」——
> 该处理正确，故主控代跑而非要求它重来。

**环境自证（与 pytest 同一条命令）**：
```
$ cd /tmp/f158_rework2_claude && python -c "import ep_no_billed_gate as m; print('GATE', m.__file__)"
GATE /tmp/f158_rework2_claude/ep_no_billed_gate.py
```

**RUN 1 · 不带 `.env`**（`ls .env` 不存在 ⇒ 本跑即「不带」）：
```
$ python -m pytest -q -n 6 -p no:cacheprovider
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. ...
3720 passed, 2 skipped, 13 xfailed, 211 warnings in 469.26s (0:07:49)
RUN1_EXIT=0
```

**RUN 2 · 带 dummy `.env`**（`DEEPSEEK_API_KEY` / `OPENAI_API_KEY` 均为 dummy 串，跑完删）：
```
$ printf 'DEEPSEEK_API_KEY=dummy-not-a-real-key\nOPENAI_API_KEY=dummy-not-a-real-key\n' > .env
$ python -m pytest -q -n 6 -p no:cacheprovider
3720 passed, 2 skipped, 13 xfailed, 211 warnings in 569.49s (0:09:29)
RUN2_EXIT=0
$ rm -f .env && git status --porcelain
（空）
```

⇒ **逐位闭合成立**：`3717 + 3 = 3720`（T1 行为自检 + 牙锁 + T3 镜像插件锁）。
⇒ **带 / 不带 `.env` 两跑读数逐位相同**，`exit 0`，收尾树净。

---

## §六 停下上报

无 A 层触发（未动禁令、甲案实测可行、T1 不改任何已签字产物哈希/基线——它只加测试、改 test 插件 docstring）。
B 层记录：见 #1 的沙箱实测（连 TEST-NET 直接返回成功，非超时）、#5 的 T3 残留归属。

## §七 我自己认为最薄弱的一处

⭐ **T1 在真实 `tests/` 套件里恒绿，它的红只在【无 conftest 的最小树】里才出得来**——
因为 conftest 的纵深防御 import 会自装门。这意味着 T1 对**真实全量**里「有人 `-o addopts=`」这个具体场景
其实**测不到红**（conftest 兜底了）；它真正的价值是：① 一条不依赖任何接线（addopts 钉 / conftest / import 自装）
的**行为**兜底——三者若都失效（换 rootdir、删 conftest 那行、`-p no:conftest` 之类）它会红；② 把「门没装上」
这件事从代理量（`_INSTALLED`）搬到了**可观测行为**上。牙锁保证了它**能**红。
⇒ 若要更强，得让 T1 覆盖到 pre-parse 那一刻（那需要它本身是个 `-p` 插件、且钉在门之前跑），
但那又回到「堵启动形态」的无上界老路——**本轮按派工方边界，不做**。
