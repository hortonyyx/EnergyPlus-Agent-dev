# B2 返工 2 · 执行档（Claude 家族施工席）

- 日期：2026-09-04 · 工作目录：`/tmp/b2_rework2_claude` · 分支：`wt/09.04g_b2_rework2`（基于 `a45f778c`）
- 派工单：[`2026-09-04g_B2_rework2.md`](../request/2026-09-04g_B2_rework2.md)
- 上一轮裁决：[`2026-09-04d`](../verdict/2026-09-04d_B2_rework1_crossreview_gpt.md)（REWORK / 阻断 2 / 不阻断 1）

## 〇、一句话结论

**返工门 = 让「手填 z 还能装配成功」在【类型层】不存在。** 本轮走派工单 §〇③ 的 **(a)+(b) 合并解**：

1. **(a) 封印载体**：装配边界 `assemble_multifloor_geometry` 只接受 `ValidatedFloorLadder`，
   该类型**唯一铸造者** = `derive_floor_ladder`，而 `derive_floor_ladder` 的**唯一入参**是密封
   `CorrectionEvidenceBundleArtifactV1`（bundle+冻结字节），且**第一步就跑 B3 字节门**。
2. **(b) 只让验证入口有装配能力**：`derive_floor_ladder` **不再有 `Sequence[FloorLevelClaimV1]` 重载**；
   低层 helper 的任意组合都拿不到能喂进装配的载体。
3. **承重机制 = z 从冻结字节解析**：`_DerivedFloorLevel.z_floor_m/ceiling_height_m` 经 `z_ref` 指针**读冻结字节**，
   ⛔ 永不读 `claim.z_m`。⇒ `model_copy(z_m=12.34)`、乃至**手工伪造 level/ladder**，对装配出的 z **完全无效**。

**为什么这条路现在构造不出来？** 装配的唯一 z 载体是 `ValidatedFloorLadder`，它的 z 是字节解析的、且它的唯一铸造者跑了字节门。
你能拿到的任何 `FloorLevelClaimV1` 都不能直接喂进装配；你能伪造的任何 level/ladder 里的 z 都会被「读回冻结字节」覆盖。
要让装配出的 z 变成 12.34，你必须提供**一份 z=12.34 的冻结阅读产物**（带自洽 sha256 + 契约分类，能过 `validate_evidence_bundle`）——
那已不是「手填 z」，而是**伪造一份 reading**，属于 reading 阶段的信任根、B2 范围之外。

---

## 一、开工自检（命令原文 + 输出原文）

```
$ cd /tmp/b2_rework2_claude && pwd && git log --oneline -1 && git status --porcelain
/tmp/b2_rework2_claude
a45f778c B2 rework 1 · execution doc — full suite 3777 passed / 0 failed (3773+4)
A  AI_agent/logs/reviews/request/2026-09-04g_B2_rework2.md
A  AI_agent/logs/reviews/verdict/2026-09-04d_B2_rework1_crossreview_gpt.md
```
`head -40 AI_agent/CLAUDE.md` 略（已读，§0 治理口径 + §1.5 不变量 #6 可扩展性铁律）。

---

## 二、改了什么（改前 → 改后）

### B-2：类型层无手填 z（`src/agent/correction/multifloor.py` 全量重写 + `pipeline.py`）

| 项 | 改前（`a45f778c`） | 改后 |
|---|---|---|
| `derive_floor_ladder` 入参 | `Sequence[FloorLevelClaimV1]`（**裸 claim 列表，不验 carrier**） | `CorrectionEvidenceBundleArtifactV1`（**密封**）；**第一步跑 `validate_evidence_bundle`** |
| 返回类型 | `tuple[_DerivedFloorLevel, ...]`（裸元组） | **`ValidatedFloorLadder`（封印类型）** |
| `_DerivedFloorLevel.z_floor_m` | `return self.lower.z_m`（**读 claim 的可 model_copy 字段**） | `_byte_z(frozen_docs, self.lower.z_ref)`（**读冻结字节**） |
| `assemble_multifloor_geometry` 入参 | `Sequence[_DerivedFloorLevel]`（**裸序列**） | `ValidatedFloorLadder`；非此类型 ⇒ `UNSEALED_FLOOR_LADDER` |

### 旧生产面真迁移（`src/agent/pipeline.py:run_correction`）

复核方 B-2 阻断第二半：`run_correction` 公开接收裸 z 浮点。

