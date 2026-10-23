# Zetaris on OCI — deployment and cleanup runbook

**Prepared 18 October 2026 (SGT); executed 19 October.** The approved dedicated `antworld`
deployment now passes platform acceptance. See the [actual results and operational handoff](../notes/zetaris-oci-deployed-2026-10-19.md)
and [generated evidence](../notes/evidence/2026-10-19-zetaris-deployment.json). The steps below
preserve the original gated plan; do not replay creation against the existing deployment.
Private-registry access is resolved. Product integration is not implemented by this runbook.

Read [approval and access status](../notes/zetaris-oci-deployment.md) and the [readiness assessment](../notes/zetaris-oci-readiness-2026-10-18.md). No employer account or machine is involved. Existing audited lab resources and their teardown are outside this runbook's scope.

## 1. Selected approach and prerequisites

**Preferred:** one on-demand `VM.Standard.E5.Flex`, **2 OCPUs / 16 GB RAM / 50 GB Balanced boot volume**, in `ap-batam-1`, using the current shape-compatible Canonical Ubuntu 24.04 x86 image. The live discovery returned `Canonical-Ubuntu-24.04-2026.09.18-0`; re-resolve its real image OCID privately at deployment time. Use ordinary on-demand capacity, not a dedicated host, reservation, preemptible instance or ARM emulation.

E6.Flex and Standard3.Flex were also listed by the live tenancy API. E4.Flex was not. Shape listing and free quota do not prove physical host capacity or a successful launch. Recheck immediately before provisioning; do not probe by launching temporary paid instances or reserve capacity just to test.

Keep the service in a **new `sponsor-services` compartment and dedicated VCN/subnet**, not in `lab-prod`/`lab-test` and not on a lab A1. No peering or shared security lists with the audited workloads. Verify the selected network CIDRs do not conflict with networks we intend to connect; exact CIDRs/OCIDs go in a private deployment manifest rather than this public document.

Before resource creation, require:

- Exact API target still resolves to tenancy name `antworld`; region is `ap-batam-1`.
- Read-only discovery evidence and current cost estimate reviewed; credit expiry is **26 November 2026**, supported by the user's screenshot, not inferred from resource age. The current balance was not refreshed through a billing API.
- Registry-access support issue resolved through the vendor, with explicit permission to pull the issued images. A ZIP download and a locally stored registry login are not proof of image access.
- Licence/evaluation and event deployment requirements understood. The downloaded page permits a server one controls, but OCI-specific event eligibility has not been confirmed by the organiser.
- Private archive hash matches the inspected original: `14c6a811a140378bec1749ceffd7fa123bafb2f178545b26354e8f9433b413d3`. If the vendor issues a new archive, inspect it as a new version rather than mixing files.
- Matching platform configuration and registry credentials kept private; approved secret-handling path available. Never display or commit the bundle `.env`, resolved Compose environment, Docker auth config or private SSH key.
- Explicit UTC teardown timestamp and cost envelope entered in the deployment manifest. **Proposed maximum retention: 7 November 2026 00:00 UTC**, after the recorded results time, only if judge access is actually required. Default to earlier cleanup once evidence is captured and no live access is needed. Trial expiry is not a retention target. The user's broad activity approval is not a reason to bypass these checks.

## 2. Network design: SSH tunnel, not public application ports

For this solo build, use a public-subnet VM with an **ephemeral** public IP and an internet-gateway route for required outbound package/image/source access. Do not allocate a load balancer, NAT gateway, reserved address, public DNS name, certificate service or paid backup by default.

Ingress: **TCP 22 only from the builder's current authorised public IPv4 `/32`** (or a separately authorised VPN CIDR). Discover and record the source at execution time; do not hardcode it from old sessions or fall back to `0.0.0.0/0`. All application/database/Spark ports remain closed to the internet. Review both subnet security lists and attached NSGs: permissive rules are additive and an NSG is not an overriding deny policy.

Outbound access must support the registry/CDN, OS packages, public sample bucket and any approved reference source. Start with the normal stateful egress policy rather than inventing an IP allowlist that breaks Azure/CDN/S3 resolution; retain OCI DNS/metadata access. No OCI provisioner keys or instance-principal policy are needed by the Zetaris VM itself.

Use two layers of protection:

1. OCI ingress restricted to SSH; no ingress for `3000`, `8888`, `8889`, `10000`, `4040`, `5432` or `8080`.
2. Replace host port publications in the local deployment override. The inspected bundle already binds API/JDBC/Spark to loopback, but **UI defaults to all host interfaces**. Do not rely only on a guest `ufw` rule: Docker publishing can bypass it.[D1][D2]

Planned `compose.loopback.yaml` (configuration specification; **not installed or render-tested**):

```yaml
services:
  ui:
    ports: !override
      - "127.0.0.1:3000:3000"
  api:
    ports: !override
      - "127.0.0.1:8888:8888"
  driver:
    ports: !override
      - "127.0.0.1:10000:10000"
  postgres:
    ports: !override []
```

