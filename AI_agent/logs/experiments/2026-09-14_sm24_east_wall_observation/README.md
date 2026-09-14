# 东侧初次Sonnet观察：目标正确、坐标失败

只给原图、上轮Haiku R21/R06种子和开发局部任务；不含源BIM/GT。144.58秒完成，CLI估算$0.3366776，非账单。

两房位置正确，但西墙x450、东墙x605与两门框端点均错；大房南墙也偏。两个trace不采用。北锚y150附近确有全宽墙，早期审计把y128–135门叶误当外墙的判断已撤回，详见[审计](execution_audit.json)。

[trace 1](detail_01/space_traces/trace_001.png) · [trace 2](detail_01/space_traces/trace_002.png) · [实际图像运输](trace_verification.json) · [原图查看重放](execution_verification.json)。两次错误图像名工具调用随后自纠，保留完整流。后续改用受约束实际像素量测，见[工作记录](../../worklog/2026-09-14_reconstruction_measured_walls_doors.md)。
