# 摊 A 对照表 —— 六工具 × 三形态 × 参数形态 × 坐标系（S-1 / S-1b / S-2 / S-3）

**席位**：Claude 侧执行档（Sonnet 5 子代理）。**产物**：本文件 + `tests/test_substrate_sweep_tools.py`
（新建，47 个测试用例：43 正锁 + 4 `xfail(strict=True)`）+ `A_evidence/`（探索脚本与原始日志）。

**方法**：全部经 **真 staging**（`build_isolation_workspace`，preview/unbound 模式）+ **真
`subprocess`** 跑 `python tools/run_cv_probe.py ...`（staged wrapper），⛔ 未直接 import
`src.agent.reading.cv_toolbox` 里的任何函数。真解释器 `/opt/venv/bin/python`。

## 顶部摘要：哪些做了、哪些没做

| 项 | 状态 |
|---|---|
| S-1 主表（6 工具 × 3 形态 = 18 格） | ✅ **18/18 全做完**，全部 `✅ 通且数对` |
| S-1b 文档示例逐字实跑（主控中途补的一格，7 条 bash 块） | ✅ **7/7 全做完**（5 通、1 因占位符语义被 shell 误解、1 按文档语义确认为"待用户自写"的非缺陷） |
| S-2 参数形态表（dispatch 称共 51 格，含重复计数） | ⚠️ **部分完成**——完整做了 `bbox`（3 种写法 × 关键形态）+ `anchors_json`/`candidates_json`（各 3 种写法的其中 2 种）+ `scale`（int/float/string 等价性）+ window 10 个过滤参数（native/string 各一次组合调用）；**未逐一穷举**每个专属参数的每种写法（见文末「没做完的格子」） |
| S-3 坐标系（3 项） | ✅ **3/3 全做完** |
| 锁 | ✅ 43 正锁 + 4 `xfail(strict=True)`，全部经真实 staging + subprocess |
| neuter | ✅ 3 把（超过下限 3 把的要求），逐条见 §7 |

---

## 0. 前提核验（本单标 ⚠️ 的每一条，逐条核过）

| # | 派工单原话 | 核verification 方法 | 结论 |
|---|---|---|---|
| 1 | §3.2「`ALLOWED_TOOLS` 就这六个，prescan 两个已于 08-15 撤除」 | 直读 `src/agent/execution/isolation_templates/guard.py` 源码：`ALLOWED_TOOLS = {crop_zoom, wall_line_profiler, storey_line_profiler, px_m_calibrator, window_cc_detector, overlay_logger}`，`PROBE_TOOL_NAMES` 同一份六个；注释明写 "2026-08-15: prescan-plan / prescan-elevation withdrawn" | **核过·成立** |
| 2 | §3.3「授权工具的参数面 = 6 个公共参数 + 15 个专属，共 51 格」 | 逐工具清点：crop_zoom=6、wall_line_profiler=6+1=7、storey_line_profiler=6、px_m_calibrator=6+3=9、window_cc_detector=6+10=16、overlay_logger=6+1=7；6+7+6+9+16+7=**51**，与 `cv_probe.py` 的 `build_parser()` 逐 subparser 选项数完全一致 | **核过·成立**（算术精确对上） |
| 3 | §3.3「我读代码看到的一个候选缺陷」：`"bbox":[100,80,700,460]` 在 A/C 形态下会被 wrapper `json.dumps` 成 `--bbox [100,80,700,460]`，`_bbox` 按逗号切后拿到 `"[100"` ⇒ 可能直接报错 | 实跑（见 §4 详述） | **核过·成立**，已登记 **F-52** |
| 4 | §3.4(1)「F-51 第一刀已在 `write_sidecar` 收口，六工具都经过它」 | 读 `cv_probe.py::execute_probe`：crop_zoom / overlay_logger 直接调 `write_sidecar`；wall_line_profiler / storey_line_profiler / px_m_calibrator / window_cc_detector 经共享 `_write()` helper 调 `write_sidecar`。实测：S-3 六工具全部正确回报源图尺寸（§6）；neuter 2（把 `write_sidecar` 的 `source_width_px` 砍半）**一次性打红全部六工具的 S-3 用例**，反向坐实"六个都真的经过它" | **核过·成立** |
| 5 | §4「灰度必须落在 `clean_vector_v1` 的灰带内（现有夹具用 128，注释说灰带是 60–230）」 | 直读 `recipes.py`：`gray_lo=60, gray_hi=230, rgb_tol=8`；本单夹具全程用 `GRAY=128`，实测 mask 正确捕获全部构造几何（无遗漏、无假阴性） | **核过·成立** |
| 6 | §6「真环境是 `/opt/venv/bin/python`；仓内 `.venv/` 是坏的（numpy 自 08-01 残缺）」 | 实测：`.venv/bin/python` 是指向系统 `/usr/bin/python3.12` 的符号链接，`import numpy` 报 `AttributeError: module 'numpy' has no attribute '__version__'`；`/opt/venv/bin/python` 下 numpy 2.4.4 / scipy 1.17.1 / PIL 12.2.0 全部正常 | **核过·成立** |

