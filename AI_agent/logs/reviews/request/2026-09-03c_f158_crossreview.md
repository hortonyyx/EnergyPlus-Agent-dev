# 跨家族复核请求 · **F-158**（跑测不许真打计费 provider 调用）

- **日期**：2026-09-03 · **请审方**：orchestrator · **复核方**：**GLM 家族**（⛔ 不得 Claude —— 施工方是 Claude 席）
- **被审 commit**：`d3313f7`（分支顶；施工原件 `aa6b61a` 等四笔，`cherry-pick -x` 落地）
- **任务书**：[2026-09-02x](2026-09-02x_f158_no_billed_calls_in_suite.md) · **交件**：[执行档](../execution/2026-09-03a_f158_no_billed_calls_claude.md)

## 一、diff（⛔ 只列代码）

```
216	0	tests/conftest.py                      ← 出口门（socket egress）
99	0	tests/test_no_billed_provider_calls.py ← 门的牙锁
132	23	tests/test_zone_agent.py               ← 替身 + live 变体
```

## 二、施工方的主张（⚠️ 自己验，⛔ 别照抄）

| | 主张 |
|---|---|
| 接缝 | 拦**网络出口**（`socket.socket.connect` / `connect_ex`），⛔ 不拦「构造客户端」 |
| T2 枚举 | ⭐ **用门自己数出来的**：第一次跑全量 `1 failed, 3671 passed` —— 那条 failed 就是真打调用的 `test_zone_agent` |
| 修完 | `3672 passed / 2 skipped / 13 xfailed / 0 failed`，**带 `.env` 与不带 `.env` 两次读数 passed 数完全一致** |
| 出口 | `@pytest.mark.live` 显式标记（默认 skip），⛔ 无「没钥匙就跳过」的静默路径 |

## 三、⭐ 主控已自查、**⛔ 不必重做**的三条（逐条查过，**全部不成立**）

1. ~~「只包了 `connect`，`connect_ex` 能绕过」~~ ⇒ ⛔ 不成立：`_install()` 两个都包（`conftest.py:157-159`）。
2. ~~「`_is_local` 用字符串前缀，IPv6 回环绕得过」~~ ⇒ ⛔ 不成立：用的是 `ipaddress`，`is_loopback` / `is_unspecified` / IPv4-mapped 都覆盖。
3. ~~「`live` 抬门会泄漏到后续测试」~~ ⇒ ⛔ 不成立：`try/finally` 里复位（`conftest.py:183-189`）。

## 四、⭐⭐⭐ 主控实测发现的**一条真缺陷**（⛔ 已量，不是假说）

> **门自报的那行「0 provider calls blocked」，在 `-n 6` 下是【结构性恒 0】的 —— 它是个代理量。**

`_BLOCKED` 是**每进程**的列表，而 xdist 的 master 进程**从不执行测试**。实测（同一批测试）：

```bash
$ python -m pytest -q -n0 -p no:cacheprovider tests/test_no_billed_provider_calls.py | tail -6
================== F-158 no-billed-calls gate: BLOCKED calls ===================
  BLOCKED ...::test_raw_socket_connect_to_remote_is_blocked_and_names_this_test -> ('192.0.2.1', 80)
  BLOCKED ...::test_socket_create_connection_to_remote_is_blocked -> ('192.0.2.1', 80)
  BLOCKED ...::test_connect_ex_to_remote_is_blocked -> ('192.0.2.1', 80)
6 passed, 1 skipped in 0.63s

$ python -m pytest -q -n2 -p no:cacheprovider tests/test_no_billed_provider_calls.py | tail -6
F-158 no-billed-calls gate: 0 provider calls blocked (this process; ...).
6 passed, 1 skipped in 1.34s          ← ⛔ 同样三条被拦，汇总却说 0
```

⇒ **任务书验收 #2 原文要求「贴门自己的枚举输出（空）」，而那份输出在并行下【不论有没有被拦都是空的】。**

⭐ **但请公平判**（⛔ 别把这条判过头）：
- **结论仍然成立** —— 被拦会抛 `ProviderCallBlocked` ⇒ **会变成 failed 测试**，而全量 `0 failed`。
  所以「没有测试发出真实连接」这个**结论**由**另一条腿**（0 failed）撑着，⛔ 塌的是**被引用的那件证据**。
- 施工方**在那行字里自己写了 hedge**（"authoritative scope = FAILED tests across workers"）
  —— 说明它知道；⚠️ 但**执行档里仍把这行当证据引用**了（§#2）。
- ⇒ 这正是 [[proxy-mistaken-for-the-thing]] 的形状：**这个数达标了，那件事就一定成立吗？**

**⇒ 请你裁定两件**：① 这该判**阻断**还是**不阻断**？② 修法选哪个 ——
**(a)** 让汇总**跨 worker 汇总**（xdist hook 回传）· **(b)** 把验收 #2 的证据**改钉在 failed 测试那条腿上**、
并把那行汇总**降级为 readout 且明写「并行下只反映本进程」**？

## 五、⭐ 还请重点攻这两处（⛔ 写成假说，未代判）

1. **替身会不会是空的** —— 任务书验收 #4：**每条被改的测试仍然测到它原本测的东西**。
   `test_zone_agent.py` 改了 **+132/−23**：请验**替身版是否仍在测 zone_agent 的解析与装配**，
   还是退化成「测了我自己造的那个 stub」。
2. **门装在 `pytest_configure`、卸在 `pytest_unconfigure`** —— 那么**在 conftest 被导入之前**
   （插件/更早的 conftest 导入期）建立的连接，或**已经绑定了 `socket.socket.connect` 引用**的库，
   会不会绕过？请构造一个实测。

## 六、返工审第三条判据

⛔ 只验「它自己那几条锁绿」不够：**换一个同形但不同的输入，缺陷仍走不通** ——
请自己造一条**新的、会真发连接**的测试（形状与它的三条牙锁不同，例如经 `httpx`/`urllib`/异步路径），
验门**仍然拦住并指名**。

## 七、交件

`AI_agent/logs/reviews/verdict/2026-09-03c_f158_crossreview_glm.md`：裁决 + 阻断/不阻断数，
逐条对 §二 / §四 / §五 / §六 报，贴命令原文 + 输出原文。⛔ 不许 `pip install -e .`；⛔ 不许 `git add -A`。
