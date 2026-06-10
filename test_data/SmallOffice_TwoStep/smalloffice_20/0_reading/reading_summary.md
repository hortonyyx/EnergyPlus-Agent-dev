# phase1 vector — sm_20 redraw 总结

> 用户指示：supp_plan 不做。本次产出 7 张 JSON（1f 由人工 worked example + 本会话做的 2f / 3f / 4 个立面）。

## 1. 每图可信度自评

| 图 | 文件 | 可信度 | 理由 |
|---|---|---|---|
| 1f_view | `1f_view.json` | 高（worked example，未改） | 14 zone 网格规整，尺寸链对得上 3+3+3+3 = 15 / 3+2+3 = 8 |
| 2f_view | `2f_view.json` | 高 | 顶 4×3.75 + 底 3×5.00 + 走廊整通；外形 15×8 与 1f 一致 |
| 3f_view | `3f_view.json` | 高 | 顶整通 + 走廊整通 + 底 2×7.50；4 zone 与 testdata thermal_zones=4 自洽 |
| South_view | `South_view.json` | 高 | F1/F2 各 3 窗，窗位 x 由 1.40+2.40+2.50… 链严格闭合；F3 无窗 |
| North_view | `North_view.json` | 中 | F2 4 个窗（1.75 宽，3 种墩 1.40/1.65/1.90）与 South 的 3 个窗（2.40 宽）不对称——已照画但 sm_20 立面非对称是设计如此还是测试图设定，phase1 不判 |
| East_view | `East_view.json` | 高 | F3 单窗 1.00×2.40，居中（3.50/1.00/3.50）；F1/F2 无窗 |
| West_view | `West_view.json` | 高 | 与 East 图视觉完全一致，单 F3 居中小窗；本地 x 方向语义不同，已在 facade_axis_note 区分 |

## 2. 反复 null / unknowns

- `strokes[*].geometry.thickness_m` 全 null（plan 墙厚仿真无需，schema §0.2）
- 所有 plan 的 `scale_origin.world_z_m` 填 null（z 由立面尺寸链给）
- 所有图 `ocr_texts` 空——sm_20 测试图没有任何文字标签
- plan 上无窗、无楼梯、无指北针，`pens_used` 只有 `["wall"]`
- elevation 外周轮廓与 wall_fill 边重合，未单独画 `outline` stroke

## 3. 立面 local x ↔ 世界轴对照（实际填写值）

| 立面 | scale_origin (world) | facade_axis_note | 本地 x 增向 |
|---|---|---|---|
| South | (0, 0, 0) | local x = world x (increasing eastward); local y = world z | world x+ |
| North | (15, 8, 0) | local x = -world x (local x increasing = world westward); local y = world z | world x− |
| East | (15, 0, 0) | local x = world y (increasing northward); local y = world z | world y+ |
| West | (0, 8, 0) | local x = -world y (local x increasing = world southward); local y = world z | world y− |

phase2 翻回世界坐标的公式（每立面）：

- South: `X_world = x_local`, `Y_world = 0`, `Z_world = y_local`
- North: `X_world = 15 - x_local`, `Y_world = 8`, `Z_world = y_local`
- East: `X_world = 15`, `Y_world = x_local`, `Z_world = y_local`
- West: `X_world = 0`, `Y_world = 8 - x_local`, `Z_world = y_local`

## 4. 对 schema v1 的反馈

### 不够用 / 不顺手处

1. **plan 的 `scale_origin.world_z_m` 字段语义模糊**：plan 视图本来 z 不在画面里，但 schema 把 world_z_m 列作必填字段。本次全填 null + note 说明，但实际可以考虑：要么把 world_z_m 标为 plan 可省略，要么允许 plan 显式留空。
2. **立面"楼板厚度"无处安放**：South/North 立面 F1 窗顶到 F2 窗 sill 的 0.80 + 1.00 = 1.80 m 这一段，里面其实隐含"楼板"，但 phase1 看不出来。phase2 拿到尺寸链就好。schema 不需要改，只是提示文档可以说一句"楼板分层带由立面 wall_fill 的 y_range 邻接关系隐含"。
3. **`uncaptured_visual_elements` 这次全是空数组**——sm_20 太干净（没檐口、没分层线、没柱梁）。这个字段在更复杂的测试图上才有价值，本次没法验证 schema §3.4 的兜底机制是否够用。建议下一个测试图（带檐口/索引线/家具）专门压一压。
4. **立面 outline 的"重合就不画"约定有点隐式**：本次 4 个立面都未画 outline，全靠 wall_fill 边充当外轮廓。schema §3.2 有写"仅当外轮廓与 wall_fill 边不重合时画"，但读 schema 时容易漏。建议在自检清单里加一条 "[ ] 检查 outline：若与 wall_fill 重合则不画，已确认本图情况"。
5. **plan 上"垂直内墙是否到走廊"靠 stroke 端点判**：sm_20 2f 顶排 vs 底排的垂直内墙都只到走廊边缘 (y=3 或 y=5) 不穿过走廊。这点没有在 schema 中明确，本次按"图上画到哪就到哪"处理。phase2 应当也是这么解读，但 schema 可以加一句"垂直内墙的 stroke 端点 = 图上实际起止；走廊穿不穿过看图"。

### 冗余处

- `geometry.thickness_m` 字段对 plan 一律 null——既然永远 null，是否可以从 plan stroke 的 schema 中直接删？保留是为了让 plan / elevation 共用一个 stroke schema，但 elevation 又是 `kind=rect` 用 `x_range_m`/`y_range_m`，本来就不用 thickness_m。建议：plan stroke 删掉 thickness_m。

### pen 枚举值的反馈

本次 7 张 JSON 用到的 pen 集合：
- plan: 仅 `wall`
- elevation: `wall_fill`, `window`

未触发：`stair` / `other`（plan 词典）、`outline` / `other`（elevation 词典）。

POC 阶段词典对 sm_20 完全够用。但 sm_20 是规整办公楼测试图，是词典的"舒适区"。真要泛化建议：

- **plan 上的"楼梯"和"电梯井"**：sm_20 没楼梯也没电梯，3 层楼怎么上下？测试图本身缺这一块。建议在做下一个测试图时画楼梯，触发 `stair` pen。
- **elevation 上的"楼板分界线"应不应该单独成一类**：当前归 `other`，但实际上"楼板线"是 phase2 验证立面分层 z 范围的强信号。建议未来扩 pen 词典加 `floor_line` （但 POC 阶段先不动）。
- **入口大门**：sm_20 立面看不到主入口门洞，schema 当前说"立面 door 不收 / 主入口在 note 里记一笔"。下个测试图若画了入口雨棚 / 入口门洞，要试一下 schema 的"note 兜底"是否足够。

### 总评

schema v1 对 sm_20 这种"规整办公楼 + 干净图纸"够用，7 张 JSON 全部 self_check 通过且 `uncaptured_visual_elements` 全空。但 sm_20 是简单情形，schema 对复杂图的健壮性（檐口 / 装饰 / 索引箭头 / 家具 / 楼梯）本次没压出来。建议下一轮 POC 故意拿一张带噪声的图试。
