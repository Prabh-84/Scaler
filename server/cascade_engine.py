# # server/cascade_engine.py
# from typing import List, Dict

# # The static architecture of our simulated microservice environment
# DEPENDENCY_GRAPH = {
#     "api_gateway":      ["auth_service", "product_service", "order_service", "cdn_cache"],
#     "auth_service":     ["user_db"],
#     "product_service":  ["postgres_primary"],
#     "order_service":    ["postgres_primary", "redis_cache"],
#     "postgres_primary": ["postgres_replica"],
#     "redis_cache":      ["redis_replica"],
#     "user_db":          [], 
#     "postgres_replica": [], 
#     "redis_replica":    [], 
#     "cdn_cache":        [], 
#     "payment_gateway":  []
# }/

# # How much a parent's health drops when a child fails
# DEPENDENCY_WEIGHTS = {
#     ("api_gateway", "auth_service"): 0.6,
#     ("api_gateway", "product_service"): 0.4,
#     ("api_gateway", "order_service"): 0.4,
#     ("order_service", "postgres_primary"): 0.7,
#     ("order_service", "redis_cache"): 0.4,
#     ("product_service", "postgres_primary"): 0.6,
#     ("auth_service", "user_db"): 0.8,
# }

# def propagate_failures(state, pending_cascades: list, last_action: dict) -> list:
#     """Runs every step to spread degradation based on active failures."""
    
#     # --- 1. Hardcoded Scenario Dynamics (The Traps) ---
    
#     # M1 False Recovery Trap (API Gateway restart gives a 1-step fake boost)
#     if state.scenario_id == "medium_m1" and last_action.get("action") == "restart" and last_action.get("target") == "api_gateway":
#         if not getattr(state, "m1_trap_active", False):
#             state.nodes["api_gateway"]["health"] = 0.65
#             state.m1_trap_active = True
#         else:
#             state.nodes["api_gateway"]["health"] = 0.40 # Reverts back to degraded
            
#     # H2 Amplification Loop (System actively worsens every step if not rolled back)
#     if state.scenario_id == "hard_h2":
#         # Check if the root cause (postgres_primary) has been rolled back
#         fixed = any(log.get("action") == "rollback" and log.get("target") == "postgres_primary" for log in state.intervention_log)
#         if not fixed:
#             if "postgres_primary" in state.nodes:
#                 current_health = state.nodes["postgres_primary"]["health"]
#                 if isinstance(current_health, (int, float)):
#                     state.nodes["postgres_primary"]["health"] = max(0.0, current_health - 0.10)
            
#             # Trap: Scaling the order service makes the postgres loop worse
#             if last_action.get("action") == "scale_replica" and last_action.get("target") == "order_service":
#                 if "postgres_primary" in state.nodes and isinstance(state.nodes["postgres_primary"]["health"], (int, float)):
#                     state.nodes["postgres_primary"]["health"] = max(0.0, state.nodes["postgres_primary"]["health"] - 0.10)

#     # --- 2. Standard Cascade Propagation ---
#     still_pending = []
#     for cascade in pending_cascades:
#         cascade["steps_until_propagation"] -= 1
#         if cascade["steps_until_propagation"] <= 0:
#             failed_node = cascade["node_id"]
#             if failed_node not in state.nodes:
#                 continue
                
#             failed_health = state.nodes[failed_node]["health"]
#             if not isinstance(failed_health, (int, float)):
#                 failed_health = 0.0 # Fallback if hidden
            
#             # Degrade parents
#             for parent_id, children in DEPENDENCY_GRAPH.items():
#                 if failed_node in children and parent_id in state.nodes:
#                     weight = DEPENDENCY_WEIGHTS.get((parent_id, failed_node), 0.3)
#                     parent = state.nodes[parent_id]
                    
#                     if isinstance(parent["health"], (int, float)):
#                         degradation = (1.0 - failed_health) * weight
#                         parent["health"] = round(max(0.0, parent["health"] - degradation), 3)
                        
#                         # Update visual status
#                         if parent["health"] < 0.2:
#                             parent["status"] = "critical"
#                         elif parent["health"] < 0.5:
#                             parent["status"] = "degraded"
#         else:
#             still_pending.append(cascade)
    
#     return still_pending


# server/cascade_engine.py
from typing import List, Dict

# The static architecture of our simulated microservice environment
DEPENDENCY_GRAPH = {
    "api_gateway":      ["auth_service", "product_service", "order_service", "cdn_cache"],
    "auth_service":     ["user_db"],
    "product_service":  ["postgres_primary", "postgres_replica"],  # BUG FIX: replica affects product_service (stale_data_responses in hard_h1)
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
    ("api_gateway", "auth_service"):        0.6,
    ("api_gateway", "product_service"):     0.4,
    ("api_gateway", "order_service"):       0.4,
    ("order_service", "postgres_primary"):  0.7,
    ("order_service", "redis_cache"):       0.4,
    ("product_service", "postgres_primary"): 0.6,
    ("product_service", "postgres_replica"): 0.35,  # BUG FIX: added weight for replica -> product_service
    ("auth_service", "user_db"):            0.8,
}

