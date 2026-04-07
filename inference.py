
# """
# inference.py — CascadeDebugEnv baseline agent

# HACKATHON VALIDATOR REQUIREMENTS:
#   [x] API_BASE_URL  — LiteLLM proxy URL (for LLM calls ONLY)
#   [x] API_KEY       — LiteLLM proxy key  (validator injects this — MUST use)
#   [x] MODEL_NAME    — model name with default
#   [x] HF_TOKEN      — present, no default (checklist rule)
#   [x] LOCAL_IMAGE_NAME — optional
#   [x] OpenAI client uses base_url=API_BASE_URL and api_key=API_KEY
#   [x] ENV_SERVER_URL — local env server (http://localhost:7860), NEVER the LLM proxy
#   [x] [START] / [STEP] / [END] plain-text stdout logs, flush=True
#   [x] No hardcoded keys or provider URLs

# CRITICAL FIX (Phase 2 failure root cause):
#   Previous submissions used API_BASE_URL for BOTH LLM calls AND env server
#   calls (/reset, /step, /grader). The validator injects API_BASE_URL as the
#   LiteLLM proxy URL — routing /reset and /step there means the proxy never
#   sees any LLM completions requests, so last_active is never updated.

#   Fix: env server calls go to ENV_SERVER_URL (localhost:7860).
#        LLM calls go to API_BASE_URL (the LiteLLM proxy). These are separate.
# """

# import requests
# import time
# import json
# import os
# import sys

# from openai import OpenAI

# # ---------------------------------------------------------------------------
# # Environment configuration
# # Validator injects: API_BASE_URL (LiteLLM proxy), API_KEY, MODEL_NAME
# # ---------------------------------------------------------------------------

# # LiteLLM proxy — ALL LLM calls MUST go here so the validator records them
# API_BASE_URL = os.environ["API_BASE_URL"].rstrip("/")
# API_KEY      = os.environ["API_KEY"]

# MODEL_NAME       = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
# HF_TOKEN         = os.getenv("HF_TOKEN")           # required by checklist, no default
# LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")   # optional, from_docker_image()

# # Local env server — /reset, /step, /grader go HERE, not to the LLM proxy
# # The container's own FastAPI app runs on port 7860 (HF Space default)
# ENV_SERVER_URL = os.getenv("ENV_SERVER_URL", "http://localhost:7860").rstrip("/")

# # ---------------------------------------------------------------------------
# # OpenAI client — MUST point at API_BASE_URL (the LiteLLM proxy)
# # This is what the validator tracks to confirm LLM calls were made
# # ---------------------------------------------------------------------------
# client = OpenAI(
#     api_key=API_KEY,
#     base_url=API_BASE_URL,
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
#     """Poll the LOCAL env server until 200 OK or retries exhausted."""
#     print(f"[INFO] Waiting for env server at {ENV_SERVER_URL} ...", flush=True)
#     for attempt in range(max_retries):
#         try:
#             r = requests.get(f"{ENV_SERVER_URL}/", timeout=10)
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
#     Calls the LLM through the OpenAI client pointed at API_BASE_URL.
#     This is the validator's LiteLLM proxy — these calls are what it tracks.
#     Returns a parsed req_body dict ready for POST /step, or None on failure.
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

#     Env calls  → ENV_SERVER_URL  (local FastAPI server, e.g. localhost:7860)
#     LLM calls  → API_BASE_URL    (validator's LiteLLM proxy, via `client`)
#     """
#     log_start(task=scenario_id, env=BENCHMARK, model=MODEL_NAME)

#     # --- Reset the environment (LOCAL env server) ---
#     try:
#         resp  = requests.post(
#             f"{ENV_SERVER_URL}/reset",
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

#         # --- Get action from LLM (calls LiteLLM proxy) or fall back ---
#         req_body = _call_llm(state)
#         if req_body is None:
#             req_body = _best_guess_action(state)

#         action_label = req_body.get("action", "unknown")
#         target       = req_body.get("target", "")
#         if target:
#             action_label = f"{action_label}:{target}"

