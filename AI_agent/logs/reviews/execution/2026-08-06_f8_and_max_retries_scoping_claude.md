# 执行日志 · F-8「全仓绿不可移植」精确排期 + `MAX_RETRIES=0` 定性

- **派工单**：`AI_agent/logs/reviews/request/2026-08-06_f8_and_max_retries_scoping_claude.md`
- **席位**：Claude 侧 Sonnet 子代理
- **基点**：`dfbd62a`（分支 `6.15_ValidationArchM0toM4`，主工作树）
- **开工自检**：`git log --oneline -1` = `dfbd62a` ✓；`pwd` = `/workspaces/EnergyPlus-Agent-dev` ✓；
  `git status --short` 只有 4 个已知 `case_tests/` 未跟踪目录 + 本单自身 ✓（未触碰它们）

---

## ⭐ 停下上报（先说这条，改写了任务一的范围）

派工单陈述「这 5 条测试在干净 worktree / 新克隆 / CI 必红」——**5 条里只有 3 条是真的因为 F-8（被
`.gitignore` 挡住的活输入）而红，另外 2 条在干净 worktree 里确实也会红，但原因与 `.gitignore` / F-8
完全无关，是我复现方法本身引入的环境假象**：

- **根因**：本机 venv（`/opt/venv`）是通过 `hatchling` editable install 装的，其 `.pth` 文件
  （`/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth`）**硬编码了主工作树的
  绝对路径** `/workspaces/EnergyPlus-Agent-dev`。当我在 `git worktree add` 出的干净副本（`/tmp/.../clean_wt`）
  里跑测试时，任何 `subprocess` 里 `from src... import ...` 解析到的仍是**主树的 `src/`**，不是干净副本自己的 `src/`。
  两个测试恰好会拿 `REPO_ROOT`（`src/agent/judge/gt_schema.py:38 REPO_ROOT = Path(__file__).resolve().parents[3]`，
  这里被解析成主树路径）跟传入的 config 路径（干净副本路径）做 `.resolve()` 相等性检查
  （`src/agent/judge/gt_manifest.py:277-278 if vg_path.resolve() != (REPO_ROOT / "src/configs/correction.yaml").resolve(): raise ValueError("gt_vg_config_path_forbidden")`），
  两个路径当然不相等 ⇒ 红。
- **判决性验证**：把 `PYTHONPATH` 显式指向干净副本自己（让它自己的 `src/` 先于 site-packages 被解析，
  这正是「真的用这份代码自己 `uv sync`」会得到的效果），这 2 条**立刻转绿**，其余 3 条依旧红：
  ```bash
  cd <clean_worktree>
  PYTHONPATH=<clean_worktree> python -m pytest \
    tests/test_inspect_dxf.py::test_manifest_inspector_cli_exit_and_json_contract \
    tests/test_gt_from_dxf.py::test_build_only_cli_round_trips_l_candidate_and_nonzero_north -q
  # => 2 passed
  ```
  这两条测试**不依赖任何 case_data / 图像 / EP 产物**——它们的 DXF 全部由测试自己用 `ezdxf` 现造在 `tmp_path`
  里（见 `tests/test_inspect_dxf.py:29-54 _build_synthetic` / `tests/test_gt_from_dxf.py` 同构的 `_dxf()`），
  真正 CI（在自己的检出路径上跑 `uv sync --frozen`，`.pth` 会正确指向那次检出自己）不会踩到这个坑。
  这一点我用 `uv sync --frozen` 在 worktree 里实测复现过（详见下方"操作注记"），随后已完整复原主树 venv。
- **⇒ 任务一的精确范围改写为**：
  - **真 F-8（3 条）**：`test_partition_on_window_jamb_real_restore_reading_r2_flags_four` ·
    `test_sm21_phase1_reading_score_regression_floor` · `test_sm21_anchor_ep_clean`
  - **假 F-8（2 条，环境假象，与 `.gitignore` 无关，真实 CI 不会踩）**：
    `test_manifest_inspector_cli_exit_and_json_contract` · `test_build_only_cli_round_trips_l_candidate_and_nonzero_north`

下面任务一的清单/分类/体积核算/机械检查，均**只针对真 3 条**；假 2 条单列一节，不建议为它们做任何 F-8 式修复。

