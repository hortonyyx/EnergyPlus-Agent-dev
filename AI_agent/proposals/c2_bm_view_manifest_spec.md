# C2 B-M 细稿 v6（定稿）：受信视图清单（Trusted View Manifest）schema + generator

> **版本史**：v1 2026-07-10 → sol+max r1 **REWORK 8**（[r1](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review.md)）→ v2（8 全采纳）→ r2 **REWORK：5 CLOSED/1 PARTIAL + 新 6**（[r2](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r2.md)）→ v3（6 全采纳）→ r3 **REWORK：r2 5 CLOSED/1 PARTIAL + 新 2（1 BLOCKER/1 HIGH）**（[r3](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r3.md)）→ v4 = r3 2 条全采纳 + 恢复累计式自包含全文（自包含判过）→ r4 **REWORK：r3 2 条均 CLOSED + 新 2（R4-X-01 共同 BLOCKER / R4-BM-01 HIGH）**（[r4](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r4.md)）→ v5 = r4 2 条全采纳（本稿成为 RunManifestV2/StageRecordV2 共同 wire 的**唯一规范 owner**、B-M 先落 B2 消费；CompletenessAssertion strict wire 冻结）→ r5 **APPROVE-WITH-CHANGES：r4 2 CLOSED/2 PARTIAL + 2 HIGH changes、零 BLOCKER**（[r5](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r5.md)）→ v6 = R5-X-01/R5-BM-01 两补丁机械并入（artifact_contract 判别 + migration commit 协议 + coverage 删裸 source_ref + user 内层 id 删除）→ r6 短文字复核 **APPROVE（两补丁 CLOSED、交叉一致、"可进入既定施工顺序、无需 r7"**，[r6](../logs/reviews/verdict/2026-07-10_c2_b2_bm_detail_review_r6.md)）——**本稿定稿**。施工序=本批先落（共同 wire+claims.py+manifest/isolation/gate 接线）→ B2 消费。
> **上位设计** = [c2_full_unlock_design.md](c2_full_unlock_design.md) v2.2：E2'.4（受信视图清单，闭 A-04 洗分漏洞）、E2'.1（负证据前提机读，C-03 细稿门）、E4.3/E4.4（direction_semantics，C-04 细稿门）、§批次重排 B-M 行（M 档，无依赖）。
> **核心不变量**：清单由编排侧从 case metadata **确定性生成，产品（reader/correction LLM）不可改、不可影响**——"源图已提供而 reader 漏读 = miss，不是 unobserved"；**reader 不得通过自报"低清/没看见"改变 judge denominator**（C-03）。
> 纪律：细稿→审→执行→复核；只放行 B-M 施工。file:line 以 `7422f42` 为准。

---

## 0. 范围与非目标

**In**：manifest schema v1 冻结（strict typed models + 条件约束，含 CompletenessAssertion strict wire）+ strict generator + **provision/verify API 分立接线**（唯一 emitter = run provisioning/0_reading preflight）+ `validate_case` 只读比对 + **isolation 全链闭环**（run 绑定、ensure 前置、merge 同门、staging 只读投影、reader 可见性铁律）+ **RunManifestV1/V2 与 StageRecordV1/V2 wire 分立（§5.1，本稿=该共同 wire 的唯一规范 owner；B-M 先落、B2 消费，r4 裁决，"先合者建"废除）** + claims.py 常量模块（内容以 B2 稿 §2.8 为准，因 B-M 先落由本批创建）+ gate① 恒 BLOCK 对账 check + 测试。

**Out**：Va applicability 逻辑本体（Va 批；但其 **source-aware 消费公式**本稿冻结为契约）、per-claim denominator/sidecar（B4b）、REPORT/HTML 桶（B5b）、立面匹配引擎 matcher / OCR 图名 hint / partial 视图消费（C3）、指北针 glyph 解析与 θ 填充（E4 批；但 **ResolvedViewDirection sidecar 接缝**本稿冻结）。

