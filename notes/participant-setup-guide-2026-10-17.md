# Organiser participant setup guide — change to access advice

> **Subsequent user decision:** [OCI deployment approval](zetaris-oci-deployment.md)
> supersedes the personal-Mac installation recommendation below. The builder approved
> deployment in `antworld` and supplied subscription-expiry evidence for 26 November.
> Vendor access/entitlement and an actual deployment remain outstanding; approval is
> recorded and should not be requested again as if still pending.

Assessed **17 October 2026 (SGT)**. Source: **Open Agent Hackathon 2026: Participant Setup Guide**, document header **Last updated 16 October 2026**. User supplied the Google Doc and subsequently approved the previously proposed bounded, read-only onboarding check.

Source URL: https://docs.google.com/document/d/1_d3osxbXZRpp4Ln80w6Obc5xx06SmkIMrgp6BOj0Ofc/edit?tab=t.0

Retrieved directly through the document's unauthenticated text export. Export: **35,807 bytes**, SHA-256 `0f493330fdf2b9b2a331217576f1711fa6387e3a478167603001ac20f7a00b67`. Raw material remains in local scratch, not the public repository. Credential-related lines were suppressed from displayed extraction. The document's stated revision date is not independently authenticated version history.

## Correction to the earlier recommendation

The earlier [documentation assessment](zetaris-docs-assessment-2026-10-17.md) preferred a supplied/shared instance based on the vendor repository and sponsor overview. **This newly supplied organiser guide directs local self-installation; it does not distribute a shared participant instance URL.** It explicitly says Zetaris and Meterless must be running on the participant's machine for eligibility. Its hardware section nevertheless offers deployment into the participant's own AWS account when the laptop cannot manage Zetaris. Those statements need an organiser interpretation if we seek any hosted/shared exception.

Therefore, **do not wait for a shared-instance allocation as the only next step, and do not assume shared access satisfies the new local-install wording.** Recommended next decision is whether to approve local Docker/Zetaris installation on the personal Mac, after account/entitlement and install prerequisites are reviewed. AWS is not approved and remains a separately billed alternative. The employer Windows machine and OCI audit lab are not installation targets under the current scope.

The guide is organiser setup/eligibility guidance, with unfinished organiser placeholders; it is not a replacement published rulebook. Keep differences from the 17 October retrieved event rules explicit rather than silently treating every tutorial instruction as a binding rule.

## Where the access details now come from

Guide Data §1.1:

1. User registers/signs in at **https://cloud.enterprise.zetaris.com/register**.
2. User opens **https://cloud.enterprise.zetaris.com/dashboard/download** (Run locally), downloads `zetaris-platform.zip`, and obtains the registry sign-in procedure.
3. With a separately approved local install running, Data §1.9 supplies these addresses:

| Interface | Guide's local address |
|---|---|
| UI / SQL Editor | `http://localhost:3000` |
| Direct REST | `http://localhost:8888/api/v1.0` |
| JDBC | `jdbc:zetaris:lightning@localhost:10000` |

These are **local defaults**, not services already running or remote endpoints. The administrator account is chosen privately before bootstrap. Confirm actual organisation ID in the running service rather than applying `1` to unrelated/shared accounts. The matching JDBC driver comes from the platform download; obtain its actual path rather than searching or guessing. REST is the guide's simplest application route; the earlier supplied prompt independently requested a JDBC onboarding check.

If the download is unavailable, the guide directs participants to **Zetaris support or Help Zetaris on HackOS**. Its help section links the HackOS Help desk at https://hackathon.genai.works/messages . No signup, account acceptance, credential retrieval or download from the account portal was performed here.

## Other consequential changes and remaining ambiguity