**本轮 6 条 ⚠️ 前提全部核实成立，零证伪**——与「派工方错误率 24/24」的历史基线不同，这次派工单（含中途补丁）的具体判断没有踩坑。中途补丁自己承认的疏漏（S-1b 未列独立可交付格）已按要求补做，见下。

**与摊 B 的编号协调（额外发现，非前提但值得记）**：摊 B（GLM）已在 `grid_B.md` 里把自己的缺陷登记为
`F-52B`/`F-53B`/`F-54B`/`F-55B`（主动加 B 后缀避免与摊 A 撞号）。本表沿用派工单原文的**无后缀**编号
`F-52`/`F-53`/`F-54`——两套编号不冲突，但**主控汇总收口时需要重新排序统一编号**（当前是"F-52 与 F-52B
同时存在、指两件不同的事"）。

---

## 1. S-1 主表（6 工具 × 3 形态 = 18 格）

**夹具**（`tests/test_substrate_sweep_tools.py` 顶部常量，全部由构造决定真值）：
1200×900 白底；两条竖线（灰 128，宽 5px，居中于 x=100/700，纵向范围 y∈[50,650)）；
两条横线（灰 128，宽 5px，居中于 y=150/550，横向范围 x∈[50,750)）；两个实心矩形
`RECT_A=(900,750,920,765)`、`RECT_B=(960,750,980,765)`（各 20×15、面积 300，彼此 x 间隙 40px，
远离两条线所在区域）。四线交叉会被 `window_cc_detector` 判成一个 bbox=[50,50,750,650] 面积 12900
的"十字"连通域——这是构造的必然结果，非缺陷，已作为已知第三候选一并锁死。

`x=100/700` 对应 15.0 m ⇒ 真值 **40.0 px/m**。

| 工具 | 形态 | 命令原文（关键参数，image/out-dir 略） | 退出码 | 产物里的实际值 | 与期望值是否相等 | 判定 |
|---|---|---|---|---|---|---|
| wall_line_profiler | B | `--tool wall_line_profiler --axis col` | 0 | 2 候选，`position_px`=[100.0, 700.0] | 相等 | ✅ |
| wall_line_profiler | A | `{"tool":"wall_line_profiler","args":{"axis":"col",...}}` via `--request` | 0 | 同上 | 相等 | ✅ |
| wall_line_profiler | C | 同上载荷 via `--batch` | 0 | 同上 | 相等 | ✅ |
| storey_line_profiler | B | `--tool storey_line_profiler`（无 axis，工具内部固定 row） | 0 | 2 候选，`position_px`=[150.0, 550.0] | 相等 | ✅ |
| storey_line_profiler | A | 同参数 via `--request` | 0 | 同上 | 相等 | ✅ |
| storey_line_profiler | C | 同参数 via `--batch` | 0 | 同上 | 相等 | ✅ |
| px_m_calibrator | B | `--anchors-json '[{"axis":"x","px_a":100,"px_b":700,"value_m":15.0}]'` | 0 | `px_per_m`=40.0, `axis_px_per_m`={"x":40.0} | 相等 | ✅ |
| px_m_calibrator | A | 同锚点（原生数组）via `--request` | 0 | 同上 | 相等 | ✅ |
| px_m_calibrator | C | 同锚点（原生数组）via `--batch` | 0 | 同上 | 相等 | ✅ |
| window_cc_detector | B | `--tool window_cc_detector`（零专属参数） | 0 | 3 候选：RECT_A(bbox=[900,750,920,765],area=300)、RECT_B(同规格 area=300)、十字块(bbox=[50,50,750,650],area=12900) | 相等（两个已知矩形精确命中 + 第三候选如实记录，非歧义） | ✅ |
| window_cc_detector | A | 同上 via `--request` | 0 | 同上 | 相等 | ✅ |
| window_cc_detector | C | 同上 via `--batch` | 0 | 同上 | 相等 | ✅ |
| crop_zoom | B | `--bbox 880,730,1000,790`（字符串写法） | 0 | `crop_size_px`=[120,60]，`source_image`=[1200,900] | 相等 | ✅ |
| crop_zoom | A | 同 bbox（**字符串**写法，理由见 §4）via `--request` | 0 | 同上 | 相等 | ✅ |
| crop_zoom | C | 同上 via `--batch` | 0 | 同上 | 相等 | ✅ |
| overlay_logger | B | `--candidates-json '[{"candidate_id":"c1","status":"accepted","reason":"rectA","geometry":{...RECT_A}}]'` | 0 | `decisions`=[{candidate_id:"c1",status:"accepted",reason:"rectA",...}]，overlay PNG 落盘存在 | 相等 | ✅ |
| overlay_logger | A | 同候选（原生数组）via `--request` | 0 | 同上 | 相等 | ✅ |
| overlay_logger | C | 同候选（原生数组）via `--batch` | 0 | 同上 | 相等 | ✅ |

