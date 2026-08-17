# 基座修法批·摊 II 执行日志 —— 工具面参数语义 + 错误可操作性 + 文档（F-52 / F-54 / F-58 / F-53）

- 日期：2026-08-16（跨 2026-08-17 收尾）
- 分支：`6.15_ValidationArchM0toM4`
- 派工单：`AI_agent/logs/reviews/request/2026-08-16_substrate_fix_dispatch_II_tools.md`
- 施工席位：执行档（Claude Sonnet 5 子代理）
- 并行摊：摊 I（净室写面 + 守门件，F-55/F-56/F-57）同时进行，文件集合与本摊不相交；
  本摊全程未碰 `src/agent/execution/isolation.py` / `guard.py` /
  `tests/test_substrate_fix_cleanroom.py` / `tests/test_substrate_sweep_policy.py`
  （`git diff --stat` 对这四个文件为空，逐次核实见 §7）。

---

## 0. 背景与四条缺陷回顾

全表：`AI_agent/logs/experiments/2026-08-16_substrate_sweep/README.md` ·
分表：`AI_agent/logs/experiments/2026-08-16_substrate_sweep/grid_A.md`。

四条共同形状（派工单的归纳，本单核实成立，见 §6）：**读图器按文档/自然写法去用工具，
工具用一种它无法据以自救的方式失败。**

---

## 1. 四条修法与理由

### F-52 —— `bbox` 原生 JSON 数组崩溃

**改动文件**：`scripts/tool_scripts/cv_probe.py::_bbox()`。

**方向选择（派工单要求由本席判断并给理由）**：只修 `_bbox()` 这一个点，**不**把 `bbox` 加进
`run_cv_probe.py` 的 `JSON_OR_PATH_KEYS`。理由：

1. **加进 `JSON_OR_PATH_KEYS` 对「原生数组」这一半没有任何新增效果**——该分支对 `list` 值的处理
   就是 `json.dumps(value, ...)`，与 bbox 当前落入的通用分支（`elif isinstance(value,(dict,list))`）
   对 list 值做的事**完全相同**。两条分支殊途同归到同一个 `"[x0,y0,x1,y1]"` 字符串，问题从未在
   wrapper 侧，一直在 `_bbox()` 不会解析这个字符串。
2. **加进 `JSON_OR_PATH_KEYS` 会引入一个新的真实回归**：该分支对「不以 `[`/`{` 开头的字符串」会
   当路径解析（`_resolve(value, root)`）。bbox 现在唯一能工作的写法是纯逗号字符串
   `"880,730,1000,790"`——这恰好**不**以 `[`/`{` 开头，会被误当路径解析成
   `<staging_root>/880,730,1000,790`，再喂给 `_bbox()` 直接崩。也就是说这个"顺手也做"的方向会
   **炸掉当前唯一在工作的写法**，是负收益，不是"多做一点更保险"。
3. **`_bbox()` 是全部三种形态（B 直接 CLI / A `--request` / C `--batch`）最终唯一收敛的入口**：
   B 形态如果读图器手打 `--bbox '[100,80,700,460]'`（模仿 `--anchors-json` 的写法，是很自然的类推），
   这个值在 `_direct_to_request`→`_request_to_argv` 全程都是字符串、不落入任何特殊分支，直接原样
   传给 `cv_probe.py` 的 argparse，只有 `_bbox()` 自己能救。只修这一点，B/A/C 三态与"原生数组"/
   "JSON 数组字符串"两种写法全部同时被覆盖，是单点修法里覆盖面最大的选择。

**修法内容**：`_bbox()` 判断值去空白后是否以 `[` 开头，是则走 `json.loads` 解析成列表再转 float；
否则走原有的逗号切分。JSON 解析失败或元素个数不为 4 都给出 `argparse.ArgumentTypeError`（保持退出码 2
+ 干净文案，不引入新的失败形态）。

### F-54 —— `run_cv_probe.py::main()` 零异常兜底

**改动文件**：`src/agent/execution/isolation_templates/run_cv_probe.py::main()`。

