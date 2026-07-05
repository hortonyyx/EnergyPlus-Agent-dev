# 审阅结果 · 0–5 管线逐阶段「输入·输出·校验」架构设计

> 审阅执行：Codex，2026-06-15  
> 审阅对象：`architecture/pipeline_stage_contracts.md`（2026-06-15 v6）  
> 请求：`request/2026-06-15_pipeline_0-5_validation_architecture_design_request.md`

## Verdict

**CHANGES REQUESTED。**

总体方向成立：reading/correction 分工、确定性门先于 judge、定性 verdict
代替数字评分、2/3/5 以代码不变量为主、judge 评语不注入自动重做 prompt，这些原则都值得
保留。

当前仍有四处会改变系统行为的架构缺口：确定性失败的路由规则会掩盖代码 bug；0_reading
目前不是可自动重抽阶段；`facade_axis.base_world` 越过了 reading/correction 边界；
2f 触发类与已知覆盖洞仍没有可靠的自动化闭环。修正这些边界后再锁施工接口更稳妥。

## Findings

### High 1 - “确定性阶段判坏必弹上游”不成立，且 0_reading 当前无法自动重抽

**对应：F2 / F4。**

**证据**

- `pipeline_stage_contracts.md:101-106` 定义：judge 打回即盲重抽；2/3/5 同输入同输出，
  判坏必弹上游 LLM 阶段；打回到 judge 归因的根因阶段。
- 当前 `src/agent/pipeline.py:646+` 的 `run_pipeline` 从 1_correction 开始，0_reading
  是外部半人工目录；代码没有“重新读某一张图”的 stage runner。
- `_make_correction_validator` 只是 `_call_json_llm` 的单次 draw 校验回调，不是跨阶段
  路由/失效/重跑 harness。

**影响**

确定性阶段失败至少有两类，不能统一弹上游：

1. 输入违反该阶段前置条件，根因确在上游；
2. 输入满足前置条件，但代码输出违反后置条件，根因是确定性代码 bug。

第二类若靠上游换样本“绕过”，会把可复现代码缺陷伪装成数据波动。另一个现实问题是，
judge 即使归因到 0_reading，现有自动流也无可调用的重读函数，只能终止并交人处理。

**建议**

- 把失败分类写进架构：`upstream_input_failure` / `deterministic_code_failure` /
  `stochastic_draw_failure` / `judge_mismatch`。
- 只有 stochastic 0/1/4 runner 才允许盲重抽；确定性后置条件失败必须 fail closed，
  记 code defect，不得自动弹上游。
- 当前半人工 0_reading 的动作定义为 `human_redraw_required`；等 VLM runner 接入后再开放
  自动 3 次预算。
- 增加全局预算与循环检测；“每阶段 3 次”之外还要限制整条 run 的总 draw/judge 次数。
- hard sample 先标为 `quarantined_failure`；只有排除 judge 误判、代码 bug、配置错误后，
  才能进入训练 hard-sample 集。

### High 2 - `facade_axis.base_world` 要求 0_reading 做跨图世界落位，违反本次分工

**对应：F1 / F7。**

**证据**

- `pipeline_stage_contracts.md:114-122` 明确 0_reading 只做 per-image 忠实描摹，不做跨图、
  拓扑或世界落位。
- 施工前置 schema 却要求每个立面写
  `{world_axis, sign, base_world:[x,y,z]}`。
- North 的 `base_world=[max_x,max_y,0]`、West 的 `[min_x,max_y,0]` 必须先知道多张平面
  reconcile 后的 footprint；这不是单张立面图的可观察事实。

**影响**

VLM 会被迫在 reading 阶段重复推导跨图世界坐标。若字段写错，代码翻译只是确定性地放大
错误。对称立面上，sign 翻转还可能同时通过“窗落在外墙”和肉眼对称检查。

**建议**

- 0_reading 只产图内事实：`view_facade`、`local_x_direction`（相对 east/west 或
  left/right）、可选镜像标记及证据。
- `world_axis` 与 `base_world` 由 1_correction 根据 authoritative facade 名、
  reconciled footprint、z-stack 确定性生成。
- 若图纸可能镜像，sign 必须有独立证据（方向标、视图标题/图框约定或人工确认），不能由
  VLM 自声明后再检查其“自洽”。
- 旧 `facade_axis_note` 只作迁移输入；不要让文本 note 与结构字段长期双真源。

### High 3 - 2f 触发类并未被确定性线保证捕获，correction 还可能擦掉归因证据

**对应：F6，重点结论。**

**证据**

- `pipeline_stage_contracts.md:122` 把 stroke↔dimension 互核描述为可逮“整条一致抄错”。
- 当前 reading schema 的 stroke 米制端点、dimension `text`、`from/to` 都由同一次识图
  生成，没有独立像素锚点、OCR token、`chain_id`、overall/segment 类型。
