---
name: per-stage-validation-judge-architecture
description: 0–5 逐阶段校验架构(用户 2026-06-15 定):每段两道门=确定性自校验①+LLM/VLM judge②;judge 结构化清单 verdict(非数字分)、盲重抽、不给流程任何额外信息、3 次→终止记 hard sample;judge=开发期数据工厂→上线撤掉只留确定性+小模型;reading=per-image 忠实/correction=拓扑+区划+跨图+对参考(最依赖人工)。活文档 contracts §0.3/§1
metadata: 
  node_type: memory
  type: project
  originSessionId: 08920ea7-d705-473f-9054-5f2b23ef37bf
---

「逐环节约束各阶段输出 + 校验方式」(plan B2–B4) 的架构,用户 2026-06-15 逐条确认。权威活文档 = [pipeline_stage_contracts.md](AI_agent/architecture/pipeline_stage_contracts.md) §0.2(三层框架)/§0.3(校验门模型)/§1(逐段校验)/§3.2(backlog)。关联 [[pipeline-0-5-refactor-status]]。

**两道门(每阶段,确定性在前 judge 在后)**：① 确定性自校验(L-不变量 block + L-交叉核对 flag,落 `*_checks.json`,坏 draw 盲重抽不烧 judge)→ ② LLM/VLM judge 按该段 rubric 逐条裁。
- **judge verdict = 结构化清单**(每条 pass/轻微/严重/致命 + 证据),**不用数字评分**(不可复现/不可执行,本项目定性>定量)。致命/严重→打回;轻微→flag 放行。
- **重做 = 盲重抽**(同输入换采样)。**judge 不给流程任何额外信息**(用户约束):评语只进带外日志(喂人/训练),绝不注入子流程下一次 prompt;复用现有 draw 级重抽 `_make_correction_validator`,**不碰 `feedback` 注入**。
- 推论:**确定性阶段(2/3/5)同输入必同出、无法自重做→判坏必弹上游 LLM 阶段**。
- 打回目标 = **judge 归因的根因阶段**(非机械上一步;2f 错在 0_reading 却要 1 之后才显)。
- 预算 **每阶段 3 次**→升级/终止 + 记 **hard sample**(靠自己输入做不出=训小模型最值钱监督信号)。
- **judge 密度**:LLM 阶段(0/1/4)重判;确定性阶段(2/3/5) judge 只看渲染做感知/合理性裁决、不重算坐标→几何阶段中间文件必须含 judge 能看的渲染件。
- **judge=开发期脚手架/数据工厂**:每条 verdict=①训小模型监督标签 ②"哪些 judge 经验可固化成确定性校验"清单。等小模型吃透+错类固化够→**撤顶尖 judge,上线只留确定性校验+小模型(轻量化,迁开源自训小模型)**。点 2(judge)与点 3(上线轻量)不是矛盾、是流水线。半人工期人能看 judge 带外评语手修、但不注入自动 prompt。

**Why**:2f 走廊识图错全程无门逮住(reading 自检过/渲图肉眼漏/correction 静默修对/三门只验最终模型);要让错在产生段显式可见+可归因。

**reading vs correction 分工再定(2026-06-15,重要,纠正早前把 polygonize/区数塞 reading)**：
- **0_reading judge 问「这张图画了什么,你忠实描了吗」**=per-image 感知,**不建拓扑、不要参考答案**。逮:① 确定性(结构 linter block / 单图尺寸链闭合 / **stroke↔dimension 互核**逮数字抄错含整条一致抄错 / 单图越界) ② VLM judge 七类明显识别错误(漏描/杂物当结构/笔型认错/数字抄错/facade_axis 声明与视图标签自洽/门 healing/整片缺失错位)。
- **1_correction judge 问「能否无定性错重画回原图?区数/窗数对不对(有参考答案)」**=跨图 reconcile+拓扑+对参考,**最依赖人工校验**。归 correction:**填色区图**(现 zonification 未启=房间即 zone 每层填色;启后另出纯 zone 划分图不画墙)、区数 vs testdata thermal_zones、窗数 vs 参考、跨图外包/z-stack 一致、**平面↔立面窗位一致(逮立面轴翻落位)**、redraw 保真。
- **polygonize(墙网闭合成区域)=拓扑重建=correction 域,reading 红线禁区**。

