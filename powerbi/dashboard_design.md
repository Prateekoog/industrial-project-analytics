# Dashboard Design: 4 pages

Every visual answers a named business question for a named user. If a visual cannot be tied to a decision, it is not on the page. A Python rendering of this design, with the real numbers, is in `reports/figures/dashboard_page1-4_*.png`.

**Layout:** 16:9 canvas. Row 1 is KPI cards, rows 2 and 3 are visuals. Slicers sit in one row above the visuals: Fiscal year, Industry, Status, Works. The theme is `projectco_theme.json`; the status colours (green, amber, orange, red) are reserved for status and never used for ordinary series.

---

## Page 1: Executive overview
**User:** MD / CFO. **Question:** "How is the portfolio doing financially, and where is the risk?"

| # | Visual | Fields / measures | Business question it answers |
|---|---|---|---|
| KPI | Card x8 | Project Count; Revenue (Rs Cr); Actual Cost (Completed); Actual Profit (Rs Cr); Actual Margin % (Completed) with Margin Label; Cost Overrun % (Completed); Delayed Projects; Potential Savings | The eight numbers a CFO asks first. Margin is shown *against the bid* so the gap is visible. |
| 1 | Clustered column | Axis `dim_date[fiscal_year]`; Total Revenue, Actual Cost | Is cost growing faster than billing? |
| 2 | Clustered bar | Axis `dim_project[industry]`; Estimated Profit (Completed), Actual Profit (Completed) | Which industries deliver the profit we bid, and which give it away? |
| 3 | Column, coloured by tier | Axis `dim_project[risk_tier]`; Project Count; legend `status` | How many live projects need senior attention? |
| 4 | Column, sorted, conditional colour | Axis `project_id`; Cost Variance % (Completed); colour by `cost_status` | Which projects broke the 5% and 10% thresholds? |
| 5 | Dot / dumbbell (or clustered bar) | `industry`; Estimated Margin %, Actual Margin % | Margin bid vs delivered by industry: points the bid team at the segments it under-prices. |

**Interactions:** clicking an industry filters every visual. Drill-through from any project to Page 2.

## Page 2: Project performance
**User:** Head of Projects / PMs. **Question:** "Which projects are off track, by how much, and where in the lifecycle?"

| # | Visual | Fields / measures | Question |
|---|---|---|---|
| KPI | Card x6 | Critical overruns; Warning; Average Delay (days); loss-making count; in-progress CPI < 1 count; High or Critical risk | Size of the problem today |
| 1 | Scatter | X `delay_days` %, Y Cost Variance %, colour `cost_status`, size Contract Value | Do late projects also overrun? (r = 0.67) Quadrant lines at 10% CV and 20% delay. |
| 2 | Column | Axis `dim_stage[stage_name]`; Stage Own Delay (days) | Which stage *adds* slippage (not just inherits it)? |
| 3 | Pareto (bar + cumulative line, one % axis) | `fact_milestones[delay_cause]`; share of added delay days | Which causes to fix first |
| 4 | Clustered column | Top-N projects by Cost Variance; Revised Budget vs Actual Cost | Estimated vs actual cost for the worst projects |
| 5 | Table with conditional formatting | In-progress projects: % complete, CPI, Forecast Cost Variance %, delay, risk score | Live watch list: where action can still change the outcome |

**Drill-through page "Project detail":** cost by category (budget vs actual), milestone Gantt-style bar (planned vs actual), supplier late lines for the project.

## Page 3: Operations and productivity
**User:** Works head / Plant manager. **Question:** "Where are we losing fabrication capacity and labour hours?"

| # | Visual | Fields / measures | Question |
|---|---|---|---|
| KPI | Card x6 | Labour Productivity (MH per t) vs 30 standard; Machine Utilisation %; Downtime %; Output Achievement %; Defect Rate %; chronic machine count | Is the shop productive and reliable? |
| 1 | Column by works | Labour Productivity (MH per t), constant line at 30 | Which works needs the most hours per tonne? |
| 2 | 100% stacked bar by works | Utilisation %, Downtime %, Idle % | Is low utilisation "no work" or "broken machines"? |
| 3 | Column by works | Defect Rate % | Where is rework consuming capacity? |
| 4 | Bar, top 12 machines | Downtime % by `dim_equipment[equipment_id]` | Which machines to target for maintenance |
| 5 | Bar | `dim_work_centre[process_type]` vs constrained-day count (filter Works-East) | Which work centre is the bottleneck? |
| 6 | Scatter (monthly) | X Downtime %, Y Labour Productivity, colour works | Proof that downtime drives man-hours per tonne |

**Explain on the page (text box):** productivity (output per hour), efficiency (standard hours ÷ actual hours), utilisation (operating ÷ available), capacity (what could be made) and output (what was made) are different measures.

## Page 4: Procurement and cost optimisation
**User:** Head of Procurement, CFO. **Question:** "Which suppliers really cost us least, and which improvements should we fund?"

| # | Visual | Fields / measures | Question |
|---|---|---|---|
| KPI | Card x6 | Supplier On-Time %; Procurement Spend; Avg Lead Time; Late Deliveries; low-OTD supplier count; procurement cycle As-Is vs To-Be | Health of the supply base |
| 1 | Scatter quadrant | X Price Index vs Market, Y Supplier On-Time %, size Spend | Cheap-but-late vs premium-and-reliable suppliers |
| 2 | Bar (diverging) | Price saving vs lateness cost per supplier (from `supplier_total_cost_of_ownership`) | Is the cheaper supplier really cheaper? |
| 3 | Line | On-Time % by PO quarter | Is delivery performance improving? |
| 4 | Bar | Material group by price volatility | Where to use price-variation clauses or hedge |
| 5 | Bar with labels | `ref_initiatives`: 5-year NPV, payback | Which improvement to fund first |

## Visual-design rules applied
- One y-axis per chart (no dual axes). The Pareto uses % for both the bars and the cumulative line.
- Status colours appear only on status fields, and always with a text label.
- No pie charts for more than 3 parts; bars are easier to compare.
- No 3D, no decorative gauges. Cards show a comparison (vs bid, vs standard), not a lone number.
