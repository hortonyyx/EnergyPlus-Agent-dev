# 施工执行记录 · 摊 E — F-22 BLOCKER-1 确定性核【无条件】印章

- 日期：2026-08-12 · 席位：Claude 侧 Sonnet
- 任务书：`AI_agent/logs/reviews/request/2026-08-12_e_unconditional_core_stamp_dispatch_claude.md`
- 文件所有权：`src/agent/correction/deterministic.py` + `src/agent/correction/schema.py` +
  `src/agent/judge/correction_score.py` + 新建/修改的测试
- 备份：`backup/src_history/2026-08-12_f22_blocker1/{deterministic,schema,correction_score}.py.orig`
  （备份的是本轮开工前的工作树状态，其中已含并行席位「摊 C」此前对 `deterministic.py`
  施工的 `annotation_basis_sink` 改动——本轮未触碰、未回退该部分）

## 0. 第 0 步防假验证自检（先做，做完才往下走）

在计划插入印章的位置（`apply_deterministic_core` v3 分支 `return validate_final_corrected_geometry(geom)`
前一行）写下 `raise RuntimeError("STEP0_STAMP_PROBE")`，构造「核跑过、有权威证据、证据与当前几何完全一致
（图纸本来就按外皮标注）」这个 §3 点名的坑场景（直接构造 `AuthoritativeEnvelope`/`EnvelopeAxisResolution`/
`EnvelopeCandidate`，不依赖真实 0_reading 文件），跑 `apply_deterministic_core(...)`：

```
about to call apply_deterministic_core with an envelope that agrees exactly with the current footprint...
STEP0 corrections rule_ids: []
RuntimeError: STEP0_STAMP_PROBE
```

**两件事同时坐实**：① 探针真的抛了 ⇒ 验收路径确实经过插入点；② `corrections` 打印为空列表 ⇒
§3 点名的坑不是假设，是这份最小构造上就能复现的真实场景（有权威证据、核真的跑过、
`envelope_atomic_transform` 记录仍然是零条）。探针已移除，`deterministic.py` 与探针前的备份逐字节相同
（`diff` 确认）。同一份构造后来复用为 Lock 2 的正式夹具。

## 1. 改了什么

### 1.1 `src/agent/correction/schema.py`
- 新增 `DeterministicCoreStampV1`（`extra="forbid"`，单字段 `version: str`）。
- 在 `CorrectedGeometryV3`（**只在这一层，不在共享基类 `CorrectedGeometry`**）新增字段
  `deterministic_core_stamp: DeterministicCoreStampV1 | None = Field(default=None, json_schema_extra={CORRECTION_DRAW_FORBIDDEN: True})`。
  **不放共享基类的理由**：本文件顶部原有的强约束——「V3 is deliberately a strict subclass family.
  The legacy classes above must remain wire-identical: historical V1/V2 artifacts retain their
  permissive extra fields and their existing serializer bytes.」——往共享基类加字段会改变**每一份**
  v1/v2 产物的序列化字节；而 `_is_trusted_output_convention` 本来就先判 `schema_version=="3"`，
  legacy 永不被信任，往 v3-only 加零成本、零 legacy 字节改动。
- 打了 `CORRECTION_DRAW_FORBIDDEN` 标记（与 `facade_segments`/`north_axis` 同一机制）。**验证零改动
  联动**：`parse.py`（b2 draw 门）与 `window_sources.py`（`_producer_preflight`）都是从
  `schema.draw_forbidden_field_names()`/`nested_draw_forbidden_fields()` **动态**取名单，
  `vocab.producer_facing_json_schema` 的 prompt-schema 剥离与孤儿 `$defs` 剪枝也是通用扫描——
  三处消费者全部**零编辑**自动接住新字段（均已实测，见 §5）。

