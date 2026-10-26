# Meterless operational gate record

Checked 26 October 2026, Singapore time. Code is implemented locally; operational acceptance
is blocked. No installation, cloud deployment, tunnel or Nightshift model success is claimed.

## Existing OCI host

The exact BatchMode/strict-host-key SSH probe to existing `zetaris-01` timed out (exit 255).
Read-only OCI rediscovery confirmed RUNNING, `VM.Standard.E5.Flex`, `ap-batam-1`, and that
the SSH hostname matches the current VNIC address. RUNNING does not establish reachability.
Python version, available RAM/disk, user cgroup support, port 18088 and the current Zetaris
baseline could not be checked through SSH. No ingress, route, NSG, host key, VM or service changed.
Raw SSH/inventory diagnostics remain in ignored `logs/meterless-operations/`.

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

## Prepared code is not deployment

The World Model is consumed by Scout/Skeptic; the Nightshift adapter and combined acceptance
harness are locally tested. The remote runner sends only a validated environment/snapshot envelope
over strict SSH stdin, bounds it to 64 KiB, rejects command/path injection, and invokes a fixed
user-scoped systemd command with a 1 GiB MemoryMax. Its real host/cgroup operation is unverified.
No release was transferred, no reverse listener was opened and no bearer was transmitted remotely.

The two independent blockers remain: SSH reachability and the rejected official installer.
The existing no-new-resources/spend constraints and 7 November 00:00 UTC retention checkpoint
are unchanged. README, metadata, deck and narrated demo remain untouched pending real acceptance;
no integration compliance, published release, clean public clone or hackathon submission is claimed.
