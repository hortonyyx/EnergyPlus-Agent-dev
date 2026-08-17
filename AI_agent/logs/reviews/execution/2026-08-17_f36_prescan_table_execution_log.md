# F-36 收债 —— `test_b2_prescan_reproduction` 长期红修复执行日志

**席位**：Claude 侧执行档（Sonnet 5 子代理，「清 F-36 旧债」摊）
**派工背景**：全仓唯一长期红 `tests/test_mep_idd_field_alignment.py::test_b2_prescan_reproduction`，
已连红四轮（08-15 / 08-16 ×2 / 08-17），每轮都被前序 orchestrator 判「旧债、与本轮无关」放过；用户 08-17
拍板本摊先清干净。
**改动文件**：仅 `tests/test_mep_idd_field_alignment.py`（`_PRESCAN_GREEN` 集合追加三行 + 注释）。
**未改动**：`src/` 零改动（本摊全程未触到需要改产品代码的情形，故未触发「改 src/ 前先备份」条款）。
**未 commit**：改动停在工作树，等待主控统一提交。

---

## 一、根因 —— 派工单的假设已证实成立

**结论：证实。不是门算错了，是记账没跟上产物。**

时间线（用 git log 精确核对，非记忆推断）：

| 提交 | 时间（UTC） | 内容 |
|---|---|---|
| `fb171ec` | 2026-08-14 07:55:04 | `08.14_B2_prescan_repro_enumerate_via_git_ls_files_not_filesystem_glob` —— 本次红的这份预扫对账表（`_PRESCAN_OBJECT_LEVEL` + `_PRESCAN_GREEN`）最后一次被改动 |
| `dc7b239` | 2026-08-15 05:48:46 | `08.14_WrapUp_ACCEPTANCE_3of3_ACHIEVED_F28_fixed_plus_F32_registered` —— 验收 3/3 收工提交，**把 `run_2026-08-14_accept_D/E/F` 三份产物的 `4_mep/mep_output.json` 一次性入库**（`git show --stat dc7b239` 逐一确认三份的 `4_mep/mep_output.json` 都在这笔提交里新增，`git log` 确认三份此后再未被改动过） |

`dc7b239` 晚于 `fb171ec` ⇒ **表已经定稿之后，产物才入库**，且入库那次提交的说明里完全没提这张表 ⇒
表没有被同步更新，纯粹是漏更新，不是门的判据本身漂移。`src/validator/checks/mep.py` 里 `_idd_field_findings`
（本门的判据实现）自 `1472cfc`（08-14，引入本门那次提交）之后**没有任何提交碰过**（`git log --oneline
1472cfc..HEAD -- src/validator/checks/mep.py` 空输出）⇒ 门本身零漂移，问题**只在表**。

---

## 二、双向对账 —— 完整清单与实际数字

用 `git ls-files -- case_tests/e2e_tests | grep '4_mep/mep_output.json$'` 枚举全部 git 跟踪的 `4_mep`
产物（与被测代码 `_artifact_runs()` 用的是同一条命令、同一份口径），与测试文件里 `_PRESCAN_OBJECT_LEVEL`
（14 条）∪ `_PRESCAN_GREEN`（改动前 6 条）逐条比对，双向：

- **git 跟踪但表里没有（缺分类）= 3 条，且只有这 3 条**：
  - `sm21_anchor/run_2026-08-14_accept_D`
  - `sm21_anchor/run_2026-08-14_accept_E`
  - `sm21_anchor/run_2026-08-14_accept_F`
- **表里有但已不在库中（陈旧条目）= 0 条**：改动前表的全部 20 条（14 红 + 6 绿）逐条核对，全部仍是
  git 跟踪状态，无一失效。
- **红绿两张表之间有无重叠（防止同一 label 被两边同时收）**：0 条重叠。

跟踪产物总数 = 23，改动前表已分类 = 20（14 红 + 6 绿），未分类 = 3 —— **三个数字互相对得上**（23 = 20 + 3），
且未分类的 3 条**正好**是 08-14 验收批那三份，与根因时间线完全吻合，不是巧合。

（附：`smalloffice_23/4_mep/mep_output.json` 仍是唯一的「跟踪外、磁盘上存在」产物，被 `_untracked_mep_outputs`
按既有机制识别并通过 `warnings.warn` 记录跳过原因，不计入本次「缺分类」清单，也不受本次改动影响——运行日志里
仍能看到那条 `UserWarning`。）

---

## 三、每份新分类的实测依据 —— 两种独立方法双重confirm，均为 GREEN

按派工单要求的顺序（先测实际、再核预扫判据、两者一致才补表），对三份产物各做了两次独立测量：

**方法 1：直接跑真实门**（`mep.idd_field_alignment` via `check_mep`，与 `test_b2_prescan_reproduction`
本体调用完全同构）：

```
sm21_anchor/run_2026-08-14_accept_D  →  status=PASS   object_level=0   field_level=0   offenders=[]
sm21_anchor/run_2026-08-14_accept_E  →  status=PASS   object_level=0   field_level=0   offenders=[]
sm21_anchor/run_2026-08-14_accept_F  →  status=PASS   object_level=0   field_level=0   offenders=[]
```

