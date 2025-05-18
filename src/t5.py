import asyncio
import json
import tomllib
import os
import sys
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.joinpath("config.toml")
HISTORY_DIR = SCRIPT_DIR.joinpath("history")


THINK_START = "<think>\n"
THINK_END = "</think>\n"

# 静态配置
CONFIG = {
    "models": [],
    "agents": [],
    "temperature": 0.6,
    "top_p": 1,
    "api_key": "",
    "openai_endpoint": "",
}

runtime_config = {
    "model": "",
    "temperature": 0.6,
    "top_p": 1,
    "api_key": "",
    "openai_endpoint": "",
    "history_file": "",
    "system_prompt": "",
}

MEMORY = []


def get_current_datetime(format="%Y%m%d%H%M%S"):
    return datetime.now().strftime(format)


def get_base_system_prompt():
    current_date = get_current_datetime("%Y-%m-%d")
    return f"Current model: {runtime_config['model']}\nCurrent date: {current_date}\nUsing language: 简体中文"


def get_system_prompt():
    return f"{get_base_system_prompt()}\n\n{runtime_config['system_prompt']}"


def get_models():
    global CONFIG, runtime_config

    msgs = ["当前可用模型有："]
    for x in CONFIG["models"]:
        current_tag = "<<< CURRENT" if x["id"] == runtime_config["model"] else ""
        msgs.append(f"{x['id']} (id={x['name']}) {current_tag}")

    return "\n".join(msgs)


def remove_reasoning(messages):
    result = []
    for msg in messages:
        result.append(
            {
                "role": msg["role"],
                "content": msg["content"],
            }
        )
    return result


async def process_query(query):
    global MEMORY, CONFIG, runtime_config

    async with httpx.AsyncClient(http2=True, timeout=300) as client:
        full_response = ""
        reasoning_contents = []
        answer_contents = []

        thinking_tag = ""

        messages = []

        if len(MEMORY) == 0:
            messages.append({"role": "system", "content": get_system_prompt()})

        messages.append(query)

        # 添加记忆
        MEMORY = MEMORY + messages

        api_url = f"{runtime_config['openai_endpoint']}/v1/chat/completions"
        api_key = runtime_config["api_key"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "messages": remove_reasoning(MEMORY),
            "model": runtime_config["model"],
            "temperature": runtime_config["temperature"],
            "top_p": runtime_config["top_p"],
            "stream": True,
        }

        async with client.stream(
            "POST",
            api_url,
            headers=headers,
            json=body,
        ) as response:
            async for chunk in response.aiter_text():
                if not chunk:
                    break

                striped: str = chunk.strip()
                full_response += f"{striped}\n"

                if striped.startswith("data:"):
                    pure_chunk = striped.replace("data: ", "")

                for line in pure_chunk.split("\n"):
                    if line == "" or line == "[DONE]":
                        continue

                    try:
                        json_data = json.loads(line)
                        if "choices" in json_data and len(json_data["choices"]) > 0:
                            delta = json_data["choices"][0]["delta"]

                            reasoning_content = delta.get("reasoning_content")
                            answer_content = delta.get("content")

                            if reasoning_content:
                                reasoning_contents.append(reasoning_content)
                                if len(reasoning_contents) > 0 and thinking_tag == "":
                                    print(THINK_START, end="", flush=True)
                                    thinking_tag = THINK_START
                                print(str(reasoning_content), end="", flush=True)

                            if answer_content:
                                answer_contents.append(answer_content)
                                if (
                                    len(answer_contents) > 0
                                    and thinking_tag == THINK_START
                                ):
                                    print(THINK_END, end="", flush=True)
                                    thinking_tag = THINK_END
                                print(str(answer_content), end="", flush=True)
                    except Exception as ex:
                        print(f"\nError: {str(ex)}")

        MEMORY.append(
            {
                "role": "assistant",
                "content": "".join(answer_contents).strip(),
                "reasoning_content": "".join(reasoning_contents),
            }
        )
        return answer_contents, reasoning_contents, full_response


def _ensure_history_dir():
    if HISTORY_DIR.exists():
        return
    HISTORY_DIR.mkdir()


