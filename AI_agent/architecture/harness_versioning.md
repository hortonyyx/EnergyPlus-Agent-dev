# harness 版本管理（2026-08-22 用户定，硬规矩）

> **口径（用户原话）**：整套 harness 按 **case 对应的能力点**做版本管理；
> **探索性的不进版本，确定性留下来的才进版本。**

配套机器可读清单 → [`harness_versions.yaml`](harness_versions.yaml)（本文是它的说明书）。

---

## 0. 它解决什么问题

之前 harness 是**一坨**：工具、提示词、门、判卷器混在一起随时改，
出了成绩说不清「是哪一版做出来的」，换了 case 也说不清「上一版覆盖不覆盖这张图」。
⇒ 每次跑测都在一个**没有名字的**基座上，[[version-number-is-not-behavior-attestation]] 那条的放大版。

---

## 1. 能力点 = 两根正交的轴（⛔ 只声明一根不算）

### 轴 A · 建筑复杂度（沿用既有 C 阶梯，[capability/pipeline_0-5_capability_upgrade_suggestions.md](../capability/pipeline_0-5_capability_upgrade_suggestions.md)）

| key | 含义 | 代表 case |
|---|---|---|
| `c1_rect` | 矩形 · 共底面盒子 | sm20 / sm21 / sm24 |
| `c2_ortho_poly` | **正交多边形 + 多层 + 多平面立面** | **sm25-L** |
| `c3_setback` | 退台 / 挑空 / 中庭竖井 | — |
| `c4_skew` | 斜交墙 | — |

### 轴 B · 图纸方言（⭐ 2026-08-22 首次被量出来，此前全项目当它不存在）

| 维度 | 取值 | 怎么测（确定性） |
|---|---|---|
| `ink_layering` | `layered` / `monochrome` | 门窗色墨迹占比 ≥1% ⇒ layered。实测 sm25 12.3% · sm24 15.6% · sm21 9.7% · **sm20 0%** |
| `wall_rep` | `two_face_lines` / `solid_fill` | 墙是两条细面线+中空，还是单条实心带。实测 sm25=两条面线 · **sm24=实心带** |
| `annotation_layer` | `present` / `absent` | 尺寸标注是否单独成色（决定见证刻度能不能自动提取） |

**⛔ 一个版本必须同时声明它支持轴 A 的哪一格、轴 B 的哪些取值。**
只写 "支持 C2" 是不合格的声明 —— 本轮实证：在 sm25（C2 · layered · two_face_lines）上造好的工具，
迁到 sm24（C1 · layered · **solid_fill**）**第一次直接失效**（零墙带）。
方言不声明，就会把「换个 case 就崩」当成「模型不行」。

---

## 2. 什么才配进版本（⛔ 唯一准入判据）

> **只有走完开发循环第 ①–④ 步、并在第 ④ 步对 gt 验过的东西，才写进版本。**

开发循环（2026-08-22 用户定）：

```
① 探索性把这个 case 做完 → ② 沉淀成定稿工序 → ③ 按定稿从头干净跑一遍
→ ④ 对 gt 判分 ──做好了?──否→ 回②查病因
                        └─是→ ⑤ 固化进 harness，版本 +1 → ⑥ 换弱模型跑
                                                              ├好→ 下一个 case
                                                              └差→ 查病因，回②
```

| 阶段 | 产物去哪 | 能不能进版本 |
|---|---|---|
| ① 探索 | run 目录 `out/tools/` · `logs/experiments/` | ⛔ **永远不进** |
| ② 沉淀 | 同上，标 `candidate` | ⛔ 不进（还没验） |
| ③④ 验证跑 | run 目录 + 判卷产物 | ⛔ 不进；**它是准入证据** |
| ⑤ 固化 | `src/` · `scripts/` · `skills/` + 本清单条目 | ✅ **只有这里** |

⛔ **反向铁律**：探索档产物不得记成成绩（[CLAUDE.md §0.2](../CLAUDE.md)）——
本条是它在 harness 侧的对应物：**探索期的工具不得被当成「harness 已具备的能力」引用。**

---

## 3. 一条版本记录必须写清六件事

| 字段 | 说明 | ⛔ 不合格的写法 |
|---|---|---|
| `capability_key` | `<环节>@<轴A>` | 缺环节前缀 |
| `version` | `v1` / `v2` …（**行为变了就 +1**，不是文件改了就 +1）| 靠时间戳 |
| `supports_dialects` | 轴 B 的取值集合 | 不写 = 默认全支持（错） |
| `admits` | 具体收了哪些工具 / recipe / skill / 门，**逐个点名** | 「读图工具箱」这种整包名 |
| `evidence` | 准入证据：哪个 run、对哪份 gt、判据得分 | 「跑通了」 |
| `known_gaps` | 这一版**明确不支持**什么 | 留空（= 假装没有边界）|

⭐ `known_gaps` 是必填项。**一个不写自己边界的版本，等于声称支持一切**——
[[declare-the-dialect-plus-consumption-ledger]] 同形：没声明过的形态要从「静默漏」变成「点名红」。

---

## 4. run 侧怎么落地

每个 run 的 `run_config.yaml` 增记一行：

```yaml
harness:
  capability_key: reading.plan@c2_ortho_poly
  version: exploratory        # 探索档一律写 exploratory，⛔ 不许填版本号
```

- `version: exploratory` ⇒ 该 run 的产物**永远不能**当作某版本的能力证据。
- 填了版本号 ⇒ 必须是本清单里已存在的条目，且该 run 只用该版本 `admits` 里点名的东西。

⚠️ **当前尚未接线**（没有代码读这个字段）。按 [CLAUDE.md §0.1](../CLAUDE.md) 的判断法则，
接线要等**第一次真的要固化**时再做——那时它才影响「下一次跑测能不能跑起来」。
在那之前本文是**人读的规矩**，清单是**手工维护的账**。
