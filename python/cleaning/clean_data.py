"""Clean the raw source extracts into an analysis-ready star schema.

Run from the project root:
    python python/cleaning/clean_data.py

RAW (data/raw) -> QUALITY CHECKS -> CLEANING -> DERIVED COLUMNS -> PROCESSED (data/processed)

Every rule is written to data/qa/cleaning_log.csv with the number of rows it changed,
and is explained in docs/DATA_QUALITY.md. Rules use only the data itself (never the
injected-issue answer key), exactly as they would on a real ERP export.
"""
import difflib
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from data_generation import reference_data as R  # noqa: E402

LOG = []


def log(table, rule, action, rows):
    LOG.append(dict(table=table, rule=rule, action=action, rows_affected=int(rows)))
    print(f"  [{table}] {rule}: {action} -> {int(rows):,} rows")


def read(name, **kw):
    return pd.read_csv(C.DATA_RAW / f"{name}.csv", **kw)


def to_date(series):
    return pd.to_datetime(series, format="%Y-%m-%d", errors="coerce").dt.date


def parse_mixed_dates(series, table, column):
    """Parse a column that mixes ISO, DD/MM/YYYY and DD-Mon-YYYY formats, logging each format found."""
    s = series.fillna("").astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index)
    for fmt, label in (("%Y-%m-%d", "ISO"), ("%d/%m/%Y", "DD/MM/YYYY"), ("%d-%b-%Y", "DD-Mon-YYYY")):
        todo = out.isna() & (s != "")
        parsed = pd.to_datetime(s[todo], format=fmt, errors="coerce")
        out.loc[parsed.index] = parsed
        if label != "ISO" and parsed.notna().sum():
            log(table, f"date format {label} in {column}", "parsed to ISO date", parsed.notna().sum())
    return pd.to_datetime(out).dt.date


def normalise_name(name):
    n = str(name).lower().strip()
    n = n.replace("&", " and ").replace("private limited", "pvt ltd").replace("limited", "ltd")
    n = re.sub(r"[.,]", "", n)
    return re.sub(r"\s+", " ", n).strip()


# --------------------------------------------------------------------------------------
# Dimensions
# --------------------------------------------------------------------------------------
def clean_dimensions():
    dims = {
        "dim_location": read("location_master"),
        "dim_client": read("clients_master"),
        "dim_employee": read("employee_master"),
        "dim_supplier": read("vendor_master"),
        "dim_material": read("material_master"),
        "dim_work_centre": read("work_centre_master"),
        "dim_equipment": read("equipment_register"),
    }
    for df in dims.values():
        for c in df.select_dtypes("object"):
            df[c] = df[c].str.strip()
    dims["dim_cost_category"] = pd.DataFrame(
        [(c[0], c[1], i + 1, c[3], c[4]) for i, c in enumerate(R.COST_CATEGORIES)],
        columns=["cost_category_id", "cost_category", "sort_order", "cost_behaviour", "gl_account"])
    dims["dim_stage"] = pd.DataFrame([(s[0], s[1], s[0], s[4], s[5]) for s in R.STAGES],
                                     columns=["stage_id", "stage_name", "stage_order", "billing_share", "description"])
    return dims


def clean_projects():
    t = "projects_master"
    df = read(t)
    canonical = {k.lower(): k for k in R.INDUSTRIES}
    synonyms = {"mining & mh": "Mining & Material Handling", "mining and material handling": "Mining & Material Handling",
                "waste water treatment": "Wastewater Treatment", "wwt": "Wastewater Treatment",
                "green h2": "Green Hydrogen", "ccus": "Carbon Capture", "thermal": "Thermal Energy",
                "industrial equip.": "Industrial Equipment", "bio-chemicals": "Biochemicals",
                "batteries": "Industrial Batteries"}
    key = df.industry.str.strip().str.lower()
    fixed = key.map(canonical).fillna(key.map(synonyms))
    log(t, "inconsistent industry labels", "mapped to 10 canonical industries", (fixed != df.industry).sum())
    assert fixed.notna().all(), "unmapped industry label"
    df["industry"] = fixed
    flag = df.has_price_variation_clause.astype(str).str.strip().str.upper()
    df["has_price_variation_clause"] = flag.isin(["Y", "YES", "1", "TRUE"])
    log(t, "mixed Y/Yes/1/TRUE flags", "converted to boolean", (~flag.isin(["TRUE", "FALSE"])).sum())
    for c in ("award_date", "planned_start_date", "planned_end_date", "actual_start_date", "actual_end_date"):
        df[c] = to_date(df[c])
    df["planned_duration_days"] = [(e - s).days for s, e in zip(df.planned_start_date, df.planned_end_date)]
    return df


