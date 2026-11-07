# Project Roadmap

> **Status (2026-11-07): build-first mode.** To meet a resume deadline, the whole project was built ahead of the lessons: data, database, SQL, Python analysis, Excel model, Power BI pack and documentation are complete and validated. The **learning phases (2 to 23) now run on the finished project**, explaining each part with the real numbers. Still pending: the Power BI `.pbix` build (needs Power BI service or Windows) and the full Phase 23 interview bank.

The project is built and taught in 23 phases. Every learning phase ends with:

1. What we completed
2. What you learned
3. The business value
4. A self-test (5–10 questions), answered and graded **before** the next learning phase starts

Purely technical work (for example, writing a generator or a loader) may be built ahead of the lesson that explains it. It is never skipped in the teaching.

## Stages at a glance

| Stage | Phases | Purpose |
|---|---|---|
| Understand | 1–3 | Know the business before touching data |
| Build the data | 4–7 | Model, generate, load and clean a realistic dataset |
| Analyse | 8–15 | Answer the which / why questions with SQL and Python |
| Improve and decide | 16–17 | Redesign a process; build business cases with ROI |
| Present | 18–19 | Power BI semantic model and 4-page dashboard |
| Prove and defend | 20–23 | Validate every number, recommend, document, prepare for interviews |

## Phase detail

| # | Phase | What we build | What you learn | Main outputs | Status |
|---|---|---|---|---|---|
| 1 | Business understanding | Company profile, business question, scope, repo skeleton | EPC, contract value, fixed-price vs cost-plus, profit vs margin, LD, cost variance, analyst thinking framework | `docs/learning/PHASE_01_*`, `PROJECT_OVERVIEW.md`, `ASSUMPTIONS.md` | ✅ Built · ⏳ self-test |
| 2 | Industrial / EPC concepts | Lifecycle and cost-structure reference | 7 lifecycle stages, milestones, critical path, cost categories, CAPEX vs OPEX, EBITDA, contribution margin, procurement cycle, productivity vocabulary | `docs/learning/PHASE_02_*` | ⏳ lesson |
| 3 | Business problem definition | Problem statement, KPI tree, success criteria | How to turn a vague question into measurable KPIs | `BUSINESS_PROBLEM.md`, `KPI_DEFINITIONS.md` (v1) | ✅ Built · ⏳ lesson |
| 4 | Data model | Star schema, ERD, grain and keys for every table | Facts vs dimensions, grain, primary and foreign keys, cardinality, why star schema | `DATA_MODEL.md`, `DATA_DICTIONARY.md` (v1) | ✅ Built · ⏳ lesson |
| 5 | Synthetic data generation | Generator with cause-and-effect and injected quality issues | How to make synthetic data behave like real data; NumPy random distributions | `python/data_generation/`, `data/raw/` | ✅ Built · ⏳ lesson |
| 6 | SQL database | PostgreSQL schema, constraints, load scripts | DDL, data types, constraints, indexes, `\copy` | `database/schema.sql`, load script | ✅ Built · ⏳ lesson |
| 7 | Data cleaning | Raw → processed pipeline with a cleaning log | Missing values, duplicates, fuzzy name matching, outliers, pandas basics | `python/cleaning/`, `data/processed/`, `DATA_QUALITY.md` | ✅ Built · ⏳ lesson |
| 8 | SQL analysis | Themed query files | SELECT → JOINs → CTEs → subqueries → window functions | `sql/01_*` … `sql/08_*` | ✅ Built · ⏳ lesson |
| 9 | Python EDA | Distributions, correlations, outliers | groupby, merge, pivot_table, apply, Matplotlib/Seaborn | `python/analysis/`, `reports/figures/` | ✅ Built · ⏳ lesson |
| 10 | Cost analysis | Cost variance by project and category; threshold classes; in-progress forecasts | Cost variance, budget variance, earned-value basics (CPI, EAC) | analysis scripts and SQL | ✅ Built · ⏳ lesson |
| 11 | Profitability analysis | Estimated vs actual profit and margin; margin deterioration | Gross profit, margin, profit variance, why revenue growth ≠ performance | analysis scripts and SQL | ✅ Built · ⏳ lesson |
| 12 | Productivity analysis | Labour productivity, utilisation, downtime, output achievement, defects, cost per unit | Productivity vs efficiency vs utilisation vs capacity vs output | analysis scripts and SQL | ✅ Built · ⏳ lesson |
| 13 | Procurement analysis | Supplier scorecard and total-cost comparison | Lead time, OTD %, price variance, total cost of ownership | analysis scripts and SQL | ✅ Built · ⏳ lesson |
| 14 | Project delay analysis | Planned vs actual duration, stage delays, delay cost | Schedule variance, delay %, critical stages | analysis scripts and SQL | ✅ Built · ⏳ lesson |
| 15 | Root cause analysis and risk score | Cost-driver decomposition, Pareto, risk scoring model | Pareto (80/20), contribution analysis, correlation vs causation, weighting | `python/analysis/`, risk scores | ✅ Built · ⏳ lesson |
| 16 | Process improvement | As-Is / To-Be procurement process with cycle times | Process mapping, bottlenecks, cycle time, value-adding vs non-value-adding steps | `PROCESS_MAP.md` | ✅ Built · ⏳ lesson |
| 17 | ROI / business case | 3+ initiatives with investment, savings, payback, ROI; Excel model | ROI vs payback, NPV basics, sensitivity and scenario analysis, Excel formulas | `ROI_ANALYSIS.md`, `excel/` | ✅ Built · ⏳ lesson |
| 18 | Power BI model | Star-schema upload to the Power BI service (browser), relationships, date table, DAX measures | Cardinality, filter direction, measures vs calculated columns, DAX | `powerbi/dax_measures.md`, `powerbi/data_dictionary.md` | 🟡 Designed (dataset, DAX, layout); .pbix build pending · ⏳ lesson |
| 19 | Power BI dashboard | 4-page dashboard built in the Power BI service, with design spec and click-by-click build guide | Visual choice per business question, layout, drill-through | `powerbi/dashboard_design.md` | 🟡 Designed (dataset, DAX, layout); .pbix build pending · ⏳ lesson |
| 20 | Validation | Automated reconciliation (cost, revenue, profit, procurement, durations) | Why analysts never trust a number they have not reconciled | `database/validation.sql`, `python/validation/` | ✅ Built · ⏳ lesson |
| 21 | Business recommendations | Insights in Observation → Analysis → Root cause → Impact → Recommendation form | Turning analysis into decisions | `BUSINESS_INSIGHTS.md` | ✅ Built · ⏳ lesson |
| 22 | GitHub documentation | Final README, limitations, future version, final audit | Presenting a project to recruiters | `README.md`, `docs/` | ✅ Built · ⏳ lesson |
| 23 | Interview preparation | 325+ questions with answers, mock interview, case studies, resume bullets, TKIL mapping | Defending every number and decision | `docs/interview/` | 🟡 Starter (top 15 questions, resume, pitches) · ⏳ full bank |