---

## 任务一 · 精确清单

### 复现命令（干净 worktree，基点 `dfbd62a`）

```bash
git worktree add /tmp/f8investigation/clean_wt dfbd62a --detach   # ⚠️ 显式基点，不用默认
cd /tmp/f8investigation/clean_wt
PYTHONPATH=/tmp/f8investigation/clean_wt python -m pytest \
  tests/test_checks_reading_correction.py::test_partition_on_window_jamb_real_restore_reading_r2_flags_four \
  tests/test_reading_score.py::test_sm21_phase1_reading_score_regression_floor \
  tests/test_validation_run_baseline.py::test_sm21_anchor_ep_clean -q
# => 3 failed（用 PYTHONPATH 消除了上面那条环境假象后，这 3 条依旧红，是干净的 F-8 信号）
```

### 3 条真 F-8 逐条

| # | 测试 | 缺失文件（精确路径） | 大小 | `.gitignore` 命中行 | 谁产的 |
|---|---|---|---|---|---|
| 1 | `tests/test_checks_reading_correction.py:345 test_partition_on_window_jamb_real_restore_reading_r2_flags_four` | `AI_agent/logs/experiments/2026-06-30_reading_scaffold_restore_validation/readings/sonnet_r2/1f_view.json` | 22,221 B | `.gitignore:7 20*_*/`（`git check-ignore -v` 实测命中，见下） | 2026-06-30 一次"reading 脚手架完整恢复"实测——**冷启隔离 Sonnet 子代理**（`claude-sonnet-4-6`）读 sm21 产出的真实识图产物；同目录 `README.md` 记录了该次实验的设计与结果（sonnet_r2 这一抽把窗洞位置 3.44/6.3/8.7/11.36 误判成竖墙，正是这条检查要抓的"窗框被误读成隔断"缺陷类型的**真实坏形态**） |
| 2 | `tests/test_reading_score.py:273-279 test_sm21_phase1_reading_score_regression_floor` | `case_tests/e2e_tests/smalloffice_21_pre/phase1/1f_view.json` + `2f_view.json`（该测试只 `glob("*_view.json")` 后按 `image_kind in (None,"plan")` 过滤，立面 4 个 `*_view.json` 被过滤掉，实际只读这 2 个） | 12,090 B + 11,697 B = 23,787 B | `.gitignore:287 case_tests/e2e_tests/smalloffice_21_pre/`（`git check-ignore -v` 实测命中） | 2026-06-09 前后的一次历史识图产出（早于 `127ba06` 那版脚手架，CLAUDE.md/memory 称其为 **sm21_pre = 回归地板**——本测试就是"不能跌破这个历史已达到的最低分"的回归锁） |
| 3 | `tests/test_validation_run_baseline.py:237-242 test_sm21_anchor_ep_clean` | `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/EP/EP_run/eplusout.end` | 97 B | `.gitignore:275 eplusout.*`（`git check-ignore -v` 实测命中；`*.end` 单独在 `:273` 也会命中，但 `eplusout.*` 是判定生效的那条） | 2026-06-16 sm21_anchor 的一次真实 Opus e2e 跑测（identity reading→pipeline→EP 全链），EnergyPlus 在该 run 目录下真跑出的完成标记 |

**关于第 3 条的"原作者部分知情"**：`tests/test_validation_run_baseline.py:161-163`
```python
# EP run outputs (eplusout.*) are gitignored, so these synthesize the .end in a
# tmp copy — hermetic on a fresh clone / CI.
_CLEAN_END = "EnergyPlus Completed Successfully-- 6 Warning; 0 Severe Errors; ...\n"
```
这段注释 + `_run_copy_with_ep()` 辅助函数确实是作者为「EP 输出被 ignore」写的应对方案，但**只接到了
`test_require_ep_blocks_when_no_run` / `test_require_ep_passes_on_clean_run`（`@_RERECORD_XFAIL`）/
`test_run_with_clean_ep_validates`（`@_RERECORD_XFAIL`）三条通用策略测试上**——它们测的是 `validate_case`
的策略分支行为，用哪段 `.end` 文本不重要，合成无损。**`test_sm21_anchor_ep_clean` 没有走这条路**：
它测的是"sm21_anchor 这个具体黄金 run 真的 0 severe"，是坐实点，不是策略点——如果给它也"合成"，
测试就退化成断言一个自己手写的字符串，正好背离了它存在的目的（证明这个具体历史 run 真的干净）。
这解释了"覆盖不全"不是疏漏，而是**这条测试的性质决定了它不能走合成路线**（见下方分类判据）。

