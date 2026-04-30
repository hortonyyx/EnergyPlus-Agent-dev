# idfpy 全线替换执行计划

> **目标**：本项目从 `eppy + 手写 Pydantic schema + 13 个 converter + ConverterManager` 全线切换到 [idfpy](../idfpy_dev/)（协作者维护）。
> **背景**：见 [CLAUDE.md §1](CLAUDE.md) 项目定位、[CLAUDE.md §3.1.2](CLAUDE.md) 现状痛点（IDD 错配 / fenestration 静默丢失 / schema 覆盖不全）。
> **本文件定位**：阶段拆分 + 角色分工 + 验收门槛。MCP 工具重写主体由协作者完成；本项目侧负责 skill / scripts / 测试数据 / 文档。

---

## 0. round-trip 验证已通过（2026-04-28）

[Tool_scripts/idfpy_roundtrip_sm15.py](../Tool_scripts/idfpy_roundtrip_sm15.py) 跑 sm_15 IDF（14 zones / 84 surfaces / 12 fenestration），结果：

| 检验 | 结果 |
|---|---|
| 对象解析 | 124 / 124 ✓ |
| `idf.validate()` 跨引用 | 0 errors ✓ |
| 几何 mixin (`area` / `normal` / `centroid`) | 直接可用，无需手算 ✓ |
| Forward nav (`surface.zone`) | 返回 Zone 对象 ✓ |
| Round-trip IDF→IDF / IDF→epJSON→重读 | 0 对象丢失 ✓ |
| 文件体积 | IDF 131k → 90k（省 31%） |

**唯一阻塞**：idfpy IDF parser 大小写敏感 bug（详见 §1.1），临时绕过 = epJSON 主路径或预处理 normalize。

---

## 1. 阶段 P0 — 阻塞解除（协作者侧 + 本项目侧并行）

### 1.1 协作者 — 修复 idfpy IDF parser 大小写 bug
- 见独立 bug 报告 [idfpy_bug_case_insensitive.md](idfpy_bug_case_insensitive.md)
- 不修也能用 epJSON 路径，但 EnergyPlus engine 输出仍以 IDF 大写为主，长期需要修
- 工作量预估：~5 行（`idfpy/idf.py:_process_block` 加 canonical case 归一化 + 1 个测试 fixture）

### 1.2 本项目 — EnergyPlus engine 版本对齐
- idfpy 当前内置 schema **26.1**，本机 engine 是 **25.2**，仓库 IDD 是 **25.1**
- 三种应对：
  1. 本机 engine 升级到 26.1（推荐，与 idfpy 主线对齐）
  2. 协作者补一份 25.2 schema 编译版（让 idfpy 可选）
  3. 暂时锁本项目用 26.1，重跑 sm_0..15 看是否有 schema breaking change
- **决策待定**，先记录，不阻塞 P1

### 1.3 本项目 — 依赖管理
- `pyproject.toml` 加 `idfpy = {path = "./idfpy_dev", editable = true}`（已 `uv pip install` 过，但需写进 lock）
- 删 `eppy` 依赖
- 不删 `data/dependencies/Energy+.idd`（保留观察期，P3 验收后再删）

---

## 2. 阶段 P1 — 小试（本项目侧主导，~3 天）

**目的**：用 idfpy 重写最小可运行链路，跑通 sm_15 几何阶段，得出实测数据指导 P2 范围。

### 2.1 范围

| 改造对象 | 操作 |
|---|---|
| **新建** `src/mcp_v2/state.py` | `ConfigState` 持有 `IDF` 实例（不动现有 `src/mcp/state.py`，并行） |
| **新建** `src/mcp_v2/api/core.py` | `create_zone` / `update_zone` / `list_zones` / `get_zone` 4 工具 |
| **新建** `src/mcp_v2/api/envelope.py` | `create_surface` / `update_surface` / `update_surfaces_batch` / `create_fenestration_surface` |
| **新建** `src/mcp_v2/api/workflow.py` | `validate_config`（直接代理 `idf.validate()`）/ `export_idf`（`idf.save()`）/ `load_idf` |
| **新建** `src/mcp_v2/server.py` | 注册到 `EnergyPlus-Agent-v2` 单独 MCP server name |
| **新建** `Tool_scripts/sm15_replay_idfpy.py` | 用 v2 工具 + sm_15 claude_ep.md 数据 build IDF，与原 sm_15.idf 比对 |

