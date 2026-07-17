# B4a Phase D 施工派发（terra 执行档，2026-07-17）

**任务**：按 [AI_agent/proposals/c2_b4a_detail_spec.md](../../proposals/c2_b4a_detail_spec.md) **v2 定稿**施工 **Phase D（render/overlay 与 B4b seam）**。该稿是唯一施工合同（累计式自包含）；本单**只放行 Phase D**（稿 §13 Phase D 行）。Phase A（`25d3946`）、Phase B（`0d13b76`）、Phase C（`80b4d00`）均已 CLOSED 收录，是 B4a 的最后一块。

## 起点：Phase A–C 已交、Phase D 在其上接
- Phase C 已落完整 typed 层：`src/agent/judge/gt_schema.py`（`GroundTruthV3`/`GtFloorV3`/`GtZoneV3`/`GtPolygonV3`/`GtRingV3`/`GtBoundarySegmentV3`/`GtOpeningV3`/`GtWorldIntervalV3`/`LegacyGroundTruthV2` 族）、`src/agent/judge/gt.py`（`load_gt()` 遇 v3 报 `gt_v3_requires_typed_consumer`、`load_gt_file()`/`load_gt_document()` 返回 `GtDocument`）、`src/agent/judge/gt_manifest.py`（`GtExtractionManifestV1` + `RasterOverlayBindingV1`）、`gt_extraction.py`（v3 build）。**Phase D 只在这套 typed API 之上加 render model + 升级两 renderer，不碰 schema/extraction/loader/manifest 语义**。
- 现役 renderer 都是 **v2-only**：`scripts/tool_scripts/render_gt.py`（直接 `gt["footprint"]["W_m"]` schema-probing、`render_plan(gt: dict)`/`render_elev(gt: dict)`、固定四 facade）；`scripts/tool_scripts/render_gt_overlay.py`（density auto-calibration + mirror 常量、`overlay_plan`/`overlay_elev`/`_calibrate`）。二者**保留 v2 legacy 行为**、另加 v3 路径。
- `scripts/tool_scripts/render_grade.py`（36KB，Jul 4）= B4b 领地，**本批一行不改、也不让它读 v3**（§11.4）。

## Phase D 范围（稿 §11 + §13 Phase D，以稿为准）

逐条锚定细稿，本单只做指向与门槛、不复述算法：

- **统一 render model（§11.1，新增 `src/agent/judge/gt_render_model.py`）**：按稿定义 frozen dataclass `RenderPolygon`/`RenderSegment`/`RenderOpening`/`PlanRenderFloor`/`ElevationRenderSurface`/`GtRenderModel`（字段与稿逐字一致）；`gt_to_render_model(doc: GtDocument) -> GtRenderModel`（v3 adapter 直转 polygon/segment；**v2 adapter 保留当前 W/D·rect·四 facade 解释仅服务 legacy、不得称其为 v3 migration**）；`render_plan_model(model)`/`render_elevation_model(model) -> Image.Image`。**renderer 只收 `GtRenderModel`，禁止任何 `gt.get("footprint",{}).get("W_m")` 一类 schema probing。**
- **`render_gt.py` v3（§11.2）**：CLI 保持盘上真实接口（positional case-name-or-json-path + `--out-dir`；候选 path 模式必须显式 `--out-dir` 防写回 GT 根）；保留脚本内可测入口 `render_plan(gt)`/`render_elev(gt)`（先 load/validate/adapt 再调 model renderer）。v3 八条行为逐条落地：header schema/hash 短码/verification；candidate 两图不可关闭高对比水印 `CANDIDATE — NOT BASELINE`；**每 floor 单独 plan panel，world→pixel 用同一 pixels-per-metre、绝不拉成 bbox**；opening 沿其实际 segment 放置（不按 bbox family 重定位）；**elevation panel 动态按所有 source view 的 `projection_surface_key` 排序创建、不断言四张**；`z_interval=null` 段标 `PLAN-ONLY / Z UNSET`、不写 `NA` 分数；north 非空画 building +Y 与 true/project North 两箭头（`(-sin θ, cos θ)`）、null 只画坐标轴不画推测北；输出名保持 `gt_plan.png`/`gt_elev.png`，无 elevation surface 时仍产带 `NO ELEVATION SOURCE BINDING` 的 `gt_elev.png` 不伪造四面板。
- **`render_gt_overlay.py` v3（§11.3）**：新增 `build_gt_overlay_images_v3(doc: GroundTruthV3, manifest: GtExtractionManifestV1, *, raster_root) -> Mapping[str, Image.Image]`（key=manifest view_id）+ `write_gt_overlay_images_v3(images, out_dir) -> tuple[Path,...]`（`out_dir` 必须不存在、原子建/清失败残留）。v3 CLI = `--gt-file --manifest --raster-root --out-dir`（**不得与 positional case 同给**）。逐条：重算 raster SHA 不符 fail；`source_label` 只作 basename 在显式 raster root 下 resolve、symlink/`..` 不逃逸；用 `pixel_to_source_m` 逆 + plan/elevation 的 `*_from_source_m` 反投影 GT 几何到像素；逐 view 动态输出 `overlay_<sanitized-view-id>.png`、sanitize 后重名 fail；变换 singular/超图界/两绑定竞争同 view 均 fail；candidate 同带不可关闭水印+hash 短码；**legacy v2 overlay 继续走原 density wrapper 由 sm21 测试锁住，v3 代码不得 fallback 到该 heuristic**。

