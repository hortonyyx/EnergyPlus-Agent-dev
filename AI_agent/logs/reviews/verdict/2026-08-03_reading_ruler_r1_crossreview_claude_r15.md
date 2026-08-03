# R1 批 B · r1 交叉对抗审（路 1）· 被审 = R1-5（terra 产出，commit `c56cbe1`）· 审 = Claude 侧子代理（Opus 档）

> ## ✅ 本文最终版
> （骨架阶段的「暂定」字样已全部落定；N6 / N4 的全量复跑确认已完成并写入 §2。）

- **日期**：2026-08-03
- **审阅单**：[`request/2026-08-03_reading_ruler_r1_crossreview_claude_r15.md`](../request/2026-08-03_reading_ruler_r1_crossreview_claude_r15.md)
- **被审范围**：`c56cbe1` 一条 commit，7 文件（**不含** r1 的另外六条 = 路 2 范围）
- **审阅工作树**：主仓库只跑只读 git（`git log` / `show` / `diff` / `branch -r`），**全程未跑 `git status`**；
  一切破坏性探针在 `/tmp/.../scratchpad/probe`（`git clone --local --no-hardlinks`，HEAD=`48e41b6`）内做。
  主工作树唯一写入 = 本报告文件。**未 commit、未 push、未 stash。**

---

## 0. 总判定

**REWORK** —— 0 BLOCKER / **3 MAJOR** / **3 MINOR** / 2 NIT。

生产码本体是**对的**：我没能证伪「冻结政策在被点名的四个面上真的接上了」。
四条新锁里有三条是**真锁**、断言落在具体 check-id 行与 `checks.json` 头部字段上，形状合规。

判 REWORK 的理由只有一条，但它正是本批 r0→r1 那句话的第三次复发：

> **R1-5 最大的那块实现 —— 让冻结政策成为「整个 run」的政策的那根线 —— 一条锁都没有。**
> 把 `_policy_with_frozen_tier` 的函数体整个删成 `return policy`（= 精确回退到 r0 被判 MAJOR 的状态），
> 受影响子集 364 测**全绿**。R1-5 交付的两条锁只覆盖几何签字门与 baseline 记账，
> **没有一条覆盖 correction / modelling / grade / typed scoring 这条主干**。

即：**「机制在所有真实路径上都生效」这次做到了；「有人改坏时会变红」这次没做到。**
这与 08-01 W4「探针 ≠ 锁」、与 r0 的「门是真的、锁是缺的」是同一个形状，
且 orchestrator 轻门的 neuter **恰好只扫到了有锁的那两处**（`step_orchestrator` 的两个
`effective_run_policy(run_dir)`），没扫到无锁的这一处 —— 与 08-01 GLM 抓到的 S-1 同族。

---

## 1. T-1…T-7 逐条判定

### T-1（最高权重）两条新锁真绑、零连带 —— **部分成立**

| | |
|---|---|
| **成立的部分** | `c56cbe1` 共新增 **4** 条测试。逐条独立 neuter 后，其中 **3 条是真锁**：摘掉对应实现即红、零连带、断言落在具体 check-id 行（`downstream.build`）与 `CheckReport` 头部（`run_profile` / `capability_profile`）上，**不是**落在「返回值存在 / 数量变了」。 |
| **不成立的部分** | 这 4 条锁**没有一条**覆盖 `run_stage.py:_policy_with_frozen_tier`（cmd_run / cmd_judge / cmd_flow 三个真实入口的接线）。见 MAJOR-1。 |
| **无假锁** | 我**没有**找到「摘掉实现仍然绿」的假锁 —— 4 条锁在其各自目标实现被摘掉时都会红（详见 §2 台账）。缺的是**覆盖面**，不是锁本身空转。 |

**「一处实现被多条锁覆盖、其中一条空转」的专项排查**：`record_baseline` 的两条锁**互相不隔离**
（N1 摘政策消费、N2 摘 `run_policy` 头部，两次都是同样两条红）。但这**不是空转** ——
两条锁各自的红点不同：N1 下 `..._uses_frozen_policy_not_cli_fallback` 红在
`assert any(row["check"] == "downstream.build" ...)`（政策消费），
`..._marks_unfrozen_run_legacy` 红在 `assert not any(...)`（反向）；N2 下两条红在头部字段断言。
⇒ 两条锁各自同时钉住「消费」与「头部」两件事，冗余但都承重。**判：不是假锁。**

