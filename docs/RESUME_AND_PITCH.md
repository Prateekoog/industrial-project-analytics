# Resume Entry and Project Pitches

## Resume entry

**Industrial Project Cost, Productivity & Profitability Analytics** | PostgreSQL, Python (pandas, Matplotlib), Excel, Power BI (DAX) | *Case study on synthetic data, inspired by an EPC engineering-internship role* | github.com/<your-username>/industrial-project-analytics

- Built an end-to-end analytics pipeline for a simulated Indian EPC company (80 projects, ~97K records): designed a PostgreSQL star schema (11 dimensions, 8 fact tables), cleaned ~3,000 injected data-quality issues, and validated every KPI with 83 automated reconciliation checks.
- Quantified a ₹246 Cr (36%) erosion of bid profit across 62 completed projects using cost-variance decomposition, Pareto and root-cause analysis in SQL and Python; traced 67% of cost overruns to labour and material, and 55% of schedule slippage to engineering rework.
- Built ROI/NPV business cases for 4 improvement initiatives in an Excel financial model. Recommended predictive maintenance (₹6.8 Cr 5-year NPV, ~3-month payback) and procurement digitisation (cycle time -36%), and showed a blanket supplier switch would destroy ₹21.5 Cr. Designed a 4-page Power BI dashboard with 40+ DAX measures and a data-derived project risk score.

**Honesty rules for this entry:**
- Always keep "synthetic data" / "case study" visible.
- Say "designed" for the Power BI dashboard until you have built the `.pbix`. Then change it to "built".
- Never say a recommendation "saved" money. It was *estimated*.

### Shorter variants (if space is tight)
- *Two bullets:* combine bullets 1 and 3: "...designed star schema; Excel ROI model; Power BI dashboard design with 40+ DAX measures".
- *One line:* "Industrial EPC cost and productivity analytics case study (PostgreSQL, Python, Excel, Power BI): found the drivers of a 36% bid-profit erosion and built ROI cases for 4 initiatives."

---

## 30-second explanation
"I built an analytics case study of a mid-sized Indian EPC company: one that builds plants for cement, sugar, mining and new-energy clients on fixed-price contracts. The data is synthetic, but I designed it with realistic cause and effect. I modelled it in PostgreSQL, cleaned and validated it in Python, and found that projects delivered 8.3% margin against 13.2% bid. Engineering rework and labour overruns were the main causes. I then built ROI cases and recommended predictive maintenance first, because it pays back in about three months."

## 60-second explanation
"In a fixed-price EPC business, revenue is locked when the contract is signed, so profit is won or lost in execution. I wanted to show how an analyst would find where it is lost.

I simulated 80 projects over five years: purchase orders, daily fabrication logs, machine downtime, timesheets, milestones and billing, around 97,000 records. I added realistic data errors, like duplicate invoices and inconsistent supplier names. I built a star schema in PostgreSQL, cleaned the data with logged rules, and checked that every ledger reconciled to the rupee.

The analysis showed that 36% of bid profit was lost: ₹193 Cr in cost overruns and ₹70 Cr in delay penalties. Two-thirds of the overrun was labour and material, and engineering rework caused over half the delay. One finding I liked: the cheapest suppliers were late half the time, but switching all of them would have cost more than the delays did. The real problem was ordering critical items too late.

I built business cases for four improvements and designed a Power BI dashboard. My recommendation was predictive maintenance first, then procurement digitisation."

## 2-minute explanation
Use the 60-second version, then add:
- **Method:**
  - Every KPI is defined once and gives the same number in SQL, Python, Excel and Power BI.
  - I aggregated each fact table before joining, to avoid double counting.
  - For in-progress projects I used earned value (CPI and EAC) rather than comparing cost-to-date with the full budget.
- **Root cause, not correlation:**
  - Compare projects with and without each symptom, then run a regression so one driver is not credited with another's effect.
  - Every driver also had to have a mechanism I could explain. For example, a late gearbox means the installation crew is idle, then overtime, then liquidated damages.
- **Risk score:**
  - I derived the weights (cost 35%, schedule 30%, productivity 20%, supplier 15%) from how strongly each factor tracked margin loss on completed projects.
  - I checked the score on those projects: the Critical tier lost about 18 points of margin, the Low tier almost none.
  - It flags three live projects now.
- **Validation of the method:** because the data was synthetic, I knew the planted causes, and the analysis recovered all seven unreliable suppliers and all four chronic machines without being told.

## 5-minute deep dive (structure)
1. **Business context (30 s):** EPC, fixed price, why execution decides profit; the ₹100 Cr example (6% overrun plus 8 weeks of LD takes margin from 14% to 5%).
2. **Data and model (60 s):** the 7 lifecycle stages; why budget and actual cost are separate facts (different grains); how the 6x over-count at work-centre level was avoided; the date dimension uses the Indian fiscal year.
3. **Data quality (40 s):** examples of the issues; the "hour balance" identity that caught hidden decimal errors; an honest residual (5 undetectable date swaps).
4. **Findings (90 s):** the profit bridge; labour +13%; new-energy projects lost 13 pp; engineering rework 55% of delay; the supplier nuance (cheap is net cheaper except SUP-008); Works-East is 16% less productive but its cost per tonne looks equal.
5. **Decisions (60 s):** four business cases; why I rank predictive maintenance first despite a lower NPV than the design gate (certainty and speed); why I would *not* switch suppliers; how each result would be measured with a control group.
6. **Limitations (20 s):** synthetic data, assumed costs, no live ERP; what a real implementation would need.

---

## Project title options
- Industrial Project Cost, Productivity & Profitability Analytics *(default)*
- EPC Project Risk & Margin Analytics: SQL, Python, Excel, Power BI