#         # --- Execute step on LOCAL env server ---
#         try:
#             res = requests.post(
#                 f"{ENV_SERVER_URL}/step",
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
#             requests.post(f"{ENV_SERVER_URL}/step", json=fallback, timeout=30)
#         except Exception as exc:
#             print(f"[WARN] Failed to send fallback declaration: {exc}", flush=True)

#     # --- Fetch final grader score from LOCAL env server ---
#     try:
#         score_data = requests.get(f"{ENV_SERVER_URL}/grader", timeout=30).json()
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

HACKATHON VALIDATOR REQUIREMENTS:
  [x] API_BASE_URL  — LiteLLM proxy (LLM calls ONLY). Has default.
  [x] API_KEY       — validator-injected. No fallback. Required.
  [x] MODEL_NAME    — model name with default.
  [x] HF_TOKEN      — present, no default (checklist rule).
  [x] LOCAL_IMAGE_NAME — optional.
  [x] OpenAI client: base_url=API_BASE_URL, api_key=API_KEY.
  [x] ENV_SERVER_URL — local FastAPI server. NEVER the LLM proxy.
  [x] [START]/[STEP]/[END] on stdout ONLY. All diagnostics → stderr.
  [x] No hardcoded keys or provider URLs.

STDOUT FORMAT — exact spec:
  [START] task=<name> env=<benchmark> model=<model>
  [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>
"""

import requests
import time
import json
import os
import sys

from openai import OpenAI

# ---------------------------------------------------------------------------
# Config — validator injects API_BASE_URL, API_KEY, MODEL_NAME
# ---------------------------------------------------------------------------
API_BASE_URL     = os.environ["API_BASE_URL"].rstrip("/")
API_KEY          = os.environ["API_KEY"]
MODEL_NAME       = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
HF_TOKEN         = os.getenv("HF_TOKEN")            # required by checklist, no default
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")    # optional
ENV_SERVER_URL   = os.getenv("ENV_SERVER_URL", "http://localhost:7860").rstrip("/")

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

BENCHMARK               = "CascadeDebugEnv"
SUCCESS_SCORE_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# Formatting helpers — spec-exact output
# ---------------------------------------------------------------------------

def _b(x: bool) -> str:
    return "true" if x else "false"

def _f(x: float) -> str:
    return f"{float(x):.2f}"

def _e(v) -> str:
    if v is None or v == "":
        return "null"
    return str(v).replace("\n", " ").strip()

# ---------------------------------------------------------------------------
# Structured log emitters — stdout ONLY
# Diagnostics (INFO/WARN/ERROR) → stderr so stdout stays spec-clean
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error=None) -> None:
    print(
        f"[STEP] step={step} action={action} reward={_f(reward)} "
        f"done={_b(done)} error={_e(error)}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: list) -> None:
    rstr = ",".join(_f(r) for r in rewards)
    print(
        f"[END] success={_b(success)} steps={steps} "
        f"score={_f(score)} rewards={rstr}",
        flush=True,
    )

def _info(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stderr, flush=True)

def _warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr, flush=True)

def _err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)

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
    _info(f"Waiting for env server at {ENV_SERVER_URL} ...")
    for attempt in range(max_retries):
        try:
            r = requests.get(f"{ENV_SERVER_URL}/", timeout=10)
            if r.status_code == 200:
                _info(f"Server ready after {attempt + 1} attempt(s).")
                return True
        except Exception:
            pass
        time.sleep(sleep_seconds)
    _warn("Env server did not become available in time.")
    return False


def _best_guess_action(state: dict) -> dict:
    nodes = state.get("nodes", {})
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
    _info(f"Best-guess fallback → {best_node} / {failure_type}")
    return {"action": "declare_root_cause", "target": best_node, "failure_type": failure_type}


def _call_llm(state: dict) -> dict | None:
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
        _warn(f"LLM call failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Main agent loop — one scenario
# ---------------------------------------------------------------------------

def run_smart_agent(scenario_id: str) -> float:
    log_start(task=scenario_id, env=BENCHMARK, model=MODEL_NAME)

    # Reset — env server only
    try:
        resp = requests.post(
            f"{ENV_SERVER_URL}/reset",
            params={"scenario_id": scenario_id},
            timeout=30,
        )
        resp.raise_for_status()
        state = resp.json()
    except Exception as exc:
        _err(f"Failed to reset env for {scenario_id}: {exc}")
        log_end(success=False, steps=0, score=0.0, rewards=[])
        return 0.0

    max_steps    = state.get("steps_remaining", 15)
    episode_done = False
    steps_taken  = 0
    score        = 0.0
    rewards      = []          # accumulates per-step rewards for [END] rewards=

    for step_num in range(1, max_steps + 1):
        if state.get("steps_remaining", 0) <= 0:
            break

        # LLM call → API_BASE_URL (what validator tracks)
        req_body = _call_llm(state)
        if req_body is None:
            req_body = _best_guess_action(state)

        action_label = req_body.get("action", "unknown")
        target       = req_body.get("target", "")
        if target:
            action_label = f"{action_label}:{target}"

        # Step — env server only
        try:
            res = requests.post(
                f"{ENV_SERVER_URL}/step",
                json=req_body,
                timeout=30,
            )
            res.raise_for_status()
            res = res.json()
        except Exception as exc:
            _err(f"/step failed: {exc}")
            rewards.append(0.0)
            log_step(step=step_num, action=action_label, reward=0.0, done=False, error=str(exc))
            break

        reward      = float(res.get("reward", 0.0) or 0.0)
        done        = bool(res.get("done", False))
        steps_taken = step_num
        rewards.append(reward)

        # Extract error — tries both common env response shapes
        error = (res.get("info") or {}).get("last_action_error") or res.get("error")

        log_step(step=step_num, action=action_label, reward=reward, done=done, error=error)

        if done:
            episode_done = True
            break

        state = res.get("observation") or state

    # Budget exhausted — force a final declaration and log it
    if not episode_done:
        _info("Budget exhausted — sending final best-guess declaration.")
        fallback = _best_guess_action(state)
        action_label = f"{fallback['action']}:{fallback['target']}"
        try:
            res = requests.post(f"{ENV_SERVER_URL}/step", json=fallback, timeout=30)
            res.raise_for_status()
            res = res.json()
            reward = float(res.get("reward", 0.0) or 0.0)
            done   = bool(res.get("done", False))
            error  = (res.get("info") or {}).get("last_action_error") or res.get("error")
        except Exception as exc:
            _warn(f"Failed to send fallback declaration: {exc}")
            reward, done, error = 0.0, False, str(exc)
        steps_taken += 1
        rewards.append(reward)
        log_step(step=steps_taken, action=action_label, reward=reward, done=done, error=error)

    # Grader score — env server only
    try:
        gr = requests.get(f"{ENV_SERVER_URL}/grader", timeout=30)
        gr.raise_for_status()
        score_data = gr.json()
        if "total" in score_data:
            score = float(score_data["total"])
        _info(f"Grader result: {json.dumps(score_data)}")
        # Use grader's own success flag if available; fallback to threshold
        success = bool(score_data.get("success", score >= SUCCESS_SCORE_THRESHOLD))
    except Exception as exc:
        _warn(f"Failed to fetch grader score: {exc}")
        success = score >= SUCCESS_SCORE_THRESHOLD

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


# ---------------------------------------------------------------------------
# Baseline suite — one scenario per difficulty tier
# ---------------------------------------------------------------------------

def run_baseline_suite() -> dict:
    results: dict = {}
    for task in ["easy_e1", "medium_m2", "hard_h2"]:
        try:
            results[task] = run_smart_agent(task)
        except Exception as exc:
            _err(f"{task} raised: {exc}")
            results[task] = 0.0
    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if wait_for_server():
        run_baseline_suite()
        # summary goes to stderr — stdout must stay clean for the parser
        _info("Baseline suite complete.")
    else:
        _err("Env server unavailable. Exiting.")
        sys.exit(1)