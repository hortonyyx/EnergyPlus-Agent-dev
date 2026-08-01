# 返工单 r2 · W4 —— 「门是真的、锁是缺的」：考试范围的五道守卫无回归锁

- **日期**：2026-08-01
- **座位**：GPT 侧 terra（`gpt-5.6-terra`，effort=high）· 通道 = `codex exec` CLI 后台
- **前序**：[返工单 r1](2026-08-01_w4_exam_scope_rework_r1.md) → 交付 `3b7d930`
- **r1 结论 = 缺陷已修，主控独立验证通过**：硬编码路径 0 命中 · `--base-dir` 可用 ·
  未声明 = 默认行为不变 · **主控独立全量 = 2042 passed / 10 xfailed / 0 failed**（与你的数字逐字一致）。
  **r1 不需要再动。本单只补锁。**

---

## 1. 主控轻门实测（在 `/tmp` 克隆里做的 neuter，不动仓库）

对 `resolve_frozen_reading_exam_scope` 的每一道守卫逐个摘除，跑
`tests/{test_view_manifest_generator,test_isolation,test_c2_b4b_phase_d,test_reading_typed_scoring_slice1}.py`
（基线 277 passed）：

| # | 摘掉的守卫 | 结果 | 判定 |
|---|---|---|---|
| N1 | 冻结件在、但 `run_config.yaml` 的声明没了 | **277 passed** | ⛔ **无锁** |
| N2 | 声明在、但冻结件不见了 | 1 failed | ✅ 有锁（你 r1 加的那条） |
| N4 | 冻结件绑的是**另一份** base manifest | **277 passed** | ⛔ **无锁**（且这是 r1 新加的检查） |
| N5 | `declaration_sha256` 不一致 | **277 passed** | ⚠️ 见 §3，**这条是冗余检查、不是缺锁** |
| N6 | `content_sha256` 不一致 | **277 passed** | ⛔ **无独立锁**（被 N5 互相遮蔽） |
| N8 | 判卷侧**根本不按 scope 收窄 bindings** | **277 passed** | ⛔⛔ **无锁 —— 这是 W4 判卷侧的全部功能点** |

**N5 + N6 一起摘 → 1 failed** ⇒ 现有那条断言（`test_run_level_exam_scope_is_frozen_without_changing_case_manifest`
里的 `assert not verify_view_manifest(...).ok`）只锁住了「两条至少还剩一条」，**任一条单独失效都测不出来**。

**⚠️ 最重的是 N8**：把判卷侧收窄 bindings 的那三行整个短路掉，**全子集依然全绿**。
你 r1 给的 C 格证据（临时 run 里手工调真 scorer，拿到 `['1f_view','South_view']`）是**探针不是锁** ——
它证明了当时能跑对，但不会在有人改坏时变红。**W5 就要靠这条功能拿数**，它必须有锁。

**这不是你 r1 造成的**：N1/N5/N6 在 r1 之前就以等价形式待在 `verify_view_manifest` 里、同样无锁；
N8 来自 W4 原始提交 `2d2137e`；只有 N4 是 r1 新加的。**如实登记，本单是补，不是罚。**

---

## 2. 本单唯一目标：把上表变成「摘掉即红」

**只加锁，不改生产语义。** 除 §3 那一条允许的删除外，`src/` 与 `scripts/` 下的行为**逐字不变**。

要补的锁（每条都必须由**你自己**用 neuter 验过是真绑）：

