# # # # Copyright (c) Meta Platforms, Inc. and affiliates.
# # # # All rights reserved.
# # # #
# # # # This source code is licensed under the BSD-style license found in the
# # # # LICENSE file in the root directory of this source tree.

# # # """
# # # FastAPI application for the Cascade Debug Env Environment.

# # # This module creates an HTTP server that exposes the CascadeDebugEnvironment
# # # over HTTP and WebSocket endpoints, compatible with EnvClient.

# # # Endpoints:
# # #     - POST /reset: Reset the environment
# # #     - POST /step: Execute an action
# # #     - GET /state: Get current environment state
# # #     - GET /schema: Get action/observation schemas
# # #     - WS /ws: WebSocket endpoint for persistent sessions

# # # Usage:
# # #     # Development (with auto-reload):
# # #     uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

# # #     # Production:
# # #     uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

# # #     # Or run directly:
# # #     python -m server.app
# # # """

# # # try:
# # #     from openenv.core.env_server.http_server import create_app
# # # except Exception as e:  # pragma: no cover
# # #     raise ImportError(
# # #         "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
# # #     ) from e

# # # try:
# # #     from ..models import CascadeDebugAction, CascadeDebugObservation
# # #     from .cascade_debug_env_environment import CascadeDebugEnvironment
# # # except ModuleNotFoundError:
# # #     from models import CascadeDebugAction, CascadeDebugObservation
# # #     from server.cascade_debug_env_environment import CascadeDebugEnvironment


# # # # Create the app with web interface and README integration
# # # app = create_app(
# # #     CascadeDebugEnvironment,
# # #     CascadeDebugAction,
# # #     CascadeDebugObservation,
# # #     env_name="cascade_debug_env",
# # #     max_concurrent_envs=1,  # increase this number to allow more concurrent WebSocket sessions
# # # )


# # # def main(host: str = "0.0.0.0", port: int = 8000):
# # #     """
# # #     Entry point for direct execution via uv run or python -m.

# # #     This function enables running the server without Docker:
# # #         uv run --project . server
# # #         uv run --project . server --port 8001
# # #         python -m cascade_debug_env.server.app

# # #     Args:
# # #         host: Host address to bind to (default: "0.0.0.0")
# # #         port: Port number to listen on (default: 8000)

# # #     For production deployments, consider using uvicorn directly with
# # #     multiple workers:
# # #         uvicorn cascade_debug_env.server.app:app --workers 4
# # #     """
# # #     import uvicorn

# # #     uvicorn.run(app, host=host, port=port)


# # # if __name__ == "__main__":
# # #     import argparse

# # #     parser = argparse.ArgumentParser()
# # #     parser.add_argument("--port", type=int, default=8000)
# # #     args = parser.parse_args()
# # #     main(port=args.port)
# # # server/app.py
# # from fastapi import FastAPI, HTTPException
# # from pydantic import BaseModel
# # from typing import Optional
# # import json
# # import os

# # from cascade_debug_env_environment import CascadeDebugEnvironment

# # app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# # # Load all 9 scenarios from the parent directory's 'scenarios' folder
# # SCENARIOS = {}
# # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# # SCENARIO_DIR = os.path.join(BASE_DIR, "scenarios")

# # try:
# #     for fname in os.listdir(SCENARIO_DIR):
# #         if fname.endswith(".json"):
# #             with open(os.path.join(SCENARIO_DIR, fname)) as f:
# #                 s = json.load(f)
# #                 SCENARIOS[s["scenario_id"]] = s
# # except FileNotFoundError:
# #     print(f"Warning: Could not find scenarios directory at {SCENARIO_DIR}")

# # active_env = None

# # # We redefine the request model here to keep the server self-contained
# # class StepRequest(BaseModel):
# #     action: str
# #     target: str
# #     failure_type: Optional[str] = None

# # @app.get("/")
# # def health_check():
# #     return {"status": "ok", "loaded_scenarios": list(SCENARIOS.keys())}

# # @app.post("/reset")
# # def reset(scenario_id: str):
# #     global active_env
# #     if scenario_id not in SCENARIOS:
# #         raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    
# #     active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
# #     return active_env.get_observation()

