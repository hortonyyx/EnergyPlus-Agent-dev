> ⛔ **orchestrator 落库说明（2026-08-27）**：以下为 GLM 家族**写在 `/tmp/ep_g1` 里的原件逐字**，未改一字
> （⚠️ 08-27 有前科：orchestrator 从对话回复里转录的版本与复核方原件**逐字节不同**，此后一律以原件为准）。
> **总判 APPROVE / 0 阻断 / 5 条不阻断 findings（F'-1…F'-5）。**
> ⭐ 上一轮欠的 **A1（独立全量）与 A6（neuter）两格占位符本轮已补真值** —— 这是派它复审的首要目的。
> ⭐ 它按触发器 #1 的**分层版**处理了我的「3 份 vs 4 份 untracked md」题错：**只记不停**（见「orchestrator 题面写错的地方」#2）。
> ⇒ **今天改触发器这一下当场兑现了。**

---

# 跨家族复核裁决（第二轮 · 返工审）· G1：零豁免复现门

- **日期**：2026-08-27　**复核席位**：GLM 家族（`glm-5.3`）
- **施工席位**：GPT 家族 sol　**被审 commit**：`ef41a39`（worktree `/tmp/ep_g1`，分支 `wt/08.27_gt_raw_layer`）
- **返工面**：`git diff 06dd513 ef41a39` = 单提交、3 文件（`src/agent/judge/gt_raw_layer.py` · `tests/test_gt_raw_layer.py` · 施工报告），与派工单声称一致（orchestrator §七#5 假设核实成立）。
- 开工自检：`git log --oneline -1` = `ef41a39` ✅；主树未触碰；本轮所有探针均已还原，`git diff` 为空。

## 总判：**APPROVE**（0 阻断 · 5 条不阻断 findings）

上一轮 APPROVE-WITH-FINDINGS 的四条 findings：**F-1 / F-2 / F-3 已修且实测验证，F-4 按派工单 §四明确划出范围（「等真有消费者时再说」）结转债**。
本轮我把上一轮欠的 A1/A6 真正跑完，并对我自己提出的「把签字件喂进复现跑」路线做了回头验证（含 21 项篡改/形态探针 + 3 次独立 neuter）——**没有找到任何「改动内容却让门照绿」的形态**。

---

## §四 验收判据 A1–A7 逐条读数

### A1 独立全量 — **PASS**
第一个动作即跑。逐字 summary 行：

```
3046 passed, 13 xfailed, 211 warnings in 405.32s (0:06:45)
```

0 failed / 0 error，exit 0。与施工自述 R6（3046 passed / 13 xfailed / 0 failed / 211 warnings）计数完全一致（耗时 405s vs 自述 498s，同机负载差异）。较基线 3042 净增 4 条测试。

### A2 未改动树上复现门真实读数 — **PASS**
自己跑 `verify_raw_layer_reproduction("sm25-L_anchor")`：

- `status = 'reproduced'`，`differing_pointers = ()`
- detail 含 `ADVISORY: neighbouring-artefact fingerprints moved (extractor_sha256)` —— 未改动树上 advisory 通道已在响（= 签字后 extractor 组确实动过，advisory 语义正确，非误报）。

### A3 旧豁免符号消失且无换名重生 — **PASS**
- `rg "SIGNATURE_DEPENDENT_POINTERS|HUMAN_REVIEW_GATE_IDS|_pointer_is_signature_dependent"`（排除 md）**0 命中**。
- 比对路径上无任何按清单跳过：`_diff_pointers(fresh, on_disk)` 的结果**不过滤直接全量上报**。
- 唯一的「允许差异」机制是 `_verified_signed_review_material` 里对晋升件的反解（详见 §3.2）——它是**哈希链校验**（证明晋升件语义 == 签字 index 绑定的 candidate），不是「比对豁免」；且 fail-closed（P7 实测）。**不是 F-1 换位置重生。**

### A4 形态级变异 — **PASS**（11 种，无一静默绿）

