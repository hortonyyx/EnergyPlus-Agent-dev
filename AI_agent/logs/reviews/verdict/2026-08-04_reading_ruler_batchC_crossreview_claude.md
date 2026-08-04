# R1 批 C（安全交付面）+ r2c 收尾 · 交叉对抗审（Claude 侧 · Opus 档）

> **本文最终版**

- **日期**：2026-08-04
- **被审对象**：`6e06ecf` → `d0e33ef`（5 commit · 施工 = GLM · 跨家族「谁写谁不批」满足）
- **审阅席**：Claude 侧 Opus 档子代理（本批不启 GPT 侧，用户定）
- **上游**：[派工单](../request/2026-08-04_reading_ruler_batchC_and_r2c_rest_dispatch.md) ·
  [orchestrator 轻门](2026-08-04_reading_ruler_batchC_orchestrator_lightgate.md) ·
  [批 B/C 原派工单 §3/§4](../request/2026-08-03_reading_ruler_r1_batchBC_dispatch.md) ·
  [施工执行日志](../execution/2026-08-04_reading_ruler_batchC_glm.md)
- **工作方式**：破坏性探针全部在 `/tmp` 克隆（`git clone --local --no-hardlinks`，HEAD `d0e33ef`）；
  主仓库只跑只读 git（`log` / `show` / `diff`），⛔ 全程未跑 `git status`、未改主工作树、未提交、未 push、未 stash。
  唯一写入 = 本报告。

---

## 0. 总判定：**REWORK**

| 级别 | 数量 | 条目 |
|---|---|---|
| **BLOCKER** | **1** | F-1 |
| **MAJOR** | **3** | F-2 · F-3 · F-4 |
| MINOR | 3 | F-5 · F-6 · F-7 |
| NIT | 2 | NIT-1 · NIT-2 |

**一句话**：批 C 的三条实现**本身都是对的**（锁全部真绑、八处独立 neuter 零假锁、独立全量 2106 绿零红），
但 **O-1 与 O-3 都只在「硬隔离」这一条布局上修好了，另一条同样活着的布局被漏掉、且被改得比修之前更糟**
—— 这正是本批 C-1 命题要我证伪的那个形状，**证伪成功**。

**⭐ 本批最重的一条（F-1）**：O-1 把旧的 flat glob **替换掉**而不是**并存**，于是
**非隔离 flat-flow 识图路径**（= 产品 skill 里写死的**盲重读恢复路径**，`judge_rubric.md:57` +
CLI 自己打印的 `run_stage.py:2039`）现在 ——
① 渲染归零（改之前这条路径渲得出图，实测两张 PNG）；
② `render_manifest.json` 被盖上 `status="unavailable"`；
③ `cmd_approve_review` 用「at least one view failed to render」**拒绝一个完全健康的 run**。
**即：批 C 想修的「用户看不到产物图」，在恢复路径上原样复现，并额外多出一个假阴性硬门。**

**与 orchestrator 轻门的关系**：轻门的七处 neuter 台账**我逐条独立复算、全部属实**（见 §5），
轻门的结论「锁真绑、零假锁」成立。轻门漏掉的不是锁强度，而是**覆盖面** ——
七处 neuter 全部落在「隔离布局」这一条路径上，**没有任何一处去问「另一条布局呢」**。
这与批 B 那句话同型：**「修好的是机制存在，没修好的是机制在所有真实路径上都生效」**。

---

## 1. 承重命题逐条

| 命题 | 结论 |
|---|---|
| **C-1** O-1 真把「用户看得到产物图」修好了 | **⛔ 不成立**（F-1 · BLOCKER；另 F-2 = 失败可以无人发现） |
| **C-2** O-4 挡得住真实病灶且没掩盖坏数据 | **前半成立 / 后半不成立**（F-4 · MAJOR） |
| **C-3** O-3 的命名唯一规范真的唯一 | **⛔ 不成立**（F-3 · MAJOR，第二处推导已找到） |
| **C-4** 五条锁全部真绑、走真实入口、断言落具体字段 | **成立**（八处独立 neuter 零假锁；唯 L-50 无新增约束力 = F-5） |
| **C-5** r2c-3 / r2c-4 / F-2 三条收尾到位 | **成立** |
| **C-6** 施工方两项自行裁定正确 | **裁定①成立 / 裁定②不成立**（F-2） |
| **C-7** 边界合规 | **全部成立**（逐项零违规） |
| **C-8** 不变量 #6 | **两处会成为要推翻的假设**（F-7 + 判断，见 §8） |

---

## 2. C-1 · O-1 是否真把「用户看得到产物图」修好了 —— **⛔ 不成立**

