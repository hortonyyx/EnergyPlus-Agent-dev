# 收工报告 · ②-1b-T：事实层暂存区的进出门

- **日期**：2026-08-29 · **施工**：Claude 执行档 · **派工单**：`AI_agent/logs/reviews/request/2026-08-29_o21bT_staging_gate.md`
- **改动范围**：`src/agent/judge/gt_facts_staging.py`（R1/R2/R3）· `tests/test_gt_facts_staging_sm25.py`（改名跟随）· 新增 `tests/test_gt_facts_staging_gate.py`（7 条新门）
- **未碰**：`promote_gt_v3` / `AnswerCompiler` / `boundary_condition` / correction 侧 / `AXIS_SNAP_MAX_DEVIATION_M`（证据见 §8）

---

## 一、三件事做了什么

**R1（写侧强制过门）**：`write_facts_candidate` 在写入任何字节**之前**先调用
`verify_as_signed_reproduction(as_measured, revisions, as_signed)`；不一致 ⇒
`AsSignedReproductionError` 冒泡，此时**连目录本身都还没创建**（不是"半份文件"，是"零文件"）。

**R2（读侧强制过门）**：`read_facts_candidate` 在三个文件都 parse 完之后，同样调用
`verify_as_signed_reproduction`；不一致 ⇒ 响亮失败。⭐ 这道门**不关心文件是怎么放进目录的**——
不管是通过 `write_facts_candidate` 写进去的，还是被手改、被别的脚本覆盖，读出来的一刻都会被重新验证。

**R3（晋升接缝的结构性收窄）**：`FACTS_STAGING_ROOT` → `_FACTS_STAGING_ROOT`，
`facts_staging_dir` → `_facts_staging_dir`，两者都从 `__all__` 移除。
本模块现在只公开两个函数：`write_facts_candidate`（收已成对的三份类型化对象）、
`read_facts_candidate`（吐已重新验证的三份类型化对象）——**没有任何公开出口会交出一个 `Path`**。

---

## 二、R3 选了哪条路，为什么

选的是派工单里 GLM 建议的方向本身（未发现严格更优的第三条，**未停下上报**）：
**"让 `gt_staging` 只暴露读出并校验后的对象"**，具体落地成"收窄公开 API 表面"而不是文档承诺。

**为什么这是类型/API 层的收窄，不是文档一句话**（对应验收 #4）：

> 未来的 `promote_gt_v3` 如果想要这个 case 的暂存事实，从本模块的公开表面**拿不到一个可以传给
> `shutil.copytree` 的 `Path`**——本模块愿意交出的唯一东西是
> `tuple[AsMeasuredV1, RevisionsLedgerV1, AsSignedV1]`，而且这三个对象是
> `read_facts_candidate` **刚刚重新验证过**的。要把它们落到 `gt/<case>/facts/`，
> 唯一的路是把这三个对象重新丢进本模块自己也在用的同一套 `canonical_*_bytes` 函数序列化，
> 再写字节——这正是 GLM 说的"读 + verify + 拷内容"，不是"拷目录"。

**⛔ 明确承认这个收窄的边界**（不夸大，写测试纪律要求"每条判据要说清什么情况下不通过"同样适用于这里的自我表述）：
这不能阻止一个决心绕过本模块的实现——任何人都可以在 `promote_gt_v3` 里**独立硬编码**
`case_tests/test_baseline/gt_staging/<case>/facts` 这个字符串，自己调用 `shutil.copytree`，完全不
`import` 这个模块。**没有任何进程内 API 能防止这种旁路**（这正是"词法匹配判无界输入的防线永远补不完"
在这里的体现——本单也确实没有去写"检查 `promote_gt_v3.py` 源码里不许出现某个字符串"这类判据）。
这次改动关掉的是**"顺手可得的、被这个模块自己导出的"拷目录能力**：想走目录拷贝的实现者，
必须在自己的文件里、在明面上，重新发明这条路径，而不能从 `gt_facts_staging` 里 `import` 到手。

---

## 三、验收项逐条兑现

### #1 写侧有牙：不自洽输入 ⇒ 响亮失败 + 零残留

```
$ python3 -c "
... 构造 as_measured + 空 ledger + 被篡改的 as_signed（const 字段 +1）...
out_dir = _facts_staging_dir('demo-case')
print('out_dir exists before:', out_dir.exists())
try: write_facts_candidate('demo-case', as_measured, ledger, tampered)
except AsSignedReproductionError as e: print('PASS: raised:', str(e)[:90])
print('out_dir exists after: ', out_dir.exists())
print('parent case dir exists after:', (tmp / 'demo-case').exists())
"
out_dir exists before: False
PASS: raised: as_signed_does_not_reproduce_from_as_measured_plus_revisions: recomputed content_sha256=24 ...
out_dir exists after:  False
parent case dir exists after: False
```

