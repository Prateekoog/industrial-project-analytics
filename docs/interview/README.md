# Interview Preparation

The full question bank comes in Phase 23 of the roadmap: 325+ questions across five levels, each with short, strong and deep answers, follow-ups and "what not to say", plus a mock-interview mode and case studies. It is built *after* the learning phases so the answers are yours, not memorised.

Until then, these are the **15 questions you must be able to answer before any interview**, with where the answer lives.

| # | Question | Core of the answer | Read |
|---|---|---|---|
| 1 | Walk me through your project. | Use the 60-second pitch | RESUME_AND_PITCH.md |
| 2 | Is this real data? Why should I trust it? | Synthetic, with planted causes; the analysis recovered all 7 unreliable suppliers and all 4 chronic machines without being told | BUSINESS_INSIGHTS.md (last section) |
| 3 | What is EPC, and why does a fixed-price contract matter? | Contractor carries the overrun; revenue is locked, profit is decided in execution | docs/learning/PHASE_01 |
| 4 | How did you calculate cost variance, and why against the *revised* budget? | Actual - revised; client-paid scope is not an overrun | KPI_DEFINITIONS.md |
| 5 | What is the difference between profit and margin? Payback and ROI? | ₹ vs %; speed vs size | KPI_DEFINITIONS.md |
| 6 | Explain your data model. Why a star schema? What is a grain? | Facts at one grain, dimensions for context; budget and actual have different grains | DATA_MODEL.md |
| 7 | How did you avoid double counting? | Aggregate before joining; output grain chosen to avoid a 6x count; ledger vs sub-ledger reconciliation | DATA_MODEL.md |
| 8 | Give an example of a data-quality issue you fixed. | Supplier name variants; the hour-balance identity catching hidden decimal errors | DATA_QUALITY.md |
| 9 | Show me a window function you used and why. | Running totals, LAG month-on-month, RANK within industry | sql/07_window_functions.sql |
| 10 | Productivity vs efficiency vs utilisation vs capacity? | Five different questions, five formulas | KPI_DEFINITIONS.md |
| 11 | Is the cheaper supplier really cheaper? | Usually yes in total; the exception is SUP-008; fix *when* we order, not *who* | BUSINESS_INSIGHTS.md #5 |
| 12 | Correlation isn't causation. How do you know? | With/without comparison + regression + a named mechanism; design gate "halved for confounding" | ROI_ANALYSIS.md #3 |
| 13 | How did you pick the risk-score weights? | Derived from correlation with margin loss; validated by tier | KPI_DEFINITIONS.md (Risk score) |
| 14 | Which initiative first, and why not the one with the biggest NPV? | Certainty and speed; pilot the uncertain one | ROI_ANALYSIS.md |
| 15 | What are the limitations? What would you do with real data? | Synthetic data, assumed costs; ERP/MES integration, automated refresh | README.md (Limitations) |
