# orchestrator 轻门 · F-7 接口修法（`a174fe8` → merge `86ab24b`）—— **PASS**

- **日期**：2026-08-05
- **施工席**：Claude 侧 Sonnet 子代理（独立 worktree `f7-source-ids-sonnet`）
  · 执行日志 [`../execution/2026-08-05_f7_source_ids_sonnet.md`](../execution/2026-08-05_f7_source_ids_sonnet.md)
- **派工单**：[`../request/2026-08-05_f7_source_ids_dispatch_sonnet.md`](../request/2026-08-05_f7_source_ids_dispatch_sonnet.md)
- **前序调查**：[`../execution/2026-08-05_f7_claim_links_interface_gap_glm.md`](../execution/2026-08-05_f7_claim_links_interface_gap_glm.md)（GLM）
- **判定**：**PASS**（下一道是 sol 跨家族对抗审，与 F-2c 合并送审）

> **轻门 = 主控独立全量 + 独立 neuter + 抽查 diff + 裁决，⛔ 不采信施工方自述的任何数字。**
> **⚠️ 提交由 orchestrator 代做**（施工席在收尾前撞 5h 额度窗，改动全在工作树未提交；
> §5#8 明列 `git add`/`commit` 属 orchestrator 亲手可做的事）。

---

## 1. 独立全量（orchestrator 亲跑，零过滤）

```
2212 passed, 10 xfailed, 209 warnings in 462.15s
```

- 命令：`python -m pytest -n 6 -q`（**⛔ 未加 `-m` 过滤**）。
- 合并前 `a8c367a`（F-2c 收口后）= **2197 / 10 / 0** ⇒ **净增 15 = F-7 的 15 条新锁，零回归、xfail 持平。**

## 2. ⭐ 合并正确性专项核验（本轮最容易静默出错的一步）

F-2c（GLM，主树）与 F-7（Sonnet，独立 worktree 基于 `3310ed3`）**改过同一个文件的同一个函数**
（`window_sources.py` 的 `verify_reading_stage_root_against_accepted_attempt`）。
git **自动合并成功**，但 F-7 把 `category` 变成了 `WindowResolverInputError` 的**必填关键字**
⇒ **任何一个 raise 点漏填即运行时 `TypeError`**，而自动合并不会察觉。

**orchestrator 独立扫描全部 raise 点**（按括号配平提取每个调用的完整实参）：

```
raises without category: 0
```

`src/agent/correction/{finalize,parse}.py` 的 4 处 raise 点亦逐一核过，全部带 `category`。
**⇒ 自动合并成功 ≠ 语义正确；本项目应把「合并后必须核对跨席位共改点」列为常规动作。**

## 3. 独立 neuter —— **三个方向，各自绑住各自的锁**

在 `--detach 86ab24b` 的一次性 worktree 里做（仓库工作树零污染）。基线：`15 passed`。

| # | 手法 | 结果 |
|---|---|---|
| A | `_claim_links` 里把 `locator = _translate_observation_reference(...)` 改回 `locator = reference`（**禁用翻译**）| **8 红 / 7 绿** —— 恰好翻译相关的 8 条（正例 + 4 个畸形参数化 + 未知图名 + 未知编号 + 归档集成），其余 7 条（向后兼容 locator / prompt 清单 ×3 / input_integrity 硬崩 / 两条分类表抽查）保持绿 |
| B | 分类**一律当成 `model_draw_error`**（该硬崩的不崩了）| **只红** `test_f7_input_integrity_error_still_hard_crashes_no_resample` |
| C | 分类**一律当成 `input_integrity_error`**（该归档重抽的崩了）| **只红** `test_f7_model_draw_error_is_archived_as_a_failed_attempt_and_blind_resampled` |

**⭐ B/C 是本次最关键的一格**：分类是本批**新加的判断**，
按 08-04 定的纪律「**neuter 变红只证明实现被调用了，不证明判据有分辨力**」，
判断类必须**两个方向各打一次**。结果 = **每个方向恰好红它自己那条锁、不误伤另一条**
⇒ 分类真有分辨力，不是一条陪绑。

## 4. 抽查 diff

