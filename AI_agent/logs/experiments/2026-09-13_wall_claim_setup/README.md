# 09-13 局部读图与分区恢复入口

本批只推进还原建模。模型走Claude订阅，无DeepSeek/付费API/EP。完整过程与结论见[工作记录](../../worklog/2026-09-13_reconstruction_annotation_recovery.md)。

| 入口 | 输入与预算 | 实际结果 |
|---|---|---|
| [run_review.py](run_review.py) | 原平面、按顺序选出的两条旧Haiku竖墙声明及全部原量测；Sonnet240秒 | [215.94秒返回](../2026-09-13_sm24_wall_claim_review/README.md)，替代墙段仍错，未接BIM |
| [run_dimensions.py](run_dimensions.py) | 原平面、两组分段标注转录；默认Haiku180秒 | [109.61秒返回](../2026-09-13_sm24_dimension_observation/README.md)，错链/错数字，未接BIM |
| 同入口 `--model sonnet --out <新目录>` | 同原图/问题，显式medium180秒 | [41.59秒返回](../2026-09-13_sm24_dimension_observation_sonnet/README.md)，两组数字/顺序正确，端点仍近似 |
| [run_bim_recovery.py](run_bim_recovery.py) | run02候选、五原图和完整Sonnet观察原文；Sonnet medium480秒 | [run03](../2026-09-13_bim_agent_sm24_run03/README.md)保存8空间，西侧改善、整案仍失败 |

从仓库根以 `python <入口路径>` 启动。固定输出入口拒绝覆盖已有run；复现实验须在新入口/新目录运行，原始输入与旧结果不改。`run_dimensions.py`支持直接指定新目录；其余脚本固定输出目录不能直接重跑已有批次。

[verify_views.py](verify_views.py)用于只读观察完成后的原图哈希、请求/问题、只读边界与实际返回像素核验；传入对应run路径。源BIM运行的运输复核复用[verify_execution.py](../2026-09-12_sm24_delegation_setup/verify_execution.py)，已兼容可选放大，GT评价另在生成结束后执行。运输检查不是图意验收。

[历史裁图复核](crop_view_review.md)解释显示差异及限度。[display_preview](display_preview/inputs.json)是当前Toolkit默认/4倍显示的离线预览，未调用模型、不含候选；像素量测仍取原图。最近邻缩放属于确定性显示工具，不创造图像证据。
