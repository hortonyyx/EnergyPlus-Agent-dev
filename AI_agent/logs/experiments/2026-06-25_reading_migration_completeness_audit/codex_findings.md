# 旧脚手架 -> 当前 0-5 reading 架构约束/能力迁移完整性通查

日期：2026-06-25

范围：
- 迁移源：`AI_agent/logs/review/2026-06-25_scaffold_degradation_audit/old_scaffold_127ba06/{guide.md,reading_guide.md,pen_library.md,prompt_template.md}`
- 当前 reading：`skills/intake_pipeline/0_reading/{guide.md,reading_guide.md,pen_library.md,session_kickoff.md}`
- 当前代码载体：`src/agent/reading/schema.py`，`src/validator/checks/reading.py`，`src/agent/reading/legacy.py`，`src/agent/correction/{deterministic.py,envelope.py}`，以及实际接线处 `src/agent/pipeline.py` / geometry kernel

方法：从旧脚手架逐项抽约束/能力，再核当前 prompt、schema、validator、pipeline、correction/core/kernel 是否仍承载。未以同目录 `RECONCILED_candidates.md` 为枚举边界。

## 总表

| # | 约束 / 能力 | 旧出处 | 新落点 | 桶 | 备注 |
|---:|---|---|---|---|---|
| 1 | reading/phase1 是“用语义画笔重描原图”，只识别并描几何，不做空间拓扑 | `old_scaffold_127ba06/guide.md:22-36`; `prompt_template.md:9-21` | `skills/intake_pipeline/0_reading/guide.md:22-36`; `session_kickoff.md:3-6`; `src/agent/pipeline.py:291-297` | ✅ 已迁 | stage 名从 phase1/phase2 改为 reading/correction；职责边界保留。 |
| 2 | 误差预算：reading 看图，correction 不看图；感知错误必须在 reading 捕获 | `guide.md:38-54`; `prompt_template.md:23-33` | `skills/intake_pipeline/0_reading/guide.md:38-70`; `src/agent/pipeline.py:291-303` | ✅ 已迁 | 当前还补强为“冗余维度通道必须挣得”：`dimensions[]` + `provenance=dimension_derived`。 |
| 3 | `null` 优先于猜测；不从背景知识补默认值 | `guide.md:52-53,79-80`; `prompt_template.md:30-31,92-93` | `skills/intake_pipeline/0_reading/guide.md:65-66,95-96,354`; `session_kickoff.md:27-28,36` | ✅ 已迁 | prompt 保留；schema 不强制“未找到必须 null”。 |
| 4 | `testdata_prompt.json` 只作尺寸/楼层数交叉校验，不可替代看图 | `prompt_template.md:58-60` | `skills/intake_pipeline/0_reading/guide.md:59-62`; `session_kickoff.md:27-28`; `src/agent/pipeline.py:330-343` | ✅ 已迁 | 当前 guide 明确“anchor against totals”但禁止复制。 |
| 5 | EP 物理抽象：墙是 2D surface/中心线；不估墙厚；门在能耗中忽略 | `guide.md:55-66,120,203-210,269` | `skills/intake_pipeline/0_reading/guide.md:71-82,139,261-268,334`; `pen_library.md:19,22,90` | ✅ 已迁 | `thickness_m=null` 仍是 prompt 约束；reading linter 尚未单独检查 plan wall thickness。 |
| 6 | 单位为米、输出两位小数 | `guide.md:70-72` | `skills/intake_pipeline/0_reading/guide.md:86-88`; `src/validator/checks/reading.py:34` | ✅ 已迁 | 两位小数主要是 prompt；代码按 0.01 m 容差做部分一致性检查。 |
| 7 | 每张图有本地图坐标；plan/elevation/section 分图解释 | `guide.md:72-78`; `reading_guide.md:90-97` | `skills/intake_pipeline/0_reading/guide.md:88-94`; `reading_guide.md:90-99`; `src/agent/reading/schema.py:31-32` | ✅ 已迁 | “local coordinates”保留；“world 轴/基准”承重部分见冲突桶 #51/#52 和删除桶 #55。 |
| 8 | OCR 原文照录，不翻译 | `guide.md:81,268`; `reading_guide.md:304-310,398`; `prompt_template.md:95` | `skills/intake_pipeline/0_reading/guide.md:97,333,353`; `reading_guide.md:306-311,400`; `pen_library.md:29` | ✅ 已迁 | prompt 保留；无自动 OCR 语言门。 |
| 9 | 启动工作流：先读三份规则文档和 worked example；一张 pilot 后停；不改代码/不跑 EP/不产 IntakeOutput | `prompt_template.md:37-45,97-113` | `skills/intake_pipeline/0_reading/session_kickoff.md:11-19,47-61` | ✅ 已迁 | 当前 kickoff 刻意变成“指针清单”，避免 durable rules 双写漂移。 |
| 10 | 每图输出独立 JSON，plan/elevation 文件按 case 表枚举 | `prompt_template.md:46-57` | `skills/intake_pipeline/0_reading/session_kickoff.md:38-46`; `src/agent/pipeline.py:70-92` | ✅ 已迁 | pipeline 稳定排序读取 `*_view.json`。 |
| 11 | 输出容器：`strokes[]` / `dimensions[]` / `ocr_texts[]` / `self_check` | `guide.md:85-198` | `skills/intake_pipeline/0_reading/guide.md:101-257`; `src/agent/reading/schema.py:35-47,55-72,109-130` | ✅ 已迁 | schema 将 `self_check` 设为可选 dict，实际承重转向 typed fields + linter。 |
| 12 | dimension-chain 是独立复合 primitive；每个数字必须进 `dimensions[]` | `guide.md:161-171,284`; `reading_guide.md:255-265`; `pen_library.md:27-28` | `skills/intake_pipeline/0_reading/guide.md:186-230,352`; `src/agent/reading/schema.py:55-72`; `src/validator/checks/reading.py:333-363,382-417` | ✅ 已迁 | 当前升级为 P1a：`text_verbatim/value_m/chain_id/role/order/anchor`，并有 parse/axis/closure 检查。 |
| 13 | 冗余通道：坐标若由尺寸链支撑，必须显式标注来源 | 旧脚手架只有“尺寸链供 phase2 推导”的能力：`guide.md:161-163` | `skills/intake_pipeline/0_reading/guide.md:52-58,132-134,180-184`; `src/agent/reading/schema.py:43-45`; `src/validator/checks/reading.py:420-512` | ✅ 已迁 | 这是当前架构新增的等价增强：用 `provenance/confidence/dimension_refs` 防止“correction 会修”软化坐标。 |
| 14 | plan/elevation 使用不同最小 pen set；不得 cross-use；无 `door` / `other` pen | `pen_library.md:10-11,55-63,81-90`; `prompt_template.md:64-69` | `skills/intake_pipeline/0_reading/pen_library.md:10-11,55-63,81-92`; `src/validator/checks/reading.py:27-29,266-284` | ✅ 已迁 | 这是 prompt -> code gate 的实迁：非法 pen x image_kind 会 fail invariant。 |
| 15 | keep-set 只有 wall/window/wall_fill/outline/dimensions/levels/text；其他识别后忽略并记录 | `pen_library.md:17-51,45-51` | `skills/intake_pipeline/0_reading/pen_library.md:17-51,45-51`; `src/validator/checks/reading.py:51-59,86-95` | ✅ 已迁 | 行为仍主要靠 prompt；linter 只验证 `uncaptured` 是 list，不验证“每个忽略项都记录”。 |
| 16 | 门洞 healing：只由门符号触发；不画 door；不 heal 无门大开口；不 heal 窗；heal 必留 trace | `guide.md:105-110,203-225`; `pen_library.md:22,90`; `prompt_template.md:70-75` | `skills/intake_pipeline/0_reading/guide.md:121-126,261-283`; `pen_library.md:22,90`; `guide.md:325-326,351`; `src/validator/checks/reading.py:27-29,266-284` | ✅ 已迁 | “无 door pen”有代码门；“只 heal 正确门洞”仍需 VLM/judge/人工看图。 |
| 17 | 一条连续墙一笔；门/窗不应把墙切碎；不得把窗洞 jamb/尺寸 tick/家具造伪墙 | `guide.md:264-267`; `prompt_template.md:89-91` | `skills/intake_pipeline/0_reading/guide.md:322-331,347-348`; `reading_guide.md:153-155`; `src/validator/checks/reading.py:420-512` | ✅ 已迁 | 当前新增 stroke-dimension consistency flag 抓“维度累计位置伪墙”的一部分；窗洞 jamb 仍主要靠 prompt + judge。 |
| 18 | reading 禁止拓扑字段：rooms、is_exterior、parent-child、belongs-to、inside/outside | `guide.md:229-239,259-264,281`; `prompt_template.md:79-80` | `skills/intake_pipeline/0_reading/guide.md:287-297,317-322,349`; `src/validator/checks/reading.py:30-31,74-75,287-302` | ✅ 已迁 | prompt 完整保留；代码门只禁 `zone/adjacent_zone/adjacent_surface/obc/world_z`，未覆盖旧例 `is_exterior/parent_wall_id/rooms[]`。 |
| 19 | downstream/correction 才负责闭区识别、is_exterior、window-parent、立面转世界、IntakeOutput | `guide.md:295-306` | `skills/intake_pipeline/0_reading/guide.md:363-374`; `src/agent/pipeline.py:291-309,687-699` | ✅ 已迁 | 当前进一步把 surface/fenestration 生成移到 deterministic geometry kernel。 |
| 20 | elevation `wall_fill`：一层一个，即使视觉连续也按楼层拆；完全断开的开口可拆段 | `pen_library.md:25,67-77,85`; `guide.md:279-280`; `reading_guide.md:216-237` | `skills/intake_pipeline/0_reading/pen_library.md:25,67-77,85`; `reading_guide.md:216-239`; `guide.md:348` | ✅ 已迁 | prompt 保留；reading linter 尚无“wall_fill count == floor count / per-floor z band”门。 |
| 21 | elevation `outline` 仅在独立且提供额外 z/顶轮廓时画；与 wall_fill 边重合则记录不画 | `pen_library.md:26`; `reading_guide.md:239-249`; `guide.md:288` | `skills/intake_pipeline/0_reading/pen_library.md:26`; `reading_guide.md:241-251`; `guide.md:356` | ✅ 已迁 | prompt 保留。 |
| 22 | elevation 识读顺序：outline -> 楼层线 -> per-floor wall_fill -> window grid/openings -> level markers -> attachments | `reading_guide.md:214-226` | `skills/intake_pipeline/0_reading/reading_guide.md:216-228` | ✅ 已迁 | 完整保留。 |
| 23 | elevation window 用 rect 的 `x_range_m/y_range_m`，立面窗是 window z 的权威图像来源 | `guide.md:124-133,254-255`; `pen_library.md:21`; `reading_guide.md:221-224` | `skills/intake_pipeline/0_reading/guide.md:143-152,312-313`; `pen_library.md:21`; `src/agent/correction/envelope.py:230-254` | ✅ 已迁 | reading 仍输出 rect；最终 world window z 由 correction/core 承载，见 #49/#50。 |
| 24 | 识别用 invariant cue，不背固定画法；样式变体非穷举；颜色只能弱提示 | `reading_guide.md:20-33,105-118,122-137` | `skills/intake_pipeline/0_reading/reading_guide.md:20-33,105-118,122-137` | ✅ 已迁 | 完整保留。 |
| 25 | 不确定时 low-confidence / unknown 并记录，不能强塞错类或静默丢弃 | `reading_guide.md:34-42`; `pen_library.md:43` | `skills/intake_pipeline/0_reading/reading_guide.md:34-42`; `pen_library.md:43`; `src/agent/reading/schema.py:43-46` | ✅ 已迁 | 当前有 `confidence` 字段，但是否填写只软约束。 |
| 26 | 固定 semantic-category 词表作为 reading guide -> pen library 的 handoff enum | `reading_guide.md:44-80` | `skills/intake_pipeline/0_reading/reading_guide.md:44-80` | ✅ 已迁 | 词表保留；schema 不直接存 category enum，只存最终 pen/ignored trace。 |
| 27 | 先判 drawing type；仅 plan/elevation 在主范围；axonometric/perspective out of scope；多图 sheet 先分割 | `reading_guide.md:85-101` | `skills/intake_pipeline/0_reading/reading_guide.md:85-101`; `src/agent/reading/schema.py:31-32`; `src/validator/checks/reading.py:42-48` | ✅ 已迁 | schema 扩展了 `supplementary/other`；linter 仅约束 plan/elevation pen set。 |
| 28 | line weight/style/medium/fill/standard variations 的识别语法 | `reading_guide.md:105-137` | `skills/intake_pipeline/0_reading/reading_guide.md:105-137` | ✅ 已迁 | 完整保留。 |
| 29 | wall 识别：边界线、闭合房间、重线；与 furniture/dimension/grid 区分 | `reading_guide.md:143-153` | `skills/intake_pipeline/0_reading/reading_guide.md:143-155`; `guide.md:327-331` | ✅ 已迁 | 当前额外加了 positive test，专防维度 tick 伪墙。 |
| 30 | column 识别但不作为 zone boundary trace | `reading_guide.md:154-161`; `pen_library.md:20` | `skills/intake_pipeline/0_reading/reading_guide.md:156-163`; `pen_library.md:20` | ✅ 已迁 | 完整保留。 |
| 31 | window 识别：plan 为墙断口+细平行玻璃线且无 swing arc；elevation 为矩形/网格/窗格 | `reading_guide.md:163-172` | `skills/intake_pipeline/0_reading/reading_guide.md:165-174`; `pen_library.md:21` | ✅ 已迁 | 完整保留。 |
| 32 | door 识别：opening + operation indicator；doorless opening 不当门 | `reading_guide.md:174-184` | `skills/intake_pipeline/0_reading/reading_guide.md:176-186`; `guide.md:276-280` | ✅ 已迁 | 完整保留。 |
| 33 | stair / vertical-circ 识别，treads/shaft symbol 不当墙；楼梯文字进 OCR | `reading_guide.md:186-204`; `pen_library.md:23-24,88-89` | `skills/intake_pipeline/0_reading/reading_guide.md:188-206`; `pen_library.md:23-24,88-89` | ✅ 已迁 | 完整保留。 |
| 34 | dimension-chain 识别：数字+terminator+extension 是一组；数字 verbatim，注意单位 | `reading_guide.md:255-265`; `pen_library.md:27` | `skills/intake_pipeline/0_reading/reading_guide.md:257-267`; `guide.md:186-230`; `src/validator/checks/reading.py:333-363` | ✅ 已迁 | 当前还有 numeric parse 门。 |
| 35 | level-marker 识别并作为 z dimension | `reading_guide.md:267-275`; `pen_library.md:28` | `skills/intake_pipeline/0_reading/reading_guide.md:269-276`; `pen_library.md:28` | ✅ 已迁 | 完整保留。 |
| 36 | scale ratio/graphic scale 识别但不作 stroke，写入 summary | `reading_guide.md:276-280`; `pen_library.md:30` | `skills/intake_pipeline/0_reading/reading_guide.md:278-282`; `pen_library.md:30` | ✅ 已迁 | pen 文档保留；session summary checklist 未单列 scale。 |
| 37 | grid-axis / north-arrow / view-marker 识别并 log，不当几何 | `reading_guide.md:282-302`; `pen_library.md:31-33` | `skills/intake_pipeline/0_reading/reading_guide.md:284-304`; `pen_library.md:31-33` | ✅ 已迁 | 完整保留。 |
| 38 | text-label / legend-titleblock / material-hatch：文字 verbatim，legend 用于解释 hatch，均不当几何 | `reading_guide.md:304-330`; `pen_library.md:29,34-35` | `skills/intake_pipeline/0_reading/reading_guide.md:306-332`; `pen_library.md:29,34-35` | ✅ 已迁 | 完整保留。 |
| 39 | furniture/sanitary/equipment/landscape/vehicle/shadow/decoration 识别并 log，不误作墙/窗/floor line | `reading_guide.md:334-385`; `pen_library.md:36-42` | `skills/intake_pipeline/0_reading/reading_guide.md:336-386`; `pen_library.md:36-42` | ✅ 已迁 | 完整保留，含 balcony/sun-shade/railing/canopy 与窗/楼层线区分。 |
| 40 | self-check checklist：维度全录、stroke 全捕获、无拓扑、pens_used、unknowns、scale_origin z 等 | `guide.md:179-197,276-292` | `skills/intake_pipeline/0_reading/guide.md:237-255,341-360`; `src/agent/reading/schema.py:123` | ✅ 已迁 | prompt 保留；schema 允许 `self_check=None`，code 不逐项验证。 |
| 41 | legacy 旧形状可读：裸 `dimensions[].text`、free-text `facade_axis_note` 不使老 artifacts 断载 | 旧 JSON schema：`guide.md:163-170,92-99,243-255` | `src/agent/reading/legacy.py:1-15,48-54,57-100,116-141`; `src/agent/reading/schema.py:20-21,126-130` | ✅ 已迁 | 迁移为保守适配：dimension backfill `value_m/text_verbatim`；world note 只作 low-confidence evidence。 |
| 42 | reading deterministic gate：合法 pen、唯一 id、有限/非退化几何、dimension parse、axis endpoint、chain closure、stroke-vs-dim flag | 旧 schema/自检隐含：`guide.md:85-198,276-292` | `src/validator/checks/reading.py:1-15,67-104,266-363,382-512` | ✅ 已迁 | 这是 prompt -> code 门的新增迁移；但并非所有旧 prompt 约束都有门。 |
| 43 | correction 实际消费 reading vectors；不看图，输出 world-frame cells/windows/z | `guide.md:295-303` | `src/agent/pipeline.py:280-354,482-516`; `src/agent/correction/schema.py:40-49,59-78` | ✅ 已迁 | 当前 correction prompt 明确 `Window.z` 是 absolute world z。 |
| 44 | 立面外包/overall dimensions 可作为权威 envelope 信号，被 code 吸收到 footprint | 旧：dimension/elevation 被 phase2 cross-check：`guide.md:301-302` | `src/agent/correction/envelope.py:178-254,297-407`; `src/agent/pipeline.py:731-742`; `src/agent/correction/deterministic.py:581-698` | ✅ 已迁 | 不是旧 prompt 字面对齐，而是 6/23 后代码化：维度/outline/wall_fill -> authoritative envelope -> guarded reconcile。 |
| 45 | 跨层轴线/外包一致性：同一墙不同层要对齐，避免抖动和 sliver | 旧 downstream contract：`guide.md:301-302`; B1 外包检查：`new_case_guide.md.bak_2026-05-29:179-180` | `src/agent/correction/deterministic.py:1-32,211-485,719-761,801-815`; `src/validator/checks/correction.py:78-118` | ✅ 已迁 | 已从 LLM 软约束转为 deterministic core：cross-floor reconcile、footprint anchors、sliver guard、gap close。 |
| 46 | z-stack 必须连续，楼层 absolute z 不能漂 | B1 绝对 z 背景：`new_case_guide.md.bak_2026-05-29:184,380` | `src/agent/correction/deterministic.py:764-791`; `src/agent/geometry/modelling.py:364-376`; `src/validator/checks/correction.py:31-40,70-75` | ✅ 已迁 | 小 gap 自动吸附并 audit，大 gap unsupported/raise。 |
| 47 | window 进入 world 后必须在父房间/父墙/楼层内，不能制造退化或整面窗 | B1 窗 z/父墙约束：`new_case_guide.md.bak_2026-05-29:182,184,186,380` | `src/agent/correction/schema.py:40-49`; `src/agent/correction/deterministic.py:817-874`; `src/agent/geometry/modelling.py:286-331,438-470`; `src/agent/geometry/build.py:44-57` | ✅ 已迁 | window clamp/drop + parent wall normal check + attachment completeness；比旧 prompt 更硬。 |
| 48 | Cross-floor split-pairing 必须逐 piece 成对，不能“split where needed”软写 | B1：`new_case_guide.md.bak_2026-05-29:185,379` | `src/agent/geometry/split_pairing.py:1-17,95-116,242-249`; `src/agent/geometry/build.py:40-43`; `src/agent/geometry/specs.py:186-220`; `src/validator/interzone.py:148-220` | ✅ 已迁 | 已完全下沉为 deterministic geometry kernel + InterZone gate；不再要求 LLM 写 split pieces。 |
| 49 | fenestration_specs 必须单独列窗、父墙、absolute z，且不许多/少造窗 | B1：`new_case_guide.md.bak_2026-05-29:186,380` | `src/agent/geometry/specs.py:223-249`; `src/agent/geometry/build.py:49-57`; `src/agent/pipeline.py:394-423` | ✅ 已迁 | serializer 写 exact windows 和 `z=min-max`；若 reading 有窗而 correction 0 窗，correction draw issue 会拦。 |
| 50 | 每个 facade 逐层独立读取 window chain，允许不同楼层窗数/分布/局部 blank | B1：`new_case_guide.md.bak_2026-05-29:183`; 坑位：`new_case_guide.md.bak_2026-05-29:380` | 部分相关但无等价落点：`skills/intake_pipeline/0_reading/reading_guide.md:216-228`; `pen_library.md:21`; `src/agent/pipeline.py:378-391,394-423` | ❌ 遗漏 | 当前只要求“record each window rect / window z authoritative”，pipeline 只抓“reading 有窗但 correction 全丢”的 all-or-nothing；没有 per-facade x per-floor chain/count/blank 的硬约束或 gate。 |
| 51 | 旧 `facade_axis_note` 四立面世界轴 + sign 仍出现在当前 guide，但 schema/session 已改 image-local、no world placement | `guide.md:72-78,243-255`; `prompt_template.md:94,102-106` | 冲突落点：`skills/intake_pipeline/0_reading/guide.md:88-94,301-313`; `session_kickoff.md:3-6,31-33`; `src/agent/reading/schema.py:13-18,83-95,126-127`; `src/validator/checks/reading.py:366-379`; `src/agent/reading/legacy.py:85-99` | ⚠️ 冲突/斩断 | 旧约束作为承重 reading 输出已被 P1b 斩断；但 guide 仍教模型写旧字段，且 JSON example 没有 canonical `facade` block。详见冲突机制 C1。 |
| 52 | `scale_origin` 旧世界落位/立面 base z 语义与当前“reading 不做 world placement”冲突 | `guide.md:78,95-100,289`; `prompt_template.md:58-60` | 冲突落点：`skills/intake_pipeline/0_reading/guide.md:94,111-116,357`; `session_kickoff.md:3-6,31-33`; `src/agent/reading/schema.py:13-18,115` | ⚠️ 冲突/斩断 | schema 只把 `scale_origin` 当 optional dict，不验证也无下游承重；world/base 归 correction。详见 C2。 |
| 53 | `reading_summary.md` / `phase1_summary.md` 四立面 local x -> world axis 表：旧 prompt 要求，当前 kickoff 未要求，但 correction prompt 仍依赖 §3 | `prompt_template.md:102-106`; `guide.md:243-255` | 冲突落点：`skills/intake_pipeline/0_reading/session_kickoff.md:52-53`; `src/agent/pipeline.py:325-327,349-352`; `AI_agent/architecture/pipeline_stage_contracts.md:142` | ⚠️ 冲突/斩断 | 当前 runner 可能不给 correction 它要求“verbatim 使用”的 §3 公式；若补回又违反 image-local/no world placement。详见 C3。 |
| 54 | `uncaptured_visual_elements` 的 carrier/强度 split-brain：guide 仍要求 nested + non-empty，schema/validator 改 top-level `uncaptured` + 可空 | `guide.md:188-196,223-225,267,291`; `pen_library.md:45-51`; `prompt_template.md:85-88` | 冲突落点：`skills/intake_pipeline/0_reading/guide.md:246-254,281-283,332,359`; `src/agent/reading/schema.py:120-123`; `src/validator/checks/reading.py:10-11,51-59,86-95`; `AI_agent/architecture/pipeline_stage_contracts.md:128,146` | ⚠️ 冲突/斩断 | 模型按 guide 写 `self_check.uncaptured_visual_elements` 时，linter 看的是 `view.uncaptured` 默认 `[]`，不会验证 nested 内容；旧“非空”也被 architecture 改掉。详见 C4。 |
| 55 | 旧 reading 作为世界轴 sign/base 的承重来源 | `guide.md:72-78,243-255`; `prompt_template.md:94,102-106` | 删除决策：`src/agent/reading/schema.py:13-18,83-95`; `AI_agent/architecture/pipeline_stage_contracts.md:124,142,144`; `src/agent/reading/legacy.py:91-99` | 🗑 有意删 | P1b 决策：0_reading 只产 image-local `view_facade/local_x_positive/mirrored/evidence`，world_axis/base_world 由 1_correction 生成。当前 guide 未清理造成 #51 冲突。 |
| 56 | `uncaptured_visual_elements` 对 clean drawing 也必须非空的旧硬线 | `guide.md:193-196,291`; `prompt_template.md:85-88` | 删除决策：`src/agent/reading/schema.py:120-122`; `src/validator/checks/reading.py:10-11,86-95`; `AI_agent/architecture/pipeline_stage_contracts.md:128,146` | 🗑 有意删 | 当前架构允许 clean drawing 用 `[]`；但“有跳过/door-heal 时必须 trace”仍应保留，问题是现在没有等价 gate，见 #54。 |

