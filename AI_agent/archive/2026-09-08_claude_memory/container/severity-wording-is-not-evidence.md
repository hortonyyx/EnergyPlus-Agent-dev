---
name: severity-wording-is-not-evidence
description: 把同一行代码产生的两条警告拆成「一真一假」——因为一条措辞吓人、一条措辞平淡
metadata:
  type: feedback
---

**2026-09-08**：一次撞墙跑出 24 条 FLAG，我把它们拆成两类：

- `reading.dimensions_present`（「dimensioned view has empty dimensions[]」）⇒ 我判 **假红**
- `reading.plan_scale_origin_usable`（「the plan channel would **score zero**」）⇒ 我判 **真缺陷、必须修**

并据此给用户的盘面写下「**不修 W#1，就算全程跑通分数也是零**」。

**GPT 席位停下上报，实测推翻**：两条**出自同一行代码** ——
`validator/checks/view_manifest.py:104` 仍对新契约产物调 `parse_reading_view`，
而 `reading/schema.py:122` 默认 `image_kind="plan"` / `strokes=[]` / `dimensions=[]` /
`scale_origin=None` ⇒ 同一句警告在 **4 张立面上也出现**（立面被解析成 plan）。
而标准入口**早有 as_drawn 专用评分分支**（`run_stage.py:2404`），
按产物契约分派、消费 `observations.face_lines` 的米制量，**不要 legacy `scale_origin`**；
我自己引用的那个 run 里**已有非零平面分**（1f 100.0 / 2f 98.1）。

**Why**：我让**警告的措辞**替我做了分类。措辞平淡的判假、措辞吓人的判真 ——
⛔ 而**严重性措辞是作者对后果的猜测，不是它成立的证据**。
这是 [[observation-named-as-fact-travels-as-fact]] 的近亲：
那条是**名字**冒充事实，这条是**严重性措辞**冒充证据。

**How to apply**：
- 判一条红是真是假，问「**它是怎么产生的**」（哪一行代码、什么输入触发），
  ⛔ 不是「**它说得多严重**」。
- ⭐ **同一批告警先按【产生它的代码路径】聚类，再逐类定性** ——
  一批里有的措辞吓人有的平淡，恰恰是**该聚类**的信号，⛔ 不是该分开的信号。
- ⚠️ 越吓人的措辞越要先查机制：它最可能让你跳过核实（我就是这么跳过的，
  并把它写进了给用户的盘面）。

配套：[[citing-someone-elses-fact-does-not-transfer-responsibility]]
· [[stop-and-report-catches-dispatcher-errors]]（第 73 次，仍是派工方错）
