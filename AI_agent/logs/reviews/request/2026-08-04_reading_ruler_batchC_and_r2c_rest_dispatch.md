# R1 · r2c 剩三条 + 批 C（渲染 / 命名 / 像素预算）派工单（施工 = GLM · 累计式自包含）

- **日期**：2026-08-04（北京时间 09:25，**非高峰 2x**；⚠️ 14:00–18:00 是 3x，长批次避开）
- **派工方**：orchestrator · **施工席**：GLM（同席位第四轮）
- **前置状态**：HEAD `6e06ecf`（已推 origin）。全仓 **2096 passed + 10 xfailed 零红**（orchestrator 轻门复验过）。
  **批 B 已收口**（r2/r2b/r2c-1 全部落地，唯一 MAJOR 已修并经独立 neuter 证明真绑）。
- **上游**：[批 B/C 原派工单](2026-08-03_reading_ruler_r1_batchBC_dispatch.md)（**批 C 正文出处，§3 与 §4 继续有效**）·
  [r2c 派工单](2026-08-04_reading_ruler_r1_batchB_r2c_dispatch.md) ·
  [轻门 + 结转债](../verdict/2026-08-04_reading_ruler_r1_batchB_r2_orchestrator_lightgate.md) ·
  [交叉审](../verdict/2026-08-04_reading_ruler_r1_batchB_r2_crossreview_claude.md)

---

## 0. 你昨晚干得好，这轮是接着往下走

批 B 三轮（r2 / r2b / r2c）**生产码零缺陷**（Claude 侧交叉对抗审四次证伪失败，反向坐实）。
**你两次「停下上报」都被判成立，两次都改掉了 orchestrator 的题** —— 这条纪律本轮继续有效。
昨晚 05:59 你撞 5 小时额度上限（07:13 已复位），**r2c 还剩三条小活**，本单先收掉，再进批 C。

---

## 第一部分 · r2c 剩三条（全是锁强度，⛔ 不改生产码行为）

> 出处 = Claude 侧交叉审 F-3 / F-4 / F-5。**r2c-1（那条 MAJOR）你昨晚已修完并通过复验，不用再动。**

### r2c-2（MINOR）两条 geometry 锁改写后丢光了 check-id 行断言
- **位置**：`tests/test_run_stage_flow.py`（`test_R1_5_approve_geometry_uses_frozen_policy_check_headers` /
  `test_R1_5_geometry_is_approved_uses_frozen_policy_check_headers`）
- r2 派工单要的是「**头部字段 + 具体 check-id 行**」两者都断言；r2b 改写后**只剩头部字段**。
- **要求**：补回具体 check-id 行断言（形态照 `test_R1_1_flow_regression_freezes_to_reading_checks_header`），
  ⛔ 不得放宽既有断言。**neuter 后仍须恰好红这两条。**

### r2c-3（MINOR）一条恒真断言，分辨力 0
- **位置**：`tests/test_orchestrate_baseline.py:106-109`（`test_R1_5_record_baseline_marks_unfrozen_run_legacy`）
- `require_ep=False` 下 `downstream.build` 对「冻结 regression」与「legacy」**都不出现** ⇒ 该断言两边都成立、区分不了。
- **要求**：改成能分辨两者的断言（例如断言 legacy 侧的档位标记 / `source == "legacy_defaulted"` 那一维），
  ⛔ 不要断言一个双方都没有的行。

### r2c-4（MINOR）`capability_profile_not_declared` 守卫零锁
- **位置**：`src/agent/execution/run_policy_freeze.py:168-173`
- 交叉审 neuter ⇒ 摘掉后 302 passed 零红；**且该守卫可达**（`provision_run_policy(..., capability_profile=None)` 实跑会抛）。
- **要求**：补一条锁。**本条不要求走 CLI**（CLI 侧确实不可达，这是「防未来 resolver 回归」的结构守卫），
  直接调 `provision_run_policy` 即可。

