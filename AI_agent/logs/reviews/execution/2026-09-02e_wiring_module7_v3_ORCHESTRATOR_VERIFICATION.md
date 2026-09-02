# ⚠️ **主控验证记录**（⛔ **不是施工方自述**）· 接线（模块 7 上半）v3

> # ⛔⛔ 先读这一段：**这份文件的身份和平常的交件不一样**
> **施工方（GLM 家族席位）撞 5 小时额度上限中断了，没能跑全量、也没写交件。**
> 它的**实现已经分段提交完整落地**（4 个提交，工作树干净，零孤儿件）。
> ⇒ 本文件是**主控自己跑、自己量**的读数，用来替代那份缺失的交件。
>
> **⭐ 这份文件【能】提供**：全量读数 · 我逐条量到的验收证据（附命令与输出）。
> **⛔ 这份文件【不能】提供**：施工方的自述、它的设计理由、它做过而我没量到的事。
> ⇒ **复核方请照此调整取信方式**：凡本文件没写的，就是**没人报过**，⛔ 不要当成"施工方声称过"。
>
> **主控边界**：我**只跑、只量，⛔ 未改一行实现**。被审内容 = 施工方那 4 个提交，原样。

- **日期**：2026-09-02 · **记录方**：orchestrator
- **施工方**：GLM 家族施工席（`/tmp/wiring_glm`）· **中断**：`429 · 已达到 5 小时的使用上限（21:18:45 重置）`
- **落地 commit**：`ae01b38` / `1665064` / `6a906db` / `ebe90cf`（逐个 `cherry-pick -x`）
- **派工单**：[接线 v3 返工](../request/2026-09-02e_wiring_module7_v3_rework.md)

---

## 一、全量（主控代跑）

```
$ python -c "import src.agent.pipeline as m; print('__file__ =', m.__file__)" \
    && python -m pytest -q -n 6 -p no:cacheprovider
__file__ = /tmp/wiring_glm/src/agent/pipeline.py
3662 passed, 13 xfailed, 211 warnings in 477.26s (0:07:57)
EXIT=0
```
⭐ 环境自证与 pytest **同一条命令**；凭据已注入（⇒ 无 F-158 那条环境红）。

## 二、我逐条量到的（⛔ 只覆盖我量过的，未量的一律留白）

### 验收 1 / 2 —— 配置节按真名加载 · route 记解析后的
```
src/configs/llm.yaml:81            correction_decision:
src/agent/pipeline.py:812          DECISION_BEAT_LLM_SECTION = "correction_decision"
src/agent/pipeline.py:807-811 注释  "BY ITS REAL NAME (v3, B-1 — ⛔ never through the
                                    `intake_`-prefixing `_section()`, which silently
                                    resolved this to `intake_correction`)"
src/agent/pipeline.py:1101         response_source = f"fixed_responses({len(...)}; model NOT called)"
src/agent/pipeline.py:1104         llm_section_resolved = None
```
⇒ **量到**：节按真名加载、缺失是响亮配置错（代码注释自述，我未构造缺节实测）；
⭐ **夹具路径与模型路径在落盘上可分**（`model NOT called` 是显式串）。
⛔ **未量到**：`llm_section_resolved` 在**模型真跑**那条路上写进 route 的实际值 —— **需要一次真实模型跑，我没跑**。

### 验收 3 —— 坐标在**类型层**装不进去（⭐ 我实测了）
```
$ python -c "<TypeAdapter(CodeToken) 逐串校验>"
模块自证: /tmp/wiring_glm/src/agent/correction/decision_schema.py
  '(12, 34)'         -> 拦住      '12,34'       -> 拦住
  'X = 12, Y = 34'   -> 拦住      '0x1F'        -> 拦住
  '[12, 34]'         -> 拦住      'MERGED_LT_3' -> 拦住
  '(12.5, 34.5)'     -> 拦住      'ok'          -> 拦住
  'x=12 y=34'        -> 拦住
```
`CodeToken = Annotated[..., StringConstraints(pattern=r"^[A-Z][A-Z_]*$", ...)]`
⇒ **字符集里没有数字** ⇒ 任何进制、任何写法的数都进不来。**上一轮漏的三种全部拦住。**

⭐⭐ **主控自己踩过的坑，写在这里防复核方重踩**：我第一次用**裸 dict** 喂
`assert_response_payload_carries_no_coordinates`，那三种**仍然放行**，我差点判"没搬只是补正则"。
**那个词法正则确实还在（`decision_schema.py:379`），但它已被显式降级为诊断**，⛔ 不再是防线。
⇒ **量这条必须从类型入口量，从运行时函数量会量错面。**

### 验收 5 —— 多轮归档逐轮可分
`src/agent/pipeline.py:991  prefix=f"correction_decision_r{packet.round_index}"` ⇒ **量到**。
⛔ **未量到**：round 0 的 decision hash **能否真的从归档重算** —— 需要一次真实模型跑。

### 验收 4 / 6 / 7
- **7 全量绿** ✅ 见 §一。
- **4（B1/B2 各一条先红后绿锁）· 6（已认可三项没被改坏）** ⇒ ⛔ **主控未独立验证**，
  只知道全量绿。**请复核方按派工单原样查。**

## 三、⛔ 明确缺失的东西（复核方请当作"无人报过"）

1. **施工方交件**（`2026-09-02e_wiring_module7_v3_glm.md`）—— 不存在。
2. **一次真实模型端到端跑** —— 上一轮有（186.232 秒、被复核方独立复现过），
   ⛔ **本轮改了模型加载那条路之后没有人再跑过**。
   ⇒ ⭐ **这恰恰是本轮阻断 1 改动的正上方** —— 建议复核方**优先跑这一次**。
3. 施工方对 §二 里"未量到"各项的说明。
