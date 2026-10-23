# Zetaris policy publication — operations runbook (dry-run package)

**Status: EXECUTED (v2) 22 Oct 2026.** Phases A–E ran as planned; the `file://` capability gate
passed, but live SELECT exposed a supplier CSV defect (embedded-quote truncation) — full story in
[`notes/zetaris-engine-defects-2026-10-22.md`](../notes/zetaris-engine-defects-2026-10-22.md).
The builder approved the quote-safe v2 plan (§8 records the sequence); §2/§3 below describe the
v1 names as originally proposed — the executed objects are the `_v2` pair with identical digests.
Nothing here predates approval: the dry-run package was presented and approved before any
mutation (approval recorded in `docs/decisions.md`, 2026-10-22).

Instance: the dedicated `zetaris-01` deployment (see
[`notes/zetaris-oci-deployed-2026-10-19.md`](../notes/zetaris-oci-deployed-2026-10-19.md));
access is loopback-only via `ssh -F ~/.oci/zetaris-deployment/ssh_config -N zetaris-01`
(UI 3000, REST 8888, JDBC 10000). All commands below are **one Lightning SQL statement
per request**, per the supplier rule.

## 1. Verified current state (read-only pre-flight, 22 Oct 2026)

| Check | Actual result |
|---|---|
| Engine | `SHOW SERVER VERSION` → **2.4.3.1** (build tag matches deployment record) |
| Lightning databases | `NY_TAXI`, `TPCDS_DB` only — **`DRIFTWATCH_REF` absent** (fresh namespace) |
| Grants | `SHOW GRANT ON ALL` → **no rows** |
| Shared volume | `/home/zetaris/customer-data` exists **inside the driver container** only; host backing store is Docker volume `zetaris_customer-data` (`/var/lib/docker/volumes/zetaris_customer-data/_data`) |
| Mount direction | driver mounts the volume **READ-ONLY** → staged-file *reads* by the driver are compatible; nothing may write back through this path |
| Admin REST path | login via UI proxy and `POST /api/v1.0/sql-editor/sqls/run` with the numeric org header work (7/7 read-only checks on 19 Oct; re-confirmed today with `SHOW`s) |

**Supplier-doc references:** `CREATE LIGHTNING DATABASE` §5.2, `CREATE LIGHTNING FILESTORE
TABLE` §5.3, `CREATE FILESTORE SESSION TABLE` §5.1, `DROP` §5.9/§5.10, `CREATE ROLE`
§20.1, `GRANT` §21.4, `ASSIGN … TO USER` §21.7 (pinned `zetaris/getting-started`
`44668b2`). **Unverified capability:** the documented examples use `s3a://` paths; the
`file://` scheme for this FORMAT CSV is a **capability gate**, probed first as a session
table (§3 step B) before any permanent object is created.

## 2. Snapshot pairs (generated, not transcribed)

Produced 22 Oct by `scripts/export_zetaris_policy.py`; reloaded through
`validate_snapshot` after export (5→5, 4→4 rules, digests match). Private copies:
`~/.oci/zetaris-deployment/policy-exports/<snapshot_id>/` (mode 0700).

| Snapshot id | Rules object / Manifest object (db `DRIFTWATCH_REF`) | expected_count | content_sha256 |
|---|---|---:|---|
| `example1_base_v1` | `policy_rules_base_v1` / `policy_manifest_base_v1` | 5 | `58729b59912976e202d4c002c144e4701193f6a54a7300b50869cbbab1bc205f` |
| `example1_no_volume_v1` | `policy_rules_no_volume_v1` / `policy_manifest_no_volume_v1` | 4 | `833ee5fac72ae7144e120cf010d785d39da22e75f32a55c4be03ef91d08cae43` |

Both share `requested_scope_hash = 7e57a6960e9229abb151af91d419cd74a61b7300cc0b9b70845420688be2f9f2`
(example_1 request scope). The variant is exactly the base minus rule **R-1** — it exists
to prove, in Task 6, that removing a published rule removes exactly the finding it
produced. All content is synthetic scenario data; no inventory, OCIDs or declarations
cross to the instance.

## 3. Execution plan (each step gated by §6 approval)

