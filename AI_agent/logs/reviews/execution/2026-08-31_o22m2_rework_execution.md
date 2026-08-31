# 执行档 · ②-2 **模块 2 返工**：补 F-1 载荷闭合 + F-2 ref 同源（2026-08-31）

- **返工方**：GLM 家族（模块 2 施工方）· **单据** → [../request/2026-08-31_o22m2_rework_glm.md](../request/2026-08-31_o22m2_rework_glm.md) · **裁决** → [../verdict/2026-08-31_o22m2_crossreview_claude.md](../verdict/2026-08-31_o22m2_crossreview_claude.md)
- **基线**：`31f873d`（模块 2 交件 commit）+ 本树在途改动 · **改动**：`src/agent/correction/evidence_contract.py`、`tests/test_o22m2_evidence_contract.py`（**仅此两个文件**，⛔ 未提交）
- **范围**：只补复核方点名的两条同源缺口，⛔ 不是重做。模块 3（`evidence_adapters.py`）一个字未碰。

---

## 一、动手前复跑复核方的两个复现（派工单 §一 要求，⛔ 不是转引）

探针脚本 `/tmp/o22m2_rework/probe_f1.py` / `probe_f2.py`（会话内临时件，不落仓库）。

**F-1（裁决书 §二 F-1 的 B1 形态）**——合法空产物（`face_lines=[]`、`hypotheses={}`，过 `AsDrawnPlanV2.model_validate`）+ `walls=present` + 0 claims + 0 dispositions + 0 debt：

```
$ python /tmp/o22m2_rework/probe_f1.py        # 改动前
F1 RESULT: walls=present + 0 wall_claims + 0 dispositions + 0 debt -> VALIDATES (hole confirmed)
```
与复核方读数**一字不差** ⇒ 洞是真的。

**F-2（裁决书 §二 F-2 的 A3 形态）**——两份合法产物 planA(1f)/planB(2f)（同名 F01/F02、同轴），一条 `paired_faces` claim：hypothesis/candidate/perception 都指 planA、`face_a_ref` 指 planA、`face_b_ref` 指 planB；处置自洽（planA F01 与 planB F02 被消费、其余 non_wall）：

```
$ python /tmp/o22m2_rework/probe_f2.py        # 改动前
A3/F2 RESULT: cross-floor wall (face_a on planA 1f, face_b on planB 2f) -> VALIDATES
  claim.face_a_ref.input_id = planA
  claim.face_b_ref.input_id = planB
```
与复核方读数一致 ⇒ 所有引用解得开、hypothesis/candidate 匹配、轴一致，**结构无懈可击**，洞是真的。

## 二、动手前的 neuter 基线（复核方 B3 主实验的读数）

方法照抄复核方：`git archive HEAD` 到 /tmp 副本、把 `validate_evidence_bundle` 整体替换为 no-op、`PYTHONPATH=<副本>` 跑单文件（避开 editable `.pth` 串回主树）：

```
$ cd /tmp/o22m2_neuter_before && PYTHONPATH=/tmp/o22m2_neuter_before \
    python -m pytest tests/test_o22m2_evidence_contract.py -n 4 -q
11 failed, 17 passed in 3.60s
```
与复核方读数（11 failed, 17 passed）**相同** ⇒ 基线对齐，验收 4 的对照成立。

## 三、改动清单

### `src/agent/correction/evidence_contract.py`（四处）

| 位置 | 改动 |
|---|---|
| :69–89（docstring） | 登记 F-1/F-2 两条新结构不变量（含「三个无载荷通道对 present 无意义」的口径） |
| :444 | `EvidenceDebtV1.kind` 增加 `"zero_payload_channel"`（F-1 的**显式**零载荷声明载体；与 `missing_channel`〔盖 absent 通道〕语义分开，docstring :431 写明） |
| :679–763（新函数段） | `_channel_has_payload`（walls→claims 或 dispositions；plan_openings→openings；其余三通道无载荷成员恒 False）· `_assert_channel_payload_closure`（present+零载荷+无该 channel 的 zero-payload debt ⇒ `PRESENT_CHANNEL_WITHOUT_PAYLOAD`；zero-payload debt 不带 channel ⇒ `ZERO_PAYLOAD_DEBT_WITHOUT_CHANNEL`）· `_claim_source_input_ids` + `_assert_claim_refs_single_sourced`（一条 claim 的**全部** ref 跨 ≥2 个 input_id ⇒ `CLAIM_REFS_SPAN_MULTIPLE_INPUTS`） |
| :1080 / :1255（接线） | F-2 接在 claim 循环**末尾**——⛔ 故意放在全部解引用之后，让指名 never-frozen input 的 ref 仍先报 `UNKNOWN_INPUT_ID`（更精确的诊断），否则既有锁 inv1b 的错误码会被抢；F-1 接在 channel_status 循环之后 |

