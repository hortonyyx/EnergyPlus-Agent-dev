# 整图优先指引包：质量回退诊断与恢复方案

Opus 5.5 受用户直接安排调查并解决“几轮开发后 agent 输出质量回退”。分支 `dev/opus-guidance-recovery-20260929`，基准 `6d4cbe5d`，未合入 main。诊断部分来自已有 run 的公开请求、工具记录、回执和既有评价。

## 最新状态（09-29）

- 用户批准“sm21 两次、串行”（[记录](approval.json)）。**run91 已执行**：只改系统提示与方法说明的指引包，**未恢复**行为和质量，详见下方“run91 结果”。按事先约定先停，同条件的第二次未执行。
- 用户批准对齐方案（[记录](approval_aligned.json)）。**run92** 在 658 秒遇 429（“monthly spend limit… session limit resets 1:10pm UTC”）中断，只存一层中间稿，质量未知，原样保留。CLI 带 `--no-session-persistence`，会话无法续接；用户同意重新开，[1 次极小文本探针](quota_probe_after_run92.json)确认额度恢复后，按完全相同条件重跑为 **run93**（[记录](approval_aligned_run93.json)，条件差异仅批次脚本的运行编号参数）。
- **run93 结果：墙体、房间关系、方向和外墙门窗恢复；室内门位置和南侧小窗高度仍错；出稿前仍以局部量测为主。** 详见下方“run93 结果”。
- 本包累计工作模型调用：run91、run92（中断）、run93 各 1 次主调用，另 1 次极小额度探针；无局部模型、续跑、自动重试或付费回退。CLI 估价 run91 5.51、run92 1.67 美元（非账单）。

## run93 结果（对齐方案，用户批准的重新开）

[运行目录](../2026-09-29_sm21_aligned_prompt_run93/) · [评价](../2026-09-29_sm21_aligned_prompt_run93/whole_drawing_evaluation.json)

实际 `claude-sonnet-5` / medium，1016.62 秒，1 次主调用，回执正常。

| 项目 | run93 | 好结果 run57/58 | 近期 run69–91 |
| --- | --- | --- | --- |
| 严格 2cm 分区 | **minor** | minor | 全部 severe |
| 房间对应 | 14/14，无拆并 | 14/14 | 4 次错并/漏房/单位错，2 次南北镜像 |
| 宿主 / 门连接 | 29/29 / 14/14 | 29/29 / 14/14 | 多次缺失 |
| 方向 | 两层均北朝上 | 正确 | run86/91 镜像 |
| 外墙门窗 | 17/17 对上，16 个位置/宽/高全在容差内（二层西窗端点偏 0.10m） | 全部 | 多次错位/错宽 |
| 原图位置 | 18/29 | 29/29 | 0–29 |
| 窗高 | 南侧小窗仍套常规 1.0–2.6m（应 1.5–2.1m） | 15/15 | 小窗/东窗多次套错 |
| 出首稿 | 第 891 秒，前 53 次调用（14 次裁图、28 次像素工具） | 120–260 秒，4–20 次 | 443–1012 秒 |

失败位置都在“按规律补齐”的对象上：一层 6 扇内门、二层南侧 4 扇门的依据写着“按门弧大致估计 / 与对面镜像”，二层中间两门被对称放在中间隔墙两侧，实际应在各自房间另一端，偏约 2.5m；南小窗套用常规窗高，尽管方法说明明确禁止。墙体靠像素剖面量得很准，门和例外窗没有逐个读。

判断：对齐用户提示后，方向错误和隔墙/房间错误在这一次消失，墙位精度回到好结果水平，这是 run69 以来最好的一次冷启动；但只有 1 次，不能说明稳定。“逐个对象读图”的问题没有解决，模型仍然量多、读少，出稿慢。

## run91 结果（用户批准，已执行）

## run91 结果（用户批准，已执行）

[运行目录](../2026-09-29_sm21_whole_drawing_run91/) · [评价](../2026-09-29_sm21_whole_drawing_run91/whole_drawing_evaluation.json) · [方向诊断](../2026-09-29_sm21_whole_drawing_run91/evaluation/orientation_diagnostic/scope.json)

实际 `claude-sonnet-5` / medium，CLI 2.1.284，1322.82 秒，1 次主调用，回执正常（returncode 0、无错误）。

