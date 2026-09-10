# 09-10 任务1梳理报告：历史好/坏 reading 跑测的实际过程与独立性

**方法说明**：本报告全部基于 Read/Grep/Glob 直接核查仓库内原始产物（run 目录下的 JSON/summary/config/log），未调用模型、未跑新实验。下文用【实证】标注我直接打开文件验证过的事实，【二手】标注仅见于历史总账文档、本轮未找到更底层证据支持的说法，【推断】标注我依据实证做的合理推论，【未核实】标注找不到证据或有矛盾的地方。旧评分（judge minor/pass）不代表源 BIM 全面通过，本报告不做这种等价。

## 一、逐案例核查结果

| # | Run（路径均在 `case_tests/e2e_tests/`） | 模型（历史 ID，不当今天可调用 ID） | 图数 | 独立性 | 证据等级 |
|---|---|---|---|---|---|
| 07-02 | `sm21_anchor/run_2026-07-02_sonnet_flow_e2e` | Sonnet 5（当时 `claude-sonnet-5`） | 6 | 独立跑，无 CV 工具箱，现造 PIL+scipy 流水线 | 分数【实证】(`0_reading/attempts/001/score_vs_gt.json`)；112次工具调用之说【二手，来自 `improvement_methodology.md §1.1`，本轮未逐条重放 transcript】 |
| 07-05 | `sm21_anchor/run_2026-07-05_haiku_downgrade` | Haiku 4.5（`claude-haiku-4-5-20251001`） | 6 | 独立跑，与 07-02 同脚手架、仅换模型的对照实验【实证，见 `run_config.yaml:1-6`】 | 全部实证 |
| 07-07 sm21 | `sm21_anchor/run_2026-07-07_haiku_cv_retest` | Haiku 4.5 | 6（pilot 只做了 1f，其余"未开始"标注留在 summary 里） | 独立跑，带完整 CV 侧车（92 份） | 全部实证 |
| 07-07 sm24 | `sm24_anchor/run_2026-07-07_haiku_cv_probe` | Haiku 4.5 | 5（此 case 无 2f） | 独立跑；**与后续"错切"完全是两条谱系**（见下节） | 全部实证；**无 gt**，"满分"是用户肉检 |
| 07-08 | `sm21_anchor/run_2026-07-08_gpt54mini_cv_retest` | gpt-5.4-mini（经 codex CLI） | 6 | 独立跑，工具箱迁移到第三家模型的对照实验 | 全部实证 |
| 08-20 S1 | `sm21_anchor/run_2026-08-20_acceptance_sonnet_S1` | Sonnet 5 | 6 | 独立跑，**专用空 staging 根**、pilot 门、订阅通道 cold-start 子代理 | 全部实证（`PROVENANCE.json` + `_run/pilot_verdict_r1.md` + `reader_invocations.jsonl`） |
| 08-20 G1（反例） | `sm21_anchor/run_2026-08-20_acceptance_gpt54mini_G1` | gpt-5.4-mini | 6 | 独立跑，3 轮 pilot 返工才放行 | 全部实证 |
| 09-09 | `AI_agent/logs/experiments/2026-09-09_automatic_source_sm21_run01` | Haiku 4.5 | 6 | 独立跑，**真正意义上的原图冷启动**（`mode: "fresh_original_drawings..."`） | 全部实证，含机器记录的成本 |

### 07-02 Sonnet（sm21）
`0_reading/attempts/001/score_vs_gt.json`【实证】给出平面墙 9/9、窗 7/7、立面窗 15/15、`max_wall_offset_m: 0.0`，与总账一致。correction/mep 阶段有 `correction_thinking.txt`/`mep_thinking.txt`，说明这是一次走完全流程（含 4_mep）的 e2e run，不是纯 reading 探针。"112 次工具调用、现造 PIL+scipy 流水线"这一说法本轮**未在该 run 目录内找到独立的调用日志文件**（该 run 早于隔离子代理架构，没有 `access_log.jsonl`/`reader_invocations.jsonl`），只能溯源到 `improvement_methodology.md §1.1` 的取证结论，属于【二手，未在本轮复核】。

