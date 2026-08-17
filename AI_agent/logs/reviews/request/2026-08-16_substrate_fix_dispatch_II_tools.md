# 派工单 —— 基座修法批·摊 II：工具面参数语义 + 错误可操作性 + 文档（F-52 / F-54 / F-58 / F-53）

**席位**：执行档（Claude Sonnet 子代理）
**并行摊**：摊 I（净室写面 + 守门件，F-55/F-56/F-57）由另一席位同时进行，**文件集合与你不相交**。

---

## 0. ⭐ 先读：「停下上报」分层

- **① 承重前提错 ⇒ 停下上报**；**② 外围论据错 ⇒ 记录后继续做完**（凡标 ⚠️前提 的句子）。
- **⛔ 派工方错误率 25/25** —— 本单凡「一律 / 全部 / 应该是」当作**可能错的前提**，请主动证伪。

---

## 1. 背景

读图器在隔离沙箱里调 CV 工具的唯一入口是 `tools/run_cv_probe.py`（wrapper）→ `cv_probe` → 工具库。
2026-08-16 的基座普查逐格实跑，在工具面撞出四条。
全表：[`../../experiments/2026-08-16_substrate_sweep/README.md`](../../experiments/2026-08-16_substrate_sweep/README.md)
· 分表 [`grid_A.md`](../../experiments/2026-08-16_substrate_sweep/grid_A.md)。

**这四条的共同形状**（⚠️ 这是我的归纳，可能错，请证伪）：
**读图器按文档/自然写法去用工具，工具用一种它无法据以自救的方式失败。**
F-49（那把量尺两种文档形态全跑不通、潜伏五周）是同族的上一例。

---

## 2. 你要修的四条

### F-52 —— `bbox` 的原生 JSON 数组写法在 `--request` / `--batch` 形态下崩溃

**现象（主控已独立复现）**：
```
{"tool":"crop_zoom","args":{...,"bbox":[100,80,700,460]}}   → 退出码 2: invalid _bbox value: '[100,80,700,460]'
{"tool":"crop_zoom","args":{...,"bbox":"100,80,700,460"}}   → 退出码 0
```
**根因**：`bbox` 不在 wrapper 的 `JSON_OR_PATH_KEYS` 里 ⇒ 走通用分支被 `json.dumps` 成单个 token，
撞上 `cv_probe._bbox` 的朴素逗号切分解析器。

**影响面**：`crop_zoom` 是**唯一以 `--bbox` 为必需参数**的工具，而 `bbox` 又是 6 个公共参数之一
（另外四个工具都能用它限定分析区域）⇒ 任何工具只要用 JSON 形态 + 原生数组写 `bbox` 都撞。

⚠️ **修法方向由你判断并给理由**（这一条是设计选择，不是照抄）：
是让 `_bbox` 也接受 JSON 数组？还是把 `bbox` 纳入「JSON 或字符串皆可」的那条分支？
还是两头都做？**要点是别只修一半** —— F-49 的教训正是「文档写的两种形态全跑不通，
而唯一可用的第三种形态没有任何文档写过」。**修完要保证：文档写出来的每一种写法都真能跑。**

### F-54 —— `run_cv_probe.py::main()` 对解析失败零异常兜底

`_direct_to_request` / `_request_to_argv` / `--request`/`--batch` 的文件读取
（`_resolve`、`read_text`、`json.loads`）**全部没有包在任何 try/except 里**
⇒ `ValueError` / `OSError` / `JSONDecodeError` 以**裸 Python 堆栈**（退出码 1）冒出，
而不是像 cv_probe 自己那样给 `parser.error` 的干净文案（退出码 2）。

复现：`python tools/run_cv_probe.py --tool wall_line_profiler --`

⚠️前提（请核）：这些错误消息本身写得很用心（`_request_to_argv` 里带可复制的 JSON 示例）
—— **问题不是消息内容，是它被埋在堆栈里**。修法应保住消息内容。

### F-58 —— `overlay_logger` 传错形状时吐裸 `AttributeError`

`--candidates-json` 传成 `{"results":[…]}`（而非 `[…]` 列表）时，
报的是 `AttributeError: 'str' object has no attribute 'get'`（`src/agent/reading/cv_toolbox/tools.py:711`），
不是可操作的校验错误。**读图器从文档学形状，学错时拿到的是栈不是指导。**

