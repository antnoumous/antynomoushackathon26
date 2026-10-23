# Zetaris on OCI — readiness and cost assessment

**Observed 18 October 2026 (SGT). Read-only assessment complete; deployment not performed.** The builder approved OCI deployment in the personal `antworld` tenancy and subsequently approved continued readiness/design activities while away. Registry access remains blocked by the vendor portal; this assessment did not create a VM, reserve capacity, register sources, install software or change Driftwatch product code.

## 1. Decision

**Prepare one dedicated x86 E5.Flex VM, but do not launch it while the vendor distribution gate is closed.** Recommended starting configuration: `VM.Standard.E5.Flex`, **2 OCPUs / 4 vCPUs / 16 GB RAM**, **50 GB Balanced boot volume**, current compatible Canonical Ubuntu 24.04 image, `ap-batam-1`. Keep it isolated from the existing audited A1 lab.

The exact tenancy identity, listed shape/image compatibility and quota headroom were verified through authenticated read-only APIs. **Physical host capacity, actual launch permission/success, Docker/Compose operation, registry pulls, platform health and sponsor eligibility are not verified.** A service allowance is not available physical capacity.[O1]

Deliverables:

- [Deployment/security/teardown runbook](../docs/zetaris-oci-runbook.md).
- [Proposed product integration design](../docs/superpowers/specs/2026-10-18-sponsor-integration-proposal.md), not implemented.
- [Generated sanitized OCI/bundle/test evidence](evidence/2026-10-18-zetaris-oci-readiness.json).
- [Generated Oracle catalog prices and Decimal calculations](evidence/2026-10-18-zetaris-oci-pricing.json).

## 2. Verified live target and resource discovery

The first identity read used the existing **`DRIFTWATCH2`** auditor profile and returned the exact tenancy name **`antworld`**. No default-profile assumption, real OCID dump or private-key display was used. Region subscriptions returned **`ap-batam-1`**, home region, `READY`; one availability domain was listed. Accessible active compartments were tenancy root, `lab-prod` and `lab-test`.

The existing lab remained separate: `lab-prod` contains `lab-batch-01`, `lab-reports-01`, `lab-web-01`; `lab-test` contains `lab-sandbox-tmp`. All four returned `RUNNING` on A1.Flex, each 1 OCPU/6 GB. The only listed VCN/subnet was the existing `lab-vcn`/`lab-public` in `lab-prod`. No network was reused or modified.

| Live catalog result | Assessment |
|---|---|
| `VM.Standard.E5.Flex` | Listed; preferred x86 candidate |
| `VM.Standard.E6.Flex` | Listed; same verified USD list-price rate at proposed size, potential alternative |
| `VM.Standard3.Flex` | Listed Intel alternative, higher computed price |
| `VM.Standard.E4.Flex` | Not listed in this target region/account; not a deployment fallback here |
| `Canonical-Ubuntu-24.04-2026.09.18-0` | Latest returned compatible Ubuntu 24.04 image, `AVAILABLE`; created 21 September 2026 |

The image list was queried with **shape and OS/version filters**, not selected by filename alone. Its reported image size is 47,694 MB; the proposed boot volume is 50 GB. Re-resolve actual image/AD/compartment IDs privately at launch rather than copying real identifiers into this public note.

## 3. Quota/resource allowances — not physical capacity

The auditor identity received **404 `NotAuthorizedOrNotFound`** from the limits API. The existing **`PROVISIONER2`** profile was then independently checked against `antworld` and used **only for read operations** to inspect limits/availability. No IAM/policy or limit increase was requested.

| Ordinary on-demand allowance | Used | Available |
|---|---:|---:|
| E5 OCPUs | 0 | 83 |
| E5 memory, GB | 0 | 1250 |
| E6 OCPUs | 0 | 83 |
| E6 memory, GB | 0 | 1250 |
| Standard3 OCPUs | 0 | 62 |
| Standard3 memory, GB | 0 | 1666 |
| Block storage, GB | 250 | 61190 |
| VCN count | 1 | 49 |

The proposed 2 OCPUs/16 GB/50 GB fits these reported ordinary allowances. Dedicated-host, reserved and reservable values were deliberately excluded from this comparison; some returned zero and are not the resources being proposed. The subnet resource-availability API returned **null**, not zero: no subnet headroom is claimed from that call. Recheck the new compartment's effective quotas and network rules before creation.

