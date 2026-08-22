# 派工单 · 立面判卷绑定生成（2026-08-22）

**施工席位**：GLM（glm-5.3）· **复核席位**：GPT 家族（codex，跨家族）· **主控**：Claude（轻门 + 裁决，⛔ 不参与施工）
> 席位由用户 2026-08-22 指定（与主控原提议对调）。⚠️ 已知风险：GPT provider 内容过滤 08-16 曾拦死审阅任务 6 次；
> 若复核发不出去，主控最多改一次措辞，再拦即回报用户，⛔ 不反复试。

---

## 一、任务一句话

让 `scripts/tool_scripts/build_score_view_bindings.py` 能为**立面**产出绑定条目，
使一份完整的六图 reading 可以被权威 typed 判卷器判分。

**当前行为**（可复现）：
```
python scripts/tool_scripts/build_score_view_bindings.py \
  --run-dir case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H2_fullcase \
  --gt case_tests/test_baseline/gt/sm25-L_anchor/gt.json
→ East_view: elevation bindings are not derivable yet (frame transform / along_origin / mirror convention)
```
不产出绑定 ⇒ 六图 run 判分 `kind=rejected / error_code=score_view_binding_invalid`。

---

## 二、⭐ 已由主控逐条核实的前提（**请独立复核；任何一条不成立立即停下上报**）

> ⚠️ 主控本轮已两次把**没核实的话**写成实测事实（编造函数名 · 把错误信息词表当未定项）。
> **下面每条都附了核实方式，请当作【可能错的前提】而不是结论。**

| # | 前提 | 核实方式 |
|---|---|---|
| P1 | **前向投影已存在且已锁**：`world = along_origin + sign × local_x` | `src/agent/judge/elevation_score.py:103-105` |
| P2 | **约定已存在且是单一真源**：`src/agent/correction/facade_convention.py`，`FACADE_WORLD_AXIS` / `FACADE_BASE_SIGN`；judge 是它**被允许的消费者**（该模块 docstring 明写） | 读该模块 docstring 与两张表 |
| P3 | **约定已被强制、不是仅可用**：Va 侧 `_validate_bindings` 独立重算 `world_axis`/`sign` 并在不符时 `_fail` | `src/agent/correction/facade_applicability.py:349-352` |
| P4 | **沿墙零点的取法已存在**：`origin = lo if sign == 1 else hi`，(lo,hi) = 该立面族世界沿墙范围 | `src/agent/correction/window_sources.py:1209` |
| P5 | **gt 侧原料齐备**：每段外轮廓带 `facade_family` / `outward_normal` / `world_along_interval` / `source_footprint_fingerprint` / `projection_surface_keys` | 见 §六 复核命令 |
| P6 | **本案走 `manifest_building_axis` 路**：manifest 立面条目 `direction_semantics="building_axis"`、`building_view_direction` 已填；gt `north_axis_deg=None`、`coordinate_frame="building_axis_world_m"` ⇒ 按 schema 校验器，`orientation_output_hash` 与 `adapter_version` 必须为 `None` | `score_schema.py:169-180` + §六 |
| P7 | **judge 侧对 gt 的绑定校验不比对指纹**（只校验层号 / 视图种类 / 立面族 / 源引用可达性）| `score_inputs.py:140-179` |
| P8 | **这些图纸未镜像**（8/8 立面 / 2 栋楼实测）⇒ 可填 `mirrored=False` / `local_x_positive="image_left_to_right"`。⚠️ `normalize_mirror_flag` 对 `"unknown"` **主动拒绝猜**，所以这必须是**有据的选择**而不是默认值 | `python AI_agent/logs/experiments/2026-08-22_elevation_mirror_convention/verify_mirror_convention.py`（退出码 0）|

## 三、已由用户拍板的约定（2026-08-22）

> **每个立面按「站在建筑外面看这面墙」绘制。** 采纳为项目约定。

⛔ **硬约束：绑定的 `world_axis` / `sign` 必须来自 `facade_convention` 模块的函数调用，
不得手抄第五份表。** 该模块 docstring 记载：此前四处各抄一份，**并已真出过一次镜像 bug**。

## 四、字段来源表（17 个，逐个点名）