## 冲突 / 斩断机制详述

### C1. `facade_axis_note` 世界轴表 vs P1b image-local schema

旧脚手架要求 elevation 在 reading 阶段给出 `facade_axis_note`，明确 local x 映射到世界轴和正负方向：南 `world x`、北 `-world x`、东 `world y`、西 `-world y`。这在旧两步法里是 phase2 将 elevation window rect 转回 world 的承重输入。

当前架构已经把这个机制改掉：`src/agent/reading/schema.py:13-18` 明确 world axis/sign/base 不在 reading，`FacadeOrientation` 只保留 image-local 字段 `view_facade/local_x_positive/mirrored/orientation_evidence`（`schema.py:83-95`）；legacy adapter 只把旧 `facade_axis_note` 作为 low-confidence evidence 保存，不提升为 image-local/world claim（`legacy.py:85-99`）。validator 也检查 elevation 是否有 `facade.view_facade`，不是检查 `facade_axis_note`（`reading.py:366-379`）。

断点在当前 skill 文档：`skills/intake_pipeline/0_reading/guide.md:301-313` 仍保留旧四立面世界轴表，JSON example 仍展示 `facade_axis_note`（`guide.md:106-116`），而 `session_kickoff.md:3-6,31-33` 又要求 no world placement / 不自造世界轴惯例。结果是：模型严格照 guide 可能输出 legacy world note，却缺 canonical `facade` block；gate 会按 P1b 判不合格，或 legacy adapter 将它降级为低置信迁移痕迹。旧约束若要“恢复”为承重输出，必须反转 P1b 架构；合理修法是清理 guide 示例，改写为 canonical `facade` block，并把世界映射生成放到 correction 代码/可审 transform artifact。