## 1. 现状对账（累计，全部经 r1–r3 核证）

| # | 事实 | 位置 |
|---|---|---|
| 1 | case metadata = `case_data/testdata_prompt.json`：`Floor plans[]{floor,path,thermal_zones,dimensioned}`、`dimensioned_views[]`、四个 `"<Dir> view path of the building"` 键（sm21 实样 6 视图）；**sm20 有 metadata 显式声明的 supplementary plan**（sm20 testdata_prompt.json:12-16） | [case_metadata.py](../../src/agent/execution/case_metadata.py) + case_data 实样 |
| 2 | `dimensioned_view_names()` 已读 `views:{}` 扩展槽（现无 case 使用）（case_metadata.py:51-75）；`load_case_metadata()` 对缺文件/坏 JSON/非 dict **静默返 `{}`**（:9-28，对 trusted generator 是 fail-open） | — |
| 3 | flow 视图发现 = `0_reading/*_view.json` glob（run_stage.py:111-134）；**source stem（`supp_plan`）≠ 产物 stem（`supp_plan_view`）**——"image stem 即对账键"只对 `*_view` 命名碰巧成立；reading skill 要求每源图一产物（session_kickoff.md:44-58） | — |
| 4 | isolation：staging 有 `MANIFEST.json` = staging 拷贝审计（isolation.py:57-88，与本清单异物）；builder 拷 case_data 下**全部 PNG**（:252-260）、kickoff 让 reader 读全部图（:308-322）；**`build_isolation_workspace` 的 `run_dir: Path | None = None` 可无 run 构建**（:91-120），`merge_isolated_output(staging_root, run_dir)` 独立接受任意目标 run（:150-166）、手造仅含 `reading.isolation_provenance_bound=PASS` 的 CheckReport、`accept=True` 直写 accepted StageRecord（:150-214）；provenance 只记 staging/settings/guard/access-log hashes、**不记 builder 的 run 身份**（:451-475）；现测试接受 `{"views":[]}`（tests/test_isolation.py:286-302）且正常走无 run 构建（:23-24） | — |
| 5 | run 根纪律 = 纯文件夹+yaml，机器记账走 `run_meta_path` 进 `<run>/_run/`（6.23 定案）；`validate_case` 合同 = non-invasive audit、默认不写盘（validation_run.py:1-14,277-283；tests/test_validation_run_baseline.py:54-65,99-105 断言不建 run manifest） | — |
| 6 | `RunManifest`：`extra="forbid"`、字段仅 case/manifest_version("1")/stages、**无 run 级 hash 槽、无 run_id**；load/save 用当前类全量 parse/dump（manifest.py:114-135）；`StageRecord` 身份只有 `output_hash`（:99-111）；isolation 第二 writer `_atomic_save_manifest` 直接 `model_dump_json`（isolation.py:514-524）；**execution 路径不存在通用 immutable run 标识**（目录名/路径会因移动/复制改义） | — |
| 7 | run_profile 分档只对特定 evidence check ids 生效（checks/schema.py:106-145,41-59）；`reading.present` 已是 INVARIANT（run_stage.py:106-121） | — |
| 8 | judge-only 路径不经 `_draw_reading`（run_stage.py:1383-1406） | — |
| 9 | 教训：prescan `overlay_path` 绝对路径致同内容异地字节不等（07-09 登记）——确定性字节是硬要求 | plan.md 07-09 条 |

## 2. 命名、落位与 reader 可见性铁律

