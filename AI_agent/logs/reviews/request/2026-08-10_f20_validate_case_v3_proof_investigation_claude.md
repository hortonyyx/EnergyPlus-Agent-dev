# 派工单 · F-20 **调查**：`validate_case` 重建几何时不传窗宿主凭证 ⇒ v3 路径彻底堵死

- **日期**：2026-08-10 · **席位**：Claude 侧 **Sonnet**（执行档）· 通道 = Agent 子代理
- **性质**：⛔ **只调查 + 出选项对比，不施工、不改生产码**（用户已拍板：先拿利弊再拍修法）
- **基点**：分支 `6.15_ValidationArchM0toM4`，**HEAD = `74b0335`**，工作树**无未提交的代码改动**
  （有 65 个未跟踪项 = `.gitignore` 08-09 改规则后重新可见的历史痕迹，⛔ **不要动它们、不要清理、不要 `git add`**）
- **全仓基线**：`python -m pytest -p no:cacheprovider -q -n 8` ⇒ **2345 passed / 10 xfailed / 0 failed**
  （⛔ 不要用 `-n auto`：16 worker 实测会在 ~98% 处静默 OOM 中断）
- **现场产物**（真实、在盘上、零 LLM 成本可反复跑）：
  `case_tests/e2e_tests/sm21_anchor/run_2026-08-09_f18_e2e_verify/`
- **成本**：本单**零 LLM 调用、零付费 API**。所有证据都能靠读盘 + 只读脚本拿到。

---

## ⛔ 0. 第一步：防假调查自检（动手前做，答案写进执行日志）

> 缘起 = **派工方（orchestrator）错误率 12/12** —— 每一次施工席「停下上报」，事后都证明是派工单的题错了。
> 本单尤其危险，因为它要你评价一段**看起来多余**的设计，而项目刚在 08-09 因为同一个动作栽过
> （F-9 设计稿 BLOCKER-3：把一个 advisory 标记读成「当初没人敢用」，
> 而理由**逐字写在引入它的那次提交说明里**，orchestrator 只读了当前源码、没读提交说明）。

请先回答这三问，**答不上来就停下上报，不要开工**：

1. 我准备用来支撑结论的证据，是**读盘/跑脚本量出来的**，还是**从代码形状推出来的**？
   （本单每一条结论都必须能指到「哪个文件的哪一行 / 哪条命令的哪一行输出」。）
2. 我要评价的那段「只读 stage 根」的设计，**它的理由我是从当前源码猜的，还是从引入它的那次提交说明读到的**？
   （⛔ 首选证据 = `git log -S` + `git blame` 找到引入提交，**读它的 message**。这是硬要求，见 Q1。）
3. 我说「某某测试没覆盖 v3」时，**我是怎么数的**？（给出可复跑的命令，⛔ 不许只凭 grep 文件名形状。）

---

## 1. 缺陷事实（orchestrator 已实测坐实，⛔ 不是推断，不要重做）

F-19 修完后续跑 flow，`2_modelling` 与 `3_split_pairing` 的 gate① **都过了**（零 block 零 flag），
但停在 `awaiting_geometry_approval`，报：

```
✗ geometry auto-approval failed: no consistent checkpoint
```

**根因链**（每一环都已实测）：

