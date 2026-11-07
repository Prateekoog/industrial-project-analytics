"""Supplier performance and total-cost-of-ownership analysis (Phase 13).

Run: python python/analysis/procurement.py

The question is not "who is cheapest?" but "who costs the project least once lateness is counted?"
"""
import numpy as np
import pandas as pd

from common import (BLUE, GREY, ORANGE, TEXT_2, cr, delay_cost_per_day, load, plt, project_kpis, save_fig,
                    save_table, update_metrics)


def main():
    t = load()
    po = t["fact_procurement"].merge(t["dim_material"][["material_id", "criticality_class", "is_steel_linked"]])
    po["critical"] = po.criticality_class.eq("A") | po.is_steel_linked
    sup = t["dim_supplier"].set_index("supplier_id")
    delivered = po[po.delivery_date.notna()]

    # --- Scorecard -----------------------------------------------------------------------
    g = delivered.groupby("supplier_id")
    sc = pd.DataFrame({
        "supplier_name": sup.supplier_name, "material_group": sup.material_group,
        "po_lines": g.size(), "spend_cr": g.line_value_inr.sum() / 1e7,
        "otd_pct": 100 * g.is_on_time.mean(),
        "avg_days_late_when_late": delivered[delivered.delivery_delay_days > 0].groupby("supplier_id").delivery_delay_days.mean(),
        "avg_lead_time_days": g.lead_time_days.mean(),
        "price_index": g.line_value_inr.sum() / (delivered.quantity * delivered.benchmark_unit_price_inr).groupby(delivered.supplier_id).sum(),
        "rejection_pct": 100 * g.qty_rejected.sum() / g.quantity.sum(),
    }).dropna(subset=["po_lines"])
    # Composite score (0-100): delivery 40%, price 30%, quality 30%. Each component is ranked as a
    # percentile within the supplier base so different units can be combined.
    sc["delivery_score"] = sc.otd_pct.rank(pct=True)
    sc["price_score"] = (-sc.price_index).rank(pct=True)
    sc["quality_score"] = (-sc.rejection_pct).rank(pct=True)
    sc["composite_score"] = (100 * (0.4 * sc.delivery_score + 0.3 * sc.price_score + 0.3 * sc.quality_score)).round(1)
    sc["rank"] = sc.composite_score.rank(ascending=False, method="min").astype(int)
    sc = sc.sort_values("rank")
    save_table(sc.reset_index(), "supplier_scorecard")

    # --- Price vs reliability quadrant ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.scatter(sc.price_index, sc.otd_pct, s=np.clip(sc.spend_cr * 4, 15, 300), color=BLUE, alpha=0.7, edgecolor="white")
    ax.axvline(1.0, color=TEXT_2, linestyle="--", linewidth=0.8)
    ax.axhline(70, color=TEXT_2, linestyle="--", linewidth=0.8)
    for x, y, lab in ((0.905, 97, "Cheap and reliable"), (1.075, 97, "Premium and reliable"),
                      (0.905, 40, "Cheap but late"), (1.075, 40, "Expensive and late")):
        ax.annotate(lab, (x, y), fontsize=8, color=TEXT_2, ha="center")
    for sid, r in sc[(sc.otd_pct < 60)].iterrows():
        ax.annotate(sid, (r.price_index, r.otd_pct), xytext=(4, -3), textcoords="offset points", fontsize=7, color=TEXT_2)
    ax.set(title="Supplier price vs on-time delivery (bubble = spend)", xlabel="Price index vs market (1.00 = market)",
           ylabel="On-time delivery %", ylim=(30, 102))
    save_fig(fig, "supplier_price_vs_otd")

    # --- Does lateness actually delay projects? Pass-through from late critical items ------
    k = project_kpis(t)
    done = k[k.status == "Completed"].set_index("project_id")
    ms = t["fact_milestones"]
    inst = ms[(ms.stage_id == 5) & ms.actual_end_date.notna()].set_index("project_id")
    a = po[(po.criticality_class == "A") & po.grn_date.notna()]
    lateness = (a.grn_date - a.need_by_date).dt.days.clip(lower=0).groupby(a.project_id).max()
    rel = pd.DataFrame({"max_a_lateness": lateness, "install_own_delay": inst.end_delay_days - inst.start_delay_days,
                        "project_delay": done.delay_days}).dropna()
    pass_through, _ = np.polyfit(rel.max_a_lateness, rel.project_delay, 1)
    pass_through = float(np.clip(pass_through, 0, 1))

    # --- Total cost of ownership: price saving vs cost of lateness -----------------------
    dc = delay_cost_per_day(t)
    crit = po[po.critical & po.grn_date.notna()].copy()
    crit["days_late_vs_need"] = (crit.grn_date - crit.need_by_date).dt.days.clip(lower=0)
    crit["market_value"] = crit.quantity * crit.benchmark_unit_price_inr
    crit["saving_vs_market"] = crit.market_value - crit.line_value_inr
    # Only the latest critical item on a project can move its finish date; spread the expected
    # delay cost across lines in proportion to lateness (pass-through estimated above).
    crit["lateness_cost"] = crit.days_late_vs_need * pass_through * crit.project_id.map(dc.delay_cost_per_day) \
        / crit.groupby("project_id").days_late_vs_need.transform(lambda x: max(1, (x > 0).sum()))
    tco = crit.groupby("supplier_id").agg(critical_spend_cr=("line_value_inr", lambda x: x.sum() / 1e7),
                                          price_saving_lakh=("saving_vs_market", lambda x: x.sum() / 1e5),
                                          lateness_cost_lakh=("lateness_cost", lambda x: x.sum() / 1e5),
                                          late_lines=("days_late_vs_need", lambda x: (x > 0).sum()))
    tco["net_benefit_lakh"] = tco.price_saving_lakh - tco.lateness_cost_lakh
    tco = tco.join(sc[["supplier_name", "material_group", "otd_pct", "price_index"]]).sort_values("net_benefit_lakh")
    save_table(tco.reset_index(), "supplier_total_cost_of_ownership")

    # The "Supplier A vs Supplier B" question, answered with the pair that has the most spend
    # in one critical material group: the cheapest supplier vs the most reliable one.
    pairs = []
    for grp, d in sc.groupby("material_group"):
        if len(d) < 2:
            continue
        cheap, reliable = d.price_index.idxmin(), d.otd_pct.idxmax()
        if cheap != reliable and grp in ("Gearboxes & Drives", "Castings & Forgings", "Motors", "Pumps & Compressors"):
            pairs.append(dict(material_group=grp, cheap=cheap, reliable=reliable,
                              cheap_price_index=d.at[cheap, "price_index"], reliable_price_index=d.at[reliable, "price_index"],
                              cheap_otd=d.at[cheap, "otd_pct"], reliable_otd=d.at[reliable, "otd_pct"],
                              cheap_net_lakh=tco.net_benefit_lakh.get(cheap, np.nan),
                              reliable_net_lakh=tco.net_benefit_lakh.get(reliable, np.nan),
                              cheap_spend_cr=d.at[cheap, "spend_cr"], reliable_spend_cr=d.at[reliable, "spend_cr"]))
    ab = pd.DataFrame(pairs)
    save_table(ab, "supplier_a_vs_b")

    fig, ax = plt.subplots(figsize=(8, 5))
    show = tco.reindex(tco.net_benefit_lakh.abs().sort_values(ascending=False).index[:14]).sort_values("net_benefit_lakh")
    y = np.arange(len(show))
    ax.barh(y + 0.2, show.price_saving_lakh, height=0.38, color=BLUE, label="Price saving vs market")
    ax.barh(y - 0.2, -show.lateness_cost_lakh, height=0.38, color=ORANGE, label="Cost of late critical deliveries")
    ax.scatter(show.net_benefit_lakh, y, color=TEXT_2, s=18, zorder=3, label="Net benefit")
    ax.set_yticks(y, [f"{i} ({r.otd_pct:.0f}% OTD)" for i, r in show.iterrows()], fontsize=8)
    ax.axvline(0, color=TEXT_2, linewidth=0.8)
    ax.set(title="Cheaper is not always cheaper: price saving vs lateness cost", xlabel="Rs lakh, critical items, all years")
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="y", visible=False)
    save_fig(fig, "supplier_total_cost")

    # --- Price volatility by material group ------------------------------------------------
    mat = t["dim_material"].set_index("material_id")
    po["price_ratio"] = po.unit_price_inr / po.material_id.map(mat.standard_price_inr)
    vol = po.groupby(po.material_id.map(mat.material_group)).price_ratio.agg(["mean", "std", "size"])
    vol["coeff_variation"] = vol["std"] / vol["mean"]
    vol = vol.sort_values("coeff_variation", ascending=False)
    save_table(vol.reset_index().rename(columns={"material_id": "material_group"}), "material_price_volatility")

    bad = sc[sc.otd_pct < 60]
    good = sc[sc.otd_pct >= 85]
    update_metrics("procurement", {
        "suppliers": len(sc), "overall_otd_pct": 100 * delivered.is_on_time.mean(),
        "critical_otd_pct": 100 * delivered[delivered.critical].is_on_time.mean(),
        "low_otd_suppliers": bad.index.tolist(), "low_otd_supplier_count": len(bad),
        "low_otd_avg_otd_pct": bad.otd_pct.mean(), "low_otd_avg_price_index": bad.price_index.mean(),
        "reliable_avg_otd_pct": good.otd_pct.mean(), "reliable_avg_price_index": good.price_index.mean(),
        "low_otd_spend_share_pct": 100 * bad.spend_cr.sum() / sc.spend_cr.sum(),
        "pass_through_days_per_day_late": pass_through,
        "avg_delay_cost_per_day_lakh": dc.delay_cost_per_day.mean() / 1e5,
        "avg_time_cost_per_day_lakh": dc.time_cost_per_day.mean() / 1e5,
        "low_otd_tco_net_lakh": tco[tco.index.isin(bad.index)].net_benefit_lakh.sum(),
        "low_otd_price_saving_lakh": tco[tco.index.isin(bad.index)].price_saving_lakh.sum(),
        "low_otd_lateness_cost_lakh": tco[tco.index.isin(bad.index)].lateness_cost_lakh.sum(),
        "most_volatile_group": vol.index[0], "most_volatile_cv": vol.coeff_variation.iloc[0],
        "top_supplier": sc.index[0], "bottom_supplier": sc.index[-1],
        "a_vs_b": ab.round(3).to_dict("records"),
        "total_spend_cr": cr(po.line_value_inr.sum()),
    })
    print(sc[["supplier_name", "otd_pct", "price_index", "rejection_pct", "composite_score"]].head(5).round(2).to_string())
    print(f"... {len(bad)} suppliers below 60% OTD: avg price index {bad.price_index.mean():.3f}, OTD {bad.otd_pct.mean():.0f}%")
    print(f"Pass-through: {pass_through:.2f} project-delay days per day of critical lateness; "
          f"avg delay cost Rs {dc.delay_cost_per_day.mean() / 1e5:.1f} L/day")
    print(tco.loc[tco.index.isin(bad.index), ["price_saving_lakh", "lateness_cost_lakh", "net_benefit_lakh"]].round(1).to_string())


if __name__ == "__main__":
    main()