- 文件名 **`view_manifest.json`**，落 `run_meta_path(run_dir, "view_manifest.json")`（= `<run>/_run/`，遵 §1#5；与 staging `MANIFEST.json` 异名异地）。
- schema 独立版本化（上位定案：view manifest 独立 schema/version，不塞 CorrectedGeometry）。
- **受信原件不进 staging**：含负证据/completeness 断言的清单本体对 reader 物理不可见。
- **staging 只读 input inventory 投影**：generator 派生 `input_inventory.json` 进 staging = 每张 required 图 `{input_id, file, view_type, declared_direction_token, floor_ref, expected_output_id}`——reader 合法获知"读什么、产什么名"，denominator 相关断言不在其中；guard 对该文件只读（写=拦）。
- **reader 可见性铁律**：**凡 reader 可见且可能承载图纸 claims 的输入，必须是 `required_view + reader_output_required=true`**（"已分类但无需产物"= 证据旁路，r2 裁死）：
  - 不要求产物的文件（`non_drawing_asset`、暂不消费的 detail 等）**不拷进 reader 可见 staging**；确因工具链需要保留的，由 guard/目录权限使 reader 不可读，staging MANIFEST 登记理由；
  - `derived_working_copy` 仅在**绑定 parent + 版本化等价规则**（哈希级 content relation，如 `*_source.png` = 原图逐字节拷贝的既有约定）时可见，其上 claim 的 provenance 归 parent；
  - **C2 域内 `reader_output_required` 恒 true**（字段保留为 C3 槽位，不是本批可用旋钮）。

## 3. Schema v1（strict typed models 全量）

### 3.0 顶层
```jsonc
{
  "view_manifest_schema_version": "1",
  "claims_vocab_version": "1",                  // 引 B2 claims.py
  "generator_version": "1",
  "completeness_ruleset_version": "1",          // §4.2 静态表版本
  "case_id": "sm21_anchor",
  "case_metadata_sha256": "<hex64>",            // 源 metadata 哈希（hash 解释链）
  "entries": [ /* ManifestEntry[]，按 input_id 字典序 */ ],
  "content_sha256": "<hex64>"                   // 规范化 payload（排除本字段）之 hash
}
```
- 全部 submodel `extra="forbid"`；消费端先验 schema+版本+content hash 再读字段；未知版本 fail closed。
- **确定性铁律**：canonical JSON（键排序、相对路径、无时间戳、浮点无损）；同一 case metadata + 同一图像字节 ⇒ 清单字节相同（§1#9 教训）。

### 3.1 entry 身份（唯一 = `input_id`）
`input_id` = 全清单唯一主键、canonical sort 键；**所有 foreign key**（opening provenance 的 source ids、ResolvedViewDirection.input_id、gate 对账、B4b sidecar 引用）一律指 `input_id`；`view_id` 术语废除；`source_image`/`expected_output_id` 只是其属性。取值规则 = 图像文件 stem（唯一性由生成期硬门保证，非依赖文件名巧合）。

### 3.2 ManifestEntry（discriminated union on `kind`）
```jsonc
{
  "kind": "required_view | excluded_input",
  "input_id": "South_view",
  "source_image": "case_data/South_view.png",   // 归一化 case 相对路径（禁绝对路径）
  "image_sha256": "<hex64>",                    // 绑定像素（防换图不换名）

  // —— kind=required_view 专有（excluded_input 禁填以下全部字段）——
  "view_type": "plan | elevation | site_plan | detail",
  "view_kind": "full",                          // C2 只产 full；partial 槽位留 C3
  "floor_ref": 1,                               // plan 必填；非 plan 禁填
  "declared_direction_token": "South",          // 原始方位 token，不判语义；elevation 必填，其余可空
  "direction_source": "standard_assumption | title_hint | matcher | user",
                                                 // token 从哪来（上位 E2'.4 四值枚举；C2 生成域只产 user/standard_assumption，
                                                 // title_hint/matcher 留 C3 值域）
  "direction_semantics": "building_axis | true_azimuth | unknown",
  "semantics_source": "standard_assumption | case_metadata | user",   // 语义为何认定（与 direction_source 两轴，枚举独立）
  "azimuth_deg": null,                          // 仅 true_azimuth：必填、有限、[0,360)；其余禁填
  "building_view_direction": "South",           // 仅 building_axis 时 generator 填；true_azimuth/unknown 恒 null
  "dimensioned": true,
  "expected_output_id": "South_view",           // 显式产物对账键（sm20 supp_plan → "supp_plan_view" 类差异由映射表写死，不猜 stem）
  "reader_output_required": true,               // C2 恒 true（§2 铁律）
  "opening_evidence": {
    "potentially_observable_claims": ["existence","along","width","sill","head","appearance"],
                                                 // 静态图种表只到"可观察"，不是 completeness
    "negative_evidence_capable_claims": [],      // 默认空！仅 §4.2 受信来源可逐 claim 开启
    "coverage": null,                            // typed domain（§3.3）或 null；开启负证据时必填
    "completeness_assertion": null               // CompletenessAssertion strict wire（§3.6）或 null
  },

  // —— kind=excluded_input 专有 ——
  "excluded_reason": "derived_working_copy | non_drawing_asset",
  "parent_input_id": "1f_view"                   // derived_working_copy 必填 + 等价规则校验；non_drawing_asset 禁填
}
```
条件约束全部 model validator 强制（枚举互斥/必填/禁填如上注释）；claims 值域 = B2 claims.py 词汇、去重、canonical sort。

