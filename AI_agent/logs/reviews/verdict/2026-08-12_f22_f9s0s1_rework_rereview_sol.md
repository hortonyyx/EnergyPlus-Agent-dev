# F-22 + F-9 S0/S1 返工复审（第二轮）裁决 — sol

- 日期：2026-08-12
- 审阅席：GPT / sol
- 返工提交：`21b47396db0018f9cc40479f5b22afcbcb49778c`
- 总判定：**CHANGES REQUIRED（触发请求书“前提错误即停”纪律）**
- 审阅状态：**已停止，非完整复审**

## 1. 结论

`BLOCKER-1` **未关闭**。当前实现没有验证“schema v3 / orthogonal_polygon / post-transform”这一完整身份，只验证了 `schema_version == "3"` 和声明常量未被改名。仓内真实的 F-17 翻转前 schema-v3 产物因此被错误标成可信，并被下游判成全项通过。

这证明请求书所列 fail-closed “四种路径”不是完整岔口：还存在第五类、且已由真实产物实例化的路径——**schema v3 已知，但 post-transform 身份缺失/不成立**。请求书 §3.5 明令发现岔口/分类/数量前提错误后停止上报，所以本席在坐实该反例后没有继续审 S0/S1、没有继续做 AST 锁 neuter，也没有给其余七条 finding 伪造关闭结论。

一个 BLOCKER 已确定未关闭，故即使其余项尚未裁定，总判定也只能是 **CHANGES REQUIRED**。

## 2. 停止触发证据

### 2.1 行为实验

公共入口：`score_correction_geometry`。对同一 case 的两份仓内真实产物分别评分：

| 产物 | 声明 schema | footprint | `facade_segments` | scorer 给出的 convention | refusal evidence | score criteria |
|---|---:|---|---:|---|---|---|
| `run_2026-08-09_f17_e2e_verify/.../output.json` | `3` | `[0.12,14.88] × [0.12,7.88]` | 0 | `trusted=True`, `identity=outer_skin_exterior_centerline_interior` | 空 | 五项全部 `pass` |
| `run_2026-08-11_continuous_e2e/.../output.json` | `3` | `[0,15] × [0,8]` | 8 | 同上 | 空 | 五项全部 `pass` |

翻转前产物的 Floor 1 boundary 实际输出为：

```text
S: read=0.12,  delta=+0.12, status=within_tol
N: read=7.88,  delta=-0.12, status=within_tol
W: read=0.12,  delta=+0.12, status=within_tol
E: read=14.88, delta=-0.12, status=within_tol
```

但它没有得到 `unsupported_output_convention`，反而得到：

```text
walls_complete=pass
windows_placed=pass
boundary_complete=pass
no_oversplit=pass
elevation_windows_placed=pass
```

因此这不是“拒判长得有点像全对”，而是该真实岔口**确实被当成可信且全对**。它直接证伪 fail closed 已覆盖完整身份空间。

独立日志：

```text
/tmp/sol_rereview_f22_v3_identity_branch_20260812.out
/tmp/sol_rereview_f22_v3_identity_branch_20260812.rc   # 0
```

### 2.2 为什么现有守卫无法区分

`src/agent/judge/correction_score.py::_is_trusted_output_convention` 的行为条件只有：

```text
geom.schema_version == "3"
AND CORRECTION_OUTPUT_CONVENTION == _TRUSTED_SCHEMA_V3_IDENTITY
```

它没有消费 run 的 `capability_profile`，也没有验证 deterministic/post-transform provenance。真实翻转前、翻转后产物都落入同一个 `schema_version == "3"` 分支，故把 schema 版本当 profile 与变换阶段的代理并不成立。

把声明改成 `bogus` 会改变行为，只能证明常量不再 inert；不能证明被它放行的产物真的具有声明所指身份。

## 3. 上一轮 findings 的第二轮状态

| Finding | 第二轮判定 | 判据 |
|---|---|---|
| **BLOCKER-1** — 声明 runtime inert、legacy 无条件删换算 | **未关闭** | 常量现已承重，但完整身份门仍 fail-open：真实 schema-v3 翻转前产物被标为 trusted、零 refusal evidence、五项全 pass。`schema_version=3` 不能证明 post-transform。 |
| **MAJOR-1** — resolver artifact / raw context 认证绑定不足 | **未裁定** | 因请求书前提错误触发停止；不得把定向测试绿冒充跨字段 hostile 复审。 |
| **MAJOR-2** — decision preimage / `accepted` 语义过弱 | **未裁定** | 同上。未完成请求书要求的 raw/context 双向错配及扩展错配组合审判。 |
| **MAJOR-3** — facade convention 未完整接线、锁可绕 | **未裁定** | 同上。未独立核实“6 个真实调用点”数量，也未完成逐点行为中和与 `/tmp` 锁 neuter。 |
| **MINOR-1** — 阈值先 round 再比较 | **未裁定** | 定向测试通过不足以替代完整边界与反事实审查；停止后未继续。 |
| **MINOR-2** — 测试标题强于判别力 | **未裁定** | 停止后未继续。 |
| **MINOR-3** — 两套 legacy mirror coercion 并存 | **未裁定** | 停止后未继续；没有据测试自述认定行为保持。 |
| **NIT-1** — 旧文案 | **未裁定** | 停止后未继续。 |

“未裁定”不表示关闭，也不表示另行发现失败；只表示本席遵守停止纪律，没有在不完整复审上签字。

## 4. 新发现

没有另立新编号。上述“已知 schema v3、但 post-transform 身份未证”是上一轮 `BLOCKER-1` 所要求运行时身份验证的直接反例，应归入原 finding，而不是用新编号稀释它。

请求书前提修正后，至少应把身份分支改写为：schema/profile/变换 provenance 分别可验证；不能继续把 `schema_version == "3"` 视为三者的等价代理。

## 5. 已运行但不构成关闭证明的测试

停止触发前已跑返工定向集合：

```text
141 passed, 18 warnings in 12.81s
exit=0
```

覆盖：`test_judge_batch_b.py`、`test_render_grade.py`、F-9 S0/S1 两个新增测试文件，以及两把 scorer-schema 定向锁。日志：

```text
/tmp/sol_rereview_targeted_20260812.out
/tmp/sol_rereview_targeted_20260812.rc   # 0
```

这些测试没有覆盖上面的真实翻转前 schema-v3 身份反例；机械绿门不能关闭 BLOCKER。

## 6. 未验证项

因触发停止，以下均未验证：

- BLOCKER-1 中请求书点名的 missing schema、显式 `None`、解析异常、未知 schema 四条路径的逐条动态结果；
- legacy “明确拒判”作为工程选择是否应接受；
- `boundary=None`/空 wall segments 在所有下游消费者中的完整传播，而非本次已证实的第五岔口；
- output convention/profile/provenance 是否真正进入 cache identity；同一 output 换 profile 是否复用旧 cache；
- MAJOR-1 的 raw bytes、manifest、readings、direction/datum、resolver/context 之间全部交叉绑定；
- MAJOR-2 的 raw/context 单边变更、frame/scope/z/floor 组合、伪造 distance/tolerance、跨 decision 重放；
- MAJOR-3 的真实调用点总数、每个调用点的行为中和、白名单锁的 dead-call neuter 与合法实现变体过约束；
- MINOR-1 阈值两侧更细的浮点格与负方向对称性；
- legacy mirror 宽松归一的独立行为保持复验；
- 全仓 pytest、compileall、`git diff --check`；
- 基线提交重跑。

本席没有执行任何 git 写操作，没有修改施工代码，也没有在工作树做 neuter。本裁决书是唯一新增输出。