# How much health is restored to a parent when a child is fixed
RECOVERY_WEIGHTS = {
    ("api_gateway", "auth_service"):        0.5,
    ("api_gateway", "product_service"):     0.3,
    ("api_gateway", "order_service"):       0.3,
    ("order_service", "postgres_primary"):  0.6,
    ("order_service", "redis_cache"):       0.35,
    ("product_service", "postgres_primary"): 0.5,
    ("product_service", "postgres_replica"): 0.3,
    ("auth_service", "user_db"):            0.7,
}

# Actions that count as "fixing" a node
FIX_ACTIONS = {"restart", "rollback", "drain_connections", "reroute_traffic"}

# BUG FIX: Maximum health a node can recover to after a fix (it shouldn't go back to 1.0 magically)
RECOVERY_CAP = 0.85


def _apply_fix_recovery(state, fixed_node: str):
    """
    BUG FIX: When a node is fixed, restore partial health to its parent nodes.
    Previously, health degraded permanently — even a perfect agent was penalised
    on cascade_damage_score because parents never recovered.
    """
    for parent_id, children in DEPENDENCY_GRAPH.items():
        if fixed_node in children and parent_id in state.nodes:
            weight = RECOVERY_WEIGHTS.get((parent_id, fixed_node), 0.2)
            parent = state.nodes[parent_id]
            if isinstance(parent["health"], (int, float)):
                parent["health"] = round(min(RECOVERY_CAP, parent["health"] + weight * 0.8), 3)
                # Update visual status after recovery
                if parent["health"] >= 0.7:
                    parent["status"] = "healthy"
                elif parent["health"] >= 0.4:
                    parent["status"] = "degraded"
                else:
                    parent["status"] = "critical"


def propagate_failures(state, pending_cascades: list, last_action: dict) -> list:
    """Runs every step to spread degradation based on active failures."""

    # --- 1. Hardcoded Scenario Dynamics (The Traps) ---

    # M1 False Recovery Trap (API Gateway restart gives a 1-step fake boost)
    if state.scenario_id == "medium_m1" and last_action.get("action") == "restart" and last_action.get("target") == "api_gateway":
        # BUG FIX: getattr with default is correct; flag is set on the state object per-episode.
        # The flag is naturally scoped to the SystemState instance so it resets on /reset.
        if not getattr(state, "m1_trap_active", False):
            state.nodes["api_gateway"]["health"] = 0.65
            state.m1_trap_active = True
        else:
            state.nodes["api_gateway"]["health"] = 0.40  # Reverts back to degraded

    # H2 Amplification Loop (System actively worsens every step if not rolled back)
    if state.scenario_id == "hard_h2":
        fixed = any(
            log.get("action") == "rollback" and log.get("target") == "postgres_primary"
            for log in state.intervention_log
        )
        if not fixed:
            if "postgres_primary" in state.nodes:
                current_health = state.nodes["postgres_primary"]["health"]
                if isinstance(current_health, (int, float)):
                    state.nodes["postgres_primary"]["health"] = max(0.0, round(current_health - 0.10, 3))

            # Trap: Scaling the order service makes the postgres loop worse
            if last_action.get("action") == "scale_replica" and last_action.get("target") == "order_service":
                if "postgres_primary" in state.nodes and isinstance(state.nodes["postgres_primary"]["health"], (int, float)):
                    state.nodes["postgres_primary"]["health"] = max(0.0, round(state.nodes["postgres_primary"]["health"] - 0.10, 3))
        else:
            # BUG FIX: If postgres_primary was rolled back, let parents recover
            _apply_fix_recovery(state, "postgres_primary")

    # --- 2. BUG FIX: Handle fix actions — restore parent health ---
    action_type = last_action.get("action")
    action_target = last_action.get("target")
    if action_type in FIX_ACTIONS and action_target and state.scenario_id != "hard_h2":
        # hard_h2 recovery is handled by its own loop above
        if action_target in state.nodes:
            # Restore the fixed node's own health
            node = state.nodes[action_target]
            if isinstance(node["health"], (int, float)) and node["health"] < RECOVERY_CAP:
                node["health"] = round(min(RECOVERY_CAP, node["health"] + 0.6), 3)
                if node["health"] >= 0.7:
                    node["status"] = "healthy"
                elif node["health"] >= 0.4:
                    node["status"] = "degraded"
            _apply_fix_recovery(state, action_target)

    # --- 3. Standard Cascade Propagation ---
    still_pending = []
    for cascade in pending_cascades:
        cascade["steps_until_propagation"] -= 1
        if cascade["steps_until_propagation"] <= 0:
            failed_node = cascade["node_id"]
            if failed_node not in state.nodes:
                continue

            failed_health = state.nodes[failed_node]["health"]
            if not isinstance(failed_health, (int, float)):
                failed_health = 0.0  # Fallback if hidden

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
