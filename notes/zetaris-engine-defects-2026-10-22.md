# Zetaris CSV engine defect — quoted cells truncated (found 22 Oct 2026, engine 2.4.3.1)

**Severity: data-corrupting, silent at the row level.** A `CREATE LIGHTNING FILESTORE TABLE ...
FORMAT CSV` table whose cell contains an embedded double quote (RFC-4180 escaped as `""`) returns
a **truncated value** from `SELECT`: the parser closes the cell at the first inner quote.

## Reproduction (our tenancy, admin and least-privilege paths alike)

Staged CSV cell on disk, valid RFC-4180 (a JSON predicate inside a CSV column):

```
"{""resource_class"":""block_volume"",""attached"":false}"
```

`SELECT rule_id, when_json FROM DRIFTWATCH_REF.policy_rules_base_v1 WHERE ...` returned:

```
"{"resource_class":"block_volume"
```

— the cell ends mid-JSON; the rest of the value is gone. No error, no warning: the row count and
all *other* columns are intact. Any naive digest/hash check downstream is the only thing that
catches it (ours rejected the snapshot and degraded to the fallback; nothing corrupted was used).

## Impact and work-around (adopted with builder approval, same day)

Percent-encoding `"` and `,` in the JSON-bearing column (`{"a":1}` → `{%22a%22%3A1}`) makes the
cell contain no CSV-special characters; the engine round-trips it byte-exact (verified live), and
the client decodes with `unquote` **only when the raw cell fails `json.loads` first** (collision-
safe for text that legitimately contains `%22`). Content digests are unchanged because they are
computed over parsed records, not cell bytes. New immutable snapshot ids `*_v2`; v1 tables revoked
and dropped; staged files never overwritten.

## Notes for the supplier / demo narrative

- The documented FORMAT CSV examples use columns without embedded quotes, which is why this hides.
- A `QUOTE` / `ESCAPE` table option, or a proper RFC-4180 parser, would remove the need.
- Found purely through a staged capability probe (session table first, permanent registration only
  after the probe), which is also the honest story for *why our agent never trusts a connector*:
  every published snapshot round-trips a digest check end to end.
- Related engine behaviour recorded the same day: `sqls/run` is the only endpoint accepting SHOW/
  DDL; one statement per request; `file://` paths work; `X-Org-ID` must be numeric; the
  user-create API rejects non-camelCase `isLdap` with a bare `Invalid value for: body`, and the
  UI gate (password ≥6) disagrees with the server rule (≥8 + upper + lower + digit + `$@!%*?&`).
