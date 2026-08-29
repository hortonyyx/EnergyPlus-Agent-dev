# 派工单 · ②-1b：**`revisions` 台账 + `as_signed` 机械派生 + B1 指纹锚 + F-D 指纹加宽**

- **日期**：2026-08-29 · **派工方**：orchestrator · **施工**：Claude 执行档 · **审**：跨家族（升一档）
- **档位**：工程档 · **基线**：**`866d518`**（②-1a-R 已过 GLM 跨家族审 APPROVE-WITH-FINDINGS / 阻断 0；权威全量 **3253 passed / 13 xfailed / 0 failed**）
- **上位**：用户 2026-08-29「继续推进」；本单 = 第 ② 步主线的第 2 单，**接在 ②-1a-R 后面**
- **相关口径**（⛔ 动手前必读）：
  [落库方案](../../architecture/gt_revision_ledger.md)（三截 §一 · 目录 §二 · 一条 revision 长什么样 §三 · 可复现门 §六 · **信任根 §七** · 晋升接法 §八 · 四条拍板 §九 · as-received 裁定 §十）·
  [目标态地图 §1.3–1.4](../../architecture/gt_and_pipeline_flow_map.md) ·
  [本批指南 §十二](../../guides/reading_correction_split_guide.md)（gt 侧确定性配对的五条准入条件）

---

## 〇、⛔ 先读

1. **本单只做三截里的后两截 + 两条指纹。**
   ⛔ 不做 `AnswerCompiler` / 出模形式 / 顶点去重 / 接头求交（**②-1c**）· ⛔ 不做 `boundary_condition`（**②-1d**）·
   ⛔ 不碰 correction / geometry 内核（**②-2**）· ⛔ 不碰 reading 侧任何东西 · ⛔ 不动判分器。
2. ⛔⛔ **绝对不许 `pip install -e .` / 任何写 `site-packages` 的命令**（venv 全机器共享，08-27 出过事故）。
3. ⛔ **不许改任何已签字件的哈希、不许绕过任何门。** 门挡住 = 门挡住了。
4. **停下上报，分层**：
   - **承重前提错**（§一那四条里任何一条你复核后不成立）⇒ **停下上报**，⛔ 不要自行绕路施工；
   - **外围数值错**（我引的某个字节数、某个计数）⇒ **记一行继续**，收工时一并报。
   - ⚠️ 派工方累计题错 **41+** 次，**且本条线上 08-28/29 已自查推翻过三版**。⭐ **本单给的每个「二选一」都可能漏了更优的第三条** —— 若你判断存在严格更优解，**停下上报**，⛔ 不要在两个次优里硬选。
5. **产物落仓库**（`AI_agent/logs/experiments/2026-08-29_o21b_*/`），⛔ 不落 `/tmp`、⛔ 不落仓库根目录。

---

## 一、承重前提（我已实测，⛔ 请自己复核一遍再开工）

### 1.1 事实层今天**只有第一截，且不落盘**

`AsMeasuredV1` schema + `build_as_measured` 在 [`src/agent/judge/as_measured.py`](../../../src/agent/judge/as_measured.py)，
**但**：`gt/<case>/facts/` 目录**不存在**（实测 `gt/sm25-L_anchor/` 只有 `gt.json` / `renders/` / `review/`），
全仓**无 CLI**，`build_as_measured` 的调用方**全在 `tests/test_as_measured_facts_layer.py`**。
⇒ **「②-1a 完成」= schema + builder + 锁落地，⛔ 不等于库里有事实层文件。本单要把它变成有。**

### 1.2 B1 指纹锚今天是**显式的空**

```python
#: ⛔ Stated absence, not a missing field: B1 is ②-1b.
converter_implementation_fingerprint: None = None
```
⭐ 这是**故意写成「声明的缺席」**（⛔ 不是漏字段）—— 一个装着没人签过的值的字段会被读成 attestation。
⇒ **本单要把它填成一个真的、外部可核的锚。**

### 1.3 F-D：转换器实现指纹**只盖一个文件**