- 2f 式“把隔墙延伸进走廊”可以同时满足尺寸链闭合和 stroke 长度自洽。
- `pipeline_stage_contracts.md:134-135` 的区数 tripwire/J1 在 correction **输出后**运行。
  若 correction 像本次一样已静默修对，区数、填色区图和最终 redraw 都会 pass。

**影响**

新设计对 2f 的实际覆盖是：

- **J0 原图 vs 线框**：应能抓多画进走廊的墙，是主捕获线；
- S0 尺寸链/stroke 互核：只能抓内部不一致，不能保证抓“自洽地全错”；
- S1 区数/J1：仅在错误幸存到 correction 输出时抓得到。

因此只要 J0 漏判、correction 又修对，原始 reading 错仍不会显式归因，触发目标没有完全
达成。

**建议**

- 把 stroke↔dimension 改名为“内部几何-尺寸一致性”，不要宣称它能验证原图抄录真值。
- 若要确定性验证抄录，先扩 schema：dimension `chain_id`、`role=overall|segment`、
  `order`、原图 pixel bbox/anchor、verbatim OCR token、provenance；或引入独立 OCR 通道。
- 增加 correction delta/audit 完整性检查：当 correction 的 cells 拓扑与 reading 墙图
  明显矛盾、或依赖 testdata 修正时，必须产生带来源的 correction/conflict 记录。这样最终
  模型修对也不会丢失“0_reading 曾错”的标签。
- 固化真实 bad fixture，而不是只保留修正后的 sm20_anchor。

### High 4 - 已知“内部边界覆盖洞”被 deferred，同时 2/3 又取消自动 judge

**对应：F4 / F6。**

**证据**

- `pipeline_stage_contracts.md:144-146` 明确现有 per-pair 门抓不到“两侧都标 Outdoors /
  不在配对图”的覆盖洞。
- 同段把 coverage completeness 延后到 B5，2/3 又明确无 per-run LLM judge。
- 该错误并不依赖 L/U 非矩形；矩形相邻 cells 同样可通过“期望共享边 vs 实际配对面”比较。

**影响**

在 `--auto-confirm`、CI 或用户肉眼漏看时，已知错误类仍可自动通过。3D 几何外形也可能
完全正确，只是内部面 OBC 错，普通用户不容易从模型外观发现。

**建议**

- 本轮先实现**当前矩形能力 profile** 的 coverage invariant，并设为 block：
  从相邻 cell polygon 的共享边/共享楼板推导 expected internal interfaces，与实际
  reciprocal pairs 做集合/面积对账。
- B5 只负责把同一接口泛化到正交多边形、退台和 void，不应推迟矩形检查本身。
- 在该 invariant 落地前，不应宣称 2/3 的自动校验闭环完整。

### Medium 1 - `uncaptured_visual_elements` 非空不应是结构 block

**对应：F3。**

**证据**

- 设计与施工方案把 `uncaptured 非空` 放入 0_reading 结构 linter block。
- committed `sm20_anchor/0_reading/2f_view.json` 的合法 clean drawing 值就是 `[]`；
  当前工作树为满足规则写入了“没有家具/没有楼梯”等负面陈述。

**影响**

干净图会被错误打回，数据也会被迫填充“未观察到什么”，污染字段原本“看见但未画”的语义。

**建议**

- block 只要求字段存在且为 list。
- 只有检测到 ignore/heal/unknown 事件时，才要求对应 provenance 记录；在事件 schema
  未建立前保持 flag，不能要求非空。
- 结构 block 应补真正的不变量：唯一 id、有限数值、合法 geometry shape、非退化 line/rect、
  dimension 可解析、axis 与端点一致。

### Medium 2 - 4_mep / 5_intakeoutput 的校验所有权仍重复，引用链表述也不正确

**对应：F1 / F3。**

**证据**

- `pipeline_stage_contracts.md:155` 已让 4_mep 检查 construction→material、
  load/HVAC→schedule、per-zone 覆盖。
- `:163-164` 又让 5 检查 zone↔load 以及“construction→material→schedule 链路”。
- Construction 不引用 Schedule；实际是两条图：
  geometry→construction→material，以及 people/lights/hvac→zone/schedule。

**影响**

同一缺陷可能在 4、5 重复报，root stage 不稳定；错误的“串行链”也会把 parser/检查器写偏。
而且 4_mep validator 已拿到 required zone set 和 used constructions，绝大多数 seam
在 4 输出点已经可见，并非“只有装配后才显形”。

**建议**

- 明确引用图与唯一 owner：
  - 3：surface/window→zone/adjacent surface；
  - 4：geometry required constructions→construction→material，以及
    people/lights/hvac→required zone set/schedule；
  - 5：只做最终 Pydantic assembly 与上述结果的 backstop，不新增另一套语义解析。
