# Week 8 PII Stress Test Findings

## 1. Objective

Evaluate document parsing, structural chunking, and hybrid regex-plus-Presidio PII detection and redaction using the adversarial memo in `data/stress_test/pii_adversarial.md`.

The objective is to identify successful redactions, missed or incomplete protection, and false positives. Preserving non-sensitive project information is also required.

## 2. Test configuration

- Source: `data/stress_test/pii_adversarial.md`
- Parser: `parse_document`
- Chunker: `chunk_structurally`
- Maximum chunk size: 800 characters
- Scrubber: `scrub_chunks(chunks, use_presidio=True)`
- Chunks processed: 8
- Presidio: Available
- Detection: Custom regular expressions plus Presidio
- Reported regex categories: email, phone, employee ID, IBAN, and card number
- Regression evidence: 6/6 regression tests passed; 3/3 obfuscated-email tests passed

## 3. Counting methodology and limitations

The source corpus contains 24 sensitive test items: 5 names, 3 email addresses, 5 phone numbers, 5 employee identifiers, 4 office addresses, and 2 financial identifiers.

A case is:
- **Caught:** evidence confirms the sensitive value was detected and redacted.
- **Missed:** evidence confirms the sensitive value remained unredacted.
- **Partial:** some protection occurred, but the value or relevant entity was incompletely redacted, or a false positive affected the result.
- **Not individually verified:** the available summary reports category-level results but does not map each result to the specific source item.

The current console summary does not provide enough item-level output to calculate an exact caught/missed/partial total for all 24 sensitive items. Therefore, this report does not claim an overall recall percentage. Items marked "Not individually verified" must be checked against the actual scrubbed output before being counted as caught or missed.

## 4. Item-by-item failure log

### 4.1 Person names â€” 5 items

| ID | Source item | Observed result | Status |
|---|---|---|---|
| N1 | Dr. Yuki Tanaka | Name replaced with [PERSON], but the title Dr. remained visible | Partial |
| N2 | Fatima Al-Rashid | Name replaced with [PERSON] in the project-team section | Caught for this occurrence |
| N3 | Rajesh Patel | Name replaced with [PERSON] in the project-team section | Caught for this occurrence |
| N4 | Aisha Mohammed | The stress-test output showed this name remained visible | Missed for this occurrence |
| N5 | Carlos Mendoza | Name replaced with [PERSON] in the project-team section | Caught for this occurrence |

Finding: Person-entity detection does not guarantee that the complete name, including titles or hyphenated names, is redacted.

### 4.2 Email addresses â€” 3 items

| ID | Source item | Observed result | Status |
|---|---|---|---|
| E1 | `alice [at] example [dot] com` | Obfuscated-email regression test passed | Caught |
| E2 | `bob.smith ï¼  exampleï¼Žcom` | Full-width email regression test passed; ordinary full-width text also experienced alteration | Caught, with false-positive concern |
| E3 | `y.tanaka(at)hospital(dot)org` | Obfuscated-email regression test passed | Caught |

Finding: All three supplied obfuscated email formats were detected and redacted in the email test. Full-width normalization and unrelated text must also be checked for unintended changes.

### 4.3 Phone numbers â€” 5 items

| ID | Source item | Observed result | Status |
|---|---|---|---|
| P1 | Yuki: `+81 (0) 3 1234 5678` | Replaced with [PHONE] in the scrubbed output | Caught |
| P2 | Fatima: `zero zero nine seven one five zero two three four five six seven` | The new WORD_PHONE rule redacted the supplied spelled-out sequence; regression test passed | Caught |
| P3 | Rajesh: `91-22-2570-1234 ext. 4501` | Number replaced with [PHONE], but extension 4501 remained visible | Partial |
| P4 | Aisha: `+44 7700 900 123` | Replaced with [PHONE] in the scrubbed output | Caught |
| P5 | Carlos: `4 0 4 . 5 5 5 . 0 1 8 2` | Replaced with [PHONE] in the scrubbed output | Caught |

Finding: Four numeric phone redactions were reported, and the spelled-out example was separately confirmed. The available summary does not prove which numeric values were completely removed or whether the extension and digit-spaced formats were protected.

### 4.4 Employee identifiers â€” 5 items

