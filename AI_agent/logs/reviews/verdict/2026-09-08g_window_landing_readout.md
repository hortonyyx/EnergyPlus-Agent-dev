# 补窗落地读数（主控独立实测，2026-09-08）

## 一 ⭐⭐⭐ 判据达成：窗第一次进入真实归档产物

`run_win_e2e/1_correction/attempts/001/output.json`：

```
attempts        = 1
windows         = 31
  绑段的        = 31
  有 room 的    = 31
  floor 已派生  = 31
corrections     = 31   （全是 window_host_resolution，与 writer 前缀/后缀契约对齐）
```

样本：`1f-win-East_view-O02` → `floor=1f` · `facade=East` · `span=[6.7226, 7.6586]`
· `z=[0.9815, 2.6096]` · `room=1f-c008`

⇒ **平面给「是窗 + 在哪堵墙」，立面给「多高」，两半第一次合成了真实窗对象。**
起点是这条腿产出**一栋没有窗的楼**（`projection_bridge` 的 `windows=[]` 是硬写的）。

## 二 · 主控独立全量：**4085 passed / 0 failed**

⛔ 不转引席位读数，主控自跑：`PYTHONPATH=... /opt/venv/bin/python -m pytest -n 6 -q`
（今早主线基线 4009 ⇒ 本日净增 **76** 个测试）。

## 三 · gate① 现状：`audit_completeness` 已消失，露出两条

```
⛔ correction.evidence_debt_coverage           ← W#7，主控的，预期内
⛔ correction.window_position_evidence_shadow  ← ⭐ 新，见 §四
flag = 0
```

⭐ `correction.audit_completeness` **不再出现** —— 补窗使 finalize 产出 31 条 corrections，
旧病因（「空 corrections」）随之消失。**当初写死「⛔ 不预设它还红、要重新实测」是对的。**

## 四 ⭐⭐⭐ 影子校验指出：我的配对方法有缺口（21/31 不一致）

```
21/31 window(s) failed the independent plan-authority vs elevation-corroborator
pairing decision (cross-check only — does not affect accept/reject)

reject_codes            : {position_evidence_pair_mismatch: 21}   ← 单一原因
max_legacy_span_delta_m : 0.0425 m     （在主控 60 mm 容差之内）
evaluated_conditions    : ambiguity_margin · claim_consistency · distance_within_tolerance
                          · scope_resolution · source_not_reused · ⭐ unique_mutual_nearest
```

### 病因（主控判断，⚠️ 待施工方实测确认）

`as_drawn_windows._plan_rows_for` 的匹配是**单向**的：每个立面洞口找**最近的**平面候选。
而影子校验要求 **`unique_mutual_nearest`** —— A 的最近是 B，**且 B 的最近也必须是 A**。
上下楼窗常常竖向对齐，单向最近很容易配成 A→B 而 B 的最近其实是 C。

⭐ 这正是 [[cross-representation-mutation-must-be-equivalent]] 记过的形状：
**跨表示配对必须穷举两个方向 + 残差硬上限**，而我只做了一个方向。

⚠️ **⛔ 不要把「影子校验不拦路」读成「可以不管」**：它不影响本次 accept/reject，
但它在说**这 31 个窗里可能有 21 个配错了对象**。窗位置错 ⇒ 立面开窗位置错 ⇒ 能耗失真，
而**产物本身看不出来**（每个窗都合法、都绑上了段和房间）。

### ⇒ 下一步（本档不做，留派工）

1. 把配对改成**互为最近**（双向），并补 `source_not_reused` 与 `ambiguity_margin` 两条；
2. ⭐ 判据 = 该影子校验的 `rejected_window_ids` **降到 0**，⛔ 不是「窗数还是 31」；
3. ⚠️ 若改成互为最近后**窗数下降**（某些洞口配不上），那是**真实信息**，
   必须记账 ⛔ 不许放宽回单向。

## 五 · 仍然未知（不变）

`2_modelling` 之后的所有段 + 出分 **一次都没被新腿的几何行使过**。
⛔ 本档的任何读数都**不能**替代总验收。
