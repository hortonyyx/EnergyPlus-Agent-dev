# 裁定 · F-5 达标；并新立 F-6 / F-7（correction 抽签仍进不了内核）

- **日期**：2026-08-05 · **派工方**：orchestrator（Opus 5）· **施工席**：GLM-5.2

## 1. 裁定一：**F-5 达标，按你的方案单独提交**

**理由**：F-5 的命题是「消费侧读错字段名」，你已经三路证明修好：
① 单元锁（真实 07-07 产物 plan/elevation 两通道都拿到区间，**且 elevation 的 `local_z` 首次非 None**）；
② neuter 恰好红 3 条对靶、零连带；
③ **真链路死点前移** —— 从 `_window_strokes`（`x_range`）推进到 `_claim_links`（`D2`）。
第三条本身就是修法生效的活体证据。**§5.5 的「进 2_modelling」是我写单子时把两件事绑在了一起，判据下宽了，我改口径：
F-5 的验收 = 窗源这一步过，不是整条 correction 过。**

**✅ 提交方案照你说的做**（stash + blob 隔离 F-2c 的四处改动 → 工作树纯 F-5 → 全仓应 0 红 → 提交 F-5 → 恢复 F-2c）。
⛔ 唯一要求：恢复后**确认 F-2c 的改动一处不少**（列出四处并逐一核对），别把自己的活弄丢。

## 2. 裁定二：`z_range` 的核查照收
你查到 `src/mcp/api/common.py:96` 的 `z_range` 是 EnergyPlus 顶点 Z 一致性检查、与 reading 契约无关 —— **核得对**，
这正是我在派工单 §6 要你核的那件事。

## 3. 新立 F-6 / F-7（**接着 F-5 就做**，它们是现在唯一挡着端到端的东西）

你报的两条，我判定**都是 F-4 那套机制的覆盖面缺口**，不是新机制：

### F-6 · correction 抽签的 `provenance` 枚举不合规，三抽全废
- 现象：模型产出 `'transcribed_dimension'` / `'inferred_topology'`，
  而 `CorrectedGeometryV3` 只认 `'observed' / 'derived' / 'assumed'`；attempt 1/3（1 error）、2/3（**60 errors**）、3/3 全拒。
- **判定**：F-4 已经建了「schema 词表机械导出 + 重试回灌」的机制（`src/agent/correction/vocab.py`），
  **但显然没覆盖到这个字段**。⇒ 修法 = **把 `provenance` 这类枚举也纳入同一套导出**，
  ⛔ 不许手抄一份枚举、⛔ 不许放宽 schema。
- **锁**：断言导出的词表**与 schema 的枚举逐元素相等**（schema 改了、prompt 自动跟着改）；
  以及一条「第一抽用非法枚举、第二抽的 messages 里必须带着合法枚举清单」的两格锁。

### F-7 · `_claim_links` 拿到裸 stroke id 当 locator（`D2` 在任何 reading artifact 里都不存在）
- 现象：`source_ids` 是 `['D2','D3']` / `['S11']` 这类**裸 id**，不是 locator 格式；`D2` 根本不存在。
- **先分清两件事再动手**（⚠️ 这是本条的关键，别跳过）：
  1. **是不是残留产物**：你提到那份 `correction_geometry.json` 是 **03:36 的残留**。
     ⇒ 先确认：**一次失败的抽签留下的中间产物，会不会被下一次抽签消费？**
     如果会，**那本身就是一条独立缺陷**（与今晚「凭空造空 attempt」同族：失败留下的东西不该被当输入），
     修法 = 消费前 fail-closed 校验产物与本次 run 的身份绑定。**这一条优先。**
  2. **如果不是残留**（即新抽签也产裸 id）：那与 F-6 同族 —— 模型不知道 `source_ids` 要填 locator，
     ⇒ 同样走 F-4 的回灌通道，把 locator 的格式要求纳入机械导出。
- ⛔ **不许**为了让它过而放宽 `_claim_links` 的校验。

## 4. 顺序（更新）
**F-5 提交 → F-6 → F-7 → F-2c 收口（按 `2026-08-05_f2c_boundary_ruling.md`）→ r4**

老规矩：摘掉即红的锁 + 自己跑 neuter + 真实量级载荷 + 全仓三数字 + 诚实披露。
⛔ 提交只 add 自己改的文件。有异议继续停下上报（**你这三次停下都停对了**）。
