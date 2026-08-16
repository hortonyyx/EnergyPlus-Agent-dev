# 复审请求 —— 撤除 reading 沙箱的「能力封口」（A3）+ F-44 日志修复

**施工方**：orchestrator（Opus 5，本人）。**⇒ 按「谁写谁不批」，本请求交 sol 执行审（升一档交叉）。**
**基线**：`dc4ca57`。**改动文件**：`src/agent/execution/isolation_templates/guard.py` ·
`tests/test_isolation.py` · `skills/intake_pipeline/0_reading/cv_toolbox.md`（+ 实验产物与文档）。

---

## 0. ⭐ 请先读这一节：「停下上报」分层（⛔ 不许写无差别的「发现前提错就停」）

- **① 承重前提错 ⇒ 停下上报**：即「若这条错了，整个改动的范围/方向就不该是这样」。
- **② 外围论据错 ⇒ 报告后继续实审**，不要停单。
  （前几轮 sol 连着两次停在请求书的外围论据错上 ⇒ 主体零审阅。）

**⛔ 派工方错误率 19/19**（本仓历史统计，同一形状 = **把「我以为的盘面」当「盘上的事实」说出口**）。
⇒ **请主动证伪本文任何一句陈述**，尤其带「全部 / 一律 / 共 N 处」的句子。

---

## 1. 背景（为什么撤这道门）

CLAUDE.md §1.5 #7（用户 **2026-08-02** 拍板）：

> 严格限制**可见信息与写出边界**，**不限制在合法输入上采用何种计算方法**。……
> 按命令形态封杀通用 CV 编程（`python -c`、临时脚本）属于**能力封口**，
> **它封掉的正是 07-02 Sonnet 那条成功路径**。

**该裁定两周未落地**：直到本轮，`guard.py` 仍然 `python -c` → DENY、任何自写脚本 → DENY。
本轮把它落地，同时作为 reading 杠杆排查的**单变量实验 E1**（一抽已跑完，见 §5）。

**用户 2026-08-16 当面拍板的档位**（三选一里选了 A）：
**放开计算，但门在执行前把要跑的代码内容按同一张词表扫一遍。**

---

## 2. 改动做了什么（请按这五条逐条核）

| # | 改动 | 位置 |
|---|---|---|
| 1 | `python -c '<code>'` DENY → **ALLOW**；`python <自写脚本>` DENY → **ALLOW** | `_check_python_execution` |
| 2 | 可执行脚本面 = **`WRITE_ALLOWED_DIRS` 本身**（`out/`、`requests/`）+ `tools/run_cv_probe.py`。⭐ **刻意排除 `tools/cv_probe.py`** | 同上 |
| 3 | **执行前代码扫描**：入口脚本 + `out//requests/` 下**全部** `.py`（import 面）逐份读出来扫；`-c` 的程序文本同理 | `_scan_executed_code` / `_scan_reader_authored_code` |
| 4 | 复合符号检查从**整串子串扫描** → **带引号状态的逐字符扫描** | `_check_shell_structure` |
| 5 | **F-44**：access_log 的 `tool_input_excerpt` 从 **deny-only** 改为 **allow 也记**（上限 500→8000）+ 新增 `executed_code` = 每份被扫文件的 `{path, sha256}` | `_append_log` |

**#4 为什么必须做**：原检查对整条命令串做子串匹配，而 `>`、`<`、`;`、`|` 是**普通 Python 运算符**
⇒ 不改的话 `python -c 'print(a > b)'` 会被拒，**等于从侧门把刚撤掉的封口装回去**。

**仍然拒绝（本轮刻意不动）**：管道 / 重定向 / `;` 等 shell 复合结构 · `cd`/`env` ·
`..` / `~` / 仓库绝对路径 · `$` 与反引号（单引号外）· `python -m` · Read 仓库文件 ·
网络外传 token · 子进程 token。

---

## 3. ⭐⭐ 请重点攻击的四处（我自己最不放心的）

### 3.1 执行前代码扫描能不能被绕过

我的主张：**「命令干净、文件里写着答案路径」这条口子不存在**，因为扫的是**要跑的字节**，
而且扫的是**整个 import 面**（`out//requests/` 下全部 `.py`），不只入口脚本。
**⛔ 我明确承认扫不住的**：编码/拼接混淆（`chr(47)+...`、base64）——按 2026-08-13 用户收窄的威胁模型
（防「产物自称经过确定性核」，不防蓄意越狱）判为范围外。
**请攻击的是「非混淆的、正常写法能不能溜过去」**，例如：
`os.environ`、`pathlib.Path.home()`、`glob`/`os.walk` 从 staging 往上走、
`sys.argv`、`site.getsitepackages()`、`__file__` 相对拼接、符号链接创建（`os.symlink`）……
**⇒ 我没有穷举过这一类，这是我最想要外部意见的一处。**

