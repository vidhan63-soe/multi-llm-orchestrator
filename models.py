"""
Data models for tasks and results
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from config import TaskType


class Task(BaseModel):
    """A task to be routed and executed"""
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex[:8])
    type: TaskType
    prompt: str
    input_text: str
    max_budget_rupees: float = 10.0
    
    class Config:
        use_enum_values = True


class ModelResult(BaseModel):
    """Result from a single model execution"""
    success: bool
    model: str
    output: Optional[str] = None
    error: Optional[str] = None
    latency_ms: int
    cost_rupees: float
    tokens_in: int = 0
    tokens_out: int = 0
    timestamp: float = Field(default_factory=lambda: __import__('time').time())


class ExecutionResult(BaseModel):
    """Final result from orchestrator with fallback chain"""
    task_id: str
    task_type: str
    success: bool
    primary_model: str
    final_model: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    
    # Metrics
    total_latency_ms: int
    total_cost_rupees: float
    attempts: List[ModelResult]
    fallback_used: bool = False
    budget_exceeded: bool = False
    
    # SLA compliance
    sla_met: bool = False
    sla_violations: List[str] = []


class ShadowTestResult(BaseModel):
    """Result from shadow testing two models"""
    task_id: str
    task_type: str
    primary_result: ModelResult
    shadow_result: ModelResult
    
    # Comparison metrics
    accuracy_diff: float  # primary - shadow
    cost_diff_percent: float  # (primary - shadow) / shadow * 100
    latency_diff_ms: int  # primary - shadow
    
    winner: str  # which model performed better
    recommendation: Optional[str] = None