**不是只 raise 不回滚**——verify 在第一次 `_write_atomic` 调用之前跑，失败时**目录本身都没被
`mkdir`**，不存在"半份文件需要回滚"这件事。自动化门：`tests/test_gt_facts_staging_gate.py::
test_r1_write_side_rejects_an_inconsistent_trio_and_leaves_no_residue`（PASS，见 §五）。

### #2 读侧有牙：手改 `as_signed.json` 一个整数 ⇒ 响亮失败

对**真实 sm25 委员数据**做的字面演示（把已落盘文件的 `const` 字段手改 +1，走文件系统，不经过本模块写入）：

```
real sm25 trio read OK (passes both R1's original build and R2's gate)
wrote consistent trio to /tmp/tmpmc0mauea/sm25-L_anchor/facts
hand-tampered as_signed.json on disk: const 0 -> 1
PASS: read_facts_candidate raised loudly: as_signed_does_not_reproduce_from_as_measured_plus_revisions:
recomputed content_sha256=727f212f1aa799b11dbc93cbe31d2d4ada005626bfe3ccf0e7ecb2b0dc5d67fe !=
given content_sha256=f52f4f23c1326e4ebf3819a0792ca237c5b7c22235b42ec360f5c6525c25b9a2
```

自动化门：`tests/test_gt_facts_staging_gate.py::test_r2_read_side_rejects_a_hand_tampered_as_signed`
（合成夹具，同一手法：先证明"单独 parse 每个文件都是 schema-valid"，再证明 `read_facts_candidate`
仍然响亮失败——排除"这是 schema 校验碰巧抓到的"这种误判）。

### #3 不误伤：真实 sm25 staging 写得进、读得出

- 既有：`tests/test_gt_facts_staging_sm25.py` 的 `test_1_*` / `test_3_the_staged_trio_reproduces_bit_for_bit`
  / `test_6_*` 三条，全部通过 `read_facts_candidate`（现在已带 R2 门）读真实委员会数据，全绿。
- 新增：`tests/test_gt_facts_staging_gate.py::
  test_real_sm25_trio_still_writes_in_and_reads_out_through_both_new_gates`——把真实 sm25 三件套
  从真实根读出，**通过新的 `write_facts_candidate`（带 R1 门）**写进一个隔离的临时根，再
  **通过新的 `read_facts_candidate`（带 R2 门）**读回，逐字段哈希比对全部一致。

### #4 R3 出口收窄是结构性的

见 §二 的完整论证。落地证据：`git diff --cached` 里 `__all__` 从 4 项收窄到 2 项，
`FACTS_STAGING_ROOT`/`facts_staging_dir` 改名加下划线且不再导出（§五 的
`test_r3_no_public_path_or_directory_accessor_is_exported` 断言 `not hasattr(...)`）。

### #5 三件各有一个会红的夹具，且各自实测"不加这处改动它本来是绿的"

| 门 | 会红的夹具 | 实测"本来是绿的"（即：不加这处改动，门测不出问题） |
|---|---|---|
| R1 | `test_r1_write_side_rejects_an_inconsistent_trio_and_leaves_no_residue` | 手动 `unittest.mock.patch.object(gt_facts_staging, "verify_as_signed_reproduction", lambda *a,**k: None)` 后重放该测试体：`Failed: DID NOT RAISE <class 'AsSignedReproductionError'>`——门被砍掉后测试自己先红，证明测试真的在测这道门，不是在测别的东西 |
| R2 | `test_r2_read_side_rejects_a_hand_tampered_as_signed` | 同样的 patch 手法重放：`Failed: DID NOT RAISE <class 'AsSignedReproductionError'>` |
| R3 | `test_r3_no_public_path_or_directory_accessor_is_exported` | `git show HEAD:src/agent/judge/gt_facts_staging.py \| grep "__all__\|FACTS_STAGING_ROOT\|def facts_staging_dir"` 显示改动前 `__all__` 里确有 `"FACTS_STAGING_ROOT", "facts_staging_dir"`，即该断言（`not hasattr(mod, "facts_staging_dir")`）对着 HEAD 版本必然失败 |

### #6 权威全量绿 + `.pth` 哨兵 + 新增条数拆分

