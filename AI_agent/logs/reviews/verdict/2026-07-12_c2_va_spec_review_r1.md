# Va 细稿 r1 交叉审判词（Fable 最高档，2026-07-12）

**对象**：`proposals/c2_va_detail_spec.md` v1（sol 次高档出稿，基座 `db651e3`）。
**结论：APPROVE-WITH-CHANGES —— 0 MAJOR + 2 MINOR + 1 NIT 束，出 v2（全文累计）。派 sol 同线程修订。**

## findings

- **VA-R1（MINOR，接缝失踪风险）**：B-M 批收口时登记的接缝「completeness 的 **user/dataset 两 source 生成通路**归 Va/B4b（case_metadata source 已通）」（plan.md B-M 条）在本稿**既未实施也未显式移交**——§1.2 Out 只字未提。Va 纯核无 I/O，不做生成是对的，但接缝登记点名了 Va，沉默会让这条通路失踪。v2 在 §1.2 显式声明：completeness user/dataset 生成通路**不在 Va 批**（与纯函数边界一致），**归 B4b 细稿承接**，并引接缝登记原文留痕。
- **VA-R2（MINOR，import 环）**：§10 要求「按仓库现公开面惯例导出 Va public symbols」——现 `correction/__init__.py` **确有集中导出惯例**（apply_deterministic_core/CorrectedGeometry/envelope），照做会构成包级环：`execution.view_manifest → from correction.claims import（触发 correction/__init__）→ facade_applicability → from execution.view_manifest import ViewManifest（此刻类未定义）`——任何**先 import view_manifest 的入口**（stage_runner、现有测试）将 ImportError。v2 改为：`correction/__init__.py` **不导出** Va 符号并写明环因，消费者直接 `from src.agent.correction.facade_applicability import …`；§11 加一条 import-order 回归测试（先 import view_manifest 再 import facade_applicability，两序皆可）。
- **VA-R3（NIT 束，措辞/失实四处）**：① §3.2 #5「family 的 Vg segments 所有 world intervals」须点名 **`world_along_interval`**（误用 visible_intervals 会在端部全遮挡段时算错 along_origin，且该错会被冻进 frame hash 校验）；② §6.3 #3「coverage=plan_floor_region/full_floor」应写成 `frame=="plan_floor_region" and region=="full_floor"`（frame/region 是 Coverage 两个字段）；③ §11.31「sm26 golden」不存在（sm26 anchor 未建），改「sm20/sm21 golden + 全部既有 anchor 零修改」（§11.21 的 sm26 语义**合成 fixture** 不受影响）；④ 七 claim 的 `target_world_interval` 语义上同为该窗沿面跨度——加跨 claim 相等断言（或写明允许不等的理由），防 caller 构造 bug 静默穿过。

## 亲核通过项（主控对实码/上位定案逐条验证）

1. **通道×属性矩阵**与 `claims.py` 实值逐项相等（plan={existence,host,along,width}，elevation={existence,along,width,sill,head,appearance}）。
2. **B-M resolved-direction 接缝**逐字段一致（B-M spec：`{input_id, resolved_building_direction, view_manifest_sha256, orientation_output_hash, adapter_version}`，"Vg/Va 只收 sidecar、缺失/漂移/不可唯一 fail closed"）——Va 不抢 E4 sidecar owner（review-ask #4 通过）。
3. `derive_view_projection_frame` **实码即拒非 bool mirrored**（isinstance 硬检查）+ XOR 翻转约定与 §3.2 #4 一致；`_is_mirrored` 宽松版属 legacy `derive_facade_frame`，本稿已禁用 legacy 路径。
4. `FacadeSegment` 字段（world_along_interval/depth/visible_intervals/source_footprint_fingerprint）、half-open 语义、`floor_ref` plan-only int 均与实码一致。
5. **existence fragment→applicable** 为设计 v2.2 §E2' 预授权（"跨 visible/hidden 边界的立面来源窗：存在性可立，证不到的完整宽/头高等 claim 单独 partial/NA"）（review-ask #2 通过）。
6. **正证据三分法**与 C-03 机读前提逐条对齐（potentially-observable=allowlist / 正向必须 opening×claim 声明 / completeness 只 gate 负证据；"完整性声明只来自受信 manifest，不来自被测产品"）；judge/executor 双独立 ledger 与 §E2'「judge 用 gt footprint+受信 manifest 独立重算、绝不消费产品 coverage」一致（review-ask #1 通过）。
7. C2 Coverage 词汇只有全覆盖档（region∈{full_floor,full_facade}），故「plan 负证据区间=target」在 C2 成立；C2.1 若引入部分 region 属 schema bump（§9 已留缝）。
8. **review-ask #3（预绑定 segment vs B4b 顺序）裁决=兼容**：Va 把 `facade_segment_id` 定义为判卷临时 target binding、不回写 Window 是对的；B5 前的产品侧绑定规则 + 无法唯一绑定的显式拒绝/NA 组合是 **B4b 细稿的义务**（gt 侧由 B4a 的 opening 段 ref 供给），本稿 §3.3 尾段已正确划界。
9. **review-ask #5 裁决=足够**：partial 只给精确区间 ledger、不冻结 0.5/权重，与 §E2'「sidecar 按 claim 分 denominator、score policy 归 B4b」一致。

## 放行

v2 并入三条后即定稿可作 B4b/Va 施工合同基础；无需 r2 全文复审，主控做 closure 快核即可。
