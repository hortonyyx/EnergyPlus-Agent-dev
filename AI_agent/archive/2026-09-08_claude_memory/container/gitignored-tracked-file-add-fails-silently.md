---
name: gitignored-tracked-file-add-fails-silently
description: 被 .gitignore 匹配的文件即使已 -f 入库，以后每次改 git add 仍被静默拦下；2026-08-09 已在本项目根治=把「按目录名形状」的规则改成「按位置」
metadata:
  node_type: memory
  type: feedback
  originSessionId: 53f7e084-3355-477f-817a-213aa11758bf
  modified: 2026-08-10T06:47:58.062Z
---

被 `.gitignore` 匹配的目录里的文件，**`-f` 入库之后，后续每一次修改 `git add` 仍会被拦，
而且失败是静默的**（2026-08-08 当轮连栽两次）：`--amend` 照常成功 · `git status` **干净** ·
`git log` **正常** · **但那 19 行根本不在 commit 里**。

**Why**：`git status` 只看 index vs 工作树的已跟踪集合，被 ignore 拦住的 add 不进 index，
于是「没有改动」和「改动没加进来」外观完全一致。
同后果不同成因的还有 [[wrapup-commit-sweeps-other-seats-wip]] 的「漏掉测试锁文件」。

**How to apply**：
- ⛔ **验收禁止用 `git status` 干净当证据**，必须 `git show HEAD:<path> | grep <新加的串>`
  或 `git show ":<path>"` 查 index —— 与 [[lock-must-exercise-real-entry-point]]
  「摘得动才算数」同精神：断言落真实产物，不落「看起来没事」。
- 改这类文件时每次都要 `-f`（在没根治的仓库里）。

**⭐ 2026-08-09 本项目已根治（用户拍板「一起收了」），修法比原计划省得多**：
- **⛔ 原登记的方案是「把过程痕迹移出 `20*_*/` 命名空间」（搬 19 个目录 + 改全部文档引用）——
  没有采用。** 查证后发现根因更浅：那条 `20*_*/` 写于 2026-05-05，commit body 写明**只为挡
  协作者一份 LangSmith 归档 `20260414_192502/`**，却写成了**不限路径的「目录名形状」规则**；
  而**该形态的目录今天工作区一个都不存在** ⇒ 规则挡不到任何本来要挡的东西，只在误伤自己。
- **修法 = 把「按名字形状」改成「按位置」**：`20*_*/` → `**/backup/**/20*_*/`。零迁移、零引用更新。
- **⭐ 通用问法（比结论值钱）**：撞见一条过宽的忽略规则时，先问
  **「这条规则本来要挡的那个东西，今天还在吗？在哪？」** —— 常见形态是
  **为一个具体位置写了一条按名字匹配的全局规则**，日久就只剩误伤。
- **⭐ 顺带查实：`!` 例外可能是死的** —— git **无法在已被排除的目录内再包含**
  （`!backup/Skill_history/` 只解禁目录本身，其 `20*_*/` 子目录照旧被排除，实测），
  且有一条例外指向的路径**根本不存在**。⇒ 这是 [[model-visible-but-not-its-business]] 那族
  「声称在守其实没守」的又一例，**这次在 `.gitignore` 里**。
- **⛔ 债还有第三面（2026-08-10 修掉一半）**：`*.txt` / `*.log` 是**全局忽略**，同一个陷阱换了条规则（仍挂）。
  **已修的那一半 = `eplusout.*`**：它连带挡掉 `eplusout.end`（0.1 KB，"0 Severe" 那一行，管理文档反复引用）
  与 `eplusout.err`，而 **`validate_case` 把 `EP/EP_run/eplusout.end` 列为必需产物**
  ⇒ **新克隆缺它就判「必需产物缺失」，红的理由与那次 run 无关**。
  修法同样**按位置**：`!case_tests/**/eplusout.end` / `!case_tests/**/eplusout.err`（例外**实测为活**，
  因为父目录未被排除；大件 `.eso`/`.csv` 仍被挡）。

- **⭐⭐ 2026-08-10 换来的新判据 —— 判断一条 ignore 规则「有没有误伤」，必须逐个列出它实际挡掉的文件**：
  `eplusout.*` 挡的 26 个文件里 **24 个是可再生大件（各 7–10 MB）、2 个是承重证据（各 ≤3 KB）**。
  我只看规则名字就在提交说明里写下「挡的正是该挡的东西、未见误伤」，**当场就是错的**。
  同一轮还错第二次（说 `eplustbl.csv` 保留了，其实被 `:285` 挡着）。
  ⇒ 与 [[interface-sweep-gate-vs-range-check]] 的「『有门』必须落到那一行在约束什么」、
  以及 [[stop-and-report-catches-dispatcher-errors]] 的「凡『一律/全部』必须逐处列值对账」**同一个错法**。
  ⭐ **两处错都是被本条自己的纪律（`git show HEAD:<path>` 逐件验收，⛔ 不看 status）照出来的** ——
  按 status 验收则两处都会静默漏过。**同轮另一个同族实犯**：把包装命令的退出码当成后台席位跑完
  （见 [[lock-must-exercise-real-entry-point]] 的「非 None ≠ 成功」）。

**⭐ 改忽略规则的验收姿势**：改前改后各跑一次
`git status --porcelain --ignored=matching | grep '^!!'`，**逐条 diff**。
注意「新变为被忽略」那批可能是假的 —— 目录解禁后 git 才能进去、把**既有其它规则**
命中的文件逐个报出来，必须用 `git check-ignore -v --no-index <path>` 落到**具体哪一行规则**
才能定性（同 [[interface-sweep-gate-vs-range-check]] 的「有门必须落到那一行在约束什么」）。
