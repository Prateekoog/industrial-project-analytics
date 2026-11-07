"""Automated validation of the processed dataset (Phase 20).

Run from the project root:
    python python/validation/validate_data.py

Three layers of checks, each producing PASS / FAIL rows in data/qa/validation_report.csv:
  1. Integrity      - primary keys unique, foreign keys resolve, values in valid ranges
  2. Reconciliation - sub-ledgers agree with the cost ledger, revenue agrees with its formula,
                      budgets agree with estimates, schedule dates agree with project dates
  3. Cleaning audit - how many injected issues the cleaning recovered, and how far processed
                      totals sit from the true (pre-corruption) totals
The script exits with code 1 if any integrity or reconciliation check fails.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

RESULTS = []


def check(layer, name, passed, detail=""):
    RESULTS.append(dict(layer=layer, check=name, result="PASS" if passed else "FAIL", detail=detail))
    print(f"  {'PASS' if passed else 'FAIL'}  [{layer}] {name}  {detail}")


def load(folder):
    return {p.stem: pd.read_csv(p) for p in sorted(folder.glob("*.csv"))}


def integrity(t):
    keys = {"dim_project": ["project_id"], "dim_client": ["client_id"], "dim_supplier": ["supplier_id"],
            "dim_material": ["material_id"], "dim_location": ["location_id"], "dim_employee": ["employee_id"],
            "dim_equipment": ["equipment_id"], "dim_work_centre": ["work_centre_id"], "dim_date": ["date"],
            "dim_cost_category": ["cost_category_id"], "dim_stage": ["stage_id"],
            "fact_budget": ["project_id", "cost_category_id"], "fact_project_cost": ["document_no"],
            "fact_procurement": ["po_line_id"], "fact_operations": ["production_id"],
            "fact_equipment": ["machine_log_id"], "fact_labor": ["labour_entry_id"],
            "fact_milestones": ["project_id", "stage_id"], "fact_revenue": ["invoice_no"]}
    for table, cols in keys.items():
        dup = t[table].duplicated(cols).sum()
        check("integrity", f"{table} primary key {'+'.join(cols)} is unique", dup == 0, f"{dup} duplicates")

    fks = [("dim_project", "client_id", "dim_client", "client_id"),
           ("dim_project", "site_location_id", "dim_location", "location_id"),
           ("dim_project", "works_location_id", "dim_location", "location_id"),
           ("dim_project", "project_manager_id", "dim_employee", "employee_id"),
           ("dim_equipment", "work_centre_id", "dim_work_centre", "work_centre_id"),
           ("fact_budget", "project_id", "dim_project", "project_id"),
           ("fact_budget", "cost_category_id", "dim_cost_category", "cost_category_id"),
           ("fact_project_cost", "project_id", "dim_project", "project_id"),
           ("fact_project_cost", "cost_category_id", "dim_cost_category", "cost_category_id"),
           ("fact_project_cost", "posting_date", "dim_date", "date"),
           ("fact_procurement", "project_id", "dim_project", "project_id"),
           ("fact_procurement", "supplier_id", "dim_supplier", "supplier_id"),
           ("fact_procurement", "material_id", "dim_material", "material_id"),
           ("fact_procurement", "buyer_id", "dim_employee", "employee_id"),
           ("fact_procurement", "po_date", "dim_date", "date"),
           ("fact_operations", "project_id", "dim_project", "project_id"),
           ("fact_operations", "works_location_id", "dim_location", "location_id"),
           ("fact_operations", "bottleneck_work_centre_id", "dim_work_centre", "work_centre_id"),
           ("fact_operations", "production_date", "dim_date", "date"),
           ("fact_equipment", "equipment_id", "dim_equipment", "equipment_id"),
           ("fact_equipment", "log_date", "dim_date", "date"),
           ("fact_labor", "project_id", "dim_project", "project_id"),
           ("fact_labor", "supervisor_id", "dim_employee", "employee_id"),
           ("fact_milestones", "project_id", "dim_project", "project_id"),
           ("fact_milestones", "stage_id", "dim_stage", "stage_id"),
           ("fact_revenue", "project_id", "dim_project", "project_id"),
           ("fact_revenue", "invoice_date", "dim_date", "date")]
    for child, col, parent, pcol in fks:
        vals = t[child][col].dropna()
        orphans = (~vals.isin(t[parent][pcol])).sum()
        check("integrity", f"{child}.{col} -> {parent}.{pcol}", orphans == 0, f"{orphans} orphans")

    po, eq, ops = t["fact_procurement"], t["fact_equipment"], t["fact_operations"]
    check("integrity", "PO quantities and prices are positive",
          ((po.quantity > 0) & (po.unit_price_inr > 0)).all())
    check("integrity", "PO line value = quantity x unit price (within 1%)",
          ((po.quantity * po.unit_price_inr - po.line_value_inr).abs() <= 0.01 * po.line_value_inr + 1).all())
    order = pd.to_datetime(po.pr_date) <= pd.to_datetime(po.po_date)
    order &= pd.to_datetime(po.po_date) <= pd.to_datetime(po.delivery_date).fillna(pd.Timestamp.max)
    check("integrity", "PO dates in process order (PR <= PO <= delivery)", order.all(), f"{(~order).sum()} violations")
    check("integrity", "machine hours: 0 <= downtime, operating <= available",
          ((eq.downtime_hours >= 0) & (eq.downtime_hours + eq.operating_hours <= eq.available_hours + 0.01)).all())
    check("integrity", "production: output >= 0 and 0 <= rework <= output",
          ((ops.actual_output_t >= 0) & (ops.rework_t >= 0) & (ops.rework_t <= ops.actual_output_t)).all())
    ms = t["fact_milestones"].dropna(subset=["actual_end_date"])
    check("integrity", "milestones: actual end >= actual start",
          (pd.to_datetime(ms.actual_end_date) >= pd.to_datetime(ms.actual_start_date)).all())


def reconciliation(t):
    proj, cost, po = t["dim_project"], t["fact_project_cost"], t["fact_procurement"]
    ops, lab, rev, bud = t["fact_operations"], t["fact_labor"], t["fact_revenue"], t["fact_budget"]

    def recon(name, ledger, subledger, tol=1.0):
        diff = (ledger.reindex(subledger.index.union(ledger.index), fill_value=0)
                - subledger.reindex(subledger.index.union(ledger.index), fill_value=0)).abs()
        check("reconciliation", name, (diff <= tol).all(), f"max difference Rs {diff.max():,.2f}")

    by = lambda df, cond: df[cond].groupby("project_id").amount_inr.sum()  # noqa: E731
    recon("Material ledger = received PO line value, per project",
          by(cost, (cost.cost_category_id == 1) & (cost.source_system == "Procurement")),
          po[po.line_status == "Received"].groupby("project_id").line_value_inr.sum())
    recon("Works labour ledger = production log labour cost, per project",
          by(cost, (cost.cost_category_id == 2) & (cost.source_system == "Production")),
          ops.groupby("project_id").labour_cost_inr.sum())
    recon("Site/engineering labour ledger = timesheet cost, per project",
          by(cost, (cost.cost_category_id == 2) & (cost.source_system == "Timesheet")),
          lab.groupby("project_id").labour_cost_inr.sum())
    recon("Works machine cost ledger = production log machine cost, per project",
          by(cost, (cost.cost_category_id == 4) & (cost.source_system == "Production")),
          ops.groupby("project_id").machine_cost_inr.sum())
    recon("Works energy ledger = production log energy cost, per project",
          by(cost, (cost.cost_category_id == 6) & (cost.source_system == "Production")),
          ops.groupby("project_id").energy_cost_inr.sum())

    b = bud.assign(diff=(bud.original_budget_inr + bud.change_order_budget_inr - bud.revised_budget_inr).abs())
    check("reconciliation", "Revised budget = original + change-order budget", (b["diff"] < 1).all())

    done = proj[proj.status == "Completed"].set_index("project_id")
    r = rev.pivot_table(index="project_id", columns="revenue_type", values="amount_inr", aggfunc="sum").fillna(0)
    r = r.reindex(done.index).fillna(0)
    billed_share = r.get("Milestone Billing", 0) / done.contract_value_inr
    check("reconciliation", "Completed projects billed 100% of contract value in milestones",
          (billed_share.sub(1).abs() < 1e-6).all(), f"min {billed_share.min():.4f}")
    ld = -r.get("Liquidated Damages", pd.Series(0, index=r.index))
    cap_ok = (ld <= C.LD_CAP * done.contract_value_inr + 1).all()
    check("reconciliation", "Liquidated damages never exceed the 5% cap", cap_ok)
    weeks_ok = all(math.isclose(v / cv / C.LD_RATE_PER_WEEK, round(v / cv / C.LD_RATE_PER_WEEK), abs_tol=1e-6)
                   for v, cv in zip(ld, done.contract_value_inr) if v > 0)
    check("reconciliation", "LD amounts are whole weeks x 0.5% of contract value", weeks_ok)

    ms = t["fact_milestones"]
    comm = ms[ms.stage_id == 7].set_index("project_id")
    match = (pd.to_datetime(done.actual_end_date) == pd.to_datetime(comm.reindex(done.index).actual_end_date)).all()
    check("reconciliation", "Project actual end date = commissioning actual end date", match)
    start = ms[ms.stage_id == 1].set_index("project_id").reindex(proj.project_id).actual_start_date.values
    check("reconciliation", "Project actual start date = concept stage actual start",
          (pd.to_datetime(start) == pd.to_datetime(proj.actual_start_date)).all())
    status_ok = ((proj.status == "Completed") == proj.actual_end_date.notna()).all()
    check("reconciliation", "Status 'Completed' <=> actual end date present", status_ok)
    pct = proj[proj.status == "Completed"].percent_complete.eq(100).all()
    check("reconciliation", "Completed projects are 100% complete", pct)
    cutoff = str(C.CUTOFF)
    late_rows = sum((t[f][c].dropna().astype(str) > cutoff).sum() for f, c in
                    (("fact_project_cost", "posting_date"), ("fact_revenue", "invoice_date"),
                     ("fact_operations", "production_date"), ("fact_equipment", "log_date"),
                     ("fact_procurement", "grn_date")))
    check("reconciliation", "No actual transactions after the data cut-off", late_rows == 0, f"{late_rows} rows")


def cleaning_audit(t):
    truth_dir = C.DATA_QA / "truth"
    issues = pd.read_csv(C.DATA_QA / "injected_issues_log.csv")
    truth = load(truth_dir)
    po_t = truth["fact_procurement"].set_index("po_line_id")
    po_c = t["fact_procurement"].set_index("po_line_id")
    restored = []
    for _, i in issues.iterrows():
        ok = None
        if i.table == "purchase_orders" and i.column in ("unit_price_inr", "quantity"):
            ok = abs(po_c.at[i.record_id, i.column] - po_t.at[i.record_id, i.column]) <= 0.01 * abs(po_t.at[i.record_id, i.column]) + 0.01
        elif i.table == "purchase_orders" and i.column == "supplier_name":
            ok = po_c.at[i.record_id, "supplier_id"] == po_t.at[i.record_id, "supplier_id"]
        elif i.table == "purchase_orders" and i.column == "delivery_date":
            diff = abs((pd.Timestamp(po_c.at[i.record_id, "delivery_date"]) - pd.Timestamp(po_t.at[i.record_id, "delivery_date"])).days)
            ok = diff == 0 if i.issue_type == "day_month_swapped" else diff <= 3
        if ok is not None:
            restored.append(dict(table=i.table, issue_type=i.issue_type, column=i.column, restored=bool(ok)))
    rest = pd.DataFrame(restored).groupby(["table", "issue_type", "column"]).restored.agg(["size", "mean"])
    for (table, issue, col), row in rest.iterrows():
        check("cleaning", f"{table}.{col} {issue}: restored {row['mean']:.0%} of {row['size']}",
              True, "(informational)")

    for table, col in (("fact_project_cost", "amount_inr"), ("fact_procurement", "line_value_inr"),
                       ("fact_operations", "actual_output_t"), ("fact_equipment", "downtime_hours"),
                       ("fact_revenue", "amount_inr"), ("fact_labor", "overtime_hours")):
        true, clean = truth[table][col].sum(), t[table][col].sum()
        gap = (clean - true) / true * 100
        check("cleaning", f"{table}.{col} total within 0.5% of truth", abs(gap) <= 0.5, f"gap {gap:+.3f}%")
    for table in ("fact_project_cost", "fact_procurement", "fact_equipment", "fact_revenue"):
        check("cleaning", f"{table} row count equals truth after de-duplication",
              len(truth[table]) == len(t[table]), f"{len(t[table]):,} vs {len(truth[table]):,}")


def main():
    print("Validating processed data ...")
    t = load(C.DATA_PROCESSED)
    integrity(t)
    reconciliation(t)
    if (C.DATA_QA / "truth").exists():
        cleaning_audit(t)
    report = pd.DataFrame(RESULTS)
    report.to_csv(C.DATA_QA / "validation_report.csv", index=False)
    fails = report[(report.result == "FAIL") & report.layer.isin(["integrity", "reconciliation"])]
    print(f"\n{(report.result == 'PASS').sum()} passed, {(report.result == 'FAIL').sum()} failed")
    if len(fails):
        sys.exit(1)


if __name__ == "__main__":
    main()
