"""Render a static preview of the 4-page dashboard (reports/figures/dashboard_page*.png).

Run: python python/visualization/dashboard_preview.py   (after the analysis scripts)

This mirrors powerbi/dashboard_design.md so the design can be reviewed before the Power BI
build. It is a Python/Matplotlib rendering of the same numbers, not a Power BI screenshot.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from common import BLUE, GREY, ORANGE, STATUS, SURFACE, TEXT, TEXT_2, C, load, plt, save_fig  # noqa: E402

AQUA = "#1baf7a"
STATUS["Critical"] = "#d03b3b"


def tile(fig, rect, label, value, sub=""):
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#ffffff", edgecolor="#e2e1dc", linewidth=1))
    ax.text(0.06, 0.72, label, fontsize=8.5, color=TEXT_2, transform=ax.transAxes)
    ax.text(0.06, 0.32, value, fontsize=17, fontweight="bold", color=TEXT, transform=ax.transAxes)
    ax.text(0.06, 0.1, sub, fontsize=7.5, color=TEXT_2, transform=ax.transAxes)


def page(title, subtitle):
    fig = plt.figure(figsize=(16, 9))
    fig.text(0.02, 0.965, title, fontsize=18, fontweight="bold", color=TEXT)
    fig.text(0.02, 0.937, subtitle, fontsize=9.5, color=TEXT_2)
    return fig


def tiles(fig, items):
    w = 0.96 / len(items)
    for i, (lab, val, sub) in enumerate(items):
        tile(fig, [0.02 + i * w, 0.80, w - 0.008, 0.11], lab, val, sub)


def clean(ax, title):
    ax.set_title(title, fontsize=10.5)
    ax.tick_params(labelsize=8)


def main():
    t = load()
    m = json.loads((C.REPORTS / "metrics.json").read_text())
    T = lambda n: pd.read_csv(C.TABLES / f"{n}.csv")  # noqa: E731
    k = T("project_kpis")
    done = k[k.status == "Completed"]
    cp, pr, pd_, dl, roi = m["cost_profitability"], m["productivity"], m["procurement"], m["delays"], m["roi"]
    fy = t["dim_date"].set_index("date").fiscal_year

    # ---------------------------------------------------------------- Page 1: Executive overview
    fig = page("Executive overview", "Synthetic case study - fictional EPC company 'ProjectCo'. Completed-project financials unless stated.")
    net_savings = sum(v["net_annual_benefit"] for v in roi["base"].values() if v["net_annual_benefit"] > 0) / 1e7
    tiles(fig, [("Projects", f"{len(k)}", f"{len(done)} completed, {len(k) - len(done)} in progress"),
                ("Revenue", f"Rs {cp['completed_revenue_cr']:,.0f} Cr", "completed projects"),
                ("Actual cost", f"Rs {cp['completed_revenue_cr'] - cp['actual_profit_cr']:,.0f} Cr", ""),
                ("Actual profit", f"Rs {cp['actual_profit_cr']:,.0f} Cr", f"bid Rs {cp['estimated_profit_cr']:,.0f} Cr"),
                ("Margin", f"{cp['weighted_actual_margin_pct']:.1f}%", f"bid {cp['weighted_est_margin_pct']:.1f}%"),
                ("Cost overrun", f"{cp['cost_overrun_pct']:.1f}%", f"Rs {cp['cost_overrun_cr']:,.0f} Cr vs revised budget"),
                ("Delayed projects", f"{int((done.delay_days > 0).sum())}", f"of {len(done)}; LD Rs {dl['ld_cr']:.0f} Cr"),
                ("Potential savings", f"Rs {net_savings:.1f} Cr/yr", "net, 3 positive initiatives")])
    gs = fig.add_gridspec(2, 3, left=0.05, right=0.98, bottom=0.07, top=0.74, hspace=0.45, wspace=0.28)

    ax = fig.add_subplot(gs[0, 0])
    rev = t["fact_revenue"].assign(fy=t["fact_revenue"].invoice_date.map(fy)).groupby("fy").amount_inr.sum() / 1e7
    cost = t["fact_project_cost"].assign(fy=t["fact_project_cost"].posting_date.map(fy)).groupby("fy").amount_inr.sum() / 1e7
    x = np.arange(len(rev))
    ax.bar(x - 0.2, rev.values, 0.38, color=BLUE, label="Revenue billed")
    ax.bar(x + 0.2, cost.reindex(rev.index).values, 0.38, color=GREY, label="Cost incurred")
    ax.set_xticks(x, rev.index)
    ax.legend(fontsize=7.5)
    clean(ax, "Revenue vs cost by fiscal year (Rs Cr, all projects)")

    ax = fig.add_subplot(gs[0, 1])
    ind = T("profitability_by_industry").sort_values("revenue", ascending=False)
    y = np.arange(len(ind))
    ax.barh(y + 0.2, ind.est_profit / 1e7, 0.38, color=GREY, label="Estimated profit")
    ax.barh(y - 0.2, ind.profit / 1e7, 0.38, color=BLUE, label="Actual profit")
    ax.set_yticks(y, ind.industry, fontsize=7.5)
    ax.invert_yaxis()
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.legend(fontsize=7.5, loc="lower right")
    clean(ax, "Estimated vs actual profit by industry (Rs Cr)")

    ax = fig.add_subplot(gs[0, 2])
    risk = T("project_risk_scores")
    tiers = ["Low", "Medium", "High", "Critical"]
    comp_counts = risk[risk.status == "Completed"].risk_tier.value_counts().reindex(tiers).fillna(0)
    wip_counts = risk[risk.status == "In Progress"].risk_tier.value_counts().reindex(tiers).fillna(0)
    ax.bar(np.arange(4) - 0.2, comp_counts, 0.38, color=GREY, label="Completed")
    bars = ax.bar(np.arange(4) + 0.2, wip_counts, 0.38, color=[STATUS[s] for s in tiers], label="In progress")
    for b_, v in zip(bars, wip_counts):
        ax.annotate(f"{int(v)}", (b_.get_x() + b_.get_width() / 2, v), xytext=(0, 2), textcoords="offset points",
                    ha="center", fontsize=8, color=TEXT_2)
    ax.set_xticks(range(4), tiers)
    clean(ax, "Risk tiers: grey = completed, coloured = in progress")

    ax = fig.add_subplot(gs[1, :2])
    s = done.sort_values("cost_variance_pct", ascending=False)
    ax.bar(range(len(s)), s.cost_variance_pct, color=[STATUS[c] for c in s.cost_status], width=0.75)
    ax.axhline(5, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.axhline(10, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.set_xticks(range(len(s)), s.project_id, rotation=90, fontsize=5.5)
    handles = [plt.Rectangle((0, 0), 1, 1, color=STATUS[c]) for c in ["Critical", "Warning", "On budget", "Under budget"]]
    ax.legend(handles, ["Critical > 10%", "Warning 5-10%", "On budget", "Under budget"], fontsize=7.5, ncol=4,
              loc="upper center")
    clean(ax, "Cost variance % by completed project")

    ax = fig.add_subplot(gs[1, 2])
    ind2 = ind.sort_values("actual_margin_pct")
    yy = np.arange(len(ind2))
    ax.hlines(yy, ind2.actual_margin_pct, ind2.est_margin_pct, color=GREY, linewidth=2)
    ax.scatter(ind2.est_margin_pct, yy, color=GREY, s=30, label="Bid", zorder=3)
    ax.scatter(ind2.actual_margin_pct, yy, color=BLUE, s=30, label="Actual", zorder=3)
    ax.set_yticks(yy, ind2.industry, fontsize=7.5)
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.legend(fontsize=7.5, loc="lower right")
    clean(ax, "Industry margin: bid vs actual (%)")
    save_fig(fig, "dashboard_page1_executive_overview")

    # ---------------------------------------------------------------- Page 2: Project performance
    fig = page("Project performance", "Which projects are over budget or late, by how much, and where in the lifecycle the time is lost.")
    wip = k[k.status == "In Progress"]
    tiles(fig, [("Critical cost overruns", f"{cp['status_counts']['Critical']}", "completed, > 10% over budget"),
                ("Warning", f"{cp['status_counts']['Warning']}", "5-10% over budget"),
                ("Avg delay", f"{dl['avg_delay_days']:.0f} days", f"{dl['avg_delay_pct']:.1f}% of planned duration"),
                ("Loss-making", f"{cp['loss_making']}", "completed projects"),
                ("In progress, CPI < 1", f"{cp['wip_cpi_below_1']} of {cp['wip_count']}", "spending ahead of progress"),
                ("High / critical risk", f"{m['root_cause_risk']['wip_high_or_critical']}", "in-progress projects")])
    gs = fig.add_gridspec(2, 3, left=0.05, right=0.98, bottom=0.07, top=0.74, hspace=0.45, wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    ax.scatter(done.delay_pct, done.cost_variance_pct, color=[STATUS[c] for c in done.cost_status], s=30, edgecolor="white")
    ax.axhline(10, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.axvline(20, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.set(xlabel="Delay %", ylabel="Cost variance %")
    clean(ax, f"Cost variance vs delay (r = {dl['corr_delay_cost_variance']:.2f})")

    ax = fig.add_subplot(gs[0, 1])
    st = T("delay_by_stage").dropna(subset=["share_pct"])
    ax.bar(st.stage_name, st.avg_own_delay, color=[ORANGE if v == st.avg_own_delay.max() else BLUE for v in st.avg_own_delay])
    ax.tick_params(axis="x", rotation=30)
    clean(ax, "Average delay added by each stage (days)")

    ax = fig.add_subplot(gs[0, 2])
    pareto = T("delay_causes_pareto")
    ax.bar(range(len(pareto)), pareto.share_pct, color=BLUE)
    ax.plot(range(len(pareto)), pareto.cumulative_pct, color=ORANGE, marker="o", markersize=4)
    ax.set_xticks(range(len(pareto)), pareto.delay_cause, rotation=30, ha="right", fontsize=7)
    ax.set_ylim(0, 105)
    clean(ax, "Delay causes, Pareto (% of added days)")

    ax = fig.add_subplot(gs[1, :2])
    top = done.nlargest(12, "cost_variance")
    x = np.arange(len(top))
    ax.bar(x - 0.2, top.revised_budget / 1e7, 0.38, color=GREY, label="Revised budget")
    ax.bar(x + 0.2, top.final_cost / 1e7, 0.38, color=BLUE, label="Actual cost")
    ax.set_xticks(x, top.project_id, fontsize=7.5)
    ax.legend(fontsize=7.5)
    clean(ax, "Estimated vs actual cost - 12 largest overruns (Rs Cr)")

    ax = fig.add_subplot(gs[1, 2])
    ax.set_axis_off()
    tbl = wip.sort_values("cost_variance_pct", ascending=False).head(8)[["project_id", "percent_complete", "cpi", "cost_variance_pct", "delay_days"]]
    cell = [[r.project_id, f"{r.percent_complete:.0f}%", f"{r.cpi:.2f}", f"{r.cost_variance_pct:+.1f}%", f"{r.delay_days:.0f}"]
            for r in tbl.itertuples()]
    tb = ax.table(cellText=cell, colLabels=["Project", "% done", "CPI", "Fcst CV", "Slip d"], loc="center", cellLoc="center")
    tb.auto_set_font_size(False)
    tb.set_fontsize(8)
    tb.scale(1, 1.35)
    ax.set_title("In-progress watch list (forecast)", fontsize=10.5, loc="left")
    save_fig(fig, "dashboard_page2_project_performance")

    # ---------------------------------------------------------------- Page 3: Operations & productivity
    ws = pd.DataFrame(pr["works_scorecard"]).T
    fig = page("Operations and productivity", "Works fabrication: man-hours per tonne, machine time, downtime and bottlenecks.")
    tiles(fig, [("Labour productivity", f"{(ws.mh_per_tonne * ws.output_t).sum() / ws.output_t.sum():.1f} MH/t", "standard 30 MH/t"),
                ("Machine utilisation", f"{pd.DataFrame(pr['recent_time_split']).T.operating_hours.mean():.0f}%",
                 f"FY25-FY26 (all years {ws.utilisation_pct.mean():.0f}%)"),
                ("Downtime", f"{ws.downtime_pct.mean():.1f}%", f"Works-East {ws.loc['Works-East', 'downtime_pct']:.1f}%"),
                ("Output achievement", f"{ws.output_achievement_pct.mean():.0f}%", "actual / planned tonnes"),
                ("Defect rate", f"{(ws.defect_rate_pct * ws.output_t).sum() / ws.output_t.sum():.1f}%", "rework tonnes"),
                ("Chronic machines", f"{pr['chronic_machine_count']}", f"{pr['chronic_share_of_downtime_pct']:.0f}% of all downtime")])
    gs = fig.add_gridspec(2, 3, left=0.06, right=0.98, bottom=0.07, top=0.74, hspace=0.45, wspace=0.32)
    ax = fig.add_subplot(gs[0, 0])
    bars = ax.bar(ws.index, ws.mh_per_tonne, color=[ORANGE if i == "Works-East" else BLUE for i in ws.index], width=0.6)
    ax.axhline(30, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.annotate("standard", (2.3, 30), fontsize=7, color=TEXT_2)
    clean(ax, "Man-hours per tonne by works")
    ax = fig.add_subplot(gs[0, 1])
    split = pd.DataFrame(pr["recent_time_split"]).T
    left = np.zeros(len(split))
    for col, colour in (("operating_hours", BLUE), ("downtime_hours", ORANGE), ("idle_hours", "#d6d5d0")):
        ax.barh(split.index, split[col], left=left, color=colour, label=col.replace("_hours", "").title(), height=0.55)
        left += split[col].values
    ax.legend(fontsize=7, loc="lower right")
    clean(ax, "Machine time FY25-FY26 (% of available)")
    ax = fig.add_subplot(gs[0, 2])
    ax.bar(ws.index, ws.defect_rate_pct, color=[ORANGE if i == "Works-East" else BLUE for i in ws.index], width=0.6)
    clean(ax, "Defect (rework) rate % by works")
    ax = fig.add_subplot(gs[1, 0:2])
    md = T("machine_downtime_ranking").head(12)
    ax.bar(md.equipment_id, md.downtime_pct, color=[ORANGE if v > 10 else BLUE for v in md.downtime_pct])
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    clean(ax, "Machines with most downtime (% of available hours)")
    ax = fig.add_subplot(gs[1, 2])
    bt = T("bottleneck_work_centres")
    east = bt[bt.works_location_id == "LOC-W2"].sort_values("share_pct")
    ax.barh(east.process_type, east.share_pct, color=BLUE)
    clean(ax, "Works-East: which work centre limited output (%)")
    save_fig(fig, "dashboard_page3_operations")

    # ---------------------------------------------------------------- Page 4: Procurement & cost optimisation
    sc = T("supplier_scorecard")
    fig = page("Procurement and cost optimisation", "Supplier reliability vs price, the true cost of late deliveries, and the improvement business cases.")
    tiles(fig, [("Supplier on-time %", f"{pd_['overall_otd_pct']:.0f}%", f"critical items {pd_['critical_otd_pct']:.0f}%"),
                ("Procurement spend", f"Rs {pd_['total_spend_cr']:,.0f} Cr", f"{len(t['fact_procurement']):,} PO lines"),
                ("Avg lead time", f"{t['fact_procurement'].lead_time_days.mean():.0f} days", "PO to goods receipt"),
                ("Late deliveries", f"{int((t['fact_procurement'].is_on_time == False).sum()):,}", "after promised date"),  # noqa: E712
                ("Low-OTD suppliers", f"{pd_['low_otd_supplier_count']}", f"price index {pd_['low_otd_avg_price_index']:.2f}"),
                ("Procurement cycle", f"{m['process']['as_is_internal_days']:.0f} -> {m['process']['to_be_internal_days']:.0f} d", "internal days, As-Is -> To-Be")])
    gs = fig.add_gridspec(2, 3, left=0.08, right=0.98, bottom=0.07, top=0.74, hspace=0.45, wspace=0.42)
    ax = fig.add_subplot(gs[0, 0])
    ax.scatter(sc.price_index, sc.otd_pct, s=np.clip(sc.spend_cr * 3, 10, 200), color=BLUE, alpha=0.7, edgecolor="white")
    ax.axvline(1, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.axhline(70, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.set(xlabel="Price index (1 = market)", ylabel="OTD %")
    clean(ax, "Supplier price vs on-time delivery")
    ax = fig.add_subplot(gs[0, 1])
    tco = T("supplier_total_cost_of_ownership").set_index("supplier_id")
    tco = tco[tco.price_saving_lakh > 0].sort_values("net_benefit_lakh").head(8)
    yy = np.arange(len(tco))
    ax.barh(yy + 0.2, tco.price_saving_lakh, 0.38, color=BLUE, label="Price saving")
    ax.barh(yy - 0.2, -tco.lateness_cost_lakh, 0.38, color=ORANGE, label="Lateness cost")
    ax.set_yticks(yy, tco.index, fontsize=7.5)
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.legend(fontsize=7)
    clean(ax, "Cheaper suppliers: saving vs lateness cost (Rs L)")
    ax = fig.add_subplot(gs[0, 2])
    po = t["fact_procurement"]
    q = po.assign(q=po.po_date.dt.to_period("Q")).groupby("q").agg(otd=("is_on_time", "mean"), n=("is_on_time", "count"))
    q = q[q.n >= 30]                                  # skip quarters with too few deliveries to judge
    ax.plot(q.index.astype(str), 100 * q.otd, color=BLUE, linewidth=2)
    ax.set_xticks(range(0, len(q), 3), q.index.astype(str)[::3], rotation=45, fontsize=7)
    clean(ax, "On-time delivery % by PO quarter")
    ax = fig.add_subplot(gs[1, 0])
    vol = T("material_price_volatility").head(8).iloc[::-1]
    ax.barh(vol.material_group, vol.coeff_variation, color=BLUE)
    ax.tick_params(axis="y", labelsize=7)
    clean(ax, "Material price volatility (coeff. of variation)")
    ax = fig.add_subplot(gs[1, 1:])
    r = T("roi_initiatives").sort_values("npv_5yr")
    short = {"Design-freeze stage gate": "Design-freeze gate", "Digital procurement workflow": "Digital procurement",
             "Predictive maintenance on chronic machines": "Predictive maintenance",
             "Critical-item supplier switch": "Blanket supplier switch"}
    bars = ax.barh(r.initiative.map(short), r.npv_5yr / 1e7, color=[BLUE if v > 0 else ORANGE for v in r.npv_5yr], height=0.55)
    for b_, row in zip(bars, r.itertuples()):
        lab = f"NPV Rs {row.npv_5yr / 1e7:.1f} Cr | payback {row.payback_years:.1f} y" if np.isfinite(row.payback_years) else \
            f"NPV Rs {row.npv_5yr / 1e7:.1f} Cr | never pays back"
        ax.annotate(lab, (max(b_.get_width(), 0), b_.get_y() + b_.get_height() / 2), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8, color=TEXT_2)
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.set_xlim(r.npv_5yr.min() / 1e7 * 1.15, r.npv_5yr.max() / 1e7 * 1.9)
    clean(ax, "Improvement initiatives: 5-year NPV (Rs Cr, base case)")
    save_fig(fig, "dashboard_page4_procurement_cost")
    print("Wrote 4 dashboard preview pages to reports/figures/")


if __name__ == "__main__":
    main()
