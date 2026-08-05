# F-2c · 施工席边界上报：F-2c-2「复用 identify_reading_contract」撞 B5 A6 judge-blind 硬边界

- **日期**：2026-08-05
- **施工席**：GLM-5.2
- **派工单**：`AI_agent/logs/reviews/request/2026-08-05_f2c_ruling_and_dispatch.md`
- **状态**：⛔ **F-2c 停下，等 orchestrator 裁定**（不提交）。F-2c-1 与锁已完成且通过；F-2c-2 逻辑完成但被硬边界挡住。

---

## 0. 一句话

F-2c-1（merge 写扁平镜像）+ 三把锁 + 四格 neuter **全部完成且真绑**（neuter 还顺手抓出并修好了一把假锁）。
但 F-2c-2「校验器复用 `identify_reading_contract`」与 **B5 A6「window_sources 必须 judge-blind」硬边界**直接冲突——
全仓跑测**恰好红 2 条**，且都是这条边界的守卫测试。按派工单「有异议停下上报」，停下等裁定。

---

## 1. 已完成且验证通过的部分（F-2c-1 + 锁）

### F-2c-1 · merge 写扁平镜像 ✅
`src/agent/execution/isolation.py` `merge_isolated_output` 在 `do_accept` 为真时，把每个 accepted 视图
另写一份 `<run>/0_reading/<view_id>.json`（内容 = 该视图对象本身，从同一份已 gate① 校验的 `views`
payload 派生，⛔ 不二次解析源文件）。只在 accept 时写，避免后续 blocking draw 覆盖 accepted 镜像。
`view_id` 即 `expected_output_id`（标准语料 = `1f_view`/`South_view`…，identity 变换 = 文件 stem），
故镜像文件名既匹配下游 `*_view.json` glob，stem 又等于信封键——隔离路径与扁平路径在 stage 根**完全一致**。

### F-2c-2 · 校验器逻辑 ✅（但见 §2 的边界冲突）
`verify_reading_stage_root_against_accepted_attempt` 改为：重建 `current` 后，**用 accepted 产物自己的
契约决定要不要套信封**（`identify_reading_contract(accepted_payload).contract_id == READING_PRODUCT_CONTRACT`
⇒ 套 `{"views": current}`），再比 `canonical_sha256`（复用 window_sources.py:44 既有 canonical 哈希）。
扁平 run（`unrecognized` 契约）不套 ⇒ 逐字节行为不变；隔离 run 套信封后与信封 accepted **精确相等**。

### 三把锁（`tests/test_e2e_break_r2_locks.py`）✅ 全绿
1. **F-2c-1 端到端**：隔离 merge 后镜像落盘 + `verify` 通过（隔离路径打通 correction 源校验那堵墙）。
2. **F-2c-2 防掉包（两格）**：clean 通过；改 `1f_view` 镜像里一个真实墙端点坐标 ⇒ 必拒（`accepted_attempt_mismatch`）。
   ⇒ 加镜像不能让这道门变恒真。
3. **扁平路径回归**：用真实扁平 `StageRunner.record` 归档 + `manifest.save`，断言扁平 output.json 仍 FLAT（无信封）、
   逐字节等于扁平 writer 产物、`verify` 通过（不套信封）。

### 四格 neuter（每格在 /tmp 备份真版后改、跑、还原）✅ 全 discriminating
| neuter | f2c1 | f2c2 | f2c3 | 证明 |
|---|---|---|---|---|
| 摘镜像写 | 🔴 | 🔴 | 🟢 | F-2c-1 真绑 |
| 比较恒真 | 🟢 | 🔴 | 🟢 | 防掉包锁真绑 |
| 永远套信封 | 🟢 | 🟢 | 🔴 | wrap 判据·扁平方向有分辨力 |
| 永不套信封 | 🔴 | 🔴 | 🟢 | wrap 判据·隔离方向有分辨力 |

**⭐ neuter 抓到一把假锁（已修）**：初版 Lock 3（扁平回归）用 `StageRunner.record` 后**忘了 `manifest.save(run_dir)`**，
导致 `manifest.accepted("0_reading")` 为 None ⇒ `verify` 在 `if accepted is None: return` 提前退出、**根本没走到比较**。
于是 N3（永远套信封）没让 f2c3 变红——典型的「锁绿着缺陷还在」。四格实验当场暴露，补 `manifest.save` + 一条
`accepted is not None` 守卫后修好。（对照 [[lock-must-exercise-real-entry-point]]：锁必须落在真实入口，不能落在"不是 None"上。）

### 全仓三数字（F-2c 当前态，未提交）
**2178 passed / 10 xfailed / 2 failed**（基线 0256060 = 2177/10/0；+3 新锁，−2 = 下方 §2 两条边界守卫）。
**仅这 2 条红，且都因 §2 的边界冲突**；其余零回归。

---

## 2. ⛔ 冲突：F-2c-2 复用 `identify_reading_contract` 撞 B5 A6 硬边界

