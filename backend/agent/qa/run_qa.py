"""
Entry point for QA runner.
Run: python -m backend.agent.qa.run_qa
"""
import asyncio
import json
import os
import sys
from pathlib import Path

async def main():
    print("=" * 60)
    print("ARCHIMEDES QA — Full System Review")
    print("=" * 60)
    print()
    
    # Set testing mode
    os.environ["TESTING"] = "1"
    
    from backend.agent.qa.qa_runner import ArchimedesQARunner
    
    runner = ArchimedesQARunner(timeout_per_test=45.0)
    
    print("Running tests... (this takes 2-5 minutes)")
    print()
    
    report = await runner.run_all()
    
    # Print summary
    print(report.to_markdown())
    
    # Save reports
    output_dir = Path("data/qa_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import time
    timestamp = int(time.time())
    
    json_path = output_dir / f"qa_report_{timestamp}.json"
    md_path = output_dir / f"qa_report_{timestamp}.md"
    latest_path = output_dir / "latest.json"
    
    json_path.write_text(json.dumps(report.to_dict(), indent=2))
    md_path.write_text(report.to_markdown())
    latest_path.write_text(json.dumps(report.to_dict(), indent=2))
    
    print(f"\nReports saved:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    print(f"  Latest: {latest_path}")
    
    # Exit with error if grade is F
    if report.overall_grade.value == "F":
        print("\n🔴 CRITICAL: Overall grade F — agent needs immediate attention")
        sys.exit(1)
    
    print(f"\n{'✅' if report.overall_grade.value in ('A','B') else '⚠️'} Overall: {report.overall_grade.value} ({report.overall_score*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