| 环 | 位置 | 事实 |
|---|---|---|
| ① | [`validation_run.py:218`](../../../src/agent/execution/validation_run.py#L218) | `bg = build_geometry(geom, capability_profile=profile)` —— **没有 `window_host_proof`** |
| ② | [`build.py:207-208`](../../../src/agent/geometry/build.py#L207) | `is_b5 and window_host_proof is None` ⇒ `raise ValueError("v3 build requires VerifiedWindowHostProof, including zero-window output")` |
| ③ | `validation_run.py:253-256` | 该异常被 `except Exception` 捕获 ⇒ `2_modelling` 记 error report |
| ④ | — | ⇒ `geometry_digest = None` ⇒ `approve_geometry()` 返回 None ⇒ **门无法签发检查点** |

**⛔ 比表面严重的一点**：`--geometry auto` 与**人工** `approve-geometry`
（`run_stage.py:2458-2460`）**走同一个 `approve_geometry()`**
⇒ 不是「自动批不了、人来批即可」，而是 **人也批不了 ⇒ v3 路径彻底堵死**。

**出生年月（git 实证）= 又一个 F-10 同型签名/契约漂移**：

| 件 | 提交 | 日期 |
|---|---|---|
| `validate_case` 那行调用的写法 | `802822f` | **07-06** |
| `build_geometry` **开始要求** proof | `2885a84`（与造出 F-19 那道门是同一提交）| **07-18** |

⇒ 被调方 07-18 加了必需参数，调用方 07-06 的写法没跟，**潜伏 3 周多**。

---

## 2. orchestrator 已核实的事实（⛔ 不要重做，但**允许并欢迎证伪**）

> 下面四条是我 2026-08-10 亲手量的。**如果你量出不一致，以你的实测为准并大声上报** ——
> 08-09 的教训正是「作者对自己推理的系统性盲区」，我也在其中。

**F-20-A｜`validate_case` 从不读 `run_manifest.json`。**
`grep -n "manifest" src/agent/execution/validation_run.py` ⇒ 只有 `RunManifest` 的 import
和 `_build_manifest(res).save(run_dir, filename="validation_manifest.json")`。
`:324-326` 有一条明确注释：这是 *validation SUMMARY* —— **NOT the M0 audit manifest
(which is backed by append-only attempt dirs)**，且刻意换了文件名以免冒充或覆盖 `run_manifest.json`。
⇒ **「只读 stage 根」是有意设计，不是疏忽。**

**F-20-B｜项目里已经有一个成熟的、能签发这份凭证的加载器。**
`load_verified_accepted_correction(*, run_dir, manifest)`（[`output_coordinates.py:370`](../../../src/agent/output_coordinates.py#L370)）
读账本的 accepted attempt、逐件核对 `artifact_hashes`、把 resolver inputs 对着**原始 view manifest 与原始 reading 字节**
重新验一遍，最后在 `:495` 调 `_verify_b5_bundle(...)` **签发 `window_host_proof`**。
它已有 6 处生产调用点，其中 **`src/agent/execution/correction_audit.py:90` 就在 execution 层**。
⇒ 「让 `validate_case` 去读账本」**不是新造耦合**，那条路已经铺好且在用。

**F-20-C｜stage 根本来就是 accepted attempt 的字节镜像（至少在这份真实产物上）。**

```
sha256  5ffb636810d90d3f7855c988934f7acf7e86a9aef1a6a242cbe31e76e1b8f3fe
        1_correction/correction_geometry_snapped.json
sha256  5ffb636810d90d3f7855c988934f7acf7e86a9aef1a6a242cbe31e76e1b8f3fe
        1_correction/attempts/001/output.json
```

两者**逐字节相同**（各 65513 字节）。
⇒ 「把凭证镜像一份到 stage 根」**也不是新增第一份副本** —— 镜像这件事已经在发生了。

**F-20-D｜这份产物的账本记录确实会走 B5 分支。**
`_run/run_manifest.json` 的 `1_correction` 记录 = `accepted_attempt=1`、
`artifact_contract="correction_b5_v1"` ⇒ 落在 `output_coordinates.py:431` 的 `b5_contracts` 集合内
⇒ 加载器会走 `:462` 那条签发 proof 的分支。

> **⇒ 因此：orchestrator 上轮在 plan.md 里把岔口写成
> 「① 耦合 manifest（新耦合）vs ② 多一处副本（新副本）」，两边的描述都不准。**
> 本单的头号任务就是**把这个岔口重新描准**，别照抄我上轮那句话。

---

## 3. 必答问题（逐条给结论 + 证据行号/命令输出）

### Q1（最高优先，B3 纪律）｜「只读 stage 根」在为哪份契约服务？

用 `git log -S` / `git blame` 找出**引入这条设计的那次提交**，**读它的 commit message 原文并引用**。
要回答：

- 这条设计当初是为了防什么？（我手上只有一句二手转述「never bind an approval to stale / unchecked bytes」——
  **请核实这句话到底出自哪里、是不是原文**。）
- **这东西没了，谁会因为「以为它还在」而算错？**（消费方常在产物外部。）
- 它今天还在防到东西吗？（对照 08-09 `.gitignore` 那次的问法：**「这条规则本来要挡的东西今天还在吗」** ——
  那次实测发现规则挡的目标一个都不存在了。本条可能同样、也可能相反，**要量**。）

⛔ **禁止**只凭当前源码里的注释就断言「这只是历史包袱」。

### Q2｜v3 重建到底缺哪些件，每件在盘上的哪里？

列一张表：件名 / 当前落盘路径 / 是否在 stage 根 / 是否在 attempt 目录 / 是否在 `_run/`。
至少覆盖 `output.json`、`feature_states.json`、`window_resolver_inputs.json`、`window_hosts.json`、
`view_manifest.json`、`0_reading/*.json`。

### Q3｜两条改法的**防篡改强度**到底差多少？（岔口重描）

在 F-20-B/C 已证实的前提下，重新把岔口描准，并对每条改法回答：

- 攻击面：一个能写 run 目录的人，在这条改法下能让门签发一份**不该签**的检查点吗？给出具体路径或证明不能。
  （提示：proof 是自校验的 —— `_reverify_window_host_proof` 会重算 claims 并比哈希，
  篡改单个件会被抓；**但请自己验证这个说法，别信我**。）
- 会不会引入**轴 B 风险**（同一事实两处声明、各自漂）？
- 对 **legacy 产物**的影响：`build.py:209` 规定 legacy geom **不得**收到 proof
  ⇒ 改法必须按 `schema_version` 分流，否则会把现有 golden anchor 打红。**请实测 blast radius。**

### Q4｜改法之外还有没有第三条路？

例如：让 `validate_case` 在**拿不到凭证**时给出**结构化的、可诊断的 NOT_APPLICABLE/BLOCK**，
而不是现在这样吞进 `except Exception` 变成一句 `kernel build failed: ...`。
（注意这**不解决**堵死问题，但可能是任何改法都该顺带做的事 —— 现在的失败信息把根因藏住了。）

### Q5｜为什么 2345 绿一条没抓到？给出可复跑的数法。

已知线索：`tests/test_validation_run_baseline.py` / `test_run_stage_flow.py` / `test_check_parity.py`
三个跑 `validate_case` 的文件里 **v3 相关命中数全部为 0**。
**请给出你数这件事的确切命令**，并回答：**最便宜的正向锁长什么样**？
（⚠️ 呼应 08-10 刚记的一条：**一道门若只有断言 fail 的测试、没有断言 pass 的测试，它恒红结构上不可观测**。
本条反过来 —— 这里是**根本没有 v3 夹具**，所以整条路径不可观测。）

### Q6｜真实产物能否当夹具？

`run_2026-08-09_f18_e2e_verify` 是**第一份真正走到几何确认门的 v3 产物**。
评估：把它（或其最小裁剪）做成回归夹具的可行性与体积代价。
⚠️ 注意 08-09 登记的坑：**落盘 `correction_geometry.json` 不能直接重放**
（带派生 `floor` 会被新门拒；当前姿势 = 解析前逐窗 `pop("floor")`，15/15 都要剥）。

---

## 4. ⛔ 边界（硬约束）

1. **不改任何生产码。** 不动 `src/`、`scripts/`、`tests/`。
2. **所有探针只在 `/tmp` 做**，⛔ 不许在工作树里造临时文件。
3. **不许 `git add` / `commit`**（唯一例外：调查报告本身落 `AI_agent/logs/experiments/2026-08-10_f20_validate_case_v3_proof/`，
   由 orchestrator 提交）。
4. **不要碰那 65 个未跟踪项。**
5. **不许读 gt**（`case_tests/test_baseline/gt/`）—— 本单与判卷无关，读了就污染。
6. 跑全仓测试用 `-n 8`；**输出直接重定向到文件，退出码单独落一个只属于该命令的文件，
   ⛔ 中间不接任何下游管道**（`pytest | tee log | head` 会因 `head` 关 stdin ⇒ `tee` 收 SIGPIPE
   ⇒ 连带打断 pytest，而你看到的「退出码 0」其实是 `head` 的）。

---

## 5. 交付物

落 `AI_agent/logs/experiments/2026-08-10_f20_validate_case_v3_proof/README.md`：

1. **§0 三问的答案**（原样写下，包括你答不上来的）。
2. **Q1–Q6 逐条结论 + 证据**（文件行号 / 命令与其输出片段 / 提交号与 message 原文）。
3. **岔口重描**：一张对比表（改法 / 防篡改强度 / 轴 B 风险 / legacy blast radius / 实现成本 / 需要几把锁）。
4. **你的推荐 + 理由**，以及**你认为需要用户拍板的点**（用大白话写，用户没有代码上下文）。
5. **可复跑脚本**随报告入库（只读、零 LLM）。
6. **⛔ 明确列出「我没能证实的部分」** —— 宁可留白，不要用推理填。

---

## 6. 合法退出口（⚠️ 请务必使用）

**以下任一情况，请立刻停下并如实上报，不要硬做：**

- 派工单里的某条「已核实事实」你量出来是**错的**（F-20-A/B/C/D 任一条）；
- Q1 找不到引入提交、或提交 message 里根本没写理由 ⇒ **如实说「查不到」**，
  ⛔ 不要用当前源码的注释冒充提交说明；
- 你发现这个岔口根本不是岔口（例如两条改法实质等价，或有第三条明显更好的路）；
- 验收/证据路径与本单某条要求**互相冲突**；
- 撞额度窗中断 ⇒ 停在哪里如实说。
  ⚠️ **纪律**：施工席中断后的自述**不可信**（已两次实证），orchestrator 一律以 `git diff` 复核 ——
  所以**如实说反而对你有利**，不必也不要粉饰。

**派工方（orchestrator）自陈错误率 = 12/12** —— 迄今每一次「停下上报」都证明是我的题错了。
**顶住不照做、如实上报，是本单期望的行为，不是失败。**