**0/1 通道事实(读 A0/A1 核实)**:0_reading 同一份 JSON 出 `strokes[]`(拓扑+大致位置)+`dimensions[]`(精确量级)两通道;1_correction 拓扑取自 strokes、量级取自 dimensions,**尺寸链为权威量级,冲突升级 A3 `checksum_failure`**(非闭眼硬挑);provenance 形式化未接=现 legacy 模式(§5.3)。**正因 1 信尺寸链>strokes,抄错尺寸会被忠实建成错量级无从察觉→reading 必须抓数字抄错**。

**facade 翻译(§2 待办)**:现 `reading_summary.md §3` 散文公式喂 correction LLM 套用→改为 0_reading 出**结构化 facade_axis 字段** + **代码确定性翻译 local→world**,§3 降级人看镜像(几何归代码)。

**逐段进度(2026-06-15 探讨,全部入档 contracts §1)**:
- **0_reading 锁**:per-image 忠实(结构 linter block / 单图尺寸链闭合 / stroke↔dimension 互核 / 越界 + VLM judge 七类明显识别错误)。
- **1_correction 锁**(最依赖人工):①确定性=A0§7 几何校验器 + 立面 local→world 代码翻译 + 跨图对账 + 窗位落墙(逮轴翻落位) + 区数 tripwire → correction_checks.json;视觉件=填色区图 `*_zones.png` + 立面窗位图 `*_elev.png`。②**看原图的 VLM judge** 对参考答案(testdata + B2 gt.json)裁 redraw 保真 5 条;区数双管(tripwire+judge)。
- **2+3 几何内核 锁**:**确定性阶段靶子=代码(单测+不变量),无 per-run LLM judge**。①确定性=封闭完整+法向一致+kernel_gate_report 提 block 关口+互逆/面积+覆盖完整性(shapely,随 B5)+spec 自洽 → kernel_checks.json。②**交互 3D 查看器**(pyvista `export_html`:转/半透/剖切+按切配上色,并掉单出 2D 覆盖图)+静态 PNG。**重要架构补充**:交互 3D = **上线保留的「用户几何确认门」**(确认几何对才进仿真)——**不是所有 judge/门都是 dev 用完即撤**,这道人工确认门留产品(BEM 常见"先看模型再跑")。

**4_mep 锁框架**(2026-06-15):输入几乎无 MEP 信息=基本全套默认,**本轮只搭框架**——引用完整性(construction/material/schedule/per-zone 覆盖 + schedule 完整性,从 5/IDF 前移)是 EP 正确性硬需求现做;合理性区间 flag + 文本 judge 类型适配先占位、等补 MEP 输入再充实;无图无 3D;参考=mep.md DRAFT,不需 gt.json。
**5_intakeoutput 锁**:确定性跨域引用完整性(zone↔per-zone 荷载、construction→material→schedule 链路)→ assembly_checks.json,契约成兜底,无 judge 无渲染。跨阶段自洽归属:3=几何内部/4=MEP 内部/5=跨域接缝,不重复。