```python
# 改前（pipeline.py:1366-1367 一带）
evidence_chain_z_floor_m: float | None = None,
evidence_chain_ceiling_height_m: float | None = None,
...
projection=EvidenceChainProjection(
    z_floor_m=evidence_chain_z_floor_m,           # 裸浮点，caller 手填
    ceiling_height_m=evidence_chain_ceiling_height_m,
)
```
```python
# 改后：两根裸浮点面被移除，收窄为【只接受字节验证过的载体】
evidence_chain_level: "object | None" = None,
...
from src.agent.correction.multifloor import _DerivedFloorLevel
if evidence_chain_level is None:
    raise ValueError("evidence_chain=True needs evidence_chain_level: ...(B2 owns sourcing)...")
if not isinstance(evidence_chain_level, _DerivedFloorLevel):
    raise TypeError("evidence_chain_level must be a _DerivedFloorLevel minted by derive_floor_ladder ...")
...
projection=EvidenceChainProjection(
    z_floor_m=evidence_chain_level.z_floor_m,        # 字节解析，⛔ 不可手填
    ceiling_height_m=evidence_chain_level.ceiling_height_m,
)
```
**迁移后谁在调用**：`pipeline.run_multifloor_correction` 用 `derive_floor_ladder(elevation_evidence)` 得到密封
ladder，逐层把 `evidence_chain_level=level`（字节验证过的 `_DerivedFloorLevel`）喂给 `run_correction`；
单层链路的 B1 测试席（`tests/test_o22m7_evidence_wiring.py`）也一并改走该载体（用合成一层立面经 `derive_floor_ladder`
铸造 level），⇒ **裸 z 面全仓不复存在**（源码 grep：`evidence_chain_z_floor_m` 在 `src/` 下已 0 命中）。

> ⚠️ 关于「`run_multifloor_correction` 零生产调用者」：本单 §五 明禁 B5（把它接进 `run_pipeline`），故本轮**不接线**。
> 但迁移的本质不是「有没有生产调用者」，而是**裸 z 面已从类型上消失** —— 无论经 `run_correction` 还是
> `run_multifloor_correction`，能进 projection 的 z 都只能是字节验证过的载体。这一点由类型承载，与是否已接线无关。

### B-3：footprint 标签只由显式前置比较产生（`multifloor.py`）

```python
# 改前：靠 ValidationError 的 loc/type 二元组判定（复核方证明它把空 floor id 也误贴成 footprint）
except ValidationError as exc:
    if _is_footprint_mismatch_error(exc):     # loc==() and type=="value_error" —— 所有 model-validator 共用
        raise MultiFloorAssemblyError("PER_FLOOR_FOOTPRINT_MISMATCH", ...) from exc
    raise
```
```python
# 改后：装配前【显式】比对每层 footprint 指纹（复刻 schema 自己的算法），不一致由我响亮报出；
# 构造期的 ValidationError 一律【原样抛】，不再有 except ValidationError。
if len({_footprint_fingerprint(floor) for floor in floors}) != 1:
    raise MultiFloorAssemblyError("PER_FLOOR_FOOTPRINT_MISMATCH", ...)
assembled = CorrectedGeometryV3(... floors=floors ...)   # 任何 schema 错原样传播
```
⇒ `PER_FLOOR_FOOTPRINT_MISMATCH` **只可能**来自这处前置比较；构造期的任何 model-level 错（空 id / 未来 windows/segments 规则 / …）
**结构上不可能**被误贴成 footprint。这是**规则**，不是「这两个例外」的名单。源码锁 `_is_footprint_mismatch_error` / `.errors()` /
`except ValidationError` 全部消失（`test_no_loctype_or_substring_footprint_predicate_remains`）。

---

## 三、⭐⭐ 自证义务三小节（派工单 §三，缺一不合格）

### ① 原路复现：复核方那条路径逐字重跑，证明它现在在哪一步、以什么具名错误失败

复核方原文路径 = 保留两条诚实 claim 的 `z_ref`，只用公开 `model_copy` 把 `z_m` 改成 `12.34/17.91`，
再只走 `derive_floor_ladder` + `assemble_multifloor_geometry` 两个公开 helper。逐字重跑（内联脚本原文输出）：

