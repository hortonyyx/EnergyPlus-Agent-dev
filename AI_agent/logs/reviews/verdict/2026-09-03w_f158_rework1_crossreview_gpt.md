# 跨家族复核裁决 · F-158 第二轮返工

- 日期：2026-09-03
- 复核方：GPT 家族
- 施工方：Claude 家族
- 复核对象：净 diff 4dbf1de..e93ec76
- 复核工作树：/tmp/f158_rework_review_gpt
- 交付工作树 HEAD：431c44b；F-158 六个代码/测试文件与 e93ec76 相比无后续改动
- 结论：⛔ REWORK —— 阻断 1 / 不阻断 1

## 一、核心结论

上一轮的具体探针已经修好：在 4dbf1de 上仍能精确复现
IMPORT_CONNECT_EX_RESULT=0 / EARLY_BOUND_CONNECT_RESULT=CONNECTED；同一探针在
e93ec76 上两路均为 BLOCKED。

但是，“这一类缺陷”尚未关闭。修法把最早加载保证完全建立在 pyproject.toml 的
ini addopts 上，而 pytest 的 -o addopts= 可以在不改 pyproject.toml 的情况下替换该输入。
我用一个不同于施工方四种常驻载体的新载体验证：

1. 用 -o addopts= 移除 ini 注入的 -p ep_no_billed_gate；
2. 让命令行插件在 import 期通过禁用代理的 urllib 访问 RFC 5737 TEST-NET；
3. 默认配置 control 被 ProviderCallBlocked 拦住；仅加入 -o addopts= 后，结果变成
   NOTBLOCKED(TimeoutError: timed out)，测试 exit 1。

这不是 provider 调用失败后的普通业务异常：control 已验证探针能识别被 URLError 包裹的
ProviderCallBlocked；变异读数中异常链没有 ProviderCallBlocked，调用已经越过门进入真实网络路径。
目标是 TEST-NET 且显式禁用代理，未访问真实 provider。

因此判据③失败，仍可在 pytest 全量之外的合法启动形态中让 test-owned 插件先于门运行。
这与上一轮 B-1 是同一个根因，计一条阻断，不重复计数。

## 二、环境与范围自证

开工第一条命令：

~~~bash
$ cd /tmp/f158_rework_review_gpt && pwd && git log --oneline -1 && git status --porcelain
$ python -c "import ep_no_billed_gate as m; print(m.__file__)"
~~~

原始输出：

~~~text
/tmp/f158_rework_review_gpt
431c44b 09.03v_dispatch_B3_v2_and_F158_rework_crossreview
（git status --porcelain 无输出）
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
~~~

未运行 pip install -e .，未改 src/、既有测试或施工代码，未写
/workspaces/EnergyPlus-Agent-dev。切换 4dbf1de / e93ec76 只用于判据①②，随后恢复
431c44b。临时探针取证后全部删除。

静态范围检查：

~~~text
$ git diff --check 4dbf1de..e93ec76
（无输出）

$ git diff --name-status e93ec76..HEAD -- ep_no_billed_gate.py pyproject.toml \
  tests/conftest.py tests/test_f158_early_gate_regression.py \
  tests/test_no_billed_provider_calls.py tests/test_gt_promotion_path.py
（无输出）
~~~

## 三、返工审三条判据

### ① 旧提交上，上一轮探针仍能复现绕过：通过

4dbf1de 尚无 ep_no_billed_gate.py，所以同一命令改用当时实际承载门的
tests.conftest 做模块落点自证。

~~~bash
$ git switch --detach 4dbf1de
$ python -c "import tests.conftest as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider \
  -p f158_preconfigure_probe \
  tests/test_f158_crossreview_probe.py::test_preconfigure_and_early_bound_connect_bypass -rf
~~~

原始关键输出：

~~~text
/tmp/f158_rework_review_gpt/tests/conftest.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
=================================== FAILURES ===================================
_______________ test_preconfigure_and_early_bound_connect_bypass _______________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

E       AssertionError: gate bypassed: IMPORT_CONNECT_EX_RESULT=0; EARLY_BOUND_CONNECT_RESULT=CONNECTED
E       assert (0 == 'BLOCKED')
E        +  where 0 = early.IMPORT_CONNECT_EX_RESULT

tests/test_f158_crossreview_probe.py:19: AssertionError
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
=========================== short test summary info ============================
FAILED tests/test_f158_crossreview_probe.py::test_preconfigure_and_early_bound_connect_bypass
1 failed in 1.03s
~~~

exit 1；精确复现上一轮两个读数。

