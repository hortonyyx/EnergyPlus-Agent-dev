# 第五轮跨家族复审裁决 —— `BLOCKER-1` 闭合 + 摊 H/I

- 日期：2026-08-14
- 审阅席：GPT 侧 sol（跨家族）
- 工作树：`/workspaces/ep-wt-C`，分支 `wt/0814_C_sol_review`，HEAD / 基点 `ea00e015`
- 总状态：**REVIEW STOPPED · REQUEST CORRECTION REQUIRED**
- 闭合结论：**本轮不得关闭 `BLOCKER-1`。** 即使暂不计请求书承重前提错误，缓存实现身份仍有可复现旁路。

## 1. 停止理由：请求书 §1.3 的承重前提与在库事实冲突

请求书断言：

1. “真实 run 的正向 `trusted=True` 至今没有做”；
2. 三次验收配置 `judge: {mode: off}`，所以“不会走判卷路径”。

这两句不能共同作为本轮裁定前提。仓内 `41f73e7` 已提交的真实 run
`case_tests/e2e_tests/sm21_anchor/run_2026-08-13_post_blocker1_e2e` 给出相反证据：

- 该 run 的 README §5 明写“摊 A 的正向证据首次在真实 run 上拿到”；运行命令虽为
  `--judge off`，但 accepted attempt 的判卷侧车确实存在。
- `_run/run_manifest.json` 的 accepted `1_correction` 是 attempt 002，合同为
  `correction_b5_orientation_v1`，并绑定 `deterministic_core_proof`。
- `1_correction/attempts/002/score_vs_gt.json` 实际为
  `declared=True, trusted=True`，且带
  `proof_bytes_sha256`、`accepted_record_sha256` 与 `scorer_schema="11"`。

因此，`judge: off` 至少不等于“该 flow 不会生成 legacy grading/cache 侧车”；真实 writer →
manifest → proof → scorer 的正向产物已经在盘。现有证据尚未证明的是：该真实 attempt 在同一验收记录中
完成了“首次写 cache 后第二次身份不变命中”的可观察复读。请求书把“复读未留证”扩大成“整条真实正向链
从未出现”，会使第三支被错误裁成全无证据。

按请求书 §0，“承重前提错、会导致错误裁定 ⇒ 停下上报”。故本轮不给出无条件 APPROVE；派工方须先把
§1.3 改成与上述在库事实一致的待证命题，再据修订口径签收真实链。

## 2. 已独立坐实、无需因重派而重复的结论

### 2.1 信任根支：收窄威胁模型在工程上可成立，但治理落字尚未照办完

用户在 `decision_log.md §5.14.1` 明确选择“不防拥有 run 目录写权的主体手动改盘”。在这个限定下，
run-local manifest + writer-issued proof 不再承担“不可伪造的外部根”，只承担“候选产物不能靠自己携带的
stamp 冒充 writer 已重放并逐键比对”的第二处记载。这个限定与现实现状相容，**上一轮仅因缺外部防篡改根
而提出的阻断，在收窄模型内可以撤销**。

但请求书“硬约束均已照办”不实。现役生产文件
`src/agent/correction/deterministic.py` 的 `DeterministicCoreProofV1` docstring 仍写：

- `externally issued proof`；
- `It is signed by StageRunner.record`；
- `the same tamper-evident mechanism`。

`tests/test_f22_blocker1_core_stamp.py` 的现役说明也仍有 `externally issued` / `signed by`。这与 §5.14.1
“代码注释一律不得再作外部根、防篡改或签名等价表述”的硬约束直接冲突。`correction_score.py` 的措辞已改，
但全链没有清净。因此信任根支的**架构争议可关，治理/文档落地尚需一轮机械清理后才算完成**。

收窄威胁模型还有必须明说的工程后果：

1. 任何拥有 run 目录写权的人工、同进程插件、CI 步骤或被攻陷工具，都可同时重写 proof 与 manifest；系统
   不检测这种改盘。
2. 本地磁盘损坏或 writer/manifest 写入 bug 若仍能形成自洽哈希，也不由“trusted”提供安全保证。
3. `trusted` 只能解释为“当前同一信任域的落库方曾签发”，不得被下游当授权、安全边界或对外交付证明。
4. 一旦进入多人协作、CI 产物交付或外部审计，现结论自动失效，必须先改 §5.14.1 并补签名/MAC、目录外
   WORM receipt 或真人签字链之一。