### T-2（最高权重）冻结政策真的覆盖整个 run —— **成立（机制），但无回归守卫**

我按审阅单建议全仓扫了 `RunPolicy(` 构造点与 `run_profile` / `capability_profile` 的读点，
**没有找到一条仍在消费局部/默认 `RunPolicy` 而能影响判定的 run 内路径** —— 证伪失败（详 §4）。
被点名的四个面逐一核过：

| 面 | 现状 | 证据 |
|---|---|---|
| correction / modelling / grade | 全部读 `policy.capability_profile` / `policy.run_profile`，而 `policy` 已在 `cmd_run:1946` / `cmd_flow:2143` 被 `_policy_with_frozen_tier` 换成冻结档 | `run_stage.py:274,277-278,286-287,299-300,327-328,394-407,423,451,471-472,508,560,595` |
| typed scoring 严格拒绝 | `run_profile in {"golden","regression"} ⇒ raise`，该 `run_profile` 沿 `policy.run_profile` 传入 | `run_stage.py:1437-1438,1489-1493` ← `1962,1979,2179,2202` 传 `policy.run_profile` |
| `record_baseline.py` | 不再自造 `RunPolicy`，改 `effective_run_policy(run_dir)` | `record_baseline.py:507-509` |
| 几何签字门 | `approve_geometry` / `geometry_is_approved` 均改冻结档 | `step_orchestrator.py:486,507` |

**独立复核施工方主动披露的那处取舍（`submit_verdict` / `_verdict_outcome` 保留 `policy or RunPolicy()`）：披露成立。**
我逐行核了这两个函数**实际读了 `policy` 的哪些字段** —— 只有
`policy.reading_runner_available`（`step_orchestrator.py:410`）与 `policy.budget.per_stage_draws`（`:411`），
**完全没有触碰 `run_profile` / `capability_profile`**。⇒ 确属运行期操作旋钮，归类正确。

**回答「同族的『运行期旋钮 vs 档位政策』还有没有别处被归错类」：有一处方向相反的错分，见 MINOR-1。**
`_policy_with_frozen_tier` 的 docstring 声称「caller still owns ephemeral operational knobs」，
但它实际只替换了 `run_profile` + `capability_profile` 两项，
而 `require_ep` / `confirmation_policy` / `judge_enabled` 在 `run_stage` 侧仍取**当次 CLI/config 的活值**，
在 `effective_run_policy` 侧却取**冻结 context 的值** —— 同一个 run 内这三项有**两个不同的权威**。
其中 `require_ep` 是**判定面**（`validation_run.py:120` 决定 `downstream.build` 是否成为阻断必需件），
不是操作旋钮。⇒ **归错类的是它，不是 `submit_verdict`。**

### T-3 `record_baseline` 不再自造档位 —— **成立**，但带一条 fail-open 副作用

- **取自哪里**：`resolve_frozen_run_policy(run_dir)` + `effective_run_policy(run_dir)`（`record_baseline.py:507-508`）。
- **取不到时**：**静默兜底、但兜得诚实** —— 无冻结件 ⇒ `legacy_defaulted=True` / `source="legacy_defaulted"` /
  `exploratory` / `rectangular`，且这四项**原样落进 `baseline["run_policy"]` 头部**（`:535-541`）。
- **兜底会不会冒充一次正常严格档记账**：**不会。** 我实测构造：一个无冻结件的 run，
  调用方传 `require_ep=True, run_profile="regression"`（= 明确要严格档）⇒
  落盘头部仍是 `legacy_defaulted / exploratory / rectangular`，且严格档才有的 `downstream.build` 行**不出现**。
  **底线「legacy 默认档不得冒充 regression」守住了**，方向是**低报**不是高报。
