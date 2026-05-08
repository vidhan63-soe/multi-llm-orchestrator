"""
Model configurations and constants for the Orchestrator
"""
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class TaskType(str, Enum):
    """GrabOn-specific task types"""
    DEAL_EXTRACTION = "deal_extraction"
    INSURANCE_INTENT = "insurance_intent"
    CREDIT_NARRATIVE = "credit_narrative"
    DEAL_COPY_GENERATION = "deal_copy_generation"
    ATTRIBUTION_ANALYSIS = "attribution_analysis"
    HINDI_LOCALIZATION = "hindi_localization"


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model"""
    provider: Literal["openai", "anthropic", "google", "groq"]
    model_name: str
    cost_per_1k_input_usd: float  # USD per 1K input tokens
    cost_per_1k_output_usd: float  # USD per 1K output tokens
    avg_latency_ms: int
    quality_tier: Literal["low", "medium", "high", "ultra"]
    max_tokens: int = 4096


# Model Registry
MODELS = {
    # Groq Models (FREE & SUPER FAST!)
    "llama-70b": ModelConfig(
        provider="groq",
        model_name="llama-3.1-70b-versatile",
        cost_per_1k_input_usd=0.00,  # FREE!
        cost_per_1k_output_usd=0.00,  # FREE!
        avg_latency_ms=150,  # Ultra fast
        quality_tier="high"
    ),
    "llama-8b": ModelConfig(
        provider="groq",
        model_name="llama-3.1-8b-instant",
        cost_per_1k_input_usd=0.00,  # FREE!
        cost_per_1k_output_usd=0.00,  # FREE!
        avg_latency_ms=100,  # Blazing fast
        quality_tier="medium"
    ),
    
    # OpenAI Models
    "gpt-4o": ModelConfig(
        provider="openai",
        model_name="gpt-4o",
        cost_per_1k_input_usd=2.50,
        cost_per_1k_output_usd=10.00,
        avg_latency_ms=800,
        quality_tier="ultra"
    ),
    "gpt-4o-mini": ModelConfig(
        provider="openai",
        model_name="gpt-4o-mini",
        cost_per_1k_input_usd=0.15,
        cost_per_1k_output_usd=0.60,
        avg_latency_ms=400,
        quality_tier="medium"
    ),
    
    # Anthropic Models
    "claude-sonnet-4": ModelConfig(
        provider="anthropic",
        model_name="claude-sonnet-4-20250514",
        cost_per_1k_input_usd=3.00,
        cost_per_1k_output_usd=15.00,
        avg_latency_ms=700,
        quality_tier="ultra"
    ),
    "claude-haiku": ModelConfig(
        provider="anthropic",
        model_name="claude-haiku-3-5-20241022",
        cost_per_1k_input_usd=0.80,
        cost_per_1k_output_usd=4.00,
        avg_latency_ms=300,
        quality_tier="medium"
    ),
    
    # Google Models
    "gemini-pro": ModelConfig(
        provider="google",
        model_name="gemini-1.5-pro",
        cost_per_1k_input_usd=1.25,
        cost_per_1k_output_usd=5.00,
        avg_latency_ms=600,
        quality_tier="high"
    ),
    "gemini-flash": ModelConfig(
        provider="google",
        model_name="gemini-1.5-flash",
        cost_per_1k_input_usd=0.075,
        cost_per_1k_output_usd=0.30,
        avg_latency_ms=250,
        quality_tier="medium"
    ),
}


@dataclass
class SLA:
    """Service Level Agreement for a task type"""
    max_latency_ms: int
    max_cost_rupees: float
    min_accuracy: float


# Task-specific SLAs
TASK_SLAS = {
    TaskType.DEAL_EXTRACTION: SLA(
        max_latency_ms=2000,
        max_cost_rupees=1.0,
        min_accuracy=0.85
    ),
    TaskType.INSURANCE_INTENT: SLA(
        max_latency_ms=500,
        max_cost_rupees=0.5,
        min_accuracy=0.95
    ),
    TaskType.CREDIT_NARRATIVE: SLA(
        max_latency_ms=5000,
        max_cost_rupees=2.0,
        min_accuracy=0.95
    ),
    TaskType.DEAL_COPY_GENERATION: SLA(
        max_latency_ms=3000,
        max_cost_rupees=0.5,
        min_accuracy=0.80
    ),
    TaskType.ATTRIBUTION_ANALYSIS: SLA(
        max_latency_ms=4000,
        max_cost_rupees=1.5,
        min_accuracy=0.90
    ),
    TaskType.HINDI_LOCALIZATION: SLA(
        max_latency_ms=2000,
        max_cost_rupees=1.0,
        min_accuracy=0.85
    ),
}


# Constants
USD_TO_INR = 83.0  # Conversion rate
GRABON_ANNUAL_TASKS = 96_000_000  # 96M tasks per year

# Task distribution at GrabOn scale (percentage)
TASK_DISTRIBUTION = {
    TaskType.DEAL_EXTRACTION: 0.60,  # 60% - 57.6M tasks
    TaskType.INSURANCE_INTENT: 0.20,  # 20% - 19.2M tasks
    TaskType.CREDIT_NARRATIVE: 0.10,  # 10% - 9.6M tasks
    TaskType.DEAL_COPY_GENERATION: 0.05,  # 5% - 4.8M tasks
    TaskType.ATTRIBUTION_ANALYSIS: 0.03,  # 3% - 2.88M tasks
    TaskType.HINDI_LOCALIZATION: 0.02,  # 2% - 1.92M tasks
}
