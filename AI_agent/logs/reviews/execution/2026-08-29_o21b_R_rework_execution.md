# 施工记录 · ②-1b-R 返工：F-137 一致性门 + F-139 换轴门 + A1 集合锁 + F-136 守恒面

- **日期**：2026-08-29 · **施工**：Claude 执行档（②-1b 原席位续上下文）· **返工单**：[`request/2026-08-29_o21b_R_rework.md`](../request/2026-08-29_o21b_R_rework.md)
- **裁决依据**：[GLM 跨家族审 REWORK / 阻断 1 条](../verdict/2026-08-29_o21b_crossreview_glm.md)
- **基线**：`596258c`（= `2196723` + 主控两个纯文档提交）
- **是否触发「停下上报」**：**否**。四件事的承重前提（阻断项范围窄、不需要动架构、明确不做正交吸附）复核成立。
- ⚠️ **过程记一笔（如实记录）**：本轮施工中途撞到 Claude 家族 5 小时额度窗口被中断过一次（语法完整、未半成品，主控已核实五个文件 `ast.parse` 逐个过）。恢复后按主控给的现状表逐条复核（**结果：R1/R4 的读数基本准确，但复核过程中发现 R1 的实现有一处严重的假阳性缺陷，见下方「意外发现」**），然后完成 R2/R3。

---

## 〇、自检

```
$ git log --oneline -3
596258c 08.29j_O21bCrossReviewREWORK_ThreeClaimsIndependentlyReproduced_AndReworkDispatch
db091be 08.29i_O21bAuthoritativeGateGreen_ThreeNewFindings_AndCrossReviewRequest
2196723 08.29_O21b_RecordCommitHashInExecutionReport

$ git status --porcelain   （中断恢复时）
 M src/agent/judge/as_measured.py
 M src/agent/judge/gt_revisions.py
 M src/agent/judge/tarch_normalize.py
 M tests/test_as_measured_facts_layer.py
 M tests/test_gt_revisions_and_as_signed.py
```

五个文件逐个 `ast.parse` 通过；`git diff` 逐文件核对，确认 R1（F-137 一致性门）与 R4（F-136 守恒面）**已实现且已接线**，R2（F-139 比轴）与 R3（A1 集合整体相等）**确未做**——与主控的读数一致。

---

## 一、⭐⭐ 意外发现：R1 的原始实现有一处会误伤真实数据的假阳性（已修复）

复核 R1 时用真实 sm25 as-received 数据跑“零 revisions”的基线（验收第 3 条的最基础形式），**结果 raise 了**：

```
wall w_x_159400_160600_111200_147600 reports face_lo=159400 but
face_line_ids_lo=['140E'] actually sit at const=159396
```

排查确认：这不是缺陷，是 `AsMeasuredWallV1` 自己文档里已经点名的**合法现象**——`face_lo`/`face_hi` 是 D3 分组后**四舍五入到 1mm 的组坐标**（`denominator.GROUP_QUANT`），单条面线自己的 `const` 允许在 ±0.5mm 内偏离组坐标（`face_groups_with_a_split_const` 字段就是登记这种情况的），sm25 真实数据里 `140E`/`137B` 恰好各有一处这样的合法偏差。我最初的实现把 `wall.face_lo` 与面线**原始 `const`** 做严格相等比较，对这种早已存在、早已命名的现象产生了假阳性——如果不修，会导致真实 sm25 数据在**没有任何 revision** 的情况下也无法通过新加的门，直接违反返工单验收第 3 条。

**修法**：比较前先把面线的 `const` 按**同一条 D3 分组公式**（`round(const_m, 3)`，即四舍五入到毫米）重算成组坐标，再与 `wall.face_lo`/`face_hi` 比较——这样未经改动的面线永远吻合，只有 translate 把 const 移出原来的毫米格才会不吻合（`src/agent/judge/gt_revisions.py::_group_const_of`）。修复后重新验证：零 revision 的真实数据干净通过，同时原始 500 单位的例子、以及所有「同形输入」变体依旧正确报红（见下）。

---