**方法 2：独立重跑当初的预扫探针本体**（`AI_agent/logs/experiments/2026-08-14_mep_arity_gate_prescan/
probe_arity.py`，08-14 产出 `prescan_output.md` 用的就是这份脚本，**未被本摊或此后任何提交改过**——
它不依赖 `mep.idd_field_alignment`，是一份独立实现同一套判据〔① IDD `\required-field` 缺失/为空
② 字段数超出 IDD 上限〕的只读脚本，可以在不信任门本身实现的前提下交叉验证）：

```
$ python probe_arity.py 2>/dev/null | grep -A3 "accept_D\|accept_E\|accept_F"
case_tests/e2e_tests/sm21_anchor/run_2026-08-14_accept_D
    objects=67  flagged=0
case_tests/e2e_tests/sm21_anchor/run_2026-08-14_accept_E
    objects=67  flagged=0
case_tests/e2e_tests/sm21_anchor/run_2026-08-14_accept_F
    objects=67  flagged=0
```

两种方法结论完全一致：**三份产物在这道门的判据下干净、零发现，应落绿**。

**回到预扫判据核对方向（派工单步骤 2）**：`prescan_output.md` 与同目录 `README.md` 记录的判据原文
——「用仓里已有的 IDD 元数据……对每个 `*_specs` 解析出的对象查两件事：① 有 `\required-field` 标记的格
是否缺失/为空 ② 字段数是否超出 IDD 上限」——与门的实现（`_idd_field_findings`）、与 `probe_arity.py`
三者是同一套判据的三份独立实现（探针脚本先于门存在，门是后来对同一判据的正式化实现）。按这套判据推演，
一份产物只要没有任何对象缺必填字段、也没有对象字段数超限，就应该落绿——这正是三份产物的实测结果，
**判据推演与实测完全一致**。

---

## 四、实测与预扫判据是否出现不一致 —— 没有

三份新产物的判据推演结论与两种独立实测结论三方一致（探针判据描述 = 门的实现 = 独立探针脚本重跑），
**不存在需要停下上报的「实测 vs 判据矛盾」情形**。

**但有一处值得记录的旁证（不是矛盾，是佐证）**：`AI_agent/plan.md`（08-15/08-16 一轮的非正式记录，
非本次派工单）此前把 F-36 的成因描述为「`accept_D/E/F` 未进 `_PRESCAN_OBJECT_LEVEL`」——即凭直觉认为
这三份应该落**红表**。本摊按派工单「不许假设、必须实测」的要求重新测过，结果是**它们该落绿表，不是红表**
——两次独立方法都不支持红。若不做实测、直接照旧笔记的方向把它们写进 `_PRESCAN_OBJECT_LEVEL` 并瞎猜一个
object-level 数字，测试虽然也会变绿，但会是一次「蒙对了字段名、蒙错了值」的假分类（08-14 验收批那三份产物
本身就是当日「六条全中」的验收通过件，几何 100 面/15 窗/14 区逐位复核过、EnergyPlus 0 Severe——落红反而
才是不合常理的方向）。这正是派工单反复强调「不许为了绿而填表」的具体案例：本摊直觉方向的旧笔记是错的，
实测纠正了它。

---

## 五、全仓数字

**改动前（复现基线，交付前先复现一次报错）**：
```
$ pytest tests/test_mep_idd_field_alignment.py -q
...
Failed: sm21_anchor/run_2026-08-14_accept_D: tracked but not classified in prescan fixture table
1 failed, 10 passed, 1 warning in 12.70s
```

**改动后（本文件单测，`-n auto` 默认并行，非自选并发）**：
```
$ pytest tests/test_mep_idd_field_alignment.py -q
...........
11 passed, 1 warning in 12.93s
```
`test_b2_prescan_reproduction` 额外单独重跑两次确认非偶然通过（各 1 passed，11.14s / 10.74s）。

**全仓（默认调用形态 `pytest -q`，不传 `-n4`/`-m` 等自选参数，交由 `pyproject.toml` 的
`addopts=["-n","auto","--dist","load"]` 决定并发度）**：

```
$ /opt/venv/bin/python -m pytest -q
...
2834 passed, 14 xfailed, 212 warnings in 576.03s (0:09:36)
[exit code 0]
```

**0 failed.** 与派工单给的基线（改动前「1 failed, 2833 passed, 14 xfailed」）精确对上：
2833 + 1 = 2834 —— 唯一那条红转绿后并入 passed 计数，xfailed 数不变（14），没有引入任何新红、
没有让任何原本绿的测试变色。212 条 warning 全部与本改动无关（`test_orchestrate_baseline.py` 的
`run_config.yaml not found` 系列是该文件本有的既存 warning，未改动过的文件；本次改动带来的唯一
warning 是 §5 提到的 `smalloffice_23` 跳过提示，属既有机制，非新增）。

---

## 六、设计问题（只登记建议 + 代价，本摊不实现）

