# 派工单 · F-5【BLOCKER】B5 窗源解析读错字段名 ⇒ **任何带窗的合规识图产物都过不了 1_correction**

- **日期**：2026-08-05
- **派工方**：orchestrator（Opus 5）
- **施工席**：GLM-5.2（**插队到 F-2c / r4 之前做**——它挡着用户的主线目标）
- **基线**：`0256060` = 2177 passed / 10 xfailed / 0 failed

---

## 1. 缺陷（一句话）

**产品契约写的是 `x_range_m` / `y_range_m`，消费者读的是 `x_range` / `y_range`。**
⇒ 取到 `None` ⇒ `_interval` 抛 `source_identity_invalid` ⇒ **1_correction 直接死**。

## 2. 逐条证据（orchestrator 实测 + 读码，均可复现）

**契约侧（两处独立声明，口径一致）**：
- `src/agent/reading/schema.py:36`：*"geometry is a free dict (line: p1/p2/thickness_m; **rect: x_range_m/y_range_m**)"*
- `skills/intake_pipeline/0_reading/guide.md:175` 与 `:360`：
  *"Elevation window strokes use `geometry.kind="rect"` + **`x_range_m` / `y_range_m`**"*

**产物侧（真实产物，两代都一样）**：
```json
{"id":"S11","pen":"window","geometry":{"kind":"rect","x_range_m":[1.24,3.64],"y_range_m":[7.76,8.0]}}
```
（07-07 的 sm21 产物、以及今天新跑的产物，**都是 `_m` 后缀**。）

**消费者侧（读的是没有 `_m` 的名字）**——`src/agent/correction/window_sources.py`：
```python
:291  world_x_interval=_interval(geometry.get("x_range"), ...)      # plan
:292  world_y_interval=_interval(geometry.get("y_range"), ...)      # plan
:297  z = geometry.get("z_range")                                   # elevation
:298  local_along_interval=_interval(geometry.get("x_range"), ...)  # elevation
```

**实跑证据**（`run_2026-08-05_smoke_downstream_r2`，输入 = 07-07 那份已知满分产物）：
```
WindowResolverInputError: source_identity_invalid: {'observation_id': 'S11', 'field': 'x_range'}
  src/agent/correction/window_sources.py:269 _interval
```

## 3. ⛔ 为什么全仓 2177 绿却挡不住它 —— **本项目招牌缺陷的最纯形态**

**测试夹具全部照抄了实现的错误拼写**：
```
tests/test_c2_b5_host_resolution.py:249   plan_geometry={"x_range": [2.9, 3.1], "y_range": [4.0, 5.0]}
tests/test_c2_b5_host_resolution.py:264   elevation_geometry={"x_range": [1.0, 2.0], "z_range": [1.0, 2.0]}
tests/test_c2_b2b_envelope_transform.py:68 "x_range": list(window.span), ...
（还有多处）
```
⇒ **实现与夹具自洽地用着同一个错名字，测试永远绿；而任何真实产物必崩。**
**⇒ 由此可断言：B5 窗源这条路，从来没有在一份合规的真实识图产物上跑通过。**

## 4. 要修

### F-5a · 消费者按契约读字段
`window_sections`（`window_sources.py:286-300` 一带）改读 **`x_range_m` / `y_range_m`**。
- **立面**：契约里立面窗的竖直区间就是 **`y_range_m`**（图像局部坐标），
  ⛔ **不存在 `z_range` 这个契约字段** —— 现在这行读 `z_range` 恒为 `None`，
  等于**立面窗的 sill/head 证据从来没有真正进过这条链**。按契约改成 `y_range_m`，
  并核一遍下游拿到这个区间之后的语义（局部 z，由 correction 映射到世界）。
- ⛔ **不许反过来改契约**（schema.py / guide.md / 所有已落盘产物都用 `_m`，改契约等于作废整个语料）。
- ⛔ **不许写"两个名字都认"的兼容层** —— 那是把一个错名字合法化，且会让下一个人不知道以谁为准。

### F-5b · 把夹具钉到契约上（否则这类错必然复发）
- 新增一条锁：**用真实合规产物**（建议直接取
  `case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest/0_reading/attempts/001/output.json`
  里的窗 stroke，或按 `guide.md:175` 的示例构造）跑通 `build_verified_window_inputs_from_run`，
  断言 plan 与 elevation 两个通道**都拿到非空区间**。
- **把既有夹具的拼写一并纠正**（`test_c2_b5_host_resolution.py` / `test_c2_b2b_envelope_transform.py` 等）：
  改完之后它们仍必须绿；**若改成契约拼写就变红，说明那条测试原本就在测一个不存在的世界**，
  ⛔ 不许为了让它绿而回退拼写 —— 停下上报。
- ⭐ **加一条结构性的锁**：夹具里出现的 geometry 字段名必须**来自契约的单一来源**
  （例如从 `guide.md`/schema 机械导出的允许字段集断言），⛔ 不许再手抄字符串。

## 5. 锁 / 验收

1. 摘掉 F-5a 的修法 ⇒ 新的真实产物锁必红；
2. **四格实测**：{plan, elevation} × {真实产物, 缺字段的坏产物} —— 真实产物拿到区间、坏产物照旧 fail-closed；
3. 自己跑 neuter，红了哪几条、有没有连带，原样进简报；
4. 全仓三数字（基线 **2177 / 10 / 0**）。
5. **交付前请自己跑一次真链路复现**：
   `python scripts/tool_scripts/run_stage.py --base-dir case_tests/e2e_tests --date 2026-08-05 flow sm21_anchor run_2026-08-05_smoke_downstream_r2 --judge off --geometry auto --to 2_modelling`
   —— 它现在死在 S11；修好后至少要能过 1_correction 进 2_modelling。**把这条命令的前后输出贴进简报。**

## 6. 交付 / 边界

- commit（`08.05_<英文标签>`，⛔ 不 push，⛔ 只 add 自己改的文件）；
  简报 `AI_agent/logs/reviews/execution/2026-08-05_f5_window_source_fields_glm.md`。
- ⛔ 不碰识图侧产物、不碰 gt、不碰判卷。
- 有异议停下上报（尤其：如果你发现 `z_range` 在别处确有契约来源，**先停下说清楚**，别两边都改）。
