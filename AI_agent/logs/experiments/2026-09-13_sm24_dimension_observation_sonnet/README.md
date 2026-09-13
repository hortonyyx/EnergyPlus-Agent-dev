# sm24 外层分段尺寸链转录（Sonnet medium）

本目录是同一张 sm24 平面、同一中性局部问题的 Sonnet 观察。它只读取左侧与底部的目标分段尺寸链，并与单根总尺寸和门窗细链区分；没有旧输出、正确数字、BIM 或 GT。相较此前 Haiku run，本次不仅换成 `claude-sonnet-5`，还显式设置 `effort: medium`，因此不能写成只有模型不同的严格 A/B。

## 结果

**目标链的文字、顺序、链身份和闭合均可作为待核标注证据；单位和像素定位不能直接当精确几何。** Sonnet 正确读出左侧四段 `4060, 2940, 4940, 8060` 和底部三段 `4180, 1640, 4180`，分别闭合到可见总尺寸 `20000`、`10000`；也正确区分了更靠建筑的两条门窗细链。原图独立核对没有发现这些数字或顺序错误。

它给出的坐标精度较低：部分 `approx_pixel_boxes` 实际覆盖整段跨距而非紧贴文字；左侧首段端点约写成 y160/290，与可见尺寸端点仍有数像素差，并把墙交点含糊称作 jamb。输出已经声明墙面、轴线或门垛的 reference face 无法确定，因此这些位置只适合回图定位，不能直接标定 BIM。

独立逐项核对见 [evaluation/visual_review.md](evaluation/visual_review.md)。

## 可复核的运行事实

- 实际模型 `claude-sonnet-5`，`effort: medium`；179.87 秒上限；41.59 秒完成；7 turns；return code 0。
- 图像 SHA-256 为 `47cf5eeeb574d0107c15898c389e4397123a34ddcefcd8c8bc61a8fd57f34350`，与 Haiku run 一致。两臂原问题 SHA-256 均为 `56e7fb1aece6e91602923217ca007fe9dbc0de5bf0be4e314d66340699088430`；从 request 提取的完整 prompt 和 system prompt 哈希也分别相同为 `556866bda5702fe566744a76ce9e039bfe47d676e64f8ab210eb831110ba2d67`、`b0b0fa617bd4e0345c4a25b74ff0e2d355a915cd18defed02ab0b814522003d7`。
- 实际工具调用：`inputs` 1 次、`view_image` 3 次、`map_dimension_chain` 2 次；原始 stream 没有工具报错。两次局部图均实际以 2× 返回，足以辨认目标文字。
- 看图剩余时间为 172、163、163 秒；模型随后完成两次纯算术并交付，没有逼近 deadline。
- `response.json` SHA-256 为 `25fba9d03b8f983836fcbfa996a964eba502a4ab2adf4d3c4fa43383cef02756`。结果是可解析的 fenced JSON，约 269 个空白分词；没有代码块外解释，但仍需提取 fence 才是纯 JSON。
- 回执估算 `$0.1034278`。`modelUsage` 另记录少量 Haiku 用量（798 input、20 output），而实际模型和最终消息均为 Sonnet；这里只记录回执事实，不推断内部用途。

证据入口：[请求](detail_01_request.json)、[原问题](detail_01/question.txt)、[输入清单](detail_01/inputs.json)、[工具日志](detail_01/tools.jsonl)、[原始流](detail_01_stream.jsonl.gz)、[回执](detail_01_receipt.json)、[原始回答](response.json)。

## 与 Haiku 的有限对照

Haiku 在同题中误选底部内链，并把左侧首尾数字读错；Sonnet medium 识别了正确层级和全部标签。这支持“此局部标注任务在本图上存在明显模型/effort能力差异”，不证明模型对其他图纸或几何语义普遍可靠。两臂运行路径也不同：Haiku 用 7 次看图、一次像素剖面并发生一次无效图片名错误；Sonnet 用 3 次看图后直接算链。闭合检查在本次与原图文字相互支持，但 `map_dimension_chain` 仍只做调用者输入的算术，不能单独认证 OCR。
