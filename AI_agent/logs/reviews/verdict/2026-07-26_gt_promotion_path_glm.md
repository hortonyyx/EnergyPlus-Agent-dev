# GLM-5.2 验证性对抗审 裁决书 —— GT 转正通道（2026-07-26）

- 审阅方：GLM-5.2（跨家族；施工方为 GPT 侧 terra，**谁写谁不批**）
- 被审对象：本批未提交工作树改动（`git status` 可见），契约 = [`proposals/gt_promotion_path_spec.md`](../../proposals/gt_promotion_path_spec.md)
- 核验清单：[`reviews/request/2026-07-26_gt_promotion_path_glm_checklist.md`](../request/2026-07-26_gt_promotion_path_glm_checklist.md)
- 性质：**验证性**（每条命题写死「验什么／怎么验／成立／不成立」），不要求探索性找未知缺陷

## 总裁决：APPROVE-WITH-CHANGES

命脉 §1 的 X-01/X-02/X-03 **三条全部成立**——变异矩阵是真的、不会被默认跑法跳过、期望集合没有被迁就现状。主体命题 Y-01~Y-05、Y-07、Y-08、Y-09、Y-10 成立；**Y-06 不成立**（双向完整性只到「声明集合 ↔ 固定白名单」，未到「声明集合 ↔ 目录实际文件」，包内可塞未签名文件而 validate/promote 双双放行）。Y-06 是签名绑定根完整性的真实缺口，但因 promote 落盘走固定白名单、rogue 文件不进受保护根、GT 几何/语义零影响，属 **fail-safe MAJOR** 而非阻断。X 组全过 ⇒ 不 REWORK；存在一条 MAJOR ⇒ 不直接 APPROVE。

> 命题一览：成立 12（X-01/02/03、Y-01/02/03/04/05/07/08/09/10）、不成立 1（Y-06）、无法判定 0。

---

## 1. 命脉（X 组）

### X-01 变异矩阵是真的，不是摆设 —— ✅ 成立

- **机制三处核对（源码）**：
  - `tests/test_gt_promotion_path.py:471` `assert text.count(original) == 1` —— 替换串必须恰好命中 1 次，否则该格自身 AssertionError 变红（不可能 silently pass）。✓
  - `:485` 子进程 `[sys.executable, "-m", "pytest", ..., "-m", "not mutation", "tests/test_gt_promotion_path.py"]` —— 排除自身防递归。✓
  - `:488` `assert failed == EXPECTED[mutant]` —— **集合 `==` 严格相等**，非子集、非非空。✓
- **MUTANTS 24 格**：逐条核对 `MUTANTS[mutant].original` 串与生产码逐字一致（gt_promotion.py 11 处 raise + tarch_review_bundle.py 13 处 raise/分支，共 24），每串在生产文件中唯一出现。
- **抽 8 格独立重跑**（`pytest -q "...::test_precondition_is_one_to_one_bound" -k "..."`）：6 格一次性 `6 passed, 18 deselected in 81.96s`；另补 `promote_report_all_green`、`index_file_set` 各 `1 passed`。
- **裸探针（/tmp/probe_semantic.py，零工作树改动）**对 `promote_semantic_invariant` 格：手动镜像仓库 → 应用变异 → 跑子进程，原始输出：
  ```text
  count(original) = 1  (must be 1)
  exit code: 1
  failed set: ['tests/test_gt_promotion_path.py::test_r4_3_production_path_rejects_neutered_geometry_mutation']
  == EXPECTED: ['...test_r4_3_production_path_rejects_neutered_geometry_mutation']
  strict equal: True
  1 failed, 39 passed, 24 deselected in 10.23s
  ```
  即「替换串恰好命中 1 次 + neuter 后失败集合精确等于 EXPECTED」由我独立复算证实，未采信测试内部断言。

### X-02 矩阵不会被默认跑法跳过 —— ✅ 成立

