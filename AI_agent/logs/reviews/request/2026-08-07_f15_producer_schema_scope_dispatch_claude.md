# 施工单 · F-15：校正抽签的 schema 暴露了「内核专属字段」，模型必填、必被拒、盲重抽治不了

- **日期**：2026-08-07 · **派工方**：orchestrator（Opus 5）· **席位**：Claude 侧 Sonnet 子代理
- **工作区**：主工作树 · **基点**：开工时 HEAD（自查并记录）
- **背景**：本轮目标（用户 08-07 定）= **拿 sm21 好 reading 产物把链路全跑通到 EnergyPlus**。
  F-9 治本已施工（未落库，改动在工作区），**跑真链路时撞上本单这堵新墙，卡在 1_correction。**

---

## ⛔ 本单分栏（派工方本轮已 4 次把推断当事实，故严格分开）

**【A 实测事实】** 附命令/路径/数字，可采信 · **【B 派工方推断】** **未验证，请优先证伪，不符就推翻并上报。**

---

## 【A 实测事实】

**A1 · 现象**：`run_2026-08-07_f9_root_fix_verify`（07-07 好 reading 产物，`flow … --to 1_correction`）
**三次抽签全挂在同一个错**：

```
attempt 3/3: WindowResolverInputError: producer_segment_ref_prefilled: {}
```

产物：`case_tests/e2e_tests/sm21_anchor/run_2026-08-07_f9_root_fix_verify/1_correction/`
（`correction_parse_error.txt` / `correction_raw.txt` / `correction_thinking.txt`，**⛔ 只读**）。
`1_correction/attempts/` **为空** ⇒ 无 accepted attempt。

**A2 · 模型到底填了什么**（orchestrator 亲查 `correction_raw.txt`）
- `windows` 15 个，`facade_segment_id` 全部填了（`'1F_North'`/`'1F_South'`/…）。
- **顶层 `facade_segments` 数组被整个造了出来**，含 `p1/p2/outward_normal/world_along_interval/
  depth/visible_intervals`，并且 `source_footprint_fingerprint` = **`'aaaa…'`（64 个 a，编造的占位哈希）**。
- 模型输出的其余部分是像样的（`schema_version:"3"`、`footprint_x:[0.12,14.88]`、`floors`/`cells` 齐全）。

**A3 · 拒绝规则在哪**
`src/agent/correction/window_sources.py:878-882` `_producer_preflight`：
`producer.facade_segments` 非空、或任一 `window.facade_segment_id is not None`
⇒ `WindowResolverInputError("producer_segment_ref_prefilled", category="model_draw_error")`。
同名早退在 `src/agent/correction/parse.py:101-105`。
注释自述这两个字段是「deterministic-core-only」，模型预填 = 「writing outside its scope」。

**A4 · 提示词里没有这个字段**
`grep -rn "facade_segment" src/agent/pipeline.py skills/intake_pipeline/` ⇒
**`pipeline.py` 零命中**；`skills/intake_pipeline/1_correction/A0_contract.md` 仅两处，
且是 `facade_segments_sha256`（:221）与检查名 `facade_segment_coverage`（:450），
**都不是「你要填/不要填这个字段」的指示**。

**A5 · schema 里有这些字段**
`src/agent/correction/schema.py:198` `facade_segment_id: str | None = None`；
`:250-251` 还有「填了但不在 `segment_ids` 里就报错」的校验
⇒ **schema 层面这是一个「可以填」的字段。**

---

## 【B 派工方推断 —— 请优先证伪】

**B1**：模型之所以必填，是因为**结构化输出把 `CorrectedGeometryV3` 整个 schema 交给了它**，
而 schema 没有任何「这些字段留空」的信号，提示词也没说（A4/A5）。
⇒ **这是接口层缺陷**，与 F-5（字段名错拼）/ F-7（locator 结构上产不出）/ F-9（镜像要模型心算）**同族**：
**把不该模型管的东西暴露给模型，再靠事后拒绝纠正。**

**B2**：**盲重抽治不了它** —— A1 显示 3/3 同一个错。
请查清：F-4 立的那套「校验失败回灌给模型」的机制，**在这条路径上到底有没有生效**？
（`parse.py` 的注释自述这两个 raise 的价值是「inner-retry channel 里一个稳定的具名拒绝码」，
⇒ 看起来是**打算**回灌的。）**若机制在却没起作用，那本身是第二个缺陷，请单独登记。**

