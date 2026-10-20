import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openai import OpenAI
from src.rag.hybrid_rerank import HybridRetriever, load_index

index = load_index("data/w9_embeddings_small.json")
retriever = HybridRetriever(index)
client = OpenAI()

with open("data/golden_set_full.jsonl", encoding="utf-8-sig") as f:
    questions = {
        item["id"]: item
        for item in (json.loads(line) for line in f)
    }

for qid in ["q06", "q09"]:
    question = questions[qid]["question"]

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[question],
    )
    vector = response.data[0].embedding

    dense = retriever.dense_search(vector, top_k=20)
    keyword = retriever.keyword_search(question, top_k=20)
    candidates = retriever.fuse(dense, keyword)[:20]
    reranked = retriever.rerank(question, candidates, top_k=20)

    print(f"\n{'=' * 60}")
    print(f"{qid}: {question}")

    print("\nPRE-RERANK CANDIDATES (RRF):")
    for rank, item in enumerate(candidates, start=1):
        print(
            rank,
            item["chunk_id"],
            "RRF =", round(item["rrf_score"], 5),
        )

    print("\nFINAL RERANKING (cross-encoder):")
    for rank, item in enumerate(reranked, start=1):
        print(
            rank,
            item["chunk_id"],
            "CE =", round(item["rerank_score"], 4),
        )