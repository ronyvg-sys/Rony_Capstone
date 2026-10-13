# W8 PII Stress Test Snapshot

## Activity A — PII detection and redaction

Tested the hybrid regex-plus-Presidio pipeline using
`data/stress_test/pii_adversarial.md`.

| Item | Observed result |
|---|---|
| Document parsing | Passed |
| Structural chunking | 8 chunks generated |
| Obfuscated email formats | All 3 supplied examples detected |
| Employee identifiers | 5 supplied identifiers detected |
| IBAN and card suffix | Both detected |
| Conventional phone formats | 4 phone-number redactions reported |
| Spelled-out phone number | Detected by the new `WORD_PHONE` rule; regression test passed |
| Names and addresses | Partial detection and redaction |
| Project budget code | Preserved |
| Low-confidence postcode false positive | Removed after setting Presidio score threshold to 0.5 |

### Findings

The hybrid pipeline detects several supplied PII formats, including obfuscated emails and employee identifiers. The supplied spelled-out phone example is now detected. Remaining gaps include complete name and address protection, broader phone-format coverage, and false-positive control.

Increasing the Presidio confidence threshold to 0.5 removed the observed `US_DRIVER_LICENSE` false positive for postcode `400050`. Other false positives remain.

### Decision

Retain the current pipeline as an experimental baseline. Improve spelled-out phone detection and address handling, add regression tests, and evaluate false positives before considering use with sensitive production documents.

**Status:** Initial stress test completed; further tuning and validation required.

### Latest validation notes

The latest stress-test output confirms that the phone number and the extension
must be assessed separately: the number was replaced with `[PHONE]`, while
extension `4501` remained visible. The address tests also show that some
street, building, and postcode details remain after geographic entities are
redacted. The name `Aisha Mohammed` remained visible in the employee-identifier
section, and the title `Dr.` remained visible before a redacted name.

The regression suite passed 6/6 tests, and all 3 obfuscated-email tests passed.
These results demonstrate the tested cases only; they do not establish complete
PII protection. See `docs/adr/pii_stress_test_findings.md` for the item-level
assessment and proposed fixes.
