# 出稿请求书 · F-20 修法设计稿（sol / GPT 侧）

- **日期**：2026-08-10 · **出稿席**：**`gpt-5.6-sol`**，effort **max** · **只读，⛔ 不施工**
- **为什么是你出稿**：本项目 08-09 有一次教训 —— orchestrator **亲手写**的 F-9 路线②设计稿被你判 **REWORK**
  （3 BLOCKER），最贵的一条与它 08-06 犯过的是**同一个盲区**。⇒ 立了纪律：
  **被判 REWORK 的稿子不宜再由同一作者写**，且**设计稿本身就不该由 orchestrator 亲手出**。
  本稿由你出、Claude 侧对抗审 —— 顺序与上次相反，「谁写谁不批」照旧成立。
- **基点**：分支 `6.15_ValidationArchM0toM4`，**HEAD = `2d991e0`**，工作树干净。
  全仓基线 **2345 passed / 10 xfailed / 0 failed**。
- **调用预算**：一轮出稿。⛔ 不要跑全仓测试（8 分 45 秒，且与出稿无关）。
  探针如需跑，**只在 `/tmp` 做**。

---

## 1. 缺陷（已实测坐实，⛔ 不要重做调查）

`validate_case`（`src/agent/execution/validation_run.py:218`）重建几何时这样调：

```python
bg = build_geometry(geom, capability_profile=profile)      # ⛔ 没有 window_host_proof
```

而 v3（`c2_b5_v1`）产物的 `build_geometry` **要求** `VerifiedWindowHostProof`
（`build.py:207-208`）⇒ 抛 `v3 build requires VerifiedWindowHostProof`
⇒ `2_modelling` 记 error ⇒ `geometry_digest = None` ⇒ `approve_geometry()` 返回 None
⇒ **几何确认门无法签发检查点**。

**⛔ 比表面严重**：`--geometry auto` 与**人工** `approve-geometry`（`run_stage.py:2458-2460`）
**走同一个 `approve_geometry()`** ⇒ 不是「自动批不了、人来批即可」，而是 **v3 路径彻底堵死**。

**⇒ 这是当前唯一挡住主线的墙**：0_reading→1_correction→2_modelling→3_split_pairing 的 gate①
本轮全部已过，就停在这道门。

---

## 2. 必读产物（**先读，不要重新调查**）

| 文件 | 是什么 |
|---|---|
| `AI_agent/logs/experiments/2026-08-10_f20_validate_case_v3_proof/README.md` | **调查全档**（Claude 侧 Sonnet 出品，363 行，Q1–Q6 逐条 + 证据） |
| 同目录 `probe_f20.sh` | 可复跑只读探针（自带 `mktemp -d`，跑完自清） |
| `AI_agent/logs/reviews/verdict/2026-08-10_f20_investigation_orchestrator_lightgate.md` | **orchestrator 轻门裁决**（独立复核了 6 条承重命题 + 补了 2 条施工席没做的） |
| `AI_agent/CLAUDE.md` §1.5 | 仍有约束力的关键不变量（**尤其 #4 gt 铁律、#6 建筑复杂度可扩展性铁律**） |

---

## 3. 岔口（**已被调查重描过，⛔ 不要沿用旧措辞**）

上一轮 plan.md 把它写成「① 耦合 manifest（**新**耦合）vs ② 多一处副本（**新**副本）」。
**两边都不准** —— 调查实测：加载器 `load_verified_accepted_correction` 已有 **7 个生产调用点**
（含 `execution/correction_audit.py:90`，就在同一层），且 stage 根**本来就镜像着** `output.json`
（与 `attempts/001/output.json` sha256 逐字节相同）。**两个「新」都不新。**

**真岔口**：

- **选项①**：`validate_case` 在能找到 `_run/run_manifest.json` 时，改走
  `load_verified_accepted_correction(run_dir=, manifest=)` 取 proof；
  **对没有账本的旧 run 保留今天的行为**。
- **选项②**：把 `feature_states.json` / `window_resolver_inputs.json` / `window_hosts.json`
  也镜像到 stage 根（`stage_runner.py:560` 那两行旁边再加三行），`validate_case` 继续不碰账本。

### 调查已实测的三条判据（你可以质疑，但请给出反证）

1. **防篡改强度不是「各有取舍」**：篡改 stage 根一个非几何字段（`windows[0].room`）
   ⇒ `1_correction` 的 17 项检查**逐条与未篡改对照完全相同**（含 `facade_frame_cross_check`）
   ⇒ **选项②在这件事上基本等于没有防线**；同样篡改落在账本绑定的 attempt 上
   ⇒ `ValueError: accepted 1_correction output.json hash does not match manifest record`，逐字节必中。
2. **选项②新增轴 B 风险，选项①不新增**：②要新增 3 处**手写**镜像 ⇒ 四个文件各两份物理拷贝。
3. **选项①的 blast radius 是真的、但可避免**：本仓 **5 个 run 目录完全没有 `_run/run_manifest.json`**，
   其中 2 个是 `tests/test_validation_run_baseline.py` 在用的 **golden 正基线**
   ⇒ 若实现成「一律要求账本」，这两个基线当场变红。
   **同一个文件里已有现成的条件分支先例**：`validation_run.py:163-168`
   （`_run/view_manifest.json` 不存在 ⇒ `NOT_APPLICABLE("run predates the view manifest wire")`）。

**调查方的推荐 = 选项①（条件分支形态）。⛔ 但这是输入不是结论 —— 你独立判。**

---

