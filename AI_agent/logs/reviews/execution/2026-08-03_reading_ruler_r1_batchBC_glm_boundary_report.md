# R1 修尺子 · 批 B/C 施工席（GLM）边界上报

- 日期：2026-08-03
- 上报方：施工席（GLM）
- 致：orchestrator
- 性质：**派工单 §2.3 明令「发现波及信任链即停下上报，不得自行决定」的核实结论 + 若干欠规格设计边界**。未开工施工，工作树零改动。

---

## 0. 我做了什么

读完派工单 + sol 方案 + 批 A 执行日志 + 批 A 派工单裁定；对批 B（S-2/S-3）与批 C（O-1/O-3/O-4）的相关代码做了精确测绘（policy / isolation / check_reading_stage / checks.json / view_manifest / dimensioned / 渲染器 / OCR schema）。下面只报**必须 orchestrator 拍板的边界**，其余可施工部分待拍板后立即开工。

---

## 1. ⛔ 已坐实的硬阻断：把 sm24 真值 `dimensioned=true` 写进 metadata 会打穿已签字 GT 信任链

派工单 §2.3 要求我「先核实改 `case_data/testdata_prompt.json` 的波及面，发现波及信任链即停下上报」。**我已核实，确实波及，故停下上报。**

### 1.1 事实链（逐行代码）

1. `build_view_manifest` **只**从 `case_data/testdata_prompt.json` 读取，`case_metadata_sha256 = hash_bytes(raw_bytes)`（`src/agent/execution/view_manifest.py:771-778`）。改这个文件 ⇒ `case_metadata_sha256` 变。
2. `dimensioned` 是 `RequiredViewEntry` 的字段（`view_manifest.py:355`），而 `content_sha256` 对「整个 payload 减去自身」求哈希（`view_manifest.py:512-514`）。**所以 `dimensioned` 由 false→true ⇒ manifest `content_sha256` 必变**，与声明写在哪无关（写 testdata_prompt.json 也好、写独立 reviewed 文件也好，manifest 内容都变）。
3. 已签字的 sm24 GT 评分侧车 `gt/sm24_anchor/score_inputs/view_bindings.json`（`JudgeScoreViewBindingsV1`）里**冻结了** `case_metadata_sha256` 与 `base_view_manifest_sha256` 两个值（`src/agent/judge/score_schema.py:175,303`）。
4. 评分入口 `load_score_view_bindings` 把「侧车里的两个值」与「本次 run 的 live manifest 的两个值」做**四元组逐字相等校验**，不等即抛 `score_view_binding_invalid`（`src/agent/judge/score_inputs.py:81-91`，校验在 `:87`）。
5. 该入口被两条评分路径调用，`expected_*` 都取自 live manifest：`scripts/tool_scripts/score_reading_vs_gt.py:107-110`、`scripts/tool_scripts/run_stage.py:1402-1405`（`base = ViewManifest.model_validate_json(...)`，`expected_case_metadata_sha256=base.case_metadata_sha256`、`expected_base_view_manifest_sha256=base.content_sha256`）。

### 1.2 结论

- 现行已签字 GT 侧车绑的是 **dimensioned=false** 的 manifest（实证：`run_2026-08-02_sonnet_full_unsup` 的 manifest 五图全 `dimensioned: false`，且该 run 对签字 GT 出过分）。
- 一旦把 sm24 五图 `dimensioned` 改成 true，**任何后续 sm24 manifest 的 `content_sha256` 都变**，对已签字 GT 评分 ⇒ `base_view_manifest_sha256` 不匹配 ⇒ 拒出分。若同时改了 testdata_prompt.json，`case_metadata_sha256` 也变 ⇒ 双 mismatch。
- 附带：`isolation.py:333` merge 时也会用 `case_metadata_sha256` 对 binding 做重验 ⇒ **老工作区（用旧 hash 建的）改完后再也 merge 不进**（§2.3 要核实的另一条波及面，同样坐实）。

**这是 §2.3 明令「停下上报」的情形。**

### 1.3 这不是「往哪写」能绕过的

我曾考虑把声明挪到独立 reviewed 文件、不折进 `case_metadata_sha256`。但只要 `dimensioned` 这个 manifest 字段值变了，manifest `content_sha256` 就变 ⇒ GT 侧车的 `base_view_manifest_sha256` 照样失配。**唯一**能让 sm24 真值=true 且仍对签字 GT 出分的办法，是**重新生成并重签 GT 评分侧车**（一次新的 GT 签字事件）。

---

## 2. 由此引出的拍板（S-3 真值 backfill 怎么处置）

| 选项 | 做什么 | 后果 |
|---|---|---|
| **甲（推荐）** | **本批不写 sm24 真值**。只交付 S-3 的**机制 + fixture 锁**（L-20/L-21 用自造 fixture、L-22/L-23 全 fixture，不碰真 sm24/GT）+ S-2 + 批 C。sm24 真值 `dimensioned=true` 的写入随 **R2 重建基线**一起做（那时 GT 本来就要重签，§2.3「只为将来的 run 生成新 manifest」与此一致）。 | 不动签字 GT；从现在到 R2 之间 sm24 无法对现签字 GT 出分——但派工单本就禁止 A/B/C 绿之前发布任何新分，且 R2 会重签，无损失。L-13/L-20 的 fail-closed 会**迫使** R2 跑 sm24 前先写真值声明，正是预期压力。 |
| 乙 | 本批就把 sm24 五图 `dimensioned=true` 写入 metadata **并**重新生成 + 真人重签 GT 评分侧车。 | 违 §4 #2「不得原地改 GT」与签字资产只读惯例，需**单独授权 + 真人（hortonyyx）签字**；且 GT 重签是独立治理事件，不该混在修尺子批里。 |