def clean_budgets(cats):
    df = read("project_budgets")
    df["cost_category_id"] = df.cost_category.map(dict(zip(cats.cost_category, cats.cost_category_id)))
    return df[["project_id", "cost_category_id", "original_budget_inr", "change_order_budget_inr", "revised_budget_inr"]]


# --------------------------------------------------------------------------------------
# Facts
# --------------------------------------------------------------------------------------
def clean_cost_ledger(cats):
    t = "cost_ledger"
    df = read(t)
    n = len(df)
    df = df.drop_duplicates()
    log(t, "exact duplicate postings", "removed (would double-count cost)", n - len(df))
    zero = df.amount_inr == 0
    log(t, "zero-amount placeholder postings", "removed", zero.sum())
    df = df[~zero].copy()
    typo_map = {"matrial": "Material", "materials": "Material", "mat-01": "Material", "labor": "Labour",
                "labour cost": "Labour", "manpower": "Labour", "sub-contractor": "Subcontractor",
                "subcon": "Subcontractor", "sub contractor": "Subcontractor", "subcontract": "Subcontractor",
                "equip.": "Equipment", "equipment hire": "Equipment", "machinery": "Equipment",
                "transport": "Transportation", "freight": "Transportation", "logistics": "Transportation",
                "power & fuel": "Energy", "electricity": "Energy", "overheads": "Overhead", "o/h": "Overhead",
                "site overhead": "Overhead", "misc": "Other", "others": "Other", "other costs": "Other"}
    canonical = {c.lower(): c for c in cats.cost_category}
    key = df.cost_category.fillna("").str.strip().str.lower()
    mapped = key.map(canonical).fillna(key.map(typo_map))
    log(t, "category typos and legacy labels", "mapped to 8 standard categories",
        (mapped.notna() & (mapped != df.cost_category)).sum())
    missing = mapped.isna()
    mapped[missing] = df.loc[missing, "gl_account"].map(dict(zip(cats.gl_account, cats.cost_category)))
    log(t, "missing cost category", "inferred from GL account code", missing.sum())
    df["cost_category_id"] = mapped.map(dict(zip(cats.cost_category, cats.cost_category_id)))
    df["posting_date"] = to_date(df.posting_date)
    return df[["document_no", "project_id", "cost_category_id", "gl_account", "posting_date", "source_system", "amount_inr"]]


