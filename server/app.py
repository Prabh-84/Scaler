# import json
# import os
# import sys
# import threading

# from fastapi import FastAPI, HTTPException

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from models import Action, StepResponse, Observation
# from server.cascade_debug_env_environment import CascadeDebugEnvironment

# app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# # ---------------------------------------------------------------------------
# # Scenario loading
# # ---------------------------------------------------------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# SCENARIO_DIR = os.path.join(BASE_DIR, "scenarios")

# print("BASE_DIR:", BASE_DIR)
# print("SCENARIO_DIR:", SCENARIO_DIR)
# print("SCENARIO_DIR exists:", os.path.exists(SCENARIO_DIR))
# if os.path.exists(SCENARIO_DIR):
#     print("Scenario files:", os.listdir(SCENARIO_DIR))


# def load_scenarios() -> dict:
#     scenarios = {}

#     if not os.path.exists(SCENARIO_DIR):
#         raise FileNotFoundError(f"Scenarios directory not found at: {SCENARIO_DIR}")

#     for fname in os.listdir(SCENARIO_DIR):
#         if fname.endswith(".json"):
#             fpath = os.path.join(SCENARIO_DIR, fname)
#             with open(fpath, "r", encoding="utf-8") as f:
#                 data = json.load(f)

#             scenario_id = data.get("scenario_id")
#             if not scenario_id:
#                 raise ValueError(f"Missing 'scenario_id' in scenario file: {fname}")

#             scenarios[scenario_id] = data

#     if not scenarios:
#         raise ValueError(f"No scenario JSON files found in: {SCENARIO_DIR}")

#     return scenarios


# # BUG FIX: Raise on startup failure so the container exits with a non-zero code
# # instead of silently starting with an empty SCENARIOS dict.
# SCENARIOS = load_scenarios()

# # ---------------------------------------------------------------------------
# # BUG FIX: Thread-safe active environment
# # Previously a bare module-level global — concurrent /reset calls would corrupt state.
# # Now guarded with a lock so each request sees a consistent active_env.
# # ---------------------------------------------------------------------------
# _env_lock = threading.Lock()
# active_env: CascadeDebugEnvironment | None = None


# # ---------------------------------------------------------------------------
# # Endpoints
# # ---------------------------------------------------------------------------

# @app.get("/")
# def health_check():
#     return {
#         "status": "ok",
#         "loaded_scenarios": list(SCENARIOS.keys()),
#         "scenario_count": len(SCENARIOS),
#     }


# @app.get("/tasks")
# def get_tasks():
#     if not SCENARIOS:
#         raise HTTPException(status_code=500, detail="No scenarios loaded.")
#     return {
#         "tasks": list(SCENARIOS.keys()),
#         "action_schema": Action.model_json_schema(),
#     }


# @app.post("/reset", response_model=Observation)
# def reset(scenario_id: str = "easy_e1"):
#     """
#     Initializes the environment for a given scenario and returns the first observation.
#     Falls back to easy_e1 if the requested scenario_id is not found.
#     """
#     global active_env

#     if not SCENARIOS:
#         raise HTTPException(status_code=500, detail="No scenarios loaded.")

#     # Graceful fallback — don't 404 the validator
#     if scenario_id not in SCENARIOS:
#         scenario_id = "easy_e1"

#     try:
#         with _env_lock:
#             active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
#             return active_env.get_observation()
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to initialize scenario '{scenario_id}': {str(e)}"
#         )


# @app.get("/state", response_model=Observation)
# def get_state():
#     global active_env

#     with _env_lock:
#         if active_env is None:
#             raise HTTPException(
#                 status_code=400,
#                 detail="No active episode. Call /reset first."
#             )
#         try:
#             return active_env.get_observation()
#         except Exception as e:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Failed to fetch environment state: {str(e)}"
#             )


# @app.post("/step", response_model=StepResponse)
# def step(req: Action):
#     """
#     Executes one action in the environment.
#     Returns observation, reward, done, info.
#     """
#     global active_env

#     with _env_lock:
#         if active_env is None:
#             raise HTTPException(
#                 status_code=400,
#                 detail="No active episode. Call /reset first."
#             )

#         try:
#             result = active_env.step(req.action, req.target, req.failure_type)

#             # BUG FIX: Only compute score when the episode is actually done.
#             # Previously get_score() was called on every step — it always raised or
#             # silently returned 0.0 mid-episode, hiding real errors.
#             reward = 0.0
#             if result.get("done"):
#                 try:
#                     score_data = active_env.get_score()
#                     if isinstance(score_data, dict):
#                         reward = float(score_data.get("total", 0.0))
#                 except Exception:
#                     reward = 0.0

#             return {
#                 "observation": result.get("observation"),
#                 "reward": reward,
#                 "done": result.get("done", False),
#                 "info": {
#                     "message": result.get("message", "")
#                 },
#             }

#         except Exception as e:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Step execution failed: {str(e)}"
#             )


# @app.get("/grader")
# def get_score():
#     """
#     Returns the final score breakdown after episode completion.
#     """
#     global active_env

#     with _env_lock:
#         if active_env is None:
#             raise HTTPException(status_code=400, detail="No active episode.")

#         try:
#             if not active_env.state.done:
#                 raise HTTPException(
#                     status_code=400,
#                     detail="Episode not complete. Must declare root cause or run out of steps."
#                 )
#             return active_env.get_score()

