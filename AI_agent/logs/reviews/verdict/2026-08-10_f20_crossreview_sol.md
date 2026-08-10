# F-20 整批交叉审裁决 · sol

- 日期：2026-08-10
- 审阅对象：`3303eee` + `ab694b4`（当前 HEAD `1538948`；`ab694b4..HEAD` 的 `src/`、`tests/` 无后续漂移）
- 裁决：**CHANGES REQUIRED / 不批准进入下一阶**
- 计数：**0 BLOCKER / 1 MAJOR / 1 MINOR / 1 NIT**
- 边界：只读审代码；所有 mutation 只在 `/tmp` 的完整快照中进行，且逐份确认含 `data/dependencies/Energy+.idd`；未读取 `case_tests/test_baseline/gt/`。

当前生产码没有发现 fail-open，真实 v3 墙也确实已打通；不批准的原因在于核心“不回退 stage-root”性质仍有一条自然、可利用、且 13 把锁全部放过的回归路径。

## 1. Findings

### MAJOR-1：L2/L3/L8 没有独立绑住 resolver 级 fallback；存在 13 把锁全绿的真实绕过形态

当前实现本身是正确的：`validation_run.py:183-194` 在 V2 accepted loader 拒绝时返回 `geom=None + FAIL/ERROR`，`validation_run.py:345-351` 统一阻止 2/3 重建。我还用“accepted 被篡改 + stage-root 换成可合法构建的 legacy 几何”的当前代码探针实测：

```text
trust fail
kernel_present False
digest None
approval None
```

但现有锁只覆盖了调用者在已经形成 trust BLOCK 后仍进入 kernel 的一种 mutation。我的另一种 mutation 更接近常见的 fail-open 写法：把 `load_verified_accepted_correction(...)` 的 `except ValueError` 改为调用 `_resolve_legacy_stage_root(snapped, ...)`。在含 `data/` 的快照中运行当前 59 项定向集：

```text
clean                         : 59 passed
resolver-level fallback mutant: 59 passed
```

即 L2、L3、L4、L8 以及其余锁全部未红。L2/L3/L4 的数据拒绝夹具中 stage-root 仍是 v3；回退虽已越权读取 stage-root，却又被“legacy 状态下 v3 必拒”这条邻近防线判成 FAIL，表面状态和 digest 仍满足断言。L8 只打 generic `RuntimeError` 分支，本来就不经过这个 `ValueError` fallback。

随后在同一 mutant 下仅把 stage-root 换成一份有效 legacy geometry、用 canonical writer 配好 2/3，并篡改 accepted `output.json` 触发 loader 拒绝，得到：

```text
trust_status    not_applicable
kernel_present  True
kernel_passed   True
digest_nonempty True
approval_signed True
```

这证明不是“虽读了但仍安全”的形式盲区，而是能把损坏的 V2 权威链降级成 legacy stage-root 并签发批准。L2/L3 被 v3 stage-root 遮蔽，L8 又不覆盖数据型 `ValueError` fallback，三者合起来仍漏掉这条路径。

要求补锁：至少加入一把 V2 负向夹具，其 stage-root 是**有效、与 accepted 不同的 legacy 几何**且 2/3 与它自洽；accepted hash/缺件触发拒绝后必须仍为 `FAIL/INVARIANT`、不得出现 kernel report、digest/approval 均为空。最好再 spy `_resolve_legacy_stage_root`，明确断言 V2 分支一次也不调用它。

### MINOR-1：11 行状态表的“意外异常 ⇒ ERROR”只覆盖 accepted-loader 半段，resolver 其余入口会直接抛出

`validation_run.py:143-154` 对 `load_run_manifest` 只捕获 `ValueError`；`validation_run.py:156-161` 调 `_resolve_legacy_stage_root` 时没有状态映射。只有 V2 loader 内部的 `validation_run.py:163-194` 同时有 `ValueError => FAIL` 与 `Exception => ERROR`。

独立探针：

```text
monkeypatch load_run_manifest -> RuntimeError:
escaped RuntimeError f20-sol-manifest-dispatch-sentinel

no-manifest + malformed stage-root JSON:
escaped JSONDecodeError Expecting property name enclosed in double quotes ...
```

这分别违背设计的“意外代码异常记 ERROR”和“已知磁盘/载荷 ValueError 记 FAIL”。二者都 fail-closed，不会回退，所以不升 MAJOR；但 `validate_case` 会崩出而不是生成 `correction.accepted_artifact_trust` 报告。应扩大 resolver 的映射范围，并补 manifest-dispatch sentinel 与 malformed legacy payload 两把锁。

