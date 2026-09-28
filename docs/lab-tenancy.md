# Lab tenancy checklist — spec §5.2, operationalised

**Deadline: create everything by Sun 29 Sep 2026.** The false-positive workload is a *month-end*
cron. Its next firing is **Wed 1 Oct 02:00**; the one after that is 1 Nov — after submissions
close. If the tenancy (and the cron) are not running by 30 Sep, the canonical
re-check → revision story **cannot exist in live metric history during the build window**
(15–20 Oct), and the live demo shrinks to idle + orphan findings only.

Why 1 Oct works for the whole window: a run on any day 15–20 Oct looks back 7 days first
(burst outside → "idle" → Skeptic sees the `month-end` tag → re-check at 31 days → burst inside,
peak ≥ 20% → verdict revised to duty-cycled). OCI Monitoring keeps 5-minute-resolution data for
30 days, so the 1 Oct burst is still retrievable on 20 Oct. Everything lines up **only** if the
burst fires on 1 Oct.

Cost: **$0/month inside the free envelope** for 4 instances; the two orphans cost ≈ $8.6/month
(50 GB volume ≈ $1.27 + reserved IP ≈ $7.30). Nothing else is needed; the plan's budget decision
("spend nothing more until the 17 Oct checkpoint") stands.

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
    `[DRIFTWATCH]` profile (home region `ap-batam-1` — everything lives in the home region).
- [ ] Copy `.env.example` → `.env` and fill the OCI block:
    `OCI_CONFIG_FILE=~/.oci/config`, `OCI_PROFILE=DRIFTWATCH`, `OCI_REGION=...`,
    `OCI_COMPARTMENT_ID=<lab-prod OCID>`. **`.env` stays gitignored; never commit it.**
- [ ] Smoke-test from the venv once Step 4 exists (it does as of this commit):
    `SAMPLE_MODE=false .venv/bin/python run.py` should return real records — see §6.

## 2. Compartments and network

- [ ] `lab-prod` compartment (everything except the sandbox lives here).
- [ ] `lab-test` compartment (the CLI-created sandbox) — so "wrong compartment" is findable.
- [ ] One VCN + public subnet in `lab-prod` (Oracle's "VCN with Internet Connectivity" wizard
      is fine). Reserve the orphan public IP **unattached** in `lab-prod`.

## 3. The four instances

Free envelope: 2× `VM.Standard.E2.1.Micro` (AMD, reliable) + 2× `VM.Standard.A1.Flex`
(1 OCPU / 6 GB each; capacity is often unavailable — retry across ADs/days, and **do not block
on ARM**: if A1 capacity never appears, run the demo with the 2 Micros + orphans and record the
limitation honestly). Ubuntu 22.04/24.04 platform images ship with Oracle Cloud Agent running,
which is what emits `CpuUtilization`.

| Instance | Where created | Freeform tags | Workload |
|---|---|---|---|
| `lab-web-01` | Terraform, `lab-prod` | `owner=ant`, `env=prod`, `iac_address=oci_core_instance.lab_web_01` | steady 40–60% CPU (§5 script) — must **not** be flagged |
| `lab-batch-01` | Terraform, `lab-prod` | `role=batch`, `schedule=month-end`, `env=prod`, `iac_address=oci_core_instance.lab_batch_01` | month-end cron (§5) — the false positive the agent catches |
| `lab-reports-01` | Terraform, `lab-prod` | `env=prod`, `iac_address=oci_core_instance.lab_reports_01` | nothing — clean idle, unambiguous waste |
| `lab-sandbox-tmp` | **OCI CLI by hand**, `lab-test` | *none* | nothing — idle **and** undeclared → unattributed |

The `schedule=month-end` tag is load-bearing: the Skeptic scans evidence payloads (which carry
`resource.tags`) for schedule signals, and that tag is what triggers the widened re-check.
The `iac_address` tags are what make the three Terraform instances *declared* and the CLI
sandbox *undeclared* — real drift, not staged.

## 4. The two orphans

- [ ] `vol-orphan-50g`: 50 GB block volume in `lab-prod`, created but **never attached** (R-1).
- [ ] `ip-orphan`: reserved public IP, **never assigned** (R-2).

## 5. Workloads (install on day one — the cron only counts if it fires while the tag exists)

`lab-batch-01` — `/usr/local/bin/month-end-batch.sh` (root cron: `0 2 1 * * /usr/local/bin/month-end-batch.sh`):

```bash
#!/bin/bash
# Simulated month-end batch: pegs CPU for ~2 hours, once a month, on the 1st at 02:00.
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

## 6. Terraform side + the live IaC capture

- [ ] Terraform manages: VCN/subnet, the three `lab-prod` instances, the volume, the IP —
      in a repo of its own (or a directory of this one that is **not** committed with state).
- [ ] The CLI sandbox is created by hand and appears in **no** `.tf` file.
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
| **by Sun 29 Sep** | Everything above exists; cron installed; metrics verified flowing |
| **Wed 1 Oct 02:00** | First month-end burst fires — do nothing, just let it |
| 2 Oct | Run `SAMPLE_MODE=false .venv/bin/python run.py --scenario data/scenarios/lab_live` once; confirm the burst is *not yet* in the 7-day window and the re-check finds it in 31 days |
| **17 Oct checkpoint** | Go/no-go on enabling the live path in the submission |
| 18–19 Oct | Film the demo against the live tenancy (masked), or against fixtures if the checkpoint says no |
