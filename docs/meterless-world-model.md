# Driftwatch's Meterless World Model subset

## Scope and attribution

This is Driftwatch's Python adaptation of a small, headless subset of the
[Meterless World Model design](https://github.com/Meterless/Meterless/tree/main/engines/world-model),
whose upstream README identifies it as an implementation specification rather than an SDK.
Driftwatch does not claim complete upstream conformance or an installed Meterless Python package.
The upstream design is Apache-2.0; the Driftwatch implementation is original project code.

The load-bearing path is `WorldStoreService` → `IngestPipelineService` →
`ContextBuilderService`. Scout reads selected resource/declaration/policy/telemetry facts through
this path. Skeptic replays each candidate's pinned selection for purpose and schedule checks.
Planner's resource map remains an assignment/counting projection, not Scout's evidence source.
Existing `E-*` references and deterministic cost/rule arithmetic remain in place.

## Persistence, provenance and bounds

Each audit owns a private SQLite database beneath its log directory. Canonical observations and
source-snapshot membership survive reopening; retrying ingestion is duplicate-safe. Content IDs
exclude run IDs and fetch timestamps, but include namespace, backend, source revision and measurement
window. The first supplied fetch timestamp and original measurement time are retained separately;
unknown timestamps remain null. A fixture alias is accepted only when the inventory join is unique,
and its original ID and fixture/degraded backend are retained.

Selections are run/namespace scoped, use pinned snapshots and exact returned telemetry windows and
resolution, and do not query a global latest state. An incomplete IaC source cannot prove absence.
An empty current policy does not resurrect prior rules. Mutation of returned models cannot rewrite
stored observations or later replay.

Limits are 10,000 observations per run, 2 MiB per payload, 128 MiB of database pages, 256 selected
records per resource and 250 ms SQLite busy wait. Storage/context failures are named and produce
abstention/partial status, unless an independently hit cap takes precedence. Integration metadata is
attached after the Writer's numeric guard; World Model references do not widen its quantity allow-list.

## Reproduce the offline proof

From the repository root, using the declared Python 3.11+ environment:

```bash
.venv/bin/python scripts/verify_world_model.py --output-dir logs/world-proof-new \
  --export-dir output_examples/world-proof-new
.venv/bin/python -m pytest -q
PY=.venv/bin/python bash scripts/run_examples.sh
```

Proof directories must not already exist. The generator runs the actual sample pipeline, reopens
its actual store to check deduplication and selected 168h/744h windows, then runs a copied fixture
with only R-1 removed. Acceptance requires that only the detached-volume finding disappears, with
changed policy observations and actual Scout/Skeptic trace consumption. Failed guards make the CLI
exit nonzero. Published JSON/JSONL copies are masked separately and carry raw/exported checksums;
original databases and captures remain private.

`output_examples/world_model/` contains the generated review proof for this milestone. This is
**offline engine evidence only**: it proves neither Nightshift inference, combined live sponsor
acceptance, a live OCI tenancy audit, public deployment nor a submitted hackathon entry. H-MEM,
Markovian, operator UI, enrichment workers and full upstream conformance are outside this subset.