[`converter_sha256()`](../../../src/agent/judge/tarch_normalize.py#L798) = `sha256(tarch_normalize.py 自己的字节)`。
我实测（`866d518`，字节数与前 12 位）：

| 文件 | 字节 | sha256[:12] | 在指纹里吗 |
|---|---:|---|---|
| `tarch_normalize.py` | 208,726 | `539615abee77` | ✅ |
| `tarch_converter_schema.py` | 64,340 | `3974929774d6` | ⛔ **不在**，而转换行为依赖它 |
| `gt_manifest.py` | 17,665 | `780975d799f9` | ⛔ **不在**，同上 |

⇒ 那文件**改一个字的注释**就让指纹翻转（噪声），而**真改了 schema / manifest 的行为却一声不吭**（漏报）。
⭐ **两个方向都错，这才是要修的。** 同族 [[version-number-is-not-behavior-attestation]]。

### 1.4 F-132：真晋升件**已经在漂**，且**零测试触达**

实测 `gt/sm24_anchor/gt.json` 的 `vg_implementation_sha256 = 60cab9e6…`，
而同一棵树上 `gt/sm25-L_anchor` 签的是 `8e45fd15…`（= 当前实现算出来的值）
⇒ **sm24 那份的溯源戳与现行代码不一致，且全仓没有任何锁在跑它的复现门，所以它漂了多久没人知道。**
⛔ **本单不修 sm24 的戳**（那要重签，归 gt 重做）——但**你新加的门必须能看见这种漂移**，⛔ 不许只在 sm25 上有牙。

---

## 二、要做什么（五件）

### R1 · `revisions` 台账：schema + 那 5 条线的第一批记录

**一条 revision 的形状**（落库方案 §三，逐字照它）：
`id` · `target` · `finding` · `verdict` · `action` · `reason` · `signed_by` · `signed_at`。

| `verdict` | 含义 | 产出 |
|---|---|---|
| `drawing_error` | 图画错了 | 带 `action` ⇒ **改 `as_signed`** |
| `as_designed` | 本该如此 | ⛔ 不改几何，**记账**；⭐ **照报但标「已确认」，⛔ 不从清单里删** |
| `producer_defect` | 工序缺守卫 | ⛔ 不改几何 ⇒ 出缺陷登记草稿 |

**四条已由用户拍板，⛔ 不要重新讨论**：
① `action` **先只实现 `translate`**，其余遇到再加，且**每加一种必须能说清「它是 `as_measured` 上的一个确定性操作」** ·
② 一条 revision 的**作废半径 = sol 的 B6 依赖闭包**（⛔ 不是「层」也不是「边」）·
③ **只有签字流程能写 `revisions`**（同 F-117 教训）· ④ `as_designed` 记账后照报。

**第一批住户 = sm25 那 5 条线**：`13AD 13AC 13AF 160A 13AE`，签字件 `1251f651…` 与 as-received `4a949224…`
之间**916 实体、handle 集相同、只有这 5 个坐标不同**，最大移动约 **6 mm**。
⛔ **本单不许替用户判 `verdict`。** 你要产出的是**一份待签清单**（机器算出的 `target` + `finding` + 候选 `action`），
`verdict` / `signed_by` / `signed_at` 留空或标 `unsigned`，**并让「未签字的 revision 不得进入 `as_signed`」成为结构性的**
（⛔ 不是一句注释）。

### R2 · `as_signed` 机械派生 + **逐位可复现门**

> **`as_signed` 必须能从 `as_measured` + `revisions` 逐位重算出来**，不一致 ⇒ **响亮失败**。

- `as_signed` 与 `as_measured` **同一个 schema**（⛔ 别为它另发明一套字段）+ 一个派生键
  （至少含：`as_measured.content_sha256` · **整份 `revisions` 的哈希** · 派生器版本）。
- ⛔ **无独立信任根**（它是派生的）—— 文档与字段命名都不许把它写成有独立信任根的东西。
- ⭐ **这条顺带解 F-130**（两把尺子一起冻住）。⛔ 但**本单不改判分器去读它**（那是 ②-1c 的活），
  只要求 `as_signed` **落盘且可复现**。

### R3 · B1：**外部获授权的实现指纹锚**

填掉 §1.2 那个 `None`。**判据不是「有个哈希」，是「画得清谁签谁」**：

- **输入**（`source.dxf` + `request`）签的是**什么**、**谁签的**；
- **实现**（转换器闭包）签的是**什么**、⭐ **锚在哪儿**（⛔ 「代码自己算自己的哈希」不叫外部锚）；
- **facts** 自己的 `content_sha256` 覆盖哪些字节。

⚠️ 我能想到两条路，**但很可能还有更优的第三条 —— 若你判断有，停下上报**：

| | 做法 | 已知代价 |
|---|---|---|
| **甲** | 把加宽后的闭包指纹 + 已签 `judge_config` / `vg_config` 一起写进 facts 的一个 `provenance` 块 | 简单；⚠️ **仍是「代码算自己」**，只是范围大了 —— 要说清它凭什么算「外部」 |
| **乙** | 指纹的**授权值**存进受签字保护的载体（如 review bundle 的索引），facts 只**引用**它 | 更像真锚；⚠️ 碰签字载体 ⇒ **必须证明现有签字件逐位不变** |

### R4 · F-D：指纹**加宽到转换闭包**

- 从「一个文件」改成「**一组构成转换行为的文件**」，且**这组的成员资格必须有出处**（⛔ 不是手挑一个列表就完事）。
- ⛔ **两个方向都要有牙**：改 `tarch_normalize.py` 的**注释**不该翻转（今天会）· 改 `tarch_converter_schema.py` 的**行为**必须翻转（今天不会）。
  ⚠️ 这两条**各自都要有一个真的变异实测**，⛔ 不许只测一个方向就写「有牙」。
- ⚠️ 改指纹**会让已签字件的复现门集体变红**（F-D 记的「恰好 5 红」就是这个形状）。
  ⇒ **必须显式处理**：是加版本闸、是把旧值当 legacy 认、还是让它红并写进「随 gt 重签一并修」——
  **三条我都能接受，⛔ 但不许静默让它绿**。选哪条要在收工报告里写明理由。

### R5 · 落盘位置与**谁能写**

落库方案 §二定的是 `case_tests/test_baseline/gt/<case>/facts/{as_measured,revisions,as_signed}.json`。
⚠️ **这里有一个我没替你解掉的张力，请你判断并在收工报告里写明**：

> `gt/` 是**答案根**，而现行纪律是「**只有晋升流程能写 `gt/`、只有签字流程能写 `revisions`**」（F-117 的教训）。
> 本单要产出文件，但 **⛔ 本单不改 `promote_gt_v3`** —— 晋升碰的是签字件路径，
> 我判断它该**随 gt 重做重签一起动**（用户已定 sm25 gt 整份重做排在这批改造之后）。

⇒ **本单的落盘走一条不写答案根的路**（staging / `gt_sources/` 侧 / 显式的 candidate 目录，你定），
并**留下一条明确的「将来怎么接进晋升」的接缝说明**（含落库方案 §八 点名的 **F-128** 回滚不对称，⛔ 本单不修，只记）。
⭐ **若你判断「不写答案根」这个前提本身是错的，停下上报** —— 这正是 §〇#4 说的那类。

---

## 三、验收项（⛔ 每条我都能说出它什么情况下会不通过）

| # | 验收 | ⛔ 什么情况下不通过 |
|---|---|---|
| 1 | 三份 facts 文件**真的产出来了**，`as_measured` 与 ②-1a 的 `content_sha256` **逐位相同** | 派生过程动了事实层 ⇒ 哈希变 |
| 2 | **未签字的 revision 结构性地进不了 `as_signed`** | 构造一条 `verdict=null` 的记录，若它影响了 `as_signed` ⇒ 红 |
| 3 | **可复现门有牙**：手改 `as_signed` 一个整数 ⇒ 响亮失败；手改 `revisions` 一条 `action` ⇒ `as_signed` 跟着变且新旧哈希不同 | 门只比对象是否存在、不比内容 ⇒ 两个变异都绿 |
| 4 | `translate` 之外的 `action` 值**被拒绝且具名** | 落进 `else: pass` ⇒ 静默忽略 |
| 5 | **指纹加宽双向变异各一格**：注释级改动**不**翻转 · schema 行为级改动**翻转** | 只做了一个方向 ⇒ 不通过（⛔ 「变异没效果」与「变异没跑」在产物上分不开，**每格必须自证变异真的生效了**）|
| 6 | 那 5 条线的**待签清单**能机器产出，且 `verdict` 全为未签 | 清单是手写的 / 已经替用户判了 verdict |
| 7 | **B1 锚的「谁签谁」写成一张表**（输入 / 实现 / facts 三行，逐行写清签字载体） | 只加了个哈希字段而说不清它凭什么算外部锚 |
| 8 | 权威全量绿，**带 `.pth` 前后哨兵**（跑前跑后各记一次 editable 装机文件哈希，两次相同才算数） | 哨兵不同 ⇒ 读数作废重跑 |
| 9 | 已签字件 `request.json` 的 `compute_request_sha256` **逐位不变**（sm25 `d738d0ac…` / sm24 `ae0fec08…`），**贴前后对照原文** | 碰了签名 payload |

⛔ **不接受的证据形式**：只有散文的「已验证」· 只有一次跑出来的红或绿（[[repeat-the-run-before-accusing-a-seat]]）·
引用行号却没回文件 `grep -n "<锚点>"` 核过（[[line-numbers-from-diff-output-are-not-file-lines]]）。

---

## 四、⛔ 明确不做（本单）

改 `promote_gt_v3` / 拷 facts 进晋升 · 修 F-128 · 修 sm24 的漂移戳（F-132）· 判分器改读事实层 ·
`AnswerCompiler` 与两种出模形式 · 正交吸附 · `boundary_condition` · 任何 reading / correction 侧改动。