**S-1 结论：18/18 全部 `✅ 通且数对`，且同一工具的 B/A/C 三种形态产出的数值逐字段完全相同**
（`tests/test_substrate_sweep_tools.py` 里每格独立断言，另在探索阶段做过跨形态直接比对，见
`A_evidence/exploration_main_grid_18cells.log`）。这是本轮最重要的正面结论：**F-49/F-51 的修法
（`e0367e1`）在主表层面是扎实的，六个工具的三种调用形态目前都是通的**。

---

## 2. S-1b：文档示例逐字实跑（主控中途补的一格）

来源：`skills/intake_pipeline/0_reading/cv_toolbox.md` 里全部 7 个 ` ```bash ` 代码块，逐字提取
（未做任何改写），在真 staging（sm21_anchor 建出、含真实 `1f_view.png`/`South_view.png`）里用
真 shell（`subprocess.run(cmd, shell=True, ...)`，忠实还原"读图器把代码块粘进 Bash 工具"的体验，
包括行末反斜杠续行）逐条跑。

| # | 命令原文（逐字） | 退出码 | 产物里的实际值 | 判定 |
|---|---|---|---|---|
| doc_1 | `--tool wall_line_profiler --image case_data/1f_view.png --out-dir out/cv --axis col` | 0 | 29 候选（真实图纸，无构造真值，仅烟测） | ✅ |
| doc_2 | `--tool crop_zoom --image case_data/1f_view.png --out-dir out/cv --bbox 120,80,620,460 --scale 2` | 0 | `crop_size_px`=[1000,760]（=(620-120)×2, (460-80)×2，精确） | ✅ |
| doc_3 | `--tool px_m_calibrator --image case_data/1f_view.png --out-dir out/cv --anchors-json '[{"axis":"x","px_a":100,"px_b":700,"value_m":15.0,...}]'` | 0 | **`px_per_m`=40.0**（=600/15，精确） | ✅ |
| doc_4 | `--tool window_cc_detector --image case_data/South_view.png --out-dir out/cv --min-area 30` | 0 | 68 候选（真实图纸，无构造真值，仅烟测） | ✅ |
| doc_5 | `--batch requests/<name>.json`（占位符原样，含尖括号） | **2** | `/bin/sh: 1: cannot open name: No such file` | ⛔（见 F-53，占位符语义问题，非工具本身缺陷） |
| doc_6 | `python -c 'import numpy as np; from PIL import Image; print(...shape)'` | 0 | stdout=`(1345, 2133)`（1f_view.png 的真实 H×W） | ✅（**注**：不经过 wrapper，只测环境能否执行；guard.py 是否放行属摊 B 范围，本单不测） |
| doc_7 | `python out/measure_bay_spacing.py` | 1 | `can't open file ...: No such file or directory` | ⬜ 不适用——文档原文明写"write it, then run it"，该脚本本就该由读图器自己先写，全新 staging 上不存在是**预期行为**，非缺陷 |

