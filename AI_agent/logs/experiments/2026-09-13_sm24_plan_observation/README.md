# sm24 平面图证账本探针（Haiku）

本目录记录一次有界、只读的方法探针：给 Haiku 一张 sm24 原始平面图，只要求先观察实体墙、开放段和门标记，并输出带像素依据的小型图证账本。它没有拿到旧候选、正确房间数、正确坐标或 GT；问题由开发助手编写，因此属于**辅助局部方法试验**，不是历史 07-07 方法的完整复现，也不是生产 BIM Agent 的公平 A/B。

## 结果

调用在传输和隔离层面成功，图意结果严重失败，**不得送入 BIM 生成或作为正确几何**。模型把门窗使用的青色线当成主要隔墙，进而给出了含多条虚构贯穿墙的七条隔墙、六个门标记和八个区域声明；其“PARTITION LAYOUT COMPLETE”“CONFIRMED”与真实工具回传相冲突。

独立逐项核对见 [evaluation/observation_review.md](evaluation/observation_review.md)。

## 可复核的运行事实

- 实际模型：`claude-haiku-4-5-20251001`；只读；240 秒上限；129.98 秒完成；24 turns；return code 0。
- 输入只有 `1f_view.png`，790×1111。隔离输入图 SHA-256 为 `47cf5eeeb574d0107c15898c389e4397123a34ddcefcd8c8bc61a8fd57f34350`，与原始图和外层拷贝一致。
- 隔离环境只暴露 `inputs`、`view_image`、`pixel_profile`、`map_dimension_chain`、`map_pixels`。实际调用为：`inputs` 1 次、`view_image` 16 次、`pixel_profile` 3 次；没有调用两个坐标映射工具。
- 三次剖面分别得到：青色候选框 0 个匹配像素；灰色大框为许多离散 run 而非连续整墙；白色框为两个离散 x-run。最终答案仍把青色写成主隔墙，并称灰色外墙得到“continuous”验证。
- `response.json` SHA-256 为 `1c49b1c684630d5f2b93e57e77c6ba2e7b673fb50aa87b758db8e297bfb3ba4a`。结果字段是“说明文字 + Markdown fenced JSON + 未决事项”，并非可直接消费的纯 JSON 账本。
- 账单字段仅作运行记录：5668 input、10997 output、158924 cache-read、14858 cache-create tokens，估算 `$0.1062614`；它不说明图意质量。

证据入口：[请求](detail_01_request.json)、[原问题](detail_01/question.txt)、[输入清单](detail_01/inputs.json)、[真实工具日志](detail_01/tools.jsonl)、[原始流](detail_01_stream.jsonl.gz)、[回执](detail_01_receipt.json)、[原始回答](response.json)。

## 方法判断

这次结果反证了“要求结构化账本和像素坐标，模型自然会基于证据读图”。Haiku 确实多看了局部图并输出了更长的结构，但它先误判图层语义，又没有让工具的零匹配和离散 run 推翻假设，于是结构化格式只是放大了自信错误。调用次数和 JSON 字段数不能当作可追溯性。

这次也不能单独否定“先观察、再装配”的原则。与 07-07 历史流程相比，它没有中性候选预扫、逐候选处置、可引用的量测结果编号或外部程序性检查点；历史结果本身也只是辅助 reading，不是 GT 或 BIM 成功证明。

后续小实验应核对结论和工具记录是否一致：按需用确定性的中性线段/颜色分层辅助观察，保留每次量测及其对应声明。零匹配或离散 run 不能被写成“该次量测确认了整条连续墙”；但量测未检出不排除原图有墙，可另用可见证据或明确推断，并说明换方法的原因。账本宜能直接解析以便核对，不能把固定候选目录、颜色规则或纯 JSON 格式升级为所有图纸的生成门槛。


实际图像重放与只读输入隔离检查见 [execution_verification.json](execution_verification.json)，全部返回图像逐像素一致；事件流已无损压缩，往返校验及原流摘要见 [stream_archive.json](stream_archive.json)。这些检查只证明运输/隔离，不证明图意正确。
