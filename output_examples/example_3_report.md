# Tenancy audit — run `run-01d27de8e8`

- **Status:** success
- **Mode:** sample
- **Sources:** inventory (fixture), iac (fixture), policy (fixture), telemetry (fixture)
- **Caps hit:** none

## Summary

- **resources examined:** 5
- **resources in scope:** 5
- **findings accepted:** 3
- **findings rejected:** 1
- **spend audited usd per month:** 106.94
- **waste found usd per month:** 93.07
- **unattributed ratio:** 0.2
- **backends:** ['fixture']
- **sources degraded:** 0
- **narrative:** Audited 5 resources across 4 sources; 3 findings accepted, 1 rejected, 1 left undetermined.
- **integrations:** {'meterless_world_model': {'status': 'used', 'services': ['WorldStoreService', 'IngestPipelineService', 'ContextBuilderService'], 'namespace': 'scenario:example_3:ac8a9ffb3ccf1429ad784cd681e26ae91cf7d60ece5157d0ec3aa9debb72a98d', 'consumers': ['Scout', 'Skeptic'], 'counts': {'entities': 15, 'observations': 15, 'snapshots': 6, 'relationships': 15}, 'store': 'world-run-01d27de8e8/world.sqlite3', 'sources': {'inventory': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['0c0a0520990cfbd53c4332b57b46c489e56ed450bb0cdddae2272b8d0add7f6b']}, 'iac': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['c69dd0efd78ce137b9e2d7c05fa01e5567340f9fd9c9a10dfdc99f9739e9e32f']}, 'policy': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['14dafc6ec3bc09c8afa044a63b990b4d7880504ab64f95f347ad6d247bff8c40']}, 'telemetry': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['2d3fb042350fce458588d58e36af6b17ea798d6467f91806dadac055f877b494', '39b2f27f1d39c878e3d7fbf52ed916e1aaba75f1a0f75e21823855b6e8b5bb0f', '4f4e8c66a63876d195702c097c0389b6a18806055955d0c651bc3b2d3ace920d']}}, 'contexts': 12, 'failures': []}, 'generation': {'configured_provider': 'rules', 'attempts': 0, 'successes': 0, 'fallbacks': 0, 'status': 'not_used', 'models': [], 'schemas': {}}, 'meterless_nightshift': {'configured_provider': 'rules', 'status': 'not_used', 'attempts': 0, 'successes': 0, 'fallbacks': 0, 'models': [], 'schemas': {}}}

## Findings

### C-002 — leftover-01 averages 3.188% CPU with a peak of 3.44% across the requested window, and has no matched Terraform declaration. Nothing in the evidence attributes a purpose to it.

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
