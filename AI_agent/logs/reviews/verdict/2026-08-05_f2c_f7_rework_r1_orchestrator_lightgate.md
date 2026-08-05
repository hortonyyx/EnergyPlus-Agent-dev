# orchestrator 轻门 · F-2c + F-7 返工 r1（`cac457a` / `49e5f42` / `5797653`）—— **PASS**

- **日期**：2026-08-05
- **施工席**：GLM-5.2（执行日志 [`../execution/2026-08-05_f2c_f7_rework_r1_glm.md`](../execution/2026-08-05_f2c_f7_rework_r1_glm.md)）
- **派工单**：[`../request/2026-08-05_f2c_f7_rework_r1_dispatch_glm.md`](../request/2026-08-05_f2c_f7_rework_r1_dispatch_glm.md)
- **上游**：[sol 对抗审 REWORK](2026-08-05_f2c_f7_crossreview_sol.md)（1 BLOCKER / 4 MAJOR）
- **判定**：**PASS** —— 四条 MAJOR 全修；**BLOCKER 未解、继续持有**（见 §5）

> **轻门 = 主控独立全量 + 独立 neuter + 抽查 diff + 裁决，⛔ 不采信施工方自述的任何数字。**

---

## 1. 独立全量（orchestrator 亲跑，零过滤）

```
2220 passed, 10 xfailed, 209 warnings in 466.88s
```

基线 `ca5e26c` = 2212 ⇒ **净增 8 条锁、零回归、xfail 持平**。**与施工方自报逐字一致。**

## 2. 独立 neuter —— 三条各自绑住，且两条落在**真实入口**

在 `--detach 4dcd96d` 的一次性 worktree 里做（仓库工作树零污染）。基线 `33 passed`。

| # | 手法 | 结果 |
|---|---|---|
| A | 把 `_check_floor_order` 的复合条件**合回** `A or B` 并整体归 `input_integrity_error`（= sol 抓出的原写法）| **恰好 2 红**：`test_f7_category_producer_floor_count_mismatch_is_model_draw_error` + **`test_f7_floor_count_mismatch_archived_as_failed_attempt_and_resampled`** |
| B | 删掉 `merge_isolated_output` 里的 stale 镜像清理块 | **恰好 1 红**：`test_f2c_rework_r1_stale_stage_root_mirrors_cleaned_before_accept` |
| C | 让 v3 catalog 前置条件失效、退回静默返回 `None` | **恰好 3 红**：缺 manifest / 缺 reading / **`test_f7_v3_missing_catalog_hard_fails_at_draw_correction_entry`** |
| — | POST-RESTORE 全部还原 | **33 passed** |

**⭐ A 与 C 各含一条行为锁**（加粗那两条）：验的是**真的归档+重抽 / 真的在 `_draw_correction` 入口硬失败**，
**不是只验 `category` 字段的值** ⇒ 符合「锁必须落在真实入口」。

**⚠️ orchestrator 自身一次失误（如实登记）**：第一次打 C 时正则匹配到 **0 处**（替换为空操作），
却拿到「22 passed」—— 若就此判定「锁不绑」或「已验」都是错的。
**已重打并确认替换生效后才采信。⇒ neuter 必须先确认「改动真的落下去了」，否则空操作会伪装成任一结论。**

## 3. 抽查 diff

| 检查项 | 结果 |
|---|---|
| MAJOR ②（逐点审计）| ✅ **54 处逐点审计**（`window_sources` 50 + `finalize` 2 + `parse` 2），审计表落执行日志；**仅 2 处归错**，均已修。`_check_floor_order` 的复合条件被**拆成两条独立 raise**，各带正确 category + 各自的注释说明「由谁决定」 |
| MAJOR ①（catalog 前置条件）| ✅ v3 下缺件即 `observation_reference_catalog_unavailable`，context 带 `missing_artifact` + `produced_by_stage="0_reading"`（**指名道姓**）；非 v3 路径行为不变 |
| MAJOR ③（`parse.py` 死标注）| ✅ 选 (b)：改为诚实注释说明它走内层盲重试通道 + 一条锁钉住**实际路径**（而非意图）|
| MAJOR ④（镜像/落盘次序）| ✅ **实测证实 sol 成立**（真实前态：stage root 预置陈旧 `*_view.json`），已修 + 锁 |
| 是否放宽任何既有判据 | ✅ 未发现 |
| 提交纪律 | ✅ 逐文件 add、三个独立提交、未 push、未扫走 orchestrator 未提交文档与未跟踪 run 目录 |

## 4. ⭐ 施工席如实登记的一条（orchestrator 认可，且这是本单的方法论产出）

**派工单 §3 我写「`parse_correction_draw` 只被两处调用」—— 实际有四处**（另有 `pipeline.py:697` 与 `finalize.py:94`）。

**施工席没有停下，而是核完后照做并如实登记**，理由：多出的两处**同样到不了分类路由**
（`:697` 同样包成 `RuntimeError`；`finalize.py:94` 仅当传 dict 时才调，而生产 live 路径都传已解析的 geom 对象）
⇒ **枚举错了、结论对了。**

**⇒ 这个分寸比机械停下更好**：停下上报的价值在于「结论会不会因此变」，不在于「派工单有没有笔误」。
**本轮第 8 次「派工方的题错了」，但第一次是「不影响结论」的那种。**

## 5. ⛔ BLOCKER 未解 —— 明确不算通过

sol 的 BLOCKER =「真实 sm21 `1_correction` accepted attempt 未产生」。**本批未解、也不该由本批解**
（直接原因是 F-9），**继续作为出口条件持有**。⛔ 不得因为本轮轻门 PASS 就宣称两批已收官。

## 6. 同日并行取得的两条外部证据（不属本批，但影响下一步判断）

- **F-9 调查完成**（Sonnet，零 LLM 成本离线复现）：又是**接口错位**，且发现代码里**本就存在优雅回滚路径**、
  只是同一个提交里两个调用点一个接了一个没接。详见其报告。
- **⭐ 探针 B 通过**：6 月 `intake_output.json` 灌进今天下游 ⇒
  `EnergyPlus Completed Successfully-- 6 Warning; 0 Severe Errors`（`eplusout.err` Severe 0 行）
  ⇒ **下游半边（9 subagent → IDF → EP）今天是好的**，本轮全部 9 条缺陷都集中在 1_correction 及其之前。
  产物 `case_tests/e2e_tests/sm21_anchor/probe_b_2026-08-05_legacy_intake/`。
