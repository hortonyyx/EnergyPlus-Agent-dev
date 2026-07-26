# GLM-5.2 验证性对抗审 核验清单 —— GT 转正通道（2026-07-26）

- 审阅方：GLM-5.2（跨家族；施工方为 GPT 侧 terra，**谁写谁不批**）
- 清单出稿：主控 Opus 5（**非施工方**）
- 被审对象：本批未提交的工作树改动（`git status` 见下），契约 = [细稿](../../proposals/gt_promotion_path_spec.md)
- 审阅性质：**验证性**（每条命题已写死"验什么／怎么验／什么算成立／什么算不成立"），不要求探索性找未知缺陷

## 0. 纪律

1. **只审不修**：不得修改任何生产代码或测试。审完 `git diff --stat` 必须与你开始时逐字节一致（自己先记录基线）。
2. **不采信施工方报数**：所有数字自己重算、自己重跑。执行日志里的表格是**待验对象**，不是证据。
3. 探针脚本一律写在 `/tmp` 下，**不得**在仓库内留文件。
4. 每条命题给出：**成立 / 不成立 / 无法判定** + 你实际跑的命令与原始输出片段。"无法判定"是合法结论，猜一个结论不是。

## 1. 命脉（X 组）——这三条不过，全批 REWORK

### X-01 变异矩阵是真的，不是摆设
- **验什么**：`tests/test_gt_promotion_path.py` 的 24 格 `test_precondition_is_one_to_one_bound`。
- **怎么验**：① 至少**抽 6 格**独立重跑（`pytest -q "tests/test_gt_promotion_path.py::test_precondition_is_one_to_one_bound[<id>]"`）；② 检查 `_apply_mutation` 是否断言精确串**恰好命中 1 次**；③ 检查子进程是否用 `-m "not mutation"` 排除自身；④ 检查判据是**集合严格相等**而非"至少红一条"。
- **成立**：抽到的每格都过，且上述三处机制都在。
- **不成立**：任一格失败；或替换串可能命中 0 次/多次而不报错；或判据放宽为子集/非空。

### X-02 矩阵不会被默认跑法跳过
- **验什么**：`mutation` marker 是否被写进 `addopts` 或任何默认排除，使这 24 格在常规全量里永不运行。
- **怎么验**：读 `pyproject.toml` 的 `[tool.pytest.ini_options]`；跑 `pytest --collect-only -q tests/test_gt_promotion_path.py | tail -3` 看总收集数是否含 24 格。
- **成立**：只注册 marker、无默认排除，默认收集含 24 格。
- **不成立**：存在默认排除 ⇒ 矩阵"存在但永不运行" = 假绿。

### X-03 期望集合没有被迁就现状
- **验什么**：`EXPECTED` 是否为了让矩阵变绿而被写成"现状是什么就期望什么"。
- **怎么验**：任取 **2 格**，人工推理"这条前置被摘掉后，逻辑上应该红哪些用例"，与 `EXPECTED` 对照；特别检查执行日志自述的两处修正（R4-9 测试穿透、新增 `promotion_ack_missing` guard）是否属于**真修**而非改期望。
- **成立**：期望集合与逻辑推理一致；两处修正是补/改测试与生产 guard，不是调期望。
- **不成立**：发现某格期望被扩大以吸收连带失败，或被缩小以掩盖假锁。

## 2. 主体命题（Y 组）

### Y-01 恒真假门已彻底移除
- **怎么验**：`grep -rn "canonical_write_drift" src/ tests/`；并通读 `gt_promotion.py` 找是否还有其它"两次调用同一纯函数比较自己"或恒假条件的分支。
- **成立**：零命中且无同类残留。**不成立**：仍有恒真/恒假的"保护"分支。

### Y-02 语义不变式真绑在生产路径
- **怎么验**：把 `gt_promotion.py` 中 `_assert_promotion_semantics(candidate, promoted)` **整行删除**（在 `/tmp` 的仓库副本里做，**不得**改工作树），跑 `tests/test_gt_promotion_path.py`，确认**有**用例变红。
- **成立**：至少 `test_r4_3_production_path_rejects_neutered_geometry_mutation` 变红。**不成立**：全绿 ⇒ false-lock 未真正修复。

