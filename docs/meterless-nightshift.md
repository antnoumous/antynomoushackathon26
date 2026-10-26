# Optional Nightshift generation

## What is implemented

Driftwatch has an explicit `meterless` generator in addition to `rules` and
`openai-compatible`. The Meterless adapter uses the existing three named JSON schemas,
validates required strings and finite numeric confidence in [0,1], and rejects a response
that echoes its bearer into published prose. It does not change financial or eligibility rules.

`SAMPLE_MODE=true` chooses RulesGenerator before reading remote provider settings. It still
runs the same World Model/agent loop and needs no runtime, model download, credentials or network.
The World Model is a minimal Python adaptation, not an installed sponsor SDK or full-conformance claim.
See [the engine guide](meterless-world-model.md).

## Configuration and readiness

Select `LLM_PROVIDER=meterless` only after separately installing and prewarming the approved
local runtime. The code reads `METERLESS_BASE_URL` (default `http://127.0.0.1:8088/v1`),
`METERLESS_TOKEN` and `METERLESS_MODEL` (only `meterless/local` is allowed). For the approved
OCI reverse tunnel the endpoint is `http://127.0.0.1:18088/v1`.

Use the real protected runtime token; blank values and `rt-local` are rejected. Do not paste
tokens into command arguments, a settings JSON, logs or chat. Every request carries bearer auth
and `meterless-app: driftwatch`; chat also carries `meterless-scope: user`. Authenticated
`/v1/models` must advertise `meterless/local`. A working `/healthz` alone is not readiness.
Unknown `meterless/*` catalog IDs remain visible but do not enable cloud routing.

Each Meterless request has a maximum 60-second budget, reduced to the remaining audit deadline.
A spawned worker and parent deadline stop slow bodies; redirects and automatic POST retries are
disabled. Response bodies are limited to 1 MiB. No model or package downloads occur during audits.
The existing OpenAI-compatible adapter retains its existing transport; do not attribute the new
spawned-transport guarantees to that separate path.

## Fallback accounting

A failure may return deterministic rules prose, but records actual backend `rules`, its category,
whether a request was attempted, latency and schema. Zero attempts stay `not_used`, even if a
configuration fallback makes the audit partial. Otherwise a fallback makes provider status partial.
A cap outranks partial in the final report, while fallback/degradation details remain visible.

The Writer collects diagnostics after its last call and numeric check, before the final
`synthesise` event. `summary.integrations.generation` describes the selected generator;
`meterless_nightshift` never calls an OpenAI-compatible or rules run a Nightshift success.
World Model metadata is retained separately. Data-source fixture/live labels are independent.

## Combined acceptance

`scripts/verify_meterless_sponsors.py` runs two actual agent loops with fixture
inventory/IaC/telemetry, selected Zetaris policy snapshots and the explicit Meterless generator.
Its CLI requires `--scenario`, `--base-settings`, `--variant-settings`, `--output-dir`.
Snapshot files accept only the existing public object/snapshot/digest selections; bearer/base/org
come from the process environment. Use a new, private, ignored output directory.

Acceptance requires matching policy digests and snapshots, actual Scout/Skeptic context events,
current-run generation observer rows for all three schemas, no fallback, successful reports,
and exactly the R-1 accepted detached-volume finding disappearing with other financial/rule/verdict
semantics unchanged. Different model wording and allocated candidate IDs are not causal changes.
A failed guard produces a nonzero CLI exit. A figure-guard refusal aborts rather than passing.

Artifacts include actual reports, report-linked traces, source outcomes, schema outcomes and world
manifests. `export_proof(raw_directory, publication_directory, runtime_env=protected_env)` checks raw and decoded JSON for both runtime credentials before creating separate masked copies,
rebinds copied report trace paths and records raw/export SHA-256 checksums; it refuses existing targets.
Injected factories are for hermetic contract tests only: they can pass logical checks but always
report `execution=injected_contract_test`, `nightshift_verified=false` and `sponsor_acceptance=false`.
A production-adapter success is hybrid sponsor proof, **not a live OCI tenancy audit**.

## Operational gates still separate

Follow `docs/superpowers/plans/2026-10-26-meterless-split-delivery.md`: existing OCI host SSH/headroom,
verified free signed/notarized Mac installation, user-owned terms/permissions, one fitting local
model, loopback-only encrypted tunnel, protected stdin credentials and actual production acceptance.
Unit tests establish none of those operational states. No NVIDIA/Nemotron, cloud relay, paid setup,
public hosting, publication or hackathon submission is claimed by this code milestone.

Provider contract source: Meterless's `docs/agent-ready/add-meterless-provider.md` in its public
repository. Installation/edition details must be rechecked against the official Mac page at setup.
