#!/usr/bin/env python3
"""Prove the local stack actually works, service by service.

`docker compose ps` says a container is running. That is not the same as the
service answering the call our code makes — SearXNG runs happily while refusing
JSON, and MinIO runs happily without the bucket. So each check here makes the
SAME request the application makes, through the same client, and reports what
came back.

This is the gate ADR-019 describes. Run it before claiming a feature works
locally, and certainly before deploying anything.

    python scripts/local_check.py
"""

from __future__ import annotations

import os
import sys

# Kept in one place so a failure can print the variable that would fix it.
CHECKS: list[tuple[str, str]] = []


def result(name: str, ok: bool, detail: str, fix: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name:22} {detail}")
    if not ok and fix:
        print(f"         fix: {fix}")
    return ok


def missing_package(name: str, exc: Exception) -> bool:
    """A missing import is an ENVIRONMENT problem, not a service problem.

    Reported separately because the first version of this script printed
    "docker compose up -d qdrant" when the real fault was that httpx was not
    installed — sending the reader to restart a container that was already
    healthy. A diagnostic that points at the wrong layer is worse than none.
    """
    module = str(exc).split("'")[1] if "'" in str(exc) else str(exc)
    return result(
        name,
        False,
        f"the {module} package is not installed",
        "uv sync --extra dev   (the venv does not match pyproject.toml)",
    )


def check_qdrant() -> bool:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    try:
        import httpx

        r = httpx.get(f"{url}/collections", timeout=5)
        r.raise_for_status()
        names = [c["name"] for c in r.json()["result"]["collections"]]
        return result("qdrant", True, f"{url} — {len(names)} collection(s): {names or 'none yet'}")
    except ImportError as exc:
        return missing_package("qdrant", exc)
    except Exception as exc:
        return result(
            "qdrant", False, f"{url} — {type(exc).__name__}: {exc}", "docker compose up -d qdrant"
        )


def check_searxng() -> bool:
    """Asks for JSON specifically, because that is the setting that breaks."""
    url = os.getenv("SEARXNG_URL", "http://localhost:8080/search")
    try:
        import httpx

        r = httpx.get(url, params={"q": "bedrock", "format": "json"}, timeout=20)
        if r.status_code == 403:
            return result(
                "searxng",
                False,
                "403 on format=json",
                "ops/searxng/settings.yml needs json in search.formats, "
                "then: docker compose restart searxng",
            )
        r.raise_for_status()
        hits = r.json().get("results", [])
        if not hits:
            return result(
                "searxng",
                False,
                "JSON works but zero results",
                "engines may be rate-limiting; retry, or check server.limiter is false",
            )
        return result("searxng", True, f"{len(hits)} results — {hits[0]['url'][:52]}")
    except ImportError as exc:
        return missing_package("searxng", exc)
    except Exception as exc:
        return result(
            "searxng", False, f"{url} — {type(exc).__name__}: {exc}", "docker compose up -d searxng"
        )


def check_minio() -> bool:
    """Uses boto3, not a MinIO client — that is the point of the S3 seam."""
    bucket = os.getenv("WORKSPACE_BUCKET", "")
    endpoint = os.getenv("AWS_ENDPOINT_URL_S3", "")
    if not bucket or not endpoint:
        return result(
            "minio (s3)",
            False,
            "WORKSPACE_BUCKET or AWS_ENDPOINT_URL_S3 unset",
            "set both from .env.local.example",
        )
    try:
        # Goes through the application's own client builder rather than making
        # one here, so this check exercises the seam that ships.
        from agent.filesystem.workspace import _s3_client

        s3 = _s3_client()
        s3.put_object(Bucket=bucket, Key="_local_check", Body=b"ok")
        body = s3.get_object(Bucket=bucket, Key="_local_check")["Body"].read()
        s3.delete_object(Bucket=bucket, Key="_local_check")
        assert body == b"ok"
        return result("minio (s3)", True, f"{endpoint} — wrote and read s3://{bucket}")
    except ImportError as exc:
        return missing_package("minio (s3)", exc)
    except Exception as exc:
        return result(
            "minio (s3)",
            False,
            f"{type(exc).__name__}: {str(exc)[:90]}",
            "docker compose up -d minio minio-init, and check the "
            "credential note in .env.local.example",
        )


def check_bedrock() -> bool:
    """The one thing that is NOT local, by decision (ADR-011)."""
    try:
        from agent.config import Config
        from agent.models import Message, build

        config = Config.load()
        reply = build(config).complete((Message("user", "Reply with: ok"),))
        return result(
            "bedrock (remote)",
            True,
            f"{config.model} — {reply.usage.input_tokens} in / {reply.usage.output_tokens} out",
        )
    except Exception as exc:
        return result(
            "bedrock (remote)",
            False,
            f"{type(exc).__name__}: {str(exc)[:90]}",
            "export AWS credentials; this is the one service with no local substitute",
        )


def check_turn() -> bool:
    """End to end: the gate has to actually fire, or the stack proves nothing."""
    try:
        from agent import turn
        from agent.config import Config

        config = Config.load()
        plain = turn.run("What is 4 times 4? Just the number.", turn.Session(), config)
        gated = turn.run(
            "Under UK law, must an employer give a written statement of employment?",
            turn.Session(),
            config,
        )
        if plain.gate_decision == "unverified":
            return result(
                "turn + gate",
                False,
                "router degraded — nothing was enforced",
                "BEDROCK_FAST_MODEL must be a callable model",
            )
        ok = bool(plain.reply) and gated.skills_triggered != ()
        return result(
            "turn + gate",
            ok,
            f"plain={plain.reply[:14]!r} gate={plain.gate_decision} | "
            f"gated skills={list(gated.skills_triggered)} refused={gated.refused}",
            "" if ok else "a skill should trigger on a legislation question",
        )
    except Exception as exc:
        return result("turn + gate", False, f"{type(exc).__name__}: {str(exc)[:90]}")


def main() -> int:
    print("Local stack check — each line makes the same call the application makes.\n")
    print(" containers:")
    container_ok = all([check_qdrant(), check_searxng(), check_minio()])
    print("\n not a container, by decision (ADR-011):")
    remote_ok = check_bedrock()
    print("\n end to end:")
    turn_ok = check_turn() if remote_ok else result("turn + gate", False, "skipped — no model")

    print()
    if container_ok and remote_ok and turn_ok:
        print("All green. The local stack is a fair test of the features that exist.")
        print("Firecrawl is still absent, so fetch_and_store and crawl_site are untested.")
        return 0
    print("Not green. Fix the FAILs above before trusting a local result.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
