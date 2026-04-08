
import requests
import time
import json
import os
from openai import OpenAI

# FIX 2: Read from env var so Docker runs use the right port without code changes
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:7860")

# FIX 1: Guard against None assignment — raises clear error at startup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable is not set. "
        "Export it before running: export OPENAI_API_KEY=gsk_..."
    )

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) debugging a distributed system.
You will be given a JSON representation of the system state.
You must output YOUR ENTIRE RESPONSE as a valid JSON object with exactly two keys:
1. "thought": A brief string explaining your reasoning based on dependencies and symptoms.
2. "action": An object containing "action_type", "target", and optionally "failure_type".

Available actions: observe, restart, isolate, rollback, drain_connections, reroute_traffic, scale_replica, declare_root_cause.

RULES:
- You cannot see a node's true health until you 'observe' it. DO THIS FIRST.
- Do NOT take irreversible actions (isolate, restart, rollback) on a node you haven't observed.
- DO NOT observe the same node multiple times.
- Once you observe the suspicious upstream node, you MUST execute a fix (like drain_connections, rollback, or restart).
- If you find the issue and fix it, the final action must be 'declare_root_cause' with the node and failure_type.
"""


def wait_for_server():
    print(f"Waiting for OpenEnv server at {SERVER_URL} ...")
    for _ in range(10):
        try:
            if requests.get(f"{SERVER_URL}/", timeout=5).status_code == 200:
                print("Server is up!")
                return True
        except Exception:  # FIX 3: explicit Exception, not bare except
            time.sleep(1)
    print("Server did not become available.")
    return False


def run_smart_agent(scenario_id: str, external_call: bool = False) -> float:
    """
    Runs the LLM agent against a scenario.
    external_call=True mutes print statements for automated evaluators.
    NOTE: for automated / Docker evaluation use inference.py instead —
    it has the full fallback logic. This file is for local interactive use.
    """
    if not external_call:
        print(f"\n========== RUNNING SMART AGENT: {scenario_id} ==========")

    try:
        state = requests.post(
            f"{SERVER_URL}/reset",
            params={"scenario_id": scenario_id},
            timeout=30,
        ).json()
    except Exception as e:
        if not external_call:
            print(f"Failed to reset server: {e}")
        return 0.0

    max_steps = state.get("steps_remaining", 15)

    for _ in range(max_steps):
        if not external_call:
            print(
                f"\n[Step {state.get('step')}] "
                f"Health: {state.get('system_health')} | "
                f"Remaining: {state.get('steps_remaining')}"
            )

        prompt = f"CURRENT STATE:\n{json.dumps(state, indent=2)}\n\nWhat is your next move?"

        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
            )
            decision = json.loads(response.choices[0].message.content)

            if not external_call:
                print(f"THOUGHT: {decision.get('thought')}")

            action_payload = decision.get("action", {})
            req_body = {
                "action": action_payload.get("action_type", "observe"),
                "target": action_payload.get("target", "api_gateway"),
            }
            if "failure_type" in action_payload and action_payload["failure_type"] is not None:
                req_body["failure_type"] = action_payload["failure_type"]

            if not external_call:
                print(f"ACTION: {req_body['action']} -> {req_body['target']}")

        except Exception as e:
            if not external_call:
                print(f"LLM Error: {e}")
            # FIX 4: Don't silently break — continue to next iteration
            # (inference.py handles a proper best-guess fallback for automated runs)
            continue

        try:
            res = requests.post(
                f"{SERVER_URL}/step",
                json=req_body,
                timeout=30,
            ).json()
        except Exception as e:
            if not external_call:
                print(f"Server step error: {e}")
            break

        if res.get("info", {}).get("message") and not external_call:
            print(f"SERVER MSG: {res['info']['message']}")

        if res.get("done"):
            break

        state = res.get("observation") or state

    # Fetch final score
    final_score = 0.0
    try:
        score_data = requests.get(f"{SERVER_URL}/grader", timeout=30).json()

        if "total" in score_data:
            final_score = score_data["total"]
            if not external_call:
                print("\n========== EPISODE COMPLETE ==========")
                print(f"FINAL SCORE: {final_score * 100:.1f}%")
                print(json.dumps(score_data.get("breakdown", {}), indent=2))
        else:
            if not external_call:
                print(f"\nEpisode ended early. Server returned: {score_data}")

    except Exception as e:
        if not external_call:
            print(f"Failed to fetch final score: {e}")

    return final_score


if __name__ == "__main__":
    if wait_for_server():
        run_smart_agent("medium_m2")
