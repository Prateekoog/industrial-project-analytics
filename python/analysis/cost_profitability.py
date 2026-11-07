"""Cost variance and profitability analysis (Phases 10-11).

Run: python python/analysis/cost_profitability.py
"""
import numpy as np
import pandas as pd

from common import (BLUE, GREY, ORANGE, STATUS, TEXT_2, bar_labels, cr, load, plt, project_kpis, save_fig,
                    save_table, update_metrics)


def category_variance(t, project_ids):
    b = t["fact_budget"][t["fact_budget"].project_id.isin(project_ids)]
    a = t["fact_project_cost"].groupby(["project_id", "cost_category_id"]).amount_inr.sum().rename("actual")
    m = b.set_index(["project_id", "cost_category_id"]).join(a).fillna({"actual": 0}).reset_index()
    m = m.merge(t["dim_cost_category"][["cost_category_id", "cost_category"]])
    g = m.groupby("cost_category")[["revised_budget_inr", "actual"]].sum()
    g["variance"] = g.actual - g.revised_budget_inr
    g["variance_pct"] = 100 * g.variance / g.revised_budget_inr
    g["share_of_overrun_pct"] = 100 * g.variance / g.variance.sum()
    return g.sort_values("variance", ascending=False), m


def main():
    t = load()
    k = project_kpis(t)
    done = k[k.status == "Completed"].copy()
    wip = k[k.status == "In Progress"].copy()
    save_table(k, "project_kpis")

    # --- Cost variance status -----------------------------------------------------------
    status = done.cost_status.value_counts().reindex(["Under budget", "On budget", "Warning", "Critical"]).fillna(0)
    cat, detail = category_variance(t, done.project_id)
    save_table(cat.reset_index(), "cost_variance_by_category")

    fig, ax = plt.subplots(figsize=(7, 3.8))
    c = cat.sort_values("variance")
    bars = ax.barh(c.index, cr(c.variance), color=[BLUE if v >= 0 else GREY for v in c.variance], height=0.6)
    bar_labels(ax, bars, "Rs {:.1f} Cr")
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.set(title="Where the Rs {:.0f} Cr overrun came from (completed projects)".format(cr(cat.variance.sum())),
           xlabel="Actual minus revised budget (Rs crore)")
    ax.grid(axis="y", visible=False)
    save_fig(fig, "cost_overrun_by_category")

    # Cost variance % per project, coloured by status band (H01)
    fig, ax = plt.subplots(figsize=(10, 3.8))
    s = done.sort_values("cost_variance_pct")
    ax.bar(range(len(s)), s.cost_variance_pct, color=[STATUS[x] for x in s.cost_status], width=0.75)
    for y, lab in ((5, "Warning 5%"), (10, "Critical 10%"), (-2, "Under budget -2%")):
        ax.axhline(y, color=TEXT_2, linestyle="--", linewidth=0.8)
        ax.annotate(lab, (0, y), xytext=(2, 3), textcoords="offset points", fontsize=8, color=TEXT_2)
    ax.set(title="Cost variance by completed project (bars coloured by status band)", ylabel="Cost variance %", xticks=[])
    handles = [plt.Rectangle((0, 0), 1, 1, color=STATUS[x]) for x in status.index]
    ax.legend(handles, [f"{x} ({int(n)})" for x, n in status.items()], loc="upper left", ncol=4, fontsize=8)
    save_fig(fig, "cost_variance_by_project")

    # --- Profit bridge: estimated (bid) profit -> actual profit ---------------------------
    est = done.estimated_profit.sum()
    co_profit = (done.co_revenue - done.change_order_budget).sum()
    pvc = done.pvc_revenue.sum()
    overrun = done.cost_variance.sum()
    ld = done.ld_deducted.sum()
    actual = done.final_profit.sum()
    assert abs(est + co_profit + pvc - overrun - ld - actual) < 10, "profit bridge does not reconcile"
    steps = [("Bid profit", est), ("Change-order profit", co_profit), ("Price variation", pvc),
             ("Cost overrun", -overrun), ("Liquidated damages", -ld)]
    fig, ax = plt.subplots(figsize=(8, 4))
    run = 0
    for i, (lab, v) in enumerate(steps):
        bottom = 0 if i == 0 else run + min(v, 0)
        ax.bar(i, cr(abs(v)), bottom=cr(bottom), color=BLUE if i == 0 else (AQUA_ if v >= 0 else ORANGE), width=0.6)
        ax.annotate(f"{cr(v):+,.0f}" if i else f"{cr(v):,.0f}", (i, cr(bottom + abs(v))), xytext=(0, 3),
                    textcoords="offset points", ha="center", fontsize=8, color=TEXT_2)
        run = v if i == 0 else run + v
    ax.bar(len(steps), cr(actual), color=BLUE, width=0.6)
    ax.annotate(f"{cr(actual):,.0f}", (len(steps), cr(actual)), xytext=(0, 3), textcoords="offset points",
                ha="center", fontsize=8, color=TEXT_2)
    ax.set_xticks(range(len(steps) + 1), [s[0] for s in steps] + ["Actual profit"], rotation=15)
    ax.set(title="Profit bridge, completed projects (Rs crore)", ylabel="Rs crore")
    ax.grid(axis="x", visible=False)
    save_fig(fig, "profit_bridge")

    # --- Estimated vs actual margin per project --------------------------------------------
    fig, ax = plt.subplots(figsize=(5.8, 5))
    ax.scatter(done.estimated_margin_pct, done.final_margin_pct, s=np.clip(cr(done.contract_value_inr), 12, 220),
               color=BLUE, alpha=0.7, edgecolor="white", linewidth=1)
    lim = [min(done.final_margin_pct.min(), 0) - 2, done.estimated_margin_pct.max() + 2]
    ax.plot(lim, lim, color=TEXT_2, linestyle="--", linewidth=1)
    ax.annotate("on the line = margin delivered as bid", (lim[1] - 1, lim[1] - 1), ha="right", va="bottom",
                fontsize=8, color=TEXT_2)
    for _, r in done.nsmallest(4, "final_margin_pct").iterrows():
        ax.annotate(r.project_id, (r.estimated_margin_pct, r.final_margin_pct), xytext=(5, -3),
                    textcoords="offset points", fontsize=7, color=TEXT_2)
    ax.axhline(0, color=GREY, linewidth=0.8)
    ax.set(title="Bid margin vs actual margin (bubble = contract size)", xlabel="Estimated (bid) margin %",
           ylabel="Actual margin %")
    save_fig(fig, "margin_estimated_vs_actual")

    # --- Industry profitability ------------------------------------------------------------
    ind = done.groupby("industry").agg(projects=("project_id", "size"), revenue=("final_revenue", "sum"),
                                       est_profit=("estimated_profit", "sum"), cv=("contract_value_inr", "sum"),
                                       profit=("final_profit", "sum"), avg_cv_pct=("cost_variance_pct", "mean"))
    ind["est_margin_pct"] = 100 * ind.est_profit / ind.cv
    ind["actual_margin_pct"] = 100 * ind.profit / ind.revenue
    ind["margin_lost_pp"] = ind.est_margin_pct - ind.actual_margin_pct
    ind = ind.sort_values("actual_margin_pct")
    save_table(ind.reset_index(), "profitability_by_industry")
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    y = np.arange(len(ind))
    ax.hlines(y, ind.actual_margin_pct, ind.est_margin_pct, color=GREY, linewidth=2)
    ax.scatter(ind.est_margin_pct, y, color=GREY, s=55, label="Bid margin", zorder=3)
    ax.scatter(ind.actual_margin_pct, y, color=BLUE, s=55, label="Actual margin", zorder=3)
    ax.set_yticks(y, [f"{i} ({n})" for i, n in zip(ind.index, ind.projects)])
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.set(title="Margin bid vs delivered, by industry (completed projects)", xlabel="Margin %")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", visible=False)
    save_fig(fig, "margin_by_industry")

    # --- In-progress projects: earned value forecast ----------------------------------------
    wip_tbl = wip[["project_id", "project_name", "industry", "percent_complete", "revised_budget", "earned_value",
                   "actual_cost_to_date", "cpi", "final_cost", "cost_variance_pct", "estimated_margin_pct",
                   "final_margin_pct", "cost_status"]].sort_values("cpi")
    save_table(wip_tbl, "in_progress_forecast")

    # Worst project: cost-driver decomposition
    worst = done.loc[done.cost_variance_pct.idxmax(), "project_id"]
    w = detail[detail.project_id == worst].assign(variance=lambda x: x.actual - x.revised_budget_inr)
    w["contribution_pct"] = 100 * w.variance / w.variance.sum()
    save_table(w.sort_values("variance", ascending=False), "worst_project_decomposition")

    pvc_cmp = done.groupby("has_price_variation_clause").agg(projects=("project_id", "size"),
                                                        avg_cv_pct=("cost_variance_pct", "mean"),
                                                        pvc_cr=("pvc_revenue", lambda x: cr(x.sum())),
                                                        margin_lost_pp=("margin_deterioration_pp", "mean"))
    save_table(pvc_cmp.reset_index(), "pvc_comparison")

    metrics = {
        "completed_revenue_cr": cr(done.final_revenue.sum()), "completed_contract_cr": cr(done.contract_value_inr.sum()),
        "estimated_profit_cr": cr(est), "actual_profit_cr": cr(actual), "profit_lost_cr": cr(est - actual),
        "profit_lost_pct_of_plan": 100 * (est - actual) / est,
        "weighted_est_margin_pct": 100 * est / done.contract_value_inr.sum(),
        "weighted_actual_margin_pct": 100 * actual / done.final_revenue.sum(),
        "cost_overrun_cr": cr(overrun), "cost_overrun_pct": 100 * overrun / done.revised_budget.sum(),
        "ld_cr": cr(ld), "co_profit_cr": cr(co_profit), "pvc_cr": cr(pvc),
        "status_counts": status.astype(int).to_dict(), "loss_making": int((done.final_profit < 0).sum()),
        "below_5pct_margin": int((done.final_margin_pct < 5).sum()),
        "top_overrun_category": cat.index[0], "top_overrun_category_cr": cr(cat.variance.iloc[0]),
        "top_overrun_category_share_pct": cat.share_of_overrun_pct.iloc[0],
        "top2_overrun_share_pct": cat.share_of_overrun_pct.iloc[:2].sum(),
        "category_variance_pct": cat.variance_pct.round(1).to_dict(),
        "category_variance_cr": (cat.variance / 1e7).round(1).to_dict(),
        "worst_project": worst, "worst_project_cv_pct": done.cost_variance_pct.max(),
        "worst_project_top_driver": w.sort_values("variance", ascending=False).cost_category.iloc[0],
        "worst_project_top_driver_pct": w.contribution_pct.max(),
        "best_industry_margin": ind.index[-1], "worst_industry_margin": ind.index[0],
        "industry_margin": ind[["est_margin_pct", "actual_margin_pct"]].round(1).to_dict("index"),
        "new_energy_margin_lost_pp": done[done.industry.isin(["Green Hydrogen", "Industrial Batteries", "Carbon Capture"])].margin_deterioration_pp.mean(),
        "mature_margin_lost_pp": done[~done.industry.isin(["Green Hydrogen", "Industrial Batteries", "Carbon Capture"])].margin_deterioration_pp.mean(),
        "wip_count": len(wip), "wip_cpi_below_1": int((wip.cpi < 1).sum()),
        "wip_forecast_critical": int((wip.cost_status == "Critical").sum()),
        "wip_forecast_overrun_cr": cr(wip.cost_variance.clip(lower=0).sum()),
    }
    update_metrics("cost_profitability", metrics)
    print(f"Profit: bid Rs {cr(est):.0f} Cr -> actual Rs {cr(actual):.0f} Cr "
          f"({metrics['weighted_est_margin_pct']:.1f}% -> {metrics['weighted_actual_margin_pct']:.1f}%)")
    print(f"Overrun Rs {cr(overrun):.0f} Cr ({metrics['cost_overrun_pct']:.1f}%), LD Rs {cr(ld):.0f} Cr; status {status.to_dict()}")
    print(cat[["variance_pct", "share_of_overrun_pct"]].round(1).to_string())


AQUA_ = "#1baf7a"

if __name__ == "__main__":
    main()
