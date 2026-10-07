# Q1 执行与交接

状态：本范围实现与离线证据已交付，**整包尚未通过验收**。C 的通用保存前拦截、G 的两条旧工具说明、I 的最终有效稿消费仍待归属协调；两份最小补丁均未应用。沙箱下不提交。

执行方 Astra；基准 `e030b6b0`，分支 `dev/astra-q1-20261007`，工作树 `D:/EnergyPlus-Agent-worktrees/q1`。开工时干净。完整读取 Agent.md、产品目标、当前任务、工作方式、名词规范、最新交接与本包指定资料后开工。

## 范围与环境

- domain · BIM rules/kernel：同层、跨层规整和三维硬约束，两种模式共用。domain · tools/methods/guidance：E/F 仅分工平面读图员；单模型只改必要规则参考。runtime 不改。
- 未改相邻 v1/q2 工作树、Q2 所属文件、V1 runtime 或共享版本登记表；未接触 runs-next/runs-cc 整案；未跑全量、未写 Git 元数据。
- work model、Paratera、DeepSeek 请求均为 **0**。按派工单和 `workflow/models.md` 的开发派工偏好，使用三位 `gpt-5.6-sol` / high 开发子代理，分别承接边界明确的 kernel、读图员、回放；Astra 负责入口、展示、审查和最终验证。开发子代理不算产品实测。
- `uv sync --frozen --python 3.12` 因 uv 缓存内 `.git` 只读失败，未更改权限。已有 `.venv` 可用，Python 与 `src.agent.__file__` 均指向 q1。每次检查使用 `scripts/activate_windows.ps1`、pytest `-n 2`，临时目录在 `AI_agent/archive/local_backup/q1/`。
- 使用基线已有 `BIM_AGENT_REGISTRY_PATH` 指向隔离测试快照；[准备脚本](prepare_offline_snapshot.py)未改共享登记表，没有登记发布版本或跳过文件/工具哈希验证。

## A–I 对照

| 条目 | 实现与边界 |
|---|---|
| A | 独立编译前规整；严格小于 0.30 m；优先标注、固定外轮廓、更多共用墙线；端点和宿主开口跟随。受命名种子/开口保护的窄条拒绝，保留对象、尺寸和改法。严格编译器本身不吸附。 |
| B | 改各层平面稿并重编译，不改 source 多边形；逐项核对空间数、宿主、门连接，失败回滚。Z 保持层高与现行楼面/顶面表示，显式 `elevation_reference:true` 优先。按“原 >=30cm 线不动”保护既有分离，其自动拒绝率代价见 H；Q2 有明确标高依据时应接入该标记，需合并协调。 |
| C | 平面试建/建层/平面修改/装配已在保存前拒绝；0.60m 检查含凹形窄颈/细舌；事后 source 检查固定正交 XYZ 门槛。**通用 build/revise 保存入口还没接入预检**，不能声称已拦住所有新候选。 |
| D | 原稿、有效稿、版本、完整清单及哈希保存；工具摘要、inspect 全文、候选 sidecar、交付报告和查看页已接入。拒绝中的尝试不算实际应用。 |
| E | 仅 reader trial：外皮/内墙中线/明确双端门框采用；歧义保持并报告。共线墙链、垂直接头与宿主开口整体随动，每步守住正交和连接；实际位移不因低分辨率最小搜索窗口而越过 0.30m。真实 7/7 层能编译，sm25 两层原先的斜墙错误已修复。 |
| F | `dimension_chains` 提供毫米段长、总长、轴向、刻度像素和来源；核对闭合和比例残差。只有两端对应外皮的总尺寸链接管该轴，原锚点交叉核对，依据写入 `regularization_inputs`。5 条原图人工读数明确是 dev auxiliary，GT 只评测。 |
| G | 替换旧逐条测剖面文本，未改 D1l 顺序。单模型只四处必要说明，[精确替换清单](intentional_model_text_changes.json)限制首请求放行；两个工具目录旧描述仍随范围补丁待协调。 |
| H | 15 组/25 稿：最终保守门下 6 成功、9 结构化拒绝；成功组原 >=30cm 分离全部保持。拒绝 after=null，不当精度提高。见[回放笔记](replay_notes.md)、[逐项摘录](itemized_changes.md)、[完整证据](replay_report.json.gz)。 |
| I | 各定向条目的最近记录为 143 通过、7 失败；最后一组 reader/入口/角色检查 54/54 通过，历史 run99 75 步和首请求精确差异检查通过。三例贯通及四项恢复仍被 Q2 session 旧输入哈希比较挡住；sm25 最后重跑已越过斜墙错误，到达同一哈希阻断。整包未通过。 |

