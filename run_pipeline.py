"""Run the whole project end to end:  python run_pipeline.py

  1. generate synthetic data (raw extracts with data-quality issues)
  2. clean raw -> processed star schema
  3. validate (integrity, reconciliation, cleaning audit)
  4. analysis: EDA, cost & profitability, productivity, procurement, delays, root cause & risk,
     process improvement, ROI
  5. outputs: Excel model, Power BI dataset, dashboard preview, data dictionary

The PostgreSQL database is built separately:  bash database/build_database.sh
"""
import runpy
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    "python/data_generation/generate_data.py",
    "python/cleaning/clean_data.py",
    "python/validation/validate_data.py",
    "python/analysis/eda.py",
    "python/analysis/cost_profitability.py",
    "python/analysis/productivity.py",
    "python/analysis/procurement.py",
    "python/analysis/delays.py",
    "python/analysis/root_cause_risk.py",
    "python/analysis/process_improvement.py",
    "python/analysis/roi_business_case.py",
    "python/reporting/build_excel_model.py",
    "python/reporting/export_powerbi.py",
    "python/visualization/dashboard_preview.py",
    "python/reporting/build_data_dictionary.py",
]

if __name__ == "__main__":
    metrics = ROOT / "reports" / "metrics.json"
    if metrics.exists():
        metrics.unlink()                      # rebuilt from scratch on every run
    for step in STEPS:
        start = time.time()
        print(f"\n=== {step}")
        script = ROOT / step
        sys.path[:0] = [str(script.parent), str(ROOT / "python")]
        runpy.run_path(str(script), run_name="__main__")
        print(f"--- done in {time.time() - start:.1f}s")
    print("\nPipeline complete. Next: bash database/build_database.sh")