- **要我证伪的形式（构造 baseline 记账档位 ≠ gate① 实际执行档位）**：
  **在 `flow` / `run` 真实入口下证伪失败** —— 这两个命令在建 policy 前先 `provision_run_policy`，
  之后 gate① 与 baseline 读的是同一份冻结件，必然一致。
  **仅在「对一个 S-2 之前的老 run 事后单独跑 `record_baseline.py`」时可构造出不一致**：
  盘上 `checks.json` 头部可能是 `regression`，而 baseline 重算出的是 `exploratory`。
  但因为头部同时写了 `legacy_defaulted=true`，**是可分辨的低报，不是冒充** ⇒ 不判为 T-3 不成立，
  改列 MINOR-2（CLI 旗标已成哑弹）。

### T-4 `GeometryApproval` 的加固 —— **是「记录」，不是「加固」；按审阅单许可登记为债**

- **四个字段有没有消费者**：**零个。** 全仓 `src/` + `scripts/` 中
  `run_policy_source` / `run_policy_legacy_defaulted` 的命中，
  除**唯一写入点** `step_orchestrator.py:492-493` 外，**全部属于另一条无关的线**
  （`CheckReport.run_policy_source` / isolation manifest 字段）。
  `GeometryApproval` 唯一的真实读取点是 `run_stage.py:2306`，它只读 `appr.actor` / `appr.policy`。
  ⇒ **四个字段没有任何读点，读了也不改变任何判定。**
- **有没有锁**：**零。** 把这四行整个删掉（N4），受影响子集 364 测**全绿**。
- **它现在挡不住什么（审阅单要求写清）**：**挡不住任何东西。**
  它挡不住「在 exploratory 档下签的字被当成 regression 档的签字使用」——
  因为**没有任何代码会去读这个字段做判断**；也挡不住「有人把这四个字段删掉」——因为没有锁。
  它**只**提供「事后有人打开 `approval.json` 用眼睛看」的可审性。
- **⚠️ 但它没有过度声称**：CLAUDE.md §2 的措辞是「一次人工签字从此绑定它是在哪个档位下签的，**事后可审**」——
  这句**准确**，没有声称它会阻断。**故不构成「记录了就以为守住了」的虚假声称**，只构成一条债。
- **旧的、无这四个字段的已签字 approval 进来会怎样**：字段默认值 =
  `legacy_defaulted` / `True` / `exploratory` / `rectangular`（`approval.py:66-70`）⇒
  **旧签字被诚实标成 legacy，不会被当成合法的 regression 签字。** 方向安全（低报），底线守住。
  副作用：一份**真的在 regression 档下、由 R1-5 之前的代码签的**字，也会被标成 legacy —— 仍是低报，可接受。

### T-5 与另六条的接缝 —— **部分成立**（三种情况里两种可分辨，第三种不可分辨）

我在 `/tmp` 下用真实 `resolve_frozen_run_policy` / `effective_run_policy` 实跑了 8 个构造（探针见 §4 末）：

| 构造 | 行为 | 是否可分辨 |
|---|---|---|
| A 政策文件缺失 | 不报错，返回 `legacy_defaulted / exploratory / rectangular` | ✅ 靠 `source` + `legacy_defaulted` 机器可分辨 |
| C 文件损坏（非法 JSON） | **raise** `run_policy_drift: ... is corrupt` | ✅ fail-closed |
| D 手工改档、**未重算哈希** | **raise**（`policy_hash` / `content_sha256` 自校验不过） | ✅ fail-closed |
| **E 手工改档 + 重算哈希，且 run 无 `run_config.yaml` 声明** | **静默接受**，返回 `source=structured_config` / `legacy_defaulted=false` / `exploratory` | ❌ **不可分辨** |
| F 同 E，但 `run_config.yaml` 声明了 regression | **raise** `run_policy_drift: run_config.yaml ... differs` | ✅ |
| **H 只改 `context`（`require_ep: true→false`）+ 重算 `content_sha256`，档位不动** | **静默接受**，档位仍 regression，但 `effective require_ep` 已被翻成 `False` | ❌ **不可分辨** |

**⇒ 对审阅单的问句「会不会静默回落到 exploratory 并看起来像一次正常执行」的回答是：会（E）。**
E/H 的根在 R1-1 的 resolver（`content_sha256` 是**payload 自身的哈希、可自行重算**，
不绑任何外部信任根；漂移复核只在 `run_config.yaml` **真的声明了**时才生效，
而 CLI-only 指定档位的 run 根本没有那份声明）。
**按审阅单「只核接缝行为、不审 R1-1 实现本身」，我不对 R1-1 判分**，但必须登记：
**R1-5 显著放大了这条接缝的后果**——见 MAJOR-3。

