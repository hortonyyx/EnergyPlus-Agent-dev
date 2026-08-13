# 派工单 · 摊 C —— 闭合 `MAJOR-C1`：标注法观测量不许把整段容差冒充「≈半墙厚」

- **日期**：2026-08-13
- **席位**：GPT 侧执行档（terra）
- **审阅去向**：Claude 侧（orchestrator 轻门 + 中档交叉复核）
- **裁决书依据**：[2026-08-12_round3_full_body_crossreview_sol.md](../verdict/2026-08-12_round3_full_body_crossreview_sol.md) §3.3
- **基线**：`2557 passed / 10 xfailed / 0 failed`（全仓 `-n auto`）
- **⛔ 并行席位警告**：另有一个席位（摊 A）在同一棵工作树上改
  `src/agent/execution/stage_runner.py` / `src/agent/judge/correction_score.py` /
  `scripts/tool_scripts/run_stage.py` / `tests/test_f22_blocker1_core_stamp.py`。
  **你只动 `src/agent/correction/envelope_transform.py`、属于本摊的新测试文件，
  以及 §3.6 明确授权的 `tests/test_c2_b2b_envelope_transform.py` 那两处断言**；
  **⛔ 绝不 `git add -A` / `stash` / `checkout`**（会毁掉对方半成品，已实犯两次）；提交由 orchestrator 统一做。

---

## 0. ⭐ 停止规矩（分层，必须先读）

1. **承重前提错**（错了则本任务方向作废）⇒ **立即停下上报**。
2. **外围论据错**（不改变任务方向）⇒ **报告里写明「派工方这句错了 + 你的实测」，然后把主体做完**。

派工方（orchestrator）历史错误率 **15/15**，§2 每条前提都写了核实方式，**请主动证伪**。

## 1. 要解决的问题（一句话）

这摊活的**全部产品价值**就是让人看见「这张图是按外皮标注还是按轴线标注」。
但 `src/agent/correction/envelope_transform.py:164-177` 的实际分档只有：

```
displacement <= output_precision_m(0.01)      -> axis_line_annotation   （按轴线标注）
displacement <= envelope_reconcile_tol_m(0.30)-> outer_skin_annotation  （按外包标注）  ← 问题在这
displacement >  0.30                          -> exceeds_tolerance
```

⇒ `0.02` / `0.12` / `0.29` **得到同一个解释「按外包标注」**。函数**既没有墙厚输入、也没有半墙厚参考带**，
而「按外包标注」这个结论的语义前提是「位移 ≈ 半墙厚」。
⇒ **报告里那句解释，对整个中间区间的绝大部分都是无证据的。**

## 2. 承重前提（**本摊的岔口已经被我机械核实过，这是本单最重要的一节**）

sol 给了两条可接受修法：**①** 拿不到可信墙厚 ⇒ 中间态改**中性名称**、只报数字不声称标注法；
**②** 给 observer 传入**可信、版本化的墙厚事实**，冻结「接近半墙厚」的显式 band，只有命中才叫 outer-skin。

**⇒ orchestrator 发单前实测：②在本批不可达。按①做。** 证据：

| # | 前提 | 我怎么验的 |
|---|---|---|
| P1 | **生产侧（reading → correction → geometry）根本没有墙厚事实**：`thickness` 在 `src/agent/correction/schema.py`、`src/agent/geometry/*.py`、`src/configs/*.yaml` 里命中数 **全为 0**；correction 层唯一一处 `thickness` 只是 `deterministic.py:597` 的一句注释 | `grep -rn thickness` 逐目录 |
| P2 | reading 那条**通道存在但今天是空的**：真实产物 `run_2026-08-11_continuous_e2e/0_reading/{1f,2f}_view.json` 里 **20 条墙笔画的 `geometry.thickness_m` 全部为 `None`** | 直接读真实产物逐条打印 |
| P3 | **仓内唯一可信墙厚在判卷 / gt 侧**（`judge/gt_manifest.py:123 default_wall_thickness_m`、`judge/gt_schema.py`、天正转换器 `_outer_skin_thickness_m`）⇒ **取用它会违反不变量 #4「gt 铁律」**（gate①/执行器绝不 import gt）| grep + 现状核实：生产侧模块对 gt 的 import 命中数为 **0** |
| P4 | 「让 reading 逐墙填墙厚、correction 判合理性」**是用户 08-11 已拍板的「标注/墙厚/出模」专项内容**，不在本批 | plan.md 〇-B / 〇-C |

**⇒ 本摊任务 = sol 的修法 ①。**
**⚠️ 邀请证伪**：如果你找到一条**生产侧、不 import gt、在这个接缝上真的取得到**的逐墙可信墙厚，
**那 P1–P3 就错了、本摊方向要改** ⇒ 按承重前提错处理，**停下上报**（附实测），⛔ 不要自己改成修法 ②。

