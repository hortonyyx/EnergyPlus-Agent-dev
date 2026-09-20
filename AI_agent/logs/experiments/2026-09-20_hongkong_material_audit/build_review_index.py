"""Render the explicit developer visual review and case entry; no automatic quality classifier."""
from pathlib import Path
import json, html
root=Path(__file__).resolve().parents[4]/'case_tests/textured_mass/hongkong/repaired_buildings'
rows=json.loads((root/'review.json').read_text())
notes={
'B415681874001063A0':('不优先','四面纹理模糊或被植被覆盖，无法可靠指出窗/入口；只宜保留为低信息反例。'),
'B416111881201063A0':('优先复核','补齐四材质后，长立面多排窗和层间带可辨，体量较规则；低层受树木遮挡，具体用途与入口仍待核。'),
'B419431906102063A0':('局部可读','低矮退台体量可见，立面受树遮挡且部分模糊；原84.4m高层标签错误，实际是长边84.4m。'),
'B338831602701063A0':('不优先','细长对象，大面积灰面和模糊色带，楼层/窗难以可靠分辨；不是已确认的单层体量。'),
'B338311587601063A0':('不优先','灰面及严重拉伸/模糊纹理占主导，不能用21面推定标准层重复。'),
'B342781599201063A0':('不优先','高塔及低基座可见，立面暗且大面积灰面；保留透明材质后现观察器不支持，完整浏览器可看。'),
'B213323371901062A0':('局部可读','正面少数开口可见，另外两向纹理明显拉伸/模糊；小体量但信息不充分，用途未证。'),
'B212263385501063A0':('局部可读','高塔窗排与外挑形态明显，但近重复细节复杂且顶部/底层证据有限；可作后续压力例，不是低层大平面。'),
'B352801986901063A0':('不优先','只有窄立面保留部分窗，大片灰面；单层商业标签错误，形体是高窄体。'),
'B353902007902063A0':('不优先','低矮长体的图像拉伸和复杂屋顶/临时构件混杂，不能作窄高简单样本。'),
'B346922109101063A0':('不优先','大面灰填充，仅一窄侧能见局部窗，四面输入明显不足。'),
'B349992122201063A0':('优先复核','两主要立面可见逐排开口，支持局部窗/层观察；另一面模糊且有灰面，底层遮挡，复杂度高于规则首例。'),
'B351842110002063A0':('局部可读','低矮建筑正面能见招牌/开口，屋面及背侧灰填充；原35.7m高楼标签错误，实际是平面长边。'),
'B353631509302063A0':('局部可读','低体量混合立面局部可读，大片灰面/植被和幕墙反射；不能沿用高层办公标签。'),
'B359571551401063A0':('局部可读','高窄建筑两侧水平开口带可辨，另侧纹理较模糊；不是原标注的低矮长条，首层和用途仍待核。'),
}
review=[]
for row in rows:
 bid=row['building_id'];lo,hi=row['viewer']['bounds_y_up_m'];extent=[round(hi[i]-lo[i],3) for i in (0,2,1)]
 grade,note=notes[bid];review.append(dict(building_id=bid,review_priority=grade,visual_findings=note,width_depth_height_m=extent,scene_parts=row['viewer']['parts'],faces=row['viewer']['faces'],mesh_observation=row['mesh_observation']['status'],building_use='not_verified',review_scope='开发助手检查四个修复后斜立面视图；不是逐窗测量、照片真值或建筑用途验收'))