### ⛔ F-1（BLOCKER）非隔离 flat-flow 路径：产物存在、渲染归零，且被**假阴性**挡在人工 review 之外

**病灶链（三处代码，逐处可查）**

1. `scripts/tool_scripts/run_stage.py:184-244` `_draw_reading` —— flat-flow 的 gate① 入口，
   glob 的是 **stage 根**的 `0_reading/*_view.json`，返回
   `out = {vj.stem: <view payload>}`（`:209-211`）。
2. `src/agent/execution/stage_runner.py:216` + `:445` —— `out_text = _to_json(output_obj)`
   原样落 `attempts/NNN/output.json` ⇒ **该文件的形状是 `{"1f_view": {...}}`，没有 `views` 外层**。
   （这不是我的推断：`src/agent/correction/window_sources.py:498-541`
   `verify_reading_stage_root_against_accepted_attempt` 的 docstring 逐字写着
   *"StageRunner archives a reading draw as one JSON object keyed by each `*_view.json` stem"*，
   并按这个形状重建字节做 hash 对账 ⇒ **下游 correction 依赖的正是这个形状**。）
3. `scripts/tool_scripts/run_stage.py:684` `_finalize_reading_renders` ——
   `views = (json.loads(out_text) or {}).get("views") or {}` ⇒ 对上面那个形状 **恒为空**
   ⇒ `view_records == []` ⇒ `:717` 的三元式判定 `status = "unavailable"`（「空 views 也算 unavailable」）。

**实跑证据（`/tmp` 克隆 · 探针 `probe_flat.py` / `probe_flat_block.py`）**

同一份输入（一张 10 m 墙的 `1f_view` + 一张 `South_view`，flat 布局 + 对应 attempt）：

```
# HEAD = d0e33ef（批 C 之后）
produced = []
render_manifest exists: True
manifest = {"source_output_hash": "605984f5…", "render_helper_version": "render_vector_to_png:v1",
            "status": "unavailable", "views": []}
pngs: []
render_status = unavailable

# HEAD = 079ce17（O-1 之前，同一份输入、同一个探针）
produced = ['/tmp/…/0_reading/1f_view_render.png', '/tmp/…/0_reading/South_view_render.png']
```

⇒ **改之前渲得出两张图，改之后一张都没有。这是 O-1 引入的回归，不是既有缺陷。**

再走真实 CLI 入口（`probe_flat_block.py`，健康 run + 已 accepted 的 manifest）：

```
1) _render_stage -> []
2) render status  -> unavailable
3) approve-review  -> BLOCKED: review blocked: 0_reading renders are unavailable for attempt 1
   (render_manifest.json status=unavailable — at least one view failed to render). …
```

⇒ **一个完全健康的 run 被硬门拒绝，理由文案还是错的**（「at least one view failed to render」——
实际是**零个 view 被尝试**）。**机器可读的 failure artifact 在这里是假的。**

**这条路径是活的，不是遗留死码 —— 三处独立佐证**

- `AI_agent/guides/new_case_guide.md:131`（换主控模型的接手手册、单一 `flow` SOP）：
  「产（见 §2.1 + 附录 A），写进 `<run>/0_reading/*_view.json`。」
- **⭐ `skills/intake_pipeline/0_reading/judge_rubric.md:57`（产品 skill，不是 dev 脚手架）**：
  盲重读子代理 *"writes/replaces the flat `0_reading/*_view.json` working copy before
  `run_stage resample … 0_reading --force` records the next attempt."*
- **⭐ `scripts/tool_scripts/run_stage.py:2039`** —— CLI 自己在 judge 打回后打印给操作者的步骤：
  *"4. Have it write/replace the flat working copy: 0_reading/*_view.json plus reading_summary.md."*

⇒ **flat-flow 就是「识图被 judge 打回之后的盲重读恢复路径」**。
换句话说：**只要一次识图被打回并重读，这条 BLOCKER 就必然触发**
—— 渲染归零 + 人工 review 永远批不过去。

**归因边界（如实登记，不夸大）**：我逐个看了仓库里最近的真实 run
（`case_tests/e2e_tests/sm24_anchor/run_2026-08-0*`），**它们全是隔离布局**
（`attempts/001/output.json`，stage 根**没有** `*_view.json`），所以 F-1 **尚未在历史 run 上发生过**。
但同时也观察到：`run_2026-08-02_sonnet_full_unsup/0_reading/` 下**有五张 `*_render.png`**
（05:14，比 attempt 晚一分钟），而 stage 根并无可 glob 的 `*_view.json`
⇒ **那批图是带外手工渲的**，与「07-08 起自动路径零渲染」的病灶陈述不矛盾，但说明
**「用户看不到任何产物图」这句话在 08-02 那轮实际上被人工绕过了**，登记以免日后归因错。

