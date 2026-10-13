from src.ingest.parsers import parse_document
from src.ingest.chunkers import chunk_structurally
from src.ingest.pii import scrub_chunks

doc = parse_document("data/stress_test/pii_adversarial.md")
chunks = chunk_structurally(doc, max_chars=800)
cleaned_chunks, reports = scrub_chunks(chunks, use_presidio=True)
cleaned = "\n".join(chunk.text for chunk in cleaned_chunks)

checks = {
    "Yuki Tanaka": "Yuki Tanaka",
    "Fatima Al-Rashid": "Fatima Al-Rashid",
    "Rajesh Patel": "Rajesh Patel",
    "Aisha Mohammed": "Aisha Mohammed",
    "Carlos Mendoza": "Carlos Mendoza",
    "Tokyo postcode": "150-0002",
    "Dubai office number": "Office 412",
    "Dubai street": "Sheikh Zayed Road",
    "Mumbai flat": "Flat 4B",
    "Mumbai postcode": "400050",
    "London street": "Baker Street",
    "London postcode": "NW1 6XE",
    "Phone extension": "4501",
}

failed = []
for label, sensitive_value in checks.items():
    passed = sensitive_value.casefold() not in cleaned.casefold()
    print(f"{'PASS' if passed else 'FAIL'}: {label}")
    if not passed:
        failed.append(label)

# Negative control: project code must remain unchanged.
project_code_ok = "PRJ-2024-KHANJAR-EU" in cleaned
print(f"{'PASS' if project_code_ok else 'FAIL'}: Project code preserved")
if not project_code_ok:
    failed.append("Project code preserved")

print(f"\nCompleteness checks: {len(checks) + 1 - len(failed)}/{len(checks) + 1} passed")
if failed:
    print("Failures:", ", ".join(failed))
    raise SystemExit(1)