### `tests/test_o22m2_evidence_contract.py`（一段新章节 + 1 行 import）

- `_empty_artifact`（:1244，复核方 F-1 形态的夹具化，自证「空产物合法」前提）
- `test_f1_present_channel_requires_payload_or_an_explicit_debt`（:1281）
- `_cross_input_artifact(cross)`（:1340，复核方 A3 形态的夹具化，`cross="face_b"`〔两面跨产物〕与 `cross="hypothesis"`〔仅 hypothesis 跨产物，证明门盖的是**全部** ref 不只两个 face ref〕两个变体；两份产物各自过 `AsDrawnPlanV2.model_validate` 自证前提）
- `test_f2_claim_refs_must_share_one_input_id`（:1457）

⭐ 「先绿后红」的机械实现：两条新门各自提取为模块级函数，测试用 `monkeypatch.setattr(evidence_contract, "<函数>", no-op)` **在本树上复现「改动前的校验器放行」**（即把新门摘掉 ⇒ validate 通过 ⇒ 洞在当前树上复现，而非转引复核方读数），随后才断言现在红。

## 四、验收逐条（命令 + 读数）

| # | 验收项 | 命令 | 读数 |
|---|---|---|---|
| 1 | F-1 反例响亮 + **诚实形态仍放行**（双向） | `python /tmp/o22m2_rework/probe_f1.py`（改后主树）；诚实形态见 `test_f1` 中段 | 改后：`REJECTED code=PRESENT_CHANNEL_WITHOUT_PAYLOAD ctx={'channel': 'walls'}`；测试内：`walls=present`+0 载荷+0 debt ⇒ 红，**加一条 `kind=zero_payload_channel, channel="walls"` 的 debt ⇒ 放行** ✓；`plan_openings` 同族（tiny 清空 opening_claims ⇒ 红，context 指名 channel）✓；无 channel 的 zero-payload debt ⇒ `ZERO_PAYLOAD_DEBT_WITHOUT_CHANNEL` ✓ |
| 2 | F-2 反例响亮 + **同源正常 claim 仍绿**（双向） | `python /tmp/o22m2_rework/probe_f2.py`（改后主树）；同源绿 = `test_f2` 开头 premise + `test_acceptance_2` 三份真实产物 | 改后：`REJECTED code=CLAIM_REFS_SPAN_MULTIPLE_INPUTS ctx={'input_ids': ['planA', 'planB']}` ✓；tiny 同源 premise 放行 ✓；三份真实产物（sm25_1f/sm25_2f/sm24_1f）在验收 5 的 30 passed 里照过 ✓ |
| 3 | 先绿后红 | `test_f1` / `test_f2` 的 `monkeypatch` 段 | 两测试各自先 neuter 新门 ⇒ `validate_evidence_bundle(art)` **放行**（BEFORE，本树复现），再断言红（AFTER）✓ |
| 4 | 既有 28 条仍全绿 + neuter **11→13** | 见下方两条命令 | 主树 30 passed（28 既有 + 2 新，零改断言）；/tmp 副本 neuter：`13 failed, 17 passed`——名单 = 复核方基线 11 条（inv1–inv8、n1_witness、observed_unclaimed、nf4_4）**原样** + `test_f1` + `test_f2` ⇒ 新门确在生产校验器里，不是测试工厂 |
| 5 | 单文件 `-n 4` 全绿 + 列改动路径 | 见下 | `30 passed in 6.86s`；改动路径 = `src/agent/correction/evidence_contract.py` + `tests/test_o22m2_evidence_contract.py`（⛔ 未 git add / 未 commit） |

**验收 4/5 的原始读数：**

```
$ python -m pytest tests/test_o22m2_evidence_contract.py -n 4 -q
30 passed in 6.86s

$ # /tmp/o22m2_neuter_after（工作树两文件拷入副本后 neuter validate_evidence_bundle）
$ cd /tmp/o22m2_neuter_after && PYTHONPATH=/tmp/o22m2_neuter_after \
    python -m pytest tests/test_o22m2_evidence_contract.py -n 4 -q
13 failed, 17 passed in 3.59s
# 红名单（sort 后）：test_f1… · test_f2… · test_inv1…inv8 · test_n1_the_sixth_state…
#   · test_nf4_4_opening_gap_index_out_of_range · test_observed_unclaimed…
```

## 五、禁令对账

