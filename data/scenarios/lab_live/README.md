# lab_live — masked capture of the author's own lab tenancy

This scenario is **not synthetic** like `example_1..3`. It is a capture of the throwaway
lab tenancy described in `docs/lab-tenancy.md` (four short-lived instances, one orphan
volume, one reserved public IP, created 28 Sep 2026), taken through the live adapters and
then masked: every OCID here was run through `scripts/mask_ocids.py` before committing.

Its job is the **fixture fallback** the live path degrades to when credentials or the API
are unreachable mid-run, so a degraded run still audits real captured shapes instead of
nothing. It is also what a `SAMPLE_MODE=false` run against a broken `~/.oci/config` reads.

The telemetry numbers here are honest for their capture time: coverage against the 168 h
rules window was ~0.01 (the tenancy was hours old), so the idle/loaded verdicts are
deliberately undetermined and only the orphan/unattributed findings fire. Ground truth for
the capture is what the pipeline actually accepted at capture time: two cost-waste orphans
and one unattributed instance; no CPU-based verdicts were possible.

`run_eval.py` scores the curated `example_1..3` scenarios; this directory is excluded from
scoring by design — you cannot hold a snapshot of a moving tenancy to a fixed answer key.
