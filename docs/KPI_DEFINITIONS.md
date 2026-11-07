# KPI Definitions

One formula per KPI, used identically in SQL (`sql/00_views.sql`), Python (`python/analysis/common.py`), Excel and DAX (`powerbi/dax_measures.md`). Thresholds come from `docs/ASSUMPTIONS.md` section H.

## Financial

| KPI | Formula | Tiny example | Notes |
|---|---|---|---|
| Revenue | Contract value + approved change orders + price variation - liquidated damages | 100 + 6 + 1 - 2 = Rs 105 Cr | C05. GST excluded. |
| Estimated cost | Sum of bid budget across 8 categories | Rs 86 Cr | The bid estimate |
| Revised budget | Estimated cost + change-order budget | 86 + 5 = Rs 91 Cr | Baseline for cost variance (C07) |
| Actual cost | Sum of ledger postings | Rs 95 Cr | Completed: final. In progress: to date. |
| Cost variance (Rs) | Actual cost - revised budget | 95 - 91 = Rs 4 Cr | Positive = overspent |
| Cost variance % | Cost variance / revised budget x 100 | 4 / 91 = 4.4% | |
| Cost status | < -2% Under budget; -2 to 5% On budget; 5 to 10% Warning; > 10% Critical | 4.4% = On budget | H01: thresholds tied to margin erosion |
| Estimated profit | Contract value - estimated cost | 100 - 86 = Rs 14 Cr | |
| Actual profit | Revenue - actual cost | 105 - 95 = Rs 10 Cr | |
| Estimated margin % | Estimated profit / contract value | 14% | |
| Actual margin % | Actual profit / revenue | 10 / 105 = 9.5% | |
| Margin deterioration (pp) | Estimated margin % - actual margin % | 14 - 9.5 = 4.5 pp | Percentage *points*, not percent |
| Profit variance | Actual profit - estimated profit | 10 - 14 = -Rs 4 Cr | |
| Portfolio margin | Total profit / total revenue (weighted) | | Never the average of project margins: that would weight a Rs 20 Cr job like a Rs 400 Cr one |
| Liquidated damages | min(ceil(contractor delay days / 7) x 0.5%, 5%) x contract value, applied only after a 14-day grace period | 25 days late: 4 weeks x 0.5% x 100 = Rs 2 Cr | C08 |

## Earned value (in-progress projects)

| KPI | Formula | Example | Meaning |
|---|---|---|---|
| Earned value (EV) | Revised budget x % complete | 100 x 40% = Rs 40 Cr | Budgeted cost of the work actually done |
| Cost performance index (CPI) | EV / actual cost to date | 40 / 46 = 0.87 | Below 1 = spending ahead of progress |
| Estimate at completion (EAC) | Revised budget / CPI | 100 / 0.87 = Rs 115 Cr | Final cost if efficiency stays the same |
| Forecast cost variance % | (EAC - revised budget) / revised budget | +15% | Same thresholds as completed projects |

## Schedule

| KPI | Formula | Notes |
|---|---|---|
| Delay days | Actual end - contractual end (completed). For in-progress projects: the largest slip already visible on a started stage. | |
| Delay % | Delay days / planned duration x 100 | H02: <= 2% On time; 2 to 10% Minor; 10 to 20% Major; > 20% Critical |
| Stage own delay | Stage end delay - stage start delay | What the stage *added* rather than inherited |
| Delay cost | Extra time-based cost (60% of overhead + half of equipment, per planned day) x delay days + LD | |

## Productivity and operations

These five words are easily confused. They mean different things:

| Term | Question it answers | Formula here | Example |
|---|---|---|---|
| **Output** | How much did we make? | Tonnes fabricated | 300 t this week |
| **Capacity** | How much *could* we make? | Machine available hours x rated t/hour at the bottleneck | 400 t/week |
| **Utilisation** | What share of available machine time was used? | Operating hours / available hours | 60% |
| **Productivity** | Output per unit of input | Tonnes per 100 man-hours, or its inverse, man-hours per tonne (MH/t) | 33 MH/t |
| **Efficiency** | How close to the standard was the work done? | Standard hours / actual hours (= 30 MH/t / actual MH/t) | 30 / 33 = 91% |

