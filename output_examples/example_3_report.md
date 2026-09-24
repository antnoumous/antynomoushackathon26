# Tenancy audit — run `run-185826040d`

- **Status:** success
- **Mode:** sample
- **Sources:** inventory (fixture), iac (fixture), policy (fixture), telemetry (fixture)
- **Caps hit:** none

## Summary

- **resources examined:** 5
- **findings accepted:** 3
- **findings rejected:** 1
- **spend audited usd per month:** 106.94
- **waste found usd per month:** 93.07
- **unattributed ratio:** 0.2
- **narrative:** Audited 5 resources across 4 sources; 3 findings accepted, 1 rejected, 1 left undetermined.

## Findings

### C-002 — leftover-01 averages 3.188% CPU with a peak of 3.44% across the requested window, and is declared in Terraform. Nothing in the evidence attributes a purpose to it.

- Resource: `ocid1.instance.oc1..••••cc01` (compute_instance)
- Class: cost_waste
- Verdict: **accepted** (confidence 0.55)
- Impact: 45.26 usd_per_month
- Evidence: E-005, E-006, E-007, E-008
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: accept — no contradicting evidence found in the consulted sources

### C-003 — leftover-01 is running and appears in no Terraform declaration. No owner tag attributes it to a team.

- Resource: `ocid1.instance.oc1..••••cc01` (compute_instance)
- Class: unattributed
- Verdict: **accepted** (confidence 0.55)
- Impact: 45.26 usd_per_month
- Evidence: E-009, E-010, E-011, E-012
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: accept — no contradicting evidence found in the consulted sources

### C-004 — vol-orphan-100g is a detached 100.0 GB block volume. It is billed continuously and is attached to nothing.

- Resource: `ocid1.volume.oc1..••••ee01` (block_volume)
- Class: cost_waste
- Verdict: **accepted** (confidence 0.55)
- Impact: 2.55 usd_per_month
- Evidence: E-013, E-014
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: accept — no contradicting evidence found in the consulted sources

### C-001 — dr-standby-01 averages 0.133% CPU with a peak of 0.15% across the requested window, and is declared in Terraform. Nothing in the evidence attributes a purpose to it.

- Resource: `ocid1.instance.oc1..••••dd01` (compute_instance)
- Class: cost_waste
- Verdict: **rejected** (confidence 0.0)
- Impact: 13.87 usd_per_month
- Evidence: E-001, E-002, E-003, E-004
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: reject — the declaration states a deliberate purpose (by design), which is exactly the falsifier this finding published

## Not determined

- `ocid1.instance.oc1..••••bb01` — coverage 20h of 168h requested
