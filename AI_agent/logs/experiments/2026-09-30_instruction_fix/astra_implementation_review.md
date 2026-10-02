**结论：暂缓开跑 run98。** 主要文字修正已落实，但目前有事实取值错误、离线检出统计失真，以及验收条件误判。建议先修下面六项，再更新零调用预检；不需要先扩大模型回归。

本次只读复算了全部 **108 份历史草稿**：标注和检查输出均与存档一致；105 份执行检查，3 份因比例异常跳过。还核对了预检散列，并做了内存中的反例验证。未改文件、未调用模型、未跑 pytest。

**一、开跑前必须修**

**1. claim facts 会报告过期或虚构的窗宽。**

位置：[bim_claim_facts.py:36](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/src/agent/execution/bim_claim_facts.py:36)。

目前直接读取 `window.get("width_m", 0.0)`。但 `width_m` 是可选附加字段，窗口的有效几何字段是 `span`；正常 `update_window` 修改 `span` 不会同步该缓存。

我用 run94 的真实候选在内存中复现：

- 将 `F1:W_T1` 的宽度改为 1.2m，facts 仍报 **2.4m**；
- 删除可选 `width_m` 字段，facts 报 **0.0m**。

这会直接误导本轮新增的跨宽度核对。应从当前规范几何或源开口计算宽度；无法取得时明确未知，不能默认为零。无需修改 claim 机制。

另外，`:21` 算的是 `z_floor + ceiling_height`，应称“候选楼面至顶面范围”，不要在 README 中统一称为“层间范围”。

**2. “完全未声明隔墙”分支把独立家具当成墙。**

位置：[plan_drawing_differences.py:219](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/src/agent/geometry/plan_drawing_differences.py:219)。

该分支在两端接墙检查之前，只要找到三条以上非外围双线，就返回：

> drawing has several double-line or banded wall lines

我构造了一个真实开敞房间、三张不接墙的双线矩形家具，结果报告 **`drawn_wall_lines: 12`**。现有家具负例包含已声明隔墙，因此没有覆盖这个分支。

最小修法可以二选一：

- 收回到有接墙证据的候选线；
- 保留为明确不认定墙体的整层观察提示，但与对象差异、逐项处理要求及检出率分开。

应补这个开敞空间负例，相关条目中的“没有画墙／墙连续”等断言也应改为实际采样到的墨线事实。

**3. 离线匹配不能支持当前对象级检出数字。**

位置：[drawing_differences_validation.py:150](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/drawing_differences_validation.py:150)。

有三个明确问题：

- `:163–164` 把一条 `no_dividers_declared` 整层提醒，匹配该层所有漏墙及缺门标注。run50 `draft_001` 的**一条提醒被计成 13 个缺隔断关系和 13 扇缺门的检出**。
- `:156–162` 匹配门洞只比方向和沿墙重叠，没有比较墙的垂直位置。run83 首层出现南墙报告匹配北门、北墙报告匹配南门，跨距约 **1.90–2.27m**。
- `:165–166` 让任意“声明墙墨线不足”匹配任意漏墙/多空间标注。例如 sm24 东南墙报告匹配东北部 `EN/EC` 并房；位置不相关。

仅剔除整层提醒、其余匹配暂保持原样，原来的 **28/31** 就变成 **15/31**，缺/错位门的 **31/41** 变成 **18/41**。这不是最终修正成绩，只说明原数字混合了不同粒度。

必须先区分整层提醒与对象定位，补位置/关联对象约束，再重算及重新判定新增的未匹配报告。并保存每稿 `reported/not_checked` 状态；目前 `run_check` 丢掉了该状态，README 才另行扣除三份跳过稿。

**4. “空间一一对应”实际只检查了参考点之间没有合并。**

位置：[evaluate.py:81](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/evaluate.py:81)。

两个反例：

- 传入 `{"status":"not_run"}`，返回 **`pass_: True`**。这不是纯假设：旧审计在候选不是两层时，确实返回 `not_run`。
- 候选多出没有参考种子的小房间，该函数无法发现，因为没有取得完整候选空间集合。

应要求审计完成、预期楼层和参考种子齐全，并核对**所有候选空间也恰好对应一个参考空间**。保留独立分区检查，它仍负责形状、重叠等问题。

高度检查的 0.05m 比较方向正确，但通过条件必须同时要求参考及候选外开口均无未匹配项，不能只看 `within == matched`。

**5. 超过十条的完整差异报告对模型不可读取。**

位置：

- [plan_drawing_differences.py:322](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/src/agent/geometry/plan_drawing_differences.py:322)
- [run_bim_agent.py:943](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/scripts/tool_scripts/run_bim_agent.py:943)、`:1218`

摘要正确显示总数和截断，也保存了完整文件；但模型没有通用文件读取工具，`inspect_plan_draft` 只返回声明与散列，装配返回甚至没有完整报告路径。

应通过已有检查入口提供完整报告或分页读取，携带对应草稿、图像及散列。**保存文件路径不等于模型可查。** 这 108 稿没有超过十条，但共同定稿已经明确要求完整内容可查，接口应在接入时闭合。

**6. 默认读取量遗漏了文字仍要求读取的 `edits`。**

位置：

