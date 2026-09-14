# sm24 完整区域轮廓观察：Haiku仍错读，未采用

[原观察](observation.txt) · [原图与编号区域](detail_01/pixel_region_overviews/overview_001.png) · [原图复核](visual_review.md) · [输入/运输核验](execution_audit.json)

原平面＋开发指定的“区域轮廓→分隔取舍”问题，Haiku/240秒上限，135秒完成。实际14次原图查看、13次成功轮廓、1次总览，另6次种子选择错误保留。仍把外部尺寸带当走廊，并把实体隔墙与门相连的多个房间并成大空间，**不能采用**。准确返回的东北小房间轮廓也未改变其合并结论。

未提供建筑JSON、旧模型、旧观察、正确数量、坐标或GT；没有运行中补答案。该输入限定是局部方法探针，与正式建筑声明接入分开，不代表产品不接声明。没有源BIM生成或修改，也没有把结果送入后续run16。

输入隔离及14原图/14派生图的实际运输一致。运行期间仅模块docstring改变，运行AST不变；起止源码和[差异核验](code_change_audit.json)均保存，原“文件未冻结”标记不改。CLI估算$0.1515004，非账单。不同范围与模型不作降本消融比较。

复现：[observe_partitions.py](../2026-09-14_reconstruction_input_setup/observe_partitions.py)；核验：[verify_observation.py](../2026-09-14_reconstruction_input_setup/verify_observation.py)。
