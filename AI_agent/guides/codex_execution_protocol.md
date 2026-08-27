# 双模型家族协作规约（主控编排 / 分档执行 / 交叉评审）

> **目的**：用户有 Claude + Codex(GPT) 两个订阅、各自 5h 重置窗口。**主控恒为 Claude 家族开对话模型**（保质量 + memory 单一权威），
> 其余角色按「角色 × 档位」矩阵在两家族间分派；**跨厂商交叉评审 = 质量核心机制（谁写谁不批）**。
> 本文 = 操作手册；核心约定同时收录在 [../CLAUDE.md](../CLAUDE.md) §5#8/#10。换主控模型读此接手。
> **2026-07-10 修订**：GPT-5.6 家族发布（有限预览）+ Fable 5 订阅 07-12 到期 → 从「Claude 编排 / Codex 执行」两方模式升级为**完整双模型家族分工**（用户 2026-07-10 拍）。文件名沿用 `codex_execution_protocol.md` 保链接稳定。

## 1. 家族版图（**2026-08-16 全量核对，下表 = 当前唯一在册口径**）

| 档位 | Claude 家族 | GPT 家族（Codex 通道） | GLM 家族 | DeepSeek 家族 | 说明 |
|---|---|---|---|---|---|
| 旗舰 | **Fable 5**（2026-07-16 起不任主控、降为点射；退场后顶位由 **Opus 4.8** 顺移） | **gpt-5.6-sol**（$5/$30） | **glm-5.3**（08-13 发布，**08-16 起席位默认**） | **deepseek-v4-pro**（08-13 GA） | sol=长程 agent；Opus=工程秩序；glm-5.3=编程/长程 agent |
| 主力 | **Sonnet 5**（$3/$15，08-31 前 $2/$10） | **gpt-5.6-terra**（$2.5/$15） | 同上（GLM 单档，无独立主力位） | **deepseek-v4-flash**（07-31 GA） | everyday work，执行主力 |
| 轻档 | **Haiku 4.5** | **gpt-5.6-luna**（$1/$6） | — | 同上 | 批量机械/提取/预处理 |
| 视觉 | 主控/子代理原生多模态 | CLI `codex exec -i` | **glm-5v-turbo**（200K，识图实验臂唯一候选） | — | GLM 无 5.3v；`glm-4.6v` 已出局（把毫米标注当像素） |

**计费性质（决定能不能随便派长批次）**：Claude / GPT / GLM = **订阅制 5h 窗口**；**DeepSeek = 按量扣账户余额**，
和管线（`src/configs/llm.yaml` 的 1_correction / 4_mep / 9 subagent）**共用同一个余额** ⇒ 席位烧穿余额会**连带打断 e2e**。
派长批次前查：`curl -s https://api.deepseek.com/user/balance -H "Authorization: Bearer $DEEPSEEK_API_KEY"`。
DeepSeek 峰谷计价（谷价=峰价一半，2026-08-16 16:00 UTC 起）⇒ 长批次排谷时段；GLM 高峰 14:00–18:00 (UTC+8) 3x 扣。

- **GPT-5.6 = 有限预览**（少量受邀组织，无公开申请入口/GA 日期；本账号 Codex 已可用，CLI ≥0.144）。三型号：~105 万 ctx / 128K 输出 / 截止 2026-02；effort `low→ultra` 六档（**luna 无 ultra**）；`ultra`≈多智能体并行（消耗大）；另有 fast 速度档（1.5x 速度多耗额度）。5.5/5.4/5.4-mini 仍可用（5.4-mini 交叉测试交接单不作废）。
- **GLM-5.3（08-16 实测 + 官方文档核对）**：1M ctx / 128K 输出；**thinking 强制常开**——`thinking.type:"disabled"` 接口收下但**静默忽略**（实测仍计 `reasoning_tokens`），`reasoning_effort` 默认 `max`（`low|high|max` 三档）。同基座纯后训练，官方称内部 Code Bench 较 5.2 **+50%**、Terminal-Bench 3.0 4.6→28.3、DeepSWE 46.2→66.9，且平均输出 token 更省（~50K vs Opus 4.8 ~120K）。**⚠️ 我方零实测**：07-21 那份「验证性审阅=Fable 级 / 探索性审阅=不及格」的能力画像是 **5.2 的**，未迁移到 5.3；档位定级沿用 5.2 那套，直到实战暴露差异。
- **DeepSeek V4 GA（08-16 核对）**：`/models` 只列 `deepseek-v4-pro` / `deepseek-v4-flash` 两个 id ⇒ **转正没换 id、旧 key 直接落 GA**，preview 名已被接口拒绝（`-preview` 报 invalid_request_error）。**⛔ 陷阱**：旧别名 `deepseek-chat` / `deepseek-reasoner` 现在**静默解析到 v4-flash**（不是 pro）⇒ 任何地方都别再写这两个名字。`reasoning_effort` = `low|high|max`（`xhigh` 也收）。
- **通道**：Claude 侧=主控会话 + Agent 子代理（`model` 参数 sonnet/opus/haiku）；GPT 侧=MCP `mcp__codex__codex` / CLI `codex exec`；
  **GLM 席位**=[`scripts/glm_code.sh`](../../scripts/glm_code.sh)；**DeepSeek 席位**=[`scripts/deepseek_code.sh`](../../scripts/deepseek_code.sh)（08-16 新增）。
  两个席位启动器**凭据只注入子进程**——全局导出 `ANTHROPIC_BASE_URL` 会静默劫持主控 Claude Code 会话。