| ID | Source item | Observed result | Status |
|---|---|---|---|
| I1 | `EMP-04827` | Included in the five reported employee-identifier redactions | Caught |
| I2 | `Staff #4082` | Included in the five reported employee-identifier redactions | Caught |
| I3 | `RJP/2019/0451` | Included in the five reported employee-identifier redactions | Caught |
| I4 | `A.M.-2021-EUR-007` | Included in the five reported employee-identifier redactions | Caught |
| I5 | `CM18234` | Included in the five reported employee-identifier redactions | Caught |

Finding: All five supplied employee identifiers were reported as detected and redacted. These patterns may need organization-specific maintenance.

### 4.5 Office addresses â€” 4 items

| ID | Source item | Observed result | Status |
|---|---|---|---|
| A1 | `1-2-3 Shibuya-ku, Tokyo 150-0002, Japan` | Street/building detail and postcode 150-0002 remained visible; some location components were redacted | Partial |
| A2 | `Office 412, Sheikh Zayed Road, Dubai, UAE` | Office 412 and Sheikh remained visible; some location components were redacted | Partial |
| A3 | `Flat 4B, 23rd Cross Road, Bandra West, Mumbai 400050` | Flat 4B, 400050, and other address components remained visible; some locations were redacted | Partial |
| A4 | `221B Baker Street, London NW1 6XE` | Baker Street details and postcode NW1 6XE remained visible; some location components were redacted | Partial |

Finding: Redacting a city or geographic entity does not ensure that a street, building number, office number, or postcode has been removed. Exact per-address output was not captured.

### 4.6 Financial identifiers â€” 3 items

| ID | Source item | Observed result | Status |
|---|---|---|---|
| F1 | `PRJ-2024-KHANJAR-EU` | Remained visible as intended; this is a non-sensitive project code | Correctly preserved |
| F2 | `GB82 WEST 1234 5698 7654 32` | Reported as redacted under IBAN | Caught |
| F3 | `****-****-****-4521` | Reported as redacted under CARD_NUMBER | Caught |

Note: The financial section contains two sensitive identifiers and one intentionally non-sensitive control. The project code must not be counted as a PII miss.

## 5. Summary of observed results

| Category | Evidence-supported result | Remaining concern |
|---|---|---|
| Names | Partial detection/redaction | Complete name coverage not demonstrated |
| Obfuscated emails | 3 supplied examples redacted | Full-width text false positives |
| Phones | Four numeric redactions reported; spelled-out example confirmed | Numeric item mapping, extensions, and digit-spaced coverage |
| Employee IDs | 5 supplied identifiers redacted | Patterns may not generalize to other organizations |
| Addresses | Geographic components sometimes redacted | Complete-address protection not demonstrated |
| Financial identifiers | IBAN and card suffix redacted | Continue regression testing |
| Non-sensitive control | Project budget code preserved | Keep this as a negative test |

Exact totals for caught, missed, and partial cases across all 24 sensitive items cannot be established from the available category-level logs. The table above intentionally avoids presenting an unsupported detection rate. To calculate exact totals, capture the scrubbed text and map each source item to its redacted result.

## 6. Proposed fixes

### Fix 1 â€” Expand phone-format handling

**Problem:** Phone numbers can be numeric, digit-spaced, contain extensions, or be written as words. A single conventional phone regex will not cover every form.

**Proposed fix:** Add dedicated patterns for known digit-spaced formats and test the extension separately. Retain the WORD_PHONE rule for spelled-out sequences.

Illustrative code for a digit-spaced North American number:

```python
import re

DIGIT_SPACED_PHONE = re.compile(
    r"(?<!\d)(?:\d[ .-]?){10}(?!\d)"
)

def find_digit_spaced_phones(text: str):
    return [m.span() for m in DIGIT_SPACED_PHONE.finditer(text)]
```

This example requires careful testing before integration: a broad pattern can match unrelated numeric sequences, and it does not validate international numbering rules. Integrate matches into the existing span-based redaction logic rather than replacing text independently.

**Trade-off:** Better coverage for selected formats, but broader patterns can create false positives. Test ordinary numbers and project codes as negative cases.

### Fix 2 â€” Improve address protection

