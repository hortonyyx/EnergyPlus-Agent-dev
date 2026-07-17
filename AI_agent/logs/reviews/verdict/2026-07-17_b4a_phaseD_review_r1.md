# B4a Phase D 执行审裁决 r1（Opus 子代理·升一档·活体探针）

- **审对象**：terra 施工 C2/B4a Phase D（render/overlay + B4b seam），工作树未 commit。
- **基座**：HEAD `d54d6fb`（Phase A–C CLOSED，1148 绿 + 9 xfail）。
- **合同**：dispatch `2026-07-17_b4a_phaseD_construction_dispatch.md`；细稿 `c2_b4a_detail_spec.md` v2 §11/§13 Phase D/§14.3/§14.4/§15.1；brief `2026-07-17_b4a_phaseD_construction_brief.md`。
- **改动文件（本批）**：新增 `src/agent/judge/gt_render_model.py` + `tests/b4b_contract_fixture.py`；改 `scripts/tool_scripts/render_gt.py`、`scripts/tool_scripts/render_gt_overlay.py`、`tests/test_gt_render.py`、`tests/test_gt_overlay.py`、`tests/test_gt_discipline.py`。

## 总裁决：ACCEPT-WITH-REWORK

代码行为面**无真洞**：统一 render model、v3 双 renderer、overlay v3 affine/安全守卫、v2 legacy 隔离、B4b fixture、discipline 门、禁区隔离——逐条独立复核 + 活体探针 + 直接构造输入 live 验证，全部实现正确。**硬合并门（§13 Phase D）满足**：B-03 动态 elevation 面板测试真锁（探针证实 4==2 变红）、discipline scan 证明固定四面/gate 词汇未进 v3 路径。

保留一项 **MAJOR = 测试覆盖 vs §14.3 契约缺口**（§14.3「测试纪律…全数落地」未达）：多条 §14.3 明列的 render 断言缺失，且一个测试名号称锁「plan-only z legend」但断言里根本没查该行为——false-green 风险。行为本身 live 验证正确，故为返工（补断言）而非重架构。

## 定向组 passed 数

| 组 | 结果 |
|---|---|
| `test_gt_render.py test_gt_overlay.py test_gt_discipline.py` | **26 passed**（9 既有 Pydantic serializer warning） |
| `test_gt_schema.py test_gt_from_dxf.py test_inspect_dxf.py test_reading_score.py test_elevation_score.py test_judge_batch_b.py test_judge_harness.py` | **125 passed** |
| 全量 pytest | 未跑（归主控轻门，与 dispatch 一致） |

活体探针后工作树**完全还原**：`gt_render_model.py`/`render_gt_overlay.py`/`test_gt_render.py` blob hash 全部复原为 terra 原值；还原后定向组重跑仍 26 passed。

## 逐条裁决

### MAJOR

**M-1 §14.3 render 断言缺口 + 误导性测试名（false-green）** — verdict: **CONFIRMED**（行为 live 正确 / 断言缺失亲验）
- `tests/test_gt_render.py:101-116` `test_v3_dynamic_elevation_panels_and_plan_only_z_legend`：函数名号称锁 plan-only-z legend，实际把 `openings[0].z_interval=None` 后**只断言** `len(render_primitives)==2` 与 `image.width==878`。§14.3 明列「plan-only z 文案存在且无 `NA score`」——grep 全测试目录**无任何** `PLAN-ONLY`/`Z UNSET`/`NA` 断言。
- 同缺口：§14.3「partial coverage 之外几何被裁且有**截断标记**」——该测试用了 partial view（coverage 0..2）却未断言 `PARTIAL — CLIPPED AT COVERAGE`；§14.3「null 不画真北」——`test_v3_verified_header_and_north_vector`（:140）只断非空 27.5 向量，无 null-north `north_vectors[0] is None` 断言。
- 失败场景（未被套住的回归）：若 `render_elevation_model` 去掉 `PLAN-ONLY / Z UNSET` legend（gt_render_model.py:305）、或误写 `NA` 分数、或丢截断标记（:304）、或 null 时误画推测北箭头——**定向组仍全绿**。
- 亲验行为正确：live 构造 z=None opening → 渲染 RGB 无 NA；null-north → `north_vectors[0]=None`；空 elevation → 760×170 `NO ELEVATION SOURCE BINDING`；27.5 → `(-0.461749, 0.887011)` 符 `(-sinθ,cosθ)`。**即行为无 bug，纯缺锁**。
- 返工建议：给该四行为各补一条显式断言（legend 文案存在 + 无 `NA`、截断标记存在、null-north 向量为 None、空-elevation 面板文案），并把误导名对齐到真实断言。

### MINOR

