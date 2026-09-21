# 开发侧原图开口方向对照

[可视对照](index.html) · [原图观测及人工选择](observations.json) · [计算结果](comparison.json)

本次从原平面/East图选取四组开口。直接同向最大端点误差8.03196m、平均5.72336m；反向最大0.01756m、平均0.00892m。计算不读取GT或旧BIM，不自动改源，也没有进入本批两份模型运行。裁区、开口分组、参考端点和标定由开发助手选择；这是可迁移方法的确定性探针，尚非工作模型自主识读或整案恢复。

工具保存七次扫描及原坐标/颜色阈值。profile_006漏掉若干立面刻度，改用已观察颜色范围后profile_007读齐；两次都保留。门洞内部弧线候选不当成新增开口，具体选择说明在observations.json。

`compare_facade_spans.py`保留正反两个假设；完整清单数量不等时保留未配对象并不给方向结论；对称或接近对称的布局不强选方向。反向匹配、对称歧义、数量不等保留、真实结果重放及图像散列检查见[验证](verification.json)。[离线页面](browser_verification.json)已核3条比较轴/12条开口条带，无外部请求。

复现量测和计算可运行：

```sh
python AI_agent/logs/experiments/2026-09-21_sm24_autonomous_review_setup/prepare_direction_probe.py --out /tmp/sm24_direction_new_run
```

输出目录必须未存在。脚本重新量测原PNG，并明确复制本次开发选定的observations.json作为计算输入；不会重新自主选择开口。通用比较器也可单独传`--input`和新的`--out`，同目录README中的实验模型仍不读取此探针。