| 项目 | 结果 |
| --- | --- |
| 行为 | 先读 reconstruction/plan_partition/plan_assembly，公开说明“先看全部整图”；但首稿前仍有 65 次调用（31 次裁图、22 次像素工具），首稿在第 1012 秒 |
| 正式成绩 | 2 层、14 空间/29 门窗/14 连接；原图位置 7/29、宿主 21/29、门连接 10/14；严格分区 severe；二层 4 条拆分/合并/缺失/多余 |
| 主要原因 | 两层都把“北外墙=0m、南外墙=8m”，即整栋南北镜像。一层南北对称只表现为位置/宿主错，二层北 2 南 4 不对称，才出现拆并 |
| 仅翻转方向诊断 | 宿主 29/29、门连接 14/14，两层房间一一对应：隔墙像素与 run58 基本相同，房间划分本身正确。位置仍只有 10/29 |
| 翻转之外的真实错误 | 一层 6 扇内门系统性偏 0.26–0.30m；一层南小窗偏 1.19m；二层南侧 4 门按等间距“补”出，偏约 1.1m；二层南窗照搬北窗范围再按隔墙切分，宽度错 |
| 看图方式 | 出稿前的局部裁图多是尺寸端点和 40 像素高的细长条，看不到门弧；run58 则用 2.2–2.5 倍、包含走廊两侧门弧的方框 |

判断：系统提示和方法说明被读到并部分采纳，但模型仍在执行用户提示里的两条方法性要求——入口代码追加的“Observe the real physical partitions before saving a quality-first candidate”，以及任务提示里的“scale from each plan's dimension annotations and their endpoints”。时间和注意力花在端点标定上，门窗靠规律补齐，方向还写反了。单次结果不证明稳定规律。

Y 方向写反在 53 次有平面草稿的历史运行中出现 5 次（GLM run32/35/36，Sonnet run86/91），模型自查发现不了：源回叠图使用它自己的标定，反着标也完全对齐。

## 对齐方案（run92，已离线准备，待用户重新批准）

与 run91 相比只改三处，系统提示和方法说明保持 run91 原样：

1. 入口代码对冷启动追加的句子改为“Read the whole drawings, then save a complete draft of every floor; inspect its actual feedback against the originals and revise substantive discrepancies.”（生产代码，影响之后所有冷启动）。
2. sm21 任务提示只替换一句：“…scale from each plan's dimension annotations and their endpoints” → “Establish one common XY origin with x east and y north for all floors, scaled from each plan's overall dimension annotations.” 见 [scope_sm21_aligned.json](scope_sm21_aligned.json)。
3. 每次提交平面返回的尺寸反馈里增加方向报告：若标定使北朝图纸下方或东朝左方，提示“平面可能被镜像，回叠无法发现，请核指北针/标注”。只提示、不拦截。对 151 份历史草稿，它恰好标出那 5 次翻转运行的 18 份草稿，其余 133 份无一误报。

离线核对：BIM 相关 16 个测试文件 151 项通过（含新增方向测试）；[预检](preflight_sm21_aligned.json) 0 调用，核实系统提示与 run91 相同、代码只差上述两个文件、用户提示只差上述两句。

拟运行：sm21 一次，同样 Sonnet 5 / medium / 3000 秒 / 24 候选 / 0 续查 / 禁委派；需要先写入 `approval_aligned.json` 才能启动：

```bash
python AI_agent/logs/experiments/2026-09-29_whole_drawing_guidance/batch_aligned.py run
```

判读：先看是否在大量局部量测前出完整首稿，再看质量（同上方主判据）。若仍走局部量测路线或质量未恢复，说明仅靠文字指引无法让当前模型回到旧做法，需要重新判断方向，不再同条件抽样。

## 结论（诊断）

回退的直接原因不是后加的几何/量测代码算错，而是 **工作模型从 09-27 凌晨起开始逐条执行我们写下的“局部量测方法”**；此前的全部好结果恰恰是在模型没有执行这套方法时取得的。

