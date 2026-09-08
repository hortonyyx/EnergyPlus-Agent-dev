---
name: real-chain-run-exposes-what-tests-cannot
description: 2026-08-05·拿真产物跑真链路一次撞出 6 条工程缺陷、全仓 2177 单测一条都测不出；最纯形态=测试夹具照抄实现的错拼写
metadata: 
  node_type: memory
  type: project
  originSessionId: 2a823d9a-5699-4868-9da3-62b70d1ab41c
  modified: 2026-08-05T10:03:06.176Z
---

**打法（可复用）**：拿一份**已知满分的历史识图产物**跑「下游机械烟测」（`--judge off --with-ep`），
把识图变量摘掉，只问「除识图外这条链今天还通不通」。2026-08-05 一次跑出 **6 条**工程缺陷，
而当时全仓 **2177 绿零红**——**单测一条都没抓到**。

**最纯的一条 = F-5**：`window_sources.py` 读 `x_range`/`y_range`/`z_range`，
而产品契约（`src/agent/reading/schema.py` + `guide.md`）是 **`x_range_m`/`y_range_m`**；
**四个测试文件的夹具全部照抄了实现的错拼写** ⇒ 实现与夹具自洽、测试永远绿，**任何真实产物必崩**
⇒ **B5 窗源这条路从来没在合规产物上跑通过**；且立面读的 `z_range` 契约里根本不存在
⇒ **窗台/窗顶证据从来没进过这条链**。

**⭐ 新治理教训（与 [[lock-must-exercise-real-entry-point]] 的「探针≠锁 / 非 None≠成功」并列）**：
> **消费某个契约的测试，其夹具必须钉到契约的单一来源（机械导出），⛔ 不许手抄字段名。**

**同批另五条**：判卷不认读图信封 + 空 scores 判 pass（「一张卷子没批 ≡ 全对」）· 隔离 merge 丢 `reading_summary.md` ·
advisory 检查触发早退致未 finalize 草稿被 accept（两段后才炸）· `SCORER_SCHEMA` 未 bump 致旧 sidecar 短路 ·
correction 内层重试是**盲的**（校验失败只写盘、不告诉模型 ⇒ 三次犯同一个错、整条链被打死）。

**同族第三条 = F-7**（08-05 下午）：`_claim_links` 要模型在 `source_ids` 填 locator
（`src:`+sha256，含**识图产物字节的哈希**）⇒ 模型**物理上算不出**，prompt 从没提过，
`_build_correction_messages` 签名里根本没有 manifest/readings（结构上产不出），
locator 基建 `build_window_source_offer` 在生产里是**孤儿**（只被测试调用），
**B5 夹具手搓真 locator 才过** ⇒ 测试绿、真链路必崩。
修法（用户拍板）= **代码侧翻译**：模型填看得见的观测引用 `<图名>/<笔画编号>`，代码翻译成 locator，
合法清单从建 locator 的**同一出口机械导出**后注入 prompt；`_claim_links` 校验一字不放宽。

**⭐⭐ 同族第四条 = F-8（08-05 晚，形态最出人意料）**：
主树 `case_tests/` 比干净检出**多 619 个被 `.gitignore` 挡住的文件**（`eplusout.*` / `*.txt` 原始 LLM 回复 / viewer HTML），
**其中一部分是测试的活输入** ⇒ **干净 worktree / 新克隆 / CI 跑全仓必红 5 条**。
实测坐实：同一份代码，主树 2197 绿 0 红、那 5 条单独在主树跑 5 passed；干净 worktree 5 红。
> **⇒ 「全仓绿」目前是「这台机器工作目录」的属性，不是「这个提交」的属性。**

**⭐ 由此得到的一族总结（F-5 / F-7 / F-8 是同一个病的三种形态）**：
**测试的绿，证明不了它声称证明的东西** ——
夹具照抄实现（F-5）· 夹具手搓生产方给不出的形态（F-7）· 依赖没进版本库的数据（F-8）。
**判别问法：这条测试如果换一台机器 / 换一份真实产物，还成立吗？**

**⇒ 排期含义**：任何「链路升级」批次收官前，必须做一次**真产物真链路**跑测；
单测绿不构成端到端可用的证据。**且报全仓数字必须说清是在哪棵树上跑的**（主树 ≠ 干净检出）。
详见 plan.md 2026-08-05 条。
