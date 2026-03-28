# server/cascade_engine.py
from typing import List, Dict

# The static architecture of our simulated microservice environment
DEPENDENCY_GRAPH = {
    "api_gateway":      ["auth_service", "product_service", "order_service", "cdn_cache"],
    "auth_service":     ["user_db"],
    "product_service":  ["postgres_primary"],
    "order_service":    ["postgres_primary", "redis_cache"],
    "postgres_primary": ["postgres_replica"],
    "redis_cache":      ["redis_replica"],
    "user_db":          [], 
    "postgres_replica": [], 
    "redis_replica":    [], 
    "cdn_cache":        [], 
    "payment_gateway":  []
}

# How much a parent's health drops when a child fails
DEPENDENCY_WEIGHTS = {
    ("api_gateway", "auth_service"): 0.6,
    ("api_gateway", "product_service"): 0.4,
    ("api_gateway", "order_service"): 0.4,
    ("order_service", "postgres_primary"): 0.7,
    ("order_service", "redis_cache"): 0.4,
    ("product_service", "postgres_primary"): 0.6,
    ("auth_service", "user_db"): 0.8,
}

def propagate_failures(state, pending_cascades: list, last_action: dict) -> list:
    """Runs every step to spread degradation based on active failures."""
    
    # --- 1. Hardcoded Scenario Dynamics (The Traps) ---
    
    # M1 False Recovery Trap (API Gateway restart gives a 1-step fake boost)
    if state.scenario_id == "medium_m1" and last_action.get("action") == "restart" and last_action.get("target") == "api_gateway":
        if not getattr(state, "m1_trap_active", False):
            state.nodes["api_gateway"]["health"] = 0.65
            state.m1_trap_active = True
        else:
            state.nodes["api_gateway"]["health"] = 0.40 # Reverts back to degraded
            
    # H2 Amplification Loop (System actively worsens every step if not rolled back)
    if state.scenario_id == "hard_h2":
        # Check if the root cause (postgres_primary) has been rolled back
        fixed = any(log.get("action") == "rollback" and log.get("target") == "postgres_primary" for log in state.intervention_log)
        if not fixed:
            if "postgres_primary" in state.nodes:
                current_health = state.nodes["postgres_primary"]["health"]
                if isinstance(current_health, (int, float)):
                    state.nodes["postgres_primary"]["health"] = max(0.0, current_health - 0.10)
            
            # Trap: Scaling the order service makes the postgres loop worse
            if last_action.get("action") == "scale_replica" and last_action.get("target") == "order_service":
                if "postgres_primary" in state.nodes and isinstance(state.nodes["postgres_primary"]["health"], (int, float)):
                    state.nodes["postgres_primary"]["health"] = max(0.0, state.nodes["postgres_primary"]["health"] - 0.10)

    # --- 2. Standard Cascade Propagation ---
    still_pending = []
    for cascade in pending_cascades:
        cascade["steps_until_propagation"] -= 1
        if cascade["steps_until_propagation"] <= 0:
            failed_node = cascade["node_id"]
            if failed_node not in state.nodes:
                continue
                
            failed_health = state.nodes[failed_node]["health"]
            if not isinstance(failed_health, (int, float)):
                failed_health = 0.0 # Fallback if hidden
            
            # Degrade parents
            for parent_id, children in DEPENDENCY_GRAPH.items():
                if failed_node in children and parent_id in state.nodes:
                    weight = DEPENDENCY_WEIGHTS.get((parent_id, failed_node), 0.3)
                    parent = state.nodes[parent_id]
                    
                    if isinstance(parent["health"], (int, float)):
                        degradation = (1.0 - failed_health) * weight
                        parent["health"] = round(max(0.0, parent["health"] - degradation), 3)
                        
                        # Update visual status
                        if parent["health"] < 0.2:
                            parent["status"] = "critical"
                        elif parent["health"] < 0.5:
                            parent["status"] = "degraded"
        else:
            still_pending.append(cascade)
    
    return still_pending