### 2.2 缓存支：proof-loss 反例已修；“scorer implementation identity”仍未成立

`41f73e7` 已把 proof 解析移到 cache lookup 之前，并把当前 proof bytes hash 与 accepted record identity
纳入 predicate。定向锁与我独立执行的 99 条测试证明：proof 不变可 hit；proof 删除/增字节后 resolver
返回 `None`，旧 `trusted=True` 不再复用。**第四轮反例 A 的原形已关闭。**

但 `_scorer_implementation_sha256()` 只哈希三个顶层 code object：

- `_score_attempt_output`；
- `_legacy_score_attempt_output`；
- `score_correction_geometry`。

真正决定 `trusted` 的 `_is_trusted_output_convention` 是被后者按全局名字调用的辅助函数，并未进入摘要。
我在真实 `StageRunner.record` 生成的 accepted B5 fixture 上先写出 `trusted=True` cache，再把该 gate 替换为
恒拒绝实现。结果：

```text
seeded_trusted= True
trust_gate_replaced= True
identity_changed_after_gate_replacement= False
scorer_calls_after_gate_replacement= []
cached_trusted_after_gate_replacement= True
```

这证明现字段只是“被选中的三个函数身份”，不是 scorer/trust-policy implementation identity。实现语义已变，
cache 仍命中。因此缓存支整体**仍开**，`MAJOR-F24` 也仍开。

最小闭合口径：使用可覆盖实际部署 scorer/trust-policy 依赖闭包的代码派生身份，例如部署 build/source-tree
revision，或显式纳入 scorer、`_is_trusted_output_convention`、core projection/trust policy 及其行为依赖的
source/code digest；不能只给当前三函数再起一个完整身份的名字。必须补一条反向锁：只替换 trust gate，
两个 live 常量与其余顶层函数不变，cache 必须 miss 且重算为 `trusted=False`。

### 2.3 真实 run 正向观察支：已有首写证据，复读证据需补，不应重跑整条 flow

请求修订后，最小可接受形态应基于已经在库的真实
`post_blocker1_e2e/1_correction/attempts/002`，或一条当前 HEAD 新建的等价
`correction_b5_orientation_v1` attempt：

1. 核对 accepted manifest 指向该 attempt，output/proof hashes 与盘上 bytes 一致；
2. 通过生产 `_judge_gt_artifacts` 入口首次计算，观察 `declared=True, trusted=True`，记录 scorer 一次调用；
3. 身份不变再调一次，观察 scorer 零调用且 cache 命中；
4. 在隔离副本中删除/篡改 proof，观察 resolver 为 `None`、旧 trusted cache miss、重算
   `trusted=False`；
5. 保留旧无 proof attempt fail closed。

这项不需要 `--record`：它验证的是 writer/proof/judge/cache 接线，不是登记正式成绩。也不必重跑 0–5 或
EnergyPlus；但若派工方坚持用新 run，配置必须允许并记录上述生产评分入口，不能再从 `judge: off` 文本直接
推导“没有判卷侧车”。

由于缓存实现身份仍开，即使补齐真实复读观察，`BLOCKER-1` 本轮也不能关闭。

## 3. 摊 H/I 与 F-27

结论：**CHANGES REQUIRED；不得把当前实现作为“surface 400 已稳定根治”的验收版本。** 可进入隔离的诊断跑，
但在 F-27 未修时，三次 clean run 只能是经验样本，不能证明协议缺陷已关闭。

已成立的部分：

- `react.py` 保留 provider 返回的全部 tool call id，让 `ToolNode` 逐一配平；这比丢弃其余 id 正确。
- `create_surfaces_batch` 的逐项成功/失败、部分成功、最多 4 项、与单条创建的字段等价性均有定向锁；本轮
  这些锁通过。
- 请求书 §1.4 的编号状态已过时：最终 `react.py` 已标为 `F-26`，不记 NIT。

仍阻断验收的两点：

1. **F-27 是根因缝，不是普通债。** `_MAX_BATCH_ITEMS=4` 只在 provider 已经完整生成并由客户端解析出
   tool call 后才执行。已知失败发生在生成期间 `finish_reason='length'`；若调用在生成中被截断，本地工具
   根本没有机会用上限拒绝它。代码上限只能拒绝“完整生成的 5+ 项调用”，不能结构性防止“第 5/6 项生成
   到一半”的幽灵调用。`react.py` 当前只记录 finish reason，未把 `length` 轮判为无效、未阻止其进入历史。
