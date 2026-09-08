---
name: spec-must-be-cumulative
description: "细稿/方案文档同路径迭代时必须累计式自包含，禁\"vN 不变\"引用已覆写正文（2026-07-10 sol 判 BLOCKER 的教训）"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d88d88bf-9bd3-4684-bc22-7857c8a3488f
---

2026-07-10 B2/B-M 细稿 r3 轮：v3 修订稿为省篇幅把大量规范写成"v2 不变/基础上修"，但 v2 正文已被同路径覆写、无版本化快照，sol 判两稿共同 BLOCKER——"指向已消失文本的增量补丁，不是可施工细稿"。

**Why**：执行者只拿当前稿施工；review verdict 只记录问题与裁决，不能充当 normative include。上位设计（c2_full_unlock_design.md v2.2）本身就是累计式全文，细稿偏离了这个惯例。

**How to apply**：同路径迭代的规范文档每版必须自包含全文（版本史头记增量即可）；确需增量写法，先把上一版逐字节固化到版本化路径+登记 SHA 再精确引用。自检口径 = "新执行者只读当前稿能否列出完整 wire/writer/consumer/验收表"。相关 [[c2-full-unlock-sprint]]。
