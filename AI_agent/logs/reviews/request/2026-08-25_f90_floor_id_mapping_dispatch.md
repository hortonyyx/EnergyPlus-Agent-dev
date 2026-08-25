# 派工单 · 楼层 id 映射层（F-90）

- **日期**：2026-08-25（用户当日令「发吧」）· **施工** = Claude 家族执行档 · **审** = ⭐ **GPT 家族**（用户 08-25 改派：「审走 GPT」）
- **档位**：工程档（碰 `src/agent/judge/`）⇒ gate① + 全量绿 + **跨家族审（GPT）**
- **为什么现在做**：它是「拿 sm25 撞 C2」那一步的**前置** —— 不修则**撞通了也量不了分**
  （GLM 亦点名：「不修就不能宣称最终 correction 成绩成立」）。⭐ **且它不依赖 sol 讨论，可与之并行。**

> ## ⛔ 开工自检
> 1. ⭐ **先完整读 `AI_agent/CLAUDE.md`**（§0 / §5#8 / §5#12），再读本单。
> 2. `pwd` = `/workspaces/EnergyPlus-Agent-dev`（主树，⛔ 不建 worktree）· 记下开工 HEAD。
> 3. **自己复现**故障（下 §一），确认属实再动手。
>
> ## ⭐⭐ 关于本单给的候选
> 跨家族「停下上报」累计 **25/25 全是派工方题错**，其中第 25 处正是
> **「我列了两条路却预设了只有这两条」**。⇒ **本单明确授权**：
> - ⭐ **下面的候选清单可能不完备。看到更优的路，直接走它并显著披露。**
> - **停报三条件，任一即停**：① 候选都不成立 · ② 候选都次优而你看到更优解 · ③ **前提本身错了**。

## 一、故障机制（已由 orchestrator 实测确证）

[`score_service.py:360-372`](../../../src/agent/judge/score_service.py#L360)：

```python
plan_sources = {item.floor_id: item.input_id for item in score_bindings.bindings
                if getattr(item, "kind", None) == "plan"}
...
source = plan_sources.get(window.floor_id)
if source is None:
    raise ScoreContractError("score_view_binding_invalid", ...)
```

- `plan_sources` 的**键**来自绑定表 ⇒ **gt 侧命名**：实测 sm25 = `F1` / `F2`
- 查的是 `window.floor_id` ⇒ **产物侧命名**：实测 sm25 = `floor_1` / `floor_2`
- ⇒ 必然取不到 ⇒ **整份判分 `rejected`，十个判据一个都没跑**

⛔ **关键约束**：绑定表生成器 [`build_score_view_bindings.build(run_dir, gt_file, input_ids)`](../../../scripts/tool_scripts/build_score_view_bindings.py#L46)
**只吃 `view_manifest` + `gt`，看不到 correction 产物** ⇒ 映射**不可能**从它那里凭空来。

## 二、⭐ 一条已经验证过的候选（orchestrator 实测，但**不是命令**）

**映射链其实已经存在，藏在窗自己的证据引用里**：

```
window.floor_id ──(窗自己的 provenance.*.source_ids，如 "1f_view/G02")──> input_id
input_id ──(绑定表 binding.input_id → binding.floor_id)──> gt 侧 floor_id
```

**实测（sm25 R0 的 accepted 产物）**：

| 产物 floor_id | 其窗的**平面**引用 | 扇数 |
|---|---|---|
| `floor_1` | **全部** `1f_view` | 15，**零例外** |
| `floor_2` | **全部** `2f_view` | 16，**零例外** |

绑定表：`1f_view → F1` · `2f_view → F2`。

⭐ **这条的好处**：⛔ 不引入任何新的隐含假设（不靠**序号**、不靠**层高 z**、不靠命名相似）；
用的是**已经存在、且已被 B5 证据链门校验过**的引用；失败时**能响亮失败**。

⚠️ **它的边界，必须由你处理并写明**：
- 某扇窗**没有**平面引用 ⇒ ？（orchestrator 认为应**响亮失败**，⛔ 不许猜）
- 同一 `floor_id` 的窗引用了**多张**平面图 ⇒ ？（矛盾，应响亮失败）
- **零窗的楼层** ⇒ 映射推不出来，但也没有窗要判 —— 这是不是问题？
- ⭐ **立面呢**？绑定表另有 `ElevationScoreViewBindingV1.floor_ids`（复数），本单是否要一并处理？
  （⚠️ 注意 **F-89**「一张立面跨两层就整份过滤」是**另一条缺陷**，⛔ 别混进来）

## 三、其他候选（⛔ 同样不是命令，且清单不完备）

| | 做法 | 已知代价 |
|---|---|---|
| **按层高 z 匹配** | gt `z_floor_m` ↔ 产物 `z_floor` | ⛔ 引入容差 ⇒ 一个没人签字的阈值（[[silent-default-threshold-behind-otherwise-conclusions]]）|
| **按序号匹配** | 两边都排序后逐个对应 | ⛔ 把「层序一致」偷设成前提；跨层缺图时静默错位 |
| **让 correction 产出 gt 的 id** | —— | ⛔⛔ **违反 gt 铁律**（产物侧绝不得知道 gt）—— 这条**明确排除** |
| **绑定表同时记两套 id** | 给生成器加产物输入 | 改变它的职责边界；且它现在的身份是「gt 侧应试范围」，混入产物命名会污染身份 |

## 四、⭐⭐ 验收判据（第 1 条最重要）

1. ⭐⭐ **必须真的判出分，⛔ 不是「不再抛异常」。**
   跑 sm25 那份现成产物的判分，**贴出实际的判分结果**（十个判据都要有读数）。
   ⚠️ 这条是硬的：一个只把异常吞掉的修法同样能让测试变绿，
   而本项目有明确教训 —— **只有负向断言的门 = 结构上不可观测**（[[gate-with-only-negative-assertions-is-unobservable]]）。
2. **新锁必须先证明会红**：在你的修法之前跑一次，它应当红；修完转绿。**两段输出都要贴。**
3. **响亮失败的那条路也要有锁**：构造一个「窗没有平面引用」或「引用矛盾」的夹具，
   证明它**响亮失败**而不是静默取默认值。
4. **全量绿** + **提交只点名自己改的文件**（⛔ 严禁 `git add -A`）+ ⛔ 不 push。

## 五、⛔ 不在本单

**F-89**（一张立面跨两层就整份过滤）· **F-98**（判分对浮点末位敏感）· 一体改相关的任何东西。
