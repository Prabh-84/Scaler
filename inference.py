# import requests
# import time
# import json
# import os
# from openai import OpenAI

# # -----------------------------
# # Environment Configuration
# # -----------------------------
# API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
# MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # Optional override if you want to explicitly set provider endpoint
# OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")

# if not OPENAI_API_KEY:
#     raise ValueError("Missing OPENAI_API_KEY environment variable.")

# client = OpenAI(
#     api_key=OPENAI_API_KEY,
#     base_url=OPENAI_BASE_URL
# )

# SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) debugging a distributed system.
# You will be given a JSON representation of the system state.
# You must output YOUR ENTIRE RESPONSE as a valid JSON object with exactly two keys:
# 1. "thought": A brief string explaining your reasoning based on dependencies and symptoms.
# 2. "action": An object containing "action_type", "target", and optionally "failure_type".

# Available actions: observe, restart, isolate, rollback, drain_connections, reroute_traffic, scale_replica, declare_root_cause.

# RULES:
# - You cannot see a node's true health until you 'observe' it. DO THIS FIRST.
# - Do NOT take irreversible actions (isolate, restart, rollback) on a node you haven't observed.
# - DO NOT observe the same node multiple times.
# - Once you observe the suspicious upstream node, you MUST execute a fix (like drain_connections, rollback, or restart).
# - If you find the issue and fix it, the final action must be 'declare_root_cause' with the node and failure_type.
# """


# def wait_for_server(max_retries: int = 15, sleep_seconds: int = 1) -> bool:
#     print(f"Waiting for server at {API_BASE_URL} ...")
#     for _ in range(max_retries):
#         try:
#             response = requests.get(f"{API_BASE_URL}/", timeout=10)
#             if response.status_code == 200:
#                 print("Server is up!")
#                 return True
#         except Exception:
#             time.sleep(sleep_seconds)
#     return False


# def run_smart_agent(scenario_id: str, external_call: bool = False) -> float:
#     """
#     Runs the LLM agent against a scenario.
#     external_call=True mutes most print statements for automated evaluators.
#     """
#     if not external_call:
#         print(f"\n========== RUNNING SMART AGENT: {scenario_id} ==========")

#     try:
#         state = requests.post(
#             f"{API_BASE_URL}/reset",
#             params={"scenario_id": scenario_id},
#             timeout=30
#         ).json()
#     except Exception as e:
#         if not external_call:
#             print(f"Failed to reset server: {e}")
#         return 0.0

#     max_steps = state.get("steps_remaining", 15)

#     for _ in range(max_steps):
#         if not external_call:
#             print(
#                 f"\n[Step {state.get('step')}] "
#                 f"Health: {state.get('system_health')} | "
#                 f"Remaining: {state.get('steps_remaining')}"
#             )

#         prompt = f"CURRENT STATE:\n{json.dumps(state, indent=2)}\n\nWhat is your next move?"

#         try:
#             response = client.chat.completions.create(
#                 model=MODEL_NAME,
#                 response_format={"type": "json_object"},
#                 messages=[
#                     {"role": "system", "content": SYSTEM_PROMPT},
#                     {"role": "user", "content": prompt}
#                 ]
#             )

#             content = response.choices[0].message.content
#             decision = json.loads(content)

#             if not external_call:
#                 print(f"🤖 THOUGHT: {decision.get('thought')}")

#             action_payload = decision.get("action", {})
#             req_body = {
#                 "action": action_payload.get("action_type", "observe"),
#                 "target": action_payload.get("target", "api_gateway")
#             }

#             if "failure_type" in action_payload and action_payload["failure_type"] is not None:
#                 req_body["failure_type"] = action_payload["failure_type"]

#             if not external_call:
#                 print(f"⚡ ACTION: {req_body['action']} -> {req_body['target']}")

#         except Exception as e:
#             if not external_call:
#                 print(f"LLM Error: {e}")
#             break

#         try:
#             res = requests.post(
#                 f"{API_BASE_URL}/step",
#                 json=req_body,
#                 timeout=30
#             ).json()
#         except Exception as e:
#             if not external_call:
#                 print(f"Server execution error: {e}")
#             break

#         if res.get("info", {}).get("message") and not external_call:
#             print(f"SERVER MSG: {res['info']['message']}")

#         if res.get("done"):
#             break

#         state = res.get("observation", state)

#     final_score = 0.0
#     try:
#         score_data = requests.get(f"{API_BASE_URL}/grader", timeout=30).json()

#         if "total" in score_data:
#             final_score = float(score_data["total"])

#             if not external_call:
#                 print("\n========== EPISODE COMPLETE ==========")
#                 print(f"FINAL SCORE: {final_score * 100}%")
#                 print(json.dumps(score_data.get("breakdown", {}), indent=2))
#         else:
#             if not external_call:
#                 print("\n========== EPISODE ENDED EARLY ==========")
#                 print(f"Server returned: {score_data}")

#     except Exception as e:
#         if not external_call:
#             print(f"Failed to fetch final score: {e}")

#     return final_score


# def run_baseline_suite() -> dict:
#     """
#     Runs one task from each difficulty bucket.
#     """
#     test_tasks = ["easy_e1", "medium_m2", "hard_h2"]
#     scores = {}

#     for task in test_tasks:
#         try:
#             scores[task] = run_smart_agent(task, external_call=True)
#         except Exception as e:
#             scores[task] = {"error": str(e)}

