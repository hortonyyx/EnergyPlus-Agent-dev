---
name: pre-run-config-confirmation
description: 每次正式跑 case 前必须先跟用户确认配置再动手，别自己拍板往下走
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1d115693-1854-4020-aa2f-deef499bb008
---

每次正式跑 case（flow / baseline run）**动手前必须停下来跟用户确认配置**——这是 SOP 硬点，不是可选。new_case_guide.md §2 Step 2「定模型配置+建 run 目录 →（跟用户确认一次）」+ Step 3「定范围+judge 开关+3 个人工校验开关 →（用户拍）」都带显式用户确认门。

**我犯过的错（2026-07-05 Haiku 降级测试）**：直接建 run 目录 + 配置 + 冷启 Haiku 子代理读图，全程没问用户一句。用户纠正「按流程每跑前你需要问我配置的哇，怎么又忘了」。

**Why**：跑测涉及模型选择/范围/judge 与人工校验开关/是否 EP+record，这些是用户要拍的决策点，不是有默认就能自走的；且降级测试这类实验用户可能有临时想法（先看 reading 质量再决定下游、改判卷尺等）。

**How to apply**：建完 run 目录草案后**停**，用 AskUserQuestion 把「模型配置 + 范围 + judge/3 人工校验开关 + 是否 with-ep/record」摆给用户拍，拿到确认再启动 flow / 冷启执行器。reading 子代理也算执行器，属确认后才启。参见 [[standardize-test-flow-and-judge-arch]]。
