

# from fastapi import FastAPI, HTTPException
# from typing import Optional
# import json
# import os
# import sys
# import threading

# ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# if ROOT_DIR not in sys.path:
#     sys.path.append(ROOT_DIR)

# from models import Action, StepResponse, Observation
# from server.cascade_debug_env_environment import CascadeDebugEnvironment

# app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# # ---------------------------------------------------------------------------
# # Scenario loading — raise at startup if broken, so container exits cleanly
# # ---------------------------------------------------------------------------

# def load_scenarios() -> dict:
#     scenarios: dict = {}
#     preferred_dirs = [
#         os.path.join(ROOT_DIR, "scenarios"),
#         "/app/scenarios",
#     ]
#     scenario_dir = next((d for d in preferred_dirs if os.path.isdir(d)), None)

#     if scenario_dir is None:
#         raise FileNotFoundError(f"No scenarios dir found. Tried: {preferred_dirs}")

#     for fname in sorted(os.listdir(scenario_dir)):
#         if not fname.endswith(".json"):
#             continue
#         fpath = os.path.join(scenario_dir, fname)
#         with open(fpath, "r", encoding="utf-8") as f:
#             data = json.load(f)
#         sid = data.get("scenario_id")
#         if not sid:
#             raise ValueError(f"Missing 'scenario_id' in {fname}")
#         scenarios[sid] = data

#     if not scenarios:
#         raise ValueError(f"No scenario JSON files found in: {scenario_dir}")
#     return scenarios


# SCENARIOS: dict = load_scenarios()

# _env_lock:  threading.Lock                        = threading.Lock()
# active_env: Optional[CascadeDebugEnvironment]     = None


# # ---------------------------------------------------------------------------
# # Intermediate reward shaping
# # ---------------------------------------------------------------------------

# def compute_intermediate_reward(env: CascadeDebugEnvironment, action: Action) -> float:
#     """
#     Shaped reward signal computed BEFORE executing the action.
#     Terminal step reward is replaced by the final grader total.
#     """
#     reward = 0.0

#     if action.action == "observe":
#         if action.target in env.state.nodes:
#             node = env.state.nodes[action.target]
#             reward += 0.08 if not node.get("observable", True) else -0.02

#     elif action.action in {"restart", "rollback", "drain_connections", "reroute_traffic"}:
#         reward += 0.05

#     elif action.action == "scale_replica":
#         reward += 0.02

#     elif action.action == "isolate":
#         reward += 0.03

#     elif action.action == "declare_root_cause":
#         reward -= 0.05  # mild penalty to discourage premature declarations

#     # Penalise documented trap actions
#     try:
#         gt = env.scenario_dict.get("ground_truth", {})
#         for trap in gt.get("trap_actions", []):
#             if (
#                 isinstance(trap, dict)
#                 and trap.get("action") == action.action
#                 and trap.get("target") == action.target
#             ):
#                 reward -= 0.15
#                 break
#     except Exception:
#         pass

#     return round(reward, 4)


# # ---------------------------------------------------------------------------
# # Endpoints
# # ---------------------------------------------------------------------------

# @app.get("/")
# def health_check():
#     return {
#         "status": "ok",
#         "cwd": os.getcwd(),
#         "base_dir": ROOT_DIR,
#         "scenario_count": len(SCENARIOS),
#         "loaded_scenarios": sorted(SCENARIOS.keys()),
#     }


# @app.get("/tasks")
# def get_tasks():
#     if not SCENARIOS:
#         raise HTTPException(status_code=500, detail="No scenarios loaded.")
#     return {
#         "tasks": sorted(SCENARIOS.keys()),
#         "action_schema": Action.model_json_schema(),
#     }


# @app.get("/schema")
# def get_schema():
#     return {
#         "action_schema":      Action.model_json_schema(),
#         "observation_schema": Observation.model_json_schema(),
#     }


# @app.post("/reset", response_model=Observation)
# def reset(scenario_id: Optional[str] = None):
#     """
#     Initialises the environment.
#     Bare POST /reset (no query param) defaults to easy_e1 — never 422s the validator.
#     """
#     global active_env
#     if not SCENARIOS:
#         raise HTTPException(status_code=500, detail="No scenarios loaded.")
#     if not scenario_id or scenario_id not in SCENARIOS:
#         scenario_id = "easy_e1"
#     try:
#         with _env_lock:
#             active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
#             return active_env.get_observation()
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Failed to init '{scenario_id}': {exc}")


