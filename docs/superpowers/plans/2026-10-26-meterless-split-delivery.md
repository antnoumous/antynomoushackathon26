# Meterless Split Deployment and Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a verified Meterless World Model plus real Nightshift inference for Driftwatch using existing OCI infrastructure and the personal Mac, then refresh the submission assets.

**Architecture:** The application/World Model run on `zetaris-01` with existing Zetaris. Nightshift runs on the Mac and is reached through an OCI-loopback-bound SSH reverse tunnel. Two independently testable code milestones precede the operational and delivery gates below.

**Tech Stack:** Python 3.11+, SQLite, existing requests/Pydantic/pytest, Mac Nightshift M5+, OpenSSH, ffmpeg/asciinema and the existing Zetaris adapter. No new cloud compute.

**Spec:** `docs/superpowers/specs/2026-10-26-meterless-split-deployment-design.md`, approved by the user on 26 October 2026.

## Global Constraints

- No new OCI instances, GPUs, disks, snapshots, paid subscriptions, cloud-model purchases or hardware resizing.
- No employer resources or employer data. No credentials on the Windows work machine.
- Preserve the sample run as CPU-only, offline, deterministic and dependency-light.
- Target only existing `zetaris-01`; require authenticated SSH, Python 3.11+, at least 2 GiB available RAM and 2 GiB free disk.
- One audit at a time; 1 GiB application memory limit; keep existing Zetaris resources and A1 workloads unchanged.
- Nightshift setup: one local text model, at most 4 GiB weights and 8 GiB total setup downloads; readiness window 10 minutes after download.
- Runtime and tunnel listeners stay loopback-only; strict host keys; no GatewayPorts change, public API/port opening or LAN hotspot.
- Model calls remain bounded at 60 seconds and remaining audit deadline; run soft/hard limits remain 300/540 seconds.
- Preserve the 7 November 00:00 UTC sponsor-host checkpoint; no retention extension or paid action is authorised.
- No push, submission creation or public sharing is authorised by design approval. Private Drive delivery of revised demo assets follows the user's existing delivery request, with exact-target readback.
- Implementation begins only after the user reviews these plans and selects an execution approach. App terms, OS prompts, permission changes and any networking remedy retain their separate approval gates.

## Review Focus

1. OCI may say RUNNING while SSH is unreachable; no automatic ingress change or alternate paid host is acceptable (Task D1).
2. A vendor installer may be unsigned, replaced or require paid activation; stop rather than bypass security or checkout (Task D2).
3. A reverse forward may bind publicly under server settings despite the requested bind; inspect the actual socket before transmitting any token (Task D3).
4. An archive/deployment may omit committed code or copy credentials unintentionally; verify SHA, an isolated target directory and a strict secret allow-list (Task D3).
5. A new integration invalidates the old video/deck/test claims; only real acceptance plus regenerated assets closes delivery (Tasks D4–D5).

## Read these milestone plans in order

1. [World Model](2026-10-26-meterless-world-model.md): five tasks, ending in an independently runnable offline engine and generated consumption proof.
2. [Nightshift provider](2026-10-26-meterless-nightshift-provider.md): five tasks, ending in a bounded adapter, truthful fallback accounting and a combined acceptance harness.
3. This runbook: operations and submission delivery. No part of a code-only unit test substitutes for the actual installation, SSH tunnel, model calls or combined sponsor proof.

Because the code milestones have distinct interfaces and meaningful independent acceptance, they are
separate plans rather than one oversized feature implementation. Execute them sequentially: agent
context/report files overlap. Do not send parallel writers into `app/loop.py`, `app/agents/writer.py`
or the existing dirty worktree.

## Baseline, deadlines and records

**User approval:** the written specification and these plans were approved on 26 October 2026;
the user selected Native execution with “go ahead”. The two code milestones and the independent
review fix pass are locally verified. Installation has not occurred: the installer-security
gate remains blocked. The user separately approved the narrow Mac `/32` SSH remedy, which
was applied and verified by strict SSH; see `docs/meterless-operations.md`. Remaining host
checks, deployment, real acceptance and final delivery are incomplete.

