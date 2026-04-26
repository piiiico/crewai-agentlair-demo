# CrewAI + AgentLair: Persistent Identity for AI Agents

Give your CrewAI agents a **persistent identity** — a real email address, encrypted credential vault, and behavioral trust score — in under 5 minutes.

Each agent gets:
- A real `@agentlair.dev` email address (no SMTP setup)
- AES-256-GCM encrypted credential vault
- Behavioral trust score (OWASP ASI03/ASI07 compliant)

## Quick start

**Install:**
```bash
pip install crewai requests python-dotenv cryptography
```

**Register your agent (one API call):**
```bash
curl -X POST https://agentlair.dev/v1/auth/agent-register \
  -H "Content-Type: application/json" \
  -d '{"name":"my-crewai-agent"}'
# Returns: api_key + @agentlair.dev email + account_id. Free.
```

**Run the demo:**
```bash
git clone https://github.com/piiiico/crewai-agentlair-demo
cd crewai-agentlair-demo
python demo.py --test     # verifies all integrations, no LLM key needed
python demo.py            # full crew (requires OPENAI_API_KEY)
```

The `--test` mode registers a fresh agent, verifies vault encrypt/decrypt, sends a real email, and wires the CrewAI tools — all without an LLM key.

## What the demo shows

| Capability | Details |
|------------|---------|
| **Persistent identity** | `@agentlair.dev` email survives container restarts |
| **Agent email** | Send real emails directly from your agent — no SMTP |
| **Encrypted vault** | Client-side AES-256-GCM; server never sees plaintext |
| **Trust score** | Behavioral score computed from what your agent does |
| **Trust gating** | Check score before allowing high-stakes actions |

## Why this matters

CrewAI agents are stateless between runs. AgentLair gives them a **persistent, verifiable identity** that works across any framework or platform:

- External systems can reach your agent at a stable email address
- Credentials survive container/session restarts — stored encrypted in the vault
- Every action contributes to a trust score that proves your agent is safe (OWASP ASI03)
- Cross-crew handoff attestation: receiving agents can verify the delegating agent's identity (OWASP ASI07)

## Architecture

```
CrewAI Agent
    │
    ├── send_email tool     → AgentLair /v1/email/send
    ├── store_secret tool   → AES-256-GCM (client) → AgentLair /v1/vault/{key}
    └── get_trust_score tool → AgentLair /v1/trust/score
```

AAT (Agent Authentication Token) is a short-lived EdDSA JWT (1h TTL) issued per session. Verifiers fetch the JWKS at `https://agentlair.dev/.well-known/jwks.json`.

## Verified output

```
=== AgentLair Integration Test ===

[1/5] Registering agent...
  ⟳ Registering new AgentLair agent: 'crewai-demo-test'
  ✓ Registered!
    Email:   crewai-demo-test-6576@agentlair.dev
    Account: acc_pGR5KN5BNUAiQ6JL

[2/5] Checking trust score...
  ✓ Score: 30/100  Level: intern  Trend: stable

[3/5] Vault AES-256-GCM round-trip...
  ✓ Stored  'test-secret'
  ✓ Retrieved: 'demo-openai-key-sk-test-1234567890' [✓ MATCH]

[4/5] Sending email (agent → own address)...
  ✓ Sent id=out_Yz63XROTZXM8X9aP  status=sent

[5/5] Wiring CrewAI tools and verifying each...
  ✓ Tools registered: ['send_email', 'store_secret', 'get_trust_score']
  ✓ send_email → Email sent (id=out_PL3qafQNc4AIDUdT, status=sent)
  ✓ store_secret → Secret stored at vault key 'crewai-test-key'
  ✓ get_trust_score → Trust score: 30/100 (level: intern)
  ✓ CrewAI agents initialized: Research Agent, Report Agent
  ✓ Each agent has 3 AgentLair tools attached

=== All 5 integration checks passed ===
   Email:      crewai-demo-test-6576@agentlair.dev
   Trust:      30/100 (intern)
   Vault:      AES-256-GCM round-trip verified
   CrewAI:     v1.14.3 — agents + tools wired
```

## Configuration

The demo auto-registers a new agent on first run and saves credentials to `.agentlair-credentials.json`. For production, use environment variables:

```bash
AGENTLAIR_API_KEY=...
AGENTLAIR_EMAIL=my-agent@agentlair.dev
AGENTLAIR_ACCOUNT_ID=acc_...
AGENTLAIR_VAULT_SEED=...   # 32-byte hex; keep this safe
```

## Related

- [AgentLair docs](https://agentlair.dev/getting-started)
- [AgentLair MCP server](https://agentlair.dev/mcp)
- [OWASP Agentic AI Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

## License

MIT — see [LICENSE](LICENSE)
