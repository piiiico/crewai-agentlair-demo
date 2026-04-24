# CrewAI + AgentLair: Identity for Your AI Agents

Give your CrewAI agents a **persistent identity** — a real email address, encrypted credential vault, and behavioral trust score — in one API call.

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
| **Encrypted vault** | Store secrets (API keys, credentials) securely with client-side encryption |
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

### 3. Run the demo

```bash
python demo.py
```

The script will:
1. Register a new AgentLair agent (or use existing credentials)
2. Create a CrewAI crew with two agents
3. Send a real email from the agent's `@agentlair.dev` address
4. Store a credential in the encrypted vault
5. Display the agent's trust score

## API reference

All calls use raw HTTP (no SDK required):

```python
import requests

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

# Store in vault (client-side encrypted)
requests.put(f"{BASE_URL}/v1/vault/my-key",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"ciphertext": encrypted_value})

# Get trust score
requests.get(f"{BASE_URL}/v1/trust/score?agent_id={account_id}",
    headers={"Authorization": f"Bearer {api_key}"})
```

## Related

- [AgentLair docs](https://agentlair.dev/getting-started)
- [LangChain integration](https://github.com/piiiico/agentlair-langchain-integration)
- [AgentLair MCP server](https://agentlair.dev/mcp)