- **Nemotron is explicit:** Power says the product must run on NVIDIA Nemotron, through Meterless or NVIDIA's API. This supports the previously noted Academy wording, but the published event rule's broader NVIDIA-contribution wording still differs. Treat Nemotron as an explicit organiser expectation to resolve/meet in the approved scope; no Driftwatch model setting was changed.
- **Build and runtime credits are distinct:** Cursor is for development; the guide says not to place Meterless/NVIDIA runtime keys in Cursor's provider settings. Reading the connection guide or doing this work through Hermes does not establish actual Cursor development.
- **Meterless is internally underspecified:** the introduction says it must run locally, the prompt library is labelled optional, and Power allows a direct NVIDIA route. Neither an optional prompt file nor a provider call automatically proves the previously proposed World Model integration. Ask what local Meterless component and runtime evidence are required.
- **Unfinished placeholders remain** for Cursor credit redemption, the Meterless library, workshop details, Meterless signup/credit/base URL and hotspot. Do not invent those details or block NVIDIA's independently documented alternative on a missing Meterless provider URL.
- **Guide smoke test is connectivity evidence, not end-to-end proof:** the model check tests that choices exist, not model identity, grounded reasoning or tool execution. It does not explicitly set a model-call timeout. Do not copy this as Driftwatch's runtime acceptance test.
- **PokéAPI creation is not covered by our approval:** the tutorial registers remote objects, whereas the approved onboarding check is read-only. Stop before source registration/DDL and before installing dependencies.

## Approved action and actual results

Approval interpreted narrowly from the preceding request: separate pinned checkout, local prerequisite checks, and authenticated read-only sample queries only once access is available. It excludes installs, cloud provisioning, object creation and Driftwatch product-code changes. It does not authorise the previously timed-out protected `AGENTS.md` write.

Created and verified a clean detached checkout at:

`/Users/ant/projects/zetaris-getting-started-readonly-44668b2`

Verified HEAD: `44668b267ad7ee0fae25ce7588e9620121d47cae`. Read the supplier instructions; no commit or push.

Live local inspection:

| Prerequisite | Observed result |
|---|---|
| Host | arm64; 32 GiB RAM; 12 logical CPUs; approximately 332 GiB free disk |
| Docker | No executable on PATH; `/Applications/Docker.app` absent |
| Python | Python 3.11.16 available |
| Java | `/usr/libexec/java_home` found no registered JDK; supplier Java discovery also found none |
| Supplier `.env.local` | Absent; no secrets read or copied from Driftwatch |
| Supplier `.venv` / `jaydebeapi` | Absent / not importable in the checked Python interpreter |
| Driver | No path supplied; no driver search performed |

Executed the actual supplier **`scripts/preflight.py --jdbc` with Python 3.11**, in that checkout, using an environment with inherited `ZETARIS_*` settings excluded. **Exit 1; `NOT READY: 10 check(s) failed`.**

- **REST:** missing API key/configuration; no authenticated REST operation executed.
- **JDBC:** no Java discovery, Python runner environment/package or JAR path; local port probe failed; no authenticated JDBC query executed.
- Because the supplier collapses socket errors to “closed,” independently repeated the same read-only local probe and obtained **`ConnectionRefusedError`, errno 61, connection refused** at `localhost:10000`. This was not an `Operation not permitted` result; no permission escalation was needed. It says nothing about any future remote endpoint.

No `SELECT 1`, discovery or sample query result is claimed. The local prerequisites are blocked; stopped as agreed. Host capacity is not proof Docker has the required allocated resources or emulation configured.

## Next approval / user action

**New approval needed:** install Docker Desktop and configure a local Zetaris platform on the personal Mac, including the vendor bundle/image download and local container/volume creation. Confirm entitlement/account terms and resource allocation first. Any OS permission/privileged installer interaction remains a user step; never enter passwords in chat. A separate JDK/JDBC-package install needs explicit scope approval if JDBC onboarding remains desired; REST runtime does not require those client dependencies.

**User action:** obtain the platform account/download entitlement through the official portal. Keep registry/account secrets private. If access is blocked or the local/Meterless/Nemotron eligibility wording needs clarification, ask Help Zetaris/organisers. Do not provision AWS or change lab retention as an automatic workaround.

**Still unapproved:** product integration, model change, source registration/DDL, cloud resources, lab lifetime change and employer-machine installation. This note records an executed prerequisite check, not a completed service setup or sponsor integration.
