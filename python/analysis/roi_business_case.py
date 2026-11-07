"""Business cases, payback and ROI for improvement initiatives (Phase 17).

Run: python python/analysis/roi_business_case.py

Definitions (docs/ROI_ANALYSIS.md):
  Net annual benefit = annual savings - annual running cost
  Payback (years)    = upfront investment / net annual benefit       -> how fast the cash comes back
  3-year ROI %       = (3-yr savings - 3-yr total cost) / 3-yr total cost x 100, where total cost =
                       investment + 3 x running cost                               -> how much it returns
  5-year NPV         = -investment + sum over 5 years of net benefit / (1 + 12%)^year (C12)
Payback and ROI answer different questions: a project can pay back fast and still be small.

Every benefit is computed from this dataset. Every cost and effectiveness figure is an assumption,
listed in ASSUMPTIONS below, and tested at low / base / high values.
"""
import json

import numpy as np
import pandas as pd

from common import (BLUE, GREY, ORANGE, TEXT_2, C, delay_cost_per_day, load, plt, project_drivers, project_kpis,
                    save_fig, save_table, update_metrics)

ASSUMPTIONS = {
    # Predictive maintenance (vibration / thermal sensors + CMMS on chronic machines)
    "pm_sensor_cost_per_machine": 5.0e5, "pm_platform_cost": 25e5, "pm_running_cost": 10e5,
    "pm_downtime_reduction": {"low": 0.15, "base": 0.35, "high": 0.50},
    "pm_repair_cost_per_event": 25_000, "pm_crew_per_machine": 3, "pm_idle_share": 0.6,
    # Digital procurement workflow (e-approval, e-RFQ, supplier portal, mobile GRN)
    "dp_implementation_cost": 70e5, "dp_running_cost": 20e5, "dp_buyer_hours_saved_per_line": 1.5,
    "dp_buyer_rate": 1000, "dp_target_achievement": {"low": 0.5, "base": 0.8, "high": 1.0},
    # Critical-item supplier switch (only where lateness cost exceeds the price saving)
    "ss_qualification_cost": 15e5, "ss_effectiveness": {"low": 0.5, "base": 0.75, "high": 0.9},
    # Design-freeze stage gate (independent design review before major procurement)
    "dg_setup_cost": 20e5, "dg_review_team_cost": 120e5, "dg_gate_days_per_project": 7, "dg_confounding_haircut": 0.5,
    "dg_prevention": {"low": 0.10, "base": 0.25, "high": 0.40},
}
YEARS = ["FY25", "FY26"]           # run-rate window: the last two fiscal years


def finance(investment, annual_saving, running):
    net = annual_saving - running
    payback = investment / net if net > 0 else np.inf
    total_cost = investment + 3 * running
    roi3 = 100 * (3 * annual_saving - total_cost) / total_cost
    npv5 = -investment + sum(net / (1 + C.DISCOUNT_RATE) ** y for y in range(1, 6))
    return dict(investment=investment, annual_saving=annual_saving, running_cost=running, net_annual_benefit=net,
                payback_years=payback, roi_3yr_pct=roi3, npv_5yr=npv5)


def predictive_maintenance(t, level):
    a = ASSUMPTIONS
    eq = t["fact_equipment"].merge(t["dim_equipment"], on="equipment_id")
    fy = t["dim_date"].set_index("date").fiscal_year
    eq["fy"] = eq.log_date.map(fy)
    m = eq.groupby("equipment_id").agg(down=("downtime_hours", "sum"), avail=("available_hours", "sum"))
    targets = m[100 * m.down / m.avail > 10].index                          # chronic machines (> 10% downtime)
    r = eq[eq.equipment_id.isin(targets) & eq.fy.isin(YEARS)]
    hours = r.downtime_hours.sum() / len(YEARS)
    events = (r.downtime_hours > 0).sum() / len(YEARS)
    ops = t["fact_operations"]
    rate = ops.labour_cost_inr.sum() / (ops.regular_labour_hours.sum() + ops.overtime_labour_hours.sum())
    constrained = ops.capacity_constrained.mean()
    lost_t_per_hour = r.rated_tonnes_per_hour.mean()
    value_per_hour = (a["pm_crew_per_machine"] * a["pm_idle_share"] * rate       # idle crew
                      + constrained * lost_t_per_hour * C.WORKS_STD_MH_PER_TONNE * rate * (C.OVERTIME_MULTIPLIER - 1))  # overtime premium to recover lost output
    red = a["pm_downtime_reduction"][level]
    saving = red * (hours * value_per_hour + events * a["pm_repair_cost_per_event"])
    invest = a["pm_sensor_cost_per_machine"] * len(targets) + a["pm_platform_cost"]
    info = dict(target_machines=list(targets), downtime_hours_per_year=hours, breakdowns_per_year=events,
                value_per_downtime_hour=value_per_hour, reduction=red)
    return finance(invest, saving, a["pm_running_cost"]), info


def digital_procurement(metrics, level):
    a, p = ASSUMPTIONS, metrics["process"]
    ach = a["dp_target_achievement"][level]
    saving = ach * (p["annual_delay_value_cr"] * 1e7
                    + p["po_lines_per_year"] * a["dp_buyer_hours_saved_per_line"] * a["dp_buyer_rate"])
    info = dict(internal_days_saved=p["internal_days_saved"] * ach, achievement=ach)
    return finance(a["dp_implementation_cost"], saving, a["dp_running_cost"]), info


