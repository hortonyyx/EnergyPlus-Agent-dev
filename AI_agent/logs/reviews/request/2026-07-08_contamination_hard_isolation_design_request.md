# 审查请求：污染硬隔离机制化设计（reread / 盲重抽执行器）

- 日期：2026-07-08 · 请求人：Fable 5（主控）· 审查人：Codex
- 背景：plan.md P1 遗留（2026-06-23 用户定）+ Fable5 体检风险#2。现状=重读/盲重抽子代理物理上有全仓读权限，仅被 prompt "告知"别看 gt/旧 attempts/judge 评语——误差预算靠自觉。两场 CV 工具箱实验（07-05/07-07）的限定条款里都挂着"prompt 级隔离"。
- 目标：把"不污染"从**指令级**提升到**机制级**——执行器在机制上**看不到**禁运物，且留下可审计证据。

## 0. 本轮实测约束（设计的硬边界）

| 事实 | 后果 |
|---|---|
| 容器内无 bwrap/docker；`unshare --mount` EPERM | OS mount-namespace 沙箱**不可用**，隔离只能落在 harness 层 |
| 一切跑 root（uid=0） | 文件权限位/chmod 挡不住，"移出可达路径"必须是物理不在场 |
| claude CLI 2.1.198 可用，支持 headless `-p` + 每进程 `--settings` | 可给重读器开**独立进程 + 独立权限配置**，不污染主会话/项目全局 settings |
| `cv_probe.py` 依赖 `src.agent.reading.cv_toolbox` 包 | 工具代码需拷入工作区（包+入口），PYTHONPATH 指向工作区 |
| gt 集中于 `case_tests/test_baseline/gt/<case>/gt.json`；污染源=gt + `<case>/run_*`（attempts/verdicts/grade 渲染）+ judge 评语 | 禁运清单可枚举、可确定性核查 |

## 1. 方案：四层叠加（L1 物理裁剪 → L2 进程权限 → L3 hook 守卫 → L4 审计合并）

### L1 clean-room 工作区（物理不在场）
新模块 `src/agent/execution/isolation.py`：`build_isolation_workspace(case_dir, run_dir, staging_root) -> WorkspaceManifest`

- staging 根在 **repo 外**（默认 `/tmp/ep_isolation/<case>_<ts>/`；产物最终合并回 repo，符合"产物落仓库"纪律）。
- **只拷入白名单**：
  - `case_data/*.png` + `case_data/testdata_prompt.json`
  - skill `skills/intake_pipeline/0_reading/`（**剔除 `judge_rubric.md`**——执行器不该见 judge 准则，现状它就躺在 skill 目录里，顺手关掉这个小口子）
  - `scripts/tool_scripts/cv_probe.py` + `src/agent/reading/cv_toolbox/` 包（平铺为 `tools/`，入口 `tools/cv_probe.py`）
  - E3 前置化 prescan 产物（`<run>/0_reading/cv_evidence/*/prescan/`，若有）
  - kickoff prompt（由 spawn 侧生成，路径全部指向工作区内）
- `out/` 子目录收执行器全部产物（view JSON、cv_evidence sidecar、reading_summary）。
- 写 `MANIFEST.json`：逐文件 sha256 + 来源路径 + 白名单类别；**builder 内置禁运断言**（gt/attempt/verdict/grade token 的文件绝不入场，命中即 raise——防未来白名单被改宽）。

### L2 进程级权限（headless spawn + 独立 settings）
`scripts/tool_scripts/spawn_isolated_reader.py`（薄 CLI，主控经 Bash 调）：

- 生成 `<staging>/isolation_settings.json`：
  - `permissions.deny`：`Read(//workspaces/**)`、`Read(//root/**)`、`Grep`/`Glob` 同规则、`WebFetch`/`WebSearch`/`Task`/`Agent` 全禁
  - `permissions.allow`：`Read(<staging>/**)`、`Write(<staging>/out/**)`、`Edit(<staging>/out/**)`、Bash（受 L3 约束）
- 启动：`claude -p <kickoff> --settings <staging>/isolation_settings.json --model <m>`，cwd=staging；支持 `--resume <session>` 续 pilot→review→batch 分段流程（主控审查点保留在 spawn 之间）。
- 每进程 settings=作用域仅此执行器，不动项目/用户全局配置。

### L3 PreToolUse hook 守卫（Bash 逃逸面收口）
工作区自带 `guard.py`（stdlib-only，随 L1 拷入），settings 挂 PreToolUse（匹配所有工具）：