**Planning baseline actually rerun:** `.venv/bin/python -m pytest -q` returned **259 passed, one
existing Starlette/AnyIO deprecation warning**. Curated evaluation returned **3 scenarios, 0 failing**;
`make_scenario.py --score 10` returned **10 held-out tenancies, 0 failing**. These are baseline checks
of the pre-integration implementation, not Meterless acceptance. Raw command output is in gitignored
`logs/meterless-planning-baseline/`.

**Plan coverage:** the two code milestones and the operational tasks map all spec acceptance gates.
Self-review includes Python-fence parsing, shell-fence syntax checks, named interface consistency,
source/helper inspection, failure-mode tests, secret boundaries and current deployment blockers.

- [ ] Record base SHA, dirty files, actual baseline suite/evaluations and the approved spec before execution.
- [ ] Use an isolated execution branch/worktree via the execution workflow; preserve unrelated work.
- [ ] Keep a task log with executing agent, actual RED/GREEN commands, verified outputs, commit SHA,
  review findings and accepted limitations. Do not attribute Hermes work to Cursor or a child agent.
- [ ] Operational feature-freeze target: **27 October 12:00 UTC / 20:00 SGT**. Use the remaining window
  for evidence, fresh clone, deck, video and form. Final hard deadline: **27 October 23:45 UTC /
  28 October 07:45 SGT**. A missed integration gate remains a compliance gap, not a reason to invent
  output or pay/provision without approval.

### Task D1: Resolve readiness by evidence, without changing infrastructure

**Files:** Create `docs/meterless-operations.md`; raw readiness output stays under gitignored
`logs/meterless-operations/`. Use the existing private SSH config and auditor profile; do not commit
IPs, full resource IDs or configuration secrets.

**Interfaces:** A readiness record with independent booleans for OCI inventory, SSH, supported Python,
RAM/disk headroom, unchanged Zetaris baseline, port availability and enforceable application limit.
Any false gate stops deployment while local code milestones can continue.

- [ ] **Step 1 — repeat the exact SSH check with no password/host-key guessing.**

```bash
ssh -F "$HOME/.oci/zetaris-deployment/ssh_config" \
  -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes \
  zetaris-01 'python3 --version'
```

If it fails, rediscover the current VNIC address using the existing read-only OCI SDK profile and
compare it with `ssh -G` for the alias. Inspect relevant subnet/security-list/NSG ingress and
client-address match read-only if authorised. Do not change ACLs/routes, replace a key, stop a VM,
switch identity to obtain write access or bypass host-key verification. Record the actual failure
and request a narrow remedy if required. The last observed check timed out; do not label it fixed
because inventory still reports RUNNING.

- [ ] **Step 2 — measure headroom and baseline only after SSH works.**

```bash
ssh -F "$HOME/.oci/zetaris-deployment/ssh_config" -o BatchMode=yes \
  -o ConnectTimeout=10 -o StrictHostKeyChecking=yes zetaris-01 \
  'python3 -c '\''import json,platform,shutil; from pathlib import Path; m={x.split(":")[0]:int(x.split()[1])*1024 for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")}; print(json.dumps({"python":platform.python_version(),"available_ram_bytes":m["MemAvailable"],"disk_free_bytes":shutil.disk_usage(Path.home()).free}))'\'''
```

Parse the JSON, require Python >=3.11 and RAM/disk >=2*1024**3, and preserve the actual values.
Run the existing read-only Zetaris verification from its operations runbook, not an invented SQL
probe or administrator mutation. Confirm 18088 is not already in use. Identify a working user-scoped
cgroup mechanism for the 1 GiB audit limit without applying it to the Zetaris containers. If the limit
cannot be enforced without extra privilege/package changes, report that gate as blocked.

- [ ] **Step 3 — document the gate result and leave cloud allocation unchanged.** Use only actual
readbacks. No extension of the existing host checkpoint, no GPU quote assumed and no claim of zero
existing billing. Commit a sanitised operational note if it changes; raw diagnostics remain private.

### Task D2: Verify the free Mac app and one local text model

