# 第四轮跨家族复审请求 —— BLOCKER-1 闭合 + C1 + A′（F-24 / A1 / F-25）

- **日期**：2026-08-13
- **审阅席位**：GPT 侧 sol（跨家族；本轮三摊全部是「作者自验」，按「谁写谁不批」必须换人）
- **被审提交**：`da2245d`（单笔，22 文件，2057 insertions）
- **上一轮裁决**：[round3 裁决书](../verdict/2026-08-12_round3_full_body_crossreview_sol.md)
- **orchestrator 轻门**：[2026-08-13 轻门裁决](../verdict/2026-08-13_blocker1_and_c1_orchestrator_lightgate.md)（PASS，零新增 finding）
- **派工单**：同目录 `2026-08-13_blocker1_core_proof_dispatch_claude.md` /
  `..._c1_annotation_semantics_dispatch_gpt.md` / `..._aprime_cache_identity_dispatch_claude.md`

---

## 0. ⭐ 停止规矩（分层 —— 上一轮证明这条必须写在最前面）

前两轮你都停在 orchestrator 请求书的**外围论据**错上（第二轮裁决书自己写着「这项前提错误不改变范围裁定」），
**代价 = 主体两轮零审阅**。第三轮把规矩分层后，五项主体全部实审完毕。**本轮沿用分层规矩**：

1. **承重前提错**（错了则本轮审阅方向作废 / 会导致错误裁定）⇒ **停下上报**。
2. **外围论据错**（不改变审阅范围）⇒ **记录后继续把主体审完**。

⛔ 不要因为本请求书某个数字或某句论据不成立就停掉整轮。

## 1. 本轮请你裁的四件事（按重要度）

### 1.1 `BLOCKER-1` 是否可以关闭

修法按你 §3.1 给的四步做的：

| 步 | 落点 |
|---|---|
| ① 落库方比对 core-owned projection | `stage_runner.py`：新增 `core_owned_projection_v1(replayed)` vs `(fresh_geom)` 逐键比对，位置在原有 per-window audit 检查**之前**。键 = `footprint_x` / `footprint_y` / `floors`（每层 ring 顶点 + cells 的 id·role·x·y·polygon + z_floor + ceiling_height）/ `windows`（id·floor_id·z）/ `conflicts` / `unsupported` / `corrections`（**按前缀**比 + 后缀形态另验）+ stamp version。不一致 ⇒ `writer_core_projection_drift` |
| ② writer 签发 proof | 全部比对通过后签 `DeterministicCoreProofV1{core_version, input_hash, core_projection_hash}`，作为**第 7 个 artifact** 绑进 accepted 账本。`input_hash` 绑真实 producer 字节 |
| ③ scorer 只认外部 proof | `_is_declared_output_convention`（旧自报检查，改名）与 `_is_trusted_output_convention`（新）拆开。后者要求：自报仍成立 **且** proof 非空 **且** `proof.core_version == live 常量` **且** `proof.core_projection_hash == hash_obj(core_owned_projection_v1(被判几何))`（**在判卷侧重算，不是读 proof 上的值**）。proof 只能由 `run_stage.py::_resolve_core_proof_for_attempt` 从 accepted 账本解析并逐字节校验侧车 |
| ④ 真实 `record` 锁 | `tests/test_c2_b5_artifact_trust.py` 新增伪造 footprint（复现你的 `[0,4]²`→`[0.12,3.88]²`）走**真实 writer** 的锁 + 一条诚实写入的正向伴生锁 |

**⛔ 连带已处理**：`test_neuter_restoring_stamp_flips_judge_back_to_accept`（把 bug 写成正向预期的那把锁）
已改写为 `test_neuter_restoring_stamp_flips_declared_not_trusted`。

**⭐ 三条口径限制，orchestrator 主动交代、请你裁**（⛔ 我们不自己下结论）：

1. **正向端到端从未在真实 run 上出现过。** 盘上零份带 proof 的 B5 产物（proof 今天才有），
   `trusted=True` 只在夹具与单测里被观察过。⇒ 用户已拍板要跑一次真链路重跑，**但本提交时点尚未跑**。
   请裁：这是否影响 BLOCKER-1 的关闭，或应作为「关闭但附带必须完成的真链路验收」。
2. **信任根从「产物自身」上移到了「accepted 账本」。** 若同时改写 proof 侧车字节**与**账本里的
   `artifact_hashes` 条目，仍可铸出 `trusted`。**请裁：本地 append-only 账本算不算合格的外部信任根**
   （与既有判据「只有有外部信任根的才配被冻结」的关系）。
3. **未穷举**：除 footprint/ring/cells 外还有哪些 core-owned 字段可 replay-divergent，
   你、施工席、orchestrator **三方都未穷举**。⛔ 我们不声称「已列全所有路径」。

### 1.2 `MAJOR-C1`（标注法观测语义）

**orchestrator 发单前机械核实推翻了你给的两条修法中的第二条可行性**（请复核这个判断）：
你的修法 ② 是「给 observer 传入可信、版本化的 wall-thickness fact」。实测：

- 生产侧（reading → correction → geometry）**没有任何墙厚事实**：`thickness` 在
  `correction/schema.py`、`geometry/*.py`、`configs/*.yaml` 命中数 **全为 0**；
  真实产物 `run_2026-08-11_continuous_e2e` 的 **20 条墙笔画 `geometry.thickness_m` 全部为 `None`**；
- 仓内唯一可信墙厚在 **judge/gt 侧**（`gt_manifest.default_wall_thickness_m`、天正 `_outer_skin_thickness_m`）
  ⇒ 取用会违反**不变量 #4 gt 铁律**（实测：生产侧对 gt 的 import 命中数为 0）。

