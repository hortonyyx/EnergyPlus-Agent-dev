# R1 批 B · r2 + r2b · 交叉对抗审（Claude 侧 · Opus 档）

> **本文最终版**

- **日期**：2026-08-04
- **审阅席**：Claude 侧交叉对抗审（Opus 档子代理），由 orchestrator 派工
- **被审对象**：`48e41b6..26a14cb` 共 7 个 commit（r2 = `6ff9f4e` `d601130` `b9923f0` `25b94dc` · r2b = `2ea029f` `7dc31bd` `26a14cb`）
- **施工席**：GLM（跨家族，「谁写谁不批」满足）
- **上游**：[orchestrator 轻门](2026-08-04_reading_ruler_r1_batchB_r2_orchestrator_lightgate.md) ·
  [r2 派工单](../request/2026-08-04_reading_ruler_r1_batchB_r2_dispatch.md) ·
  [r2-3/r2-4 裁定](../request/2026-08-04_reading_ruler_r1_batchB_r2b_ruling_and_dispatch.md) ·
  [执行日志 §7 §8](../execution/2026-08-03_reading_ruler_r1_batchB_glm.md)
- **纪律自证**：全部破坏性探针在 `/tmp` 克隆内（`probe` / `probe2` / `probe_base`）；主工作树零改动、零 commit、零 push、
  全程只跑只读 git（未跑 `git status`）；未读 `case_tests/test_baseline/gt/**`。

---

## 0. 总判定：**APPROVE-WITH-CHANGES**

| 级别 | 数 | 条目 |
|---|---|---|
| **BLOCKER** | **0** | — |
| **MAJOR** | **1** | F-1（Q-1 定级：记账那条锁绑不住它自称绑的档位维度，且全仓无第二条锁替补） |
| **MINOR** | **4** | F-2 / F-3 / F-4 / F-5 |
| **NIT** | **1** | N-1 |
| **证伪失败（反向坐实）** | **4** | Q-2 删除安全 · Q-3 judge 路无新问题 · Q-4 篡改面真消失 · Q-6 source 三态无洞 |

**四条正文（r2-1 / r2-2 / r2-3 / r2-4）全部落地且方向正确。生产码零缺陷 —— 本轮全部 finding 都是「锁的强度 / 声明的真实性」问题。**
唯一的 MAJOR 与 orchestrator 轻门的 MINOR-1 是同一条，**我定级为 MAJOR**，理由见 §1。
**不阻断批 B 收口**：出口很小（照抄仓库里已有的正确写法），可与 D-2 一并归 R2 债。

---

## 1. Q-1（最高权重）：定级 **MAJOR**，并找到 4 个同族

### 1.1 独立复现：确认，且比轻门测到的范围更宽

**neuter E**（`scripts/tool_scripts/record_baseline.py:512`，**只摘档位、保留调用方 `require_ep`**）：

```python
-    policy = effective_run_policy(run_dir, require_ep=require_ep)
+    from src.agent.execution.policy import RunPolicy as _RP  # NEUTER-E
+    policy = _RP(require_ep=require_ep)  # 档位丢失，调用方旋钮保留
```

| 范围 | 结果 |
|---|---|
| `tests/test_orchestrate_baseline.py` | **34 passed, 1 xfailed — 零红** |
| `+ test_provenance_baseline.py + test_run_stage_flow.py` | **39 + 35 passed — 零红** |
| **全仓 `pytest -q -n 4`（克隆内）** | **2081 passed, 8 skipped, 10 xfailed, 6 failed** |

那 6 条 failed **与 neuter 无关**：在**同一份未改动的克隆**上跑同样 6 条，**逐条同样红**
（`test_reading_score` / `test_checks_reading_correction` / `test_validation_run_baseline` /
`test_inspect_dxf` / `test_gt_from_dxf` / `test_zone_agent`）——克隆缺 gitignored 的活输入与 API 凭据所致
（与 memory 里登记的「根 `logs/experiments/` 是活输入却不在 git 里」同一根因）。
**⇒ 失败集合与克隆基线逐条相同 ⇒ 全仓 2095 条测试里没有任何一条抓得住这次 neuter。**

### 1.2 断言维度分离：三个 neuter 变体把话说死

我把 `effective_run_policy` 的两个维度（**冻结档位** / **调用方旋钮**）拆开各摘一次
（子集 = `test_orchestrate_baseline` + `test_run_stage_flow` + `test_provenance_baseline` + `test_reading_ruler_r1_batchB`，共 94 条）：

| 变体 | 摘掉什么 | 红了哪几条 |
|---|---|---|
| **A1** | `effective_run_policy` → `RunPolicy()` 全默认（= 三条锁 docstring 自称的那个 neuter） | **3 红**：`test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback` + 两条 geometry 锁 |
| **A3** | 保留冻结档位，**只丢调用方旋钮**（`require_ep`/`confirmation_policy`/…） | **1 红**：只有 `test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback` |
| **E** | 保留调用方旋钮，**只丢冻结档位**（在 `record_baseline` 调用点） | **0 红（全仓）** |

**⇒ 结论精确到维度**：那条锁**绑的是 `require_ep` 这一维**（A3 证明），
**完全不绑「冻结档位到达 `record_baseline` 的 `validate_case`」这一维**（E 证明）。
它在 A1 下变红，**是因为 A1 顺带把 `require_ep` 也摘了**，不是因为档位。