## 3. 修法

1. **中间档改中性具名**：不再叫 `outer_skin_annotation`。改成明确表达「非零、在容差内、标注法未知需人工判读」
   的名字（sol 举例 `reconcilable_nonzero_displacement`），**只报数字，不声称标注法**。
2. **四种状态仍必须各自具名** —— 这摊活本来就是为「⛔ 缺席不是信号，除非显式把缺席变成信号」而立的
   （无 intent 会把「按轴线标注(好)」「超容差(最该报警)」「无权威证据(无信息)」压成同一个空白）。
   ⇒ ⛔ 不许把中间档并进别的档、⛔ 不许退化成「有值/无值」二分。
3. **同步改掉声称标注法的所有人类可读文本**：`_ANNOTATION_BASIS_LABEL_ZH` /
   `_ANNOTATION_BASIS_INTERPRETATION_ZH` / `annotation_basis_report()` 里的
   `interpretation_rule` 那段（`:203-212`）—— 它现在逐字把 `0.01 < 位移 <= 0.30` 写成「按外包标注」。
   **文本必须与新语义一致**（这条不是文字工作：判卷/人读报告就是这摊活的唯一出口）。
4. **保持纯观测**：⛔ 不设门、⛔ 不阻断、⛔ 不改任何既有 correction/conflict/unsupported/intent 判定、
   ⛔ 不抛异常、仍然**恰好返回 4 条观测**、仍然**在 intent 生成之前算**。
6. **⭐ 必须改掉两条把错误语义钉住的既有断言（2026-08-13 补，orchestrator 派工错误已更正）**：
   `tests/test_c2_b2b_envelope_transform.py:366-389`（函数名逐字写着
   `test_annotation_basis_names_outer_skin_annotation_at_half_wall_thickness_scale`）
   与 `:455` 的参数化用例 `(0.12, 0.12, "outer_skin_annotation", True)`。
   **这两处正是 `MAJOR-C1` 的锁形态**：它们断言 0.12 m 得到「按外包标注」，且**名字声称是「半墙厚量级」
   而实现里根本没有墙厚输入** ⇒ 与 BLOCKER-1 那把错锁同一形状（**锁越完备，越会把错误的语义固化下来**）。
   ⇒ **本单授权你修改这两处**，并要求：**改写后的测试不得再声称任何它验证不了的「半墙厚」语义**
   （函数名也要跟着改）。⛔ 除这两处外，仍不许动其它席位的文件。
7. **`axis_line_annotation`（<= 0.01）这一档保留原语义** —— 位移≈0 确实只能是「按轴线标注」，
   它不依赖墙厚。⚠️ 若你认为这条也需要证据支持，**报告出来但不要擅自改**。

## 4. 验收条件（缺一条即未完工）

1. **锁住「无依据不许声称」这个性质**：至少一把锁断言
   `0.02` / `0.12` / `0.29` 三个位移**都不会**得到「按外包标注」类结论，
   且**它们仍各自可见、带着自己的数字**。
2. **锁住报告文本**：断言 `annotation_basis_report()` 产出的 `interpretation_rule`
   **不再把中间区间描述成外包标注**。
3. **回归用例自证前提**：先断言「旧口径在这个夹具上确实会给出 outer_skin」（即前提成立），
   再断言新口径不再如此；**前提破了要大声报错**，⛔ 不许静默退化成空锁。
4. **neuter 实测**：把你改的分档实现中和掉，新锁必须转红，并核对红点位置。
   顺带回答「不加这处改动，这道门本来红不红」。
5. **全仓绿**：`python -m pytest tests -q -n auto` 与基线对账、零回归；
   **判「跑完了」必须看到 `N passed` 汇总行**。⚠️ 打印式探针请用 `-n0`（`-n auto` 会吞 worker stdout）。
6. **真实产物上跑一次**：在 `run_2026-08-11_continuous_e2e` 的真实 correction 产物上，
   把修法前后的四条观测逐条打印对照（这份产物的四条边位移应当≈0.12）。
   ⚠️ **这正是本摊最要紧的一次实测**：修法后它应当从「按外包标注」变成中性档
   —— 也就是说**我们今天并不知道这张图是不是按外皮标注的**，这个「不知道」必须变得可见。
7. **如实分账**：哪些实测、哪些推理、哪些没验。⛔ 不许把未验证项写成已验证。

## 5. 运维

- **本摊必须能在一个 5 小时额度窗内收尾**（上一批撞窗三次）。判断做不完就**停下上报**，
  ⛔ 不要停在「改了行为、锁一把没写」的中间态（上一批实犯，摊 C 恰好就是这个坑）。
- 中断时**不要总结自己做了什么**：orchestrator 一律以 `git diff` 为准（已三次实证席位自述不可信）。
