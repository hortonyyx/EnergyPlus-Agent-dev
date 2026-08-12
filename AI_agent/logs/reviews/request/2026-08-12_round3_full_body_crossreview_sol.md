# 请求书 · **第三轮**跨家族复审 — 主体全量（前两轮均未审到主体）

- **日期**：2026-08-12 · **席位**：sol（GPT-5.6），effort = `max`
- **审阅范围** = 两个 commit：`a17ed0f`（四摊）+ `HEAD`（MAJOR-B1 补齐）。**工作树干净。**

---

## ⭐⭐⭐ 0. 最重要的一条：**停止规矩已分层，请按新规矩执行**

**前两轮你都按「发现前提错即停」停下了，两次都对 —— 我的请求书确实错了。
但代价是：BLOCKER-1 修法、摊 B/C/D、上一轮 7 条 finding，到现在【一次都没被真正审过】。**

你第二轮裁决书自己写着「这项前提错误**不改变**范围裁定」—— **你知道那条错是外围的，是我的硬规矩逼你停。
规矩的缺陷在我这边，现已修正**：

> **① 承重前提错**（错了则整个任务方向/范围作废）⇒ **停下上报，不必继续。**
> **② 外围论据或支撑证据错**（错了不改变任务方向）⇒ **报告该错，然后【继续把其余部分审完】。**

**⛔ 本轮请不要因为某一句描述有误就停掉整单。** 把错记进裁决书的「派工方前提错误」一节，继续审。
**本轮的成功标准 = 主体真的被审到，而不是又抓到我一个错。**

---

## 1. 送审主体（全部尚未受审）

| # | 内容 | 位置 |
|---|---|---|
| 1 | **F-22 BLOCKER-1 修法**：确定性核【无条件】印章 + 判卷验印 | `deterministic.py` · `schema.py` · `judge/correction_score.py` · `tests/test_f22_blocker1_core_stamp.py` |
| 2 | **F-9 S2**（首版 + MAJOR-B1 补齐） | `window_position.py` · `validator/checks/correction.py` · `tests/test_f9_route2_s2_authoritative_projector.py` |
| 3 | **标注法观测量**（纯观测） | `envelope_transform.py` · `finalize.py` · `tests/test_c2_b2b_envelope_transform.py` |
| 4 | **F-23** | `tests/test_c2_b4b_phase_d.py` |
| 5 | **上一轮你标「未裁定」的 7 条**（MAJOR-1/2/3 · MINOR-1/2/3 · NIT-1）——对应代码自 `21b4739` 起未再改动 | 见 [第一轮裁决](../verdict/2026-08-12_f22_f9s0s1_rework_rereview_sol.md) |

**⚠️ 本请求书刻意少写事实断言**（前两轮的错都出在我的断言上）。
下面 §2/§3 是**我的主张，请自行取证**；凡我没写的，请以代码与实测为准。

---

## 2. orchestrator 的主张（**全部当作待证伪**）

| # | 主张 | 我的做法 |
|---|---|---|
| a | 全仓 **2557 passed / 10 xfailed / 0 failed** | 独立跑，rc=0，`.rc` 新文件名且时间戳与日志同刻，汇总行在（今日起点 2470）|
| b | 印章**无条件**（唯一 v3 `return` 前最后一句、无 `if`），能覆盖伪造值 | 读码 + 换方向 neuter：把「只在核真改了东西时才盖」的坑造回去 ⇒ 零位移锁转红 |
| c | 真实产物：`f17`（翻转前，真差 0.12m）拒判 · `continuous_e2e`（翻转后，正确）**也拒判**（用户已接受的代价）| 直接调 `_is_trusted_output_convention` |
| d | F-9 S2 接线为真 | 换方向 neuter：中和共享实现 ⇒ 18 红，含两条真实入口锁 |
| e | 标注法四态真可分 | 第三方向 neuter：把被推翻的原口径装回去 ⇒「按轴线」「超容差」两格转红 |
| f | **⛔ 新 finding `MAJOR-B2`（见 §3）** | 第五方向 neuter |

