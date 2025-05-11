import asyncio
import json
import os
import sys

import httpx

QWEN3 = "Qwen/Qwen3-8B"
QWEN2_5 = "Qwen/Qwen2.5-7B-Instruct"
GLM_Z1 = "THUDM/GLM-Z1-9B-0414"

THINK_START = "<think>\n"
THINK_END = "</think>\n"

api_key = "sk-3412"


async def process_query(query):
    async with httpx.AsyncClient() as client:
        full_response = ""
        reasoning_contents = []
        answer_contents = []

        thinking_tag = ""

        async with client.stream(
            "POST",
            "http://localhost:10000/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GLM_Z1,
                "messages": [
                    {"role": "system", "content": "answer in 中文"},
                    {"role": "user", "content": query},
                ],
                "stream": True,
            },
            timeout=30,
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

        return full_response, reasoning_contents, answer_contents


async def chat_loop():
    print("\nSimple chatbox!")
    print("Type your queries or 'quit' to exit.")

    while True:
        try:
            query = input("\nQuery: ").strip()

            if query.lower() == "/quit" or query.lower() == "/q":
                break

            _, reasoning_contents, answer_contents = await process_query(query)
            with open("response.md", "a", encoding="utf-8") as f:
                reasoning = "".join(reasoning_contents)
                if len(reasoning) > 0:
                    f.write(
                        f"## User\n\n{query}\n\n## Assistant\n\n{THINK_START}{reasoning}{THINK_END}\n{''.join(answer_contents)}\n\n"
                    )
                else:
                    f.write(
                        f"## User\n\n{query}\n\n## Assistant\n\n{''.join(answer_contents)}\n\n"
                    )

        except Exception as ex:
            print(f"\nError: {str(ex)}")
            raise ex


if __name__ == "__main__":
    asyncio.run(chat_loop())