- [bim_agent_guidance.py:173](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/scripts/tool_scripts/bim_agent_guidance.py:173)、`:188`
- [batch.py:54](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/batch.py:54)

TOOLS 仍要求准备调用时读取所列参考，并将 `revise_bim` 指向 `edits`；工具说明也指向它。DELIVERY 给出最小格式，却没有解除这项读取要求。

当前 `edits` 为 **6,364 字符**。按现有要求计入后：

| 口径 | 本版 | run58 |
|---|---:|---:|
| 工具说明去缩进 | 53,605 | 48,205 |
| 按实际发送 | 55,728 | 49,945 |

因此“低于基线”尚不成立。可明确已给出的完整格式无需再读参考、其他操作按需读取；或者将确需读取的内容计入并压缩。无需因此启动全面说明书重构。

**二、文字与其他运行时改动**

以下部分基本忠实落实定稿：

- `CORE:35–40` 保留临时估值，允许合理取证后仍不确定的信息成为显式假设。
- `DRAWING_METHOD:85–90` 用 `Aim for` 表达各层草稿重心，并明确局部取证和编译纠错可随时进行，没有新增绝对门槛。
- `FINISHING` 已由主提示与续查共用。
- 看图返回给出了实际倍率和坐标换算；claim facts 尊重 `value_targets`，没有改变采信规则或自动判错。
- 新检查确实修了轮廓内掩膜、横纵尺度分别处理、已声明开口排除，并增加了部分重叠的端点差异。
- 参考段落搬移没有发现内容丢失。

以下**不单独阻塞纯图纸的 run98，但合入前必须处理**：

1. **全局 CORE 限制了部分推理。**  
   `bim_agent_guidance.py:26–28` 的“没有画出的墙不建”发给了所有输入类型，与 `MESH_VIEWS:150–153` 的缺失内部布局推断直接冲突。应把图纸专用限制放进图纸做法，共用原则保留“已知与推断分开、保留实际空间”。原有禁止假楼板的约束也不应随改写丢失。

2. **输入类型判断尚未完整解决未知与旧体量视图。**  
   `run_bim_agent.py:223` 对未标类型且没有原网格的图片仍默认图纸，旧的体量渲染图输入仍可能走错；`build_guide:236–243` 的 `unknown` 包含图纸和体量视图方法，却不含照片段。明确类别的新入口可用，但不能宣称未知/混合输入已全部处理好。

3. **放大提示应写“最长边”，不是“宽”。**  
   `bim_agent_guidance.py:69` 的“约 500px 宽可放大三倍”对狭长高框不成立。应改为“裁框最长边约 500px”。

4. **运行与设计说明尚未同步。**  
   本次提交没有更新共同定稿列出的 `run_case` 和设计说明。尤其应说明新参数、报告范围及完整报告的读取方式。

**三、离线记录与 README 的准确性**

已核实成立：

- 108 稿的数量及三个案例分布；
- 43 份无标注差异稿均无报告；
- 三份比例异常稿包含 36 条门相关标注；
- 参数曾在同批数据上调整、没有独立留出集，README 已明确披露；
- run57/58 严格高度均为 17/17，run93 为 15/17，run94 为 9/13，并有四个未匹配参考窗。

还需修正：

- “漏墙 31 处”实际来自参考种子合并后构造的**缺分隔关系**，不天然等于 31 道独立物理墙。
- 人工判定的 run61 条目将门写成 **V3**；实际报告对象是 **门 D4、宿主隔墙 V3**。位置：[adjudication.json:314](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/drawing_differences_adjudication.json:314)。
- 按同一运行、同图相邻成功草稿复算，得到 **30 项消失、42 项仍报**，不是 README 的 41。应保存逐对记录和筛选口径。
- 29 条人工认定真实差异、1 条无法判断，不能扩展成普遍“零误报”；本轮已复现开敞空间家具反例。
- `evaluate.py:60–78` 的 `difference_trace` 只给下一稿总数，没有逐对象标记是否仍报，更没有证明模型据报告取证。应收准说明或补对象关联。

这些统计修正不否定量具的用途，但当前数字不能作为它已满足接入条件的证据。

**四、batch.py 与 run98 条件**

执行范围基本正确：

- `approval.json` 只放行 run98；
- 3000 秒、24 候选、medium、零续查、原图冷启动正确；
- `sonnet` 在现有路由中固定到 `claude-sonnet-5`；
- 拒绝覆盖既有运行目录，没有整案重试循环；
- 六份预检的原图散列均匹配；run98 的 44 个实现文件、指南及 batch 散列匹配当前文件；
- 执行后读取真实回执。

建议同时补三个小点：

- 开始模型调用前，也将实际图片散列与预检保存值比较；目前冻结检查主要比较实现，当前图片虽未变，但执行入口没有这条断言。
- 异常回执应明确给出失败退出状态。当前 `run_one:189–192` 只是打印，调用方可能误把脚本退出成功当实验通过。
- “不重试”已落实到本脚本；不能据此宣称控制了 Claude CLI 内部重试。禁委派目前也主要靠任务提示，MCP 中仍暴露 `review_detail`，应如实区分文字约束与程序禁止。

**开跑条件建议：先修上述六项，重算受影响的离线统计并刷新预检，再跑获准的 run98 一次。** 体量路径的修正可不占用本次模型额度，但不能带着已知矛盾合入 main。