### F-53 —— 文档里的占位符尖括号在真 shell 里会被当成重定向

`skills/intake_pipeline/0_reading/cv_toolbox.md` 第 53 行：
```
python tools/run_cv_probe.py --batch requests/<name>.json
```
逐字粘进真 shell ⇒ `<` `>` 被解析成重定向 ⇒ 实际执行 `--batch requests/`、
stdin 读文件 `name`、stdout 写文件 `.json`，**报错与真实问题毫无关联**。

**与 F-45 同族但机制不同**：F-45 挡在 guard 的命令白名单，F-53 挡在 **shell 的元字符解析**，
guard 和 wrapper 都不参与、也管不到 ⇒ **只能在文档侧修**。

⚠️ **顺手做一件事**：`cv_toolbox.md` 里**所有**可执行代码块，逐个检查还有没有别的
「逐字粘贴就跑不通」的写法（今天的普查只跑了示例本身，没有系统查占位符）。
⛔ 但**只改文档措辞**，不要借机改工具行为。

---

## 3. 交付

1. **修法本体**（`scripts/tool_scripts/cv_probe.py` · `src/agent/execution/isolation_templates/run_cv_probe.py` ·
   `src/agent/reading/cv_toolbox/tools.py` · `skills/intake_pipeline/0_reading/cv_toolbox.md`，按需）；
2. **行为验证**（每条都要）：**正向**（原来跑不通的现在通且数对）+ **反向**（原来能跑的仍能跑）
   + **neuter**（中和修法 ⇒ 新锁变红 ⇒ 还原 ⇒ `git diff` 零残留）；
3. **新锁** → `tests/test_substrate_fix_tools.py`（新建），**走真实入口**
   （真 staging + 子进程跑 staged wrapper，⛔ 不许直接 import 工具函数——F-49 潜伏五周正因为库层测试全绿）；
4. **执行日志** → `AI_agent/logs/reviews/execution/2026-08-16_substrate_fix_II_execution_log.md`。

**⭐ 特别要求**：今天普查立的 4 把 `xfail(strict=True)` 里有两把钉的就是 F-52
（`test_s2_bbox_native_json_array_form_a` / `_form_c`），一把钉 F-53。
**你的修法会让它们意外变绿 ⇒ pytest 报红 ⇒ 那是正确行为**（提醒摘掉 xfail）。
请把这些 xfail **改成正锁**，并在日志里逐把列出来。

---

## 4. ⛔ 回归口径

- **必须跑**：`pytest tests/test_substrate_sweep_tools.py tests/test_cv_toolbox.py tests/test_isolation.py -n0 -q`
- 凡被你改红的既有锁，⛔ **不许直接改锁让它变绿** —— 逐条判断旧语义该不该翻，
  **有意推翻的在日志里逐处列出（第几把、旧语义、为何该翻）**。

---

## 5. 纪律

- **⛔ 不许碰**：摊 I 的文件（`src/agent/execution/isolation.py` ·
  `src/agent/execution/isolation_templates/guard.py` · `tests/test_substrate_fix_cleanroom.py` ·
  `tests/test_substrate_sweep_policy.py`）· `AI_agent/` 下除你那份执行日志以外的文档。
  ⚠️ **`run_cv_probe.py` 你我都可能要动** —— 你只动 §2 点名的参数解析部分
  （`JSON_OR_PATH_KEYS` / `main()` 的异常兜底），**⛔ 别动写入面与授权表相关的任何一行**
  （`OUTPUT_ROLE_KEYS` / `ALLOWED_TOOLS` / `_writable_root`）——那是摊 I 的。
- **⛔ 不 commit**。**⛔ 不跑 `pip install -e`**。**⛔ 不跑全仓测试**。
- 真解释器 `/opt/venv/bin/python`。
- **改 `src/` / `skills/` 前先备份**：`cp` 到 `backup/{src,Skill}_history/2026-08-16_substrate_fix_II/`。

---

## 6. 回什么

① 四条各自的修法与理由（尤其 F-52 的方向选择）；② 行为验证三向的证据；
③ 摘掉/改成正锁的 xfail 逐把清单；④ 被改红的既有锁逐处清单；⑤ 你证伪掉的我的前提；⑥ 没做完的部分。