**出口建议（不替施工方设计，只给约束）**：`_finalize_reading_renders` 必须能同时消费两种形状
——`{"views": {...}}`（隔离 merge）与 `{<stem>: {...}}`（flat / 盲重读）；
且**「形状不认识」必须与「渲染失败」分成两个状态**，不得共用 `unavailable`。

---

### ⛔ F-2（MAJOR）stage 级渲染失败 = 零 failure artifact，与「历史 run」不可区分，且**不阻断 review**

`_render_stage`（`run_stage.py:771-806`）顶层保留了 `except Exception`。
逐图失败确实被 `_finalize_reading_renders` 记进 manifest（这部分是对的），
但**在写 manifest 之前**炸掉的一切（`output.json` 读不出 / 解不开、`renders/` 建不了、
manifest 写不下去、`import` 失败）会一路冒到 `:805`，被吞成 `produced` 里的一条**字符串**，
**磁盘上不留任何 artifact** ⇒ `_reading_render_status` 返回 `"missing"` ⇒ 守卫**放行**。

实跑（`probe_missing.py`，attempt 的 `output.json` 故意写坏）：

```
=== A) attempt output.json is CORRUPT (render blows up at stage level) ===
  _render_stage -> ['(render error for 0_reading: JSONDecodeError: …)']
  manifest written? False
  status -> missing
  approve-review -> OK rc= 0          ← 放行

=== B) pre-O-1 historical run (renders never attempted) ===
  status -> missing
  approve-review -> OK rc= 0          ← 同样放行、同样是 missing
```

⇒ **今天炸掉的 run 与 pre-O-1 历史 run 被压成同一个状态**，肉眼与机器都分不开。
这**违反派工单 O-1 的硬要求**：「渲染失败⛔不得继续伪装成『肉检材料齐全』……
**必须留下机器可见的 failure artifact**」。在这条路径上，failure artifact **不存在**
（只有一条转瞬即逝的字符串进 judge packet，不落盘、不进 manifest、不进 run_state）。

**顺带**：`_render_reading_attempts`（`:744-767`）一旦在中途 raise，
`produced` 整个列表连同**已经渲好的 accepted attempt 的图路径**一起丢失
（列表只在函数末尾返回）⇒ judge packet 的 `renders` 变空，尽管盘上其实有图。

---

## 3. C-2 · O-4 像素预算 —— **前半成立、后半不成立**

### ✅ 成立的部分

实跑（`probe_o4.py`，10 × 20 m 结构 + 真实病灶那种 pixel anchor `[360,450]`）：

```
A) pixel OCR anchor [360,450] on a 10x20 m plan -> rendered, canvas = (585, 1035)
B) 200 m x 20 m structure                       -> REFUSED: canvas 9135x1035 … exceeds the pixel budget
C) legit metric annotation at [12.0, 5.0]       -> canvas (585,1035)，与无标注时逐位相同
```

- **3.3 亿像素这个具体病灶确实被挡住了**：OCR anchor 不再进 extent（`render_vector_to_png.py:70-78`），
  画布回到结构几何的 585×1035。
- **超预算是 raise 不是 clamp**（`:94-102`，`CanvasBudgetExceeded`），符合「⛔ 绝不能 clamp 之后放行」。
- **合法 metric annotation 零误拒**（C 组）：metric anchor 既不扩画布也不触发拒绝
  ⇒ **我找假阳性的尝试失败了**（反向坐实，见 §7）。

### ⛔ F-4（MAJOR）派工单列为**本批必做（立即层）**的四件事只交付了两件，且净效果是**坏数据被彻底掩盖**

派工单 O-4「本批必做（立即层）」逐字四件：
① 画布只由结构几何决定 → **已做**；
② `Image.new` 前硬限 → **已做**；
③ **「metric annotation 按 trusted canvas bounds + 合理 margin 检查，越界 flag/block」** → **未做**；
④ **「pixel anchor 不进入 metric transform」** → **未做**。

- ④ 的实况：`render_vector_to_png.py:150-154` 里 OCR anchor **仍然过 `tx()` / `ty()`**，
  只是画出去被 PIL 自然裁掉。执行日志 §2「缺口/披露」自己写着
  「绘制层 OCR 仍经 `tx/ty`……未单独锁绘制层」——**披露属实，但这是必做项不是债**。
