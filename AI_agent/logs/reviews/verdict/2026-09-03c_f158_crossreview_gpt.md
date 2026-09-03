# 跨家族复核 · 裁决 —— F-158 no-billed-calls gate

- **日期**：2026-09-03 · **复核方**：GPT 家族（施工方为 Claude，满足跨家族）
- **被审 commit**：`d3313f7`
- **工作树**：`/tmp/f158_review_gpt`
- **裁决**：⛔ **REWORK —— 阻断 1 · 不阻断 3**
- **核心结论**：现有默认全量已不再走已知的 DeepSeek provider 路径，带 / 不带 `.env`
  均为 `3672 passed, 2 skipped, 13 xfailed, 0 failed`；同步 OpenAI 路径与新造的异步
  httpx 路径都会在 socket 出口响亮失败并指名。**但“任何测试都结构性不可能出网”尚未成立**：
  在 `pytest_configure` 之前加载的插件能真连接，且它预先捕获的 bound `sock.connect` 在测试体内
  仍可绕门，整个过程门报 0。

计数口径：B-1 是同一个“安装时点晚于可执行导入代码”的根因，经“导入期调用”和“预绑定后调用”
两条腿复现，计 **1 条阻断**。N-1～N-3 是三个证据/文档问题，计 **3 条不阻断**。

---

## 〇、环境自证与纪律

开工第一条命令及输出原文：

```bash
$ pwd && git log --oneline -1 && git status --porcelain
$ python -c "import sys; print(sys.executable)"
/tmp/f158_review_gpt
d3313f7 09.03a_F158_execution_report
?? AI_agent/logs/reviews/request/2026-09-03c_f158_crossreview.md
/opt/venv/bin/python
```

环境可用；冻结 commit 与请求书一致。未运行 `pip install -e .`，未改 `src/` 或既有 `tests/`，
未执行 `git add -A`，也未修改 `/workspaces/EnergyPlus-Agent-dev`。临时探针均用新文件，取证后删除；
删除后状态为：

```bash
$ git status --porcelain
?? AI_agent/logs/reviews/request/2026-09-03c_f158_crossreview.md
```

---

## 一、施工方 §二 四项主张

### 1. 接缝：✅ 成立

代码确实只 wrap `socket.socket.connect` / `connect_ex`；构造 provider 客户端不触门。
临时测试只构造并关闭 `OpenAI(base_url="https://api.deepseek.com")`，不发送请求：

```bash
$ python -m pytest -q -n 6 -p no:cacheprovider \
    tests/test_f158_crossreview_probe.py::test_client_construction_is_not_blocked
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
1 passed in 1.79s
```

带 key 的修前 zone 原形探针则走到真实发送接缝，栈为
`OpenAI → httpx → httpcore → socket.create_connection → sock.connect`，并由门抛错：

```bash
$ set -a
$ . /workspaces/EnergyPlus-Agent-dev/.env
$ set +a
$ python - <<'PY'
import os
print('DEEPSEEK_API_KEY_SET', bool(os.environ.get('DEEPSEEK_API_KEY')))
print('OPENAI_API_KEY_SET', bool(os.environ.get('OPENAI_API_KEY')))
PY
$ python -m pytest -q -n 6 -p no:cacheprovider \
    tests/test_f158_original_zone_probe.py -rf
DEEPSEEK_API_KEY_SET True
OPENAI_API_KEY_SET False
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
...
/opt/venv/lib/python3.12/site-packages/httpcore/_backends/sync.py:208: in connect_tcp
    sock = socket.create_connection(
/usr/lib/python3.12/socket.py:850: in create_connection
    sock.connect(sa)
tests/conftest.py:145: in wrapper
    raise ProviderCallBlocked(
E   conftest.ProviderCallBlocked: F-158 no-billed-calls gate: test
    'tests/test_f158_original_zone_probe.py::test_zone_agent_creates_two_zones_original_shape'
    tried to open a real network connection to ('198.18.0.120', 443).
...
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
FAILED tests/test_f158_original_zone_probe.py::test_zone_agent_creates_two_zones_original_shape
1 failed in 14.04s
```

因此“拦发出请求、不是拦构造客户端”的实现与已知 provider 路径均验证成立。

### 2. T2 枚举：✅ 范围结论成立；⚠️ “第一次全量由门自己数出”字面不成立（N-2）