- **⚠️ 席位里的 `total_cost_usd` 不可信**：Claude Code 用 Anthropic 价目表估算，套到 GLM/DeepSeek 上是**假数字**
  （08-16 实测：一句 "reply OK" 报 $0.14）。真实消耗看 DeepSeek 余额接口 / GLM 订阅窗口，不看这个字段。
  同理 `contextWindow` 客户端一律按 200K 报（GLM-5.3 实际 1M）。

### 1.1 ⭐ 席位路由（2026-08-24 用户令，当前有效）

> 用户原话：「**审优先换 GLM 侧，如果还需要三方先用 DeepSeek，GPT 有点告急了。**」

- **跨家族审 = GLM 家族**（`scripts/glm_code.sh`，默认 glm-5.3）。⛔ 这条线上不再默认派 GPT/sol。
- **需要第三方意见时 = DeepSeek**（`scripts/deepseek_code.sh`）。
  ⚠️ 仍受 §1 那条约束：DeepSeek **按量扣余额、与管线共用**，派长批次前先查余额。
- **⚠️ GLM 席位是 5 小时窗口**：2026-08-24 实测，连打三轮审（四/五/六审）之后
  在写完最后一份裁决时撞到上限（提示「已达到 5 小时的使用上限」，配额 07:10 重置）。
  ⇒ **一轮审 ≈ 一个大额度块**；连轴排三轮以上要预留重置时间。
- **实战记录（2026-08-24）**：GLM 连做三轮对抗审，每轮都给出**可复现命令 + 实测数字**、
  且**每轮都独立复验上一轮的修**（不信送审方的 RESULTS，直接对夹具重跑），
  第五轮造出「产物里没有一个假数却优于诚实产物」的作弊。
  ⇒ 07-21 那份「GLM 探索性审阅不及格」的画像是 **5.2 的**，**5.3 在对抗审上的实战表现与之不符**，
  按本条记录更新使用口径。

## 2. 角色分工矩阵（用户 2026-07-10 拍；**2026-07-12 用户重梳为四档对位阶梯**；**2026-07-16 主控降档**）

**2026-07-16 用户拍板（主控降档，Fable 在场期新口径）**：
- **主控 = Opus 4.8**（开会话即 Opus、**整场不切模型**——同会话中途切模型会把已写缓存全部作废；跨 5h 窗缓存本就过期〔TTL≤1h〕，故切主控本身无缓存税）。主控职责清单不变（编排/裁决/judge/memory+管理文档/commit，不亲手改 src、不亲手出细稿）。
- **Fable 5 在场期收敛为三类点射**（Agent 子代理 `model: fable` 或独立短会话，喂精简 brief）：①**规划/方案出稿**（维持「规划一律 Fable 出、sol 对抗审」）②**工程细稿最高档交叉审**（不变）③**大节点复核 / 疑难会诊**。
- **「Fable 退场后双独立出案→综合」路径预埋不启用**（07-16 用户确认：Fable 未退场前不走）。
- 排工拍板制 / 谁写谁不批 / 审升一档全部不变。动因=Fable 主控烧 5h 窗太快+撞 Fable 单独限额；Opus 单价≈Fable 一半→单窗可开发量↑。**试点**：B4a Phase C = Opus 主控首战，收工复盘三指标（主控裁决漏检 vs 升一档审 findings / 返工率 / 单窗完成量）后固化。

