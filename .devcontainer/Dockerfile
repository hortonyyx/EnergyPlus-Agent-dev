# 开发容器镜像 —— 多端 (Windows / Mac / 云) 统一的开发环境。
#
# 与 docker/Dockerfile (服务器镜像) 的区别:
#   - 服务器镜像把代码 COPY 进去、构建发布制品;
#   - 本镜像不 COPY 代码 —— 代码由 VS Code Dev Containers 挂载进来,改即生效。
#
# 基础镜像自带 Linux 版 EnergyPlus 25.1.0,`energyplus` 已在 PATH 上。
FROM nrel/energyplus:25.1.0

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
