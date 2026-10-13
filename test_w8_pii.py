from src.ingest.parsers import parse_document
from src.ingest.chunkers import chunk_structurally
from src.ingest.pii import scrub_chunks

doc = parse_document("data/stress_test/pii_adversarial.md")
chunks = chunk_structurally(doc, max_chars=800)

scrubbed, reports = scrub_chunks(chunks, use_presidio=True)

print("Chunks:", len(chunks))
print("Presidio status:", reports[0]["presidio_status"])

for i, (chunk, report) in enumerate(zip(scrubbed, reports)):
    print(f"\n--- Chunk {i} ---")
    print("Detected PII types:", report["detected_types"])
    print("Redactions:", report["n_redactions"])
    print(chunk.text[:400])
    print("...")
