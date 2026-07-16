# B4a Phase C 返工 r1 派发（terra 执行档，2026-07-16）

**背景**：Phase C 施工经 Opus 升一档执行审 = **APPROVE-WITH-CHANGES**（1 MAJOR + 4 MINOR + 1 NIT；覆盖回归无安全锁丢失、信任根洞安全、硬边界全过）。judgement 全文 = [verdict/2026-07-16_b4a_phaseC_review_r1.md](../verdict/2026-07-16_b4a_phaseC_review_r1.md)。**主控裁决 = 返工**：F1 必修（含缺测），F2–F5 CONFIRMED 一并修，F6 NIT 顺手清，review-ask 采纳你的处置。**只做以下清单，不扩范围**；返工续原批不重拍。

合同不变：细稿 `AI_agent/proposals/c2_b4a_detail_spec.md` v2；派工简报 `2026-07-16_b4a_phaseC_construction_dispatch.md`。基座=你的 Phase C 工作树（未 commit）。

## 必修

### F1（MAJOR）§10.8 build 末段 tolerances 自检是恒真死分支 —— 主控已亲核坐实
`gt_extraction.py:708` `generator(tolerances=inputs.tooling.tolerances)` 与 `:714` `doc.generator.tolerances != inputs.tooling.tolerances` 是**同一对象/同一值自比**，`!=` 恒 False，分支永不触发。§10.8 要求的防御性自检**形在实亡**。
- **修**：让该自检**真正具备触发能力**——`doc.generator.tolerances` 记录值须与**几何计算实际消费的 resolved profile** 逐字段比对，且比对基准取**独立引用/快照**（不是把同一个 `inputs.tooling.tolerances` 既塞进 generator 又当比对右操作数）。按 §10.8 意图设计接缝：resolved profile 单点解析→线程进 Vg/opening/elevation 计算与 generator 记录两路，自检验证"记录值 == 实际消费值"，任一字段偏离即 `gt_build_profile_tolerances_mismatch`。
- **必配缺测（§14.1 明令）**：加**单字段差异负测**——构造 generator.tolerances 与实际消费 profile 某一字段不等 → 断言 `gt_build_profile_tolerances_mismatch` 真 raise。**验收硬门**：把 `:714` 那行逻辑改坏（或注掉自检）时该负测必须变红；恒真式版本下它抓不住，即为假绿。
- 归属：`test_gt_extraction.py` 本批未测 `extract_gt_v3`，这道负测须落进对 `extract_gt_v3` 的测试（`test_gt_extraction.py` 或 `test_gt_from_dxf.py`，就近）。

### F2（MINOR）`--dxf` 源隔离守卫缺失 + 简报谎报
§10.1 要求 `--dxf` 源须脱离 `DEFAULT_GT_DIR`/`gt_sources`/`case_data`，当前**未实现且无测**；而执行简报却声称含 source-isolation 覆盖（写侧 `--out` 保护已实现已测、读侧 `--dxf` 没有）。
- **修**：实现 `--dxf` 读侧源隔离守卫（落受保护根内→稳定错误码拒绝）+ 负测。
- **纪律**：返工简报如实标注"上批 source-isolation 覆盖仅写侧、读侧本轮补齐"，不得再含未验证 claim（简报谎报是连续多批的复发纪律点）。

### F3（MINOR）CLI 丢 §10.1 明列必填参
CLI 把 §10.1 明列的 `--config`/`--vg-config` 两必填参改成硬编码（方向安全但偏离文档接口）。
- **修**：按 §10.1 恢复 `--config`/`--vg-config` 显式必填参（judge_config / vg_config 经参传入，不硬编码路径）。

### F4（MINOR）§10.7 elevation 两负测缺失
逻辑正确但无用例：①多最优 tie（多个总成本落 tie epsilon）→ fail；②多 view 同 opening z-disagreement → `elevation_opening_vertical_disagreement`。（plan-opening tie 已测、不重复。）
- **修**：补这两条负测。

### F5（MINOR）writer 篡改 content_sha256 无锁测
行为正确（活体探针：落盘=重算值非篡改值），但**无回归锁**。
- **修**：加回归锁测——传入 content_sha256 被篡改的 doc → 断言落盘字节的 content_sha256 = 重算值（writer 不信调用方 hash）。

### F6（NIT）顺手清
`_bbox_points` 死重复分支 / inspector 读 DXF 两遍 / build 双重 inspect 冗余——**低风险，能就近清则清，不值当大改就逐条记 defer**，不阻塞。

## review-ask 裁决（无需改逻辑）
canonical bytes 保留 raw source hash + 锁"提取器实体遍历序不敏感"= **采纳你的处置**（与 §5.4 明文一致：顺序不敏感仅指 DXF entity 经 extractor 后得同一 canonical wire）。活体 PROBE 4 已证 reorder 测试真打乱迭代序并断言逐字节相同、非假绿。**可选**：代码内加一行注释自解释 §5.4 依据。

## 硬边界（不变）
- 零资产扰动：不改 `gt.json`/DXF/PNG/golden；合成 DXF 只进 pytest 临时目录；无 v3 GT 写仓库可见路径；`gt_sources/` 不动。
- 不碰 Phase D（`render_gt*.py`）、correction/Vg/Va、B4b 车道（`score_*`）。
- 不 commit；不改管理文档。**只动本清单涉及的文件**，不扩面。

## 交付
1. 工作树内完成修复+测试（不 commit）。
2. 更新/追加执行简报 `2026-07-16_b4a_phaseC_construction_brief.md` 加"返工 r1"节：逐 F 项修法 + 新增测试 + F1 负测"改坏即变红"证据 + F6 逐条处置（清/defer）+ 全量 passed 数 + 本轮改动文件清单。
3. 回复 terse report（逐 F 项一行结论 + 新测 passed + 全量数 + 偏差/review-ask）。

审向：**Opus 子代理 delta 复审（聚焦 F1 自检真活+负测真红、F2 守卫、F3 接口、F4/F5 缺测）→ 主控轻门**。
