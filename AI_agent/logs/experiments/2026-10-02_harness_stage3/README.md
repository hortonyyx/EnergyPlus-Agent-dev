# 阶段 3：已交付，待 Opus 验收

派工起点 `0662d205`；专用工作树 `.worktrees/astra-stage3`，分支 `dev/astra-stage3-20261002`。
最终运行源码为 `dd4bc0b9`，源码逐文件哈希见 [代码身份](validation/final_code_identity.json)。
本树未合入 main、未 push；正式验收由 Opus 维护，本页不代表验收通过。

## 交付入口

- [中文交付报告](delivery_report.md)：阶段 3 A–I、自评边界、阶段 2 跟进、用量和后续安排。
- [三批结果定稿](role_results.md)、[全部评价](role_evaluation.json)、[原图定位复核页](role_review.html)：32 组合全保留。
- [逐请求用量与偏差](role_usage.json)、[12 次估算校准](calibration/README.md)。
- [最终离线回归](validation.json)、[MCP 演示](validation/offline_demo_20261003.json)、[交付归档核验](delivery_verification.json)、[范围与凭据检查](scope_audit.json)。
- [无损归档](evidence_all.compact.tar.xz)、[完整改动与提交索引](changes.json)。
- [首批整案方案](full_case_proposal.md)：sm24 还原、Voimatalo 部分推理各一次，尚未批准、尚未运行。
- [实施记录](../../worklog/2026-10-02_astra_harness_stage3.md)与[三批协议说明](role_followup_plan.md)。

## 续接状态

10-02 后台两小时硬时限中断，末提交 `9da40977`；10-03 按 Opus 指令完成西立面及平面人工评价，修复根工具额度/直接工具时限，并补齐恢复时兄弟预留范围检查。最终241项离线验证和归档核验全部完成；交付报告及完整提交索引已定稿。

角色账 **42/60**（41 次实报、1 次超时用量未知），估算校准 **12/20**。10-03 续接外部调用 **0**，无新子代理。本批已关闭，剩余额度不自动使用；没有待启动模型或整案任务。角色最终六组数值 6/6、关键定位 5/6、接口收下 4/6、综合通过 3/6，全部三批对错见结果表，不能混作同条件排名。

下一步仅为 Opus 验收、汇总整案方案后报用户决定。若验收需修复，先读当前 HEAD、状态与本目录；不要重新发送完成题、覆盖旧运行、修补原始答案或把历史回包当成当前源码运行。已有类型名依 10-03 指令保持。

## 离线复核

在本工作树执行，临时文件也留在树内。这些命令不调用任何模型：

```bash
mkdir -p .stage3-work/tmp
export PYTHONPATH="$PWD:$PWD/tests"
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$PWD/.stage3-work/tmp"
python AI_agent/logs/experiments/2026-10-02_harness_stage3/verify_delivery.py --archive AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_all.compact.tar.xz
python AI_agent/logs/experiments/2026-10-02_harness_stage3/role_cases/evaluate.py validate
```

精简归档恢复后每个文件的字节数和 SHA-256 都须相符；仓库原图仅按路径/哈希引用，未重复入包。若需落盘，选择本树内一个不存在的新目录：

```bash
python AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_pack.py restore --archive AI_agent/logs/experiments/2026-10-02_harness_stage3/evidence_all.compact.tar.xz --output .stage3-work/restored_delivery
```

原始工作记录继续保存在被忽略的 `.stage3-work/roles`、`roles_followup`、`roles_final`，最终演示为 `offline_delivery_20261003`，最终测试为 `validation_20261003`。旧 `validation_final` 红灯及旧批次没有删除，必要证据另存于本目录 `validation/`。外层 Codex 内部请求及开发子代理用量未获取；归档中的脚本 usage 不计入 Paratera 消耗。
