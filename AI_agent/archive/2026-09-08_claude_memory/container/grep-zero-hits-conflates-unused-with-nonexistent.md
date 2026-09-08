---
name: grep-zero-hits-conflates-unused-with-nonexistent
description: grep 一个名字返回零结果，在「存在但零调用」和「根本没这个名字」之间是二义的——我把 docstring 里的中文描述当成函数名，据此写出「全仓零生产调用者」并发进三份文档
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2f8fd7aa-2be5-41c4-8ab8-fa97701b33f1
  modified: 2026-08-22T09:25:24.399Z
---

**2026-08-22，GLM 跨家族审 MINOR-1 抓出本轮唯一一条没被任何工具拦下的错。**

## 事实

我读 `src/validator/checks/view_manifest.py`，看到第 43 行的 docstring：

```python
def check_reading_stage(...):
    """The "merge 同门" checker (:func:`check_view_manifest_coverage`) + per-view ..."""
```

我把那句**描述性的中文短语**「merge 同门 checker」当成了一个标识符 `check_view_manifest_merge`，
然后 `grep -rn "check_view_manifest_merge"` → **零结果**，
于是写下「⭐ `check_view_manifest_merge` 全仓**零生产调用者**」，
并以**实测事实**的口吻发进 **三份文档**（plan.md / 工具缺口清单 / 跨家族派工单）。

**代码里从来没有过这个函数。** 我发的是一句关于不存在之物的「实测结论」。

## ⭐ 机制（这才是可复用的部分）

> **`grep <name>` 返回零结果，至少有两种原因：**
> **① 这个名字存在、但没人调用它（＝一条发现）**
> **② 这个名字从来不存在（＝我记错了）**
> **零结果本身分不开这两者，而 ①听起来像成果、②听起来像错误 —— 所以人会默认读成 ①。**

同族：[[absence-conflates-causes-in-observables]]（缺席把多种原因压成同一个空白）·
[[absent-file-read-as-passing-check]]（`grep … || echo 通过`：文件不存在也算通过）。
区别在于：那两条是**观测量**的缺席，这条是**被观测对象**的缺席 —— 更隐蔽，
因为验证动作（grep）本身跑得好好的，只是问错了名字。

## ⛔ 它与「量错了」不同类

本轮我另犯四处错，全部当场被工具拦下（链闭合抓 OCR 数错、gate① 抓 axis 填反、
尺寸链抓碎片规则漏、跨轴检查抓抄近道）。**唯独这一条工具拦不住** ——
因为它不是测量错误，是**把读到的东西记成了另一个东西**，落到产物上就是一句流利的假话。

## How to apply

- **引用任何标识符（函数 / 字段 / 参数 / 配置键）之前，先确认它存在**：
  `grep -n "^def <name>\\|^<name>\\s*=\\|\\"<name>\\"" `，⛔ 不是 `grep <name>` 看有没有调用。
- **零结果时必须二选一地写出来**：写「该名字在仓库中不存在」还是写「存在但零调用」——
  ⛔ 不许含混地写成「零调用者」。
- **docstring / 注释里的自然语言描述不是标识符**。中英混排的注释尤其容易被读成命名
  （「the X checker」→ `check_X`）。
- 涉及**要发出去**的结论（派工单、裁决、给用户的汇报）时，这一步不能省：
  跨家族审能抓住它，但那已经消耗了另一个席位一整轮。
