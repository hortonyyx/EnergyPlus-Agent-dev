# 复审裁决书 —— 引号状态机 / 禁词表收窄 / 旧锁计数（补审三项）

- **审方**：GLM（复审席，换人审；作者是 orchestrator 本人）
- **请求书**：`AI_agent/logs/reviews/request/2026-08-16_e1_residual_three_items_review_sol.md`
- **被审对象**：`src/agent/execution/isolation_templates/guard.py`（HEAD = `e0367e1`，guard.py 最后改动在 `f6f2c46`，已核实）+ `tests/test_isolation.py`
- **性质**：⛔ 只审不改。零生产码改动、零 commit、全部试验在 `/tmp`。
- **总裁决**：**CHANGES REQUIRED（2 BLOCKER / 1 MINOR / 1 NIT）**。三项全部实审完毕，未触发停单。

---

## 0. 前提核对（停下上报分层）

- HEAD = `e0367e1` ✓；guard.py 自 `f6f2c46` 未动 ✓（「审 HEAD 即可」成立）。
- §2.1 代码在位（`_quote_states` guard.py:1005 / `_check_shell_structure` guard.py:1035）✓
- §2.2 代码在位（`EXEC_DENY_PATH_TOKENS` guard.py:259 / `ROOT_LITERALS` :341 / `EXEC_DENY_IMPLICIT_PATHS` :335）✓
- §2.3 范围核实：`dc4ca57..f6f2c46` 中动 `tests/test_isolation.py` 的**只有 `f6f2c46` 一个 commit**，请求书给的入手命令覆盖面正确 ✓
- **NIT-1（外围论据错，记录不停单）**：请求书 §1 称「`e0367e1` 只动了 `run_cv_probe.py` 与测试」——实际该 commit 还动了
  `src/agent/execution/isolation.py`（10 行）、`src/agent/reading/cv_toolbox/sidecar.py`（12 行）、
  两个 skills 文档（`guide.md`/`session_kickoff.md`）。guard.py 确实未动，故不影响审 HEAD 的结论，
  但「只动了」这句应更正。

**三项承重前提全部成立，正常审完。**

---

## 1. §2.1 引号状态机 `_quote_states` / `_check_shell_structure`

### 结论

**三态机本身（bare / `'` / `"` + 反斜杠转义）没有找到判错反例**：12 组构造样本对拍真实 bash，
所有引号内 / 转义形态（`"a;b"`、`'a;b'`、`a\;b`、`"a\;b"`、双引号内 `` ` ``、双引号内 `$`、单引号内两者、
`$'` ANSI-C、`#` 注释）的「操作符是否活着」判定与 bash 一致，`$` 与 `` ` `` 在双引号内也正确拒绝
（bash 在双引号内确实展开它们，拒绝方向正确）。

**但整体结构性检查有一个危险方向的洞**：

### BLOCKER-1：换行（`\n` / `\r`）不在元字符集里 —— 「第二条命令」整体绕过 exec 扫描

`_check_shell_structure` 只拦 `;|&<>` + `` ` `` + `$`。**换行在 bash 里与 `;` 同为命令分隔符**，
而它既不在检查集里、也不在引号里——`shlex.split` 把它当普通空白。后果：

- guard 视角：`ls -la\npython -c '<code>'` 经 `shlex.split` 得 `['ls','-la','python','-c','<code>']`，
  `parts[0]='ls'` ∈ `READ_ONLY_COMMANDS` ⇒ 走**只读命令分支**，`-c` 因以 `-` 开头被跳过、
  `<code>` 被当作一个「路径参数」只过 `_path_arg`。**`_scan_executed_code` 根本不被调用**
  ——`EXEC_DENY_NETWORK` / `EXEC_DENY_INDIRECTION` / `EXEC_DENY_DYNAMIC` / `EXEC_DENY_IMPLICIT_PATHS` /
  `ROOT_LITERALS` / 全部禁词，一个都不查。
- 真实 bash：换行分隔，第二行 `python -c` 照常执行。

**三组对照实测**（staging 搭于 `/tmp/e1rv/staging`，guard 为 HEAD 原件拷贝）：

| 命令 | guard | 理由 |
|---|---|---|
| `python -c 'import urllib.request as u; print(u.__name__)'` | **deny** | `python -c program references network egress (urllib)` |
| `ls -la; python -c '<同上>'` | **deny** | `compound shell token forbidden: ;` |
| `ls -la⏎python -c '<同上>'`（换行分隔） | **allow (rc=0)** | `allowed read-only command` |

真实 bash 执行第三条：`SECOND_COMMAND_RAN, urllib importable: urllib.request`——
**网络外传预备代码真的执行了**，而 guard 对它零扫描。2026-08-02 明令隔离必须防的「网络外传」，
在这里只剩 audit log 里的一条 allow 记录（F-44 能事后看见，但门没拦）。

复现（任一 staging）：

```bash
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"ls -la\npython -c '\''import urllib.request as u; print(u.__name__)'\''"}}' \
  | python3 guard.py ; echo "rc=$?"   # → rc=0（allow）