def clean_purchase_orders(suppliers, materials, steel):
    t = "purchase_orders"
    df = read(t, dtype={"supplier_name": str})
    n = len(df)
    df = df.drop_duplicates()
    log(t, "exact duplicate PO lines", "removed (would double-count spend)", n - len(df))

    master = {normalise_name(v): k for k, v in zip(suppliers.supplier_id, suppliers.supplier_name)}
    exact = df.supplier_name.map(lambda s: master.get(normalise_name(s)))
    fuzzy = df.loc[exact.isna(), "supplier_name"].map(
        lambda s: master.get((difflib.get_close_matches(normalise_name(s), master.keys(), n=1, cutoff=0.85) or [None])[0]))
    df["supplier_id"] = exact.fillna(fuzzy)
    variant = df.supplier_name != df.supplier_id.map(dict(zip(suppliers.supplier_id, suppliers.supplier_name)))
    log(t, "inconsistent supplier names", "matched to vendor master after normalising", (variant & exact.notna()).sum())
    log(t, "supplier names not matching after normalising", "matched by fuzzy similarity >= 0.85", fuzzy.notna().sum())
    assert df.supplier_id.notna().all(), "unmatched supplier names remain"

    date_cols = ["pr_date", "pr_approval_date", "rfq_date", "po_date", "supplier_confirm_date", "promised_date",
                 "delivery_date", "inspection_date", "grn_date", "need_by_date"]
    for c in date_cols:
        df[c] = parse_mixed_dates(df[c], t, c)

    # Day and month swapped: delivery before order confirmation, and swapping fixes it
    def swap(d):
        try:
            return d.replace(month=d.day, day=d.month)
        except (ValueError, AttributeError):
            return None
    bad = df.delivery_date.notna() & (df.delivery_date < df.supplier_confirm_date)
    swapped = df.loc[bad, "delivery_date"].map(swap)
    ok = swapped.notna() & (swapped >= df.loc[bad, "supplier_confirm_date"]) & (
        df.loc[bad, "inspection_date"].isna() | (swapped <= df.loc[bad, "inspection_date"]))
    df.loc[swapped[ok].index, "delivery_date"] = swapped[ok]
    log(t, "delivery date before order confirmation", "day/month swap corrected", ok.sum())
    log(t, "delivery date before order confirmation", "could not be corrected, set to null", (~ok).sum())
    df.loc[swapped[~ok].index, "delivery_date"] = None

    # Missing delivery date on a received line: impute from inspection date minus the typical lag
    lag = pd.Series([(i - d).days for d, i in zip(df.delivery_date, df.inspection_date)
                     if pd.notna(d) and pd.notna(i)]).median()
    miss = df.delivery_date.isna() & df.inspection_date.notna()
    df["delivery_date_imputed"] = miss
    df.loc[miss, "delivery_date"] = df.loc[miss, "inspection_date"].map(lambda d: d - pd.Timedelta(days=int(lag)))
    log(t, "missing delivery date on received line", f"imputed as inspection date minus median lag ({int(lag)} days)", miss.sum())

    neg = df.quantity < 0
    df.loc[neg, "quantity"] = df.loc[neg, "quantity"].abs()
    log(t, "negative quantity", "sign corrected (line value is positive)", neg.sum())
    # line_value is the invoiced amount and is trusted; unit price must agree with it
    implied = df.line_value_inr / df.quantity
    missing_p = df.unit_price_inr.isna()
    zero_p = df.unit_price_inr == 0
    inconsistent = ~missing_p & ~zero_p & ((df.unit_price_inr - implied).abs() / implied > 0.01)
    log(t, "missing unit price", "derived as line value / quantity", missing_p.sum())
    log(t, "zero unit price", "derived as line value / quantity", zero_p.sum())
    log(t, "unit price inconsistent with line value (e.g. extra zero)", "replaced by line value / quantity",
        inconsistent.sum())
    fix = missing_p | zero_p | inconsistent
    df.loc[fix, "unit_price_inr"] = implied[fix].round(2)

    # Derived columns used by every downstream tool
    mat = materials.set_index("material_id")
    idx = dict(zip(pd.to_datetime(steel.month_start).dt.to_period("M"), steel.steel_price_index))
    po_month = pd.to_datetime(df.po_date).dt.to_period("M")
    steel_linked = df.material_id.map(mat.is_steel_linked).astype(bool)
    std = df.material_id.map(mat.standard_price_inr)
    df["benchmark_unit_price_inr"] = np.where(steel_linked, std * po_month.map(idx) / 100, std).round(2)
    days = lambda a, b: [(y - x).days if pd.notna(x) and pd.notna(y) else np.nan for x, y in zip(df[a], df[b])]  # noqa: E731
    df["lead_time_days"] = days("po_date", "grn_date")
    df["delivery_delay_days"] = days("promised_date", "delivery_date")
    df["is_on_time"] = np.where(df.delivery_date.notna(), df.delivery_delay_days <= 0, None)
    for c in ("lead_time_days", "delivery_delay_days"):
        df[c] = pd.array(df[c], dtype="Int64")
    cols = ["po_line_id", "po_number", "project_id", "supplier_id", "material_id", "buyer_id"] + date_cols + [
        "quantity", "unit_price_inr", "line_value_inr", "benchmark_unit_price_inr", "qty_rejected", "line_status",
        "lead_time_days", "delivery_delay_days", "is_on_time", "delivery_date_imputed"]
    return df[cols]


