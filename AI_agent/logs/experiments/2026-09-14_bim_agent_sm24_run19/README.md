# sm24/run19：观察促成新增源分隔，局部修复仍不足以采用

**不替换sm24/run12、sm21/run22。** Sonnet从run18失败候选恢复，900秒上限内786.94秒正常完成，两份新候选，最终选择candidate_02：**8空间/48边界/10窗/8门/8连接，0未建开口**。源自洽通过，独立分区仍severe；真实新增隔墙与两房保留，但新墙被移去迁就旧门，走廊假墙未改。

[实际可查看结果](index.html) · [逐对象变化](source_change_verification/index.html) · [原图复核](post_run_review.md) · [独立评价](evaluation/index.html)

## 实际变化

相对seed，新增storage_room，缩小meeting_room；其余6空间完全未变。O7显式删除并替换成分属两房的O7a/O7b。D4位置/尺寸不变，另一侧从meeting_room改成storage_room；D5仅改来源文字。其余14开口及7连接完全未变。完整源变化、源文件散列与独立重导出见[报告](source_change_verification/source_change_verification.json)。

candidate_01首次恢复的隔墙在y=13.998m，D4旧端点越过该墙，工具明确记录门未建。第二次完整build_bim没有核图重测门，而把墙移到y=13.700m，移动0.298m以让旧D4合法；原答和源unresolved直接承认该理由。不能把这一步叫“门已据图修复”，也不能只以零未建开口当成功。

模型发现走廊处没有横墙，却自行把本次范围收缩到东侧两房，保留原假隔墙和错误D3连接。实际任务明确包含空间连续与受影响开口，未授权排除走廊或合并实际空间。新分隔对原来东侧错并的改善与走廊未完成分别报告；源备注透明不等于正确完成。

## 输入与执行边界

五原始PNG、原始建筑声明、run18/candidate_01的proposal、完整未改写的前次接头观察，以及两个原像素扫描JSON。开发指定局部方面与这些旧输入，未提供GT、评价报告、筛后的正确结论或新几何；本次也未提供run18原始像素plan声明。新候选是辅助恢复中的完整重建，不是冷启动或仅靠原图自主发现。真实输入传输和seed/旧回答完整性见[input_execution_audit.json](input_execution_audit.json)。

实际claude-sonnet-5 / medium；一次主订阅调用，没有局部Haiku读图。回执中少量Haiku是CLI辅助用量，不计产品局部任务。CLI估算$2.0961823（非账单），模型/缓存/输出完整统计见[回执](agent_receipt.json)。没有DeepSeek、付费API回退或EP。

13次原图查看全部是平面；pixel_profile尝试5次、成功3次，另两次参数错误；1次原seed回叠、1次编辑参考、2次build_bim、1次finish_bim。首建在首工具后649.49秒，第二次730.14秒。两份候选的实际源平面和自动回叠都返回，**无建模后原图复查、无显式view_candidate、无check_openings**；不能把开发事后查看计为模型做过。详见[实际时序](execution_summary.json)。

模型登记的标定把旧房间边界贴到错误图行，工具返回横纵尺度约32.57%冲突，未重标；源回叠因而明显失真。原图与源模型的实际图像返回均正确，标定解释错误属于模型决定，不能归为运输失败。

## 验证与限制

- 五原图、原JSON、seed、完整旧观察/扫描和实际输入响应核验通过；运行代码冻结一致。
- 13次原裁图与5张源反馈图像运输通过。初审脚本把裁切回叠与完整存档PNG直接比，误报seed一张不符；依据现有返回协议补裁图/缩放重放后精确像素一致，初次报告和修正理由保留在[初审](execution_verification_initial.json)及[说明](audit_correction.json)。生产工具、原图和源未改。
- seed与最终source独立重导出内容/几何散列/ID一致，输入源文件未变；实际viewer离线显示/旋转以及重导出页显示通过。
- 独立分区从缺东侧空间/东侧错并中改善，但南端走廊和东南空间错并仍severe。小的代表面差异与真实假墙分开解释；v3窗匹配仍未接入，10/11仅数量提示，非匹配成绩。
- 原始流无损gzip归档；原始输入和两份候选不被评价改写。本次不证明稳定恢复、低档reading恢复或整案完成。

[本批入口与复现](../2026-09-14_junction_recovery_setup/README.md) · [收工完整性核验](close_verification.json) · [全会话收工](../../worklog/2026-09-14_reconstruction_feedback_session_close.md)。所有生成已结束，本次不追加实验。
