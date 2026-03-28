# # # Copyright (c) Meta Platforms, Inc. and affiliates.
# # # All rights reserved.
# # #
# # # This source code is licensed under the BSD-style license found in the
# # # LICENSE file in the root directory of this source tree.

# # """Cascade Debug Env Environment Client."""

# # from typing import Dict

# # from openenv.core import EnvClient
# # from openenv.core.client_types import StepResult
# # from openenv.core.env_server.types import State

# # from .models import CascadeDebugAction, CascadeDebugObservation


# # class CascadeDebugEnv(
# #     EnvClient[CascadeDebugAction, CascadeDebugObservation, State]
# # ):
# #     """
# #     Client for the Cascade Debug Env Environment.

# #     This client maintains a persistent WebSocket connection to the environment server,
# #     enabling efficient multi-step interactions with lower latency.
# #     Each client instance has its own dedicated environment session on the server.

# #     Example:
# #         >>> # Connect to a running server
# #         >>> with CascadeDebugEnv(base_url="http://localhost:8000") as client:
# #         ...     result = client.reset()
# #         ...     print(result.observation.echoed_message)
# #         ...
# #         ...     result = client.step(CascadeDebugAction(message="Hello!"))
# #         ...     print(result.observation.echoed_message)

# #     Example with Docker:
# #         >>> # Automatically start container and connect
# #         >>> client = CascadeDebugEnv.from_docker_image("cascade_debug_env-env:latest")
# #         >>> try:
# #         ...     result = client.reset()
# #         ...     result = client.step(CascadeDebugAction(message="Test"))
# #         ... finally:
# #         ...     client.close()
# #     """

# #     def _step_payload(self, action: CascadeDebugAction) -> Dict:
# #         """
# #         Convert CascadeDebugAction to JSON payload for step message.

# #         Args:
# #             action: CascadeDebugAction instance

# #         Returns:
# #             Dictionary representation suitable for JSON encoding
# #         """
# #         return {
# #             "message": action.message,
# #         }

# #     def _parse_result(self, payload: Dict) -> StepResult[CascadeDebugObservation]:
# #         """
# #         Parse server response into StepResult[CascadeDebugObservation].

# #         Args:
# #             payload: JSON response data from server

# #         Returns:
# #             StepResult with CascadeDebugObservation
# #         """
# #         obs_data = payload.get("observation", {})
# #         observation = CascadeDebugObservation(
# #             echoed_message=obs_data.get("echoed_message", ""),
# #             message_length=obs_data.get("message_length", 0),
# #             done=payload.get("done", False),
# #             reward=payload.get("reward"),
# #             metadata=obs_data.get("metadata", {}),
# #         )

# #         return StepResult(
# #             observation=observation,
# #             reward=payload.get("reward"),
# #             done=payload.get("done", False),
# #         )

# #     def _parse_state(self, payload: Dict) -> State:
# #         """
# #         Parse server response into State object.

# #         Args:
# #             payload: JSON response from state request

# #         Returns:
# #             State object with episode_id and step_count
# #         """
# #         return State(
# #             episode_id=payload.get("episode_id"),
# #             step_count=payload.get("step_count", 0),
# #         )
# # client.py
# import requests
# import time

# SERVER_URL = "http://127.0.0.1:8000"

# def wait_for_server():
#     """Wait for the FastAPI server to boot up."""
#     print("Waiting for OpenEnv server...")
#     for _ in range(10):
#         try:
#             res = requests.get(f"{SERVER_URL}/")
#             if res.status_code == 200:
#                 print("Server is up!", res.json())
#                 return True
#         except requests.ConnectionError:
#             time.sleep(1)
#     return False

# def run_systematic_baseline(scenario_id: str):
#     """
#     A baseline agent that observes degraded nodes, 
#     tries to fix them, and declares a root cause.
#     """
#     print(f"\n--- Starting Evaluation: {scenario_id} ---")
    
#     # 1. Reset Environment
#     try:
#         obs = requests.post(f"{SERVER_URL}/reset?scenario_id={scenario_id}").json()
#     except Exception as e:
#         print(f"Failed to reset environment: {e}")
#         return

#     step_count = 0
#     done = False
    
#     while not done:
#         step_count += 1
#         print(f"\n[Step {step_count}] Health: {obs.get('system_health')} | Remaining: {obs.get('steps_remaining')}")
        
#         # Simple Logic: Find the first node showing symptoms that we haven't observed yet
#         target_node = None
#         action_to_take = "observe"
        
#         for node_id, data in obs.get("nodes", {}).items():
#             if data.get("visible_symptoms") and data.get("health") == "hidden":
#                 target_node = node_id
#                 action_to_take = "observe"
#                 break
#             elif data.get("visible_symptoms") and data.get("health") != "hidden":
#                 # If we observed it and it has symptoms, try restarting it
#                 target_node = node_id
#                 action_to_take = "restart"
#                 break
                
