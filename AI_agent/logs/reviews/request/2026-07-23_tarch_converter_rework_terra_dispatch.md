# 派工单：天正 DXF → GT v3 转换器 返工施工（terra）

**日期**：2026-07-23 · **主控**：Opus 4.8 · **施工方**：terra（GPT 侧）
**审**：GLM（GLM 侧，谁写谁不批成立）执行 sol 撰写的结构化核验清单 → 主控轻门
**性质**：返工（rework），不是新建。**裁决书就是规范**。

---

## 0. 唯一权威 = sol 裁决书

**规范文档（最高效力）** = [`logs/reviews/verdict/2026-07-22_tarch_converter_p0p2_sol.md`](../verdict/2026-07-22_tarch_converter_p0p2_sol.md)。
该裁决书 §6 列了 **9 条返工出口，缺一不可**。§2 Findings 给了每条的精确定位（文件:行号）+ 失败场景 + 核验方式。
**照它逐条改，不要重新论证 sol 的结论**（结论已被主控独立复核确认，尤其 B-01 = G8 假绿）。

配套材料（背景，非规范）：定稿 [`proposals/tarch_to_gtv3_converter_plan.md`](../../proposals/tarch_to_gtv3_converter_plan.md)、
opus 算法正文 [`tarch_to_gtv3_converter_plan_opus.md`](../../proposals/tarch_to_gtv3_converter_plan_opus.md)、
事实底座 [`SURVEY.md`](../../logs/experiments/2026-07-21_sm24_gt_extraction/SURVEY.md)、
上轮 P2 施工简报 [`2026-07-22_tarch_converter_p2_glm.md`](../execution/2026-07-22_tarch_converter_p2_glm.md)。

代码位置：`src/agent/judge/tarch_normalize.py` + `src/agent/judge/tarch_converter_schema.py` +
`tests/test_tarch_converter_p{0,1,2}_*.py`。晋升产物在 `case_tests/test_baseline/gt_sources/sm24_anchor/`（返工后需重生成，当前不可信）。

---

## 1. 九条出口逐条（=裁决书 §6，此处只补主控裁定与设计指引）

对照裁决书 §6 原文施工。以下每条给出**主控补充**（设计指引 / 边界判断），冲突处以本派工单为准。

### 出口 1 — 重写 G8（BLOCKER B-01，主保险，最重）
裁决 §6#1：*从可持久化的 zone edge `p1/p2 + basis + thickness` 独立重算 offset/法向并重建实体墙带；不得读取正向 `offset_native`。增加同墙两侧 basis/thickness/轴线一致性检查。B-01 两个反例必须红在 G8 或更早的专门 gate。*

**主控设计指引（重要——这是本批唯一的架构活）**：

1. **G8 独立重建**：`g8_reconstruct_wall_region` 现在（`tarch_normalize.py:1248-1282`）对每条边做
   `v -= n·offset_native`，读的是正向 `offset_native` 与存好的 `nx,ny`。改为：
   - 法向**从该边两个输出顶点 `p1→p2` 的几何重新求**（正交边，右手外法向），不读 `_ZoneEdgeRec.nx/ny`；
   - offset **从 `basis+thickness` 重新算**（`outer_skin→t` / `wall_axis→t/2`），不读 `_ZoneEdgeRec.offset_native`；
   - 为此 `_ZoneEdgeRec` 需持久化边端点 `p1,p2`（现在只能从 `zone.vertices` 平行推，明确存下更稳、也便于 source_map）。
   - 变异测试：把某条边的 `basis` 记反（内墙记成外墙）/ `thickness` 改一个值 ⇒ 断言 G8 **重新执行后变红**（不是手算残差）。**同时把 `offset_native` 保持不变** —— 证明 G8 已经不消费它（现在改 basis 不改 offset，G8 WKB 字节纹丝不动 = 假锁）。

2. **⚠️ 但独立重建仍不够 —— 必须加"同墙一致性门"（裁决 §6#1 后半句，这是抓场景 A 的真正闸门）**。
   主控已推演坐实：场景 A（错轴线 x=4060、左记 t=360、右记 t=120）里，即便 G8 完全独立重算，
   两腔体仍被**如实重建**（左 4060−180=3880✓、右 4060+60=4120✓），**G8 残差还是 0**。
   真正的错误在**输出的区划线位置错 + 同一道物理墙两侧记了互相冲突的厚度**。
   ⇒ 新增一道门（G8 的一部分或独立编号，你定），做**背靠背边配对一致性**：
   - **配对**：内墙由两个相邻腔体夹着；两条 zone 边若**共线、法向相反、沿墙跨度有重叠区间** ⇒ 它们是同一道墙的两面。
     **必须处理部分重叠**（丁字/十字接头处一条边可能沿其跨度与两个不同邻居分段配对）——按重叠子区间拆开配对，不能整边一对一。
   - **一致断言**（每对，在 `τ` 内）：`basis_left == basis_right` **且** `thickness_left == thickness_right`。
     场景 A：360≠120 → 红。这一条是场景 A 的必红点。
   - 冗余强化（可选但推荐）：`thickness == offset_left + offset_right`（= 两腔体面之间的物理墙宽），
     可同时兜"轴线偏移"类错误。
   - **必红夹具**：独立构造场景 A（错轴线 + 冲突厚度），断言这道门变红。构造场景 B（面积补偿）归出口 2 的承重门（见下）。

