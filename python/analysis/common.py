"""Shared helpers for the analysis scripts: loading, the project KPI table, chart style.

The project KPI table here applies exactly the same formulas as sql/00_views.sql, so SQL,
Python, Excel and Power BI all report the same numbers (checked in validation).
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

# Chart palette (validated reference palette from the dataviz method)
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29c"
STATUS = {"Under budget": "#2a78d6", "On budget": "#0ca30c", "Warning": "#fab219", "Critical": "#d03b3b",
          "On time": "#0ca30c", "Minor delay": "#fab219", "Major delay": "#ec835a", "Critical delay": "#d03b3b",
          "Low": "#0ca30c", "Medium": "#fab219", "High": "#ec835a"}
TEXT, TEXT_2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": "#d6d5d0", "axes.labelcolor": TEXT_2, "xtick.color": TEXT_2, "ytick.color": TEXT_2,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": TEXT, "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#ebeae6",
    "grid.linewidth": 0.8, "axes.axisbelow": True, "font.size": 10, "legend.frameon": False,
    "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
})


def load():
    """All processed tables, with date columns parsed."""
    t = {}
    for p in sorted(C.DATA_PROCESSED.glob("*.csv")):
        df = pd.read_csv(p)
        for c in df.columns:
            if c.endswith("_date") or c in ("date", "month_start"):
                df[c] = pd.to_datetime(df[c])
        t[p.stem] = df
    return t


def cr(x):
    return x / C.CRORE


def project_kpis(t):
    """One row per project: budget, cost, revenue, profit, margin, variance, schedule (mirrors SQL views)."""
    p = t["dim_project"].set_index("project_id")
    b = t["fact_budget"].groupby("project_id")[["original_budget_inr", "change_order_budget_inr", "revised_budget_inr"]].sum()
    b.columns = ["estimated_cost", "change_order_budget", "revised_budget"]
    cost = t["fact_project_cost"].groupby("project_id").amount_inr.sum().rename("actual_cost_to_date")
    rev = t["fact_revenue"].pivot_table(index="project_id", columns="revenue_type", values="amount_inr",
                                        aggfunc="sum").reindex(p.index).fillna(0)
    k = p.join(b).join(cost)
    k["revenue_to_date"] = rev.sum(axis=1)
    k["pvc_revenue"] = rev.get("Price Variation", 0)
    k["ld_deducted"] = -rev.get("Liquidated Damages", 0)
    k["co_revenue"] = rev.get("Change Order", 0)
    k["approved_co_value"] = k.change_order_budget * k.contract_value_inr / k.estimated_cost
    done = k.status == "Completed"
    k["estimated_profit"] = k.contract_value_inr - k.estimated_cost
    k["estimated_margin_pct"] = 100 * k.estimated_profit / k.contract_value_inr
    k["earned_value"] = k.revised_budget * k.percent_complete / 100
    k["cpi"] = np.where(done, np.nan, k.earned_value / k.actual_cost_to_date)
    k["final_cost"] = np.where(done, k.actual_cost_to_date, k.actual_cost_to_date / (k.percent_complete / 100))
    k["final_revenue"] = np.where(done, k.revenue_to_date, k.contract_value_inr + k.approved_co_value + k.pvc_revenue)
    k["cost_variance"] = k.final_cost - k.revised_budget
    k["cost_variance_pct"] = 100 * k.cost_variance / k.revised_budget
    k["final_profit"] = k.final_revenue - k.final_cost
    k["final_margin_pct"] = 100 * k.final_profit / k.final_revenue
    k["margin_deterioration_pp"] = k.estimated_margin_pct - k.final_margin_pct
    k["cost_status"] = pd.cut(k.cost_variance_pct, [-np.inf, C.CV_UNDER, C.CV_WARNING, C.CV_CRITICAL, np.inf],
                              labels=["Under budget", "On budget", "Warning", "Critical"]).astype(str)

    ms = t["fact_milestones"]
    started = ms[ms.actual_start_date.notna()]
    slip = started.assign(s=started.end_delay_days.fillna(started.start_delay_days)).groupby("project_id").s.max()
    k["delay_days"] = np.where(done, (k.actual_end_date - k.planned_end_date).dt.days, slip.reindex(k.index).clip(lower=0))
    k["delay_pct"] = 100 * k.delay_days / k.planned_duration_days
    k["schedule_status"] = pd.cut(k.delay_pct, [-np.inf, C.DELAY_MINOR, C.DELAY_MAJOR, C.DELAY_CRITICAL, np.inf],
                                  labels=["On time", "Minor delay", "Major delay", "Critical delay"]).astype(str)
    return k.reset_index()


def save_fig(fig, name):
    C.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(C.FIGURES / f"{name}.png")
    plt.close(fig)


def save_table(df, name, index=False):
    C.TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.TABLES / f"{name}.csv", index=index)


def update_metrics(section, values):
    """Collect headline numbers in reports/metrics.json so every document quotes the same figures."""
    path = C.REPORTS / "metrics.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[section] = values
    def plain(o):
        o = o.item() if hasattr(o, "item") else o
        return round(o, 4) if isinstance(o, float) else o
    path.write_text(json.dumps(data, indent=2, default=plain))


def bar_labels(ax, bars, fmt="{:.1f}", inside=False):
    for b in bars:
        w = b.get_width()
        ax.annotate(fmt.format(w), (w, b.get_y() + b.get_height() / 2), xytext=(4 if w >= 0 else -4, 0),
                    textcoords="offset points", va="center", ha="left" if w >= 0 else "right", color=TEXT_2, fontsize=8)


def low_otd_suppliers(t, threshold=0.6):
    po = t["fact_procurement"].dropna(subset=["delivery_date"])
    otd = po.groupby("supplier_id").is_on_time.mean()
    return set(otd[otd < threshold].index)


def delay_cost_per_day(t):
    """Rs per day a project loses when its completion slips: time-based overhead (60% of overhead
    budget, E02) + site equipment (half the equipment budget) spread over planned days, plus LD
    accrual of 0.5% of contract value per week (C08)."""
    p = t["dim_project"].set_index("project_id")
    b = t["fact_budget"].pivot_table(index="project_id", columns="cost_category_id", values="revised_budget_inr")
    time_cost = (0.6 * b[7] + 0.5 * b[4]) / p.planned_duration_days
    ld = C.LD_RATE_PER_WEEK * p.contract_value_inr / 7
    return pd.DataFrame({"time_cost_per_day": time_cost, "ld_per_day": ld, "delay_cost_per_day": time_cost + ld})


def project_drivers(t, k):
    """Observable operational drivers per project (no hidden simulation variables are used)."""
    po, ops, lab, ms = t["fact_procurement"], t["fact_operations"], t["fact_labor"], t["fact_milestones"]
    mat = t["dim_material"].set_index("material_id")
    po = po.assign(critical=po.material_id.map(mat.criticality_class).eq("A") | po.material_id.map(mat.is_steel_linked))
    bad = low_otd_suppliers(t)
    rec = po[po.grn_date.notna()]
    d = pd.DataFrame(index=k.project_id)
    d["low_otd_supplier_share"] = po.assign(v=po.line_value_inr * po.supplier_id.isin(bad)).groupby("project_id").v.sum() \
        / po.groupby("project_id").line_value_inr.sum()
    crit = rec[rec.critical]
    d["late_critical_share"] = (crit.grn_date > crit.need_by_date).groupby(crit.project_id).mean()
    a = rec[rec.material_id.map(mat.criticality_class).eq("A")]
    d["max_critical_lateness_days"] = (a.grn_date - a.need_by_date).dt.days.clip(lower=0).groupby(a.project_id).max()
    d["price_index"] = po.groupby("project_id").line_value_inr.sum() / (po.quantity * po.benchmark_unit_price_inr).groupby(po.project_id).sum()
    g = ops.groupby("project_id")
    d["works_mh_per_t"] = (g.regular_labour_hours.sum() + g.overtime_labour_hours.sum()) / g.actual_output_t.sum()
    d["works_constrained_share"] = g.capacity_constrained.mean()
    site = lab[lab.labour_type == "Site Erection"].groupby("project_id")
    d["site_labour_efficiency"] = site.earned_hours.sum() / (site.regular_hours.sum() + site.overtime_hours.sum() + site.idle_hours.sum())
    eng = ms[(ms.stage_id == 2) & ms.actual_end_date.notna()].set_index("project_id")
    d["engineering_slip_days"] = eng.end_delay_days - eng.start_delay_days
    d["new_energy"] = k.set_index("project_id").industry.isin(["Green Hydrogen", "Industrial Batteries", "Carbon Capture"]).astype(int)
    return d.reset_index()