### 1.3 根因：`record_baseline` 的头部结构上就见证不了 `effective_run_policy`

`scripts/tool_scripts/record_baseline.py:507-545`：

```python
frozen = resolve_frozen_run_policy(run_dir)          # :507  ← 头部的唯一来源
policy = effective_run_policy(run_dir, require_ep=require_ep)  # :512  ← 喂给 validate_case
res = validate_case(run_dir, policy=policy, write_reports=False)
...
"run_policy": {
    "source": frozen.source, "legacy_defaulted": frozen.legacy_defaulted,
    "run_profile": frozen.run_profile, "capability_profile": frozen.capability_profile,
    "policy_hash": frozen.policy_hash,                # :539-545 —— 五项全部来自 frozen
},
```

`baseline["run_policy"]` 的五个字段**全部**取自 `frozen`（第 507 行），与第 512 行的 `policy` **没有任何数据依赖**。
⇒ 断言这个头部，**永远**只能证明「冻结记录里写着 regression」，**证明不了「regression 进了校验」**。

**⭐ 仓库里就有正确写法作对照 —— 同一批 R1-5 的另一个调用点做对了**：
`src/agent/execution/step_orchestrator.py:484-496`（`approve_geometry`）把两个来源**拆开用**：

```python
frozen    = resolve_frozen_run_policy(run_dir)
effective = effective_run_policy(run_dir)
res = validate_case(run_dir, case_dir=case_dir, policy=effective)
appr = GeometryApproval(
    run_policy_source=frozen.source,            # 溯源字段 ← frozen
    run_policy_legacy_defaulted=frozen.legacy_defaulted,
    run_profile=effective.run_profile,          # ⭐ 档位 ← effective
    capability_profile=effective.capability_profile,
)
```

**⇒ 出口（比轻门给的更小）**：把 `record_baseline.py:542-543` 两行的 `frozen.` 改成 `policy.`
（`source` / `legacy_defaulted` / `policy_hash` 仍归 `frozen`），即与 `approve_geometry` 对齐 ——
改完 neuter E 立刻会红，**不需要造新 fixture、不需要新加检查**。
轻门给的「fixture 里放一条只在 regression 下阻断的检查」是更强的第二层（与 `test_L10/L11` 同形，见 §1.4），可一并做。

### 1.4 定级理由：为什么是 MAJOR 不是 MINOR

1. **一条承重性质在全仓 2095 条测试里零覆盖**（§1.1 全仓级实测）。R1-5 的立项句就是「让冻结的档位成为整个 run 的档位」，
   `record_baseline` 是它三个正文面之一；今天在这一面上做任何回归都会静默通过。
2. **它的 docstring 正在声称自己守着这件事**（`tests/test_orchestrate_baseline.py:52-58`：
   *"replace effective_run_policy with RunPolicy() … ⇒ the tier header drops to exploratory/rectangular"*）——
   **这句因果解释本身是错的**：头部不来自 `effective_run_policy`，档位掉了头部也不会变。
   **这正是 r2-3 被立项要消灭的那一族**（「一个模块/一条锁声称自己在守某个不变量，其实没在守」）：
   **r2b 消灭了 `_policy_with_frozen_tier` 的假 docstring，同一轮又造出一条新的假 docstring。**
3. **本项目对该族的既有量刑就是 MAJOR/BLOCKER**（W4 的 `is not None`、r0 的 L-13、B4b 的豁免位）。
4. **对照组存在**：`test_L10_isolation_policy_truth_regression_blocks`（`tests/test_reading_ruler_r1_batchB.py:520-542`）
   证明这个项目会写强档位锁 —— 它断言 `len(report.blocking()) == 4`，**一个只在 regression 下成立的 disposition**，
   档位一掉就红。**能力在、这一处没用上。**

**减轻情节（故不升 BLOCKER）**：① 生产码**是对的**（`effective_run_policy` 本身被两条 geometry 锁真绑，A1 已证）；
② 该缺陷是 r2-4 改写的**副作用**，而 r2-4 的主方向（收回 context 消费）经我实跑证明是正确且彻底的（Q-4）；
③ 出口只有两行。

### 1.5 ⭐ 同族普查（Q-1 ③）

**方法**：① 全仓 `grep` 所有自称 `Neuter` 的锁（5 个文件 45 处）逐条比对「断言读的值的写入路径」vs「docstring 自称的机制」；
② 全仓 `grep` 对 `run_policy`/`run_profile`/`capability_profile`/`run_policy_source` 的断言（24 处）逐条溯源；
③ 对每个可疑点实跑 neuter。**结果 = 找到 4 个同族，全部集中在 r2-4 改写的这三条锁附近，没有扩散到别的子系统。**

