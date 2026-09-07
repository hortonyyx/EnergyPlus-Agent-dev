# 复核单 · G-c 返工 1 跨家族复核（GLM 家族）

> **施工方 = GPT-6 Astra**（`codex exec`，effort `xhigh`）· **你 = GLM 家族独立复核方**（用户 2026-09-07 指定）
> ⛔ 你不是作者，⛔ 不得替它改代码。

## 〇 与安全攻防无关的声明

本单是**建筑 CAD 图纸几何入库 + 单元测试维护**。「锁 / 门 / 负样本 / 存货 / 攻击 / 变异」
是本项目对**单元测试判据**的固定叫法，⛔ 与网络安全、攻防、漏洞利用无关。
敏感词请读作「测试断言 / 测试用例 / 反例夹具 / 修改源码后重跑」。

## 一 在哪、审什么

- **工作目录 `/tmp/gc_rw1_review_glm`**（detached HEAD `f0437dba`）。
  ⛔ 不要动主树、⛔ 不要动 `/tmp/gc_rework_astra`、⛔ 不要动 `/tmp/gc_snap_ladder`。
- **审阅范围 = 5 段返工提交 `fd5c3388..f0437dba`**（⛔ 其前的 8 段是上一轮 G-c 内核，不在本轮范围）：
  ```
  633bdc81  T1_retire_form_b
  035fc237  T2_rebuild_negative_stock
  b6664f22  T3_derive_scan_inventory
  50ee08b0  T4_enumerate_fixture_inventory
  f0437dba  T2_room_completeness
  ```
  改动面：`tests/` 8 个文件 + 新增 `tests/gc_rework1_inventory.md`（189 行对照表）。
- **必读（⛔ 一律用主树绝对路径 —— 本单写在被审提交之后，按构造不在你树里）**：
  - 本单：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/request/2026-09-07f_Gc_rework1_crossreview.md`
  - 派工单（**含 T1 勘误段**）：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/request/2026-09-07d_Gc_rework1_dispatch.md`
  - 交件（2068 行）：`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/execution/2026-09-07d_Gc_rework1_execution.md`

### 开工先自检

```sh
cd /tmp/gc_rw1_review_glm
git log --oneline -1                       # 必须 f0437dba
python -c "import tests.deferred_projection_ledger as m; print(m.__file__)"
# ⭐ 必须落在 /tmp/gc_rw1_review_glm。落别处 ⇒ 停下上报。
```

⛔ 绝不许跑 `pip install -e .` 或任何写 `site-packages` 的命令。⛔ 跑测一律 `-n 6`。

---

## 二 ⭐⭐⭐ 派工方（主控）已经核过什么、⛔ 【没核】什么

**⛔ 别把「主控核过」当成整块核过了。你的价值在下表右栏。**

| ✅ 主控已机械核实（⛔ 你不必重做，但可证伪） | 读数 |
|---|---|
| 独立全量（我自己跑的，非转引） | **`4009 passed / 0 failed / 2 skipped / 13 xfailed`**，469.38s、`-n 6`；跑前跑后 `__file__` 均落 `/tmp/gc_rework_astra`；`.pth` 哈希 `5198f6f9…` 未动 |
| 数目对账 | 主线 `3989` + G-c 阶梯本身净增 `20` = **`4009`**；本轮返工**零净增测试**、把 6 红转绿 |
| 对照表真实性 | 168 行、**零重复**、**全部对得上真实存在的测试函数**、涉 12 个文件 |
| 对照表**外延完整性** | 主控用独立 token 扫描（13AD/13AE/13AF·`rev-`·`axis_snapped_lines`·`non_orthogonal_lines`·`AXIS_SNAP_MAX_*`·`tarch_wall_free_end`·`boundary_ring_losses`·`SM25_DEFERRED`）得 67 个命中函数，其中 10 个不在表内，**逐个查完全部是合法排除或我自己的扫描假阳性** ⇒ 零缺口 |
| T1 是否只改数字 | ⛔ 否：裁决正文改写为「RETIRED with G-c」+ 机制，旧文降格 `Historical adjudication`；未动 `SM25_DEFERRED_F157_UNAVAILABLE_COUNT` |
| T2 是否改期望值了事 | ⛔ 否：函数内构造合成 unsigned 记录，且**期望集从独立路径（clean 答案的 `face_line_handles`）推出**，再要求精确集合相等 |
| 落库纪律 | 5 段各自成段 · 工作树干净 · **零孤儿件** |

| ⛔ 主控**没有**核的（= 本轮复核的主战场） |
|---|
| **① 席位声称的每一次「变异后变红」，我一次都没独立跑过** —— T2/T4 的牙全部只有它的自述 |
| ② T3「48 是坐标出现次数、13AF 贡献两个端点」这条**推导**的正确性 |
| ③ T4 额外修的三处（`after_p1` 豁免方向 / facts 成功路径 BLOCK 库存 / 每次仅删一条 snap 的反例）|
| ④ 类 A 第三条（`test_external_quantities_are_bit_identical` 身份串）重建得对不对 |
| ⑤ 交件 2068 行里的逐条原始输出与实际是否一致 |