## 待协调的最小补丁

[派工单](brief.md)只开放 Toolkit 三个平面入口，并将 session.py 归 Q2。以下补丁已生成、语法与 `git apply --check` 通过，**均未应用**，已向用户解释并请求协调：

1. [source_save_gate.patch](source_save_gate.patch)：Toolkit.build 在分配候选前调用已实现的 `reject_source_proposal`，内存构建 source、检查硬约束；拒绝只存审计，不分配 candidate。另替换两个平面工具目录失效的“不对齐”说明。预检 helper 有行为测试。
2. [session_compiled_plan.patch](session_compiled_plan.patch)：Q2 建层/返工消费端兼容原输入和通过文件路径/原始字节哈希验证的最终数字稿，继续保留旧格式和严格校验。现代码将最终稿与原输入哈希比较，E/F/A–C 一改稿就不等。不能靠改回原输入而丢掉规整结果。

Trial 已独立保存 E/F 数值输入和 A–C 编译有效稿，Submission 交最终稿；这是 session 消费规则需要同步的原因。

## 离线统计与限制

5/10/30 cm 三个门槛按四个互斥区间统计：`<=5 / (5,10] / (10,30] / >30 cm`。房间指标为匹配边界 Hausdorff，门窗为沿墙最大端点误差。拒绝组没有后指标。

- cmp3：sm24 role/single 通过；sm21 两组因附带改变既有 >=30cm 分离线而拒绝；sm25 两组因约 11–15cm 近线、受保护窄条和 <0.6m 空间拒绝。
- Opus：2 通过、sm25 拒绝。Claude：sm24 两例通过，另 4 例结构化拒绝。旧循环/悬空错误已变为明确回滚原因。
- 成功真实稿房间 `7/3/6/0`、门窗 `33/4/5/0` 前后不变；本次 A–C 历史成功稿没有实际移动。尝试但未交付的变化不记“已消除”。
- 成功组既有 >=30cm 线对绝对保持：真实 `24/24`、Opus `28/28`、Claude `26/26`。这一保守解释使多墙楼层更常拒绝跨层对齐，需 Opus 验收产品代价，本包未擅自放宽。
- E 的真实试建 7/7 层能编译；F 的开发辅助链 5/5 层能编译。成功 reader 结果的房间数、门窗数、宿主与门连接不变。

| 成功样本 | 房间边界：前 → 后 | 门窗位置：前 → 后 |
|---|---|---|
| A–C · cmp3 两组 | `7/3/6/0 → 7/3/6/0` | `33/4/5/0 → 33/4/5/0` |
| A–C · Opus 两组 | `22/0/0/0 → 22/0/0/0` | `49/1/0/0 → 49/1/0/0` |
| A–C · Claude 两组 | `14/2/0/0 → 14/2/0/0` | `41/5/1/0 → 41/5/1/0` |
| E · 真实 7 层 | `29/12/21/5 → 58/1/3/5` | `132/15/5/1 → 135/15/2/1` |
| F · 辅助 5 层，原稿 → 墨线 → 尺寸 | `24/5/17/5 → 42/1/3/5 → 44/0/2/5` | `96/11/4/0 → 98/12/1/0 → 98/12/1/0` |

