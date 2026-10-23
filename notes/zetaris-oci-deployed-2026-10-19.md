# Zetaris OCI deployment — verified 19 October 2026

## Result and scope

The approved, dedicated self-managed platform is **running in `antworld`, `ap-batam-1`**.
This is pre-build-window infrastructure preparation, not a completed Driftwatch sponsor integration
or proof of event eligibility. The published new-work window remains 22–27 October; declare this
setup and the September application baseline separately.

Generated acceptance evidence: [`evidence/2026-10-19-zetaris-deployment.json`](evidence/2026-10-19-zetaris-deployment.json).
The earlier [readiness assessment](zetaris-oci-readiness-2026-10-18.md),
[runbook](../docs/zetaris-oci-runbook.md) and
[product proposal](../docs/superpowers/specs/2026-10-18-sponsor-integration-proposal.md)
remain references; their unexecuted/blocked descriptions are historical.

## What was created and verified

- Dedicated `sponsor-services` compartment; `zetaris-vcn`, public subnet, internet gateway,
  internet route and dedicated security rules. No peering or shared lab networking.
- Instance `zetaris-01`: **E5.Flex, 2 OCPUs / 4 vCPUs, 16 GB RAM**, Ubuntu 24.04.5 x86_64.
- **50 GB boot volume, Balanced 10 VPUs/GB**; ephemeral public IPv4. No reserved address,
  extra volume, NAT gateway, load balancer, DNS service or paid backup was created.
- The write profile's exact tenancy was rechecked before creation. Every created resource ID
  was saved privately and read back. Instance shape/state/tags, storage performance, public IP
  lifetime, subnet/security-list attachment and absence of attached NSGs were reverified.
- Ingress permits **TCP 22 from one current builder IPv4 `/32` only**. Outbound access supports
  required packages, registry and public sample S3 sources. No public application-port ingress.
- SSH uses a dedicated client key and a locally provisioned, pinned server host key; strict
  checking remains enabled. No OCI API private key or provisioner configuration went to the VM.
- Docker Engine **29.9.1**, Compose **5.6.0**, installed on the new VM from Docker's official
  Ubuntu repository. No Docker, JDK or Python bridge was installed on the Mac.
- Original archive hash matched the inspected bundle. The three issued image manifests were
  authenticated first; full images were subsequently pulled, with actual runtime digests saved.
- Matching vendor configuration retained; default administrator/database passwords replaced.
  Telemetry configuration was preserved rather than silently disabled.

## Runtime acceptance

| Check | Actual result |
|---|---|
| Vendor preflight | All required checks passed |
| Vendor `verify.sh` | **9 passed, 0 failed**, including its `select 7 as seven` end-to-end query |
| Long-running services | Postgres, driver, API and UI all running/healthy |
| One-shot jobs | `init` and `bootstrap` both exited **0** |
| Actual engine query | `SHOW SERVER VERSION` reports **2.4.3.1** |
| Direct REST | Seven authenticated read-only checks succeeded with the administrator JWT |
| JDBC | The same seven checks succeeded with the supplied proprietary JAR, inside the driver container using its existing Java 17 compiler module |
| Sample catalog | **15 NY_TAXI tables, 24 TPCDS_DB tables** enumerated, not assumed from documentation |
| Sample read | `SELECT * FROM NY_TAXI.customers LIMIT 5` returned **5 rows** |
| Description | `NY_TAXI.customers` returned **17 columns** |
| Local access | SSH tunnel active; local UI configuration and administrator login both returned HTTP **200** |
| Network | Runtime publications are **127.0.0.1 only**: UI 3000, REST 8888, JDBC 10000. External TCP probes from the builder did not connect to 3000/8888/8889/10000/4040/5432/8080 |

The seventh-query count includes `SELECT 1`, version, database listing, both table listings,
customer description and the limited customer SELECT. JDBC was **not** tested through a Mac
JDK/`jaydebeapi` bridge. Direct REST used an administrator JWT from UI login; a separate
read-only runtime principal/API token has **not** yet been established. This admin smoke test
is not the product's future least-privilege credential design.

## Private operator handoff

