# E-a · B5 端到端接线 · 接线点勘察（2026-09-05 主控只读实测）

## 一、事实复核：B4 配对模块今天确实零生产调用者

```
grep -rn "opening_synthesis" src/ scripts/ --include=*.py   # 除自身外：0 命中
grep -rln "opening_synthesis" tests/ | wc -l                 # 2（只有测试）
```
⇒ plan.md「B4 配对模块今天零生产调用者」**成立**（09-05 复核，基准 HEAD `b4f0b348`）。
B4 那一轮只改了一个文件：`src/agent/correction/opening_synthesis.py`（+328 −43）。

## 二、接线要喂给它什么（`synthesize_openings`，`opening_synthesis.py:1009`）

| 入参 | 谁该提供 | 备注（docstring 原话，⛔ 非我推测）|
|---|---|---|
| `elevation_doc: dict` | 一张立面的 as-drawn 产物 | —— |
| `walls` / `plan_openings: Sequence[CutLineV1]` | **投影桥**（B1）的平面侧切线 | 「either loader produces them; here they are pure data」|
| `mirrored` / `local_x_positive` | **调用方声明**的画法朝向 | 「resolved fail-closed through the signed convention (`facade_convention`)；本函数⛔ 从不猜方向」|
| `evidence_debts` | T4-a 的债 | —— |
| `elevation_source: ElevationSourceIdentity` | **调用方声明**的那一份冻结源身份 | ⭐ B4 返工 1 的 B-2：债只在 `affected_refs` **恰好点名这一个实例**时退役 ⇒ **South 只退 South 的债**；不声明源 = 不退任何债 |

⭐ **两个「调用方的义务」是接线单的实质内容**，⛔ 不是「调一下函数」：
1. **哪些平面洞口是这张立面的候选** —— docstring 明写归 `facade_visibility` 管，
   ⛔ **不许用 bbox 极值抄近路**（原文点名了这条捷径）。
2. **朝向必须来自签字过的 convention**，⛔ 不许在调用点现编。

## 三、下游接缝已经在场

`pipeline.py` 的 correction 段已经把**模型那一拍**接好了
（`_make_decision_response_provider`，`:946` 起；packet→response，带无坐标载荷守卫 + 严格类型构造 + 格式重试）。
⇒ E-a 不是「从零接」，是**把 B4 的配对结果接进这条已经在跑的三拍循环**。

## 四、派工单要写死的两条（今天就能定）
- **交 judge 必须以 strict 进入**（plan.md E-a 已记）
- **身份从 bundle 的 `source_artifacts[0]` 提取，⛔ 不许手拼**（同上）
- ⭐ 补一条：**接线后必须有一条锁证明「不声明 `elevation_source` 就退不了债」**
  —— 那是 B4 返工 1 花一轮才买回来的性质，接线时最容易被顺手绕过。
