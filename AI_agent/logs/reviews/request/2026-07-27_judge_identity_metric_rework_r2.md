# 返工单 r2 · 判卷器「数值身份 + 计分度量」收尾两项（2026-07-27）

- **施工** = GLM-5.2（续 r1）· **复审** = sol · **主控** = Opus 5
- **前置** = `32c173a`（r1 主体 + neuter 自查 + 真锁补齐，全仓 **1710 绿 + 10 xfail**）
- **本单范围 = 只做两项**：r1 自查表里诚实标为 PARTIAL 的 ⑥ 与 ⑦。**施工主体不要重做。**

---

## 0. 主控裁定

r1 续作的诚实纪律**做对了**（不再宣称零 false-lock、自查中主动暴露自己漏钉的 GT 侧码锁并补真、两项未达成如实标 PARTIAL）。这一轮只收尾。

**裁定：⑥⑦ 两项都做，不接受 PARTIAL 结项。**

- **⑥（W5 接线）= 必做**。这不是"缺个锁"，而是 sol 的 **R-4 活体反例现在仍然成立** —— 生产判合法、判卷判非法的形态还在代码里，**真实 case 仍会撞假红**。而消灭这个形态正是本批立项的初衷。
- **⑦（N-1 e2e 链路锁）= 一并做**。当前架构理由成立（sol 独立验证 interior key 与 facade id 集合交集为空）故无实际风险，但缺锁 = 基线 §3 点名的「门是真的、锁是缺的」原型。既然开一轮，顺手焊死。

---

## 1. ⑥ W5 共享正交判据真接线（死骨架）

### 1.1 病灶（主控已定位到行）

