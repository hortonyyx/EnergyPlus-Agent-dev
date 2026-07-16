# B4a Phase B 施工执行简报（terra）

## 范围与预检

- 唯一合同：`c2_b4a_detail_spec.md` v2；仅施工 Phase B（manifest-aware inspector、plan polygonize）及派单 PA-R1/PA-R2 束；未触碰 B4b 车道、Phase C/D、correction/Vg/Va、资产或管理文档。
- §14.5 preflight：PASS。`pydantic/shapely/ezdxf/PIL/OmegaConf`、`vg_for_direction/VisibilityTolerances`、`footprint_fingerprint`、`load_core_tolerances()` 全部可导入/执行；未安装或升级依赖、未改 lockfile。

## 改动映射

| 合同/派单项 | 施工与测试 |
|---|---|
| §8/§9 | `inspect_dxf.py` 改为严格 `--dxf/--manifest/--config/--vg-config` 只读 preflight；无 manifest 恒 UNBOUND（exit 2），manifest 路径做 hash/unit/selector/proxy/polygonize 检查，`--json-out` 仅可原子新建到非资产根。 |
| §10 Phase B | 新增 `gt_extraction.py`：显式 manifest 绑定、单位/affine、clip、axis/snap、Shapely dry-run polygonize、L/U 无洞 canonical ring、seed 驱动 footprint/zone 选择、zone tiling、source ancestry、跨楼层 footprint 一致性；只产 `PlanExtractionResult`，没有伪造 `GroundTruthV3`、opening、segment 或写盘入口。 |
| §13/§14 Phase B | 新增 `test_gt_extraction.py`：两层 L/U + zone 正例，dangle/bulge 拒例，无 manifest UNBOUND；扩展的 inspector 既有合成 DXF 回归保持。 |
| PA-R1 | 已有 resolved 相对 `parts` 形状保护与“新建 e2e case_data”负测复核为绿，未回退为依赖目录存在性的策略。 |
| PA-R2 | `wall_thickness_m` 去除合同外默认；删除 methods canonical 死码；生产 assert 改显式 fail；`compute_gt_implementation_hashes` 在 extractor 文件到位后正例固化；补 missing→None、bad JSON、bool/NaN/CW/nonorth/self-touch/hole/multipolygon 拒例，以及 `OmegaConf.load` 联合 monkeypatch 锁。稳定码 `gt_default_root_candidate_forbidden` 未改。 |

## r1 finding 闭合映射

| finding | 闭合 |
|---|---|
| PB-C1 | Phase B 对 `centerline` 明确 `dxf_centerline_unsupported_in_phase_b` 阻断；outer_skin 正例与 centerline 负例已测。 |
| PB-C2 | `gt_manifest.validate_manifest_view_clips()` 以 source-m 面积和 resolved topology tolerance 判重叠，inspector/extractor 入口均调用；交叠负测与直接 validator 探针已测。 |
| PB-C3 | 补 cut/proxy/unit/hash/view-overlap/seed 歧义，且 `test_inspect_dxf.py` 覆盖 CLI PASS/UNBOUND/内部错、json-out 新建/已存在；L/U、dangle、bulge 保持。 |
| PB-C4 | snap 明确拆 node-join 聚类与 axis-alignment 投影/短边/斜边；两值不同的行为分叉已测。 |
| PB-C5 | polygonize 诊断真实携带 dangle/cut/invalid count；cut 计数/阻断已测。 |
| PB-C6 | proxy 仅在 bound view 内 BLOCK，unbound/view 外只 INFO；bound proxy 阻断测已加。 |
| PB-C7 | zone seed 到 face boundary 必须大于 node-join；near-boundary 负测已加。 |
| PB-C8 | selector 实体触 clip edge 直接 `dxf_entity_clip_boundary`；负测已加。 |
| PB-C9 / PA-R2 残留 | CLI 先验证 json-out 再 stdout、使用真实 implementation hashes、INSUNITS ft 映射；Inf/真 self-touch/双 zone host 拒例已固化。TOCTOU 的新文件竞争窗口仅留 NIT 记录。 |

## 验收与测试

- Phase B extraction + inspector：13 passed。
- schema/manifest/PA-R：48 passed。
- 派单指定 Phase A 回归（discipline/from_dxf/render/overlay）：25 passed。
- 合计定向：86 passed；`git diff --check` PASS。
- 零资产扰动复核：本批改动文件为 `scripts/tool_scripts/inspect_dxf.py`、`src/agent/judge/gt_manifest.py`、`src/agent/judge/gt_schema.py`、`src/agent/judge/gt_extraction.py`、`tests/test_inspect_dxf.py`、`tests/test_gt_schema.py`、`tests/test_gt_extraction.py` 与本简报；没有 `gt.json`/DXF/PNG/golden 改动。并行 B4b 车道改动未触碰；未创建 commit。

## 预期行为、未决与审请

- inspector 不再把无 manifest 的 drawing 当可提取真值；plan core 遇 dangle/cut/bulge/clip/seed 歧义均 fail closed，绝无 largest-bbox fallback。
- Phase C 的 GT candidate、boundary segments、openings/elevation matching 与 Phase D render 均未实现，按派单留待后续单独施工。
- 偏差：centerline 在 Phase B 采取合同允许的稳定码拒绝，而非实施 §10.3.4 外偏；Phase C/D 项仍未实现，均为范围内显式留待后单。NIT：`--json-out` 对“不覆盖竞态新建文件”仍有 TOCTOU 窗口。review-ask：请复核上述 Phase-B 拒绝策略、clip-overlap 双入口和 CLI 合同。 

## 本批改动文件

- `scripts/tool_scripts/inspect_dxf.py`
- `src/agent/judge/gt_extraction.py`
- `src/agent/judge/gt_manifest.py`
- `src/agent/judge/gt_schema.py`
- `tests/test_gt_extraction.py`
- `tests/test_inspect_dxf.py`
- `tests/test_gt_schema.py`
- `AI_agent/logs/reviews/execution/2026-07-15_b4a_phaseB_construction_brief.md`

## r2 就地补丁（2026-07-16）

| finding | 补丁与测试 |
|---|---|
| PB-C10 | 当前环境实测 `polygonize_full` 返回 `(polygons, cut_edges, dangles, invalid)`；修正解包顺序。测试以真实 tail-dangle 断言仅 `dangle_count=1`，以两闭环 bridge-cut 断言仅 `cut_count=1`，两者均仍 BLOCK。 |
| PB-C11 | proxy 由四角采样改为 bbox 与 bound clip 的轴向相交判定，巨型包围 proxy 不再逃逸；bbox/extent 异常以 `dxf_proxy_extent_unavailable` BLOCK；view 外 proxy 产 `dxf_proxy_outside_bound_views` INFO。三条均有 repo 测试。 |

- r2 后偏差：centerline Phase-B 拒绝路线、Phase C/D 留待后单及诊断输出的 TOCTOU NIT 不变；PB-C10/C11 无残留。