### C2. `scale_origin` 的 world placement/base z 与 no-world-placement 边界冲突

旧 schema 中 `scale_origin` 记录本图 local origin 在世界系的位置，elevation `world_z_m` 还表示立面 base elevation（`old guide.md:95-100`）。当前 guide 原样保留了这段（`skills/.../guide.md:111-116`），但 schema 只给 `scale_origin: dict | None`（`schema.py:115`），没有 typed invariant、没有 validator、没有 downstream consumer；同一 schema 顶部又声明 world axis/sign/base 不在 reading（`schema.py:13-18`）。

机制问题：这是一个“prompt 还在、承重链断了”的字段。模型填错不会被 gate 抓；模型不填也不会被 schema 阻断；correction/core 实际从 reading vectors、testdata、envelope/z-stack 重建 world frame。若保留字段，应重新定义为 image-local scale/origin/bounds 并禁止 world/base；若要 world origin，则需要 correction-side transform artifact，而不是 reading artifact。

### C3. `reading_summary.md §3` 翻译公式的 dangling dependency

旧 `prompt_template.md:102-106` 要 phase1 summary 写“四立面 x_local -> world-axis table”。当前 `session_kickoff.md:52-53` 只要求 per-image confidence、repeated null/unknown、schema feedback，没有再要求 §3 或四立面公式。但 `src/agent/pipeline.py:349-352` 在 correction prompt 仍写“Use the facade translation formulas in reading_summary.md §3 verbatim”。

