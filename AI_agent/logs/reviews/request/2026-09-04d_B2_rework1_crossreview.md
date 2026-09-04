# 复核单 · **B2 返工 1** 跨家族审

- **日期**：2026-09-04 · **复核方**：**GPT 家族**（⛔ **不得 Claude** —— Claude 是施工方）
- **工作目录（写死）**：`/tmp/b2rw_review_gpt`（detached @ `wt/09.04a_b2_rework`）· ⛔ 别写主树
- **上一轮裁决**：[`2026-09-03al`](../verdict/2026-09-03al_B2_crossreview_gpt.md)（**你出的**，REWORK / 阻断 3 / 不阻断 1）
- **返工单**：[`2026-09-04a`](2026-09-04a_B2_rework1.md)
- **审对象**：`git diff 82f9ce32..wt/09.04a_b2_rework` —— 四笔
  （`b07534ed` B-1 封装载体 · `1d74e67c` B-3 抽结构判据 · `b7f6c9fa` 测试 · `a45f778c` 执行档）
- **自报全量**：`3777 passed / 0 failed`（= `3773 + 4`）⇒ ⭐ 请核

## 一、⛔ 三条阻断逐条重造（⛔ 别只读代码，跑你自己的变异）

| 上轮 | 你上轮的实测 | 现在要验 |
|---|---|---|
| **B-1** 入口丢掉冻结字节校验 carrier | 保留原 `z_ref`、只手改 `z_m` 为 `12.34/15.24/18.54` ⇒ **正式入口接受并产出** | ⭐ **同一攻击现在必须被拒**（`FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE` 或等价具名错）|
| **B-2** 「无 z 参数」只是签名外观 | 手造 `DerivedFloorLevel(z_floor_m=12.34, ...)` 直接装配即绕过 | ⭐ 返工门是**让这条路在类型层不存在** —— ⛔ 若它只是「加了一句检查」，请判不通过 |
| **B-3** footprint 错判吞掉别的错 | 「必填 `name` 缺失 + 类型错 + 键名撞 needle」⇒ 被误报成 footprint 不一致 | ⭐ 现在必须**按结构判定**（`loc`/`type`），⛔ 不看 message 文本 |

## 二、⭐⭐ 施工方自报最薄弱（请重点打）

> **B-3 的结构判据依赖一条推理**：「本构造点**唯一可达**的 empty-loc `value_error` 就是 footprint」——
> 成立于当前 `windows=[]` / `facade_segments=[]` / id 已去重。
> **将来 B4 若往这里装 windows/segments，判据需收窄**；最干净是让 schema 为 footprint 违规
> 抛**可辨识子类 / 稳定 code**。它说超出本单范围，已在 docstring + 注释 + 测试里留档。

⭐ **请判**：① 那条「唯一可达」的推理**今天成立吗**（⛔ 请自己构造反例试）
② **B4 现在已经合并进主线了** —— 这个「将来」是不是**已经到了**？
③ 留档够不够，还是该现在就补。

## 三、⭐ 派工方已替施工方做完的事（⛔ 不必你重做，但可复核）

**逐层 gt 对账**由派工方以 judge 身份做完 → [judge 记录](../verdict/2026-09-03an_B2_gt_reconciliation_judge.md)：
**层数 gt=2 / 产物=2 逐位相等；标高准到 2.1 mm = 0.155 像素**，残差归 reading 的像素标定。
⚠️ 该档**只对了 z 梯子一个维度**，⛔ **F-1（生产帧平面几何零 gt 对账）原样挂着**。

## 四、验收（照返工单 §四 六条逐条报）
`1` z 漂移是机器门不是人工抽检 · `2` 手填 z 的路在类型层不存在 · `3` 旧生产面已迁移 ·
`4` footprint 错判是结构判定 · `5` 上轮过审的不退化 · `6` 全量绿逐位闭合。

## 五、⚠️ 环境
```bash
cd /tmp/b2rw_review_gpt && \
python -c "import src.agent.correction.multifloor as m; print(m.__file__)" && \
    python -m pytest -q -n 6 -p no:cacheprovider
```
⛔ 不用 `-n auto`。⛔ 不跑 `pip install -e .`。⛔ 不要改代码。
⚠️ 同机主控在跑权威全量，预期竞争；**判假红看有没有 summary 行**。

## 六、裁决
`AI_agent/logs/reviews/verdict/2026-09-04d_B2_rework1_crossreview_gpt.md`：
`APPROVE` / `APPROVE-WITH-FINDINGS` / `REWORK` + **阻断 N / 不阻断 M**；
§一 三条 · **§二 三问正面回答** · §四 六条。⭐ 没能复现的明写「未复现」。
