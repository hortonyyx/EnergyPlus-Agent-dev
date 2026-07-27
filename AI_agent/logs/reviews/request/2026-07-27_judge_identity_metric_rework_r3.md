# 返工单 r3 · 判卷器「数值身份 + 计分度量」（2026-07-27）

- **施工** = GLM-5.2（续 r2）· **复审** = sol · **主控** = Opus 5
- **前置** = `7c17998`（全仓 **1715 绿 + 10 xfail**）
- **依据** = [sol 复审裁决书 r2](../verdict/2026-07-27_judge_identity_metric_sol_r2.md)（REWORK · 2 BLOCKER / 2 MAJOR）

---

## 0. 主控裁决与范围

sol 的 4 条 findings **全部成立**，主控独立核实要点见下。**但本单只做三项**，第四项（R2-B2 来源身份合同）**移出本批、另行立项**——理由在 §4，这是主控的范围裁定，不是你可以自行降级的项。

**本单范围**：R2-B1（新引入的假绿，最紧急）+ R2-M1（守恒硬门留了容差窗）+ R2-M2（N-1 链路锁只钉了一半）。

---

## 1. R2-B1 死骨架 · 混合缺陷的优先级（本单最重）

### 1.1 病灶

r2 为修 R-4 把 advisory 配对提到了正交拓扑门**之前**。后果（sol 活体实证，生产五项全绿的正式 `CorrectedGeometryV3` 上可达）：

| 输入 | 判卷结果 |
|---|---|
| 只有 1e-9 真缝 | `score_product_identity_invalid` / `scoring.input_identity` ✅ 正确判红 |
| 同样的 1e-9 真缝 **+ 一条未配对 advisory 边** | `score_unsupported_combination` / `scoring.capability` ❌ **整轮 NA、不出分** |

⇒ **产品只要额外画一条 5e-10 的斜边，就能让自己的真拓扑破洞免于判红。** 这是本批 r0「4 m 墙拿 8/8」之后**第二次**把假红修成假绿的换位。

### 1.2 照此改：先收集诊断，再按优先级裁决 —— 不是换顺序

**⚠️ 不要简单把两行顺序换回 tile-before-advisory。** sol 已验证那样会让同一输入报 `exterior_duplicate_owner`（advisory 边的扰动传播到相连外墙边），也就是 r2 施工时遇到的「第二张脸」。**两种顺序各有一种错，说明问题不在顺序，在于「谁先跑谁定案」这个结构。**

**正确结构（三步）**：

1. **收集，不立即抛**：把配对过程中遇到的问题收成**诊断列表**（每条含：类别 + 错误码 + 门 id + context），而不是遇到第一个就 raise。
2. **按类别裁决优先级**（硬规则）：
   - **`identity` / `topology` 类（真破裂）> `capability` 类（判卷器量不了）**。
   - **只要存在任何一条 identity 类诊断，整轮必须以 identity 码红**，绝不允许被 capability NA 掩盖。
   - 只有在**零** identity 类诊断时，才允许以 capability NA 收场。
3. **同类内取最精确**：若同为 identity 类，优先报最贴近根因的那条（如真缝的 `invalid_interior_edge_pair` 优于被 advisory 扰动出来的 `exterior_duplicate_owner`）。这条是 **nice-to-have，不是硬门**——做不到就报任一条 identity 码，但**不许因此退回 NA**。

### 1.3 顺带修（sol 同源发现）

`_log_advisory_hit` 只在**配对成功后**调用 ⇒ **真正触发 unsupported 的未配对 advisory 边不进日志**。而 R-4 下一阶段「两次真实 run 零 advisory 命中后翻 blocking」的计数，最需要的恰恰是这些命中。**未配对 advisory 也必须进可计数的运行时产物。**

### 1.4 验收锁（混合缺陷优先级锁，缺一不可）

用 sol 裁决书 §2 R2-B1 给的活体构造（footprint `[0,4]×[0,10]`，cell A 右边 near-vertical advisory 底 `x=2.0` 顶 `x=2.0+5e-10`，B `y=[0,5]`，C `y=[5+1e-9,10]`）：

1. **只有真缝** ⇒ identity 红，错误码逐字不变。
2. **真缝 + 未配对 advisory** ⇒ **仍是 identity 红，不许降级为 capability NA**。（当前必红。）
3. **只有未配对 advisory、无真缝** ⇒ capability NA（`score_unsupported_combination`）。证明没有把合法的 NA 形态一律打成红。
4. **指定 neuter**：把优先级裁决规则反转（capability 优先）⇒ 第 2 条锁必须变红。

---

## 2. R2-M1 · 守恒硬门补完整

B-1 的大额重复记功**已堵住**（sol 独立验证：4 m 活体现在响亮拒绝；摘掉拒绝门后第二道防线也只给 `4 m pass + 4 m miss`，不复发 8 m）。**但返工单 r1 §1 要求的「负 extra 必须抛错，不许静默归零」没有兑现。**

现状：先允许 `covered <= obs_length + 1e-9`，随后 `extra = obs.length - covered; if extra > claim_complete_epsilon_m:` ⇒ **容差窗内的负数仍按 r0 的同一形状被吞掉**。sol 活体实测：`obs_length=4.0 / covered=4.0000000005 / extra_rows=0 / delta=5e-10`。