**Files:** Downloads/probes under `$TMPDIR/meterless-install/`; installed app under `~/Applications/`.
Only sanitised actual installation observations enter `docs/meterless-operations.md`.

**Interfaces:** Verified app path/version/signature/Gatekeeper result, recorded actual model identity
and weight size, no-charge activation, local-only compute and authenticated runtime readiness.

- [ ] **Step 1 — preflight and discover the current official link.** At execution time load
`computer-use` and its `references/macos-app-installation.md`. Inspect existing installations and
processes without overwriting them. Measure Mac RAM/disk and read the current official Mac page.
Use the actual advertised M5+ insider link, follow redirects with HEAD and record final HTTPS URL,
MIME type and byte count. If the no-charge offer is absent/expired, stop for the user; do not checkout.

- [ ] **Step 2 — download with a byte cap, fingerprint and inspect without executing.**
The following planned downloader accepts only a URL already discovered from the official page:

```python
from pathlib import Path
import hashlib, urllib.request

def download_bounded(url: str, destination: Path, max_bytes: int) -> tuple[int, str]:
    if destination.exists() or not url.startswith("https://"):
        raise ValueError("refuse existing destination or non-HTTPS download")
    total = 0
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=30) as response, destination.open("xb") as output:
            if not response.url.startswith("https://"):
                raise ValueError("download redirected away from HTTPS")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("setup download budget exceeded")
                digest.update(chunk)
                output.write(chunk)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return total, digest.hexdigest()
```

Use the official destination host or a vendor-justified redirect only. Save the actual byte count
and SHA-256; call it a fingerprint unless compared with a separately published vendor checksum.
Installer + later model downloads must remain within the 8 GiB total; the model alone within 4 GiB.
Mount read-only, discover the actual app bundle rather than guessing its name, then verify:

```bash
hdiutil verify "$DMG"
hdiutil attach -readonly -nobrowse -mountpoint "$MOUNT" "$DMG"
codesign --verify --deep --strict "$BUNDLE"
spctl --assess --type execute --verbose=4 "$BUNDLE"
codesign -dv --verbose=4 "$BUNDLE"
```

`DMG`, `MOUNT` and `BUNDLE` are the concrete discovered scratch paths. Stop on invalid signature,
unaccepted Gatekeeper result or unexplained provenance; do not strip quarantine, disable Gatekeeper
or ad-hoc sign. Ask the user if this requires a changed security decision.

- [ ] **Step 3 — non-clobbering user-local installation and user-owned onboarding.**

```bash
test ! -e "$DEST" && test ! -L "$DEST"
mkdir -p "$HOME/Applications"
ditto "$BUNDLE" "$DEST"
codesign --verify --deep --strict "$DEST"
spctl --assess --type execute --verbose=2 "$DEST"
hdiutil detach "$MOUNT"
open -g -a "$DEST"
```

Set DEST from the inspected app's real name. Run stop-on-error, not a pasted sequence that continues
after failure. Record the installed Info.plist version and process state. User handles terms,
activation and OS permission prompts; launch success is not proof of account/model readiness.
If GUI tooling is unavailable, ask the user for the specific onboarding actions rather than silently
repairing Hermes/desktop permissions or declaring setup successful.

- [ ] **Step 4 — select only one fitting local text model.** Inspect the actual catalog, model
licence, weight bytes and available memory before Download/Activate. Prefer a 2B–3B text model only
if it meets the approved size/memory gates and appears in this edition. No fleet, media packages,
cloud keys, cloud relay, overnight schedules or LAN hotspot. Record actual bytes, not estimates
presented as measurements. If the UI auto-selects extra downloads or cannot enforce the budget,
stop before authorising them.

- [ ] **Step 5 — runtime readiness and all used structured schemas.** Read the protected runtime
token in-process from the discovered state path without displaying it. Use the implemented provider
adapter for authenticated `/v1/models` and the three schemas, requiring discovered `meterless/local`.
Bound readiness/prewarm at 10 minutes after download and each request at the planned transport
budget; no repeated unbounded polling. A plain ping, web cockpit or `/healthz` alone is insufficient.
Keep results classified as Mac-local runtime proof until the OCI tunnel is tested.

