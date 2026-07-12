# B2b 施工 r1 主控终审判词（Fable，2026-07-12，方案A：terra 施工 / Claude 侧终审）

**对象**：terra B2b 首轮交付（基座 `6df4398`，工作树未 commit；简报 [2026-07-12_b2b_construction_brief.md](../execution/2026-07-12_b2b_construction_brief.md)）。
**独立验证**：主控全量 pytest = **879 passed + 9 xfailed，零回归**（基线 876+9，+3 为本批新测）；逐行 diff 全读；review-ask 三条逐一亲核。
**结论：REWORK —— 3 MAJOR + 4 MINOR + 2 NIT。骨架成立（事务/门序/审计形状/容差纪律全对），但批次核心能力 §5.2 未交付，返工同线程继续。**

## MAJOR

- **B2B-C1（§5.2/§5.3 平面化图未建）**：`envelope_transform._intervals_for_component` 的 component 区间**只由 footprint 边构成**；细稿 §5.2#1 明文"输入 edges = footprint ring 边 + 每个 cell 的 polygon/bbox ring 边"、#2 在 T-junction/重叠端点分割、§5.3#2 必要时 materialize kink 顶点、#3 变形后去重复点/共线 degree-2 点再 canonicalize——均未实现。后果：**共线内墙经 T-junction 延伸出 footprint 边区间的形状会被硬门整体误拒**（fail-closed 方向对，但功能未交付）；细稿 §10 的 U 形 wing_break 旗舰场景（x=3.00→3.10、内墙随共享轴联动）大概率落在此类。修法=按 §5.2 建 per-floor 平面化图（cell 边进闭包+T-junction 分割+kink materialize+§5.3#3 清理），并用 U 形/T-junction fixture 证明"该成功的成功"。
- **B2B-C2（§5.4 窗后置拒绝缺失）**：变形后仅比对 host (floor,room,facade) 三元组与 span-in-host（经 re-resolve）；细稿明文的「**宽/高低于 min_edge_length_m 拒绝**」「**span 跨过 wing break 拒绝**」未实现（span 反转仅靠 strict validator 间接兜）。窗宽 0.35→0.05 的退化窗当前会被**静默接受**。
- **B2B-C3（§11 测试矩阵大面积缺失，terra 自报偏离 #2）**：逐 hard-gate 独立负例、v1/v2×五状态快照矩阵、U 形跨层 endpoint、T-junction materialization、window ambiguity 全族、§7.4 故障注入（monkeypatch 每门抛受控/非受控异常）均未落。C1/C2 修复必须连带这些 fixture 一起交，简报的章节→测试映射表同步补全。

## MINOR

- **B2B-C4（§7.3 conflict 分类坍缩）**：回滚 conflict 恒写 `conflict_type="facade_plan_mismatch"`、`claim_type="numeric"`；细稿枚举三值/两值——identity/ambiguity 类失败（window_host_unique、identity_snapshot、axis_attachment 多解）应映射 `reference_or_identity_ambiguity`，拓扑类失败 `claim_type="topology_identity"`。按门→分类映射落地+测试锁。
- **B2B-C5（§4.3 v3 证据级审计丢失）**：legacy 路径对 axis 级 conflict/skip 记 conflicts/unsupported（deterministic.py:652-658 留存）；v3 事务路径对 **axis 级 conflict/skip 与 endpoint 级 conflict resolution 均不记任何审计**（resolve 阶段直接丢弃）——细稿 §4.3"skipped/unsupported 按现有 audit 分类记录、evidence conflict 记 conflict"落空，证据静默蒸发。
- **B2B-C6（source_facade 子串猜测）**：`resolve_envelope_move_intents` 用 `name.lower() in source.view.lower()` 推 facade（"southeast" 会先命中 "South"）；应复用 `_view_facade` 词界正则或让 facade 随 EnvelopeCandidate 结构化携带。现有轴权门可兜大部分错配，但审计里的 source_facade 可能失实。
- **B2B-C7（frame_transform_hash preimage 偏离）**：实现 hash 全 vertex 列表；细稿 §4.2#5 写"投影 extent"。冻结前对齐（改 extent-only，或回细稿登记偏离理由）——该 hash 会进持久审计，B4b/B5 消费后再改= golden churn。

## NIT

- **B2B-C8**：Phase A 门执行序（实测 #4→#2→#3→#1→#5→#6）与细稿"按序 1→6"不一致，多故障输入的 `failed_gate_id` 会漂，审计可比性受损。
- **B2B-C9**：新 `_apply_envelope_reconcile` dispatcher 生产路径不调用（仅测试 import），且其 v3"立即事务"语义与生产核内"canonical 准备后、后置事务"时序不同——要么让核走 dispatcher，要么注释钉死 test-only shim，防漂移。

