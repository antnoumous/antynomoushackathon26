# Zetaris supplied documentation — readiness and Driftwatch next steps

> **Subsequent organiser-guide update:** [participant setup guide assessment](participant-setup-guide-2026-10-17.md)
> changes the access recommendation below. The guide dated 16 October directs local
> installation and explicitly expects Nemotron; do not assume a shared participant URL
> will be issued or that shared access meets eligibility. The user has since approved the
> bounded read-only onboarding check: pinned checkout and actual preflight completed,
> blocked on missing prerequisites. Installation and product changes remain unapproved.

**Assessed: 17 October 2026 (SGT). Documentation/code inspection only.** No sponsor integration, installation, signup, provisioning, authenticated query, track change or lab-retention change is authorised or claimed.

## 1. Conclusion

**Enough information to choose a bounded architecture and define a read-only access check; not enough to claim operational readiness. Videos are optional unless a specific access/setup problem remains.** The next missing evidence is an actual participant endpoint/account, permissions and a successful query—not another public dataset.

Prefer an organiser-supplied shared instance. Treat local Docker as a separately approved fallback and managed AWS as a paid deployment in our own account, not equivalent to free participant access. Keep the existing OCI SDK inventory/telemetry paths and four-agent critic loop. Propose Zetaris-backed policy rules first, followed by IaC declarations; retain fixture-only sample mode. These remain recommendations pending approval.

Read alongside [the 14 October assessment](zetaris.md), [Meterless analysis](meterless.md), and [the host-documents digest](host-docs-digest.md). This supplement qualifies the earlier REST-first recommendation; it does not replace historical decisions silently.

## 2. Source authority, inventory and version

Two attachments have distinct hashes; neither is a binding rulebook. Raw attachments remain outside the repository.

| Ref | Attachment | Authority | Bytes | SHA-256 |
|---|---|---|---:|---|
| A1 | `zetaris-getting-started-prompt.md` | Supplied client workflow; its embedded instructions are material to assess, not permission to execute | 1369 | `a4e86e940266c530afe9616ec3d8031bc1fed4ab5d60c6031ded6a6f7dfc5a1e` |
| A2 | `zetaris-sponsor-overview.md` | Sponsor overview with explicit access/documentation **TBC**; no authority to weaken event rules | 882 | `b972fca16f5b4ab5ed086dcc6f17890cbb33bdfef7d01e99ca302f5bc3e50844` |

All **19 supplied URLs** were retrieved successfully. GitHub catalog pages were retrieved through official raw Markdown at the pinned commit. Landing-page retrieval does not mean every linked knowledge-base article was reviewed. Rendered and Markdown versions are alternate presentations, not separate independent corroboration.

| Ref | Supplied URL | Authority / assessment use |
|---|---|---|
| U01 | https://kbase.zetaris.com/knowledge | Official supplier index: SQL, connections, deployment and security references; not a service entitlement |
| U02 | https://zetaris.github.io/getting-started/docs/guides/troubleshooting.html | Official operational guidance: permissions, network errors, team isolation |
| U03 | https://zetaris.github.io/getting-started/docs/guides/zetaris-lightning-sql-companion.html | Official repo findings, explicitly scoped by version/fixture; not guarantees for our instance |
| U04 | https://zetaris.github.io/getting-started/docs/guides/zetaris-lightning-sql-commands.html | Official syntax/privilege reference; read-only starter versus DDL/admin operations |
| U05 | https://github.com/zetaris/getting-started/blob/main/open_data/usl/usl-sources.md | Supplier SIC/company models and their tested/unverified limits |
| U06 | https://github.com/zetaris/getting-started/blob/main/open_data/parquet_csv/parquet-csv-data-sources.md | Supplier file catalog: licensing and known failures, not required project data |
| U07 | https://github.com/zetaris/getting-started/blob/main/open_data/rest_apis/rest-api-sources.md | Supplier REST catalog: example response shapes and source restrictions |
| U08 | https://zetaris.github.io/getting-started/open_data/usl/HOWTO.html | Supplier optional model lifecycle and prerequisites |
| U09 | https://zetaris.github.io/getting-started/docs/guides/first-dataset.html | Supplier PokéAPI walkthrough; **creates objects**, unlike the read-only starter |
| U10 | https://zetaris.github.io/getting-started/docs/connections/lightning-recipe-reference.html | Supplier read-only NY_TAXI/TPCDS_DB starter |
| U11 | https://zetaris.github.io/getting-started/docs/connections/claude-code-connection.html | Harness wrapper around shared client setup |
| U12 | https://zetaris.github.io/getting-started/docs/connections/cursor-connection.html | Harness wrapper; reading it is not evidence of Cursor development |
| U13 | https://zetaris.github.io/getting-started/docs/connections/codex-connection.html | Harness wrapper, including command-environment network caveats |
| U14 | https://abdulwkazi.com/zcgsignup/ | Personal walkthrough, lower authority than vendor entitlement/terms; no free-compute guarantee |
| U15 | https://zetaris.github.io/getting-started/docs/install/managed-aws-cluster-guide.html | Official deployment guidance; resources and billing in the participant's AWS account |
| U16 | https://abdulwkazi.com/zcgls/ | Personal Apple Silicon/Docker walkthrough; no native ARM guarantee |
| U17 | https://zetaris.github.io/getting-started/docs/install/updated_zetaris_installation_guide.html | Official local bundle, Docker sizing and licensing guidance |
| U18 | https://zetaris.github.io/getting-started/ | Supplier navigation/entry point |
| U19 | https://github.com/zetaris/getting-started | Supplier recipes/client repository; platform accounts and drivers are separate |

