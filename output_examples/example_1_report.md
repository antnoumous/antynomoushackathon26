# Tenancy audit — run `run-ade4bbe3ef`

- **Status:** success
- **Mode:** sample
- **Sources:** inventory (fixture), iac (fixture), policy (fixture), telemetry (fixture)
- **Caps hit:** none

## Summary

- **resources examined:** 6
- **resources in scope:** 6
- **findings accepted:** 4
- **findings rejected:** 1
- **spend audited usd per month:** 196.18
- **waste found usd per month:** 105.66
- **unattributed ratio:** 0.167
- **backends:** ['fixture']
- **sources degraded:** 0
- **narrative:** Audited 6 resources across 4 sources; 4 findings accepted, 1 rejected, 1 left undetermined.
- **integrations:** {'meterless_world_model': {'status': 'used', 'services': ['WorldStoreService', 'IngestPipelineService', 'ContextBuilderService'], 'namespace': 'scenario:example_1:65674f222c7ab9948c58a6b6a029608ceb850f7eeb8b3a8232a9a199e5ab47f9', 'consumers': ['Scout', 'Skeptic'], 'counts': {'entities': 18, 'observations': 19, 'snapshots': 8, 'relationships': 19}, 'store': 'world-run-ade4bbe3ef/world.sqlite3', 'sources': {'inventory': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['f6c069a97252a7a521952c5b262688cf24b8ad11e44a1c1e1fd7f9eb3c614a05']}, 'iac': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['e687c0fcca8327d0a4d0b61c188eac49eee20a175390f25c8e2feb65e4443998']}, 'policy': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['042af430914224e1687a11f5a49bcd328b60c5b80da40e88c6f1ab0cb431fcab']}, 'telemetry': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['1d5210b7c9be9acb620f4ba7eb48b0911919d4ae9a38834c1a8f3ad78eafc5f4', '7399fd7128371f957c962e8c835e0c66c7fdae0078dc8737ab3ba3ec8358667f', 'd44fe079dcfa76342d2d5adaa496019c9510f97120ab93abbb6a6f79b1cef479', 'dbd3e8839f695f25d86c8913b15a1715854292280bb33782660a1dde6cda1f0f', 'f8e94164466b84400f64041ee5af8696907455821b0d35d53a5afa7697af4376']}}, 'contexts': 17, 'failures': []}, 'generation': {'configured_provider': 'rules', 'attempts': 0, 'successes': 0, 'fallbacks': 0, 'status': 'not_used', 'models': [], 'schemas': {}}, 'meterless_nightshift': {'configured_provider': 'rules', 'status': 'not_used', 'attempts': 0, 'successes': 0, 'fallbacks': 0, 'models': [], 'schemas': {}}}

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