# # @app.post("/step")
# # def step(req: StepRequest):
# #     global active_env
# #     if not active_env:
# #         raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
    
# #     result = active_env.step(req.action, req.target, req.failure_type)
# #     return result

# # @app.get("/grader")
# # def get_score():
# #     global active_env
# #     if not active_env:
# #         raise HTTPException(status_code=400, detail="No active episode.")
# #     if not active_env.state.done:
# #         raise HTTPException(status_code=400, detail="Episode not complete. Must declare root cause or run out of steps.")
    
# #     return active_env.get_score()
# # from fastapi import FastAPI, HTTPException
# # from typing import Optional, Dict, Any
# # import json
# # import os
# # import sys

# # # Add the parent directory to sys.path so we can import models and client
# # sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# # from models import Action, StepResponse, Observation
# # from cascade_debug_env_environment import CascadeDebugEnvironment

# # app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# # SCENARIOS = {}
# # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# # SCENARIO_DIR = os.path.join(BASE_DIR, "scenarios")

# # for fname in os.listdir(SCENARIO_DIR):
# #     if fname.endswith(".json"):
# #         with open(os.path.join(SCENARIO_DIR, fname)) as f:
# #             s = json.load(f)
# #             SCENARIOS[s["scenario_id"]] = s

# # active_env = None

# # @app.get("/")
# # def health_check():
# #     return {"status": "ok"}

# # # REQUIRED ENDPOINT 1: /tasks
# # @app.get("/tasks")
# # def get_tasks():
# #     return {
# #         "tasks": list(SCENARIOS.keys()),
# #         "action_schema": Action.model_json_schema() # Required by checklist
# #     }

# # # REQUIRED ENDPOINT 2: /reset
# # @app.post("/reset", response_model=Observation)
# # def reset(scenario_id: str):
# #     global active_env
# #     if scenario_id not in SCENARIOS:
# #         raise HTTPException(status_code=404, detail="Scenario not found.")
# #     active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
# #     return active_env.get_observation()

# # # REQUIRED ENDPOINT 3: /state
# # @app.get("/state", response_model=Observation)
# # def get_state():
# #     global active_env
# #     if not active_env:
# #         raise HTTPException(status_code=400, detail="No active episode.")
# #     return active_env.get_observation()

# # # REQUIRED ENDPOINT 4: /step (Must return obs, reward, done, info)
# # @app.post("/step", response_model=StepResponse)
# # def step(req: Action):
# #     global active_env
# #     if not active_env:
# #         raise HTTPException(status_code=400, detail="Call /reset first.")
    
# #     result = active_env.step(req.action, req.target, req.failure_type)
    
# #     # Calculate intermediate reward (partial progress)
# #     current_score = active_env.get_score()["total"] if active_env.state.done else 0.0
    
# #     return {
# #         "observation": result.get("observation"),
# #         "reward": current_score, # Fulfills the reward requirement
# #         "done": result.get("done", False),
# #         "info": {"message": result.get("message", "")} # Fulfills the info requirement
# #     }

# # # REQUIRED ENDPOINT 5: /grader
# # @app.get("/grader")
# # def get_score():
# #     global active_env
# #     if not active_env:
# #         raise HTTPException(status_code=400, detail="No active episode.")
# #     return active_env.get_score()

# # # REQUIRED ENDPOINT 6: /baseline
# # @app.get("/baseline")
# # def run_baseline():
# #     """Triggers the inference script and returns baseline scores."""
# #     from client import run_systematic_baseline # Import our baseline agent
    
# #     scores = {}
# #     # Test one from each difficulty to prove it works
# #     test_tasks = ["easy_e1", "medium_m2", "hard_h2"] 
    
# #     for task in test_tasks:
# #         try:
# #             score = run_systematic_baseline(task, external_call=True)
# #             scores[task] = score
# #         except Exception as e:
# #             scores[task] = f"Error: {str(e)}"
            
# #     return {"baseline_scores": scores}
# # server/app.py
# from fastapi import FastAPI, HTTPException
# from typing import Optional, Dict, Any
# import json
# import os
# import sys

