"""Project delay analysis (Phase 14): how late, which stage, which cause, what it cost.

Run: python python/analysis/delays.py
"""
import numpy as np
import pandas as pd

from common import (BLUE, GREY, ORANGE, STATUS, TEXT_2, bar_labels, cr, delay_cost_per_day, load, plt,
                    project_kpis, save_fig, save_table, update_metrics)


def main():
    t = load()
    k = project_kpis(t)
    done = k[k.status == "Completed"]
    ms = t["fact_milestones"].merge(t["dim_stage"][["stage_id", "stage_name", "stage_order"]])
    comp = ms[ms.milestone_status == "Completed"].copy()
    comp["own_delay"] = (comp.end_delay_days - comp.start_delay_days).clip(lower=0)
    # The Procurement stage "ends" at the last goods receipt of ANY item, usually a non-critical one
    # needed late on site, so its own delay is not on the critical path. Late critical items show up
    # where they bite: as "Supplier delay" on Fabrication (steel) and Installation (critical equipment).
    critical_path = comp[comp.stage_id != 3]

    # --- Which stage adds the most delay? -------------------------------------------------
    stage = comp.groupby(["stage_order", "stage_name"]).agg(avg_end_delay=("end_delay_days", "mean"),
                                                           avg_own_delay=("own_delay", "mean"),
                                                           total_added_days=("own_delay", "sum")).reset_index()
    cp_total = stage.loc[stage.stage_name != "Procurement", "total_added_days"].sum()
    stage["share_pct"] = np.where(stage.stage_name == "Procurement", np.nan, 100 * stage.total_added_days / cp_total)
    save_table(stage, "delay_by_stage")

    # --- Root causes (Pareto, one axis: both bars and cumulative line are % of total) --------
    causes = critical_path[critical_path.delay_cause != "On schedule"].groupby("delay_cause").own_delay.sum().sort_values(ascending=False)
    share = 100 * causes / causes.sum()
    cum = share.cumsum()
    save_table(pd.DataFrame({"added_delay_days": causes, "share_pct": share, "cumulative_pct": cum}).reset_index(),
               "delay_causes_pareto")
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(share))
    ax.bar(x, share, color=BLUE, width=0.6)
    ax.plot(x, cum, color=ORANGE, marker="o", markersize=5, linewidth=2)
    for i, (s, c) in enumerate(zip(share, cum)):
        ax.annotate(f"{s:.0f}%", (i, s), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=TEXT_2)
    ax.axhline(80, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.annotate("80%", (len(share) - 0.5, 80), xytext=(0, 3), textcoords="offset points", fontsize=8, color=TEXT_2)
    ax.set_xticks(x, share.index, rotation=20, ha="right")
    ax.set(title="Pareto of delay causes (critical-path stages; line = cumulative %)", ylabel="% of added delay days",
           ylim=(0, 105))
    ax.grid(axis="x", visible=False)
    save_fig(fig, "delay_causes_pareto")

    # --- Delay vs cost overrun ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter(done.delay_pct, done.cost_variance_pct, color=[STATUS[s] for s in done.schedule_status], s=40,
               edgecolor="white")
    r = done[["delay_pct", "cost_variance_pct"]].corr().iloc[0, 1]
    m, b = np.polyfit(done.delay_pct, done.cost_variance_pct, 1)
    xs = np.linspace(done.delay_pct.min(), done.delay_pct.max(), 10)
    ax.plot(xs, m * xs + b, color=TEXT_2, linewidth=1)
    ax.annotate(f"r = {r:.2f}", (xs[-1], m * xs[-1] + b), xytext=(-4, 6), textcoords="offset points", ha="right",
                fontsize=8, color=TEXT_2)
    handles = [plt.Line2D([], [], marker="o", linestyle="", color=STATUS[s]) for s in ("On time", "Minor delay", "Major delay", "Critical delay")]
    ax.legend(handles, ["On time", "Minor", "Major", "Critical"], fontsize=8, loc="upper left")
    ax.set(title="Late projects also overrun cost", xlabel="Delay % of planned duration", ylabel="Cost variance %")
    save_fig(fig, "delay_vs_cost_variance")

    # --- What did delay cost? ---------------------------------------------------------------
    dc = delay_cost_per_day(t)
    d = done.set_index("project_id").join(dc)
    d["extra_time_cost"] = d.delay_days.clip(lower=0) * d.time_cost_per_day
    cost_by_status = d.groupby("schedule_status").agg(projects=("delay_days", "size"), avg_delay=("delay_days", "mean"),
                                                      ld_cr=("ld_deducted", lambda x: cr(x.sum())),
                                                      extra_time_cost_cr=("extra_time_cost", lambda x: cr(x.sum())),
                                                      avg_margin_pct=("final_margin_pct", "mean"))
    cost_by_status = cost_by_status.reindex(["On time", "Minor delay", "Major delay", "Critical delay"]).dropna(how="all")
    save_table(cost_by_status.reset_index(), "delay_cost_by_status")

    sched = done.schedule_status.value_counts()
    wip = k[k.status == "In Progress"]
    update_metrics("delays", {
        "completed_delayed_pct": 100 * (done.delay_days > 0).mean(),
        "avg_delay_days": done.delay_days.mean(), "median_delay_days": done.delay_days.median(),
        "avg_delay_pct": done.delay_pct.mean(), "schedule_status_counts": sched.to_dict(),
        "ld_projects": int((done.ld_deducted > 0).sum()), "ld_cr": cr(done.ld_deducted.sum()),
        "extra_time_cost_cr": cr(d.extra_time_cost.sum()),
        "delay_cost_total_cr": cr(d.extra_time_cost.sum() + d.ld_deducted.sum()),
        "top_cause": causes.index[0], "top_cause_share_pct": share.iloc[0],
        "top2_causes": causes.index[:2].tolist(), "top2_share_pct": share.iloc[:2].sum(),
        "cause_share_pct": share.round(1).to_dict(),
        "top_stage": stage.dropna(subset=["share_pct"]).sort_values("share_pct").iloc[-1].stage_name,
        "top_stage_share_pct": stage.share_pct.max(),
        "stage_share_pct": dict(zip(stage.stage_name, stage.share_pct.round(1).fillna(-1))),
        "procurement_avg_tail_days": float(stage.loc[stage.stage_name == "Procurement", "avg_own_delay"].iloc[0]),
        "corr_delay_cost_variance": r,
        "margin_on_time": d[d.schedule_status == "On time"].final_margin_pct.mean(),
        "margin_major_or_worse": d[d.schedule_status.isin(["Major delay", "Critical delay"])].final_margin_pct.mean(),
        "wip_slipping": int((wip.delay_days > 0).sum()),
        "wip_major_or_worse": int(wip.schedule_status.isin(["Major delay", "Critical delay"]).sum()),
    })
    print(stage[["stage_name", "avg_own_delay", "share_pct"]].round(1).to_string(index=False))
    print(share.round(1).to_string())
    print(cost_by_status.round(2).to_string())


if __name__ == "__main__":
    main()
