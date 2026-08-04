# R1 批 B · r2 + r2b · orchestrator 轻门

- **日期**：2026-08-04（北京时间 05:15）
- **被审对象**：r2（`6ff9f4e` → `25b94dc`）+ r2b（`2ea029f` → `26a14cb`），施工 = **GLM**（同一席位两轮）
- **性质**：orchestrator 轻门 = **唯一权威门**。本文只覆盖 r2/r2b；批 C 未开工。
- **上游**：[r2 派工单](../request/2026-08-04_reading_ruler_r1_batchB_r2_dispatch.md) ·
  [r2-3/r2-4 裁定 + r2b 续派](../request/2026-08-04_reading_ruler_r1_batchB_r2b_ruling_and_dispatch.md)

---

## 0. 总判定：**四条全部落地，轻门通过（带 1 条 MINOR 移交交叉审）**

| 条目 | 修的是 | commit | 状态 |
|---|---|---|---|
| **r2-1** | `capability_profile` 拼错一字母仍静默降 `rectangular`（批 B 立项事实的另一半） | `6ff9f4e` + `b9923f0` | ✅ |
| **r2-2** | 冻结记录 `source` 硬编码常量 ⇒「带来源」名存实亡 + 一条恒真断言 | `d601130` | ✅ |
| **r2-3** | `_policy_with_frozen_tier` = 恒空操作 + 假 docstring ⇒ 删冗余 / judge 路内联 | `2ea029f` | ✅ |
| **r2-4** | `context` 已成判定面却在漂移面外 ⇒ 按 (b) 收回消费、降为非权威快照 | `7dc31bd` | ✅ |

**独立全量**（orchestrator 自跑 `pytest -q -n 6`，工作树干净、⛔ 无 `-m` 过滤）：

```
2095 passed, 10 xfailed, 171 warnings in 348.96s (0:05:48)
```

**与施工方自报逐数字一致。** 起点 2089（r1 末）→ 2095，**净增 6 条锁、零回归**。

---

## 1. ⭐ 独立 neuter 六处（**本轮选点刻意覆盖每条正文实现——这正是我上一轮栽的地方**）

**方法**：`/tmp` 克隆（HEAD `26a14cb`），每次只改一处 → 跑受影响子集 → `git checkout -- .` 复原（每轮均验证工作树零残留）。

| # | 摘掉哪一处实现 | 红了哪几条 | 连带 | 判定 |
|---|---|---|---|---|
| **A** | `effective_run_policy` 档位回落 `RunPolicy()` 全默认（`run_policy_freeze.py`） | `test_R1_5_approve_geometry_uses_frozen_policy_check_headers`、`test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers` | 零 | ✅ **改写后仍真绑**（裁定 §2.2#4 的硬要求） |
| **B** | 恢复 `context` 消费（= r2-4 病灶原状） | `test_R1_5_record_baseline_context_tamper_does_not_change_blocking` | 零 | ✅ 新篡改面锁真绑 |
| **C** | `_parse_capability_profile` raise → warn+None | `test_r2_1_flow_typo_capability_profile_fails_closed`（走真实 `cmd_flow`）、`test_run_config_invalid_capability_profile_fails_closed` | 零 | ✅ 真绑，且**CLI 与单元两层都有** |
| **D** | `_resolve_run_profiles` 的 source 三态 → 硬编码 `structured_config` | `test_r2_2_cli_only_run_source_is_cli`、`test_r2_2_mixed_decl_source_is_mixed`、`test_R1_2_absent_run_profile_still_cli_authoritative`、`test_r2_1_absent_capability_profile_still_cli_authoritative` | 零（后两条本就断言 source 语义） | ✅ 真绑 |
| **F** | `_draw_reading` 的冻结档读取 → `"exploratory"` | `test_R1_1_flow_regression_freezes_to_reading_checks_header` | 零 | ✅ **删掉冗余层后真正承重的那条线，锁住了** |
| **E** | `record_baseline` 的 `effective_run_policy(...)` → `RunPolicy(require_ep=require_ep)`（**只摘档位、保留调用方开关**） | **零条** | — | ⛔ **见 MINOR-1** |

