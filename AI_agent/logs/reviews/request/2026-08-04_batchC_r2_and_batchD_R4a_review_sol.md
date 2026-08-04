# 批 C r2 + 批 D/R4-a · 交叉对抗审阅单（审 = sol · GPT 侧）

- **日期**：2026-08-04 · **派工方**：orchestrator · **审阅席**：**sol，effort = max**（用户 08-04 指定）
- **施工方 = Claude 侧**（批 C r2 接手 + 批 D/R4-a）⇒ **「谁写谁不批」满足，跨家族**
- **性质**：**对抗审**。任务不是确认它做了，而是**尽力证伪它真的做到了**。
- **基线**：orchestrator 独立全量 `pytest -q -n 6` ⇒ **2148 passed + 10 xfailed 零红**（退出码 0）

---

## 0. 背景（一句话）

reading 的判卷尺子与交付面坏了三周多没人发现，因为**两个观测通道同时瞎了**：渲染断链（人看不到产物图）
+ gate① 分辨力为 0（92.1 % 与 9.0 % 的产物同为 0 阻断）。批 A/B/C 修尺子与交付面，批 D 恢复判卷图，R4-a 建成绩分账。
**⛔ 三批全绿之前，本项目不得发布任何识图分数或「识图变好/变坏」的结论** —— **本次审阅是解除条件之一**。

## 1. 被审对象

**A. 批 C r2**（`58f9179` → `f7cc1ff`，4 commit）
- `32db683` NIT：`MAX_CANVAS_SIDE_PX` 既当像素上限又当**米**上限的单位双关 ⇒ 拆出 `MAX_STRUCTURAL_SIDE_M` + 补锁
- `7de68cb` **X-1 + X-2**（两条 MAJOR，见 §3）
- `066fff4` X-3：`_fit_scale` 的 `total_fit` 项此前零锁 ⇒ 补锁
- `f7cc1ff` X-5：render manifest 的 error surface / 损坏即放行 ⇒ 补锁

**B. 批 D + R4-a**（`794b47a` / `8336bd5` / `b8ff69f`，经两个 merge 落主线）
- **R4-a**：`src/agent/execution/reading_mode.py`（新模块）+ `run_config.yaml` 可选 `reading_mode:` 段
  + `flow --record` 处 fail-closed；**成绩分账**
- **批 D**：`render_typed_grade()` 恢复六 panel（两层平面 + 四立面）+ 图例；缺失立面画显式占位

## 2. 上游（冲突处以裁定为准）

| 文件 | 作用 |
|---|---|
| `AI_agent/logs/reviews/request/2026-08-04_batchC_r2_dispatch.md` | 批 C r2 派工单（X-1/X-2 要求 + X-2 的**骨架**） |
| `AI_agent/logs/reviews/verdict/2026-08-04_reading_ruler_batchC_r1_crossreview_claude.md` | 上一轮交叉审（X-1…X-5 原始证据） |
| `AI_agent/logs/reviews/request/2026-08-04_batchD_and_R4a_dispatch.md` | 批 D/R4-a 派工单 |
| `AI_agent/decision_log.md` **§5.14** | **「什么值得被冻结」判据（用户拍板）** —— X-2 的骨架即出自此 |
| `AI_agent/CLAUDE.md` §1.5 | 不变量，尤其 **#4 gt 铁律**、**#6 复杂度可扩展性**、**#7 成绩记账口径** |

## 3. 承重命题（逐条给 成立 / 不成立 / 无法判定 + 证据）

> 证据 = 文件:行 + 你实际跑的命令与输出摘录。**「读代码看起来没问题」不是证据。**

### S-1（最高权重）X-2 的「可信画幅」真的无法被被测方影响
实现声称：画幅**只**取自 `case_data` 源图真实像素尺寸 + 已冻结、经 R1-6 指纹核对的 `image_sha256`；
产品自己的 `strokes` / `dimensions` / 任何 `extra` 字段（`schema.py` 是 `extra="allow"`）**一概不看**。
- **要你证伪的形式**：**找出任何一条产品可控的输入，使可信画幅变大 / 使越界检查不再阻断。**
  找到一条即 S-1 不成立。注意 `_image_bounds` 保留了「无可信来源时回落产品自算」的降级路径 ——
  **请重点攻这条降级路径能否被产品自己触发**（例如让 manifest 查不到、stem 对不上、指纹不匹配）。

### S-2 X-1 真的补上了「像素化尺寸端点」的探测
- **复现载荷**（orchestrator 已实跑）：`{"strokes":[{"geometry":{"kind":"line","p1":[0,0],"p2":[10,0]}},…],
  "dimensions":[{"from":[360,450],"to":[365,450]}]}` —— 在 `d0e33ef` 上渲染器 raise
  `canvas 16560x20385 (337575600 px)`；在 `57d47ea` 上**静默渲出 6373×7845**。