- 若 5 重复检查，明确标注为 defense-in-depth，不参与 root-stage 归因。

### Medium 3 - MEP 当前只查引用完整性，仍漏已知对象语义错误

**对应：F6。**

**证据**

- 4_mep 本轮只实做引用覆盖和 Schedule:Compact day-type 完整性。
- 项目历史已出现 SimpleGlazing 被错误作为多层 construction 材料导致 EP fatal；
  请求点名的 no-mass material draw 也不是“名字是否存在”能发现的。

**影响**

名称链全部闭合仍可能生成 IDD/对象语义非法或物理字段缺失的 MEP。

**建议**

本轮至少加入可确定性判断的 IDF-fragment 结构规则：对象可解析、必填字段、正值约束、
`WindowMaterial:SimpleGlazingSystem` standalone construction、`Material:NoMass`
正 thermal resistance、Schedule type 引用存在。合理区间可继续 flag/deferred。

### Medium 4 - 用户几何确认门需要成为调用策略，不应成为管线不可绕过的交互

**对应：F5。**

上线保留 3D 查看器与轻量化目标并不冲突，但“每次都暂停等用户”会破坏 batch、CI、
`intake_node` 和 API 调用。应把“生成 review artifact”和“是否要求人工批准”分开：

- viewer 始终可产；
- `confirmation_policy=required|optional|disabled` 由产品/CLI 调用方决定；
- 批量基线可显式 auto-confirm，但仍保留 hash 绑定的 approval/audit；
- 人工批准必须绑定 exact `building_geometry.json` hash，不能批准后重新抽 1_correction。

### Low 1 - judge 密度总则与逐段契约互相矛盾

`pipeline_stage_contracts.md:106` 写 2/3/5 judge 看渲染做裁决；`:144-146`、`:163`
又明确 2/3/5 无 per-run judge。应统一为：自动 judge 只在 0/1/4；2/3 只有用户门或
dev 手动触发 VLM；5 无 judge。

### Low 2 - judge verdict 需要“不适用/无法判断/归因不确定”

只用 pass/minor/major/critical 会逼 judge 对不可见证据强行定级。建议 schema 增加
`not_applicable`、`insufficient_evidence`、`root_stage|null`、`root_confidence` 和
`retriable`；unknown 不得自动路由。

## F1-F8 明确答复

| 项 | 结论 |
|---|---|
| **F1 边界** | polygonize/区数/跨图归 correction 是对的；但 `facade_axis.base_world` 又把跨图世界落位塞回 reading，需移出。4/5 引用所有权也需去重。 |
| **F2 盲重抽** | 对随机 draw 自洽；对系统性错会按设计终止，这本身可接受。不可接受的是把所有确定性失败弹上游、把当前不可运行的 0 当自动 stage、以及未经排障直接标 hard sample。 |
| **F3 分层** | reading 只让真正 schema/数值不变量 block 合理；`uncaptured 非空`过度 block。coverage 在当前矩形 profile 应 block，不应只 flag/defer。 |
| **F4 无 judge** | 原则成立，但前提是 postcondition 完整。矩形 coverage 洞未补前，2/3 的自动线仍不闭合；确定性代码 bug 必须停，不得上游重抽。 |
| **F5 用户门** | 与轻量上线协调，但必须是 caller policy + hash-bound approval，不能把交互硬塞进通用 pipeline。 |
| **F6 完整性** | 2f：J0 应抓；确定性线不保证；correction 修对后 S1 会失去原始归因。残余盲区至少包括 facade 自声明错、矩形覆盖洞、对象语义非法/no-mass。 |
| **F7 facade 翻译** | 翻译归代码正确；`base_world` 与 world placement 应由 correction 生成，reading 只给图内方向证据。 |
| **F8 成本** | 确定性在前能明显降成本；还需全局预算、按 flag/新样本触发 judge、artifact hash cache，避免每次全量重判。 |

## Acceptance Summary

| 设计项 | 结果 |
|---|---|
| reading / correction 主职责切分 | PARTIAL：polygonize 切分正确，facade world placement 越界 |
| 两道门与定性 verdict | PASS，需补 unknown/归因不确定 |
| judge 不注入反馈 | PASS，保留 |
| 盲重抽与根因路由 | FAIL：确定性 bug 分类、0 runner、预算/循环未定义 |
| 2f 触发案例闭环 | PARTIAL：J0 有覆盖，确定性与最终归因不保证 |
| 2/3/5 无自动 judge | PARTIAL：原则可接受，矩形 coverage invariant 必须先补 |
| MEP/assembly 校验归属 | FAIL：重复且引用图表述错误 |
| 上线用户确认门 | PASS-WITH-CHANGES：改为 caller policy + artifact hash approval |

