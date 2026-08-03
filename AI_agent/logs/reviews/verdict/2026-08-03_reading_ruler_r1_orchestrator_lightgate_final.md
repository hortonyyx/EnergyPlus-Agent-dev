# R1 批 B · r1 返工 · orchestrator 轻门（终版）

- **日期**：2026-08-03
- **被审对象**：r1 全 7 条（`63a41b9` → `22f8f14`，共 9 个 commit）
- **施工**：GLM-5.2（R1-1…R1-4 / R1-6 / R1-7 + context 接线）+ **terra**（R1-5，GLM 额度耗尽后接手）
- **性质**：orchestrator 轻门 = 唯一权威门。**本文只覆盖 r1；批 C 未开工。**

---

## 0. 总判定：**r1 七条全部落地，轻门通过**

| 条目 | 修的是 | commit | 状态 |
|---|---|---|---|
| **R1-1** | `flow`/`run` 标准入口：声明严格档、实际跑宽松档 | `63a41b9` + `2daf846`(context) | ✅ |
| **R1-2** | 档位拼错一个字母 ⇒ 静默降档（+ **J-2** 混合列表 raise） | `3e3ac1e` | ✅ |
| **R1-3** | 离线审计面把四态折回 bool、丢结构化声明 | `6d38f0c` | ✅ |
| **R1-4** | fail-closed 落在冻结产物写盘之后 ⇒ 可绕过 | `c9b1aae` | ✅ |
| **R1-6** | 签字来源零校验（`"0"*64` 占位指纹放行） | `472c844` | ✅ |
| **R1-7** | 配置与 CLI 冲突静默取其一 | `1e3be7f` | ✅ |
| **R1-5** | 冻结政策未成为整个 run 的政策（含**人工签字门**） | `c56cbe1` + `22f8f14`(日志) | ✅ |

**独立全量**（orchestrator 自跑 `pytest -q -n 8`，工作树干净、⛔ 无 `-m` 过滤）：

```
2089 passed, 10 xfailed, 165 warnings in 353.21s
```

**与施工方自报逐数字一致。** 起点 2068（r0 末）→ 2089，**净增 21 条锁，零回归**。

---

## 1. 核心缺陷已消失（独立核实，非采信）

裁定 §1.3 点名的两处 —— `confirm_geometry` / `geometry_is_approved` 用 `RunPolicy()` 全默认
⇒ **人工几何签字门恒按 `exploratory`+`rectangular` 判** —— 现已改为 `effective_run_policy(run_dir)`。

**且做得比要求多**：`GeometryApproval` 现在同时钉上
`run_policy_source` / `run_policy_legacy_defaulted` / `run_profile` / `capability_profile`
⇒ **一次人工签字从此绑定「它是在哪个档位下签的」**，事后可审。这是我没要求、但方向正确的加固。

---

## 2. ⭐ 独立 neuter（轻门的承重动作，本项目栽过两次的地方）

**做法**：把 `step_orchestrator.py` 里两处 `effective_run_policy(run_dir)` 换回 `RunPolicy()`
（= r0 的缺陷形态），跑 `test_run_stage_flow` + `test_orchestrate_baseline` + `test_reading_ruler_r1_batchB`。

```
FAILED tests/test_run_stage_flow.py::test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers
FAILED tests/test_run_stage_flow.py::test_R1_5_approve_geometry_uses_frozen_policy_check_headers
2 failed, 82 passed, 1 xfailed
```

⇒ **恰好红这两条 R1-5 锁、零连带**；POST-RESTORE `test_run_stage_flow` **30 passed** 全绿、工作树逐字复原。

**⇒ 锁是真绑的。** 对照本项目两次教训：r0 的 L-13 摘掉实现仍绿（喂内部函数 `None`、绕过真实 argparse 默认）；
更早的 `score_vs_gt is not None` 绿着而判卷在拒 —— **这次的断言落在 `checks.json` 头部字段 + 具体 check-id 行上，
且经独立 neuter 证明真绑。**

---

## 3. terra 的「判断取舍」已核实成立

terra 在 review-ask 里主动披露：**draw budget 与 reread availability 属运行期操作旋钮、不是冻结的档位政策**，
故 `submit_verdict` / `_verdict_outcome` 里保留的 `policy or RunPolicy()` 不改。

**orchestrator 核实 ⇒ 成立**：这两个函数只读 `policy.reading_runner_available` 与
`policy.budget.per_stage_draws`，**从不读 `run_profile` / `capability_profile`**；
唯一生产调用者 `run_stage.py:2060` 确实传了真实 policy。

⇒ **归类正确，且它是「披露」而非「静默跳过」** —— 派工单要的正是这个行为。

---

## 4. 边界合规

| 项 | 结论 |
|---|---|
| `gt/**` 与 sm24 `testdata_prompt.json` 零触碰 | ✅ |
| 真实 sm24/sm21 manifest `content_sha256` 逐字不变 | ✅（守卫测试仍绿） |
| 未 push | ✅ |
| 批 C 未顺手做 | ✅（半截仍在 `git stash`） |
| 登记为缺口而非修的 | terra 报 **none**；GLM 侧的登记见其执行日志 |

---

## 5. 尚未完成（登记，不当已完成汇报）

1. **r1 的交叉对抗审未做**。施工跨了两个家族 ⇒ 按「谁写谁不批」需**两路**：
   - **R1-5（terra 产出，GPT 侧）⇒ 派 GLM 审**。这正是项目对 GLM 的能力画像所长
     （**验证性审阅达最高档**：给定清单验锁真绑、零漏判零误报；探索性审阅不及格）——
     而这里清单是现成的（裁定 §1.3 + 派工单同族点名），要验的就是「锁是否真绑」。
   - **R1-1…R1-7 的 GLM 产出 ⇒ 派 sol 重审**，并**补完上轮被平台内容策略中断的 P-3…P-9**。
2. **批 C 未开工**（渲染 / 命名 / 像素预算）。半截 28 行在 `git stash`（`batchC-wip-render-pixel-budget`）。
3. **⛔ 约束不变**：批 A/B/C 三批全绿之前，不得发布任何识图分数或「识图变好/变坏」的结论。

---

## 6. 运维记录（本轮真实代价）

| 窗口 | 时段 | 时长 | 产出 |
|---|---|---|---|
| GLM 下午 | 15:38 起（**3x 高峰**） | 35 min | 1 条 |
| GLM 晚间 | 20:40 起（2x 非高峰） | 67 min | 6 条 |
| terra | 13:50 UTC 起 | ~30 min | 1 条（R1-5，最大的一条） |

**⇒ 同一个 5h 窗口，高峰与非高峰产出差约 6 倍。**（教训已落 plan.md 运维段 + memory。）

**⚠️ orchestrator 自身两次同型失误（如实登记）**：用 `ps | grep | head -1` 取席位 pid，
**两次都抓到包装层进程**（`setsid` 壳 / `bash -c` 壳）而非真正干活的进程 ⇒
第一次虚惊、**第二次直接产出错误结论「terra 零提交退出」并已汇报给用户**（随后自查纠正）。
**修法**：哨兵判据改为**不依赖 pid 的进程家族判据**（`ps aux | grep -c '[c]odex exec'` 归零）。
**这与项目已有的「哨兵判据不得用文件非空」是同一条教训 —— 判据不得落在「看起来像那个东西」的第一个匹配上。**