**我的推荐：甲。** 它完全落在派工单 §2.3 两条限制内（只造将来 run 的 manifest、不改历史、不碰签字 GT），又把机制与锁全部交付。请拍：**甲还是乙？**

---

## 3. S-3 机制的另一处欠规格：声明带「来源」时写在哪、fail-closed 怎么按档位 gate

派工单 §2.2 要求每个 required view 声明 `dimensioned` **及其来源**（§2.3 还要 source image sha256 + reviewer + 日期 + 依据），且 §2.2.2 推荐 manifest wire 带 `state + authority/source_hash`。现行 `dimensioned_views` 只是 stem 字符串列表（`view_manifest.py:653-659,784-785`），**没有来源字段**。另：§2.2.1「regression/golden run 缺失声明 ⇒ provisioning 失败」要按 `run_profile` gate，但 `build_view_manifest` 是 case 级、不知 run 档位。

这是「机制对、边界留给施工方猜」的典型形状（本项目三轮 REWORK 的共同病根）。我的**建议实现**（除非 orchestrator 另定）：

- **输入侧**：`testdata_prompt.json` 增 `dimensioned_views` 结构化形态（每项 `{view, dimensioned, source:{image_sha256, reviewer, date, basis}}`）；旧「stem 字符串列表」作为兼容读法。来源不折进 `case_metadata_sha256` 之外的额外通道——它本就和 testdata_prompt.json 一起被哈希（甲方案下 sm24 真值不写入，故对签字 GT 无影响；fixture 各自自带）。
- **manifest wire 侧**：`RequiredViewEntry.dimensioned` 由 bool 升为带 `state(declared_true|declared_false|unknown) + authority/source_hash`；unknown 在 strict provisioning 被拒（L-20），legacy 已存 manifest 只读不拒（仿 exam-scope 的「读不 fail、新 strict provisioning 才 fail」）。
- **fail-closed gate**：由 provisioning wrapper（已知 run_profile）在 strict 档校验「case 是否对每个 required view 声明了 dimensioned」，缺即 `dimensioned_applicability_unknown`；`build_view_manifest` 本身保持 case 级。

**请确认是否照此实现**，或给出你想要的声明位置/wire 形态。

---

## 4. 几处较轻的设计决定（我拟按最小实现做，除非另定）

| 编号 | 决定 | 我拟这么做 |
|---|---|---|
| **G4**（S-2 policy hash 覆盖面） | `_run/run_policy.json` 的 hash 只含 `capability_profile + run_profile`（gate① `check_reading_stage` 实际消费、且决定 blocking 的两项）。§2.1 说的「validation/review 相关开关」(confirmation_policy / judge_enabled / validation_scope / require_ep) **不**进 gate① policy hash——它们不影响 reading 检查的 blocking，塞进去会把无关 toggle 耦合进 gate① 事务。exam_scope 已另立冻结。 |
| **G6**（legacy 检测） | 仿 `resolve_frozen_reading_exam_scope`：有 `_run/run_policy.json` ⇒ 用之并重验 hash；无 ⇒ 标 `legacy_defaulted=exploratory`，**只读历史 run 不 fail**；strict fail-closed（L-13）只在**新 run provisioning** 触发。 |
| **G7**（O-1 渲染落点） | 隔离路径：merge/finalization 共用 renderer 读 aggregate `views`，落 `attempts/NNN/renders/<expected_output_id>.png` + 记 source output hash/render helper version/每图状态；flat 路径保留 `0_reading/<stem>_render.png` 作「便利副本」。渲染失败 ⇒ review 标 unavailable/blocked（L-41），不吞错装 complete。 |
| **G8**（O-4 像素预算） | renderer 画布**只由结构几何/extents 决定，annotation 不扩画布**；`Image.new` 前硬限：单边 ≤ 8192px、总像素 ≤ 50M（约 330M 的 d2 产物会被拦）。超限 ⇒ 拒绝渲染并留 failure artifact，**不 clamp 后放行**。数字可调，先取这个。 |
| **G9**（O-4 OCR 越界信号） | 新增 gate① 检查 `reading.annotation_frame_bounds`：metric anchor 越结构 bounds + margin ⇒ **FLAG（advisory，不 block）** + renderer 用 bounded canvas；pixel anchor 不进 metric transform（L-52）。**不**把它升为 block（避免 §4 #1 同型误拒）。若你要 block 请示下。 |

---

## 5. 待拍板后的施工计划

- 拍板后我立即按「甲 + §3 建议 + §4 最小实现」开工。
- 顺序仍按派工单：批 B（S-2 → S-3 机制+fixture 锁，**不含 sm24 真值写入**）→ 写执行日志 → 本地提交 → 批 C（O-1/O-3/O-4）→ 执行日志 → 本地提交。不 push。
- 全仓用 `pytest -q -n 6`；每条锁做 neuter 自查（摘掉即红、零连带），诚实登记。
- sm24 真值 `dimensioned=true` 与（可能的）GT 重签，按拍板结果要么随 R2 做、要么单独授权批。

**请就 §2（甲/乙）、§3（声明/wire 形态）、§4（五条较轻决定）给出裁定。**