### ② 新提交上，同一探针两路均 BLOCKED：通过

~~~bash
$ git switch --detach e93ec76
$ python -c "import ep_no_billed_gate as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider \
  -p f158_preconfigure_probe \
  tests/test_f158_crossreview_probe.py::test_preconfigure_and_early_bound_connect_bypass -rf
~~~

原始输出：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
================== F-158 no-billed-calls gate: BLOCKED calls ===================
  BLOCKED <collection/import phase> -> ('192.0.2.1', 80)
1 passed in 1.08s
~~~

exit 0。import 期 connect_ex 的 BLOCKED 出现在 master readout；预绑定实例方法在 worker
测试体中的断言也通过，故两路均已被拦。

### ③ 自造同形不同实例载体：失败，构成 B-1 阻断

施工方常驻回归锁已有四种：

1. import 期 socket.connect_ex；
2. import 期 socket.create_connection；
3. import 期预绑定实例 sock.connect，测试体调用；
4. import 期预绑定类属性 socket.socket.connect，测试体调用。

我的载体不同：替换的是“装门时刻”的配置输入本身，即 -o addopts=；调用面使用禁代理的
urllib opener。它不是以上四种连接/引用载体。施工锁的子进程恰好显式写死
-p ep_no_billed_gate，并同时用 -o addopts= 清空 ini，因此没有覆盖“生产接线被 -o 替换”
这一形态；静态排序锁也只读取文件内容，无法观察 CLI override 后的有效配置。

先跑默认配置 control：

~~~bash
$ python -c "import ep_no_billed_gate as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider \
  -p f158_addopts_override_probe \
  tests/test_f158_addopts_override_probe.py::test_addopts_replacement_cannot_remove_early_gate -rf
~~~

原始输出：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
================== F-158 no-billed-calls gate: BLOCKED calls ===================
  BLOCKED <collection/import phase> -> ('192.0.2.1', 80)
1 passed in 1.05s
~~~

仅加入 -o addopts=：

~~~bash
$ python -c "import ep_no_billed_gate as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider -o addopts= \
  -p f158_addopts_override_probe \
  tests/test_f158_addopts_override_probe.py::test_addopts_replacement_cannot_remove_early_gate -rf
~~~

原始输出：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
=================================== FAILURES ===================================
______________ test_addopts_replacement_cannot_remove_early_gate _______________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

    def test_addopts_replacement_cannot_remove_early_gate():
>       assert probe.ADDOPTS_OVERRIDE_URLLIB_RESULT == "BLOCKED", (
            "gate bypassed after -o addopts=: "
            f"ADDOPTS_OVERRIDE_URLLIB_RESULT={probe.ADDOPTS_OVERRIDE_URLLIB_RESULT}"
        )
E       AssertionError: gate bypassed after -o addopts=: ADDOPTS_OVERRIDE_URLLIB_RESULT=NOTBLOCKED(TimeoutError: timed out)
E       assert 'NOTBLOCKED(T...r: timed out)' == 'BLOCKED'
E
E         - BLOCKED
E         + NOTBLOCKED(TimeoutError: timed out)

tests/test_f158_addopts_override_probe.py:7: AssertionError
=========================== short test summary info ============================
FAILED tests/test_f158_addopts_override_probe.py::test_addopts_replacement_cannot_remove_early_gate
1 failed in 1.33s
~~~

exit 1。这里前置的 python -c 只证明模块解析位置；它是另一个进程，不会替 pytest
进程装门。pytest 进程中，命令行插件先执行了 urllib；之后 tests/conftest.py 才 import
ep_no_billed_gate，已无法追回 import 期调用。

阻断判定：返工修好了既有例子，但没有修好“启动载体可被换掉”这一类缺陷。pyproject.toml
内排序正确并不等于有效 addopts 不可被替换。

## 四、全量与带/不带 .env 对照

两轮均在交付 HEAD 431c44b 上运行；相关 F-158 文件与 e93ec76 相同。全部固定 -n 6。
以下保留命令及所有非进度点阵输出原文；pytest -q 的纯点阵中段不承载额外读数，明确折叠，
没有用施工方自述补数。

### 1. 不带 .env

命令原文：

~~~bash
$ env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY bash -c '
python -c "import os, ep_no_billed_gate as m; print(m.__file__); print(\"DEEPSEEK_API_KEY_SET\", bool(os.environ.get(\"DEEPSEEK_API_KEY\"))); print(\"OPENAI_API_KEY_SET\", bool(os.environ.get(\"OPENAI_API_KEY\")))"
python -m pytest -q -n 6 -p no:cacheprovider --disable-warnings
'
~~~

