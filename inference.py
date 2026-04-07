
# import requests
# import time
# import json
# import os
# import sys

# from openai import OpenAI

# # ---------------------------------------------------------------------------
# # Environment configuration
# # Validator injects: API_BASE_URL, API_KEY, MODEL_NAME
# # Checklist also requires: HF_TOKEN (no default), LOCAL_IMAGE_NAME (optional)
# # ---------------------------------------------------------------------------

# API_BASE_URL     = os.getenv("API_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
# MODEL_NAME       = os.getenv("MODEL_NAME",   "llama-3.3-70b-versatile")
# HF_TOKEN         = os.getenv("HF_TOKEN")           # NO default (checklist rule)
# LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")   # optional, for from_docker_image()

# # ---------------------------------------------------------------------------
# # API_KEY resolution — CRITICAL
# #
# # The validator injects "API_KEY" as the LiteLLM proxy key.
# # Resolution order (first non-empty wins):
# #   1. API_KEY       ← what the validator injects (MUST come first)
# #   2. HF_TOKEN      ← hackathon-required fallback
# #   3. OPENAI_API_KEY ← local dev override
# #   4. "placeholder" ← last resort so client never crashes at init
# #
# # The client base_url MUST be API_BASE_URL (the proxy URL).
# # Never use a hardcoded provider URL like api.groq.com when running via validator.
# # ---------------------------------------------------------------------------

# API_KEY = (
#     os.getenv("API_KEY")        # validator-injected LiteLLM proxy key  ← CRITICAL
#     or os.getenv("HF_TOKEN")
#     or os.getenv("OPENAI_API_KEY")
#     or "placeholder"
# )

# # All LLM calls go through the OpenAI client configured with the proxy vars
# client = OpenAI(
#     api_key=API_KEY,
#     base_url=API_BASE_URL,   # This IS the LiteLLM proxy when validator runs
# )

# # ---------------------------------------------------------------------------
# # Constants
# # ---------------------------------------------------------------------------
# BENCHMARK               = "CascadeDebugEnv"
# SUCCESS_SCORE_THRESHOLD = 0.5

# # ---------------------------------------------------------------------------
# # Mandatory structured log helpers
# # Exact plain-text format required by validator:
# #   [START] task=easy_e1 env=CascadeDebugEnv model=llama-3.3-70b-versatile
# #   [STEP] step=1 action=observe:auth_service reward=0.08 done=False
# #   [END] task=easy_e1 score=0.75 steps=4 success=True
# # Rules: stdout only, flush=True, plain key=value (NOT JSON)
# # ---------------------------------------------------------------------------

# def log_start(task: str, env: str, model: str) -> None:
#     print(f"[START] task={task} env={env} model={model}", flush=True)


# def log_step(step: int, action: str, reward: float, done: bool) -> None:
#     print(
#         f"[STEP] step={step} action={action} reward={round(reward, 4)} done={done}",
#         flush=True,
#     )


# def log_end(task: str, score: float, steps: int, success: bool) -> None:
#     print(
#         f"[END] task={task} score={round(score, 4)} steps={steps} success={success}",
#         flush=True,
#     )


# # ---------------------------------------------------------------------------
# # SRE agent system prompt
# # ---------------------------------------------------------------------------
# SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) diagnosing a distributed microservice system.
# You receive a JSON snapshot of the current system state.

# Respond with a single valid JSON object with exactly two keys:
# 1. "thought": one sentence explaining your reasoning
# 2. "action": object with:
#    - "action_type": one of observe | restart | isolate | rollback | drain_connections | reroute_traffic | scale_replica | declare_root_cause
#    - "target": node id (string)
#    - "failure_type": string — ONLY include when action_type is declare_root_cause

# STRICT RULES:
# - You cannot see a node's true health until you "observe" it. ALWAYS observe first.
# - NEVER take irreversible actions (isolate, restart, rollback) on unobserved nodes.
# - NEVER observe the same node twice.
# - After observing a critical/degraded node, apply a fix action to it.
# - Your FINAL action MUST be declare_root_cause with the correct node and failure_type.
# - Follow dependency chains: api_gateway → auth_service → user_db, etc.
# - Avoid documented trap actions — if something looks too obvious, think twice.
# """