F 的 `D-south`、`D-hall` 各从 <=5cm 退到 5–10cm，逐项像素、宿主与墨线证据保留在报告；未出现新的 >30cm 项。E/F 的“能编译”是对应独立步骤验证，不等于新 A–C 硬约束下整案可交付。

同一最终代码两次回放结果完全一致，报告 SHA-256 为 `9a680ff7fd2806f7c0097ad34c4b28d53e5e876ea0aec830ce96d36e3ab9b63b`。

逐项清单位置：`regularization_replay[].items` 下分别是 applied_changes、eliminated、attempted_changes_not_delivered、rejected。对象尺寸在 input_validation，原始/有效状态在 before/after。sm25 分工/单模型分别为该数组第 5/6 项。E/F 每扇变化与退档在 reader_alignment_replay 和 summary.reader_alignment，未隐藏退档。

## 给模型的文字变化

字符数含空白，详见[计数](guidance_counts.json)。

| 内容 | 之前 | 之后 |
|---|---:|---:|
| 单模型读图方法 | 4066 | 4131 |
| plan_partition 参考 | 7448 | 8617 |
| plan_assembly 参考 | 1725 | 2161 |
| 平面读图员指引 | 9045 | 9134 |

单模型四处替换：读图第 5 步说明硬约束/清单；建层参考说明规整、版本与依据；修改参考说明间接移动；装配参考说明 XY/Z 和显式标高。单模型不开 E/F；立面读图员文本与基准相同。

## 验证与提交建议

全部 XML 结果保留，包括失败记录；其中 Windows 失败堆栈的换行已统一 LF，XML 解析内容逐项不变。[验证汇总](verification_summary.json)按条目取最近一次结果，不冒充一次全量检查：150 个不同条目中 143 通过、7 失败。最后一组 [pytest_acceptance.xml](pytest_acceptance.xml) 为 54 通过；[pytest_sm25_final.xml](pytest_sm25_final.xml) 是读图边界修复后的单项贯通复核，仍因 session 哈希比较失败。

七项未通过：sm21/sm24/sm25 三例完整分工；读图员试建后恢复；全部读图员完成后恢复；`build_plan_bim` 与 `claim_transaction` 两处内部回执后恢复。失败不是机器忙导致的已知偶发现象，未通过重试掩盖。对应运行证据保留在 `AI_agent/archive/local_backup/q1/pytest-final/` 和 `pytest-sm25-final/`。

初次未激活 Windows UTF-8 环境造成的读取错误已纠正；旧动态墙厚门槛及混同原稿/有效稿的断言已替换。一轮晚到 kernel 修改造成隔离快照哈希失配，冻结代码并刷新快照后重跑，未放松哈希检查。run99 的 75 步真实工具重放通过，包含它的检查批次用时约 9 分钟，模型请求 0。

[最终归属核对](scope_check.json)：30 份改动/新增 Python 文件语法通过，文本无 CRLF，`git diff --check` 通过。`run_bim_agent.py` 只改变 Toolkit 的三个获派入口；角色指引只改变三个平面段落。Q2/V1 禁改文件及共享登记表均未改变。两份待协调补丁的 `git apply --check` 通过，未应用。

本轮旧测试临时目录的清理被自动审批审查拒绝，返回 `blocked by policy`；未执行删除、未换方式绕过，临时目录保留。本轮输入只读，运行中的整案与相邻工作树未动。

建议 Opus 复核后分组提交，本树不提交：

1. A–C：kernel、严格编译元数据、固定 source 检查、规整 helper、Toolkit 三入口和相关测试/参考。
2. D：审计 sidecar 与继承、报告/查看页。
3. E–G：墨线/尺寸链、Trial/Submission 最终稿和恢复、平面指引与测试。
4. H–I：回放脚本/结果、文字差异清单、验证与交接。
5. 协调合入两份范围补丁，完成三例贯通/恢复后再统一登记；本报告不是整包已验收的结论。