### 07-05 Haiku 降级（对照组，坏）
`run_config.yaml`【实证】明确写着这是"与 07-02 Sonnet 基线相同脚手架、唯一变量是模型"的受控降级实验。`reading_summary.md`【实证】通篇没有任何 crop_zoom / px_m_calibrator / wall_line_profiler 字样，墙位描述为"visually estimated"、"estimated at y=2.4"，但自评置信度写的是 **MEDIUM-HIGH / HIGH**（几乎全篇高置信）。最终评分是 0/9・0/7・0/15。**这是一条很硬的证据**：自评置信度与是否真的用工具测量完全脱钩，"看起来很确信"不能作为可信度信号。

### 07-07 Haiku（sm21，好）
`0_reading/1f_view.json`【实证】的墙笔画全部是 `"kind": "line", p1/p2"` 单线段，外周墙用**外皮线**为基准（note 明写"外皮线 y=0"），内部隔墙/走廊墙用**中线**为基准（note 明写"中线 y=5.00"）。这证实了 roadmap 所说"历史好 reading 已是单线"——**但基准不是统一的，是按构件类型分流的混合基准（外皮/中线），且这个分流规则写在每条笔画的 note 文字里，不是 schema 里的结构化字段**。`reading_summary.md`【实证】记录了完整的标定链路：`crop_zoom` 放大尺寸链端点→亚像素锚点→`px_m_calibrator`→用这把尺子换算墙线；44 条候选拒收台账全部带理由；32 条尺寸链全量转录。

### 07-07 Haiku（sm24，好，无 gt）
`0_reading/1f_view.json`【实证】同样是 `line` kind、p1/p2 单线段，note 里同样显式标注"outer face"与"中线"两种基准（如 S1 的 note："South perimeter wall, outer face = local y 0.00"）。`reading_summary.md`【实证】质量非常突出：51 条尺寸、11 条链全部闭合、10 处门洞治愈（3 处链钉位+7 处像素测量，且**诚实分开标注**）、还倒过来给 harness 提了 6 条 schema 反馈。**这份 reading 当时确实无 gt**，"满分"是用户人工肉检结论，本报告不能把它当量化通过。

### sm24 的"好 reading"与后续"错切"——**可以干净分开**
这是本任务要求特别核查的一点。我在 `case_tests/e2e_tests/sm24_anchor/` 下找到了另一条完全独立的谱系：`run_2026-06-24_opus_reading`。核对 `report/REPORT.md`【实证】：
- 识图模型是 **Opus**（不是 07-07 的 Haiku），日期是 06-24（早于 07-07 十几天），有自己独立的 0_reading 产物。
- "11 区≠testdata 的 8 区"这个 tripwire 出现在 **1_correction 阶段**（`correction.zone_count_tripwire`），根因写得很明确：确定性几何内核把两个**非矩形**房间（L 形走廊、阶梯西墙 office）按矩形规则拆成了 4 个 cell，reading 阶段本身的 7 条 J0 判据（含 `no_furniture_as_wall`、`no_dimension_as_wall`）**全部 pass**。
- REPORT 原话："本 run **没有'错'**——是一个干净跑通的非方形探针"；"非校正错，是确定性内核把两个非矩形房间按矩形分解"。

**结论：sm24 的"好 reading"（07-07 Haiku）与"11 区错切"（06-24 Opus + 确定性内核）是两个不同日期、不同模型、不同 run 目录、且错误定位在不同流水线阶段（correction 的几何内核分解，不是 reading）的独立事件。** 把两者混为一谈会误判 Haiku 07-07 那份 reading 的质量；我在 `run_2026-07-07_haiku_cv_probe/1_correction/correction_raw.txt` 中抽查未见任何 zone_count 相关字样，支持这个分离结论，但我**没有完整读完该 correction 全文**，不排除其他问题，这点标【未核实】。