**必做**：
1. **任何** `covered > observation.length` 与**任何**负 extra ⇒ 响亮拒绝，不留容差窗。
2. 补 **per-target 硬门**：`passing + failing == target.length`，在代码里 raise。
3. **锁必须走 `match_plan_segments` 接线**，不许再用直调 helper 只钉 `8.0 > 4.0 + tol` 代替（现有锁就是这个形状）。

---

## 3. R2-M2 · N-1 链路锁补另外两半

`:230 → assign_openings` 的接线锁**是真锁**（sol 独立验证断线即红）。但另外两半没交付：

1. **仍是单段夹具**：`_n1_gt` 把 bundle 的 4 个 facade segment 包回 GT（North/South/East/West 各一），窗只在唯一 South segment 上 ⇒ **仍是单段包含**，不是「同一 facade 多 GT span / 产品 span 跨段」。
   sol 实测：把唯一候选门 `len(candidates) == 1` 弱化为 `if candidates`，两个相关文件 **82 passed 全绿** ⇒ **没有任何夹具走到多 candidate 分支**。
   （注：旧 straddle 夹具用相邻 `[0,2]/[2,4]` 对产品 `[0,4]`，在「完整包含」候选定义下其实是 **0 candidate**，不是 >1。）
2. **只断言 `extras == ()`，没断言 host claim 结果** ⇒ sol 实测让 host resolver 对所有窗恒回 `"miss"`，该测试**仍 1 passed** = host claim 部分是假锁。

**必做**：新造**真正同 facade 多 span** 的正式 `VerifiedWindowHostProof` 窗夹具，走 `score_typed_attempt → assign_openings → build_correction_host_resolver → score_opening_claims_v3`，**逐字断言 host claim 为 `complete`**（或点名的 fail-closed 结果）。
**两条指定 neuter 各自必须变红**：① 唯一候选门弱化为 `if candidates`；② host resolver 恒回 `"miss"`。

**关于 renderer stub**：sol 判定**可以接受**（host resolution 与 claim scoring 在 renderer 之前执行，画图不反向参与判定）。锁效力被削弱的原因是单段夹具 + 弱断言，**不是** stub。这条不用改。

---

## 4. 移出本批：R2-B2 来源身份合同（主控范围裁定）

**指控成立且严重**。主控独立核实：
- [segment_score.py:78](../../../../src/agent/judge/segment_score.py#L78) `_cluster_axis(raw_values: Iterable[float], ...)` —— 只收浮点值。
- [segment_score.py:133](../../../../src/agent/judge/segment_score.py#L133) `_build_floor_identity` 把点展平成 `(float(p[0]) for p in materialized)` ⇒ **来源身份在进聚类器之前就丢光了**。
- `score_identity_contract_mismatch` 全仓**只在码表出现一次**，零 raise、零输入版本、零负锁。
- 合同④ 的非相邻重复顶点 / 归并后自触自交 / 同 owner 反向配对**全部静默接受**（sol 活体：`(0,2)` 重复顶点 + `(0,2)→(2,2)→(0,2)` 回折边，两条反向边同属 zone `Z`，当前产出一条 `zone_ids=("Z","Z")` 的"内墙"）。

**⇒ 移出本批的理由（主控裁定，不是降低要求）**：
1. 这**不是补锁，是跨层重构** —— 要把来源身份（`(floor_id, zone_id, vertex_index)` 等）穿透 GT / correction / reading 三种数据结构一路传进聚类器，涉及的是数据流形状，不是某个函数的判据。
2. **返工单 r1 §2 已经给过一次死骨架，两轮都没落地，且 r1 自查表未将其标为 PARTIAL** ⇒ 施工方**误以为已完成**。同一条在同一档位上连续两轮不达，继续原地重派不会有不同结果。
3. 本单其余三项是**当下真实风险**（R2-B1 是活的假绿路径），不应被这条重构阻塞。

**⇒ 处置**：单独立项，**派工由用户拍板**（可能需要更高档执行档或拆成多轮）。**本单施工方不要碰这条**——不要"顺手做一点"，半成品的来源身份传递比没有更危险。

---

## 5. 纪律与交付

- 纪律沿用[原派工单 §1](2026-07-27_judge_identity_metric_construction_dispatch.md)：`gt/` 一字节不许动 / 不改 `AI_agent/CLAUDE.md` / 不在仓库根落文件 / neuter 只在 `/tmp` 副本做且工作树还原。
- 基线 **1715 绿 + 10 xfail**，零回归。
- 执行日志续写 r3 节：三项各自的**指定 neuter 实测结果**（红了几条、红在哪）+ 全仓输出 + 两次 `git status`。
- **诚实纪律**：r1 续作与 r2 你都做对了（如实标 PARTIAL、自查中主动暴露自己漏钉的锁）。**继续这样。** 特别地：**如果 §1 的优先级裁决你实现后发现某条验收锁过不了，如实说过不了**，不要调整锁去迁就实现。

## 6. 一句话

本批已经两次把假红改成假绿（r0 的 4 m 墙拿 8/8、r2 的真缝洗成 NA）。共同形状都是**判卷器在"该判红"和"该说量不了"之间站错了边**。§1 的优先级规则就是把这条边界一次性焊死：**只要存在真破裂，就必须红；capability NA 只配在完全没有真破裂时出场。**