## 亲核通过项

1. **v2 polygon 安全拒绝分支原文保留 + 既有锁测试通过**（B2 批 F1 教训复核点）；v1/v2 全程走原 legacy helper，字节级行为未动。
2. **v3 矩形+非矩形统一事务** = 细稿 §2.1 明文要求（"禁双实现"），合稿。
3. **成功审计 §7.2 形状逐键核对一致**（含 intents 去 source_ids、moved 四桶、三容差名值来自 config、changes_topology）。
4. **三新容差**必填无默认 + `0<attach≤endpoint_match≤reconcile`、`agreement≤reconcile` 交叉校验 + `_SMALL_TOL_M`/`+1e-9` 裸字面量清零 + yaml/A0 登记。
5. **DIMCHAIN_CLOSE_TOL_M 迁 `src/agent/reading/constants.py`**，validator 与 B2b parser 共同 import，无第二份 0.010。
6. **wing marker 解析** = exact 三字段（boundary_ref/boundary_kind=="wing_break"/boundary_endpoint∈{from,to}）+ role==segment+chain_id+int order + 显式 `dimension_chain_is_closed_for_endpoint(..., close_tol_m=DIMCHAIN_CLOSE_TOL_M)` 无隐式默认；producer 义务已进 reading guide。
7. **review-ask #2 主体解决**：accepted-overall 的 in-memory extent 覆写**已实现**（`extract_authoritative_envelope` 深拷贝 projection_footprint 覆写极值，不回写 geometry）；残留=C7 hash preimage。
8. §7.4 异常边界正确（只捕 `EnvelopeTransformRejected`，编程错误上抛）；`set_cell_polygon_vertices` 重派生 bbox（§5.3#5）；window z 永不改；`before` fresh round-trip + deep-copy candidate + 单条 commit/rollback 符合 §7.1。
9. 主控独立全量 **879 绿 + 9 xfailed 零回归**；`git diff --check` 过；改动文件集与派发边界一致（无越界施工）。

## 处置

返工单发 terra 同线程：C1+C2+C3 为返工主体（连带 fixture），C4-C7 一并修，C8/C9 顺手。返工后主控再跑独立全量+复核 C1 fixture 真实通过（U 形/T-junction 必须"成功路径"通过而非 conflict 逃逸）。

---

## r2 闭案（主控复核返工 r1，同日）

**结论：CLOSED —— 九条 findings 全闭，B2b 批收录。**

- **独立全量 pytest = 903 passed + 9 xfailed，零失败**（基线 876 → 首轮 879 → 返工后 903；+24 为返工新增测试锁）。
- **C1 亲核**：`_floor_axis_edges` footprint+每 cell 共线边进闭包、传递吸收 T-junction/重叠端点（断开同坐标墙不并入）、per-floor 闭包+跨层同构校验（§5.1）、`_materialize_axis_splits` kink 顶点、degree-2 共线清理保留 deliberate kink；**U 形跨层 wing_break(3.00→3.10) 与 T-junction 内墙联动两条 fixture 均为成功提交路径**（committed=True、notch depth 轴逐值不动、bottom cell T-junction x 同步 3.1）。
- **C2 亲核**：窗 span/z < min_edge_length_m 显式拒 + span 跨 wing break 显式拒，两负例锁（`test_post_transform_window_min_width_and_wing_crossing_reject`）。
- **C3**：八 §6.2 门逐门回滚参数化 + §7.4 故障注入（非预期异常上抛零 mutation）+ v1/v2×{none,accepted,skipped,conflict,over-tol} 五状态矩阵 + endpoint marker producer 路径测试全落；简报映射表补全。
- **C4**：`_conflict_shape` 门→(conflict_type, claim_type) 三值/两值映射 + identity 分类测试。**C5**：`_append_evidence_audit` v3 axis skip/conflict/over-tol + endpoint conflict 按 legacy 同类落 conflicts/unsupported + axis conflict 测试。**C6**：改用词界 `_FACADE_RE`，"Southeast"子串误认有拒绝测试。**C7**：frame hash preimage 改 canonical `projection_extent`（x/y 极值）。**C8**：Phase A 序对齐（schema→evidence/intent→binding→host→attachment）。**C9**：生产 v3 late dispatch 统一走 `_apply_envelope_reconcile` dispatcher，时序注释钉死。
- F1 教训复核点二次通过：v2 polygon 拒绝锁测试原文保留；原 v3 blanket-reject 测试正确翻转为"blanket 拒绝已移除"断言。
