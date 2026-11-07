# Assumptions Register

Every number in this project rests on assumptions. This file records each major one, the value chosen, **why** it was chosen, and where it is used, so that any figure can be challenged and traced.

**Ground rules**

- All data is synthetic. The company (ProjectCo), its clients, suppliers and employees are fictional.
- Values marked *plausible synthetic* are realistic in shape and order of magnitude but are **not** sourced market data. Do not quote them as industry facts in an interview.
- When a later phase changes an assumption, the change is recorded in the change log at the bottom, not silently overwritten.

---

## A. Scope and positioning

| ID | Assumption | Why | Used in |
|---|---|---|---|
| A01 | The project is "an industrial operations analytics case study inspired by the business problems and responsibilities described in an Engineering Internship role at TKIL Industries." | Honest positioning. Inspired by a job description, not built on company data. | README, interviews |
| A02 | No TKIL data, projects, clients or systems are used or implied. Industry categories come from the kinds of industries named in the role context. | Avoids misrepresentation. | Everywhere |
| A03 | The analysis supports management decisions (which projects need attention, which suppliers to keep, which improvement to fund). It is not statutory accounting. | Defines the level of financial precision required. | Phases 10–17 |
| A04 | Machine learning is out of scope for the core project. | Descriptive, diagnostic and prescriptive analysis fully answers the business question. ML is discussed as future work. | Phase 22 |

## B. Company and portfolio

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| B01 | Company profile | ProjectCo, a fictional mid-sized Indian heavy-engineering and EPC company | Matches the business context of the role without imitating any real company | All |
| B02 | Analysis window | Project starts from Apr 2021 (FY22) to Sep 2025. Data cut-off 31 Mar 2026 (end of FY26). | Five fiscal years give trends and cover a full commodity price cycle. A fiscal-year-end cut-off matches how management reviews performance. | Generator, date table |
| B03 | Portfolio size and status | 80 projects: 62 completed and 18 in progress at cut-off (as generated) | Within the brief's 50–100 range. About 8 per industry allows comparison while each project stays explainable. In-progress projects are where management can still act. | All |
| B04 | Industry mix (project count) | Sugar 12, Cement 12, Mining & Material Handling 12, Industrial Equipment 10, Thermal Energy 8, Wastewater Treatment 8, Biochemicals 6, Green Hydrogen 5, Industrial Batteries 4, Carbon Capture 3 | Established industries make up most of the order book. New-energy segments are emerging: fewer projects, higher technical risk. | Generator |
| B05 | Contract value distribution | ₹15 Cr to ₹450 Cr, right-skewed (log-normal), median about ₹70 Cr | Project businesses have many mid-sized and a few very large contracts. The skew is deliberate: it teaches why the median is often better than the mean. | Generator, EDA |
| B06 | Planned duration | 10 to 36 months, increasing with contract value and technical complexity | Larger and first-of-a-kind plants take longer | Milestones |
| B07 | Locations | 3 fabrication works (Works-West near Pune, Works-East near Kolkata, Works-South near Chennai). Fabrication is assigned by a planning rule: the works with the least committed load over the project's fabrication window, preferring the home-region works; Works-East is loaded 15% lighter because planners know it breaks down more. Project sites are in states where each industry clusters, e.g. sugar in Maharashtra, Uttar Pradesh, Karnataka; cement in Rajasthan, Madhya Pradesh, Andhra Pradesh; mining in Jharkhand, Odisha, Chhattisgarh; green hydrogen in Gujarat, Rajasthan. | Gives realistic geography for transport cost and regional comparisons | dim_location |
| B08 | Project managers | 12 PMs with different track records | Enables a classic confounding question: is performance driven by the PM or by the type of project they are given? | Phase 15 |
| B09 | Clients | 37 fictional client companies, some with repeat projects | Repeat clients allow client-level profitability analysis | dim_client |
| B10 | Names | All names are invented. Employee names are generated combinations of common Indian first and last names and do not refer to real people. No real brand names are used for suppliers or clients. | Avoids implying real relationships | Generator |