A machine can be highly *utilised* but unproductive (running slowly, making rework). Labour can be *efficient* while output is low (no work loaded). Each KPI points to a different fix.

| KPI | Formula | Threshold / standard |
|---|---|---|
| Labour productivity | (Regular + overtime labour hours) / output tonnes | Standard 30 MH/t (F04) |
| Labour efficiency % | 30 MH/t / actual MH/t | 100% = on standard |
| Machine utilisation % | Operating hours / available hours | Available = scheduled - planned maintenance (F03) |
| Downtime % | Unplanned downtime hours / available hours | Chronic machine: > 10% |
| Idle % | Idle hours / available hours | Utilisation + downtime + idle = 100% |
| Output achievement % | Actual output / planned output | 100% = plan met |
| Defect (rework) rate % | Rework tonnes / output tonnes | Good 1-3%, problem > 5% (F05) |
| Conversion cost per tonne | (Labour + machine + energy cost) / output tonnes | Excludes material |
| Overtime % | Overtime hours / total labour hours | |
| Site labour efficiency | Earned hours / (regular + overtime + idle hours) | < 90% flagged |
| Capacity-constrained days % | Days when demand exceeded bottleneck capacity / production days | |

## Procurement

| KPI | Formula | Notes |
|---|---|---|
| On-time delivery % (OTD) | Lines delivered on or before promised date / delivered lines | G03, no grace period. Low-OTD supplier: < 60%. |
| Lead time | Goods receipt date - PO date (days) | G04 |
| Delivery delay | Delivery date - promised date | > 0 = late |
| Price index vs market | Sum(line value) / Sum(quantity x benchmark price) | 1.00 = market; 0.93 = 7% cheaper |
| Price variance | (Unit price - benchmark price) x quantity | |
| Rejection rate % | Rejected quantity / delivered quantity | |
| Procurement spend | Sum of PO line value | |
| Critical lateness | Goods receipt - need-by date for A-class and steel lines (if > 0) | What actually holds up the project |
| Total cost to project (TCO) | Price saving vs market - (critical lateness days x pass-through x project delay cost per day) | Pass-through 0.73 is estimated from the data |
| Supplier composite score | 40% delivery + 30% price + 30% quality, each as a percentile rank | Weights put delivery first because lateness costs more than price |
| Procurement cycle time (internal) | Sum of PR approval, RFQ issue, quotes and PO, confirmation, wait for inspection, and GRN posting days | Excludes the supplier's manufacturing lead time |

## Risk score

Risk score (0-100) = 35% x cost risk + 30% x schedule risk + 15% x supplier risk + 20% x productivity risk.

| Component | 0 at | 100 at |
|---|---|---|
| Cost risk | Cost variance (actual or forecast) <= 0% | >= +15% |
| Schedule risk | Delay % <= 0 | >= 25% |
| Supplier risk | 0% of critical lines late vs need date | >= 40% |
| Productivity risk | Half site labour efficiency (100% to 75%), half works MH/t (30 to 40) | |

The weights are derived, not chosen. Each is proportional to that component's correlation with margin lost on the 62 completed projects (0.96, 0.75, 0.40, 0.45), normalised and rounded to the nearest 5%. Tiers: Low < 25, Medium 25-45, High 45-65, Critical >= 65. On completed projects the tiers line up with outcomes: average margin lost is 0.2, 6.6, 10.8 and 17.7 pp respectively.

## ROI

| KPI | Formula |
|---|---|
| Net annual benefit | Annual saving - annual running cost |
| Payback period (years) | Upfront investment / net annual benefit: *how fast the money comes back* |
| 3-year ROI % | (3 x annual saving - (investment + 3 x running cost)) / (investment + 3 x running cost): *how much it returns per rupee of total cost* |
| 5-year NPV | -investment + sum over 5 years of net benefit / 1.12^year: *value in today's rupees at a 12% cost of capital* (C12) |
