"""Verify a region on this account can serve everything the app needs.

Tests, in one region: the candidate MAIN model with a real TOOL call (the thing
we're fixing), the FAST model, the memory LLM, and Titan embeddings.

Usage: . /tmp/probe-creds.env; .venv/bin/python scripts/probe_stack.py <region>
"""

from __future__ import annotations

import json
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

REGION = sys.argv[1] if len(sys.argv) > 1 else "ap-northeast-1"
CFG = Config(retries={"max_attempts": 1}, connect_timeout=8, read_timeout=40)
rt = boto3.client("bedrock-runtime", region_name=REGION, config=CFG)

# Candidate main-model ids to try, in order. First that answers wins.
MAIN_CANDIDATES = [
    "global.anthropic.claude-sonnet-4-6",
    "apac.anthropic.claude-sonnet-4-6",
    "jp.anthropic.claude-sonnet-4-6",
]
FAST_CANDIDATES = ["amazon.nova-lite-v1:0", "apac.amazon.nova-lite-v1:0"]
MEM_LLM_CANDIDATES = ["amazon.nova-pro-v1:0", "apac.amazon.nova-pro-v1:0"]
EMBED_CANDIDATES = ["amazon.titan-embed-text-v2:0", "amazon.titan-embed-text-v1"]

_WEATHER_TOOL = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    }
                },
            }
        }
    ]
}


def try_tool_call(model_id: str) -> tuple[bool, str]:
    """Return (made_a_proper_tool_call?, detail)."""
    try:
        resp = rt.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "What's the weather in Tokyo? Use the tool."}],
                }
            ],
            toolConfig=_WEATHER_TOOL,
            inferenceConfig={"maxTokens": 512, "temperature": 0},
        )
        blocks = resp["output"]["message"]["content"]
        tool_uses = [b for b in blocks if "toolUse" in b]
        if tool_uses:
            tu = tool_uses[0]["toolUse"]
            return True, f"proper toolUse -> {tu['name']}({json.dumps(tu['input'])})"
        text = " ".join(b.get("text", "") for b in blocks).strip()
        return False, f"NO tool call; emitted text instead: {text[:80]!r}"
    except ClientError as exc:
        return False, exc.response.get("Error", {}).get("Code", "?")


def try_converse(model_id: str) -> tuple[bool, str]:
    try:
        resp = rt.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "Reply with the word OK."}]}],
            inferenceConfig={"maxTokens": 16, "temperature": 0},
        )
        txt = resp["output"]["message"]["content"][0].get("text", "").strip()
        return True, repr(txt[:40])
    except ClientError as exc:
        return False, exc.response.get("Error", {}).get("Code", "?")


def try_embed(model_id: str) -> tuple[bool, str]:
    try:
        resp = rt.invoke_model(modelId=model_id, body=json.dumps({"inputText": "hello world"}))
        vec = json.loads(resp["body"].read())["embedding"]
        return True, f"dim={len(vec)}"
    except ClientError as exc:
        return False, exc.response.get("Error", {}).get("Code", "?")
    except Exception as exc:  # noqa: BLE001
        return False, type(exc).__name__


def first_working(label: str, candidates: list[str], fn) -> None:
    print(f"\n{label}:")
    for cid in candidates:
        ok, detail = fn(cid)
        mark = "✅" if ok else "❌"
        print(f"  {mark} {cid:45} {detail}")
        if ok:
            print(f"  -> USE: {cid}")
            return
    print("  -> NONE worked")


print(f"probing full stack in region: {REGION}")
first_working("MAIN model (tool-calling test)", MAIN_CANDIDATES, try_tool_call)
first_working("FAST model", FAST_CANDIDATES, try_converse)
first_working("MEMORY llm", MEM_LLM_CANDIDATES, try_converse)
first_working("EMBEDDINGS", EMBED_CANDIDATES, try_embed)
