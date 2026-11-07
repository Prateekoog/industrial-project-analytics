# ROI Analysis: Improvement Business Cases

Source: `python/analysis/roi_business_case.py`. The live Excel version, with a scenario switch and a sensitivity grid, is the `ROI_Model` sheet in `excel/project_financial_model.xlsx`.

## Definitions (and why ROI is not payback)

| Measure | Formula | Answers |
|---|---|---|
| Net annual benefit | Annual saving - annual running cost | How much better off each year |
| **Payback** | Upfront investment / net annual benefit | *How fast* the cash comes back (a liquidity and risk lens) |
| **3-year ROI** | (3-yr saving - 3-yr total cost) / 3-yr total cost, where total cost = investment + 3 x running cost | *How much* it returns per rupee spent |
| **5-year NPV** | -investment + sum of net benefit / 1.12^t, for t = 1 to 5 | Value created in today's rupees at a 12% cost of capital |

Payback ignores everything after the money is back and ignores the size of the prize; ROI ignores timing; NPV captures both. A small fix can pay back in weeks yet create less value than a larger one.

**What is computed vs assumed.** Every *benefit driver* is measured from the dataset: downtime hours, delay days, lateness, price premiums. Every *cost* and every *effectiveness* figure is an assumption. Each is listed below and tested at low, base and high values. None of these costs come from vendor quotes.

## The four initiatives (base case)

| Initiative | Investment | Annual saving | Running cost / yr | Net benefit / yr | Payback | 3-yr ROI | 5-yr NPV (low - base - high) |
|---|---|---|---|---|---|---|---|
| Design-freeze stage gate | ₹0.20 Cr | ₹6.10 Cr | ₹2.20 Cr | ₹3.89 Cr | < 1 month | 169% | ₹0.7 - **13.8** - 27.0 Cr |
| Predictive maintenance on 6 chronic machines | ₹0.55 Cr | ₹2.13 Cr | ₹0.10 Cr | ₹2.03 Cr | ~3 months | 652% | ₹2.4 - **6.8** - 10.1 Cr |
| Digital procurement workflow | ₹0.70 Cr | ₹1.94 Cr | ₹0.20 Cr | ₹1.74 Cr | ~5 months | 348% | ₹3.0 - **5.6** - 7.3 Cr |
| Blanket switch to most-reliable suppliers | ₹0.15 Cr | ₹3.41 Cr | ₹9.33 Cr price premium | -₹5.92 Cr | never | -64% | -₹25.6 - **-21.5** - -19.0 Cr |

### 1. Predictive maintenance on chronic machines
- **Evidence:** 6 machines (14% of the fleet) cause 43.5% of all unplanned downtime. They run 10-19.5% downtime against a fleet median of 3.5%, and four of them are 20+ years old. In FY25-FY26 they lost about 5,030 hours a year over about 600 breakdowns. Monthly data shows each extra point of downtime adds 0.66 man-hours per tonne (r = 0.94).
- **Value per downtime hour (₹9,100):** idle crew (3 workers x 60% not redeployable x labour rate), plus the overtime premium needed to recover lost output on capacity-constrained days, plus ₹25,000 repair cost per breakdown event.
- **Assumptions:** sensors ₹5 L per machine plus ₹25 L platform; ₹10 L per year running cost; **downtime reduction 35% base (15% low, 50% high)**. Sensitivity: even at a 10% reduction it pays back in about 13 months (Excel `ROI_Model` grid).
- **Excluded upside:** schedule benefit on the Works-East bottleneck, which is constrained on 45% of production days.

### 2. Digital procurement workflow
- **Evidence:** internal cycle of 34.5 days; the To-Be best-quartile benchmark is 22.2 days (`PROCESS_MAP.md`). Applying the saving to critical items avoids 183 project-delay days historically, worth ₹2.3 Cr per year at run-rate.
- **Assumptions:** ₹70 L implementation, ₹20 L per year licences; 1.5 buyer hours saved per PO line at ₹1,000 per hour; **80% of the target achieved (50% low, 100% high)**.
- **Why it is robust:** it has the narrowest NPV range of the three positive cases. Even the low case is worth ₹3.0 Cr.

### 3. Design-freeze stage gate (independent design review before major procurement)
- **Evidence:** engineering rework is the top delay cause (54.8% of added delay days). Projects whose engineering slipped more than 30 days lost 12.0 pp of margin against 3.0 pp for the rest (+8.9 pp).
- **Benefit logic:** the excess margin loss on affected projects' revenue, **halved** to allow for confounding (new-energy projects both slip more and lose more for other reasons), times the **share of design changes prevented: 25% base (10% low, 40% high)**.
- **Costs:** ₹1.2 Cr per year review team, plus 7 extra engineering days on every new project at its time-based cost (about ₹1.0 Cr per year), plus ₹20 L set-up.
- **Caution:** it has the largest NPV but the widest range. The low case is only just positive (₹0.7 Cr). This is the case most dependent on an assumption the data cannot test.

### 4. Blanket supplier switch: rejected by the data
- Moving all critical-item spend from cheaper suppliers to the most reliable one in each group costs a **₹9.3 Cr per year price premium** to avoid **₹3.4 Cr per year of lateness cost**, and its NPV is negative in every scenario.
- The supplier analysis shows why. In aggregate, the 7 low-OTD suppliers saved ₹48.4 Cr on price against ₹23.5 Cr of lateness cost. The problem is *lateness on specific critical items*, not cheap suppliers as such.
- Only SUP-008 (steel plates, 47% on time) costs more in lateness (₹13.7 Cr) than it saves (₹8.2 Cr).

## Recommendation: what to do first

| Order | Initiative | Why this order |
|---|---|---|
| **1. Implement now** | Predictive maintenance (6 machines) | Fastest payback (~3 months), smallest investment, positive even in the low case, contained to one works, and measurable within one quarter (downtime % per machine). A quick win that funds the next step. |
| **2. Implement next** | Digital procurement workflow | Most certain benefit (narrowest NPV range); payback ~5 months; targets the step with the largest internal delay. 3-6 month implementation. |
| **3. Pilot, then decide** | Design-freeze stage gate | Largest prize (₹13.8 Cr NPV) but most uncertain. Pilot it on the next 3 new-energy projects, where design changes are most frequent, and measure the engineering-slip rate before scaling. |
| **Do not do** | Blanket supplier switch | Destroys ₹21.5 Cr of value. Instead, for critical items with low-OTD suppliers, add delivery-linked penalties and expediting, and move SUP-008's critical plate orders. |

Together the three positive initiatives are worth about **₹7.7 Cr per year net** (base case). The ranking is not simply by NPV: certainty and speed of payback are weighed alongside size, as a management committee would.

## How the result will be measured
- **Predictive maintenance:** downtime % per targeted machine, monthly, against its FY25-FY26 baseline; MH per tonne at Works-East.
- **Digital procurement:** internal cycle time per PO line (target 22 days); share of critical lines arriving after their need date.
- **Design gate:** share of projects with engineering slip over 30 days (baseline 32%); margin deterioration of pilot vs non-pilot projects.
- Comparison method: before/after with a control group (non-target machines, non-pilot projects), so a general improvement is not credited to the initiative.
