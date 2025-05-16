# Lacia

本地优先的 Chat-box，支持 openai 兼容接口。

## 运行

可以配合 [openai-api-forward](https://github.com/yuekcc/openai-api-forward) 使用。需要先安装 [uv](https://github.com/astral-sh/uv)

```sh
uv sync
uv run main.py
```

## Roadmap

- [x] LLM 基本支持
- [x] 多轮对话
- [x] 对话记录到 markdown 格式文件
- [x] 命令 `/q` 退出
- [x] 命令 `/c` 或 `/r` 清空记忆体
- [x] 命令 `/m list` 或 `/m` 列出全部可用模型
- [x] 命令 `/m xxx` 切换模型
- [ ] 命令 `/agent xxx` 切换系统提示
- [ ] MCP 支持
- [x] 支持配置文件
- [x] 支持 `@filepath 问题` 方式引用文件。只能在开头使用 `@filepath`

## LICENSE

[MIT](LICENSE)
