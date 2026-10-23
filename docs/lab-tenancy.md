# Lab tenancy — operational checklist and verified checkpoints

**Current state (5 October 2026):** the personal trial lab was provisioned on 28 September
via the OCI API. Four A1.Flex instances and two orphans are present. The batch host uses UTC:
`0 2 1 * *` fired on **1 October 02:00 UTC / 10:00 SGT**, for approximately two hours.
The 1 October evening check verified that burst using real Monitoring data.

The **5 October 00:00 SGT** audit succeeded with live inventory and telemetry, file-backed
declarations and policy, no degraded sources, and **156.75/168 hours (93.3%)** telemetry
coverage. Its findings were mixed: batch and sandbox were R-4 (low mean, high peak), reports
was rejected because its declaration says **"intentionally running"**, web was unflagged,
and both orphans plus sandbox's unattributed finding were accepted. **No re-check or revision
occurred**: the month-end burst was still inside the initial seven-day window.

The next observation is **9 October 00:00 SGT (8 October 16:00 UTC)**, after the scheduled
burst leaves the 168-hour window on **8 October 12:00 SGT**. Other CPU peaks may still affect
which rule fires. If batch is proposed under R-3, its schedule evidence should cause the
Skeptic to request 744 hours. That wider history is **not yet sufficient**: 80% requires
595.2 hours; from the earliest saved datapoint (28 September 03:15 UTC), even continuous
reporting cannot reach that span before **23 October 06:27 SGT**, after submissions close.
Do not promise a successful live revision during the build window. A traced re-investigation
followed by honest insufficient-history abstention is useful evidence; the bundled scenarios
remain the credential-free demonstration of a completed revision.

Keep the original 5 October evidence unchanged. A checksum-verified, gitignored snapshot is
`logs/checkpoint-20261005-originals.zip`; it contains the saved report, metrics, trace and cron
report plus a generated SHA-256 manifest. Raw artifacts stay local. Mask separate copies before
publishing or filming. **Do not change rules, declarations or workloads to force a demo verdict.**

Budget: earlier free-envelope and orphan-price estimates were planning assumptions, not a
verified bill. The trial lab uses the entrant's credit; no additional provisioning is planned.
Keep the **21 October teardown** plan and verify credit expiry/billing separately.

> **Employer rule, unchanged:** this is your *personal* tenancy only. Nothing from Oracle's
> tenancies, customers, or work accounts — not names, not tags, not OCIDs, not screenshots.

---

## 1. Prerequisites (one evening)

- [ ] API user + group for the auditor. Policy in the **tenancy root** (metrics live there):

  ```hcl
  # Terraform: oci_identity_groups.driftwatch, oci_identity_policies.driftwatch
  allow group DriftwatchReaders to read instance-family    in tenancy
  allow group DriftwatchReaders to read volume-family      in tenancy
  allow group DriftwatchReaders to read virtual-network-family in tenancy
  allow group DriftwatchReaders to read metrics            in tenancy
  ```

  (Read-only everywhere — the agent never writes to the tenancy.)
- [ ] API key uploaded for that user; `~/.oci/config` written on this Mac with a
    `[DRIFTWATCH2]` read-only profile for the trial lab (home region `ap-batam-1`).
- [ ] Copy `.env.example` → `.env` and fill the OCI block:
    `OCI_CONFIG_FILE=~/.oci/config`, `OCI_PROFILE=DRIFTWATCH2`, `OCI_REGION=ap-batam-1`,
    `OCI_COMPARTMENT_ID=<lab-prod OCID>`. **`.env` stays gitignored; never commit it.**
- [ ] Smoke-test from the venv once Step 4 exists (it does as of this commit):
    `SAMPLE_MODE=false .venv/bin/python run.py` should return real records — see §6.

## 2. Compartments and network

- [ ] `lab-prod` compartment (everything except the sandbox lives here).
- [ ] `lab-test` compartment (the CLI-created sandbox) — so "wrong compartment" is findable.
- [ ] One VCN + public subnet in `lab-prod` (Oracle's "VCN with Internet Connectivity" wizard
      is fine). Reserve the orphan public IP **unattached** in `lab-prod`.

## 3. The four instances

Actual trial lab: 4× `VM.Standard.A1.Flex`, 1 OCPU / 6 GB each, created through the API.
The earlier two-Micro/two-A1 plan was not used. Oracle Cloud Agent emits `CpuUtilization`;
live Monitoring confirmed all four streams. Tags and file-backed declarations express lab
intent; they are not proof that Terraform applied these resources.

| Instance | Where created | Freeform tags | Workload |
|---|---|---|---|
| `lab-web-01` | API, `lab-prod`; declared | `owner=ant`, `env=prod`, `iac_address=oci_core_instance.lab_web_01` | steady ~50% CPU — unflagged on 5 October |
| `lab-batch-01` | API, `lab-prod`; declared | `role=batch`, `schedule=month-end`, `env=prod`, `iac_address=oci_core_instance.lab_batch_01` | month-end cron — R-4 on 5 October, no re-check |
| `lab-reports-01` | API, `lab-prod`; declared | `env=prod`, `iac_address=oci_core_instance.lab_reports_01` | low average CPU; declared intentionally running — critic rejected waste finding |
| `lab-sandbox-tmp` | API, `lab-test`; undeclared | *none* | low average CPU; real peaks — R-4 plus R-5 on 5 October |

