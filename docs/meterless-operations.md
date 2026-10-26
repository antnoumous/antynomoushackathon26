# Meterless operational gate record

Checked 26 October 2026, Singapore time. Code is implemented locally; operational acceptance
is blocked. No installation, cloud deployment, tunnel or Nightshift model success is claimed.

## Existing OCI host

The first strict SSH probe timed out. On 26 October the user separately approved permitting
this Mac's current public IPv4 address for SSH. Two independent IP services agreed; signed
OCI discovery matched `zetaris-01` and its current VNIC to the existing SSH configuration.
The change appended exactly one stateful TCP/22 source `/32` rule to its existing security list.
The original ingress and egress rules, tags and display name were preserved, using an ETag
conditional update. An independent auditor-identity GET verified the exact resulting rules.
No route, NSG, VM, host key, service or other port was changed.

A new BatchMode connection with strict host-key checking and multiplexing disabled succeeded
(exit 0). The read-only remote probe measured Python **3.12.3**, 13,123,022,848 bytes available
RAM and 35,209,449,472 bytes free disk, exceeding the planned 2 GiB headroom checks.
Port 18088 was unused and the user systemd manager was active. This is **not** a verified
MemoryMax enforcement or current authenticated Zetaris baseline; those checks remain pending.
The application was not transferred or started. Original timeout captures remain ignored;
private before/request/after snapshots and SSH proof are retained under the existing local
OCI deployment directory, outside expiring scratch and outside the repository.

For rollback, re-read the current list and conditionally remove only the newly added Mac SSH
rule. Do not replace the current list with an old snapshot that might discard later changes.

## Mac installer security gate

The Mac measured arm64 / Apple M6, macOS 27.0.1, 34,359,738,368 bytes RAM and
350,003,879,936 bytes free disk. No Nightshift/Meterless bundle was found in the two standard
Applications locations; this is not an exhaustive disk inventory.

The official Mac page still advertised M5+ insider access through 28 October. Its linked
HTTPS installer resolved on the vendor's own host. Downloaded size matched HEAD:
128,552,779 bytes. SHA-256 artifact fingerprint (not compared with a separately published checksum):
`483888c72f58d055bd711b15c21d5fcb4f70b33b8f7ae86caf12f76fe4887a15`.

The DMG checksum verified. Its sole app was **Nightshift Setup.app**, identifier
`ai.meterless.installer.mac-m5`, arm64. `codesign --verify --deep --strict` returned zero,
but identity inspection showed **Signature=adhoc, TeamIdentifier not set**. Gatekeeper
`spctl --assess --type execute --verbose=4` returned **exit 3: rejected**.
A self-consistent ad-hoc signature is not a verified publisher/notarization result.

Installation stopped at that gate. The app was not copied or launched; no terms, account,
OS permission, model download, paid action or security bypass was accepted. The read-only
DMG mount was detached. Download and verification captures remain in private scratch.
A vendor-trusted/notarized build is required before this approved installation path can continue.

Rechecked on 26 October at 10:16 UTC: a fresh download from the current official M5+ link
had the same byte count and SHA-256 as above. Read-only reassessment again found the same
ad-hoc publisher identity and Gatekeeper exit 3. It was not installed or executed and the
mount was detached. `ns` was absent from PATH and no TCP/8088 listener existed at the check.
The official CLI documentation says Web/M1 editions have no local endpoint; they are not
an API substitute. The checked public GitHub release offered a Windows MSI, not a Mac fix.
No supported trusted Mac replacement was identified in those checked sources.
The Windows edition requires an NVIDIA CUDA GPU; the free Web and M1 editions have no local
endpoint, and the DGX Spark build requires DGX-class hardware. None is an available trusted
runtime here. A vendor support request asking for a Developer-ID-signed/notarized M5+ build
was sent to the vendor on 26 October 2026; no reply had been received at the last check. Diagnostic metadata and captured official guidance
were copied to protected durable local storage; the duplicate DMG remains scratch-only.

## Portal requirements cross-check

On 26 October the signed-in Resources Hub document `Technical Execution Requirements` was read
directly. It defines the Meterless obligation as "at least one Meterless Engine (H-MEM,
Markovian, World Model or Scout Intent) working in a feature, and Meterless Nightshift as your
primary AI provider", and notes a judge may not have Zetaris or Nightshift running, so sample
mode matters. That guide is explicitly "recommended practice, not a rule, unless the Rules say
otherwise"; the binding sentence remains Official Rules §5, "Every submission must integrate
Zetaris and Meterless."

That reading exposed two compatibility defects, fixed here with regression tests: the guide
documents `METERLESS_RUNTIME_TOKEN` and `METERLESS_MODEL=meterless/auto`, while this repository
read only `METERLESS_TOKEN` and refused `auto`. Both names are now accepted (a conflicting pair
is rejected rather than guessed) and both routing modes are selectable. A judge following the
official guide would previously have received a silent rules fallback.

## Prepared code is not deployment

The World Model is consumed by Scout/Skeptic; the Nightshift adapter and combined acceptance
harness are locally tested. The remote runner sends only a validated environment/snapshot envelope
over strict SSH stdin, bounds it to 64 KiB, rejects command/path injection, and invokes a fixed
user-scoped systemd command with a 1 GiB MemoryMax. Its real host/cgroup operation is unverified.
No release was transferred, no reverse listener was opened and no bearer was transmitted remotely.

SSH reachability is restored. The rejected official installer remains a hard blocker; host cgroup enforcement and the authenticated Zetaris baseline are still unverified.
The existing no-new-resources/spend constraints and 7 November 00:00 UTC retention checkpoint
are unchanged. README, metadata, deck and narrated demo remain untouched pending real acceptance;
no integration compliance, published release, clean public clone or hackathon submission is claimed.