**doc_3 特别重要**：这正是 F-49 点名"文档与 wrapper 自带 usage 写的两种形态全都跑不通"的那一条
文档示例。今天逐字重跑，**不仅退出码 0，`px_per_m` 算出来精确等于文档隐含的 40.0**（锁在
`test_doc_example_px_m_calibrator_runs_and_computes_the_documented_scale`，特意断言了数值而不
是只看退出码——避免"修到看起来没崩但算错了"被判定为通过）。

**doc_5 是本单新发现的缺陷（F-53），是 F-45 同族的第二种触发机制**：F-45 挡在"guard 按命令形态
DENY"；这条挡在**shell 元字符**——`<name>` 里的 `<` 和 `>` 是真实的 shell 重定向操作符，逐字粘贴
时 shell 会把它解析成"用名为 `name` 的文件做 stdin、把 stdout 写到名为 `.json` 的文件"，而不是
把 `requests/<name>.json` 当一个整体路径串。报错 `cannot open name: No such file` 对一个不熟悉
这个坑的读图器来说完全指错方向。详见 §5。

---

## 3. S-2 参数形态表（优先子集，非全 51 格穷举）

按时间预算，优先覆盖了：①被点名的候选缺陷（bbox）②与 F-49 同族、最该复核的两个（anchors_json /
candidates_json）③一个跨工具通用机制的代表样本（scale 的 int/float/string 等价性、window 10 个
过滤参数的 native/string 等价性）。

| 参数 | 写法 | 形态 | 退出码 | 结果 | 判定 |
|---|---|---|---|---|---|
| `bbox` | 原生 JSON 数组 `[880,730,1000,790]` | A（`--request`） | **2** | `argument --bbox: invalid _bbox value: '[880,730,1000,790]'` | ⛔（**F-52**） |
| `bbox` | 原生 JSON 数组 `[880,730,1000,790]` | C（`--batch`） | **2** | 同上 | ⛔（**F-52**） |
| `bbox` | 字符串 `"880,730,1000,790"` | A | 0 | `crop_size_px`=[120,60] | ✅（对照组，证明只是这一种写法坏） |
| `bbox` | 字符串（本就是唯一形态） | B | 0 | 同上 | ✅ |
| `anchors_json` | 原生 JSON 数组 | A/C | 0 | 见 S-1 主表 px_m_calibrator | ✅ |
| `anchors_json` | 内联 JSON 字符串 | A | 0 | `px_per_m`=40.0 | ✅ |
| `anchors_json` | 文件路径字符串（先写 `requests/xxx.json` 再传路径） | A | 0 | `px_per_m`=40.0 | ✅ |
| `candidates_json` | 原生 JSON 数组 | A/C | 0 | 见 S-1 主表 overlay_logger | ✅ |
| `candidates_json` | 文件路径字符串 | A | 0 | `decisions[0].candidate_id`="c1" | ✅ |
| `scale` | int `2` / float `2.0` / string `"2"`（A 形态）+ string `"2"`（B 形态） | A×3 + B | 0（全部） | 四种写法的 `crop_size_px` 全部等于 `[240,120]` | ✅（四写法等价） |
| window 10 个过滤参数 | 原生 int/float 一次性组合调用 | A | 0 | — | ✅ |
| window 10 个过滤参数 | 字符串数字一次性组合调用 | A | 0 | 与原生调用的 `results` 逐字段相等 | ✅ |

**S-2 结论**：除了 §4 详述的 `bbox` 这一个真实缺陷（F-52），`anchors_json`/`candidates_json`
（F-49 那一族最该复核的参数）三种写法全部正常，`scale`/window 过滤参数的 native-vs-string 也
全部等价——**F-49 的修法（`JSON_OR_PATH_KEYS` 分支）本身是扎实的，问题只在于它没有覆盖到
`bbox`**（`bbox` 不在 `JSON_OR_PATH_KEYS` 里，落进了 `_request_to_argv` 的通用
`isinstance(value,(dict,list))→json.dumps` 分支，而 `cv_probe._bbox` 用朴素逗号切分解析，
两者不兼容）。

