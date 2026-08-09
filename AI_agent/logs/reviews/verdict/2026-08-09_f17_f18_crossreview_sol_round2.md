# 交叉审裁决（第二轮 · 复核返工）· F-17 + F-18

- **日期**：2026-08-09
- **审阅方**：`gpt-5.6-sol` / effort high（只读）
- **被审**：返工提交 `bab4d09`（第一轮裁决 = [APPROVE-WITH-CHANGES](2026-08-09_f17_f18_crossreview_sol.md)）
- **⛔ 复审理由**：返工同样由 orchestrator 亲手完成 ⇒「谁写谁不批」问题原样存在

> **⭐ 第二轮再次证明了这道环节的价值**：orchestrator 返工时**新引入**了一条
> 过度泛化的表述（把一次实测观察写成「2 的幂 ⇒ 永不产生 ULP」的普适定律），
> sol 给出反例证伪（`p1=2.6317878, L=8, x=7.877522392` ⇒ 偏差 −8.88e-16），
> orchestrator 已独立复算证实并收窄表述。
> ⇒ **同一类错误（从测量过度外推）在同一批里连犯两次，两次都是交叉审抓的。**

---

# 总裁决：APPROVE-WITH-CHANGES

**0 BLOCKER / 0 MAJOR / 1 MINOR**

上一轮的 1 MAJOR + 3 MINOR 均已实质解决，三向 neuter 也可信。唯一遗留是返工新引入的“2 的幂”规律表述过度泛化；不影响生产修法，但会误导后续夹具设计。

## MINOR

1. “宿主线长度为 2 的幂 ⇒ 永不产生 ULP”不成立。

   [测试说明及用例](</workspaces/EnergyPlus-Agent-dev/tests/test_f18_window_host_float_tolerance.py:170>)和 [plan.md](</workspaces/EnergyPlus-Agent-dev/AI_agent/plan.md:780>)把规律写成了无条件命题，但真实算路是：

   `t = ((x - p1) * L) / L²`，然后 `x' = p1 + t * L`

   当 `L=2^k` 时，乘除缩放通常无损；但 `x-p1` 和最后的 `p1+…` 仍可能舍入。仓库真实 helper 的正常建筑尺度反例：

   - `p1=2.6317878`
   - `p2=10.6317878`
   - `L=8`
   - `x=7.877522392`
   - 往返得到 `7.8775223919999995`，偏差 `-8.881784197001252e-16`，即 1 ULP。

   当前测试实际只证明了“沿轴原点为 0、长度 8、该组 span”会精确往返。建议将名称和说明收窄为“零原点、正常数值范围下的 2 的幂缩放”，不能再称“任何 2 的幂宿主线永不产生 ULP”。

## 上一轮 findings 复核

1. **MAJOR-1：已解决。**

   四个正向用例均有真实分辨力：

   - `[0,15] / 11.36`：偏差 `-1.776e-15`
   - `[0,15] / 2.19`：偏差 `+4.441e-16`
   - `[0,7.88] / 2.19–5.55`：两端均有偏差
   - `[0,7.88] / 3.44–4.64`：高端偏差 `-8.882e-16`

   将比较器在内存中恢复为精确比较后，4/4 均因 `world span` 转红。

   [_round_trip_differs](</workspaces/EnergyPlus-Agent-dev/tests/test_f18_window_host_float_tolerance.py:84>) 的前提断言也有效：把垂直夹具退化为当前那个零原点 `[0,8]` 样本后，`_round_trip_differs=False`，测试会在进入容差断言前直接报 `fixture premise broken`。

2. **MINOR-2：已解决。**

   [eps_xyz](</workspaces/EnergyPlus-Agent-dev/src/agent/correction/window_host.py:647>) 使用 `(*eps_xy, 0.0)`；z 又确实由 [window_verts_on_line](</workspaces/EnergyPlus-Agent-dev/src/agent/geometry/modelling.py:412>) 原值复制。

   `z + 1e-12` 当前被判为 `vertices` 问题。把 z 临时恢复成 `1e-9` 容差后，F-18 文件结果恰为 **1 failed / 10 passed**，只红 `1e-12-exact`。

3. **MINOR-3：已解决。**

   [_same_resolution_representation_close](</workspaces/EnergyPlus-Agent-dev/src/agent/correction/window_host.py:486>) 是上一轮明确接受的语义化命名方案。目前只有三个调用点，全部位于 `window_host_claim_issues` 的同一事实回比路径，没有候选匹配误用。无需强制局部化。

4. **MINOR-4：已解决。**

   [顺序无关锁](</workspaces/EnergyPlus-Agent-dev/tests/test_f17_cross_axis_envelope.py:281>) 对矩形和 L 形分别比较：

   - footprint rings
   - cell polygon/bbox
   - 排序后的 moved audit

   当前正序/逆序完全相等。以内存方式恢复旧“边移边判”实现后，矩形、L 形及两格顺序测试共 **4/4 转红**。

## 验证结论

- 当前目标测试：**16 passed**
- 精确判据 neuter：**4/4 红**
- z 容差 neuter：**恰好 1 红**
- F-17 旧 relocate neuter：**4/4 红**
- 未发现生产代码新缺陷
- 未修改文件、未 commit、未 push

审阅期间分支被外部推进到 `e9ae474`，但该提交只改 `plan.md` 和新增设计文档；本裁决仍严格针对 `bab4d09`，目标实现与测试未被后续提交改变。
tokens used
