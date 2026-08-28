# 派工单 · B4-②a：数值门 + 两把结构锁

- **日期**：2026-08-29 · **派工方**：orchestrator · **施工**：Claude 执行档 · **审**：GLM 跨家族
- **档位**：工程档 · **基线**：`e638655`（分支 `08.23_AsDrawnReading`）
- **上位**：B4-① 已 APPROVE-WITH-FINDINGS 收口（`dc8821b`）；本单做**不需要重签**的那三条

---

## 〇、⛔ 先读

1. **本单只做 F-A / F-B / F-E 三条。**
   ⛔ **不做** F-C（版本机制）· F-D（指纹加宽）· 平面锚点重签 —— **那三条都要重签答案**，归 B4-②b。
   ⛔ 不做事实层 · 不做正交吸附 · 不碰 `tarch_normalize.py`（⚠️ 见 §四.3）。
2. ⛔ **绝对不许 `pip install -e .` / 任何写 `site-packages` 的命令**。
3. **停下上报分层**：承重前提错 ⇒ 停下上报；外围数值错 ⇒ 记一行继续。
   ⚠️ **派工方累计题错 41 次**（今日三次）。**请当成「题面可能又错了」来读。**

---

## 一、F-A（主条）：**空间合同的牙只随声明走，盖章按槽位、内容盲**

**跨家族审实测**（GLM，`dc8821b` 上）：把 manifest 那份 affine **剥掉 `domain_space`/`codomain_space`**，
塞进 request 的 native 槽 ⇒ **`model_validate` 静默通过**，`affine_spaces()` **按槽位盖章**成 `dxf_native→world_metre`，
clip 角点偏 **Δ = 12264.7 m**。**三个槽位同形全过。**
**对照**：只要**保留声明**，两把锁立刻红 ⇒ 牙是真的，只是够不着裸系数。

⚠️ **不是合成场景**：迁移期签字件**本来就不带声明**（正是 strip 存在的理由），
且 `_build_manifest`（`tarch_normalize.py:2732-2744`）今天构造的仍是**裸 `Affine2D`** + 手工 `/mpu`；
`grep -n "require_affine_spaces" src/agent/judge/tarch_normalize.py` ⇒ **0 行**。
⇒ **算术回归（多除 / 漏除 `mpu`）今天会静默通过。**

### 要做什么

在 **`TarchConversionRequestV1` 层**加一条**数值一致性检查**（复核方给的处方）：

> **同名两槽的 `|det|` 应相差恰好 `mpu²`**（sm24/sm25 `mpu=0.001` ⇒ **1e6 倍**）。

**为什么用 `|det|`**：**旋转不变**，⛔ 不会被「图纸转了个角度」这类合法情形误伤。
⛔ **不进任何签名 payload**（⇒ 签字哈希必须逐位不变，见 §三.1）。
⭐ 它**一条同时抓住两种形态**：裸系数换槽 · `/mpu` 算术回归。

⚠️ **⛔ 这道门是 sol 当初 B4 主张 2 要的【第二道门】** —— A 类型门（B4-① 已交付）+ **B 数值门（本条）**。
⛔ 不许把它做成类型门的附属；它必须在**没有任何声明**的输入上也有牙。

## 二、F-B：`Affine2DV1` 的「唯一生产者」没有 tripwire

今天的事实**已复核为真**（全仓唯一构造点 `reading_typed_adapter.py:241`、唯一调用 `:451`、三个消费点）。
⛔ **但第二个生产者出现时会静默拿错两端、零锁变红**（复核方内存演示：
外来 `Affine2DV1(xx=0.01, …)` 实为 pixel→world，被 `apply_affine_2d` 静默接受）。

⇒ **加一把「构造点计数 = 1」的结构锁**（⭐ 仓内有先例 —— F-116 那批的 `f116_c` 就是结构锁）。
⛔ **不是**字面 grep `Affine2DV1(`，要能扛住换行 / 别名 import。

## 三、F-E：`Affine1D` 同病未治

立面 `world_along_from_source_m` / `world_z_from_source_m`，**四个字段位**
（`gt_manifest.py:168/169` + `tarch_converter_schema.py:717-718/746-747`），
类型仅 `source_axis/scale/offset` + `scale≠0` 校验（`gt_manifest.py:76-85`），**零空间标注**。
**当前潜伏**：sm24 manifest **0 个**立面视图 ⇒ 今天无签字碰撞对；⭐ **manifest 哪天签了立面，1000× 碰撞即成真。**
⇒ 给它同样的两端空间合同（照 `Affine2D` 的做法），**同样走版本闸保签名**。

---

## 三之二、验收（⛔ 每条都要能不通过）

1. ⭐ **签字哈希逐位不变**：sm25 request `d738d0ac…` · sm24 request `ae0fec08…` · sm24 manifest `c40cbc8b…`
   —— **贴前后两组原文对照**。⚠️ **只有这三份**（sm25 无 manifest、sm21 两样皆无）。
   ⭐ 另贴 `PlanFrameCertificateV1.preimage_sha256` = `05a29dc3…` 不变。
2. ⭐⭐ **数值门必须在【裸系数】上有牙**：夹具 = **复核方那三段换槽脚本的同形**
   （剥掉声明 → 塞进另一个槽 → 期望**红**）。⛔ 不许只在带声明的对象上验。
3. **反空转**：证明数值门不是恒真 —— 给出「不加这道门时它会放过什么」的实测。
4. **F-B 的结构锁**：造一个第二生产者 ⇒ 必须红。
5. **全量** `pytest -n 6`（⛔ 无 `-m`、⛔ 不用 `-n auto`）+ `.pth` 前后哨兵。贴汇总行原文。
6. **范围**：贴 `git diff --numstat` 原文。

---

## 四、⚠️ 我方可能又错的地方（请主动证伪）

1. **「`|det|` 相差恰好 `mpu²`」这条公式我没实算过** —— 它来自复核方的建议。
   ⇒ **动手前先拿 sm24 那对真货算一遍**：request `m00=m11=0.001` vs manifest `m00=m11=1.0`
   ⇒ `det` 应为 `1e-6` vs `1.0`，比值 `1e6 = mpu²` ✓（我只做了心算）。**若实算不符 ⇒ 承重前提错，停下上报。**
2. **「同名两槽」在每个 case 上都同时存在吗？** ⚠️ **实测 sm25 只有 request、没有 manifest**
   ⇒ 那条门在 sm25 上**根本没有对照物**。⛔ 别把一道**在主力 case 上无存货**的门当成有牙的
   （[[gate-teeth-direction-follows-fixture-inventory]]）。⇒ **请想清楚：单侧存在时这道门检查什么？**
3. **⛔ 不要碰 `tarch_normalize.py`** —— 复核方实测：`converter_sha256()` = **该文件自己的字节哈希**，
   **改一个字的注释**就让 `test_gt_raw_layer.py` **恰好 5 红**（触发重签）。
   ⚠️ 而 F-A 的病灶（`_build_manifest` 产裸 `Affine2D`）**正在那个文件里**
   ⇒ **本单只在 `TarchConversionRequestV1` 层加门，⛔ 不进那个文件**；病灶侧的修复归 B4-②b（重签批次）。
   **⭐ 若你认为不碰它就做不成这道门 ⇒ 停下上报，别自行扩路。**
