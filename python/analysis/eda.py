"""Exploratory data analysis: shape, missing values, distributions, outliers, correlations.

Run: python python/analysis/eda.py
"""
import seaborn as sns

from common import BLUE, GREY, TEXT_2, cr, load, plt, project_drivers, project_kpis, save_fig, save_table, update_metrics


def main():
    t = load()
    # 1. Shape and missing values. Nulls left after cleaning are expected and meaningful,
    #    e.g. actual_end_date is null because a project is still running.
    rows = []
    for name, df in t.items():
        for col in df.columns[df.isna().any()]:
            rows.append(dict(table=name, column=col, missing=int(df[col].isna().sum()),
                             missing_pct=round(100 * df[col].isna().mean(), 2)))
    save_table(__import__("pandas").DataFrame(rows), "eda_missing_values")
    save_table(__import__("pandas").DataFrame([dict(table=n, rows=len(d), columns=d.shape[1]) for n, d in t.items()]),
               "eda_table_shapes")

    k = project_kpis(t)
    done = k[k.status == "Completed"]

    # 2. Contract value is right-skewed: the mean is pulled up by a few large contracts.
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.hist(cr(k.contract_value_inr), bins=20, color=BLUE, edgecolor="white", linewidth=1.5)
    for v, lab, ls in ((cr(k.contract_value_inr).mean(), "mean", "-"), (cr(k.contract_value_inr).median(), "median", "--")):
        ax.axvline(v, color=TEXT_2, linestyle=ls, linewidth=1.2)
        ax.annotate(f"{lab} Rs {v:.0f} Cr", (v, ax.get_ylim()[1] * 0.92), xytext=(4, 0), textcoords="offset points",
                    color=TEXT_2, fontsize=8)
    ax.set(title="Contract values are right-skewed", xlabel="Contract value (Rs crore)", ylabel="Projects")
    save_fig(fig, "eda_contract_value_distribution")

    # 3. Outliers in cost variance, by the IQR rule (beyond 1.5 x IQR from the quartiles)
    q1, q3 = done.cost_variance_pct.quantile([0.25, 0.75])
    lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    outliers = done[(done.cost_variance_pct < lo) | (done.cost_variance_pct > hi)]
    save_table(outliers[["project_id", "project_name", "industry", "cost_variance_pct", "final_margin_pct"]], "eda_cv_outliers")

    # 4. Correlation between project outcomes and operational drivers (completed projects)
    d = project_drivers(t, k).merge(done[["project_id", "cost_variance_pct", "delay_pct", "margin_deterioration_pp"]])
    cols = {"cost_variance_pct": "Cost variance %", "delay_pct": "Delay %", "margin_deterioration_pp": "Margin lost (pp)",
            "low_otd_supplier_share": "Low-OTD supplier share", "late_critical_share": "Late critical items",
            "works_mh_per_t": "Works MH per tonne", "works_constrained_share": "Works constrained days",
            "site_labour_efficiency": "Site labour efficiency", "engineering_slip_days": "Engineering slip",
            "new_energy": "New-energy project"}
    corr = d[list(cols)].rename(columns=cols).corr()
    save_table(corr.round(3), "eda_correlation_matrix", index=True)
    fig, ax = plt.subplots(figsize=(8.5, 7))
    sns.heatmap(corr, cmap=sns.diverging_palette(250, 15, s=75, l=50, as_cmap=True), center=0, vmin=-1, vmax=1,
                annot=True, fmt=".2f", annot_kws={"size": 7}, linewidths=1, linecolor="white", cbar_kws={"shrink": 0.7}, ax=ax)
    ax.set_title("What moves with cost overrun and margin loss? (Pearson r, completed projects)")
    ax.grid(False)
    save_fig(fig, "eda_correlation_heatmap")

    update_metrics("eda", {
        "projects": len(k), "completed": len(done), "in_progress": int((k.status == "In Progress").sum()),
        "contract_value_mean_cr": cr(k.contract_value_inr).mean(), "contract_value_median_cr": cr(k.contract_value_inr).median(),
        "portfolio_value_cr": cr(k.contract_value_inr.sum()), "cv_outliers": outliers.project_id.tolist(),
        "fact_rows": int(sum(len(v) for n, v in t.items() if n.startswith("fact_"))),
    })
    print(f"EDA: {len(k)} projects, median contract Rs {cr(k.contract_value_inr).median():.0f} Cr vs mean "
          f"Rs {cr(k.contract_value_inr).mean():.0f} Cr; {len(outliers)} cost-variance outliers")
    print(corr[["Cost variance %", "Margin lost (pp)"]].round(2).to_string())


if __name__ == "__main__":
    main()
