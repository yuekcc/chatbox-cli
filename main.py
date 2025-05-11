import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

QWEN3 = "Qwen/Qwen3-8B"
QWEN2_5 = "Qwen/Qwen2.5-7B-Instruct"
GLM_Z1 = "THUDM/GLM-Z1-9B-0414"

THINK_START = "<think>\n"
THINK_END = "</think>\n"

API_KEY = "sk-3412"

# TODO 支持配置持久化
config = {
    "model": QWEN2_5,
    "temperature": 0.6,
    "top_p": 1,
}

SCRIPT_PATH = Path(__file__)
SCRIPT_DIR = SCRIPT_PATH.parent


def get_current_datetime(format="%Y%m%d%H%M%S"):
    return datetime.now().strftime(format)


def get_system_prompt():
    current_date = get_current_datetime("%Y-%m-%d")
    return f"You are a helpful assistant. Please reply in 中文. Current date is {current_date}"


async def process_query(query):
    async with httpx.AsyncClient(http2=True, timeout=300) as client:
        full_response = ""
        reasoning_contents = []
        answer_contents = []

        thinking_tag = ""

        # TODO 支持注入历史 message 实现多轮对话
        messages = [
            {"role": "system", "content": get_system_prompt()},
        ]
        messages.append({"role": "user", "content": query})

        async with client.stream(
            "POST",
            "http://localhost:10000/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "messages": messages,
                "model": config["model"],
                "temperature": config["temperature"],
                "top_p": config["top_p"],
                "stream": True,
            },
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

        return answer_contents, reasoning_contents, full_response


def dump_messages(query, answer_contents, reasoning_contents):
    history_file_name = (
        f"{SCRIPT_DIR}/history/history-{get_current_datetime('%Y%m%d')}.md"
    )
    with open(history_file_name, "a", encoding="utf-8") as f:
        buf = []
        buf.append("## User")
        buf.append(query)
        buf.append("## Assistant")

        reasoning = "".join(reasoning_contents)
        if len(reasoning) > 0:
            buf.append(f"{THINK_START}{reasoning}{THINK_END}")
        buf.append("".join(answer_contents))

        f.write("\n\n".join(buf))


async def handle_system_command(query):
    if query.lower() == "/quit" or query.lower() == "/q":
        exit(0)
    elif query.lower() == "/m qwen2.5":
        config["model"] = QWEN2_5
        print(f"[System] using model {QWEN2_5}")
        return True
    elif query.lower() == "/m qwen3":
        config["model"] = QWEN3
        print(f"[System] using model {QWEN3}")
        return True
    elif query.lower() == "/m glm_z1":
        config["model"] = GLM_Z1
        print(f"[System] using model {GLM_Z1}")
        return True

    return False


async def chat_loop():
    # 清屏
    print("\033[2J\033[H", end="")

    print("ChatBox CLI v0")
    print("Type your queries or '/q' to exit.")
    print(f"Using {config['model']}.\n")

    prompt_session = PromptSession()

    while True:
        try:
            with patch_stdout():
                query = await prompt_session.prompt_async("Query: ")

            query = query.strip()
            parsed = await handle_system_command(query)
            if parsed:
                continue

            answer_contents, reasoning_contents, _ = await process_query(query)
            dump_messages(query, answer_contents, reasoning_contents)
            print("")
        except Exception as ex:
            print(f"\nError: {str(ex)}")
            exit(1)


if __name__ == "__main__":
    asyncio.run(chat_loop())
