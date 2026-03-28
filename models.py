# from pydantic import BaseModel, Field
# from typing import List, Dict, Optional
# from enum import Enum
# from openenv.core.models import Action, Observation

# class FailureType(str, Enum):
#     CRASH = "crash"
#     MEMORY_LEAK = "memory_leak"
#     CONN_EXHAUSTION = "connection_exhaustion"
#     NETWORK_LATENCY = "network_latency"

# class CascadeAction(Action):
#     """The commands the agent can run."""
#     cmd: str = Field(..., description="observe, restart, isolate, rollback, or declare_root_cause")
#     node_id: str = Field(..., description="Target node ID (e.g., 'postgres_primary')")
#     declared_failure: Optional[FailureType] = Field(None)

# class NodeInfo(BaseModel): 
#     status: str  # "healthy", "degraded", "critical", "hidden"
#     latency_ms: float
#     is_observable: bool = False

# class CascadeObservation(Observation):
#     """The dashboard provided to the agent at each step."""
#     system_health: float = Field(..., ge=0.0, le=1.0)
#     nodes: Dict[str, NodeInfo]
#     steps_remaining: int
#     active_alerts: List[str]
# from pydantic import BaseModel
# from typing import Dict, List, Optional, Union, Any

# class Action(BaseModel):
#     action: str
#     target: str
#     failure_type: Optional[str] = None

# class NodeView(BaseModel):
#     status: str
#     health: Union[float, str]
#     visible_symptoms: List[str]
#     is_isolated: bool

# class Observation(BaseModel):
#     step: int
#     steps_remaining: int
#     system_health: float
#     nodes: Dict[str, NodeView]
#     active_alerts: List[dict]
#     intervention_log: List[dict]
#     cascade_risk: str

# # --- NEW: Strict OpenEnv Return Models ---
# class StepResponse(BaseModel):
#     observation: Observation
#     reward: float  # Required by spec
#     done: bool     # Required by spec
#     info: Dict[str, Any] # Required by spec

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Any


class Action(BaseModel):
    action: str
    target: str
    failure_type: Optional[str] = None


class NodeView(BaseModel):
    status: str
    health: Union[float, str]
    visible_symptoms: List[str]
    is_isolated: bool


class Observation(BaseModel):
    step: int
    steps_remaining: int
    system_health: float
    nodes: Dict[str, NodeView]
    active_alerts: List[dict]
    intervention_log: List[dict]
    cascade_risk: str


class StepResponse(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)