## B4b 交接边界（§15.1，硬约束）
Phase D 新增只读 **B4b contract fixture factory（测试代码内）**：给 B4b 一个稳定的 typed `GroundTruthV3` 构造入口，覆盖 §15.1 罗列的稳定输入（typed loader、verification/hash、per-floor footprint/zones、完整 segment list 含 hidden/depth/visible_intervals/0..N surface keys、opening floor/host/segment/along/nullable-z/source refs、optional north）。`visible_intervals` = **Vg 派生量非独立观察真值**。**B4a 一律不输出** `scoreable`/`claim_status`/`denominator`/`completeness` 字段——越界即偏差。fixture factory 只落测试代码、不进生产 import。

## 硬边界
- 基座 = 当前 HEAD（Phase C CLOSED，代码 **1148 绿 + 9 xfail，树干净**；`d54d6fb` 纯管理文档、无代码改动）。
- 施工前先跑稿 §14.5 preflight（只查已有依赖，缺依赖停止报 blocker，不改 lockfile）。
- **零资产扰动**（§2.2、§14.4）：不改任何 `gt.json`/DXF/PNG/golden；合成 L/U DXF 只进 pytest 临时目录（复用 §12 夹具，`ezdxf` 在 `tmp_path` 生成）；`gt_sources/sm21_anchor/source.dxf` 不动。
- **`render_grade.py`、score modules、run-stage、Va/completeness 一行不改**（§14.4）；v3 路径不得读 `render_grade`。
- gt 铁律：生产路径（executor/correction/reading）零 judge import；`tests/test_gt_discipline.py` 既有门保持绿并按下条扩。
- **discipline 门扩（§14.4，本批硬交付）**：v3 render 路径 AST/源码**禁用** `_FLOOR_OF`/`_ROLES`/`PLAN_BAND_Y`/`largest bbox`/`range(4)` 与固定四 panel 构造；schema/manifest 的闭 `FacadeFamily` Literal 与四方向 Vg 循环是允许的几何 vocab、不得误报；diff 中无 `case_tests/test_baseline/gt/**`/`gt_sources/**`/golden/PNG/DXF 变动；全部输出固定排序、重复运行 hash 相同。
- review-ask 已裁定（§15.3 R1–R5）照执行不重开。
- 本批不创建 commit；不改管理文档（本 dispatch 与执行简报除外）。

## 测试纪律（稿 §14.3 render 单测 + §14.4 discipline 门，全数落地）
- plan path vertices 不是 bbox；zone 面积/label 数正确；L/U concavity 在 primitive tree 可见。
- candidate 两图水印不可关闭；verified 显示 reviewer/date/hash 且无 candidate 水印。
- segment count/visible-hidden style/depth labels 与 model 一致。
- **panel count = surface key 数、≠ 常数 4**；partial coverage 之外几何被裁且有截断标记。
- inner-notch opening 落内段；plan-only z 文案存在且无 `NA score`。
- north 27.5° 箭头按 `(-sin θ, cos θ)` 数值正确，null 不画真北。
- overlay affine 连续坐标正反算误差 < 显式 endpoint epsilon；最终 PIL 像素落点误差 ≤ 1px；raster hash mismatch fail。
- **v2 sm21 当前关键尺寸、zone/opening count、四 panel legacy 行为不变**（回归锁）。
- **独立合并条件（§13 Phase D 硬门）**：B-03 关闭证据齐备（elevation panel 动态、非固定四）；discipline scan 证明 gate 隔离与固定四面假设**未进入 v3 路径**——这两条各给显式测试锁死。
- 定向组：新增/扩展 `test_gt_render.py`/`test_gt_overlay.py`/`test_gt_discipline.py`（+ 必要时 render model 单测），逐组记 passed 数；全量 pytest 归主控轻门。稿章节→测试映射表写进简报。

## 交付
1. 工作树内完成代码+测试（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-17_b4a_phaseD_construction_brief.md`（改动映射/稿章节→测试映射/验收与测试/预期行为变化/未决·偏离/review-ask——无则注明 none；**附本批改动文件清单**）。
3. 回复只给 terse report（各组 passed/改动文件/关键结论/偏差/review-ask 摘要），不贴 diff。

审向：**Opus 子代理执行审（升一档·最高对抗档·活体探针）→ 主控轻门（独立全量+抽查+裁决）**。
