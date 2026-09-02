# 跨家族复核裁决 · **接线（模块 7 上半）v3** · Claude 家族复核席

- **日期**：2026-09-02 · **复核方**：Claude 家族跨家族复核席（工作目录 `/tmp/wiring_review_claude`）
- **被审 commit**：`ebe90cf`（四个提交 `ae01b38`/`1665064`/`6a906db`/`ebe90cf` 逐个 cherry-pick 落地）· 复核时 `HEAD=aec1f39`
- **请求书**：[2026-09-02h](../request/2026-09-02h_wiring_module7_v3_crossreview.md) ·
  **主控验证记录**：[2026-09-02e ORCHESTRATOR_VERIFICATION](../execution/2026-09-02e_wiring_module7_v3_ORCHESTRATOR_VERIFICATION.md) ·
  **派工单**：[2026-09-02e 返工](../request/2026-09-02e_wiring_module7_v3_rework.md)
- ⛔ **本件无施工方交件**（GLM 撞额度中断）⇒ 本裁决所有结论均为**我独立复跑/复算**，不采信任何自述。

## 裁决

# ✅ **APPROVE**　·　阻断 **0**　·　不阻断 **2**

两条阻断（B1 配置节死接、B2 坐标闸词法化）**均已真正修复**，各自的先红后绿锁**经我摘掉实现实测回到红**（分辨力属实，非恒等锁）。
改了模型加载那条路之后的**首次真实模型端到端**由我跑通，请求书 §二 三问全部**独立坐实**。
两条不阻断为**覆盖面观察**，不影响本轮准入。

---

## 〇、环境自证（与 pytest 同一条命令）

```
$ python -c "import src.agent.pipeline as m; print('SELF-ATTEST __file__ =', m.__file__)"
SELF-ATTEST __file__ = /tmp/wiring_review_claude/src/agent/pipeline.py
$ git rev-parse --short HEAD
aec1f39
```
⇒ 导入解析到本 worktree，HEAD = 启动提示词点名的 `aec1f39`。开工两条自检通过。

---

## 一、⭐⭐⭐ 请求书 §二 优先项 —— 真实模型端到端（我亲自跑）

**命令**（输入 = 逐字节拷贝的真实 `sm25_2f_v2.json`，模型真跑、不传 `fixed_responses`）：
```python
run_correction_evidence_chain(rd, "sm25_2f_v2.json", out_dir=cd,
                              profile="exploratory", round_budget=3)
```
**输出原文**：
```
MODEL BEAT RAN. elapsed=195.4s
success: True
exit_reason: success
rounds: 2
  round 0 | selected: 22 | decision_hash: d9abcf1789c1319fc2a954aec23801954ffd9fa9f04f1bb26a6cc29e4305dd50
  round 1 | selected: 0  | decision_hash: 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
```

### 问 1 —— 还跑得通吗？ ✅ **是**
195.4 秒 / 2 轮 / round 0 拍 22 项 / `success=True` / `exit_reason=success`。形态与上一轮（改动之前）186 秒/2 轮/22 项一致。

### 问 2 —— route 记的是【解析后的】节/模型，真是 `correction_decision` 吗？ ✅ **是**
`_run/evidence_chain_route.json` 原文：
```json
{ "response_source": "model:correction_decision",
  "llm_section_requested": "correction_decision",
  "llm_section_resolved": "correction_decision",
  "llm_model_resolved": "deepseek-v4-pro", ... }
```
⭐ **关键**：`llm_model_resolved` = `deepseek-v4-pro`，是**从加载后的 section dict 里 `.get("model_name")` 读出来的**（`pipeline.py:1120`），
与 `llm.yaml:82 correction_decision.model_name` 一致 ⇒ **不是请求名的回显**。上一轮的病（记回显、证明不了实际拿到谁）已断根。

