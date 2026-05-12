# Vector Schema v1.2 — phase1 输出格式（"用语义笔重画原图"）

> v1.2（2026-05-12，sm_20 跑完后微调）：(a) plan 的 `scale_origin.world_z_m` 显式约定一律 null；(b) 自检清单加 outline 重合检查项。
>
> v1.1（2026-05-12）：在 v1 基础上**拆分 plan / elevation 的 pen 词典**，门统一从必需词典移除，立面墙身灰填充约定"逐层一个 wall_fill"，新增 `uncaptured_visual_elements` 字段。
>
> v1 取代 v0。v0 把房间归组 / 内外分类 / 父子映射混进 phase1，违反"phase1 只识图、phase2 才做拓扑"的分工。v1 修正。

---

## 0. 心智模型

把 phase1 想成"用一套**带语义标签的笔**把原图重新描一遍"：
- "**墙笔**" 描所有墙画过的笔触
- "**窗笔**" 描所有窗画过的笔触
- ……外加尺寸链、文字标注

**phase1 干的事**：辨认每一笔是哪种构件类型，按类型分类描出几何形状
**phase1 不干的事**：把多笔合并成"一面外墙" / 圈出"这是一个房间" / 说"这扇窗属于哪面墙" / 判"这堵墙朝外还是朝内"

那些拓扑推理全部留给 phase2。

### 0.1 误差预算（重要）

phase1 和 phase2 在误差类型上是完全互斥的：

| 阶段 | 看得到的 | 可能引入的误差 |
|---|---|---|
| phase1 | 原图（多模态） | **识图误差**：尺寸读错、笔触遗漏、坐标偏移、立面 x 轴方向搞错 |
| phase2 | phase1 JSON + skills 规则文档 + testdata_prompt 元信息（**不看图**）| **纯推理误差**：归组错误、内外判错、父子映射错、IntakeOutput 字段写错 |

**推论**：
- 所有"图上某数值 / 位置 / 笔触类型"的错都必须在 phase1 截断。phase1 一旦写错，phase2 没机会回溯纠正
- POC Step 5 diff 评估时，IntakeOutput 中任何与原图视觉相关的不一致，根因 100% 落在 phase1；任何拓扑 / 命名 / 字段格式错才是 phase2 的事
- 所以 phase1 写 JSON 时**宁可填 null 也不要瞎猜**——null 是"我没看清"，瞎猜的数值会让 phase2 把错的数当真的算

### 0.2 仿真物理特性的影响

EnergyPlus 的 zone 由 **surface（2D 面）**围合，墙没有厚度的概念。所以：
- plan 上的"粗黑墙"在仿真里就是一条 **centerline**（2D 折线），墙身宽度不参与计算
- phase1 不必费力估墙厚——`thickness_m` 字段一律填 `null`
- 立面 `wall_fill` 矩形只用作 z 范围信号源（哪层 z 在哪段），不代表"墙有多厚"

---

## 1. 全局约束

- **单位**：米，两位小数
- **每张图自带本地 2D 坐标系**：
  - `image_kind="plan"`：x = 世界 x（东向），y = 世界 y（北向）
  - `image_kind="elevation"`：x = 沿该立面的水平方向（`facade_axis_note` 说明对应世界哪条轴含符号），y = 世界 z（向上为正，地面 z=0）
  - `image_kind="section"`：按图实际定义，在 `facade_axis_note` 里说明
- **scale_origin** 记录本图本地 (0,0) 在世界系下的位置
- **描摹规则**：图上画了什么写什么，找不到填 `null`，禁止从背景知识补默认值
- **文字标签 OCR 原样**，不翻译

---

## 2. JSON Schema