⇒ 按你的修法 **①** 施工：中间档改名 `reconcilable_nonzero_displacement`，
解释文本改为「非零、超出 output_precision_m 但仍 <= envelope_reconcile_tol_m；**当前没有可信墙厚事实，
不能据此判断标注法，需人工判读**」。四态仍各自具名、纯观测性质未动。
真实产物四条边（各 0.120 m）：**「按外包标注」→「标注法未知」**。

**⚠️ 另请注意（可能属你的裁量范围）**：那把既有锁
`test_annotation_basis_names_outer_skin_annotation_at_half_wall_thickness_scale`
**函数名逐字声称「半墙厚量级」而实现从来没有墙厚输入** ⇒ 与 BLOCKER-1 那把锁同一形状
（**锁把错误语义固化了**）。已随本摊改写。

### 1.3 `MAJOR-F24` + `MINOR-A1` + `NIT-F25`（摊 A′）

- **F-24**：`_load_valid_score_sidecar` 判据新增 `scoring_semantics`，其值由
  `deterministic.DETERMINISTIC_CORE_STAMP_VERSION` + `correction_score.CORRECTION_OUTPUT_CONVENTION`
  **两个 live 常量 module-qualified 读取派生**（⛔ 不是新的手写版本号；中和任一常量该字段跟着变）。
  锁 = 1 条机制自检 + **1 条正向（身份不变 ⇒ 缓存命中）** + 2 条反向（任一常量变 ⇒ 缓存失效）。
  **⛔ orchestrator 主动交代的覆盖缺口**：你 §6 点名的三项里，**只自动绑了两项**
  （core stamp version、output convention）；**第三项「scorer implementation identity」仍依赖人手动 bump
  `LEGACY_SCORE_CACHE_SCHEMA`**（代码注释如实写明了这一点、未冒充完整）。
  **请裁这是否满足 F-24 的「至少三项」口径。**
- **MINOR-A1**：`no_data_boundary_floors > 0` 时 `boundary_complete` 由 `pass` 改为 `severe`
  （orchestrator 在真实产物上行为验证：`suggested_status = "severe"`）。
  ⚠️ 施工席自报的判断取舍：**未新开 `unavailable` 状态值**，因为该 criteria 词表历来只有
  `pass`/`minor`/`severe` 三档。请裁「被拒判」与「实测不合格」是否需要更细的语义区分。
- **NIT-F25**：legacy 改名 `LEGACY_SCORE_CACHE_SCHEMA`；`score_schema.py` 里那个**同值重复别名
  `SCORER_SCHEMA` 被删除而非改名**（依据 = 除定义行外全仓零生产读者）。
  独立性锁保留并改指向 `SCORE_SIDECAR_SCHEMA`。
  ⚠️ 施工席自报未验：非 Python 文件里是否有硬编码该符号名的游离引用（概率低，未穷举）。

### 1.4 上一轮仍开的 finding —— **本轮未动，请确认它们的状态不变**

`MAJOR-1` · `MAJOR-2` · `MAJOR-B2` · `MAJOR-B3`（**条件 5 未实现却声明 evaluated —— 今天就已经是假的**）
· `MINOR-3` · `MINOR-B4` · `MINOR-B5` · `MINOR-D1`。
⛔ 本轮**没有**声称它们被处理过。

## 2. 测试基线（orchestrator 独立实测三次，非采信席位自述）

| 时点 | 数字 | 凭据 |
|---|---|---|
| 开工基线 | `2557 passed / 10 xfailed / 0 failed` | rc=0 独占文件 + 汇总行 |
| 摊 A+C 后 | `2568 passed / 10 xfailed / 0 failed` | 同上 |
| 摊 A′ 后（= 本提交） | **`2573 passed / 10 xfailed / 0 failed`** | 同上，`+5` 恰为本摊新增 5 条测试 |

命令 `python -m pytest tests -q -n auto`。⚠️ 打印式探针需 `-n0`（`-n auto` 吞 worker stdout）。

## 3. orchestrator 轻门做过什么（避免你重复劳动）

已做（详见轻门裁决书）：① 三次独立全量；② **orientation 契约的行为验证** —— 施工席自报未攻击测试
`correction_b5_orientation_v1`，而**盘上每个真实 run 用的恰是它**；orchestrator 实测该契约下
compare 真的执行（2 次真实调用）+ proof 真的绑上 + 制造分歧 ⇒ `writer_core_projection_drift`、
**accepted pointer 未移动**；③ 你的 level-1 攻击复现 ⇒ 手加印章现在只得 `declared=True, trusted=False`，
伪造 proof ⇒ `trusted=False`；④ 哈希覆盖面 == 比较面（7 键）；⑤ F-20 式回归：34 份历史账本中
**23 份 V2 全部照旧可加载**，11 份失败全是既有 V1 legacy（与 08-10 盘点 V1×11/V2×22 吻合）。

**⇒ 建议你把力气花在**：1.1 的三条口径限制（尤其**账本算不算外部信任根**）、
1.3 的 F-24 三项覆盖、以及**我们都没穷举的 replay-divergent 字段面**。

## 4. 派工方错误率如实登记：**16/16**

本日新增一条：给摊 C 的派工单写「只动这一个源文件 + 你自己的新测试」，
**而仓里有一把既有锁硬断言了要被推翻的旧语义** ⇒ 「只动这些文件」与「全仓必须绿」**互相冲突、任务字面不可完成**。
GPT 侧席位走合法退出口停下上报（本项目「停下上报」第 16 次全是派工方题错），orchestrator 改单后续跑。
> ⭐ 类别 = **验收条件互相冲突**（第三次），且本次成因是**没先查「既有锁是否钉住了要被推翻的语义」**。
