# 跨家族复核单 · B4-① affine 两端空间合同

- **日期**：2026-08-29 · **复核方**：GLM（跨家族）· **施工方**：Claude 执行档 · **派工方**：orchestrator
- **被审 commit**：**`dc8821b`**（`08.29x_AffineTwoEndSpaceContract`，分支 `08.23_AsDrawnReading`，⛔ 未 push）
- **原派工单**：`AI_agent/logs/reviews/request/2026-08-29_b4_affine_space_contract.md`
- **⛔ 只看**：原派工单 + `git show dc8821b` + 你自己跑出来的测试输出。⛔ 不看施工方自述。

---

## 一、⚠️ 先说两条**派工方（我）的题面错**，请当成「可能还没改干净的口子」去攻

1. ⛔ **我写「新 request 声明 v4 并绑定空间」——这条不能照做。**
   施工方实测：`tarch_normalize.py` 的 `_validate_raster_intents` 开头是
   `if request.request_version != 3: return`，且全文件 **7 处**以 `request_version == 3` 当门
   ⇒ **加 v4 会静默跳过签字标定校验（fail-open）**。**orchestrator 已独立复核属实。**
   它改用**排除集合 + tripwire 测试**。**请你判这个替代方案够不够。**
2. **我的表格类名写错**：manifest 那个 `world_from_source_m` 在 `PlanViewBindingV1`，
   不在 `GtExtractionManifestV1`；且是**四个字段位、不是三个**（`pixel_to_source_m` 有两处）。

⇒ **累计派工方题错 41 次**（今日三次：F-126 的 R2 · 并行跑测窗口 · 本单的 v4）。

---

## 二、⭐ 请你回答的五问

### 1. ⭐⭐ `Affine2DV1` 做成**类属性、不上线**，这个决定对吗？
理由是「**只有一个生产者、一个应用点，两端恒定**」，且加 wire 字段会移动 `preimage_sha256`
（该值以 `transform_sha256` 落在 **10 份 `score_vs_gt.json`** 里）。
**问**：这个「唯一生产者/应用点」的判断经得起推敲吗？将来多一个生产者时，
类属性会**静默给出错误的两端**吗？有没有锁在那一刻变红？

### 2. **签名保住了，但会不会是「空间根本没落到线上」造成的空转？**
施工方做了反空转实测（不 pop 则 sm25 request 变 `8d844bc6…`、sm24 manifest 变 `8a69ac33…`）。
**请抽验这一条**，⛔ 别照收。

### 3. ⭐ **再找一种能骗过这批新锁的真实错误形态。**
⛔ 不是造合成 bug，是「哪种真实改法会让它们全绿而缺陷仍在」。
（上两轮你分别找到了 `os.walk` 回退腿、成功路径滤 BLOCK —— 就按那个标准。）

### 4. **13 条「会红」/ 4 条「不会红」的自评准确吗？**
施工方自己把锁分成了三类（13 条真判据 / 4 条非判据 / 1 条将来才有牙）。
**请抽验其中至少 3 条**，特别是它标为「⭐ 今天这个 payload 静默通过」的那条。

### 5. **换同形输入仍走不通吗？**
只验证 sm24 那一对 1000× 不算数。换 sm25、换 `pixel_to_source_m` 的两个字段位、
换立面（`Affine1D`，⭐ **施工方自报同病未治**）—— 这条路是不是**仍然**走不通？

---

## 三、事实清单（orchestrator 已独立复现，⛔ 请自己再跑）

| | 读数 |
|---|---|
| `git diff --numstat HEAD~1` | `affine_space.py` 256/0 · `gt_manifest.py` 52/0 · `reading_typed_adapter.py` 14/0 · `score_schema.py` 24/1 · `tarch_converter_schema.py` 35/0 · `test_affine_space_contract.py` 310/0 |
| **主控权威全量** | **`3167 passed / 13 xfailed / 0 failed`** · `PYTEST_EXIT=0` · 1336.61s · `-n 6` · ⛔ 无 `-m` |
| `.pth` 前后哨兵 | `58f547fa…` 两次同值 |
| 算术 | **3146 + 21 = 3167**（`--collect-only` 实读；21 条全来自 B4，GLM 那单 +0）|
| ⭐ 签字哈希（我独立算） | sm25 request `d738d0ac…` · sm24 request `ae0fec08…` · sm24 manifest `c40cbc8b…` —— **盘上=重算，逐位相同** |
| ⚠️ 存量更正 | **不是三份**：sm25 只有 request（无 manifest）· **sm21 两样都没有** |

---

## 四、⭐ 施工方新报的两条，请一并判是否成立

1. ⭐⭐ **`converter_sha256()` = `sha256(tarch_normalize.py 自己的字节)`** ⇒ 那个文件**改一个字的注释**
   就触发 5 条签字锁红；⛔ **反过来 `tarch_converter_schema.py` / `gt_manifest.py` 改了却不进这个指纹**。
   **问**：这算不算一个缺口（实现指纹只盖一个文件，而行为依赖好几个）？本单正好改了后两个。
2. **`Affine1D` 同病未治**（立面 `world_along_from_source_m` / `world_z_from_source_m`，同样零空间标注）。

## 五、裁决格式
`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` / `REJECT`，逐条标阻断/不阻断，**每条给可复现命令 + 实测数字**。
写进 `AI_agent/logs/reviews/verdict/2026-08-29_b4_crossreview_glm_verdict.md`（**唯一允许你写的文件**）。
⛔ 只读复核，⛔ 不改工作树 · ⛔ 绝对不许 `pip install -e .` · 跑测 `pytest -n 6`（⛔ 不用 `-n auto`）。
⚠️ **现在没有别的席位在飞** ⇒ 你可以放心跑全量，但跑测期间⛔ 不要改任何文件。
