from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.pipeline.settings import Settings
from src.rag.naive_rag import ask_rag, load_index


def load_golden_set(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--label",
        required=True,
        help="Evaluation label, e.g. wk6-chunk-medium",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="Path to RAG index JSON file",
    )
    parser.add_argument(
        "--golden",
        default="data/golden_set_full.jsonl",
        help="Golden set JSONL file",
    )
    args = parser.parse_args()

    settings = Settings()

    golden_path = Path(args.golden)
    index_path = Path(args.index)

    golden = load_golden_set(golden_path)
    index = load_index(index_path)

    print(f"Label          : {args.label}")
    print(f"Golden set     : {golden_path}")
    print(f"Questions      : {len(golden)}")
    print(f"Index          : {index_path}")
    print(f"Index chunks   : {len(index.get('chunks', []))}")
    print()

    results = []
    retrieval_hits = 0
    total_latency_ms = 0.0

    for i, item in enumerate(golden, start=1):
        question = item["question"]
        expected_keywords = item.get("expected_keywords", [])

        start = time.perf_counter()

        try:
            result = ask_rag(
                question,
                index,
                settings,
                top_k=3,
            )

            latency_ms = (time.perf_counter() - start) * 1000
            total_latency_ms += latency_ms

            answer = result.get("answer", "")
            sources = result.get("sources", [])

            answer_lower = answer.lower()

            matched_keywords = [
                keyword
                for keyword in expected_keywords
                if keyword.lower() in answer_lower
            ]

            # A question is considered a retrieval/evaluation hit
            # when at least one expected keyword is present.
            hit = len(matched_keywords) > 0

            if hit:
                retrieval_hits += 1

            row = {
                "id": item.get("id"),
                "question": question,
                "expected_keywords": expected_keywords,
                "matched_keywords": matched_keywords,
                "hit": hit,
                "answer": answer,
                "sources": sources,
                "latency_ms": round(latency_ms, 2),
                "tokens_in": result.get("tokens_in", 0),
                "tokens_out": result.get("tokens_out", 0),
            }

            results.append(row)

            print(
                f"[{i:02d}/{len(golden)}] "
                f"{'HIT ' if hit else 'MISS'} "
                f"{latency_ms:8.2f} ms "
                f"{question}"
            )

        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000

            row = {
                "id": item.get("id"),
                "question": question,
                "expected_keywords": expected_keywords,
                "matched_keywords": [],
                "hit": False,
                "answer": "",
                "sources": [],
                "latency_ms": round(latency_ms, 2),
                "tokens_in": 0,
                "tokens_out": 0,
                "error": str(exc),
            }

            results.append(row)

            print(
                f"[{i:02d}/{len(golden)}] ERROR "
                f"{latency_ms:8.2f} ms "
                f"{question}"
            )
            print(f"             {exc}")

    hit_rate = retrieval_hits / len(golden) if golden else 0.0
    avg_latency_ms = total_latency_ms / len(golden) if golden else 0.0

    output_dir = Path("rag_runs")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{args.label}.json"

    evaluation = {
        "label": args.label,
        "index": str(index_path),
        "golden_set": str(golden_path),
        "questions": len(golden),
        "retrieval_hits": retrieval_hits,
        "retrieval_hit_rate": round(hit_rate, 4),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "results": results,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)

    print()
    print("Evaluation complete")
    print(f"Retrieval hits : {retrieval_hits}/{len(golden)}")
    print(f"Hit rate       : {hit_rate:.2%}")
    print(f"Average latency: {avg_latency_ms:.2f} ms")
    print(f"Results file   : {output_path}")


if __name__ == "__main__":
    main()