**A. Stage (host-side, operator sudo).** For each snapshot id `S`:
```
sudo mkdir -p /var/lib/docker/volumes/zetaris_customer-data/_data/shared/driftwatch-policy/S
sudo cp  <exported rules.csv manifest.csv>  .../shared/driftwatch-policy/S/
sudo chmod -R a+rX /var/lib/docker/volumes/zetaris_customer-data/_data/shared
```
Then verify in-container the driver (uid 1001) can read the files and that
`sha256sum` of the staged CSVs matches the export listing (immutable after this point —
a changed policy means a NEW snapshot id, never an overwrite).

**B. Capability probe (ephemeral, restart-clean).** One statement:
```sql
CREATE FILESTORE SESSION TABLE dw_stage_probe FORMAT CSV OPTIONS (
  path "file:///home/zetaris/customer-data/shared/driftwatch-policy/example1_base_v1/rules.csv",
  header "true")
```
Then `SELECT COUNT(*) FROM session.dw_stage_probe` → expect 5. On failure: **STOP**; no
permanent objects are created; the reviewed alternative is proposed instead (§7). On
success the session table needs no cleanup (cleared at restart; `DROP TABLE` available).

**C. Permanent registration (admin, base then variant — 5 statements, one per request):**
```sql
CREATE LIGHTNING DATABASE DRIFTWATCH_REF DESCRIBE BY "Driftwatch synthetic reference policies";
CREATE LIGHTNING FILESTORE TABLE policy_rules_base_v1 FROM DRIFTWATCH_REF FORMAT CSV OPTIONS (
  path "file:///home/zetaris/customer-data/shared/driftwatch-policy/example1_base_v1/rules.csv",
  header "true");
CREATE LIGHTNING FILESTORE TABLE policy_manifest_base_v1 FROM DRIFTWATCH_REF FORMAT CSV OPTIONS (
  path "file:///home/zetaris/customer-data/shared/driftwatch-policy/example1_base_v1/manifest.csv",
  header "true");
-- and the identical pair for .../example1_no_volume_v1/ with tables policy_rules_no_volume_v1
--   and policy_manifest_no_volume_v1
```
These exact statements are also emitted per-export into
`proposed_registration.sql` inside each private export directory.

**D. Registration verification (admin reads):** `SHOW LIGHTNING DATABASES`,
`SHOW LIGHTNING TABLES DRIFTWATCH_REF`, `SELECT * FROM DRIFTWATCH_REF.policy_manifest_base_v1`
(1 row; digest/count/scope hash equal to §2), `SELECT COUNT(*) FROM
DRIFTWATCH_REF.policy_rules_base_v1` (5), variant (4).

**E. Least-privilege runtime access.** Runtime needs a non-admin principal with SELECT
only. Per the supplier guide, API keys inherit their account's permissions and **must be
created by the human account holder in the UI (Management → API Tokens) — an agent must
never create or fetch one** — so:
1. *Builder action (UI, in tunnel):* create a user `driftwatch-runtime` (non-admin) and
   set its password; later create its API key and paste it into the repo `.env` yourself.
2. *Operator SQL (approved step):*
```sql
GRANT SELECT ON LIGHTNING DATABASE TABLE DRIFTWATCH_REF.policy_rules_base_v1 TO USER '<runtime-user>';
GRANT SELECT ON LIGHTNING DATABASE TABLE DRIFTWATCH_REF.policy_manifest_base_v1 TO USER '<runtime-user>';
GRANT SELECT ON LIGHTNING DATABASE TABLE DRIFTWATCH_REF.policy_rules_no_volume_v1 TO USER '<runtime-user>';
GRANT SELECT ON LIGHTNING DATABASE TABLE DRIFTWATCH_REF.policy_manifest_no_volume_v1 TO USER '<runtime-user>';
ASSIGN LIGHTNING DATABASE DRIFTWATCH_REF TO USER '<runtime-user>';
```
3. *Verification:* as the runtime user: the five reads above succeed; one
   `CREATE …`/`GRANT …` attempt is rejected (negative probe proves least-privilege).

**F. Pin the runtime settings** (already templated in `.env.example`):
`DRIFTWATCH_POLICY_SOURCE=zetaris`, `ZETARIS_POLICY_SNAPSHOT=example1_base_v1`,
`ZETARIS_POLICY_SHA256=58729b59…205f` (+ variant for the Task-6 run), object names,
loopback URL, org id, and the key from E.1. Task 6 then runs the pipeline for real.

