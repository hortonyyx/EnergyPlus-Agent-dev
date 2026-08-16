# 复审裁决 —— 撤除 reading 沙箱「能力封口」（A3）+ F-44

**审阅方**：GPT 侧 sol（`gpt-5.6-sol`，effort high，MCP thread `01a0089c-5698-72b2-9f1e-b24c7738ec86`）。
**施工方**：orchestrator（Opus 5）。**请求书**：[`../request/2026-08-16_a3_capability_uncap_request.md`](../request/2026-08-16_a3_capability_uncap_request.md)。

## 裁决：**CHANGES REQUIRED**（1 BLOCKER）→ 已修 → **⛔ 后半段未审完**

### BLOCKER-1（sol，成立，已修）—— 执行前扫描只覆盖 `.py`

```python
# out/runner.py  ← 被扫，零禁词
exec(Path('out/payload.txt').read_text())   # payload.txt 不是 .py，从未被读
```

sol 端到端复现（`BYPASS True`，`executed_code` 只记了 `runner.py`）。
**非混淆，是普通动态加载。** 它同时证伪施工方写在注释/run_config 里的三句话：
「即将执行的代码都会被扫」「扫的是整个 import 面」「`executed_code` 完整记录实际执行代码」。

**修法（两条互相独立）**：
1. `_scan_reader_authored_code`：`rglob("*.py")` → `rglob("*")`，扫可写目录下**全部可 UTF-8 解码的文件**；
   二进制跳过并在 docstring **明写为残留限制**（不假称已覆盖）。
2. 新增 `EXEC_DENY_DYNAMIC`（`exec(`/`eval(`/`compile(`/`runpy`/`importlib`/`__import__`/
   `load_module`/`exec_module`/`pickle`/`marshal`）—— 按名拒绝「跑 guard 没读过的字节」。

### 施工方自查补充的两条（sol 未走到）

- **F-46 第二形态**：完全不用 `exec` —— `.txt` 携带**路径**，干净脚本 `open` 两次。
  ⇒ 只加机制黑名单挡不住，**必须动文件集合**。
- **F-47 / ⛔ 请求书 §3.4 的主张被自己证伪**：「纯斜杠豁免没放过任何真实路径」是**假的** ——
  `os.walk('/')` 零禁词遍历整个文件系统、guard 放行。
  ⇒ 补 `ROOT_LITERALS`（引号里的根）+ `EXEC_DENY_IMPLICIT_PATHS`
  （`os.sep`/`Path.home()`/`expanduser`/`os.environ`/…），**保住带空格的除法仍可用**。

### 验证

三条修法各自正向 + 反向 + 阴性对照实跑；补 **15 把锁**；
定向子集 273 全绿；全仓 **2662 → 2680 绿 / 10 xfail / 1 红**（F-36 旧债，与本改动无关）。

## ⛔ 未完成的复审（转下轮，不得记为已审）

sol 按请求书 §0「承重前提错 ⇒ 停下上报」的规矩，在 BLOCKER-1 处**正确地中断**，
以下三项**未经外部审**：

1. `_quote_states` / `_check_shell_structure` 手写引号状态机的反例；
2. 请求书 §3.3（扫描词表剔掉 `attempts`/`verdict`/`grade`）能否证伪；
3. 「本轮推翻旧断言共 4 处」这个计数是否漏报第五处。

**续审受阻的原因（如实记，⛔ 两件事要分开）**：
- **GPT 通道**：首轮发起被安全过滤拦 2 次（换防御性表述后第 3 次通过）；
  `codex-reply` 续审又被拦 1 次、换表述后返回**空内容**、再发再被拦 1 次。
  ⇒ **共 4 次未能取得续审输出**，属**通道/风控问题，不是审阅方拒审**。
- **GLM 通道**：已按 `scripts/glm_code.sh -p … --allowedTools "Read,Grep,Glob,Bash"` 派出补审
  （同一份四项任务书），**跑满 50 分钟超时、`GLM_EXIT=124`、零输出**
  ⇒ ⛔ 既不是「已审」也不是「被拦」，是**没产出**。
  **⚠️ 运维登记（F-48）**：GLM headless 席位吃了一份约 2.5 KB 的任务书 + 只读工具集，
  50 分钟零 stdout。下次重试前先用一句话的小任务验通道，⛔ 别直接押长任务
  —— 与本仓已记的「探针零输出 ≠ 目标不存在」同族：**先自证通道能出声。**

**orchestrator 自证（⛔ 不能替代换人审）**：对拍真实 bash 15 条样本 ——
guard 放行的每条 `shlex.split` 与 bash argv 一致，不一致处全在保守方向（bash 当字面量而 guard 拒）。

## ⭐ 本轮方法论产出

- **通用判据**：**撤掉一道「按形态封杀」的门，工作量不在放开，在把判据搬到新的测量点上；
  搬家时旧判据覆盖过的每一种形态都要重新问一遍「新判据看得见它吗」。** 本轮搬了两次才搬对。
  三个提问：**carrier 问题**（只看某类文件吗）· **机制 vs 载体**（两者要各自成立）·
  **写出来 vs 取出来**（运行时取到的路径，文本扫描看不见）。
- **⛔ 派工方错误率 19/19 → 21/21**（请求书 §3.1「口子不存在」+ §3.4「没放过真实路径」）。
- **✅ 请求书里写「派工方错误率 19/19，请主动证伪」当天兑现** —— sol 第一条 BLOCKER 就打在被点名处。
- **对 E1 结论的影响**：E1 跑在有这三个口子的 guard 下，但其「没碰答案」**靠实测不靠保证**
  （逐条读过 `executed_code` 与全部自写脚本，三种形态一种都没出现）。**这正是 F-44 的价值。**
