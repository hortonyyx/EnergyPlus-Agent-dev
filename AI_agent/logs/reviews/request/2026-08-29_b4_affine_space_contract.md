# 派工单 · B4-①：affine 的两端空间合同

- **日期**：2026-08-29 · **派工方**：orchestrator · **施工**：Claude 执行档 · **审**：跨家族
- **档位**：工程档（碰 `src/agent/judge/` 类型 + 契约哈希）⇒ gate① + 全量绿 + 跨家族审
- **基线 commit**：`5a8fb2c`（分支 `08.23_AsDrawnReading`）
- **上位背景**：这是 ②-1（= gt 生产链）施工次序的**第 1 位**。全档 → `2026-08-29_sol_rework_rebaselined.md` 附录

---

## 〇、⛔ 先读（读完再动手）

1. **本单只做「空间合同」这一半。**
   ⛔ **不做**标定门 / plan controls 重签（那是 B4-②，**用户尚未拍板**）·
   ⛔ **不做**正交吸附（F-129）· ⛔ **不做**事实层（B2）· ⛔ **不做**坐标改整数存储（那是本单的**下游**）。
2. ⛔ **绝对不许跑 `pip install -e .` / 任何写 `site-packages` 的命令**（venv 全机器共享，出过事故）。
3. **停下上报触发器【分层】**：
   - **承重前提错**（§一里任何一条「已实测」你复现不出来）⇒ **停下上报，⛔ 别自行扩路**
   - **外围数值错**（行号偏了、计数差一个）⇒ **记一行继续做**，交件时一并说
   ⚠️ **上一单（F-126）我方题面就写错了一条承重前提**（累计第 39 次）。**这一单请当成「题面可能又错了」来读。**

---

## 一、缺陷（orchestrator 已逐条独立核过，⛔ 请你自己再核一遍）

`Affine2D`（[`gt_manifest.py:39`](../../../src/agent/judge/gt_manifest.py#L39)）= **六个裸浮点数 + 一个非奇异校验，⛔ 零空间标注**。

**同一个类型承载三种不同的两端空间，其中两个还同名**：

| 字段 | 位置 | domain → codomain |
|---|---|---|
| `pixel_to_source_m` | `tarch_converter_schema.py:767` | pixel → source-metre |
| `world_from_source_m` | `tarch_converter_schema.py:692`（`PlanViewIntentV1`）| **dxf-native → world-metre** |
| `world_from_source_m` | `gt_manifest.py:117`（`GtExtractionManifestV1`）| **source-metre → world-metre** |

后两条**同名、差一个 `metres_per_unit`（sm25 = 0.001）⇒ 1000×**。
**今天靠一段注释 + 一次手工除因子避免撞车** —— [`tarch_normalize.py:2732`](../../../src/agent/judge/tarch_normalize.py#L2732) 逐字写着：
> `affine = plan_view.world_from_source_m  # native -> world (m00 = metres_per_unit)`
> …the manifest `world_from_source_m` maps **source-METRES → world** … **NOT native → world**

⚠️ **第二个 affine 类型**：`Affine2DV1`（[`score_schema.py:578`](../../../src/agent/judge/score_schema.py#L578)），判分侧自己一份。

---

## 二、要做什么

### R1 · 给 affine 加**双端空间合同**
`domain_space` + `codomain_space`，取值至少覆盖 `pixel` / `dxf_native` / `source_metre` / `world_metre`。
⭐ **`Affine2DV1` 一并覆盖，⛔ 不许只改一个**（只改一个 = 只修一半）。

### R2 · **compose helper** 验空间衔接
提供组合函数，`left.codomain != right.domain` ⇒ **响亮失败**。
⛔ 字段改名只作迁移期 fail-fast，**⛔ 不代替空间合同**。

### R3 · ⭐ **保住已签字答案的哈希**（本单最容易翻车的地方）
`compute_request_sha256` 哈希的是 `request.model_dump(mode="json")` = **整个模型** ⇒ 直觉上加字段会让所有签名失效。

**但文件里已有版本闸先例**（`tarch_converter_schema.py`，逐字）：
```python
if request.request_version == 1:
    payload.pop("wall_thickness_range_m", None)
    payload.pop("min_room_area_m2", None)
```
> docstring：「Omitting them when hashing a declared v1 request **preserves old signatures**;
> all new requests must declare v2 and bind both fields.」

**实测 sm25 与 sm24 的 `request.json` 都是 `request_version = 3`。**
⇒ **照抄这条路子**：新字段对 `request_version <= 3` 一律 `pop`；新 request 声明 **v4** 并绑定空间。
⇒ `manifest_sha256` 同理（`compute_manifest_sha256` / `canonical_manifest_payload`）。

⚠️ **必须在 docstring 里如实写一句**：迁移期内空间合同**不进签名** ⇒ 这道门**保护的是代码、不是签字产物**；
⛔ 别写成"签名已经覆盖空间"。

---

## 三、验收（⛔ 每条都要能不通过）

1. **⭐ 签字不变（最硬的一条）**：三份已签字答案的 `request_sha256` 与 `manifest_sha256`
   **跑前跑后逐位相同**。⛔ 贴出前后两组哈希原文对照，别只说"没变"。
   （目录：`case_tests/test_baseline/gt_sources/{sm25-L_anchor,sm24_anchor,sm21_anchor}`；sm21 若无 request 则说明）
2. **类型门有牙**：⭐ **夹具直接用上面那对同名 1000× 的真货**，⛔ 不许造合成 affine。
   断言：把 manifest 的 `world_from_source_m`（source_metre→world）喂给期望 native→world 的位置 ⇒ **必须红**。
3. **`Affine2DV1` 已覆盖**：给出它也被约束的证据。
4. **逐把锁说明「不加这处改动，这把锁会不会红」** —— 答不出"会红"的锁没有分辨力。
5. **全量**：`pytest -n 6`（⛔ 不加 `-m`，⛔ 不用 `-n auto`）。贴**汇总行原文**，⛔ 不许 `| tail`。
   `.pth` 前后哨兵两次同值。
6. **范围**：贴 `git diff --numstat` 原文。碰到 §〇 列的禁区 ⇒ 说明理由。

---

## 四、⚠️ 我方可能又错的地方（请主动证伪）

1. 「`Affine2DV1` 也需要空间合同」—— 我只看了它的定义位置，**没查它的实际消费者**。
   若它的两端空间**恒定且单一**，加合同可能是过度设计 ⇒ **查清楚再决定，并把结论写进交件**。
2. 「照抄 v1 那条版本闸就能保住签名」—— 我读了那段代码，**没实跑验证过加字段后 pop 的效果**。
   ⇒ **第 1 条验收就是它的实测**；若实测不成立 ⇒ **承重前提错，停下上报**。
3. 三个 affine 的两端空间是我从**代码注释 + 字段名**读出来的，⛔ 未逐个数值验证。
   ⇒ 动手前**自己验一遍**（例如拿 sm25 的 request 与 manifest 各取一个点算一遍，看差不差 1000 倍）。