`!override` requires **Compose 2.24.4 or later** and fully replaces the list. An ordinary added ports list can retain the original publication; that is not acceptable.[D3] Pin/verify a compatible Compose release during installation. Keep `COMPOSE_PROFILES` empty so the optional Caddy TLS service does not publish 80/443. Never change the API container's internal service-to-service port simply because we remove its host publication.

For every Compose operation, use the same selected project/files, either explicit `-f` flags or a private, consistent `COMPOSE_FILE` setting. Example render check:

```sh
docker compose -f docker-compose.yml -f compose.loopback.yaml config --quiet
```

Inspect only the rendered **port bindings/service names** using a filtering procedure; never print a complete resolved config with secret values. Require no host binding on `0.0.0.0` or `::`. If `!override` is unsupported, stop and correct the tool version; do not start with an additive fallback.

Reach the service from the personal Mac using an SSH tunnel:

```sh
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:3000:127.0.0.1:3000 \
  -L 127.0.0.1:8888:127.0.0.1:8888 \
  -L 127.0.0.1:10000:127.0.0.1:10000 \
  ubuntu@<private-manifest-public-address>
```

Use an approved key already associated with this new host, and verify the SSH host key through the deployment record/Console. Do not disable strict host-key checking. Bind forwards only to loopback. If a local port is occupied, select a free local port and update the client settings without changing the remote port.

With the browser at `http://localhost:3000`, the bundled UI's localhost secure-context exception applies. Do not browse the VM's public IP over plain HTTP: the bundle README documents a `crypto.randomUUID` failure outside secure contexts. A future public judge-facing UI would require a separate HTTPS/access design, not an emergency open-port workaround.

## 3. Resource creation — only after the gate opens

Use `PROVISIONER2` for explicit build-time writes, never the read-only auditor identity. Re-verify the target before any write. Record every resource's real ID in a gitignored/private manifest, with human-readable aliases in public notes.

Suggested names: compartment `sponsor-services`; VCN `zetaris-vcn`; subnet `zetaris-public`; instance `zetaris-01`. Check for existing matches first; names alone do not establish ownership. If an object exists, compare its compartment, tags and specification before deciding whether to reuse it. Never mutate an unrelated same-name resource.

Apply a dedicated ownership tag set such as `project=driftwatch`, `purpose=zetaris-sponsor`, `owner=ant`, plus the chosen `expires_at` timestamp. These are proposed governance tags, not evidence of Terraform management.

Create only: compartment, VCN and its required DHCP/security/route objects, one internet gateway, subnet/NSG, one on-demand VM and its 50 GB boot volume. Use an ephemeral address. No capacity reservation, secondary volume, load balancer, cluster or DNS zone. Keep launch retries bounded; a host-capacity failure is not permission to alter IAM or open another region without reassessment.

Verify by reading back the exact created IDs: lifecycle, shape config, image, boot-volume performance, network attachment, public-IP type, ingress/egress, and tags. Do not claim success on the create response alone.

## 4. Host preparation and private artifact transfer

On the new Ubuntu host only:

1. Confirm OS, architecture, available CPUs/RAM/disk and network access. Install Docker Engine, CLI, containerd and the Compose plugin using Docker's current official Ubuntu repository instructions.[D1] No `curl | sh`, no Podman shim, no developer workstation installation.
2. Check Docker server version and Compose version. Keep Docker administration privileged; membership in the Docker group is effectively root access, so use a deliberate account/sudo policy rather than broad group access.
3. Transfer the verified bundle privately, preserve the original unchanged, inspect paths and unpack into a dedicated service directory outside the source repository. No public artifact bucket or anonymous download link.
4. Keep the supplied configuration files as a matching set. Do not source `.env` as shell code; do not replace issued image references with guessed moving tags. An `.env.server.example` exists, but do not blindly copy it over the matching file or expose its defaults. Explicitly set private administrator values and the chosen non-secret sizing/URL settings through the approved secret workflow.
5. Start with the documented laptop-size engine allocation (`2g`, two engine threads, API heap `1g`) on the larger native x86 host; this is a reference-data demo, not a benchmark. Profile and increase only if the observed workload needs it. Keep the shared run budget in the application, independent of host service startup time.
6. Keep `ALLOWED_ORIGINS` and `GUI_URL` aligned with the actual tunneled browser URL. Do not assume org ID `1`; the verifier extracts the actual organisation ID from login.
7. Review the bundled telemetry configuration and applicable event requirements before startup. The Compose file contains telemetry variables; the private `.env` was not opened, so this assessment does not assert whether telemetry is enabled. Never fabricate telemetry or disable an eligibility requirement to make a smoke check pass.
8. Set private file/directory permissions. No `.env`, registry auth, SSH key, raw login response, platform keypair or Docker volume enters Git or a public report.

Registry login is user/vault-controlled on this host. Use the issued procedure without printing secrets or putting a password in process arguments. `preflight.sh` only checks for a registry reference in Docker config; **an authenticated pull of the exact issued images is the definitive distribution check**. Do not create another credential or guess a registry username to get around the portal error.

## 5. Start and verify

