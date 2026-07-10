# C2 收官设计全面对抗审（三审）

Date: 2026-07-10  
Object: `AI_agent/proposals/c2_full_unlock_design.md`（本地未提交 v2.1）  
Evidence: `AI_agent/logs/experiments/2026-07-10_e4_relative_north_axis_probe/`  
Prior verdicts: `2026-07-10_c2_full_unlock_review.md`、`2026-07-10_c2_full_unlock_review_r2.md`  
Verdict: **APPROVE-WITH-CHANGES**

本轮指定复核的 10 项：**CLOSED 10 / PARTIAL 0 / NOT-CLOSED 0**。

- r1 上轮残留 5 项：**5/5 CLOSED**。
- r2 新增 5 项：**5/5 CLOSED**。
- 历史累计：r1 的 16 项与 r2 的 5 项现均已闭合，**21/21 CLOSED**。
- 本轮未发现新的架构性 finding；列 **5 项 required changes（HIGH 1 / MEDIUM 4）**，均不改变已拍方向、主 DAG 或工作量主档。

v2.1 已达到从 REWORK 升档的条件：E1/E2/E3 的证据与责任边界可执行，v3 类型和 sidecar 边界已选定，manifest 无先用后造，知识/interactive 不再依赖无证据抽签，E4 也从“字段存在”推进为经 EnergyPlus 25.1 实证的 Relative 出口方案。尚需的 changes 是把几处跨节旧摘要和当前代码接缝写到无二义，适合在 B-M、B2、E4-output-contract 等细稿开工门前补入；无需为此重开第四次整稿架构审。

本轮只读本地工作树和已有探针产物，除本 verdict 外未修改任何文件，未 commit。

## 一、E4 探针独立复核

探针结论可信，本审没有只采信 `RESULTS.md`：

1. 输入 diff 显示 `world_000 → rel_000` 只把 `GlobalGeometryRules` 从 World 改 Relative，并把 14 个 Zone 的非零 origins 归零；surface/fenestration vertices 未改。`rel_000 → rel_090/270` 只改 `Building.North Axis`。
2. 直接解析四份 `eplusout.eio`：均为 **114 HeatTransfer Surfaces / 14 Zones**；`rel_000` 对 `world_000` 同名面 azimuth mismatch 0，`rel_090/270` 对 `rel_000` 的模 360 偏转 mismatch 0，四变体 zone floor-area/volume mismatch 0。
3. 四份 `eplusout.end` 均 `Completed Successfully`、0 severe；Relative 三份各 3 warnings，World 为 5。
4. “Any non-zero Building/Zone North Axes or non-zero Zone Origins are ignored” 只在 World err 中出现 1 次，Relative 三份均 0 次。

因此 `Relative + Zone Origin/Direction 全 0 + building-frame detailed vertices + Building.North Axis=θ` 的核心 surface/zone 变换已获证。探针没有 daylighting/shading 数据行，故它不替代 v2.1 已列的 building-bound coordinate-object 全量审计；该审计继续作为 `E4-output-contract` 细稿和验收门，而不构成继续 REWORK 的理由。

## 二、10 项闭合矩阵