### 假 F-8（2 条，独立说明，不建议按 F-8 处理）

| 测试 | 实际红因 | 真实 CI 会红吗 |
|---|---|---|
| `test_manifest_inspector_cli_exit_and_json_contract` | 见上文停下上报 | 不会（DXF 自己造，`.pth` 在自己检出里指向自己） |
| `test_build_only_cli_round_trips_l_candidate_and_nonzero_north` | 同上 | 同上 |

---

## 任务一 · 分类（3 条真 F-8）

判据：**能否脱离"某次具体识图/仿真跑测的真实产出"而不失去测试意图**——脱离得掉 ⇒ 该合成（②）；
脱离不掉（测试的意义就是"这份历史真实产出必须保持这个质量/结果"）且文件够小够稳 ⇒ 该入仓（①）；
两者都不成立、且文件真的取决于环境（如受版权/体积限制的外部数据）⇒ 该 `skipif`（③）。

| # | 测试 | 分类 | 理由 |
|---|---|---|---|
| 1 | 窗框误判夹具 | **① 入仓小体积夹具** | 22 KB，测试文档自陈是「real bad fixtures」——检查要抓的是模型的真实错误形状（窗洞位置被误判为竖墙的具体坐标模式），手写夹具会不可避免地"照抄检查的实现逻辑"而不是复现模型真实会犯的错（本项目已多次撞过这个坑，见 F-5/F-7 教训：夹具抄实现 ⇒ 测试自洽但护不住真实产出）。稳定、单一用途、不会随后续跑测再生成新版本。 |
| 2 | sm21_pre 回归地板 | **① 入仓小体积夹具** | 23.8 KB（只取该测试实际消费的 2 个 plan JSON，不必带 4 个立面 JSON + 6 张 PNG + summary.md）。这是被 CLAUDE.md/memory 反复引用的"回归地板"基准，其存在意义就是锁定一个具体历史时点的识图质量，本质就是判卷回归夹具，天然属于①。 |
| 3 | sm21_anchor EP 完成标记 | **① 入仓小体积夹具** | 97 B，纯文本。不适用②（见上方"原作者部分知情"分析——合成会让测试断言退化成断言自己写的字符串，失去"这个具体历史 run 真的跑干净"的证明力）；不适用③（这不是"缺真实产物才能测"的情况，产物已经存在于本机磁盘上、只是没入库，跳过没有意义）。 |

三条**全部落在①**，没有②/③/④。

## 任务一 · 体积核算（走①）

| 文件 | 字节 |
|---|---|
| `AI_agent/logs/experiments/2026-06-30_reading_scaffold_restore_validation/readings/sonnet_r2/1f_view.json` | 22,221 |
| `case_tests/e2e_tests/smalloffice_21_pre/phase1/1f_view.json` | 12,090 |
| `case_tests/e2e_tests/smalloffice_21_pre/phase1/2f_view.json` | 11,697 |
| `case_tests/e2e_tests/sm21_anchor/run_2026-06-16_opus_e2e/EP/EP_run/eplusout.end` | 97 |
| **合计** | **46,105 B ≈ 45.0 KB，4 个文件** |

（若图省事把 `sonnet_r2/` 整目录〔含 6 个 view json + 6 张 render png + summary.md，148 KB〕和
`smalloffice_21_pre/phase1/` 整目录〔含 4 个立面 json + 6 张 png + summary.md，140 KB〕都收进来，
总量约 **288 KB**——但测试机械依赖只用得到 46 KB 那部分，多收的是"人看着舒服"的上下文，非必需。）

## 任务一 · ⭐ 防复发的机械检查（2 个选项，未实现）