### Task D3: Safe release transfer, reverse tunnel and secret-in-memory runner

**Files:** Create `scripts/run_meterless_remote.py`, `tests/test_meterless_remote.py` and extend
`scripts/verify_meterless_sponsors.py` with `--stdin-env` support. Local secret payloads and remote
raw run directories are untracked/private. Deployment is an isolated directory under
`~/driftwatch-meterless/<commit-sha>/`, never the existing Zetaris deployment directory.

**Interfaces:**

```python
ALLOWED_ENV = {
    "LLM_PROVIDER", "METERLESS_BASE_URL", "METERLESS_TOKEN", "METERLESS_MODEL",
    "ZETARIS_REST_URL", "ZETARIS_API_KEY", "ZETARIS_ORG_ID",
}

def validate_runtime_env(payload: dict) -> dict[str, str]: ...
def run_remote_acceptance(*, ssh_config: Path, release_dir: str,
                          runtime_env: dict[str, str], base_settings: dict,
                          variant_settings: dict, output_dir: str,
                          run_subprocess=subprocess.run) -> int: ...
```

The runner sends a strictly validated JSON object over SSH stdin; it never places token values in
argv or prints the payload. The remote acceptance CLI reads `--stdin-env`, validates the same
allow-list and builds its explicit per-run env without mutating a global .env or dumping os.environ.
It accepts only environment strings, not commands/import paths. Reuse the existing public snapshot
settings validation for the two selection objects. Use the dedicated read-only Zetaris runtime key,
never the administrator key. No OCI credentials or general LLM/cloud keys are copied.

- [ ] **Step 1 — RED→GREEN for the runner before remote execution.**

```python
def test_remote_runner_keeps_tokens_out_of_argv_and_output(tmp_path, capsys):
    from scripts.run_meterless_remote import run_remote_acceptance
    calls = []
    def process(argv, **kwargs):
        calls.append((argv, kwargs))
        return type("Result", (), {"returncode": 0})()
    rc = run_remote_acceptance(ssh_config=tmp_path / "ssh-config",
        release_dir="driftwatch-meterless/test-release",
        runtime_env={"LLM_PROVIDER":"meterless", "METERLESS_TOKEN":"unit-secret",
            "METERLESS_BASE_URL":"http://127.0.0.1:18088/v1",
            "METERLESS_MODEL":"meterless/local", "ZETARIS_API_KEY":"unit-zetaris",
            "ZETARIS_ORG_ID":"unit-org", "ZETARIS_REST_URL":"http://127.0.0.1:9000/api/v1.0"},
        base_settings={"snapshot_id":"base", "policy_object":"S.base",
            "manifest_object":"S.manifest", "expected_sha256":"a"*64},
        variant_settings={"snapshot_id":"variant", "policy_object":"S.variant",
            "manifest_object":"S.manifest", "expected_sha256":"b"*64},
        output_dir="logs/acceptance-unit", run_subprocess=process)
    assert rc == 0
    assert calls
    assert "unit-secret" not in repr(calls[0][0])
    assert "unit-secret" in calls[0][1]["input"]
    assert "unit-secret" not in capsys.readouterr().out
```

Add separate failing tests rejecting `OCI_CONFIG_FILE`, unknown env keys, non-string values, command
characters/path traversal in release/output paths, missing dedicated tokens and forbidden snapshot
settings. The implementation uses the fixed SSH alias `zetaris-01`, shell-quotes only validated
paths, invokes one fixed acceptance entry point and forwards no arbitrary remote command. Test a
nonzero SSH result without falsely declaring upload/acceptance success. Test size bounds before
parsing stdin; maximum payload is 64 KiB. Implement `--stdin-env` with the same validated fields and
no secret echo. Run targeted/full tests and commit these helpers before release export.

