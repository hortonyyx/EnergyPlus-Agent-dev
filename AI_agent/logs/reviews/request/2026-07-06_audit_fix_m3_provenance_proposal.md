# M3 · run 溯源自动采集(执行简报,待 Codex 方案审)

> 缘起:体检 A2-5(`FABLE5_REPORT.md`)+ 用户硬纪律 memory[run-provenance-recording-requirement]:每 run 必记全链路模型配置+脚手架状态,否则回归归因卡死(2026-06-24 教训:sm21_pre 识图归属无法从产物坐实,被迫 A/B 补证)。现状=`git_sha`/`is_dirty`/skill 内容哈希全仓库零命中;`run_config.yaml` 只有读取点无写入点;`record_baseline` 缺失字段填 "unknown"。体检把它列为「实验作数性」三缺口之一,先于下一次作数 A/B 落地。
> 纪律:备份 `backup/{src,scripts}_history/2026-07-06_m3_provenance/`;零 golden 改动;零契约改动。

## 1. 方案

**采集点 = `record_baseline`**(用户既定落点),写进 `_run/baseline.json` 新顶层块 `provenance`:

```json
"provenance": {
  "git_sha": "<git rev-parse HEAD>",
  "git_dirty": true,
  "git_dirty_paths": ["src/...", "..."],      // capped(如 ≤50 条+总数),防爆
  "skills_intake_hash": "<sha256>",            // skills/intake_pipeline/ 目录内容哈希
  "reading_src_hash": "<sha256>",              // src/agent/reading/ 目录内容哈希
  "collected_at": "<ISO8601>"
}
```

- **目录内容哈希算法(确定性)**:遍历目录内全部文件(排除 __pycache__/.pyc),按相对路径排序,逐个 `sha256(relpath + "\0" + file_bytes)` 连进总哈希。纯函数,落 `src/agent/execution/` 或 record_baseline 内部 helper,单测锁定确定性(同内容同哈希/改一字节变)。
- **git 信息**:subprocess 调 `git rev-parse HEAD` + `git status --porcelain`(相对仓库根);**git 不可用/非 git 环境 → 字段填 null + `collection_error` 说明,不 raise**(best-effort,与 record_baseline 现有软降级风格一致)。
- **展示**:REPORT.md 的 GEN 事实区(模型配置置顶节)追加 provenance 摘要行(sha 短形+dirty 标记+两个哈希短形)。
- **顺手清一件死件(体检 A2-4)**:`RunPolicy.reading_runner_ladder`(policy.py:56,零消费)——**删除**(若审阅发现有序列化兼容风险则改为保留并注明,报回)。

## 2. 明确不做(防 scope 蔓延)
- 不做 fail-closed(不因缺 provenance 阻塞 record);不写 run_config.yaml(那是跑前人工拍的配置,写入点是 SOP 不是代码);不动 llm.yaml;reading 模型钉死已由 7.03 baseline.models 解决,本批不重复。

## 3. 验收
- 单测:目录哈希确定性 ×2;record_baseline 产出含 provenance 块(git 可用路径 + monkeypatch git 失败的软降级路径);REPORT GEN 区含摘要。
- 全量 pytest 绿、9 xfail 不变;**已存 anchor 的 baseline.json 不动**(只影响新记录)。

## 3b. 裁决(2026-07-06,Codex 审 APPROVE-WITH-CHANGES,4 findings 全采纳,定案)

1. **删 `collected_at` 字段**(finding 1 HIGH):不写任何挂钟时间进 provenance 块——git_sha+内容哈希即身份;保 record_baseline 幂等与未来精确重录 diff。
2. **哈希范围扩**(finding 2):加 `correction_src_hash`(src/agent/correction/)+ `correction_config_hash`(src/configs/correction.yaml 单文件)——脚手架状态的第二源一并钉死。
3. **git 锚定仓库根**(finding 3):`git -C <project_root>`,不依赖 run_dir/环境 cwd;project_root 从模块位置推导。
4. **重录兼容注记**(finding 4):在 provenance 块实现处留注释——未来 golden 精确重录比对须归一/排除 provenance 环境依赖字段;不改现有比对代码(现无消费者会炸,审已核)。

## 4. 审阅需求
1. baseline.json 加顶层块有无消费者做严格 schema 校验会炸(record_baseline 读回/report_assembly/golden 测试)?
2. 目录哈希范围是否该再含 `src/agent/correction/`(skill prose 之外影响 reading→correction 行为的第二源)?给判断。
3. reading_runner_ladder 删除的兼容面(有无旧 orchestration_state/baseline 序列化包含它反序列化会炸)。
4. subprocess git 调用在测试环境(tmp_path 非 git 仓库)的行为面。