| # | 位置 | 形状 | 级别 |
|---|---|---|---|
| **F-1** | `tests/test_orchestrate_baseline.py:44-83` | 见 §1.1–1.4 —— 断言读 `frozen`，自称证明 `effective` | **MAJOR** |
| **F-2** | `tests/test_orchestrate_baseline.py:160` 注释 | 同一族第二例，**r2-4 本轮新落**：注释写 *"frozen tier still consumed"*，但读的仍是 `baseline["run_policy"]`（来自 `frozen`）⇒ 它见证的是「冻结记录没被篡改」，**不是「档位被消费了」**。该锁**承重的那条断言（篡改后 `downstream.build` 仍不出现）是真绑的**（我复跑 neuter B 恰好红 1 条），只是这两行注释误述。 | MINOR |
| **F-3** | `tests/test_orchestrate_baseline.py:106-109` | **恒真断言**：`not any(downstream.build)`。r2-4 之后 `require_ep` 只来自调用方，该测试传 `require_ep=False` ⇒ 该行**对任何 run 都不会出现**。实跑证明：`PROBE-F3 downstream.build present: frozen_regression=False legacy=False` ⇒ 它**分不开 legacy 与冻结 regression**。（该锁的另外四条 tier 断言仍真绑，故只是内含一条空转断言 —— **与 r2-2 本轮刚修掉的那条恒真断言同形**。） | MINOR |
| **F-4** | `tests/test_run_stage_flow.py:1084-1157` | 两条 geometry 锁在改写中**丢掉了全部 check-id 行断言**（原 `any(row.check_id == "downstream.build" …)`），现在只断言 report 头部字段 + `"downstream" not in reports`。**锁仍真绑**（A1 恰好红这两条），但违 r2 派工单 §2.2「断言落在具体 check-id 行 **+** `checks.json` 头部字段」——**只剩头部那一半**。 | MINOR |
| **F-5** | `src/agent/execution/run_policy_freeze.py:168-173` | r2-1 新增的 `capability_profile_not_declared` 守卫**零锁**。**neuter G**（`if False and …`）⇒ **302 passed 零红**。且它**不是不可达**：实跑 `provision_run_policy(run, run_profile="regression", capability_profile=None)` ⇒ `ValueError: capability_profile_not_declared`（`PROBE-F5`）。**GLM 在 commit message 里如实披露了这一点**（"CLI 不可达 … neuter point2 两条 CLI 锁皆绿"），故只判 MINOR：违的是本项目 standing 纪律「每条新守卫必须有摘掉即红的锁」，不是隐瞒。 | MINOR |

**同族边界（如实登记我查过但判定不成立的）**：
- `test_R1_1_flow_regression_freezes_to_reading_checks_header`（R1-1c）：断言 `checks.json` 头部，而该头部由
  `run_stage.py:218-229` 的**另一次** `resolve_frozen_run_policy` 写入、**不是**来自 `policy` ——
  形状上像同族，**但它的 docstring 自称的 neuter 是 `_resolve_run_profiles` 回退，而那条路会同时改变冻结记录 ⇒ 头部真的会变** ⇒ **自称与实际一致，不入族**。
  （我另跑 neuter F 复现轻门：摘掉 `_draw_reading` 的冻结档读取 ⇒ **恰好红 1 条 R1-1c、零连带**。）
- `approve_geometry` 的 `GeometryApproval.run_profile`：来自 `effective`（见 §1.3）⇒ **正确，不入族**。
- `test_L10/L11`（isolation 档位真相）：断言 disposition 计数（`len(report.blocking()) == 4` / `== []`），
  **档位是该断言的必要条件** ⇒ **强锁，不入族**。

---

## 2. Q-2：r2-3 删除 **安全**（我的证伪尝试失败，反向坐实）

### 2.1 三处调用点确实曾是恒空操作 —— 成立

- **`cmd_run`（原 :1946）/ `cmd_flow`（原 :2143）**：`policy` 由 `_make_policy` 用 `_resolve_run_profiles` 的结果构造
  （`run_stage.py:1933-1948` / `2139-2158`），随后 `_manifest_for_attempts` → `provision_run` → `provision_run_policy`
  用**同一对值**冻结。`provision_run_policy`（`:260-277`）在记录已存在时：
  `legacy_defaulted` ⇒ raise；`policy_hash` 不等 ⇒ raise；否则返回的 `existing` 与请求**逐字段相等**。
  ⇒ **冻结档恒等于当次 resolved 档，override 恒空。** 成立。
- **`cmd_judge`（原 :2046）**：见 Q-3。成立。

### 2.2 ⛔ 我按要求去构造「删除后失守且无锁会红」的路径 —— **构造失败**

**探针 Q2**：直接模拟「组装出来的 policy 丢了冻结档位」（= `_policy_with_frozen_tier` 原本负责修复的那个形态）：

```python
# scripts/tool_scripts/run_stage.py :1691-1697  _make_policy
-        run_profile=run_profile,
-        capability_profile=capability_profile,
+        run_profile="exploratory",          # NEUTER-Q2
+        capability_profile="rectangular",   # NEUTER-Q2
```

**⇒ 5 条红**：`test_R1_1_flow_config_run_profile_overrides_cli_default` +
`test_flow_run_config_capability_profile_overrides_only_when_present`[×2] +
`test_cmd_run_config_capability_profile_overrides_only_when_present`[×2]。
这几条锁在 `_make_draw_fn` 处捕获 `policy`（`tests/test_run_stage_flow.py:709-711`
`seen.append((policy.run_profile, policy.capability_profile))`）——
**`_make_draw_fn` 正是 correction / modelling / grade / typed-scoring 拿到 policy 的那一道口** ⇒ **这四个面有锁。**