```

**分层与归因**（如实记账）：
- 这是 `_check_shell_structure` 的**元字符集缺陷**，不是 `_quote_states` 三态逻辑的缺陷（后者对拍全对）。
- 换行洞**早于 A3 存在**：旧版 substring 扫描的 `COMPOUND_TOKENS` 同样不含换行，且旧版
  `READ_ONLY_COMMANDS = {"ls","file"}` 分支同样只看 `parts[0]`。A3 不是它的引入者。
  但 A3 使它的 payload 空间从「藏一个裸命令」扩大到「藏一段完全免检的 python 代码」——危害面变了。
- 它**同时推翻请求书引述的作者自证**「guard 放行的每条……不一致处全在保守方向」：换行是
  **危险方向**的分歧（guard 放行、shell 执行结构）。
- `\r`（CR）同构绕过（已实测 `echo a\r rm -rf /` → guard allow、bash 第二条执行）。

**修法方向（登记，不施工）**：把换行/CR 纳入「bare 状态下的结构分隔符」拒绝集即可（quoted 内的多行
字符串本就合法，三态机已能区分）。注意配套锁：现有 `_READER_COMPUTATION_ALLOWED` 的正向样本
全是单行，补一条「合法多行 `-c`（换行在引号内）仍 allow」的负向对照，防止修法把引号内换行一并误杀。

---

## 2. §2.2 `EXEC_DENY_PATH_TOKENS` 收窄是否过头

### 结论：作者那句主张**在当前代码上为假**，且可端到端证伪——但打穿它的不是那三个词。

> 待证伪主张原文：「这三个词单独无法够到任何东西，因为通往它们的真实路径都要先经过仓库根或 `..`，两者仍拒。」

### BLOCKER-2：`cwd` / `__file__` 锚点 + `parents` 链 —— 取出路径的第二个入口，F-47 枚举漏掉的一族

`EXEC_DENY_IMPLICIT_PATHS`（guard.py:335）枚举的是 `os.sep / .home() / expanduser / os.environ /
getenv / sys.prefix / site.getsite`，**不含 `Path.cwd` / `os.getcwd` / `__file__` / `.parent(s) /
expandvars`**。而 staging 在真实部署里是 `/tmp/ep_isolation/<case>/`（`isolation.py:188`，
`_require_outside_repo` 强制在仓库外），cwd 的 parents 链 2–4 层就是 `/`：
`Path('/tmp/ep_isolation/x').parents[2] == '/'`（已实测）。

反例脚本（guard 判 **allow**，rc=0；`out/prog.py`）：

```python
import os
from pathlib import Path
base = Path.cwd().parents[2] / 'workspaces'
hits = []
for r, d, f in os.walk(base):
    for n in f:
        if n.startswith('gt') and n.endswith('.json'):
            hits.append(os.path.join(r, n))
print(hits[:3])
```

真实执行输出（**只打印路径、未读内容**）：

```
['/workspaces/glm_exam/case_tests/test_baseline/gt/sm21_anchor/gt.json',
 '/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/sm21_anchor/gt.json',
 '/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/sm24_anchor/gt.json']