### T-6 边界合规 —— **①存疑（需 orchestrator 确认）/ ②③④⑤成立 / ⑥ 挑战见下**

| | 结论 | 证据 |
|---|---|---|
| ① 未 push | **⚠️ 事实是：`c56cbe1` 已在 origin 上**（`git branch -r --contains c56cbe1` ⇒ `origin/6.15_ValidationArchM0toM4`；`git log origin/<branch>..HEAD` 为空）。**但我无法区分是施工席自己推的、还是 orchestrator 08-03 收工 ritual（§5#12 = commit + push）推的。** 后者是合规的、也是最可能的解释。⇒ **不判违规，转 orchestrator 一句话确认。** |
| ② `gt/**` 与 sm24 `testdata_prompt.json` 零字节改动 | ✅ `git show --name-only c56cbe1` 全部 7 个文件均不在 `case_tests/` 下；`git diff --stat c56cbe1^ c56cbe1 -- case_tests/` 输出为空 |
| ③ 真实 sm24 / sm21 manifest `content_sha256` 逐字不变 | ✅ 同上，本 commit **未触碰任何 manifest 文件**，逐字不变是构造性成立 |
| ④ 未读 GT 答案 | ✅ `git show c56cbe1 \| grep judge.gt\|load_gt\|gt_path` 零命中；新增代码只 import `run_policy_freeze` / `policy` / `validation_run` |
| ⑤ 未顺手做批 C / 批 D / R1.5 | ✅ 7 文件全部落在冻结政策接线这一条线上，无识图 schema / 坐标来源 / 判卷层改动 |
| ⑥ 欠规格边界报 none | **⚠️ 挑战不通过。** 至少存在两处施工方**做了判断却未上报**的欠规格边界：(a) `record_baseline` 的 `require_ep` / `run_profile` 两个参数被**降级为哑弹**（代码注释里自认「deliberately do NOT recreate a requested strict tier」= 这是一个**语义决策**，不是无歧义实现）；(b) `_policy_with_frozen_tier` **只替换两项而非全部档位相关项**，把 `require_ep` 留在活值一侧（同样是决策，且与 `effective_run_policy` 的口径不一致）。两处都属「派工单没写死、施工方自行拍了」，按 07-28 立的规矩应停下上报。⇒ **MINOR-1 / MINOR-2 即由此而来。** |

### T-7 复杂度可扩展性（不变量 #6）—— **成立，无烤死假设**

- `RunPolicyRecord` 的档位是 `capability_profile: str`（`Literal` 只在校验器里用元组白名单），
  加档位 = 往 `_CAPABILITY_PROFILES` 加一项 + 升 `schema_version`，**是加槽位不是推翻**。
- `GeometryApproval` 新加的四个字段**全部带默认值**，旧件可直接加载 ⇒ schema 演进接缝在。
- **非方形 / 退台 / 挑空 / 中庭**只会带来**新的 capability 档**（如 `orthogonal_polygon` 之后的更强档），
  而本 commit 的全部逻辑都是「把 run 声明的那个档原样传下去」，**对档位的取值内容零假设**。
- **唯一要留意的**（不判 finding）：`_run_policy_hash` 只哈希两个标量。若将来档位变成
  **per-floor / per-view 的结构化能力声明**，这个「两标量」的哈希面要一起升级；
  但那属于 schema 升版的正常动作，不是要推翻的假设。

---

## 2. 逐锁 / 逐实现 neuter 台账

**方法**：`/tmp` 克隆（HEAD `48e41b6`），每次只改一处、跑同一受影响子集、跑完 `git checkout -- .` 复原。
子集 = 9 个文件（`test_orchestrate_baseline` / `test_step_orchestrator` / `test_execution_foundation` /
`test_run_stage_flow` / `test_audit_remediation_accepted_inputs` / `test_isolation` /
`test_reading_ruler_r1_batchB` / `test_provenance_baseline` / `test_validation_run_baseline`）。
**克隆内基线 = 1 failed / 364 passed / 9 xfailed**，其中那 1 条 `test_sm21_anchor_ep_clean`
是**克隆固有红**（依赖 gitignored 的 sm21 EP 产物，未随 `git clone` 带出），
在下表所有行里恒定出现，**已从「红了哪几条」中剔除**。