**修法内容**：把 `--help` 早退之后的全部函数体包进 `try: ... except (ValueError, OSError) as exc:`，
捕获后打印 `run_cv_probe.py: error: {exc}`（消息原文保留，不改写、不截断）到 stderr，返回 2。
`json.JSONDecodeError` 是 `ValueError` 子类，不需要单列。argparse 自己的 `parser.error()` 路径走
`SystemExit`（不是 `Exception` 子类），完全不受这个 `try/except` 影响，行为逐字节不变
（已实测验证，见 §2）。

**为什么用「整个 main() 函数体」这样宽的包裹范围，而不是只包住派工单点名的
`_direct_to_request`/`_request_to_argv`/文件读取**：派工单原话是"main() 的异常兜底"，是一个安全网
定位，不是要求逐行精确圈出哪几个调用。这个范围选择还带来一个正向副作用：F-58 修好后
`overlay_logger` 从深处抛出的 `ValueError`，同样会被这个安全网接住变成干净退出（见下方"两条修法的
协同"）。範囲没有扩大到会掩盖真实程序 bug 的地步——只多捕获 `ValueError`/`OSError` 这两类"调用方
输入有问题"的异常，`AttributeError`/`TypeError`/`KeyError` 等代表代码本身有缺陷的异常类型完全不在
捕获范围内，不会被这次修法悄悄吞掉。

**两条修法的协同（意料之中，非巧合）**：F-58 修好后，`overlay_logger` 对错误形状的 `candidates_json`
抛的是 `ValueError`（此前是 `AttributeError`）。`AttributeError` 不在 F-54 的捕获类型里，所以**如果
只修 F-58 不修 F-54**，这个错误依然会以裸 traceback 冒出来（已用 neuter 实测验证，见 §2 F-58 neuter
部分）——F-54 单独修不能替 F-58 兜底，F-58 单独修也不能让消息不带 traceback，两条修法各自独立地
必要，谁都不是谁的一部分。

### F-58 —— `overlay_logger` 裸 `AttributeError`

**改动文件**：`src/agent/reading/cv_toolbox/tools.py::overlay_logger()`。

**修法内容**：函数入口先校验 `candidates` 是不是 `list`，不是则抛 `ValueError`，消息里带上收到的实际
类型名并附一个可直接抄的正确写法示例（`[{"candidate_id":"c1","status":"accepted",...}]`）。再在
`for candidate in candidates:` 循环内加一层 `isinstance(candidate, dict)` 检查，覆盖"外层是 list、
内层元素不是 dict"这另一种错误形状（比如 `["not_a_candidate_object"]`）。两处检查都放在
`_load_rgb(image)` 之前，形状不对时不做任何图像 I/O。

原有更深一层的检查（候选字典是 dict 但缺 geometry 时抛 `"...must carry drawable geometry..."`）
完全未动，新加的检查只处理"形状本身就不对"这一类，不影响"形状对但语义不完整"那一类既有校验
（已用既有单元测试 + 本单新锁双重验证不变，见 §2）。

### F-53 —— 文档尖括号占位符

**改动文件**：`skills/intake_pipeline/0_reading/cv_toolbox.md`。

**修法内容**：把第 53 行 `python tools/run_cv_probe.py --batch requests/<name>.json` 改成
`python tools/run_cv_probe.py --batch requests/sweep.json`，并在代码块前的说明文字里明确写出
"这是一个具体文件名、不是占位符；尖括号是 shell 重定向符，逐字复制会被解析成重定向而不是路径"。
`requests/sweep.json` 这个具体名字直接取自 `run_cv_probe.py::_USAGE_TEXT` 里已经在用的同一个例子
（`# requests/sweep.json: {...}` / `python tools/run_cv_probe.py --batch requests/sweep.json`），
让文档与 wrapper 自带的 `--help` 文本用词一致，不新造一套命名。

