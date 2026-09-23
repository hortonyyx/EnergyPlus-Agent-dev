# CLI 兼容性处理

首次请求明确 claude-opus-5-5，被服务端以 400 拒绝：Claude Code 2.1.198 不支持此型号，最低要求 2.1.280。没有有效审阅回答。

执行 claude update，将当前 npm-global 安装更新为 2.1.280；CLI 同时把自身安装方式记录从 native 更正为 global。随后 claude --version 核对为 2.1.280。

round1_retry 与首次提示字节相同，保留首次失败记录，不回退到别的模型或通道。
