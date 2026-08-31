# 跨家族审请求书 · ②-2 **模块 2**：correction 证据契约类型层

- **日期**：2026-08-31 · **请求方**：orchestrator · **施工方**：**GLM 家族** · **审阅方**：**Claude 家族**（换人审 · 审恒升一档）
- **送审对象** = **`31f873d`** · **基线** = **`8abd6e0`** ⇒ 以 `git diff 8abd6e0..31f873d -- src/agent/correction/evidence_contract.py tests/test_o22m2_evidence_contract.py` 为准
- **派工单** → [2026-08-30_o22m2_evidence_contract_dispatch.md](2026-08-30_o22m2_evidence_contract_dispatch.md)（⭐ 含末尾 §六–§八 的二次发单补充）·
  **执行档** → [../execution/2026-08-30_o22m2_evidence_contract_execution.md](../execution/2026-08-30_o22m2_evidence_contract_execution.md) ·
  **口径（已过审设计稿）** → [../verdict/2026-08-30_o22_evidence_contract_gpt_design.md](../verdict/2026-08-30_o22_evidence_contract_gpt_design.md)
- ⚠️ **同机有两个写席位在飞**（GPT 写 `judge/as_measured.py` + `gt_staging/`；GLM 写 `correction/evidence_adapters.py`）
  ⇒ **你是只读席位**：实验一律 `git archive 31f873d` 到 `/tmp` 副本里做；跑测 **`-n 6`**；**唯一可写 = 你的裁决书**。

---

## 〇、⛔ 请这样审
不信自述 · **引用位置一律回文件 `grep -n` 核**（⛔ 别对 `git show` 输出 `grep -n`）· 一次红/绿都不是证据 ·
⛔ 不许 `pip install -e .` · ⛔ 不许改被审对象 · ⛔ 不许 `git add`/`commit`。
**裁决**写到 `AI_agent/logs/reviews/verdict/2026-08-31_o22m2_crossreview_claude.md`，
格式 = `APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK`，**阻断与不阻断分开列**，每条给：现象 → **你自己的**复现命令与读数 → 影响 → 方向。

## 一、施工方自报（⛔ 全部待你独立复核）
类型层 + 硬不变量 1–8 校验器 + **28 条锁**，**零接线**；三份真实产物各自构造出 bundle；
**NF-4 五种破坏的前四种从「今天 PASS」变成响亮失败**，第五种留 pin 归模块 3/4。
一个架构决定：**bundle 的构造工厂在测试文件里，⛔ 不在生产代码里**（理由：派工单禁「不产 adapter」，
翻译是模块 3 的活）⇒ 它自称**承重锁 = `validate_evidence_bundle`（生产代码）**，构造期拒绝只是早失败。

## 二、⭐⭐⭐ 请优先打的三处（前两处是它自报的最薄弱处）

### B1 · 它自报最薄弱：**`channel_status` 的 `present` 与实际载荷之间没有闭合锁**
它的原话：「`walls: present` 但 `wall_claims` 为空」**今天能全绿通过**；它只锁了「`absent` 必须带 debt」这一半，
「`present` 必须真有载荷（或显式记零载荷 debt）」**没有立门**。
⚠️ 而设计稿 §3.3 立 `channel_status` 的**动机**恰恰是防「**墙走新腿、窗悄悄仍从目录里随便找 `strokes`**」。
⇒ **请判**：① 这个洞今天有没有实害（本层零流量，所以问的是**接线日**）；
② 它说「载荷闭合的语义属模块 3」——**这个边界站得住吗**，还是在把自己该判的推走？
③ ⭐ 它自己说「若不补，就是下一个『**无一假数却八门全绿**』的形状」—— **这句自评对不对？**

### B2 · 它自报次弱：**不变量 6/7 靠【文案子串】判定**
`AMBIGUOUS_CONTRACT_MATCH` 是用 `"AMBIGUOUS" in decision.reason` 区分的
⇒ 别处改一句措辞，这个 code 就会退化。
⇒ **请判**：它说「仍响亮、不是静默，只是 code 错位」——**这个安慰成立吗**？
⭐ 本项目口径：**词法匹配判无界输入的防线永远补不完**（[[lexical-guard-cannot-be-completed]]）。

### B3 · ⭐⭐⭐ 主控加：**「工厂在测试里」这个决定，会不会让 28 条锁里有一批锁的是【测试自己】**
它自己划了这条线（构造期拒绝 = 早失败、不承重；校验器 = 承重），并声称每一族破坏都有
「**绕开构造器、直接打在校验器上**」的独立证据。
⇒ **请逐条核这句**：**28 条锁里，有几条在【绕开工厂】之后仍然红？** 几条其实只证明了工厂会拒？
⭐ 判据 = 本项目的 [[lock-must-exercise-real-entry-point]]：**摘得动才算数**。
⇒ 建议做法：把 `validate_evidence_bundle` 摘掉（neuter），看**恰好红几条**；再把工厂的拒绝摘掉，看红几条。

## 三、另外三个攻击面（主控加）

### A1 · **它把 NF-4 的第 4 种「收进本单」了 —— 这个扩范围对不对？**
派工单只要求前三种。它判定 `gap_index` 越界「是纯引用完整性、机械可查」⇒ 自行纳入。
⇒ 请判：**理由成立吗**？以及它是否**顺手**把别的东西也带进来了（`git diff` 逐条核范围）。

### A2 · **第五种 pin 的归属划分**
它把「未被选中的悬空候选」pin 给模块 3 与模块 4，理由 = 设计稿 §4.3「bundle 只引用**被选中**的 pairs」。
⇒ 请判：这个 pin **会不会永远没人接**（[[review-scope-complement-must-be-reconciled]]：缝里那半没人审）。
⭐ 具体问法：**模块 3 的派工单还没写** —— 那这条 pin 今天靠什么保证不丢？

### A3 · ⭐⭐ **请自造第 6 类破坏，且要「结构合法但语义假」**
NF-4 的五种是**复核方挑的**，本单的 15 种是**施工方挑的**。
⇒ 请你**再挑一种谁都没想到的**。方向提示（⛔ 别被我限住）：
**数值可信度**（面线坐标合法但物理荒谬）· **跨视图身份**（同一个 id 在两个 view 里指不同东西）·
**bundle 自身的 `content_sha256` 与其内容的关系**。

## 四、两个是非题
1. **「零接线」是真的吗？** —— `vector_contract.py` / `pipeline.py` 相对基线是否**整文件零 diff**。
2. **它有没有碰任何进 `canonical_bytes` 的面 / 任何已落库产物？**（本项目 08-30 刚因这条栽过，题错 #51）

## 五、⛔ 不属于本单
F-153（在飞）· ②-1d 返工 · 模块 3（在飞）· F-152 的彻底解 · NF-1 微单（另有单）。