我用 `git show cb4df23:tests/test_zone_agent.py` 对照修前内容，新建等价临时测试；忽略当前替身版
`tests/test_zone_agent.py` 后跑完整全量。无 key 的独立读数与施工档逐位一致：

```bash
$ env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY python -c \
  "import os; print('DEEPSEEK_API_KEY_SET', bool(os.environ.get('DEEPSEEK_API_KEY'))); print('OPENAI_API_KEY_SET', bool(os.environ.get('OPENAI_API_KEY')))"
$ env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY python -m pytest -q -n 6 \
    -p no:cacheprovider --ignore=tests/test_zone_agent.py \
    --ignore=tests/test_f158_crossreview_probe.py \
    --ignore=tests/test_f158_zone_stub_probe.py
DEEPSEEK_API_KEY_SET False
OPENAI_API_KEY_SET False
bringing up nodes...
bringing up nodes...
...
FAILED tests/test_f158_original_zone_probe.py::test_zone_agent_creates_two_zones_original_shape
1 failed, 3671 passed, 1 skipped, 13 xfailed, 211 warnings in 486.86s (0:08:06)
```

唯一失败就是修前 zone 测试；带 key 的上一个聚焦实测又证明同一测试会真走 provider 出口并被门拦。
所以范围结论“只有这 1 条”成立。

但上面无 key 全量的实际异常是构造 `AsyncOpenAI` 时缺 key，发生在 socket 之前：

```text
src/agent/llm.py:96: in create_llm
    return init_chat_model(model_id, **kwargs)
...
E   openai.OpenAIError: The api_key client option must be set either by passing
    api_key to the client or by setting the OPENAI_API_KEY environment variable
```

故施工档把“第一次无 key 全量的 1 failed”称为“门自己枚举”的证据归属不准确。正确证据链是：
**无 key 全量锁定唯一候选 + 带 key 对该候选实测门命中**。结论不变，计 N-2 不阻断。

### 3. 修完全量：✅ 成立（有 / 无 `.env` 完全同数）

无 `.env`（显式 unset；进度点阵省略，首尾为原始输出）：

```bash
$ env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY bash -c '
pwd
python -c "import os,sys; import src.agent.pipeline as p; print(\"PYTHON\", sys.executable); print(\"MODULE_FILE\", p.__file__); print(\"DEEPSEEK_API_KEY_SET\", bool(os.environ.get(\"DEEPSEEK_API_KEY\"))); print(\"OPENAI_API_KEY_SET\", bool(os.environ.get(\"OPENAI_API_KEY\")))"
python -m pytest -q -n 6 -p no:cacheprovider --disable-warnings
'
/tmp/f158_review_gpt
PYTHON /opt/venv/bin/python
MODULE_FILE /tmp/f158_review_gpt/src/agent/pipeline.py
DEEPSEEK_API_KEY_SET False
OPENAI_API_KEY_SET False
bringing up nodes...
bringing up nodes...
...
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
3672 passed, 2 skipped, 13 xfailed, 211 warnings in 454.11s (0:07:34)
```

带 `.env`（只读 source，没有打印 secret；进度点阵省略）：

```bash
$ bash -c '
set -a
. /workspaces/EnergyPlus-Agent-dev/.env
set +a
pwd
python -c "import os,sys; import src.agent.pipeline as p; print(\"PYTHON\", sys.executable); print(\"MODULE_FILE\", p.__file__); print(\"DEEPSEEK_API_KEY_SET\", bool(os.environ.get(\"DEEPSEEK_API_KEY\"))); print(\"OPENAI_API_KEY_SET\", bool(os.environ.get(\"OPENAI_API_KEY\")))"
python -m pytest -q -n 6 -p no:cacheprovider --disable-warnings
'
/tmp/f158_review_gpt
PYTHON /opt/venv/bin/python
MODULE_FILE /tmp/f158_review_gpt/src/agent/pipeline.py
DEEPSEEK_API_KEY_SET True
OPENAI_API_KEY_SET False
bringing up nodes...
bringing up nodes...
...
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
3672 passed, 2 skipped, 13 xfailed, 211 warnings in 454.61s (0:07:34)
```

两次 passed / skipped / xfailed 完全一致，均 `0 failed`。验收 #5、#6 成立。

### 4. 出口：✅ 显式 `live`，默认 skip；无按 key 静默跳过

静态负检查与 marker 位置原始输出：