| 禁令 | 对账 |
|---|---|
| 1 不改既有断言；28 锁全绿 | 既有 28 条**零改动**（diff 只有新增章节 + 1 行 import），30 passed 里含全部 28 条 ✓ |
| 2 不动 `vector_contract.py`/`pipeline.py`/`src/agent/judge/` | `git diff --stat HEAD -- <三路径>`：前两者**零 diff**；`src/agent/judge/as_measured.py` 有 +25/−1——那是 **GPT 席位（F-153 第三轮）的在途 WIP**，本会话从未打开过该文件，不碰不判 |
| 3 `nf4_1`/`nf4_2` 语义保留 | 两测试与其依赖的工厂 `_must_exist` **零改动**。其 assert 语义仍是「**今天工厂会拒**」（`SELECTED_PAIR_REFERENCES_UNKNOWN_FACE` / `BUCKET_KEY_REFERENCES_UNKNOWN_FACE` 只在测试文件里抛），⛔ 不是「校验器会拒」——校验器级对照仍是 `PAIR_HYPOTHESIS_MISMATCH`（inv3c）与 `DISPOSITION_REFERENCES_UNKNOWN_FACE`（inv2a）。本轮新增的 `CLAIM_REFS_SPAN_MULTIPLE_INPUTS` 与 `PRESENT_CHANNEL_WITHOUT_PAYLOAD` 则是**真校验器齿**（neuter 名单里 f1/f2 双红为证） |
| 4 不改已落库产物/`canonical_bytes` 面 | 新 kind 值不触任何既有 bundle 的 `content_sha256`（三份真实产物照过、acceptance_5 字节级锁仍绿为证）；`grep open\(|\.write|Path\(|gt_staging|canonical_bytes` 于本单新增行 = 无 |
| 5 不 add/commit/install/`-n auto`/全量 | 全程只跑本文件、`-n 4`；/tmp 副本实验用 `-n 4` |
| 6 F-152 | `git diff HEAD -- <两文件> | grep '^+' | grep '"src/\|"tests/\|"AI_agent/'` ⇒ 无（新增字符串常量全是 json pointer 与 channel 名） |

## 六、分层停报对账

**未触发。** 三条必停逐一核过：① 两个复现都复现出来了（§一）；② 没有任何既有锁因本单变红（§四#5）；③ F-1 的载荷闭合**不需要 adapter 信息**——`walls→wall_claims/face_dispositions`、`plan_openings→opening_claims` 都是 bundle 自己的字段，复核方的边界判断（本层就能判）成立。只记不停项：debt 的 kind 取名（`zero_payload_channel`）与错误码取名按自选落定，如上。

## 七、自报最薄弱处（请复核方往这里打）

1. ⭐ **`zero_payload_channel` debt 是自报式的**：一个懒惰的 adapter 可以给每个 present 通道永远挂一条 zero-payload debt，把 F-1 变成纸门。我认为这与 `ambiguous_face + debt` 同构——门的牙在「**不许静默**」，不在「不许为零」；「能否带着 zero-payload debt 继续走」是模块 3+/pipeline 的政策面。但「zero-payload debt 本身被滥用」这个方向**本层没有也不该有锁**，值得复核方判一下我这条边界划得对不对。
2. **已知未锁的方向（有意不锁，非遗漏）**：「present + **有**载荷 + 仍挂 zero-payload debt」（声明与事实不符的**过度声明**）我不判红——它是冗余不是静默漏洞，且多源 bundle 下「部分源空跑」的诚实记账可能长这个形状。派工单只要了两条缺口，⛔ 不自作主张扩门。
3. **F-2 把 `perception_source_ref` 也纳入了同源检查**——超出复核方字面点名的四个 ref（face_a/face_b/hypothesis/candidate）。理由：设计稿 §3.2「身份即 input_id」的自然推论是**一条 claim 的全部证据同源**；但如果模块 3 的 adapter 有合法理由让 perception_source_ref 指向聚合 manifest 之类的别处，这里会撞门。若复核方判这个扩展过了，收窄成四个 ref 是一行改动。
4. 三个无载荷通道（elevation/dimensions/room_roles）的 `present` 我做成「必须挂 zero-payload debt 才放行」而不是恒红——理由：类型层不禁构造 present 行、禁令交由显式 debt；若判「恒红」更对，改 `_channel_has_payload` 一处即可。

## 八、给主控的收尾提示

- 两文件**未提交**（归主控）；`git status` 里另有 GPT 席位在途的 `as_measured.py` 与本树模块 3 文件，均非本单所动。
- 模块 3 的派工单（§六–§八）我已读：切段改判被确认、`test_tail_segmentation_is_pinned_to_module_4` 的 pin 写法被认可，本单未触碰模块 3 任何文件。