| # | 形态 | 读数 |
|---|---|---|
| S1 | zones 数组重排（[0]↔[1]） | `content_mismatch` 红 |
| S2 | zone 内 edges 重排 | `content_mismatch` 红 |
| S3 | 数字→字符串（`0.12`→`"0.12"`） | **裸 `ValidationError` 炸出**（strict 模式不强转；响亮但非 verdict 通道，见 F'-2） |
| S4 | 塞未知字段 `glm_evil` | `ValidationError` 炸出（`extra="forbid"`，塞不进） |
| S5 | 删必填字段 `converter_sha256` | `ValidationError` 炸出 |
| S6 | `near_threshold_faces` → `[]`（空数组 vs 有值） | `content_mismatch` 红 |
| S7 | gate id 改名 `G6→G6X` | `ValidationError` 炸出（id 是 schema Literal，改不了名） |
| S8 | 重复 JSON 键、同值 | 照绿 —— 解析后内容等价，属「比内容不比字节」契约内（字节确实不同、语义无法洗白） |
| S9 | 等值浮点改写（`0.12`→`0.120`） | 照绿 —— 同上，内容等价 |
| S10 | 嵌套塌缩（zone → `{}`） | `ValidationError` 炸出 |
| S11 | zones 外面再包一层 list | `ValidationError` 炸出 |

未跑：Unicode 归一化（与 S8/S9 同族：解析后内容等价即绿，属契约内）。**判定：没有任何一条能「改动内容却让门照绿」。** 六种 schema 非法形态走的是裸异常路径——响亮、但不是 typed verdict（F'-2，不阻断）。

### A5 两种红分得开 — **PASS**（各造一次，自己跑）
- **content_mismatch**：克隆树上 `thickness_m 0.12→0.13` ⇒ `content_mismatch`，指名 `/zones/0/edges/0/thickness_m`（且只此一条）。
- **implementation_drift**：克隆树上改 `converter_sha256` 首位 ⇒ `implementation_drift`，`drifted_fingerprints=('converter_sha256',)`，`differing_pointers=()`。
- fingerprint 判定先行返回，漂移树不会被报成坏产物。与施工自述 R3 一致。

### A6 neuter 逐条 — **PASS**（本轮独立复验 3 条新机制，全部还原）

| neuter（我施加的形状） | `tests/test_gt_raw_layer.py` | 行为读数（我的探针） |
|---|---|---|
| **N1'** 删掉 ack/index 复制进复现目录 | **1 failed / 10 passed**，只红基线复现锁 | 未改动树退化为 `content_mismatch` + **15 个签字相关指针**（G10 evidence 全族 + G6 判定族 + `/status` + `/normalized_dxf_sha256`），与自述 N1 的「15 个」一致 |
| **N2'** 只摘「重算 files 摘要 vs index 自报值」一道 | **1 failed / 10 passed**，只红签字链锁 | 篡改 index 的 files 条目仍被**下一道锁**拦住（`review_ack_index_signature_mismatch`，仍 `inputs_unavailable`）——这条链是**双锁**，单摘一道不放行。自述 N2 称「放行为 reproduced」对应的是它同时摘两道的更宽 neuter；锁本身两条路径都红，无实质出入 |
| **N5'** 摘晋升件反解 candidate hash 校验 | **1 failed / 10 passed**，只红签字链锁 | 篡改晋升件语义（`ceiling_height_m +0.01`）错绿为 `reproduced` —— 证明反解校验正是接住晋升件篡改的那根线 |

未独立重做 N3（重复 gate id）/N4（VG 降回 advisory）：`test_r4` / `test_r5` 两条锁在 23-passed 定向与全量里均绿，代码路径（`_normalise_for_diff` 的长度断言、`_fatal_fingerprints` 拼入 vg 组）已逐行读过。**每次 neuter 后 `git checkout --` 还原，最终定向 `test_gt_raw_layer.py + test_gt_discipline.py` = 23 passed（与自述一致），`git diff` 为空。**

⚠️ 按 [[neuter-proves-wiring-not-discriminating-power]] 的口径声明：以上只证明接线；分辨力由 A4/A5 的真实篡改另证。

