# Sim BIM Agent

从建筑图纸、图片或三维网格生成可查看的轻量 BIM。当前主要研发方向为图纸分工建模。程序通过自有 runtime 接模型服务，不需要 Codex 进程。

## 开始使用

本目录包含已验证的程序与资源。已安装环境时直接使用 `Start.cmd`；重建环境时在 PowerShell 执行 `./setup.ps1`（需 Python 3.12 和 uv）。

```powershell
./Start.cmd doctor
./Start.cmd demo --output D:/Sim-BIM-Agent/runs/my-first-demo
./Start.cmd auth status
./Start.cmd auth login
./Start.cmd auth models
./Start.cmd check D:/Sim-BIM-Agent/my-run.json
./Start.cmd run D:/Sim-BIM-Agent/my-run.json --case my-building
./Start.cmd run D:/Sim-BIM-Agent/my-run.json --case my-building --resume
```

`doctor` 检查文件、版本与依赖，不联网。`demo` 使用明确标记的两房间合成示例，生成源 BIM 和离线 HTML 查看页，不调用模型，也不代表真实建筑识读质量。每次演示使用新的输出目录。

## 输入和输出

复制 `config.example.json` 到自己的工作目录，按实际情况修改输入位置、模型和运行设置。`input_root` 是本次获准使用的输入根，`input` 是其中一个案例子目录；`run_root` 是独立输出目录，`output` 是本次运行名。避免把整个盘或程序目录当作运行根。图纸、输出和凭据不放在安装目录，更新程序不会覆盖它们。

`input_kind: "images"` 要求 `input` 指向至少包含一张可读 PNG 的目录；该目录直接包含的每个 `*.png` 都必须是有效图片文件，不能引用目录外的图片。图片不递归读取，目前不接收 JPEG 或 PDF。`floor_plan_images` 如有填写，必须使用这些 PNG 的准确文件名。单模型的 `input_kind: "mesh"` 要求 `input` 指向现有的 `.glb` 文件；分工模式目前仅接收图纸图片。`check` 只做配置及输入文件预检，不验证图纸识读质量或网格几何是否可用于建模。

ChatGPT 订阅通过 `auth login` 使用用户自己的账号授权。凭据由本机专用存储保护，不打包进程序；默认存储位置保留 `%LOCALAPPDATA%/EnergyPlus-Agent/openai-subscription`。已有授权不需随版本更新重新登录。GLM 订阅和 Paratera 通过运行配置指定独立凭据文件，不能把密钥写入发布文件。

## 当前能力边界

单模型与图纸分工模式使用共同的源 BIM 和工具。10 cm 规整的目标是空间划分、关系及几何自洽；复杂图纸的稳定质量仍在迭代。完整交互编辑界面尚未交付。真实订阅是否可用须在用户完成账号授权后单独验证；离线示例不会验证账号。

EnergyPlus 是可选下游，需要独立安装和适用的物性配置；本程序检查不等于仿真结果验收。`release-manifest.json` 标识本版提交、runtime/domain 版本与文件哈希。开发在 D 盘仓库进行；本目录由发布脚本生成，修改程序后应重新发布。

查看器使用随程序附带的 Three.js/OrbitControls；来源及许可说明在 `scripts/tool_scripts/vendor` 中。