**选项 A：AST 静态扫描测试文件里的路径字面量，逐个跑 `git check-ignore`。**
- 做法：pre-commit hook 或 CI 步骤，解析每个变更/新增的 `tests/*.py`，抓取形如
  `Path("...")`（含 `Path(...) / "literal"` 链式拼接，本仓库现有测试的路径几乎都是这种写法）的字符串字面量，
  对每个疑似路径调 `git check-ignore -q <path>`，命中则拦停（除非该测试同时标了显式豁免注释/白名单）。
  本仓库已有同类精神的基础设施可复用套路（`affected_tests.py` 的 AST import 边扫描，`CLAUDE.md` 有提及），
  不是从零发明。
- 代价：**heuristic**——只能抓"路径字面量在源码里直接可见"的情况；动态拼接（`for f in glob(...)`）、
  从外部配置读路径、或路径变量在别的模块里定义再 import 进来的情况会漏判。也需要维护一份"这个测试就是该走
  gitignored real fixture、不算违规"的白名单（否则新增③类 `skipif` 测试会被误拦）。实现/维护成本中等，
  运行成本极低（纯静态、秒级）。

**选项 B：CI 增加一个"影子任务"——在全新检出上跑一遍全仓测试，而不是复用长期存在的开发环境。**
- 做法：CI 里独立于主任务再加一步：`git clone --depth 1 <repo> /tmp/x && cd /tmp/x && uv sync --frozen && pytest -q`
  （或等价的容器化全新构建）。这与我本次验证 F-8 的方法完全同构（干净 worktree + 独立跑测），
  是"新克隆会不会红"这个问题最直接、零启发式的答案——不需要猜哪些字符串是路径，任何一种"这台机器独有、
  新环境没有"的依赖（不止 `.gitignore` 挡住的文件，还包括本次任务一开场撞见的"共享 venv 里 editable-install
  路径绑死旧检出"这类假象、遗留的临时文件、未声明的环境变量……）都会被同一个信号——"红了"——直接捕获。
- 代价：**成本真实存在但可控**——一次全新 `uv sync` + 全仓测试，比复用已装好的环境慢（额外几分钟量级，
  取决于依赖下载缓存命中率），且需要独立的执行时间/计算资源（不能和主 CI 任务共享同一个预热好的环境，
  否则这项检查本身就失去意义）。不需要维护白名单或猜测规则，误报率趋近于零（唯一"误报"是本任务撞见的
  那种"真正的环境差异其实与 gitignore 无关"的情况——但那恰恰也是想抓的东西，参见本单开头的停下上报）。

**建议**：选项 B 是唯一真正"零遗漏"的检查（同时也是本单据以纠正派工单前提的方法），但成本較高、
适合定在"合并到主分支前"或"每日一次"这类不那么高频的节奏（呼应 CLAUDE.md 已有的"跑测节奏三档"原则，
而非塞进每次 commit）；选项 A 便宜、能挡住大多数新增违例，适合作日常 pre-commit/PR 级别的快速门，
但需要接受它有盲区。**两者不互斥，理想形态是 A 做日常快门、B 做发布前/每日的权威门**——与本仓库现有
"轻门=唯一权威门、日常跑受影响子集"的分级节奏一致。

## 任务一 · 排期建议

- **3 条真 F-8（46 KB / 4 文件）可以一次性收掉**：无 schema 决策、无接口设计、不改任何测试断言，
  唯一动作是把这 4 个具体文件从"存在但被 ignore"变成"入库"（`git add -f` 这 4 个路径），
  是一个非常小、边界清楚的独立小 PR。
- **机械检查（选项 A 或 B）应单独立项**：这是基础设施/工具决策（选哪个方案、放在哪一层跑测节奏、
  维护白名单的责任人是谁），和"收掉这 3 条红"不是同一个工作量级，不建议捆在一起做。
- **"假 F-8"的 2 条不需要任何后续动作**：它们不红在真实 CI 上，为它们做任何 F-8 式修复都是在解决一个
  不存在的问题；如果确实想让"worktree + 共享 venv"这种开发时的临时验证方式也保持干净，那是另一个课题
  （venv 隔离策略），与本单主题（版本库输入完整性）不同源，不建议并入本批。

## 操作注记（诚实记录一次对共享环境的短暂改动，已复原）