def supplier_switch(t, level):
    a = ASSUMPTIONS
    tco = pd.read_csv(C.TABLES / "supplier_total_cost_of_ownership.csv").set_index("supplier_id")
    sc = pd.read_csv(C.TABLES / "supplier_scorecard.csv").set_index("supplier_id")
    # Only suppliers that are cheaper than market AND whose lateness cost exceeds that saving
    losers = tco[(tco.price_saving_lakh > 0) & (tco.net_benefit_lakh < 0)]
    years = t["fact_procurement"].po_date.dt.year.nunique()
    premium, avoided = 0.0, 0.0
    for sid, r in losers.iterrows():
        grp = sc[sc.material_group == r.material_group]
        best = grp.otd_pct.idxmax()
        premium += (grp.at[best, "price_index"] - r.price_index) / r.price_index * r.critical_spend_cr * 1e7 / years
        avoided += r.lateness_cost_lakh * 1e5 / years
    eff = a["ss_effectiveness"][level]
    info = dict(suppliers_switched=list(losers.index), annual_price_premium=premium, annual_lateness_cost=avoided)
    return finance(a["ss_qualification_cost"], eff * avoided, premium), info


def design_gate(t, level):
    a = ASSUMPTIONS
    k = project_kpis(t)
    d = project_drivers(t, k).merge(k, on="project_id")
    done = d[d.status == "Completed"]
    hit = done.engineering_slip_days > 30
    excess_pp = done[hit].margin_deterioration_pp.mean() - done[~hit].margin_deterioration_pp.mean()
    fy = t["dim_date"].set_index("date").fiscal_year
    rev_per_year = done[hit].final_revenue.groupby(done[hit].actual_end_date.map(fy)).sum().reindex(YEARS).fillna(0).mean()
    prevent = a["dg_prevention"][level]
    saving = prevent * a["dg_confounding_haircut"] * excess_pp / 100 * rev_per_year
    # The gate itself adds review days to every new project's engineering: time-based cost, not LD
    starts = k.planned_start_date.map(fy).value_counts().reindex(YEARS).fillna(0).mean()
    gate_cost = starts * a["dg_gate_days_per_project"] * delay_cost_per_day(t).time_cost_per_day.mean()
    info = dict(excess_margin_lost_pp=excess_pp, affected_revenue_per_year=rev_per_year, prevention=prevent,
                affected_share_pct=100 * hit.mean(), gate_time_cost_per_year=gate_cost, projects_started_per_year=starts)
    return finance(a["dg_setup_cost"], saving, a["dg_review_team_cost"] + gate_cost), info


def main():
    t = load()
    metrics = json.loads((C.REPORTS / "metrics.json").read_text())
    builders = {
        "Predictive maintenance on chronic machines": lambda lv: predictive_maintenance(t, lv),
        "Digital procurement workflow": lambda lv: digital_procurement(metrics, lv),
        "Critical-item supplier switch": lambda lv: supplier_switch(t, lv),
        "Design-freeze stage gate": lambda lv: design_gate(t, lv),
    }
    rows, infos = [], {}
    for name, build in builders.items():
        for lv in ("low", "base", "high"):
            fin, info = build(lv)
            rows.append(dict(initiative=name, scenario=lv, **fin))
            if lv == "base":
                infos[name] = info
    res = pd.DataFrame(rows)
    save_table(res.round(2), "roi_scenarios")
    base = res[res.scenario == "base"].set_index("initiative")
    base["rank_npv"] = base.npv_5yr.rank(ascending=False).astype(int)
    save_table(base.reset_index().round(2), "roi_initiatives")
    pd.Series({k: json.dumps(v) if isinstance(v, dict) else v for k, v in ASSUMPTIONS.items()}).rename("value") \
        .to_csv(C.TABLES / "roi_assumptions.csv")

    # Chart: 5-year NPV with low-high range
    rng = res.pivot(index="initiative", columns="scenario", values="npv_5yr").reindex(base.sort_values("npv_5yr").index)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = np.arange(len(rng))
    ax.barh(y, rng["base"] / 1e7, color=BLUE, height=0.5)
    ax.hlines(y, rng["low"] / 1e7, rng["high"] / 1e7, color=TEXT_2, linewidth=1.5)
    for i, (lo, b, hi) in enumerate(zip(rng["low"], rng["base"], rng["high"])):
        ax.annotate(f"Rs {b / 1e7:.1f} Cr (payback {base.loc[rng.index[i], 'payback_years']:.1f} y)",
                    (max(hi, b) / 1e7, i), xytext=(5, 0), textcoords="offset points", va="center", fontsize=8, color=TEXT_2)
    ax.set_yticks(y, rng.index)
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.set(title="5-year NPV of improvement initiatives (bar = base case, line = low-high range)", xlabel="Rs crore")
    ax.set_xlim(right=max(rng["high"].max() / 1e7 * 1.6, 1))
    ax.grid(axis="y", visible=False)
    save_fig(fig, "roi_npv_initiatives")

    update_metrics("roi", {
        "base": base[["investment", "annual_saving", "running_cost", "net_annual_benefit", "payback_years",
                      "roi_3yr_pct", "npv_5yr", "rank_npv"]].round(2).to_dict("index"),
        "scenarios": res.pivot(index="initiative", columns="scenario", values="npv_5yr").round(0).to_dict("index"),
        "details": infos, "assumptions": ASSUMPTIONS,
        "total_net_annual_benefit_cr": base.net_annual_benefit.clip(lower=0).sum() / 1e7,
    })
    show = base[["investment", "net_annual_benefit", "payback_years", "roi_3yr_pct", "npv_5yr"]].copy()
    show[["investment", "net_annual_benefit", "npv_5yr"]] /= 1e7
    print(show.round(2).to_string())
    print(json.dumps(infos, indent=1, default=lambda o: round(float(o), 2) if not isinstance(o, list) else o)[:1500])


if __name__ == "__main__":
    main()