**问题**：这张表手工维护，任何新 `4_mep` 产物入库都会让 `test_b2_prescan_reproduction` 再红一次
——本次是第五次撞见同一形状（前四轮都被判"旧债、跳过"）。有没有低成本办法让「新产物未分类」从硬红
变成可操作的提示？

### 方案 A（推荐立即做，风险最低）：把失败信息从「报名字」升级为「报测量结果 + 现成的表项」

现状：`else: pytest.fail(f"{label}: tracked but not classified in prescan fixture table")`
只报名字，逼着排查者重新走一遍「跑门 → 看结果 → 判断填哪张表 → 手打一行」的全过程（本摊正是这么做的，
花了本文档大半篇幅）。

改法：失败分支里，`al`（`check_mep` 的门结果）在那一行**已经算出来了**，顺手把它拼进报错文本：

```python
else:
    if al.status == CheckStatus.PASS:
        hint = f'    "{label}",  # add to _PRESCAN_GREEN'
    else:
        hint = f'    "{label}": {obj_level},  # add to _PRESCAN_OBJECT_LEVEL'
    pytest.fail(
        f"{label}: tracked but not classified in prescan fixture table.\n"
        f"Measured just now: {'PASS' if al.status == CheckStatus.PASS else f'FAIL, object_level={obj_level}'}.\n"
        f"Suggested line (verify against prescan methodology before pasting):\n{hint}"
    )
```

- **代价**：约 10 行改动，全部在这一个 `else` 分支里，零语义变化（仍然硬红，仍然一份都不许跳过）。
- **收益**：把「排查」压缩成「跑一次测试、看报错、抄一行」，本摊今天手工做的双向对账 + 双方法测量以后
  单份新产物场景下可以直接从报错文本里读到，不必重新展开。
- **不改变的东西**：门仍然是硬红（不解决"每次新增产物都要来补一行"这件事本身的存在，只是让补的成本
  趋近于零），这是刻意保留——见方案 B 里为什么不建议削弱它。

### 方案 B（更进一步，需要先回答一个治理问题，不建议在没有配套约束的情况下单独做）：
真正的「待分类清单」= 未分类产物降级为 warning、不再 hard fail

把 `else` 分支从 `pytest.fail` 改成 `warnings.warn`（仿照现有 `_untracked_mep_outputs` 的处理方式），
未分类产物连同实测结果一起进一个非阻断的清单。

- **代价 / 风险**：这道门存在的本意（docstring 原文）是「对账门 —— 保证这道 MEP 字段校验门的判据没有
  偏移」，其隐含的强制力来自"任何新产物都必须被人看一眼、显式归类"——它不只是复现旧结论，也顺带充当
  "新产物落库时必须有人确认过这道字段对齐门对它说什么"的强制检查点。降级为 warning 之后：
  1. 新产物可以无限期停留在"待分类"状态而不影响 CI/全仓绿——这正是本摊要清理的"四轮被放过"模式的
     制度化版本，只是从"红了但被人为跳过"变成"从不变红、也就没人会去处理"，本质风险更高而非更低；
  2. 需要一个新的强制机制防止"待分类"清单无限增长（比如清单非空时给一条独立的、低成本但仍然会红的
     卫兵测试——但那其实就是把方案 A 的"必须显式补表"绕了一圈又绕回来，复杂度净增）；
  3. 与本仓 memory 里已经吃过亏的"立规则不给合法出口 ⇒ 模型自己发明出口"和"只有负向断言的门 =
     恒红不可观测"两条经验同族——一道不再阻断的门，长期看容易变成没人读的信号（本仓的
     `all_visible_strokes_captured` 字段就是先例：产品自己写了、代码从来没人消费）。
  - **只有在补一条"清单非空即阻断"的配套检查的前提下，方案 B 才不会退化成"关掉了强制力"**，而那样
    做之后，净收益相对方案 A 就只剩"报错信息挪到了另一个文件里"，工程量明显更大、风险不明显更低。
  - **本摊结论：建议先落地方案 A（零风险、即时见效）；方案 B 是否值得做，取决于是否愿意为它配一条
    新的强制检查——这是一个治理决策，不是纯粹的工程优化，留给用户/主控另行拍板。**

以上两案均**未实现**，仅登记于本文件。

---

## 七、纪律自查

- ⛔ 未 commit（等主控统一提交）。
- ⛔ 未跑 `pip install -e`；全程使用 `/opt/venv/bin/python`。
- `src/` 零改动 ⇒ 未触发「改 `src/` 前先备份到 `backup/src_history/2026-08-17_f36/`」条款，该目录未创建。
- 未发生「实测判定与预扫判据矛盾」的情形，故未触发「停下上报」；本文件全程走「记录后继续」路径。
- 派工方错误率登记：本摊派工单的两处核心假设（「根因 = `dc7b239` 带入未同步表」「判据 = required-field
  缺失 + 字段数超限」）经独立核实**均成立**，没有需要证伪的条目。唯一需要指出的方向性错误来自**更早一轮**
  （08-15/08-16 记在 `plan.md` 里的非正式笔记，猜测 accept_D/E/F 该落红表），已在第四节说明并更正，
  不计入本次派工方的错误率（那不是本次派工单的内容）。