2. **surface 完整性补救分支未经真实触发，也缺 wiring 锁。** 它第二次直接调用 `agent.invoke(...)`，绕过
   `invoke_with_self_repair` 每轮强制执行的 `local_config.validate_references()`；修复后若仍缺面，也只
   `logger.error` 后继续返回不完整 state。外层门以后可能抓住，但该 hotfix 自己既不 fail closed，也没有
   证明补救调用、二次完整性与二次引用校验真正接线。该分支又是施工席越过派工边界自行加入，不能靠纯
   `_expected_surface_names` 解析单测签收。

H/I 最小闭合口径：

- 在 `react.py` 协议层把 `finish_reason == "length"` 的 assistant turn 判为无效，不允许该轮的 tool calls
  执行或进入下一次提交的历史；给完整轮/截断轮双向 wiring 锁。
- 对 surface 补救分支，要么回退这段越界功能；要么经明确授权后让补救仍走共享 self-repair/引用校验，
  第二轮仍缺时结构化失败，并补“首轮零调用 → 补救建齐”与“补救仍不齐 → fail closed”两条 wiring 锁。
- 完成后再按既定三次新 run、单次 flow、100 面/15 窗/14 区、0 Severe、零非法重试、顶点逐位相同验收。

## 4. 实际执行与输出

未重复已给出的全仓 `2603 passed / 10 xfailed / 0 failed` 基线。

### 4.1 定向测试

```text
python -m pytest -q -n 6 \
  tests/test_c2_b5_artifact_trust.py \
  tests/test_f24_scoring_semantics_cache_identity.py \
  tests/test_react_llm_resilience.py \
  tests/test_batch_create_surfaces.py

99 passed in 6.32s
```

### 4.2 缓存实现身份探针

通过不落盘 Python 探针加载 `tests/test_c2_b5_artifact_trust.py::_accepted`，走真实 writer-backed fixture 与
生产 `_judge_gt_artifacts`；输出见 §2.2。第一次装载因未把 `tests/` 加入 `sys.path`，在业务逻辑启动前失败：

```text
ModuleNotFoundError: No module named 'test_c2_b5_parent_and_verts'
```

修正模块搜索路径后探针 rc=0，复现 stale trusted cache。

### 4.3 静态/仓内证据核验

- `git diff --check 41f73e7^ 41f73e7`：rc=0，零输出。
- 查阅 `41f73e7`、`f2e6c47`、`bac31d4` 的最终代码、测试、提交说明与相关派工单。
- 机械读取真实 `post_blocker1_e2e` / `accept_B` 的 run config、accepted manifest 与 score sidecar，得到
  §1 所列矛盾。
- 未运行新的真实 provider flow，未运行 EnergyPlus，未触发 surface 完整性补救真实分支。

## 5. 请求书 §4 四项明确答复

1. **`BLOCKER-1` 不能关闭。** 信任根架构争议在收窄模型内可关，但治理措辞未清；proof-loss 缓存反例已修，
   scorer implementation identity 仍可旁路；真实 run 已有正向首写，不是“从未做”，但复读证据需按 §2.3
   补齐。最低闭合口径见 §2.1–§2.3。
2. **收窄模型有工程后果。** 它明确豁免 run-dir 写权主体、同域工具/CI 与自洽磁盘改写，`trusted` 不能作为
   安全或对外交付保证；扩大协作/交付边界前必须补外部根。
3. **摊 H/I = CHANGES REQUIRED。** F-27 未修时只能做隔离诊断跑，不能进入“根治已稳定”的验收闭环；
   完整性补救越界且零真实触发、绕过共享二次引用校验，也不能签收。
4. **实际执行 / 未验证**见 §4；全仓基线没有重复跑。

## 6. 最终裁决

本轮同时存在请求承重前提错误与独立的缓存实现身份旁路。故状态不是 APPROVE，也不能把
`BLOCKER-1` 写成 closed：**REVIEW STOPPED · REQUEST CORRECTION REQUIRED；在修订请求并完成上述最低闭合口径前，
维持 `BLOCKER-1 OPEN`。**