**⇒ 五处真绑、零假锁、零连带。** 其中 **F 是本轮最关键的一次**：r2-3 删掉了那层冗余，
**必须证明「冻结档到达 `checks.json`」这条性质仍有锁守着** —— 摘掉 `_draw_reading` 的冻结档读取，
`test_R1_1_flow_regression_freezes_to_reading_checks_header` 恰好红。**删除是安全的。**

---

## 2. ⛔ MINOR-1（本轮唯一发现，移交交叉审定级）：记账那条锁绑的不是它自称绑的东西

- **位置**：`tests/test_orchestrate_baseline.py:44` `test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback`
  + `scripts/tool_scripts/record_baseline.py:507-512`
- **它的 docstring 自称**：「Neuter: replace `effective_run_policy` with `RunPolicy()` … ⇒ the tier header drops
  to exploratory/rectangular and downstream.build disappears ⇒ **reds**」。
- **实测（neuter E）**：**只把档位摘掉、保留调用方 `require_ep`** ⇒ **零条红**。
- **原因**：该锁的头部断言（`run_profile == "regression"` 等）读的是 `baseline["run_policy"]`，
  而那个头部来自函数里**另一行** `frozen = resolve_frozen_run_policy(run_dir)`，
  **不是**来自喂给 `validate_case` 的那个 `policy` ⇒ 头部断言**证明不了「冻结档位真的进了校验」**。
  真正让它红的是 `require_ep`（**调用方旋钮**）带出的 `downstream.build` 行。
- **⇒ 性质**：**不是生产码缺陷，是锁的强度问题**，且**恰是本项目反复栽的那一族**
  （「锁看着绑、其实绑的是另一个东西」——W4 的 `is not None` / r0 的 L-13 / 昨夜的旁支 neuter）。
- **出口**：fixture 里放一条**只在 `regression` 下阻断、`exploratory` 下不阻断**的检查，
  使「档位是否真的进了 `validate_case`」在断言上可见。**⚠️ 与 D-2 一并处理，不单独开一轮。**
- ⚠️ **如实登记**：上一轮 Claude 侧交叉审做同族 neuter（N1）时**红了 2 条** —— 那是 **r2b 改写这两条锁之前**的状态。
  **r2b 的改写在方向上正确（require_ep 不该来自冻结 context），但顺手削弱了档位那一维的断言。**

---

## 3. 施工方两次「停下上报」的处置回顾（本轮最有价值的部分）

**GLM 两次拒绝按派工单硬做，都被证明是对的，且两次都改掉了 orchestrator 的题**：

- **r2-3**：我要它给 `_policy_with_frozen_tier` 补锁。它实跑证明该函数是**恒空操作**（run/flow 因 provisioning 在其之前、
  散度被 drift 门拦截），**拒绝伪造一条 neuter 不红的假锁**。
  orchestrator 核实属实，**并补齐它没分析的第三条路**（`cmd_judge` 从不 provision、用 argparse 默认档，
  但其唯一消费者 `submit_verdict` 根本不读档位 ⇒ 同样恒空）。
  ⇒ 处置从「补锁」改判为**删冗余 + 改掉那句声称自己在守的假 docstring + 引用既有锁**。
- **r2-4**：我给的 (a)「把 context 纳入哈希」它论证**挡不住篡改**（哈希是 payload 自身哈希、可自行重算，
  防漂移的唯一外部根是 `run_config.yaml`，而 `require_ep` 不在其中）。**orchestrator 采纳并立了通用判据**：
  > **只有在 `run_config.yaml` 里声明的东西才有外部信任根，才配被冻结成档位政策并参与防漂移；
  > 命令行的运行期开关一律来自当次调用、不冻结、不据以判定。**
  （这是 terra 在 R1-5 自己划、我在 r1 轻门批准过的那条线的另一侧 ⇒ 统一成一条。）

