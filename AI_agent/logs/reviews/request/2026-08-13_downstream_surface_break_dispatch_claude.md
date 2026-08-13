# 派工单 · 摊 F —— 下游 `surface` 节点确定性崩溃：定位机制 + 修通 + 补韧性

- **日期**：2026-08-13
- **席位**：Claude 侧执行档（Sonnet 5）
- **审阅去向**：GPT 侧（跨家族）
- **⭐ 为什么这摊最优先**：**用户当前的目标就是「好 reading 产物一路跑完」**，而这是唯一挡在那儿的东西。
- **并行席位**：另有一摊（摊 G）在改 `scripts/tool_scripts/run_stage.py` + `src/agent/judge/*`。
  **你的文件面 = `src/agent/graph.py` / `src/agent/react.py` / 下游 subagent 与工具实现 / 必要时 `src/agent/llm.py`**。
  ⛔ 绝不 `git add -A` / `stash` / `checkout`；⛔ 不要 commit。

---

## 0. 停止规矩（分层）

1. **承重前提错**（错了则任务方向作废）⇒ **停下上报**。
2. **外围论据错**（不改变方向）⇒ **报告里写明「派工方这句错了 + 你的实测」，继续做完主体**。

派工方历史错误率 **17/17**（今日两条：给摊 C 的验收条件互相冲突 · 把「目录 append-only」错说成「账本 append-only」）。
⇒ §2 每条都请主动证伪。**尤其 §3 的机制假设我一条都没验证，它们是待证伪的猜测，不是结论。**

## 1. 现象（orchestrator 实测）

真实 run：`case_tests/e2e_tests/sm21_anchor/run_2026-08-13_post_blocker1_e2e`
（0–5 段全部 accepted，见其 [README.md](../../../case_tests/e2e_tests/sm21_anchor/run_2026-08-13_post_blocker1_e2e/README.md)）。

```
[EP node=intake] → zone → material → schedule → cross_ref_foundations → construction   ← 这些都完成了
✗ EP downstream run failed: BadRequestError: Error code: 400 -
  "An assistant message with 'tool_calls' must be followed by tool messages responding to
   each 'tool_call_id'. (insufficient tool messages following tool_calls message)"
```

- 日志打印的是**已完成**节点；节点序（`graph.py:103-104`）= `construction → surface → fenestration`
  ⇒ **崩在 `surface`**（要建 **100 个面**，全链工具调用最密集的一段）。
- **确定性**：orchestrator 连跑两次，**逐字同一错误、同一位置**（⛔ 不是抽风）。
- flow 退出码 **30**，**EP 零产物**。

## 2. 承重前提（我怎么验的写在括号里，请证伪）

| # | 前提 | 我怎么验的 |
|---|---|---|
| P1 | **不是今天的改动搞坏的** | `git show --name-only da2245d` 只碰 correction/judge/execution/scripts，**下游一行没动**；`git log -- src/agent/graph.py src/agent/react.py` 最近一次是 `299149c` |
| P2 | **同样的输入 08-11 跑通过**（下游全过 + EP 0 Severe） | `run_2026-08-11_continuous_e2e/EP/EP_run/` 有完整产物；本 run 识图与它**逐字节相同**（`cmp` 验过），2_modelling 顶点**460 个逐位同序全同** |
| P3 | **复现极便宜** | 本 run 的 0–5 段已全部 accepted ⇒ 直接重跑 `flow ... --judge off --geometry auto --with-ep`（**不加 `--from`**）会从下游续，**不重跑任何 LLM 校正段**。orchestrator 已用此法复现第二次 |
| P4 | react 循环用 LangGraph 标准 `ToolNode(handle_tool_errors=True)`，且 `llm.bind_tools(tools, parallel_tool_calls=False)`（`react.py:41,51-55`）⇒ 「N 个调用少回 N 条结果」在正常路径上应当维持 | 读源码 |
| P5 | **下游这一整段没有韧性**：4_mep 有**段级重试**（本 run attempt 001 崩、002 过，自愈了）；下游一个 provider 400 直接带倒整条 flow | 本 run 实测两处对照 |

