# F-2c · orchestrator 裁定 + 派工：隔离产物打不通 `0_reading → 1_correction` 的最后一堵墙

- **日期**：2026-08-05
- **缘起**：施工席（GLM）在 `fb78e74` 交付后**停下上报**：F-2a/F-2b 做完，
  隔离路径**仍然**走不到 correction，死在
  `src/agent/correction/window_sources.py:498 verify_reading_stage_root_against_accepted_attempt`
  （实跑复现 `source_identity_invalid / accepted_attempt_mismatch`）。
  它**没有自行扩范围**（会牵动渲染契约与「隔离产物权威来源」口径），请 orchestrator 裁定。**做得对。**

---

## 1. 事实（orchestrator 已独立读码核实）

该函数的作用是**防「验收之后被掉包」**：把 `<run>/0_reading/` 下的**扁平** `*_view.json` 重建成
`{stem: json}`、算 `hash_text(json.dumps(current, indent=2))`，与 accepted 记录的 `output_hash` 比对。

隔离路径有**两处形状对不上**：

| # | 对不上的地方 |
|---|---|
| ① | **扁平镜像根本不存在** —— merge 只往 `attempts/NNN/output.json` 写 ⇒ 重建出 `{}` ⇒ 哈希必不等 |
| ② | 即便存在，accepted 的 `output.json` 是**信封** `{"views": {…}}`，而重建出来的是**扁平** `{stem: …}` ⇒ 字节仍不等 |

**⚠️ 同一个形状差还有第三个受害者**（orchestrator 昨夜实跑撞到）：
`flow` 找不到扁平 `*_view.json` ⇒ 判 `reading.present` 失败 ⇒ **凭空造出一条 `{}` 空 attempt**。

## 2. 裁定（口径，施工方按此做，⛔ 不许自行改口径）

**要修的是「产物没落到该落的地方」，不是「把门放松」。**

- ⛔ **否决**「让校验器接受缺失的扁平镜像」或「隔离路径跳过该校验」——
  那等于为隔离路径开一条无防掉包的旁路，且会再造一条形状分支（本项目已多次栽在「第二把尺子」上）。
- ✅ **采纳**：**merge 落盘时把扁平镜像一并写出来**，让隔离路径与扁平路径在 stage 根**看起来完全一样**。
  下游（correction / 渲染 / `reading.present` / 判卷）**一律不需要知道产物是不是隔离来的**。

### 具体两条

**F-2c-1 · merge 写扁平镜像**
`merge_isolated_output` 在写完 `attempts/NNN/` 之后，把每个视图另写一份
`<run>/0_reading/<stem>.json`（内容 = 该视图对象本身，与扁平流一致），
`reading_summary.md` 已由 F-2a 搬运、保持不变。
**镜像必须与 accepted 产物同源同内容**（从同一份已校验 payload 派生，⛔ 不许二次解析源文件）。

**F-2c-2 · 校验器按 accepted 的契约形状重建，而不是写死扁平**
`verify_reading_stage_root_against_accepted_attempt` 重建 `current` 之后，
**用 accepted 产物自己的契约决定要不要套信封**（复用 `identify_reading_contract`，
⛔ 不许新写一个形状判定），再比 canonical 文本哈希。
⇒ 扁平 run 逐字节不变；隔离 run 的镜像重建后与信封 accepted **精确相等**。

## 3. 锁

1. **端到端锁（最重要）**：构造一个「隔离 merge 之后」的 run，断言
   `verify_reading_stage_root_against_accepted_attempt` **通过**；
   摘掉 F-2c-1 的镜像写出 ⇒ 该锁必红。
2. **防掉包锁不许退化**：镜像写好之后，**改其中一个视图的一个坐标** ⇒ 校验器**必须仍然拒绝**
   （这是该函数存在的唯一理由，⛔ 不能因为加了镜像就变成恒真）。
3. **扁平路径零变化**：既有扁平 run 的重建字节与 accepted 哈希逐字相等（回归锁）。
4. 顺带核一下：`reading.present` / `_render_stage` 在有镜像之后是否还会造空 attempt；
   若仍会，**在简报里报告**（⛔ 本单不要顺手改，那是另一条）。
5. 自己跑 neuter，红了哪几条、有没有连带，原样进简报；全仓三数字。

## 4. 交付 / 边界

- commit（`08.05_<英文标签>`，⛔ 不 push，⛔ 只 add 自己改的文件）；
  简报 `AI_agent/logs/reviews/execution/2026-08-05_f2c_glm.md`。
- ⛔ 不碰识图侧、gt、判卷语义、typed v3。
- 排在 F-4 之后做。有异议停下上报。
