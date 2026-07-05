# 提案 · Reading 脚手架完整恢复(valid ∧ 兼容,不留缺漏)

> 日期：2026-06-27 ｜ 作者：Claude(出方案) ｜ 待 Codex 审方案
> 范围：**仅 reading(stage 0)**——`skills/intake_pipeline/0_reading/*` + `src/agent/reading/schema.py` + `src/validator/checks/reading.py`。1-5 后做。

## 0. 原则(用户 2026-06-27 ratify)
- **目标不是"Sonnet 达 sm21_pre 就停"**。北极星 = 弱/开源 VLM;脚手架=降智补偿。按 Sonnet 调到"刚好够"= 给目标欠配。
- **先补全**:旧脚手架(`127ba06` sm21_pre 时代)里 **`有效 ∧ 与新架构兼容`** 的约束**一条不漏**地补进当前脚手架。
- **后精简**:弱模型"文字约束过多会否适得其反"的顾虑 → **不在本轮预先砍**;留到后期用**检索库 / 代码化**等方式精简。本轮**先不要有缺漏**。
- **载体优先序**:能做成**确定性代码门**的优先代码门(弱模型跟 prose 更差;呼应"强制约束别交给 LLM 记得")。但本轮不强求全代码化(那是精简期的事)。
- **sm21_pre = 回归地板**:`score_reading_vs_gt` 实测=(a) 确认强模型没退化 +(b) 攒换弱模型要复用的评测 harness;**不是**逐条补一点就测一次的门。

## 1. 三类去向(基于 N1e `RECONCILED_candidates.md` 26 条 + N1f `RECONCILED.md` #50/禁字段门)

### ✅ 已落地(P0 批 6.25 + 本轮 6.27,确认在册、无需重做)
| 候选 | 内容 | 落点 |
|---|---|---|
| 1,2,4,12,16 | 坐标硬线 / testdata 锚定 / 一段一笔反例 / 错误预算 / dimensions[] 示例对齐 schema | guide §0.1/§5/§2(6.25) |
| 18 | uncaptured 载体/强度错位 | F2 对齐顶层 + door-heal CROSS_CHECK(6.27) |
| 17(部分) | 立面朝向口径冲突 §4 vs schema | F1 image-local 已消(6.27) |
| 14 | 反过度分割条款(NEW>OLD) | **保留不动**(6.22) |

### 🟢 应补(valid ∧ 兼容)——本轮恢复目标
| 候选 | 内容 | 建议载体 | 备注 |
|---|---|---|---|
| 5 | 每份 skill 文档"管什么"的作用说明 | prose(kickoff/guide 头) | 弱模型尤其需要知道三文档分工 |
| 6 | "re-trace"具体坐标示例(pen 画 (0,0)→(15,0)、窗 rect (1.4,1.0)→(3.8,2.8)) | prose(guide §2 示例旁) | 具体示例对弱模型价值高 |
| 7 | 图/输出清单表(2f/3f/各立面/supp 源→输出) | prose(kickoff 表已部分有→补全列) | 防漏图/漏输出 |
| 8 | worked-example 锚(指明范例文件+"不要重写") | prose(kickoff) | 现仅"follow the style"、补回路径锚 |
| 9 | 门 healing 护栏全文(只 heal 门符号/doorless 不 heal/窗不 heal/留痕) | **核对**:current §2.1 似已全有 → 若全有则标"已覆盖",缺则补 | Codex 核 old vs 现 §2.1 逐条 |
| 10 | 杂物 non-keep 警告全表(columns/beams/decorative/index arrows/grid/stair treads) | **核对**:current pen_library 表似更全 → 补 old 有现无的项 | Codex 核 old vs 现 pen_library |
| 11 | workflow 措辞自相含糊("stop then batch" vs "pilot then wait") | prose(kickoff workflow 消歧) | 一致性 |
| 15 | self-check 加 provenance/tick 项 | prose(guide §6 self-check list) | 与 reading-honest 配套 |
| 19 | schema 示例自相不一致(wall 例带 provenance、window/polyline 例不带,但 self-check 要求每条带) | prose(guide §2 把所有 stroke 示例补 provenance/confidence) | 一致性 |
| 20 | `pen:str`/`geometry:dict` 自由 vs 文档受限契约 | **代码门**(validator 校 pen∈合法集×image_kind〔现有 `_pen_kind` 已做〕+ geometry.kind∈{line,rect,polyline}) | 核现有 `_pen_kind` 覆盖到哪;geometry.kind 校验可补 |
| 21 | `image_kind` 扩 section/supplementary/other(schema)vs prompt 只 plan/elevation | prose(guide/pen 提一句扩展 kinds 的处置) | 一致性 |
| 26 | plan window 动作"which wall"措辞 vs "belongs-to 归 correction" | prose(pen_library 改:窗只记位置,父墙归 correction) | 防 reading 越界做拓扑 |
| **#50** | per-facade/floor 独立窗链(楼层间窗数/分布/blank 可不同、不复制 typical floor) | **reading 侧 prose(本轮)** + correction 侧 count/blank CROSS_CHECK gate(**stage-1 companion,1-5 时做**) | 旧硬约束、遗漏;reading 侧先补 recording 纪律 |
| **禁字段门** | `_FORBIDDEN_STROKE_KEYS` 漏挡 `is_exterior/parent_window_ids/rooms[]`(guide §5 反例有、门没覆盖) | **代码门**(扩 `_FORBIDDEN_STROKE_KEYS`) | 把 prose 反例升成机器门 |

