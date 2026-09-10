# sm24 四立面：尺寸工具与逐面回查辅助恢复

**回查接线实际运行，窗位错误没有修复。** 295.48 秒正常结束，模型显式选回 [seed](seed/viewer.html)，没有新候选。仍为 **1 个整层合并空间 / 11 窗 / 3 外门**，几何检查通过；南侧右窗仍向左偏 0.48 米。不得将模型总结中的“全部位置一致、不需修改”当作独立结论。

[交付页](delivery.html) · [源模型](seed/source_model.json) · [原始方案](seed/proposal.json) · [独立诊断](evaluation/index.html) · [外开口坐标诊断](evaluation/opening_coordinate_diagnostics.json) · [浏览器验证](../2026-09-10_parallel_modelling_browser_qa/README.md)

## 输入与实际运行

从 [run01/candidate_01](../2026-09-10_partial_inference_sm24_run01/README.md) 保存方案恢复，仅有四张原立面和深圳/办公/一层/约200平方米声明。开发助手显式要求重新核对各面尺寸链、调用新的累计工具、让 Haiku 独立读一条链，并按立面回查门窗。未给正确数字、门窗数、平面、真实房间数或 GT；保留整层合并与内部未知。这是**有程序性指导的辅助恢复**，不是新的冷启动成功。

生成代码为 `b44caa7f`；[输入快照](inputs.json) 记录四图和七份实施文件的 SHA-256、完整范围、seed 来源。运行结束后、实施代码未变时核验，14项均通过，见 [产物核验](artifact_verification.json)。恢复过程重记来源及源哈希，实际物理模型、假设和未解决项均未改变；并非源 JSON 字节完全不变。

主调用为 Claude 订阅 `sonnet`，实际 `claude-sonnet-5` / medium；局部任务为只读 `haiku`，实际 `claude-haiku-4-5-20251001`，197.08 秒。共2次订阅调用，CLI估算合计 $0.6957458，不是订阅账单。没有 DeepSeek、付费 API 回退、GT 输入生成或 EP。完整回执与请求留在目录；两份流记录以 gzip 无损保存，字节数及原SHA见 [压缩记录](compressed_streams.json)。

实际工具轨迹包含22次图像查看、2次像素剖面、2次尺寸链计算、1次 Haiku 局部复核、1次清单查看、8份回查及1次交付；没有几何编辑或新建候选。

## 工具反馈与模型总结的差距

- `map_dimension_chain` **只计算了西、东两面**，没有南、北工具调用。最终总结却称四面均经工具重算且14个开口全对；实际南侧右窗 `W_S2` 仍为 `[7.48, 8.98]`，原图累计与独立参照为 `[7.96, 9.46]`。这次工具可用仍未带来修正。
- 两次调用都将以毫米为单位的分段链配上 `expected_total=20`；接口约定期望总长与链同单位，故返回 `expected_total_m=0.02`、`closure_error_m=19.98`。实际链总长20米正确，错误来自调用者的期望总长单位。模型没有处理这项反馈。后续宜把期望总长单位表达得更直接，并检验模型是否按返回区间核对实际对象。
- Haiku 独立读西面，正确列出尺寸链及5窗/0门，但把窗与尺寸段的关系配错，并把1500/1200毫米等窗估成约800–850毫米。主模型只采用数量，不接受这些宽度；这说明目标档可贡献局部信息，本次尚不能独立可靠定位开口。没有完成“裁到真正关键局部并给原图像素依据”的预期质量。
- 8份新回查覆盖四面 × 窗/门，西面门明确提交空观察，全部为 `consistent_with_supplied_observations`。新范围确实消除了把其他面的开口算作漏项的误报。**这些是身份/清单与供给观察一致，不是坐标或图像真值验收**。passage 仍 `not_reviewed`，没有因建成数为零自动放行。

## 独立评价与下一步

生成结束后才运行共用诊断。旧分区比较仍报告1对8为 severe，但本任务允许按明确选定的低简化档合并，未提供内部平面；这项差异用于说明隐藏信息，不能直接判部分推理失败。旧窗评分器不支持本例 typed v3 参照，明确 `not_evaluated`，不压平、不伪造分数。

另复用 [本案例坐标诊断脚本](../2026-09-10_partial_inference_sm24_run01/evaluate_opening_coordinates.py)，按同层/同立面/同种类、等数量组的空间顺序比较实际源顶点，不拟合或镜像。14个外开口可配对：一扇窗偏0.48米，其他13个的水平区间吻合，高度仅约0.0000112米提取残差。该结果不是完整 typed claim 评分，也不证明视觉身份或真实内部格局。

```bash
python AI_agent/logs/experiments/2026-09-10_partial_inference_sm24_run01/evaluate_opening_coordinates.py \
  --run AI_agent/logs/experiments/2026-09-10_partial_inference_sm24_run02 \
  --candidate seed --out /tmp/sm24-partial-run02-opening-recheck.json
```

本程不再同型重试。下一小步应验证**不见旧候选答案的关键图像独立提取，再与源对象比较**，针对观察自证和实际位置不一致，而不是继续累积“观察一致”状态。该改进方法尚未实跑。
