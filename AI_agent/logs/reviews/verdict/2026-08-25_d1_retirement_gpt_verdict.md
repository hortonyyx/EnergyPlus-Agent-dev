# GPT 跨家族复核裁决 · 双份代码退役（债 D-1）

- **被审 commit**：`98e72d6`（worktree `/workspaces/ep_d1_retire` 的 detached HEAD，**尚未合回主线**）
- **审阅方**：**GPT 家族**（用户 08-25 定「审走 GPT」）　**日期**：2026-08-25
- 请求单 → [`../request/2026-08-25_d1_retirement_crossreview_gpt.md`](../request/2026-08-25_d1_retirement_crossreview_gpt.md) ·
  施工报告 → [`../execution/2026-08-25_d1_retirement_construction_report.md`](../execution/2026-08-25_d1_retirement_construction_report.md)

## ⭐ 结论：**APPROVE-WITH-FINDINGS**

> 退役逻辑与现有消费者行为可接受，**未发现应阻断合并的代码回归**；
> 但 **identity 壳并非普适语义等价**、**AST 判据不能防未来漂移**，
> 且**全量因缺 API 凭据未能在它那边复现「0 failed」**。

## 一、⚠️⚠️ 它抓到 orchestrator 一个错：**我把实现写错了，而且是照抄自述没核 diff**

> 任务书与施工报告都把实现写成 `globals().update(vars(_impl))` / 「整个 namespace」——
> **diff 实际是逐项复制并排除 dunder**。**这个错误会改变对 `__file__`/`__name__` 的分析。**

orchestrator 已核 diff，**GPT 属实**。真实实现：

```python
for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value
```

⇒ 因为**排除了 dunder**，壳的 `__name__`/`__file__` **仍指 tools 文件**（与我请求单里的假设相反）。
⭐ **这正是 §5#8「自述与 diff 冲突一律以 diff 为准」的活例，而我把施工方的自述直接抄进了审阅单。**

## 二、identity 壳：不是模块别名，是**导入时的对象快照**

GPT 实测：`shim is not src`，但 **`shim.grade is src.grade`**，且 **`grade.__globals__ is vars(src)`**。
对壳重绑 `WIDTH_COEFF=9` **不影响 src 函数**；src 的后绑定属性**不会出现在壳中**。

| 风险 | 结论 |
|---|---|
| 模块级可变状态共享 | ⭐ **当前六个 src 模块没有模块级 list/dict/set/cache**，现有夹具也无相关 monkeypatch ⇒ **风险未触发** |
| `python -m src.…` 串扰 | ⛔ 不会 —— `run_all.py:71` 用 `subprocess.run([sys.executable]…)` 是**新进程**。⚠️ **若将来改用 `runpy` 或同进程再 import src，则会共享状态** |
| `__file__` 依赖 | src 侧实质使用仅 `denominator.py:77`，src 深度与旧 tools 深度**都算到同一 repo 根** ⇒ 无害 |
| `__module__` / pickle / `inspect.getsource` | ✅ 独立全仓搜索：**这六件的消费者均无此类依赖**（pickle 命中都是无关的 graph/contract 测试）⇒ 席位那句**对当前仓库成立**，但⛔ 不代表壳普适等价 |
| ⭐⭐ **GPT 新发现的脆点** | 各 CLI 壳先 **`del sys`**，再依赖 src namespace 把 `sys` 转发回来。当前五个带 CLI 的 src 都 `import sys` 所以可跑 —— ⛔ **将来 src 删掉该 import 会让壳 CLI 破裂** |

## 三、⭐⭐ AST 判据的定位：**一次性检查，不是防漂移的门**

它对整个 `FunctionDef` 做 `ast.dump`（只剥 docstring）⇒ **函数名、参数名、局部变量名、语句顺序全参与哈希**。
GPT 三个内存反例实测：

```
local_rename        intersection_size=0
independent_reorder intersection_size=0
helper_split        intersection_size=0
```

> **结论：它主要是「证明这一次六份精确副本已退役」的一次性检查，不是可靠的未来防漂移门。**
> 语义等价重写 / lambda / 顶层逻辑 / 辅助函数拆分都会漏，**而且它未接入 pytest/CI**。

## 四、其余三条

