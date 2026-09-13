# 东侧恢复与编号区域定位实验入口

本目录只保留开发编排脚本和原图工具预检，不是固定产品流程。完整结果见[工作记录](../../worklog/2026-09-13_reconstruction_region_localization.md)。

| 脚本 | 实际范围与结果 |
|---|---|
| run_recovery.py | run07→run08，Sonnet medium东侧恢复；错移东南门，未采用 |
| run_northeast.py | run07→run09，Sonnet low东北局部；未改源，错误自证不采信 |
| observe_northeast.py | 独立Haiku完整房间trace，目标定位失败/超时，未应用 |
| observe_overview.py | 新编号总览下Haiku仅定位探针，正确R21；没有trace或BIM修改 |
| audit_source.py RUN | 结束后核新旧源对象、门宽高、覆盖守恒和局部操作/同输入导出重放，不读GT |

运行目录已经存在，重做须先更改脚本中的输出到新目录，不覆盖本轮结果。旧脚本若用最新工具重跑并非历史代码复现；实际运行脚本快照保存在各run的implementation，run08/run09摘要已与输入清单核对。

original_overview.png/json保存开发预检的默认20候选：目标小房间被尺寸标注组件挤出前20。original_overview_40.png/json保存改成40后的39候选，未截断。此默认调参已明确计入开发介入，没有将正确R21/seed写进模型输入。

实际离线浏览器复用既有环境，命令前缀为`PLAYWRIGHT_BROWSERS_PATH=/tmp/ep-bim-browser-qa/browsers /tmp/ep-bim-browser-qa/bin/python`，查看/旋转脚本为`../2026-09-10_autonomous_recovery_setup/browser_check.py`，交付页状态核验脚本为`../2026-09-10_overlay_feedback_setup/browser_delivery_check.py`。首次缺浏览器目录变量导致启动失败，补变量后通过，未安装新环境。

独立评价复用`../2026-09-12_sm24_delegation_setup/evaluate.py --run RUN`，只在summary落盘后读取GT。run09源空间未变，复用run08 seed有效分区结果，不重复全量。所有模型输入只含所选原图、当前scope及显式指定的旧proposal，不包含该评价结果。