| ID | 上轮状态/severity | 三审状态 | v2.1 核验 |
|---|---|---|---|
| A-04 | PARTIAL / HIGH | **CLOSED** | E2′.5 已升为 opening×claim，provenance/applicability 双轴、per-claim denominator、partial/NA 呈现均明确；B-M 在 reading 前生成，judge 独立重算。 |
| B-01 | PARTIAL / BLOCKER | **CLOSED** | v3 已选 `Floor.id + Floor.footprint` 内嵌；FacadeSegment、Window ref/evidence、north-axis evidence、knowledge-ref、独立 sidecars、`extra=forbid` 与 legacy adapter 均定案，不再留“键或内嵌”二选一。 |
| B-04 | PARTIAL / BLOCKER | **CLOSED** | B4a/B4b 保持 XL 拆批；B4b 明列 per-claim NA 机读形状、denominator、policy/sidecar/render 与 scorer schema 身份。 |
| B-06 | PARTIAL / HIGH | **CLOSED** | B-M 成为前置 producer；accepted-attempt/hash/schema/helper/manifest 绑定保留；B5b 只消费 manifest 并归档 hash，不再兼任 producer。 |
| B-07 | PARTIAL / BLOCKER | **CLOSED** | `B-M`、`Vg/Va`、B4a/B4b、B5/B5b 与 E4-output-contract/B-O 的图无环且无 manifest 反向依赖；B2b 仍正确依赖 B2+B3。 |
| R2-A-01 | HIGH | **CLOSED** | 宿主 resolver 已按 plan/elevation 拆支：plan 可挂 hidden segment，elevation 只在 visible candidates 中解析 room；negative evidence 也加了 completeness 前提。C-03 只清理重复节的旧绝对表述并补 manifest 机读槽。 |
| R2-A-02 | HIGH | **CLOSED** | prior_fill 已禁止 LLM 无证据抽签，要求唯一 default/无并列确定性选择；五元组 knowledge ref、floor-local z、ceiling/clearance guard 与 no-clamp 均在。C-05 完成首表跨 entry 匹配和 hash 规范。 |
| R2-A-03 | MEDIUM | **CLOSED** | `NEEDS_INPUT`、request artifact、checkpoint digest、resume、attempt 记账与 CI fail-fast 均冻结，interactive 不会静默降级。 |
| R2-B-01 | BLOCKER | **CLOSED** | Relative 路线已由用户定案，E4-output-contract 前置且工作量 S→L；EP 25.1 探针五项经本审独立复算成立。C-01 仅把现代码的实际写入点和 legacy gate 纳入细稿硬门。 |
| R2-B-02 | HIGH | **CLOSED** | accepted correction orientation 已成为唯一 owner；装配 override、typed evidence、顺时针角语义、真值 0/assumed 0、sanity、direction semantics 与 gt applicability 均明确。C-02 固定兼容占位 0 的具体校验语义。 |

上述 CLOSED 是设计决策闭合；B2/B2b/B4/B5/E4 等仍须按 v2.1 自身要求先出代码级细稿，不等于授权跳过批次审阅直接连续施工。

## 三、v2.1 末尾 3 个开放问题

### 1. r2 五条升审门是否全部闭合？

**是。** 对应的 10 个复核项全部 CLOSED；唯一原 BLOCKER（World 下 North Axis 无效）已由 Relative 定案、前置细稿批与实跑探针共同关闭。剩余 C-01～C-05 是局部合同精确化，不要求改变方向或重排主链。

### 2. MEP `building.north_axis` 用装配 override 还是从 MepOutput 移除？

**本轮采用装配段 deterministic override，暂不移除字段。** 这是 C2/v3 的低兼容面方案：现有 `MepOutput`、4_mep fixture、11 字段 IntakeOutput 与下游 BuildingSchema 不需要破坏性改型。

必须同时写死以下语义，避免“默认 0 与权威 θ 不同”被误判为 conflict：

- 4_MEP 里的 `building.north_axis` 是**无权威兼容占位**，校验为且只允许 `0.0`；LLM 显式给非零值在 S4 直接 INVARIANT fail。
- `assemble_intake_output` 必须接收 accepted orientation evidence，并**无条件用其 `value_deg` 替换占位 0**；不得拿占位 0 与 θ 做值冲突比较。
- 硬冲突只指 orientation artifact 缺失/多份、schema/digest 不匹配、角度非法或两条运行路径输入不一致。
- 后续若单独做 MepOutput breaking version，可再把 north_axis 从 authorable subtype 移除；C2 不为此扩大改面。

### 3. r2-Q6 的四层知识 schema 能否直接采用，还有什么缺项？

**四层骨架直接采用，但须补四个确定性字段/规则后才算冻结：**

1. `entry.applies_to` 使用版本化、规范化 `space_type_id`；自由文本 `Cell.role` 先经显式 alias/taxonomy 映射，未知 role 不做模糊匹配。
2. 多个 entry 同时命中时定义 specificity/`match_priority` 全序；并列为 INVARIANT。候选层建议统一为每 entry **恰一 `default_candidate_id`**，不要同时保留“default 或 candidate priority”两套默认算法。
3. 明确 no-match/候选 runtime guard 全失败的终态：有显式 generic entry 才可 fallback，否则 interactive→`NEEDS_INPUT`，prior_fill→unresolved/INVARIANT，不回 prose/LLM 猜值。
4. `content_sha256` 定义为规范化 payload（排除 `content_sha256` 自身）之 hash，或改为外置 digest；dataset version 一经发布不可原地改。静态 schema/load 校验与结合当前 floor ceiling 的 runtime guard 分开记账。

## 四、APPROVE-WITH-CHANGES

