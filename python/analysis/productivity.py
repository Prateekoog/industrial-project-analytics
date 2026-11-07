"""Works productivity, machine utilisation, downtime and bottlenecks (Phase 12).

Run: python python/analysis/productivity.py

Definitions used (docs/KPI_DEFINITIONS.md):
  Output         - tonnes fabricated
  Capacity       - tonnes the works COULD make with all machines available
  Utilisation    - operating hours / available hours (how much of the available time machines worked)
  Efficiency     - standard hours / actual hours (how well the time that was worked was used)
  Productivity   - output per unit of input, here man-hours per tonne (MH/t)
"""
import numpy as np
import pandas as pd

from common import BLUE, GREY, ORANGE, TEXT_2, bar_labels, load, plt, save_fig, save_table, update_metrics
import config as C


def main():
    t = load()
    ops, eq = t["fact_operations"], t["fact_equipment"]
    dim_eq, wc, loc = t["dim_equipment"], t["dim_work_centre"], t["dim_location"]
    works_name = dict(zip(loc.location_id, loc.location_name))
    eq = eq.merge(dim_eq[["equipment_id", "equipment_name", "work_centre_id", "works_location_id", "commission_year",
                          "machine_hour_rate_inr"]], on="equipment_id")
    eq = eq.merge(t["dim_date"][["date", "fiscal_year"]], left_on="log_date", right_on="date")

    # --- Works scorecard -----------------------------------------------------------------
    g = ops.groupby("works_location_id")
    hours = g.regular_labour_hours.sum() + g.overtime_labour_hours.sum()
    score = pd.DataFrame({
        "output_t": g.actual_output_t.sum(),
        "mh_per_tonne": hours / g.actual_output_t.sum(),
        "overtime_pct": 100 * g.overtime_labour_hours.sum() / hours,
        "defect_rate_pct": 100 * g.rework_t.sum() / g.actual_output_t.sum(),
        "output_achievement_pct": 100 * g.actual_output_t.sum() / g.planned_output_t.sum(),
        "conversion_cost_per_t": (g.labour_cost_inr.sum() + g.machine_cost_inr.sum() + g.energy_cost_inr.sum()) / g.actual_output_t.sum(),
        "labour_cost_per_t": g.labour_cost_inr.sum() / g.actual_output_t.sum(),
        "constrained_days_pct": 100 * g.capacity_constrained.mean(),
    })
    e = eq.groupby("works_location_id")
    score["utilisation_pct"] = 100 * e.operating_hours.sum() / e.available_hours.sum()
    score["downtime_pct"] = 100 * e.downtime_hours.sum() / e.available_hours.sum()
    score["idle_pct"] = 100 * e.idle_hours.sum() / e.available_hours.sum()
    score["labour_efficiency_pct"] = 100 * C.WORKS_STD_MH_PER_TONNE / score.mh_per_tonne
    score.index = score.index.map(works_name)
    save_table(score.reset_index().rename(columns={"works_location_id": "works"}), "works_scorecard")

    # Time split of available machine hours, recent two fiscal years (FY25-FY26)
    recent = eq[eq.fiscal_year.isin(["FY25", "FY26"])]
    split = recent.groupby("works_location_id")[["operating_hours", "downtime_hours", "idle_hours"]].sum()
    split = 100 * split.div(split.sum(axis=1), axis=0)
    split.index = split.index.map(works_name)
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    left = np.zeros(len(split))
    for col, colour, lab in (("operating_hours", BLUE, "Operating"), ("downtime_hours", ORANGE, "Downtime"),
                             ("idle_hours", "#d6d5d0", "Idle (no work loaded)")):
        bars = ax.barh(split.index, split[col], left=left, color=colour, label=lab, height=0.55, edgecolor=C_SURFACE, linewidth=2)
        for b, v in zip(bars, split[col]):
            if v > 4:
                ax.annotate(f"{v:.0f}%", (b.get_x() + b.get_width() / 2, b.get_y() + b.get_height() / 2), ha="center",
                            va="center", fontsize=8, color="white" if colour != "#d6d5d0" else TEXT_2)
        left += split[col].values
    ax.set(title="How machine time was spent, FY25-FY26 (% of available hours)", xlim=(0, 100))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8)
    ax.grid(False)
    save_fig(fig, "machine_time_split_by_works")

    by_fy = eq.groupby(["works_location_id", "fiscal_year"]).agg(op=("operating_hours", "sum"), dt=("downtime_hours", "sum"),
                                                                  av=("available_hours", "sum"))
    by_fy["utilisation_pct"] = 100 * by_fy.op / by_fy.av
    by_fy["downtime_pct"] = 100 * by_fy.dt / by_fy.av
    save_table(by_fy[["utilisation_pct", "downtime_pct"]].round(1).reset_index(), "utilisation_by_works_fy")

    # --- Machines: who breaks down the most --------------------------------------------------
    m = eq.groupby(["equipment_id", "equipment_name", "work_centre_id", "works_location_id", "commission_year",
                    "machine_hour_rate_inr"]).agg(down=("downtime_hours", "sum"), avail=("available_hours", "sum"),
                                                  events=("downtime_hours", lambda x: (x > 0).sum())).reset_index()
    m["downtime_pct"] = 100 * m.down / m.avail
    m = m.sort_values("downtime_pct", ascending=False)
    save_table(m, "machine_downtime_ranking")
    top = m.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars = ax.barh(top.equipment_id + "  " + top.equipment_name.str.replace(r" #\d", "", regex=True), top.downtime_pct,
                   color=[ORANGE if v > 10 else BLUE for v in top.downtime_pct], height=0.6)
    bar_labels(ax, bars, "{:.1f}%")
    ax.axvline(m.downtime_pct.median(), color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.annotate(f"median machine {m.downtime_pct.median():.1f}%", (m.downtime_pct.median(), -0.6), xytext=(3, 0),
                textcoords="offset points", fontsize=8, color=TEXT_2)
    ax.set(title="Ten machines with the most unplanned downtime", xlabel="Downtime % of available hours")
    ax.grid(axis="y", visible=False)
    save_fig(fig, "machine_downtime_top10")

    # --- Bottlenecks -----------------------------------------------------------------------
    cons = ops[ops.capacity_constrained].merge(wc[["work_centre_id", "process_type"]], left_on="bottleneck_work_centre_id",
                                               right_on="work_centre_id")
    bott = cons.groupby(["works_location_id", "process_type"]).size().rename("constrained_project_days").reset_index()
    bott["share_pct"] = 100 * bott.constrained_project_days / bott.groupby("works_location_id").constrained_project_days.transform("sum")
    bott["works"] = bott.works_location_id.map(works_name)
    save_table(bott.sort_values(["works", "share_pct"], ascending=[True, False]), "bottleneck_work_centres")

    # --- Downtime -> productivity: monthly works-level relationship ------------------------
    ops_m = ops.assign(month=ops.production_date.dt.to_period("M")).groupby(["works_location_id", "month"]).agg(
        hours=("regular_labour_hours", "sum"), ot=("overtime_labour_hours", "sum"), out=("actual_output_t", "sum"),
        cost=("labour_cost_inr", "sum"))
    eq_m = eq.assign(month=eq.log_date.dt.to_period("M")).groupby(["works_location_id", "month"]).agg(
        dt=("downtime_hours", "sum"), av=("available_hours", "sum"))
    rel = ops_m.join(eq_m).dropna()
    rel = rel[rel.out > 200]
    rel["mh_per_t"] = (rel.hours + rel.ot) / rel.out
    rel["downtime_pct"] = 100 * rel.dt / rel.av
    rel["labour_cost_per_t"] = rel.cost / rel.out
    slope, intercept = np.polyfit(rel.downtime_pct, rel.mh_per_t, 1)
    r = rel[["downtime_pct", "mh_per_t"]].corr().iloc[0, 1]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    colours = {"LOC-W1": BLUE, "LOC-W2": ORANGE, "LOC-W3": "#1baf7a"}
    for w, d in rel.reset_index().groupby("works_location_id"):
        ax.scatter(d.downtime_pct, d.mh_per_t, s=28, color=colours[w], alpha=0.8, label=works_name[w], edgecolor="white")
    xs = np.linspace(rel.downtime_pct.min(), rel.downtime_pct.max(), 20)
    ax.plot(xs, intercept + slope * xs, color=TEXT_2, linewidth=1.2)
    ax.annotate(f"+{slope:.2f} MH/t per 1 pt of downtime (r = {r:.2f})", (xs[-1], intercept + slope * xs[-1]),
                xytext=(-5, 8), textcoords="offset points", ha="right", fontsize=8, color=TEXT_2)
    ax.set(title="More downtime, more man-hours per tonne (monthly, by works)", xlabel="Machine downtime %",
           ylabel="Man-hours per tonne")
    ax.legend(fontsize=8, loc="upper left")
    save_fig(fig, "downtime_vs_productivity")

    reasons = eq[eq.downtime_hours > 0].groupby("downtime_reason").downtime_hours.sum().sort_values(ascending=False)
    save_table((100 * reasons / reasons.sum()).round(1).rename("share_pct").reset_index(), "downtime_reasons")

    east = score.loc["Works-East"]
    west = score.loc["Works-West"]
    chronic = m[m.downtime_pct > 10]
    update_metrics("productivity", {
        "works_scorecard": score.round(2).to_dict("index"),
        "east_vs_west_mh_per_t_gap_pct": 100 * (east.mh_per_tonne / west.mh_per_tonne - 1),
        "east_vs_west_cost_per_t_gap_pct": 100 * (east.conversion_cost_per_t / west.conversion_cost_per_t - 1),
        "downtime_mh_slope": slope, "downtime_mh_corr": r,
        "chronic_machines": chronic.equipment_id.tolist(), "chronic_machine_count": len(chronic),
        "chronic_share_of_downtime_pct": 100 * chronic.down.sum() / m.down.sum(),
        "chronic_share_of_machines_pct": 100 * len(chronic) / len(m),
        "top_machine": m.iloc[0].equipment_id, "top_machine_downtime_pct": m.iloc[0].downtime_pct,
        "east_top_bottleneck": bott[bott.works_location_id == "LOC-W2"].sort_values("share_pct").iloc[-1].process_type,
        "east_top_bottleneck_share_pct": bott[bott.works_location_id == "LOC-W2"].share_pct.max(),
        "recent_time_split": split.round(1).to_dict("index"),
    })
    print(score[["mh_per_tonne", "defect_rate_pct", "conversion_cost_per_t", "utilisation_pct", "downtime_pct",
                 "constrained_days_pct"]].round(1).to_string())
    print(f"{len(chronic)} chronic machines ({100 * len(chronic) / len(m):.0f}% of fleet) cause "
          f"{100 * chronic.down.sum() / m.down.sum():.0f}% of downtime; downtime->MH/t slope {slope:.2f} (r={r:.2f})")


C_SURFACE = "#fcfcfb"

if __name__ == "__main__":
    main()
