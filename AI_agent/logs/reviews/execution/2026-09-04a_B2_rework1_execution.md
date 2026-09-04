# 执行档 · B2 返工 1：把 z 的信任链接回冻结字节

- **日期**：2026-09-04 · **施工方**：Claude 家族施工席 · **工作目录**：`/tmp/b2_rework_claude` · **分支**：`wt/09.04a_b2_rework`
- **派工单**：[`2026-09-04a_B2_rework1.md`](../request/2026-09-04a_B2_rework1.md)
- **上一轮裁决**：[`2026-09-03al`](../verdict/2026-09-03al_B2_crossreview_gpt.md)（REWORK / 阻断 3 / 不阻断 1）

## 开工自检（命令原文 + 输出原文）

```
$ pwd && git log --oneline -1 && git branch --show-current && \
  python -c "import src.agent.correction.multifloor as m; print(m.__file__)"
/tmp/b2_rework_claude
82f9ce32 B2 step 4: execution doc — full suite 3773 passed / 0 failed (3756+17)
wt/09.04a_b2_rework
/tmp/b2_rework_claude/src/agent/correction/multifloor.py
```

⇒ 工作目录、分支、`m.__file__` 均落在本 worktree（承重不变量，cwd 胜 `.pth`）。

## 改动范围（`git diff --numstat 82f9ce32 HEAD`，仅列源码/测试）

```
122  49  src/agent/correction/multifloor.py
 30   4  src/agent/pipeline.py
162  25  tests/test_b2_multifloor_assembly.py
```

⛔ **未碰 `evidence_contract.py` / `EvidenceDebtV1` schema**（T4-a 正由 GLM 另单在做）：
`git diff 82f9ce32 HEAD -- src/agent/correction/evidence_contract.py` = 空。
⛔ 未做 B4 洞口合成、未动 B3 立面适配器、未 `pip install -e .`、未 `git add -A`。

**分段提交**（4 段）：

```
b7f6c9fa B2 rework 1 · tests: sealed-carrier entry + type-level no-z + structural relabel
1d74e67c B2 rework 1 · B-3: extract _is_footprint_mismatch_error for a testable structural predicate
b07534ed B2 rework 1 · B-1: entry consumes+validates the sealed evidence carrier
ef9c3817 B2 rework 1 · B-2+B-3: private _DerivedFloorLevel (no raw z) + structural footprint relabel
```

> ⚠️ **据实记一条**：开工时主控预置并**已 staged**的三份 md（本单 + 两份裁决）在 index 里，
> 我第一次 `git commit`（用显式路径 `git add src/...`）时把它们**一并带进了 `ef9c3817`**。
> 它们本就属于本分支、无内容丢失、未波及任何他席 WIP（全程未用 `git add -A`）。只是与代码混在了一个 commit，属瑕不掩瑜，未改写历史。

## 逐条对 §四 六条验收

### #1 ⭐⭐⭐ z 漂移是【机器门】不是人工抽检 —— ✅

**做法（B-1）**：`run_multifloor_correction` 的入参从脱离 artifact 的 `Sequence[FloorLevelClaimV1]`
改成**封印 carrier** `CorrectionEvidenceBundleArtifactV1`（bundle + frozen bytes）。
进门第一件事就是跑 B3 **已有**的那道门 `validate_evidence_bundle(...)`
（`evidence_contract.py:1215`，内含 `FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`，行 `1718`），
**在任何 per-floor chain 之前**。⛔ 不是重写一道。

改前改后（`pipeline.py`）：

```python
# 改前
def run_multifloor_correction(elevation_floor_level_claims, plan_runs):
    levels = derive_floor_ladder(elevation_floor_level_claims)   # 拿不到 frozen_sources

# 改后
def run_multifloor_correction(elevation_evidence, plan_runs):
    validate_evidence_bundle(elevation_evidence)                 # ← B3 值↔字节门，先跑
    levels = derive_floor_ladder(elevation_evidence.bundle.floor_level_claims)
```

**机器门证据**（测试 `test_tampered_z_is_rejected_by_the_gate_before_any_chain`）：
保留原 `z_ref`、只把最上一 rung 的 `z_m` 手改为 `12.34`、重 `finalize_bundle` 封印 ⇒

```
raises EvidenceContractError.code == "FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE"
chain_calls == []   # 断言 run_correction 一次都没被调 ⇒ 门在 chain 之前变红
```

