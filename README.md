# Chatbox CLI

命令行中的 chatbox，支持 openai 兼容接口。配合 [openai-api-forward](https://github.com/yuekcc/openai-api-forward) 使用。

## 运行

需要先安装 [uv](https://github.com/astral-sh/uv)

```sh
uv sync
uv run main.py
```

## Roadmap

- [x] LLM 基本支持
- [x] 多轮对话
- [x] 对话记录到 markdown 格式文件
- [x] 命令 `/q` 退出
- [x] 命令 `/m list` 或 `/m` 列出全部可用模型
- [x] 命令 `/m xxx` 切换模型
    - [x] `/m qwen2.5`
    - [x] `/m qwen3`
    - [x] `/m glm_z1`
- [ ] 命令 `/agent xxx` 切换系统提示
- [ ] MCP 支持

## LICENSE

[MIT](LICENSE)