### 事实
- 派工单 §2 明令：校验器「**复用 `identify_reading_contract`**，⛔ 不许新写一个形状判定」。
- `identify_reading_contract` 定义在 `src/agent/judge/reading_typed_adapter.py`（judge 模块）。
- **B5 A6 硬边界（2 条守卫 + 模块 docstring）禁止 window_sources.py 引用 judge 代码**：
  - `tests/test_c2_b5_source_routing.py:213 test_b5_a6_production_source_is_judge_blind`：
    `assert "src.agent.judge" not in <window_sources.py 源码>` —— 纯字符串扫描，连局部 import / 字符串都拦。
  - `tests/test_c2_b5_parent_and_verts.py:1162 test_c5_production_correction_and_geometry_sources_import_no_judge`：
    扫 `src/agent/correction` 全树，含 `"src.agent.judge"` 即 offender。
  - `window_sources.py:1-5` docstring：「It imports no judge code: score bindings are an oracle for tests only.」

我在 `verify_...` 里用了**局部 import**（匹配该函数已有的 `from src.agent.execution.manifest import ...` 局部 import 模式），
逻辑上能跑、三把锁全绿，但**字符串 `"src.agent.judge"` 出现在了 window_sources.py** ⇒ 两条边界守卫必红。

### 为什么这是真冲突（不是我能自行消解的实现细节）
- 不能"换种 import 写法绕过"：B5 A6 是字符串扫描，任何形式引用 `src.agent.judge` 都触发；用 importlib + 变量拼路径是**绕锁不是守约**，不做。
- 不能"在 window_sources 里手写一个形状判定"：派工单明令 ⛔ 不许新写形状判定。
- **唯一能同时满足「复用」与「judge-blind」的解 = 把 `identify_reading_contract` 从 judge 模块挪到非 judge 共享位置**，
  让 window_sources 从新位置 import、judge 侧改 re-export。但这**触碰 judge 模块结构**，属范围决策，派工单的
  「⛔ 不碰识图侧 / gt / 判卷语义 / typed v3」让我不敢擅自挪 judge 代码 ⇒ 停下等裁定。

### 值得注意：`identify_reading_contract` 本身不是"判卷语义"
它是**纯形状探测器**（`"views" in raw` + 值类型判定，零 score/GT/test-oracle 逻辑），已经被 `scripts/tool_scripts/run_stage.py`
生产路径多处调用。B5 A6 边界的**本意**是挡住 judge **score/oracle** 代码泄进生产（"score bindings are an oracle for tests only"）；
`identify_reading_contract` 不携带这类信息。所以这条边界对它**过宽**——但边界的实现是钝器文本扫描，照抓。

---

## 3. 请 orchestrator 裁定（三选一，含推荐）

- **【推荐】选项 A · 把探测器挪到非 judge 共享模块**：新建 `src/agent/execution/reading_contract.py`
  （execution 非 correction/非 judge，window_sources 本就 import execution），把 `identify_reading_contract` +
  `ReadingContractDecision` + 契约常量搬过去；`reading_typed_adapter.py` 改为 `from ...execution.reading_contract import ...`
  re-export（judge 侧零语义变化）；window_sources 从 execution import。
  ⇒ **复用同一个探测器（非新写）+ window_sources 重新 judge-blind + 不碰 reading worker / gt / 判卷语义 / typed v3**。
  代价：动 judge 模块一处（def→import）。
- **选项 B · orchestrator 覆写「⛔ 不许新写形状判定」**：在 window_sources 内写一个**极薄的**形状判定（`isinstance(views:=raw.get("views"), dict)` 级别），
  显式标注"与 identify_reading_contract 同语义、因 B5 A6 边界就地复刻"。保持边界、零 judge 触碰，但技术上是"第二处形状判定"。
- **选项 C · 收窄 B5 A6 守卫**：把"src.agent.judge 字符串扫描"改成 AST 级"禁止 import judge 的 score/oracle 子树"，
  放行纯形状探测器。**不推荐**——项目多次栽在"放宽守卫"上，且改动面更大。

我的推荐是 **A**：它最忠实地同时满足派工单「复用」与 B5 A6「judge-blind」，且改动可控、语义零变化。
但 A 触碰 judge 模块布局，所以交 orchestrator 拍。

---

## 4. 当前工作树状态（未 commit、未 push）

- `src/agent/execution/isolation.py`：F-2c-1 镜像写入 ✅（无边界问题）
- `src/agent/correction/window_sources.py`：F-2c-2 校验器 + **触发边界的局部 import** ⛔
- `scripts/tool_scripts/run_stage.py`：`_extract_reading_views` 注释随函数行为同步更新 ✅
- `tests/test_e2e_break_r2_locks.py`：imports + 三把锁 ✅
- /tmp 备份：`/tmp/f2c_isolation.real.py`、`/tmp/f2c_ws.real.py`（neuter 用）

**等裁定后**：按选定选项改掉 window_sources 的 import，重跑全仓确认 2 条边界守卫转绿（预期 2180/10/0），
再写正式简报 + 单独提交（`08.05_<label>`，⛔ 不 push，只 add 自己改的文件）。然后才做第二单 r4。

## 5. r4 不受影响
第二单（恢复 reading review 环）与 F-2c 完全独立、无边界冲突；但派工单要求"按顺序做"，F-2c 卡在裁定，
故 r4 暂不动，等 F-2c 落定再开工（除非 orchestrator 指示先做 r4）。
