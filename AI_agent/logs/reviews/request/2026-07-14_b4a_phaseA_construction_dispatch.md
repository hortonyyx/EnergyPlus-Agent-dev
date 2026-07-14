# B4a Phase A 施工派发（terra 执行档，2026-07-14）

**任务**：按 [AI_agent/proposals/c2_b4a_detail_spec.md](../../proposals/c2_b4a_detail_spec.md) **v2 定稿**施工 **Phase A（schema、loader、config、dual-read）**。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase A**（稿 §13 Phase A 行），Phase B/C/D 后续单独派工。

## Phase A 范围（稿 §13 + 对应章节）

- 新增 `src/agent/judge/gt_schema.py`（§5 全部 v3 model + §4.2 canonical ring + §5.4 稳定 ID/排序 + §5.5 canonical bytes/hash/candidate writer + §6.1 LegacyV2 全 wire + §7 validator 结构/语义两层）；
- 新增 `src/agent/judge/gt_manifest.py`（§8.2 manifest v1 wire + §8.3 tolerance profile/`load_gt_tooling_config`）；
- 新增 `src/configs/judge_gt.yaml`（§8.3 七值完整、model 无默认）+ **A0 §8.4 七行登记**（Vg 两值只交叉引用不复制）；
- 修改 `src/agent/judge/gt.py`（§6.2 API：兼容 `load_gt()` + `load_gt_document`/`load_gt_file`；**loader 分层契约按 v2 新定案执行**——语义层一律取 `doc.generator.tolerances` 存档自验证、load 路径禁读 tooling config 禁比当前 profile、「与当轮 profile 相等」断言只属 build 侧、monkeypatch 回归锁）；
- 新增 `tests/test_gt_schema.py`（§14.1 schema/loader 单测全族）+ §6.3 v2 回归门（sm21 SHA 前后相同/`load_gt` 深等 raw/不许测试重写 sm21）。
- **不碰** extractor/render/scorer/`run_stage.py`/correction/Vg/Va（§3.1 表内 Phase B/C/D 件一律不动）。

## 硬边界

- 基座 = HEAD `6cd6836`（Va 批已收录，1070 绿 + 9 xfail，树干净）。
- 施工前先跑稿 §14.5 preflight（只查已有依赖，缺依赖停止报 blocker，不改 lockfile）。
- 零资产扰动（§2.2.8）：不改任何 `gt.json`/DXF/PNG/golden；合成输入只进 pytest 临时目录。
- 不提供 `--write`/`--promote`/overwrite 能力（§2.2.7/§5.5）。
- gt 铁律：生产路径（executor/correction/reading）零 judge import；`tests/test_gt_discipline.py` 既有门保持绿。
- 备份：主控已全量备份 `backup/src_history/2026-07-14_b4a_phaseA/`。
- 本批不创建 commit；不改管理文档。

## 测试纪律

- 定向组：新增 `test_gt_schema.py` + 既有 `test_gt_discipline.py`/`test_gt_render.py`/`test_reading_score.py`/`test_elevation_score.py`/`test_judge_harness.py` 回归，逐组记 passed 数；全量 pytest 归主控轻门。
- 稿 §14.1 测试族全数落地；确有未竟逐条列明，不得静默；稿章节→测试映射表写进简报。
- 独立合并条件（§13 Phase A）：旧测试全绿、新 API 无默认 scorer caller、工作树无资产变更。

## 交付

1. 工作树内完成代码+测试（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-14_b4a_phaseA_construction_brief.md`（改动映射/验收与测试/预期行为变化/未决·偏离/review-ask——无则注明 none）。
3. 回复只给 terse report（各组 passed/改动文件/关键结论/偏差/review-ask 摘要），不贴 diff。

审向：**Opus 执行审（升一档）→ 主控轻门（独立全量+抽查+裁决）**。
