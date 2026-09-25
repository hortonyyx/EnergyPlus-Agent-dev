# Voimatalo 09-25 candidate_01 独立复核（Sonnet）

## 结论

相比被退回的09-16 candidate_04（整层开敞、缺扫描区只标"unknown"），本轮 candidate_01
在方法论上明显更扎实：把每层拆成走廊+9类分区+3个竖向核，每条判断都挂了坐标与纹理依据；
用 shapely 对80个 space 做全量多边形相交检测未发现任何真实重叠，3个连续竖向空间
（CORE_N_continuous/CORE_S_continuous/STAIR_S_stair_hall）经边界表逐一核对，确认只有首尾各一块
楼板/天花，中间没有虚假楼板；用图连通性 BFS 检查，除5个屋顶围护体（技术性、无需人员可达）外
全部75个房间都能经门/敞开水平接触追溯到某个外部门；新测的8扇沿街窗有独立脚本、阈值和
plane-hit 校验，且"F2–F5窄柱无窗、只有F6–F7"的拒绝结果恰好印证了"卫生间窄窗只在顶两层"
的判断。所有门都精确落在对应空间的已观测外墙范围内，没有发现隔墙切窗、窗口错挂空间的情况。
真正的风险不在几何错误，而在解释层面：整套流线体系系于"西南沿街高玻璃竖带=主楼梯间"这一个
不可验证的纹理判读（开发者已自陈风险并给出回退方案）；南、东两端从"贴邻山墙"变为"无窗实体墙"
是从缺失数据反推的归纳结论，而 `source_enclosure` schema 没有"贴邻建筑"条件，这两片外墙目前
只能存成普通实体外墙，会让下游 EnergyPlus 把它们当真外墙算辐射/对流换热——这一点开发者已在
`PUBLIC_INTERFACE_NOTES.md` 里如实记录，但在正式建能耗模型前必须先处理，否则南、东两端十几个
房间×7层的负荷会失真。合并办公带、WC/service 大间等简化已经写清楚是简化而非精细划分，符合
用户此前对"笼统 unknown"的批评方向。

## 严重问题

1. **贴邻山墙缺少专门围护条件，会被下游当真外墙计算负荷**
   - 位置：`candidate_01/source_model.json` 中所有 `plane y=-33.4` / `plane x=19.5` 的墙
     （如 `space/F2_office_se/wall/0`、`space/F2_office_e/wall/1` 等，F1–F7 共约30余段），
     `enclosure: "physical"`, `adjacent_space_ids: []`。
   - 证据：`PUBLIC_INTERFACE_NOTES.md` 第1节自述 `src/agent/geometry/source_enclosure.py` 的
     `_CONDITIONS` 只有 `{"open","unknown"}`，没有"贴邻建筑/不对室外"选项；`report.json:
     provenance.party_wall_inference` 单独列了这些边界，但表示方式仍是"无开口实体墙"。
   - 影响：若直接拿这份 source_model 做 EnergyPlus 围护结构生成，这些墙会按普通外墙处理
     （全部对室外辐射+对流），与"贴邻山墙、近绝热"的判断矛盾，南端(STAIR_S/office_se/wc_s一侧)
     和东端(office_e/office_n一侧) 多个房间的逐层负荷会被系统性算错。
   - 建议：在真正跑 EnergyPlus 前，手动把这些墙的构造改成绝热或与假想邻栋耦合的边界，或推动
     在 schema 里加 `adjacent_building` 枚举（PUBLIC_INTERFACE_NOTES.md 已给出最小方案）。

## 一般问题

2. **电梯位置表述前后不完全一致**
   - 位置：`case_plan_v2.json: continuous_spaces[STAIR_S].evidence`（"...may also hold a lift"）
     与 `continuous_spaces[CORE_S].role = vertical_circulation_lift_core_hypothesis`。
   - 问题：南端相距约5–8m的两处（街面 STAIR_S 与内院侧 CORE_S）都被暗示可能有电梯，
     `unresolved` 里又说"南核内电梯数量、次楼梯…未建模"，读者容易误解为两台独立电梯。
   - 建议：明确电梯只在 CORE_S 一处，STAIR_S 的"may also hold a lift"改为"不排除"或直接删除，
     避免语义漂移。

3. **合并办公带作为单一 EnergyPlus 热区会掩盖长边梯度**
   - 位置：`office_w`（x -13.7..-7.65, y -21.3..19.2，约40m长单间）、`office_c`（约31m）、
     `office_n`（约22.7m），均只有一扇代表性门连 `corridor`（见 `connections.typical`）。
   - 问题：这是明确声明的简化（`office_zone_merged_cells_hypothesis`），对能耗建模量级合理，
     但如果被后续流程直接当逐间温区使用，会抹掉沿街长边不同朝向/进深位置的太阳得热和温度梯度。
   - 建议：在移交下一阶段时重申"这些是合并态，不是逐间温区"，避免被误用。

