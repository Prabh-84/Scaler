# # server/grader.py
# from typing import List, Dict

# class CascadeGrader:
#     def __init__(self, scenario_id: str, ground_truth: dict):
#         self.ground_truth = ground_truth
#         self.scenario_id = scenario_id
    
#     def score(self, episode_trace: List[dict], final_system_health: float, initial_system_health: float) -> dict:
#         d1 = self._root_cause_accuracy(episode_trace)
#         d2 = self._intervention_order_score(episode_trace)
#         d3 = self._cascade_damage_score(final_system_health, initial_system_health)
#         d4 = self._step_efficiency(episode_trace)
        
#         # Weighted Final Score
#         total = (0.35 * d1) + (0.30 * d2) + (0.25 * d3) + (0.10 * d4)
        
#         return {
#             "scenario_id": self.scenario_id,
#             "root_cause_accuracy": round(d1, 3),
#             "intervention_order":  round(d2, 3),
#             "cascade_damage":      round(d3, 3),
#             "step_efficiency":     round(d4, 3),
#             "total":               round(total, 3),
#             "breakdown": {
#                 "correct_root_cause": self._get_declared_root_cause(episode_trace),
#                 "ground_truth_root_cause": self.ground_truth.get("root_cause_node")
#             }
#         }
    
#     def _root_cause_accuracy(self, trace: List[dict]) -> float:
#         declarations = [a for a in trace if a.get("action") == "declare_root_cause"]
#         if not declarations: 
#             return 0.0
        
#         score = 0.0
#         # Check primary root cause
#         primary_node = self.ground_truth.get("root_cause_node")
#         primary_type = self.ground_truth.get("root_cause_type")
        
#         for dec in declarations:
#             if dec.get("target") == primary_node:
#                 score += 0.5 if dec.get("failure_type") != primary_type else 1.0
        
#         # Check secondary root cause (e.g., for Hard H1 Scenario)
#         sec = self.ground_truth.get("secondary_root_cause")
#         if sec:
#             score = score / 2.0  # Max 0.5 for primary if a secondary exists
#             for dec in declarations:
#                 if dec.get("target") == sec.get("node"):
#                     score += 0.25 if dec.get("failure_type") != sec.get("type") else 0.5
                    
#         return min(1.0, score)
    
#     def _intervention_order_score(self, trace: List[dict]) -> float:
#         score = 1.0
#         observed_nodes = set()
#         IRREVERSIBLE = {"isolate", "restart", "rollback"}
#         INTERVENTION = {"isolate", "restart", "rollback", "drain_connections", "reroute_traffic", "scale_replica"}
        
#         for action in trace:
#             action_type = action.get("action")
#             target = action.get("target")
            
#             if action_type == "observe": 
#                 observed_nodes.add(target)
#             elif action_type in INTERVENTION:
#                 # Penalize acting without observing first
#                 if target not in observed_nodes: 
#                     score -= 0.15 
#                 # Penalize irreversible actions on the wrong node
#                 if action_type in IRREVERSIBLE and target != self.ground_truth.get("root_cause_node"):
#                     score -= 0.25 
            
#             # Penalize falling for specific traps defined in the JSON
#             trap_nodes = [t.get("node") for t in self.ground_truth.get("trap_actions_nodes", []) if isinstance(t, dict)]
#             trap_strings = [t.get("action") + ":" + t.get("target", "") for t in self.ground_truth.get("trap_actions", []) if isinstance(t, dict)]
            
#             if target in trap_nodes or f"{action_type}:{target}" in trap_strings:
#                 score -= 0.10
                
#         return max(0.0, score)
    
#     def _cascade_damage_score(self, final_health: float, initial_health: float) -> float:
#         if initial_health == 0: 
#             return 0.0
#         return min(1.0, max(0.0, final_health / initial_health))
    
#     def _step_efficiency(self, trace: List[dict]) -> float:
#         optimal = self.ground_truth.get("optimal_steps", 5)
#         actual = len(trace)
#         if actual == 0: 
#             return 0.0
#         return min(1.0, optimal / actual)
    
#     def _get_declared_root_cause(self, trace: List[dict]):
#         for action in trace:
#             if action.get("action") == "declare_root_cause":
#                 return {"node": action.get("target"), "failure_type": action.get("failure_type")}
#         return None



# server/grader.py
# from typing import List, Dict


# class CascadeGrader:
#     def __init__(self, scenario_id: str, ground_truth: dict):
#         self.ground_truth = ground_truth
#         self.scenario_id = scenario_id

#     def score(self, episode_trace: List[dict], final_system_health: float, initial_system_health: float) -> dict:
#         d1 = self._root_cause_accuracy(episode_trace)
#         d2 = self._intervention_order_score(episode_trace)
#         d3 = self._cascade_damage_score(final_system_health, initial_system_health)
#         d4 = self._step_efficiency(episode_trace)

#         # Weighted Final Score
#         total = (0.35 * d1) + (0.30 * d2) + (0.25 * d3) + (0.10 * d4)