### ⛔ 排除(arch-不兼容 或 已查实无效)——**不补**,本提案要 Codex 确认排除合理
| 候选 | 为何不补 |
|---|---|
| 3 | facade 四立面**世界轴映射表** = P1b 有意删;硬编码正交假设、在 C2/C4 斜交/多边形上**主动误导**,对弱模型更致命。本轮刚删,不可回。 |
| 22 | pen 集去 `other`/`stair` = 当前最小 pen 集**有意设计**;不回 other/stair pen(它们走 recognize→log)。 |
| 23 | 门"record two strokes" → "heal into one continuous wall" = 当前**正确设计**(误差预算归 reading heal);不回两-strokes。 |
| 25 | `room_labels`(RoomRoleObservation)= phase-1 role **有意新增**;保留。 |
| (prompt 强度) | A/B 已证伪非杠杆;不当"已验证约束"重塞。 |
| 13 | provenance/confidence/dimension_refs = reading-honest 新增、非旧约束;已在册,保留。 |

### 🔍 需 Codex 单独裁(validity/兼容性存疑)
- 候选 **24**(wall cue 从"粗黑实线/填充"偏向"encloses rooms/close a region"带拓扑味):是否轻微越线 reading↔correction 红线?建议**核**——若"encloses rooms"只作识别 cue(非拓扑判定)则保留,若诱导 reading 做闭区判断则收回纯视觉 cue。

## 2. 执行分解(focus reading,本轮)
1. **prose 补**(5,6,7,8,11,15,19,21,26 + #50 reading 侧 + 9/10 核后缺项):`guide.md`/`reading_guide.md`/`pen_library.md`/`session_kickoff.md`。
2. **代码门补**:① 禁字段门扩 `is_exterior/parent_window_ids/rooms`(`checks/reading.py` `_FORBIDDEN_STROKE_KEYS`);② geometry.kind 合法集校验(候选 20,若 `_pen_kind` 未覆盖);各加回归测试。
3. **stage-1 companion(记录、不做)**:#50 correction 侧 per-facade/floor count/blank CROSS_CHECK gate。
4. **不动**:reading-honest(13/14)、最小 pen 集(22)、heal 设计(23)、room_labels(25)、image-local(3 已删不回)、correction A1-A4+核、baseline。
5. **测**:冷启 Sonnet 用恢复后脚手架重读 sm21 + `score_reading_vs_gt` 对 gt → 回归地板 + harness。**不作逐条门**。

## 3. 给 Codex 的审阅需求(方案审)
1. **逐条核 9/10**:old `127ba06` phase1 vs 现 `0_reading` 的门-healing 护栏 / 杂物 non-keep 表,列出"old 有现无"的具体缺项(我没逐字 diff,凭 RECONCILED 候选)。
2. **核排除合理性**:3/22/23/25 排除是否都站得住(尤其有没有把"其实有效且兼容"的误排)。
3. **候选 24 裁定**:"encloses rooms" cue 是否越 reading↔correction 红线。
4. **候选 20 现状**:`_pen_kind`/schema 现在校到哪、geometry.kind 该不该补门。
5. **遗漏自查**:除 N1e 26 + N1f #50/禁字段门,old phase1 还有没有**两审都漏**的有效约束(独立扫一遍 old phase1 四文档)。
6. **载体判断**:我标"prose"的里有没有该升代码门的(本轮力所能及范围内)。

---

## 4. 决议(2026-06-27,Codex 方案审 APPROVE-WITH-CHANGES,Claude 全采纳)
- **候选 9** → 改判 **✅已覆盖**(现 §2.1 门-healing 护栏全在),**不重加**。
- **候选 10** → 收窄为**只补 `beam` / overhead 隐线** wording 进 pen_library(其余 columns/decorative/index/grid/stair treads/no-`other` 已覆盖)。
- **候选 24** → **保留现状**("encloses rooms/close a region" 是合法识别 cue、非拓扑输出)。
- **候选 20** → 代码门:`_pen_kind` 已挡非法 pen + 未知 geometry.kind,**但放过 `geometry.kind` 缺失** → 收紧"kind 必填且 ∈{line,rect,polyline}" + 补 polyline well-formed(points≥2)。
- **禁字段门** → `_FORBIDDEN_STROKE_KEYS` += {`is_exterior`,**`parent_wall_id`**,`parent_window_ids`,`rooms`}(Codex 自查:old prompt 显式禁 `parent_wall_id`,两审都漏)。
- **排除项 3/22/23/25/prompt 强度** → Codex 确认**全部正确排除**,无误排。
- **候选 7** → 本轮 prose;**未来**有 expected-image manifest 时升确定性完整性门。
- 据此进入执行(派 Codex,非 Claude)。