```
=== §三#1 : reviewer's round-2 path, replayed VERBATIM ===
B2_RESULT=REJECTED_BY_GATE  code= FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE
B2_CLAIMS_OVERLOAD=ABSENT  ( AttributeError )
```
- **在哪一步失败**：`derive_floor_ladder(tampered_art)` 的**第一步 `validate_evidence_bundle`**，即任何 per-floor chain 之前。
- **具名错误**：`FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`（z_m=12.34 ≠ 冻结字节 2.71 → B3 字节门）。
- **两 helper 组合已不存在**：`derive_floor_ladder` 不再接受 claim 列表（`B2_CLAIMS_OVERLOAD=ABSENT`），
  复核方「保留 z_ref、只改 z_m、只走两个公开 helper」这条路在类型上断了。
- 对应锁：`test_reviewer_round2_bypass_is_dead_at_the_public_helpers` · `test_tampered_z_is_rejected_by_the_gate_before_any_chain`（并断言 `chain_calls == []`）。

### ② ⭐⭐⭐ 换同形输入仍走不通：我自己另设一条同形但不同的路径

复核方两轮都用「公开 API + model_copy」，且明说「甚至不必直接 import 私有类」。我的同形攻击**换个方向**：
**绕过 gate，直接手工伪造密封载体**（`ValidatedFloorLadder` + 从 `model_copy(z_m=12.34/17.91)` 的 claim 造 `_DerivedFloorLevel`），
再装配。这正是派工单 §三#2 点名的「先绕过你新加的那个构造函数」。原文输出：

```
=== §三#2 : my OWN same-shape attack — forge the sealed ladder, skip gate ===
HAND_FILLED z_m on claims = 12.34 / 17.91
LEVEL byte-resolved z_floor / ceiling = 0.0 2.9
B2_HANDFILL_TOOK_EFFECT = False
```
**为什么这一类都走不通**：即使我完全绕过 gate、亲手构造 `_DerivedFloorLevel`/`ValidatedFloorLadder`，
`z_floor_m` 仍从 `z_ref` 读**冻结字节**（0.0/2.9），我手填的 12.34/17.91 **无效**。要让它变成 12.34，我必须换掉冻结字节本身
（= 伪造一份 reading 产物），这不是「手填 z」。另外 `assemble_multifloor_geometry([level], ...)` 传裸序列 ⇒ `UNSEALED_FLOOR_LADDER`
（`test_assemble_refuses_a_bare_level_sequence`），`run_correction(evidence_chain_level=12.34)` ⇒ `TypeError`
（`test_run_correction_refuses_a_bare_z_requires_validated_level`）。⇒ **这一类**（公开组合 / 私有伪造 / 裸序列 / 裸 z 面）全部封死。
对应锁：`test_my_own_same_shape_forge_the_sealed_ladder_cannot_inject_a_hand_z` 等四条。

### ③ B-3 第二反例：除「空 floor id」外，我自己再找一条今天可达的 model-level 错误

派工单提示 = `schema.py:490` 那条规则的另一半 = **id 重复**。原文输出：

```
=== §三#3 : second reachable model-level error is NOT relabeled footprint ===
EMPTY_ID_RESULT=RAW ValidationError | footprint-relabeled?  False
DUP_ID_RESULT code= DUPLICATE_FLOOR_ID
```
- **空 floor id**（复核方点名，经 `model_copy` proxy 到达最终构造）→ **原样 `ValidationError`**（`v3 floor ids must be non-empty`），
  ⛔ 未被贴成 footprint（`footprint-relabeled? False`）。
- **id 重复**（我找的第二条）→ 装配自己的具名 `DUPLICATE_FLOOR_ID`，⛔ 亦非 footprint。
- 真的 footprint 不一致 → `PER_FLOOR_FOOTPRINT_MISMATCH`（来自显式前置比较）。
- 对应锁：`test_footprint_relabel_is_from_an_explicit_precheck_only` + 源码锁 `test_no_loctype_or_substring_footprint_predicate_remains`。

---

## 四、验收（逐条对派工单 §四七条）

