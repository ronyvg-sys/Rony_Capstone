from src.ingest.pii import scrub_pii_regex

samples = [
    "alice [at] example [dot] com",
    "bob.smith ＠ example．com",
    "y.tanaka(at)hospital(dot)org",
]

for sample in samples:
    cleaned, flags = scrub_pii_regex(sample)
    print("\nOriginal:", repr(sample))
    print("Cleaned: ", repr(cleaned))
    print("Flags:   ", flags)