## 4. ⭐ 你必须回答的设计问题（不止「选哪个」）

1. **选项定夺**：①/②/第三条路。**给理由，并说明你不选的那条会在什么情况下咬人。**
2. **条件分支的确切语义**：账本**存在**但取 proof **失败**时怎么办？
   （哈希对不上 / 六件套缺件 / `artifact_contract` 不是 B5 / 账本存在但那个 run 是 legacy v1。）
   ⛔ **fail-open 是本项目明令禁止的形态**（08-08 刚修过两处 fail-open）。
   请给出**每一种失败对应哪个 check_id、哪个 CheckLayer、哪个 CheckStatus**。
3. **Q4 那条独立出口要不要做**：现状 `validation_run.py:253` 的 `except Exception`
   把**任何**异常压成一句 `kernel build failed: {e}`，不区分「内核真坏了」和「proof 结构性拿不到」。
   调查方建议给后者一个独立 check_id。**你判要不要、叫什么、放哪。**
4. **legacy / 无账本 run 的语义**：它们今天**能过**这道门（几何 digest 签得出来）。
   改完之后它们应该 ①照旧能过 ②降级为 NOT_APPLICABLE ③还是别的？
   ⚠️ 注意这直接决定那 2 个 golden 基线红不红。
5. **`--intake-from` / `ValidationScope.DOWNSTREAM_ONLY` 路径**（`validation_run.py:94-97`）
   是否受影响？（它整段跳过 0–4。）
6. **锁怎么配**：调查方指出 **全部 5 个**调用 `validate_case` 的测试文件 **v3 覆盖为 0**
   ⇒ 这条路径从来没有测试拿 v3 产物喂过。
   最便宜的现成砖 = `tests/test_c2_b5_artifact_trust.py:39-66` 的 `_accepted(tmp_path)`
   （用 `StageRunner.record(...)` 造一份货真价实的 accepted attempt）。
   **请给出锁清单**，且每把锁必须满足本项目两条硬纪律：
   - **自证前提**：先断言「不加修法，这把锁在这个夹具上确实会红」，前提破了要**大声报错**，
     ⛔ 不许静默退化成空锁；
   - **正向锁不可缺**：本项目 08-10 刚吃过一次
     —— 一道门若**只有断言 `fail` 的测试、没有断言 `pass` 的测试**，
     它**恒红结构上不可观测**，且所有 fail 断言会因此全部永远绿。
7. **施工顺序**：能不能安全地分步落地？哪一步单独落地会产生危险的中间态？
   （你 08-09 审 F-9 时正是抓到「S3 单独落地会产生合法但错误的窗位」这类问题。）

---

## 5. ⛔ 硬约束（违反即 REWORK）

1. **不变量 #4（gt 铁律）**：`case_tests/test_baseline/gt/` 只对 gate② judge 与人开放，
   gate①/执行器**绝不 import**。⛔ 你也不要读它。
2. **不变量 #6（建筑复杂度可扩展性铁律）**：每个决策必须为未来复杂体量
   （**非方形 / 退台 / 挑空 / 中庭**）留路，**不得把「共用 footprint / 每层满铺 / 固定层高」
   这类当前简化假设烤死**。⚠️ 你 08-09 正是用这条否掉了 F-9 设计稿指定复用的帧参数。
3. **⛔ 删掉／推翻任何一段看起来多余的东西之前，先找出它在为哪份契约服务** ——
   这条**同样适用于一个标记、一个 flag、一句注释**，
   且**首选证据是引入它的那次提交说明，不是当前源码**。
   （这正是 F-9 设计稿 BLOCKER-3 的成因。调查方已就 `06d01a0` / `963d952` 做过这道功课，
   结论见调查报告 Q1 —— **你可以复核，但如果你要推翻某段现存设计，请自己再做一遍这道功课。**）
4. **⛔ 只读**：不改 `src/` / `tests/` / `scripts/`，不 `git add` / `commit` / 切分支。
   探针只在 `/tmp`。
5. **⛔ 不要跑全仓测试。**

---

## 6. 交付物

设计稿落 `AI_agent/proposals/f20_validate_case_v3_proof_design.md`：

1. **选项定夺 + 理由**（含「不选的那条会在什么情况下咬人」）。
2. **§4 七个问题逐条回答。**
3. **改动清单**：文件 / 函数 / 大致形状（**伪代码即可，⛔ 不要写成可直接粘贴的完整实现**）。
4. **锁清单**：每把锁「锁什么 / 夹具怎么来 / 自证前提怎么写 / 不加修法它红不红」。
5. **分步施工顺序 + 每步单独落地的危险中间态。**
6. **需用户拍板的点** —— ⚠️ **必须白话**：用户没有代码上下文，
   ⛔ 禁用代码变量名/内部代号当主语，四段讲（背景 / 问题 / 每个选项的后果 / 推荐+理由）。
7. **⛔ 你没能确定的部分**，明确列出。宁可留白，不要用推理填。

---

## 7. 合法退出口

以下任一情况请**停下如实上报**，不要硬出稿：

- 你认为这个岔口是**伪岔口**（两条实质等价，或有明显更好的第三条路）；
- 调查报告里某条「已实测」你复核下来是**错的**（请给反证，orchestrator 会重新裁决）；
- 本请求书某两条要求**互相冲突**；
- 你需要的信息不在白名单里。

**⛔ 派工方（orchestrator）自陈错误率 = 13/13** —— 迄今每一次执行席「停下上报」，
事后都证明是派工单的题错了。**顶住不照做、如实上报是期望行为，不是失败。**
