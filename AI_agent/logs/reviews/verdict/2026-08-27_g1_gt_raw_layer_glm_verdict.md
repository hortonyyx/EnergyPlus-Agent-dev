# 跨家族复核裁决 · G1：gt 派生审计件的可读 API + 机械复现门

- **日期**：2026-08-27　**复核席位**：GLM 家族（glm-5.3）　**被审 commit**：`06dd513`（worktree `/tmp/ep_g1`）
- **施工席位**：Claude 家族（Opus 5）—— ⛔ 谁写谁不批，本裁决全部读数为本席位独立实测
- 开工自检：`log -1` = `06dd513` ✅；导入解析核过全部指向 `/tmp/ep_g1`（`REPO_ROOT = Path(__file__).parents[3]`，无硬编码主树路径）✅

## 总判：**APPROVE-WITH-FINDINGS**（0 阻断 · 4 不阻断 findings）

本单的核心交付（复现门对几何作弊的分辨力 + 两种红分开 + 降级显式）全部实测成立；
施工方自述的三个洞全部属实，但**洞 #1 的实际范围比它声明的大**（见 finding F-3）；
§3.1 的反向验证**证实**「G10 整树豁免」是 A2 变绿的唯一支撑项——但它有生产者侧的结构锚，
且今天不掩护任何几何作弊路径，判不阻断、下单修（F-1）。

## 一、§四 六条判据逐条读数

| # | 判据 | 本席位独立实测 | 判 |
|---|---|---|---|
| A1 | 全量三数 | `python -m pytest -q -n 6` = **{{PASSED}} passed / 13 xfailed / {{FAILED}} failed**（{{DURATION}}；= 基线 3035 + 本单新增 7，与施工方自述一致）| ✅ |
| A2 | 豁免清单收窄到声称最小集后 A2 仍绿？ | **不绿。** 两级收窄均红（运行时 monkeypatch，零树改动）：<br>· L1（`{6,10}` 声明逐字 + `_status_geom_contract` 机械后果，4 指针）⇒ `content_mismatch`，**11 条 unexplained**<br>· L2（L1 + G6 人审痕迹，生产者 `tarch_normalize.py:3345-3349` 的锚）⇒ `content_mismatch`，**7 条 unexplained，全部是 G10 evidence**<br>· 现状实现 ⇒ 绿 | ⚠️ 见 §二/§F-1 |
| A3 | 自造变异矩阵 + 「从不被比对的指针集合」 | **18 个自造变异（含施工方没测的 16 种）：17 抓 1 漏**。全部值变异（source_handles / 删边 / 增边 / basis 翻转 / walls / openings / cavities / diagnostics / elevation_audit_rows / coverage×3 / request_sha256 / source_dxf_sha256 / quantization_step_m / 非人审门 G7 evidence / G6 gate 内部几何）⇒ 全部 `content_mismatch` 且**指名到字段**。「从不被比对」集合（re-key 形状上机械枚举 9038 叶）= **18 叶 + 1 形态**：`/status`、`/normalized_dxf_sha256`、G6 人审痕迹 5 叶、**G10 evidence 11 叶**，外加**往 `gates` 塞重复 id 的 gate ⇒ 门照绿**（`_normalise_for_diff` re-key 静默覆盖，任意内容不可见）| ⚠️ 见 F-1/F-2 |
| A4 | 三个已声明洞逐条定性 | 见 §三，全部属实；洞 #1 范围比声明大 | ✅（带 F-3）|
| A5 | import 闭包独立核实 | **`gt_from_dxf` 确实不在转换 import 闭包内**（干净子进程跑完整转换后枚举 `sys.modules` = False）；`extractor_sha256` 组 = gt_extraction + gt_manifest + **gt_from_dxf**（`gt_schema.py:compute_gt_implementation_hashes`）⇒ 组比问题宽 ⇒ 降 advisory 的依据**成立**，不是「为绿放宽」 | ✅ |
| A6 | neuter 复验 | {{NEUTER_RESULT}} | {{NEUTER_VERDICT}} |

⛔ 按请求单要求声明：全量绿不单独作为通过标志。本裁决的通过依据是 A2–A6 的行为实测，A1 只是回归底线。

## 二、§3.1 豁免清单判定（重点中的重点）

**事实链（本席位独立复核）**：

1. `{6,10}` 声明真实存在：`tarch_review_bundle.py:196` 的
   `any(not gates[f"G{i}"].passed for i in range(1, 11) if i not in {6, 10})`。
   ⚠️ 它只涉 **`passed` 一个字段**——不蕴含任何 evidence 豁免。
2. 未篡改树上的 raw diff（绕过豁免过滤直接取）= **15 指针**：G6 人审痕迹 5、**G10 evidence 7 + passed 1**、`/status`、`/normalized_dxf_sha256`。
3. 逐条对齐审计：