### NIT-1：仍有几条结构上无信息或逻辑冗余的断言

- L5 `tests/test_c2_b5_artifact_trust.py:1095`：`accepted_hash_before = record.output_hash` 后再断言同一个内存对象的同一字段未变；`validate_case` 实际重新加载另一份 manifest 对象，因此这条不能证明盘上 manifest/hash 未变。应重读盘上 manifest 或冻结 accepted bytes/hash 后比较。
- NIT-1 两参数实例的 `:1231` 与 legacy 实例的 `:1297`：先断言 `status == FAIL`，再断言 `status != NOT_APPLICABLE`，后者逻辑上恒真。可删或改成独立 reason/source 断言。

这些不削弱已有主断言，故合并计一项 NIT。

## 2. C1–C6 独立复验

### C1 — PASS

严格执行：

```bash
python -m pytest -p no:cacheprovider -q -n 8 > /tmp/f20_sol_full.log 2>&1; echo $? > /tmp/f20_sol_full.rc
```

独立证据：

```text
/tmp/f20_sol_full.rc: 0
2358 passed, 10 xfailed, 209 warnings in 442.94s (0:07:22)
```

13 把锁另跑：`13 passed in 9.52s`，rc=0。

### C2 — PASS（但受 MINOR-1 的状态映射偏离限定）

- `git diff 3303eee^ 3303eee -- src tests` 只有 `validation_run.py` 与三个测试文件；`stage_runner.py` 未改。`3303eee..ab694b4` 只改两份测试。
- `_TRUST_CHECK_ID` 的生产使用点只有 `validation_run.py:338`，加入的是 `crep`，随后 `res.reports["1_correction"] = crep`；没有进入 kernel report。
- V2 accepted source 只在 `validation_run.py:164-181` 形成；三个消费口分别是 `check_correction`（`:322-330`）、`build_geometry`（`:366-369`）、`check_kernel`（`:375-380`）。
- trust `FAIL/ERROR` 在 `:345-351` 直接停住。上文“可构建 legacy stage-root + accepted 篡改”的当前代码探针仍得到 `FAIL / no kernel / no digest / no approval`，确认当前实现没有 fail-open。

### C3 — PASS

NIT-1 的 exact neuter（manifest `ValueError` 静默当 `None`）在含 `data/` 快照中：

```text
FAILED test_f20_nit1_legacy_schema_manifest_unreadable_is_fail_closed_not_masked
1 failed, 58 passed
```

两个 v3 参数实例确实被邻近 v3 防线遮住，但新增 legacy-schema 变体精确绑住该分支。

零窗 neuter（零窗时 resolver 返回 `proof=None/evidence=None`）结果：

```text
FAILED test_f20_l1_v3_accepted_proof_reaches_validate_case[zero-window]
1 failed, 58 passed
```

with-window 实例不红，说明参数化零窗锁真实、且粒度准确。

### C4 — PASS

先扫描 `case_tests/e2e_tests/*/run_*/1_correction/correction_geometry_snapped.json`：15 份中 schema v3 恰好 1 份，即 `run_2026-08-09_f18_e2e_verify`。

将该 run 与 `case_data/` 拷到 `/tmp/f20_sol_c4.FJ32s4/`，按冻结 policy 独立运行并只在副本签发：

```text
policy                  exploratory / orthogonal_polygon / optional
trust                   pass / invariant
correction_host         pass
modelling_passed        True
kernel_host             pass
digest                  3409f90b9b8000092127875e0209767ab559ee818879ddc6af0b406dc704f4be
approval_nonnull        True
approval_digest_matches True
```

同时披露：该 run 整体 `blocked=True`，原因是缺 `4_mep/mep_output.json` 与 `5_intakeoutput/intake_output.json`；这不影响本项只验证的几何 digest/签发性质。

### C5 — PASS

定向集干净基线：`59 passed`。

1. 声称的 mutation：

```python
if manifest is None or not isinstance(manifest, RunManifestV2):
# ->
if manifest is None:
```

结果恰好 L6 红：`1 failed, 58 passed`，失败点为 V1 的 trust 从预期 `NOT_APPLICABLE` 变 `FAIL`。

2. 反方向 collapse（让 `None` 落进 V2 分支）：

```python
if manifest is not None and not isinstance(manifest, RunManifestV2):
```