- 从 09-25 08:00 到 09-27 04:19 的 13 次 Sonnet 5 冷启动，任务提示都要求“Read reconstruction, plan_partition and plan_assembly”，模型 **13 次都只读了平面格式参考**，看完整图后 31–259 秒、4–20 次工具调用内出首稿，三个案例拓扑全部正确（sm21 两次 29/29）。
- 09-27 07:24 起的 15 次冷启动，同样的提示下 **13 次读了 reconstruction、15 次读了 plan_assembly**，首稿推迟到 443–849 秒、22–77 次工具调用之后；错并/漏房/单位错出现 4 次（run72/75/83/86），另 3 次额度中断。
- run81 用未改的旧生产树、与 run57/58 **逐字节相同的请求**，同样读了方法参考并出现同样的行为。因此触发不在我们的代码里，而在模型服务侧行为（遵从度）变化；但它暴露的是我们指引里一直存在、却从未在好结果中生效过的做法。
- 逐次数据见 [regime_evidence.json](regime_evidence.json)（由各 run 的 `agent_request.json`、`tools.jsonl`、`agent_receipt.json` 及既有 [质量报告](../2026-09-28_dimension_first_comparison/quality_report/report.json) 直接汇总）。

## 已排除的解释

| 解释 | 核查 | 结论 |
|---|---|---|
| 用户级 CLI 配置/技能/插件变化 | 启动带 `--setting-sources ""`、`--strict-mcp-config`、自定义系统提示和独立临时目录；run58 与 run81 的 init 事件（CLI 2.1.280、36 工具、技能/插件列表、输出风格）逐项相同 | 排除 |
| 服务端图像缩放/可见细节变化 | 同一步“看 1F+2F 两张整图”的上下文增量：run57 5897、run58 5897、run81 5911 token | 排除 |
| “medium”思考量变化 | 每次调用的思考 token：好结果 468–1862，之后 443–2676，无系统性变化；变化在调用次数（13–22 → 43–85） | 排除为主因 |
| 新代码算错/转换错误 | 旧树 run81 同样变坏；此前 19 份草稿跨版本编译一致；错误均在模型首份声明时进入 | 排除为触发因素 |

服务端到底改了什么无法从本地证实；修复不依赖这一点。

## 好做法与坏做法的实际差别

好结果（9 次，三案例）的共同顺序：列输入 → 读平面格式参考 → 看全部整图 → 每层一次性完整声明（按总尺寸标定、外墙取外皮、内隔墙取双线中线）→ 装配 → 对照立面确认窗高 → 抽查 1–2 处空间关系 → 交付。首份声明依据几乎一致：“Overall dims to outer faces; partitions at drawn double-line centres”。

变坏后：先读完三份参考，再在首稿前做 50–80 次局部裁图、刻度端点放大、像素剖面和区域填充；已证实的错误机制（Opus 09-28 调查与本次复核）：

1. 用局部像素判据否掉图上画出的隔墙（“无灰填/墙厚支撑弱”），造成 run75/83/86 错并；
2. 把裁图内坐标当原图坐标（run83：718 实为 1118）；
3. 墙面与中线混用、逐墙量厚导致位置漂移；
4. 窗高按常规窗族套用到小窗/东窗。

这些做法来自指引中早已存在、好结果时期被模型跳过的内容：任务提示和系统提示都要求读 `reconstruction`（逐刻度标定、双线两侧面分别量、每个接头放大）；系统提示写着“Prioritize … over an early first draft”，任务提示写着先观察再保存；对“拆分”有谨慎要求，对“漏墙”没有对称保护。09-27 之后每一轮新增提醒/反馈，也都被逐条执行，进一步拉长局部流程。

## 本包改动（只改 `scripts/tool_scripts/bim_agent_guidance.py`）

原则：让“完全照指引做”就等于好结果实际的做法；工具、其他参考、任务提示全部不变。

1. 系统提示：删去“做图纸还原先读 reconstruction 量测方法”，改为整图优先的默认做法——看全部整图，每层一次性完整声明；按总尺寸标定并把墙放在尺寸所指的参照面上（常见为外墙外皮、隔墙双线中线）；保真在完整保存稿上核查并局部修订；出首稿前，裁图/像素工具只用于整图解决不了的具体问题。
2. 对称保护：不得因局部裁图无填色、线细或剖面弱而漏掉图上画出的隔墙；填色、颜色、线宽只是制图习惯。
3. 局部工具的引导语由“看完平面后选工具”改为“仍有具体不确定时选工具”。
4. “质量优先于尽早出首稿”改为“保真比速度重要；靠对完整保存稿对照原图来达到，出稿前长时间局部量测不增加保真”。质量优先的目标不变，只改正工作顺序。
5. 裁图位置一律从原图像素网格读，不用裁图内偏移。
6. `reconstruction` 参考由 7470 字改写为 3276 字的同一整图优先方法，保留已证有用的检查：单位写法、窗高分族与例外窗、尺寸链段序、开口两端、保存后逐项回查与局部修订。