**⇒ 「停下上报」这条纪律今晚产生了本批最高价值的两次修正。** 两次都是**派工方的题错了**，不是施工方没做到。

---

## 4. 边界合规

| 项 | 结论 |
|---|---|
| `gt/**` 与 sm24 `testdata_prompt.json` 零字节改动 | ✅（`git diff --name-only 48e41b6..HEAD` 零命中） |
| 未 push | ✅（本地 7 个 commit 未推） |
| 未动管理文档（除自己执行日志） | ✅ |
| 批 C 未顺手做 | ✅（半截仍在 `git stash`） |
| 假注释清理 | ✅ G-4 免责声明与 `_policy_with_frozen_tier` docstring **两处假声明本轮一并消除** |

---

## 5. 下一步

1. **Claude 侧子代理交叉对抗审 r2 + r2b**（用户 08-03 定：本批不再启 GPT 侧；施工 = GLM ⇒ 审 = Claude，「谁写谁不批」满足）。
   **MINOR-1 作为承重命题之一交给它定级**，并请它找同族（还有没有别的锁绑的是「另一条路径算出来的值」）。
2. 交叉审若无 BLOCKER ⇒ 批 B 收口；**D-2 / D-3 / D-4 + MINOR-1 一并归 R2 债**。
3. **之后才是批 C**（渲染 / 命名 / 像素预算）。
4. **⛔ 约束不变**：批 A/B/C 三批全绿之前，不得发布任何识图分数或「识图变好/变坏」的结论。

---

## 6. 追加：r2c 轮（交叉审 findings 收尾）· orchestrator 复验

- **r2c 派工单**：[2026-08-04_reading_ruler_r1_batchB_r2c_dispatch.md](../request/2026-08-04_reading_ruler_r1_batchB_r2c_dispatch.md)（4 条，全是锁强度）
- **实际落地**：**只落 r2c-1（那条 MAJOR）** = `a231cc3`。施工席 **05:59 撞 GLM 5 小时额度上限**（07:13 复位）
  ⇒ **r2c-2 / r2c-3 / r2c-4 三条 MINOR 未做**，如实登记为债（见 §7）。

**r2c-1 复验（orchestrator 独立 neuter，`/tmp` 克隆 HEAD `a231cc3`）**：

改动本身是**行为保持**的两行取值修正 —— `baseline["run_policy"]` 的**档位两字段**改从
`policy`（= 喂给 `validate_case` 的那个 effective policy）取，**溯源字段仍取 `frozen`**
（镜像 `step_orchestrator.approve_geometry:494-495` 的拆分），另加一条「只在 `regression` 下阻断」的 fixture 检查。

| neuter | r2c-1 之前 | r2c-1 之后 |
|---|---|---|
| `record_baseline` 的 `effective_run_policy(...)` → 自搓 `RunPolicy(require_ep=require_ep)`（**只摘档位、保留调用方开关**） | **零条红**（全仓 2095 条，轻门与交叉审各自独立复现） | **恰好红 3 条**：`test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback` · `test_R1_5_record_baseline_regression_tier_surfaces_blocking_check_row`（新增） · `test_R1_5_record_baseline_context_tamper_does_not_change_blocking`，**零连带** |

⇒ **MAJOR（F-1 / 轻门 MINOR-1）已消除，锁真绑。**

**独立全量**（orchestrator 自跑 `pytest -q -n 6`，工作树干净、⛔ 无 `-m`）：

```
2096 passed, 10 xfailed, 177 warnings in 358.50s (0:05:58)
```

**2089（r1 末）→ 2096，净增 7 条锁、零回归。**

---

## 7. 批 B 收口状态 + 结转债

**⇒ 批 B 收口**：生产码零已知缺陷（交叉审四次证伪失败反向坐实）· 全仓零红 · 边界零违反 ·
唯一 MAJOR 已修并经独立 neuter 证明真绑。