**另外三条路我逐条查了，都走不通**：
| 我试图构造的失守路径 | 为什么走不通 |
|---|---|
| resume 时 CLI 给了不同档位 | `provision_run_policy` 比 `policy_hash` ⇒ `run_policy_drift` raise（fail-closed） |
| 冻结后编辑 / 删除 `run_config.yaml` | 同上；且 `resolve_frozen_run_policy` 另有 `_declared_policy` 复核 |
| 绕过 provisioning 到达 policy 消费 | `provision_run` 无条件调 `provision_run_policy`（`run_provision.py:96-103`）；`_manifest_for_attempts`（`run_stage.py:170-178`）在 V1 拒绝之后**无分支地**调 `provision_run` |

### 2.3 「冻结档到达 checks.json」仍有锁守着 —— 成立

**neuter F**（`run_stage.py:226-227` 的 `eff_capability` / `eff_run_profile` 硬写成 `rectangular`/`exploratory`）
⇒ **恰好红 1 条**：`test_R1_1_flow_regression_freezes_to_reading_checks_header`，**零连带**。与轻门逐字吻合。

**⇒ Q-2 判定：成立（删除安全）。我未能构造出反例。**

---

## 3. Q-3：cmd_judge 改动 **未引入新问题**（第二次证伪失败）

### 3.1 独立核实：`submit_verdict` / `_verdict_outcome` 确实从不读档位

用 AST 提取三个函数体逐行扫 `run_profile` / `capability_profile` / `policy.`：

```
--- submit_verdict   (337-364): 零命中
--- _verdict_outcome (367-445): 只有 policy.reading_runner_available / policy.budget.per_stage_draws
--- _post_gate1      (294-331): 只有 policy.confirmation_blocks(...) / policy.judge_enabled
```

**⇒ 施工方与裁定的声称成立，我独立复算一致。**

### 3.2 legacy / 缺件 / 损坏 三种形态实跑

我在克隆里对 `cmd_judge` 走真实入口跑了三个探针（`_synthetic_judge_case` fixture）：

| 形态 | 结果 |
|---|---|
| 冻结件在（regression/orthogonal） | ✅ `policy.run_profile == "regression"`、`capability_profile == "orthogonal_polygon"` ⇒ **改动确实生效** |
| 冻结件**缺失**（legacy replay） | ✅ 合成 legacy 记录，不报错（既有 `test_cmd_judge_missing_view_manifest_is_not_applicable` 覆盖） |
| 冻结件与 `run_config.yaml` **漂移** | ⚠️ 抛未捕获 `ValueError: run_policy_drift: run_config.yaml run_profile='regression' differs from the frozen run_policy.json run_profile='exploratory'` |
| 冻结件**损坏** | ⚠️ 抛未捕获 `ValueError: run_policy_drift: frozen run_policy.json is corrupt: 1 validation error…` |

后两行看起来像 r2-3 引入的新失败面（同一命令对 view-manifest 漂移是优雅的 `return 2` + `INVARIANT` 提示，
对 run-policy 漂移却是 traceback）。**我去证伪 —— 证伪成功、对施工方有利**：
把同样三个探针搬到 **r2 之前的 `48e41b6`** 跑，**结果逐条相同**（同样 2 raise、同样 1 passed）。
根因：删掉的 `_policy_with_frozen_tier` **本身就调 `resolve_frozen_run_policy`**，
所以 `cmd_judge` 在 r2-3 之前**已经**会在漂移/损坏时抛。

**⇒ Q-3 判定：r2-3 对 judge 路是行为等价改造，零新问题。**
（那个「view-manifest 漂移优雅、run-policy 漂移 traceback」的不一致是**前置存在的**，不属本批，登记为 N-1。）

---

## 4. Q-4：篡改面 **真的消失了**，不是搬了地方（第三次证伪失败）

### 4.1 实跑篡改（我自己写的探针，不复用施工方的锁）

四格矩阵：{未篡改, 篡改并重算 `content_sha256`} × {调用方 `require_ep=False`, `=True`}，
每格跑真实 `record_baseline.record_baseline(...)`，比对 `json.dumps(baseline["blocking"], sort_keys=True)` **整串**：

```
PROBE-Q4 caller_require_ep=False: identical=True
   downstream.build present: untampered=False tampered=False
PROBE-Q4 caller_require_ep=True: identical=True
   downstream.build present: untampered=True tampered=True
PROBE-Q4 caller knob is load-bearing: False=>no row, True=>row present
```

探针内另断言了**篡改后的记录确实还能加载**（`resolve_frozen_run_policy` 返回 `context.require_ep.value is True`）——
即完整性校验被满足、这是真篡改而不是坏文件。

**⇒ ① 篡改对 `blocking` 输出零影响（整串相等，两种调用方取值下都成立）；
② 调用方旋钮是承重的（False⇒无行 / True⇒有行）⇒ 判定权真的搬到了调用方，而不是消失或换了个可篡改的地方。**

### 4.2 `context` 是否还有判定消费者残留 —— **零残留**

全仓 `grep` 冻结记录 `context` 的读取方：
`record.context` / `frozen.context` / `policy_record.context` / `["context"]` 在 `src/` `scripts/` 下 **零命中**；
`run_policy_freeze.py` 内对 `context` 的引用只剩 **`:34` 与 `:93` 两处注释** 和 `_build_record` 的写入。
`effective_run_policy`（`:329-378`）里原来的 `_ctx` / `_bool_ctx` / `_enum_ctx` 三个取值 helper **已整体删除**。

