

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