# F-60 —— guard 把**代码里的英文标点**判成路径穿越 ⇒ 一个文件毒死整个工作区的执行面

**发现时间**：2026-08-17 pilot r1 审阅时（orchestrator）
**状态**：⛔ 未修。本 run 的归因**已被污染**。
**同族**：F-49（工具文档形态跑不通 ⇒ E1「零次用于测量」归因不成立）·
F-52 · 「词法扫描只能判断以文本出现的路径」那条结构性上限。

---

## 一、三条同时成立的事实（逐条实测，非读代码）

判据源码 = [`src/agent/execution/isolation_templates/guard.py:436-439`](../../../../../src/agent/execution/isolation_templates/guard.py#L436-L439)：

```python
if ".." in text:
    return False, "parent traversal token is forbidden"
if "~" in text:
    return False, "home token is forbidden"
```

裸子串匹配，作用在**整份脚本正文**上。后果：

1. **英文省略号被判成上级目录**
   `print("Scanning for vertical walls...")` 里的 `...` 命中 `".." in text`。
2. **表示「约等于」的波浪号被判成家目录**
   `# Find bounds of walls (gray = ~180)` 里的 `~` 命中 `"~" in text`。
3. **⭐⭐⭐ 扫描面是 `out/` 下【全部】 `.py`，不是要跑的那一个**
   ⇒ 只要工作区里存在一个含上述字符的 `.py`，**此后任何 python 命令一律 DENY**，
   哪怕执行的是另一个完全干净的文件。**一个文件毒死整个执行面。**

## 二、判别梯（决定性，四组只改一个变量）

| 组 | `out/` 下留下的 `.py` | guard 结果 | 指名的文件 |
|---|---|---|---|
| A | `measure_1f.py`（读图器自己写的，含 `"...walls..."`）| DENY | `measure_1f.py` |
| B | A 移走，留 `probe_ellipsis.py` = 仅 `print("done...")` | DENY | `probe_ellipsis.py` |
| C | 再移走，留 `probe_tilde.py` = 仅 `x = 1  # about ~180` | DENY（home token）| `probe_tilde.py` |
| D | 只留 `probe_clean.py` = 仅 `print("clean")` | **ALLOW** | — |

⚠️ **我第一次测错了**：初测「移走 measure_1f.py 后仍 DENY」⇒ 差点判定「毒死说不成立」。
真因 = **我自己的探针文件带了同一个毛病**。
靠**打印真实拒绝理由**（而不是看 ALLOW/DENY 这个形状）才分开。
⇒ 又一次「形状匹配 ≠ 行为验证」。

## 三、对本 run 的影响（必须与成绩一起说）

access_log（30 行：27 allow / 3 deny）显示读图器 **真的尝试了像素测量，两次，两次都被拦**：

| 它想干什么 | 被拒理由 | 真实触发字符 |
|---|---|---|
| `python out/measure_1f.py` | parent traversal token | `print("...walls...")` 的省略号 |
| `python -c "<numpy 像素分析>"` | home token | `# gray = ~180` 的波浪号 |
| `ls … \| grep …` | compound shell token `\|` | （另一类，非本条）|

被拦之后它才退回去写整数坐标。

⇒ **⛔ 本抽「没去量」这个观测，至少有一部分是工具链造成的，不是模型的行为。**
⇒ 与 F-49 对 E1 的污染**同形**：`memory/verify-the-path-works-before-blaming-the-model`
白纸黑字记着「判『模型不肯做 X』前先确认做 X 的路是通的」，**本轮差点原样重犯**。

## 四、⛔ orchestrator 自己的错误（如实登记）

我起草的 pilot 审阅意见（`feedback_issued.md`）里：

- **第 5 条写「你的脚本算完 intensity profile 又把结果扔了」—— 事实错。**
  脚本**根本没跑成**，它不是扔了结果，是被 guard 拦在门外。
- **第 1 条「你从没在能分辨墙边的放大倍数下看过像素」—— 不公平。**
  它试过，被拦了。

**该意见尚未发给读图器**（发之前查了 access_log 才发现）。⇒ 派工方错误率 +2。

## 五、修法方向（未拍板，只登记）

guard 里**已经存在**「自由文本不该按路径扫」的框架（`CONTENT_ROLE_KEYS`，
见 `guard.py:196-229`，注释里甚至已举了 `wall_..[0-9]` / `z ~ 0.0` 两个例子），
但**脚本正文这条通道完全没用上它** —— 而代码注释与字符串字面量天然就是自由文本。

三个面，建议分开评估：
1. **判据面**：`".." in text` 太宽。至少要求它出现在**路径形态**里（如 `../`、`/..`、引号内的路径串）。
2. **扫描面**：为什么扫 `out/` 下全部 `.py` 而不是**实际 import 闭包**？
   「一个文件毒死整个执行面」是这条设计的直接后果。
3. **可自救面**：拒绝理由指名了文件与 token 类别，但**没说是哪一行、哪个字符**
   ⇒ 读图器（和我）都要靠猜。同族 F-53/F-54/F-58「失败方式无法据以自救」。

⚠️ 第 1 面**必须小心**：`..` 与 `~` 的确是真实绕过手段，**⛔ 不得直接删掉这两条**。
且 BLOCKER-2（`cwd`/`__file__`/`parents` 锚点族）本就未修 ——
放宽词法面之前要想清楚它与那条的叠加效应。