#         except HTTPException:
#             raise
#         except Exception as e:
#             raise HTTPException(
#                 status_code=500,
#                 detail=f"Failed to compute grade: {str(e)}"
#             )


# @app.get("/baseline")
# def run_baseline():
#     """
#     Runs the baseline agent on one easy, one medium, and one hard task.
#     """
#     try:
#         from inference import run_smart_agent
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to import baseline agent from inference.py: {str(e)}"
#         )

#     test_tasks = ["easy_e1", "medium_m2", "hard_h2"]
#     scores = {}

#     for task in test_tasks:
#         try:
#             scores[task] = run_smart_agent(task, external_call=True)
#         except Exception as e:
#             scores[task] = {"error": str(e)}

#     return {"baseline_scores": scores}
from fastapi import FastAPI, HTTPException
from typing import Optional
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from models import Action, StepResponse, Observation
from server.cascade_debug_env_environment import CascadeDebugEnvironment

app = FastAPI(title="CascadeDebugEnv OpenEnv Server")


def load_scenarios() -> dict:
    scenarios = {}

    preferred_dirs = [
        os.path.join(ROOT_DIR, "scenarios"),
        "/app/scenarios",
    ]

    scenario_dir = None
    for d in preferred_dirs:
        if os.path.isdir(d):
            scenario_dir = d
            break

    if scenario_dir is None:
        raise FileNotFoundError("Could not find scenarios directory.")

    for fname in os.listdir(scenario_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(scenario_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenario_id = data.get("scenario_id")
            if not scenario_id:
                raise ValueError(f"Missing scenario_id in {fname}")

            scenarios[scenario_id] = data

    if not scenarios:
        raise ValueError(f"No scenario JSON files found in {scenario_dir}")

    return scenarios


def compute_intermediate_reward(env: CascadeDebugEnvironment, action: Action) -> float:
    reward = 0.0

    if action.action == "observe":
        if action.target in env.state.nodes:
            target_node = env.state.nodes[action.target]
            if target_node["observable"]:
                reward -= 0.02
            else:
                reward += 0.08

    elif action.action in {"restart", "rollback", "drain_connections", "reroute_traffic", "scale_replica"}:
        reward += 0.05

    elif action.action == "isolate":
        reward += 0.03

    elif action.action == "declare_root_cause":
        reward -= 0.05

    try:
        ground_truth = env.scenario_dict.get("ground_truth", {})
        trap_actions = ground_truth.get("trap_actions", [])
        for trap in trap_actions:
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


SCENARIOS = load_scenarios()
active_env = None


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "cwd": os.getcwd(),
        "base_dir": ROOT_DIR,
        "scenario_count": len(SCENARIOS),
        "loaded_scenarios": list(SCENARIOS.keys()),
    }


@app.get("/tasks")
def get_tasks():
    if not SCENARIOS:
        raise HTTPException(status_code=500, detail="No scenarios loaded.")

    return {
        "tasks": list(SCENARIOS.keys()),
        "action_schema": Action.model_json_schema(),
    }


@app.get("/schema")
def get_schema():
    return {
        "action_schema": Action.model_json_schema(),
        "observation_schema": Observation.model_json_schema(),
    }


@app.post("/reset", response_model=Observation)
def reset(scenario_id: Optional[str] = None):
    global active_env

    if not SCENARIOS:
        raise HTTPException(status_code=500, detail="No scenarios loaded.")

    if not scenario_id or scenario_id not in SCENARIOS:
        scenario_id = "easy_e1"

    try:
        active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
        return active_env.get_observation()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize scenario '{scenario_id}': {str(e)}"
        )


@app.get("/state", response_model=Observation)
def get_state():
    global active_env

    if active_env is None:
        raise HTTPException(
            status_code=400,
            detail="No active episode. Call /reset first."
        )

    try:
        return active_env.get_observation()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch environment state: {str(e)}"
        )


@app.post("/step", response_model=StepResponse)
def step(req: Action):
    global active_env

    if active_env is None:
        raise HTTPException(
            status_code=400,
            detail="No active episode. Call /reset first."
        )

    try:
        reward = compute_intermediate_reward(active_env, req)
        result = active_env.step(req.action, req.target, req.failure_type)

        if active_env.state.done:
            score_data = active_env.get_score()
            if isinstance(score_data, dict):
                reward = float(score_data.get("total", 0.0))

        return {
            "observation": result.get("observation"),
            "reward": reward,
            "done": result.get("done", False),
            "info": {
                "message": result.get("message", "")
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Step execution failed: {str(e)}"
        )


@app.get("/grader")
def get_score():
    global active_env

    if active_env is None:
        raise HTTPException(status_code=400, detail="No active episode.")

    try:
        if not active_env.state.done:
            raise HTTPException(
                status_code=400,
                detail="Episode not complete. Must declare root cause or run out of steps."
            )

        return active_env.get_score()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute grade: {str(e)}"
        )


@app.get("/baseline")
def run_baseline():
    try:
        from inference import run_smart_agent
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import baseline agent from inference.py: {str(e)}"
        )

    test_tasks = ["easy_e1", "medium_m2", "hard_h2"]
    scores = {}

    for task in test_tasks:
        try:
            scores[task] = run_smart_agent(task, external_call=True)
        except Exception as e:
            scores[task] = {"error": str(e)}

    return {"baseline_scores": scores}