### 07-08 gpt-5.4-mini（sm21，好，带 known_defect）
`reading_summary.md`【实证】：9/9 墙・6/7 窗・15/15 立面窗，token 约 0.90M/case（约 Haiku 基线 1.5 倍）。`reading_fixtures.json`【实证】记录了它的已知缺陷：链式算术把 0.24m 的未标注余量平摊丢失，直接导致第 7 扇窗漏判——这是"good"标签下的**已登记具体缺陷**，不是全绿。

### 08-20 S1（sm21，好，工程档非成绩档）
`PROVENANCE.json`【实证】把这次跑测的性质写得很清楚："工程档，不是成绩档"，用途是验证"07-07 那套形式在当前代码树上还成立吗"。关键独立性证据：
- 专用空 staging 根 `/tmp/ep_accept_S1`，杜绝复用 08-19 那次留有半成品脚本的目录（`.note` 明确写了这层污染防范）。
- `_run/pilot_verdict_r1.md`【实证】：orchestrator(Opus 5) 只看过程证据（crop_zoom 次数、标定锚是否对图元、跨轴分歧）做出 APPROVE 决定，**未接触 gt**，然后才允许跑分——判卷用的是确定性 `score_reading_vs_gt`，不是模型自评。
- `reader_invocations.jsonl`【实证】：3 次调用，第 2 次 `returncode: 1`、`session_form: "resume"`，与"读到第 4 张图时烧穿 5 小时会话窗口、`--resume` 续跑"的说法完全对得上。
- `0_reading/attempts/001/score_vs_gt.json`【实证】：`max_wall_offset_m: 0.0`，但仔细看明细，墙的实际落位是 0.11-0.12m 内缩（中线基准），窗落在标称位置——**两种基准混在一份产物里**，只是判卷用的墙容差是 0.3m，这个偏差被容差吸收掉了，没有拉低分数。这正是 `reading_fixtures.json` 里记的 known_defect "R-2"。
- 本次运行**没有找到任何美元成本记录**（`llm.yaml` 是下游 correction 用的 DeepSeek 配置，与 reading 阶段用的 Claude 订阅子代理无关；`reader_invocations.jsonl` 只有耗时没有金额）。总账文档里的"$7.32/图"【二手，本轮未找到底层账单文件，按用户口径这类无成本证据的说法不算数】。

### 08-20 G1（sm21，反例）
`_run/pilot_verdict_r3.md`【实证】：3 轮返工才放行，r2 的问题是"派工方文本自相矛盾导致坐标未换算"，orchestrator 靠产物哈希变化（`3df4d7fb3ffdee46`→变化）而不是自陈述来确认"这次是真改了"。最终判卷 7/9・5/7・立面 6/15，撞出"两轴拆成单轴调用规避告警"的失效模式（`reading_process_metrics.py` 侧的 `calibration_axes_agree` 检测住了）。

### 09-09 Haiku sm21（真失败，冷启动）
`report.json`【实证】是本轮唯一**带机器成本记录**的案例：`estimated_cost_usd: 0.52`（CLI 估算，非账单）、44 轮、`num_turns`。reading 阶段的确定性技术检查是 97 pass / 24 n/a / 8 fail（8 个 fail 全部是 `dimension_chain_closure` 和 `partition_on_window_jamb`），**但仍被标记 `reading_technical_acceptance: "accepted"`**——因为这些是已知类别的失败，不是硬阻断。真正让这次跑测失败的是人工视觉复核："漏隔墙、错走廊、门未保留几何"（`controller_stop.reason`），随后两次 correction（Sonnet 4-6 订阅）均超时/被中断，**没有产出可用 BIM**。这个案例证明：确定性检查 pass 率高（97/8≈92%）不等于人工能接受的空间保真度。

