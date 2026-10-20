
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if str(PACKAGE_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from dotenv import load_dotenv
from openai import OpenAI

from rag.hybrid_rerank import HybridRetriever, load_index


def main():
    load_dotenv(REPO_ROOT / ".env")

    client = OpenAI()
    data = load_index(PACKAGE_ROOT / "data" / "w9_embeddings_small.json")

    retriever = HybridRetriever(data)

    question = "What is the top priority risk in Project ABC?"

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=question,
    )
    query_vector = response.data[0].embedding

    dense = retriever.dense_search(query_vector, top_k=5)
    bm25 = retriever.keyword_search(question, top_k=5)

    print("\nDENSE RETRIEVAL")
    for rank, item in enumerate(dense, start=1):
        print(f"{rank}. {item['chunk_id']} | {item['dense_score']:.4f}")

    print("\nBM25 RETRIEVAL")
    for rank, item in enumerate(bm25, start=1):
        print(f"{rank}. {item['chunk_id']} | {item['bm25_score']:.4f}")

    fused = retriever.fuse(dense, bm25)

    print("\nRRF FUSION")
    for rank, item in enumerate(fused[:5], start=1):
        print(f"{rank}. {item['chunk_id']} | {item['rrf_score']:.6f}")

    reranked = retriever.rerank(question, fused[:10], top_k=5)

    print("\nCROSS-ENCODER RERANKING")
    for rank, item in enumerate(reranked, start=1):
        print(f"{rank}. {item['chunk_id']} | {item['rerank_score']:.4f}")


if __name__ == "__main__":
    main()