| # | 摘掉哪一处实现 | 红了哪几条（已剔除克隆固有红） | 连带 | 判定 |
|---|---|---|---|---|
| **N1** | `record_baseline.py:507-509` 政策消费 → 复原自造 `RunPolicy(require_ep=…, run_profile=…)` | `test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback`、`test_R1_5_record_baseline_marks_unfrozen_run_legacy` | 零 | ✅ 真锁 |
| **N2** | `record_baseline.py:535-541` 删掉 `run_policy` 头部块 | 同上两条 | 零 | ✅ 真锁 |
| **N3** | `step_orchestrator.py:486` → `policy=RunPolicy()` | `test_R1_5_approve_geometry_uses_frozen_policy_check_headers` | 零 | ✅ 真锁（**独立复现 orchestrator 轻门的结论**） |
| **N4** | `step_orchestrator.py:492-495` 删掉 `GeometryApproval` 四个新字段 | **零条**（**已全量复跑确认**） | — | ⛔ **无锁**（MAJOR-2） |
| **N5** | `step_orchestrator.py:507` → `policy=RunPolicy()` | `test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers` | 零 | ✅ 真锁（**独立复现轻门结论**） |
| **N6** | `run_stage.py:1689-1703` `_policy_with_frozen_tier` → `return policy`（= 精确回退 r0） | **零条**（**已全量复跑确认**） | — | ⛔ **无锁**（MAJOR-1） |
| **N7** | `run_stage.py:2305` `policy.run_profile == "golden"` → `args.run_profile == "golden"` | **零条** | — | ⛔ 无锁（NIT-1，仅影响一行告警打印） |
| **N8** | `run_policy_freeze.py:304` `effective_run_policy` 首行插 `return RunPolicy()` | `..._uses_frozen_policy_not_cli_fallback`、`..._approve_geometry_…`、`..._geometry_is_approved_…` 共 3 条 | 零 | ✅ 共享 helper 被 3 条锁钉住 |

**N8 少红的那一条（`marks_unfrozen_run_legacy`）不是假锁**：对一个 legacy run，
`effective_run_policy` 本来就返回与 `RunPolicy()` 等价的值（exploratory / rectangular / optional / require_ep=False），
neuter 不改变其行为 ⇒ 不红是**正确**的。

**⇒ 台账小结：4 条锁全部真绑、零假锁、零连带；但 R1-5 的 8 处实现改动里有 3 处（N4 / N6 / N7）零锁，其中 N6 是本 commit 最重的一块。**

### 2.1 N6 / N4 的**全量**复跑确认（受影响子集不足以下 MAJOR 结论，故补此步）

在同一个 `/tmp` 克隆里跑**全仓无过滤** `pytest -q -n 4` 三次（基线 / N6 / N4），逐次比对**失败集合**：

| 轮次 | 结果行 | 失败集合 |
|---|---|---|
| 克隆基线 | `6 failed, 2077 passed, 8 skipped, 10 xfailed in 265.83s` | `test_partition_on_window_jamb_real_restore_reading_r2_flags_four` / `test_build_only_cli_round_trips_l_candidate_and_nonzero_north` / `test_manifest_inspector_cli_exit_and_json_contract` / `test_sm21_phase1_reading_score_regression_floor` / `test_sm21_anchor_ep_clean` / `test_zone_agent_creates_two_zones` |
| **N6**（摘掉 `_policy_with_frozen_tier`） | `6 failed, 2079 passed, 8 skipped, 10 xfailed in 264.96s` | **与基线逐条相同** |
| **N4**（摘掉 approval 四字段） | `6 failed, 2079 passed, 8 skipped, 10 xfailed in 250.09s` | **与基线逐条相同** |

**⇒ 全仓范围内，两处 neuter 均零测试变红，MAJOR-1 / MAJOR-2 成立。**

