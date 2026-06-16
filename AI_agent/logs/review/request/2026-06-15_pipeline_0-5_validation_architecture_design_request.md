# 审阅请求：0–5 管线逐阶段「输入·输出·校验」架构设计

- **日期**：2026-06-15
- **发起**：主开发 Agent（Opus）
- **审阅方**：Codex（跨模型）
- **类型**：**设计审阅**（不是代码审；代码尚未实现，本轮先定设计 + 出施工方案）
- **配套施工方案审阅**：见 `2026-06-15_pipeline_0-5_validation_build_plan_request.md`（施工方案落地后另发）

---

## 0. 背景（为什么做这次设计）

`sm20_anchor` 端到端首跑暴露一个系统性盲点：2f 识图把整通走廊误切成 4 段（11 区 ≠ 应有 8 区），但 **reading 自检过、人工渲图肉眼漏、1_correction 靠 testdata+尺寸链静默修对、下游三道门只验最终模型故全 0 issue —— 识图错全程无一环显式逮住**。

由此用户决定系统化「逐环节约束各阶段输出 + 校验方式」（[plan.md](../../plan.md) B2–B4）。经一轮逐阶段探讨，设计已全部落到权威活文档 **[architecture/pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md)**（2026-06-15 v1→v6 全文重写 + 逐段锁定）。本请求审的就是这份设计。

## 1. 审阅范围

**只审设计本身**（contracts §0.2/§0.3/§1/§3.2 + §4 不变量 6）。重点：

1. **校验门模型（§0.3）**：每段两道门——① 确定性自校验（L-不变量 block + L-交叉核对 flag，落 `*_checks.json`，坏 draw 盲重抽）→ ② LLM/VLM judge（结构化清单 verdict：pass/轻微/严重/致命 + 证据，**不用数字评分**；致命/严重打回、轻微 flag）。
2. **判 judge 约束（§4 不变量 6）**：judge **不给流程任何额外信息**——重做=盲重抽（同输入换采样）、judge 评语只进带外日志、绝不注入子流程 prompt；打回到 **judge 归因的根因阶段**；每阶段 **3 次**预算→终止记 hard sample。
3. **judge 密度 / 确定性阶段定位**：LLM 阶段(0/1/4)重判；**确定性阶段(2/3/5)靶子是代码（单测+不变量）、无 per-run LLM judge**，只留确定性门 + 渲染（2/3 的交互 3D 查看器 = **上线保留的用户几何确认门**）。
4. **reading/correction 分工再定（§1）**：**0_reading = per-image 忠实**（结构 linter / 单图尺寸链闭合 / stroke↔dimension 互核 / 越界 + 七类 VLM judge），**不建拓扑、不要参考答案**；**polygonize/区数/跨图/填色区图全归 1_correction**。**1_correction = 拓扑+跨图 reconcile+对参考**（A0§7 几何校验 + 立面 local→world 代码翻译 + 跨图对账 + 窗位落墙 + 区数 tripwire + 看原图 VLM judge 裁 redraw 保真），全管线最依赖人工校验。
5. **逐段校验分配 + 跨阶段自洽归属（§1 5_intakeoutput 末表）**：3=几何内部 / 4=MEP 内部 / 5=跨域接缝，不重复不遗漏。
6. **judge=开发期数据工厂→上线轻量**：judge verdict = 训小模型监督标签 + 错类固化清单；小模型吃透后撤 judge，上线只留确定性校验 + 小模型（用户终极目标=迁开源自训小模型）。

## 2. 关注点（希望重点判断）

- **F1 边界正确性**：reading/correction 这刀切得对吗？把 polygonize（拓扑重建）禁在 reading、归 correction，是否彻底？还有没有别的 check 放错段（如"立面轴翻"拆成 reading 声明自洽 + correction 落位检测，对吗）？
- **F2 判 judge 模型自洽性**：「judge 不给信息 + 盲重抽」会不会导致系统性错（非采样波动类）3 次必败→大量误终止？3 次预算 + hard-sample 是否足够兜底？「确定性阶段同输入必同出→判坏必弹上游」这条推理对吗？
- **F3 分层与处置**：每条 check 归 L-不变量(block) vs L-交叉核对(flag) 是否得当？有无**过度 block**（该 flag 放行的却拦）或**过度 flag**（该 block 的放过）？尤其 0_reading 只 block「结构 linter」、其余全 flag——够不够稳？
- **F4 确定性阶段无 judge 是否成立**：2/3/5 真的不需要 per-run LLM judge 吗？有没有"输入合法但确定性代码产错"且单测+不变量+渲染都兜不住的情形？
- **F5 上线用户确认门**：把交互 3D 几何确认作为**保留到产品**的人工门，与"撤 judge、轻量上线"目标是否冲突/协调？
- **F6 完整性（最关键）**：**拿 2f 这个触发案例验证新设计**——确定性 + judge 双线是否都能逮住？还有没有**类 2f 的盲区**（某错类无任何 check/judge 覆盖）？特别留意：跨图轴翻、整条尺寸一致抄错、裸 zone、覆盖洞、no-mass material draw。
- **F7 facade 翻译归代码**：把立面 local→world 从「LLM 套 summary §3 散文公式」改成「代码读结构化 `facade_axis` 字段确定性翻译」+ 0_reading 新增结构化字段——这条是否引入新风险（如 facade_axis 字段本身被识图写错，谁逮）？
- **F8 dev 成本**：顶尖 VLM judge 在 dev 期门每阶段每轮——「确定性在前、judge 只评残差」的分层是否足以把成本/调用量压到可接受？

## 3. 相关文件

- **权威设计**：[architecture/pipeline_stage_contracts.md](../../architecture/pipeline_stage_contracts.md)（§0.2 三层框架 / §0.3 门模型 / §1 逐段 / §3.2 backlog / §4 不变量 / §5 接缝缺口）
- 触发案例上下文：[[pipeline-0-5-refactor-status]] + [[per-stage-validation-judge-architecture]]（记忆）
- 现有校验代码（被引用、设计据此扩展）：`src/agent/pipeline.py:360` `_make_correction_validator`（draw 重抽）/ `src/agent/geometry/modelling.py:280+`（内核硬守卫）/ `src/validator/interzone.py:224` / `src/validator/schedules.py` / `src/agent/intakeoutput.py:67` `validate_contract` / `src/runner/runner.py:31` `read_ep_end`
- 既有缺口：contracts §5.1–5.5（A0 registry / MEP 先验 / provenance / audit sidecar / 连接性补缝）

## 4. 验收标准（请按 §6#14 格式回 review 到 `review/`）

- **verdict**：APPROVE / APPROVE-WITH-NITS / CHANGES REQUESTED
- **分级 findings**（High/Medium/Low）+ 证据 + 建议修复，逐条对应上面 F1–F8 或新发现
- 特别请明确回答：**F6（2f 验证 + 残余盲区）** 和 **F2（盲重抽模型是否自洽）** 这两条
- 命名：`review/2026-06-15_pipeline_0-5_validation_architecture_design_review.md`

> 注：本轮**不审实现细节**（无代码）。施工方案是另一份请求。设计若 CHANGES REQUESTED，主开发 Agent 逐条处置后再定施工。
