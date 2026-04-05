
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from typing import Optional
# import json
# import os
# import sys

# ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# if ROOT_DIR not in sys.path:
#     sys.path.append(ROOT_DIR)

# from models import Action, StepResponse, Observation
# from server.cascade_debug_env_environment import CascadeDebugEnvironment

# app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# # ✅ CORS FIX (IMPORTANT)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # dev ch sab allow
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ---------------------------------------------------------------------------
# # Scenario loading
# # ---------------------------------------------------------------------------
# def load_scenarios() -> dict:
#     scenarios = {}

#     preferred_dirs = [
#         os.path.join(ROOT_DIR, "scenarios"),
#         "/app/scenarios",
#     ]

#     scenario_dir = None
#     for d in preferred_dirs:
#         if os.path.isdir(d):
#             scenario_dir = d
#             break

#     if scenario_dir is None:
#         raise FileNotFoundError(
#             f"Could not find scenarios directory. Tried: {preferred_dirs}"
#         )

#     for fname in os.listdir(scenario_dir):
#         if fname.endswith(".json"):
#             fpath = os.path.join(scenario_dir, fname)
#             with open(fpath, "r", encoding="utf-8") as f:
#                 data = json.load(f)

#             scenario_id = data.get("scenario_id")
#             if not scenario_id:
#                 raise ValueError(f"Missing scenario_id in {fname}")

#             scenarios[scenario_id] = data

#     if not scenarios:
#         raise ValueError(f"No scenario JSON files found in {scenario_dir}")

#     return scenarios


# SCENARIOS = load_scenarios()
# active_env = None


# # ---------------------------------------------------------------------------
# # Reward shaping
# # ---------------------------------------------------------------------------
# def compute_intermediate_reward(env: CascadeDebugEnvironment, action: Action) -> float:
#     reward = 0.0

#     if action.action == "observe":
#         if action.target in env.state.nodes:
#             node = env.state.nodes[action.target]
#             if not node["observable"]:
#                 reward += 0.08
#             else:
#                 reward -= 0.02

#     elif action.action in {"restart", "rollback", "drain_connections", "reroute_traffic"}:
#         reward += 0.05

#     elif action.action == "scale_replica":
#         reward += 0.02

#     elif action.action == "isolate":
#         reward += 0.03

#     elif action.action == "declare_root_cause":
#         reward -= 0.05

#     try:
#         ground_truth = env.scenario_dict.get("ground_truth", {})
#         for trap in ground_truth.get("trap_actions", []):
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
#         "loaded_scenarios": list(SCENARIOS.keys()),
#     }


# @app.get("/tasks")
# def get_tasks():
#     if not SCENARIOS:
#         raise HTTPException(status_code=500, detail="No scenarios loaded.")
#     return {
#         "tasks": list(SCENARIOS.keys()),
#         "action_schema": Action.model_json_schema(),
#     }


# @app.get("/schema")
# def get_schema():
#     return {
#         "action_schema": Action.model_json_schema(),
#         "observation_schema": Observation.model_json_schema(),
#     }


# @app.post("/reset", response_model=Observation)
# def reset(scenario_id: Optional[str] = None):
#     global active_env

#     if not SCENARIOS:
#         raise HTTPException(status_code=500, detail="No scenarios loaded.")

#     if not scenario_id or scenario_id not in SCENARIOS:
#         scenario_id = "easy_e1"

#     try:
#         active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
#         return active_env.get_observation()
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to initialize scenario '{scenario_id}': {str(e)}"
#         )


# @app.get("/state", response_model=Observation)
# def get_state():
#     global active_env

#     if active_env is None:
#         raise HTTPException(
#             status_code=400,
#             detail="No active episode. Call /reset first."
#         )
#     try:
#         return active_env.get_observation()
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to fetch environment state: {str(e)}"
#         )


# @app.post("/step", response_model=StepResponse)
# def step(req: Action):
#     global active_env

#     if active_env is None:
#         raise HTTPException(
#             status_code=400,
#             detail="No active episode. Call /reset first."
#         )

#     try:
#         reward = compute_intermediate_reward(active_env, req)

#         result = active_env.step(req.action, req.target, req.failure_type)

#         if result.get("done"):
#             try:
#                 score_data = active_env.get_score()
#                 if isinstance(score_data, dict):
#                     reward = float(score_data.get("total", 0.0))
#             except Exception:
#                 reward = 0.0

#         return {
#             "observation": result.get("observation"),
#             "reward": reward,
#             "done": result.get("done", False),
#             "info": {
#                 "message": result.get("message", "")
#             },
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Step execution failed: {str(e)}"
#         )


# @app.get("/grader")
# def get_score():
#     global active_env

#     if active_env is None:
#         raise HTTPException(status_code=400, detail="No active episode.")

#     try:
#         if not active_env.state.done:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Episode not complete."
#             )
#         return active_env.get_score()

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to compute grade: {str(e)}"
#         )


# @app.get("/baseline")
# def run_baseline():
#     try:
#         from inference import run_smart_agent
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to import baseline agent: {str(e)}"
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse  # ✅ ADDED
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

# ✅ CORS FIX (IMPORTANT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Scenario loading
# ---------------------------------------------------------------------------
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
        raise FileNotFoundError(
            f"Could not find scenarios directory. Tried: {preferred_dirs}"
        )

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


SCENARIOS = load_scenarios()
active_env = None


# ---------------------------------------------------------------------------
# Reward shaping
# ---------------------------------------------------------------------------
def compute_intermediate_reward(env: CascadeDebugEnvironment, action: Action) -> float:
    reward = 0.0

    if action.action == "observe":
        if action.target in env.state.nodes:
            node = env.state.nodes[action.target]
            if not node["observable"]:
                reward += 0.08
            else:
                reward -= 0.02

    elif action.action in {"restart", "rollback", "drain_connections", "reroute_traffic"}:
        reward += 0.05

    elif action.action == "scale_replica":
        reward += 0.02

    elif action.action == "isolate":
        reward += 0.03

    elif action.action == "declare_root_cause":
        reward -= 0.05

    try:
        ground_truth = env.scenario_dict.get("ground_truth", {})
        for trap in ground_truth.get("trap_actions", []):
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

# 🔥 CHANGED: root now redirects to frontend
@app.get("/")
def root():
    return RedirectResponse(url="http://localhost:3000")


@app.get("/health")
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

        if result.get("done"):
            try:
                score_data = active_env.get_score()
                if isinstance(score_data, dict):
                    reward = float(score_data.get("total", 0.0))
            except Exception:
                reward = 0.0

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
                detail="Episode not complete."
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
            detail=f"Failed to import baseline agent: {str(e)}"
        )

    test_tasks = ["easy_e1", "medium_m2", "hard_h2"]
    scores = {}

    for task in test_tasks:
        try:
            scores[task] = run_smart_agent(task, external_call=True)
        except Exception as e:
            scores[task] = {"error": str(e)}

    return {"baseline_scores": scores}