# server/cascade_debug_env_environment.py
import json
from typing import Dict, List, Optional
from .cascade_engine import propagate_failures
from .grader import CascadeGrader

class SystemState:
    """Internal tracker for the true state of the simulated microservices."""
    def __init__(self, scenario: dict):
        self.scenario_id = scenario["scenario_id"]
        self.step = 0
        self.steps_remaining = scenario["step_budget"]
        self.intervention_log = []
        self.done = False
        
        # Load initial nodes from the JSON scenario
        self.nodes = {}
        for node_id, data in scenario["initial_node_states"].items():
            self.nodes[node_id] = {
                "status": data["status"],
                "health": data["health"],
                "observable": data["observable"],
                "visible_symptoms": data.get("visible_symptoms", []),
                "is_isolated": False
            }
            
    @property
    def system_health(self) -> float:
        healths = [n["health"] for n in self.nodes.values() if isinstance(n["health"], (int, float))]
        if not healths: return 0.0
        return round(sum(healths) / len(healths), 3)


class CascadeDebugEnvironment:
    """The main interface for the OpenEnv server to interact with."""
    def __init__(self, scenario_dict: dict):
        self.scenario_dict = scenario_dict
        self.state = SystemState(scenario_dict)
        self.grader = CascadeGrader(scenario_dict["scenario_id"], scenario_dict["ground_truth"])
        self.initial_health = self.state.system_health
        
        # Load pending failures from the scenario (e.g., slow memory leaks)
        self.pending_cascades = [
            {
                "node_id": f["node"],
                "failure_type": f["type"],
                "steps_until_propagation": f.get("degradation_delay_steps", 0)
            }
            for f in scenario_dict.get("failure_injections", [])
        ]
        self.last_action = {}

    def step(self, action: str, target: str, failure_type: str = None) -> dict:
        """Executes a single step in the environment."""
        if self.state.done:
            return {"error": "Episode already finished."}

        # --- Intercept for Hard H3 Decoy Wall ---
        if self.state.scenario_id == "hard_h3" and target == "payment_gateway":
            msg = "payment_gateway is an external service managed by a third-party. Circuit breaker has been active for 72 hours. This is expected baseline behavior. No available actions affect this service."
            self.state.step += 1
            self.state.steps_remaining -= 1
            self.state.intervention_log.append({"action": action, "target": target, "result": msg})
            
            if self.state.steps_remaining <= 0:
                self.state.done = True
                
            return {"observation": self.get_observation(), "message": msg, "done": self.state.done}

        # --- Process Normal Action ---
        self.state.step += 1
        self.state.steps_remaining -= 1
        self.last_action = {"action": action, "target": target}
        
        log_entry = {"action": action, "target": target}
        if failure_type: 
            log_entry["failure_type"] = failure_type

        # Action Logic
        if action == "observe":
            if target in self.state.nodes:
                self.state.nodes[target]["observable"] = True
                # Medium M3 Specific Log Reveal trap
                if self.state.scenario_id == "medium_m3" and target == "auth_service":
                    injections = self.scenario_dict.get("failure_injections", [])
                    if injections and "log_entry_on_observe" in injections[0]:
                        log_entry["log_revealed"] = injections[0]["log_entry_on_observe"]
                        
        elif action == "isolate":
            if target in self.state.nodes:
                self.state.nodes[target]["is_isolated"] = True
                
        elif action == "declare_root_cause":
            self.state.done = True
            log_entry["failure_type"] = failure_type

        self.state.intervention_log.append(log_entry)

        # Check step budget
        if self.state.steps_remaining <= 0 and not self.state.done:
            self.state.done = True

        # Run cascade engine to worsen the system if the agent didn't fix it
        if not self.state.done:
            self.pending_cascades = propagate_failures(self.state, self.pending_cascades, self.last_action)

        return {"observation": self.get_observation(), "done": self.state.done}

    def get_observation(self) -> dict:
        """Constructs the partial view of the system that the agent is allowed to see."""
        nodes_view = {}
        for node_id, node_data in self.state.nodes.items():
            nodes_view[node_id] = {
                "status": node_data["status"],
                "health": node_data["health"] if node_data["observable"] else "hidden",
                "visible_symptoms": node_data["visible_symptoms"],
                "is_isolated": node_data["is_isolated"]
            }
            
        # Compile active alerts based on health thresholds
        alerts = []
        for node_id, n_data in self.state.nodes.items():
            for symptom in n_data["visible_symptoms"]:
                h = n_data["health"]
                severity = "medium"
                if isinstance(h, (int, float)):
                    if h < 0.2: severity = "critical"
                    elif h < 0.5: severity = "high"
                alerts.append({"node": node_id, "type": symptom, "severity": severity})
                
        alerts = sorted(alerts, key=lambda x: ["critical","high","medium"].index(x["severity"]))

        return {
            "step": self.state.step,
            "steps_remaining": self.state.steps_remaining,
            "system_health": self.state.system_health,
            "nodes": nodes_view,
            "active_alerts": alerts,
            "intervention_log": self.state.intervention_log,
            "cascade_risk": "high" if self.state.system_health < 0.4 else "medium" if self.state.system_health < 0.7 else "low"
        }

    def get_score(self) -> dict:
        """Calls the grader to evaluate the entire episode."""
        return self.grader.score(
            episode_trace=self.state.intervention_log,
            final_system_health=self.state.system_health,
            initial_system_health=self.initial_health
        )