# @app.get("/state", response_model=Observation)
# def get_state():
#     global active_env
#     with _env_lock:
#         if active_env is None:
#             raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
#         try:
#             return active_env.get_observation()
#         except Exception as exc:
#             raise HTTPException(status_code=500, detail=f"State error: {exc}")


# @app.post("/step", response_model=StepResponse)
# def step(req: Action):
#     """
#     Executes one action.
#     Intermediate reward on non-terminal steps; final grader total on terminal steps.
#     """
#     global active_env
#     with _env_lock:
#         if active_env is None:
#             raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
#         try:
#             reward = compute_intermediate_reward(active_env, req)
#             result = active_env.step(req.action, req.target, req.failure_type)

#             if result.get("done"):
#                 try:
#                     score_data = active_env.get_score()
#                     if isinstance(score_data, dict):
#                         reward = float(score_data.get("total", 0.0))
#                 except Exception:
#                     reward = 0.0

#             return {
#                 "observation": result.get("observation"),
#                 "reward":      reward,
#                 "done":        result.get("done", False),
#                 "info":        {"message": result.get("message", "")},
#             }
#         except Exception as exc:
#             raise HTTPException(status_code=500, detail=f"Step failed: {exc}")


# @app.get("/grader")
# def get_score():
#     """Returns the final score breakdown. Only valid after done=True."""
#     global active_env
#     with _env_lock:
#         if active_env is None:
#             raise HTTPException(status_code=400, detail="No active episode.")
#         try:
#             if not active_env.state.done:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="Episode not complete. Declare root cause or exhaust step budget.",
#                 )
#             return active_env.get_score()
#         except HTTPException:
#             raise
#         except Exception as exc:
#             raise HTTPException(status_code=500, detail=f"Grader error: {exc}")


# @app.get("/baseline")
# def run_baseline():
#     """Runs baseline LLM agent on easy/medium/hard and returns scores."""
#     try:
#         from inference import run_smart_agent
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=f"Import inference.py failed: {exc}")

#     scores: dict = {}
#     for task in ["easy_e1", "medium_m2", "hard_h2"]:
#         try:
#             scores[task] = run_smart_agent(task)
#         except Exception as exc:
#             scores[task] = {"error": str(exc)}
#     return {"baseline_scores": scores}
"""
app.py — root-level FastAPI server (Dockerfile entry point)

This is the OpenEnv-compatible HTTP server for CascadeDebugEnv.
The validator pings this server at the HF Space URL.
inference.py talks to THIS server via API_BASE_URL for env calls (reset/step/grader).
LLM calls in inference.py go to API_BASE_URL which the validator redirects
through its LiteLLM proxy.
"""

from fastapi import FastAPI, HTTPException
from typing import Optional
import json
import os
import sys
import threading

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from models import Action, StepResponse, Observation
from server.cascade_debug_env_environment import CascadeDebugEnvironment

app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# ---------------------------------------------------------------------------
# Scenario loading — raise at startup if broken, so container exits cleanly
# ---------------------------------------------------------------------------

