# Meterless code review and verified fix record

26 October 2026. The independent reviewer inspected `649767c..2802107` read-only. Its
422-test run and offline evaluations passed, but adversarial probes identified six important
code defects. The implementer reproduced all six, then completed one RED→GREEN fix pass.
The fixes were verified by regression tests and whole-suite runs, not an independent re-review.
No reported critical/important code finding remains open; operational acceptance is still blocked.

## Reproduced findings and fixes

| Finding | Root-cause correction | Regression evidence | Commit |
|---|---|---|---|
| Catalog credential echo could enter exported proof | Bound and validate catalog IDs; reject bearer-containing metadata. Export requires the protected runtime environment and scans raw/decoded JSON before creating any copy. | `test_discovery_rejects_secret_echo_or_unsafe_unbounded_ids`; `test_publication_rejects_catalog_credentials_before_any_copy` — RED→GREEN, including encoded JSON echoes. | `118fe2b` |
| Partial IPC could block the deadline supervisor | Read bounded multiprocessing frames incrementally through nonblocking macOS/Linux pipe FDs; keep checking the absolute deadline through headers and bodies. | `test_stalled_ipc_frame_cannot_block_deadline_or_leak_child` — partial header/body cases failed under an outer process-group timeout, then passed with no surviving child. | `26b07f3` |
| Display-name schedule evidence was dropped | Search the complete pinned resource model, retaining name/tag signals without reading the mutable projection. | `test_name_only_schedule_signal_uses_pinned_resource_and_forces_wider_recheck` — mutable name changed after capture; pinned nightly name still forces 744h and the burst-based revision. | `ff37cb9` |
| Model paraphrases manufactured revisions and extra spend | Deduplicate on deterministic resource/class/rules/impact/attribution outcomes; exclude generated prose, evidence IDs and irrelevant measurement-window changes. | `test_model_paraphrases_do_not_create_revisions_or_change_accounting` — actual generator responses alternate wording across rechecks; findings/counts/spend remain equal. | `164af73` |
| Malformed live fields crashed namespace construction | Validate/stage Resource models before namespace access; classify malformed fields and sanitize load-failure diagnostics. | `test_malformed_live_namespace_input_finishes_classified_partial` — null/integer/container IDs and compartments return partial reports with final report events and no raw sentinel. | `67803bf` |
| Lone Unicode surrogates were counted as model success | Require returned prose to encode as strict UTF-8 before recording success. | `test_non_scalar_model_text_is_schema_fallback_not_success`; `test_http_escaped_surrogate_summary_finishes_with_partial_report` — claim/reason/summary and real local HTTP coverage. | `47c4146` |

The review fixtures also exposed an important pre-existing deterministic-prose defect: R-3
claimed a Terraform declaration even when no IaC match existed. The fallback statement now
follows the actual match (`test_idle_fallback_does_not_invent_a_terraform_declaration`,
RED→GREEN, commit `ea9ac2e`). Eligibility, confidence and financial calculations are unchanged.

All these regressions live in `tests/test_meterless_review_regressions.py`. The final complete
suite returned **446 passed**, with the same existing Starlette/AnyIO deprecation warning.
Curated evaluation returned **3 scenarios, 0 failing**; held-out evaluation returned **10 tenancies,
0 failing**. Undefined metrics remain n/a, not perfect scores. Regenerated offline engine proof
and separately verified raw/export checksums are under `output_examples/world_model_review_2026-10-26/`.
The earlier offline milestone proof is retained, not overwritten.

## Review exclusions and executor rulings

Each item the reviewer declined was assessed rather than silently dropped. These rulings
record the review checkpoint; subsequent separately approved operations are recorded in
`meterless-operations.md`:

1. **D1 SSH/host state:** retain the independently measured SSH blocker. RUNNING/current address
   is not host readiness; no Python/headroom/cgroup/port or live Zetaris-baseline claim follows.
2. **D2 installer/runtime:** retain the measured Gatekeeper rejection. No app launch, user terms,
   licensing, model catalog/download or Nightshift inference is established.
3. **Release/tunnel/cgroup:** helper code and its MemoryMax request are tested; actual transfer,
   loopback binding, enforcement and remote cleanup remain unverified. Do not deploy around D1/D2.
4. **D4 combined sponsors:** controlled transports prove contracts only. Genuine model/policy
   acceptance and tunnel outage/recovery must still run; no live tenancy audit is claimed.
5. **D5 delivery/publication:** original dirty assets remain preserved. No final media refresh,
   public-clone verification, push, public sharing or hackathon submission is claimed complete.
6. **Discovery on every audit:** retain the approved readiness/prewarm boundary; ordinary generation
   POSTs do not repeat discovery. Production acceptance does authenticated discovery. Operators
   must establish the real preflight before deployment, not infer readiness from a POST wrapper.
7. **OpenAI-compatible transport:** retain its explicitly documented existing behavior; do not
   attribute Meterless's new IPC/deadline guarantees to that separate transport. Changed accounting
   remains covered by the suite.
8. **Broader engine/vendor claims:** full upstream conformance, multi-audit resume, current vendor
   compatibility and independent licensing/originality certification are not established here.
9. **Private originals:** the reviewer did not inspect excluded operational/private captures. The
   executor re-generated new offline proof and independently rehashed both its raw and exported files.
10. **Static tooling:** ruff/mypy were unavailable and were not installed. No lint/type-check success
    is claimed. Import/syntax execution, tests and the source security scan are separate evidence.

If any of these exclusions is later treated as a completion claim, that would be an error. They
remain operational prerequisites or explicit non-claims, not deferred code defects disguised as polish.
There were no reviewer-listed minor findings to defer.

## Remaining gate

At the review checkpoint SSH timed out and Gatekeeper rejected the official M5+ installer.
Subsequently the user approved exactly one Mac `/32` TCP/22 allowance; API readback and a
fresh strict SSH connection now verify that remedy. See `meterless-operations.md` for current
host checks. The installer gate remains blocked; no OS-security bypass, cloud allocation or
paid action occurred. Local commits are not published or submitted. Keep the execution ledgers
until the incomplete delivery work resumes.