### 1.2 `src/agent/correction/deterministic.py`
- 新增常量 `DETERMINISTIC_CORE_STAMP_VERSION = "1"`（本轮唯一声明处）。
- `apply_deterministic_core` 的 v3 分支尾部、`return validate_final_corrected_geometry(geom)`
  **前一行**（该分支唯一返回语句前的最后一条语句，无论走「零 intent」「rejected 回滚」「committed」
  哪条内部路径都会汇合到这一行）：
  ```python
  geom.deterministic_core_stamp = DeterministicCoreStampV1(version=DETERMINISTIC_CORE_STAMP_VERSION)
  ```
  **直接赋值，不判断「是否已有值」**——这既满足「无条件」，也顺带让一个万一混过 draw 前置门的伪造值
  在每次真实核跑过后被覆盖（belt-and-suspenders，不是唯一防线）。

### 1.3 `src/agent/judge/correction_score.py`
- `_is_trusted_output_convention` 从两个条件（`schema_version=="3"` +
  `CORRECTION_OUTPUT_CONVENTION` 未被篡改）扩到三个条件，新增
  `stamp_version == deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION`。
  **模块限定读取**（`from src.agent.correction import deterministic as deterministic_module`，
  不是 `from ... import DETERMINISTIC_CORE_STAMP_VERSION`）——与 `CORRECTION_OUTPUT_CONVENTION`
  同一条「单一声明源、禁止漂移」纪律：测试改 `deterministic_module.DETERMINISTIC_CORE_STAMP_VERSION`
  能被判卷侧实时读到，不会因为「from-import 在导入时拷贝一份」而失效。
- 顺手修了一处会跟着这次改动变得**失实**的拒判文案：原文案无条件说「schema_version 不合格」，
  但新增的三个失败原因里有两个（印章缺失 / 印章版本不对）时 `schema_version` 明明是合格的 `"3"`——
  继续用旧文案会让拒判理由本身说谎。改为按三个原因分支给出具体归因（并被 Lock 3 的测试锁住：
  拒判理由必须含 `"deterministic_core_stamp"`、不得含旧的 `"schema_version does not qualify"`）。
  **`output_convention` 返回字典的三个既有 key 未变**（`schema_version`/`trusted`/`identity`），
  只字未加——这是刻意的收敛选择，见 §4.2。

## 2. 四把锁各自绑什么 + 自证前提的实测

新文件 `tests/test_f22_blocker1_core_stamp.py`（15 个测试函数，全绿）：

| 锁 | 测试函数 | 绑的判据 | 自证前提 |
|---|---|---|---|
| **1** pre-flip 真实产物被拒判 | `test_pre_flip_real_artifact_is_rejected_and_premise_self_proven` | 真实读取 `run_2026-08-09_f17_e2e_verify/1_correction/attempts/001/output.json`（sol 复现表第一行）⇒ `trusted=False`、`boundary=None`、`wall_hits=(0,N)` 且 N>0（不是空列表，是「GT 真有内墙、全部读成 miss」，比空列表更强）、拒判证据条目在场 | **重新推导旧的一票制判据**（`schema_version=="3"` 单条件）并断言它在这份真实产物上会判 `True`——即 sol 报告里「五项全 pass」的成因；随后断言新逻辑判 `False` |
| **1b（伴随）** post-flip-pre-stamp 真实产物同样被拒判 | `test_post_flip_pre_stamp_real_artifact_also_rejected` | 真实读取 `run_2026-08-11_continuous_e2e`（sol 复现表第二行，F-17 修复后但早于本次印章）⇒ `trusted=False` | 断言磁盘上这份产物今天确实没有 `deterministic_core_stamp` 键（不是猜测） |
| **2** 零位移合法产物仍被信任 | `test_zero_displacement_legit_product_is_still_trusted` + `test_zero_displacement_via_absent_envelope_is_also_still_trusted` | 两条独立构造：①有权威证据但与当前几何一致（§3 点名场景本身，与第 0 步探针同一构造）②完全没有权威证据（`authoritative_envelope=None`）——两条都真跑 `apply_deterministic_core`，都得到 `trusted=True`、`boundary_hits()==(4,4)` | 先断言 `corrections==conflicts==unsupported==[]`（核真的跑过、真的零记录），再断言 `deterministic_core_stamp` 非空且判卷信任 |
| **3** 无印章⇒fail closed 且不像全对 | `test_fail_closed_variants_do_not_look_like_a_pass`（参数化 5 变体：键缺失/显式 None/版本"0"/"bogus"/"2"）+ `test_malformed_stamp_inner_shape_raises_at_parse_not_silently_untrusted` | 5 变体全部 `trusted=False`、`boundary=None`、`boundary_hits()==(0,0)`、拒判证据在场且文案含 `"deterministic_core_stamp"`；额外一条锁住**结构性损坏**（印章字段在但缺 `version` 子键）在 pydantic 解析阶段就 `ValidationError`，不会被判卷悄悄降级成「等同于没印章」 | 先从一份真实跑通、确认 `trusted=True` 的产物出发（sanity），再逐一 mutate |
| **4** 印章承重不是注释 | `test_stamp_value_mutation_on_product_changes_scoring_behavior`（改产物自己的印章值）+ `test_declared_trusted_version_mutation_changes_scoring_behavior`（改声明的可信版本常量，与既有 `CORRECTION_OUTPUT_CONVENTION` 自测同一手法） | 两个方向都验证：从 `trusted=True` 出发改成 `bogus` ⇒ `trusted=False`；额外验证恢复常量后判定也跟着恢复（非单向锁死） | 两条都先断言「改之前确实是 True」 |