**m-1 overlay v3 安全/健壮守卫零负测** — verdict: **CONFIRMED**（守卫 live 全部正确 / 负测缺失亲验）
- `render_gt_overlay.py`：`_safe_raster`（`..`/绝对路径/子目录/symlink 逃逸）、`_within`（投影超图界）、竞争绑定（同 view_id 两 overlay `gt_overlay_competing_bindings`）、`_sanitized_view_id`（sanitize 到空）、`_inverse_affine`（singular）——`tests/test_gt_overlay.py` 仅锁了 hash-mismatch + sanitized-collision + doc/manifest-binding + output-exists；上述 5 类**无负测**。
- 亲验守卫正确（live 探针）：`../outside.png`→`raster_label_invalid`、`/etc/passwd`→`raster_label_invalid`、`root/real.png`→`raster_label_invalid`、symlink→`raster_escape`、越界点→`projection_out_of_bounds`、`'...'`/`'///'`→`view_id_unsanitisable`、det=0→`singular_affine`；合法 basename 正常通过。singular 另有 `Affine2D` schema 层兜底。
- 说明：§14.3 的测试矩阵仅**显式要求** hash-mismatch 负测（已有）；这些属 §11.3 行为但非 §14.3 明列，故降 MINOR。但均为安全相关（路径穿越/越界），建议补负测。

**m-2 partial-view 面板宽度用常量代理** — verdict: **CONFIRMED**
- `test_v3_dynamic_elevation_panels...:116` `image.width==878`、`test_renders_both_views:40` `plan.size==(1724,634)`、`test_v3_dynamic...` 类断言用像素常量。这些常量断言脆弱（字体/PIL 版本漂移即碎）且是弱行为代理。所幸同测试内 panel-count(==2)/vertex-count(==6)/watermark-pixel/affine-round-trip 是真行为锁（探针证实）——故非纯假绿，仅代理偏弱。建议弱化像素常量、保留语义断言。

### NIT

**n-1 `GtRenderModel` 超出稿字段** — `gt_render_model.py:82-85` 在稿 §11.1 的 5 字段外加了 `verification_status`/`reviewer_id`/`reviewed_on`/`content_sha256`。**非偏差**：§11.2.1 要求 header 显 verification/hash + candidate 水印，稿的 dataclass sketch 欠列这些，terra 补齐是 load-bearing。其余 primitive dataclass 字段与稿逐字一致。

**n-2 discipline 违禁词扫描范围** — `test_gt_discipline.py:94-110` 只扫 `render_elevation_model`/`render_plan_model` + overlay v3 切片，未含 `gt_to_render_model` 与 `render_gt.py` v3 分支。这两处经亲验无违禁词（typed 属性访问，非 dict-probing），故当前无害；但严格「v3 路径全覆盖」应把这两段纳入扫描。

## 恒真式 / 自指 / 假绿专列

- **无恒真式**：4 个活体探针（面板数、affine round-trip、raster-hash、legacy-pixel）逐一篡改后测试确实变红——断言均触达真行为、非常量恒真。
- **无危险自指**：`b4b_contract_fixture.py` 用生产 `vg_for_direction`/`footprint_fingerprint` 产 `visible_intervals`（§15.1 明定 Vg 派生量，合规），并经生产 `validate_gt_v3` 重算校验；render 测试断言的是 render 输出 vs 独立构造的 model，非「被测函数自产期望自比」。
- **一处 false-green（已列 M-1）**：`test_v3_..._plan_only_z_legend` 名实不符——名字承诺 legend，断言未查。

## 禁区越界核查（全部 CLEAN）

- `git status`：仅 5 改（两 renderer + 三测试）+ 4 新增（render model / b4b fixture / brief / dispatch）。`render_grade.py`/score/run-stage/`validation_run`/Va-applicability/completeness/intakeoutput/`checks/` **一行未改**（`git diff --name-only` 亲验）。
- **零资产扰动**：diff 无 `gt.json`/`.dxf`/`.png`/golden/`gt_sources/`/`test_baseline/gt/**`（亲验）。
- **生产零 judge import**：`pipeline.py`/`execution`/`correction`/`reading` 无 `gt_render_model`/`b4b_contract_fixture` import；`b4b_contract_fixture` 仅 `tests/` import（亲验）。
- **v3 路径无 schema-probing**：`gt_to_render_model` v3 分支全走 typed `doc.*` 属性（唯一 `.get` 是内部局部 dict `openings_by_floor`）；`W_m`/`D_m` 仅出现在 `_legacy_render_model`（v2 适配器，typed `doc.footprint.W_m`，合规）。overlay/render_gt v3 分支无 `_calibrate`/`_FLOOR_OF`/`_ROLES`/`PLAN_BAND_Y`/`range(4)`/固定四面板。
- **v2 未伪装成 v3**：`_legacy_render_model` 明标 isolated-for-v2、`source_schema_version=2`、仅非-v3 时路由；v2 raw dict 走 legacy 像素 renderer（(1724,634)/(1828,980) 像素锁探针证实）。
- **CLI 互斥正确**：overlay v3 `--gt-file/--manifest/--raster-root/--out-dir` 与 positional case 互斥；`load_gt_file(allow_legacy=False)` 拒 v2；render_gt 显式 path 强制 `--out-dir`。

