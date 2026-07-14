# C2 B4b 批施工细稿 v2

- 日期：2026-07-14
- 出稿角色：B4b 批施工细稿出稿人（sol 次高档）
- 状态：已吸收 r1 <code>APPROVE-WITH-CHANGES</code> 的全部 2 MINOR/1 NIT 与五项主控裁决；本文件只定义施工合同，不表示代码或资产已落地
- 范围：segment-level plan/elevation scorer、Va 驱动的逐 claim applicability、独立 denominator、机器可读 NA、PNG 灰色斜线、score sidecar/cache 身份
- 禁止夹带：B5 host resolver、B5b provenance HTML 着色、B6 资产迁移，以及任何 golden/GT 资产变更

## 版本史

| 版本/审次 | 日期 | 累计记录 |
|---|---|---|
| v1 | 2026-07-14 | 首稿：冻结 B4b strict wire、四 Phase、Va-only applicability、per-claim denominator/NA、sidecar v8/cache 与 grade v3。 |
| r1 交叉审 | 2026-07-14 | Fable 最高档裁决 <code>APPROVE-WITH-CHANGES</code>：0 MAJOR、2 MINOR、1 NIT；§17 五项全部批准。判词：<code>AI_agent/logs/reviews/verdict/2026-07-14_c2_b4b_spec_review_r1.md</code>。 |
| v2 | 2026-07-14 | 累计吸收 B4B-F1：Phase A 登记完整 frame-transform hash preimage 进 A0；B4B-F2：reference plan/elevation 正证据区间公式；B4B-F3：GT interior shared-edge 零容差精确归组；§17 写入五项主控批准结论。 |

## 0. 执行结论

B4b 可以拆成四个顺序 Phase 独立施工、独立测试、独立合并，但只能在对应 B4a 接口落地并完成逐字对账后启动。B4b 的生产代码边界保持为 judge-only：GT、Va 适配、计分、sidecar、grade renderer 均位于 judge/run-stage 一侧；production schema 与 production artifact contract 不反向导入任何 judge 模块。

本稿冻结以下总裁决：

1. 现役 <code>SCORER_SCHEMA</code> 是字符串 <code>"7"</code>，B4b 落地值为 <code>"8"</code>。请求中“schema 2 重算”只作为旧机制来源，不作为当前盘面值。
2. GT v2 继续走现役 legacy scorer/renderer；GT v3 只能走 typed loader 与 B4b capability dispatch，禁止 raw-dict 降级到 legacy scorer。
3. Va 的 reference applicability ledger 是唯一 denominator 适用性来源；B4a 的 <code>visible_intervals</code> 只能作为 Vg 派生/校验信息，不能冒充第二份独立观察真值。
4. <code>NOT_APPLICABLE</code> 不等于 0 分、不等于半分；partial 也不固定折半。每个 claim 的 denominator 按 Va 精确可见区间计算。
5. 当前 B4a v3 GT 没有独立 appearance 真值，所以 <code>appearance</code> 在本批明确逐 claim NA；<code>host</code> 则只由 judge 临时解析出的 segment+zone 关系计分，不向产品写回 canonical host，也不抢 B5 resolver 所有权。
6. 现役 view manifest 没有可信的 GT source-view 映射、镜像信息和 true/unknown direction 解算结果。B4b 新增 judge-only score input bindings；禁止信任产品输出自报镜像或假定 <code>input_id == GT view_id</code>。
7. user/dataset completeness 由 judge-only overlay builder 生成“effective manifest”内存投影；现役 base manifest 仍是 execution 侧唯一 emitter，B4b 不改写它。
8. sidecar 身份扩大到 GT、capability、base/effective manifest、score inputs、Va/Vg/helper、judge tolerance、output 与 accepted-attempt 身份；任一不一致均自动重算。
9. B4b PNG 用灰色斜线表达未观察/NA；HTML 中对 assumed/observed 的猜测色仍归 B5b，本批只在 sidecar 留数据接缝。
10. 本批不新增、不修改、不搬迁任何 golden 或 GT 资产；真实 v3 案例 promotion 是独立资产批次和联合门禁。

## 1. 权威输入、盘面事实与解释规则

### 1.1 权威优先序

发生歧义时按下列顺序裁决，后项不得覆盖前项：

1. <code>AI_agent/proposals/c2_full_unlock_design.md</code> v2.2 的 B4b 总体边界；
2. <code>AI_agent/proposals/c2_b4a_detail_spec.md</code> v2，尤其 §6.2、§15.1、§15.2；
3. <code>AI_agent/proposals/c2_va_detail_spec.md</code> v2、现役 <code>facade_applicability.py</code> 和 Va construction verdict；
4. 当前盘上 judge、render、run-stage、manifest、schema 与测试实码；
5. 本稿对上游未定接缝作出的最小、显式、可撤销裁决。

若当前盘面与历史评审叙述冲突，以当前盘面确定迁移起点，以更高位设计确定目标；必须在 sidecar schema、测试与评审记录中显式说明，不得静默兼容。

### 1.2 已核验盘面基线

- <code>scripts/tool_scripts/run_stage.py</code> 当前 <code>SCORER_SCHEMA = "7"</code>。
- 当前 sidecar 顶层含 stage、attempt、output_hash、source、scorer_schema、case、tolerances、scores、elevation、floor_map、evidence、score_criteria；缓存身份未覆盖 GT hash/schema、capability、view manifest、helper version 或 accepted record。
- 当前 <code>reading_score.py</code>、<code>correction_score.py</code>、<code>elevation_score.py</code> 与 <code>render_grade.py</code> 均保留矩形 W/D、四 facade 或 raw-dict 假设；B4b v3 路径不得复用这些几何假设。
- 当前 elevation candidate 函数虽接收 along/sill/head/width tolerance，实际 legacy 匹配仍以 overlap ratio 为主。此行为必须作为 v2 regression 冻结，不能借 B4b 偷修。
- <code>ViewManifest</code>、completeness ruleset、Va ledger 与 helper 现役版本均为 <code>"1"</code>。
- base manifest 当前只从 case metadata 生成 completeness；schema 已能表达 <code>user</code> 与 <code>dataset_ref</code>，但没有对应生成 owner/path。
- <code>RunManifestV2</code> 已绑定 base view manifest hash 与 accepted StageRecord 链；当前 score sidecar 不属于 production artifact key 集。
- 默认盘面只有 <code>case_tests/test_baseline/gt/sm21_anchor/gt.json</code> 是 schema 2 GT，其文件 SHA-256 为 <code>a9be379b1735163528396c36d96653cdf71a67ffe54dde6f942c7c86f53f3f8a</code>。sm20 没有 GT。
- Va 现役 A0 hash preimage 是：按 <code>(floor_id, N/S/E/W rank, along.lo, along.hi, depth, id)</code> 排序后的完整 <code>FacadeSegment.model_dump(mode="json")</code>，使用 sorted-key、compact JSON 后 SHA-256。
- Va r2 已通过主体施工复核，但 B4b 必须吸收 VA-C7 六项测试/债务：第八 claim 显式拒绝、重复 <code>opening_id</code>、dangling source、product declaration 删除后的双调用、concave multi-segment fixture、删除/防回归 tautological no-op assert。当前实码已不含判词点名的 no-op（对应位置是正常 <code>flip</code> 计算），故该项以 source-scan 回归封口；不得为“制造清理 diff”重改纯核。

### 1.3 并行 B4a 处理纪律

B4a 正并行施工。本稿只依赖其 v2 细稿中冻结的公共合同，不把尚未完成的工作树文件当权威输入，也不预读后续 Phase 的半成品行为。每个 B4b Phase 启动前都执行 §14 的“落地后逐字对账门”；不一致时先停工评审，不写双轨 shim 掩盖差异。

## 2. 范围、所有权与不变量

### 2.1 B4b 拥有

- GT v3 typed scoring adapter；
- judge-only score config 与 A0 注册；
- judge-only view bindings、resolved-direction 引用与 completeness overlay；
- 任意正交/凹多边形的 plan boundary/interior segment scorer；
- GT opening 与产品 observation 的确定性匹配；
- reference/product/absence 三类 Va 调用和逐 claim denominator；
- plan/elevation claim score fusion、policy 与机器结果；
- score sidecar v8、cache invalidation、原子写；
- v3 grade PNG 的实际多边形投影和 NA 灰色斜线；
- legacy v2 完整回归与 typed CLI dispatch；
- VA-C7 六项回归债务。

### 2.2 B4b 不拥有

- 修改 production output schema；
- 为产品补写 facade segment id；
- B5 的 canonical host resolver 或 host namespace；
- B5b 的 HTML/REPORT provenance 色彩；
- 从图像猜 north、mirror、floor 或 source view；
- 生成/提升真实 GT v3、golden、verified overlay 资产；
- 放宽 B4a loader、Va ledger 或 B-M manifest 的冻结 wire；
- 把 <code>correction.yaml</code> 或 soft run config 当 judge tolerance 来源。

### 2.3 强制不变量

1. production 模块对 <code>src.agent.judge</code> 的 import 数为零。
2. judge tolerance 只来自版本化 strict config；缺项、额外项、非有限数或非法关系一律拒绝。
3. GT v3 loader 失败不得 fallback 到 v2/raw path。
4. 每个 opening 恰有七个 claim row，顺序与 Va 冻结顺序一致。
5. reference ledger 决定 denominator；product ledger 只作产品声明/证据审计，删除产品声明不得改变 denominator。
6. NA units 不进入 numerator 或 denominator；miss units 进入 denominator；partial units 由公式产生。
7. 对 unsupported combination 必须给机器可读 NA 或 REJECTED，禁止空对象、零分或 legacy fallback。
8. 匹配平局不能靠输入顺序、ID 字典序或浮点偶然性破局，必须拒绝。
9. sidecar identity 全量命中才允许 cache hit。
10. v2 评分与像素行为保持现役语义，sm20 无 GT 行为也必须锁定。

## 3. 术语与总数据流

### 3.1 术语

- target：GT v3 中一个 segment 或 opening。
- observation：reading/correction 在一个受信 input view/frame 中产生的可评分几何。
- reference ledger：由 GT target、受信视图与 completeness 生成的 Va applicability；唯一 denominator 来源。
- product ledger：由产品 declaration/feature state 生成的 Va ledger；只用于审计产品说了什么。
- absence ledger：针对 unmatched 产品 observation 构造的“GT 无正例”查询；只有受信负覆盖足够时才可判 extra。
- base manifest：execution 侧生成且 RunManifest 已绑定的原始 <code>ViewManifestV1</code>。
- effective manifest：judge 在内存中把获准 completeness overlay 合入 base manifest 后的 canonical 投影。
- score inputs：GT bundle 下独立 review 的 judge-only view bindings、direction resolution 与 completeness 声明。
- eligible unit：某 claim 对 denominator 的贡献，可为 0、1 或区间比例。

### 3.2 数据流

    RunManifest + accepted StageRecord
                 |
                 v
    base ViewManifest ---- judge completeness overlay
                 |                 |
                 +-------> effective manifest
                                  |
    typed GT v3 -> GT-to-Va adapter + score view bindings
          |                       |
          +-----------> reference Va ledgers
          |
    product output -> typed observations -> product Va ledgers
          |                       |
          +------ deterministic matching
                                  |
                   per-claim denominator/results
                                  |
                  policy + sidecar v8 + grade PNG

任何 identity、capability 或 totality gate 失败都在进入下游几何评分前停止。最前置 identity 尚未构造成功时直接返回 machine REJECTED，不写可缓存 sidecar/PNG；identity 已验证后的下游 REJECTED 才可写错误信息板。REJECTED 不画误导性红绿 grade；顶层 NA 只画带原因的灰色信息板。