---

## 三 ⭐⭐⭐ 三条复核（缺一不合格）

1. **改动前复现得出**：在 `fd5c3388` 上，那 6 条确实红（主控读数：`6 failed, 47 passed`）。
2. **改动后复现不出**：在 `f0437dba` 上确实绿。
3. ⭐⭐⭐ **换同形但不同的输入仍走不通 —— 你自己造，⛔ 不许只用它造的。**

---

## 四 逐条核这五件事

### 1. ⭐⭐⭐ **牙是不是真的（本单头号任务）**

派工单 T2/T4 要求：**每条重建的负样本必须实测「不加这处改动，这门本来红不红」**。
席位自述「三个同形变异在 T4 前 `3 passed`、T4 后 `3 failed`」，并把变异脚本
（`test_T2_red.py` / `test_T4_sensitivity.py`）**全文嵌进了交件 §复现脚本原文**。

⛔ **不许转引它的读数。** 请：
- 把那两个脚本从交件里取出、在**你自己的树**里跑一遍，确认「正确代码下的红/绿」与它写的一致；
- ⭐ 更要紧：**对每一条被重建/重推的锁，你自己另造一个变异**（⛔ 与它的不同），
  确认那把锁**确实会红**。⛔ 「测试绿了」不等于「断言被求值了」
  （[[gate-with-only-negative-assertions-is-unobservable]]：问「不加这处改动，这门本来红不红」）。
- 名单（⭐ 至少覆盖这 6 把 + T4 额外三处）：`test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na` ·
  `test_l4_discarded_non_orthogonal_segments_are_itemised` · `test_external_quantities_are_bit_identical` ·
  `test_the_scan_goes_red_when_the_snap_is_removed` · `test_projected_ring_identity_holds_with_no_tolerance_at_all` ·
  `test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches`。

### 2. ⭐⭐ **T3 的基线是【推导】还是【抄观测值】**

派工单写死：⛔ 不许把 46 改成 48，要**重新推导这个基线钉的是什么**。
席位的答复是「**48 不是面线条数，是坐标出现次数；13AF 贡献两个端点**」——
即它认为**派工方（我）把这个桶的语义说错了**。
⇒ **请独立判断这条更正对不对**：那个桶到底在数什么？`46 → 48` 的 +2 是不是就是 13AF 的两个端点？
⛔ 若它错了，那是阻断（等于换了个说法抄观测值）。

### 3. ⭐⭐ **T4 那三处「额外修复」是真缺陷还是自造工作量**

`after_p1` 豁免方向 · facts 成功路径 BLOCK 库存 · 每次仅删一条 snap 的反例。
逐条问：**不修它，会漏掉什么？** 若「不修也没有任何真实场景会错」，那就是自造工作量（不阻断但要记）。

### 4. **交件的原始输出与实际是否一致**（抽查即可，⛔ 不必逐行）
随机抽 3 处它贴的命令输出，在你树里重跑，看对不对得上。**对不上就是阻断**。

### 5. ⭐ **它自己点名的「最薄弱的一处」你同不同意**
它写：最薄弱 = T4 外延判断，「若某个**动态 helper 间接读了当前 facts** 而源码看不出这层依赖，
仍可能漏掉另一把空转锁；**全量绿不能替代这层判断**」。
⇒ **请就这一条给独立意见**：这个风险真实吗？有没有便宜的办法把它变成可观测的？

---

## 五 停下上报（分层）

**本项目 70/70 的「停下上报」全是派工方的题错，记功不记过。**

**A 类 · 承重前提错 ⇒ 立刻停**：① 自检 `__file__` 落点不对；② `fd5c3388` 上不是 6 红 / `f0437dba` 上不是全绿；
③ 你判定**某把锁其实没有牙**（§四-1 抓到）；④ 你判定 T3 那条语义更正是错的；
⑤ 你认为本单**题面**就不对。

**B 类 · 外围错 ⇒ 记录并继续**：本单引的某个数字/行号对不上 · 你对某条「无需动」的判断有异议。

⚠️ **一次跑出来的红不是证据** —— 同树重跑至少 2 次再下结论。

---

## 六 交件格式

裁决书写到
`/workspaces/EnergyPlus-Agent-dev/AI_agent/logs/reviews/verdict/2026-09-07g_Gc_rework1_crossreview_glm.md`
（⭐ 主树绝对路径）。必须含：

- **裁决** `APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` + **阻断 N / 不阻断 N**。
- §三 三条复核**各自的原始命令与输出**。
- §四-1 **你自己造的变异逐条列出**（哪把锁 · 你怎么变的 · 红了没有），⛔ 不许只写「已验证」。
- §四-2 你对 T3 语义的独立判断 + 依据。
- §四-3/4/5 逐条作答，每条注明**是量的还是推的**。
- **全量读数**：`python -m pytest -q -n 6 -p no:cacheprovider`，跑前跑后各核一次 `__file__`。
  ⭐ 主控参照 = **`4009 passed / 0 failed / 2 skipped / 13 xfailed`**（469.38s）。
- **你自己最薄弱的一处判断**是什么。
