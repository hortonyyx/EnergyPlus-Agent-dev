# GLM 跨家族复核裁决 · 装机路径止血（F-94 A 案）

- **被审 commit**：`91ae82d`　**审阅方**：GLM（glm-5.3）　**日期**：2026-08-25
- **请求单**：[`../request/2026-08-25_f94_bootstrap_crossreview_glm.md`](../request/2026-08-25_f94_bootstrap_crossreview_glm.md)
- **施工报告**：[`../execution/2026-08-25_f94_bootstrap_construction_report.md`](../execution/2026-08-25_f94_bootstrap_construction_report.md)

## ⭐ 结论：**APPROVE-WITH-FINDINGS**

16 个脚本的自举、机械锁、红/绿两段、行为验证、范围纪律**全部独立复验成立**；
全量由 GLM 自己跑绿。findings 5 条**均不阻塞**，其中两条直接决定债 D-2 怎么写。

## 一、⭐⭐ 它正面回答了「这道锁把 A 变成机制了吗」

> **这道锁把 A 从「约定」变成了「机制」—— 但只是【执行机制】（enforcement），不是【根治机制】。
> 「真正的机制性根治仍然只有 B」在有锁之后依然成立，一字不改。**

三条实测证据：

1. **串台的根原样活着**：`.pth` 内容仍是主树绝对路径，实测注入在 `sys.path` **末尾**（index 5 = 最后一项）。
   A + 锁做完，这个全局注入机制**没有任何变化**。
2. ⭐⭐ **锁的覆盖边界 = A 的收窄边界，而覆盖外有【现成的活例】**：
   **`tests_scripts/deepseek_review.py:28`** —— 模块级 `from src.agent.llm import load_llm_section`、
   **无自举**、**docstring 里就有文档化的裸跑用法**。在 worktree 里跑它 ⇒ **静默用主树的代码，锁对此沉默**。
   （⛔ 不是施工失职 —— 派工单范围就框死在 `scripts/`；但它证明**锁关的是「枚举过的那面墙上的门」，不是「拆地雷」**。）
3. **锁只验形态不验参数**：层数写错的自举在锁下全绿而串台依旧 ⇒ **「有 insert」≠「insert 对了」**。

> ⭐ **准确表述**：**锁 = 在一个枚举过的暴露面上，把「忘关门」从静默变成响亮。**
> 它机制化了「**A 的完备性不退化**」这一件事，**没有、也不可能机制化掉串台本身。**

⇒ **D-2 的紧迫度⛔ 不因这道锁降低**。GLM 建议写成
**「中高紧迫、本批收尾前后排期，⛔ 不写『远期』」**，理由：
多席位 worktree 是**常态**工作方式（当前就挂着 3 棵树），每次开树做实验都在 A 覆盖外的入口上冒险；
而 B 案成本并不高（删 `.pth` + 全走 `python -m`），**收益是整个缺陷类目消失**。

## 二、锁的分辨力：✅ 有，且找到一个**假阴性方向**的洞

**独立验证**：`/tmp` 搭探针树，把真实 `gt_promote.py` 的三行自举删掉 ⇒
`RED: 1 offending script(s): scripts/tool_scripts/gt_promote.py (src-import lines: [10])`
—— **红且精确点名** ✅

**七种合成 offender 实测**：

| 形态 | 锁行为 | 判定 |
|---|---|---|
| bootstrap 在模块级 `try:` 里（实际有效）| 红 | 保守误报，安全方向 |
| **`sys.path.append`** | 红 | ⭐ **正确的红** —— append 把自己树排在 `.pth` 之后，**防不了串台** ⇒ 判据选 `insert` 选对了 |
| `os.sys.path.insert` | 红 | 保守误报，极罕见 |
| ⭐⭐ **`parents[5]` 层数写错** | **放行** | ⛔ **唯一假阴性洞**：锁只认调用形态、**不验参数** ⇒ 层数错 = 锁绿而串台依旧 |
| bootstrap + src 导入都在 `if __name__` 里 | 红 | 保守误报（双层嵌套只下潜一层）|
| `from sys import path` 后 `path.insert` | 红 | 保守误报 |
| bootstrap 在函数体内定义并调用 | 红 | 保守误报 |

⭐ **洞的现状盘点**：GLM 逐个核了当前树全部 **22** 个自举脚本 —— `parents[N]` 的 N **全部与脚本深度一致**
（含 5 个先例逐个点名）⇒ **当前树无实例**，故不阻塞。