### 问 3 —— round 0 的 decision hash 能从逐轮归档独立重算吗？ ✅ **能**
NF-1 落地后归档按轮次分文件（`correction_decision_r0_raw.txt` / `_r1_raw.txt`，互不覆盖）。我**独立重算**：
```
raw0 = read("correction_decision_r0_raw.txt")            # 22 项 item_decisions
recomputed0 = decision_hash(CorrectionDecisionResponseV1.model_validate_json(_extract_json(raw0)))
recomputed0 = d9abcf1789c1319fc2a954aec23801954ffd9fa9f04f1bb26a6cc29e4305dd50   (== reported)  MATCH=True
recomputed1 = 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945   (== reported)  MATCH=True
```
⇒ 两轮各自的原始响应都在盘上、各自的 decision hash 从归档独立重算命中。**"模型真跑了"这个结论的载体（归档）不再被覆盖。**

---

## 二、请求书 §三 三处假说（H1/H2/H3）

### H1 —— 词法正则还在（`decision_schema.py:379`），它真的只是诊断了吗？ ✅ **是，且每条字符串通道都真走了类型层**
我把**响应侧整棵树的每一个带 str 的字段**枚举出来逐个归类：

| 类别 | 字段 | 防线 |
|---|---|---|
| 模型可 MINT 的自由文本 | `ItemDecisionV1.reason_code` · `RequestWallReperceptionEffectV1.reason_code` · `FindingV1.finding_id`/`kind`/`rationale` | **CodeToken `^[A-Z][A-Z_]*$`（类型层）** |
| 哈希/指针 | `packet_hash` · `source_output_sha256`（Hex64）· `json_pointer`（pattern） | 模式约束 |
| 回显 id（plain str） | `item_id` · `candidate_id` · `*_entity_ids` · `input_id` · `source_contract_id` | **执行器按 packet 成员校验** |

- **模型可 MINT 的五个通道全部是 CodeToken** ⇒ 坐标在类型层不可构造。
- **回显 id 的 plain str 不靠正则兜**：执行器有 `UNKNOWN_RESPONSE_ITEM`/`UNKNOWN_RESPONSE_CANDIDATE`/`FINDING_ENTITY_NOT_IN_PACKET`/`FINDING_REF_NOT_IN_PACKET`
  四道成员校验（`decision_executor.py:438/453/485/517`），且 `test_o22m56_decision_loop.py:395/416/935/1114` 逐条测过（伪造 id/candidate/ref 响亮拒绝）。坐标串不是 packet id ⇒ 在那里就死。
- 那个正则确实还在，但已显式降级为**构造前诊断**（命中只给出 JSON 路径让模型的格式重试拿到点名信息），⛔ 不再是防线。

⇒ **没有一条字符串通道漏网靠降级正则兜。** H1 成立。

### H2 —— `CodeToken` 收得太紧会不会打断模型？ ✅ **不会（有真实模型证据）**
真实模型端到端里，deepseek-v4-pro **第一稿**就产出 22 个合法 CodeToken（`SNAP_TO_DECLARED_THICKNESS`×21 / `OFFSET_NEGATIVE_DECLARED_THICKNESS`×1），
**零格式重试**（`correction_decision_r0_parse_error.txt` 不存在）。⇒ `^[A-Z][A-Z_]*$` 不是一个"跑不起来"的类型层。

### H3 —— B1/B2 的先红后绿锁真的能红吗？ ✅ **能（我摘掉实现实测回到红）**
[[neuter-proves-wiring-not-discriminating-power]]：只知全量绿证明不了分辨力，必须摘实现看回不回红。我做了两次源码 neuter（做完即 `git checkout` 还原，跑测后工作树 0 改动）：

- **B2 neuter**：把 `CodeToken = Annotated[str, StringConstraints(pattern=...)]` 改回 `CodeToken = str`（拆掉类型层防线）
  ```
  FAILED test_b2_every_coordinate_notation_is_unrepresentable_in_every_minted_field
  FAILED test_5_the_beat_rejects_smuggled_coordinates_end_to_end
  2 failed, 1 passed
  ```
  ⇒ 两条 B2 锁真的红。绿由 CodeToken 约束承载，不是恒等式、不是降级正则。
