# 派工单 · 摊 A —— 闭合 F-22 `BLOCKER-1`：把「自报的印章」换成「由落库方签发的 provenance」

- **日期**：2026-08-13
- **席位**：Claude 侧执行档（Sonnet 5）
- **审阅去向**：GPT 侧 sol（跨家族，「谁写谁不批」）
- **裁决书依据**：[2026-08-12_round3_full_body_crossreview_sol.md](../verdict/2026-08-12_round3_full_body_crossreview_sol.md) §3.1
- **基线**：`2557 passed / 10 xfailed / 0 failed`（全仓 `-n auto`；orchestrator 今日独立复跑中，收到即以实测值为准）

---

## 0. ⭐ 停止规矩（分层，必须先读）

上一批连续两轮因为「发现前提错就停」这条无差别硬规矩，把整批主体挡在审阅之外。本单按分层规矩写：

1. **承重前提错**（错了则本任务方向作废、或修法会造成错误行为）⇒ **立即停下上报，不要继续施工。**
2. **外围论据错**（不改变任务方向）⇒ **在交付报告里写明「派工方这句是错的 + 你的实测」，然后继续把主体做完。**

本单 §2 每一条前提都标了「我是怎么验的」。**请把它们当【可能错的前提】读并主动证伪** —— 派工方（orchestrator）在本项目的
历史错误率是 **15/15**，最近两条分别是「穷举身份不合法、漏掉身份合法但过时」和「否定式结构断言未经实测」。

## 1. 要解决的问题（一句话）

昨天给确定性核加的印章，**存在产品自己携带的字段里** ⇒ 它不是「核跑过」的证明，只是「对象声称核跑过」。
sol 两级反例（orchestrator 已独立复现）：

1. 往 F-17 翻转前的**真实产物**手加一行 `"deterministic_core_stamp": {"version": "1"}`
   ⇒ 判卷 `trusted=False → True`，两层 boundary 变 `4/4`（该产物每条外边实际差 0.12 m）。
2. 更狠：伪造一份**内部自洽**的候选（`[0,4]²` 的 producer 重签成 `[0.12,3.88]²`，重物化 Vg、
   重算 feature claims / host claims / candidate identity / evidence）⇒ **真实 `StageRunner.record`
   接受并持久化了这份伪造几何。**

> ⭐ **判别问法（本单的灵魂）：「这个字段，被评判的一方能不能自己写？」
> 能写 ⇒ 最多叫 `declared`，绝不能叫 `trusted`。**

## 2. 承重前提（我的核实方式写在括号里，请证伪）

| # | 前提 | 我怎么验的 |
|---|---|---|
| P1 | 落库方**已经**在重放确定性核：`src/agent/execution/stage_runner.py:308-338` 从 embedded raw/reading 重建 envelope 并调 `apply_deterministic_core`，结果在局部变量 `replayed` 里 | 直接读源码 |
| P2 | 但它**只**拿 `replayed.windows` 去核 audit/host 行（`:361-383`），以及 corrections/conflicts/unsupported 的 audit↔output 一致性（`:339-349`）；**从不比较 footprint / 每层 ring / cells** | 直接读源码 + sol 的伪造候选被接受 |
| P3 | 判卷函数 `score_correction_geometry`（`src/agent/judge/correction_score.py:442-458`）**只收裸 dict / CorrectedGeometry，没有任何 run/manifest 上下文** | 读签名 + 全仓搜调用点 |
| P4 | 它在生产里**只有一条**调用链：`run_stage.py:1639 _score_attempt_output` → `judge/score_service.py:711-728` → `run_stage.py:1449 _legacy_score_attempt_output` → 判卷 | `grep -rn score_correction_geometry src/ scripts/` 仅两处非定义命中 |
| P5 | **账本是拿得到的**：上游 `_grade_attempt_artifacts`（`run_stage.py:1606-1613`）的形参里**有 `attempt_dir`** ⇒ 从那里可以定位 accepted manifest，再把「已验证的 proof」往下传 | 读源码；⚠️ **我没有实测 manifest 在该目录下的确切定位方式**，这是**你要先核实的第一件事**（见 §4 步骤 0）|
| P6 | 那把锁 `tests/test_f22_blocker1_core_stamp.py:470-500` 把「往裸 dict 上恢复印章 ⇒ 判卷必须重新信任」**写成了正向预期** ⇒ 新语义下它的断言方向就是错的，必须改写，不是保留 | 读测试源码与 docstring |

**⚠️ 外围性质、不承重、但请顺手核实**：我**没有**穷举「除 footprint/ring/cell 之外还有哪些 core-owned 字段
可以 replay-divergent 却仍被接受」。sol 也明说没穷举。⇒ **不要在交付里声称「已列全所有路径」**。

## 3. ⛔ 三条硬禁止

1. **⛔ 不许让候选自己提供 proof。** proof 必须由**落库方在重放成功之后**签发。
   凡「产品里多一个字段/bool/version 就算证明」的方案，都是同一个 bug 换个壳。
2. **⛔ 不许写「不与行为绑定的声明」。** 这个形状昨天一天现形三次（版本号当身份证据 → 印章自报 →
   coverage 手写常量）。你新加的任何 `evaluated/verified/trusted` 字样字段，
   **必须能通过「把对应实现中和掉、看该字段是否跟着变」的实测**。
3. **⛔ 判卷侧不许 import gt 之外的任何越界依赖，更不许让 gate①/执行器 import gt**（不变量 #4）。

