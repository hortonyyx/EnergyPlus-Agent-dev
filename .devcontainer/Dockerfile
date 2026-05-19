# 开发容器镜像 —— 多端 (Windows / Mac / 云) 统一的开发环境。
#
# 与 docker/Dockerfile (服务器镜像) 的区别:
#   - 服务器镜像把代码 COPY 进去、构建发布制品;
#   - 本镜像不 COPY 代码 —— 代码由 VS Code Dev Containers 挂载进来,改即生效。
#
# 基础镜像自带 Linux 版 EnergyPlus 25.1.0,`energyplus` 已在 PATH 上。
FROM nrel/energyplus:25.1.0

# 非交互式 apt —— 否则 python3.12-dev 拉进来的 tzdata 会在构建期弹出
# "Geographic area" 时区选择交互框,容器构建无 TTY 会永久挂死。
# 用 ARG(而非 ENV)使其只在构建期生效、不泄漏到容器运行时环境。
ARG DEBIAN_FRONTEND=noninteractive

# Python 3.12 (Ubuntu 22.04 默认只有 3.10; pyproject.toml 要求 >=3.12)
# git 是 VS Code Dev Containers 的运行依赖;curl/ca-certificates/gnupg 用于添加 PPA
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates gnupg \
    && curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xF23C5A6CF475977595C89F51BA6932366A755776" \
       | gpg --dearmor -o /etc/apt/trusted.gpg.d/deadsnakes.gpg \
    && echo "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu jammy main" \
       > /etc/apt/sources.list.d/deadsnakes.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3.12 python3.12-venv python3.12-dev \
    && rm -rf /var/lib/apt/lists/*

# Node.js —— 三个 AI CLI 都是 npm 包。原先用 devcontainer feature 装,
# 但 feature 来自 ghcr.io,国内网络下经常拉取超时(socket hang up)导致容器
# 创建直接失败。改为构建期用 NodeSource 仓库装,不再依赖 ghcr.io。
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# 三个 AI CLI 在构建期装,不放 postCreateCommand:
#   - 构建期装,npm install 若中途网络波动会让 docker build 直接失败、即时可见;
#     放 postCreateCommand 曾出现包写入了 node_modules 但 /usr/bin bin 软链接
#     没建好的"静默半完成"状态(rebuild 后 claude/codex/gemini 全 command not found)。
#   - 装进镜像层后 Rebuild Container 走缓存,不必每次重新拉。
RUN npm install -g @anthropic-ai/claude-code @openai/codex @google/gemini-cli

# uv: 用安装脚本而非 COPY —— 自动检测运行时架构,避免在 arm64 Mac 上构建时
# 错误拉取 arm64 uv 而基础镜像是 amd64 导致的架构不匹配问题。
RUN curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh

# venv 放在挂载工作区之外:
#   1) 避免与宿主机 (Windows/Mac) 自己的 .venv 在同一目录互相覆盖;
#   2) 绕开 bind-mount 在 Windows/Mac 上的慢 IO。
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
ENV UV_PYTHON=/usr/bin/python3.12
ENV PATH="/opt/venv/bin:${PATH}"
