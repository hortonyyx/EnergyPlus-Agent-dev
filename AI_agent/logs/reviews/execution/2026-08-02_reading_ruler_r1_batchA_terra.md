# R1 reading ruler · 批 A 执行记录（terra）

- 日期：2026-08-02
- 范围：仅批 A；未开工批 B/C，未提交、未推送。

## L-03 处置表态

**同意 orchestrator 的处置：L-03 不另立锁，内容由 L-02 吞并。**

sol 的 L-03 前提是 `local_x_positive` 具有判卷数值语义；只翻声明、保留数值时应令目标 observation 变为 miss/extra。N-2 已裁定该字段对判卷永不读取，不得参与投影、适用性或分母，因此该预期结果现在与契约相反。L-02/N-5 对 LTR、RTL、任意值及缺失值均断言 `payload.kind == c2_scored`、分母与具体评分行逐字相同，恰好证明该字段不承重；另立 L-03 只会重新引入已废除的双参数化语义。

## Neuter 自查（已完成）

每项均临时摘掉唯一对应实现改动，运行同一主锁组，并在记录结果后恢复工作树。

| 锁 | 对应改动 | 结果 |
|---|---|---|
| L-01 | `mirrored` 不参与 elevation 标准化 | 将 `mirrored=true` 临时重新接入投影（反射 local interval）：**1 failed（L-01）、5 passed**；失败落在 `payload.kind` 相同而具体 opening/claim/criterion 行改变；零连带。已恢复。 |
| L-02 | `local_x_positive` 不参与 elevation 标准化 | 将任意审计值 `audit-only` 临时接入投影（反射 local interval）：**1 failed（L-02）、5 passed**；失败落在 `payload.kind` 相同而具体 opening/claim/criterion 行改变；零连带。已恢复。 |
| L-03 | N-2 下由 L-02 吞并 | 不适用（见上） |
| L-04 | 窗观测缺失仍保留为 miss | 将 `observation is None` 的结果临时改为 `complete`（模拟错误过滤）：**1 failed（L-04）、5 passed**；North/`op_ae1` 的具体 existence 行由应有的 `miss` 变成 `complete`，`payload.kind` 仍被检查；零连带。已恢复。 |
| L-05 | 移除 local-x disagreement 的早退及其 witness | 临时恢复一条历史 North 的 v1 frame-disagreement witness：**1 failed（L-05）、4 passed**；`payload.kind == c2_scored` 与 North/`op_ae1` existence `complete` 仍成立，失败精确落在已废弃 witness 非空，证明它不再存在且不再决定分数；零连带。已恢复。 |
| L-06 | adapter v2 纳入 cache identity | 临时去掉 cache 的 complete identity comparison：**1 failed（L-06）、4 passed**；v1 helper identity 错误命中原 v2 sidecar；该锁先确认 `payload.kind == c2_scored` 和 North/`op_ae1` existence `complete`，再断言 cache miss；零连带。已恢复。 |

## 批 A 改动清单

- `skills/intake_pipeline/0_reading/guide.md`：将立面 x 轴写死为图像左缘为 0、向右为正；不再要求产品选择或声明读向。
- `src/agent/reading/schema.py`：`local_x_positive` 改为可选的非承重审计字段；兼容历史原始产物。
- `src/agent/judge/reading_typed_adapter.py`：v2 标准化只从 reviewed binding 投影；产品的 `local_x_positive` 和 `mirrored` 都不参与投影、适用性或分母；历史误写 RTL 的 North/West 自动按其原有 LTR 数值解释。
- `src/agent/judge/{reading_typed_score.py,score_schema.py,score_service.py}`：升级 reading contract/adapter/cache identity 至 v2，防止 v1 score cache 复用。
- `src/agent/correction/envelope.py`：修复全仓发现的旧投影入口，固定采用 v2 左到右契约，不把可选审计字段 `local_x_positive` 传入几何投影。
- `tests/test_reading_typed_{adapter,scoring_slice0,scoring_slice1,score_integration}.py`：反转旧的 local-x rejection 预期，并新增/加固 L-01、L-02、L-04、L-05、L-06 的 payload kind 与具体 score-row 断言。

未实现方向校验，属已知缺口：本批仅钉死产品/判卷契约，**没有**实现对读图器实际是否从左向右读取的立面 x 方向校验；不得据此声称方向已被机器约束。

已删除旧口径半成品 `local_x_migration.py` 与 `case_tests/replay_overlays/`：N-3 已裁定四条历史 RTL 声明的数值本来就是 LTR，N-2 又规定判卷永不读取该字段；因此 migration/overlay/strict-reject 路径既无语义对象也会违背“不徒增复杂度”，删除而非保留死路径。

## 全仓测试

首次 `pytest -q -n0`（2065 collected）在 20:52 后为 **1 failed, 2054 passed, 10 xfailed**。失败是 `tests/test_c2_b2b_envelope_transform.py::test_endpoint_closure_requires_explicit_tolerance_and_marker_is_extra_only`，不是测试迁就：`FacadeOrientation.local_x_positive` 变为可选后，correction 的 envelope 投影把显式 `None` 传给旧的方向投影器，导致合法缺失声明的 wing evidence 被静默丢弃。

已在 `src/agent/correction/envelope.py` 将该消费点改为 v2 的固定 `image_left_to_right`，不读取该非承重产品字段。失败锁与 L-01/L-02/L-04/L-05/L-06 回归：**6 passed**。

第二次 `pytest -q -n0`（2065 collected）：**2055 passed, 10 xfailed, 150 warnings，零 failed**，耗时 19:00。
