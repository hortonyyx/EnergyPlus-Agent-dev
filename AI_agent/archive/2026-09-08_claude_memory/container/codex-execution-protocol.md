---
name: codex-execution-protocol
description: 多模型家族协作规约（2026-07-10 GPT-5.6 轮大修订；07-21 起四家族见 [[glm-family-onboarding]]）——角色矩阵/交叉评审/额度动态/本机沙箱硬坑
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 183c412a-7147-435c-ae81-fa759354fb61
  modified: 2026-08-16T08:12:00.466Z
---

**⚠️⚠️⚠️ 2026-07-16 用户拍板主控降档（最新口径，详 [[opus-controller-fable-spot]]）**：主控=**Opus 4.8**(开会话即 Opus,整场不切);Fable 在场期降三类点射(规划出稿+sol 对抗审/细稿最高档交叉审/大节点复核·疑难会诊);「Fable 退场后双独立出案→综合」预埋不启用;四档对位与审阶梯不变。下文所有"主控现 Fable"表述按此更正。**主控同款可经子代理审(2026-07-16 用户澄清,已落 guide §2)**:「主控不亲手审」=保主对话上下文干净,不禁用主控同款——GPT 侧执行(terra)的次高档 Claude 审=Opus,正解=起 **Opus 子代理**审(独立上下文、只回传 findings 摘要),非主控主上下文亲手审(=方案A)。**预算注记**:terra 施工→审阶梯必绑 Opus、省不掉 Opus 预算(B4a Phase C 实战撞一次 Opus 会话限额);Opus 紧时「Sonnet 施工+sol 审」审落 GPT 侧基本不吃 Opus 更稳。

**⚠️⚠️ 2026-07-12 用户重梳四档对位阶梯+同日补充（落 guide §2+CLAUDE §5#8）**：四档=Fable↔sol/Opus↔sol/Sonnet↔terra/Haiku↔luna。**审一律高产出一档**：规划(Fable 在场期)=恒 Fable 出·sol 对抗审(GPT 暂无对标 Fable 档);工程细稿=次高档出(Opus/sol,不占 Fable!主控不亲手出稿)→最高档 Fable/sol 交叉审(Claude 稿→sol,GPT 稿→Fable);执行=中档→执行审 Opus/sol 交叉(GPT 执行→Opus,Claude 执行→sol)+主控大节点。**Fable 退场后**:规划=双独立出案(互不可见)→**新启**会话综合(综合稿视为综合方家族产物)→**另一家族新启**对抗审,两边均不继承初稿上下文;细稿审 Claude 侧审员 Fable→Opus 顺移。**排工拍板制(硬流程)**:每次排工先出派工表(任务×执行者×审者×档位)交用户拍板再派;返工续同循环免重拍;按两家族窗口额度调工作量。额度侧按轮拍。

**⚠️ 2026-07-21 起为四家族**（Claude/GPT/**GLM**/DeepSeek）：GLM=执行档主力+次高档备用（只做复核、一般不单独出稿）；派工表须含 GLM、仍用户拍板再放。**⭐ 2026-08-16 用户改两处**：GLM 席位默认升 `glm-5.3`（定级不动，5.3 我方零实测）· **DeepSeek 不再「退出日常开发选项」，已加 `scripts/deepseek_code.sh` 席位**（⛔ 按量扣余额且与管线共用，长批次前查余额）。详 [[glm-family-onboarding]]；家族版图权威表 = `AI_agent/guides/codex_execution_protocol.md` §1。

**⚠️ 2026-07-10 大修订（用户拍，替代下文两方模式的分工/档位部分；机制类段落仍有效）**：GPT-5.6 家族有限预览到账（sol 旗舰 $5/$30 / terra 主力 $2.5/$15 / luna 轻档 $1/$6；effort 到 ultra≈多智能体，luna 无 ultra）+ **Fable 5 订阅 2026-07-12 到期退场**。新分工=**完整双模型家族角色矩阵**（详 `AI_agent/guides/codex_execution_protocol.md` §2 + CLAUDE §5#8）：主控恒 Claude（现 Fable→07-12 后 Opus4.8）；规划=Fable5→退场后 Opus+sol 双独立出案→新 Opus 复核统一；工程推理=Opus/sol；执行=Sonnet5/terra；批量机械=Haiku/luna；**方案评审=交叉最顶**（Claude 产物→sol，GPT 产物→Fable/Opus，effort=最高两档 max/ultra 主控择一）；**大节点复核=交叉中档**（Claude 执行→terra，GPT 执行→Opus）；疑难杂症=交叉最顶。**原则**：谁写谁不批（跨厂商交叉必须）；强度不写死主控按任务定；**额度侧派批次活前问用户拍**（规划/方案评审保质量不受额度约束）；批准者只看需求+diff+测试输出。**操作坑**：`~/.codex/config.toml` 已无模型默认→**裸调用落 sol+low，禁止，必显式传 model+effort**；sol 系统卡有过度追求目标风险→原则上不当执行器，确需时三护栏（单独授权/可验证证据/限变更范围）。首个矩阵实测=C2 收官设计首审（sol+max）。**⚠️07-10 用户当日提醒「现在开始都按新分工做,别再全自己干了」**(语境:E4 探针我亲手跑了 EP+写解析器):**探针/实验类的执行(跑命令/解析/对账)也要派执行档**,主控只出 spec+裁决;「地基事实亲核」例外收窄为聚焦 read 代码/文档,不含跑实验。

