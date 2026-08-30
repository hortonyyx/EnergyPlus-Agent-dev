# 返工单 · ②-1d（GLM 跨家族审判 **REWORK / 阻断 1**）

- **日期**：2026-08-30 · **派工方**：orchestrator · **返工方**：**GPT 家族**（原施工方，⭐ 谁写谁改）
- **返工对象** = `8442442`（你交的 ②-1d）· **裁决书**（⛔ 先完整读）→
  [`../verdict/2026-08-30_o21d_crossreview_glm.md`](../verdict/2026-08-30_o21d_crossreview_glm.md)
- **原派工单** → [`2026-08-30_o21d_boundary_condition_dispatch.md`](2026-08-30_o21d_boundary_condition_dispatch.md)
- **基线**：⏸ **待模块 1 席位交件后重取**（⛔ 本单不许与另一个写席位同时在主树写）
- **状态**：✅ 已定稿。⏸ **待启动**

---

## 〇、⭐ 先说：**主体没被推翻，返工量小且纯门侧**

裁决原文：**「返工量小（纯门侧双向对账 + 非空断言，不碰任何一列的值），验收标准我已写成可机械执行的三个『必须红』。」**

⭐ 并且**请求书的头号担忧被你的实现证伪了，这是好消息**：我怀疑「对账门是恒等式」（facts 的
`boundary_condition` 若从转换器 `basis` 派生 ⇒ 自己跟自己比）。复核方**双向实证它不是**：
两个谓词四点实质不同、`derive` 不读任何 stored basis；**改 converter 单条 basis ⇒ 门红且只红 1 条**；
**斜切外轮廓 ⇒ 两列天然分歧、门响亮红**（`unknown:2` · `facts=5 converter=4`）。
⇒ `100/100 全同` 是 **sm25 语料性质**（25 个 ring 全是 4 边轴对齐矩形），**不是恒等式**。

---

## 一、⛔ 阻断 B1（**逐字贴裁决书原文，⛔ 我不转述**）

> **B1 · 对账门的分母由被测方自供，配对集静默缩水时门照绿——0 配对也绿。**

> | 变异 | 结果 | 判 |
> |---|---|---|
> | E1 改 converter 列单条 basis | 红、只红 1 条 | ✅ 有牙 |
> | E5 删 ring 中 1 条边（sequence 断） | 红 `facts_boundary_sequence_not_contiguous` | ✅ 有牙 |
> | E2b converter 同位重复 zone | 红 `converter_zone_pairing_not_unique`（len=2） | ✅ 有牙 |
> | **E3 facts 侧删整个 ring（4 条）** | **`passed=True, paired=96, structural=[]`** | ⛔ 静默 |
> | **E4 facts 侧 `boundary_edges` 全空** | **`passed=True, paired=0, mismatches=0`** | ⛔ 静默 |
> | **E2c converter 多一个 zone（平移 50 m，不被任何 facts cavity covers）** | **`passed=True, paired=100, structural=[]`** | ⛔ 静默 |

> 静默形态**不是捏造的**，各有真实触发路径（均已实测）：
> - **E4 型**：`_boundary_footprint`（`as_measured.py:1163`）在 exterior ring ≠ 1 或 polygon 无效时静默返回空
>   ⇒ `derive_boundary_edges` 返回 `[]` ⇒ **门 0 配对 0 不一致全绿**。
>   exterior ≠ 1 = **多栋楼图纸；sm24（本批验收 case）就是两栋楼**。
> - **E3 型**：ring 内任何一条边 `_boundary_owners` 返回 ≠1（角缝/无主段）或被判 junction fragment
>   ⇒ **整 ring `continue` 静默丢弃**。实测两个真实形态：① footprint 一个顶点挪 2 m（图纸毛刺级别）
>   ⇒ **整层 44 条全部消失，门仍 `passed=True`（paired=56）**；② 管井夹具：2 条已正确判出的
>   `unclaimed_void` 随整 ring 被吞。
> - **E2c 型**：converter 幻觉出的 zone 只要不被任何 facts cavity 的 representative covers，**完全不进任何对账**。

> 返工要求（**纯门侧，⛔ 仍不许修任何一列**，与派工单 §四预裁 1 一致）：
> 让以下每个变异**必须红**、正常 sm25 仍 100/100 绿：
> ① E3（facts 删一个 ring）⇒ 红；② E4（facts `boundary_edges` 全空）⇒ 红；
> ③ E2c（converter 多一个未被认领的 zone）⇒ 红——即 facts cavity ↔ converter zone **双向全集对账** + 非空断言
> （或把「本视图无 boundary_edges」显式列为带理由的结构失败/声明盲区，⛔ 不许静默）。
> 复现：`cd /tmp/o21d_rev && PYTHONPATH=/tmp/o21d_rev python probe2_mutations.py`。

### ⭐ 主控独立复现（**逐条跑过，并纠正了自己的一次误读**）

`probe2_mutations.py` 我原样跑过，**E3 / E4 逐位复现**。
⚠️ **E2c 不在那个 probe 里**（probe2 只有 E2a 平移 5 m / E2b 同位，两者都**被抓住**）——
我一度据此以为裁决书把 E2c 说错了，**是我读错**：E2c 是**平移 50 m**、落在所有 facts cavity 之外。
我按 E2a 改平移量补跑，**逐位复现**：`E2c passed=True paired=100 structural=[] ⛔ 静默`。
⇒ **三个静默形态全部属实**；⛔ **不是「只有 facts 侧缺锁」——两侧都缺**，所以处方是**双向**全集对账。