未改：39 个工具、其他全部参考、房间类型/命名/claim/立面对照等能力、任务提示与预算。三维体量（mesh）相关段落原样保留，本包未验证部分推理路径。

## 离线验证（0 模型调用）

- BIM 工作流相关 16 个测试文件共 150 项通过（`-n 4`）：tools、plan_partition、glm_route、inputs、mesh、region_overview、candidate_budget、claims、continuation、delivery_reply、input_view_status、shape_claims、view_references、plan_evidence_feedback、plan_measurement_binding、plan_revision。
- `batch.py prepare` 对 sm21/sm24/sm25 各在真实入口跑到模型进程启动前阻断：任务提示与 run58/run56/run54 逐字节相同，原图哈希相同，42 个生产文件中只有指引文件与 main 不同，MCP 实际返回新版 reconstruction 全文。见 [preflight_sm21.json](preflight_sm21.json)、[preflight_sm24.json](preflight_sm24.json)、[preflight_sm25.json](preflight_sm25.json)。

离线检查只证明改动可执行、条件可控，**不证明模型会改变行为或质量已恢复**。

## 原定节点回归（首轮提请时的方案）

执行情况：用户只批准 sm21 两次；run91 已执行（结果见上）；同条件的 run92 按事先约定未执行，改为上方对齐方案待重新批准；run93/run94 未获批准。下表保留提请时原文。

| 顺序 | run | 案例 | 对照的好结果 |
|---|---|---|---|
| 1 | run91 | sm21 | run57/58：14/29/14，位置 29/29 |
| 2 | run92 | sm21 重复 | 同上 |
| 3 | run93 | sm24 | run55/56/59/61/62：8/21/10，位置 15–21/21 |
| 4 | run94 | sm25 | run53/54：29/61/30，位置 61/61、53/61 |

条件：Sonnet 5（固定 `claude-sonnet-5`）/ medium / 3000 秒 / 24 候选 / 0 续查 / 禁委派；只用原图，无旧稿、GT、声明。每条单独一步启动，脚本核上一条真实回执正常完成后才允许下一条；429 或错误即停，不重试、不覆盖。历史单次 CLI 估价 $1.2–5.2，非订阅账单。

```bash
# 在工作树根目录，逐条执行，每条之间先看回执与结果
python AI_agent/logs/experiments/2026-09-29_whole_drawing_guidance/batch.py run --id run91
python AI_agent/logs/experiments/2026-09-29_whole_drawing_guidance/batch.py run --id run92
python AI_agent/logs/experiments/2026-09-29_whole_drawing_guidance/batch.py run --id run93
python AI_agent/logs/experiments/2026-09-29_whole_drawing_guidance/batch.py run --id run94
```

事先确定的判读口径：

- **主判据（质量）**：房间数与一一对应、无错拆错并；门窗宿主与门连接完整；原图位置（sm21 目标 ≥26/29，好结果 29/29）；外窗高度含南小窗、东窗等例外窗；单位/尺度正确。保留原 2cm 严格分区评分，不改容差。
- **机制核对（不作质量门槛）**：是否恢复“看整图后一次性声明”的做法，首稿前工具调用次数和耗时。
- 若行为恢复且 sm21 两次质量达到好结果水平，再看 sm24/sm25 跨案例；若行为恢复但质量未恢复，说明还有别的因素；若模型仍走局部量测路线，说明指引未被采纳，需要重新判断，不继续同条件抽样。
- 4 次只是恢复的首个信号，不等于稳定性已证明。

## 限制

- 服务端行为变化的具体原因无法本地证实，只能由时间分界和逐字节相同请求推断。
- 指引改动同时作用于所有图纸案例；部分推理/体量路径未测。
- run86、run87 未在既有质量报告中逐项评分，表中计数取自各自 README。
