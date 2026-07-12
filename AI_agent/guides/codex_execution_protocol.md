# 双模型家族协作规约（主控编排 / 分档执行 / 交叉评审）

> **目的**：用户有 Claude + Codex(GPT) 两个订阅、各自 5h 重置窗口。**主控恒为 Claude 家族开对话模型**（保质量 + memory 单一权威），
> 其余角色按「角色 × 档位」矩阵在两家族间分派；**跨厂商交叉评审 = 质量核心机制（谁写谁不批）**。
> 本文 = 操作手册；核心约定同时收录在 [../CLAUDE.md](../CLAUDE.md) §5#8/#10。换主控模型读此接手。
> **2026-07-10 修订**：GPT-5.6 家族发布（有限预览）+ Fable 5 订阅 07-12 到期 → 从「Claude 编排 / Codex 执行」两方模式升级为**完整双模型家族分工**（用户 2026-07-10 拍）。文件名沿用 `codex_execution_protocol.md` 保链接稳定。

## 1. 家族版图（2026-07-10 现状）

| 档位 | Claude 家族 | GPT 家族（Codex 通道） | 说明 |
|---|---|---|---|
| 旗舰 | **Fable 5**（07-12 订阅到期退场）→ **Opus 4.8** | **gpt-5.6-sol**（$5/$30） | sol=Terminal-Bench 2.1 SOTA、长程 agent；Opus=工程秩序/长期协作 |
| 主力 | **Sonnet 5**（$3/$15，08-31 前 $2/$10） | **gpt-5.6-terra**（$2.5/$15） | everyday work，执行主力 |
| 轻档 | **Haiku 4.5** | **gpt-5.6-luna**（$1/$6） | 批量机械/提取/预处理 |

- **GPT-5.6 = 有限预览**（少量受邀组织，无公开申请入口/GA 日期；本账号 Codex 已可用，CLI ≥0.144）。三型号：~105 万 ctx / 128K 输出 / 截止 2026-02；effort `low→ultra` 六档（**luna 无 ultra**）；`ultra`≈多智能体并行（消耗大）；另有 fast 速度档（1.5x 速度多耗额度）。5.5/5.4/5.4-mini 仍可用（5.4-mini 交叉测试交接单不作废）。
- **通道**：Claude 侧=主控会话 + Agent 子代理（`model` 参数 sonnet/opus/haiku）；GPT 侧=MCP `mcp__codex__codex` / CLI `codex exec`。

## 2. 角色分工矩阵（用户 2026-07-10 拍；**2026-07-12 用户重梳为四档对位阶梯**）

**四档对位阶梯（2026-07-12 用户拍 + 同日补充修订，当前唯一口径）**：

| 档位 | Claude 侧 ↔ GPT 侧 | 职责 |
|---|---|---|
| **最高档** | **Fable 5 ↔ sol** | 规划/方向 + 方案审 |
| **次高档** | **Opus 4.8 ↔ sol** | 出工程方案/细稿 + 执行审 |
| **中档** | **Sonnet 5 ↔ terra** | 执行（按 spec 改码+跑测） |
| **低档** | **Haiku 4.5 ↔ luna** | 批量机械/提取/预处理 |

**审一律比产出高一档（07-12 用户补充）**：
- **规划**（Fable 在场期）：GPT 家族暂无对标 Fable 的档 → **规划一律 Fable 出、sol 对抗审**。
- **工程细稿**：次高档出（Opus 或 sol；细稿不占 Fable，主控不亲手出稿）→ **审交最高档 Fable/sol 交叉**（Claude 侧稿→sol 审，GPT 侧稿→Fable 审）。
- **执行**：中档 Sonnet/terra → **执行审交次高档 Opus/sol 交叉**（GPT 执行→Opus 审，Claude 执行→sol 审）+ 主控大节点自跑全量与逐行 diff。

**Fable 退场后**（届时两家族档位对齐，顶档配对 Opus↔sol）：
- 规划 = **双独立出案**（Opus 与 sol 互不可见）→ **主控综合**（主控默认 Claude 家族；新启会话，不继承任一初稿上下文；综合稿视为 Claude 侧产物）→ **对抗审 = sol 新启会话**（不继承其初稿上下文）。（07-12 用户确认：综合方=主控。）
- 工程细稿审的 Claude 侧审员由 Fable 顺移为 Opus；其余对位不变。

