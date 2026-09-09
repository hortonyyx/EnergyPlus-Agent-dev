# 原图 reading 诊断

日期：2026-09-09。范围仅为本实验从 sm21 六张原图自动产生的 Stage 0 reading；未调用模型、未修改生成答案，也未把 GT 作为生成输入。

## 结论

`0_reading` 被接受，表示它通过了本次 **exploratory** 档的技术入口和隔离审计；不表示图纸保真、源房间分区或门窗/开口关系已经可信。该结论尤其不能作为通用源 BIM 的“已可导出”依据。

本次 reading 至少有三类直接影响后续源 BIM 的风险：

1. 门被压平成墙。1F 只有 `S8`、`S9` 的墙备注写了 `healed door opening`，没有门的 ID、端点、宽度或状态；其 `uncaptured` 又笼统说 entrance doors 也被 healed。2F 把室内门写为 “not explicitly counted”，其 `door_heal_traced` 为 not applicable。这样下游没有可保留的开口和空间连通来源，不能把结果当作“门已识别”。见 [1F JSON](run/0_reading/1f_view.json)、[2F JSON](run/0_reading/2f_view.json) 和 [checks](run/0_reading/attempts/001/checks.json)。

2. 内部隔断不具备闭合/连通证明。1F 的 `S8` 在 `[3.78, 4.0]`、`S13` 在 `[0.5, 3.3]` 和 `[7.77, 3.3]` 有不与其它墙相接的端点；这与原图中上下各三间、横贯走廊的结构不符。1F 有 3 条、2F 有 1 条内部墙坐标与窗框重合，现有检查已定位为 `partition_on_window_jamb` 失败。这也解释了查看中走廊线断裂/错位、东侧窗成为离墙矩形的风险。

3. 尺寸和摘要不能支持校准结论。六张视图的 `dimension_chain_closure` 都失败；其中两张 plan 只有总宽/总高，缺分段链。`reading_summary.md` 却称全部尺寸已转录和验证，还说 plan `scale_origin` 为 null，实际两张 plan 都声明了 `[0,0]`。摘要可以说明模型自述，不能替代 JSON 与检查。见 [摘要](run/0_reading/reading_summary.md) 和 [检查](run/0_reading/attempts/001/checks.json)。

## CV 为什么没有约束结果

隔离工作区确实产生了 27 个 CV sidecar，且 provenance 已把它们归档；例如 1F/2F 的 `wall_line_profiler` 与 `window_cc_detector`。但这些候选的 overlay 状态是 `undecided`，`scale_px_per_m` 为空，reading JSON 也没有把候选 ID 或像素—米变换接成来源。因此当前门禁只审计它们是否存在，无法比对“读出的墙/窗是否贴合候选”。`reading.calibration_axes_agree` 因没有 `px_m_calibrator` 而是 not applicable。

证据见隔离 [1F wall profiler](run/0_reading/attempts/001/cv_evidence/cv_evidence/1f_view/001_wall_line_profiler.json)、[1F window detector](run/0_reading/attempts/001/cv_evidence/cv_evidence/1f_view/001_window_cc_detector.json) 和 [isolation provenance](run/0_reading/attempts/001/isolation_provenance.json)。代码上，sidecar 写入在 [sidecar.py](../../../../src/agent/reading/cv_toolbox/sidecar.py)，reading 检查只把缺标定记为不适用的路径在 [reading.py](../../../../src/validator/checks/reading.py)，而不执行候选—输出几何匹配。

## 为什么仍被接受

本 run 的 profile 是 exploratory。reading linter 的说明将 ID、合法笔型、非退化几何、字段形状等列为 invariant；尺寸链闭合、窗框重合和标定问题是 cross-check。exploratory 下后者会记录失败而不阻断接受，故 `reading.view_manifest_coverage` 与所有 invariant 通过后仍能合并 accepted attempt。见 [checks](run/0_reading/attempts/001/checks.json)、[reading.py](../../../../src/validator/checks/reading.py) 和 [isolation merge](../../../../src/agent/execution/isolation.py)。

这一分层本身合理：单纯的尺寸链或窗框相交启发式存在合法例外，不能把每个 flag 一律升级为硬阻断，更不能让细小尺寸差成为主线前置。另一方面，当前 source 导出也把 drawing partition fidelity 与 opening completeness 标作 `not_evaluated`，所以不应由 accepted 状态推断源空间正确。见 [source_bim.py](../../../../src/agent/execution/source_bim.py)。

## 最小后续建议

先用本次“走廊断裂、隔断缺失、门被压平、离墙窗”的可查看反例，校准一个面向 **源房间与门保留** 的确定性门禁：检查候选源空间是否因内部墙自由端、窗宿主不成立或被 heal 的门而无法保留独立分区/连接。现有 `partition_on_window_jamb`、尺寸链记录和线段拓扑可作诊断输入；评价侧 `tarch_normalize.s4_close_topology` 已有 polygonize/dangle 的确定性做法可参考，但不应导入 GT 或把该启发式直接当成通用拒绝规则。先在这一真实反例上确定误报边界，再接入 source flow。

## 本轮后续状态

校正的首次 Sonnet 请求在 600 秒超时。随后旧逻辑的一次重试已由主助手在发现上述失真后中断；没有新的 `1_correction` 接受产物，也没有新 BIM 导出。本实验目前只保留 reading 与诊断证据。