- `pyproject.toml` `[tool.pytest.ini_options]` 仅有 `pythonpath`/`testpaths`/`markers`，**无 `addopts`、无任何默认 `-m "not mutation"` 排除**（`markers` 只注册不排除）。
- `pytest --collect-only -q tests/test_gt_promotion_path.py | tail -3` → `64 tests collected`（40 常规 + 24 变异），24 格在默认收集内。

### X-03 期望集合没有被迁就现状 —— ✅ 成立

- **格 A `promote_target_root_protected`**（逻辑推理）：摘掉「目标根受保护」门后，唯一应红的是 `test_r4_unprotected_target_root_refuses`（它显式用无 marker 根期望 `promotion_gt_dir_unprotected`）；`test_r4_11_existing_target_is_untouched` 用带 marker 的 `_test_gt_root`，不受该门 neuter 影响 ⇒ 无连带。与 `EXPECTED["promote_target_root_protected"]` 一致。
- **格 B `sign_near_threshold_confirmation`**（逻辑推理）：该门只在 `sign_review_bundle` 内，promote 路径不直接查近阈值 ⇒ neuter 后只红 `test_r3_4_near_threshold_requires_explicit_confirmation`，无 promote 侧连带。与 EXPECTED 一致。
- **执行日志自述两处修正**（均经源码核实为**真修**，非调期望）：
  1. **R4-9 测试穿透**：`test_r4_9_bad_candidate_content_hash_refuses`（测试文件 `:320-331`）在注入坏 `content_sha256` 时**同步把 `index.candidate_gt_sha256` 也设成同一坏值**（`:323-324`）+ monkeypatch `load_gt_file`，使身份门（`:94` `candidate.content_sha256 != index.candidate_gt_sha256`）不先拦、能到达 content-hash 门。这是**改测试构造让锁真正可达**，不是改 EXPECTED 吸收失败。
  2. **新增 `promotion_ack_missing` guard**：`gt_promotion.py:82-83` 显式 `if not ack_path.is_file(): raise ValueError("promotion_ack_missing")`，配套 `test_r4_4_missing_ack_refuses`（`:273-276`）。是**新增生产 guard + 测试**，不是调期望。MUTANTS `promote_ack_exists` original 串与此处源码逐字一致，裸探针确认 neuter 后该测试变红。

---

## 2. 主体命题（Y 组）

### Y-01 恒真假门已彻底移除 —— ✅ 成立

- `grep -rn "canonical_write_drift" src/ tests/` → exit 1（零命中）。
- 通读 `gt_promotion.py` 全 123 行：`canonical_gt_v3_bytes(promoted)` 仅在 `:100` 用于序列化写入（`data = canonical_gt_v3_bytes(promoted)`），**非**「两次调用同一纯函数比较自己」的恒真门。`_assert_promotion_semantics`（`:60-67`）是 `candidate.model_dump` vs `promoted.model_dump` 的真比较（pop verification+content_sha256 后 `before != after`）。无恒真/恒假残留分支。

### Y-02 语义不变式真绑在生产路径 —— ✅ 成立（附 MINOR-1）

- 裸探针（/tmp/probe_semantic.py）：在镜像仓库临时把 `_assert_promotion_semantics` 的 `raise` 替换为 `pass`（等价于删除守卫调用效果），子进程跑出 `1 failed = test_r4_3_production_path_rejects_neutered_geometry_mutation`。**至少 test_r4_3 变红 ⇒ 字面成立**。
- **注意（与执行日志 r1 MAJOR-2 自述一致）**：test_r4_3 的失败根因是 neuter 后下游 `gt_source_case_mismatch at /case`，**不是**语义不变式门本身抓住的（门被 neuter 了）。即 test_r4_3 的篡改（改 `case` 字段）同时被「语义不变式门」和「下游 case 检查」双重覆盖，neuter 语义门后下游仍抓 ⇒ 该用例对语义门的绑定是**冗余绑定**。语义不变式门对「纯几何字段篡改」的独立抓力**未被任何测试直接正向验证**。施工方在执行日志 r1 已诚实标注此点。详见 MINOR-1。

