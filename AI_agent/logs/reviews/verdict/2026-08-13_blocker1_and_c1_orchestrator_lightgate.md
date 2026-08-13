# orchestrator 轻门 —— 摊 A（BLOCKER-1 core proof）+ 摊 C（MAJOR-C1 标注语义）

- **日期**：2026-08-13
- **裁定**：**PASS（零新增 finding）**，转第四轮跨家族复审（GPT 侧 sol）
- **口径**：本轮**全部结论均为 orchestrator 独立实测**，⛔ 未采信任何施工席自述。
  轻门 = 独立全量 + 换方向 neuter + 抽查裁决，**不替代**跨家族执行审（「谁写谁不批」）。

---

## 1. 独立全量

| 项 | 值 |
|---|---|
| 命令 | `python -m pytest tests -q -n auto` |
| 结果 | **`2568 passed, 10 xfailed, 211 warnings in 442.50s`** |
| 退出码 | `rc=0`（**独占文件名**，`.rc` 时间戳晚于日志 ⇒ 非陈旧残留）|
| 汇总行 | 在（⛔ 未只凭退出码判「跑完」）|
| 今日基线 | 开工时独立复跑 **`2557 passed / 10 xfailed / 0 failed`** ⇒ **+11、零回归、零红** |

⚠️ 摊 C 席位在施工中途报告过两次全量红（`test_c2_b2_v3` / `test_output_coordinate_identity`），
归因为「摊 A 并行改动」。**orchestrator 未采信该归因，而是在两摊都收工后自己重跑**
⇒ 终态 0 failed ⇒ 那些红是 A 施工中间态的瞬时现象，已消失。

## 2. 换方向 neuter / 探针（施工席的方向不计入）

### 2.1 ⭐ 主方向：**orientation 契约的行为验证**（本轮最有价值的一次测量）

**动因**：摊 A 席位自报未覆盖项 #4 = 「没有为 `correction_b5_orientation_v1` 单独做伪造攻击测试，
它与 `correction_b5_v1` 走同一代码分支」。**而 orchestrator 核实：盘上每一个真实 run 用的都恰好是
`correction_b5_orientation_v1`**（`run_2026-08-11_continuous_e2e`、`run_2026-08-09_f18_e2e_verify`）。

⇒ 「同一分支所以覆盖到了」是**形状匹配**。本项目 08-11 刚栽过：grep 说 4 处副本已合并，
中和共享实现后才发现有一个调用点纹丝不动。**判接线只能行为验证。** 故实测：

| 探针 | 结果 |
|---|---|
| **PROBE1**：orientation 写入时统计 `core_owned_projection_v1` 真实调用 | `contract = correction_b5_orientation_v1` · **`proof bound = True`** · **compare 真的跑了（2 次调用，`[0.0,4.0]`）** |
| **PROBE3**：orientation 路径上让候选投影与重放投影分歧 | **`writer_core_projection_drift` 抛出** · **accepted pointer `1 → 1` 未移动** |
| PROBE2（弃用） | 撞上施工席那个 helper 自己的 sanity 断言（它为 base 路径而写，orientation 会改变 feature-state claim 形态）⇒ **helper 的护栏起了作用**，改用 PROBE3 达到同一目的 |

**自证**：两个探针都先断言「计数器起始为空 / 伪造值确实不同」再断言目标
（⇒ **探针零输出 ≠ 目标不存在**，这条纪律今天第三次兑现）。
⇒ **席位自报的覆盖缺口，在真实产物所用的那个契约上已由行为实测关闭。**

### 2.2 sol 原始反例（level-1）在生产判卷函数上复现

拿 F-17 翻转前**真实产物**（`footprint_x=[0.12,14.88]`，每条外边真差 0.12 m）：

| 场景 | `output_convention` |
|---|---|
| 原样（无印章、无 proof） | `declared=False, trusted=False, identity=None` |
| **手加一行印章**（sol level-1 攻击原型） | **`declared=True, trusted=False`** ⇐ 正是要求的语义 |
| 直接塞一份伪造 proof 给判卷 | **`trusted=False`**（投影哈希不匹配被抓） |