**未做的部分**（诚实列出，避免"做了代表样本"被误读成"穷举过"）：`recipe`/`sidecar_name`/`axis`
/`residual_warn_px`/`residual_warn_m` 这几个专属参数只在主表和探索阶段各验证过 1–2 次（均正常，
见 `A_evidence/exploration_s2_priority_cells.log`），未对每一个都补三种写法的正式锁；window 的
10 个过滤参数没有逐个单独测（只测了"全部一次性传入"这一种组合，覆盖了机制但不是逐参数覆盖）。

---

## 4. §3.3 候选缺陷裁定：**成立**（登记为 F-52）

**机制**（读代码 + 实跑双重确认）：

`src/agent/execution/isolation_templates/run_cv_probe.py::_request_to_argv` 对每个参数按角色
分流：`OUTPUT_ROLE_KEYS`（仅 `out_dir`）→ 解析成可写根路径；`JSON_OR_PATH_KEYS`（仅
`anchors_json`、`candidates_json`）→ 原生数组/对象就 `json.dumps` 成内联 JSON 字符串，字符串
且不以 `[`/`{` 开头就当路径解析；`PATH_KEYS`（`image`、`out_dir`、`anchors_json`、
`candidates_json`）→ 路径解析；**其余任何键**，只要值是 `list`/`dict`，一律落进通用分支
`json.dumps(value, separators=(",",":"))`。

`bbox` **不在** `JSON_OR_PATH_KEYS` 里（该集合硬编码只有那两个键），所以
`"bbox":[880,730,1000,790]` 落进最后这个通用分支，被序列化成**一个 CLI token**
`"[880,730,1000,790]"`。而 `scripts/tool_scripts/cv_probe.py::_bbox` 的解析是：

```python
def _bbox(value: str) -> list[float]:
    parts = [float(part) for part in value.split(",")]
    ...
```

`"[880,730,1000,790]".split(",")` 得到 `["[880", "730", "1000", "790]"]`，`float("[880")`
直接抛 `ValueError`，argparse 接住后转成 `parser.error`，进程以退出码 2 终止。

**实跑证据**（`tests/test_substrate_sweep_tools.py::test_s2_bbox_native_json_array_form_a` /
`_form_c`，两把 `xfail(strict=True)` 锁）：

```
$ python tools/run_cv_probe.py --request requests/xxx.json   # {"tool":"crop_zoom","args":{...,"bbox":[880,730,1000,790]}}
退出码: 2
usage: run_cv_probe.py crop_zoom [-h] --image IMAGE --out-dir OUT_DIR [--recipe RECIPE] [--bbox BBOX] [--scale SCALE] [--sidecar-name SIDECAR_NAME]
run_cv_probe.py crop_zoom: error: argument --bbox: invalid _bbox value: '[880,730,1000,790]'
```

`--batch` 形态复现一致。**对照组**（`bbox` 写成字符串 `"880,730,1000,790"`）在 A/B/C 三种形态下
全部正常（S-1 主表 crop_zoom 那一行、S-2 表里的对照组行），证明缺陷精确定位在
"`bbox` 的原生 JSON 数组写法"这一种情况，不是 `crop_zoom` 或 `bbox` 参数整体坏了。

**与 F-49 的关系**：同族——都是"某个参数的自然 JSON 写法在 wrapper 里跑不通"，且诊断出的根因
形状完全一致（该参数没被放进能正确处理数组/对象的分支）。区别在于 F-49 影响的是
`px_m_calibrator`/`overlay_logger` 的**唯一必需参数**（工具完全不可用），F-52 影响的是
`crop_zoom` 的**唯一必需参数**——crop_zoom 同样因此在 A/C 形态 + 原生数组写法下完全不可用，
但由于 dispatch 表格里 bbox 有"字符串写法"这条退路且退路是可发现的（B 形态本来就只能是字符串，
容易类推到 A/C 也用字符串），破坏性比 F-49 当时略低，但**仍是同一等级的"自然写法不通"问题**。

---

## 5. 缺陷清单（F-52 起，⛔ 均未修，仅登记）

### F-52 —— `bbox` 参数的原生 JSON 数组写法在 A/C 形态下崩溃

- **现象**：A（`--request`）与 C（`--batch`）形态下，`"bbox":[x0,y0,x1,y1]`（原生 JSON 数组，
  dispatch §3.3 表格里标 ⚠️ 的"自然 JSON 写法"）导致 `cv_probe` argparse 报
  `argument --bbox: invalid _bbox value` 并以退出码 2 终止；同一参数写成字符串
  `"x0,y0,x1,y1"` 完全正常。
