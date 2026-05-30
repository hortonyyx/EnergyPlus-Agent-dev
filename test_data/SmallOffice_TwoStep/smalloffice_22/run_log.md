# smalloffice_22 · 两步法运行记录

- 日期：2026-05-29（运行）/ 2026-05-30（审阅记录）
- 流程：两步法（phase1 半人工识图 → phase2 拓扑 → 9 下游 → InterZone 门 → EP）
- 结论：✅ 全链路干净跑通（继 sm_20 / sm21 之后第三个两步法干净 EP anchor）

## 案例
- 深圳 3 层办公，每层 15 × 8 m（360 m²/层）
- 热区：F1=7 / F2=8 / F3=4 → 共 19 区（16 办公 + 3 走廊）
- 异图新案例（非 sm_20 / sm21 同源素材），含家具/门噪声

## 本次运行的模型组合
> per-case llm.yaml 已于 2026-05-30 换成新简版模板（按阶段/节点分段、可逐个调），
> 默认组合与本次运行一致（几何 pro / CRUD flash），故配置即留档。
- phase2（intake_phase2）：deepseek-v4-pro，thinking=enabled，reasoning_effort 本次未设（≈ provider 默认 high；模板现已显式写 high）
- 几何节点 surface / construction / fenestration：deepseek-v4-pro，thinking=disabled
- CRUD 节点 zone / material / schedule / hvac / people / lights：deepseek-v4-flash，thinking=disabled

## 产物体量
- 19 Zone / 135 BuildingSurface:Detailed / 16 FenestrationSurface:Detailed
- 6 Construction / 16 People / 16 Lights（办公区，走廊不放人/灯，符合规格）
- 楼层标高 z = 0 / 3.60 / 7.20，与 phase1 反算一致

## 验收
- **InterZone 确定性门**：135 面 / OBC=Surface 90 / OBC=Outdoors 38 / OBC=Ground 7 / Adiabatic 0；
  互逆配对 45；**pair_issues = 0**（零误杀、零跨层配对缺陷）
- **EnergyPlus 25.1.0**：`Completed Successfully` / 0 Severe / 0 Fatal / 6 Warning / 7.26 s
  - 6 个 warning 全无害：Timestep 默认、无 design day、weather location 覆盖、World/Relative 坐标提示、
    World 坐标系提示、Ground 温度默认。
  - 注：pipeline 内那次 EP 报 "executable not found"（容器内引擎路径问题），结果由事后手工
    rerun 补跑（`output_twostep_e2e/energyplus_rerun.log`，12:37）。机制无关，仅环境路径。

## 审阅发现
1. **fenestration 节点话术过报（无害）**：节点收尾 summary 声称 "18 fenestrations confirmed"，
   但 fenestration_specs 实际枚举 16 扇、IDF 实建也是 16 扇（spec=16 / IDF=16 一致）。
   多报的 2 扇是 LLM 自然语言总结里的幻觉，未污染 IDF，几何正确。仅话术问题。
2. 其余几何/拓扑：InterZone 门 0 缺陷 + EP 0 severe，跨层配对自洽；deterministic 门覆盖到的
   层面（互逆/面积/法向/共面/最小边长）全过。
   - 建模质量主线（跨层 split-pairing 亚厘米抖动 / 天花按下层细分区切分）仍属
     [capability/recognition_modeling_capability.md] 长期主线，门只保证自洽不保证"对"，本案
     未深挖该层，留待容差重生成落地时统一评估。

## 残留 / TODO
- [ ] OpenStudio 人工验收（dimensions_check，用户填）
- [ ] 如需正式 baseline 归档：`记录这次跑 smalloffice_22 <tag>` 走 test_baseline 协议