The reported internet-gateway limit of one must not be read as an account-wide prohibition on a second VCN: Oracle documents one internet gateway **per VCN**.[O2] Do not infer a guaranteed successful launch from shape listing, limits, positive credit, or a previous launch in another architecture.

## 4. List-price calculation

### Sources, currency and scope

Oracle's official public product catalog was directly retrieved and checked in the parent assessment, not accepted solely from a delegated summary. Catalog `lastUpdated`: **8 October 2026 14:38:16.165 UTC**. The relevant **eight distinct SKUs**, their **USD `PAY_AS_YOU_GO`** rates and calculations are retained in the generated pricing evidence.[O3]

| Shape | OCPU SKU / USD per OCPU-hour | Memory SKU / USD per GB-hour | Proposed compute / hour |
|---|---|---|---:|
| E5.Flex | `B97384` / 0.03 | `B97385` / 0.002 | **0.092** |
| E6.Flex | `B111129` / 0.03 | `B111130` / 0.002 | **0.092** |
| Standard3.Flex | `B94176` / 0.04 | `B94177` / 0.0015 | **0.104** |

For the proposed 50 GB Balanced boot volume:

| Component | SKU | USD rate |
|---|---|---:|
| Provisioned storage | `B91961` | 0.0255 / GB-month |
| Performance | `B91962` | 0.0017 / VPU-per-GB-month |
| Selected performance | 10 VPUs/GB | Combined **2.125 / full calendar month** |

Compute formula: `2 × OCPU-hour price + 16 × memory-GB-hour price`.
Boot formula: `50 × (0.0255 + 10 × 0.0017)`.

Oracle's storage-pricing footnote specifies per-second proration after a one-minute minimum using the actual seconds in each calendar month, not a fixed 730-hour month.[O4] For unknown launch dates in October/November, the table gives the 31-day/30-day denominator range; **these are runtime durations, not an instruction to start now or an exact submission-window duration**. All calculations used Python `Decimal`.

| Runtime | E5 or E6: compute + 50 GB boot | Standard3: compute + 50 GB boot |
|---|---:|---:|
| 24 hours | **USD 2.2765–2.2788** | USD 2.5645–2.5668 |
| 144 hours / six days | **USD 13.6593–13.6730** | USD 15.3873–15.4010 |
| 480 hours / twenty days | **USD 45.5310–45.5767** | USD 51.2910–51.3367 |

**These are compute-plus-boot subtotals, not an all-inclusive quote or cash invoice.** No trial credit, Always Free deduction, tax or FX conversion was applied. The screenshot supports a 26 November subscription expiry and low usage at capture time; it is not a fresh API credit balance or a guarantee of this deployment's cash treatment.

A current separately priced public-IPv4 SKU was **not found** in the retrieved catalog, including a parent-side scan for public-IP/IPv4/address products. That is a pricing-verification gap, not proof that an address costs zero. Do not import `data/pricing.json`'s orphan reserved-IP assumption into the attached ephemeral-IP estimate. Also excluded: Zetaris licence/support, registry charges, additional storage/backups, paid network services, transfer charges beyond allowances, taxes and account-specific discounts. No new public-IP reservation, NAT gateway, load balancer or backup is proposed.

Before any launch: reprice against the actual start/teardown time and account terms, verify current credit, record the cost envelope, and retain a cleanup manifest. Provision only after the registry issue is resolved. Recommended operational budget is to minimise service lifetime, not consume the remaining credit simply because it exists.

## 5. Bundle findings that change the deployment plan

The private ZIP's hash, integrity/path checks and actual Bash syntax-check exits are in generated evidence. **Five shell scripts passed `bash -n`; this did not execute them.** No bundled `.env` or `.env.server.example` was read. Credential-related lines were suppressed from displayed README/Compose/script review copies.

Important differences from the older generic guide:

