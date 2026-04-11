"""Managed Agent — Anthropic SDK v0.92.0+

One-time setup: creates agent + environment, prints IDs for Railway env vars.
Per-run: creates a session, sends a task, streams events until idle.

Correct SDK method paths (beta namespace):
  client.beta.environments.create()
  client.beta.agents.create()
  client.beta.sessions.create(agent=AGENT_ID, environment_id=ENV_ID)
  client.beta.sessions.events.send(session_id=..., events=[...])
  client.beta.sessions.stream(session_id=...)
  client.beta.sessions.events.list(session_id=...)
"""

import json
import os
import traceback
import anthropic


# ════════════════════════════════════════════════════════════════════════
#  AGENT SYSTEM PROMPT
# ════════════════════════════════════════════════════════════════════════

AGENT_SYSTEM_PROMPT = """You are the Corporate HQ Intelligence Agent for a Charlotte, NC barbershop operation.

You are talking to William, the owner. He charges $40-65 per cut and is building a competitive intelligence operation to prepare for expanding from a suite to a full shop.

YOUR ROLE:
- Answer questions about his business using real data
- Speak in plain, direct business language — no developer jargon, no corporate buzzwords
- If the data does not exist yet, say so honestly. Never make up numbers.
- Keep answers concise and actionable

YOUR OPERATOR:
- Solo barber, South Park suite (zip 28210), 10 years experience
- Current pricing: Fade $45, Skin Fade $55, Combo $65
- Annual gross: ~$42,000 — transitioning to full shop ownership
- Goal: Open a full barbershop with chair rentals targeting $75K-$120K/year

PRIORITY ZIP CODES (minority-serving Charlotte neighborhoods):
28216 (Beatties Ford), 28208 (West Charlotte), 28206 (North Charlotte),
28215 (Eastway/Shamrock), 28212 (East Charlotte), 28202 (Uptown),
28203 (South End), 28205 (Plaza Midwood/NoDa), 28217 (Steele Creek), 28269 (University)

You have access to bash, file tools, and web search in your container. Use them to gather real data and help William make informed business decisions."""


# ════════════════════════════════════════════════════════════════════════
#  ONE-TIME SETUP — run once, save the IDs to Railway env vars
# ════════════════════════════════════════════════════════════════════════

def setup_managed_agent():
    """Create the agent and environment once. Returns (agent_id, env_id, error).

    Run this once, then save the IDs as Railway env vars:
      CORPORATE_HQ_AGENT_ID=agent_...
      CORPORATE_HQ_ENV_ID=env_...
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None, None, "ANTHROPIC_API_KEY not set"

    client = anthropic.Anthropic(api_key=api_key)

    try:
        # 1. Create environment
        environment = client.beta.environments.create(
            name="corporate-hq-env",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        )
        env_id = environment.id

        # 2. Create agent (model, system, tools live here — NOT on the session)
        agent = client.beta.agents.create(
            name="Corporate HQ Agent",
            model="claude-sonnet-4-6",
            system=AGENT_SYSTEM_PROMPT,
            tools=[
                {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
            ],
        )
        agent_id = agent.id

        return agent_id, env_id, None

    except Exception as e:
        traceback.print_exc()
        return None, None, str(e)


# ════════════════════════════════════════════════════════════════════════
#  PER-RUN — called each time an agent task is triggered
# ════════════════════════════════════════════════════════════════════════

def run_agent_task(task: str, agent_id: str = None, env_id: str = None) -> dict:
    """Create a session, send the task, stream until idle, return the result.

    Args:
        task: The user message / task description to send.
        agent_id: Agent ID (falls back to CORPORATE_HQ_AGENT_ID env var).
        env_id: Environment ID (falls back to CORPORATE_HQ_ENV_ID env var).

    Returns:
        {"reply": "...", "mode": "managed"} on success
        {"error": "..."} on failure
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    agent_id = agent_id or os.environ.get("CORPORATE_HQ_AGENT_ID", "")
    env_id = env_id or os.environ.get("CORPORATE_HQ_ENV_ID", "")

    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured."}
    if not agent_id:
        return {"error": "CORPORATE_HQ_AGENT_ID not set. Run /api/setup-agent first."}
    if not env_id:
        return {"error": "CORPORATE_HQ_ENV_ID not set. Run /api/setup-agent first."}

    client = anthropic.Anthropic(api_key=api_key)

    try:
        # Create a new session for this task
        session = client.beta.sessions.create(
            agent=agent_id,
            environment_id=env_id,
        )

        # Stream-first: open stream, then send the task
        reply_parts = []

        with client.beta.sessions.stream(session_id=session.id) as stream:
            # Send the user message while the stream is open
            client.beta.sessions.events.send(
                session_id=session.id,
                events=[{
                    "type": "user.message",
                    "content": [{"type": "text", "text": task}],
                }],
            )

            for event in stream:
                if event.type == "agent.message":
                    for block in (event.content or []):
                        if hasattr(block, "text") and block.text:
                            reply_parts.append(block.text)
                elif event.type == "session.status_terminated":
                    break
                elif event.type == "session.status_idle":
                    # Only break on terminal stop reasons
                    if hasattr(event, "stop_reason") and event.stop_reason:
                        if getattr(event.stop_reason, "type", "") == "requires_action":
                            continue
                    break

        reply = "".join(reply_parts)
        if not reply:
            reply = "Agent completed the task but produced no text output."

        return {"reply": reply, "mode": "managed", "session_id": session.id}

    except Exception as e:
        traceback.print_exc()
        return {"error": f"Managed agent failed: {str(e)}"}