**neuter B**（把 `require_ep` 改回读 `record.context`）⇒ **恰好红 1 条**：
`test_R1_5_record_baseline_context_tamper_does_not_change_blocking`，**零连带**。与轻门吻合。

**⇒ Q-4 判定：成立。这是本批质量最高的一条 —— 它把「防篡改」从「再加一层哈希」换成了「取消判定入口」，
是结构性消除而非再叠一层「以为守住了」。**

---

## 5. Q-5：三条 R1-5 锁 **仍真绑**，但在**一个维度上被削弱**

| 锁 | 仍真绑？ | 绑的是哪一维 | 我的复跑 |
|---|---|---|---|
| `test_R1_5_approve_geometry_uses_frozen_policy_check_headers` | ✅ | 冻结档位（stage-report 头部） | A1 红 / A3 绿 / E 绿 |
| `test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers` | ✅ | 同上 | A1 红 / A3 绿 / E 绿 |
| `test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback` | ⚠️ **部分** | **只绑调用方 `require_ep`**，不绑档位 | A1 红 / **A3 红** / **E 绿** |

**⇒ 「改写后仍真绑」这条硬要求：前两条完全满足；第三条只在 `require_ep` 这一维满足，档位那一维丢了 = F-1（MAJOR）。**

**⚠️ 与轻门台账的一处数字差异，如实登记**：轻门 row A 记「neuter A ⇒ 红 2 条（两条 geometry 锁）」，
而我按 docstring 字面做的 **A1（`return RunPolicy()` 全默认）⇒ 红 3 条**（多出 record_baseline 那条）。
差异来自 neuter 的具体写法是否保留 `require_ep` kwarg；施工方 commit message 里写的「neuter A ⇒ 三锁均红」**与我一致**。
这个差异不影响结论 —— 反而是它把 F-1 的维度切了出来：**A1 红 3 条掩盖了「档位维度无锁」，A3/E 才把它逼出来。**

**「有没有在别的维度上也削弱」—— 有，见 F-4**：两条 geometry 锁改写后**不再有任何 check-id 行断言**，
只剩 report 头部字段。它们仍真绑（A1 红），但对照 r2 派工单 §2.2 的措辞是**只做到了一半**。
（我认为这一半是 r2-4 语义变更的**必然**结果 —— `require_ep` 收回调用方之后，geometry 门确实不该再产 `downstream.build` 行；
出口应是**换一条在 regression 下才 block 的 check-id**，与 §1.3 给 F-1 的第二层出口是同一件事，可一并做。）

---

## 6. Q-6：r2-1 / r2-2 的锁 —— **走真实 CLI 入口、断言合规、三态无洞**

### 6.1 真实入口

`tests/test_run_stage_flow.py` 的五条新锁**全部经 `rs.cmd_flow(_args(...))`**（真实 CLI 命令函数 + argparse 形状的 `_args`），
不存在 r0 的 L-13 那种「把 `None` 直接喂内部函数」。逐条核过：`:877` `:900` `:933` `:957` `:978`。

### 6.2 断言落点

- **r2-1a**（`:876-880`）：`pytest.raises(ValueError, match="capability_profile_invalid")`
  + **落盘证据**：`_run/run_policy.json` 与 `_run/run_manifest.json` **都不存在**（= 失败发生在冻结之前）。✅ 合规。
- **r2-1b / r2-2 A/B/C**：断言 `resolve_frozen_run_policy(run_dir)` 的**具体字段**（`source` / `run_profile` / `capability_profile`），
  不是「非空 / 总数变了」。✅ 合规。
- ⚠️ **这五条都没有 check-id 行断言** —— 但它们考的是 **provisioning 层**（冻结前 fail-closed / 来源标签），
  **本来就不产生 check 行**，`checks.json` 头部在 R1-1c 那条锁里已被覆盖。⇒ **不算违纪**。

### 6.3 neuter 复跑（我自己独立做，未采信自查表）

| neuter | 摘掉什么 | 红了哪几条 | 连带 |
|---|---|---|---|
| **C** | `_parse_capability_profile` raise → warn+None（`run_config.py:211-216`） | `test_r2_1_flow_typo_capability_profile_fails_closed`（真 `cmd_flow`）+ `test_run_config_invalid_capability_profile_fails_closed`（单元层） | **零**（302 条子集内） |
| **D** | `_resolve_run_profiles` 三态 → 硬编码 `"structured_config"`（`run_stage.py:1636-1641`） | `test_r2_2_cli_only_run_source_is_cli` · `test_r2_2_mixed_decl_source_is_mixed` · `test_R1_2_absent_run_profile_still_cli_authoritative` · `test_r2_1_absent_capability_profile_still_cli_authoritative` | **零** |
| **G** | `_build_record` 的 `capability_profile_not_declared` 守卫 | **零红（302 passed）** | — ⇒ **F-5** |

**⇒ C / D 与轻门逐条吻合，真绑、双层覆盖、零假锁。**

### 6.4 三态语义边界：**没有洞**

`run_stage.py:1634-1641` 是**对称**判据（`run_from_cfg` / `cap_from_cfg` 两个布尔的对称组合），四种组合穷尽：