## 二、四件事逐条兑现

### R1（阻断）· F-137 一致性门

`src/agent/judge/gt_revisions.py::_verify_walls_still_match_their_face_lines`，在 `derive_as_signed` 末尾对每一堵墙跑：
`face_lo`/`face_hi` 与其 `face_line_ids_lo`/`_hi` 所指面线的**组坐标**核对相等；`thickness == face_hi-face_lo`；`along_min`/`along_max` 与所指面线的实际 along 区间（`_group_along_extent`，与原配对公式 `max(lo,hi)`/`min(lo,hi)` 同式）核对相等。任一项不符 ⇒ `AsSignedReproductionError`。

**验收 1**（原始例子）：

```
$ python3 -c "... 1379 const+500 ..."
raised OK: as_signed_wall_face_lo_disagrees_with_its_face_lines: wall w_x_0_2400_52400_8640...
```

**验收 2（⭐ 关键，逐条清单，均已写成 `tests/test_gt_revisions_and_as_signed.py::test_f137_*` 提交测试）**：

| 变体 | 结果 |
|---|---|
| 换**另一条**被墙引用的面线（HI 侧而非 LO 侧，`1A2` 而非 `1A1`，同 const） | ✅ raise（`test_f137_b`） |
| 换 `field=along_min` | ✅ raise（`test_f137_c`） |
| 换 `field=along_max` | ✅ raise（`test_f137_d`） |
| 换正负位移（`-500` 而非 `+500`） | ✅ raise（`test_f137_e`） |
| 真实 sm25 数据、换一条**不同的**被墙引用面线（`13DA`，另一堵墙）+ const+500 | ✅ raise（人工复现，语义与 test_f137_b 相同） |
| 真实 sm25 数据、`1379` 的 `along_min` 越过绑定阈值（+3000，跨过邻墙 137B 的 along_min） | ✅ raise |

**验收 3**（不误伤）：
- 合成夹具零 revisions → 通过（`test_f137_f`）
- 合成夹具、面线偏离组坐标 0.4mm（复刻真实 sm25 的 140E 现象）、零 revisions → 通过（`test_f137_g`，回归锁，防止“意外发现”那处假阳性再犯）
- **真实 sm25 五条全 `unsigned` 的台账派生** → 通过（`tests/test_gt_facts_staging_sm25.py::test_3_the_staged_trio_reproduces_bit_for_bit`，用的是重新生成后的真实落盘产物，不是构造夹具）

**docstring 对齐**：`_verify_walls_still_match_their_face_lines` 的文档档明写这就是 `AsMeasuredWallV1` 之前声称存在、但全仓无代码实现的那道检查；该文档违例（指南 §五#1）已随本单代码落地而对齐——检查现在是真的了。

### R2 · F-139 换轴语义漂移

`detect_translate_candidates` 在比较三个数值字段**之前**先比 `axis`：不同轴 ⇒ 直接判 `face_line_axis_changed`（`candidate_action=None`），不再进入数值比较。

**验收**：
- 合成夹具复刻 GLM 的探针（before `axis=y,const=1000` → after 同 handle `axis=x,const=990`，数值差 10 恰好像一次平移）：修复前会被误判为合法 translate 候选；`tests/test_gt_revisions_and_as_signed.py::test_detect_axis_swap_with_numeric_coincidence_is_not_reported_as_translate` 断言修复后 `candidate_action is None` 且 `finding.check=="face_line_axis_changed"`。
- **sm25 真实五条清单逐位不变**：重新跑 `detect_translate_candidates`，仍是 2 条 translate（13AC/160A）+ 3 条 None（13AD/13AE/13AF），与返工前完全一致（这 5 个真实 handle 本身没有轴翻转，回归验证过）。

### R3 · A1 集合整体相等 + 措辞对齐

`test_f_d_d_known_pre_fix_values_are_pinned_not_recomputed` 的断言从 `in`/`not in` 改成 `KNOWN_PRE_F_D_CONVERTER_SHA256 == frozenset({sm25_report["converter_sha256"]})`，并加了一条基于 `git show a40d56d:...` 的对象级溯源断言。新增 `test_f_d_d2_the_exact_equality_assertion_actually_has_teeth` 做自证：往集合里塞一个凭空哈希后，**同一形状**的相等断言必须 `AssertionError`（构造验证，不依赖真的去改模块常量）。