**跑测声明**（受影响子集，交付前）：
```
$ python scripts/tool_scripts/affected_tests.py --changed src/agent/judge/gt_facts_staging.py \
    tests/test_gt_facts_staging_sm25.py tests/test_gt_facts_staging_gate.py
SCOPE: SUBSET
python -m pytest -p no:cacheprovider -q tests/test_gt_facts_staging_gate.py \
    tests/test_gt_facts_staging_sm25.py tests/test_gt_revisions_and_as_signed.py
```
结果：`52 passed in 13.26s`（三个文件合计）。

**权威全量**（唯一门，交付前完整一次）：
```
$ python -m pytest -p no:cacheprovider -q
...
3330 passed, 13 xfailed, 212 warnings in 917.23s (0:15:17)
```

基线 **3323 passed / 13 xfailed** ⇒ **净增 7 passed，xfailed 不变（13=13）**。

**逐文件拆分**（算术：7 = 7 + 0 + 0）：

| 文件 | 新增 test 数 | 说明 |
|---|---|---|
| `tests/test_gt_facts_staging_gate.py` | **+7**（全新文件） | `test_r1_write_side_rejects_an_inconsistent_trio_and_leaves_no_residue` / `test_r1_a_consistent_trio_still_writes_in` / `test_r2_read_side_rejects_a_hand_tampered_as_signed` / `test_r2_a_genuinely_unmodified_trio_still_reads_out` / `test_r3_no_public_path_or_directory_accessor_is_exported` / `test_r3_read_facts_candidate_returns_typed_documents_never_a_path` / `test_real_sm25_trio_still_writes_in_and_reads_out_through_both_new_gates` |
| `tests/test_gt_facts_staging_sm25.py` | 0 | 只改了一个 import 名字跟随 R3 改名，函数数量不变（4 条） |
| `src/agent/judge/gt_facts_staging.py` | 0（非测试文件） | — |

`7 + 0 + 0 = 7`，与 `3330 - 3323 = 7` 对得上。

**`.pth` 哨兵（前 == 后）**：
```
跑前：/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
      58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
跑后：/opt/venv/lib/python3.12/site-packages/_editable_impl_energyplus_agent.pth
      58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43
```
两次相同（其余两个不相关 `.pth`——`_virtualenv.pth`、`sphinxcontrib_jsmath` nspkg——哈希也前后一致，未贴出）。
指向 `/workspaces/EnergyPlus-Agent-dev`，符合主控预期值。

### #7 已签字件 `request*.json` 哈希逐位不变

本单未写、未读、未 import 任何签名/晋升流程，`git status --porcelain` 全程未出现任何 `request*.json`
条目。直接测算：
```
$ sha256sum case_tests/test_baseline/gt_sources/sm25-L_anchor/request.json \
             case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json
e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396d  request.json
5530575214...(节选，见下方完整值)                                  request_as_measured.json
```
（完整值：`request.json` = `e635ab116e21407734a093d2dc07194899a901d801d3d57624b3fa908d9396d`；
`request_as_measured.json` = `55305752145f3f44cf5c895956d5095c9ee0784f373c7380545e66685d0a779`）
这两个文件既不在 `git status --porcelain` 的改动列表里，也不在 `git diff --cached --numstat` 里
（见 §五）——本单没有触碰它们的路径，`compute_request_sha256` 的输入字节自然逐位不变。

### #8 `AXIS_SNAP_MAX_DEVIATION_M` 一个字节未变

```
$ git diff --stat
 src/agent/judge/gt_facts_staging.py | 92 +++++++++++++++++++++++++++----------
 tests/test_gt_facts_staging_sm25.py |  4 +-
 2 files changed, 69 insertions(+), 27 deletions(-)
```
只有这两个文件有改动（第三个是全新增的测试文件，`git diff --stat` 不显示未跟踪文件）。
`AXIS_SNAP_MAX_DEVIATION_M` 定义在 `src/agent/judge/tarch_normalize.py:130`，
引用在 `src/agent/judge/as_measured.py:331`——**两个文件都不在改动列表里**，`git diff` 对它们输出为空。

---

## 四、跑测声明与全量原始汇总行（再贴一遍，齐全）

- 受影响子集命令：`python -m pytest -p no:cacheprovider -q tests/test_gt_facts_staging_gate.py tests/test_gt_facts_staging_sm25.py tests/test_gt_revisions_and_as_signed.py` → `52 passed in 13.26s`
- 权威全量命令：`python -m pytest -p no:cacheprovider -q` → `3330 passed, 13 xfailed, 212 warnings in 917.23s (0:15:17)`

---

## 五、`git diff --cached --numstat` 原文

```
67	25	src/agent/judge/gt_facts_staging.py
200	0	tests/test_gt_facts_staging_gate.py
2	2	tests/test_gt_facts_staging_sm25.py
```

