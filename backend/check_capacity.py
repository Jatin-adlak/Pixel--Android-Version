"""Measure authenticated read traffic against a PIXEL staging deployment."""

import argparse
import asyncio
import json
import math
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import httpx

READ_PATHS = ("/me/", "/feed/?kind=post", "/events/", "/feed/?kind=moment", "/spotlights/")


async def measure(origin, tokens, rounds):
    timings = []
    outcomes = Counter()
    async with httpx.AsyncClient(
        base_url=f"{origin}/api/v1", limits=httpx.Limits(max_connections=len(tokens)), timeout=15
    ) as client:

        async def browse(token, offset):
            for index in range(rounds * len(READ_PATHS)):
                path = READ_PATHS[(offset + index) % len(READ_PATHS)]
                started = time.perf_counter()
                try:
                    response = await client.get(path, headers={"Authorization": f"Bearer {token}"})
                    outcomes[response.status_code] += 1
                    if response.status_code == 200:
                        timings.append((time.perf_counter() - started) * 1000)
                except httpx.RequestError:
                    outcomes["network_error"] += 1
                await asyncio.sleep(1)

        await asyncio.gather(*(browse(token, offset) for offset, token in enumerate(tokens)))
    timings.sort()
    p95 = timings[math.ceil(len(timings) * 0.95) - 1] if timings else None
    return outcomes, p95


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin", help="HTTPS staging API origin")
    parser.add_argument(
        "tokens", type=Path, help="Local JSON array of 100 fresh staging access tokens"
    )
    parser.add_argument("--rounds", type=int, default=6, choices=range(1, 13))
    args = parser.parse_args()
    origin = urlsplit(args.origin)
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.path not in {"", "/"}
        or origin.query
        or origin.fragment
    ):
        parser.error("Use a staging HTTPS origin without a path or credentials.")
    tokens = json.loads(args.tokens.read_text(encoding="utf-8"))
    if (
        not isinstance(tokens, list)
        or len(tokens) != 100
        or not all(
            isinstance(token, str)
            and token
            and token.isascii()
            and not any(c.isspace() for c in token)
            for token in tokens
        )
        or len(set(tokens)) != 100
    ):
        parser.error("Supply exactly 100 distinct access tokens from dedicated staging accounts.")
    outcomes, p95 = asyncio.run(measure(args.origin.rstrip("/"), tokens, args.rounds))
    print(
        f"100 concurrent virtual users. Outcomes: {dict(outcomes)}. Successful request p95: {p95 or 0:.0f} ms."
    )
    return int(p95 is None or p95 > 1000 or sum(outcomes.values()) != outcomes[200])


if __name__ == "__main__":
    raise SystemExit(main())