## 三、其余攻击面 + 验收

| | 结果 |
|---|---|
| **16 这个数** | ✅ 用**独立重写的 AST 判据**扫两棵树：BASE `8c780ba` = **32 / 22 / 6 ⇒ offenders 16**，与改动文件**逐一对应**；HEAD `91ae82d` = **offenders 0** |
| **行为验证** | ✅ 做了、做对了。⭐ GLM 用**零污染方法独立复刻**（不写 marker，改用 `PYTHONVERBOSE=1` 让解释器自己交代）：已修脚本 ⇒ `code object from /tmp/…/f94_wt/src/__init__.py`（**自己的树**）；BASE 版无自举脚本 ⇒ `import 'src'` 全链来自 **主树**，且 `exit=0`。**原样复现施工结论** |
| **主树未污染** | ✅ 独立复核：`src/__init__.py` **0 字节 · `git diff HEAD` 空 · 最后改动 `299149c`（4 月）**；`f94_behavior_wt` 已清 |
| **范围** | ✅ 17 文件 / 300 insertions / 0 deletions，全在 `scripts/**` + 新锁；⛔ 未碰 venv / `.pth` / `src/` / 交接契约 / `AI_agent/` |
| **全量（GLM 自己跑的）** | **`3016 passed, 13 xfailed, 212 warnings in 678.20s (0:11:18)`** exit 0；3014→3016 净增 2 = 锁的两条测试（**两条都在默认收集内**已确认）|

## 四、⚠️ 派工单还有别的题错吗 —— **除「26」外没有**

GLM 逐句对了实测：`.pth` 末尾注入 ✅（index 5）· 6 先例名单 ✅ ·
`guides/` 裸跑命令「≥15 处」✅（**恰好 15**：`new_case_guide.md` 12 + `codex_execution_protocol.md` 3）·
pytest 入口安全论断 ✅（`pyproject.toml:46`）· 锁的要求与实现一致**且实现更强**（延迟导入 + 行号先序）。
⇒ **本轮派工单仅「26」一处题错**（累计 **26/26**）。

两处「定义留缝」它判**不算错**：①「全部**需要它**的脚本」的「需要」未定义 ——
席位以**零例外**化解并单列披露，**处理严格更优**；②范围框在 `scripts/` —— 本就名为 scripts 止血，
但留下的 `tests_scripts/` 缺口**是真窟窿**（finding #2）。

## 五、Findings（⛔ 全部非阻塞）

| # | 内容 | 处置 |
|---|---|---|
| 1 | **锁不验 bootstrap 参数**（只匹配调用形态）⇒ `parents[N]` 层数错则锁绿而串台依旧。当前 22/22 全对、无实例 | 将来加参数形态校验 |
| 2 | ⭐⭐ **锁覆盖外有现存串台入口**：`tests_scripts/deepseek_review.py:28`（模块级 src 导入 + 无自举 + docstring 文档化裸跑）⇒ **「A 收窄不消除」的活证据** | 建议锁的 `_iter_script_files()` 扩一行到 `tests_scripts/`，**或明确并入 D-2** |
| 3 | 保守误报清单（模块级 `try:` / 双层 `if` / `os.sys.path` / `from sys import path` / 函数内 bootstrap 一律判红）—— 会逼作者改回标准形态；⭐ `append` 判红是**正确**的 | 记录在案 |
| 4 | **E402**：ruff `select` 含 `E`、`ignore` 仅 E501/N805/N806 ⇒ 一旦引入 ruff，22 个脚本全红。当前 ruff 未装、零 lint 门 ⇒ **GLM 意见：现在不动**（动了反造 17 文件新 diff、超出本单），将来真引入时用 **per-file-ignores 给 `scripts/**` 关 E402**（自举 idiom 的必然形态，属误报类；6→22 是规模变化不是类别变化，与 §0 科研 P0 口径一致）| 采纳，登记 |
| 5 | 锁的 `__main__` CLI **恒 exit 0**（只打印不设退出码）—— 作演示够用（真门是 pytest 的 assert），但若接进 shell 判红会踩坑 | 加 `sys.exit(bool(result))` 一行事 |

## 六、现场清理

`/tmp/glm_review/mut_wt`（上一轮遗留）**已 remove** ✅ · 本轮探针与验证 worktree **均已清** ✅ ·
全程未改主树、未提交、未 push ✅