- ③ 的实况：gate① 对 OCR **零覆盖**。全仓 `grep`：
  `src/validator/checks/reading.py` 里 `ocr` 只出现 **1 次**，且是
  `:56 _ROOM_LABEL_BASES = {"label", "furniture", "ocr"}`（room-label 的 pen 基名，与 anchor 无关）；
  `ocr_texts` 在整个 `src/` 只有一处 —— `src/agent/reading/schema.py:126 ocr_texts: list`（完全 untyped）。

**⇒ 净效果**：`[360,450]` 这个明显是像素的锚点，**改之前唯一的暴露方式就是那张 3.3 亿像素的 PNG**；
O-4 把这个信号删掉了，而派工单要求同批补上的替代信号（③）没补
⇒ **现在它既不炸也不报，被完全掩盖**。这正是 C-2 后半「没有掩盖坏数据」要问的，答案是**掩盖了**。

派工单只把**一件事**明确划为「⛔ 本批不做（登记为债）」= OCR schema 版本化（`anchor_m`/`anchor_px`）；
③④ 不在豁免之列。施工方把它们写成「G-9 债」自行降级 ——
**这属于本项目反复强调的「欠规格/改范围要停下上报」，本轮没有停**
（对照：批 B 两次停下上报都被判成立并改掉了 orchestrator 的题）。

### ⚠️ F-7（MINOR）预算常数把「建筑不超过 ~182 m」烤死了（并入 C-8）

`MAX_CANVAS_SIDE_PX = 8192` 配固定 `SCALE_PX_PER_M = 45`
⇒ **任何一个方向超过 8192 / 45 ≈ 182 m 的建筑，永远渲不出来**。
上面 B 组即实例：200 m × 20 m 的板楼算出 9135 × 1035 = **9.4 M 像素，只有总预算 50 M 的五分之一**，
却仅因**单边帽**被拒。而按 O-1，被拒 ⇒ `unavailable` ⇒ **人工 review 被硬门挡住**。
⇒ 一栋合法的长条形建筑会被交付面判成「渲染失败」。详见 §8。

---

## 4. C-3 · O-3 的「唯一规范」是否唯一 —— **⛔ 不成立**

### ⛔ F-3（MAJOR）第二处推导就在生产码里，而且是**读图器实际收到的第一条指令**

`src/agent/execution/isolation.py:689-700` `_write_kickoff` 生成 staging 的 `kickoff_prompt.md`，
其 `:694` 逐字写着：

```python
"The drawings are at case_data/. Write reading outputs (per-image "
"<name>_view.json and reading_summary.md) under out/, and write CV-probe "
```

而 `spawn_command`（`isolation.py:713-732`）把这份文本**作为 `claude -p <prompt>` 的参数**直接喂给读图器
⇒ **它比 `session_kickoff.md` 更靠前、更直接**（skill 文档是「去读一下」，这份是「现在照做」）。

⇒ O-3 在 `session_kickoff.md` 里写下的
「**Do NOT** derive the output name from the source PNG by appending `_view` …… re-derive it nowhere」
与生产码同一时刻发出的 `<name>_view.json` **正面冲突**。
**O-3 的病灶（「图名以 `_view` 结尾的 case 必踩，读图器照通则做就被拒收」）在真实隔离路径上原样存在。**

**并且这一处正是派工单点名要锁的**：L-50 原文「**kickoff 生成的文本引用的是 exact id**。
**摘掉即红**（文档再自行拼 `_view`）」。交付的 L-50
（`tests/test_isolation.py:2409-2431`）**对 kickoff 文本零断言**，只测 merge 端拒收
⇒ 这条要求既没实现、也没有锁会因此变红。

### ⚠️ F-5（MINOR）L-50 对既有约束力零增量

独立 neuter（N-E，见 §5）：摘掉 `isolation.py:602-606` 的 `extra` 检查 ⇒ 红 2 条 ——
新的 `test_merge_per_image_view_suffix_misapplied_is_rejected` **与既有的**
`test_merge_per_image_extra_is_rejected`。两条共用同一个 hook。
⇒ **把 L-50 整条删掉，该机制依然被既有测试锁着**：L-50 只是同一机制的第二个夹具形状，
**没有为 O-3 真正新增的行为（命名规范）建立任何锁**。
执行日志把这记为「同源 extra hook、非连带」是准确的，但它同时也意味着**零增量约束力**，
这一层执行日志没说。

### NIT-1（卫生）新正文仍在散文里复述推导