**结转 R2 的债（逐条有出口，不阻断收口）**：
| 债 | 内容 | 出处 |
|---|---|---|
| ~~r2c-2~~ | ~~两条 geometry 锁丢了 check-id 行断言~~ **⇒ 已闭，见 §8 更正** | 交叉审 F-4 |
| **r2c-3** | `tests/test_orchestrate_baseline.py:106-109` 恒真断言，分辨力 0 | 交叉审 F-3 |
| **r2c-4** | `capability_profile_not_declared` 守卫零锁（可达但无锁） | 交叉审 F-5 |
| **F-2** | `tests/test_orchestrate_baseline.py:160` 注释误述「frozen tier still consumed」（只需改注释） | 交叉审 F-2 |
| **N-1** | judge 路 run-policy 漂移在同一命令下两种出口（`return 2` vs traceback）·**前置存在、不计本批** | 交叉审 N-1 |
| ~~Q-8 措辞~~ | **✅ 已闭（2026-08-04 用户拍板）**：改为「两道检查题 + 在册清单」，全文落 [decision_log §5.14](../../../decision_log.md) | 交叉审 Q-8 |
| **D-2 / D-3 / D-4** | `GeometryApproval` 四字段零消费者零锁 · L-13 锁仍直喂 `None` · judge 路若出现 tier 消费者须补锁 | 08-03 两路交叉审 + r2b 裁定 |

**⛔ 约束不变**：批 A/B/C 三批全绿之前，不得发布任何识图分数或「识图变好/变坏」的结论。**批 C 尚未开工。**

---

## 8. ⛔ orchestrator 记账更正（2026-08-04 09:40）：r2c-2 其实已完成，且被我扫进了 wrap-up 提交

**事实**（施工席复工后报出、orchestrator 用 `git log -- <file>` 独立核实）：

- 施工席 05:59 撞额度中断时，**r2c-2 的改动已写在工作树、但未提交**；
- orchestrator 06:30 收工执行 `git add -A && git commit`，**把这些未提交的测试代码一并扫进了 `6e06ecf`**
  —— 而那条提交的信息只写了「管理文档同步」，**实为含代码改动**，且已推 origin。
- ⇒ **§7 结转债清单里「r2c-2 未做」是错的**，本节更正；plan.md 顶部同步更正。

**两点如实说明**：
1. **测试口径没出岔**：§6 那次全量 `2096 passed` 跑的就是**含这些改动的工作树**
   ⇒ 已验证状态与推上去的状态一致，**不存在「测的是 A、推的是 B」**。
2. **但提交信息与内容不符**，且已 push ⇒ **不 force push 改历史**（项目禁令），
   改为在此登记 + 施工席执行日志 `## 9` 同步记明「r2c-2 落在 `6e06ecf`，非独立 commit」。

**⇒ 教训（与「哨兵判据不得落在第一个匹配上」同族）**：
> **收工的 `git add -A` 会把并行席位遗留的未提交工作一并收走。**
> 席位中断后、orchestrator 提交前，**必须先看一眼 `git status` 里有没有不属于本次提交的改动**
> （本轮我只核了「未 push / 未碰 gt / 未动管理文档」这三项边界，**没核「工作树里有没有别人的半成品」**）。

**r2c-2 的锁 orchestrator 已独立复验为真绑**（本节结论，非采信自报）：
除施工席做的 A1（`effective_run_policy` 档位回落默认 ⇒ 红 4 条，四条共享同一 hook、属同源非连带），
orchestrator 另做**更窄的 neuter** —— 只把 disposition 的档位门去掉
（`ReportSchema.dispositions()` 里 `run_profile=self.run_profile` → 写死 `"exploratory"`，**头部字段一字不动**）
⇒ **恰好红 `test_R1_5_approve_geometry_uses_frozen_policy_check_headers` 与
`test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers` 两条**
⇒ **新增的 check-id 行断言真承重，不是装饰。**

**并立判据（已告知施工席，以后照此办）**：
> **「零连带」= 摘掉实现后红的都是依赖这处实现的锁，没有无关测试被带红；
> 不是「红的条数必须等于本条目的锁数」。** 多条锁共享同一 hook 时同源全红是正常的。
