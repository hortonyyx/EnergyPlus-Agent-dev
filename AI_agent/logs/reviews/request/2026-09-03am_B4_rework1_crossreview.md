# 复核单 · **B4 返工 1** 跨家族审

- **日期**：2026-09-03（第三程）· **复核方**：**Claude 家族**（⛔ **不得 GLM** —— GLM 是施工方）
- **工作目录（写死）**：`/tmp/b4rw_review_claude`（detached @ `wt/09.03ag_b4`）· ⛔ 别写主树
- **上一轮裁决**：[`2026-09-03ah`](../verdict/2026-09-03ah_B4_crossreview_gpt.md)（GPT 出，**REWORK / 阻断 2 / 不阻断 3**）
- **返工单**：[`2026-09-03aj`](2026-09-03aj_B4_rework1.md)
- **审对象**：`git diff 4ea103d..wt/09.03ag_b4` —— 三笔（`5b1b0c4` B-1 · `b15ee62` B-2 · `1999687` 执行档）
- **改动面**：`src/agent/correction/opening_synthesis.py` **328/43** · `tests/test_b4_opening_synthesis.py` **321/21**
- **自报全量**：`3778 passed`（= `3756 + 20 + 2`）⇒ ⭐ 请核

## 一、⭐ 逐条复核上一轮那两条阻断（⛔ 别只读代码，跑变异）

| 上轮 | 上轮实测读数 | 你要判 |
|---|---|---|
| **B-1** 注册表 handler **不承重** | 把前缀指向语义不相干但存在的 `grid_units` ⇒ `WRONG_HANDLER_ACCEPTED`，**债照销** | ⭐ **同样的变异现在必须响亮失败或至少不销账**。⛔ 「名字存在且 callable」不算 |
| **B-2** 销账**没绑定源实例** | 用 B3 **真实**字节为 East/West 各产一张债，只跑 South 的门 ⇒ **两张真实债一起被销** | ⭐ **重造那个反例**：混入 **≥2 张其他 facade 的真实债** ⇒ **只能销当前实例** |

## 二、⭐⭐ 派工方在这一轮做了一次【签字】，请你审这个签字本身

上轮复核方把 B-2 的修法选择交回派工方。**我签了：用现有的 `affected_refs`**，理由三条：
① 它已带 `input_east` / `input_west`，够用 ② **零 schema 改动 ⇒ 零哈希扰动 ⇒ 不碰基线**
③ **T4-a（给债加 obligation/owner 正式字段）仍在等用户拍板**，⛔ 不许本单提前替它做决定。

> **请判**：`affected_refs` **够不够**承担「绑定到本次核过的那一个源实例」这件事？
> ⛔ **如果你认为它不够、必须升 schema，请直说** —— 那我这个签字就是错的，该翻。

## 三、⭐ 施工方自报最薄弱（请重点打）

> **`elevation_source` 是调用方声明的信任边界** —— dict **无字节可重哈希**，**身份无法机械重算**。

⭐ 它自己给了出路：建议 B5 接线单写死「身份必须从 bundle 的 `source_artifacts[0]` 提取，⛔ 不许手拼」。
**请判**：① 这个信任边界在**本轮**是否可接受 ② 它给的出路够不够 ③ 要不要现在就补一道门。

⚠️ **另**：施工方说明第一笔提交把主控预置暂存的**返工单与裁决两份管理文件**一并带入（内容一字未动），
已在执行档开头记明。⭐ 请顺手核实**确实一字未动**（`git show` 比对）。

## 四、⛔ 本轮明确不该做的（核它有没有越界）

⛔ 改 `EvidenceDebtV1` schema（T4-a 等用户拍板）· ⛔ 为「0 对」加任何对齐/吸附/阈值 ·
⛔ 重做本体（等式门 / 逐边厚度 / 区间配对 / 前提命名 —— 上轮已过审五项）。
⇒ ⭐ 请核 `git diff --exit-code 4ea103d..HEAD -- src/agent/correction/evidence_contract.py` **为空**。

## 五、验收（照返工单 §五 六条逐条报）

`1` 处理器那一栏真承重 · `2` 销账绑定源实例 · `3` 两条都有常驻锁且有牙 ·
`4` schema 一个字节没动 · `5` 上轮过审五项不退化 · `6` 全量绿逐位闭合。

## 六、⚠️ 环境

```bash
cd /tmp/b4rw_review_claude && \
python -c "import src.agent.correction.opening_synthesis as m; print(m.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```
⛔ 不用 `-n auto`。⛔ 不跑 `pip install -e .`。⛔ 不要改代码。
⚠️ 同机有 GPT 席位在复审 B2，预期竞争；**判假红看有没有 summary 行**。

## 七、裁决

`AI_agent/logs/reviews/verdict/2026-09-03am_B4_rework1_crossreview_claude.md`：
`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` + **阻断 N / 不阻断 M**；
§一 两条 · **§二 那个签字正面回答** · §三 三问 · §五 六条。
⭐ 凡没能复现的，明写「未复现」。
