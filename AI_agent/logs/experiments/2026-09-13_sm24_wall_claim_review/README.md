# sm24 两条竖墙声明局部返工

本目录记录一次只读、局部的纠错探针。输入是一张原始 `1f_view.png`、上次 Haiku 账本按原顺序选出的前两条含 `VERTICAL` 的墙声明（P1、P6），以及上次三条 `pixel_profile` 原始记录。没有 GT、正确坐标、正确房间数、旧评价或生产候选。`prior_evidence_provenance.json` 明记 `contains_evaluation: false`；其来源 response 与 tools 哈希也已保存。

## 结果

实际 `claude-sonnet-5` 在 215.94 秒完成，没有触发 239.93 秒外层超时。它纠正了两项根本错误：旧青色测试为零不能支持 P1，青色弧是门符号而非主要墙线；P1 在 x≈307 从上到下连续的声明应撤销。但它给出的替代墙段仍有严重图意错误，P6 的修正中心甚至落到新剖面测试框之外，因此**本次结果不能进入 BIM 或候选恢复**。

独立逐项核对见 [evaluation/visual_review.md](evaluation/visual_review.md)。

## 真实运行事实

- 输入图 SHA-256 为 `47cf5eeeb574d0107c15898c389e4397123a34ddcefcd8c8bc61a8fd57f34350`，与前两次平面观察的原图一致。
- 成功调用：`view_image` 5 次、`pixel_profile` 6 次；没有坐标映射或其他工具。原始 stream 另有 2 次失败的 `pixel_profile` 尝试，模型把图片名写成并不存在的 `wall_check_x460`、`wall_check_x400`，工具均返回“choose an exact image name from input inventory”；模型随后改用 `1f_view.png` 成功重试。保存的 `tools.jsonl` 只记成功调用，不能据它说整个调用过程无错。前四次看图覆盖整图、两条声明所在的中央区域，最后一次再次裁看中央局部。
- 新剖面确实把灰色墙带作为候选：x=390–410 的横向聚合峰在 x=402；x=450–470 的峰在 x=457。纵向聚合还返回多个离散 y-run，而不是整段连续证据。
- `response.json` SHA-256 为 `645a56d5fb57d66e56f82369f22a4dddd9b7199f29053e6330b3e607b58ae8cd`。其中 fenced JSON 可单独解析且约 423 个空白分词，满足 600-word 上限，但外层仍是说明文字加代码块，不是纯 JSON 字段。
- 回执记录 14 turns，估算费用 `$0.3946355`。`modelUsage` 另出现少量 Haiku 记账（1791 input、16 output），而回执 `actual_model` 和最终消息均为 `claude-sonnet-5`；这里只记录事实，不推断该内部记账用途。

证据入口：[原问题](detail_01/question.txt)、[旧声明与旧剖面](prior_evidence.json)、[来源证明](prior_evidence_provenance.json)、[请求](detail_01_request.json)、[真实工具日志](detail_01/tools.jsonl)、[原始流](detail_01_stream.jsonl.gz)、[回执](detail_01_receipt.json)、[原始回答](response.json)。

## 剩余时间反馈

修复后的看图返回真实递减值：233、228、203、171、69 秒；此前 Sonnet 对照中该字段始终为 `null`。模型最终明确说剩余时间将尽并开始交付，在外层截止前约 24 秒完成，因此“字段已传递、这次没有再次超时”可验证。`pixel_profile` 的保存日志仍没有 `remaining_seconds`，最后一次可见时间值也只是上一轮看图时的 69 秒；单次先后变化不能证明修复是完成的唯一原因，更不能证明模型读图成功。

## 方法含义

把范围缩到两条可证伪声明、原样附上反证、要求先判 retain/revise/reject，确实比自由观察更容易让模型放弃错误的青色墙叙事。问题没有就此解决：`pixel_profile` 只是按指定颜色和轴做像素聚合，横墙交点、门弧、家具都可能进入同一 run；模型仍把“有匹配”直接解释成墙，并忽略测试框边界。下一次方法改进应先让工具结果携带可引用的覆盖率/方向含义，并用确定性检查拒绝“修正坐标超出量测框”“离散 run 被写成连续墙”等矛盾；本次不支持继续把这份文字答案喂给生产模型。