### 2.2 验收
- sm_15 几何阶段 IDF round-trip：counts 一致 / `idf.validate()` 0 errors
- LLM 在 v2 工具下走完几何阶段，token 总量与现有 §3.1+§3.2 P0 完成态对比
- `Tool_scripts/export_idf.py` 5 条补丁 → 看哪些能丢（idfpy 的 `validate()` 已可顶替补丁 0/3/4）

### 2.3 决策点
P1 完成后回答两个问题：
1. **MCP 工具粒度还要不要 79 个？** idfpy 让 CRUD 几乎归一化为 `idf.add(obj)` / `idf.get(...)` / `idf.remove(...)` 三招，工具数预计可压到 ~20-25
2. **batch 接口是否还有必要？** idfpy 内部全是 Python 对象操作（不经 MCP），同一 tool call 内多次 `idf.add` 无 round-trip 开销，`update_surfaces_batch` 价值大幅下降

---

## 3. 阶段 P2 — 全量切换（协作者主导 MCP，本项目侧并行 skill / scripts / 数据，~1.5-2 周）

### 3.1 协作者负责（MCP 工具重写）

| 改动 | 说明 |
|---|---|
| **删** `src/validator/data_model.py` | 33 个 Pydantic Schema → idfpy 自动生成的 859 个 |
| **删** `src/converters/`（13 文件） | YAML→IDF converter → `idf.add(obj)` 直写 |
| **删** `src/converter_manager.py` | 不再需要"转换器编排" |
| **删** `src/runner/runner.py` | 替换为 `idfpy.sim.simulate()` 薄包装 |
| **重写** `src/mcp/state.py` | `ConfigState` 改持 `IDF` 实例，`*_specs` 字典全废 |
| **重写** `src/mcp/api/`（7 个 group） | 工具数 79 → 估 20-25，CRUD 直接代理 idfpy |
| **重写** `src/mcp/tools/base.py` | 不再需要 `BaseTool` 抽象，idfpy 已有 instance 生命周期 |
| **决定** batch 接口是否保留 | 见 §2.3 决策点 2 |
| **决定** `update_surface` 的"修正 boundary"流程 | idfpy 的 `surface.zone` / `.normal` 让自动 boundary 推断（[token_optimization.md §4.5](token_optimization.md)）实现量级降低 |

### 3.2 本项目侧并行（skill / scripts / 文档 / 测试数据）

| 改动 | 说明 |
|---|---|
| **重写** `skills/energyplus_mcp/energyplus_mcp_prompt.md`（主） | 删 ConverterManager / YAML 中介 / 4 条手工补丁规范；按 idfpy 思路（idf.add → idf.validate → idf.save）重写工具调用流程 |
| **重写** `skills/energyplus_mcp/zonetool_prompt.md` | 适配新 create_zone API（参数名可能变） |
| **删** `skills/energyplus_mcp/schedule_compact_guide.md` | idfpy 的 Schedule:Compact 由 Pydantic schema 强校验，不需要文档级规范 |
| **重写** `skills/energyplus_mcp/export_idf.md` + `Tool_scripts/export_idf.py` | 大幅缩减：补丁 0/3/4 由 idfpy.validate 顶替；保留补丁 1/2（数据填充） |
| **重写** `skills/energyplus_mcp/open_model/energyplus_mcp_prompt.md` | 同主版同步 |
| **更新** `AI_agent/new_case_guide.md` | 验证清单从 5 档调整（`validate()` 顶替原 P0/P1 几道关） |
| **更新** `AI_agent/CLAUDE.md` | §3.1.2 的"系统性缺陷"部分加注"已被 idfpy 解决"；§7.7 几何/MEP skill 拆分计划落到 idfpy 之上 |
| **重写** `AI_agent/token_optimization.md` | §3.1 ack-only / §3.2 batch 重新评估（很多 CRUD 工具消失）；§4.5 自动 boundary 推断借 idfpy mixin 大幅简化 |
| **删** `data/dependencies/Energy+.idd` | P3 验收稳定后再删 |
| **迁移** `data/schemas/*.yaml` 测试用 YAML | 写一次性脚本：旧 YAML → idfpy 对象 → 重存 epJSON（本项目内只读 epJSON） |
| **重做** `test_data/test_baseline/` 全部 anchor | 旧 anchor 基于已废 harness + 已废 converter，全部失效；用 sm_15 在新栈下重建 |
| **保留** `test_data/SmallOffice/smalloffice_*/` 输入数据 | testdata_prompt.json + 4 张 view 不动；`output/` 子目录全部需重跑 |