### 3.2 `_check_shell_structure` 的引号状态机是否正确

`_quote_states` 是我手写的三态机（bare / `'` / `"`）+ 反斜杠转义。
**请找反例**：能让 shell 实际执行到某个操作符、而这个状态机认为它在引号里的写法。
（这是本轮我唯一新增的**解析**逻辑，也是我在设计时明确说过「解析歧义是本仓吃过亏的形状」的地方。）

### 3.3 `EXEC_DENY_PATH_TOKENS` 收窄是否过头

执行代码扫描用的**不是**完整 `DENY_TOKENS`，我剔掉了 `attempts` / `verdict` / `grade`。
理由：三者都是本项目自己的日常词（`grade line` = 室外地坪线），且仓里已有锁
`test_guard_allows_reading_summary_with_prose_forbidden_tokens` 判定它们在读图器散文里合法；
若拿它们扫代码，一句 `# grade line at 0.000` 就会让**整场会话**的 python 全部失效。
**⛔ 请证伪我这句**：「这三个词单独无法够到任何东西，因为通往它们的真实路径都要先经过仓库根或 `..`，两者仍拒。」

### 3.4 `/` 豁免

`_lexical_check` 里我加了一处豁免：**纯由斜杠构成的 token 不当作绝对路径**
（否则 `px / m` 里的 `/` 会被判成「逃出 staging 的绝对路径」，普通除法就用不了）。
**请核**：这个豁免有没有放过任何真实路径。我的主张是「`/etc/passwd` 含非斜杠字符，仍被同一行拒」。

---

## 4. 已做的验证（⛔ 请核实这些验证本身是否成立，不要只信结论）

- **20 条行为探针**（真建 staging、真驱动 hook，⛔ 非形状匹配）：
  正向 7 · 边界 8 · held 3 · **阴性对照 2**（wrapper 仍可用 · 移除脏文件后**同一条命令**放行）。
- **沙箱内真跑通**：`python out/measure.py` 用 numpy+PIL+scipy 读图 rc=0。
- **定向子集**：`tests/test_isolation.py` + `tests/test_cv_toolbox.py` = **255 全绿**。
- **权威全量**：**2662 passed / 10 xfailed / 1 failed**，唯一那条红 = `test_b2_prescan_reproduction`
  （F-36 旧债，`dc7b239` 带进，与本改动无关；该文件对 guard/isolation 零引用）。
  基线 2635 ⇒ **+27 把锁、零回归**。
- **被我推翻的旧锁共 4 处**（请核实我改得对、且没顺手放宽别的）：
  ① `test_guard_security_properties_stay_denied[python_c]` —— **把 `python -c` 从「安全属性」除名**
  （我的论证：它从来不是信息边界属性，是被归在安全标题下的能力封口）；
  ② `_DIRECT_BASH_BOUNDARY_SHAPES` 去掉 `python_dash_c` 与 `cat`，新增
  `script_outside_writable_dirs` / `nonexistent_script` / `module_form_pip` / `module_form_server`；
  ③ `test_guard_rejects_forbidden_bash_shapes` 移出 `python -c`；
  ④ `test_guard_real_shell_denials_include_an_isolation_safe_next_step` 改两条文案、**删掉 `find` 那条**
  （`find` 现在允许）。

**⚠️ 一处我自己发现并已改的口子（供你判断我漏没漏同类）**：
第一版我把 `python -m` 也放行了 ⇒ `python -m pip install …` 可联网+改环境、`python -m http.server` 可开端口，
而模块名是**已安装模块**、代码根本不经过扫描。现已整体拒绝 `-m`。

---

## 5. 实验结果（⛔ 这部分不是请你审的对象，但影响你对「是否达成目的」的判断）

E1 一抽跑完（`run_2026-08-16_reading_restart_E1_uncapped`）：
读图器**真的用了**新能力 **4 次**（自写脚本 ×1 + `python -c` ×3），**但零次用于测量** ——
三次 `-c` 全是 `json.load` 自己刚写的输出文件打印「valid」；那个叫 `measure_1f.py` 的脚本
**坐标全硬编码**、内墙注着 `estimated from visual inspection`。工作模式没变（仍 1/6 图），墙 0/9。

⇒ 变量纯度 ✅（prescan 零出现）· 信息边界 ✅（3 条 deny 无一条够答案，66 条 allow 的
`executed_code` 逐条核过）。

---

## 6. 请回什么

按 **BLOCKER / MAJOR / MINOR / NIT** 分级。特别希望看到：

1. §3.1 那一类「非混淆的正常写法」的**具体反例**（能跑通的最好）；
2. §3.2 引号状态机的**具体反例**；
3. 我在 §3.3 / §3.4 的两句主张，**哪一句你能证伪**；
4. 有没有**我推翻旧锁时顺手放宽的第五处**（我只找到四处，这类「我以为共 N 处」正是本仓错 19/19 的形状）。