#         # If we didn't find anything obvious, or we are running out of time, guess and end it
#         if not target_node or obs.get("steps_remaining", 0) <= 2:
#             target_node = list(obs.get("nodes", {}).keys())[0] # Just pick the first node
#             action_to_take = "declare_root_cause"
            
#         print(f"Agent Action -> {action_to_take.upper()} on {target_node}")
        
#         payload = {"action": action_to_take, "target": target_node}
#         if action_to_take == "declare_root_cause":
#             payload["failure_type"] = "unknown_crash"
            
#         # 2. Take Step
#         res = requests.post(f"{SERVER_URL}/step", json=payload).json()
        
#         if res.get("message"):
#             print(f"Server Message: {res.get('message')}")
            
#         done = res.get("done", False)
#         if not done:
#             obs = res.get("observation", {})

#     # 3. Get Final Score
#     print("\nEpisode Complete. Fetching Score...")
#     score = requests.get(f"{SERVER_URL}/grader").json()
#     print(f"FINAL SCORE: {score['total'] * 100}%")
#     print(f"Breakdown: Accuracy={score['root_cause_accuracy']}, Intervention={score['intervention_order']}, Damage={score['cascade_damage']}")

# if __name__ == "__main__":
#     if wait_for_server():
#         # Test it on the first easy scenario
#         run_systematic_baseline("easy_e1")
# client.py
import requests
import time
import json
import os
from openai import OpenAI

SERVER_URL = "http://127.0.0.1:8000"

# --- 1. GROQ CONFIGURATION ---
# Replace this with your actual gsk_ key from Groq
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
# We tell the OpenAI client to route traffic to Groq instead of OpenAI
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# FIXED: We must use a valid Groq model, not gpt-4o
GROQ_MODEL = "llama-3.3-70b-versatile"

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

def wait_for_server():
    print("Waiting for OpenEnv server...")
    for _ in range(10):
        try:
            if requests.get(f"{SERVER_URL}/").status_code == 200:
                print("Server is up!")
                return True
        except:
            time.sleep(1)
    return False

def run_smart_agent(scenario_id: str, external_call: bool = False):
    """
    Runs the LLM agent against a scenario. 
    external_call=True mutes the print statements for the automated evaluator.
    """
    if not external_call:
        print(f"\n========== RUNNING SMART AGENT: {scenario_id} ==========")
        
    try:
        state = requests.post(f"{SERVER_URL}/reset?scenario_id={scenario_id}").json()
    except Exception as e:
        if not external_call: print(f"Failed to reset server: {e}")
        return 0.0
    
    # Safety loop limit so it doesn't get stuck forever
    max_steps = state.get("steps_remaining", 15)
    
    for _ in range(max_steps):
        if not external_call:
            print(f"\n[Step {state.get('step')}] Health: {state.get('system_health')} | Remaining: {state.get('steps_remaining')}")
        
        prompt = f"CURRENT STATE:\n{json.dumps(state, indent=2)}\n\nWhat is your next move?"
        
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            decision = json.loads(response.choices[0].message.content)
            
            if not external_call:
                print(f"🤖 THOUGHT: {decision.get('thought')}")
            
            action_payload = decision.get("action", {})
            req_body = {
                "action": action_payload.get("action_type", "observe"),
                "target": action_payload.get("target", "api_gateway")
            }
            if "failure_type" in action_payload:
                req_body["failure_type"] = action_payload["failure_type"]
                
            if not external_call:
                print(f"⚡ ACTION: {req_body['action']} -> {req_body['target']}")
            
        except Exception as e:
            if not external_call: print(f"LLM Error: {e}")
            break
            
        # Execute on Server
        try:
            res = requests.post(f"{SERVER_URL}/step", json=req_body).json()
        except Exception as e:
            if not external_call: print(f"Server execution error: {e}")
            break
        
        if res.get("info", {}).get("message") and not external_call:
            print(f"SERVER MSG: {res.get('info')['message']}")
            
        if res.get("done"):
            break
            
        state = res.get("observation")

    # Get Final Score Safely
    final_score = 0.0
    try:
        score_data = requests.get(f"{SERVER_URL}/grader").json()
        
        # Check if the server actually returned a score, or an error (like 'Episode not complete')
        if "total" in score_data:
            final_score = score_data['total']
            
            if not external_call:
                print("\n========== EPISODE COMPLETE ==========")
                print(f"FINAL SCORE: {final_score * 100}%")
                print(json.dumps(score_data.get('breakdown', {}), indent=2))
        else:
            if not external_call:
                print("\n========== EPISODE ENDED EARLY ==========")
                print(f"Server returned: {score_data}")
                
    except Exception as e:
        if not external_call: print(f"Failed to fetch final score: {e}")
        
    return final_score

if __name__ == "__main__":
    if wait_for_server():
        # Test it locally to watch the magic happen
        run_smart_agent("medium_m2")