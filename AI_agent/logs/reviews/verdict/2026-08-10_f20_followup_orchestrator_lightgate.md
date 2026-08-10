# orchestrator 轻门 · F-20 交叉审返工（GPT 侧 terra）

- **日期**：2026-08-10 · **裁决人**：orchestrator（Opus）
- **被审对象**：sol 三条 findings 的返工（`validation_run.py` +21 · `test_c2_b5_artifact_trust.py` +90 −5）
- **裁决**：**PASS** — 0 BLOCKER / 0 MAJOR / 0 MINOR

---

## 1. ⭐ MAJOR-1（本批最贵的一条）—— orchestrator 独立复现，**锁真绑**

**变异**：把 `_resolve_correction_source` **V2 加载器侧**（`validation_run.py:202` 那个
`except ValueError`）由「返回 `FAIL`」改成回退 `_resolve_legacy_stage_root(...)`
= sol 指出的经典 fail-open。

```
恰好 1 条红、零连带：
  test_f20_major1_v2_rejection_never_falls_back_to_buildable_legacy_stage_root
（1 failed, 71 passed, 8 xfailed）
```

**对照**：返工前同一变异下 **69 项定向测试全绿、零锁捕获**（orchestrator 已实测）。
⇒ **缺陷已被真正锁住。**

### ⛔ orchestrator 第一次 neuter 打错了块（如实登记）

首次用正则匹配「第一个带 `trust_status=CheckStatus.FAIL` 的 `except ValueError` 块」
⇒ 命中的是 **NIT-1 那个（manifest 读不出来）**，不是 V2 加载器那个
⇒ 红的是 3 条 NIT-1 锁，我差点据此误判。改用**行号精确定位**后才打中目标。

⭐ **副产品**：那次打错反而证明了**另一个 fail-open 位点也确实被守着**
（manifest 不可解析 ⇒ 3 条锁红）。⇒ **两个 fail-open 位点现在都有锁。**

⇒ 兑现纪律「neuter 必须先确认改动真的落到目标上」——
本轮我在同一条纪律上栽了两次（前一次是副本漏拷 `data/`）。

## 2. MINOR-1 —— 生产码改动范围核实

`git diff` 逐行读过：`src/` 的改动**严格只有异常映射**两处 ——
① manifest dispatcher 的意外异常 ⇒ `ERROR` trust 行；
② legacy stage-root parser：载荷型 `ValueError` ⇒ `FAIL`、意外型 ⇒ `ERROR`。
**⛔ 未触碰** `stage_runner.py` / `build_geometry` / 加载器合同 / `DOWNSTREAM_ONLY` early return。
与设计稿状态表「已知载荷型 ⇒ FAIL、意外型 ⇒ ERROR」一致。

terra 自陈两把新锁各自 neuter「恰好 1 条红、无连带」（映射移除方向）。

## 3. NIT-1

无信息断言已清理（同内存对象字段自比 + 三条被前置断言逻辑蕴含的冗余断言）。

## 4. 独立全量

```
2361 passed / 10 xfailed / 0 failed   （rc = 0）
```

= 2358 + 3（MAJOR-1 一把 + MINOR-1 两把），**零回归**，与 terra 逐字一致。

---

## 5. ⭐ 本批最该记住的一条 —— **遮蔽模式必须横向推广，不能只在发现它的那一处修**

MAJOR-1 的根因不是「忘了写锁」，是 **L2/L3 的 v3 夹具让 fail-open 撞上第二条防线
（`_resolve_legacy_stage_root` 自己的「v3 必须 FAIL」）⇒ 缺陷被遮蔽、锁照样绿**。

**⛔ 而 F-20 施工席自己在 NIT-1 上发现过这个模式**（其 neuter⑤ 逐字记着：
「v3 夹具下被另一条独立防线掩盖、红不了 ⇒ 补 legacy-schema 变体才精确捕获」），
**却没有把它推广到 L2/L3/L8**；而**施工席与 orchestrator 共同签字**判过
「L2/L3/L8 已独立覆盖该防线、不需重复」—— **两方都错，由跨家族审推翻。**

⇒ **新判别问法**：**「我这个夹具里，有没有第二条防线会先于目标门把这个变异拦下？」**
若有 ⇒ 这把锁测的是那条防线，不是目标门。
⇒ **凡在某一处发现了遮蔽，必须立刻横扫同批所有锁问同一个问题。**

## 6. 记账

- **派工方错误率 15/15 维持**（本批的错误判断是「已独立覆盖」那条签字，
  但它由施工席先提出、orchestrator 附议，**不新增派工单出题错误**）。
- **⭐ 跨家族审阶梯本轮价值兑现三次**：sol 出稿时躲开两发雷（V1/V2 三态 · 新检查放哪层）·
  sol 审施工时抓出这条 MAJOR ⇒ **「谁写谁不批」在本批共拦下三处同家族盲区。**
- **额度形态**：本批 = **Claude 侧施工 + GPT 侧审与返工**，审阶梯整个落在 GPT 侧
  （用户 08-10 定：新活优先走 GPT 额度），**基本未消耗 Opus 预算**。