| cfg.run_profile | cfg.capability_profile | source | 有锁？ |
|---|---|---|---|
| 声明 | 声明 | `structured_config` | ✅ lock B |
| 未声明 | 未声明 | `cli` | ✅ lock A |
| 声明 | 未声明 | `mixed` | ✅ lock C（+ `test_r2_1_absent_capability…`） |
| 未声明 | 声明 | `mixed` | ⬜ 无锁 —— **但与上一行走的是同一个 `elif run_from_cfg or cap_from_cfg` 分支**，结构上不可能分叉 ⇒ **N-1（NIT）** |

**并核实了 r2-2 声称的二阶后果**：`resolve_frozen_run_policy:315-325` 的漂移复核确实**只对 `decl_* is not None` 的字段做**
⇒ `cli` run 无声明故 N/A、`mixed` run 只复核声明侧。**施工方「drift 逻辑本就正确、source 只是让适用面机器可见」的判断成立，我独立核实一致。**
⚠️ 附带如实登记：`source` **目前没有任何判定消费者**（只流向 `checks.json` 头部 `run_policy_source`、
`GeometryApproval`、`isolation` 的溯源字段）。**这是符合裁定的**（裁定 §1.3.3 明令不许加「断言未被消费的值」式的锁），
但请 orchestrator 注意：它与本项目反复撞见的「产出了信号、没人读」形状**外观相同、性质不同**——
这里的正确性是由 drift 逻辑独立保证的，`source` 只是审计标签，**不要在未来被误当成守卫**。

---

## 7. Q-7：边界合规 —— **逐条通过**

| 项 | 结论 | 证据 |
|---|---|---|
| 未 push | ✅ | `git log --oneline origin/6.15_ValidationArchM0toM4..HEAD` = **7** 条未推 |
| `case_tests/test_baseline/gt/**` 零字节 | ✅ | `git diff --name-only 48e41b6..26a14cb -- 'case_tests/test_baseline/gt/**' '**/testdata_prompt.json'` ⇒ **0 命中** |
| sm24 `testdata_prompt.json` 零字节 | ✅ | 同上 |
| 未读 GT | ✅ | 全 diff 的 `+` 行 `grep -inE "load_gt\|test_baseline/gt\|gt\.json"` ⇒ **零命中** |
| 未原地改历史 manifest / attempt | ✅ | 改动共 9 个文件，**无任何 `case_tests/**` 路径**（见下） |
| 未做批 C / D / R1.5 | ✅ | 批 C 半截仍在 `git stash` ⇒ `stash@{0}: On 6.15_ValidationArchM0toM4: batchC-wip-render-pixel-budget`（未取用） |
| 未动 `AI_agent/` 下其他管理文档 | ✅ | `AI_agent/**` 命中**唯一一个**：施工方自己的执行日志 |
| 执行日志未覆盖 §7 | ✅ | `git diff --numstat` ⇒ **309 添加 / 0 删除**（严格 append-only，r0/r1/§7 逐字未动） |

**改动全集（9 文件）**：`scripts/tool_scripts/{record_baseline,run_stage}.py` ·
`src/agent/execution/{run_config,run_policy_freeze,run_provision}.py` ·
`tests/{test_orchestrate_baseline,test_run_config,test_run_stage_flow}.py` ·
`AI_agent/logs/reviews/execution/2026-08-03_reading_ruler_r1_batchB_glm.md`。**无一越界。**

---

## 8. Q-8：不变量 #6 —— 判据**不会被推翻**，但**措辞需要改**（只给判断，不出设计）

**判据原文**：「只有在 `run_config.yaml` 里被声明的东西才有外部信任根，才配被冻结成档位政策并参与防漂移。」

**结论：这条判据的*形状*是可扩展的，非方形 / 退台 / 挑空 / 中庭不会推翻它；但它的*措辞*已经与仓库现状不符，且底下有一处窄接缝。**

1. **形状可扩展 ✅**。它约束的是**政策旋钮的信任根**，不是几何。复杂体量增加的是 *case/几何* 声明
   （per-floor footprint / 变高区 / void），**不是 run-policy 旋钮**。将来若真需要新的冻结旋钮
   （例如一个决定内核走哪条策略的 `massing_profile`），这条判据给出的是**生长路径**而非禁令：
   「把它声明进 `run_config.yaml`，它就获得信任根、就可以被冻结」。⇒ **不是烤死的假设。**

2. **措辞已经不准 ⚠️（现在就不准，不用等复杂体量）**。仓库里**已经有第二个外部信任根**：
   `provision_view_manifest` 冻结的是 **case 身份**，其声明根是 `case_data/testdata_prompt.json`（`dimensioned_views` 等），
   不是 `run_config.yaml`；`reading_exam_scope` 亦然。**判据字面把信任根钉死在单一文件名上**，
   写进长期文档会与这两处冲突。**建议改述为「有冻结的、被测者写不了的外部声明根」**，把文件名降为例子。

3. **一处窄接缝，值得现在登记 ⚠️**：`run_policy_freeze.py:60-64`
   `def _run_policy_hash(capability_profile: str, run_profile: str)` —— **恰好两个位置参数**，
   `RunPolicyRecord` 也是两个扁平字段。**加第三个冻结维度会改变所有既有 run 的 `policy_hash`**
   ⇒ 所有历史冻结件当场失效（`_canonical_and_hash_consistent` 会 raise）。
   好消息是 `RUN_POLICY_SCHEMA_VERSION = "1"` 已在位、`legacy_defaulted` 通道也在
   ⇒ **有版本化迁移路，是迁移成本不是架构死路**。按不变量 #6 的口径，这属于「接缝在、别把它焊死」——
   **建议：以后新增冻结维度时走 schema_version 升版，⛔ 不要往 `_run_policy_hash` 里加位置参数。**

