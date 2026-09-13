# 历史好 reading 与当前 BIM Agent 工作方式对照

本记录是 2026-09-13 的有界只读复盘。范围只含 07-07 sm24 Haiku、07-08 sm21 GPT-5.4-mini 的原始产物/运行记录，以及当前 `run_bim_agent.py` 和 09-12 sm24 冷启动的真实调用。没有运行模型、没有读取或修改 GT 来生成几何，也没有改生产代码。本文只提方法证据；历史 reading 的高分或人工好评不等于源 BIM、门窗连通或整案成功。

## 一、原件核对结果

| 实例 | 真正执行的读图方式 | 外部介入与输入条件 | 能证明什么 / 不能证明什么 |
|---|---|---|---|
| 07-07 sm24 Haiku | `measure-before-draw` 被明确要求；最终目录保留 38 份 CV JSON：14 次裁图、5 次标定、2 次墙线投影、8 次窗连通域、4 次层线投影、5 次候选处置叠图。平面每条关键墙说明尺寸链或像素换算，未标注的 H6 明记为空 `dimension_refs` 的像素量测；真实无门开放段也单列而未“补墙”。历史过程记录另称约 96 次工具往返、约 0.65M tokens。 | 冷启动只在提示层隔离，完整原始 spawn prompt 未随 run 保存；可核实的 provenance 只明确记载必用量测。Fable 主控先因粗锚、漏墙漏窗和换算矛盾打回一次，又因 `anchor` schema 形状打回一次。输入 `testdata_prompt.json` 还给了 200m²、1 层和 `thermal_zones: 8`；这不是 GT 坐标，但会给完整性判断强先验。 | 支持“量测、候选逐项处置、可追溯的未知”能帮助弱模型读清复杂正交平面。sm24 当时没有 GT，结论来自人工看图；门主要埋在墙 note/`uncaptured`，不是结构化开口。后续 correction 还被记录为改坏部分 reading，因此不能称整案成功。 |
| 07-08 sm21 GPT-5.4-mini | 原始 Codex 日志完整保存。先单独处理 1F pilot，再开五个独立会话逐图处理其余图；提示提供预计算的中性 prescan 候选，skill 自己要求先标定、再量测、再画，并要求核验/处置候选。六份日志共有 308 次 shell `exec`，其中包括显式 `crop_zoom`、`px_m_calibrator`、墙/层线投影、窗连通域和 prescan 调用，也包括读文件与写 JSON，不能把 308 全算成 CV 量测。 | Opus 主控审过 1F pilot 后才放批量；GT 被物理排除在隔离目录外，但输入元数据明确给了每层 7 个 thermal zones、240m²、两层和“dimensioned”。最终 GT scorer 是生成后的评价，不是 reader 输入。 | 墙 9/9、立面窗 15/15，但平面窗只有 6/7。已登记缺陷是纯尺寸链累计把 0.24m 未标注墙带余量放错位置，造成后续窗漂移；这是 reading-only，没有源 BIM 或连通验收，不能称“模型无关配方已经普遍成功”。 |
| 当前 BIM Agent 与 09-12 sm24 run01 | 当前 GUIDE 约 229 行、2034 词，同时解释整案建模、墙厚、开口、局部编辑、回叠、交付和局部委派；量测被写成可选。工具已有看图、像素剖面、尺寸链累计、像素换算、建模、源平/立面查看、回叠、开口检查和修订，但没有直接暴露旧 prescan/墙线投影/窗连通域/候选处置账本。run01 的真实主调用只有 `inputs` 1 次、`view_image` 22 次、`review_detail` 1 次、`build_bim` 1 次；没有像素剖面、尺寸链、像素换算、候选源查看、回叠、开口检查、修订或 `finish_bim`。 | 单个 Sonnet 会话同时承担读五图、空间解释、完整 BIM JSON、委派、检查与交付。唯一候选到剩余约 90 秒才保存。局部 Haiku 问题还预填了错误的“10000mm 高”前提；Haiku 将 3 窗读成 4 窗，父模型未核清冲突。 | 9 空间/11 窗/11 门的源几何自洽，但独立分区 severe，连续办公室被错拆；这直接说明“GUIDE 写了量测和反馈”不等于模型形成了这种工作方式。提示长不是单独因果，真实差异是没有形成建模前可检查的证据产物，也没有留出建模后的反馈轮次。 |

直接证据入口：

