from src.ingest.pii import scrub_pii_regex

cases = [
    (
        "Spelled-out phone",
        "Call: zero zero nine seven one five zero two three four five six seven",
        "[WORD_PHONE]",
        True,
    ),
    (
        "Ordinary prose",
        "I have zero concerns about the project.",
        "[WORD_PHONE]",
        False,
    ),
    (
        "Obfuscated email",
        "Contact alice [at] example [dot] com",
        "[OBFUSCATED_EMAIL]",
        True,
    ),
    (
        "Employee ID",
        "Employee ID: EMP-04827",
        "[EMPLOYEE_ID]",
        True,
    ),
    (
        "IBAN",
        "Account: GB82 WEST 1234 5698 7654 32",
        "[IBAN]",
        True,
    ),
    (
        "Project code",
        "Project code: PRJ-2024-KHANJAR-EU",
        "[EMPLOYEE_ID]",
        False,
    ),
]

failed = 0

for name, source, expected, should_detect in cases:
    cleaned, flags = scrub_pii_regex(source)
    detected = any(flag["entity_type"] == expected[1:-1] for flag in flags)
    passed = detected == should_detect

    print(f"{'PASS' if passed else 'FAIL'}: {name}")
    print("  Result:", cleaned)

    if not passed:
        failed += 1

print(f"\nTotal: {len(cases) - failed}/{len(cases)} passed")

if failed:
    raise SystemExit(1)
