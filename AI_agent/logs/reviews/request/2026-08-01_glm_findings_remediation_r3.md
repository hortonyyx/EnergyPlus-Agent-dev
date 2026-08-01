# 返工单 r3 · GLM 对抗审 findings 窄修（S-1 + NIT-1）

- **日期**：2026-08-01 · **座位**：GPT 侧 terra（`gpt-5.6-terra`，effort=high）· 通道 = `codex exec` CLI 后台
- **来源**：[GLM-5.2 裁决书](../verdict/2026-08-01_reading_unsupervised_enablement_glm.md) = **APPROVE-WITH-CHANGES**
  （0 BLOCKER / 0 MAJOR / **1 MINOR** / **1 NIT**；20 条命题全部成立；独立全量 2046 与主控逐字一致）
- **主控裁决 = 两条全部成立、全部修**（S-1 已由主控独立复现，NIT-1 的污染判断已由主控独立复核）

---

## 1. S-1（MINOR·假锁）— merge 时的考试范围漂移门没有锁

**位置**：[`src/agent/execution/isolation.py:340-343`](../../../../src/agent/execution/isolation.py#L340)

```python
if binding.get("reading_exam_scope_sha256") != (
    verification.exam_scope.content_sha256 if verification.exam_scope else None
):
    raise ValueError("merge refused: the reading exam scope changed since this workspace was built")
```

**这道门由 W4 `2d2137e` 引入，但没有任何测试锁住它。**

**主控独立复现（`/tmp` 克隆，比 GLM 跑得更宽）**：摘掉这三行后
`pytest tests/test_isolation.py tests/test_view_manifest_generator.py` = **244 passed，零变红**。
现有 `tests/test_isolation.py:558` 只断言 binding **记录了** scope 哈希，**没有断言「改了会被拒」**。

**为什么只是 MINOR 但仍必须修**：它是纵深防御（真正的不可变更性已由 resolver 那 6 道守卫锁住，
且 `binding.json` 在 staging 根、受写保护）⇒ 单独失效的可达危害被包住。
**但本批自己立的标准就是「每条新守卫必须有摘掉即红的锁」——这条是漏网的那个，按自己的标准修。**

**要求**：补一条 merge 拒绝锁（建议名 `test_merge_rejects_reading_exam_scope_changed_since_build`）：
build 之后、merge 之前篡改该 run 的冻结 scope（或换绑另一份 base），断言 merge `raise`
且理由指明「reading exam scope changed」。**必须自己 neuter 验真**：摘掉那三行 ⇒ **恰好这条红**，
并报告有无连带。

---

## 2. NIT-1（卫生）— 探针模板用了真实楼宽做语法样例

**位置**：`src/agent/execution/isolation_templates/guard.py` 的 `_BATCH_TEMPLATE`
（以及散在各处 hint 串里的同一组数字）：`px_a:100 / px_b:700 / value_m:15.0 / dimension_ref:"overall_width"`。

**已核实不是污染**：`15.0` / `overall_width` 与目标 case **sm24 无关**
（GLM 查 gt.json 无该键无该值；**主控独立用结构化遍历复核 = 0 命中**，
主控最初用裸正则查出的「15.0」经查是命中了 sha256 十六进制串里的 `15`，非真实尺寸）。
`15.0` 实为 worked-example 那栋楼（`smalloffice_20`）的真实宽度，读图器本来就通过 style-anchor 合法可见。

**但仍要改**：语法样例用**任何真实建筑的真实尺寸**都是在赌「以后的目标 case 不会撞上这个数」。
**改成显式占位值**（例如 `value_m: 12.345` + `dimension_ref: "example_span"`，
像素值同理换成一看就是假的），**让它不可能与任何未来 case 的真实尺寸偶合**。

**要求**：改完跑一遍受影响子集 + 全仓；若有测试断言了这些字面串，**一并更新断言**
（这类断言改动是本项允许的，因为改的是样例数据本身，不是在迁就实现）。

---

## 3. 硬边界

1. **只做上面两条。** 不许顺手改别的；不动 GT / 签名件 / case 元数据；三个身份哈希仍须逐字不变。
2. **不许放宽任何守卫。** S-1 是补锁，不是改门。
3. **neuter 只在 `/tmp` 副本做**，做完恢复，不留痕迹进仓库。
4. W1/W3/W4/r1/r2 的其余生产码不动。

## 4. 验收

1. **neuter 自查表**：S-1 那条锁 —— 摘掉哪三行 → 哪个测试函数红 → 有无连带（真跑输出，不接受推理）。
2. **全仓跑一次**（`python -m pytest -n auto`，不加 `-m`）：**≥ 2046 绿 + 10 xfail + 0 红**。
3. 三个身份哈希逐字不变的证据。
4. NIT-1 改完后：`grep` 证明 `15.0` / `overall_width` 已不在 `guard.py` 的样例串里。

## 5. 交付

- 执行日志续写新一节「GLM findings 窄修 r3」到
  [`AI_agent/logs/reviews/execution/2026-08-01_reading_unsupervised_enablement_terra.md`](../execution/2026-08-01_reading_unsupervised_enablement_terra.md)。
- 一个 commit（message 仿 `<月.日>_<英文标签>`，body 含 ①改动 ②为何此刻 ③影响）。**不许 push。**
- 欠规格边界一律停下上报。撞 `.git/index.lock` → 停下上报，不要自行删锁（主控只跑只读命令）。
- 回主对话只给简报：neuter 自查表 / 全仓绿数 / 改了哪几个文件 / review-ask 段。