A1 pins **`44668b267ad7ee0fae25ce7588e9620121d47cae`**. A direct GitHub API read found `main` at that same SHA, with committer timestamp **15 October 2026 00:07:47 UTC**. Use that immutable version for a reproducible onboarding check; re-check before later work. Official shared setup and implementation were additionally inspected at this commit: `AGENTS.md`, `docs/connections/client-setup.md`, `scripts/preflight.py`, `scripts/zetaris_sql.py`, plus the harness wrappers and related helpers reviewed in parallel. Supplier instructions apply to a future supplier workspace, not as replacements for Driftwatch's instructions.

Local-only public snapshots and size/SHA-256 manifests live in `/Users/ant/.hermes/cache/scratch/zetaris-docs-20261017/` (`linked-snapshots/manifest.json` covers the supplied URLs). Scratch is disposable evidence, not the durable project reference. No raw supplier document was copied into this public repo.

## 3. Rules reconciliation

A2 advertises a free participant instance, Tinkerer usage and Sponsor Tech scoring, but still says access/documentation **TBC before 22 October**. It does not prove we have access, define duration/quotas, or say integrations are optional.

The live event page was directly retrieved again on 17 October, including its expanded-rule payload. Rules §§4–5 still state the **22 October 00:00 → 27 October 23:45 UTC** build window, declared pre-existing components, mandatory Zetaris/Meterless integration and Cursor development; NVIDIA wording remains contribution-dependent on that page. Its §6 still calls for the demo, deck, repository and sponsor explanation. The older sponsor overview does not override these published rules. Source: https://hackathon.genai.works/event/open-agent-hackathon-2026 . The 14 October Academy/Nemotron wording conflict was not resolved by this doc set.

Keep the unresolved organiser gates: primary-track/Wildcard mapping, baseline declaration and final challenge, exact NVIDIA/Nemotron requirement, and whether the proposed Python Meterless adaptation satisfies sponsor expectations. No track was selected here.

## 4. Client connection is not platform deployment

| Path | Prerequisites and interpretation | Recommendation |
|---|---|---|
| Supplied/shared instance | Actual UI/JDBC/API addresses, account, permissions and team namespace; no local platform needed. SQL Editor requires no Java client. | First choice; access not verified. |
| Local platform | Bundle plus matching platform `.env`, registry credentials and entitlement; amd64 images; Docker with recommended 8 GB RAM, four CPUs, 15 GB disk; ARM needs emulation. | Separate fallback approval. The Mac's earlier no-Docker check is historical, not re-tested today. |
| Managed AWS | Connect own AWS account and deploy infrastructure/cluster; AWS charges separately; resources may cost even without active compute; suspension/deletion is not necessarily complete cleanup. | Do not provision for this assessment. Obtain account-specific cost/cleanup scope before any approval. |

The local install guide distinguishes the Apache-licensed recipes from platform images. It describes licence/evaluation entitlement, with up to 30 days' internal evaluation absent an Order—not indefinite platform rights. Confirm hackathon/demo entitlement; this review did not independently establish contractual rights. A blog's no-credit-card signup is not evidence of free AWS resources. [U14–U17]