1. **Actual service set:** `postgres`, `init`, `driver`, `api`, `ui`, `bootstrap`, optional `caddy`. That is six default services plus optional Caddy. **No `ai-datasteward` service exists in the inspected Compose file.** Do not invent/install it to satisfy an older guide's service list.
2. **UI publication:** UI defaults to a host-wide port publication; API/JDBC/Spark have loopback bindings. Apply a reviewed replacement-port override before starting, in addition to OCI ingress restrictions. Docker warns that published ports can bypass `ufw`; merging ordinary port lists can preserve the original exposure.[D1][D2]
3. **TLS versus tunnel:** the bundle documents that browsing plain HTTP at a remote hostname/IP can fail due to browser secure-context requirements. Use localhost through SSH forwarding for this build. Optional Caddy/public HTTPS is a separate design, not necessary for tunneled local use.
4. **Persistence:** named Docker volumes store metastore/audit, shared keys, driver data/logs and customer data on the boot volume in the proposed design. `down -v` destroys data/keys; deleting the boot disk destroys their storage unless separately backed up.
5. **Verifier scope:** the actual script checks four long-running services, two one-shot jobs, UI configuration, login and an end-to-end query **`select 7 as seven`**. A separate `SELECT 1` check must still be run if claimed. It obtains the real org ID from login; do not assume `1`.
6. **Registry preflight:** checking Docker config for a registry name is weaker than authenticating and pulling the exact issued images. No login/pull was attempted.
7. **Bootstrap:** the bundled first start registers vendor sample sources. This is a platform setup side effect, not the proposed Driftwatch source integration. Additional recipe DDL remains a separate scope.

The runbook specifies a private SSH-only deployment, a Compose `!override` loopback configuration requiring version 2.24.4+, service-aware verification and explicit cleanup. That configuration is a documented proposal, **not a Docker-rendered or runtime-tested artifact** on this Mac.

## 6. Retention and build-window boundaries

- The existing audited lab's **21 October** teardown is unchanged by this assessment. New sponsor infrastructure is separate.
- Do not start billing while waiting on registry credentials.
- Minimum retention: only as long as needed for setup/integration and generated evidence. Preserve offline judge reproduction independently.
- Optional upper planning checkpoint: **7 November 2026 00:00 UTC**, after the recorded 6 November results announcement, only if live judging requires it. Final exact start/teardown dates go in the deployment manifest. This is not a scheduled job or a reason to retain until trial expiry.
- New product work must be attributed to the actual **22 October 00:00 → 27 October 23:45 UTC** build window; declared pre-existing baseline and preparation remain separate. No product integration was implemented here.

## 7. Verification, remaining gates and next trigger

**Executed:** authenticated read-only identity/region/resource/image/shape/limits checks; archive integrity/path and shell syntax checks; current primary-source price retrieval; Decimal costing; full existing offline test suite. **Result: 116 tests passed**, one existing Starlette/AnyIO deprecation warning. Exact output is in the generated readiness evidence. No model endpoint was called.

**Not executed:** launch/capacity reservation, Docker install/render/pull/start, service authentication, SQL discovery/sample query, source registration, persistent World Model implementation or Nemotron capability test. No working deployment/integration claim is made.

Remaining external gates:

- Zetaris support resolves the registry-access error and confirms the applicable distribution/evaluation entitlement.
- Organiser clarifies OCI hosting and the local-Meterless/Nemotron wording if those remain eligibility questions. No messages were sent on the user's behalf; the user reports already emailing support.
- Native x86 host capacity, launch permissions, final cost/cleanup timestamp and hardened runtime are verified at execution time.
- Product integration proposal gets the appropriate design review before implementation; the builder's broad approval to continue this preparation is recorded, not used to pretend a not-yet-written spec was already reviewed.

**Trigger:** when legitimate registry access is available, use the prepared runbook and actual cost/identity rechecks. No further open-ended document research or unrelated public dataset onboarding is necessary to begin that controlled deployment.

## Primary references

[O1] https://docs.oracle.com/en-us/iaas/Content/Compute/Concepts/computeoverview.htm — service allowance versus physical host capacity.

[O2] https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingIGs.htm — internet-gateway scope and routing.

[O3] https://apexapps.oracle.com/pls/apex/cetools/api/v1/products — official catalog source, with exact selected rows/hash in generated evidence; https://www.oracle.com/cloud/price-list .

[O4] https://www.oracle.com/cloud/storage/block-volumes/pricing/ — calendar-month/per-second storage-proration rules; https://www.oracle.com/cloud/storage/block-volumes/faq/ — provisioned boot-volume pricing.

https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm — x86 OCPU/vCPU mapping; live API is the target's shape/limit evidence.

[D1] https://docs.docker.com/engine/install/ubuntu/ — supported installation and firewall implications.

[D2] https://docs.docker.com/reference/compose-file/merge/ — replacement semantics and version requirement.

The supplier archive is a private input; only findings and its checksum are retained here. Real OCIDs, private billing screenshot, keys, tokens and vendor env values are not copied into this repository.
