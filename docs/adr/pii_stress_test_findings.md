# Week 8 PII Stress Test Findings

## 1. Objective

Evaluate document parsing, structural chunking, and hybrid regex-plus-Presidio PII scrubbing using an adversarial internal memo.

## 2. Test configuration

- Source: `data/stress_test/pii_adversarial.md`
- Parser: `parse_document`
- Chunker: `chunk_structurally`
- Maximum chunk size: 800 characters
- Scrubber: `scrub_chunks(chunks, use_presidio=True)`
- Chunks processed: 8
- Presidio status: Available
- Regex rules: Email, phone, employee ID, IBAN, and card-number patterns

## 3. Findings

| Test item | Observed result | Finding |
|---|---|---|
| Standard and obfuscated email addresses | Three email forms were redacted | Passed for the supplied examples |
| Full-width email characters | Email was redacted, but ordinary text containing full-width characters was also altered | Partial; investigate false positives |
| Phone numbers in conventional formats | Four phone-number redactions were reported | Partial; review the exact matches |
| Spelled-out phone number | Added `WORD_PHONE` regex; the supplied sequence is now redacted and the regression test passes | Improved; further formats need testing |
| Employee identifiers | Five identifiers were redacted | Passed for the supplied examples |
| IBAN | Redacted as `IBAN` | Passed |
| Payment card suffix | Redacted as `CARD_NUMBER` | Passed |
| Person names | Presidio detected `PERSON`, but some names remained visible | Partial; verify entity-level coverage |
| Office addresses | Presidio redacted some geographic components, but complete addresses were not consistently removed | Partial |
| Project budget code | `PRJ-2024-KHANJAR-EU` remained visible | Good; avoids redacting this non-PII project code |
| False positives | Some ordinary geographic text was labelled as `LOCATION` or `PERSON`. Postcode `400050` was initially labelled `US_DRIVER_LICENSE` with score 0.01; after setting `score_threshold=0.5`, that detection disappeared | Improved; other false positives remain |

## 4. Main observations

1. Regex rules reliably handled the tested employee identifiers, IBAN, card suffix, and supplied obfuscated email formats.
2. Presidio added named-entity and location detection beyond the custom regex rules.
3. The supplied spelled-out phone number is now detected by the `WORD_PHONE` regex. A regression test confirms ordinary prose remains unchanged.
4. Address detection was incomplete: redacting individual words does not guarantee that an entire address has been protected.
5. Some ordinary text was over-redacted. This can reduce the usefulness of documents for downstream RAG retrieval.
6. Raising the Presidio confidence threshold to 0.5 removed the observed low-confidence `US_DRIVER_LICENSE` false positive for postcode `400050`; this does not establish that all false positives have been eliminated.
7. A detector label appearing in the report does not prove that every occurrence of that entity type was successfully removed.

## 5. Recommended improvements

- Expand regression tests for additional spelled-out phone formats and check for false positives.
- Add address-specific detection and test complete address removal.
- Review Presidio recognizer configuration and confidence thresholds to reduce false positives.
- Evaluate detection and redaction separately for each expected PII item.
- Add regression tests for both sensitive values and non-sensitive project codes.
- Re-run the complete test suite after each change.

## 6. Conclusion

The hybrid pipeline is operational and provides broader coverage than regex-only scrubbing. The supplied spelled-out phone example is now detected by the `WORD_PHONE` rule. Remaining gaps include complete name and address protection, broader phone-format coverage, and false-positive control. Further tuning and regression testing are required before treating the pipeline as suitable for sensitive production documents.

Note: Findings above reflect the observed console output. Exact per-item recall and false-positive rates have not yet been calculated.
