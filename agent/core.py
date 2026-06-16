import json
from .providers import AIProvider
from .tools import get_tool_definitions, execute_tool
from .prompts import ORCHESTRATOR_SYSTEM

MAX_ITERATIONS = 15


async def run_agent(
    provider: AIProvider,
    model: str,
    messages: list,
    system_prompt: str = None,
):
    if system_prompt is None:
        system_prompt = ORCHESTRATOR_SYSTEM

    all_messages = [{"role": "system", "content": system_prompt}] + messages
    tool_defs = get_tool_definitions()

    for step in range(MAX_ITERATIONS):
        msg, usage = await provider.chat_completion(
            model, all_messages, tools=tool_defs
        )

        if msg.get("tool_calls"):
            all_messages.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": msg["tool_calls"],
            })

            for tc in msg["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                tool_name = tc["function"]["name"]
                result = await execute_tool(tool_name, args)
                all_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result),
                })
        else:
            final = msg["content"] or ""
            return final, usage, all_messages

    return "I've reached the maximum steps. Please refine your request or break it into smaller parts.", {}, all_messages