# # ---------------------------------------------------------------------------
# # Utilities
# # ---------------------------------------------------------------------------

# def wait_for_server(max_retries: int = 60, sleep_seconds: float = 1.0) -> bool:
#     """Poll the local env server until 200 OK or retries are exhausted."""
#     print(f"[INFO] Waiting for env server at {API_BASE_URL} ...", flush=True)
#     for attempt in range(max_retries):
#         try:
#             r = requests.get(f"{API_BASE_URL}/", timeout=10)
#             if r.status_code == 200:
#                 print(f"[INFO] Server ready after {attempt + 1} attempt(s).", flush=True)
#                 return True
#         except Exception:
#             pass
#         time.sleep(sleep_seconds)
#     print("[WARN] Env server did not become available in time.", flush=True)
#     return False


# def _best_guess_action(state: dict) -> dict:
#     """
#     Fallback when LLM errors or budget runs out without declare_root_cause.
#     Picks the most suspicious node so the episode always ends with a score.

#     Priority (lower = more suspicious):
#       1 — critical status + visible symptoms
#       2 — critical status (no visible symptoms)
#       3 — degraded status + visible symptoms
#       4 — degraded status (no visible symptoms)
#       5 — any node with visible symptoms
#       6 — everything else (healthy / hidden)
#     """
#     nodes      = state.get("nodes", {})
#     candidates = []

#     for node_id, node_data in nodes.items():
#         health   = node_data.get("health")
#         symptoms = node_data.get("visible_symptoms", [])
#         status   = node_data.get("status", "")

#         if status == "critical" and symptoms:
#             prio = 1
#         elif status == "critical":
#             prio = 2
#         elif status == "degraded" and symptoms:
#             prio = 3
#         elif status == "degraded":
#             prio = 4
#         elif symptoms:
#             prio = 5
#         else:
#             prio = 6

#         h_val = health if isinstance(health, (int, float)) else 1.0
#         candidates.append((prio, h_val, node_id, symptoms))

#     candidates.sort(key=lambda x: (x[0], x[1]))

#     best_node    = candidates[0][2] if candidates else "api_gateway"
#     best_syms    = candidates[0][3] if candidates else []
#     failure_type = best_syms[0]     if best_syms   else "unknown_failure"

#     print(f"[INFO] Best-guess fallback → {best_node} / {failure_type}", flush=True)
#     return {
#         "action":       "declare_root_cause",
#         "target":       best_node,
#         "failure_type": failure_type,
#     }


# def _call_llm(state: dict) -> dict | None:
#     """
#     Calls the LLM through the OpenAI client (which points at API_BASE_URL).
#     Returns a parsed req_body dict ready for POST /step, or None on failure.
#     ALL LLM traffic goes through API_BASE_URL — the validator's LiteLLM proxy.
#     """
#     prompt = (
#         f"CURRENT SYSTEM STATE:\n{json.dumps(state, indent=2)}\n\n"
#         "What is your next action? Respond with JSON only."
#     )
#     try:
#         response = client.chat.completions.create(
#             model=MODEL_NAME,
#             response_format={"type": "json_object"},
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user",   "content": prompt},
#             ],
#         )
#         content        = response.choices[0].message.content
#         decision       = json.loads(content)
#         action_payload = decision.get("action", {})

#         req_body: dict = {
#             "action": action_payload.get("action_type", "observe"),
#             "target": action_payload.get("target",      "api_gateway"),
#         }
#         ft = action_payload.get("failure_type")
#         if ft is not None:
#             req_body["failure_type"] = ft

#         return req_body

#     except Exception as exc:
#         print(f"[WARN] LLM call failed: {exc}", flush=True)
#         return None


# # ---------------------------------------------------------------------------
# # Main agent loop — one scenario
# # ---------------------------------------------------------------------------