# # Add the parent directory to sys.path so we can import models and client
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from models import Action, StepResponse, Observation
# from server.cascade_debug_env_environment import CascadeDebugEnvironment

# app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# SCENARIOS = {}
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# SCENARIO_DIR = os.path.join(BASE_DIR, "scenarios")

# # Load scenarios on startup
# try:
#     for fname in os.listdir(SCENARIO_DIR):
#         if fname.endswith(".json"):
#             with open(os.path.join(SCENARIO_DIR, fname)) as f:
#                 s = json.load(f)
#                 SCENARIOS[s["scenario_id"]] = s
# except FileNotFoundError:
#     print(f"Warning: Could not find scenarios directory at {SCENARIO_DIR}")

# active_env = None

# @app.get("/")
# def health_check():
#     return {"status": "ok", "loaded_scenarios": list(SCENARIOS.keys())}

# # REQUIRED ENDPOINT 1: /tasks
# @app.get("/tasks")
# def get_tasks():
#     """Returns the list of available tasks and the JSON schema for Actions."""
#     return {
#         "tasks": list(SCENARIOS.keys()),
#         "action_schema": Action.model_json_schema()
#     }

# # REQUIRED ENDPOINT 2: /reset
# @app.post("/reset", response_model=Observation)
# def reset(scenario_id: str):
#     """Initializes the environment and returns the first observation."""
#     global active_env
#     if scenario_id not in SCENARIOS:
#         raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    
#     active_env = CascadeDebugEnvironment(SCENARIOS[scenario_id])
#     return active_env.get_observation()

# # REQUIRED ENDPOINT 3: /state
# @app.get("/state", response_model=Observation)
# def get_state():
#     """Returns the current state of the environment."""
#     global active_env
#     if not active_env:
#         raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
#     return active_env.get_observation()

# # REQUIRED ENDPOINT 4: /step
# @app.post("/step", response_model=StepResponse)
# def step(req: Action):
#     """Takes an action and returns observation, reward, done, and info."""
#     global active_env
#     if not active_env:
#         raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
    
#     result = active_env.step(req.action, req.target, req.failure_type)
    
#     # Calculate intermediate reward (partial progress)
#     # OpenEnv requires a float reward signal.
#     current_score = active_env.get_score()["total"] if active_env.state.done else 0.0
    
#     return {
#         "observation": result.get("observation"),
#         "reward": current_score,
#         "done": result.get("done", False),
#         "info": {"message": result.get("message", "")}
#     }

# # REQUIRED ENDPOINT 5: /grader
# @app.get("/grader")
# def get_score():
#     """Returns the final score breakdown after an episode finishes."""
#     global active_env
#     if not active_env:
#         raise HTTPException(status_code=400, detail="No active episode.")
#     if not active_env.state.done:
#         raise HTTPException(status_code=400, detail="Episode not complete. Must declare root cause or run out of steps.")
    
#     return active_env.get_score()

# # REQUIRED ENDPOINT 6: /baseline
# @app.get("/baseline")
# def run_baseline():
#     """Triggers the inference script and returns baseline scores for validation."""
#     # We import the Groq-powered LLM agent from client.py
#     from client import run_smart_agent 
    
#     scores = {}
#     # Test one from each difficulty to prove it works to the validators
#     test_tasks = ["easy_e1", "medium_m2", "hard_h2"] 
    
#     for task in test_tasks:
#         try:
#             # external_call=True mutes the terminal prints so it doesn't clutter the server logs
#             score = run_smart_agent(task, external_call=True) 
#             scores[task] = score
#         except Exception as e:
#             scores[task] = f"Error: {str(e)}"
            
#     return {"baseline_scores": scores}

# server/app.py
from fastapi import FastAPI, HTTPException
from typing import Optional, Dict, Any
import json
import os
import sys

# Add the parent directory to sys.path so we can import models and environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Action, StepResponse, Observation
from server.cascade_debug_env_environment import CascadeDebugEnvironment

app = FastAPI(title="CascadeDebugEnv OpenEnv Server")

