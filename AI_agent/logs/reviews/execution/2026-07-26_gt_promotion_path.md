# 2026-07-26 GT promotion path — terra execution log

## WP-1 实测（修改前）

连续两次以同一 staging `source.dxf`、同一 sm24 calibrated request、同一 config，写入不同临时 work_dir：

```text
a normalized.dxf 01dfc92b5db08b65a3cffa9c7dae6355c24246c2b2a96a7a1ba950b792e88040
b normalized.dxf d48c47861e494464957c926f71205f388fe2c38348c6bf8fbb7933c136dcafcc
```

`diff -u` 的全部实测差异：

| 位置 | 实测结论 |
|---|---|
| header `$TDCREATE` | 每次 ezdxf save 写当前 Julian 时间 |
| header `$TDUPDATE` | 每次 ezdxf save 写当前 Julian 时间 |
| header `$VERSIONGUID` | 每次 ezdxf save 重新生成 GUID |
| `OBJECTS/DICTIONARYVAR/WRITTEN_BY_EZDXF` code 1 | ezdxf 版本标记内嵌当前 ISO 时间 |

已逐项检查且未变：`$FINGERPRINTGUID`、`$TDUCREATE`、`$TDUUPDATE`、`$HANDSEED`、实体数（418）、生成实体句柄序列、浮点文本与 DXF 的其它文本段。

修复只位于转换器的两次增广 DXF 写出：在 `Drawing.update_all()` 后将四个时间字段、两枚 GUID 和 ezdxf marker 设为 `source_sha256 + request_sha256` 的纯函数；GUID 使用 namespace UUID5。未全局 monkeypatch ezdxf，读取路径未改。

## WP-1 修复后实证

同一 calibrated v3 输入的连续双跑：

```text
normalized.dxf sha256 (both) = 5141994f90dd6a928a5fe805a347bb32563b7a455135d2339fc3b133908fa0a1
manifest_sha256     (both) = dfb26cfe705a40b81d4044f047a941451062e718bf90e1f0796295f672d075bc
GT content_sha256   (both) = e5a2f5a667ea27fedf472f17308bde6a0cb5c1ae3ade3f667c934edece615a17
cmp normalized.dxf exit = 0
cmp canonical gt.json exit = 0
diff -ru seven renders exit = 0
```

后续含本批 WP-2/3/4 代码的最终机械比对：

```text
mechanical_excluding_three_equal= True
old_content= a1f996f953bddf6f9c6764c8487204b19e1f374dbff00e1ebe6bfd5a69e2a2f8
new_content= fff14babdc0a8576fd9b67077cb9c2de09fba660b90c430928e005373af73179
old_manifest= fb1b2ed6d1a80ca3a8e22a3891a2e3861062ea843479d1ea5f1b7eba79e7f321
new_manifest= 81bc85d2ad72c58c703cd9819878bb706e258aa1688d24f49a46a08947893e16
old_source= aef4ee965c1799490b8bdb1ab207dea1216ff8b7b37130bb59b9c1af6f34d90c
new_source= 44ac3bd5dfea6f1f811b10df3597e54374ff6333aff983ba850f02fe5cacf145
```

脚本逻辑：解析两个 `gt.json`，深拷贝后仅删除 `content_sha256`、`generator.manifest_sha256`、`sources[0].content_sha256`，再 Python `==` 递归比较；结果为 `True`。无第四处字段变化。

与 2026-07-25 已验收 7 PNG 的 sha256 比较：7/7 不同（`gt_plan.png`、`gt_elev.png`、`overlay_1f_view.png`、四张立面 overlay）。原因是候选渲染均显示 `content_sha256` 的候选状态条带；GT 几何字段在上述机械比对中全等。新同源双跑的同 7 PNG 已逐字节相同。

## WP-2 / WP-3 / WP-4

