# energyplus_mcp migration audit (2026-05-11)

## Scope

目标：检查 `skills/energyplus_mcp/*.md` 是否已经把旧流程里与“识图 -> 几何理解 -> 下游可恢复 spec”有关的约束完整迁移到当前新架构。

本次审计依据：

- 当前 intake 装配点：[src/agent/nodes/intake.py](../src/agent/nodes/intake.py)
- 当前规则库：
  - [skills/energyplus_mcp/energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md)
  - [skills/energyplus_mcp/intake_output_contract.md](../skills/energyplus_mcp/intake_output_contract.md)
  - [skills/energyplus_mcp/zonetool_prompt.md](../skills/energyplus_mcp/zonetool_prompt.md)
- 旧流程外显产物样例：
  - [AI_agent/backup/new_case_guide.md.bak_2026-05-06](backup/new_case_guide.md.bak_2026-05-06)
  - [test_data/SmallOffice/smalloffice_16/output/claude_ep.md](../test_data/SmallOffice/smalloffice_16/output/claude_ep.md)

说明：这里把旧 `sm16` 产物只当作“旧流程显式要求了哪些识图中间事实”的证据，不拿它做新 case 的正确性对拍。

## Executive summary

结论：**大部分核心识图规则已经迁入新架构，但还不能判定为“完整迁移完成”**。

当前状态更接近：

- intake 装配层已经正确接入 rule library，`skills/energyplus_mcp/*.md` 不是 dead code
- 共享外包、坐标系、逐层分区、blank facade、window-parent-wall、命名一致性等主干规则已经迁入
- 但旧流程里若干决定稳定性的“强制外显几何脚手架”现在只剩“内部完成”的软约束
- 立面逐层独立窗链这一点仍未写成足够硬的规则，`sm16` 类 facade 有误读风险

## What is already migrated

### 1. intake 确实会整包加载规则库

[src/agent/nodes/intake.py](../src/agent/nodes/intake.py) 会：

- 读取 `skills/energyplus_mcp/*.md`
- 逐文件拼进 system prompt
- 明确要求“把整包 markdown 当作 mandatory instructions”

这说明当前识图规则的主载体已经切到文档库，而不是散落在一次性 prompt 里。

### 2. 旧流程最核心的几何主线基本都在

当前文档已覆盖这些关键能力：

- 输入包结构、逐层 floor plan、back-compat top view
- image label 权威化
- shared-footprint invariant
- dimension-chain checksum
- 单一世界坐标系
- room enumeration -> role assignment -> coordinate synthesis -> topology synthesis -> fenestration synthesis 的顺序化推导
- corridor / stair / WC / lift / lobby / service room 显式识别
- blank facade = zero windows
- window 必须落在真实 exterior wall
- `zone_specs` / `surface_specs` / `fenestration_specs` 必须可机械恢复

对应证据：

- [energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md)
- [intake_output_contract.md](../skills/energyplus_mcp/intake_output_contract.md)
- [zonetool_prompt.md](../skills/energyplus_mcp/zonetool_prompt.md)

### 3. 旧 `claude_ep.md` 里的关键信息类型，已经被新合同映射到 prose specs

旧流程外显的是：

- Dimension Extraction
- Floor plan diagram / ASCII sketch
- adjacency matrix
- zone coordinates table
- fenestration table

新规则没有再要求输出这些中间文件，但已经明确要求 intake 在内部恢复同类事实，并把它们压进：

- `zone_specs`
- `surface_specs`
- `fenestration_specs`

这部分迁移方向是对的。

## Gaps not fully migrated

### Gap A. facade window chain 仍缺“逐层独立读取”的硬约束