- [ ] **Step 2 — transfer only a reviewed committed tree and verify its identity.** Run the existing
publish-content/OCID guard on the committed release. Use `git archive` of that exact SHA and hash the
archive. Transfer to a new remote directory, verify the remote hash before extraction and refuse a
pre-existing destination. `.env`, SSH/OCI keys, private run logs, model weights and uncommitted work
must not be in the archive. Check a known implementation source hash after extraction; an exit-zero
copy of the wrong/stale tree is not deployment. Remote package installation is only the existing
requirements into a new venv using the verified Python 3.11+; no apt upgrade or Zetaris changes.

- [ ] **Step 3 — start a separately tracked reverse tunnel.**

```bash
ssh -F "$HOME/.oci/zetaris-deployment/ssh_config" -N -T \
  -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -R 127.0.0.1:18088:127.0.0.1:8088 zetaris-01
```

Run it as a tracked background process, not detached `ssh -f`, and preserve its exact process handle.
Read the remote listening socket and require 127.0.0.1:18088 only; reject wildcard/IPv6-any binds.
Do not send a token before this check. Verify Mac 8088 also remains loopback-only. If forwarding is
forbidden or a listener is occupied, stop this task's tunnel and ask for a specific remedy; do not
change SSHD/NSG/GatewayPorts or kill another service.

- [ ] **Step 4 — enforce the audit limit and run over stdin.** Use the headroom-verified user-scoped
cgroup to cap this audit and its worker processes at 1 GiB, with one audit at a time; prove the limit
from the process/cgroup readback. Do not claim a limit from a command that failed or switch to sudo.
Read the Mac runtime token and existing dedicated Zetaris key into memory, build only ALLOWED_ENV,
set the model endpoint to the OCI loopback tunnel and the Zetaris endpoint to its inspected local
service address. The runner sends credentials over stdin into the one remote process. Keep raw
outputs private and do not copy the complete Mac .env. The loopback tunnel needs no LAN hotspot.

### Task D4: Real combined acceptance and reproducible evidence

**Files:** Raw outputs under gitignored `logs/meterless-acceptance-<run>/`; sanitised generated
copies under `output_examples/meterless_acceptance/`; update `docs/meterless-operations.md` only
with the observed run, actual source/provider outcomes and constraints.

**Interfaces:** A generated acceptance result links the exact release SHA, world database/context
IDs, policy snapshot digests, model/routing outcomes and report/trace paths; it is not a manually
written success JSON. Compare unaffected resource/class/verdict/impact/rule semantics, not exact
model-written prose: a different wording alone is not a changed audit result. The existing figure
guard remains mandatory.

- [ ] **Step 1 — run the implemented production-adapter acceptance harness.** Supply the existing
immutable base/no-R-1 snapshot selections, read-only policy credentials and `meterless/local`.
Use a new output directory; never overwrite the 22 October Zetaris proof or the original media.
The actual command's nonzero exit is failure even if some artifact exists.
- [ ] **Step 2 — inspect the semantic proof, not only the boolean.** Require actual World Model
consumption by Scout/Skeptic; authenticated Zetaris-backed policy on both sides with matching digests;
a Nightshift success for every used schema; zero provider fallbacks; exact expected R-1 finding
removal; other semantic claim/verdict/impact results unchanged; no dangling evidence or invented
figures. Candidate/evidence IDs may differ. Both windows and coverage remain traceable. Label the
run **hybrid: synthetic inventory/IaC/telemetry, live Zetaris policy and live Nightshift inference**.
- [ ] **Step 3 — exercise failure explicitly without mutating vendor state.** Disconnect only this
task's tunnel and run a bounded provider check: require offline/fallback reporting and failed sponsor
acceptance, not a reused prior success. Reconnect and obtain new successful evidence. Perform invalid-
token and malformed-response checks in unit tests or a private local probe, never by publishing a
real token or changing the actual runtime's authentication settings.
- [ ] **Step 4 — generate export copies and checksum manifests.** Run the established masking tool
on copies, keep raw originals unchanged, and check that published output cannot contain full OCIDs,
real non-loopback private/public host addresses, credential headers or prompts with secrets.
Documented loopback endpoint examples are allowed; an IP scan must not reject those as a leak.
Export machine-readable integration
status and generated references through a committed generator. Hash the exact artifacts and verify
the exported JSON parses. Re-run full suite, curated/held-out evaluations and CLI/HTTP offline checks.
- [ ] **Step 5 — stop only temporary resources on completion/abort.** Close this tunnel/process handle,
stop this task's audit, preserve evidence and report any remaining app process. Do not stop Zetaris,
terminate OCI resources, delete the world store or silently uninstall Nightshift. No retention change.