## 4. 修法（sol 四步，逐字落实）

**步骤 0（先做，属核实不属施工）**：确认 P5 —— 从 `attempt_dir` 到 accepted manifest 的确切定位方式，
以及 manifest 上适合挂 proof 的位置（append-only attempts 账本，`src/agent/execution/manifest`）。
**若发现 accepted manifest 在判卷时点结构上拿不到 ⇒ 这是承重前提错 ⇒ 停下上报**（附你的实测），
不要自己改设计绕过去。

**步骤 1 —— 落库方比对 core-owned projection**（`stage_runner.py`，紧接现有 replay 之后）：
对 `replayed` 与候选做 canonical/hash 相等比较，**至少覆盖**：footprint · 每层 ring 与 cells ·
核之后的 window span/floor · corrections / conflicts / unsupported · stamp。
⚠️ **关键微妙处**：候选是**过了 host resolution / finalize 的最终产物**，其 window 字段可能**合法地**
与核直出不同。⇒ 先定义**不含 final-owned 字段**的 `DeterministicCoreOutputV1` 投影再比；
或在落库方重放完整 finalize 后逐字节比最终产物。**哪些字段是 final-owned，必须你机械测出来**
（⛔ 不许猜、⛔ 不许「先放宽到能过」）。**自证方式**：未改动的真实产物必须通过，
sol 那个伪造候选必须失败 —— 两边都要有实测输出。

**步骤 2 —— 由落库方签发 proof**：重放并比对成功后，签发
`deterministic_core_proof{core_version, input_hash, core_projection_hash}` 并**绑进 accepted manifest / sidecar**。

**步骤 3 —— 判卷只认外部 proof**：只有在拿到 accepted manifest 上**已验证的 proof** 时，
才允许把出模约定标为 `trusted`。裸 dict 上的内嵌 stamp **最多叫 `declared`**；
**无外部 proof 时 boundary / wall-extent 必须保持 `unavailable`**（不是 pass、不是 fail）。
这一步需要把 proof 沿 P4 的调用链往下传（`_grade_attempt_artifacts` → `_score_attempt_output` →
`score_service` seam → `_legacy_score_attempt_output` → 判卷）。

**步骤 4 —— 补一把真实 `StageRunner.record` 锁**：像 sol 探针那样构造「内部自洽但与 producer replay 不同」
的候选，**必须在 accepted pointer 移动之前稳定失败**。
⛔ 这把锁必须走**真实 `StageRunner.record` 入口**，不许在夹具里自造一个简化 writer。

**步骤 5 —— 改写那把错锁**（`tests/test_f22_blocker1_core_stamp.py:470-500`）：
它今天断言「裸 dict 恢复印章 ⇒ 重新 trusted」。新语义下正确的断言是
**「裸 dict 上的印章只能得到 `declared`，boundary 保持 unavailable」**。
⛔ 不许简单删掉了事 —— 它原本想守的「判定是 live 逐次读取、不是单向闩锁」这个性质要保留，
只是改成在**有/无外部 proof** 两种情况上验。

## 5. 验收条件（缺一条即未完工）

1. **全仓绿**：`python -m pytest tests -q -n auto`，与基线对账 **只增不减、零回归**；
   **判「跑完了」必须看到 `N passed` 汇总行**，⛔ 不许拿退出码文件当唯一凭据，
   ⛔ 退出码文件名不许跨两次跑复用（已实犯：陈旧的 `0` 被当本轮结果）。
2. **每把新锁都要 neuter 实测**：把被它守的实现中和掉，锁必须转红；**并逐把核对红点位置**。
   ⛔ 「变红」不等于「有分辨力」——请顺带回答「不加这处改动，这道门本来红不红」。
3. **⛔ 防假验证自检**：写明你的验收路径**真的经过了你改的那几行**
   （历史坑：冻结产物 + 跳段入口 = 假验证温床）。
4. **探针纪律**：**探针零输出 ≠ 目标不存在** —— 先自证探针看得见目标再断言。
   ⚠️ 本仓默认 `-n auto` **会吞掉 worker 的 stdout**，做打印式探针请用 `-n0`。
5. **两条真实产物行为**：`run_2026-08-09_f17_e2e_verify`（翻转前、真差 0.12 m）与
   `run_2026-08-11_continuous_e2e`（翻转后、正确）在修法前后的判卷结果各是什么，**逐条实测写出来**。
   （用户已接受「两份历史产物都会被拒判、需重跑一次」这个代价，⛔ 不要加历史白名单。）
6. **交付报告里如实分账**：哪些是实测、哪些是推理、哪些没验。⛔ 不许把未验证项写成已验证。

## 6. 运维硬约束

- **本摊必须能在一个 5 小时额度窗内收尾**（上一批撞窗三次，一次让 4 小时推理全丢）。
  ⇒ 若判断做不完，**优先保「步骤 1+2+4 的落库侧闭环 + 对应锁」**，把步骤 3 的判卷侧接线拆成第二段并**明确上报**。
- **⛔ 绝不 `git add -A` / `stash` / `checkout`**：另有一个席位（摊 C）在同一棵工作树上改
  `src/agent/correction/envelope_transform.py`。你**只**动你自己的文件；提交由 orchestrator 统一做。
- 中断时**不要总结自己做了什么** —— 本项目已三次实证「施工席中断的自述不可信」，orchestrator 一律以 `git diff` 为准。