| 字段 | 来源 |
|---|---|
| `kind` | 常量 `"elevation"` |
| `input_id` | manifest 必需条目 |
| `floor_ids` | gt 该立面视图的 `floor_ids` |
| `facade_family` | gt 该立面视图的 `facade_family` |
| `gt_source_view_ids` | 该立面族的 gt 视图 id（与外轮廓段 `projection_surface_keys` 对得上）|
| `resolved_building_direction` | manifest 条目 `building_view_direction`（P6）|
| `resolution_source` | `"manifest_building_axis"`（P6）|
| `orientation_output_hash` / `adapter_version` | `None`（P6 的 schema 校验器强制）|
| `source_footprint_fingerprint` | ⛔ **见 §五 停下上报 S1** |
| `world_axis` | `facade_convention.world_axis(family)` |
| `sign` | `facade_convention.resolve_sign(family, mirrored=…, local_x_positive=…)` |
| `along_origin` | `lo if sign==1 else hi`，(lo,hi) 取自该族外轮廓段 `world_along_interval` 的并集（P4）|
| `mirrored` | `False`（P8，**须在代码注释里写明依据**）|
| `local_x_positive` | `"image_left_to_right"`（P8）|
| `frame_transform_sha256` | `score_inputs.frame_transform_sha256(binding)`（已有辅助）|

## 五、⛔ 停下上报项（**不许自己拍板，报回来**）

**S1 · 多层立面的 footprint 指纹取哪一个？**
sm25 的 F1 与 F2 外轮廓**几何完全相同**，但每个 x 坐标相差 **3.553e-15 m**（浮点残量），
于是两层 `footprint_fingerprint` 完全不同（`36fb25250aad…` vs `fbfc5e046f79…`）。
而立面绑定只有**一个** `source_footprint_fingerprint` 字段、却要覆盖 `floor_ids=(F1,F2)`。
⚠️ **校正侧的同类推导在这种情况下是直接 raise 的**
（`window_sources.py:1204` → `direction_binding_ring_incompatible`）。
⛔ **不许随便取 F1 的那个。** 请把可选处置与各自后果报回来（例如：量化后再哈希 / 允许每层一个 /
判卷侧自算规范化指纹 / 判定这属于 gt 生成器缺陷需重签），由用户拍板。
（同族已登记缺陷：plan.md「跨层 footprint 用浮点逐位相等比较，残差 3.55e-15 m」。）

**S2 · 凡 §二 任一前提复核不成立，立即停下上报**，⛔ 不要绕过去继续做。
本项目累计 22/22 次「停下上报」都是派工方（主控）的题出错了。

## 六、复核命令（原样可跑）

```bash
# P5/P6 原料
python - <<'PY'
import json
g=json.load(open('case_tests/test_baseline/gt/sm25-L_anchor/gt.json'))
print('north_axis_deg', g['north_axis_deg'], '| frame', g['coordinate_frame'])
print('elev views', [(v['id'],v['facade_family'],v['floor_ids'],v['direction_semantics'])
                     for s in g['sources'] for v in s['views'] if v['kind']=='elevation'])
seg=g['floors'][0]['boundary_segments'][0]; print('seg fields', sorted(seg))
PY
# P8 约定 vs 真图纸
python AI_agent/logs/experiments/2026-08-22_elevation_mirror_convention/verify_mirror_convention.py
```

## 七、必须交的锁（⛔ 缺一不算完）

1. **正向**：sm25 六图 run 能产出 6 条绑定（2 plan + 4 elevation），判分从
   `rejected` → `c2_scored`，且 `channel_applicability` 里 elevation 为 `applicable`。
2. **反向（约定锁）**：把某个立面的 `sign` 人为改反 ⇒ 必须被 Va 的 `_validate_bindings` 拒收（P3）。
   ⛔ 若实测**没有**被拒，说明 P3 不成立 —— 停下上报。
3. **反向（镜像可见性锁）**：⭐ 用户拍板时要的那道门 ——
   **当把产物整体反射后反而与 gt 更吻合时必须报红**，而不是静默算分。
   ⚠️ 这是新判据，**必须在真实夹具上响过**（收录判据同 `reading_process_metrics`：
   好的全绿 + 至少一份坏的红）；造不出会响的夹具就停下上报，⛔ 不许交一道从没红过的门。
4. **neuter 实测**：每把锁摘掉对应实现后必须变红，且**摘的是接线不是机制**
   （主控本轮已在这上面栽过一次：第一版锁只测 helper，摘掉接线仍全绿）。
5. **全量**：主树 `python -m pytest -q -n auto`，与施工前基线对账（当前 **2996 passed / 13 xfailed**）。

## 八、⛔ 明确不做

- 不改 `facade_convention`（约定已定且已被强制）
- 不改 `elevation_score.py` 的投影公式（已存在、已锁）
- 不改识图产物、不改 gt（S1 若指向 gt 生成器，报回来由用户拍）
- 不为 sm25 特化：绑定推导必须对 sm24（单层立面）同样成立

## 九、验收

复核席位（GPT/codex）出 `APPROVE / REWORK / BLOCK`，逐条附**实测命令与输出**，写入
`AI_agent/logs/reviews/verdict/2026-08-22_elevation_score_bindings_gpt_verdict.md`。
⛔ 无实测输出的条目按 MINOR 计。