Do not deploy the sponsor stack on the ARM OCI lab by default, extend the **21 October** teardown, or transfer personal sponsor credentials to the employer Windows machine. Existing cost/expiry verification and approval gates remain.

### Protocol choice

**Qualify, not blindly repeat, the 14 October REST-first recommendation:** REST is the lower-dependency candidate for Driftwatch's Python runtime, but the newly supplied prompt explicitly chooses **JDBC onboarding**. If approved for execution, honour that workflow and report protocol results separately. The eventual runtime protocol is a separate decision based on the actual exposed service, permissions, latency, driver availability and packaging cost. [A1; shared client setup]

| Route | Required settings / dependencies |
|---|---|
| JDBC | Supplied JDBC URL, username/password, **JDK 11+**, matching driver JAR. If path unset, ask for its full path; do not guess/search. Python runner additionally needs `.venv` and `jaydebeapi`; direct Java does not. |
| Direct REST | Supplied API base ending `/api/v1.0`, GUI-created bearer API key, explicit numeric organisation ID, UUID request identifiers. No JDK/JAR. |
| UI-proxy REST | Separate UI origin in `ZETARIS_BASE_URL`, appropriate auth and organisation settings. Passing direct REST does not verify this route. |

For the **supplier checkout**, its client settings belong in gitignored `.env.local`, never prompts/logs. Do not rename Driftwatch's existing `.env` to satisfy another repository's convention, or copy OCI/model secrets into the supplier workspace. The **platform bundle's** `.env` is yet another context. Any approved Driftwatch adapter should receive credentials through environment variables under Driftwatch's own conventions. GUI token creation is a user action; do not request tokens in chat. [shared client setup; U17]

## 5. Material implementation caveats

These are code-reading findings at the pinned supplier commit, independently checked in the parent review; they are **not failures observed against a live instance**.

| Supplier location | Observed behaviour | Consequence |
|---|---|---|
| `scripts/preflight.py:33–41,109–123` | Credential checks and combined failure counter; REST runs before JDBC even with `--jdbc`. | A combined failure status is not proof JDBC failed. Preserve per-protocol evidence and the A1 stop-on-JDBC-failure gate. |
| `scripts/preflight.py:63–71` | Probes hard-coded `localhost:10000`; all socket `OSError`s become “closed”; finds Java path without checking version. | Check the supplied remote host/port, preserve error type, confirm Java version. A denied local probe is not evidence a remote service is down. |
| `scripts/preflight.py:95–106` | Discovery failures are informational rather than fatal. | “READY” does not prove required sample-table discovery. Verify the named queries explicitly. |
| `scripts/zetaris_sql.py:184–221` | Direct REST defaults org ID to `1` and uses a **600-second** request timeout. | Supply actual org ID; do not copy timeout into Driftwatch's **540-second total budget** (`app/config.py:10–16`). Bound the whole operation by remaining time. |
| `scripts/zetaris_sql.py:251–294` | JDBC wrapper has no explicit connection/query deadline; fetches all rows before slicing; fetch exceptions return empty results. | Add demonstrable bounds/error handling for any adapted runtime client. Client-side `--limit` is not a fetch bound; use SQL `LIMIT` and verify completeness separately. |

Raw HTTP/server errors may contain sensitive response details; sanitize future logs. Any runtime adapter must distinguish auth/transport/query/parse failure from a genuinely empty complete catalog. Do not allow a failure to become “no declarations,” which would create false shadow-infrastructure findings.

## 6. Smallest useful Driftwatch scope — recommendation only

Current code re-read on 17 October:

- `app/sources/live.py:23–36` still selects file-backed `iac` and `policy`; these are the bounded integration seams.
- `app/sources/__init__.py:18–29` branches to fixtures before importing live code. Preserve that network-free sample-mode gate.
- `app/models.py:46–62` defines the exact `IaCDeclaration` and `PolicyRule` contracts. Policy `when` is a dictionary, so remote serialization must be specified, decoded and validated; a USL scalar schema cannot be assumed to carry it unchanged.
- `app/agents/scout.py:142–205` matches declarations and attaches policy/declaration evidence. Remote rows must actually drive that path, not just appear in a startup SQL call.
- `SourceResult.backend` is only `live`/`fixture` (`app/sources/base.py:24–29`). A future adapter needs explicit provider/object/query/version/count provenance without claiming an existing `zetaris` enum value. Pricing remains separate, as documented in the 14 October assessment.

