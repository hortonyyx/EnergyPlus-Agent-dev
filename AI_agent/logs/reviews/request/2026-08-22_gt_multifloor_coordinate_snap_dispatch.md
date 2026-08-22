# 派工单 · S1：多层轮廓世界坐标吸附（2026-08-22）

**施工席位**：GLM（glm-5.3）· **复核席位**：GPT 家族（gpt-5.6-sol，跨家族）· **主控**：Claude（轻门 + 裁决，⛔ 不参与施工）
**用户拍板**：2026-08-22「修答案生成器，让几何相同的多层轮廓指纹逐位一致」（治根方案）

---

## 一、⭐ 已由主控追出并核实的因果链（**请独立复核；任一条不成立立即停下上报**）

> ⚠️ 主控本轮已有**四条**前提被下游抓错（编造函数名 · 把错误信息词表当未定项 · P7 以偏概全 · P6 字面不成立），
> **全是「查了一处就当成全都如此」**。下面每条都请当作【可能错的前提】。

| # | 前提 | 核实方式 |
|---|---|---|
| **Q1** | 两层平面在 DXF 图纸上画在**不同位置**，各有一套 world-from-source 仿射；实测 sm25：`plan-F1 m02=30.469` / `plan-F2 m02=-24.511800000000004`，**而两者 `m12` 相同（-28.2136）** | `AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/request_v3.json` |
| **Q2** | 因此**只有 x 坐标**在两层间差 `3.552713678800501e-15` m，**y 逐位相同** —— 与 Q1 的「m02 不同、m12 相同」吻合 | 见 §四 复核命令 |
| **Q3** | 转换器的量化 `_quantize` 工作在 **DXF 原生单位**（该模块注释原文：「work in DXF native units; convert to world at the edge」），**世界变换发生在量化之后**，之后**没有任何再吸附** | `src/agent/judge/tarch_normalize.py:110-116`；世界变换 `gt_extraction.py:189-193` `_transform` |
| **Q4** | 后果一：两层 `footprint_fingerprint` 完全不同（`36fb25250aad…` vs `fbfc5e046f79…`）| §四 |
| **Q5** | 后果二：North/South 两层 `world_along_interval` 不同（`(0.0, 25.0)` vs `(-3.55e-15, 24.999999999999996)`）| §四 |
| **Q6** | ⭐ **Q4 与 Q5 是同一根因的两个症状** —— 只修指纹不修坐标，默认生成器会**越过指纹门**继续产出 North/South 的无效 `along_origin`（GPT 复核 MAJOR-2 明确指出）| `verdict/2026-08-22_elevation_score_bindings_gpt_verdict.md` MAJOR-2 |
| **Q7** | 本项目**已有签过字的同类噪声口径**：`tarch_normalize.py:2930` `_PAIRING_Z_TOLERANCE_M = 1e-9`，注释论证「浮点重结合噪声 O(1e-15)；1 纳米比毫米量化步长低 6 个数量级、比噪声底高 6 个数量级，绝不可能吸收真实漂移」⇒ 本批**不需要新拍一个阈值**，沿用同一论证形态即可 | 读该常量与注释 |

## 二、要做什么

**在世界变换的出口补一次吸附**：世界坐标算出来之后吸附到已声明的网格，
使「图纸上几何相同、但画在不同图纸位置」的多层轮廓产出**逐位相同**的世界坐标。

⛔ **不许**只把指纹规范化而不动坐标（Q6：那样 North/South 仍会出无效 origin）。
⛔ **不许**在下游各处加容差绕过（治标；且每个严格 `==` 都要各加一次，将来别处还会爆）。

**吸附精度**：⛔ 不许拍一个新数。请**沿用 Q7 的论证形态**给出取值并在代码注释里写明论证
（噪声量级 / 与声明量化步长的距离 / 为什么不可能吸收真实漂移），取值本身在执行日志里点名交主控与复核。

## 三、⛔ 停下上报项

**T1 · 影响面**：改世界变换出口会改变**所有** v3 答案的字节吗？
请实测 sm24（单层）**重建后 `content_sha256` 变不变**。
- 若 sm24 也变 ⇒ **停下上报**：这意味着已签字的历史答案全部要重签，超出本单范围，须用户拍板。
- 若只有多层案变 ⇒ 继续，并在日志里点名列出受影响的 case。

**T2 · 重签**：sm25 答案重建后必须由**用户签字**（`gt_review_sign.py`，G10）。
⛔ 施工方**不得**代签、不得跳过签字直接入库。请把重建好的候选包路径与新 `content_sha256`
报回来，由主控转呈用户签字。

**T3 · 凡 §一 任一前提复核不成立，立即停下上报。**

## 四、复核命令（原样可跑）

```bash
python - <<'PY'
import json
g=json.load(open('case_tests/test_baseline/gt/sm25-L_anchor/gt.json'))
v={f['id']:(f['footprint_fingerprint'][:12], f['footprint']['exterior']['vertices']) for f in g['floors']}
print('fingerprints:', {k:a for k,(a,_) in v.items()})
a,b=v['F1'][1], v['F2'][1]
print('max |Δ| per axis:', max(abs(q[0]-p[0]) for p,q in zip(a,b)), max(abs(q[1]-p[1]) for p,q in zip(a,b)))
for fam in ('North','South','East','West'):
    for f in g['floors']:
        s=[x for x in f['boundary_segments'] if x['facade_family']==fam]
        print(fam, f['id'], (min(x['world_along_interval']['lo'] for x in s), max(x['world_along_interval']['hi'] for x in s)))
PY
```

## 五、必须交的锁（⛔ 缺一不算完）

1. **正向**：sm25 重建后 F1/F2 `footprint_fingerprint` **逐位相同**，四个立面族两层
   `world_along_interval` **逐位相同**。
2. **端到端**：sm25 六图 run 判分从 `rejected` → **`c2_scored`**，plan 与 elevation
   **两个频道都 `applicable`**（这是本单的最终验收）。
3. **非回归**：sm24（单层）重建后 `content_sha256` 与现有一致（若不一致 ⇒ T1 停下上报）。
4. **反向锁**：构造一份两层坐标**真的不同**（超出噪声量级，例如差 1 mm）的输入 ⇒
   必须仍然 fail closed，⛔ 不许被吸附抹平。**这条最关键**：证明吸附只吃噪声、不吃真实差异。
5. **neuter**：摘掉吸附 ⇒ 锁 1/2 变红；且摘的是**接线**不是机制。
6. **全量**：主树 `python -m pytest -q -n auto`，与基线 **3008 passed / 13 xfailed** 对账。

⚠️ **全量跑的时候⛔ 不许再跑任何会写 `case_tests/` 的命令**（判分 / `flow` / `artifacts` / `record`）——
主控刚因此制造过一次假红，白跑 16 分钟并差点误判施工席位。

## 六、⛔ 明确不做

- 不改判卷侧的严格相等比较（治标）
- 不改立面绑定生成器（上一批刚落地、已复核）
- 不代签 gt
- 不为 sm25 特化：吸附对任何多层 case 都必须成立

## 七、验收

执行日志 → `AI_agent/logs/reviews/execution/2026-08-22_gt_coordinate_snap_glm_execution.md`
复核裁决 → `AI_agent/logs/reviews/verdict/2026-08-22_gt_coordinate_snap_gpt_verdict.md`
（`APPROVE / REWORK / BLOCK` + 逐条附实测命令与输出；⛔ 无实测输出按 MINOR 计）