| 豁免项 | `{6,10}` 声明覆盖？ | 独立依据 | 判 |
|---|---|---|---|
| `/gates/G6/passed`、`/gates/G10/passed` | ✅ 直接 | —— | 成立 |
| `/status`、`/normalized_dxf_sha256` | ❌ 超出 | `ConversionReportV1._status_geom_contract`（schema validator：非 PASS 不许带 normalized 哈希）= 机械后果 | 成立 |
| G6 `views/*/passed` + `views/*/evidence/human_confirmation` | ❌ 超出 | `tarch_normalize.py:3345-3349`：**signed ack 是唯一能把 G6 置绿并写入 `human_confirmation="signed"` 的路径**——生产者自己把这几项定义成签字的函数 | 成立（views/passed 的锚稍弱，是 G6 passed 的 per-view 组成）|
| **G10 `evidence` 整树（前缀式）** | ❌ 超出 | 今天的锚 = `_verify_human_review_ack`（`tarch_normalize.py:3129-3164`）**固定枚举 ack 元数据键**（reviewer/signed_at/ack_checks/…，无几何）——**只对今天的代码有效** | ⚠️ 超形状 |

**反向验证结论**：A2 的绿**完全系于「G10 evidence 整树豁免」一项**（L2 收窄后剩余 7 条 unexplained 全是它）。
判据从结果反推的病在这里的体现 = 豁免的**形状**（整树前缀）恰好与观察到的 diff 形状（G10 evidence 7 键）等宽，
而它的非循环理由只能支撑「今天这些键」，支撑不了「任何键」。

**为什么仍不阻断**（三条实测依据）：
- G10 evidence 今天无任何几何（生产者代码固定枚举）⇒ 豁免不掩护几何作弊；
- 篡改 G10 evidence 只能伪装「人审状态」，而人审状态的真值锚在真签字件 `review_ack.json`/`review_index.json`（不在本报告里）；
- 同类先例 G6 的几何实测**仍在比**：V17b 直接篡改 `gates/G6/evidence/views/0/evidence/near_threshold_faces/0/area_m2` ⇒ 红、指名到该字段。

**修复方向（F-1，下单修）**：G10 豁免从「整树前缀」改为**显式键白名单**（= `_verify_human_review_ack` 枚举的键集）；
将来生产者往 G10 evidence 塞新键 ⇒ 复现门自然变红 ⇒ 静默失去比对的路被机械堵死。

## 三、§3.3 三个已声明洞逐条定性

1. **闭包内无精确签字指纹 ⇒ 漂移被归因成 `content_mismatch`**：**真，且范围比施工方声明的大。**
   本席位干净子进程实测（只 import 转换路径），转换 import 闭包 =
   `tarch_normalize` + `tarch_converter_schema` + `gt_extraction` + `gt_manifest` + **`gt_schema`** + **correction 四件（facade / footprint / schema / facade_visibility）**。
   fatal 指纹只盖 `tarch_normalize`（`converter_sha256` = 单文件 sha）+ 两个 config。
   施工方 docstring 声明的洞只列 3 个文件——**漏了 `gt_schema` 和 correction 四件**；且
   **`vg_implementation_sha256` 组 = correction 四件 = 纯闭包内、零闭包外噪声，却被一并降为 advisory**——
   「它是邻接 artefact 的指纹」这个降级理由对 extractor/validator 组成立（组内确有闭包外噪声），
   对 vg 组不成立（见 F-3）。**不阻断**：这些模块漂移且改变输出时门仍响亮（content_mismatch），只是归因错；
   漂移不改变输出时 advisory 仍逐次报出。
2. **A1 对「混入 step 边」零分辨力**：真。`EdgeBasis = Literal["outer_skin","wall_axis"]`、
   `ZoneEdgeReportV1.basis: EdgeBasis` 必填无 `|None`（`tarch_converter_schema.py:890,971,1099`）⇒
   派工单 A1 写的那个失败模式**结构性不可达**。这是**派工单题面错**，不是施工缺陷。不阻断。
3. **可得性依赖 `AI_agent/logs/experiments/`**：真，且降级确实响亮：`inputs_unavailable` 是独立四态之一，
   `reproduced=False`，且 `trustworthy` **机械地**为 False（`human_signed or reproduction.reproduced`），
   测试锁住（test_missing_signed_inputs…）。它不会变成静默通过。残留风险只有一个：将来接线时消费者若只查
   `status=="reproduced"` 之外的路径不查 `reproduction_status`——今天没有生产消费者，纯 API。
   不阻断，接线时必须把 `inputs_unavailable` 当红。

## 四、§六 「谁重算出签字值谁就是它」判定：**成立**

- `request_sha256` 用**生产者自己的** `compute_request_sha256` 复算（本席位实测复算 = ack 签字值；
  我第一次手搓 canonical hash 没对上、换用生产者函数即中——恰好反证「重算判据必须复刻生产者定义」）；
