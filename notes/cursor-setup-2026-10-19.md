# Cursor setup — 19 October 2026

The builder approved proceeding with Cursor setup after the live event requirement was
explained. This authorises the personal-Mac editor installation, not a paid subscription,
account/terms acceptance, an execution-method selection or pre-window product implementation.

## Verified installation

- Personal Mac: arm64, macOS 27.0.1; no existing Cursor.app found in the two standard app locations.
- Official current download page `https://cursor.com/download` directly lists the Apple Silicon
  3.24 selector used. Its redirect resolved to HTTPS `downloads.cursor.com`.
- Downloaded DMG SHA-256: `0043463fbbb1c0222ff10cfd62a86286791a74c2ede89875719d7113ec0c32bd`.
  This is a local artifact fingerprint, not an independently published vendor checksum.
- Disk-image checksum verification succeeded. Mounted read-only, copied to
  `/Users/ant/Applications/Cursor.app`, then unmounted.
- Deep/strict code-signature verification succeeded before and after copying.
  Gatekeeper accepted the application as **Notarized Developer ID**, with a stapled ticket.
  Signing team identifier: `VDXQ22DGB9`.
- Actual installed bundle and CLI version: **3.24.18**, architecture arm64.
- App was launched without a project/file argument; the main Cursor process is running.
- Editor CLI symlink `/Users/ant/.local/bin/cursor` points to the bundled editor launcher;
  the local bin directory is already on the current PATH. No existing command was overwritten.
- No Homebrew, system-wide application replacement, quarantine removal, Gatekeeper bypass,
  shell-profile edit, paid plan selection or account creation occurred.

## Pending, not claimed complete

GUI automation returned `computer_use backend unavailable` during its read-only capture.
The user needs to complete any Cursor sign-in/onboarding personally. No password, token,
payment or 2FA was supplied through automation, and no account state is claimed verified.
Privacy/account preferences and subscription entitlement have not been inspected or changed.

The Driftwatch repository and all credential files were **not opened** in Cursor. Establish
secret/context exclusions and privacy preferences before opening/indexing the dirty working
tree; ignoring files is not a claim of OS-level access isolation. Do not copy OCI credentials,
platform administrator/registry secrets or model keys into editor chats or rules.

Installation is not evidence of Cursor development. Actual reviewed build-window implementation
or tests performed with Cursor must be retained/disclosed separately. The M1 written plan still
awaits review/execution-method selection and the recorded build-window/eligibility/access gates.
The earlier plan discovery that Cursor was absent is historical; this installation resolves the
application-presence prerequisite only.

## User-reported sign-in and context exclusions

The builder subsequently reported **signed in**. This is user confirmation, not an
independently inspected account/subscription or privacy setting. A fresh app-scoped capture
still failed with the same computer-use backend error; no login tokens or account storage
were read to work around it.

Created repository-root `.cursorignore` before deliberately loading the repository. It excludes
environment secrets (while retaining `.env.example`), private key/credential names, Terraform
state/variable-value files, private directories, working logs and dependency/cache internals.
Sanitized `logs/samples/` and source/fixture files remain available. An isolated Git parser
check verified **17 excluded paths and 7 allowed paths**, without opening any actual secret.
This is pattern verification, not a claim that Cursor UI enforcement has been exercised.

Official ignore reference, directly retrieved on 19 October:
`https://cursor.com/docs/reference/ignore-file`. It explicitly states terminal/MCP tools are
not blocked by `.cursorignore`. Official data-handling reference:
`https://cursor.com/data-use`. Privacy Mode is separate from file exclusions and is not
local-only inference; retention exceptions exist. No undocumented account/privacy flag was
edited. The builder must confirm Privacy Mode in Cursor settings before project loading;
keep terminal/tool approvals in place and do not provide editor tools with cloud credentials.

## Privacy confirmation and workspace opening

The builder subsequently confirmed configuring Privacy Mode after the supplied screenshot
showed Share Data selected and the Privacy Mode alternative. This is user-confirmed setting
state, not independent GUI readback. Root `.cursorignore` was checked before opening.

Opened the actual repository and M1 plan through the installed editor CLI, omitting secret-related
and cloud/model credential environment variables from the launcher. `cursor --status` returned
exit 0 and explicitly reported the implementation-plan window in `open-agent-hackathon`.
No secret file was read, no product command/code change was performed, and no new permission,
paid plan or account operation was requested. Existing Cursor process environment and actual
AI-context enforcement are not attested by this launcher-environment filtering.

Cursor is now available with the plan open for review. Execution-method selection and the
recorded build-window/eligibility/publication gates still apply. Opening the editor and plan
is setup, not claimed implementation evidence.