**遮蔽自查**：Lock 2 两条构造都先独立断言「核没有报错、真的返回了、审计列表确实是空的」才继续判卷，
排除了「其实是抛异常被 pytest 判成别的失败」这类误判可能；Lock 3 的参数化夹具先断言起点
`trusted=True`（sanity），确保后续 5 种变体的红不是因为夹具本身就不成立。

## 3. neuter 两个方向的结果（行为验证，非 grep/AST）

按任务书 §5「判据 = 把印章的产出中和掉,判卷跟不跟着变」+「至少两个方向」执行，均在真实入口上做：

- **方向 A（生产侧，`test_neuter_writer_stops_stamping_judge_flips_to_reject`）**：用 `monkeypatch`
  替换 `deterministic_module.apply_deterministic_core` 本体——包一层「调用真实实现、再把它刚写的
  印章清空」，模拟「核还没学会盖章」（即改动前的核）。**`correction_score.py` 一行未动**。
  结果：同一份在 Lock 2 里验证过「不中和会判 True」的调用，中和后判卷翻成 `False`
  （`boundary=None`）。遮蔽自查已写进该测试 docstring：Lock 2 已独立证明未中和版本判 True，
  所以这里翻红只能归因于中和本身。
- **方向 B（消费侧/反向，`test_neuter_restoring_stamp_flips_judge_back_to_accept`）**：从 Lock 1
  里已证实「判 False」的真实产物出发，**不碰 `correction_score.py`**，只在拷贝上补回一个合法印章，
  判卷翻回 `True`。用于排除「一旦见过没印章的产物就永久拒判」这种单向死锁的可能——证明判定是
  逐次实时读值，不是某种缓存的单向状态。
- 两个方向都不是 grep/AST 形状匹配：A 是对**真实函数对象**做运行时替身，走**真实调用**
  （`deterministic_module.apply_deterministic_core(...)` 实际执行到底）；B 是对**真实磁盘产物**
  的**真实判卷入口**（`score_correction_geometry`）做行为对照，两次调用之间只有印章字段一个变量。

（另有一条 belt-and-suspenders 测试 `test_producer_draw_prefilling_stamp_is_rejected_at_preflight`，
验证 draw 前置门确实会拒绝模型预填印章的原始载荷——不属于任务书四把锁，是免费验证 CORRECTION_DRAW_FORBIDDEN
机制零改动联动是否成立。）

## 4. §4 两个风险的查证结果

### 4.1 加字段会不会打坏既有哈希/批准链

**结论：不会打坏；额外查到一条「结构上目前零影响、但值得记录」的相邻发现。**

顺着 `grep -rn "sha256\|hash_obj\|content_sha256"` 走了一遍 1_correction 产物的消费口：