### 3.3 coverage typed domain
```jsonc
"coverage": { "frame": "plan_floor_region | elevation_local_along",
              "region": "full_floor | full_facade",     // C2 两值；interval 列表槽位留 C3（补交/局部视图）
              "completeness_assertion_id": "…" }        // source 统一经 assertion 解引用（r5 修：删裸 source_ref，
                                                         // extra=forbid 使 coverage 携带任何来源字段=硬门拒）
```
无坐标框架的裸标量废除。

### 3.4 ResolvedViewDirection sidecar（接缝冻结，E4 批实现）
true_azimuth/unknown 的 resolved 方向**永不回写 manifest**（保 content_sha256 与唯一 emitter）；E4 adapter 产独立 attempt-bound sidecar：`{input_id, resolved_building_direction, view_manifest_sha256, orientation_output_hash, adapter_version}`。Vg/Va 只收该 sidecar 的 resolved 向量；缺失/hash 漂移/不可唯一映射 fail closed。

### 3.5 source-aware Va 消费公式（本稿冻结为契约，Va 批实现）
按证据通道分支（上位 E1'.2 两支；无条件 ∩ Vg 会把凹形建筑里平面对 hidden facade 的合法证据错降 NA，r2 裁死）：
- **plan 来源 claim**：trusted `plan_floor_region` 与 footprint/宿主边界空间覆盖判定，**不与任何立面 Vg visibility 相交**（hidden 不阻止平面证据）；
- **elevation 来源 claim**：trusted `elevation_local_along` **∩ 该视图 Vg visible intervals**；
- 跨通道 conflict 在双方各自 coverage 判定**之后**再比较（负证据前提照 E2'.1）；
- **凹形 hidden segment 四例语料**：plan positive 保留 / plan trusted absence 可作负证据 / elevation absence = NA / elevation positive 仅 visible claim 生效；**sm26 三反例**：hidden elevation absence 不构成负证据 / plan 正证据保留 existence·host·along·width / sill·head 值可 assumed 但 denominator NA。

### 3.6 CompletenessAssertion strict wire（C-03 信任根，r4 R4-BM-01 修——不留给施工者临场设计）

