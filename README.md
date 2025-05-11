# Chatbox CLI

命令行中的 chatbox。配合 [openai-api-forward](https://github.com/yuekcc/openai-api-forward) 使用。

## 运行

需要先安装 [uv](https://github.com/astral-sh/uv)

```sh
uv sync
uv run main.py
```

## Roadmap

- [x] LLM 基本支持
- [ ] 命令 `/q` `/quit` 退出
- [ ] 命令 `/model xxx` 切换模型
- [ ] 命令 `/agent xxx` 切换通知本
- [ ] MCP 支持

## LICENSE

MIT