- 对 tool_input 全序列化字符串检查：出现 repo 绝对路径、`case_tests`、`test_baseline`、`gt.json`、`..` 逃逸、`~`、staging 外绝对路径 → **deny（exit 2）**。
- **Bash 白名单语法**：仅允许 `python tools/cv_probe.py <args>` 形态 + 少量只读工具（`ls`/`file` 限工作区内）；拒绝含 `;` `|` `&&` `` ` `` `$(` 的复合命令、拒绝 `python -c`。cv_probe 的路径参数逐个解析，必须落在 staging 内。
- 每次判定 append `access_log.jsonl`（tool/decision/reason/时间戳）→ 审计产物。

### L4 合并回 + 确定性 contamination check
- 主控（或 wrapper 的 `merge` 子命令）把 `out/` 产物经**既有 manifest append 路径**收编进 run attempts；provenance 记：workspace MANIFEST sha、settings sha、guard sha、access_log 摘要（denied 计数）。
- 新确定性检查（进 `src/validator/checks/` 或独立）：①MANIFEST 无禁运文件；②access_log 无"denied 后同 token 换形态成功"的可疑序列（先做①+denied 统计，②启发式后续）。

## 2. 范围切割（本轮 vs 顺延）

- **本轮=0_reading 重读/盲重抽**（代理式 VLM、工具多、逃逸面最大、两场实验的方法论短板就在这）。
- correction/4_mep 盲重抽=run_pipeline 单-shot API 调用，合同输入天然隔离；列**核查项**（确认 prompt 组装只含合同输入，不加改造）。
- codex 执行器（danger-full-access）隔离=顺延（codex 干代码活不干重读；等 OpenAI 侧重读常态化再议）。
- OS 级沙箱（宿主 docker/bwrap）=增强钩子，接口上给 staging 根参数留位即可。

## 3. 如实限界（写进产物文档）

root + 无内核沙箱 ⇒ L2/L3 是 **harness 强制**（确定性代码判定）而非 OS 强制；理论上模型可构造混淆绕 L3 字符串检查（如 base64 shell）。相对现状（纯 prompt 自觉）是从 0 到机制级的跃迁：白名单 Bash 语法 + 禁复合命令 + 路径逐参解析后，实际逃逸需要主动对抗性构造，且 access_log 全程留痕可事后审计。

## 4. 批次与验收

- **H1**：`isolation.py` builder + MANIFEST + 禁运断言 + 单测（白名单完整/禁运拒入/manifest 哈希稳定）
- **H2**：`guard.py` + settings 生成 + 单测（允许/拒绝矩阵：cv_probe 合法调用过、复合命令拒、路径逃逸拒、gt token 拒）
- **H3**：`spawn_isolated_reader.py`（build/spawn/resume/merge 子命令）+ provenance 接线 + `new_case_guide.md` spawn 协议段改写（老 prompt 级协议标注废弃）
- 验收：全测试套绿（现 517）+ 一次 sm21 图集的**真 spawn 冒烟**（Haiku，1 图 pilot 即可，验证 settings/hook 真拦截：故意在 kickoff 里塞一句"读 /workspaces/...gt.json"应被 deny 且留痕）

## 5. 请 Codex 审的具体问题

1. L2 deny 规则的模式语法是否与 claude CLI settings 实际匹配语义一致（`Read(//abs/**)` 写法）？有无更稳的写法？
2. L3 Bash 白名单会不会掐死执行器必需动作（如 skill 里要求的 overlay 回读→那是 Read 不是 Bash，应该没事）？
3. MANIFEST 禁运断言的 token 表（gt/attempt/verdict/grade/judge）够不够，会不会误伤合法文件（如 prescan 的 `candidates.json`）？
4. merge 回收路径走既有 manifest append 是否有并发/hash 绑定坑？
5. 整体有无更简做法达到同等机制强度（欢迎推翻）。

## 6.（审后修订 2026-07-08）Codex verdict = APPROVE-WITH-CHANGES，5 MAJOR+4 MINOR 全采纳

详 [verdict](../verdict/2026-07-08_contamination_hard_isolation_design_verdict.md)。设计按以下修订执行：

1. **L2 完整 settings**（MAJOR-1）：明确 defaultMode + allow 仅 staging/out + deny 覆盖 repo/root/home/web/Agent/`mcp__*`；staging 必须在 repo 外且 spawn 时 cwd=staging；H2 验收含真实 `claude -p --settings` 冒烟（staging 内 Read 成功 / repo gt Read 被拒）。
2. **L3 结构化 Bash allowlist**（MAJOR-2 + §5.5 简化建议）：Bash 唯一放行形态=`python tools/run_cv_probe.py --request <staging内json>`（wrapper 校验 request JSON schema+逐路径 resolve 后必须在 staging 内+symlink 目标也在 staging 内）；`shlex` 解析、拒复合命令/`python -c`/`cd`/`env`/重定向；spawn 用干净 env（PYTHONPATH=staging）。
3. **cv_toolbox 布局保结构**（MAJOR-3）：staging 内保留 `src/agent/reading/cv_toolbox/` 相对结构，`tools/cv_probe.py`+`tools/run_cv_probe.py` 为薄 wrapper；H1 验收含 staging 内真实 `python tools/run_cv_probe.py`（真图冒烟）。
4. **merge 串行+原子**（MAJOR-4）：主控串行 merge + attempt index 碰撞重试 + manifest 原子写；`isolation_provenance.json` 落 attempt 目录并纳入 hash 绑定；MANIFEST/settings/guard hash/access_log 副本归档进 attempt（MINOR-4），staging 本体可清理。
5. **resume 降级为冷启传文件**（MAJOR-5）：pilot→batch 每段冷启新 session；主控 review 反馈以文件写入 staging（须过"无禁运 token"词法检查，guard 同查）；不用 `--resume`。
6. **禁运断言精确化**（MINOR-1/3）：路径/文件名精确规则=硬 block（`test_baseline/gt/**`、`gt.json`、`run_*/**`、`attempts/**`、`judge.json`、`verdict*`、`grade*`、`*_score*`、`judge_rubric.md`）；裸语义 token 只出 warning；MANIFEST source_path 记 repo-relative；access_log 每条记 tool/input hash/normalized paths/decision/reason/guard version，merge 时存全量 hash。
7. **批次改 H1 / H2 / H3a(spawn)+H3b(merge/provenance)+H3c(guide 改写)**；负例验收补 symlink、`python -c`、request JSON 引外部路径三类。