- 07-07 sm24：[run provenance](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/llm.yaml)、[reading summary](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/reading_summary.md)、[1F 原件](../../../../case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading/1f_view.json)、[过程记录](../2026-07-07_haiku_cv_retest/README.md)、[输入元数据](../../../../case_tests/e2e_tests/sm24_anchor/case_data/testdata_prompt.json)。
- 07-08 mini：[pilot 原提示](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-08_gpt54mini_cv_retest/0_reading/codex_logs/pilot_prompt.txt)、[原始调用日志目录](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-08_gpt54mini_cv_retest/0_reading/codex_logs/)、[reading summary](../../../../case_tests/e2e_tests/sm21_anchor/run_2026-07-08_gpt54mini_cv_retest/0_reading/reading_summary.md)、[已知缺陷登记](../../../../case_tests/test_baseline/reading_fixtures.json)。
- 当前方式：[BIM Agent 源码](../../../../scripts/tool_scripts/run_bim_agent.py)、[09-12 sm24 run01](../2026-09-12_bim_agent_sm24_run01/README.md)、[真实工具日志](../2026-09-12_bim_agent_sm24_run01/tools.jsonl)、[Haiku 实际问题](../2026-09-12_bim_agent_sm24_run01/detail_01/question.txt)。

## 二、最多三项可泛化建议

### 1. 先做一份小而结构化的“图证账本”，再让模型提交 BIM

建议先作为实验方法，不急着改生产 harness。对当前最关键的一张平面，要求模型在第一次 `build_bim` 前把以下内容写进可保存、可复查的中间结果：实体隔墙的连续区间、明确无门的开放区间、门窗标记、采用的标注链或像素标定、每项的 observed/inferred/unknown。它不必恢复旧 legacy reading 全 schema，也不规定单线或双线；重点是让空间拆分依据在整案 JSON 之前显式出现。

原因不是“历史调用多所以更好”。sm24 历史原件真正保住了这次失败的关键语义：H6 是无标注像素量测，走廊东侧有真实开放段，7 处室内门有逐段像素依据；当前 run01 则在 22 次看图后直接提交整案，分区依据无法单独检查。旧 CV 工具只适合干净矢量 CAD，实验可先复用现存的中性 prescan/投影/连通域能力；生产是否暴露这些工具，应等换图结果再决定，不能把固定颜色或阈值写成建筑语义。

### 2. 把历史 pilot 的有效部分复现为“程序性检查点”，不要把正确几何交给 reviewer

在同一总预算内，限定第一阶段只核一张关键平面并尽早保存初始候选；检查点只问：标定锚是否来自所述标注端点、换算是否自洽、每个潜在房间边界/开放段是否有处置、未知是否保留、schema 能否执行。reviewer 不得给房间数、墙坐标、GT 对照或“这里应合并/拆分”的答案。通过后才展开立面、门窗高度和整案装配，并预留源平面/回叠后的至少一次修订机会。

这是对真实外部介入的诚实复现：07-07 sm24 的好结果经过一次流程返工和一次 schema 返工；07-08 mini 也由 Opus 审 pilot 后才并行剩余五图。当前 run01 直到剩 90 秒才首次建模，随后未看候选，说明“早保存、再反馈”的文字没有形成预算结构。检查点应是可选编排能力，不升级成所有图纸必须通过的固定串行流程。

### 3. 下一批用匹配条件的小对照验证方法，不沿用旧分数作成功标准

建议在本轮 sm24 恢复之外另开一个小实验，先只比较一张未参与调试的平面：相同模型、相同原图、相同总时间和相同用户元数据，一臂用当前整案自由方式，一臂用“图证账本 + 程序性检查点”。若不打算在真实产品输入中提供 thermal-zone 数，两个实验都应去掉它；若保留，则两臂同时提供并明确它是用户约束。生成阶段不放 GT、旧正确 reading、正确房间数或坐标。

评价在产物保存后独立完成，首看源空间是否错拆/错并、实体隔墙和真实开放段是否正确、门窗是否保留且连接合理，再记录时间、token、人工打回内容和建模后修订次数。之后至少换一种画法/布局复测；同一张图的缩放或换色只能测抗扰动，不能证明泛化。07-08 mini 的 6/7 平面窗和 07-07 sm24 的人工好评都应保留为历史限制，不作为新实验的通过门槛。

## 三、结论边界

历史证据支持的是一种工作原则：模型负责认图意和处理歧义，确定性工具负责量、算和留痕，装配前后都有可质疑的检查点。它不支持把旧坐标、8/7 个 zone 先验、固定颜色阈值、单线表示或多 Agent 接力写死进产品，也不支持把旧 reading 高分换算成当前轻量 BIM 成功率。

## 本次后续实测与入口

已做一张原平面的 [Haiku局部观察](../2026-09-13_sm24_plan_observation/README.md) 和 [同题Sonnet对照](../2026-09-13_sm24_plan_observation_sonnet/README.md)：前者图意严重错、后者超时，均未送入BIM。不是本页建议的完整历史工序复现或同模型方法消融。`run_plan_probe.py` 保存问题与调用方式，支持`--model haiku|sonnet --out 新目录`；本次两臂发生在子截止时间修复之前，未来重跑会使用修复后的时间反馈和简短剩时提示，原请求/回执/清单保留旧条件。
