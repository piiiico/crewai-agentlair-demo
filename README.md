# CrewAI + AgentLair: Identity for Your AI Agents

Give your CrewAI agents a **persistent identity** — a real email address, AES-256-GCM encrypted credential vault, and behavioral trust score — in one API call.

```
curl -X POST https://agentlair.dev/v1/auth/agent-register \
  -H "Content-Type: application/json" \
  -d '{"name":"my-crewai-agent"}'

# Returns: API key + @agentlair.dev email + trust score. Free.
```

## What this demo shows

| Capability | What you get |
|------------|-------------|
| **Persistent identity** | A real `@agentlair.dev` email address that survives session restarts |
| **Agent email** | Send real emails directly from your CrewAI agent — no SMTP |
| **Encrypted vault** | Store secrets with client-side AES-256-GCM (cryptography package) |
| **Trust score** | Behavioral trust score computed from what your agent does |

## Why it matters

CrewAI agents are stateless between runs. AgentLair gives them a **persistent, verifiable identity** that works across any framework or platform:

- External systems can reach your agent at its email address
- Credentials survive container restarts
- Every action contributes to a trust score that proves your agent is safe

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — or let the script register a new agent automatically
```

### 3a. Test integrations (no LLM key needed)

```bash
python demo.py --test
```

This verifies all AgentLair integrations (register, trust score, vault, email, CrewAI tool wiring) without needing an LLM API key.

### 3b. Run the full LLM-orchestrated demo

```bash
export OPENAI_API_KEY=sk-...   # or configure another provider in .env
python demo.py
```

## Verified output

Running `python demo.py --test` against the live AgentLair API:

```
=== AgentLair Integration Test ===

[1/5] Registering agent...
  ⟳ Registering new AgentLair agent: 'crewai-demo-test'
  ✓ Registered!
    Email:   crewai-demo-test-8429@agentlair.dev
    Account: acc_MGZeQHzprGscGj8U
  Email:   crewai-demo-test-8429@agentlair.dev
  Account: acc_MGZeQHzprGscGj8U

[2/5] Checking trust score...
  ✓ Score: 30/100  Level: intern  Trend: stable

[3/5] Vault AES-256-GCM round-trip...
  ✓ Stored  'test-secret'
  ✓ Retrieved: 'demo-openai-key-sk-test-1234567890' [✓ MATCH]

[4/5] Sending email (agent → own address)...
  ✓ Sent id=out_BbDbBHWnhqCy7YQ4  status=sent

[5/5] Wiring CrewAI tools and verifying each...
  ✓ Tools registered: ['send_email', 'store_secret', 'get_trust_score']
  ✓ send_email → Email sent (id=out_zCHfT6BNL79CvCm3, status=sent)
  ✓ store_secret → Secret stored at vault key 'crewai-test-key'
  ✓ get_trust_score → Trust score: 30/100 (level: intern)

  ✓ CrewAI agents initialized: Research Agent, Report Agent
  ✓ Each agent has 3 AgentLair tools attached

=== All 5 integration checks passed ===
   Email:      crewai-demo-test-8429@agentlair.dev
   Trust:      30/100 (intern)
   Vault:      AES-256-GCM round-trip verified
   CrewAI:     v1.14.2 — agents + tools wired
```

## API reference

All calls use raw HTTP (no SDK required):

```python
import requests, os, base64, hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_URL = "https://agentlair.dev"

# Register an agent
response = requests.post(f"{BASE_URL}/v1/auth/agent-register",
    json={"name": "my-agent"})
creds = response.json()
# creds["api_key"], creds["email_address"], creds["account_id"]

# Send email
requests.post(f"{BASE_URL}/v1/email/send",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "from": email_address,
        "to": "recipient@example.com",
        "subject": "Hello from my agent",
        "text": "Agent-authored message"
    })

# Store in vault (AES-256-GCM client-side encryption)
dk = hashlib.sha256(seed + b"my-key").digest()
aesgcm = AESGCM(dk)
nonce = os.urandom(12)
ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
requests.put(f"{BASE_URL}/v1/vault/my-key",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"ciphertext": base64.b64encode(nonce + ciphertext).decode()})

# Get trust score
requests.get(f"{BASE_URL}/v1/trust/score?agent_id={account_id}",
    headers={"Authorization": f"Bearer {api_key}"})
```

## Related

- [AgentLair docs](https://agentlair.dev/getting-started)
- [AgentLair MCP server](https://agentlair.dev/mcp)

## License

MIT — see [LICENSE](LICENSE)
