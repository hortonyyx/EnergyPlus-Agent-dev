# 返工单 r3 · 硬隔离脚手架批（r2 复审的两条 MINOR）

> 主控 Opus 5 · 2026-07-31
> 依据 = [r2 复审裁决书](../verdict/2026-07-31_isolation_scaffold_r2_verification.md)
> （APPROVE-WITH-CHANGES · 0 BLOCKER / 0 MAJOR / 2 MINOR / 3 NIT · R2-1…R2-6 六项全成立 · neuter 10/10 吻合）
>
> **本单是收口，不是推翻。** r2 的六项修复主控已逐条独立复验为真修好，全仓 1908 绿零回归。

---

## R3-1 · MINOR-2 · fail-closed 缺省把 F-4 的摩擦搬到了别处（**必须在复验轮跑识图前修**）

**实况（复审方实测）**：R2-1 裁定的「其余一切 key 一律按 path 角色无条件检查」是 fail-closed 缺省，
方向正确、相对 `f98d248` 不是回退、施工方照做无误。**但** `CONTENT_ROLE_KEYS` 至今只列了
Write/Edit 的四个文本体参数，**没有人枚举过识图子代理实际会用到的其余自由文本参数**。
后果：`TodoWrite` 的 `activeForm` 写 `grade line` 被拒、`Grep` 的 `pattern` 含 `..` 或 `~` 被拒 ——
这些在 r1 都是 ALLOW。

**为什么必须现在修**：本批存在的**唯一理由**就是消除 F-4 那类摩擦
（07-30 实况：第一轮 8 次拒绝里 7 次是与守卫搏斗、零安全价值、纯烧弱模型预算，
并把必交产物 `reading_summary.md` 卡到写不出来）。现在摩擦只是换了个参数位置。
**若照现状跑复验轮，会重演同一场搏斗，并再次污染「脚手架摩擦」这条归因候选。**

**死骨架**：
1. **按名枚举**识图子代理实际可用工具的自由文本参数，补进 `CONTENT_ROLE_KEYS`。
   至少含 `activeForm`、`description`、`pattern`（Grep）、`prompt`、`query`、`command` 之外的说明类参数。
   **枚举依据不许靠猜** —— 去看 `_write_settings` 放行了哪些工具、
   以及 07-30 的 `access_log.jsonl` 里实际出现过哪些 `tool_name`/参数名，两者取并集。
2. **缺省仍然是 fail-closed**（未知 key 按 path 处理），这条 R2-1 的硬要求**不许动**。
   本项只是把「已知的自由文本参数」显式移进豁免名单，不是改缺省方向。
3. `Bash` 的 `command` **仍走全串严格检查**，不许进豁免名单。

**必须新增的锁**：
- 可用性正例：**非 Write/Edit 工具**（至少 TodoWrite 与 Grep 各一条）携带
  `grade line` / `..` / `~` 的自由文本参数 ⇒ **ALLOW**。
- 缺省仍 fail-closed 的负锁：**未知 key** 携带越界路径 ⇒ 仍 **DENY**（钉住 R2-1 不被本项削弱）。
- 路径参数不受影响的负锁：`file_path="case_tests"` ⇒ 仍 **DENY**。

## R3-2 · MINOR-1 · wrapper 与 guard 的可写根语义不一致

`scripts/tool_scripts/cv_probe.py` 侧（staging 内为 `tools/run_cv_probe.py`）的 `_writable_root`
仍用 `resolve(strict=False)`，未跟 R2-3 给 guard 钉死的「可写根必须是 staging 内的真实目录、
resolve 后仍等于自身字面路径」语义。

生产不可达（guard 先 fail-closed，子代理也造不出 symlink），故复审方评 MINOR。
**但返工单 r2 的 R2-2 骨架第 2 条明写「wrapper 侧做同一约束，避免 guard/wrapper 策略差」，该条只闭了一半。**

**死骨架**：把 R2-3 的可写根钉死语义**抽成一处共享实现**，guard 与 wrapper 各自调用同一份，
消除两处策略漂移的可能。
**必须新增的锁**：预置 `out -> tools` 后**绕过 hook 直调 wrapper** ⇒ 拒绝执行、`tools/**` 零新增。

## R3-3 · 三条 NIT（顺手清，不阻断）

① `test_guard_r2_param_role_is_total_over_keys` 首条断言是同义反复（承重的是第二个循环，
且它挂在生产码自称「非权威」的 `PATH_ROLE_KEYS` 上）⇒ 改成真承重断言或删掉首条。
② `__pycache__` 豁免不限深度（r2 已授权，登记即可）。
③ `evaluate()` 里逐 target 循环按构造不可达 ⇒ 清死码。

---

## 纪律

1. 只碰 `src/agent/execution/isolation_templates/**`、`scripts/tool_scripts/cv_probe.py`
   （及 `isolation.py` 若共享实现需要）及其测试。
   **不碰** `src/agent/judge/**`（已 CLOSED，须字节稳定）、`case_tests/test_baseline/gt/**`、`AI_agent/CLAUDE.md`。
2. 不许削弱既有断言；不许动 R2-1 的 fail-closed 缺省方向。
3. 每把新锁给 neuter 自查（定点破坏 → 真跑 → 报实际变红的测试名）。
   **本批已抓到两把假锁**（夹具形状、常量比对），对自己的新锁用同样的怀疑。
4. 基线 = **1908 passed / 10 xfailed / 0 failed**（主控已独立复核）。
   中间轮用 `scripts/tool_scripts/affected_tests.py` 算子集，交付前跑一次全仓。
5. 追加「返工 r3」节到 `AI_agent/logs/reviews/execution/2026-07-31_isolation_scaffold_glm.md`。
6. 骨架有错 ⇒ 停下上报。

## 跑测纪律（转写进复验轮）

复审方另提一条运行纪律，主控采纳并已写进复验轮 README：
**复验轮跑完必须读 `access_log.jsonl` 的拒绝计数**，否则「脚手架摩擦」这条归因候选下轮依旧无法证伪。
