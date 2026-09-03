# 复核单 · **B2 多楼层装配** 跨家族审

- **日期**：2026-09-03（第三程）· **复核方**：**GPT 家族**（⛔ **不得 Claude** —— Claude 是施工方）
- **工作目录（写死）**：`/tmp/b2_review_gpt`（detached @ `wt/09.03ai_b2`）· ⛔ 别写主树
- **任务书**：[`2026-09-03ai`](2026-09-03ai_B2_multifloor_assembly_dispatch.md)（八条验收，规则形态）
- **审对象**：`git diff c13e1ec..wt/09.03ai_b2` —— 四笔分段提交
  （`4db9c7a` 纯装配模块 · `7852e82` 接线 + 具名 footprint 前提门 · `8458b4f` 17 条验收测试 · `82f9ce3` 执行档）
- **改动面**：`src/agent/correction/multifloor.py` **+279**（新）· `pipeline.py` **+84** · `tests/test_b2_multifloor_assembly.py` **+453**
- **施工方自述**：[执行档](../execution/2026-09-03ai_B2_multifloor_assembly_execution.md) ⭐ **线索，非证据**
- **自报全量**：`3773 passed / 0 failed`（= `3756 + 17`）⇒ ⭐ 请核这个 `+17`

## 一、⭐⭐⭐ 施工方自己点名要你打的三处（⭐ 我照转，并各加一句我的看法）

| # | 它请你打什么 | ⭐ 派工方补充 |
|---|---|---|
| **1** | **T5 的「无 z 参数」是否真堵死手填** —— 能否找到一条路径，让产物里某层 z **不来自** `derive_floor_ladder`？ | ⭐ 这正是本单的**承重项**（T1 的全部意义）。⛔ 别只看入口签名，要找**旁路** |
| **2** | **`derive_floor_ladder` 的选层是否真跟数据走** —— 它复用 B3 已过审的 `FLOOR_LEVEL_SELECTION_RULE` | ⭐ 它说「B3 选错我跟着错，但那是 B3 的账」——**这个免责成立吗**？请判 |
| **3** | ⚠️⚠️ **`PER_FLOOR_FOOTPRINT_MISMATCH` 是否掩盖别的错** —— 它**捕获 schema 自己的 ValidationError 再重贴标签**，而且**按 message 子串判定** | ⭐⭐ **这是本项目栽过的形状**（[[lexical-guard-cannot-be-completed]]：词法匹配判无界输入的防线永远补不完）。⛔ **请重点打这一条**：造一个**别的** ValidationError（字段类型错 / 必填缺失 / 枚举越界），看它会不会被吞成 footprint 错 |

⭐ **施工方自报最薄弱**：「#3 的 z-stack 连续性**按构造恒真**」——它诚实声明了这一点，
并说真正防 z 出错的是 #1 的字节引用。⭐ **请判这个自评准不准**。

## 二、⛔ 两条本单特有的判据约束（⭐ 派工方在任务书里写死的，请一并核它有没有遵守）

1. ⛔ **不许拿「零洞零重叠」当判据** —— 设计稿已证它在本链**按构造恒真**（自派生 footprint 自己当分母）= **无牙读数**。
   ⇒ 请核：**它有没有把这个数写进验收**（报可以，当判据不行）。
2. ⛔ **施工席不许读 gt** —— 验收 #7 要求零 gt 接触。
   ⇒ 请**自己 grep 核实**：新增代码与新增测试**都不 import `judge.gt`、不读 `case_tests/.../gt/`**。
   ⚠️ **逐层 gt 对账由派工方以 judge 身份另做**，⛔ 不是它的验收项、也⛔ 不是你的。

## 三、验收（照任务书 §六 八条逐条报）

`1` 层高来自证据不是手填 · `2` 新链不再走手填（摘掉派生 ⇒ 须响亮失败，⛔ 不许静默退回参数）·
`3` 两层装出 `floors[]` 且过层连续性校验 · `4` 层数不是常数（**三层、2.9/3.3/4.2 混排**夹具）·
`5` 坏输入响亮失败 · `6` 单外对撞规则自己走过 · `7` **零 gt 接触** · `8` 全量绿逐位闭合。

## 四、⚠️ 环境

```bash
cd /tmp/b2_review_gpt && \
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```
⛔ 不用 `-n auto`。⛔ 不跑 `pip install -e .`。⛔ 不要改代码。
⚠️ 同机有 Claude 席位在复审 B4 返工，预期竞争；**判假红看有没有 summary 行**。

## 五、裁决

`AI_agent/logs/reviews/verdict/2026-09-03al_B2_crossreview_gpt.md`：
`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` + **阻断 N / 不阻断 M**；
§一 三处逐条判 · §二 两条核实 · §三 八条逐条报。
⭐ 凡没能复现的，明写「未复现」，⛔ 不许拿自述凑裁决。
