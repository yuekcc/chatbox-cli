# Lacia

一个命令行中的 AI Agent。

## 运行

需要先安装 [uv](https://github.com/astral-sh/uv)。

```sh
uv sync
uv run lacia
```

LLM 接口，只支持 OpenAI 兼容接口。可以配合 [openai-api-forward](https://github.com/yuekcc/openai-api-forward) 使用。

## Roadmap

- [x] LLM 基本支持
- [x] 多轮对话
- [x] 对话记录到 markdown 格式文件
- [x] 命令 `/q` 退出
- [x] 命令 `/c` 或 `/r` 清空记忆体
- [x] 命令 `/m list` 或 `/m` 列出全部可用模型
- [x] 命令 `/m xxx` 切换模型
- [x] 命令 `/a xxx` 切换系统提示
- [ ] MCP 支持
- [x] 支持配置文件
- [x] 支持 `@filepath` 方式引用文件。只能在开头使用 `@`
- [x] 在启动时通过 `-C workdir` 可以指定工作目录（工作目录会影响 @filepath 指令查找文件）

### 内置工具

- [ ] fetch_file
- [ ] fetch_web
- [ ] patch

## LICENSE

[MIT](LICENSE)
