# 派工单 · 摊 G —— 缓存绕过当前 proof（`BLOCKER-1` 剩余半）+ F-24 第三项身份

- **日期**：2026-08-13
- **席位**：GPT 侧执行档（terra）
- **审阅去向**：Claude 侧（跨家族）
- **依据**：[sol 第四轮裁决](../verdict/2026-08-13_round4_blocker1_closure_crossreview_sol.md) §2.2 / §2.3 / §3.1 / §3.5
- **基线**：`2573 passed / 10 xfailed / 0 failed`（orchestrator 独立实测，rc=0、汇总行在）
- **并行席位**：另有一摊（摊 F）在改 `src/agent/graph.py` / `src/agent/react.py` / 下游 subagent。
  **你的文件面 = `scripts/tool_scripts/run_stage.py` + `src/agent/judge/*` + 你自己的测试**。
  ⛔ 绝不 `git add -A` / `stash` / `checkout`；⛔ 不要 commit。

---

## 0. 停止规矩（分层）

1. **承重前提错** ⇒ **停下上报**。2. **外围论据错** ⇒ **报告写明后继续做完主体**。
派工方历史错误率 **17/17**（今日两条，其中一条正是**给你的上一摊**写了互相冲突的验收条件）。请主动证伪本单前提。

## 1. 要修的缺陷（sol 实测，⛔ 不是推理）

**信任判据被缓存绕过。** sol 的行为反例：

```text
production_entry=_judge_gt_artifacts
manifest_output_hash_check_passed=True
proof_resolver_after_deletion=None
scorer_calls_after_deletion= []
cached_trusted_after_deletion= True
```

步骤：用真实 `StageRunner.record` 写出 accepted B5 产物 → 从生产判卷入口 `_judge_gt_artifacts` 首次计算
得到 `trusted=True` 缓存 → **删除 `deterministic_core_proof.json`** → 先确认
`_resolve_core_proof_for_attempt(...) is None` → 再走**同一个生产入口** ⇒
**判卷函数零调用、旧侧车直接复用、仍然 `trusted=True`。**

**根因是时序**：`run_stage.py:1785-1795` **先** `_load_valid_score_sidecar`，只有 miss 之后才在
`:1797-1802` 解析 proof；而当前缓存判据（`:1689-1718`）里**没有 proof hash / proof 是否存在 /
accepted-record identity**。⇒「判卷只认外部 proof」**在首次计算成立，在缓存命中不成立**。

**⛔ 这条已经不是纯结构性缺口了**：orchestrator 今日跑的真实 run
（`run_2026-08-13_post_blocker1_e2e`）已经在盘上留下**本仓第一份 `scorer_schema="11"` 的
`trusted=True` 缓存** ⇒ 这个洞现在**真实可命中**。

**第二条（F-24 第三项）**：sol 把判卷实现本体换成另一个实现、两个 live 常量不变
⇒ **陈旧缓存照样命中**（`changed_scorer_calls=[]`, `stale_cache_reused=True`）
⇒ 「第三项由人记得 bump 就够了」**不是文字之争，是可观察行为**。

## 2. 修法（sol 给的最低口径，四条 + F-24 一条）

1. **缓存查找之前**先解析并验证**当前** accepted proof；
2. **缓存身份绑定「当前外部根认证过的 proof identity」** —— 至少 **proof bytes hash + accepted record identity**；
3. **缓存自称 `trusted=True` 时，proof 缺失/失效必须 miss 并重算为拒判** —— ⛔ 不许信缓存自报；
4. 补**真实入口锁**：「先有 trusted 缓存 → 删除/篡改 proof → resolver 返回 None → **缓存 miss** →
   `trusted=False`」，**同时保留 proof 不变时必须命中的正向锁**；
5. **F-24 第三项**：把 **scorer implementation identity** 也绑进 `scoring_semantics`
   （⛔ 不许是又一个手写常量 —— 必须能通过「换掉实现 ⇒ 该身份跟着变 ⇒ 缓存失效」的实测）。

## 3. ⭐ 治理前提已变（**今天用户刚拍的，会影响你的措辞与范围**）

用户 2026-08-13 拍板 **明文收窄威胁模型**（已落 `AI_agent/decision_log.md §5.14.1`）：

> **本项目防的是「产物自称经过确定性核」，⛔ 不防「拥有 run 目录写权的主体手动改盘」。**

**对你这摊的三条直接影响**：
- ⛔ **不要**去做签名 / MAC / 外部只写一次存储 —— **那些出路本轮不采纳**（威胁模型已收窄）。
- ⛔ **措辞纪律**：代码注释 / 字段名 / 报告里**不得**把账本或 proof 侧车称为
  「tamper-evident external root」「防篡改的外部信任根」或等价说法。
  `trusted` 在本口径下的准确含义 = **「由落库方在重放并逐键比对成功后签发过」**，**不是「无法伪造」**。
  **若你发现今天已落库的代码里有这类过强措辞，请一并改掉并在报告里点名**（这属于本摊范围）。
- ✅ 但**本条不豁免这摊活**：缓存绕过 proof 与信任根之争**无关** —— sol 明确它**独立阻止 closure**。

## 4. 验收条件

1. **正反两把锁都要**（⛔ 只有反向锁 = 本项目栽过的「只有负向断言的门恒红不可观测」）：
   反向 = 删/篡改 proof ⇒ 缓存 miss ⇒ `trusted=False`；正向 = proof 不变 ⇒ **缓存必须命中**（否则你只是把缓存关了）。
2. **F-24 第三项的锁**：换掉判卷实现（两个常量不变）⇒ 缓存必须失效。
3. **回归用例自证前提**：先断言「修法前该夹具上确实能复现 sol 的反例」，再断言修后不能；
   **前提破了要大声报错**，⛔ 不许静默退化成空锁。
4. **neuter 实测**：每把新锁中和其守护实现 ⇒ 转红 + 红点位置对 + 回答「不加这处改动本来红不红」。
5. **盘上那份真实缓存**：说明你的修法对
   `case_tests/e2e_tests/sm21_anchor/run_2026-08-13_post_blocker1_e2e/1_correction/attempts/*/score_vs_gt.json`
   这份**已存在的 schema-11 trusted 缓存**的实际影响（会不会失效、要不要重算）。⛔ 不要删它。
6. **全仓**：与基线 `2573 passed / 10 xfailed / 0 failed` 对账、零回归；**判跑完看 `N passed` 汇总行**；
   退出码文件用新文件名。⚠️ 打印式探针用 `-n0`。
7. **如实分账**：实测 / 推理 / 未验。⛔ 不许把未验证项写成已验证。

## 5. 运维

- 本摊**必须能在一个 5 小时额度窗内收尾**；做不完就停下上报，
  ⛔ 不要停在「改了行为、锁一把没写」的中间态。
- 中断时**不要总结自己做了什么**（orchestrator 一律以 `git diff` 为准）。