```bash
$ if rg -n 'pytest\.mark\.skipif|pytest\.skip\(' tests/conftest.py \
    tests/test_no_billed_provider_calls.py tests/test_zone_agent.py; then true; \
  else echo 'NO_RUNTIME_KEY_BASED_SKIP_PATH'; fi
$ rg -n '@pytest\.mark\.live|skip_live = pytest\.mark\.skip|if request\.node\.get_closest_marker\("live"\)' \
    tests/conftest.py tests/test_no_billed_provider_calls.py tests/test_zone_agent.py
NO_RUNTIME_KEY_BASED_SKIP_PATH
tests/test_zone_agent.py:133:@pytest.mark.live
tests/conftest.py:183:    if request.node.get_closest_marker("live"):
tests/conftest.py:200:    skip_live = pytest.mark.skip(reason="live provider test; select with -m live")
tests/test_no_billed_provider_calls.py:85:@pytest.mark.live
```

默认聚焦运行中两条 live 均 skip，离线 zone 测试实际通过；显式 `-m live` 时门牙的 live 对照
确实运行且门被抬起：

```bash
$ python -m pytest -q -n 6 -p no:cacheprovider \
    tests/test_no_billed_provider_calls.py tests/test_zone_agent.py
bringing up nodes...
bringing up nodes...

....s.s..                                                                [100%]
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
7 passed, 2 skipped in 2.78s

$ env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY python -m pytest -q -n 6 \
    -p no:cacheprovider -m live \
    tests/test_no_billed_provider_calls.py::test_live_marker_lifts_the_gate
bringing up nodes...
bringing up nodes...

.                                                                        [100%]
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
1 passed in 1.12s
```

2 skipped 恰为两条显式 live，不依赖 key 是否存在。施工方第四项主张成立。

---

## 二、请求书 §四：`-n6` 汇总恒 0 的裁定

### N-1（不阻断）—— 缺陷属实，但塌的是被引用证据，不是门的失败语义

同一轮 `-n6` 跑牙锁时，raw connect / create_connection / connect_ex 三条均在 worker 中被拦并由
`pytest.raises` 捕获，master 却打印 0：

```bash
$ python -m pytest -q -n 6 -p no:cacheprovider \
    tests/test_no_billed_provider_calls.py tests/test_zone_agent.py
bringing up nodes...
bringing up nodes...

....s.s..                                                                [100%]
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
7 passed, 2 skipped in 2.78s
```

更强的复现是本轮新形 async httpx 探针：worker 明确抛 `ProviderCallBlocked` 并使测试失败，
同一份终端摘要仍然报 0（全文见 §四）。所以该数在 `-n6` 下对 worker 阻断数没有分辨力，不能再被
执行档 §#2 当作“0 条被拦”的证据。

**阻断性裁定：不阻断。** 对门覆盖到的调用，`ProviderCallBlocked` 会沿调用链造成 failed；权威全量
`0 failed` 仍支撑“现有默认测试没有走该 provider 出口”。汇总读数的错误没有让已覆盖调用放行。
本裁定不替 B-1 的更早导入绕过免责；B-1 是另一条独立的执行缺口。

### 修法选择：选 **(b)**

把验收 #2 的权威证据改钉到 **failed 测试集合**，把 terminal summary 降级为 readout，并明写：
“xdist 并行时只反映 master 本进程，不能证明 workers 的 blocked 数为 0”。执行档 §#2 也应撤回
对该 0 的证据引用。

不选 (a) 的理由不是“跨 worker 做不到”，而是它并不直接恢复现有验收文字：默认全量本来就包含
三条牙锁，它们故意触门又捕获；正确跨 worker 汇总会是至少 3，而不是 0。若将来确需完整遥测，
可另做跨 worker、分“牙锁预期阻断 / 非预期阻断”的统计，但它不是本单结论的权威腿。

---

## 三、请求书 §五 两个假说

### 1. 替身是否空转：✅ 不空转；但它确实不测自然语言解析

临时语义探针把 `zone_specs` 改成 `THIS IS NOT A ZONE SPEC`，同时 spy 真实
`ZoneTool.create`，并断言 `create_llm(node_name="zone")` 的接缝与两个真实 create 调用；
没有 patch `build_react_agent` 或 `make_zone_tools`：

