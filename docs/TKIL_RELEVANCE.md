# Why This Project Is Relevant to the TKIL Engineering Internship

This is a case study **inspired by** the responsibilities in the TKIL Industries Engineering Internship description. It uses no TKIL data and makes no claim about TKIL's projects or systems. The table maps each responsibility to concrete evidence in this repository.

| Job-description area | What I did in this project | Evidence |
|---|---|---|
| **Cost optimisation** | Cost variance by project and by 8 cost categories; profit bridge; Pareto of overrun rupees (labour + material = 67%) | `sql/02_cost_analysis.sql`, `python/analysis/cost_profitability.py`, BUSINESS_INSIGHTS 1-2 |
| **Productivity enhancement** | Man-hours per tonne, labour efficiency, machine utilisation, downtime, output achievement, defect rate; downtime-to-productivity relationship (0.66 MH/t per point) | `sql/04_productivity.sql`, `python/analysis/productivity.py`, BUSINESS_INSIGHTS 6 |
| **Process improvement** | Measured the As-Is procurement cycle from timestamps; designed a To-Be process using best-quartile benchmarks (-36% internal cycle time) | `docs/PROCESS_MAP.md` |
| **Process mapping / As-Is and To-Be** | Mermaid process maps with cycle time per step, value-adding vs waiting steps, bottleneck identification | `docs/PROCESS_MAP.md` |
| **Data-driven analysis** | 97K-record star schema; 8 themed SQL files; Python EDA, correlations, regression; 83 automated validation checks | `sql/`, `python/`, `data/qa/validation_report.csv` |
| **Product / process cost analysis** | Conversion cost per tonne by works; cost per tonne vs MH per tonne (shows why a cost KPI alone can hide productivity loss) | `reports/tables/works_scorecard.csv` |
| **Profitability analysis** | Estimated vs actual profit and margin for 80 projects; margin deterioration by industry and PM; PVC impact | `sql/03_profitability.sql`, Excel `Profitability` sheet |
| **Financial modelling** | Excel model with live formulas (XLOOKUP, INDEX/MATCH, SUMIFS, NPV, scenario switch, what-if); earned value (CPI, EAC) forecasts for live projects | `excel/project_financial_model.xlsx` |
| **Feasibility studies / business cases** | Four initiatives with investment, savings, running cost; low/base/high scenarios; a negative case rejected on the evidence | `docs/ROI_ANALYSIS.md` |
| **ROI analysis** | Payback vs ROI vs NPV, defined and calculated separately; sensitivity grid and break-even | `python/analysis/roi_business_case.py`, Excel `ROI_Model` |
| **Investment decisions** | Ranked initiatives by NPV, payback *and* certainty; recommended an order (predictive maintenance, then digital procurement, then a design-gate pilot) | `docs/ROI_ANALYSIS.md` |
| **End-to-end project management** | 23-phase roadmap; 7-stage project lifecycle model; milestone delay analysis; assumptions register with change log | `docs/ROADMAP.md`, `docs/ASSUMPTIONS.md`, `sql/06_project_delays.sql` |
| **Manufacturing / plant operations** | Simulated 3 fabrication works with 42 machines, shifts, planned maintenance, breakdowns, bottlenecks, overtime | `python/data_generation/generate_data.py`, `fact_operations`, `fact_equipment` |
| **Digital transformation** | Business case for digital procurement (e-approval, e-RFQ, supplier portal, mobile GRN) and predictive maintenance (sensors + CMMS); Power BI decision dashboard | `docs/ROI_ANALYSIS.md`, `powerbi/` |
| **Market / business analysis** | Industry-level profitability across 10 industrial segments (sugar, cement, mining, thermal, new energy); new-energy under-estimation finding | BUSINESS_INSIGHTS 3 |
| **Supplier / procurement analysis** | Supplier scorecard, total cost of ownership, "cheaper vs more reliable" analysis with data | `sql/05_procurement.sql`, BUSINESS_INSIGHTS 5 |
| **Risk management** | Data-derived project risk score, validated on completed projects; watch list of 3 live projects | `python/analysis/root_cause_risk.py`, BUSINESS_INSIGHTS 7 |
| **Reporting to management** | 4-page dashboard design, executive insights in Observation → Root cause → Impact → Recommendation format | `powerbi/dashboard_design.md`, `docs/BUSINESS_INSIGHTS.md` |

## How to say it in the interview
"The role talks about cost optimisation, productivity, process improvement and ROI for plant and project operations. I built a case study that does exactly that on simulated EPC data. I found where margin was lost, traced it to root causes, redesigned a process with measured cycle times, and built business cases with payback and NPV. I used synthetic data because real project costs are confidential. The method (data model, cleaning, validation, analysis, business case) is what I'd bring to TKIL's real data."
