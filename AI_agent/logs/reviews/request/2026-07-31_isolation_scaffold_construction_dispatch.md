# 派工单 · 硬隔离识图脚手架修复批（F-1 / F-2 / F-4 / F-5）

> 主控 Opus 5 · 2026-07-31 · 收件人 = GLM-5.2（执行档施工）
> 审阅方 = sol（GPT 侧顶档，升一档交叉对抗审）· 主控轻门
>
> **本文给死骨架。** 骨架内的实现细节归你；骨架本身**不许自行改动** —— 觉得骨架有错，
> **停下上报**，不要自己改了再交（这是本项目认可的正面样板，见 §6）。

---

## 1. 背景

2026-07-30 sm24 端到端跑测第一次尝试。硬隔离识图机制（2026-07-08 落地）**第一次在真实 case 上跑**，
撞出四个脚手架缺陷。同轮识图质量从 2026-07-07 同模型同工具的 **8/8 满分掉到 1/8**
（GT 八道隔墙 · 容差 0.30 m），**判为机制退化、非模型能力**。本批修的就是嫌疑机制。

已实证的历史结论：**脚手架退化 = 识图退化的主因，且可恢复**（2026-06-25）。
所以本批不是「体验优化」，是识图质量的直接杠杆。

复验轮会在本批修完后重跑识图并用同一把尺子量 —— **你的交付质量直接决定那个数字**。

---

## 2. 现状事实（主控已逐条读码复核，可直接采信）

| 编号 | 事实 | 落点 |
|---|---|---|
| A | `session_kickoff.md:13-14` 明令「Read all three … then follow the worked-example plan JSON's style」，并给出仓库内路径 `case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json` = **必读输入** | `skills/intake_pipeline/0_reading/session_kickoff.md` |
| B | build 对该文件**零处理**（`_copy_reading_skill` 只拷 skill 目录） ⇒ 不进 staging | `src/agent/execution/isolation.py:467-477` |
| C | `guard.py` 的 `DENY_TOKENS` 含 `case_tests` ⇒ 子代理按原路径读**必被拒** | `isolation_templates/guard.py:18-28` |
| D | ⇒ 子代理被自己的 kickoff 指向一个隔离墙外、且必被守卫拦下的文件 | — |
| E | `_lexical_check` 对**整个序列化 tool input** 做词法扫描，Write/Edit 的 `content` 也在内 | `guard.py:77-88` + `:184-189` |
| F | 活体后果：子代理写必交产物 `reading_summary.md` 时用「约等号 ~」被拒 **三次**、该文件最终没写出来；写立面 JSON 时 **`grade line`（室外地坪线）** 被禁词 `grade` 误伤 | 07-30 access_log |
| G | 同族被拦（全是正常写法）：`python -c` 内分号、`> /dev/null`、管道、三点省略号 | — |
| H | 第一轮 8 次拒绝里 **7 次是与守卫搏斗**、零安全价值 | 07-30 access_log |
| I | `evidence_dir` = `Path(out_dir)/"cv_evidence"/<stem>`，工具**自己**追加两级 + label 一级；手册读起来像要传完整路径 ⇒ 照抄产生套娃 `.../prescan/cv_evidence/1f_view/prescan/`，且套娃件**不会**进 staging（拷贝守卫只认 `run_*/0_reading/cv_evidence/<stem>/prescan/**`）| `src/agent/reading/cv_toolbox/sidecar.py:23-24` + `isolation.py:497-509` |
| J | `merge_isolated_output` 硬要求单一聚合件 `{"views": {<expected_output_id>: <ReadingView>}}`；`session_kickoff.md` 却明令「每张图一个 JSON 落 `0_reading/<name>_view.json`」⇒ **两边没人负责拼装**，07-30 由主控手工机械组装 | `isolation.py:292-296` |

### ⭐ 主控预扫新增（07-30 未记，本批必须一并修）

**K · 守卫没有写保护 = 真逃逸面。**
`evaluate()` 对非 Bash 工具只检查「路径在 staging 内」，**不限制写哪里**。
子代理可以直接 Write 覆写 `tools/run_cv_probe.py` —— 那是 Bash 白名单唯一放行的可执行文件
（`guard.py:148-158`）—— 然后用允许的命令执行任意代码。
**而扫散文内容（E）对此毫无防御作用。**
⇒ 本批的方向是**「收紧写保护 + 放松散文扫描」配对做**，净效果是守卫**更严**、可用性**更好**。
不许只做放松那一半。

### 主控已替你消掉的不确定性

`case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json` 经
`_assert_source_allowed()` **实跑通过**（主控 2026-07-31 亲测），sha256 = `d3424c42c7ffc6c7dd242a56aa153dcd5ac5795c1f58a1e2dcd4ba320853b5ab`。
⇒ **build 可以经正规 `_copy_file` 拷入并登记 MANIFEST，不需要放宽任何污染断言。**
若你发现事实并非如此，**停下上报**，不要去改 `_assert_rel_allowed` / `HARD_BLOCK_*`。

