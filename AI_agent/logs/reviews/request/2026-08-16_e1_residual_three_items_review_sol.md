# 复审请求（补审·三项）—— reading 隔离沙箱守门件：引号状态机 / 禁词表收窄 / 旧锁计数

**收件**：GPT 家族（sol）
**性质**：**我方自有代码的防御性复审**。被审对象是本项目自己写的测试隔离壳（净室），
它的作用是**防止被评测的读图模型读到评测答案**（gt / baseline / 历史 run）。
这是评测卫生（防作弊）设施，不是对外部系统的攻击工具。请以「找我们自己这道门的漏洞」的角度审。

**为什么是补审**：上一轮（2026-08-16 上半场）的请求书
[`2026-08-16_a3_capability_uncap_request.md`](2026-08-16_a3_capability_uncap_request.md)
共提了四个攻击面。其中：

- **§3.1（执行前代码扫描能否绕过）✅ 已审** —— sol 抓到 BLOCKER 并端到端复现，已修（F-46）；
- **§3.4（`/` 豁免）✅ 已自查证伪并修** —— 我自己写的「纯斜杠豁免没放过任何真实路径」**是假的**
  （`os.walk('/')` 零禁词遍历整个文件系统、guard 放行），已修（F-47）；
- **§3.2 / §3.3 / §4 的「共 4 处」计数 ⛔ 三项未经换人审** —— sol 按「停下上报」规矩在承重前提处中断，
  GPT 通道随后被 provider 安全过滤连拦 4 次、GLM 侧补审跑满 50 分钟零输出（F-48）。

⇒ **本单只审这三项。** 按「谁写谁不批」，作者（orchestrator）自己对拍过真实 bash，
**但那是作者自证，不能替代换人审。**

---

## 0. 「停下上报」分层（⛔ 不许无差别地「发现前提错就停」）

- **① 承重前提错 ⇒ 停下上报**：本单赖以成立的东西不成立（例如三项里有两项其实已经不在代码里了）⇒ 停。
- **② 外围论据错 ⇒ 报告后继续审完**：我下面写的任何一句具体判断错了，**记下来照常审完三项**。

**⛔ 派工方错误率 24/24**（上一轮兑现两次：sol 打掉 §3.1，我自己打掉 §3.4）。
本单里凡「我的主张是……」都请当作**待证伪对象**。

---

## 1. 被审对象

- 文件：`src/agent/execution/isolation_templates/guard.py`（HEAD = `e0367e1`；
  该文件最后一次改动在 `f6f2c46`，`e0367e1` 只动了 `run_cv_probe.py` 与测试 ⇒ **审 HEAD 即可**）
- 相关测试：`tests/test_isolation.py`
- 背景：这道门是 hook，读图器的每一条 Bash / Write 都先过 `evaluate()`，
  返回 `allow` 才真的执行。它要防的是**读图器把评测答案带出净室**，
  以及**读图器执行会外泄信息的代码**（联网、起子进程、读 staging 之外的路径）。

---

## 2. 请审的三项

### 2.1 引号状态机 `_quote_states` / `_check_shell_structure`

`_quote_states` 是我手写的三态机（bare / `'` / `"`）+ 反斜杠转义，
`_check_shell_structure` 用它判断命令里的 shell 元字符（`;` `|` `&&` `||` `` ` `` `$(` `>` `<`）
是不是落在引号内——落在引号内才允许（读图器要能写 `python -c '... if a > b ...'`）。

**请找反例**：**能让真实 shell 执行到某个操作符、而这个状态机认为它在引号里**的写法。
（这是那一批唯一新增的**解析**逻辑；「解析歧义」是本仓反复吃过亏的形状。）

⚠️ 作者自证（**不可替代换人审**）：我拿 15 条样本对拍过真实 bash，
guard 放行的每条 `shlex.split` 与 bash argv 一致，不一致处全在保守方向。

### 2.2 `EXEC_DENY_PATH_TOKENS` 收窄是否过头

扫描**将被执行的代码**时用的**不是**完整 `DENY_TOKENS`：我剔掉了 `attempts` / `verdict` / `grade` 三个词。

理由：三者都是本项目的日常词（`grade line` = 室外地坪线），
仓里已有锁 `test_guard_allows_reading_summary_with_prose_forbidden_tokens` 认定它们在读图器散文里合法；
若拿它们扫代码，一句 `# grade line at 0.000` 就会让**整场会话**的 python 全部失效。

**⛔ 请证伪我这句主张**：
> 「这三个词单独无法够到任何东西，因为通往它们的真实路径都要先经过仓库根或 `..`，两者仍拒。」

⚠️ 请注意这句话的语境已经变了：上一轮之后新增了 `ROOT_LITERALS` 与 `EXEC_DENY_IMPLICIT_PATHS`
（F-47 的修法，防「路径不是写出来的、是取出来的」）。**请在当前代码上重判这句，别只看当时的论证。**

### 2.3 「被我推翻的旧锁共 4 处」这个计数

我在上一轮声明**只推翻了 4 处旧锁**：

1. `test_guard_security_properties_stay_denied[python_c]` —— 把 `python -c` 从「安全属性」除名；
2. `_DIRECT_BASH_BOUNDARY_SHAPES` 去掉 `python_dash_c` 与 `cat`，新增
   `script_outside_writable_dirs` / `nonexistent_script` / `module_form_pip` / `module_form_server`；
3. `test_guard_rejects_forbidden_bash_shapes` 移出 `python -c`；
4. `test_guard_real_shell_denials_include_an_isolation_safe_next_step` 改两条文案、删掉 `find` 那条。

**请核**：① 这 4 处我改得对不对；② **有没有第五处**——我在放开能力时顺手放宽、
但没登记的旧锁或旧断言。（「我以为共 N 处」正是本仓错 24/24 的固定形状，
所以这一项**不是形式主义**，请当真找。）

建议入手：`git diff dc4ca57 f6f2c46 -- tests/test_isolation.py`（那一批的测试改动全在这个范围里）。

---

## 3. 回什么

按 **BLOCKER / MAJOR / MINOR / NIT** 分级，每条给**可复现命令或具体反例**（能跑通的最好）。
特别希望看到：

1. §2.1 引号状态机的**具体反例**；
2. §2.2 那句主张，你能不能证伪（在**当前**代码上）；
3. §2.3 的**第五处**（若有）；
4. 以及：这三项里有没有哪一项其实**已经不成立了**（代码后来变过、我的描述过时）。

⛔ 本单**只审不改**：不要提交修法。发现的问题登记为 finding，修法由主控排下一轮。
