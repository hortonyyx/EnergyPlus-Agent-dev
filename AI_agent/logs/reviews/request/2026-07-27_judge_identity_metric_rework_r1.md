# 返工单 r1 · 判卷器「数值身份 + 计分度量」（2026-07-27）

- **施工** = GLM-5.2（续上轮，返工轮免重拍）· **复审** = sol（同席位续审）· **主控** = Opus 5
- **返工依据** = [sol 裁决书](../verdict/2026-07-27_judge_identity_metric_sol.md)（REWORK · 2 BLOCKER / 4 MAJOR / 1 MINOR）
- **上轮产物** = `29a1ce0`（**不回滚**，在其上续作）

---

## 0. 主控裁决

**sol 的 7 条 findings 全部成立，无一驳回。** 主控独立复核要点：

- **B-1 主控独立读码确认，且比裁决书描述更糟**：[segment_score.py:516](../../../../src/agent/judge/segment_score.py#L516) 外层逐 target 独立循环、`exactly_one` 每个 target 内重建 ⇒ 同一条产品墙在多个 target 循环里各记一次功；[:551](../../../../src/agent/judge/segment_score.py#L551) 的 `obs_covered` 在 sol 夹具下累加到 **8.0 > 产品墙自身长度 4.0**；[:571](../../../../src/agent/judge/segment_score.py#L571) 算出 extra = **−4.0**，被 `> claim_complete_epsilon_m` 静默吞掉。**全程零守恒检查。**
- 上轮把假红修成了**假绿**——后者更危险：假红看得见（有人会来问为什么判红），假绿无声。

**⚠️ 本单的 §1、§2 是主控给的死骨架，不是建议。** 上轮三条最重的缺陷都源于「机制选对了、但边界条件自己猜」，这轮不留猜的余地。骨架之外的实现细节仍归你判断。

---

## 1. B-1 死骨架 · 覆盖必须守恒且支撑线唯一

**病根**：当前「联合切点」只在**单个 target 内部**成立。基线 C-1′ 要求的是**产品向答案单向配准**，而实现里产品段从未被注册到唯一的答案支撑线，于是一条几何可以在多条平行支撑线上重复赚长度。

**照此重建，三步顺序不可换：**

**步骤 1 · 单向注册（产品 → 答案，永不反向）**
每条产品段先解析出它**唯一**归属的答案支撑线：
- 候选 = 所有满足既有判卷容差（`plan_axis_alignment_tol_m` + `plan_position_tol_m`）且投影区间有正重叠的答案支撑线。
- **恰好 1 条** → 注册。
- **0 条** → 该产品段全长记 `no_extra_walls`（多画）。
- **≥ 2 条** → **响亮拒绝，新增分码**（见下）。**不许选最近的、不许都算、不许取第一个。**

> **为什么 ≥2 是拒绝而不是选最近**：两条答案墙相距 0.2 m 而判卷位置容差是 0.3 m，此时判卷尺本身分不开这两道墙。按基线 R-4，判卷器此时**只许说「我量不了」（unsupported），不许替上游做决定**。选最近 = 判卷器拿自己的尺子替用户裁决建筑语义，正是本批要根除的病。

**步骤 2 · 每条支撑线内做联合切点**（现有算法，保留），但只对已注册到该支撑线的产品段做。

**步骤 3 · 守恒不变式（硬门，必须在代码里 raise，不是断言注释）**
- `sum(每条产品段被记的 cover) <= 该产品段自身长度 + tol`，违反即抛。
- `extra` 计算前先断言 `obs_covered[key] <= obs.length + tol`；**负 extra 必须抛错，不许静默归零**（当前 `> epsilon` 把 −4.0 吞掉了）。
- 每条答案墙：`passing + failing == 墙长`（既有守恒断言延伸到长度口径）。

**验收锁（缺一不可）**：
1. sol 的活体夹具（GT footprint `[0,2]×[0,4]`，三 zone x 区间 `[0,1]/[1,1.2]/[1.2,2]` ⇒ 两道 4 m 内墙 x=1.0 与 x=1.2；产品两 zone、唯一内墙 x=1.1、长 4 m）——**当前得 `8/8 pass`，返工后必须响亮拒绝或产生 4 m miss，绝不允许 8 m passing**。
2. **守恒锁**：构造 `covered > product_length` 的输入，断言抛错。**摘掉守恒 raise 这一行，这条锁必须变红。**
3. 正常间距对照锁（两道答案墙间距 > 2× 位置容差）：仍正常出分，证明步骤 1 没有过度拒绝。

---

## 2. B-2 死骨架 · 「意图」来自来源身份，不要发明新输入格式

**sol 的诊断正确**：合同 ①/② 需要知道两个出现值是「同一意图」还是「不同意图」，而 `_cluster_axis` 只有距离，于是用距离反推意图 = 循环假设。

**主控裁定：意图身份 = 来源身份，它在输入里本就存在，不要造新格式、不要改 GT schema、不要要求上游多传字段。**

同一个坐标值的每次「出现」，都能机械地追溯到它的来源：
- polygon 顶点 → `(floor_id, zone_id, 顶点索引)`
- boundary segment 端点 → `(floor_id, segment_id, 端点侧)`
- reading/correction observation 端点 → 同理

**合同①（同意图必合并）**：同一来源的同一个坐标在管线里被读取多次时，其全部出现值的直径必须 < 合并阈。这是可机械验证的——不需要任何人声明"意图"。
**合同②（异意图必分开）**：不同来源的两个坐标，若最小距离落在 (合并阈, 分裂阈] 即护带内 → 响亮拒绝；若 < 合并阈 → 它们会被焊成同一原子，此时必须检查**是否造成 owner 重数冲突 / 零长边 / 环自交**（合同④），有则拒绝。

> 若你实测发现某条合同在现有输入结构下**确实无法机械验证**，**停下上报主控**，不要自行降级为"假设"。上轮就是在这里自行降级的。

**合同③（无距离落护带内）**：已实现，保留。
**合同④**：当前只覆盖 polygon 相邻顶点坍缩。必须扩展到：boundary segment、reading segment、**非相邻**重复顶点、归并后环自交、owner 重数冲突。
**合同版本不匹配**：当前完全缺失，须落地。

### 2.1 直径阈主控裁定（不许再自选）

当前 `merge=1e-12` / `diam=1e-11`。**直径守卫阈大于合并阈 ⇒ 守卫形同虚设**：链式桥接可以让簇直径长到 1e-11 而不触发守卫，正是 sol 反例 1（三个相邻 gap 各 < merge、总直径 1.8e-12 > merge，静默合并仍 GREEN）。

**裁定：`diameter_threshold` 必须 ≤ `merge_threshold`**，即簇直径不得超过"同一意图允许的最大分散度"本身。取 `diam = merge = 1e-12` 或更严。
`merge=1e-12` / `split=1e-11` 两个数字**保留**（sol 独立复算余量成立：合并侧对实测漂移 562×、对 20 m 单 ulp 281×；分裂侧对 1e-9 缺口 100×）。**只改直径阈。**

---

## 3. R-5 分码落地（A3 / A2 连带）

当前所有身份层失败都归到 `score_gt_identity_invalid` / `score_product_identity_invalid` 两个顶层码，差异只放在 `context["reason"]` —— 不满足基线 R-5「分码」。

**必做**：
1. 在 [score_schema.py:46](../../../../src/agent/judge/score_schema.py#L46) `STABLE_ERROR_CODES` 新增稳定分码，至少覆盖：非有限值 / 护带内歧义 / 链式桥接超直径 / 归并致边坍缩 / 合同版本不匹配 / **§1 的支撑线注册歧义**。门表 [:51](../../../../src/agent/judge/score_schema.py#L51) 同步。
2. **上下文必须记录被合并的原始 binary64 对（hex）与精确直径** —— 当前只记代表点的一个 x hex，事后无法复现判定。
3. **A2 两侧分别钉顶层精确 code**：答案侧 `score_gt_identity_invalid`、产品侧 `score_product_identity_invalid`，断言 `caught.value.code ==` 精确串。sol 已证明当前把 GT 侧码改成产品侧码，三条相关测试仍全绿。

---

## 4. 假锁重做（M-1 / M-2 / M-4）

**这三条的共同形状 = false-lock（假绿的近亲）：门是真的、锁是假的。** 上轮执行日志声称「21 条锁全部经 neuter、零 false-lock」，sol 用四组 neuter 证伪。

**M-1 · A8 重写**（[test_judge_identity_metric.py:257](../../../../tests/test_judge_identity_metric.py#L257)）：
- 两种产品必须携带**不同的 sub-merge 近邻值**（当前两产品提供给池的相关坐标值相同，即使真的非法联合建池也不会移动答案代表值 ⇒ 夹具无鉴别力）。
- 比较改为**答案原子序列的规范字节 + `denominator` 的 binary64 字节精确相等**（`struct.pack(">d", …)`），**去掉 `pytest.approx`** —— 基线 C-1′ 要的是逐字节，`approx` 放过了 sol 实测的 `4.0` vs `3.9999999999995` 污染。
- **指定 neuter**：在 match 内插入 GT+产品联合建池（基线明令禁止的情形），这条锁必须变红。

**M-2 · P-1(b) 恢复**（[test_c2_b4b_phase_b.py:166](../../../../tests/test_c2_b4b_phase_b.py#L166)）：
- 恢复 overlong 夹具（`long: [2,3.2]` 对 target `[2,3]`），并**用断言执行注释里那句话**：精确断言 `[("complete", 1.0), ("extra", 0.2)]`。注释不是锁。
- 状态集合断言**改回 `==`**（sol 实测当前状态集合恰好就是四项，`<=` 没有实现需要 ⇒ 属无理由弱化）。
- **指定 neuter**：把 [segment_score.py:571](../../../../src/agent/judge/segment_score.py#L571) 改成「observation 覆盖过任一 target 就丢弃全部 overshoot」，这条锁必须变红（当前 23 条全绿）。

**M-4 · A11 neuter 表重做**：
- 上轮自查表的 5 守卫结论**作废重做**，逐条给「摘掉哪一行 → 哪几条测试变红」，并**如实标注哪些锁与 sol 的四组 neuter 对应**。
- **不得再宣称「零 false-lock」**，除非每条都经指定 neuter 实证。

---

## 5. M-3 · W5 共享正交判据必须真接线

sol 全仓引用核实：生产端 `cell_geometry` 只 import 常量、仍自行执行 `dx > _EPS and dy > _EPS`；判卷端对共享模块**零 import**；`classify_edge_orthogonality` 与 `edge_is_axis_aligned` 的生产/判卷调用数**均为 0**；advisory 没有被记录、传播或写入任何运行时结果。⇒ **shipped-untested，派工单 W5 未交付。**

**必做**：
1. 生产端（`cell_geometry`）与判卷端**都真实调用**共享判据，不是各自复制逻辑。零 gt import 约束不变（不变量 #4）。
2. advisory 必须有**运行时产物**（被记录/传播/落进结果），否则「加 advisory」是空话。
3. **修 R-4 活体反例**：sol 构造的 cell A 共享边（底 x=`0.5`、顶 x=`0.5+5e-10`）+ cell B 反向共享边（底 x=`0.5`、顶 x=`0.5+4e-10`）⇒ **生产 `validate_corrected_geometry` 五项全 GREEN，而 scorer 报 `score_product_identity_invalid / exterior_duplicate_owner`**。
   **这正是本批要根除的病的原型**：判卷器拿自己的能力上限宣判上游几何非法。此形态**必须走 unsupported / NA**，不许报 product identity invalid。
4. **指定 neuter**：把共享 helper 首行改 `raise`，必须有**生产路径**测试变红（当前只有直接调用它的新增单元测试会红 ⇒ 接缝没焊住）。

---

## 6. N-1 · §5-B 出口 2 补齐

sol 独立验证确认你的架构理由**成立**（interior key 形如 `F1:interior:(...)`、facade id 形如 `F1:facade:<sha256>`，实测集合交集为空；窗宿主最终查的是 facade id）⇒ P-3 不升级为 BLOCKER。**但派工单出口 2 仍未交付。**

补**正式的完整链路锁**：correction window → facade multi-span → `assign_openings` → `build_correction_host_resolver` / claim。
**指定 neuter**：把 [score_service.py:230](../../../../src/agent/judge/score_service.py#L230) 的 `product_to_gt.update(...)` 改成只调 helper、不接入消费端 ⇒ 新锁必须变红（当前 21 条全绿）。

---

## 7. 交付与纪律

- 纪律**全部沿用**[原派工单 §1](2026-07-27_judge_identity_metric_construction_dispatch.md)：`case_tests/test_baseline/gt/` 一个字节不许动 / 不改 `AI_agent/CLAUDE.md` / 不在仓库根落文件 / neuter 只在 `/tmp` 副本做且工作树还原 / 开工收工两次 `git status --short` 逐字相等。
- 全仓基线 **1706 绿 + 10 xfail**（sol 独立复跑确认），要求零回归。
- 执行日志**续写**到 [2026-07-27_judge_identity_metric_glm.md](../execution/2026-07-27_judge_identity_metric_glm.md)，新开「r1 返工」一节，必须含：**重做后的 neuter 自查表**（含与 sol 四组 neuter 的对应）+ B-1 守恒锁证据 + 全仓输出 + 两次 git status。
- **诚实优先于完成**：做不完精确标 PARTIAL 说明卡在哪。**上轮把「用单元夹具替代 e2e 夹具」标成「性质标注非 PARTIAL」，这种降级不要再出现** —— 出口没达成就是没达成，如实标 PARTIAL 由主控裁量，比自行判定"等价"可信得多。
- 完成后回报主控，主控派 sol 复审（同席位续审），再走主控轻门。

## 8. 给施工方的一句话

上一轮你把**假红修成了假绿**。假红有人会来问「为什么判红」，假绿**没有人会来问** —— 它会一路签进标准答案。本轮所有守恒锁、精确码锁、字节锁的意义都在这里：**让判卷器在自己不确定的时候闭嘴，而不是给一个好看的分数。**