`session_kickoff.md:54-57` 一边说「不要从 PNG 名推导」，一边又把转换规则完整讲了一遍
（「stem 已以 `_view` 结尾 ⇒ 就是它自己；`supp_plan` ⇒ `supp_plan_view`」）。
派工单要求静态表格「**⛔ 不得再次推导名字**」。正文虽以「re-derive it nowhere」收尾，
但一个照散文办事的读图器**拿到的仍是一条可执行的推导规则**。

---

## 5. C-4 · 逐锁 neuter 台账（**全部由我独立复跑**）

**方法**：`/tmp` 克隆（HEAD `d0e33ef`）· 每次只改**一处**（精确单行/单块替换，脚本落盘可复核）
· 跑受影响文件 · `git checkout -- .` 复原并复核 `git diff` 为空。
⚠️ **环境坑（登记）**：本容器 `/opt/venv` 有一条 editable `.pth` 指向 `/workspaces/EnergyPlus-Agent-dev`
⇒ 在克隆里跑 pytest 若不加 `PYTHONPATH=$PWD`，`src.*` 会解析回**主仓库**、neuter 形同没做。
**本台账全部在 `PYTHONPATH=$PWD` 下跑，并已用 `__file__` 打印验证解析到克隆**：

```
isolation: /tmp/.../probe/src/agent/execution/isolation.py
run_stage: /tmp/.../probe/scripts/tool_scripts/run_stage.py
```

| # | 摘掉哪一处实现 | 红了哪几条 | 连带 | 走真实入口？ | 判定 |
|---|---|---|---|---|---|
| **N-A** | `run_stage.py:757` `_render_reading_attempts` 提前 `return []`（= 回到 flat glob 时代） | `test_L40_isolation_aggregate_renders_per_attempt_with_hashes`、`test_L40_render_stage_reading_branch_reads_attempts_not_stage_root` | 零（3 passed） | ✅ L-40b 经真 `_render_stage("0_reading", …)` | ✅ 真绑 |
| **N-B** | `run_stage.py:717` status 三元式 → 恒 `"complete"` | `test_L41_render_failure_records_unavailable_not_complete` | 零（4 passed） | ✅ 真 `_finalize_reading_renders` + monkeypatch 真 `rv.render` 抛 | ✅ 真绑 |
| **N-C** | `run_stage.py:741` `_reading_render_status` → 恒 `"complete"` | 上条 + `test_L41_failed_render_blocks_review_approval` | 零（3 passed，同源守卫失明） | ✅ | ✅ 真绑 |
| **N-D** | `run_stage.py:2237` `cmd_approve_review` 守卫 `if False and …` | `test_L41_failed_render_blocks_review_approval` | 零（4 passed） | ✅ 真 CLI 入口 `cmd_approve_review` | ✅ 真绑 |
| **N-E** | `isolation.py:603` `if extra:` → `if False and extra:` | `test_merge_per_image_view_suffix_misapplied_is_rejected`（L-50）+ **既有** `test_merge_per_image_extra_is_rejected` | 零（203 passed） | ✅ 真 `merge_isolated_output` | ⚠️ 真绑但**零增量**（F-5） |
| **N-F** | `render_vector_to_png._collect_points` 加回 OCR anchor（= O-4 病灶原状） | `test_L51_pixel_ocr_anchor_does_not_blow_up_canvas`、`test_L52_pixel_vs_metric_ocr_anchor_canvas_unchanged` | 零（companion 绿） | ✅ 真 `rv.render` | ✅ 真绑 |
| **N-G** | 摘掉 `render_vector_to_png.py:95` 的预算 raise | `test_L51_over_budget_structural_canvas_is_refused_not_clamped` | 零（2 passed） | ✅ | ✅ 真绑（**旁证**：该轮 2 s → **56 s** 且 xdist worker `gw2` 直接 crash —— 它真的去分配那张巨图了） |
| **N-H** | `run_policy_freeze.py:168` `capability_profile_not_declared` 守卫短路（r2c-4） | `test_R1_5_new_run_without_capability_profile_fails_closed` | 零（35 passed + 1 xfailed） | ✅ 直调真 `provision_run_policy` | ✅ 真绑 |

**⇒ 八处 neuter 全部「摘掉即红」，零假锁，与 orchestrator 轻门台账逐条吻合。**
**断言质量**：L-40/L-41 落 `render_manifest.json` 的具体字段（`status` / `source_output_hash` /
`render_hash == hash_file(png)`）+ png 实存 + `SystemExit` 消息串；L-50 落 merge 的 `ValueError("unexpected")`；
r2c-4 落 `capability_profile_not_declared` 具体错误串。
**⛔ 没有任何一条落在「返回值存在 / 不是 None / 总数变了」上。**