- **复现命令**：
  ```
  echo '{"tool":"crop_zoom","args":{"image":"case_data/<img>.png","out_dir":"out/cv","bbox":[100,80,700,460]}}' > requests/r.json
  python tools/run_cv_probe.py --request requests/r.json
  # 退出码 2: argument --bbox: invalid _bbox value: '[100,80,700,460]'
  ```
- **影响面**：`crop_zoom` 是本仓 CV 工具箱里**唯一以 `--bbox` 为必需参数**的工具（`cv_probe.py`
  的 `parse_probe_args` 显式检查 `if args.tool == "crop_zoom" and args.bbox is None: parser.error(...)`），
  且 `bbox` 也是 6 个公共参数之一、window_cc_detector/wall_line_profiler/storey_line_profiler/
  px_m_calibrator 都能选用它来限定分析区域——任何工具只要用 A/C 形态 + 原生数组写 `bbox`
  都会撞这条。
- **⛔ 不要修**。
- **对应锁**：`test_s2_bbox_native_json_array_form_a`、`test_s2_bbox_native_json_array_form_c`
  （均 `xfail(strict=True)`）。

### F-53 —— 文档 `--batch requests/<name>.json` 占位符字面粘贴时被 shell 误解为重定向

- **现象**：`skills/intake_pipeline/0_reading/cv_toolbox.md` 第 53 行的示例
  `python tools/run_cv_probe.py --batch requests/<name>.json` 如果被逐字复制进一个真实
  shell（包括 Claude 的 Bash 工具，其底层就是 `bash -c "<command>"`），`<` 与 `>` 会被
  shell 当作真实的输入/输出重定向操作符解析，而不是文档约定俗成的"占位符尖括号"。命令实际
  变成：`python tools/run_cv_probe.py --batch requests/`，stdin 重定向自文件 `name`
  （不存在），stdout 重定向到文件 `.json`。报错 `cannot open name: No such file` 与真实
  问题（缺少批量请求文件）毫无关联，读图器据此排障会被引向错误方向。
- **复现命令**：
  ```
  cd <staging_root>
  python tools/run_cv_probe.py --batch requests/<name>.json
  # /bin/sh: 1: cannot open name: No such file
  ```
  （用 argv 列表形式绕开 shell 直接调用同一命令，行为不同——`FileNotFoundError`，见下方
  F-54 的复现命令，证实问题确实出在 shell 层而不是 wrapper 本身）。
- **影响面**：仅这一处文档示例（`cv_toolbox.md` 里唯一含尖括号占位符的可执行代码块）；
  与 F-45（doc 示例在 guard 层被 DENY）同族但机制不同——**F-45 挡在 guard 的命令形态白名单，
  F-53 挡在 shell 的元字符解析，guard 和 wrapper 都不参与、也管不到**。
- **⛔ 不要修**。
- **对应锁**：`test_doc_example_batch_placeholder_is_not_shell_safe`（`xfail(strict=True)`）。

### F-54 —— `run_cv_probe.py` 自身的 `main()` 对 `--request`/`--batch`/直接参数解析零异常兜底

- **现象**：`tools/run_cv_probe.py::main()` 里，`_direct_to_request`、`_request_to_argv`、
  `--request`/`--batch` 的文件读取（`_resolve`、`Path.read_text`、`json.loads`）全部**没有
  包在任何 try/except 里**。这些函数抛出的 `ValueError`/`OSError`/`json.JSONDecodeError`
  会以**未捕获的 Python 完整堆栈**（退出码 1）冒出来，而不是像 `cv_probe.py` 自己的
  argparse 路径那样给出干净的 `parser.error()` 文案（退出码 2，`usage: ...` + 一行错误）。
- **复现命令**：
  ```
  python tools/run_cv_probe.py --tool wall_line_profiler --
  # 退出码 1，完整 Python Traceback，最后一行 ValueError: probe parameter name is empty
  ```