def clean_production_log():
    t = "production_log"
    df = read(t)
    df["production_date"] = to_date(df.production_date)
    over = (df.actual_output_t > 3 * df.planned_output_t) & (df.actual_output_t / 10 <= 1.5 * df.planned_output_t)
    df.loc[over, "actual_output_t"] = (df.loc[over, "actual_output_t"] / 10).round(3)
    log(t, "output more than 3x plan and plausible after /10", "decimal-shift corrected", over.sum())
    neg = df.rework_t < 0
    df.loc[neg, "rework_t"] = df.loc[neg, "rework_t"].abs()
    log(t, "negative rework tonnes", "sign corrected", neg.sum())
    miss = df.regular_labour_hours.isna()
    ratio = (df.regular_labour_hours / df.actual_output_t).groupby(df.works_location_id).transform("median")
    df["labour_hours_imputed"] = miss
    df.loc[miss, "regular_labour_hours"] = (df.loc[miss, "actual_output_t"] * ratio[miss]).round(1)
    log(t, "missing regular labour hours", "imputed: output x works median hours per tonne", miss.sum())
    return df


def clean_machine_log():
    t = "machine_log"
    df = read(t)
    n = len(df)
    df = df.drop_duplicates()
    log(t, "exact duplicate machine-day records", "removed", n - len(df))
    df["log_date"] = to_date(df.log_date)
    neg = df.downtime_hours < 0
    df.loc[neg, "downtime_hours"] = df.loc[neg, "downtime_hours"].abs()
    log(t, "negative downtime hours", "sign corrected", neg.sum())
    # The machine log must satisfy: available = downtime + operating + idle. Operating and idle hours
    # come from the machine controller; downtime is typed in by hand, so it is the column to correct.
    implied = (df.available_hours - df.operating_hours - df.idle_hours).round(2)
    broken = (df.downtime_hours - implied).abs() > 0.05   # tolerance for 2-dp rounding
    log(t, "downtime breaks available = downtime + operating + idle (e.g. extra zero)",
        "recalculated from the hour balance", (broken & (df.downtime_hours > df.available_hours)).sum())
    log(t, "downtime breaks the hour balance but is below available hours (hidden extra zero)",
        "recalculated from the hour balance", (broken & (df.downtime_hours <= df.available_hours)).sum())
    df.loc[broken, "downtime_hours"] = implied[broken].clip(lower=0)
    miss = df.downtime_reason.isna() & (df.downtime_hours > 0)
    df.loc[miss, "downtime_reason"] = "Unspecified"
    log(t, "downtime without a reason code", "labelled 'Unspecified'", miss.sum())
    return df


def clean_timesheets():
    t = "site_timesheets"
    df = read(t)
    df["week_ending_date"] = to_date(df.week_ending_date)
    ok = df.overtime_hours.notna()
    rate = (df.labour_cost_inr / (df.regular_hours + df.idle_hours + C.OVERTIME_MULTIPLIER * df.overtime_hours))
    rate = rate.where(ok).groupby([df.project_id, df.labour_type]).transform("median")
    miss = ~ok
    implied_ot = (df.labour_cost_inr / rate - df.regular_hours - df.idle_hours) / C.OVERTIME_MULTIPLIER
    df.loc[miss, "overtime_hours"] = implied_ot[miss].clip(lower=0).round(1)
    log(t, "missing overtime hours", "back-calculated from labour cost and the crew's hourly rate", miss.sum())
    zero = df.headcount == 0
    hours = df.regular_hours + df.overtime_hours + df.idle_hours
    df.loc[zero, "headcount"] = (hours[zero] / np.where(df.labour_type[zero] == "Engineering", 48, 52)).round().clip(lower=1)
    log(t, "zero headcount with hours booked", "estimated from hours / standard weekly hours", zero.sum())
    df["headcount"] = df.headcount.astype(int)
    return df