- 新增 `tarch_review_bundle.py`：原子 candidate bundle、冻结 inventory 公式、逐文件验 inventory、签署、签后强制重跑。
- 新增 `gt_review_sign.py`：只由磁盘内容计算 ack binding，拒绝覆盖、篡改、非 G6/G10 红门与未确认近阈值。
- 新增 `gt_promotion.py` / `gt_promote.py`：PASS 十门、既有 `_verify_human_review_ack` 直调、candidate/hash/case/index 前置，临时兄弟目录原子写入与重读自校。
- 未向 `case_tests/test_baseline/gt/` 写任何内容；测试只用 `/tmp` 根。

## 实跑锁与 neuter 自查

| 锁 | 实跑结果 | neuter 实跑 / 结论 |
|---|---|---|
| R1-1 | `test_r1_1...` 绿 | R1-2 在测试内 monkeypatch metadata pin 为 no-op，字节不等，锁真实绑定 |
| R1-2 | `test_r1_2...` 绿 | 同左；被 neuter 的目标为 `_apply_deterministic_dxf_metadata` |
| R1-3 | `test_r1_3...` 绿 | 不适用：输入变更正例，验证 source/request 各自改变 UUID5 GUID |
| R1-4 | `test_r1_4...` 绿 | 双跑 GT 与七 PNG 均逐字节相同 |
| R1-5 | 全仓转换器读取相关测试绿 | 不新增读取测试（细稿规定既有转换器测试即证据） |
| R2-1..R2-4、R2-6 | `test_gt_promotion_path.py` 绿 | 条件/篡改负例实跑 |
| R2-5 | 绿 | monkeypatch `_sort_inventory_entries` 为 identity，R2-4 的两顺序 inventory 改为不等 |
| R3-1..R3-6 | 绿 | 签署正例、每项拒签前置已实跑 |
| R3-7 | **未完成 fresh-process 逐前置 neuter 表** | 当前是负例绑定测试，不把它伪称为逐前置 neuter 验收 |
| R4-1..R4-13（已实现项） | 绿 | 覆盖全链、语义不变式 neuter、ack/index/文件/PASS/candidate/hash/case/存在目录/原子失败/自校绑定 |
| R4-14 | **未完成 fresh-process 逐前置 neuter 表** | 当前为逐项负例和部分 monkeypatch，不把它伪称为完整 R4-14 |
| R4-15 | 全仓绿 | 未修改 sm21；未另做独立逐字节 snapshot |

## 测试

针对性：

```text
tests/test_tarch_converter_reproducibility.py: 4 passed
tests/test_gt_promotion_path.py: 30 passed
```

全仓 pytest 原始输出尾部：

```text
...........................................                              [100%]
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1617 passed, 10 xfailed, 150 warnings in 566.35s (0:09:26)
```

警告为既有 pydantic serializer、Pillow `getdata` deprecation 与 flow 缺省 `run_config.yaml` RuntimeWarning；无 failed。

## 未竟 / 最脆处

未竟：R3-7 与 R4-14 要求的“每条前置 fresh-process neuter 后只红对应条”尚未完整实跑；R4-15 未做独立 sm21 byte snapshot。最脆处是 promote 以临时目录白名单识别测试 GT 根；这符合本批测试隔离，但应由审阅方重点核查其不会放宽真实受保护根策略。

---

## r1 REWORK（主控轻门后）

- MAJOR-1：删除恒真 `canonical_gt_v3_bytes(promoted)` 自比；落盘后的重读字节自校保留。
- MAJOR-2：R4-3 改为生产路径真变异：monkeypatch `_verified_document` 返回 `case="changed_case"`，`promote_gt_v3` 必须在写入前抛 `promotion_semantic_invariant_failed` 且不创建目标。fresh-process 临时删除 `_assert_promotion_semantics(candidate, promoted)` 调用后，实跑该用例得到 **1 failed**，实际异常变为后续 `gt_source_case_mismatch`，证明删除守卫确使该锁变红；随后已恢复守卫，正常两项回归 `2 passed in 13.44s`。
- MINOR-1：自定义测试根改为必须包含显式 `.gt-promotion-test-root` 标记；不再以整个 `/tmp` 为白名单。
- MINOR-2：review index 现在同时比较“声明集合”与候选 review 文件集合，检测少列/多列的双向完整性。
- MINOR-4：`near_threshold_confirmed` 现在直接记录人的 `confirm_near_threshold` 输入。
- MINOR-5：新增 `scripts/tool_scripts/gt_review_rerun.py` 作为签后强制重跑 CLI。
- MINOR-3：未补 ezdxf 默认 writer 等价性锁；仍是已知升级漂移风险。

