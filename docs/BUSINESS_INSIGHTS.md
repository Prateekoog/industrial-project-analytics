# Business Insights

Every number below comes from the analysis outputs (`reports/metrics.json`, `reports/tables/`, `sql/results/`). The data is synthetic; the method is what transfers to real data. Each insight follows **Observation → Analysis → Root cause → Business impact → Recommendation**.

---

## 1. Execution gave away 36% of the profit we bid

- **Observation:** On 62 completed projects (₹5,247 Cr revenue), the bid margin was **13.2%** and the delivered margin was **8.3%**. Profit fell from ₹683 Cr planned to ₹437 Cr. 8 projects lost money and 16 earned under 5%.
- **Analysis (profit bridge):**

  | Step | ₹ Cr |
  |---|---|
  | Bid profit | 683 |
  | Change-order profit | +18 |
  | Price variation | −1 |
  | Cost overrun vs revised budget | −193 (4.2%) |
  | Liquidated damages | −70 |
  | **Actual profit** | **437** |

  Cost variance status of completed projects: 6 under budget, 30 on budget, 16 warning, 10 critical (over 10%).
- **Root cause:** cost overruns (78% of the erosion) and delay penalties (28%), partly offset by change orders. Insights 2 to 6 explain each.
- **Business impact:** ₹246 Cr of profit lost over 5 years, about ₹50 Cr a year.
- **Recommendation:** Review every live project monthly on CPI, EAC and the risk score (insight 7), not on revenue billed. Revenue is fixed at the bid; only cost and schedule can still be managed.

## 2. Labour and material drive two-thirds of the overrun, and labour overruns hardest

- **Observation:** Labour overran by **₹67 Cr (+13.2%)** and material by **₹63 Cr (+2.6%)**. Together they are **67%** of the ₹193 Cr overrun. Energy (+9.9%), equipment (+5.2%) and overhead (+4.9%) follow.
- **Analysis:** Labour is only 11% of the budget but overruns by 13% because of three effects that all appear in the data:
  - **Idle site crews** waiting for late critical items, the client or weather.
  - **Overtime at 2x** to catch up.
  - **Works downtime**, which leaves fabrication crews standing.
  
  Material overruns in rupees because it is half of all cost. Its drivers are quantity growth from engineering rework and price movement on steel-linked items.
- **Root cause:** Projects with site labour efficiency under 90% lost **6.5 pp** more margin. Industrial Equipment, the most labour-intensive industry, bid the highest margin (17.3%) yet delivered only 9.6%.
- **Business impact:** Each 1% of labour overrun costs about ₹5 Cr over the portfolio; each 1% of material about ₹24 Cr.
- **Recommendation:** Track site labour efficiency (earned ÷ actual hours) weekly by project. Treat idle hours as a procurement and planning failure, not a labour one. For labour-heavy industries, raise the labour contingency in bids.

## 3. New-energy projects are systematically under-estimated

- **Observation:** On the 7 completed green hydrogen, battery and carbon capture projects, margin fell by **13.3 pp** (bid 15-17%, delivered 2-4%) against **5.0 pp** on mature industries. Average cost variance was 11.0% against 4.3%.
- **Analysis:** These projects had more engineering slip, more quantity growth (bills of material were under-estimated), and longer testing and commissioning ("Technical issues" delays).
- **Root cause:** First-of-a-kind technology risk was priced as a *higher bid margin*, not as *contingency in the cost estimate*. The margin was then consumed by cost.
- **Business impact:** Carbon capture 16.7% to 2.1%; batteries 16.2% to 3.0%; green hydrogen 15.1% to 4.3%. These are the growth segments of the order book.
- **Recommendation:** Add an explicit technology contingency of about **7 percentage points of cost** (the observed CV gap) to new-energy estimates, and pilot the design-freeze gate there first (insight 4).

## 4. Engineering rework is the biggest cause of delay, and delay is expensive

- **Observation:** 59 of 62 completed projects finished late, on average **36 days (7.9%)**: 7 on time, 35 minor, 16 major and 4 critical delays.
- **Analysis:** Of the delay days added by critical-path stages, **engineering rework causes 54.8%**, supplier delay 14.3%, labour productivity 7.0%, client-side 7.0%, technical issues 6.6%, equipment breakdown 5.8% and weather 4.5%. By stage, engineering adds 51% and installation 30%. Delay and cost overrun move together (r = 0.67).
- **Root cause:** Design-basis changes during engineering push back requisitions for steel and critical equipment, which pushes fabrication and installation. Projects whose engineering slipped more than 30 days lost **12.0 pp** of margin against **3.0 pp** for the rest.
- **Business impact:** Delay cost **₹89 Cr**: ₹70 Cr of liquidated damages on 34 projects, plus ₹20 Cr of extra time-based overhead and crane hire. On-time projects delivered a **12.9%** margin; projects with major or critical delays delivered **4.1%**.
- **Recommendation:** A design-freeze stage gate (independent design review before major procurement), first as a pilot. Business case in `ROI_ANALYSIS.md`: NPV ₹13.8 Cr base case, but the most uncertain of the four initiatives.

## 5. The procurement problem is late critical items, not cheap suppliers

- **Observation:**
  - Overall on-time delivery is 76%, and 73% on critical items.
  - 7 suppliers deliver on time only **52%** of the time. They are **7% cheaper** than market and carry 22% of spend.
  - Reliable suppliers deliver on time 91% of the time at 5% above market.