`gt_raw_layer.py::_expected_converter_sha256` 的 docstring 措辞按要求加强，明确写「sm25 的 `converter_sha256` 信号在重签之前恒为 `reproduced`」（不是「漂移不可检测」这种更弱的说法），并把 GLM 独立验证过的对照实验（往闭包成员追加真实语句、观察 sm25 恒绿 / sm24 正确变红）写进注释。⛔ 只改断言与措辞，**未改** `_expected_converter_sha256` 的豁免行为本身。

### R4 · F-136 守恒面换字段

新增 `AsMeasuredConverterReadoutsV1.degenerate_line_handles`（零长丢弃，itemized）与 `s1_nonorthogonal_discarded_handles`（S1 非正交丢弃，itemized），均从 `geo.diagnostics` 按 code 转运（`tarch_wall_degenerate_line` / `tarch_wall_nonorthogonal`），**未改转换器**。`AsMeasuredViewV1._ledger_identity` **新增**（不是替换）一条更宽的恒等式：
`len(all_wall_handles) == wall_lines_total + len(s1_nonorthogonal_discarded_handles) + degenerate_line_count`，
并附带 `len(degenerate_line_handles) == degenerate_line_count` 的自洽检查。原有的窄恒等式（`wall_lines_total == face_lines + non_orthogonal + degenerate_in_wall_lines`）保留，因为它检查的是另一件事（`geo.wall_lines` 内部的真实、非空分桶），删掉会丢失一个仍然有效的检查。

`consumed_wall_handles` 全仓零写入点（`tarch_normalize.py` 里只有 `default_factory=set` 的声明，无一处赋值），已**删除**（三处测试调用点同步更新）。

**验收**（`tests/test_as_measured_facts_layer.py::test_r4_*`）：
- 真实 as-received plan-F1：`all_wall_handles=226`、`wall_lines_total=223`、`s1_nonorthogonal_discarded_handles=['13AD','13AE']`、`degenerate_line_handles=['13DC']`、`degenerate_line_count=1`，`226==223+2+1` 逐位成立（`test_r4_the_wider_s1_identity_is_real_on_as_received_plan_f1`）。
- **自证有牙**：把 `13DC` 从 `degenerate_line_handles` 删掉（保留 `degenerate_line_count=1`）⇒ 红（`as_measured_degenerate_line_handles_count_mismatch`，`test_r4_removing_13dc_from_the_itemized_list_turns_the_identity_red`）；连计数一起删（隔离测宽恒等式本身）⇒ 红（`as_measured_s1_handle_ledger_broken`，`test_r4_removing_13dc_and_its_count_together_breaks_the_primary_identity`）。
- `consumed_wall_handles` 字段确认已从模型里消失（`test_r4_consumed_wall_handles_field_is_gone`）。

⚠️ **注意**：GLM 报告里 `226==223+2+1` 的数字是在 **as-received** 图上量的（`13AD`/`13AE` 在 as-received 是非正交丢弃）。我最初把回归测试错写在 **signed** 图上，signed 图里这两条已经被拉直成干净面线，`wall_lines_total` 因此是 225 不是 223——跑出来的红让我发现了这个用错夹具的错误，改用 `as_received_doc` 后即通过。这个小插曲本身也印证了 F-136/A3 的判断是对的：两份图的非正交丢弃数量确实不同。

---

## 三、facts 落盘产物为什么变了（逐位核对，非意外）

`case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/*.json` 三份文件都因为本单重新生成而改变，逐字段核对如下（`git show HEAD:<path>` vs 当前文件，结构化 diff）：

