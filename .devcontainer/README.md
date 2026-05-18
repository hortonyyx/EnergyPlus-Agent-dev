# 多端开发环境指南

本项目用 **VS Code Dev Container** 统一 Windows / Mac / 云端的开发环境:
代码运行、终端、EnergyPlus 全在一个 Linux 容器里,各端字节级一致。

> 心智模型:VS Code 窗口仍在你的宿主机上,但"执行代码"的一切
> (集成终端、`python`、`pytest`、`energyplus`、AI CLI)都在容器里。

---

## 1. 首次启用(每台机器一次)

### 前置
- 安装 **Docker Desktop**(https://www.docker.com/products/docker-desktop/,免费),启动并等引擎就绪。
- VS Code 安装 **Dev Containers** 扩展(`ms-vscode-remote.remote-containers`)。

### 进容器
- `git clone` 本仓库 → VS Code 打开。
- 按 `F1` → `Dev Containers: Reopen in Container`。
- 首次构建会拉镜像(`nrel/energyplus`,约 170MB)+ 装 Node + 跑依赖,**需几分钟**。

### 改了 .devcontainer/ 之后
配置(`features` / `postCreateCommand` / `mounts` / `Dockerfile`)变更后,
必须用 `F1` → **`Dev Containers: Rebuild Container`**(Reopen 不会重跑这些)。

---

## 2. 进容器后自查

在 VS Code 集成终端(已是容器内的 shell)里执行:

```bash
python -c "import sys; print(sys.platform)"   # linux
which energyplus                              # /usr/local/bin/energyplus 之类
uv run pytest -q                              # 依赖 / EnergyPlus / IDD 验证
claude --version && codex --version && gemini --version
```

---

## 3. 每台机器各自要做的(不随 git 同步)

| 项 | 说明 |
|---|---|
| `.env` | 照 `.env.example` 新建并填密钥。被 gitignore,不跨端同步。 |
| Docker Desktop | 每台机器各装一次。 |
| AI CLI 登录态 | 通过 `mounts` 挂载宿主机 `~/.claude` `~/.codex` `~/.gemini` 复用;挂载失败则在容器内重新登录。 |

---

## 4. 环境一致性要点

- **EnergyPlus**:容器内为 `nrel/energyplus:25.1.0`。本地若装 25.2.0,patch 版本略有差异;
  仿真数值若需严格对齐以容器版本为准。
- **venv**:容器的 venv 在 `/opt/venv`(不在挂载工作区),不会与宿主机自己的 `.venv` 冲突。
- **换行符**:`.gitattributes` 统一为 LF;`.bat/.cmd/.ps1` 保留 CRLF。
- **AI coding**:Claude Code / Codex / Gemini CLI 已装入容器,从集成终端启动,
  它们跑的命令才在一致的 Linux 环境里。

---

## 5. MCP 服务

- **项目级**(`.mcp.json`,随 git 走):`EnergyPlus-Agent` —— 容器内开箱即用。
- **用户级**(`~/.claude.json`,随 mount 走):配置会进容器,但服务程序本身
  必须在容器里能跑。指向 Windows 路径 / Windows venv 的服务(如 deepseek-bridge)
  需改造成跨平台命令、最好收进项目级 `.mcp.json`。

---

## 6. 云端 / 远程开发

同一套 `.devcontainer/` 可直接复用:

- **GitHub Codespaces**:仓库页 "Create codespace",自动按本配置造环境,浏览器/手机可用。
- **Claude Code on web**:连 GitHub 仓库,云端 agent 改代码开 PR,适合手机 vibe coding。

产出统一走分支 / PR,回到本地 `git pull`。

---

## 7. 同步纪律

- **git 是唯一同步通道**。不要再用 Seafile 等文件同步工具同步本项目目录
  —— 它与 git 两套机制叠加会损坏 `.git`。
- 切换设备前务必 `git push`(WIP 也推一个分支)。