**0–5 逐段全部锁定(2026-06-15)**。产出三件交叉审阅工作流(CLAUDE §6#14):① 设计 review 请求 `logs/review/request/2026-06-15_pipeline_0-5_validation_architecture_design_request.md` ② **施工方案 [pipeline_validation_build_plan.md](AI_agent/architecture/pipeline_validation_build_plan.md)**(模块布局 src/validator/checks/+src/agent/judge/ + 依赖序 M1 地基→M2 全段确定性校验+视觉件→M3 judge 门基建+三 judge→M4 集成+上线门+baseline + 逐项施工卡 + 风险点) ③ 施工 review 请求 `..._validation_build_plan_request.md`。

**Codex 双 review 已回并全盘接受(2026-06-15,双 CHANGES REQUESTED)** → contracts 升 v7 + 施工方案升 v2。关键纳入(原设计被纠的几处):①**确定性后置失败 fail-closed 记 code defect、不弹上游**(原"判坏必弹上游"错;0=manual→human_redraw_required;只 stochastic 0/1/4 盲重抽;全局预算+循环检测;hard sample 先 quarantine) ②**新增 M0 执行/审计地基**(stage runner/append-only attempts/失效 DAG/resume/hash 绑定 approval——没这层不接 gate) ③**facade 仅 image-local**,world_axis/base_world 归 1_correction 生成(原塞 reading 越界) ④**reading schema 迁移**(dimensions 加 chain_id/role/order/value_m/text_verbatim/anchor;**stroke↔dim 降低置信 flag、非 2f 主验收**) ⑤2f 归因 delta-audit(correction 修对也保留"0 曾错"标签)+固化真实坏 fixture ⑥**矩形 coverage 本轮 block**(非随 B5) ⑦**uncaptured 不 block** ⑧**4 拥有全部 MEP 引用图+对象语义(SimpleGlazing/NoMass/schedule type)+统一 idf_fragments parser;5 仅 backstop**(Construction 不引用 Schedule) ⑨check schema v2(status/hash/policy-事实分离) ⑩用户门=调用策略+hash 绑定 ⑪viewer trimesh 先行+spike。施工序改 **M0→M1(schema+parser)→M2a(0/1)→M2b(2/3)→M2c(4/5+EP)→M3 judge→M4 产品**。review 文档 logs/review/review/2026-06-15_pipeline_0-5_validation_{architecture_design,build_plan}_review.md。

**Codex re-verify 已回(2026-06-15,NOT YET CLOSEABLE→must-fix 全落)** → contracts v8 + 施工方案 v3。re-verify High 1 戳中要害:**§0.4 不能当覆盖 banner、§1/§3 必须逐段改齐**(我原偷懒用 banner)——已逐处改:0_reading facade→image-local 朝向字段(view_facade/local_x_positive=image_left_to_right/mirrored/orientation_evidence,**不混 east/west**)·uncaptured 不 block·stroke↔dim 降「内部一致性」低置信非 2f 主验收·0=manual→human_redraw;1_correction world 落位在本段生成+delta/audit 归因;2/3 viewer trimesh 先行·用户门=调用策略+hash 绑 digest·kernel_gate_report 提 block;4 idf_fragments parser+对象语义(SimpleGlazing/NoMass/schedule type) block;5 仅 assemble+backstop·全 MEP 引用图归 4。Medium:完整失效 DAG(0→1-5/1→2-5/2→3-5/3→4-5/4→5)+approval 绑 geometry checkpoint digest(building_geometry+geometry_specs+kernel report+version)+per-milestone 验收测试矩阵(M0 状态机/M2a-c 真实坏 fixture/M3 judge unknown 不串线/M4 兼容)。**Codex 判:三项完成即两 review CLOSEABLE、可直接开工 M0、无需第三轮架构重审。** grep 自查活区块矛盾词已清。

**How to apply**:施工前读 contracts v8(§0.3/§0.4 速查/§1 正文为准)+施工方案 v3+三份 review;每条 check 配单测+真实坏 fixture、policy 与事实分离(stage+profile 映射 block/flag)、改 skill/src 按 §6#5 备份。**下一步**:review 闭环(可标 CLOSED),**按 build plan M0(执行/审计地基)→M1→M2a/b/c→M3→M4 施工**;确定性优先(M2 无 per-run judge),判 judge M3 后置;确定性后置失败 fail-closed 不弹上游。