## 3. ⚠️ 待证伪的机制假设（⛔ 我一条都没验证，不要当结论）

按你自己的实测排除/确认，**不要照着改**：

1. provider **忽略了 `parallel_tool_calls=False`**、一条消息里塞了多个调用，而回填只答了一个；
2. 消息历史在某处被**截断/裁剪**（长循环 + 100 次调用的历史很长），把带 `tool_calls` 的那条留下、对应结果丢了；
3. LangGraph **recursion/step limit** 在循环中途终止，留下未被回答的 `tool_calls`；
4. 某个工具在 `ToolNode` 的错误处理**之外**抛出（例如序列化阶段），导致该 id 没有结果消息；
5. provider 端行为变化（P2 成立 ⇒ 仓库外的变化是最可能的一类）。

⭐ **请先把「到底是哪一条」用证据定下来再动手**。建议第一步 = 把 `surface` 那一轮的**真实消息历史**
（含每条 assistant 消息的 `tool_calls` id 与其后的 tool 消息 id）dump 出来对账 —— `src/agent/trace.py`
里已有 `TraceCollector`，`build_react_agent` 支持传 `trace_collector`（⇒ 可能不需要新造设施）。

## 4. 要交付的两件事

### 4.1 修通（主体）
让**这个 run 的下游一路跑到 EnergyPlus**。⛔ 硬禁止：
- ⛔ **不许靠放宽/关闭任何门**来「跑通」；
- ⛔ **不许静默换模型/换 provider**当修法（若你判断必须换，**停下上报**，这是用户决策）；
- ⛔ **不许把 100 个面拆成「少建几个」**之类降低真实工作量的做法。

### 4.2 补韧性（同样重要，别省）
**一个 provider 400 不该带倒整条 flow。** 下游那一段需要与 4_mep 等价的**重试/降级**：
至少让**可重试的 provider 侧错误**得到有界重试，且**失败要落下可诊断的证据**（哪个节点、第几轮、消息历史摘要），
⛔ 不是把异常吞掉当成功。**若你认为韧性应落在 flow 编排层而不是下游内部，说明理由后按你的判断做，并在报告里点名。**

## 5. 验收条件

1. **真实 run 跑通**：`run_2026-08-13_post_blocker1_e2e` 的下游走完 + `EP/EP_run/eplusout.end` 存在
   且 **0 Severe**；把 `eplusout.end` 那一行原文贴进报告。
2. **⛔ 先证明你的修法针对的是真机制**：给出「未修时逐字复现该 400 → 修后同一入口通过」的对照实测。
   ⛔ 不许只给「现在过了」。
3. **锁**：为你定位到的机制补锁（⛔ 不许只测「跑通了」）；每把新锁做 **neuter 实测**（中和实现 ⇒ 转红 + 红点位置对）
   并回答**「不加这处改动，这道门本来红不红」**。
   ⚠️ 若该机制**只能靠真实 provider 复现**（无法在单测里稳定构造），**如实说明**并至少锁住
   **韧性那一半**（模拟一个可重试错误 ⇒ 重试路径被走到 + 有界 + 失败留证据）。
4. **全仓**：`python -m pytest tests -q -n auto` 与基线 **`2573 passed / 10 xfailed / 0 failed`** 对账、零回归；
   **判跑完看 `N passed` 汇总行**；退出码文件**用新文件名**。⚠️ 打印式探针用 `-n0`（`-n auto` 吞 worker stdout）。
5. **如实分账**：实测 / 推理 / 未验各自列清。⛔ 不许把未验证项写成已验证。

## 6. 运维

- **本摊必须能在一个 5 小时额度窗内收尾**。若「定位机制」本身就吃掉一个窗口，
  **交付「机制已定位 + 证据」并停下上报**也算合格 —— ⛔ 但不要停在「改了行为、锁一把没写」的中间态。
- 中断时**不要总结自己做了什么**（本项目已三次实证席位自述不可信，orchestrator 一律以 `git diff` 为准）。
