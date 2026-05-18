# 开发容器镜像 —— 多端 (Windows / Mac / 云) 统一的开发环境。
#
# 与 docker/Dockerfile (服务器镜像) 的区别:
#   - 服务器镜像把代码 COPY 进去、构建发布制品;
#   - 本镜像不 COPY 代码 —— 代码由 VS Code Dev Containers 挂载进来,改即生效。
#
# 基础镜像自带 Linux 版 EnergyPlus 25.1.0,`energyplus` 已在 PATH 上。
FROM nrel/energyplus:25.1.0

# uv: 从官方镜像直接拷贝二进制(无需 pip 安装)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# git 是 VS Code Dev Containers 的运行依赖;curl/ca-certificates 备用
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# venv 放在挂载工作区之外:
#   1) 避免与宿主机 (Windows/Mac) 自己的 .venv 在同一目录互相覆盖;
#   2) 绕开 bind-mount 在 Windows/Mac 上的慢 IO。
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
ENV PATH="/opt/venv/bin:${PATH}"