## 二、可信度分级证据表

| 结论 | 等级 | 依据 |
|---|---|---|
| 07-07 sm21/sm24、08-20 S1 三份产物均为单线（`kind:"line"`）墙表示 | 实证 | 直接读取 JSON `strokes[*].geometry` |
| 单线基准按构件类型分流（外周=外皮线，内部隔墙=中线），写在 note 文字里而非结构化字段 | 实证 | sm21/sm24 两份 1f_view.json 的 note 逐条核对 |
| 08-20 S1 存在"墙用中线、窗用标称位置"的双基准不一致（R-2），被 0.3m 容差吸收未拉低分 | 实证 | `score_vs_gt.json` 明细数值 |
| sm24 好 reading（07-07 Haiku）与 11 区错切（06-24 Opus）分属不同 run、不同模型、错误定位在 correction 内核阶段 | 实证 | 两份 REPORT/summary 交叉核对 |
| 07-02 Sonnet 现造 112 次工具调用 | 二手（未复核底层 transcript） | `improvement_methodology.md §1.1` |
| 07-07 sm21 成本 0.4–0.6M tokens、08-20 S1 单图 $7.32 | 二手，无原始账单文件支撑 | 总账文档口径 |
| 09-09 失败案例 reading 阶段成本 $0.52（CLI 估算） | 实证（但明确非账单） | `report.json` |
| 08-21 解剖："`bc3b9ac686` 这份 07-07 产物被 19 个 run 复用"，不能按 run 数计成功次数 | 二手，本轮未逐一核对 19 个 run 的哈希 | `2026-08-21_historical_reading_dissection/README.md` |

## 三、可复用经验（非总账复述）

1. **自评置信度不可信，工具调用证据链可信。** 07-05 全篇自评"HIGH"但 0 分；08-20 S1/G1 的可靠判据是"crop_zoom 是否调用、标定锚是否指对图元、两轴是否一次给全"，靠产物哈希变化而非自陈述确认返工生效。
2. **单线基准目前靠自然语言 note 维系，没有结构化字段区分外皮/中线。** 若要做双线或显式基准声明，需要先把这条隐性规则升级为 schema 字段，否则每次判卷容差都在悄悄吸收基准不一致（R-2 类缺陷）。
3. **"好 reading"标签需要按缺陷登记而非二元判断**（`known_defects` 机制，07-08/08-20 S1 都是"好但有名有姓的缺陷"）。
4. **reading 阶段的确定性技术检查通过率高（09-09 达到 92%）不能替代人工/视觉复核**；真正的空间保真问题（漏墙、错走廊、门丢几何）是检查覆盖不到的部分。
5. **sm24 反面案例的教训是流水线阶段归因，不是模型归因**：11 区错切根因是几何内核对非矩形空间的矩形分解规则，不是某次识图差。

## 四、未核实事项与下一步

- 07-02 的 112 次工具调用未在本轮重放/核对其 transcript 原文（该 run 无 `access_log.jsonl`）。
- 07-07 sm21/sm24 及 08-20 S1 的美元成本均无底层账单文件，仅二手估算，不应写入正式成本基线。
- `run_2026-07-07_haiku_cv_probe/1_correction/` 是否也有其他非 zone_count 类问题，本轮仅做了关键词抽查，未逐段读完。
- `reading_fixtures.json` 里 14 份夹具中除本报告覆盖的几份外，其余（08-15/08-16/08-18/08-21 T1）未在本任务范围内深入核查，留给相关任务。
- 仓库中存在一份 `AI_agent/logs/experiments/2026-09-10_reading_architecture_review/`（未纳入 Git）是此前一次编排脚本对本任务的另一次尝试，`history_stream.jsonl` 中未见 `"type":"result"` 事件、无 `history_run.json`/`history_report.md`，**判断为中途中断、未产出结论**，本报告未采信其内容，建议主助手确认是否需要清理该未跟踪目录。