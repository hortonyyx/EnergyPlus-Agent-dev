# A4-T 交付报告（实施中）

派工：Opus 5.5；执行：Astra；开始：2026-10-05 00:39 UTC。
基准：`aa48d72f5a89d7f091ef20baa42771088b545e7b`；工作分支：`dev/astra-a4t-20261005`。
本分支小步提交，不合入 main、不推送。验收以 [派工单](brief.md) 和 [A4-T 条件](../../../project/unified_agent_acceptance.md#吸收包第四批-a4-t全楼检查上下层对齐与细条平面差异检查10-05-派出astra) 为准。

## A. 上下层对齐与细条

已接保存、装配和交付的已有返回：上下层近共线墙、源接触细条、薄空间、覆盖细缝和小台阶；提供对象、尺寸、容差依据及已有线建议，不修改几何。相同优先级时列出两条已有线交模型选择，不捏造中间坐标。

默认值为 `min(墙厚, max(两个像素, 半墙厚))`；本地墙厚已声明时进一步封顶。墙厚未记录时从本层原图内至少三条长双线/带状线估计中位宽，明确是墨线估计；无墙厚则只用比例尺，无两者则标未检查。用户细度上限尚未配置，如实列在未覆盖范围。

最终 [源候选核验](source_replay.json)：11 份（亲做三例、Claude Code 好结果六份、10-04 两份 sm25），59 条层间偏差、59 条细接触片；与源坐标和接触宽度独立逐条复算，不存在的偏差 0 条。亲做 sm21、sm24 为 0；亲做 sm25 命中已知 6 cm 墙偏差、4 条 9 μm 墙偏差与 9 条接触细条，本楼两层默认容差约 7.57/7.63 cm。新线路 sm25 有 11 条墙偏差；旧线路毫米模型不放宽容差，标比例尺范围不适用。真实设计意图仍需模型看证据裁决，几何事实核对不等于语义误报率证明。

纯几何检查覆盖 9 项反例；额外约束薄条的备选线必须平行，不能拿垂直端边作为目标。完整受影响检查与返回体积核对仍在做。

## B. 平面差异检查

已补：双线的有界门口断线连接；与现有墙相接的遗漏双线之间可互为端点证据；两条候选面须有相近长度与足够原始墨线支持，避免将走廊墙与短桌边误配。对几乎占满一个墙段、原图又无墨线支持的无门洞口，单列 `unsupported_open_separator`，避免原检查扣除洞口后漏掉多余隔墙。范围说明列出楼层、标定轮廓、已查隔墙段，以及外墙/窗、斜墙/单线完整性、高度、用途等未覆盖范围；0 不再暗示整图正确。

[115 份草稿回放](plan_replay.json) 与 [逐项复核](plan_adjudication.json)：

| 输入 | 新增提示 | 冻结标签命中 | 原图另行确认 | 新增误报 |
|---|---:|---:|---:|---:|
| 原 108 份冻结草稿 | 8 | 5 | 3 | 0 |
| 10-04 两份 sm25，共 6 份已编译草稿 | 2 | — | 2 | 0 |
| sm24 run100 draft_002 补充反例 | 4 | — | 4 | 0 |

冻结标签命中从 175 到 180，新增 5、丢失 0。另 3 条是 sm21 真实走廊墙 y≈624 与声明 y=600 的位置差，原房间种子标签未标这种偏移；不是让模型再加一道墙。sm25 两条来自新线路 draft_009/011 的同一处分隔，已与 `candidate_07` 的 `F1:D_core`、`F1:S_C`/`F1:S_corr` 连接及源哈希对应。旧订阅线三份草稿都因毫米当米标 `not_checked`，不算零差异通过。条数按草稿计，同一错误跨修订重复不算独立样本。上述 0 只指新增提示，不宣称旧检查器全部无误报。

## C. 文字与返回体积

只替换操作指南第 5 步，针对 sm24 run100 漏双线、sm25 `D_core` 多余分隔、亲做 sm25 层间 6 cm 偏移；提醒按报告覆盖范围读数，对齐已有线并保留房间/门窗/连接。[同口径计数](instruction_comparison.json)：

| 项目 | 改前 | 改后 |
|---|---:|---:|
| 系统提示 | 9,555 | 9,532 |
| 工具说明 | 16,762 | 16,762 |
| 参数结构 | 17,179 | 17,179 |
| 常读参考 | 15,705 | 15,705 |
| **四项合计** | **59,201** | **59,178（−23）** |

全目录仍 43 个工具，默认启用仍 38 个；没有新增工具。新增精度诊断摘要最多 8 条，保留总数/分类、几何位置、尺度与墙厚数值，详细依据和全部条目进入 A3-T 的哈希报告，现有 `read_candidate_items` 可分页读取。

[真实 MCP 返回比较](reply_comparison.json)，以新线路 sm25 保存的相同输入分别运行基准和新版：4 次历史调用，加从最终草稿/源提案重新保存的 2 次调用。计全部文字块字符，不计图片或协议封套。

| 返回 | 改前 | 改后 | 增量 |
|---|---:|---:|---:|
| 平面修订 `revise_plan_bim` | 36,684 | 38,595 | +1,911 |
| 多层装配 `assemble_plan_bim` | 32,842 | 39,958 | +7,116 |
| 源修订 `revise_bim` | 58,004 | 65,092 | +7,088 |
| 交付 `finish_bim` | 3,850 | 3,850 | 0 |
| 平面保存 `build_plan_bim` | 28,867 | 30,778 | +1,911 |
| 源保存 `build_bim` | 29,715 | 36,803 | +7,088 |

六组源模型文件字节、几何内容、返回图片全部相同。交付维持原短摘要，完整交付报告含新检查；定向测试确认能通过已有工具按哈希读回。新增文字是诊断摘要和实际覆盖说明，不把未变的候选几何再拷一遍。

## D. 版本与检查

当前新版本 `t1-20261005-a4t.2`，54 个文件；[核验](version_verification.json)全部哈希一致，原有 8 个版本逐条保持不变。`.1` 是补上“备选线必须平行”之前的开发快照。离线检查设置本工作树 `PYTHONPATH`，pytest 显式 `-n 2 -s`，临时文件仅放本工作树。
最终检查覆盖直接引用改动模块的全部 30 个文件，并扩到 BIM/runtime/harness 和相邻装配检查，共 81 个文件；运行中，当前出现 1 项失败，等待汇总断言后定位，不计为通过。

[两底座三例核对](runner_parity.json)已通过：sm24、sm25、sm21 的系统指引、工具目录、名称/说明/参数、任务正文逐字节一致；输入图片哈希相同。只走模型请求准备边界，Claude Code 的真实模型启动被拦住，新底座用脚本适配器，未发模型请求。不把离线核验写成工作模型整案验收。
模型请求：0；后续仍为 0。无外部付费调用。

## 进度、提交与遗留

- 开工：已读 `AI_agent/Agent.md`、派工单及 A–D 验收要求，正在加载项目上下文和历史证据。
- `64bc4f69`：报告初稿。首次普通 Git 提交在共享文件系统索引刷新耗时过长，停止后改显式路径提交成功。
- `5732cb9b`：A 的检查实现与首轮源证据。
- `8d5acc4f`：B、文字预算、新版本及源建议平行性修正；最终检查和返回体积证据随后提交。
- 初轮 23 项定向测试通过。发现源建议的垂直边问题后，主动终止尚未完成的综合轮，保留 [中止记录](validation/initial_interrupted/related.json)，以修正后 `final2` 为验收轮。开发快照的版本不匹配不计为通过。
- 交付时间目标约 110 分钟；若接近时限，优先保证 A 完整提交，如实交回 B 的剩余范围。

## 离线复现

下列命令均在本工作树执行，无模型调用。`materialize.py` 只从现有 Git 证据对象解出所需文件到 `.tmp_a4t/history`，逐文件核哈希；原始实验目录只读。新一轮测试使用新的标签，保留已有证据。

```bash
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-05_absorb_a4t/materialize.py
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-05_absorb_a4t/replay.py sources
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-05_absorb_a4t/replay.py plans
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-05_absorb_a4t/adjudicate.py
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_tool_package_t1/measure_instructions.py --baseline aa48d72f --output AI_agent/logs/experiments/2026-10-05_absorb_a4t/instruction_comparison.json
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-05_absorb_a4t/measure_replies.py
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-03_runtime_r3/compare_runners.py --output AI_agent/logs/experiments/2026-10-05_absorb_a4t/runner_parity.json
PYTHONPATH="$PWD" python AI_agent/logs/experiments/2026-10-05_absorb_a4t/validate.py repeat_001
PYTHONPATH="$PWD" python -m src.agent_runtime.agent_registry verify
```