机制问题：当前 runner 会把 `reading_summary.md` 作为 correction reference 读入（`pipeline.py:325-327`），但 kickoff 没保证它包含 §3；若 reading 遵循 P1b 不写世界公式，correction prompt 就引用不存在的承重文本；若 reading 为满足 pipeline 写回旧世界公式，又与 no-world-placement/P1b 冲突。应二选一：删除 pipeline 对 §3 的依赖，改由 correction 根据 `facade` + reconciled footprint + z-stack 生成 transform；或把 summary §3 明确降为 human-only/non-bearing，并让 correction 不“verbatim”依赖它。

### C4. `uncaptured` carrier 与强度不一致

旧脚手架把 `uncaptured_visual_elements` 放在 `self_check` 内，并强制非空，尤其用于记录 out-of-dictionary strokes、主动排除的 clutter、door-heal traces（`old guide.md:188-196,223-225,291`）。当前 guide 仍这么写（`skills/.../guide.md:246-254,359`），但 schema 另设 top-level `uncaptured`，并注释“clean drawing -> []；linter only enforces exists + list, never non-empty”（`schema.py:120-122`）。validator 的 `_uncaptured_list` 只读取 top-level `uncaptured` 或 top-level legacy `uncaptured_visual_elements` extra（`reading.py:51-59`），不会读取 `self_check.uncaptured_visual_elements`；由于 Pydantic 默认 `uncaptured=[]`，缺字段也会被视为 list 通过（`reading.py:86-95`）。