3. **场景 B（面积补偿）不归 G8**，归出口 2 的"近阈值承重 + 人核"。见裁决 B-02 / §6#2。

### 出口 2 — 让三承重件真正承重（BLOCKER B-02）
裁决 §6#2：近阈值面必须有明确人工裁决/ack；G10 未签字不得 pass/晋升；`ConversionReportV1(status=PASS)` 必须验证所有要求 gates 都 `passed=true`；报告内 overlay 路径改 bundle-relative + hash-bound。
**主控补充**：
- `PASS` validator（`tarch_converter_schema.py:920-931`）+ 报告 status 逻辑（`tarch_normalize.py:1831-1847`）都要改成"**全门 passed 才 PASS**"，不能只看 BLOCK 诊断数。变异：临时让任一门 `passed=false`，断言报告**不再 PASS**、bundle **不晋升**。
- G10 人核：`verification_status=="candidate"` 时 G10 **不得** `passed=true`；需要一个可追溯的真人签字动作（source-hash 绑定的 ack 记录）才置 `passed`。本批**跑一次真实人工签字**（届时会同步主控/用户），否则 G10 保持未通过、sm24 不晋升。
- 近阈值面（场景 B 的抓手）：不能只塞进 G6 evidence，必须要求人工确认（列面积+坐标，人判"这是小房间还是墙"）。
- overlay 路径：晋升报告里改 bundle-relative（现在写的是绝对 staging 路径，换工作区即失效）；N-02 顺手修（凹区标签用 `representative_point` 不用 `centroid`）。

### 出口 3 — 接 source/request hash gate（BLOCKER B-03）
裁决 §6#3：入口在读几何前核**实际 source SHA**、**request 自哈希**、plan_view/floor 归属；不符发稳定 BLOCK 码并**不写几何**。
**主控补充**：入口（`tarch_normalize.py:678-718`）在 `ezdxf.readfile` 之前先 `sha256(实际文件) == request.source_dxf_sha256` 且 `request.request_sha256 == compute_request_sha256(request)`；任一不符发 `tarch_input_source_hash_mismatch`（BLOCK）并中止。变异：把声明 SHA 改成 64 个 `0`，断言出 BLOCK、不 PASS、不写几何。

### 出口 4 — 按事件坐标实现 S7（MAJOR M-01 + M-02）
裁决 §6#4：移除 `1/50000/1` native-unit 常量和 range-derived sampling pad；对 WallRegion 事件投影**精确分段**；所有测厚必须对账**六类离散 evidence**（定稿 §2.1），超 range 只作 fail sanity；厚度 proof 写入 report/source_map。
**主控补充**：
- `_march_thickness`/`_thickness_profile`（`tarch_normalize.py:919-1024`）的采样 march（step=1、上限 50000、外环 ≤1、pad=range 上限/2）全部移除。改为对墙体域/腔体边的**顶点事件坐标**精确求交分段（定稿正文 opus §4 S7-3 的事件坐标法）。
- **厚度必须绑六类证据**（定稿 §2.1：窗块短边 / 墙端 cap / PUB_DIM 显式 / PUB_HATCH 外墙局部 / 另段精确复现 / 人审 override）。`_ZoneEdgeRec` / `ZoneEdgeReportV1` / source_map 每条边写 `ThicknessEvidenceV1`（proof_ids 非空）。无证据 ⇒ 发 `tarch_wall_thickness_unevidenced` / `tarch_provenance_incomplete`，不得静默出厚度。变异：单房环传 `wall_lines=[]`，断言发诊断而非静默四条 240 边全绿。
- 合法墙厚区间**只作 sanity 上下界**（超界 fail），**不得**作为厚度来源或 pad 参数（现在 `wall_thickness_range_m[1]/2` 进了 pad = 范围驱动输出，必须断掉）。

### 出口 5 — 补真 gate mutation tests（MAJOR M-03）
裁决 §6#5：逐门删/放宽后**恰有对应必红夹具失败**；测试**必须从触发输入重新跑 gate**，不得手算 helper 代替。G5 面积证人需独立于 `unary_union(faces)`。
**主控补充**：这是本批的**验收命脉**（上轮 neuter 7 门 35 测全绿）。每一门（G1–G10）配一个必红夹具：在独立进程/fixture 里，先跑真实 gate assembly，把**该门**的 `passed` 强制改 True（或删掉该门的拦截逻辑），断言**恰好对应的那个测试**变红、别的不变。G5 需要一个**独立外包证人**（不能拿 `unary_union(faces)` 自证面积）。