L6 仍红，失败点为 no-manifest trust 从 `NOT_APPLICABLE` 变 `FAIL`；另有 parity 独立连带，共 `2 failed, 57 passed`。因此 L6 不只对原先一种塌法敏感，但后一种不是零连带。

### C6 — PASS

- 用精确的修前提交 `2c7e0a4` 的 `src/` 快照独立跑 F13 anchor，得到修前 digest：`bed87c03e4c9947858f540a638ee495658fca56545f120352ef9e4003de8a5c8`；当前实现同值。
- 在含 `data/` 的快照中于 `res.reports["2_modelling"] = krep` 前加入同一 trust row，冻结锁实际变红：

```text
expected bed87c03e4c9947858f540a638ee495658fca56545f120352ef9e4003de8a5c8
actual   1f9cc8bbff8e03821b31d9e5b5c95c75e5607d83af1bc169f9a41d21912446d5
```

定向结果为冻结锁 + parity 两项红：`2 failed, 57 passed`。故冻结锁确实绑定了 report-shape/digest 性质。

## 3. 四处重点判定

### 3.1 冻结锚点

独立扫描 `case_tests/e2e_tests` 的 38 个 `run_*`，逐个调用当前 `validate_case`：0 异常，只有 F13 一项 digest 非空，值正是冻结字面量。它是 V2 ledger + schema v1 + `base_v2`，accepted 与 stage-root bytes 相同，正中 F-20 改动的 V2 legacy 分支。

`blocked=True` 只因没有 `0_reading/*_view.json`。digest 条件在 `validation_run.py:459-472` 只依赖 2/3 文件、`geometry_consistent` 与通过的 kernel report；全局 blocker 在随后 `_finalize` 汇总。因此 `blocked` 不会让 equality 变空或削弱该锁。

判定：**对“仓内已有的非空历史 geometry approval 不失效”而言，这一个锚点是穷尽集合，足够放行该性质；不是抽样。** 它对当前历史是强锁，但对 no-manifest/V1 的通用未来兼容面没有覆盖。建议另冻一份程序化 legacy fixture 的修前 digest，降低真实 run 被搬迁/清理带来的运维脆弱性；不把此建议计缺陷。

### 3.2 13 把锁的结构恒真横扫

| # | 锁 | 判定 |
|---|---|---|
| 1 | L1 with-window | 强：trust/correction/kernel 三个 PASS + 2_modelling PASS + 非空 digest + 实签；无空比较。 |
| 2 | L1 zero-window | 强：同上，且 zero-proof neuter 精确单红。 |
| 3 | L2 output hash | 对当前 caller-level fallback 有效；但 v3 stage-root 会遮住 resolver-level fallback，纳入 MAJOR-1。 |
| 4 | L3 六件套缺件 | exact keys/files 非空，删除前有正对照；与 L2 同样存在 v3 stage-root 遮蔽，纳入 MAJOR-1。 |
| 5 | L4 v3 降 contract | `FAIL + digest None` 有效，但未断言 kernel 不出现；对选择性 fallback 粒度偏弱，纳入 MAJOR-1。 |
| 6 | L5 stage-root 篡改 | accepted/stage-root 先相等、后不等且 digest 稳定，主体有效；`:1095` 的同对象 hash 自比无信息，计 NIT-1。 |
| 7 | L6 no-manifest/V1 | 两态状态与可审性有效；`:1126` 是两次调用的确定性锁，不是历史值锁，但注释已诚实，历史性质由 #13 承担。两边此前已断言非空，不是 `None == None`。 |
| 8 | L7 v3 under legacy state | 两种状态均断言 trust FAIL；digest None 可能由 no-proof 邻近门产生，未独立钉“未进 kernel”。 |
| 9 | L8 unknown loader exception | accepted loader 单次调用、ERROR、无 kernel、无 digest，强；但未覆盖 manifest dispatcher/legacy parser，形成 MINOR-1。 |
| 10 | NIT-1 invalid JSON（v3） | 主结果被 v3-under-legacy 邻近门遮住；不是独立锁。legacy 变体 #12 承担真实绑定；`FAIL => != N/A` 冗余。 |
| 11 | NIT-1 unknown version（v3） | 同 #10。 |
| 12 | NIT-1 legacy-schema | exact neuter 精确单红，强；末尾 `FAIL => != N/A` 仍冗余。 |
| 13 | F13 frozen digest | 与完整 64-hex 字面值比较，且修前快照独立复测同值；不是 `None`、不是同实现自比，也不是只断言长度。强。 |

