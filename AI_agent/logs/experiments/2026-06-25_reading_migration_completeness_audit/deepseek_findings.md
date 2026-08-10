✅ 58 | ❌ 0 | ⚠️ 2 | 🗑 0

（说明：已迁条目按语义聚类统计，部分高度相似的旧约束合并为 1 条；冲突 2 条详述见后）

| 约束 (旧脚手架要求模型做/不做/保证什么) | 旧出处 | 新落点 | 桶 | 备注 |
|---|---|---|---|---|
| **角色分离**：阶段1只重描，不做空间拓扑（不合并笔划成房间、不判内外、不归属门窗、不封闭区域） | guide §0,§3; prompt “mental model” | 0_reading/guide.md §0,§3；自检 `no_topology_inferred` 保留 | ✅ | 术语 “phase” 改为 “stage”，约束等同 |
| **误差预算**：阶段1负责感知（见图像），阶段2负责推理（不见图像）；阶段1错误不可被阶段2纠正；阶段1宁 null 勿猜 | guide §0.1; prompt “error budget” | 0_reading/guide.md §0.1 扩展但保留核心；新增“双通道冗余”和“testdata 锚定”作为补充 | ✅ | 原始预算原则完全保留，额外增强了防御 |
| **模拟物理 → 门愈合**：EP 中墙无厚度、门被忽略 → 门开口必须愈合成连续墙；窗不愈合 | guide §0.2,§2.1; pen_library §1 door action | 0_reading/guide.md §0.2,§2.1；pen_library.md 保留相同动作 | ✅ | 门愈合规则（仅门符号、不愈无门开口、不愈窗、留痕）一字不差 |
| **单位与精度**：所有长度单位为米，保留两位小数 | guide §1 | 0_reading/guide.md §1 | ✅ | |
| **本地 2D 坐标系定义**：平面 x=世界东/y=世界北；立面 x=水平沿立面 (由 facade_axis_note 解释世界轴)/y=世界 z (上正) | guide §1 | 0_reading/guide.md §1 一字不差；但 schema 及下游仅接受 image-local（见冲突桶） | ⚠️ | 坐标轴声明未变，但与 facade 字段冲突，世界轴映射载体变更（详见冲突说明） |
| **scale_origin**：记录图像本地原点在世界位置；平面 world_z 为 null；立面基底标高 | guide §1,§2 JSON schema; self_check | 0_reading/guide.md §1,§2；代码 schema.py 保留 dict | ✅ | |
| **描画规则**：写所见，缺则 null，不凭背景知识补默认值 | guide §1 | 0_reading/guide.md §1 | ✅ | |
| **OCR 逐字**：文字绝不翻译，保留原文 | guide §1,§5 反例 | 0_reading/guide.md §1,§5 | ✅ | |
| **stroke 结构与厚度**：plan wall thickness_m 一律 null；door 不是 pen | guide §2 JSON, §0.2, §5; pen_library §2 | 0_reading/guide.md §2,§0.2,§5；pen_library.md §2,§4 反例 | ✅ | |
| **dimensions 转录**：所有尺寸链数字必须转录到 dimensions[] | guide §2,§6; pen_library §1 dimension-chain action | 0_reading/guide.md dimensions 结构大幅增强（chain_id/role/value_m/text_verbatim 等），自检 `all_dimensions_transcribed` 仍存在 | ✅ | 旧约束提升为结构化尺寸链，增加了闭合检查 (“per-floor window chain” 等从此受益) |
| **ocr_texts 转录**：文字标签逐字入 `ocr_texts[]` | guide §2 | 0_reading/guide.md §2 | ✅ | |
| **self_check 与 uncaptured 必填**：排除的元素、愈合的门等必须记入 `uncaptured_visual_elements`，且字段要求 non‑empty（即使无排除也要留备注） | guide §2,§5,§6; prompt “core discipline 4'” | 0_reading/guide.md JSON 注释仍说 “Even when … leave an explicit note”，但代码 `reading.py` 只检查存在且为 list，**不强求非空** | ⚠️ | 旧约束的强制力被代码检查放松，导致“防止静默丢失”的机制弱化（详见冲突说明） |
| **门愈合 guardrails**：仅对带门符号开口愈合；不愈无门开口；不愈窗；必须留痕（note + uncaptured） | guide §2.1 | 0_reading/guide.md §2.1 完全保留 | ✅ | |
| **禁止拓扑/世界字段**：stroke 不能有 `is_exterior`/`parent_window_ids`/`rooms[]`/`zone` 等 | guide §3,§5; prompt “core discipline 3” | 0_reading/guide.md §5 保留；代码 `reading.py` `_no_topology_fields` 强制（阻止 `zone`/`adjacent_zone` 等） | ✅ | 从纯 prompt 约束升级为代码门 |
| **禁止拆分连续墙**：一段连续墙必须是一个 stroke；门两侧愈合成一条 stroke；窗不打断墙 | guide §5; prompt “core discipline 5” | 0_reading/guide.md §5 明确 “one stroke per continuous stroke” 并增加 “window jamb / dimension ticks 不是墙” 的反例 | ✅ | |
| **立面 facade_axis_note 必须给出世界轴映射及方向（含四立面表格）** | guide §4,§6; pen_library 无直接；prompt “core discipline 7” | 0_reading/guide.md §4 完全保留旧表格；但 `schema.py` 规定世界轴不在此，而在 `correction`；`reading.py` 检查 elevation 时强制要求 `facade` 字段（view_facade 等），不依赖 `facade_axis_note` | ⚠️ | 旧约束载体被新架构去功能化，prompt 与 schema 严重不一致（详见冲突说明） |
| **立面 wall_fill 按楼层分割**：必须每层一个 wall_fill stroke，不能整面一个 | pen_library §3; guide §6 自检; prompt “core discipline 2'” | 0_reading/pen_library.md §3 保留，自检条目仍在 | ✅ | |
| **合法笔集**：plan 只能用 wall/window；elevation 只能用 wall_fill/window/outline；无 other/door 笔；禁止跨图像种类用笔；禁止发明笔 | pen_library §2,§4; prompt “core discipline 1,4” | 0_reading/pen_library.md §2,§4 保留；代码 `reading.py` `_pen_kind` 强制检查 | ✅ | |
| **分类动作映射（keep-set / ignore-set）**：楼梯、家具、柱、装饰等识别后不追踪，记录到 uncaptured；尺寸链和文字走对应数组；门触发愈合 | pen_library §1 | 0_reading/pen_library.md §1 映射表相同 | ✅ | |
| **立面窗户是窗口 z 的权威来源**（强调其 y_range 决定世界 z） | pen_library §1 elevation window action 注释 | 0_reading/pen_library.md 保留该注释 | ✅ | “absolute world z” 隐含在此，新 guide 未削弱 |
| **识别纪律**：基于不变线索而非固定风格；不确定时标注未知/低置信度，不强制分类 | reading_guide §0.1,§0.2,§I | 0_reading/reading_guide.md 相应部分保留 | ✅ | |
| **绘图类型限定**：仅 orthographic 平面、立面在 scope；其他类型识别并做相应处理 | reading_guide §A | 0_reading/reading_guide.md §A 保留 | ✅ | |
| **立面读取顺序**：轮廓→楼面线→wall_fill→窗→标高→附件 | reading_guide §E.0 | 0_reading/reading_guide.md §E.0 保留 | ✅ | |
| **识别自检项**：确定绘图类型、不变线索、解决混淆对、立面顺序、未知标记、逐字文本、不在此决定动作 | reading_guide §I | 0_reading/reading_guide.md §I 保留 | ✅ | |
| **工作流与边界**：先读三文档；参考已示例 JSON 风格；从 testdata_prompt.json 读元数据（仅用于尺寸/层高交叉检查，不复制到 JSON）；先做单张试点，等待审核再批处理；完成后写 reading_summary.md；不修改 src/、不运行 pipeline、不生成 IntakeOutput | prompt_template.md 全文 | 0_reading/session_kickoff.md 有对应工作流；0_reading/guide.md §0.1 含 “anchor against testdata totals … never copy” | ✅ | |
| **禁止将楼梯踏步追踪为墙** | pen_library §4 | 0_reading/pen_library.md §4 保留 | ✅ | |
| **禁止将立面门当作窗**（即使开口破坏 wall_fill） | 无（旧版 pen_library 仅说 door not drawn） | 0_reading/pen_library.md 新增反例 | ✅ | 旧约束隐含，当前显式强化 |
| **立面轮廓 outline 仅在提供额外 z 信息或不与 wall_fill 边缘重合时才单独记录** | guide §6 自检; pen_library §1 outline action | 0_reading/pen_library.md §1 保留；self_check 条目仍在 | ✅ | |
| **scale_origin.world_z_m 对 plan 必须填 null（不是 0.00）** | guide §6 自检 | 0_reading/guide.md 自检列表仍有此项 | ✅ | |
| **self_check.pens_used 列出实际使用的笔** | guide §6 自检 | 0_reading/guide.md 自检列表仍有此项 | ✅ | |
| **禁止从 testdata_prompt 直接复制内容到 JSON** | prompt_template.md | 0_reading/guide.md §0.1 明确 “never copy testdata content into the JSON” | ✅ | |
| **provenance / confidence / dimension_refs 与双通道冗余** | 无（这是 M1 新增） | 0_reading/guide.md §0.1 冗余通道；guide §2 新字段；schema.py 定义；reading.py 部分检查 | 🗑→新 | 非旧有，但可视为对旧“尺寸链转录”约束的加固；不属迁移遗漏 |

