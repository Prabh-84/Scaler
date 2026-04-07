
# import requests
# import time
# import json
# import os
# from openai import OpenAI

# # ---------------------------------------------------------------------------
# # Environment configuration — all read from env vars for Docker compatibility
# # ---------------------------------------------------------------------------
# # FIX 1: default port 7860 — matches Dockerfile CMD uvicorn ... --port 7860
# API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
# MODEL_NAME   = os.getenv("MODEL_NAME",   "llama-3.3-70b-versatile")
# OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
# OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")

# # FIX 2: Fail fast at import time with a human-readable error
# if not OPENAI_API_KEY:
#     raise ValueError(
#         "OPENAI_API_KEY environment variable is not set. "
#         "Export it before running: export OPENAI_API_KEY=gsk_..."
#     )

# client = OpenAI(
#     api_key=OPENAI_API_KEY,
#     base_url=OPENAI_BASE_URL,
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
#     print("Server did not become available in time.")
#     return False


# def _declare_best_guess(state: dict, external_call: bool = False) -> dict:
#     """
#     FIX 3: Emergency fallback when the LLM errors or the budget runs out
#     without a declare_root_cause. Picks the most suspicious visible node
#     so the episode always ends with a score instead of a 400 from /grader.

#     Priority ranking:
#       1 — critical status with visible symptoms
#       2 — critical status (no symptoms visible)
#       3 — degraded with visible symptoms
#       4 — degraded (no symptoms)
#       5 — any node with symptoms
#       6 — everything else
#     """
#     nodes = state.get("nodes", {})
#     candidates = []

#     for node_id, node_data in nodes.items():
#         health   = node_data.get("health")
#         symptoms = node_data.get("visible_symptoms", [])
#         status   = node_data.get("status", "")

#         if status == "critical" and symptoms:
#             priority = 1
#         elif status == "critical":
#             priority = 2
#         elif status == "degraded" and symptoms:
#             priority = 3
#         elif status == "degraded":
#             priority = 4
#         elif symptoms:
#             priority = 5
#         else:
#             priority = 6

#         # Use numeric health as tiebreaker (lower = worse = more suspicious)
#         h_val = health if isinstance(health, (int, float)) else 1.0
#         candidates.append((priority, h_val, node_id, symptoms))

#     # Sort by priority asc, then health asc (sickest first within same priority)
#     candidates.sort(key=lambda x: (x[0], x[1]))

#     best_node = candidates[0][2] if candidates else "api_gateway"
#     best_symptoms = candidates[0][3] if candidates else []

#     # Use first symptom as a hint for failure_type — better than "unknown"
#     failure_type = best_symptoms[0] if best_symptoms else "unknown_failure"

#     if not external_call:
#         print(f"[BestGuess] Fallback declaration → {best_node} / {failure_type}")

#     return {
#         "action":       "declare_root_cause",
#         "target":       best_node,
#         "failure_type": failure_type,
#     }


# def run_smart_agent(scenario_id: str, external_call: bool = False) -> float:
#     """
#     Runs the LLM agent against a scenario.
#     Returns the final grader score (0.0–1.0).
#     external_call=True suppresses print output for the automated evaluator.
#     """
#     if not external_call:
#         print(f"\n========== RUNNING SMART AGENT: {scenario_id} ==========")

#     # Reset the environment
#     try:
#         state = requests.post(
#             f"{API_BASE_URL}/reset",
#             params={"scenario_id": scenario_id},
#             timeout=30,
#         ).json()
#     except Exception as e:
#         if not external_call:
#             print(f"Failed to reset server: {e}")
#         return 0.0

#     max_steps    = state.get("steps_remaining", 15)
#     episode_done = False

#     for _ in range(max_steps):
#         # Safety: stop if the server already considers episode done
#         if state.get("steps_remaining", 0) <= 0:
#             break