```python
class CaseMetadataSourceRef(BaseModel):        # 全部 extra="forbid"
    source: Literal["case_metadata"]
    json_pointer: str                           # 指向 testdata_prompt.json 内断言位置
    case_metadata_sha256: Hex64
class UserSourceRef(BaseModel):
    source: Literal["user"]
    content_sha256: Hex64                       # 用户断言文本内容 hash（身份唯一归外层 CompletenessAssertion.assertion_id，
                                                 # r5 修：删内层重复 id，杜绝双 assertion identity）
class DatasetSourceRef(BaseModel):
    source: Literal["dataset_ref"]
    dataset_id: str; dataset_version: str; contract_id: str
    content_sha256: Hex64                       # 绑定数据集内容，禁任意字符串 ref、防原地换内容
CompletenessSourceRef = CaseMetadataSourceRef | UserSourceRef | DatasetSourceRef   # discriminated on `source`

class CompletenessAssertion(BaseModel):
    assertion_id: str
    source_ref: CompletenessSourceRef
```
**OpeningEvidence 顶层 validator 一次执行全部联动约束**：
1. `negative_evidence_capable_claims ⊆ potentially_observable_claims`；
2. negative claims 非空 ⇔ `coverage` 与 `completeness_assertion` **同时存在**；为空 ⇔ 二者同时为 null；
3. `coverage.completeness_assertion_id == completeness_assertion.assertion_id`（禁悬空引用）；
4. frame-region 配对：`plan_floor_region ⇔ full_floor`、`elevation_local_along ⇔ full_facade`（C2 域）；
5. coverage **无独立来源声明**——source 统一经 assertion_id 解引用（r5 修：裸 source_ref 已删，"家族一致"字符串校验二义消灭）。
测试：三 source 各一正例；五负例 = 悬空 assertion id / 错误 frame-region 配对 / negative 非 observable 子集 / 空非空联动破坏 / dataset 原地换内容（hash 不符）；coverage 携带来源字段 = unknown-field 拒。

## 4. Generator

### 4.1 strict loader（独立于 `load_case_metadata` 的宽容行为）
metadata 必须存在、合法 JSON object，否则 raise；声明路径必须解析进本 case input root（allowlist、禁逃逸/symlink 出根），统一归一化 `case_data/<name>`；repo-relative legacy 路径（sm21 现状）归一化算法唯一；重复 basename/stem、大小写冲突、非 PNG 各有定义行为（冲突=raise）。**原子写**：temp + fsync + replace；幂等 = 重算比对 content_sha256，不一致 INVARIANT（防跑中换 case_data）。

### 4.2 字段映射规则（确定性，全部来自 case metadata，无一来自产品）
| metadata 来源 | 映射 |
|---|---|
| `Floor plans[]` | required_view + `view_type=plan` + `floor_ref` + `dimensioned`（并集 `dimensioned_views[]`；两处矛盾=raise） |
| `"<Dir> view path of the building"` | required_view + `view_type=elevation` + `declared_direction_token=<Dir>` + `direction_source=user` |
| （无显式声明时） | `direction_semantics=building_axis` + `semantics_source=standard_assumption`（现库全部 case 默认；E4.4 守卫由此机读成立） |
| `views:{}` 扩展槽（既有） | per-view 覆盖：`direction_semantics/azimuth_deg/view_kind/completeness` 断言等，`semantics_source=case_metadata` |
| metadata 声明的 supp/site/detail | **typed required_view**（不落 excluded；expected_output_id 按映射表写死，如 `supp_plan → supp_plan_view`） |
| 图种 → opening_evidence | **静态常量表只填 `potentially_observable_claims`**（plan 行 = existence/host/along/width；elevation 行 = existence/along/width/sill/head/appearance）；`negative_evidence_capable_claims` 默认空，仅显式受信来源（case metadata `views:{}` 完整性断言 / 用户声明 / 版本化 dataset ref）逐 claim 开启 + coverage/completeness_assertion 必填 |

### 4.3 生成期硬门（fail closed）
声明路径不存在/不可读；立面方向重复；floor_ref 重复；input_id/expected_output_id 重复；`true_azimuth` 缺角度；`view_kind=partial` 声明（"partial views not supported in C2" raise）；dimensioned 矛盾；**未分类图像 BLOCK**（case_data 存在但 metadata 未覆盖且不匹配任何 excluded 规则 = raise，"audit-only undeclared" 概念废除）；derived_working_copy 与 parent 哈希关系不符。

