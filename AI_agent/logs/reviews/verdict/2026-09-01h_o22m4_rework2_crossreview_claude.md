# 跨家族审 · **②-2 模块 4 第二轮返工**（`wall_compiler` 的 F-1 / N-1）

- **日期**：2026-09-01 · **施工方**：**GLM 家族**（原席位）· **复核方**：**Claude 家族 / orchestrator**（跨家族，恒升一档）
- **被审 commit**：**`ba3303c`** · **被审对象（⛔ 只这一个文件）**：`tests/test_o22m4_wall_compiler.py` **+123 / −0**
  ⚠️ 同 commit 内的 `evidence_contract.py` +187/−50 是**模块 2 的件**，⛔ 不在本单范围（已另派 GLM 审）。
- **审阅方式**：⛔ **不看执行者自述**，只看 ① 原始派工单 ② `git show` diff ③ 我自己跑的变异矩阵。
- **隔离**：全部变异在独立 worktree `/tmp/o22m4_review_orch` 内做，**主树零改动**；
  每次变异后 `git checkout -- src/agent/correction/wall_compiler.py`（⛔ 从未 `git checkout -- .`）。

## 裁决：**APPROVE**（阻断 **0** 条 · 不阻断 **2** 条）

⭐ **返工范围应为【两轮一起】**：返工一轮 `a13120d` (+264) 当时被判 REWORK、**从未过审**，
返工二轮 `ba3303c` (+123) 只是补 F-1/N-1 ⇒ 本裁决覆盖 `a6f5383..ba3303c` 的测试面共 **+387**。
（CLAUDE.md 记的「+387」是对的，但它是两轮之和 —— 我跑了 `git log --numstat` 核过：264 + 123 = 387。）

---

## 一、⭐⭐⭐ 三格判据

> ⛔ ①② 只验证「这个例子修好了」，③ 才验证「**这类**缺陷修好了」。

**每一格都带「这次导入的是哪个文件 + 变异在不在」的自证**，⛔ 因为审阅期间共享 venv 的
`.pth` 曾被改指（原因见 §三），不自证的读数一律作废。

### 格① · 缺陷当时**真在**（父提交 `a6990be` + 复核方 GPT 的 F-1 变异）

```
$ python -c "import src.agent.correction.wall_compiler as m; ..."
IMPORTS FROM: /tmp/o22m4_review_orch/src/agent/correction/wall_compiler.py
MUTATION PRESENT: True

$ python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6
...........................                                              [100%]
27 passed in 6.51s
```
⇒ **逐字复现 GPT 的读数**：注入 `len(candidates)==1 ⇒ 静默自动执行`，**27 条全绿**。缺陷是真的。

### 格② · 返工后**同一变异变红，且红对位置**（`ba3303c`）

```
IMPORTS FROM: /tmp/o22m4_review_orch/src/agent/correction/wall_compiler.py
MUTATION PRESENT: True

E  AssertionError: the axis item vanished from open_items -- a silent auto-execute
   path closed it (F-1's mutation does exactly this)
E  assert 0 == 1
FAILED tests/test_o22m4_wall_compiler.py::test_single_face_genuinely_single_candidate_stays_open
1 failed, 29 passed in 5.55s
```
⇒ **精准红掉新夹具那一条，且只红它。**

### 格③ · ⭐⭐⭐ **换同形输入仍走不通**（本裁决最有分量的一格）

我**没有**重复格②的触发器，而是换成**真实产物本来就有的形状**——
「厚度值唯一、正负两个候选」（⭐ **这正是原 B 锁量的那个代理量**）：

```python
if candidates and len({c.thickness_source.value_m for c in candidates
                       if c.thickness_source is not None}) == 1:
    chosen = next(c for c in candidates if c.symbolic_operation == "OFFSET_POSITIVE")
    wall = wall.model_copy(update={...}); return wall, [], []
```
```
FAILED ... ::test_single_face_genuinely_single_candidate_stays_open
FAILED ... ::test_single_face_unique_thickness_scale_still_requires_a_decision
FAILED ... ::test_single_face_why_not_names_enumerable_offsets_when_candidates_exist
3 failed, 27 passed in 5.27s
```
⇒ ⭐ **换了触发器仍然红 3 条，其中一条正是原来那把 B 锁。**
**这一类的静默收敛被堵住了，⛔ 不只是 F-1 那一个例子。**

---

## 二、验收表逐项读数（⛔ 我自己跑的）

