"""
Main entry point for the Orchestrator Agent
"""
import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from orchestrator import Orchestrator
from policies import POLICIES
from evaluation import EvaluationHarness
from shadow_testing import ShadowTester
from config import TaskType
from models import Task


console = Console()


def setup():
    """Load environment and check API keys"""
    load_dotenv()
    
    # Check for API keys
    keys_present = {
        "OpenAI": bool(os.getenv("OPENAI_API_KEY")),
        "Anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "Google": bool(os.getenv("GOOGLE_API_KEY")),
    }
    
    console.print("\n[bold cyan]API Key Status:[/bold cyan]")
    for provider, present in keys_present.items():
        status = "[green]✓[/green]" if present else "[red]✗[/red]"
        console.print(f"  {status} {provider}")
    
    if not all(keys_present.values()):
        console.print("\n[yellow]Warning: Some API keys missing. Set MOCK_MODE=true to test without API calls.[/yellow]")
    
    return keys_present


def run_evaluation(policy_name: str, save_results: bool = True):
    """Run evaluation with specified policy"""
    
    # Initialize
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    orchestrator = Orchestrator(mock_mode=mock_mode)
    evaluator = EvaluationHarness(orchestrator)
    
    # Get policy
    if policy_name not in POLICIES:
        console.print(f"[red]Error: Policy '{policy_name}' not found.[/red]")
        console.print(f"Available policies: {', '.join(POLICIES.keys())}")
        return
    
    policy = POLICIES[policy_name]
    
    # Run evaluation
    results = evaluator.run_eval(policy, policy_name=policy_name)
    
    # Calculate GrabOn scale costs
    scale_projection = evaluator.calculate_grabon_scale_cost(results)
    
    console.print(f"\n[bold green]GrabOn Scale Cost Projection (96M tasks/year):[/bold green]")
    console.print(f"  Total Annual Cost: [cyan]Rs. {scale_projection['total_annual_cost_rupees']:,.0f}[/cyan]")
    console.print(f"  Total Annual Cost: [cyan]${scale_projection['total_annual_cost_usd']:,.0f}[/cyan]")
    console.print(f"  Monthly Cost: [cyan]Rs. {scale_projection['monthly_cost_rupees']:,.0f}[/cyan]")
    
    # Save results
    if save_results:
        output_dir = Path("results")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"eval_{policy_name}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "evaluation": results,
                "scale_projection": scale_projection
            }, f, indent=2, default=str)
        
        console.print(f"\n[green]Results saved to {output_file}[/green]")
    
    return results, scale_projection


def compare_policies():
    """Compare all policies and generate recommendations"""
    
    console.print("\n[bold cyan]Comparing All Routing Policies[/bold cyan]\n")
    
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    orchestrator = Orchestrator(mock_mode=mock_mode)
    evaluator = EvaluationHarness(orchestrator)
    
    all_results = {}
    all_projections = {}
    
    for policy_name in POLICIES.keys():
        console.print(f"\n{'='*60}")
        policy = POLICIES[policy_name]
        results = evaluator.run_eval(policy, policy_name=policy_name)
        projection = evaluator.calculate_grabon_scale_cost(results)
        
        all_results[policy_name] = results
        all_projections[policy_name] = projection
    
    # Comparison table
    console.print(f"\n{'='*60}")
    console.print("[bold cyan]Policy Comparison Summary[/bold cyan]\n")
    
    table = Table(show_header=True)
    table.add_column("Policy", style="cyan")
    table.add_column("SLA Compliance", justify="right")
    table.add_column("Avg Score", justify="right")
    table.add_column("Avg Cost", justify="right")
    table.add_column("Annual Cost (Rs.)", justify="right")
    table.add_column("Annual Cost (USD)", justify="right")
    
    for policy_name in POLICIES.keys():
        summary = all_results[policy_name]['summary']
        projection = all_projections[policy_name]
        
        table.add_row(
            policy_name,
            f"{summary['sla_compliance_rate']:.1%}",
            f"{summary['avg_score']:.2f}",
            f"Rs.{summary['avg_cost_rupees']:.2f}",
            f"{projection['total_annual_cost_rupees']:,.0f}",
            f"${projection['total_annual_cost_usd']:,.0f}"
        )
    
    console.print(table)
    
    # Save comparison
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "policy_comparison.json", 'w') as f:
        json.dump({
            "results": all_results,
            "projections": all_projections
        }, f, indent=2, default=str)
    
    console.print(f"\n[green]Comparison saved to results/policy_comparison.json[/green]")
    
    # Recommendation
    console.print("\n[bold yellow]Recommendation:[/bold yellow]")
    
    # Find best balance
    best_cost = min(all_projections.values(), key=lambda x: x['total_annual_cost_rupees'])
    best_quality = max(all_results.values(), key=lambda x: x['summary']['avg_score'])
    best_sla = max(all_results.values(), key=lambda x: x['summary']['sla_compliance_rate'])
    
    console.print(f"  • Lowest Cost: [green]{best_cost['policy']}[/green] (Rs. {best_cost['total_annual_cost_rupees']:,.0f}/year)")
    console.print(f"  • Highest Quality: [green]{best_quality['policy']}[/green] (score: {best_quality['summary']['avg_score']:.2f})")
    console.print(f"  • Best SLA Compliance: [green]{best_sla['policy']}[/green] ({best_sla['summary']['sla_compliance_rate']:.1%})")