——以下为 2026-06-21 确立的两方模式原文（机制/沙箱坑仍有效，分工档位以上文为准）——**Why**: 用户有 Claude+Codex 两订阅各 5h 窗口；坚持 Claude 主控（保质量+记忆单一权威），但执行尽量派 Codex——推理算 Codex 额度，Claude 只花「写 spec+审 diff+读简报」，省上下文 + 拉长每周期可开发时间。**How to apply**: 每个执行类任务默认考虑派 Codex。

**分工**：Claude=方案/拆解/审 git diff/judge②/memory+管理文档/碰铁律契约的判断题/git commit；Codex=按 spec 改码+跑测/探索式读码回 digest/CLI 看图/per-stage 跑。派不派、派哪模型/sandbox 主控动态定（目标=保质量+减 Claude 消耗，非定死）。

**省上下文四机制**：①不在 prompt 塞大文件、给路径让 Codex 自己读；②产出走磁盘、回主对话只给简报（明令 do NOT paste diffs）；③Claude 审 git diff 不让 Codex 回贴；④`codex-reply` 续 session 省重发 context。

**审阅方向（反转旧 §5#8）**：Claude 出方案 → Codex 审方案（落 logs/review/）→ Claude 裁决（**不盲从**，逐条采纳/校准/反驳）→ 派 Codex 执行器 → **Claude 不逐次全审**：把 Codex 当可靠执行工具，执行简报必含「审阅需求(review-ask)」段由 Codex 自报需复核处，Claude 只核 escalate 的、**大节点才全面审**（自跑 pytest+逐行 diff+端到端回归）。方案类决策**双审**后再派。判断题（方案地基事实、裁决 Codex critique）仍 Claude 自持。**Why 补充**：逐次全审会抵消省消耗初衷（2026-06-21 用户校准）。**⚠️ Anti-pattern（2026-06-25 用户纠正「你怎么忘 codex 协作机制了」）**：skill 脚手架恢复这种**方案+执行**节点，我直接自己从头编辑到尾、既没派 Codex 审方案也没派 Codex 执行，白烧 Claude 上下文。**教训=动手改 skill/方案类前先停一拍自检「这该不该走 Codex」**；真忘了、木已成舟时至少补「派 Codex 审已落 diff」（本次补救：xhigh 审 → APPROVE-WITH-CHANGES、5 findings 全采纳，含 Codex linter probe 实测坐实的 `dimensions[]` 示例链不闭合 bug + kickoff 二次 durable 副本漂移风险）。**⚠️⚠️ 2026-06-27 重犯（第二次）**：reading 冲突修法,已"出方案+用户 ratify"后我**又自己把 7 文件全改、只把 Codex 当事后审**——用户纠正「出了方案≠可以自己执行」,工作回滚。**教训固化进 CLAUDE.md §5#8 硬默认**（实质改动一律 Claude 出方案→Codex 审→Codex 执行→Claude 复核;Claude 亲手只做方案/审/judge/memory+管理文档/commit）。**同 session 后半段做对了的模板**：reading 脚手架完整恢复 = Claude 出方案(提案 doc)→Codex xhigh 审方案(APPROVE-WITH-CHANGES)→Claude 裁决全采纳→Codex high 执行(backup+改码+测+审阅需求)→Claude 大节点全面审(自跑 pytest 349/9 + 逐行 diff 代码门 + 排除项 guardrail)→commit。独立审计(全 0-5 迁移)也派 Codex、Claude 不并行自查保独立。

**本机沙箱硬坑（实测）**：Codex MCP 碰本地文件**必须 `sandbox=danger-full-access`**——read-only/workspace-write 起 bwrap 失败（内核禁 userns）→**静默回退读 GitHub @main**（行号不可信）。sandbox 建 thread 时定死、`codex-reply` 改不了→换权限须新开 `codex` 会话。看图走 CLI `codex exec -i`（MCP 无图参数，`echo ""|` 喂 EOF 防死等）。默认 `~/.codex/config.toml` = gpt-5.5/xhigh、本项目 trusted。**effort 按角色分档（2026-06-23 用户改，替代旧「宜高不宜低」）**：方案审阅 `xhigh`；执行 `medium`/`high` 由主控按任务复杂度定、**默认不再 xhigh**；per-call 降档经 MCP `config={"model_reasoning_effort":"medium"|"high"}` 覆盖 config.toml 的 xhigh 默认（codex MCP 有 `model` 参数，effort 只能经 `config` 覆盖）。

**铁律**：memory+管理文档只 Claude 写（Codex 永不碰，杜绝记忆不同步）；commit 只 Claude；改 src 先备份。

详版操作手册 `AI_agent/guides/codex_execution_protocol.md` + CLAUDE.md §5#8。范例=P0#1 跨层墙对齐（见 [[sm21-dualmodel-backlog]]）。
