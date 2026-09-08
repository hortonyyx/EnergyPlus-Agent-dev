---
name: cache-in-front-of-a-gate-is-a-second-entrance
description: 判据前面若有缓存，缓存命中那条路就是第二个入口——我只验了首次计算那条，sol 用「先算出 trusted 缓存→删掉凭证→缓存照样给 trusted」把门绕过去
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cc9a6b0d-6528-4c5f-a729-647c4bb3c4a6
  modified: 2026-08-13T11:04:00.108Z
---

08-13 实证。F-22 BLOCKER-1 的修法把信任判据改成「只认落库方签发、绑进账本的 proof」。
**orchestrator 轻门把这条验到了首次计算路径上（手加印章⇒只得 declared、伪造 proof⇒trusted=False，都对），
判了 PASS。sol 第四轮用一条我没走的路推翻**：

先让生产判卷入口算出一份 `trusted=True` 的**缓存侧车** → **删掉 proof 文件** →
确认 `_resolve_core_proof_for_attempt` 明确返回 `None` → 再走**同一个生产入口**
⇒ **判卷函数零调用、旧侧车直接复用、仍然 `trusted=True`**。
根因是**时序**：缓存判据在 proof 解析**之前**，而缓存 key 里没有 proof 身份。

⭐ **判别问法 =「这道判据前面有没有缓存？缓存命中那条路，走不走这道判据？」**
⭐ 更一般的形状 = **「我验的是这道门，还是绕过这道门的那条路？」**
⛔ 「首次计算时判据生效」**不等于**「判据生效」——缓存、memo、侧车、快照都是同族的第二入口。

修法口径（sol 给的最低四条）：缓存查找**之前**先解析并验证当前 proof · 缓存身份绑
proof bytes hash + accepted record identity · 缓存自称 trusted 时 proof 缺失必须 miss 并重算为拒判 ·
补真实入口锁（先 trusted 缓存→删 proof→miss→trusted=False）**且保留 proof 不变时必须命中的正向锁**。

与 [[gate-with-only-negative-assertions-is-unobservable]]、[[neuter-must-cover-wiring-not-just-mechanism]] 同族：
都是「机制对了但接线/入口没覆盖到」。与 [[hash-of-whole-report-is-not-an-equality-test-for-its-parts]] 的
「问法=这个 hash 覆盖的范围是不是正好等于我要判的那件事」互补——这条问的是**覆盖的入口**而非覆盖的字段。