## C. Commercial and financial

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| C01 | Currency and storage | INR. Stored as full rupees (`NUMERIC(18,2)`); presented in ₹ Lakh / ₹ Crore | Full rupees avoid rounding errors; Lakh/Crore is how Indian management reads numbers | All |
| C02 | Fiscal year | April to March. The label is the year in which the FY ends (FY25 = Apr 2024 to Mar 2025). | Indian reporting convention | dim_date |
| C03 | Taxes | All figures exclude GST | GST is collected on behalf of the government and passed through. Including it would inflate revenue and cost equally and distort margin. | All financials |
| C04 | Contract type | All contracts are fixed-price (lump-sum). About 35% include a steel price-variation clause (PVC) that passes part of steel price movement to the client. | Fixed-price means the contractor carries overrun risk, which is why cost variance matters. PVC lets us test whether projects without price protection suffer more from steel inflation. | dim_project, fact_revenue |
| C05 | Revenue formula | `Final Revenue = Contract Value + Approved Change Orders + PVC Adjustments − Liquidated Damages` | Reflects how project revenue actually moves after signing | fact_revenue, validation |
| C06 | Change orders | About 40% of projects receive approved change orders worth 2–8% of contract value, priced at the project's bid margin | Clients commonly add or modify scope mid-project | fact_revenue |
| C07 | Revised budget | `Revised Budget = Original Estimated Cost + Estimated Cost of Approved Change Orders`. Cost variance is measured against the revised budget. | Client-requested extra scope should not be counted as a cost overrun. Measuring against the original budget would blame the project team for work the client asked for and paid for. | Phase 10 |
| C08 | Liquidated damages (LD) | 0.5% of contract value per week (or part week) of contractor-attributable delay, capped at 5% of contract value, applied only when that delay exceeds a 14-day grace period. Delays caused by the client (late kick-off, site not ready) or weather extend the deadline and attract no LD. | A common LD structure in Indian EPC contracts. Real contracts vary (0.5–1% per week, caps of 5–10%). | Phases 11, 14 |
| C09 | Profit definition | Project profit = project revenue − all project costs, including allocated overhead. Analysed over the whole project life, not by accounting period (Ind AS 115 revenue recognition is out of scope). Monthly revenue trends use invoice dates. | Management judges a project on its whole-life economics. Period accounting would add complexity without changing any decision this project supports. | Phase 11 |
| C10 | Bid (estimated) margin by industry, *plausible synthetic* | Thermal 8–12%, Cement 10–14%, Sugar 11–15%, Wastewater 11–15%, Mining & MH 12–16%, Biochemicals 12–16%, Industrial Batteries 13–18%, Green Hydrogen 14–19%, Industrial Equipment 15–20%, Carbon Capture 15–20% | Mature, competitive segments bid tighter. Equipment supply carries less site risk and more proprietary engineering. First-of-a-kind technologies carry a risk premium. | Generator |
| C11 | Steel price movement, *plausible synthetic* | A synthetic steel price index that rises about 30% from Apr 2021 to mid-2022, eases about 15% by end-2023, then stays roughly flat | Shaped like the 2021–22 commodity spike so that material cost volatility exists in the data. It is not actual market data. | Procurement prices |
| C12 | Discount rate for business cases | 12% per year | A typical cost of capital for an Indian industrial company. Used only for NPV in Phase 17. | Phase 17 |

## D. Project lifecycle and schedule

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| D01 | Lifecycle stages | Concept → Engineering → Procurement → Fabrication → Installation → Testing → Commissioning | Standard industrial project lifecycle; explained in Phase 2 | fact_milestones |
| D02 | Stage overlap | Stages overlap ("fast-tracking"). Procurement starts during engineering; fabrication starts before all procurement is complete. | This is how EPC schedules are compressed in practice. It also means stage durations do not simply add up to project duration. | Milestones |
| D03 | Delay propagation | A stage delay passes to the next stage, minus any slack (float) in the schedule | Not every delay moves the completion date. This lets us identify which stages are critical. | Phase 14 |
| D04 | Delay causes | Supplier delay, engineering rework, equipment breakdown, labour shortage or productivity, client-side (site not ready, approvals), weather / force majeure | Covers the main controllable and uncontrollable causes. Client-side and force-majeure delays carry no LD (C08). | Phase 14 |
| D05 | Contractual completion date | Planned end of the Commissioning stage | The date the LD clause measures against | Phase 14 |
| D06 | Stage gating | Fabrication starts when 60% of steel has been received and drawings allow. Installation can start once 40% of fabrication is done. Critical (A-class) items are requisitioned late in engineering (45-90% through) because their specifications freeze late; installation then needs 55% of its planned duration after the last critical item arrives. | Makes supplier lateness on critical items a real cause of project delay | Generator, Phase 13 |
| D07 | Design-basis changes | 12% of mature projects and up to 42% of new-technology projects hit a mid-engineering design change: long engineering slip, extra rework hours and bill-of-material growth | Creates the "multiple problems at once" projects real portfolios contain | Generator, Phase 15 |
| D08 | Estimating error | Bills of material carry a random estimating error (standard deviation 6%), biased upwards by 8% for new technologies | First-of-a-kind plants are harder to estimate | Generator |