```python
assert factory_calls == [((), {"node_name": "zone"})]
assert [item["Name"] for item in created] == [
    "Z01_F1_Office_SW", "Z02_F1_Corridor_N",
]
assert {zone.name for zone in out["config_state"].zones} == {
    "Z01_F1_Office_SW", "Z02_F1_Corridor_N",
}
```

```bash
$ python -m pytest -q -n 6 -p no:cacheprovider \
    tests/test_f158_zone_stub_probe.py -vv
============================= test session starts ==============================
platform linux -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /opt/venv/bin/python
rootdir: /tmp/f158_review_gpt
configfile: pyproject.toml
plugins: langsmith-0.7.33, xdist-3.8.0, anyio-4.13.0
created: 6/6 workers
6 workers [1 item]

tests/test_f158_zone_stub_probe.py::test_stub_still_executes_real_zone_tool_but_does_not_parse_specs
[gw0] [100%] PASSED tests/test_f158_zone_stub_probe.py::test_stub_still_executes_real_zone_tool_but_does_not_parse_specs

F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
============================== 1 passed in 2.73s ===============================
```

判定：替身硬编码工具调用，因此即使输入是垃圾仍造出两 zone，**不测自然语言解析**；但它没有直接
篡改输出，两个 zone 是经真实 ReAct 图和真实 `ZoneTool.create` 装配进去的，所以仍测到 node 接缝、
ReAct 循环、真实工具与 ConfigState 装配。施工方已把“真模型解释自然语言”明确登记为默认覆盖丢失，
并移入显式 live 测试，符合任务书 T3/T4；不计缺陷。

### 2. B-1（阻断）—— `pytest_configure` 前导入与预绑定引用均能绕过

临时 `-p f158_preconfigure_probe` 插件在模块 import 时做两件事：

1. 对 TEST-NET `192.0.2.1:80` 调 `connect_ex`；
2. 在门安装前保存一个 bound `sock.connect`，测试体内再调用。

测试的期望写成“必须 BLOCKED”；实际两个调用均通过门，探针按预期红：

```bash
$ python -m pytest -q -n 6 -p no:cacheprovider -p f158_preconfigure_probe \
    tests/test_f158_crossreview_probe.py::test_preconfigure_and_early_bound_connect_bypass -rf
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
=================================== FAILURES ===================================
_______________ test_preconfigure_and_early_bound_connect_bypass _______________
[gw0] linux -- Python 3.12.13 /opt/venv/bin/python

>       assert result == "BLOCKED", (
            f"gate bypassed: IMPORT_CONNECT_EX_RESULT="
            f"{early.IMPORT_CONNECT_EX_RESULT}; EARLY_BOUND_CONNECT_RESULT={result}"
        )
E       AssertionError: gate bypassed: IMPORT_CONNECT_EX_RESULT=0; EARLY_BOUND_CONNECT_RESULT=CONNECTED
E       assert 'CONNECTED' == 'BLOCKED'
E         - BLOCKED
E         + CONNECTED

tests/test_f158_crossreview_probe.py:30: AssertionError
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
FAILED tests/test_f158_crossreview_probe.py::test_preconfigure_and_early_bound_connect_bypass
1 failed in 1.57s
```

`0 / CONNECTED` 证明调用不只“没有被门报”，而是真走到了内核/本机网络环境；探针使用 TEST-NET，
没有访问 provider。门仍自报 0。

施工方 docstring 只如实披露了“预绑定 bound method”盲区，却同时宣称 `pytest_configure` 安装能覆盖
“whole session / collection / module-import”。这个宣称对测试模块的普通收集期大体成立，
对更早插件 / initial conftest 的可执行导入期不成立。任务书规则是“任何测试试图发真实请求都必须
响亮失败”，不是“普通 test item 开始后才拦”；且这个绕过能在 pytest 仍全绿时真出网，故判阻断。

**返工验收要求**：门必须在任何可执行第三方插件 / initial conftest 导入之前安装（例如专用最早启动
插件在 import 时安装并钉死加载顺序；若不能保证 Python 插件加载顺序，则用进程/网络层 deny）；永久
加入两条牙锁：① 早期插件导入期连接，② 门前捕获 bound 引用后在测试体调用。两条都必须响亮失败并
留下可归因名称，不能只修改文档缩窄承诺。

---

## 四、请求书 §六：新形、真连接的第三条判据

临时测试使用现有牙锁没有覆盖的 `asyncio.run + httpx.AsyncClient(trust_env=False)`，目标为
TEST-NET；不写 `pytest.raises`，要求门自己令测试失败。原始输出：

