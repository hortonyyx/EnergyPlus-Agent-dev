# 派工单 · 摊 H —— `surface` 节点 400 重新诊断（⛔ 上一轮的机制结论已被证伪）

- **日期**：2026-08-13
- **席位**：GPT 侧（跨家族 —— 上一轮诊断由 Claude 侧做出且结论错误，按「判错的稿子不宜同一作者重写」换人）
- **审阅去向**：Claude 侧
- **基线**：全仓 `2589 passed / 10 xfailed / 0 failed`（orchestrator 独立实测，rc=0 + 汇总行）
- **代码基线**：`41f73e7`（含上一轮的修法与诊断插桩）

---

## 0. 停止规矩（分层）

1. **承重前提错** ⇒ **停下上报**。2. **外围论据错** ⇒ 报告写明后继续做完主体。
派工方历史错误率 **18/18**（本条新增一例见 §4）。请主动证伪本单每条。

## 1. ⛔ 上一轮的结论错在哪（这是本单存在的理由）

上一轮（摊 F）判定机制 = **「DeepSeek 无视 `bind_tools(parallel_tool_calls=False)`，一条 AIMessage 塞 28 个
tool_calls」**，修法 = `react.py::_enforce_single_tool_call`（只保留第一个、丢弃其余）+ 有界重试 3 次
+ `ReactLLMCallError` 携带消息配对摘要。

**该结论已被它自己加的诊断插桩证伪。** orchestrator 在**干净的单次验收跑**
（`run_2026-08-13_oneshot_acceptance`，同一代码基线）上复现同一个 400，而现场是：

```
8 total messages; unpaired tool_call_ids at end: []
total AIMessage tool_calls emitted: 3; total ToolMessages: 3
multi-call turns (parallel_tool_calls should be False): []     ← 没有批量
DUPLICATE tool_call ids within AIMessage.tool_calls: {}
DUPLICATE tool_call_id across ToolMessages: {}
ToolMessages whose tool_call_id matches NO known AIMessage tool_call: []
[2]AI(1 call) [3]Tool [4]AI(1 call) [5]Tool [6]AI(1 call) [7]Tool   ← 逐位配对
```

⇒ **每轮只有一个工具调用、本地历史逐位完美配对，provider 照样 400。**
批量现象**确实存在过**（上一轮在 surface 观测到 28 个/轮），但**它不是（唯一）触发条件**。

## 2. 承重事实（orchestrator 实测，请证伪）

| # | 事实 | 怎么验的 |
|---|---|---|
| P1 | **是间歇性的，不是确定性的** — 修法后 **1 成 1 败**：09:02 那次跑通到 EP（`0 Severe`）、09:34 干净单次跑 400 | 两个 run 目录 + 两份日志与 `.rc` 均在盘上 |
| P2 | **重试 3 次全部失败** ⇒ 一旦历史里有 provider 不接受的东西，**重发同一份历史必然同样被拒** ⇒ **在 LLM 调用层重试治不了被污染的历史** | 报错原文 `LLM call failed after 3 attempt(s)` |
| P3 | 崩得**很早**：`surface` 只发了 3 个工具调用、8 条消息就 400（该节点总共要建 **100 个面**） | 上方诊断输出 |
| P4 | **`thinking: disabled` 的声明是真的作用到了 surface 节点** —— `load_llm_section("surface")` 实测返回 `extra_body={'thinking': {'type': 'disabled'}}`、`model=deepseek-v4-pro` | 我实跑了 `load_llm_section` |
| P5 | 崩溃节点固定是 `surface`（`construction → surface → fenestration`）；`intake/zone/material/schedule/cross_ref_foundations/construction` 每次都过 | 四次跑的日志一致 |
| P6 | 复现便宜：那两个 run 的 0–5 段均已 accepted ⇒ 重跑 flow **不加 `--from`** 会直接从下游续，不重跑任何 LLM 校正段 | orchestrator 用此法复现过 |

## 3. ⚠️ 待证伪的假设（⛔ 我一条都没验证，别照着改）