```
as_measured.json:
  VALUE DIFF converter_implementation_fingerprint: af8eec90... -> 22b394a2...
  REMOVED    views[*]/converter_readouts/consumed_wall_handles
  ADDED      views[*]/converter_readouts/degenerate_line_handles
  ADDED      views[*]/converter_readouts/s1_nonorthogonal_discarded_handles

revisions.json:
  VALUE DIFF as_measured_content_sha256: d0fd263c... -> e5a621a8...   （仅此一处；5 条 revision 记录本身逐位不变）

as_signed.json:
  同 as_measured 的 schema 差异 + derivation 里的两个哈希跟着 as_measured/revisions 走
```

`converter_implementation_fingerprint` 会变是**预期内**的：它就是 F-D 加宽后的 `converter_sha256()`（13 文件闭包 AST 归一化哈希），而本单**真的编辑了闭包成员 `tarch_normalize.py`**（删除 `consumed_wall_handles` 字段）——这正是加宽后的指纹应该检测到的那类真实代码变化，指纹移动证明它在正确工作，不是意外。`revisions.json` 里 5 条真实记录（target/finding/candidate_action/verdict）**逐位未变**，验证了 R2 的修复没有影响 sm25 真实清单。

---

## 四、跑测

**受影响子集**：

```
python scripts/tool_scripts/affected_tests.py --changed src/agent/judge/as_measured.py \
  src/agent/judge/gt_revisions.py src/agent/judge/tarch_normalize.py src/agent/judge/gt_raw_layer.py \
  tests/test_as_measured_facts_layer.py tests/test_gt_revisions_and_as_signed.py \
  tests/test_gt_facts_staging_sm25.py tests/test_tarch_converter_reproducibility.py

跑测声明：受影响子集 = tests/test_affected_tests_map.py tests/test_as_drawn_denominator_consistency_readout.py
tests/test_as_drawn_denominator_f126.py tests/test_as_measured_facts_layer.py tests/test_gt_facts_staging_sm25.py
tests/test_gt_from_dxf.py tests/test_gt_multifloor_world_snap.py tests/test_gt_overlay.py
tests/test_gt_promotion_path.py tests/test_gt_raw_layer.py tests/test_gt_revisions_and_as_signed.py
tests/test_tarch_converter_gate_mutations.py tests/test_tarch_converter_p1_geometry.py
tests/test_tarch_converter_p2_geometry.py tests/test_tarch_converter_reproducibility.py
tests/test_tarch_elevation_must_red.py tests/test_tarch_opening_carriers.py

结果（第一次，加 R4 自证测试之前）：394 passed, 1 xfailed, exit 0
```

⚠️ **如实记录两处过程事故**：

1. 受影响子集跑完后，我启动了一次交付前全仓（后台），**但随后在它仍在运行时又编辑了 3 个测试文件**（补写 R4 自证测试 + R2/R3 措辞），违反「全量在跑时不许动树」——那次全量的读数因此作废，我在它结束前手动 kill 掉，**未采用其结果**。
2. 重新起跑的第一次全量**尾部是基础设施崩溃，不是测试变红**——`xdist` worker 在收尾阶段抛 `OSError: cannot send (already closed?)` 并刷了一屏 `PluggyTeardownRaisedWarning`，日志没能给出汇总行（这次崩溃与上一条的 kill 时机重叠，我判断是我的 `kill -9` 恰好砸在它收尾那一刻，不是并发写树造成的第二次数据损坏——但既然汇总行没出来，就不能采信，只能算「未完成」）。⇒ **两次都不采用，只采用下面第三次、全程无干预、有完整汇总行的一次**。

以下是改动全部完成、确认树干净、且这次从头到尾未被打断后重新起跑的一次：

```
$ ps aux | grep pytest    # 确认无其他进程
$ sha256sum /opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
跑前 2026-08-29T14:40:15Z  58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43 -> /workspaces/EnergyPlus-Agent-dev

$ python -m pytest -p no:cacheprovider -q
...
3305 passed, 13 xfailed, 212 warnings in 749.79s (0:12:29)
EXIT:0

跑后 2026-08-29T14:53:16Z  58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43 -> /workspaces/EnergyPlus-Agent-dev   （哨兵一致）
```