### ⚠️ F-6（MINOR）L-41c 的 docstring 声称锁住了 `missing` 分支，实际没有 —— 「假 docstring」同族第五次

`tests/test_reading_renders.py:185-190` 的 docstring 写着：

> "This keeps the guard from over-blocking healthy runs **and pins the 'missing' branch
> (pre-O-1 runs stay approvable)**."

但该测试 `:206` 调 `rs._finalize_reading_renders(adir)` **写出的是 `complete` manifest**，
`:207` 也断言 `== "complete"` ⇒ **它从头到尾没有走过 `missing` 分支**。
把 `cmd_approve_review` 里 `== "unavailable"` 改成 `!= "complete"`（即让 `missing` 也阻断，
= 破坏「pre-O-1 可批」这条向后兼容承诺）⇒ **全套 5 条锁依然全绿**。

⇒ 施工方自己的裁定②（「`missing` 不阻断」）**是本批唯一一条零锁的行为承诺**，
而 docstring 声称它被锁住了。这与项目已记录四次的
「声称在守其实没守 / 文档不可能验证别人有没有遵守自己」**完全同族**。
（与 F-2 合看：`missing` 这一态既没锁、语义又超载，是 O-1 里最脆的一块。）

### NIT-2 L-51 四条断言里三条是自证的

`tests/test_render_vector_to_png.py:50-52` 的三条（`< MAX_CANVAS_PIXELS`、两条 `<= MAX_CANVAS_SIDE_PX`）
在预算守卫存在的前提下**恒真** —— 一旦超限 `rv.render` 已经 raise、测试在 `:48` 就错了。
真正有分辨力的是 `:54 assert img.size[0] < 2000`。不影响锁成立（N-F 实测会红），仅记卫生。

---

## 6. C-5 / C-6 / C-7

### C-5 · r2c-3 / r2c-4 / F-2 —— **成立**

- **r2c-3**（`tests/test_orchestrate_baseline.py:169-192`）：恒真断言 `not any(downstream.build)` 已删除。
  派工单要的是「改成能分辨两者的断言」，施工方选择**删除 + 依赖同函数既有断言**。
  我独立核过留下的四条**确实有分辨力**：测试以 `run_profile="regression"` 调用，却断言
  `source == "legacy_defaulted"` / `legacy_defaulted is True` / `run_profile == "exploratory"` /
  `capability_profile == "rectangular"` —— 冻结 regression 侧四条全反 ⇒ 互斥、可区分。**分辨力 0 的问题已消除。**
- **r2c-4**：新锁走**真实入口** `provision_run_policy(run, run_profile="regression", capability_profile=None)`，
  断言落具体错误串。N-H 实测摘掉守卫恰好红这一条、零连带（此前交叉审实测为零锁，本轮已补上）。**成立。**
- **F-2（注释误述）**：`:266-273` 的 "frozen tier still consumed" 已改为「冻结记录未被篡改」，
  与实况一致（`effective_run_policy` 本就不读 context）。**成立。**

### C-6 · 施工方两项自行裁定 —— **独立挑战结果：①成立 / ②不成立**

**裁定①「渲染失败不阻断纯数值 gate①、只阻断人工 review 批准」= 成立，且我为它补了一条 orchestrator 没查的证据。**
我去找**绕过守卫的第二个入口**：全仓 `grep` 显示 `record_review` / `mark_review_approved`
在 `src/` + `scripts/` 里**唯一的调用点就是 `run_stage.py:2244` / `:2252`，都在 `cmd_approve_review` 内**
（其余命中全是 `__init__.py` 的 re-export 与 `__all__`）。
⇒ **人工 review 批准只有这一道门，守卫扣在门上是完整的。证伪失败 ⇒ 反向坐实。**
理由层面也认同：渲染是交付面，不该污染 gate① 的数值判定。

**裁定②「`missing` 不阻断、只有 `unavailable` 阻断」= ⛔ 不成立（按其陈述的理由）。**
施工方与轻门都把 `missing` 等同于「pre-O-1 的历史 run」。**实测不是**（F-2）：
`missing` 同时吸收了「**今天的 run、渲染试过了、在写 manifest 之前炸掉**」这一类。
两态**在语义上确实可区分**（`missing` ≠ `complete`，历史 run 没被伪装成完成 —— 这一点轻门说对了），
但**三种现实被压进两个状态**，其中「炸掉」那一种既无 artifact 也不阻断，
**正好落在派工单「必须留下机器可见的 failure artifact」的反面**。
⇒ 向后兼容的目标是对的，实现方式（用「有没有 manifest」当代理变量）不足以承载它。
出口方向：把「本轮尝试过渲染」这件事本身落盘（哪怕是一个空壳 manifest + `status="error"`），
让 `missing` 回到只表示「从未尝试」。

