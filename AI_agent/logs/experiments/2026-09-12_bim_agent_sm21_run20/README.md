# sm21 保留六个二层门的宿主修复 run20

**六个二层门及其房间—走廊连接真正建成；当前14空间/12窗/14门、14连接。** [交付](delivery.html) · [BIM](candidate_01/viewer.html) · [二层平面](candidate_01/plan_F2.png) · [独立核对](independent_review.json)。窗口问题未修，整案仍未完成。

## 条件与修订

代码 `5fed31a5` 将开口实际z和源空间上下界送入原宿主失败报告。由run19/candidate_02的原proposal恢复，保留当时六条未建门，不从删除后的candidate_03继续。[启动脚本](../2026-09-12_wall_host_setup/run_opening_recovery.py)只指定修复宿主失败并保留可见门洞，不供正确高度/门位/GT。九份实现与六原图摘要冻结在inputs.json。

Claude订阅一次，claude-sonnet-5/medium主模型，32.32秒正常结束，上限300秒；CLI估计$0.2798949，非订阅账单。CLI还报告辅助Haiku4.5的18输出token，无review_detail、DeepSeek、付费API或EP。

模型先读取seed与新诊断，再一次提交六条update_opening，将原z=0..2.1m改为3.0..5.1m。它随后查看修订后的二层平面并选定candidate_01。没有删门、改房间、移动门平面端点或改变两侧连接对象。六门全部实际建成，未建数从6降为0，连接从8升到14，源几何检查通过。

## 核验与限制

[产物核验](artifact_verification.json)通过九实现/六原图摘要和源哈希；只新增六门与六连接，原房间、边界、窗和已建门不变。[逐字段独立核对](independent_review.json)确认14个原门声明都保留、六门原平面端点与两侧空间不变。不能将这一修复计为run19原冷启动成功。

本次没有重看原图，只根据实际源楼层和既有门高假设修正绝对坐标。操作source_refs声称图上支持相同门高，没有新图像查看支撑；2.1m门高与3.0m二层基准仍是继承的声明，不能写成重新量测或实际楼层高度已确认。门宽/平面位置仍有近似，窗仍12个且原配对问题全部保留。

[实际返回平面核验](candidate_view_verification.json)确认模型收到的1张二层平面与保存图像一致。主助手已查看；[离线交付](browser_check/summary.json)和[修订二层显示/旋转](browser_floor_2/summary.json)通过，无页面错误、失败请求或外网。无标定回叠或正式开口回查。事件流无损压缩并留摘要。

源空间与窗同run19，复用其[独立平面分区pass与窗4/15匹配](../2026-09-12_bim_agent_sm21_run19/evaluation/index.html)，不重复GT评分。门的实际建成与连接新增另按源对象核实。后续从此原图冷启动派生分支核对立面楼层标高、补漏窗和修窗位置/尺寸；run18较完整的旧候选继续保留为独立对照，不混称已合并成功。
