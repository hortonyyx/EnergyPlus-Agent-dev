# 2026-09-08 按内容重新组织项目文档

用户要求不再为旧布局保留入口，直接围绕重新确定的目标组织清晰的管理体系。此次基于前轮全文审计和 `20b8d056` 的约束，不重新审阅全部历史，也不开始业务功能开发。

## 组织结果

顶层保留 Agent.md 和 README.md；project 管目标/路线/决定，design 管系统/共同模型/现有实现/评价，workflow 管工作方式/模型费用/case/会话设置。合计13份现行 Markdown，目录中不再放重复 README 或旧路径跳转页。
原31份现行正文的有效内容按职责合并，50份历史跳转页、旧 CLAUDE 兼容页和退役 YAML 指针删除。架构/能力/提案/参考/暂缓不再各自维护相似内容；实际已实现与设计目标仍清楚分开。
DeepSeek 事先明确同意、Claude/GLM 订阅调用与派工授权、Git 全权授权、全部项目记忆同步及收工动作保持有效。本地 memory 的文档路径随之更新，Agent.md 路径不变。

## 资产与引用

旧演示、prescan 实现和本地备份分别移入 archive 下对应目录；本地备份由 archive/.gitignore 忽略。历史原稿与此前恢复包继续保留，重组前布局由 `checkpoint/2026-09-08-before-content-reorganization` 保存。
logs 保留真实运行与测试数据路径：main.py 的 runtime、多个测试和 GT 工具的 experiments，以及个别回归的 reviews JSON 都仍有实际消费者。历史正文保持原样，不为保持旧管理入口而留下空跳转页。
仓库外部文档和源码中的相关引用更新到现行说明或准确的归档原稿。历史原文内部路径仍按当时布局解释，可从对应 Git 版本查看；当前导航统一以新总目录为准。

## 验证

本轮90个旧资产原始字节核对通过；13份现行文档共515行，导航链接、外部引用和会话加载检查通过。Python引用改动经语法树核对，shell及配置引用只改注释。具体结果见 [验证记录](../experiments/2026-09-08_content_reorganization/README.md)。
没有调用 DeepSeek 或其他运行模型，没有重跑全量或生成新 case。下一次业务工作见 [路线与任务](../../project/roadmap.md)。

交付采用正常commit/push，完成标签为 `checkpoint/2026-09-08-content-organized`；仍保留单一main和一个worktree。