1. **`geometry_checkpoint_digest`**（`src/agent/execution/approval.py:37`，F-20 吃过大亏的那个
   `hash_obj(kernel_check_report)` 同款结构）——直接读代码确认它哈希的是
   `building_geometry`（2_modelling 输出）+ `geometry_specs`（文本）+ `kernel_check_report`
   （2_modelling 检查报告）+ stage/check 版本串，**完全不碰 1_correction 的 `CorrectedGeometry`
   对象/`output.json` 字节**。不受影响。
2. **`PreparedCandidateIdentity`/`output_sha256`**（`finalize.py`/`stage_runner.py`/
   `output_coordinates.py`/`window_host.py` 等大量消费点）——逐一读码确认全部是**同一次运行内的
   自洽校验**（"这次算出来的字节，hash 一下等不等于这次算出来的另一份记录"），不存在「与历史某次
   运行冻结的值比对」的用法。新字段进入序列化字节 ⇒ 这些 hash 的**数值**会变（预期内），但校验的
   **逻辑**是自洽的，不会因为多了一个字段就报错。已用 `finalize.py:170-186` 的构造路径 + B5 writer
   独立重放路径（`stage_runner.py:308-349`）逐行核对，重放比较只看 `.windows`/
   `corrections`/`conflicts`/`unsupported` 几个窄字段，**不比较整份 `model_dump()`**，新字段不在
   比较范围内。
3. **`build.py:218`**（`proof_geom.model_dump(mode="json") != geom.model_dump(mode="json")`）——
   看着像「加字段会让这条全字段比较翻车」的候选，但两侧都源自**同一次运行**内先后两次对同一
   `apply_deterministic_core` 输出的复现，新字段在两侧都会一致出现，不构成新的不对称。
4. **判卷侧 sidecar 缓存**（`scripts/tool_scripts/run_stage.py::_load_valid_score_sidecar`，
   **不在本次文件所有权内，只读未改**）——这是本轮意外查到的最值得记录的一条，与「加字段打坏哈希」
   方向相反，是「**没打坏**、但也没有主动收紧」：该缓存的命中判据是
   `output_hash`（产物字节哈希）+ `scorer_schema`（`run_stage.py` 里的静态版本号，当前 `"10"`）+
   `tolerances`，**不含任何与 `_is_trusted_output_convention` 内部逻辑相关的字段**。理论上，如果
   磁盘上存在一份「用本轮改动之前、但已经是 `scorer_schema=="10"` 的代码」跑出来的 sidecar，本轮
   改动不会让它失效——会被当缓存命中直接复用，掩盖修复。**已用 `find` 扫描全仓库全部
   `score_vs_gt.json`（约 30 份）逐一读出 `scorer_schema` 字段，最大值为 `9`**（含
   `run_2026-08-11_continuous_e2e` 那份，值为 `9` 且 `output_convention: None`——它甚至不是本轮
   BLOCKER-1 第一轮判卷改动之后写的），**当前仓库里不存在任何 `scorer_schema=="10"` 的旧 sidecar**，
   所以**今天这一刻，这条风险的实际影响面是零**——凡今天在磁盘上的产物走判卷都会因为
   `scorer_schema` 不匹配而强制重算，不会绕过修复。但这是「`run_stage.py` 早先已把
   `SCORER_SCHEMA` 从 9 提到 10」这一动作（08-11 F-22 第一轮改动，commit `21b4739`）顺带带来的
   免费保护，**不是本轮主动加的防线**——`run_stage.py` 不在本次文件所有权内，我没有（也不能）
   为本轮改动再次提升该版本号。**如实标注为未验证项/未决事项**：若后续有人在 `run_stage.py`
   持有权限的批次里改动判卷相关逻辑却忘记同步提升 `SCORER_SCHEMA`，会重新打开这个口子；建议
   跟进（不在本单范围内处理）。

### 4.2 会让多少既有测试转红

