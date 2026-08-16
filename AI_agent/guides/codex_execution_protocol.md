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

## 8. 一轮完整范例（P0#1 跨层墙对齐，2026-06-21，两方模式旧例、流程骨架仍适用）

1. Claude 兜底读 `deterministic.py` 核实根因 → 写方案落 `request/`。
2. Codex full-access 审方案 → REWORK（3 DISAGREE + 2 BLOCKER，落 `verdict/`）。
3. Claude 裁决采纳 + 校准 → v2.1 spec；`codex-reply` 二审 → APPROVE-WITH-CHANGES 无 BLOCKER。
4. Claude 备份 src → 派执行器实现 → 回简报 281 passed。
5. Claude 自验：审 diff 逐行 + 自跑 pytest + 读新测非空 + sm21 端到端 112→100。
6. Claude 同步 plan/decision_log/memory + commit。

（新矩阵下的对应替换：步骤 2 评审 = 交叉最顶 sol+max/ultra；步骤 4 执行 = terra/Sonnet medium-high；大节点另加交叉中档复核。首个新矩阵实测 = C2 收官设计首审，见 plan.md。）