**四档对位阶梯（2026-07-12 用户拍 + 同日补充修订，当前唯一口径）**：

| 档位 | Claude 侧 ↔ GPT 侧 | 职责 |
|---|---|---|
| **最高档** | **Fable 5 ↔ sol** | 规划/方向 + 方案审 |
| **次高档** | **Opus 4.8 ↔ sol** | 出工程方案/细稿 + 执行审 |
| **中档** | **Sonnet 5 ↔ terra** | 执行（按 spec 改码+跑测） |
| **低档** | **Haiku 4.5 ↔ luna** | 批量机械/提取/预处理 |

**审一律比产出高一档（07-12 用户补充）**：
- **规划**（Fable 在场期）：GPT 家族暂无对标 Fable 的档 → **规划一律 Fable 出、sol 对抗审**（07-16 起 Fable 以点射子代理/独立短会话方式出稿，不任主控）。
- **工程细稿**：次高档出（Opus 或 sol；细稿不占 Fable，主控不亲手出稿）→ **审交最高档 Fable/sol 交叉**（Claude 侧稿→sol 审，GPT 侧稿→Fable 审）。
- **执行**：中档 Sonnet/terra → **执行审交次高档 Opus/sol 交叉**（GPT 执行→Opus 审，Claude 执行→sol 审）+ 主控大节点自跑全量与逐行 diff。
  - **⚠️ 2026-07-14 用户纠偏（硬口径）**：执行审**恒升一档、不许跳两档**——主控（最高档）不得亲手替代次高档执行审（B2b/B-O 返工轮违例：主控直接逐行终审 terra 施工，跳两档+烧最贵长上下文）；主控大节点=独立全量+抽查 diff+review-ask 裁决，是执行审**之外**的轻门、不是替代。07-11「方案A」（施工 terra、终审翻 Claude 侧、免中间审）收回为**额度应急预案**，启用须当轮用户明示。
  - **⚠️ 2026-07-16 用户澄清（主控切 Opus 后）**：「主控不亲手审」的义务 = **保主对话上下文干净**，**不等于**禁用主控同款模型审。GPT 侧执行（terra）的次高档 Claude 执行审 = Opus，与主控同款——正解 = **起一个 Opus 子代理审**（独立上下文、只回传 findings 摘要，主对话不被污染），而非主控在主上下文亲手逐行审（=方案A）。故 terra 施工 → Opus 子代理升一档审 → 主控轻门，合规。**预算注记**：terra 施工时审阶梯绑 Opus、省不掉 Opus 预算（B4a Phase C 实战撞过一次 Opus 会话限额）；若某轮 Opus 预算紧，**「Sonnet 施工 + sol 审」**把审阶梯落 GPT 侧、基本不吃 Opus，更稳——施工侧归属按当轮额度动态拍（§5#8 口径）。

**Fable 退场后**（届时两家族档位对齐，顶档配对 Opus↔sol；**07-16 用户确认此节为预埋条款、Fable 在场期不启用**）：
- 规划 = **双独立出案**（Opus 与 sol 互不可见）→ **主控综合**（主控默认 Claude 家族；新启会话，不继承任一初稿上下文；综合稿视为 Claude 侧产物）→ **对抗审 = sol 新启会话**（不继承其初稿上下文）。（07-12 用户确认：综合方=主控。）
- 工程细稿审的 Claude 侧审员由 Fable 顺移为 Opus；其余对位不变。

**排工拍板制（07-12 用户定，硬流程）**：主控**每次排工前出一张派工表**（任务 × 执行/出稿者 × 审者 × 档位/effort）交用户拍板后才派；用户按两家族窗口额度调整工作量分配。中途续同一循环的返工/补强不必重拍，新批次必须上表。

- 主控（开对话）恒 Claude 家族（**2026-07-16 起 = Opus 4.8**；Fable 在场期只点射、不任主控）：编排/裁决/judge/memory+管理文档/commit，**不亲手改 src、不亲手出细稿**。
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

## 7.5 跑测口径（2026-07-26 用户拍板 + 同日提速批落地）