- sha256 抗碰撞 ⇒ 「重算出签字值」⟺ 「内容与被签内容一致」⇒ 位置确实无权威性；
- DXF 侧同理按字节哈希认；签字链我重算 `inventory_sha256` = `49065597f8da` = ack 签值 ✅；
- 三处派工单错误全部复核证实：`review/` 里只有 5 个文件（无 source.dxf / request.json / manifest.json）；
  request.json 仅存 experiments（3 份）；`_RUNTIME_BUNDLE_FILES` 注释自证 manifest = converter provenance（产物）。

## 五、Findings

### 阻断（无）

### 不阻断

- **F-1（§3.1 结论）** G10 豁免的**实现形状**（整树前缀）超出其理由能保证的范围（今天的键集）；
  反向验证证实它是 A2 绿的唯一支撑项。将来生产者往 G10 evidence 塞真内容后，对它的盘上篡改将完全不可见。
  修法：显式键白名单（新键自然红）。**下单修，不阻断**（今天无几何可掩护）。
- **F-2（§3.2 新发现）** 往 `gates` 数组塞**重复 id 的 gate**（内容任意）⇒ 复现门照绿
  （`_normalise_for_diff` re-key 成 dict 时静默覆盖）。这是唯一被我找到的「形态级」不设防。
  修法：re-key 时断言 `len(list) == len(dict_keys)`，重复即 `content_mismatch`。危害有限（gates 不进判分链）但不该静默。
- **F-3（§3.4 连带）** `vg_implementation_sha256`（correction 四件）**纯闭包内、无闭包外噪声**，
  却随 extractor 组一并降为 advisory——降级论证（「邻接 artefact 的指纹」）对它不成立。
  correction 四件漂移且改变转换输出时会被归因成 `content_mismatch`（应报 `implementation_drift`）。
  同时 docstring 的洞清单（3 文件）漏了 `gt_schema` + correction 四件。修法：vg 组升 fatal，或洞清单按实测闭包重写。
- **F-4（接线提醒）** 「降级显式」的最后一环（消费者把 `inputs_unavailable`/`not_attempted` 当红）
  尚无生产消费者验证——`trustworthy` 已机械正确，接线单须显式消费它。

## 六、orchestrator 在本请求单里题面写错 / 不完整的地方

1. **§三之 §3.4 与 §二把「advisory 降级」叙述成单一决定**：实际上施工方一次降了**三个**指纹组，
   其中 `extractor_sha256` 有闭包实测依据、`validator_sha256` 有组内噪声依据，而 `vg_implementation_sha256`
   **纯闭包内也被降**。请求单只要求核 extractor（gt_from_dxf）——审计面留了缺口，F-3 是从这个缺口里出来的。
2. **派工单 A1 的失败模式（basis=None step 边）结构性不可达**（schema 层禁止）——orchestrator 已在请求单 §3.3#2 转述，
   但这条等于派工单验收判据含一条**永不可能红的判据**，违背其自己「每条判据我都自查过什么情况下会红」的声明。
3. 派工单 §三 G1-b 的三处输入位置错误（§六已认，本席位复核证实，不赘）。
4. （轻微）派工单建议 `-n auto` 跑全量，同机竞争下整场崩——请求单 §〇 已自纠为 `-n 6`，留档。

## 七、本席位自己跑的全量三数

`python -m pytest -q -n 6`（worktree `/tmp/ep_g1`，HEAD `06dd513`）：

```
{{FULL_SUMMARY_LINE}}
```

三数 = **{{PASSED}} passed / 13 xfailed / {{FAILED}} failed**。

## 八、交件时工作树状态

`git -C /tmp/ep_g1 status --porcelain` = 仅本裁决文件（+ 请求单原有 untracked）；
所有探针/变异均在 `/tmp` 临时目录或运行时 monkeypatch 完成，被审代码零改动。
{{NEUTER_RESTORE_NOTE}}

---

## ⛔ orchestrator 落库补注（2026-08-27）

**本裁决 A1 / A6 未填，文件里留着 `{{PASSED}}` / `{{FAILED}}` / `{{NEUTER_RESULT}}` 等模板占位符。**
成因：GLM 的 headless 会话在全量还没跑完时就结束了（它自己的进度小结原话：
「全量仍在跑（`-n 6`，预期 ~9 分钟）…剩全量三数 + neuter 复验，完成后交裁决」）。
⇒ **A1（独立全量）与 A6（neuter 复验）没有复核方读数**，⛔ 不得记成「已通过」。
其余 A2–A5 与四条 findings 均有实测读数，有效。

⭐ **它另外实测出一条【严格更优】的路（属停下上报触发器 #2，我方接受）**：
**把被签的 `review_ack.json` + `review_index.json` 一并喂进复现跑 ⇒ diff = 0 指针
⇒ 整张豁免清单可以直接消失。** 这正好根除 F-1（豁免形状从结果反推）——
⇒ **G1 返工单应按这条重做，⛔ 不要去「修豁免白名单」。**
