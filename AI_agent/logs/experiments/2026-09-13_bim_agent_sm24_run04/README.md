# sm24 run04：有界委派与局部走廊修复

已保存并选定 **8空间/52边界/11窗/11门/11连接** 的新源BIM。走廊两侧分界从3.767/5.843m调整为4.18/5.82m，独立对照确认改善；东侧分隔和东南转折仍错，整案未通过。

[交付页](delivery.html) · [直接查看](candidate_01/viewer.html) · [源平面](candidate_01/plan_F1.png) · [独立对照](evaluation/index.html) · [原图/源/观察复核](evaluation/visual_review.md)

## 输入与角色

原输入仅run03的proposal加五原图，开发助手给通用的“选择一个未解决平面问题、协调局部观察、用代码修改并查看”任务；没有提供GT、开发评测坐标或前置观察原文。Sonnet自行选底部尺寸链与走廊关系，实际发起一次90秒上限Haiku任务。父问题预填两条链数字，所以不是Haiku独立数字转录实验；子目录仍与seed/评价文件隔离。完整[父请求](agent_request.json)、[子请求](detail_01_request.json)与[实际子问题](detail_01/question.txt)保存原文。

主调用Sonnet medium为204.12秒，包含Haiku34.35秒；主调用预算300秒，保存候选时约108秒剩余、finish时约102秒剩余。Sonnet输出13670 token；两调用CLI估算合计$0.6598474（非订阅账单）。父时长扣串行子时长为169.77秒，仍含工具/启动开销，不等于纯思考时间。详见[runtime_audit.json](runtime_audit.json)。

上次run03主调用469.54秒、Sonnet输出38714 token、CLI估算$1.282029；本次数字更低，但输入seed、纠错范围、代码和预算均不同，不能据此断言Haiku委派造成降本，也不证明已实现Sonnet只调度。

## 实际修改与保留问题

- 代码`reshape_spaces`一次改7个已有空间的polygon和包围盒，Reception不变，保留整个连续走廊。七扇走廊侧门显式平移到新宿主线，宽高不变；全部窗物理几何及门/窗/连接ID保留。
- 接待区通走廊的门另行从x=3.90..4.80改为4.37..5.64m，宽0.90→1.27m，是模型显式核图后做的修改，**不是全部门宽保持**。精度/原图依据以后评为准。旧Office1门宽0.74m未在本轮修复。
- 源自洽通过、0未建/不支持开口；独立分区仍severe，内部缺失/多出边界长度由约40.086/40.065m降至15.560/16.494m。该线差统计不是错误墙总长度，也不作为全案通过依据。
- 生成期实际查看新源平面并finish；没有开口回查、没有原图回叠。图面端点/墙面基准尚有未核，门状态和东侧纵向分隔仍未解决。

## Haiku效果必须单列

Haiku只看两张裁图，没有像素量测/尺寸累计，返回内分界点约x385–390和505–510，明显偏离原图约400/460。Sonnet实际采用约399/460及原图标注，却把子答的“上方有墙”说成独立确认，甚至写入修改理由；该背书不能采信。工序运输和时限有效，局部reading仍未恢复，Sonnet仍承担主要图意裁定。失败子答全文保留，不以修对走廊把它改记成功。

## 核验

[execution_verification.json](execution_verification.json)核对父6张原图、1张实际源平面、子2张原图运输和子目录隔离，均通过；父1次虚构图名的pixel_profile错误也保留。两个事件流[无损压缩往返](stream_archive.json)已校验。

[楼层离线查看](browser_F1/summary.json)与[交付页](browser_delivery_check/summary.json)通过，0页面错误/外部请求，主助手实际查看原图、源平面和楼层截图。独立评价仅在生成结束后运行，实际输入摘要/几何变更见[source_change_audit.json](evaluation/source_change_audit.json)。

相关空间编辑/源生成17项、子任务预算/隔离6项检查通过；源码、介入范围、下一入口见[工作记录](../../worklog/2026-09-13_reconstruction_coordinator.md)。