**三档节奏**（用户 2026-07-26 定）：施工方**中间轮只跑受影响子集** / 施工方**交付前跑一次全仓**（原始输出进执行日志，是审阅方判零回归的唯一依据）/ **主控轻门独立全量 = 唯一权威门**（不削）。

**全仓默认并行**（`pyproject.toml` 的 `addopts = ["-n","auto","--dist","load"]`，依赖 `pytest-xdist`）：

```bash
python -m pytest -p no:cacheprovider -q            # 全仓，16 核 4.5–8 分钟（空机 ~4 分 20 秒）
python -m pytest -p no:cacheprovider -q -n0        # 串行，15–26 分钟；调试单测/看清 traceback 时用
```

- **调试单文件加 `-n0`**：起 16 个 worker 有约 6 秒固定开销，小文件串行更快（实测单文件 3s vs 9s）。
- **`--dist loadfile` 不要用**：会把 `test_gt_promotion_path.py` 那 25 格变异矩阵压到同一 worker，提速报废。
- **嵌套 pytest 必须钉 `-n0`**：全仓唯一一处在 `tests/test_gt_promotion_path.py`（子进程会继承父进程并行参数 → 25 格 × 16 worker 压死机器）。以后再写「子进程起 pytest」的测试同此。
- **并行安全铁律**：测试**不许**往仓库内固定路径写东西，也不许把仓库内固定文件喂给会在其目录旁建临时文件的外部程序（EnergyPlus 会在输入 idf 旁建 `in.idf`）——两个 worker 撞同一路径就随机爆。写外部程序的输入也要拷进 `tmp_path`。同理，**别用紧的 subprocess 超时**当断言（满载机器上启动慢是常态，`test_mcp_stdio` 的 10 秒就这么炸过 → 已放宽到 120 秒）。
- **并行↔串行等价的验收方式**（改动跑测基础设施时必做）：三份 `-q -rA` 输出（串行 1 次 + 并行 2 次）各抽 `^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED) <nodeid>` 排序去重，两两 `diff` 必须空。**只对计数不算过**。
- **验锁用的临时 neuter 只在 `/tmp` 副本里做**，不许在工作树里改了再还原：主控/审阅方随时可能在跑门，工作树一旦短暂处于被改状态，双方数字与 hash 就互相打脸（2026-07-26 提速批实际撞过一次时间窗）。

**「受影响子集」由工具算，不许自由裁量**：

```bash
python scripts/tool_scripts/affected_tests.py --changed <改动路径>...      # 常用
python scripts/tool_scripts/affected_tests.py --since <git-ref>            # 只看已提交范围，忽略工作树未提交改动
python scripts/tool_scripts/affected_tests.py --changed <路径> --explain    # 看每个测试是因哪条边被选中
```

- 首行 `SCOPE: FULL` / `SCOPE: SUBSET`，随后是可直接粘贴的 pytest 命令 + 一行**跑测声明**（执行日志里必须贴这行，声明你跑了哪些）。
- 映射 = 静态 AST import 边（含相对导入）+ **字符串路径边**（捕获 `subprocess` 调脚本这种无 import 的耦合）的传递闭包；一等公民 = `src/**`、`scripts/**`、`tests/**` 的 `.py` 加仓库根 top-level `*.py`。
- **fail-closed**：非 Python 路径 / 全仓触发器（`pyproject.toml`、`uv.lock`、`**/conftest.py`、`src/configs/**`、共享测试 helper、工具与规则表自身）/ 已删除文件 / 规则表坏掉 / 改动模块无覆盖测试 —— 一律回落 `SCOPE: FULL`。**过度选择安全、漏选不安全**，工具按这个方向设计。
- 规则表 `scripts/tool_scripts/affected_tests_rules.yaml` 里的 `uncovered_allowlist` = **诚实的未覆盖清单**（每条带理由），由 `tests/test_affected_tests_map.py` 双向卡死（实算未覆盖集合必须与清单严格相等）：新模块没测试就得进清单，模块有了测试就得出清单。
- **子集有多便宜，看改的是叶子还是枢纽**（2026-07-26 实测，共 93 个测试文件）：叶子模块很便宜（`judge/tarch_normalize.py` → 9 个、`tool_scripts/run_stage.py` → 6 个、`tool_scripts/cv_probe.py` → 3 个），但 `src/agent/**` 的枢纽接近全仓（`pipeline.py` → 85、`validator/schedules.py` → 86）。**根因不是工具保守过头**：`src/agent/__init__.py` 第一行就 `from src.agent.graph import build_graph`，于是 import 任何 `src.agent.*` 都会把整张图拉进来。要让枢纽子集真变小，得把那个包 `__init__` 改惰性（顺带能压掉每个测试的 import 开销）＝**登记跟进债，不在提速批范围**。另注：函数体内的 `import` 也算边（AST 不区分模块级/函数级）＝保守、宁多跑不漏跑。