### C-7 · 边界合规 —— **逐条成立，零违规**

| 项 | 证据 | 结论 |
|---|---|---|
| 未 push | `git log --oneline -1 origin/6.15_ValidationArchM0toM4` = `6e06ecf`（HEAD `d0e33ef`，5 commit 未推） | ✅ |
| `gt/**` + sm24 `testdata_prompt.json` 零字节 | `git diff --name-only 6e06ecf d0e33ef -- 'case_tests/test_baseline/gt/**' '**/testdata_prompt.json'` ⇒ **0 行** | ✅ |
| 未读 GT | 两个新测试文件 `grep gt/load_gt/test_baseline` ⇒ 零命中；fixture 全为自造合成几何 | ✅ |
| 未原地改历史 manifest / attempt | 全 diff 无 `run_manifest` / `view_manifest.json` / `attempts/` 命中 | ✅ |
| `stroke_dimension_consistency` 未升硬门 | 全 diff `grep` ⇒ 零命中 | ✅ |
| 未做批 D / 批 E / R1.5 | 改动面仅 O-1/O-3/O-4 + r2c，无越界 | ✅ |
| 未动 `AI_agent/` 下别人的管理文档 | 全 diff 只含施工方自己两份执行日志（`2026-08-03_…batchB_glm.md` §9 续写 + `2026-08-04_…batchC_glm.md` 新建） | ✅ |
| （工作树里 CLAUDE.md / decision_log / plan / batchB lightgate 的未提交改动） | 按派工说明属 **orchestrator 自己的**，**未记到施工方头上** | — |

改动面共 9 文件：2 份执行日志 + `render_vector_to_png.py` + `run_stage.py` + `session_kickoff.md` + 4 个测试文件。

---

## 7. ⭐ 我证伪失败的尝试（反向坐实，价值不低于发现缺陷）

1. **找 approve-review 守卫的旁路** —— 全仓只有 `cmd_approve_review` 调 `record_review`/`mark_review_approved`
   ⇒ **裁定① 的守卫覆盖是完整的**。
2. **找假锁** —— 八处独立 neuter 全部恰好红其目标、零连带
   ⇒ **L-40a/b、L-41a/b/c、L-51×2、L-52、L-50（机制层）、r2c-4 无一是假锁**，与轻门台账逐条吻合。
3. **找 O-4 的假阳性（合法 metric annotation 被误拒）** —— 构造落在结构范围外的合法 metric anchor
   （`[12.0, 5.0]` on a 10×20 m plan）⇒ 画布与无标注时**逐位相同**、不拒绝、不报错
   ⇒ **误拒不存在**（代价是该标注被静默裁出画面，见 §8 判断）。
4. **找 O-1 对 `1_correction` 渲染的连带破坏** —— `_render_stage` 的 `1_correction` 分支
   在 diff 里逐字未动，独立全量 2106 绿 ⇒ **无连带**。
5. **找 r2c-3 删断言之后测试是否变空壳** —— 留下的四条断言经独立复核**确实互斥可区分** ⇒ **删得对**。
6. **找 `gt` / sm24 受保护件 / 别人的管理文档被碰** —— 零命中。

---

## 8. C-8 · 不变量 #6（复杂体量可扩展性）—— 两处会成为要推翻的假设

**只给判断，不给设计（按派工要求）。**

1. **⛔「渲染只从 attempts 读」这条假设已经在今天就被证伪了，不用等复杂体量。**
   F-1 就是它的第一张脸：代码把「硬隔离」当成了**唯一**布局，而仓库里同时活着第二种
   （flat / 盲重读）。**这不是「以后长不到复杂体量」的问题，是「现在就漏了一条」的问题。**
   往前看更明显：多 attempt / 多 case / 未来别的 reading 产出通道（如 R1.5 的像素锚点产物）
   都会再增加形状。**判断：`_finalize_reading_renders` 必须以「views 提取器」为接缝，
   而不是把 `.get("views")` 烤死在函数体里。**