**顺手排查（派工单 §2 F-53 段末尾要求）**：把 `cv_toolbox.md` 全部 7 个 ` ```bash ` 代码块逐块过了
一遍，找去引号后仍残留 `<identifier>` 形状 token 的情况——**只有这一处**。其余 6 块要么是具体值
（`case_data/1f_view.png`、`--bbox 120,80,620,460` 等），要么尖括号出现在单引号 JSON 字符串内部
（`-c` 那个 python 单行脚本、`--anchors-json` 的内联 JSON），单引号内的字符不会被 shell 当元字符解析，
不构成同类风险。这个排查后来直接写成了本单交付的一把正锁
（`test_f53_negative_no_other_bash_block_has_an_unquoted_angle_bracket_placeholder`），
不是只做了一次性人工检查就算数。

**⛔ 只改了措辞，未改任何工具行为**——四个改动文件里，`cv_toolbox.md` 是纯文本改动，
没有触碰任何 `.py` 文件之外的逻辑。

---

## 2. 行为验证三向证据

方法论：全部经**真实 staging**（`build_isolation_workspace`）+ **真实 `subprocess`** 跑
`python tools/run_cv_probe.py ...`（staged wrapper），零处直接 `import` 工具函数来断言修法效果。
详细锁在 `tests/test_substrate_fix_tools.py`（新建，23 个测试用例）+
`tests/test_substrate_sweep_tools.py`（xfail 转正锁，见 §3）。以下摘录关键证据（完整命令与输出见
测试文件本体，均已跑通）。

### F-52

- **正向**：`--request`（A）与 `--batch`（C）两种形态，`bbox=[100,80,700,460]`（原生数组）现在
  `returncode==0`，`crop_size_px==[600,380]`（=700-100, 460-80，算术精确）。另加一格覆盖
  「B 形态手打 JSON 数组字符串 `--bbox '[100,80,700,460]'`」同样通过、同样数对——这格不在派工单
  点名的 A/C 范围内，是本席主动补的，验证"单点修法覆盖三态"这条判断本身。
- **反向**：既有的逗号字符串写法（B/A/C 三态）全部保持 `returncode==0` 且 `crop_size_px` 不变；
  真正畸形的 bbox（元素数不对、非数字）仍然 `returncode==2` + 干净 argparse 报错，不是被新逻辑
  意外放行。
- **neuter**：把 `scripts/tool_scripts/cv_probe.py` 换成 `backup/scripts_history/2026-08-16_substrate_fix_II/`
  下的未修版本，重建一份全新 staging（staging 在 build 时拷贝文件，必须晚于替换才能拿到坏版本），
  重放同一个正向用例 → `returncode==2`，stderr 含 `invalid _bbox value`（原始报错文案原样重现）。
  `finally` 块恢复文件字节，恢复后与恢复前 `read_bytes()` 相等（Python 级校验，不只是肉眼看
  `git diff`）。

### F-54

- **正向**：派工单原始复现命令 `--tool wall_line_profiler --`，`returncode` 从 1 变 2，stderr 不含
  `Traceback`，且含原始消息 `probe parameter name is empty`（一字不改）。另加三格覆盖派工单命令之外
  的失败家族：`--request` 指向不存在的文件（`OSError`）、`--bbox` 后漏值（`ValueError`）、
  `--tool` 传一个不存在的工具名（`ValueError`）——三格全部 `returncode==2`、无 traceback、原始消息
  保留。
- **反向**：一个写对的 `--request` 调用仍 `returncode==0`；argparse 自己的错误路径
  （`--request` 后面漏掉值这种 argparse 级别的语法错）逐字节不受影响——usage 文本、
  `expected one argument` 错误文案、退出码 2 全部照旧；`--help` 仍正常输出。
- **neuter**：把 `run_cv_probe.py` 换回未修版本，重建 staging，重放原始复现命令 →
  `returncode==1`，stderr 含 `Traceback` 且含原始消息（证明这不是"消息也丢了"，只是"没了裸栈"这一件
  事被修复）。恢复后字节级校验通过。

### F-58

- **正向（真实 CLI，非直接 import）**：`--candidates-json` 传 `{"results":[...]}`（信封包裹）→
  `returncode==2`，stderr **不含** `Traceback` 也**不含** `AttributeError`，含
  `must be a JSON array of candidate objects` 与 `not a dict`。另一种错误形状——列表本身对但元素
  不是对象（`["not_a_candidate_object"]`）→ 同样 `returncode==2`，含
  `each overlay candidate must be a JSON object`。
- **反向**：合法的 candidates 列表仍 `returncode==0` 且产物字段正确；**既有的更深一层检查**（候选是
  合法对象但缺 geometry）仍然独立触发，消息不变（`must carry drawable geometry`），证明新加的两处
  形状检查没有影响原有校验的触达路径。
- **neuter（关键：只动 F-58 一个文件，F-54 的修法保持原样）**：把 `tools.py` 换回未修版本（
  `run_cv_probe.py` 不动），重建 staging，重放信封包裹的正向用例 → `returncode==1`，stderr 同时含
  `Traceback` **和** `AttributeError` 与原始报错 `'str' object has no attribute 'get'`。
  **这证实了 F-54 的捕获类型（ValueError/OSError）确实接不住 AttributeError**——F-54 单独在场
  救不了这个场景，必须 F-58 自己把异常类型换成 ValueError 才行。两条修法互相独立、谁都不是半个
  修法搭另一半的便车。

### F-53

- **正向**：测试**从磁盘动态读取** `cv_toolbox.md` 当前内容（不是把文档文字复制成测试里的字符串
  常量），正则提取出当前的 `--batch` 那一行命令，在 staging 里先创建它引用的文件
  （`requests/sweep.json`，带一个可执行的最小 batch 请求），再把提取到的整行命令交给真实 shell
  （`subprocess.run(..., shell=True)`）执行 → `returncode==0`，stderr 不含
  `cannot open name`，且输出的 JSON 里 `request_count==1`、`results[0].tool=="wall_line_profiler"`——
  不仅 shell 没误解，命令本身也真的成功跑通并做了正确的事。另有一格断言当前文档引用的路径
  不再匹配占位符正则 `<identifier>`。
- **反向**：① 文档里其它代码块（用 `wall_line_profiler` 的第一块）依然逐字节可跑；
  ② 全文档 7 个代码块扫一遍，去掉单/双引号内的内容后，找不到任何 `<identifier>` 形状的裸 token
  （这条同时是 §1 F-53 段落说的"顺手排查"落成的正锁）。
- **neuter**：把 `cv_toolbox.md` 换回未修版本（内容里含 `<name>`），**测试不改一行**——它是从磁盘
  动态读的，同一份代码这次读到的就是旧文本——重放同一个"正向"逻辑 → 提取出的命令带
  `<name>`，真实 shell 执行后 `returncode!=0`，stderr 含 `cannot open name`（shell 把 `<`/`>`
  解析成重定向后的真实报错）；全文档扫描同时确认此时**恰好**能找到这一个 `<name>` 占位符
  （不多不少），与 §5#5 grid_A.md 记录的原始缺陷现象完全吻合。恢复后字节级校验通过。

### 会话中断恢复后的完整性核对（2026-08-17）

因额度中断插入了一轮状态核对（详见对话记录），核对内容：① 四把 `_neutered()` context manager 全部
`try/finally` 完整、无中途遗留的"改坏状态"；② 四个修法文件的当前内容与本节描述的修法逐一对得上
（用文件里各自的特征字符串核对）；③ `tests/test_substrate_sweep_tools.py` 内 `xfail` 标记数为 0；
④ 摊 I 四个禁碰文件 `git diff --stat` 为空。核对方式与结论见对话记录，此处只登记"核过、干净"这一事实。

---

## 3. xfail 摘掉/改成正锁 —— 逐把清单

改动文件：`tests/test_substrate_sweep_tools.py`（本文件不在摊 II 的禁碰清单内，派工单本身要求
把里面的 xfail 改成正锁）。

| # | 测试函数 | 归属缺陷 | 派工单是否点名 | 处理 |
|---|---|---|---|---|
| 1 | `test_s2_bbox_native_json_array_form_a` | F-52 | ✅ 点名 | 摘 `xfail`，断言从只查 `returncode==0` 加强为同时查 `crop_size_px==[120,60]` |
| 2 | `test_s2_bbox_native_json_array_form_c` | F-52 | ✅ 点名 | 同上 |
| 3 | `test_doc_example_batch_placeholder_is_not_shell_safe` | F-53 | ✅ 点名 | 摘 `xfail`；常量 `DOC_5_BATCH_PLACEHOLDER` 改名为 `DOC_5_BATCH_EXAMPLE` 且值同步文档新文本；测试体新增「先写 `requests/sweep.json`」这一步，并加 `request_count==1` 断言 |
| 4 | `test_s2_wrapper_validation_errors_are_clean_not_raw_tracebacks` | F-54 | **⚠️ 未点名（见 §6 第 1 条）** | 摘 `xfail`，加一行 `assert "probe parameter name is empty" in proc.stderr` |

四把摘除后，`tests/test_substrate_sweep_tools.py` 内 `@pytest.mark.xfail` 数量为 0
（`grep -c` 核实）；顺手把 `test_grid_crop_zoom` 里一处指向"F-52 是 xfail cell"的过期注释更新为
"F-52 现已修复"，不影响该测试断言本身。

---

## 4. 被改红的既有锁 —— 逐处清单

**无**。本摊没有任何一把非 xfail 的既有锁被改动断言或改红。理由：

- 四条修法都是**放宽接受面**（bbox 多接受一种写法、main() 多捕获两类已知异常、overlay_logger
  在崩溃前多做一次形状校验、文档改了一处不改变工具行为的文字）——没有一条是"缩紧现有行为"，
  不存在"以前通过、现在应该失败"的既有场景。
- 已用 §2 的"反向"验证逐条确认：所有先前就能工作的调用形态（bbox 逗号字符串、
  合法 request、合法 overlay candidates、文档其余代码块、argparse 自身错误路径）在修法后
  行为不变。
- 回归口径要求的三个文件跑测结果见 §7，`test_cv_toolbox.py`/`test_isolation.py` 内既有测试
  （非本摊新建/新改）零失败、零断言变更。

---

## 5. 被证伪 / 被核实成立的前提

### 核实成立（未证伪，逐条列出核verification 方法）

1. "这些错误消息本身写得很用心……问题不是消息内容，是它被埋在堆栈里"——核实成立。
   F-54/F-58 两处修法均把原始消息字符串原样保留、原样打印，§2 的每格证据都断言了消息文本
   本身在场，不是只断言"不崩了"。
2. "顺手扫查 `cv_toolbox.md` 全部代码块，找其它同类占位符"——扫过，**只有派工单点名的这一处**，
   见 §1 F-53 段与新建的正锁。

### 证伪 / 更正

1. **"今天普查立的 xfail 里有三把钉的正是你要修的东西（两把 F-52 + 一把 F-53）"——不完整，
   实际是四把。** 派工单这句话枚举的 3 把（`test_s2_bbox_native_json_array_form_a` /
   `_form_c` / `test_doc_example_batch_placeholder_is_not_shell_safe`）确实都存在且都归本摊，
   但 `tests/test_substrate_sweep_tools.py` 里其实还有第 4 把 `xfail(strict=True)`——
   `test_s2_wrapper_validation_errors_are_clean_not_raw_tracebacks`，直接钉住的正是 F-54
   （wrapper 裸堆栈），而 F-54 明确是派工单 §2 要求本摊修的四条之一。这把锁没有被那句"三把"
   的枚举提到，但按同一段文字自己的逻辑（"你的修法会让它们意外变绿"）它显然也在被覆盖范围内。
   已实测验证：修完 F-54 后，这把锁如预期变绿变红（xfail 场景下 XPASS），已按同样的规则摘掉
   `xfail` 改成正锁（§3 第 4 行）。**这是外围论据错误（枚举漏了一项，不影响任何承重结论），
   按分层规则记录后继续做完，未停下。**
2. **F-52 修法方向"是否两头都做"——派工单把这个留作开放问题让本席判断，不是一个断言，
   谈不上"证伪"，但判断过程本身发现了一个反直觉的结果，值得单独记录**：直觉上"两头都做"
   听起来最保险，但把 `bbox` 加进 `JSON_OR_PATH_KEYS` 这半个"两头"实测会**引入新的真实回归**
   （把当前唯一能工作的逗号字符串写法送进路径解析、直接崩掉）。已在 §1 F-52 段详细写出这个
   判断的推理链和反例，本单最终**只改了 `_bbox()` 一个点**，理由是这个单点已经覆盖了"两头"
   本来想覆盖的全部场景，且不引入新回归。

未发现其它可证伪的 ⚠️ 前提。

---

## 6. 没做完的部分

- **无**。四条缺陷的修法、三向行为验证、四把 xfail 转正锁、执行日志全部完成。
- 派工单 §4 要求的三个回归文件（`test_substrate_sweep_tools.py` / `test_cv_toolbox.py` /
  `test_isolation.py`）联合跑测结果见 §7（因摊 I 并发改动 `isolation.py`/`guard.py`/
  `test_isolation.py` 导致中途有一次基线读数被污染，已等待其阶段性稳定后重新起跑，
  过程记录见对话记录，不重复贴入本文件）。

---

## 7. 回归口径结果

`pytest tests/test_substrate_sweep_tools.py tests/test_cv_toolbox.py tests/test_isolation.py -n0 -q`

**结果：324 passed, 0 failed, 0 xfailed，退出码 0，耗时 482.59s（约 8 分钟）。**

按文件拆分（`--collect-only` 核对用例数）：`test_substrate_sweep_tools.py` 47 个
（本摊 47 = 43 原有正锁 + 4 把 xfail 全部转正锁，见 §3；47 = 0 xfailed 已验证）·
`test_cv_toolbox.py` 29 个（零改动，全部沿用既有断言）·`test_isolation.py` 248 个
（该文件同期被摊 I 并行扩充，本摊零改动、只作只读回归对象）。三者相加
47+29+248=324，与总数吻合。

**这一次回归是在摊 I 的并行改动（`isolation.py`/`guard.py`/`test_isolation.py`）已完成当前一轮
落盘之后跑的**——此前有一次尝试因摊 I 仍在改动同一批文件而读数不可信（`test_isolation.py`
当时出现大量与 `access_log.jsonl` 路径相关的失败，均可归因于摊 I 的 F-55 迁移工作正在进行中，
与本摊四条修法无关），已弃用该次读数，详见对话记录。本节数字是等待摊 I 阶段性稳定后
重新起跑的结果，是本摊唯一采信的回归证据。

`git diff --stat` 确认本摊触碰文件集合：

```
scripts/tool_scripts/cv_probe.py
skills/intake_pipeline/0_reading/cv_toolbox.md
src/agent/execution/isolation_templates/run_cv_probe.py
src/agent/reading/cv_toolbox/tools.py
tests/test_substrate_sweep_tools.py        (新增：改 xfail 为正锁)
tests/test_substrate_fix_tools.py          (新建)
```

`git diff --stat` 对摊 I 禁碰文件（`src/agent/execution/isolation.py` /
`src/agent/execution/isolation_templates/guard.py` /
`tests/test_substrate_fix_cleanroom.py` / `tests/test_substrate_sweep_policy.py`）为空
（本摊零改动，那些文件里出现的修改属于摊 I 自己的工作）。

`run_cv_probe.py` 内仅动了 `main()` 函数体与其上方新增的 `_EXPECTED_ERRORS` 常量；
`JSON_OR_PATH_KEYS` / `OUTPUT_ROLE_KEYS` / `ALLOWED_TOOLS` / `_writable_root` 均未触碰
（`git diff` 逐行核对确认，见对话记录）。

---

## 8. 备份记录

改动前按本仓硬纪律备份到：

- `backup/src_history/2026-08-16_substrate_fix_II/run_cv_probe.py`
- `backup/src_history/2026-08-16_substrate_fix_II/tools.py`
- `backup/Skill_history/2026-08-16_substrate_fix_II/cv_toolbox.md`
- `backup/scripts_history/2026-08-16_substrate_fix_II/cv_probe.py`
  （`scripts/` 不在派工单 §5 明文列出的 `src`/`skills` 两类里，但为与本仓通用的
  `backup/{src,Skill,scripts}_history/` 备份纪律一致，仍一并备份；这四份备份也是
  §2 全部 neuter 测试的"pre-fix original"数据源。）

这些备份文件同时是 `tests/test_substrate_fix_tools.py` 里全部 neuter 测试的数据源
（`_neutered()` context manager 直接读取这四个路径）。