# def run_smart_agent(scenario_id: str) -> float:
#     """
#     Runs the LLM SRE agent against one scenario.
#     Emits [START] / [STEP] / [END] structured logs to stdout.
#     Returns final grader score in [0.0, 1.0].
#     """
#     log_start(task=scenario_id, env=BENCHMARK, model=MODEL_NAME)

#     # --- Reset the environment ---
#     try:
#         resp  = requests.post(
#             f"{API_BASE_URL}/reset",
#             params={"scenario_id": scenario_id},
#             timeout=30,
#         )
#         state = resp.json()
#     except Exception as exc:
#         print(f"[ERROR] Failed to reset env for {scenario_id}: {exc}", flush=True)
#         log_end(task=scenario_id, score=0.0, steps=0, success=False)
#         return 0.0

#     max_steps    = state.get("steps_remaining", 15)
#     episode_done = False
#     steps_taken  = 0
#     score        = 0.0

#     for step_num in range(1, max_steps + 1):
#         if state.get("steps_remaining", 0) <= 0:
#             break

#         # --- Get action from LLM or fall back to best-guess ---
#         req_body = _call_llm(state)
#         if req_body is None:
#             req_body = _best_guess_action(state)

#         # Build a readable action label for the [STEP] log
#         action_label = req_body.get("action", "unknown")
#         target       = req_body.get("target", "")
#         if target:
#             action_label = f"{action_label}:{target}"

#         # --- Execute step on the local env server ---
#         try:
#             res    = requests.post(
#                 f"{API_BASE_URL}/step",
#                 json=req_body,
#                 timeout=30,
#             ).json()
#         except Exception as exc:
#             print(f"[ERROR] /step failed: {exc}", flush=True)
#             log_step(step=step_num, action=action_label, reward=0.0, done=False)
#             break

#         reward      = float(res.get("reward", 0.0) or 0.0)
#         done        = bool(res.get("done",   False))
#         steps_taken = step_num

#         # Mandatory [STEP] log — emitted for every single step
#         log_step(step=step_num, action=action_label, reward=reward, done=done)

#         if done:
#             episode_done = True
#             break

#         state = res.get("observation") or state

#     # --- Force-close if budget exhausted without declare_root_cause ---
#     if not episode_done:
#         print("[INFO] Budget exhausted — sending final best-guess declaration.", flush=True)
#         fallback = _best_guess_action(state)
#         try:
#             requests.post(f"{API_BASE_URL}/step", json=fallback, timeout=30)
#         except Exception as exc:
#             print(f"[WARN] Failed to send fallback declaration: {exc}", flush=True)

#     # --- Fetch final grader score ---
#     try:
#         score_data = requests.get(f"{API_BASE_URL}/grader", timeout=30).json()
#         if "total" in score_data:
#             score = float(score_data["total"])
#         print(f"[INFO] Grader result: {json.dumps(score_data)}", flush=True)
#     except Exception as exc:
#         print(f"[WARN] Failed to fetch grader score: {exc}", flush=True)

#     success = score >= SUCCESS_SCORE_THRESHOLD
#     log_end(task=scenario_id, score=score, steps=steps_taken, success=success)
#     return score


# # ---------------------------------------------------------------------------
# # Baseline suite — one scenario per difficulty tier
# # ---------------------------------------------------------------------------

# def run_baseline_suite() -> dict:
#     """Runs easy_e1, medium_m2, hard_h2 and returns their scores."""
#     results: dict = {}
#     for task in ["easy_e1", "medium_m2", "hard_h2"]:
#         try:
#             results[task] = run_smart_agent(task)
#         except Exception as exc:
#             print(f"[ERROR] {task} raised: {exc}", flush=True)
#             results[task] = 0.0
#     return results