⇒ 复核方原实测的 `OFFICIAL_ENTRY_OUTPUT_Z [(12.34, …)]` 这条旁路已封死。
配套 `test_honest_carrier_passes_the_gate_and_derives` 证明门**不是墙**：诚实 carrier 照过。

### #2 手填 z 的路在类型层不存在 —— ✅（说明为什么现在构造不出来）

**做法（B-2）**：`DerivedFloorLevel`（公开、直接暴露 `z_floor_m` / `ceiling_height_m` 两个可填字段）
→ 私有 `_DerivedFloorLevel`，**只持有两条 bounding `FloorLevelClaimV1`**（`lower` / `upper`），
`z_floor_m`、`ceiling_height_m`（及四个 ref/id）全部改成**只读 `@property`**，从两条 claim 计算：
`z_floor_m == lower.z_m`、`ceiling_height_m == upper.z_m - lower.z_m`。
从 `__all__` 移除。

**为什么现在构造不出来**（三层）：
1. **没有 `z_floor_m=` / `ceiling_height_m=` 这两个构造关键字了** —— 复核方原来的
   `DerivedFloorLevel(z_floor_m=12.34, ceiling_height_m=5.67)` 现在是 `TypeError`
   （测试 `test_no_raw_z_hand_fill_path_exists`：`pytest.raises(TypeError)`）。
   要把 z 塞进去，**只能**提供一条 `FloorLevelClaimV1`，而 claim 必带 `z_ref` 指向冻结字节。
2. **唯一的合法铸造者是 `derive_floor_ladder`**，而**唯一生产可达路径** `run_multifloor_correction`
   在铸造前先跑 #1 的字节门 ⇒ 「直接手造 claim」= z_m 与字节不符 = 具名变红。
3. 该类**私有**且不在 `__all__`；`z_floor_m` 是 property，`level.z_floor_m = 99.0` 抛 `AttributeError`（frozen + 无 setter）。

⇒ 「手填的 z 能装配成功」这条路在**类型层**（无关键字、无可写字段）+ **信任层**（生产入口先验字节）双重不存在。

### #3 旧生产面已迁移 —— ✅

复核方点名两处旧手填面：`DerivedFloorLevel` 公开暴露 z、`assemble_multifloor_geometry` 公开收裸 z。
全仓 `grep` 确认**除本模块与本测试外零引用**（`run_multifloor_correction` 是唯一生产消费者，无外部生产调用）。

- `DerivedFloorLevel` 公开类：**删除**（改为私有 `_DerivedFloorLevel`，见 #2 改前改后）。
- `assemble_multifloor_geometry(levels, …)`：签名保留，但 `levels` 现在只能是私有 `_DerivedFloorLevel`
  （无裸 z、只能由验字节的 `derive_floor_ladder` 铸造）⇒ 装配边界不再接收裸 z。
- `run_multifloor_correction` 入口签名从裸 claims → 封印 carrier（见 #1），生产入口即受验证的派生 carrier。

调用图 / 变异证据：
- `test_run_multifloor_has_no_z_parameter`：入口签名与 `MultiFloorPlanRun._fields` 都无 `z_floor`/`ceiling_height`。
- `test_wiring_feeds_the_derived_z_into_the_chain`：喂给每个 chain 的 z **逐个等于**派生 rung 的 z（captured，⛔ 非调用方声明）。
- `test_neutered_derivation_fails_loud_never_falls_back`：把 `derive_floor_ladder` neuter 成返回 `()` ⇒
  诚实 carrier 先过门、再因零层 `FLOOR_PLAN_COUNT_MISMATCH` 具名变红，⛔ 不回落到手填 z。

### #4 footprint 错判是结构判定 —— ✅

**做法（B-3）**：不再按 `str(exc)` 子串判定，改按 `ValidationError` 的 **loc/type 结构**：
抽出模块级判据 `_is_footprint_mismatch_error(exc)` = `所有 err 的 loc==() 且 type=="value_error"`。

**实测依据**（探针，pydantic v2）：
- 真 footprint 冲突（`schema.py:_v3_integrity` model_validator 抛 ValueError）⇒ **n=1，`type=value_error`，`loc=()`**；
- 复核方造例（必填 `name` 缺失 + `cells[0].x[0]` 类型错 + 键名撞 needle）⇒ 三条错**全部 `loc` 非空**
  （`missing`/`float_parsing`/`extra_forbidden`），而 `str(exc)` 确实含 needle —— 正是旧子串误报的根。
