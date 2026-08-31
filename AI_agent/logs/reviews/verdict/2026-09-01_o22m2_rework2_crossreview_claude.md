# 跨家族审 · **②-2 模块 2 第二轮返工**（载荷来源闭合 + 不可承载通道拒 present）

- **日期**：2026-09-01 · **施工方**：GLM 家族（`2148409`）· **复核方**：**Claude 家族 / orchestrator**（跨家族）
- **被审对象**：`2148409`（`evidence_contract.py` +128 · `test_o22m2_evidence_contract.py` +239/-1）
- **审阅方式**：⛔ 不看执行者自述；只看返工单 + diff + 测试输出 + **复核方自己的三条检查**
- **隔离**：三席在飞 ⇒ **全部实验在独立 worktree** `58bb59f`，**主树零改动**

## 裁决：**APPROVE-WITH-FINDINGS**（阻断 **0** 条 · 不阻断 **2** 条）

---

## 一、⭐⭐⭐ 返工审的三条检查（⛔ 前两条只验证「这个例子修好了」，第三条才验证「这类缺陷修好了」）

### ① 新件把两条阻断关掉了 —— ✅
`pytest -n 4 tests/test_o22m2_evidence_contract.py` = **33 passed**（旧 30 + 新 3）。
三条新锁按名字对得上返工单的两条阻断：
`test_b1_payload_must_come_from_the_channels_declared_source`（B-1 正向）·
`test_b1_declared_source_without_payload_needs_a_scoped_debt`（B-1 **反向**，验收 2）·
`test_b2_a_channel_without_payload_carrier_can_never_be_present`（B-2）。

### ② 新门确实在**校验器**里，不是在测试工厂里 —— ✅（复核方独立复跑 neuter 对撞）
把 `validate_evidence_bundle` 整个 neuter 掉：
```
基线            : 33 passed
neuter 之后     : 16 failed / 17 passed
```
**16 条红里包含全部三条新锁**，其余 13 条与返工前名单一致。
⇒ 验收 5 独立成立：**若新门写在测试工厂里，neuter 后它们不会红。**

### ③ ⭐⭐⭐ **换同形输入 —— 仍走得通**（见 §二，这是本次审的主要产出）

## 二、不阻断 N1 · **`absent` 却带着载荷：第三个载体，实测放行**

⭐ **这条是施工方自己点名留给主控定夺的**（它在执行档里写「第三方向至今无门、未登记」）。
**复核方独立构造并实测，确认它是活的，不是假设**：

```
基线正常 bundle 通过 ✅   wall_claims=2  face_dispositions=4  opening_claims=1
  channel_status = [dimensions:absent, elevation_openings:absent,
                    plan_openings:present(tiny), room_roles:absent, walls:present(tiny)]

同形输入 ① walls 改成 absent + missing_channel debt，而 2 条 wall claim / 4 条 disposition 照旧在包里
   ⇒ ❌ 放行
同形输入 ② plan_openings 改成 absent + missing_channel debt，而 1 条 opening claim 照旧在包里
   ⇒ ❌ 放行
```
**机制**：B-1 与 B-2 两道门**都以 `if status.state != "present": continue` 开头**
（`evidence_contract.py` 的 `_assert_channel_payload_closure` 与 `_assert_channel_source_closure`）
⇒ **只要声明成 `absent`，两道门一起让路。**

⭐⭐⭐ **同一病族的第三次换载体**（[[gate-measures-right-but-carrier-gets-swapped]]）：
| 轮次 | 载体 |
|---|---|
| 一轮 | **全局空载荷** —— 说 present 却什么都没有 |
| 二轮 | **错误来源的载荷** —— 说来自 A，其实来自 B |
| **三轮（本条）** | **`absent` 却带着载荷** —— 干脆不声明，门就不看了 |

⇒ ⛔ **不阻断本次返工**（返工单只要求 B-1/B-2，施工方做到了，而且是它自己把第三条指出来的）；
⇒ ✅ **另立单**，已写 → [`2026-09-01_o22m2_absent_with_payload_dispatch.md`](../request/2026-09-01_o22m2_absent_with_payload_dispatch.md)。

## 三、不阻断 N2 · scoped 豁免是**超集语义**（施工方自报，复核方确认）

`unscoped = (declared - payload) - scoped[channel]`。
若一条 scoped debt 声称「来源 X 本次没有载荷」而 **X 其实产了载荷**，X 本来就不在 `declared - payload` 里
⇒ 减它是空操作 ⇒ **这句不实的声明被静默接受**。
⚠️ 危害有限（它只会让台账多一句假话，不会放行错误载荷），⛔ 本轮不要求改；
⭐ 但**登记**：将来若有人拿 debt 台账当事实读，这里就是它不可信的地方。

## 四、机械核对（其余验收项）
| # | 验收项 | 结论 |
|---|---|---|
| 1 | B-1 两反例响亮 + 正常 bundle 仍绿 | ✅（基线三份产物照过，本地复跑 33 passed）|
| 3 | B-2 反例响亮 + **合法出口 `walls=present + zero_payload_channel(walls)` 仍放行** | ✅（`test_f1_...` 在 neuter 名单里，说明那条出口是被量着的）|
| 4 | 先绿后红自证 | ✅（新锁均含改动前放行的前提断言）|
| 6 | 模块 3 一并跑 | ✅ 76 passed（m4 22 + m3 21 + m2 33）|
| 禁令 2/3 | 未动 `vector_contract.py` / `pipeline.py` / `judge/` / `evidence_adapters.py` | ✅ `git show --numstat 2148409` 只有 2 个源文件 + 3 份文档 |

## 五、给主控的一句话
两条阻断真修了，而且**修在校验器里**（neuter 独立验过）。
**本次审最值钱的不是确认它修好了，是第三条检查**：同一病族换第三个载体——`absent` 却带着载荷——**实测仍然放行**，
而这条是**施工方自己交出来的**。⇒ 收口，另立单。
