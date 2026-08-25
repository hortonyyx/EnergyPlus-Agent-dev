# 跨家族复核请求 · 装机路径止血（F-94 A 案）

- **日期**：2026-08-25　**对方**：GLM 家族（用户定「施工走 Claude 侧，审走 GLM」）
- **档位**：工程档 ⇒ **审恒升一档**；⛔ **谁写谁不批**（派工单 orchestrator 出、施工 Claude 家族做）
- **原始需求**：[`2026-08-25_f94_bootstrap_dispatch.md`](2026-08-25_f94_bootstrap_dispatch.md)
- **上一轮同族裁决**（供参照）：[`../verdict/2026-08-25_merge_blockers_f93_f94_glm_verdict.md`](../verdict/2026-08-25_merge_blockers_f93_f94_glm_verdict.md)

## 一、被审对象

| | |
|---|---|
| **diff** | **`91ae82d`** —— `git show 91ae82d` / `git diff 8c780ba..91ae82d`（BASE = 开工 HEAD `8c780ba`）|
| **改动形状** | 16 个 `scripts/**` 脚本各 +5 行自举 + 新增 `tests/test_scripts_bootstrap_lock.py` |
| **测试输出** | 施工报告粘贴的原文 → [`../execution/2026-08-25_f94_bootstrap_construction_report.md`](../execution/2026-08-25_f94_bootstrap_construction_report.md) |
| **orchestrator 已机械核过** | 范围 17 文件/300 行 · 工作树未被扫 · ⭐ **主树 `src/__init__.py` 未被行为验证的 marker 污染**（0 字节、最后改动 4 月）· 临时 worktree 已清理 · 全量 3014→3016 净增 2 自洽 · 16 这个数已独立复核 |

⛔ 只看**原始需求 + `git diff` + 测试输出**，⛔ 不看长篇自述；自述与 diff 冲突以 diff 为准。
⚠️ 树上另有 orchestrator 并行的 `AI_agent/` 管理文档提交，**与本单无关**，⛔ 别算进施工范围。

## 二、⭐ 请重点攻的五条

1. ⭐⭐ **那道新锁是不是真的有分辨力？**
   `tests/test_scripts_bootstrap_lock.py` 用 AST 扫描 `scripts/**`，
   找「有 `from src…`/`import src…` 但模块级没有先行 `sys.path.insert`」的脚本。
   施工席位**自带了一个合成 offender 的自检**（这正是你上一轮 findings #2 提的改进）。
   ⭐ 请独立验证：**把任意一个已修脚本的自举行摘掉，这道锁会不会红、且红在那个文件上**？
   并判断 AST 判据本身有没有洞（例如：bootstrap 写在 `try:` 里、写在 `if __name__` 里、
   用 `sys.path.append` 而非 `insert`、用 `os.sys.path`、相对层数 `parents[N]` 写错）。
2. ⭐ **16 这个数对不对？**
   orchestrator 独立数过：`scripts/**/*.py` 共 **32**，含 src 导入的 **22**，原有自举 **6** ⇒ 需改 **16**。
   ⚠️ **派工单 §一 写的「其余 26 个」是错的**（照抄上一轮席位说法，那 26 里有 10 个不 import src）
   —— 这条 orchestrator 已自认。请你独立复核 22/6/16 这三个数。
3. ⭐ **行为验证做了没有、做对没有？**
   派工单要求：造一棵**非主树**工作树，裸跑 **2 个已改脚本 + 1 个未改对照**，贴实际输出。
   ⛔ **只读代码的结论不算**。请判断它贴的输出是否真的证明了「已改的解析到自己那棵树」。
4. **范围**：⛔ 是否碰了 venv / `.pth` / 装机配置？那是 B 案（**已转维护债 D-2**），**碰了即 REJECT**。
   ⛔ 是否碰了 `src/agent/pipeline` 内核 / 交接契约 / `src/validator/`？
5. ⚠️ **副作用：E402。**
   自举行插在 import 之间 ⇒ 那 16 个文件的后续 import 不在文件顶部。
   `pyproject.toml` 的 ruff 配置 **select 含 `E`、ignore 只有 E501** ⇒ 规则上 E402 会命中。
   ⭐ **但 orchestrator 实测：ruff 未安装，且 `tests/` 与 hook 里没有任何 lint 门** ⇒ 当前不会让全量变红。
   **请判断**：这是否可接受（它沿用的是那 6 个脚本原本就有的模式，从 6 处扩到 22 处是规模变化不是类别变化），
   还是应当要求加 `# noqa: E402` 或把 E402 加进 ignore。**⛔ 这不是阻塞项，请给意见即可。**

## 三、验收判据

1. **全量绿**：`python -m pytest -n auto` ⇒ 0 failed / 0 errors；xfailed 与修前一致或有解释。
   ⭐ **请自己跑一遍**，⛔ 不要只信施工席位粘的汇总行。
2. **新锁红/绿两段**：施工方应提供「补完前跑一次会红并列出漏网脚本」+「补完后转绿」。请复验。
3. **提交卫生**：diff 里⛔ 不应混入 `AI_agent/` 下的管理文档。

## 四、⚠️ 请一并回答

**跨家族「停下上报」累计 25/25 全是派工方题错**（上一轮你自己新指出了第 25 处）。
⇒ **这次的派工单本身有没有题错？**
已知我错了一处（那个「26 个」）。**还有别的吗？** 尤其请攻：
- 「A 案 = 给脚本加自举」这个方向本身对不对（你上一轮说过「长期应对齐 B，A 只收窄暴露面不消除机制」）；
- 派工单要求的那道锁，**是不是把 A 案从「约定」变成了「机制」**？还是它只是把遗漏从「静默」变成「响亮」，
  而**真正的机制性根治仍然只有 B**？——**这个区分请说清楚**，它决定债 D-2 的紧迫度怎么写。
