# sm24：同一份源 BIM 的关闭门 EP 分叉

2026-09-09，最终 run02 已全年运行成功：**8 热区、58 基面、11 窗、1 源门对应 2 个 EP 门面，0 严重错误、5 警告**。源文件及其中门的 unknown 状态保持不变。

- [源 BIM 查看](../2026-09-09_source_bim_run04/sm24_assisted/viewer.html)、[源文件](inputs/source_model.json)
- [EP 运行报告](ep/report.json)、[实际完成记录](ep/EP/eplusout.end)、[完整警告](ep/EP/eplusout.err)
- [最终 IDF](ep/model.idf)、[源映射与门策略审计](ep/source_mapping.json)、[EP 几何](ep/building_geometry.json)
- [独立门策略](inputs/opening_policy.json)、[物性来源和假设](inputs/provenance.json)
- [无门策略时的拒绝记录](without_policy/report.json)、[复现命令及代码哈希](report.json)
- [115 项测试记录](tests.txt)、[完整 EP 原始输出](ep/EP_outputs.tar.gz)

本案来自历史辅助 sm24 八空间模型，门位置和宽度由旧 reading 人工转录，门高假设 2.1m。源几何自洽检查通过，上一程独立评价仍有 3 条严重分区差异；EP 成功不改变该结论，不是新原图冷启动或整案保真通过。

源门 `corridor_north_mouth` 保留 unknown。独立策略明确本次仿真按全年关闭处理，使用实验不透明门构造；并未声称图纸观察到了关闭状态。源门只有一份，两侧 Door 子面互相配对，均回指该源门。已知敞开门和空通道继续拒绝导出，不能用实体门代替。

物性使用 sm21 无几何模板的材料、作息与对象样板，按这八个源空间重新绑定。统一 0.1 人/m²、10 W/m² 照明、每空间一套理想负荷系统；门热阻 0.25 m²K/W、无热容。这些是工程贯通假设，不是协作者已交付或校准物性。5 条警告分别为默认时间步、未给设计日、采用天气文件地点、未给地温、1 个未使用构造。

从仓库根复现，须使用新的输出目录；不调用产品模型或 GT：

```bash
python scripts/tool_scripts/diagnose_ep_doors.py --out AI_agent/logs/experiments/NEW_EP_DOORS_RUN --with-ep
```

脚本先验证同一源输入在缺少门策略时被拒绝，再通过真实 `backend-ep --opening-policy` 命令写入和运行。完整命令在 `report.json`，省略 `--with-ep` 时仅导出，不算仿真成功。复现物性与源输入已保存，协作者正式接口见 [契约](../../../design/ep_physics_contract.md)。

首次 run01 在 IDF 写入前的子面核查暴露了源 ID 字段访问错误，尚未启动 EP；代码修复后新建 run02，未覆盖失败证据。[失败记录](../2026-09-09_ep_doors_sm24_run01/ep/report.json) 仍可查看。本次只有最终 run02 调用了一次 EnergyPlus。派工和完整交接见 [工作记录](../../worklog/2026-09-09_ep_doors.md)。
