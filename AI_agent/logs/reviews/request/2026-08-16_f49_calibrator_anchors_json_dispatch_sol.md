# 派工单 — F-49：`px_m_calibrator` 在隔离沙箱里两种文档形态全坏

- **日期**：2026-08-16
- **施工**：sol（gpt-5.6-sol，effort=high）
- **审**：orchestrator 轻门（独立复跑 + 逐行 diff）；⚠️ sol 是最高档，跨家族执行审此轮不另派，如实登记
- **用户拍板**：派 sol（2026-08-16 当面）

---

## ⛔ sol 执行护栏三条（规约 §5，本单明确授权范围）

1. **单独授权**：只允许改本单 §4 列出的文件。**删除 / 覆盖 / 推送均未授权**，需要时停下上报。
2. **每阶段给可验证证据**：每条改动都要给「改前红 / 改后绿」的实跑输出，不接受「我认为它现在可以了」。
3. **限变更范围**：**一个 Slice 做完即停**。⛔ 不许顺手重构 `guard.py` 的判据、不许动 `PATH_KEYS` 之外的安全面、不许改 F-35（CV 证据不进 attempt）——那是另一笔债。

---

## 1. 现象（orchestrator 实跑得到，非推断）

隔离读图跑 `run_2026-08-16_B1_pilotgate_G1` 中，读图器 3 次尝试调用 `px_m_calibrator` 全部失败，
随后退回肉眼估像素。复跑三种参数形态，结果：

| `anchors_json` 形态 | 谁这么写 | 结果 |
|---|---|---|
| 内联 JSON 字符串 | `skills/intake_pipeline/0_reading/cv_toolbox.md` 示例 **+ `run_cv_probe.py` 自带 `_USAGE_TEXT`** | ⛔ `argument --anchors-json: invalid _json_arg value: '/workspaces/ep_reading_staging_B1G1/[{"axis":"x",...]'` |
| JSON 数组（request 文件的 `args.anchors_json`） | `run_cv_probe.py` 自带 usage 的 request 示例 | ⛔ `ValueError: anchors_json must be a path string` |
| 指向文件的路径 | **没有任何文档写** | ✅ 唯一能用；产出 `out/<dir>/cv_evidence/<stem>/001_px_m_calibrator.json` + overlay |

## 2. 病因（已定位，仍请你独立确认——见 §6）

`src/agent/execution/isolation_templates/run_cv_probe.py`

- L31 `PATH_KEYS = {"image", "out_dir", "anchors_json", "candidates_json"}`
- `_request_to_argv` 分支顺序：`OUTPUT_ROLE_KEYS` → **`PATH_KEYS`（要求 str，做 `_resolve(value, root)`）** → `isinstance(value,(dict,list))` → `None`

⇒ `anchors_json` 是**字符串**时被当路径、拼上 staging 根；是**数组**时先撞 `PATH_KEYS` 分支的
`must be a path string` 而永远走不到 `json.dumps` 那条。

上游 `scripts/tool_scripts/cv_probe.py:36 _json_arg` 本身**两种都收**（`path.exists()` 则读文件，否则 `json.loads`）
⇒ 坏的是 wrapper 的强制路径化，不是 cv_probe。

## 3. 影响面（这是本单值得高优先级的理由）

- **`px_m_calibrator` = 像素→米的唯一出厂工具**。它在隔离沙箱里从未被成功调用过。
- 已核实 `run_2026-08-16_reading_restart_E1_uncapped` 的 access_log：读图器试了 4 次
  （1 次撞旧文档形态被 guard 拒，3 次 guard 放行但零产出），然后才改写硬编码坐标的自制脚本。
  ⇒ 项目此前记的结论「能力给了、用了、零次用于测量」**漏了一半**：出厂测量工具在它脚下是坏的。
- `candidates_json`（`overlay_logger`）同族，**大概率同病**，请一并验。

## 4. 授权改动面（只有这四个文件）

1. `src/agent/execution/isolation_templates/run_cv_probe.py`
2. `skills/intake_pipeline/0_reading/cv_toolbox.md`（示例须与修好后的真实可用形态一致）
3. `tests/test_isolation.py`（或新建 `tests/test_f49_calibrator_anchors_json.py`，你选）
4. 本单同目录下的执行日志（`AI_agent/logs/reviews/execution/2026-08-16_f49_sol.md`）

## 5. 验收要件（缺一不可）

**R-1 三种形态全部可用**，且都真跑出 sidecar + overlay：
   ① 内联 JSON 字符串（direct `--anchors-json '[...]'`）
   ② request/batch 里的 JSON 数组
   ③ 文件路径（**现有唯一可用形态，⛔ 不得因修法而坏掉**）

**R-2 路径语义不得放宽**：`image` / `out_dir` 仍严格按路径解析与包含性校验；
   `out_dir` 的可写根约束（`OUTPUT_ROOT_DIR="out"`）**一字不动**。
   判 JSON 还是路径的依据要写死且可判定（建议：`str` 去空白后首字符 ∈ `[`/`{` 即视为内联 JSON；
   其余按路径）——**你若认为该判据有更好的写法或有反例，按 §6 直接推翻它。**

**R-3 锁必须走真实入口且自证前提**：
   - 锁要经 **`tools/run_cv_probe.py` 的真实命令行入口**（⛔ 不许只单测内部函数）；
   - **每条锁必须先证明它在修法前是红的**：贴出「在未修的树上跑同一条测试」的失败输出。
     没有这段输出的锁一律视为未交付（本仓已有多次「全仓绿但锁是假的」前科）。

**R-4 guard 与 wrapper 不得对同一形态给出不同判定**：修完后 `guard.py` 放行的形态，
   wrapper 必须也能跑通；反之 wrapper 拒的，guard 不该先放行。给出这条的实测对照。

**R-5 文档一致性**：`cv_toolbox.md` 的示例 与 `run_cv_probe.py` 的 `_USAGE_TEXT`
   **不得再出现任何跑不通的形态**。逐条实跑贴输出。

**R-6 全仓不回归**：`python -m pytest -p no:cacheprovider -q`（走 `/opt/venv`，⛔ 别用仓内 `.venv/`，
   它的 numpy 自 08-01 起是坏的）。贴汇总行。基线 = 本单发出时工作树。

## 6. ⚠️ 可能错的前提，请主动证伪

本单 §2 的病因是 orchestrator 读码 + 复跑得出的，**但它是【可能错的前提】，不是结论**。请独立核：

- 「`anchors_json` 进 `PATH_KEYS` 是设计意图（防路径逃逸）」——**我没找到它的原始理由**。
  若你查出它确实在挡某个真实攻击面，**修法必须换一种、并把该攻击面写清楚**，⛔ 不许直接放开。
- 「上游 `_json_arg` 两种都收」——我只读了代码没有穷举，请实测。
- 「`candidates_json` 同病」——我没验，可能是错的。

**orchestrator 本轮已知错误率 = 24/24 曾被证伪的派工前提**（本项目历史统计，含今天两条）。
⇒ **本单里任何一句分类/因果陈述都欢迎被推翻，推翻比照做有价值。**

## 7. 交付形态

- 回主对话只给**简报**：改了哪几个文件 / R-1..R-6 逐条结论 / 全仓汇总行 / **审阅需求(review-ask)**。
  ⛔ 不要贴 diff、不要贴文件内容。
- 详细过程写 `AI_agent/logs/reviews/execution/2026-08-16_f49_sol.md`。
- ⛔ 不 commit。