## E. Cost structure

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| E01 | Cost categories and typical planned share of project cost, *plausible synthetic* | Material and bought-out equipment 45–55%; Subcontractor 10–16%; Labour 9–13%; Overhead 6–9%; Equipment (machinery and cranes) 4–7%; Transportation 3–5%; Other (insurance, guarantees, testing) 2–4%; Energy 1–3% | Equipment-heavy EPC is material-dominated. Shares shift by industry, e.g. wastewater has more civil subcontracting; industrial equipment has more works labour. | fact_project_cost |
| E02 | Overhead behaviour | Part of overhead is time-based (site establishment and supervision cost per month); the rest is allocated works and head-office overhead | Time-based overhead is the mechanism by which delay raises cost | Generator, Phase 14 |
| E03 | Labour rates (fully loaded), *plausible synthetic* | Works direct labour ₹300–450 per hour; site labour ₹2,200–3,200 per worker-day; engineers ₹900–1,600 per hour | Fully loaded rates include wages, benefits and statutory costs | fact_labor |
| E04 | Overtime premium | 2× the ordinary hourly rate | Indian labour law requires overtime at twice the ordinary wage rate (Factories Act, 1948, Section 59; the same rule continues under the Occupational Safety, Health and Working Conditions Code, 2020) | fact_labor |
| E05 | Energy tariff, *plausible synthetic* | ₹7.6 per kWh in FY22, rising about 3% a year | Typical order of magnitude for Indian industrial power tariffs | Energy cost |
| E06 | Labour budget split | Works fabrication 35%, site erection 45%, engineering 20% of the labour budget. Fabricated tonnes = works labour budget / (works rate x 30 MH/t). | Ties physical quantities to the budget so that variances arise from productivity, not inconsistent inputs | Generator |
| E07 | Delay cost per day | Time-based cost (60% of overhead + 50% of equipment budget) / planned days, plus LD accrual of 0.5% of contract value / 7 | Used in total-cost-of-ownership and ROI cases; LD accrual applies only to contractor-caused delay | Phases 13, 17 |

## F. Works operations (fabrication)

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| F01 | Works structure | 3 works, each with work centres for cutting, plate rolling, welding, machining, assembly, and blasting & painting; 42 major machines in total, about 90 t/day bottleneck capacity per works | Typical heavy-fabrication shop layout | dim_equipment |
| F02 | Shift pattern | 2 shifts × 8 hours, 6 days a week (Sunday off), closed on national holidays. About 300 working days a year, 16 scheduled hours per machine per working day. | Common pattern for Indian fabrication works | fact_operations, fact_equipment |
| F03 | Time definitions | Available hours = scheduled hours − planned maintenance. Downtime = unplanned stoppages. Operating hours = available hours − downtime − idle (no work loaded). | Separates "machine broken" from "no work". Mixing the two is the most common utilisation mistake. Explained in Phase 12. | Phase 12 |
| F04 | Output unit | Tonnes (MT) of fabricated equipment and structure. Labour productivity expressed as man-hours per tonne (MH/MT, lower is better) and tonnes per 100 man-hours (higher is better). Typical range 20–60 MH/MT depending on complexity, *plausible synthetic*. | MH/MT is how fabrication shops measure labour productivity | Phase 12 |
| F05 | Quality | Defect rate = tonnes needing rework at inspection ÷ tonnes inspected. Good shops run about 1–3%; above 5% indicates a problem. *Plausible synthetic.* | Rework consumes labour and machine hours a second time | Phase 12 |
| F06 | Problem machines | A minority of machines (ageing or poorly maintained) have chronic unplanned downtime, which lowers output and raises overtime and cost per tonne | Creates the downtime → productivity → cost chain that the analysis must find | Phases 12, 15 |