### Task D5: Refresh claims, media, published tree and submission handoff

**Files:** README.md, metadata.json, docs/demo-storyboard.md, docs/decisions.md,
docs/demo/narration/manifest.json, scripts/demo_session.sh, scripts/demo_show_trace.py,
new generated demo/deck assets and runtime evidence. Existing dirty text/media must be merged,
not replaced wholesale; read the current files before editing. Load the relevant powerpoint,
submission-packaging and humanizer skills when executing this task.

- [ ] **Step 1 — update attribution from verified code.** State the implemented three-service subset,
real consumers, actual local model and Nightshift route, synthetic-vs-live data, provider fallback,
limits and source licences. Only set mounted/verified fields that the recorded acceptance proves.
The old 'Meterless not integrated' text must be revised consistently, not just in one footer.
Do not claim NVIDIA/Nemotron, full engine conformance or a live customer-tenancy audit.
- [ ] **Step 2 — record genuine new footage.** Add the real combined sponsor acceptance/consumption
view to the demo script, record it from the reviewed tree and preserve the original cast/video.
Do not edit a cast to fabricate a missing integration. Replace the stale 259-test line with actual
new captured results or avoid a numeric count. Name the chosen track and declared baseline.
- [ ] **Step 3 — regenerate narration and deck with the already approved voice.** Revise the spoken
text only after proof exists; preserve the user's approved synthetic voice and pace. Use the stored
narration/assembly workflow, check the **rendered** scene boundaries, extend genuine holds and keep
the final video within 1–4 minutes. Remove the unintegrated-Meterless disclaimer only if both gates
passed; retain true remaining limits. Update deck visuals, sponsor roles and test/evidence claims.
Full-decode audio/video, check levels/ending and inspect representative frames for text and secrets.
- [ ] **Step 4 — track the intended release, review and ask before publication.** The repo ignores
new MP4 files. Choose one explicit release path and a narrow ignore exception if embedding video in
Git, or document the approved Drive delivery instead; do not globally unignore raw media. Commit
reviewed changes only. A fresh independent reviewer checks code, security and each published claim;
reproduce/fix findings before calling it ready. Request explicit push approval, then push only the
approved branch/commit. A local commit is not published.
- [ ] **Step 5 — verify the public clone and private delivery.** After approved push, clone from the
actual public remote into scratch, verify the expected SHA/content marker, create a new venv,
install requirements, run the full suite and literal documented credential-free CLI/HTTP commands.
Exercise them with sockets blocked and provider secrets absent. Parse the actual returned report;
do not rely only on exit zero. Re-check regenerated evidence and committed-file secret scanning.
Upload revised video/audio/deck to the user's Drive only within the approved private delivery scope,
read back exact IDs, compare sizes and checksums, inspect permissions and return verified links.
Do not create the HackOS submission or public sharing permissions without explicit approval.

## Coverage and execution handoff

The code plans cover identity/storage/recovery/context/consumption/offline gates and the bounded
provider/structured-output/fallback gates. D1–D3 cover actual host/app/tunnel/secret boundaries; D4
covers real combined execution; D5 covers attribution/media/publishing/fresh-clone/delivery.

A final report must separate: implemented and locally tested; actually installed; OCI-deployed;
real provider/combined acceptance passed; published and clean-clone-verified; submission uploaded.
Each state needs its own evidence. Missing a prerequisite remains a named blocker, not a synthetic
result or a declaration of overall success.

**Recommended execution method:** Native in this session, then one fresh independent whole-branch
review. The code milestones share agent/context/report boundaries, so sequential implementation
avoids merge contention; native execution also minimises repeated context cost in the short window.
Subagent-driven remains available if the user prefers per-task independent implementation/review.
Wait for the user's plan review and execution-method selection before starting either code plan or
performing app installation/deployment.