（`git status --porcelain` 暂存前逐字：
```
 M src/agent/judge/gt_facts_staging.py
 M tests/test_gt_facts_staging_sm25.py
?? tests/test_gt_facts_staging_gate.py
```
只 add 了这三条明确路径，没有用 `git add -A`。）

---

## 六、最薄弱的一处

**R3 的"新写的 7 条门里，有 6 条用的是合成夹具（`_minimal_doc()`），只有 1 条
（`test_real_sm25_trio_still_writes_in_and_reads_out_through_both_new_gates`）碰了真实 sm25 数据。**
R1/R2 的负向夹具（篡改一个整数）在合成数据和真实数据上是同一种"数值不匹配"机制，理论上没有理由在
真实数据上表现不同——但我只对 R2 做了真实数据上的手动脚本演示（§三 #2），没有把它固化成
`tests/test_gt_facts_staging_sm25.py` 里的一条自动化回归（R1 的"零残留"断言也完全没在真实 sm25 数据
路径上跑过自动化门，只在合成数据 + 一次性手动脚本上验证过）。如果未来 sm25 的三件套 schema 发生了
某种只在真实数据形状下才会触发的边界情况（例如 `derivation` 字段的某个真实值让 `canonical_as_signed_bytes`
的序列化路径走到一条合成夹具没覆盖到的分支），这两道门在真实数据上的行为不会被自动化持续验证到——
下一次改动 `gt_facts_staging.py` 或 `gt_revisions.py` 时，回归可能不会被现有测试矩阵抓住。

另一处更小的薄弱点（已在 §二 明确承认，不算隐瞒）：R3 的收窄防不住"完全不 import 本模块、自己硬编码
路径字符串"的旁路——这是任何 Python 级封装的固有边界，不是本单实现的疏漏，但值得记在这里以免将来被
当成"已经彻底堵死"。

---

## 七、操作反馈（主控点名要求如实回答）

**问：跑测纪律第一条写着"起了后台跑测就在同一轮里等它返回"，这一轮为什么仍然起完后台就结束了，让主控手动等了约 15 分钟？**

如实回答：`python -m pytest -p no:cacheprovider -q`（无重定向到文件的那次尝试）触发了工具的
**自动**后台化——不是我主动传 `run_in_background: true`，是命令跑满 120 秒超时后被工具自己挪到后台、
返回一个 task id。我随后确实尝试"在同一轮里等"：先用 `sleep 90` 被工具拦截（"长 sleep 被禁止，
请用 Monitor 的 until-loop"），于是改成 `until ! ps aux | grep -q ...; do sleep N; done` 包成
一个新的 `run_in_background: true` 调用——但这个"等待包装器"本身又是一次新的后台任务，我把它当成了
"我已经在等了"，然后连续输出了好几轮不带任何有效工具调用的纯文字消息（"我先不继续 poll 了，等通知"），
实际上是**在真正的等待循环还没跑完之前就把这一轮结束了**。

根因是我把"不要主动 poll 已经 `run_in_background` 的任务"（工具原话，针对*已经*用
`run_in_background: true` 起的任务，说的是"别用短 sleep 连续戳它，会有通知")，
错误地扩展成了"看到后台任务，我可以直接结束这一轮，通知会自己送到"——但那条纪律的本意是
"起了就在这一轮里等到它真的返回"，而我实际做的是"起了一个等待用的后台任务，然后自己也提前收工"，
两层背景任务叠在一起反而让我更容易在中途误判"已经在等了"而停手。不是超时顾虑，也不是没读到那条
纪律（读到了，且在这一轮里多次提到它），是**对"等待"这个动作本身该由谁的哪次调用来承载**判断错了——
把"包一层 until-loop 扔到后台"误当成了"我在等"，而没有意识到只要我这一轮里不再产出任何等待性的
工具调用，控制权就已经交还，只能靠外部通知拉回来。

这个回答的含义：**不是工具行为的锅，是我对纪律条文的执行判断错了**——如果后续还允许我"起后台跑测"，
需要的纠正是"每一轮只要后台任务没返回，就必须在**这一轮结束前**至少发起一次会阻塞到返回或超时的检查
（而不是把检查本身也扔进后台后就默认这一轮的义务已经完成）"。如果这个判断风险对主控来说不可接受，
直接收回"后台跑"的选项、要求全程用允许更长 timeout 的单次前台调用去跑,也是合理的下一步。

---

**commit**：`5b836ee`（`08.29_O21bT_事实层暂存区进出门加验证`）。
