# sm24 墙与门的局部量测、裁定、应用

这是开发编排的实验入口，不是固定产品流程。完整结果、费用和介入边界见[工作记录](../../worklog/2026-09-14_reconstruction_measured_walls_doors.md)。

- `observe.py`：东侧Sonnet初次观察，坐标错，未应用。
- `observe_measured.py`：Haiku先用连通区/墙支持量测，门框正确、完整边界解释错误。
- `review_measured.py`：Sonnet接收原样量测并裁定共同代表线，未输入源BIM或GT。
- `apply_two_traces.py`：两trace→三空间保守重分配、两门显式更新；逆时针环、完整共边和原外缘必须满足。首次run10环向失败，修后run11成功。
- `observe_west_doors.py`：仅原图首次错选外墙；`--with-source-wall-hint`给代码由run11投影的疑似内墙线后正确量出三门，无旧门位置/期望门数。
- `apply_west_doors.py`：按保存的模型门框文字与profile应用三门，开发显式撤回连续墙上的旧假门，生成run12。
- `verify_original_views.py RUN`、`verify_trace_transport.py RUN`：复用前轮核验代码，适配完成标记/工具清单，核实际返回图、原坐标及区域/trace重放。
- `verify_west_application.py`：验证run12只改三门/删一假门、其他源对象保留及完整操作/导出/回叠重放。

运行目录固定且拒绝覆盖；重跑先选择新输出。各run保留实际脚本快照及摘要，不用当前文件冒充历史调用代码。源审计复用`../2026-09-13_east_partition_setup/audit_source.py`；独立GT评价只在完成后运行`../2026-09-12_sm24_delegation_setup/evaluate.py`。浏览器沿用已安装环境及旧`browser_check.py`，未新增依赖。
