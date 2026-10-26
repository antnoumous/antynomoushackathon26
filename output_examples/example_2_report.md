# Tenancy audit — run `run-d486f7b60b`

- **Status:** success
- **Mode:** sample
- **Sources:** inventory (fixture), iac (fixture), policy (fixture), telemetry (fixture)
- **Caps hit:** none

## Summary

- **resources examined:** 5
- **resources in scope:** 5
- **findings accepted:** 0
- **findings rejected:** 0
- **spend audited usd per month:** 0
- **waste found usd per month:** 0
- **unattributed ratio:** 0.0
- **backends:** ['fixture']
- **sources degraded:** 0
- **narrative:** Audited 5 resources across 4 sources; 0 findings accepted, 0 rejected, 0 left undetermined.
- **integrations:** {'meterless_world_model': {'status': 'used', 'services': ['WorldStoreService', 'IngestPipelineService', 'ContextBuilderService'], 'namespace': 'scenario:example_2:3feef20d75ce6a95f23ad9bb44382bf6c287fbab96ddb9da7f5bee8435751e32', 'consumers': ['Scout'], 'counts': {'entities': 18, 'observations': 18, 'snapshots': 6, 'relationships': 18}, 'store': 'world-run-d486f7b60b/world.sqlite3', 'sources': {'inventory': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['ed6402932fef59d0c0a1cc2dbaadb6f109915734abbc3d1684b8a1405a6dceae']}, 'iac': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['7e6ab33533ecef2fc18b92db39e7f1b8d0a34479afb6c715db9db2d338db1253']}, 'policy': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['79773534d87ae5b4825e38ff41db9c4fd3151bd7012ad470eada1a4d88e0956c']}, 'telemetry': {'backends': ['fixture'], 'complete': True, 'degraded': False, 'snapshots': ['663a8fa5209fb2a0ee6459ad61e8259e868a695245d1af304168ab025dafd4cd', 'd2c2b5f57a04cf2a81cbc11b6e9ce358ef80134e782bebd7fcef3030780620a6', 'e8960397f9f20a6d07cf4d33705ccd1498ef0a192b15ed57f5f0fdc1f85be4e6']}}, 'contexts': 8, 'failures': []}, 'generation': {'configured_provider': 'rules', 'attempts': 0, 'successes': 0, 'fallbacks': 0, 'status': 'not_used', 'models': [], 'schemas': {}}, 'meterless_nightshift': {'configured_provider': 'rules', 'status': 'not_used', 'attempts': 0, 'successes': 0, 'fallbacks': 0, 'models': [], 'schemas': {}}}

## Findings
