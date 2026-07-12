# B2b 细稿 r1 交叉审判词（Fable 最高档，2026-07-12）

**结论：APPROVE-WITH-CHANGES —— 1 MAJOR + 1 MINOR + 1 NIT，出 v2（全文累计）。GPT 限额重置后派 sol 同线程修订。**

## findings

- **B2B-R1（MAJOR，§0 开工门自相矛盾）**：§0"开工前必须机械断言"五条中后三条断言 `envelope_axis_attach_tol_m` 等**B2b 自己在 §8.1 才新增**的字段——照稿开工前必失败。v2 拆两段：B3 前置断言（开工前）：`coverage_area_tol_m2` + `correction.coverage` 语义；B2b 自有三容差断言（施工顺序步骤 1 完成后自检）。
- **B2B-R2（MINOR，§6.1 前置守卫 #7 评估时点矛盾）**：`envelope_topology_preserved` 需要候选模拟结果，却列在"候选副本写值前依次执行"清单里，且与 §6.2 post gate #8 重复。v2 写明：#7 于候选模拟后、写值提交前评估（或并入 post gates 并说明防御纵深意图），消除执行者歧义。
- **B2B-R3（NIT，签名数值默认与稿内纪律冲突）**：`dimension_chain_is_closed_for_endpoint(..., close_tol_m: float = DIMCHAIN_CLOSE_TOL_M)` 带默认值，而 §8.3 要求 private tol 参数"必填、无数值默认"。v2 二选一写死：豁免"A0 命名常量默认"（非裸字面量），或去掉默认。

## 亲核通过项（主控对实码逐字验证）

- §2.3 `check_coverage(geom: CorrectedGeometry) -> list[GeometryFinding]` 与 `geometry_validator.py:84` 实码签名一致；§2.1 Window/WindowV3 字段形状（span/z/room/floor_id/facade_segment_id/provenance）与 `schema.py` 实码一致。
- §1.3/§10.6 F1 两拒绝分支：legacy v2+polygon 原文保留+逐字节断言、v3 blanket reject 窄化后 unsafe 路径仍锁——F1 教训（安全拒绝必须有测试锁）全承接。
- §7 原子事务：候选深拷贝、fresh-copy 回滚、非预期异常传播+入参零 mutation、生产签名无故障注入开关。
- §9 容差纪律：三新容差命名+排序校验（attach ≤ endpoint ≤ reconcile）、`_SMALL_TOL_M` 升命名配置值不变、静态 grep 断言。
- 与 Vg 定稿时序相容：变形事务在 core 内、Vg materialize 在 core 后 → 事务时 facade_segments 恒空（draw 合同保证），§5.5 防御门为纵深非矛盾；两稿都改 `finalize.py` → **后落批次须 rebase 先落批次**（施工派工时注明，Vg 先行）。
- §4.2 producer 义务（reading guide 加 exact marker + producer-path 测试禁 fixture-only 正例）——真产线通路完整。
