> ⛔ **orchestrator 落库说明（2026-08-27）**：这是 F-97 返工审的**第一次派出**，
> GPT sol **开工即停下上报**，⛔ **没有对 `f2a8ccf` 的实现作任何实体裁决**。
> **它是对的，是我的题错 —— 累计第 37 次「停下上报」，第 37 次都是派工方的题出错了。**
> 病根：我在请求单 §〇 写「工作树干净、`status --porcelain` 为空」，可我**随后自己**把请求单
> 拷进了那个 worktree；再叠上「交件时只剩裁决文件」，两条**结构上不可同时满足**。
> ⇒ 已修题面（§〇 点名那份 untracked 请求单 + 交件状态改成两项）并**重新派出**，
> 实体裁决见 `2026-08-27_f97_rework_gpt_verdict.md`。
> ⭐ 同族已登记：[[stop-and-report-catches-dispatcher-errors]]。
> 以下为复核方**逐字**原件（`/tmp/ep_f97` 内 80 行），未改一字。

---

# F-97 契约判别器返工复核裁决（GPT 家族 sol）

## 总判

**REWORK（流程性停下上报；未对 `f2a8ccf` 的实现质量作实体裁决）**。

开工 HEAD 校验通过：

```text
f2a8ccf 08.27_F97Rework_DeclaredSchemaNeverFallsBackToLegacy_AndTheLedgerGoesFirst
```

但在完整读完请求单后的第一轮只读取证中，工作树起始状态不是题面所称的干净状态：

```text
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
```

这直接命中请求单 §六停下上报触发器 #1（题面与实测不符），并使“不得改动既有文件”与“交件时 `status --porcelain` 只剩复核方自己写的裁决文件”无法同时成立。若删除或纳入版本控制这份既有请求单，又会超出复核方只写裁决文件的授权，命中触发器 #4。故依题面要求立即停止，不继续静态审查、变异、neuter 或测试；以下 `NOT RUN` 不是被审实现失败。

## A1–A7 逐条读数

| 判据 | 读数 | 结论 |
|---|---|---|
| A1 | `NOT RUN`；未启动全量，因开工即命中停下触发器 | 无法判定；没有 summary 行 |
| A2 | `NOT RUN`；B-01/B-02/B-03 未做旧、新 commit 双向验证 | 无法判定 |
| A3 | `NOT RUN`；未逐条判新锁走生产入口还是 helper | 无法判定 |
| A4 | `NOT RUN`；未改被审代码，未做 neuter | 无法判定 |
| A5 | `NOT RUN`；未独立重数 43/328/371 及字节变化面 | 无法判定 |
| A6 | `NOT RUN`；未进行主动找缝实验 | 无法判定 |
| A7 | `NOT RUN`；未复查 N-01/N-02/N-03 | 无法判定 |

## 六处逐条结论

1. **三条阻断的双向验证**：`NOT RUN`，无实体结论。
2. **第二处手写清单**：`NOT RUN`，无实体结论。
3. **两处各分类一遍**：`NOT RUN`，无实体结论。
4. **兼容面独立重数**：`NOT RUN`，无实体结论。
5. **再找一种真实输入形态**：`NOT RUN`，无实体结论。
6. **信任根与生产者形状一致性**：`NOT RUN`，无实体结论。

## Findings

### 阻断

- **B-STOP-01：题面宣称的干净起点与实测冲突。** 初始 `git status --porcelain` 已列出未跟踪的本轮请求单。这不是本复核席创建的文件。
- **B-STOP-02：交件状态要求在当前起点下不可满足。** 保留既有请求单，则交件状态不可能“只剩裁决文件”；删除、移动、提交或改写它，均不是本席获准的复核动作。需由 orchestrator 先明确该文件应当是已跟踪基线、允许保留的例外，或由其在复核开始前清理/提交。

### 不阻断

- 无。因强制停下，未对代码形成任何不阻断 finding。

## orchestrator 题面写错的地方

1. 请求单 §〇称 worktree 在 orchestrator 实测下 `status --porcelain` 为空；本席开工实测并非如此，已有：

   ```text
   ?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
   ```

2. “交件时工作树应只剩复核方自己写的裁决文件”遗漏了上述既有未跟踪请求单，导致该要求在不越权处理既有文件的前提下不可满足。

这正属于题面明确要求直说的 orchestrator 错误；不归因于被审提交。

## 全量 summary 行

```text
NOT RUN — 开工即命中请求单 §六 #1/#4 停下上报触发器，因此没有 pytest summary 行。
```

## 交件时工作树状态

本裁决文件写入后的实际只读核验为两项：

```text
?? AI_agent/logs/reviews/request/2026-08-27_f97_rework_crossreview_gpt.md
?? AI_agent/logs/reviews/verdict/2026-08-27_f97_rework_gpt_verdict.md
```

其中第一项在本席开工前已经存在；第二项是本席唯一写入。