## G. Procurement

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| G01 | Supplier base | 40 fictional suppliers across 12 material groups (structural steel, plates, pipes and fittings, castings and forgings, gearboxes, motors, bearings, valves, pumps, electrical and cables, instrumentation, refractory). 94 materials. | Realistic breadth for an equipment EPC company | dim_supplier, dim_material |
| G02 | Hidden supplier behaviour | Suppliers follow hidden archetypes: reliable-premium, average, cheap-but-late, quality-problem, price-volatile. The archetype is **not** stored in the analysis data. | The analysis must discover supplier behaviour from transactions, as a real analyst would | Phase 13 |
| G03 | On-time delivery | A delivery is on time if received on or before the supplier's committed date. No grace period. | Strict and simple. Some companies allow a grace window; this is noted as a sensitivity in Phase 13. | Phase 13 |
| G04 | Lead time | Calendar days from purchase order date to goods receipt date | Standard procurement definition | Phase 13 |
| G05 | Procurement process steps | Purchase requisition → approval → RFQ and quotes → purchase order → supplier confirmation → delivery → inspection → goods receipt. Step timestamps are recorded so cycle time per step can be measured. | Needed for the As-Is / To-Be analysis | Phase 16 |

## H. Classification thresholds

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| H01 | Cost variance status | Under budget: CV% < −2%. On budget: −2% to +5%. Warning: +5% to +10%. Critical: > +10%. | Derived from margin erosion, not picked by habit. At a typical 14% bid margin, a +5% overrun removes about 4.3 margin points (about a third of profit); +10% removes about 8.6 points (most of it). Underruns beyond −2% are flagged too, because systematic over-estimation makes bids uncompetitive. | Phase 10 |
| H02 | Schedule delay status (preliminary) | On time: delay ≤ 2% of planned duration. Minor: 2–10%. Major: 10–20%. Critical: > 20%. | Will be checked against the LD cost of each band in Phase 14 | Phase 14 |
| H03 | Risk score | Four components (cost, schedule, supplier, productivity) scaled 0-100. Weights are proportional to each component's correlation with margin lost on completed projects, rounded to 5%: **cost 35%, schedule 30%, productivity 20%, supplier 15%**. Tiers: Low < 25, Medium 25-45, High 45-65, Critical >= 65. Margin is excluded because it is the outcome the score predicts. | Weights chosen by feel cannot be defended in an interview; the tiers are validated against completed-project outcomes | Phase 15 |

## I. Data quality

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| I01 | Injected issues | Raw extracts contain deliberate problems at controlled rates (roughly 1–3% of rows per issue type): duplicate records; inconsistent supplier names (case, abbreviations, "Pvt Ltd" vs "Private Limited"); missing values; date errors (delivery before order, swapped day and month); outliers (an extra zero); invalid values (negative quantities); zero values; wrong categories (typos, legacy codes) | Real source systems are messy. Clean synthetic data would make the cleaning phase meaningless. | Phases 5, 7 |
| I02 | Answer key | The generator logs every issue it injects to a separate file that the cleaning code never reads | Lets us measure objectively how many issues the cleaning pipeline found and fixed | Phase 7 |

## J. Tools and environment

