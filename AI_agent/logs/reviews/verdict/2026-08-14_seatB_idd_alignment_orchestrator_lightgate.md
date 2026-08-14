# orchestrator 轻门 —— 摊 B（`mep.idd_field_alignment` 通用字段对齐检查）

- **日期**：2026-08-14
- **被审**：`1472cfc`（分支 `wt/0814_B_idd_alignment`，工作树 `/workspaces/ep-wt-B`）
- **施工席**：GLM-5.2 · **执行报告**：`logs/reviews/execution/2026-08-14_idd_field_alignment_glm.md`
- **判定**：**施工按单做对了；⛔ 但派工单本身有一处硬伤 —— 阻塞档结构上不可能触发。**
  ⇒ **不是施工席的问题，是 orchestrator 的题错（第 18 次）。**
- ⚠️ 本轮**尚未**跨家族审（按「谁写谁不批」仍必须换人；本文只是 orchestrator 轻门）。

---

## 1. ✅ 独立复核通过的三项（orchestrator 自跑，未采信席位自述）

| 项 | 方法 | 结果 |
|---|---|---|
| **零回归（B3）** | 同一批真实产物，在基线树（`ep-wt-C`）与摊 B 树各跑一次 `check_mep`，逐份比**阻断集合** | **20/20 逐份完全一致，漂移 0** ✅ |
| **预扫复现（B2）** | 同上，看新检查在每份上的状态 | **红 14 / 绿 6**，与 orchestrator 预扫逐份吻合 ✅ |
| **检查条数** | 同上 | 18 → **19** ✅ |

（探针 `lightgate_b.py` 走**真实 `check_mep` 入口**，⛔ 非读源码形状匹配。）

## 2. ⛔ 轻门发现：**阻塞档是一道结构上恒绿的门**

派工单 §2.2 规定「阻塞名单 = 代码确定性生成的对象类型」，初值为摊 A 那两类。
**orchestrator 行为实测（`ep-wt-B` 树，真实 `check_mep` + `rep.blocking()`）**：

| 构造 | 新检查状态 | 它进阻断集了吗 |
|---|---|---|
| `HVACTemplate:Thermostat, T1;`（**只写 1 格**，属阻塞名单） | **pass** | **False** |
| `HVACTemplate:Thermostat, T1, Sch_H, , Sch_C;`（写全，对照组） | pass | False |
| `ZoneControl:Thermostat` 少一格（accept_C 真实形态） | fail | False（只报告 —— 符合设计） |
| `People` 缺 A5（6 份历史产物真实形态） | fail | False（只报告 —— 符合设计） |

**根因（查 IDD 坐实）**：

```
HVACTemplate:Thermostat               : 共 5 格，\required-field 只有 ['Name']
HVACTemplate:Zone:IdealLoadsAirSystem : 共 30 格，\required-field 只有 ['Zone Name']
```

⇒ 判据①（缺必填格）对这两类**只在「连第一格都没写」时才可能触发**，而代码渲染器永远会写第一格；
判据②（超字段数）**已被施工席自证是真实解析路径上的死代码**（eppy 对超字段对象**静默截断或 crash**，
`authored > idd` 对任何能解析成功的对象恒不成立）。
⇒ **两条判据对阻塞档同时失效 ⇒ 该门今天的净效果 = 纯报告，名义分档、实质零阻塞能力。**

**⛔ 这是 orchestrator 的题错**：派工单指定了阻塞名单，**却没有先去 IDD 里核一遍
「这两类的必填格到底有几格、这条判据对它们能不能触发」** —— 与本日另两处题错同一形状
（把「我以为的盘面」当「盘上的事实」写进单子）。**施工席按单做对了，不记它的账。**

### 建议修法（交下一轮，⛔ 本文不擅自改）

阻塞档想抓的是「**代码生成的那几行一旦对不齐就是代码 bug**」，
而 IDD 的 `\required-field` **不是那件事的探测器**。正确探测器应是
「**解析回来的对象是不是渲染器打算写的那个形状**」——
即由摊 A 的渲染器给出期望字段数/字段位，门断言逐位一致（round-trip 断言）。
这条同时能让阻塞档**真的可触发**，且中和渲染器即变红（可做 neuter 自证）。

## 3. ✅ 施工席自陈未验证项 —— 逐条核过，**全部属实且诚实**

1. 判据②是真实链路上的死代码 —— ✅ 与 §2 的实测一致（且比派工单写的更彻底）。
2. eppy 对超字段对象**静默截断且无人报警** —— ⚠️ **这条比判据②本身更值钱**，
   已超出本摊范围，**应单独登记为债**（解析器会悄悄吃掉字段 ⇒ 任何按位置读的门都在读被截断后的形态）。
3. `smalloffice_23/4_mep/` 被 `.gitignore:320` 排除 —— ✅ 核实属实（`git check-ignore` 命中、`NOT TRACKED`）
   ⇒ **orchestrator 预扫说的「21 份」是本机工作目录的属性，干净检出只有 20 份**（F-8 族，预扫 README 已更正）。
4. 去重口径 = 「不复述诊断」而非「不报 offender」 —— 已知悉，留给跨家族审裁。
5. 摊 A 接缝仅按今天的类型集验证 —— 与派工单 §3 一致。

## 4. ⚠️ 席位 B5「全仓 rc=1」= **环境假红，不是回归**（orchestrator 已查到根因）

席位报：`2 failed`（`test_gt_from_dxf` / `test_inspect_dxf`），并判为「基线预先存在、与本摊无关」。
**现象属实，诊断错。** orchestrator 实测：

| 树 | 同一份代码 | 结果 |
|---|---|---|
| 主树 `/workspaces/EnergyPlus-Agent-dev` | 同 commit | **16 passed** |
| 干净 worktree `/workspaces/ep-wt-C` | 同 commit | **2 failed / 14 passed** |

**根因（已坐实）**：这两条测试用 `subprocess` 跑 `python scripts/tool_scripts/<x>.py`。
脚本式启动时 `sys.path[0]` = **脚本所在目录**（不是 cwd）⇒ `import src...` 落到 **editable 安装**，
而它指向**主树** ⇒ 子进程里 `REPO_ROOT = /workspaces/EnergyPlus-Agent-dev`，
测试传的却是 worktree 路径 ⇒ `gt_vg_config_path_forbidden`（`gt_manifest.py:278`）。
实测证据：worktree 内以脚本形态启动，`gt_schema.__file__` 打印的是**主树**路径。

**⇒ 三条后果（均须记）**：
1. **任何 worktree 席位报的「全仓绿/红」都不可全信** —— 权威全量必须在主树跑；
2. 席位数字与 orchestrator 基线**完全对得上**：`2601 passed + 2 failed = 2603`（= 基线 total），
   `2612 = 2601 + 本摊新增 11` ⇒ **本摊零回归成立**；
3. **F-8 族新面**：仓库**不能从干净检出直接跑绿全仓**（CLI 子进程跨树导入）⇒ 独立登记为债。

## 5. 结论

- 摊 B **可进入跨家族审**；零回归与预扫复现已由 orchestrator 独立坐实。
- **必须随件转达给审阅方的两条**：① §2 阻塞档恒绿（**派工方题错**，非施工缺陷）；
  ② §4 环境假红的根因，避免审阅方重复踩。
- 新登记债：**eppy 静默截断超字段对象** · **干净检出跑不绿全仓（CLI 子进程跨树导入）**。
