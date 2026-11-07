"""As-Is / To-Be procurement process analysis (Phase 16).

Run: python python/analysis/process_improvement.py

As-Is cycle times are measured from the timestamps on every PO line. To-Be targets are NOT
invented percentages: for each internal step the target is the 25th-percentile time ProjectCo
already achieves today on comparable lines (best demonstrated practice). A digital workflow is
assumed to make that best-quartile performance the norm. Supplier manufacturing lead time is
external and left unchanged.
"""
import numpy as np
import pandas as pd

from common import (BLUE, GREY, ORANGE, TEXT_2, delay_cost_per_day, load, plt, project_kpis, save_fig, save_table,
                    update_metrics)

STEPS = [  # (step, start column, end column, internal?, To-Be change)
    ("PR approval", "pr_date", "pr_approval_date", True, "Digital approval: value-based routing, mobile approve, 48h escalation"),
    ("RFQ issue", "pr_approval_date", "rfq_date", True, "RFQ auto-created from approved PR"),
    ("Quotes and PO", "rfq_date", "po_date", True, "e-RFQ portal with pre-qualified suppliers; online comparison"),
    ("Supplier confirmation", "po_date", "supplier_confirm_date", True, "PO acknowledgement on supplier portal"),
    ("Supplier lead time", "supplier_confirm_date", "delivery_date", False, "Unchanged (external)"),
    ("Wait for inspection", "delivery_date", "inspection_date", True, "QC slot booked from supplier dispatch notice"),
    ("Goods receipt posting", "inspection_date", "grn_date", True, "Mobile GRN on inspection pass"),
]


def main():
    t = load()
    po = t["fact_procurement"].merge(t["dim_material"][["material_id", "criticality_class"]])
    po = po[po.grn_date.notna()].copy()
    po["value_band"] = pd.cut(po.line_value_inr, [0, 1e6, 1e7, np.inf], labels=["< Rs 10 L", "Rs 10 L-1 Cr", "> Rs 1 Cr"])
    rejected = po.qty_rejected > 0

    rows, saved = [], pd.Series(0.0, index=po.index)
    for step, a, b, internal, change in STEPS:
        days = (po[b] - po[a]).dt.days
        if step == "Goods receipt posting":
            days = days.where(~rejected)          # rejected lines wait for replacement supply, not paperwork
        target = days.groupby(po.value_band, observed=True).transform(lambda x: x.quantile(0.25)) if internal else days
        to_be = np.minimum(days, target)
        if internal:
            saved = saved.add((days - to_be).fillna(0), fill_value=0)
        rows.append(dict(step=step, internal=internal, as_is_mean=days.mean(), as_is_median=days.median(),
                         as_is_p90=days.quantile(0.9), to_be_mean=to_be.mean(), saved_mean=(days - to_be).mean(),
                         to_be_change=change))
    steps = pd.DataFrame(rows)
    save_table(steps.round(2), "process_as_is_to_be")

    internal = steps[steps.internal]
    as_is_internal, to_be_internal = internal.as_is_mean.sum(), internal.to_be_mean.sum()

    # Chart: internal process time per step, As-Is vs To-Be
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = np.arange(len(internal))
    ax.barh(y + 0.2, internal.as_is_mean, height=0.38, color=GREY, label=f"As-Is ({as_is_internal:.1f} days)")
    ax.barh(y - 0.2, internal.to_be_mean, height=0.38, color=BLUE, label=f"To-Be ({to_be_internal:.1f} days)")
    for i, (a_, b_) in enumerate(zip(internal.as_is_mean, internal.to_be_mean)):
        ax.annotate(f"{a_:.1f}", (a_, i + 0.2), xytext=(3, 0), textcoords="offset points", va="center", fontsize=8, color=TEXT_2)
        ax.annotate(f"{b_:.1f}", (b_, i - 0.2), xytext=(3, 0), textcoords="offset points", va="center", fontsize=8, color=TEXT_2)
    ax.set_yticks(y, internal.step)
    ax.invert_yaxis()
    ax.set(title="Internal procurement cycle time per PO line: As-Is vs To-Be (mean days)", xlabel="Days")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="y", visible=False)
    save_fig(fig, "process_as_is_to_be")

    # --- Impact on critical items and project delay (completed projects) -----------------
    k = project_kpis(t)
    done_ids = set(k.loc[k.status == "Completed", "project_id"])
    po["saved_days"] = saved
    a = po[(po.criticality_class == "A") & po.project_id.isin(done_ids)].copy()
    a["late_now"] = (a.grn_date - a.need_by_date).dt.days.clip(lower=0)
    a["late_to_be"] = ((a.grn_date - a.need_by_date).dt.days - a.saved_days).clip(lower=0)
    proj = a.groupby("project_id")[["late_now", "late_to_be"]].max()
    proj["lateness_reduction"] = proj.late_now - proj.late_to_be
    import json
    from common import C
    metrics = json.loads((C.REPORTS / "metrics.json").read_text())
    pass_through = metrics["procurement"]["pass_through_days_per_day_late"]
    proj["delay_days_avoided"] = pass_through * proj.lateness_reduction
    dc = delay_cost_per_day(t)
    proj["value_inr"] = proj.delay_days_avoided * proj.index.map(dc.delay_cost_per_day)
    save_table(proj.reset_index().round(2), "process_delay_impact_by_project")

    fy = t["dim_date"].set_index("date").fiscal_year
    completions = k[k.status == "Completed"].actual_end_date.map(fy).value_counts()
    per_year = completions.reindex(["FY25", "FY26"]).fillna(0).mean()
    annual_value = proj.value_inr.sum() / len(done_ids) * per_year
    lines_per_year = po.po_date.map(fy).value_counts().reindex(["FY25", "FY26"]).mean()

    update_metrics("process", {
        "as_is_internal_days": as_is_internal, "to_be_internal_days": to_be_internal,
        "internal_days_saved": as_is_internal - to_be_internal,
        "internal_reduction_pct": 100 * (1 - to_be_internal / as_is_internal),
        "approval_as_is_mean": float(steps.loc[steps.step == "PR approval", "as_is_mean"].iloc[0]),
        "approval_to_be_mean": float(steps.loc[steps.step == "PR approval", "to_be_mean"].iloc[0]),
        "approval_share_of_internal_pct": 100 * float(steps.loc[steps.step == "PR approval", "as_is_mean"].iloc[0]) / as_is_internal,
        "biggest_step": internal.sort_values("as_is_mean").iloc[-1].step,
        "projects_with_delay_avoided": int((proj.delay_days_avoided > 0).sum()),
        "delay_days_avoided_total": proj.delay_days_avoided.sum(),
        "delay_value_avoided_total_cr": proj.value_inr.sum() / 1e7,
        "completions_per_year": per_year, "annual_delay_value_cr": annual_value / 1e7,
        "po_lines_per_year": lines_per_year,
    })
    print(steps[["step", "as_is_mean", "as_is_p90", "to_be_mean", "saved_mean"]].round(1).to_string(index=False))
    print(f"Internal cycle {as_is_internal:.1f} -> {to_be_internal:.1f} days; delay avoided "
          f"{proj.delay_days_avoided.sum():.0f} project-days on {int((proj.delay_days_avoided > 0).sum())} projects; "
          f"annual value Rs {annual_value / 1e7:.2f} Cr")


if __name__ == "__main__":
    main()
