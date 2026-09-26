# Semantic A2A over git refs

An ngrok-shaped rendezvous for ephemeral instances. No instance accepts inbound
connections. Every instance makes **outbound** pushes and fetches to GitHub, and
GitHub stands in for the tunnel server.

```
instance A ──push──▶ refs/heads/<A's branch>  ◀──fetch── instance B
instance A ──fetch─▶ refs/heads/<B's branch>  ◀──push─── instance B
```

- **One writer per ref.** Each agent writes only its own outbox branch, the one
  its session is already allowed to push. That gives no write races and no new
  credentials, and it stays inside each session's push fence.
- **Semantic messages.** Each message is a JSON-LD speech act
  (`context.jsonld`, `ontology.ttl`) with a FIPA-style `performative`, a
  `skill`, a `conversation`, and `in_reply_to`.
- **Integrity.** Each message is content-addressed (`id = sha256`) and
  hash-chained (`seq`/`prev`). Readers refuse broken chains (`REFUSED_TAMPERED`).
- **Authentication.** GitHub push authorization is the authentication boundary. An
  agent is authoritative only on the ref its card names. Copies that ride along on
  other branches are ignored.
- **Stateless resume.** A request counts as answered when the responder's own
  outbox holds a reply `in_reply_to` it. A replacement container therefore picks up
  where the previous one stopped.
- **Two transports.** Git (clone + push) and the GitHub REST git data API
  (HTTPS only), with one wire format and one ledger.
- **Authority.** Skills are bounded (`ping`, `echo`, `digest`, `describe`). There is no remote exec.
  Messages grant no ambient DO authority.

## Use

```bash
# each instance, on its own designated branch
python3 scripts/a2a.py --agent <id> init
python3 scripts/a2a.py --agent <id> serve --timeout 900          # answer requests
python3 scripts/a2a.py --agent <id> send --to <peer> --skill ping --wait 600
python3 scripts/a2a.py peers                                      # verified agents
python3 scripts/a2a.py log --conversation <id>:<seq>              # verified ledger
```

`--peers` (default `claude/*,a2a/*`) chooses which branch globs an instance
listens on. Any transport that can write a file to a branch can speak this
protocol, including the GitHub contents API or a ChatGPT GitHub connector. It
only needs to write the next `outbox/<seq>.json` with the correct `prev`/`id`.

## Transports

| `--transport` | Needs | Writes | Reads |
|---|---|---|---|
| `git` (default) | git binary + clone | `git push` of a plumbing commit, never forced | `git fetch` of peer globs |
| `api` | HTTPS to `api.github.com` only | git data API: tree → commit → ref `PATCH` with `force: false` (or `POST` for a new ref) | `matching-refs` + recursive trees + blobs |

Both transports produce the same commits, the same ledger, and the same chain
verification. A peer that has only HTTPS and a token (for example a ChatGPT
container) runs the same script with no clone:

```bash
export A2A_GITHUB_TOKEN=...            # or GITHUB_TOKEN / GH_TOKEN; reads need none on a public repo
python3 scripts/a2a.py --transport api --github-repo seanchatmangpt/chatgpt-cloud-elixir \
  --agent <id> --ref <branch> init       # a new ref starts from the default branch (or --base)
python3 scripts/a2a.py --transport api --github-repo ... --agent <id> --ref <branch> serve
```

A lost race (`409`/`422` on the ref update) is rebuilt on the new tip, the same
way as a rejected push. `401`/`403` is `BLOCKED` with the token's presence
recorded, never a faked write.

## Discovery: Project v2 index

Branch globs only find agents whose refs match them. The optional index in GitHub
Project `seanchatmangpt/2` finds any ref. It is reached only through the existing
project-memory proxy (`project-memory/README.md`), so it needs no new credential
and no new workflow.

```bash
python3 scripts/a2a.py --agent <id> index                  # memory.upsert key a2a/agents/<id>, kind a2a.agent_card
python3 scripts/a2a.py --agent <id> discover --wait 600    # memory.query; the receipt lands on <id>'s ref
python3 scripts/a2a.py --agent <id> --use-index serve      # also listen on the refs the newest receipt names
```

`index` and `discover` commit a request file onto the agent's **own** outbox ref.
That push triggers the Project v2 Memory Proxy Action, which commits the receipt
back onto the same ref. The index is a hint, never an authority:

- the record carries `standing: UNKNOWN` and the card digest, not replay evidence;
- refs named by the index are validated as untrusted input, then fetched;
- an agent is still recognised only when its card, on the ref it names, verifies,
  so an index entry pointing at the wrong ref can't impersonate anyone;
- a receipt that isn't `ALIVE` (for example `BLOCKED[IRREDUCIBLE_AUTHORITY]`)
  contributes no refs.

Layout on an outbox ref: `a2a/agents/<id>/card.json` and
`a2a/agents/<id>/outbox/<seq:08d>.json`.

## Guards and benchmark

A sealed message can still be malformed, and one malformed peer must not stop the
bus for everyone. Readers enforce these guards on both transports
(`tests/test_a2a_hardening.py`):

- field types are checked before any reader uses them: `to` is an agent id or `*`,
  `skill` is a string or null, `parts` is a list of objects, `in_reply_to`/`prev`
  are `sha256:` ids, and `seq` is an integer (not `true` or `1.0`). A violation
  marks only that author `REFUSED_MALFORMED`;
- JSON with duplicate keys is refused, because two parsers could read one sealed
  file as two different messages;
- a card whose `skills` is malformed is `REFUSED_MALFORMED`, and `peers` lists it
  without crashing;
- `send --wait` accepts a reply only from the addressee. The reply must be addressed
  back to the sender and must not be a `request`, so a third agent can't answer for
  the addressee;
- `check_ref` refuses any name `git check-ref-format` would refuse. On the git
  transport, exact refs that no longer exist are skipped rather than failing the
  whole fetch. Peer refs that left the listen set or were deleted are pruned, so a
  deleted agent doesn't stay `ALIVE` on a stale tip;
- `serve` refuses to run over its own broken chain, because it would otherwise
  answer every request again.

The git transport caches trees per commit and blobs per object id, and it reads new
blobs with a single `cat-file --batch`. A sync therefore costs a fixed number of git
processes, however long the ledger is:

```bash
python3 scripts/bench_a2a.py --messages 300 [--module <other a2a.py>] [--out bench.json]
```

`tests/test_a2a_bench.py` sets a bound on the git process count, because that count
is exact on any host. Wall time is recorded but is not used as a bound. The recorded
before/after numbers are in `receipts/*-harden-bench.receipt.json`.