```

——**答案面的确切位置已经到手**；下一步 `open(hits[0]).read()` 不需要任何新的许可，guard 看不见。
代码文本不含：`..`、`~`、`case_tests`、`test_baseline`、`gt.json`（比较用 startswith/endswith 运行时拼接，
即便写 `n == 'gt' + '.json'` 同样不构成字面 token）、无网络/间接/动态词、无 `'/'` 字面量、无
`os.sep`/`.home()`/`os.environ`。`_scan_executed_code` 六道检查全绿。

对照实测（证明 F-47 的锁确实在、且本反例走的是它们够不着的地方）：

| 载体 | guard |
|---|---|
| `os.walk('/')`（字面量） | **deny** —— `names the filesystem root ('/')` |
| `os.walk(os.sep)` | **deny** —— 同上 |
| `Path.cwd().parents[2]` + `os.walk`（锚点） | **allow** |
| `Path(__file__).parents[3]` + `iterdir`（锚点，脚本形态） | **allow**，真实执行已爬出 staging 列出上级目录 |

同族未拦变体（供修法枚举时一并考虑）：`os.getcwd()`、`os.path.dirname` 链、`os.path.expandvars('$PWD')`、
`sys.argv`、`Path().resolve()`。`tests/test_isolation.py` 对整族**零锁**（grep `parents|cwd|getcwd|__file__`
只命中测试自身的 `cwd=staging` 调用参数）。

**对主张的准确拆账**（这条最重要，请勿修错方向）：

1. 主张的**结论为假**：「通往它们的真实路径都要先经过仓库根或 `..`」不成立——`parents` 链既不写
   仓库根也不写 `..`。
2. 但**账不记在三个被剔除的词上**：本反例代码里根本没有 `attempts`/`verdict`/`grade`；把三个词加回
   `EXEC_DENY_PATH_TOKENS`，反例原样成立。它打穿的是 F-47 想堵的同一件事（「路径不是写出来的、是
   取出来的」）的**剩余面**——锚点族（cwd / `__file__` / parent 链）不在 `EXEC_DENY_IMPLICIT_PATHS`
   的枚举里。
3. 因此修法方向 = 补锚点拦截（`cwd`/`getcwd`/`__file__`/`.parent`/`expandvars` 等进 implicit 列表，
   或改为允许列出「相对路径锚点白名单」），而**不是**回填三个词。回填只会重新制造
   `# grade line at 0.000` 那个误杀问题，且对本反例无效。
4. 严重性与 sol 上轮的 `os.walk('/')`（判 BLOCKER、修为 F-47）**同族同级**：普通、非混淆的 Python 写法，
   落在声明的威胁模型（「防走捷径」）之内。

---

## 3. §2.3 「被我推翻的旧锁共 4 处」计数

### 结论：计数正确，无第五处；4 处改法全部成立。另有一条放宽未配锁（MINOR）。

机械核对：提取 `git diff dc4ca57 f6f2c46 -- tests/test_isolation.py` 的**全部删除行**（共 8 条实质删除
+ 3 行 docstring 改写），逐条归位——

| 删除行 | 归属 |
|---|---|
| `"python -c 'print(1)'"`（rejects_forbidden_bash_shapes 参数表） | 处 3 ✓ |
| `("python_c", …)`（security_properties_stay_denied 参数表） | 处 1 ✓ |
| docstring "six of the eight…" | 处 1 连带 ✓ |
| tee 文案 / mkdir 文案 / find 条目（safe_next_step） | 处 4 ✓ |
| `("python_dash_c", …)` / `("not_allowlisted_command", "cat …")`（boundary shapes） | 处 2 ✓ |

**无第五处删除/改写。** 4 处改法逐项验证：

1. **处 1（python_c 除名）成立**：`python -c` 有替代信息边界锁
   `test_guard_information_boundary_survives_a3_removal[dash_c_reads_answers]`（`-c` 读 gt → deny）。
   「跑程序本身不是信息边界属性」的归类与 08-02 拍板一致。
2. **处 2（boundary shapes 重排）成立**：四个新增形状在 HEAD 上逐条实测全部真实 deny
   （`script_outside_writable_dirs` / `nonexistent_script` / `module_form_pip` / `module_form_server`
   均得 rc=2 且理由对应）；`cat` 移除有正向锁 `read_own_file` 承接。
3. **处 3（移出 python -c）**：同处 1。
4. **处 4（文案）成立**：两条新文案与 guard 实际输出**逐字一致**——
   `compound shell token forbidden: |; express the pipeline in the Python program instead` /
   `command is not allowlisted: mkdir; run it from Python instead (…)`。

### MINOR-1：三个命令的 allowlist 放宽**静默**（F-43 同族），`find` 尤其刺眼