---

## ⚠️ 冲突 / 斩断 — 机制详述

### 1. 立面方向映射：从“模型硬写世界轴”到“image‑local”，prompt 未同步

**旧约束**  
`facade_axis_note` 必须写明局部 x 对应哪个世界轴及其增加方向（如 “South facade: local x = world x, increasing eastward”），并由模型严格遵循四立面表格填充。该约束要求 **模型在读取阶段即完成世界坐标映射**，并把结果写死在 JSON 元数据中。

**当前架构改变**  
- 代码侧 (`schema.py`) 引入 `FacadeOrientation`：`view_facade` 取自可信元数据（图像名/标签），`local_x_positive` 只用屏幕方向（`image_left_to_right` 等），**世界轴/符号/基面明确不在此**，全部推给 `1_correction` 推导。  
- 确定性检查 (`reading.py`) 对 elevation **强制要求** `facade` 字段且 `view_facade` 非空，若缺失立即 FAIL；而旧的 `facade_axis_note` 仅保留为 legacy 字段，不参与逻辑。  
- **但**`0_reading/guide.md` §1、§4 仍原封不动地包含了旧版的世界轴坐标系声明和四立面表，并要求模型照样填写 `facade_axis_note`。`session_kickoff.md` 只说 “fill the facade‑orientation fields exactly as the schema + guide.md define them”，却未说明新的 `facade` 结构是什么、是否取代 `facade_axis_note`。