4. **WC/service 大间内部无再分**
   - 位置：`wc_s`（6.05m×4.2m≈25㎡，F2–F7）、`service_n`（3.65m×7.3m≈27㎡，F1–F8），均只有
     一扇门、南北两侧不分前室/男女。
   - 问题：面积、位置合理，但已明确声明是"WC/service"合并表达；若后续要做给排水或人流分析需要
     再拆分，目前只适合能耗尺度使用。这一点在案例文本里已提，但报告里可以更醒目地重复一次。

## 可接受但需说明的

5. **新增8扇窗的自动色阈值测量**（`observations/west_band_windows.json`,
   `measure_band_windows.py`）：方法透明（rb_drop/lum_drop 阈值 + plane-hit 校验），且
   "narrow列F2–F5全部 rejected（no window-like rows），只留F6–F7"与"卫生间窄窗只在顶两层"
   的判断自洽，交叉验证良好；开发者已如实注明反光/污渍可能被误判、边缘精度±0.1–0.2m，可接受。

6. **南、东两端"从 unknown 改判 party wall"是缺失数据的归纳推理，不是直接观测**：查看
   `observations/south_end_grid.png`、`east_end_grid.png` 可见两端确实系统性缺扫描（南端有一团
   疑似邻楼屋顶剪影，东端几乎是大片空白只剩顶部一条深色窄带），推理方向合理；已在
   `report.json: provenance.party_wall_inference` 与 `case_plan_v2.json: assumptions` 中单独归档、
   不与真正的"unknown"混淆，是对09-16遗留问题的改进，但结论本身仍是推断，不是"看到了墙"。

7. **5个 ROOF_*_enclosure 空间在门连通图里没有任何门**（`ROOF_N_BASE/ROOF_N/ROOF_STACK/ROOF_S/
   ROOF_enclosure`），经 BFS 验证确认它们不影响其余75个空间的可达性，是有意的技术性屋顶围护体
   （`roof_enclosure_simplified`），不是遗漏；但文档里没有明说"这些不需要人员可达"，容易被下一个
   审阅者误认为连通性缺陷，建议补一句说明。

8. **office_nw"两列非标准大窗"及北向首层店面/入口沿用09-16已有证据**：用
   `AI_agent/logs/experiments/2026-09-15_voimatalo_developer_walkthrough/evidence_01/north.png`
   交叉看，北立面左侧约20%–55%宽度确有一组比两侧更密集/成对的窗，与"大窗房间"判断方向一致；
   但这是继承证据，09-25本轮未重新测量这部分，只新增了西侧沿街的8扇窗。

## 你实际查看了哪些图/文件

- `case_plan_v2.json`（全文）、`PUBLIC_INTERFACE_NOTES.md`（全文）
- `candidate_01/source_model.json`：`spaces`（80个全量）、`boundaries`（524条，重点看 CORE_N/
  CORE_S/STAIR_S 的 floor/ceiling/wall）、`connections`（88条）、`source_enclosure`
  （`declaration.boundaries`、`open_connections`）、`opening_hosts`（388条，重点核对
  west_band_* 与 party wall 平面上有无窗）、`conflicts`/`unsupported`/`validation`
- `candidate_01/report.json`：`status`/`counts`/`unresolved`/`not_evaluated`/
  `provenance.party_wall_inference`
- `observations/manifest.json`、`observations/west_south.json`（像素-世界坐标映射校验）、
  `observations/west_band_windows.json`（8扇新窗全文）、`measure_band_windows.py`（测量脚本逻辑）
- 图片：`observations/west_south_grid.png`、`west_band_hi_grid.png`、`south_end_grid.png`、
  `east_end_grid.png`、`court_long_south_grid.png`、`court_short_corner_grid.png`、
  `top_grid_grid.png`、`west_north_grid.png`
- `result_01/plans/plan_compare_z14.png`（新旧候选对比）
- `result_01/feedback/new_south_end.png`、`new_court_long_south.png`、`new_east_end.png`、
  `new_court_short_corner.png`（源BIM边界X光叠加在原始网格上）
- `AI_agent/logs/experiments/2026-09-15_voimatalo_developer_walkthrough/evidence_01/north.png`
  （交叉核对 office_nw 大窗证据）
- 自写 `/opt/venv/bin/python`（含 shapely）脚本：全量多边形相交检测、连通图 BFS 可达性检查、
  楼层 z 连续性检查、opening_hosts 与 party-wall 平面窗口交叉核对