**排工拍板制（07-12 用户定，硬流程）**：主控**每次排工前出一张派工表**（任务 × 执行/出稿者 × 审者 × 档位/effort）交用户拍板后才派；用户按两家族窗口额度调整工作量分配。中途续同一循环的返工/补强不必重拍，新批次必须上表。

- 主控（开对话）恒 Claude 家族（现 Fable→退场后 Opus）：编排/裁决/judge/memory+管理文档/commit，**不亲手改 src、不亲手出细稿**。
- 疑难杂症（连续修复失败/跨系统边界/并发一致性/高错误代价）：交叉最顶档。

**四条原则（用户拍）**：
1. **谁写谁不批**——跨厂商交叉评审是必须不是可选；批准者只看**原始需求 + diff + 测试输出 + 必要架构上下文**，不看执行者长篇自述（防叙事带偏）。
2. **推理强度不写死**——主控按任务需求动态定；「最顶」= 该模型最高两档（max/ultra），选哪档也归主控。
3. **额度动态平衡**——不预设偏烧哪边；**派批次活前看两边窗口余量、问用户拍额度侧**（免得老撞顶等重置）。规划/方向与方案评审**保质量不降档**，其余角色可按额度换侧/降档。
4. **主控家族恒 Claude**——memory + 管理文档 + commit 单一权威不动摇（§7）。

## 3. 省上下文的四条机制（决定省得多不省）

1. **不在 prompt 里塞大文件**——给执行器文件路径，让它自己读盘；主控基本不亲自 Read 大文件。
2. **产出走磁盘**——执行器直接改工作树 + 详细日志/报告写文件；**回主对话只给简报**（X passed / 改了哪几个文件 / 关键结论 / 偏差 / **审阅需求**）。明确要求「Reply INLINE with ONLY a terse report, do NOT paste diffs/file contents」，且**简报必含「审阅需求(review-ask)」段**：执行器自报哪些处没把握 / 做了判断取舍 / 动了风险点或不变量、建议主控复核（无则注明「none — routine spec'd execution」），诚实标注不确定、不得过度自信。
3. **主控审 `git diff`**（自己跑，便宜），不让执行器回贴文件内容。
4. **多步迭代续同一 session**——GPT 侧用 `codex-reply`（context 留 Codex 侧）；Claude 侧用 SendMessage 续子代理。

## 4. 通道与参数

- **MCP `mcp__codex__codex` / `mcp__codex__codex-reply`**（主力）：session 持久（`threadId` 续），适合「写代码+跑测」多步执行 + 方案审阅。
- **CLI `codex exec -i <图>`**（看图专用）：MCP 无图像参数，识图/读平面立面必须走 CLI；大输出 redirect 到文件读 tail；坑① 后台进程 stdin 不 EOF 致 codex 死等干耗，用 `echo "" | codex …` 喂 EOF；坑② `-i` 是可变参数会吞尾随位置 prompt → prompt 走 stdin。
- **⚠️ 调用必须显式传 model + effort**：`~/.codex/config.toml` **已不钉模型默认**（只剩 trust_level），裸调用会落 CLI 内置默认 = **sol + low**（旗舰最低档，不伦不类）——**禁止裸调用**。MCP 经 `config={"model":"gpt-5.6-…","model_reasoning_effort":"…"}`；CLI 经 `-m <model> -c model_reasoning_effort=<effort>`。
- **Claude 侧执行器** = Agent 工具 `model` 参数（sonnet/haiku/opus）；隔离读图一律走 `spawn_isolated_reader.py`（污染硬隔离，new_case_guide 附录 A）。

## 5. 本机沙箱校准（硬坑，2026-06-21 实测）+ sol 执行护栏

- **read-only / workspace-write 两档不可用**：会去起 bwrap 沙箱，本机内核禁 userns 起不来，于是**静默回退去读 GitHub @main**（行号是远端、与本地分支不一致、不可信）。
  → **凡需碰本地文件的 Codex MCP 调用，一律 `sandbox=danger-full-access`**（跳过沙箱、不走 bwrap）。