### A7 上一轮四条 findings 复查 — **F-1/F-2/F-3 已修，F-4 结转债**

| # | 现状 | 我的证据 |
|---|---|---|
| **F-1** 豁免清单 | **已整张删除**（非白名单化） | rg 0 命中 + diff 全文 + A3 无重生 |
| **F-2** 重复 gate id 照绿 | **已修**：重复 id ⇒ `content_mismatch`、指针 `/gates` | `test_r4` 绿 + 代码读（re-key 前断言 `len(list)==len(dict)`，ValueError 被接进 verdict 通道而非裸炸——这条做对了，恰是 F'-2 该抄的样式） |
| **F-3** VG 纯闭包却降 advisory / docstring 洞清单漏 | **选了升 fatal**；docstring 洞清单已含 `gt_schema` | `test_r5` 绿 + fatal 集读码（converter/judge_config/vg_config + vg_implementation）；洞清单现为 `gt_extraction / gt_manifest / gt_schema / tarch_converter_schema` |
| **F-4** `inputs_unavailable`/`not_attempted` 无生产消费者 | **仍开放** —— 但派工单 §四明确「⛔ F-4 不做（等真有消费者时再说）」⇒ 按单执行，非未完成交付 | 窄+宽两轮 grep（`verify_raw_layer_reproduction|load_gt_raw_layer|RawLayerTrust|GtRawLayer|reproduction_status|inputs_unavailable|not_attempted|trustworthy`）：**生产代码 0 消费方**，全部命中为无关注释/测试 |

---

## §三 五处重点逐条结论

### 3.1 「把签字件喂进复现跑」会不会自证？—— **不会（内容侧实测不成立），带一个已定名的残留**

这是我上一轮提的路线，本轮回头验。**实测判据与结果**：

1. **喂进去的两份文件不是从被审报告派生的**（实测）：`review_index.json` 的 files 清单 = `gt/gt.json` + 8 张 renders/overlays + `opening_elevation_audit.json` + `review_annotations.json`；`_RUNTIME_BUNDLE_FILES` 明确把 `conversion_report.json`、`review_ack.json`、`review_index.json` 都列为**不进 index 的运行时文件**。ack 签的是 dxf 字节哈希、request 内容哈希、files 清单规范摘要——**没有一样来自被审的那份报告**。
2. **喂之前先按签字链验过，且链条独立于报告**：门自己**重算** files 规范摘要（不信自报值）⇒ 要求 == index 自报 == ack 签值；再用反解把晋升件 gt.json 绑回 index 的 `candidate_gt_sha256`；reviewer/signed_on 与晋升件交叉核对。
3. **ack 对复现输出的影响面实测**：单翻 `near_threshold_confirmed`（P2）⇒ 恰好 8 个指针动（G10 evidence 的确认位 + G6 的判定/确认戳 + `/status` + `/normalized_dxf_sha256`），**几何指针一个不动**；篡改 G10 evidence 里的 reviewer（P1）⇒ `content_mismatch` 指名 `/gates/G10/...`。
4. **结论**：这些字段对人审件的依赖是**定义使然**（旧 docstring 早就写明 G6/G10 的判定「是人签的函数、不是图纸的函数」）。喂进去是**补齐原跑输入**，而且比旧豁免设计**强**：旧设计对这 8 族指针**完全免检**（塞什么假 evidence 都行），新设计要求它们与签字件**逐字段一致**。
5. **残留（不阻断，F'-3 相邻）**：`near_threshold_confirmed` 这个 bool 在链条里没有交叉绑定（reviewer/日期有、它没有），它的信任根只剩 git 提交历史——但这是**整份 gt.json 答案层同级的保护**（能改它的人直接就能改答案），不构成对本门的额外削弱。

### 3.2 「反解允许的变化再重算哈希」—— **不是 F-1 换位置重生：清单有生产者锚，fail-closed 与掩护面均已实测**