为验证"假 F-8"是环境假象而非真实 F-8，我在 worktree 里跑了 `uv sync --frozen`（想验证"真的自己
`uv sync` 会不会正确"）。**这一步误伤了共享 venv**：`uv sync` 认的是当前激活的 `VIRTUAL_ENV`
（`/opt/venv`，与主树共用），所以它把 editable-install 指针从主树 swap 到了 worktree，
顺带因为 lock 差异卸载了 7 个与本项目代码无直接 import 关系的包（`aiohttp`/`aiohappyeyeballs`/
`aiosignal`/`frozenlist`/`multidict`/`propcache`/`yarl`——全仓 `grep` 确认零处直接 `import aiohttp`，
且它们本就不在 `uv.lock` 里，应是之前某次会话手工装的游离依赖）。**已立即在主树 `uv sync --frozen`
一次复原 editable-install 指针**（现内容确认回到 `/workspaces/EnergyPlus-Agent-dev`），并用
`pytest --collect-only -q` 确认全仓 2244 个测试项零 import 报错。那 7 个游离包未恢复（它们本不在
lock 里，恢复它们不是"复原"而是"重新引入漂移"）。如实登记，供后续任何人发现 venv 与预期不符时对账。

---

## 任务二 · `MAX_RETRIES` 为什么被关成 0

### 1. 它到底关掉了什么重试（调用链 + 行号）

```
src/agent/_share.py:7      MAX_RETRIES: Final[int] = 0
        ↓
src/agent/state.py:243     max_retries: int = MAX_RETRIES     # AgentState 字段默认值
        ↓（唯一消费点）
src/agent/nodes/validate.py:41
    if errors and state.retry_count < state.max_retries:
        return Command(goto="intake", update={..., "retry_count": state.retry_count + 1, ...})
```

`grep -rn "retry_count\|max_retries" src/` 全仓只有这一个消费点（`src/rag/rag.py` 的 `max_retries` 是
另一个同名但无关的局部参数，管的是 embedding API 的传输层重试，不读这个常量）。

**关掉的东西**：下游 LangGraph（intake → 9 subagent → cross_ref → **validate** → simulate）里，
`validate_node` 校验配置引用（`validate_references()` + E4 输出坐标契约）出错后，**在打扰人类之前**
本该有的"自动静默重试"分支——`errors and retry_count < max_retries` 恒为 `errors and 0 < 0` = `False`
（`retry_count` 初值 0，`max_retries` 恒 0）⇒ **这个分支永远是死代码，实际运行时从未被进入过**。
效果是：**任何一次校验出错，哪怕是第一次，都直接跳过自动重试、立刻 `interrupt()` 转人工审阅**
（`validate.py:54`），而不是先让系统自己悄悄重试几次再决定要不要打扰人。

### 2. 何时被设成 0、当时理由

```bash
git log --all -S "MAX_RETRIES: Final" -- src/agent/_share.py
# => 唯一命中: 299149c "4.20-zero"（2026-04-21，仓库创世提交）
git log -p --follow -S "MAX_RETRIES: Final" -- src/agent/_share.py | grep -n "^commit\|MAX_RETRIES: Final"
# => 1:commit 299149c...   19:+MAX_RETRIES: Final[int] = 0
```

**只有一次改动记录**：仓库的**第一个提交** `299149c "4.20-zero"`（一次性带入 `.gitignore`/`.env.example`/
`AI_agent/CLAUDE.md`/`data/dependencies/Energy+.idd` 等全部创世文件，非某次功能改动）。
`git show 299149c:AI_agent/CLAUDE.md` / `AI_agent/plan.md` / `README.md` 三处 `grep -i retry` **零命中**——
**当时没有任何文档给出"为什么是 0"的理由**。此后四个月零次改动（`-S` 精确匹配定义行，之后所有命中
`299149c`/`8dd4167`/`4b87e9f`/`a658989`/`dfbd62a` 全是**引用/讨论它**的注释与文档提交，没有一次改了这行）。

### 3. 现在设回非 0 会发生什么（读代码，未跑）