## 6.5 ⭐⭐⭐ 派工单 / 复核单的四条模板条款（2026-08-27 实测立，⛔ 每条都有当天读数）

> 立此节的事实依据全在 [`../plan.md` 2026-08-27](../plan.md) 与
> [`../logs/reviews/verdict/2026-08-27_f97_rework2_glm_verdict.md`](../logs/reviews/verdict/2026-08-27_f97_rework2_glm_verdict.md)。

### ① 返工审必须写三格判据，⛔ 缺第三格等于没审

| 格 | 问的是 |
|---|---|
| ① 在**返工前**的 commit 上**复现得出** | 复现不出 ⇒ **上一轮判错了**，如实写 |
| ② 在**返工后**的 commit 上**复现不出** | —— |
| ③ ⭐ **换【同形】输入仍走不通** | **「这类缺陷」修好了没有** |

**实测**：08-27 F-97 返工审，①② **三条阻断全绿**，③（唯一新加的一格）**一次抓出全部 3 条**：
只修了半句 · 修法挪了个位置 · 前提本身不成立。
⇒ ⛔ **只做 ①② = 只验证「被举的那个例子修好了」。**
⭐ 第三格**同时下放给施工方**（自己先跑一轮）+ **复核方另换方向再找一轮**，两份都要。
⭐ **③ 要给方向、⛔ 不要给清单**（清单会被当穷举）：写「上一轮打的是 X 面，请换方向」+ 提示 + 「⛔ 只是提示」。

### ② 停下上报触发器必须**分层**

- **(a) 承重前提错 ⇒ 停**：错了则整件事方向作废 / 判据不再有意义。
- **(b) 外围事实错 ⇒ 记进「orchestrator 题面写错的地方」，然后【继续做】。**
- **判别问法：这条错如果成立，我还需不需要审这份 diff？需要 ⇒ 只记不停。**

**实测**：不分层的版本让一处「返工面里有 3 份还是 4 份 md」的计数错**空转两轮复核**；
改分层后**当天兑现两次**（GLM 一次、施工席位一次），**两处题面错零轮空转**。
⛔ 这条 2026-08-12 就写进过 memory，**没执行** ⇒ 现固化进模板。

### ③ 复核单必须明写「**本轮你没有维持一致的义务**」

**实测**：08-27 GLM 复审时**当场推翻了自己上一轮的逐字处方并写进裁决**
（施工方指出 fifo 挂死无 `except` 可捕、`RecursionError` 既非 `OSError` 亦非 `UnicodeDecodeError`
⇒ 照那条处方逐字做仍会崩），并交代**自己第一版探针被围栏伪影骗过**。
⇒ 复核方审自己上一轮的结论时，**默认压力是维持一致**；这句话是解除它的唯一手段。

### ④ ⛔⛔ 环境两条硬禁令 + 哨兵

- **⛔ 席位绝对不许跑 `pip install -e .` / `pip install .` / 任何写 `site-packages` 的命令** ——
  venv **全机器共享**，改它 = 把别的席位与主树一起拖下水。import 有问题一律 `python -m` / pytest 入口。
- ⭐ **权威全量必须带 `.pth` 前后哨兵**（跑前跑后各记一次哈希，**两次相同才算数**）；
  复核单加一条 **A8 哨兵判据**（开工前 + 交件前各读一次，变了即停下上报）。
- **实测**：`.pth` 曾被改指到某个 worktree、**正好穿过一次主树权威全量的窗口** ⇒ 那轮读数作废重跑。
  ⇒ 「全仓绿 = 树 + 启动器 + 这段时间」的**第四种假象：跑测【途中】启动器被第三方改掉**。

### ⑤ 发单前的**最后一个动作**固定为：重跑环境读数