**另**：`tests/test_orchestrate_baseline.py:160` 有一句注释误述「frozen tier still consumed」，**顺手改掉注释即可，不补锁**。

**第一部分交付**：续写批 B 执行日志的 `## 9. r2c` 段（`logs/reviews/execution/2026-08-03_reading_ruler_r1_batchB_glm.md`），
⛔ 别覆盖 §7 / §8。**做完停下 commit，再进第二部分。**

---

## 第二部分 · 批 C（安全交付面）

> **性质与批 B 完全不同**：批 B 改的是执行信任事务，批 C 改的是**交付面** —— 用户能不能看到产物图、
> 文件名对不对、渲染会不会把机器撑爆。**分开提交、分开审。**

### ⚠️ 先取回你自己的半截工作
批 C 的像素预算你上次留了 28 行在 `git stash`：**`batchC-wip-render-pixel-budget`**。
用 `git stash list` 找到它、`git stash show -p <ref>` 取内容（⛔ 不要 `git stash pop` 直接盖到工作树上，
先看再决定用哪几行）。

### 顺序：**O-3（最小）→ O-4（安全）→ O-1（最大）**。做不完就停下上报，不要硬塞。

### O-3 · 精确输出文件名（低成本 P0）
- **病灶**：`skills/intake_pipeline/0_reading/session_kickoff.md:51` 的通则 `<name>_view.json`
  与同文件 `:57-65` 的示例表格**自相矛盾**；真正的规则在 `view_manifest.py`，对已经以 `_view` 结尾的 stem 是 identity
  ⇒ **图名以 `_view` 结尾的 case 必踩，读图器照通则做就会被拒收**。
- **要改成唯一规范**：**只按 staging `input_inventory.json` 给出的 `expected_output_id` 写 `<expected_output_id>.json`**。
  静态表格只能作**非规范示例**，⛔ 不得再次推导名字。
- **锁 L-50**：source `foo_view.png`、inventory 的 expected 为 `foo_view` ⇒ **只接受** `foo_view.json`、
  `foo_view_view.json` **被拒**；kickoff 生成的文本引用的是 exact id。**摘掉即红**（文档再自行拼 `_view`）。

### O-4 · OCR 锚点 / 3.3 亿像素（安全 P0）
- **根因链（已完整查明，不用重查）**：`src/agent/reading/schema.py:119-129` 的 `ocr_texts` **完全 untyped**；
  `guide.md:269-272` 示例看着像 metric local anchor，而 `Dimension.anchor` 注释写的是 pixel（schema `:65-81`）
  ⇒ **坐标载体语义不统一**；validator 只查 typed `room_labels` 的 anchor（`src/validator/checks/reading.py:212-318`）、
  **不查 OCR**；renderer 把 OCR anchor 纳入画布 extent（`render_vector_to_png.py:50-77`），
  且在 `Image.new`（`:85`）之前**没有任何像素预算** ⇒ 真实产物 `1f_view/T1=[360,450]` 把约 10×20 m 的图撑成 **3.3 亿像素**。
- **本批必做（立即层）**：renderer 的画布**只由结构几何 / 显式 trusted metric bounds 决定**，
  **annotation ⛔ 不得扩张画布**；在分配之前**硬限** width / height / total pixels。
  metric annotation 按 trusted canvas bounds + 合理 margin 检查，越界 flag/block；**pixel anchor 不进入 metric transform**。
  **⛔ 绝不能「clamp 之后放行」——那会隐藏坏数据。**
- **⛔ 本批不做（登记为债）**：把 OCR schema 版本化为显式 `anchor_m` / `anchor_px`（或 `{frame, point}`），
  legacy `anchor` 在 strict 下不得猜单位。
- **锁 L-51**：10×20 m 结构 + OCR metric anchor `[360,450]` ⇒ gate 报 frame/bounds 错；
  renderer 在 `Image.new` **之前**拒绝或改用 bounded canvas，**像素预算不超限**。**摘掉即红**。