```jsonc
{
  // ===== 元数据 =====
  "image_label": "Floor 1 plan view",       // 用 testdata_prompt.json 里的官方 label
  "image_kind": "plan | elevation | section | other",
  "facade_axis_note": null,                 // elevation 必填，否则 null
                                            // 例: "South facade: local x = world x, increasing eastward"
                                            //     "North facade: local x = -world x, i.e. x_local increasing = world westward"
  "scale_origin": {
    "world_x_m": 0.00,                      // 本图本地 (0,0) 在世界 x 的位置
    "world_y_m": 0.00,                      // 本图本地 (0,0) 在世界 y 的位置
    "world_z_m": null,                      // plan: 一律 null（z 由立面尺寸链给）; elevation: 该立面底标高（地面通常 0.00）
    "note": "本图本地原点 = 整栋投影 SW 内角"
  },

  // ===== 笔触 =====
  // 每根 stroke = 一根连续画出的笔触 + 该笔的语义类型 (pen)。
  // 如果一根本应连续的笔被开洞（如墙上挖了门洞）打断成两段，记两个 stroke。
  "strokes": [
    {
      "id": "S1",
      "pen": "wall",                        // 枚举: wall | window | door | stair | other
                                            // other 用于无法归类的可见笔触（如指北针、标题块）
      "geometry": {
        "kind": "line",                     // line | rect | polyline | arc
        "p1": [0.00, 0.00],
        "p2": [15.00, 0.00],
        "thickness_m": null                 // plan 墙一律 null（EP zone 由 surface 围合，墙无厚度）
      },
      "note": ""                            // 自由文字，比如"南侧水平外周墙"
    },
    // 矩形填充示例（立面图墙身、立面图窗）
    {
      "id": "S99",
      "pen": "window",
      "geometry": {
        "kind": "rect",
        "x_range_m": [1.40, 3.80],          // 本图本地坐标
        "y_range_m": [1.00, 2.80]
      },
      "note": "shouth facade F2 window 1"
    },
    // polyline 示例（非直线墙）
    {
      "id": "S100",
      "pen": "wall",
      "geometry": {
        "kind": "polyline",
        "points": [[0,0],[5,0],[5,3],[8,3]],
        "thickness_m": 0.30,
        "closed": false
      },
      "note": ""
    },
    // arc 示例（门的开启弧线）
    {
      "id": "S101",
      "pen": "door",
      "geometry": {
        "kind": "arc",
        "center": [5.00, 2.00],
        "radius": 0.90,
        "start_deg": 0,
        "end_deg": 90
      },
      "note": "door swing arc"
    }
  ],

  // ===== 尺寸链（结构化复合图元）=====
  // 视觉上"两端 tick + 中间数字"是一个 chunk，单独成类；phase2 才用它推坐标
  "dimensions": [
    {
      "id": "D1",
      "text": "15.00",                      // 原样抄录尺寸链数字
      "from": [0.00, 0.00],
      "to":   [15.00, 0.00],
      "axis": "x",                          // x | y | z（z 仅 elevation）
      "note": "底部总长链"
    }
  ],

  // ===== 文字标注 =====
  "ocr_texts": [
    {"id": "T1", "text": "Office 101", "anchor": [3.00, 1.50], "note": ""}
  ],

  // ===== 自检 =====
  "self_check": {
    "all_dimensions_transcribed": true,     // 尺寸链数字是否全部抄录
    "all_visible_strokes_captured": true,   // 所有可见笔触是否都进了 strokes 数组
    "no_topology_inferred": true,           // 是否克制住没去归房间 / 判内外 / 配父子
    "pens_used": ["wall"],                  // 本图实际用到的 pen 值（去重）
    "unknowns_noted": [
      "墙厚未标尺寸 → strokes[*].thickness_m 为 null"
    ],
    "uncaptured_visual_elements": [
      // 看到但无法归入当前 pen 词典的可见笔触；为空数组表示词典够用
      // 例: "South_view 顶部出现一根斜线檐口装饰，未归入 other 是否合适？"
    ]
  }
}
```

---

## 3. pen 枚举说明（按 image_kind 拆）

**重要**：plan 和 elevation 用不同的 pen 合法值集。phase1 必须按图的 `image_kind` 选对应词典，不要跨用。

### 3.1 image_kind = "plan" 合法 pen

| pen 值 | 视觉特征（典型）| 何时用 |
|---|---|---|
| `wall` | 粗黑实线 / 黑色填充矩形条 | 任何一根识别为墙的笔触 |
| `window` | 墙体上挖洞 + 蓝色短条（仅当 plan 上确实画了窗）| 窗（sm_20 plan 没画窗）|
| `stair` | 平行斜线 / 楼梯踏步符号 | 楼梯 |
| `other` | 上述都不是但确实画了 | 指北针、轴网编号、家具、标题块 |

**plan 不收 `door`**——仿真不需要门，平面上的门弧 / 门洞一律忽略不进 strokes（除非用户后续明确要门）。

### 3.2 image_kind = "elevation" 合法 pen

| pen 值 | 视觉特征（典型）| 何时用 |
|---|---|---|
| `wall_fill` | 浅灰填充矩形（一层一块）| **每层墙身一个 wall_fill stroke**（见 §3.3）|
| `window` | 蓝色填充矩形 | 立面窗 |
| `outline` | 立面整体外轮廓粗线 | 仅当外轮廓与 wall_fill 边不重合 / 单独画了一根整体外框 |
| `other` | 上述都不是但确实画了 | 分层线（楼板分界）、结构线（柱梁）、装饰线（线脚 / 檐口）、立面索引箭头、阴影 |

**elevation 不收 `door`**——和 plan 同理，主入口门可在 note 里记一笔但不进 strokes。

**`other` 的处理**：见到不进枚举的笔触统一标 `other` + note 里描述"这是分层线"或"这是檐口装饰"。不要为每类装饰新造 pen 值——POC 阶段保持最小词典。

### 3.3 立面 wall_fill 的约定（关键）

立面墙身灰填充按"**每层一个 wall_fill stroke**"记。例：

