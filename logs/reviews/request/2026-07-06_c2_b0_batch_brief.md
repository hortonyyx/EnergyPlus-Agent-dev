# C2 · B0 批执行简报（schema_version 真机制 + profile 线程化 + parent-wall 唯一归属 + 覆盖门 helper 收敛）

- **日期**: 2026-07-06；**依据**: [proposals/c2_orthogonal_polygon_design.md](../../../AI_agent/proposals/c2_orthogonal_polygon_design.md) D1/D4(前半)/D5(helper 部分)/D8 B0 行/D10#4#7，细节冲突以 `logs/reviews/verdict/2026-07-06_c2_design_review.md` 为准。
- **流程注记**: 设计已过 Codex 审(D10 定案)；本批简报由 Claude 从定稿设计直接派生，Codex 在执行前先对照设计文档+verdict 审一遍简报（发现越界/漏项先报再动手），审+执同线程——周额度收尾的合规变体，痕迹记执行日志。

## 范围（仅此四项）

1. **D1 · `schema_version` 机制**：`CorrectedGeometry` 根加 `schema_version: str = "1"`（缺省 "1"=现行矩形制）。分发规则：确定性核、几何内核入口、gate① 读它——`"1"` 走现行路径（字节级不变）；未知版本 → 新 gate① check `correction.schema_version_supported` **INVARIANT fail（拒绝静默降级）**。`"2"` 的启用路径属 B1+，本批只建机制。bump 规则按 D1 落 A0 注册（凡新增几何槽位必 bump）。
2. **D1 · `capability_profile` 线程化进内核**：内核入口（`build_zone_volumes`/`split_pairing` 顶层）感知 profile；规则 = profile 允许的形状 ⊇ 数据声明的形状，否则 gate① fail。新 profile 值 `orthogonal_polygon`（`rectangular` 仍默认）。**D10#4：须含 `run_stage.py` 与几何 builder 全部入口**。
3. **D4 前半 · `_find_parent_wall` 唯一归属修复（C1 正确性，独立可提前项）**：废"静默选最后 match"——同朝向候选墙集合按"窗世界坐标落入墙段 span"唯一归属；歧义（跨两段/落缝上）→ kernel gate fail 而非静默。**"沿宿主墙段参数化区间"的半步留 B5 不做**。D10#7 预扫在案：28 份 correction 产物归属 0 歧义 = 行为安全；sm24 一份 raw correction 现行 attachment 已失败 = 既有事实非本批引入。
4. **D5 部分 · 覆盖门 helper 收敛双写**：kernel checks 与内核主路径的重复实现（含 by_floor 邻接双写，体检 C3#7）收敛到单一共享 helper——**纯重构、行为字节级不变**；覆盖门 v2 的 block 语义属 B3 不做。

## 明确不做（越界即停）

Cell.polygon（B1）/ footprints（B2）/ 覆盖门 v2 block（B3）/ gt·scorer 线段化（B4）/ facade_segments+接线（B5）/ skill·prompt 词汇（B6）/ IntakeOutput 契约、reading schema、correction prose（D7）。

## 验收

- 全量 pytest 绿 + 零 golden 改动（逐批断言）。
- **v1 数据字节级行为不变的回归断言**（各层 footprint 相同、schema_version 缺省、rectangular profile 下：几何产物与现行一致）。
- 新增针对性测试：① schema_version 缺省="1"、未知版本 INVARIANT fail；② profile ⊉ 数据形状 → gate fail、`orthogonal_polygon` 接受 v1 数据；③ 合成歧义窗（落两墙段缝上）→ kernel gate fail；④ helper 收敛后 checks 与主路径同输入同输出。
- 新 check 自动进 parity 锁范围（M1 机制），新常数/规则 A0 登记、禁裸字面量。