| ID | Assumption | Value | Why | Used in |
|---|---|---|---|---|
| J01 | Database | PostgreSQL 15 (local). SQL kept compatible with PostgreSQL 13+. | Open source, standard SQL, strong window-function support | database/, sql/ |
| J02 | Python | Python 3.13 with pandas, NumPy, Matplotlib, Seaborn, openpyxl. No heavier frameworks. | Every library has a clear job; nothing is added to look impressive | python/ |
| J03 | Excel | The installed Excel for Mac (16.97) does **not** support XLOOKUP (perpetual licence). Every XLOOKUP is wrapped as `IFERROR(XLOOKUP(...), INDEX/MATCH)`, so the model works in both old and Microsoft 365 Excel. Functions added in Excel 2010 (RANK.EQ, PERCENTRANK.INC) are stored with the `_xlfn.` prefix. Excel for Mac has no Power Pivot, so the model uses formulas, PivotTables and What-If tools. | Verified by opening and recalculating the workbook in the installed Excel | excel/ |
| J04 | Power BI path | **Status: open, to be settled before Phase 18.** Everything Power BI needs (data workbook, DAX measures, layout spec, click-by-click build guide) is prepared on the Mac first, so the build itself takes one focused session of about 3–4 hours. Options, in order of preference: (1) the Power BI service in the browser, if a college email turns out to work with Microsoft (a 2-minute check); (2) one session on any Windows PC, such as a college lab or a friend's laptop (the Microsoft Store version of Power BI Desktop usually installs without admin rights); (3) a cloud Windows VM on an Azure free account, with sign-up and card verification done by the user; (4) a local Windows VM, only after freeing about 30 GB of disk. | The development machine is an Apple M1 Mac (8 GB RAM, about 23 GB free disk) with no Windows PC and no confirmed work or school Microsoft account. Power BI Desktop is Windows-only, and the Power BI service needs a work or school account. Preparing everything in advance keeps the Power BI step short and lets it move to whichever machine is available. | powerbi/ |
| J05 | Reproducibility | Fixed random seed (42). One command regenerates every dataset. | Anyone can reproduce every number | Generator |
| J06 | Data volume (as generated) | 80 projects; 40 suppliers; 94 materials; 84 staff (contract workers are crew-level, not individuals); 42 machines; 560 milestones; 4,439 PO lines; 8,835 ledger postings; 13,396 works production days; 64,848 machine-days; 3,787 timesheet-weeks; 510 invoices | Large enough to be credible and to need SQL and pandas; small enough to fit comfortably in Excel (1,048,576-row limit) and Power BI import mode | Generator |
| J07 | Power BI data delivery | Analysis-ready star-schema tables are delivered as CSVs **and** as one Excel workbook with one named Table per star-schema table. The date dimension is generated in Python, not with DAX. Power BI reads files, not the local PostgreSQL database. | One workbook uploads to the Power BI service as a single multi-table semantic model and also loads in Desktop. A Python-built date table avoids depending on any feature that differs between the web and Desktop. The service cannot reach a database running on a laptop without a gateway. | data/processed/, powerbi/ |

## K. Business-case assumptions (Phase 17)

Benefits are measured from the data; the costs and effectiveness below are assumptions, tested at low / base / high.

| ID | Initiative | Assumption | Low / Base / High |
|---|---|---|---|
| K01 | Predictive maintenance | Sensors ₹5 L per machine + ₹25 L platform; ₹10 L per year running; ₹25,000 repair cost per breakdown; 3-person crew, 60% idle while down | Downtime reduction 15% / 35% / 50% |
| K02 | Digital procurement | ₹70 L implementation, ₹20 L per year licences; 1.5 buyer hours saved per PO line at ₹1,000 per hour | Share of best-quartile target achieved 50% / 80% / 100% |
| K03 | Supplier switch | ₹15 L qualification; price premium = gap to the group's most reliable supplier | Lateness avoided 50% / 75% / 90% |
| K04 | Design-freeze gate | ₹20 L set-up; ₹1.2 Cr per year review team; 7 review days added to every new project; benefit halved for confounding | Design changes prevented 10% / 25% / 40% |
| K05 | Run-rate window | Annual figures use the average of FY25 and FY26 | n/a |

---

## Change log

| Date | Phase | Change |
|---|---|---|
| 2026-11-06 | 1 | Initial register created |
| 2026-11-06 | 1 | No Windows access confirmed. J04 changed from "build `.pbix` on Windows" to "Power BI service in the browser" as the primary path. J03 notes Excel for Mac limits. J07 added (file-based Power BI data delivery, Python-built date table). |
| 2026-11-06 | 1 | No confirmed work or school Microsoft account either. J04 reopened: options ranked, and the Power BI build redesigned as one prepared 3–4 hour session on whichever platform is available. |
| 2026-11-07 | Build | Build-first mode at the user's request (resume deadline). Values updated to the generated data (B03, B07, B09, F01, G01, J06). Added C08 14-day LD grace period, D06-D08 (stage gating, design changes, estimating error), E06-E07 (labour split, delay cost per day), section K (business-case assumptions). H03 weights now derived (35/30/20/15). J03 updated after verifying the workbook in the installed Excel. |