### 3.3 不动的部分
- `src/rag/`、`src/database/`、`src/configs/`（embedding 路径）—— 与 idfpy 无关
- `src/agent/`（LangGraph 多模态 agent）—— 多模态入口不变，下游 IDF 构建工具集换成新 MCP server
- `Tool_scripts/preprocess_images.py`、`Tool_scripts/baseline_record.py` —— 与 idfpy 无关

---

## 4. 阶段 P3 — 全量回归 + 验收（本项目侧，~3-5 天）

### 4.1 验收门槛

| 项 | 要求 |
|---|---|
| sm_0 ~ sm_15 round-trip | 旧 IDF → idfpy → epJSON → idfpy → IDF，counts 一致 / `validate()` 0 errors |
| sm_15 几何阶段重跑 | LLM 用新 MCP 工具走完，counts 与 anchor 一致（14/84/12） |
| EnergyPlus 仿真 | sm_0（已知唯一能起仿真的）在新栈下仍能起仿真，结果不变（参考 [CLAUDE.md §3.1.2](CLAUDE.md) sm_0 Fatal 根因，新栈应消除） |
| token 实测 | sm_15 重跑取 `/context` total，与 §0 deferred MCP 架构下旧 anchor 横向对比；预计 messages 段下降 30%+（CRUD 工具大量消失） |
| 双向 round-trip | `IDF → from_dict → IDF` / `IDF → epJSON → IDF`，对象数 + key 字段 100% 一致 |

### 4.2 重建 baseline anchor

- `test_data/test_baseline/runs/2026-XX-XX_sm15_idfpy_v1/`
- `meta.pipeline_version: "idfpy_v1"`（与旧 `yaml_to_idf_v1` 分桶，不直接比较 token / counts）
- 至少 3 个 case：sm_15 几何 / sm_0（含 MEP）/ sm_13（多 case 完整流水线）

### 4.3 切换发布
- 主分支 PR 合并前：在 `Skill_history/` + `MCP_history/` 各建一份切换前快照
- 合并后立即更新 [README.md](../README.md) 项目结构 + 技术栈
- `pyproject.toml` 删 eppy 依赖

---

## 5. 风险登记

| 风险 | 缓解 |
|---|---|
| idfpy 是 alpha，可能在 P1/P2 暴露更多 bug | 协作者直接维护，BUG 反馈周期短；用 round-trip + `validate()` 双重保护 |
| EnergyPlus 26.1 vs 25.2 schema 不一致 | 见 §1.2，先在 P1 暴露差异 |
| MCP 工具粒度变化对 LLM 行为冲击 | skill 强约束改写 + 小试阶段 sm_15 比对；预设 Opus fallback |
| 旧 case（sm_0..14）若某些 IDF 因 bug #1 解析失败 | epJSON 主路径绕过；或写一次性 case-fix preprocessor |
| LangGraph agent 端不改但 MCP server name 改了 | 仅改 `.mcp.json` 的 server name 映射，agent 侧 import 路径不动 |
| token_optimization.md §3.1/§3.2 已落地的优化被 P2 推翻 | 节省指标重评；CRUD 工具数减少本身就是 token 节省，方向一致 |

---

## 6. 时间预算

| 阶段 | 时长 | 主导方 |
|---|---|---|
| P0 阻塞解除 | 1-2 天 | 协作者（bug 修复）+ 本项目（依赖） |
| P1 小试 | ~3 天 | 本项目 |
| P2 全量切换 | ~1.5-2 周 | 协作者（MCP）+ 本项目（skill / scripts / 数据，并行） |
| P3 验收 | ~3-5 天 | 本项目 |
| **合计** | **~3-4 周** | |

---

## 7. 当前 Next Step

1. **协作者**：阅读 [idfpy_bug_case_insensitive.md](idfpy_bug_case_insensitive.md)，修复 IDF parser 大小写 bug（不阻塞 P1，但越早越好）
2. **本项目**：决策 EnergyPlus engine 版本（升 26.1 / 锁 25.2 / 等协作者补 25.2 schema），见 §1.2
3. **本项目 P1 启动**：`src/mcp_v2/` 起步，先做 `core.py` + `envelope.py` 两个 group，跑 sm_15 几何阶段
4. **冻结 token_optimization.md §4 计划项**：§4.1 / §4.2 / §4.3 / §4.4 / §4.5 全部暂停，避免在 P2 推翻前重复投入

---

_最后更新：2026-04-28 — 首版起草。基于 sm_15 round-trip 验证（[Tool_scripts/idfpy_roundtrip_sm15.py](../Tool_scripts/idfpy_roundtrip_sm15.py)）通过的事实，列 P0-P3 四阶段、协作者/本项目分工、验收门槛、风险登记_