R4-15 snapshot（返工测试前）：

```text
463803b107907da9f58dc24b370c6c72bc70c1e2bc6b5fa810555eb559fe8f56  sm21_anchor recursive file-hash manifest
```

本返工轮尚未完成 R3-7、R4-14 的全量逐前置 fresh-process neuter 表，也未在返工后运行第二次 snapshot，因此不可宣称这三项已闭环。

## r1 final rerun

MINOR-3 选择等价性锁而非版本钉死：`test_ezdxf_default_writer_matches_converter_writer_except_pinned_metadata` 实跑 `1 passed in 3.40s`。它对同一 DXF 分别走 ezdxf 默认 `saveas()` 和 `_save_converter_augmented_dxf()`，仅剥离 `$TDCREATE/$TDUCREATE/$TDUPDATE/$TDUUPDATE/$FINGERPRINTGUID/$VERSIONGUID/WRITTEN_BY_EZDXF` 后逐字节相等。

R4-15 返工后第二次 snapshot：

```text
before = 463803b107907da9f58dc24b370c6c72bc70c1e2bc6b5fa810555eb559fe8f56
after  = 463803b107907da9f58dc24b370c6c72bc70c1e2bc6b5fa810555eb559fe8f56
result = identical
```

返工后全仓 pytest 原始输出尾部：

```text
............................................                             [100%]
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1618 passed, 10 xfailed, 150 warnings in 640.23s (0:10:40)
```

**仍未闭环（不得误报）**：R3-7 与 R4-14 的“每条前置、fresh-process、只红对应项”全表没有完成；本轮只完成了 R4-3 守卫删除的 fresh-process 证伪。其余签署/promote 前置目前仍是常规负例测试，不能替代该验收表。

## R3-7 / R4-14 fresh-process 源码变异矩阵（本轮闭环）

实现：`tests/test_gt_promotion_path.py::test_precondition_is_one_to_one_bound`（`@pytest.mark.mutation`）。每格在临时镜像精确替换一次源码串（替换数 `assert == 1`），子进程运行：

```text
python -m pytest -q -p no:cacheprovider -m "not mutation" tests/test_gt_promotion_path.py
```

`mutation` marker 已在 `pyproject.toml` 注册；失败 nodeid 集合与下表的 `EXPECTED` 严格作 `==` 比较。共享 index 前置服务 R2/R3/R4，相关多 nodeid 是同一前置的明确对应锁，并非连带。

