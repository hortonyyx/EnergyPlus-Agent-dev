---
name: EnergyPlus exe 本地路径
description: D:\EnergyPlusV25-2-0\energyplus.exe — 手动跑 EP simulate 时的本地引擎位置 (Windows)
type: reference
---
**路径**: `D:\EnergyPlusV25-2-0\energyplus.exe`（bash 风格 `/d/EnergyPlusV25-2-0/energyplus.exe`）
**版本**: 25.2.0-cf7368216c

**何时用**:
- 手动验证 IDF 是否能跑通 EP（不走 run_full_pipeline.py 的 simulate 节点）
- 调用形式: `/d/EnergyPlusV25-2-0/energyplus.exe -x -w <epw> -d <output_dir> -r <idf>`
- EPW 仓内有 `data/weather/Shenzhen.epw`

**runner 解析顺序**（2026-05-07 晚 v3 修复后，[src/runner/runner.py resolve_energyplus_exe](../../../src/runner/runner.py)）：
1. `$ENERGYPLUS_EXE` env var（已写在 [.env](../../../.env)：`D:\EnergyPlusV25-2-0\energyplus.exe`）
2. `shutil.which("energyplus")` 查 PATH（CI / 别的机器可走这个）
3. `DEFAULT_ENERGYPLUS_EXE` 硬编码兜底（同上路径，本机用户确认不会改）

→ `python scripts/run_full_pipeline.py <case>` 跑到 simulate 节点会自动找到 EP，不再 FileNotFoundError。

**其他 EP 安装位置**：
- OpenStudio Application 自带 EP: `/d/Program Files/openstudioapplication-1.11.0-rc2/EnergyPlus/`（版本可能不同，优先用顶级 V25-2-0 那个）

**典型用法**（实证 sm_16_newarch 用过）:
```bash
cd <project_root>
mkdir -p <case>/output/ep_run_X
/d/EnergyPlusV25-2-0/energyplus.exe -x \
  -w data/weather/Shenzhen.epw \
  -d <case>/output/ep_run_X \
  -r <case>/output/<idf_name>.idf
# 看 ep_run_X/eplusout.end 是否 "Completed Successfully"
# 看 ep_run_X/eplusout.err 详细 warnings/severe/fatal
```
