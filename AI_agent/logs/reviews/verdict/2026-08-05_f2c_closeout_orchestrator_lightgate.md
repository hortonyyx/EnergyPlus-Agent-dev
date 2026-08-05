# orchestrator 轻门 · F-2c 收口（`a8c367a`）—— **PASS**

- **日期**：2026-08-05
- **施工席**：GLM-5.2（执行日志 [`../execution/2026-08-05_f2c_closeout_glm.md`](../execution/2026-08-05_f2c_closeout_glm.md)）
- **派工单**：[`../request/2026-08-05_f2c_closeout_dispatch_glm.md`](../request/2026-08-05_f2c_closeout_dispatch_glm.md)
- **前序裁定**：[`../request/2026-08-05_f2c_boundary_ruling.md`](../request/2026-08-05_f2c_boundary_ruling.md)
- **判定**：**PASS**（下一道是 sol 跨家族对抗审，与 F-7 合并送审）

> **轻门 = 主控独立全量 + 独立 neuter + 抽查 diff + 裁决，⛔ 不采信施工方自述的任何数字。**

---

## 1. 独立全量（orchestrator 亲跑，零过滤）

```
2197 passed, 10 xfailed, 209 warnings in 423.72s
```

- 命令：`python -m pytest -n 6 -q`（**⛔ 未加 `-m` 过滤**；worker 数限为 6 而非 `auto`，
  因彼时另有一个 Sonnet 子代理席位在跑，防 16 worker × 350–700 MB 叠加撞容器内存上限。
  提速批已机械证明并行与串行**节点集合逐字节相等**，限 worker 不削弱门）。
- 基线 `9fd8a9a` = 2193 绿 / 10 xfail / 0 红 ⇒ **净增 4 条锁、零回归、xfail 持平**。
- **与施工方自报的 2197/10/0 逐字一致。**

## 2. 独立 neuter —— **两个方向各自独立绑住**

被验对象 = 本批新增的 `test_f2c_single_contract_detector_is_canonical`（「全仓只有一个探测器」）。
它由**两半**构成（`is` 同一性 + 源码扫描），必须分别验，**否则可能一半陪绑**。

| 方向 | 手法 | 结果 |
|---|---|---|
| (a) | 在 `src/agent/judge/reading_typed_adapter.py` 追加第二个 `def identify_reading_contract`（**会遮蔽 re-export**）| **红**，落在 `:440` 的 `is` 断言 |
| (b) | 在 `src/agent/correction/envelope.py` 追加第二个 `def identify_reading_contract`（**不影响 `is`**）| **红**，落在 `:455` 的源码扫描断言（`envelope.py` != `contract.py`）|
| POST-RESTORE | 还原后复跑 | **绿** |

⇒ **两半各自有分辨力**，不是一格红另一格陪绑。
neuter 在 `--detach a8c367a` 的一次性 worktree 里做，**仓库工作树零污染**（纪律：验锁 neuter 不在主树做）。

> **⭐ 判据纪律复核**：本项目 08-04 定的「neuter 变红只证明**实现被调用了**，不证明**判据有分辨力**」——
> 本次专门为此拆成两个方向打，就是为了不重蹈「一个方向红即判真绑」的覆辙（orchestrator 08-04 在此处栽过两次）。

## 3. 抽查 diff

| 检查项 | 结果 |
|---|---|
| B5 A6 两条守卫（`test_c2_b5_source_routing.py:215`、`test_c2_b5_parent_and_verts.py:1162`）是否被动过 | ✅ **一字未改**，原样恢复绿 |
| 是否就地复刻了第二个形状判定（第二把尺子）| ✅ 无。`src/` 下 `def identify_reading_contract` **恰好一处** = `src/agent/reading/contract.py` |
| judge 侧是否语义零变化 | ✅ 纯 re-export，**同一对象**（`is` 断言即在锁里）；调用点一字未改 |
| 新模块是否真的零 judge 依赖 | ✅ `src/agent/reading/contract.py` 只用 `dataclasses` + `typing` |
| 既存重复声明是否收敛 | ✅ `READING_CONTRACT_DETECTOR_VERSION` 从两份（`score_schema.py:550` + `reading_typed_adapter.py:43`）收敛为一份；`ReadingContractDecision.contract_id` 的 Literal 改由 `READING_PRODUCT_CONTRACT` 常量导出 ⇒ 消除「Literal 与常量两处记载」的漂移 |
| 提交纪律 | ✅ 逐文件 `git add`（8 个文件），**未扫走** orchestrator 的 `plan.md` 未提交改动，**未扫走** `case_tests/` 下未跟踪 run 目录；未 push |

## 4. 施工席如实登记的一条（orchestrator 认可其处置）

首轮全量撞 1 红 `test_d5_..._d6_new_judge_modules_stay_judge_only` ——
根因是它在 `contract.py` 的 docstring 里写了**字面** `src.agent.judge.score_schema`，被该**字符串扫描**守卫抓到。
**它改的是自己的措辞，没有动守卫。** ⇒ 处置正确（与「守卫是判据不是障碍」一致），复跑全绿。

## 5. 结转 / 留给 sol 审的点

- 本批**不含** F-7（另一席位施工中），二者合并后一起送 sol 跨家族对抗审：
  [`../request/2026-08-05_f2c_f7_crossreview_brief_sol.md`](../request/2026-08-05_f2c_f7_crossreview_brief_sol.md)。
- **⚠️ 工作树仍有未提交内容**（非本批产物）：`AI_agent/plan.md` 的实时更新 +
  `AI_agent/logs/reviews/` 下本轮四份新文档 + `case_tests/` 下三个未跟踪 run 目录。
  **收工统一处理时须先通读 `git status`，⛔ 不许 `git add -A`**（本项目实犯过：收工扫走并行席位半成品并推送）。