`git -C <worktree> log --oneline -1` + `status --porcelain` + `cat <.pth>`，**逐字贴进 §〇**；
「交件时应是什么状态」写成**这份读数 + 你的裁决/报告文件**，⛔ 不写「只剩你的文件」这种把既有文件抹掉的说法。
**实测**：写单时量过、随后自己 `cp` 了一份请求单进去 ⇒ 那句「工作树干净」**被我自己作废**，空转一轮。

### ⑥ ⭐⭐ 判「席位死没死」只能按进程实体，⛔ 不看日志、⛔ 不 grep 脚本名

**2026-08-28 一次踩三个坑**（拉 GLM 出架构稿时）：

1. `bash scripts/glm_code.sh -p ...` 跑满 10 分钟、日志**只有一行启动 warning** ⇒ 我按 timeout 砍了它。
   ⛔ **它其实在正常工作** —— headless `-p` **只在整轮结束时输出**，中途日志必然是空的。
   ⇒ **日志空白不是「死了」，也不是「活着」，它什么都不是。**
2. 改用 `nohup ... &` 塞进工具调用，事后 `pgrep -af glm_code.sh` 没找到 ⇒ 判「没起来」，又重启一次。
   ⛔ **它活着** —— 进程名是 **`claude`**，不是脚本名。
   ⇒ 结果 **两个 GLM 会话跑同一份题**：踩 §7.5「同家族⛔ 不许并行两个」、烧双份额度、
   **且两边会抢写同一个输出文件**。
3. 正解 = 用**工具自带的后台机制**（跨轮次常驻、结束有通知），⛔ 别自己 `nohup &`。

**唯一可靠的点名法**（进程名全都叫 `claude`，只能按环境变量认家族）：

```bash
for p in $(ps -eo pid,comm | awk '$2=="claude"{print $1}'); do
  tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -q "bigmodel.cn" && echo "GLM 存活: $p"
done
```

⇒ **重启任何席位之前跑一次；重启之后再跑一次确认「恰好一个」。**
同族口径：判跑完看**产物 / 汇总行**，⛔ 不看退出码（§④）。

---

## 8. 一轮完整范例（P0#1 跨层墙对齐，2026-06-21，两方模式旧例、流程骨架仍适用）

1. Claude 兜底读 `deterministic.py` 核实根因 → 写方案落 `request/`。
2. Codex full-access 审方案 → REWORK（3 DISAGREE + 2 BLOCKER，落 `verdict/`）。
3. Claude 裁决采纳 + 校准 → v2.1 spec；`codex-reply` 二审 → APPROVE-WITH-CHANGES 无 BLOCKER。
4. Claude 备份 src → 派执行器实现 → 回简报 281 passed。
5. Claude 自验：审 diff 逐行 + 自跑 pytest + 读新测非空 + sm21 端到端 112→100。
6. Claude 同步 plan/decision_log/memory + commit。

（新矩阵下的对应替换：步骤 2 评审 = 交叉最顶 sol+max/ultra；步骤 4 执行 = terra/Sonnet medium-high；大节点另加交叉中档复核。首个新矩阵实测 = C2 收官设计首审，见 plan.md。）

---

## 2.1 历史条款与实犯记录（2026-08-18 从 CLAUDE.md §5#8 原样搬入）

> 搬家理由 = CLAUDE.md 是根文件，不该塞操作手册正文。本节**逐字未改**，含已失效条款（如 Fable 相关）以备溯源；
> **当前口径以本文 §1/§2 为准**，冲突处 §1/§2 胜。

