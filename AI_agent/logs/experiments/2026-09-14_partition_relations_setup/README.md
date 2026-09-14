# 还原建模：候选定位与接头返工

**本轮取得了局部判读纠正，没有生成可采用的新BIM。** 直接要求模型输出完整隔墙/两侧点仍会造墙；按真实像素候选引用能固定主几何位置，但没有解决墙、家具、窗和门洞的全部语义。Sonnet针对接头返工改对了两项主要关系，同时又错解邻近墙段，因此完整回答仍不自动采纳。sm24/run12、sm21/run22保留。

## 四次真实调用

| 实验 | 实际模型 / effort | 秒 | 实际工具 | 结果 |
|---|---|---:|---|---|
| [自由坐标局部观察](../2026-09-14_sm24_east_partition_observation/README.md) | Haiku 4.5 / 默认 | 155.23 | 7次原图查看 | 横墙、侧点和连续路径均有实质错误 |
| [候选式Haiku](../2026-09-14_sm24_east_profile_observation/index.html) | Haiku 4.5 / 默认 | 125.17 | 15次原图、2次扫描 | 引用真实区间，仍把家具当墙、漏认带门纵墙、含混走廊空隙 |
| [同题Sonnet](../2026-09-14_sm24_east_profile_sonnet/index.html) | Sonnet 5 / medium | 124.43 | 5次原图、3次扫描 | 认对家具/纵墙，仍把真横墙降为碎段、走廊当横墙门洞、窗当标注 |
| [接头返工](../2026-09-14_sm24_junction_feedback/README.md) | Sonnet 5 / medium | 139.18 | 7次原图 | 改对横墙端接及走廊开敞；左侧真墙/门位置与朝向等仍错 |

四次均240秒上限内正常完成，共544.01秒；CLI估算合计$0.7840375，**非真实账单、非降本结论**。原始回执及逐模型用量见各run和[汇总](session_summary.json)。只走已授权Claude订阅，没有DeepSeek、付费API回退或EP。

前三次只提供sm24原始平面与开发限定的 `[360,260,630,610]` 范围，不供建筑声明、源候选、GT、已知正确墙位或旧观察。候选式两次另外指定两轴扫描、灰度色带和阈值，完整接收所有候选，不预筛正确墙。Sonnet与Haiku独立作答，未互相供答案。第四次是**显式开发返工**：从前一完整原答挑两处连接问题，裁图位置由已测端点/区间计算，提供完整未改写原答和核查方法；没有给正确关系或新几何，来源见[反馈记录](../2026-09-14_sm24_junction_feedback/feedback_provenance.json)。这些均非自主冷启动，也不能外推到整案稳定性。

## 可复用交付

- `observe_relations.py`：隔离只读局部调用，保留原图/问题、运行时代码快照、实际模型/用量及未改写原答。支持完整关系观察、候选式观察和显式问题文件返工；不开放BIM写入工具。
- `review_candidate_observation.py`：从原答提取唯一JSON；核图像散列、候选文件、候选ID和区间引用；列未覆盖/重复/坏引用。原图上逐条显示实际支持区间，可开关核对，不连接断线、不修坐标、不做墙身份或保真放行。
- `profile_diagnostic/`：开发侧使用既有像素量具的原始两轴对照。色罩同时抓到墙、家具和交叉笔画，不能直接作为墙目录。

两份候选式回答的引用均能指回真实区间，坏引用与原图散列问题为0。Haiku未引用2个单像素交点；Sonnet重复做x扫描，文件级覆盖缺口不能直接当漏墙数，跨assessment分别引用同候选不同区间也不是重复建墙。两页已用现有离线Chromium核实际图像/SVG坐标、逐项开关和全部显示，页面/控制台/资源错误0。它们仅为观察核查页，不是BIM结果页。

四次运行的隔离输入、原图/实际返回裁图和扫描图运输、只读工具范围全部核验；每次生产代码和本次runner运行中均未变。原始流无损压缩并回解验证。独立事后原图复核与输入/运输核验分开，均不是盲评或自动保真成功。

## 复现

新run目录必须不存在；模型调用仅在明确需要新实验时执行，普通验证不调用模型。

```bash
python AI_agent/logs/experiments/2026-09-14_partition_relations_setup/observe_relations.py --out NEW_RUN --model haiku --mode profile_candidates
python AI_agent/logs/experiments/2026-09-14_partition_relations_setup/observe_relations.py --out NEW_FEEDBACK_RUN --model sonnet --question-file AI_agent/logs/experiments/2026-09-14_partition_relations_setup/junction_feedback.md
```

完成后只读核验：

```bash
python AI_agent/logs/experiments/2026-09-14_reconstruction_input_setup/verify_observation.py RUN
python AI_agent/logs/experiments/2026-09-14_partition_relations_setup/review_candidate_observation.py PROFILE_RUN
```

参考审计脚本适用于 `assessments/refs` 输出；接头返工的 `junctions` 输出不强行转换成可执行几何。完整交接见[本轮记录](../../worklog/2026-09-14_reconstruction_partition_observation.md)。