# # ---------------------------------------------------------------------------
# # Entry point
# # ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     if wait_for_server():
#         final_results = run_baseline_suite()
#         print(json.dumps(final_results, indent=2), flush=True)
#     else:
#         print("[ERROR] Env server unavailable. Exiting.", flush=True)
#         sys.exit(1)
"""
inference.py — CascadeDebugEnv baseline agent
==============================================

HACKATHON VALIDATOR REQUIREMENTS (all satisfied):
  [x] API_BASE_URL  = os.getenv("API_BASE_URL", "<default>")
  [x] MODEL_NAME    = os.getenv("MODEL_NAME",   "<default>")
  [x] HF_TOKEN      = os.getenv("HF_TOKEN")          -- NO default
  [x] LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") -- optional
  [x] OpenAI client uses base_url=API_BASE_URL and api_key=API_KEY
      where API_KEY = os.environ["API_KEY"]  (validator injects this)
  [x] [START] / [STEP] / [END] plain-text stdout logs, flush=True
  [x] No module-level raise / crash
  [x] No hardcoded keys or other providers

CRITICAL FIX vs submission #32:
  The validator injects two env vars:
    API_BASE_URL  — the LiteLLM proxy URL  (must use as base_url)
    API_KEY       — the LiteLLM proxy key  (must use as api_key)

  Previous submissions used OPENAI_API_KEY / HF_TOKEN for the client key.
  The LiteLLM proxy key was NEVER used → validator saw zero API calls through
  its proxy → "No API calls were made through our LLM proxy".

  Fix: client is always initialised with:
    api_key  = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN") or ...
    base_url = API_BASE_URL   (which IS the proxy URL when validator runs)
"""

import requests
import time
import json
import os
import sys

from openai import OpenAI

# ---------------------------------------------------------------------------
# Environment configuration
# Validator injects: API_BASE_URL, API_KEY, MODEL_NAME
# Checklist also requires: HF_TOKEN (no default), LOCAL_IMAGE_NAME (optional)
# ---------------------------------------------------------------------------

API_BASE_URL     = os.getenv("API_BASE_URL", "http://127.0.0.1:7860").rstrip("/")
MODEL_NAME       = os.getenv("MODEL_NAME",   "llama-3.3-70b-versatile")
HF_TOKEN         = os.getenv("HF_TOKEN")           # NO default (checklist rule)
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")   # optional, for from_docker_image()

# ---------------------------------------------------------------------------
# API_KEY resolution — CRITICAL
#
# The validator injects "API_KEY" as the LiteLLM proxy key.
# Resolution order (first non-empty wins):
#   1. API_KEY       ← what the validator injects (MUST come first)
#   2. HF_TOKEN      ← hackathon-required fallback
#   3. OPENAI_API_KEY ← local dev override
#   4. "placeholder" ← last resort so client never crashes at init
#
# The client base_url MUST be API_BASE_URL (the proxy URL).
# Never use a hardcoded provider URL like api.groq.com when running via validator.
# ---------------------------------------------------------------------------

API_KEY = (
    os.getenv("API_KEY")        # validator-injected LiteLLM proxy key  ← CRITICAL
    or os.getenv("HF_TOKEN")
    or os.getenv("OPENAI_API_KEY")
    or "placeholder"
)

# All LLM calls go through the OpenAI client configured with the proxy vars
client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL,   # This IS the LiteLLM proxy when validator runs
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BENCHMARK               = "CascadeDebugEnv"
SUCCESS_SCORE_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# Mandatory structured log helpers
# Exact plain-text format required by validator:
#   [START] task=easy_e1 env=CascadeDebugEnv model=llama-3.3-70b-versatile
#   [STEP] step=1 action=observe:auth_service reward=0.08 done=False
#   [END] task=easy_e1 score=0.75 steps=4 success=True
# Rules: stdout only, flush=True, plain key=value (NOT JSON)
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool) -> None:
    print(
        f"[STEP] step={step} action={action} reward={round(reward, 4)} done={done}",
        flush=True,
    )