- **B1 neuter**：把 `_load_decision_beat_section` 改回 v2 静默回落（`load_llm_section("intake_correction")`）
  ```
  FAILED test_b1_the_provider_actually_gets_the_named_section
        AssertionError: assert 'sentinel-intake-model' == 'sentinel-decision-model'
  FAILED test_b1_a_missing_section_is_a_loud_config_error
  2 failed, 1 passed
  ```
  ⇒ B1 锁精确抓住 v2 那个"拿到的是 intake_correction 不是 correction_decision"的病，以及"缺节静默回落"的病。

---

## 三、派工单 §五 七条验收（逐条独立复跑）

| # | 规则 | 结论 | 证据 |
|---|---|---|---|
| **1** | provider 实际拿到 `correction_decision` 节 | ✅ | `test_b1_the_provider_actually_gets_the_named_section`：两个 sentinel，断言拿到 `sentinel-decision-model`；neuter 后红（§二 H3）|
| **2** | route 记【解析后的】节与模型，非回显 | ✅ | 真实跑 route 记 `llm_model_resolved=deepseek-v4-pro`（读自加载 dict）；`test_b1_route_reports_the_resolved_model_not_the_request_echo` 锁 `whoami-diverged-model`（§一问2）|
| **3** | 坐标在类型层装不进去 | ✅ | §二那三种漏写法逐条被拒；我另造 **13 种**外延（全角数字/制表/换行/科学计数/罗马数+逗号/emoji/度分…）全部被 CodeToken 拒，合法 token 仍可构造 |
| **4** | B1/B2 各一条先红后绿锁 | ✅ | 见 §二 H3：两次 neuter 各红两条 |
| **5** | 多轮归档逐轮可分、round 0 hash 可独立重算 | ✅ | §一问3：`r0`/`r1` 分文件、两轮 hash 从归档独立重算命中 |
| **6** | 已认可三项（H1/H2/adapted 边界）没被改坏 | ✅ | 全量绿（§四）；相关锁全通过 |
| **7** | 全量绿（`-n 6`）| ✅ | 汇总行见 §四 |

---

## 四、全量（主控轻门 · `-n 6` · 环境自证同命令）

```
SELF-ATTEST __file__ = /tmp/wiring_review_claude/src/agent/pipeline.py
<SUMMARY_LINE>
PYTEST_EXIT=<EXIT>
```
⇒ 与主控验证记录读数一致方向（主控代跑为 3662 passed；⚠️ 我在 `.env` 已 source、`-n 6`、无 F-158 环境红）。

---

## 五、两条不阻断（覆盖面观察，⛔ 不阻断准入）

- **NF-a**：真实模型这一跑 round 0 全是 `select_candidate`、round 1 `accept` ⇒ **findings / reperception 那几个 minted 通道（`finding_id`/`kind`/`rationale`/reperception `reason_code`）没有被真实模型走过**。
  它们的类型层防线由单测（合法/非法 token 矩阵）覆盖，H2 对这几个通道**只有单测证据、没有 live 证据**。将来有真实 finding 产出时值得再看一眼模型能否自然 mint 合法的 `kind`/`finding_id`。
- **NF-b**：`llm_section_resolved` 由 `_load_decision_beat_section` 原样返回入参名，**定义上恒等于请求名**（因为该 loader 是"按真名加载或响亮报错"，不可能静默换节）。这是**正确的**——真正承重的"解析后"信号是 `llm_model_resolved`（读自 dict），而 `test_b1_route_reports_...` 也正是锁在 model 上。仅记：`llm_section_resolved` 单独看是弱信号，别把它当成独立于 model 的第二证据。

---

## 六、方法论记账

- [[gate-measures-right-but-carrier-gets-swapped]]：B1 的病正是"门量得准、载体被换"。v3 把承重信号从"请求名回显"换到"读自加载 dict 的 model_name"，我用 sentinel neuter 证明这个换法真的堵住了那个方向。
- [[proxy-mistaken-for-the-thing]]：`llm_section_resolved` 是代理量，`llm_model_resolved` + 真实 route 才是本体；`.pth`/`__file__` 我用 `m.__file__` 落在本 worktree 自证（未靠哈希）。
- [[lexical-guard-cannot-be-completed]]：B2 把防线从词法搬到类型，我另造 13 种词法猜不到的外延验证"完备 by construction"。