- **影响面**：`main()` 里**所有**验证失败路径（畸形直接参数、`--batch`/`--request` 指向
  不存在的文件等）。**在被 guard.py 保护的产品路径下几乎不可达**——guard 自己的
  `_check_probe_wrapper`（`isolation_templates/guard.py`）会在 Bash 工具调用真正执行前，
  用同一批异常类型（`OSError, ValueError, json.JSONDecodeError`）先做一次干净校验并拒绝，
  wrapper 根本不会带着坏输入被启动。但**只要有任何调用方绕开 guard 直接跑 wrapper**（本单
  自己的测试方法论正是如此——dispatch 明令"真 staging + subprocess 跑 staged wrapper"、
  ⛔ 不许经 guard），这个缺口就是真实、可复现的。
- **⛔ 不要修**。
- **对应锁**：`test_s2_wrapper_validation_errors_are_clean_not_raw_tracebacks`
  （`xfail(strict=True)`）。

---

## 6. S-3 坐标系（3 项，全部完成）

### (1) 六工具的 sidecar 都必须回报源图真实尺寸

**结论：成立，六工具全部正确**。`test_s3_source_size_reported_by_every_tool`（对 6 个工具各跑
一次最小调用，其中 crop_zoom 额外带 `--bbox` 限定裁切区域）逐一断言
`source_image.width_px/height_px == 1200/900`（夹具真实尺寸），六个全部通过。neuter 2（见 §7）
把 `write_sidecar` 的宽度砍半后，六个工具的这条断言**同时**变红，反向证实六者共用同一个收口点
`write_sidecar`，不是"六份各自实现、恰好都对"。

### (2) `crop_zoom` 带 `--bbox` + `--scale` 时，sidecar 报的仍是源图尺寸 + crop chain 可反解

**结论：两半都成立**。
- 源图尺寸不受裁切影响：`crop_zoom --bbox 880,730,1000,790` 报 `source_image`=[1200,900]（非
  裁切后的 [120,60]）；`--bbox 50,50,750,650 --scale 3` 同样报 [1200,900]（非裁切放大后的
  [2100,1800]）。
- **反解验证**（用夹具里已知的竖线位置）：对同一个 `--bbox 50,50,750,650 --scale 3` 窗口跑
  `wall_line_profiler --axis col`（该工具内部用 crop chain 同款的
  `_source_coord(local, offset, scale)` 公式把候选换算回源坐标），报出的两条线位置为
  **100.33 / 700.33**，与真值 100/700 相差 **0.33 px**，**在 dispatch 要求的 ≤1px 容差内**。
  该 0.33px 偏差已定位成因（记录于探索日志，非缺陷）：最近邻插值把 5px 宽的线放大 3 倍后，
  FWHM 质心估计相对"精确的 3× 中心点"产生了亚像素量级的量化偏移，量级完全符合最近邻放大的
  已知数值特性。**本单未把这 0.33px 登记为缺陷**——它在声明的容差带内，且有可解释、非随机的
  数值成因。测试见 `test_s3_crop_scale_roundtrip_within_one_pixel`（容差 `abs=1.0`）。

### (3) overlay PNG 在哪个帧——不预设，实测记录

**结论（开放问题已实测封闭）：overlay PNG 永远是源图帧，与 `--bbox`/`--scale` 无关。**

读代码 + 实测双重确认：`cv_probe.py::execute_probe` 与 `_write()` 里，**所有**六个工具调用
`overlay_logger()` 时传入的都是 `args.image`（原始源图路径），不是裁切/缩放后的图；候选几何
（`_line_results`/`window_cc_detector` 等）在写入 overlay 之前已经用 `_source_coord` 换算回
了源坐标系。实测三种代表形态（`crop_zoom` 带 bbox、`wall_line_profiler` 带 bbox+scale、
`overlay_logger` 本身不带 bbox）产出的 overlay PNG 尺寸**全部等于源图尺寸 [1200,900]**，与
是否裁切无关（测试 `test_s3_overlay_png_is_always_in_the_source_frame`，parametrize 三种
工具形态）。

**附带澄清（同一个开放问题的另一半，dispatch 没直接问但答案是这条调查的直接推论）**：
`crop_zoom` **还会**额外产出一个 `..._crop.png` 文件（与 `..._overlay.png` 是两个不同文件），
这个才是真正的裁切局部帧——尺寸等于 `crop_size_px`（本例 [120,60]），实测像素内容也确认了：
在已知竖线源坐标 x=100 对应的裁切局部坐标处取样为灰色，偏移开的位置为白色。见
`test_s3_crop_png_is_in_the_crop_local_frame_not_source`。

