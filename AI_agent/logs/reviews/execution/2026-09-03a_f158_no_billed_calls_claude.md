# 执行档 · F-158：让「跑测真打一次计费 provider 调用」结构上不可能

- **日期**：2026-09-03 · **施工席**：Claude 家族 · **worktree**：`/tmp/f158_claude` · **分支**：`wt/09.02x_f158` · **基线**：`cb4df23`
- **任务书**：[`2026-09-02x_f158_no_billed_calls_in_suite.md`](../request/2026-09-02x_f158_no_billed_calls_in_suite.md)
- **本次是【重新实现】**：孤儿件（`logs/experiments/2026-09-02_f158_orphan_wip/`，⚠️ 该目录未提交到本分支基线，我从主树**只读**）仅作线索；门与替身全部从零重写并自补锁。孤儿 README 的 5 处疑点在下方 §疑点作答里逐条回答。

## 分段提交（4 笔，⛔ 无孤儿）

```
4ba0ec9 09.03a_F158_egress_gate_conftest      (tests/conftest.py           216 +)
18a8641 09.03a_F158_gate_teeth_locks          (tests/test_no_billed_...    99 +)
7dcfbfe 09.03a_F158_zone_agent_offline_stub_plus_live (tests/test_zone_agent.py 132/23)
<本档提交>                                      (execution 交件)
```

---

## 接缝选择（T1）：拦【发出请求】那一层，不是【构造客户端】

门 = 在 `tests/conftest.py` 里 wrap `socket.socket.connect` / `socket.socket.connect_ex`（**网络出口点**）。理由：
- **构造 LLM 客户端不花钱**，且有测试合法地构造（schema 往返、工具接线）；**只有向可路由远端发出字节**才扣 DeepSeek 共用余额。
- `socket.connect` **provider/HTTP 库无关**：真实计费路径 `langchain_openai → openai SDK → httpx → httpcore → socket.create_connection`，而 `create_connection` 内部建 socket 后调 `.connect()`，全走这个被 wrap 的类方法。⇒ **换 HTTP 客户端库换不掉被测的那个东西**（[[gate-measures-right-but-carrier-gets-swapped]]）。
- **唯一合法出口 = 显式 `@pytest.mark.live`**（默认全量排除，`-m live` 才选）；⛔ **没有「没钥匙就跳过」这条静默路径**。

---

## 疑点作答（孤儿 README 5 问，逐条实测）

1. **接缝能不能被绕过？** 残余盲区如实标注在 conftest docstring：拦的是**类属性**，抓不到「已捕获 bound `sock.connect` 引用」或「C 层/io_uring 直连」的调用者——但**真实 provider 路径不走那些**，且 lock 里钉死了真正要紧的路径（原始 `socket`、`create_connection`、`urllib3` 都过 `socket.connect`）。#1 实测：故意连 `api.deepseek.com` 被拦，报出解析后的 IP。
2. **`_is_local` 用字符串前缀？** 改用 `ipaddress`：`::1` / `::ffff:127.0.0.1`（走 `ipv4_mapped`）/ 整个 `127.0.0.0/8` 全识别，外网/`api.deepseek.com` 一律判远端。单测 `test_is_local_*` 覆盖。
3. **只在测试执行期装门，收集/import 期不设防？** 改为 `pytest_configure` 装、`pytest_unconfigure` 卸 → **全会话在线**，收集期/import 期的连接同样被拦；`@pytest.mark.live` 测试体内经 autouse fixture 临时抬门。
4. **有没有牙没验证 + 是否踩「跳过」禁令？** #3 实测门有牙（摘门 → `DID NOT RAISE` 红）；出口是**显式人写 marker**（选项②），不是 `skipif(no key)`，未踩 #6 禁令。
5. **`EP_NO_BILLED_LOG` 可选 → 还算门自己在数吗？** 改为门**无条件**在内存累计 + `pytest_terminal_summary` 每轮打印（见 #3 复跑的 `BLOCKED ... ('192.0.2.1', 80)`）；`EP_NO_BILLED_LOG` 降级为**可选附加**机读 sink。