**新增测试条数逐文件拆分**（基线 `3292 passed, 13 xfailed` → 本轮 `3305 passed, 13 xfailed`，净增 **13**）：

```
tests/test_as_measured_facts_layer.py          43 -> 47   +4 条（R4 自证）
tests/test_gt_revisions_and_as_signed.py       23 -> 31   +8 条（R1 F-137 批次 7 条 + R2 换轴 1 条）
tests/test_tarch_converter_reproducibility.py  13 -> 14   +1 条（R3 A1 自证）
                                                     合计   +13 条
```

`4 + 8 + 1 = 13`，与 `3305 - 3292 = 13` 逐位对上。

⚠️ **主控点名要求解释：受影响子集只报了 `385 -> 394`（+9），全量净增 13，缺的 4 条哪来的**：
`394` 那次跑的时间点在我**补写 R4 自证测试（+4，落在 `test_as_measured_facts_layer.py`）之前**——那 4 条测试是在受影响子集跑完之后才写的，写完后我没有重新跑一次子集就直接去跑了全量。⛔ **不是 `affected_tests.py` 的映射漏了这个文件**——`test_as_measured_facts_layer.py` 本来就在受影响子集清单里（因为 `as_measured.py` 是本单改动的源文件之一，工具已经正确把它的测试文件纳入范围），只是我在它已经跑完之后又追加了测试、没有重新跑一遍子集去确认。**8 + 1 = 9** 与子集的 `+9` 完全对上（`gt_revisions_and_as_signed.py` 的 8 条 R1/R2 测试、`tarch_converter_reproducibility.py` 的 1 条 R3 测试，这些在写受影响子集命令时就已经存在）；**+4** 是后补的、只在全量里体现。这是一次操作顺序上的疏漏（该在补写后重新跑一次子集），不是工具或映射的缺陷，全量本身逐位跑过、完整覆盖了这 4 条，不影响交付质量。

---

## 五、`git diff --cached --numstat`

⛔ 只 add 明确路径，未用 `-A`/`.`。

```
204	0	AI_agent/logs/reviews/execution/2026-08-29_o21b_R_rework_execution.md
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_signed.json
1	1	case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/revisions.json
63	6	src/agent/judge/as_measured.py
17	6	src/agent/judge/gt_raw_layer.py
126	2	src/agent/judge/gt_revisions.py
11	1	src/agent/judge/tarch_normalize.py
63	5	tests/test_as_measured_facts_layer.py
146	8	tests/test_gt_revisions_and_as_signed.py
37	5	tests/test_tarch_converter_reproducibility.py
```

（本文件自身那一行 `204` 是贴入这段之前的行数，此后又追加了这段与 §六，自指滞后，不追着重贴。）

---

## 六、我认为最薄弱的一处

**R1 的假阳性插曲本身**——我在实现一个"新的一致性检查"时，第一版就撞上了系统里一个已经命名、已经存在、但我没有先去读的合法现象（`face_groups_with_a_split_const`）。这次是自己在交付前发现并修复的，但它说明：**任何"逐字段比对"式的新检查，动手前都该先问一遍"这个字段今天允许在多大范围内合法偏离，谁在容忍它"**，而不是假设"不等就是错"。这条经验本身比这次修复更值得审阅方关注——建议下一次对 `gt_revisions.py` 再加检查前，先过一遍 `AsMeasuredConverterReadoutsV1` 里所有"允许偏离/允许缺席"的字段清单。

其次，`_group_const_of` 的 1mm 容忍窗口目前是**硬编码复刻**（`_GROUP_QUANT_DECIMALS = 3`），如果 `denominator.GROUP_QUANT` 将来改变，这里不会自动跟着变——这是又一处"两份实现你必须记得一起改"的耦合，值得考虑要不要直接 import `denominator.GROUP_QUANT` 而不是复刻常量（本单未改，因为 `gt_revisions.py` 目前没有依赖 `denominator` 模块，引入这个依赖是否合适需要跨单判断）。

---

## 七、Commit

`201f47f` on `08.23_AsDrawnReading`（11 files changed, 686 insertions(+), 36 deletions(-)）