**B3 · 三条候选修法**（⛔ 未验证，请评估后自行选择并说明理由）：
- **① 接口层（推断最优）**：给校正抽签一个**生产者视角的 schema 变体**，
  **结构上就不含**内核专属字段（`facade_segments` / `facade_segment_id` / resolver 审计行）
  ⇒ 模型**无法**填错。符合本项目反复得到的教训「修法必须在接口层」。
  ⚠️ 风险：`CorrectedGeometryV3` 是既有契约，改动面可能很大 —— **请先评估再动**。
- **② 提示词层**：明确告诉模型这些字段留空。便宜，但靠 LLM 听话，且与 F-12 的教训冲突
  （**prompt 正则锁已被实证可被无害改写绕过**，prompt 不是防线）。
- **③ 回灌层**：把这个具名拒绝码有效地回灌给模型（若 B2 查出机制没生效）。
  ⚠️ 单独用它治标不治本（模型每次都要先错一次）。
- ⇒ **①+③ 可能是组合最优，但由你评估后定，并在日志里论证。**

---

## ⛔ 硬边界

- ⛔ **不许放宽 `_producer_preflight` 的拒绝**（那是真门，模型确实不该填）。
- ⛔ 不改 `_BASE_SIGN` / 方向约定 · ⛔ 不放宽任何容差 · ⛔ 不碰 0.12m 那条既有债。
- ⛔ 不改下游提示词 / 几何内核 / drift 门。
- ⚠️ **工作区里有 F-9 治本的未落库改动**（`src/agent/correction/window_sources.py`、
  `src/agent/pipeline.py`）—— **那是上一单的成果，⛔ 不要回退、不要覆盖**；
  **先把它 commit 保全**（message `08.07_f9_root_fix_b1_advisory_world_interval`，
  body 说明 B1 成立、advisory 不进强制路径），再开始本单。
- ✅ 改 `src/` 前先 `cp` 备份到 `backup/src_history/2026-08-07_f15_producer_schema/`。
- ⛔ 不 push · ⛔ 不许 `git add -A`（逐个 add，提交前 `git status --short` 通读）·
  ⚠️ 撞 `index.lock` 等释放再重试、⛔ 不手动删锁。

## 锁 + neuter

- **锁必须走真实入口**，且**必须能被真实模型输出的形态触发**
  （⛔ 不许手搓一个"刚好合规"的夹具 —— F-5 教训：夹具照抄实现 ⇒ 测试永远绿而真链路必崩）。
  ✅ 盘上就有真实的越界产出：`correction_raw.txt`（**只读**，可裁剪成夹具入仓）。
- **neuter 自验**：把病灶**本体**改回缺陷形态，确认锁真红，再逐字节复原。
- ⛔ **不许写自指锁**（把实现的输出喂回实现自己的判定）——本轮已被交叉审抓到一次。

## ⭐ 主验收

**拿 07-07 那份好 reading 产物真跑 1_correction，出 accepted attempt。**
（`case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/`，新 run 目录，
⛔ 不覆盖既有 run，档位 `exploratory`。**会烧 LLM 钱，用户已为本轮目标授权。**）
- 逐窗给「`source_ids` → 换算世界区间 → 与自己平面区间的重叠数字」，
  证明**北立面 4 扇窗各自配到自己**（这同时验收上一单的 F-9 治本）。
- 全仓零回归（基线开工时自查，当前约 2262）。
- **若过了 1_correction 之后在更后面撞到新墙 ⇒ 不算你的锅**，如实登记现象+定性，**⛔ 不要顺手修**。

## 交付

执行日志 `AI_agent/logs/reviews/execution/2026-08-07_f15_producer_schema_scope_claude.md`。
最终回复：① B1/B2 结论+证据 ② 选了哪条修法及理由 ③ 改了什么 ④ 锁在哪几条断言
⑤ **neuter 红了几条红在哪** ⑥ **真链路：accepted attempt 有没有出 + 北立面 4 扇窗的重叠数字**
⑦ 全仓数字 ⑧ commit SHA（含 F-9 保全那次）⑨ 新墙（若有）。

## 停下上报（**记功不记过**）

本轮 **11 次「停下上报」全是派工方（我）的题错了**，且**出错的 4 单全是我把推断当事实写了进去**
（这就是本单分栏的原因）。
⇒ **【B】栏任何一条与你所见不符 ⇒ 直接推翻并上报，这是本单期待的正常结果。**
⇒ **【A】栏若也不符 ⇒ 立刻停下上报。**