---

## T2 枚举结果（⭐ 用门自己数，⛔ 非 grep 名单）

带门跑全量（`-n 6`，无替身、无 .env），**唯一进入范围的真实测试 = 1 条**：

```
FAILED tests/test_zone_agent.py::test_zone_agent_creates_two_zones - openai.OpenAIError
1 failed, 3671 passed, 1 skipped, 13 xfailed in 467.07s
```

- ⭐ **印证任务书 §一**：派工方 grep 名单里的 `test_output_coordinate_application.py` **并未红**（它离线测 `make_zone_tools`，不发请求）⇒ grep 名单**多列了一个**，不可信。
- ⚠️ **一个实测细节**：在**无 key** 的 shell 里，`test_zone_agent` 是在**构造 openai 客户端**阶段抛 `OpenAIError("api_key must be set")`，**在 `socket.connect` 之前**，所以本 shell 里门没拦它、`EP_NO_BILLED_LOG` 里没有它——它是**因缺钥匙红**。**带 key 的席位**（source .env）则会真连 `api.deepseek.com` → 被门拦。两种情形都指向同一条测试要治。这正是任务书说「每个 worktree 席位必红一条」的机制。

（`EP_NO_BILLED_LOG` 里仅有的 3 行是我自己 lock 里 `pytest.raises` 故意触发并捕获的 `test_no_billed_provider_calls.py::test_{raw_socket,connect_ex,create_connection}_*`，非真实缺陷。）

---

## T3 处置：test_zone_agent（选①替身 + 保留②live）

- `test_zone_agent_creates_two_zones` → **改用 `_ScriptedLLM` 假模型**（`monkeypatch` `src.agent.nodes.zone.create_llm`），脚本发两次 `create_zone` 工具调用后收尾。**仍测**：zone_agent 节点自身组合（create_llm 槽→build_react_agent→make_zone_tools）、**真** `create_zone` 工具改 `ConfigState`、ReAct 循环接线、结果抽取、尾部 frame 归零。离线、默认全量内。
- 新增 `test_zone_agent_creates_two_zones_live`（`@pytest.mark.live`）= **原真 provider 路径**，默认排除、`-m live` 才跑，**保留**真模型集成覆盖。

## T4 覆盖欠账清单

| 测试 | 处置 | 默认全量丢了什么覆盖 | 去哪了 |
|---|---|---|---|
| `test_zone_agent_creates_two_zones` | ① 替身 | 「**真模型**把自然语言 `zone_specs` 解读成两个正确命名的 zone」这一维 | 移到 `test_zone_agent_creates_two_zones_live`（`-m live`）|
| （无②：范围仅 1 条，已用①保留大部分覆盖 + 新增 live 兜底真模型维）| | | |

**旁注（覆盖仍在别处）**：ReAct 循环韧性由 `test_react_llm_resilience.py`（同用假模型）离线覆盖；`make_zone_tools`/`create_zone`/ConfigState 装配由 `test_output_coordinate_application.py` 离线覆盖。⇒ 唯一净丢失就是上表那一维。

---

## 逐条对验收 §四（六条）

### #1 任何测试发真实请求 ⇒ 响亮失败并指名自己（造临时测试取证后删）
命令 + 输出原文：
```
$ cat > tests/test_f158_temp_deliberate.py   # socket.create_connection(("api.deepseek.com",443),timeout=2)
$ python -m pytest tests/test_f158_temp_deliberate.py -n 6 -p no:cacheprovider -q -rf
E   conftest.ProviderCallBlocked: F-158 no-billed-calls gate: test
    'tests/test_f158_temp_deliberate.py::test_f158_deliberately_calls_out' tried to open a real
    network connection to ('198.18.0.120', 443). This would emit a real, billed provider request.
    Give it a fake/stub ... or ... mark it @pytest.mark.live ...
FAILED tests/test_f158_temp_deliberate.py::test_f158_deliberately_calls_out
$ rm tests/test_f158_temp_deliberate.py && git status --porcelain     # (空)
```
✅ **红 + 指名自己**（连 `api.deepseek.com` 解析后的 IP 也打出来），取证后删、树干净。