- **要你证伪的形式**：**找一种坏坐标形态仍然零信号**（既不 raise、gate① 也不报）。
  另核：**合法产物有没有被误伤**（假阳性）。

### S-3 R4-a 的分账不能被绕过、也不能误伤历史
口径**唯一权威 = CLAUDE.md §1.5 #7**：**两条正式 lane（`autonomous` / `controlled`）
+ 一个 dev 期职能（tool-invention，⛔ 不是第三条 lane）**。
- **核**：新 run 缺 `reading_mode` 是否**真的 fail-closed**（⛔ 不得静默按 autonomous 记）；
  历史 run 是否标 `legacy_unknown` 且**不冒充任何 lane**；`dev_function=true` 是否在报告里**显式**标「不作为正式成绩」。
- **要你证伪的形式**：构造一条路径，使某轮成绩**被记成 autonomous 而实际有 agent 在场**。

### S-4 批 D 的判卷图真的能让人看出立面对错
- **核**：六 panel（两层平面 + 四立面）+ 图例是否都在；缺失立面是否**显式占位**（⛔ 不得静默省略 ——
  省略会让「漏画」看起来像「没考」）；标签是否仍互压；**是否读了产品的 mirror/local-x 声明**（边界：绝不能读）。

### S-5 全部新锁真绑、走真实路径、断言落具体字段
orchestrator 已独立 neuter 验过 X-1（4 红）与 X-2（1 红，覆盖三种撑大手法），**请独立复跑并找我漏的**；
**⭐ 重点找假锁**（摘掉实现仍绿 / 断言落在「返回值存在 / 总数变了」）。

### S-6 边界合规
未 push · `gt/**` 与 sm24 `testdata_prompt.json` 零字节 · 未读 GT · 未原地改历史 manifest/attempt ·
`stroke_dimension_consistency` 未升硬门 · 未做 R1.5/R2。
⚠️ 工作树里 `AI_agent/` 的未提交改动**是 orchestrator 的**，别记到施工方头上。

### S-7 不变量 #6（复杂度可扩展性）
`reading_mode` schema、六 panel 布局、可信画幅的来源假设，在**非方形 / 退台 / 挑空 / 中庭**
与多 attempt / 多 case 场景下会不会成为要推翻的假设？**只要判断，不要求设计。**

## 4. 已知失效模式（请当作清单来找）

1. **「锁绿 ≠ 锁真绑」**（本项目栽过四次）：断言落在「返回值存在 / 不是 None / 总数变了」等于没断言。
2. **「只在一条路径上修好了」**（本轮批 C 的 BLOCKER 与上轮同形）：**每条锁要走会踩到该缺陷的真实路径**。
3. **「移走症状没补检测」**（X-1 即此）：把爆炸信号消掉却没补探测器 ⇒ 坏数据比修之前更难发现。
4. **「考生自己填的字段决定这道题考不考」**（X-2 即此）。
5. **「声称在守其实没守」**（已第 7 次）：docstring / 注释声称的保护与实际触发条件不一致。
6. ⚠️ **`cmd 2>&1 | tail` 会把退出码换成 `tail` 的 0** —— 上一轮审阅席差点因此在**错误的克隆**上做完整轮 neuter。
   要判成败用 `cmd > log 2>&1; echo $?`。

## 5. 你可以做 / 不可以做

- ✅ 读全仓源码/测试/文档与 git 历史；跑测试；**破坏性探针只在 `/tmp` 克隆里做**
  （`git clone --local --no-hardlinks`；⚠️ **克隆里必须 `PYTHONPATH=$PWD`**，否则 editable `.pth` 解析回主仓 = 等于没做）。
- ⚠️ 克隆基线本身有 ~1–6 条环境红（缺未跟踪输入 / 需 OpenAI 网络）⇒ **先跑干净基线做对照**，别记成 neuter 结果。
- ⛔ 不改主工作树、不提交、不 push；⛔ 主仓库不要跑 `git status`；⛔ 不读 GT 答案数字。
- 跑测 `pytest -q -n 4`，⛔ 不许 `-n auto`、⛔ 永远不许加 `-m`。

## 6. 交付

报告落 `AI_agent/logs/reviews/verdict/2026-08-04_batchC_r2_and_batchD_R4a_review_sol.md`：
总判定（APPROVE / APPROVE-WITH-CHANGES / REWORK + 各级计数）· S-1…S-7 逐条 + 证据 ·
**逐锁 neuter 台账** · 清单外自主发现 · **证伪失败的尝试也要写**（反向坐实，价值不低于发现缺陷）· 独立全量尾部原文 + 退出码。

**orchestrator 轻门 = 独立全量 + 亲核 diff + 独立复跑 neuter，是唯一权威门；你的报告不是终裁，但 BLOCKER 一律先信。**