8. **双模型家族分工（硬默认：主控别自己开干；2026-07-10 GPT-5.6 轮修订；⚠️2026-07-12 用户重梳四档对位阶梯为唯一口径+同日补充；**⚠️2026-07-16 用户拍板主控降档=主控切 Opus 4.8、Fable 在场期降点射，四档对位与审阶梯不变**，详 [guides/codex_execution_protocol.md](../guides/codex_execution_protocol.md) §2：最高档 Fable↔sol/次高档 Opus↔sol/中档 Sonnet↔terra/低档 Haiku↔luna；**审一律高产出一档**=规划〔Fable 在场期恒 Fable 出·sol 对抗审〕/细稿次高档出·最高档 Fable/sol 交叉审/执行中档·执行审 Opus/sol 交叉+主控大节点；细稿不占 Fable、主控不亲手出稿；Fable 退场后规划=双独立出案→**新启**会话综合〔综合稿=综合方家族产物〕→另一家族**新启**对抗审,两边均不继承初稿上下文（**⚠️2026-07-21 Fable 退订 ⇒ 本条正式启用**，最高档位 Claude 侧空缺、Opus 即顶档）；**排工拍板制：每次排工先出派工表交用户拍板再派,中途返工续循环免重拍**）**（操作手册 [guides/codex_execution_protocol.md](../guides/codex_execution_protocol.md)）：**主控 = Claude 家族开对话模型**（**2026-07-16 用户拍板起 = Opus 4.8**，开会话即 Opus、整场不切模型〔同会话中途切模型=已写缓存全作废〕；**Fable 5 在场期降为三类点射**：①规划/方案出稿〔子代理或独立短会话+精简 brief〕②工程细稿最高档交叉审〔不变〕③大节点复核/疑难会诊。动因=Fable 主控烧 5h 窗太快+撞 Fable 单独限额；缓存按「模型+前缀」隔离且 TTL≤1h、跨窗本就冷启→切主控无缓存税，Opus 单价≈Fable 一半→单窗可开发量↑），亲手只做：① 方案/规划 ② 审 diff/裁决 ③ judge ④ memory + 管理文档（`AI_agent/`）纯文字编辑 ⑤ `git add`/`commit`（唯一小例外：trivial 单点改且方案言明、或纯文档/计划编辑）。**凡实质改动（`src/`/`skills/`/`tests/`/MCP/下游）一律走角色矩阵**：方案（规划/方向档 = ~~Fable 在场期仍 Fable 出稿~~**Fable 2026-07-21 退订、条款失效**；**现行 = Opus 与 sol 跨家族双独立出案 → 综合 → 另一家族新启对抗审**〔07-21 正式启用；综合方按轮拍，可由主控综合，此时对抗审派非 Claude 家族〕）→ **交叉最顶对抗审**（Claude 侧产物→sol；GPT 侧产物→Fable/Opus；effort = 最高两档 max/ultra 主控择一）→ 主控裁决（不盲从）→ **派执行档实现**（Sonnet 5 子代理 / terra；批量机械活 Haiku/luna；简报含「审阅需求」）→ routine 采信、**大节点交叉中档复核**（Claude 侧执行→terra；GPT 侧执行→Opus）+ 主控全面审。**谁写谁不批**（跨厂商交叉是必须）；推理强度不写死、主控按任务定；**额度侧动态定**：派批次活前看两边窗口、问用户拍（规划/方向与方案评审保质量不受额度约束）；复核简报纪律 = 批准者只看原始需求+diff+测试输出，不看执行者长篇自述。独立审计/交叉核实同样交叉派发，主控只设 brief、不与之并行自查以保独立性。**⚠️ 2026-06-27 教训**：已「出方案 + 用户 ratify」后，Claude 仍自己把 reading 修法 7 个文件全改了、只把 Codex 当事后审稿 → 违反分工、已全部回滚重做。**「出了方案 ≠ 可以自己执行」**。**⚠️ 2026-07-11 第三犯，用户令强化**：B-M 首轮施工规矩派了 Sonnet，但交叉复核后的**两轮返工主控又亲手改码**（Fable 额度烧穿、中途被迫切号）→ 硬化条款：**返工轮 / 复核 findings 修复 / 探针·实验执行同属实质改动，一律派执行档**；主控「大节点全面审」= 审 diff + 自跑测试，**不含亲手修**；察觉自己在编辑 `src`/`tests`/`skills` 即违规信号——停手改派。额度侧属哪家按轮动态拍（例：2026-07-11 用户拍 GPT 侧频繁重置期间**施工优先派 terra、终审翻 Claude 侧**，谁写谁不批方向随之反转）。
   **⚠️ 2026-07-21 用户拍板：GLM 家族接入 ⇒ 四家族**（Claude / GPT / **GLM** / DeepSeek）。
   - **GLM-5.2 = 执行档（施工）主力**；**可坐次高档备用位，但主要做复核类工作、一般不单独出稿**。
     依据 = 回溯测实测能力画像（[logs/experiments/2026-07-21_glm_capability_exam/](../logs/experiments/2026-07-21_glm_capability_exam/README.md)）：**验证性审阅**（给定 finding 清单、验锁真绑/防 false-lock）达 **Fable 级**（7/7 锁全 neuter、零漏判零误报、操作纪律满分）；**探索性审阅**（无线索处找未知缺陷）**不及格**（漏掉 Fable 当初靠活体探针抓的必崩缺陷、误判 APPROVE）。
     ⇒ **适合接「返工轮复核」**（验证施工者补的锁是否真绑目标门，如 Fable r2 那类任务），为最高档腾额度专攻首轮对抗审；**不得**替代首轮对抗审与规划出稿。
   - **派工表必须把 GLM 算进候选**（与 Claude/GPT 侧同列）；**仍是用户拍板再放**（排工拍板制不变）。
   - **运维**：一场深度对抗审 ≈ 烧穿一个 5 小时订阅窗口；高峰 14:00–18:00 (UTC+8) 额度 **3x** 扣、非高峰 2x（促销期至 2026-09 降 1x）⇒ **长批次避开下午**。席位启动器 [`scripts/glm_code.sh`](../../scripts/glm_code.sh)（凭据只注入子进程；**全局 `ANTHROPIC_BASE_URL` 会静默劫持主控会话**）。
   - **在册主力仅两个（2026-07-21 用户定）**：**`glm-5.2`（文本）+ `glm-5v-turbo`（多模态，200K）**；其余（`glm-5-turbo` / `glm-4.7` / `glm-4.5-air` / `glm-4.6v` / `glm-4.6v-flash`）**不专门指定即不用**——`glm_code.sh` 的 small/fast 槽位因此也默认 `glm-5.2`（省额度需 `GLM_SMALL_MODEL=glm-4.5-air` 当轮显式覆盖）。
   - **多模态仅 V 系**，主力 `glm-5.2` 是纯文本看不了图；识图实验臂唯一候选 = `glm-5v-turbo`（`glm-4.6v` 因把图纸毫米标注当像素坐标出局，且已不在册）。

