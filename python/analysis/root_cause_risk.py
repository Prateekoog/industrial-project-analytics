"""Root-cause analysis and the project risk score (Phase 15).

Run: python python/analysis/root_cause_risk.py

Root cause: compare outcomes for projects WITH and WITHOUT each operational symptom, then
check the effects jointly with a simple regression so one driver is not credited with another's
impact. Correlation is not causation; each driver here also has a mechanism we can name.

Risk score: four components scaled 0-100. Weights are DERIVED from the data: each component's
correlation with margin lost on completed projects, normalised to 100% and rounded to 5%.
Margin itself is not a component, because margin is what the score tries to predict (circular).
"""
import numpy as np
import pandas as pd

from common import (BLUE, GREY, ORANGE, STATUS, TEXT_2, load, plt, project_drivers, project_kpis, save_fig,
                    save_table, update_metrics)

TIERS = [(0, 25, "Low"), (25, 45, "Medium"), (45, 65, "High"), (65, 101, "Critical")]


def scale(x, zero_at, full_at):
    """Linear 0-100 scale, clipped. zero_at may be above full_at for 'lower is worse' measures."""
    return (100 * (x - zero_at) / (full_at - zero_at)).clip(0, 100)


def main():
    t = load()
    k = project_kpis(t)
    d = project_drivers(t, k).merge(k, on="project_id")
    done = d[d.status == "Completed"].copy()

    # --- 1. Symptom comparisons (with vs without) --------------------------------------------
    tests = {
        "Engineering slip > 30 days": done.engineering_slip_days > 30,
        "Critical item arrived after need date": done.max_critical_lateness_days > 0,
        "Site labour efficiency < 90%": done.site_labour_efficiency < 0.90,
        "Fabricated at Works-East": done.works_location_id == "LOC-W2",
        "New-energy technology": done.new_energy == 1,
        "Above-median low-OTD supplier spend": done.low_otd_supplier_share > done.low_otd_supplier_share.median(),
    }
    rows = []
    for name, mask in tests.items():
        for flag, grp in ((True, done[mask]), (False, done[~mask])):
            rows.append(dict(symptom=name, present=flag, projects=len(grp), avg_cost_variance_pct=grp.cost_variance_pct.mean(),
                             avg_delay_days=grp.delay_days.mean(), avg_margin_lost_pp=grp.margin_deterioration_pp.mean()))
    comp = pd.DataFrame(rows)
    save_table(comp.round(2), "root_cause_symptom_comparison")
    gap = comp.pivot(index="symptom", columns="present", values="avg_margin_lost_pp")
    gap["difference_pp"] = gap[True] - gap[False]
    gap = gap.sort_values("difference_pp")

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    bars = ax.barh(gap.index, gap.difference_pp, color=[ORANGE if v > 0 else GREY for v in gap.difference_pp], height=0.55)
    for b, v in zip(bars, gap.difference_pp):
        ax.annotate(f"{v:+.1f} pp", (v, b.get_y() + b.get_height() / 2), xytext=(4 if v >= 0 else -4, 0),
                    textcoords="offset points", va="center", ha="left" if v >= 0 else "right", fontsize=8, color=TEXT_2)
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.set(title="Extra margin lost when a symptom is present (completed projects)",
           xlabel="Margin lost with symptom minus without (percentage points)")
    ax.grid(axis="y", visible=False)
    save_fig(fig, "root_cause_symptoms")

    # --- 2. Joint view: standardised regression of margin lost on the drivers ---------------
    X_cols = ["engineering_slip_days", "max_critical_lateness_days", "site_labour_efficiency", "works_mh_per_t",
              "low_otd_supplier_share", "new_energy"]
    m = done.dropna(subset=X_cols + ["margin_deterioration_pp"])
    X = (m[X_cols] - m[X_cols].mean()) / m[X_cols].std()
    X = np.column_stack([np.ones(len(X)), X.values])
    y = m.margin_deterioration_pp.values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((y - X @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    reg = pd.DataFrame({"driver": X_cols, "std_coefficient_pp": beta[1:]}).sort_values("std_coefficient_pp", ascending=False)
    save_table(reg.round(3), "root_cause_regression")

    # --- 3. Risk score ---------------------------------------------------------------------
    d["cost_risk"] = scale(d.cost_variance_pct, 0, 15)                       # 0 at on-budget, 100 at +15%
    d["schedule_risk"] = scale(d.delay_pct, 0, 25)                           # 0 on time, 100 at 25% late
    d["supplier_risk"] = scale(d.late_critical_share.fillna(0), 0, 0.4)     # share of critical lines late vs need
    d["productivity_risk"] = 0.5 * scale(d.site_labour_efficiency.fillna(1), 1.0, 0.75) + \
        0.5 * scale(d.works_mh_per_t.fillna(30), 30, 40)
    comps = ["cost_risk", "schedule_risk", "supplier_risk", "productivity_risk"]
    hist = d[d.status == "Completed"]
    corr = hist[comps].corrwith(hist.margin_deterioration_pp).clip(lower=0)
    raw = corr / corr.sum()
    weights = (raw * 20).round() / 20                                        # nearest 5%
    weights.iloc[weights.values.argmax()] += 1 - weights.sum()               # make them add to exactly 100%
    d["risk_score"] = sum(weights[c] * d[c] for c in comps).round(1)
    d["risk_tier"] = pd.cut(d.risk_score, [x[0] for x in TIERS] + [101], labels=[x[2] for x in TIERS], right=False).astype(str)
    w_tbl = pd.DataFrame({"component": comps, "correlation_with_margin_lost": corr.values, "weight": weights.values})
    save_table(w_tbl.round(3), "risk_weights")

    tier_check = d[d.status == "Completed"].groupby("risk_tier").agg(projects=("project_id", "size"),
                                                                     avg_margin_lost_pp=("margin_deterioration_pp", "mean"),
                                                                     avg_margin_pct=("final_margin_pct", "mean"))
    tier_check = tier_check.reindex([x[2] for x in TIERS]).dropna(how="all")
    save_table(tier_check.reset_index(), "risk_tier_validation")
    cols = ["project_id", "project_name", "industry", "status", "percent_complete", "cost_variance_pct", "delay_days",
            "final_margin_pct", "estimated_margin_pct"] + comps + ["risk_score", "risk_tier"]
    scores = d[cols].sort_values("risk_score", ascending=False)
    save_table(scores.round(2), "project_risk_scores")

    wip = scores[scores.status == "In Progress"].head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    left = np.zeros(len(wip))
    colours = {"cost_risk": BLUE, "schedule_risk": ORANGE, "supplier_risk": "#1baf7a", "productivity_risk": "#eda100"}
    for c in comps:
        contrib = weights[c] * wip[c].values
        ax.barh(wip.project_id, contrib, left=left, color=colours[c], height=0.6, edgecolor="#fcfcfb", linewidth=2,
                label=f"{c.replace('_risk', '').title()} ({weights[c]:.0%})")
        left += contrib
    for i, (s, tier) in enumerate(zip(wip.risk_score, wip.risk_tier)):
        ax.annotate(f"{s:.0f} {tier}", (s, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8, color=TEXT_2)
    ax.set(title="In-progress projects: risk score and what drives it", xlabel="Risk score (0-100)", xlim=(0, 100))
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="y", visible=False)
    save_fig(fig, "risk_score_in_progress")

    tiers_all = d.groupby(["status", "risk_tier"]).size().unstack(fill_value=0)
    update_metrics("root_cause_risk", {
        "symptom_gap_pp": gap.difference_pp.round(2).to_dict(),
        "regression_r2": r2, "regression_std_coef": dict(zip(reg.driver, reg.std_coefficient_pp.round(2))),
        "risk_weights": weights.round(2).to_dict(), "risk_corr": corr.round(3).to_dict(),
        "tier_validation_margin_lost": tier_check.avg_margin_lost_pp.round(2).to_dict(),
        "tier_counts": {s: tiers_all.loc[s].to_dict() for s in tiers_all.index},
        "top_risk_wip": scores[scores.status == "In Progress"].head(5)[["project_id", "risk_score", "risk_tier"]].to_dict("records"),
        "wip_high_or_critical": int(scores[(scores.status == "In Progress") & scores.risk_tier.isin(["High", "Critical"])].shape[0]),
    })
    print(gap.round(2).to_string())
    print(f"Regression R2 {r2:.2f}:", dict(zip(reg.driver, reg.std_coefficient_pp.round(2))))
    print("Weights:", weights.to_dict())
    print(tier_check.round(2).to_string())
    print(scores[scores.status == "In Progress"].head(6)[["project_id", "industry", "risk_score", "risk_tier"]].to_string(index=False))


if __name__ == "__main__":
    main()
