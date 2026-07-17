# B4a Phase D 返工 r1 派发（terra 执行档，2026-07-17）

**背景**：Phase D 施工经 Opus 子代理升一档审 = **ACCEPT-WITH-REWORK**（裁决 [2026-07-17_b4a_phaseD_review_r1.md](../verdict/2026-07-17_b4a_phaseD_review_r1.md)）。**代码行为面无真洞**（6 活体探针全过、禁区全 CLEAN、B-03 硬门满足），扣在**测试覆盖 vs §14.3 契约缺口**。主控已亲核唯一 MAJOR = CONFIRMED。本轮**纯补测试锁 + 扩 discipline 扫描，不改任何 render 行为**（行为已验证正确，改了即偏差）。

## 起点
- 工作树 = terra Phase D 施工态（未 commit），定向组 26 passed、schema/dxf/judge 回归 125 passed，全量绿（主控轻门确认）。
- **本轮不碰生产 render 逻辑**：`gt_render_model.py`/`render_gt.py`/`render_gt_overlay.py` 的行为一行不动；只在测试文件加断言/负测，+ `test_gt_discipline.py` 扩扫描范围。若发现必须改生产码才能过 → 停止报 blocker（说明行为审已判正确，不该需要）。

## 返工项（逐条闭合）

### M-1（MAJOR，必闭）：§14.3 render 断言缺口 + 误导性测试名
`tests/test_gt_render.py` 现有 `test_v3_dynamic_elevation_panels_and_plan_only_z_legend`（:101）名号称锁 plan-only-z legend，实际只断 `len==2`/`width==878`。补齐 §14.3 明列、当前**全测试目录零锁**的四条行为断言（文案在 `gt_render_model.py` 真实存在：:268/:304/:305，去掉即须变红）：
1. **plan-only z legend 存在 + 无 NA 分数**：z_interval=None 的 opening 所在 elevation 面板渲染须含 `PLAN-ONLY / Z UNSET` 文案、且**不含** `NA`。用可靠手段验文案（如渲染时把 legend 文案收进 `image.info` 的结构化记录再断言，或对该 primitive 记账；**不要**用脆弱像素坐标当唯一证据）。
2. **partial 截断标记存在**：partial view（`world_along_coverage` 非空）面板须含 `PARTIAL — CLIPPED AT COVERAGE` 标记。
3. **null 不画真北**：补一条 north_axis_deg=None 的用例，断言 north 向量为 None（对照 `test_v3_verified_header_and_north_vector` 的 27.5 非空锁）。
4. **空 elevation binding 面板文案**：无 elevation surface 时 `gt_elev` 须含 `NO ELEVATION SOURCE BINDING`、不伪造四面板。
5. **改名**：把误导测试名对齐真实断言（拆成语义清晰的多个测试，或改名 + 补断言使名实相符）。
- **验收自证**：补断言后，临时把 `gt_render_model.py` 对应文案行注掉/改坏，确认新断言变红（活体自证），随后**还原生产码**——简报里记录你做的自证及结果。

### m-1（MINOR，闭）：overlay v3 安全/健壮守卫负测
`render_gt_overlay.py` 的安全守卫（审已 live 确认全部正确触发但无回归锁）补负测到 `tests/test_gt_overlay.py`，每类断稳定错误码：
- `_safe_raster`：`..` 逃逸 / 绝对路径 / 子目录 / symlink 逃逸 → 各断 `raster_label_invalid`（symlink → `raster_escape`，按实际码）；
- `_within`：投影点超图界 → `projection_out_of_bounds`；
- 竞争绑定：同 view_id 两 overlay → `gt_overlay_competing_bindings`；
- `_sanitized_view_id`：sanitize 到空（如 `'...'`/`'///'`）→ `view_id_unsanitisable`；
- `_inverse_affine`：singular（det=0）→ `singular_affine`。
- 用审裁决 §「活体探针 P5」给的输入/期望码为锚（以实际实现码为准，不猜）。

### m-2（MINOR，闭）：弱化像素常量代理
`test_gt_render.py` 里用像素常量当行为代理的断言（如 `image.width==878`、`plan.size==(1724,634)`）——保留真语义锁（panel-count/vertex-count/watermark/affine round-trip），把纯像素常量降级为「非退化」式弱断言（如 `>0`/存在），避免字体/PIL 版本漂移碎测。**v2 legacy 像素锁除外**（那是 v2 行为不变的回归锁，保留精确像素）。

### n-2（NIT，闭）：discipline 扫描补 v3 路径全覆盖
`test_gt_discipline.py` 的违禁词扫描（`_FLOOR_OF`/`_ROLES`/`PLAN_BAND_Y`/`largest bbox`/`range(4)`/固定四 panel）当前只覆盖 `render_elevation_model`/`render_plan_model` + overlay v3 切片；把 `gt_to_render_model` 与 `render_gt.py` 的 v3 分支也纳入扫描范围（审已亲验这两处无违禁词，本条是防未来回归的覆盖补全）。闭 `FacadeFamily` Literal 与四方向 Vg 循环是合法 vocab、不得误报。

### n-1（NIT）：不动
`GtRenderModel` 超稿加的 4 个 verification 字段是 §11.2.1 header 所需、load-bearing，审判定非偏差——**保留不改**。

## 硬边界
- 不 commit；不改管理文档（本 dispatch 与执行简报除外）。
- **零生产 render 行为改动**（见起点）；零资产扰动；`render_grade.py`/score/run-stage/Va/completeness/intakeoutput 一行不改；gt 铁律生产零 judge import 保持。
- 合成夹具只进 pytest tmp。

## 交付
1. 工作树内测试补齐（不 commit）。
2. 执行简报 `AI_agent/logs/reviews/execution/2026-07-17_b4a_phaseD_construction_brief.md` **追加「返工 r1」节**（逐项 M-1/m-1/m-2/n-2 修法 + 新增测试名 + 自证记录 + 定向 passed 数 + 本轮改动文件）。
3. terse report：各项闭合状态 / 新增测试数 / 定向 passed / 自证结果 / 偏差。

审向：**主控轻门**（返工纯测试侧，主控独立全量 + 抽查关键新断言的活体自证 + 裁决；不再起子代理审，除非发现新实质风险）。