| 检查项 | 结果 |
|---|---|
| `_claim_links` 的严格校验是否被放宽 | ✅ **一条未放宽**。原有 `positive_claims` / `potentially_observable_claims` / `permitted` / existence 唯一性 全部原样保留，只是各自补了 `category` |
| 翻译是否是**唯一**入口 | ✅ `_translate_observation_reference` 是唯一翻译点；已是合法 `src:<64hex>` 的原样放行（向后兼容既有夹具）|
| 是否**静默猜**歧义引用 | ✅ 无。畸形 / 未知图名 / 未知编号**各抛具名错误**（`observation_reference_ambiguous` / `_view_unknown` / `_observation_unknown`）|
| prompt 清单是否与执法侧同源（机械导出）| ✅ `derive_observation_reference_catalog` 直接读 `_catalog(...)` 的 rows —— **与 `_translate_observation_reference` 校验的是同一份**，构造上不可能漂移 |
| prompt 是否泄露 locator | ✅ `format_observation_reference_catalog` 只输出 `<view>/<id>` + 允许的 claim，**永不输出 `src:` 或 64-hex**；prompt 正文并明令「不许写 `src:` 前缀的哈希、你算不出也不要试」|
| 分类是否落在错误类型/抛出点 | ✅ `category` 是 `WindowResolverInputError` 的**必填关键字** ⇒ **漏填即 `TypeError`，不会静默落桶**；消费侧 `run_stage.py:412/423` 只读 `exc.category`，**未匹配任何消息文字** |
| 是否有兜底默认 | ✅ 无（必填关键字即杜绝）|
| 是否留旧签名静默回退 | ⚠️ 见 §6 结转一条 |

## 5. ⭐ 真链路证据（比单测锁更硬 —— 这是本单的核心验收条件）

跑测 `run_2026-08-05_f7_verify_sonnet`（07-07 sm21 识图产物 · `exploratory` · 标准 `flow` SOP）：

- **attempt 001**：`correction.window_source_reference **fail**` ——
  `source_claim_undeclared: {'window_id': 'win_1F_N_1', 'claim': 'appearance'}`
  （模型把 `appearance` 挂到**平面**来源上；平面只允许 `existence/host/along/width`）
  ⇒ **被归档为失败 attempt 并盲重抽，不是硬崩** ⇒ **F-7 的新分类在真链路上生效。**
- **重抽那次**：**完全通过 `_claim_links`**，一路走到
  `finalize → apply_deterministic_core → _apply_envelope_reconcile → apply_v3_envelope_transaction
  → _dry_resolve_current_ring → resolve_window_hosts` 才崩
  ⇒ **F-7 的死点确已越过。**

**⇒ 派工单 §3.2 要求的「出 accepted attempt」未达成，但原因是下一道墙（F-9 候选），不归本单。**
本批的定义就是「测试绿、真链路崩」，因此真链路上的**推进证据**即本单的有效验收。

## 6. 结转 / 留给 sol 审的点

1. **`build_observation_reference_catalog_from_run` 在文件缺失时返回 `None`（清单不注入）**，
   docstring 自陈「advisory only，执法侧独立重算，缺清单只削弱引导、不削弱契约」——
   **该辩解在正确性上成立，但可用性上存疑**：清单缺失 ⇒ 模型无引导 ⇒ 必然填错 ⇒ 归档重抽 ⇒ **可能空转烧完重抽预算**。
   **请 sol 重点打这条**（是否该在 v3 目标下把「清单可导出」升为前置条件）。
2. **F-9 候选**：`window_host.py:877` `WindowHostResolutionError(tuple(conflicts))`
   —— **`conflicts` 内容从未被打印或落盘**，整个 traceback 零诊断，**与 F-3「报一句看不懂的话」同型**；
   且 `WindowHostResolutionError` 是**另一个异常类**，不在 F-7 分类的覆盖面里（当前=硬崩）。
   只读调查已派 GLM（[派工单](../request/2026-08-05_f9_window_host_investigation_dispatch_glm.md)），**修法方向待用户拍板**。
3. **F-8**（干净检出跑全仓必红 5 条，`.gitignore` 挡掉 619 个含测试活输入的文件）—— 独立缺陷，已登记，未排期。