# --- Bulletproof Scenario Loading ---
def load_scenarios() -> dict:
    scenarios = {}
    
    # Start searching from the Docker root directory (/app) or the current file directory
    search_dir = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
    
    # Walk through EVERY folder and file in the directory
    for root, dirs, files in os.walk(search_dir):
        for fname in files:
            if fname.endswith(".json"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # If it looks like a scenario, load it!
                        if isinstance(data, dict) and "scenario_id" in data:
                            scenarios[data["scenario_id"]] = data
                except Exception:
                    pass # Ignore any irrelevant JSON files
                    
    if not scenarios:
        print(f"CRITICAL ERROR: No scenario JSON files found ANYWHERE in {search_dir}!")
        
    return scenarios

SCENARIOS = {}
try:
    SCENARIOS = load_scenarios()
except Exception as e:
    print(f"[Startup Error] Failed to load scenarios: {e}")

active_env = None

# --- Endpoints ---

@app.get("/")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok", 
        "loaded_scenarios": list(SCENARIOS.keys()),
        "scenario_count": len(SCENARIOS)
    }

# REQUIRED ENDPOINT 1: /tasks
@app.get("/tasks")
def get_tasks():
    """Returns the list of available tasks and the JSON schema for Actions."""
    if not SCENARIOS:
        raise HTTPException(status_code=500, detail="No scenarios loaded.")
        
    return {
        "tasks": list(SCENARIOS.keys()),
        "action_schema": Action.model_json_schema()
    }

# REQUIRED ENDPOINT 2: /reset
@app.post("/reset", response_model=Observation)
def reset(scenario_id: Optional[str] = "easy_e1"):
    """
    Initializes the environment for a given scenario and returns the first observation.
    Defaulting to 'easy_e1' ensures the automated validator doesn't crash on empty POSTs.
    """
    global active_env
    
    if not SCENARIOS:
        raise HTTPException(status_code=500, detail="No scenarios loaded.")

    # Fallback just in case the validator passes null or an invalid string
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

# REQUIRED ENDPOINT 3: /state
@app.get("/state", response_model=Observation)
def get_state():
    """Returns the current state of the environment."""
    global active_env
    if not active_env:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
    
    try:
        return active_env.get_observation()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch state: {str(e)}")

# REQUIRED ENDPOINT 4: /step
@app.post("/step", response_model=StepResponse)
def step(req: Action):
    """Takes an action and returns observation, reward, done, and info."""
    global active_env
    if not active_env:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")
    
    try:
        result = active_env.step(req.action, req.target, req.failure_type)
        
        # Calculate intermediate reward (partial progress)
        # OpenEnv requires a float reward signal.
        reward = 0.0
        if active_env.state.done:
            score_data = active_env.get_score()
            if isinstance(score_data, dict):
                reward = float(score_data.get("total", 0.0))
        
        return {
            "observation": result.get("observation"),
            "reward": reward,
            "done": result.get("done", False),
            "info": {"message": result.get("message", "")}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step execution failed: {str(e)}")

# REQUIRED ENDPOINT 5: /grader
@app.get("/grader")
def get_score():
    """Returns the final score breakdown after an episode finishes."""
    global active_env
    
    if not active_env:
        raise HTTPException(status_code=400, detail="No active episode.")
    
    if not active_env.state.done:
        raise HTTPException(
            status_code=400, 
            detail="Episode not complete. Must declare root cause or run out of steps."
        )
    
    try:
        return active_env.get_score()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute grade: {str(e)}")

# REQUIRED ENDPOINT 6: /baseline
@app.get("/baseline")
def run_baseline():
    """Triggers the inference script and returns baseline scores for validation."""
    try:
        # Import the Groq-powered LLM agent from inference.py
        from inference import run_smart_agent 
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import baseline agent from inference.py: {str(e)}"
        )
    
    scores = {}
    # Test one from each difficulty to prove it works to the validators
    test_tasks = ["easy_e1", "medium_m2", "hard_h2"] 
    
    for task in test_tasks:
        try:
            # external_call=True mutes the terminal prints so it doesn't clutter the server logs
            score = run_smart_agent(task, external_call=True) 
            scores[task] = score
        except Exception as e:
            scores[task] = {"error": str(e)}
            
    return {"baseline_scores": scores}