### Y-03 promote 不改几何（独立构造） —— ✅ 成立

- /tmp/probe_link.py 自走链路 `build_review_bundle → sign_review_bundle → rerun_signed_review_bundle → promote_gt_v3`（目标根 /tmp），解析候选与转正 `gt.json`，**只**去 `verification` + `content_sha256` 后递归 `==`：
  ```text
  candidate==promoted after removing ONLY verification+content_sha256: True
  third-party field diffs: []
  ```
  无第三处差异。

### Y-04 可复现性（本批地基） —— ✅ 成立

- `pytest -q tests/test_tarch_converter_reproducibility.py` → `5 passed in 19.91s`（R1-1 增广 DXF 双跑字节同 / R1-2 neuter 钉死逻辑释放 / R1-3 **换 source/request ⇒ UUID5 GUID 改变**〔附加项，证钉死值是输入函数非常量〕/ R1-4 GT content_sha256 + 7 PNG 双跑字节同 / MINOR-3 ezdxf 默认 writer 等价锁）。
- 钉死逻辑 `_apply_deterministic_dxf_metadata` 由 `test_r1_2` monkeypatch 为 no-op 证明真绑（neuter 后字节由等变不等）。

### Y-05 fail-closed：无假绿转正路径 —— ✅ 成立（附 MINOR-2）

/tmp/probe_link.py + /tmp/probe_y5_5_and_y6.py 独立构造七条，**全部 raise 且 target 目录未创建**：

| # | 构造 | 实测 raise | 写入字节 |
|---|---|---|---|
| 1 | 无 `review_ack.json` | `ValueError: promotion_ack_missing` | 否 |
| 2 | ack `review_index_sha256` 改一位 | `ValueError: promotion_ack_index_mismatch` | 否 |
| 3a | `gt/gt.json` +1 字节 | `ValueError: review_index_file_hash_mismatch` | 否 |
| 3b | `gt/renders/gt_plan.png` +1 字节 | `ValueError: review_index_file_hash_mismatch` | 否 |
| 4 | `conversion_report` G1=false（status 仍 PASS） | `ConversionReportV1` ValidationError（schema「PASS⇒全绿」先抓） | 否 |
| 5 | 候选 status=human_verified（合法 methods） | `ValueError: promotion_candidate_status_invalid` | 否 |
| 6 | case 名不符 | `ValueError: promotion_candidate_identity_mismatch` | 否 |
| 7 | 目标目录已存在 | `FileExistsError: promotion_target_exists`；`keep` 字节不变 | 否 |

- 条 5 初次用非法 methods 触发 `gt_wire_invalid`（我构造错误），**重做用合法 methods 后干净命中 `promotion_candidate_status_invalid`**——`candidate_status` 门真绑。
- 条 4 的 raise 根因是 `ConversionReportV1` schema 不变式（status==PASS ⇒ all gates passed）先于 promote 的 `_all_gates_green` 抓住。`_all_gates_green` 门的「status==PASS」分支由 `promote_report_all_green` 变异格独立证明真绑（neuter 后 `test_r4_7_nonpass_report_refuses` 红）；其「逐门 passed」分支被 schema 冗余覆盖。详见 MINOR-2。任一构造均**被拒且未写入**，符合 Y-05 字面。

### Y-06 清单完整性是双向的 —— ❌ 不成立

- /tmp/probe_link.py + /tmp/probe_y5_5_and_y6.py + /tmp/probe_y6_root.py：在合法包**新增一个未列入 `review_index.json` 的文件**（`rogue_evidence.txt`），三种位置（bundle 根 / `review/` / `gt/`）全部：
  ```text
  [rogue_root.txt]         validate=PASS(escape) | promote=PASS(escape)
  [review/rogue_review.txt] validate=PASS(escape) | promote=PASS(escape)
  [gt/rogue_gt.txt]        validate=PASS(escape) | promote=PASS(escape)
  ```