**与 F-4 的关系：不冲突，因为根本不是同一条通道。** F-4 修的是 `src/agent/pipeline.py:_call_json_llm`
里 1_correction/4_mep 阶段的 LLM 调用重试（`pipeline.py:692 attempts=3` / `:788 attempts=3`，硬编码在调用点，
`retry_guidance` 是格式纠错回灌），这条路径**完全不读 `MAX_RETRIES`/`state.max_retries`**——
`grep -n "MAX_RETRIES" src/agent/pipeline.py` 零命中。改 `MAX_RETRIES` 对 F-4 那条通道零影响。

**与 F-11 的关系：不会破坏正确性，但会放大 F-11 刚登记过的真实风险（结构性死循环里的静默烧钱）。**
`src/agent/runner.py:32-42`（`InterruptLoopBreakerError` 的 docstring）原话已经把 `MAX_RETRIES=0` 当**既定前提**
写进了熔断器的设计依据：*"A `validate -> intake -> ... -> validate` cycle with a persistent error,
`MAX_RETRIES=0`, and an intake short-circuit cannot self-terminate... Rather than rely on the error
'eventually going away', the breaker counts consecutive **identical error-bearing interrupts** and aborts."*
关键在于熔断器只数 **`interrupt()` 的出现次数**（`runner.py:110-141` `pending = [...t.interrupts...]`），
不数 `validate→intake` 自动重试的圈数。如果 `max_retries` 设为 N>0：
- 对于**真正瞬时性/可自愈的错误**（`validate_node` 文档定义的设计目标场景），会按预期工作：
  自动重试 N 次，成功就不再打扰人，符合 `validate.py:31` 文档说的 "auto-retry on error up to
  max_retries; else HITL"。
- 对于**像 F-11 那种结构性错误**（`cross_ref_foundations` 在 surfaces 还没造出来前就用终态 snapshot
  校验 115 条 `VERTEX_FRAME_DRIFT`，`graph.py:52` 有错即短路回 validate）——这类错误**不会因为重跑
  `intake_node` 而消失**（`intake.py:71-90`：`validation_errors` 非空 ⇒ 短路条件 `not state.validation_errors`
  不成立 ⇒ 每次自动重试都会重新触发一次**真实的、计费的** `run_pipeline_artifacts` 1_correction LLM 调用，
  而 F-11 的病根跟 1_correction 产出内容毫无关系）。设 `max_retries=N` 相当于给这类"注定复发"的错误
  **在每一次被熔断器计数之前，先免费送 N 轮静默重试**——F-11 当时"1h40m ≈ 400 圈才发现、烧的是按量计费的
  DeepSeek"这个实犯（`AI_agent/plan.md` F-11 条目）正是因为当时**熔断器还不存在**；熔断器修好之后
  （`4b87e9f`→`a658989`），`max_retries` 若仍是 0，坏情况下最多 4 圈（3 次相同 interrupt + 1 次触发熔断）
  就能报清楚；若 `max_retries=N`，同样触发熔断需要 `(N+1)×4` 圈量级的真实 LLM 调用——**熔断器兜住的是
  "会不会死循环"，兜不住"死循环里每一圈的成本"，`max_retries` 直接放大后者**。
- **不会死锁、不会让熔断器失效**——两者语义正交，机制上互不阻塞；代价是**结构性错误场景下的成本被放大**，
  且放大倍数由 `max_retries` 的值直接决定。

### 4. 结论（一句话）

`MAX_RETRIES=0` **不是被谁调低/关闭的**——它是仓库创世提交里从未被赋予过非零值、且四个月来无人
复核也无任何文档给过理由的**初始默认值**；今天最近一次真正打交道的工作（F-11）明确选择的是
"保留它、给它配熔断器兜底"而不是"回填成非零"，所以按"有意 vs 误伤"二选一更接近**"有意维持现状"**——
建议不必单独立项去"修"，把当前语义（0 = 校验一有错立即转人审、零自动静默重试）连同 §3 的成本前提
（若未来要调高，必须先确认触发的错误类别是瞬时可自愈的，否则会放大结构性死循环的烧钱）一并写进
`architecture/pipeline_stage_contracts.md` 或 `state.py` 的字段注释存档即可结案；只有当产品侧确实想要
"配置校验错误先自动愈合几次再打扰人"这个新行为时，才值得为它单独立项设计。