- **Analysis: does a lower price lead to lower total cost?**
  - Mostly, yes. On critical items the 7 low-OTD suppliers saved **₹48.4 Cr** on price and caused **₹23.5 Cr** of lateness cost: each day a critical item is late delays the project by **0.73 days**, at about ₹7.3 L per day.
  - Gearboxes, as a "Supplier A vs B" test: cheap SUP-017 (52% on time, index 0.91) comes out **₹8.1 Cr net ahead**. Reliable SUP-016 (97% on time, index 1.07) is **₹4.4 Cr behind** once its price premium is counted.
  - The exception is **SUP-008** (steel plates, 47% on time). Its lateness cost of ₹13.7 Cr exceeds its ₹8.2 Cr saving.
  - A regression on completed projects (R² = 0.75) confirms the pattern. Holding lateness constant, a higher share of low-OTD suppliers *reduces* margin loss (they are cheaper); critical-item lateness *increases* it.
- **Root cause:** Critical items arrive after their need date (projects where that happened lost **6.5 pp** more margin). This is driven by late requisitions after engineering changes and a slow internal process (34.5 days from requisition to receipt, before the supplier even starts).
- **Business impact:** A blanket switch to the most reliable suppliers would **destroy ₹21.5 Cr** of value (NPV): a ₹9.3 Cr per year premium to avoid ₹3.4 Cr per year of lateness.
- **Recommendation:**
  - Keep the cheaper suppliers, but add delivery-linked penalties and expediting for critical items.
  - Move SUP-008's critical plate orders to another supplier.
  - Fix *when* we order: the digital procurement workflow cuts the internal cycle from 34.5 to 22.2 days (NPV ₹5.6 Cr, payback about 5 months).

## 6. Six machines cause 44% of downtime, and a cost-per-tonne KPI hides it

- **Observation:**
  - Works-East needs **33.5 man-hours per tonne**, 16% more than Works-West (28.9).
  - Its downtime is 8.7% against 2.6%, its rework rate 4.0% against 1.7%, and it is capacity-constrained on **45%** of production days. Plate rolling is the most frequent bottleneck there.
  - Yet its **conversion cost per tonne is the same as Works-West** (₹18,828 vs ₹18,976), because its labour rate is 15% lower.
- **Analysis:**
  - **6 machines (14% of the fleet) cause 43.5% of all unplanned downtime.** They run at 10-19.5% downtime against a fleet median of 3.5%, and four are 20+ years old.
  - Month by month, each extra point of downtime adds 0.66 MH per tonne (r = 0.94).
  - Downtime reason codes are spread evenly across six categories, so the useful cut is *by machine*, not by reason.
- **Root cause:** Ageing bottleneck machines with breakdown (reactive) maintenance.
- **Business impact:** About 5,030 downtime hours a year on those machines, worth about ₹9,100 per hour in idle crew, overtime and repairs. The capacity lost at the bottleneck also delays fabrication.
- **Recommendation:**
  - Predictive maintenance on the 6 machines: investment ₹55 L, payback about 3 months, NPV ₹6.8 Cr. **Implement first.**
  - Report productivity in man-hours per tonne alongside cost per tonne. A cost KPI alone hid this problem.

## 7. Three live projects need intervention now

- **Observation:** 16 of 18 in-progress projects have a **CPI below 1** (spending ahead of progress), with a forecast overrun of **₹91 Cr** if nothing changes. 17 are already slipping.
- **Analysis:** The risk score uses weights derived from the 62 completed projects: cost 35%, schedule 30%, productivity 20%, supplier 15%. It separates outcomes cleanly. Completed projects in the Low tier lost 0.2 pp of margin; Medium 6.6 pp; High 10.8 pp; Critical 17.7 pp.
- **The three critical-risk projects:**

  | Project | Industry | % complete | CPI | Forecast cost variance | Slip | Forecast margin vs bid |
  |---|---|---|---|---|---|---|
  | PRJ-072 | Wastewater Treatment | 78% | 0.87 | +15.2% | 87 days | −1.0% vs 12.3% |
  | PRJ-073 | Mining & Material Handling | 66% | 0.87 | +14.3% | 83 days | 1.4% vs 13.8% |
  | PRJ-074 | Industrial Batteries | 41% | 0.88 | +13.1% | 122 days | 6.7% vs 17.6% |

- **Recommendation:** Hold recovery reviews on these three this month. PRJ-074 is only 41% complete, so it has the most room to recover. Agree client-side delays formally, to avoid liquidated damages on excusable delay.

## 8. The price-variation clause did not protect margin in this period

- **Observation:** The 22 projects with a steel price-variation clause (PVC) had *higher* average cost variance (6.1% vs 4.5%), and PVC billing netted **−₹1.2 Cr**: money returned to clients.
- **Analysis:** Many PVC projects were awarded near the 2022 steel peak and bought steel after prices fell, so the clause passed the saving to the client. PVC is a two-way risk-sharing tool, not a margin lever. It reduces exposure to price swings in both directions.
- **Recommendation:** Use PVC to cap downside risk on long, steel-heavy contracts awarded when prices are low. Do not count it as a margin protection when steel is near a peak. Structural steel is the most volatile material group (coefficient of variation 9.2%).

---

## Does the method actually work? (validation on known causes)

The data is synthetic, so the true causes are known (hidden files in `data/qa/`). The analysis never reads them. Afterwards, its findings were compared with the truth:

| Planted cause | Did the analysis find it? |
|---|---|
| 7 "cheap but late" suppliers | All 7 found by OTD < 60% (no false positives) |
| 4 chronically unreliable machines | All 4 found, plus 2 "poor" machines also above 10% downtime |
| Design-basis changes on 17 completed projects | Found as "engineering slip > 30 days" (+8.9 pp margin loss; true effect +9.6 pp) |
| Quality-problem suppliers | Visible in the scorecard: about 8% rejection vs under 0.4% for the others |

This is the honest answer to "why should I trust synthetic data?": the data was built with known causes, and the analysis recovered them without being told what they were.