**⇒ Q-8 判定：判据成立、可长到复杂体量；两条措辞/接缝提醒交 orchestrator，不阻断本批。**

---

## 9. 逐锁 neuter 台账（**全部由我在 `/tmp` 克隆内独立复跑**，未采信任何自查表）

**方法**：`git clone --local --no-hardlinks` ⇒ 每次只改一处 ⇒ 跑受影响子集 ⇒ `git checkout -- . && git clean -fd` 复原
（每轮开头都先复原，故各轮互不污染）。子集 = `test_orchestrate_baseline` + `test_run_stage_flow` + `test_provenance_baseline`
+ `test_reading_ruler_r1_batchB`（94 条），C/G 两轮扩到 + `test_run_config` + `test_isolation`（302 条）。

| # | 摘掉哪一处实现（文件:行） | 红了哪几条 | 连带 | 真实 CLI 入口？ | 判定 |
|---|---|---|---|---|---|
| **A1** | `run_policy_freeze.py:370-377` → `return RunPolicy()` 全默认 | `test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback` · `test_R1_5_approve_geometry_uses_frozen_policy_check_headers` · `test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers`（**3 红**） | 零 | geometry 两条走 `cmd_flow`；baseline 那条走真 `record_baseline` | ✅ 三锁在「全默认」这个粗粒度下真绑 |
| **A3** | 同上，**只丢调用方旋钮**、保留冻结档位 | `test_R1_5_record_baseline_uses_frozen_policy_not_cli_fallback`（**1 红**） | 零 | 同上 | ✅ 调用方旋钮维度有锁（**且只有这一条**） |
| **E** | `record_baseline.py:512` → `RunPolicy(require_ep=require_ep)`（**只丢冻结档位**） | **零红（全仓 2095 条）** | — | — | ⛔ **F-1（MAJOR）** |
| **B** | `run_policy_freeze.py:376` → `require_ep=require_ep` 改回读 `record.context` | `test_R1_5_record_baseline_context_tamper_does_not_change_blocking`（1 红） | 零 | 真 `record_baseline` | ✅ 新篡改面锁真绑 |
| **C** | `run_config.py:211-216` `_parse_capability_profile` raise → warn+None | `test_r2_1_flow_typo_capability_profile_fails_closed` · `test_run_config_invalid_capability_profile_fails_closed`（2 红） | 零（302 条内） | ✅ 前者走真 `cmd_flow` | ✅ **CLI + 单元双层真绑** |
| **D** | `run_stage.py:1636-1641` source 三态 → 硬编码 `structured_config` | `test_r2_2_cli_only_run_source_is_cli` · `test_r2_2_mixed_decl_source_is_mixed` · `test_R1_2_absent_run_profile_still_cli_authoritative` · `test_r2_1_absent_capability_profile_still_cli_authoritative`（4 红） | 零 | ✅ 四条全走 `cmd_flow` | ✅ 真绑 |
| **F** | `run_stage.py:226-227` `_draw_reading` 冻结档读取 → `rectangular`/`exploratory` | `test_R1_1_flow_regression_freezes_to_reading_checks_header`（1 红） | 零 | ✅ 真 `cmd_flow` + 真 `_draw_reading` | ✅ **r2-3 删除后承重的那条线锁住了** |
| **G** | `run_policy_freeze.py:168` `capability_profile_not_declared` 守卫短路 | **零红（302 passed）** | — | — | ⛔ **F-5（MINOR，施工方已披露）** |
| **Q2** | `run_stage.py:1695-1696` `_make_policy` 档位硬写成最松档 | `test_R1_1_flow_config_run_profile_overrides_cli_default` + `test_{flow,cmd_run}_config_capability_profile_overrides_only_when_present`（各 2 参数化，**共 5 红**） | 零 | ✅ 全走 `cmd_flow`/`cmd_run` | ✅ **证伪失败 ⇒ r2-3 删除安全** |

**⇒ 7 处真绑（含 1 处双层）· 2 处零锁（F-1 / F-5）· 全程零连带 · 每轮复原后子集全绿。**

---

## 10. 清单外自主发现

- **N-1（NIT · 前置存在，非本批引入）**：`cmd_judge` 对两类「输入不可信」的处置**不一致** ——
  view-manifest 漂移是 `print("✗ … INVARIANT fail")` + `return 2`（`run_stage.py:2035-2039`），
  run-policy 漂移/损坏是**未捕获 `ValueError` traceback**。同一条命令、同一类风险、两种出口。
  **实跑证明该不一致在 `48e41b6` 上同样存在** ⇒ 不计入本批账，登记为跟进债。
- **N-2（观察，非 finding）**：`source` 字段目前零判定消费者（§6.4 末）。**符合裁定**，但形状与本项目反复栽的
  「产出了信号没人读」相同，**建议在 D-4 旁边一并登记**：将来若有人想用 `source` 做判定，
  必须同时补锁 —— 否则它会变成第三类假锁（「标签看起来像守卫」）。