## 4. Capability matrix 与顶层结果

### 4.1 Capability key

dispatch key 必须至少由下列字段组成：

    (
        gt_schema,
        gt_profile,
        product_stage,
        product_schema,
        view_manifest_schema,
        completeness_ruleset,
        reference_va_schema,
        segment_geometry_capability,
    )

禁止只按文件是否存在或 Python 类型猜路径。

### 4.2 冻结矩阵

| GT | 产品 | 结果路径 | 裁决 |
|---|---|---|---|
| v2 | reading 现役 schema | legacy reading | 精确保持现役 |
| v2 | correction v1/v2/v3 可被现役 adapter 接受 | legacy correction/elevation | 精确保持现役 |
| v3 C2 | reading + 完整 score bindings | B4b C2 reading | 可计分 |
| v3 C2 | correction v3 + 合法 segment 集 | B4b C2 correction | 可计分 |
| v3 | correction v1/v2 | 顶层 NA | <code>unsupported_product_schema</code> |
| v3 | 未知/未支持 GT profile | 顶层 NA | <code>unsupported_gt_profile</code> |
| v3 | door 或未支持 opening kind 的相关 row | 逐 claim NA | <code>unsupported_target_kind</code> |
| v3 | appearance claim | 逐 claim NA | <code>reference_value_unavailable</code> |
| v3 | host 有 plan applicability 且产品 segment+zone 可唯一解析 | B4b C2 host | judge-only 关系计分，不写回 |
| v3 | host 的产品 segment/zone 歧义 | REJECTED | <code>score_product_segment_unresolved</code> |
| 任意 | identity/hash/schema 非法 | REJECTED | 对应稳定错误码 |
| v3 | view binding/direction/segment 解析歧义 | REJECTED | 禁止 fallback |
| v3 | Va totality 或 denominator conservation 失败 | REJECTED | 禁止部分 sidecar |

顶层 NA 表示输入组合合法但本批不具备评分能力；REJECTED 表示输入或内部合同不合法。两者都不得伪装成 0 分。

## 5. 稳定常量、错误码与 gate id

### 5.1 版本常量

    SCORER_SCHEMA = "8"
    SCORE_SIDECAR_SCHEMA = "8"
    JUDGE_SCORE_CONFIG_SCHEMA = "1"
    JUDGE_SCORE_BINDINGS_SCHEMA = "1"
    JUDGE_COMPLETENESS_OVERLAY_SCHEMA = "1"
    SEGMENT_SCORER_HELPER_VERSION = "b4b_segment_score_v1"
    GT_TO_VA_ADAPTER_VERSION = "b4b_gt_to_va_v1"
    DENOMINATOR_HELPER_VERSION = "b4b_denominator_v1"
    GRADE_RENDERER_VERSION = "b4b_grade_png_v1"

Va 与 Vg helper version 必须从各自公开常量读取并写入 identity；不得在 B4b 复制一个看似相同的版本字符串。

### 5.2 稳定错误码

- <code>score_gt_identity_invalid</code>
- <code>score_product_identity_invalid</code>
- <code>score_view_manifest_invalid</code>
- <code>score_view_binding_invalid</code>
- <code>score_direction_unresolved</code>
- <code>score_completeness_input_invalid</code>
- <code>score_visibility_adapter_mismatch</code>
- <code>score_product_segment_unresolved</code>
- <code>score_claim_applicability_invalid</code>
- <code>score_match_ambiguous</code>
- <code>score_denominator_nonconserving</code>
- <code>score_sidecar_invalid</code>
- <code>score_unsupported_combination</code>
- <code>score_atomic_write_failed</code>

被调用的 B4a/Va 公共 API 若抛其冻结错误，B4b sidecar 的 <code>cause_code</code> 原样保存；B4b 对外 error code 使用上列稳定分类，不改写上游原始码。

### 5.3 gate id

- <code>scoring.input_identity</code>
- <code>scoring.capability</code>
- <code>scoring.view_bindings</code>
- <code>scoring.completeness</code>
- <code>scoring.applicability</code>
- <code>scoring.matching</code>
- <code>scoring.denominator_totality</code>
- <code>scoring.sidecar_identity</code>
- <code>scoring.render_totality</code>

gate 结果是 <code>pass | not_applicable | reject</code>，每个非 pass 都必须带稳定 reason/error code 与确定性 detail。

## 6. Strict wire contracts

本节是施工必须照抄的公开 wire。所有模型使用 Pydantic v2、<code>extra="forbid"</code>、strict 标量、有限浮点与显式 discriminated union。JSON canonicalization 一律为 UTF-8、sorted keys、compact separators、禁止 NaN/Infinity，随后 SHA-256 小写十六进制。

### 6.0 只读上游输入投影

B4b 不复制上游模型，但施工者只需以下冻结投影即可定位全部消费字段：

- <code>GroundTruthV3</code>：integer <code>schema_version=3</code>、case、<code>geometry_profile="c2_simple_orthogonal_no_holes"</code>、<code>coordinate_frame="building_axis_world_m"</code>、verification、generator、sources、nullable north axis、floors、openings、content hash。
- source document/view：source id/content hash；view id、<code>plan|elevation</code>、非空 floor ids、nullable projection surface key/facade family/view kind/world-along coverage/direction semantics/azimuth。
- floor：immutable id、z、ceiling height、actual footprint、fingerprint、非空 zones、开放数量 boundary segments。
- zone：id/role/actual polygon/非空 source refs。
- boundary segment：id/floor/exterior/family/p1/p2/normal/world-along/depth/Vg-derived visible intervals/fingerprint/0..N projection keys/nullable thickness/source refs。
- opening：id、<code>window|door</code>、floor、nullable host zone（当前 C2 必非空）、boundary segment、world-along、nullable z、非空 source refs。
- entity ref：source id、view id、entity handle、nullable subentity index、role Literal；B4b 只按 source/view/role 建证据，不读 DXF 路径。
- generator：extractor/validator/Vg hashes、manifest/judge/Vg config hashes，以及存档的 GT+Vg tolerances。B4b 重验 GT 派生几何时只用这些存档值，不读当前 tooling config。

Va 输入/输出直接 import 现役 strict public 类型：<code>FacadeVisibilityLedgerV1</code>、<code>ElevationViewBindingV1</code>、<code>OpeningClaimsV1</code>、<code>OpeningApplicabilityLedgerV1</code>；claim order、status/reason、半开区间、source decisions 和 hash preimage 均不在 B4b fork。correction v3 直接 import <code>CorrectedGeometryV3</code> 的 floor footprint/cells、facade segments、windows、provenance 和 feature-state identity；reading raw payload只在 §6.8 normalizer 边界出现。