1. **清单谁定的**：反解的更新集（`status→candidate / reviewer_id→None / reviewed_on→None / methods→[]` + `content_sha256` 重算）**逐字镜像晋升生产者自己的变换**（`gt_promotion.py` L52–61 的 update 字典 + content_sha256 重算），而晋升代码自带纪律断言（L65–69「Promotion may alter verification evidence and its dependent content hash only」）；candidate 侧三字段必须为空还有 **schema 锚**（`gt_schema.py` `gt_wire_candidate_verification_invalid`）。**不是施工方就地枚举。**
2. **多一个合法可变字段会怎样**（实测 P7）：给 verification 塞 `promotion_note` ⇒ `inputs_unavailable`（`promoted_gt_invalid`），**fail-closed 属实，自述没说谎**。原因结构性成立：content hash 覆盖除自身外全部字段（含 verification），任何反解没覆盖的晋升变化都会让重算对不上签字 candidate。
3. **反解写错/少算会怎样**：反解漏 reset 一个字段 ⇒ candidate 带着晋升痕迹 ⇒ 哈希对不上签字值 ⇒ 红（fail-closed）。**掩护面实测（P6）**：篡改晋升件的 `verification.methods` ⇒ 门**仍绿**——反解把这个字段 reset 回 `[]` 再哈希，签字链管不到它。掩护面 = **恰好 `verification.methods` 一个元数据字段**（status/reviewer/日期有交叉核对，其余全在哈希里）。不阻断，登记 F'-3。

### 3.3 删掉豁免清单后分辨力有没有退化 — **没有**（A4 表 + G6 几何证据专项）
换方向自造 11 种形态（见 A4），无静默绿。G6 几何证据族专项：`near_threshold_faces` 清空（S6）⇒ 红；施工的 `area_m2 2.544→2.545` 变异由新增 `test_r2` 锁死（23-passed 内含）。**「喂签字件 ⇒ 人审门整段失去比对」的担忧实测不成立**——判定与确认戳仍比对（P1/P2 都红），只是现在它们有合法的求值环境。

### 3.4 施工方自认「最可能塌」四条 — 逐条定性
1. **request 可得性**：⚠️ **不是假设风险，已经在现存第二份 case 上发生**——sm24_anchor 也有 `review/conversion_report.json`，我实跑 ⇒ `inputs_unavailable`（experiments 下无 request.json 能重算出签字哈希）。fail-closed 行为正确（响亮、不假绿），但**门的可用面 = 现存 2 份 case 里的 1 份**。且「响亮」目前只到返回值为止（F'-1/F'-4）。
2. **晋升语义将来扩字段** ⇒ fail-closed：实测成立（P7）。
3. **归因盲区**（4 文件在闭包内无精确指纹 ⇒ 抓得住、报成 `content_mismatch` 而非 `implementation_drift`）：**不阻断**。仍是红、仍是响亮、清单已在 docstring 诚实声明；属归因精度债。
4. **单 case 证据**：现存全集其实是两份（sm25+sm24），其中一份输入缺失。就本单范围（G1 门本体 + sm25 锚点 case）**可接受**；sm24 的 request 找回或明确放弃，登记进 plan（F'-5）。

### 3.5 F-3 选「VG 升 fatal」的代价 — **选择成立，但代价要说破**
- **误报路径存在且很快会踩**：vg 组 = `correction/{facade_visibility,facade,footprint,schema}.py` 四件，指纹是**文件粒度**不是行为粒度——只改 `correction/schema.py` 里与转换无关的行（本批 reading/correction 一体改的主战场！）也会 ⇒ `implementation_drift`。**本批期间这道门对 sm25 预计常红**，直到下次重签。
- 为什么仍成立：归因不错（确实「这棵树不再是产出该报告的实现」——说的是真话）；verdict 文案已自带解释（"re-check after aligning the tree"）；且组内无闭包外文件，不会把 CLI-only 编辑这类假漂移混进来（extractor 当初降 advisory 防的正是那个）。
- 代价的消化方式是**流程性**的（红 = 「树动了」的信号 + 重签仪式），不是代码能消的。写进裁决供 orchestrator 排期时知情。

---

## Findings

### 阻断
**无。**

### 不阻断（按重要度排序）

