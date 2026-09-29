"""Which reliably-accessible strong models make a PROPER tool call (not leaked text)?

Tests each candidate in one region with a weather tool. The whole point of the
model switch is reliable structured tool calling, so this is the decisive test.

Usage: . /tmp/probe-creds.env; .venv/bin/python scripts/probe_toolcall.py <region>
"""

from __future__ import annotations

import json
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

REGION = sys.argv[1] if len(sys.argv) > 1 else "ap-northeast-1"
rt = boto3.client(
    "bedrock-runtime",
    region_name=REGION,
    config=Config(retries={"max_attempts": 1}, connect_timeout=8, read_timeout=60),
)

CANDIDATES = [
    "deepseek.v3.2",
    "zai.glm-5",
    "qwen.qwen3-235b-a22b-2507-v1:0",
    "moonshotai.kimi-k2.5",
    "mistral.mistral-large-3-675b-instruct",
    "minimax.minimax-m2.5",
]

TOOL = {
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


def probe(model_id: str) -> str:
    try:
        resp = rt.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "What's the weather in Tokyo? Use the tool."}],
                }
            ],
            toolConfig=TOOL,
            inferenceConfig={"maxTokens": 1024, "temperature": 0},
        )
        blocks = resp["output"]["message"]["content"]
        stop = resp.get("stopReason")
        tool_uses = [b for b in blocks if "toolUse" in b]
        if tool_uses:
            tu = tool_uses[0]["toolUse"]
            return f"✅ PROPER tool call: {tu['name']}({json.dumps(tu['input'])}) [stop={stop}]"
        text = " ".join(b.get("text", "") for b in blocks).strip()
        return f"⚠️  NO tool call; text: {text[:90]!r} [stop={stop}]"
    except ClientError as exc:
        return f"❌ {exc.response.get('Error', {}).get('Code', '?')}"
    except Exception as exc:  # noqa: BLE001
        return f"❌ {type(exc).__name__}"


print(f"tool-calling probe in {REGION}:\n")
for m in CANDIDATES:
    print(f"{m:42} {probe(m)}")