### C-01 — HIGH — E4 Relative 合同须落到确定性运行状态，并显式保住 v1/v2 分支

v2.1 已选对方案，但当前代码仍有三个具体 seam：`intake._seed_config()` 只写 building/site，`ConfigState.global_geometry_rules` 默认 World；`zone.py` 还明确指示 LLM 把 x/y/z origin 写成房间/楼层位置；公开 IntakeOutput 又没有 coordinate-system 字段。若细稿只改 prompt 或只改 Building North Axis，仍可能复发 r2 的假完成；若全局无门切 Relative，又与“v1/v2 行为不变”承诺含混。

建议修法：`E4-output-contract` 冻结一个**内部**（不扩 11 字段）的 `OutputCoordinateContract`/run metadata，绑定 accepted correction schema+digest；v3/E4 路径由 intake seed 确定性设置 `GlobalGeometryRules=Relative`，Zone agent 后由代码统一把 x/y/z origin 与 direction 覆盖为 0，并以 gate 拒绝任一非零，prompt 只作辅助。v1/v2 默认继续走现 World legacy branch，除非另案批准全局语义迁移；不能用 `θ != 0` 猜分支，因为 v3 的真值 0/assumed 0 也属于 E4 合同。integrated 与 stepwise 路径都须断言最终 ConfigState、IDF setting、14 区 origins 与 EP warning。

### C-02 — MEDIUM — 把 MEP override 的“占位 0”语义写进规范与 gate

按 Q2 采用 override，但将 E4.2 的“MEP 不得书写/冲突硬错”改成上述精确定义：S4 只允许占位 0，S5 无条件用 accepted θ 覆盖；默认 0 对 θ=90 不是 conflict。否则实现者可能对每个非零 θ 都报假冲突，或静默接受 MEP 的第二权威。

### C-03 — MEDIUM — negative evidence 的前提须在 E2 主条款和 B-M schema 中同样可执行

E1′.2 已正确限定 negative evidence，但 E2′.1 仍保留“段 observed 而一边无窗→必有一边读错”的旧绝对句。将其改为引用 E1′.2，并在受信 B-M manifest 中类型化 `negative_evidence_capable_claims`、可信 coverage region/interval 与 completeness 来源；reader 不得通过自报“低清/没看见”改变 judge denominator。没有受信完整性声明时，“无”只能是未佐证，不是 conflict。

### C-04 — MEDIUM — 同步两处旧术语，避免 Vg/Va 与方位语义被反向实现

- E1′.4 仍把“segment+visibility+applicability”统称为只吃 polygon+direction 的 V；改成 `Vg(polygon,direction)` 与 `Va(Vg, B-M, opening claims)`，两者均可为纯函数，但输入/责任不同。
- E4.4 的“图纸‘南立面’=建筑系南”须加条件：只有 manifest `direction_semantics=building_axis` 时成立；`true_azimuth` 必须带 numeric `azimuth_deg` 并经 θ 映射到 building-axis view，`unknown`/不可唯一映射则 conflict 或留 C3，不得与 E4.3 的“图名只是 hint”冲突。

### C-05 — MEDIUM — 将知识冻结规则写回规范节，删除旧的 LLM 候选摘要

`知识库骨架`仍写“表内选择（LLM 只挑候选）/每条 id+版本+出处”，与 E2′.2 的 deterministic default 和五元组引用不一致。把 Q3 的四层 schema及新增四规则直接写入该规范节；尤其定义跨 entry 匹配全序、no-match 终态和 hash canonicalization。设计正文须自包含，不能让施工者回查 r2 verdict 才知道真正 schema。

## 五、增量扫结论与放行边界

- 未发现新的几何反例、D1–D10 冲突、gt 泄漏、DAG 环或 E4 方向反号。
- E4 探针覆盖普通 heat-transfer surfaces、fenestration、zone area/volume；daylighting/building shading/site shading 的相对/世界坐标归属继续由 C-01 所述细稿审计，不把“探针中 0 行”误写成已覆盖。
- `APPROVE-WITH-CHANGES` 放行的是 v2.1 总设计与分批细稿阶段，不放行 B2→B6 连续施工。C-01/C-02 在 E4-output-contract 开工前落；C-03/C-04 在 B-M/Vg/Va 细稿前落；C-05 在知识表/loader 细稿前落。
- 五项按上文机械并入后，不需第四次整稿复审；各代码级细稿照 v2.1 既定纪律独立审阅。

## 审阅需求（review-ask）

none — routine review