---

## 9. Comate 内网模型网关（2026-08-18 从 CLAUDE.md §5#14 原样搬入）

14. **Comate 内网模型网关 = 「路线 3·人工中继」备用通道（2026-07-27 用户拍板登记，需要时才用）**：用户在公司 Comate 有近乎全量头部模型的调用权（**含 Fable 5** ⇒ 2026-07-21 起空缺的 Claude 侧最高档审阅位有回补可能）。
    - **接入实况（主控只读诊断）**：网关 = OneAPI 风格（`X-Oneapi-Request-Id` + APISIX），候选 base URL `https://oneapi-comate.baidu-int.com/v1`，四个路由（`/v1/models`·`/chat/completions`·`/messages`·`/responses`）在无 token 时均返回 OneAPI 统一鉴权错误 ⇒ **路由存在但协议实现未证**（尤其 `/v1/messages` 的多轮 `tool_use`/`tool_result` 往返）。**⛔ 当前 dev container 连不上该内网域名**（TLS 0.04s 即断；同环境 GitHub 200 / 智谱 401 正常 ⇒ 出网无碍，是内网可达性问题）。**⚠️ 诊断纪律**：本沙箱把**任何**域名（含不存在的）解析到递增假地址且都「连得上」⇒ **DNS/TCP 连通性测试在此环境下全是假阳性**，只能用「不带凭证的真实 HTTP 请求」判可达。
    - **数据流向（用户已知悉并接受用于非代码用途）**：多厂商网关**必须解密**才能路由与计费 ⇒ **公司网关是链路的一端、不是管道**，明文提示词对其可见且绑定工号；**agent 用法会把整个代码库增量上传**。公司政策鼓励用模型开发（合规无碍），但**课题组数据不出组**是另一层约束 ⇒ 未确认留存政策前**不走施工**。待确认三项：请求体是否落盘 / 留存期与查看权 / 是否二次用途。
    - **⇒ 当前口径 = 路线 3（人工中继）**：**只做不碰代码的活**（规划出稿、方案/细稿评审、算法思路、通用工程问题），由主控出**脱敏 prompt**（不含项目源码/文件树）→ 用户在 Comate 侧跑 → 结果贴回。**不接为 worker 席位**（施工仍走 Claude/GPT/GLM 现有席位）。技术路径若要升级为真席位，第一道坎是**网络可达**、第二道才是协议（多轮工具调用），详 [plan.md](../plan.md) 07-27 条。