## 活体探针清单（探后全还原）

| # | 探针（篡改点→期望） | 结果 |
|---|---|---|
| P1 | `render_elevation_model` surfaces `*2`（模拟固定/翻倍面板）→ 动态面板测试应红 | ✅ `AssertionError: 4 == 2`，还原 blob 复原 |
| P2 | `_pixel_for_world_plan` 出参 `+3px` → affine round-trip 测试应红 | ✅ world 算回 `(3.05,1.25)≠(2.75,1.25)`、pixel 偏移被抓，还原 |
| P3 | build v3 SHA 校验短路 `if False and …` → raster-hash-mismatch 测试应红 | ✅ DID NOT RAISE → 红，还原 |
| P4 | legacy 像素锁期望 `(1724,634)→(1724,999)` → v2 size 测试应红（兼验 v2 走 legacy 路径） | ✅ `(1724,634)==(1724,999)` 红，还原 |
| P5 | 直呼 `_safe_raster`/`_within`/`_sanitized_view_id`/`_inverse_affine` 恶意输入 | ✅ `..`/绝对/子目录/symlink/越界/空 sanitize/singular 全 raise，合法 basename 通过 |
| P6 | 直构 model 验 null-north/空-elevation/plan-only-z/27.5-north 行为 | ✅ 全部行为正确（见 M-1 亲验） |

工作树最终态：`git status` 与 terra 提交前一致（三个 probed 文件 blob hash 全复原），零残留。

---

## 返工 r1 收回 + 主控轻门收口（2026-07-17，主控 Opus）

**返工派工**：[2026-07-17_b4a_phaseD_rework_r1_dispatch.md](../request/2026-07-17_b4a_phaseD_rework_r1_dispatch.md)（纯补测试锁 + 扩 discipline 扫描、零生产 render 行为改动）。terra 续原线程闭合，8 新 pytest items，偏差 none。

**逐项闭合核实**：
- **M-1（MAJOR）✅ 闭**：`test_gt_render.py:116` `test_v3_dynamic_elevation_panels_partial_and_plan_only_legends` + `test_v3_null_north_omits_true_north_vector`(:134) + `test_v3_no_elevation_binding_has_explicit_panel_text`(:140) 补齐四行为锁，用 `_captured_render_text` monkeypatch 结构化捕获文案断言（非脆弱像素）：`PLAN-ONLY / Z UNSET` 存在 + 无 `NA`（:130）/ `PARTIAL — CLIPPED AT COVERAGE`（:131）/ `north_vectors==[None]`（:137）/ `NO ELEVATION SOURCE BINDING`（:143）；误导测试名已对齐真实断言。
- **m-1（MINOR）✅ 闭**：overlay v3 安全守卫负测补齐（路径/symlink 逃逸、越界、竞争绑定、空 sanitize、singular affine）。
- **m-2（MINOR）✅ 闭**：v3 纯像素常量弱化为非退化断言；v2 sm21 精确像素锁保留。
- **n-2（NIT）✅ 闭**：discipline 扫描覆盖 `gt_to_render_model` + `render_gt.py` v3 分支。
- **n-1（NIT）**：`GtRenderModel` verification 字段保留不改（§11.2.1 所需，判定非偏差）。

**主控轻门**：
- **审 diff**：返工确实**只动测试侧**——`render_gt.py`(+47)/`render_gt_overlay.py`(+183) 与施工态一致无额外生产改动、`gt_render_model.py`(307 行) 施工态不变；rework 增量全在 `test_gt_render`(+27)/`test_gt_overlay`(+32)/`test_gt_discipline`(+8)。
- **M-1 锁活体自证（主控亲手抽查）**：临时把 `gt_render_model.py:305` legend 文案改为 `PROBE_BROKEN_LEGEND` → `test_v3_dynamic_elevation_panels_partial_and_plan_only_legends` 在 :130 变红（捕获文案证实）；随后**还原生产码**、工作树零残留。**审报的 false-green 已真封**。
- **独立全量 pytest**：**1168 passed + 9 xfailed**（Phase C 基线 1148 + 施工 +12 + 返工 +8）。
- **禁区复核 CLEAN**：`render_grade.py`/score/run-stage/Va/completeness/intakeoutput 一行未改；零资产扰动；生产零 judge import。

**裁决：B4a Phase D CLOSED**。B4a 全系列（Phase A–D）收官；连同 REC-B PASS，B4b Phase B 依赖侧全部就绪。**升一档审首轮抓 MAJOR（M-1 shipped-untested 假绿）= 审阶梯价值又一现**；返工率 = 1 轮全闭无二次返工；本批施工+审+返工+收口全走完于单主控窗。
