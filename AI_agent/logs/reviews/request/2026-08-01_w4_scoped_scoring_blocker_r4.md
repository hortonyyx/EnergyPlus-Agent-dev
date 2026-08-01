# 返工单 r4 · ⛔BLOCKER —— 减卷判卷跑不通（W4 的功能点实际未达成）

- **日期**：2026-08-01 · **座位**：GPT 侧 terra（`gpt-5.6-terra`，effort=high）· 通道 = `codex exec` CLI 后台
- **发现方式**：**W5 第一次真实使用减卷判卷**（sm24 声明 `[1f_view, South_view]`，两抽识图产物已落盘）
- **性质**：**BLOCKER**——W4 的判卷侧功能点「减卷之后照常出分」**从未真正达成**，
  之前三道关（施工自查 / 主控轻门 / GLM 对抗审）全部漏过，原因见 §3。

---

## 1. 现象（主控实跑，可复现）

两个 run 的 `0_reading/attempts/001/score_vs_gt.json` **payload 均为**：

```json
{"kind": "rejected", "error_code": "score_view_binding_invalid", "gate_id": "scoring.view_bindings"}
```

⇒ **减卷之后出不了分**。判卷器没有崩（符合 R-4「只许说 unsupported 不许崩」），但**功能不可用**。

## 2. 根因（主控已定位并活体复现，非推测）

[`src/agent/judge/score_inputs.py:141`](../../../../src/agent/judge/score_inputs.py#L141)
`validate_score_view_bindings_against_gt` 调用下层校验时**没有把考试范围传下去**：

```python
validate_score_view_bindings(bindings=bindings, base=base)   # ← 缺 input_ids=
```

于是 `required` = base manifest 里**全部五张** plan/elevation，`declared` = 收窄后的**两张**，
集合不等 ⇒ raise。**主控活体复现的 context 逐字**：

```
{'required': ['1f_view','East_view','North_view','South_view','West_view'],
 'declared': ['1f_view','South_view']}
```

**`input_ids` 这个参数本来就存在**（同文件 `materialize_va_elevation_bindings`，:357 就在用），
**只是没接到 GT 侧这条路上**。

**⚠️ 修完第一处会立刻撞第二处，一并处理，别只修一处**：
[`opening_claim_score.py:234`](../../../../src/agent/judge/opening_claim_score.py#L234)
逐个遍历 GT opening 的 `source_refs`，**任一 ref 指向的 view 没有 binding 就 raise**。
减卷后 East/North/West 没有 binding ⇒ 凡是 `source_refs` 提到它们的 opening 必然触发。

## 3. 为什么三道关都没拦住（必须记，这是本轮最重要的治理数据）

**terra 补的 L8 锁是假绿**：`test_typed_reading_scorer_consumes_only_frozen_exam_scope_bindings`
断言的是 `artifacts["score_vs_gt"] is not None` —— 而**判卷器「拒绝」时产出的也是一个非 None 的侧车**
⇒ **锁绿着，判卷其实是拒的**。

GLM 的 C 组与主控轻门都验了**机制**（冻结 / 防漂移 / 消费侧收窄 / 六道守卫真锁），
**但没有任何一方真的跑一次「带范围声明的完整判卷」并检查它出了分**。
⇒ 与本批已立的「**探针 ≠ 锁**」同族，再加一条：**「非 None」不是「成功」**。

---

## 4. 要求的行为（全参数表，别留缺省分支）

| # | 情形 | 要求 |
|---|---|---|
| A | **未声明范围** | 与今天**逐字节相同**。这条是硬底线 |
| B | 声明了范围，**GT 侧信任根校验** | 必须按**范围内子集**校验，**不是**全清单。范围内每一张的既有 GT 侧检查（floor / facade / source-ref 信任根）**一条不许少、不许放松** |
| C | 声明了范围，**GT opening 的 `source_refs` 指向范围外的 view** | **跳过该 ref，不得 raise**。判据见下 |
| D | 声明了范围，**某 opening 的 `source_refs` 一条都不在范围内** | 该 opening **整个移出本轮分母**，并**显式记录**为「不在本轮考试范围」+ 声明来源（与视图级 `not_applicable` 同构）。**不得静默丢弃、不得记成 miss** |
| E | 声明了范围，**opening 至少有一条 ref 在范围内** | **照常计分**，用在范围内的证据 |

**判据的理由（主控裁定，不下放）**：读图器**根本没见过**范围外那些图，
把只在那些图上才看得见的 opening 算成「漏画」＝**冤枉**；
但只要它有任何一条证据落在范围内，就**照常考**——**减少题量不等于放水**。

**⛔ 不许**：为了让它跑通而放宽任何**范围内**的检查；不许改 GT；不许改签名件；三个身份哈希仍须逐字不变。

---

## 5. 锁（本单的另一半，与修复同等重要）

1. **把 L8 那条假绿锁修成真锁**：断言判卷**成功出分**（`payload["kind"]` 不是 `rejected`
   / 有真实计分结果），**而不是**断言 `is not None`。
   **自查方式**：把你的修复回退掉 ⇒ 该锁必须变红（现在它是绿的，这就是问题）。
2. **补 C/D/E 三格各一条锁**，每条都要 neuter 验真（摘掉对应分支 ⇒ 恰好那条红）。
3. **补一条 A 格锁**（未声明范围时 GT 侧校验行为不变）。

## 6. 验收（缺一不算交付）

1. **真实端到端证据**：用仓库里现成的两个 run
   `case_tests/e2e_tests/sm24_anchor/run_2026-08-01_haiku_w5_scoped_{d1,d2}`
   （**识图产物已落盘、已 merge、已过 gate①；不要重跑识图，只重跑判卷**）
   跑 `run_stage.py --run-profile regression --capability-profile orthogonal_polygon flow sm24_anchor <run> --to 0_reading --judge stop`，
   **给出两个 run 的 `score_vs_gt.json` 里 `payload["kind"]` 不再是 `rejected` 的实际输出**。
2. **分母确实缩小了**：给出减卷后的分母构成，证明它只含 `1f_view` + `South_view`
   （派工单原 §4 验收第 3 条，**一直没有被真正演示过**）。
3. **neuter 自查表**：§5 每条锁——摘掉什么 → 哪个测试函数红 → 有无连带。
4. **全仓跑一次**（`-n auto`，不加 `-m`）：**≥ 2047 绿 + 10 xfail + 0 红**。
5. 三个身份哈希逐字不变。

## 7. 交付

- 执行日志新一节「W4 减卷判卷 BLOCKER 修复 r4」。
- 一个 commit（`<月.日>_<英文标签>`，body 三段）。**不许 push。**
- **欠规格边界一律停下上报。** 撞 `.git/index.lock` → 停下上报，不要自行删锁。
- 回主对话只给简报：两个 run 的判卷结果 / 分母构成 / neuter 表 / 全仓绿数 / review-ask。