## 4. Acceptance this unlocks (Task 6 consumes it)

- Runtime fetch returns 5 rules with full provenance; a rule removed in the published
  variant (R-1) demonstrably removes exactly its finding through the full loop — the
  plan's "source change affects an appropriate finding/critic decision" gate, on the
  actual Zetaris engine rather than the in-memory transport alone.
- Fixture-vs-Zetaris parity: same rules through both paths yield identical findings.
- Failure modes re-run live: timeout (kill tunnel mid-fetch), wrong snapshot (mismatch →
  schema/query, never partial), degraded → fixture identity preserved.

## 5. Rollback

```sql
DROP LIGHTNING DATABASE TABLE DRIFTWATCH_REF.policy_rules_base_v1;   -- and the other three
DROP LIGHTNING DATABASE DRIFTWATCH_REF;
```
plus: remove the staged directories, revoke/`DROP USER` the runtime user, delete its API
key in the UI, unset `DRIFTWATCH_POLICY_SOURCE`. Nothing else on the instance was touched;
sample mode and file mode never depend on any of this.

## 6. Approval checklist (all four required before any §3 mutation)

- [ ] Snapshot pair naming/digests (§2) confirmed by builder
- [ ] Staging into the existing shared volume (§3A) approved — host writes via operator sudo only
- [ ] `file://` probe accepted as the gate for §3C (§7 fallback understood)
- [ ] Runtime-user plan (§3E) understood — including that the API key is builder-handled end to end

## 7. If the capability gate fails

If the `file://` scheme is unsupported (only object-store paths accepted by FORMAT CSV):
stop; do **not** create an S3 bucket, expose HTTP, or copy data into a cached catalog
(plan's explicit prohibitions). Reviewed alternatives to bring back for approval: (a) a
REST session table over the *existing loopback* API surface serving the CSV — same
least-privilege shape; (b) publication limited to the instance's supported sample-style
ingestion with synthetic-only policy rows re-derived each run. Either way, offline mode
is unaffected and M1 evidence stays honest about what was actually executed.

## 8. Execution record (22 Oct 2026, engine 2.4.3.1)

| Step | Outcome |
|---|---|
| A staging | 4/4 sha256 equal across Mac → host volume → driver-readable (`uid 1001` head verified) |
| B capability probe | session table over `file://` returned 5 — gate cleared |
| C v1 registration | db 806 + 4 tables OK |
| D verification | manifests read back exact digests; **SELECT showed `when_json` truncated at the first embedded quote** — validation rejected every fetch, orchestrator degraded to fixture, zero corrupted data used |
| E user/grants | runtime user created by builder; 4× `GRANT SELECT` + `ASSIGN` OK; negative probes (`CREATE`, `GRANT`) refused: "User is not permitted to run this command" |
| defect found | supplier CSV parser mishandles RFC-4180 escaped quotes → notes/zetaris-engine-defects |
| approval | builder approved v2 quote-safe plan (§1 alternatives excluded) |
| v2 export | percent-encoded cells; `content_sha256` 58729b…205f / 833ee5…ae43 **unchanged** (digests cover parsed records) |
| v2 staging/register | hashes 4/4; 4 tables created; round-trip byte-exact (`{%22resource_class%22%3A...}` intact) |
| v2 grants + retire | 4 grants OK; v1 revoked then dropped — final namespace is exactly the four `_v2` tables |
| **live acceptance** | `scripts/verify_zetaris_policy.py` dual-run: base rules 5 / variant 4, provenance provider=zetaris on both, **only_in_base = [eee5, cost_waste, accepted]**, only_in_variant = [], **sponsor_acceptance: true** |
| drills | dead endpoint (127.0.0.1:18888): degraded→fixture, sponsor=false, findings still computed; tampered pin (sha 0…0): rejected→degraded, sponsor=false |
| regression | full suite 259 passed; sample-mode `run.py` OK; evals 3×(P=1.0 R=1.0 V=1.0, deterministic); held-out scorer OK |

Artifacts: private originals under `~/.oci/zetaris-deployment/acceptance-2026-10-22/`; sanitized
publication in `output_examples/zetaris_acceptance_2026-10-22/` (masked + secret/OCID-scanned).
v1 staged CSVs remain on the volume but nothing references them; rollback per §5 applies to `_v2`.
