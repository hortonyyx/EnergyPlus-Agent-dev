# 当前 `view_image` 与历史 `crop_zoom` 的显示差异复核

本复核只读代码、已保存工具记录和历史产物。没有调用模型、没有修改正在运行的墙段返工，也没有把评价、正确墙位或房间数放进其输入。

## 可证事实

当前的 `Toolkit.view` 在 [`scripts/tool_scripts/run_bim_agent.py`](../../../../scripts/tool_scripts/run_bim_agent.py) 的 `view` 方法中，先按原始像素裁剪，再只调用 `thumbnail((1600, 1600))`。Pillow 的 `thumbnail` 只缩小、不放大。因此任意小裁剪按原大小返回；元数据的 `original_pixels_per_returned_pixel` 为 `[1.0, 1.0]` 并不表示放大后的查看。

这不是抽象推测，09-13 实际只读观察的日志给出了同一行为：

| 运行 | 原图裁剪 | 实际返回 | 结果 |
| --- | --- | --- | --- |
| Sonnet 墙账本探针 | `[390,190,420,260]`，30×70 px | 30×70 px | 未放大；`coordinate_grid` 不显示。 |
| Sonnet 墙账本探针 | `[380,850,480,900]`，100×50 px | 100×50 px | 未放大。 |
| Haiku 墙账本探针 | `[240,275,620,310]`，380×35 px | 380×35 px | 未放大。 |

来源分别为 `AI_agent/logs/experiments/2026-09-13_sm24_plan_observation_sonnet/detail_01/tools.jsonl` 与 `AI_agent/logs/experiments/2026-09-13_sm24_plan_observation/detail_01/tools.jsonl` 的 `view_image` 元数据。两臂对同一 790×1111 原图均实际返回了多条窄而原始尺寸的裁剪；Sonnet 的最后一张 30×70 图尤其直接。

历史的确定性 `crop_zoom` 则不同。`src/agent/reading/cv_toolbox/tools.py` 中 `_prepare_image` 对 `scale != 1` 调用 `resize(..., Image.Resampling.NEAREST)`；`crop_zoom` 将该放大后的 PNG 写出，并在 sidecar 记录 `source_to_local` / `local_to_source` 换算。它没有改原图，也没有把放大后的局部坐标伪装成原始坐标。

保存的历史产物表明确实使用过该能力：

- `AI_agent/logs/experiments/2026-08-15_reading_restart/D1_cv_evidence/1f_view/cv_evidence/1f_view/004_crop_zoom.json`：原图 bbox `[1140,190,1220,260]` 为 80×70 px，`scale=4`，生成 `crop_size_px=[320,280]`；对应 PNG 同为 320×280。
- 同目录 12 个保存的 `crop_zoom` sidecar 有 1× 三个、2× 两个、3× 两个、4× 五个。09-09 保存的一次读图也实际使用 4×：300×120 px 变成 1200×480 px。
- `crop_zoom` 的实现追溯到提交 `e3ec9aec`（07-06）。本工作树没有可直接打开的 07-07 原始 `crop_zoom` sidecar；历史报告把 07-07 的多次逐候选放大核验作为过程事实，但本复核不把没有保留的图像呈现细节补写成直接证据。

当前 `pixel_profile` 是另一回事：它对原图裁剪后的 numpy 像素计算，没有显示缩放，也没有理由因显示放大而改它的输入或数值结果。

## 可得出的范围

存在一个明确的图像使用差异：当前 readonly MCP 能裁剪但不能在返回给模型前放大细节；历史 CV 工具可用最近邻生成 2×–4×的局部视图，并保留精确的原图坐标变换。对 30×70 这类图，二者的视觉呈现显著不同。

这不能证明显示大小是 Haiku 把青色窗/门线误当隔墙的根因，也不能证明它会让 Sonnet 在 240 秒内交付。那两次失败还包含图层语义错误、工具反证未被采纳、无阶段性交付等独立事实；历史好 reading 也不是一个可归因到单变量的无监督对照。

## 最小通用方案（随后已实现）

仅给现有 `view_image` 增加可选的展示参数，例如 `display_scale: float = 1.0`：

1. 保持默认 `1.0`，所以现有调用、原图、裁剪语义和返回大小完全不变。
2. 对显式请求且小于展示上限的裁剪，在 `crop` 后用 `NEAREST` 放大；上限仍为 1600 px。30×70、`display_scale=4` 会返回 120×280，原图 bbox 仍是 `[390,190,420,260]`。
3. 元数据继续把 `box_original_pixels` 作为唯一可回写坐标；补充 `display_scale`，并按实际返回尺寸计算 `original_pixels_per_returned_pixel`（上述例子为 `[0.25,0.25]`）。这样网格、后续裁剪和像素引用仍回到原图帧。
4. `pixel_profile`、源图文件、候选、评价输入和默认视图不改；这只是按需的呈现选项，不新增质量门、候选推断或模型调用。

实现时应补两个小测试：默认小裁剪仍为 30×70；显式 4× 返回 120×280 且 bbox 与原图坐标换算保持一致。可以在当前 `view_image` 参数上完成，无需恢复旧 CV pipeline、写临时图或把固定图层规则搬入总 Agent。

随后实现、离线6项验证及真实原图显示/模型使用见[本轮记录](../../worklog/2026-09-13_reconstruction_annotation_recovery.md)。历史和当前失败记录未改，放大对识读效果的独立因果仍未验证。
