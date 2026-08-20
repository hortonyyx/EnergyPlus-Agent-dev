# G1 pilot r2 · 判卷之后的附记（⛔ 独立文件，以免改动被封存正文的哈希）

> 被附记的封存正文 = `pilot_verdict_r2.md`，其封存哈希 sha16 = `615a1b8a2bc82abd`。

---

## ⛔ 附记（判卷之后追加，⛔ 不修改上方已封存正文）

**上方的预测失败了。** 判卷结果与 r1 **逐字节相同**（产物 sha16 同为 `3df4d7fb3ffdee46`，
墙 4/4 · 窗 3/3 · 最大偏移仍是 **0.18 m**）。

**原因 = 派工方（orchestrator）的返工文本自相矛盾**，不是读图器不照做：
文本里既写了 "propagate the resulting scale through the strokes you have already drawn"，
又写了 "Do not re-trace the drawing"。读图器把后者当主导，明确回复
「The pilot drawing itself was not retraced」——**它的选择在给定文本下是合理的。**

⇒ **裁定改判：r2 = REWORK（第二轮），原因归派工方。**

## ⭐ 这次暴露出的、值得记进 reading 专项的东西

「换一把尺子重算已画好的笔画」这件事，**在当前产物形态下无法纯代码完成**——
因为产物里存的是**米坐标**，不是像素锚点。要重算就必须让读图器回去重新测像素。

⇒ 这正是 [reading 专项 §9.1](../../../../AI_agent/capability/reading/improvement_methodology.md) 那条根治修法
（**读图器只写像素锚点 + 证据引用，米制换算由代码唯一执行**）的**直接实证理由**：
若产物存的是像素锚点，本次返工就是一次纯代码的重算，零模型参与、零歧义空间。
**本抽是该修法迄今最具体的一份支持证据。**
