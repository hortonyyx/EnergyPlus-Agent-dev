# sm24 外门窗高度续修

[四立面对照](index.html) · [最终模型](candidate_02/viewer.html) · [质量结论](assessment.json)

三外门底/顶从0/2.4m修正为0.2/2.6m，西侧四短窗顶从3.4m修正为2.8m。生成后独立对照的14个外开口高度均一致（最大差0.000011m，为参照小数残差），最终仍 **8空间/54面/11窗/10门/10连接**。平面分区、门窗位置与连接全部保持。整案尚未通过：原数厘米墙位偏差、内门高度假设和部分依据说明缺陷保留。

## 范围与真实执行

代码基点`0f7b18b2`，本轮没有生产工具或指引改动。输入为run03的`plan_drafts/draft_001/plan.json`、原五PNG与原建筑声明。开发限定全部外开口竖向基准/高度复核，并质疑继承的“门底0、西窗同北窗”假设；不提供正确高度、GT或预选裁图。只准改外开口z和说明，内门高度/全部平面几何保持，属于有开发范围指示的恢复，不是独立冷启动。

模型先构建`candidate_01`作为基线：继承墙网物理字段相同，assumptions文字有调整，不能称输入字节完全原样提交。实际50次`view_image`（东25/南15/北5/西5）后，经`revise_bim`形成`candidate_02`，查看全部四向实际源立面、检查开口并选择交付。没有`pixel_profile`、`view_pixel_profile`或`review_detail`调用。

Claude订阅requested Sonnet、actual `claude-sonnet-5`，medium effort，1200秒上限；665.27秒正常结束，输出56870 token，CLI估算$3.4968712（非账单）。回执Haiku属于CLI辅助，不是局部委派。没有DeepSeek、付费API或EP。

## 改动与解释分别核验

| 实际开口 | 原底/顶(m) | 当前底/顶(m) |
|---|---|---|
| 北、南、东三外门 | 0 / 2.4 | 0.2 / 2.6 |
| 西侧WW1–WW4四短窗 | 1 / 3.4 | 1 / 2.8 |
| 其余七外窗 | 已有值 | 保持 |
| 七内门 | 0 / 2.4（假设） | 保持假设 |

原图及最终四立面已由开发助手查看。外门洞口按含门楣亮窗的整组开口表达，没有另造窗或改变平面身份。所有源空间、墙面、开口宿主、状态、连接及XY保持。

**依据解释仍有问题：** 原East_view左竖链明确为1900/2400/200，模型未认出该直接门标注，将正确东门高度记作与其他门族的图形推断。终答及source_refs还称“thin horizontal-line scans”“逐像素量测”，实际工具只做裁图/网格查看，没有数值扫描记录；只能按视读估算记账，不把这些说明当作确定性量测已发生。错误/不充分的说明随原输出保留，开发审计另列，未偷偷改成更好的来源。

## 核验

- `scope_verification.json` / `verify_scope.py`：冻结声明及原图散列、candidate_02→candidate_01真实修订链、operations.json与MCP请求、父proposal摘要及最终source逐对象范围；`final_candidate.scope_pass=true`。
- `verification.json`：源/显示精确重放，8张有保存对应物的反馈图逐像素一致；普通原图裁看另列，不泛称50次都已逐张验证。
- `opening_comparison.json`：只在生成结束后引入GT。按原20000mm总长及保留原点显式平移[0,20,0]，原坐标结果同时保留，不拟合、不回写源。14个外开口高度一致不等于14个开口所有属性/整楼均通过。
- `frame_aligned_partition.json`：分区仍severe，继承约4—7cm墙位偏差。门窗高度修正没有改变这些分区残差。
- `browser_verification.json`及`viewer_verified.png`：离线查看、源散列、旋转、交付页通过；`report_view_verification.json`核四面报告的图和链接。
- `archive_verification.json`：22份实现散列匹配代码基点，流无损gzip往返。核验复用run01的`verify_run.py`、`align_evaluation.py`、`verify_browser.py`并指向本run；本轮无生产变更，不重复pytest全量。

**下一次必须从`candidate_02`用`--resume-candidate`继续。** 本run的`plan_drafts/draft_001/plan.json`只是修订前基线；若用它恢复会丢掉这次高度改动。三个有界续修已处理首轮主要漏墙/错并及门窗错误，下一项应评估较少开发指示下能否自行发现并完成同类修订，而不是按GT把厘米偏差逐点调绿。