- South_view 是 3 层办公楼 → 出 3 个 wall_fill stroke，分别覆盖 F1 / F2 / F3 的灰填充矩形（按 y 范围分）
- 即使灰色看上去是连续一整块（无明显分层缝），只要尺寸链标出了每层 z 范围，仍按 3 个 stroke 写，phase1 借尺寸链分层
- 一层内若灰填充因门洞 / 窗洞**完全打断**（窗框周围有白色无填充区），按打断后的矩形段各自记一个 stroke；但 sm_20 立面窗是叠加在灰填上的，**不打断 wall_fill**，仍是一层一个

phase2 拿到逐层 wall_fill 后直接映射为每层 wall surface 的 z_floor / z_top，比"整面墙一个 fill 再拆"省事。

### 3.4 视觉识别 vs 空间拓扑（再次强调）

判 wall vs window vs wall_fill vs other 是**视觉识别**层面的判断（笔的样子不同），属于 phase1 范畴。
判 wall 是 ext vs int / window 属于哪面 wall / 多面 wall 围成哪个 room / wall_fill 哪层对应 plan 哪个 zone ←—— 这些是**空间拓扑**判断，全留给 phase2。

---

## 4. 立面图特别注意

`facade_axis_note` 必须包含本地 x 轴对应世界哪条轴 + 增方向（含符号）：

| 立面 | facade_axis_note 例 |
|---|---|
| South | `"South facade: local x = world x (increasing eastward); local y = world z"` |
| North | `"North facade: local x = -world x (local x increasing = world westward); local y = world z"` |
| East | `"East facade: local x = world y (increasing northward); local y = world z"` |
| West | `"West facade: local x = -world y (local x increasing = world southward); local y = world z"` |

立面图的窗 stroke 用 `geometry.kind="rect"` + `x_range_m` / `y_range_m`（本图本地坐标），phase2 用 `facade_axis_note` 翻回世界系。

---

## 5. 反例

- ❌ `"pen": "wall", "is_exterior": true` —— is_exterior 是 phase2 判，不要加字段
- ❌ 把房间多边形塞进 strokes —— 房间不是画出来的笔触
- ❌ `"pen": "wall", "parent_window_ids": [...]` —— 父子关系是 phase2 推
- ❌ 把同一根连续墙拆成 10 段小 stroke —— 一笔到底就一个 stroke；除非真的被开洞打断
- ❌ `"text": "办公室"` 当原图写的 "Office 101" —— OCR 不翻译
- ❌ `"thickness_m": 0.20` —— plan 墙一律 null（仿真不需要墙厚，见 §0.2）
- ❌ 用瞎猜的数值替代 null —— 宁可填 null（"没看清"），不要让 phase2 把错值当真值算（见 §0.1）
- ❌ plan 上画了 `"pen": "wall_fill"` —— wall_fill 只在 elevation 词典里
- ❌ elevation 上画了 `"pen": "wall"` —— elevation 的墙用 wall_fill；wall 这个值 plan 专用
- ❌ 立面整面墙一个 wall_fill —— 应"每层一个 wall_fill"（见 §3.3）
- ❌ 为门 / 家具 / 装饰线新造 pen 值如 `"furniture"` / `"cornice"` —— POC 阶段不扩词典，归 `other` + note 描述

---

## 6. 自检清单

- [ ] 按 image_kind 选对了 pen 词典（plan 用 §3.1，elevation 用 §3.2）
- [ ] 每根可见的 wall/window/wall_fill 笔触都进了 strokes 数组，pen 字段对
- [ ] elevation 墙身按"每层一个 wall_fill"切分
- [ ] 没有 rooms[] / is_exterior / parent 关系等拓扑字段
- [ ] 没有 door / 家具 / 装饰类的独立 pen 值（都归 other 或不记）
- [ ] 尺寸链每个数字都进了 dimensions 数组
- [ ] 文字标签原样抄
- [ ] 找不到的字段填 null
- [ ] 立面图 facade_axis_note 含轴向 + 符号
- [ ] 立面 outline：若与 wall_fill 边重合则不单独画（schema §3.2）；已确认本图情况
- [ ] plan 的 scale_origin.world_z_m 为 null（不要写 0.00）
- [ ] self_check.pens_used 列出本图用到的 pen 集
- [ ] self_check.uncaptured_visual_elements 列出词典覆盖不到的笔触

---

## 7. 与下游契约

phase2 接收一组 v1 JSON（每图一份）+ testdata_prompt.json + skills/energyplus_mcp/*.md，重建拓扑：
- 把多根 wall stroke 围合的封闭区域识别为房间 / zone
- 判每根 wall 的 is_exterior（看是否在外周）
- 把每根 window stroke 映射到 parent wall
- 立面 stroke 翻回世界坐标，做 plan ↔ elevation 一致性核验
- 输出 IntakeOutput Pydantic

phase1 的输出不是 IntakeOutput，**也不应直接和 IntakeOutput 字段对齐**。phase1 的产物只是"重新描了一遍图"。