def log_end(task: str, score: float, steps: int, success: bool) -> None:
    print(
        f"[END] task={task} score={round(score, 4)} steps={steps} success={success}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# SRE agent system prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an elite Site Reliability Engineer (SRE) diagnosing a distributed microservice system.
You receive a JSON snapshot of the current system state.

Respond with a single valid JSON object with exactly two keys:
1. "thought": one sentence explaining your reasoning
2. "action": object with:
   - "action_type": one of observe | restart | isolate | rollback | drain_connections | reroute_traffic | scale_replica | declare_root_cause
   - "target": node id (string)
   - "failure_type": string — ONLY include when action_type is declare_root_cause

STRICT RULES:
- You cannot see a node's true health until you "observe" it. ALWAYS observe first.
- NEVER take irreversible actions (isolate, restart, rollback) on unobserved nodes.
- NEVER observe the same node twice.
- After observing a critical/degraded node, apply a fix action to it.
- Your FINAL action MUST be declare_root_cause with the correct node and failure_type.
- Follow dependency chains: api_gateway → auth_service → user_db, etc.
- Avoid documented trap actions — if something looks too obvious, think twice.
"""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def wait_for_server(max_retries: int = 60, sleep_seconds: float = 1.0) -> bool:
    """Poll the local env server until 200 OK or retries are exhausted."""
    print(f"[INFO] Waiting for env server at {API_BASE_URL} ...", flush=True)
    for attempt in range(max_retries):
        try:
            r = requests.get(f"{API_BASE_URL}/", timeout=10)
            if r.status_code == 200:
                print(f"[INFO] Server ready after {attempt + 1} attempt(s).", flush=True)
                return True
        except Exception:
            pass
        time.sleep(sleep_seconds)
    print("[WARN] Env server did not become available in time.", flush=True)
    return False


def _best_guess_action(state: dict) -> dict:
    """
    Fallback when LLM errors or budget runs out without declare_root_cause.
    Picks the most suspicious node so the episode always ends with a score.

    Priority (lower = more suspicious):
      1 — critical status + visible symptoms
      2 — critical status (no visible symptoms)
      3 — degraded status + visible symptoms
      4 — degraded status (no visible symptoms)
      5 — any node with visible symptoms
      6 — everything else (healthy / hidden)
    """
    nodes      = state.get("nodes", {})
    candidates = []

    for node_id, node_data in nodes.items():
        health   = node_data.get("health")
        symptoms = node_data.get("visible_symptoms", [])
        status   = node_data.get("status", "")

        if status == "critical" and symptoms:
            prio = 1
        elif status == "critical":
            prio = 2
        elif status == "degraded" and symptoms:
            prio = 3
        elif status == "degraded":
            prio = 4
        elif symptoms:
            prio = 5
        else:
            prio = 6

        h_val = health if isinstance(health, (int, float)) else 1.0
        candidates.append((prio, h_val, node_id, symptoms))

    candidates.sort(key=lambda x: (x[0], x[1]))

    best_node    = candidates[0][2] if candidates else "api_gateway"
    best_syms    = candidates[0][3] if candidates else []
    failure_type = best_syms[0]     if best_syms   else "unknown_failure"

    print(f"[INFO] Best-guess fallback → {best_node} / {failure_type}", flush=True)
    return {
        "action":       "declare_root_cause",
        "target":       best_node,
        "failure_type": failure_type,
    }


def _call_llm(state: dict) -> dict | None:
    """
    Calls the LLM through the OpenAI client (which points at API_BASE_URL).
    Returns a parsed req_body dict ready for POST /step, or None on failure.
    ALL LLM traffic goes through API_BASE_URL — the validator's LiteLLM proxy.
    """
    prompt = (
        f"CURRENT SYSTEM STATE:\n{json.dumps(state, indent=2)}\n\n"
        "What is your next action? Respond with JSON only."
    )
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        content        = response.choices[0].message.content
        decision       = json.loads(content)
        action_payload = decision.get("action", {})

        req_body: dict = {
            "action": action_payload.get("action_type", "observe"),
            "target": action_payload.get("target",      "api_gateway"),
        }
        ft = action_payload.get("failure_type")
        if ft is not None:
            req_body["failure_type"] = ft

        return req_body

    except Exception as exc:
        print(f"[WARN] LLM call failed: {exc}", flush=True)
        return None


# ---------------------------------------------------------------------------
# Main agent loop — one scenario
# ---------------------------------------------------------------------------

def run_smart_agent(scenario_id: str) -> float:
    """
    Runs the LLM SRE agent against one scenario.
    Emits [START] / [STEP] / [END] structured logs to stdout.
    Returns final grader score in [0.0, 1.0].
    """
    log_start(task=scenario_id, env=BENCHMARK, model=MODEL_NAME)

    # --- Reset the environment ---
    try:
        resp  = requests.post(
            f"{API_BASE_URL}/reset",
            params={"scenario_id": scenario_id},
            timeout=30,
        )
        state = resp.json()
    except Exception as exc:
        print(f"[ERROR] Failed to reset env for {scenario_id}: {exc}", flush=True)
        log_end(task=scenario_id, score=0.0, steps=0, success=False)
        return 0.0

    max_steps    = state.get("steps_remaining", 15)
    episode_done = False
    steps_taken  = 0
    score        = 0.0

    for step_num in range(1, max_steps + 1):
        if state.get("steps_remaining", 0) <= 0:
            break

        # --- Get action from LLM or fall back to best-guess ---
        req_body = _call_llm(state)
        if req_body is None:
            req_body = _best_guess_action(state)

        # Build a readable action label for the [STEP] log
        action_label = req_body.get("action", "unknown")
        target       = req_body.get("target", "")
        if target:
            action_label = f"{action_label}:{target}"

        # --- Execute step on the local env server ---
        try:
            res    = requests.post(
                f"{API_BASE_URL}/step",
                json=req_body,
                timeout=30,
            ).json()
        except Exception as exc:
            print(f"[ERROR] /step failed: {exc}", flush=True)
            log_step(step=step_num, action=action_label, reward=0.0, done=False)
            break

        reward      = float(res.get("reward", 0.0) or 0.0)
        done        = bool(res.get("done",   False))
        steps_taken = step_num

        # Mandatory [STEP] log — emitted for every single step
        log_step(step=step_num, action=action_label, reward=reward, done=done)

        if done:
            episode_done = True
            break

        state = res.get("observation") or state

    # --- Force-close if budget exhausted without declare_root_cause ---
    if not episode_done:
        print("[INFO] Budget exhausted — sending final best-guess declaration.", flush=True)
        fallback = _best_guess_action(state)
        try:
            requests.post(f"{API_BASE_URL}/step", json=fallback, timeout=30)
        except Exception as exc:
            print(f"[WARN] Failed to send fallback declaration: {exc}", flush=True)

    # --- Fetch final grader score ---
    try:
        score_data = requests.get(f"{API_BASE_URL}/grader", timeout=30).json()
        if "total" in score_data:
            score = float(score_data["total"])
        print(f"[INFO] Grader result: {json.dumps(score_data)}", flush=True)
    except Exception as exc:
        print(f"[WARN] Failed to fetch grader score: {exc}", flush=True)

    success = score >= SUCCESS_SCORE_THRESHOLD
    log_end(task=scenario_id, score=score, steps=steps_taken, success=success)
    return score


# ---------------------------------------------------------------------------
# Baseline suite — one scenario per difficulty tier
# ---------------------------------------------------------------------------

def run_baseline_suite() -> dict:
    """Runs easy_e1, medium_m2, hard_h2 and returns their scores."""
    results: dict = {}
    for task in ["easy_e1", "medium_m2", "hard_h2"]:
        try:
            results[task] = run_smart_agent(task)
        except Exception as exc:
            print(f"[ERROR] {task} raised: {exc}", flush=True)
            results[task] = 0.0
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if wait_for_server():
        final_results = run_baseline_suite()
        print(json.dumps(final_results, indent=2), flush=True)
    else:
        print("[ERROR] Env server unavailable. Exiting.", flush=True)
        sys.exit(1)