机制问题：旧 trace 能力没有完全消失，但 code gate 与 prompt carrier 错位，导致“看得见的 trace”对机器门不起作用。架构上 clean `[]` 是有意删除旧非空硬线（`pipeline_stage_contracts.md:128`）；但 conditional logging（有 skip/heal 时必须留痕）没有等价确定性门，只能靠 VLM/judge 或人工渲图。应统一字段位置，并让 validator 至少读 canonical + nested legacy；是否强制 conditional trace 需要图像侧 judge，不宜单靠 JSON linter。

## 遗漏候选

1. per-facade / per-floor window chain：B1 明确要求逐层独立读 window chain，允许楼层间窗数、分布、blank 不同（`new_case_guide.md.bak_2026-05-29:183`）。当前 reading 文档只说 elevation 按 window grid/openings 记录每个 rect；pipeline 只做“有窗但 correction 输出 0 窗”的全局 all-or-nothing 检查。建议补：
   - reading guide/pen/session 明写“每个 facade x floor 独立 window chain，不可复制 typical floor”；
   - reading summary 或 JSON 增加 `window_chain_observations`/per-floor window count；
   - correction gate 增加 per-facade/floor expected-vs-output count/blank check，至少作为 CROSS_CHECK flag。

## 四桶计数

- 已迁：49
- 遗漏：1
- 冲突/斩断：4
- 有意删：2