---

## 3. 死骨架（四个 Slice，按序做，每个做完即停并 commit）

### S1 · 样板件进 staging（对应 F-2）

1. build 把 §2 那份 worked-example 经 **`_copy_file`** 拷进 staging，落点用**不触 `DENY_TOKENS` 的路径**，
   定为 `reference/worked_example_plan.json`。
2. **必须进 `MANIFEST.json`**（category 自拟，如 `reference`）。
   07-30 主控手工补入的那份**不在 MANIFEST 内**，导致 merge 的溯源清单漏记 —— 本批必须由 build 登记，
   这是本 Slice 的**主要价值**，不是附带。
3. kickoff 侧指向该 staging 路径：`_write_kickoff` 生成的文本里给出新路径，
   **或** build 改写拷入的 `session_kickoff.md` 中的路径。二选一，你定，但**必须两边口径一致**
   —— 不许出现「kickoff 说 A、文件在 B」的第二次同型缺陷。
4. 污染面：该文件是**另一栋楼**（smalloffice_20）、不含 sm24 任何信息 ⇒ 非污染。
   `_assert_manifest_clean` 必须继续通过，**不许为此放宽**。

**必须新增的锁**：
- 正例 = build 后 `reference/worked_example_plan.json` 存在、字节与仓库源相同、且在 MANIFEST 内。
- 负锁 = 摘掉拷贝调用 ⇒ 该测试变红（不许靠「文件恰好在」而绿）。
- 一致性锁 = kickoff 文本里出现的样板件路径，在 staging 内**实际存在**（不是硬编码字符串比对，是真去 stat）。

### S2 · 守卫：收紧写保护 + 放松散文扫描（对应 F-4 + K）

**2a · 写保护（先做这半，这是收紧）**
- Write / Edit / NotebookEdit 类工具的**目标路径**只许落在 `out/**` 与 `requests/**`；其余一律 deny。
- build 预建 `requests/` 目录，并在 kickoff 里写明「CV probe 的请求 JSON 写到 `requests/`」。
- 明确 deny 的（必须有测试逐条钉住）：`tools/**`、`guard.py`、`isolation_settings.json`、
  `MANIFEST.json`、`skills/**`、`src/**`、`case_data/**`、`prescan/**`、`reference/**`、staging 根。

**2b · 放松散文扫描（后做这半）**
- `DENY_TOKENS` / `~` / `..` 这三类**路径性**禁词，只作用于**被 `_looks_like_path()` 判定为路径的字符串**。
- 非路径字符串（Write/Edit 的 `content` 散文、note 文字等）**不做**这三类扫描。
- **Bash 的 `command` 整串仍走原严格检查**（那是命令行不是散文），`COMPOUND_TOKENS` / 命令白名单 /
  `python -c` 禁令 / 请求文件递归校验（`_validate_request_file`）**全部保留不动**。
- `DENY_TOKENS` 表本身**不删任何条目** —— 它对路径仍然有效。

**必须保留的安全性质（每条一个回归锁，本 Slice 交付的核心）**：
读 `gt.json` deny / `case_tests` 路径 deny / 越界绝对路径 deny / 越界 symlink deny /
非白名单命令 deny / `python -c` deny / 复合 shell token deny / 请求 JSON 内含禁词 deny。
**这八条在改造前后都必须红→deny，任何一条变 allow 即交付失败。**

**必须新增的锁**：
- 可用性正例：`Write out/reading_summary.md` 且 content 含 `~`、`grade line`、`..`、分号 ⇒ **allow**。
- 写保护负锁：`Write tools/run_cv_probe.py` ⇒ **deny**（这条在改造前是 allow，是本批新堵的洞）。

### S3 · prescan 落点语义收口（对应 F-1）

1. `cv_probe.py` 的 `prescan-plan` / `prescan-elevation`：若 `--out-dir` 的末级目录名是
   `cv_evidence` 或 `prescan`（即调用方已经手动拼了工具会自己追加的层级）⇒ **fail-closed 拒绝**，
   错误信息给出正确样例。
2. 无论成功失败，**回显最终落点绝对路径**。
3. `AI_agent/guides/new_case_guide.md` §2.1 把命令行样例**写死**成 `--out-dir <RUN>/0_reading`，
   并注明工具会自行追加 `cv_evidence/<stem>/prescan/`。

**必须新增的锁**：套娃 `--out-dir` ⇒ 非零退出且不落任何文件；正常 `--out-dir` ⇒ 落点与
`isolation._copy_prescan` 的拷贝守卫 `_is_run_prescan_path` **口径一致**（这条是真正要防的回归）。

### S4 · merge 目录形态自聚合（对应 F-5）

