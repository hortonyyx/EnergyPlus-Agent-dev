# sm21方法参考A：429中断，完整质量未知

用户批准的[方法对照](../2026-09-28_dimension_first_comparison/README.md)第二条。B正常回执核过后独立启动；实际`claude-sonnet-5 / medium`，826.83秒、returncode1/is_error=true、api_error_status429。提供方回执报告用量限制，本批立即停止，没有重试、续查、换模或额外调用。中断不作为完整失败率或方法优劣证据。

仅保存首层`candidate_01`，7空间/14门窗/8连接；[查看中断草稿](delivery.html)。系统选择来源是`latest_saved_fallback_not_agent_selected`，不是工作模型最终选择；没有二层候选、装配、claim或finish。原始输入、40文件快照、公开调用与压缩原始流保留，实际A参考全文hash已核。

[中间状态复盘](interrupted_audit.json)记录：首份声明把15000/8000直接作为米制世界坐标，源轮廓实际15000×8000m，层高仍3m；南小窗已建，东侧走廊窗未建且原声明显式列为未复核；普通窗z1.6..2.6m、小窗1.5..2.4m，与原立面有差别。这些错误确实进入了中间稿，但运行尚未到最终复核，不能认定其完成后仍会保留。没有用缺二层的状态生成完整GT成绩，也没有生成`postrun_audit.json`。

41次公开工具请求，25次view_image、11次view_pixel_profile，未使用平面量测引用。源/显示精确重放、36张图像运输解码、25张实际原图返回字节/像素、单层浏览器源hash/旋转/离线检查通过。只有一层，双层切换明确记不适用；这些检查不能证明尺度或图纸理解正确。复现：`python -m AI_agent.logs.experiments.2026-09-28_dimension_first_comparison.inspect_run85`。

CLI估价$1.7869642，非订阅账单，原始用量留在`agent_receipt.json`。不修补或覆盖此草稿，不以它替代最终结果，不在额度恢复后自动补跑。