1. **某条 `ToolMessage` 的 content 为空/近空** ⇒ provider 端不把它算作「已回应」
   （`ToolNode(handle_tool_errors=True)` 会把工具异常转成文本 ToolMessage，也可能产生空内容）。
   ⇒ **诊断插桩现在只打了 id 与配对，没打 content 长度** —— 这是最便宜的下一步。
2. **AIMessage 的 `content` 为空**（只有 tool_calls）⇒ 某些 provider 的轮次校验器不接受。
3. `max_tokens: 64000` 触顶 / `finish_reason=length` ⇒ 上一轮的 AIMessage 被截断，
   本地看起来仍是「1 个合法 tool_call」，但 provider 侧记的那一轮是残的。
4. **上一轮修法自己引入的**：`_enforce_single_tool_call` **丢弃了其余 tool_calls**
   ⇒ 若 provider 端把它**下发过的全部 id** 都算进「必须被回应」，那么**我们只回一个 = 结构上必然 400**。
   ⚠️ **这条假设与 P1 的「1 成 1 败」都能对上，优先级最高**：
   09:02 那次可能恰好没触发批量、所以没丢弃、所以通过；09:34 触发了批量 ⇒ 丢弃 ⇒ 必然 400。
   **⇒ 若成立，则上一轮的修法不是修复而是新的致因**，必须改成「回应全部 id」而不是「丢弃」。
5. provider 侧其它未知的轮次校验规则。

**⭐ 请先把 §3.4 判掉**（它可以只靠**读上一轮的日志/诊断**与**一次带 content 长度与 finish_reason 的插桩跑**判定）。

## 4. ⛔ 派工方本轮的错（如实登记，第 18 例）

orchestrator 在验收条件里写「**每一段 attempts 必须 = 1**，出现 attempt 002 即判不通过」——
**这条对 `1_correction` 是错的**：该段正常就会写两次（基础写入 + 方位增强写入），
本 run 的 `1_correction attempts=2` **不是重试、不是错误**。
✅ 该条真正想抓的是 **4_mep 的解析器崩溃**，而本 run **4_mep attempts=1（未复发）**。
⇒ **验收条件 A3 应改为「除 1_correction 的两次法定写入外，任何段不得出现重试」。**

## 5. 交付要求

1. **机制定死**（本摊的核心产出）：给出**证据**，不是推断。⛔ 不许在机制未定死时改代码「试试看」。
2. **若 §3.4 成立** ⇒ 修法必须是**回应 provider 下发的全部 tool_call id**（而不是丢弃其余），
   并说明这与 `parallel_tool_calls=False` 的关系。
3. **验收跑**：新建 run、复用同一份冻结识图、**单次 flow 调用**从 1_correction 跑到 EP，
   要求 **真实退出码 0 + `0 Severe` + IDF 100 面/15 窗/14 区 + 4_mep 无重试**。
   ⚠️ 因 P1 是间歇性，**必须连跑 ≥3 次单次调用全部通过**才算稳（⛔ 一次通过不算）。
4. **锁**：为定死的机制补锁（含**正向**锁）；每把新锁 neuter 实测 + 回答「不加这处改动本来红不红」。
5. **全仓**与基线 `2589 / 10 / 0` 对账、零回归；判跑完看 `N passed` 汇总行；退出码文件用新文件名。
6. **顺带修一处编号撞车**（纯记账）：上一轮把自己标成 `F-25`，而 `F-25` 已是「两个同名常量」那条；
   本族缺陷应为 **F-26**。请把 `src/agent/react.py` 里的 `F-25` 注释改为 `F-26`。
7. **如实分账**：实测 / 推理 / 未验。⛔ 不许把未验证项写成已验证。

## 6. 运维

- 单摊须能在一个 5 小时额度窗内收尾；做不完就停下上报（⛔ 别停在「改了行为、锁没写」）。
- ⛔ 绝不 `git add -A` / `stash` / `checkout`；⛔ 不要 commit。
- 中断时不要总结自己做了什么（orchestrator 一律以 `git diff` 为准）。
