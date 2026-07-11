# Support Triage Scorecard (eval_kit example)

**Items scored:** 20/20 (0 failed to classify)

**Severity accuracy:** 16/20 (80%)

**Routing accuracy:** 14/20 (70%)


## Severity Confusion Matrix

| true \ pred | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| P1 | 6 | 1 | 0 | 0 |
| P2 | 0 | 2 | 2 | 0 |
| P3 | 0 | 1 | 6 | 0 |
| P4 | 0 | 0 | 0 | 2 |

**Under-predicted (predicted less urgent than reality):** 3
- T012: true P2 -> predicted P3 -- "Bedroom thermostat shows offline in the app, has been since yesterday. Can't adjust temp r..."
- T021: true P2 -> predicted P3 -- "App keeps logging me out every few hours and I have to keep re-entering my password, kind ..."
- T060: true P1 -> predicted P2 -- "Resident in 407 says their front door lock has not responded to app, keypad, or physical k..."

**Over-predicted (predicted more urgent than reality):** 1
- T030: true P3 -> predicted P2 -- "Resident in 112 reported being locked out last night, our office confirmed they used the b..."

## Severity Confusable-Pattern Audit

Items deliberately written to test whether the classifier applies
nuance rules, not just keyword matching.

- **Resolved lockout via backup code (should not stay P1)**: 2/3 correct
  - [OK] T028: true P2, predicted P2
  - [OK] T029: true P3, predicted P3
  - [MISS] T030: true P3, predicted P2
- **False-alarm leak, confirmed dry (should downgrade to P3)**: 4/4 correct
  - [OK] T031: true P3, predicted P3
  - [OK] T032: true P3, predicted P3
  - [OK] T033: true P3, predicted P3
  - [OK] T034: true P3, predicted P3
- **Multi-unit thermostat = property-wide P1, not per-unit P2**: 2/2 correct
  - [OK] T007: true P1, predicted P1
  - [OK] T008: true P1, predicted P1
- **Unresolved >24h on safety-adjacent device = escalation override to P1**: 2/3 correct
  - [OK] T009: true P1, predicted P1
  - [OK] T010: true P1, predicted P1
  - [MISS] T060: true P1, predicted P2

## Routing Confusion Matrix

| true \ pred | Tier 1 Support | Tier 2 Escalations | Field Service / Hardware Dispatch | Access Control & Security | Environmental Monitoring | Billing & Account Management | Product/Engineering Bug Report |
|---|---|---|---|---|---|---|---|
| Tier 1 Support | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Tier 2 Escalations | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Field Service / Hardware Dispatch | 0 | 0 | 1 | 0 | 3 | 0 | 0 |
| Access Control & Security | 0 | 0 | 1 | 4 | 0 | 0 | 1 |
| Environmental Monitoring | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| Billing & Account Management | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| Product/Engineering Bug Report | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
