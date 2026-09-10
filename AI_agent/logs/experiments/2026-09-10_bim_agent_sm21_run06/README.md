# sm21 独立冷启动：已生成可查看候选，原图保真仍失败

[查看入口](index.html) · [最终源 BIM](candidate_03/viewer.html) · [独立分区/窗比较](evaluation/index.html) · [事后原图复核](evaluation/visual_review.md) · [评价摘要](assessment.json)

本次仅提供六张原图和通用建模范围，没有 seed、正确数量、坐标、GT 或定向修复提示。模型在 603.87 秒内正常结束，保存三版候选。最终为 **14 空间 / 84 源边界 / 14 窗 / 14 门**，无未建开口，源几何自洽通过；**原图保真未通过，不能替代 run05 的辅助恢复结果或记作独立冷启动成功**。

## 实际生成与事后发现

| 候选 | 实际结果 | 模型采取的动作 |
|---|---|---|
| candidate_01 | 14 空间、14 窗、8 个已建门、6 个未建门；几何 severe | 首次建模时二层门高度误用楼层相对值 |
| candidate_02 | 14 空间、14 窗、14 门；几何通过 | 根据反馈把六个二层门的高度改为世界坐标 [3.0, 5.1] |
| candidate_03 | 几何与 02 相同，完整源摘要改变 | 只更新假设和未决事项，未修复下述原图差异 |

- 独立窗对照：已建窗 14/15 对应（12 complete、2 within_tol），漏一层南侧 x=[3.44,4.64]、z=[1.5,2.1] 的小窗。原图可见该位置是窗，候选却把南侧外门放到了这里；真实外门在更西端。这是门窗身份与位置混淆。
- 一层隔墙位置有差异，尤其南排第二隔墙 x=10.68 m，原图/参照约 x=10 m。北排 x=4.94/9.82、南排第一道 x=4.82 的小偏差需与墙面表示分开判断，不能一概视作拆房并房，也不能用同一宽容差吞掉 0.68 m 错位。
- 原始分区比较保留 severe；一层缺失/额外内部线长各 11.84 m 是偏移线段的对照统计，**不代表实际新增/拆除 11.84 m 物理隔墙**。二层内部线长差为 0。空间数量相同不证明位置正确，门数相同不证明原图连接保真。
- 最终原图门洞与墙位复核见 [visual_review.md](evaluation/visual_review.md)，由开发助手在生成结束后完成；GT 仅在评测侧，内门不能靠不完整的 GT 门清单验收。

## 回查工具确实被调用，但反馈没有闭合

本轮新增 `check_openings`，模型自行对 candidate_02 提交两次整层门清单回查：

- [一层回查](opening_reviews/review_001.json) 报告两个外门的空间标记不符，以及对应的两个未匹配对象。原因是观察把 `outside` 当作额外空间，而源模型只列室内一侧；这个报告本身不证明真实外门错连。模型没有按格式重新提交。
- [二层回查](opening_reviews/review_002.json) 六个 ID 均对应，但四个办公室门位标为 uncertain，全部保留 observation_pending。
- 两份结论均为 `observations_require_follow_up`，保真均为 `not_evaluated`。最终 candidate_03 没有绑定其新摘要的回查，也没有任何窗清单回查。

模型最后文字却称回查全部对应、没有未匹配项，并称平面与原图一致。该自述与实际记录冲突，原样保留在 agent_receipt.json，**不作为验收结论**。本工具只检查结构化观察与源清单的一致性；错误视觉判断仍可能自洽，不能自动检出漏看的图像对象。

## 用量、时间和验证

主模型实际 `claude-sonnet-5`、medium effort，一次 Claude 订阅 CLI 调用，603.87 秒，预算 900 秒，正常结束。CLI 估算 **$1.7039702**，不是订阅账单。没有 `ask_detail` 视觉子任务；回执另含 CLI 内部 Haiku 用量 $0.000701，已计入总估算，不能表述成 Haiku 从未出现。未调用 DeepSeek、付费 API 或 EnergyPlus。

31 次记录工具调用：inputs 1、看原图 19、像素投影 4、build 1、revise 2、看候选 2、check_openings 2。未使用 map_coordinates 或 ask_detail。首候选距首次工具调用 **511.14 秒**，仍然偏晚；存在低支持像素查询，不能把四次投影等同可靠量测。模型修复二层门高度后尚有时间，却以局部近似为由结束。

新增模块 11 项、真实 stdio/隔离边界 4 项离线测试通过，共 15 项，不重复累计前轮 27 项。另用历史开发观察重放 [run04/run05 开口差异](../2026-09-10_opening_review_replay/README.md)，准确指出两处旧多余门；该观察未进入本轮冷启动。

运行实现对应代码 `25e9e6a5`，四个文件摘要均与提交和本机一致。物理 geometry 字段逐项确认 candidate_02 与 03 相等（修订历史除外）；查看入口沿用模型实际看过的 02 平面，明确标注，不冒称查看过 03。完整校验见 artifact_verification.json。原始流无损 gzip，解压摘要见 compressed_streams.json。

## 复现和后续

```bash
python scripts/tool_scripts/run_bim_agent.py run \
  --images case_tests/e2e_tests/sm21_anchor/case_data \
  --out AI_agent/logs/experiments/<new-independent-run> \
  --scope '<agent_request.json 中保存的通用范围>' \
  --timeout 900
```

原始请求、生产报告和候选不改写；独立评价在生成完成后运行本目录 evaluate.py，输出 evaluation/。重新评测用新的输出副本，不能覆盖本次证据。源码、GT 路径/摘要、原图摘要、回查和修订记录均已留档，评测不反馈生成模型。

下一步从这些保存产物定位跨图门窗身份、尺寸链/墙面基准混用，以及未处理的回查反馈。先做最小工具或反馈改动，再用独立 run 验证；如用本次具体错误提示恢复，必须另记为定向辅助。暂不扩到 sm24/sm25，不把问题转成 GT 毫米精修或 EP 验收。