那一批把 `READ_ONLY_COMMANDS` 从 `{"ls","file"}` 扩到 `{"ls","file","cat","head","tail","wc","find"}`
（放宽 5 个命令）。cat/head 配了新正向锁（`_READER_COMPUTATION_ALLOWED` 的 `read_own_file`/`head_own_file`）；
**`tail` / `wc` / `find` 三个命令的 allow 行为零正向锁**。`find` 正是处 4 被删的那条旧文案锁的对象：
删除本身登记在案，但「find 现在 allowlist、其参数仍过 `_path_arg`」这个新行为没有任何测试钉住——
实测今天 `find ../..` 被拒（`parent traversal token is forbidden`），但若 READ_ONLY 分支的路径检查回归，
无测试变红。这不是「第五处被推翻的锁」（没有旧断言被删——旧测试里本就没有 tail/wc/find 的 deny 断言），
是放宽未配锁，登记与 F-43（「授权表收窄静默、放宽同样静默」）同族。

---

## 4. 与 F-55（`python -c` 写面敞开，已登记不修）的交互

- **与 BLOCKER-2（锚点绕过）：独立、可叠加，互不为前提。** F-55 是写面（改 guard.py / 清 access_log），
  BLOCKER-2 是读面（信息边界，本题本职）。只修 F-55，BLOCKER-2 原样成立；只堵锚点，F-55 原样成立。
  组合形态（先读 gt、再清 log 毁审计）会更糟，但单独任一已足够致命。
- **与 BLOCKER-1（换行）：直接叠加。** 换行洞让第二行 python -c 免检，而 F-55 恰好证明这种免检 python -c
  的写破坏真的能落地——`ls\npython -c '<改写 guard.py / 清空 access_log>'` 一条命令同时绕开扫描与
  审计。同样互不依赖：修掉换行洞后 F-55 仍在（`python -c` 直跑也行）；修掉 F-55 后换行洞仍是
  exec 扫描的整体旁路。
- **对 §2.2 那句主张的影响（用户点名的问法）**：「词表收窄安不安全」在写面敞开的前提下**更不成立，
  但账要分开记**。F-55 意味着一切「guard 仍拒 X」的推理连前提都没有（guard 本体可被改写后再放行），
  所以「两者仍拒」在 F-55 在场时是双重失效。但即便 F-55 明天修好，BLOCKER-2 独立成立 ⇒
  **词表收窄的安危结论不因 F-55 改变**（本来就不安全，理由是锚点族）；F-55 只是让整道门的信任根
  进一步松动。修法排序上 F-55 不应挡在这两条 BLOCKER 前面，也不被它们挡。
- 与 §2.3：无交互（测试计数与写面无关）。

---

## 5. 汇总表

| # | 级别 | 条目 | 一句话 |
|---|---|---|---|
| BLOCKER-1 | 🔴 | `_check_shell_structure` 元字符集漏换行/CR | `ls⏎python -c '<code>'` → allow，第二行**完全免检执行**（EXEC_DENY_* 全旁路）；三态机本身无判错 |
| BLOCKER-2 | 🔴 | `EXEC_DENY_IMPLICIT_PATHS` 漏 cwd/`__file__`/parent 锚点族 | `Path.cwd().parents[2]`+`os.walk` → allow，已实测定位本仓 gt.json 真实路径；**与三个被剔除词无关，修法是补锚点不是回填词表** |
| MINOR-1 | 🟡 | `tail`/`wc`/`find` 放宽无正向锁 | F-43 同族（放宽静默）；`find` 的旧文案锁已删、新行为零锁 |
| NIT-1 | ⚪ | 请求书 §1 外围描述不准 | `e0367e1` 还动了 `isolation.py`/`sidecar.py`/2 个 skills 文档，非「只动了 run_cv_probe.py 与测试」；不影响审 HEAD 结论 |

**派工方主张证伪兑现（请求书 §0 邀请项）**：本轮证伪两条——
①「不一致处全在保守方向」（换行是危险方向分歧）；②「三个词单独无法够到任何东西…两者仍拒」
（parents 链不经过仓库根文本也不经过 `..`）。另更正一处外围描述（NIT-1）。

**三项是否有一项已不成立**：无。三项均与 HEAD 代码相符。

## 6. 试验环境

- staging：`/tmp/e1rv/staging`（guard.py = HEAD 原件逐字节拷贝；含 `out/ requests/ tools/ case_data/`）；
  真实部署布局验证：`/tmp/ep_isolation/_e1rv_check`（`Path.cwd().parents[2] == '/'` 实测）。
- 所有「够到答案」的验证只打印路径、未读取任何 gt 内容；网络验证仅 `import`，未发起任何请求。
- 本裁决书为唯一交付物；仓库零改动（`git status` 未新增除本文件与请求书外的任何跟踪内改动）。