- **锁 L-52**：同一段文字分别用 `anchor_px` 与合法 `anchor_m` ⇒ pixel anchor **不改变** metric canvas；
  metric anchor 按 trusted bounds 绘制。**摘掉即红**。

### O-1 · aggregate 自动渲染（**07-08 起每轮识图零渲染，用户看不到任何产物图**）
- **病灶**：`scripts/tool_scripts/run_stage.py` 的 `_render_stage` 只 glob `0_reading/*_view.json`，
  而硬隔离的正常产物落在 `attempts/NNN/output.json`（`isolation.py:344-380`）
  ⇒ **两条布局天然错开**，于是每轮都渲不出图。
- **要改成**：由 attempt finalization / merge **共用同一个 renderer** 读取 aggregate `views`，
  把图写到 `attempts/NNN/renders/<expected_output_id>.png`，记录 **source output hash + render helper version
  + 每图状态/hash**。accepted 根目录下的别名**只能是便利副本、不能是唯一证据**。
- **渲染失败⛔不得继续伪装成「肉检材料齐全」**：对要求人工 review 的 run 应阻断 `review_complete`；
  是否阻断纯数值 gate① 可另定，但**必须留下机器可见的 failure artifact**。
- **锁 L-40**：isolation 只产出 `attempts/001/output.json`、根目录**没有** `*_view.json`
  ⇒ 生成 expected set 的 per-attempt renders，**每图 source hash / render hash 齐全**。**摘掉 flat glob 依赖即红。**
- **锁 L-41**：向 renderer 注入异常 ⇒ review status 明确为 unavailable/blocked、**不得显示 complete**。
  **摘掉 best-effort 吞错即红。**

**第二部分交付**：**新建**执行日志 `AI_agent/logs/reviews/execution/2026-08-04_reading_ruler_batchC_glm.md`
（⛔ 别写进批 B 那份）。每条含：设计 → 改动清单（文件:行）→ **neuter 自查** → 受影响子集结果 → 缺口/披露。

---

## 3. 纪律（硬的，逐条）

- **每条锁「摘掉即红、零连带」**，neuter 自查如实登记；**「全仓绿」不构成锁真绑的证据**。
- **锁走真实入口**；断言落**具体 check-id 行 / 具体产物字段**，⛔ 不得落在「返回值存在 / 总数变了 / 不是 None」。
- ⛔ **不得把 `stroke_dimension_consistency` 升为硬门**。
- ⛔ **不得原地改**历史 `_run/view_manifest.json` / RunManifest / 历史 attempt / GT。
- ⛔ **不得以「当前样例转绿」为验收**；⛔ 不得让产品内容决定考卷；
  ⛔ 不得把 N/A 一律计 miss（object-conditional 的 N/A 合法，要保留 + 机器可读原因）。
- ⛔ **不读 GT**（`case_tests/test_baseline/gt/`）；需要 fixture 自己造，⛔ 不得从 GT 拷数字。
- ⛔ **不碰** sm24 `testdata_prompt.json` 任何字节；⛔ **不 push**；⛔ 不顺手做批 D / 批 E / R1.5。
- ⛔ **不动 `AI_agent/` 下除你自己执行日志外的管理文档**。
- **做完一件存一件、每条改完即本地 commit**（`8.04_R2C_<条目>_<标签>` / `8.04_BatchC_<条目>_<标签>`）。
- 中间轮跑受影响子集；**每部分交付前跑一次全仓 `pytest -q -n 6`**（⛔ 不许 `-n auto`，⛔ 永远不许加 `-m`）。
  **基线 = 2096 passed + 10 xfailed 零红。**
- **⛔ 再遇欠规格边界，停下上报** —— 你昨晚两次都做对了。

## 4. 完工信号

第一部分：批 B 执行日志 `## 9` 段写完 + 三条各自 commit + 全仓结果。
第二部分：批 C 执行日志建好写完 + 每条 commit + 全仓结果。
**做不完就停下上报当前进度，⛔ 不要硬塞。**