- **F'-1（= 上一轮 F-4，结转债，派工单已划出范围）**：复现门与 `RawLayerTrust` 至今**零生产消费方**（窄+宽 grep 实测）。`inputs_unavailable` / `not_attempted` 的「响亮」只存在于返回值与测试断言里——**接线时消费者必须把非 `reproduced` 一律当红**，否则降级显式化的最后一环仍然悬空。配套实况：sm24 已因 request 缺失真实处于该状态（F'-5）。
- **F'-2 crash 通道不 typed**：盘上报告 schema 非法（6/11 种形态）时 `verify_raw_layer_reproduction` 以**裸 `ValidationError`** 退出（`gt_raw_layer.py:472` 的 `model_validate_json` 不在 try 内），而非四态 verdict。今天响亮无害（且无消费者）；**接线之日就是隐患**——调用方对异常的处理若与 verdict 分叉，「响亮」就漏气。修法应照抄本单 F-2 的样式：接进 `content_mismatch`（或专设状态）+ 指针取自校验错误路径。
- **F'-3 反解掩护面 = `verification.methods`**：实测篡改该字段门照绿（P6）。纯元数据、动不了几何（其余全被签字 candidate 哈希绑死），但当前签字链对它零绑定——要么在 docstring 声明，要么给 methods 也加交叉核对。
- **F'-4 VG fatal 的运维代价**：见 §3.5。本批 correction 一体改期间 sm25 预计常红；建议在批内 README/跑测口径里预先写明「这道门的红 = 树动了，需重签或解释」，避免届时被当回归。
- **F'-5 sm24 的签字 request 已不可寻**：门正确 fail-closed，但现存两份带审计件的 case 只剩一份可复现。request 的权威来自**内容重算**（位置不承权），把真件归档到耐久位置是安全的找回路径；或者明确记「sm24 复现门不可用」。建议进 plan.md。

---

## orchestrator 题面写错 / 需更正的地方

按 §七 逐条证伪的结果，**六处自认里五处核实无误**（§七#1 自述列未核——本轮我全部核了，无出入；#2 F-4「没提」确为事实且派工单本来就不含；#3 自证框架——实测内容侧不成立，已按题面要求直说；#5 返工面假设正确；#6 六个数字——3046/13、29/136、basis 90:46、厚度 78:58、五次 neuter 1/10 全部复核相符）。真正的更正项：

1. **§3.4#1 把 request 不可得写成将来时的假设**（「目录**被清理则**会响亮降级」）——实测它**已经发生**：sm24_anchor 今天就是 `inputs_unavailable`。这不是前瞻风险，是现状；下一份复现门读数盘点时应按「可用面 1/2」记账。
2. **小误**：复核请求 §〇 说 worktree 里有「**3 份** untracked 的 md」并列了 3 个文件名——实际有 **4 份**（第 4 份正是本轮请求单自身 `2026-08-27_g1_rework_crossreview_glm.md`，同为 untracked）。我按「不删任何 untracked md」处理，无实害。
3. **上一轮裁决的两格占位符本轮已补真值**（A1 全量行、A6 neuter 三条独立读数），即 §二.1 欠账清偿；另按触发器 #5 自查上一轮裁决：未发现判错需推翻的条目（F-1..F-4 四条现状全部与当时的判词一致）。

## 本席位自己跑的全量 summary 行（逐字）

```
3046 passed, 13 xfailed, 211 warnings in 405.32s (0:06:45)
```

（`python -m pytest -q -n 6`，`/tmp/ep_g1`，HEAD `ef41a39`，exit 0；跑测期间未与 `/tmp/ep_f97` 席位互踩，无同机竞争假红。）

## 交件时工作树状态

- HEAD = `ef41a39 08.27_GtRawLayerZeroExemptionRework`（未动）。
- **tracked 文件零改动**（`git diff` 为空）：本轮全部 neuter 已逐次 `git checkout --` 还原；探针文件 `tests/test_zz_glm_probe.py` 已删除。
- untracked 共 4 份 md，均为 orchestrator 留件（3 份请求/裁决 + 本轮请求单自身），未删未改。
- 本裁决文件即为本轮在 worktree 内的唯一写入。