Proposed sequence: **policy adapter → IaC declarations → shared evidence consumed by Scout/Skeptic**, alongside the separately scoped minimal Meterless World Model. Keep OCI signing, pagination and Monitoring windows in the working SDK adapters. Generic REST recipes do not establish OCI control-plane support.

Public/synthetic project reference data is sufficient. Do not send real tenancy identifiers, private infrastructure, credentials or employer data to a shared platform. A remote server cannot read a laptop-local JSON path: source hosting/registration and its permissions must be designed and approved. A controlled snapshot may be acceptable if disclosed as such; do not describe it as live zero-copy OCI federation. Confirm rights to share individual reference fields before uploading.

The cookbooks are **patterns, not a backlog**: NY Taxi/TPCDS establish client access; PokéAPI optionally establishes source registration but needs DDL approval. Finance/weather datasets do not improve this auditor. Catalogs explicitly label failures/unverified sources; USL/materialization is optional, not a minimum runtime prerequisite. The USL reference-gap example reinforces a useful requirement: preserve unmatched records and distinguish missing from incomplete data; inner joins must not silently hide resources. [U05–U10]

## 7. Next steps and stop gates

1. **Obtain participant access details, not new infrastructure.** Ask sponsor/organiser for UI URL, JDBC URL, matching driver distribution, account delivery method, organisation/team namespace, read/create permissions, supported REST route, availability/quotas/expiry, and hackathon entitlement. Credentials stay outside chat. Existing material does not establish these for us.
2. **Approve a read-only onboarding check in a separate pinned supplier checkout.** Proposed timebox: one hour of investigation before escalating blockers, not a completion estimate. Review prerequisites first; show missing dependencies and ask before installing. Honour A1's JDBC route, separate JDBC/REST outcomes and stop on JDBC blockers. No blanket readiness inference from the script's exit code.
3. **Prove SQL and table access.** `SELECT 1`, server version, `SHOW LIGHTNING DATABASES`, discovery of supplied NY_TAXI/TPCDS_DB tables, `DESCRIBE` and a qualified `SELECT ... LIMIT 5`. Missing samples are an access question, not permission to create replacements. Save sanitized results/timings and actual version. No PokéAPI creation is needed for this gate.
4. **Approve exact source/adapter scope only after access works.** Define team-owned policy/IaC object names, reachable reference source, schema/JSON mapping, read-only runtime role, row-count/completeness checks, timeout/degradation behaviour and rollback. Preview every proposed DDL/source registration and wait for separate approval; do not run a cookbook wholesale.
5. **Build new eligible work in the window once scope is approved.** Require generated proof: changed synthetic reference data affects an appropriate finding/critic outcome; fixture/remote parity; auth/timeout/malformed/truncated-result failures; unavailable-service fallback explicitly disclosed; unchanged curated/held-out evaluation quality; sample mode with sockets blocked and no credentials. A successful `SELECT 1` is not a meaningful runtime integration.
6. **Record real sponsor usage.** README and A2-requested `metadata.json` identify implemented placement, data type, protocol, limitations, adapted code and actual evidence. Actual Cursor development must be evidenced separately. Do not claim integration points or points earned from reading guides.

**Video gate:** consult a recording only if the assigned instance/driver procedure is unclear, a specific documented operation fails, or the organiser resolves an eligibility/entitlement question there. A video cannot supply our missing account or prove runtime behaviour.

## 8. Not performed

No supplier scripts executed; no service login or authenticated SQL; no credentials read; no dependency or Docker install; no signup, platform image download, object creation, cloud operation, lab retention change, product-code edit, generated evidence edit, commit or push. Public documentation was downloaded to local scratch for inspection. Operational readiness and sponsor integration remain unverified.

### Supplemental primary references

All following paths are under `https://raw.githubusercontent.com/zetaris/getting-started/44668b267ad7ee0fae25ce7588e9620121d47cae/`: `docs/connections/client-setup.md`, `AGENTS.md`, `scripts/preflight.py`, `scripts/zetaris_sql.py`, `scripts/zetaris_api.py`, `scripts/query_zetaris.py`, `scripts/run_sql.py`, `scripts/HOWTO.md`, `README.md`, `START-HERE.md`. Referenced supplier line numbers above apply only to that commit.