输出原文（纯点阵中段折叠）：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
DEEPSEEK_API_KEY_SET False
OPENAI_API_KEY_SET False
bringing up nodes...
bringing up nodes...

........................................................................ [  1%]
（中间均为 pytest -q 进度点阵；无 F/E）
.........................................................s.........x.... [ 98%]
............................................................             [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
3717 passed, 2 skipped, 13 xfailed, 211 warnings in 485.74s (0:08:05)
~~~

exit 0；与基线 3717 / 2 / 13 / 0 完全一致。

### 2. 带 .env

复核树自身没有 .env；只读 source /workspaces/EnergyPlus-Agent-dev/.env，未输出 secret，
也未写该主树。

命令原文：

~~~bash
$ bash -c '
set -a
. /workspaces/EnergyPlus-Agent-dev/.env
set +a
python -c "import os, ep_no_billed_gate as m; print(m.__file__); print(\"DEEPSEEK_API_KEY_SET\", bool(os.environ.get(\"DEEPSEEK_API_KEY\"))); print(\"OPENAI_API_KEY_SET\", bool(os.environ.get(\"OPENAI_API_KEY\")))"
python -m pytest -q -n 6 -p no:cacheprovider --disable-warnings
'
~~~

输出原文（纯点阵中段折叠）：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
DEEPSEEK_API_KEY_SET True
OPENAI_API_KEY_SET False
bringing up nodes...
bringing up nodes...

........................................................................ [  1%]
（中间均为 pytest -q 进度点阵；无 F/E）
.........................................................s.............. [ 98%]
..........................................................               [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
3717 passed, 2 skipped, 13 xfailed, 211 warnings in 463.86s (0:07:43)
~~~

exit 0。两轮 passed / skipped / xfailed / failed 逐项相同，验收 #6 与验收 #4 的
.env 对照腿成立。

## 五、验收 #4/#5 与常驻牙锁

### 1. 常驻早期锁、socket/urllib 牙锁

~~~bash
$ python -c "import ep_no_billed_gate as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider \
  tests/test_f158_early_gate_regression.py \
  tests/test_no_billed_provider_calls.py -rf
~~~

原始输出：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
bringing up nodes...
bringing up nodes...

.......s..                                                               [100%]
F-158 no-billed-calls gate READOUT (non-authoritative): 0 provider calls blocked in THIS process. Under -n parallelism this is the master process only, not workers; authoritative evidence that no billed call happened = the suite's FAILED-test set.
9 passed, 1 skipped in 1.47s
~~~

默认 skip 的一条正是显式 live 测试；urllib 永久牙锁通过。施工方“摘掉 import 期
_install() 后常驻锁必须红”的源代码变异过程：未复现。复核方遵守“不改代码”，没有修改
跟踪文件；判据①已在真实旧提交上独立复现同一根因，判据②验证恢复后绿。

### 2. 同步 OpenAI 真发送响亮失败并指名

临时测试使用假 key、禁用代理的 httpx.Client 和 https://198.18.0.120，未捕获异常。

~~~bash
$ python -c "import ep_no_billed_gate as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider \
  tests/test_f158_provider_paths_probe.py::test_sync_openai_real_send_is_blocked_and_named -rf
~~~

原始关键输出：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
E       ep_no_billed_gate.ProviderCallBlocked: F-158 no-billed-calls gate: test 'tests/test_f158_provider_paths_probe.py::test_sync_openai_real_send_is_blocked_and_named' tried to open a real network connection to ('198.18.0.120', 443).
E       openai.APIConnectionError: Connection error.
FAILED tests/test_f158_provider_paths_probe.py::test_sync_openai_real_send_is_blocked_and_named
1 failed in 3.37s
~~~

exit 1 是阳性牙锁预期：ProviderCallBlocked 是 APIConnectionError 的直接 cause，且测试名与
目标地址均清楚。

### 3. 异步 httpx 真发送响亮失败并指名

~~~bash
$ python -c "import ep_no_billed_gate as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider \
  tests/test_f158_provider_paths_probe.py::test_async_httpx_really_connects_is_blocked_and_named -rf
~~~

原始关键输出：

~~~text
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
| ep_no_billed_gate.ProviderCallBlocked: F-158 no-billed-calls gate: test 'tests/test_f158_provider_paths_probe.py::test_async_httpx_really_connects_is_blocked_and_named' tried to open a real network connection to ('192.0.2.1', 80).
FAILED tests/test_f158_provider_paths_probe.py::test_async_httpx_really_connects_is_blocked_and_named
1 failed in 1.51s
~~~

exit 1 同样是阳性牙锁预期。异常组根因明确为 ProviderCallBlocked，并指名测试与地址。
两个临时 provider 探针取证后均已删除。

### 4. N-1/N-2/N-3 口径

- N-1：通过。terminal summary 已明确写为 READOUT (non-authoritative)，说明 -n 下只看
  master，并把权威证据钉到 FAILED-test set；本轮聚焦与两次全量均实测到新文案。
- N-2：文档已改成“无 key 锁定候选 + 带 key 活体命中”的正确证据归属；本轮没有重新
  制造上一轮修前 zone 候选，故该历史枚举读数未复现。
- N-3：通过。新增 test_urllib_request_to_remote_is_blocked，聚焦实测通过，产物与文档一致。

## 六、派工方点名 P-1 / P-2 / P-3

### P-1：启动器溢出面没有完整覆盖；并入 B-1，不重复计数

当前已知树内溢出处理是有效的：

- tests/test_gt_promotion_path.py 的镜像 helper 在复制 pyproject.toml 时同步复制
  ep_no_billed_gate.py；
- 两次 3717 全量均 exit 0，说明当前 25 条 promotion mutation 等现存子 pytest 没有退化；
- 相关 F-158 文件在 e93ec76 到 431c44b 间无后续漂移。

但“完整覆盖”不成立。新增静态锁只断言 pyproject 文件里的第一个 -p 是门插件；它不检查
pytest 解析 -o addopts= 后的有效配置。我的判据③已证明启动器输入可被替换，故 P-1 的未覆盖
部分与 B-1 同根，只计一条阻断。

### P-2：隐式依赖边成立；当前不阻断，计 N-1

全仓 tests 下对 pyproject.toml 的实际镜像复制只有：

~~~text
tests/test_gt_promotion_path.py:583: shutil.copy2(REPO / "pyproject.toml", mirror / "pyproject.toml")
tests/test_gt_promotion_path.py:587: shutil.copy2(REPO / "ep_no_billed_gate.py", mirror / "ep_no_billed_gate.py")
~~~

当前唯一实例已配对且被两次全量覆盖，所以不阻断本交付。但这确实是常驻的隐式依赖：
未来新增“复制 pyproject + 子 pytest”位置时，结构锁不会自动要求同时复制门插件。其失败会在
子 pytest 启动时报 ImportError，不会静默放行 provider，因此按维护/扩展风险计 1 条不阻断。

### P-3：薄 re-export 退化没有掉现有 hook / fixture / 副作用；不计 finding

旧 tests/conftest.py 与新 ep_no_billed_gate.py 的可执行表面对照为：

~~~text
pytest_configure
pytest_unconfigure
@pytest.fixture(autouse=True) _lift_gate_for_live
pytest_collection_modifyitems
pytest_terminal_summary
~~~

五项逐一保留；_is_local、_current_test、_record、_guarded、_install/_uninstall、
ProviderCallBlocked 与状态也都迁移。新实现只增加 import 期安装和幂等状态，并按 N-1 修改
readout 文案。仓内没有其他 Python 文件从 conftest import；薄壳仍 re-export
ProviderCallBlocked 与 _is_local。常驻聚焦 9 passed / 1 skipped 和两次全量进一步证明 hook、
fixture、live skip 与本地连接许可未退化。因此 P-3 判“不成立”。

## 七、最终计数与返工边界

| 编号 | 性质 | 裁定 |
|---|---|---|
| B-1 | 阻断 | -o addopts= 可替换门的唯一早期接线；命令行插件 import 期 urllib 越门 |
| N-1 | 不阻断 | pyproject.toml 与仓库根插件存在未来镜像复制的隐式依赖，当前唯一实例已配对且全量绿 |

最终：REWORK，阻断 1，不阻断 1。

返工目标仍是关闭“更早 test-owned 代码先于门执行”这类缺陷，而不只是再把本次 urllib
探针加入现有显式 -p gate 的四载体锁。修复后至少应让 -o addopts= 这一启动输入变体也不能
使早期插件越门，并为“有效启动配置”而非仅 pyproject 静态文本补永久回归。

裁决完成后的最终状态：

~~~text
$ git status --porcelain
?? AI_agent/logs/reviews/verdict/2026-09-03w_f158_rework1_crossreview_gpt.md
$ python -c "import ep_no_billed_gate as m; print(m.__file__)"
/tmp/f158_rework_review_gpt/ep_no_billed_gate.py
~~~

除本裁决文件外工作树干净。