### #2 默认全量里被门拦下的条数 = 0
门自报（无 key 权威全量末行）：`F-158 no-billed-calls gate: 0 provider calls blocked`；全量 `0 failed`（见 #5）。✅

### #3 门有牙：摘门 ⇒ 至少一条红 → 恢复 → git 干净
```
$ # 临时把 _install() 改成 no-op
$ python -m pytest tests/test_no_billed_provider_calls.py::test_socket_create_connection_to_remote_is_blocked -n0 -q -rf
E   Failed: DID NOT RAISE <class 'conftest.ProviderCallBlocked'>
FAILED tests/test_no_billed_provider_calls.py::test_socket_create_connection_to_remote_is_blocked
$ git checkout -- tests/conftest.py && git status --porcelain      # (空)
$ python -m pytest ...::test_socket_create_connection_to_remote_is_blocked -n0 -q
  BLOCKED tests/test_no_billed_provider_calls.py::test_socket_create_connection_to_remote_is_blocked -> ('192.0.2.1', 80)
1 passed
```
✅ 摘门即红、恢复后 `git status` 空、复跑绿。

### #4 每条被改的测试仍测到原本要测的东西；做不到明写丢了什么
见 §T3 + §T4。zone 替身保留节点组装+真工具+装配；唯一丢失（真模型解读）已登记并移到 live。✅

### #5 全量绿（`-n 6`，环境自证同命令）
**无 .env shell**（同一条命令带自证）：
```
MODULE_FILE /tmp/f158_claude/src/agent/pipeline.py
ZONE_MODULE_FILE /tmp/f158_claude/src/agent/nodes/zone.py
DEEPSEEK_API_KEY_SET False   OPENAI_API_KEY_SET False
...
3672 passed, 2 skipped, 13 xfailed, 211 warnings in 486.87s (0:08:06)   EXIT=0
```
✅ `0 failed`。（2 skipped = 两条 live：`test_live_marker_lifts_the_gate` + `test_zone_agent_creates_two_zones_live`。）

### #6 不带 .env 也绿（+ 带 .env 对照）
- **不带 .env**（这正是本单兑现）：即上面 #5 的读数，`DEEPSEEK_API_KEY_SET False` 下 `0 failed`。✅
  ⛔ **未用「跳过没钥匙的测试」凑绿**：zone 测试是**替身跑过**（不是 skip），2 skipped 是显式 `live` marker、与钥匙无关。
- **带 .env 对照**（`source /workspaces/.../.env`）：
```
MODULE_FILE /tmp/f158_claude/src/agent/pipeline.py
DEEPSEEK_API_KEY_SET True
...
3672 passed, 2 skipped, 13 xfailed, 211 warnings in 536.89s (0:08:56)   EXIT=0
```
✅ **带钥匙也 `0 failed`、门自报 0 blocked** —— 证明修好后（zone 走替身、live 显式排除）**即便有 key 也无任何测试发出连接、无扣费**。两次读数（无 key / 带 key）**passed 数完全一致（3672/2/13）**。

---

## 停下上报

- **A 层**：无。范围仅 1 条（<5），未触及 §三禁令。
- **B 层（记一条继续）**：
  1. 任务书 §六与启动提示词交件文件名不一致（§六写 `2026-09-02x_...`，启动提示词写 `2026-09-03a_...`）；按启动提示词落 `2026-09-03a_...`。
  2. 孤儿归档目录 `logs/experiments/2026-09-02_f158_orphan_wip/` **未提交到本分支基线 `cb4df23`**（在主树/其他 worktree 里有）；我从主树**只读**了它，未改动任何 `/workspaces` 内容。
  3. 无 key shell 下 `test_zone_agent` 的红是**缺 key 的 `OpenAIError`**（构造客户端阶段），发生在 `socket.connect` 之前 → 门在此 shell 未直接拦它；带 key 才由门拦。两路都指向同一条测试，处置一致，不影响结论。