| # | 判据 | 读数 | 结论 |
|---|---|---|---|
| 1 | 永久夹具的产品事实 `len(candidates)==1`，**测试自己先断言候选数** | 源码实测：先 `assert len(opened)==1`、再 `assert len(opened[0].candidates)==1`，**然后**才断言不变量；走**真实入口** `wc.compile_wall_ir`，且只把**真实枚举器**收窄到 `[:1]`（候选的 id / preview / source 全真） | ✅ |
| 2 | F-1 变异 ⇒ 必须红，且红的是验收 1 那条 | 格② | ✅ |
| 3 | **反向变异**（把门焊死）⇒ 必须有锁红 | 让显式裁决一律不生效（`for decision in ()`）⇒ **9 failed, 21 passed，含新夹具本身** | ✅ 它不是「一律开项」蒙混 |
| 4 | `why_not_auto_resolved` 两支各一条锁，各自变异必须红 | 把两支说明**对调** ⇒ **2 failed, 28 passed**，两条锁**各自**红 | ✅ |
| 5 | M7 不许退 · `single_face` 存货 **> 0**（⛔ 不钉 302/16/8/35） | M7 变异（摘掉 open item）⇒ **8 failed, 22 passed**；`single_face` 测试项 **9** > 0 | ✅ |
| 6 | 定向子集全绿 | 未变异基线 `30 passed in 5.26s`；`git status --porcelain` 空 | ✅ |

---

## 三、⚠️ 审阅期间的环境事故（**与被审件无关，但必须记**）

审阅中途共享 venv 的 editable 哨兵从 `58f547fa…4e43` 变成 `e7171c92…0619`，
`.pth` 内容被改指到 `/tmp/o22m2_review_glm`。

**⛔ 我一度判定是 GLM 席位跑了被禁的 `pip install -e .` —— 这个判定是错的。**
我去读了它的会话记录，**20 条 Bash 调用全部只读**（git show/log/diff · grep · sed · ls · cat · sha256sum），
**没有一条 install**。

**真因（判别实验，⛔ 不是推理）**：
```
$ cat .mcp.json
{"mcpServers":{"EnergyPlus-Agent":{"command":"uv","args":["run","python","main.py",...]}}}
$ env | grep UV_PROJECT_ENVIRONMENT
UV_PROJECT_ENVIRONMENT=/opt/venv

--- 实验前 --- /tmp/o22m2_review_glm
$ cd /tmp/o22m4_review_orch && uv run python -c "pass"
      Built energyplus-agent @ file:///tmp/o22m4_review_orch
--- 实验后 --- /tmp/o22m4_review_orch
```
⇒ ⭐⭐⭐ **本项目的 `.mcp.json` 用 `uv run` 起 MCP server，而 `UV_PROJECT_ENVIRONMENT` 全局指向 `/opt/venv`
⇒ 任何以 worktree 为工作目录启动的 claude 席位，都会在启动 MCP server 时把共享 editable 安装改指到那棵 worktree。**
**是我把席位放进 worktree 造成的，⛔ 不是席位违纪。** 已 `uv run` 从主树恢复，哨兵回到 `58f547fa…4e43`。

---

## 四、不阻断 findings（2 条）

### N-1 · **执行方自述与实件不符**：自称「不钉实现文本」，实为**字面子串**断言
提交说明写「N-1 两支解释各补一条锁……**锁写成规则、不钉实现文本**」。
实件断言的是 prose 子串：`"enumerable" in item.why_not_auto_resolved` ·
`"candidate set is empty" not in …` · `"re-perception" in …`。
⭐ **它有牙（验收 4 已实测），失败模式是【假红】不是【假绿】** ⇒ 不阻断；
但改一次措辞就会无故变红，且这类词法判据补不完（同族 [[lexical-guard-cannot-be-completed]]）。
⛔ **派工单验收 4 本身没有要求「不钉实现文本」**，所以这是**自述**的问题，不是交付的问题。

### N-2 · 旧腿第二处候选生成点：**我量到了边界，⛔ 没量完**
`_compile_legacy_trace`（`wall_compiler.py:999`）有第二处 `_offset_candidates` 调用点，本轮夹具没点名它。
**我实测它并非零存货**：把该处候选收窄到 1 ⇒ `test_unknown_basis_with_thickness_still_never_silent_identity` 红
（`1 failed, 29 passed`）。
⛔ **但我没有在那条腿上打完整的「静默自动执行」形状** —— 所以我只能说「候选数方向有存货」，
**不能说「F-1 形状在旧腿上也被堵住了」**。
⇒ ⭐ 归属：**这条腿用户已定要整条拆**（指南 §十之二），**随拆旧腿单一并消失** ⇒ ⛔ 不要求现在补夹具；
拆单里那条「同数量级的新格式夹具顶上」的要求已覆盖它。

---

## 五、复现命令与环境

```
worktree   /tmp/o22m4_review_orch   （detached，主树零改动）
基线       git checkout ba3303c && python -m pytest tests/test_o22m4_wall_compiler.py -q -n 6  → 30 passed
交件前     git status --porcelain → 空
哨兵       58f547fa9433af6eca0e8f362652b78916b13a21fbeab4ef06f1e07e46744e43（已恢复并复核）
```

## 六、我认为派工单哪里写错了
**派工单 §四 验收表写得干净**（是规则、不是现状名单，验收 5 明确写「⛔ 不写死这四个数」）——
这是 08-31 那条题错之后的正确形态，⛔ 无异议。
⚠️ 唯一一处：验收 3 的措辞「把『开项』改成对**所有**候选数都开项」字面上就是**当前行为**，
照字面做变异等于没变。我按其**意图**（防「把门焊死」）改做了「显式裁决一律不生效」，读数见验收 3。
