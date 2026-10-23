# OCI expiry: Driftwatch impact assessment and free-only backup plan

**Assessed:** 13 October 2026, morning SGT. **Constraint:** no paid upgrade, no new trial account, no new resources or deletion without approval.

> **Same-day correction:** the user clarified that the expiry notice concerns the original `antnynomous` tenancy, not the hackathon lab `antworld`, which remains active and available. A fresh signed check of `DRIFTWATCH2` confirmed tenancy name `antworld` and all four lab hosts RUNNING. The 13 October expiry must **not** be attributed to `antworld`. Do not execute the conditional Plan B cleanup on the basis of this notice. Keep the hackathon lab unchanged; the free-only capacity issue below is a separate planning concern for its own eventual trial expiry. Its actual credit balance and expiry date remain unverified by this assessment.

## Bottom line

The hackathon submission can survive loss of the live tenancy. The primary credential-free path is working and was re-verified today. The four-host lab is **not safely within the current documented Always Free envelope**. Preserve data first; do not interpret today's running state as a survival guarantee.

The user's notice gives expiry as **13 October 2026 00:25 UTC / 08:25 SGT**, already past, and the user subsequently attributed it to **`antnynomous`**. It does not supersede the lab tenancy's separate expiry estimate. Gmail OAuth returned `invalid_grant`, and browser access was unavailable; the exact email wording, subscription status, and credit balances have not been independently verified.

## 1. What expired, and why this matters

For a standard Oracle trial, promotional credit expires; this does not ordinarily end Always Free eligibility. Trial credit can end through elapsed time or credit exhaustion. Some special promotions behave differently, so the notice must be matched to the actual tenancy.[4]

Oracle's retrieved documentation now specifies an A1 allowance of **2 OCPUs and 12 GB RAM**, rather than the 4/24 assumption recorded in the project. Boot and block storage share a **200 GB** home-region allowance.[1]

Oracle separately warns that an over-allowance A1 fleet at trial expiry can have **all A1 instances disabled**, followed by deletion after 30 days unless upgraded.[2] We are not recommending an upgrade. General promotion guidance describes a grace period, but the FAQ describes only a few days of continued resource existence and the specific A1 rule is harsher; do not treat that grace period as guaranteed working compute through the hackathon.[3][4]

## 2. Read-only live facts

Signed OCI SDK calls succeeded using only the existing auditor profiles. API inventory was captured at **13 October 2026 02:36 UTC / 10:36 SGT**. No resource was created, stopped, resized, terminated, or upgraded.

| Item | Lab: `antworld` / `DRIFTWATCH2` | Original: `antnynomous` / `DRIFTWATCH` |
|---|---|---|
| Region checked | ap-batam-1 | ap-batam-1 |
| Nonterminated compute | Four A1.Flex hosts, all RUNNING | `antos`, A1.Flex, RUNNING |
| Total A1 OCPUs / RAM | 4 / 24 GB | 1 / 6 GB |
| Boot storage | Four 50 GB boots: 200 GB | One 47 GB boot |
| Extra block storage | `vol-orphan-50g`: 50 GB | `vol-orphan-50g`: 50 GB |
| Combined boot + block | **250 GB** | **97 GB** |
| Reserved IP observed | `ip-orphan`, unattached | `lab-prod-ip`, unattached |
| Fresh CPU streams | All four reporting after the stated expiry | Root-compartment CPU was not checked in this assessment |

These totals concern the checked region, accessible compartments, and listed resource types—not a complete billing or all-service audit. The auditor response did not establish per-resource Always Free labels or account billing status. The original tenancy fits the published compute/storage numbers; that is not a certification that every resource is free.

### Fresh Driftwatch live result

Run `run-9f4353766f` completed successfully:

- Inventory and telemetry: live. Declarations and policy: file-backed, as designed.
- Six resources examined; four findings accepted, one rejected, two undetermined entries; zero degraded sources.
- A real `request_recheck` occurred. The 744-hour result had **359 hours of history**, below the unchanged sufficiency threshold, and the agent abstained. Do not describe this as a completed live revision.
- Separately saved telemetry: four streams with **167.917 hours** of coverage for the 168-hour window; four streams with **359 hours** for 744 hours.

The report's USD figures use the project's pricing model. They are **not Oracle billing measurements or verified cash savings**; Free Tier entitlement and trial credits are not a billing engine in Driftwatch. Boot volumes are also absent from its normal six-resource audit inventory; this assessment queried them independently. Thus, a successful app audit does not certify free-tier compliance.

## 3. Impact on the submission

| Area | Assessment |
|---|---|
| Agent, CLI, and HTTP implementation | No cloud-hosting dependency for sample operation |
| Credential-free judged path | Re-verified; safe primary route |
| Live four-host demo | Currently available; this expiry notice does not establish a lab outage. Retain the offline backup for independent availability risks. |
| Monthly-burst evidence | Preserved locally; cannot be regenerated by creating a new host now |
| Live completed re-check/revision | Still not demonstrated; insufficient genuine wider history |
| Existing packaged evidence | Originals unchanged; hashes checked |
| Lab trial expiry / 21 October teardown assumption | Not changed by the original-tenancy notice; verify the lab's own expiry and balance separately. |

## 4. Recommended backup plan

