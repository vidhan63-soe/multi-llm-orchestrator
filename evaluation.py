"""
Evaluation Harness with automated test cases and scoring
"""
from typing import List, Dict, Callable
import json
from rich.console import Console
from rich.table import Table
from rich.progress import track

from config import TaskType, TASK_SLAS, GRABON_ANNUAL_TASKS, TASK_DISTRIBUTION
from models import Task, ExecutionResult
from orchestrator import Orchestrator
from policies import RoutingPolicy


console = Console()


class EvaluationHarness:
    """
    Automated evaluation system for the orchestrator
    """
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.test_cases = self._create_test_cases()
    
    def _create_test_cases(self) -> List[Task]:
        """Generate comprehensive test cases across all task types"""
        cases = []
        
        # Deal Extraction (8 cases)
        deal_templates = [
            "Flat 40% off on Myntra fashion. Min order Rs. 2000. Code: FASHION40. Valid till Dec 31, 2026.",
            "Get 50% cashback up to Rs. 500 on Zomato orders. Use code FEAST50. Valid for new users only.",
            "Buy 1 Get 1 free on all Puma shoes. No code needed. In-store and online. Limited time offer.",
            "Extra 15% off on Ajio western wear. Stack with existing offers. Code: WEST15. Ends Dec 20.",
            "Upto 70% off + Rs. 200 instant discount on MakeMyTrip hotels. Code: TRAVEL200.",
            "Flat Rs. 300 off on Swiggy orders above Rs. 500. First 3 orders. Code: NEW300.",
            "20% off on all Boat audio products. No minimum order. Code: SOUND20.",
            "Free shipping + 30% off on Nykaa beauty products. Code: BEAUTY30. Valid on app only."
        ]
        
        for i, template in enumerate(deal_templates):
            cases.append(Task(
                type=TaskType.DEAL_EXTRACTION,
                prompt="Extract discount details: percentage/amount, type (flat/cashback/BOGO), minimum order, coupon code, conditions, and expiry.",
                input_text=template
            ))
        
        # Insurance Intent Classification (6 cases)
        insurance_queries = [
            "I just bought a new laptop from Amazon, what if it breaks?",
            "My Swiggy order never arrived and I want a refund",
            "Can I get protection for my iPhone screen damage?",
            "I'm booking a flight to Goa, what if I need to cancel?",
            "Do you have coverage for lost packages during delivery?",
            "Just browsing deals, not interested in insurance right now"
        ]
        
        intent_labels = [
            "electronics_damage",
            "order_refund",
            "device_protection",
            "travel_cancellation",
            "delivery_protection",
            "none"
        ]
        
        for query, label in zip(insurance_queries, intent_labels):
            cases.append(Task(
                type=TaskType.INSURANCE_INTENT,
                prompt=f"Classify user intent: electronics_damage, order_refund, device_protection, travel_cancellation, delivery_protection, or none. Respond with only the category.",
                input_text=query
            ))
        
        # Credit Narrative Generation (6 cases)
        credit_profiles = [
            "GMV: Rs. 45,000/month, 12 transactions, avg order: Rs. 3,750, 92% on-time payments, member since Jan 2025",
            "GMV: Rs. 1,20,000/month, 35 transactions, avg order: Rs. 3,428, 100% on-time, member since Aug 2024",
            "GMV: Rs. 15,000/month, 5 transactions, avg order: Rs. 3,000, 80% on-time, member since Nov 2025",
            "GMV: Rs. 2,50,000/month, 68 transactions, avg order: Rs. 3,676, 98% on-time, premium member since 2023",
            "GMV: Rs. 8,000/month, 3 transactions, avg order: Rs. 2,666, 67% on-time, new member Dec 2025",
            "GMV: Rs. 85,000/month, 22 transactions, avg order: Rs. 3,863, 95% on-time, member since Mar 2024"
        ]
        
        for profile in credit_profiles:
            cases.append(Task(
                type=TaskType.CREDIT_NARRATIVE,
                prompt="Generate a compliance-ready credit assessment narrative for Poonawalla Fincorp. Cite specific data points. Format: Assessment, Key Metrics, Recommendation.",
                input_text=f"User profile: {profile}"
            ))
        
        # Deal Copy Generation (4 cases)
        deal_contexts = [
            "Myntra: 50% off on ethnic wear, Diwali sale, premium brands included",
            "Zomato: Free delivery + 40% off, lunch hours only, top restaurants",
            "MakeMyTrip: Flat Rs. 5000 off on international flights, summer holidays",
            "Nykaa: Buy 2 Get 1 free on skincare, Korean brands, limited stock"
        ]
        
        for context in deal_contexts:
            cases.append(Task(
                type=TaskType.DEAL_COPY_GENERATION,
                prompt="Generate persuasive WhatsApp deal copy (max 160 chars). Include discount, urgency, CTA. Emoji optional.",
                input_text=context
            ))
        
        # Attribution Analysis (3 cases)
        attribution_data = [
            "Click: source=email, timestamp=2026-05-01T10:30, user_id=U123. Purchase: timestamp=2026-05-01T11:15, order_value=Rs.4500, merchant=Myntra",
            "Click: source=push, timestamp=2026-05-02T14:00, user_id=U456. Purchase: timestamp=2026-05-03T09:30, order_value=Rs.1200, merchant=Zomato",
            "Click: source=sms, timestamp=2026-05-03T08:00, user_id=U789. Purchase: timestamp=2026-05-08T18:45, order_value=Rs.8900, merchant=MakeMyTrip"
        ]
        
        for data in attribution_data:
            cases.append(Task(
                type=TaskType.ATTRIBUTION_ANALYSIS,
                prompt="Analyze attribution: Is this a valid conversion? Calculate time-to-convert, channel effectiveness, and confidence score (0-1).",
                input_text=data
            ))
        
        # Hindi Localization (3 cases)
        english_copy = [
            "Get 50% off on all fashion items. Shop now and save big!",
            "Free delivery on your first order. Use code WELCOME.",
            "Limited time offer: Buy 1 Get 1 on all products."
        ]
        
        for copy in english_copy:
            cases.append(Task(
                type=TaskType.HINDI_LOCALIZATION,
                prompt="Translate to Hindi with cultural adaptation. Maintain tone and urgency. Natural, not literal translation.",
                input_text=copy
            ))
        
        return cases
    
    def score_result(self, result: ExecutionResult, task: Task) -> float:
        """
        Score a result (0.0 to 1.0)
        Simple heuristic scoring - in production, use LLM-as-judge or ground truth
        """
        if not result.success or not result.output:
            return 0.0
        
        output = result.output.lower()
        
        # Task-specific scoring logic
        if task.type == TaskType.DEAL_EXTRACTION:
            # Check for key elements
            has_discount = any(char.isdigit() for char in output)
            has_code = 'code' in output or 'coupon' in output
            has_conditions = any(word in output for word in ['min', 'above', 'valid', 'till'])
            score = (has_discount * 0.4 + has_code * 0.3 + has_conditions * 0.3)
            return min(score, 1.0)
        
        elif task.type == TaskType.INSURANCE_INTENT:
            # Check if output mentions valid intent categories
            intents = ['electronics', 'travel', 'device', 'delivery', 'refund', 'none', 'protection']
            mentioned = sum(1 for intent in intents if intent in output)
            return 0.9 if mentioned > 0 else 0.3
        
        elif task.type == TaskType.CREDIT_NARRATIVE:
            # Check for financial terms and structure
            terms = ['gmv', 'transaction', 'payment', 'assessment', 'credit', 'recommendation']
            score = sum(0.15 for term in terms if term in output)
            has_structure = len(output) > 100 and ':' in output
            return min(score + (0.2 if has_structure else 0), 1.0)
        
        elif task.type == TaskType.DEAL_COPY_GENERATION:
            # Check length and key elements
            length_ok = 50 < len(result.output) < 180
            has_discount = any(char.isdigit() for char in output)
            has_urgency = any(word in output for word in ['now', 'limited', 'today', 'hurry'])
            return 0.4 * length_ok + 0.3 * has_discount + 0.3 * has_urgency
        
        elif task.type == TaskType.ATTRIBUTION_ANALYSIS:
            # Check for analysis components
            has_timeframe = 'time' in output or 'hour' in output or 'day' in output
            has_confidence = 'confidence' in output or 'score' in output
            has_verdict = any(word in output for word in ['valid', 'invalid', 'yes', 'no'])
            return 0.3 * has_timeframe + 0.3 * has_confidence + 0.4 * has_verdict
        
        elif task.type == TaskType.HINDI_LOCALIZATION:
            # Check if output contains Hindi characters (Devanagari script)
            has_hindi = any('\u0900' <= char <= '\u097F' for char in result.output)
            reasonable_length = 20 < len(result.output) < 300
            return 0.8 * has_hindi + 0.2 * reasonable_length
        
        # Default scoring
        return 0.7 if len(output) > 20 else 0.3
    
    def run_eval(self, policy: RoutingPolicy, policy_name: str = "Unknown") -> Dict:
        """Run full evaluation suite"""
        console.print(f"\n[bold cyan]Running Evaluation: {policy_name}[/bold cyan]")
        console.print(f"Test cases: {len(self.test_cases)}\n")
        
        results = []
        
        for task in track(self.test_cases, description="Executing tasks..."):
            exec_result = self.orchestrator.execute_with_fallback(task, policy)
            score = self.score_result(exec_result, task)
            
            sla = TASK_SLAS[task.type]
            
            results.append({
                "task_id": exec_result.task_id,
                "task_type": exec_result.task_type,
                "model": exec_result.final_model,
                "score": score,
                "latency_ms": exec_result.total_latency_ms,
                "cost_rupees": exec_result.total_cost_rupees,
                "sla_met": exec_result.sla_met,
                "fallback_used": exec_result.fallback_used,
                "success": exec_result.success
            })
        
        # Calculate summary statistics
        summary = self._generate_summary(results, policy_name)
        
        # Display results
        self._display_results(results, summary)
        
        return {
            "policy": policy_name,
            "summary": summary,
            "results": results
        }
    
    def _generate_summary(self, results: List[Dict], policy_name: str) -> Dict:
        """Generate summary statistics"""
        total = len(results)
        passed = sum(1 for r in results if r['sla_met'])
        successful = sum(1 for r in results if r['success'])
        
        # By task type
        by_task = {}
        for result in results:
            task_type = result['task_type']
            if task_type not in by_task:
                by_task[task_type] = []
            by_task[task_type].append(result)
        
        task_summaries = {}
        for task_type, task_results in by_task.items():
            task_summaries[task_type] = {
                "count": len(task_results),
                "avg_score": sum(r['score'] for r in task_results) / len(task_results),
                "avg_cost": sum(r['cost_rupees'] for r in task_results) / len(task_results),
                "avg_latency": sum(r['latency_ms'] for r in task_results) / len(task_results),
                "sla_compliance": sum(1 for r in task_results if r['sla_met']) / len(task_results),
            }
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": successful / total,
            "sla_compliance_rate": passed / total,
            "avg_score": sum(r['score'] for r in results) / total,
            "avg_cost_rupees": sum(r['cost_rupees'] for r in results) / total,
            "avg_latency_ms": sum(r['latency_ms'] for r in results) / total,
            "fallback_rate": sum(1 for r in results if r['fallback_used']) / total,
            "by_task_type": task_summaries
        }
    
    def _display_results(self, results: List[Dict], summary: Dict):
        """Display results in rich table format"""
        
        # Summary table
        table = Table(title="Evaluation Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Tests", str(summary['total_tests']))
        table.add_row("SLA Compliance", f"{summary['sla_compliance_rate']:.1%}")
        table.add_row("Success Rate", f"{summary['success_rate']:.1%}")
        table.add_row("Avg Score", f"{summary['avg_score']:.2f}")
        table.add_row("Avg Cost", f"Rs. {summary['avg_cost_rupees']:.2f}")
        table.add_row("Avg Latency", f"{summary['avg_latency_ms']:.0f}ms")
        table.add_row("Fallback Rate", f"{summary['fallback_rate']:.1%}")
        
        console.print(table)
        
        # Per-task-type breakdown
        console.print("\n[bold]Performance by Task Type:[/bold]\n")
        
        for task_type, stats in summary['by_task_type'].items():
            console.print(f"[cyan]{task_type}[/cyan]:")
            console.print(f"  Score: {stats['avg_score']:.2f} | Cost: Rs.{stats['avg_cost']:.2f} | "
                         f"Latency: {stats['avg_latency']:.0f}ms | SLA: {stats['sla_compliance']:.1%}")
    
    def calculate_grabon_scale_cost(self, policy_results: Dict) -> Dict:
        """
        Calculate projected costs at GrabOn's 96M tasks/year scale
        """
        summary = policy_results['summary']
        by_task = summary['by_task_type']
        
        annual_costs = {}
        total_annual_cost = 0
        
        for task_type, distribution in TASK_DISTRIBUTION.items():
            task_type_str = task_type.value
            
            if task_type_str in by_task:
                avg_cost_per_task = by_task[task_type_str]['avg_cost']
                annual_tasks = GRABON_ANNUAL_TASKS * distribution
                annual_cost = annual_tasks * avg_cost_per_task
                
                annual_costs[task_type_str] = {
                    "annual_tasks": int(annual_tasks),
                    "cost_per_task": avg_cost_per_task,
                    "annual_cost_rupees": annual_cost
                }
                
                total_annual_cost += annual_cost
        
        return {
            "policy": policy_results['policy'],
            "total_annual_cost_rupees": total_annual_cost,
            "total_annual_cost_usd": total_annual_cost / 83,
            "by_task_type": annual_costs,
            "monthly_cost_rupees": total_annual_cost / 12,
        }
