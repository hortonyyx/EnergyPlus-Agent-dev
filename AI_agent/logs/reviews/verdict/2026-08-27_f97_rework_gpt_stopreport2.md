> ⛔ **orchestrator 落库说明（2026-08-27）**：这是 F-97 返工审的**第二次派出**，GPT sol **又是开工即停**，
> ⛔ 仍未对 `f2a8ccf` 作任何实体裁决。**累计第 38 次「停下上报」，第 38 次仍全是派工方的题错。**
> 表层病因：我在 §〇 写返工面「另有**三份** md」，`git diff --numstat` 实测是**四份**。
> ⭐⭐⭐ **真正的病因不是这个数** —— 是我把 §六 触发器 #1 写成了**不分层的「数值对不上就停」**，
> 于是一处纯外围的计数错（返工面里有几份 md，与实现质量零关系）**把整轮实体复核全部挡在门外**。
> ⛔ **而这条我 08-12 就写进 memory 了**（[[stop-and-report-catches-dispatcher-errors]] How-to-apply #11：
> 「① 承重前提错 ⇒ 停；② 外围论据错 ⇒ **报告并继续审其余**」）—— **写下自检 ≠ 执行自检**，同一个形状。
> ⇒ 第三次派出已把触发器 #1 改成分层版，并把 §〇 全部数字换成 `--numstat` 逐字读数。
> 以下为复核方**逐字**原件，未改一字。

---

# F-97 契约判别器返工跨家族复核裁决（GPT 家族 sol）

## 总判

**REWORK（STOP-AND-REPORT；仅为程序性裁决，不是对 `f2a8ccf` 实现质量的实体裁决）**

命中请求单 §六触发器 #1「题面与实测不符」，故依题面要求立即停止。没有继续阅读实现、运行定向测试、做变异实验或运行全量；下列 A1–A7 与六处重点均不得据此解释为通过或不通过。

## 停下上报依据

请求单 §〇 对 `git diff 8fda4c1 f2a8ccf` 的返工面陈述为两份源码、一份测试以及“**另有三份 md**”。实际执行：

```text
$ git diff --name-status 8fda4c1 f2a8ccf
M	AI_agent/logs/reviews/execution/2026-08-27_f97_contract_discriminator_construction_report.md
A	AI_agent/logs/reviews/request/2026-08-27_f97_contract_discriminator_crossreview_gpt.md
M	AI_agent/logs/reviews/request/2026-08-27_f97_contract_discriminator_dispatch.md
A	AI_agent/logs/reviews/verdict/2026-08-27_f97_contract_discriminator_gpt_verdict.md
M	src/agent/pipeline.py
M	src/agent/reading/vector_contract.py
M	tests/test_f97_vector_contract.py
```

其中 md 是 **4 份**，不是 3 份。文件名与数量均由 Git 直接给出。请求单 §六 #1 明定“我引用的行号、commit、数值、文件名对不上”即停下上报，因此不能把这个差异自行解释或绕过。

同时核实：

```text
$ git log --oneline -1
f2a8ccf 08.27_F97Rework_DeclaredSchemaNeverFallsBackToLegacy_AndTheLedgerGoesFirst

$ git rev-list --count 8fda4c1..f2a8ccf
1
```

故 HEAD 匹配，且 `8fda4c1..f2a8ccf` 仅有一个提交；触发原因只在返工面 md 数量的题面事实错误。

## A1–A7 逐条读数

| 判据 | 读数 | 结论 |
|---|---|---|
| A1 | 全量未运行；无 summary 行 | **未判定**。继续跑会违反已命中的停下触发器。 |
| A2 | B-01/B-02/B-03 双向验证均未执行 | **未判定**。 |
| A3 | 新锁的生产入口/helper 身份未检查 | **未判定**。 |
| A4 | neuter 未执行 | **未判定**。 |
| A5 | 43/328/371 未独立重数 | **未判定**。 |
| A6 | 主动找缝未执行 | **未判定**。 |
| A7 | N-01/N-02/N-03 未复查 | **未判定**。 |

## 六处重点逐条结论

1. **三条阻断双向验证**：未执行，未判定。
2. **第二处手写清单及机械对账**：未检查，未判定。
3. **两处各分类一遍及分歧输入**：未检查，未判定。
4. **兼容面与字节变化面独立重数**：未执行，未判定。
5. **换方向主动寻找真实输入缝隙**：未执行，未判定。
6. **`CheckReport` 产物侧与生产者形状一致性**：未检查，未判定。

## Findings

### 阻断

- **B-STOP-01 — 题面返工面文件数错误。** §〇 声称另有 3 份 md，Git 实测为 4 份，直接命中 §六 #1。需由 orchestrator 修正或明确撤销该触发后重新派审，才能形成实体实现裁决。

### 不阻断

- 无。由于停下触发器要求即时停止，本轮没有获得足以支持实现层不阻断 finding 的证据。

## orchestrator 题面写错的地方

1. §〇 的“另有三份 md”错误；正确读数为 **4 份 md**。
2. 本次第二版对开工 untracked 状态的修正确实成立：写裁决前，`git status --porcelain` 只有请求单一项。因此本轮不是再次为已修正的那一条停下。
3. §七 #4 所担心的提交范围遗漏未发生：`8fda4c1..f2a8ccf` 实测只有 1 个提交。
4. 其余自认可能写错的数值和事实未核验，原因是触发器要求在首个命中处停止；不能把“未核验”写成“正确”。

## 全量 summary 行

```text
NOT RUN — no pytest summary line; stopped under request §六 trigger #1 before tests.
```

上行是明确的未运行记录，不冒充 pytest 输出。请求单同时要求“命中即停止”和抄录全量 summary；前者在本次已命中，因此不存在可逐字抄录的 pytest summary 行。

## 交件时工作树状态

预期并在写入后核对为：

```text
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
?? AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_gpt_verdict.md
```

仅两项：orchestrator 预置且要求保留的请求单，以及本裁决文件。没有修改被审源码或测试。
