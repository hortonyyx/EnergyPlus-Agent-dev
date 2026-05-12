# Phase 1 启动 Prompt v1（直接粘进新 Claude Code 会话）

> v1 取代 v0。v0 让 Opus 同时做识图 + 拓扑，违反分工。v1 修正：phase1 只识图，phase2 才做拓扑。
> 用法：在 `EnergyPlus-Agent-dev` 项目根新起 Claude Code 会话（Opus 4.7），把下面 "---" 之间的内容整段粘贴作为首条消息。

---

我在做一个 intake 两步法 POC（背景 [AI_agent/floorplan_redraw_strategy.md](AI_agent/floorplan_redraw_strategy.md)）。本会话只做 **phase 1：用语义笔重画原图**——把建筑图纸上的每一根可见笔触按类型（墙笔 / 窗笔 / 门笔 / 楼梯笔 / ...）描出来，**不做任何空间拓扑推理**。

## 心智模型

phase1 = "用一套带语义标签的笔，把原图重画一遍"。比如"墙笔在 (0,0)→(15,0) 画了一根 wall stroke"、"窗笔在立面 (1.4, 1.0)→(3.8, 2.8) 画了一个填充矩形"。

phase1 **不做**：把多根墙笔围合成"一个房间" / 判某墙是"外墙还是内墙" / 说"这扇窗属于哪面墙" / 写"南立面 F2 中间窗的 z_min/z_max"。**所有拓扑推理留给 phase2**。

## 误差预算（关键，看 schema §0.1）

phase1 看图、phase2 不看图。所以：

- **识图误差只能在 phase1 截断**。phase1 一旦尺寸读错、坐标偏移、立面 x 轴搞反、笔触漏画，phase2 没机会回溯纠正——phase2 拿到的就是错的当真的算
- **宁可填 null 也不要瞎猜**。null = "我没看清/没标"，phase2 知道这是缺失。瞎猜的数值是污染
- EP 仿真 zone 由 surface（2D 面）围合，**墙没厚度**——plan 墙的 `thickness_m` 一律填 `null`，不要费力估视觉笔宽

## 你的任务

1. 完整读 [test_data/SmallOffice/smalloffice_20_redraw/vector_schema_v1.md](test_data/SmallOffice/smalloffice_20_redraw/vector_schema_v1.md)（**必读**，含 strokes / pen 枚举 / 立面 facade_axis_note 规范 / 反例 / 自检）
2. 看 worked example：[phase1_vector/1f_view.json](test_data/SmallOffice/smalloffice_20_redraw/phase1_vector/1f_view.json) 已经由人工降级写好（10 根 wall stroke + 16 个 dim，**不要重写**），照它的风格做剩下 7 张
3. 按下表给剩下 7 张图各产一份 JSON：

| 源 PNG | 输出 JSON | image_kind |
|---|---|---|
| ~~1f_view.png~~ | ~~1f_view.json~~ | ~~plan~~（已完成，作 worked example）|
| `2f_view.png` | `phase1_vector/2f_view.json` | plan |
| `3f_view.png` | `phase1_vector/3f_view.json` | plan |
| `South_view.png` | `phase1_vector/South_view.json` | elevation |
| `North_view.png` | `phase1_vector/North_view.json` | elevation |
| `East_view.png` | `phase1_vector/East_view.json` | elevation |
| `West_view.png` | `phase1_vector/West_view.json` | elevation |
| `supp_plan.png` | `phase1_vector/supp_plan.json` | 自行判断 |

所有源图在 [test_data/SmallOffice/smalloffice_20_redraw/](test_data/SmallOffice/smalloffice_20_redraw/) 目录下。元信息看 [testdata_prompt.json](test_data/SmallOffice/smalloffice_20_redraw/testdata_prompt.json) —— 但只用来了解楼层数 / 层高 / 总尺寸，**不要把 testdata_prompt 的内容直接抄进 phase1 JSON**（phase1 应只反映图上看到的东西）。

## 核心纪律

1. **plan 和 elevation 用不同 pen 词典**（schema §3）：
   - plan 合法 pen = `wall` / `window` / `stair` / `other`（**不收 door**）
   - elevation 合法 pen = `wall_fill` / `window` / `outline` / `other`（**不收 wall、不收 door**）
   - 跨用即错。比如 elevation 上的墙身必须用 `wall_fill` 不是 `wall`
2. **立面墙身按"每层一个 wall_fill stroke"切分**（schema §3.3）。sm_20 是 3 层 → 每个立面图出 3 个 wall_fill。即使灰填上下视觉连续，按尺寸链的分层 z 范围切
3. **拓扑不是 phase1 的工作**。禁止字段：`is_exterior` / `parent_wall_id` / `rooms[]` / 任何"X 属于 Y / X 朝外 / X 围合"类语义
4. **POC 阶段不扩 pen 词典**。看到分层线 / 结构柱梁 / 装饰线 / 索引箭头一律 `pen="other"` + note 描述；不要新造 `cornice` / `column` / `level_line` 等枚举值。看到词典覆盖不到的笔触在 `self_check.uncaptured_visual_elements` 里记一笔
5. **一笔到底就一个 stroke**。比如外墙南侧从 (0,0) 到 (15,0) 是**一根** wall stroke，不要拆 3 段。除非真被窗洞物理打断
6. **找不到填 null**，禁止默认值。plan 墙的 `thickness_m` 一律 null（仿真不用，schema §0.2）；其他字段图上找不到也填 null
7. **立面图 facade_axis_note 必须含符号**（schema §4 四立面对照表）
8. **OCR 原样**，找不到文字标签就 ocr_texts 留空数组

## 工作流

1. 读 schema v1 + worked example 1f_view.json（理解风格）
2. 先做 `2f_view.png` 一张 pilot，完成后停下来让我看，**不要直接批量做完所有 7 张**
3. 我审 2f_view OK 后，再 batch 处理 3f_view + 4 个立面 + supp_plan
4. 全部完成后，写一份 [phase1_vector/phase1_summary.md](test_data/SmallOffice/smalloffice_20_redraw/phase1_vector/phase1_summary.md)：
   - 8 张图各自的可信度自评（高/中/低，含理由）
   - 哪些字段反复 null / unknowns
   - 4 立面 x_local ↔ 世界轴对照表（实际填写值）
   - 你对 schema v1 的反馈：哪里不够用 / 哪里冗余 / 哪些 pen 枚举值不够

## 边界

- 不要改 [src/](src/)、[skills/](skills/)、[AI_agent/](AI_agent/) 任何文件
- 不要改 1f_view.json（已是 worked example）
- 不要跑 `run_full_pipeline.py` 或任何 EnergyPlus 工具
- 不要产 IntakeOutput 字段（zone_specs / surface_specs / fenestration_specs / ... 等等），那全是 phase2 的事

ready 后先做 2f_view.png pilot，完成后停下来等我反馈。