**Problem:** Presidio may detect a city or location while leaving a street name, building number, unit number, or postcode visible.

**Proposed fix:** Add country-specific address and postcode recognizers for the countries represented in the corpus. Add tests that assert that every sensitive component of each address is removed, not just that LOCATION was detected.

Illustrative test:

```python
def assert_address_redacted(scrubbed_text: str, address_parts: list[str]):
    remaining = [
        part for part in address_parts
        if part and part.casefold() in scrubbed_text.casefold()
    ]
    assert not remaining, f"Address components remain: {remaining}"
```

Example test inputs should include `Shibuya-ku`, `150-0002`, `Sheikh Zayed Road`, `Office 412`, `Baker Street`, and `NW1 6XE`. Adapt the assertions to the actual output and normalization rules.

**Trade-off:** Country-specific recognizers improve targeted coverage but require ongoing maintenance and can redact legitimate non-sensitive references. Address protection should be validated for the full value.

### Fix 3 â€” Improve person-name coverage without indiscriminately lowering thresholds

**Problem:** Some names remain visible even when Presidio detects PERSON entities. Lowering the confidence threshold may increase false positives.

**Proposed fix:** Add a regression test for each name in the corpus, including `Dr. Yuki Tanaka` and `Fatima Al-Rashid`. Inspect detected spans and redacted output separately. Review recognizer configuration and use a controlled, documented fallback review for unresolved names.

Illustrative test:

```python
def assert_sensitive_value_removed(scrubbed_text: str, value: str):
    assert value.casefold() not in scrubbed_text.casefold(), (
        f"Sensitive value remains: {value}"
    )
```

Use this assertion on the complete name and, where appropriate, its constituent sensitive components. Avoid treating a successful PERSON label as proof of complete redaction.

**Trade-off:** Stronger assertions expose misses but may require better handling of titles, hyphens, and partial-name redaction. Manual review adds operational effort.

### Fix 4 â€” Control false positives and preserve negative controls

**Problem:** Ordinary geographic text can be labelled PERSON or LOCATION. A low-confidence `US_DRIVER_LICENSE` detection was initially reported for postcode `400050`.

**Proposed fix:** Retain the tested Presidio threshold of `0.5` as the current experimental setting, and maintain both positive and negative regression tests. Review the actual spans and confidence scores before changing recognizer settings.

Illustrative negative test:

```python
def assert_non_pii_preserved(scrubbed_text: str, value: str):
    assert value in scrubbed_text, (
        f"Non-PII value was unexpectedly changed: {value}"
    )

assert_non_pii_preserved(
    scrubbed_text,
    "PRJ-2024-KHANJAR-EU",
)
```

**Trade-off:** A stricter threshold may reduce false positives but can also miss genuine PII. The threshold must be evaluated against both positive and negative cases.

## 7. Implemented changes and regression evidence

The following improvements have already been reported in the Week 8 implementation:

- Added the `WORD_PHONE` rule for the supplied spelled-out phone sequence.
- Added tests for three obfuscated email formats.
- Added regression tests for employee IDs, IBAN, and preservation of a project code.
- Adjusted Presidio's score threshold to `0.5`, which removed the observed low-confidence `US_DRIVER_LICENSE` result for postcode `400050`.

Previously reported test results:

- Python compilation: passed.
- `test_w8_regression.py`: 6/6 passed.
- `test_w8_emails.py`: 3/3 passed.
- `test_w8_pii.py`: executed; the stress test still showed incomplete name/address protection and false positives.

These results must be rerun before the documentation commit. The regression tests do not prove that every item in the full corpus is protected.

## 8. Conclusion and production readiness

The hybrid regex-plus-Presidio pipeline is a useful experimental baseline. It detects the tested obfuscated emails, employee identifiers, IBAN, card suffix, and spelled-out phone sequence. It also preserves the non-sensitive project code in the reported stress test.

However, complete name and address protection, broader phone-format coverage, and false-positive control remain unresolved. The exact per-item catch rate has not been calculated because the available summary does not map every detection to its source item.

**Decision:** Do not treat the current scrubber as the sole protection against PII disclosure in production. Capture item-level redaction evidence, complete the positive and negative regression tests, and validate the output before processing sensitive project documents downstream.