# ════════════════════════════════════════════════════════════════════════
#  CHAT SESSION — for the embedded chat widget (persistent session)
# ════════════════════════════════════════════════════════════════════════

def create_chat_session(agent_id: str = None, env_id: str = None) -> dict:
    """Create a managed agent session for the chat widget.

    Returns:
        {"session_id": "sess_...", "mode": "managed"} on success
        {"session_id": "local", "mode": "messages", "note": "..."} on fallback
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    agent_id = agent_id or os.environ.get("CORPORATE_HQ_AGENT_ID", "")
    env_id = env_id or os.environ.get("CORPORATE_HQ_ENV_ID", "")

    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured."}

    if not agent_id or not env_id:
        reason = []
        if not agent_id:
            reason.append("CORPORATE_HQ_AGENT_ID not set")
        if not env_id:
            reason.append("CORPORATE_HQ_ENV_ID not set")
        return {"session_id": "local", "mode": "messages", "note": "; ".join(reason)}

    client = anthropic.Anthropic(api_key=api_key)

    try:
        session = client.beta.sessions.create(
            agent=agent_id,
            environment_id=env_id,
        )
        return {"session_id": session.id, "mode": "managed"}

    except AttributeError as e:
        return {"session_id": "local", "mode": "messages",
                "note": f"SDK lacks managed agents API: {str(e)}"}
    except Exception as e:
        traceback.print_exc()
        return {"session_id": "local", "mode": "messages",
                "note": f"Managed agent failed: {str(e)}"}


def send_chat_message(session_id: str, user_message: str) -> dict:
    """Send a message to an existing managed agent chat session.

    Uses stream-first pattern: opens SSE stream, sends message, collects response.
    The agent toolset runs server-side — no custom tool handling needed.

    Returns:
        {"reply": "...", "mode": "managed"} on success
        {"error": "..."} on failure
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured."}

    client = anthropic.Anthropic(api_key=api_key)
    reply_parts = []

    try:
        with client.beta.sessions.stream(session_id=session_id) as stream:
            # Send message while stream is open (stream-first pattern)
            client.beta.sessions.events.send(
                session_id=session_id,
                events=[{
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_message}],
                }],
            )

            for event in stream:
                if event.type == "agent.message":
                    for block in (event.content or []):
                        if hasattr(block, "text") and block.text:
                            reply_parts.append(block.text)
                elif event.type == "session.status_terminated":
                    break
                elif event.type == "session.status_idle":
                    if hasattr(event, "stop_reason") and event.stop_reason:
                        if getattr(event.stop_reason, "type", "") == "requires_action":
                            continue
                    break

        reply = "".join(reply_parts)
        if not reply:
            reply = "I processed your request but had no text response. Try asking again."

        return {"reply": reply, "mode": "managed"}

    except Exception as e:
        traceback.print_exc()
        return {"error": f"Managed agent chat failed: {str(e)}"}
