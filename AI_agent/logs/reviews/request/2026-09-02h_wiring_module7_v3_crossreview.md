# 跨家族复核请求 · **接线（模块 7 上半）v3**

- **日期**：2026-09-02 · **请求方**：orchestrator · **复核方**：**Claude 家族复核席**（⛔ 不得 GLM —— 施工方是 GLM；GPT 正在飞另一件）
- **被审 commit**：**`ebe90cf`**（施工方四个原件逐个 `cherry-pick -x` 落分支）
- **派工单**：[接线 v3 返工](2026-09-02e_wiring_module7_v3_rework.md) ·
  **上一轮裁决**：[GPT REWORK / 阻断 2](../verdict/2026-09-02d_wiring_module7_v2_crossreview_gpt.md)

> ## ⛔⛔⛔ 本件与平常不同：**没有施工方交件**
> 施工方（GLM）撞 5 小时额度上限中断，实现**已分段提交完整落地**，但**没跑全量、没写交件**。
> ⇒ 代替它的是一份 **[主控验证记录](../execution/2026-09-02e_wiring_module7_v3_ORCHESTRATOR_VERIFICATION.md)**
> —— ⭐ **请先读那份文件的开头**：它写清了**哪些是主控量到的、哪些是明确没人量过的**。
> ⛔ **凡它没写的，就是【没人报过】，不要当成"施工方声称过"。**
> ⇒ ⭐ **这意味着你的独立复跑比平常更重要**：平常你在核对一份自述，这次**没有自述可核**。

**被审 diff**：
```
src/agent/correction/decision_schema.py  +109 -24
src/agent/pipeline.py                     +82 -10
src/configs/llm.yaml                       +9  -6
tests/test_o22m7_evidence_wiring.py      +393 -35
tests/test_o22m56_decision_loop.py        +27 -27
```

---

## 一、上一轮的两条阻断，这轮怎么修的（⭐ 请你验，⛔ 别采信我的转述）

- **阻断 1**（配置节名字对不上 ⇒ 静默回落 ⇒ **跑通用的不是配置点名的模型**）：
  改为 `DECISION_BEAT_LLM_SECTION = "correction_decision"` **按真名加载**，
  代码注释自述"⛔ 绝不走 `intake_` 前缀的 `_section()`"，节缺失 = 响亮配置错。
- **阻断 2**（坐标闸是词法正则、整数坐标全穿）：`reason_code` 等收窄为
  `CodeToken = StringConstraints(pattern=r"^[A-Z][A-Z_]*$")` —— **字符集无数字**。

## 二、⭐⭐⭐ 请你优先做的一件事

**⛔ 本轮改了模型加载那条路之后，【没有任何人跑过一次真实模型端到端】。**
上一轮那次跑通（186.232 秒 / 2 轮 / 22 项裁决 / `success=True`）是**改动之前**的，
而**本轮阻断 1 的改动正落在它正上方**。

⇒ ⭐ **请你跑一次真实模型端到端**，并回答：
1. 它还跑得通吗？
2. `route` 里记的**解析后的节/模型**，是不是**真的**是 `correction_decision` 那一节？
   （上一轮的病就是"记的是请求名的回显" ⇒ 证明不了实际拿到谁。）
3. round 0 的 decision hash **能不能从逐轮归档独立重算**？（NF-1 声称修了，⛔ 无人验过。）

## 三、请你打的三处（假说形态，⛔ 未代判）

| # | 疑点 | 为什么怀疑 |
|---|---|---|
| **H1** | **那个词法正则还在（`decision_schema.py:379`），它真的只是诊断了吗？** | ⭐ **主控踩过这个坑**：我用**裸 dict** 喂运行时函数，早上漏的三种**仍然放行**，差点判"没搬只是补正则"；从**类型入口**量才是全拦住。⇒ 请你确认**每一条**字符串通道都真的走了类型层，⛔ 别有一条漏网还靠那个降级正则兜 |
| **H2** | **`CodeToken` 收得太紧会不会打断模型？** | `^[A-Z][A-Z_]*$` 要模型自己 MINT 一个全大写标识符。⭐ 这与 §二 的真实模型跑是同一件事：**模型可能就是产不出合法值** ⇒ 那会变成一个"跑不起来"的类型层 |
| **H3** | **B1/B2 的先红后绿锁真的能红吗？** | 派工单验收 4 要求两条阻断各有一条先红后绿锁。⛔ **主控未独立验证**，只知道全量绿 ⇒ [[neuter-proves-wiring-not-discriminating-power]]：变红≠有分辨力，**摘掉实现要真的回到红** |

## 四、常规项

1. 派工单 §五 **七条验收**逐条独立复跑（主控只覆盖了 1/2/3/5/7 的一部分，见验证记录 §二的留白）。
2. ⭐ 指南 §五#2：**再找一种能骗过它的真实错误形态**。
3. **环境**：本 worktree 无 `.env`。跑全量前同一 shell 先执行
   `set -a && . /workspaces/EnergyPlus-Agent-dev/.env && set +a`（否则 `test_zone_agent.py` 必红一条 = F-158）。
   环境自证与 pytest 同一条命令：
   `python -c "import src.agent.pipeline as m; print(m.__file__)" && python -m pytest ...`
4. 跑测 **`-n 6`**。
5. 裁决 → `AI_agent/logs/reviews/verdict/2026-09-02h_wiring_module7_v3_crossreview_claude.md`，
   给 APPROVE / APPROVE-WITH-FINDINGS / REWORK + 阻断数 / 不阻断数。
6. ⭐ **分段提交**（今天已有两个席位因中断丢过工作）。