⇒ **「能自己写的字段最多叫 `declared`，绝不能叫 `trusted`」已在行为上兑现。**

### 2.3 哈希覆盖范围 == 判据范围（避开「哈希整份报告不能当子事实判据」老坑）

`core_owned_projection_v1` 返回的键 = `footprint_x` / `footprint_y` / `floors`（含每层 ring 顶点、
cells 的 id·role·x·y·polygon、z_floor、ceiling_height）/ `windows`（id·floor_id·z）/
`conflicts` / `unsupported` / `corrections`。
落库方逐键比对的正是这 7 项（`corrections` 按**前缀**比 + 后缀形态另验），
proof 的 `core_projection_hash = hash_obj(candidate_projection)` **哈希的就是同一个 dict**；
印章本身由 proof 的 `core_version` + `_is_declared_output_convention` 另行覆盖。
⇒ **不存在「哈希覆盖面 ≠ 比较面」的缝**。

### 2.4 F-20 式回归自查（往产物加字段会不会作废历史批准）

新增 `deterministic_core_proof` 被登记为 **ALLOWED but NOT REQUIRED**。实测 34 份历史账本：
**V2 账本 23 份全部照旧可加载**；11 份失败全是 `manifest_version != '2'` 的 **V1 legacy**
（与 08-10 盘点的 **V1×11 / V2×22** 逐数吻合）⇒ **不是本次改动引入的回归**，
施工席「设为 required 会让历史账本在 load 时就崩」的理由**成立**。

## 3. 摊 C 独立复核

- 独立跑 `tests/test_c1_annotation_semantics.py` + `tests/test_c2_b2b_envelope_transform.py`
  ⇒ **37 passed, rc=0**（与席位自述一致）。
- 中间档已改名 `reconcilable_nonzero_displacement`，标签「非零且容差内，标注法未知」，
  解释文本改为「当前没有可信墙厚事实，不能据此判断标注法，需人工判读」；
  `interpretation_rule`（人读出口）由标签派生 ⇒ 同步生效。**四态仍各自具名**、纯观测性质未动。
- **真实产物**（`continuous_e2e`）四条边 0.120 m：**「按外包标注」→「标注法未知」**
  ⇒ 该摊唯一的产品价值（**让「我们其实不知道这张图按什么标注」变得可见**）达成。

## 4. ⛔ 转第四轮复审时必须如实交代的三条口径限制

1. **正向端到端从未在真实 run 上出现过**：盘上**零份** B5 correction 产物带 proof
   （proof 是今天才有的），故 `trusted=True` 只在夹具与单测里被观察过，
   **没有任何真实 run 走通过「拿到 trusted」这一侧**。
   ⇒ **用户已拍板的真链路重跑不是可选项，它是唯一能观测正向的途径。**
2. **信任根从「产物自身」上移到了「accepted 账本」**：若同时改写侧车字节**与**账本里的
   `artifact_hashes` 条目，仍可铸出 trusted。这是本地账本的固有边界，
   **应由 sol 裁定「账本算不算合格的外部信任根」**，orchestrator 不自行结论。
3. **未穷举**：除 footprint/ring/cells 之外还有哪些 core-owned 字段可 replay-divergent，
   **sol 与施工席都未穷举，orchestrator 也未**。⛔ 不得声称「已列全所有路径」。

## 5. 待续（本轮之内）

- **摊 A′ 已派出**（F-24 缓存身份 + MINOR-A1 + NIT-F25）。
  **F-24 必须在真链路重跑之前闭合** —— 那次重跑会写出本仓第一份新版缓存，
  fail-open 门正是从那一刻起才真的敞开（orchestrator 实测：盘上侧车最高 `scorer_schema=9`，
  摊 A 已把它提到 `"11"` ⇒ 今天尚无陈旧命中）。
- 之后：跑前**停下与用户确认配置** → 真链路重跑 → 第四轮复审（A + A′ + C 合并送 sol）。