2. **⛔ `MAX_CANVAS_SIDE_PX` + 固定 `SCALE_PX_PER_M` 把「建筑单边 ≤ ~182 m」烤死了。**
   这正是不变量 #6 点名要防的那类「纯只适用当前情况的简化假设」：
   现在的 case 是 10 × 20 m，182 m 的天花板看不见；
   一到长条板楼 / 退台的展开立面 / 中庭剖面 / 总图，单边帽先于总像素帽触发
   （实测 200 × 20 m ⇒ 9.4 M 像素、只占总预算 1/5，仍被拒）。
   **且拒绝的后果被 O-1 放大**：`CanvasBudgetExceeded` ⇒ `unavailable` ⇒ 人工 review 被硬门挡死
   ⇒ **一栋合法建筑会被交付面判成「渲染失败」**。
   **判断：预算必须表达成「内容是否荒谬」，不能表达成「像素是否超」**——
   固定 px/m 下这两件事是同一个数，正是烤死点所在。（⛔ 仍不得改成 clamp。）

3. **`render_manifest.json` 的形状本身：可扩展性尚可，但缺版本位。**
   `{source_output_hash, render_helper_version, status, views:[{expected_output_id, status, render_hash, error}]}`
   —— per-attempt 归档、按 `expected_output_id` 索引，多 attempt / 多 case 天然分文件，**这部分是对的**。
   两处窄：① 每个 view 恒定一张图（`render_hash` 是标量），
   挑空/中庭/多层复合视图要出多张时得改形状；② **manifest 自己没有 `schema_version`**，
   `render_helper_version` 管的是渲染器不是 manifest 契约 ⇒ 将来形状变了，
   老 manifest 读起来会静默错位而不是响亮拒绝。**判断：不是要推翻的假设，但应在下次动它时补版本位。**

4. **（观察，非缺陷）** metric annotation 现在不再扩画布 ⇒ 落在结构范围外的合法标注会被**静默裁出画面**。
   当前 case 的房间标注都在墙内，无感；退台/中庭那种「标注在轮廓之外」的画法会开始丢东西。
   与 F-4 的 ③ 是同一个出口（trusted bounds + margin 检查）。

---

## 9. 给 orchestrator 的出口清单（按优先级）

1. **F-1（BLOCKER）** —— `_finalize_reading_renders` 必须认 flat 形状；
   「形状不认识」与「渲染失败」必须分状态，⛔ 不得共用 `unavailable`。
   **配锁**：flat 布局（stage 根 `*_view.json` + `{stem: view}` 形状的 attempt）走真 `_render_stage`
   ⇒ 出图 + `status="complete"` + `cmd_approve_review` 放行；摘掉即红。
2. **F-3（MAJOR）** —— `isolation.py:694` 的 `<name>_view.json` 改成按 `input_inventory.json` 的
   `expected_output_id`；**并补上派工单 L-50 原本就要的那条锁**（kickoff 生成文本引用 exact id，摘掉即红）。
3. **F-2（MAJOR）** —— stage 级失败必须落盘 failure artifact；`missing` 回归为「从未尝试」。
4. **F-4（MAJOR）** —— ③ metric annotation 的 trusted-bounds 检查、④ pixel anchor 不进 metric transform，
   二者是派工单的**本批必做**项，需 orchestrator 明确裁定：补做，还是正式改判为债（并说明为何可延）。
5. **F-5 / F-6 / F-7 / NIT-1 / NIT-2** —— 见各节，均非阻断。

---

## 10. 独立全量跑测（尾部原文）

**环境说明（如实登记）**：本容器 `/opt/venv` 有 editable `.pth` 指向主仓库
⇒ 直接在克隆里跑会解析回主仓库；且用 `git clone --local` 得到的克隆**缺 gitignored 的活输入**
（首次跑出 6 红，其中 4 条纯属缺件）。
故最终跑法 = **对主工作树做完整副本（含未跟踪文件）+ `PYTHONPATH` 钉死副本**，
⛔ 未在主工作树跑测、未改主工作树。命令：`pytest -q -n 4`（⛔ 无 `-m` 过滤）。

```
2106 passed, 10 xfailed, 177 warnings in 344.85s (0:05:44)
```

**⇒ 与 orchestrator 轻门的 2106 passed + 10 xfailed 逐字一致，零红。**
`tests/test_zone_agent.py::test_zone_agent_creates_two_zones`（真跑 OpenAI、可能网络红）本轮通过，
与本批无关、未记账。

**⚠️ 中间过程如实登记**：第一次尝试用 `git clone --local` 跑出 `6 failed`
（`test_checks_reading_correction` / `test_gt_from_dxf` / `test_inspect_dxf` / `test_reading_score` /
`test_validation_run_baseline` / `test_zone_agent`），第二次用完整副本但未钉 `PYTHONPATH` 跑出 `2 failed`
（`test_gt_from_dxf` / `test_inspect_dxf`，根因 = `gt_vg_config_path_forbidden` 的仓库根解析回主仓库）。
**这两轮结果作废、不构成对本批的任何指控**，仅登记以说明最终数字的取得过程。