def dump_messages():
    global runtime_config

    if runtime_config["history_file"] == "":
        runtime_config["history_file"] = HISTORY_DIR.joinpath(
            f"history-{get_current_datetime('%Y%m%d')}.md"
        )

    _ensure_history_dir()
    with open(runtime_config["history_file"], "a", encoding="utf-8") as f:
        buf = []

        for msg in MEMORY:
            buf.append(f"## {msg['role']}")
            if "reasoning_content" in msg and msg["reasoning_content"]:
                buf.append(f"{THINK_START}{msg['reasoning_content']}{THINK_END}")

            content = msg["content"]
            if type(content) is str:
                buf.append(msg["content"])
            elif type(content) is list:
                for content_item in content:
                    if "type" in content_item and content_item["type"] == "text":
                        buf.append(content_item["text"])
            else:
                print(
                    "\n[System] unknown message content structure, ignored in dumping message",
                    content,
                )

        f.write("\n\n".join(buf))


def cut_history():
    global runtime_config
    if runtime_config["history_file"]:
        saved_file = HISTORY_DIR.joinpath(
            f"history-{get_current_datetime('%Y%m%d-%H%M%S')}.md"
        )
        os.rename(runtime_config["history_file"], saved_file)
        runtime_config["history_file"] = ""


async def handle_system_command(query):
    global MEMORY

    cmd_line: str = query.lower()

    if cmd_line == "/q":
        exit(0)

    if cmd_line == "/r" or cmd_line == "/c":
        MEMORY = []
        print("[System] 清空记忆体")
        # 记录一份历史文件
        cut_history()
        return True

    if cmd_line.startswith("/m"):
        args = cmd_line.split(" ")[1:]
        if len(args) == 0 or args[0] == "list":
            print(f"[System] {get_models()}")
            return True
        model_name = args[0]
        for x in CONFIG["models"]:
            if x["name"] == model_name:
                runtime_config["model"] = x["id"]
                print(f"[System] using model {x['id']}")
                return True

    return False


def _read_file_content(file_path: str, file_index: int):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        return f"<ATTACHMENT_FILE>\n<FILE_INDEX>File {file_index}</FILE_INDEX>\n<FILE_NAME>{file_path}</FILE_NAME>\n<FILE_CONTENT>\n{content}\n</FILE_CONTENT>\n</ATTACHMENT_FILE>"


def prepare_query(query: str):
    parts = query.split(" ", maxsplit=1)
    if len(parts) == 1:
        return {"role": "user", "content": query}

    fst, main_query = parts
    if not fst.startswith("@"):
        return {"role": "user", "content": query}

    files = fst.replace("@", "", 1).split(",")
    file_content = []
    for file_index, file in enumerate(files):
        file_content.append(_read_file_content(file, file_index))

    return {
        "role": "user",
        "content": [
            {"type": "text", "text": "\n\n".join(file_content)},
            {"type": "text", "text": main_query},
        ],
    }


async def chat_loop():
    while True:
        try:
            prompt_session = PromptSession()
            with patch_stdout():
                query: str = await prompt_session.prompt_async(">>> ")

            query = query.strip()
            if query == "":
                print("[System] 请输入请求")
                print("----\n")
                continue

            if query.startswith("/"):
                parsed = await handle_system_command(query)
                if parsed:
                    print("----\n")
                    continue

            await process_query(prepare_query(query))
            dump_messages()

            # LLM 输出的最后没有换行，手工补充换行
            print("\n----")
            print(f"[System] Memory size is {len(MEMORY)}\n")
        except Exception as ex:
            print(f"\n[System] Error: {str(ex)}")
            exit(1)


def main():
    global CONFIG, runtime_config

    with open(CONFIG_PATH, "rb") as f:
        CONFIG = MappingProxyType(tomllib.load(f))

        # 更新运行时配置
        runtime_config["api_key"] = CONFIG["api_key"]
        runtime_config["openai_endpoint"] = CONFIG["openai_endpoint"]
        runtime_config["temperature"] = CONFIG["temperature"]
        runtime_config["top_p"] = CONFIG["top_p"]
        runtime_config["model"] = CONFIG["models"][0]["id"]
        runtime_config["system_prompt"] = CONFIG["agents"][0]["prompt"]

    # 清屏
    print("\033[2J\033[H", end="")

    print("Lacia v0")
    print("----")
    print(f"工作目录：{os.getcwd()}")
    print(f"模型：{runtime_config['model']}")
    print("请输入问题或 '/q' 退出")
    print()

    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