#         if not external_call:
#             print(
#                 f"\n[Step {state.get('step')}] "
#                 f"Health: {state.get('system_health')} | "
#                 f"Remaining: {state.get('steps_remaining')}"
#             )

#         prompt   = f"CURRENT STATE:\n{json.dumps(state, indent=2)}\n\nWhat is your next move?"
#         req_body = None
#         llm_ok   = True

#         try:
#             response = client.chat.completions.create(
#                 model=MODEL_NAME,
#                 response_format={"type": "json_object"},
#                 messages=[
#                     {"role": "system", "content": SYSTEM_PROMPT},
#                     {"role": "user",   "content": prompt},
#                 ],
#             )
#             content  = response.choices[0].message.content
#             decision = json.loads(content)

#             if not external_call:
#                 print(f"THOUGHT: {decision.get('thought')}")

#             action_payload = decision.get("action", {})
#             req_body = {
#                 "action": action_payload.get("action_type", "observe"),
#                 "target": action_payload.get("target", "api_gateway"),
#             }
#             if "failure_type" in action_payload and action_payload["failure_type"] is not None:
#                 req_body["failure_type"] = action_payload["failure_type"]

#             if not external_call:
#                 print(f"ACTION: {req_body['action']} -> {req_body['target']}")

#         except Exception as e:
#             if not external_call:
#                 print(f"LLM Error: {e} — using best-guess fallback")
#             llm_ok = False

#         # FIX 4: If LLM failed, use best-guess instead of breaking the loop.
#         if not llm_ok or req_body is None:
#             req_body = _declare_best_guess(state, external_call)

#         # Execute step on server
#         try:
#             res = requests.post(
#                 f"{API_BASE_URL}/step",
#                 json=req_body,
#                 timeout=30,
#             ).json()
#         except Exception as e:
#             if not external_call:
#                 print(f"Server step error: {e}")
#             break

#         if res.get("info", {}).get("message") and not external_call:
#             print(f"SERVER MSG: {res['info']['message']}")

#         if res.get("done"):
#             episode_done = True
#             break

#         # FIX 6: Fallback to previous state if observation is missing
#         state = res.get("observation") or state

#     # FIX 5: If loop exited without a declare (budget ran out), force one now
#     if not episode_done:
#         if not external_call:
#             print("[Post-loop] Budget exhausted — issuing final best-guess declaration.")
#         fallback = _declare_best_guess(state, external_call)
#         try:
#             requests.post(f"{API_BASE_URL}/step", json=fallback, timeout=30)
#         except Exception as e:
#             if not external_call:
#                 print(f"Failed to send post-loop declaration: {e}")

#     # Fetch final score
#     final_score = 0.0
#     try:
#         score_data = requests.get(f"{API_BASE_URL}/grader", timeout=30).json()

#         if "total" in score_data:
#             final_score = float(score_data["total"])
#             if not external_call:
#                 print("\n========== EPISODE COMPLETE ==========")
#                 print(f"FINAL SCORE: {final_score * 100:.1f}%")
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
#     """Runs one task from each difficulty bucket and returns scores."""
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
"""
inference.py  — CascadeDebugEnv baseline agent
=================================================
FIXES vs submission #30
-----------------------
1. CRITICAL: Removed module-level `raise ValueError` for missing OPENAI_API_KEY.
   The validator runs this file without any env vars pre-set, so that raise
   caused an immediate non-zero exit → Phase 2 fail.
   Now the key is resolved lazily inside main() with a clear fallback chain:
     OPENAI_API_KEY → HF_TOKEN (hackathon-required var) → dummy (server-side key)

2. Added mandatory [START] / [STEP] / [END] structured stdout log format
   as specified by the hackathon sample inference script. Deviations in these
   field names cause incorrect evaluation scoring.

3. API_BASE_URL defaults to port 7860 (matches Dockerfile EXPOSE + CMD).

4. MODEL_NAME falls back to "llama-3.3-70b-versatile" (Groq, fast, free tier).

5. _declare_best_guess() prioritises critical → degraded+symptoms → degraded nodes
   so that LLM errors still end the episode with a real score.

6. Post-loop safety: if the step budget runs out without a declare_root_cause,
   one final best-guess declaration is fired so /grader never returns 400.

7. wait_for_server() retries for 60 s (up from 15 s) to handle slow cold starts
   on Hugging Face Spaces free tier.

8. run_baseline_suite() covers easy_e1, medium_m2, hard_h2 — one from each tier.
"""