---

## 二、五条不阻断的处置要求（⛔ 逐条明确「改了/不改+理由」）

| # | 处置口径 |
|---|---|
| **N1** | ⭐ 与 B1 同根：**`unclaimed_void`/`unknown` 的落库级存货 = 0**（R3 的供货是谓词级，落库级零行使）。⛔ B1 修好后**不许**再暗示「四档可产」——请在层契约里如实写成「落库级存货 = 0」 |
| **N2** | ⭐⭐ **`5_000` units（0.5 m）上限没人签过字**，且**语义混同**（系统基准差 vs 错配防护）。实测选中解残差 **0.247–0.339 m 全是基准差**（内皮 vs 墙中线）；**外墙 offset ≥ 0.36 m 的方言 ⇒ 正确配对会假红**。⇒ **本单要么把它 per-case 参数化并写明它防的是什么，要么明确标为待签字**。⛔ 别就地发明一个新数（[[silent-default-threshold-behind-otherwise-conclusions]]）|
| **N3** | 新锁覆盖面是**列举式**（6 字段 + `context` 通道）；现状安全（复核方 grep 实证编译器只消费 3 个字段、全在清空列表内）⇒ **登记为锁形态的已知边界**即可，本单不必扩 |
| **N4** | ⭐ **`reconcile_boundary_basis` 零生产接线**（全仓仅测试调用）——「不一致 = 必须有人看的观测量」，但**没有任何自动红的位置**。⇒ **随 B1 一并接进 staging / 走查工具链**（⛔ 原派工单没要求接线，故复核方未判阻断；但 B1 修好而没人调它 = 白修）|
| **N5** | `derive_boundary_edges` 三个静默出口（`exterior≠1` / polygon 无效 / `min_room_area_m2=None` 直通）**均无 diagnostics** ⇒ 与 B1/E4 同根；**实现时⛔ 不许留新的静默出口** |

---

## 三、验收项（⛔ 每条我都能说出它什么情况下会不通过）

| # | 验收 | ⛔ 什么情况下不通过 |
|---|---|---|
| 1 | ⭐⭐⭐ **三条「必须红」逐条实测**：E3 ⇒ 红 · E4 ⇒ 红 · E2c ⇒ 红，且**正常 sm25 仍 100/100 绿** | 任一条仍绿 |
| 2 | ⭐ **每条红都要「只红该红的」**：贴出红的具体条目，⛔ 不许整份 NA（[[invalidation-blast-radius-must-be-scoped]]）| 一坏就整层 NA |
| 3 | ⭐⭐ **换同形输入仍走不通**（返工审第三条）：**E4 的真实触发路径是「多栋楼」**（`exterior ring ≠ 1`）—— 请用 **sm24（两栋楼，本批验收 case）** 实测，⛔ 不许只用合成的空 `boundary_edges` | 只证明「把它清空会红」，没证明真实的多栋楼路径会红 |
| 4 | N1–N5 **逐条**有「改了/不改+理由」 | 漏任何一条 |
| 5 | **不碰任何一列的值**：`git diff` 里转换器 `basis` 判据与 facts `boundary_condition` 谓词**逐字节不变** | 顺手把哪一列改成迎合另一列 |
| 6 | 权威全量归主控；你交受影响子集 + `.pth`/HEAD 前后哨兵原文 | 哨兵不同 ⇒ 读数作废 |
| 7 | 答案根 `case_tests/test_baseline/gt/` **零字节改动** | 碰了答案根 |

---

## 四、⛔ 明确不做（本单）

**修任何一列的判据**（⛔ 本单纯门侧）· correction 侧 · 模块 1（另一个席位在做）·
**F-149 外部锚** · 改 `promote_gt_v3` · 重签答案 · 正交吸附 · 降模型智力。

### ⛔⛔ 派工方已预先裁定的两处张力（⛔ 别为它们停下上报）

1. **验收 3 要拿 sm24 实测，而 sm24 今天没有事实层**（`gt_staging/*/facts` 只有 sm25）——
   **不冲突**：验收 3 要的是**触发 `exterior ring ≠ 1` 这条路径**，可以用 sm24 的 **DXF/转换器输出**喂到
   `_boundary_footprint` 那一层，⛔ 不要求给 sm24 建整套事实层（那是另一个单）。
   ⚠️ 若你发现**结构上做不到** ⇒ 停下上报。
2. **N4 要「接进走查工具链」，而 §四禁「改 `promote_gt_v3`」** —— **不冲突**：
   走查工具链 = `gt_review_*` / staging 侧；`promote_gt_v3` 是**入库**那一步，⛔ 仍不许碰。

---

## 五、⛔ 停下上报触发器（**分层**）

**必须停**：① 三条「必须红」里有任何一条**结构上做不到**（⇒ 门的形态要改，⛔ 别自己改）·
② 验收 3 的 sm24 路径结构上走不通 · ③ 修 B1 必须改到某一列的值（⇒ 与 §四禁令真互斥）·
④ 本单任务项与本单禁令真的互斥。

**只记不停**：`5_000` 那个数最终怎么处置的分歧 · 夹具放哪个文件 · N3 登记的措辞。
⭐ 本项目「停下上报」**累计 48 次全部是派工方（我）的题错** ⇒ 觉得题有问题请一定停。