### 出口 6 — 完成强制矩阵（MAJOR M-08）
裁决 §6#6：L / 丁字 / 十字 / 自由端 / 厚度变化 **每类正负例**；至少含"同边两次变化""合法上限变化不改变已测几何""LINE 端点反转不变""native units m/mm 同变"。
**主控补充**：合成夹具矩阵，手算期望顶点，逐格真调 S7/gate。测试文件头部**声称有 thickness-change 但实际没有**（裁决 M-08 点名）——补齐并让声称与事实一致。

### 出口 7 — 恢复 fail-closed（MAJOR M-04）
裁决 §6#7：dialect 规则重叠、非法外扩 polygon、空 provenance、远端/厚度歧义 均须 **BLOCK + 最小冲突集**；不得 `buffer(0)` 猜修。把未接线码接实或从 registry 移除。
**主控补充**：
- `_classify_block` dialect 门窗规则重叠（`X_DOOR` 同时匹配 window/door）⇒ 发 `tarch_opening_kind_ambiguous`，不固定猜 window。
- S7 外扩 / G8 反缩产生自交多边形 ⇒ **不得** `buffer(0)` 静默修（现 `tarch_normalize.py:1235-1239/1276-1279`）；发 BLOCK + 最小冲突集。
- opening 多解诊断的 `solutions` 要携带候选 cap handles（最小冲突集），不能只报 `candidate_count`。

### 出口 8 — 修契约版本与复杂度接缝（MAJOR M-06 + M-07）
裁决 §6#8：对 P0 后增字段**提升/迁移 request 版本**并加**跨版本 hash 测试**；移除 `/1000` 和 `floors[0]` 单位/单层假设，或在当前 profile 明确前置 BLOCK 而不是静默只取首层。
**主控补充**：
- P1/P2 向 `request_version=1` 加了 `wall_thickness_range_m`、`min_room_area_m2`（破了 P0 契约冻结）⇒ 提 `request_version`、加迁移规则、加跨版本 hash 兼容测试。
- 写死项（裁决 M-07）：native-unit 常量（`>1.0`、`≤1.0`、`/1000`）、方向相关过滤（LINE 端点反转致 gap count 变）、`floors[0]` 单 view ⇒ 去写死或**明确前置 BLOCK**（当前 profile 不支持多层就显式拒，不静默取首层）。"无烤死常量"测试要**扫算法体数值常量**，不能只扫 schema 三个变量名。

### 出口 9 — 补失败人核件（MAJOR M-08 尾 + N-02）
裁决 §6#9：BLOCK 路径生成 `overlay_diagnostics`；凹区标签用 `representative_point`；完成一次可追溯的真实人工签字再声称 G10 通过。
**主控补充**：BLOCK 时也要产一张标出失败位置的诊断 overlay（现在只在成功且有 zones 时写 plan SVG）。

**顺手**：N-01（MINOR）——`run_p2_conversion` 对 `work_dir` 无保护检查，可指向受保护目录。加一道 `work_dir` 也必须在 staging 的 guard。

---

## 2. 验收（acceptance）

1. **场景 A 必红**（错轴线 + 冲突厚度）：新"同墙一致性门"变红。**场景 B 必红**（面积补偿）：近阈值承重门要求人核、不静默 PASS。
2. **九门变异测试**：逐门 neuter，恰对应测试红、其余绿（上轮 7 门假锁必须清零）。
3. **hash 篡改**（source SHA→全 0）：BLOCK、不 PASS、不写几何。
4. **PASS 全门**：任一门 `passed=false` ⇒ 报告不 PASS、bundle 不晋升。
5. **厚度无证据**（`wall_lines=[]`）：发诊断，不静默出厚度。
6. **sm24 端到端**：重生成 bundle；8 区 / 对称差 0 / 重叠 0 / v3 preflight PASS **仍成立**（但现在是"真门通过"而非弱公式自洽）；G10 需真人签字后才晋升。
7. **全仓测试绿 + 无回归**（现基线 `1508 passed, 9 xfailed`；返工后数字会变，报准确值）。
8. **gt 隔离不破**（`test_gt_discipline.py` 11/11；converter 不被 gate①/执行器/reading/correction import）。

## 3. 流程纪律

- **诚实披露**：做不完的、部分修的、有残留风险的，**明写在简报里**（对标 B4b Phase D terra 的正面样板；反面是"未竟说成留给审查")。
- 简报落 `logs/reviews/execution/2026-07-23_tarch_converter_rework_terra.md`：逐条出口 → 做法 / 变异测试 / 残留；acceptance 8 项逐项报结果。
- **备份**：动 `src/` 前按 §5#4 `cp` 到 `backup/src_history/2026-07-23_tarch_rework/`。
- **不要动** gate①、执行器、reading/correction、golden、gt.json、v3 提取器本体。
- commit message 仿 `<月.日>_<英文标签>`，body 含①改动②为何此刻③影响；结尾 `Co-Authored-By`。
- 你的验收清单会由 sol 写成结构化核验单（GLM 执行）。**允许你把 acceptance 当测试标准来写代码（TDD）**,但场景 A/B 的必红夹具要用**真实几何构造 + 真跑门**,不能只对着数字硬编码——GLM 会用独立几何复验。