#         return {
#             "scenario_id": self.scenario_id,
#             "root_cause_accuracy": round(d1, 3),
#             "intervention_order":  round(d2, 3),
#             "cascade_damage":      round(d3, 3),
#             "step_efficiency":     round(d4, 3),
#             "total":               round(total, 3),
#             "breakdown": {
#                 "correct_root_cause": self._get_declared_root_cause(episode_trace),
#                 "ground_truth_root_cause": self.ground_truth.get("root_cause_node")
#             }
#         }

#     def _root_cause_accuracy(self, trace: List[dict]) -> float:
#         declarations = [a for a in trace if a.get("action") == "declare_root_cause"]
#         if not declarations:
#             return 0.0

#         primary_node = self.ground_truth.get("root_cause_node")
#         primary_type = self.ground_truth.get("root_cause_type")
#         sec = self.ground_truth.get("secondary_root_cause")

#         # BUG FIX: Use only the FIRST declaration for primary and secondary,
#         # not a loop that can accumulate score from multiple declare calls.
#         primary_score = 0.0
#         secondary_score = 0.0
#         primary_declared = False
#         secondary_declared = False

#         for dec in declarations:
#             if not primary_declared and dec.get("target") == primary_node:
#                 primary_score = 0.5 if dec.get("failure_type") != primary_type else 1.0
#                 primary_declared = True
#             if sec and not secondary_declared and dec.get("target") == sec.get("node"):
#                 secondary_score = 0.25 if dec.get("failure_type") != sec.get("type") else 0.5
#                 secondary_declared = True

#         if sec:
#             # Max 0.5 for primary + max 0.5 for secondary = 1.0 total
#             total = (primary_score / 2.0) + secondary_score
#         else:
#             total = primary_score

#         return min(1.0, total)

#     def _intervention_order_score(self, trace: List[dict]) -> float:
#         score = 1.0
#         observed_nodes = set()
#         IRREVERSIBLE = {"isolate", "restart", "rollback"}
#         INTERVENTION = {"isolate", "restart", "rollback", "drain_connections", "reroute_traffic", "scale_replica"}

#         # BUG FIX: Build trap sets ONCE outside the loop, not inside (was recomputed every iteration)
#         # BUG FIX: Key was "trap_actions_nodes" (doesn't exist in any scenario JSON).
#         #          The correct key is "trap_actions" — extract node targets from that list.
#         trap_actions_list = [t for t in self.ground_truth.get("trap_actions", []) if isinstance(t, dict)]
#         trap_nodes = {t.get("target") for t in trap_actions_list if t.get("target")}
#         trap_strings = {t.get("action", "") + ":" + t.get("target", "") for t in trap_actions_list}

#         for action in trace:
#             action_type = action.get("action")
#             target = action.get("target")

#             if action_type == "observe":
#                 observed_nodes.add(target)
#             elif action_type in INTERVENTION:
#                 # Penalize acting without observing first
#                 if target not in observed_nodes:
#                     score -= 0.15
#                 # Penalize irreversible actions on the wrong node
#                 if action_type in IRREVERSIBLE and target != self.ground_truth.get("root_cause_node"):
#                     score -= 0.25

#             # Penalize falling for specific traps
#             if target in trap_nodes or f"{action_type}:{target}" in trap_strings:
#                 score -= 0.10

#         return max(0.0, score)

#     def _cascade_damage_score(self, final_health: float, initial_health: float) -> float:
#         if initial_health == 0:
#             return 0.0
#         return min(1.0, max(0.0, final_health / initial_health))

#     def _step_efficiency(self, trace: List[dict]) -> float:
#         optimal = self.ground_truth.get("optimal_steps", 5)
#         actual = len(trace)
#         if actual == 0:
#             return 0.0
#         return min(1.0, optimal / actual)

#     def _get_declared_root_cause(self, trace: List[dict]):
#         for action in trace:
#             if action.get("action") == "declare_root_cause":
#                 return {"node": action.get("target"), "failure_type": action.get("failure_type")}
#         return None


# server/grader.py
# FIXES applied:
#   1. _intervention_order_score: trap_nodes was built from key "trap_actions_nodes"
#      which DOES NOT EXIST in any scenario JSON. The correct key is "trap_actions".
#      This meant node-based trap penalties never fired at all.
#   2. _intervention_order_score: trap sets were recomputed inside the action loop
#      on every iteration — moved outside to O(1) lookup sets.
#   3. _root_cause_accuracy: looping over all declarations and summing score means
#      calling declare_root_cause twice on the same correct node doubled the score
#      to 2.0 (capped at 1.0 by min(), but the math was wrong for secondary causes).
#      Now only the FIRST matching declaration per node counts.
#   4. _intervention_order_score: the irreversible-action penalty compared target
#      only to the PRIMARY root_cause_node. For hard_h1 (dual failure), acting
#      on the secondary root cause node was incorrectly penalised.

from typing import List, Dict