| # | 规则 | 判定 | 证据 |
|---|---|---|---|
| **1** | 不经过冻结字节验证的 z，无法被装配 —— 由**类型**承载 | ✅ | 装配唯一 z 载体 = `ValidatedFloorLadder`，唯一铸造者 `derive_floor_ladder` 第一步跑 `validate_evidence_bundle`；z 字节解析。见 §〇、§三① |
| **2** | 低层 helper 的任意组合不得重新获得生产装配能力 | ✅ | §三① 原路复现（gate 拒）+ §三② 自设同形路径（伪造载体亦无效 + 裸序列 `UNSEALED_FLOOR_LADDER`）双双走不通 |
| **3** | 旧生产面已真迁移（⛔「新入口没人调用」不算） | ✅ | `run_correction` 裸 z 浮点面移除、收窄为 `evidence_chain_level`（只收 `_DerivedFloorLevel`）；`src/` 下 `evidence_chain_z_floor_m` 0 命中；调用者 = `run_multifloor_correction` + o22m7 单层席。见 §二 |
| **4** | 任何非 footprint 的 model-level 错，不得被贴成 `PER_FLOOR_FOOTPRINT_MISMATCH`；断言写成**规则** | ✅ | footprint 标签只来自显式前置比较；构造期错一律原样抛（无 `except ValidationError`）。§三③ 空 id→raw、dup id→`DUPLICATE_FLOOR_ID` |
| **5** | 真的 footprint 不一致仍被正确识别 | ✅ | `test_per_floor_footprint_mismatch_is_loud` + §三③(c) → `PER_FLOOR_FOOTPRINT_MISMATCH` |
| **6** | 上两轮已过审的不退化 | ✅ | 本文件三层混排 / 两层连续性（过 pipeline 真 z-stack 门）/ 具名坏输入 / B-1 字节门（改中间 rung 重封印仍拒，`test_tampered_z...`）全绿；本文件 **26 passed**（原 21 + 5 条 §三 自攻击） |
| **7** | 全量绿（`-n 6`）· 逐位闭合 | ✅ | `3782 passed / 2 skipped / 13 xfailed / 0 failed`；`3777 + 5 = 3782`（新增 5 条 §三 锁）。见 §五 |

---

## 五、命令原文 + 输出原文

### 环境自证 + 全量（同一条命令）
```
$ python -c "import src.agent.correction.multifloor as m; print('FILE', m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider
FILE /tmp/b2_rework2_claude/src/agent/correction/multifloor.py
...
3782 passed, 2 skipped, 13 xfailed, 211 warnings in 474.52s (0:07:54)
```
- `m.__file__` 落在 `/tmp/b2_rework2_claude/` 工作树内 ✅（承重不变量，cwd 胜过 `.pth`）。
- 有 summary 行、`0 failed` ⇒ 非同机竞争假红。

### B2 局部（同一条命令）
```
$ python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider tests/test_b2_multifloor_assembly.py
/tmp/b2_rework2_claude/src/agent/correction/multifloor.py
..........................                                               [100%]
26 passed in 4.69s
```

### o22m7 单层链路（迁移后，同一条命令）
```
$ python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider tests/test_o22m7_evidence_wiring.py
/tmp/b2_rework2_claude/src/agent/correction/multifloor.py
...............................                                          [100%]
31 passed in 5.18s
```

### 提交（分段，逐路径 add）
```
76178fd0 B2 rework 2 · pre-staged dispatch + prior verdict docs
25f5fdec B2 rework 2 · B-2: type-layer no-hand-fill (sealed ladder + byte-resolved z)
0f470a6a B2 rework 2 · tests: new-API rewrite + §三 self-attack suite
4f224a28 B2 rework 2 · migrate o22m7 single-floor chain to the validated-level face
```
（本执行档提交为第 5 段。）

---

## 六、最薄弱一处（据实自评）

**信任边界的「另一侧」我没有在类型上封死，而是靠论证划界。** 承重机制是「z 从冻结字节解析」，
它把复核方两轮的**具体攻击**（保留 z_ref、改 z_m、绕 gate 伪造载体）全部证否；但它对**「亲手伪造一份完整自洽的冻结立面产物」**
（bytes + 匹配 sha256 + 能被 `classify_vector_json` 判成 elevation 契约 + 过 `FLOOR_LADDER_NOT_EXHAUSTIVE` 等全部门）
**不设第二道防线** —— 我把这一层判为「= 提供一份（伪造的）reading，属 reading 信任根、B2 范围外」。
这个判断是**范围主张**，不是类型强制：如果复核方认为「B2 也该防伪造冻结产物」，那我这条边界会被击穿。
我的立场依据是 §五 明禁碰 `evidence_contract.py`（伪造检测归那层的 `classify_vector_json` / sha256 / 契约门），
且 B2 的载体不含「重新校验冻结产物真伪」的职责。**这一处最值得复核方对着打。**

次弱：`derive_floor_ladder` 现在每次都完整跑一遍 `validate_evidence_bundle`（多层装配时逐次），是性能税、非正确性问题；
本轮 P0 是正确性，未做缓存。