当前 [energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 对 facade 的说法还是偏单层抽象：

- `bottom horizontal chain = window placement along the facade`

但旧 `sm16` 立面实际需要：

- 北立面按 F3 / F2 / F1 各自读取不同 horizontal chain
- 东西立面也需要逐层判断 blank vs non-blank

证据见 [smalloffice_16/output/claude_ep.md](../test_data/SmallOffice/smalloffice_16/output/claude_ep.md) 的 North / East / West facade 段。

影响：

- 对 `sm16` 这类“不同楼层窗链位置不同”的 facade，新文档没有把“per-floor chain, read separately, never share blindly”写成硬约束
- 这会让模型更容易退回成“全立面一条链”的过度简化

结论：**这一块还没迁完。**

### Gap B. 旧流程的“强制外显几何脚手架”变成了“内部完成即可”

旧 guide 强制要求：

- 每层标注图
- `claude_ep.md`
- 逐层 shared-footprint checksum
- 逐层 adjacency matrix
- 逐层 zone coordinates table
- fenestration table

见 [backup/new_case_guide.md.bak_2026-05-06](backup/new_case_guide.md.bak_2026-05-06)。

新文档虽然加了 “Mandatory Internal Derivation Order” 和 “Topology Sketch Requirement”，但不再要求这些几何事实必须以可审计中间格式外显。

影响：

- 规则意图在，但可复核性下降
- 一旦 intake prose 写得不够密，新架构更难区分“模型真的理解了几何”还是“只是写了看起来合理的自然语言”

这不是纯缺失，而是**约束强度下降**。

### Gap C. unsupported-case 语义还没完全统一

手工 Step 4 约定是：

- 外包不一致 -> 直接停下

见 [AI_agent/new_case_guide.md](new_case_guide.md)。

但当前 [energyplus_mcp_prompt.md](../skills/energyplus_mcp/energyplus_mcp_prompt.md) 同时写了：

- manual step 4: stop
- structured-output runtime path: 仍返回 `IntakeOutput`，但把不一致写进 specs

影响：

- 新架构不同入口对同一 unsupported geometry 的行为不完全一致
- 旧流程的 fail-fast 守门没有完全收束成一条规则

### Gap D. metadata/contract 层仍缺“旧脚手架对应到 prose 的最小密度模板”

当前 contract 已要求 `zone_specs` / `surface_specs` / `fenestration_specs` “机械可恢复”，但还没把旧脚手架对应成足够硬的 prose 模板，比如：

- `zone_specs` 至少要达到“逐层坐标表”密度
- `surface_specs` 至少要达到“逐层 adjacency matrix + exterior/interior mapping”密度
- `fenestration_specs` 至少要达到“逐窗一行记录 + facade chain provenance”密度

虽然文档已经朝这个方向写了 preferred structure，但“必须包含哪些最小事实字段”的语气还可以更硬。

## Assessment

如果问题是：

- “现在这套文档是不是已经把旧流程的识图能力主干迁进来了？”

答案是：**是，主干已迁入。**

如果问题是：

- “现在这套文档能不能说已经把旧流程的稳定识图约束完整迁完了？”

答案是：**还不能。**

当前更准确的判断：

- **迁移完成度：约 75%~85%**
- 缺的不是大框架，而是几处会直接影响 `sm16` 类案例稳定性的硬约束强度

## Recommended next edits

1. 在 `energyplus_mcp_prompt.md` 的 facade 规则里补硬约束：
   - horizontal window chains may differ by floor
   - read each floor's window chain separately
   - do not reuse one floor's chain for another unless the facade explicitly shows it

2. 在 `intake_output_contract.md` 里把以下语义从 “preferred” 提升到 “required minimum density”：
   - `zone_specs` ~= per-floor coordinate table
   - `surface_specs` ~= per-floor topology / adjacency recovery contract
   - `fenestration_specs` ~= one-record-per-window recovery contract

3. 统一 unsupported shared-footprint case 的 fail-fast 语义，至少在生产入口上不要双标。

4. 若目标是恢复旧架构在 `sm16` 的稳定度，建议在 intake 自检中新增一条：
   - verify per-facade per-floor window counts and spans are mutually consistent before final prose generation

## Bottom line

这次检查支持一个比较明确的判断：

**新架构并不是“没接上旧识图规则”，而是“已经接上了大部分规则，但还差几条关键硬约束，尤其是 facade 逐层窗链与旧几何脚手架的强制外显等价物”。**