The `schedule=month-end` tag is load-bearing: the Skeptic scans evidence payloads (which carry
`resource.tags`) for schedule signals, and that tag is what triggers the widened re-check.
The file-backed `iac.json` lists the three declared hosts; the sandbox is absent. This is a
controlled personal lab, not a discovered production incident or a verified Terraform deployment.

## 4. The two orphans

- [ ] `vol-orphan-50g`: 50 GB block volume in `lab-prod`, created but **never attached** (R-1).
- [ ] `ip-orphan`: reserved public IP, **never assigned** (R-2).

## 5. Workloads (install on day one — the cron only counts if it fires while the tag exists)

`lab-batch-01` — `/usr/local/bin/month-end-batch.sh` (UTC host; `/etc/cron.d/month-end-batch`
contains `0 2 1 * * root /usr/local/bin/month-end-batch.sh`):

```bash
#!/bin/bash
# Simulated month-end batch: ~2 hours, on the 1st at 02:00 UTC / 10:00 SGT.
end=$((SECONDS+7200))
while [ $SECONDS -lt $end ]; do :; done
```

`lab-web-01` — steady ~50% duty cycle (`@reboot` systemd unit or cron):

```bash
#!/bin/bash
# Calibrated load: 0.5s busy / 0.5s idle ≈ 50% of the shape's OCPUs.
while true; do
  t=$((SECONDS+1)); while [ $SECONDS -lt $((t)) ] && [ $((SECONDS%1)) -eq 0 ]; do :; done
  sleep 0.5
done
```

(Simpler and good enough: `while true; do timeout 0.5s bash -c 'while :; do :; done'; sleep 0.5; done`.
Verify in the Monitoring console that `CpuUtilization` settles at 40–60% for `lab-web-01`,
<5% for the idle pair, and adjust the duty ratio if it doesn't — the rule thresholds are
mean <5% and peak boundaries at 20%.)

**Verify within a day of launch:** Console → Monitoring → the instance → `CpuUtilization`
has data points. No points = Cloud Agent not running = the whole telemetry story is dead;
fix it before anything else.

**If you miss 1 Oct** (provisioning slips): install the same cron anyway, and run the job once
by hand on a date 8–30 days before your demo run (`/usr/local/bin/month-end-batch.sh &`). The
tag and the job are real; one hand-triggered execution of a real monthly job is honest history,
and the report says what the evidence says either way. Note it in `docs/decisions.md` if used.

## 6. File-backed declarations and the live capture

- [x] Lab resources were created through the OCI API, not a verified Terraform apply.
- [x] `iac.json` supplies lab declarations; its Terraform-shaped addresses and paths are
      labels, not evidence of files or commit history (`last_commit` is `not-a-git-repo`).
- [x] The sandbox is absent from that declaration set.
- [ ] For the live run, the IaC source is file-backed by design (it reads declarations, not
      Terraform Cloud): maintain `data/scenarios/lab_live/iac.json` listing the three declared
      instances (same shape as `example_1/iac.json`), and run the auditor with
      `--scenario data/scenarios/lab_live`. The directory also needs `policy.json` (copy the five
      rules verbatim from `example_1`), and `inventory.json`/`telemetry.json` exist only as
      **fallback** fixtures — for the live demo leave them as copies of the *masked* captured
      output (see §7) so a mid-demo source failure degrades to something true, not empty.

## 7. Before anything is committed or filmed

- [ ] Run `.venv/bin/python scripts/mask_ocids.py <file>` on **every** artifact that leaves the
      machine — captured JSON, logs for the repo, video frames showing the console. The test
      suite scans every tracked file and fails on an unmasked OCID, but the video is on you.
- [ ] `.env`, `~/.oci/config`, the private key and Terraform state are never committed
      (`tests/test_mask_ocids.py` + `.gitignore` guard the repo; the video guard is manual).
- [ ] No screenshot, terminal scrollback or clipboard in the video shows the employer —
      this tenancy only, its real name is fine, real OCIDs are not.

## 8. Timeline

| Date | Action |
|---|---|
| **28 Sep** | Lab provisioned; cron installed; metrics verified flowing |
| **1 Oct 02:00–04:00 UTC / 10:00–12:00 SGT** | Scheduled burst; verified by the 22:00 SGT check |
| **5 Oct 00:00 SGT** | Live audit successful, 93.3% coverage; mixed findings, no re-check/revision |
| **9 Oct 00:00 SGT** | Read-only follow-up after burst ages out; inspect re-check and insufficient-history behavior, without assuming a verdict |
| **Before 15 Oct** | Confirm HackOS track/partner requirements and review workshop recordings |
| **17 Oct checkpoint** | Assess live evidence and disclose limits; do not assume 744-hour coverage clears in time |
| 18–19 Oct | Film the demo against the live tenancy (masked), or against fixtures if the checkpoint says no |
| **21 Oct** | Planned teardown of the personal trial lab |
