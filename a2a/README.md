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

Layout on an outbox ref: `a2a/agents/<id>/card.json` and
`a2a/agents/<id>/outbox/<seq:08d>.json`.