**⭐ orchestrator 自己答不了的**：
1. **印章方案本身的工程正确性** —— 我参与了岔口分析，判不了。
2. **fail closed 的第 N 类路径** —— 我只能想到我想到的那些；**你第一轮正是用「第五类」推翻了我的四分类。**
3. **席位点名要复核的两条**（见 §4）。
4. 摊 D 把「一次性纪律检查被烤成永久测试」的定性 —— 证据链我复核过，**但它是唯一信源**。

---

## 3. ⛔ orchestrator 轻门新抓的 `MAJOR-B2`（请裁级别与修法）

**中和条件 2 的实现**（`_is_unique_nearest` 恒 `True`）后，产物**仍然宣称**该条件已验：

```
evaluated_conditions   = [..., "unique_mutual_nearest"]
unevaluated_conditions = []
```

根因 = `CURRENTLY_EVALUATED_POSITION_EVIDENCE_CONDITIONS`（`window_position.py:609-610`）是**手写常量**，
`:1534-1535` 直接赋给报告，**不由代码实际执行了什么推导**。

⇒ **与你第一轮抓的 BLOCKER-1 同形：不与行为绑定的声明 = 带变量名的注释。**
而 **S3 正要靠这份声明决定该 decision 能不能承重。**

**⚠️ 责任如实说明**：我的派工单只要求「结构化记录 evaluated/unevaluated」，
**没要求由行为推导** ⇒ 席位照做了。但同段写了「使将来任何再次的部分实现不可能悄悄冒充完整」，
按此意图现实现不达标。**请裁：这算 MAJOR 还是 BLOCKER，以及修法方向。**

---

## 4. 施工席自己点名要你复核的两条（诚实披露，请重点打）

1. **facade 家族过滤是它的架构判断**（设计稿未逐字给算法）：条件 2 的 plan 侧候选域若不按 facade family 过滤，
   真实 clean e2e 产物上 **6/15 扇窗**会被误判为同分歧义（南北/东西对称）。
   它用 `geom.facade_segments`（Vg，已物化，非 bbox 极值）做过滤。
   ⚠️ 它同时指出：该过滤依赖 `facade_segments` 已物化，**S3/S4 若把判定挪到 hydration 之前会失效**。
2. **一处真实行为收紧**：z 数据缺失（`not_declared`）的被引源，补齐前被两道既有守卫**都放过而静默 accepted**，
   补齐后改判 `rejected`。它认定这是正确收紧（否则「省略 z 就能跳过条件 2/3」）。**请核实这个判断。**

**另有 6 条它自陈的未验证项**，在
`AI_agent/logs/reviews/execution/2026-08-12_majorb1_s2_pairing_completion_claude.md` §5。

---

## 5. 两条新登记债（未修，请判要不要升级）

- **F-24**：判卷侧车 cache key **不含印章状态**。orchestrator 核实「当前零影响」依据成立
  （盘上 `scorer_schema` 分布 9×20/8×4/7×4/6×1，无一到 `"10"`），**但结构性缺口是真的** ⇒ fail-open 入口。
- **F-25**：`SCORER_SCHEMA` 同名两处、值不同 —— `run_stage.py:94="10"` vs `judge/score_schema.py:40="8"`。

---

## 6. ⛔ 硬纪律

1. **⛔ 不要任何 git 写操作**（`checkout`/`stash`/`clean`/`commit`/`reset`）。只读命令随意。
2. **判「是否已接线／已关闭」只能用行为验证**，⛔ 不能用 grep / 精确 AST 语法。
3. 验锁 neuter **只在 `/tmp` 做**，做完还原。
   ⚠️ **本仓 pytest 默认 `-n auto`，xdist 会吞掉 worker 的 stdout** —— 要看打印必须加 `-n0`
   （orchestrator 今天因此差点误判一次「探针零输出 = 目标不存在」）。
4. **⭐ 探针零输出 ≠ 目标不存在**：先自证探针看得见目标，再断言目标变没变。
5. 跑测用**独立新文件名**落日志与退出码，判跑完**看汇总行**。**基线 = 2557 / 10 xfail / 0 红。**

## 7. 输出

裁决书落 `AI_agent/logs/reviews/verdict/2026-08-12_round3_full_body_crossreview_sol.md`：
总判定 · **§1 五项主体逐项裁定（这是本轮的主要产出）** · `MAJOR-B2` 级别与修法 ·
§4 两条的复核结论 · 新发现 · **派工方前提错误（如有，记录后继续）** · **你未验证的项**。
