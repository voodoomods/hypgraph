# Verifying a record

A HypGraph record can be checked by someone who doesn't trust whoever kept it. This page says what each check shows,
and the one step that turns "consistent" into "not rewritten": checking the record against a head published
somewhere its keeper can't change.

## Four different guarantees

| | What it shows | How | What it doesn't show |
|---|---|---|---|
| **1. Internal consistency** | The chain of events is unbroken, and every node, version, link, withdrawal and retraction matches the event that wrote it. | `hypgraph verify study.bundle.json` (or a graph file), `verify_bundle(b)` in Python, `HypGraph.verifyBundle` in the browser | That it wasn't rewritten. Whoever can write the record can change it, recompute every hash, or cut it short, and it still verifies. |
| **2. Not rewritten since it was published** | The record ends at the head that was published. Any change to anything before it, or a record cut short, ends somewhere else. | `hypgraph verify study.bundle.json --head <published head>`, `verify_bundle(b, head=...)`, `anchored(g.verify(), head)` | Who published that head. That's the job of where it was published (below). |
| **3. Provenance of the evidence** | Who recorded what, and how: a lab-recorded run (only the instrument author files those) or an agent's report, its inputs and outputs by hash, which lines of support are independent. | The record's derived standing: `hypgraph show CL1 --why`, the report | That the instrument's own files are honest. A host decides who the instrument is (the policy). |
| **4. That a claim is true** | Nothing. | Reviews, replications, separate implementations, new data: the evidence the record keeps and ranks | — |

A verified bundle with a matching published head proves the record is the one that was published, unchanged. The
claims in it stand exactly as well as the record derives, and no better.

## Publishing a head

`hypgraph verify` prints the full head:

```text
$ hypgraph demo && hypgraph export -o study.bundle.json
Wrote study.bundle.json: 59 events, 24 nodes
$ hypgraph verify study.bundle.json
✓ study.bundle.json: 59 events verified — chain intact, every row matches the event that wrote it.
  head 565123f3a7ac06ed18ab555935fde0457ebb6a302dc188fc83dbf36af579623f
  consistent with itself; to rule out a rewrite, check it against a published head (--head)
$ hypgraph verify study.bundle.json --head 565123f3a7ac06ed
✓ study.bundle.json: 59 events verified — chain intact, every row matches the event that wrote it.
  head 565123f3a7ac06ed18ab555935fde0457ebb6a302dc188fc83dbf36af579623f
  matches the anchored head: not rewritten or cut short since it was published
```

(Your head will differ: node ids and times are part of what is hashed.)

Publish that head somewhere you don't control after the fact. Any of these is enough, and none needs new
infrastructure:

- **In the paper, preregistration or report** that relies on the record: "Record head: `565123f3a7ac…`".
- **As a release asset or in a signed tag** of the repository that holds the work: `git tag -s study-v1 -m "head 565123f3…"`.
- **Signed with a key your readers already trust**, using tools they already have:

  ```bash
  hypgraph verify study.bundle.json --json | python -c "import json,sys; print(json.load(sys.stdin)['head'])" > study.head
  ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n hypgraph-head study.head          # writes study.head.sig
  ```

  and a reader checks the signature, then the record against it:

  ```bash
  ssh-keygen -Y verify -f allowed_signers -I you@example.org -n hypgraph-head -s study.head.sig < study.head
  hypgraph verify study.bundle.json --head "$(cat study.head)"
  ```

- **With a third-party timestamp** (an RFC 3161 service, or any public notarisation) over `study.head`, if you need
  to show *when*.

A record keeps growing. Publish the head of each version you rely on; a later bundle still verifies, and its chain
passes through every earlier head (an earlier head is the `hash` of one of its events).

## Checking without HypGraph

The bundle stores every event and every version body as the exact string that was hashed. A verifier only runs
SHA-256 over strings and compares: no JSON canonicalisation to reimplement. The record format, including the bundle
and the verifier's rules, is in [spec.md](spec.md). The site checks bundles in the browser with WebCrypto, from a
separate implementation.

## Scoped bundles and references

- `hypgraph export --inv INV` writes one investigation. Events outside it are redacted to their hash, so the chain
  still verifies, but their content can't be checked; the verifier says how many. The full record rules out a change
  hidden among them.
- A source that pins another record's node checks that the cited body still hashes to the pinned version. It doesn't
  check the cited record's history: for that, verify that record against its own published head.

## Try it

`dev/e2e_install.py` installs HypGraph into a fresh environment and walks the whole path: a record, a claim accepted
and one refused, a review, an export, and verification in another directory with no graph file, on its own and
against the head, and failing on an edited copy. `tests/test_anchoring.py` rewrites a record (changing a claim and
recomputing every hash) and cuts one short: both verify on their own, and both fail against the published head.
