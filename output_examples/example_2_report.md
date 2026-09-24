# Tenancy audit — run `run-9a938965e4`

- **Status:** success
- **Mode:** sample
- **Sources:** inventory (fixture), iac (fixture), policy (fixture), telemetry (fixture)
- **Caps hit:** none

## Summary

- **resources examined:** 6
- **findings accepted:** 4
- **findings rejected:** 1
- **spend audited usd per month:** 196.18
- **waste found usd per month:** 105.66
- **unattributed ratio:** 0.167
- **narrative:** Audited 6 resources across 4 sources; 4 findings accepted, 1 rejected, 1 left undetermined.

## Findings

### C-002 — sandbox-tmp is running and appears in no Terraform declaration. No owner tag attributes it to a team.

- Resource: `ocid1.instance.oc1..••••ddd4` (compute_instance)
- Class: unattributed
- Verdict: **accepted** (confidence 0.55)
- Impact: 6.57 usd_per_month
- Evidence: E-005, E-006, E-007, E-008
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: accept — no contradicting evidence found in the consulted sources

### C-003 — vol-orphan-50g is a detached 50.0 GB block volume. It is billed continuously and is attached to nothing.

- Resource: `ocid1.volume.oc1..••••eee5` (block_volume)
- Class: cost_waste
- Verdict: **accepted** (confidence 0.55)
- Impact: 1.27 usd_per_month
- Evidence: E-009, E-010
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: accept — no contradicting evidence found in the consulted sources

### C-004 — ip-orphan is a reserved public IP with no assigned entity. It is billed whether or not it is attached.

- Resource: `ocid1.publicip.oc1..••••fff6` (reserved_public_ip)
- Class: cost_waste
- Verdict: **accepted** (confidence 0.55)
- Impact: 7.3 usd_per_month
- Evidence: E-011, E-012
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: accept — no contradicting evidence found in the consulted sources

### C-005 — batch-01 averages 1.002% CPU but peaks at 58.0%. The cost is the idle shape it holds around the clock, not the work it does.

- Resource: `ocid1.instance.oc1..••••bbb2` (compute_instance)
- Class: cost_waste
- Verdict: **revised** (confidence 0.75)
- Impact: 90.52 usd_per_month_upper_bound
- Evidence: E-013, E-014, E-015, E-016
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 2: accept — a low mean with a peak this high is a duty-cycle problem, not an idle resource

### C-001 — batch-01 averages 0.766% CPU with a peak of 0.888% across the requested window, and is declared in Terraform. Nothing in the evidence attributes a purpose to it.

- Resource: `ocid1.instance.oc1..••••bbb2` (compute_instance)
- Class: cost_waste
- Verdict: **rejected** (confidence 0.75)
- Impact: 90.52 usd_per_month
- Evidence: E-001, E-002, E-003, E-004
- Would be withdrawn by: a current, declared, owned purpose for this resource would withdraw this finding
- Round 1: recheck — a schedule signal (month-end) is present, so the requested window may exclude the most recent run
- Superseded by: `C-005`

## Not determined

- `ocid1.instance.oc1..••••ddd4` — coverage 41h of 168h requested
