---
name: list-the-directory-before-writing-a-new-doc
description: 动手写"新"文档前先 ls 一眼同目录；我重写了一份已存在的稿子，还把旧稿已经写对的字段写漏了
metadata:
  type: feedback
---

2026-08-25：用户问「话说你上轮不是写过一份讨论吗？」—— **写过**。
`logs/reviews/request/` 里已有一份给 sol 的架构讨论稿（六问、含污点声明），
我没查就重写了一份内容高度重叠的求解单给另一个家族。

**⛔ 真正的代价不是重复劳动，是质量倒退**：旧稿 §二**正确列出**了新识图产物的
`hypotheses.{opening_candidates, opening_types}`，我重写时**漏了这两个字段** ——
而跨家族对方**第一条就抓住了它**，并指出不纳入接口则门窗语义仍然断线。
⇒ **重写一份文档 = 把已经踩平的坑重新挖一遍**，因为我复述的是记忆而不是那份文件。

**How to apply**：
- 写任何"新"文档前，**先 `ls -lt` 那个目录**（尤其 `logs/reviews/request/`、`architecture/`、`guides/`）。
  成本 5 秒，我这次省掉这 5 秒的代价是一整份文档 + 一个被漏掉的字段。
- 找到旧稿后，**默认是累计式改写那一份**（[[spec-must-be-cumulative]]），⛔ 不是并存两份。
  确实需要并存（受众/性质不同）时，**两边都要写明各自定位并互加指针**，否则下一轮必然读错。
- 同族：[[reproduce-the-form-not-the-run]]（翻历史先读当时的 README）——
  **同一个病根：拿脑子里的印象代替那份文件本身。**