### Y-03 promote 不改几何（独立构造，不复用施工方测试）
- **怎么验**：自己走一遍链路（`build_review_bundle` → `sign_review_bundle` → `rerun_signed_review_bundle` → `promote_gt_v3`，目标根用 `/tmp`），把转正结果与候选 `gt.json` 解析后，**只**去掉 `verification` 与 `content_sha256` 两键，递归比较。
- **成立**：完全相等。**不成立**：任何第三处差异。

### Y-04 可复现性（本批地基）
- **怎么验**：同一源图 + 同一 request 连续跑两次转换（`/tmp` 下不同 work_dir），`cmp` 增广 DXF、比较 GT `content_sha256`、比较 7 张 PNG 的 sha256。
- **成立**：三者全部相同。**不成立**：任一不同。
- **附加**：确认钉死值是**输入的函数**而非常量——换一张不同的源图或改 request，`$VERSIONGUID`/`$FINGERPRINTGUID` 必须随之改变（否则是"钉成同一常量"的假绿）。

### Y-05 fail-closed：无假绿转正路径
逐条构造并确认 `promote_gt_v3` **拒绝**（自己造，不看施工方测试）：
1. 没有 `review_ack.json`；2. ack 的 `review_index_sha256` 改一位；3. 包内任一被索引文件改一个字节（至少试 `gt.json` 与一张 PNG）；4. `conversion_report.json` 里任一门为 `false`；5. 候选 GT 的 `verification.status` 已是 `human_verified`；6. `case` 名不符；7. 目标目录已存在（并确认**原目录内容未被动**）。
- **成立**：七条全部 raise 且**未写入任何字节**。**不成立**：任一条被放行，或失败后留下半个目录。

### Y-06 清单完整性是双向的
- **怎么验**：在合法包里**新增一个未列入 `review_index.json` 的文件**，再跑 `validate_review_index` / `promote_gt_v3`。
- **成立**：被拒（施工方声称本轮已补双向完整性）。**不成立**：放行 ⇒ 人核看到的文件集合与被校验的集合可以不同。

### Y-07 禁区
- **怎么验**：`git status --short case_tests/`（须为空）；`git diff --stat` 确认未碰 `.gitignore`；确认 `case_tests/test_baseline/gt/` 下**没有** `sm24_anchor` 目录（本批**不得**实际转正 sm24，那一步由主控亲自执行）；确认 `gt/sm21_anchor/**` 逐字节未变。
- **成立**：全部满足。**不成立**：任一被触碰。

### Y-08 全仓计数独立重算
- **怎么验**：`pytest -q`（**不加** `-m` 过滤，含 24 格变异，约 15 分钟）。
- **成立**：`0 failed`、`10 xfailed`，passed 数与你自己的收集数自洽。**不成立**：任何 failed，或 xfailed 数变化。

### Y-09 三个 CLI 可用
- **怎么验**：`--help` 各跑一次；并至少让 `gt_review_sign.py` 在 `/tmp` 的合法包上真跑一次出签。
- **成立**：可运行且行为与细稿 §4/§5 一致。

### Y-10 诚实性核对
- **验什么**：[执行日志](../execution/2026-07-26_gt_promotion_path.md) 的每一处"已完成/已验证"声称，是否与仓库实况一致。
- **重点**：日志自述的 24 格矩阵表、`sm21` 双 snapshot 相同、MINOR-3 的 ezdxf 等价锁、以及"无假锁、无非对应连带"这句结论。
- **成立**：声称与实况一致（含诚实标注的未竟项）。**不成立**：任何一处声称大于实况。

## 3. 输出格式

裁决书写 `AI_agent/logs/reviews/verdict/2026-07-26_gt_promotion_path_glm.md`，含：
- 总裁决：APPROVE / APPROVE-WITH-CHANGES / REWORK
- 逐条命题：成立 / 不成立 / 无法判定 + 证据
- BLOCKER / MAJOR / MINOR / NIT 分级的 finding 清单，每条给**可执行的出口**
- 你实际跑过的命令清单
- 结束前自证：`git diff --stat` 与你开审时一致（只审不修）