⚠️ **如实登记两点**：
① 克隆基线那 6 条红**与本 commit 无关**，是克隆环境固有（4 条依赖 gitignored 的 sm21/DXF 输入，
1 条 `test_zone_agent` 需要 OpenAI 网络，1 条 sm21 EP 产物缺失）——
主工作树全量是 **2089 绿零红**（§5），两者不矛盾。
② N6/N4 两轮的 `passed` 比基线多 2（2079 vs 2077）。**这不是 neuter 造成的** ——
neuter 只删行为、不新增用例；应为克隆内跑测累积的产物影响了某处按文件系统状态参数化的收集。
**结论只依赖「失败集合逐条相同 + 通过数未下降」这个比较，不依赖绝对计数**，故不影响判定。

---

## 3. 清单外自主发现

### MAJOR-1（本单最重）`_policy_with_frozen_tier` —— R1-5 的主干实现零回归守卫

- **位置**：`scripts/tool_scripts/run_stage.py:1689-1703`（定义）+ `:1946`（cmd_run）/ `:2046`（cmd_judge）/ `:2143`（cmd_flow）
- **一句话失败场景**：任何人（含未来的重构）把 `_policy_with_frozen_tier` 改回 `return policy`，
  **correction / modelling / grade / typed-scoring 立刻全部退回读 CLI/默认档**（= r0 被判 MAJOR 的原状），
  而**整个测试仓一条都不会红** —— 于是「同一个 run 内检查、判卷、记账各认各的档」会**静默复活**，
  且下一次有人跑 sm24 时，`checks.json` 头部会再一次写着 `exploratory` 而 `run_config.yaml` 声明着 `regression`。
- **为什么这条最重**：这正是 R1-5 派工单的**正文**（「冻结的政策只接到 reading checker，没成为整个 run 的政策」），
  而 R1-5 交付的两条锁钉的是**几何签字门**与 **baseline 记账**这两个**旁支**。
  派工单 §3 白纸黑字要求「**每条**要有摘掉即红、零连带的锁」。
- **出口**：补一条走**真实 CLI 入口**（`cmd_run` 或 `cmd_flow`，⛔ 不许直接调内部函数绕过 argparse）的锁：
  构造一个冻结档 = `regression`/`orthogonal_polygon` 而 CLI/`run_config` 给 `exploratory`/`rectangular` 的 run，
  断言落盘 `1_correction/*_checks.json`（或 typed scoring 的严格拒绝）**头部字段 = regression/orthogonal_polygon**、
  以及某条只在严格档才出现的具体 check-id 行。摘掉 `_policy_with_frozen_tier` 必须红。

### MAJOR-2 `GeometryApproval` 四字段 = 零消费者 + 零锁

- **位置**：`src/agent/execution/approval.py:66-70`（定义）+ `src/agent/execution/step_orchestrator.py:492-495`（唯一写入）
- **一句话失败场景**：把这四行删掉，全仓无一条测试变红，
  于是「一次人工签字绑定它在哪个档位下签的」这条**唯一的实现**会在下次重构中被无声删除，而没有人会知道。
- **⚠️ 与本项目已犯的「第二类假锁」的区别（如实登记）**：它**没有**被声称成阻断项，
  CLAUDE.md 的措辞「事后可审」是准确的 ⇒ **不是虚假声称，是一条真债**。
- **出口（二选一，均可）**：(a) 只补锁 —— 一条断言「在冻结 regression 档下 `approve_geometry` 产出的
  `approval.json` 四字段 = regression/orthogonal_polygon/structured_config/false」的回归锁；
  (b) 补消费者 —— 让 `record_baseline` / `cmd_flow --record` 在
  `approval.run_profile != frozen.run_profile` 时拒绝或至少落一条 flag。
  **审阅单允许只登记为债**，故本条**不单独构成 REWORK 理由**。

### MAJOR-3 `context` 被从「非漂移绑定的审计快照」提升为判定面，但漂移面没跟着扩

- **位置**：`src/agent/execution/run_policy_freeze.py:22-30`（G-4 免责声明）
  vs `:292-294, 326-335`（`effective_run_policy` 消费 context）
  vs `src/agent/execution/validation_run.py:120`（`require_ep` 决定 `downstream.build` 是否成为阻断必需件）
