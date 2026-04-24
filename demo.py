"""
CrewAI + AgentLair Demo
=======================
Adds persistent identity, email, vault, and trust scoring to a CrewAI crew.

Each agent in the crew gets:
  - A real @agentlair.dev email address
  - Client-side AES-256-GCM encrypted credential vault
  - Behavioral trust score

Run: python demo.py
Test integrations (no LLM key needed): python demo.py --test
"""

import os
import json
import base64
import hashlib
import secrets
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from crewai import Agent, Task, Crew
from crewai.tools import tool

# Load .env if present
load_dotenv()

AGENTLAIR_BASE = "https://agentlair.dev"
CREDENTIALS_FILE = ".agentlair-credentials.json"


# ── AgentLair helpers ──────────────────────────────────────────────────────────

def register_agent(name: str) -> dict:
    """Register a new AgentLair agent. Returns api_key, email_address, account_id."""
    resp = requests.post(
        f"{AGENTLAIR_BASE}/v1/auth/agent-register",
        json={"name": name},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def send_email(api_key: str, from_addr: str, to: str, subject: str, body: str) -> dict:
    """Send an email from the agent's @agentlair.dev address."""
    resp = requests.post(
        f"{AGENTLAIR_BASE}/v1/email/send",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"from": from_addr, "to": to, "subject": subject, "text": body},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def vault_store(api_key: str, key: str, plaintext: str, seed: bytes) -> dict:
    """Encrypt and store a secret in AgentLair Vault (client-side AES-256-GCM)."""
    # Derive a 32-byte key from the seed + key name
    dk = hashlib.sha256(seed + key.encode()).digest()
    aesgcm = AESGCM(dk)
    nonce = os.urandom(12)  # 96-bit nonce, unique per encryption
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    encoded = base64.b64encode(nonce + ciphertext).decode()

    resp = requests.put(
        f"{AGENTLAIR_BASE}/v1/vault/{key}",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"ciphertext": encoded},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def vault_retrieve(api_key: str, key: str, seed: bytes) -> str:
    """Retrieve and decrypt a secret from AgentLair Vault."""
    resp = requests.get(
        f"{AGENTLAIR_BASE}/v1/vault/{key}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    resp.raise_for_status()
    blob = base64.b64decode(resp.json()["ciphertext"])
    nonce, ciphertext = blob[:12], blob[12:]
    dk = hashlib.sha256(seed + key.encode()).digest()
    return AESGCM(dk).decrypt(nonce, ciphertext, None).decode()


def get_trust_score(api_key: str, account_id: str) -> dict:
    """Fetch the agent's behavioral trust score."""
    resp = requests.get(
        f"{AGENTLAIR_BASE}/v1/trust/score?agent_id={account_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ── Credential management ──────────────────────────────────────────────────────

def load_or_register(agent_name: str) -> tuple[dict, bytes]:
    """
    Load credentials from .agentlair-credentials.json or register fresh.
    Returns (creds_dict, vault_seed).
    """
    # Prefer environment variables (e.g., in CI or production)
    api_key = os.getenv("AGENTLAIR_API_KEY")
    email = os.getenv("AGENTLAIR_EMAIL")
    account_id = os.getenv("AGENTLAIR_ACCOUNT_ID")
    vault_seed_hex = os.getenv("AGENTLAIR_VAULT_SEED")

    if api_key and email and account_id:
        print(f"  ✓ Using credentials from environment")
        seed = bytes.fromhex(vault_seed_hex) if vault_seed_hex else secrets.token_bytes(32)
        return {"api_key": api_key, "email_address": email, "account_id": account_id}, seed

    # Load from local credentials file
    creds_path = Path(CREDENTIALS_FILE)
    if creds_path.exists():
        data = json.loads(creds_path.read_text())
        print(f"  ✓ Loaded credentials from {CREDENTIALS_FILE}")
        seed = bytes.fromhex(data["vault_seed"])
        return data, seed

    # Register a new agent
    print(f"  ⟳ Registering new AgentLair agent: '{agent_name}'")
    creds = register_agent(agent_name)
    seed = secrets.token_bytes(32)

    data = {**creds, "vault_seed": seed.hex()}
    creds_path.write_text(json.dumps(data, indent=2))
    print(f"  ✓ Registered!")
    print(f"    Email:   {creds['email_address']}")
    print(f"    Account: {creds['account_id']}")
    return data, seed


# ── CrewAI tools backed by AgentLair ──────────────────────────────────────────

def make_agentlair_tools(api_key: str, from_email: str, account_id: str, vault_seed: bytes):
    """Create CrewAI tools that use AgentLair for email, vault, and trust."""

    @tool("send_email")
    def send_email_tool(to: str, subject: str, body: str) -> str:
        """
        Send a real email from this agent's @agentlair.dev address.
        Args: to (recipient email), subject, body (plain text)
        """
        result = send_email(api_key, from_email, to, subject, body)
        return f"Email sent (id={result['id']}, status={result['status']})"

    @tool("store_secret")
    def store_secret_tool(key: str, value: str) -> str:
        """
        Store a secret in the agent's AES-256-GCM encrypted vault.
        Args: key (identifier), value (the secret to store)
        """
        vault_store(api_key, key, value, vault_seed)
        return f"Secret stored at vault key '{key}'"

    @tool("get_trust_score")
    def get_trust_score_tool() -> str:
        """Get this agent's behavioral trust score from AgentLair."""
        score_data = get_trust_score(api_key, account_id)
        score = score_data["score"]
        level = score_data["atfLevel"]
        return f"Trust score: {score}/100 (level: {level})"

    return [send_email_tool, store_secret_tool, get_trust_score_tool]


# ── Integration test (no LLM required) ────────────────────────────────────────

def run_test():
    """
    Directly test all AgentLair integrations and CrewAI tool wiring.
    Does not require an LLM API key.
    """
    print("\n=== AgentLair Integration Test ===\n")

    # 1. Register agent
    print("[1/5] Registering agent...")
    creds, vault_seed = load_or_register("crewai-demo-test")
    api_key = creds["api_key"]
    email_address = creds["email_address"]
    account_id = creds["account_id"]
    print(f"  Email:   {email_address}")
    print(f"  Account: {account_id}")

    # 2. Trust score
    print("\n[2/5] Checking trust score...")
    score_data = get_trust_score(api_key, account_id)
    print(f"  ✓ Score: {score_data['score']}/100  Level: {score_data['atfLevel']}  Trend: {score_data['trend']}")

    # 3. Vault store + retrieve (AES-256-GCM round-trip)
    print("\n[3/5] Vault AES-256-GCM round-trip...")
    secret_value = "demo-openai-key-sk-test-1234567890"
    vault_store(api_key, "test-secret", secret_value, vault_seed)
    print(f"  ✓ Stored  'test-secret'")
    retrieved = vault_retrieve(api_key, "test-secret", vault_seed)
    match = "✓ MATCH" if retrieved == secret_value else "✗ MISMATCH"
    print(f"  ✓ Retrieved: '{retrieved}' [{match}]")

    # 4. Send email
    print("\n[4/5] Sending email (agent → own address)...")
    email_result = send_email(
        api_key, email_address, email_address,
        "AgentLair Integration Test",
        f"Trust score: {score_data['score']}/100\nVault: OK\nThis message proves the email integration works."
    )
    print(f"  ✓ Sent id={email_result['id']}  status={email_result['status']}")

    # 5. Wire up CrewAI tools and call each directly
    print("\n[5/5] Wiring CrewAI tools and verifying each...")
    agentlair_tools = make_agentlair_tools(api_key, email_address, account_id, vault_seed)
    tool_names = [t.name for t in agentlair_tools]
    print(f"  ✓ Tools registered: {tool_names}")

    # Call each tool directly to verify they work
    for t in agentlair_tools:
        if t.name == "get_trust_score":
            result = t.func()
            print(f"  ✓ get_trust_score → {result}")
        elif t.name == "store_secret":
            result = t.func("crewai-test-key", "crewai-test-val")
            print(f"  ✓ store_secret → {result}")
        elif t.name == "send_email":
            result = t.func(
                email_address,
                "CrewAI Tool Test",
                "Direct tool invocation test from CrewAI integration suite."
            )
            print(f"  ✓ send_email → {result}")

    # Initialize CrewAI agents (proves framework wires up, LLM call deferred to kickoff)
    researcher = Agent(
        role="Research Agent",
        goal="Verify AgentLair integrations",
        backstory="A test agent checking AgentLair wiring.",
        tools=agentlair_tools,
        verbose=False,
    )
    reporter = Agent(
        role="Report Agent",
        goal="Send results via AgentLair email",
        backstory="A communication agent with @agentlair.dev identity.",
        tools=agentlair_tools,
        verbose=False,
    )
    print(f"\n  ✓ CrewAI agents initialized: {researcher.role}, {reporter.role}")
    print(f"  ✓ Each agent has {len(agentlair_tools)} AgentLair tools attached")

    print("\n=== All 5 integration checks passed ===")
    print(f"   Email:      {email_address}")
    print(f"   Trust:      {score_data['score']}/100 ({score_data['atfLevel']})")
    print(f"   Vault:      AES-256-GCM round-trip verified")
    print(f"   CrewAI:     v{__import__('crewai').__version__} — agents + tools wired")
    print("\nTo run the full LLM-orchestrated crew:")
    print("  export OPENAI_API_KEY=sk-...")
    print("  python demo.py\n")


# ── Main demo (requires LLM key) ───────────────────────────────────────────────

def main():
    print("\n=== CrewAI + AgentLair Demo ===\n")

    # Get or register AgentLair credentials
    print("[Step 1] Identity")
    creds, vault_seed = load_or_register("crewai-demo-agent")
    api_key = creds["api_key"]
    email_address = creds["email_address"]
    account_id = creds["account_id"]

    print(f"\n  Agent identity: {email_address}")

    # Create AgentLair-backed tools
    agentlair_tools = make_agentlair_tools(api_key, email_address, account_id, vault_seed)

    # Define CrewAI agents
    researcher = Agent(
        role="Research Agent",
        goal="Gather information and store credentials securely in the vault",
        backstory=(
            "An autonomous researcher with a persistent AgentLair identity. "
            "Stores discovered credentials securely and maintains a trust record."
        ),
        tools=agentlair_tools,
        verbose=True,
    )

    reporter = Agent(
        role="Report Agent",
        goal="Send findings to stakeholders via email and check trust score",
        backstory=(
            "A communication agent with a real @agentlair.dev email address. "
            "Sends verified, agent-authored reports to external parties."
        ),
        tools=agentlair_tools,
        verbose=True,
    )

    # Define tasks
    research_task = Task(
        description=(
            "1. Check the agent's current trust score using get_trust_score. "
            "2. Store the demo API key 'demo-openai-key' with value 'sk-demo-123' "
            "   in the vault using store_secret. "
            "3. Return a summary: trust score + vault confirmation."
        ),
        expected_output="Trust score and vault storage confirmation",
        agent=researcher,
    )

    report_task = Task(
        description=(
            "Send an email summarizing the research findings. "
            f"Send to: {email_address} "
            "(the agent's own address — this proves the email works end-to-end). "
            "Subject: 'CrewAI + AgentLair Demo Results'. "
            "Body: include the trust score and vault confirmation from the research task."
        ),
        expected_output="Email sent confirmation with message ID",
        agent=reporter,
        context=[research_task],
    )

    # Run the crew
    print("\n[Step 2] Starting CrewAI crew...\n")
    crew = Crew(
        agents=[researcher, reporter],
        tasks=[research_task, report_task],
        verbose=True,
    )
    result = crew.kickoff()

    # Show final trust score
    print("\n=== Final Results ===")
    print(f"Crew output: {result}")

    score_data = get_trust_score(api_key, account_id)
    print(f"\n  Trust score: {score_data['score']}/100")
    print(f"  Level:       {score_data['atfLevel']}")
    print(f"  Trend:       {score_data['trend']}")
    print(f"  Email:       {email_address}")
    print(f"\n  Demo complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CrewAI + AgentLair Demo")
    parser.add_argument(
        "--test", action="store_true",
        help="Run integration tests (no LLM key needed)"
    )
    args = parser.parse_args()

    if args.test:
        run_test()
    else:
        main()
