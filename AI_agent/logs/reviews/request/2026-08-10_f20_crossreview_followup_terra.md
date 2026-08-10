# 派工单 · F-20 交叉审返工（sol 的 MAJOR-1 / MINOR-1 / NIT-1）

- **日期**：2026-08-10 · **席位**：GPT 侧 **`gpt-5.6-terra`** · effort **high**
- **基点**：分支 `6.15_ValidationArchM0toM4`，**HEAD = 最新**，工作树干净
- **全仓基线**：**2358 passed / 10 xfailed / 0 failed**（`-n 8`，约 7 分 45 秒）
- **上游裁决**：[sol 交叉审](../verdict/2026-08-10_f20_crossreview_sol.md) = **CHANGES REQUIRED**
- **⛔ 谁写谁不批**：sol 提的 findings，**你来修**，orchestrator 轻门。

---

## 1. ⛔ MAJOR-1（本单主菜）：resolver 级 fail-open 无锁

### 缺陷（**orchestrator 已独立复现，⛔ 不必再证，直接修**）

把 `src/agent/execution/validation_run.py` 里 `_resolve_correction_source` **V2 侧**的

```python
    except ValueError as exc:
        return _CorrectionSource(..., trust_status=CheckStatus.FAIL, ...)
```

改成回退 `_resolve_legacy_stage_root(snapped, reason=...)`（= 经典 fail-open）
⇒ **69 项定向测试（`test_c2_b5_artifact_trust` + `test_check_parity` + `test_validation_run_baseline`）全绿、零锁捕获。**

**⇒ 这正是派工单禁令第 2 条、也是设计稿最强调的那条规则，而全仓没有任何锁守着它。**

### ⭐ 根因（决定了修法怎么写，**请务必读懂再动手**）

**L2/L3 用的是 v3 夹具** ⇒ fail-open 退回 stage-root 之后，
那份 **v3 几何又被 `_resolve_legacy_stage_root` 自己的「v3 在 legacy 状态下必须 FAIL」拦住**
⇒ 最终仍然 `FAIL` ⇒ **缺陷被遮蔽、锁照样绿。**

⭐ **同一个遮蔽模式，F-20 施工席自己在 NIT-1 上发现过**
（它的 neuter⑤ 记着：「NIT-1 的 fail-open 变异在 v3 夹具下被另一条独立防线掩盖、红不了
⇒ 补 legacy-schema 变体才精确捕获」），**但没有把它推广到 L2/L3/L8**。
sol 说的「换成可构建的 legacy stage-root 后能产出 digest 并成功签发批准」正是这一层。

### 要做的

补一把（或一组）锁，**必须满足**：

1. **stage-root 放一份可构建的 legacy-schema 几何**（不是 v3）——
   这样 fail-open 一旦发生，**回退路径会真的走通、产出 digest、甚至签发批准**
   ⇒ 缺陷不再被第二条防线遮住。
2. **V2 账本侧制造一次 loader 拒绝**（例如篡改 accepted `output.json` 使哈希对不上，
   照 L2 的既有做法）。
3. **断言**：trust 行必须 `FAIL`、`geometry_digest` 必须为 `None`、
   **且 `approve_geometry` 必须签不出检查点**。
4. **⭐ 自证前提（硬要求）**：先在**未变异**的同一夹具上断言 trust `PASS` 且 digest 非空；
   前提破了要**大声报错**，⛔ 不许静默退化成空锁。
5. **⭐ neuter 必须实测**：把上面那条 fail-open 变异注入 `/tmp` 副本
   ⇒ **你这把新锁必须转红**。⛔ **不红就停下上报、不要交付。**

---

## 2. MINOR-1：「意外异常 ⇒ ERROR」只覆盖了一半

设计稿状态表最后一行要求「已知磁盘/载荷异常以外的意外代码异常 ⇒ `ERROR`」，
但实现里该映射**只包住 accepted-loader 那一段**；
**manifest dispatcher 与 legacy payload parser 会直接抛出**
⇒ `validate_case` **崩出**，而不是产出 `correction.accepted_artifact_trust` 报告。

⚠️ 二者仍是 fail-closed（不回退），故 sol 未升 MAJOR。

**要做的**：扩大 resolver 的异常映射范围，使这两条入口的异常也落成 trust 行
（**已知载荷型 ⇒ `FAIL`；意外型 ⇒ `ERROR`**，与设计稿一致），
并补 **两把锁**：① manifest-dispatch 抛哨兵异常 ② legacy payload 损坏。
每把锁同样要**自证前提**。

---

## 3. NIT-1：清掉几条无信息断言

sol 列的（以裁决书原文为准）：

- **L5** 有一条**同内存对象字段自比**（比较同一次调用返回的同一对象的两个字段/引用）；
- 三条被前置 `== FAIL` **逻辑蕴含**的冗余断言
  （如先断言 `status == FAIL`、再断言 `status != NOT_APPLICABLE`，后者恒真）——
  裁决书点了 `:1231`、`:1297` 两处实例。

**要做的**：删掉或改成**有信息量**的断言（例如改断言具体的 reason / source 字段）。
⛔ 不许只是把它们注释掉。

---

## 4. ⛔ 边界

1. `src/` 只允许改 **MINOR-1** 那一处异常映射；⛔ 其余生产码不动
   （尤其 ⛔ 不许改 `stage_runner.py`、⛔ 不许动 `build_geometry` / 加载器的合同）。
2. neuter 只在 `/tmp` 副本做。⚠️ **副本必须拷 `data/`**
   （orchestrator 本轮因漏拷 `data/dependencies/Energy+.idd` 拿到过一次「10 条红」的假结果），
   且 `case_tests` 可以软链到主仓（只读）。
3. ⛔ 不许 `git add` / `commit` / 切分支。⛔ 不许读 `case_tests/test_baseline/gt/`。
4. ⛔ 不许改那两个 golden 基线目录、⛔ 不许动 `run_2026-08-07_f13_e2e_verify`
   （冻结锁的锚点）。

## 5. 验收

1. **独立全量**：`python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20fu_full.log 2>&1; echo $? > /tmp/f20fu_full.rc`
   ⚠️ ⛔ 不要 `-n auto`（~98% 静默 OOM）· ⛔ 中间不接任何管道 · ⛔ 不要叠 `nohup`/`&`。
   **判据 = 汇总行 + 属于该命令的 `.rc` 两者俱在**；
   ⛔ **`.rc` 缺失只说明「没跑完」、不等于「被杀」** —— 判活查 `pgrep`（全量约 7 分 45 秒）。
2. **逐把新锁 neuter**：分别报「注入什么变异 ⇒ 恰好哪几条红 ⇒ 有无连带」。
3. 明确回答：**MAJOR-1 那条 fail-open 变异下，你的新锁红了吗？**

## 6. 交付物

执行日志落 `AI_agent/logs/reviews/execution/2026-08-10_f20_crossreview_followup_terra.md`。

## 7. 合法退出口

- MAJOR-1 的新锁在 fail-open 变异下**不红** ⇒ 停下上报（说明锁没绑住目标）；
- 造不出「可构建的 legacy-schema stage-root」夹具 ⇒ 停下上报；
- MINOR-1 的扩大映射会牵动超出本单边界的生产码 ⇒ 停下上报；
- 本单某两条要求互相冲突 ⇒ 停下上报。

**⛔ 派工方（orchestrator）自陈错误率 = 15/15**，且**本批已被 sol 推翻过一次签字判断**
（「L2/L3/L8 已独立覆盖」是施工席与 orchestrator 共同签的，事后证明错了）。
**顶住不照做、如实上报是期望行为，不是失败。**
