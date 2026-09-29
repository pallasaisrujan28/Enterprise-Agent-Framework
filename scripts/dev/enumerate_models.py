"""Enumerate and INVOKE every text model in every Bedrock region for this account.

For each region: list TEXT foundation models, map inference profiles, then try a
tiny Converse on each model (direct id, falling back to its inference-profile id
when on-demand isn't supported). Prints which models actually answer.

Usage:  . /tmp/probe-creds.env; .venv/bin/python scripts/enumerate_models.py
"""

from __future__ import annotations

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

# Known reasoning-capable families, flagged in the output for convenience.
_REASONING_HINTS = ("gpt-oss", "kimi", "minimax", "deepseek-r1", "deepseek.r1", "qwq", "magistral")

_CFG = Config(retries={"max_attempts": 0}, connect_timeout=6, read_timeout=30)


def regions() -> list[str]:
    return boto3.Session().get_available_regions("bedrock")


def profile_map(region: str) -> dict[str, str]:
    """base modelId -> inference-profile id, for models that need a profile."""
    out: dict[str, str] = {}
    try:
        bedrock = boto3.client("bedrock", region_name=region, config=_CFG)
        paginator = bedrock.get_paginator("list_inference_profiles")
        for page in paginator.paginate():
            for prof in page.get("inferenceProfileSummaries", []):
                pid = prof.get("inferenceProfileId", "")
                for m in prof.get("models", []):
                    arn = m.get("modelArn", "")
                    base = arn.split("/")[-1] if arn else ""
                    if base and base not in out:
                        out[base] = pid
    except Exception:  # noqa: BLE001
        pass
    return out


def text_models(region: str) -> list[dict]:
    bedrock = boto3.client("bedrock", region_name=region, config=_CFG)
    resp = bedrock.list_foundation_models(byOutputModality="TEXT")
    return resp.get("modelSummaries", [])


def try_converse(region: str, model_id: str) -> tuple[bool, str]:
    rt = boto3.client("bedrock-runtime", region_name=region, config=_CFG)
    try:
        resp = rt.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "Reply with the word OK."}]}],
            inferenceConfig={"maxTokens": 16, "temperature": 0},
        )
        txt = resp["output"]["message"]["content"][0].get("text", "").strip().replace("\n", " ")
        return True, txt[:40]
    except ClientError as exc:
        return False, exc.response.get("Error", {}).get("Code", "?")
    except Exception as exc:  # noqa: BLE001
        return False, type(exc).__name__


def main() -> None:
    answered: dict[str, list[str]] = {}  # model id -> regions that answered
    for region in regions():
        try:
            models = text_models(region)
        except EndpointConnectionError:
            continue
        except ClientError as exc:
            print(f"[{region}] list failed: {exc.response.get('Error', {}).get('Code')}")
            continue
        if not models:
            continue
        profiles = profile_map(region)
        print(f"\n=== {region} ({len(models)} text models) ===")
        for m in sorted(models, key=lambda x: x.get("modelId", "")):
            mid = m.get("modelId", "")
            types = m.get("inferenceTypesSupported", []) or []
            candidates: list[str] = []
            if "ON_DEMAND" in types:
                candidates.append(mid)
            if mid in profiles:
                candidates.append(profiles[mid])
            if not candidates:
                candidates.append(mid)  # try anyway; some are callable without the flag
            ok, detail = False, ""
            used = ""
            for cid in candidates:
                ok, detail = try_converse(region, cid)
                used = cid
                if ok:
                    break
            flag = " ⭐REASONING" if any(h in mid for h in _REASONING_HINTS) else ""
            if ok:
                answered.setdefault(mid, []).append(region)
                print(f"  ✅ {used:55} -> {detail!r}{flag}")
            else:
                print(f"  ❌ {used:55} {detail}{flag}")

    print("\n\n================ ANSWERED MODELS (across regions) ================")
    for mid in sorted(answered):
        flag = " ⭐" if any(h in mid for h in _REASONING_HINTS) else ""
        print(f"  {mid}{flag}  -> {', '.join(answered[mid])}")


if __name__ == "__main__":
    main()
