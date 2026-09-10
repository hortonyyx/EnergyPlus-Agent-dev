# 2026-09-10：sm24 外立面开口回查重放

这是对 `2026-09-10_partial_inference_sm24_run01/candidate_01` 保存观察的离线、确定性诊断。原始 run、原图和原回查 JSON 均未修改；本目录不把人工声明的范围写回原运行，也不评价原图保真。

重放时把七份保存的 `observations` 分别人工声明为 `South`、`North`、`North`、`South`、`East`、`East`、`West`，对应原回查 `review_001` 至 `review_007`。另补一份人工声明的 `West` / `door` 完整空观察（`marks=[]`），以验证零开口立面不会被已建对象数量掩盖。方向由源 BIM 中开口的 `host_boundary_id` 和实际墙面外法向计算，不读取图片文件名。

| 类别 | 北 | 南 | 东 | 西 | 汇总 |
|---|---:|---:|---:|---:|---|
| 门 | D_N1 | D_S1 | D_E1 | 空观察 | 四面均与所报观察一致 |
| 窗 | W_N1 | W_S1, W_S2 | W_E1, W_E2, W_E3 | W_W1..W_W5 | 四面均与所报观察一致 |

每份有实际对象的观察只匹配其宿主方向的开口，不再把另三面的模型开口报为 `unaccounted_model_opening`。若删去西向门的空观察，门的整层汇总为 `partial`；因此本次一致只说明人工声明范围下的源模型与保存观察相符。`drawing_fidelity` 始终为 `not_evaluated`，不能据此宣称原图保真或模型已完整。

重放使用当前工作树的 `review_openings` 与 `summarize_delivery`，输入为原 run 的 `source_model.json`、七份保存观察和保存图片元数据；未调用模型、网络或付费 API。

本次实际回执保存于 [replay_results.json](replay_results.json)，可用 [replay.py](replay.py) 对不可变原 run 重新生成。脚本要求显式给出原 run 和新的输出路径，避免误写入原运行目录。
