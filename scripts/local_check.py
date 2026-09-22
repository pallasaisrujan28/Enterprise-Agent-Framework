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


def check_search() -> bool:
    """The web-search backend, making the same call web_search makes.

    Whichever backend is configured — duckduckgo by default, needing no
    container. A real query, because the failure worth catching is an empty
    result set (a blocked scrape, a rate limit), which only a live call reveals.
    """
    try:
        from agent.tools import search_backend

        hits = search_backend.search("amazon bedrock", max_results=5)
        name = search_backend.backend_name()
        if not hits:
            return result(
                f"search ({name})",
                False,
                "zero results",
                "duckduckgo may be rate-limiting; retry, or set "
                "SEARCH_BACKEND=searxng with the container up",
            )
        return result(f"search ({name})", True, f"{len(hits)} results — {hits[0]['url'][:48]}")
    except ImportError as exc:
        return missing_package("search", exc)
    except Exception as exc:
        return result("search", False, f"{type(exc).__name__}: {str(exc)[:90]}")


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


def check_fetch() -> bool:
    """The fetch backend, making the same call fetch_and_store makes.

    Uses `direct` locally (httpx + trafilatura), so this needs no Firecrawl. A
    real page rather than a stub, because the failure mode worth catching is
    "extracted nothing", which only a real page reveals.
    """
    try:
        from agent.tools import fetch_backend

        md = fetch_backend.scrape("https://en.wikipedia.org/wiki/Amazon_Bedrock")
        return result(
            "fetch (%s)" % fetch_backend.backend_name(),
            len(md) > 200,
            f"extracted {len(md)} chars of markdown",
            "" if len(md) > 200 else "extraction returned almost nothing",
        )
    except ImportError as exc:
        return missing_package("fetch", exc)
    except Exception as exc:
        return result("fetch", False, f"{type(exc).__name__}: {str(exc)[:90]}")


def check_bedrock() -> bool:
    """The one thing that is NOT local, by decision (ADR-011)."""
    try:
        from agent.model import MODEL_ID, get_model

        usage = get_model().invoke("Reply with: ok").usage_metadata or {}
        return result(
            "bedrock (remote)",
            True,
            f"{MODEL_ID} — {usage.get('input_tokens', 0)} in / {usage.get('output_tokens', 0)} out",
        )
    except Exception as exc:
        return result(
            "bedrock (remote)",
            False,
            f"{type(exc).__name__}: {str(exc)[:90]}",
            "export AWS credentials; this is the one service with no local substitute",
        )


def check_turn() -> bool:
    """End to end through the deepagents harness, with the gate actually firing.

    Two questions, because one proves less than it looks: an unregulated question
    shows a turn completes, and a legislation question shows the obligation gate
    still WITHHOLDS. A stack where the gate silently stopped enforcing would pass
    the first check on its own.
    """
    try:
        import warnings

        warnings.filterwarnings("ignore")
        from agent import brain

        agent = brain.build_agent()

        def ask(question: str, thread: str) -> tuple[str, dict]:
            out = agent.invoke(
                {"messages": [{"role": "user", "content": question}]},
                config={"configurable": {"thread_id": thread}},
            )
            return out["messages"][-1].text.strip(), (out.get("obligation_verdict") or {})

        plain, plain_verdict = ask("What is 4 times 4? Just the number.", "check-plain")
        _, gated_verdict = ask(
            "Under UK law, must an employer give a written statement of employment?",
            "check-gated",
        )

        if plain_verdict.get("decision") == "unverified":
            return result(
                "brain + gate",
                False,
                "router degraded — NO obligation was checked",
                "BEDROCK_FAST_MODEL must name a callable model",
            )

        ok = bool(plain) and gated_verdict.get("decision") == "block"
        return result(
            "brain + gate",
            ok,
            f"plain={plain[:14]!r} gate={plain_verdict.get('decision')} | "
            f"gated={gated_verdict.get('decision')} policies={gated_verdict.get('policies')}",
            "" if ok else "a legislation question should trigger a policy and be withheld",
        )
    except ImportError as exc:
        return missing_package("brain + gate", exc)
    except Exception as exc:
        return result("brain + gate", False, f"{type(exc).__name__}: {str(exc)[:90]}")


def main() -> int:
    print("Local stack check — each line makes the same call the application makes.\n")
    print(" containers:")
    container_ok = all([check_qdrant(), check_search(), check_minio(), check_fetch()])
    print("\n not a container, by decision (ADR-011):")
    remote_ok = check_bedrock()
    print("\n end to end:")
    turn_ok = check_turn() if remote_ok else result("brain + gate", False, "skipped — no model")

    print()
    if container_ok and remote_ok and turn_ok:
        print("All green. The local stack is a fair test of the features that exist.")
        print("Page fetching uses the `direct` backend (no JavaScript); switch")
        print("FETCH_BACKEND=firecrawl with a real Firecrawl for client-rendered pages.")
        return 0
    print("Not green. Fix the FAILs above before trusting a local result.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
