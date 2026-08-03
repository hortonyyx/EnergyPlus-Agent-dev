# R1 批 B/C · orchestrator 对 GLM 边界上报的裁定

- **日期**：2026-08-03
- **上游**：[GLM 边界上报](../execution/2026-08-03_reading_ruler_r1_batchBC_glm_boundary_report.md) · [批 B/C 派工单](2026-08-03_reading_ruler_r1_batchBC_dispatch.md)
- **性质**：裁定。与派工单冲突处**以本文为准**；派工单其余部分（尤其 §4 明令禁止清单、§5 交付要求）**全部不变**。

---

## 0. 先记一句：这次停下上报是正确的

派工单 §2.3 要求「发现波及信任链即停下上报，不得自行决定」，施工席**照做了，且核实链完整、工作树零改动**。
这是本项目要的正面样板行为（**不扣分，记正分**）。

---

## 1. 阻断已由 orchestrator 独立核实 —— **属实**

施工席的事实链逐条复核通过：

- `RequiredViewEntry.dimensioned` 是 manifest 字段（`src/agent/execution/view_manifest.py:355`）；
- `content_sha256` = 对**整个 payload 减去自身**求哈希（`view_manifest.py:511-514`）
  ⇒ **`dimensioned` 由 false→true，`content_sha256` 必变，与声明写在哪无关**；
- 已签字 GT 侧车 `gt/sm24_anchor/score_inputs/view_bindings.json` 冻结了
  `base_view_manifest_sha256 = 459513f1…` 与 `case_metadata_sha256 = f2efff86…`；
- `load_score_view_bindings` 对四元组做**逐字相等**校验，不等即抛
  `score_view_binding_invalid`（`src/agent/judge/score_inputs.py:86-91`）。

**⇒ 写入 sm24 真值 = 打穿已签字 GT 的评分信任链。施工席的判断成立。**

---

## 2. 拍板 1（sm24 真值 backfill）：**采纳甲**

**本批不写 sm24 真值。** 只交付 S-3 的**机制 + fixture 锁**（L-20/L-21/L-22/L-23 全部用自造 fixture，
**不碰真 sm24 metadata、不碰 GT**）+ S-2 + 批 C。

**理由**（三条，按权重）：

1. 乙需要**一次新的 GT 签字事件**（重新生成 + 真人 `hortonyyx` 重签评分侧车）。
   **GT 重签是独立的治理事件，不得混进修尺子批**——本项目已有教训：把两件性质不同的事塞进一批，
   边界就会被实现方猜。
2. 甲完全落在派工单 §2.3 两条限制内（只为将来的 run 造 manifest / 不改历史 / 不碰签字 GT）。
3. 施工席指出的那条**预期压力是对的**：L-13/L-20 的 fail-closed 会**迫使** R2 在跑 sm24 之前
   先把真值声明写出来。这正是我们要的形态——**让缺失变成硬失败，而不是静默默认**。

**⚠️ 随之产生一条登记债（必须写进执行日志，orchestrator 已同步登记进 plan.md）**：

> **债 D-1**：sm24 五图 `dimensioned=true` 的真值写入 + GT 评分侧车重新生成与真人重签
> ⇒ **归 R2（重建基线）**，且**需用户单独授权 + 真人签字**。
> 在 D-1 完成之前，**sm24 对现签字 GT 的评分保持现状（五图 `dimensioned=false`）**；
> 这不影响本批，因为派工单已禁止 A/B/C 全绿之前发布任何新分数。

**⛔ 附带边界（本批必须遵守）**：不得为了让锁变绿而修改
`case_tests/test_baseline/gt/**` 或 `case_tests/e2e_tests/sm24_anchor/case_data/testdata_prompt.json`
的**任何字节**。若某条锁在不碰这两处的前提下写不出来，**停下上报**，不要降级。

### 2.1 对 L-21 的追加要求（防止锁空转）

L-21 改用 fixture 之后，**fixture 必须在形状上与真 sm24 同构**，否则这条锁证明不了接线：

- 五个 required view（含 plan 与 elevation 两类）；
- 声明 `dimensioned=true` 之后，`dimensions_present` 与 `dimension_p1a_fields` **各 5 行由 N/A 转为真实判定**；
- **其他 check-id 的结果逐项不变**；
- **四条 closure 仍然 block**（即：打开尺寸类检查**不会**顺手把已有的阻断洗掉）。