---

## 7. 锁清单

`tests/test_substrate_sweep_tools.py`：**47 个测试用例，43 正锁 + 4 `xfail(strict=True)`**。

| 分组 | 数量 | 说明 |
|---|---|---|
| S-1 主表 | 18 正锁 | 6 工具 × `@pytest.mark.parametrize("form", ["B","A","C"])` |
| S-1b 文档示例 | 6 正锁 + 1 xfail | doc_1/2/3/4/6/7 正锁，doc_5（F-53）xfail |
| S-2 参数形态 | 8 正锁 + 2 xfail | bbox 对照组/anchors_json/candidates_json/scale×4/window 过滤参数 正锁；bbox 原生数组×2（F-52）xfail |
| S-3 坐标系 | 11 正锁 | 六工具尺寸×6 + roundtrip×1 + overlay 帧×3 + crop 局部帧×1 |
| F-54 | 1 xfail | wrapper 裸栈 |
| **合计** | **43 正锁 + 4 xfail = 47** | 真实 pytest 输出：`43 passed, 4 xfailed in ~47-52s` |

`pytest tests/test_substrate_sweep_tools.py -n0 -q` 已本地跑通，产物见
`A_evidence/pytest_final_verbose_run.txt`。

### neuter（3 把，全部超额完成"至少 3 把"要求，逐条 git diff 复核零残留）

详细过程见 `A_evidence/neuter_log.md`；摘要：

| # | 目标文件/函数 | 改动 | 打红的锁 | 还原后 `git diff --stat` |
|---|---|---|---|---|
| 1 | `tools.py::px_m_calibrator`，`px_per_m` 公式加 `+1.0` | 1 行 | 5 个：主表 px_m_calibrator×3 形态 + doc_3 + S-2 anchors_json 路径写法，恰好覆盖所有摸到同一段公式的锁 | 空 |
| 2 | `sidecar.py::write_sidecar`，`source_width_px` 砍半（`//2`） | 1 行 | 10 个：S-3 六工具尺寸检查全部 + 主表 crop_zoom×3 形态 + roundtrip 检查，与"六工具共用一个收口点"的判断完全吻合 | 空 |
| 3 | `tools.py::window_cc_detector`，`area_px` 加 `+7` | 1 行 | 3 个：主表 window_cc_detector×3 形态，精确、无连带 | 空 |

三轮 neuter 结束后跑全量：`43 passed, 4 xfailed`（与 neuter 前完全一致），`git status --short -- src/`
干净。**判据满足**：三把锁都是"改坏了实现就真的变红"，不是形状匹配。

---

## 8. 没做完的格子

按优先级（主表 > S-3 > S-1b > S-2）交付，S-2 参数形态表**未穷举**，具体缺口：

1. **未逐参数补写法锁**：`recipe`、`sidecar_name`、`axis`、`residual_warn_px`、
   `residual_warn_m` 这 5 个专属参数只在探索阶段各验证了 1–2 种写法（均正常，见
   `A_evidence/exploration_s2_priority_cells.log`），未对每个都补齐"B 字符串 / A 原生 /
   A 字符串"三种写法的正式 pytest 锁。
2. **window_cc_detector 的 10 个过滤参数未逐个单独测**：只测了"全部一次性以原生类型传入"
   vs"全部一次性以字符串传入"两种组合调用（验证的是共享的"其余键一律 `str()`"机制本身，
   而非每个参数独立生效），未逐参数拆开单独验证边界值。
3. **B 形态下 `anchors_json`/`candidates_json` 的"内联 JSON 字符串"写法**只在 S-1 主表
   （B 形态本就用这个写法）验证过，未额外补"B 形态 + 文件路径字符串"这一种组合的正式锁
   （探索阶段验证过 wrapper 机制对称，但没转成正式测试）。
4. **`image`/`out_dir` 的"绝对路径"写法未测**（dispatch 参数表只列了"相对路径"一种，本单
   也只测了相对路径，绝对路径在 staging 场景下是否等价未验证）。

以上均为**参数形态表（S-2）的深度覆盖缺口**，⛔ 不影响 S-1 主表、S-1b 文档示例、S-3 坐标系
三项已 100% 完成的结论。