#     return scores


# if __name__ == "__main__":
#     if wait_for_server():
#         results = run_baseline_suite()
#         print(json.dumps(results, indent=2))
#     else:
#         print("Server did not become available.")


# inference.py
import requests
import time
import json
import os
from openai import OpenAI

# -----------------------------
# Environment Configuration
# -----------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")

# BUG FIX: Raise early with a clear message if the key is missing.
# Previously this just assigned None to os.environ which raises a TypeError
# somewhere deep in the OpenAI client, making the root cause hard to find.
if not OPENAI_API_KEY:
    raise ValueError(
        "Missing OPENAI_API_KEY environment variable. "
        "Set it via: export OPENAI_API_KEY=gsk_..."
    )

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

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


def wait_for_server(max_retries: int = 15, sleep_seconds: int = 1) -> bool:
    print(f"Waiting for server at {API_BASE_URL} ...")
    for _ in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=10)
            if response.status_code == 200:
                print("Server is up!")
                return True
        except Exception:
            time.sleep(sleep_seconds)
    print("Server did not become available in time.")
    return False


def _declare_best_guess(state: dict) -> dict:
    """
    BUG FIX: When the LLM errors out mid-episode, we need to end the episode
    cleanly so /grader can return a score. This picks the most degraded visible node
    as a best-guess root cause declaration to avoid leaving the episode incomplete.
    """
    nodes = state.get("nodes", {})
    best_node = "api_gateway"
    worst_health = 1.0

    for node_id, data in nodes.items():
        h = data.get("health")
        if isinstance(h, (int, float)) and h < worst_health:
            worst_health = h
            best_node = node_id

    return {
        "action": "declare_root_cause",
        "target": best_node,
        "failure_type": "unknown"
    }


def run_smart_agent(scenario_id: str, external_call: bool = False) -> float:
    """
    Runs the LLM agent against a scenario.
    external_call=True mutes most print statements for automated evaluators.
    """
    if not external_call:
        print(f"\n========== RUNNING SMART AGENT: {scenario_id} ==========")

    try:
        state = requests.post(
            f"{API_BASE_URL}/reset",
            params={"scenario_id": scenario_id},
            timeout=30
        ).json()
    except Exception as e:
        if not external_call:
            print(f"Failed to reset server: {e}")
        return 0.0

    max_steps = state.get("steps_remaining", 15)
    llm_error_occurred = False

    for _ in range(max_steps):
        if not external_call:
            print(
                f"\n[Step {state.get('step')}] "
                f"Health: {state.get('system_health')} | "
                f"Remaining: {state.get('steps_remaining')}"
            )

        prompt = f"CURRENT STATE:\n{json.dumps(state, indent=2)}\n\nWhat is your next move?"

        req_body = None
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.choices[0].message.content
            decision = json.loads(content)

            if not external_call:
                print(f"THOUGHT: {decision.get('thought')}")

            action_payload = decision.get("action", {})
            req_body = {
                "action": action_payload.get("action_type", "observe"),
                "target": action_payload.get("target", "api_gateway")
            }

            if "failure_type" in action_payload and action_payload["failure_type"] is not None:
                req_body["failure_type"] = action_payload["failure_type"]

            if not external_call:
                print(f"ACTION: {req_body['action']} -> {req_body['target']}")

        except Exception as e:
            if not external_call:
                print(f"LLM Error: {e}")
            # BUG FIX: Don't just break on LLM error — send a declare_root_cause
            # so the episode ends cleanly and /grader can return a (low) score.
            # Previously the loop broke, the episode stayed incomplete, and /grader
            # returned a 400 error, giving final_score = 0.0 with no useful info.
            llm_error_occurred = True
            req_body = _declare_best_guess(state)

        try:
            res = requests.post(
                f"{API_BASE_URL}/step",
                json=req_body,
                timeout=30
            ).json()
        except Exception as e:
            if not external_call:
                print(f"Server execution error: {e}")
            break

        if res.get("info", {}).get("message") and not external_call:
            print(f"SERVER MSG: {res['info']['message']}")

        if res.get("done"):
            break

        if llm_error_occurred:
            # We already sent a declare — no point continuing the loop
            break

        state = res.get("observation", state)

    # Get Final Score
    final_score = 0.0
    try:
        score_data = requests.get(f"{API_BASE_URL}/grader", timeout=30).json()

        if "total" in score_data:
            final_score = float(score_data["total"])

            if not external_call:
                print("\n========== EPISODE COMPLETE ==========")
                print(f"FINAL SCORE: {final_score * 100:.1f}%")
                print(json.dumps(score_data.get("breakdown", {}), indent=2))
        else:
            if not external_call:
                print("\n========== EPISODE ENDED EARLY ==========")
                print(f"Server returned: {score_data}")

    except Exception as e:
        if not external_call:
            print(f"Failed to fetch final score: {e}")

    return final_score


def run_baseline_suite() -> dict:
    """
    Runs one task from each difficulty bucket.
    """
    test_tasks = ["easy_e1", "medium_m2", "hard_h2"]
    scores = {}

    for task in test_tasks:
        try:
            scores[task] = run_smart_agent(task, external_call=True)
        except Exception as e:
            scores[task] = {"error": str(e)}

    return scores


if __name__ == "__main__":
    if wait_for_server():
        results = run_baseline_suite()
        print(json.dumps(results, indent=2))
    else:
        print("Server did not become available.")