- **一句话失败场景**：把 `<run>/_run/run_policy.json` 里 `context.require_ep.value` 从 `true` 改成 `false`
  并重算 `content_sha256`（该哈希是 payload **自身**的哈希、可自行重算，不绑任何外部信任根），
  记录**照常通过校验、照常通过 `run_config.yaml` 漂移复核**（漂移复核只覆盖两个档位标量），
  于是 `record_baseline` 的记账**静默不再把缺失的 EP 产物记成阻断行**，而 `baseline["run_policy"]`
  头部仍显示 `regression` ⇒ **一份看上去是严格档、实则漏记了阻断项的 baseline。**
  **我在 `/tmp` 实跑过这条（构造 H），确实通过。**
  ⚠️ **精确划界（避免夸大）**：同一篡改对**几何签字门**是**无害**的 ——
  `approve_geometry` / `geometry_is_approved` 只读 `res.geometry_digest` / `res.geometry_approved`，
  这两项不受 `require_ep` 影响。**受影响的只有 baseline 记账这一面。**
- **为什么算 MAJOR 而不是「本来就这样」**：`run_policy_freeze.py:22-30` 的 G-4 免责声明**明文写着**
  把 context 排除在漂移检测外的**理由**是「they do not affect reading-check blocking」。
  R1-5 之后这个理由**已经不成立** —— context 现在决定 `require_ep` / `confirmation_policy` / `judge_enabled`。
  **一个模块的不变量声明变成假的，比字段本身可篡改更危险**：下一个实现者会照着那段注释继续假设 context 无判定作用。
- **出口（三选一）**：(a) 把 context 里**真正是判定面**的那几项纳入 `policy_hash` / 漂移复核；
  (b) 或反过来把 `effective_run_policy` 对 context 的消费收回，只从冻结档位 + 当次显式入参推导；
  (c) **最低限度**：把 `:22-30` 那段 G-4 免责声明改写成实况（否则它是一条会误导人的假注释）。
  ⚠️ (c) 只解决误导、不解决可篡改。

### MINOR-1 `require_ep` / `confirmation_policy` / `judge_enabled` 在同一个 run 内有两个权威

- **位置**：`run_stage.py:1689-1703`（只替换 2 项）vs `run_policy_freeze.py:326-335`（从 context 取 4 项）
- **一句话失败场景**：一个 run 先被 `flow --to 5_intakeoutput`（无 `--with-ep`）跑过一次 ⇒ 冻结 context 记下
  `require_ep=false`；随后 `flow --with-ep --record` 复跑时 `provision_run_policy` **幂等返回旧记录、不更新 context**
  ⇒ **`record_baseline` 拿到的 `require_ep` 是 `false`**，尽管本次调用明确要求了 EP。
  （实际后果被 `_flow_ep`「EP 未产出 `eplusout.end` 即返回错误码」兜住 ⇒ 故判 MINOR 而非 MAJOR。）
- **另一半**：`_policy_with_frozen_tier` 的 docstring 声称 caller 只保留
  「draw budget 与 re-reader 可用性」两个旋钮，**与实况不符** —— 它实际还把
  `require_ep` / `confirmation_policy` / `judge_enabled` 全留在了 caller 侧。

### MINOR-2 `record_baseline` 的 `--require-ep` / `--run-profile` 已成哑弹，argparse 仍在广告它们

- **位置**：`scripts/tool_scripts/record_baseline.py:489-490`（参数）/ `:877-883`（argparse）/ `:889`（透传）
  + `scripts/tool_scripts/run_stage.py:2317-2318`（flow 侧仍在传这两个已死的参数）
- **一句话失败场景**：有人跑 `record_baseline.py <case> <run> --require-ep --run-profile regression`
  期待一次严格档记账，**两个旗标都被静默忽略**，落盘的是 legacy/exploratory 记账；
  唯一的提示是 `baseline["run_policy"]` 头部（要主动去看才看得见），**命令行不报任何错**。
- **出口**：要么让这两个旗标在与冻结档冲突时**显式报错**（fail-closed，符合本项目口径），
  要么删除旗标 + 删掉 `run_stage.py:2317-2318` 的透传。**⛔ 不建议保留现状** ——
  「广告了但静默不生效的严格档旗标」正是本批要修的那个病的一个小号。

### MINOR-3 `cmd_judge` 的 `_policy_with_frozen_tier` 是一次空动作

