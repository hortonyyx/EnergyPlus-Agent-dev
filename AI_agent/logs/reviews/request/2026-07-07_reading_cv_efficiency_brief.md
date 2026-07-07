# Reading CV 效率批次执行简报（E 批）——纪律固化 + 配方宏工具 + 预扫前置化

- **日期**：2026-07-07 · **主控/方案**：Fable 5 · **执行**：Codex（本简报先经 Codex 对抗审）
- **缘起**：同日 sm21 判决性实验（`logs/experiments/2026-07-07_haiku_cv_retest/`）：Haiku 4.5 + CV 工具箱 = 与 Sonnet 5 基线逐项相同满分（9/9·7/7·15/15·0.0m），对照臂 0/9 全崩。**能力问题已判决；本批解决效率与固化**。
- **用户授权**（2026-07-07）：全权推进；两条硬约束——①全程守不变量 #6（建筑复杂度升级兼容性，禁烤死正交/方形假设）；②拿不准/多方案/需实测的修法，停下与用户+Codex 共议。
- **实测成本基线**：Haiku reading sm21 全程 ~400-600k tokens（含 1 轮返工）；sm24 pilot+返工 ~290k/50 次工具往返。三大头=返工整轮重来 / 交互式单工具循环+overlay 图回读 / 冷启固定成本。

## E1 纪律固化进 skill（砍"返工轮"）

把两轮 pilot 打回项从 per-run 指令固化为版本化 skill 纪律，提升首抽合格率：

1. `skills/intake_pipeline/0_reading/cv_toolbox.md` **Disciplines 扩充**（保持英文纯 spec、无版本叙事）：
   - calibrate-first：任何米制坐标写入前必须先完成该图 px↔m 标定；**标定锚 = 尺寸链 extension-line/tick 像素**（crop_zoom 高倍定位），禁用墙线端点/文本行位置当锚；残差目标 ≤1px，超限必须迭代锚点。
   - measure-before-draw：墙线/窗盒/楼层线坐标必须来自工具测量（profiler/CC/tick），禁纯目测写数。
   - single-formula 留痕：像素→米一律 `v_m=(px−origin_px)/px_per_m`，stroke note 记 px、origin、结果；不可复现的数=错误数据。
   - completeness：候选逐条 crop 核验后 accept/reject，禁"只描主要墙"；reject 必须 overlay_logger 留理由。
   - un-dimensioned elements：标定后的像素测量=测量非猜测；provenance 如实记 pixel-measured、dimension_refs 留空、引用 sidecar 序号（衔接 Phase B `anchor_px` 槽位）。
   - schema-shape 提醒：`dimensions[].anchor` 为 flat `[x0,y0,x1,y1]` 像素 bbox（sm24 实测 51 条全写成自创 dict 的教训）。
2. `session_kickoff.md` 第 23 行 "Optional CV evidence tools" → 改为指向 cv_toolbox.md 自身声明的适用纪律（措辞如 "CV evidence tools — see cv_toolbox.md for when they are required"），**required/optional 的判定权收进 cv_toolbox.md**（避免 kickoff 与工具文档两处口径）。cv_toolbox.md 声明：clean vector CAD PNG 上为 **required**（数据依据=本判决性实验）；噪声/手绘档 defer（C5 鲁棒性分档未做）。
3. **A/B 基线影响声明**：此改动改变未来 run 的脚手架基线（07-07 前的 run 是"指令要求使用"口径）——decision_log 记一条，скill 内容哈希自然变化由 provenance 采集。

## E2 配方宏工具（砍"单工具循环"）

新 CLI 动词 `prescan-plan` / `prescan-elevation`（挂 `cv_probe.py`，实现进 `cv_toolbox/recipes.py` 现骨架）：

- **prescan-plan**：一次调用完成 灰度掩膜→行/列投影全候选→（可选给定标定后）限带 CC 窗候选→tick 线检测，输出：
  - `cv_evidence/<stem>/prescan/candidates.json`：**候选一律线段形式** `{"kind":"wall_line_candidate","p1_px":[x,y],"p2_px":[x,y],"strength":…,"fwhm_px":…}`——**不得**用"轴+常数坐标"表形（那会烤死正交假设；正交行列投影产物只是线段的特例，斜墙档未来换检测器、表形不变）。**#6 检查点**。
  - 综合 overlay PNG 一张（全候选编号标注），替代逐工具逐图回读。