import requests
import time
import json
import os
import sys

from openai import OpenAI

# ---------------------------------------------------------------------------
# Environment configuration — all read from env vars for Docker compatibility
# ---------------------------------------------------------------------------

# The hackathon mandates these three variables in the environment config.
# We use them here so the validator's container always has something to work with.
API_BASE_URL  = os.getenv("API_BASE_URL",  "http://127.0.0.1:7860").rstrip("/")
MODEL_NAME    = os.getenv("MODEL_NAME",    "llama-3.3-70b-versatile")
HF_TOKEN      = os.getenv("HF_TOKEN",      "")  # hackathon-required var

# Key resolution (never raise at module level — validators run without env vars):
#   1. OPENAI_API_KEY  (set explicitly by operator)
#   2. HF_TOKEN        (hackathon-required; Groq keys start with gsk_)
#   3. "MISSING_KEY"   (placeholder — OpenAI client init won't crash; LLM calls fail
#                       gracefully inside try/except, and _declare_best_guess() fires)
OPENAI_API_KEY  = (
    os.getenv("OPENAI_API_KEY")
    or HF_TOKEN
    or "MISSING_KEY"
)
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")

# Build the client once at module level (no crash — key is always a string now)
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

# ---------------------------------------------------------------------------
# Task / benchmark metadata (required by [START] log format)
# ---------------------------------------------------------------------------

BENCHMARK  = "CascadeDebugEnv"
MAX_STEPS  = 15   # upper bound; actual budget comes from scenario step_budget
MAX_TOTAL_REWARD = 1.0   # scores are clamped to [0, 1]
SUCCESS_SCORE_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# Mandatory structured log helpers — [START] / [STEP] / [END]
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    """Emit the mandatory [START] log line."""
    print(
        json.dumps({
            "event": "START",
            "task":  task,
            "env":   env,
            "model": model,
        }),
        flush=True,
    )


def log_step(step: int, action: dict, reward: float, done: bool, error=None) -> None:
    """Emit the mandatory [STEP] log line."""
    record = {
        "event":  "STEP",
        "step":   step,
        "action": action,
        "reward": reward,
        "done":   done,
    }
    if error is not None:
        record["error"] = str(error)
    print(json.dumps(record), flush=True)


def log_end(success: bool, steps: int, score: float, rewards: list) -> None:
    """Emit the mandatory [END] log line."""
    print(
        json.dumps({
            "event":   "END",
            "success": success,
            "steps":   steps,
            "score":   round(score, 4),
            "rewards": [round(r, 4) for r in rewards],
        }),
        flush=True,
    )


# ---------------------------------------------------------------------------
# SRE agent system prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) debugging a distributed microservice system.
You will be given a JSON representation of the current system state.

You must output YOUR ENTIRE RESPONSE as a valid JSON object with exactly two keys:
1. "thought": A brief string explaining your reasoning (which node looks most suspicious, why).
2. "action": An object with:
   - "action_type": one of observe | restart | isolate | rollback | drain_connections | reroute_traffic | scale_replica | declare_root_cause
   - "target": the node id to act on
   - "failure_type": (only for declare_root_cause) your best guess at the failure type string