**断言必须落在具体 check-id 的行上，不得落在「返回值存在」或「总数变了」上。**（派工单 §4 #3 的教训。）

---

## 3. 拍板 2（S-3 声明位置与 wire 形态）：**照走**，加两条约束

采纳施工席 §3 的建议实现：

- **输入侧**：`testdata_prompt.json` 增结构化 `dimensioned_views`（每项
  `{view, dimensioned, source:{image_sha256, reviewer, date, basis}}`）；旧「stem 字符串列表」作兼容读法。
- **manifest wire 侧**：`RequiredViewEntry.dimensioned` 由 bool 升为
  `state(declared_true|declared_false|unknown) + authority/source_hash`。
- **fail-closed gate**：由已知 `run_profile` 的 provisioning wrapper 在 strict 档校验；
  `build_view_manifest` 保持 case 级、不感知档位。

**追加约束两条**：

1. **`unknown` 与 `declared_false` 的差异必须在 wire 上一路保留到 `checks.json`**，
   不得在任何一层折回 bool。这是 S-3 的核心（「该考的题没考」正是折叠造成的），
   **要有一条锁专门断言这个差异不被折叠**（可并入 L-23）。
2. **legacy 已存 manifest 只读不 fail**（仿 exam-scope）——但**只读路径必须能把
   「这是 legacy 默认值」这件事表达出来**，不得让它看起来像一次正常的 `declared_false` 声明。

---

## 4. 拍板 3（§4 五条较轻决定）：**照走**，其中 G4 附一条披露义务

| 编号 | 裁定 |
|---|---|
| **G4** policy hash 覆盖面 | **采纳收窄**（hash 只含 `capability_profile + run_profile`）。⚠️ **但这偏离 sol 的 S-2 原文**（原文含「validation/review relevant switches」）⇒ **必须在执行日志里显式写明「此处偏离 sol S-2，理由是……」**，好让 GPT 施工审能针对性挑战。另：其余 toggle **可以记录进 `_run/run_policy.json` 作非哈希上下文**，只是不参与 drift 判定。 |
| **G6** legacy 检测 | **照走**。有 `_run/run_policy.json` ⇒ 用之并重验 hash；无 ⇒ 标 `legacy_defaulted=exploratory`、只读不 fail；strict fail-closed 只在**新 run provisioning** 触发。⚠️ 底线不变：**legacy 默认档不得冒充 regression**。 |
| **G7** 渲染落点 | **照走**。隔离路径落 `attempts/NNN/renders/<expected_output_id>.png` + 记 source output hash / render helper version / 每图状态；flat 保留便利副本；渲染失败标 unavailable/blocked，**不吞错装 complete**。 |
| **G8** 像素预算 | **照走**（单边 ≤ 8192px、总像素 ≤ 50M；超限**拒绝并留 failure artifact，不 clamp 放行**）。追加：**两个上限必须是具名常量**，且 L-51 直接断言该常量生效（改常量即锁的行为跟着变），不得把数字散落在调用点。 |
| **G9** OCR 越界信号 | **照走：FLAG（advisory），不升 block。** 与派工单 §4 #1 同型（未做假阳性调查前不升硬门）。**安全由 G8 的资源门兜底，语义留 P1** —— 这正是 sol「安全 P0 + 语义 P1」的分层，不是放水。 |

---

## 5. 复工指令

按「甲 + §3（含两条追加约束）+ §4（G4 附披露义务、G8 附具名常量）」**立即开工**。

顺序与交付要求**完全按派工单不变**：
批 B（S-2 → S-3 机制 + fixture 锁，**不含 sm24 真值写入**）→ 执行日志 → 本地提交
→ 批 C（O-1 / O-3 / O-4）→ 执行日志 → 本地提交。**不 push。**

全仓 `pytest -q -n 6`；每条锁做 neuter 自查（摘掉即红、零连带）并**如实登记**；
交付前跑一次全仓（基线 **2055 passed + 10 xfailed，零红**）。

**再遇欠规格边界，同样停下上报——这次的处理方式是对的。**
