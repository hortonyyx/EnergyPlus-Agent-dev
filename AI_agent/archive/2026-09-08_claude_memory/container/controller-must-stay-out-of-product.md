---
name: controller-must-stay-out-of-product
description: "不变量 #7 —— 2026-08-02 用户重订：禁的是「端到端主控伸手 + 成绩记错人」，不再禁「环节内部有 controller」；隔离原则改为限信息不限方法"
metadata:
  node_type: memory
  type: project
  originSessionId: 1fe41113-f07f-4e71-9a72-bdd0e9e20827
  modified: 2026-08-02T11:21:49.489Z
---

**⭐2026-08-02 用户重订（第三版，唯一口径）**，已落 `AI_agent/CLAUDE.md` §1.5 #7；
依据 = `AI_agent/logs/reviews/verdict/2026-08-02_reading_regression_controller_cv_investigation.md` §0.4/§0.5。
**07-31 版与 08-01 版凡与本版冲突处全部作废。**

**核心改判：要禁的从来是「谁在做」和「记成谁的成绩」，不是「环节内部有没有控制」。**

- **⛔ 端到端主控（我）对环节内部只能启动与接收**：✅ 创建 job / 传**冻结的** bundle+profile / 等待 /
  收 `status + output + evidence manifest`；dev 期编排（建工作区/spawn/merge/跑确定性工具）与**兼任 judge** 仍合法。
  ⛔ 写 directive/feedback · **看了图之后指导 worker** · 替它挑 CV 参数或返工区域 · 操作内部会话 ·
  **接触 gt 后把结论送回同一 run**。
- **✅ 新许可：reading 可以有自己的 controller**（`ReadingService` 内部组件）——
  与主控**彻底解耦** · **Flash 档或以下**（thinking off / 结构化输出 / 短上下文） ·
  **最多一次计划 + 一次局部返工** · **不得直接写最终坐标**（stroke 必须来自 worker + 工具证据） ·
  是**权衡方案不是永久架构**（后续代码化/降档/撤除）。
- **⛔ 成绩分三条 lane 记账**（`reading_mode` provenance 块）：**autonomous**（目标 VLM + 冻结工具箱、零 controller）·
  **controlled** · **tool-invention**。后两者算真实工程成功，但**不得记成「弱模型独立满分」**；
  autonomous lane 必须一直保留，否则不知道离「本地开源 VLM 自主完成」还有多远。
  **降档动因 = reading 要转本地开源 VLM 部署，Haiku 是那个档位的代理，不是省钱实验。**
- **⛔ 隔离原则改写**：**严格限制可见信息与写出边界，不限制在合法输入上采用何种计算方法。**
  按命令形态封杀通用 CV 编程（`python -c`/临时脚本）= 能力封口，封掉的正是 07-02 Sonnet 那条成功路径。
- **judge 出口不变**：不过 ⇒ 整轮盲重抽零信息；judge 不得说「哪里错了、该怎么改」。
  （区分：**环节自己的 controller 做局部返工是允许的**，受约束的是跨环节评判者。）

**08-01 排查的四条违规仍成立**（pilot 停等 review + `feedback.md` 续作〔「停下等审阅」写在产品 skill 库
`session_kickoff.md` 里，08-01 已改，`isolation.py:642` 同句副本一并改〕· per-run directive 198 行
〔**删它必须与补门成对做**，其 §2/§4.7 是两条缺失 gate① 检查的替代品〕· 预扫参数主控临时挑 ·
`check_feedback_text` 纯词法挡不住裸坐标）——但**同样的动作若由 ReadingService 内部 controller 做，现在合法**。

**⚠️ 「gate① 分辨力 = 0」这个旧结论要改口径**（08-02 主控实测）：08-02 那份产物 gate① **本来就抓到 5 条 fail**
（`dimension_chain_closure` ×4 + `stroke_dimension_consistency` ×1），只是 merge 没透传 profile ⇒
落盘成 `rectangular`+`exploratory` ⇒ 0 阻断；按声明的 `regression` 重算 = **4 条 blocker**。
**准确说法 = 「严格档从未真正执行过」**，不是「门没有分辨力」。详 [[reading-supervision-contamination]]。

**⛔ 2026-08-02 用户追加：reading 内部 agent 怎么设计 + 工具箱怎么持续迭代进化 = 架构决策，禁直接施工。**
必须走完整正规程序：**主控出问题书（只给事实与坑、不给解法方向）→ 跨家族出累计式自包含设计细稿 →
交叉对抗审（写稿的不审自己的）→ ⭐用户与主控当面敲定方案与架构 → 才派施工**。
修断线 / 重判 / 把已有正确路径工序化不受此限（补既有机制，非新架构）。

⚠️ 与 [[codex-execution-protocol]] 区分：那条讲开发期主控不许自己写码；本条讲环节内部的控制边界与成绩归因。
