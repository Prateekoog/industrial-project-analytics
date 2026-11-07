"""Export the Power BI dataset: one workbook with one Excel Table per star-schema table (ASSUMPTIONS J07).

Run: python python/reporting/export_powerbi.py   (after the analysis scripts)

The same workbook uploads to the Power BI service (browser) as a multi-table semantic model and
loads in Power BI Desktop. dim_project is enriched with the analysis snapshot (cost status,
schedule status, risk score and tier) so the dashboard can slice by them without re-deriving the
risk model in DAX. The initiative table feeds the "Potential savings" KPI.
"""
import json
import sys
import warnings
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

TABLES = ["dim_date", "dim_project", "dim_client", "dim_location", "dim_employee", "dim_supplier", "dim_material",
          "dim_work_centre", "dim_equipment", "dim_cost_category", "dim_stage", "fact_budget", "fact_project_cost",
          "fact_procurement", "fact_operations", "fact_equipment", "fact_labor", "fact_milestones", "fact_revenue"]


def main():
    warnings.filterwarnings("ignore", message="In write-only mode")
    data = {n: pd.read_csv(C.DATA_PROCESSED / f"{n}.csv") for n in TABLES}
    kpi = pd.read_csv(C.TABLES / "project_kpis.csv")[["project_id", "cost_variance_pct", "final_margin_pct",
                                                      "estimated_margin_pct", "cost_status", "delay_days", "schedule_status"]]
    risk = pd.read_csv(C.TABLES / "project_risk_scores.csv")[["project_id", "risk_score", "risk_tier"]]
    # Flatten descriptive attributes into the dimensions (star, not snowflake): one filter path per fact
    loc = data["dim_location"].set_index("location_id")
    emp = data["dim_employee"].set_index("employee_id")
    cli = data["dim_client"].set_index("client_id")
    dp = data["dim_project"]
    dp["client_name"] = dp.client_id.map(cli.client_name)
    dp["project_manager"] = dp.project_manager_id.map(emp.employee_name)
    dp["site_city"] = dp.site_location_id.map(loc.city)
    dp["site_state"] = dp.site_location_id.map(loc.state)
    dp["region"] = dp.site_location_id.map(loc.region)
    dp["works_name"] = dp.works_location_id.map(loc.location_name)
    data["dim_project"] = dp.merge(kpi, on="project_id").merge(risk, on="project_id")
    wc = data["dim_work_centre"].set_index("work_centre_id")
    de = data["dim_equipment"]
    de["process_type"] = de.work_centre_id.map(wc.process_type)
    de["works_name"] = de.works_location_id.map(loc.location_name)
    data["dim_location"] = data["dim_location"][data["dim_location"].location_type == "Works"]   # used as the Works dimension
    for unused in ("dim_client", "dim_employee"):                                                 # flattened into dim_project
        data.pop(unused)
    roi = pd.read_csv(C.TABLES / "roi_initiatives.csv")[["initiative", "investment", "annual_saving", "running_cost",
                                                         "net_annual_benefit", "payback_years", "roi_3yr_pct", "npv_5yr"]]
    roi = roi.replace([float("inf")], None)
    data["ref_initiatives"] = roi

    out_dir = C.POWERBI_DIR / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    wb = Workbook(write_only=True)
    for name, df in data.items():
        ws = wb.create_sheet(name[:31])
        ws.append(list(df.columns))
        for row in df.itertuples(index=False):
            ws.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in row])
        tab = Table(displayName=name, ref=f"A1:{get_column_letter(df.shape[1])}{len(df) + 1}")
        tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
        tab._initialise_columns()                    # write-only mode: name the table columns explicitly
        for column, heading in zip(tab.tableColumns, df.columns):
            column.name = str(heading)
        ws.add_table(tab)
        df.to_csv(out_dir / f"{name}.csv", index=False)
    path = C.POWERBI_DIR / "ProjectCo_PowerBI_Dataset.xlsx"
    wb.save(path)

    # Report theme using the same validated palette as the Python charts
    theme = {"name": "ProjectCo Analytics",
             "dataColors": ["#2A78D6", "#EB6834", "#1BAF7A", "#EDA100", "#E87BA4", "#008300", "#6250D6", "#E34948"],
             "background": "#FCFCFB", "foreground": "#0B0B0B", "tableAccent": "#2A78D6",
             "good": "#0CA30C", "neutral": "#FAB219", "bad": "#D03B3B",
             "maximum": "#D03B3B", "center": "#F0EFEC", "minimum": "#2A78D6"}
    (C.POWERBI_DIR / "projectco_theme.json").write_text(json.dumps(theme, indent=2))
    print(f"Wrote {path.relative_to(C.ROOT)} ({len(data)} tables) and powerbi/data/*.csv")


if __name__ == "__main__":
    main()