- **prescan-elevation**：storey 行投影 + facade 区域 CC + tick 检测，同表形。
- 工具/配方带 `capability_profile` 声明字段（`rectangular`/`orthogonal_polygon` 档=行列投影适用；斜墙档=预留检测器槽位、当前 NOT_IMPLEMENTED 显式拒绝而非静默错答）。**#6 检查点**：正交多边形（C2 当前目标）行列投影天然兼容——L 形走廊 sm24 实测已验证；真正失效边界在斜墙（远期），接口不烤死。
- 确定性要求同 C0（零 RNG、幂等）；sidecar append-only 纪律不变；单测=表形 schema + 幂等 + 与现单工具输出一致性（同图 prescan 的墙候选集合 ⊇ 单独 profiler 候选集合）。

## E3 预扫前置化接线（砍"VLM 在环的机械循环"；方向修订已获用户 2026-07-07 授权）

- **架构**：编排层（主控，spawn 子代理前）确定性跑 prescan → 子代理输入 = 原图 + prescan candidates.json + 综合 overlay + skill。VLM 职责收敛为：①候选语义判定（墙/家具/尺寸线/窗）+ 补漏扫视 ②尺寸文本 verbatim 读数 ③标定锚选择与确认 ④reading JSON 写作。
- **污染分析**：prescan 纯像素处理、零 gt 依赖、零语义预判——不构成新污染面；候选表不含"这是墙"的断言（kind=*_candidate），语义判定权完整留给 VLM+纪律，**不违反"LLM 判语义"分工铁律**。
- 子代理仍可自主追加 cv_probe 调用（crop 核验歧义处必须保留）。
- SOP 文档（new_case_guide §2.1/附录A）与 spawn 协议模板同步更新。
- **预期收益**：~20 次工具往返 → 1-2 次；overlay 逐图回读 → 单图；估 token 砍半。

## E4（OPEN QUESTION——按用户规则停下共议，本批不实现）

**标定自动化的 OCR 依赖**：E3 前置化后，唯一无法前置的关键步是"哪对 tick 对应哪个总尺寸值"（需读"15000"这类文本）。两案：
- (a) **prescan 只出像素候选，标定仍由 VLM 挑锚+读数**（现简报采用）：不引依赖、不推翻 2026-07-02 "OCR 暂不起（Phase C）" 裁决；代价=保留一轮 VLM 标定往返。同日数据：Haiku 读数本身无错（OCR 判据阳性），故 (a) 的质量风险低。
- (b) **上轻量数字 OCR**（模板匹配/tesseract）把标定也前置：判据已变——OCR 从"纠错件"（判据=VLM 读数错误率，实测低→不需要）变为"预扫使能件"（判据=前置化完整性/成本）；引依赖+鲁棒性面扩大。
- **建议 (a) 先行，(b) 挂 Phase C 待 E1-E3 收益数据出来再议**；请 Codex 审时对此表态。

## 批次序 / 验收

- E1（skill prose，小）→ E2（工具+测试，中）→ E3（接线+SOP，小）；E1 可与 E2 并行。
- 验收 = 同 harness 重跑 sm21 Haiku 冷启（判卷满分保持 + token/往返数对比记录进实验日志）。**注意跑验收前按惯例向用户拍配置**。
- 红线不变：gt 隔离（prescan 不读 gt、判卷侧不变）；`skills/` 纯当前版本 spec；测试全绿零 golden 改动。

## Codex 审点（对抗式）

1. E2 候选表形是否真正为非正交留足了槽（#6）；2. E3 污染面判断是否有漏；3. E1 纪律措辞是否与既有 guide.md/§0.1 冲突或重复（脚手架禁重复原则）；4. E4 表态；5. 各批漏配的测试。

## 定案（2026-07-07 Codex 审 APPROVE-WITH-CHANGES，6 findings 全采纳；verdict 见 `../verdict/2026-07-07_reading_cv_efficiency_review.md`）

1. **[MAJOR→E2]** 候选必须是**有界真实线段**：行/列投影峰须与该线上的灰度掩膜连续 run 求交后输出实际起止（禁全图跨度线）；测试必须含 L 形局部墙段（部分跨度）案例。
2. **[MAJOR→E3]** 候选命名机械中性化：`line_band_candidate` / `cc_box_candidate`（禁 wall_/window_ 前缀）；VLM 的 accept 判定必须显式落 reading JSON/sidecar，预扫产物永不直接当几何真相源。
3. **[MAJOR→E1]** cv_toolbox.md 只写 CV 特有纪律 + 指向 guide.md §0.1/pen_library 的指针，禁复制既有规则文本。
4. **[MINOR]** gt-discipline 扫描覆盖 prescan 入口。5. **[MINOR]** 行为测试补：综合 overlay/不支持 profile 显式拒绝/tick/杂物/幂等。6. **[MINOR]** prescan sidecar 本批 advisory-only（gate/correction/judge 不消费）。
7. **E4 = 方案 (a) 定案**（VLM 挑锚+读数；OCR 触发条件=跨模型交叉测试暴露标定/读数失败，届时先 advisory 非真相源）。