- **根因**：`validate_review_index`（`tarch_review_bundle.py:77-80`）的「双向」是 `listed（index 声明集合）!= expected（_review_files 固定白名单）`，**不是**「目录实际文件集合 != index 声明集合」。`_review_files`（`:88-90`）是硬编码四类（gt.json + renders/*.png + audit + annotations），既不在白名单、也不在 index 声明里的文件完全逃逸。
- **缓解（已实测）**：promote 落盘走固定白名单（`gt_promotion.py:107-110`），rogue 不进受保护根——/tmp/probe_y6_root.py 实测 promoted 目标 13 文件无 rogue；GT 几何/语义零影响。
- **与施工方声称的落差**：执行日志 MINOR-2 自述「检测少列/多列的**双向完整性**」——在其自己口径（declared ↔ allowlist）下兑现（`test_r3_index_file_set_refuses_signature` 证明），但在清单 Y-06 口径（declared ↔ directory）下**不兑现**：人核在 bundle 目录里看到的文件集合可以与被签名校验的集合不同。

### Y-07 禁区 —— ✅ 成立

- `git status --short case_tests/` → 空。
- `git diff --name-only | grep gitignore` → 空（`.gitignore` 未碰）。
- `case_tests/test_baseline/gt/` 仅 `README.md` + `sm21_anchor`，**无 `sm24_anchor`**。
- `sm21_anchor` 不在本批 `git diff` 内（未 tracked 变更）。
- R4-15 逐字节：自算 sm21 hash（9 文件流式 sha256）全仓 pytest 跑前 = `cd5de4b0…`、跑后 = `cd5de4b0…`（identical）。施工方报 `463803b1…` 系其不同算法，我以自己 before/after 自洽为准。

### Y-08 全仓计数独立重算 —— ✅ 成立

- 命令：`python -m pytest -q -p no:cacheprovider`（**不加** `-m`，含 24 格变异）。
- 原始总结行：
  ```text
  1652 passed, 10 xfailed, 150 warnings in 875.56s (0:14:35)
  ```
- `0 failed`、`10 xfailed`（与基线一致，无数变化）、passed=`1652` 与收集数自洽。与主控独立复跑（1652/10/0）**逐数字一致**；与施工方报「1628 passed + 24 deselected」（`pytest -q -m 'not mutation'`）自洽（1628+24=1652）。警告为既有 pydantic serializer / Pillow `getdata` deprecation / flow 缺省 `run_config.yaml` RuntimeWarning，无 failed。

### Y-09 三个 CLI 可用 —— ✅ 成立

- `python scripts/tool_scripts/gt_review_sign.py --help` / `gt_promote.py --help` / `gt_review_rerun.py --help` 三 CLI 均正常，参数与细稿 §4.1/§5.1 一致（sign：`--reviewer --signed-at --confirm-near-threshold`；promote：`--case --gt-dir`；rerun：positional bundle）。
- /tmp/probe_link.py 真跑 `sign_review_bundle` 出签：磁盘 `review_ack.json` `decision=approved reviewer=glm`，且 `ack.review_index_sha256 == index.inventory_sha256`（hash 由工具从磁盘现算，未手传）。

### Y-10 诚实性核对 —— ✅ 成立（一处声称需收窄，见 MAJOR-1）

- **24 格矩阵表**：抽 8 格全过 + 裸探针 1 格原始输出，与执行日志「24 passed, 40 deselected」自洽。
- **sm21 双 snapshot**：git 层面 sm21 不在本批 diff（最强证据）+ 自算 hash before==after（`cd5de4b0…`）。
- **MINOR-3 ezdxf 等价锁**：`test_ezdxf_default_writer_matches_converter_writer_except_pinned_metadata` 实跑 `1 passed`（含于 reproducibility 5 passed）。
- **WP-1 实测非确定源清单**（`$TDCREATE/$TDUPDATE/$VERSIONGUID` + `WRITTEN_BY_EZDXF`）：与 `test_r1_2` neuter 证据自洽。
- **机械比对三处差异**（content_sha256/manifest_sha256/sources[0].content_sha256）：逻辑必然（可复现化改增广 DXF 字节 ⇒ manifest ⇒ content_sha256），执行日志已诚实记录 + 7 PNG 不同原因（候选状态条带）；Y-03 独立证明 promote 前后无第三处差异（不同比较，互补）。
- **未竟诚实标注**：执行日志「仍未闭环」段最终已不含 R3-7/R4-14/MINOR-3（均矩阵化或等价锁闭环），与实况一致。
- **落差**：MINOR-2「双向完整性」声称强于实况（见 Y-06 / MAJOR-1）。

---

## 3. Finding 清单（分级 + 可执行出口）

### MAJOR-1（Y-06）签名绑定的「双向完整性」未覆盖目录实际文件
- **现象**：bundle 内可存在既不在 `review_index` 声明、也不在 `_review_files` 白名单的文件，`validate_review_index` 与 `promote_gt_v3` 均放行。人核看到的 bundle 目录文件集合 ≠ 被签名校验的集合。
- **现实危害（已限定）**：promote 落盘白名单固定，rogue 不进受保护根；GT 几何/语义零影响。危害集中在「人核阶段可能被 bundle 内未签名附属文件误导」。
- **出口（二选一）**：
  - (A) 把完整性收严为真双向：`validate_review_index` 扫描 bundle 目录下全部文件（至少 `review_index` 声明的根 + `gt/` + `review/`），要求 `set(directory_files) == set(index.listed)`，任一多出即 `review_index_file_set_mismatch`；或
  - (B) 维护现状但**收窄声称**：在细稿/执行日志明确「签名只覆盖固定白名单文件，bundle 内允许存在未签名附属件」，并把 MINOR-2 的「双向完整性」措辞改为「声明集合 ↔ 白名单集合」，避免被解读为更强的目录级完整。
- **推荐 (A)**：本批是最高信任资产的签名绑定根，目录级完整才与人核语义（「我看了这批文件」）对齐。

### MINOR-1（Y-02）语义不变式门对「纯几何篡改」无独立正向证明
- **现象**：`test_r4_3` 篡改 `case` 字段，被语义不变式门与下游 case 检查**双重覆盖**；neuter 语义门后下游仍抓 ⇒ test_r4_3 对语义门的绑定冗余。语义门能否独立抓住「墙厚/洞口/区等几何字段」篡改未被直接验证。
- **出口**：补一条 neuter 正例——monkeypatch `_verified_document` 改一个**纯几何字段**（如某墙 `thickness` 或某面顶点），期望 `semantic_invariant_failed` 且不被下游其它门先抓；证明语义门独立抓几何篡改。

### MINOR-2（Y-05 条4）`_all_gates_green` 的「逐门 passed」分支被 schema 冗余覆盖
- **现象**：`ConversionReportV1` schema 强制 `status==PASS ⇒ all gates passed`，故「status=PASS + 某门 false」先被 schema 抓；promote 的 `_all_gates_green` 里 `all(gates.values())` 实际不可独立到达（唯有 `report.status == "PASS"` 分支独立，已由 `promote_report_all_green` 格证明）。
- **出口**：可保留为纵深防御，但建议在 `_all_gates_green` 注释标明「逐门检查由 schema 保证，此处 status 检查为独立冗余」，或在 `test_r4_7` 之外补一条能到达「逐门」分支的构造（若 schema 将来放宽）。

### NIT-1（X-01 探针）test_r4_3 失败信息当前是 `gt_source_case_mismatch`
- 非缺陷，仅信息可读性：neuter 语义门后 test_r4_3 报的是下游 case 门。执行日志已诚实标注。无需出口，登记备查。

> 无 BLOCKER。MAJOR-1 是唯一需处置项且 fail-safe（不阻断主控向用户请签与亲自转正）。

---

## 4. 实际跑过的命令清单

```text
# 基线
git status --short ; git diff --stat ; git diff --staged --stat
# 命脉 X-01
pytest -q "tests/test_gt_promotion_path.py::test_precondition_is_one_to_one_bound" \
  -k "promote_target_root_protected or sign_near_threshold_confirmation or promote_semantic_invariant or index_file_bytes or promote_candidate_content_hash or promote_ack_exists" -p no:cacheprovider
  → 6 passed, 18 deselected in 81.96s
pytest -q "...::test_precondition_is_one_to_one_bound[promote_report_all_green]" -p no:cacheprovider   → 1 passed
pytest -q "...::test_precondition_is_one_to_one_bound[index_file_set]" -p no:cacheprovider             → 1 passed
python /tmp/probe_semantic.py   # 裸探针，count==1 + failed==EXPECTED 严格相等
# 命脉 X-02
pytest --collect-only -q tests/test_gt_promotion_path.py | tail -3   → 64 tests collected
# Y-04
pytest -q tests/test_tarch_converter_reproducibility.py -p no:cacheprovider   → 5 passed in 19.91s
# Y-01/Y-07
grep -rn "canonical_write_drift" src/ tests/   → exit 1
git status --short case_tests/ ; git diff --name-only | grep -i gitignore
# Y-09
python scripts/tool_scripts/gt_review_sign.py --help
python scripts/tool_scripts/gt_promote.py --help
python scripts/tool_scripts/gt_review_rerun.py --help
# Y-03/Y-05/Y-06/Y-09 独立链路探针（/tmp，零工作树改动）
python /tmp/probe_link.py
python /tmp/probe_y5_5_and_y6.py
python /tmp/probe_y6_root.py
# Y-08 全仓（含 24 格变异，不加 -m 过滤）
python -m pytest -q -p no:cacheprovider   → 1652 passed, 10 xfailed in 875.56s
# R4-15 sm21 逐字节
python /tmp/sm21_hash.py   (pre = post = cd5de4b0…)
# 施工文件 hash 自证
for f in <9 施工文件>; do sha256sum "$f"; done | diff - /tmp/baseline_hashes.txt   → IDENTICAL
```

## 5. 结束前自证（只审不修）

- **被审施工产物逐字节未动**：开审时记录的 9 个施工文件（`pyproject.toml`、`src/agent/judge/tarch_normalize.py`、`scripts/tool_scripts/gt_{promote,review_rerun,review_sign}.py`、`src/agent/judge/{gt_promotion,tarch_review_bundle}.py`、`tests/test_{gt_promotion_path,tarch_converter_reproducibility}.py`）sha256，与审毕重算**逐文件 IDENTICAL**（`diff /tmp/baseline_hashes.txt` 空）。生产代码与测试零改动。
- **sm21 既有资产逐字节未变**：自算 sm21_anchor（9 文件）流式 sha256，全仓 pytest 跑前/跑后均为 `cd5de4b0e43e3a1feaf5c79afe38e8e6d37e2142a8093a9e7828ba658371b192`。
- **`case_tests/` 全程干净**：开审/审毕 `git status --short case_tests/` 均空；`.gitignore` 未在 `git diff` 内。
- **唯一写入的仓库文件** = 本裁决书（`AI_agent/logs/reviews/verdict/2026-07-26_gt_promotion_path_glm.md`）。所有探针脚本一律写在 `/tmp`（`probe_semantic.py`/`probe_link.py`/`probe_y5_5_and_y6.py`/`probe_y6_root.py`/`sm21_hash.py`/`baseline_*.txt`），仓库内无遗留。
- **`git diff --stat` 与开审基线的唯一差异** = 新增 `AI_agent/plan.md | 13 +++++++`。该项**非本审阅方引入**（全程未编辑 plan.md），内容经核为主控管理文档同步（记录本批立项/派工/轻门 r1·r2/GLM 审阅进行中），**非 terra 被审施工产物**（既非生产代码亦非测试）；本批被审代码/测试的 `git diff --stat`（`pyproject.toml +3` / `tarch_normalize.py +75/-6`）与开审基线**逐字节一致**。如实披露，不掩饰。