- **位置**：`scripts/tool_scripts/run_stage.py:2046`
- **说明**：`cmd_judge` 构造的 `policy` 只被送进 `submit_verdict`（`:2063`），
  而 `submit_verdict` / `_verdict_outcome` **从不读 `run_profile` / `capability_profile`**（见 T-2）。
  ⇒ 这行接线**不改变任何行为**。不是缺陷，但会让人误以为 judge 路径的档位已被冻结政策管住 ——
  **实际上 judge 路径压根不看档位**。建议加一行注释说明，或删除。

### NIT-1 `cmd_flow` golden 告警的 `args → policy` 改动零锁
`run_stage.py:2305`。摘掉即回退，全仓无红。后果仅为**少打印一行 golden 人核建议**，故仅 NIT。

### NIT-2 `_draw_reading` 的 legacy 分支在 flat-flow 下已成死码
`run_stage.py:218-222`：`if policy_record.legacy_defaulted: eff_capability = policy.capability_profile`。
由于 `cmd_run` / `cmd_flow` 在建 policy 前必先 `provision_run_policy`，`policy_record` 永远是
`structured_config`；且 R1-5 之后 `policy` 的档位本身也已被换成冻结档 ⇒ 该分支的注释
（「A legacy run without one **keeps its CLI policy**」）在 flat-flow 路径上**已不再描述事实**。
无功能后果，属注释腐化。

---

## 4. 我证伪失败的尝试（反向坐实，价值不低于发现缺陷）

1. **想找「仍在消费局部/默认 `RunPolicy` 而能影响判定」的路径 —— 没找到。**
   全仓 `RunPolicy(` 构造点共 5 处生产命中：`step_orchestrator.py:358/378`（已核为纯操作旋钮）、
   `validation_run.py:89`（`policy or RunPolicy()` 兜底，但**全部生产调用者都显式传 policy**）、
   `run_stage.py:1673`（`_make_policy`，其产物随后即被 `_policy_with_frozen_tier` 覆盖档位）、
   `run_policy_freeze.py:326`（`effective_run_policy` 本体）。**T-2 的机制侧站得住。**
2. **想证伪施工方对 `submit_verdict` 的披露（怀疑它偷偷用了档位）—— 失败。**
   逐行核实这两个函数只读 `reading_runner_available` 与 `budget.per_stage_draws`。**披露属实。**
3. **想构造「baseline 记账冒充 regression」—— 失败。** 只能构造出**低报**（legacy 冒充不了严格档），
   方向与本项目底线一致。T-3 的 fail-safe 方向是对的。
4. **想在 4 条新锁里找假锁（断言落在「存在 / 数量变了」上）—— 失败。**
   4 条锁的断言全部落在 `CheckReport.run_profile` / `.capability_profile` 头部字段与
   `downstream.build` 这个**具体 check-id** 上，形状完全合规，
   且 N1/N3/N5/N8 逐次证明它们摘掉实现真的会红。**这一点上 R1-5 明显吸取了 W4「非 None ≠ 成功」的教训。**
5. **想找「一处实现被多条锁覆盖、其中一条空转」—— 失败**（详 T-1）。
6. **想让 T-6②③ 不成立（找 gt / manifest 被顺手改动）—— 失败。** 本 commit 对 `case_tests/` 零触碰。

**探针留档**：T-5 的 8 个构造（A/B/C/D/E/F/G/H）与 8 次 neuter 的驱动脚本落在
`<scratchpad>/{neuter.sh,n1..n8.py}`，全部在 `/tmp` 克隆内执行，主工作树零改动。

---

## 5. 独立全量测试

**命令**（主工作树，`-n 4`，⛔ 无 `-m` 过滤）：

```
python -m pytest -q -n 4
```

**尾部输出原文**：

```
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2089 passed, 10 xfailed, 165 warnings in 530.30s (0:08:50)
EXIT=0
```

⇒ **2089 passed + 10 xfailed + 0 failed，与 orchestrator 轻门基线逐字一致、零红。**

**⚠️ 但请注意本单的核心结论正建立在「全绿」之上**：
`c56cbe1` 的三处实现（N4 / N6 / N7）**摘掉之后这 2089 条依然全绿** ——
**「全仓 2089 绿」在这三处上不构成任何证据。**（§2.1 为此另跑了三轮全量对照。）

clone 内 N6 / N4 的全量复跑确认见 **§2.1**。