### 4.4 API 分立（无双义）
`provision_view_manifest(case_dir, run_dir)`（**唯一 emitter**：run provisioning/0_reading preflight 调）与 `verify_view_manifest(case_dir, run_dir)`（**绝不写盘**：validate_case、judge-only/replay、isolation build/merge 调；缺失/漂移 = finding/INVARIANT）。显式迁移 = `provision --migrate` CLI（唯一写盘例外，显式旗标）。`validate_case` 只调 verify（内存重建 expected 与磁盘/hash 比对，保 non-invasive 合同与"验旧 anchor 不改 golden"）。

## 5. RunManifest V1/V2 + isolation 全链闭环

### 5.1 RunManifest/StageRecord wire 分立（**本稿 = 唯一规范 owner；B-M 先落、B2 消费**，r4 R4-X-01 修）

不在同一类加字段（required 则 v1 load 炸、optional 则 v1 save 被新键污染）；**顶层与嵌套 record 都分型**——只分顶层会让"V1 原封"名不副实（现 `RunManifest.stages` 嵌 `StageRecord`，manifest.py:99-135）：

```python
class StageRecordV1(BaseModel):        # 当前 StageRecord 字段逐字不动（含 output_hash）；load/save 字节不变
class RunManifestV1(BaseModel):        # 现类原封；stages: dict[str, StageRecordV1]

ArtifactKey = Literal["output", "checks", "audit", "feature_states", "isolation_provenance"]  # 受控 enum，未知键拒
ArtifactContract = Literal["migrated_v1", "base_v2", "reading_isolated_v2", "correction_b2_v1"]
class StageRecordV2(BaseModel):        # = StageRecordV1 同字段 +
    record_schema_version: Literal["2"]
    artifact_contract: ArtifactContract   # r5 修：machine-readable 合同判别，仅对应 writer/migrator 可设
    artifact_hashes: dict[ArtifactKey, Hex64]
class RunManifestV2(BaseModel):
    manifest_version: Literal["2"]
    run_id: Hex32                      # 必填 immutable，128-bit random，run provisioning 唯一生成
                                       #（目录名/路径因移动复制改义，不作身份——r3 裁决）
    run_inputs: RunInputs              # {view_manifest_sha256: Hex64}
    stages: dict[str, StageRecordV2]
```
- **必填键规则只由 `artifact_contract` 决定**（r5 修，废除"B2 后/legacy"自然语言判别；load 校验，缺本合同必填键/未知键=拒；禁调用方用默认值降级）：

  | artifact_contract | 必含键 | 唯一 writer |
  |---|---|---|
  | `migrated_v1` | 只登记迁移时真实存在且迁移合同允许的键 | migrator |
  | `base_v2` | `{output, checks}` | StageRunner 通用 attempt writer |
  | `reading_isolated_v2` | `{output, checks, isolation_provenance}` | isolation merge writer |
  | `correction_b2_v1` | `{output, checks, audit, feature_states}` | B2 correction attempt writer |

  **B2 correction writer 必设 `artifact_contract="correction_b2_v1"` + `stage_version` bump 到冻结值 `"2"`**（现 StageRunner 默认 `"1"`，stage_runner.py:124-134——调用方漏 bump/漏设合同 = loader 交叉校验拒：native V2 correction record 报 `base_v2` 两键即拒）；伪造 `migrated_v1` 但 attempt provenance 显示 native = 拒。