**冲突后果**  
- 模型收到两条矛盾指令：prompt 要求填写包含世界轴的 `facade_axis_note`，代码检查却只要不含世界轴的 `facade` 字段。若模型仅按 prompt 输出 `facade_axis_note` 而未填 `facade`，**直接触发 `reading.py` INVARIANT 失败**（“elevation missing image‑local facade orientation”）。  
- 旧约束本身的功能（由模型判断并锁定世界轴映射）在新架构中**被去功能化**——即使模型填写了正确的世界轴，下游也仅依赖代码从 `view_facade` + `local_x_positive` 推导，不再信任模型的判断。这导致旧约束的载体（`facade_axis_note`）变成废字段，而模型被要求做出的“世界轴推理”反而可能引入本已避免的错误。

**为何不能简单视为“已迁移”**  
因为新的 image‑local 方向模型虽然等价保护了“朝向信息”，但 **prompt 未更新为新字段、检验门也不接受旧字段**。当模型按 prompt 行动时会被代码拒绝，导致 reading 阶段无法通过，形成 **机制性断裂**。必须同步更新 guide.md 和 pen_library/session_kickoff，明确 elevation 只需填写 `facade`（屏幕方向），并删除或降级 `facade_axis_note` 到“仅供人工审核”的程度。

### 2. `uncaptured_visual_elements` 非空要求被代码检测放松

**旧约束**  
`uncaptured_visual_elements` 必须是 **非空数组**，任何被排除的元素（家具、楼梯、装饰）或愈合的门都必须显式登记；即使字典已足够，也必须写一条备注，以杜绝“静默丢失”。该约束直接体现在旧 guide 的 JSON 注释、§5 反例、§6 自检列表中，属于必须遵守的核心纪律。

**当前架构改变**  
- 代码 `reading.py` 的 `_uncaptured_list` 检查 **只要求字段存在且为 list，不强求非空**；注释明确说明 “NOT required non‑empty — clean drawing → []”。  
- `0_reading/guide.md` 中 JSON example 的注释仍保留 “Even when … leave an explicit note rather than an empty default”，即 **prompt 端仍维持旧约束**。

**冲突后果**  
- 模型若遵循 prompt 仍会填写备注，但如果某次会话中模型忽略该句、输出空 `[]`，**代码不会拦截**，与旧架构“强制门”的效果相悖。  
- 旧约束的核心理念——用强制非空来阻止“我觉得没有排除所以不写”的认知偏差——被代码的宽松标准削弱，可能导致信息丢失风险回升。

**为何不能归为“有意删”**  
因为 prompt 文档未同步删除该要求，且旧约束的存在理由（door healing 痕迹、clutter 清单审计）依然有效。当前矛盾在于：代码门的设计者可能认为“空列表在干净图纸中是合理的”，但与旧约束的防御逻辑冲突。需要决定是让代码恢复非空检查，还是更新 prompt 放弃强制非空但通过其他机制（如显式 `uncaptured` 的 note 字段）补偿。

---

> **结论**：两条冲突均源自“代码/ schema 已按新架构更新，而 0_reading 技能文档仍沿用旧两步法文本”，导致 LLM 收到的 instruction 与下游验收条件脱节。修复方向为统一 prompt 与代码门，否则 reading 阶段的产出将不可接受或质量退化。