| 锁 | 必须锁住的守卫 | 构造要点 |
|---|---|---|
| **L1** | 冻结件在、声明被删 | provision 出冻结件后，把 `run_config.yaml` 里的 `reading_exam_scope` 段删掉，断言 resolver `raises` 且理由指明「声明缺失」 |
| **L4** | 冻结件绑到另一份 base manifest | 用**另一个 case**（或另一份合法 manifest）产出的 base 去调 resolver，断言 `raises` 且理由指明「绑定了不同的 base view manifest」 |
| **L6** | `content_sha256` 不一致 | 见 §3：删掉 N5 之后，既有那条断言就变成 N6 的独立锁；**你仍须 neuter 证明这一点**，不能只靠推理 |
| **L7** | 冻结件损坏 | 往冻结件里写非法 JSON / 缺字段，断言 `raises` 且理由指明「corrupt」。（这条我没 neuter，**你先查它有没有锁**，有就注明、没有就补） |
| **L8** | **判卷侧按 scope 收窄 bindings** | 走 `_grade_typed_attempt_artifacts`（或其之上的真实入口）**真跑一次**有 scope 的 `0_reading` 判卷，断言消费到的 bindings **恰好**是声明的那两个 `input_id`；**短路掉收窄那三行必须让这条红**。夹具可复用你 r1 建临时 scoped run 的那套做法，但要落成**仓库内的测试**，不是临时脚本 |

---

## 3. 允许（并且推荐）的一处删除：N5 是冗余检查

`content_sha256` 是**整个 payload（含 `declaration_sha256`）**的哈希，且 `ReadingExamScope`
的 `model_validator` 会强制 `content_sha256` 与自身 payload 一致
⇒ **`content_sha256` 相等 ⟺ payload 相等 ⟹ `declaration_sha256` 必然相等**。
即 N6 完全包含 N5，**N5 不可能成为唯一触发原因**，也因此**不可能为它构造独立锁**。

⇒ **推荐处置 = 删掉 N5 那三行**（删完 N6 就自动获得独立锁，L6 顺带成立）。

**⚠️ 你有权保留它**，但保留就必须：① 在代码里写明「本检查被 `content_sha256` 完全包含、
仅作纵深防御」；② **不得**在交付说明里声称它有锁。**不许既保留、又当成一道独立的门来报。**

若你的推导与我不同（例如你能构造出「declaration_sha256 不等而 content_sha256 相等」的合法输入），
**停下上报、给出那个输入**，不要自行按任一方向处置。

---

## 4. 硬边界

1. **不许改任何既有断言与夹具**去迁就实现；既有测试逐字节不动（新增除外）。
2. **不动 GT / `case_tests/test_baseline/gt/**` / 签名件 / case 元数据**；三个身份哈希仍须逐字不变。
3. **不许放宽任何守卫**来让锁好写。锁要迁就门，不是门迁就锁。
4. **neuter 只在 `/tmp` 副本里做**，做完恢复；**不许把 neuter 痕迹留进仓库**。
5. W1（`15cfcb8`）/ W3（`0763164`）/ r1（`3b7d930`）的生产码不许再动。

---

## 5. 验收（缺一不算交付）

1. **neuter 自查表**：上表每条锁 —— 「摘掉哪几行 → 哪一条测试变红（精确到测试函数名）→ 是否有连带误伤」。
   **必须是真跑的输出**，不接受推理。**若某条锁摘掉后没红，如实写「假锁」并修到真绑**。
2. **N8 那条要额外证明不是假锁**：短路收窄三行后，**只有**你新加的那条红（其余不受影响）。
3. **全仓跑一次**（`python -m pytest -n auto`，不加 `-m`）：**≥ 2042 绿 + 10 xfail + 0 红**。
4. 三个身份哈希逐字不变的证据。

## 6. 交付要求

- 执行日志续写新一节「W4 返工 r2（补锁）」到
  [`AI_agent/logs/reviews/execution/2026-08-01_reading_unsupervised_enablement_terra.md`](../execution/2026-08-01_reading_unsupervised_enablement_terra.md)。
- 一个 commit，message 仿 `<月.日>_<英文标签>`，body 含 ①改动 ②为何此刻 ③影响。**不许 push。**
- **欠规格边界一律停下上报，不得自行降级为假设。**
- 回主对话只给简报：neuter 自查表结论 / 全仓绿数 / 改了哪几个文件 / **review-ask 段**。
- 撞 `.git/index.lock` → **停下上报，不要自行删锁**。主控本轮只跑只读命令。
