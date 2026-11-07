"""Turn the clean simulated tables into messy source-system extracts (I01, I02).

Real ERP, MES and timesheet exports are never clean. Each function below copies one
"true" table, damages a small, controlled share of rows in a realistic way, and logs
every change to data/qa/injected_issues_log.csv. The cleaning pipeline never reads
that log; validation uses it afterwards to measure how much the cleaning recovered.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

LOG = []


def _log(table, record_id, column, issue, original, injected):
    LOG.append(dict(table=table, record_id=record_id, column=column, issue_type=issue,
                    original_value=original, injected_value=injected))


def _pick(rng, df, share, mask=None):
    pool = df.index if mask is None else df.index[mask]
    n = int(round(len(pool) * share))
    return rng.choice(pool, size=n, replace=False) if n else []


def _fmt_date(rng, value):
    """Mostly ISO dates, with the occasional DD/MM/YYYY or DD-Mon-YYYY from a different export."""
    if value is None or pd.isna(value):
        return ""
    d = pd.Timestamp(value)
    r = rng.random()
    if r < 0.04:
        return d.strftime("%d/%m/%Y")
    if r < 0.05:
        return d.strftime("%d-%b-%Y")
    return d.strftime("%Y-%m-%d")


def _supplier_variant(rng, name):
    variants = [
        name.upper(), name.lower(), f"  {name} ", name.replace("Pvt Ltd", "Private Limited"),
        name.replace("Pvt Ltd", "Pvt. Ltd."), name.replace("Ltd", "Limited"), name.replace("&", "and"),
        name.replace(" ", "  ", 1), name[:-1] if name.endswith("d") else name + ".",
    ]
    variants = [v for v in variants if v != name]
    return variants[int(rng.integers(0, len(variants)))]


def corrupt_purchase_orders(rng, po, suppliers):
    t = "purchase_orders"
    df = po.copy()
    names = dict(zip(suppliers.supplier_id, suppliers.supplier_name))
    df.insert(df.columns.get_loc("supplier_id"), "supplier_name", df.supplier_id.map(names))
    df = df.drop(columns="supplier_id")

    for i in _pick(rng, df, 0.12):
        new = _supplier_variant(rng, df.at[i, "supplier_name"])
        _log(t, df.at[i, "po_line_id"], "supplier_name", "inconsistent_name", df.at[i, "supplier_name"], new)
        df.at[i, "supplier_name"] = new
    received = df.grn_date.notna()
    for i in _pick(rng, df, 0.015, received):
        _log(t, df.at[i, "po_line_id"], "delivery_date", "missing_value", str(df.at[i, "delivery_date"]), "")
        df.at[i, "delivery_date"] = None
    swappable = df.delivery_date.notna() & df.delivery_date.map(lambda d: hasattr(d, "day") and d.day <= 12 and d.day != d.month)
    for i in _pick(rng, df, 0.006, swappable):
        d = df.at[i, "delivery_date"]
        new = d.replace(month=d.day, day=d.month)
        _log(t, df.at[i, "po_line_id"], "delivery_date", "day_month_swapped", str(d), str(new))
        df.at[i, "delivery_date"] = new
    for i in _pick(rng, df, 0.01):
        _log(t, df.at[i, "po_line_id"], "unit_price_inr", "missing_value", df.at[i, "unit_price_inr"], "")
        df.at[i, "unit_price_inr"] = np.nan
    for i in _pick(rng, df, 0.008, df.unit_price_inr.notna()):
        new = round(df.at[i, "unit_price_inr"] * 10, 2)
        _log(t, df.at[i, "po_line_id"], "unit_price_inr", "outlier_extra_zero", df.at[i, "unit_price_inr"], new)
        df.at[i, "unit_price_inr"] = new
    for i in _pick(rng, df, 0.004, df.unit_price_inr.notna()):
        _log(t, df.at[i, "po_line_id"], "unit_price_inr", "zero_value", df.at[i, "unit_price_inr"], 0)
        df.at[i, "unit_price_inr"] = 0.0
    for i in _pick(rng, df, 0.005):
        _log(t, df.at[i, "po_line_id"], "quantity", "negative_value", df.at[i, "quantity"], -df.at[i, "quantity"])
        df.at[i, "quantity"] = -df.at[i, "quantity"]

    date_cols = [c for c in df.columns if c.endswith("_date")]
    for c in date_cols:
        df[c] = [_fmt_date(rng, v) for v in df[c]]
    dupes = df.loc[_pick(rng, df, 0.015)]
    for pid in dupes.po_line_id:
        _log(t, pid, "*", "duplicate_row", "", "")
    df = pd.concat([df, dupes]).sort_values("po_line_id", kind="stable").reset_index(drop=True)
    return df


def corrupt_cost_ledger(rng, cost, categories):
    t = "cost_ledger"
    df = cost.copy()
    names = dict(zip(categories.cost_category_id, categories.cost_category))
    df.insert(df.columns.get_loc("cost_category_id"), "cost_category", df.cost_category_id.map(names))
    df = df.drop(columns="cost_category_id")
    typos = {"Material": ["Matrial", "MATERIAL", "material ", "Materials", "MAT-01"],
             "Labour": ["Labor", "LABOUR", "Labour Cost", "Manpower"],
             "Subcontractor": ["Sub-contractor", "Subcon", "Sub Contractor", "SUBCONTRACT"],
             "Equipment": ["Equip.", "Equipment Hire", "Machinery"],
             "Transportation": ["Transport", "Freight", "Logistics"],
             "Energy": ["Power & Fuel", "Electricity", "ENERGY"],
             "Overhead": ["Overheads", "O/H", "Site Overhead"],
             "Other": ["Misc", "Others", "Other Costs"]}
    for i in _pick(rng, df, 0.05):
        opts = typos[df.at[i, "cost_category"]]
        new = opts[int(rng.integers(0, len(opts)))]
        _log(t, df.at[i, "document_no"], "cost_category", "incorrect_category", df.at[i, "cost_category"], new)
        df.at[i, "cost_category"] = new
    for i in _pick(rng, df, 0.015):
        _log(t, df.at[i, "document_no"], "cost_category", "missing_value", df.at[i, "cost_category"], "")
        df.at[i, "cost_category"] = None
    zero = df.loc[_pick(rng, df, 0.005)].copy()
    zero["amount_inr"] = 0.0
    zero["document_no"] = [f"JV-Z{k:06d}" for k in range(len(zero))]
    for doc in zero.document_no:
        _log(t, doc, "amount_inr", "zero_value", "", 0)
    dupes = df.loc[_pick(rng, df, 0.01)]
    for doc in dupes.document_no:
        _log(t, doc, "*", "duplicate_row", "", "")
    return pd.concat([df, zero, dupes]).sort_values(["posting_date", "document_no"], kind="stable").reset_index(drop=True)


def corrupt_production_log(rng, ops):
    t = "production_log"
    df = ops.copy()
    df.insert(0, "production_id", [f"OPS-{k:06d}" for k in range(1, len(df) + 1)])
    for i in _pick(rng, df, 0.015):
        _log(t, df.at[i, "production_id"], "regular_labour_hours", "missing_value", df.at[i, "regular_labour_hours"], "")
        df.at[i, "regular_labour_hours"] = np.nan
    for i in _pick(rng, df, 0.004, df.actual_output_t > 1):
        new = round(df.at[i, "actual_output_t"] * 10, 3)
        _log(t, df.at[i, "production_id"], "actual_output_t", "outlier_extra_zero", df.at[i, "actual_output_t"], new)
        df.at[i, "actual_output_t"] = new
    for i in _pick(rng, df, 0.003, df.rework_t > 0):
        _log(t, df.at[i, "production_id"], "rework_t", "negative_value", df.at[i, "rework_t"], -df.at[i, "rework_t"])
        df.at[i, "rework_t"] = -df.at[i, "rework_t"]
    return df


def corrupt_machine_log(rng, eq):
    t = "machine_log"
    df = eq.copy()
    df.insert(0, "machine_log_id", [f"ML-{k:06d}" for k in range(1, len(df) + 1)])
    down = df.downtime_hours > 0
    for i in _pick(rng, df, 0.004 / max(down.mean(), 1e-9), down):
        new = round(df.at[i, "downtime_hours"] * 10, 2)
        _log(t, df.at[i, "machine_log_id"], "downtime_hours", "outlier_extra_zero", df.at[i, "downtime_hours"], new)
        df.at[i, "downtime_hours"] = new
    for i in _pick(rng, df, 0.02, down & (df.downtime_hours < 50)):
        _log(t, df.at[i, "machine_log_id"], "downtime_hours", "negative_value", df.at[i, "downtime_hours"],
             -df.at[i, "downtime_hours"])
        df.at[i, "downtime_hours"] = -df.at[i, "downtime_hours"]
    for i in _pick(rng, df, 0.03, df.downtime_reason.notna()):
        _log(t, df.at[i, "machine_log_id"], "downtime_reason", "missing_value", df.at[i, "downtime_reason"], "")
        df.at[i, "downtime_reason"] = None
    dupes = df.loc[_pick(rng, df, 0.005)]
    for k in dupes.machine_log_id:
        _log(t, k, "*", "duplicate_row", "", "")
    return pd.concat([df, dupes]).sort_values("machine_log_id", kind="stable").reset_index(drop=True)


def corrupt_timesheets(rng, lab):
    t = "site_timesheets"
    df = lab.copy()
    for i in _pick(rng, df, 0.01, df.overtime_hours > 0):
        _log(t, df.at[i, "labour_entry_id"], "overtime_hours", "missing_value", df.at[i, "overtime_hours"], "")
        df.at[i, "overtime_hours"] = np.nan
    for i in _pick(rng, df, 0.004):
        _log(t, df.at[i, "labour_entry_id"], "headcount", "zero_value", df.at[i, "headcount"], 0)
        df.at[i, "headcount"] = 0
    return df


def corrupt_projects(rng, projects):
    t = "projects_master"
    df = projects.copy()
    variants = {"Cement": ["cement", "Cement "], "Mining & Material Handling": ["Mining & MH", "Mining and Material Handling"],
                "Wastewater Treatment": ["Waste Water Treatment", "WWT"], "Green Hydrogen": ["Green H2"],
                "Carbon Capture": ["CCUS"], "Thermal Energy": ["Thermal", "thermal energy"],
                "Industrial Equipment": ["Industrial Equip."], "Sugar": ["SUGAR"], "Biochemicals": ["Bio-chemicals"],
                "Industrial Batteries": ["Batteries"]}
    for i in _pick(rng, df, 0.12):
        opts = variants[df.at[i, "industry"]]
        new = opts[int(rng.integers(0, len(opts)))]
        _log(t, df.at[i, "project_id"], "industry", "incorrect_category", df.at[i, "industry"], new)
        df.at[i, "industry"] = new
    yes, no = ["Y", "Yes", "1", "TRUE"], ["N", "No", "0", "FALSE"]
    df["has_price_variation_clause"] = [(yes if v else no)[int(rng.integers(0, 4))] for v in df.has_price_variation_clause]
    return df


def corrupt_milestones(rng, ms):
    t = "milestones"
    df = ms.copy()
    both = df.actual_start_date.notna() & df.actual_end_date.notna() & (df.actual_start_date != df.actual_end_date)
    for i in _pick(rng, df, 0.012, both):
        a, b = df.at[i, "actual_start_date"], df.at[i, "actual_end_date"]
        _log(t, f"{df.at[i, 'project_id']}|{df.at[i, 'stage_id']}", "actual_start_date|actual_end_date",
             "dates_swapped", f"{a}|{b}", f"{b}|{a}")
        df.at[i, "actual_start_date"], df.at[i, "actual_end_date"] = b, a
    return df


def corrupt_billing(rng, rev):
    t = "billing"
    df = rev.copy()
    variants = {"Milestone Billing": ["Milestone", "Milestone Invoice"], "Change Order": ["CO", "Variation"],
                "Price Variation": ["PVC", "Price Escalation"], "Liquidated Damages": ["LD", "Penalty - LD"]}
    for i in _pick(rng, df, 0.08):
        opts = variants[df.at[i, "revenue_type"]]
        new = opts[int(rng.integers(0, len(opts)))]
        _log(t, df.at[i, "invoice_no"], "revenue_type", "incorrect_category", df.at[i, "revenue_type"], new)
        df.at[i, "revenue_type"] = new
    dupes = df.loc[_pick(rng, df, 0.01)]
    for k in dupes.invoice_no:
        _log(t, k, "*", "duplicate_row", "", "")
    return pd.concat([df, dupes]).sort_values("invoice_no", kind="stable").reset_index(drop=True)


def write_raw_extracts(truth, rng):
    LOG.clear()
    C.DATA_RAW.mkdir(parents=True, exist_ok=True)
    cats = truth["dim_cost_category"]
    budgets = truth["fact_budget"].merge(cats[["cost_category_id", "cost_category"]], on="cost_category_id")
    raw = {
        "projects_master": corrupt_projects(rng, truth["dim_project"]),
        "clients_master": truth["dim_client"],
        "vendor_master": truth["dim_supplier"],
        "material_master": truth["dim_material"],
        "employee_master": truth["dim_employee"],
        "location_master": truth["dim_location"],
        "work_centre_master": truth["dim_work_centre"],
        "equipment_register": truth["dim_equipment"],
        "project_budgets": budgets.drop(columns="cost_category_id")[
            ["project_id", "cost_category", "original_budget_inr", "change_order_budget_inr", "revised_budget_inr"]],
        "cost_ledger": corrupt_cost_ledger(rng, truth["fact_project_cost"], cats),
        "purchase_orders": corrupt_purchase_orders(rng, truth["fact_procurement"], truth["dim_supplier"]),
        "production_log": corrupt_production_log(rng, truth["fact_operations"]),
        "machine_log": corrupt_machine_log(rng, truth["fact_equipment"]),
        "site_timesheets": corrupt_timesheets(rng, truth["fact_labor"]),
        "milestones": corrupt_milestones(rng, truth["fact_milestones"]),
        "billing": corrupt_billing(rng, truth["fact_revenue"]),
        "steel_price_index": truth["ref_steel_price_index"],
    }
    for name, df in raw.items():
        df.to_csv(C.DATA_RAW / f"{name}.csv", index=False)
    log = pd.DataFrame(LOG)
    log.to_csv(C.DATA_QA / "injected_issues_log.csv", index=False)
    print(f"Wrote {len(raw)} raw extracts to data/raw/ and {len(log):,} injected issues to data/qa/")
    print(log.groupby(["table", "issue_type"]).size().to_string())
