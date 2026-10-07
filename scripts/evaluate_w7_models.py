"""Evaluate OpenAI Small, OpenAI Large, and Local MiniLM on the W7 golden set."""

import json
import os
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient

from src.rag.embeddings_local import embed_local


GOLDEN_SET = Path("data/golden_set_full.jsonl")

MODELS = {
    "small": {
        "collection": "capstone_chunks_small",
        "model": "text-embedding-3-small",
        "price_per_million_tokens": 0.02,
    },
    "large": {
        "collection": "capstone_chunks_large",
        "model": "text-embedding-3-large",
        "price_per_million_tokens": 0.13,
    },
    "local": {
        "collection": "capstone_chunks_local",
        "model": "all-MiniLM-L6-v2",
        "price_per_million_tokens": 0.0,
    },
}


def load_questions() -> list[dict]:
    return [
        json.loads(line)
        for line in GOLDEN_SET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def keyword_hit(text: str, expected_keywords: list[str]) -> bool:
    text_lower = text.lower()

    return all(
        keyword.lower() in text_lower
        for keyword in expected_keywords
    )


def evaluate_model(
    name: str,
    config: dict,
    questions: list[dict],
    qdrant: QdrantClient,
    openai_client: OpenAI | None,
) -> dict:
    print()
    print("=" * 70)
    print(f"MODEL: {name.upper()}")
    print("=" * 70)

    hits = 0
    latencies_ms = []
    query_tokens = 0
    query_cost = 0.0
    details = []

    for question in questions:
        question_text = question["question"]
        expected_keywords = question["expected_keywords"]

        start = time.perf_counter()

        if name == "local":
            query_vector = embed_local([question_text])[0]
        else:
            response = openai_client.embeddings.create(
                model=config["model"],
                input=question_text,
            )

            query_vector = response.data[0].embedding

            tokens = response.usage.prompt_tokens
            query_tokens += tokens

            query_cost += (
                tokens / 1_000_000
            ) * config["price_per_million_tokens"]

        results = qdrant.query_points(
            collection_name=config["collection"],
            query=query_vector,
            limit=3,
            with_payload=True,
        ).points

        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies_ms.append(elapsed_ms)

        retrieved_text = "\n".join(
            point.payload.get("text", "")
            for point in results
        )

        hit = keyword_hit(
            retrieved_text,
            expected_keywords,
        )

        if hit:
            hits += 1

        retrieved_ids = [
            point.payload.get("chunk_id", "")
            for point in results
        ]

        details.append(
            {
                "id": question["id"],
                "question": question_text,
                "expected_keywords": expected_keywords,
                "hit": hit,
                "latency_ms": elapsed_ms,
                "retrieved_chunks": retrieved_ids,
            }
        )

        print(
            f"{question['id']}: "
            f"{'HIT' if hit else 'MISS'} | "
            f"{elapsed_ms:.1f} ms"
        )

    hit_rate = hits / len(questions) * 100

    p50_latency = statistics.median(latencies_ms)

    print()
    print(f"Hit rate: {hits}/{len(questions)} ({hit_rate:.1f}%)")
    print(f"Latency p50: {p50_latency:.1f} ms")

    if name == "local":
        print("Query embedding cost: $0.00000000")
    else:
        print(f"Query embedding tokens: {query_tokens}")
        print(f"Query embedding cost: ${query_cost:.8f}")

    return {
        "model": name,
        "hit_count": hits,
        "total_questions": len(questions),
        "hit_rate_percent": hit_rate,
        "latency_p50_ms": p50_latency,
        "query_tokens": query_tokens,
        "query_cost_usd": query_cost,
        "details": details,
    }


def main() -> None:
    load_dotenv()

    qdrant = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )

    openai_client = OpenAI()

    questions = load_questions()

    print(f"Golden-set questions: {len(questions)}")

    results = []

    for name, config in MODELS.items():
        result = evaluate_model(
            name,
            config,
            questions,
            qdrant,
            openai_client,
        )
        results.append(result)

    output_file = Path("data/w7_model_evaluation.json")

    output_file.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("FINAL COMPARISON")
    print("=" * 70)

    for result in results:
        print(
            f"{result['model']:>6} | "
            f"Hit rate: {result['hit_count']}/{result['total_questions']} "
            f"({result['hit_rate_percent']:.1f}%) | "
            f"p50: {result['latency_p50_ms']:.1f} ms | "
            f"Cost: ${result['query_cost_usd']:.8f}"
        )

    print()
    print(f"Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()