# Haiku：门框量测改善，完整参考面解释仍错

原图、既有区域种子及前次Sonnet标定假说，加开发指定先region/再据墙支持判门的工作方式。100.18秒完成，CLI估算$0.1249622，非账单。

两门断口y322..357、381..416有实际区域轮廓与灰支持区间共同支持。但小房南界366、大房北界372是同一墙两侧；东界602为内面。两份完整trace拒绝直接应用。后续Sonnet只处理该参考面冲突，不重新凭缩略图猜门。

[量测审计](execution_audit.json) · [原图查看重放](execution_verification.json) · [实际返回图/区域/trace重放](trace_verification.json) · [西墙支持](detail_01/pixel_profiles/profile_001.png)。工具参数误用/重试保留，不以几何可执行或模型“已完成”自述代替图意核验。
