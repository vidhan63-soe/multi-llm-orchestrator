"""
Routing policies for model selection
"""
from abc import ABC, abstractmethod
from typing import Protocol
from config import TaskType, MODELS


class RoutingPolicy(ABC):
    """Abstract base class for routing policies"""
    
    @abstractmethod
    def select_model(self, task_type: TaskType) -> str:
        """Select a model for the given task type"""
        pass
    
    @abstractmethod
    def get_fallback_chain(self, primary_model: str, task_type: TaskType) -> list[str]:
        """Get fallback models for the primary model"""
        pass


class CostMinimizingPolicy(RoutingPolicy):
    """
    Selects the cheapest model that meets minimum quality requirements.
    Use for high-volume, cost-sensitive workloads.
    """
    
    def select_model(self, task_type: TaskType) -> str:
        """Select cheapest model per task type"""
        routing = {
            TaskType.DEAL_EXTRACTION: "llama-8b",  # FREE & fast for extraction
            TaskType.INSURANCE_INTENT: "llama-8b",  # FREE & perfect for classification
            TaskType.CREDIT_NARRATIVE: "llama-70b",  # FREE but high quality
            TaskType.DEAL_COPY_GENERATION: "llama-8b",  # FREE, creative enough
            TaskType.ATTRIBUTION_ANALYSIS: "llama-70b",  # FREE, analytical
            TaskType.HINDI_LOCALIZATION: "gemini-flash",  # Better multilingual
        }
        return routing[task_type]
    
    def get_fallback_chain(self, primary_model: str, task_type: TaskType) -> list[str]:
        """Fallback to other cheap/free models"""
        cheap_models = ["llama-8b", "llama-70b", "gemini-flash", "gpt-4o-mini"]
        return [m for m in cheap_models if m != primary_model][:2]


class QualityMaximizingPolicy(RoutingPolicy):
    """
    Selects the highest quality model regardless of cost.
    Use for compliance-critical or high-stakes workloads.
    """
    
    def select_model(self, task_type: TaskType) -> str:
        """Select best quality model per task type"""
        routing = {
            TaskType.DEAL_EXTRACTION: "gemini-pro",  # Good at structured extraction
            TaskType.INSURANCE_INTENT: "gpt-4o",  # High accuracy needed
            TaskType.CREDIT_NARRATIVE: "claude-sonnet-4",  # Best for compliance narratives
            TaskType.DEAL_COPY_GENERATION: "gpt-4o",  # Creative + persuasive
            TaskType.ATTRIBUTION_ANALYSIS: "claude-sonnet-4",  # Complex reasoning
            TaskType.HINDI_LOCALIZATION: "gemini-pro",  # Best multilingual
        }
        return routing[task_type]
    
    def get_fallback_chain(self, primary_model: str, task_type: TaskType) -> list[str]:
        """Fallback to other high-quality models"""
        quality_models = ["claude-sonnet-4", "gpt-4o", "gemini-pro"]
        return [m for m in quality_models if m != primary_model][:2]


class LatencyMinimizingPolicy(RoutingPolicy):
    """
    Selects the fastest model to meet strict latency SLAs.
    Use for real-time, user-facing workloads like checkout.
    """
    
    def select_model(self, task_type: TaskType) -> str:
        """Select fastest model per task type"""
        # Sort models by latency
        sorted_models = sorted(
            MODELS.items(),
            key=lambda x: x[1].avg_latency_ms
        )
        
        # For critical latency tasks, use fastest
        if task_type == TaskType.INSURANCE_INTENT:
            return "gemini-flash"  # 250ms - fastest
        
        # For others, use fast medium-tier models
        return "claude-haiku"  # 300ms - fast + decent quality
    
    def get_fallback_chain(self, primary_model: str, task_type: TaskType) -> list[str]:
        """Fallback to other fast models"""
        fast_models = ["gemini-flash", "claude-haiku", "gpt-4o-mini"]
        return [m for m in fast_models if m != primary_model][:2]


class BalancedPolicy(RoutingPolicy):
    """
    Balances cost, quality, and latency based on task requirements.
    Production-recommended policy with Groq for speed/cost optimization.
    """
    
    def select_model(self, task_type: TaskType) -> str:
        """Select balanced model per task type"""
        routing = {
            TaskType.DEAL_EXTRACTION: "llama-8b",  # FREE & fast enough
            TaskType.INSURANCE_INTENT: "llama-8b",  # Speed critical + FREE
            TaskType.CREDIT_NARRATIVE: "claude-sonnet-4",  # Quality critical
            TaskType.DEAL_COPY_GENERATION: "llama-70b",  # Creative + FREE
            TaskType.ATTRIBUTION_ANALYSIS: "llama-70b",  # Analytical + FREE
            TaskType.HINDI_LOCALIZATION: "gemini-flash",  # Language + cost
        }
        return routing[task_type]
    
    def get_fallback_chain(self, primary_model: str, task_type: TaskType) -> list[str]:
        """Task-specific fallback chains"""
        chains = {
            TaskType.DEAL_EXTRACTION: ["llama-8b", "llama-70b", "gemini-flash"],
            TaskType.INSURANCE_INTENT: ["llama-8b", "gemini-flash", "gpt-4o-mini"],
            TaskType.CREDIT_NARRATIVE: ["claude-sonnet-4", "llama-70b", "gpt-4o"],
            TaskType.DEAL_COPY_GENERATION: ["llama-70b", "llama-8b", "gpt-4o-mini"],
            TaskType.ATTRIBUTION_ANALYSIS: ["llama-70b", "gemini-pro", "gpt-4o"],
            TaskType.HINDI_LOCALIZATION: ["gemini-flash", "gemini-pro", "llama-70b"],
        }
        
        chain = chains.get(task_type, ["llama-8b", "llama-70b", "gemini-flash"])
        return [m for m in chain if m != primary_model][:2]


# Policy registry
POLICIES = {
    "cost": CostMinimizingPolicy(),
    "quality": QualityMaximizingPolicy(),
    "latency": LatencyMinimizingPolicy(),
    "balanced": BalancedPolicy(),
}
