
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
# Scenario loading
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

_env_lock: threading.Lock = threading.Lock()
active_env: Optional[CascadeDebugEnvironment] = None

# ---------------------------------------------------------------------------
# Frontend static export setup
# ---------------------------------------------------------------------------

# Next export output path
FRONTEND_OUT_DIR_CANDIDATES = [
    os.path.join(ROOT_DIR, "chaos-frontend", "out"),
    "/app/chaos-frontend/out",
]

FRONTEND_OUT_DIR = next(
    (d for d in FRONTEND_OUT_DIR_CANDIDATES if os.path.isdir(d)),
    None,
)

if FRONTEND_OUT_DIR:
    assets_dir = os.path.join(FRONTEND_OUT_DIR, "_next")
    if os.path.isdir(assets_dir):
        app.mount("/_next", StaticFiles(directory=assets_dir), name="next_assets")

    # Optional common static dirs if they exist
    for static_name in ["static", "images"]:
        static_path = os.path.join(FRONTEND_OUT_DIR, static_name)
        if os.path.isdir(static_path):
            app.mount(f"/{static_name}", StaticFiles(directory=static_path), name=static_name)

# ---------------------------------------------------------------------------
# Intermediate reward shaping
# ---------------------------------------------------------------------------

def compute_intermediate_reward(env: CascadeDebugEnvironment, action: Action) -> float:
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
        reward -= 0.05

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
# API endpoints
# ---------------------------------------------------------------------------

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
                "reward": reward,
                "done": result.get("done", False),
                "info": {"message": result.get("message", "")},
            }
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Step failed: {exc}")


@app.get("/grader")
def get_score():
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

# ---------------------------------------------------------------------------
# Frontend routes
# ---------------------------------------------------------------------------

@app.get("/")
def serve_frontend_index():
    if FRONTEND_OUT_DIR:
        index_path = os.path.join(FRONTEND_OUT_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
    return {
        "status": "ok",
        "message": "Frontend build not found",
        "scenario_count": len(SCENARIOS),
        "loaded_scenarios": sorted(SCENARIOS.keys()),
    }


@app.get("/{full_path:path}")
def serve_frontend_spa(full_path: str):
    # Don't hijack API routes
    blocked_prefixes = ("tasks", "schema", "reset", "state", "step", "grader", "baseline", "docs", "openapi.json", "redoc")
    if full_path.startswith(blocked_prefixes):
        raise HTTPException(status_code=404, detail="Not found")

    if FRONTEND_OUT_DIR:
        target_path = os.path.join(FRONTEND_OUT_DIR, full_path)

        if os.path.isfile(target_path):
            return FileResponse(target_path)

        if os.path.isfile(target_path + ".html"):
            return FileResponse(target_path + ".html")

        index_path = os.path.join(FRONTEND_OUT_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Frontend file not found")