class CascadeGrader:
    def __init__(self, scenario_id: str, ground_truth: dict):
        self.ground_truth = ground_truth
        self.scenario_id = scenario_id

    def score(
        self,
        episode_trace: List[dict],
        final_system_health: float,
        initial_system_health: float,
    ) -> dict:
        d1 = self._root_cause_accuracy(episode_trace)
        d2 = self._intervention_order_score(episode_trace)
        d3 = self._cascade_damage_score(final_system_health, initial_system_health)
        d4 = self._step_efficiency(episode_trace)

        total = (0.35 * d1) + (0.30 * d2) + (0.25 * d3) + (0.10 * d4)

        return {
            "scenario_id": self.scenario_id,
            "root_cause_accuracy": round(d1, 3),
            "intervention_order": round(d2, 3),
            "cascade_damage": round(d3, 3),
            "step_efficiency": round(d4, 3),
            "total": round(total, 3),
            "breakdown": {
                "correct_root_cause": self._get_declared_root_cause(episode_trace),
                "ground_truth_root_cause": self.ground_truth.get("root_cause_node"),
            },
        }

    def _root_cause_accuracy(self, trace: List[dict]) -> float:
        declarations = [a for a in trace if a.get("action") == "declare_root_cause"]
        if not declarations:
            return 0.0

        primary_node = self.ground_truth.get("root_cause_node")
        primary_type = self.ground_truth.get("root_cause_type")
        sec = self.ground_truth.get("secondary_root_cause")

        # FIX 3: Track whether each root cause has already been matched.
        # Old loop accumulated score across ALL declarations, so two correct
        # declarations gave score=2.0 (then min-clamped to 1.0).
        primary_score = 0.0
        secondary_score = 0.0
        primary_matched = False
        secondary_matched = False

        for dec in declarations:
            if not primary_matched and dec.get("target") == primary_node:
                primary_score = (
                    0.5 if dec.get("failure_type") != primary_type else 1.0
                )
                primary_matched = True

            if sec and not secondary_matched and dec.get("target") == sec.get("node"):
                secondary_score = (
                    0.25 if dec.get("failure_type") != sec.get("type") else 0.5
                )
                secondary_matched = True

        if sec:
            # Max 0.5 for primary + max 0.5 for secondary = 1.0 total
            total = (primary_score / 2.0) + secondary_score
        else:
            total = primary_score

        return min(1.0, total)

    def _intervention_order_score(self, trace: List[dict]) -> float:
        score = 1.0
        observed_nodes = set()
        IRREVERSIBLE = {"isolate", "restart", "rollback"}
        INTERVENTION = {
            "isolate", "restart", "rollback",
            "drain_connections", "reroute_traffic", "scale_replica",
        }

        # FIX 1 + 2: Build trap sets ONCE outside the loop using the CORRECT key.
        # Old code used "trap_actions_nodes" — that key does not exist in any scenario
        # JSON, so trap_nodes was always an empty list and the trap penalty never fired.
        trap_actions_list = [
            t for t in self.ground_truth.get("trap_actions", [])
            if isinstance(t, dict)
        ]
        trap_nodes = {t.get("target") for t in trap_actions_list if t.get("target")}
        trap_strings = {
            t.get("action", "") + ":" + t.get("target", "")
            for t in trap_actions_list
        }

        # FIX 4: Collect ALL legitimate root cause nodes (primary + secondary).
        # Old code only checked primary — acting on the secondary in hard_h1 was
        # wrongly penalised as an irreversible action on the "wrong" node.
        valid_root_nodes = {self.ground_truth.get("root_cause_node")}
        sec = self.ground_truth.get("secondary_root_cause")
        if sec and sec.get("node"):
            valid_root_nodes.add(sec["node"])

        for action in trace:
            action_type = action.get("action")
            target = action.get("target")

            if action_type == "observe":
                observed_nodes.add(target)
            elif action_type in INTERVENTION:
                # Penalise acting on a node that was never observed first
                if target not in observed_nodes:
                    score -= 0.15
                # Penalise irreversible actions on any node that is NOT a root cause
                if action_type in IRREVERSIBLE and target not in valid_root_nodes:
                    score -= 0.25

            # Penalise documented trap actions
            if target in trap_nodes or f"{action_type}:{target}" in trap_strings:
                score -= 0.10

        return max(0.0, score)

    def _cascade_damage_score(self, final_health: float, initial_health: float) -> float:
        if initial_health == 0:
            return 0.0
        return min(1.0, max(0.0, final_health / initial_health))

    def _step_efficiency(self, trace: List[dict]) -> float:
        optimal = self.ground_truth.get("optimal_steps", 5)
        actual = len(trace)
        if actual == 0:
            return 0.0
        return min(1.0, optimal / actual)

    def _get_declared_root_cause(self, trace: List[dict]):
        for action in trace:
            if action.get("action") == "declare_root_cause":
                return {
                    "node": action.get("target"),
                    "failure_type": action.get("failure_type"),
                }
        return None