**定为 merge 侧自聚合，不是让 kickoff 多要一个文件。**
理由 = 项目不变量「强制约束别交给 LLM 记得」（CLAUDE.md §4#2）：
让弱模型记得多写一个聚合件，就是把硬约束交给 prompt，本项目已明令不这么做。

1. `merge_isolated_output`：若 `out/` 下没有单一聚合件，但存在若干 `<expected_output_id>.json`
   （按该 run 的 `view_manifest` 的 `expected_output_id` 枚举），则**纯机械聚合**为
   `{"views": {<expected_output_id>: <该文件内容>}}`。
2. **零内容改动**：聚合只做搬运，不许规范化、不许补默认值、不许排序改写内容。
   聚合结果的每个 view 必须与源文件 `json.loads` 后**逐字段相等**。
3. **fail-closed**：缺件（manifest 要求的 id 没有对应文件）或多件（出现 manifest 之外的 `*_view.json`）
   ⇒ **响亮报错**，不许静默补空、不许静默忽略多余件。
4. 单一聚合件仍然被接受（老路径不破）。

**必须新增的锁**：正例（五图目录 → 聚合等价于手工聚合，逐字节比对）/
缺件必红 / 多件必红 / 聚合内容零改动（对每个 view 做 `==` 断言）。

---

## 4. 硬约束

1. **不许弱化污染硬隔离**。S2 的净效果必须是守卫**更严**；§3 S2 那八条安全性质是验收红线。
2. **不许改测试迁就实现**。现有断言不得为让新码通过而改写；确需改动单列并说明为何原断言是错的。
3. **不碰** `case_tests/test_baseline/gt/**`（受保护答案树）、**不碰** `AI_agent/CLAUDE.md`
   （管理文档主权在主控 —— 2026-07-26 有施工方越界改本文档被判 MAJOR 的前例）。
4. **不碰**判卷层（`src/agent/judge/**`）—— 那是本轮**另一个席位**（sol）的并行批次，改了会撞车。
5. 跑测节奏：中间轮跑受影响子集（`scripts/tool_scripts/affected_tests.py` 算，**禁自由裁量**），
   交付前跑一次全仓。基线 = **1786 passed / 10 xfailed / 0 failed**。
   主控轻门的独立全量是唯一权威门，你的自跑不替代它。

---

## 5. 交付物

1. 四个 Slice 的代码 + 测试，**每个 Slice 边界一次 commit**（message 仿 `7.31_<EnglishLabel>`）。
2. 执行日志落 `AI_agent/logs/reviews/execution/2026-07-31_isolation_scaffold_glm.md`：
   每个 Slice 记「做了什么 / 新增哪些锁 / neuter 自查表 / 跑了哪些测试 + 数字」。
3. **neuter 自查表**（本批的验收命脉）：每把新锁指定一处 neuter（生产码定点破坏），
   报告该 neuter 下**具体哪些测试变红**。
   「全仓绿」**不等于**「锁是真的」—— 本项目在这一点上栽过至少三次
   （2026-07-22 九门 7 门假锁 / 2026-07-27 连续三轮 false-lock）。
   **诚实披露优于伪造**：查出自己的锁其实是假锁并修到夹具层，是本项目认可的正面样板
   （2026-07-28 施工方自查出两处假锁，被记为该批最值得记的三条治理数据点之一）。
4. 回主对话只给 **terse inline 简报**：X passed / 改了哪几个文件 / 关键结论 / 偏差 / **review-ask 段**
   （哪些处没把握 / 做了判断取舍 / 动了风险点）。无则写 `none`。
   **不要贴 diff 或文件内容** —— 主控自己跑 `git diff`。

---

## 6. 停下上报的情形（明确鼓励，不扣分）

- 骨架的某条前提被实测证伪（例如某个断言实际会拒绝）。
- 某条「必须保留的安全性质」与「必须新增的可用性正例」实测互斥。
- 发现骨架漏定了某个边界。

**⇒ 停下、上报、等主控裁定。不许自行降级为假设后接着做。**
2026-07-26 有施工方发现派工单前提有误（`.gitignore` 的 `output/` 是全局规则）停下上报，
主控改派工单 —— 那被记为「执行档发现派工单前提错时停下上报」的样板。
2026-07-27 连续三轮 REWORK 的共同病根，恰恰是**边界留给施工方猜**。

---

## 7. 验收口径（主控 + sol 会这样验）

1. 主控独立全量 pytest，逐数字对账，零回归。
2. 主控亲核 diff，重点看 S2 是否只做了放松那一半。
3. 主控在 `/tmp` 副本上自己拆你指定的 neuter，看红的是不是你说的那几条。
4. **活体验收**：真跑一次 `spawn_isolated_reader build`，检查
   ① 样板件在 staging 且在 MANIFEST ② `requests/` 已建 ③ kickoff 路径与实际落点一致。
5. sol 做升一档交叉对抗审（谁写谁不批），会用活体探针查假锁与安全回退。