### 6.1 基础别名

    from typing import Annotated, Literal
    from pydantic import (
        BaseModel,
        ConfigDict,
        Field,
        JsonValue,
        StrictBool,
        StrictStr,
        StringConstraints,
    )

    FiniteFloat = Annotated[
        float,
        Field(strict=True, allow_inf_nan=False),
    ]
    NonNegativeFloat = Annotated[
        float,
        Field(strict=True, ge=0.0, allow_inf_nan=False),
    ]
    PositiveFloat = Annotated[
        float,
        Field(strict=True, gt=0.0, allow_inf_nan=False),
    ]
    UnitFloat = Annotated[
        float,
        Field(strict=True, ge=0.0, le=1.0, allow_inf_nan=False),
    ]
    NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
    PositiveInt = Annotated[int, Field(strict=True, ge=1)]
    Hex64 = Annotated[
        StrictStr,
        StringConstraints(pattern=r"^[0-9a-f]{64}$"),
    ]
    StableId = Annotated[
        StrictStr,
        StringConstraints(min_length=1, max_length=256),
    ]
    ClaimName = Literal[
        "existence",
        "host",
        "along",
        "width",
        "sill",
        "head",
        "appearance",
    ]
    CardinalFamily = Literal["North", "South", "East", "West"]
    ViewKind = Literal["plan", "elevation"]

    class StrictWire(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

### 6.2 Judge score config

文件路径固定为 <code>src/configs/judge_score.yaml</code>。B4b 代码不能从 <code>correction.yaml</code>、环境变量或 <code>GradeConfig</code> 为 v3 填默认值。

    class JudgeScoreConfigV1(StrictWire):
        schema_version: Literal["1"]
        plan_axis_alignment_tol_m: PositiveFloat
        plan_position_tol_m: PositiveFloat
        plan_extent_tol_m: PositiveFloat
        claim_complete_epsilon_m: PositiveFloat
        opening_match_center_tol_m: PositiveFloat
        opening_assignment_tie_epsilon: PositiveFloat
        along_claim_tol_m: PositiveFloat
        width_claim_tol_m: PositiveFloat
        sill_claim_tol_m: PositiveFloat
        head_claim_tol_m: PositiveFloat
        floor_line_tol_m: PositiveFloat

建议 v1 值如下，并在实施时登记进 A0：

    schema_version: "1"
    plan_axis_alignment_tol_m: 0.05
    plan_position_tol_m: 0.30
    plan_extent_tol_m: 0.30
    claim_complete_epsilon_m: 0.05
    opening_match_center_tol_m: 0.40
    opening_assignment_tie_epsilon: 1.0e-9
    along_claim_tol_m: 0.40
    width_claim_tol_m: 0.40
    sill_claim_tol_m: 0.30
    head_claim_tol_m: 0.30
    floor_line_tol_m: 0.30

额外校验：

- <code>claim_complete_epsilon_m</code> 小于等于每个 claim tolerance；
- tie epsilon 小于每个几何 tolerance；
- config canonical content hash 写入 sidecar；
- config 文件缺失或多字段直接 <code>score_gt_identity_invalid</code>，不得内置 fallback。

### 6.3 Judge score view bindings

建议资产路径为每个 GT v3 case bundle 下 <code>score_inputs/view_bindings.json</code>。它是 judge-only reviewed input，不进入 production output，也不由产品生成。

    class PlanScoreViewBindingV1(StrictWire):
        kind: Literal["plan"]
        input_id: StableId
        floor_id: StableId
        gt_source_view_ids: tuple[StableId, ...]

    class ElevationScoreViewBindingV1(StrictWire):
        kind: Literal["elevation"]
        input_id: StableId
        floor_ids: tuple[StableId, ...]
        facade_family: CardinalFamily
        gt_source_view_ids: tuple[StableId, ...]
        resolved_building_direction: CardinalFamily
        resolution_source: Literal[
            "manifest_building_axis",
            "resolved_direction_sidecar",
        ]
        orientation_output_hash: Hex64 | None
        adapter_version: StableId | None
        source_footprint_fingerprint: Hex64
        world_axis: Literal["x", "y"]
        sign: Literal[-1, 1]
        along_origin: FiniteFloat
        mirrored: StrictBool
        local_x_positive: Literal[
            "image_left_to_right",
            "image_right_to_left",
        ]
        frame_transform_sha256: Hex64

    ScoreViewBindingV1 = Annotated[
        PlanScoreViewBindingV1 | ElevationScoreViewBindingV1,
        Field(discriminator="kind"),
    ]

    class JudgeScoreViewBindingsV1(StrictWire):
        schema_version: Literal["1"]
        case_id: StableId
        gt_content_sha256: Hex64
        case_metadata_sha256: Hex64
        base_view_manifest_sha256: Hex64
        bindings: tuple[ScoreViewBindingV1, ...]
        content_sha256: Hex64

校验合同：

1. <code>content_sha256</code> 的 preimage 是该对象删除自身字段后的 canonical JSON。
2. 每个 base manifest required plan/elevation input 恰有一个 binding；多、少、重复均拒绝。
3. plan 的 floor、elevation 的 canonical 非空/唯一 floor-id 集与 facade 必须在 typed GT 与 manifest 中同时存在；同一 elevation 可覆盖多层，不得拆成固定“一层一图”。
4. 每个 <code>gt_source_view_id</code> 必须被对应 GT segment/opening 的 source refs 实际引用，且 kind/floor/facade 一致。
5. 标准 building-axis direction 必须使用 <code>resolution_source="manifest_building_axis"</code> 且 orientation hash/adapter 均为 null；true/unknown 必须使用 <code>resolved_direction_sidecar</code>，orientation hash 与 adapter version 均非空。
6. <code>mirrored</code> 与 <code>local_x_positive</code> 只来自此受信文件；产品输出中的同名字段只可作一致性审计，不能驱动 denominator。
7. 空 <code>gt_source_view_ids</code> 拒绝；不得用“所有 view”兜底。
8. 调 Va 前由 adapter 逐字段复制 frame，并设置 public <code>ElevationViewBindingV1.view_manifest_sha256 = effective_manifest.content_sha256</code>。B4b Phase A 实施批必须先把下列 <code>frame_transform_sha256</code> preimage 按 VA-C3 同款登记进 A0，再允许 scorer 独立重算：

        {
            "schema": "view_projection_binding_v1",
            "input_id": binding.input_id,
            "resolved_building_direction": binding.resolved_building_direction,
            "source_footprint_fingerprint": binding.source_footprint_fingerprint,
            "world_axis": binding.world_axis,
            "sign": binding.sign,
            "along_origin": binding.along_origin,
            "mirrored": binding.mirrored,
            "local_x_positive": binding.local_x_positive,
        }

   preimage 只含上列九个键，缺一、多一或改名都不兼容；尤其不含 manifest hash、resolution source、orientation output hash、adapter version、floor/facade scope 或 GT source refs。序列化口径固定为 Pydantic JSON 标量、sorted keys、compact separators、<code>ensure_ascii=False</code>、UTF-8，再作小写 SHA-256。B4b 不 import Va 私有 <code>_frame_hash</code>；独立结果必须与 score input 声明相同。overlay 变化只改变 effective-manifest identity，不改变此受信 frame preimage/hash。

### 6.4 User/dataset completeness overlay

候选/注册路径：

- case-owned human declaration：<code>score_inputs/completeness.json</code>；
- dataset registry：<code>case_tests/test_baseline/judge_datasets/completeness/&lt;dataset_id&gt;/&lt;version&gt;/...</code>；
- builder：<code>scripts/tool_scripts/build_judge_score_inputs.py</code>，输出只能在候选目录或临时目录，不能直接写 protected GT/golden root。

    class PlanFullFloorCoverageV1(StrictWire):
        kind: Literal["full_floor"]
        floor_id: StableId

    class ElevationFullFacadeCoverageV1(StrictWire):
        kind: Literal["full_facade"]
        floor_ids: tuple[StableId, ...]
        facade_family: CardinalFamily

    CompletenessCoverageV1 = Annotated[
        PlanFullFloorCoverageV1 | ElevationFullFacadeCoverageV1,
        Field(discriminator="kind"),
    ]

    class UserDeclarationBodyV1(StrictWire):
        input_id: StableId
        assertion_id: StableId
        negative_claims: tuple[ClaimName, ...]
        coverage: CompletenessCoverageV1
        asserted_by: StableId
        assertion_revision: PositiveInt

    class UserCompletenessDeclarationV1(StrictWire):
        source: Literal["user"]
        body: UserDeclarationBodyV1
        body_sha256: Hex64

    class DatasetDeclarationBodyV1(StrictWire):
        input_id: StableId
        assertion_id: StableId
        negative_claims: tuple[ClaimName, ...]
        coverage: CompletenessCoverageV1
        dataset_id: StableId
        dataset_version: StableId
        contract_id: StableId

    class DatasetCompletenessDeclarationV1(StrictWire):
        source: Literal["dataset_ref"]
        body: DatasetDeclarationBodyV1
        body_sha256: Hex64

    CompletenessDeclarationV1 = Annotated[
        UserCompletenessDeclarationV1 | DatasetCompletenessDeclarationV1,
        Field(discriminator="source"),
    ]

    class JudgeCompletenessOverlayV1(StrictWire):
        schema_version: Literal["1"]
        case_id: StableId
        gt_content_sha256: Hex64
        base_view_manifest_sha256: Hex64
        declarations: tuple[CompletenessDeclarationV1, ...]
        content_sha256: Hex64

映射到现役 B-M wire：

- user 映射为 <code>UserSourceRef(source="user", content_sha256=body_sha256)</code>；
- dataset 映射为 <code>DatasetSourceRef(source="dataset_ref", dataset_id, dataset_version, contract_id, content_sha256=body_sha256)</code>；
- declaration scope 经 input binding 验证后映为现役 <code>Coverage(frame="plan_floor_region", region="full_floor")</code> 或 <code>Coverage(frame="elevation_local_along", region="full_facade")</code>；negative claims 与 assertion id 原样进入该 view 的 <code>OpeningEvidence</code>；
- <code>body_sha256</code> 是 body canonical JSON 的 hash；overlay <code>content_sha256</code> 是删除自身字段后的整文件 hash。

合并规则：

1. 每个 input 最多一个 completeness source，因为现役 <code>OpeningEvidenceV1</code> 每 view 只容纳一个 assertion。
2. base manifest 已有 case-metadata assertion 时，overlay 默认拒绝；只有 assertion id、coverage、negative claims 与 source ref 全部一致的幂等重复可接受。
3. overlay input 必须存在且 coverage 与 view kind/floor/facade 完全一致。
4. <code>negative_claims</code> 必须非空、按冻结 claim order 去重 canonical，并是该 view 的 <code>potentially_observable_claims</code> 子集。
5. effective manifest 是纯函数结果，写入 sidecar hash；不得覆盖 base manifest 文件或 RunManifest 中的 base hash。
6. dataset declaration 必须能在只读 registry 中按四元组和 body hash 唯一解析；user declaration 必须是 case review 批次显式批准的内容。
7. 没有 completeness 不是错误，只表示不能据此把未匹配产品 opening 判为 extra。
8. declaration 是 case/GT-owned trust input，刻意不随 attempt 复制；每次评分通过 sidecar 中的 overlay/effective-manifest hash 与 <code>ProductIdentityV8(stage, attempt, output, accepted record)</code> 重新绑定。这样复用受审声明但不能跨 case、GT 或 attempt 偷换。

### 6.5 Identity 与 capability wire

    class GtIdentityV8(StrictWire):
        path_id: StableId
        file_sha256: Hex64
        content_sha256: Hex64
        schema_version: Literal[2, 3]
        profile: StableId | None
        coordinate_frame: StableId | None
        verification_status: Literal["candidate", "human_verified"] | None
        loader_helper_version: StableId

    class ProductIdentityV8(StrictWire):
        stage: Literal["reading", "correction"]
        attempt: NonNegativeInt
        output_sha256: Hex64
        output_schema: StableId
        accepted: StrictBool
        accepted_stage_record_sha256: Hex64 | None
        source: StableId

    class ManifestIdentityV8(StrictWire):
        base_view_manifest_sha256: Hex64
        effective_view_manifest_sha256: Hex64
        case_metadata_sha256: Hex64
        completeness_ruleset: StableId
        completeness_overlay_sha256: Hex64 | None
        score_view_bindings_sha256: Hex64 | None

    class HelperIdentityV8(StrictWire):
        scorer_schema: Literal["8"]
        segment_scorer: Literal["b4b_segment_score_v1"]
        gt_to_va_adapter: Literal["b4b_gt_to_va_v1"]
        denominator_helper: Literal["b4b_denominator_v1"]
        grade_renderer: Literal["b4b_grade_png_v1"]
        va_helper: StableId
        vg_helper: StableId
        claims_contract: StableId

    class CapabilityDecisionV8(StrictWire):
        path: Literal["legacy_v2", "c2_v3", "not_applicable", "rejected"]
        capability_key: tuple[StableId, ...]
        reason: StableId | None
        gate_id: StableId

    class LegacyGradeTolerancesV8(StrictWire):
        wall_tol_m: NonNegativeFloat
        window_centre_tol_m: NonNegativeFloat
        elevation_along_tol_m: NonNegativeFloat
        sill_tol_m: NonNegativeFloat
        head_tol_m: NonNegativeFloat
        width_tol_m: NonNegativeFloat
        position_tol_m: NonNegativeFloat
        extent_tol_m: NonNegativeFloat
        complete_eps_m: NonNegativeFloat
        overlap_accept: UnitFloat
        overlap_complete: UnitFloat
        floor_line_tol_m: NonNegativeFloat

    class LegacyToleranceIdentityV8(StrictWire):
        profile_kind: Literal["legacy_grade_config"]
        values: LegacyGradeTolerancesV8
        content_sha256: Hex64

    class C2ToleranceIdentityV8(StrictWire):
        profile_kind: Literal["judge_score_config_v1"]
        values: JudgeScoreConfigV1
        content_sha256: Hex64

    ToleranceIdentityV8 = Annotated[
        LegacyToleranceIdentityV8 | C2ToleranceIdentityV8,
        Field(discriminator="profile_kind"),
    ]

    class ScoreIdentityV8(StrictWire):
        gt: GtIdentityV8
        product: ProductIdentityV8
        manifest: ManifestIdentityV8
        helpers: HelperIdentityV8
        capability: CapabilityDecisionV8
        tolerances: ToleranceIdentityV8
        reference_applicability_sha256: Hex64 | None
        product_applicability_sha256: Hex64 | None
        absence_applicability_sha256: Hex64 | None

<code>accepted_stage_record_sha256</code> 的 preimage 是 accepted StageRecord 的 canonical model dump；未 accepted 时必须为 null。之后同一 attempt 被接受会改变 identity 并触发重算。

legacy identity 使用当前 <code>GradeConfig.as_tolerances()</code> 的十二字段 canonical hash；C2 identity 使用完整 <code>JudgeScoreConfigV1</code> 与文件 hash。两条路径不得混用：legacy 行为继续由现役 run config 驱动，v3 绝不读取 <code>correction.yaml</code> 或 legacy <code>GradeConfig</code>。

### 6.6 Per-claim score wire

    class IntervalV1(StrictWire):
        lo: FiniteFloat
        hi: FiniteFloat

    class ClaimApplicabilityRefV8(StrictWire):
        ledger_content_sha256: Hex64
        opening_id: StableId
        claim: ClaimName
        target_world_interval: IntervalV1
        status: Literal["applicable", "partially_applicable", "not_applicable"]
        reason: Literal[
            "full_observable_coverage",
            "existence_observable_fragment",
            "partial_observable_coverage",
            "unobserved",
        ]
        applicable_intervals: tuple[IntervalV1, ...]
        unobserved_intervals: tuple[IntervalV1, ...]
        considered_source_view_ids: tuple[StableId, ...]
        supporting_source_view_ids: tuple[StableId, ...]
        facade_segment_ids: tuple[StableId, ...]

    class ClaimValueErrorV8(StrictWire):
        metric: Literal[
            "binary",
            "masked_interval_endpoint",
            "masked_interval_length",
            "scalar_absolute",
        ]
        value: NonNegativeFloat | None
        tolerance: NonNegativeFloat | None

    class KnowledgeRefAuditV8(StrictWire):
        dataset_id: StableId
        dataset_version: StableId
        entry_id: StableId
        candidate_id: StableId
        content_sha256: Hex64

    class ClaimProvenanceAuditV8(StrictWire):
        claim: ClaimName
        provenance: Literal["observed", "derived", "assumed"]
        source_ids: tuple[StableId, ...]
        method: StableId | None
        knowledge_ref: KnowledgeRefAuditV8 | None

    class ClaimOutcomeSliceV8(StrictWire):
        slice_id: StableId
        applicable_intervals: tuple[IntervalV1, ...]
        units: UnitFloat
        result: Literal[
            "complete",
            "within_tolerance",
            "miss",
            "conflict",
        ]
        error: ClaimValueErrorV8
        evidence_source_ids: tuple[StableId, ...]

    class ClaimScoreRowV8(StrictWire):
        target_id: StableId
        target_kind: Literal["window", "door"]
        claim: ClaimName
        applicability: ClaimApplicabilityRefV8
        eligible_units: UnitFloat
        result: Literal[
            "complete",
            "within_tolerance",
            "miss",
            "conflict",
            "not_applicable",
        ]
        na_reason: StableId | None
        outcome_slices: tuple[ClaimOutcomeSliceV8, ...]
        matched_observation_ids: tuple[StableId, ...]
        evidence_source_ids: tuple[StableId, ...]
        product_provenance: tuple[ClaimProvenanceAuditV8, ...]

    class ClaimSummaryV8(StrictWire):
        claim: ClaimName
        target_count: NonNegativeInt
        eligible_target_count: NonNegativeInt
        partial_target_count: NonNegativeInt
        denominator_units: NonNegativeFloat
        complete_units: NonNegativeFloat
        within_tolerance_units: NonNegativeFloat
        miss_units: NonNegativeFloat
        conflict_units: NonNegativeFloat
        not_applicable_target_count: NonNegativeInt
        na_reasons: dict[StableId, NonNegativeInt]

    class ExtraObservationV8(StrictWire):
        observation_id: StableId
        target_kind: Literal["window", "door"]
        status: Literal["extra", "not_applicable"]
        reason: StableId
        absence_ledger_content_sha256: Hex64 | None
        observed_intervals: tuple[IntervalV1, ...]
        trusted_negative_intervals: tuple[IntervalV1, ...]

    class Point2V8(StrictWire):
        x: FiniteFloat
        y: FiniteFloat

    class SegmentScoreRowV8(StrictWire):
        target_id: StableId
        floor_id: StableId
        segment_kind: Literal[
            "exterior_boundary",
            "interior_partition",
            "floor_line",
        ]
        target_p1: Point2V8
        target_p2: Point2V8
        result: Literal["complete", "within_tolerance", "miss"]
        eligible_units: Literal[1.0]
        position_error_m: NonNegativeFloat | None
        extent_error_m: NonNegativeFloat | None
        matched_observation_ids: tuple[StableId, ...]
        evidence_source_ids: tuple[StableId, ...]

    class SegmentExtraV8(StrictWire):
        observation_id: StableId
        floor_id: StableId
        segment_kind: Literal["exterior_boundary", "interior_partition"]
        result: Literal["extra", "not_applicable"]
        reason: StableId
        evidence_source_ids: tuple[StableId, ...]

    class ScoreCriterionV8(StrictWire):
        criterion_id: Literal[
            "walls_complete",
            "boundary_complete",
            "windows_placed",
            "window_plan_geometry",
            "window_elevation_geometry",
            "floor_lines_complete",
            "no_oversplit",
            "negative_evidence_complete",
        ]
        eligible: StrictBool
        denominator_units: NonNegativeFloat
        passing_units: NonNegativeFloat
        failing_units: NonNegativeFloat
        na_reasons: dict[StableId, NonNegativeInt]
        verdict: Literal[
            "pass",
            "fail",
            "not_applicable",
            "insufficient_evidence",
        ]

模型 validator 还必须冻结：

- <code>IntervalV1.lo &lt; hi</code>，tuple canonical sorted、无重叠/相接未合并项；
- applicability status/reason 严格采用 Va 的四行唯一映射，且 applicable 与 unobserved 两组恰好分割 target interval；
- 每个 opening 的 claim rows 恰七条且按 <code>CLAIM_ORDER</code>，target/claim/ledger 引用存在且唯一；
- <code>eligible_units</code> 位于 [0,1]；result 为 <code>not_applicable</code> 当且仅当 units 为 0、<code>na_reason</code> 非空且 outcome slices 为空；
- 非 NA row 的 units 大于 0、na reason 为 null，slice units 之和等于 eligible units；每个 slice 按 claim 限制 metric，row result 是 <code>conflict &gt; miss &gt; within_tolerance &gt; complete</code> 的最坏非零 slice；
- provenance rows 按 <code>CLAIM_ORDER</code>、claim 唯一；assumed 必须带完整五元组 knowledge ref，observed/derived 禁带 knowledge ref。provenance 只审计，不改变 reference applicability、units 或 PNG score 色；
- count 非负，summary 的 target 分区与 row 重算完全一致；
- criterion 的 passing + failing 等于 denominator；eligible=false 当且仅当 denominator 为 0 且 verdict 为 not_applicable。

上位文案 <code>NOT_APPLICABLE(unobserved)</code> 在 JSON 中精确落为 <code>result="not_applicable"</code>、<code>na_reason="unobserved"</code>、<code>eligible_units=0.0</code>、空 outcome slices；大写形式仅是 UI 标签。

每个 summary 必须满足：

    denominator_units
      == complete_units
       + within_tolerance_units
       + miss_units
       + conflict_units

比较采用 config tie epsilon；序列化前把绝对值小于等于 tie epsilon 的残差归零。仍不守恒则 <code>score_denominator_nonconserving</code>，不写部分 sidecar。

### 6.7 顶层 sidecar v8

Va ledger 在 v8 中直接使用已收录 public strict type，不复制一个近似 wire：

    from src.agent.correction.facade_applicability import (
        OpeningApplicabilityLedgerV1,
    )

    class LegacyScoredPayloadV8(StrictWire):
        kind: Literal["legacy_scored"]
        legacy_contract: Literal["score_sidecar_v7_projection"]
        legacy_payload_sha256: Hex64
        legacy_payload: JsonValue

    class C2ScoredPayloadV8(StrictWire):
        kind: Literal["c2_scored"]
        segment_rows: tuple[SegmentScoreRowV8, ...]
        segment_extras: tuple[SegmentExtraV8, ...]
        claim_rows: tuple[ClaimScoreRowV8, ...]
        claim_summaries: tuple[ClaimSummaryV8, ...]
        extras: tuple[ExtraObservationV8, ...]
        score_criteria: tuple[ScoreCriterionV8, ...]
        reference_applicability_ledgers: tuple[
            OpeningApplicabilityLedgerV1, ...
        ]
        product_applicability_ledgers: tuple[
            OpeningApplicabilityLedgerV1, ...
        ]
        absence_applicability_ledgers: tuple[
            OpeningApplicabilityLedgerV1, ...
        ]

    class NotApplicablePayloadV8(StrictWire):
        kind: Literal["not_applicable"]
        reason: Literal[
            "unsupported_product_schema",
            "unsupported_gt_profile",
            "unsupported_view_contract",
            "no_supported_targets",
        ]
        detail: StrictStr

    class RejectedPayloadV8(StrictWire):
        kind: Literal["rejected"]
        error_code: StableId
        cause_code: StableId | None
        gate_id: StableId
        detail: StrictStr

    ScorePayloadV8 = Annotated[
        LegacyScoredPayloadV8
        | C2ScoredPayloadV8
        | NotApplicablePayloadV8
        | RejectedPayloadV8,
        Field(discriminator="kind"),
    ]

    class EmbeddedLedgerContractV1(StrictWire):
        ledger_kind: Literal["reference", "product", "absence"]
        ledger_count: NonNegativeInt
        aggregate_sha256: Hex64

    class ScoreArtifactContractV1(StrictWire):
        contract_version: Literal["1"]
        output_sha256: Hex64
        sidecar_schema_version: Literal["8"]
        grade_kind: Literal[
            "legacy_grade",
            "c2_grade",
            "not_applicable_board",
            "rejected_board",
        ]
        grade_png_sha256: Hex64
        embedded_ledgers: tuple[EmbeddedLedgerContractV1, ...]

    class ScoreSidecarV8(StrictWire):
        schema_version: Literal["8"]
        identity: ScoreIdentityV8
        artifact_contract: ScoreArtifactContractV1
        payload: ScorePayloadV8
        content_sha256: Hex64

<code>JsonValue</code> 只用于 legacy v7 opaque projection，不得用于新增 C2 row 或 ledger。legacy payload 是现役 v7 serializer 的 canonical JSON 投影，目的仅为 byte/semantic regression；v3 renderer 不得读取它。

sidecar <code>content_sha256</code> 是删除自身字段后的 canonical JSON hash。所有嵌入 ledger 先由 Va strict model 重新校验，且各自 content hash 与 identity/row 引用一致。Va 已在每个 ledger 内按 floor/segment/opening canonical 排序；每类 ledger tuple 再按 <code>content_sha256</code> 排序，aggregate hash 的 preimage 是该有序 content-hash JSON 数组，零 ledger 使用空数组 hash。artifact contract 是 Va 移交所要求的 judge-side artifact 扩展，内嵌 sidecar 且不修改 production <code>RunManifestV2.ArtifactKey</code>。

顶层 model validator 还须断言 artifact output hash 等于 identity product hash、grade kind 与 payload kind 唯一对应、三类 aggregate 与 identity/payload 三方相等，且 ledger contract 固定按 reference/product/absence 顺序恰三项；cache loader/finalizer 另以实际 PNG bytes 验 grade hash。legacy/NA/REJECTED 的三项均为零 ledger 空数组 hash。

### 6.8 规范化输入与公开函数签名

v3 scorer 先把 reading/correction 转为同一 strict judge-only observation wire。raw JSON 只能出现在 loader 边界，不能流入 geometry、Va 或 policy helper。

    class SegmentObservationV1(StrictWire):
        observation_id: StableId
        source_input_id: StableId
        floor_id: StableId
        segment_kind: Literal["exterior_boundary", "interior_partition"]
        p1: Point2V8
        p2: Point2V8
        adjacent_room_ids: tuple[StableId, ...]

    class OpeningObservationV1(StrictWire):
        observation_id: StableId
        source_input_id: StableId
        channel: Literal["plan", "elevation"]
        floor_id: StableId
        kind: Literal["window", "door"]
        facade_family: CardinalFamily
        world_along_interval: IntervalV1
        z_interval: IntervalV1 | None
        declared_room_id: StableId | None
        declared_facade_segment_id: StableId | None
        provenance: tuple[ClaimProvenanceAuditV8, ...]

    class FloorLineObservationV1(StrictWire):
        observation_id: StableId
        source_input_id: StableId
        floor_id: StableId
        z_world_m: FiniteFloat

    class NormalizedProductEvidenceV1(StrictWire):
        stage: Literal["reading", "correction"]
        product_schema: StableId
        output_sha256: Hex64
        segments: tuple[SegmentObservationV1, ...]
        openings: tuple[OpeningObservationV1, ...]
        floor_lines: tuple[FloorLineObservationV1, ...]

    class SegmentAssignmentV1(StrictWire):
        target_segment_id: StableId
        observation_ids: tuple[StableId, ...]
        method: Literal[
            "global_axis_overlap_assignment",
            "temporary_unique_span_binding",
        ]

以下签名冻结；实现可增加下划线 private helper，不得另造第二套 public scorer：

    def load_score_gt_identity(
        path: Path | str,
    ) -> tuple[GtIdentityV8, GtDocument | None]: ...

    def load_judge_score_config(
        path: Path | str,
    ) -> JudgeScoreConfigV1: ...

    def load_score_view_bindings(
        path: Path | str,
        *,
        expected_case_id: str,
        expected_gt_content_sha256: str,
        expected_case_metadata_sha256: str,
        expected_base_view_manifest_sha256: str,
    ) -> JudgeScoreViewBindingsV1: ...

    def load_completeness_overlay(
        path: Path | str | None,
        *,
        expected_case_id: str,
        expected_gt_content_sha256: str,
        expected_base_view_manifest_sha256: str,
    ) -> JudgeCompletenessOverlayV1 | None: ...

    def build_effective_view_manifest(
        *,
        base: ViewManifest,
        overlay: JudgeCompletenessOverlayV1 | None,
    ) -> ViewManifest: ...

    def materialize_va_elevation_bindings(
        *,
        score_bindings: JudgeScoreViewBindingsV1,
        effective_manifest: ViewManifest,
    ) -> tuple[ElevationViewBindingV1, ...]: ...

    def adapt_gt_v3_to_va_visibility(
        gt: GroundTruthV3,
    ) -> FacadeVisibilityLedgerV1: ...

    def build_reference_opening_claims(
        *,
        gt: GroundTruthV3,
        score_bindings: JudgeScoreViewBindingsV1,
    ) -> tuple[OpeningClaimsV1, ...]: ...

    def derive_reference_applicability(
        *,
        visibility: FacadeVisibilityLedgerV1,
        manifest: ViewManifest,
        elevation_views: tuple[ElevationViewBindingV1, ...],
        claims: tuple[OpeningClaimsV1, ...],
    ) -> OpeningApplicabilityLedgerV1: ...

    def build_product_opening_claims(
        *,
        product: NormalizedProductEvidenceV1,
        score_bindings: JudgeScoreViewBindingsV1,
        segment_assignments: tuple[SegmentAssignmentV1, ...],
    ) -> tuple[OpeningClaimsV1, ...]: ...

    def derive_product_applicability(
        *,
        visibility: FacadeVisibilityLedgerV1,
        manifest: ViewManifest,
        elevation_views: tuple[ElevationViewBindingV1, ...],
        claims: tuple[OpeningClaimsV1, ...],
    ) -> OpeningApplicabilityLedgerV1: ...

    def build_absence_opening_claims(
        *,
        unmatched: tuple[OpeningObservationV1, ...],
        score_bindings: JudgeScoreViewBindingsV1,
        segment_assignments: tuple[SegmentAssignmentV1, ...],
    ) -> tuple[OpeningClaimsV1, ...]: ...

    def derive_absence_applicability(
        *,
        visibility: FacadeVisibilityLedgerV1,
        manifest: ViewManifest,
        elevation_views: tuple[ElevationViewBindingV1, ...],
        claims: tuple[OpeningClaimsV1, ...],
    ) -> OpeningApplicabilityLedgerV1: ...

    def normalize_reading_for_score(
        *,
        payload: JsonValue,
        output_sha256: str,
        manifest: ViewManifest,
        score_bindings: JudgeScoreViewBindingsV1,
    ) -> NormalizedProductEvidenceV1: ...

    def normalize_correction_for_score(
        *,
        payload: CorrectedGeometryV3,
        output_sha256: str,
        manifest: ViewManifest,
        score_bindings: JudgeScoreViewBindingsV1,
    ) -> NormalizedProductEvidenceV1: ...

    def score_plan_segments(
        *,
        gt: GroundTruthV3,
        product: NormalizedProductEvidenceV1,
        config: JudgeScoreConfigV1,
    ) -> tuple[
        tuple[SegmentScoreRowV8, ...],
        tuple[SegmentExtraV8, ...],
        tuple[SegmentAssignmentV1, ...],
    ]: ...

    def score_opening_claims(
        *,
        gt: GroundTruthV3,
        product: NormalizedProductEvidenceV1,
        reference_ledger: OpeningApplicabilityLedgerV1,
        product_ledger: OpeningApplicabilityLedgerV1,
        effective_manifest: ViewManifest,
        segment_assignments: tuple[SegmentAssignmentV1, ...],
        config: JudgeScoreConfigV1,
    ) -> tuple[
        tuple[ClaimScoreRowV8, ...],
        tuple[ClaimSummaryV8, ...],
        tuple[ExtraObservationV8, ...],
        tuple[OpeningApplicabilityLedgerV1, ...],
    ]: ...

    def decide_score_capability(
        *,
        gt_identity: GtIdentityV8,
        stage: Literal["reading", "correction"],
        product_schema: str,
        view_manifest: ViewManifest,
    ) -> CapabilityDecisionV8: ...

    def score_attempt(
        *,
        gt_identity: GtIdentityV8,
        gt: GtDocument | None,
        product_payload: JsonValue,
        product_identity: ProductIdentityV8,
        run_manifest: RunManifestV2,
        accepted_stage_record: StageRecordV2 | None,
        base_view_manifest: ViewManifest,
        score_bindings: JudgeScoreViewBindingsV1 | None,
        completeness_overlay: JudgeCompletenessOverlayV1 | None,
        legacy_grade_config: GradeConfig | None,
        c2_config: JudgeScoreConfigV1 | None,
    ) -> tuple[ScoreIdentityV8, ScorePayloadV8]: ...

    def render_score_grade_png(
        *,
        gt: GtDocument | None,
        identity: ScoreIdentityV8,
        payload: ScorePayloadV8,
    ) -> bytes: ...

    def finalize_score_sidecar(
        *,
        identity: ScoreIdentityV8,
        payload: ScorePayloadV8,
        grade_png: bytes,
    ) -> ScoreSidecarV8: ...

    def load_cached_score(
        path: Path | str,
        *,
        grade_path: Path | str,
        expected_identity: ScoreIdentityV8,
    ) -> ScoreSidecarV8 | None: ...

    def commit_score_artifacts(
        *,
        sidecar_path: Path | str,
        grade_path: Path | str,
        sidecar: ScoreSidecarV8,
        grade_png: bytes,
    ) -> None: ...

上述类型的导入来源固定为：B4a public <code>GtDocument/GroundTruthV3</code>，现役 <code>ViewManifest</code>，<code>RunManifestV2/StageRecordV2</code>，现役 <code>GradeConfig</code>，correction <code>CorrectedGeometryV3</code>，以及 Va public <code>FacadeVisibilityLedgerV1/ElevationViewBindingV1/OpeningClaimsV1/OpeningApplicabilityLedgerV1</code>。legacy path 要求 GT document 与 legacy config 非空、C2 config 为空；C2 path 要求 GT document 与 C2 config 非空、legacy config 为空；合法 unsupported profile 的 NA path 可令 GT document 为空。任何上游实际符号漂移由 §14 对账裁决，不在实现中用 <code>Any</code> 或反射兜底。

所有 public 函数只抛一个 judge 边界异常 <code>ScoreContractError(code, gate_id, cause_code, context)</code>；<code>code</code> 只能取 §5.2，<code>gate_id</code> 只能取 §5.3，context 必须是 canonical JSON value 且不得含路径外泄或异常 repr。被调 B4a/Va 的冻结错误放入 cause code。

## 7. GT v3 与 Va 适配

### 7.1 Typed loader

- v2：沿现役 legacy loader/score path。
- v3：只调用 B4a 公共 <code>load_gt_document()</code> 或 <code>load_gt_file()</code>。
- 禁止对 v3 调用 legacy <code>load_gt()</code>；B4a 规定的 <code>gt_v3_requires_typed_consumer</code> 必须保持可见。
- scorer 接收的是 typed <code>GroundTruthV3</code>，内部不能再次读 raw dict。
- run-stage 正式评分只接受 <code>human_verified</code> v3；candidate 只可由显式 test/候选检查命令调用 typed file loader，不能产生可 promotion 的 score/grade。candidate 进入正式入口为 <code>score_gt_identity_invalid</code>。
- <code>load_score_gt_identity()</code> 先以文件 bytes 计算 file hash，再验证当前 schema 的 canonical content hash。schema 2/3 以外或 hash 无法验证直接 machine reject、无 sidecar；schema 3 envelope 合法但 profile 非 <code>c2_simple_orthogonal_no_holes</code> 时返回 identity + null document，供 capability 产顶层 NA，绝不把未知 profile 喂给几何 scorer。

### 7.2 GT-to-Va facade adapter

B4b 不直接信任 GT 中由 Vg 派生的 <code>visible_intervals</code>。适配步骤固定：

1. 用 GT footprint 与 B4a/A0 中冻结的 Vg tolerances 独立重跑公开 Vg。
2. 将 Vg 输出与 <code>GtBoundarySegmentV3</code> 按 floor、family、world endpoints、along interval 一一对应。
3. 零匹配、多匹配、遗漏或额外 segment 均 <code>score_visibility_adapter_mismatch</code>。
4. 成功后以 GT stable id 替换派生临时 id，构造 Va 公开 <code>FacadeSegment</code>。
5. adapter source 固定为 judge GT，写入 GT content hash、schema、Vg helper version 和 adapter version。
6. 以 A0 的 frozen preimage 独立计算 <code>facade_segments_sha256</code>；不得 import Va 私有 hash helper。
7. 将独立 hash 与 Va ledger identity 交叉验证。

preimage 精确为所有 public <code>FacadeSegment.model_dump(mode="json")</code> 的数组，排序键：

    (
        floor_id,
        {"North": 0, "South": 1, "East": 2, "West": 3}[facade_family],
        world_along_interval.lo,
        world_along_interval.hi,
        depth,
        id,
    )

随后对完整数组作 sorted-key compact UTF-8 JSON + SHA-256；不能只 hash id/interval 子集。

该重跑是“同一冻结算法的完整性校验”，不是第二份人工观察真值。真正的可观察性只由 verified GT source refs、受信 bindings 和 completeness 交给 Va 决定。

### 7.3 Reference ledger

对每个 GT window 建一个 <code>OpeningClaimsV1</code>：

- 恰有七 claim；
- plan source refs 可支持 existence/host/along/width；
- elevation source refs可支持 existence/along/width/sill/head/appearance；
- GT 的 z/sill/head 为 null 时，对应 claim 没有 reference value，最终 NA；
- source view id 必须经 score bindings 映射到 manifest input；
- 每个 claim target interval 使用 GT <code>world_along_interval</code>；
- 不得从产品输出或产品 provenance 增删 reference source。

positive evidence 区间构造写死如下。令 target 半开区间 <code>T=[t_lo,t_hi)</code>：

1. plan source：对允许的每个 claim 构造 <code>PlanClaimEvidenceV1.world_interval = T</code>，逐端点原样复制，不做 tolerance 扩张、visible clip 或 bbox 截断；Va 的 plan bypass 随后执行标准 <code>world_interval ∩ target</code>。
2. elevation source：只使用 §6.3 已验真的该 view frame。其 forward map 为 <code>world_along = along_origin + sign * local_x</code>，其中 mirror 与 local-x 方向已经由受信 frame 合成为合法 <code>sign ∈ {-1,+1}</code>。先逆映射 target 两端：

       u0 = (t_lo - along_origin) / sign
       u1 = (t_hi - along_origin) / sign
       ElevationClaimEvidenceV1.local_interval = [min(u0,u1), max(u0,u1))

   不再额外翻转或套用产品 mirror。Va 标准通道再做 local→world、升序、<code>∩ target</code>、<code>∩ target-segment visible_intervals</code>，产出最终 applicable/unobserved intervals。
3. 性质：上述 reference evidence 表示“假定该 source 图上完整可见此窗”的最大正证据，不表示整个 target 已可计分。真实可评分范围只由 Va 与 Vg-derived visible intervals 相交后收窄；B4b 不提前用 visible intervals 改写 evidence，也不把最大 evidence 直接当 denominator。
4. 性质测试：对 <code>sign=±1</code>、mirror 两态和 local-x 两态，逆映射所得 local 两端经同一受信 forward map 后取升序，必须精确恢复 T；随后人为切短 visible intervals，只能收窄 Va output，不能改变输入 evidence 或 target。

调用 Va 产生 reference ledger，保存完整 ledger、bindings、source decision 与 content hash。ledger 的七行 totality、区间覆盖、状态一致性失败均 <code>score_claim_applicability_invalid</code>。

### 7.4 Product ledger

产品 opening/declaration 按其实际 source、feature state 与 segment binding 构造独立 Va 输入。它的用途是：

- 审计产品是否声明 observed/assumed；
- 检查 product-declaration 删除是否改变产品 ledger；
- 给 B5b 留 provenance 数据接缝；
- 检测产品 identity 自相矛盾。

它不得进入 reference denominator 公式。对同一输入执行“含 declaration”与“删除 declaration”两次 Va 的 VA-C7 测试，必须证明只有 product ledger/hash 改变，reference ledger、denominator 与 GT identity 不变。

geometry ledger 选择固定：accepted correction v3 在 feature-state/hash 全验后使用其 <code>source_kind="accepted_correction"</code> visibility；reading 没有 accepted correction geometry，故把已匹配 observation 投影到 GT target segment 后使用 <code>source_kind="judge_gt"</code> visibility，但 product <code>OpeningClaimsV1</code>、sidecar product identity 与最终 ledger hash仍绑定 reading output。两种情况都不能把 product ledger冒充 reference ledger。

### 7.5 Absence ledger 与 extra

未匹配产品 opening 不能自动判 extra。步骤固定：

1. 先把 observation 唯一绑定到 GT facade segment 与受信 view。
2. 对相应 span 构造恰七 claim、没有任何 positive evidence 的 absence query，并仍由 Va 计算该 view 是否完整观察。synthetic opening id 固定为 <code>absence:&lt;sha256({output_sha256, observation_id, segment_id, span}) 前24位&gt;</code>，整批检查截断碰撞。
3. 只有 trusted negative intervals 完整覆盖 observation span，才记 <code>extra</code>。
4. 覆盖不全或无 completeness 时记逐 observation NA，reason 为 <code>unobserved_reference_absence</code>。
5. segment 无法唯一绑定时是 REJECTED，不是 NA，也不能用中心点最近项猜。

因此 Va 仍是 applicability 的唯一引擎，B4b 不另写一个“看起来可见”的 extra 判据。

## 8. Segment 与 opening scoring 算法

### 8.1 GT segment 集

- correction v3 的 floor-id 集必须与 GT v3 floor-id 集精确相等；reading 只由 plan/elevation score binding 映到 GT floor。v3 禁用 legacy 的 name/ordinal/z/order floor 猜测，缺失、多余或重复 floor id 为 <code>score_product_identity_invalid</code>。
- exterior boundary：直接使用 typed GT boundary segments。
- interior partition：GT v3 已由 B4a validator 保证 zone tiling 零重叠、零缝隙且共享边端点逐位相等。按有向端点 tuple 作精确反向匹配：边 <code>(p1,p2)</code> 只与逐值相等的 <code>(p2,p1)</code> 归为一组，恰由两个 zone 反向共享时形成一个 interior target。GT 侧容差固定为零，不读取任何 judge tolerance、不做 snap/近线/近端点合并；零个、超过一个反向 mate 或与已验 exterior 拓扑矛盾均为 GT/adapter invariant failure。
- 外边/内边都保留 stable target id、floor、world endpoints、长度与邻接 zone ids。
- 凹多边形、多段同 family、短回折、非矩形 floor 都必须保留；禁止收缩成 W/D bbox 或四条 facade。

### 8.2 产品 segment 集

- reading：从受信 plan frame 中提取 wall strokes/segments，先做坐标反变换，再保留 source observation id。
- correction：从 cell/footprint polygon edges 提取，不使用 bbox。
- 同一直线的碎片只在 gap 小于 config extent tolerance、且没有拓扑分叉时合并；原 observation ids 仍写 sidecar。
- correction window 的 <code>facade_segment_id</code> 若存在，必须验证 floor/family/span；若缺失，只准在同 floor/family 中找到完整包含 span 的唯一产品 segment，记 <code>temporary_unique_span_binding</code>。
- 零个或多个候选均 <code>score_product_segment_unresolved</code>；B4b 不写回产品，也不生成 canonical host id。

### 8.3 Segment assignment

候选边先满足：

1. floor 相同；
2. 令 target 的单位切向/法向为 t/n、产品端点为 q1/q2，<code>axis_alignment_error_m = abs(dot(q2-q1, n))</code> 不超过 <code>plan_axis_alignment_tol_m</code>；
3. <code>position_error_m = abs(dot(mid(q1,q2)-mid(p1,p2), n))</code> 不超过 <code>plan_position_tol_m</code>；
4. 正投影 overlap 为正。

全局 assignment 的字典序目标固定为：

1. 最大匹配 target 数；
2. 最大总 overlap 长度；
3. 最小总横向距离；
4. 最小总 extent symmetric-difference。

若两个 assignment 在 tie epsilon 内完全等价，拒绝 <code>score_match_ambiguous</code>。不得再用 id 或列表顺序破局。

每个 matched segment 的状态：

- complete：position 与 endpoint/extent error 均不超过 complete epsilon；
- within_tolerance：均不超过各自 tolerance，但至少一个超过 complete epsilon；
- miss：有候选但超过 tolerance，或 target 未匹配；
- extra：unmatched 产品 segment；segment 是 plan 几何事实，不需要 opening completeness 才能判，但必须来自 manifest 的 required full plan view。opening completeness assertion 不得越权证明 wall coverage。

### 8.4 Opening assignment

按 source view 独立匹配，候选约束：

- floor、opening kind、resolved GT segment 一致；
- target 与 observation along interval 正 overlap；
- center distance 不超过 <code>opening_match_center_tol_m</code>。

全局目标：

1. 最大匹配数；
2. 最大总 interval overlap；
3. 最小总 center distance；
4. 最小总 width difference。

tie 处理与 segment 相同。多个 plan/elevation source 可以佐证同一 GT opening，但同一 source observation 不能匹配多个 target。重复 <code>opening_id</code>、dangling source 或八个 claim 在进入 assignment 前由 Va/adapter 合同拒绝。

### 8.4.1 Host 的 judge-only 关系解析

host 不调用也不产出 B5 canonical resolver 结果。对 reference Va 判为可用的 plan host row，按以下纯评分关系解析：

1. GT 侧使用 <code>GtOpeningV3.boundary_segment_id + host_zone_id</code>；当前 C2 profile 的 host zone 非空且在 opening span 上与该 boundary segment 有正宽共线边。
2. 产品侧先按 §8.2 唯一解析 product facade segment。window 的 <code>room</code> 未声明时是缺失预测，host 记 miss；声明了 dangling room/cell id 是产品合同错误，REJECTED。
3. 已声明 room/cell 的 polygon boundary 必须在 window 完整产品 span 上与该 product segment 正宽共线。零个或多个相邻 room 是 <code>score_product_segment_unresolved</code>；唯一但声明 room 不是该相邻 room，host 记 miss。
4. product segment 经 §8.3 assignment 映到 GT segment。映射等于 GT opening segment，且其 span 对应的唯一 GT 邻接 zone 等于 <code>host_zone_id</code>，host 才 complete；唯一但关系不同为 miss。
5. 此关系只存在于 <code>ClaimScoreRowV8</code> 的审计 evidence 中，不修改 <code>WindowV3.facade_segment_id</code>、room 或任何 output。

因此 B4b 已能判未来 B5 挂载是否正确，但没有提前取得 B5 的 writer/validator 所有权。

### 8.5 精确 partial denominator

令 GT target interval 为 T，reference Va 给出的 applicable interval union 为 A，长度函数为 L。所有 interval 先 canonical merge、clip 到 T，并按 Va epsilon 校验。

每个 claim 的 eligible units：

- capability/reference-value override 先执行：appearance、unsupported target kind、以及 GT value 为 null 的 sill/head 均为 0 并带稳定 NA reason，不能被 Va 的可观察 coverage 抬成可计分；
- reference status <code>not_applicable</code>：0；
- reference status <code>applicable</code> 且 reason 为 <code>full_observable_coverage</code>：1；
- existence status <code>applicable</code> 且 reason 为 <code>existence_observable_fragment</code>：1；这是 Va 对 existential claim 的冻结特例，不能误计为 full-width 证据；
- <code>partially_applicable</code>：
  - host：L(A) / L(T)，并且只在 plan source 能唯一解析 segment+zone 关系时比较；
  - along：L(A) / L(T)；
  - width：L(A) / L(T)；
  - sill：有非空 A 且 GT sill 非 null 时记 1；
  - head：有非空 A 且 GT head 非 null 时记 1；
  - appearance：0，reason <code>reference_value_unavailable</code>。

Va 冻结 wire 不会产 <code>partially_applicable</code> existence；若收到该组合即 <code>score_claim_applicability_invalid</code>。不存在固定 0.5。A 为空、越界、重叠或 L(A) 大于 L(T) 均拒绝。

allocation 规则：

- full、existence、host、sill、head 各产一个 outcome slice；
- partial along/width 对 A 的每个 canonical component 各产一 slice，units 精确为该 component 长度除以 L(T)；
- 若 trusted negative conflict 只覆盖 component 的一部分，先按所有 A/N endpoints 再切片，再分别分配 complete/within/miss/conflict units；
- 序列化值不预先四舍五入，只有守恒比较使用 tie epsilon。

### 8.6 Claim 比较

对 interval claims，把所有受信 source 的 applicable positive union 记为 A，产品预测 interval 为 P。Va 的 <code>negative_evidence_intervals</code> 表示“该 source 有资格把缺失当负证据”，不是另一个 desired-negative 几何集合；它只进入 absence/conflict 裁决，不能从 GT target 中相减或充当第二份观察真值。

- existence：P 与 A 有正 overlap即 complete；无 overlap 为 miss。existence-fragment 的 eligible unit 仍为 1。
- host：先要求产品 window 的 segment 与 room/cell 关系在产品几何内唯一，再把产品 segment 和相邻 zone 分别映射到 GT；两者同时等于 GT <code>boundary_segment_id</code> 与 <code>host_zone_id</code> 才 complete，唯一但任一不等为 miss，零/多解析为 REJECTED。partial 时按其 eligible units 加权。
- along：
  - full coverage 时直接比较 T/P 的 lo、hi，metric 为两端绝对误差最大值；
  - partial 时令 <code>P_A = P ∩ A</code>，对 A 的每个 component 计算未被 P 覆盖的 prefix/suffix 最大长度，取全局最大值；P 落在 A 外的部分在本 row 不受罚。
- width：
  - full coverage 时 metric 为 <code>abs(L(P)-L(T))</code>；
  - partial 时 metric 为 <code>L(A)-L(P ∩ A)</code>，只评价可观察宽度。
- sill/head：对每个能观察该 scalar 的 source 比较 absolute error；GT value null 时 NA。
- appearance：按 capability matrix NA；host 按 plan 的唯一 segment+zone 关系评分。

结果阈值：

- error 小于等于 complete epsilon：complete；
- error 小于等于 claim tolerance：within_tolerance；
- 超过 tolerance 或无匹配：miss；
- 两个独立可观察 source 的 scalar/interval 结果互相超过 tolerance：conflict，计入 denominator 且按 fail units 处理。

产品超出 partial A 的部分不在该 target claim 中受罚；若其 span 由另一受信 negative coverage 完整覆盖，则由 absence ledger 记 extra。这样既不惩罚不可见区域，也不把不可见区域当正确。

### 8.6.1 Trusted negative conflict

对每个 target/claim，逐 source 读取 Va <code>SourceEvidenceDecisionV1.negative_evidence_intervals</code>，只承认带有效 completeness assertion 的区间：

1. 同一 source 同一区间同时出现 GT positive declaration 与 trusted negative absence 是 reference/manifest 自相矛盾，REJECTED，不把矛盾转嫁成产品 miss。
2. 产品在某 source 无 positive declaration，而该 source 的 trusted negative interval 覆盖 target 可评分 slice；若另一 source 有产品 positive，则该 slice 为 conflict。
3. 若所有应表达该 claim 的完整 source 都无产品 positive，slice 为 miss。
4. negative coverage 只覆盖 slice 一部分时按 §8.5 endpoints 切开，只给覆盖部分 conflict/miss units。
5. 无 completeness、遮挡、裁切或区间外缺失不产生 conflict。

这条只消费 Va 已输出的 negative intervals，不自行推断“图上没画”。

### 8.7 多 source fusion

- 先逐 source 计算 applicability 与 error，再按 target/claim 聚合。
- 至少一个 source complete 且其余可观察 source 不冲突：complete。
- 无 complete、至少一个 within 且其余不冲突：within。
- 任何独立可观察 source 冲突：conflict。
- 所有 source NA：NA。
- 不允许用多个弱 partial 自动拼成 full，除非其 applicable interval union 经 Va totality 明确覆盖 T；拼接后的 denominator 上限仍为 1。

### 8.8 Elevation 与 plan 的职责

- plan 可评分：existence、host、along、width。host resolver 是 judge-only、无写回的评分关系解析器；B5 仍拥有 production canonical 挂载。
- elevation 可评分：existence、along、width、sill、head；appearance 保留 row 但 NA。
- floor line 用实际 floor z 与受信 elevation frame 比较，不按 W/D 或固定四面投影。
- GT z null 的 sm26-style opening：plan claims 正常，sill/head 明确 NA，PNG 标注 <code>PLAN-ONLY · z NA</code>。
- mirror/local-x 只按 bindings 变换；true/unknown direction 没有外部 resolution 时整 view REJECTED。
- GT <code>north_axis_deg</code> 只进入 GT content identity；所有 scorer 几何留在 building-axis world frame，不按真北旋转 segment/family。

## 9. Policy 与 verdict

### 9.1 Legacy v2

保留现役 wall/window/boundary/elevation counter、criteria、verdict 和 renderer 输入语义。不得为了统一 v3 denominator 而改变 v2：

- sm21 floor mapping 与现有 complete/within/miss/extra 数；
- correction elevation 当前 14 complete、1 miss、1 extra 的既有断言；
- legacy elevation overlap-ratio 行为；
- sm20 无 GT 时不生成伪 sidecar/grade；
- schema 7 或更早 sidecar 在 schema 8 进程中重算。

### 9.2 C2 v3 criteria

criteria 只从 normalized rows/summary 生成，至少包含：

- <code>walls_complete</code>；
- <code>boundary_complete</code>；
- <code>windows_placed</code>（existence）；
- <code>window_plan_geometry</code>（along/width）；
- <code>window_elevation_geometry</code>（sill/head 及受支持的 along/width）；
- <code>floor_lines_complete</code>；
- <code>no_oversplit</code>；
- <code>negative_evidence_complete</code>。

每项 criterion wire 必须含 <code>eligible</code>、<code>denominator_units</code>、<code>passing_units</code>、<code>failing_units</code>、<code>na_reasons</code> 与 machine verdict。

裁决规则：

- denominator 为 0：criterion <code>not_applicable</code>，不通过也不失败；
- miss/conflict units 大于政策阈值：fail；
- NA 不进入阈值；
- 顶层所有核心 criteria 均 NA：顶层 <code>not_applicable</code>；
- identity/totality 非法：顶层 REJECTED，不进入 StageVerdict 分数聚合；
- <code>StageVerdict.not_applicable</code> 与 <code>insufficient_evidence</code> 沿现役机器枚举使用，不新增近义字符串。

## 10. Sidecar、cache、run-stage 与原子性

### 10.1 写入位置与所有权

沿用 attempt 目录中的 <code>score_vs_gt.json</code> 和 <code>grade.png</code>，但内容由 schema 8 writer 管理。B4b 定义 judge-side <code>ScoreArtifactContractV1</code>，不扩充 production <code>RunManifestV2.ArtifactKey</code>。RunManifest 与 accepted StageRecord 只作为受信输入。

### 10.2 Cache hit

cache loader 必须：

1. strict parse <code>ScoreSidecarV8</code>；
2. 重算 sidecar content hash；
3. 从当前盘面独立构造 expected <code>ScoreIdentityV8</code>；
4. 对整个 identity 做结构相等比较；
5. 重验所有嵌入 ledger content hash 和 claim row 引用；
6. 确认 capability path 与当前 dispatch 一致；
7. 确认 grade renderer version 与 grade 文件 identity 一致。

任何 schema 0–7、缺字段、额外字段、hash/helper/config/manifest/accepted 状态变化、ledger 引用变化均 cache miss 并重算。不得写“兼容默认值”把旧 sidecar 提升为 v8。

### 10.3 Accepted attempt identity

- 未 accepted：<code>accepted=false</code>、record hash null；
- accepted：hash accepted StageRecord canonical dump，并验证其 artifact chain 指向当前 output hash；
- 同一 attempt 后续被接受、撤销或 StageRecord 改变都触发重算；
- correction accepted output 若含 Va feature state/declaration，必须同时验证 output hash、feature state hash 与公开 artifact contract。

### 10.4 原子写

sidecar 与 PNG 都采用同目录临时文件、flush、fsync、<code>os.replace</code>。顺序固定：

1. 完成全部评分与 strict validation；
2. 生成临时 PNG 并验证可解码；
3. 生成临时 sidecar 并回读 strict validation；
4. replace PNG；
5. replace sidecar，sidecar 是 commit marker。

进程中断只能留下可安全忽略的 temp；不能留下新 sidecar 指向旧 PNG。原子写失败为 <code>score_atomic_write_failed</code>，保留最后一个完整旧 pair。

### 10.5 CLI

<code>score_reading_vs_gt.py</code> 必须迁到 typed GT dispatch：

- v2 仍输出 legacy projection；
- v3 要求 manifest、bindings、judge config 与可选 completeness overlay；
- 提供 <code>--explain-capability</code> 输出 capability decision，不做评分；
- 缺 v3 输入给稳定错误，不调用 raw legacy scorer；
- CLI 与 run-stage 共用同一 service 函数，禁止复制 scoring policy。

## 11. Grade PNG 合同

### 11.1 Dispatch

- GT v2 + legacy payload：完全走现役 renderer，像素 regression 不变。
- GT v3 + C2 payload：走新的 typed polygon renderer。
- 顶层 NA：灰色信息板，列 capability/reason，无红绿几何。
- identity 后 REJECTED：错误信息板，列 gate/error code，不生成伪计分图；identity 前 REJECTED 不产 artifact。

### 11.2 v3 几何

- 使用 B4a public <code>gt_to_render_model(doc) -&gt; GtRenderModel</code> 与 actual polygon；不得调用 W/D bbox transform。
- 动态枚举实际 facade segments；不得固定 N/S/E/W 各一个 panel。
- plan/elevation panel 都显示 stable segment/opening id 的短标签，sidecar 保留全 id。
- projection、mirror、local x 只来自 score bindings。

### 11.3 NA 灰色斜线

- renderer v1 常量冻结为 <code>NA_FILL_RGBA=(224,224,224,192)</code>、<code>NA_LINE_RGBA=(107,114,128,224)</code>、设备像素线宽 2、法向间距 8、左下到右上 45°；不从主题、DPI 比例或 matplotlib 默认值漂移。
- full NA：覆盖整个 target claim rail/几何。
- partial：只在 <code>unobserved_intervals</code> clip 后画斜线；applicable fragment 仍按 complete/within/miss 色显示。
- 灰 hatch 不计作 miss/extra，不与红色叠加制造“失败”暗示。
- z-null：对应 elevation rail 全 hatch 并标 <code>PLAN-ONLY · z NA</code>。
- host 只对 unobserved residual 画 hatch；appearance 因无 reference value 整条 claim rail hatch，并各自显示明确 reason。
- PNG 不根据 observed/assumed provenance 猜颜色；sidecar 只保留 provenance/knowledge ref 供 B5b。

### 11.4 Render totality

每个 sidecar target/claim 必须在 renderer audit map 中恰有一个位置或显式 <code>not_rendered_reason</code>。多/少 target、未知 segment、区间 clip 不守恒均 <code>scoring.render_totality</code> reject。

## 12. 文件级施工清单

路径可因 B4a 实际落地小幅对账，但职责不得合并回 production：

### 12.1 新增

- <code>src/agent/judge/score_schema.py</code>：§6 strict wire 与 canonical hash。
- <code>src/agent/judge/score_config.py</code>：judge config loader/validation。
- <code>src/agent/judge/score_inputs.py</code>：bindings、direction、completeness overlay 与 effective manifest。
- <code>src/agent/judge/segment_score.py</code>：polygon segment extraction/assignment。
- <code>src/agent/judge/opening_claim_score.py</code>：GT-to-Va adapter、matching、denominator/fusion。
- <code>src/configs/judge_score.yaml</code>：唯一 v3 tolerance profile。
- <code>scripts/tool_scripts/build_judge_score_inputs.py</code>：候选 user/dataset declaration builder/validator。
- B4b Phase 对应的 synthetic/temp-only 测试文件。

### 12.2 修改

- <code>src/agent/judge/reading_score.py</code>：保留 legacy；增加 typed dispatch adapter，不在旧函数内塞 v3 分支。
- <code>src/agent/judge/correction_score.py</code>：同上。
- <code>src/agent/judge/elevation_score.py</code>：同上；legacy overlap 行为锁定。
- <code>src/agent/judge/score_policy.py</code>：新增 denominator-aware v3 policy，legacy policy 不动。
- <code>scripts/tool_scripts/render_grade.py</code> 与 <code>scripts/tool_scripts/_grade_transform.py</code>：新增 typed polygon path，legacy transform 不动。
- <code>scripts/tool_scripts/run_stage.py</code>：schema 8、全 identity cache、原子 pair、accepted identity。
- <code>scripts/tool_scripts/score_reading_vs_gt.py</code>：typed service/dispatch。
- A0：B4b Phase A 实施批登记 judge config/hash/helper/version，并逐键登记 §6.3.8 的 <code>view_projection_binding_v1</code> frame-transform preimage 与 sorted-key compact UTF-8 SHA-256 口径；登记完成是独立重算开工门。本出稿轮不改 A0。
- Va tests：吸收 VA-C7 六项；Va module 只有 source scan 发现 no-op 回归时才改，且只在对应施工 Phase 处理。

### 12.3 明确不改

- production output schema；
- <code>view_manifest.py</code> 的 base emitter；
- <code>RunManifestV2</code> production artifact key union；
- 任何 <code>case_tests/.../gt</code>、golden、verified overlay；
- B5/B5b/B6 文件。

## 13. 四 Phase 施工包

四个 Phase 严格顺序；每个 Phase 在自己的 gate 全绿后可独立 merge，但真实 v3 promotion 仍等 §15 联合门禁。

### Phase A — 合同、identity 与 score inputs

前置：B4a Phase A 已落地，执行 <code>B4B-REC-A</code> 逐字对账。

施工：

- strict score schema/config/canonical hash；
- typed loader capability dispatch skeleton；
- GT identity、product/accepted identity、helper identity；
- score view bindings 与 resolved direction validation；
- user/dataset completeness builder、effective manifest pure function；
- GT-to-Va adapter facade hash preimage proof；
- 按 §6.3.8 把 frame-transform 全字段 preimage 登记进 A0，并实现不依赖 Va 私有 helper 的独立 hash；
- sidecar v8 NA/REJECTED skeleton，不接几何 scorer。

测试：

- strict extra/missing/type/NaN/Infinity 拒绝；
- config hash/关系/A0 fixture；
- schema 7 sidecar 必重算；
- base/effective manifest hash 区分；
- user/dataset 两条真实生成路径与 body hash；
- 每 view 单 source、base 冲突、幂等重复；
- standard/true/unknown direction；
- mirrored/local-x 不能来自产品；
- GT-to-Va facade hash 与 A0 frozen preimage 字节相等；
- sign 正负、mirror 两态与 local-x 两态 fixture 的 frame-transform hash 与 A0 固定向量字节相等；缺/多任一 preimage 键均失败；
- v3 绝不调用 raw <code>load_gt()</code>。

出口 gate：

- <code>B4B-A1-wire-strict</code>
- <code>B4B-A2-identity-total</code>
- <code>B4B-A3-completeness-owner</code>
- <code>B4B-A4-va-preimages</code>
- <code>B4B-A5-production-import-zero</code>

### Phase B — Plan segments、opening matching 与 denominator

前置：Phase A 合并；B4a Phase B/C 的 polygon/segment/opening typed 输出落地并执行 <code>B4B-REC-B</code>。

施工：

- exterior/interior actual polygon segment extraction；
- reading/correction segment observations；
- deterministic global assignment 与 tie rejection；
- correction window temporary unique span binding；
- reference/product/absence Va 调用；
- plan existence/host/along/width；
- exact partial units 与 claim summaries；
- extra 的 completeness gate。

测试：

- 凹多边形、L/U 形、多同-family segment、短回折；
- concave multi-segment Va fixture；
- 禁止 bbox/fixed-four-side；
- assignment 输入顺序/ID 重命名不变；
- exact tie 必拒绝；
- missing/ambiguous product segment id；
- partial 10%、50%、90% 按精确比例，证明不是固定 0.5；
- NA/0/miss 三者守恒；
- declaration 删除双调用：reference denominator 不变；
- 无 completeness 的 unmatched opening 为 NA，有完整负覆盖才 extra；
- duplicate opening id、dangling source、第八 claim 拒绝。

出口 gate：

- <code>B4B-B1-segment-topology</code>
- <code>B4B-B2-assignment-determinism</code>
- <code>B4B-B3-va-only-applicability</code>
- <code>B4B-B4-denominator-conservation</code>
- <code>B4B-B5-extra-proof</code>

### Phase C — Elevation、fusion、policy 与 capability 完整面

前置：Phase B 合并；Va 公共合同保持 v1；B4a elevation/source refs 落地并执行 <code>B4B-REC-C</code>。

施工：

- elevation actual-segment projection；
- mirror/local x/direction frame；
- sill/head/floor-line score；
- plan/elevation 多 source fusion/conflict；
- host judge-only 关系评分、appearance/z-null NA；
- v3 criteria/verdict；
- unsupported combination 顶层 NA；
- 逐 target/claim totality。

测试：

- mirrored/non-mirrored 相同世界结果；
- true/unknown 缺 resolver 拒绝；
- multi-facade same family；
- plan-only z-null；
- sill/head partial binary eligibility；
- source conflict 进入 conflict units；
- host 的正确/错误/歧义三面，appearance 明确 NA 且不入 denominator；
- correction v1/v2 + GT v3 顶层 NA；
- door row <code>unsupported_target_kind</code>；
- 全核心 criterion NA 的顶层 verdict。

出口 gate：

- <code>B4B-C1-frame-trust</code>
- <code>B4B-C2-elevation-claims</code>
- <code>B4B-C3-fusion-totality</code>
- <code>B4B-C4-na-machine-surface</code>
- <code>B4B-C5-policy-conservation</code>

### Phase D — Run-stage、cache、renderer、CLI 与回归封口

前置：Phase C 合并；B4a Phase D render seam 落地并执行 <code>B4B-REC-D</code>。

施工：

- <code>SCORER_SCHEMA "7" -> "8"</code>；
- full identity cache validator；
- accepted StageRecord digest；
- sidecar/PNG atomic pair；
- typed polygon renderer 与 gray hatch；
- CLI service dispatch；
- legacy v2 regression；
- VA-C7 六项最终债务扫描；
- import boundary/static scan。

测试：

- schema 0–7 sidecar 全重算；
- 逐个改变 GT hash/schema、capability、config、base/effective manifest、overlay、bindings、Va/Vg/helper、output、accepted 状态都重算；
- 完全相同 identity 才 cache hit；
- interrupted write/fault injection 不暴露半 pair；
- gray hatch full/partial clip、z-null label、NA 信息板；
- legacy renderer pixel hash/采样点保持；
- sm21 当前 floor map/counters/elevation assertions；
- sm20 无 GT 行为；
- CLI v2/v3/NA/REJECTED；
- source scan 无 tautological no-op assert；
- production import judge 为零；
- 无 GT/golden diff。

出口 gate：

- <code>B4B-D1-cache-identity</code>
- <code>B4B-D2-atomic-artifacts</code>
- <code>B4B-D3-gray-hatch</code>
- <code>B4B-D4-legacy-v2-regression</code>
- <code>B4B-D5-va-c7-closed</code>
- <code>B4B-D6-protected-assets-clean</code>

## 14. B4a 落地后逐字对账门

### 14.1 通用规则

每道 reconciliation gate 都产一份机器 diff/人工签字记录，比较“B4a v2 细稿冻结合同”与“实际 merge 后公共 API”。只允许：

- 字段、Literal、strictness、hash preimage、错误码、helper version 完全一致；或
- 先由 B4a/B4b 联合 review 更新权威合同，再施工。

不允许 B4b 私下接受两个字段名、两个 preimage 或 raw/typed 双轨。

### 14.2 <code>B4B-REC-A</code>

逐字核对：

- <code>GroundTruthV3</code>、<code>GtBoundarySegmentV3</code>、<code>GtOpeningV3</code>；
- <code>load_gt_document()</code>、<code>load_gt_file()</code>、legacy <code>load_gt()</code> 的 v3 fail；
- content/file hash 定义；
- verification/profile/source ref wire；
- strict error code。

### 14.3 <code>B4B-REC-B</code>

逐字核对：

- floor/zone polygon、boundary/interior segment id；
- opening <code>boundary_segment_id</code>、world-along interval、nullable z；
- Vg tolerance 与 segment排序/preimage；
- stable id 与 geometry canonicalization。

### 14.4 <code>B4B-REC-C</code>

逐字核对：

- elevation source refs、view kind/floor/facade identity；
- render/source-view binding seam；
- verified overlay 的独立性声明；
- Va adapter 所需的全部公开字段。

### 14.5 <code>B4B-REC-D</code>

逐字核对：

- B4a typed render model；
- grade overlay 接口；
- promotion gate 名称与 required artifacts；
- B4a §15.2 对 B4b scorer/sidecar/cache/render 的联合验收项。

## 15. 验收与 promotion

### 15.1 每 Phase merge 条件

- 本 Phase 指定测试全绿；
- 全仓相关 targeted suite 绿；
- mypy/ruff 或仓库对应静态检查绿；
- protected GT/golden roots 无 diff；
- production import boundary scan 绿；
- sidecar/schema/A0 变更与本稿一致；
- 前一 Phase gate 仍绿。

### 15.2 真实 v3 promotion 条件

B4b 代码 merge 不自动批准真实 GT v3。promotion 必须在独立资产批同时满足：

1. B4a typed GT、verification、render overlay 全部批准；
2. B4b scorer、reference/product/absence ledgers、denominator、sidecar/cache、gray hatch 全绿；
3. score view bindings 与 completeness source 经过人工/数据集 review；
4. B4a/B4b 联合 promotion gate 签字；
5. 单独资产 diff 明示每个新/变更 GT、golden、overlay；
6. legacy sm21 与 sm20 回归无变化。

### 15.3 最小验证命令族

实际文件名按施工落地，但 CI 至少提供等价命令：

    pytest -q tests/test_c2_b4b_contract.py
    pytest -q tests/test_c2_b4b_score_inputs.py
    pytest -q tests/test_c2_b4b_plan_segments.py
    pytest -q tests/test_c2_b4b_claim_denominator.py
    pytest -q tests/test_c2_b4b_elevation.py
    pytest -q tests/test_c2_b4b_sidecar_cache.py
    pytest -q tests/test_c2_b4b_render_grade.py
    pytest -q tests/test_c2_va_applicability.py
    pytest -q tests/test_judge_batch_b.py

另做静态断言：

- <code>SCORER_SCHEMA == "8"</code>；
- production import judge 数为零；
- protected asset diff 为空；
- Va source 不含已知 tautological no-op assert pattern；
- v3 path 不引用 W/D bbox/fixed-four-facade helper；
- v3 path 不读 <code>correction.yaml</code>。

## 16. 失败、回滚与诊断

- 合法 unsupported：写 schema 8 NA sidecar/信息板，可 cache，reason 稳定。
- GT/product/manifest 最前置 identity 无法构造：直接返回 machine REJECTED，不写 sidecar/PNG，也不 cache。
- identity 已构造后的 binding/applicability/matching 合同非法：写 schema 8 REJECTED sidecar/错误板；不得写几何分数。
- 内部 totality/守恒失败：视为 REJECTED，并保留 gate/error/cause；不得丢弃诊断。
- 写入失败：保留上一个完整 pair，返回稳定错误。
- B4a 对账失败：停止对应 Phase，不创建兼容 shim。
- legacy regression 失败：回滚该 Phase 的 dispatch 接线；不得更新 golden 追随新行为。
- v3 promotion 失败：只撤销资产批，不要求回滚已通过的 judge capability 代码。

## 17. 主控裁决登记（r1 五项全批准）

v1 的五项裁决题已由主控在 r1 全部裁定，v2 不再把它们列作开放问题；施工按下表冻结结论执行：

| # | 裁决题 | 主控裁决 | v2 施工落点 |
|---|---|---|---|
| 1 | 新增 judge-only <code>score_inputs/view_bindings.json</code> 作为受信 GT view/mirror/frame 映射 | **批准**：judge 使用自己的受审输入，不信任产品自报，也不假定 input id 与 GT view id 相等；真实资产走独立 asset review。 | §6.3 strict wire、§13 Phase A、§15 promotion gate。 |
| 2 | partial denominator：existence/sill/head 为有可见片段时 binary；host/along/width 为 <code>L(A)/L(T)</code>；host judge-only 不写回；appearance NA | **批准**：scalar 可见即可读值，interval 按可见长度配比；host 不抢 B5 writer，appearance 无独立 GT 真值。 | §8.5–§8.6 outcome slices、守恒与 NA wire。 |
| 3 | <code>SCORER_SCHEMA "7" -&gt; "8"</code> | **确认**：主控亲核 <code>scripts/tool_scripts/run_stage.py:75</code> 现值为 <code>"7"</code>；“schema 2 重算”只作历史机制描述。 | §5.1 常量、§10 cache invalidation、Phase D schema bump。 |
| 4 | manifest v1 每 view 最多一个 completeness source；judge-only overlay 生成 effective manifest，不改 base emitter/RunManifest | **批准**：单 assertion 槽位是现役 wire 事实，effective manifest 为内存纯函数并以 hash 入 sidecar。 | §6.4 owner/trust/hash/attempt binding。 |
| 5 | B4b 只交付 PNG 灰纹 NA 与 sidecar provenance 接缝；HTML assumed/observed 猜色归 B5b | **批准**：符合总设计批次分工。 | §11 renderer；B5b 边界保持不动。 |

五项均无残留裁决不确定。上述批准不扩大 B4b 到 B5/B5b/B6，也不批准本批修改任何 GT/golden。
