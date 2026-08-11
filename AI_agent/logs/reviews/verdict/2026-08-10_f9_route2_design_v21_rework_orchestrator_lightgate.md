# F-9 路线②设计稿 v2.1 · 返工轻门裁决（orchestrator）

> 日期：2026-08-10 · 受审：`AI_agent/proposals/f9_route2_evidence_citation_design.md`（v2 → v2.1，+111/−21）
> 返工席：`gpt-5.6-sol` / effort max · 轻门：orchestrator（Claude 侧 Opus 5）
> 前序：[v2 对抗审裁决](2026-08-10_f9_route2_design_v2_crossreview_orchestrator.md) = APPROVE-WITH-CHANGES（1 MAJOR / 2 MINOR）

## 裁决

**PASS** —— MAJOR-1 与 MINOR-1 均已实质关闭，**零新增问题**。设计稿可据以出施工单。

## 范围核实（防"顺手重写"）

`git diff --stat` = **1 文件 / +111 / −21**，仅动目标文档。882 行的稿子**没有被重写**，
v2 已解掉的 v1 三条 BLOCKER + 五条 MAJOR 的正文**一字未动** —— 返工范围守住了。

## MAJOR-1（z 轴 datum 未声明）· 关闭

新增 §7.3「local-z datum 与 scope 唯一归属」，与 §7.2（改名为「当前 local-x datum mode」）对称：

| 要求（我提的） | 稿中落点 | 判定 |
|---|---|---|
| 给 z 轴与 §7.2 对称的显式声明 + 未声明 typed 拒绝 | `z_datum_mode: world_z \| floor_local_z`，strict variant；缺失/未知/少 origin/少 assignment 一律 `projection_datum_unresolved` | ✅ |
| 写死「一条立面笔画归属哪个 scope」的判定规则（含边界与重叠） | §7.3 五条机械规则 + 冻结 `projection_scope_epsilon_m = 1e-9` 的 `contained()` 谓词；闭区间判定；空⇒`projection_scope_unresolved`、多解⇒`projection_scope_ambiguous` | ✅ |
| §12.2「Pair positive」补同 view / 同 along / 仅 z 不同的夹具，去掉 z scope 必红 | 已补，且**拆成三把具名子锁**（见下） | ✅ |

**⭐ 三条我没要求、但正确的加固**（记正分）：

1. **「今天产物的 local-z 恰等于 world-z 不能充当声明」写进了稿子** ——
   这正是我 MAJOR-1 里点的"更隐蔽的一层"（实现者随手假设今天会碰巧全对）。
   稿子直接把它列为**不可接受的推断来源**，并要求版本化 reading 合同或 authenticated sidecar 明文承诺。
2. **scope 过滤必须发生在距离计算与 mutual-nearest 排名之前** ——
   否则其他楼层的 stroke 会先进候选域制造同分、再被报成 ambiguity（自造歧义）。
3. **source 的 scope 解析必须独立于任何 window、且在看见 model citation 之前形成** ——
   堵死"拿 window.z 最近者补齐 assignment"的循环论证。

**另**：跨边界 stroke ⛔ 不许按 midpoint / overlap 长度 / 最近楼层拆派，必须有显式 cross-band scope；
重叠 scope ⛔ 不取第一项、不选最窄 —— 与项目「⛔ 不得兜底默认」一族一致。

**承重新声明已核实**：稿中「window 的 `z` 继续按现合同解释为 world-z」属实 ——
`src/agent/correction/schema.py:215` 逐字为 `z: list[float]  # [sill, head] world`，
真实产物二层窗 `z=[4.00,5.80]`（`floor_2.z_floor=3.0`）亦印证。

**错误词表已同步扩写**（§9）：`projection_datum_unresolved` / `projection_scope_unresolved` /
`projection_scope_ambiguous` 三码分列，出口均为 upstream evidence block（⛔ 不重抽模型），
并加了「绝不猜 mode、origin 或 scope」。
**哈希 preimage 亦已扩**（§8.1）：`z_datum_mode`、resolved `scope_id`、projected world-z、plan `floor_ref` 入 hash。

## MINOR-1（0.300 m 阈值不可观测）· 关闭，且做得比要求更细

我要求「两个 regime + 跨阈值对照」。稿子把 `Pair positive` **拆成三把具名子锁**，
理由写得明白：**不能把多个前提揉成一次"最终 PASS"** —— 这比我提的要求更严：

- **① z-scope 锁**：同 view / 同 along / world-z 分属两层的两条 stroke；neuter scope filter 后必须因同分或错配转红；
  另用 `floor_local_z` + 非零 per-scope origin 固定按层归零的输入，缺任一 assignment 即红；
- **② regime 锁**：**同时**保留老夹具非零带内样本 `d=0.12` 与现代产物零差样本 `d=0`
  ⇒ 证明既没有只接受 exact-zero、也没有为 zero 特判；
- **③ threshold 锁**：除端点残差外完全相同的 `d=0.29` / `d=0.31` 两格，钉住 `<= 0.300` 的放行/拦截边界；
  **把配置改到 `0.28` 或 `0.32` 至少一格必须红**。

`projection_scope_epsilon_m` 单列且明文「不是测量容差、绝不能借用 `window_evidence_pairing_tol_m`」
—— 与项目「`ge=1` 是范围校验不是语义门」那条教训同源，正确。
「expected 不得调用 production projector 生成」保留。

## §14.3 · 已按要求更新且口径照抄

三条实测项已从「未验证」移入「审裁新增实测」，**并逐字保留了我给的口径限制**：
「今天盘上的一份语料（1 个 case / 15 扇窗），不是代码保证或"模型永远如此"的不变量证明，
施工期 targeted replay 仍须保留」。
且自行补了一句正确的推论：**「这份语料没有 `(0, 0.300]` 内样本，故不能独自赋予阈值分辨力」**
⇒ 由 §12.2 的专锁承载该证明。这是对我实测数据的正确解读，未过度外推。

## 结论

- **PASS**，0 新增 finding。**⇒ 可以出施工单了。**
- 施工单起草时须原样带上：§7.3 五条 scope 规则 · §12.2 三把具名子锁及其 neuter 要求 ·
  §14.3 的语料口径限制（防施工方把"15/15 通过"当成不变量）。
- 施工席建议按协作规约走 **执行档**（Sonnet / terra），**⛔ 不派 sol 施工**（sol 过度追目标、不当执行器）；
  施工后的审按「谁写谁不批」交另一家族。
