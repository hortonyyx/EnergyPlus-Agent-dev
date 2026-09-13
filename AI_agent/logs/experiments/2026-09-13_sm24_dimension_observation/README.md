# sm24 左侧与底部外层分段尺寸链转录

本目录记录一次 Haiku 只读局部转录：输入只有原始 `1f_view.png` 和中性任务，要求区分左侧、底部的外层分段链、单根总尺寸及靠建筑的门窗间距链。没有旧输出、期望数字/数量、BIM 或 GT；结果只可作为待核标注证据。

## 结果

**完成了调用，但目标链转录失败，不可直接使用。** 模型读对了两条单根总尺寸 `20000`、`10000`，也准确抄出了底部靠建筑的七段门窗链并算得 10000；但任务明确要求的是另一条外层分段链。它把被要求排除的内链命名为 `outermost chain`，真正的底部分段链完全漏掉。左侧目标链只抄对中间两段，首尾两段读错，像素盒也没有覆盖相应文字。

独立图文核对见 [evaluation/visual_review.md](evaluation/visual_review.md)。

## 可复核的运行事实

- 实际模型 `claude-haiku-4-5-20251001`；179.86 秒上限；109.61 秒完成；14 turns；return code 0。
- 图像 SHA-256 为 `47cf5eeeb574d0107c15898c389e4397123a34ddcefcd8c8bc61a8fd57f34350`，与此前 sm24 原图一致。
- 成功工具调用：`inputs` 2 次、`view_image` 7 次、`pixel_profile` 1 次、`map_dimension_chain` 2 次。原始 stream 另有一次失败的 `pixel_profile`：模型使用不存在的图片名 `left_vertical_dimensions`，收到“choose an exact image name from input inventory”，随后改用 `1f_view.png` 重试成功。`tools.jsonl` 只保存成功调用。
- `display_scale` 实际生效：左侧长裁图请求 4×，受 1600px 返回上限约束实际为 2×；底部裁图实际约 3.56×；左侧局部裁图达到 4×。失败不能归因于工具完全没有放大。
- 看图返回的 `remaining_seconds` 从 173 递减到 91；本 run 在截止前约 70 秒交付。
- `response.json` SHA-256 为 `478e62d9401ff41d85f75c3403aa7afe1cd3de4d9dee2dd5169244a5d63066a5`。内部 fenced JSON 可解析，约 174 个空白分词；外层仍带标题和说明，并非纯 JSON。

证据入口：[请求](detail_01_request.json)、[原问题](detail_01/question.txt)、[输入清单](detail_01/inputs.json)、[真实成功工具日志](detail_01/tools.jsonl)、[含失败调用的原始流](detail_01_stream.jsonl.gz)、[回执](detail_01_receipt.json)、[原始回答](response.json)。

## 方法判断

放大解决了字形可见性，却没有解决“数字属于哪一层尺寸链”。`map_dimension_chain` 只替模型对自行输入的数字做加法，回传还明确写着 `caller_supplied_dimensions_and_frame_not_independently_verified`；错误链恰好闭合总尺寸，反而让模型更自信。后续若继续，应先让每段标签绑定同一根尺寸线的相邻两个延长线端点，再允许求和，并在确定性检查中拒绝标签盒不覆盖文字、盒中心不沿同一尺寸线、以及把已排除内链称为目标链的结果。本次原文不应进入 BIM。