**如实报数：本轮改动过程中一共发现并修复了 14 个转红的既有测试**（全部通过「补一个有效印章」或
「更新一处过时的精确计数断言」修复，**没有放宽 `_is_trusted_output_convention` 本身或任何一把锁的
判据**）：

| 文件 | 转红数 | 根因 | 修法 |
|---|---|---|---|
| `tests/test_judge_batch_b.py` | 11 | 共享夹具 `_v3_output`（多个测试复用）与真实产物
  `run_2026-08-11_continuous_e2e` 都没有印章 | ① 给 `_v3_output` 无条件注入合法印章
  （它本来就无条件注入 `schema_version:"3"`，性质相同——都是「这个夹具代表一份可信 v3 产物」的
  既有假设，只是现在多了一个必要条件）；② `test_output_convention_declaration_mutation_...`
  改为先断言磁盘产物当前确实无印章判 False（新增自证前提，见 §2 表格「1b」），再在**拷贝**上补印章继续测原有的
  `CORRECTION_OUTPUT_CONVENTION` 篡改自测 |
| `tests/test_c2_b2_v3.py` | 1 | `_mismatched_bbox_geom` 手搭 payload 没有印章，命中的是
  footprint-bounds 路由测试（R8），非本次改动的目标行为 | 给该夹具补印章 |
| `tests/test_f15_producer_schema_scope.py` | 2 | 两个**精确计数**测试断言「恰好三个字段」携带
  `CORRECTION_DRAW_FORBIDDEN` 标记 / 「stripped 后剩下的 `$defs`/`properties` 恰好是某个固定集合」——
  新字段合法地成为第四个被标记字段，这两个断言的前提被有意改变 | 更新期望集合为四个字段
  （含 `deterministic_core_stamp`），测试改名 `..._exactly_the_three_fields` →
  `..._exactly_the_four_fields`（如实反映新现实，不是放宽——两条测试仍然精确断言「不多不少」） |

**均已复核**：这些修复没有一条触碰 `_is_trusted_output_convention`、`DETERMINISTIC_CORE_STAMP_VERSION`
比较逻辑、或任何一把新锁；全部是「让既有夹具满足新的、有意加严的前提」或「更新一个因新字段合法出现
而过时的精确计数」。

## 5. 全仓汇总行

**最终权威跑测**（本轮所有改动，含全部测试修复落地之后）：见下方「6. 收尾」——因篇幅原因，权威数字
写在收尾小节，此处先记录中间过程的一次全仓（用于及早发现问题，非最终交付判据）：

- 中间跑（`fullsuite_20260812_082000`，在 `test_f15_producer_schema_scope.py` 两处修复**落地之前**
  启动，故仍包含它们）：`3 failed, 2530 passed, 10 xfailed`。三条失败：
  `test_f15_producer_schema_scope.py::test_schema_forbidden_marker_present_on_exactly_the_three_fields`
  （已修，见 §4.2）、同文件 `test_producer_schema_preserves_everything_else_byte_identical`（已修）、
  `tests/test_c2_b4b_phase_d.py::test_d6_judge_scoring_path_leaves_case_tests_byte_for_byte_unchanged`
  ——**这条单独复跑（`-p no:cacheprovider`，去并行）稳定通过**，且不在本单文件所有权内（任务书 §0
  明令「⛔ 不要动 tests/test_c2_b4b_phase_d.py（摊 D 的）」，本轮确实零改动）。**更准确的根因、非猜测**：
  用 `git status` 逐时间点核对，本轮开工时该文件**尚未被修改**（不在最初的 `modified:` 列表里），
  而到本报告收尾时它已是 `268 insertions(+), 3 deletions(-)`——即**摊 D 在本轮进行期间正对同一份
  文件做并发施工**，那次中间跑的采集/执行窗口大概率撞上了它编辑中途的一个中间状态，与本轮三份
  改动（不含任何文件系统写入语句）无关。已在最终跑测中复核为 0 failed（见下）。

## 6. 收尾：最终权威全仓结果

