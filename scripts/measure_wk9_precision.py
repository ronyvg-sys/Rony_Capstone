"""Compare dense retrieval with Week 9 hybrid retrieval and reranking."""

import json
from pathlib import Path

import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.hybrid_rerank import HybridRetriever, load_index

#ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "data" / "golden_set_full.jsonl"
LABELS_PATH = ROOT / "data" / "w9_relevance_labels.jsonl"
INDEX_PATH = ROOT / "data" / "w9_embeddings_small.json"
OUTPUT_PATH = ROOT / "data" / "w9_precision_results.json"


def read_jsonl(path):
    with path.open("r", encoding="utf-8-sig") as file:
        return [json.loads(line) for line in file if line.strip()]


def precision_at_k(results, relevant_ids, k):
    retrieved_ids = [item["chunk_id"] for item in results[:k]]
    return len(set(retrieved_ids) & relevant_ids) / k


def main():
    load_dotenv(ROOT / ".env")

    questions = read_jsonl(GOLDEN_PATH)
    labels = {item["id"]: set(item["relevant_chunk_ids"])
              for item in read_jsonl(LABELS_PATH)}

    index = load_index(INDEX_PATH)
    retriever = HybridRetriever(index)
    client = OpenAI()

    results = []

    for question in questions:
        question_id = question["id"]
        query = question["question"]

        if question_id not in labels:
            raise ValueError(f"Missing relevance labels for {question_id}")

        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        query_vector = embedding_response.data[0].embedding

        dense_results = retriever.dense_search(query_vector, top_k=5)
        hybrid_results = retriever.search(
            query=query,
            query_vector=query_vector,
            candidate_k=20,
            top_k=5,
        )

        relevant_ids = labels[question_id]

        row = {
            "id": question_id,
            "question": query,
            "dense_precision_at_3": precision_at_k(
                dense_results, relevant_ids, 3
            ),
            "dense_precision_at_5": precision_at_k(
                dense_results, relevant_ids, 5
            ),
            "hybrid_rerank_precision_at_3": precision_at_k(
                hybrid_results, relevant_ids, 3
            ),
            "hybrid_rerank_precision_at_5": precision_at_k(
                hybrid_results, relevant_ids, 5
            ),
            "dense_top5": [item["chunk_id"] for item in dense_results[:5]],
            "hybrid_rerank_top5": [
                item["chunk_id"] for item in hybrid_results[:5]
            ],
        }
        results.append(row)

        print(
            f"{question_id}: "
            f"Dense P@3={row['dense_precision_at_3']:.3f}, "
            f"P@5={row['dense_precision_at_5']:.3f} | "
            f"Hybrid+Rerank P@3="
            f"{row['hybrid_rerank_precision_at_3']:.3f}, "
            f"P@5={row['hybrid_rerank_precision_at_5']:.3f}"
        )

    metric_keys = [
        "dense_precision_at_3",
        "dense_precision_at_5",
        "hybrid_rerank_precision_at_3",
        "hybrid_rerank_precision_at_5",
    ]
    summary = {
        metric: sum(row[metric] for row in results) / len(results)
        for metric in metric_keys
    }

    output = {
        "description": (
            "Initial Week 9 retrieval evaluation using provisional "
            "chunk relevance labels."
        ),
        "question_count": len(results),
        "relevance_labels": str(LABELS_PATH.relative_to(ROOT)),
        "summary": summary,
        "results": results,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nAVERAGE METRICS")
    for metric, value in summary.items():
        print(f"{metric}: {value:.3f}")

    print(f"\nSaved results to: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