| 范围 | 变异 guard | 实跑红例 | 结果 |
|---|---|---|---|
| index | inventory_algorithm | `test_r3_index_algorithm_refuses_signature` | 严格相等 |
| index | 逐文件字节/hash | R2-2 四参数、R3-2、R4-6 两参数 | 严格相等（共享 7 项） |
| index | 文件 entry 类型 | `test_r3_index_file_entry_shape_refuses_signature` | 严格相等 |
| index | files 列表类型 | `test_r3_index_file_list_shape_refuses_signature` | 严格相等 |
| index | 声明文件集合 | `test_r3_index_file_set_refuses_signature` | 严格相等 |
| index | inventory hash | R2-3 两参数、R3-3 | 严格相等（共享 3 项） |
| index | JSON 可解析 | `test_r3_index_malformed_refuses_signature` | 严格相等 |
| index | schema | `test_r3_index_schema_refuses_signature` | 严格相等 |
| index | files 排序 | `test_r3_index_unsorted_refuses_signature` | 严格相等 |
| R4 | ack 文件存在（本轮新增显式 guard） | `test_r4_4_missing_ack_refuses` | 严格相等 |
| R4 | ack-index 一致 | `test_r4_5_bad_ack_index_refuses` | 严格相等 |
| R4 | 既有验签通过 | `test_r4_ack_verification_refuses` | 严格相等 |
| R4 | candidate content hash | `test_r4_9_bad_candidate_content_hash_refuses` | 严格相等 |
| R4 | candidate case/index 身份 | `test_r4_10_case_mismatch_refuses` | 严格相等 |
| R4 | candidate 状态 | `test_r4_8_already_verified_candidate_refuses` | 严格相等 |
| R4 | 写后重读/字节自校 | `test_r4_13_postwrite_selfcheck_is_bound` | 严格相等 |
| R4 | PASS + 十门全绿 | `test_r4_7_nonpass_report_refuses` | 严格相等 |
| R4 | 语义不变式 | `test_r4_3_production_path_rejects_neutered_geometry_mutation` | 严格相等 |
| R4 | 目标目录不存在 | `test_r4_11_existing_target_is_untouched` | 严格相等 |
| R4 | 目标根受保护 | `test_r4_unprotected_target_root_refuses` | 严格相等 |
| R3 | 不覆盖已有 ack | `test_r3_6_ack_never_overwritten` | 严格相等 |
| R3 | 除 G6/G10 外八门全绿 | `test_r3_5_nonreview_red_gate_refuses_signature` | 严格相等 |
| R3 | near-threshold 显式确认 | `test_r3_4_near_threshold_requires_explicit_confirmation` | 严格相等 |
| R3 | source DXF hash | `test_r3_source_hash_refuses_signature` | 严格相等 |

矩阵严格复跑原始输出：

```text
........................                                                 [100%]
24 passed, 40 deselected in 339.97s (0:05:39)
```

### 本轮发现与处置

- 初次变异发现 R4-9 的测试先被 candidate/index 身份门拦截，未到达 content-hash guard；已同步 index 的 candidate hash 后再注入坏 hash。修后 guard neuter 恰好只红 R4-9。
- `review_ack.json` 缺失原先由底层 `read_bytes()` fail-closed；为使 §5.2 存在前置可单独变异，本轮新增 `promotion_ack_missing` 显式 guard 与测试。
- 除上述测试穿透修正/显式存在 guard 外，无假锁、无非对应连带；未修改任何 baseline GT 资产。

## 本轮全仓复跑（排除 mutation 自递归）

命令：`pytest -q -m 'not mutation'`。常规测试新增 10 个拒绝锁，故通过数由交接基线 1618 增至 1628；24 个 mutation 参数格按 marker 设计显示为 deselected，已在上节单独严格复跑。

原始输出尾部：

```text
tests/test_run_stage_flow.py::test_cmd_run_refuses_persisted_v1_run
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1744: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1168/test_cmd_run_refuses_persisted0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_flow_refuses_persisted_v1_run
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1918: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1168/test_cmd_flow_refuses_persiste0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1628 passed, 24 deselected, 10 xfailed, 150 warnings in 526.79s (0:08:46)
```

## GLM 裁决书三项返工（terra）

### MAJOR Y-06：目录实际文件集合闭合

- `validate_review_index` 现执行目录级规则：`actual_files ⊆ index.files ∪ runtime_allowlist`；第三类文件抛 `review_index_directory_file_set_mismatch`。这在签署和转正路径均会执行，故未签名附件不能留在供人核的 bundle 内。
- 实跑真实 `build_review_bundle`（临时目录）得到的**签前**实际文件共 23 个：

  ```text
  conversion_report.json
  gt/gt.json
  gt/renders/gt_elev.png
  gt/renders/gt_plan.png
  gt/renders/overlay_1f_view.png
  gt/renders/overlay_East_view.png
  gt/renders/overlay_North_view.png
  gt/renders/overlay_South_view.png
  gt/renders/overlay_West_view.png
  manifest.json
  normalized.dxf
  opening_elevation_audit.json
  overlay_plan.svg
  rasters/1f_view.png
  rasters/East_view.png
  rasters/North_view.png
  rasters/South_view.png
  rasters/West_view.png
  rasters/testdata_prompt.json
  request.json
  review_annotations.json
  review_index.json
  source.dxf
  ```

