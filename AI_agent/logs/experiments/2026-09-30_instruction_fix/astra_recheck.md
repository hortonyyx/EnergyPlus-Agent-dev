**可以开跑 run98，仅执行已批准的 sm21 一次。六项开跑阻塞已解除；另有两处非阻塞遗漏。**

1. **claim facts：到位。** 按当前 span／端点计算，缺失返回 `None`；字段名称准确。只读复现 run94 改窄窗，现报 **1.2 m**。[bim_claim_facts.py:18](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/src/agent/execution/bim_claim_facts.py:18)

2. **整层提醒：到位。** 已增加长度、接外墙及排除沿外墙条件，标记 `scope=floor`；条目改为墨线事实。原三张独立双线桌子反例现为 **0 条报告**。[plan_drawing_differences.py:220](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/src/agent/geometry/plan_drawing_differences.py:220)

3. **离线统计口径：到位。** 同墙与位置约束、整层提醒单列、检查状态均落实。我重新计算 **108 稿，与保存结果一致**；41 处未修对象下一稿仍有报告。人工记录有一处字段漏改，见后。[drawing_differences_validation.py:153](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/drawing_differences_validation.py:153)

4. **评价：到位。** `not_run`、缺楼层、额外无参照房间均判失败；高度通过条件包含两边无未配对项。已只读核对 run93/94 和上述反例。[evaluate.py:94](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/evaluate.py:94)

5. **完整报告：到位。** `inspect_plan_draft` 返回完整列表并校验草稿哈希；摘要有读取指引，装配带 `draft_id`。内存验证可返回超过 10 条，错误哈希不会附入。[run_bim_agent.py:2344](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/scripts/tool_scripts/run_bim_agent.py:2344)

6. **读取量：到位。** 已明确免读提示中给过格式的参考，工具说明同步。复算 **47,651／49,798** 正确，六份预检的代码、参考和图片散列均吻合。[bim_agent_guidance.py:177](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/scripts/tool_scripts/bim_agent_guidance.py:177)

两处非阻塞问题，建议归档／合入前补齐：

- **新引入：** `run_label` 函数被删除，但 `label` 入口仍调用它，会报 `NameError`；应恢复函数。不影响现有冻结标注、`check` 或 run98。[drawing_differences_validation.py:268](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/drawing_differences_validation.py:268)
- **遗留漏改：** run61 的说明已正确，但结构化 `object` 仍为 `V3`；应改为门 `D4`，宿主另记 `V3`。这不改变 33 条真差异、1 条无法判断的数量。[drawing_differences_adjudication.json:318](/workspaces/EnergyPlus-Agent-dev/.worktrees/opus-guidance-20260929/AI_agent/logs/experiments/2026-09-30_instruction_fix/drawing_differences_adjudication.json:318)

本次未改文件、未调用模型、未跑 pytest。