| 端 | 位置 | 现在怎么判 |
|---|---|---|
| 生产 | [cell_geometry.py:164](../../../../src/agent/correction/cell_geometry.py#L164) | `if dx > _EPS and dy > _EPS:` → 拒。即「dx 或 dy ≤ 1e-9 就算轴对齐」 |
| 判卷 | [segment_score.py](../../../../src/agent/judge/segment_score.py) `_pair_interior_edges` 分流 | `p1[0] == p2[0] or p1[1] == p2[1]` → **精确相等** |

**两把尺子不同 ⇒ sol 的活体反例**：cell A 共享边 `dx=5e-10`、cell B 反向共享边 `dx=4e-10`
- 生产：`5e-10 ≤ 1e-9` ⇒ 合法，`validate_corrected_geometry` 五项全 GREEN
- 判卷：`5e-10 ≠ 0` ⇒ 不进正交路径 → 落 general 路径 → 要求**精确反向**配对 → A 的 `5e-10` 与 B 的 `4e-10` 不精确反向 ⇒ **抛 `score_product_identity_invalid`**

⇒ **判卷器拿自己的精确性上限，宣判生产已判合法的几何非法。**

### 1.2 照此改（三步）

**步骤 1 · 生产端真调共享函数**
[cell_geometry.py:164](../../../../src/agent/correction/cell_geometry.py#L164) 改为调用 `edge_is_axis_aligned(dx, dy)`（语义等价：`not (dx>eps and dy>eps)` ≡ `dx<=eps or dy<=eps`）。
**当前只 import 了常量 `ORTHOGONALITY_EPSILON as _EPS`、自己重写了判据** —— 这正是 sol 说的"没接线"。**判据本身必须来自共享模块，不是各自复制一遍。**

**步骤 2 · 判卷端用共享判据分类，并把「量不了」和「非法」彻底分开**
`_pair_interior_edges` 的 ortho/general 分流改用 `classify_edge_orthogonality`：
- `axis_aligned`（精确 0）→ 走现有正交 T 切分路径，**不变**。
- `near_orthogonal_advisory`（0 < min(dx,dy) ≤ 1e-9）→ **生产已判合法，判卷器精确路径量不了** ⇒ 走 **unsupported / capability NA**，**绝不允许抛 `score_*_identity_invalid`**。
  - 表达方式用既有机制：`score_unsupported_combination` + `scoring.capability` 门（[score_service.py:153](../../../../src/agent/judge/score_service.py#L153) 已有先例），或等价的 capability NA 路径。**不要发明第三套。**
  - **判据只有一条**：这条边生产端认不认？认 ⇒ 判卷器最多说"我量不了"。
- `non_orthogonal`（两者都 > 1e-9）→ 生产端本就会拒，判卷端此时报 identity invalid 是**正确**的（上游根本不该产出它）。

**步骤 3 · advisory 必须有运行时产物**
R-4 要求「本批只加 advisory」。当前 advisory **没有被记录、传播或写进任何结果** ⇒ 等于没加。必须让 `near_orthogonal_advisory` 的命中**落进运行时可见的地方**（计数/审计字段/结构化日志任选其一，但要能在真实 run 后回答「这次跑有没有命中、命中几条」）——因为下一阶段「两次真实 run 零命中后翻 blocking」的判据就靠它。**本批仍不得翻 blocking。**

### 1.3 验收锁（缺一不可）

1. **R-4 活体反例锁**：sol 的夹具（cell A 共享边 `dx=5e-10` / cell B 反向 `dx=4e-10`）⇒ 断言 `validate_corrected_geometry` 五项全 GREEN **且** 判卷器**不**抛 `score_product_identity_invalid`（走 unsupported/NA）。**当前这条必红。**
2. **对照锁**：把 B 顶点改成与 A 相同的 `0.5+5e-10`（sol 已验此形态生产仍 GREEN）⇒ 判卷器正常抽出 1 条内墙、正常出分。证明步骤 2 没有把合法形态一律打成 NA。
3. **非法形态仍红**：`non_orthogonal` 边（dx、dy 均 > 1e-9）⇒ 生产拒 + 判卷 identity invalid，**错误码逐字不变**。
4. **接线锁（指定 neuter）**：把 `classify_edge_orthogonality` / `edge_is_axis_aligned` 首行改 `raise` ⇒ **必须有生产路径测试变红 + 有判卷路径测试变红**。
   ⚠️ r1 自查表 ⑥ 的实测结果是「全仓仅单元测试红、**0 生产路径红**」—— 这次要的就是把这个数字从 0 变成非 0。
5. **不变量 #4 不破**：`orthogonality.py` 仍零 judge import、零 gt import。

---

## 2. ⑦ N-1 窗宿主 e2e 链路锁

派工单 §5-B 出口 2 与返工单 §6 的正式出口，r0/r1 两轮都没交付。

**补一条完整链路锁**：correction window → facade multi-span → `assign_openings` → `build_correction_host_resolver` / claim。
- 夹具必须是**正式的 correction window**（不是直接调 `_resolve_facade_product_to_gt` 的单元夹具），需要构造 `VerifiedWindowHostProof` 全链（r1 日志已把这条路径写明）。
- **既有窗夹具全是单段** ⇒ **多段覆盖夹具必须新造**。

**指定 neuter**：把 [score_service.py:230](../../../../src/agent/judge/score_service.py#L230) 的 `product_to_gt.update(...)` 改成只调 helper、不接入消费端 ⇒ **新锁必须变红**。
⚠️ r1 自查表 ⑦ 的实测结果是「全仓 **0 红**」—— 这次同样要把 0 变成非 0。

---

## 3. 纪律与交付

- 纪律全部沿用[原派工单 §1](2026-07-27_judge_identity_metric_construction_dispatch.md)：`case_tests/test_baseline/gt/` 一字节不许动 / 不改 `AI_agent/CLAUDE.md` / 不在仓库根落文件 / neuter 只在 `/tmp` 副本做且工作树还原。
- 基线 **1710 绿 + 10 xfail**，零回归。
- 执行日志续写 r2 节：两项各自的**指定 neuter 实测结果**（尤其 ⑥-4 与 ⑦ 的"红了几条、红在哪"）+ 全仓输出 + 两次 `git status`。
- **诚实纪律**：r1 你做对了——继续。做不完精确标 PARTIAL 说明卡在哪，**不要自行判定等价**。
- 完成后回报主控 → sol 复审（同席位续审，它已有本批完整上下文）→ 主控轻门。

## 4. 一句话

⑥ 不是补锁，是**把「判卷器宣判上游几何非法」这条路彻底堵死** —— 本批立项就是为了这件事。判卷器唯一被允许说的是「我量不了」。