在 §4.2 三处测试修复（`test_judge_batch_b.py` 11 处 + `test_c2_b2_v3.py` 1 处 +
`test_f15_producer_schema_scope.py` 2 处）与本文件所有小节全部落地**之后**，独立重跑一次全仓
（`fullsuite_20260812_083138`，日志见
`/tmp/claude-0/-workspaces-EnergyPlus-Agent-dev/95485813-f489-466d-bdeb-288b7236b5e3/scratchpad/fullsuite_20260812_083138.log`，
退出码文件同目录 `.rc`）：

```
2538 passed, 10 xfailed, 211 warnings in 423.55s (0:07:03)
exit=0
```

**0 failed**。`test_c2_b4b_phase_d.py::test_d6_judge_scoring_path_leaves_case_tests_byte_for_byte_unchanged`
在这次干净重跑中**没有再次出现**——坐实了 §5 记录的判断：中间跑撞上的是摊 D 对同一文件的并发施工中间
状态，不是本轮改动引入的回归（本轮三份改动的文件不含任何文件系统写入语句，且本轮全程未碰该文件，
`git status` 逐时间点核对过）。

与任务书写明的基线 `2515 passed / 10 xfailed / 0 failed` 相比：**+23 passed，xfailed 不变，
0 failed 不变**。这 +23 不全是本轮贡献——本任务开工前工作树里已有其他并行席位（摊 C「标注法观测」
批、F-9 route② S2 shadow projector 批）留下的未提交改动与新测试文件，它们的用例也计入这次全仓总数。
**本轮自己新增的用例数（`tests/test_f22_blocker1_core_stamp.py`）= 15**（`grep -c "^def test_"` 确认
11 个测试函数，其中 Lock 3 那一个函数是 5 路参数化 ⇒ 11 − 1 + 5 = 15，与 `--collect-only` 实测的
15 条一致）；本轮同时把 §4.2 表格里 14 个既有转红测试改回绿（这部分是「让红变绿」，不新增用例数，
只改变既有用例的通过/失败状态）。

## 7. 未验证项与不确定判断（如实列出）

1. **`run_stage.py` 的 `SCORER_SCHEMA` 未被本轮提升**（见 §4.1 第 4 点）——当前零现实影响
   （磁盘上无 `scorer_schema=="10"` 的旧 sidecar），但结构上不是本轮主动关闭的口子，
   而是借用了上一轮改动顺带留下的版本号台阶。`run_stage.py` 不在本单文件所有权内，
   未做改动，仅记录。
2. **`src/agent/judge/score_schema.py::load_cached_score`（`ScoreSidecarV8/V9`「typed」判卷路径的
   缓存）未做同等深度的追查**——已确认磁盘上真实 `1_correction` sidecar 全部走的是
   `run_stage.py` 的旧版扁平 sidecar 形状（`{stage, attempt, output_hash, scorer_schema, ...}`），
   不是 V8/V9 typed 形状，本轮改动的影响面因此以旧版路径为准；但没有逐行读完 `ScoreIdentityV8`/
   `ProductIdentityV8` 的完整字段定义去证明「即使某天 correction 走 typed 路径也不会有类似的
   scorer-schema 未随语义变化而提升」的问题——按 memory「correction v3 typed 路径至今休眠、未接生产」
   的既有记录判断优先级较低，如实标注未验证。
3. **除 `tests/` 与 `AI_agent/logs/reviews/` 下的新增/修改文件外，未检索项目文档
   （如 `architecture/pipeline_stage_contracts.md`）是否有文字描述了旧的「两条件」信任公式**——
   本单任务书未要求同步文档，本轮只动了源码注释与测试；若这类文档存在会有表述过时但不影响任何
   校验/测试的风险，未纳入本次改动范围。
4. **未做任何真实 `flow`/`run_pipeline` 端到端重跑**（例如让 `run_2026-08-11_continuous_e2e`
   真的重新走一遍产出带印章的新产物）——任务书接受这是预期结果（现有产物需重跑一次才重新有分数），
   本执行只在单元/集成测试层面验证了机制本身；真实重新出分需要一次正式的端到端跑测（未在本单范围）。
