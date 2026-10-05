from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)

    weight = position - lower

    return values[lower] + (values[upper] - values[lower]) * weight


def load_run(label: str) -> dict:
    path = Path("rag_runs") / f"{label}.json"

    if not path.exists():
        raise FileNotFoundError(f"Evaluation file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--metric",
        required=True,
        choices=[
            "retrieval_hit_rate",
            "cost_per_query",
            "p95_latency",
        ],
    )

    parser.add_argument(
        "--label",
        required=True,
    )

    args = parser.parse_args()

    run = load_run(args.label)
    results = run.get("results", [])

    if args.metric == "retrieval_hit_rate":
        hits = sum(1 for row in results if row.get("hit"))
        total = len(results)

        value = hits / total if total else 0.0

        print(f"Label              : {args.label}")
        print(f"Retrieval hits     : {hits}/{total}")
        print(f"Retrieval hit rate : {value:.2%}")

    elif args.metric == "cost_per_query":
        costs = []

        for row in results:
            tokens_in = row.get("tokens_in", 0)
            tokens_out = row.get("tokens_out", 0)

            # gpt-4o-mini pricing:
            # $0.15 / 1M input tokens
            # $0.60 / 1M output tokens
            cost = (
                (tokens_in / 1_000_000) * 0.15
                + (tokens_out / 1_000_000) * 0.60
            )

            costs.append(cost)

        avg_cost = statistics.mean(costs) if costs else 0.0

        print(f"Label              : {args.label}")
        print(f"Queries            : {len(costs)}")
        print(f"Average cost/query : ${avg_cost:.6f}")

    elif args.metric == "p95_latency":
        latencies = [
            float(row.get("latency_ms", 0))
            for row in results
            if "latency_ms" in row
        ]

        value = percentile(latencies, 0.95)

        print(f"Label              : {args.label}")
        print(f"Queries            : {len(latencies)}")
        print(f"P95 latency        : {value:.2f} ms")


if __name__ == "__main__":
    main()
