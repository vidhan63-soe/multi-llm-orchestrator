"""
Shadow Testing: Compare two models on the same task
"""
import asyncio
from typing import Dict, List
from collections import defaultdict

from models import Task, ModelResult, ShadowTestResult
from orchestrator import Orchestrator
from config import TaskType


class ShadowTester:
    """
    Runs shadow tests to compare model performance
    """
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.shadow_results: List[ShadowTestResult] = []
    
    def run_shadow_test(
        self,
        task: Task,
        primary_model: str,
        shadow_model: str,
        ground_truth_score_fn
    ) -> ShadowTestResult:
        """
        Execute task on both models and compare results
        """
        # Call both models
        primary_result = self.orchestrator.call_model(primary_model, task)
        shadow_result = self.orchestrator.call_model(shadow_model, task)
        
        # Score outputs (higher is better)
        primary_score = ground_truth_score_fn(primary_result.output) if primary_result.success else 0.0
        shadow_score = ground_truth_score_fn(shadow_result.output) if shadow_result.success else 0.0
        
        # Calculate differences
        accuracy_diff = primary_score - shadow_score
        
        cost_diff_percent = 0.0
        if shadow_result.cost_rupees > 0:
            cost_diff_percent = (
                (primary_result.cost_rupees - shadow_result.cost_rupees) / 
                shadow_result.cost_rupees * 100
            )
        
        latency_diff_ms = primary_result.latency_ms - shadow_result.latency_ms
        
        # Determine winner
        if not primary_result.success:
            winner = shadow_model
        elif not shadow_result.success:
            winner = primary_model
        else:
            # Winner is model with better accuracy, or cheaper if accuracy is similar
            if abs(accuracy_diff) < 0.05:  # Similar accuracy
                winner = primary_model if primary_result.cost_rupees < shadow_result.cost_rupees else shadow_model
            else:
                winner = primary_model if primary_score > shadow_score else shadow_model
        
        # Generate recommendation
        recommendation = None
        if winner == shadow_model and shadow_result.cost_rupees < primary_result.cost_rupees:
            savings = (1 - shadow_result.cost_rupees / primary_result.cost_rupees) * 100
            recommendation = (
                f"Switch to {shadow_model}: {abs(accuracy_diff)*100:.1f}% accuracy difference "
                f"with {savings:.1f}% cost savings"
            )
        
        result = ShadowTestResult(
            task_id=task.id,
            task_type=task.type.value,
            primary_result=primary_result,
            shadow_result=shadow_result,
            accuracy_diff=accuracy_diff,
            cost_diff_percent=cost_diff_percent,
            latency_diff_ms=latency_diff_ms,
            winner=winner,
            recommendation=recommendation
        )
        
        self.shadow_results.append(result)
        return result
    
    def analyze_shadow_tests(self, min_samples: int = 10) -> Dict[str, any]:
        """
        Analyze accumulated shadow test results and generate routing recommendations
        """
        if len(self.shadow_results) < min_samples:
            return {
                "status": "insufficient_data",
                "samples": len(self.shadow_results),
                "required": min_samples
            }
        
        # Group by task type
        by_task_type = defaultdict(list)
        for result in self.shadow_results:
            by_task_type[result.task_type].append(result)
        
        recommendations = []
        
        for task_type, results in by_task_type.items():
            if len(results) < min_samples:
                continue
            
            # Aggregate statistics
            avg_accuracy_diff = sum(r.accuracy_diff for r in results) / len(results)
            avg_cost_diff = sum(r.cost_diff_percent for r in results) / len(results)
            avg_latency_diff = sum(r.latency_diff_ms for r in results) / len(results)
            
            # Count winners
            primary_wins = sum(1 for r in results if r.winner == r.primary_result.model)
            shadow_wins = len(results) - primary_wins
            
            # Get model names
            primary_model = results[0].primary_result.model
            shadow_model = results[0].shadow_result.model
            
            # Generate recommendation if shadow is clearly better
            if shadow_wins > primary_wins * 1.2 and avg_cost_diff > 10:
                recommendations.append({
                    "task_type": task_type,
                    "current_model": primary_model,
                    "recommended_model": shadow_model,
                    "reason": f"Shadow model wins {shadow_wins}/{len(results)} times with {abs(avg_cost_diff):.1f}% cost savings",
                    "accuracy_impact": f"{avg_accuracy_diff*100:+.1f}%",
                    "cost_savings": f"{abs(avg_cost_diff):.1f}%",
                    "latency_impact": f"{avg_latency_diff:+d}ms"
                })
        
        return {
            "status": "analysis_complete",
            "total_samples": len(self.shadow_results),
            "task_types_analyzed": len(by_task_type),
            "recommendations": recommendations
        }
