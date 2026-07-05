# 审阅请求：0–5 校验架构「施工方案」

- **日期**：2026-06-15
- **发起**：主开发 Agent（Opus）
- **审阅方**：Codex（跨模型）
- **类型**：**施工方案审阅**（仍无代码；审"怎么建、什么序、模块切分、可行性、测试策略"）
- **前置**：设计审阅 `2026-06-15_pipeline_0-5_validation_architecture_design_request.md`（审设计本身）。本请求审的是把那份设计落地的施工方案。

---

## 0. 背景

设计已锁定在 [architecture/pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md)（0–5 逐段输入·输出·校验 + §0.3 门模型）。据此出了施工方案 **[architecture/pipeline_validation_build_plan.md](../../architecture/pipeline_validation_build_plan.md)**：模块布局 + 依赖序 + 4 里程碑（M1 地基 / M2 全段确定性校验+视觉件 / M3 judge 门基建+三 judge / M4 集成+上线门+baseline）+ 逐项施工卡 + 风险点。本请求审这份方案。

## 1. 审阅范围

[pipeline_validation_build_plan.md](../../architecture/pipeline_validation_build_plan.md) 全文，重点 §0 模块布局 / §1 依赖序 / §2 逐项施工卡 / §4 风险点。

## 2. 关注点（希望重点判断）

- **B1 模块切分**：`src/validator/checks/`（逐段确定性校验 + F1 公共 schema）+ `src/agent/judge/`（F2 门基建）+ `src/agent/correction/{facade,geometry_validator}.py` + `scripts/tool_scripts/` 渲染——切分合理吗？有没有更顺手的归位？`interzone.py`/`schedules.py` 保留原位被复用 vs 并入 checks/，哪个好？
- **B2 依赖序 / 里程碑**：M1→M2→M3→M4 对吗？**M2（全段确定性）独立先落、不依赖 judge**——这个"确定性优先、judge 后置"的切法是否最优？M2 内各段能否真并行？有没有隐藏的跨项依赖（如 S1 依赖 P1 facade 字段——还有别的吗）？
- **B3 逐项可行性 / 算法缺口**（对应 §4 风险）：
  - **stroke↔dimension 互核**的配准与容差（§4.1）——这条是逮"整条尺寸抄错"的关键，算法可行吗？会不会误报频繁？
  - **A0§7 coverage**（shapely union 对比 footprint，§4.2）矩形够不够、非矩形该不该本轮就留接口？
  - **facade 字段旧 case 兼容**回退（§4.3）。
  - **judge harness 复用 `_make_correction_validator`**（§4.4）——一套重试环能否同时服务"确定性 block 重抽"与"judge 打回重抽"，不漂移？
  - **pyvista 容器内**（§4.5）`export_html` 无显示器 OK、`screenshot()` 需 offscreen——可行性 + 备选（matplotlib/trimesh+three.js）该不该预留。
- **B4 测试策略**：每条确定性 check 配单测 + 2f 式 fixture——覆盖够吗？judge 层（含 mock）怎么测才不脆？有没有该加的回归 anchor（sm20_anchor 当确定性校验的正例 golden）？
- **B5 接线风险**：把 gate①/gate② 串进 `pipeline.py` 每段、加重试/路由/终止环——对现有 e2e 流程（`run_full_pipeline --reading-from`）的侵入面、向后兼容（旧 case / `--intake-from`）、`IntakeOutput` 契约零影响——有没有被忽略的破坏点？
- **B6 范围纪律**：哪些标"占位 stub"（4_mep 合理性区间/J4）、哪些"deferred"（覆盖完整性 shapely 随 B5 / provenance §5.3 / gt.json 富化 B2）——本轮 in-scope 划得对吗？有没有该提前或该砍的？
- **B7 工作量 / 切片**：M2 是大头，能否进一步切成可独立 merge 的小 PR（按段）？里程碑粒度是否便于 review + 回归？

## 3. 相关文件

- **施工方案**：[architecture/pipeline_validation_build_plan.md](../../architecture/pipeline_validation_build_plan.md)
- **设计（WHAT）**：[architecture/pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md)
- 复用/扩展的现有代码：`src/agent/pipeline.py:360`（draw 重抽，judge harness 拟复用）/ `src/agent/geometry/modelling.py:280+`（内核守卫）/ `src/validator/{interzone,schedules,data_model}.py` / `src/agent/intakeoutput.py:67` / `src/runner/runner.py:31` / `scripts/tool_scripts/render_corrected_geometry.py`
- 正例 golden 候选：`case_tests/e2e_tests/sm20_anchor`（19 区/135 面/EP 干净，2f 已修）

## 4. 验收标准（请按 §6#14 回 review 到 `review/`）

- **verdict**：APPROVE / APPROVE-WITH-NITS / CHANGES REQUESTED
- 分级 findings（High/Med/Low）+ 证据 + 建议，逐条对应 B1–B7 或新发现
- 特别请明确：**B3（算法缺口可行性）** 与 **B5（接线破坏点）** 这两条
- 若建议调整模块切分/依赖序/里程碑，请给出替代方案
- 命名：`review/2026-06-15_pipeline_0-5_validation_build_plan_review.md`

> 主开发 Agent 收到两份 review（设计 + 施工）后逐条处置，CHANGES REQUESTED 项改完再开工（用户定"全部确定完再一起施工落地"）。