def run_shadow_test():
    """Run shadow testing to compare models"""
    
    console.print("\n[bold cyan]Running Shadow Tests[/bold cyan]\n")
    
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    orchestrator = Orchestrator(mock_mode=mock_mode)
    evaluator = EvaluationHarness(orchestrator)
    shadow_tester = ShadowTester(orchestrator)
    
    # Run 20 shadow tests
    test_cases = evaluator.test_cases[:20]
    
    for i, task in enumerate(test_cases, 1):
        console.print(f"[cyan]Shadow Test {i}/20:[/cyan] {task.type.value}")
        
        # Compare primary vs shadow models based on task type
        if task.type == TaskType.DEAL_EXTRACTION:
            primary = "gpt-4o-mini"
            shadow = "gemini-flash"
        elif task.type == TaskType.INSURANCE_INTENT:
            primary = "gemini-flash"
            shadow = "claude-haiku"
        elif task.type == TaskType.CREDIT_NARRATIVE:
            primary = "claude-sonnet-4"
            shadow = "gpt-4o"
        else:
            primary = "gpt-4o-mini"
            shadow = "gemini-flash"
        
        # Simple scoring function
        def score_fn(output):
            if not output:
                return 0.0
            return min(len(output) / 200, 1.0)  # Simple length-based score
        
        result = shadow_tester.run_shadow_test(task, primary, shadow, score_fn)
        
        console.print(f"  Winner: [green]{result.winner}[/green]")
        console.print(f"  Cost diff: {result.cost_diff_percent:+.1f}%")
        if result.recommendation:
            console.print(f"  💡 {result.recommendation}")
        console.print()
    
    # Analyze results
    analysis = shadow_tester.analyze_shadow_tests(min_samples=5)
    
    console.print("\n[bold green]Shadow Test Analysis:[/bold green]\n")
    console.print(f"Status: {analysis['status']}")
    console.print(f"Total Samples: {analysis.get('total_samples', 0)}")
    
    if analysis['status'] == 'analysis_complete':
        console.print(f"\n[bold]Routing Recommendations:[/bold]")
        
        if analysis['recommendations']:
            for rec in analysis['recommendations']:
                console.print(f"\n• [cyan]{rec['task_type']}[/cyan]:")
                console.print(f"  Current: {rec['current_model']}")
                console.print(f"  Recommended: [green]{rec['recommended_model']}[/green]")
                console.print(f"  Reason: {rec['reason']}")
                console.print(f"  Impact: {rec['accuracy_impact']} accuracy, {rec['cost_savings']} cost savings")
        else:
            console.print("  No changes recommended. Current routing is optimal.")
    
    # Save results
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "shadow_tests.json", 'w') as f:
        json.dump({
            "results": [r.dict() for r in shadow_tester.shadow_results],
            "analysis": analysis
        }, f, indent=2, default=str)
    
    console.print(f"\n[green]Shadow test results saved to results/shadow_tests.json[/green]")


def interactive_demo():
    """Interactive demo mode"""
    
    console.print("\n[bold cyan]Interactive Orchestrator Demo[/bold cyan]\n")
    
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    orchestrator = Orchestrator(mock_mode=mock_mode)
    
    # Choose policy
    console.print("Available policies:")
    for i, policy_name in enumerate(POLICIES.keys(), 1):
        console.print(f"  {i}. {policy_name}")
    
    choice = input("\nSelect policy (1-4): ")
    policy_name = list(POLICIES.keys())[int(choice) - 1]
    policy = POLICIES[policy_name]
    
    console.print(f"\nUsing [green]{policy_name}[/green] policy\n")
    
    # Choose task type
    console.print("Task types:")
    task_types = list(TaskType)
    for i, task_type in enumerate(task_types, 1):
        console.print(f"  {i}. {task_type.value}")
    
    choice = input("\nSelect task type (1-6): ")
    task_type = task_types[int(choice) - 1]
    
    # Get input
    console.print(f"\n[cyan]Enter your input for {task_type.value}:[/cyan]")
    user_input = input("> ")
    
    # Create task
    prompts = {
        TaskType.DEAL_EXTRACTION: "Extract discount details from this deal:",
        TaskType.INSURANCE_INTENT: "Classify insurance intent:",
        TaskType.CREDIT_NARRATIVE: "Generate credit assessment:",
        TaskType.DEAL_COPY_GENERATION: "Generate deal copy:",
        TaskType.ATTRIBUTION_ANALYSIS: "Analyze attribution:",
        TaskType.HINDI_LOCALIZATION: "Translate to Hindi:"
    }
    
    task = Task(
        type=task_type,
        prompt=prompts[task_type],
        input_text=user_input
    )
    
    # Execute
    console.print("\n[yellow]Processing...[/yellow]\n")
    result = orchestrator.execute_with_fallback(task, policy)
    
    # Display result
    console.print(f"[bold]Result:[/bold]")
    console.print(f"  Model: [cyan]{result.final_model}[/cyan]")
    console.print(f"  Success: [green]{result.success}[/green]")
    console.print(f"  Latency: {result.total_latency_ms}ms")
    console.print(f"  Cost: Rs.{result.total_cost_rupees:.2f}")
    console.print(f"  SLA Met: {'✓' if result.sla_met else '✗'}")
    
    if result.output:
        console.print(f"\n[bold]Output:[/bold]")
        console.print(result.output)


def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="GrabOn Orchestrator - Multi-LLM Task Router"
    )
    
    parser.add_argument(
        "command",
        choices=["eval", "compare", "shadow", "demo"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--policy",
        choices=list(POLICIES.keys()),
        default="balanced",
        help="Routing policy to use (for eval command)"
    )
    
    args = parser.parse_args()
    
    # Setup
    setup()
    
    # Route command
    if args.command == "eval":
        run_evaluation(args.policy)
    elif args.command == "compare":
        compare_policies()
    elif args.command == "shadow":
        run_shadow_test()
    elif args.command == "demo":
        interactive_demo()


if __name__ == "__main__":
    main()
