"""
Core Orchestrator Engine with multi-LLM routing and fallback chains
"""
import os
import time
import random
from typing import Optional
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

from config import MODELS, TASK_SLAS, USD_TO_INR
from models import Task, ModelResult, ExecutionResult
from policies import RoutingPolicy


class Orchestrator:
    """
    Multi-LLM orchestration engine with intelligent routing and fallback chains
    """
    
    def __init__(self, mock_mode: bool = False):
        """Initialize API clients"""
        self.mock_mode = mock_mode or os.getenv("MOCK_MODE", "false").lower() == "true"
        
        if not self.mock_mode:
            # Check if using Azure OpenAI
            self.use_azure = os.getenv("USE_AZURE_OPENAI", "false").lower() == "true"
            
            if self.use_azure:
                # Azure OpenAI client
                from openai import AzureOpenAI
                self.openai_client = AzureOpenAI(
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
                )
                # Store deployment names
                self.azure_deployments = {
                    "gpt-4o": os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O", "gpt-4o"),
                    "gpt-4o-mini": os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O_MINI", "gpt-4o-mini")
                }
            else:
                # Direct OpenAI client
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Groq client (uses OpenAI-compatible API)
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                self.groq_client = OpenAI(
                    api_key=groq_key,
                    base_url="https://api.groq.com/openai/v1"
                )
            else:
                self.groq_client = None
            
            self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        self.execution_history = []
        
    def call_model(self, model_name: str, task: Task) -> ModelResult:
        """
        Execute a single model call with proper error handling
        """
        start_time = time.time()
        config = MODELS[model_name]
        
        # Mock mode for testing without API calls
        if self.mock_mode:
            return self._mock_call(model_name, task, start_time)
        
        try:
            if config.provider == "openai":
                result = self._call_openai(model_name, config, task, start_time)
            elif config.provider == "anthropic":
                result = self._call_anthropic(model_name, config, task, start_time)
            elif config.provider == "google":
                result = self._call_google(model_name, config, task, start_time)
            elif config.provider == "groq":
                result = self._call_groq(model_name, config, task, start_time)
            else:
                raise ValueError(f"Unknown provider: {config.provider}")
            
            return result
            
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            return ModelResult(
                success=False,
                model=model_name,
                error=str(e),
                latency_ms=latency,
                cost_rupees=0.0
            )
    
    def _call_openai(self, model_name: str, config, task: Task, start_time: float) -> ModelResult:
        """Call OpenAI API (direct or Azure)"""
        # For Azure, use deployment name instead of model name
        if hasattr(self, 'use_azure') and self.use_azure:
            model_identifier = self.azure_deployments.get(model_name, config.model_name)
        else:
            model_identifier = config.model_name
        
        response = self.openai_client.chat.completions.create(
            model=model_identifier,
            messages=[{
                "role": "user",
                "content": f"{task.prompt}\n\n{task.input_text}"
            }],
            max_tokens=min(1000, config.max_tokens),
            temperature=0.7
        )
        
        output = response.choices[0].message.content
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens
        latency = int((time.time() - start_time) * 1000)
        
        cost_usd = (
            tokens_in * config.cost_per_1k_input_usd / 1000 +
            tokens_out * config.cost_per_1k_output_usd / 1000
        )
        cost_rupees = cost_usd * USD_TO_INR
        
        return ModelResult(
            success=True,
            model=model_name,
            output=output,
            latency_ms=latency,
            cost_rupees=cost_rupees,
            tokens_in=tokens_in,
            tokens_out=tokens_out
        )
    
    def _call_anthropic(self, model_name: str, config, task: Task, start_time: float) -> ModelResult:
        """Call Anthropic API"""
        response = self.anthropic_client.messages.create(
            model=config.model_name,
            max_tokens=min(1000, config.max_tokens),
            messages=[{
                "role": "user",
                "content": f"{task.prompt}\n\n{task.input_text}"
            }],
            temperature=0.7
        )
        
        output = response.content[0].text
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        latency = int((time.time() - start_time) * 1000)
        
        cost_usd = (
            tokens_in * config.cost_per_1k_input_usd / 1000 +
            tokens_out * config.cost_per_1k_output_usd / 1000
        )
        cost_rupees = cost_usd * USD_TO_INR
        
        return ModelResult(
            success=True,
            model=model_name,
            output=output,
            latency_ms=latency,
            cost_rupees=cost_rupees,
            tokens_in=tokens_in,
            tokens_out=tokens_out
        )
    
    def _call_google(self, model_name: str, config, task: Task, start_time: float) -> ModelResult:
        """Call Google Gemini API"""
        model = genai.GenerativeModel(config.model_name)
        response = model.generate_content(
            f"{task.prompt}\n\n{task.input_text}",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=min(1000, config.max_tokens),
                temperature=0.7
            )
        )
        
        output = response.text
        latency = int((time.time() - start_time) * 1000)
        
        # Gemini doesn't expose token counts easily, estimate
        tokens_in = len(task.prompt.split()) + len(task.input_text.split())
        tokens_out = len(output.split())
        tokens_in = int(tokens_in * 1.3)  # rough tokenization multiplier
        tokens_out = int(tokens_out * 1.3)
        
        cost_usd = (
            tokens_in * config.cost_per_1k_input_usd / 1000 +
            tokens_out * config.cost_per_1k_output_usd / 1000
        )
        cost_rupees = cost_usd * USD_TO_INR
        
        return ModelResult(
            success=True,
            model=model_name,
            output=output,
            latency_ms=latency,
            cost_rupees=cost_rupees,
            tokens_in=tokens_in,
            tokens_out=tokens_out
        )
    
    def _call_groq(self, model_name: str, config, task: Task, start_time: float) -> ModelResult:
        """Call Groq API (OpenAI-compatible)"""
        if not self.groq_client:
            raise ValueError("Groq API key not configured")
        
        response = self.groq_client.chat.completions.create(
            model=config.model_name,
            messages=[{
                "role": "user",
                "content": f"{task.prompt}\n\n{task.input_text}"
            }],
            max_tokens=min(1000, config.max_tokens),
            temperature=0.7
        )
        
        output = response.choices[0].message.content
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens
        latency = int((time.time() - start_time) * 1000)
        
        # Groq is FREE!
        cost_usd = 0.0
        cost_rupees = 0.0
        
        return ModelResult(
            success=True,
            model=model_name,
            output=output,
            latency_ms=latency,
            cost_rupees=cost_rupees,
            tokens_in=tokens_in,
            tokens_out=tokens_out
        )
    
    def _mock_call(self, model_name: str, task: Task, start_time: float) -> ModelResult:
        """Mock API call for testing"""
        time.sleep(random.uniform(0.1, 0.3))  # Simulate latency
        
        config = MODELS[model_name]
        latency = int((time.time() - start_time) * 1000)
        
        # Simulate token usage
        tokens_in = len(task.prompt.split()) + len(task.input_text.split())
        tokens_out = random.randint(50, 200)
        
        cost_usd = (
            tokens_in * config.cost_per_1k_input_usd / 1000 +
            tokens_out * config.cost_per_1k_output_usd / 1000
        )
        cost_rupees = cost_usd * USD_TO_INR
        
        # Simulate occasional failures for fallback testing
        if random.random() < 0.05:  # 5% failure rate
            return ModelResult(
                success=False,
                model=model_name,
                error="Simulated API timeout",
                latency_ms=latency,
                cost_rupees=0.0
            )
        
        # task.type is already a string when coming from Pydantic
        task_type_str = task.type if isinstance(task.type, str) else task.type.value
        
        return ModelResult(
            success=True,
            model=model_name,
            output=f"[MOCK] Generated output for {task_type_str} using {model_name}",
            latency_ms=latency,
            cost_rupees=cost_rupees,
            tokens_in=tokens_in,
            tokens_out=tokens_out
        )
    
    def execute_with_fallback(
        self,
        task: Task,
        policy: RoutingPolicy
    ) -> ExecutionResult:
        """
        Execute task with intelligent fallback chain and budget enforcement
        """
        primary_model = policy.select_model(task.type)
        fallback_chain = policy.get_fallback_chain(primary_model, task.type)
        
        total_cost = 0.0
        total_latency = 0
        attempts = []
        budget_exceeded = False
        
        # Try primary + fallback chain
        for attempt_num, model in enumerate([primary_model] + fallback_chain):
            # Check budget before attempting
            if total_cost >= task.max_budget_rupees:
                budget_exceeded = True
                break
            
            # Exponential backoff with jitter on retries
            if attempt_num > 0:
                wait_time = min(2 ** attempt_num + random.uniform(0, 1), 10)
                time.sleep(wait_time)
            
            # Execute call
            result = self.call_model(model, task)
            attempts.append(result)
            
            total_cost += result.cost_rupees
            total_latency += result.latency_ms
            
            # Success - return immediately
            if result.success:
                sla = TASK_SLAS[task.type]
                sla_violations = []
                
                if result.latency_ms > sla.max_latency_ms:
                    sla_violations.append(f"Latency: {result.latency_ms}ms > {sla.max_latency_ms}ms")
                if total_cost > sla.max_cost_rupees:
                    sla_violations.append(f"Cost: Rs.{total_cost:.2f} > Rs.{sla.max_cost_rupees}")
                
                # Get task type as string
                task_type_str = task.type if isinstance(task.type, str) else task.type.value
                
                exec_result = ExecutionResult(
                    task_id=task.id,
                    task_type=task_type_str,
                    success=True,
                    primary_model=primary_model,
                    final_model=model,
                    output=result.output,
                    total_latency_ms=total_latency,
                    total_cost_rupees=total_cost,
                    attempts=attempts,
                    fallback_used=(attempt_num > 0),
                    budget_exceeded=False,
                    sla_met=(len(sla_violations) == 0),
                    sla_violations=sla_violations
                )
                
                self.execution_history.append(exec_result)
                return exec_result
        
        # All attempts failed
        task_type_str = task.type if isinstance(task.type, str) else task.type.value
        
        exec_result = ExecutionResult(
            task_id=task.id,
            task_type=task_type_str,
            success=False,
            primary_model=primary_model,
            final_model=None,
            error="All models failed" if not budget_exceeded else "Budget exceeded",
            total_latency_ms=total_latency,
            total_cost_rupees=total_cost,
            attempts=attempts,
            fallback_used=True,
            budget_exceeded=budget_exceeded,
            sla_met=False,
            sla_violations=["Execution failed"]
        )
        
        self.execution_history.append(exec_result)
        return exec_result
    
    def get_metrics_summary(self):
        """Get summary metrics from execution history"""
        if not self.execution_history:
            return {}
        
        total_tasks = len(self.execution_history)
        successful = sum(1 for r in self.execution_history if r.success)
        
        return {
            "total_tasks": total_tasks,
            "successful": successful,
            "failed": total_tasks - successful,
            "success_rate": successful / total_tasks if total_tasks > 0 else 0,
            "avg_cost_rupees": sum(r.total_cost_rupees for r in self.execution_history) / total_tasks,
            "avg_latency_ms": sum(r.total_latency_ms for r in self.execution_history) / total_tasks,
            "fallback_usage": sum(1 for r in self.execution_history if r.fallback_used) / total_tasks,
            "sla_compliance": sum(1 for r in self.execution_history if r.sla_met) / total_tasks,
        }