def load_scenarios() -> dict:
    scenarios: dict = {}
    preferred_dirs = [
        os.path.join(ROOT_DIR, "scenarios"),
        "/app/scenarios",
    ]
    scenario_dir = next((d for d in preferred_dirs if os.path.isdir(d)), None)

    if scenario_dir is None:
        raise FileNotFoundError(f"No scenarios dir found. Tried: {preferred_dirs}")

    for fname in sorted(os.listdir(scenario_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(scenario_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        sid = data.get("scenario_id")
        if not sid:
            raise ValueError(f"Missing 'scenario_id' in {fname}")
        scenarios[sid] = data

    if not scenarios:
        raise ValueError(f"No scenario JSON files found in: {scenario_dir}")
    return scenarios


SCENARIOS: dict = load_scenarios()

_env_lock:  threading.Lock                        = threading.Lock()
active_env: Optional[CascadeDebugEnvironment]     = None


# ---------------------------------------------------------------------------
# Intermediate reward shaping
# ---------------------------------------------------------------------------

def compute_intermediate_reward(env: CascadeDebugEnvironment, action: Action) -> float:
    """
    Shaped reward signal computed BEFORE executing the action.
    Terminal step reward is replaced by the final grader total.
    """
    reward = 0.0

    if action.action == "observe":
        if action.target in env.state.nodes:
            node = env.state.nodes[action.target]
            reward += 0.08 if not node.get("observable", True) else -0.02

    elif action.action in {"restart", "rollback", "drain_connections", "reroute_traffic"}:
        reward += 0.05

    elif action.action == "scale_replica":
        reward += 0.02

    elif action.action == "isolate":
        reward += 0.03

    elif action.action == "declare_root_cause":
        reward -= 0.05  # mild penalty to discourage premature declarations

    # Penalise documented trap actions
    try:
        gt = env.scenario_dict.get("ground_truth", {})
        for trap in gt.get("trap_actions", []):
            if (
                isinstance(trap, dict)
                and trap.get("action") == action.action
                and trap.get("target") == action.target
            ):
                reward -= 0.15
                break
    except Exception:
        pass

    return round(reward, 4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "cwd": os.getcwd(),
        "base_dir": ROOT_DIR,
        "scenario_count": len(SCENARIOS),
        "loaded_scenarios": sorted(SCENARIOS.keys()),
    }


@app.get("/tasks")
def get_tasks():
    if not SCENARIOS:
        raise HTTPException(status_code=500, detail="No scenarios loaded.")
    return {
        "tasks": sorted(SCENARIOS.keys()),
        "action_schema": Action.model_json_schema(),
    }


@app.get("/schema")
def get_schema():
    return {
        "action_schema":      Action.model_json_schema(),
        "observation_schema": Observation.model_json_schema(),
    }


@app.post("/reset", response_model=Observation)
def reset(scenario_id: Optional[str] = None):
    """
    Initialises the environment.
    Bare POST /reset (no query param) defaults to easy_e1 — never 422s the validator.
    """
    global active_env
    if not SCENARIOS:
        raise HTTPException(status_code=500, detail="No scenarios loaded.")
    if not scenario_id or scenario_id not in SCENARIOS:
        scenario_id = "easy_e1"
    try:
        with _env_lock:
            active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
            return active_env.get_observation()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to init '{scenario_id}': {exc}")


@app.get("/state", response_model=Observation)
def get_state():
    global active_env
    with _env_lock:
        if active_env is None:
            raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
        try:
            return active_env.get_observation()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"State error: {exc}")


@app.post("/step", response_model=StepResponse)
def step(req: Action):
    """
    Executes one action.
    Intermediate reward on non-terminal steps; final grader total on terminal steps.
    """
    global active_env
    with _env_lock:
        if active_env is None:
            raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
        try:
            reward = compute_intermediate_reward(active_env, req)
            result = active_env.step(req.action, req.target, req.failure_type)

            if result.get("done"):
                try:
                    score_data = active_env.get_score()
                    if isinstance(score_data, dict):
                        reward = float(score_data.get("total", 0.0))
                except Exception:
                    reward = 0.0

            return {
                "observation": result.get("observation"),
                "reward":      reward,
                "done":        result.get("done", False),
                "info":        {"message": result.get("message", "")},
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Step failed: {exc}")


@app.get("/grader")
def get_score():
    """Returns the final score breakdown. Only valid after done=True."""
    global active_env
    with _env_lock:
        if active_env is None:
            raise HTTPException(status_code=400, detail="No active episode.")
        try:
            if not active_env.state.done:
                raise HTTPException(
                    status_code=400,
                    detail="Episode not complete. Declare root cause or exhaust step budget.",
                )
            return active_env.get_score()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Grader error: {exc}")


@app.get("/baseline")
def run_baseline():
    """Runs baseline LLM agent on easy/medium/hard and returns scores."""
    try:
        from inference import run_smart_agent
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import inference.py failed: {exc}")

    scores: dict = {}
    for task in ["easy_e1", "medium_m2", "hard_h2"]:
        try:
            scores[task] = run_smart_agent(task)
        except Exception as exc:
            scores[task] = {"error": str(exc)}
    return {"baseline_scores": scores}