(root/'visual_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
style='''<meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>body{font:16px/1.65 system-ui;color:#21324a;background:#f5f7fb;margin:30px auto;max-width:1400px;padding:0 20px}a{color:#146bbc}article,header{background:white;border:1px solid #d2dbe7;border-radius:12px;margin:20px 0;padding:22px}.images{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}img{width:100%}button{padding:8px 16px;margin:6px;cursor:pointer}.badge{border-radius:6px;background:#e6f2f6;padding:4px 8px}small{color:#4a5c71}@media(max-width:750px){.images{grid-template-columns:1fr}}</style>'''
page=style+'<title>香港15个素材：修复及质量复核</title><header><h1>15 个香港素材：先恢复完整模型，再看质量</h1><p>已纠正全批轴向，补回两例丢失的62个三角面。15份完整场景均可离线旋转；现有建模观察工具14份可读，1份透明材质明确不支持。</p><p>2份优先复核候选，其余保留作局部可读或低信息样本。建筑用途均未逐栋核实，本页没有BIM生成或整案验收。</p><p><a href="../README.md">方法、原件与限制</a> · <a href="review.json">转换与浏览器核验</a> · <a href="visual_review.json">逐栋判读</a></p><button onclick="filter(\'\')">全部15份</button><button onclick="filter(\'优先复核\')">优先复核2份</button><button onclick="filter(\'局部可读\')">局部可读</button><button onclick="filter(\'不优先\')">不优先</button></header>'
order={'优先复核':0,'局部可读':1,'不优先':2}
for row in sorted(review,key=lambda r:order[r['review_priority']]):
 bid=row['building_id'];dims=' × '.join(f'{v:.2f}' for v in row['width_depth_height_m'])
 page+=f'''<article data-grade="{row['review_priority']}"><h2>{bid} <span class="badge">{row['review_priority']}</span></h2><p>{row['visual_findings']}</p><p>宽 × 深 × 高：{dims} m · {row['scene_parts']}材质网格 / {row['faces']}三角面 · 观察工具：{row['mesh_observation']}</p><div class="images"><div>旧错误转换预览<img loading="lazy" src="../single_buildings/{bid}/view.png"></div><div>完整转换 A 面<a href="{bid}/viewer.html"><img loading="lazy" src="{bid}/view_A.png"></a></div><div>完整转换 C 面<a href="{bid}/viewer.html"><img loading="lazy" src="{bid}/view_C.png"></a></div></div><p><a href="{bid}/viewer.html">旋转查看完整模型</a> · <a href="{bid}/view_B.png">B面</a> · <a href="{bid}/view_D.png">D面</a> · <a href="{bid}/input.glb">修复GLB</a> · <a href="{bid}/repair.json">转换依据</a></p><small>© 香港特别行政区政府 地政总署；仅转换与局部坐标平移，未补面、未增强纹理。用途和物理窗界仍须核实。</small></article>'''
page+='''<script>function filter(g){document.querySelectorAll('article').forEach(x=>x.hidden=g&&x.dataset.grade!==g)}</script>'''
(root/'index.html').write_text(page)
# README is the current entry; the exact received text remains in audit snapshot.
text='''# 香港单体素材：09-20 完整转换与质量重审

[打开15例对照与旋转模型](repaired_buildings/index.html) · [独立转换审计](../../../AI_agent/logs/experiments/2026-09-20_hongkong_material_audit/conversion_audit.md) · [来源/选样复核](../../../AI_agent/logs/experiments/2026-09-20_hongkong_material_audit/source_review.md)

09-18按建筑ID从香港地政总署单体化模型取得15份素材。09-20接手发现旧转换只取第一个网格，丢原节点轴向变换；**全批在观察器里侧躺，两例丢62面及部分贴图**。旧文档把平面深度当高度，由此给出的单层/高层、用途和质量梯度不成立。原始下载CRC有效，但格式可读不证明转换完整或适合读窗。

`single_buildings/`保留原下载文件、旧错误GLB、预览和记录；`repaired_buildings/`保存全场景新GLB、转换依据、四视图及自包含查看器，原件没有覆盖。完整场景采用标准Y-up，观察器再映射到Z-up；只加统一平移去大地图坐标，未旋转建筑相对世界的关系、补面或增强贴图。所有原压缩图像字节、材质、UV、节点关系保留。

## 当前结果

- 15/15全场景的节点实例、顶点、UV、材质与原图字节对照通过；两primitive+多实例变换合成回归通过。
- 15/15实际离线浏览器四向查看通过，贴图全载入、面数一致，无脚本错误/外部请求。查看器为无光照双面观察，不等于完整PBR效果。
- 14/15可由现有`MeshObservation`读取；B342…完整场景包含原生BLEND透明材质，工具明确拒绝。透明面保留，不能丢掉它换取“15/15通过”。
- 2例优先继续核实身份/用途与关键立面；其他为局部可读或低信息反例。不是15个已验收建模案例，不以建筑ID、面数、JPG大小或整图像素/面积代替实际质量。

| ID | 宽×深×高 m（纠正轴向） | 本次目视分组 | 限制 |
|---|---|---|---|
'''
for row in review:
 dims='×'.join(f'{v:.2f}' for v in row['width_depth_height_m']);text+=f"| {row['building_id']} | {dims} | {row['review_priority']} | {row['visual_findings']} |\n"
text+='''
这次检查四个斜立面整体图，不是逐窗真值标注。灰面可能是贴邻/原采集未覆盖，不能直接当作实际无窗；模糊或树遮挡要保留未知。用途仍全部未核实，旧`selection.py`标签只是历史选择理由。

## 复现与后续采集

```bash
# 不访问网络，从已下载原glTF全量重装，另存新目录，并实际离线查看。
# --screenshots 需要本机已有 Playwright/Chromium。
python case_tests/textured_mass/hongkong/review_buildings.py --screenshots
# 单栋打包，不改变原场景：
python case_tests/textured_mass/hongkong/pack_building.py source.gltf output.glb
# 新下载批次务必用新目录，完整转换已接入；不会自动覆盖09-18旧记录。
python case_tests/textured_mass/hongkong/fetch_buildings.py --out /path/to/new_batch
```

`fetch_buildings.py`沿用HTTP Range读取ZIP中央目录、只取目标条目并逐个CRC校验。首次15栋传输约24.2MB；09-20修复不重新下载。`verify_buildings.py`现只检查修复目录的格式兼容性，明确报告14可读/1透明材质不支持；完整转换与查看入口为`review_buildings.py`。原版脚本及README在[接手快照](../../../AI_agent/logs/experiments/2026-09-20_hongkong_material_audit/received_2026-09-18/)保留。

先核优先候选的实际用途与正立面证据，若不符合普通办公/住宿/商业研究对象，再从已知可读的Helsinki官方原件挑简单单体，Melbourne 2020作备选；不再按错误梯度批量凑样。开放IFC合成输入仍按用户决定保留待议，本轮未展开。

## 来源与存储

© The Government of the Hong Kong SAR (Lands Department)。数据集：3D Visualisation Map (Individualised models)，原发布页及条款见[来源复核](../../../AI_agent/logs/experiments/2026-09-20_hongkong_material_audit/source_review.md)。本地转换与观察页由项目制作，非发布方原件。

原`.gltf/.bin/.jpg`及渲染缓存按既有`.gitignore`留本地，可凭逐栋record重新取；旧GLB/记录及新自含GLB/查看器/四视图入Git。自含GLB内保留原图压缩字节，查看器复用同一字节，不以二次压缩降低质量。
'''
(root.parent/'README.md').write_text(text)