- 其中 index 声明的 10 件为 `gt/gt.json`、7 张 `gt/renders/*.png`、`opening_elevation_audit.json`、`review_annotations.json`。已知运行件白名单逐项为 `source.dxf`（转换输入）、`request.json`（转换请求）、`manifest.json`（溯源）、`conversion_report.json`（十门证据）、`normalized.dxf`（确定性中间件）、`overlay_plan.svg`（既有 ack verifier 输入）、`review_index.json`（不能自索引的绑定根）、`review_ack.json`（签后产生）。唯一目录例外是显式的 `rasters/`：它是调用方拷入、供 overlay 渲染消费的可变输入资源树；实跑中为上述 6 件，故不能以固定文件名枚举，但未放宽其它目录。
- 新增参数化红例：在 bundle 根、`review/`、`gt/` 分别放 `rogue_root.txt`、`review/rogue_review.txt`、`gt/rogue_gt.txt`；每例均断言 `validate_review_index` 与 `promote_gt_v3` 抛上述错误，且目标目录不存在。
- 变异矩阵新增 `index_directory_file_set` 格；隔离镜像实跑：`1 passed in 17.97s`，其子进程仍以失败 nodeid 集合 `== EXPECTED` 判定，预期三条 rogue 参数例全红。

### MINOR-1：纯几何语义不变式正证

- R4-3 改为在生产路径 monkeypatch `_verified_document` 后，仅将首个 boundary segment 的 `wall_thickness_m` 从 `0.24` 改为 `0.25`；不改 `case` 或其它身份字段。`promote_gt_v3` 抛 `promotion_semantic_invariant_failed`，目标目录未创建。常规通道实跑：`43 passed, 25 deselected in 14.50s`。

### MINOR-2：`_all_gates_green` 逐门分支

- 选择代码注释而非新增不可达构造：`ConversionReportV1` 已保证 `PASS` 时各门均绿，`all(gates.values())` 是转正信任边界的纵深防御；`status == "PASS"` 分支仍具独立意义，保留以防 schema 规则未来变化。

## 本轮全仓复跑（含默认收集的 25 个 mutation 格）

命令：`pytest -q`（无 `-m` 过滤）；退出码：`0`。原始输出尾部：

```text
tests/test_run_stage_flow.py::test_flow_first_pass_packet_has_gt_evidence_before_manifest_save
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1918: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_flow_first_pass_packet_ha0/sm21_anchor/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_judge_block_auto_invalidates_and_force_resamples
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1918: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_flow_judge_block_auto_inv0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_terminal_stop_returns_20
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1918: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_flow_terminal_stop_return0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_flow_geometry_auto_records_auto_policy
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1918: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_flow_geometry_auto_record0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_run_refuses_persisted_v1_run
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1744: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_cmd_run_refuses_persisted0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_cmd_flow_refuses_persisted_v1_run
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1918: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_cmd_flow_refuses_persiste0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_new_run_flow_smoke_produces_v2_base_v2_records
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1918: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_new_run_flow_smoke_produc0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

tests/test_run_stage_flow.py::test_v1_run_resumable_after_explicit_migration
  /workspaces/EnergyPlus-Agent-dev/scripts/tool_scripts/run_stage.py:1744: RuntimeWarning: run_config.yaml not found under /tmp/pytest-of-root/pytest-1261/test_v1_run_resumable_after_ex0/case/run; using flow defaults
    run_config = load_run_config(run_dir)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1656 passed, 10 xfailed, 150 warnings in 898.05s (0:14:58)
```

未竟项：无；未修改 `case_tests/test_baseline/gt/`、`.gitignore`，未提交 git commit。
