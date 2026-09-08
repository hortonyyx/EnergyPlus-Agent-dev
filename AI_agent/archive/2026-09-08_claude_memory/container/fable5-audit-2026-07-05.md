---
name: fable5-audit-2026-07-05
description: "Fable5 项目大审已完成,报告在 logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md——7 处挑战既有结论+Top8 风险+修复批次建议"
metadata: 
  node_type: memory
  type: project
  originSessionId: f8c3e328-a034-4f57-ac8d-7eaba0518947
---

2026-07-05/06 Fable5 自主主控完成项目体检,交付 `AI_agent/logs/experiments/2026-07-05_fable5_project_audit/FABLE5_REPORT.md`(4 路子代理取证+Fable5 综合,零代码改动)。

**核心裁决**:
- **A3 迁移第四路=复现 GO**,无有效约束流失;旧 caveat"run_pipeline 自校半拉子"应撤销但换记新账。
- **挑战"口径齐 validate_case"**:0_reading 段生产路径只跑 6/~15 检查(evidence_preflight 投影静默丢 9 个 INVARIANT,evidence_preflight.py:96-99)=HIGH 活跃缺口;S5 check_assembly 报告从不进 `_gate_self_check_report`=结构性死门。
- **证伪"版本化 schema 接缝"**:schema_version 字段不存在;capability_profile 全仓库仅 kernel.py:226 一处消费、几何内核零感知。
- **判卷层对 C2 零准备**(零 capability_profile/polygon 分支,斜墙在 scorer 不可见);§8b Hungarian 动机修正(立面已穷举最优,问题=组合爆炸);**win_tol=死参数**(平面窗实际吃 extent_tol)。
- **C1 精化**:Haiku 实验只证明 **prose** 脚手架托不起弱 VLM;Haiku+CV 工具箱复测=北极星战略判决性实验。
- **Top 风险#2=实验作数性三缺口**(污染 prompt 级隔离+provenance 零自动采集+盲抽只 mock 验证),建议先于一切作数 A/B 落地。

**D 补充自查(2026-07-06 用户授权,超出体检单)**:
- D1 环境:**残缺 `.venv` 活雷**(numpy 坏,取证代理实踩,应删只留 /opt/venv);**ezdxf 游离 uv 依赖图**(新环境 gt 工具链断);dotenv/openai/attrs 仅传递声明;git"main 未推"经主控复核降级=仅 ref 陈旧(对象已随分支在远端),真事项=78 commit 分叉待合并;64k 截断顾虑未兑现+未记录优点(LLM 负载随区数不随面数)。
- D2 skill:**链闭合门硬编码 0.05 vs A0 文档 10mm(5 倍松,reading.py:669)**;全 NoMass 包络 hard 规则零门;恒温/理想负荷 schedule 引用无门(S4-07 同清单漏叶);候选 17 实已闭合(plan 记录过时);judge_rubric 仍在执行 skill 目录;A0 registry 反向漂移三容差;README 违反 skill 库卫生政策。

**修复批次建议**:批次零=删.venv/补依赖/闭合门常数对齐(半天);批次一=实验基建三件;批次二=check registry 一把解口径缺口+D2 两个 mep 小门;批次三=小测试补丁(4_mep golden raise/zone_closure 数值分支/report 抓取器);C2 相关按报告 B1 开工序。

**✅ 修复批次 M1–M4 已落地(2026-07-06,commit `fea6981`+`2661fd4`,489 绿+9 xfail,Claude 编排/Codex 双审执行)**:M1 口径收口(S0 完整检查内联+reading_checks.json+S5 门接活+`tests/test_check_parity.py` parity 锁)/M2 三道门(闭合容差 10mm·construction_thermal_mass·hvac_schedule_refs 非空引用)+依赖卫生(ezdxf 等入 pyproject·testpaths·删 .venv)/M3 provenance 块(git_sha+dirty+三目录哈希·无时间戳)/M4 测试补丁。管理文档已同步(CLAUDE §2/plan/contracts)。**遗留待拍板**:污染硬隔离、INVARIANT 全档硬 raise、check registry 重构、判卷 §8b 批。**CV C0+C1 已落地**(`e3ec9ae`);**C2 开工设计已定稿**(`c8abb8b`·proposals/c2_orthogonal_polygon_design.md·D8 批次 B0-B6+D10 定案·Codex 审全采纳)。**下一场 Opus 排队单(用户认可 Fable5 末期只做方案、工程与跑测归 Opus)**:①Codex 补审 CV 批→②Haiku 复测(跑前拍配置)→③C2 按 D8 执行→④污染隔离设计。全部已推远端(至 `0c54a90`)。

**How to apply**:后续会话引用体检结论直接读报告;体检遗留项见 CLAUDE.md §2 2026-07-06 块。
