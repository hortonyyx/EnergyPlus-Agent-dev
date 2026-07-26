# 接手单：GT 转正通道 —— R3-7 / R4-14 变异矩阵（2026-07-26）

- 前一施工方：terra（同批 WP-1..WP-4 + r1 返工均已交付，因上下文预算耗尽交接，**未伪造自查表**，处置正确）
- 本接手方：terra（全新会话，精简上下文）
- 主控：Opus 5 ｜ 审阅方：GLM-5.2（谁写谁不批，跨家族）
- 契约：[细稿](../../proposals/gt_promotion_path_spec.md) + [返工单](2026-07-26_gt_promotion_path_rework.md) + [执行日志](../execution/2026-07-26_gt_promotion_path.md)

## 现状（接手方无需重做）

本批代码已全部就位并过主控轻门的全量复跑：**1618 passed / 10 xfailed / 0 failed**。
已闭：MAJOR-1（恒真假门已删）、MAJOR-2（语义不变式锁改为经生产路径真变异，并实跑「删除守卫即红」）、MINOR-1/2/3/4/5、R4-15（sm21 双 snapshot 相同 `463803…fe8f56`）。

## 唯一剩余任务

**R3-7 / R4-14 = 签署工具与 promote 的每条内联前置的源码变异矩阵。**

这两条是本批验收纪律的命脉：项目前两批（转换器 P0–P2 及其返工轮）都栽在「门看着在、实际大面积 false-lock」，而本批 r1 已经复现过一次同样的模式（MAJOR-2）。现有普通负例测试**不能**充当该表。

## 方案骨架（主控已定，照做）

前置是 `promote_gt_v3` / `sign_review_bundle` 内联的 `if ... raise`，无法从外部 monkeypatch 单条 ⇒ 走**源码行变异 + 子进程跑整套**：

```python
MUTANTS = {   # id: (相对路径, 精确原文串, 替换)
    "promote_report_not_all_green": ("src/agent/judge/gt_promotion.py",
        'raise ValueError("promotion_report_not_all_green")', "pass"),
    # promote 每条前置一格；sign_review_bundle 每条前置一格
}
EXPECTED = {"promote_report_not_all_green": {"test_r4_7_nonpass_report_refuses"}, ...}

@pytest.mark.mutation
@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_precondition_is_one_to_one_bound(mutant, tmp_path):
    repo = _mirror_repo(tmp_path)             # 只拷 src/ scripts/ tests/ + pyproject.toml
    _apply_mutation(repo, *MUTANTS[mutant])   # 精确串替换，替换数必须恰为 1
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                          "-m", "not mutation",          # 关键：排除自身，防无限递归
                          "tests/test_gt_promotion_path.py"],
                         cwd=repo, capture_output=True, text=True)
    assert _failed_test_names(out.stdout) == EXPECTED[mutant], out.stdout[-4000:]
```

**四个坑**：
1. 子进程必须 `-m "not mutation"` 排除自身，并在 `pyproject.toml` 注册 `mutation` marker。
2. `_apply_mutation` 必须断言精确串**恰好出现 1 次**——变异没打中会伪装成绿。
3. 判据是**集合相等**：多红（连带）与少红（假锁）都要失败，不是"至少红一条"。
4. **每条前置一格，一条不落**：promote 侧（报告十门全绿 / ack-index 一致 / 验签通过 / candidate 状态 / case 与 index 身份 / 内容 hash 自洽 / 目标已存在 / 写后自校 …）、签署侧（index 合法 / 逐文件字节 / 源图 hash / 八门全绿 / 近阈值确认 / ack 不覆盖 …）。

**若某条前置没有对应用例保护 = 发现真洞**：补用例并在表里标「本轮新发现」，不得调整期望值迁就现状。

## 交付

1. 完整 R3-7 / R4-14 表（每格：变异什么 → 实跑红了哪些 → 是否恰好只红对应项），追加进同一份执行日志。
2. 出现「neuter 后全绿」或「连带红」照实写并修。
3. 全仓复跑一次（基线 1618 passed / 10 xfailed / 0 failed），原始输出尾部进日志。

## 禁区

细稿 §6 照旧。特别：不得写入 `case_tests/test_baseline/gt/`；不改 `.gitignore`；不放宽既有容差/断言；不 `git commit`。
