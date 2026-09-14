# 事后墙网诊断：不作为还原候选

[原图回叠](post_run_inspection/source_on_original.png) · [实际源平面](post_run_inspection/source_plan.png) · [诊断查看器](candidate_01/viewer.html) · [独立分区](evaluation/index.html)

开发在 run17 结束后复制第二份模型声明，墙位、外轮廓、种子和标定原样保留，**全部17个开口显式排除**。完整原声明在 [original_declaration.json](original_declaration.json)，门窗及逐项宿主检查在 [excluded_openings.json](excluded_openings.json)。源假设/未解决项同样标记缺全部开口；不是模型完成或选定的候选，不得作为恢复基点。

8空间、48边界，源自洽通过，独立分区 severe。北部连续空间被错拆，走廊边界和东南折角缺失。房间数相同不代表还原正确；本诊断不评价门窗数量/高度，未建0只是输入已明确排除全部开口，不是原门窗问题解决。

零模型调用；通用 Toolkit 的 provenance.generator 固定文本仍为 Claude subscription tool loop，其 mode 和输入清单、源假设明确标记 developer_post_generation_wall_only_diagnostic，不能据这段通用文本误计为订阅生成。源重导出一致、离线加载/旋转通过；GT和本图均在原运行后使用，没有回传模型。