Local-only operational files are under `/Users/ant/.oci/zetaris-deployment/`:

- `manifest.json`: exact owned resource IDs, current network address, retention/cost checkpoint.
- `ssh_ed25519`, `known_hosts`, `ssh_config`: dedicated SSH identity and strict tunnel configuration.
- `platform-admin.json`: generated UI administrator credentials, **mode 0600**. Open locally;
  never paste it into chat, put it in a screenshot, attach it to a ticket or commit it.
- Private runtime/SQL/JDBC/verifier evidence; these are not automatically publication-safe.

The current tunnel exposes the UI at `http://localhost:3000`. To re-establish it after this
session or after a tunnel exit, use the dedicated config, not an address copied from a report:

```sh
ssh -F /Users/ant/.oci/zetaris-deployment/ssh_config -N zetaris-01
```

Do not launch a duplicate tunnel while those ports are already bound. The local source `/32`
can change when the builder changes networks; reassess the single owned security rule rather
than opening SSH to the world. Tunnel persistence across desktop/session shutdown is not
promised, and service restart after an OCI reboot was not exercised in this acceptance.

Remote platform directory: `/home/ubuntu/zetaris-private/zetaris-platform`.
Use `sudo` for Docker operations, with **both** `docker-compose.yml` and `compose.loopback.yaml`.
The driver/API/UI and database defaults use `restart: unless-stopped`; no Docker-group access
was granted to the login user. Root's Docker auth and the matching `.env` must remain private.
Do not run `down -v`, overwrite the installation, or reset metastore volumes to diagnose a login.

## Cost and retention

Prior verified gross compute-plus-boot estimate: **about USD 2.28/day**, excluding unresolved
network/IPv4/vendor costs, taxes and account-specific credits. Private manifest records a
**USD 46 gross compute/boot envelope** and **7 November 2026 00:00 UTC** retention checkpoint
(**08:00 SGT**). This is **not an automated teardown schedule** or proof of all-inclusive cost.
Prefer earlier cleanup once live access/evidence is no longer needed. Trial expiry remains
26 November according to the supplied billing evidence; current credit balance was not refreshed
through a billing API. Existing audited lab teardown remains separate and was not changed.

## Actual failures, repairs and API distinctions

1. Immediate readback of the newly created compartment returned 404; a later exact-ID read
   returned ACTIVE. No IAM expansion or alternate resource creation was used to bypass it.
2. The initial client-side image-pull command hit the tool's time limit. A bounded server-side
   systemd job completed the pull; actual image inspection confirmed all required images/digests.
3. Operator preparation initially made all shell scripts 0700 under root. The non-root driver
   (UID 1001) could not read its bind-mounted entrypoint. Only non-secret `init/*.sh` scripts
   were changed to 0755; `.env`/private key permissions remain restrictive. This was our
   preparation error, not a claimed vendor defect.
4. The initial generated administrator password was long random hexadecimal but failed Zetaris's
   lowercase/uppercase/number/special-character policy. Logs proved user registration failed,
   explaining login HTTP 404. A policy-compliant random secret was generated and affected
   containers recreated, **without deleting volumes**. Both bootstrap and login then passed.
5. `/query/sql/start` accepts SELECT requests, not arbitrary SHOW/DESCRIBE text. Sending the
   latter there returned HTTP 400 `Bad Select SQL`. The documented general SQL endpoint
   `/api/v1.0/sql-editor/sqls/run` succeeded for all seven checks. Do not misdiagnose this
   request-schema rejection as a missing database or absent engine feature.

## Still outside this completed deployment

No custom Driftwatch reference objects, adapters, World Model, Nemotron configuration/calls,
track switch, model-driven verdicts or submission compliance claim. No product code changed;
no commit/push was performed. Existing dirty repository work was preserved. Organiser OCI-hosting
acceptance and vendor entitlement/licensing scope were not independently confirmed by a written
reply; successful authentication/pulls establish technical access, not those legal/event claims.

Next product step remains review of the bounded proposal, a reviewed implementation plan and
build-window attribution. The deployed infrastructure makes a real connection test possible;
it does not replace the source-completeness, least-privilege, deadline and offline acceptance gates.