- **冻结不变量：`StageRecordV2.output_hash == artifact_hashes["output"]`**（两条 accepted identity 不得矛盾，不等=load 拒）。
- `load_run_manifest()` 版本分发；普通 `save()` 与 isolation `_atomic_save_manifest()` 共用同一 versioned serializer（消灭双 writer 漂移）。
- **显式 migration（v1→v2）与 commit 协议**（r5 修——两个最终文件不可能一次 rename 原子，禁笼统声称原子）：①**内存**完成 run_id 生成 + view manifest 构建 + 全部 **stages backfill**（逐 accepted pointer 验文件存在、重算**真实存在**产物 hash、`StageRecordV1→V2` 逐条转换并按合同设 `artifact_contract="migrated_v1"`；缺 legacy sidecar = 登记合法缺省，**绝不伪造**）；②两个新文件写同目录 temp + fsync；③**提交顺序冻结：view_manifest.json 先落，RunManifestV2 最后落 = 唯一 commit point**——V1 loader **忽略孤儿 view_manifest**（清单在而 manifest 仍 V1 = 迁移未完成，只读语义不变）；重试 = 孤儿清单按 content_sha256 一致则复用、不一致则覆盖重写；崩溃恢复 = 幂等重跑或清理孤儿；任一步失败 = RunManifestV2 不落地，语义保持 V1 不动。
- **grandfather = 只读**：v1 run 仅允许 validation/replay/report（coverage 明示 N/A）；**任何创建/接受新 0_reading attempt 的命令（flow reading、resample、isolation merge）在 v1 run 上一律 BLOCK**，提示走显式 migration。
- 测试：v1 只读不写 / v1 resample 拒绝 / migrate 后可重抽 / v1 load-save bytes 不变 / backfill 逐 pointer 校验 + 缺 sidecar 合法缺省 / 未知 artifact 键拒 / 缺本合同必填键拒 / output 双 hash 不等拒 / **native V2 correction 报 base_v2 拒（交叉负例）/ 伪造 migrated_v1 与 provenance 不符拒 / 孤儿 view_manifest：V1 loader 忽略 + 重试 hash 复用/覆盖 + 崩溃恢复幂等**。
- **落批顺序（写回依赖表）**：本稿先落该共同 wire + claims.py；B2 消费 `StageRecordV2.artifact_hashes`——**DAG 加 B-M→B2 边**（登记 plan.md；上位 v2.2 批表原为并行根，此为细稿阶段依赖细化，非批范围变更；B2 不越界生成 view manifest）。

### 5.2 isolation run 绑定
- **正式（可 merge）builder 强制 `run_dir`**；`run_dir=None` 分支 = **preview/unbound 模式**：staging provenance 写入不可移除的 `merge_eligible: false`，`merge_isolated_output` 恒拒（tests/test_isolation.py:23-24,286-302 用法按新合同改写，简报点名）。
- **正式模式 staging immutable provenance 绑定**：`run_id` + case_id + `view_manifest_sha256` + case_metadata_sha256 + 逐图 image_sha256（build 前先 `verify_view_manifest`，缺失即拒建）。
- **merge 身份比较**：`run_id + case_id + view_manifest_sha256 + metadata/image hashes` 逐项相等（**不比较整份 run-manifest hash**——它随合法 StageRecord 更新变化，会让 in-flight workspace 无故失效，r3 消歧）；不等=拒。
- **merge 同门**：对 aggregate payload 调与 flat-flow **同一** coverage/schema checker（按 `expected_output_id` 对账 + ReadingView schema 解析）；**`report.blocking` 非空禁 accept——`accept=True` 入参不得覆盖**；pilot/partial 产物 = 未接受 partial attempt，不冒充完整 accepted 0_reading。
- 负例（八组）：empty views / missing entry / extra stem / tampered image / changed manifest / 无 run build 后 merge（恒拒）/ 为 run A build 并入 run B——**含"同 case 同图同 manifest、仅 run_id 不同"的 A→B 例** / build 后目标 manifest 被替换。

## 6. gate① 对账 check

