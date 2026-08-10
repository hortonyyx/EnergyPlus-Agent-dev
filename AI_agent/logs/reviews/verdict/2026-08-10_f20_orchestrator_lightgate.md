# orchestrator 轻门 · F-20 施工（Claude 侧 Sonnet）

- **日期**：2026-08-10 · **裁决人**：orchestrator（Opus）
- **被审对象**：工作树未提交改动（4 文件 / +698 −65）+
  [执行日志](../execution/2026-08-10_f20_validate_case_v3_proof_claude.md)
- **裁决**：**PASS-WITH-CHANGES** — **0 BLOCKER / 1 MAJOR / 0 MINOR**
  ⇒ **修法本身通过（那堵墙确已倒）**，但 **MAJOR 必须补掉**才能交跨家族复核。

---

## 1. 以 `git diff` 为准的核实（⛔ 未采信施工席自述）

| 项 | 结果 |
|---|---|
| 实际改动 | `validation_run.py` +272 · `test_c2_b5_artifact_trust.py` +472 · `test_check_parity.py` +7 · `test_run_pipeline_self_checks.py` ±12 —— **与自述一致** |
| ⛔ 禁令：不许改 `stage_runner.py`（选项②） | ✅ 未出现在 diff 中 |
| ⛔ 禁令：不许 fail-open | ✅ 逐分支读过：V2 侧任何 `ValueError` ⇒ `geom=None` + `FAIL`，**无一处回退 stage-root**；未知异常 ⇒ `ERROR` |
| ⛔ 禁令：新检查不许进 `2_modelling` 报告 | ✅ `_TRUST_CHECK_ID` 只在 `crep`（= `res.reports["1_correction"]`）上 `add` |
| **NIT-1**（manifest 存在但读不出来） | ✅ **已实现**：单独 `except ValueError` ⇒ `FAIL`，注释逐字写明「must NOT be silently treated as "no manifest"（那会 fail-open 到不受信的便利副本）」 |
| **NIT-2**（零窗 v3） | ✅ **已验且未触发退出口**：`_bundle()` 本就有 `include_window`，L1 已参数化 `[with-window]/[zero-window]` |
| ⚠️ **改了一个既有测试**（最可疑处，逐行读过） | ✅ **改法正确**：用 `.pop(...)` **并断言弹出值必须是 `not_applicable`**，不是无条件排除；其余检查照旧逐项比对。若该检查将来变状态，该测试仍会红 |

## 2. 独立全量（orchestrator 自跑）

```
2357 passed, 10 xfailed, 209 warnings in 464.09s (0:07:44)
```

= 基线 **2345 + 12**，**零回归**，与施工席逐字一致。

## 3. 真实产物独立复现（F-5 纪律）

`run_2026-08-09_f18_e2e_verify`（**全项目唯一一份 v3 产物**）在 `/tmp` 只读副本上：

```
trust 行            : PASS
2_modelling         : 无 fail/error（此前是 kernel build failed）
geometry_digest 非空: True
approve_geometry    : 签发成功
```

⇒ **那堵墙确已倒。战线可从几何确认门继续往下推。**

---

## 4. ⭐ 换方向 neuter（施工席测了 7 个方向，orchestrator 换了 2 个它没测的）

**⛔ 第一次尝试作废并如实记录**：orchestrator 首个 `/tmp` 副本只拷了 `src tests pyproject.toml`、
**漏了 `data/`** ⇒ `kernel.pairing_gate` 因找不到 `Energy+.idd` 报环境错 ⇒ 得到「10 条红」的**假结果**。
重建副本 + **先立零变异干净基线（58 passed）** 后重跑。
⇒ 兑现「neuter 必须先确认改动真的落下去了」与「换台机器还成立吗」两条纪律。

### 方向①：把三态塌回二值（复现 **sol 抓到的第一发雷**）

变异 = `if manifest is None or not isinstance(manifest, RunManifestV2):` → `if manifest is None:`
（即让 V1 账本落进 V2 分支）

```
结果：恰好 L6 一条红、零连带（1 failed, 57 passed）
```

✅ **sol 的第一发雷被精确锁住。**

### 方向②：把 trust 行挪进 kernel report（复现 **sol 抓到的第二发雷**）⇒ ⛔ **抓到 MAJOR**