横扫结论：

- 未发现另一处“两边都是 `None`/空集/空列表却相等”的主断言；L6 在比较前已断言两边 digest 非空，冻结锁又以字面量兜底。
- 未发现只靠“长度 64”承担安全性质的断言。
- 发现一处同内存对象字段自快照（L5）和三次逻辑蕴含式冗余断言，计 NIT-1。
- 更危险的不是字面恒真，而是**邻近防线产生同一表面结果**：L2/L3 的 v3 stage-root 让 resolver-level fail-open 仍显示 FAIL/None，最终导致 MAJOR-1。

### 3.3 锁粒度缺口

**不同意“L2/L3/L8 已独立覆盖、不需补锁”。** 它们只覆盖“trust status 已经是 BLOCK，但调用者仍进入 rebuild”的统一后置 guard。它们覆盖不到“accepted loader 拒绝后，resolver 先降级到 legacy path，使 BLOCK 根本没有形成”的路径；我的 mutant 59/59 全绿，且有效 legacy stage-root 能产生 digest/approval。

因此必须补一把可构建 legacy stage-root 的 V2 负向锁，或直接 spy V2 分支绝不调用 legacy resolver。无需在 L4/L5/L6/L7/NIT-1 每把机械重复，但至少要有一把真正不受 v3 no-proof 门遮蔽的独立哨兵。

### 3.4 11 行状态表与 V2 legacy 风险

前 10 行均有实际分支且语义一致：

| 状态 | 实现/独立证据 |
|---|---|
| no manifest + legacy | `:156-161 -> :113-128`，L6 为 N/A，2_modelling/digest 非空 |
| V1 + legacy | 同分支，L6 为 N/A 且不升级 manifest |
| no manifest/V1 + v3 | `:114-123`，L7 为 FAIL/无 digest |
| manifest JSON/version/schema 不可解析 | `:143-154`；invalid/unknown/schema-invalid 探针均 FAIL、无 kernel/digest |
| V2 缺 accepted pointer | loader `output_coordinates.py:381-383`；独立集成探针为 FAIL、无 kernel/digest |
| output/hash 不符 | L2 + loader `:391-414`，FAIL |
| B5 六件套缺件 | L3 + contract/file guards，FAIL |
| v3 + 非 B5 contract | L4 + loader `:448-460`，FAIL |
| V2 + legacy | 独立探针为 `PASS / schema 1 / proof None / evidence None` |
| V2 + v3 | L1/C4 为 PASS，三个消费口均拿到 proof |
| 非预期异常 | **仅 V2 loader 内符合 ERROR；manifest dispatcher 与 legacy parser 不符合，见 MINOR-1** |

全盘 V2 accepted 扫描得到 5 项：1 项 downstream probe 缺 stage-root，本就不会进入该 rebuild；其余 4 项同时有 accepted/stage-root，四对 bytes 均相同，其中 3 项是 legacy、1 项是本批 v3。因此今天的 legacy 行没有造成 corpus 差异，但这确实只是语料事实。

风险判定：**接受“V2 + legacy 改读 accepted attempt”的行为改变。** 用户原则已经把 V2 ledger 指向的 accepted artifact 定为唯一权威；未来若两份几何分歧，digest 改变、旧 approval 失效并要求重批，正是应有的安全结果，不应为了维持旧 digest 回退便利副本。需要保留 release/migration 提示，但不构成本批缺陷。

## 4. 未能验证

1. 未在真实权限拒绝、设备 I/O 故障上制造 OS 级错误；MINOR-1 的“意外异常”用 sentinel 证明，已知载荷异常用 malformed JSON 证明。
2. 未对六件套的六种缺件逐种重新做本轮 mutation；本轮独立执行了 L3 的 `window_hosts.json` 集成锁，完整测试集中的既有参数化 anti-tamper 锁均通过。
3. 仓内没有第二个非空历史 digest，因而无法用第二个真实 run 交叉验证冻结锚点；没有用 `None` 结果代替证据。

## 5. 结论

修法主体当前行为正确，C1–C6 均可确认；但“V2 拒绝后绝不降级 stage-root”是本批承重性质，现有 13 把锁仍允许一个能实际签发不受信几何的自然 fail-open mutant 全绿。**先补 MAJOR-1，再复核；MINOR-1 应同批修正状态映射。**