`reading.view_manifest_coverage` = **`CheckLayer.INVARIANT`，所有 run_profile 恒 BLOCK**（r1 裁决：input identity/completeness 无豁免；`reading.present` 先例同层）：
- required_view（C2 恒 output_required）的 `expected_output_id` 缺产物 = miss（BLOCK）；
- 产物 stem 不在 expected 集合 = 身份错（BLOCK）；
- manifest 缺失/hash 不符 = BLOCK。
探索单图/pilot 走未 accepted partial attempt/独立工具模式，不进正式 DAG。denominator 层面的 miss 计分归 B4b，本 check 只管诚实性阻塞。

## 7. 消费者接缝登记（本批不施工）
Va（§3.5 公式 + opening×claim applicability 输入）、B4b（per-claim denominator + sidecar 绑 view_manifest_sha256）、B5b（归档 + assumed 桶只消费不再造）、E4（direction_semantics/azimuth 证据 + §3.4 sidecar）、judge（用 gt footprint + 本清单独立重算，绝不消费产品 coverage 产物，上位 E2'.5）。

## 8. 测试计划（累计全量）

1. **确定性**：同 case 连跑两次字节相同；改一图像字节→仅该 entry image_sha256 与顶层 hash 变；绝对路径永不出现；原子写并发半写。
2. **hash 纪律**：content_sha256 排除自身可复算；篡改任一字段可检出；case_metadata_sha256 解释链。
3. **sm21+sm20 双 fixture 全映射**：sm21 六视图（2 plan dimensioned + 4 elevation user/building_axis+standard_assumption）；**sm20 supplementary plan → typed required_view + expected_output_id=`supp_plan_view`**。
4. **生成期硬门逐条**（§4.3 全部，含未分类 BLOCK、路径逃逸、坏 metadata、partial、方向/id 重复、dimensioned 矛盾、derived 等价不符）。
5. **entry 身份四负例**：duplicate input_id / 同 stem 异路径 / expected_output_id 冲突 / provenance 悬空引用。
6. **方向三轴**：building_axis 填 resolved / true_azimuth 带角不填 resolved / unknown 全空；azimuth 域校验（有限 [0,360)）；direction_source 与 semantics_source 独立取值。
7. **负证据**：默认空 + 三受信来源开启 + coverage/assertion 必填联动 + **sm26 三反例 + 凹形四例语料**（B-M 侧锁语料与 schema 表达力；Va 逻辑本体归 Va 批）。
8. **gate① 恒 BLOCK 三态**（缺/多/hash 漂移）× exploratory 与 regression 同判。
9. **isolation 八负例**（§5.2）+ merge 强制 accept 被拒 + staging projection 只读（guard 拦写）+ 受信原件不在 staging + reader 可见性三负例（supp plan 可见但 output_required=false 生成期拒 / excluded detail 留 staging 被 builder 断言拦 / derived copy 哈希关系不符拒）。
10. **RunManifest/StageRecord 八例**（§5.1）+ v2 往返 + v1 兼容读。
11. **validate_case 只读**：验旧 anchor 零写盘、grandfather 分支 NOT_APPLICABLE。
12. **ResolvedViewDirection 接缝**：sidecar schema 校验 + 消费端拒缺/拒 hash 漂移。
13. **CompletenessAssertion wire**（§3.6）：三 source 正例 + 五负例。

## 9. 验收

- 全量测试绿 + **零 golden**（老 anchor 零写盘/零改动）；两处预期行为变化在简报向用户明示（非回归）：① `tests/test_isolation.py` 空 views 接受断言按新合同反转；② v1 run 拒新 attempt（C-03 硬门收紧）。
- sm21/sm20/sm24 三 case `build_view_manifest` 干跑 + sm21/sm20 人工抽查登记简报。
- 与 B2 耦合（r4 定案）：**B-M 先落** claims.py（内容以 B2 稿 §2.8 为准）与 RunManifestV2/StageRecordV2 共同 wire（本稿 §5.1 = 唯一规范 owner）；B2 消费。

## 10. 开放问题：无（r1–r4 全部裁决已吸收）
