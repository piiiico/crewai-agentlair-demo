---
title: "How to Add Identity to Your CrewAI Agents"
description: "Give your CrewAI agents a real email address, encrypted vault, and behavioral trust score — in one API call. No SDK required."
date: 2026-04-25
---

# How to Add Identity to Your CrewAI Agents

CrewAI is excellent at multi-agent orchestration. But every CrewAI agent has the same problem: the moment your script finishes, the agent disappears. No persistent email address. No credential storage. No way for external systems to reach it.

AgentLair fixes this. One API call gives your agent:
- A real `@agentlair.dev` email address
- An encrypted credential vault
- A behavioral trust score

Here's how to wire it up.

## The registration call

```python
import requests

resp = requests.post("https://agentlair.dev/v1/auth/agent-register",
    json={"name": "my-crewai-agent"})

creds = resp.json()
# {
#   "api_key": "al_live_...",
#   "email_address": "my-crewai-agent@agentlair.dev",
#   "account_id": "acc_...",
#   "tier": "free"
# }
```

Save `api_key` and `email_address`. You'll use them in every subsequent API call.

## Email as a CrewAI tool

```python
from crewai.tools import tool

@tool("send_email")
def send_email_tool(to: str, subject: str, body: str) -> str:
    """Send a real email from this agent's @agentlair.dev address."""
    resp = requests.post("https://agentlair.dev/v1/email/send",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": email_address,
            "to": to,
            "subject": subject,
            "text": body,
        })
    result = resp.json()
    return f"Email sent (id={result['id']}, status={result['status']})"
```

Attach this to any CrewAI `Agent` and it can send real email. No SMTP. No configuration. The `@agentlair.dev` address is persistent — the same agent can receive replies in a future session.

## Credential vault

Agents often need to handle API keys and secrets. AgentLair Vault stores them encrypted with client-side encryption — AgentLair sees only the ciphertext:

```python
import base64, hashlib, secrets

def encrypt_secret(plaintext: str, seed: bytes, key_name: str) -> str:
    """Simple client-side encryption (use AES-GCM in production)."""
    dk = hashlib.sha256(seed + key_name.encode()).digest()
    nonce = secrets.token_bytes(16)
    keystream = hashlib.sha256(dk + nonce).digest()
    ciphertext = bytes(a ^ b for a, b in zip(plaintext.encode(), keystream * 4))
    return base64.b64encode(nonce + ciphertext).decode()

# Store
ciphertext = encrypt_secret("sk-openai-abc123", vault_seed, "openai-key")
requests.put("https://agentlair.dev/v1/vault/openai-key",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"ciphertext": ciphertext})
```

The vault key persists across sessions. Your agent can retrieve its own credentials on startup.

## Trust score

Every action your agent takes contributes to a behavioral trust score:

```python
resp = requests.get(
    f"https://agentlair.dev/v1/trust/score?agent_id={account_id}",
    headers={"Authorization": f"Bearer {api_key}"})

score = resp.json()
# {
#   "score": 30,
#   "atfLevel": "intern",
#   "trend": "stable",
#   "dimensions": { "consistency": ..., "restraint": ..., "transparency": ... }
# }
```

New agents start at 30 (intern level). The score rises as the agent acts consistently, respects rate limits, and maintains audit coverage. External systems can check this score before accepting work from your agent — a verifiable track record, not just a claim.

## Putting it together

```python
from crewai import Agent, Task, Crew

# Wire up the tools
agentlair_tools = [send_email_tool, store_secret_tool, get_trust_score_tool]

researcher = Agent(
    role="Research Agent",
    goal="Research and store findings securely",
    backstory="An agent with a persistent AgentLair identity",
    tools=agentlair_tools,
)

reporter = Agent(
    role="Report Agent",
    goal="Send findings via email",
    backstory="A communication agent with a real email address",
    tools=agentlair_tools,
)

crew = Crew(agents=[researcher, reporter], tasks=[research_task, report_task])
result = crew.kickoff()
```

The full working example is at [github.com/piiiico/crewai-agentlair-demo](https://github.com/piiiico/crewai-agentlair-demo).

## What this unlocks

| Without AgentLair | With AgentLair |
|-------------------|----------------|
| Agent disappears at script end | Persistent identity across sessions |
| No way to receive replies | Real `@agentlair.dev` inbox |
| Credentials in plaintext env vars | Client-side encrypted vault |
| No trust record | Behavioral trust score |

## Get started

Register for free at [agentlair.dev](https://agentlair.dev) — or let the demo script handle it automatically.

The only required credential is an LLM API key (OpenAI, Anthropic, or any OpenAI-compatible endpoint). AgentLair registration happens in the script itself.

```bash
git clone https://github.com/piiiico/crewai-agentlair-demo
cd crewai-agentlair-demo
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY to .env
python demo.py
```

Questions? Reply to this post or reach the maintainer at [pico@amdal.dev](mailto:pico@amdal.dev).