```bash
$ python -m pytest -q -n 6 -p no:cacheprovider \
    tests/test_f158_crossreview_probe.py::test_new_shape_httpx_async_really_connects -rf
bringing up nodes...
bringing up nodes...

F                                                                        [100%]
=================================== FAILURES ===================================
__________________ test_new_shape_httpx_async_really_connects __________________
[gw1] linux -- Python 3.12.13 /opt/venv/bin/python
...
  |   File "/opt/venv/lib/python3.12/site-packages/httpcore/_backends/anyio.py", line 115, in connect_tcp
  |     stream: anyio.abc.ByteStream = await anyio.connect_tcp(
...
    |   File "/usr/lib/python3.12/asyncio/selector_events.py", line 659, in _sock_connect
    |     sock.connect(address)
    |   File "/tmp/f158_review_gpt/tests/conftest.py", line 145, in wrapper
    |     raise ProviderCallBlocked(
    | conftest.ProviderCallBlocked: F-158 no-billed-calls gate: test
    | 'tests/test_f158_crossreview_probe.py::test_new_shape_httpx_async_really_connects'
    | tried to open a real network connection to ('192.0.2.1', 80).
F-158 no-billed-calls gate: 0 provider calls blocked (this process; authoritative scope = FAILED tests across workers).
FAILED tests/test_f158_crossreview_probe.py::test_new_shape_httpx_async_really_connects
1 failed in 1.56s
```

✅ 新形异步 HTTP 路径仍被门拦住并准确指名，第三条判据通过；同时再次实证 N-1。

### N-3（不阻断）—— 文档声称牙锁已有 urllib/urllib3，实际没有永久锁

```bash
$ if rg -n 'urllib|urllib3|httpx' tests/test_no_billed_provider_calls.py; then true; \
  else echo 'NO_URLLIB_OR_HTTPX_LOCK_IN_TEETH_FILE'; fi
$ rg -n 'teeth test.*urllib|raw.*create_connection.*urllib|urllib3' tests/conftest.py \
    AI_agent/logs/reviews/execution/2026-09-03a_f158_no_billed_calls_claude.md
NO_URLLIB_OR_HTTPX_LOCK_IN_TEETH_FILE
AI_agent/logs/reviews/execution/2026-09-03a_f158_no_billed_calls_claude.md:29:1. **接缝能不能被绕过？** ... lock 里钉死了真正要紧的路径（原始 `socket`、`create_connection`、`urllib3` 都过 `socket.connect`）。
tests/conftest.py:34:matter (raw ``socket``, ``socket.create_connection``, ``urllib``).
```

这不影响本轮 async httpx 活体通过，也不影响 socket 接缝本身，故不阻断；但两份文档应改成
“由 `create_connection` 锁间接论证高层 HTTP 路径”，或补一条永久高层客户端锁，不能继续写成
已有 urllib/urllib3 牙锁。

---

## 五、逐条结案与返工边界

| 项 | 裁定 | 计数 |
|---|---|---:|
| §二 接缝 | 成立：构造不拦，sync provider 真发送会拦 | 通过 |
| §二 T2 范围 | 唯一 1 条成立；“第一次无 key 全量由门枚举”证据归属不准 | N-2，不阻断 |
| §二 修完 | 有 / 无 `.env` 均 `3672/2/13/0`，成立 | 通过 |
| §二 出口 | 显式 live、默认 skip、无 key-based skip，成立 | 通过 |
| §四 xdist 汇总 | 真缺陷；不阻断；选 **(b)**，撤销其证据资格 | N-1，不阻断 |
| §五 替身 | 不空转；真实工具装配仍测，解析维移入 live 且已登记 | 通过 |
| §五 更早导入 / 预绑定 | 两路均真绕过，pytest 可全绿而出网 | **B-1，阻断** |
| §六 新形 async httpx | 响亮失败并指名，成立 | 通过 |
| 牙锁文档 | 声称已有 urllib/urllib3 永久锁，实际没有 | N-3，不阻断 |

**最终：REWORK，阻断 1，不阻断 3。** 返工只需关闭 B-1 并补永久回归；N-1 按 (b) 修证据口径，
N-2/N-3 修文档与证据归属。无需改 `src/agent/nodes/*`、LLM 配置或 zone 替身方案。
