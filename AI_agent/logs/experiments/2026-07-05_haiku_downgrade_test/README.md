# Haiku 4.5 降级测试 — reading 能力对照（2026-07-05）

**问题**：脚手架 vs 模型能力，谁是 reading 质量的杠杆？
**设计**：单变量 A/B。同一套**完全恢复的脚手架**（git skill/reading 内容哈希与 Sonnet 5 基线**逐字节相同**）、同一 case（sm21_anchor 满家具双层图）、同一把判卷尺（scorer_schema 7、默认容差）、同一冷启隔离协议（只喂 case_data 图 + skill，禁 gt/attempts/judge 评语）。**唯一变量 = reading 模型**：Haiku 4.5（`claude-haiku-4-5-20251001`，Agent tool `model=haiku`）vs Sonnet 5（基线 `run_2026-07-02_sonnet_flow_e2e`）。
**背景**：本环境 Agent tool 够不到 Sonnet 4.6，精确 4.6 对照需用户独立会话；改用登记在册的 Haiku 4.5 降级测试从"下方"攻这个杠杆问题（Haiku 弱于 4.6）。

## 结果（reading vs gt 坐标对账，判卷权威判据）

| 维度 | **Haiku 4.5**（本次） | **Sonnet 5**（基线） |
|---|---|---|
| 平面墙 (1f+2f) | **0/9**（1f 0/4·2f 0/5） | 9/9 |
| 平面窗 | **0/7** | 7/7 |
| 外框 footprint | 8/8 ✓ | 8/8 ✓ |
| 过度分割 | **+9 条多余内墙** | 0 |
| 立面窗 | **0/15 placed·17 extra** | 15/15 complete |
| 最大墙偏移 | 0.18m（轴近但段长/位置全错） | 0.0m |
| 立面朝向 | 四立面全 `ambiguous` | South aligned |

score_criteria：`walls_complete=severe(0/9)` · `windows_placed=severe(0/7)` · `no_oversplit=severe(+9)` · `elevation_windows_placed=severe(0/15)`；唯一 `boundary_complete=pass(8/8)`。

## 读得对的 vs 崩的
- **对**：外框 15×8（有尺寸标注、易）、楼层分隔线 z=3.0。
- **崩**：全部内墙隔断（位置估的：1f 竖墙画在 x=3.64 而 gt 在 x=5/10；横墙 y=2.4 自称"没标注、估的"）、全部立面窗（纯目测 x，无窗中尺寸）。Haiku 自己的 reading_summary 就标了这些为 "medium confidence / visual estimation"。

## 裁决
- **模型能力是主导杠杆**。同一套让 Sonnet 5 达 9/9·15/15·0.0m 的脚手架，换 Haiku 4.5 → 除 trivially-dimensioned 外框/楼层线外**全线归零**。脚手架**有它托不起弱 VLM 的能力地板**：约束能提示"读准坐标/别过度分割/窗中尺寸锚定"，但弱模型在满家具图上**感知就是错的**，脚手架给不出它看不到的东西。
- **非方差**。坍塌是 0/15、0/9 的整体性，不同于当年 Sonnet 4.6 窗 4–11 的 run 方差带；n=1 已足够定性（若要 n>1 可补 reread，但结论不会翻）。
- **CV 提上日程**（Phase C / 经典 CV 工具箱当 VLM 看图小工具，见 [capability/reading_improvement_methodology.md](../../capability/reading_improvement_methodology.md)）：sm21_pre 那次好 reading 的 forensics 已证 Sonnet 5 是**自发写经典 CV**（灰度投影定位墙线 + 连通域数窗）才拿到 0.0m 精度——弱 VLM 拿不到这套拐杖就崩。把 CV"量而非看"做成显式工具箱是给弱/开源 VLM 的关键杠杆。

## 产物
- run：`case_tests/e2e_tests/sm21_anchor/run_2026-07-05_haiku_downgrade/`（停在 J0 characterization stop，未推下游；DeepSeek 额度未花）。
- 判卷图：`0_reading/grade.png`（平面绿外框+红乱内墙；立面绿楼层线+全红窗）。
- 对照基线：`run_2026-07-02_sonnet_flow_e2e/`（用户 2026-07-05 定为 reading 参考 baseline）。