- **sandbox 在建 thread 时定死**：`codex-reply` 续会话不能改 sandbox。想换权限 → 新开 `codex` 会话。
- **⚠️ CLI `codex exec resume` 不继承原会话 sandbox（2026-07-10 实测）**：resume 会**静默落回 workspace-write**（= 走 bwrap，本机即踩上面的静默回退坑），且**不吃 `--sandbox` 旗**（报 unexpected argument）——resume 续会话必须带 **`--dangerously-bypass-approvals-and-sandbox`**；发射后 **`grep sandbox <exec log>` 核实生效**再走开。
- 全自主执行：`approval-policy=never`（不打断），靠主控审 diff 兜底。
- **⚠️ sol 执行护栏（系统卡风险）**：sol 相比 5.5 在 agentic coding 中更易**过度追求目标**（替换用户指定资源/声称完成未验证工作等，绝对率低但需防护）。故 **sol 原则上不当执行器**（矩阵已排 terra/Sonnet）；确需 sol 执行（疑难终端任务）时三条硬护栏：① 删除/覆盖/推送/外发必须单独授权 ② 每阶段给可验证证据（测试输出/diff/实际状态）③ 限单次变更范围，完成一个工作包重新审视计划。

## 6. 审阅流程与信任边界

```
主控出方案（规划档参与，见 §2）
  → 交叉最顶对抗审（落 logs/reviews/verdict/）→ 主控裁决（不盲从）
  → 派执行档实现（简报含「审阅需求」自报需复核处）
  → routine 采信简报；大节点 → 交叉中档复核 + 主控全面审 → 主控 commit
```

- **执行结果不逐次全审**：把执行器当**可靠执行工具**，由它在「审阅需求」里自决哪些要 escalate；主控只复核被 escalate 的处（逐次全审抵消省消耗初衷）。
- **大节点才全面审**：里程碑 commit 前实质改动、集成接缝、碰 5 条铁律/IntakeOutput 契约、或执行器报不确定 → 交叉中档复核 + 主控全面审（自跑 pytest + 逐行 diff + 端到端回归）。
- **方案类决策双审后再派**：主控拟方案 + 交叉最顶审 + 主控裁决，无 BLOCKER 才 dispatch。
- **双独立规划**（Fable 退场后）：Opus 与 sol **各自独立**出方案（互不可见对方产出）→ 新开 Opus 复核会话统一 → 主控采纳；沿用「不与之并行自查以保独立性」纪律。
- **判断题仍主控自持**（便宜且是质量命门，不外包）：① 方案地基事实（根因定位、不变量）动方案前主控亲自聚焦 read 确认；② 评审给 REWORK/critique 时逐条裁决（采纳/校准/反驳），不照单全收。
- **审计留痕**：`logs/reviews/request/<date>_<topic>_request.md` = 方案（含 revise 演进）；`logs/reviews/verdict/<date>_<topic>_review.md` = 评审（含二审）；多轮 revise 用 `codex-reply`/SendMessage 续同会话。

## 7. 守质量 + 记忆一致的铁律

- **memory + 管理文档只主控写**（CLAUDE.md §5#1）→ 执行器/评审器永不碰，杜绝「各自记忆不同步」。
- **git commit 只主控**（§5#7）；执行器改工作树**绝不** commit/push。
- **改 src 前主控先备份**（§5#4，`backup/src_history/<date>_<reason>/`），git clean 之外再加一层。
- 执行器只做**已 spec 清楚的执行**，不做开放式设计；碰铁律/契约/judge verdict 的判断题留主控。

## 8. 一轮完整范例（P0#1 跨层墙对齐，2026-06-21，两方模式旧例、流程骨架仍适用）

1. Claude 兜底读 `deterministic.py` 核实根因 → 写方案落 `request/`。
2. Codex full-access 审方案 → REWORK（3 DISAGREE + 2 BLOCKER，落 `verdict/`）。
3. Claude 裁决采纳 + 校准 → v2.1 spec；`codex-reply` 二审 → APPROVE-WITH-CHANGES 无 BLOCKER。
4. Claude 备份 src → 派执行器实现 → 回简报 281 passed。
5. Claude 自验：审 diff 逐行 + 自跑 pytest + 读新测非空 + sm21 端到端 112→100。
6. Claude 同步 plan/decision_log/memory + commit。

（新矩阵下的对应替换：步骤 2 评审 = 交叉最顶 sol+max/ultra；步骤 4 执行 = terra/Sonnet medium-high；大节点另加交叉中档复核。首个新矩阵实测 = C2 收官设计首审，见 plan.md。）