| | 结论 |
|---|---|
| **v1 豁免边界** | ✅ **当前可接受**（两处只共享 `_chain_zero_px`，无 src/run_all 现行链路；保留历史快照更符合证据归档）。⚠️ **但机械豁免过宽**：`split_known_lineage` **只按文件名豁免** ⇒ 这两个文件将来新增任意重复函数也全绿。若保留为长期门，应锁定「文件 + src 目标 + 函数名/哈希 + **恰好 1 个**」|
| **`glm_rework` 连带修复** | ✅ **正确**。锚文本在 `reading_grade.py:175` 的**实际赋值逻辑**中且**仅出现一次**，⛔ 不是碰巧匹配注释。GPT 在两个 commit 上各新鲜跑一次：exit=0、stdout 完全一致、`glm_rework.json` **逐字节相同（SHA-256 同为 `4f3adb…f9cd`）**；连带抽验 7 个产物全部相等 |
| **产物抽验** | ✅ 另抽 `ink_palette` / `denominator` 两条 CLI：改前后 stdout 相同、SHA-256 相同、`cmp` 为 0。⚠️ **但它指出一处矛盾**：施工报告说「167 逐字节 + 4 规范化等价」，而提交内 README 称「只有 1 个例外」⇒ **两个说法对不上**；GPT 能确认抽样零不等价，**但不为精确的 167/4 计数背书** |
| **判据红/绿两态** | ✅ 自己复跑：红态 `8 shared (6 duplicate / 2 exempt)` + 六对逐项列出 + 期望 YES；绿态 `2 shared (0 duplicate)` + (b)=0 + (c)=0 + PASS |
| **范围** | ✅ 9 文件 / +385 −3177，仅 7 个 tools 件 + README + 判据脚本；`git diff-tree --check` 通过；worktree clean |

## 五、⚠️ 全量：GPT 那边 **1 failed**，判为**环境问题**

```
1 failed, 3016 passed, 13 xfailed, 211 warnings in 438.59s
```

唯一失败 = `tests/test_zone_agent.py:30` 创建 OpenAI-compatible client 时**缺 `OPENAI_API_KEY`/`DEEPSEEK_API_KEY`**；
本提交未碰该测试或相关 src。
⇒ **GPT 明确不为「独立复现 3017 passed」背书，要求合回前在有凭据的环境补跑这一项。**
⭐ **orchestrator 注**：主树跑过多次全量均为 `3017 passed`（含该测试通过）⇒ 主树有凭据、worktree 的 codex 环境没有。
**⇒ 合回主线后必须在主树补跑一次全量**，这是 GPT 这条要求的落地方式。

## 六、对施工席位 4 条上报的评估 + **第 5 条**

| # | GPT 的判定 |
|---|---|
| 1（按路径加载只有两处不完整）| ✅ **事实成立且重要**（确有平铺 import 与 subprocess CLI 两条漏列通道）。⚠️ 但「候选 A 只改 `_load`」是**过度表述** —— 派工单 A 本身要求改夹具引用，只是消费清单不完整 |
| 2（行数各差 1 / docstring 逐字相同）| **部分认同**：两对确实逐字节相同、其余四对只差 import/root ⇒「各差一行」错；但**「docstring 相同」仍成立** |
| 3（run_all 已不吃 6 原件）| **事实成立，但⛔ 不算派工方题错** —— 派工单本就说明 run_all 的路径加载对象是 `reconstruct_check_v2`，从未声称它消费六原件 |
| 4（判据多抓 2 对 v1）| **有效的新发现，但⛔ 不等于原清单错误** —— 派工单明确说了清单可能不全 |
| ⭐⭐ **5（GPT 新指出）** | **任务书与施工报告都把实现误写成 `globals().update`／「整个 namespace」** ⇒ 见 §一 |

⇒ **净增的派工方题错 = 第 1 条（消费清单不完整）与第 5 条（实现误述）两处。**

## 七、⭐ 对那条教训的评估：**成立，且应固化得更强**

> 施工席位的原话：「四个『点名必跑』全绿不够 —— run_all 内部拉起的第五个夹具以『结果少一段』的形式**静默失败**。」

GPT 的加强：**`run_all.py:268` 会把子夹具失败写成 `{"error": …}`，而第 395 行仍返回 0。**
⇒ **规范应是「任何子夹具 error / 缺段 / 未刷新 ⇒ `run_all` 非零退出」**，再配合完整 artifact manifest 与规范化对比。
**仅看四个外层退出码确实不够。**

## 八、清理

两个临时 worktree 已全部移除；未改文件、未提交、未 push ✅
