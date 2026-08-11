# F-9 路线② 施工单（第一批）｜**只做 S0 + S1**

**派工方**：orchestrator（Opus 5）· **执行席**：Claude 侧执行档（Sonnet）· **审**：GPT 侧（谁写谁不批）
**日期**：2026-08-11 · **基线**：全仓 2361 绿 / 10 xfail / 0 红（`-n auto`）

**唯一权威规范** = [`AI_agent/proposals/f9_route2_evidence_citation_design.md`](../../../proposals/f9_route2_evidence_citation_design.md)（v2.1，已过对抗审 + 轻门，零新增 finding）。
该稿是**累计式自包含**的，按它施工，**⛔ 不许改稿**。

> **⛔ 派工方历史错误率 13/13** —— 迄今每次执行席「停下上报」，查实**都是派工单的题错了**。
> **包括本单对范围的切分（只做 S0+S1）也可能是错的**：若施工中发现 S1 不动 S2 就无法保持行为不变，
> **停下上报，⛔ 不要顺手把 S2 做了。** 这是合法退出口，不是失败。

---

## 1. 本批范围（写死）

**只做设计稿 §10 的 S0 与 S1。⛔ 不碰 S2 / S3 / S4。**

| 步 | 内容（详见稿 §10 对应小节，落点见 §11） | 稿里对它的定性 |
|---|---|---|
| **S0** | 阶段合同、错误词表与 artifact 版本壳：新增 raw type · `CorrectionTarget.draw_model/full_model` · raw projection context · resolver artifact V2 · position decision / artifact strict models · 显式 loader registry · typed error categories。**均先不接 live production。** | 可独立验收：**是** |
| **S1** | 完整合并 facade convention：`facade.py::_CONVENTION` · `window_sources.py::_BASE_SIGN` · `facade_applicability.py::_BASE_SIGN` · judge 侧 `_BASE_SIGN` · inline XOR，全部并成单源；加 versioned mirror adapter。**行为保持不变。** | 可独立验收：**是**；施工上必须**先于 S2**，否则 shadow 会再造一份临时公式 |

**为什么这么切**：S0/S1 在稿里都写明可独立验收；S1 是 S2 的施工前置；而 S4 稿里明确
**「不能拆成可独立落地的小步」**（跨 schema / identity / writer 的原子批次）⇒ 不在本批。

**⛔ 明确不做**：不启用 detector（S3）· 不做 producer cutover（S4）· 不删 model-authored span ·
不改 live prompt · 不改 live production 接线（S0 的新类型**先不接**）。

---

## 2. 防假验证自检（**动代码之前先做完，做不到就停下上报**）

设计稿的兼容合同覆盖**三类** artifact，不是两类 ——
**v1 / v2 / historical-v3 producer artifact V1**。（请求书上一轮把它写成「v1/v2 两种」，
被 sol 纠正：仓库里已存在 historical v3 producer artifact V1；照二分法施工会漏掉一整类边界。）

**第一步：把这三类在盘上的真实样本逐类列出来**——文件路径 + 数量 + 各自的版本判据来自哪个字段。

- **三类都数得出来** ⇒ 继续施工，并把这份清单写进交付报告（它是 §12.2「Legacy scope」锁的夹具来源）。
- **有任一类数不出来 / 数出来的与本单描述不符** ⇒ **停下上报，⛔ 不许开始改代码**，
  也 ⛔ 不许用「有没有 span」去猜版本（稿 §12.2 Legacy scope 行明令禁止）。

---

## 3. 锁（按设计稿，不打折）

**总纪律 = 稿 §12.1 七条**，逐条落到本批每一道新增门：
① 真实入口路径锁 · ② 明确 check-id 的**正向 PASS 锁** · ③ 失败夹具**先自证前提** ·
④ neuter / mutation 后**必红** · ⑤ 逐 window 属性 oracle · ⑥ 对「**是否被第二道防线先拦**」作显式断言 ·
⑦ hash / 集合相等断言前，**先断言双方非空与 totality**。

**本批对应 §12.2 锁矩阵中这几行**（若你判定某行必须等 S2+ 才能施工，**停下上报并说明理由**，⛔ 不要静默跳过）：

- `Raw contract` · `Raw projection context` · `Legacy scope` —— 属 S0；
- `Convention truth` —— 属 S1（4 facade × 2 mirror × 2 local-direction 外部字面量 truth table +
  `"true"/"false"/"unknown"` 字符串边界 + live-consumer structure lock）。

**三条容易翻车的具体要求**（都是本项目实犯换来的）：

1. **⛔ 相等断言前必须先断言两边非空** —— 08-10 实犯：施工席声称「两个 digest 逐字节相同」，
   而两边都是 `None`（`None == None` 恒真），该性质从未被验过。
2. **⛔ 不许写只有负向断言的门** —— 一道门若只有「断言它 fail」的测试、没有「断言它 pass」的测试，
   则它恒红不可能被测试发现，且所有 fail 断言会永远绿（F-19 实证）。
3. **遮蔽自检** —— 对每把锁问：「**我这个夹具里，有没有第二条防线会先于目标门把这个变异拦下？**」
   若有 ⇒ 这把锁测的是那条防线、不是目标门。**凡发现遮蔽必须横扫同批所有锁**（08-10 实证：
   施工席在同批另一处发现过这个模式却没横向推广，orchestrator 还附议了「不需重复」—— 两方都错）。

**行为保持的证明方式**：S1 是纯合并、行为不变 ⇒ 需要一把**外部字面量 truth table**
（expected 手写，**⛔ 不许调用被合并的任何一份实现来生成 expected** —— 否则是恒等锁，
它只证明「两套规范已统一」，**不证明规范是对的**）。

---

## 4. 跑测与交付

- 中间轮跑受影响子集；**交付前跑一次全仓 `-n auto`**（基线 2361 绿 / 10 xfail / 0 红）。
- ⛔ **pytest 输出直接重定向到文件，退出码单独落一个只属于该命令的文件，中间不接任何管道**
  （`| head` / `| tee` 会 SIGPIPE 连带打断 pytest，通知里的「退出码 0」是管道尾巴的 —— 已两次实证）。
- 交付报告必须含：§2 三类 artifact 的实测清单 · 全仓绿数 · 新增锁清单与各自 check-id ·
  **neuter 逐把红点位置**（不是「总数变了」）· §3 遮蔽自检结论 · 稿 §13.3 完成定义中**本批已满足/未满足**逐条对照。
- **⛔ 不要 `git commit`**（orchestrator 统一落库）；**⛔ 不要改设计稿**；发现稿子有错 ⇒ 停下上报。
- production / shared module **⛔ 不得 import** `src.agent.judge` / `case_tests` / `tests` / 任何 GT 路径（稿 §11 末段）。
