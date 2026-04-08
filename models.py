
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
