# Zetaris on OCI — approved deployment direction

**19 October deployment complete:** [verified runtime/access report](zetaris-oci-deployed-2026-10-19.md)
and [generated acceptance evidence](evidence/2026-10-19-zetaris-deployment.json) supersede the
blocked/unprovisioned state below. Dedicated E5 service is running; nine vendor checks and
seven checks each via direct REST/in-container JDBC passed. No custom product integration.

**18 October assessment complete:** [readiness and cost evidence](zetaris-oci-readiness-2026-10-18.md)
verifies `antworld` through the API, E5/E6/Standard3 listing, compatible Ubuntu image and
quota headroom. [Runbook](../docs/zetaris-oci-runbook.md) and
[product proposal](../docs/superpowers/specs/2026-10-18-sponsor-integration-proposal.md)
are prepared. At that assessment's cutoff registry access remained blocked and no resources
or product code had changed; the 19 October report records the subsequent infrastructure writes.

## 17 October 2026 — approval and corrected trial expiry

The builder explicitly approved implementing the Zetaris deployment in the **`antworld` OCI tenancy**, rather than installing the stack on the personal Mac. This authorises the infrastructure deployment direction; no VM or sponsor service has yet been created. Product integration, source registration and track/model changes remain separate scopes.

The builder states the tenancy has sufficient trial credit and expires **26 November 2026**. A supplied console screenshot visibly confirms a subscription usage period **28 September–26 November 2026**, an expiry of **26 November 2026**, and low usage against its credit allocation. The screenshot itself does not display the tenancy name. Attribute the antworld identity to the builder, and verify the API target before provisioning. Do not publish the screenshot, subscription identifier or personal billing details. Earlier approximate 27 October expiry assumptions are superseded by this evidence for the identified subscription; it does not establish expiry for another tenancy.

This approval does not automatically change the existing audited lab's 21 October teardown. Keep a dedicated sponsor-service VM separate from the workloads being audited. Establish the actual tenancy/profile identity, regional x86 availability, priced configuration and teardown plan before resource creation. Trial expiry is not a target to keep the service running until.

## Account/platform access — prerequisite history (technical access verified 19 October)

Official installation reference, re-read on 17 October:
https://zetaris.github.io/getting-started/docs/install/updated_zetaris_installation_guide.html

1. User registers/signs in at https://cloud.enterprise.zetaris.com/register after reviewing the vendor terms/privacy policy. A portal account and the administrator account later created inside the deployed platform are distinct.
2. User opens https://cloud.enterprise.zetaris.com/dashboard/download (**Run locally**) and obtains `zetaris-platform.zip`, the matching platform `.env` and registry sign-in details. Despite the page title, this is the self-managed bundle relevant to our proposed Linux OCI deployment, not the managed-AWS cluster workflow.
3. Confirm the actual licence/evaluation or hackathon entitlement covers the intended OCI-hosted evaluation and demonstration. The installation guide describes up to 30 days of internal evaluation without an Order; signup alone does not prove an indefinite licence or establish public-demo rights. The recipe repository's Apache licence does not license the platform images.
4. If the download is not enabled or the entitlement scope is unclear, ask Zetaris Support / Help Zetaris on HackOS to enable participant access and confirm that a dedicated self-managed OCI x86 VM is acceptable. Never purchase an upgrade or accept billing commitments merely to unblock setup without approval.

Unauthenticated HTTP retrieval of both portal routes returned HTTP 200 HTML application shells. That does not verify their actual logged-in UI, downloadable artifacts or this user's account entitlement. The official installation guide provides the routes above.

Passwords, registry secrets and platform `.env` contents stay out of chat, public repository and logs. User can save the vendor archive privately and supply its local filesystem path; private bundle handling is separate from inspecting/publishing its contents. Use the credential vault for any later supported secret entry; never ask the user to paste registry passwords or account keys into chat.

## Historical state at the 17–18 October preparation cutoff

- Separate supplier checkout is already verified at `44668b267ad7ee0fae25ce7588e9620121d47cae`.
- Earlier client preflight failed because no platform/configuration/JDBC prerequisites were available. It was not an OCI deployment test.
- User subsequently registered and downloaded `/Users/ant/Downloads/zetaris-platform.zip`.
  Archive integrity passed; SHA-256 is `14c6a811a140378bec1749ceffd7fa123bafb2f178545b26354e8f9433b413d3`.
  It contains the matching configuration, Compose file, scripts and JDBC driver. Bundled
  credential files have not been opened or published.
- The registry-access button returned the generic portal error “We could not accept your
  request right now. Please try again in a moment.” User reports emailing Zetaris support.
  Cause and registry entitlement remain unverified; no known fix is claimed.
- While waiting, static inspection confirmed safe archive member paths and successful
  `bash -n` syntax checks for every bundled shell script. No vendor script was executed.
  These are structural checks, not runtime/security certification. Generated local-only
  report: `/Users/ant/.hermes/cache/scratch/zetaris-bundle-static-check.json`.
- No registry login, VM provisioning or cloud-resource change has been performed. Registry
  credentials/image access remain the startup blocker; approval for the OCI deployment
  is already recorded. Prepare a read-only tenancy/capacity/cost assessment and isolated
  network/teardown plan without creating an idle paid VM.