- **N-3（正面数据点，值得记）**：`approve_geometry` 与 `record_baseline` 是**同一批、同一个人写的两个调用点**，
  一个把「溯源来源」与「判定档位」拆开取对了、一个全取了 `frozen` 取错了。
  ⇒ **F-1 不是能力问题，是「同一模式的两处实现没有互相对齐」**；
  这类缺陷用「同族普查」抓得到、用「单点 neuter」抓不到 —— 与 r2 派工单 §2.4 新增的那条纪律同源。

---

## 11. 我证伪失败的尝试（反向坐实，逐条登记）

| # | 我试图证明 | 做法 | 结果 |
|---|---|---|---|
| **1** | r2-3 删除后存在一条失守且无锁的路径（Q-2 明确要求我找） | ① 硬写 `_make_policy` 档位为最松档；② 逐条推演 resume / 改 config / 删 config / 绕过 provisioning 四条路 | **失败** —— ① 恰好红 5 条；②③④ 全被 `provision_run_policy` 的 `policy_hash` 门 fail-closed ⇒ **删除安全** |
| **2** | r2-3 的 `cmd_judge` 内联引入了新的失败面（漂移/损坏时崩） | 三个真实入口探针，先在 `26a14cb` 跑出 2 个 raise，再**搬到 `48e41b6` 重跑** | **失败** —— 老版本**逐条同样 raise**（`_policy_with_frozen_tier` 本就调 `resolve_frozen_run_policy`）⇒ **行为等价，零新问题** |
| **3** | r2-4 只是把篡改面搬了个地方 | 四格矩阵实跑真 `record_baseline`，比对 `blocking` **整串** JSON；并验证篡改件确实仍能通过完整性校验 | **失败** —— 两种调用方取值下**整串逐字相等**，且调用方旋钮被证明是承重的 ⇒ **篡改面真消失** |
| **4** | `source` 三态在「只声明 capability」这一格上有语义洞 | 读 `_resolve_run_profiles:1634-1641` 判据结构 + 核 drift 适用面 | **失败** —— 对称布尔判据，四格穷尽走两个分支，第四格与第三格**同分支不可能分叉** ⇒ 只剩「无独立锁」的 NIT |
| **5** | 同族缺陷已扩散到 R1-1 / L10-L12 / isolation 等别的子系统 | 全仓 45 处 `Neuter` docstring + 24 处 tier/source 断言逐条溯源，对可疑点实跑 neuter F | **失败** —— R1-1c 自称与实际一致；`approve_geometry` 取值正确；L10/L11 断言 disposition 计数是强锁 ⇒ **同族被限制在 r2-4 改写的那三条锁附近，未扩散** |

**这五条失败的价值不低于那 6 条 finding**：它们把 r2-3 的删除安全性、r2-4 的篡改面消除、r2-2 的三态完整性
**从「施工方声称」变成「独立复算」**。

---

## 12. 独立全量跑测（尾部原文）

**干净工作树、`26a14cb`、`pytest -q -n 4`（⛔ 无 `-n auto`、⛔ 无 `-m` 过滤）**：

```
2095 passed, 10 xfailed, 171 warnings in 404.04s (0:06:44)
```

**⇒ 与 orchestrator 轻门（`-n 6`，2095 / 10）和施工方自报逐数字一致。零红、零回归。**

---

## 13. 出口清单（给 orchestrator）

| # | 级别 | 出口 | 建议归属 |
|---|---|---|---|
| **F-1** | MAJOR | `record_baseline.py:542-543` 的 `frozen.run_profile` / `frozen.capability_profile` 改为 `policy.*`（照抄 `step_orchestrator.py:494-495` 的写法）；`source`/`legacy_defaulted`/`policy_hash` 仍归 `frozen`。改完 neuter E 立即变红。**第二层**（可选、更强）：fixture 加一条只在 `regression` 下 block 的检查，与 `test_L10` 同形。同步改掉 `tests/test_orchestrate_baseline.py:52-58` 那句错的因果解释。 | **与 D-2 一并归 R2 债**（轻门 MINOR-1 = 本条） |
| **F-2** | MINOR | 改 `tests/test_orchestrate_baseline.py:160` 注释（"frozen tier still consumed" ⇒ 实况「冻结记录的档位未被篡改」）。随 F-1 一起改。 | R2 债 |
| **F-3** | MINOR | `tests/test_orchestrate_baseline.py:106-109` 的恒真断言：或删除，或改成能分辨 legacy 的形态。 | R2 债 |
| **F-4** | MINOR | 两条 geometry 锁补回 check-id 行断言 —— 换一条在 `regression` 下才 block 的 check-id（与 F-1 第二层是同一件事）。 | R2 债 |
| **F-5** | MINOR | 给 `capability_profile_not_declared` 补一条 neuter 即红的锁（直接走 `provision_run_policy(..., capability_profile=None)` 即可，已实证可达）。 | R2 债 |
| **N-1** | NIT | `cmd_judge` 的 run-policy 漂移/损坏出口与 view-manifest 出口对齐（`print` + `return 2`）。**前置存在，不计本批。** | 跟进债 |
| **N-1'** | NIT | `source` 第四格（只声明 capability）补一条对称锁。 | 跟进债 |
| **Q-8** | 提醒 | ① 判据措辞改为「有冻结的外部声明根」，别钉死单一文件名；② 将来新增冻结维度走 `schema_version` 升版，⛔ 不往 `_run_policy_hash` 加位置参数。 | 写进长期文档时处理 |

**⇒ 无 BLOCKER，批 B 可收口。**
