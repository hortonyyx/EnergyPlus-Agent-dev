# 债 D-1 退役 · 双份代码转单份（2026-08-25）

- **派工单**：`../reviews/request/2026-08-25_d1_duplicate_code_retirement_dispatch.md`
- **施工**：GLM 家族执行档（worktree `/workspaces/ep_d1_retire` @ `fa8e597`）· **审**：GPT 家族（另开）
- **做了什么**：2026-08-23 实验目录 `tools/` 下 6 个已有 src 对应件的文件，替换为
  **转发壳**（自举 sys.path → `import` src 权威件 → 把其命名空间含私有名全量搬入 →
  `__main__` CLI 委托 src 件的 `main`）。壳不含任何函数/类定义 ⇒ 逻辑只剩 src 一份，
  「改一份忘另一份」的结构性风险消失；所有历史路径（`from plan_ink import ...` 平铺
  import、`spec_from_file_location` 按路径加载、`python3 tools/xxx.py ...` 子进程 CLI）
  原样可跑，**夹具与历史命令零改动**。

## 退役映射（6 对，AST 签名扫描证实无第 7 对）

| tools 壳 | src 权威件 |
|---|---|
| `as_drawn_v2.py` | `src/agent/reading/as_drawn/as_drawn_v2.py` |
| `plan_ink.py` | `src/agent/reading/as_drawn/_plan_ink.py` |
| `ink_palette.py` | `src/agent/reading/as_drawn/pens.py`（转正时改名）|
| `checks_as_drawn_v2.py` | `src/validator/checks/as_drawn.py`（转正时改名）|
| `reading_grade.py` | `src/agent/judge/as_drawn/reading_grade.py` |
| `denominator.py` | `src/agent/judge/as_drawn/denominator.py` |

## 机械判据：`verify_no_logic_duplicate.py`

- **(a) 函数体指纹零交集**：tools↔src 全量 .py 的函数级规范化 AST（剥 docstring）
  哈希比对，相交 = 同一段逻辑两处。
- **(b) identity 转发**：以夹具同款 `spec_from_file_location` 加载每个壳，其命名空间
  每个非 dunder 名与 src 件 `is` 同一对象，且壳无自有公共名。
- **(c) 壳零顶层 def/class**。
- **`--baseline HEAD` 模式** = 分辨力自证：对改前版本必须恰好报出 6 对 DUPLICATE
  （实测 YES）。
- **v1 档案血统豁免（显式、点名、非静默）**：判据比派工单清单多抓到 2 对——
  `as_drawn.py` / `as_drawn_elev.py` 各有 1 个 `_chain_zero_px` 与 v2 同体。
  它们是 v1 演进前身（无 src 对应件；转正只收了 v2 链），其中 as_drawn.py 里还是
  嵌套局部函数，是历史快照的一部分；不存在「两个可改份」（v1 档案没有现行链路以
  它为源，无被改动机）。豁免打印进输出，边界 = `RETIRED` 键集，机械可判。

## 改前/改后行为对比

- 四个夹具（`glm_cheats` / `glm_probes` / `glm_sweeps` / `run_all`）改前、改后各跑一遍：
  stdout 数值逐项一致；out 产物逐文件比对，除一个文件外逐字节相同。
- 唯一例外 `out/sm24_1f_GLM_band_to_two_edges.json`：差异全部是 `"F0"`/`"F1"` 键序
  互换，**递归排序键后完全等价**。键序漂移源自 `reconstruct_check_v2.py`（不在本单
  6 件内、未改动）的 dict 迭代序受 PYTHONHASHSEED 影响的跨进程不稳定性——改前
  两次跑之间同样漂（git 历史可证），与壳无关。

## 撞出并修复的一处：glm_rework.py 的源码文本手术

壳化首跑 run_all 时 `RESULTS_v2.json` 的 `glm_rework` 段变成
`{"error": "glm_rework.py exited 1"}`——**glm_rework（第五轮审的系数扫描夹具，run_all
每次必跑）在 `_grade_with_coeff` 里读 `tools/reading_grade.py` 的源码文本**，断言其中
含 `ln["width_m"] < WIDTH_COEFF * need`（六审 Finding 2 的防漂移守卫），把系数替换进
文本后 exec 出临时判分器扫系数。壳不含该文本 ⇒ 守卫红。

修法 = 与 `run_all.py:214-216` 转正时的先例完全同款：`glm_rework.py` 改读
`src/agent/judge/as_drawn/reading_grade.py`（src 件 175 行逐字含守卫锚文本，守卫依然
成立；这是全 tools 目录唯一一处对 .py 源码的文本级读取）。修复后 glm_rework 单跑
通过（系数扫描表、`launder_non_wall` C1 95.7→54.3、strip stats 与改前一致），
run_all 终验重跑恢复完整 RESULTS_v2。

**教训（-feed-the-answer-in 的再证实）**：四个「点名必跑」夹具全绿不够——run_all
内部还会拉起未点名的第五个夹具，其失败以「RESULTS_v2 少一段」的形式静默存在，
是对全部 out 产物做规范化对比才撞出来的。

## 已知残留（如实登记，不静默）

- `reconstruct_check_v2.py` 跨进程键序不稳定（见上）——它是五轮审 gt 侧尺子的证据
  文件，本单不动；若将来要复现逐字节产物，固定 `PYTHONHASHSEED` 即可。