- 结构上（pydantic 只在字段全过后才跑 after-validator；本构造点 `windows=[]`/`facade_segments=[]`、id 已去重）
  ⇒ 此处唯一可达的 empty-loc value_error 就是 footprint。

**测试 `test_footprint_relabel_is_structural_not_substring`**（喂**真实生产判据** `_is_footprint_mismatch_error`）：

```
(a) reviewer 造例:  needle in str(exc) == True   且   _is_footprint_mismatch_error == False   ⇒ 不重贴
(b) 真 footprint 冲突:  assemble_multifloor_geometry(...).code == "PER_FLOOR_FOOTPRINT_MISMATCH" ⇒ 具名
```

复核方点名的次生风险（重贴分支里 `floor_ids = [f.id for f in floors]` 对 dict 抛 `AttributeError`）也不复存在：
该分支的 `floors` 恒为 model_copy 出的 `FloorV3` 实例。

### #5 上一轮已过审的不退化 —— ✅

17 条原测试**逐条保留**（三层混排 `test_three_storey_mixed_heights_*`、两层连续性
`test_two_storey_assembles_and_passes_pipeline_zstack_check`、具名坏输入
`test_*_is_loud` ×6、无 sm25 常量 `test_no_sm25_elevation_reading_*`、零 gt `test_new_files_never_touch_gt` 等）。
签名迁移的 3 条（wiring / neutered / real-chain）**规则不变、仅改为传封印 carrier**。

```
$ python -m pytest -q -p no:cacheprovider tests/test_b2_multifloor_assembly.py
21 passed in 7.92s            # 17 基线 + 4 返工新增
$ python -m pytest -q -n 6 -p no:cacheprovider \
    tests/test_b3_elevation_leg.py tests/test_c2_b5_host_resolution.py tests/test_tarch_elevation_must_red.py
134 passed in 20.83s          # B3 腿 / B5 host / 立面必红 均无回归
```

### #6 全量绿（`-n 6`）· 逐位闭合 —— ✅

```
$ python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
  python -m pytest -q -n 6 -p no:cacheprovider
/tmp/b2_rework_claude/src/agent/correction/multifloor.py
3777 passed, 2 skipped, 13 xfailed, 211 warnings in 455.61s (0:07:35)
```

- **逐位闭合**：基线 `3773`（3756 + 17）+ 本轮新增 **4** 条（#1 机器门 ×2、#2 类型层 ×1、#4 结构判据 ×1）= **3777**。
- `2 skipped / 13 xfailed` 与基线一致；**0 failed**，summary 行在场 ⇒ 非同机竞争假红。
- ⚠️ 同机有 GLM 席位在做 T4-a，故用 `-n 6`（非 `-n auto`），符合并发治理。
- `m.__file__` 与 pytest 同一条命令，落在本 worktree ⇒ 变异生效、非串台。

## 最薄弱一处（据实）

**B-3 的结构判据依赖「本构造点唯一可达的 empty-loc value_error 就是 footprint」这条推理，
而它建立在 `assemble_multifloor_geometry` 里 `windows=[]` / `facade_segments=[]` / id 已去重这三个当前事实上。**
判据本身（`loc==() and type=="value_error"`）是结构的、不看文本，且 `_v3_integrity` 里其余 model 级
value_error（floor-id 唯一、window/segment 引用）在本构造点都不可达 —— 但这是**当前**装配形态的性质，
不是 pydantic 层面锁死的不变量。若将来 B4 让本处开始装 windows/facade_segments，`_is_footprint_mismatch_error`
可能把另一种 empty-loc value_error 也认成 footprint。
**缓解**：判据与理由都写进了 `_is_footprint_mismatch_error` 的 docstring 与构造点注释，并由
`test_footprint_relabel_is_structural_not_substring` 喂真实造例锁住「字段错不重贴」这半。
**彻底解**（超出本单范围）：等 B4 真的往本处装 windows/segments 时，把判据收窄成「schema 对 footprint 抛的那一类」——
届时最干净的是让 schema 为 footprint 违规抛一个**可辨识的异常子类/稳定 code**，而不是继续靠「唯一可达」推理。

## 停下上报

无 A 层触发（未动 §四禁令；B-2 的「类型层不存在」已穷尽落地，见 #2 三层论证；未改任何已落库产物哈希/基线）。
B 层：上文 md 混入首 commit 一条，已据实记录、无实害。