变异 = 在 `res.reports["2_modelling"] = krep` 之前把同一条 trust 行也 `krep.add(...)`
（模拟一次「重构时挪了位置」）

```
结果：8 把 F-20 锁一把没红。只有 test_check_parity 红
     （且是因为新 check_id 出现在未豁免的 stage ⇒ 间接命中，不是在守这条性质）
```

---

## 5. ⛔ MAJOR-1：L6 的 digest 断言是**自比自**，不是跟修前冻结值比

设计稿 §4 的 L6 **逐字要求**：

> 旧 digest 用**施工前冻结的** fixture 值（或等价 frozen report）对比，
> **不在修后临时「算一个期望值」**。

**实现做的正是设计明令禁止的那件事**（`tests/test_c2_b5_artifact_trust.py`，L6 内）：

```python
assert res_a2.geometry_digest == res_a.geometry_digest  # stable across repeat runs
```

`res_a` 与 `res_a2` 是**同一份代码**的两次调用 ⇒ digest 公式一变，两边一起变、断言照样绿。

**这正是 2026-08-07 记下的「恒等锁 ≠ 正确性锁」** ——
恒等锁证明「两次算法一致」，**不证明这套算法与历史一致**。

**orchestrator 补充查实**：`grep` 全 `tests/`，**没有任何一处把 `geometry_digest` 钉在字面值上**
⇒ **「历史几何批准不失效」这条性质，全仓零锁**。

⚠️ **公平地说**：施工席**确实验过**这条性质（验收项④用 `git archive` 取修前只读快照
与工作树逐字节对比，两个 golden 基线的 `blocked`/`blocking_summary`/`digest` 全同）——
**那是一次有效的人工验证**。问题是**它没有变成锁**：
⇒ **今天是对的，但没有任何东西守着它明天还对。**

**要求**：补一把把 golden 基线 digest **钉在修前实测字面值**上的锁
（或等价的 frozen report fixture）。⛔ 不许再用「同一版本跑两次相等」。

---

## 6. 施工席自陈的三条未完成（照单收下，⛔ 不得当成已解决）

1. neuter② 暴露的锁粒度缺口（L4/L5/L6/L7/NIT-1 对「trust BLOCK 后是否越权碰 stage-root」不敏感）
   —— 施工席判断 L2/L3/L8 已独立覆盖该防线、不需重复，**如实登记未擅自定论**。orchestrator 同意，**不追加**。
2. 未重新普查全部 22 份 V2 账本的 stage-root/accepted 一致性（只对派工单点名的 4 个做 targeted replay）
   —— orchestrator 08-10 已机械测过那 4 个（DIFF=0），**其余 18 个无 accepted 记录、本就不适用**。**结清。**
3. F-21 在验收③中被亲眼撞见（签发了一个 `blocked=True` run 的检查点）**且严格未碰** —— ✅ 守住了边界。
   与 GPT 侧 terra 当日独立调查结论一致（**非已证实缺陷，留档不修**）。

---

## 7. ⭐ 登记两条「施工席做得比派工单更好」

1. **主动补掉一个自己撞出的连带缺口**：`test_run_pipeline_self_checks.py` 有一份**独立的**
   inline-vs-`validate_case` 比对逻辑，不经豁免表 ⇒ 加新检查后会红。它**修了而不是绕过**，
   且修法是「pop 并断言值」而非无条件排除。**派工单没点到这个文件。**
2. **neuter⑤ 自己发现了一个真实盲区**：NIT-1 的 fail-open 变异在 v3 夹具下
   **被另一条独立防线（v3-under-legacy 检测）掩盖、红不了**
   ⇒ 它补了 legacy-schema 变体才精确捕获。**这正是「锁看起来在守其实没守」那一族，它自己抓到了。**

---

## 8. 裁决

**PASS-WITH-CHANGES**：生产码修法**通过**（三条禁令全守、两条 NIT 全落实、真实产物证实解开、零回归）。
**⛔ MAJOR-1 必须补掉**（L6 冻结 digest 锁）后方可交跨家族复核。

**⇒ 下一步**（用户 08-10 定：**新活优先走 GPT 额度**）：
① 补锁派 **GPT 侧 terra**；② 补完后整批交 **GPT 侧 sol** 跨家族复核
（Claude 侧施工 ⇒ 审阶梯落 GPT 侧，**基本不吃 Opus 额度**，正是协作规约推荐的省额度形态）。
