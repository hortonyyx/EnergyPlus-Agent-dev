---
name: reference-docker-hub-mirror-cn
description: Docker Hub 国内拉取受阻；可用镜像源 docker.1ms.run
metadata: 
  node_type: memory
  type: reference
  originSessionId: a36d0a3d-6f97-4dd3-8043-5b52bfe60b2c
---

国内网络下 `registry-1.docker.io` 拉镜像 TLS 握手反复超时(`auth.docker.io` 反而通)。

可用镜像源:`docker.1ms.run` —— `docker pull docker.1ms.run/<repo>:<tag>` 然后 `docker tag` 打回原名,`FROM` 即可本地命中。
不可用:`docker.m.daocloud.io`(manifest 403)、`dockerproxy.cn`(已死)、`docker.1panel.live`(403)、`docker.xuanyuan.me`(429 限流)。

devcontainer 相关坑同时见仓库 `.devcontainer/Dockerfile` 注释:ghcr.io feature 拉取超时已改 NodeSource;`ARG DEBIAN_FRONTEND=noninteractive` 防 tzdata 交互卡死。