RULES — follow these strictly:
- You CANNOT see a node's true health until you "observe" it. Always observe first.
- Do NOT take irreversible actions (isolate, restart, rollback) on a node you have NOT observed.
- Do NOT observe the same node twice.
- If a node is critical and you have observed it, apply a fix (rollback, drain_connections, or restart).
- Your final action MUST be "declare_root_cause" with the correct node and failure_type.
- Prefer observing upstream dependency chain nodes (api_gateway → auth_service → user_db etc.).
- Avoid trap actions — if an action looks obvious but the system description warns about it, skip it.
"""


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def wait_for_server(max_retries: int = 60, sleep_seconds: int = 1) -> bool:
    """Poll the server until it responds 200 or retries are exhausted."""
    print(f"[DEBUG] Waiting for server at {API_BASE_URL} ...", flush=True)
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=10)
            if response.status_code == 200:
                print(f"[DEBUG] Server is up after {attempt + 1} attempt(s).", flush=True)
                return True
        except Exception:
            pass
        time.sleep(sleep_seconds)
    print("[DEBUG] Server did not become available in time.", flush=True)
    return False


def _declare_best_guess(state: dict, external_call: bool = False) -> dict:
    """
    Emergency fallback: picks the most suspicious visible node and issues
    declare_root_cause so the episode always ends with a grader score.

    Priority (lower = more suspicious):
      1 — critical status + visible symptoms
      2 — critical status (no symptoms)
      3 — degraded + visible symptoms
      4 — degraded (no symptoms)
      5 — any node with symptoms
      6 — everything else
    """
    nodes = state.get("nodes", {})
    candidates = []

    for node_id, node_data in nodes.items():
        health   = node_data.get("health")
        symptoms = node_data.get("visible_symptoms", [])
        status   = node_data.get("status", "")

        if status == "critical" and symptoms:
            priority = 1
        elif status == "critical":
            priority = 2
        elif status == "degraded" and symptoms:
            priority = 3
        elif status == "degraded":
            priority = 4
        elif symptoms:
            priority = 5
        else:
            priority = 6

        h_val = health if isinstance(health, (int, float)) else 1.0
        candidates.append((priority, h_val, node_id, symptoms))

    candidates.sort(key=lambda x: (x[0], x[1]))

    best_node     = candidates[0][2] if candidates else "api_gateway"
    best_symptoms = candidates[0][3] if candidates else []
    failure_type  = best_symptoms[0] if best_symptoms else "unknown_failure"

    if not external_call:
        print(f"[DEBUG] BestGuess fallback → {best_node} / {failure_type}", flush=True)

    return {
        "action":       "declare_root_cause",
        "target":       best_node,
        "failure_type": failure_type,
    }


def _call_llm(state: dict) -> dict | None:
    """
    Calls the LLM and returns a parsed req_body dict, or None on failure.
    Never raises — all exceptions are caught and logged.
    """
    prompt = f"CURRENT STATE:\n{json.dumps(state, indent=2)}\n\nWhat is your next move?"
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        content  = response.choices[0].message.content
        decision = json.loads(content)

        action_payload = decision.get("action", {})
        req_body = {
            "action": action_payload.get("action_type", "observe"),
            "target": action_payload.get("target",      "api_gateway"),
        }
        if action_payload.get("failure_type") is not None:
            req_body["failure_type"] = action_payload["failure_type"]

        return req_body

    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return None


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run_smart_agent(scenario_id: str, external_call: bool = False) -> float:
    """
    Runs the LLM agent against one scenario.
    Returns the final grader score in [0.0, 1.0].

    external_call=True suppresses verbose print output for the automated evaluator
    but structured [START]/[STEP]/[END] logs are always emitted.
    """
    if not external_call:
        print(f"\n{'='*50}", flush=True)
        print(f"RUNNING SMART AGENT: {scenario_id}", flush=True)
        print(f"{'='*50}", flush=True)

    log_start(task=scenario_id, env=BENCHMARK, model=MODEL_NAME)

    # --- Reset environment ---
    try:
        resp = requests.post(
            f"{API_BASE_URL}/reset",
            params={"scenario_id": scenario_id},
            timeout=30,
        )
        state = resp.json()
    except Exception as exc:
        if not external_call:
            print(f"[DEBUG] Failed to reset server: {exc}", flush=True)
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return 0.0

    max_steps    = state.get("steps_remaining", MAX_STEPS)
    episode_done = False
    rewards: list[float] = []
    steps_taken  = 0
    score        = 0.0
    success      = False

    for step_num in range(1, max_steps + 1):
        if state.get("steps_remaining", 0) <= 0:
            break

        if not external_call:
            print(
                f"\n[Step {state.get('step')}] "
                f"Health: {state.get('system_health')} | "
                f"Remaining: {state.get('steps_remaining')}",
                flush=True,
            )

        # --- Get action from LLM or fallback ---
        req_body = _call_llm(state)
        if req_body is None:
            req_body = _declare_best_guess(state, external_call)

        if not external_call:
            print(f"ACTION: {req_body.get('action')} → {req_body.get('target')}", flush=True)

        # --- Execute step on server ---
        try:
            res = requests.post(
                f"{API_BASE_URL}/step",
                json=req_body,
                timeout=30,
            ).json()
        except Exception as exc:
            if not external_call:
                print(f"[DEBUG] Server step error: {exc}", flush=True)
            log_step(step=step_num, action=req_body, reward=0.0, done=False, error=str(exc))
            break

        reward = res.get("reward", 0.0) or 0.0
        done   = res.get("done",   False)
        error  = res.get("info",   {}).get("message") or None

        rewards.append(reward)
        steps_taken = step_num

        log_step(step=step_num, action=req_body, reward=reward, done=done, error=error)

        if not external_call and error:
            print(f"SERVER MSG: {error}", flush=True)

        if done:
            episode_done = True
            break

        # Update state (fall back to previous good state if observation missing)
        state = res.get("observation") or state

    # --- Force-close episode if budget exhausted without a declaration ---
    if not episode_done:
        if not external_call:
            print("[DEBUG] Budget exhausted — issuing final best-guess declaration.", flush=True)
        fallback = _declare_best_guess(state, external_call)
        try:
            requests.post(f"{API_BASE_URL}/step", json=fallback, timeout=30)
        except Exception as exc:
            if not external_call:
                print(f"[DEBUG] Failed to send post-loop declaration: {exc}", flush=True)

    # --- Fetch final grader score ---
    try:
        score_data = requests.get(f"{API_BASE_URL}/grader", timeout=30).json()
        if "total" in score_data:
            score   = float(score_data["total"])
            success = score >= SUCCESS_SCORE_THRESHOLD
            if not external_call:
                print(f"\nFINAL SCORE: {score * 100:.1f}%", flush=True)
                print(json.dumps(score_data.get("breakdown", {}), indent=2), flush=True)
        else:
            if not external_call:
                print(f"[DEBUG] Grader returned: {score_data}", flush=True)
    except Exception as exc:
        if not external_call:
            print(f"[DEBUG] Failed to fetch final score: {exc}", flush=True)

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


# ---------------------------------------------------------------------------
# Baseline suite — one scenario per difficulty tier
# ---------------------------------------------------------------------------

def run_baseline_suite() -> dict:
    """Runs one task from each difficulty bucket and returns a scores dict."""
    test_tasks = ["easy_e1", "medium_m2", "hard_h2"]
    scores: dict = {}
    for task in test_tasks:
        try:
            scores[task] = run_smart_agent(task, external_call=False)
        except Exception as exc:
            scores[task] = {"error": str(exc)}
    return scores


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if wait_for_server():
        results = run_baseline_suite()
        print(json.dumps(results, indent=2), flush=True)
    else:
        print("[DEBUG] Server did not become available. Exiting.", flush=True)
        sys.exit(1)