The archive contains **six default services**, plus optional Caddy: four long-running (`postgres`, `driver`, `api`, `ui`) and two one-shot jobs (`init`, `bootstrap`). The public install guide's `ai-datasteward` expectation does **not** match this inspected Compose file; absence of that service is not by itself an install failure. Resolve the difference against the actual issued bundle, not by inventing another container.

Use the hardened Compose selection consistently for all commands and for the vendor verifier. The verifier internally invokes plain `docker compose`; propagate `COMPOSE_FILE` so it inspects the same model. Run the vendor preflight only after registry access and host prerequisites exist; it is not a bypass for missing entitlement.

Sequence: validate configuration quietly → preflight → pull → start detached → inspect all service states → run `verify.sh`. Wait for observed health/completion rather than declaring success after a fixed sleep. Keep startup polling finite and record the last healthy component on failure. Do not run a vendor destructive reinstall/test suite against this installation.

Acceptance evidence:

- Four long-running services running/healthy; `init` and `bootstrap` completed with exit 0. Optional Caddy absent/inactive.
- Actual vendor verifier passes all applicable checks (the inspected version performs UI configuration, login and an end-to-end `select 7 as seven`; **do not label its query `SELECT 1`**).
- Independently run authenticated `SELECT 1`, `SHOW SERVER VERSION`, `SHOW LIGHTNING DATABASES`, sample table listing/description, then SQL `LIMIT 5` from an actual accessible supplied table. A missing sample is a source/access issue, not permission to create it during a read-only check.
- Actual organisation ID and chosen protocol validated separately: direct REST, UI proxy and JDBC are different paths. JDBC needs matching JAR and a tested JDK/Python bridge on the client where it runs. The platform VM does not need a second host JVM just to run its containers.
- `docker ps`/host socket inspection and OCI rule readback show no publicly reachable application ports; verify the Mac can use the tunnel and that external connections are blocked. A static YAML review does not satisfy this runtime check.
- Record selected image digests, bundle hash, engine version, configuration profile, health results, table counts, timings and failure/degradation outcomes without secrets. JAR filename is not proof of running engine version.
- Resource/service ownership and cleanup manifest complete. No unmasked real OCIDs in publication copies.

Do **not** register PokéAPI or the proposed Driftwatch reference objects during this infrastructure acceptance phase. Their DDL and data placement belong to the product-integration scope and build-window attribution.

## 6. Persistence, recovery and cleanup

Compose named volumes include Postgres metastore/audit, driver data/key material, driver logs and shared customer data; optional Caddy also has data/config volumes. They reside on the selected VM's boot storage in this design, so there is no automatic independence from VM/boot-volume deletion.

- Routine pause: `docker compose stop` retains data. OCI compute stop can save eligible CPU/RAM charges, but boot storage remains and restart capacity may not be available; do not call a stopped VM a zero-cost deployment.
- Recreate containers: `docker compose down` retains named volumes; this is not a tested disaster-recovery procedure.
- **Never use `down -v` to troubleshoot**: it removes metastore, shared keys and encrypted data. Do not run `docker system prune --volumes` as a space-management shortcut.
- Before an authorised final teardown, export only needed reference definitions and generated evidence to private storage; sanitize separate publication copies. A ZIP of logs is evidence preservation, not a full backup or a demonstrated restore.
- Preserve the independent existing OCI audit lab untouched. Use exact new resource IDs and ownership tags, not broad compartment/name-prefix deletes.

Teardown order: capture agreed evidence → stop the sponsor service → terminate the new VM with **boot-volume deletion explicitly selected** → verify boot volume and any backups are actually gone → remove owned address allocations/NSG/subnet/routes/gateway/VCN → remove the new compartment only if empty and approved. Re-read every target after deletion. Retained boot volumes, backups or reserved IPs can outlive a VM.

At the retention checkpoint, record whether judging still needs a live service. No unattended retention beyond the selected timestamp without reassessment. No deletion of the existing lab on 21 October is performed or rescheduled by this runbook.

## 7. Stop conditions

Stop and report, rather than improvise, on: registry/entitlement failure; wrong tenancy; no eligible x86 capacity; cost envelope exceeded; unexpected public binding; missing/changed matching vendor config; unresolved secret-entry route; bootstrap data source failure; failed authenticated query; or conflict with final event requirements. Never weaken audit thresholds, fabricate sponsor evidence, expose an internal login endpoint, or change another team's objects to obtain a demo.

## Primary references and evidence

- Downloaded bundle SHA-256 above: `README.md`, `docker-compose.yml`, `preflight.sh`, `verify.sh`, `caddy/Caddyfile`, `conf/spark-defaults.conf` inspected through credential-redacted copies; private env files not read. Raw supplier files are not copied into the public repo.
- OCI discovery/limits evidence: [sanitized assessment](../notes/zetaris-oci-readiness-2026-10-18.md).
- [D1] https://docs.docker.com/engine/install/ubuntu/
- [D2] https://docs.docker.com/engine/network/port-publishing/
- [D3] https://docs.docker.com/reference/compose-file/merge/
- https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm
- https://docs.oracle.com/en-us/iaas/Content/Compute/Concepts/computeoverview.htm
- https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingIGs.htm
- https://zetaris.github.io/getting-started/docs/install/updated_zetaris_installation_guide.html
