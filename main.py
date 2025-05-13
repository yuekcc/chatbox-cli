import asyncio
import json
import tomllib
import os
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

SCRIPT_PATH = Path(__file__)
SCRIPT_DIR = SCRIPT_PATH.parent
CONFIG_PATH = SCRIPT_DIR.joinpath("config.toml")


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
    global CONFIG

    msgs = ["当前可用模型有："]
    for x in CONFIG["models"]:
        msgs.append(f"{x['id']} (id={x['name']})")

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
    global MEMORY
    global CONFIG
    global runtime_config

    async with httpx.AsyncClient(http2=True, timeout=300) as client:
        full_response = ""
        reasoning_contents = []
        answer_contents = []

        thinking_tag = ""

        messages = []

        if len(MEMORY) == 0:
            messages.append({"role": "system", "content": get_system_prompt()})

        messages.append({"role": "user", "content": query})

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

                # print(f">>>{chunk.strip()}<<<", end="\n", flush=True)
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


def dump_messages():
    global runtime_config

    if runtime_config["history_file"] == "":
        runtime_config["history_file"] = SCRIPT_DIR.joinpath(
            f"history/history-{get_current_datetime('%Y%m%d')}.md"
        )

    with open(runtime_config["history_file"], "a", encoding="utf-8") as f:
        buf = []
        # buf.append(
        #     f"----\nmodel: {runtime_config['model']}\ntemperature: {runtime_config['temperature']}\ntop_p: {runtime_config['top_p']}\n----"
        # )

        for msg in MEMORY:
            buf.append(f"## {msg['role']}")
            if "reasoning_content" in msg and msg["reasoning_content"]:
                buf.append(f"{THINK_START}{msg['reasoning_content']}{THINK_END}")
            buf.append(msg["content"])

        f.write("\n\n".join(buf))


def cut_history():
    global runtime_config
    if runtime_config["history_file"]:
        saved_file = SCRIPT_DIR.joinpath(
            f"history/history-{get_current_datetime('%Y%m%d-%H%M%S')}.md"
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
                if not parsed:
                    print(f"[System] 异常。未知指令：{query}")
                print("----\n")
                continue

            await process_query(query)
            dump_messages()

            # LLM 输出的最后没有换行，手工补充换行
            print("\n----")
            print(f"[System] Memory size is {len(MEMORY)}\n")
        except Exception as ex:
            print(f"[System] Error: {str(ex)}")
            exit(1)


if __name__ == "__main__":
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

    print("Lyseya v0.0.1")
    print("请输入问题或 '/q' 退出")
    print(f"正在使用 {runtime_config['model']}\n")

    asyncio.run(chat_loop())