### Plan A — primary: local, offline sample mode

Run Driftwatch on the personal Mac. Use the existing Windows x86 sample-only clone as a secondary execution platform; no personal OCI credentials, model keys, or employer artifacts cross that boundary.

Today's checks:

- `.venv/bin/python -m pytest -q`: **116 passed**, one existing deprecation warning.
- All three scenarios ran twice with `socket.socket` and `socket.create_connection` replaced by failing functions.
- Every scenario succeeded and repeated deterministically; zero must-not-flag violations.
- Examples 1 and 3: precision, recall, and verdict accuracy **1.0**. Example 2 has no positive ground truth, so those metrics correctly remain **null**, with all five negative controls unflagged.
- Primary example executed the rejected/revised finding path without credentials or network.

Use `SAMPLE_MODE=true .venv/bin/python run.py` for the offline path. Film sample mode as sample mode; label curated/generated scenarios as synthetic. Masked captured live data is historical evidence, not current live telemetry. Do not present today's separate telemetry export as a turnkey replay scenario: it has not been validated as such.

This assessment re-tested the current local tree; it did not repeat the earlier clean-clone/container verification or reinstall dependencies on Windows.

### Plan B — optional: reduce the existing lab, only after approval

If the notice identifies `antworld` and its current limits match the retrieved policy, a minimal useful lab would retain:

- `lab-batch-01`: 1 OCPU / 6 GB, preserving its resource identity and monthly-workload history.
- `lab-sandbox-tmp`: 1 OCPU / 6 GB in the separate compartment, retaining the undeclared-resource case.
- Their two 50 GB boot volumes and the 50 GB orphan: **2 OCPUs / 12 GB / 150 GB** combined storage.

This would require terminating `lab-web-01` and `lab-reports-01` and deleting their corresponding boot volumes **after export and explicit approval**. Retaining the detached boots would leave total storage at 250 GB and would not fix the storage overage. Merely stopping hosts is not a complete remediation.

Before any deletion: confirm names/OCIDs privately, inspect actual workloads and any user data, export needed configuration and data locally, validate those exports, confirm the notice/subscription/limits, then authorize the exact resource list. No VM-disk backup was performed today. A zero-cost file export is the default; don't create paid snapshots or images blindly.

After any approved cleanup, read back instance states, volume totals, quota availability, the selected hosts' accessibility, and fresh telemetry. Re-run the live auditor. Reducing the fleet **after** expiry is a recovery attempt, not a guarantee that Oracle will keep or re-enable it. Do not delete and recreate the two retained hosts merely to make the shape fit; new capacity and their identities/history are valuable.

Idle free compute can separately be reclaimed under Oracle's seven-day CPU/network/memory conditions.[1] The retained workloads are intentionally low duty-cycle; don't manufacture artificial load or alter the audit thresholds to conceal this risk. Keep local execution independent of them.

### Plan C — original tenancy, without rebuilding

If `antworld` becomes unusable, the original `antos` host remains a possible **small live inventory/telemetry check**, subject to account labels, actual access, and limits. Its existing one-OCPU allocation and 97 GB storage fit the documented caps in the checked region. It does not contain the four-host lab's history or declaration relationships; it cannot replace that demo unchanged.

Do not stop/recreate `antos`, attempt a paid shape, or create another free account. Do not wait on scarce new A1 capacity to finish the submission. Sample mode remains the fallback even if both OCI tenancies fail.

## 5. Evidence preserved today

Local, gitignored raw evidence:

- `logs/expiry-20261013/`: current inventory, independent boot/block totals, actual telemetry, live request/report/trace/state, offline results, and separately masked copies.
- `logs/expiry-20261013-evidence.zip`: **44 hashed files** plus the generated manifest; archive CRC and every embedded SHA-256 checked.
- Archive SHA-256: `0d27b4510fb191d7b6f7793afafa26fbc751e619039634b600e1b6d31970502a`.
- The original 5 October checkpoint was copied unchanged. All four embedded evidence hashes and corresponding original files were verified.

This is an **application-evidence backup**, not a complete VM, OS, or user-data backup. Raw files contain personal resource identifiers; keep them private. Masked copies are separate, never replacements for originals. The archive currently has only a verified local copy; off-device preservation remains to be arranged at a user-approved destination.

## 6. Next decisions

1. User clarified the notice concerns `antnynomous`. Keep `antworld` unchanged; separately confirm its own subscription balance/expiry and applicable limits before its free-only transition. Do not provide passwords, card data, or verification codes in chat.
2. Choose Plan A as the guaranteed submission route; keep any live recording supplementary.
3. If shrinking the lab, approve the two named compute removals and their boot-volume removals only after workload/data export is validated.
4. Store the private evidence archive on a second personal storage device/location. Avoid the employer-managed machine for raw data or credentials.
5. Record the resulting decision in `docs/decisions.md`, then correct the lab/README/AGENTS assumptions without rewriting historical entries. No such scope or destructive decision has been applied in this assessment.

## Sources

[1] https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
[2] https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm
[3] https://docs.oracle.com/en-us/iaas/Content/GSG/Tasks/signingup_topic-What_Happens_When_the_Promotion_Expires.htm
[4] https://www.oracle.com/cloud/free/faq