def clean_milestones():
    t = "milestones"
    df = read(t)
    for c in ("planned_start_date", "planned_end_date", "actual_start_date", "actual_end_date"):
        df[c] = to_date(df[c])
    bad = df.actual_start_date.notna() & df.actual_end_date.notna() & (df.actual_end_date < df.actual_start_date)
    df.loc[bad, ["actual_start_date", "actual_end_date"]] = df.loc[bad, ["actual_end_date", "actual_start_date"]].values
    log(t, "actual end before actual start", "start and end swapped back", bad.sum())
    d = lambda a, b: [(y - x).days if pd.notna(x) and pd.notna(y) else np.nan for x, y in zip(df[a], df[b])]  # noqa: E731
    df["planned_duration_days"] = d("planned_start_date", "planned_end_date")
    df["actual_duration_days"] = d("actual_start_date", "actual_end_date")
    df["start_delay_days"] = d("planned_start_date", "actual_start_date")
    df["end_delay_days"] = d("planned_end_date", "actual_end_date")
    for c in ("planned_duration_days", "actual_duration_days", "start_delay_days", "end_delay_days"):
        df[c] = pd.array(df[c], dtype="Int64")
    return df


def clean_billing():
    t = "billing"
    df = read(t)
    n = len(df)
    df = df.drop_duplicates()
    log(t, "duplicate invoices in extract", "removed (would double-count revenue)", n - len(df))
    std = {"milestone": "Milestone Billing", "milestone invoice": "Milestone Billing", "co": "Change Order",
           "variation": "Change Order", "pvc": "Price Variation", "price escalation": "Price Variation",
           "ld": "Liquidated Damages", "penalty - ld": "Liquidated Damages"}
    key = df.revenue_type.str.strip().str.lower()
    canonical = {v.lower(): v for v in std.values()}
    fixed = key.map(canonical).fillna(key.map(std))
    log(t, "non-standard revenue type labels", "mapped to 4 standard types", (fixed != df.revenue_type).sum())
    df["revenue_type"] = fixed
    df["invoice_date"] = to_date(df.invoice_date)
    return df


def build_dim_date():
    d = pd.DataFrame({"date": pd.date_range("2020-10-01", "2027-12-31")})
    d["date_key"] = d.date.dt.strftime("%Y%m%d").astype(int)
    d["year"] = d.date.dt.year
    d["quarter"] = "Q" + d.date.dt.quarter.astype(str)
    d["month_num"] = d.date.dt.month
    d["month_name"] = d.date.dt.strftime("%B")
    d["month_short"] = d.date.dt.strftime("%b")
    d["year_month"] = d.date.dt.strftime("%Y-%m")
    d["month_start"] = d.date.dt.to_period("M").dt.to_timestamp()
    fy = np.where(d.month_num >= 4, d.year + 1, d.year)            # C02: FY ends in March
    d["fiscal_year_num"] = fy
    d["fiscal_year"] = "FY" + pd.Series(fy % 100).astype(str).str.zfill(2)
    d["fiscal_month_num"] = (d.month_num - 4) % 12 + 1
    d["fiscal_quarter"] = "Q" + ((d.fiscal_month_num - 1) // 3 + 1).astype(str)
    d["day_of_week"] = d.date.dt.strftime("%a")
    d["is_working_day"] = (d.date.dt.weekday != 6) & ~d.date.dt.date.isin(R.HOLIDAYS)
    d["date"] = d.date.dt.date
    d["month_start"] = d.month_start.dt.date
    return d


def main():
    print("Cleaning raw extracts ...")
    dims = clean_dimensions()
    steel = read("steel_price_index")
    tables = dict(dims)
    tables["dim_project"] = clean_projects()
    tables["dim_date"] = build_dim_date()
    tables["fact_budget"] = clean_budgets(dims["dim_cost_category"])
    tables["fact_project_cost"] = clean_cost_ledger(dims["dim_cost_category"])
    tables["fact_procurement"] = clean_purchase_orders(dims["dim_supplier"], dims["dim_material"], steel)
    tables["fact_operations"] = clean_production_log()
    tables["fact_equipment"] = clean_machine_log()
    tables["fact_labor"] = clean_timesheets()
    tables["fact_milestones"] = clean_milestones()
    tables["fact_revenue"] = clean_billing()
    tables["ref_steel_price_index"] = steel

    C.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(C.DATA_PROCESSED / f"{name}.csv", index=False)
    pd.DataFrame(LOG).to_csv(C.DATA_QA / "cleaning_log.csv", index=False)
    print(f"Wrote {len(tables)} processed tables to data/processed/ and {len(LOG)} cleaning rules to data/qa/")


if __name__ == "__main__":
    main()
