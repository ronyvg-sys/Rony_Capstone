# Project ABC — Risk Register

| Risk ID | Risk | Probability | Impact | Rating | Mitigation | Owner |
|---|---|---|---|---|---|---|
| R-001 | Data migration and billing reconciliation may not complete before UAT | High | High | CRITICAL | Daily reconciliation tracking, additional validation cycles, dedicated SME support | Data Migration Lead |
| R-002 | External payment gateway dependency may delay integration testing | Medium | High | HIGH | Confirm interface readiness and establish fallback test data | Integration Lead |
| R-003 | UAT business resources may not be available for the complete test window | Medium | Medium | MEDIUM | Obtain business resource commitment and publish test calendar | Business Lead |
| R-004 | Production environment capacity may be insufficient for peak billing volume | Low | High | MEDIUM | Complete performance testing and capacity assessment | Technical Lead |
| R-005 | Late change requests may affect release readiness | Medium | Medium | MEDIUM | Enforce change-control process and assess impact before approval | Project Manager |

## Top Priority Risk

**R-001 — Data migration and billing reconciliation delay is the top priority risk.**

It is rated CRITICAL because both probability and impact are HIGH.

The risk directly threatens UAT readiness and the December production release.

## Immediate Actions
- Complete outstanding reconciliation scenarios.
- Review migration defects daily.
- Assign dedicated data SMEs.
- Track reconciliation completion percentage.
- Escalate unresolved critical defects through project governance.
