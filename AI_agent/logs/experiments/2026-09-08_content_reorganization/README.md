# 文档按内容重组的验证记录

基线：`20b8d056`，检查点：`checkpoint/2026-09-08-before-content-reorganization`。

- [document_map.json](document_map.json)：83个旧文档/配置路径的内容去向；用于本次审计，不在旧位置保留兼容入口。
- [asset_manifest.json](asset_manifest.json)：90个移动资产的前后位置及SHA-256，本地备份内容不会因此提交。
- [source_reference_map.json](source_reference_map.json)：外部文档/源码引用更新范围。

原业务运行产物仍在既有 logs/case 位置，原文归档不变。结果见 [validation.json](validation.json)：13份现行文档、515行；现行文档与维护中的导航链接无断链；90个移动资产哈希一致，65个本地备份文件仍被忽略。

18个Python文件的引用改动通过语法树核对：去掉文档字符串并规范化本次文档路径后，计算结构一致。3个shell脚本及.env.example/.gitignore只改注释；没有修改模型配置、几何算法或真实case产物。
新会话实际读入新的project/workflow路径和DeepSeek事先同意约束。无需pytest全量，没有调用运行模型。
