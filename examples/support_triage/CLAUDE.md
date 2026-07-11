# Ticket Triage Classification Logic

This file is the instruction set `run_example.py` uses to classify each ticket. It
is loaded automatically by the Claude Code CLI because it lives in this directory --
it's the runtime prompt, not documentation. Adapted from the taxonomy in
[claude-triage-simulator](https://github.com/neeshykha/claude-triage-simulator),
trimmed to a 20-ticket demonstration subset for this kit.

## Domain

Support tickets for an IoT/smart-home platform serving multifamily residential
properties. Devices in scope: smart locks, thermostats, leak/water sensors, access
panels, and the resident-facing mobile app.

## Severity Taxonomy

Classify into exactly one of four levels. Work through the checks in order -- the
first one that applies sets the severity, then later checks can only push it up,
never down.

**P1 -- Critical**: active safety/security exposure, active property damage, or an
outage affecting multiple units/the whole property with no workaround.

**P2 -- High**: a single resident or unit fully blocked from a core function, no
active safety/damage exposure, no property-wide scope.

**P3 -- Medium**: degraded but functional -- a workaround exists or the issue is
annoying but not blocking.

**P4 -- Low**: no functional impact -- how-to questions, account/app confusion,
feature requests, cosmetic issues.

**Escalation override:** if a ticket describes a safety-adjacent device (locks,
leak sensors) AND has been unresolved for more than 24 hours, bump the severity one
level regardless of the above. Does not apply to thermostats or app/billing issues.

## Routing Categories

Route to exactly one team: Tier 1 Support, Tier 2 Escalations, Field Service /
Hardware Dispatch, Access Control & Security, Environmental Monitoring, Billing &
Account Management, Product/Engineering Bug Report.

**Routing tie-break:** if a ticket touches both a device and looks like a software
bug, route by whichever the ticket text more directly blames.

## Known Confusable Patterns

- **Resolved lockout via backup code**: P1 only if the person is currently locked
  out right now. Already resolved via keypad backup = P2 at most.
- **False-alarm leak, confirmed dry**: urgent language ("emergency", "water
  everywhere") doesn't override a confirmed-dry, now-normal sensor reading -- P3.
- **Multi-unit thermostat**: several units on the same floor/building reporting the
  same thermostat failure is a shared-controller issue -- P1 property-wide scope,
  even though thermostats are normally P2-max.
- **Unresolved >24h on safety-adjacent device**: bump one severity level via the
  escalation override, regardless of how calm the ticket's tone is.

## Output Format

For each ticket, return strict JSON with no other text:

```json
{"severity": "P1", "routing": "Access Control & Security", "reasoning": "one sentence"}
```
